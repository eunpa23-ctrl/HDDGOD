@echo off
echo [*] 작업표시줄(Windows Explorer)을 새로고침하여 시작메뉴 변경사항을 즉시 반영합니다...
taskkill /f /im explorer.exe >nul 2>&1
timeout /t 1 /nobreak >nul
start explorer.exe
echo [*] 새로고침 완료!
