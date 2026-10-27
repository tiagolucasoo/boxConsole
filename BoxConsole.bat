@echo off
title BoxConsole
cd /d "%~dp0"
chcp 65001 >nul
python main.py
if errorlevel 1 pause
