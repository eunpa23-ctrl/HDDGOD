@echo off
setlocal
chcp 949 >nul
title [제우스 HDD PROTECTOR] 클라이언트 원클릭 설치

:: 관리자 권한 확인 및 VBScript 승격
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [안내] 관리자 권한을 획득하는 중입니다...
    echo Set UAC = CreateObject^("Shell.Application"^) > "%temp%\getadmin.vbs"
    echo UAC.ShellExecute "cmd.exe", "/k pushd %~dp0 ^&^& call %~f0 admin", "", "runas", 1 >> "%temp%\getadmin.vbs"
    "%temp%\getadmin.vbs"
    del "%temp%\getadmin.vbs" >nul 2>&1
    exit /b
)

pushd "%~dp0" >nul 2>&1
cls
echo ================================================================
echo   [제우스 HDD PROTECTOR] 클라이언트 원클릭 자동 설치
echo ================================================================
echo.

echo [1/5] 기존 ZeusAgent 프로세스 정리 중...
taskkill /F /IM ZeusAgent.exe >nul 2>&1
ping 127.0.0.1 -n 2 >nul

echo [2/5] C:\ZeusAgent 배포 및 복사 중...
if not exist "C:\ZeusAgent" mkdir "C:\ZeusAgent"

:: ZeusAgent 폴더 통째로 복사 (robocopy 사용 - 가장 빠르고 완벽한 복사)
if exist "%~dp0ZeusAgent" (
    robocopy "%~dp0ZeusAgent" "C:\ZeusAgent" /E /NP /R:2 /W:1 >nul 2>&1
) else if exist "ZeusAgent" (
    robocopy "ZeusAgent" "C:\ZeusAgent" /E /NP /R:2 /W:1 >nul 2>&1
) else if exist "%~dp0ZeusAgent.zip" (
    tar -xf "%~dp0ZeusAgent.zip" -C "C:\ZeusAgent" >nul 2>&1
) else if exist "ZeusAgent.zip" (
    tar -xf "ZeusAgent.zip" -C "C:\ZeusAgent" >nul 2>&1
)

if not exist "C:\ZeusAgent\ZeusAgent.exe" (
    echo.
    echo [오류] 배포 파일 복사에 실패했습니다!
    echo 네트워크 공유 폴더 연결 상태를 확인해주세요.
    echo.
    popd >nul 2>&1
    pause
    exit /b
)

echo.
echo [*] 파일 복사 성공 확인:
dir "C:\ZeusAgent\ZeusAgent.exe" | findstr "ZeusAgent.exe"
echo.

echo [3/5] 디펜더 실시간 감시 예외 등록 및 다운로드 차단 해제...
powershell -Command "Add-MpPreference -ExclusionPath 'C:\ZeusAgent'" >nul 2>&1
powershell -Command "Add-MpPreference -ExclusionProcess 'ZeusAgent.exe'" >nul 2>&1
powershell -Command "Get-ChildItem -Path 'C:\ZeusAgent' -Recurse | Unblock-File" >nul 2>&1

echo [4/5] 방화벽 및 시작프로그램 자동 등록...
netsh advfirewall firewall add rule name="ZeusAgent" dir=in action=allow program="C:\ZeusAgent\ZeusAgent.exe" enable=yes >nul 2>&1
netsh advfirewall firewall add rule name="ZeusAgent_Out" dir=out action=allow program="C:\ZeusAgent\ZeusAgent.exe" enable=yes >nul 2>&1
reg add "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Run" /v "ZeusAgent" /t REG_SZ /d ""C:\ZeusAgent\ZeusAgent.exe"" /f >nul 2>&1

echo [5/5] 제우스 에이전트 실행 중...
start "" "C:\ZeusAgent\ZeusAgent.exe"

echo.
echo ================================================================
echo   ★ [설치 완료] 제우스 클라이언트 설치가 성공적으로 완료되었습니다!
echo   우측 하단 트레이 아이콘을 확인하세요.
echo ================================================================
echo.
popd >nul 2>&1
pause
