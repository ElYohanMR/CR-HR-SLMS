@echo off
cd /d "%~dp0"
start "" "%LOCALAPPDATA%\SamtecLockers\venvs\dev\Scripts\pythonw.exe" "%~dp0launch.pyw" --configure
