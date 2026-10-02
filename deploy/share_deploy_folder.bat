@echo off
chcp 65001 >nul
title [제우스 HDD PROTECTOR] 관리 PC 네트워크 공유폴더 활성화
cls
echo ================================================================
echo   ⚡ 제우스 HDD PROTECTOR - 1-클릭 클라이언트 배포 공유폴더 설정
echo ================================================================
echo.

:: 관리자 권한 확인
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [오류] 마우스 우클릭 후 [관리자 권한으로 실행]을 눌러주세요.
    pause
    exit /b 1
)

set "DEPLOY_DIR=%~dp0ClientDeploy"

echo [*] 배포 폴더 경로: %DEPLOY_DIR%
echo [*] 네트워크 공유(ClientDeploy) 활성화 중...

:: 기존 공유가 있으면 삭제 후 재등록
net share ClientDeploy /delete /y >nul 2>&1
net share ClientDeploy="%DEPLOY_DIR%" /GRANT:Everyone,READ >nul 2>&1

if %errorlevel% equ 0 (
    echo.
    echo ================================================================
    echo  [성공] 네트워크 공유폴더가 활성화되었습니다!
    echo.
    echo  클라이언트 PC 10대에서 [Windows 키 + R] 누른 후 아래 경로 입력:
    echo  \\%COMPUTERNAME%\ClientDeploy
    echo.
    echo  접속 후 [1_설치하기.bat]을 우클릭하여 관리자 권한으로 실행하세요!
    echo ================================================================
) else (
    echo [오류] 공유폴더 설정 실패. 권한을 확인해주세요.
)

echo.
pause
