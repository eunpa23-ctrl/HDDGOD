@echo off
chcp 65001 >nul
title [제우스 HDD PROTECTOR] 클라이언트 ZeusAgent 폴더 배포 빌더
cls
echo ================================================================
echo   ⚡ 제우스 HDD PROTECTOR - 클라이언트 폴더(onedir) 패키지 빌드
echo ================================================================
echo.

cd /d "%~dp0.."

echo [*] PyInstaller 설치 확인...
python -m pip install -q pyinstaller

echo [*] ZeusAgent 폴더 컴파일 시작 (약 30초 소요)...
pyinstaller --noconfirm --onedir --windowed --name "ZeusAgent" ^
    --hidden-import "pystray._win32" ^
    --add-data "common;common" ^
    --add-data "client;client" ^
    run_client.py

if exist "dist\ZeusAgent\ZeusAgent.exe" (
    echo.
    echo [*] 빌드 완료! 패키징 및 배포 동기화 중...
    python deploy\package_and_deploy.py
    echo.
    echo ================================================================
    echo  🎉 [성공] ZeusAgent 폴더 및 ZeusAgent.zip 배포가 완료되었습니다!
    echo ================================================================
) else (
    echo.
    echo [오류] 빌드에 실패했습니다. 파이썬 환경을 확인해주세요.
)

echo.
pause
