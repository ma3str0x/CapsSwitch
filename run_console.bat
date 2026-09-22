@echo off
cd /d "%~dp0"
title CapsSwitch Console

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" main.py
) else (
    python main.py
)
pause
