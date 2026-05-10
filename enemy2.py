import pygame
import heapq
import random
from tank import Tank

class EnemyTankCP(Tank):
    SHOOT_MARGIN = 30  #tolerancja linii ognia

    def __init__(self, x, y):
        super().__init__(x, y, (200, 0, 0))
        self.speed = 2

        #Dane ścieżki A*
        self.path         = []
        self._last_goal   = None
        self._last_indest = None  # cache niezniszczalnych ścian

        self.idle_timer     = 0
        self.idle_dir_timer = 0

        self._shoot_cooldown    = 0
        self._post_shot_target  = None
        self._post_shot_timeout = 0
        self._wander_target     = None  #punkt docelowy patrolu w strefie

    def update_ai(self, target_rect, player_rect, player_bullets,
                  all_walls, dest_walls, enemy_bullets, indest_walls=None):
        old_pos = self.rect.copy()
        self._shoot_cooldown    = max(0, self._shoot_cooldown - 1)
        self._post_shot_timeout = max(0, self._post_shot_timeout - 1)

        #Sprawdzamy czy środek bota jest wewnątrz strefy przejmowania
        in_point = target_rect.collidepoint(self.rect.centerx, self.rect.centery)

        if not in_point:
            self._drive_to_point(target_rect, player_rect, all_walls,
                                 dest_walls, enemy_bullets, indest_walls)
        else:
            self._patrol_in_point(target_rect, player_rect, all_walls,
                                  enemy_bullets, indest_walls)

        #Cofamy pozycję jeśli wjechaliśmy w ścianę i resetujemy ścieżkę A*
        if pygame.sprite.spritecollideany(self, all_walls):
            self.rect      = old_pos
            self.path      = []
            self._last_goal = None

    def _drive_to_point(self, target_rect, player_rect, all_walls,
        dest_walls, enemy_bullets, indest_walls):

        # Przeliczamy pozycje na kafelki do użycia w A*
        start = (self.rect.centerx // 40, self.rect.centery // 40)
        goal  = (target_rect.centerx  // 40, target_rect.centery  // 40)

        dest_coords = frozenset(
            (w.rect.centerx // 40, w.rect.centery // 40) for w in dest_walls
        )
        indest_coords = frozenset(
            (w.rect.centerx // 40, w.rect.centery // 40) for w in all_walls
            if (w.rect.centerx // 40, w.rect.centery // 40) not in dest_coords
        )

        #Przeliczamy ścieżkę gdy cel się zmienił lub mapa się zmieniła
        if (goal != self._last_goal
                or indest_coords != self._last_indest
                or not self.path):
            self.path         = self._a_star(start, goal, indest_coords, dest_coords)
            self._last_goal   = goal
            self._last_indest = indest_coords

        #Strzelamy do gracza w trakcie jazdy
        self._try_shoot_at_player(player_rect, enemy_bullets, indest_walls,
                                  target_rect, all_walls)

        if not self.path:
            return

        #Pobieramy następny kafelek z ścieżki i obliczamy jego środek w pikselach
        tx = self.path[0][0] * 40 + 20
        ty = self.path[0][1] * 40 + 20

        #Wyrównujemy pozycję do osi kafelka żeby nie dryfować między kafelkami
        if abs(tx - self.rect.centerx) < 6: self.rect.centerx = tx
        if abs(ty - self.rect.centery)  < 6: self.rect.centery = ty

        #Obliczamy kierunek do następnego kafelka
        dx = (1 if tx > self.rect.centerx else -1 if tx < self.rect.centerx else 0)
        dy = (1 if ty > self.rect.centery  else -1 if ty < self.rect.centery  else 0)
        nav = (dx, dy) if (dx, dy) != (0, 0) else self.direction
        if nav != self.direction:
            self.direction = nav
            self.rotate(self.direction)

        #Jeśli zniszczalna ściana przed nami strzelamy, w przeciwnym razie jedziemy
        if self.wall_in_front(list(dest_walls), check_dist=15):
            self.shoot(enemy_bullets)
        else:
            self.rect.x += self.direction[0] * self.speed
            self.rect.y += self.direction[1] * self.speed

        #Zdejmujemy osiągnięty węzeł ze ścieżki
        if abs(self.rect.centerx - tx) < 5 and abs(self.rect.centery - ty) < 5:
            self.path.pop(0)

    def _patrol_in_point(self, target_rect, player_rect, all_walls,
                         enemy_bullets, indest_walls):
        #Sprawdzamy czy gracz jest wewnątrz strefy przejmowania
        player_in_zone = target_rect.collidepoint(player_rect.centerx, player_rect.centery)

        #Jeśli brak celu losujemy nowy lub ustawiamy gracza jako cel
        if self._wander_target is None:
            self._wander_target = self._pick_wander_target(
                target_rect, all_walls, player_rect if player_in_zone else None)

        tx, ty = self._wander_target

        #Cel osiągnięty losujemy następny punkt
        if abs(self.rect.centerx - tx) < 16 and abs(self.rect.centery - ty) < 16:
            self._wander_target = self._pick_wander_target(
                target_rect, all_walls, player_rect if player_in_zone else None)
            tx, ty = self._wander_target

        #Sprawdzamy czy obecny kierunek jest nadal dobry
        cur_ok = False
        if self.direction != (0, 0):
            test = self.rect.move(self.direction[0] * self.speed,
                                  self.direction[1] * self.speed)
            wall_free = not any(w.rect.colliderect(test) for w in all_walls)
            if player_in_zone:
                #Gdy gracz w strefie wystarczy że kierunek jest wolny od ścian
                cur_ok = wall_free
            else:
                #Podczas normalnego patrolu kierunek musi też zbliżać do celu
                moves_closer = (
                    abs(test.centerx - tx) + abs(test.centery - ty)
                    < abs(self.rect.centerx - tx) + abs(self.rect.centery - ty)
                )
                cur_ok = wall_free and moves_closer

        if not cur_ok:
            #Wybieramy nowy kierunek poruszania się
            dx = tx - self.rect.centerx
            dy = ty - self.rect.centery
            if abs(dx) >= abs(dy):
                candidates = [
                    (1, 0) if dx > 0 else (-1, 0),
                    (0, 1) if dy > 0 else (0, -1),
                ]
            else:
                candidates = [
                    (0, 1) if dy > 0 else (0, -1),
                    (1, 0) if dx > 0 else (-1, 0),
                ]
            candidates += [(-candidates[0][0], -candidates[0][1])]

            chosen = None
            for d in candidates:
                test = self.rect.move(d[0] * self.speed, d[1] * self.speed)
                if not any(w.rect.colliderect(test) for w in all_walls):
                    chosen = d
                    break

            if chosen and chosen != self.direction:
                self.direction = chosen
                self.rotate(chosen)
            elif chosen is None:
                #Wszystkie kierunki zablokowane losujemy zupełnie nowy cel
                self._wander_target = self._pick_wander_target(
                    target_rect, all_walls, None)

        # Wykonujemy ruch
        old_pos = self.rect.copy()
        if self.direction != (0, 0):
            self.rect.x += self.direction[0] * self.speed
            self.rect.y += self.direction[1] * self.speed

        # Cofamy i losujemy nowy cel jeśli wjechaliśmy w ścianę lub wyjechaliśmy ze strefy
        if (any(w.rect.colliderect(self.rect) for w in all_walls)
                or not target_rect.collidepoint(self.rect.centerx, self.rect.centery)):
            self.rect = old_pos
            self._wander_target = self._pick_wander_target(
                target_rect, all_walls, player_rect if player_in_zone else None)

        self._try_shoot_at_player(player_rect, enemy_bullets, indest_walls,
                                  target_rect, all_walls)

    def _pick_wander_target(self, target_rect, all_walls, player_rect=None):
        #Jeśli gracz jest w strefie ustawiamy go jako cel
        if player_rect is not None:
            return (player_rect.centerx, player_rect.centery)

        #Losujemy punkt wewnątrz strefy z marginesem od krawędzi
        margin = 15
        x_min = target_rect.left  + margin
        x_max = target_rect.right  - margin
        y_min = target_rect.top   + margin
        y_max = target_rect.bottom - margin

        for _ in range(30):
            cx = random.randint(x_min, x_max)
            cy = random.randint(y_min, y_max)
            probe = pygame.Rect(cx - 10, cy - 10, 20, 20)
            if not any(w.rect.colliderect(probe) for w in all_walls):
                return (cx, cy)

        return (target_rect.centerx, target_rect.centery)

    def _try_shoot_at_player(self, player_rect, enemy_bullets, indest_walls, target_rect, all_walls):
        if self._shoot_cooldown > 0:
            return

        drive_dir = self.direction
        shot_fired = False

        #Strzelamy jeśli gracz jest już w linii aktualnego kierunku jazdy
        if self.target_in_front(player_rect, margin=self.SHOOT_MARGIN):
            clear = (indest_walls is None
                     or self.has_clear_line_of_sight(player_rect, indest_walls))
            if clear:
                self.shoot(enemy_bullets)
                shot_fired = True

        if shot_fired:
            self._shoot_cooldown = 22
            new_pos = self._random_pos_in_zone(target_rect, all_walls)
            if new_pos:
                self._post_shot_target = new_pos
                self._post_shot_timeout = 90

    def _random_pos_in_zone(self, target_rect, all_walls):
        #Losujemy punkt docelowy wewnątrz strefy oddalony od obecnej pozycji bota
        margin = 12
        x_min, x_max = target_rect.left + margin, target_rect.right  - margin
        y_min, y_max = target_rect.top  + margin, target_rect.bottom - margin
        if x_max <= x_min or y_max <= y_min:
            return None
        current = pygame.math.Vector2(self.rect.center)
        for _ in range(40):
            cx = random.randint(x_min, x_max)
            cy = random.randint(y_min, y_max)
            if pygame.math.Vector2(cx, cy).distance_to(current) < 20:
                continue
            if not any(w.rect.colliderect(pygame.Rect(cx-10, cy-10, 20, 20))
                       for w in all_walls):
                return (cx, cy)
        return None

    def get_best_direction(self, target_rect):
        #Wybieramy kierunek w stronę celu na podstawie większej różnicy osi
        dx = target_rect.centerx - self.rect.centerx
        dy = target_rect.centery  - self.rect.centery
        if abs(dx) > abs(dy): return (1, 0) if dx > 0 else (-1, 0)
        return (0, 1) if dy > 0 else (0, -1)

    def target_in_front(self, target_rect, margin=25):
        #Sprawdzamy czy cel jest w linii strzału przed lufą
        d = self.direction
        if d == (0,-1): return abs(self.rect.centerx-target_rect.centerx)<margin and target_rect.centery<self.rect.centery
        if d == (0, 1): return abs(self.rect.centerx-target_rect.centerx)<margin and target_rect.centery>self.rect.centery
        if d == (-1,0): return abs(self.rect.centery-target_rect.centery)<margin and target_rect.centerx<self.rect.centerx
        if d == (1, 0): return abs(self.rect.centery-target_rect.centery)<margin and target_rect.centerx>self.rect.centerx
        return False

    def wall_in_front(self, dest_walls, check_dist=15):
        #Tworzymy prostokąt przed lufą i sprawdzamy czy koliduje ze zniszczalną ścianą
        d = self.direction
        if d==(0,-1): r=pygame.Rect(self.rect.centerx-5, self.rect.top-check_dist, 10, check_dist)
        elif d==(0,1):r=pygame.Rect(self.rect.centerx-5, self.rect.bottom, 10, check_dist)
        elif d==(-1,0):r=pygame.Rect(self.rect.left-check_dist, self.rect.centery-5, check_dist,10)
        elif d==(1, 0):r=pygame.Rect(self.rect.right, self.rect.centery-5, check_dist,10)
        else: return False
        return any(w.rect.colliderect(r) for w in dest_walls)

    def has_clear_line_of_sight(self, target_rect, indest_walls):
        #sprawdzamy czy niezniszczalna ściana blokuje tor pocisku do celu
        dx, dy = self.direction
        cx, cy = self.rect.centerx, self.rect.centery
        steps  = (abs(target_rect.centerx-cx) if dx else abs(target_rect.centery-cy)) // 10
        for i in range(1, int(steps)+1):
            p = pygame.Rect(cx+dx*i*10-4, cy+dy*i*10-4, 8, 8)
            if any(w.rect.colliderect(p) for w in indest_walls):
                return False
        return True

    def _a_star(self, start, goal, indest_walls, dest_walls_coords):
        #Algorytm A* na siatce kafelków koszt zniszczalnej ściany = 6, wolne pole = 1
        def h(a, b):
            return abs(a[0]-b[0]) + abs(a[1]-b[1])  # heurystyka Manhattan

        queue = [(0, start)]
        came_from = {start: None}
        cost_so_far = {start: 0}

        while queue:
            _, curr = heapq.heappop(queue)

            if curr == goal:
                break
            for d in [(0,1),(0,-1),(1,0),(-1,0)]:
                nxt = (curr[0]+d[0], curr[1]+d[1])
                if not (0 <= nxt[0] < 20 and 0 <= nxt[1] < 15):
                    continue
                if nxt in indest_walls:
                    continue  #niezniszczalna ściana pomijamy
                step     = 6 if nxt in dest_walls_coords else 1
                new_cost = cost_so_far[curr] + step

                if nxt not in cost_so_far or new_cost < cost_so_far[nxt]:
                    cost_so_far[nxt] = new_cost
                    heapq.heappush(queue, (new_cost + h(nxt, goal), nxt))
                    came_from[nxt] = curr

        #Odtwarzamy ścieżkę idąc wstecz od celu do startu
        path, c = [], goal
        while c in came_from and c != start:
            path.append(c)
            c = came_from[c]
        return path[::-1]