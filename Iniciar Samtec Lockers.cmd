@echo off
cd /d "%~dp0"
if not exist "%LOCALAPPDATA%\SamtecLockers\venvs\dev\Scripts\pythonw.exe" (
    echo Falta el entorno de Python. Ejecuta scripts\setup.ps1 primero.
    pause
    exit /b 1
)
start "" "%LOCALAPPDATA%\SamtecLockers\venvs\dev\Scripts\pythonw.exe" "%~dp0launch.pyw"
