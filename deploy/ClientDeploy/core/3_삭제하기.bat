@echo off
setlocal enabledelayedexpansion
pushd "%~dp0"
title [제우스 HDD PROTECTOR] 클라이언트 에이전트 완전 삭제 (언인스톨)
cls
echo ================================================================
echo   [제우스 HDD PROTECTOR] 클라이언트 에이전트 완전 삭제 (언인스톨)
echo ================================================================
echo.

:: 관리자 권한 확인
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [오류] 관리자 권한이 필요합니다.
    echo 마우스 우클릭 후 [관리자 권한으로 실행]을 클릭해 주세요!
    echo.
    popd >nul 2>&1
    pause
    exit /b 1
)

echo [경고] 제우스 에이전트 및 관련 설정(방화벽, 디펜더 예외, 자동실행)을
echo        시스템에서 완전히 제거합니다.
echo.
set /p CONFIRM="정말로 삭제를 진행하시겠습니까? (Y/N): "
if /i not "!CONFIRM!"=="Y" (
    echo.
    echo [취소] 삭제가 취소되었습니다.
    popd >nul 2>&1
    timeout /t 2 >nul
    exit /b 0
)

echo.
echo [1/5] 실행 중인 ZeusAgent 프로세스 종료 중...
taskkill /F /IM ZeusAgent.exe >nul 2>&1
ping 127.0.0.1 -n 2 >nul

echo [2/5] 시작프로그램 및 작업 스케줄러 등록 해제 중...
schtasks /delete /tn "ZeusAgent" /f >nul 2>&1
schtasks /delete /tn "ZeusClientAgent" /f >nul 2>&1
reg delete "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Run" /v "ZeusAgent" /f >nul 2>&1
reg delete "HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\Run" /v "ZeusAgent" /f >nul 2>&1

echo [3/5] 방화벽 허용 규칙 및 윈도우 디펜더 예외 목록 제거 중...
netsh advfirewall firewall delete rule name="ZeusAgent" >nul 2>&1
netsh advfirewall firewall delete rule name="ZeusAgent_Out" >nul 2>&1
powershell -NoProfile -Command "$ErrorActionPreference='SilentlyContinue'; Remove-MpPreference -ExclusionPath 'C:\ZeusAgent'; Remove-MpPreference -ExclusionProcess 'ZeusAgent.exe'" >nul 2>&1

echo [4/5] 바탕화면 바로가기 정리 중...
if exist "%PUBLIC%\Desktop\넷플릭스.lnk" (
    attrib -r -h -s "%PUBLIC%\Desktop\넷플릭스.lnk" >nul 2>&1
    del /f /q "%PUBLIC%\Desktop\넷플릭스.lnk" >nul 2>&1
)
if exist "%USERPROFILE%\Desktop\넷플릭스.lnk" (
    attrib -r -h -s "%USERPROFILE%\Desktop\넷플릭스.lnk" >nul 2>&1
    del /f /q "%USERPROFILE%\Desktop\넷플릭스.lnk" >nul 2>&1
)
if exist "%ALLUSERSPROFILE%\Desktop\넷플릭스.lnk" (
    attrib -r -h -s "%ALLUSERSPROFILE%\Desktop\넷플릭스.lnk" >nul 2>&1
    del /f /q "%ALLUSERSPROFILE%\Desktop\넷플릭스.lnk" >nul 2>&1
)

echo [5/5] 프로그램 설치 폴더(C:\ZeusAgent) 완전 삭제 중...
cd /d "%TEMP%"
start /b "" cmd /c "ping 127.0.0.1 -n 2 >nul & rd /s /q C:\ZeusAgent"

echo.
echo ================================================================
echo   * [삭제 완료] 제우스 클라이언트가 시스템에서 완전히 삭제되었습니다!
echo   - 프로세스, 시작프로그램, 방화벽/디펜더 설정이 초기화되었습니다.
echo ================================================================
echo.
popd >nul 2>&1
pause
exit /b 0
