import math

# game settings
# O H3 é ARMv7 e o raycasting é feito na CPU. 480x270 com 160 raios deixa o
# jogo jogável; o host do BoxConsole amplia para a área de 960x540.
RES = WIDTH, HEIGHT = 480, 270
# RES = WIDTH, HEIGHT = 1920, 1080
HALF_WIDTH = WIDTH // 2
HALF_HEIGHT = HEIGHT // 2
FPS = 24

PLAYER_POS = 1.5, 5  # mini_map
PLAYER_ANGLE = 0
PLAYER_SPEED = 0.004
PLAYER_ROT_SPEED = 0.002
PLAYER_SIZE_SCALE = 60
PLAYER_MAX_HEALTH = 100

MOUSE_SENSITIVITY = 0.0003
MOUSE_MAX_REL = 40
MOUSE_BORDER_LEFT = 100
MOUSE_BORDER_RIGHT = WIDTH - MOUSE_BORDER_LEFT

FLOOR_COLOR = (30, 30, 30)

FOV = math.pi / 3
HALF_FOV = FOV / 2
# 160 raios com SCALE=3 cobrem os 480 px sem faixas. Cada raio gera um
# transform.scale; reduzir de 320 para 160 foi o maior ganho no H3.
NUM_RAYS = WIDTH // 3
HALF_NUM_RAYS = NUM_RAYS // 2
DELTA_ANGLE = FOV / NUM_RAYS
MAX_DEPTH = 20

SCREEN_DIST = HALF_WIDTH / math.tan(HALF_FOV)
SCALE = WIDTH // NUM_RAYS

# Textura menor também reduz o custo de subsurface/scale por coluna.
TEXTURE_SIZE = 128
HALF_TEXTURE_SIZE = TEXTURE_SIZE // 2