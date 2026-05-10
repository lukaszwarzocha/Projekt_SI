import pygame
import random
from tank import Tank

#Możliwe kierunki ruchu czołgu (góra, dół, lewo, prawo)
DIRS  = [(0, -1), (0, 1), (-1, 0), (1, 0)]
INF   = float('inf')
TILE  = 40   #rozmiar kafelka w pikselach
STEP  = 20   #krok symulacji w Minimax (pół kafelka)
DEPTH = 4    #głębokość drzewa Minimax
COST_DEST = 8  #koszt przejścia przez zniszczalną ścianę


def _dist(ax, ay, bx, by):
    # Dystans Manhattan między dwoma punktami
    return abs(ax - bx) + abs(ay - by)


def _move_cost(nx, ny, indest_fs, dest_fs):
    #Sprawdzamy koszt wejścia na pozycję (nx, ny) testując 4 rogi hitboxa czołgu
    #Niezniszczalna ściana = INF (całkowita blokada), zniszczalna = COST_DEST
    half = 8
    best = 0
    for cx in (nx - half, nx + half):
        for cy in (ny - half, ny + half):
            tx, ty = cx // TILE, cy // TILE
            if not (0 <= tx < 20 and 0 <= ty < 15):
                return INF
            if (tx, ty) in indest_fs:
                return INF
            if (tx, ty) in dest_fs:
                best = COST_DEST
    return best


def _minimax(bx, by, px, py, indest_fs, dest_fs, cost_acc, depth, alpha, beta, maxi):
    #Warunek stopu oceniamy stan gdy dotarliśmy do liścia drzewa
    if depth == 0:
        return -_dist(bx, by, px, py) - cost_acc * 2

    if maxi:
        #Tura bota (MAX) szukamy ruchu który maksymalizuje ocenę
        best = -INF
        moved = False
        for d in DIRS:
            nx = bx + d[0] * STEP
            ny = by + d[1] * STEP
            c  = _move_cost(nx, ny, indest_fs, dest_fs)
            if c == INF:
                continue  #niezniszczalna ściana pomijamy kierunek
            moved = True
            val   = _minimax(nx, ny, px, py, indest_fs, dest_fs,
                             cost_acc + c, depth-1, alpha, beta, False)
            if val > best: best = val
            alpha = max(alpha, best)
            if beta <= alpha: break  # przycinanie alfa-beta
        return best if moved else -_dist(bx, by, px, py) - cost_acc * 2
    else:
        #Tura gracza (MIN) zakładamy że gracz ucieka od bota
        best = INF
        moved = False
        for d in DIRS:
            nx = px + d[0] * STEP
            ny = py + d[1] * STEP
            tx, ty = nx // TILE, ny // TILE
            if not (0 <= tx < 20 and 0 <= ty < 15) or (tx, ty) in indest_fs:
                continue
            moved = True
            val   = _minimax(bx, by, nx, ny, indest_fs, dest_fs,
                             cost_acc, depth-1, alpha, beta, True)
            if val < best: best = val
            beta = min(beta, best)
            if beta <= alpha: break  #przycinanie alfa-beta
        return best if moved else -_dist(bx, by, px, py) - cost_acc * 2


def _best_direction(bx, by, px, py, indest_fs, dest_fs):
    #Sprawdzamy każdy możliwy kierunek i wybieramy ten z najwyższą oceną Minimax
    best_val, best_dir = -INF, None
    for d in DIRS:
        nx = bx + d[0] * STEP
        ny = by + d[1] * STEP
        c  = _move_cost(nx, ny, indest_fs, dest_fs)
        if c == INF:
            continue
        val = _minimax(nx, ny, px, py, indest_fs, dest_fs,
                       c, DEPTH-1, -INF, INF, False)
        if val > best_val:
            best_val, best_dir = val, d
    return best_dir


def _can_shoot(bx, by, d, px, py, indest_fs):
    #sprawdzamy czy strzał w kierunku d trafi gracza
    #trzeba być w tej samej osi co kierunek strzału
    dx, dy = d
    if dx != 0 and abs(by - py) >= 16: return False
    if dy != 0 and abs(bx - px) >= 16: return False
    cx, cy = bx, by
    for _ in range(25):
        cx += dx * 10; cy += dy * 10
        tx, ty = cx // TILE, cy // TILE
        if not (0 <= tx < 20 and 0 <= ty < 15) or (tx, ty) in indest_fs:
            return False  #ściana niezniszczalna blokuje tor pocisku
        if abs(cx - px) < 16 and abs(cy - py) < 16:
            return True  #pocisk trafia gracza
    return False


