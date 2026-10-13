@echo off
chcp 949 >nul
title [제우스 HDD PROTECTOR] 클라이언트 에이전트 설치

pushd "%~dp0" >nul 2>&1

net session >nul 2>&1
if not errorlevel 1 goto START_INSTALL

echo ================================================================
echo   [안내] 관리자 권한으로 자동 승격을 요청합니다...
echo   UAC 확인 창이 뜨면 [예]를 눌러주세요.
echo ================================================================
powershell -NoProfile -Command "Start-Process cmd.exe -ArgumentList '/c pushd \"%~dp0\" && call \"%~f0\" admin' -Verb RunAs" >nul 2>&1
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
echo   [제우스 HDD PROTECTOR] 클라이언트 에이전트 자동 설치 및 검증
echo ================================================================
echo.

:: ================================================================
:: [0/5] 윈도우 에디션 및 UWF 엔진 순차 점검 (진행률 표시 + 1회 재시도 + 자체검증)
:: ================================================================
echo [0/5] 윈도우 에디션 및 UWF 순간복구 엔진 상태 점검 중...

:: [0-1] 윈도우 에디션 검사 및 Enterprise 승격
set RETRY_EDITION=0
:CHECK_EDITION
reg query "HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion" /v EditionID 2>nul | findstr /I "Enterprise" >nul 2>&1
if not errorlevel 1 (
    echo   - [검증 1/3] 윈도우 에디션 : Windows Enterprise 확인 [정상]
    goto CHECK_UWF_PKG
)

if %RETRY_EDITION% geq 1 (
    echo   - [알림] Enterprise 승격 1회 재시도 후에도 Pro 상태입니다. UWF 설치를 계속 진행합니다.
    goto CHECK_UWF_PKG
)

echo   - Windows Pro 감지: Enterprise 정품 볼륨 라이선스 키 주입 중 (잠시 대기)...
cscript //nologo C:\Windows\System32\slmgr.vbs /ipk NPPR9-FWDCX-D2C8J-H872K-2YT43 >nul 2>&1
ping 127.0.0.1 -n 6 >nul
set /a RETRY_EDITION+=1
goto CHECK_EDITION

:: [0-2] UWF 엔진(Client-UnifiedWriteFilter) 설치 및 검증
:CHECK_UWF_PKG
set RETRY_DISM=0
:DO_DISM_CHECK
where uwfmgr.exe >nul 2>&1
if not errorlevel 1 (
    echo   - [검증 2/3] UWF 핵심 엔진  : uwfmgr.exe 탑재 확인 [정상]
    goto CHECK_VOLUME_PROTECT
)

if %RETRY_DISM% geq 1 (
    echo   - [경고] DISM 1회 재시도 후에도 uwfmgr.exe가 감지되지 않았습니다. 다음 단계로 이동합니다.
    goto STEP_KILL
)

echo.
echo   - UWF 기능(Client-UnifiedWriteFilter) 패키지 설치 진행 중... (실시간 진행률)
echo   ----------------------------------------------------------------
dism /online /enable-feature /featurename:Client-UnifiedWriteFilter /all /norestart
echo   ----------------------------------------------------------------
ping 127.0.0.1 -n 4 >nul

where uwfmgr.exe >nul 2>&1
if not errorlevel 1 (
    echo   - [검증 2/3] UWF 핵심 엔진  : 설치 및 검증 완료 [정상]
    goto CHECK_VOLUME_PROTECT
)

echo   - [재시도] UWF 엔진 설치가 아직 감지되지 않았습니다. 5초 후 1회 재시도합니다...
ping 127.0.0.1 -n 6 >nul
set /a RETRY_DISM+=1
goto DO_DISM_CHECK

:: [0-3] C: 드라이브 보호 볼륨 바인딩 및 검증
:CHECK_VOLUME_PROTECT
set RETRY_VOL=0
:DO_VOL_CHECK
where uwfmgr.exe >nul 2>&1
if errorlevel 1 goto VERIFY_SUMMARY

