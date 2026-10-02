@echo off
pushd "%~dp0"
title [제우스 HDD PROTECTOR] 클라이언트 정밀 검수 도구
cls
echo ================================================================
echo   [제우스 HDD PROTECTOR] 클라이언트 정밀 검수
echo ================================================================
echo.

:: 관리자 권한 확인
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [경고] 반드시 [관리자 권한으로 실행]해주세요!
    echo.
    popd
    pause
    exit /b 1
)

echo 1. 통신 확인 중...
ping 192.168.0.100 -n 4

echo.
echo 2. 설치 폴더 확인...
dir C:\ZeusAgent

echo.
echo 3. 제우스 에이전트 프로세스 확인...
tasklist | findstr ZeusAgent.exe

echo.
echo 4. UWF 상태 확인...
uwfmgr filter get-config

echo.
echo ================================================================
echo   [완료] 검수가 완료되었습니다.
echo ================================================================
echo.
popd
pause
