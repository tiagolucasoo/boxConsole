"""Bomberman em Pygame, feito para o BoxConsole.

Objetivo: destruir os tijolos, pegar melhorias e eliminar todos os inimigos
antes que as bombas acertem você.

Controles:
    Setas / W A S D ..... mover
    Espaço / Enter ...... soltar bomba
    R ................... reiniciar
    ESC ................. sair
"""

from __future__ import annotations

import math
import random
import sys

import pygame

WIDTH, HEIGHT = 800, 600
# O tabuleiro agora é pré-renderizado; 60 FPS deixa a movimentação suave.
FPS = 60
COLS, ROWS = 15, 11
TILE = 48
BOARD_X = (WIDTH - COLS * TILE) // 2
BOARD_Y = 64
HUD_H = 64

FLOOR = 0
WALL = 1
BRICK = 2

BG = (14, 16, 23)
GRID_A = (27, 30, 40)
GRID_B = (31, 34, 45)
WALL_COLOR = (78, 83, 101)
WALL_LIGHT = (106, 112, 134)
WALL_DARK = (52, 56, 70)
BRICK_COLOR = (158, 92, 54)
BRICK_DARK = (108, 60, 34)
BRICK_LIGHT = (190, 120, 74)
PLAYER_BODY = (74, 156, 255)
PLAYER_LIGHT = (224, 238, 255)
PLAYER_VISOR = (28, 36, 58)
ENEMY_BODY = (232, 82, 92)
ENEMY_DARK = (150, 40, 52)
EXIT_COLOR = (110, 230, 150)
TEXT = (240, 244, 255)
MUTED = (150, 158, 176)

BOMB_FUSE = 2.0
BOMB_RANGE = 2
EXPLOSION_TIME = 0.45
MAX_BOMBS = 4
MAX_RANGE = 6


def center_of(col: int, row: int) -> tuple[float, float]:
    return (
        BOARD_X + col * TILE + TILE / 2,
        BOARD_Y + row * TILE + TILE / 2,
    )


_FONT_CACHE = {}
_TEXT_CACHE = {}


def _get_font(size, bold):
    key = (size, bool(bold))
    font = _FONT_CACHE.get(key)
    if font is None:
        font = pygame.font.Font(None, size)
        font.set_bold(bool(bold))
        _FONT_CACHE[key] = font
    return font


def draw_text(
    surface,
    text,
    size,
    color,
    center=None,
    topleft=None,
    topright=None,
    bold=False,
):
    key = (str(text), size, tuple(color), bool(bold))
    image = _TEXT_CACHE.get(key)
    if image is None:
        image = _get_font(size, bold).render(str(text), True, color)
        if len(_TEXT_CACHE) > 160:
            _TEXT_CACHE.clear()
        _TEXT_CACHE[key] = image
    rect = image.get_rect()
    if center:
        rect.center = center
    elif topleft:
        rect.topleft = topleft
    elif topright:
        rect.topright = topright
    surface.blit(image, rect)
    return rect


class Bomb:
    def __init__(self, col: int, row: int, radius: int) -> None:
        self.col = col
        self.row = row
        self.radius = radius
        self.timer = BOMB_FUSE


class Explosion:
    def __init__(self, cells: set[tuple[int, int]]) -> None:
        self.cells = cells
        self.timer = EXPLOSION_TIME


class PowerUp:
    def __init__(self, col: int, row: int, kind: str) -> None:
        self.col = col
        self.row = row
        self.kind = kind


