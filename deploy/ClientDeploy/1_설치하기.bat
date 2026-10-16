@echo off
setlocal enabledelayedexpansion
pushd "%~dp0"
title [제우스 HDD PROTECTOR] 클라이언트 에이전트 설치기
cls
echo ================================================================
echo   [제우스 HDD PROTECTOR] 클라이언트 에이전트 자동 설치 및 등록
echo ================================================================
echo.

:: 관리자 권한 확인
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [오류] 반드시 마우스 우클릭 후 [관리자 권한으로 실행]해 주세요!
    echo.
    popd >nul 2>&1
    pause
    exit /b 1
)

:STEP_KILL
echo [1/4] 실행 중인 기존 ZeusAgent 프로세스 정리 중...
taskkill /F /IM ZeusAgent.exe >nul 2>&1
ping 127.0.0.1 -n 2 >nul

echo [2/4] C:\ZeusAgent 디렉토리 준비 및 Windows Defender 예외 등록...
if not exist "C:\ZeusAgent" mkdir "C:\ZeusAgent"
powershell -NoProfile -Command "$ErrorActionPreference='SilentlyContinue'; Add-MpPreference -ExclusionPath 'C:\ZeusAgent'; Add-MpPreference -ExclusionProcess 'ZeusAgent.exe'" >nul 2>&1

echo [3/4] 최신 에이전트 바이너리 및 설정 동기화 중...
if exist "%~dp0core\ZeusAgent.exe" goto COPY_CORE
if exist "core\ZeusAgent.exe" goto COPY_CORE_REL
if exist "%~dp0ZeusAgent\ZeusAgent.exe" goto COPY_ONEDIR
if exist "ZeusAgent\ZeusAgent.exe" goto COPY_ONEDIR_REL
if exist "%~dp0ZeusAgent.exe" goto COPY_LOCAL
if exist "ZeusAgent.exe" goto COPY_LOCAL_REL
goto DOWNLOAD_SERVER

:COPY_CORE
echo   - core 패키지 파일 복사 중...
copy /y "%~dp0core\ZeusAgent.exe" "C:\ZeusAgent\ZeusAgent.exe" >nul 2>&1
copy /y "%~dp0core\config.ini" "C:\ZeusAgent\config.ini" >nul 2>&1
copy /y "%~dp0core\version.txt" "C:\ZeusAgent\version.txt" >nul 2>&1
copy /y "%~dp0core\netflix.ico" "C:\ZeusAgent\netflix.ico" >nul 2>&1
copy /y "%~dp0core\*.dll" "C:\ZeusAgent\" >nul 2>&1
copy /y "%~dp0core\3_삭제하기.bat" "C:\ZeusAgent\3_삭제하기.bat" >nul 2>&1
copy /y "%~dp03_삭제하기.bat" "C:\ZeusAgent\3_삭제하기.bat" >nul 2>&1
goto CHECK_CONFIG

:COPY_CORE_REL
echo   - core 패키지 파일(상대경로) 복사 중...
copy /y "core\ZeusAgent.exe" "C:\ZeusAgent\ZeusAgent.exe" >nul 2>&1
copy /y "core\config.ini" "C:\ZeusAgent\config.ini" >nul 2>&1
copy /y "core\version.txt" "C:\ZeusAgent\version.txt" >nul 2>&1
copy /y "core\netflix.ico" "C:\ZeusAgent\netflix.ico" >nul 2>&1
copy /y "core\*.dll" "C:\ZeusAgent\" >nul 2>&1
copy /y "core\3_삭제하기.bat" "C:\ZeusAgent\3_삭제하기.bat" >nul 2>&1
copy /y "3_삭제하기.bat" "C:\ZeusAgent\3_삭제하기.bat" >nul 2>&1
goto CHECK_CONFIG

:COPY_ONEDIR
echo   - ZeusAgent 디렉토리 동기화 중...
robocopy "%~dp0ZeusAgent" "C:\ZeusAgent" /E /NP /R:2 /W:1 >nul 2>&1
goto CHECK_CONFIG

:COPY_ONEDIR_REL
echo   - ZeusAgent 디렉토리(상대경로) 동기화 중...
robocopy "ZeusAgent" "C:\ZeusAgent" /E /NP /R:2 /W:1 >nul 2>&1
goto CHECK_CONFIG