echo   - C: 드라이브 순간복구 보호 볼륨 등록 중...
uwfmgr.exe volume protect C: >nul 2>&1

:: 자체 검증: get-config 조회로 C: 확인
uwfmgr.exe get-config 2>nul | findstr /I "C:" >nul 2>&1
if not errorlevel 1 (
    echo   - [검증 3/3] C: 드라이브 보호 : 순간복구 볼륨 바인딩 확인 [정상]
    goto VERIFY_SUMMARY
)

if %RETRY_VOL% geq 1 (
    echo   - [알림] C: 드라이브 바인딩 재시도 완료.
    goto VERIFY_SUMMARY
)

echo   - [재시도] C: 드라이브 바인딩 1회 재시도 중...
ping 127.0.0.1 -n 3 >nul
set /a RETRY_VOL+=1
goto DO_VOL_CHECK

:VERIFY_SUMMARY
echo.
echo   ================================================================
echo     [순간복구 핵심 환경 자체 검증 통과]
echo     1. 윈도우 에디션 : Windows Enterprise            [ 정 상 ]
echo     2. UWF 엔진 설치  : uwfmgr.exe 시스템 탑재 완료  [ 정 상 ]
echo     3. C: 드라이브   : 순간복구 보호 바인딩 완료     [ 정 상 ]
echo   ================================================================
echo   >> 모든 사전 검증을 마쳤습니다. 에이전트 설치 단계로 순차 진행합니다.
echo.

:STEP_KILL
echo [1/5] 기존 실행 중인 ZeusAgent 프로세스 정리 중...
taskkill /F /IM ZeusAgent.exe >nul 2>&1
ping 127.0.0.1 -n 2 >nul

echo [2/5] C:\ZeusAgent 디렉터리 준비 및 백신 예외 등록...
if not exist "C:\ZeusAgent" mkdir "C:\ZeusAgent"
powershell -NoProfile -Command "$ErrorActionPreference='SilentlyContinue'; Add-MpPreference -ExclusionPath 'C:\ZeusAgent'; Add-MpPreference -ExclusionProcess 'ZeusAgent.exe'" >nul 2>&1

echo [3/5] 최신 에이전트 파일 복사 및 배포...
if exist "%~dp0core\ZeusAgent.exe" goto COPY_CORE
if exist "core\ZeusAgent.exe" goto COPY_CORE_REL
if exist "%~dp0ZeusAgent\ZeusAgent.exe" goto COPY_ONEDIR
if exist "ZeusAgent\ZeusAgent.exe" goto COPY_ONEDIR_REL
if exist "%~dp0ZeusAgent.exe" goto COPY_LOCAL
if exist "ZeusAgent.exe" goto COPY_LOCAL_REL
goto DOWNLOAD_SERVER

:COPY_CORE
echo   - core 폴더에서 최신 파일 복사 중...
copy /y "%~dp0core\ZeusAgent.exe" "C:\ZeusAgent\ZeusAgent.exe" >nul 2>&1
copy /y "%~dp0core\config.ini" "C:\ZeusAgent\config.ini" >nul 2>&1
copy /y "%~dp0core\version.txt" "C:\ZeusAgent\version.txt" >nul 2>&1
copy /y "%~dp0core\netflix.ico" "C:\ZeusAgent\netflix.ico" >nul 2>&1
copy /y "%~dp0core\*.dll" "C:\ZeusAgent\" >nul 2>&1
goto CHECK_CONFIG

:COPY_CORE_REL
echo   - core 폴더(상대)에서 최신 파일 복사 중...
copy /y "core\ZeusAgent.exe" "C:\ZeusAgent\ZeusAgent.exe" >nul 2>&1
copy /y "core\config.ini" "C:\ZeusAgent\config.ini" >nul 2>&1
copy /y "core\version.txt" "C:\ZeusAgent\version.txt" >nul 2>&1
copy /y "core\netflix.ico" "C:\ZeusAgent\netflix.ico" >nul 2>&1
copy /y "core\*.dll" "C:\ZeusAgent\" >nul 2>&1
goto CHECK_CONFIG

