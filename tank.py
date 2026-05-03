import pygame
from bullet import Bullet


class Tank(pygame.sprite.Sprite):
    def __init__(self, x, y, color):
        """Inicjalizacja czołgu - grafika, hitbox i statystyki bazowe"""
        super().__init__()
        self.color = color

        # --- Grafika (34x34) ---
        self.base_image = pygame.Surface((34, 34), pygame.SRCALPHA)
        pygame.draw.rect(self.base_image, color, (6, 6, 22, 22))  # Korpus
        pygame.draw.rect(self.base_image, (40, 40, 40), (0, 2, 6, 30))  # Gąsienica L
        pygame.draw.rect(self.base_image, (40, 40, 40), (28, 2, 6, 30))  # Gąsienica P
        pygame.draw.rect(self.base_image, (60, 60, 60), (14, 0, 6, 16))  # Lufa
        self.image = self.base_image

        # --- Fizyka i Ruch ---
        # Hitbox (20x20) mniejszy od grafiki ułatwia manewrowanie
        self.rect = pygame.Rect(0, 0, 20, 20)
        self.rect.center = (x, y)
        self.direction = (0, -1)
        self.speed = 2.5
        self.angles = {(0, -1): 0, (0, 1): 180, (-1, 0): 90, (1, 0): 270}

        # --- Statystyki ---
        self.max_health = self.health = 2
        self.last_shot = 0
        self.reload_time = 800
        self.has_strong_shot = self.has_armor = False
        self.extra_lives = 0

    def get_reload_progress(self):
        """Zwraca postęp przeładowania (0.0 - 1.0)"""
        return min(1.0, (pygame.time.get_ticks() - self.last_shot) / self.reload_time)

    def draw_bars(self, screen):
        """Rysuje paski HP, przeładowania oraz efekty specjalne (pancerz)"""
        bx, top = self.rect.centerx - 15, self.rect.top
        # Pasek HP
        pygame.draw.rect(screen, (150, 0, 0), (bx, top - 20, 30, 4))
        pygame.draw.rect(screen, (0, 255, 0), (bx, top - 20, 30 * (self.health / self.max_health), 4))

        # Pasek przeładowania (tylko gdy trwa ładowanie)
        prog = self.get_reload_progress()
        if prog < 1.0:
            pygame.draw.rect(screen, (50, 50, 50), (bx, top - 12, 30, 4))
            pygame.draw.rect(screen, (255, 200, 0), (bx, top - 12, 30 * prog, 4))

        # Wizualne efekty power-upów
        if self.has_armor: pygame.draw.circle(screen, (0, 100, 255), self.rect.center, 18, 2)
        if self.has_strong_shot: pygame.draw.circle(screen, (255, 50, 0), self.rect.center, 21, 2)

    def rotate(self, new_dir):
        """Obraca grafikę czołgu, zachowując środek hitboxa"""
        if new_dir != (0, 0):
            self.direction = new_dir
            self.image = pygame.transform.rotate(self.base_image, self.angles.get(new_dir, 0))
            self.rect = self.image.get_rect(center=self.rect.center)

    def move(self, dx, dy):
        """Porusza czołgiem z uwzględnieniem normalizacji prędkości na ukos"""
        if dx == 0 and dy == 0: return

        # Normalizacja prędkości dla ruchu ukośnego (Pitagoras)
        factor = 1.414 if dx != 0 and dy != 0 else 1.0
        self.rect.x += (dx * self.speed) / factor
        self.rect.y += (dy * self.speed) / factor

        self.rotate((dx, dy))

        # Szybka blokada czołgu w granicach ekranu (800x600)
        self.rect.clamp_ip(pygame.Rect(0, 0, 800, 600))

    def shoot(self, bullet_group):
        """Tworzy pocisk na wylocie lufy, jeśli czołg jest przeładowany"""
        if self.get_reload_progress() >= 1.0:
            bx = self.rect.centerx + self.direction[0] * 18
            by = self.rect.centery + self.direction[1] * 18
            bullet_group.add(Bullet(bx, by, self.direction))
            self.last_shot = pygame.time.get_ticks()