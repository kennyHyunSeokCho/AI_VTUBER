@echo off
echo Starting Voice Blend Backend...
call .venv\Scripts\activate.bat
cd /d "%~dp0"
set PYTHONPATH=%CD%
python backend/main.py

