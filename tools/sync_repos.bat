@echo off
chcp 65001 >nul
title [제우스 HDD PROTECTOR] G드라이브 <-> C드라이브 내문서 실시간 동기화
echo [*] G:드라이브와 C:드라이브 내문서 프로젝트를 동기화합니다...
robocopy "G:\내 드라이브\PROJECT\HDDGOD" "C:\Users\USER\Documents\HDDGOD" /MIR /R:1 /W:1 /NP
echo.
echo [*] 동기화 완료!
timeout /t 3
