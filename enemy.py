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

# --- Pomocnicze heurystyki ---

def _chebyshev(ax, ay, bx, by):
    """Dystans Czebyszewa - lepsza miara dla ruchu 4-kierunkowego
    niż Manhattan, bo uwzględnia 'obwiednie' ruchów."""
    return max(abs(ax - bx), abs(ay - by))


def _has_los(ax, ay, bx, by, indest_fs):
    """Sprawdza czy między A i B nie ma niezniszczalnej ściany
    (tzw. Line Of Sight) idąc po prostej z krokiem STEP."""
    dx = bx - ax
    dy = by - ay
    steps = max(abs(dx), abs(dy)) // STEP
    if steps == 0:
        return True
    for i in range(1, steps + 1):
        cx = ax + dx * i // steps
        cy = ay + dy * i // steps
        tx, ty = cx // TILE, cy // TILE
        if (tx, ty) in indest_fs:
            return False
    return True


def _eval(bx, by, px, py, indest_fs, powerups, cost_acc):
    """
    Heurystyka oceniająca stan gry.

    Komponenty:
    - Odległość Czebyszewa do gracza (im bliżej tym lepiej dla bota)
    - Bonus za LOS do gracza (bot ma czysty strzał = warto być blisko)
    - Kara za koszt drogi (kolizje ze zniszczalnymi ścianami)
    - Premia za bliskość użytecznego power-upa (jeśli gracz jest daleko)
    """
    dist_to_player = _chebyshev(bx, by, px, py)

    los_bonus = 0
    if indest_fs is not None:
        same_row = abs(by - py) < 16
        same_col = abs(bx - px) < 16
        if (same_row or same_col) and _has_los(bx, by, px, py, indest_fs):
            los_bonus = 80

    pu_bonus = 0
    if powerups and dist_to_player > 120:
        closest_pu = min(
            (_chebyshev(bx, by, pw[0], pw[1]), pw) for pw in powerups
        )
        pu_dist, _ = closest_pu
        if pu_dist < 100:
            pu_bonus = max(0, 40 - pu_dist // 3)

    score = -dist_to_player * 2 + los_bonus + pu_bonus - cost_acc * 2
    return score


def _move_cost(nx, ny, indest_fs, dest_fs):
    #Sprawdzamy koszt wejścia na pozycję (nx, ny) testując 4 rogi hitboxa czołgu
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


def _player_can_shoot(bx, by, px, py, indest_fs):
    """Symulacja: czy gracz mógłby strzelić w bota z pozycji (px, py)?"""
    same_row = abs(py - by) < 16
    same_col = abs(px - bx) < 16
    if not (same_row or same_col):
        return False
    return _has_los(px, py, bx, by, indest_fs)


def _minimax(bx, by, px, py, indest_fs, dest_fs, cost_acc, depth, alpha, beta, maxi, powerups=None):
    if depth == 0:
        return _eval(bx, by, px, py, indest_fs, powerups, cost_acc)

    if maxi:
        #Tura bota (MAX)
        best = -INF
        moved = False
        for d in DIRS:
            nx = bx + d[0] * STEP
            ny = by + d[1] * STEP
            c  = _move_cost(nx, ny, indest_fs, dest_fs)
            if c == INF:
                continue
            moved = True
            val   = _minimax(nx, ny, px, py, indest_fs, dest_fs,
                             cost_acc + c, depth-1, alpha, beta, False, powerups)
            if val > best: best = val
            alpha = max(alpha, best)
            if beta <= alpha: break  # przycinanie alfa-beta
        return best if moved else _eval(bx, by, px, py, indest_fs, powerups, cost_acc)
    else:
        #Tura gracza (MIN)
        if _player_can_shoot(bx, by, px, py, indest_fs):
            shot_penalty = _eval(bx, by, px, py, indest_fs, powerups, cost_acc) - 60
            return shot_penalty

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
                             cost_acc, depth-1, alpha, beta, True, powerups)
            if val < best: best = val
            beta = min(beta, best)
            if beta <= alpha: break
        return best if moved else _eval(bx, by, px, py, indest_fs, powerups, cost_acc)


def _best_direction(bx, by, px, py, indest_fs, dest_fs, powerups=None):
    best_val, best_dir = -INF, None
    for d in DIRS:
        nx = bx + d[0] * STEP
        ny = by + d[1] * STEP
        c  = _move_cost(nx, ny, indest_fs, dest_fs)
        if c == INF:
            continue
        val = _minimax(nx, ny, px, py, indest_fs, dest_fs,
                       c, DEPTH-1, -INF, INF, False, powerups)
        if val > best_val:
            best_val, best_dir = val, d
    return best_dir


