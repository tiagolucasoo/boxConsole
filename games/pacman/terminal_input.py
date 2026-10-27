"""Leitura de teclado não bloqueante para o Pac-Man no terminal.

Substitui o pacote ``keyboard`` (que exige root no Linux e não funciona bem
em TVs/consoles). Usa termios/select no Linux e msvcrt no Windows.
"""

from __future__ import annotations

import atexit
import os
import sys


class TerminalInput:
    def __init__(self) -> None:
        self._old = None
        self._enabled = False
        self.pressed: set[str] = set()
        atexit.register(self.restore)

    def enable(self) -> None:
        if self._enabled or os.name == "nt":
            self._enabled = True
            return
        if not sys.stdin.isatty():
            self._enabled = False
            return
        try:
            import termios
            import tty

            fd = sys.stdin.fileno()
            self._old = termios.tcgetattr(fd)
            tty.setcbreak(fd)
            self._enabled = True
            # Esconde o cursor durante o jogo; o menu volta a mostrá-lo.
            sys.stdout.write("\x1b[?25l")
            sys.stdout.flush()
        except Exception:
            self._old = None
            self._enabled = False

    def restore(self) -> None:
        try:
            if sys.stdout.isatty():
                sys.stdout.write("\x1b[?25h")
                sys.stdout.flush()
        except Exception:
            pass
        if self._old is None:
            self._enabled = False
            return
        try:
            import termios

            termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, self._old)
        except Exception:
            pass
        self._old = None
        self._enabled = False

    def _push(self, key: str) -> None:
        if key:
            self.pressed.add(key)

    def poll(self) -> set[str]:
        """Lê tudo que estiver disponível e devolve as teclas pressionadas."""
        self.pressed = set()
        if os.name == "nt":
            self._poll_windows()
        else:
            self._poll_posix()
        return self.pressed

    def is_pressed(self, key: str) -> bool:
        return key in self.pressed

    def _poll_windows(self) -> None:
        try:
            import msvcrt
        except ImportError:
            return
        while msvcrt.kbhit():
            ch = msvcrt.getwch()
            if ch in ("\x00", "\xe0"):
                code = msvcrt.getwch()
                self._push(
                    {
                        "H": "up",
                        "P": "down",
                        "K": "left",
                        "M": "right",
                        "\x86": "f12",
                    }.get(code, "")
                )
            elif ch == "\x1b":
                self._push("esc")
            elif ch in ("\r", "\n"):
                self._push("enter")
            else:
                self._push(ch.lower())

    def _poll_posix(self) -> None:
        if not self._enabled:
            return
        try:
            import select

            while select.select([sys.stdin], [], [], 0)[0]:
                ch = sys.stdin.read(1)
                if ch == "\x1b":
                    # Pode ser só ESC, uma seta (ESC [ A/B/C/D) ou F12
                    # (ESC [ 2 4 ~). Lê a sequência inteira antes de decidir.
                    seq = ch
                    while len(seq) < 8:
                        ready = select.select([sys.stdin], [], [], 0.02)[0]
                        if not ready:
                            break
                        seq += sys.stdin.read(1)
                        if seq[-1].isalpha() or seq[-1] == "~":
                            break
                    if seq == "\x1b":
                        self._push("esc")
                    elif seq in ("\x1b[A", "\x1b[B", "\x1b[C", "\x1b[D"):
                        self._push(
                            {"\x1b[A": "up", "\x1b[B": "down",
                             "\x1b[C": "right", "\x1b[D": "left"}[seq]
                        )
                    elif seq == "\x1b[24~":
                        self._push("f12")
                    continue
                if ch in ("\r", "\n"):
                    self._push("enter")
                else:
                    self._push(ch.lower())
        except Exception:
            pass
