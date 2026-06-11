import pygame
import sys
import random
import glob
from tank import Tank
from enemy import EnemyTank
from enemy2 import EnemyTankCP
from map_loader import load_map

SCREEN_WIDTH, SCREEN_HEIGHT = 800, 600
TILE_SIZE, FPS = 40, 60

pygame.init()
FONT_BIG   = pygame.font.SysFont("Arial", 64, bold=True)
FONT_MID   = pygame.font.SysFont("Arial", 32, bold=True)
FONT_SMALL = pygame.font.SysFont("Arial", 20)

class PowerUp(pygame.sprite.Sprite):
    def __init__(self, x, y, p_type):
        super().__init__()
        self.type = p_type
        self.image = pygame.Surface((20, 20))
        self.rect = self.image.get_rect(center=(x, y))
        self.spawn_time = pygame.time.get_ticks()
        colors = {'strong': (255, 0, 0), 'armor': (0, 0, 255), 'life': (0, 255, 0)}
        self.image.fill(colors.get(p_type, (200, 200, 200)))

    def update(self):
        if pygame.time.get_ticks() - self.spawn_time > 15000:
            self.kill()

def get_random_map():
    maps = glob.glob("Maps/map*.txt")
    if not maps:
        return "Maps/map1.txt"
    return random.choice(maps)


def get_random_map_cp():
    maps = glob.glob("Maps2/map*.txt")
    if not maps:
        return "Maps2/map1.txt"
    return random.choice(maps)


def draw_text(screen, text, font, x, y, color=(255, 255, 255)):
    img = font.render(text, True, color)
    screen.blit(img, img.get_rect(center=(x, y)))

