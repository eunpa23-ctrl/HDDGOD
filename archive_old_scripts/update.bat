@echo off
timeout /t 2 /nobreak >nul
taskkill /F /IM ZeusAgent.exe >nul 2>&1
move /y ZeusAgent_new.exe ZeusAgent.exe
move /y version_new.txt version.txt
start "" "ZeusAgent.exe"
del "%~f0"
