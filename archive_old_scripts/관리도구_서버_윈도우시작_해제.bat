@echo off
chcp 65001 >nul
title [제우스 HDD PROTECTOR] 서버 윈도우 시작 시 자동 실행 해제기
echo ================================================================
echo   ⚡ [제우스 HDD PROTECTOR] 서버 윈도우 시작 프로그램 해제
echo ================================================================
echo.
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "ZeusServer" /f >nul 2>&1

if %errorlevel% equ 0 (
    echo [OK] 윈도우 시작 시 서버 자동 실행이 성공적으로 해제되었습니다.
) else (
    echo [알림] 이미 등록되어 있지 않거나 해제 완료되었습니다.
)
echo.
pause
