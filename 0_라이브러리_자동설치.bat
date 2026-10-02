@echo off
setlocal
title [ZEUS HDD PROTECTOR] Auto Library Installer
cd /d "%~dp0"
python -m common.auto_installer
echo.
pause
