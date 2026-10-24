"""Pong em Pygame, feito para o BoxConsole.

Controles:
    W / S ou Cima / Baixo ..... mover a raquete
    Espaço / Enter ............ sacar (servir)
    R ......................... reiniciar a partida
    ESC ....................... sair
"""

from __future__ import annotations

import random
import sys

import pygame

WIDTH, HEIGHT = 800, 600
FPS = 30
WIN_SCORE = 7

BG = (18, 20, 28)
FG = (240, 244, 255)
ACCENT = (90, 200, 255)
BALL = (255, 220, 120)
CPU = (255, 120, 160)
MUTED = (130, 136, 152)


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


class Paddle:
    def __init__(self, x: int) -> None:
        self.reset(x)

    def reset(self, x: int) -> None:
        self.rect = pygame.Rect(x, HEIGHT // 2 - 50, 14, 100)
        self.speed = 7

    def move(self, direction: int) -> None:
        self.rect.y += direction * self.speed
        self.rect.y = max(0, min(HEIGHT - self.rect.height, self.rect.y))

    def ai(self, ball: "Ball") -> None:
        if ball.rect.centery > self.rect.centery + 10:
            self.move(1)
        elif ball.rect.centery < self.rect.centery - 10:
            self.move(-1)


class Ball:
    def __init__(self) -> None:
        self.serve(random.choice([-1, 1]))

    def serve(self, direction: int = 1) -> None:
        self.rect = pygame.Rect(WIDTH // 2 - 8, HEIGHT // 2 - 8, 16, 16)
        self.vx = 5 * direction
        self.vy = random.choice([-4, -3, 3, 4])

    def update(self) -> None:
        self.rect.x += self.vx
        self.rect.y += self.vy
        if self.rect.top <= 0 or self.rect.bottom >= HEIGHT:
            self.vy *= -1
            self.rect.y = max(0, min(HEIGHT - self.rect.height, self.rect.y))


class Pong:
    def __init__(self) -> None:
        self.player = Paddle(30)
        self.cpu = Paddle(WIDTH - 30 - 14)
        self.ball = Ball()
        self.reset()

    def reset(self) -> None:
        self.player.reset(30)
        self.cpu.reset(WIDTH - 30 - 14)
        self.ball.serve(random.choice([-1, 1]))
        self.player_score = 0
        self.cpu_score = 0
        self.state = "serve"
        self.message = "Espaço / Enter para sacar"

    def point(self, winner: str) -> None:
        if winner == "player":
            self.player_score += 1
        else:
            self.cpu_score += 1
        if self.player_score >= WIN_SCORE or self.cpu_score >= WIN_SCORE:
            self.state = "over"
            if self.player_score > self.cpu_score:
                self.message = "Você venceu! R para jogar de novo"
            else:
                self.message = "CPU venceu! R para jogar de novo"
        else:
            self.state = "serve"
            self.message = "Ponto! Espaço / Enter para sacar"
            self.ball.serve(-1 if winner == "player" else 1)

    def update(self) -> None:
        if self.state == "play":
            self.ball.update()

            if self.ball.rect.colliderect(self.player.rect) and self.ball.vx < 0:
                self.ball.vx *= -1
                self.ball.rect.left = self.player.rect.right
            if self.ball.rect.colliderect(self.cpu.rect) and self.ball.vx > 0:
                self.ball.vx *= -1
                self.ball.rect.right = self.cpu.rect.left

            if self.ball.rect.right < 0:
                self.point("cpu")
            elif self.ball.rect.left > WIDTH:
                self.point("player")

            self.cpu.ai(self.ball)


def draw(game: Pong, surface) -> None:
    surface.fill(BG)

    # linha central pontilhada
    for y in range(0, HEIGHT, 28):
        pygame.draw.rect(surface, (60, 66, 84), pygame.Rect(WIDTH // 2 - 2, y, 4, 14))

    pygame.draw.rect(surface, ACCENT, game.player.rect, border_radius=4)
    pygame.draw.rect(surface, CPU, game.cpu.rect, border_radius=4)
    pygame.draw.circle(surface, BALL, game.ball.rect.center, 8)

    draw_text(surface, str(game.player_score), 60, FG, center=(WIDTH // 2 - 80, 50), bold=True)
    draw_text(surface, str(game.cpu_score), 60, FG, center=(WIDTH // 2 + 80, 50), bold=True)

    draw_text(surface, "VOCÊ", 22, MUTED, topleft=(30, 14))
    draw_text(surface, "CPU", 22, MUTED, topleft=(WIDTH - 80, 14))

    if game.state != "play":
        draw_text(surface, game.message, 28, FG, center=(WIDTH // 2, HEIGHT - 50))

    draw_text(
        surface,
        "W/S ou ↑/↓ mover   •   Espaço/Enter sacar   •   R reiniciar   •   ESC sair",
        20,
        MUTED,
        center=(WIDTH // 2, HEIGHT - 18),
    )
    pygame.display.flip()


def main() -> None:
    pygame.init()
    pygame.display.set_caption("Pong — BoxConsole")
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    clock = pygame.time.Clock()
    game = Pong()

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
                    if game.state == "serve":
                        game.state = "play"
                    elif game.state == "over":
                        game.reset()

        keys = pygame.key.get_pressed()
        if game.state == "play":
            if keys[pygame.K_UP] or keys[pygame.K_w]:
                game.player.move(-1)
            if keys[pygame.K_DOWN] or keys[pygame.K_s]:
                game.player.move(1)

        game.update()
        draw(game, screen)
        clock.tick(FPS)


if __name__ == "__main__":
    main()
