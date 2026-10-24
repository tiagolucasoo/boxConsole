"""
Snake Eater
Made with PyGame
"""

import pygame, sys, random


# Difficulty settings
# Easy      ->  10
# Medium    ->  25
# Hard      ->  40
# Harder    ->  60
# Impossible->  120
difficulty = 25

# Window size
frame_size_x = 720
frame_size_y = 480

# Checks for errors encountered
check_errors = pygame.init()
# pygame.init() example output -> (6, 0)
# second number in tuple gives number of errors
if check_errors[1] > 0:
    print(f'[!] Had {check_errors[1]} errors when initialising game, exiting...')
    sys.exit(-1)


# Initialise game window
pygame.display.set_caption('Snake Eater')
game_window = pygame.display.set_mode((frame_size_x, frame_size_y))


# Colors (R, G, B)
black = pygame.Color(0, 0, 0)
white = pygame.Color(255, 255, 255)
red = pygame.Color(255, 0, 0)
green = pygame.Color(0, 255, 0)
blue = pygame.Color(0, 0, 255)
snake_head = pygame.Color(140, 255, 140)
apple = pygame.Color(225, 70, 70)
leaf = pygame.Color(90, 200, 100)


# FPS (frames per second) controller
fps_controller = pygame.time.Clock()


# Game variables
snake_pos = [100, 50]
snake_body = [[100, 50], [100-10, 50], [100-(2*10), 50]]

food_pos = [random.randrange(1, (frame_size_x//10)) * 10, random.randrange(1, (frame_size_y//10)) * 10]

direction = 'RIGHT'
change_to = direction

score = 0
paused = False


# Game Over
def game_over():
    my_font = pygame.font.SysFont('times new roman', 90)
    game_over_surface = my_font.render('YOU DIED', True, red)
    game_over_rect = game_over_surface.get_rect()
    game_over_rect.midtop = (frame_size_x/2, frame_size_y/4)

    hint_font = pygame.font.SysFont('consolas', 24)
    hint_surface = hint_font.render('R = jogar de novo   |   ESC = sair', True, white)
    hint_rect = hint_surface.get_rect()
    hint_rect.midtop = (frame_size_x/2, frame_size_y/2)

    game_window.fill(black)
    game_window.blit(game_over_surface, game_over_rect)
    show_score(0, red, 'times', 20)
    game_window.blit(hint_surface, hint_rect)
    pygame.display.flip()

    # Espera o jogador decidir em vez de fechar sozinho.
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    reset_game()
                    return
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()
        fps_controller.tick(15)


# Score
def show_score(choice, color, font, size):
    score_font = pygame.font.SysFont(font, size)
    score_surface = score_font.render('Score : ' + str(score), True, color)
    score_rect = score_surface.get_rect()
    if choice == 1:
        score_rect.midtop = (frame_size_x/10, 15)
    else:
        score_rect.midtop = (frame_size_x/2, frame_size_y/1.25)
    game_window.blit(score_surface, score_rect)
    # pygame.display.flip()


# Coloca a comida sempre em uma casa livre (nunca sobre a cobra)
def spawn_food():
    global food_pos
    free_cells = [
        [x, y]
        for x in range(10, frame_size_x - 9, 10)
        for y in range(10, frame_size_y - 9, 10)
        if [x, y] not in snake_body
    ]
    if free_cells:
        food_pos = random.choice(free_cells)


# Reinicia a partida sem fechar o jogo
def reset_game():
    global snake_pos, snake_body, direction, change_to, score
    snake_pos = [100, 50]
    snake_body = [[100, 50], [90, 50], [80, 50]]
    direction = 'RIGHT'
    change_to = direction
    score = 0
    spawn_food()


spawn_food()


# Main logic
while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
        # Whenever a key is pressed down
        elif event.type == pygame.KEYDOWN:
            # W -> Up; S -> Down; A -> Left; D -> Right
            if event.key == pygame.K_UP or event.key == ord('w'):
                change_to = 'UP'
            if event.key == pygame.K_DOWN or event.key == ord('s'):
                change_to = 'DOWN'
            if event.key == pygame.K_LEFT or event.key == ord('a'):
                change_to = 'LEFT'
            if event.key == pygame.K_RIGHT or event.key == ord('d'):
                change_to = 'RIGHT'
            # Esc -> Create event to quit the game
            if event.key == pygame.K_ESCAPE:
                pygame.event.post(pygame.event.Event(pygame.QUIT))
            # P / Espaço -> pausar ou continuar
            if event.key in (pygame.K_p, pygame.K_SPACE):
                paused = not paused

    # Pausa: congela a cobra até o jogador mandar continuar
    if paused:
        pause_font = pygame.font.SysFont('consolas', 30)
        pause_surface = pause_font.render('PAUSADO', True, white)
        pause_rect = pause_surface.get_rect()
        pause_rect.midtop = (frame_size_x/2, 15)
        show_score(1, white, 'consolas', 20)
        game_window.blit(pause_surface, pause_rect)
        pygame.display.update()
        fps_controller.tick(difficulty)
        continue

    # Making sure the snake cannot move in the opposite direction instantaneously
    if change_to == 'UP' and direction != 'DOWN':
        direction = 'UP'
    if change_to == 'DOWN' and direction != 'UP':
        direction = 'DOWN'
    if change_to == 'LEFT' and direction != 'RIGHT':
        direction = 'LEFT'
    if change_to == 'RIGHT' and direction != 'LEFT':
        direction = 'RIGHT'

    # Moving the snake
    if direction == 'UP':
        snake_pos[1] -= 10
    if direction == 'DOWN':
        snake_pos[1] += 10
    if direction == 'LEFT':
        snake_pos[0] -= 10
    if direction == 'RIGHT':
        snake_pos[0] += 10

    # Snake body growing mechanism
    snake_body.insert(0, list(snake_pos))
    if snake_pos[0] == food_pos[0] and snake_pos[1] == food_pos[1]:
        score += 1
        spawn_food()  # nova comida sempre em casa livre
    else:
        snake_body.pop()

    # GFX
    game_window.fill(black)
    for index, pos in enumerate(snake_body):
        # A cabeça ganha um tom mais claro para destacar
        color = snake_head if index == 0 else green
        pygame.draw.rect(game_window, color, pygame.Rect(pos[0], pos[1], 10, 10))

    # Snake food (uma maçã com folhinha)
    pygame.draw.circle(game_window, apple, (food_pos[0] + 5, food_pos[1] + 5), 5)
    pygame.draw.rect(game_window, leaf, pygame.Rect(food_pos[0] + 5, food_pos[1] - 1, 4, 3))

    # Game Over conditions
    # Getting out of bounds
    if snake_pos[0] < 0 or snake_pos[0] > frame_size_x-10:
        game_over()
    if snake_pos[1] < 0 or snake_pos[1] > frame_size_y-10:
        game_over()
    # Touching the snake body
    for block in snake_body[1:]:
        if snake_pos[0] == block[0] and snake_pos[1] == block[1]:
            game_over()

    show_score(1, white, 'consolas', 20)
    # Refresh game screen
    pygame.display.update()
    # Refresh rate
    fps_controller.tick(difficulty)