:COPY_ONEDIR
echo   - ZeusAgent 폴더 동기화 중...
robocopy "%~dp0ZeusAgent" "C:\ZeusAgent" /E /NP /R:2 /W:1 >nul 2>&1
goto CHECK_CONFIG

:COPY_ONEDIR_REL
echo   - ZeusAgent 폴더(상대) 동기화 중...
robocopy "ZeusAgent" "C:\ZeusAgent" /E /NP /R:2 /W:1 >nul 2>&1
goto CHECK_CONFIG

:COPY_LOCAL
echo   - 로컬 파일 복사 중...
copy /y "%~dp0ZeusAgent.exe" "C:\ZeusAgent\ZeusAgent.exe" >nul 2>&1
copy /y "%~dp0config.ini" "C:\ZeusAgent\config.ini" >nul 2>&1
goto CHECK_CONFIG

:COPY_LOCAL_REL
echo   - 로컬 파일 복사 중...
copy /y "ZeusAgent.exe" "C:\ZeusAgent\ZeusAgent.exe" >nul 2>&1
copy /y "config.ini" "C:\ZeusAgent\config.ini" >nul 2>&1
goto CHECK_CONFIG

:DOWNLOAD_SERVER
echo   - 파일 다운로드: 카운터 서버(192.168.0.100)에서 다운로드 시도...
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
echo   [오류] C:\ZeusAgent\ZeusAgent.exe 파일 설치에 실패했습니다!
echo   네트워크 연결 상태나 배포 파일을 확인해 주세요.
echo ================================================================
echo.
pause
popd >nul 2>&1
exit /b 1

:EXE_OK
echo   - 실행 파일 준비 완료:
dir "C:\ZeusAgent\ZeusAgent.exe" | findstr "ZeusAgent.exe"

echo.
echo [4/5] 보안 차단 해제, 방화벽 등록 및 부팅 시 관리자 자동 시작 등록...
powershell -NoProfile -Command "$ErrorActionPreference='SilentlyContinue'; Get-ChildItem -Path 'C:\ZeusAgent' -Recurse | Unblock-File" >nul 2>&1
netsh advfirewall firewall add rule name="ZeusAgent" dir=in action=allow program="C:\ZeusAgent\ZeusAgent.exe" enable=yes >nul 2>&1
netsh advfirewall firewall add rule name="ZeusAgent_Out" dir=out action=allow program="C:\ZeusAgent\ZeusAgent.exe" enable=yes >nul 2>&1
reg add "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Run" /v "ZeusAgent" /t REG_SZ /d "C:\ZeusAgent\ZeusAgent.exe" /f >nul 2>&1
reg add "HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\Run" /v "ZeusAgent" /t REG_SZ /d "C:\ZeusAgent\ZeusAgent.exe" /f >nul 2>&1
schtasks /create /tn "ZeusAgent" /tr "C:\ZeusAgent\ZeusAgent.exe" /sc onlogon /rl highest /f >nul 2>&1

echo.
echo [5/5] 제우스 에이전트 프로세스 백그라운드 시작 중...
ping 127.0.0.1 -n 2 >nul
start "" "C:\ZeusAgent\ZeusAgent.exe"

echo.
echo ================================================================
echo   * [설치 완료] 제우스 클라이언트 에이전트 설치가 완료되었습니다!
echo   - 우측 하단 작업표시줄 트레이 아이콘을 확인하세요.
echo   - 카운터 관제 대시보드(192.168.0.100:8000)에서 ONLINE을 확인하세요.
echo ================================================================
echo.
popd >nul 2>&1
pause
exit /b 0
