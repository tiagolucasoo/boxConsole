"""Breakout em Pygame, feito para o BoxConsole.

Controles:
    A / D ou Esquerda / Direita ..... mover a raquete
    Espaço / Enter .................. lançar a bola
    R ............................... reiniciar
    ESC ............................. sair
"""

from __future__ import annotations

import random
import sys

import pygame

WIDTH, HEIGHT = 800, 600
# Movimento por frame: 60 FPS preserva a velocidade original.
FPS = 60
PADDLE_W, PADDLE_H = 120, 16
BALL_SIZE = 14
BRICK_ROWS = 6
BRICK_COLS = 10
BRICK_W = WIDTH // BRICK_COLS
BRICK_H = 26
TOP_OFFSET = 70

BG = (16, 18, 26)
FG = (240, 244, 255)
MUTED = (130, 136, 152)
PADDLE_COLOR = (90, 200, 255)
BALL_COLOR = (255, 220, 120)
ROW_COLORS = [
    (255, 92, 92),
    (255, 150, 80),
    (255, 214, 90),
    (120, 220, 120),
    (90, 200, 255),
    (190, 130, 255),
]


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


def draw_text(surface, text, size, color, center=None, topleft=None, bold=False):
    key = (str(text), size, tuple(color), bool(bold))
    image = _TEXT_CACHE.get(key)
    if image is None:
        image = _get_font(size, bold).render(str(text), True, color)
        if len(_TEXT_CACHE) > 128:
            _TEXT_CACHE.clear()
        _TEXT_CACHE[key] = image
    rect = image.get_rect()
    if center:
        rect.center = center
    elif topleft:
        rect.topleft = topleft
    surface.blit(image, rect)
    return rect


class Breakout:
    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.paddle = pygame.Rect(WIDTH // 2 - PADDLE_W // 2, HEIGHT - 50, PADDLE_W, PADDLE_H)
        self.ball = pygame.Rect(0, 0, BALL_SIZE, BALL_SIZE)
        self.ball_attached = True
        self.score = 0
        self.lives = 3
        self.message = "Espaço / Enter para lançar"
        self.bricks = []
        for row in range(BRICK_ROWS):
            for col in range(BRICK_COLS):
                rect = pygame.Rect(col * BRICK_W + 2, TOP_OFFSET + row * BRICK_H, BRICK_W - 4, BRICK_H - 4)
                self.bricks.append([rect, ROW_COLORS[row % len(ROW_COLORS)]])
        self.center_ball()

    def center_ball(self) -> None:
        self.ball.center = (self.paddle.centerx, self.paddle.top - BALL_SIZE)

    def launch(self) -> None:
        if not self.ball_attached:
            return
        self.ball_attached = False
        self.vx = random.choice([-4, -3, 3, 4])
        self.vy = -6

    def update(self, keys) -> None:
        speed = 8
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.paddle.x -= speed
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.paddle.x += speed
        self.paddle.x = max(0, min(WIDTH - self.paddle.width, self.paddle.x))

        if self.ball_attached:
            self.center_ball()
            return

        self.ball.x += self.vx
        self.ball.y += self.vy

        if self.ball.left <= 0 or self.ball.right >= WIDTH:
            self.vx *= -1
            self.ball.x = max(0, min(WIDTH - self.ball.width, self.ball.x))
        if self.ball.top <= 0:
            self.vy *= -1
            self.ball.y = 0

        if self.ball.colliderect(self.paddle) and self.vy > 0:
            self.vy *= -1
            self.ball.bottom = self.paddle.top
            offset = (self.ball.centerx - self.paddle.centerx) / (self.paddle.width / 2)
            self.vx = int(6 * offset) or (3 if self.vx >= 0 else -3)

        for brick in self.bricks[:]:
            if self.ball.colliderect(brick[0]):
                self.bricks.remove(brick)
                self.score += 1
                self.vy *= -1
                break

        if self.ball.top > HEIGHT:
            self.lives -= 1
            self.ball_attached = True
            self.center_ball()
            if self.lives <= 0:
                self.message = f"Você perdeu! Pontos: {self.score} — R para reiniciar"
            else:
                self.message = "Bola perdida! Espaço / Enter para lançar"

        if not self.bricks:
            self.message = f"Você venceu! Pontos: {self.score} — R para reiniciar"


def draw(game: Breakout, surface) -> None:
    surface.fill(BG)

    for rect, color in game.bricks:
        pygame.draw.rect(surface, color, rect, border_radius=5)

    pygame.draw.rect(surface, PADDLE_COLOR, game.paddle, border_radius=8)
    pygame.draw.circle(surface, BALL_COLOR, game.ball.center, BALL_SIZE // 2)

    draw_text(surface, f"Pontos: {game.score}", 28, FG, topleft=(20, 16), bold=True)
    draw_text(surface, f"Vidas: {game.lives}", 28, FG, topleft=(WIDTH - 130, 16), bold=True)

    if game.message:
        draw_text(surface, game.message, 26, FG, center=(WIDTH // 2, HEIGHT - 80))

    draw_text(
        surface,
        "A/D ou ←/→ mover   •   Espaço/Enter lançar   •   R reiniciar   •   ESC sair",
        20,
        MUTED,
        center=(WIDTH // 2, HEIGHT - 18),
    )
    pygame.display.flip()


def main() -> None:
    pygame.init()
    pygame.display.set_caption("Breakout — BoxConsole")
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    clock = pygame.time.Clock()
    game = Breakout()

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
                    game.reset()
                if event.key in (pygame.K_SPACE, pygame.K_RETURN):
                    game.launch()

        game.update(pygame.key.get_pressed())
        draw(game, screen)
        clock.tick(FPS)


if __name__ == "__main__":
    main()