class Player:
    def __init__(self, col: int, row: int) -> None:
        self.spawn = (col, row)
        self.speed = 7.5
        self.alive = True
        self.invuln = 0.0
        self.reset_position()

    def reset_position(self) -> None:
        col, row = self.spawn
        self.col = col
        self.row = row
        self.tc = col
        self.tr = row
        self.moving = False
        self.t = 0.0
        self.px, self.py = center_of(col, row)
        self.facing = (0, 1)

    def update(self, dt: float, game: "Bomberman", keys) -> None:
        if not self.alive:
            return
        self.invuln = max(0.0, self.invuln - dt)

        if self.moving:
            self.t += dt * self.speed
            if self.t >= 1.0:
                self.col, self.row = self.tc, self.tr
                self.px, self.py = center_of(self.col, self.row)
                self.moving = False
                self.t = 0.0
                self.try_start(game, keys)
            else:
                x1, y1 = center_of(self.col, self.row)
                x2, y2 = center_of(self.tc, self.tr)
                self.px = x1 + (x2 - x1) * self.t
                self.py = y1 + (y2 - y1) * self.t
        else:
            self.try_start(game, keys)

    def try_start(self, game: "Bomberman", keys) -> None:
        direction = None
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            direction = (-1, 0)
        elif keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            direction = (1, 0)
        elif keys[pygame.K_UP] or keys[pygame.K_w]:
            direction = (0, -1)
        elif keys[pygame.K_DOWN] or keys[pygame.K_s]:
            direction = (0, 1)
        if direction is None:
            return

        dc, dr = direction
        nc, nr = self.col + dc, self.row + dr
        if game.can_walk(nc, nr):
            self.moving = True
            self.tc, self.tr = nc, nr
            self.t = 0.0
            self.facing = direction


class Enemy:
    def __init__(self, col: int, row: int) -> None:
        self.col = col
        self.row = row
        self.tc = col
        self.tr = row
        self.moving = False
        self.t = 0.0
        self.px, self.py = center_of(col, row)
        self.speed = 2.6
        self.direction = (0, 0)
        self.alive = True
        self.phase = random.random() * math.tau

    def cell(self) -> tuple[int, int]:
        if self.moving and self.t >= 0.5:
            return self.tc, self.tr
        return self.col, self.row

    def update(self, dt: float, game: "Bomberman") -> None:
        if not self.alive:
            return
        if self.moving:
            self.t += dt * self.speed
            if self.t >= 1.0:
                self.col, self.row = self.tc, self.tr
                self.px, self.py = center_of(self.col, self.row)
                self.moving = False
                self.t = 0.0
                self.choose_direction(game)
            else:
                x1, y1 = center_of(self.col, self.row)
                x2, y2 = center_of(self.tc, self.tr)
                self.px = x1 + (x2 - x1) * self.t
                self.py = y1 + (y2 - y1) * self.t
        else:
            self.choose_direction(game)

    def choose_direction(self, game: "Bomberman") -> None:
        options = []
        for direction in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            dc, dr = direction
            if game.can_walk(self.col + dc, self.row + dr):
                options.append(direction)

        reverse = (-self.direction[0], -self.direction[1])
        if len(options) > 1 and reverse in options:
            options.remove(reverse)

        if not options:
            direction = reverse if game.can_walk(self.col + reverse[0], self.row + reverse[1]) else None
        elif self.direction in options and random.random() < 0.55:
            direction = self.direction
        else:
            direction = random.choice(options)

        if direction is None:
            return

        dc, dr = direction
        nc, nr = self.col + dc, self.row + dr
        if game.can_walk(nc, nr):
            self.direction = direction
            self.moving = True
            self.tc, self.tr = nc, nr
            self.t = 0.0


