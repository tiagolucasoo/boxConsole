#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Menu principal do BoxConsole em Pygame.

O catálogo de jogos continua vindo de ``console_ui.py`` (modo terminal), para
que os dois menus mostrem exatamente os mesmos jogos.

Capas:
    Coloque imagens em ``images/<id>.png`` (ou .jpg, .jpeg, .webp, .bmp).
    Enquanto não houver imagem, o espaço fica em branco, com uma dica discreta
    do caminho do arquivo.
"""

from __future__ import annotations

import os
import platform
import subprocess
import sys
import time
import traceback
from collections import defaultdict
from pathlib import Path

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame

import console_ui as catalog
import diagnostics
import game_host

# ---------------------------------------------------------------------------
# Constantes visuais
# ---------------------------------------------------------------------------

VW, VH = 1280, 720
FPS = 30
# Sem eventos, o laço praticamente não redesenha. 5 Hz é suficiente para
# expirar avisos e detectar joystick sem gastar CPU no H3.
IDLE_FPS = 5
COVERS_DIR = Path(catalog.BASE_DIR) / "covers"
IMAGE_DIRS = (
    Path(catalog.BASE_DIR) / "images",
    COVERS_DIR,
    Path(catalog.BASE_DIR) / "imagens",
)

TEXT = (238, 242, 252)
MUTED = (150, 159, 180)
FAINT = (92, 101, 124)
PANEL = (24, 28, 40)
PANEL_2 = (32, 37, 51)
PANEL_3 = (40, 46, 63)
BORDER = (58, 66, 88)
CYAN = (95, 215, 240)
MAGENTA = (225, 115, 235)
GOLD = (255, 200, 95)
GREEN = (110, 225, 150)
RED = (255, 105, 115)
YELLOW = (255, 210, 90)

COVER_EXTS = (".png", ".jpg", ".jpeg", ".jfif", ".webp", ".bmp")

# Alguns arquivos usam nomes "naturais" em vez do id do catálogo.
COVER_ALIASES = {
    "game2048": ("game2048", "2048"),
    "pacman": ("pacman", "pac-man"),
    "pong": ("pong", "pingpong"),
    "speed": ("speed", "speed-racer", "speedracer", "corrida"),
}

# Efeitos do menu. Os arquivos podem ficar na raiz ou em ``sounds/``.
# WAV vem primeiro: no ARMv7/TV box o SDL_mixer costuma abrir WAV sem
# depender de codecs extras. MP3/OGG continuam aceitos como fallback.
SOUND_EXTS = (".wav", ".ogg", ".mp3", ".flac")
SOUND_DIRS = (Path(catalog.BASE_DIR) / "sounds", Path(catalog.BASE_DIR))
SOUND_STEMS = {
    "hover": ("sound-hover", "hover"),
    "select": ("sound-click", "click", "select"),
    "return": ("sound-return", "return"),
}
HOVER_VOLUME = 0.8
SELECT_VOLUME = 0.55
RETURN_VOLUME = 0.7


def iter_menu_sounds(kind: str):
    """Lista os candidatos na ordem de preferência, sem repetir caminhos."""
    seen: set[Path] = set()
    for folder in SOUND_DIRS:
        for stem in SOUND_STEMS[kind]:
            for ext in SOUND_EXTS:
                candidate = folder / f"{stem}{ext}"
                if candidate in seen:
                    continue
                seen.add(candidate)
                if candidate.is_file():
                    yield candidate


def find_menu_sound(kind: str) -> Path | None:
    """Localiza um efeito do menu, aceitando variações de nome/formato."""
    return next(iter_menu_sounds(kind), None)

ANSI_COLORS = {
    catalog.Fore.RED: (255, 96, 96),
    catalog.Fore.YELLOW: (255, 214, 90),
    catalog.Fore.GREEN: (110, 220, 140),
    catalog.Fore.CYAN: (80, 210, 230),
    catalog.Fore.MAGENTA: (225, 110, 230),
    catalog.Fore.LIGHTRED_EX: (255, 120, 130),
    catalog.Fore.LIGHTGREEN_EX: (120, 235, 150),
    catalog.Fore.LIGHTYELLOW_EX: (255, 226, 120),
    catalog.Fore.LIGHTBLUE_EX: (110, 170, 255),
    catalog.Fore.LIGHTCYAN_EX: (120, 225, 245),
    catalog.Fore.LIGHTMAGENTA_EX: (235, 140, 245),
    catalog.Fore.LIGHTWHITE_EX: (240, 244, 255),
}

_font_cache: dict[tuple[int, bool], pygame.font.Font] = {}
_text_cache: dict[tuple[str, int, tuple, bool], pygame.Surface] = {}
_wrap_cache: dict[tuple[str, int, int], list[str]] = {}
_ellipsis_cache: dict[tuple[str, int, int], str] = {}
_CACHE_LIMIT = 512


def get_font(size: int, bold: bool = False) -> pygame.font.Font:
    key = (size, bold)
    if key not in _font_cache:
        _font_cache[key] = pygame.font.SysFont(
            "segoeui,arial,dejavusans,liberationsans", size, bold=bold
        )
    return _font_cache[key]


def clear_text_caches() -> None:
    _text_cache.clear()
    _wrap_cache.clear()
    _ellipsis_cache.clear()


def draw_text(surface, text, size, color, pos, anchor="topleft", bold=False):
    """Desenha texto reaproveitando a superfície renderizada."""
    key = (str(text), size, tuple(color), bool(bold))
    image = _text_cache.get(key)
    if image is None:
        image = get_font(size, bold).render(str(text), True, color)
        if len(_text_cache) >= _CACHE_LIMIT:
            _text_cache.clear()
        _text_cache[key] = image
    rect = image.get_rect(**{anchor: pos})
    surface.blit(image, rect)
    return rect


def wrap_text(text: str, font: pygame.font.Font, max_width: int) -> list[str]:
    key = (str(text), id(font), max_width)
    cached = _wrap_cache.get(key)
    if cached is not None:
        return cached
    words = str(text).split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = word if not current else f"{current} {word}"
        if font.size(candidate)[0] <= max_width or not current:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    result = lines or [""]
    if len(_wrap_cache) >= _CACHE_LIMIT:
        _wrap_cache.clear()
    _wrap_cache[key] = result
    return result


def ellipsize(text: str, font: pygame.font.Font, max_width: int) -> str:
    key = (str(text), id(font), max_width)
    cached = _ellipsis_cache.get(key)
    if cached is not None:
        return cached
    value = str(text)
    if font.size(value)[0] <= max_width:
        result = value
    else:
        ellipsis = "…"
        while value and font.size(value + ellipsis)[0] > max_width:
            value = value[:-1]
        result = value + ellipsis
    if len(_ellipsis_cache) >= _CACHE_LIMIT:
        _ellipsis_cache.clear()
    _ellipsis_cache[key] = result
    return result


def mix(a, b, t: float):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def accent_of(game: dict):
    return ANSI_COLORS.get(game.get("cor"), CYAN)


def status_of(game: dict) -> tuple[str, tuple[int, int, int]]:
    if not catalog.game_available(game):
        return "AUSENTE", RED
    if catalog.missing_deps(game):
        return "FALTA DEP", YELLOW
    return "PRONTO", GREEN


def draw_pill(surface, text, x, y, color, size=16, anchor_left=True):
    font = get_font(size, True)
    width = font.size(text)[0] + 26
    height = 32
    rect = pygame.Rect(0, 0, width, height)
    if anchor_left:
        rect.topleft = (x, y)
    else:
        rect.topright = (x, y)
    pygame.draw.rect(surface, mix(color, PANEL, 0.82), rect, border_radius=16)
    pygame.draw.rect(surface, color, rect, 1, border_radius=16)
    draw_text(surface, text, size, color, rect.center, anchor="center", bold=True)
    return rect


# ---------------------------------------------------------------------------
# Aplicação
# ---------------------------------------------------------------------------

class Launcher:
    def __init__(self, fullscreen: bool = True) -> None:
        # Em aparelhos ARM antigos o mixer padrão (44.1 kHz estéreo) consome
        # CPU demais e compete com o desenho dos jogos. Mono com buffer maior
        # reduz falhas de áudio e travadas.
        pygame.mixer.pre_init(44100, -16, 1, 1024)
        pygame.init()
        pygame.key.set_repeat(250, 85)
        pygame.joystick.init()

        self.clock = pygame.time.Clock()
        self.fullscreen = fullscreen
        self.screen: pygame.Surface | None = None
        self.canvas: pygame.Surface | None = None
        self.bg: pygame.Surface | None = None
        self._dim: pygame.Surface | None = None
        self._game_chrome: pygame.Surface | None = None
        self._game_chrome_key: tuple | None = None

        self.selected = 0
        self.mode = "menu"  # menu | details | system
        self.details_focus = 0
        self.details_message = ""
        self.running = True
        # Só redesenha quando algo muda (tecla, mouse, joystick, aviso).
        self.dirty = True
        self._menu_cache: pygame.Surface | None = None
        self._menu_cache_key: tuple | None = None
        self._status_version = 0
        self._scaled_canvas: pygame.Surface | None = None
        self._scaled_canvas_size = (0, 0)
        self._game_scaled: pygame.Surface | None = None
        self._game_scaled_size = (0, 0)

        self.toast = ""
        self.toast_until = 0.0
        self.mouse_pos = (-200, -200)

        self.cover_cache: dict[tuple[str, tuple[int, int]], pygame.Surface | None] = {}
        self.cover_source_cache: dict[Path, pygame.Surface | None] = {}
        self.cover_path_cache: dict[str, Path | None] = {}
        self.cover_index: dict[str, Path] | None = None
        self.status = {game["id"]: status_of(game) for game in catalog.GAMES}

        self.joysticks: list[pygame.joystick.Joystick] = []
        self.axis_last: dict[tuple[int, int], float] = defaultdict(float)

        self.card_rects: list[tuple[int, pygame.Rect]] = []
        self.cover_rect = pygame.Rect(0, 0, 0, 0)
        self.detail_buttons: dict[int, pygame.Rect] = {}
        self.back_rect = pygame.Rect(0, 0, 0, 0)

        self.hover_sound: pygame.mixer.Sound | None = None
        self.select_sound: pygame.mixer.Sound | None = None
        self.return_sound: pygame.mixer.Sound | None = None
        self._hover_channel = None
        self._select_channel = None
        self._return_channel = None
        self._quitting = False

        self.create_display()
        self.init_audio()
        self.init_joysticks()

    # ------------------------------------------------------------------
    # Display
    # ------------------------------------------------------------------

    def create_display(self) -> None:
        pygame.display.set_caption("BoxConsole — Jogos Arcade")
        # Desenha sempre em 1280x720. O aparelho/TV faz o upscale para a
        # resolução nativa, evitando um smoothscale de tela cheia por frame,
        # que é o principal gargalo em ARMv7 com pouca RAM.
        if self.fullscreen:
            try:
                self.screen = pygame.display.set_mode((VW, VH), pygame.FULLSCREEN)
            except pygame.error:
                info = pygame.display.Info()
                width = max(640, info.current_w or 1280)
                height = max(480, info.current_h or 720)
                self.screen = pygame.display.set_mode((width, height), pygame.FULLSCREEN)
        else:
            self.screen = pygame.display.set_mode((VW, VH), pygame.RESIZABLE)

        pygame.mouse.set_visible(True)
        self._real_flip = pygame.display.flip
        _font_cache.clear()
        clear_text_caches()
        self.canvas = pygame.Surface((VW, VH)).convert()
        self.bg = self.build_background()
        # As capas são superfícies independentes do display. Mantê-las no
        # cache evita redecodificar tudo ao alternar F11 tela cheia/janela.
        self._dim = None
        self._game_chrome = None
        self._game_chrome_key = None
        self._menu_cache = None
        self._menu_cache_key = None
        self._scaled_canvas = None
        self._scaled_canvas_size = (0, 0)
        self._game_scaled = None
        self._game_scaled_size = (0, 0)
        self.dirty = True
        self.preload_covers()

    def build_background(self) -> pygame.Surface:
        surface = pygame.Surface((VW, VH)).convert()
        for y in range(VH):
            t = y / max(1, VH - 1)
            color = (
                int(9 + 10 * t),
                int(12 + 8 * t),
                int(23 + 16 * t),
            )
            pygame.draw.line(surface, color, (0, y), (VW, y))

        glow = pygame.Surface((VW, VH), pygame.SRCALPHA)
        for center, radius, color in (
            ((1080, 40), 390, (50, 180, 255, 16)),
            ((1080, 40), 250, (50, 180, 255, 14)),
            ((170, 690), 420, (220, 80, 255, 14)),
            ((660, 360), 520, (20, 100, 160, 10)),
        ):
            pygame.draw.circle(glow, color, center, radius)
        surface.blit(glow, (0, 0))

        grid = pygame.Surface((VW, VH), pygame.SRCALPHA)
        for x in range(0, VW, 64):
            pygame.draw.line(grid, (255, 255, 255, 6), (x, 0), (x, VH))
        for y in range(0, VH, 64):
            pygame.draw.line(grid, (255, 255, 255, 6), (0, y), (VW, y))
        surface.blit(grid, (0, 0))
        return surface

    def init_joysticks(self) -> None:
        self.joysticks = []
        try:
            for index in range(pygame.joystick.get_count()):
                stick = pygame.joystick.Joystick(index)
                stick.init()
                self.joysticks.append(stick)
        except Exception:
            self.joysticks = []

    # ------------------------------------------------------------------
    # Sons do menu
    # ------------------------------------------------------------------

    def init_audio(self) -> None:
        """Carrega os efeitos; sem áudio o menu continua funcionando em silêncio."""
        self.hover_sound = None
        self.select_sound = None
        self.return_sound = None
        self._hover_channel = None
        self._select_channel = None
        self._return_channel = None
        self._quitting = False
        self.audio_error = ""

        # Alguns aparelhos só aceitam 22050 Hz mono ou precisam de buffer
        # maior. Tenta as combinações mais comuns antes de desistir.
        if not pygame.mixer.get_init():
            for args in (
                (44100, -16, 2, 512),
                (44100, -16, 2, 1024),
                (22050, -16, 1, 512),
            ):
                try:
                    pygame.mixer.init(*args)
                    if pygame.mixer.get_init():
                        break
                except Exception as exc:
                    self.audio_error = str(exc)

        if not pygame.mixer.get_init():
            return

        try:
            pygame.mixer.set_num_channels(8)
        except Exception:
            pass

        for kind, attribute, volume in (
            ("hover", "hover_sound", HOVER_VOLUME),
            ("select", "select_sound", SELECT_VOLUME),
            ("return", "return_sound", RETURN_VOLUME),
        ):
            # Tenta WAV primeiro, depois OGG/MP3. Se um formato falhar no
            # SDL_mixer do TV box, o próximo candidato ainda é tentado.
            for path in iter_menu_sounds(kind):
                try:
                    sound = pygame.mixer.Sound(str(path))
                    sound.set_volume(volume)
                    setattr(self, attribute, sound)
                    break
                except Exception as exc:
                    self.audio_error = f"{path.name}: {exc}"
                    continue

    def stop_menu_sounds(self) -> None:
        for channel_name in ("_hover_channel", "_select_channel", "_return_channel"):
            channel = getattr(self, channel_name)
            if channel is not None:
                try:
                    channel.stop()
                except Exception:
                    pass
                setattr(self, channel_name, None)

    def play_hover(self) -> None:
        if not self.hover_sound:
            return
        channel = getattr(self, "_hover_channel")
        if channel is not None:
            try:
                channel.stop()
            except Exception:
                pass
        try:
            self._hover_channel = self.hover_sound.play()
        except Exception:
            self._hover_channel = None

    def play_select(self) -> None:
        self.stop_menu_sounds()
        if not self.select_sound:
            return
        try:
            self._select_channel = self.select_sound.play()
        except Exception:
            self._select_channel = None

    def play_return(self) -> None:
        """Toca o som de encerramento e espera o efeito terminar."""
        self.stop_menu_sounds()
        if not self.return_sound:
            return
        try:
            self._return_channel = self.return_sound.play()
            if self._return_channel is not None:
                # pygame.quit() cortaria o áudio se saíssemos imediatamente.
                pygame.time.wait(int(self.return_sound.get_length() * 1000) + 60)
        except Exception:
            pass
        self._return_channel = None

    def request_exit(self) -> None:
        if self._quitting:
            return
        self._quitting = True
        self.running = False
        self.play_return()

    def real_scale(self) -> float:
        if not self.screen:
            return 1.0
        sw, sh = self.screen.get_size()
        return min(sw / VW, sh / VH) or 1.0

    def to_virtual(self, pos) -> tuple[float, float]:
        if not self.screen:
            return pos
        sw, sh = self.screen.get_size()
        scale = self.real_scale()
        ow, oh = VW * scale, VH * scale
        ox, oy = (sw - ow) / 2, (sh - oh) / 2
        return ((pos[0] - ox) / scale, (pos[1] - oy) / scale)

    def from_virtual(self, pos) -> tuple[float, float]:
        if not self.screen:
            return pos
        sw, sh = self.screen.get_size()
        scale = self.real_scale()
        ow, oh = VW * scale, VH * scale
        ox, oy = (sw - ow) / 2, (sh - oh) / 2
        return (ox + pos[0] * scale, oy + pos[1] * scale)

    def present(self) -> None:
        if not self.screen or not self.canvas:
            return
        sw, sh = self.screen.get_size()
        scale = self.real_scale()
        ow, oh = max(1, int(VW * scale)), max(1, int(VH * scale))
        ox, oy = (sw - ow) // 2, (sh - oh) // 2
        if (ow, oh) == (sw, sh):
            # Caminho rápido: resolução igual à do canvas, sem escala.
            self.screen.blit(self.canvas, (0, 0))
        else:
            self.screen.fill((0, 0, 0))
            # Nearest neighbor é muito mais barato que smoothscale no ARM.
            # Reaproveita a superfície de destino para não alocar por frame.
            if self._scaled_canvas_size != (ow, oh) or self._scaled_canvas is None:
                self._scaled_canvas = pygame.Surface((ow, oh)).convert()
                self._scaled_canvas_size = (ow, oh)
            try:
                pygame.transform.scale(self.canvas, (ow, oh), self._scaled_canvas)
                scaled = self._scaled_canvas
            except TypeError:
                scaled = pygame.transform.scale(self.canvas, (ow, oh))
                self._scaled_canvas = scaled
            self.screen.blit(scaled, (ox, oy))
        self._real_flip()

    def toggle_fullscreen(self) -> None:
        self.fullscreen = not self.fullscreen
        self.create_display()
        self.toast = "Tela cheia" if self.fullscreen else "Modo janela"
        self.toast_until = time.monotonic() + 1.8

    # ------------------------------------------------------------------
    # Capas
    # ------------------------------------------------------------------

    def _build_cover_index(self) -> None:
        """Indexa as capas uma vez; evita varrer pastas a cada tamanho."""
        index: dict[str, Path] = {}
        for directory in IMAGE_DIRS:
            if not directory.is_dir():
                continue
            try:
                for path in directory.iterdir():
                    if path.is_file() and path.suffix.lower() in COVER_EXTS:
                        index.setdefault(path.stem.lower(), path)
            except OSError:
                continue
        self.cover_index = index

    def find_cover(self, game_id: str) -> Path | None:
        if game_id in self.cover_path_cache:
            return self.cover_path_cache[game_id]
        if self.cover_index is None:
            self._build_cover_index()
        assert self.cover_index is not None
        found = None
        for name in COVER_ALIASES.get(game_id, (game_id,)):
            found = self.cover_index.get(name.lower())
            if found is not None:
                break
        self.cover_path_cache[game_id] = found
        return found

    def preload_covers(self) -> None:
        """Pré-carrega as capas visíveis e as miniaturas do carrossel."""
        for game in catalog.GAMES:
            for size in ((520, 292), (156, 88)):
                try:
                    self.get_cover(game["id"], size)
                except Exception:
                    pass

    def _cover_source(self, path: Path) -> pygame.Surface | None:
        if path in self.cover_source_cache:
            return self.cover_source_cache[path]
        try:
            image = pygame.image.load(str(path))
            # JPEG/BMP não têm transparência; convert_alpha() só desperdiça
            # memória e tempo nesses formatos.
            if path.suffix.lower() in (".png", ".webp"):
                image = image.convert_alpha()
            else:
                image = image.convert()
        except Exception:
            image = None
        self.cover_source_cache[path] = image
        return image

    def get_cover(self, game_id: str, size: tuple[int, int]) -> pygame.Surface | None:
        size = (max(1, int(size[0])), max(1, int(size[1])))
        key = (game_id, size)
        if key in self.cover_cache:
            return self.cover_cache[key]

        path = self.find_cover(game_id)
        if not path:
            self.cover_cache[key] = None
            return None

        source = self._cover_source(path)
        if source is None:
            self.cover_cache[key] = None
            return None

        try:
            iw, ih = source.get_size()
            # Mostra a arte inteira (sem cortar). Se não for 16:9, sobram
            # faixas discretas na cor do painel.
            scale = min(size[0] / iw, size[1] / ih)
            nw, nh = max(1, int(iw * scale + 0.5)), max(1, int(ih * scale + 0.5))
            scaled = pygame.transform.smoothscale(source, (nw, nh))
            fitted = pygame.Surface(size).convert()
            fitted.fill((20, 24, 35))
            fitted.blit(scaled, ((size[0] - nw) // 2, (size[1] - nh) // 2))
            image: pygame.Surface | None = fitted
        except Exception:
            image = None

        self.cover_cache[key] = image
        return image

    def draw_cover(self, game: dict, rect: pygame.Rect, accent, big: bool = False) -> None:
        assert self.canvas is not None
        image = self.get_cover(game["id"], rect.size)
        if image:
            self.canvas.blit(image, rect.topleft)
            pygame.draw.rect(self.canvas, mix(accent, (255, 255, 255), 0.25), rect, 2, border_radius=12)
        else:
            pygame.draw.rect(self.canvas, (20, 24, 35), rect, border_radius=12)
            pygame.draw.rect(self.canvas, (48, 56, 76), rect, 1, border_radius=12)
            if big:
                draw_text(
                    self.canvas,
                    f"images/{game['id']}.png",
                    14,
                    (62, 70, 92),
                    (rect.centerx, rect.bottom - 18),
                    anchor="center",
                )

    # ------------------------------------------------------------------
    # Desenho: componentes
    # ------------------------------------------------------------------

    def draw_header(self, game: dict | None = None, surface=None) -> None:
        if surface is None:
            surface = self.canvas
        assert surface is not None
        box = get_font(52, True).render("Box", True, CYAN)
        console = get_font(52, True).render("Console", True, MAGENTA)
        surface.blit(box, (62, 26))
        surface.blit(console, (62 + box.get_width(), 26))

        draw_text(surface, "JOGOS ARCADE", 17, MUTED, (66, 88), bold=True)

        if game is not None:
            accent = accent_of(game)
            draw_text(
                surface,
                "JOGANDO AGORA",
                13,
                FAINT,
                (VW - 64, 32),
                anchor="topright",
                bold=True,
            )
            name_font = get_font(26, True)
            name = ellipsize(game["nome"], name_font, 470)
            draw_text(
                surface,
                name,
                26,
                accent,
                (VW - 64, 50),
                anchor="topright",
                bold=True,
            )
            draw_text(
                surface,
                "F12 volta ao menu  ·  o jogo roda dentro do frame",
                13,
                MUTED,
                (VW - 64, 86),
                anchor="topright",
            )
        else:
            draw_text(
                surface,
                f"{len(catalog.GAMES):02d} JOGOS",
                19,
                MUTED,
                (VW - 64, 38),
                anchor="topright",
                bold=True,
            )
            draw_text(
                surface,
                "PYGAME EDITION  ·  v1.5",
                14,
                FAINT,
                (VW - 64, 66),
                anchor="topright",
                bold=True,
            )
        pygame.draw.line(surface, (46, 54, 75), (64, 122), (VW - 64, 122), 2)

    def _draw_game_footer(self, surface, accent, button) -> None:
        draw_text(
            surface,
            "Jogo embutido no BoxConsole  ·  use o menu do jogo ou VOLTAR",
            15,
            MUTED,
            (64, 682),
        )
        pygame.draw.rect(surface, PANEL_2, button, border_radius=9)
        pygame.draw.rect(surface, accent, button, 1, border_radius=9)
        draw_text(
            surface,
            "VOLTAR  (F12)",
            15,
            accent,
            button.center,
            anchor="center",
            bold=True,
        )
        self.draw_credit(surface)

    def draw_game_frame(self, game: dict, host) -> None:
        """Desenha o jogo embutido dentro do frame do BoxConsole."""
        assert self.canvas is not None and self.bg is not None
        surface = self.canvas
        accent = accent_of(game)
        area = pygame.Rect(160, 130, 960, 540)
        button = pygame.Rect(VW - 64 - 190, 674, 190, 32)
        host.exit_button_rect = button

        game_surface = host.virtual_surface
        if game_surface is None:
            # Só acontece enquanto o jogo carrega; não precisa de cache.
            surface.blit(self.bg, (0, 0))
            self.draw_header(game)
            pygame.draw.rect(surface, (8, 11, 18), area, border_radius=14)
            pygame.draw.rect(surface, (48, 56, 76), area, 1, border_radius=14)
            host.game_rect = area
            draw_text(
                surface,
                f"Carregando {game['nome']}...",
                22,
                MUTED,
                area.center,
                anchor="center",
                bold=True,
            )
            self._draw_game_footer(surface, accent, button)
            self.present()
            return

        sw, sh = game_surface.get_size()
        scale = min(area.w / max(1, sw), area.h / max(1, sh))
        gw = max(1, int(sw * scale))
        gh = max(1, int(sh * scale))
        game_rect = pygame.Rect(0, 0, gw, gh)

        # Jogos retratos (Flappy, Sudoku, 2048, Tetris) deixavam faixas
        # escuras enormes. Em vez de centralizar, usamos a lateral direita
        # para uma ficha compacta do jogo.
        panel_rect: pygame.Rect | None = None
        if gw <= gh and area.w - gw > 180:
            game_rect.left = area.left + 24
            game_rect.centery = area.centery
            panel_x = game_rect.right + 28
            panel_rect = pygame.Rect(
                panel_x,
                area.top + 24,
                max(1, area.right - panel_x - 24),
                area.height - 48,
            )
        else:
            game_rect.center = area.center

        # O cabeçalho, a moldura e o rodapé são iguais em todos os frames.
        # Monta uma única vez e só blita o jogo por cima; evita renderizar
        # textos e formas de tela cheia a cada frame do jogo.
        key = (game["id"], sw, sh, gw, gh, tuple(panel_rect) if panel_rect else None)
        if key != self._game_chrome_key or self._game_chrome is None:
            chrome = pygame.Surface((VW, VH)).convert()
            chrome.blit(self.bg, (0, 0))
            self.draw_header(game, chrome)
            pygame.draw.rect(chrome, (8, 11, 18), area, border_radius=14)
            pygame.draw.rect(chrome, (48, 56, 76), area, 1, border_radius=14)
            if panel_rect is not None:
                self._draw_portrait_panel(chrome, game, accent, panel_rect)
            self._draw_game_footer(chrome, accent, button)
            self._game_chrome = chrome
            self._game_chrome_key = key

        surface.blit(self._game_chrome, (0, 0))
        if (gw, gh) == (sw, sh):
            scaled = game_surface
        else:
            # Nearest neighbor: essencial para jogos pequenos rodando em
            # ARMv7. Reaproveita a superfície de destino a cada frame.
            if self._game_scaled_size != (gw, gh) or self._game_scaled is None:
                self._game_scaled = pygame.Surface((gw, gh)).convert()
                self._game_scaled_size = (gw, gh)
            try:
                pygame.transform.scale(game_surface, (gw, gh), self._game_scaled)
                scaled = self._game_scaled
            except TypeError:
                scaled = pygame.transform.scale(game_surface, (gw, gh))
                self._game_scaled = scaled
        surface.blit(scaled, game_rect.topleft)
        pygame.draw.rect(surface, accent, game_rect, 2, border_radius=8)
        host.game_rect = game_rect
        self.present()

    def _draw_portrait_panel(self, surface, game: dict, accent, rect: pygame.Rect) -> None:
        """Ficha lateral para jogos retratos, no lugar de faixas vazias."""
        pygame.draw.rect(surface, PANEL, rect, border_radius=14)
        pygame.draw.rect(surface, mix(accent, BORDER, 0.45), rect, 1, border_radius=14)

        x = rect.x + 22
        width = max(1, rect.width - 44)
        y = rect.y + 20
        draw_text(surface, "FORMATO RETRATO", 13, FAINT, (x, y), bold=True)
        y += 25
        draw_text(
            surface,
            ellipsize(game["nome"], get_font(25, True), width),
            25,
            TEXT,
            (x, y),
            bold=True,
        )
        y += 36
        meta = f"{game['genero']}  ·  {game['players']}"
        draw_text(surface, ellipsize(meta, get_font(14), width), 14, MUTED, (x, y))
        y += 30

        description_font = get_font(16)
        for line in wrap_text(game["descricao"], description_font, width)[:3]:
            draw_text(surface, line, 16, MUTED, (x, y))
            y += 21

        y += 12
        draw_text(surface, "CONTROLES", 13, FAINT, (x, y), bold=True)
        y += 24
        for keys, action in game.get("controles", [])[:5]:
            key_text = ellipsize(str(keys), get_font(15, True), 150)
            draw_text(surface, key_text, 15, accent, (x, y), bold=True)
            draw_text(
                surface,
                ellipsize(action, get_font(15), width - 170),
                15,
                TEXT,
                (x + 160, y),
            )
            y += 24

        hint_y = rect.bottom - 28
        if y < hint_y:
            draw_text(
                surface,
                "F12 ou VOLTAR encerra o jogo",
                13,
                FAINT,
                (x, hint_y),
            )

    def draw_credit(self, surface=None) -> None:
        """Crédito do projeto, discreto no rodapé de todas as telas do menu."""
        if surface is None:
            surface = self.canvas
        assert surface is not None
        text = (
            f"{catalog.PROJECT_CREDIT} · projeto open source: "
            f"{catalog.PROJECT_URL}"
        )
        font = get_font(12)
        draw_text(
            surface,
            ellipsize(text, font, VW - 96),
            12,
            MUTED,
            (VW // 2, 704),
            anchor="midtop",
        )

    def draw_hints(self, items, y: int = 686) -> None:
        assert self.canvas is not None
        surface = self.canvas
        key_font = get_font(14, True)
        label_font = get_font(16)
        gap = 26
        widths = []
        for key, label in items:
            widths.append(key_font.size(key)[0] + 20 + 8 + label_font.size(label)[0])
        total = sum(widths) + gap * max(0, len(items) - 1)
        x = max(28.0, (VW - total) / 2)

        for (key, label), width in zip(items, widths):
            key_width = key_font.size(key)[0] + 20
            key_rect = pygame.Rect(int(x), y - 13, key_width, 26)
            pygame.draw.rect(surface, (33, 39, 55), key_rect, border_radius=6)
            pygame.draw.rect(surface, (61, 70, 93), key_rect, 1, border_radius=6)
            draw_text(surface, key, 14, TEXT, key_rect.center, anchor="center", bold=True)
            draw_text(
                surface,
                label,
                16,
                MUTED,
                (x + key_width + 8, y - 9),
            )
            x += width + gap

    def draw_toast(self, y: int = 655) -> None:
        if not self.toast or time.monotonic() >= self.toast_until:
            return
        assert self.canvas is not None
        font = get_font(17, True)
        width = min(VW - 120, font.size(self.toast)[0] + 44)
        rect = pygame.Rect(0, 0, width, 36)
        rect.center = (VW // 2, y)
        pygame.draw.rect(self.canvas, (36, 42, 58), rect, border_radius=10)
        pygame.draw.rect(self.canvas, GOLD, rect, 1, border_radius=10)
        draw_text(
            self.canvas,
            ellipsize(self.toast, font, width - 24),
            17,
            TEXT,
            rect.center,
            anchor="center",
            bold=True,
        )

    # ------------------------------------------------------------------
    # Desenho: menu
    # ------------------------------------------------------------------

    def draw_menu(self, show_hints: bool = True, show_toast: bool = True) -> None:
        assert self.canvas is not None and self.bg is not None
        key = (self.selected, bool(show_hints), self._status_version)
        if self._menu_cache is not None and self._menu_cache_key == key:
            self.canvas.blit(self._menu_cache, (0, 0))
        else:
            self._draw_menu_uncached(show_hints)
            self._menu_cache = self.canvas.copy()
            self._menu_cache_key = key
        if show_toast:
            self.draw_toast()

    def _draw_menu_uncached(self, show_hints: bool) -> None:
        assert self.canvas is not None and self.bg is not None
        surface = self.canvas
        surface.blit(self.bg, (0, 0))
        self.draw_header()

        game = catalog.GAMES[self.selected]
        accent = accent_of(game)
        status_text, status_color = self.status[game["id"]]

        cover = pygame.Rect(64, 148, 520, 292)
        self.cover_rect = cover
        self.draw_cover(game, cover, accent, big=True)

        x = 616
        top = 148
        draw_pill(surface, game["genero"], x, top, accent, size=15)
        draw_pill(surface, status_text, VW - 64, top, status_color, size=15, anchor_left=False)

        title_font = get_font(44, True)
        title_width = VW - 64 - x - 170
        title = ellipsize(game["nome"], title_font, title_width)
        draw_text(surface, title, 44, TEXT, (x, 190), bold=True)

        description_font = get_font(21)
        description = wrap_text(game["descricao"], description_font, VW - 64 - x)
        y = 250
        for line in description[:3]:
            draw_text(surface, line, 21, (196, 204, 220), (x, y))
            y += 27

        y = max(y + 14, 342)
        draw_text(surface, "CONTROLES", 14, FAINT, (x, y), bold=True)
        y += 24
        for keys, action in game["controles"][:3]:
            draw_text(surface, keys, 17, accent, (x, y), bold=True)
            draw_text(surface, action, 17, TEXT, (x + 182, y))
            y += 24

        self.draw_carousel()
        if show_hints:
            self.draw_hints(
                [
                    ("← →", "navegar"),
                    ("ENTER", "detalhes"),
                    ("J", "jogar"),
                    ("D", "diagnóstico"),
                    ("F11", "tela cheia"),
                    ("ESC", "sair"),
                ]
            )

    def draw_carousel(self) -> None:
        assert self.canvas is not None
        surface = self.canvas
        total = len(catalog.GAMES)
        visible = 6
        start = max(0, min(self.selected - 2, total - visible))
        self.card_rects = []

        draw_text(surface, "BIBLIOTECA", 14, FAINT, (80, 466), bold=True)
        draw_text(
            surface,
            f"{self.selected + 1:02d} / {total:02d}",
            14,
            MUTED,
            (VW - 80, 466),
            anchor="topright",
            bold=True,
        )

        if start > 0:
            draw_text(surface, "‹", 44, MUTED, (64, 552), anchor="center", bold=True)
        if start + visible < total:
            draw_text(surface, "›", 44, MUTED, (VW - 64, 552), anchor="center", bold=True)

        card_w, card_h, gap = 172, 138, 14
        x0 = (VW - (visible * card_w + (visible - 1) * gap)) // 2
        y0 = 492

        for slot in range(min(visible, total)):
            index = start + slot
            game = catalog.GAMES[index]
            accent = accent_of(game)
            x = x0 + slot * (card_w + gap)
            y = y0 - (6 if index == self.selected else 0)
            rect = pygame.Rect(x, y, card_w, card_h)
            self.card_rects.append((index, rect))

            selected = index == self.selected
            pygame.draw.rect(
                surface,
                PANEL_2 if selected else PANEL,
                rect,
                border_radius=12,
            )
            pygame.draw.rect(
                surface,
                accent if selected else BORDER,
                rect,
                2 if selected else 1,
                border_radius=12,
            )

            thumb = pygame.Rect(x + 8, y + 8, card_w - 16, 88)
            self.draw_cover(game, thumb, accent, big=False)

            name_font = get_font(16, True)
            name = ellipsize(game["nome"], name_font, card_w - 16)
            draw_text(
                surface,
                name,
                16,
                accent if selected else TEXT,
                (x + 8, y + 104),
                bold=True,
            )
            draw_text(
                surface,
                f"{index + 1:02d}",
                12,
                FAINT,
                (x + 8, y + 122),
                bold=True,
            )

    # ------------------------------------------------------------------
    # Desenho: detalhes
    # ------------------------------------------------------------------

    def get_dim(self) -> pygame.Surface:
        """Overlay escuro reaproveitado; criar isso a cada frame custa caro."""
        if self._dim is None:
            self._dim = pygame.Surface((VW, VH), pygame.SRCALPHA)
            self._dim.fill((4, 6, 11, 192))
        return self._dim

    def draw_details(self) -> None:
        assert self.canvas is not None
        self.draw_menu(show_hints=False, show_toast=False)

        self.canvas.blit(self.get_dim(), (0, 0))

        game = catalog.GAMES[self.selected]
        accent = accent_of(game)
        status_text, status_color = self.status[game["id"]]
        surface = self.canvas

        modal = pygame.Rect(80, 44, 1120, 632)
        pygame.draw.rect(surface, (18, 21, 31), modal, border_radius=20)
        pygame.draw.rect(surface, accent, modal, 2, border_radius=20)
        pygame.draw.line(surface, accent, (112, 48), (VW - 112, 48), 3)

        draw_text(
            surface,
            "ESC  voltar",
            14,
            FAINT,
            (VW - 112, 68),
            anchor="topright",
            bold=True,
        )

        cover = pygame.Rect(112, 84, 450, 253)
        self.draw_cover(game, cover, accent, big=True)

        left_y = 360
        draw_text(
            surface,
            "FICHA TÉCNICA",
            14,
            FAINT,
            (112, left_y),
            bold=True,
        )
        left_y += 26
        draw_text(
            surface,
            f"Stack: {' · '.join(game['stack'])}",
            16,
            MUTED,
            (112, left_y),
        )
        left_y += 24
        draw_text(surface, f"Licença: {game['licenca']}", 16, MUTED, (112, left_y))
        left_y += 24
        author = ellipsize(f"Autor: {game['autor']}", get_font(16), 450)
        draw_text(surface, author, 16, MUTED, (112, left_y))
        left_y += 24
        draw_text(
            surface,
            f"Jogadores: {game['players']}",
            16,
            MUTED,
            (112, left_y),
        )
        left_y += 24
        perfil = game.get("perfil") or {}
        resolucao = perfil.get("res")
        fps = perfil.get("fps")
        perfil_text = f"Perfil: {resolucao[0]}x{resolucao[1]}" if resolucao else "Perfil: adaptativo"
        if fps:
            perfil_text += f" · {fps} FPS"
        draw_text(surface, perfil_text, 16, MUTED, (112, left_y))
        left_y += 24
        embedded = game_host.GameHost.can_embed(game)
        draw_text(
            surface,
            "Execução: frame embutido" if embedded else "Execução: janela própria",
            16,
            GREEN if embedded else YELLOW,
            (112, left_y),
            bold=True,
        )

        x = 610
        title_font = get_font(38, True)
        title = ellipsize(game["nome"], title_font, 550)
        draw_text(surface, title, 38, TEXT, (x, 82), bold=True)

        draw_pill(surface, game["genero"], x, 138, accent, size=14)
        draw_pill(surface, status_text, VW - 112, 138, status_color, size=14, anchor_left=False)

        draw_text(surface, "VISÃO GERAL", 14, FAINT, (x, 190), bold=True)
        description_font = get_font(20)
        y = 212
        for line in wrap_text(game["descricao"], description_font, 558)[:3]:
            draw_text(surface, line, 20, (200, 208, 224), (x, y))
            y += 25

        draw_text(surface, "CONTROLES", 14, FAINT, (x, 306), bold=True)
        y = 330
        for keys, action in game["controles"][:4]:
            draw_text(surface, keys, 17, accent, (x, y), bold=True)
            draw_text(surface, action, 17, TEXT, (x + 182, y))
            y += 25

        draw_text(surface, "DEPENDÊNCIAS", 14, FAINT, (x, 456), bold=True)
        dep_x = x
        for dep in game["deps"]:
            color = GREEN if catalog.module_available(dep) else YELLOW
            width = get_font(16, True).size(dep)[0] + 38
            chip = pygame.Rect(dep_x, 478, width, 26)
            pygame.draw.rect(surface, mix(color, PANEL, 0.84), chip, border_radius=8)
            pygame.draw.rect(surface, color, chip, 1, border_radius=8)
            pygame.draw.circle(surface, color, (chip.left + 14, chip.centery), 4)
            draw_text(
                surface,
                dep,
                16,
                color,
                (chip.left + 25, chip.centery),
                anchor="midleft",
                bold=True,
            )
            dep_x += width + 8

        missing = catalog.missing_deps(game)
        if missing:
            pip_list = " ".join(catalog.PIP_NAMES.get(dep, dep) for dep in missing)
            draw_text(
                surface,
                f"Instale: python -m pip install {pip_list}",
                15,
                YELLOW,
                (x, 508),
            )

        draw_text(surface, "REPOSITÓRIO ORIGINAL", 14, FAINT, (x, 528), bold=True)
        repo = game.get("repo")
        repo_text = game.get("repo_texto")
        if repo:
            repo_value = ellipsize(repo, get_font(16), 558)
            repo_color = CYAN
        elif repo_text:
            repo_value = repo_text
            repo_color = YELLOW
        else:
            repo_value = "a ser adicionado (preencha \"repo\")"
            repo_color = FAINT
        draw_text(surface, repo_value, 16, repo_color, (x, 550))

        if self.details_message:
            draw_text(
                surface,
                ellipsize(self.details_message, get_font(15), 558),
                15,
                GOLD,
                (x, 574),
            )

        buttons = [
            (0, "JOGAR"),
            (1, "REPOSITÓRIO"),
            (2, "VOLTAR"),
        ]
        button_w, button_h, gap = 180, 48, 18
        total_w = len(buttons) * button_w + (len(buttons) - 1) * gap
        bx = (VW - total_w) // 2
        by = 596
        self.detail_buttons = {}
        for focus, label in buttons:
            rect = pygame.Rect(bx, by, button_w, button_h)
            self.detail_buttons[focus] = rect
            focused = self.details_focus == focus
            pygame.draw.rect(
                surface,
                accent if focused else PANEL_2,
                rect,
                border_radius=12,
            )
            pygame.draw.rect(
                surface,
                mix(accent, (255, 255, 255), 0.35) if focused else BORDER,
                rect,
                2 if focused else 1,
                border_radius=12,
            )
            draw_text(
                surface,
                label,
                18,
                (16, 19, 28) if focused else TEXT,
                rect.center,
                anchor="center",
                bold=True,
            )
            bx += button_w + gap

        self.draw_hints(
            [("← →", "escolher"), ("ENTER", "confirmar"), ("R", "repositório"), ("ESC", "voltar")],
            y=690,
        )

    # ------------------------------------------------------------------
    # Desenho: sistema
    # ------------------------------------------------------------------

    def draw_system(self) -> None:
        assert self.canvas is not None
        self.draw_menu(show_hints=False, show_toast=False)

        self.canvas.blit(self.get_dim(), (0, 0))

        surface = self.canvas
        modal = pygame.Rect(80, 44, 1120, 632)
        pygame.draw.rect(surface, (18, 21, 31), modal, border_radius=20)
        pygame.draw.rect(surface, CYAN, modal, 2, border_radius=20)
        pygame.draw.line(surface, CYAN, (112, 48), (VW - 112, 48), 3)

        draw_text(surface, "SISTEMA & DIAGNÓSTICO", 34, TEXT, (112, 78), bold=True)
        draw_text(surface, "AMBIENTE", 14, FAINT, (112, 132), bold=True)

        python_version = (
            f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        )
        arch = "64-bit" if sys.maxsize > 2**32 else "32-bit"
        env_lines = [
            f"Python {python_version} ({arch})",
            f"{platform.system()} {platform.release()}  ·  {platform.machine()}",
            f"BoxConsole em {catalog.BASE_DIR}",
        ]
        mixer_info = pygame.mixer.get_init()
        if mixer_info:
            loaded_effects = sum(
                1 for sound in (self.hover_sound, self.select_sound, self.return_sound) if sound
            )
            env_lines.append(
                f"Áudio: mixer {mixer_info[0]} Hz, {mixer_info[2]} canal(is)"
                f"  ·  efeitos {loaded_effects}/3"
            )
        else:
            env_lines.append("Áudio: mixer indisponível (menu segue em silêncio)")
        env_y = 158
        for line in env_lines:
            draw_text(surface, ellipsize(line, get_font(18), 1050), 18, MUTED, (112, env_y))
            env_y += 24

        # As posições abaixo são calculadas a partir das linhas de ambiente.
        # Antes eram fixas e a quarta linha/última coluna invadiam os títulos.
        status_title_y = env_y + 6
        draw_text(surface, "STATUS DOS JOGOS", 14, FAINT, (112, status_title_y), bold=True)
        half = (len(catalog.GAMES) + 1) // 2
        column_width = 470
        status_top = status_title_y + 30
        row_step = min(30, max(22, (512 - status_top) // max(1, half)))
        for column in range(2):
            x = 112 + column * (column_width + 46)
            for row, index in enumerate(
                range(column * half, min((column + 1) * half, len(catalog.GAMES)))
            ):
                row_y = status_top + row * row_step
                game = catalog.GAMES[index]
                entry = self.status.get(game["id"])
                if entry is None:
                    entry = status_of(game)
                status_text, status_color = entry
                draw_text(
                    surface,
                    ellipsize(game["nome"], get_font(18), column_width - 150),
                    18,
                    TEXT,
                    (x, row_y),
                )
                draw_text(
                    surface,
                    status_text,
                    15,
                    status_color,
                    (x + column_width, row_y + 2),
                    anchor="topright",
                    bold=True,
                )

        draw_text(surface, "BIBLIOTECAS", 14, FAINT, (112, 520), bold=True)
        draw_text(
            surface,
            "verde = instalada   ·   amarelo = ausente",
            13,
            FAINT,
            (VW - 112, 520),
            anchor="topright",
        )
        all_deps = []
        for game in catalog.GAMES:
            for dep in game["deps"]:
                if dep not in all_deps:
                    all_deps.append(dep)

        dep_x = 112
        dep_y = 546
        for dep in all_deps:
            installed = catalog.module_available(dep)
            color = GREEN if installed else YELLOW
            width = get_font(16, True).size(dep)[0] + 38
            if dep_x + width > VW - 112:
                dep_x = 112
                dep_y += 32
            chip = pygame.Rect(dep_x, dep_y, width, 26)
            pygame.draw.rect(surface, mix(color, PANEL, 0.84), chip, border_radius=8)
            pygame.draw.rect(surface, color, chip, 1, border_radius=8)
            pygame.draw.circle(surface, color, (chip.left + 14, chip.centery), 4)
            draw_text(
                surface,
                dep,
                16,
                color,
                (chip.left + 25, chip.centery),
                anchor="midleft",
                bold=True,
            )
            dep_x += width + 8

        back = pygame.Rect(0, 0, 200, 46)
        back.center = (VW // 2, 622)
        self.back_rect = back
        pygame.draw.rect(surface, CYAN, back, border_radius=12)
        draw_text(surface, "VOLTAR", 18, (16, 19, 28), back.center, anchor="center", bold=True)

        self.draw_hints([("ESC", "voltar"), ("ENTER", "voltar")], y=690)

    # ------------------------------------------------------------------
    # Eventos
    # ------------------------------------------------------------------

    def navigate(self, delta: int) -> None:
        if self.mode == "menu":
            previous = self.selected
            self.selected = (self.selected + delta) % len(catalog.GAMES)
            if self.selected != previous:
                self.play_hover()
                self.dirty = True
        elif self.mode == "details":
            previous = self.details_focus
            self.details_focus = (self.details_focus + delta) % 3
            if self.details_focus != previous:
                self.dirty = True

    def confirm(self) -> None:
        self.dirty = True
        if self.mode == "menu":
            self.play_select()
            self.mode = "details"
            self.details_focus = 0
            self.details_message = ""
        elif self.mode == "details":
            if self.details_focus == 0:
                self.launch_game(catalog.GAMES[self.selected])
            elif self.details_focus == 1:
                self.open_repo(catalog.GAMES[self.selected])
            else:
                self.stop_menu_sounds()
                self.mode = "menu"
        else:
            self.stop_menu_sounds()
            self.mode = "menu"

    def back(self) -> None:
        if self.mode == "menu":
            self.request_exit()
        else:
            self.stop_menu_sounds()
            self.mode = "menu"
            self.details_message = ""
            self.dirty = True

    def open_repo(self, game: dict) -> None:
        self.details_message = catalog.open_repository(game)
        self.dirty = True

    def refresh_status(self) -> None:
        catalog.clear_module_cache()
        self.status = {game["id"]: status_of(game) for game in catalog.GAMES}
        self._status_version += 1
        self.dirty = True

    def launch_game(self, game: dict) -> None:
        self.stop_menu_sounds()
        if not catalog.game_available(game):
            self.mode = "details"
            self.details_focus = 0
            self.details_message = (
                "Jogo indisponível: confira a pasta e o arquivo de entrada."
            )
            return

        missing = catalog.missing_deps(game)
        if missing:
            pip_list = " ".join(catalog.PIP_NAMES.get(dep, dep) for dep in missing)
            self.mode = "details"
            self.details_focus = 0
            self.details_message = f"Instale: python -m pip install {pip_list}"
            return

        if game_host.GameHost.can_embed(game):
            self.launch_embedded(game)
        else:
            self.launch_external(game)

    def launch_embedded(self, game: dict, max_frames: int | None = None) -> None:
        """Roda o jogo na mesma janela, dentro do frame do BoxConsole."""
        host = game_host.GameHost(self, game, max_frames=max_frames)
        message = ""
        fallback = False

        try:
            message = host.run()
        except game_host.EmbeddingUnsupported:
            fallback = True
        except KeyboardInterrupt:
            raise
        except Exception as exc:
            traceback.print_exc()
            diagnostics.log(f"Erro no jogo embutido {game['id']}", exc_info=True)
            if host.frames_rendered <= 1:
                fallback = True
            else:
                message = f"Erro em {game['nome']}: {exc}"
        finally:
            try:
                pygame.font.init()
            except Exception:
                pass
            _font_cache.clear()
            pygame.key.set_repeat(250, 85)
            pygame.display.set_caption("BoxConsole — Jogos Arcade")
            pygame.mouse.set_visible(True)
            try:
                pygame.event.set_grab(False)
            except Exception:
                pass
            try:
                pygame.joystick.init()
                self.init_joysticks()
            except Exception:
                self.joysticks = []
            pygame.event.clear()
            # O jogo pode ter parado/reinicializado o mixer; recarrega os sons
            # do menu para que continuem válidos ao voltar.
            self.init_audio()
            # Libera as superfícies de moldura/frame do jogo; elas não são
            # necessárias no menu e podem ocupar vários MB no H3.
            self._game_chrome = None
            self._game_chrome_key = None
            self._game_scaled = None
            self._game_scaled_size = (0, 0)

        if fallback:
            self.toast = (
                f"{game['nome']}: modo embutido indisponível; abrindo em janela."
            )
            self.toast_until = time.monotonic() + 2.5
            self.launch_external(game)
            return

        self.mode = "menu"
        self.details_message = ""
        self.toast = message or f"{game['nome']} encerrado."
        self.toast_until = time.monotonic() + 3.5
        self._menu_cache = None
        self._menu_cache_key = None
        self.dirty = True

    def launch_external(self, game: dict) -> None:
        """Modo reserva: abre o jogo em uma janela/console próprio."""
        modulo = game.get("modulo")
        if modulo:
            cmd = [sys.executable, "-m", modulo]
            cwd = str(catalog.BASE_DIR)
        else:
            cmd = [sys.executable, game["entry"]]
            cwd = str(catalog.game_dir(game))

        child_env = os.environ.copy()
        child_env.setdefault("PYTHONIOENCODING", "utf-8")

        creationflags = 0
        if os.name == "nt" and "Terminal" in game.get("stack", []):
            creationflags = subprocess.CREATE_NEW_CONSOLE

        pygame.event.clear()
        pygame.display.quit()
        # Aqui o display é realmente encerrado (diferente do F11), então as
        # superfícies convertidas podem ficar inválidas. Recarrega do zero.
        self.cover_cache.clear()
        self.cover_source_cache.clear()

        message = ""
        try:
            proc = subprocess.run(
                cmd,
                cwd=cwd,
                env=child_env,
                creationflags=creationflags,
            )
            if proc.returncode == 0:
                message = f"{game['nome']} encerrado."
            else:
                message = f"{game['nome']} encerrado com código {proc.returncode}."
        except KeyboardInterrupt:
            message = "Jogo interrompido."
        except Exception as exc:
            diagnostics.log(f"Erro ao iniciar externamente {game['id']}", exc_info=True)
            message = f"Erro ao iniciar {game['nome']}: {exc}"

        pygame.display.init()
        try:
            self.create_display()
        except Exception:
            self.running = False
            return

        self.mode = "menu"
        self.toast = message
        self.toast_until = time.monotonic() + 3.5
        self._menu_cache = None
        self._menu_cache_key = None
        self.dirty = True

    def handle_events(self, first_event=None) -> None:
        events = []
        if first_event is not None and first_event.type != pygame.NOEVENT:
            events.append(first_event)
        events.extend(pygame.event.get())
        # Apenas eventos que podem alterar o desenho acordam o laço. Movimento
        # de mouse e ruído do analógico não devem manter o menu a 30 FPS.
        immediate_redraw = {
            pygame.QUIT,
            pygame.VIDEORESIZE,
            pygame.MOUSEBUTTONDOWN,
            pygame.MOUSEWHEEL,
            pygame.JOYBUTTONDOWN,
            pygame.JOYHATMOTION,
        }
        for event in events:
            if event.type in immediate_redraw:
                self.dirty = True
            if event.type == pygame.QUIT:
                self.request_exit()
                return

            elif event.type == pygame.VIDEORESIZE and not self.fullscreen:
                self.screen = pygame.display.set_mode(event.size, pygame.RESIZABLE)

            elif event.type == pygame.KEYDOWN:
                # Segurar Enter/Espaço não pode abrir a ficha e iniciar o jogo
                # no mesmo instante por causa da repetição automática.
                if getattr(event, "repeat", False) and event.key in (
                    pygame.K_RETURN,
                    pygame.K_KP_ENTER,
                    pygame.K_SPACE,
                    pygame.K_j,
                    pygame.K_r,
                    pygame.K_d,
                    pygame.K_F11,
                    pygame.K_ESCAPE,
                    pygame.K_BACKSPACE,
                    pygame.K_q,
                ):
                    continue

                self.dirty = True
                if event.key == pygame.K_F11:
                    self.toggle_fullscreen()
                    continue

                if self.mode == "menu":
                    # No menu, A/D ficam de fora para não conflitar com o
                    # atalho D de diagnóstico; setas e W/S continuam valendo.
                    if event.key in (pygame.K_LEFT, pygame.K_UP, pygame.K_w):
                        self.navigate(-1)
                    elif event.key in (pygame.K_RIGHT, pygame.K_DOWN, pygame.K_s):
                        self.navigate(1)
                    elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                        self.confirm()
                    elif event.key == pygame.K_j:
                        self.launch_game(catalog.GAMES[self.selected])
                    elif event.key == pygame.K_d:
                        self.refresh_status()
                        self.mode = "system"
                    elif event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE, pygame.K_q):
                        self.request_exit()
                        return
                    elif event.unicode.isdigit():
                        number = int(event.unicode)
                        if number == 0 and len(catalog.GAMES) >= 10:
                            self.selected = 9
                        elif 1 <= number <= len(catalog.GAMES):
                            self.selected = number - 1
                        else:
                            continue
                        self.mode = "details"
                        self.details_focus = 0
                        self.details_message = ""
                        self.play_select()

                elif self.mode == "details":
                    if event.key in (pygame.K_LEFT, pygame.K_UP, pygame.K_a, pygame.K_w):
                        self.navigate(-1)
                    elif event.key in (pygame.K_RIGHT, pygame.K_DOWN, pygame.K_d, pygame.K_s):
                        self.navigate(1)
                    elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                        self.confirm()
                    elif event.key == pygame.K_j:
                        self.launch_game(catalog.GAMES[self.selected])
                    elif event.key == pygame.K_r:
                        self.open_repo(catalog.GAMES[self.selected])
                    elif event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE, pygame.K_v, pygame.K_q):
                        self.back()

                else:  # system
                    if event.key in (
                        pygame.K_ESCAPE,
                        pygame.K_BACKSPACE,
                        pygame.K_RETURN,
                        pygame.K_KP_ENTER,
                        pygame.K_v,
                        pygame.K_q,
                        pygame.K_SPACE,
                    ):
                        self.mode = "menu"

            elif event.type == pygame.MOUSEMOTION:
                self.mouse_pos = self.to_virtual(event.pos)
                if self.mode == "menu":
                    for index, rect in self.card_rects:
                        if rect.collidepoint(self.mouse_pos):
                            if index != self.selected:
                                self.selected = index
                                self.play_hover()
                                self.dirty = True
                            break
                elif self.mode == "details":
                    for focus, rect in self.detail_buttons.items():
                        if rect.collidepoint(self.mouse_pos):
                            if focus != self.details_focus:
                                self.details_focus = focus
                                self.dirty = True
                            break

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                pos = self.to_virtual(event.pos)
                if self.mode == "menu":
                    clicked = False
                    for index, rect in self.card_rects:
                        if rect.collidepoint(pos):
                            if index == self.selected:
                                self.play_select()
                                self.mode = "details"
                                self.details_focus = 0
                                self.details_message = ""
                            else:
                                self.selected = index
                                self.play_hover()
                            clicked = True
                            break
                    if not clicked and self.cover_rect.collidepoint(pos):
                        self.play_select()
                        self.mode = "details"
                        self.details_focus = 0
                        self.details_message = ""
                elif self.mode == "details":
                    for focus, rect in self.detail_buttons.items():
                        if rect.collidepoint(pos):
                            self.details_focus = focus
                            self.confirm()
                            break
                else:
                    if self.back_rect.collidepoint(pos):
                        self.mode = "menu"

            elif event.type == pygame.MOUSEWHEEL and self.mode == "menu":
                self.navigate(-1 if event.y > 0 else 1)

            elif event.type == pygame.JOYBUTTONDOWN:
                if event.button == 0:
                    self.confirm()
                elif event.button in (1, 2):
                    self.back()

            elif event.type == pygame.JOYHATMOTION:
                x, y = event.value
                if x < 0 or y > 0:
                    self.navigate(-1)
                elif x > 0 or y < 0:
                    self.navigate(1)

            elif event.type == pygame.JOYAXISMOTION:
                if event.axis in (0, 1) and abs(event.value) > 0.6:
                    direction = 1 if event.value > 0 else -1
                    key = (event.axis, direction)
                    now = time.monotonic()
                    if now - self.axis_last[key] > 0.18:
                        self.axis_last[key] = now
                        if event.axis == 0:
                            self.navigate(direction)
                        else:
                            self.navigate(direction)

    # ------------------------------------------------------------------
    # Loop
    # ------------------------------------------------------------------

    def draw(self) -> None:
        if self.mode == "menu":
            self.draw_menu()
        elif self.mode == "details":
            self.draw_details()
        else:
            self.draw_system()
        self.draw_credit()
        self.present()

    def run(self) -> None:
        while self.running:
            if self.dirty:
                self.handle_events()
            else:
                # Sem redesenho pendente, dorme até um evento chegar. Assim o
                # menu fica em ~0% de CPU sem atrasar as teclas do controle.
                first = pygame.event.wait(int(1000 / IDLE_FPS))
                self.handle_events(first)

            if not self.running:
                break
            if self.toast and time.monotonic() >= self.toast_until:
                self.toast = ""
                self.dirty = True
            if self.dirty:
                self.draw()
                self.dirty = False
                self.clock.tick(FPS)


def main(fullscreen: bool = True) -> None:
    app = Launcher(fullscreen=fullscreen)
    try:
        app.run()
    finally:
        app.stop_menu_sounds()
        pygame.quit()


if __name__ == "__main__":
    main(fullscreen="--windowed" not in sys.argv)
