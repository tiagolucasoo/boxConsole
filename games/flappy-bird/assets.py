import os
import pygame

sprites = {}
audios = {}


def load_sprites():
    path = os.path.join("assets", "sprites")
    for file in os.listdir(path):
        name = file.split('.')[0]
        sprite = pygame.image.load(os.path.join(path, file))
        # Superfícies convertidas usam o formato da tela e são bem mais
        # rápidas de desenhar, especialmente em aparelhos ARM antigos.
        # Fundo e chão são opacos; usar convert() evita alpha blending.
        if name in ("background", "floor"):
            sprites[name] = sprite.convert()
        else:
            sprites[name] = sprite.convert_alpha()


def get_sprite(name):
    return sprites[name]


def load_audios():
    path = os.path.join("assets", "audios")
    for file in os.listdir(path):
        audios[file.split('.')[0]] = pygame.mixer.Sound(os.path.join(path, file))


def play_audio(name):
    audios[name].play()
