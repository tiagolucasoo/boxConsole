#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pac-Man em Pygame para o BoxConsole.

Mantém o mapa, os quatro fantasmas, as estratégias de perseguição, a
pontuação, o cronômetro e as dificuldades da versão de terminal. A diferença
é que agora o jogo desenha em uma superfície Pygame e roda embutido no
launcher, sem precisar abrir um terminal externo.

A versão antiga continua em ``main.py`` e pode ser executada diretamente.
"""

from __future__ import annotations

import math
import time

import pygame

import strategy
from utilidades import mapa_original

# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------

WIDTH, HEIGHT = 960, 540
TILE = 16
LEFT_COL = 2  # as duas primeiras colunas do mapa são os rótulos A, B, C...
BOARD_W = 54 * TILE
BOARD_H = 27 * TILE
BOARD_X = (WIDTH - BOARD_W) // 2
BOARD_Y = 78

BG = (5, 7, 18)
PANEL = (13, 17, 33)
PANEL_2 = (20, 26, 48)
BORDER = (48, 61, 94)
TEXT = (240, 244, 255)
MUTED = (151, 162, 188)
DOT = (255, 224, 170)
YELLOW = (255, 214, 64)
WALL_FILL = (16, 31, 86)
WALL_EDGE = (50, 112, 255)
GHOST_FLOOR = (12, 18, 38)
WHITE = (255, 255, 255)
RED = (255, 76, 96)

GHOST_COLORS = {
    "8": (255, 76, 96),
    "7": (72, 224, 238),
    "6": (91, 231, 123),
    "5": (235, 105, 222),
}
GHOST_CHARS = set(GHOST_COLORS)

DIFFICULTIES = [
    ("Fácil", "facil", 0.15),
    ("Médio", "medio", 0.10),
    ("Difícil", "dificil", 0.05),
]
DIFFICULTY_BY_KEY = {key: interval for _, key, interval in DIFFICULTIES}
DIFFICULTY_NAME = {key: name for name, key, _ in DIFFICULTIES}


# ---------------------------------------------------------------------------
# Texto
# ---------------------------------------------------------------------------

_font_cache: dict[tuple[int, bool], pygame.font.Font] = {}
_text_cache: dict[tuple, pygame.Surface] = {}


def get_font(size: int, bold: bool = False) -> pygame.font.Font:
    key = (size, bool(bold))
    font = _font_cache.get(key)
    if font is None:
        font = pygame.font.Font(None, size)
        font.set_bold(bool(bold))
        _font_cache[key] = font
    return font


def text_image(text: str, size: int, color, bold: bool = False) -> pygame.Surface:
    key = (str(text), size, tuple(color), bool(bold))
    image = _text_cache.get(key)
    if image is None:
        image = get_font(size, bold).render(str(text), True, color)
        if len(_text_cache) > 256:
            _text_cache.clear()
        _text_cache[key] = image
    return image


def draw_text(
    surface: pygame.Surface,
    text: str,
    size: int,
    color,
    pos=None,
    anchor: str = "topleft",
    bold: bool = False,
):
    image = text_image(str(text), size, color, bold)
    rect = image.get_rect()
    if pos is not None:
        setattr(rect, anchor, pos)
    surface.blit(image, rect)
    return rect


def format_time(seconds: float) -> str:
    total = max(0, int(seconds))
    return f"{total // 60:02d}:{total % 60:02d}"


# ---------------------------------------------------------------------------
# Jogo
# ---------------------------------------------------------------------------


class PacmanGame:
    def __init__(self, screen: pygame.Surface) -> None:
        self.screen = screen
        self.running = True
        self.state = "start"
        self.difficulty_index = 1
        self.difficulty = DIFFICULTIES[self.difficulty_index][1]
        self.tick_interval = DIFFICULTY_BY_KEY[self.difficulty]

        self.overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        self.overlay.fill((0, 0, 0, 195))

        self.board: pygame.Surface | None = None
        self.matrix: list[list[str]] = []
        self.ghosts: list[dict] = []
        self.px = self.py = 0
        self.prev_px = self.prev_py = 0
        self.pacman_dir = "right"
        self.buffered_direction: str | None = None

        self.score = 0
        self.food_left = 0
        self.start_time = time.time()
        self.final_score = 0
        self.final_time = "00:00"
        self.acc = 0.0
        self.anim_progress = 1.0
        self.pause_index = 0

        self.player_name = "JOGADOR"

    # ------------------------------------------------------------------
    # Estado
    # ------------------------------------------------------------------

    def reset(self, difficulty: str | None = None) -> None:
        if difficulty:
            self.difficulty = difficulty
        for index, (_, key, _) in enumerate(DIFFICULTIES):
            if key == self.difficulty:
                self.difficulty_index = index
                break
        self.tick_interval = DIFFICULTY_BY_KEY.get(self.difficulty, 0.10)

        self.matrix = [list(line) for line in mapa_original.strip().split("\n")]
        self.px = self.py = -1
        for y, row in enumerate(self.matrix):
            if "+" in row:
                self.py, self.px = y, row.index("+")
                break
        if self.px < 0 or self.py < 0:
            raise RuntimeError("Mapa do Pac-Man sem posição inicial '+'.")

        self.ghosts = []
        for char in ("8", "7", "6", "5"):
            for y, row in enumerate(self.matrix):
                for x, cell in enumerate(row):
                    if cell == char:
                        self.ghosts.append(
                            {
                                "y": y,
                                "x": x,
                                "char": char,
                                "deixou_para_tras": "*",
                                "prev_y": y,
                                "prev_x": x,
                            }
                        )

        self.food_left = sum(row.count(".") for row in self.matrix)
        self.score = 0
        self.start_time = time.time()
        self.final_score = 0
        self.final_time = "00:00"
        self.acc = 0.0
        self.anim_progress = 1.0
        self.buffered_direction = None
        self.pacman_dir = "right"
        self.prev_px, self.prev_py = self.px, self.py
        self._build_board()
        self.state = "playing"

    def _elapsed(self) -> float:
        return time.time() - self.start_time

    def _elapsed_text(self) -> str:
        return format_time(self._elapsed())

    def _sync_previous(self) -> None:
        self.prev_px, self.prev_py = self.px, self.py
        for ghost in self.ghosts:
            ghost["prev_x"], ghost["prev_y"] = ghost["x"], ghost["y"]

    # ------------------------------------------------------------------
    # Tabuleiro
    # ------------------------------------------------------------------

    def _build_board(self) -> None:
        board = pygame.Surface((BOARD_W, BOARD_H)).convert()
        board.fill(BG)
        for y, row in enumerate(self.matrix):
            for x in range(LEFT_COL, len(row)):
                cell = row[x]
                rect = pygame.Rect(
                    (x - LEFT_COL) * TILE,
                    y * TILE,
                    TILE,
                    TILE,
                )
                if cell == "#":
                    inner = rect.inflate(-1, -1)
                    pygame.draw.rect(board, WALL_FILL, inner, border_radius=4)
                    pygame.draw.rect(board, WALL_EDGE, inner, 1, border_radius=4)
                elif cell == ".":
                    pygame.draw.circle(
                        board,
                        DOT,
                        (rect.centerx, rect.centery),
                        2,
                    )
                elif cell == "*":
                    pygame.draw.rect(board, GHOST_FLOOR, rect)
        self.board = board

    def _erase_dot(self, x: int, y: int) -> None:
        if self.board is None:
            return
        pygame.draw.rect(
            self.board,
            BG,
            ((x - LEFT_COL) * TILE, y * TILE, TILE, TILE),
        )

    # ------------------------------------------------------------------
    # Entrada
    # ------------------------------------------------------------------

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type != pygame.KEYDOWN:
            return
        key = event.key

        if key == pygame.K_F12:
            self.running = False
            return

        if self.state == "start":
            if key == pygame.K_ESCAPE:
                self.running = False
            elif key in (pygame.K_UP, pygame.K_w):
                self.difficulty_index = (self.difficulty_index - 1) % 3
            elif key in (pygame.K_DOWN, pygame.K_s):
                self.difficulty_index = (self.difficulty_index + 1) % 3
            elif key in (pygame.K_1, pygame.K_KP1):
                self.difficulty_index = 0
            elif key in (pygame.K_2, pygame.K_KP2):
                self.difficulty_index = 1
            elif key in (pygame.K_3, pygame.K_KP3):
                self.difficulty_index = 2
            elif key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                self.reset(DIFFICULTIES[self.difficulty_index][1])

        elif self.state == "playing":
            if key in (pygame.K_ESCAPE, pygame.K_p):
                self._pause()
            elif key in (pygame.K_UP, pygame.K_w):
                self.buffered_direction = "up"
            elif key in (pygame.K_DOWN, pygame.K_s):
                self.buffered_direction = "down"
            elif key in (pygame.K_LEFT, pygame.K_a):
                self.buffered_direction = "left"
            elif key in (pygame.K_RIGHT, pygame.K_d):
                self.buffered_direction = "right"

        elif self.state == "paused":
            if key == pygame.K_ESCAPE:
                self._resume()
            elif key in (pygame.K_UP, pygame.K_w):
                self.pause_index = (self.pause_index - 1) % 4
            elif key in (pygame.K_DOWN, pygame.K_s):
                self.pause_index = (self.pause_index + 1) % 4
            elif key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                if self.pause_index == 0:
                    self._resume()
                elif self.pause_index == 1:
                    self.reset(self.difficulty)
                elif self.pause_index == 2:
                    self.state = "difficulty"
                else:
                    self.running = False

        elif self.state == "difficulty":
            if key == pygame.K_ESCAPE:
                self.state = "paused"
            elif key in (pygame.K_UP, pygame.K_w):
                self.difficulty_index = (self.difficulty_index - 1) % 3
            elif key in (pygame.K_DOWN, pygame.K_s):
                self.difficulty_index = (self.difficulty_index + 1) % 3
            elif key in (pygame.K_1, pygame.K_KP1):
                self.difficulty_index = 0
            elif key in (pygame.K_2, pygame.K_KP2):
                self.difficulty_index = 1
            elif key in (pygame.K_3, pygame.K_KP3):
                self.difficulty_index = 2
            elif key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                self.reset(DIFFICULTIES[self.difficulty_index][1])

        elif self.state in ("gameover", "victory"):
            if key == pygame.K_ESCAPE:
                self.running = False
            elif key in (pygame.K_r, pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                self.reset(self.difficulty)

    def _pause(self) -> None:
        self.state = "paused"
        self.pause_index = 0
        self.buffered_direction = None
        self._sync_previous()
        self.anim_progress = 1.0

    def _resume(self) -> None:
        self.state = "playing"
        self.acc = 0.0
        self.buffered_direction = None
        self._sync_previous()
        self.anim_progress = 1.0

    # ------------------------------------------------------------------
    # Lógica
    # ------------------------------------------------------------------

    def update(self, dt: float) -> None:
        if self.state != "playing":
            self.anim_progress = 1.0
            return

        # Evita um salto enorme depois de uma pausa/engasgo do sistema.
        self.acc += min(max(dt, 0.0), 0.25)
        steps = 0
        while self.acc >= self.tick_interval and steps < 4 and self.state == "playing":
            self.acc -= self.tick_interval
            self._step()
            steps += 1

        if steps >= 4 and self.acc > self.tick_interval:
            self.acc = self.tick_interval * 0.99
        if self.state == "playing":
            self.anim_progress = min(1.0, self.acc / self.tick_interval)
        else:
            self.anim_progress = 1.0

    def _read_direction(self) -> str | None:
        if self.buffered_direction:
            direction = self.buffered_direction
            self.buffered_direction = None
            return direction

        keys = pygame.key.get_pressed()
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            return "up"
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            return "down"
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            return "left"
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            return "right"
        return None

    def _step(self) -> None:
        self.prev_px, self.prev_py = self.px, self.py
        for ghost in self.ghosts:
            ghost["prev_x"], ghost["prev_y"] = ghost["x"], ghost["y"]

        # Os fantasmas se movem antes do Pac-Man, como na versão de terminal.
        for ghost in self.ghosts:
            char = ghost["char"]
            if char == "8":
                dy, dx = strategy.fantasma_blinky(
                    self.matrix, ghost, self.py, self.px
                )
            elif char == "7":
                dy, dx = strategy.fantasma_pinky(
                    self.matrix, ghost, self.py, self.px
                )
            elif char == "6":
                dy, dx = strategy.fantasma_inky(
                    self.matrix, ghost, self.py, self.px
                )
            else:
                dy, dx = strategy.fantasma_clyde(
                    self.matrix, ghost, self.py, self.px
                )

            next_y, next_x = ghost["y"] + dy, ghost["x"] + dx
            if next_y == self.py and next_x == self.px:
                self._end_game("gameover")
                return

            if not (0 <= next_y < len(self.matrix) and 0 <= next_x < len(self.matrix[0])):
                continue
            if self.matrix[next_y][next_x] not in ("#", "8", "7", "6", "5"):
                self.matrix[ghost["y"]][ghost["x"]] = ghost["deixou_para_tras"]
                ghost["deixou_para_tras"] = self.matrix[next_y][next_x]
                ghost["y"], ghost["x"] = next_y, next_x
                self.matrix[next_y][next_x] = char

        direction = self._read_direction()
        if direction:
            self.pacman_dir = direction
            dx, dy = {
                "up": (0, -1),
                "down": (0, 1),
                "left": (-1, 0),
                "right": (1, 0),
            }[direction]
            next_y, next_x = self.py + dy, self.px + dx
            if (
                0 <= next_y < len(self.matrix)
                and 0 <= next_x < len(self.matrix[0])
                and self.matrix[next_y][next_x] != "#"
            ):
                destination = self.matrix[next_y][next_x]
                if destination == ".":
                    self.score += 10
                    self.food_left -= 1
                    self._erase_dot(next_x, next_y)
                elif destination in GHOST_CHARS:
                    self._end_game("gameover")
                    return

                self.matrix[self.py][self.px] = " "
                self.py, self.px = next_y, next_x
                self.matrix[self.py][self.px] = "+"

                if self.food_left <= 0:
                    self._end_game("victory")
                    return

    def _end_game(self, state: str) -> None:
        self.state = state
        self.final_score = self.score
        self.final_time = self._elapsed_text()
        self._sync_previous()
        self.anim_progress = 1.0
        self.buffered_direction = None

    # ------------------------------------------------------------------
    # Desenho
    # ------------------------------------------------------------------

    def draw(self) -> None:
        if self.state == "start":
            self._draw_start()
            return

        self._draw_game()
        if self.state == "paused":
            self._draw_pause()
        elif self.state == "difficulty":
            self._draw_difficulty()
        elif self.state in ("gameover", "victory"):
            self._draw_end()

    def _cell_center(self, x: float, y: float) -> tuple[int, int]:
        return (
            int(BOARD_X + (x - LEFT_COL + 0.5) * TILE),
            int(BOARD_Y + (y + 0.5) * TILE),
        )

    def _draw_game(self) -> None:
        self.screen.fill(BG)
        draw_text(self.screen, "PAC-MAN", 28, YELLOW, (BOARD_X, 10), bold=True)
        draw_text(
            self.screen,
            f"{self.score:06d}",
            28,
            TEXT,
            (WIDTH // 2, 24),
            anchor="center",
            bold=True,
        )
        draw_text(
            self.screen,
            self._elapsed_text(),
            22,
            (92, 218, 240),
            (WIDTH - BOARD_X, 16),
            anchor="topright",
            bold=True,
        )
        draw_text(
            self.screen,
            f"Dificuldade: {DIFFICULTY_NAME.get(self.difficulty, 'Médio')}",
            17,
            MUTED,
            (BOARD_X, 48),
        )
        draw_text(
            self.screen,
            f"Restam: {self.food_left}",
            17,
            MUTED,
            (WIDTH - BOARD_X, 48),
            anchor="topright",
        )

        if self.board is not None:
            self.screen.blit(self.board, (BOARD_X, BOARD_Y))

        progress = self.anim_progress if self.state == "playing" else 1.0
        for ghost in self.ghosts:
            gx = ghost["prev_x"] + (ghost["x"] - ghost["prev_x"]) * progress
            gy = ghost["prev_y"] + (ghost["y"] - ghost["prev_y"]) * progress
            cx, cy = self._cell_center(gx, gy)
            self._draw_ghost(cx, cy, GHOST_COLORS[ghost["char"]])

        pac_x = self.prev_px + (self.px - self.prev_px) * progress
        pac_y = self.prev_py + (self.py - self.prev_py) * progress
        cx, cy = self._cell_center(pac_x, pac_y)
        mouth = 0.24
        if self.state == "playing":
            mouth = 0.24 + 0.10 * (0.5 + 0.5 * math.sin(time.time() * 14))
        self._draw_pacman(cx, cy, 7, self.pacman_dir, mouth)

        draw_text(
            self.screen,
            "WASD/setas mover   ·   ESC pausa   ·   F12 sair",
            16,
            MUTED,
            (WIDTH // 2, HEIGHT - 18),
            anchor="center",
        )

    def _draw_pacman(
        self,
        cx: int,
        cy: int,
        radius: int,
        direction: str,
        mouth: float = 0.24,
    ) -> None:
        angle = {
            "right": 0.0,
            "down": math.pi / 2,
            "left": math.pi,
            "up": -math.pi / 2,
        }.get(direction, 0.0)
        pygame.draw.circle(self.screen, YELLOW, (cx, cy), radius)
        p1 = (
            cx + math.cos(angle - mouth) * (radius + 2),
            cy + math.sin(angle - mouth) * (radius + 2),
        )
        p2 = (
            cx + math.cos(angle + mouth) * (radius + 2),
            cy + math.sin(angle + mouth) * (radius + 2),
        )
        pygame.draw.polygon(self.screen, BG, [(cx, cy), p1, p2])

    def _draw_ghost(self, cx: int, cy: int, color) -> None:
        radius = 7
        pygame.draw.circle(self.screen, color, (cx, cy - 1), radius)
        pygame.draw.rect(
            self.screen,
            color,
            (cx - radius, cy - 1, radius * 2, radius + 3),
        )
        pygame.draw.polygon(
            self.screen,
            color,
            [
                (cx - radius, cy + radius + 1),
                (cx - radius + 4, cy + radius - 2),
                (cx - radius + 8, cy + radius + 1),
                (cx, cy + radius - 2),
                (cx + 4, cy + radius + 1),
                (cx + 8, cy + radius - 2),
                (cx + radius, cy + radius + 1),
            ],
        )
        for eye_x in (cx - 3, cx + 3):
            pygame.draw.circle(self.screen, WHITE, (eye_x, cy - 2), 2)
            pygame.draw.circle(self.screen, (25, 42, 80), (eye_x, cy - 1), 1)

    def _draw_start(self) -> None:
        self.screen.fill(BG)
        draw_text(
            self.screen,
            "PAC-MAN",
            64,
            YELLOW,
            (WIDTH // 2, 86),
            anchor="center",
            bold=True,
        )
        draw_text(
            self.screen,
            "Recriação em Pygame · BoxConsole",
            20,
            MUTED,
            (WIDTH // 2, 132),
            anchor="center",
        )

        self._draw_pacman(WIDTH // 2 - 96, 205, 18, "right", 0.28)
        for index, color in enumerate(GHOST_COLORS.values()):
            self._draw_ghost(WIDTH // 2 - 24 + index * 44, 205, color)

        box_w, box_h, gap = 190, 54, 18
        total = len(DIFFICULTIES) * box_w + (len(DIFFICULTIES) - 1) * gap
        start_x = (WIDTH - total) // 2
        for index, (name, key, _) in enumerate(DIFFICULTIES):
            rect = pygame.Rect(start_x + index * (box_w + gap), 300, box_w, box_h)
            selected = index == self.difficulty_index
            pygame.draw.rect(self.screen, PANEL_2 if selected else PANEL, rect, border_radius=10)
            pygame.draw.rect(
                self.screen,
                YELLOW if selected else BORDER,
                rect,
                2,
                border_radius=10,
            )
            draw_text(
                self.screen,
                name,
                25,
                YELLOW if selected else TEXT,
                rect.center,
                anchor="center",
                bold=selected,
            )

        draw_text(
            self.screen,
            "1/2/3 ou ↑↓ escolher   ·   ENTER começar",
            19,
            TEXT,
            (WIDTH // 2, 392),
            anchor="center",
        )
        draw_text(
            self.screen,
            "WASD/setas mover   ·   ESC pausa   ·   F12 sair",
            16,
            MUTED,
            (WIDTH // 2, HEIGHT - 30),
            anchor="center",
        )

    def _draw_pause(self) -> None:
        self.screen.blit(self.overlay, (0, 0))
        draw_text(
            self.screen,
            "PAUSADO",
            48,
            YELLOW,
            (WIDTH // 2, 142),
            anchor="center",
            bold=True,
        )
        options = ["Continuar", "Reiniciar", "Mudar dificuldade", "Sair para o menu"]
        for index, option in enumerate(options):
            selected = index == self.pause_index
            draw_text(
                self.screen,
                ("> " if selected else "  ") + option,
                26,
                YELLOW if selected else TEXT,
                (WIDTH // 2, 228 + index * 45),
                anchor="center",
                bold=selected,
            )
        draw_text(
            self.screen,
            "↑↓ escolher   ·   ENTER confirmar   ·   ESC continuar",
            16,
            MUTED,
            (WIDTH // 2, HEIGHT - 38),
            anchor="center",
        )

    def _draw_difficulty(self) -> None:
        self.screen.blit(self.overlay, (0, 0))
        draw_text(
            self.screen,
            "DIFICULDADE",
            38,
            YELLOW,
            (WIDTH // 2, 150),
            anchor="center",
            bold=True,
        )
        for index, (name, key, _) in enumerate(DIFFICULTIES):
            selected = index == self.difficulty_index
            draw_text(
                self.screen,
                ("> " if selected else "  ") + name,
                28,
                YELLOW if selected else TEXT,
                (WIDTH // 2, 230 + index * 52),
                anchor="center",
                bold=selected,
            )
        draw_text(
            self.screen,
            "ENTER aplicar e reiniciar   ·   ESC voltar",
            16,
            MUTED,
            (WIDTH // 2, HEIGHT - 38),
            anchor="center",
        )

    def _draw_end(self) -> None:
        self.screen.blit(self.overlay, (0, 0))
        victory = self.state == "victory"
        title = "VITÓRIA!" if victory else "GAME OVER"
        color = (110, 235, 145) if victory else RED
        draw_text(
            self.screen,
            title,
            54,
            color,
            (WIDTH // 2, 170),
            anchor="center",
            bold=True,
        )
        draw_text(
            self.screen,
            f"Pontuação: {self.final_score}",
            30,
            TEXT,
            (WIDTH // 2, 250),
            anchor="center",
            bold=True,
        )
        draw_text(
            self.screen,
            f"Tempo: {self.final_time}",
            24,
            MUTED,
            (WIDTH // 2, 292),
            anchor="center",
        )
        draw_text(
            self.screen,
            "R / ENTER reiniciar   ·   ESC sair",
            18,
            TEXT,
            (WIDTH // 2, 370),
            anchor="center",
        )


def main() -> None:
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Pac-Man - BoxConsole")
    clock = pygame.time.Clock()
    game = PacmanGame(screen)

    while game.running:
        dt = clock.tick(60) / 1000.0
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                game.running = False
                break
            game.handle_event(event)
        if not game.running:
            break
        game.update(dt)
        game.draw()
        pygame.display.flip()


if __name__ == "__main__":
    main()
