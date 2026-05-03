import pygame
from walls import DestructibleWall, IndestructibleWall

def load_map(filename, tile_size=40):
    #Tworzymy trzy grupy: wszystkie ściany, tylko zniszczalne, tylko niezniszczalne
    walls        = pygame.sprite.Group()
    dest_walls   = pygame.sprite.Group()
    indest_walls = pygame.sprite.Group()

    try:
        with open(filename, 'r') as file:
            for row_idx, line in enumerate(file):
                for col_idx, char in enumerate(line):
                    #Przeliczamy indeks kafelka na pozycję w pikselach
                    x = col_idx * tile_size
                    y = row_idx * tile_size

                    if char == '#':
                        #Niezniszczalna ściana szara
                        w = IndestructibleWall(x, y)
                        indest_walls.add(w)
                        walls.add(w)
                    elif char == 'X':
                        #Zniszczalna ściana brązowa => można ją zniszczyć
                        w = DestructibleWall(x, y)
                        dest_walls.add(w)
                        walls.add(w)

    except FileNotFoundError:
        print(f"Nie znaleziono pliku mapy: {filename}")

    return walls, dest_walls, indest_walls