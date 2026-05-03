import pygame

class Bullet(pygame.sprite.Sprite):
    def __init__(self, x, y, direction):
        super().__init__()
        #Pocisk to mały żółty kwadrat 10x10
        self.image = pygame.Surface((10, 10))
        self.image.fill((255, 255, 0))
        self.rect = self.image.get_rect(center=(x, y))
        self.direction = direction  #wektor kierunku np. (1,0) = prawo
        self.speed = 7

    def update(self):
        #Przesuwamy pocisk o wektor kierunku razy prędkość
        self.rect.x += self.direction[0] * self.speed
        self.rect.y += self.direction[1] * self.speed

        #Usuwamy pocisk gdy wyleci poza ekran
        if not pygame.display.get_surface().get_rect().colliderect(self.rect):
            self.kill()