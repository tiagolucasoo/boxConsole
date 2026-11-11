import pygame as pg
import math
from collections import OrderedDict
from settings import *


class RayCasting:
    def __init__(self, game):
        self.game = game
        self.ray_casting_result = []
        self.objects_to_render = []
        self.textures = self.game.object_renderer.wall_textures
        # Cada quadro produz até NUM_RAYS escalas de uma coluna de parede.
        # Em ARM, reutilizar as combinações recentes reduz bastante alocações
        # temporárias sem manter um atlas enorme na RAM.
        self.wall_column_cache = OrderedDict()
        self.max_cached_columns = 512

    def get_wall_column(self, texture, source_y, source_height, source_x, output_height):
        """Retorna uma coluna de parede escalada, usando LRU pequeno."""
        source_y = max(0, int(source_y))
        source_height = max(1, int(source_height))
        source_x = max(0, min(TEXTURE_SIZE - SCALE, int(source_x)))
        # Dois pixels de precisão são suficientes nesta resolução e aumentam
        # muito a chance de reaproveitar a mesma escala entre raios.
        output_height = max(1, min(HEIGHT, int(output_height) // 2 * 2))
        key = (texture, source_x, source_y, source_height, output_height)
        cached = self.wall_column_cache.get(key)
        if cached is not None:
            self.wall_column_cache.move_to_end(key)
            return cached

        column = self.textures[texture].subsurface(
            source_x, source_y, SCALE, source_height
        )
        cached = pg.transform.scale(column, (SCALE, output_height))
        self.wall_column_cache[key] = cached
        if len(self.wall_column_cache) > self.max_cached_columns:
            self.wall_column_cache.popitem(last=False)
        return cached

    def get_objects_to_render(self):
        self.objects_to_render = []
        for ray, values in enumerate(self.ray_casting_result):
            depth, proj_height, texture, offset = values
            source_x = offset * (TEXTURE_SIZE - SCALE)

            if proj_height < HEIGHT:
                height = max(1, int(proj_height))
                wall_column = self.get_wall_column(
                    texture, 0, TEXTURE_SIZE, source_x, height
                )
                wall_pos = (ray * SCALE, HALF_HEIGHT - height // 2)
            else:
                texture_height = TEXTURE_SIZE * HEIGHT / proj_height
                source_height = max(1, int(texture_height))
                source_y = HALF_TEXTURE_SIZE - source_height // 2
                wall_column = self.get_wall_column(
                    texture, source_y, source_height, source_x, HEIGHT
                )
                wall_pos = (ray * SCALE, 0)

            self.objects_to_render.append((depth, wall_column, wall_pos))

    def ray_cast(self):
        self.ray_casting_result = []
        texture_vert, texture_hor = 1, 1
        ox, oy = self.game.player.pos
        x_map, y_map = self.game.player.map_pos

        ray_angle = self.game.player.angle - HALF_FOV + 0.0001
        for ray in range(NUM_RAYS):
            sin_a = math.sin(ray_angle)
            cos_a = math.cos(ray_angle)

            # horizontals
            y_hor, dy = (y_map + 1, 1) if sin_a > 0 else (y_map - 1e-6, -1)

            depth_hor = (y_hor - oy) / sin_a
            x_hor = ox + depth_hor * cos_a

            delta_depth = dy / sin_a
            dx = delta_depth * cos_a

            for i in range(MAX_DEPTH):
                tile_hor = int(x_hor), int(y_hor)
                if tile_hor in self.game.map.world_map:
                    texture_hor = self.game.map.world_map[tile_hor]
                    break
                x_hor += dx
                y_hor += dy
                depth_hor += delta_depth

            # verticals
            x_vert, dx = (x_map + 1, 1) if cos_a > 0 else (x_map - 1e-6, -1)

            depth_vert = (x_vert - ox) / cos_a
            y_vert = oy + depth_vert * sin_a

            delta_depth = dx / cos_a
            dy = delta_depth * sin_a

            for i in range(MAX_DEPTH):
                tile_vert = int(x_vert), int(y_vert)
                if tile_vert in self.game.map.world_map:
                    texture_vert = self.game.map.world_map[tile_vert]
                    break
                x_vert += dx
                y_vert += dy
                depth_vert += delta_depth

            # depth, texture offset
            if depth_vert < depth_hor:
                depth, texture = depth_vert, texture_vert
                y_vert %= 1
                offset = y_vert if cos_a > 0 else (1 - y_vert)
            else:
                depth, texture = depth_hor, texture_hor
                x_hor %= 1
                offset = (1 - x_hor) if sin_a > 0 else x_hor

            # remove fishbowl effect
            depth *= math.cos(self.game.player.angle - ray_angle)

            # projection
            proj_height = SCREEN_DIST / (depth + 0.0001)

            # ray casting result
            self.ray_casting_result.append((depth, proj_height, texture, offset))

            ray_angle += DELTA_ANGLE

    def update(self):
        self.ray_cast()
        self.get_objects_to_render()
