import pygame
from pygame import mixer
from pygame import font
import os
import sys
from fighter import Fighter

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

# Colors
RED = (255, 0, 0)
YELLOW = (255, 255, 0)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
BLUE = (0, 0, 255)
GREEN = (0, 255, 0)

# Initialize Game Window
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.NOFRAME)
pygame.display.set_caption("Street Fighter")
clock = pygame.time.Clock()

# Load Assets
bg_image = pygame.image.load(resource_path("assets/images/bg1.jpg")).convert()
bg_normal = pygame.transform.smoothscale(bg_image, (SCREEN_WIDTH, SCREEN_HEIGHT))
victory_img = pygame.image.load(resource_path("assets/images/victory.png")).convert_alpha()
victory_img_big = pygame.transform.scale(
    victory_img, (victory_img.get_width() * 2, victory_img.get_height() * 2)
)
warrior_victory_img = pygame.image.load(resource_path("assets/images/warrior.png")).convert_alpha()
wizard_victory_img = pygame.image.load(resource_path("assets/images/wizard.png")).convert_alpha()

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

# Load Fighter Spritesheets
warrior_sheet = pygame.image.load(resource_path("assets/images/warrior.png")).convert_alpha()
wizard_sheet = pygame.image.load(resource_path("assets/images/wizard.png")).convert_alpha()

# Define Animation Steps
WARRIOR_ANIMATION_STEPS = [10, 8, 1, 7, 7, 3, 7]
WIZARD_ANIMATION_STEPS = [8, 8, 1, 8, 8, 3, 7]

# Fighter Data
WARRIOR_SIZE = 162
WARRIOR_SCALE = 2
WARRIOR_OFFSET = [72, 46]
WARRIOR_DATA = [WARRIOR_SIZE, WARRIOR_SCALE, WARRIOR_OFFSET]
WIZARD_SIZE = 250
WIZARD_SCALE = 2
WIZARD_OFFSET = [112, 110]
WIZARD_DATA = [WIZARD_SIZE, WIZARD_SCALE, WIZARD_OFFSET]

# Game Variables
score = [0, 0]  # Player Scores: [P1, P2]


def draw_text(text, font, color, x, y):
    img = font.render(text, True, color)
    screen.blit(img, (x, y))


def blur_bg(image):
    """Desfoque barato: reduz e amplia uma única vez no início."""
    small = pygame.transform.smoothscale(image, (96, 54))
    return pygame.transform.smoothscale(small, (SCREEN_WIDTH, SCREEN_HEIGHT))


bg_blurred = blur_bg(bg_normal)


def draw_bg(image=None, is_game_started=False):
    # As duas versões do fundo já estão prontas; nada de blur por frame.
    screen.blit(bg_normal if is_game_started else bg_blurred, (0, 0))


