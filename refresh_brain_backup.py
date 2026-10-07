# -*- coding: utf-8 -*-
"""
agent_brain_backup 폴더를 최신 성공 내역으로 갱신
"""
import os
import shutil

ROOT_DIR = r"C:\Users\USER\Documents\HDDGOD"
BACKUP_DIR = os.path.join(ROOT_DIR, "agent_brain_backup")
BRAIN_DIR = r"C:\Users\USER\.gemini\antigravity\brain\36085afd-6c99-45b2-8ff8-4ac77cbb1e5b"

# 기존 백업 디렉터리 정리
if os.path.exists(BACKUP_DIR):
    shutil.rmtree(BACKUP_DIR)
os.makedirs(BACKUP_DIR, exist_ok=True)

# 1. 제우스_최종성공_현황.md 복사
src_status = os.path.join(BRAIN_DIR, "제우스_최종성공_현황.md")
if os.path.exists(src_status):
    shutil.copy2(src_status, os.path.join(BACKUP_DIR, "제우스_최종성공_현황.md"))
    print("Copied 제우스_최종성공_현황.md")

# 2. README.md 생성 (AI 세션 복원 전용 핵심 컨텍스트)
readme_content = """# 🧠 제우스 HDD PROTECTOR - AI 세션 메모리 백업

이 폴더는 AI 보조자(Antigravity)가 세션이 초기화되거나 새 PC에서 시작할 때,
지금까지 성공적으로 검증 완료된 내역만을 바탕으로 즉시 작업을 이어가기 위한 최신 메모리 백업입니다.

## 📌 핵심 계정 및 네트워크 환경
- 카운터 PC (관제 서버): `192.168.0.100:8000`
- 1번 손님 PC: `192.168.0.91` (ID: `DESKTOP-T3KLECC`)
- 넷플릭스 계정: `eunpa23@naver.com` / `@Oep0325` (CDP 2단계 물리 키보드 로그인 검증 완료)
- 네이버 OTP IMAP: `UDT766M1ZSCP`
- GitHub 저장소: `https://github.com/eunpa23-ctrl/HDDGOD`

## 📦 현재 최신 빌드 및 배포 구조
- 빌드 방식: PyInstaller `--onedir` (폴더 통째 배포 모드, v1.0.23)
- 배포 위치: `deploy/ClientDeploy/ZeusAgent/` 및 `ZeusAgent.zip`
- 설치 방식: `install.bat` (Unblock-File + Add-MpPreference 디펜더 예외 자동 탑재)
- 원격 제어: `screen_streamer.py` (DPI 보정 + 마우스 커서 선명 오버레이 합성)

자세한 성공 내역은 `제우스_최종성공_현황.md`를 참고하세요.
"""

with open(os.path.join(BACKUP_DIR, "README.md"), "w", encoding="utf-8") as rf:
    rf.write(readme_content)
print("Created README.md in agent_brain_backup")
