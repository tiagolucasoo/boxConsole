#!/usr/bin/env bash
# BoxConsole - launcher para Linux / TV box
# Cria um ambiente Python isolado para evitar o erro PEP 668.
set -u

cd "$(dirname "$0")" || exit 1

export PYGAME_HIDE_SUPPORT_PROMPT=1

# Prefere o Python do sistema (/usr/bin/python3), que e o que recebe o
# python3-pygame instalado pelo apt. Se ele ja tiver tudo, roda direto.
PY=""
if [ -n "${BOXCONSOLE_PYTHON:-}" ]; then
    PY="$BOXCONSOLE_PYTHON"
    if ! command -v "$PY" >/dev/null 2>&1; then
        echo "Python configurado em BOXCONSOLE_PYTHON nao encontrado: $PY"
        exit 1
    fi
    if "$PY" -c "import colorama, pygame" >/dev/null 2>&1; then
        exec "$PY" main.py "$@"
    fi
else
    for cand in /usr/bin/python3 python3 python; do
        if ! command -v "$cand" >/dev/null 2>&1; then
            continue
        fi
        [ -z "$PY" ] && PY="$cand"
        if [ -z "${BOXCONSOLE_VENV:-}" ] && "$cand" -c "import colorama, pygame" >/dev/null 2>&1; then
            exec "$cand" main.py "$@"
        fi
    done
fi

if [ -z "$PY" ]; then
    echo "Python 3 nao encontrado. Instale python3 e tente novamente."
    exit 1
fi

# Escolhe onde criar o ambiente virtual.
if [ -n "${BOXCONSOLE_VENV:-}" ]; then
    VENV_DIR="$BOXCONSOLE_VENV"
elif [ -n "${HOME:-}" ] && mkdir -p "${XDG_DATA_HOME:-$HOME/.local/share}/boxconsole" 2>/dev/null; then
    VENV_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/boxconsole/venv"
else
    VENV_DIR="$PWD/.venv"
fi

RUN_PY=""

# Reaproveita um ambiente virtual ja ativo, se houver.
if [ -n "${VIRTUAL_ENV:-}" ] && [ -x "$VIRTUAL_ENV/bin/python" ]; then
    RUN_PY="$VIRTUAL_ENV/bin/python"
    VENV_DIR="$VIRTUAL_ENV"
fi

if [ -z "$RUN_PY" ]; then
    if [ ! -x "$VENV_DIR/bin/python" ]; then
        echo "Preparando ambiente Python isolado em: $VENV_DIR"
        mkdir -p "$(dirname "$VENV_DIR")" 2>/dev/null || true
        if ! "$PY" -m venv --copies --system-site-packages "$VENV_DIR"; then
            echo
            echo "Nao foi possivel criar o ambiente virtual."
            echo "No Debian/Ubuntu/TV box, instale os pacotes do sistema:"
            echo "  sudo apt install python3-venv python3-pip python3-colorama python3-pygame"
            echo
            echo "Tentando usar o Python do sistema..."
            if "$PY" -c "import colorama" >/dev/null 2>&1; then
                exec "$PY" main.py "$@"
            fi
            echo "O colorama tambem nao esta instalado. Instale os pacotes acima e rode de novo."
            exit 1
        fi
    fi
    RUN_PY="$VENV_DIR/bin/python"
fi

if ! "$RUN_PY" -c "import colorama" >/dev/null 2>&1; then
    echo "Instalando colorama no ambiente isolado..."
    if ! "$RUN_PY" -m pip install --disable-pip-version-check --no-input colorama; then
        echo "Falha ao instalar colorama. Verifique a internet ou use:"
        echo "  sudo apt install python3-colorama"
        if "$PY" -c "import colorama" >/dev/null 2>&1; then
            echo "Usando o colorama do sistema..."
            exec "$PY" main.py "$@"
        fi
        exit 1
    fi
fi

if ! "$RUN_PY" -c "import pygame" >/dev/null 2>&1; then
    echo "Pygame nao encontrado. Tentando instalar no ambiente isolado..."
    if ! "$RUN_PY" -m pip install --disable-pip-version-check --no-input pygame; then
        echo
        echo "Nao foi possivel instalar o pygame."
        echo "O BoxConsole vai abrir no menu de terminal, sem capas."
        echo "Para o menu grafico, instale o pygame pelo sistema:"
        echo "  sudo apt install python3-pygame"
        echo "Depois rode de novo: bash boxconsole.sh"
    fi
fi

exec "$RUN_PY" main.py "$@"
