#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BoxConsole — console de jogos arcade open source
================================================

Menu de terminal (modo secundário / reserva) do BoxConsole:
navegue com as setas, confirme com OK/Enter e abra a ficha de cada jogo.
O programa abre em tela cheia (janela maximizada no Windows).

O menu principal agora é o Pygame (main.py). Este módulo é usado quando o
Pygame não está disponível ou quando se executa "python main.py --terminal".

COMO COMPLETAR OS DADOS DOS REPOSITÓRIOS
----------------------------------------
Edite a lista GAMES abaixo. Em cada jogo, os campos:
    "repo"    -> URL do repositório original (ou None para "em breve")
    "autor"   -> autor/equipe do projeto original
    "licenca" -> licença do projeto
    "site"    -> link opcional de play/download
Quando "repo" for None, a ficha mostra que o repositório ainda será
adicionado. É só preencher a URL e o botão [R] passa a abrir no navegador.

Uso:
    python main.py --terminal
    python console_ui.py

Dependências:
    colorama é opcional; sem ele o terminal funciona sem cores.
"""

from __future__ import annotations

import importlib.util
import os
import re
import shutil
import subprocess
import sys
import textwrap
import time
import webbrowser
from pathlib import Path

try:
    from colorama import Back, Fore, Style, init as colorama_init

    HAS_COLORAMA = True
except ImportError:
    # O catálogo e o menu Pygame não dependem de colorama. No terminal,
    # ausência do pacote apenas desliga as cores em vez de impedir o launcher.
    class _NoColor:
        def __getattr__(self, _name: str) -> str:
            return ""

    Back = Fore = Style = _NoColor()  # type: ignore[assignment]
    HAS_COLORAMA = False

    def colorama_init(*_args, **_kwargs) -> None:
        return None

colorama_init()
# Garante acentos e desenhos de caixa no terminal (Windows incluso).
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

BASE_DIR = Path(__file__).resolve().parent
# Os jogos ficam em ``games/``. O fallback para a raiz mantém o projeto
# funcionando antes de rodar o script de organização.
GAMES_DIR = BASE_DIR / "games"
IMAGES_DIR = BASE_DIR / "images"
SOUNDS_DIR = BASE_DIR / "sounds"
IS_WINDOWS = os.name == "nt"
# Evita o banner de boas-vindas do pygame ao checar dependências dos jogos.
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")


# ---------------------------------------------------------------------------
# CATÁLOGO — edite/adicione jogos aqui
# ---------------------------------------------------------------------------

GAMES = [
    {
        "id": "doom",
        "nome": "Doom in PyGame",
        "genero": "FPS · Raycasting 3D",
        "players": "1 jogador",
        "descricao": (
            "Um shooter em primeira pessoa com motor 3D em raycasting, inimigos "
            "com IA e combate intenso. Explore corredores escuros e enfrente demônios."
        ),
        "controles": [
            ("W A S D", "mover pelo mapa"),
            ("Mouse", "olhar ao redor"),
            ("Clique", "atirar"),
        ],
        "stack": ["Python", "Pygame"],
        "deps": ["pygame"],
        "perfil": {"res": (480, 270), "fps": 24},
        "pasta": "Doom-PyGame",
        "entry": "main.py",
        "comando": "python main.py",
        "cor": Fore.RED,
        "repo": "https://github.com/Umang-Lodaya/Doom-PyGame",
        "site": None,
        "autor": "Umang Lodaya",
        "licenca": "Não informada na pasta",
    },
    {
        "id": "flappy",
        "nome": "Flappy Bird",
        "genero": "Arcade · Reflexo",
        "players": "1 jogador",
        "descricao": (
            "Use a barra de espaço para manter o pássaro no ar, desvie dos canos "
            "e marque pontos. Simples de aprender, difícil de largar."
        ),
        "controles": [
            ("Espaço", "bater as asas / subir"),
            ("ESC", "reiniciar após o game over"),
            ("Q", "sair do jogo"),
        ],
        "stack": ["Python", "Pygame"],
        "deps": ["pygame"],
        "perfil": {"res": (288, 512), "fps": 60},
        "pasta": "flappy-bird",
        "entry": "main.py",
        "comando": "python main.py",
        "cor": Fore.YELLOW,
        "repo": "https://github.com/mehmetemineker/flappy-bird",
        "site": "https://mehmetemineker.github.io/flappy-bird/",
        "autor": "Mehmet Emin Eker",
        "licenca": "Apache 2.0",
    },
    {
        "id": "pacman",
        "embed": True,
        "nome": "Pac-Man",
        "genero": "Arcade · Labirinto",
        "players": "1 jogador",
        "descricao": (
            "Recriação em Pygame do clássico, com quatro fantasmas e estratégias "
            "próprias de perseguição, três dificuldades, pausa e pontuação."
        ),
        "controles": [
            ("W A S D / setas", "mover o Pac-Man"),
            ("ESC / P", "pausar e abrir o menu"),
            ("Enter", "confirmar opções"),
            ("F12", "voltar ao menu do BoxConsole"),
        ],
        "stack": ["Python", "Pygame"],
        "deps": ["pygame"],
        "perfil": {"res": (960, 540), "fps": 60},
        "pasta": "pacman",
        "entry": "pygame_main.py",
        "comando": "python pygame_main.py",
        "cor": Fore.YELLOW,
        "repo": "https://github.com/tiagolucasoo/pacman",
        "site": None,
        "autor": "Tiago Lucas e equipe (IFPR Londrina)",
        "licenca": "Não informada na pasta",
    },
    {
        "id": "street",
        "nome": "Street Fighter",
        "genero": "Luta 2D · Versus CPU",
        "players": "1 jogador",
        "descricao": (
            "Jogo de luta 2D contra a IA: ataque, corra e pule para zerar a vida "
            "do Wizard e somar pontos. Os menus são navegados com o mouse."
        ),
        "controles": [
            ("A / D", "mover para os lados"),
            ("W", "pular"),
            ("R / T", "dois tipos de ataque"),
        ],
        "stack": ["Python", "Pygame"],
        "deps": ["pygame"],
        "perfil": {"res": (960, 540), "fps": 30},
        "pasta": "Street_Fighter",
        "entry": "src/main.py",
        "comando": "python src/main.py",
        "cor": Fore.MAGENTA,
        "repo": "https://github.com/AadityaPanda/Street_Fighter",
        "site": None,
        "autor": "Aaditya Panda",
        "licenca": "MIT",
    },
    {
        "id": "mario",
        "nome": "Super Mario",
        "genero": "Plataforma 2D",
        "players": "1 jogador",
        "descricao": (
            "Implementação em Pygame inspirada no clássico: fase, inimigos, "
            "painel, sons e menu. Corra, pegue impulso e pule até o fim do nível."
        ),
        "controles": [
            ("← / →", "mover o Mario"),
            ("Espaço", "pular"),
            ("Shift", "correr"),
        ],
        "stack": ["Python", "Pygame"],
        "deps": ["pygame"],
        "perfil": {"res": (640, 480), "fps": 60},
        "pasta": "super-mario-python",
        "entry": "main.py",
        "comando": "python main.py",
        "cor": Fore.GREEN,
        "repo": "https://github.com/mx0c/super-mario-python",
        "site": None,
        "autor": "mx0c (inspirado em Meth-Meth-Method)",
        "licenca": "Não informada na pasta",
    },
    {
        "id": "donkeyking",
        "nome": "Donkey King",
        "genero": "Plataforma 2D · Arcade",
        "players": "1 jogador",
        "descricao": (
            "Suba as plataformas, desvie dos barris e dos macacos e alcance a "
            "taça para avançar. Três fases com moedas, vidas extras e perigos "
            "aleatórios, agora rodando em Python 3."
        ),
        "controles": [
            ("W A S D / setas", "mover e subir/descer escadas"),
            ("Espaço / X / Z / Enter", "pular"),
            ("Q", "sair do jogo"),
            ("F12", "voltar ao menu do BoxConsole"),
        ],
        "stack": ["Python", "Pygame"],
        "deps": ["pygame"],
        "perfil": {"res": (1300, 630), "fps": 60},
        "pasta": "DonkeyKing",
        "entry": "DonkeyMain.py",
        "comando": "python DonkeyMain.py",
        "cor": Fore.YELLOW,
        "repo": "https://github.com/pinkeshbadjatiya/DonkeyKing",
        "site": None,
        "autor": "Pinkesh Badjatiya",
        "licenca": "GPLv3",
    },
    {
        "id": "zelda",
        "nome": "PyZelda RPG",
        "genero": "RPG de ação · Aventura",
        "players": "1 jogador",
        "descricao": (
            "RPG de ação estilo Zelda com armas, magias, inimigos, upgrades e "
            "save. Explore os mapas criados no Tiled e evolua seu personagem."
        ),
        "controles": [
            ("Setas / W A S D", "mover o personagem"),
            ("Espaço", "atacar com a arma"),
            ("Ctrl esquerdo", "lançar magia"),
            ("Q / E", "trocar arma / magia"),
        ],
        "stack": ["Python", "Pygame", "Tiled"],
        "deps": ["pygame"],
        "perfil": {"res": (960, 540), "fps": 30},
        "pasta": "pyzelda-rpg",
        "entry": "code/main.py",
        "comando": "python code/main.py",
        "cor": Fore.LIGHTGREEN_EX,
        "repo": "https://github.com/artemshchirov/pyzelda-rpg",
        "site": None,
        "autor": "Artem Shchirov",
        "licenca": "MIT",
    },
    {
        "id": "tetris",
        "nome": "Tetris",
        "genero": "Puzzle · Arcade",
        "players": "1 jogador",
        "descricao": (
            "O clássico Tetris em Pygame: encaixe as peças, complete linhas e "
            "faça o máximo de pontos antes de perder."
        ),
        "controles": [
            ("← / →", "mover a peça"),
            ("↓", "descer mais rápido"),
            ("↑", "girar a peça"),
        ],
        "stack": ["Python", "Pygame"],
        "deps": ["pygame"],
        "perfil": {"res": (800, 750), "fps": 30},
        "pasta": "tetris-pygame",
        "entry": "Tetris.py",
        "comando": "python Tetris.py",
        "cor": Fore.CYAN,
        "repo": "https://github.com/rajatdiptabiswas/tetris-pygame",
        "site": None,
        "autor": "Rajat Dipta Biswas",
        "licenca": "Não informada na pasta",
    },
    # ------------------------------------------------------------------
    # Jogos que já vêm embutidos no próprio Pygame (exemplos oficiais).
    # Não precisam de pasta: o BoxConsole roda "python -m pygame.examples.*".
    # ------------------------------------------------------------------
    {
        "id": "aliens",
        "nome": "Aliens",
        "genero": "Arcade · Space Shooter",
        "players": "1 jogador",
        "descricao": (
            "Mini jogo oficial do Pygame: defenda a base dos aliens que descem "
            "em formação. Usa sprites, sons, música e tela cheia."
        ),
        "controles": [
            ("← / →", "mover a nave"),
            ("Espaço", "atirar"),
            ("F", "alternar tela cheia"),
        ],
        "stack": ["Python", "Pygame", "Exemplo oficial"],
        "deps": ["pygame"],
        "perfil": {"res": None, "fps": 60},
        "modulo": "pygame.examples.aliens",
        "pasta": "pygame",
        "entry": None,
        "comando": "python -m pygame.examples.aliens",
        "cor": Fore.LIGHTBLUE_EX,
        "repo": "https://github.com/pygame/pygame/blob/main/examples/aliens.py",
        "site": "https://www.pygame.org/docs/",
        "autor": "Comunidade Pygame",
        "licenca": "LGPL 2.1",
    },
    {
        "id": "sudoku",
        "nome": "Sudoku",
        "genero": "Puzzle · Lógica",
        "players": "1 jogador",
        "descricao": (
            "Sudoku 9x9 aleatório com três dificuldades, cronômetro, destaque de "
            "erros e dicas. Complete sem repetir nas linhas, colunas e blocos."
        ),
        "controles": [
            ("Setas / W A S D", "mover a seleção"),
            ("1 a 9", "preencher a célula"),
            ("0 / Backspace", "apagar a célula"),
            ("N / D / H", "novo, dificuldade e dica"),
        ],
        "stack": ["Python", "Pygame"],
        "deps": ["pygame"],
        "perfil": {"res": (660, 800), "fps": 30},
        "pasta": "sudoku",
        "entry": "main.py",
        "comando": "python main.py",
        "cor": Fore.LIGHTMAGENTA_EX,
        "repo": None,
        "repo_texto": "*Jogo Próprio",
        "site": None,
        "autor": "Criado para o BoxConsole",
        "licenca": "MIT",
    },
    {
        "id": "snake",
        "nome": "Snake Eater",
        "genero": "Arcade · Clássico",
        "players": "1 jogador",
        "descricao": (
            "O clássico jogo da cobrinha: coma as maçãs, cresça e não bata na "
            "parede nem no próprio corpo."
        ),
        "controles": [
            ("Setas / W A S D", "mover a cobra"),
            ("P / Espaço", "pausar / continuar"),
            ("R", "jogar de novo após perder"),
            ("ESC", "sair"),
        ],
        "stack": ["Python", "Pygame"],
        "deps": ["pygame"],
        "perfil": {"res": (720, 480), "fps": 25},
        "pasta": "snake-pygame",
        "entry": "Snake Game.py",
        "comando": 'python "Snake Game.py"',
        "cor": Fore.LIGHTGREEN_EX,
        "repo": "https://github.com/rajatdiptabiswas/snake-pygame",
        "site": None,
        "autor": "Rajat Dipta Biswas",
        "licenca": "Não informada na pasta",
    },
    {
        "id": "pong",
        "nome": "Pong",
        "genero": "Arcade · Esporte",
        "players": "1 jogador",
        "descricao": (
            "Duelo de raquetes contra a CPU: rebata a bola e seja o primeiro a "
            "marcar 7 pontos."
        ),
        "controles": [
            ("W / S ou ↑ ↓", "mover a raquete"),
            ("Espaço / Enter", "sacar e reiniciar"),
            ("R / ESC", "reiniciar / sair"),
        ],
        "stack": ["Python", "Pygame"],
        "deps": ["pygame"],
        "perfil": {"res": (800, 600), "fps": 60},
        "pasta": "pong",
        "entry": "main.py",
        "comando": "python main.py",
        "cor": Fore.LIGHTCYAN_EX,
        "repo": None,
        "repo_texto": "*Jogo Próprio",
        "site": None,
        "autor": "Criado para o BoxConsole",
        "licenca": "MIT",
    },
    {
        "id": "breakout",
        "nome": "Breakout",
        "genero": "Arcade · Tijolos",
        "players": "1 jogador",
        "descricao": (
            "Quebre todos os tijolos com a bola sem deixar que ela caia. Você "
            "tem 3 vidas para limpar a tela."
        ),
        "controles": [
            ("A / D ou ← →", "mover a raquete"),
            ("Espaço / Enter", "lançar a bola"),
            ("R / ESC", "reiniciar / sair"),
        ],
        "stack": ["Python", "Pygame"],
        "deps": ["pygame"],
        "perfil": {"res": (800, 600), "fps": 60},
        "pasta": "breakout",
        "entry": "main.py",
        "comando": "python main.py",
        "cor": Fore.LIGHTRED_EX,
        "repo": None,
        "repo_texto": "*Jogo Próprio",
        "site": None,
        "autor": "Criado para o BoxConsole",
        "licenca": "MIT",
    },
    {
        "id": "game2048",
        "nome": "2048",
        "genero": "Puzzle · Números",
        "players": "1 jogador",
        "descricao": (
            "Junte peças iguais com as setas até chegar ao 2048. Cuidado para "
            "não travar o tabuleiro."
        ),
        "controles": [
            ("Setas / W A S D", "deslizar os números"),
            ("U", "desfazer o último movimento"),
            ("R / ESC", "novo jogo / sair"),
        ],
        "stack": ["Python", "Pygame"],
        "deps": ["pygame"],
        "perfil": {"res": (520, 640), "fps": 30},
        "pasta": "2048",
        "entry": "main.py",
        "comando": "python main.py",
        "cor": Fore.LIGHTYELLOW_EX,
        "repo": None,
        "repo_texto": "*Jogo Próprio",
        "site": None,
        "autor": "Criado para o BoxConsole",
        "licenca": "MIT",
    },
    {
        "id": "bomberman",
        "nome": "Bomberman",
        "genero": "Arcade · Labirinto",
        "players": "1 jogador",
        "descricao": (
            "Plante bombas, destrua tijolos e elimine os inimigos antes que o "
            "labirinto exploda em você. Colete melhorias pelo caminho."
        ),
        "controles": [
            ("Setas / W A S D", "mover"),
            ("Espaço / Enter", "soltar bomba"),
            ("R / ESC", "reiniciar / sair"),
        ],
        "stack": ["Python", "Pygame"],
        "deps": ["pygame"],
        "perfil": {"res": (800, 600), "fps": 60},
        "pasta": "bomberman",
        "entry": "main.py",
        "comando": "python main.py",
        "cor": Fore.LIGHTWHITE_EX,
        "repo": None,
        "repo_texto": "*Jogo Próprio",
        "site": None,
        "autor": "Criado para o BoxConsole",
        "licenca": "MIT",
    },
    {
        "id": "speed",
        "nome": "Speed Racer",
        "genero": "Corrida · Arcade",
        "players": "1 jogador",
        "descricao": (
            "Jogo de corrida em Pygame: desvie dos carros, colete combustível e "
            "percorra a maior distância possível. A velocidade e os obstáculos "
            "aumentam o desafio a cada trecho."
        ),
        "controles": [
            ("← / →", "mover o carro"),
            ("Enter", "iniciar / voltar ao menu"),
        ],
        "stack": ["Python", "Pygame"],
        "deps": ["pygame"],
        "perfil": {"res": (900, 525), "fps": 30},
        "pasta": "SPEED-RACER",
        "entry": "Speed Racer.py",
        "comando": 'python "Speed Racer.py"',
        "cor": Fore.LIGHTRED_EX,
        "repo": "https://github.com/KeeratSachdeva/SPEED-RACER",
        "site": None,
        "autor": "Keerat Sachdeva",
        "licenca": "Não informada na pasta",
    },
]

PIP_NAMES = {
    "pygame": "pygame",
    "cv2": "opencv-python",
    "numpy": "numpy",
    "scipy": "scipy",
    "keyboard": "keyboard",
    "pyfiglet": "pyfiglet",
    "colorama": "colorama",
}

APP_VERSION = "1.5"
PROJECT_URL = "https://github.com/tiagolucasoo/boxConsole"
PROJECT_URL_TEXT = "github.com/tiagolucasoo/boxConsole"
PROJECT_CREDIT = (
    "Desenvolvido por Tiago Lucas Oliveira (IFPR Londrina) · 2026 · BoxConsole"
)
PROJECT_CREDIT_OPEN_SOURCE = f"Projeto open source · {PROJECT_URL_TEXT}"
FULLSCREEN = True  # maximiza a janela do console ao iniciar (Windows)


# ---------------------------------------------------------------------------
# Tema / suporte a terminais
# ---------------------------------------------------------------------------

ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")
_unicode_ok = True
for _sample in ("╭─│╮╰╯▸█▀▄…⏳✔"):
    try:
        _sample.encode(sys.stdout.encoding or "utf-8")
    except Exception:
        _unicode_ok = False
        break

if _unicode_ok:
    CH = {
        "tl": "╭", "tr": "╮", "bl": "╰", "br": "╯", "h": "─", "v": "│",
        "dot": "·", "arrow": "▸", "bar": "█", "ok": "✔", "bad": "✖",
        "wait": "⏳", "updown": "↑ ↓", "leftright": "← →", "enter": "ENTER",
        "sys": "⚙",
    }
else:
    CH = {
        "tl": "+", "tr": "+", "bl": "+", "br": "+", "h": "-", "v": "|",
        "dot": "|", "arrow": ">", "bar": "#", "ok": "*", "bad": "X",
        "wait": "...", "updown": "W/S", "leftright": "A/D", "enter": "ENTER",
        "sys": "S",
    }

ELLIPSIS = "…" if _unicode_ok else "..."


def visible_len(text: str) -> int:
    return len(ANSI_RE.sub("", text))


def pad(text: str, width: int) -> str:
    return text + " " * max(0, width - visible_len(text))


def center(text: str, width: int) -> str:
    gap = max(0, width - visible_len(text))
    left = gap // 2
    return " " * left + text + " " * (gap - left)


def clip_plain(text: str, width: int) -> str:
    if len(text) <= width:
        return text
    return text[: max(0, width - len(ELLIPSIS))] + ELLIPSIS


def pack_styled(items: list[str], width: int) -> list[str]:
    """Junta itens coloridos em linhas, respeitando a largura visível."""
    rows: list[str] = []
    current = ""
    for item in items:
        candidate = item if not current else f"{current}   {item}"
        if visible_len(candidate) > width and current:
            rows.append(current)
            current = item
        else:
            current = candidate
    if current:
        rows.append(current)
    return rows


def wrap(text: str, width: int) -> list[str]:
    return textwrap.wrap(
        text, width=width, break_long_words=False, break_on_hyphens=False
    ) or [""]


def term_cols() -> int:
    return shutil.get_terminal_size((80, 24)).columns


def term_lines() -> int:
    return shutil.get_terminal_size((80, 24)).lines


def layout() -> tuple[int, int, bool]:
    """Retorna (largura da caixa, largura interna, modo compacto)."""
    cols = term_cols()
    # Deixa uma coluna de folga para o terminal não quebrar a borda da caixa.
    width = max(58, min(cols - 4, 88))
    inner = width - 4
    compact = term_lines() < 30
    return width, inner, compact


def hard_clear() -> None:
    sys.stdout.write("\x1b[2J\x1b[3J\x1b[H")


def render(lines: list[str]) -> None:
    """Redesenha sem piscar, centralizando o conteúdo na tela."""
    top = max(0, (term_lines() - len(lines)) // 2)
    sys.stdout.write("\x1b[H\x1b[J" + "\n" * top + "\n".join(lines))
    sys.stdout.flush()


def hide_cursor() -> None:
    sys.stdout.write("\x1b[?25l")
    sys.stdout.flush()


def show_cursor() -> None:
    sys.stdout.write("\x1b[?25h")
    sys.stdout.flush()


_CONSOLE_WINDOW = {"hwnd": None, "was_maximized": False}


def enter_fullscreen() -> None:
    """Maximiza a janela do console no Windows (melhor esforço)."""
    if not FULLSCREEN or not IS_WINDOWS:
        return
    try:
        import ctypes

        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleTitleW("BoxConsole")
        hwnd = kernel32.GetConsoleWindow()
        if not hwnd:
            return
        _CONSOLE_WINDOW["hwnd"] = hwnd
        _CONSOLE_WINDOW["was_maximized"] = bool(user32.IsZoomed(hwnd))
        user32.ShowWindow(hwnd, 3)  # SW_MAXIMIZE
        user32.SetForegroundWindow(hwnd)
        # Dá tempo para o terminal recalcular as dimensões antes do 1º desenho.
        time.sleep(0.15)
    except Exception:
        pass


def leave_fullscreen() -> None:
    if not IS_WINDOWS or not _CONSOLE_WINDOW["hwnd"]:
        return
    if _CONSOLE_WINDOW["was_maximized"]:
        return
    try:
        import ctypes

        ctypes.windll.user32.ShowWindow(_CONSOLE_WINDOW["hwnd"], 9)  # SW_RESTORE
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Caixas e cabeçalho
# ---------------------------------------------------------------------------

W = 78
INNER = 74
COMPACT = False


def refresh_layout() -> None:
    global W, INNER, COMPACT
    W, INNER, COMPACT = layout()


def btop() -> str:
    return f"  {Fore.CYAN}{CH['tl']}{CH['h'] * (W - 2)}{CH['tr']}{Style.RESET_ALL}"


def bbot() -> str:
    return f"  {Fore.CYAN}{CH['bl']}{CH['h'] * (W - 2)}{CH['br']}{Style.RESET_ALL}"


def brow(content: str = "") -> str:
    return (
        f"  {Fore.CYAN}{CH['v']}{Style.RESET_ALL} "
        + pad(content, W - 4)
        + f" {Fore.CYAN}{CH['v']}{Style.RESET_ALL}"
    )


def hsep() -> str:
    return (
        f"  {Fore.CYAN}{CH['v']}{Style.RESET_ALL} "
        + f"{Fore.CYAN}{CH['h'] * (W - 4)}{Style.RESET_ALL}"
        + f" {Fore.CYAN}{CH['v']}{Style.RESET_ALL}"
    )


LOGO_BOX = [
    " ____   ______   __",
    "|  _ \\ / __ \\ \\ / /",
    "| |_) | |  | \\ V /",
    "|  _ <| |  | |> <",
    "| |_) | |__| / . \\",
    "|____/ \\____/_/ \\_\\",
]
LOGO_CONSOLE = [
    "  _____ ____  _   _  _____  ____  _      ______",
    " / ____/ __ \\| \\ | |/ ____|/ __ \\| |    |  ____|",
    "| |   | |  | |  \\| | (___ | |  | | |    | |__",
    "| |   | |  | | . ` |\\___ \\| |  | | |    |  __|",
    "| |___| |__| | |\\  |____) | |__| | |____| |____",
    " \\_____\\____/|_| \\_|_____/ \\____/|______|______|",
]
LOGO_WIDTH = 19 + 2 + 48
LOGO_HEIGHT = len(LOGO_BOX)


def brand() -> str:
    return (
        f"{Fore.LIGHTCYAN_EX}{Style.BRIGHT}Box{Style.RESET_ALL}"
        f"{Fore.LIGHTMAGENTA_EX}{Style.BRIGHT}Console{Style.RESET_ALL}"
    )


def logo_art() -> list[str]:
    """Arte ASCII grande: BOX em ciano e CONSOLE em magenta."""
    if W < LOGO_WIDTH + 2:
        return [brand()]
    art = []
    for index in range(LOGO_HEIGHT):
        left = LOGO_BOX[index].ljust(19)
        right = LOGO_CONSOLE[index].ljust(48)
        art.append(
            f"{Fore.LIGHTCYAN_EX}{Style.BRIGHT}{left}{Style.RESET_ALL}  "
            f"{Fore.LIGHTMAGENTA_EX}{Style.BRIGHT}{right}{Style.RESET_ALL}"
        )
    return art


def header(tight: bool = False, very_tight: bool = False) -> list[str]:
    lines = [""]
    for art_line in logo_art():
        lines.append("  " + center(art_line, W))
    if not very_tight:
        lines.append("")
    bar = CH["h"] * 7
    subtitle = (
        f"{Fore.CYAN}{bar}{Style.RESET_ALL}  "
        f"{Fore.WHITE}{Style.BRIGHT}Jogos Arcade{Style.RESET_ALL}  "
        f"{Fore.MAGENTA}{bar}{Style.RESET_ALL}"
    )
    lines.append("  " + center(subtitle, W))
    if not very_tight:
        lines.append("")
    # "tight" remove a linha em branco final; "very_tight" remove as duas.
    if tight and lines and lines[-1] == "":
        lines.pop()
    return lines


def slim_header(section: str, one_line: bool = False) -> list[str]:
    title = (
        "  "
        + brand()
        + f"{Fore.LIGHTBLACK_EX}  {CH['arrow']}  {section}{Style.RESET_ALL}"
    )
    if one_line:
        return [title]
    lines = ["", title]
    if not COMPACT:
        lines.append("")
    return lines


# ---------------------------------------------------------------------------
# Estado dos jogos
# ---------------------------------------------------------------------------

_module_cache: dict[str, bool] = {}


def module_available(name: str) -> bool:
    """Checa uma dependência uma única vez por execução."""
    cached = _module_cache.get(name)
    if cached is not None:
        return cached
    try:
        available = importlib.util.find_spec(name) is not None
    except Exception:
        available = False
    _module_cache[name] = available
    return available


def clear_module_cache() -> None:
    _module_cache.clear()


def game_dir(game: dict) -> Path:
    """Pasta do jogo em ``games/``, com fallback para a raiz antiga."""
    pasta = game["pasta"]
    novo = GAMES_DIR / pasta
    if novo.exists():
        return novo
    return BASE_DIR / pasta


def game_entry(game: dict) -> Path | None:
    """Caminho do arquivo de entrada, ou None para jogos embutidos no Pygame."""
    if game.get("modulo"):
        return None
    entry = game.get("entry")
    if not entry:
        return None
    return game_dir(game) / entry


def game_available(game: dict) -> bool:
    """True se o jogo pode ser iniciado (arquivo ou módulo do Pygame existe)."""
    modulo = game.get("modulo")
    if modulo:
        return module_available(modulo)
    entry = game_entry(game)
    return bool(entry and entry.exists())


def missing_deps(game: dict) -> list[str]:
    return [dep for dep in game["deps"] if not module_available(dep)]


def game_status(game: dict) -> tuple[str, str]:
    if not game_available(game):
        return f"{CH['bad']} AUSENTE", Fore.RED
    missing = missing_deps(game)
    if missing:
        return f"{CH['bad']} FALTA DEP", Fore.YELLOW
    return f"{CH['ok']} PRONTO", Fore.GREEN


def deps_styled(game: dict) -> str:
    parts = []
    for dep in game["deps"]:
        color = Fore.GREEN if module_available(dep) else Fore.YELLOW
        parts.append(f"{color}{dep}{Style.RESET_ALL}")
    sep = f"{Fore.LIGHTBLACK_EX}, {Style.RESET_ALL}"
    return sep.join(parts)


# ---------------------------------------------------------------------------
# Entrada de teclado (setas, OK e botão voltar de controle remoto)
# ---------------------------------------------------------------------------

def _read_key_windows() -> str:
    import msvcrt

    ch = msvcrt.getwch()
    if ch in ("\x00", "\xe0"):
        code = msvcrt.getwch()
        return {"H": "up", "P": "down", "K": "left", "M": "right"}.get(code, "")
    if ch == "\x03":
        raise KeyboardInterrupt
    if ch in ("\r", "\n"):
        return "enter"
    if ch == "\x1b":
        return "esc"
    if ch in ("\x08", "\x7f"):
        return "backspace"
    return ch.lower()


def _read_key_posix() -> str:
    import select
    import termios
    import tty

    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
        if ch == "\x03":
            raise KeyboardInterrupt
        if ch == "\x1b":
            ready, _, _ = select.select([sys.stdin], [], [], 0.05)
            if not ready:
                return "esc"
            seq = sys.stdin.read(1)
            if seq == "[":
                ready, _, _ = select.select([sys.stdin], [], [], 0.05)
                if ready:
                    code = sys.stdin.read(1)
                    return {"A": "up", "B": "down", "C": "right", "D": "left"}.get(code, "")
            return "esc"
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
    if ch in ("\r", "\n"):
        return "enter"
    if ch == "\x7f":
        return "backspace"
    return ch.lower()


def _read_key_fallback() -> str:
    try:
        line = input("» ").strip().lower()
    except EOFError:
        raise KeyboardInterrupt
    if line == "":
        return "enter"
    if line.isdigit():
        return line
    return line[:1]


def read_key() -> str:
    if not sys.stdin.isatty():
        return _read_key_fallback()
    if IS_WINDOWS:
        return _read_key_windows()
    return _read_key_posix()


# ---------------------------------------------------------------------------
# Tela principal
# ---------------------------------------------------------------------------

def footer(text: str) -> str:
    text = clip_plain(text, max(10, W - 2))
    return "  " + center(f"{Fore.LIGHTBLACK_EX}{text}{Style.RESET_ALL}", W)


def draw_main(selected: int) -> str:
    refresh_layout()
    # Com muitos jogos o logo grande não cabe: tenta o modo "tight" e, se
    # ainda faltar espaço, cai para o cabeçalho compacto de uma linha.
    big = 16 + len(GAMES)
    if big <= term_lines():
        lines = header()
    elif big - 1 <= term_lines():
        lines = header(tight=True)
    elif big - 2 <= term_lines():
        lines = header(tight=True, very_tight=True)
    else:
        lines = slim_header("JOGOS ARCADE")
    lines.append(btop())

    name_width = 18
    genre_width = 22
    heading = (
        f"   {Fore.LIGHTBLACK_EX}#  "
        f"{'JOGO':<{name_width}}{'GÊNERO':<{genre_width}}{Style.RESET_ALL}"
    )
    heading = pad(heading, INNER - 6) + f"{Fore.LIGHTBLACK_EX}STATUS{Style.RESET_ALL}"
    lines.append(brow(heading))
    lines.append(hsep())

    # Em terminais baixos a lista completa não cabe. Mostra uma janela ao
    # redor do jogo selecionado, mantendo a navegação previsível.
    total = len(GAMES)
    visible_games = max(1, term_lines() - len(lines) - 4)
    if visible_games >= total:
        start = 0
        end = total
    else:
        start = max(0, min(selected - visible_games // 2, total - visible_games))
        end = start + visible_games

    for index in range(start, end):
        game = GAMES[index]
        status_text, status_color = game_status(game)
        selected_now = selected == index

        marker = f"{game['cor']}{CH['arrow']}{Style.RESET_ALL}" if selected_now else " "
        number = f"{Fore.LIGHTBLACK_EX}{index + 1:02d}{Style.RESET_ALL}"
        if selected_now:
            name = f"{game['cor']}{Style.BRIGHT}{game['nome']}{Style.RESET_ALL}"
        else:
            name = f"{Fore.LIGHTWHITE_EX}{game['nome']}{Style.RESET_ALL}"

        name_cell = pad(name, name_width)
        genre = clip_plain(game["genero"], genre_width)
        genre_cell = f"{Fore.LIGHTBLACK_EX}{genre:<{genre_width}}{Style.RESET_ALL}"
        left = f"{marker} {number}  {name_cell}{genre_cell}"
        right = f"{status_color}{status_text}{Style.RESET_ALL}"
        gap = max(1, INNER - visible_len(left) - visible_len(right))
        lines.append(brow(left + " " * gap + right))

    lines.append(bbot())
    if end - start >= total:
        ajuda = (
            f"{CH['updown']} navegar   {CH['enter']}/OK detalhes   "
            "J jogar   D diagnóstico   Q sair"
        )
    else:
        ajuda = (
            f"{CH['updown']} navegar  {CH['enter']} detalhes  J jogar  D diag  Q sair"
            f"   {start + 1:02d}-{end:02d}/{total:02d}"
        )
    lines.append(footer(ajuda))

    # Rodapé de crédito, sem estourar a altura disponível do terminal.
    available = max(0, term_lines() - len(lines))
    if available >= 2:
        lines.append(footer(PROJECT_CREDIT))
        lines.append(footer(PROJECT_CREDIT_OPEN_SOURCE))
    elif available == 1:
        lines.append(
            footer(f"Tiago Lucas Oliveira (IFPR Londrina) · {PROJECT_URL_TEXT}")
        )
    return "\n".join(lines)


def main_menu() -> int | str | None:
    selected = 0
    total = len(GAMES)
    while True:
        render(draw_main(selected).split("\n"))
        key = read_key()

        if key in ("up", "w"):
            selected = (selected - 1) % total
        elif key in ("down", "s"):
            selected = (selected + 1) % total
        elif key == "enter":
            return selected
        elif key == "j":
            launch_game(GAMES[selected])
        elif key == "d":
            return "system"
        elif key in ("q", "esc"):
            return None
        elif key.isdigit():
            number = int(key)
            if number == 0 and len(GAMES) >= 10:
                return 9  # atalho extra: 0 abre o 10º jogo
            if 1 <= number <= len(GAMES):
                return number - 1


# ---------------------------------------------------------------------------
# Ficha do jogo — aqui ficam os "botões" de detalhes/repositório
# ---------------------------------------------------------------------------

def detail_button(text: str, focused: bool) -> str:
    if focused:
        return (
            f"{Back.LIGHTCYAN_EX}{Fore.BLACK}{Style.BRIGHT}"
            f"  {text}  {Style.RESET_ALL}"
        )
    return f"{Fore.LIGHTBLACK_EX}  {text}  {Style.RESET_ALL}"


def draw_details(index: int, message: str = "", focus: int = 0) -> str:
    refresh_layout()
    game = GAMES[index]
    accent = game["cor"]
    status_text, status_color = game_status(game)
    repo = game.get("repo")
    repo_texto = game.get("repo_texto")
    very_compact = term_lines() < 24
    ultra_compact = term_lines() < 22
    micro_compact = term_lines() < 19

    lines = slim_header("DETALHES DO JOGO", one_line=very_compact)
    lines.append(btop())
    lines.append(brow(center(f"{accent}{Style.BRIGHT}{game['nome']}{Style.RESET_ALL}", INNER)))
    meta = f"{game['genero']}  {CH['dot']}  {game['players']}  {CH['dot']}  {game['pasta']}"
    lines.append(
        brow(
            center(
                f"{Fore.LIGHTBLACK_EX}{meta}{Style.RESET_ALL}"
                f"   {status_color}{Style.BRIGHT}{status_text}{Style.RESET_ALL}",
                INNER,
            )
        )
    )
    lines.append(hsep())

    label = lambda text: brow(f"{accent}{Style.BRIGHT}{text}{Style.RESET_ALL}")
    gap = [] if COMPACT else [brow("")]

    if not ultra_compact:
        lines.append(label("VISÃO GERAL"))
    descricao = wrap(game["descricao"], INNER - 2)
    desc_limit = 1 if micro_compact else (2 if very_compact else len(descricao))
    if len(descricao) > desc_limit:
        descricao = descricao[:desc_limit]
        descricao[-1] = clip_plain(descricao[-1] + " …", INNER - 2)
    for chunk in descricao:
        lines.append(brow(f"  {chunk}"))

    lines.extend(gap)
    lines.append(label("CONTROLES"))
    for keys, action in game["controles"]:
        lines.append(
            brow(f"  {Fore.YELLOW}{Style.BRIGHT}{keys:<16}{Style.RESET_ALL}{action}")
        )

    lines.extend(gap)
    lines.append(label("FICHA TÉCNICA"))
    if very_compact:
        stack = clip_plain(" · ".join(game["stack"]), max(8, INNER - 24))
        lines.append(
            brow(
                f"  {Fore.LIGHTBLACK_EX}Stack:{Style.RESET_ALL} {stack}"
                f"   {Fore.LIGHTBLACK_EX}Deps:{Style.RESET_ALL} {deps_styled(game)}"
            )
        )
        autor = clip_plain(game["autor"], max(8, INNER - 34))
        lines.append(
            brow(
                f"  {Fore.LIGHTBLACK_EX}Licença:{Style.RESET_ALL} {game['licenca']}"
                f"   {Fore.LIGHTBLACK_EX}Autor:{Style.RESET_ALL} {autor}"
            )
        )
    else:
        lines.append(brow(f"  {Fore.LIGHTBLACK_EX}Stack:{Style.RESET_ALL} {clip_plain(' · '.join(game['stack']), INNER - 12)}"))
        lines.append(brow(f"  {Fore.LIGHTBLACK_EX}Dependências:{Style.RESET_ALL} {deps_styled(game)}"))
        lines.append(brow(f"  {Fore.LIGHTBLACK_EX}Licença:{Style.RESET_ALL} {game['licenca']}"))
        lines.append(brow(f"  {Fore.LIGHTBLACK_EX}Autor:{Style.RESET_ALL} {game['autor']}"))

    lines.extend(gap)
    if not ultra_compact:
        lines.append(label("REPOSITÓRIO ORIGINAL"))
    if repo:
        prefix = (
            f"  {Fore.LIGHTBLACK_EX}Repo:{Style.RESET_ALL} "
            if ultra_compact
            else "  "
        )
        lines.append(
            brow(f"{prefix}{Fore.LIGHTCYAN_EX}{clip_plain(repo, INNER - 10)}{Style.RESET_ALL}")
        )
    elif repo_texto:
        lines.append(brow(f"  {Fore.LIGHTYELLOW_EX}{repo_texto}{Style.RESET_ALL}"))
    else:
        lines.append(
            brow(
                f"  {Fore.LIGHTBLACK_EX}{CH['wait']} a ser adicionado "
                f"(preencha \"repo\" em console_ui.py){Style.RESET_ALL}"
            )
        )

    lines.append(hsep())
    if message:
        lines.append(brow(center(f"{Fore.YELLOW}{Style.BRIGHT}{clip_plain(message, INNER - 2)}{Style.RESET_ALL}", INNER)))
    else:
        buttons = "    ".join(
            [
                detail_button("JOGAR", focus == 0),
                detail_button("REPOSITÓRIO", focus == 1),
                detail_button("VOLTAR", focus == 2),
            ]
        )
        lines.append(brow(center(buttons, INNER)))
    lines.append(bbot())

    # Em terminais muito baixos ainda pode faltar espaço. Remove apenas os
    # rótulos de seção, preservando conteúdo e botões, até caber na altura.
    limit = max(12, term_lines())
    if len(lines) > limit:
        for marker in ("VISÃO GERAL", "CONTROLES", "FICHA TÉCNICA", "REPOSITÓRIO ORIGINAL"):
            if len(lines) <= limit:
                break
            for position, line in enumerate(lines):
                plain = ANSI_RE.sub("", line).strip(" │")
                if plain == marker:
                    lines.pop(position)
                    break
    return "\n".join(lines)


def open_repository(game: dict) -> str:
    repo = game.get("repo")
    if not repo:
        if game.get("repo_texto"):
            return f"{game['repo_texto']} — sem repositório externo."
        return "Repositório ainda não cadastrado — edite GAMES em console_ui.py."
    try:
        opened = webbrowser.open(repo)
        return (
            "Abrindo repositório no navegador..."
            if opened
            else f"Não foi possível abrir o navegador. URL: {repo}"
        )
    except Exception:
        return f"Não foi possível abrir o navegador. URL: {repo}"


def show_details(index: int) -> None:
    message = ""
    focus = 0
    while True:
        render(draw_details(index, message, focus).split("\n"))
        message = ""
        key = read_key()

        if key in ("left", "a", "up"):
            focus = (focus - 1) % 3
        elif key in ("right", "d", "down"):
            focus = (focus + 1) % 3
        elif key in ("enter", " "):
            if focus == 0:
                launch_game(GAMES[index])
            elif focus == 1:
                message = open_repository(GAMES[index])
            else:
                return
        elif key in ("v", "backspace", "esc", "q"):
            return
        elif key == "j":
            launch_game(GAMES[index])
        elif key == "r":
            message = open_repository(GAMES[index])


# ---------------------------------------------------------------------------
# Inicialização dos jogos
# ---------------------------------------------------------------------------

def launch_game(game: dict) -> None:
    refresh_layout()
    modulo = game.get("modulo")
    entry = game_entry(game)
    available = game_available(game)
    missing = missing_deps(game)
    hard_clear()
    show_cursor()

    lines = ["", ""]
    if not available:
        if modulo:
            lines.append("  " + f"{Fore.RED}{Style.BRIGHT}EXEMPLO DO PYGAME INDISPONÍVEL{Style.RESET_ALL}")
            lines.append("")
            lines.append(f"  O módulo {Fore.YELLOW}{modulo}{Style.RESET_ALL} não foi encontrado.")
            lines.append("")
            lines.append("  Atualize o Pygame para ter os exemplos oficiais:")
            lines.append("")
            lines.append(f"  {Fore.LIGHTCYAN_EX}{Path(sys.executable).name} -m pip install --upgrade pygame{Style.RESET_ALL}")
        else:
            lines.append("  " + f"{Fore.RED}{Style.BRIGHT}JOGO INDISPONÍVEL{Style.RESET_ALL}")
            lines.append("")
            lines.append(f"  Arquivo de entrada não encontrado:")
            lines.append(f"  {Fore.YELLOW}{entry}{Style.RESET_ALL}")
            lines.append("")
            lines.append("  Verifique se a pasta do jogo está dentro de games/.")
    elif missing:
        pip_list = " ".join(PIP_NAMES.get(dep, dep) for dep in missing)
        lines.append("  " + f"{Fore.YELLOW}{Style.BRIGHT}DEPENDÊNCIAS PENDENTES{Style.RESET_ALL}")
        lines.append("")
        lines.append(f"  Para jogar {Fore.WHITE}{Style.BRIGHT}{game['nome']}{Style.RESET_ALL}, instale:")
        lines.append("")
        for dep in missing:
            lines.append(f"    {Fore.YELLOW}·{Style.RESET_ALL} {PIP_NAMES.get(dep, dep)}")
        lines.append("")
        lines.append(f"  {Fore.LIGHTCYAN_EX}{Path(sys.executable).name} -m pip install {pip_list}{Style.RESET_ALL}")
    else:
        lines.append("  " + f"{game['cor']}{Style.BRIGHT}INICIANDO  {game['nome'].upper()}{Style.RESET_ALL}")
        lines.append("")
        if modulo:
            lines.append(f"  Módulo:   {Fore.WHITE}{modulo}{Style.RESET_ALL}")
            lines.append(f"  Origem:   {Fore.LIGHTBLACK_EX}embutido no Pygame{Style.RESET_ALL}")
        else:
            lines.append(f"  Pasta:    {Fore.WHITE}{game['pasta']}{Style.RESET_ALL}")
        lines.append(f"  Comando:  {Fore.LIGHTCYAN_EX}{game['comando']}{Style.RESET_ALL}")
        lines.append("")
        lines.append(f"  {Fore.LIGHTBLACK_EX}Feche a janela do jogo para voltar ao console.{Style.RESET_ALL}")
        sys.stdout.write("\n".join(lines) + "\n")
        sys.stdout.flush()

        code = None
        try:
            child_env = os.environ.copy()
            child_env.setdefault("PYTHONIOENCODING", "utf-8")
            if modulo:
                cmd = [sys.executable, "-m", modulo]
                cwd = str(BASE_DIR)
            else:
                cmd = [sys.executable, game["entry"]]
                cwd = str(game_dir(game))
            proc = subprocess.run(cmd, cwd=cwd, env=child_env)
            code = proc.returncode
        except KeyboardInterrupt:
            code = 130
        except Exception as exc:
            hard_clear()
            print(f"\n  {Fore.RED}Erro ao iniciar o jogo:{Style.RESET_ALL} {exc}")
            print(f"\n  {Fore.LIGHTBLACK_EX}Pressione qualquer tecla para voltar.{Style.RESET_ALL}")
            read_key()
            hide_cursor()
            return

        hard_clear()
        if code == 0:
            print(f"\n  {Fore.GREEN}{CH['ok']} {game['nome']} encerrado.{Style.RESET_ALL}")
        else:
            print(f"\n  {Fore.YELLOW}Jogo encerrado com código {code}.{Style.RESET_ALL}")
        print(f"\n  {Fore.LIGHTBLACK_EX}Pressione qualquer tecla para voltar ao console.{Style.RESET_ALL}")
        sys.stdout.flush()
        read_key()
        hide_cursor()
        return

    lines.append("")
    lines.append("")
    lines.append(f"  {Fore.LIGHTBLACK_EX}Pressione qualquer tecla para voltar ao console.{Style.RESET_ALL}")
    sys.stdout.write("\n".join(lines) + "\n")
    sys.stdout.flush()
    read_key()
    hide_cursor()


# ---------------------------------------------------------------------------
# Diagnóstico do sistema
# ---------------------------------------------------------------------------

def draw_system() -> str:
    refresh_layout()
    very_compact = term_lines() < 24
    ultra_compact = term_lines() < 20
    lines = slim_header("SISTEMA & DIAGNÓSTICO", one_line=very_compact)
    lines.append(btop())
    if not very_compact:
        lines.append(brow(center(f"{Fore.WHITE}{Style.BRIGHT}AMBIENTE{Style.RESET_ALL}", INNER)))
        lines.append(hsep())
    pyver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    arch = "64-bit" if sys.maxsize > 2**32 else "32-bit"
    platform_name = (
        "Windows" if IS_WINDOWS
        else "Linux" if sys.platform.startswith("linux")
        else "macOS" if sys.platform == "darwin"
        else sys.platform
    )
    lines.append(brow(f"  {Fore.LIGHTBLACK_EX}Python:{Style.RESET_ALL} {pyver} ({arch})"))
    lines.append(brow(f"  {Fore.LIGHTBLACK_EX}Sistema:{Style.RESET_ALL} {platform_name}  {CH['dot']}  terminal {term_cols()}x{term_lines()}"))
    lines.append(brow(f"  {Fore.LIGHTBLACK_EX}BoxConsole:{Style.RESET_ALL} v{APP_VERSION}  {CH['dot']}  {clip_plain(str(BASE_DIR), INNER - 38)}"))

    lines.extend([] if COMPACT else [brow("")])
    if not ultra_compact:
        lines.append(brow(f"{Fore.CYAN}{Style.BRIGHT}STATUS DOS JOGOS{Style.RESET_ALL}"))
    if COMPACT and len(GAMES) > 8:
        # Muitos jogos: mostra o status em duas colunas para caber na tela.
        col = (INNER - 2) // 2
        half = (len(GAMES) + 1) // 2

        def status_cell(game: dict) -> str:
            name = f" {game['nome']}"
            status_text, status_color = game_status(game)
            gap = max(1, col - visible_len(name) - visible_len(status_text))
            return name + " " * gap + f"{status_color}{status_text}{Style.RESET_ALL}"

        for i in range(half):
            cell = status_cell(GAMES[i])
            if i + half < len(GAMES):
                cell += "  " + status_cell(GAMES[i + half])
            lines.append(brow(cell))
    else:
        for game in GAMES:
            status_text, status_color = game_status(game)
            left = f"  {game['nome']}"
            right = f"{status_color}{status_text}{Style.RESET_ALL}"
            gap = max(1, INNER - visible_len(left) - visible_len(right))
            lines.append(brow(left + " " * gap + right))

    lines.extend([] if COMPACT else [brow("")])
    if not ultra_compact:
        lines.append(brow(f"{Fore.CYAN}{Style.BRIGHT}BIBLIOTECAS{Style.RESET_ALL}"))
    all_deps = []
    for game in GAMES:
        for dep in game["deps"]:
            if dep not in all_deps:
                all_deps.append(dep)
    dep_items = [
        f"{Fore.GREEN}{CH['ok']}{Style.RESET_ALL} {dep}" if module_available(dep)
        else f"{Fore.YELLOW}{CH['bad']}{Style.RESET_ALL} {dep}"
        for dep in all_deps
    ]
    for dep_row in pack_styled(dep_items, INNER - 2):
        lines.append(brow(f"  {dep_row}"))
    if not ultra_compact:
        lines.append(brow(f"  {Fore.LIGHTBLACK_EX}{clip_plain('Instale o que faltar com: python -m pip install <pacote>', INNER - 2)}{Style.RESET_ALL}"))
        lines.append(hsep())
    lines.append(brow(center(f"{Fore.LIGHTBLACK_EX}[ V / ESC ] VOLTAR AO CONSOLE{Style.RESET_ALL}", INNER)))
    lines.append(bbot())
    return "\n".join(lines)


def show_system() -> None:
    while True:
        render(draw_system().split("\n"))
        key = read_key()
        if key in ("v", "esc", "backspace", "q", "enter"):
            return


# ---------------------------------------------------------------------------
# Boas-vindas / saída
# ---------------------------------------------------------------------------

def goodbye() -> None:
    refresh_layout()
    hard_clear()
    show_cursor()
    lines = [
        "",
        "  " + center(brand(), W),
        "",
        "  " + center(f"{Fore.LIGHTBLACK_EX}Até a próxima partida.{Style.RESET_ALL}", W),
        "",
    ]
    sys.stdout.write("\n".join(lines) + "\n")
    sys.stdout.flush()


def main() -> None:
    enter_fullscreen()
    try:
        hard_clear()
        hide_cursor()
        while True:
            choice = main_menu()
            if choice is None:
                break
            if choice == "system":
                show_system()
            else:
                show_details(choice)
    except KeyboardInterrupt:
        pass
    finally:
        goodbye()
        leave_fullscreen()


if __name__ == "__main__":
    main()
