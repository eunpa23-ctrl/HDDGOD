# -*- coding: utf-8 -*-
"""
⚡ [제우스 HDD PROTECTOR] 개발 및 검증용 가상 클라이언트 에이전트
- 1번 PC 없이 이 개발 PC에서 가상 클라이언트(PC-01 / DESKTOP-T3KLECC)를 즉각 구동
- 관제 서버 웹소켓 실시간 연결, 화면 스트리밍, 마우스 원격 제어, 넷플릭스 봇 검증
"""
import os
import sys
import asyncio
import logging
import argparse

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

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("VirtualClient")

def run():
    parser = argparse.ArgumentParser(description="가상 제우스 클라이언트")
    parser.add_argument("--id", default="DESKTOP-T3KLECC", help="클라이언트 ID (기본: DESKTOP-T3KLECC)")
    parser.add_argument("--server", default="127.0.0.1", help="서버 IP (기본: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="서버 포트 (기본: 8000)")
    args = parser.parse_args()

    print("=" * 65)
    print(f"  [Zeus Virtual Client Mode]")
    print(f"  - Client ID: {args.id}")
    print(f"  - Target Server: ws://{args.server}:{args.port}")
    print("=" * 65)

    from client.client_agent import ZeusClientAgent
    
    agent = ZeusClientAgent()
    agent.client_id = args.id
    agent.server_ip = args.server
    agent.server_port = args.port
    agent.local_ip = "127.0.0.1"

    # 가상 모드: 개발 PC 보호를 위해 OS 레벨 정책 변경(전원/시작메뉴/볼륨)은 건너뜀
    def dummy_boot():
        logger.info("[가상 모드] 개발 PC 보호를 위해 OS 전원/볼륨 강제 정책은 건너뜁니다.")
    agent.on_system_boot = dummy_boot

    # 업데이트 체크 시에도 가상 모드에서는 자기 자신 exe 덮어쓰기 건너뜀
    orig_check_update = agent.check_and_apply_update
    def virtual_check_update(force=False):
        logger.info("[가상 모드] 원격 업데이트 신호 수신 확인! (가상 모드이므로 정상 수신 로깅만 수행)")
    agent.check_and_apply_update = virtual_check_update

    # 에이전트 시작
    try:
        agent.start()
    except KeyboardInterrupt:
        logger.info("가상 클라이언트 종료.")

if __name__ == "__main__":
    run()
