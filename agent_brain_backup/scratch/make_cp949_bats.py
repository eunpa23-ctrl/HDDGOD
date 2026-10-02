# -*- coding: utf-8 -*-
import os

bat1 = """@echo off
pushd "%~dp0"
title [제우스 HDD PROTECTOR] 클라이언트 10초 원터치 자동 설치기
cls
echo ================================================================
echo   [제우스 HDD PROTECTOR] 클라이언트 10초 원터치 자동 설치
echo ================================================================
echo.

:: 관리자 권한 확인
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [오류] 마우스 우클릭 후 반드시 [관리자 권한으로 실행]을 눌러주세요!
    echo.
    popd
    pause
    exit /b 1
)

echo [1/6] 프로그램 설치 폴더 생성 및 복사 (C:\\ZeusAgent)...
if not exist "C:\\ZeusAgent" mkdir "C:\\ZeusAgent"
copy /y "core\\*.*" "C:\\ZeusAgent\\" >nul 2>&1

if not exist "C:\\ZeusAgent\\ZeusAgent.exe" (
    echo [알림] 상대경로 재시도 중...
    copy /y "%~dp0core\\*.*" "C:\\ZeusAgent\\" >nul 2>&1
)

echo [2/6] Windows UWF 순간복구 기능 활성화 중...
dism /online /enable-feature /featurename:Client-UnifiedWriteFilter /all /norestart >nul 2>&1

echo [3/6] 영구 보존 격리 예외 폴더 생성 및 등록...
if not exist "C:\\ProgramData\\NetflixProfile" mkdir "C:\\ProgramData\\NetflixProfile"
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

echo [4/6] 24시간 무인 전원 및 절전 차단 정책 적용...
powercfg /h off >nul 2>&1
powercfg /change monitor-timeout-ac 0 >nul 2>&1
powercfg /change standby-timeout-ac 0 >nul 2>&1
powercfg /change hibernate-timeout-ac 0 >nul 2>&1
powercfg -setacvalueindex SCHEME_CURRENT SUB_BUTTONS PBUTTONACTION 0 >nul 2>&1
powercfg -SetActive SCHEME_CURRENT >nul 2>&1

echo [5/6] 시작메뉴 전원 버튼(다시 시작) 복원 및 방해화면 차단...
reg delete "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Policies\\Explorer" /v "NoClose" /f >nul 2>&1
reg delete "HKLM\\Software\\Microsoft\\Windows\\CurrentVersion\\Policies\\Explorer" /v "NoClose" /f >nul 2>&1
reg add "HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\UserProfileEngagement" /v "ScoobeSystemSettingEnabled" /t REG_DWORD /d 0 /f >nul 2>&1
reg add "HKLM\\SOFTWARE\\Policies\\Microsoft\\Windows\\WindowsUpdate\\AU" /v "NoAutoRebootWithLoggedOnUsers" /t REG_DWORD /d 1 /f >nul 2>&1

echo [6/6] 윈도우 시작 시 자동 실행 등록 및 에이전트 즉시 가동...
schtasks /create /tn "ZeusClientAgent" /tr "C:\\ZeusAgent\\ZeusAgent.exe" /sc onlogon /rl highest /f >nul 2>&1
reg add "HKLM\\Software\\Microsoft\\Windows\\CurrentVersion\\Run" /v "ZeusAgent" /t REG_SZ /d "C:\\ZeusAgent\\ZeusAgent.exe" /f >nul 2>&1

:: 설치 즉시 에이전트 백그라운드 가동
start "" "C:\\ZeusAgent\\ZeusAgent.exe"

echo.
echo ================================================================
echo  [설치 완료] 제우스 클라이언트 에이전트가 가동되었습니다!
echo  작업표시줄 트레이에 [초록 방패 아이콘]이 나타납니다.
echo  시작메뉴 전원 [다시 시작] 버튼도 정상 복원되었습니다.
echo ================================================================
echo.
popd
pause
"""

for root in [r'G:\내 드라이브\PROJECT\HDDGOD', r'C:\Users\USER\Documents\HDDGOD']:
    p1 = os.path.join(root, 'deploy', 'ClientDeploy', '1_설치하기.bat')
    with open(p1, 'wb') as f:
        f.write(bat1.strip().replace('\n', '\r\n').encode('cp949'))
    print('Updated CP949 CRLF in:', root)
