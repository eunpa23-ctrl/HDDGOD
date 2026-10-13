@echo off
chcp 65001 >nul
title [제우스 HDD PROTECTOR] 관제 서버
cd /d "C:\HDDGOD"
echo ================================================================
echo   [제우스 HDD PROTECTOR] 중앙 관제 서버를 실행합니다...
echo ================================================================
"C:\Users\USER\AppData\Local\Programs\Python\Python314\python.exe" run_server.py
pause
