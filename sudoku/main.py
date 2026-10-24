"""Sudoku em Pygame, feito para o BoxConsole.

Controles:
    Setas / W A S D .... mover a seleção
    1-9 ................ preencher a célula
    0 / Backspace ...... apagar a célula
    N .................. novo jogo
    D .................. alternar dificuldade
    H .................. dica (revela a célula selecionada)
    ESC ................ sair

Mouse: clique na célula e nos botões da tela.
"""

from __future__ import annotations

import random
import sys
import time

import pygame

# ---------------------------------------------------------------------------
# Configuração
# ---------------------------------------------------------------------------

WINDOW_W = 660
WINDOW_H = 800
BOARD_SIZE = 540
CELL = BOARD_SIZE // 9
BOARD_X = (WINDOW_W - BOARD_SIZE) // 2
BOARD_Y = 90

PAD_Y = BOARD_Y + BOARD_SIZE + 22
PAD_H = 46
PAD_GAP = 4
PAD_W = (BOARD_SIZE - 8 * PAD_GAP) // 9

CTRL_Y = PAD_Y + PAD_H + 14
CTRL_H = 46
CTRL_GAP = 12

DIFFICULTIES = [
    ("Fácil", 40),
    ("Médio", 32),
    ("Difícil", 26),
]

# Cores
BG = (24, 26, 34)
BOARD_BG = (250, 250, 252)
FIXED_BG = (232, 234, 240)
SEL_BG = (255, 226, 130)
SAME_BG = (214, 228, 255)
LINE_THIN = (170, 176, 190)
LINE_THICK = (36, 38, 50)
NUM_GIVEN = (28, 30, 42)
NUM_PLAYER = (28, 96, 200)
NUM_WRONG = (208, 56, 56)
TITLE = (238, 240, 248)
MUTED = (150, 156, 172)
ACCENT = (96, 200, 255)
GOOD = (110, 220, 140)
BAD = (240, 120, 120)


# ---------------------------------------------------------------------------
# Geração de tabuleiro
# ---------------------------------------------------------------------------

