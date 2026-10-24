#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Executa um jogo Pygame dentro da janela do BoxConsole.

A ideia: o jogo continua sendo um programa independente, mas em vez de criar
outra janela, ``pygame.display.set_mode`` é redirecionado para uma superfície
virtual. O host desenha o frame do BoxConsole e encaixa essa superfície na área
do jogo. Flip/update, mouse e eventos são traduzidos para as coordenadas da
superfície virtual.

Jogos que não são Pygame (como o Pac-Man, que roda no terminal) continuam no
modo externo. Jogos que abrem janelas próprias de outra biblioteca também são
enviados para o modo externo.
"""

from __future__ import annotations

import gc
import os
import runpy
import sys
import types
from pathlib import Path

import pygame

import console_ui as catalog


class EmbeddedExit(BaseException):
    """Sai do jogo embutido e volta ao menu (F12)."""


class EmbeddingUnsupported(Exception):
    """O jogo usa um recurso que não pode ser embutido (ex.: OpenGL)."""


class GameHost:
    """Hospeda um jogo Pygame dentro da área de jogo do launcher."""

    def __init__(self, launcher, game: dict, max_frames: int | None = None) -> None:
        self.launcher = launcher
        self.game = game
        self.max_frames = max_frames

        self.virtual_surface: pygame.Surface | None = None
        self.virtual_size = (960, 540)
        self.game_rect = pygame.Rect(0, 0, 0, 0)
        self.exit_button_rect = pygame.Rect(0, 0, 0, 0)
        self.frames_rendered = 0
        self.last_error = ""
        self.exit_reason = ""
        # Alguns jogos chamam pygame.display.flip() sem limitar o FPS. Sem
        # este teto, um jogo simples pode ocupar 100% da CPU do TV box.
        self._frame_clock = pygame.time.Clock()
        # Alguns jogos chamam update() e flip() no mesmo frame. Sem isso, o
        # host desenharia duas vezes e o relógio dormiria duas vezes.
        self._last_render_ms = -1000

        self.original: dict[str, object] = {}
        self.timers: set[int] = set()
        self._rendering = False
        self._installed = False

    @staticmethod
    def can_embed(game: dict) -> bool:
        """True para jogos que desenham em Pygame e podem ir para o frame."""
        if not game.get("embed", True):
            return False
        return "Terminal" not in game.get("stack", [])

    # ------------------------------------------------------------------
    # Ciclo de vida
    # ------------------------------------------------------------------

    def run(self) -> str:
        self.install()
        try:
            # Eventos pendentes do menu (clique em JOGAR, teclas, QUIT) não
            # podem vazar para o jogo.
            pygame.event.clear()
            self.draw_loading()
            self.execute_game()
            return f"{self.game['nome']} encerrado."
        except EmbeddedExit as exc:
            self.exit_reason = str(exc)
            return "Voltou ao menu."
        except SystemExit:
            return f"{self.game['nome']} encerrado."
        finally:
            self.uninstall()

    def install(self) -> None:
        self.original = {
            "set_mode": pygame.display.set_mode,
            "get_surface": pygame.display.get_surface,
            "flip": pygame.display.flip,
            "update": pygame.display.update,
            "toggle_fullscreen": pygame.display.toggle_fullscreen,
            "display_quit": pygame.display.quit,
            "display_info": pygame.display.Info,
            "set_caption": pygame.display.set_caption,
            "set_icon": pygame.display.set_icon,
            "pygame_quit": pygame.quit,
            "event_get": pygame.event.get,
            "event_poll": pygame.event.poll,
            "event_wait": pygame.event.wait,
            "mouse_get_pos": pygame.mouse.get_pos,
            "mouse_get_rel": pygame.mouse.get_rel,
            "mouse_set_pos": pygame.mouse.set_pos,
            "set_timer": pygame.time.set_timer,
        }
        if hasattr(pygame.display, "get_window_size"):
            self.original["get_window_size"] = pygame.display.get_window_size

        # O launcher usa repetição de teclas no menu; dentro do jogo ela
        # atrapalharia os controles. Desliga e restaura no final.
        pygame.key.set_repeat()
        self._installed = True

        pygame.display.set_mode = self._set_mode  # type: ignore[assignment]
        pygame.display.get_surface = self._get_surface  # type: ignore[assignment]
        pygame.display.flip = self._flip  # type: ignore[assignment]
        pygame.display.update = self._update  # type: ignore[assignment]
        pygame.display.toggle_fullscreen = self._noop  # type: ignore[assignment]
        pygame.display.quit = self._noop  # type: ignore[assignment]
        pygame.display.Info = self._info  # type: ignore[assignment]
        pygame.display.set_caption = self._noop  # type: ignore[assignment]
        pygame.display.set_icon = self._noop  # type: ignore[assignment]
        pygame.quit = self._noop  # type: ignore[assignment]
        pygame.event.get = self._event_get  # type: ignore[assignment]
        pygame.event.poll = self._event_poll  # type: ignore[assignment]
        pygame.event.wait = self._event_wait  # type: ignore[assignment]
        pygame.mouse.get_pos = self._mouse_get_pos  # type: ignore[assignment]
        pygame.mouse.get_rel = self._mouse_get_rel  # type: ignore[assignment]
        pygame.mouse.set_pos = self._mouse_set_pos  # type: ignore[assignment]
        pygame.time.set_timer = self._set_timer  # type: ignore[assignment]
        if "get_window_size" in self.original:
            pygame.display.get_window_size = self._get_window_size  # type: ignore[assignment]

    def uninstall(self) -> None:
        if not self._installed:
            return

        for name, function in self.original.items():
            if name == "get_window_size":
                if hasattr(pygame.display, "get_window_size"):
                    pygame.display.get_window_size = function  # type: ignore[assignment]
                continue
            if name == "display_info":
                pygame.display.Info = function  # type: ignore[assignment]
                continue
            if name == "display_quit":
                pygame.display.quit = function  # type: ignore[assignment]
                continue
            if name == "set_caption":
                pygame.display.set_caption = function  # type: ignore[assignment]
                continue
            if name == "set_icon":
                pygame.display.set_icon = function  # type: ignore[assignment]
                continue
            if name == "pygame_quit":
                pygame.quit = function  # type: ignore[assignment]
                continue
            if name == "set_timer":
                pygame.time.set_timer = function  # type: ignore[assignment]
                continue

            target = {
                "set_mode": pygame.display,
                "get_surface": pygame.display,
                "flip": pygame.display,
                "update": pygame.display,
                "toggle_fullscreen": pygame.display,
                "event_get": pygame.event,
                "event_poll": pygame.event,
                "event_wait": pygame.event,
                "mouse_get_pos": pygame.mouse,
                "mouse_get_rel": pygame.mouse,
                "mouse_set_pos": pygame.mouse,
            }.get(name)
            attribute = {
                "set_mode": "set_mode",
                "get_surface": "get_surface",
                "flip": "flip",
                "update": "update",
                "toggle_fullscreen": "toggle_fullscreen",
                "event_get": "get",
                "event_poll": "poll",
                "event_wait": "wait",
                "mouse_get_pos": "get_pos",
                "mouse_get_rel": "get_rel",
                "mouse_set_pos": "set_pos",
            }.get(name)
            if target is not None and attribute:
                setattr(target, attribute, function)

        # Para timers criados pelo jogo (Doom, Flappy etc.).
        for event_type in self.timers:
            try:
                self.original["set_timer"](event_type, 0)  # type: ignore[operator]
            except Exception:
                pass

        try:
            pygame.mixer.music.stop()
            pygame.mixer.stop()
        except Exception:
            pass

        try:
            pygame.event.set_grab(False)
        except Exception:
            pass
        try:
            pygame.event.set_allowed(None)
        except Exception:
            pass
        try:
            pygame.mouse.set_visible(True)
        except Exception:
            pass
        try:
            pygame.font.init()
        except Exception:
            pass

        pygame.display.set_caption("BoxConsole — Jogos Arcade")
        pygame.key.set_repeat(250, 85)
        pygame.event.clear()

        # Libera a superfície virtual e os módulos carregados pelo jogo antes
        # de voltar ao menu. Em 1 GB de RAM isso evita fragmentação a cada
        # ciclo abrir/fechar jogo.
        self.virtual_surface = None
        self.virtual_size = (960, 540)
        gc.collect()

        self._installed = False

    # ------------------------------------------------------------------
    # Display virtual
    # ------------------------------------------------------------------

    def _set_mode(self, size=(0, 0), flags=0, depth=0, *args, **kwargs):
        if flags & pygame.OPENGL:
            raise EmbeddingUnsupported("O jogo pede uma janela OpenGL.")
        try:
            width, height = int(size[0]), int(size[1])
        except Exception:
            width, height = 960, 540
        if width <= 0 or height <= 0:
            width, height = 960, 540

        self.virtual_size = (width, height)
        self.virtual_surface = pygame.Surface((width, height)).convert()
        self.virtual_surface.fill((0, 0, 0))
        return self.virtual_surface

    def _get_surface(self):
        if self.virtual_surface is None:
            return self._set_mode((960, 540))
        return self.virtual_surface

    def _get_window_size(self):
        return self.virtual_size

    def _info(self):
        real = self.original["display_info"]()  # type: ignore[operator]
        info = types.SimpleNamespace()
        for name in dir(real):
            if name.startswith("_"):
                continue
            try:
                setattr(info, name, getattr(real, name))
            except Exception:
                pass
        info.current_w, info.current_h = self.virtual_size
        return info

    def _flip(self):
        self.render()

    def _update(self, *args, **kwargs):
        self.render()

    def _noop(self, *args, **kwargs):
        return None

    def draw_loading(self) -> None:
        self.launcher.draw_game_frame(self.game, self)

    def render(self) -> None:
        if self._rendering:
            return
        now = pygame.time.get_ticks()
        # update() + flip() no mesmo frame: desenha apenas uma vez.
        if now - self._last_render_ms < 2:
            return
        self._last_render_ms = now
        self._rendering = True
        try:
            self.frames_rendered += 1
            if self.max_frames is not None and self.frames_rendered > self.max_frames:
                raise EmbeddedExit("max_frames")
            # Teto de 60 FPS. Jogos que já têm clock.tick(60) não são
            # afetados; jogos sem limite deixam de saturar a CPU.
            self._frame_clock.tick(60)
            self.launcher.draw_game_frame(self.game, self)
        finally:
            self._rendering = False

    # ------------------------------------------------------------------
    # Coordenadas
    # ------------------------------------------------------------------

    def _canvas_to_game(self, canvas_pos) -> tuple[int, int]:
        rect = self.game_rect
        if rect.w <= 0 or rect.h <= 0:
            return (0, 0)
        gx = (canvas_pos[0] - rect.x) * self.virtual_size[0] / rect.w
        gy = (canvas_pos[1] - rect.y) * self.virtual_size[1] / rect.h
        return (
            max(0, min(self.virtual_size[0] - 1, int(gx))),
            max(0, min(self.virtual_size[1] - 1, int(gy))),
        )

    def _real_to_game(self, real_pos) -> tuple[int, int]:
        return self._canvas_to_game(self.launcher.to_virtual(real_pos))

    def _game_to_real(self, game_pos) -> tuple[int, int]:
        rect = self.game_rect
        if rect.w <= 0 or rect.h <= 0:
            return (0, 0)
        canvas_x = rect.x + game_pos[0] * rect.w / self.virtual_size[0]
        canvas_y = rect.y + game_pos[1] * rect.h / self.virtual_size[1]
        return self.launcher.from_virtual((canvas_x, canvas_y))

    def _scale_delta(self, delta) -> tuple[int, int]:
        rect = self.game_rect
        if rect.w <= 0 or rect.h <= 0:
            return (0, 0)
        launcher_scale = self.launcher.real_scale()
        if launcher_scale <= 0:
            launcher_scale = 1.0
        sx = self.virtual_size[0] / (rect.w * launcher_scale)
        sy = self.virtual_size[1] / (rect.h * launcher_scale)
        return (int(delta[0] * sx), int(delta[1] * sy))

    # ------------------------------------------------------------------
    # Mouse e eventos
    # ------------------------------------------------------------------

    def _mouse_get_pos(self):
        return self._real_to_game(self.original["mouse_get_pos"]())  # type: ignore[operator]

    def _mouse_get_rel(self):
        delta = self.original["mouse_get_rel"]()  # type: ignore[operator]
        return self._scale_delta(delta)

    def _mouse_set_pos(self, pos):
        return self.original["mouse_set_pos"](self._game_to_real(pos))  # type: ignore[operator]

    def _transform_event(self, event):
        if event.type == pygame.NOEVENT:
            return event

        if event.type == pygame.KEYDOWN:
            is_f12 = event.key == pygame.K_F12
            is_ctrl_q = event.key == pygame.K_q and bool(
                getattr(event, "mod", 0) & pygame.KMOD_CTRL
            )
            if is_f12 or is_ctrl_q:
                raise EmbeddedExit("atalho de saida")

        if event.type in (
            pygame.MOUSEMOTION,
            pygame.MOUSEBUTTONDOWN,
            pygame.MOUSEBUTTONUP,
        ):
            if (
                event.type == pygame.MOUSEBUTTONDOWN
                and event.button == 1
                and self.exit_button_rect.w > 0
            ):
                canvas_pos = self.launcher.to_virtual(event.pos)
                if self.exit_button_rect.collidepoint(canvas_pos):
                    raise EmbeddedExit("botao voltar")

            data = dict(event.dict)
            data["pos"] = self._real_to_game(event.pos)
            if event.type == pygame.MOUSEMOTION:
                data["rel"] = self._scale_delta(event.rel)
            return pygame.event.Event(event.type, data)

        return event

    def _event_get(self, *args, **kwargs):
        events = self.original["event_get"](*args, **kwargs)  # type: ignore[operator]
        return [self._transform_event(event) for event in events]

    def _event_poll(self, *args, **kwargs):
        event = self.original["event_poll"](*args, **kwargs)  # type: ignore[operator]
        return self._transform_event(event)

    def _event_wait(self, *args, **kwargs):
        event = self.original["event_wait"](*args, **kwargs)  # type: ignore[operator]
        return self._transform_event(event)

    def _set_timer(self, event, millis, *args, **kwargs):
        if millis:
            if isinstance(event, int):
                self.timers.add(event)
            elif isinstance(event, (list, tuple)):
                self.timers.update(
                    item for item in event if isinstance(item, int)
                )
        return self.original["set_timer"](event, millis, *args, **kwargs)  # type: ignore[operator]

    # ------------------------------------------------------------------
    # Execução do jogo
    # ------------------------------------------------------------------

    def execute_game(self) -> None:
        entry = catalog.game_entry(self.game)
        modulo = self.game.get("modulo")
        # Jogos de módulo (ex.: pygame.examples.aliens) não têm pasta própria;
        # o cwd do processo externo é a raiz do BoxConsole.
        game_dir = Path(catalog.BASE_DIR) if modulo else Path(catalog.game_dir(self.game))

        old_cwd = os.getcwd()
        old_path = list(sys.path)
        old_argv = list(sys.argv)
        modules_before = set(sys.modules)

        try:
            os.chdir(game_dir)
            if entry:
                # O Python normal coloca a pasta do script no sys.path, não a
                # pasta do jogo. Alguns jogos têm o entry em subpasta (ex.:
                # PyZelda em code/main.py e imports em code/settings.py).
                script_dir = Path(entry).resolve().parent
                sys.path.insert(0, str(game_dir))
                sys.path.insert(0, str(script_dir))
            else:
                sys.path.insert(0, str(game_dir))
            sys.argv = [str(entry)] if entry else ["-m", str(modulo)]

            if modulo:
                runpy.run_module(str(modulo), run_name="__main__", alter_sys=True)
            else:
                runpy.run_path(str(entry), run_name="__main__")
        finally:
            os.chdir(old_cwd)
            sys.path[:] = old_path
            sys.argv = old_argv

            # Remove módulos locais carregados pelo jogo para não contaminar
            # o próximo jogo com nomes genéricos (settings, classes etc.).
            for name in set(sys.modules) - modules_before:
                module = sys.modules.get(name)
                filename = getattr(module, "__file__", None)
                if not filename:
                    continue
                try:
                    if Path(filename).resolve().is_relative_to(game_dir.resolve()):
                        del sys.modules[name]
                except Exception:
                    pass
