import pygame

class Bullet(pygame.sprite.Sprite):
    def __init__(self, x, y, direction, is_strong=False):
        super().__init__()

        self.is_strong = is_strong
        #Pocisk to mały żółty kwadrat 10x10 (czerwony/pomarańczowy jeśli silny)
        self.image = pygame.Surface((10, 10))
        if is_strong:
            self.image.fill((255, 50, 0))
        else:
            self.image.fill((255, 255, 0))
        self.rect = self.image.get_rect(center=(x, y))
        self.direction = direction
        self.speed = 7

    def update(self):
        #Przesuwamy pocisk o wektor kierunku razy prędkość
        self.rect.x += self.direction[0] * self.speed
        self.rect.y += self.direction[1] * self.speed

        if not pygame.display.get_surface().get_rect().colliderect(self.rect):
            self.kill()