# -*- coding: utf-8 -*-
r"""
제우스 HDD PROTECTOR - 클라이언트 통합 백그라운드 에이전트 데몬
G:\내 드라이브\PROJECT\HDDGOD\client\client_agent.py
"""
import os
import sys
import time
import socket
import uuid
import json
import threading
import logging
import asyncio
import websockets
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from common.config import CLIENT_SERVER_IP, CLIENT_SERVER_PORT, HEARTBEAT_INTERVAL
from common.protocol import (
    PacketType, CommandType, UWFStatus, NetflixStatus, make_packet, parse_packet
)
from client.uwf_controller import UWFController
from client.power_policy import PowerPolicy
from client.windows_optimizer import WindowsOptimizer
from client.netflix_bot import NetflixBot
from client.screen_streamer import ScreenStreamer
from client.client_tray import ClientTrayUI
from client.log_streamer import WebSocketLogHandler

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s"
)
logger = logging.getLogger("ZeusAgent")

class ZeusClientAgent:
    """클라이언트 PC 통합 제어 백그라운드 서비스"""

    def __init__(self):
        self.server_ip = CLIENT_SERVER_IP
        self.server_port = CLIENT_SERVER_PORT
        self.client_id = self.get_client_identity()
        self.local_ip = self.get_local_ip()
        self.mac_addr = self.get_mac_address()

        self.netflix_bot = NetflixBot()
        self.streamer = ScreenStreamer()
        self.is_streaming_screen = False
        self.ws_conn = None
        self.otp_needed = False
        self.otp_sent = False
        self.cred_needed = False
        self.cred_requested = 0

        # 실시간 로그 스트리머: 모든 로그를 서버 대시보드로 자동 전송
        self.ws_log_handler = WebSocketLogHandler(agent_ref=self, level=logging.INFO)
        logging.getLogger().addHandler(self.ws_log_handler)

    def get_client_identity(self) -> str:
        """호스트명 기반 고유 클라이언트 ID 생성 (예: PC-01)"""
        hostname = socket.gethostname()
        return hostname

    def get_local_ip(self) -> str:
        # 1. 관리 서버 IP를 목적지로 소켓을 연결하여 실제 통신 중인 로컬 LAN IP 추출 (가장 정확)
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect((self.server_ip, int(self.server_port)))
            ip = s.getsockname()[0]
            s.close()
            if ip and not ip.startswith("127."):
                return ip
        except Exception:
            pass

        # 2. 공인 DNS 대상 폴백
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            if ip and not ip.startswith("127."):
                return ip
        except Exception:
            pass

        return "127.0.0.1"

    def get_mac_address(self) -> str:
        try:
            mac_int = uuid.getnode()
            return ':'.join(f'{(mac_int >> i) & 0xff:02x}' for i in range(40, -8, -8))
        except Exception:
            return "00:00:00:00:00:00"

    def on_system_boot(self) -> None:
        """매 부팅 시 0.1초 만에 실행되는 필수 안전/최적화 루틴"""
        logger.info("=== 제우스 부팅 시퀀스 가동 ===")
        # 0. 바탕화면 보호 (DesktopGuard)
        try:
            from client.desktop_guard import DesktopGuard
            guard = DesktopGuard()
            guard.restore_wallpaper()
            import threading
            threading.Thread(target=guard.monitor_wallpaper_loop, daemon=True).start()
        except Exception as e:
            logger.error(f"DesktopGuard 초기화 실패: {e}")

        # 1. 마스터 볼륨 100% 강제 고정 및 음소거 해제
        PowerPolicy.set_master_volume_100()

        # 2. 전원 안전 관리 (빠른시작 OFF, 절전 OFF, 전원버튼 봉쇄, '종료' 숨기고 '다시시작' 유지)
        PowerPolicy.apply_power_safety()
        PowerPolicy.hide_only_shutdown_keep_restart()
        PowerPolicy.setup_nic_wol()

        # 3. MS 방해화면 박멸 & 자동 업데이트 강제 재부팅 차단
        WindowsOptimizer.optimize_all_on_boot()

        # 4. 팟플레이어 및 넷플릭스 격리 프로필 예외 등록
        UWFController.apply_exclusions()

        # 5. 바탕화면 필수 아이콘 자동 복구 & 배경화면 영구 유지
        try:
            from client.desktop_guard import DesktopGuard
            DesktopGuard.restore_saved_wallpaper()
            DesktopGuard.sync_desktop_icons()
            DesktopGuard.start_wallpaper_watcher()
        except Exception as e:
            logger.warning(f"바탕화면/아이콘 관리자 구동 중 예외: {e}")

        logger.info("=== 제우스 부팅 시퀀스 완료 ===")

    def start_netflix_routine(self) -> None:
        """손님이 넷플릭스를 실행했을 때만 감지하여 자동 로그인 연동 (강제 재실행 안 함)"""
        def routine():
            # 1. 바탕화면에 넷플릭스 전용 아이콘 바로가기 자동 보장
            self.netflix_bot.ensure_desktop_shortcut()

            logger.info("넷플릭스 상시 감시 대기 중 (손님이 바로가기 실행 시 자동 로그인)...")
            was_running = False

            while True:
                try:
                    # 2. 크롬(넷플릭스)이 켜져 있는지 확인
                    is_running = self.netflix_bot.is_cdp_available()

                    if is_running:
                        if not was_running:
                            logger.info("🎬 [ZeusAgent] 손님이 넷플릭스를 실행함 -> 자동 로그인 검사 및 수행!")
                            was_running = True
                            self.netflix_bot.connect_cdp()

                        # 상태 점검 및 미로그인 시 자동 로그인 수행
                        st = self.netflix_bot.check_and_handle_login()
                        if st == "NEED_LOGIN":
                            self.cred_needed = True
                        elif st == NetflixStatus.LOGGED_IN:
                            self.otp_needed = False
                            self.cred_needed = False
                        elif st == NetflixStatus.OTP_WAITING:
                            if not self.otp_needed:
                                logger.info("⚡ [ZeusAgent] 넷플릭스 4자리 OTP 대기 상태 감지! 서버 알림 준비...")
                                self.otp_needed = True

                    else:
                        if was_running:
                            logger.info("🛑 [ZeusAgent] 손님이 넷플릭스를 종료함 -> 대기 모드로 전환 (강제 재실행 안 함)")
                            was_running = False
                            self.netflix_bot.current_status = NetflixStatus.CLOSED
                            self.otp_needed = False
                            self.otp_sent = False

                except Exception as e:
                    logger.warning(f"넷플릭스 감시 중 오류: {e}")

                time.sleep(2)

        threading.Thread(target=routine, daemon=True).start()

    async def run_heartbeat_loop(self, websocket):
        """3초 주기 하트비트 생존 신호 전송 및 OTP 상태 연동"""
        while True:
            try:
                uwf_st = UWFController.get_status()
                payload = {
                    "client_id": self.client_id,
                    "ip": self.local_ip,
                    "mac": self.mac_addr,
                    "uwf_status": uwf_st,
                    "netflix_status": self.netflix_bot.current_status,
                    "is_streaming": self.is_streaming_screen
                }
                pkt = make_packet(PacketType.HEARTBEAT, payload)
                await websocket.send(pkt)

                # 4자리 OTP 대기 상태이고 아직 서버에 전송하지 않았으면 즉각 발송
                if self.otp_needed and not self.otp_sent:
                    self.otp_sent = True
                    otp_pkt = make_packet(PacketType.OTP_REQUIRED, {
                        "client_id": self.client_id,
                        "ip": self.local_ip
                    })
                    await websocket.send(otp_pkt)
                    logger.info("📡 [ZeusAgent] 서버로 OTP_REQUIRED 즉시 전송 완료!")

                # 넷플릭스 1회용 계정 정보 필요 시 서버에 요청
                if self.cred_needed:
                    now = time.time()
                    if now - self.cred_requested > 10:
                        self.cred_requested = now
                        cred_pkt = make_packet(PacketType.CREDENTIAL_REQUEST, {
                            "client_id": self.client_id
                        })
                        await websocket.send(cred_pkt)
                        logger.info("📡 [ZeusAgent] 서버로 넷플릭스 계정 정보(CREDENTIAL_REQUEST) 요청 전송 완료!")

                await asyncio.sleep(HEARTBEAT_INTERVAL)
            except Exception as e:
                logger.warning(f"하트비트 전송 실패: {e}")
                break

    async def handle_server_commands(self, websocket):
        """관리 서버로부터 수신된 원격 제어 명령 실행"""
        async for msg in websocket:
            packet = parse_packet(msg)
            p_type = packet.get("type")
            data = packet.get("data", {})

            if p_type == PacketType.COMMAND:
                action = data.get("action")
                logger.info(f"서버 원격 명령 수신: {action}")

                if action == CommandType.REBOOT or action == CommandType.REBOOT_RECOVER:
                    asyncio.create_task(asyncio.to_thread(UWFController.reboot_restore))
                elif action == CommandType.REBOOT_MAINTENANCE:
                    asyncio.create_task(asyncio.to_thread(UWFController.reboot_to_maintenance))
                elif action == CommandType.SHUTDOWN:
                    asyncio.create_task(asyncio.to_thread(os.system, "shutdown /s /t 0 /f"))
                elif action == CommandType.RESTART_NETFLIX:
                    logger.info("관리 서버 원격 명령: 넷플릭스 강제 가동")
                    asyncio.create_task(asyncio.to_thread(self.netflix_bot.launch_chrome_with_cdp))
                elif action == CommandType.ENABLE_UWF:
                    logger.info("🛡️ [원격 명령] UWF 순간복구 보호 모드 활성화 시작...")
                    asyncio.create_task(asyncio.to_thread(UWFController.reboot_and_protect))
                elif action == CommandType.DISABLE_UWF:
                    logger.info("🔧 [원격 명령] UWF 보호 해제 (유지보수 모드) 시작...")
                    asyncio.create_task(asyncio.to_thread(UWFController.reboot_to_maintenance))
                elif action == CommandType.UPDATE_AGENT:
                    logger.info("🔄 [원격 명령] 관리자 강제 클라이언트 업데이트 실행...")
                    asyncio.create_task(asyncio.to_thread(self.check_and_apply_update, True))
                elif action == CommandType.START_SCREEN_STREAM:
                    logger.info("📡 [원격 제어] 화면 스트리밍 가동 명령 수신 -> 캡처 시작!")
                    self.is_streaming_screen = True
                elif action == CommandType.STOP_SCREEN_STREAM:
                    logger.info("💤 [원격 제어] 화면 스트리밍 절전 중지 명령 수신!")
                    self.is_streaming_screen = False

            elif p_type == PacketType.OTP_SUBMIT:
                # 네이버 메일에서 자동 추출되었거나 점주가 입력한 4자리 코드
                code = data.get("otp_code", "")
                logger.info(f"수신된 4자리 OTP [{code}] 화면 입력 시도...")
                asyncio.create_task(asyncio.to_thread(self.netflix_bot.input_otp_code, code))
                
            elif p_type == PacketType.CREDENTIAL_RESPONSE:
                email = data.get("email")
                password = data.get("password")
                if email and password:
                    logger.info(f"서버로부터 임시 넷플릭스 계정을 발급받았습니다: {email}")
                    self.netflix_bot.target_email = email
                    self.netflix_bot.target_password = password
                    self.cred_needed = False
                    self.cred_requested = 0

            elif p_type == PacketType.REMOTE_INPUT:
                # 모바일 터치 및 마우스/키보드 입력 제어
                evt = data.get("event")
                self.streamer.handle_remote_input(evt, data)

    async def run_screen_stream_loop(self, websocket):
        """화면 스트리밍 활성화 시 논블로킹 스레드 캡처로 12 FPS 스트리밍"""
        while True:
            if self.is_streaming_screen:
                try:
                    b64 = await asyncio.to_thread(self.streamer.capture_frame_base64)
                    if b64:
                        pkt = make_packet(PacketType.SCREEN_FRAME, {
                            "client_id": self.client_id,
                            "frame": b64
                        })
                        await websocket.send(pkt)
                except Exception as e:
                    logger.error(f"화면 프레임 전송 실패: {e}")
                    break
                await asyncio.sleep(0.08)
            else:
                await asyncio.sleep(0.2)

    def get_best_server_ip(self) -> str:
        """로컬 테스트 감지 또는 config.ini/기본 IP 자동 해석"""
        # 1. config.ini 파일이 있으면 최우선 적용
        config_paths = [
            r"C:\ZeusAgent\config.ini",
            os.path.join(ROOT_DIR, "deploy", "ClientDeploy", "core", "config.ini"),
            os.path.join(ROOT_DIR, "config.ini")
        ]
        for cp in config_paths:
            if os.path.exists(cp):
                try:
                    import configparser
                    cfg = configparser.ConfigParser()
                    cfg.read(cp, encoding="utf-8")
                    for sec in ["CLIENT", "Client", "SERVER", "Server"]:
                        if cfg.has_section(sec):
                            for opt in ["server_ip", "Server_IP", "IP", "server_host"]:
                                if cfg.has_option(sec, opt):
                                    val = cfg.get(sec, opt).strip()
                                    if val and val != "0.0.0.0":
                                        return val
                except Exception:
                    pass

        # 2. 로컬 머신에서 관제 서버가 켜져 있는지 확인 (로컬 개발 편의성)
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.5)
            if s.connect_ex(("127.0.0.1", self.server_port)) == 0:
                s.close()
                return "127.0.0.1"
            s.close()
        except Exception:
            pass

        return self.server_ip

    async def connect_and_serve(self):
        """관리 PC 서버 WebSocket 연결 유지 및 자동 재접속"""
        while True:
            target_ip = self.get_best_server_ip()
            uri = f"ws://{target_ip}:{self.server_port}/ws/client/{self.client_id}"
            try:
                logger.info(f"관리 서버 연결 시도: {uri}")
                async with websockets.connect(uri, open_timeout=3) as ws:
                    logger.info(f"관리 서버({target_ip}) 연결 성공!")
                    self.ws_conn = ws

                    # --- 연결 직후: 버퍼에 쌓인 로그 먼저 일괄 전송 ---
                    await self.ws_log_handler.flush_buffer(ws)

                    # --- 자율 진단: 지난번 크래시 로그가 있으면 서버로 보고 ---
                    crash_log_path = os.path.join(self.get_app_dir(), "crash.log")
                    if os.path.exists(crash_log_path):
                        try:
                            with open(crash_log_path, "r", encoding="utf-8") as f:
                                err_text = f.read()
                            pkt = make_packet(PacketType.ERROR_REPORT, {
                                "client_id": self.client_id,
                                "error": "Crash from previous run",
                                "traceback": err_text
                            })
                            await ws.send(pkt)
                            os.remove(crash_log_path) # 성공 시 삭제
                        except Exception:
                            pass
                            
                    await asyncio.gather(
                        self.run_heartbeat_loop(ws),
                        self.handle_server_commands(ws),
                        self.run_screen_stream_loop(ws)
                    )
            except Exception as e:
                logger.warning(f"서버({target_ip}) 연결 대기 중 (5초 후 재시도): {e}")
                self.ws_conn = None
                await asyncio.sleep(5)

    def get_app_dir(self) -> str:
        """PyInstaller 실행 파일 경로 또는 개발 루트 디렉터리 반환"""
        if getattr(sys, "frozen", False):
            return os.path.dirname(os.path.abspath(sys.executable))
        return ROOT_DIR

    def check_and_apply_update(self, force=False):
        """서버와 버전을 비교하고 새 버전이 있거나 force=True면 덮어쓰기 업데이트 수행"""
        import requests
        try:
            app_dir = self.get_app_dir()
            # 현재 버전 읽기
            version_path = os.path.join(app_dir, "version.txt")
            current_version = "0.0.0"
            if os.path.exists(version_path):
                try:
                    with open(version_path, "r", encoding="utf-8") as f:
                        current_version = f.read().strip().replace('"', '').replace("'", "").replace('\ufeff', '').strip()
                except Exception:
                    pass

            # 서버 최신 버전 조회
            server_url = f"http://{self.server_ip}:{self.server_port}"
            res = requests.get(f"{server_url}/api/version", timeout=3)
            if res.status_code != 200:
                return
            latest_version = res.text.strip().replace('"', '').replace("'", "").replace('\ufeff', '').strip()

            if force or (latest_version and latest_version != current_version):
                reason = "강제 업데이트 명령" if force else f"현재: {current_version} -> 최신: {latest_version}"
                logger.info(f"🔄 클라이언트 업데이트 진행! ({reason})")
                
                # 새 실행 파일 다운로드 (안정적인 30초 타임아웃)
                exe_res = requests.get(f"{server_url}/api/download/update", stream=True, timeout=30)
                if exe_res.status_code == 200:
                    new_exe_path = os.path.join(app_dir, "ZeusAgent_new.exe")
                    with open(new_exe_path, "wb") as f:
                        for chunk in exe_res.iter_content(chunk_size=65536):
                            if chunk:
                                f.write(chunk)
                    
                    # 파일 다운로드 완전성 검증 (최소 5MB 이상)
                    if not os.path.exists(new_exe_path) or os.path.getsize(new_exe_path) < 5000000:
                        logger.error("업데이트 파일 다운로드 불완전 (크기 미달), 업데이트 중단")
                        return

                    # 새 버전 파일 쓰기
                    new_ver_path = os.path.join(app_dir, "version_new.txt")
                    with open(new_ver_path, "w", encoding="utf-8") as f:
                        f.write(latest_version)

                    # 업데이트 배치 파일 생성 (무인 무중단 재시도 루프)
                    bat_path = os.path.join(app_dir, "update.bat")
                    bat_content = f"""@echo off
cd /d "%~dp0"
ping 127.0.0.1 -n 3 >nul
taskkill /F /IM ZeusAgent.exe >nul 2>&1
ping 127.0.0.1 -n 2 >nul

set RETRY=0
:RETRY_MOVE
if not exist "ZeusAgent_new.exe" goto LAUNCH
move /y "ZeusAgent_new.exe" "ZeusAgent.exe" >nul 2>&1
if errorlevel 1 (
    set /a RETRY+=1
    if %RETRY% lss 15 (
        ping 127.0.0.1 -n 2 >nul
        goto RETRY_MOVE
    )
)

:MOVE_VER
if exist "version_new.txt" move /y "version_new.txt" "version.txt" >nul 2>&1

:LAUNCH
ping 127.0.0.1 -n 2 >nul
start "" "%~dp0ZeusAgent.exe"
del "%~f0"
"""
                    with open(bat_path, "w", encoding="cp949") as f:
                        f.write(bat_content)

                    # 배치 파일 실행 후 현재 프로세스 완전 종료
                    import subprocess
                    subprocess.Popen(bat_path, shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
                    os._exit(0)
        except Exception as e:
            logger.error(f"업데이트 확인 중 오류: {e}")

    def start(self):
        """에이전트 전체 구동"""
        # 0. 자동 업데이트 체크
        try:
            self.check_and_apply_update()
        except Exception as e:
            logger.warning(f"업데이트 체크 중 예외: {e}")

        # 1. 윈도우 부팅 안전 정책 실행
        try:
            self.on_system_boot()
        except Exception as e:
            logger.warning(f"부팅 시퀀스 적용 중 예외: {e}")

        # 2. 넷플릭스 실행
        try:
            self.start_netflix_routine()
        except Exception as e:
            logger.warning(f"넷플릭스 루틴 구동 중 예외: {e}")

        # 3. 트레이 아이콘 백그라운드 쓰레드 실행
        try:
            tray = ClientTrayUI(on_restart_netflix=self.start_netflix_routine)
            threading.Thread(target=tray.run_tray, daemon=True).start()
        except Exception as e:
            logger.warning(f"트레이 아이콘 구동 중 예외: {e}")

        # 4. 서버 통신 비동기 루프 실행
        asyncio.run(self.connect_and_serve())

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--launch-netflix":
        from client.netflix_bot import NetflixBot
        bot = NetflixBot()
        bot.launch_chrome_with_cdp()
        sys.exit(0)

    agent = ZeusClientAgent()
    agent.start()
