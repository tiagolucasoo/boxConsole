import pygame.sprite

import configs
from layer import Layer


class Hint(pygame.sprite.Sprite):
    def __init__(self, lines, y, *groups):
        self._layer = Layer.UI
        self.lines = lines
        self.font = pygame.font.Font(None, 18)
        self.__render(y)

        super().__init__(*groups)

    def __render(self, y):
        rendered = [self.font.render(line, True, (255, 255, 255)) for line in self.lines]

        width = max(img.get_width() for img in rendered) + 20
        height = sum(img.get_height() for img in rendered) + 12

        self.image = pygame.surface.Surface((width, height), pygame.SRCALPHA)
        self.image.fill((0, 0, 0, 150))

        line_y = 6
        for img in rendered:
            self.image.blit(img, ((width - img.get_width()) // 2, line_y))
            line_y += img.get_height()

        self.rect = self.image.get_rect(center=(configs.SCREEN_WIDTH / 2, y))
