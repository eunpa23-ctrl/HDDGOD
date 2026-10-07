import os

content_install = """@echo off
pushd "%~dp0"
title [제우스 HDD PROTECTOR] 클라이언트 원클릭 자동 설치기
cls
echo ================================================================
echo   [제우스 HDD PROTECTOR] 클라이언트 원클릭 자동 설치
echo ================================================================
echo.

:: 관리자 권한 확인
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [경고] 제우스 원클릭 설치 프로그램은 반드시 [관리자 권한으로 실행]해주세요!
    echo.
    popd
    pause
    exit /b 1
)

echo [1/6] 프로그램 설치 폴더 생성 및 기존 프로세스 종료 중 (C:\\ZeusAgent)...
taskkill /F /IM ZeusAgent.exe >nul 2>&1
ping 127.0.0.1 -n 2 >nul
if not exist "C:\\ZeusAgent" mkdir "C:\\ZeusAgent"
copy /y "core\\*.*" "C:\\ZeusAgent\\" >nul 2>&1

if not exist "C:\\ZeusAgent\\ZeusAgent.exe" (
    echo [알림] UNC 네트워크 경로 대응 복사 중...
    copy /y "%~dp0core\\*.*" "C:\\ZeusAgent\\" >nul 2>&1
)

echo [2/6] Windows UWF (통합 쓰기 필터) 기능 활성화 중...
dism /online /enable-feature /featurename:Client-UnifiedWriteFilter /all /norestart >nul 2>&1

echo [3/6] 방화벽 설정 및 예외 처리 중...
netsh advfirewall firewall add rule name="ZeusAgent" dir=in action=allow program="C:\\ZeusAgent\\ZeusAgent.exe" enable=yes >nul 2>&1
netsh advfirewall firewall add rule name="ZeusAgent_Out" dir=out action=allow program="C:\\ZeusAgent\\ZeusAgent.exe" enable=yes >nul 2>&1

echo [4/6] 시작프로그램 등록 중...
reg add "HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run" /v "ZeusAgent" /t REG_SZ /d "\\"C:\\ZeusAgent\\ZeusAgent.exe\\"" /f >nul 2>&1

echo [5/6] 윈도우 디펜더 예외 처리 중...
powershell -Command "Add-MpPreference -ExclusionPath 'C:\\ZeusAgent'" >nul 2>&1
powershell -Command "Add-MpPreference -ExclusionProcess 'ZeusAgent.exe'" >nul 2>&1

echo [6/6] 제우스 에이전트 최초 실행 중...
start "" "C:\\ZeusAgent\\ZeusAgent.exe"

echo.
echo ================================================================
echo   [완료] 제우스 HDD PROTECTOR 설치가 완료되었습니다!
echo   우측 하단 트레이 아이콘을 확인하세요.
echo ================================================================
echo.
popd
pause
"""

content_inspect = """@echo off
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
dir C:\\ZeusAgent

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
"""

with open(r"G:\내 드라이브\PROJECT\HDDGOD\deploy\ClientDeploy\1_설치하기.bat", "w", encoding="cp949") as f:
    f.write(content_install)

with open(r"G:\내 드라이브\PROJECT\HDDGOD\deploy\ClientDeploy\2_정밀검수.bat", "w", encoding="cp949") as f:
    f.write(content_inspect)

print("Batch files created with cp949 encoding.")
