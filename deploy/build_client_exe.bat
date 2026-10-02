@echo off
chcp 65001 >nul
title [제우스 HDD PROTECTOR] 클라이언트 ZeusAgent.exe 무설치 단일 빌더
cls
echo ================================================================
echo   ⚡ 제우스 HDD PROTECTOR - 클라이언트 단일 실행 파일(EXE) 빌드
echo ================================================================
echo.

cd /d "%~dp0.."

echo [*] PyInstaller 설치 확인...
python -m pip install -q pyinstaller

echo [*] ZeusAgent.exe 무설치 단일 파일 컴파일 시작 (약 1분 소요)...
pyinstaller --noconfirm --onefile --windowed --name "ZeusAgent" ^
    --hidden-import "pystray._win32" ^
    --add-data "common;common" ^
    --add-data "client;client" ^
    run_client.py

if exist "dist\ZeusAgent.exe" (
    echo.
    echo [*] 빌드 완료! 배포 폴더(deploy\ClientDeploy\core)로 파일 복사 중...
    if not exist "deploy\ClientDeploy\core" mkdir "deploy\ClientDeploy\core"
    copy /y "dist\ZeusAgent.exe" "deploy\ClientDeploy\core\ZeusAgent.exe" >nul 2>&1
    echo.
    echo ================================================================
    echo  🎉 [성공] ZeusAgent.exe 배포 파일 생성이 완료되었습니다!
    echo  위치: deploy\ClientDeploy\core\ZeusAgent.exe
    echo ================================================================
) else (
    echo.
    echo [오류] 빌드에 실패했습니다. 파이썬 환경을 확인해주세요.
)

echo.
pause
