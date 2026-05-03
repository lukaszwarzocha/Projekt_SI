import pygame

class Wall(pygame.sprite.Sprite):
    def __init__(self, x, y, color, destructible):
        super().__init__()
        #Każda ściana to kwadrat 40x40 pikseli (jeden kafelek mapy)
        self.image = pygame.Surface((40, 40))
        self.image.fill(color)
        self.rect = self.image.get_rect(topleft=(x, y))
        #Flaga informuje system kolizji czy pocisk może zniszczyć tę ścianę
        self.destructible = destructible

class DestructibleWall(Wall):
    def __init__(self, x, y):
        #Ściana zniszczalna oznaczona w pliku mapy jako 'X', kolor brązowy
        super().__init__(x, y, (139, 69, 19), True)

class IndestructibleWall(Wall):
    def __init__(self, x, y):
        #Ściana niezniszczalna oznaczona jako '#', kolor szary
        super().__init__(x, y, (80, 80, 80), False)