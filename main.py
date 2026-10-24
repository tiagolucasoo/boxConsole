#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""BoxConsole — entrada principal.

O menu Pygame é o modo padrão, com capas em ``images/``.
Se o Pygame não estiver disponível (ou a tela falhar), o mesmo launcher abre
automaticamente o menu de terminal, que continua completo em ``console_ui.py``.

Uso:
    python main.py              # menu Pygame (fallback automático)
    python main.py --windowed   # menu Pygame em janela
    python main.py --terminal   # força o menu de terminal

Teclas no menu Pygame:
    ← → / ↑ ↓ ou W A S D  navegar
    Enter / OK            abrir detalhes
    J                     jogar direto
    D                     diagnóstico
    F11                   tela cheia / janela
    ESC / Backspace / Q   sair
"""

from __future__ import annotations

import os
import sys
import traceback

# Evita o banner do pygame ao iniciar o menu.
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

# Garante acentos e setas no texto de ajuda também no terminal do Windows.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def run_terminal() -> None:
    """Abre o menu de terminal (modo secundário)."""
    import console_ui

    console_ui.main()


def run_pygame(windowed: bool = False) -> None:
    """Abre o menu Pygame (modo principal)."""
    import pygame_ui

    pygame_ui.main(fullscreen=not windowed)


def main(argv: list[str] | None = None) -> None:
    args = list(sys.argv[1:] if argv is None else argv)

    if "--help" in args or "-h" in args:
        print(__doc__)
        return

    if "--terminal" in args:
        run_terminal()
        return

    try:
        import pygame  # noqa: F401
    except ImportError:
        print("Pygame não encontrado. Abrindo o menu de terminal...")
        print("Para usar o menu com capas, instale pygame (ex.: sudo apt install python3-pygame).")
        print("No Linux/TV box, instale pelo sistema: sudo apt install python3-pygame")
        run_terminal()
        return

    windowed = "--windowed" in args or os.environ.get("BOXCONSOLE_WINDOWED") == "1"
    try:
        run_pygame(windowed=windowed)
    except KeyboardInterrupt:
        pass
    except Exception:
        print("\nO menu Pygame não pôde ser aberto.")
        traceback.print_exc()
        print("\nAbrindo o menu de terminal como reserva...\n")
        try:
            import pygame

            pygame.quit()
        except Exception:
            pass
        run_terminal()


if __name__ == "__main__":
    main()
