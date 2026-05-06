@echo off
REM LexAgent - Instalador y arranque (Windows)
where python >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Python no esta instalado o no esta en el PATH.
  exit /b 1
)
python "%~dp0install.py" %*
