import pygame
from pygame import mixer
from pygame import font
import math
import os
import random
import sys
from fighter import Fighter
from characters import CHARACTERS, CHARACTER_BY_ID

# Helper Function for Bundled Assets
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        # When running from src directory, look in parent directory for assets
        if os.path.basename(os.getcwd()) == "src":
            base_path = os.path.abspath("..")
        else:
            base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

mixer.init()
pygame.init()

# Constants — resolução fixa e leve para o H3 (o host escala se precisar).
SCREEN_WIDTH = 960
SCREEN_HEIGHT = 540
FPS = 30
ROUND_OVER_COOLDOWN = 3000
# Os novos cenários têm o chão mais baixo que o antigo bambuzal.
COMBAT_FLOOR_Y = SCREEN_HEIGHT - 40

# Colors
RED = (255, 0, 0)
YELLOW = (255, 255, 0)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
BLUE = (0, 0, 255)
GREEN = (0, 255, 0)

# Paleta do menu: noite, madeira e luz de lanterna.
GOLD = (238, 190, 82)
GOLD_LIGHT = (255, 228, 154)
GOLD_DARK = (152, 108, 38)
CRIMSON = (204, 48, 58)
CRIMSON_DARK = (88, 14, 22)
STEEL = (198, 206, 220)
STEEL_DARK = (94, 104, 124)
PANEL = (8, 13, 22)

# Initialize Game Window
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.NOFRAME)
pygame.display.set_caption("Street Fighter")
clock = pygame.time.Clock()

# Load Assets
# O menu usa o telhado à noite (bg.jpg). O combate escolhe aleatoriamente
# entre fundo-1.jpg e fundo-2.jpg ao iniciar cada luta.
menu_image = pygame.image.load(resource_path("assets/images/bg.jpg")).convert()
victory_img = pygame.image.load(resource_path("assets/images/victory.png")).convert_alpha()
victory_img_big = pygame.transform.scale(
    victory_img, (victory_img.get_width() * 2, victory_img.get_height() * 2)
)

# Fonts
menu_font = pygame.font.Font(resource_path("assets/fonts/turok.ttf"), 50)
menu_font_title = pygame.font.Font(resource_path("assets/fonts/turok.ttf"), 100)
count_font = pygame.font.Font(resource_path("assets/fonts/turok.ttf"), 80)
score_font = pygame.font.Font(resource_path("assets/fonts/turok.ttf"), 30)
score_font_large = pygame.font.Font(resource_path("assets/fonts/turok.ttf"), 60)
controls_font = pygame.font.Font(resource_path("assets/fonts/turok.ttf"), 35)
small_font = pygame.font.Font(resource_path("assets/fonts/turok.ttf"), 25)
player_label_font = pygame.font.Font(resource_path("assets/fonts/turok.ttf"), 25)
countdown_font = pygame.font.Font(resource_path("assets/fonts/turok.ttf"), 100)

# Music and Sounds
pygame.mixer.music.load(resource_path("assets/audio/music.mp3"))
pygame.mixer.music.set_volume(0.5)
pygame.mixer.music.play(-1, 0.0, 5000)
sword_fx = pygame.mixer.Sound(resource_path("assets/audio/sword.wav"))
sword_fx.set_volume(0.5)
magic_fx = pygame.mixer.Sound(resource_path("assets/audio/magic.wav"))
magic_fx.set_volume(0.75)

# Game Variables
score = [0, 0]  # Player Scores: [P1, P2]


_text_cache = {}


def render_text(font, text, color):
    """Renderiza uma vez por combinação; evita font.render a cada frame."""
    key = (id(font), str(text), tuple(color))
    image = _text_cache.get(key)
    if image is None:
        image = font.render(str(text), True, color)
        if len(_text_cache) > 128:
            _text_cache.clear()
        _text_cache[key] = image
    return image


def draw_text(text, font, color, x, y):
    screen.blit(render_text(font, text, color), (x, y))


