#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Logs de diagnóstico do BoxConsole.

Mantém os erros fora da tela cheia: em uma TV box, um traceback impresso no
terminal normalmente não fica visível. O arquivo também recebe o dump do
``faulthandler`` se o processo morrer por falha nativa (ex.: segfault do SDL).
"""

from __future__ import annotations

import faulthandler
import os
import traceback
from datetime import datetime
from pathlib import Path

_FAULT_FILE = None


def data_dir() -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming")
    else:
        base = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share")
    path = base / "boxconsole"
    try:
        path.mkdir(parents=True, exist_ok=True)
        return path
    except OSError:
        return Path.cwd()


LOG_PATH = data_dir() / "boxconsole.log"


def log(message: str, exc_info: bool = False) -> None:
    """Acrescenta uma linha ao log, sem nunca interromper o launcher."""
    try:
        with LOG_PATH.open("a", encoding="utf-8") as stream:
            stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            stream.write(f"[{stamp}] {message}\n")
            if exc_info:
                traceback.print_exc(file=stream)
    except OSError:
        pass


def enable_faulthandler() -> None:
    """Registra falhas nativas no mesmo arquivo de log."""
    global _FAULT_FILE
    if _FAULT_FILE is not None:
        return
    try:
        _FAULT_FILE = LOG_PATH.open("a", encoding="utf-8")
        faulthandler.enable(file=_FAULT_FILE, all_threads=True)
    except Exception:
        _FAULT_FILE = None
