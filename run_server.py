# -*- coding: utf-8 -*-
import os
import sys

# 프로젝트 루트 경로를 최우선 sys.path 및 작업 디렉터리로 설정
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
os.chdir(ROOT_DIR)

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# 자동 패키지 검사 및 누락 시 packages/ 폴더에서 오프라인 자동 설치
from common.auto_installer import ensure_dependencies
ensure_dependencies(ROOT_DIR)

from common.config import SERVER_HOST, SERVER_PORT, CLIENT_SERVER_IP

# 대시보드 접속 URL 결정 (설정된 서버 IP 우선 적용)
target_ip = CLIENT_SERVER_IP if (CLIENT_SERVER_IP and CLIENT_SERVER_IP != '0.0.0.0') else (SERVER_HOST if SERVER_HOST != '0.0.0.0' else '127.0.0.1')
dashboard_url = f"http://{target_ip}:{SERVER_PORT}"

print("=" * 60)
print("  ⚡ [제우스 HDD PROTECTOR] 관리 PC 중앙 관제 서버")
print("=" * 60)
print(f"[*] 프로젝트 위치: {ROOT_DIR}")
print(f"[*] 관제 대시보드 주소: {dashboard_url}")
print("[*] 관제 서버를 가동합니다... (종료: Ctrl + C)")
print("=" * 60)

import socket
import webbrowser
import time

def is_port_active(host, port):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.8)
        res = (s.connect_ex((host, port)) == 0)
        s.close()
        return res
    except Exception:
        return False

# 이미 서버가 실행 중인지 감지 (중복 실행 방지 및 브라우저 즉시 오픈)
try:
    if is_port_active(target_ip, SERVER_PORT) or is_port_active("127.0.0.1", SERVER_PORT):
        print(f"[*] 관제 서버가 이미 백그라운드에서 동작 중입니다!")
        print(f"[*] 관제 대시보드 브라우저 화면을 엽니다: {dashboard_url}")
        webbrowser.open(dashboard_url)
        time.sleep(1.5)
        sys.exit(0)
except Exception:
    pass

try:
    import uvicorn
    import threading
    from server.server_core import app

    def open_browser():
        time.sleep(1.2)
        try:
            webbrowser.open(dashboard_url)
        except Exception:
            pass

    threading.Thread(target=open_browser, daemon=True).start()
    uvicorn.run(app, host=SERVER_HOST, port=SERVER_PORT, reload=False)
except KeyboardInterrupt:
    print("\n[*] 서버가 정상적으로 종료되었습니다.")
    sys.exit(0)
except Exception as e:
    print(f"\n[오류 발생] {e}")
    sys.exit(1)
