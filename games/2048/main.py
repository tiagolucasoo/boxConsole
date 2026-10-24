"""2048 em Pygame, feito para o BoxConsole.

Controles:
    Setas / W A S D ..... deslizar os números
    U ................... desfazer o último movimento
    R ................... novo jogo
    ESC ................. sair
"""

from __future__ import annotations

import random
import sys

import pygame

WIDTH, HEIGHT = 520, 640
GRID_SIZE = 4
CELL = 110
GAP = 10
BOARD_SIZE = GRID_SIZE * CELL + (GRID_SIZE - 1) * GAP
BOARD_X = (WIDTH - BOARD_SIZE) // 2
BOARD_Y = 110

BG = (250, 248, 240)
BOARD_BG = (187, 173, 160)
EMPTY = (205, 193, 180)
TEXT_DARK = (119, 110, 101)
TEXT_LIGHT = (249, 246, 242)
HUD = (24, 26, 34)

TILE_COLORS = {
    2: (238, 228, 218),
    4: (237, 224, 200),
    8: (242, 177, 121),
    16: (245, 149, 99),
    32: (246, 124, 95),
    64: (246, 94, 59),
    128: (237, 207, 114),
    256: (237, 204, 97),
    512: (237, 200, 80),
    1024: (237, 197, 63),
    2048: (237, 194, 46),
}


def draw_text(surface, text, size, color, center=None, topleft=None, bold=False):
    font = pygame.font.Font(None, size)
    font.set_bold(bold)
    image = font.render(text, True, color)
    rect = image.get_rect()
    if center:
        rect.center = center
    elif topleft:
        rect.topleft = topleft
    surface.blit(image, rect)
    return rect


class Game2048:
    def __init__(self) -> None:
        self.best = 0
        self.new_game()

    def new_game(self) -> None:
        self.board = [[0] * GRID_SIZE for _ in range(GRID_SIZE)]
        self.score = 0
        self.undo_board = None
        self.undo_score = 0
        self.won = False
        self.add_tile()
        self.add_tile()

    def empty_cells(self):
        return [(r, c) for r in range(GRID_SIZE) for c in range(GRID_SIZE) if self.board[r][c] == 0]

    def add_tile(self) -> None:
        cells = self.empty_cells()
        if not cells:
            return
        row, col = random.choice(cells)
        self.board[row][col] = 4 if random.random() < 0.1 else 2

    def compress(self, line: list[int]) -> tuple[list[int], int, bool]:
        values = [v for v in line if v != 0]
        result = []
        gained = 0
        index = 0
        while index < len(values):
            if index + 1 < len(values) and values[index] == values[index + 1]:
                merged = values[index] * 2
                result.append(merged)
                gained += merged
                if merged >= 2048:
                    self.won = True
                index += 2
            else:
                result.append(values[index])
                index += 1
        result += [0] * (GRID_SIZE - len(result))
        return result, gained, result != line

    def move(self, direction: str) -> None:
        before = [row[:] for row in self.board]
        before_score = self.score
        moved = False

        for i in range(GRID_SIZE):
            if direction == "left":
                line = self.board[i][:]
                new_line, gained, changed = self.compress(line)
                self.board[i] = new_line
            elif direction == "right":
                line = list(reversed(self.board[i]))
                new_line, gained, changed = self.compress(line)
                self.board[i] = list(reversed(new_line))
            elif direction == "up":
                line = [self.board[r][i] for r in range(GRID_SIZE)]
                new_line, gained, changed = self.compress(line)
                for r in range(GRID_SIZE):
                    self.board[r][i] = new_line[r]
            else:  # down
                line = list(reversed([self.board[r][i] for r in range(GRID_SIZE)]))
                new_line, gained, changed = self.compress(line)
                new_line = list(reversed(new_line))
                for r in range(GRID_SIZE):
                    self.board[r][i] = new_line[r]

            self.score += gained
            moved = moved or changed

        if moved:
            self.best = max(self.best, self.score)
            self.undo_board = before
            self.undo_score = before_score
            self.add_tile()

    def undo(self) -> None:
        if self.undo_board is None:
            return
        self.board = self.undo_board
        self.score = self.undo_score
        self.undo_board = None

    def can_move(self) -> bool:
        if self.empty_cells():
            return True
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                value = self.board[r][c]
                if c + 1 < GRID_SIZE and self.board[r][c + 1] == value:
                    return True
                if r + 1 < GRID_SIZE and self.board[r + 1][c] == value:
                    return True
        return False


def draw(game: Game2048, surface) -> None:
    surface.fill(BG)

    draw_text(surface, "2048", 54, HUD, topleft=(BOARD_X, 22), bold=True)
    draw_text(surface, f"Pontos: {game.score}", 26, TEXT_DARK, topleft=(BOARD_X + 170, 26))
    draw_text(surface, f"Recorde: {game.best}", 26, TEXT_DARK, topleft=(BOARD_X + 170, 54))

    pygame.draw.rect(surface, BOARD_BG, (BOARD_X, BOARD_Y, BOARD_SIZE, BOARD_SIZE), border_radius=8)

    for row in range(GRID_SIZE):
        for col in range(GRID_SIZE):
            x = BOARD_X + col * (CELL + GAP) + GAP
            y = BOARD_Y + row * (CELL + GAP) + GAP
            value = game.board[row][col]
            color = TILE_COLORS.get(value, (60, 58, 50)) if value else EMPTY
            rect = pygame.Rect(x, y, CELL, CELL)
            pygame.draw.rect(surface, color, rect, border_radius=6)
            if value:
                size = 48 if value < 100 else 40 if value < 1000 else 32
                text_color = TEXT_DARK if value <= 4 else TEXT_LIGHT
                draw_text(surface, str(value), size, text_color, center=rect.center, bold=True)

    if game.won:
        draw_text(surface, "Você chegou a 2048!", 30, (46, 160, 90), center=(WIDTH // 2, BOARD_Y + BOARD_SIZE + 26))
    if not game.can_move():
        draw_text(surface, "Sem movimentos! R para novo jogo", 28, (200, 70, 70), center=(WIDTH // 2, BOARD_Y + BOARD_SIZE + 26))

    draw_text(
        surface,
        "Setas/WASD mover   •   U desfazer   •   R novo   •   ESC sair",
        20,
        TEXT_DARK,
        center=(WIDTH // 2, HEIGHT - 16),
    )
    pygame.display.flip()


def main() -> None:
    pygame.init()
    pygame.display.set_caption("2048 — BoxConsole")
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    clock = pygame.time.Clock()
    game = Game2048()

    key_moves = {
        pygame.K_UP: "up",
        pygame.K_w: "up",
        pygame.K_DOWN: "down",
        pygame.K_s: "down",
        pygame.K_LEFT: "left",
        pygame.K_a: "left",
        pygame.K_RIGHT: "right",
        pygame.K_d: "right",
    }

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    return
                if event.key == pygame.K_r:
                    game.new_game()
                elif event.key == pygame.K_u:
                    game.undo()
                elif event.key in key_moves:
                    game.move(key_moves[event.key])

        draw(game, screen)
        clock.tick(30)


if __name__ == "__main__":
    main()