def draw_heart(screen, x, y, size, color):
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    r = size // 2
    pygame.draw.circle(surf, color, (r // 2, r // 2), r // 2)
    pygame.draw.circle(surf, color, (size - r // 2, r // 2), r // 2)
    pygame.draw.polygon(surf, color, [(0, r // 2), (size, r // 2), (size // 2, size)])
    screen.blit(surf, (x, y))

def draw_ui(screen, player):
    if player.extra_lives > 0:
        draw_heart(screen, 20, 20, 30, (220, 20, 20))


def spawn_powerup(powerups, all_walls):
    if len(powerups) >= 2:
        return
    for _ in range(15):
        px, py = random.randint(40, 760), random.randint(40, 560)
        temp = pygame.Rect(px - 10, py - 10, 20, 20)
        if not any(w.rect.colliderect(temp) for w in all_walls):
            powerups.add(PowerUp(px, py, random.choice(['strong', 'armor', 'life'])))
            break

def get_safe_spawn_point(all_walls, existing_tanks):
    for _ in range(50):
        rx, ry = random.randint(450, 750), random.randint(50, 550)
        temp = pygame.Rect(rx - 20, ry - 20, 40, 40)
        if (not any(w.rect.colliderect(temp) for w in all_walls)
                and not any(t.rect.colliderect(temp) for t in existing_tanks)):
            return rx, ry
    return 700, 300

COL_W = SCREEN_WIDTH  // 3
ROW_H = SCREEN_HEIGHT // 3

SECTOR_CENTERS = [
    (COL_W * c + COL_W // 2, ROW_H * r + ROW_H // 2)
    for r in range(3) for c in range(3)
]

CAP_W, CAP_H = 140, 140

def sector_to_rect(sector_idx):
    cx, cy = SECTOR_CENTERS[sector_idx]
    return pygame.Rect(cx - CAP_W // 2, cy - CAP_H // 2, CAP_W, CAP_H)

def opposite_side_spawn(sector_idx, all_walls, existing_tanks):
    col = sector_idx % 3
    if col == 0:
        x_range = (550, 760)
    elif col == 2:
        x_range = (40, 250)
    else:
        x_range = None

    for _ in range(80):
        if x_range:
            rx = random.randint(*x_range)
        else:
            rx = random.choice([random.randint(40, 280), random.randint(520, 760)])
        ry = random.randint(40, 560)
        temp = pygame.Rect(rx - 20, ry - 20, 40, 40)
        if (not any(w.rect.colliderect(temp) for w in all_walls)
                and not any(t.rect.colliderect(temp) for t in existing_tanks)):
            return rx, ry

    for ry_fb in range(60, 560, 40):
        temp = pygame.Rect(740, ry_fb - 20, 40, 40)
        if not any(w.rect.colliderect(temp) for w in all_walls):
            return 760, ry_fb
    return 760, 300


def handle_combat(player, enemies, player_bullets, enemy_bullets, dest_walls, indest_walls, all_walls):
    pygame.sprite.groupcollide(player_bullets, indest_walls, True, False)
    pygame.sprite.groupcollide(enemy_bullets,  indest_walls, True, False)
    pygame.sprite.groupcollide(player_bullets, dest_walls,   True, True)
    pygame.sprite.groupcollide(enemy_bullets,  dest_walls,   True, True)

    enemy_collided = pygame.sprite.spritecollideany(player, enemies)
    if enemy_collided:
        enemy_collided.kill()
        if player.has_armor:
            player.has_armor = False
        else:
            player.health = 0

    hits = pygame.sprite.groupcollide(enemies, player_bullets, False, True)
    for enemy, bullets in hits.items():
        for bullet in bullets:
            dmg = 2 if bullet.is_strong else 1
            if enemy.has_armor:
                enemy.has_armor = False
            else:
                enemy.health -= dmg
        if enemy.health <= 0:
            enemy.kill()

    enemy_bullets_hit = pygame.sprite.spritecollide(player, enemy_bullets, True)
    for bullet in enemy_bullets_hit:
        dmg = 2 if bullet.is_strong else 1
        if player.has_armor:
            player.has_armor = False
        else:
            player.health -= dmg

    if player.health <= 0:
        if player.extra_lives > 0:
            player.extra_lives = 0
            player.health = 2
            player.rect.center = (60, 60)
            return "PLAYING"
        return "DEAD"
    return "PLAYING"

def run_deathmatch(screen, clock, num_enemies):
    path = get_random_map()
    all_walls, dest_walls, indest_walls = load_map(path, TILE_SIZE)

    all_sprites    = pygame.sprite.Group(all_walls)
    player_bullets = pygame.sprite.Group()
    enemy_bullets  = pygame.sprite.Group()
    enemies        = pygame.sprite.Group()
    powerups       = pygame.sprite.Group()

    player = Tank(60, 60, (34, 139, 34))
    all_sprites.add(player)
    tanks_to_check = [player]

    for _ in range(num_enemies):
        sx, sy = get_safe_spawn_point(all_walls, tanks_to_check)
        e = EnemyTank(sx, sy)
        enemies.add(e)
        all_sprites.add(e)
        tanks_to_check.append(e)

    last_spawn = pygame.time.get_ticks()
    game_over  = False
    res_txt, res_col = "", (255, 255, 255)

    while True:
        screen.fill((20, 20, 20))
        now = pygame.time.get_ticks()

        for event in pygame.event.get():
            if event.type == pygame.QUIT: pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN and game_over and event.key == pygame.K_r:
                return

        if not game_over:
            #Power-up pojawia się co 2,5 sekundy (przyspieszony spawn w DM)
            if now - last_spawn > 2500:
                spawn_powerup(powerups, all_walls)
                last_spawn = now

            keys = pygame.key.get_pressed()
            dx = keys[pygame.K_RIGHT] - keys[pygame.K_LEFT]
            dy = keys[pygame.K_DOWN] - keys[pygame.K_UP]
            player.move(dx, dy, all_walls)

            if keys[pygame.K_SPACE]:
                player.shoot(player_bullets)

            for pw in pygame.sprite.spritecollide(player, powerups, True):
                if pw.type == 'strong': player.has_strong_shot = True
                elif pw.type == 'armor': player.has_armor = True
                elif pw.type == 'life':  player.extra_lives = 1

            for enemy in list(enemies):
                for pw in pygame.sprite.spritecollide(enemy, powerups, True):
                    if pw.type == 'strong': enemy.has_strong_shot = True
                    elif pw.type == 'armor': enemy.has_armor = True
                    elif pw.type == 'life':
                        #Jeśli wróg jest ranny – leczymy do pełna, inaczej dodatkowe życie
                        if enemy.health < enemy.max_health:
                            enemy.health = enemy.max_health
                        else:
                            enemy.extra_lives = 1

            #AI każdego bota dostaje listę pozostałych botów, żeby:
            #  1) nie wjeżdżać w nich podczas ruchu
            #  2) nie strzelać gdy sojusznik stoi w linii ognia
            enemy_list = list(enemies)
            for enemy in enemy_list:
                others = [e for e in enemy_list if e is not enemy]
                enemy.update_ai(player.rect, all_walls, dest_walls, enemy_bullets,
                                list(powerups),
                                player_bullets=player_bullets,
                                other_enemies=others)

            #Awaryjne rozdzielanie botów - na wypadek gdyby prewencja zawiodła
            #(np. po spawnie w pobliżu, po zniszczeniu ściany itp.)
            for i, e1 in enumerate(enemy_list):
                for e2 in enemy_list[i+1:]:
                    if not e1.alive() or not e2.alive():
                        continue
                    if e1.rect.colliderect(e2.rect):
                        edx = e1.rect.centerx - e2.rect.centerx
                        edy = e1.rect.centery  - e2.rect.centery
                        if abs(edx) >= abs(edy):
                            push = 2 if edx >= 0 else -2
                            e1.rect.x += push
                            e2.rect.x -= push
                        else:
                            push = 2 if edy >= 0 else -2
                            e1.rect.y += push
                            e2.rect.y -= push
                        if pygame.sprite.spritecollideany(e1, all_walls):
                            e1.rect.x -= push if abs(edx) >= abs(edy) else 0
                            e1.rect.y -= push if abs(edy)  > abs(edx) else 0
                        if pygame.sprite.spritecollideany(e2, all_walls):
                            e2.rect.x += push if abs(edx) >= abs(edy) else 0
                            e2.rect.y += push if abs(edy)  > abs(edx) else 0

            player_bullets.update()
            enemy_bullets.update()
            powerups.update()

            status = handle_combat(player, enemies, player_bullets, enemy_bullets, dest_walls, indest_walls, all_walls)
            p_dead = (status == "DEAD")
            e_dead = (len(enemies) == 0)
            if p_dead and e_dead:
                game_over, res_txt, res_col = True, "REMIS!",     (255, 165, 0)
            elif p_dead:
                game_over, res_txt, res_col = True, "PRZEGRANA!", (255, 0, 0)
            elif e_dead:
                game_over, res_txt, res_col = True, "WYGRANA!",   (0, 255, 0)

        all_sprites.draw(screen)
        powerups.draw(screen)
        player_bullets.draw(screen)
        enemy_bullets.draw(screen)
        draw_ui(screen, player)

        if not game_over:
            player.draw_bars(screen)
            for e in enemies: e.draw_bars(screen)
        else:
            draw_text(screen, res_txt, FONT_BIG,   400, 300, res_col)
            draw_text(screen, "R - Powrót", FONT_SMALL, 400, 380)

        pygame.display.flip()
        clock.tick(FPS)

def run_capture_point(screen, clock):
    path = get_random_map_cp()
    all_walls, d_walls, i_walls = load_map(path, TILE_SIZE)

    current_sector = 4
    capture_rect   = sector_to_rect(4)

    player = Tank(60, 60, (34, 139, 34))
    enemies = pygame.sprite.Group()
    p_bullets = pygame.sprite.Group()
    e_bullets = pygame.sprite.Group()
    powerups = pygame.sprite.Group()
    all_sprites = pygame.sprite.Group(all_walls, player)

    sx, sy = opposite_side_spawn(current_sector, all_walls, [player])
    first_enemy = EnemyTankCP(sx, sy)
    enemies.add(first_enemy)
    all_sprites.add(first_enemy)

    progress = 0.0
    capture_speed = 0.04

    used_sector_thresholds = set()
    spawned_at_pcts = set()

    total_time = 170 * 1000
    start_ticks = pygame.time.get_ticks()
    last_pu_spawn = pygame.time.get_ticks()

    game_over = False
    res_txt, res_col = "", (255, 255, 255)
    sector_announce_timer = 0

    while True:
        screen.fill((20, 20, 20))
        now = pygame.time.get_ticks()
        time_left = max(0, total_time - (now - start_ticks))

        for ev in pygame.event.get():
            if ev.type == pygame.QUIT: pygame.quit(); sys.exit()
            if ev.type == pygame.KEYDOWN and game_over and ev.key == pygame.K_r:
                return

        if not game_over:

            if abs(progress) >= 25:
                sect_thresh = int(progress / 25) * 25
                if sect_thresh != 0 and sect_thresh not in used_sector_thresholds:
                    used_sector_thresholds.add(sect_thresh)
                    other_sectors = [i for i in range(9) if i != current_sector]
                    current_sector = random.choice(other_sectors)
                    capture_rect = sector_to_rect(current_sector)
                    sector_announce_timer = 120

                    sx, sy = opposite_side_spawn(current_sector, all_walls, [player] + list(enemies))
                    new_e = EnemyTankCP(sx, sy)
                    enemies.add(new_e)
                    all_sprites.add(new_e)

            if progress >= 15:
                spawn_thresh = int(progress / 15) * 15
                if spawn_thresh not in spawned_at_pcts:
                    spawned_at_pcts.add(spawn_thresh)
                    sx, sy = opposite_side_spawn(current_sector, all_walls, [player] + list(enemies))
                    new_e = EnemyTankCP(sx, sy)
                    enemies.add(new_e)
                    all_sprites.add(new_e)

            if now - last_pu_spawn > 4000:
                spawn_powerup(powerups, all_walls)
                last_pu_spawn = now

            capture_zone = capture_rect.inflate(4, 4)
            player_in = capture_zone.colliderect(player.rect)
            enemy_in = any(capture_zone.colliderect(e.rect) for e in enemies)

            if player_in and not enemy_in:
                progress = min(100, progress + capture_speed)
            elif enemy_in and not player_in:
                progress = max(-100, progress - capture_speed)

            keys = pygame.key.get_pressed()
            dx = keys[pygame.K_RIGHT] - keys[pygame.K_LEFT]
            dy = keys[pygame.K_DOWN] - keys[pygame.K_UP]
            player.move(dx, dy, all_walls)

            if keys[pygame.K_SPACE]:
                player.shoot(p_bullets)

            for pw in pygame.sprite.spritecollide(player, powerups, True):
                if pw.type == 'strong': player.has_strong_shot = True
                elif pw.type == 'armor': player.has_armor = True
                elif pw.type == 'life':
                    player.extra_lives += 1
                    player.health = 2

            for enemy in list(enemies):
                for pw in pygame.sprite.spritecollide(enemy, powerups, True):
                    if pw.type == 'strong': enemy.has_strong_shot = True
                    elif pw.type == 'armor': enemy.has_armor = True
                    elif pw.type == 'life':
                        if enemy.health < enemy.max_health:
                            enemy.health = enemy.max_health
                        else:
                            enemy.extra_lives = 1

            for en in enemies:
                en.update_ai(capture_rect, player.rect, p_bullets, all_walls, d_walls, e_bullets,
                             indest_walls=i_walls, powerups=list(powerups))

            #Rozdzielamy boty które wjechały w siebie
            enemy_list = list(enemies)
            for i, e1 in enumerate(enemy_list):
                for e2 in enemy_list[i+1:]:
                    if not e1.alive() or not e2.alive():
                        continue
                    if e1.rect.colliderect(e2.rect):
                        edx = e1.rect.centerx - e2.rect.centerx
                        edy = e1.rect.centery  - e2.rect.centery
                        if abs(edx) >= abs(edy):
                            push = 2 if edx >= 0 else -2
                            e1.rect.x += push
                            e2.rect.x -= push
                        else:
                            push = 2 if edy >= 0 else -2
                            e1.rect.y += push
                            e2.rect.y -= push
                        if pygame.sprite.spritecollideany(e1, all_walls):
                            e1.rect.x -= push if abs(edx) >= abs(edy) else 0
                            e1.rect.y -= push if abs(edy)  > abs(edx) else 0
                        if pygame.sprite.spritecollideany(e2, all_walls):
                            e2.rect.x += push if abs(edx) >= abs(edy) else 0
                            e2.rect.y += push if abs(edy)  > abs(edx) else 0

            p_bullets.update()
            e_bullets.update()
            powerups.update()

            status = handle_combat(player, enemies, p_bullets, e_bullets, d_walls, i_walls, all_walls)

            if status == "DEAD":
                game_over, res_txt, res_col = True, "ZNISZCZONY!", (255, 0, 0)
            elif progress >= 100:
                game_over, res_txt, res_col = True, "PUNKT ZDOBYTY!", (0, 255, 0)
            elif progress <= -100:
                game_over, res_txt, res_col = True, "WRÓG PRZEJĄŁ PUNKT!", (255, 0, 0)
            elif time_left <= 0:
                game_over, res_txt, res_col = True, "KONIEC CZASU!", (255, 165, 0)

        if progress > 0:
            p_col, msg = (0, 255, 0), f"PRZEJMOWANIE: {int(progress)}%"
        elif progress < 0:
            p_col, msg = (255, 0, 0), f"WRÓG PRZEJMUJE: {abs(int(progress))}%"
        else:
            p_col, msg = (150, 150, 150), "PUNKT NEUTRALNY"

        for r in range(1, 3):
            pygame.draw.line(screen, (40, 40, 60), (0, r * ROW_H), (SCREEN_WIDTH, r * ROW_H), 1)
        for c in range(1, 3):
            pygame.draw.line(screen, (40, 40, 60), (c * COL_W, 0), (c * COL_W, SCREEN_HEIGHT), 1)

        if sector_announce_timer > 0:
            sector_announce_timer -= 1
            color = (255, 255, 0) if (sector_announce_timer // 6) % 2 == 0 else p_col
            pygame.draw.rect(screen, color, capture_rect, 4)
        else:
            pygame.draw.rect(screen, p_col, capture_rect, 3)

        all_sprites.draw(screen)
        p_bullets.draw(screen)
        e_bullets.draw(screen)
        powerups.draw(screen)
        draw_ui(screen, player)

        if not game_over:
            player.draw_bars(screen)
            for e in enemies: e.draw_bars(screen)

        m, s = divmod(time_left // 1000, 60)
        draw_text(screen, f"CZAS: {m:02d}:{s:02d}", FONT_MID,   400, 30)
        draw_text(screen, msg, FONT_SMALL, 400, 75, p_col)

        if sector_announce_timer > 0:
            ann_surf = FONT_MID.render("! PUNKT PRZENIESIONY !", True, (255, 255, 0))
            ann_surf.set_alpha(min(255, sector_announce_timer * 3))
            screen.blit(ann_surf, ann_surf.get_rect(center=(400, 120)))

        if game_over:
            draw_text(screen, res_txt, FONT_BIG, 400, 300, res_col)
            draw_text(screen, "R - POWRÓT DO MENU", FONT_SMALL, 400, 380)

        pygame.display.flip()
        clock.tick(FPS)

def main():
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Tank Battle 2D")
    clock  = pygame.time.Clock()
    state, selected, enemy_count = "MENU", 0, 1

    while True:
        screen.fill((30, 30, 50))

        if state == "MENU":
            draw_text(screen, "TANK BATTLE 2D", FONT_BIG, 400, 150, (255, 215, 0))
            for i, txt in enumerate(["DEATHMATCH", "CAPTURE POINT"]):
                color = (255, 255, 255) if selected == i else (100, 100, 100)
                draw_text(screen, txt, FONT_MID, 400, 300 + i * 70, color)

            for event in pygame.event.get():
                if event.type == pygame.QUIT: pygame.quit(); sys.exit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_UP:   selected = 0
                    if event.key == pygame.K_DOWN: selected = 1
                    if event.key == pygame.K_RETURN:
                        if selected == 0: state = "SETTINGS"
                        else:
                            run_capture_point(screen, clock)
                            state = "MENU"

        elif state == "SETTINGS":
            draw_text(screen, f"WROGOWIE: {enemy_count}", FONT_MID, 400, 250)

            slider_rect = pygame.Rect(250, 450, 300, 10)
            pygame.draw.rect(screen, (100, 100, 100), slider_rect)
            handle_x = slider_rect.left + (enemy_count - 1) * (slider_rect.width // 2)
            pygame.draw.rect(screen, (200, 200, 200), (handle_x - 10, slider_rect.centery - 15, 20, 30))
            draw_text(screen, "ENTER - START, ESC - POWRÓT", FONT_SMALL, 400, 520)

            for event in pygame.event.get():
                if event.type == pygame.QUIT: pygame.quit(); sys.exit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_LEFT:   enemy_count = max(1, enemy_count - 1)
                    if event.key == pygame.K_RIGHT:  enemy_count = min(3, enemy_count + 1)
                    if event.key == pygame.K_ESCAPE: state = "MENU"
                    if event.key == pygame.K_RETURN:
                        run_deathmatch(screen, clock, enemy_count)
                        state = "MENU"

        pygame.display.flip()
        clock.tick(FPS)

if __name__ == "__main__":
    main()