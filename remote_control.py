#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Controle remoto do BoxConsole pelo celular.

O servidor usa apenas a biblioteca padrão (``http.server``) e um punhado de
threads. Não há streaming de vídeo, WebSocket nem dependências extras: o
celular abre uma página leve, mostra o controle do jogo atual e envia os
toques por HTTP. Os eventos são injetados na fila do Pygame e o estado das
teclas também é mesclado em ``pygame.key.get_pressed``, para jogos que usam
consulta contínua (WASD/setas).

A porta padrão é 8765 e pode ser alterada por ``BOXCONSOLE_REMOTE_PORT``.
Para desligar o recurso, use ``BOXCONSOLE_REMOTE=0``.
"""

from __future__ import annotations

import json
import os
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

import pygame

BASE_DIR = Path(__file__).resolve().parent
VERSION = "1.0"
DEFAULT_PORT = 8765
MAX_BODY = 4096
RELEASE_AFTER = 5.0
DEBUG = os.environ.get("BOXCONSOLE_REMOTE_DEBUG", "") not in ("", "0", "false", "False")
HTML_PATH = BASE_DIR / "remote_ui.html"

# ---------------------------------------------------------------------------
# Perfis dos controles
# ---------------------------------------------------------------------------

KEY_LABELS = {"up": "▲", "down": "▼", "left": "◀", "right": "▶"}


def _key(action_id: str, label: str, key: str, role: str = "secondary", repeat: bool = False) -> dict:
    return {
        "id": action_id,
        "label": label,
        "key": key,
        "kind": "key",
        "role": role,
        "repeat": repeat,
    }


def _click(action_id: str, label: str, role: str = "a") -> dict:
    return {
        "id": action_id,
        "label": label,
        "kind": "click",
        "role": role,
        "repeat": False,
    }


def _turn(action_id: str, label: str, dx: int) -> dict:
    return {
        "id": action_id,
        "label": label,
        "kind": "turn",
        "dx": int(dx),
        "role": "secondary",
        "repeat": True,
    }


def _dpad(keys: dict, repeat=True) -> list[dict]:
    actions = []
    for name in ("up", "down", "left", "right"):
        if name not in keys:
            continue
        repeat_this = bool(repeat) if isinstance(repeat, bool) else name in repeat
        actions.append(
            _key(name, KEY_LABELS[name], keys[name], role=name, repeat=repeat_this)
        )
    return actions


def _profile(
    game_id: str,
    name: str,
    subtitle: str,
    hint: str,
    accent: str,
    dpad: list[dict],
    primary: list[dict],
    secondary: list[dict],
    numpad: bool = False,
) -> dict:
    return {
        "id": game_id,
        "name": name,
        "subtitle": subtitle,
        "hint": hint,
        "accent": accent,
        "dpad": dpad,
        "primary": primary,
        "secondary": secondary,
        "numpad": bool(numpad),
    }


PROFILES = {
    "menu": _profile(
        "menu",
        "BoxConsole",
        "Escolha um jogo",
        "Setas navegam · A abre a ficha · B volta",
        "#22d3ee",
        _dpad(
            {
                "up": "K_UP",
                "down": "K_DOWN",
                "left": "K_LEFT",
                "right": "K_RIGHT",
            },
            repeat=True,
        ),
        [
            _key("a", "ABRIR", "K_RETURN", "a"),
            _key("b", "VOLTAR", "K_ESCAPE", "b"),
            _key("x", "JOGAR", "K_j", "x"),
            _key("y", "DIAGN.", "K_d", "y"),
        ],
        [
            _key("full", "TELA CHEIA", "K_F11"),
        ],
    ),
    "doom": _profile(
        "doom",
        "Doom",
        "WASD + mira",
        "WASD move · A atira · use OLHAR para virar",
        "#fb7185",
        _dpad({"up": "K_w", "down": "K_s", "left": "K_a", "right": "K_d"}),
        [
            _click("a", "ATIRAR", "a"),
            _key("b", "SAIR", "K_ESCAPE", "b"),
        ],
        [
            _turn("look_l", "◀ OLHAR", -34),
            _turn("look_r", "OLHAR ▶", 34),
            _key("ok", "CONFIRMAR", "K_RETURN"),
        ],
    ),
    "flappy": _profile(
        "flappy",
        "Flappy Bird",
        "Um toque para voar",
        "Toque em VOAR · ESC reinicia depois do game over",
        "#fbbf24",
        [],
        [
            _key("a", "VOAR", "K_SPACE", "a"),
            _key("b", "ESC", "K_ESCAPE", "b"),
        ],
        [
            _key("quit", "SAIR", "K_q"),
        ],
    ),
    "pacman": _profile(
        "pacman",
        "Pac-Man",
        "Coma todos os pontos",
        "Setas movem · A confirma · B pausa",
        "#fde047",
        _dpad(
            {
                "up": "K_UP",
                "down": "K_DOWN",
                "left": "K_LEFT",
                "right": "K_RIGHT",
            }
        ),
        [
            _key("a", "INICIAR", "K_RETURN", "a"),
            _key("b", "PAUSA", "K_p", "b"),
        ],
        [
            _key("esc", "MENU", "K_ESCAPE"),
            _key("enter", "CONFIRMAR", "K_RETURN"),
        ],
    ),
    "street": _profile(
        "street",
        "Street Fighter",
        "Escolha o lutador e vença",
        "A/D move · W pula · A e B atacam · CONFIRMAR escolhe",
        "#fb923c",
        _dpad(
            {
                "up": "K_w",
                "down": "K_s",
                "left": "K_a",
                "right": "K_d",
            }
        ),
        [
            _key("a", "SOCO", "K_r", "a"),
            _key("b", "CHUTE", "K_t", "b"),
            _key("x", "CONFIRMAR", "K_RETURN", "x"),
            _key("y", "VOLTAR", "K_ESCAPE", "y"),
        ],
        [],
    ),
    "mario": _profile(
        "mario",
        "Super Mario",
        "Pule e corra",
        "Setas movem · A pula · B corre · CONFIRMAR no menu",
        "#38bdf8",
        _dpad(
            {
                "up": "K_UP",
                "down": "K_DOWN",
                "left": "K_LEFT",
                "right": "K_RIGHT",
            }
        ),
        [
            _key("a", "PULAR", "K_SPACE", "a"),
            _key("b", "CORRER", "K_LSHIFT", "b"),
        ],
        [
            _key("ok", "CONFIRMAR", "K_RETURN"),
            _key("esc", "VOLTAR", "K_ESCAPE"),
        ],
    ),
    "sonic": _profile(
        "sonic",
        "Sonic Game",
        "Pule para desviar",
        "A ou ▲ pula e inicia · B volta",
        "#06b6d4",
        _dpad(
            {
                "up": "K_UP",
                "down": "K_DOWN",
                "left": "K_LEFT",
                "right": "K_RIGHT",
            }
        ),
        [
            _key("a", "PULAR", "K_SPACE", "a"),
            _key("b", "VOLTAR", "K_ESCAPE", "b"),
            _key("x", "INICIAR", "K_RETURN", "x"),
        ],
        [
            _key("f12", "MENU CONSOLE", "K_F12"),
            _key("enter", "INICIAR", "K_RETURN"),
        ],
    ),
    "donkeyking": _profile(
        "donkeyking",
        "Donkey King",
        "Suba e desvie dos barris",
        "Setas sobem escadas · A pula",
        "#f87171",
        _dpad(
            {
                "up": "K_UP",
                "down": "K_DOWN",
                "left": "K_LEFT",
                "right": "K_RIGHT",
            }
        ),
        [
            _key("a", "PULAR", "K_SPACE", "a"),
            _key("b", "PULAR 2", "K_x", "b"),
        ],
        [],
    ),
    "zelda": _profile(
        "zelda",
        "PyZelda",
        "Aventura em Tiled",
        "Setas movem · A ataca · B magia · X/Y trocam",
        "#4ade80",
        _dpad(
            {
                "up": "K_UP",
                "down": "K_DOWN",
                "left": "K_LEFT",
                "right": "K_RIGHT",
            }
        ),
        [
            _key("a", "ATACAR", "K_SPACE", "a"),
            _key("b", "MAGIA", "K_LCTRL", "b"),
            _key("x", "ARMA", "K_q", "x"),
            _key("y", "MAGIA 2", "K_e", "y"),
        ],
        [
            _key("ok", "CONFIRMAR", "K_RETURN"),
            _key("esc", "VOLTAR", "K_ESCAPE"),
        ],
    ),
    "tetris": _profile(
        "tetris",
        "Tetris",
        "Encaixe as peças",
        "Setas movem e giram · A gira · B desce",
        "#a78bfa",
        _dpad(
            {
                "up": "K_UP",
                "down": "K_DOWN",
                "left": "K_LEFT",
                "right": "K_RIGHT",
            },
            repeat={"left", "right", "down"},
        ),
        [
            _key("a", "GIRAR", "K_UP", "a"),
            _key("b", "DESCER", "K_DOWN", "b"),
        ],
        [
            _key("esc", "SAIR", "K_ESCAPE"),
        ],
    ),
    "aliens": _profile(
        "aliens",
        "Aliens",
        "Defenda a nave",
        "Setas movem · A atira/inicia",
        "#86efac",
        _dpad({"left": "K_LEFT", "right": "K_RIGHT"}),
        [
            _key("a", "ATIRAR", "K_SPACE", "a"),
            _key("b", "TELA", "K_f", "b"),
        ],
        [
            _key("esc", "SAIR", "K_ESCAPE"),
        ],
    ),
    "sudoku": _profile(
        "sudoku",
        "Sudoku",
        "Complete o tabuleiro",
        "Setas escolhem · toque nos números · A apaga",
        "#67e8f9",
        _dpad(
            {
                "up": "K_UP",
                "down": "K_DOWN",
                "left": "K_LEFT",
                "right": "K_RIGHT",
            },
            repeat=True,
        ),
        [
            _key("a", "APAGAR", "K_BACKSPACE", "a"),
            _key("b", "NOVO", "K_n", "b"),
            _key("x", "DIFIC.", "K_d", "x"),
            _key("y", "DICA", "K_h", "y"),
        ],
        [
            _key("esc", "SAIR", "K_ESCAPE"),
        ],
        numpad=True,
    ),
    "snake": _profile(
        "snake",
        "Snake Eater",
        "Coma e cresça",
        "Setas mudam a direção · A pausa · B reinicia",
        "#34d399",
        _dpad(
            {
                "up": "K_UP",
                "down": "K_DOWN",
                "left": "K_LEFT",
                "right": "K_RIGHT",
            }
        ),
        [
            _key("a", "PAUSAR", "K_SPACE", "a"),
            _key("b", "REINICIAR", "K_r", "b"),
        ],
        [
            _key("esc", "SAIR", "K_ESCAPE"),
        ],
    ),
    "pong": _profile(
        "pong",
        "Pong",
        "Não deixe a bola cair",
        "Setas sobem/descem · A saca · B reinicia",
        "#22d3ee",
        _dpad({"up": "K_UP", "down": "K_DOWN"}),
        [
            _key("a", "SACAR", "K_SPACE", "a"),
            _key("b", "REINICIAR", "K_r", "b"),
        ],
        [
            _key("esc", "SAIR", "K_ESCAPE"),
        ],
    ),
    "breakout": _profile(
        "breakout",
        "Breakout",
        "Quebre todos os blocos",
        "Setas movem · A lança · B reinicia",
        "#f472b6",
        _dpad({"left": "K_LEFT", "right": "K_RIGHT"}),
        [
            _key("a", "LANÇAR", "K_SPACE", "a"),
            _key("b", "REINICIAR", "K_r", "b"),
        ],
        [
            _key("esc", "SAIR", "K_ESCAPE"),
        ],
    ),
    "game2048": _profile(
        "game2048",
        "2048",
        "Junte os números iguais",
        "Setas deslizam · A desfaz · B novo jogo",
        "#f59e0b",
        _dpad(
            {
                "up": "K_UP",
                "down": "K_DOWN",
                "left": "K_LEFT",
                "right": "K_RIGHT",
            },
            repeat=True,
        ),
        [
            _key("a", "DESFAZER", "K_u", "a"),
            _key("b", "NOVO", "K_r", "b"),
        ],
        [
            _key("esc", "SAIR", "K_ESCAPE"),
        ],
    ),
    "bomberman": _profile(
        "bomberman",
        "Bomberman",
        "Solte bombas e sobreviva",
        "Setas movem · A solta bomba · B reinicia",
        "#fb923c",
        _dpad(
            {
                "up": "K_UP",
                "down": "K_DOWN",
                "left": "K_LEFT",
                "right": "K_RIGHT",
            }
        ),
        [
            _key("a", "BOMBA", "K_SPACE", "a"),
            _key("b", "REINICIAR", "K_r", "b"),
        ],
        [
            _key("ok", "CONFIRMAR", "K_RETURN"),
            _key("esc", "SAIR", "K_ESCAPE"),
        ],
    ),
    "speed": _profile(
        "speed",
        "Speed Racer",
        "Desvie e vá longe",
        "Setas desviam · A inicia/volta",
        "#f97316",
        _dpad({"left": "K_LEFT", "right": "K_RIGHT"}),
        [
            _key("a", "INICIAR", "K_RETURN", "a"),
            _key("b", "SAIR", "K_ESCAPE", "b"),
        ],
        [],
    ),
}

GLOBAL_ACTIONS = [
    _key("__menu", "MENU", "K_F12", "global"),
]

# O teclado numérico do Sudoku é montado pela interface. Estas ações não
# aparecem nos perfis, mas continuam válidas em qualquer jogo.
NUMBER_ACTIONS = {
    f"num{digit}": _key(
        f"num{digit}", digit, f"K_{digit}", "secondary", repeat=False
    )
    for digit in "0123456789"
}

PROFILE_ACTIONS: dict[str, dict[str, dict]] = {}
for _profile_data in PROFILES.values():
    _map: dict[str, dict] = {}
    for _action in (
        _profile_data["dpad"]
        + _profile_data["primary"]
        + _profile_data["secondary"]
        + GLOBAL_ACTIONS
    ):
        _map[_action["id"]] = _action
    PROFILE_ACTIONS[_profile_data["id"]] = _map


# ---------------------------------------------------------------------------
# Estado das teclas remotas + gancho no Pygame
# ---------------------------------------------------------------------------


class _PressedState:
    """Mistura o teclado físico com as teclas pressionadas no celular."""

    __slots__ = ("_real", "_service")

    def __init__(self, real, service: "RemoteService") -> None:
        self._real = real
        self._service = service

    def __getitem__(self, key):
        with self._service._lock:
            if key in self._service._pressed_keys:
                return True
        try:
            return bool(self._real[key])
        except (IndexError, KeyError, TypeError):
            return False

    def __len__(self) -> int:
        return max(512, len(self._real))

    def __iter__(self):
        for key in range(len(self)):
            yield self[key]


def _event_unicode(key: int) -> str:
    if 32 <= key <= 126:
        return chr(key)
    return {
        pygame.K_RETURN: "\r",
        pygame.K_KP_ENTER: "\r",
        pygame.K_BACKSPACE: "\b",
        pygame.K_TAB: "\t",
        pygame.K_ESCAPE: "\x1b",
    }.get(key, "")


def _lan_ip() -> str:
    """Descobre o IP da rede local sem enviar tráfego para a internet."""
    sock = None
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(0.25)
        sock.connect(("8.8.8.8", 80))
        ip = sock.getsockname()[0]
        if ip and not ip.startswith("127."):
            return ip
    except Exception:
        pass
    finally:
        try:
            if sock is not None:
                sock.close()
        except Exception:
            pass

    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ip = info[4][0]
            if ip and not ip.startswith("127."):
                return ip
    except Exception:
        pass
    return "127.0.0.1"


class RemoteService:
    def __init__(self, host: str = "0.0.0.0", port: int = DEFAULT_PORT) -> None:
        self.host = host
        self.port = int(port)
        self.server: ThreadingHTTPServer | None = None
        self.thread: threading.Thread | None = None
        self.watchdog: threading.Thread | None = None
        self.running = False
        self.error = ""
        self.url = ""
        self.ip = _lan_ip()
        self.html = ""
        self.game_id = "menu"
        self.started_at = time.monotonic()

        self._lock = threading.RLock()
        self._pressed_keys: set[int] = set()
        self._clicked: set[str] = set()
        self._mouse_dx = 0
        self._last_seen = time.monotonic()
        self._stop_event = threading.Event()

        self._orig_get_pressed = None
        self._orig_get_rel = None
        self._hooks_installed = False

    # -- ciclo de vida --------------------------------------------------

    def start(self) -> dict:
        if self.running:
            return self.info()

        try:
            self.html = HTML_PATH.read_text(encoding="utf-8")
        except OSError:
            self.html = (
                "<!doctype html><html lang='pt-BR'><meta charset='utf-8'>"
                "<title>BoxConsole</title><body style='background:#080b12;color:#e5e7eb;"
                "font-family:sans-serif;padding:2rem'><h1>BoxConsole</h1>"
                "<p>Arquivo <code>remote_ui.html</code> não encontrado.</p></body></html>"
            )

        self._stop_event.clear()
        candidates = [self.port]
        for extra in range(1, 11):
            candidate = self.port + extra
            if candidate not in candidates:
                candidates.append(candidate)

        last_error: Exception | None = None
        for candidate in candidates:
            try:
                service = self

                class Handler(_RemoteHandler):
                    pass

                Handler.service = service  # type: ignore[attr-defined]
                server = _ThreadingServer((self.host, candidate), Handler)
                self.server = server
                self.port = candidate
                break
            except OSError as exc:
                last_error = exc
                self.server = None

        if self.server is None:
            self.error = f"não foi possível abrir a porta {self.port}: {last_error}"
            self.running = False
            return self.info()

        self.url = f"http://{self.ip}:{self.port}/"
        self._install_hooks()
        self.thread = threading.Thread(
            target=self.server.serve_forever,
            kwargs={"poll_interval": 0.4},
            name="boxconsole-remote",
            daemon=True,
        )
        self.thread.start()
        self.watchdog = threading.Thread(
            target=self._watchdog_loop, name="boxconsole-remote-watchdog", daemon=True
        )
        self.watchdog.start()
        self.running = True
        self.error = ""
        return self.info()

    def stop(self) -> None:
        if not self.running and self.server is None:
            return
        self._stop_event.set()
        self.running = False
        self.release_all()
        self._remove_hooks()
        server = self.server
        self.server = None
        if server is not None:
            try:
                server.shutdown()
            except Exception:
                pass
            try:
                server.server_close()
            except Exception:
                pass
        for thread in (self.thread, self.watchdog):
            if thread is not None and thread is not threading.current_thread():
                try:
                    thread.join(timeout=1.0)
                except Exception:
                    pass
        self.thread = None
        self.watchdog = None

    def info(self) -> dict:
        return {
            "running": self.running,
            "url": self.url,
            "port": self.port,
            "ip": self.ip,
            "error": self.error,
            "game": self.game_id,
            "version": VERSION,
        }

    # -- ganchos no Pygame ----------------------------------------------

    def _install_hooks(self) -> None:
        if self._hooks_installed:
            return
        try:
            self._orig_get_pressed = pygame.key.get_pressed
            self._orig_get_rel = pygame.mouse.get_rel
            pygame.key.get_pressed = self._get_pressed  # type: ignore[assignment]
            pygame.mouse.get_rel = self._get_rel  # type: ignore[assignment]
            self._hooks_installed = True
        except Exception as exc:
            self.error = f"gancho de teclado indisponível: {exc}"
            self._hooks_installed = False

    def _remove_hooks(self) -> None:
        if not self._hooks_installed:
            return
        try:
            if pygame.key.get_pressed is self._get_pressed:
                pygame.key.get_pressed = self._orig_get_pressed  # type: ignore[assignment]
        except Exception:
            pass
        try:
            if pygame.mouse.get_rel is self._get_rel:
                pygame.mouse.get_rel = self._orig_get_rel  # type: ignore[assignment]
        except Exception:
            pass
        self._hooks_installed = False

    def _get_pressed(self):
        real = self._orig_get_pressed() if self._orig_get_pressed else []
        return _PressedState(real, self)

    def _get_rel(self):
        real = (0, 0)
        if self._orig_get_rel is not None:
            try:
                real = self._orig_get_rel()
            except Exception:
                real = (0, 0)
        with self._lock:
            dx = self._mouse_dx
            self._mouse_dx = 0
        return (int(real[0]) + dx, int(real[1]))

    # -- perfil atual ---------------------------------------------------

    def set_game(self, game_id: str) -> None:
        self.release_all()
        with self._lock:
            self.game_id = game_id if game_id in PROFILES else "menu"
            self._last_seen = time.monotonic()

    def current_profile(self) -> dict:
        with self._lock:
            return PROFILES.get(self.game_id, PROFILES["menu"])

    def _find_action(self, action_id: str) -> dict | None:
        with self._lock:
            game_id = self.game_id
        profile = PROFILES.get(game_id, PROFILES["menu"])
        action = PROFILE_ACTIONS.get(profile["id"], {}).get(action_id)
        if action is not None:
            return action
        if action_id in NUMBER_ACTIONS:
            return NUMBER_ACTIONS[action_id]
        return PROFILE_ACTIONS["menu"].get(action_id)

    # -- entrada --------------------------------------------------------

    def _post_key(self, key: int, down: bool, repeat: bool = False) -> None:
        try:
            event_type = pygame.KEYDOWN if down else pygame.KEYUP
            pygame.event.post(
                pygame.event.Event(
                    event_type,
                    {
                        "key": key,
                        "mod": 0,
                        "unicode": _event_unicode(key) if down else "",
                        "scancode": 0,
                        "repeat": bool(repeat) if down else False,
                    },
                )
            )
        except Exception:
            pass

    def _post_mouse(self, down: bool) -> None:
        try:
            event_type = pygame.MOUSEBUTTONDOWN if down else pygame.MOUSEBUTTONUP
            pygame.event.post(
                pygame.event.Event(
                    event_type,
                    {"button": 1, "pos": (0, 0), "remote": True},
                )
            )
        except Exception:
            pass

    def press_action(self, action_id: str) -> bool:
        action = self._find_action(action_id)
        if action is None:
            return False
        kind = action.get("kind", "key")
        now = time.monotonic()

        if kind == "key":
            key = getattr(pygame, str(action.get("key", "")), None)
            if not isinstance(key, int):
                return False
            with self._lock:
                was_pressed = key in self._pressed_keys
                self._pressed_keys.add(key)
                self._last_seen = now
            # Repetição do cliente vira KEYDOWN repetido, útil em menus e
            # jogos que avançam uma casa por evento (2048, Sudoku, Tetris).
            self._post_key(key, True, repeat=was_pressed)
            return True

        if kind == "click":
            with self._lock:
                if action_id in self._clicked:
                    self._last_seen = now
                    return True
                self._clicked.add(action_id)
                self._last_seen = now
            self._post_mouse(True)
            return True

        if kind == "turn":
            dx = int(action.get("dx", 0))
            with self._lock:
                self._mouse_dx += dx
                self._last_seen = now
            return True

        return False

    def release_action(self, action_id: str) -> bool:
        action = self._find_action(action_id)
        if action is None:
            return False
        kind = action.get("kind", "key")

        if kind == "key":
            key = getattr(pygame, str(action.get("key", "")), None)
            if not isinstance(key, int):
                return False
            with self._lock:
                was_pressed = key in self._pressed_keys
                self._pressed_keys.discard(key)
                self._last_seen = time.monotonic()
            if was_pressed:
                self._post_key(key, False)
            return True

        if kind == "click":
            with self._lock:
                was_pressed = action_id in self._clicked
                self._clicked.discard(action_id)
                self._last_seen = time.monotonic()
            if was_pressed:
                self._post_mouse(False)
            return True

        return True

    def release_all(self) -> None:
        with self._lock:
            keys = list(self._pressed_keys)
            clicks = list(self._clicked)
            self._pressed_keys.clear()
            self._clicked.clear()
            self._mouse_dx = 0
            self._last_seen = time.monotonic()
        for key in keys:
            self._post_key(key, False)
        for _ in clicks:
            self._post_mouse(False)

    def touch(self) -> None:
        with self._lock:
            self._last_seen = time.monotonic()

    def _watchdog_loop(self) -> None:
        while not self._stop_event.wait(0.4):
            with self._lock:
                active = bool(self._pressed_keys or self._clicked)
                stale = active and (time.monotonic() - self._last_seen) > RELEASE_AFTER
            if stale:
                self.release_all()

    def status_payload(self) -> dict:
        with self._lock:
            game_id = self.game_id
        profile = PROFILES.get(game_id, PROFILES["menu"])
        return {
            "ok": True,
            "version": VERSION,
            "game": {
                "id": game_id,
                "name": profile["name"],
            },
            "profile": profile,
            "global": GLOBAL_ACTIONS,
            "url": self.url,
            "server_time": round(time.monotonic() - self.started_at, 1),
        }


# ---------------------------------------------------------------------------
# servidor HTTP
# ---------------------------------------------------------------------------


class _ThreadingServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True
    request_queue_size = 16


class _RemoteHandler(BaseHTTPRequestHandler):
    service: RemoteService
    protocol_version = "HTTP/1.1"
    server_version = "BoxConsoleRemote"
    sys_version = ""

    def log_message(self, fmt, *args):  # noqa: A003
        if DEBUG:
            super().log_message(fmt, *args)

    def _send(self, status: int, body: bytes, content_type: str, extra=None) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store, max-age=0")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        if extra:
            for key, value in extra.items():
                self.send_header(key, value)
        self.end_headers()
        if body:
            try:
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError):
                pass

    def _json(self, status: int, data: dict) -> None:
        body = json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        self._send(status, body, "application/json; charset=utf-8")

    def _read_json(self) -> dict | None:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            return None
        if length < 0 or length > MAX_BODY:
            return None
        if length == 0:
            return {}
        try:
            raw = self.rfile.read(length)
            value = json.loads(raw.decode("utf-8"))
            return value if isinstance(value, dict) else None
        except Exception:
            return None

    def do_GET(self) -> None:  # noqa: N802
        path = urlsplit(self.path).path
        if path in ("/", "/index.html", "/remote"):
            body = self.service.html.encode("utf-8")
            self._send(200, body, "text/html; charset=utf-8")
            return
        if path == "/api/status":
            self._json(200, self.service.status_payload())
            return
        if path in ("/health", "/healthz"):
            self._send(200, b"ok", "text/plain; charset=utf-8")
            return
        if path == "/favicon.ico":
            self._send(204, b"", "image/x-icon")
            return
        self._send(404, b"not found", "text/plain; charset=utf-8")

    def do_POST(self) -> None:  # noqa: N802
        path = urlsplit(self.path).path
        if path == "/api/action":
            data = self._read_json()
            if data is None:
                self._json(400, {"ok": False, "error": "json inválido"})
                return
            action_id = str(data.get("action", ""))[:64]
            down = bool(data.get("down", False))
            if not action_id:
                self._json(400, {"ok": False, "error": "action ausente"})
                return
            found = (
                self.service.press_action(action_id)
                if down
                else self.service.release_action(action_id)
            )
            self._json(200 if found else 404, {"ok": found})
            return

        if path == "/api/release":
            self.service.release_all()
            self._json(200, {"ok": True})
            return

        if path == "/api/heartbeat":
            self.service.touch()
            self._json(200, {"ok": True})
            return

        self._send(404, b"not found", "text/plain; charset=utf-8")


# ---------------------------------------------------------------------------
# API pública do módulo
# ---------------------------------------------------------------------------

_service: RemoteService | None = None


def start() -> dict:
    global _service
    if os.environ.get("BOXCONSOLE_REMOTE", "1").lower() in ("0", "off", "false", "no"):
        return {"running": False, "url": "", "port": 0, "error": "desativado", "game": "menu"}

    if _service is not None and _service.running:
        return _service.info()

    try:
        port = int(os.environ.get("BOXCONSOLE_REMOTE_PORT", DEFAULT_PORT))
    except (TypeError, ValueError):
        port = DEFAULT_PORT
    if port <= 0 or port > 65535:
        port = DEFAULT_PORT

    _service = RemoteService(port=port)
    info = _service.start()
    if info.get("running"):
        print(f"[BoxConsole] Controle no celular: {info['url']}")
    elif info.get("error") and info["error"] != "desativado":
        print(f"[BoxConsole] Controle remoto: {info['error']}")
    return info


def stop() -> None:
    global _service
    service = _service
    _service = None
    if service is not None:
        service.stop()


def set_game(game_id: str) -> None:
    if _service is not None:
        _service.set_game(game_id)


def url() -> str:
    if _service is not None and _service.running:
        return _service.url
    return ""


def info() -> dict:
    if _service is not None:
        return _service.info()
    return {"running": False, "url": "", "port": 0, "error": "", "game": "menu"}


def status_payload() -> dict:
    if _service is not None:
        return _service.status_payload()
    return {
        "ok": False,
        "version": VERSION,
        "game": {"id": "menu", "name": "BoxConsole"},
        "profile": PROFILES["menu"],
        "global": GLOBAL_ACTIONS,
        "url": "",
        "server_time": 0,
    }
