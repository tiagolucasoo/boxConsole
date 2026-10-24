#!/usr/bin/env bash
# BoxConsole - launcher para Linux / TV box (ARMv7)
# Não instala Pygame à força: no Debian/Ubuntu ARM o pacote do sistema
# (python3-pygame) é bem mais leve e confiável que compilar do zero.
set -u

cd "$(dirname "$0")" || exit 1
export PYGAME_HIDE_SUPPORT_PROMPT=1

PY="${BOXCONSOLE_PYTHON:-}"
if [ -n "$PY" ]; then
    if ! command -v "$PY" >/dev/null 2>&1; then
        echo "Python configurado em BOXCONSOLE_PYTHON não encontrado: $PY"
        exit 1
    fi
elif [ -n "${VIRTUAL_ENV:-}" ] && [ -x "$VIRTUAL_ENV/bin/python" ]; then
    PY="$VIRTUAL_ENV/bin/python"
else
    for cand in /usr/bin/python3 python3 python; do
        if command -v "$cand" >/dev/null 2>&1; then
            PY="$cand"
            break
        fi
    done
fi

if [ -z "$PY" ]; then
    echo "Python 3 não encontrado. Instale python3 e tente novamente."
    exit 1
fi

# colorama é obrigatório até para o menu de terminal.
if ! "$PY" -c "import colorama" >/dev/null 2>&1; then
    echo "Falta o colorama."
    echo "Debian/Ubuntu: sudo apt install python3-colorama"
    echo "Ou: $PY -m pip install --user colorama"
    exit 1
fi

# Se o Pygame não existir, main.py abre o menu de terminal automaticamente.
if ! "$PY" -c "import pygame" >/dev/null 2>&1; then
    echo "Pygame não encontrado: abrindo o menu de terminal."
    echo "Para o menu gráfico: sudo apt install python3-pygame"
fi

exec "$PY" main.py "$@"