def valid(board: list[list[int]], row: int, col: int, value: int) -> bool:
    for i in range(9):
        if board[row][i] == value or board[i][col] == value:
            return False
    box_row, box_col = (row // 3) * 3, (col // 3) * 3
    for r in range(box_row, box_row + 3):
        for c in range(box_col, box_col + 3):
            if board[r][c] == value:
                return False
    return True


def find_empty(board: list[list[int]]) -> tuple[int, int] | None:
    for r in range(9):
        for c in range(9):
            if board[r][c] == 0:
                return r, c
    return None


def find_empty_mrv(board: list[list[int]]):
    """Célula vazia com menos opções (deixa a contagem de soluções rápida)."""
    best = None
    best_count = 10
    for r in range(9):
        for c in range(9):
            if board[r][c] == 0:
                count = sum(1 for v in range(1, 10) if valid(board, r, c, v))
                if count < best_count:
                    best_count = count
                    best = (r, c)
                    if count == 0:
                        return best
    return best


def count_solutions(board: list[list[int]], limit: int = 2) -> int:
    cell = find_empty_mrv(board)
    if cell is None:
        return 1
    row, col = cell
    total = 0
    for value in range(1, 10):
        if valid(board, row, col, value):
            board[row][col] = value
            total += count_solutions(board, limit - total)
            board[row][col] = 0
            if total >= limit:
                break
    return total


def generate_solution() -> list[list[int]]:
    board = [[0] * 9 for _ in range(9)]

    def fill() -> bool:
        cell = find_empty_mrv(board)
        if cell is None:
            return True
        row, col = cell
        numbers = list(range(1, 10))
        random.shuffle(numbers)
        for value in numbers:
            if valid(board, row, col, value):
                board[row][col] = value
                if fill():
                    return True
                board[row][col] = 0
        return False

    fill()
    return board


def make_puzzle(givens: int) -> tuple[list[list[int]], list[list[int]]]:
    solution = generate_solution()
    puzzle = [row[:] for row in solution]
    cells = [(r, c) for r in range(9) for c in range(9)]
    random.shuffle(cells)
    to_remove = 81 - givens
    removed = 0
    for row, col in cells:
        if removed >= to_remove:
            break
        backup = puzzle[row][col]
        puzzle[row][col] = 0
        if count_solutions([r[:] for r in puzzle], 2) != 1:
            puzzle[row][col] = backup
        else:
            removed += 1
    return puzzle, solution


# ---------------------------------------------------------------------------
# Jogo
# ---------------------------------------------------------------------------

class Sudoku:
    def __init__(self) -> None:
        self.difficulty = 0
        self.running = True
        self.new_game()
        self.selected = (0, 0)
        self.message = ""
        self.message_color = TITLE
        self.message_until = 0.0

    # -- estado ----------------------------------------------------------
    def new_game(self) -> None:
        name, givens = DIFFICULTIES[self.difficulty]
        self.puzzle, self.solution = make_puzzle(givens)
        self.board = [row[:] for row in self.puzzle]
        self.fixed = [[self.puzzle[r][c] != 0 for c in range(9)] for r in range(9)]
        self.start_time = time.time()
        self.elapsed = 0.0
        self.solved = False
        self.hints = 0
        self.selected = self.first_empty()
        self.flash(f"Novo jogo: {name}", ACCENT, 2.0)

    def first_empty(self) -> tuple[int, int]:
        for r in range(9):
            for c in range(9):
                if self.board[r][c] == 0:
                    return r, c
        return 0, 0

    def flash(self, text: str, color=TITLE, seconds: float = 1.6) -> None:
        self.message = text
        self.message_color = color
        self.message_until = time.time() + seconds

    def current_message(self) -> tuple[str, tuple[int, int, int]]:
        if self.solved:
            return "Você venceu! Pressione N para outro jogo.", GOOD
        if time.time() < self.message_until:
            return self.message, self.message_color
        return "", TITLE

    def select(self, row: int, col: int) -> None:
        self.selected = (row % 9, col % 9)

    def move_selection(self, dr: int, dc: int) -> None:
        row, col = self.selected
        self.selected = ((row + dr) % 9, (col + dc) % 9)

    def place(self, value: int) -> None:
        if self.solved:
            return
        row, col = self.selected
        if self.fixed[row][col]:
            self.flash("Essa célula já veio pronta no desafio.", BAD, 1.2)
            return
        self.board[row][col] = value
        if value and value != self.solution[row][col]:
            self.flash("Número incorreto.", BAD, 1.2)
        self.check_win()

    def erase(self) -> None:
        if self.solved:
            return
        row, col = self.selected
        if self.fixed[row][col]:
            return
        self.board[row][col] = 0

    def hint(self) -> None:
        if self.solved:
            return
        row, col = self.selected
        if self.fixed[row][col] or self.board[row][col] == self.solution[row][col]:
            for r in range(9):
                for c in range(9):
                    if not self.fixed[r][c] and self.board[r][c] != self.solution[r][c]:
                        row, col = r, c
                        break
                else:
                    continue
                break
        if not self.fixed[row][col] and self.board[row][col] != self.solution[row][col]:
            self.board[row][col] = self.solution[row][col]
            self.fixed[row][col] = True
            self.hints += 1
            self.flash(f"Dica usada ({self.hints}).", ACCENT, 1.4)
        self.selected = (row, col)
        self.check_win()

    def check_win(self) -> None:
        if self.board == self.solution:
            self.solved = True
            self.elapsed = time.time() - self.start_time

    def cycle_difficulty(self) -> None:
        self.difficulty = (self.difficulty + 1) % len(DIFFICULTIES)
        self.new_game()

    def time_text(self) -> str:
        seconds = int(self.elapsed if self.solved else time.time() - self.start_time)
        return f"{seconds // 60:02d}:{seconds % 60:02d}"


# ---------------------------------------------------------------------------
# Desenho
# ---------------------------------------------------------------------------

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


def number_rects():
    rects = []
    x = BOARD_X
    for number in range(1, 10):
        rects.append((number, pygame.Rect(x, PAD_Y, PAD_W, PAD_H)))
        x += PAD_W + PAD_GAP
    return rects


def control_rects():
    labels = ["Apagar", "Novo", "Dificuldade", "Sair"]
    width = (BOARD_SIZE - 3 * CTRL_GAP) // 4
    rects = []
    x = BOARD_X
    for label in labels:
        rects.append((label, pygame.Rect(x, CTRL_Y, width, CTRL_H)))
        x += width + CTRL_GAP
    return rects


def draw(game: Sudoku, surface) -> None:
    surface.fill(BG)
    draw_text(
        surface,
        "SUDOKU",
        56,
        TITLE,
        center=(WINDOW_W // 2, 40),
        bold=True,
    )
    name, _ = DIFFICULTIES[game.difficulty]
    draw_text(surface, f"Dificuldade: {name}", 24, MUTED, topleft=(BOARD_X, 68))
    draw_text(surface, f"Tempo: {game.time_text()}", 24, MUTED, topleft=(BOARD_X + 230, 68))
    draw_text(surface, f"Dicas: {game.hints}", 24, MUTED, topleft=(BOARD_X + 400, 68))

    # fundo do tabuleiro
    pygame.draw.rect(surface, BOARD_BG, (BOARD_X, BOARD_Y, BOARD_SIZE, BOARD_SIZE))

    selected_value = game.board[game.selected[0]][game.selected[1]]
    for row in range(9):
        for col in range(9):
            rect = pygame.Rect(BOARD_X + col * CELL, BOARD_Y + row * CELL, CELL, CELL)
            value = game.board[row][col]
            if game.fixed[row][col]:
                pygame.draw.rect(surface, FIXED_BG, rect)
            if (row, col) == game.selected:
                pygame.draw.rect(surface, SEL_BG, rect)
            elif selected_value and value == selected_value:
                pygame.draw.rect(surface, SAME_BG, rect)

            if value:
                if game.fixed[row][col]:
                    color = NUM_GIVEN
                elif value != game.solution[row][col]:
                    color = NUM_WRONG
                else:
                    color = NUM_PLAYER
                draw_text(
                    surface,
                    str(value),
                    40,
                    color,
                    center=rect.center,
                    bold=game.fixed[row][col],
                )

    # linhas
    for i in range(10):
        thick = i % 3 == 0
        width = 3 if thick else 1
        color = LINE_THICK if thick else LINE_THIN
        x = BOARD_X + i * CELL
        y = BOARD_Y + i * CELL
        pygame.draw.line(surface, color, (x, BOARD_Y), (x, BOARD_Y + BOARD_SIZE), width)
        pygame.draw.line(surface, color, (BOARD_X, y), (BOARD_X + BOARD_SIZE, y), width)

    # teclado numérico
    for number, rect in number_rects():
        pygame.draw.rect(surface, (46, 50, 64), rect, border_radius=8)
        pygame.draw.rect(surface, ACCENT, rect, width=2, border_radius=8)
        draw_text(surface, str(number), 30, TITLE, center=rect.center, bold=True)

    # botões de controle
    for label, rect in control_rects():
        pygame.draw.rect(surface, (46, 50, 64), rect, border_radius=8)
        pygame.draw.rect(surface, (90, 96, 116), rect, width=2, border_radius=8)
        draw_text(surface, label, 24, TITLE, center=rect.center)

    # rodapé / mensagem
    message, color = game.current_message()
    if message:
        draw_text(surface, message, 26, color, center=(WINDOW_W // 2, CTRL_Y + CTRL_H + 28))

    pygame.display.flip()


# ---------------------------------------------------------------------------
# Loop principal
# ---------------------------------------------------------------------------

def main() -> None:
    pygame.init()
    pygame.display.set_caption("Sudoku — BoxConsole")
    screen = pygame.display.set_mode((WINDOW_W, WINDOW_H))
    clock = pygame.time.Clock()
    game = Sudoku()

    while game.running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                game.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    game.running = False
                elif event.key in (pygame.K_UP, pygame.K_w):
                    game.move_selection(-1, 0)
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    game.move_selection(1, 0)
                elif event.key in (pygame.K_LEFT, pygame.K_a):
                    game.move_selection(0, -1)
                elif event.key in (pygame.K_RIGHT, pygame.K_d):
                    game.move_selection(0, 1)
                elif event.key in (pygame.K_0, pygame.K_BACKSPACE, pygame.K_DELETE, pygame.K_KP0):
                    game.erase()
                elif event.key == pygame.K_n:
                    game.new_game()
                elif event.key == pygame.K_h:
                    game.hint()
                elif event.unicode in "123456789":
                    game.place(int(event.unicode))
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                pos = event.pos
                if pygame.Rect(BOARD_X, BOARD_Y, BOARD_SIZE, BOARD_SIZE).collidepoint(pos):
                    col = (pos[0] - BOARD_X) // CELL
                    row = (pos[1] - BOARD_Y) // CELL
                    game.select(row, col)
                    continue
                for number, rect in number_rects():
                    if rect.collidepoint(pos):
                        game.place(number)
                        break
                else:
                    for label, rect in control_rects():
                        if not rect.collidepoint(pos):
                            continue
                        if label == "Apagar":
                            game.erase()
                        elif label == "Novo":
                            game.new_game()
                        elif label == "Dificuldade":
                            game.cycle_difficulty()
                        elif label == "Sair":
                            game.running = False
                        break

        draw(game, screen)
        clock.tick(30)

    pygame.quit()


if __name__ == "__main__":
    main()