class EnemyTank(Tank):
    THINK_EVERY = 15  #ilośc klatek do uruchomienia MiniMax

    def __init__(self, x, y):
        super().__init__(x, y, (200, 0, 0))
        self.speed        = 2
        self._timer       = random.randint(0, self.THINK_EVERY - 1)  #losowy start
        self._move_dir    = random.choice(DIRS)
        self._stuck_timer = 0
        self._last_pos    = (x, y)
        self.reload_time += random.randint(-150, 150)  #różny czas przeładowania

    def update_ai(self, player_rect, all_walls, dest_walls, enemy_bullets):
        old_pos = self.rect.copy()

        #Budujemy zbiory kafelków dla obu typów ścian
        dest_fs = frozenset(
            (w.rect.centerx // TILE, w.rect.centery // TILE)
            for w in dest_walls
        )
        indest_fs = frozenset(
            (w.rect.centerx // TILE, w.rect.centery // TILE)
            for w in all_walls
            if (w.rect.centerx // TILE, w.rect.centery // TILE) not in dest_fs
        )

        px, py = player_rect.centerx, player_rect.centery

        #Wykrywamy czy bot utknął w miejscu przez za długo
        cur_pos = (self.rect.centerx, self.rect.centery)
        if cur_pos == self._last_pos:
            self._stuck_timer += 1
        else:
            self._stuck_timer = 0
        self._last_pos = cur_pos

        #Po 30 klatkach bez ruchu wymuszamy losowy wolny kierunek
        if self._stuck_timer > 30:
            self._stuck_timer = 0
            free = [d for d in DIRS
                    if _move_cost(self.rect.centerx + d[0]*STEP,
                                  self.rect.centery + d[1]*STEP,
                                  indest_fs, dest_fs) < INF]
            if free:
                self._move_dir = random.choice(free)
            self._timer = self.THINK_EVERY

        #Co THINK_EVERY klatek uruchamiamy Minimax żeby wybrać nowy kierunek
        self._timer += 1
        if self._timer >= self.THINK_EVERY:
            self._timer = -random.randint(0, 5)  #żeby boty nie myślały w tym samym momencie
            new_dir = _best_direction(
                self.rect.centerx, self.rect.centery,
                px, py, indest_fs, dest_fs)
            if new_dir is not None:
                self._move_dir = new_dir

        #Wykonujemy ruch w wybranym kierunku
        d = self._move_dir
        if d != self.direction:
            self.direction = d
            self.rotate(d)

        self.rect.x += self.direction[0] * self.speed
        self.rect.y += self.direction[1] * self.speed

        #Obsługa kolizji ze ścianą
        hit = pygame.sprite.spritecollideany(self, all_walls)
        if hit:
            self.rect = old_pos

            # Sprawdzamy czy old_pos nie jest wewnątrz ściany (np. po zniszczeniu ściany)
            if pygame.sprite.spritecollideany(self, all_walls):
                tx = round(self.rect.centerx / TILE) * TILE
                ty = round(self.rect.centery  / TILE) * TILE
                self.rect.center = (tx, ty)
                if pygame.sprite.spritecollideany(self, all_walls):
                    for d2 in DIRS:
                        self.rect.center = (tx + d2[0]*TILE, ty + d2[1]*TILE)
                        if not pygame.sprite.spritecollideany(self, all_walls):
                            break

            hit_dest = getattr(hit, 'destructible', False)
            if hit_dest:
                #Zniszczalna ściana strzelamy żeby ją usunąć
                self.shoot(enemy_bullets)
            else:
                #Niezniszczalna ściana szukamy wolnego kierunku
                free = [d2 for d2 in DIRS
                        if d2 != self.direction and
                        _move_cost(self.rect.centerx + d2[0]*STEP,
                                   self.rect.centery + d2[1]*STEP,
                                   indest_fs, dest_fs) < INF]
                if free:
                    self._move_dir = random.choice(free)
                    self.direction = self._move_dir
                    self.rotate(self._move_dir)
                self._timer = self.THINK_EVERY

        #Heurystyka strzału sprawdzamy czy gracz jest w linii ognia
        bx, by = self.rect.centerx, self.rect.centery
        shoot_dir = self._dir_to(player_rect)
        if _can_shoot(bx, by, shoot_dir, px, py, indest_fs):
            saved = self.direction
            if shoot_dir != self.direction:
                self.direction = shoot_dir
                self.rotate(shoot_dir)
            self.shoot(enemy_bullets)
            if self.direction != saved:
                #Wracamy do kierunku jazdy po strzale
                self.direction = saved
                self.rotate(saved)
        elif any(w.rect.colliderect(self._front_rect(14)) for w in dest_walls):
            #Zniszczalna ściana przed nami strzelamy żeby ją usunąć
            self.shoot(enemy_bullets)

    def _dir_to(self, target):
        #Zwracamy kierunek do celu na podstawie większej różnicy osi
        dx = target.centerx - self.rect.centerx
        dy = target.centery  - self.rect.centery
        if abs(dx) > abs(dy): return (1, 0) if dx > 0 else (-1, 0)
        return (0, 1) if dy > 0 else (0, -1)

    def _front_rect(self, dist):
        #Zwracamy prostokąt przed lufą czołgu do wykrywania ścian
        d = self.direction
        if d==(0,-1): return pygame.Rect(self.rect.centerx-5, self.rect.top-dist,   10,   dist)
        if d==(0, 1): return pygame.Rect(self.rect.centerx-5, self.rect.bottom,     10,   dist)
        if d==(-1,0): return pygame.Rect(self.rect.left-dist,  self.rect.centery-5, dist, 10)
        if d==(1, 0): return pygame.Rect(self.rect.right,      self.rect.centery-5, dist, 10)
        return self.rect.copy()