class Bomberman:
    def __init__(self) -> None:
        self.elapsed = 0.0
        self._board_cache = None
        self.board_dirty = True
        self.reset()

    def reset(self) -> None:
        self.build_map()
        self.player = Player(1, 1)
        self.enemies = [
            Enemy(COLS - 2, ROWS - 2),
            Enemy(COLS - 2, 1),
            Enemy(1, ROWS - 2),
        ]
        self.bombs: list[Bomb] = []
        self.explosions: list[Explosion] = []
        self.powerups: list[PowerUp] = []
        self.score = 0
        self.lives = 3
        self.max_bombs = 1
        self.fire_range = BOMB_RANGE
        self.state = "playing"
        self.respawn_timer = 0.0
        self.elapsed = 0.0
        self.board_dirty = True

    def build_map(self) -> None:
        self.grid = [[FLOOR] * COLS for _ in range(ROWS)]
        for row in range(ROWS):
            for col in range(COLS):
                if (
                    col == 0
                    or row == 0
                    or col == COLS - 1
                    or row == ROWS - 1
                    or (col % 2 == 0 and row % 2 == 0)
                ):
                    self.grid[row][col] = WALL
                elif random.random() < 0.64:
                    self.grid[row][col] = BRICK

        # área inicial sempre livre
        for col, row in ((1, 1), (2, 1), (3, 1), (1, 2), (1, 3)):
            self.grid[row][col] = FLOOR

        # cantos dos inimigos livres, com pelo menos uma saída garantida
        for col, row in (
            (COLS - 2, ROWS - 2),
            (COLS - 2, 1),
            (1, ROWS - 2),
        ):
            self.grid[row][col] = FLOOR
            for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nc, nr = col + dc, row + dr
                if (
                    1 <= nc < COLS - 1
                    and 1 <= nr < ROWS - 1
                    and not (nc % 2 == 0 and nr % 2 == 0)
                ):
                    self.grid[nr][nc] = FLOOR

    def can_walk(self, col: int, row: int) -> bool:
        if not (0 <= col < COLS and 0 <= row < ROWS):
            return False
        if self.grid[row][col] != FLOOR:
            return False
        return not any(bomb.col == col and bomb.row == row for bomb in self.bombs)

    @staticmethod
    def entity_cell(entity) -> tuple[int, int]:
        if getattr(entity, "moving", False) and entity.t >= 0.5:
            return entity.tc, entity.tr
        return entity.col, entity.row

    def place_bomb(self) -> None:
        if self.state != "playing" or not self.player.alive:
            return
        col, row = self.entity_cell(self.player)
        if any(bomb.col == col and bomb.row == row for bomb in self.bombs):
            return
        if len(self.bombs) >= self.max_bombs:
            return
        self.bombs.append(Bomb(col, row, self.fire_range))

    def drop_powerup(self, col: int, row: int) -> None:
        if random.random() >= 0.30:
            return
        kind = "bomb" if random.random() < 0.5 else "fire"
        self.powerups.append(PowerUp(col, row, kind))

    def explode_bomb(self, bomb: Bomb) -> None:
        if bomb not in self.bombs:
            return

        queue = [bomb]
        cells: set[tuple[int, int]] = set()

        while queue:
            current = queue.pop(0)
            if current not in self.bombs:
                continue
            self.bombs.remove(current)
            cells.add((current.col, current.row))

            for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                for step in range(1, current.radius + 1):
                    col = current.col + dc * step
                    row = current.row + dr * step
                    if not (0 <= col < COLS and 0 <= row < ROWS):
                        break
                    if self.grid[row][col] == WALL:
                        break
                    cells.add((col, row))

                    if self.grid[row][col] == BRICK:
                        self.grid[row][col] = FLOOR
                        self.board_dirty = True
                        self.score += 10
                        self.drop_powerup(col, row)
                        break

                    for other in self.bombs:
                        if other is not current and other.col == col and other.row == row:
                            if other not in queue:
                                queue.append(other)
                            break

        self.explosions.append(Explosion(cells))

        for enemy in self.enemies[:]:
            if enemy.alive and self.entity_cell(enemy) in cells:
                enemy.alive = False
                self.enemies.remove(enemy)
                self.score += 100

        if self.player.alive and self.player.invuln <= 0 and self.entity_cell(self.player) in cells:
            self.kill_player()

        if not self.enemies and self.state == "playing":
            self.state = "won"

    def kill_player(self) -> None:
        if not self.player.alive or self.player.invuln > 0 or self.state != "playing":
            return
        self.player.alive = False
        self.lives -= 1
        if self.lives <= 0:
            self.state = "gameover"
        else:
            self.respawn_timer = 1.2

    def update(self, dt: float, keys) -> None:
        if self.state != "playing":
            return

        self.elapsed += dt

        if self.respawn_timer > 0:
            self.respawn_timer -= dt
            if self.respawn_timer <= 0:
                self.player.reset_position()
                self.player.alive = True
                self.player.invuln = 2.2

        if self.player.alive:
            self.player.update(dt, self, keys)

        for enemy in self.enemies[:]:
            enemy.update(dt, self)

        for bomb in self.bombs[:]:
            bomb.timer -= dt
            if bomb.timer <= 0:
                self.explode_bomb(bomb)

        for explosion in self.explosions[:]:
            explosion.timer -= dt
            if explosion.timer <= 0:
                self.explosions.remove(explosion)

        if self.player.alive:
            cell = self.entity_cell(self.player)
            for powerup in self.powerups[:]:
                if (powerup.col, powerup.row) == cell:
                    self.powerups.remove(powerup)
                    if powerup.kind == "bomb":
                        self.max_bombs = min(MAX_BOMBS, self.max_bombs + 1)
                    else:
                        self.fire_range = min(MAX_RANGE, self.fire_range + 1)
                    self.score += 25

            for enemy in self.enemies:
                if not enemy.alive:
                    continue
                distance = math.hypot(self.player.px - enemy.px, self.player.py - enemy.py)
                if distance < TILE * 0.62:
                    self.kill_player()
                    break


