import pygame

class PowerUp(pygame.sprite.Sprite):
    def __init__(self, x, y, p_type):
        super().__init__()
        self.type = p_type
        self.spawn_time = pygame.time.get_ticks()

        #Power-upy
        colors = {
            'strong': (255, 0, 0),  # czerwony silny strzał
            'armor':  (0, 0, 255),  # niebieski tymczasowy pancerz
            'life':   (0, 255, 0),  # zielony dodatkowe życie
        }

        self.image = pygame.Surface((25, 25))
        self.image.fill(colors.get(p_type, (255, 255, 255)))
        self.rect = self.image.get_rect(center=(x, y))

    def update(self):
        if pygame.time.get_ticks() - self.spawn_time > 15000:
            self.kill()