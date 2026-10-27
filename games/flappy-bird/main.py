import pygame

import assets
import configs
from objects.background import Background
from objects.bird import Bird
from objects.column import Column
from objects.floor import Floor
from objects.gameover_message import GameOverMessage
from objects.gamestart_message import GameStartMessage
from objects.hint import Hint
from objects.score import Score

pygame.init()

display = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
screen = pygame.Surface((configs.SCREEN_WIDTH, configs.SCREEN_HEIGHT)).convert()

pygame.display.set_caption("Flappy Bird Game v1.0.2")

img = pygame.image.load('assets/icons/red_bird.png').convert_alpha()
pygame.display.set_icon(img)

pygame.mouse.set_visible(False)

# O tamanho da tela virtual não muda durante a partida. Calcula uma vez,
# em vez de fazer smoothscale de tela cheia a cada frame.
_display_width, _display_height = display.get_size()
_display_scale = min(
    _display_width / configs.SCREEN_WIDTH,
    _display_height / configs.SCREEN_HEIGHT,
)
_scaled_size = (
    int(configs.SCREEN_WIDTH * _display_scale),
    int(configs.SCREEN_HEIGHT * _display_scale),
)
_display_offset = (
    (_display_width - _scaled_size[0]) // 2,
    (_display_height - _scaled_size[1]) // 2,
)


_scaled_surface = None


def draw_display():
    global _scaled_surface
    # Nearest neighbor é muito mais rápido que smoothscale no ARMv7.
    if _scaled_size == (configs.SCREEN_WIDTH, configs.SCREEN_HEIGHT):
        frame = screen
    else:
        if _scaled_surface is None:
            _scaled_surface = pygame.Surface(_scaled_size).convert()
        pygame.transform.scale(screen, _scaled_size, _scaled_surface)
        frame = _scaled_surface

    display.fill(0)
    display.blit(frame, _display_offset)
    pygame.display.flip()


clock = pygame.time.Clock()
# Espaçamento em pixels, não em tempo. Em um H3 lento o timer de 1,5 s
# criava canos mais próximos que a largura de um cano (um "túnel" em cima
# do outro). Assim o espaçamento fica correto em qualquer FPS.
COLUMN_SPACING = 150
running = True
gameover = False
gamestarted = False

assets.load_sprites()
assets.load_audios()

sprites = pygame.sprite.LayeredUpdates()


def create_sprites():
    Background(0, sprites)
    Background(1, sprites)
    Floor(0, sprites)
    Floor(1, sprites)

    bird = Bird(sprites)
    game_start_message = GameStartMessage(sprites)
    score = Score(sprites)
    start_hint = Hint(["ESPAÇO: começar", "ESC: sair"], 90, sprites)

    return bird, game_start_message, score, start_hint


bird, game_start_message, score, start_hint = create_sprites()

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE and not gamestarted and not gameover:
                gamestarted = True
                game_start_message.kill()
                start_hint.kill()
                Column(sprites)
            if event.key == pygame.K_ESCAPE and gameover:
                gameover = False
                gamestarted = False
                sprites.empty()
                bird, game_start_message, score, start_hint = create_sprites()
            elif event.key == pygame.K_ESCAPE or (event.key == pygame.K_q and gameover):
                running = False

        if not gameover:
            bird.handle_event(event)

    screen.fill(0)

    sprites.draw(screen)

    if gamestarted and not gameover:
        sprites.update()
        columns = [sprite for sprite in sprites if isinstance(sprite, Column)]
        last_x = max((column.rect.x for column in columns), default=-9999)
        if last_x <= configs.SCREEN_WIDTH - COLUMN_SPACING:
            Column(sprites)

    if bird.check_collision(sprites) and not gameover:
        gameover = True
        gamestarted = False
        GameOverMessage(sprites)
        Hint(["ESC: voltar ao início", "Q: sair"], 330, sprites)
        assets.play_audio("hit")

    for sprite in sprites:
        if type(sprite) is Column and sprite.is_passed():
            score.value += 1
            assets.play_audio("point")

    draw_display()
    clock.tick(configs.FPS)

pygame.quit()