def _can_shoot(bx, by, d, px, py, indest_fs, dest_fs=None):
    #sprawdzamy czy strzał w kierunku d ma w pełni czystą linię do gracza
    #Blokujemy LOS na OBU rodzajach ścian
    dx, dy = d
    if dx != 0 and abs(by - py) >= 16: return False
    if dy != 0 and abs(bx - px) >= 16: return False
    cx, cy = bx, by
    for _ in range(25):
        cx += dx * 10; cy += dy * 10
        tx, ty = cx // TILE, cy // TILE
        if not (0 <= tx < 20 and 0 <= ty < 15):
            return False
        if (tx, ty) in indest_fs:
            return False
        if dest_fs is not None and (tx, ty) in dest_fs:
            return False
        if abs(cx - px) < 16 and abs(cy - py) < 16:
            return True
    return False


def _nearest_powerup_dir(bx, by, powerups, indest_fs, dest_fs):
    """Zwraca kierunek do najbliższego power-upa lub None."""
    if not powerups:
        return None
    best_dist = INF
    best_pu = None
    for pu in powerups:
        d = _chebyshev(bx, by, pu[0], pu[1])
        if d < best_dist:
            best_dist = d
            best_pu = pu

    if best_pu is None or best_dist > 200:
        return None

    best_val, best_dir = INF, None
    for d in DIRS:
        nx = bx + d[0] * STEP
        ny = by + d[1] * STEP
        c = _move_cost(nx, ny, indest_fs, dest_fs)
        if c == INF:
            continue
        dist = _chebyshev(nx, ny, best_pu[0], best_pu[1])
        if dist < best_val:
            best_val, best_dir = dist, d
    return best_dir