def draw_floor(surface) -> None:
    # Desenha no sistema de coordenadas do tabuleiro (0,0), não na tela.
    for row in range(ROWS):
        for col in range(COLS):
            rect = pygame.Rect(col * TILE, row * TILE, TILE, TILE)
            pygame.draw.rect(surface, GRID_A if (col + row) % 2 == 0 else GRID_B, rect)


def draw_walls(surface, game: Bomberman) -> None:
    for row in range(ROWS):
        for col in range(COLS):
            kind = game.grid[row][col]
            if kind == FLOOR:
                continue
            rect = pygame.Rect(col * TILE, row * TILE, TILE, TILE)
            if kind == WALL:
                pygame.draw.rect(surface, WALL_DARK, rect)
                inner = rect.inflate(-4, -4)
                pygame.draw.rect(surface, WALL_COLOR, inner, border_radius=4)
                pygame.draw.line(
                    surface, WALL_LIGHT, inner.topleft, (inner.right, inner.top), 2
                )
                pygame.draw.line(
                    surface, WALL_LIGHT, inner.topleft, (inner.left, inner.bottom), 2
                )
            else:
                pygame.draw.rect(surface, BRICK_DARK, rect)
                inner = rect.inflate(-3, -3)
                pygame.draw.rect(surface, BRICK_COLOR, inner, border_radius=3)
                for offset in (12, 24, 36):
                    pygame.draw.line(
                        surface,
                        BRICK_DARK,
                        (inner.left + 2, inner.top + offset),
                        (inner.right - 2, inner.top + offset),
                        2,
                    )
                pygame.draw.line(
                    surface,
                    BRICK_LIGHT,
                    (inner.centerx, inner.top + 9),
                    (inner.centerx, inner.top + 20),
                    2,
                )
                pygame.draw.line(
                    surface,
                    BRICK_LIGHT,
                    (inner.left + 12, inner.top + 26),
                    (inner.left + 12, inner.top + 36),
                    2,
                )
                pygame.draw.line(
                    surface,
                    BRICK_LIGHT,
                    (inner.right - 12, inner.top + 26),
                    (inner.right - 12, inner.top + 36),
                    2,
                )


def draw_powerups(surface, game: Bomberman, ticks: float) -> None:
    for powerup in game.powerups:
        x, y = center_of(powerup.col, powerup.row)
        x += math.sin(ticks * 4 + powerup.col) * 2
        y += math.sin(ticks * 3 + powerup.row) * 3
        size = 30
        rect = pygame.Rect(0, 0, size, size)
        rect.center = (x, y)
        color = (86, 210, 132) if powerup.kind == "bomb" else (255, 150, 64)
        pygame.draw.rect(surface, (18, 22, 30), rect.inflate(6, 6), border_radius=8)
        pygame.draw.rect(surface, color, rect, border_radius=7)
        letter = "B" if powerup.kind == "bomb" else "F"
        draw_text(surface, letter, 26, (18, 22, 30), center=rect.center, bold=True)


