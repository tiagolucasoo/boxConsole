import os
import pygame
from csv import reader


# Mapas são recriados nas transições, mas tiles, sprites e efeitos são os
# mesmos. Sem este cache cada transição decodificava novamente centenas de
# PNGs e criava cópias de áudio desnecessárias.
_image_cache = {}
_folder_cache = {}
_sound_cache = {}


def get_path(path):
    absolute_path = os.path.dirname(__file__)
    full_path = os.path.join(absolute_path, path)

    return full_path


def import_csv_layout(path: str) -> list:
    unique_path = get_path(path)
    terrain_map = []
    with open(unique_path) as level_map:
        layout = reader(level_map, delimiter=',')
        for row in layout:
            terrain_map.append(list(row))
        return terrain_map


def import_folder(path: str) -> list:
    unique_path = get_path(path)
    cached = _folder_cache.get(unique_path)
    if cached is not None:
        return cached

    surface_list = []

    for root, _, img_files in os.walk(unique_path):
        for image in sorted(img_files):
            full_path = os.path.join(root, image)
            surface_list.append(load_image(full_path))

    # As superfícies não são modificadas pelos sprites; compartilhar a lista
    # elimina recarga de disco e picos de memória ao mudar de mapa.
    _folder_cache[unique_path] = surface_list
    return surface_list


def load_image(path: str, alpha: bool = True) -> pygame.Surface:
    """Carrega uma imagem uma vez e devolve a Surface compartilhada."""
    absolute_path = os.path.normcase(os.path.abspath(path))
    key = (absolute_path, alpha)
    image = _image_cache.get(key)
    if image is None:
        image = pygame.image.load(absolute_path)
        image = image.convert_alpha() if alpha else image.convert()
        _image_cache[key] = image
    return image


def load_sound(path: str) -> pygame.mixer.Sound:
    """Evita decodificar o mesmo efeito uma vez para cada inimigo."""
    absolute_path = os.path.normcase(os.path.abspath(path))
    sound = _sound_cache.get(absolute_path)
    if sound is None:
        sound = pygame.mixer.Sound(absolute_path)
        _sound_cache[absolute_path] = sound
    return sound