def cover_fit(image, size):
    """Escala a imagem cobrindo a tela inteira, sem distorcer."""
    iw, ih = image.get_size()
    scale = max(size[0] / iw, size[1] / ih)
    nw, nh = int(iw * scale + 0.5), int(ih * scale + 0.5)
    scaled = pygame.transform.smoothscale(image, (nw, nh))
    output = pygame.Surface(size).convert()
    output.blit(scaled, ((size[0] - nw) // 2, (size[1] - nh) // 2))
    return output


def build_combat_backgrounds():
    """Prepara os dois fundos de luta uma vez, já no tamanho da tela."""
    backgrounds = []
    for name in ("fundo-1.jpg", "fundo-2.jpg"):
        image = pygame.image.load(
            resource_path(os.path.join("assets", "images", name))
        ).convert()
        backgrounds.append(cover_fit(image, (SCREEN_WIDTH, SCREEN_HEIGHT)))
    return backgrounds


def build_menu_background():
    """Fundo noturno + painel central. Tudo calculado uma única vez."""
    base = cover_fit(menu_image, (SCREEN_WIDTH, SCREEN_HEIGHT))

    tint = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    tint.fill((3, 7, 16, 86))
    base.blit(tint, (0, 0))

    # Escurece topo e base para o título/legendas ficarem legíveis.
    gradient = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    for y in range(SCREEN_HEIGHT):
        if y < 170:
            alpha = int(190 * (1 - y / 170))
        elif y > 360:
            alpha = int(205 * ((y - 360) / (SCREEN_HEIGHT - 360)))
        else:
            alpha = 0
        if alpha:
            pygame.draw.line(gradient, (2, 5, 11, alpha), (0, y), (SCREEN_WIDTH, y))
    base.blit(gradient, (0, 0))

    vignette = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    for index in range(38):
        alpha = 3 + int(index * 1.5)
        inset = index * 3
        pygame.draw.rect(
            vignette,
            (0, 0, 0, alpha),
            (inset, inset, SCREEN_WIDTH - inset * 2, SCREEN_HEIGHT - inset * 2),
            3,
        )
    base.blit(vignette, (0, 0))

    glows = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    pygame.draw.circle(glows, (190, 45, 55, 36), (132, 420), 210)
    pygame.draw.circle(glows, (120, 74, 200, 32), (828, 408), 220)
    base.blit(glows, (0, 0))

    line_y = 157
    pygame.draw.line(base, GOLD_DARK, (SCREEN_WIDTH // 2 - 180, line_y), (SCREEN_WIDTH // 2 + 180, line_y), 1)
    pygame.draw.polygon(
        base,
        GOLD,
        [
            (SCREEN_WIDTH // 2, line_y - 4),
            (SCREEN_WIDTH // 2 + 4, line_y),
            (SCREEN_WIDTH // 2, line_y + 4),
            (SCREEN_WIDTH // 2 - 4, line_y),
        ],
    )
    return base


def build_menu_panel():
    """Painel de vidro atrás dos botões do menu principal."""
    panel = pygame.Surface((474, 324), pygame.SRCALPHA)
    for y in range(panel.get_height()):
        t = y / max(1, panel.get_height() - 1)
        color = (
            7 + int(3 * t),
            11 + int(3 * t),
            20 + int(4 * t),
            194,
        )
        pygame.draw.line(panel, color, (0, y), (panel.get_width(), y))
    pygame.draw.rect(
        panel, (GOLD[0], GOLD[1], GOLD[2], 46), panel.get_rect(), 1, border_radius=10
    )
    pygame.draw.line(
        panel,
        (GOLD[0], GOLD[1], GOLD[2], 92),
        (18, 1),
        (panel.get_width() - 18, 1),
        1,
    )
    return panel


_portrait_cache = {}


def get_character_portrait(character, max_size):
    """Recorta o frame de retrato do personagem, sem manter o PNG na memória."""
    key = (character["id"], max_size)
    cached = _portrait_cache.get(key)
    if cached is not None:
        return cached

    sheet = pygame.image.load(
        resource_path(os.path.join("assets", "images", character["sheet"]))
    ).convert_alpha()
    row, index = character["portrait"]
    rect = character["rows"][row][index]
    crop = sheet.subsurface(rect)
    width, height = crop.get_size()
    scale = min(max_size[0] / width, max_size[1] / height)
    size = (max(1, int(width * scale)), max(1, int(height * scale)))
    image = pygame.transform.scale(crop, size)
    _portrait_cache[key] = image
    return image


def _clean_frame(crop):
    """Remove fragmentos de poses vizinhas que encostam no recorte.

    As folhas novas são colagens: às vezes um pedaço da pose de cima fica
    dentro do retângulo de outra. Mantemos o corpo principal e os efeitos que
    estão na mesma faixa vertical (bola de fogo, bastão solto etc.).
    """
    width, height = crop.get_size()
    mask = pygame.mask.from_surface(crop)
    visited = bytearray(width * height)
    components = []

    for start_y in range(height):
        for start_x in range(width):
            start_index = start_y * width + start_x
            if visited[start_index] or not mask.get_at((start_x, start_y)):
                continue
            stack = [(start_x, start_y)]
            visited[start_index] = 1
            pixels = []
            min_x = max_x = start_x
            min_y = max_y = start_y
            while stack:
                x, y = stack.pop()
                pixels.append((x, y))
                min_x = min(min_x, x)
                max_x = max(max_x, x)
                min_y = min(min_y, y)
                max_y = max(max_y, y)
                for dy in (-1, 0, 1):
                    ny = y + dy
                    if ny < 0 or ny >= height:
                        continue
                    for dx in (-1, 0, 1):
                        if dx == 0 and dy == 0:
                            continue
                        nx = x + dx
                        if nx < 0 or nx >= width:
                            continue
                        index = ny * width + nx
                        if not visited[index] and mask.get_at((nx, ny)):
                            visited[index] = 1
                            stack.append((nx, ny))
            components.append((len(pixels), min_x, min_y, max_x, max_y, pixels))

    if not components:
        return crop
    main = max(components, key=lambda component: component[0])
    main_top, main_bottom = main[2], main[4]
    keep = []
    for component in components:
        area = component[0]
        if component is main:
            keep.append(component)
            continue
        if area < 20:
            continue
        # Pequenos fragmentos colados na borda superior são sobras da pose
        # de cima; efeitos grandes (bolas de fogo) continuam preservados.
        if area < 200 and component[4] <= 12:
            continue
        center_y = (component[2] + component[4]) / 2
        if main_top - 6 <= center_y <= main_bottom + 6:
            keep.append(component)

    clean = pygame.Surface((width, height), pygame.SRCALPHA)
    for _area, _min_x, _min_y, _max_x, _max_y, pixels in keep:
        for x, y in pixels:
            clean.set_at((x, y), crop.get_at((x, y)))
    bounds = clean.get_bounding_rect()
    if bounds.w <= 0 or bounds.h <= 0:
        return crop
    return clean.subsurface(bounds)


def _bottom_anchor_x(surface):
    """Centro horizontal dos pixels próximos ao chão do frame."""
    mask = pygame.mask.from_surface(surface)
    width, height = surface.get_size()
    band_top = max(0, height - max(8, height // 4))
    left = width
    right = -1
    for y in range(band_top, height):
        for x in range(width):
            if mask.get_at((x, y)):
                left = min(left, x)
                right = max(right, x)
    if right < left:
        return width // 2
    return (left + right) / 2


def load_character_animations(character):
    """Cria as 7 animações normalizadas a partir dos recortes irregulares.

    Os frames são recortados, escalados e centralizados pelo apoio dos pés.
    Assim o corpo não "desliza" quando um golpe tem uma bola de fogo ou um
    bastão comprido. O PNG original é descartado no fim da função.
    """
    sheet = pygame.image.load(
        resource_path(os.path.join("assets", "images", character["sheet"]))
    ).convert_alpha()
    scale = character["scale"]
    rows = character["rows"]

    # Primeiro passe: recorta/escala cada frame usado uma única vez.
    frame_cache = {}
    metrics = {}
    for action in character["actions"]:
        for ref in action:
            row, index = ref[0], ref[1]
            angle = ref[2] if len(ref) > 2 else 0
            key = (row, index, angle)
            if key in frame_cache:
                continue
            source_rect = rows[row][index]
            crop = _clean_frame(sheet.subsurface(source_rect))
            size = (max(1, int(crop.get_width() * scale)),
                    max(1, int(crop.get_height() * scale)))
            frame = pygame.transform.scale(crop, size)
            if angle:
                frame = pygame.transform.rotate(frame, angle)
            anchor = _bottom_anchor_x(frame)
            frame_cache[key] = frame
            metrics[key] = (anchor, frame.get_width() - anchor, frame.get_height())

    max_side = max(max(left, right) for left, right, _height in metrics.values())
    max_height = max(height for _left, _right, height in metrics.values())
    pad = 8
    cell_width = int(max_side * 2 + pad * 2)
    cell_height = int(max_height + pad)

    # Segundo passe: coloca cada frame num canvas comum, com os pés no fundo.
    animation_list = []
    for action in character["actions"]:
        frames = []
        for ref in action:
            row, index = ref[0], ref[1]
            angle = ref[2] if len(ref) > 2 else 0
            key = (row, index, angle)
            source = frame_cache[key]
            anchor, _right, _height = metrics[key]
            frame_surface = pygame.Surface((cell_width, cell_height), pygame.SRCALPHA)
            frame_surface.blit(
                source,
                (cell_width // 2 - int(anchor), cell_height - source.get_height()),
            )
            frames.append(frame_surface)
        animation_list.append(frames)

    data = [cell_width, 1, [0, 0]]
    return animation_list, data


def make_button_background(selected):
    surface = pygame.Surface((MENU_BUTTON_W, MENU_BUTTON_H), pygame.SRCALPHA)
    top = (34, 24, 22, 238) if selected else (10, 17, 29, 224)
    bottom = (16, 11, 12, 238) if selected else (5, 9, 17, 224)
    for y in range(MENU_BUTTON_H):
        t = y / max(1, MENU_BUTTON_H - 1)
        color = tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(4))
        pygame.draw.line(surface, color, (0, y), (MENU_BUTTON_W, y))
    pygame.draw.line(surface, (255, 255, 255, 16), (10, 1), (MENU_BUTTON_W - 10, 1))
    return surface


def make_button_glow():
    surface = pygame.Surface((MENU_BUTTON_W + 24, MENU_BUTTON_H + 24), pygame.SRCALPHA)
    for index in range(9):
        alpha = max(0, 20 - index * 2)
        pygame.draw.rect(
            surface,
            (GOLD[0], GOLD[1], GOLD[2], alpha),
            pygame.Rect(12 - index, 12 - index, MENU_BUTTON_W + index * 2, MENU_BUTTON_H + index * 2),
            border_radius=12,
        )
    return surface


MENU_BUTTON_W = 420
MENU_BUTTON_H = 54
MENU_BUTTON_GAP = 14
MENU_BUTTON_X = (SCREEN_WIDTH - MENU_BUTTON_W) // 2
MENU_BUTTON_Y = 202
MENU_ITEMS = [
    ("START GAME", "START"),
    ("CONTROLS", "CONTROLS"),
    ("SCORES", "SCORES"),
    ("EXIT", "EXIT"),
]

def build_screen_panel():
    """Painel único das telas de controles/recordes."""
    panel = pygame.Surface((880, 392), pygame.SRCALPHA)
    for y in range(panel.get_height()):
        t = y / max(1, panel.get_height() - 1)
        pygame.draw.line(
            panel,
            (7 + int(3 * t), 11 + int(3 * t), 20 + int(4 * t), 236),
            (0, y),
            (panel.get_width(), y),
        )
    pygame.draw.rect(
        panel, (GOLD[0], GOLD[1], GOLD[2], 54), panel.get_rect(), 1, border_radius=10
    )
    pygame.draw.line(
        panel,
        (GOLD[0], GOLD[1], GOLD[2], 82),
        (20, 1),
        (panel.get_width() - 20, 1),
        1,
    )
    return panel


COMBAT_BACKGROUNDS = build_combat_backgrounds()
bg_normal = COMBAT_BACKGROUNDS[0]
menu_bg = build_menu_background()
MENU_PANEL = build_menu_panel()
SCREEN_PANEL = build_screen_panel()
MENU_BUTTON_IDLE = make_button_background(False)
MENU_BUTTON_ACTIVE = make_button_background(True)
MENU_BUTTON_GLOW = make_button_glow()
MENU_LEFT = get_character_portrait(CHARACTER_BY_ID["ryu"], (190, 245))
MENU_RIGHT = pygame.transform.flip(
    get_character_portrait(CHARACTER_BY_ID["akuma"], (190, 245)), True, False
)


def draw_bg(is_game_started=False):
    # Fundo do combate e fundo do menu já estão prontos; nada de scale por frame.
    screen.blit(bg_normal if is_game_started else menu_bg, (0, 0))


def draw_action_button(text, font, x, y, width, height):
    """Botão escuro com contorno dourado, usado nas telas internas."""
    rect = pygame.Rect(x, y, width, height)
    pygame.draw.rect(screen, PANEL, rect, border_radius=6)
    pygame.draw.rect(screen, GOLD, rect, 2, border_radius=6)
    text_img = render_text(font, text, GOLD_LIGHT)
    screen.blit(text_img, text_img.get_rect(center=rect.center))
    return rect


def victory_screen(winner_img):
    start_time = pygame.time.get_ticks()
    while pygame.time.get_ticks() - start_time < ROUND_OVER_COOLDOWN:

        screen.blit(victory_img_big, (SCREEN_WIDTH // 2 - victory_img_big.get_width() // 2,
                                      SCREEN_HEIGHT // 2 - victory_img_big.get_height() // 2 - 50))

        screen.blit(winner_img, (SCREEN_WIDTH // 2 - winner_img.get_width() // 2,
                                 SCREEN_HEIGHT // 2 - winner_img.get_height() // 2 + 100))

        pygame.display.update()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()
        clock.tick(FPS)


def draw_gradient_text(text, font, x, y, colors):
    """
    Draws a gradient text by layering multiple text surfaces with slight offsets.
    """
    offset = 2
    for i, color in enumerate(colors):
        img = render_text(font, text, color)
        screen.blit(img, (x + i * offset, y + i * offset))


def make_title_surface(text, font, colors):
    width, height = font.size(text)
    surface = pygame.Surface((width + 8, height + 8), pygame.SRCALPHA)
    for index, color in enumerate(colors):
        surface.blit(font.render(text, True, color), (index * 2, index * 2))
    return surface


title_text = "STREET FIGHTER"
title_surface = make_title_surface(
    title_text,
    menu_font_title,
    [CRIMSON_DARK, CRIMSON, (238, 120, 64), GOLD_LIGHT],
)
title_shadow = menu_font_title.render(title_text, True, BLACK)
TITLE_RECT = title_surface.get_rect(center=(SCREEN_WIDTH // 2, 76))

subtitle_surface = small_font.render("A R C A D E   E D I T I O N", True, GOLD)
SUBTITLE_RECT = subtitle_surface.get_rect(center=(SCREEN_WIDTH // 2, 138))


def draw_menu_title():
    screen.blit(title_shadow, TITLE_RECT.move(6, 6))
    screen.blit(title_surface, TITLE_RECT)
    screen.blit(subtitle_surface, SUBTITLE_RECT)
    line_y = SUBTITLE_RECT.centery
    pygame.draw.line(
        screen,
        GOLD_DARK,
        (SUBTITLE_RECT.left - 84, line_y),
        (SUBTITLE_RECT.left - 18, line_y),
        1,
    )
    pygame.draw.line(
        screen,
        GOLD_DARK,
        (SUBTITLE_RECT.right + 18, line_y),
        (SUBTITLE_RECT.right + 84, line_y),
        1,
    )


def draw_menu_portraits():
    now = pygame.time.get_ticks()
    bob = int(math.sin(now * 0.0025) * 4)
    if MENU_LEFT is not None:
        rect = MENU_LEFT.get_rect(midbottom=(140, 505 + bob))
        screen.blit(MENU_LEFT, rect)
    if MENU_RIGHT is not None:
        rect = MENU_RIGHT.get_rect(midbottom=(820, 505 - bob))
        screen.blit(MENU_RIGHT, rect)


def draw_menu_button(rect, label, selected, number):
    if selected:
        screen.blit(MENU_BUTTON_GLOW, (rect.x - 12, rect.y - 12))
    screen.blit(MENU_BUTTON_ACTIVE if selected else MENU_BUTTON_IDLE, rect)
    pygame.draw.rect(
        screen,
        GOLD if selected else (44, 58, 78),
        rect,
        1,
        border_radius=7,
    )
    pygame.draw.rect(
        screen,
        GOLD if selected else CRIMSON_DARK,
        (rect.x + 5, rect.y + 9, 3, rect.height - 18),
        border_radius=2,
    )
    if selected:
        pygame.draw.polygon(
            screen,
            GOLD,
            [
                (rect.x + 16, rect.centery - 6),
                (rect.x + 24, rect.centery),
                (rect.x + 16, rect.centery + 6),
            ],
        )

    label_surface = render_text(
        controls_font, label, GOLD_LIGHT if selected else STEEL
    )
    screen.blit(
        label_surface,
        (rect.x + 38, rect.centery - label_surface.get_height() // 2),
    )
    number_surface = render_text(
        small_font,
        f"0{number}",
        GOLD_DARK if selected else (70, 80, 98),
    )
    screen.blit(
        number_surface,
        (
            rect.right - 24 - number_surface.get_width(),
            rect.centery - number_surface.get_height() // 2,
        ),
    )


def draw_menu_footer():
    hint = render_text(
        small_font,
        "W / S  NAVEGAR    |    ENTER  CONFIRMAR    |    ESC  SAIR",
        (164, 174, 194),
    )
    screen.blit(hint, hint.get_rect(center=(SCREEN_WIDTH // 2, 522)))


def main_menu():
    selected = 0
    button_rects = [
        pygame.Rect(
            MENU_BUTTON_X,
            MENU_BUTTON_Y + index * (MENU_BUTTON_H + MENU_BUTTON_GAP),
            MENU_BUTTON_W,
            MENU_BUTTON_H,
        )
        for index in range(len(MENU_ITEMS))
    ]

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_UP, pygame.K_w):
                    selected = (selected - 1) % len(MENU_ITEMS)
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    selected = (selected + 1) % len(MENU_ITEMS)
                elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                    return MENU_ITEMS[selected][1]
                elif event.key == pygame.K_ESCAPE:
                    return "EXIT"
            elif event.type == pygame.MOUSEMOTION:
                for index, rect in enumerate(button_rects):
                    if rect.collidepoint(event.pos):
                        selected = index
                        break
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for index, rect in enumerate(button_rects):
                    if rect.collidepoint(event.pos):
                        selected = index
                        return MENU_ITEMS[index][1]

        draw_bg(is_game_started=False)
        screen.blit(MENU_PANEL, (243, 176))
        draw_menu_portraits()
        draw_menu_title()
        for index, (label, _action) in enumerate(MENU_ITEMS):
            draw_menu_button(
                button_rects[index],
                label,
                index == selected,
                index + 1,
            )
        draw_menu_footer()
        pygame.display.update()
        clock.tick(FPS)


SELECT_CARD_W = 160
SELECT_CARD_H = 286
SELECT_CARD_GAP = 18
SELECT_CARD_X = (SCREEN_WIDTH - (len(CHARACTERS) * SELECT_CARD_W + (len(CHARACTERS) - 1) * SELECT_CARD_GAP)) // 2
SELECT_CARD_Y = 124
select_name_font = pygame.font.Font(resource_path("assets/fonts/turok.ttf"), 24)


def _draw_character_card(rect, character, selected):
    if selected:
        glow = pygame.Surface((rect.w + 22, rect.h + 22), pygame.SRCALPHA)
        for index in range(8):
            alpha = max(0, 24 - index * 3)
            pygame.draw.rect(
                glow,
                (GOLD[0], GOLD[1], GOLD[2], alpha),
                pygame.Rect(11 - index, 11 - index, rect.w + index * 2, rect.h + index * 2),
                border_radius=12,
            )
        screen.blit(glow, (rect.x - 11, rect.y - 11))

    pygame.draw.rect(screen, (8, 13, 22), rect, border_radius=9)
    if selected:
        pygame.draw.rect(screen, GOLD, rect, 3, border_radius=9)
        pygame.draw.rect(screen, (GOLD[0], GOLD[1], GOLD[2], 92), rect.inflate(-8, -8), 1, border_radius=7)
    else:
        pygame.draw.rect(screen, (52, 64, 82), rect, 2, border_radius=9)

    portrait = get_character_portrait(character, (rect.w - 22, 184))
    screen.blit(portrait, portrait.get_rect(center=(rect.centerx, rect.y + 104)))

    name = render_text(select_name_font, character["name"], GOLD_LIGHT if selected else STEEL)
    screen.blit(name, name.get_rect(center=(rect.centerx, rect.bottom - 52)))

    tag = render_text(small_font, "FIGHTER", GOLD_DARK if selected else (70, 80, 98))
    screen.blit(tag, tag.get_rect(center=(rect.centerx, rect.bottom - 24)))

    if selected:
        pygame.draw.polygon(
            screen,
            GOLD,
            [
                (rect.centerx - 7, rect.bottom + 7),
                (rect.centerx + 7, rect.bottom + 7),
                (rect.centerx, rect.bottom + 15),
            ],
        )


def character_select():
    selected = 0
    card_rects = [
        pygame.Rect(
            SELECT_CARD_X + index * (SELECT_CARD_W + SELECT_CARD_GAP),
            SELECT_CARD_Y,
            SELECT_CARD_W,
            SELECT_CARD_H,
        )
        for index in range(len(CHARACTERS))
    ]

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_LEFT, pygame.K_a):
                    selected = (selected - 1) % len(CHARACTERS)
                elif event.key in (pygame.K_RIGHT, pygame.K_d):
                    selected = (selected + 1) % len(CHARACTERS)
                elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                    return CHARACTERS[selected]
                elif event.key == pygame.K_ESCAPE:
                    return None
            elif event.type == pygame.MOUSEMOTION:
                for index, rect in enumerate(card_rects):
                    if rect.collidepoint(event.pos):
                        selected = index
                        break
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for index, rect in enumerate(card_rects):
                    if rect.collidepoint(event.pos):
                        selected = index
                        return CHARACTERS[index]

        draw_bg(is_game_started=False)

        title = "SELECT YOUR FIGHTER"
        title_img = render_text(menu_font, title, GOLD_LIGHT)
        screen.blit(title_img, title_img.get_rect(center=(SCREEN_WIDTH // 2, 48)))
        subtitle = render_text(
            small_font,
            "O OPONENTE DA CPU SERA ESCOLHIDO ALEATORIAMENTE",
            (164, 174, 194),
        )
        screen.blit(subtitle, subtitle.get_rect(center=(SCREEN_WIDTH // 2, 90)))

        for index, character in enumerate(CHARACTERS):
            _draw_character_card(card_rects[index], character, index == selected)

        hint = render_text(
            small_font,
            "A / D  OU  SETAS  ESCOLHER    |    ENTER  LUTAR    |    ESC  VOLTAR",
            GOLD,
        )
        screen.blit(hint, hint.get_rect(center=(SCREEN_WIDTH // 2, 500)))

        pygame.display.update()
        clock.tick(FPS)


def scores_screen():
    while True:
        draw_bg()
        screen.blit(SCREEN_PANEL, (40, 88))

        scores_title = "SCORES"
        draw_text(
            scores_title,
            menu_font,
            GOLD_LIGHT,
            SCREEN_WIDTH // 2 - menu_font.size(scores_title)[0] // 2,
            24,
        )

        p1_text = f"P1: {score[0]}"
        p2_text = f"P2: {score[1]}"
        shadow_offset = 5

        draw_text(
            "PLAYER 1",
            small_font,
            GOLD_DARK,
            SCREEN_WIDTH // 2 - small_font.size("PLAYER 1")[0] // 2,
            160,
        )
        p1_text_x = SCREEN_WIDTH // 2 - score_font_large.size(p1_text)[0] // 2
        p1_text_y = 190
        draw_text(
            p1_text,
            score_font_large,
            BLACK,
            p1_text_x + shadow_offset,
            p1_text_y + shadow_offset,
        )
        draw_gradient_text(
            p1_text,
            score_font_large,
            p1_text_x,
            p1_text_y,
            [GOLD_DARK, GOLD_LIGHT],
        )

        draw_text(
            "CPU",
            small_font,
            CRIMSON,
            SCREEN_WIDTH // 2 - small_font.size("CPU")[0] // 2,
            290,
        )
        p2_text_x = SCREEN_WIDTH // 2 - score_font_large.size(p2_text)[0] // 2
        p2_text_y = 320
        draw_text(
            p2_text,
            score_font_large,
            BLACK,
            p2_text_x + shadow_offset,
            p2_text_y + shadow_offset,
        )
        draw_gradient_text(
            p2_text,
            score_font_large,
            p2_text_x,
            p2_text_y,
            [CRIMSON_DARK, (238, 120, 64)],
        )

        return_button = draw_action_button(
            "RETURN TO MAIN MENU",
            controls_font,
            SCREEN_WIDTH // 2 - 220,
            488,
            500,
            46,
        )

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return
            if event.type == pygame.MOUSEBUTTONDOWN:
                if return_button.collidepoint(event.pos):
                    return

        pygame.display.update()
        clock.tick(FPS)


def controls_screen():
    while True:
        draw_bg()
        screen.blit(SCREEN_PANEL, (40, 88))

        controls_title = "CONTROLS GUIDE"
        draw_text(
            controls_title,
            menu_font,
            GOLD_LIGHT,
            SCREEN_WIDTH // 2 - menu_font.size(controls_title)[0] // 2,
            24,
        )

        pygame.draw.line(screen, (78, 70, 52), (470, 112), (470, 452), 1)

        # Movement controls
        draw_text("MOVEMENT:", controls_font, GOLD, 90, 112)
        draw_text("A - Move Left", small_font, STEEL, 90, 154)
        draw_text("D - Move Right", small_font, STEEL, 90, 184)
        draw_text("W - Jump", small_font, STEEL, 90, 214)

        # Attack controls
        draw_text("ATTACKS:", controls_font, GOLD, 90, 258)
        draw_text("R - Close Range Attack", small_font, (236, 132, 120), 90, 298)
        draw_text("T - Long Range Attack", small_font, (236, 132, 120), 90, 328)

        # Game info
        draw_text("GAME INFO:", controls_font, GOLD, 510, 112)
        draw_text("You choose your fighter", small_font, GOLD_LIGHT, 510, 154)
        draw_text("Computer picks a random fighter", small_font, (236, 132, 120), 510, 184)
        draw_text("Each attack deals 10 damage", small_font, STEEL, 510, 214)
        draw_text("First to lose all health loses", small_font, STEEL, 510, 244)

        # Tips
        draw_text("TIPS:", controls_font, GOLD, 510, 294)
        draw_text("Jump to avoid attacks", small_font, STEEL, 510, 334)
        draw_text("Use close attacks when near", small_font, STEEL, 510, 364)
        draw_text("Use long attacks at distance", small_font, STEEL, 510, 394)
        draw_text("Watch for AI patterns!", small_font, STEEL, 510, 424)

        # Return button
        return_button = draw_action_button(
            "RETURN TO MAIN MENU",
            controls_font,
            SCREEN_WIDTH // 2 - 220,
            488,
            500,
            46,
        )

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return
            if event.type == pygame.MOUSEBUTTONDOWN:
                if return_button.collidepoint(event.pos):
                    return

        pygame.display.update()
        clock.tick(FPS)


def reset_game(player_character, cpu_character):
    global fighter_1, fighter_2
    player_animations, player_data = load_character_animations(player_character)
    if cpu_character["id"] == player_character["id"]:
        # Reaproveita as superfícies quando os dois lutadores são iguais.
        cpu_animations, cpu_data = player_animations, player_data
    else:
        cpu_animations, cpu_data = load_character_animations(cpu_character)

    player_sound = magic_fx if player_character["sound"] == "magic" else sword_fx
    cpu_sound = magic_fx if cpu_character["sound"] == "magic" else sword_fx
    start_y = COMBAT_FLOOR_Y - 180
    fighter_1 = Fighter(
        1, 180, start_y, False, player_data, sound=player_sound,
        animation_list=player_animations, frame_anchor=True,
        floor_y=COMBAT_FLOOR_Y,
    )
    fighter_2 = Fighter(
        2, 700, start_y, True, cpu_data, sound=cpu_sound,
        animation_list=cpu_animations, frame_anchor=True,
        floor_y=COMBAT_FLOOR_Y,
    )


def draw_health_bar(health, x, y):
    pygame.draw.rect(screen, BLACK, (x, y, 200, 20))
    if health > 0:
        pygame.draw.rect(screen, RED, (x, y, health * 2, 20))
    pygame.draw.rect(screen, WHITE, (x, y, 200, 20), 2)


def countdown():
    countdown_texts = ["3", "2", "1", "FIGHT!"]

    for text in countdown_texts:
        draw_bg(is_game_started=True)

        text_img = countdown_font.render(text, True, RED)
        text_width = text_img.get_width()
        x_pos = (SCREEN_WIDTH - text_width) // 2

        draw_text(text, countdown_font, RED, x_pos, SCREEN_HEIGHT // 2 - 50)

        pygame.display.update()
        pygame.time.delay(1000)


def game_loop(player_character, cpu_character):
    global score, bg_normal
    bg_normal = random.choice(COMBAT_BACKGROUNDS)
    reset_game(player_character, cpu_character)
    round_over = False
    winner_img = None
    game_started = True

    countdown()

    while True:
        draw_bg(is_game_started=game_started)

        draw_text(f"P1: {score[0]}", score_font, RED, 20, 20)
        draw_text(f"P2: {score[1]}", score_font, RED, SCREEN_WIDTH - 220, 20)
        
        # Add player identification labels
        draw_text(f"USER - {player_character['name']}", player_label_font, BLUE, 20, 85)
        draw_text(
            f"CPU - {cpu_character['name']}",
            player_label_font,
            (255, 100, 0),
            SCREEN_WIDTH - 220,
            85,
        )
        
        draw_health_bar(fighter_1.health, 20, 50)
        draw_health_bar(fighter_2.health, SCREEN_WIDTH - 220, 50)

        exit_button = draw_action_button(
            "MAIN MENU", menu_font, SCREEN_WIDTH // 2 - 150, 20, 300, 50
        )

        if not round_over:
            fighter_1.move(SCREEN_WIDTH, SCREEN_HEIGHT, fighter_2, round_over)
            fighter_2.move(SCREEN_WIDTH, SCREEN_HEIGHT, fighter_1, round_over)

            fighter_1.update()
            fighter_2.update()

            if not fighter_1.alive:
                score[1] += 1
                round_over = True
                winner_img = get_character_portrait(cpu_character, (260, 300))
            elif not fighter_2.alive:
                score[0] += 1
                round_over = True
                winner_img = get_character_portrait(player_character, (260, 300))
        else:
            victory_screen(winner_img)
            return

        fighter_1.draw(screen)
        fighter_2.draw(screen)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return
            if event.type == pygame.MOUSEBUTTONDOWN:
                if exit_button.collidepoint(event.pos):
                    return

        pygame.display.update()
        clock.tick(FPS)


if __name__ == "__main__":
    while True:
        menu_selection = main_menu()

        if menu_selection == "START":
            player_character = character_select()
            if player_character is not None:
                opponents = [
                    character
                    for character in CHARACTERS
                    if character["id"] != player_character["id"]
                ]
                cpu_character = random.choice(opponents or CHARACTERS)
                game_loop(player_character, cpu_character)
        elif menu_selection == "CONTROLS":
            controls_screen()
        elif menu_selection == "SCORES":
            scores_screen()
        else:
            pygame.quit()
            exit()