def draw_button(text, font, text_col, button_col, x, y, width, height):
    pygame.draw.rect(screen, button_col, (x, y, width, height))
    pygame.draw.rect(screen, WHITE, (x, y, width, height), 2)
    text_img = font.render(text, True, text_col)
    text_rect = text_img.get_rect(center=(x + width // 2, y + height // 2))
    screen.blit(text_img, text_rect)
    return pygame.Rect(x, y, width, height)


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


def draw_gradient_text(text, font, x, y, colors):
    """
    Draws a gradient text by layering multiple text surfaces with slight offsets.
    """
    offset = 2
    for i, color in enumerate(colors):
        img = font.render(text, True, color)
        screen.blit(img, (x + i * offset, y + i * offset))


def make_title_surface(text, font, colors):
    width, height = font.size(text)
    surface = pygame.Surface((width + 8, height + 8), pygame.SRCALPHA)
    for index, color in enumerate(colors):
        surface.blit(font.render(text, True, color), (index * 2, index * 2))
    return surface


title_text = "STREET FIGHTER"
title_surface = make_title_surface(title_text, menu_font_title, [BLUE, GREEN, YELLOW])
title_shadow = menu_font_title.render(title_text, True, BLACK)


def main_menu():
    while True:
        draw_bg(bg_image, is_game_started=False)

        title_x = SCREEN_WIDTH // 2 - menu_font_title.size(title_text)[0] // 2
        title_y = 10
        screen.blit(title_shadow, (title_x + 5, title_y + 5))
        screen.blit(title_surface, (title_x, title_y))

        button_width = 280
        button_height = 60
        button_spacing = 30

        start_button_y = SCREEN_HEIGHT // 2 - (button_height + button_spacing) * 2 + 50
        controls_button_y = SCREEN_HEIGHT // 2 - (button_height + button_spacing) * 1 + 50
        scores_button_y = SCREEN_HEIGHT // 2 + (button_height + button_spacing) * 0 + 50
        exit_button_y = SCREEN_HEIGHT // 2 + (button_height + button_spacing) * 1 + 50

        start_button = draw_button("START GAME", menu_font, BLACK, GREEN, SCREEN_WIDTH // 2 - button_width // 2,
                                   start_button_y, button_width, button_height)
        controls_button = draw_button("CONTROLS", menu_font, BLACK, GREEN, SCREEN_WIDTH // 2 - button_width // 2,
                                     controls_button_y, button_width, button_height)
        scores_button = draw_button("SCORES", menu_font, BLACK, GREEN, SCREEN_WIDTH // 2 - button_width // 2,
                                    scores_button_y, button_width, button_height)
        exit_button = draw_button("EXIT", menu_font, BLACK, GREEN, SCREEN_WIDTH // 2 - button_width // 2,
                                  exit_button_y, button_width, button_height)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                if start_button.collidepoint(event.pos):
                    return "START"
                if controls_button.collidepoint(event.pos):
                    return "CONTROLS"
                if scores_button.collidepoint(event.pos):
                    return "SCORES"
                if exit_button.collidepoint(event.pos):
                    pygame.quit()
                    exit()

        pygame.display.update()
        clock.tick(FPS)


def scores_screen():
    while True:
        draw_bg(bg_image)

        scores_title = "SCORES"
        draw_text(scores_title, menu_font_title, RED, SCREEN_WIDTH // 2 - menu_font_title.size(scores_title)[0] // 2, 20)

        p1_text = f"P1: {score[0]}"
        p2_text = f"P2: {score[1]}"
        shadow_offset = 5

        p1_text_x = SCREEN_WIDTH // 2 - score_font_large.size(p1_text)[0] // 2
        p1_text_y = SCREEN_HEIGHT // 2 - 50
        draw_text(p1_text, score_font_large, BLACK, p1_text_x + shadow_offset, p1_text_y + shadow_offset)  # Shadow
        draw_gradient_text(p1_text, score_font_large, p1_text_x, p1_text_y, [BLUE, GREEN])  # Gradient

        p2_text_x = SCREEN_WIDTH // 2 - score_font_large.size(p2_text)[0] // 2
        p2_text_y = SCREEN_HEIGHT // 2 + 50
        draw_text(p2_text, score_font_large, BLACK, p2_text_x + shadow_offset, p2_text_y + shadow_offset)  # Shadow
        draw_gradient_text(p2_text, score_font_large, p2_text_x, p2_text_y, [RED, YELLOW])  # Gradient

        return_button = draw_button(
            "RETURN TO MAIN MENU", menu_font, BLACK, GREEN,
            SCREEN_WIDTH // 2 - 220, SCREEN_HEIGHT - 55, 500, 50,
        )

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                if return_button.collidepoint(event.pos):
                    return

        pygame.display.update()
        clock.tick(FPS)


def controls_screen():
    while True:
        draw_bg(bg_image)

        # Title
        controls_title = "CONTROLS GUIDE"
        draw_text(controls_title, menu_font_title, GREEN, SCREEN_WIDTH // 2 - menu_font_title.size(controls_title)[0] // 2, 20)
        
        # Movement controls
        draw_text("MOVEMENT:", controls_font, WHITE, 100, 150)
        draw_text("A - Move Left", small_font, BLUE, 100, 190)
        draw_text("D - Move Right", small_font, BLUE, 100, 220)
        draw_text("W - Jump", small_font, BLUE, 100, 250)
        
        # Attack controls
        draw_text("ATTACKS:", controls_font, WHITE, 100, 300)
        draw_text("R - Close Range Attack", small_font, RED, 100, 340)
        draw_text("T - Long Range Attack", small_font, RED, 100, 370)
        
        # Game info
        draw_text("GAME INFO:", controls_font, WHITE, 500, 150)
        draw_text("• You play as the WARRIOR (left)", small_font, YELLOW, 500, 190)
        draw_text("• Computer plays as WIZARD (right)", small_font, (255, 100, 0), 500, 220)
        draw_text("• Each attack deals 10 damage", small_font, WHITE, 500, 250)
        draw_text("• First to lose all health loses", small_font, WHITE, 500, 280)
        
        # Tips
        draw_text("TIPS:", controls_font, WHITE, 500, 330)
        draw_text("• Jump to avoid attacks", small_font, GREEN, 500, 370)
        draw_text("• Use close attacks when near", small_font, GREEN, 500, 400)
        draw_text("• Use long attacks at distance", small_font, GREEN, 500, 430)
        draw_text("• Watch for AI patterns!", small_font, GREEN, 500, 460)
        
        # Return button
        return_button = draw_button(
            "RETURN TO MAIN MENU", menu_font, BLACK, GREEN,
            SCREEN_WIDTH // 2 - 220, SCREEN_HEIGHT - 55, 500, 50,
        )

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                if return_button.collidepoint(event.pos):
                    return

        pygame.display.update()
        clock.tick(FPS)


def reset_game():
    global fighter_1, fighter_2
    fighter_1 = Fighter(1, 180, 250, False, WARRIOR_DATA, warrior_sheet, WARRIOR_ANIMATION_STEPS, sword_fx)
    fighter_2 = Fighter(2, 700, 250, True, WIZARD_DATA, wizard_sheet, WIZARD_ANIMATION_STEPS, magic_fx)


def draw_health_bar(health, x, y):
    pygame.draw.rect(screen, BLACK, (x, y, 200, 20))
    if health > 0:
        pygame.draw.rect(screen, RED, (x, y, health * 2, 20))
    pygame.draw.rect(screen, WHITE, (x, y, 200, 20), 2)


def countdown():
    countdown_texts = ["3", "2", "1", "FIGHT!"]

    for text in countdown_texts:
        draw_bg(bg_image, is_game_started=True)

        text_img = countdown_font.render(text, True, RED)
        text_width = text_img.get_width()
        x_pos = (SCREEN_WIDTH - text_width) // 2

        draw_text(text, countdown_font, RED, x_pos, SCREEN_HEIGHT // 2 - 50)

        pygame.display.update()
        pygame.time.delay(1000)


def game_loop():
    global score
    reset_game()
    round_over = False
    winner_img = None
    game_started = True

    countdown()

    while True:
        draw_bg(bg_image, is_game_started=game_started)

        draw_text(f"P1: {score[0]}", score_font, RED, 20, 20)
        draw_text(f"P2: {score[1]}", score_font, RED, SCREEN_WIDTH - 220, 20)
        
        # Add player identification labels
        draw_text("USER", player_label_font, BLUE, 20, 85)
        draw_text("COMPUTER", player_label_font, (255, 100, 0), SCREEN_WIDTH - 220, 85)
        
        draw_health_bar(fighter_1.health, 20, 50)
        draw_health_bar(fighter_2.health, SCREEN_WIDTH - 220, 50)

        exit_button = draw_button("MAIN MENU", menu_font, BLACK, YELLOW, SCREEN_WIDTH // 2 - 150, 20, 300, 50)

        if not round_over:
            fighter_1.move(SCREEN_WIDTH, SCREEN_HEIGHT, fighter_2, round_over)
            fighter_2.move(SCREEN_WIDTH, SCREEN_HEIGHT, fighter_1, round_over)

            fighter_1.update()
            fighter_2.update()

            if not fighter_1.alive:
                score[1] += 1
                round_over = True
                winner_img = wizard_victory_img
            elif not fighter_2.alive:
                score[0] += 1
                round_over = True
                winner_img = warrior_victory_img
        else:
            victory_screen(winner_img)
            return

        fighter_1.draw(screen)
        fighter_2.draw(screen)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                if exit_button.collidepoint(event.pos):
                    return

        pygame.display.update()
        clock.tick(FPS)


while True:
    menu_selection = main_menu()

    if menu_selection == "START":
        game_loop()
    elif menu_selection == "CONTROLS":
        controls_screen()
    elif menu_selection == "SCORES":
        scores_screen()
