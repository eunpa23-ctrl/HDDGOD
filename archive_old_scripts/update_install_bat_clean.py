# -*- coding: utf-8 -*-

bat_content = """@echo off
chcp 949 >nul
title [제우스 HDD PROTECTOR] 클라이언트 에이전트 설치

pushd "%~dp0" >nul 2>&1

net session >nul 2>&1
if not errorlevel 1 goto START_INSTALL

echo ================================================================
echo   [안내] 관리자 권한 자동 승격을 요청합니다...
echo   UAC 확인 창이 뜨면 [예]를 눌러주세요.
echo ================================================================
powershell -NoProfile -Command "Start-Process cmd.exe -ArgumentList '/c pushd \\"%~dp0\\" && call \\"%~f0\\" admin' -Verb RunAs" >nul 2>&1
if not errorlevel 1 (
    popd >nul 2>&1
    exit /b 0
)

cls
echo ================================================================
echo   [필수 안내] 관리자 권한으로 실행해야 합니다!
echo.
echo   우클릭 -> [관리자 권한으로 실행]을 눌러주세요.
echo ================================================================
echo.
pause
popd >nul 2>&1
exit /b 1

:START_INSTALL
cls
echo ================================================================
echo   [제우스 HDD PROTECTOR] 클라이언트 에이전트 자동 설치 및 등록
echo ================================================================
echo.

:: ================================================================
:: [0/4] 네트워크 공유 폴더 보안 정책 최적화 (게스트 로그온 허용)
:: ================================================================
echo [0/4] 네트워크 환경 및 공유 폴더 접근 권한 구성 중...
reg add "HKLM\\SYSTEM\\CurrentControlSet\\Services\\LanmanWorkstation\\Parameters" /v AllowInsecureGuestAuth /t REG_DWORD /d 1 /f >nul 2>&1
echo   - 네트워크 게스트 공유 액세스 정책 적용 완료 [OK]
echo.

:STEP_KILL
echo [1/4] 기존 실행 중인 ZeusAgent 프로세스 정리 중...
taskkill /F /IM ZeusAgent.exe >nul 2>&1
ping 127.0.0.1 -n 2 >nul

echo [2/4] C:\\ZeusAgent 디렉토리 준비 및 백신 예외 등록...
if not exist "C:\\ZeusAgent" mkdir "C:\\ZeusAgent"
powershell -NoProfile -Command "$ErrorActionPreference='SilentlyContinue'; Add-MpPreference -ExclusionPath 'C:\\ZeusAgent'; Add-MpPreference -ExclusionProcess 'ZeusAgent.exe'" >nul 2>&1

echo [3/4] 최신 에이전트 파일 복사 중...
if exist "%~dp0core\\ZeusAgent.exe" goto COPY_CORE
if exist "core\\ZeusAgent.exe" goto COPY_CORE_REL
if exist "%~dp0ZeusAgent\\ZeusAgent.exe" goto COPY_ONEDIR
if exist "ZeusAgent\\ZeusAgent.exe" goto COPY_ONEDIR_REL
if exist "%~dp0ZeusAgent.exe" goto COPY_LOCAL
if exist "ZeusAgent.exe" goto COPY_LOCAL_REL
goto DOWNLOAD_SERVER

:COPY_CORE
echo   - core 패키지에서 최신 파일 복사 중...
copy /y "%~dp0core\\ZeusAgent.exe" "C:\\ZeusAgent\\ZeusAgent.exe" >nul 2>&1
copy /y "%~dp0core\\config.ini" "C:\\ZeusAgent\\config.ini" >nul 2>&1
copy /y "%~dp0core\\version.txt" "C:\\ZeusAgent\\version.txt" >nul 2>&1
copy /y "%~dp0core\\netflix.ico" "C:\\ZeusAgent\\netflix.ico" >nul 2>&1
copy /y "%~dp0core\\*.dll" "C:\\ZeusAgent\\" >nul 2>&1
goto CHECK_CONFIG

:COPY_CORE_REL
echo   - core 패키지(상대경로)에서 최신 파일 복사 중...
copy /y "core\\ZeusAgent.exe" "C:\\ZeusAgent\\ZeusAgent.exe" >nul 2>&1
copy /y "core\\config.ini" "C:\\ZeusAgent\\config.ini" >nul 2>&1
copy /y "core\\version.txt" "C:\\ZeusAgent\\version.txt" >nul 2>&1
copy /y "core\\netflix.ico" "C:\\ZeusAgent\\netflix.ico" >nul 2>&1
copy /y "core\\*.dll" "C:\\ZeusAgent\\" >nul 2>&1
goto CHECK_CONFIG

:COPY_ONEDIR
echo   - ZeusAgent 단일 패키지 동기화 중...
robocopy "%~dp0ZeusAgent" "C:\\ZeusAgent" /E /NP /R:2 /W:1 >nul 2>&1
goto CHECK_CONFIG

:COPY_ONEDIR_REL
echo   - ZeusAgent 단일 패키지(상대경로) 동기화 중...
robocopy "ZeusAgent" "C:\\ZeusAgent" /E /NP /R:2 /W:1 >nul 2>&1
goto CHECK_CONFIG

:COPY_LOCAL
echo   - 현재 폴더에서 파일 복사 중...
copy /y "%~dp0ZeusAgent.exe" "C:\\ZeusAgent\\ZeusAgent.exe" >nul 2>&1
copy /y "%~dp0config.ini" "C:\\ZeusAgent\\config.ini" >nul 2>&1
goto CHECK_CONFIG

:COPY_LOCAL_REL
echo   - 현재 폴더(상대)에서 파일 복사 중...
copy /y "ZeusAgent.exe" "C:\\ZeusAgent\\ZeusAgent.exe" >nul 2>&1
copy /y "config.ini" "C:\\ZeusAgent\\config.ini" >nul 2>&1
goto CHECK_CONFIG

:DOWNLOAD_SERVER
echo   - 원격 다운로드: 카운터 서버(192.168.0.100)에서 다운로드 시도...
powershell -NoProfile -Command "Invoke-WebRequest -Uri 'http://192.168.0.100:8000/api/download/update' -OutFile 'C:\\ZeusAgent\\ZeusAgent.exe' -UseBasicParsing -TimeoutSec 30" >nul 2>&1
goto CHECK_CONFIG

:CHECK_CONFIG
if exist "C:\\ZeusAgent\\config.ini" goto CHECK_EXE
echo [CLIENT] > "C:\\ZeusAgent\\config.ini"
echo server_ip = 192.168.0.100 >> "C:\\ZeusAgent\\config.ini"
echo server_port = 8000 >> "C:\\ZeusAgent\\config.ini"
echo heartbeat_interval = 3 >> "C:\\ZeusAgent\\config.ini"
echo admin_password = 1234 >> "C:\\ZeusAgent\\config.ini"

:CHECK_EXE
if exist "C:\\ZeusAgent\\ZeusAgent.exe" goto EXE_OK
echo.
echo ================================================================
echo   [오류] C:\\ZeusAgent\\ZeusAgent.exe 파일 설치에 실패했습니다!
echo   네트워크 연결 상태나 공유 권한을 확인해 주세요.
echo ================================================================
echo.
pause
popd >nul 2>&1
exit /b 1

:EXE_OK
echo   - 실행 파일 준비 완료:
dir "C:\\ZeusAgent\\ZeusAgent.exe" | findstr "ZeusAgent.exe"

echo.
echo [4/4] 방화벽 등록 및 시작프로그램 자동 실행 등록 중...
powershell -NoProfile -Command "$ErrorActionPreference='SilentlyContinue'; Get-ChildItem -Path 'C:\\ZeusAgent' -Recurse | Unblock-File" >nul 2>&1
netsh advfirewall firewall add rule name="ZeusAgent" dir=in action=allow program="C:\\ZeusAgent\\ZeusAgent.exe" enable=yes >nul 2>&1
netsh advfirewall firewall add rule name="ZeusAgent_Out" dir=out action=allow program="C:\\ZeusAgent\\ZeusAgent.exe" enable=yes >nul 2>&1
reg add "HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run" /v "ZeusAgent" /t REG_SZ /d "C:\\ZeusAgent\\ZeusAgent.exe" /f >nul 2>&1
reg add "HKCU\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run" /v "ZeusAgent" /t REG_SZ /d "C:\\ZeusAgent\\ZeusAgent.exe" /f >nul 2>&1
schtasks /create /tn "ZeusAgent" /tr "C:\\ZeusAgent\\ZeusAgent.exe" /sc onlogon /rl highest /f >nul 2>&1

echo.
echo 제우스 에이전트 프로세스 백그라운드 실행 중...
ping 127.0.0.1 -n 2 >nul
start "" "C:\\ZeusAgent\\ZeusAgent.exe"

echo.
echo ================================================================
echo   * [설치 완료] 제우스 클라이언트 에이전트 설치가 완료되었습니다!
echo   - 우측 하단 작업표시줄 트레이 아이콘을 확인하세요.
echo   - 카운터 서버 대시보드(192.168.0.100:8000)에서 ONLINE을 확인하세요.
echo ================================================================
echo.
popd >nul 2>&1
pause
exit /b 0
"""

import glob
import os

files = glob.glob(r"Z:\deploy\ClientDeploy\1_*.bat")
if files:
    target_path = files[0]
else:
    target_path = r"Z:\deploy\ClientDeploy\1_설치하기.bat"

with open(target_path, "w", encoding="cp949") as f:
    f.write(bat_content)

print(f"Updated {target_path} successfully with CP949 encoding.")
