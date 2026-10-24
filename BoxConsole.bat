@echo off
title BoxConsole
cd /d "%~dp0"
chcp 65001 >nul
python -c "import colorama" >nul 2>&1
if errorlevel 1 python -m pip install colorama
python main.py
if errorlevel 1 pause
