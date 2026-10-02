# -*- coding: utf-8 -*-
content = '''@echo off
pushd "%~dp0"
title [제우스 HDD PROTECTOR] 클라이언트 10초 원클릭 자동 설치기
cls
echo ================================================================
echo   [제우스 HDD PROTECTOR] 클라이언트 10초 원클릭 자동 설치
echo ================================================================
echo.

:: 관리자 권한 확인
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [경고] 마우스 우클릭 후 반드시 [관리자 권한으로 실행]해주세요!
    echo.
    popd
    pause
    exit /b 1
)

echo [1/6] 프로그램 설치 폴더 복사 중 (C:\\ZeusAgent)...
if not exist "C:\\ZeusAgent" mkdir "C:\\ZeusAgent"
copy /y "core\\*.*" "C:\\ZeusAgent\\" >nul 2>&1

if not exist "C:\\ZeusAgent\\ZeusAgent.exe" (
    echo [알림] 상대경로 재시도 중...
    copy /y "%~dp0core\\*.*" "C:\\ZeusAgent\\" >nul 2>&1
)

echo [2/6] Windows UWF 순간복구 기능 활성화 중...
dism /online /enable-feature /featurename:Client-UnifiedWriteFilter /all /norestart >nul 2>&1

echo [3/6] 격리 프로필 및 필수 예외 폴더 등록 중...
if not exist "C:\\ProgramData\\NetflixProfile" mkdir "C:\\ProgramData\\NetflixProfile"
if exist "C:\\ZeusAgent\\netflix.ico" (
    copy /y "C:\\ZeusAgent\\netflix.ico" "C:\\ProgramData\\NetflixProfile\\netflix.ico" >nul 2>&1
)
uwfmgr.exe file add-exclusion "C:\\ProgramData\\NetflixProfile" >nul 2>&1
if exist "C:\\Program Files\\DAUM\\PotPlayer" (
    uwfmgr.exe file add-exclusion "C:\\Program Files\\DAUM\\PotPlayer" >nul 2>&1
)
if exist "C:\\Program Files (x86)\\PicaLive" (
    uwfmgr.exe file add-exclusion "C:\\Program Files (x86)\\PicaLive" >nul 2>&1
)
if exist "C:\\PicaLive" (
    uwfmgr.exe file add-exclusion "C:\\PicaLive" >nul 2>&1
)
if exist "C:\\Program Files (x86)\\PicaAir" (
    uwfmgr.exe file add-exclusion "C:\\Program Files (x86)\\PicaAir" >nul 2>&1
)
if not exist "C:\\ZeusAgent\\DesktopIcons" mkdir "C:\\ZeusAgent\\DesktopIcons"
uwfmgr.exe file add-exclusion "C:\\ZeusAgent" >nul 2>&1
uwfmgr.exe file add-exclusion "%APPDATA%\\Microsoft\\Windows\\Themes" >nul 2>&1

echo [4/6] 24시간 무인 전원 및 절전 정책 적용 중...
powercfg /h off >nul 2>&1
powercfg /change monitor-timeout-ac 0 >nul 2>&1
powercfg /change standby-timeout-ac 0 >nul 2>&1
powercfg /change hibernate-timeout-ac 0 >nul 2>&1
powercfg -setacvalueindex SCHEME_CURRENT SUB_BUTTONS PBUTTONACTION 0 >nul 2>&1
powercfg -SetActive SCHEME_CURRENT >nul 2>&1

echo [5/6] 시작메뉴 전원 버튼(종료 숨김, 다시시작 유지) 및 최적화 설정...
reg delete "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Policies\\Explorer" /v "NoClose" /f >nul 2>&1
reg delete "HKLM\\Software\\Microsoft\\Windows\\CurrentVersion\\Policies\\Explorer" /v "NoClose" /f >nul 2>&1
reg add "HKLM\\SOFTWARE\\Microsoft\\PolicyManager\\default\\Start\\HideShutDown" /v "value" /t REG_DWORD /d 1 /f >nul 2>&1
reg add "HKLM\\SOFTWARE\\Microsoft\\PolicyManager\\current\\device\\Start" /v "HideShutDown" /t REG_DWORD /d 1 /f >nul 2>&1
reg add "HKLM\\SOFTWARE\\Microsoft\\PolicyManager\\default\\Start\\HideRestart" /v "value" /t REG_DWORD /d 0 /f >nul 2>&1
reg add "HKLM\\SOFTWARE\\Policies\\Microsoft\\Windows\\WindowsUpdate\\AU" /v "NoAutoRebootWithLoggedOnUsers" /t REG_DWORD /d 1 /f >nul 2>&1
:: 윈도우 원격 데스크톱(RDP) 서비스 활성화 및 방화벽 허용
reg add "HKLM\\System\\CurrentControlSet\\Control\\Terminal Server" /v "fDenyTSConnections" /t REG_DWORD /d 0 /f >nul 2>&1
netsh advfirewall firewall set rule group="remote desktop" new enable=Yes >nul 2>&1
netsh advfirewall firewall set rule group="원격 데스크톱" new enable=Yes >nul 2>&1

echo [6/6] 부팅 시 자동 시작 등록 및 에이전트 실행 중...
schtasks /create /tn "ZeusClientAgent" /tr "C:\\ZeusAgent\\ZeusAgent.exe" /sc onlogon /rl highest /f >nul 2>&1
reg add "HKLM\\Software\\Microsoft\\Windows\\CurrentVersion\\Run" /v "ZeusAgent" /t REG_SZ /d "C:\\ZeusAgent\\ZeusAgent.exe" /f >nul 2>&1

:: 설치 후 에이전트 백그라운드 즉시 실행
start "" "C:\\ZeusAgent\\ZeusAgent.exe"

echo.
echo ================================================================
echo  [설치 완료] 제우스 클라이언트 세팅이 완료되었습니다!
echo  - 작업표시줄 트레이에 [초록 방패 아이콘]이 나타납니다.
echo  - 시작메뉴 전원에 [다시 시작] 버튼이 활성화되었습니다. (종료버튼 숨김)
echo  - 바탕화면에 [넷플릭스] 바로가기 아이콘이 등록되었습니다.
echo ================================================================
echo.
popd
pause
'''

crlf_content = content.replace('\r\n', '\n').replace('\n', '\r\n')
paths = [
    r'G:\내 드라이브\PROJECT\HDDGOD\deploy\ClientDeploy\1_설치하기.bat',
    r'C:\Users\USER\Documents\HDDGOD\deploy\ClientDeploy\1_설치하기.bat'
]
for p in paths:
    with open(p, 'wb') as f:
        f.write(crlf_content.encode('cp949'))
    print('Wrote CP949 CRLF to:', p)
