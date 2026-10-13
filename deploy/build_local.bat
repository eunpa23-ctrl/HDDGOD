@echo off
setlocal
cd /d "%~dp0.."
set "PY=C:\Users\pc03\AppData\Local\Programs\Python\Python314\python.exe"
set "PYINSTALLER=C:\Users\pc03\AppData\Local\Programs\Python\Python314\Scripts\pyinstaller.exe"

echo [*] Starting PyInstaller Build...
"%PYINSTALLER%" --clean --noconfirm --onefile --windowed --name "ZeusAgent" --hidden-import "pystray._win32" --add-data "common;common" --add-data "client;client" --add-binary "deploy\ClientDeploy\core\vcruntime140.dll;." --add-binary "deploy\ClientDeploy\core\vcruntime140_1.dll;." run_client.py

if exist "dist\ZeusAgent.exe" (
    echo [*] Copying to deploy folder...
    copy /y "dist\ZeusAgent.exe" "deploy\ClientDeploy\core\ZeusAgent.exe" >nul
    echo [SUCCESS] Build completed!
) else (
    echo [ERROR] Build failed!
)