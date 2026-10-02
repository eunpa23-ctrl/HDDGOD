@echo off
chcp 65001 >nul
title [제우스 HDD PROTECTOR] 서버 윈도우 시작 시 자동 실행 등록기
echo ================================================================
echo   ⚡ [제우스 HDD PROTECTOR] 서버 윈도우 시작 프로그램 등록
echo ================================================================
echo.
set "VBS_PATH=%~dp0서버실행.vbs"
reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "ZeusServer" /t REG_SZ /d "wscript.exe \"%VBS_PATH%\"" /f >nul 2>&1

if %errorlevel% equ 0 (
    echo [OK] 윈도우 시작 시 서버 자동 실행이 성공적으로 등록되었습니다!
    echo       등록 위치: HKCU\Software\Microsoft\Windows\CurrentVersion\Run -^> ZeusServer
    echo       실행 명령: wscript.exe "%VBS_PATH%"
) else (
    echo [오류] 레지스트리 등록에 실패했습니다. 관리자 권한을 확인하세요.
)
echo.
pause