def draw_bombs(surface, game: Bomberman, ticks: float) -> None:
    for bomb in game.bombs:
        x, y = center_of(bomb.col, bomb.row)
        pulse = 1.0 + 0.07 * math.sin(ticks * 14 + bomb.col)
        radius = int(17 * pulse)
        pygame.draw.circle(surface, (10, 12, 18), (int(x), int(y)), radius + 3)
        pygame.draw.circle(surface, (34, 38, 50), (int(x), int(y)), radius)
        pygame.draw.circle(
            surface,
            (78, 84, 104),
            (int(x - radius * 0.32), int(y - radius * 0.32)),
            max(2, radius // 4),
        )
        pygame.draw.line(
            surface,
            (200, 170, 80),
            (int(x + radius * 0.4), int(y - radius * 0.7)),
            (int(x + radius * 0.9), int(y - radius * 1.25)),
            3,
        )
        spark = int(3 + 2 * abs(math.sin(ticks * 18 + bomb.row)))
        pygame.draw.circle(
            surface,
            (255, 224, 120),
            (int(x + radius * 0.95), int(y - radius * 1.3)),
            spark,
        )


def draw_explosions(surface, game: Bomberman, ticks: float) -> None:
    for explosion in game.explosions:
        fade = max(0.0, min(1.0, explosion.timer / EXPLOSION_TIME))
        for index, (col, row) in enumerate(explosion.cells):
            x, y = center_of(col, row)
            flicker = 0.9 + 0.1 * math.sin(ticks * 30 + index)
            outer = int(23 * flicker)
            inner = int(14 * flicker * fade)
            pygame.draw.rect(
                surface,
                (255, 112, 48),
                pygame.Rect(x - outer, y - outer, outer * 2, outer * 2),
                border_radius=9,
            )
            pygame.draw.rect(
                surface,
                (255, 206, 86),
                pygame.Rect(x - inner, y - inner, inner * 2, inner * 2),
                border_radius=7,
            )
            core = max(2, int(6 * fade))
            pygame.draw.circle(surface, (255, 248, 214), (int(x), int(y)), core)


def draw_player(surface, player: Player, ticks: float) -> None:
    if not player.alive:
        return
    if player.invuln > 0 and int(ticks * 12) % 2 == 0:
        return

    x, y = int(player.px), int(player.py)
    pygame.draw.ellipse(surface, (6, 8, 14), (x - 16, y + 15, 32, 9))
    pygame.draw.circle(surface, PLAYER_BODY, (x, y + 3), 16)
    pygame.draw.circle(surface, PLAYER_LIGHT, (x, y - 6), 13)
    pygame.draw.rect(surface, PLAYER_VISOR, (x - 9, y - 9, 18, 9), border_radius=4)
    pygame.draw.circle(surface, (120, 190, 255), (x + 6, y + 8), 4)
    pygame.draw.line(surface, (255, 214, 120), (x, y - 18), (x + 5, y - 25), 2)
    pygame.draw.circle(surface, (255, 224, 130), (x + 5, y - 25), 3)


def draw_enemies(surface, game: Bomberman, ticks: float) -> None:
    for enemy in game.enemies:
        if not enemy.alive:
            continue
        x, y = int(enemy.px), int(enemy.py)
        bob = math.sin(ticks * 6 + enemy.phase) * 2
        pygame.draw.ellipse(surface, (6, 8, 14), (x - 15, y + 14, 30, 8))
        pygame.draw.circle(surface, ENEMY_DARK, (x, int(y + 2 + bob)), 17)
        pygame.draw.circle(surface, ENEMY_BODY, (x, int(y + bob)), 15)
        pygame.draw.circle(surface, (255, 248, 240), (x - 5, int(y - 4 + bob)), 5)
        pygame.draw.circle(surface, (255, 248, 240), (x + 6, int(y - 4 + bob)), 5)
        pygame.draw.circle(surface, (24, 24, 32), (x - 4, int(y - 3 + bob)), 2)
        pygame.draw.circle(surface, (24, 24, 32), (x + 7, int(y - 3 + bob)), 2)
        pygame.draw.line(
            surface,
            ENEMY_DARK,
            (x - 7, int(y + 11 + bob)),
            (x - 11, int(y + 16 + bob)),
            3,
        )
        pygame.draw.line(
            surface,
            ENEMY_DARK,
            (x + 7, int(y + 11 + bob)),
            (x + 11, int(y + 16 + bob)),
            3,
        )


def draw_hud(surface, game: Bomberman) -> None:
    draw_text(surface, "BOMBERMAN", 38, (255, 178, 72), topleft=(BOARD_X, 14), bold=True)
    draw_text(
        surface,
        f"Pontos: {game.score}    Vidas: {game.lives}    Inimigos: {len(game.enemies)}    "
        f"Bombas: {len(game.bombs)}/{game.max_bombs}    Fogo: {game.fire_range}",
        22,
        TEXT,
        topright=(BOARD_X + COLS * TILE, 26),
        bold=True,
    )


def draw_overlay(surface, game: Bomberman) -> None:
    if game.state == "playing":
        if game.respawn_timer > 0:
            draw_text(
                surface,
                f"Você foi atingido! Vidas restantes: {game.lives}",
                30,
                (255, 150, 120),
                center=(BOARD_X + COLS * TILE // 2, BOARD_Y + ROWS * TILE // 2),
                bold=True,
            )
        return

    overlay = pygame.Surface((COLS * TILE, ROWS * TILE), pygame.SRCALPHA)
    overlay.fill((8, 10, 16, 190))
    surface.blit(overlay, (BOARD_X, BOARD_Y))

    if game.state == "won":
        title = "Você venceu!"
        color = EXIT_COLOR
    else:
        title = "Fim de jogo"
        color = (255, 110, 110)

    center_x = BOARD_X + COLS * TILE // 2
    center_y = BOARD_Y + ROWS * TILE // 2
    draw_text(surface, title, 54, color, center=(center_x, center_y - 30), bold=True)
    draw_text(
        surface,
        f"Pontos: {game.score}",
        30,
        TEXT,
        center=(center_x, center_y + 20),
        bold=True,
    )
    draw_text(
        surface,
        "R para jogar de novo    •    ESC para sair",
        24,
        MUTED,
        center=(center_x, center_y + 60),
    )


def draw(game: Bomberman, surface, ticks: float) -> None:
    surface.fill(BG)
    # Paredes e tijolos só mudam quando um tijolo é destruído. Montar o
    # tabuleiro uma vez e blitá-lo inteiro evita centenas de draw_rect por frame.
    if game.board_dirty or game._board_cache is None:
        board = pygame.Surface((COLS * TILE, ROWS * TILE)).convert()
        draw_floor(board)
        draw_walls(board, game)
        game._board_cache = board
        game.board_dirty = False
    surface.blit(game._board_cache, (BOARD_X, BOARD_Y))
    draw_powerups(surface, game, ticks)
    draw_bombs(surface, game, ticks)
    draw_explosions(surface, game, ticks)
    draw_enemies(surface, game, ticks)
    draw_player(surface, game.player, ticks)
    draw_hud(surface, game)
    draw_overlay(surface, game)
    pygame.display.flip()


def main() -> None:
    pygame.init()
    pygame.display.set_caption("Bomberman — BoxConsole")
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    clock = pygame.time.Clock()
    game = Bomberman()

    while True:
        dt = min(clock.tick(FPS) / 1000.0, 0.05)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    return
                if event.key == pygame.K_r:
                    game.reset()
                elif event.key in (pygame.K_SPACE, pygame.K_RETURN):
                    game.place_bomb()

        game.update(dt, pygame.key.get_pressed())
        draw(game, screen, pygame.time.get_ticks() / 1000.0)


if __name__ == "__main__":
    main()
