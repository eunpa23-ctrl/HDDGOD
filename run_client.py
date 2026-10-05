# -*- coding: utf-8 -*-
"""
⚡ [제우스 HDD PROTECTOR] 클라이언트 에이전트 실행기
- 누락된 패키지가 있을 시 packages/ 폴더에서 오프라인 자동 설치 후 에이전트 실행
"""
import os
import sys

# 프로젝트 루트 경로를 sys.path에 추가
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
os.chdir(ROOT_DIR)

# 1. 넷플릭스 바로가기 단독 호출 시 크롬 실행 후 즉시 종료 (중복 실행 락 검사 전에 최우선 처리)
if len(sys.argv) > 1 and "--launch-netflix" in sys.argv:
    try:
        from client.netflix_bot import NetflixBot
        bot = NetflixBot()
        bot.launch_chrome_with_cdp()
    except Exception as e:
        pass
    sys.exit(0)

# ── 중복 실행 방지: 소켓 포트 점유 방식 (TIME_WAIT 안전 재시도) ───────
import socket as _sock
import time as _t
_lock_bound = False
for _try in range(10):
    try:
        _lock_sock = _sock.socket(_sock.AF_INET, _sock.SOCK_STREAM)
        _lock_sock.setsockopt(_sock.SOL_SOCKET, _sock.SO_REUSEADDR, 1)
        _lock_sock.bind(("127.0.0.1", 47890))
        _lock_bound = True
        break
    except OSError:
        _t.sleep(1)

if not _lock_bound:
    sys.exit(0)  # 10초 대기 후에도 포트 점유 중이면 이미 실행 중인 다른 인스턴스가 존재함
# ─────────────────────────────────────────────────────────────────

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# 자동 패키지 검사 및 누락 시 packages/ 폴더에서 오프라인 자동 설치
from common.auto_installer import ensure_dependencies
ensure_dependencies(ROOT_DIR)

print("=" * 60)
print("  ⚡ [제우스 HDD PROTECTOR] 클라이언트 에이전트 가동")
print("=" * 60)

import time
try:
    from client.client_agent import ZeusClientAgent
    agent = ZeusClientAgent()
    agent.start()
except KeyboardInterrupt:
    pass
except Exception as e:
    import traceback
    err_text = traceback.format_exc()
    try:
        log_dir = r"C:\ZeusAgent" if os.path.exists(r"C:\ZeusAgent") else ROOT_DIR
        with open(os.path.join(log_dir, "crash.log"), "a", encoding="utf-8") as f:
            f.write(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] 에이전트 비정상 종료:\n{err_text}\n")
    except Exception:
        pass
    if sys.stdout and sys.stdin and not getattr(sys, "frozen", False):
        print(f"\n[오류 발생] {e}")
        input("\n엔터 키를 누르면 창을 닫습니다...")
    sys.exit(1)
