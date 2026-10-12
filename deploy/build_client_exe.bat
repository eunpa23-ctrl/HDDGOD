@echo off
title ZeusAgent Builder
cls
echo ================================================================
echo   ZeusAgent Client Builder (OneFile)
echo ================================================================
echo.
cd /d "%~dp0.."
echo [*] Checking PyInstaller...
python -m pip install -q pyinstaller
echo [*] Compiling ZeusAgent (takes ~30s)...
pyinstaller --clean --noconfirm --onefile --windowed --name "ZeusAgent" --hidden-import "pystray._win32" --add-data "common;common" --add-data "client;client" --add-binary "deploy\ClientDeploy\core\vcruntime140.dll;." --add-binary "deploy\ClientDeploy\core\vcruntime140_1.dll;." run_client.py
if exist "dist\ZeusAgent.exe" (
    echo.
    echo [*] Build Complete! Copying to deploy folder...
    if not exist "deploy\ClientDeploy\core" mkdir "deploy\ClientDeploy\core"
    copy /y "dist\ZeusAgent.exe" "deploy\ClientDeploy\core\ZeusAgent.exe" >nul 2>&1
    if exist "dist\deploy\ClientDeploy\core" copy /y "dist\ZeusAgent.exe" "dist\deploy\ClientDeploy\core\ZeusAgent.exe" >nul 2>&1
    if exist "dist\deploy\ClientDeploy\ZeusAgent.zip" del /f /q "dist\deploy\ClientDeploy\ZeusAgent.zip" >nul 2>&1
    if exist "deploy\ClientDeploy\ZeusAgent.zip" del /f /q "deploy\ClientDeploy\ZeusAgent.zip" >nul 2>&1
    echo.
    echo ================================================================
    echo  [SUCCESS] ZeusAgent.exe is ready!
    echo ================================================================
) else (
    echo.
    echo [ERROR] Build failed.
)
echo.
pause