class EnemyTank(Tank):
    THINK_EVERY = 15  #ilość klatek do uruchomienia MiniMax

    def __init__(self, x, y):
        super().__init__(x, y, (200, 0, 0))
        self.speed        = 2
        self._timer       = random.randint(0, self.THINK_EVERY - 1)
        self._move_dir    = random.choice(DIRS)
        self._stuck_timer = 0
        self._last_pos    = (x, y)
        self.reload_time += random.randint(-150, 150)
        self._go_for_powerup = False
        self._ally_dodge_timer = 0  #cooldown na zmianę kierunku przez sojusznika

    def update_ai(self, player_rect, all_walls, dest_walls, enemy_bullets,
                  powerups=None, player_bullets=None, other_enemies=None):
        old_pos = self.rect.copy()
        self._ally_dodge_timer = max(0, self._ally_dodge_timer - 1)

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
        bx, by = self.rect.centerx, self.rect.centery

        pu_positions = [(pw.rect.centerx, pw.rect.centery) for pw in powerups] if powerups else []

        #Wykrywamy czy bot utknął
        cur_pos = (bx, by)
        if cur_pos == self._last_pos:
            self._stuck_timer += 1
        else:
            self._stuck_timer = 0
        self._last_pos = cur_pos

        if self._stuck_timer > 30:
            self._stuck_timer = 0
            free = [d for d in DIRS
                    if _move_cost(bx + d[0]*STEP,
                                  by + d[1]*STEP,
                                  indest_fs, dest_fs) < INF]
            if free:
                self._move_dir = random.choice(free)
            self._timer = self.THINK_EVERY

        #Co THINK_EVERY klatek - logika wyboru celu i Minimax
        self._timer += 1
        if self._timer >= self.THINK_EVERY:
            self._timer = -random.randint(0, 5)

            dist_to_player = _chebyshev(bx, by, px, py)

            self._go_for_powerup = False
            if pu_positions and dist_to_player > 150:
                nearest_pu_dist = min(_chebyshev(bx, by, p[0], p[1]) for p in pu_positions)
                needs_powerup = not self.has_armor or not self.has_strong_shot
                if nearest_pu_dist < 180 and needs_powerup:
                    self._go_for_powerup = True

            if self._go_for_powerup:
                new_dir = _nearest_powerup_dir(bx, by, pu_positions, indest_fs, dest_fs)
            else:
                new_dir = _best_direction(bx, by, px, py, indest_fs, dest_fs, pu_positions)

            if new_dir is not None:
                self._move_dir = new_dir

        #Wykonujemy ruch w wybranym kierunku
        d = self._move_dir
        if d != self.direction:
            self.direction = d
            self.rotate(d)

        self.rect.x += self.direction[0] * self.speed
        self.rect.y += self.direction[1] * self.speed

        #Obsługa kolizji - ze ścianą I z innym botem
        hit = pygame.sprite.spritecollideany(self, all_walls)
        ally_hit = None
        if other_enemies:
            for other in other_enemies:
                if self.rect.colliderect(other.rect):
                    ally_hit = other
                    break

        if hit:
            self.rect = old_pos

            # Sprawdzamy czy old_pos nie jest wewnątrz ściany
            if pygame.sprite.spritecollideany(self, all_walls):
                #Snap do ŚRODKA kafelka (środki: 20, 60, 100, ...)
                tcol = self.rect.centerx // TILE
                trow = self.rect.centery  // TILE
                tx = int(tcol * TILE + TILE // 2)
                ty = int(trow * TILE + TILE // 2)
                self.rect.center = (tx, ty)
                if pygame.sprite.spritecollideany(self, all_walls):
                    for d2 in DIRS:
                        self.rect.center = (tx + d2[0]*TILE, ty + d2[1]*TILE)
                        if not pygame.sprite.spritecollideany(self, all_walls):
                            break

            hit_dest = getattr(hit, 'destructible', False)
            if hit_dest:
                #Strzelamy w zniszczalną ścianę tylko jeśli FAKTYCZNIE jest przed lufą
                #i nie ma już pocisku w drodze, i nie ma sojusznika w linii ognia.
                #
                #Jeśli wall_in_front jest False (np. snap-to-tile-center wyplątał nas
                #z bocznej kolizji 34x34), po prostu NIC NIE ROBIMY - bot pojedzie dalej
                #w następnej klatce. Wcześniejsza wersja resetowała kierunek tutaj co
                #klatkę co dawało efekt "kręcenia się wokół własnej osi".
                wall_in_front = any(
                    w.rect.colliderect(self._front_rect(20)) for w in dest_walls
                )
                if (wall_in_front
                        and not self._friendly_bullet_in_path(enemy_bullets, player_bullets)
                        and not self._ally_in_line(other_enemies)):
                    self.shoot(enemy_bullets)
            else:
                #Niezniszczalna ściana - szukamy wolnego kierunku
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
        elif ally_hit:
            #Kolizja z innym botem - cofamy się i ZMIENIAMY KIERUNEK NAJWYŻEJ RAZ NA
            #~20 klatek (cooldown). Bez cooldownu każda klatka kolizji wybierała nowy
            #kierunek (losowo z preferowanych) i bot kręcił się wokół własnej osi.
            self.rect = old_pos
            if self._ally_dodge_timer == 0:
                #DETERMINISTYCZNY wybór: pierwsza próba to "ucieczka od sojusznika"
                #w osi w której jest najbliżej. Kolejne to perpendykularne.
                adx = self.rect.centerx - ally_hit.rect.centerx  # wektor OD sojusznika
                ady = self.rect.centery  - ally_hit.rect.centery
                if abs(adx) >= abs(ady):
                    primary = (1, 0) if adx >= 0 else (-1, 0)
                    candidates = [primary, (0, -1), (0, 1), (-primary[0], 0)]
                else:
                    primary = (0, 1) if ady >= 0 else (0, -1)
                    candidates = [primary, (-1, 0), (1, 0), (0, -primary[1])]

                for d2 in candidates:
                    if d2 == self.direction:
                        continue
                    if _move_cost(self.rect.centerx + d2[0]*STEP,
                                  self.rect.centery + d2[1]*STEP,
                                  indest_fs, dest_fs) == INF:
                        continue
                    test_rect = self.rect.move(d2[0]*STEP, d2[1]*STEP)
                    if any(test_rect.colliderect(o.rect) for o in other_enemies):
                        continue
                    #Zmieniamy tylko _move_dir - rotacja zachodzi w bloku ruchu
                    #w następnej klatce (a NIE tutaj co klatkę). To gwarantuje
                    #że rotacja dzieje się max raz na zmianę kierunku.
                    self._move_dir = d2
                    self._ally_dodge_timer = 20  #~0.33s cooldownu
                    break
            #Nie resetujemy self._timer - niech Minimax działa na normalnym harmonogramie
            #(wcześniej reset timera dawał Minimaxowi natychmiastową szansę wybrania
            #znowu kierunku w sojusznika - druga przyczyna spinów).

        #Heurystyka strzału sprawdzamy czy gracz jest w linii ognia
        bx, by = self.rect.centerx, self.rect.centery
        shoot_dir = self._dir_to(player_rect)
        if _can_shoot(bx, by, shoot_dir, px, py, indest_fs, dest_fs):
            #Rotujemy do shoot_dir TYLKO jeśli reload jest gotowy. Wcześniej bot
            #rotował tam-i-z-powrotem co klatkę (rotacja zachodzi też gdy strzał
            #nie idzie bo reload), co dawało "migotanie/kręcenie" lufy.
            if self.get_reload_progress() >= 1.0:
                saved = self.direction
                if shoot_dir != self.direction:
                    self.direction = shoot_dir
                    self.rotate(shoot_dir)
                #Nie strzelamy jeśli sojusznik byłby w linii ognia (friendly fire)
                if not self._ally_in_line(other_enemies):
                    self.shoot(enemy_bullets)
                if self.direction != saved:
                    self.direction = saved
                    self.rotate(saved)
        elif any(w.rect.colliderect(self._front_rect(14)) for w in dest_walls):
            #Zniszczalna ściana przed nami - strzelamy żeby ją usunąć, chyba że
            #już leci pocisk w tym kierunku lub sojusznik stoi w linii ognia
            if (not self._friendly_bullet_in_path(enemy_bullets, player_bullets)
                    and not self._ally_in_line(other_enemies)):
                self.shoot(enemy_bullets)

    def _dir_to(self, target):
        dx = target.centerx - self.rect.centerx
        dy = target.centery  - self.rect.centery
        if abs(dx) > abs(dy): return (1, 0) if dx > 0 else (-1, 0)
        return (0, 1) if dy > 0 else (0, -1)

    def _front_rect(self, dist):
        d = self.direction
        if d==(0,-1): return pygame.Rect(self.rect.centerx-5, self.rect.top-dist,   10,   dist)
        if d==(0, 1): return pygame.Rect(self.rect.centerx-5, self.rect.bottom,     10,   dist)
        if d==(-1,0): return pygame.Rect(self.rect.left-dist,  self.rect.centery-5, dist, 10)
        if d==(1, 0): return pygame.Rect(self.rect.right,      self.rect.centery-5, dist, 10)
        return self.rect.copy()

    def _friendly_bullet_in_path(self, enemy_bullets, player_bullets=None, max_dist=70):
        """
        Czy w naszej linii ognia leci już jakiś pocisk w tym samym kierunku?
        Jeśli tak - nie wystrzeliwujemy drugiego, bo pierwszy zniszczy ścianę
        a nasz pocisk poleci do końca ekranu w pustkę.
        """
        d = self.direction
        if d == (0, 0):
            return False
        bx, by = self.rect.centerx, self.rect.centery

        def check(bullets):
            if bullets is None:
                return False
            for b in bullets:
                if b.direction != d:
                    continue
                forward = d[0] * (b.rect.centerx - bx) + d[1] * (b.rect.centery - by)
                if not (0 < forward < max_dist):
                    continue
                if d[0] != 0 and abs(b.rect.centery - by) < 16:
                    return True
                if d[1] != 0 and abs(b.rect.centerx - bx) < 16:
                    return True
            return False

        return check(enemy_bullets) or check(player_bullets)

    def _ally_in_line(self, allies, max_dist=200):
        """
        Czy w naszej linii ognia stoi inny bot (sojusznik)?
        Jeśli tak - nie strzelamy, bo trafilibyśmy własnego (friendly fire).
        Sprawdzamy oś, kierunek i odległość do max_dist pikseli.
        """
        d = self.direction
        if d == (0, 0) or not allies:
            return False
        bx, by = self.rect.centerx, self.rect.centery
        for ally in allies:
            forward = d[0] * (ally.rect.centerx - bx) + d[1] * (ally.rect.centery - by)
            if not (0 < forward < max_dist):
                continue
            #tolerancja prostopadła - czołg ma ~20px szerokości, dajemy 22px
            if d[0] != 0 and abs(ally.rect.centery - by) < 22:
                return True
            if d[1] != 0 and abs(ally.rect.centerx - bx) < 22:
                return True
        return False