import pygame
from bullet import Bullet

class Tank(pygame.sprite.Sprite):

    def __init__(self, x, y, color):
        super().__init__()
        self.color = color

        self.base_image = pygame.Surface((34, 34), pygame.SRCALPHA)
        pygame.draw.rect(self.base_image, color, (6, 6, 22, 22))  # Korpus
        pygame.draw.rect(self.base_image, (40, 40, 40), (0, 2, 6, 30))  # Gąsienica L
        pygame.draw.rect(self.base_image, (40, 40, 40), (28, 2, 6, 30))  # Gąsienica P
        pygame.draw.rect(self.base_image, (60, 60, 60), (14, 0, 6, 16))  # Lufa
        self.image = self.base_image

        self.rect = pygame.Rect(0, 0, 20, 20)
        self.rect.center = (x, y)
        self.direction = (0, -1)
        self.speed = 2.5
        self.angles = {(0, -1): 0, (0, 1): 180, (-1, 0): 90, (1, 0): 270}

        self.max_health = self.health = 2
        self.last_shot = 0
        self.reload_time = 800
        self.has_strong_shot = self.has_armor = False
        self.extra_lives = 0

    def get_reload_progress(self):
        return min(1.0, (pygame.time.get_ticks() - self.last_shot) / self.reload_time)

    def draw_bars(self, screen):
        bx, top = self.rect.centerx - 15, self.rect.top
        #Pasek HP
        pygame.draw.rect(screen, (150, 0, 0), (bx, top - 20, 30, 4))
        pygame.draw.rect(screen, (0, 255, 0), (bx, top - 20, 30 * (self.health / self.max_health), 4))

        #Pasek przeładowania (tylko gdy trwa ładowanie)
        prog = self.get_reload_progress()
        if prog < 1.0:
            pygame.draw.rect(screen, (50, 50, 50), (bx, top - 12, 30, 4))
            pygame.draw.rect(screen, (255, 200, 0), (bx, top - 12, 30 * prog, 4))

        #Wizualne efekty power-upów
        if self.has_armor: pygame.draw.circle(screen, (0, 100, 255), self.rect.center, 18, 2)
        if self.has_strong_shot: pygame.draw.circle(screen, (255, 50, 0), self.rect.center, 21, 2)

    def rotate(self, new_dir):
        if new_dir != (0, 0):
            self.direction = new_dir
            self.image = pygame.transform.rotate(self.base_image, self.angles.get(new_dir, 0))
            self.rect = self.image.get_rect(center=self.rect.center)

    def move(self, dx, dy, walls=None):
        if dx == 0 and dy == 0:
            return

        SPEED_MAP = {
            (1, 0): 2.7,  # prawo
            (-1, 0): 2.7,  # lewo
            (0, 1): 2.7,  # dół
            (0, -1): 2.7,  # góra
            (1, 1): 2.7,  # prawo-dół
            (-1, 1): 2.7,  # lewo-dół
            (1, -1): 2.7,  # prawo-góra
            (-1, -1): 2.7,  # lewo-góra
        }

        speed = SPEED_MAP.get((dx, dy), self.speed)
        length = (dx ** 2 + dy ** 2) ** 0.5
        move_x = (dx / length) * speed
        move_y = (dy / length) * speed

        if dx != 0:
            self.rotate((dx, 0))
        else:
            self.rotate((0, dy))

        if walls is None:
            self.rect.x += move_x
            self.rect.y += move_y
            self.rect.clamp_ip(pygame.Rect(0, 0, 800, 600))
            return

        old_x = self.rect.x
        self.rect.x += move_x
        if pygame.sprite.spritecollide(self, walls, False):
            self.rect.x = old_x

        old_y = self.rect.y
        self.rect.y += move_y
        if pygame.sprite.spritecollide(self, walls, False):
            self.rect.y = old_y

        self.rect.clamp_ip(pygame.Rect(0, 0, 800, 600))

    def shoot(self, bullet_group):
        if self.get_reload_progress() >= 1.0:
            bx = self.rect.centerx + self.direction[0] * 18
            by = self.rect.centery + self.direction[1] * 18
            bullet_group.add(Bullet(bx, by, self.direction))
            self.last_shot = pygame.time.get_ticks()