:COPY_LOCAL
echo   - 로컬 파일 복사 중...
copy /y "%~dp0ZeusAgent.exe" "C:\ZeusAgent\ZeusAgent.exe" >nul 2>&1
copy /y "%~dp0config.ini" "C:\ZeusAgent\config.ini" >nul 2>&1
goto CHECK_CONFIG

:COPY_LOCAL_REL
echo   - 로컬 파일(상대경로) 복사 중...
copy /y "ZeusAgent.exe" "C:\ZeusAgent\ZeusAgent.exe" >nul 2>&1
copy /y "config.ini" "C:\ZeusAgent\config.ini" >nul 2>&1
goto CHECK_CONFIG

:DOWNLOAD_SERVER
echo   - 서버 다운로드: 카운터 서버(192.168.0.100)로부터 바이너리 다운로드 시도...
powershell -NoProfile -Command "Invoke-WebRequest -Uri 'http://192.168.0.100:8000/api/download/update' -OutFile 'C:\ZeusAgent\ZeusAgent.exe' -UseBasicParsing -TimeoutSec 30" >nul 2>&1
goto CHECK_CONFIG

:CHECK_CONFIG
if exist "C:\ZeusAgent\config.ini" goto CHECK_EXE
echo [CLIENT] > "C:\ZeusAgent\config.ini"
echo server_ip = 192.168.0.100 >> "C:\ZeusAgent\config.ini"
echo server_port = 8000 >> "C:\ZeusAgent\config.ini"
echo heartbeat_interval = 3 >> "C:\ZeusAgent\config.ini"
echo admin_password = 1234 >> "C:\ZeusAgent\config.ini"

:CHECK_EXE
if exist "C:\ZeusAgent\ZeusAgent.exe" goto EXE_OK
echo.
echo ================================================================
echo   [오류] C:\ZeusAgent\ZeusAgent.exe 파일이 존재하지 않습니다!
echo   네트워크 연결 상태나 배포 경로를 확인해 주세요.
echo ================================================================
echo.
pause
popd >nul 2>&1
exit /b 1

:EXE_OK
echo   - 에이전트 실행 파일 준비 완료:
dir "C:\ZeusAgent\ZeusAgent.exe" | findstr "ZeusAgent.exe"

echo.
echo [4/4] 방화벽 개방 및 윈도우 시작프로그램 자동 등록 중...
powershell -NoProfile -Command "$ErrorActionPreference='SilentlyContinue'; Get-ChildItem -Path 'C:\ZeusAgent' -Recurse | Unblock-File" >nul 2>&1
netsh advfirewall firewall add rule name="ZeusAgent" dir=in action=allow program="C:\ZeusAgent\ZeusAgent.exe" enable=yes >nul 2>&1
netsh advfirewall firewall add rule name="ZeusAgent_Out" dir=out action=allow program="C:\ZeusAgent\ZeusAgent.exe" enable=yes >nul 2>&1
reg add "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Run" /v "ZeusAgent" /t REG_SZ /d "C:\ZeusAgent\ZeusAgent.exe" /f >nul 2>&1
reg add "HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\Run" /v "ZeusAgent" /t REG_SZ /d "C:\ZeusAgent\ZeusAgent.exe" /f >nul 2>&1
schtasks /create /tn "ZeusAgent" /tr "C:\ZeusAgent\ZeusAgent.exe" /sc onlogon /rl highest /f >nul 2>&1

echo.
echo 에이전트 프로세스 백그라운드 가동 중...
ping 127.0.0.1 -n 2 >nul
start "" "C:\ZeusAgent\ZeusAgent.exe"

echo.
echo ================================================================
echo   * [설치 완료] 제우스 클라이언트 에이전트 설치가 완료되었습니다!
echo   - 작업표시줄 트레이 아이콘을 확인하세요.
echo   - 카운터 관제 대시보드(192.168.0.100:8000)에서 ONLINE을 확인하세요.
echo   - 프로그램 완전 삭제 시 [C:\ZeusAgent\3_삭제하기.bat] 를 실행하세요.
echo ================================================================
echo.
popd >nul 2>&1
pause
exit /b 0
