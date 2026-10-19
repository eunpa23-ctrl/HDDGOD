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
import subprocess
import asyncio
import websockets
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from common.config import CLIENT_SERVER_IP, CLIENT_SERVER_PORT, HEARTBEAT_INTERVAL
from common.protocol import (
    PacketType, CommandType, NetflixStatus, make_packet, parse_packet
)
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

        # 피카 잠금/해제 동시성 및 중복 방지 제어
        self.is_pica_unlocking = False
        self.last_pica_unlock_time = 0.0
        self.pica_unlock_lock = threading.Lock()
        self.was_pica_locked_on_stream_start = False
        self.pica_exe_path = r"C:\Program Files (x86)\PicaClient\pmclient.exe"
        try:
            pfile = os.path.join(self.get_app_dir(), "pica_path.txt")
            if os.path.exists(pfile):
                with open(pfile, "r", encoding="utf-8") as pf:
                    saved = pf.read().strip()
                    if saved:
                        self.pica_exe_path = saved
        except Exception:
            pass

    def get_pica_admin_password(self) -> str:
        """손님 PC 피카 관리자 잠금해제 비밀번호 (점주 지정: 1234)"""
        return "1234"

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

        logger.info("=== 제우스 부팅 시퀀스 완료 ===")

    def check_netflix_window_active(self) -> bool:
        """Windows API를 통해 화면에 넷플릭스 창이 실제로 떠 있는지 초고속 검사 (0.001초)"""
        try:
            import ctypes
            found = False
            def enum_cb(hwnd, lparam):
                nonlocal found
                if ctypes.windll.user32.IsWindowVisible(hwnd):
                    length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
                    if length > 0:
                        buf = ctypes.create_unicode_buffer(length + 1)
                        ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
                        t = buf.value.lower()
                        if "netflix" in t or "넷플릭스" in t:
                            found = True
                            return False
                return True
            CB = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
            ctypes.windll.user32.EnumWindows(CB(enum_cb), 0)
            return found
        except Exception:
            return False

    def start_netflix_routine(self) -> None:
        """손님이 넷플릭스를 실행했을 때만 감지하여 자동 로그인 연동 (강제 재실행 안 함)"""
        def routine():
            # 1. 바탕화면에 넷플릭스 전용 아이콘 바로가기 자동 보장
            self.netflix_bot.ensure_desktop_shortcut()

            logger.info("넷플릭스 상시 감시 대기 중 (손님이 바로가기 실행 시 자동 로그인)...")
            was_running = False

            while True:
                try:
                    # 1. CDP 포트(9222) 활성화 확인
                    is_cdp = self.netflix_bot.is_cdp_available()

                    # 2. 윈도우 창 제목 중 Netflix 존재 여부 확인 (일반 브라우저/앱 실행 폴백)
                    is_win_active = self.check_netflix_window_active()

                    if is_cdp:
                        if not was_running:
                            logger.info("🎬 [ZeusAgent] 손님이 넷플릭스를 실행함 (CDP) -> 자동 로그인 검사 및 수행!")
                            was_running = True
                            self.netflix_bot.connect_cdp()

                        # 상태 점검 및 미로그인 시 자동 로그인 수행
                        st = self.netflix_bot.check_and_handle_login()
                        if st == "NEED_LOGIN":
                            self.cred_needed = True
                        elif st == NetflixStatus.LOGGED_IN:
                            self.otp_needed = False
                            self.cred_needed = False
                            time.sleep(5)
                            continue
                        elif st == NetflixStatus.OTP_WAITING:
                            if not self.otp_needed:
                                logger.info("⚡ [ZeusAgent] 넷플릭스 4자리 OTP 대기 상태 감지! 서버 알림 준비...")
                                self.otp_needed = True
                        elif st == NetflixStatus.CLOSED:
                            was_running = False
                            self.otp_needed = False
                            self.cred_needed = False

                    elif is_win_active:
                        # CDP 포트가 안 열려 있더라도 창에 넷플릭스가 켜져 있으면 '시청중'으로 실시간 반영!
                        if not was_running:
                            logger.info("🎬 [ZeusAgent] 넷플릭스 창 활성화 감지 (일반 브라우저/창) -> 시청중 상태 전환")
                            was_running = True
                        self.netflix_bot.current_status = NetflixStatus.LOGGED_IN
                        time.sleep(3)
                        continue

                    else:
                        if was_running:
                            logger.info("🛑 [ZeusAgent] 손님이 넷플릭스를 종료함 -> 대기 모드로 전환")
                            was_running = False
                            self.otp_needed = False
                            self.otp_sent = False
                        self.netflix_bot.current_status = NetflixStatus.CLOSED

                except Exception as e:
                    logger.warning(f"넷플릭스 감시 중 오류: {e}")

                time.sleep(2)

        threading.Thread(target=routine, daemon=True).start()

    def get_local_version(self) -> str:
        """현재 에이전트 버전 조회"""
        try:
            ver_path = os.path.join(self.get_app_dir(), "version.txt")
            if os.path.exists(ver_path):
                with open(ver_path, "r", encoding="utf-8") as f:
                    return f.read().strip()
        except Exception:
            pass
        return "알 수 없음"

    async def run_heartbeat_loop(self, websocket):
        """3초 주기 하트비트 생존 신호 전송 및 OTP 상태 연동"""
        while True:
            try:
                # 피카 잠금 상태 감지 (서버 PC는 항상 NONE)
                pica_st = "NONE"
                if not self.is_server_node():
                    try:
                        pica_st = self.get_pica_state()
                    except Exception:
                        pica_st = "UNKNOWN"

                cpu_usage = 0.0
                ram_percent = 0.0
                ram_used_gb = 0.0
                ram_total_gb = 0.0
                try:
                    import psutil
                    cpu_usage = round(psutil.cpu_percent(interval=None), 1)
                    vm = psutil.virtual_memory()
                    ram_percent = round(vm.percent, 1)
                    ram_used_gb = round(vm.used / (1024**3), 1)
                    ram_total_gb = round(vm.total / (1024**3), 1)
                except Exception:
                    pass

                payload = {
                    "client_id": self.client_id,
                    "ip": self.local_ip,
                    "mac": self.mac_addr,
                    "uwf_status": "DISABLED",
                    "netflix_status": self.netflix_bot.current_status,
                    "pica_status": pica_st,
                    "is_streaming": self.is_streaming_screen,
                    "version": self.get_local_version(),
                    "cpu": cpu_usage,
                    "ram": ram_percent,
                    "ram_used_gb": ram_used_gb,
                    "ram_total_gb": ram_total_gb
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

                if action in (CommandType.REBOOT, CommandType.REBOOT_RECOVER, CommandType.REBOOT_MAINTENANCE):
                    logger.info("🔄 [원격 명령] PC 즉시 재부팅 실행...")
                    asyncio.create_task(asyncio.to_thread(os.system, "shutdown /r /t 0 /f"))
                elif action == CommandType.SHUTDOWN:
                    asyncio.create_task(asyncio.to_thread(os.system, "shutdown /s /t 0 /f"))
                elif action == CommandType.RESTART_NETFLIX:
                    logger.info("관리 서버 원격 명령: 넷플릭스 강제 가동")
                    asyncio.create_task(asyncio.to_thread(self.netflix_bot.launch_chrome_with_cdp))
                elif action == CommandType.UPDATE_AGENT:
                    logger.info("🔄 [원격 명령] 관리자 강제 클라이언트 업데이트 실행...")
                    asyncio.create_task(asyncio.to_thread(self.check_and_apply_update, True))
                elif action == CommandType.UNINSTALL_AGENT:
                    logger.info("🗑️ [원격 명령] 제우스 클라이언트 원격 완전 삭제(언인스톨) 실행...")
                    asyncio.create_task(asyncio.to_thread(self.uninstall_agent))
                elif action in (CommandType.OPTIMIZE_MEMORY, "OPTIMIZE_MEMORY"):
                    logger.info("⚡ [원격 명령] 유휴 캐시 메모리 최적화(EmptyWorkingSet) 실행...")
                    asyncio.create_task(asyncio.to_thread(self.optimize_local_memory))
                elif action == CommandType.START_SCREEN_STREAM:
                    logger.info("📡 [원격 제어] 화면 스트리밍 가동 명령 수신 -> 캡처 시작!")
                    self.is_streaming_screen = True
                    # ⚠️ 손님 PC에서 피카 관리자 로그인(Ctrl+Alt+Shift+X) 자동 실행 일체 금지!
                    # 카운터 서버에서 직접 우클릭 제어하므로 손님 PC는 화면 스트리밍만 안전하게 수행합니다.
                elif action == CommandType.STOP_SCREEN_STREAM:
                    logger.info("💤 [원격 제어] 화면 스트리밍 절전 중지 명령 수신!")
                    self.is_streaming_screen = False
                elif action == CommandType.UNLOCK_PICA:
                    # 카운터 서버 직접 제어로 일원화 (손님 PC 매크로 실행 안 함)
                    logger.info("ℹ️ [원격 명령] 피카 관리자 로그인은 카운터 서버에서 직접 제어되므로 손님 PC 매크로는 건너뜁니다.")
                elif action == CommandType.LOCK_PICA:
                    # 카운터 서버 직접 제어로 일원화 (손님 PC 매크로 실행 안 함)
                    logger.info("ℹ️ [원격 명령] 피카 잠금 복구는 카운터 서버에서 직접 제어되므로 손님 PC 매크로는 건너뜁니다.")

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
        """화면 스트리밍 활성화 시 8 FPS 경량 스트리밍 (하트비트 대역폭 보호)"""
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
                    logger.warning(f"화면 프레임 전송 일시 지연: {e}")
                    await asyncio.sleep(0.5)
                await asyncio.sleep(0.12)
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
        self.loop = asyncio.get_running_loop()
        while True:
            target_ip = self.get_best_server_ip()
            uri = f"ws://{target_ip}:{self.server_port}/ws/client/{self.client_id}"
            try:
                logger.info(f"관리 서버 연결 시도: {uri}")
                async with websockets.connect(
                    uri,
                    open_timeout=5,
                    ping_interval=20,
                    ping_timeout=20,
                    max_size=10 * 1024 * 1024
                ) as ws:
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
        """서버와 버전을 비교하고 새 버전이 있거나 force=True면 덮어쓰기 업데이트 수행 (GUI 포함)"""
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

            # 서버 최신 버전 조회 (부팅 초기 네트워크 안정화 대기: 최대 3회 재시도)
            server_url = f"http://{self.server_ip}:{self.server_port}"
            res = None
            for attempt in range(3):
                try:
                    res = requests.get(f"{server_url}/api/version", timeout=4)
                    if res.status_code == 200:
                        break
                except Exception:
                    pass
                import time
                time.sleep(2)

            if not res or res.status_code != 200:
                return
            latest_version = res.text.strip().replace('"', '').replace("'", "").replace('\ufeff', '').strip()

            if force or (latest_version and latest_version != current_version):
                reason = "강제 업데이트 명령" if force else f"현재: {current_version} -> 최신: {latest_version}"
                logger.info(f"🔄 클라이언트 업데이트 진행! ({reason})")
                
                # 원격 강제 명령(force=True)일 경우 백그라운드 스레드 크래시를 방지하기 위해 GUI 생성 건너뜀
                use_gui = not force
                root = None
                progress = None
                pct_lbl = None
                lbl = None
                
                if use_gui:
                    try:
                        import tkinter as tk
                        from tkinter import ttk
                        root = tk.Tk()
                        root.title("제우스 에이전트 패치 업데이트")
                        root.geometry("450x180")
                        root.attributes("-topmost", True)
                        root.eval('tk::PlaceWindow . center')
                        
                        lbl = tk.Label(root, text=f"제우스 에이전트 업데이트 시작...\n버전 {current_version} -> {latest_version}\n다운로드 중입니다. 잠시만 기다려주세요.", font=("맑은 고딕", 11))
                        lbl.pack(pady=15)
                        
                        progress = ttk.Progressbar(root, orient="horizontal", length=350, mode="determinate")
                        progress.pack(pady=10)
                        
                        pct_lbl = tk.Label(root, text="0%", font=("맑은 고딕", 10, "bold"))
                        pct_lbl.pack()
                        
                        root.update()
                    except Exception:
                        use_gui = False
                        root = None

                # 새 실행 파일 다운로드 (안정적인 30초 타임아웃)
                exe_res = requests.get(f"{server_url}/api/download/update", stream=True, timeout=30)
                if exe_res.status_code == 200:
                    total_length = exe_res.headers.get('content-length')
                    new_exe_path = os.path.join(app_dir, "ZeusAgent_new.exe")
                    
                    with open(new_exe_path, "wb") as f:
                        if total_length is None:
                            if use_gui and progress:
                                progress.config(mode="indeterminate")
                                progress.start()
                            for chunk in exe_res.iter_content(chunk_size=65536):
                                if chunk:
                                    f.write(chunk)
                                    if use_gui and root:
                                        root.update()
                        else:
                            total_length = int(total_length)
                            downloaded = 0
                            for chunk in exe_res.iter_content(chunk_size=65536):
                                if chunk:
                                    f.write(chunk)
                                    downloaded += len(chunk)
                                    if use_gui and progress and root:
                                        pct = int((downloaded / total_length) * 100)
                                        progress['value'] = pct
                                        pct_lbl.config(text=f"{pct}%")
                                        root.update()
                    
                    # 파일 다운로드 완전성 검증 (최소 5MB 이상)
                    if not os.path.exists(new_exe_path) or os.path.getsize(new_exe_path) < 5000000:
                        logger.error("업데이트 파일 다운로드 불완전 (크기 미달), 업데이트 중단")
                        if use_gui and root:
                            root.destroy()
                        return

                    if use_gui and root:
                        lbl.config(text="다운로드 완료! 에이전트를 재시작합니다...")
                        progress['value'] = 100
                        pct_lbl.config(text="100%")
                        root.update()
                        import time
                        time.sleep(1)
                        root.destroy()

                    # 업데이트 플래그 생성 (업데이트 직후 UI 표시용)
                    with open(os.path.join(app_dir, "just_updated.flag"), "w", encoding="utf-8") as f:
                        f.write(latest_version)

                    # 새 버전 파일 쓰기
                    new_ver_path = os.path.join(app_dir, "version_new.txt")
                    with open(new_ver_path, "w", encoding="utf-8") as f:
                        f.write(latest_version)

                    # 1. 업데이트 배치 파일 생성 (견고한 무인 교체 루프)
                    bat_path = os.path.join(app_dir, "update.bat")
                    bat_content = f"""@echo off
setlocal enabledelayedexpansion

:: ========================================================
:: [0] 관리자 권한 자동 승격 (SYSTEM 실행 시 바로 통과)
:: ========================================================
net session >nul 2>&1
if %errorlevel% neq 0 (
    powershell -NoProfile -Command "Start-Process cmd.exe -ArgumentList '/c', '\"%~f0\"' -Verb RunAs -WindowStyle Hidden"
    exit /b 0
)

:: ========================================================
:: [1] PyInstaller 임시 환경변수 완전 초기화
:: ========================================================
set _MEIPASS2=
set _MEIPASS=
set _PYI_APPLICATION_HOME_DIR=
set PYINSTALLER_STRICT_UNLOAD_MODE=

:: ========================================================
:: [2] 작업 디렉터리를 에이전트 폴더로 명시적 이동
:: ========================================================
cd /d "%~dp0"

:: 3초 대기 후 기존 프로세스 종료
ping 127.0.0.1 -n 4 >nul
taskkill /F /IM ZeusAgent.exe >nul 2>&1
ping 127.0.0.1 -n 2 >nul

:: 잔여 temp 임시 폴더 삭제
if exist "%~dp0temp" rmdir /s /q "%~dp0temp" >nul 2>&1

:: 새 실행 파일 교체 시도 (최대 30회)
set RETRY=0
:RETRY_MOVE
if not exist "%~dp0ZeusAgent_new.exe" goto MOVE_VER
del /f /q "%~dp0ZeusAgent.exe" >nul 2>&1
move /y "%~dp0ZeusAgent_new.exe" "%~dp0ZeusAgent.exe" >nul 2>&1
if errorlevel 1 (
    set /a RETRY+=1
    if !RETRY! lss 30 (
        ping 127.0.0.1 -n 2 >nul
        goto RETRY_MOVE
    )
    echo [update.bat] ERROR: ZeusAgent.exe 교체 실패 >> "%~dp0bat_debug.log"
    goto LAUNCH
)

:MOVE_VER
if exist "%~dp0version_new.txt" move /y "%~dp0version_new.txt" "%~dp0version.txt" >nul 2>&1

:LAUNCH
ping 127.0.0.1 -n 2 >nul
start "" /D "%~dp0" "%~dp0ZeusAgent.exe"
exit /b 0
"""
                    with open(bat_path, "w", encoding="cp949") as f:
                        f.write(bat_content)
                        f.flush()
                        os.fsync(f.fileno())

                    # 트레이 아이콘 정지
                    if hasattr(self, "tray") and self.tray and getattr(self.tray, "icon", None):
                        try:
                            self.tray.icon.stop()
                        except Exception:
                            pass

                    # 2. 파이썬 환경변수 멸균 및 완전 독립 분리 프로세스로 실행
                    clean_env = os.environ.copy()
                    keys_to_remove = [k for k in clean_env.keys() if k.startswith("_PYI") or k.startswith("_MEI") or k.startswith("PYINSTALLER")]
                    for k in keys_to_remove:
                        clean_env.pop(k, None)

                    # [Windows 완벽 독립 백그라운드 구동] 
                    # CREATE_NO_WINDOW (0x08000000) | CREATE_NEW_PROCESS_GROUP (0x00000200) 플래그로 
                    # 부모 프로세스(ZeusAgent.exe)가 즉시 종료되어도 update.bat가 백그라운드에서 끝까지 완벽 실행됨
                    try:
                        SPAWN_FLAGS = 0x08000000 | 0x00000200
                        subprocess.Popen(
                            ["cmd.exe", "/c", bat_path],
                            creationflags=SPAWN_FLAGS,
                            close_fds=True,
                            cwd=app_dir,
                            env=clean_env
                        )
                        logger.info("🚀 update.bat 백그라운드 독립 프로세스 실행 성공!")
                    except Exception as ex:
                        logger.error(f"update.bat 실행 실패: {ex}")

                    import time
                    time.sleep(0.5)
                    os._exit(0)
        except Exception as e:
            logger.error(f"업데이트 확인 중 오류: {e}")

    def optimize_local_memory(self):
        """윈도우 프로세스 유휴 캐시 메모리 회수 (EmptyWorkingSet)"""
        try:
            import gc
            import ctypes
            import psutil
            gc.collect()
            before_vm = psutil.virtual_memory()

            kernel32 = ctypes.windll.kernel32
            psapi = ctypes.windll.psapi
            trimmed_count = 0

            for proc in psutil.process_iter(['pid']):
                try:
                    pid = proc.info['pid']
                    if pid <= 4:
                        continue
                    h_process = kernel32.OpenProcess(0x001F0FFF, False, pid)
                    if h_process:
                        if psapi.EmptyWorkingSet(h_process):
                            trimmed_count += 1
                        kernel32.CloseHandle(h_process)
                except Exception:
                    pass

            after_vm = psutil.virtual_memory()
            freed_mb = round((before_vm.used - after_vm.used) / (1024 * 1024), 1)
            logger.info(f"⚡ [메모리 최적화 완료] {trimmed_count}개 프로세스 정리, {freed_mb}MB 메모리 즉시 확보 ({before_vm.percent}% -> {after_vm.percent}%)")
            return {
                "status": "ok",
                "trimmed_count": trimmed_count,
                "freed_mb": freed_mb,
                "current_ram_percent": after_vm.percent,
                "available_gb": round(after_vm.available / (1024**3), 2)
            }
        except Exception as e:
            logger.error(f"메모리 최적화 실패: {e}")
            return {"status": "error", "message": str(e)}

    def uninstall_agent(self) -> None:
        """클라이언트 원격 완전 삭제 및 시스템 원상 복구"""
        try:
            import tempfile
            logger.info("🗑️ [언인스톨] 완전 삭제 스크립트 작성 및 독립 실행 준비...")
            bat_content = r"""@echo off
setlocal enabledelayedexpansion
:: [1] 프로세스 종료 대기
ping 127.0.0.1 -n 3 >nul
taskkill /F /IM ZeusAgent.exe >nul 2>&1
ping 127.0.0.1 -n 2 >nul

:: [2] 시작프로그램 및 작업 스케줄러 등록 해제
schtasks /delete /tn "ZeusAgent" /f >nul 2>&1
schtasks /delete /tn "ZeusClientAgent" /f >nul 2>&1
reg delete "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Run" /v "ZeusAgent" /f >nul 2>&1
reg delete "HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\Run" /v "ZeusAgent" /f >nul 2>&1

:: [3] 방화벽 규칙 및 윈도우 디펜더 예외 해제
netsh advfirewall firewall delete rule name="ZeusAgent" >nul 2>&1
netsh advfirewall firewall delete rule name="ZeusAgent_Out" >nul 2>&1
powershell -NoProfile -Command "$ErrorActionPreference='SilentlyContinue'; Remove-MpPreference -ExclusionPath 'C:\ZeusAgent'; Remove-MpPreference -ExclusionProcess 'ZeusAgent.exe'" >nul 2>&1

:: [4] 바탕화면 바로가기 삭제
if exist "%PUBLIC%\Desktop\넷플릭스.lnk" (
    attrib -r -h -s "%PUBLIC%\Desktop\넷플릭스.lnk" >nul 2>&1
    del /f /q "%PUBLIC%\Desktop\넷플릭스.lnk" >nul 2>&1
)
if exist "%USERPROFILE%\Desktop\넷플릭스.lnk" (
    attrib -r -h -s "%USERPROFILE%\Desktop\넷플릭스.lnk" >nul 2>&1
    del /f /q "%USERPROFILE%\Desktop\넷플릭스.lnk" >nul 2>&1
)
if exist "%ALLUSERSPROFILE%\Desktop\넷플릭스.lnk" (
    attrib -r -h -s "%ALLUSERSPROFILE%\Desktop\넷플릭스.lnk" >nul 2>&1
    del /f /q "%ALLUSERSPROFILE%\Desktop\넷플릭스.lnk" >nul 2>&1
)

:: [5] 설치 폴더(C:\ZeusAgent) 완전 삭제
cd /d "%TEMP%"
set RETRY=0
:RETRY_DEL
if not exist "C:\ZeusAgent" goto DONE
rd /s /q "C:\ZeusAgent" >nul 2>&1
if exist "C:\ZeusAgent" (
    set /a RETRY+=1
    if !RETRY! lss 10 (
        ping 127.0.0.1 -n 2 >nul
        goto RETRY_DEL
    )
)
:DONE
del "%~f0" >nul 2>&1
exit /b 0
"""
            temp_dir = tempfile.gettempdir()
            bat_path = os.path.join(temp_dir, "zeus_uninstall.bat")
            with open(bat_path, "w", encoding="cp949") as f:
                f.write(bat_content.replace("\r\n", "\n").replace("\n", "\r\n"))
                f.flush()
                os.fsync(f.fileno())

            # 트레이 아이콘 종료
            if hasattr(self, "tray") and self.tray and getattr(self.tray, "icon", None):
                try:
                    self.tray.icon.stop()
                except Exception:
                    pass

            # 무창 분리 프로세스로 실행
            DETACHED_FLAGS = 0x08000000 | 0x00000200
            subprocess.Popen(
                ["cmd.exe", "/c", bat_path],
                creationflags=DETACHED_FLAGS,
                close_fds=True
            )
            logger.info("🗑️ [언인스톨] 백그라운드 삭제 프로세스 기동 완료. 에이전트 종료.")
            import time
            time.sleep(0.5)
            os._exit(0)
        except Exception as e:
            logger.error(f"원격 언인스톨 실행 실패: {e}")

    def is_server_node(self) -> bool:
        """현재 PC가 손님용이 아닌 서버(메인 서버/관리 서버 등)인지 판별"""
        try:
            local_ip = self.get_local_ip()
            if local_ip in ["192.168.0.2", "192.168.0.100"]:
                return True
            cid = (self.client_id or "").upper()
            if cid in ["PC-09", "SERVER", "SERVER_MAIN", "HOST"]:
                return True
            if self.config.getboolean("SERVER", "is_server", fallback=False):
                return True
        except Exception:
            pass
        return False

    def get_pica_state(self) -> str:
        """피카 관리프로그램 화면 잠금/사용 상태 3단계 정밀 판별
        - 'ADMIN': 점주 관리자 로그인 상태 ('관리자로그아웃' 버튼 감지)
        - 'USING': 손님 실제 이용 중 ('후불로그아웃', '선불로그아웃', '남은시간', '사용시간' 감지)
        - 'LOCKED': 빈자리 화면보호기 잠김 상태 (대기)
        """
        self._pica_debug_count = getattr(self, "_pica_debug_count", 0) + 1
        do_log = (self._pica_debug_count % 5 == 1)

        if self.is_server_node():
            if do_log:
                logger.warning(f"🚨 [피카감지디버그] is_server_node=True! ip={self.local_ip}, cid={self.client_id}")
            return "NONE"
        try:
            import ctypes
            from ctypes import wintypes
            user32 = ctypes.windll.user32

            # WinSta0\Default 대화형 데스크톱 핸들 접근 보장
            try:
                hdesk = user32.OpenDesktopW("Default", 0, False, 0x01FF)
                if hdesk:
                    user32.SetThreadDesktop(hdesk)
            except Exception:
                pass

            detected_mode = "LOCKED"

            WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

            sw = user32.GetSystemMetrics(0)
            sh = user32.GetSystemMetrics(1)
            if sw <= 0 or sh <= 0:
                sw, sh = 1920, 1080

            def is_rect_visible_on_screen(cr):
                # 너비/높이가 0 이하이거나, 화면 좌표계 밖(음수 등)에 숨겨진 오프스크린 컨트롤 제외
                w = cr.right - cr.left
                h = cr.bottom - cr.top
                if w <= 0 or h <= 0:
                    return False
                if cr.right <= 0 or cr.bottom <= 0:
                    return False
                if cr.left >= sw or cr.top >= sh:
                    return False
                return True

            def check_text(hwnd, txt: str):
                nonlocal detected_mode
                t = txt.strip().replace(' ', '')
                if not t:
                    return
                # 1. 관리자 모드 우선 감지 (관리자로그아웃 버튼 창이 화면에 보임)
                for k in ['관리자로그아웃', '관리자로그아웃버튼']:
                    if k in t:
                        cr = wintypes.RECT()
                        user32.GetWindowRect(hwnd, ctypes.byref(cr))
                        if is_rect_visible_on_screen(cr):
                            logger.info(f"⚡ [피카 관리자 감지] 활성 화면상 포착: k={k}, RECT=({cr.left},{cr.top},{cr.right},{cr.bottom})")
                            detected_mode = "ADMIN"
                            return
                # 2. 손님 이용 중 감지 (후불/선불 로그아웃, 잔여/사용시간 창이 화면에 보임)
                for k in ['후불로그아웃', '선불로그아웃', '남은시간:', '잔여시간:', '사용시간:']:
                    if k in t:
                        cr = wintypes.RECT()
                        user32.GetWindowRect(hwnd, ctypes.byref(cr))
                        if is_rect_visible_on_screen(cr):
                            if detected_mode != "ADMIN":
                                logger.info(f"👤 [피카 손님 감지] 활성 화면상 포착: k={k}, RECT=({cr.left},{cr.top},{cr.right},{cr.bottom})")
                                detected_mode = "USING"
                            return

            def enum_proc(h, lp):
                if user32.IsWindowVisible(h):
                    c_txt = ctypes.create_unicode_buffer(512)
                    user32.GetWindowTextW(h, c_txt, 512)
                    check_text(h, c_txt.value)

                    def child_proc(ch, lp2):
                        if user32.IsWindowVisible(ch):
                            c_txt2 = ctypes.create_unicode_buffer(512)
                            user32.GetWindowTextW(ch, c_txt2, 512)
                            check_text(ch, c_txt2.value)
                        return True
                    user32.EnumChildWindows(h, WNDENUMPROC(child_proc), 0)
                return True

            user32.EnumWindows(WNDENUMPROC(enum_proc), 0)

            if do_log:
                logger.warning(f"🔍 [피카감지상태] state={detected_mode}")

            return detected_mode
        except Exception as e:
            logger.error(f"피카 잠금 판별 오류: {e}")
            return "LOCKED"

    def is_pica_locked(self) -> bool:
        """기존 화면 잠금 여부 호환 (대기 상태이면 True)"""
        return self.get_pica_state() == "LOCKED"

    def unlock_pica_screen(self):
        """PC 관리 에이전트(피카/PICA) 화면 잠금 해제 -> 관리자 로그인 수행 (피카 유지 및 카운터 관리자 표기)"""
        with self.pica_unlock_lock:
            now = time.time()
            if self.is_pica_unlocking or (now - self.last_pica_unlock_time < 3.0):
                logger.warning("⚠️ [피카 해제] 이미 잠금 해제가 진행 중이거나 최근 3초 내 실행됨 -> 중복 실행 방지 건너뜀")
                return
            self.is_pica_unlocking = True
            self.last_pica_unlock_time = now

        try:
            import ctypes
            from ctypes import wintypes
            import psutil
            from client.screen_streamer import ensure_default_desktop

            ensure_default_desktop()
            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32

            # Per-Monitor DPI Awareness V2 활성화
            try:
                user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
            except Exception:
                try:
                    ctypes.windll.shcore.SetProcessDpiAwareness(2)
                except Exception:
                    try:
                        user32.SetProcessDPIAware()
                    except Exception:
                        pass

            BM_CLICK = 0x00F5
            BN_CLICKED = 0
            WM_COMMAND = 0x0111
            EM_SETSEL = 0x00B1
            WM_CLEAR = 0x0303
            VK_RETURN = 0x0D
            VK_BACK = 0x08
            VK_CONTROL = 0x11
            VK_A = 0x41

            WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

            def click_control(hwnd, parent, rect=None):
                user32.SendMessageW(hwnd, BM_CLICK, 0, 0)
                user32.PostMessageW(hwnd, BM_CLICK, 0, 0)
                if parent:
                    cid = user32.GetDlgCtrlID(hwnd)
                    wparam = ((BN_CLICKED & 0xFFFF) << 16) | (cid & 0xFFFF)
                    user32.PostMessageW(parent, WM_COMMAND, wparam, hwnd)
                if rect:
                    cx = (rect[0] + rect[2]) // 2
                    cy = (rect[1] + rect[3]) // 2
                    if cx > 0 and cy > 0:
                        user32.SetCursorPos(cx, cy)
                        time.sleep(0.04)
                        user32.mouse_event(2, 0, 0, 0, 0)
                        time.sleep(0.04)
                        user32.mouse_event(4, 0, 0, 0, 0)

            target_pw = self.get_pica_admin_password()
            logger.info(f"🔑 [피카 관리자 로그인] 비밀번호: '{target_pw}' (카운터 '관리자' 동기화)")

            pica_pids = set()
            for p in psutil.process_iter(['pid', 'name']):
                try:
                    if any(k in p.info['name'].lower() for k in ['pmclient', 'pmlc', 'pica']):
                        pica_pids.add(p.info['pid'])
                except Exception:
                    pass

            def dump_all_pica():
                top_hwnds = []
                def enum_top(h, lp):
                    pid = wintypes.DWORD()
                    user32.GetWindowThreadProcessId(h, ctypes.byref(pid))
                    if pid.value in pica_pids and user32.IsWindowVisible(h) and not user32.IsIconic(h):
                        top_hwnds.append((h, pid.value))
                    return True
                user32.EnumWindows(WNDENUMPROC(enum_top), 0)

                all_ctrls = []
                for th, pid_val in top_hwnds:
                    t_top = ctypes.create_unicode_buffer(256)
                    user32.GetWindowTextW(th, t_top, 256)
                    c_top = ctypes.create_unicode_buffer(256)
                    user32.GetClassNameW(th, c_top, 256)
                    r_top = wintypes.RECT()
                    user32.GetWindowRect(th, ctypes.byref(r_top))
                    all_ctrls.append((th, c_top.value, t_top.value.strip(), 0, 0, (r_top.left, r_top.top, r_top.right, r_top.bottom), True, True))

                    def enum_ch(ch, lp):
                        if not user32.IsWindowVisible(ch):
                            return True
                        c_cls = ctypes.create_unicode_buffer(256)
                        user32.GetClassNameW(ch, c_cls, 256)
                        c_txt = ctypes.create_unicode_buffer(256)
                        user32.GetWindowTextW(ch, c_txt, 256)
                        cid = user32.GetDlgCtrlID(ch)
                        cr = wintypes.RECT()
                        user32.GetWindowRect(ch, ctypes.byref(cr))
                        all_ctrls.append((ch, c_cls.value, c_txt.value.strip(), th, cid, (cr.left, cr.top, cr.right, cr.bottom), True, False))
                        return True
                    user32.EnumChildWindows(th, WNDENUMPROC(enum_ch), 0)
                return all_ctrls, top_hwnds

            def get_system_dpi_scale():
                """각 PC의 디스플레이 배율(100%, 125%, 150% 등)을 Windows API로 실시간 자동 감지"""
                try:
                    ctypes.windll.user32.SetProcessDpiAwarenessContext(-4)
                except Exception:
                    try:
                        ctypes.windll.user32.SetProcessDPIAware()
                    except Exception:
                        pass
                try:
                    if hasattr(user32, 'GetDpiForSystem'):
                        dpi = user32.GetDpiForSystem()
                        if dpi > 0:
                            return max(1.0, dpi / 96.0)
                except Exception:
                    pass
                return 1.0

            dpi_scale = get_system_dpi_scale()
            logger.info(f"🖥️ [DPI 배율 감지] 시스템 디스플레이 배율: {dpi_scale:.2f}x ({int(dpi_scale * 100)}%)")

            def find_admin_dialog_pair(ctrls):
                ok_candidate = None
                # 배율(100%, 125%, 150%)에 맞춘 동적 버튼 크기 판별
                min_w = int(20 * dpi_scale)
                max_w = int(260 * dpi_scale) # 100%->260px, 125%->325px, 150%->390px까지 수용
                min_h = int(15 * dpi_scale)
                max_h = int(110 * dpi_scale) # 100%->110px, 125%->137px, 150%->165px까지 수용

                # 1순위: 피카 전용 '관리자 모드 변경' 버튼
                for c in ctrls:
                    ch, cls_nm, txt, parent, cid, rect, is_vis, is_top = c
                    t = txt.replace(' ', '')
                    if ('관리자' in t and ('변경' in t or '모드' in t or '로그인' in t)) and t not in ['취소', '닫기'] and not is_top:
                        w = rect[2] - rect[0]
                        h = rect[3] - rect[1]
                        if min_w <= w <= max_w and min_h <= h <= max_h:
                            ok_candidate = (ch, parent, rect, txt)
                            break

                # 2순위: 범용 '확인', 'OK', '로그인' 버튼
                if not ok_candidate:
                    for c in ctrls:
                        ch, cls_nm, txt, parent, cid, rect, is_vis, is_top = c
                        t = txt.replace(' ', '')
                        if t in ['확인', 'OK', '로그인'] and not is_top:
                            w = rect[2] - rect[0]
                            h = rect[3] - rect[1]
                            if min_w <= w <= max_w and min_h <= h <= max_h:
                                ok_candidate = (ch, parent, rect, txt)
                                break

                # '취소' 버튼도 함께 탐색 (실패 시 닫기용)
                for c in ctrls:
                    ch, cls_nm, txt, parent, cid, rect, is_vis, is_top = c
                    t = txt.replace(' ', '')
                    if t in ['취소', '닫기', 'Cancel'] and not is_top:
                        cancel_candidate = (ch, parent, rect, txt)
                        break

                if ok_candidate:
                    dlg_hwnd = ok_candidate[1]
                    for c in ctrls:
                        ch, cls_nm, txt, parent, cid, rect, is_vis, is_top = c
                        if parent == dlg_hwnd and 'edit' in cls_nm.lower():
                            return (ch, parent, rect), ok_candidate, cancel_candidate

                return None, None, cancel_candidate

            # [1단계: 이미 열려 있는 관리자 로그인 창 탐색]
            ctrls, tops = dump_all_pica()
            admin_edit, admin_ok, cancel_btn = find_admin_dialog_pair(ctrls)

            if not admin_edit:
                logger.info("🔓 [피카 해제] 1단계: '관리자 로그인' 창 미발견 -> 단축키 Ctrl+Alt+Shift+X 전송...")
                for th, _ in tops:
                    cr = wintypes.RECT()
                    user32.GetWindowRect(th, ctypes.byref(cr))
                    # 화면상에 실제로 보이는(양수 좌표) 창에만 포그라운드 설정
                    if cr.right > 0 and cr.bottom > 0 and (cr.right - cr.left) > 100:
                        user32.SetForegroundWindow(th)
                        user32.BringWindowToTop(th)
                        time.sleep(0.05)
                        break

                user32.keybd_event(0x11, 0x1D, 0, 0)
                user32.keybd_event(0x10, 0x2A, 0, 0)
                user32.keybd_event(0x12, 0x38, 0, 0)
                user32.keybd_event(0x58, 0x2D, 0, 0)
                time.sleep(0.15)
                user32.keybd_event(0x58, 0x2D, 2, 0)
                user32.keybd_event(0x12, 0x38, 2, 0)
                user32.keybd_event(0x10, 0x2A, 2, 0)
                user32.keybd_event(0x11, 0x1D, 2, 0)

                for _ in range(25):
                    time.sleep(0.1)
                    ctrls, tops = dump_all_pica()
                    admin_edit, admin_ok, cancel_btn = find_admin_dialog_pair(ctrls)
                    if admin_edit:
                        break

            # [2단계: 비밀번호 1234 직접 주입 및 확인 클릭 (DPI 무관 100% 성공)]
            if admin_edit and admin_ok:
                e_hwnd, e_parent, e_rect = admin_edit
                ok_hwnd, ok_parent, ok_rect, ok_txt = admin_ok
                logger.info(f"🎯 관리자 로그인 다이얼로그 포착 완료! (Dialog HWND: {e_parent}, Edit HWND: {e_hwnd}, OK HWND: {ok_hwnd}, Button: '{ok_txt}')")

                # 대화상자 포그라운드 활성화
                user32.SetForegroundWindow(e_parent)
                time.sleep(0.06)
                user32.SetFocus(e_hwnd)
                time.sleep(0.06)

                # Edit 박스 내부 마우스 클릭으로 확실한 포커스 위치
                cx = (e_rect[0] + e_rect[2]) // 2
                cy = (e_rect[1] + e_rect[3]) // 2
                user32.SetCursorPos(cx, cy)
                time.sleep(0.04)
                user32.mouse_event(2, 0, 0, 0, 0)
                time.sleep(0.04)
                user32.mouse_event(4, 0, 0, 0, 0)
                time.sleep(0.06)

                # 기존 텍스트 완전 삭제 (Ctrl+A -> Backspace 및 EM_SETSEL)
                user32.keybd_event(VK_CONTROL, 0x1D, 0, 0)
                user32.keybd_event(VK_A, 0x1E, 0, 0)
                time.sleep(0.04)
                user32.keybd_event(VK_A, 0x1E, 2, 0)
                user32.keybd_event(VK_CONTROL, 0x1D, 2, 0)
                time.sleep(0.04)

                for _ in range(12):
                    user32.keybd_event(VK_BACK, 0x0E, 0, 0)
                    time.sleep(0.02)
                    user32.keybd_event(VK_BACK, 0x0E, 2, 0)
                    time.sleep(0.02)

                user32.SendMessageW(e_hwnd, EM_SETSEL, 0, -1)
                user32.SendMessageW(e_hwnd, WM_CLEAR, 0, 0)
                time.sleep(0.06)

                # 🚀 1순위: WM_SETTEXT (0x000C) 직접 주입
                WM_SETTEXT = 0x000C
                WM_GETTEXTLENGTH = 0x000E
                BM_CLICK = 0x00F5
                user32.SendMessageW(e_hwnd, WM_SETTEXT, 0, target_pw)
                time.sleep(0.06)
                cur_len = user32.SendMessageW(e_hwnd, WM_GETTEXTLENGTH, 0, 0)

                # 🚀 2순위: WM_SETTEXT 미반영 시 키보드 타이핑 주입
                if cur_len != len(target_pw):
                    logger.info(f"⌨️ WM_SETTEXT 미적용(길이 {cur_len}) -> 키보드 타이핑으로 비밀번호 '{target_pw}' 주입 중...")
                    for ch_digit in target_pw:
                        vk = ord(ch_digit)
                        sc = user32.MapVirtualKeyW(vk, 0)
                        user32.keybd_event(vk, sc, 0, 0)
                        time.sleep(0.04)
                        user32.keybd_event(vk, sc, 2, 0)
                        time.sleep(0.04)
                else:
                    logger.info(f"✅ WM_SETTEXT로 비밀번호 '{target_pw}' 직접 주입 완료!")

                time.sleep(0.12)

                # 🚀 확인/변경 버튼 클릭: BM_CLICK 메시지 전송 + 물리 마우스 클릭 2중 실행!
                logger.info(f"🎯 로그인 확인 버튼('{ok_txt}', HWND: {ok_hwnd}) BM_CLICK 전송 및 클릭")
                user32.SendMessageW(ok_hwnd, BM_CLICK, 0, 0)
                time.sleep(0.05)
                click_control(ok_hwnd, ok_parent, ok_rect)

                # Enter 키 보조 전송
                user32.keybd_event(VK_RETURN, 0x1C, 0, 0)
                time.sleep(0.08)
                user32.keybd_event(VK_RETURN, 0x1C, 2, 0)
                time.sleep(1.5)
            else:
                logger.warning("⚠️ '관리자 로그인' 창 쌍(Edit+OK)을 특정하지 못함!")

            # 최종 상태 확인 (최대 5초간 피카 관리자 로그인 전환 대기)
            unlocked = False
            for _ in range(10):
                if not self.is_pica_locked():
                    unlocked = True
                    break
                time.sleep(0.5)

            if unlocked:
                logger.info("🎉 [피카 해제 완료] 피카 관리자 로그인 100% 성공! (카운터 관리프로그램에 '관리자' 정상 표기)")
            else:
                logger.warning(f"⚠️ [피카 해제] 관리자 로그인 미전환 감지 (잠금 상태: {self.is_pica_locked()})")
                # 🛑 잠금해제 실패 시 '관리자 페이지' 다이얼로그가 화면에 남아있지 않도록 취소 버튼 클릭 및 ESC로 원상 복구!
                try:
                    cleanup_ctrls, _ = dump_all_pica()
                    for c in cleanup_ctrls:
                        ch, cls_nm, txt, parent, cid, rect, is_vis, is_top = c
                        t = txt.replace(' ', '')
                        if t in ['취소', '닫기', 'Cancel'] and not is_top:
                            logger.info(f"🧹 [피카 복구] 잔여 '취소' 버튼(HWND:{ch}) 감지 -> 클릭하여 관리자 창 닫기")
                            click_control(ch, parent, rect)
                            time.sleep(0.3)
                            break
                    # ESC 키 보조 전송
                    user32.keybd_event(0x1B, 0x01, 0, 0)
                    time.sleep(0.05)
                    user32.keybd_event(0x1B, 0x01, 2, 0)
                except Exception as e:
                    logger.warning(f"취소 복구 예외: {e}")
        except Exception as e:
            logger.error(f"피카 해제 매크로 실행 오류: {e}")
        finally:
            self.is_pica_unlocking = False

    def lock_pica_screen(self):
        """PC 관리 에이전트(피카/PICA) 관리자 로그아웃 -> 화면보호기 잠금 복구 (카운터 정상 대기 복귀)"""
        try:
            import ctypes
            from ctypes import wintypes
            import psutil
            import subprocess
            from client.screen_streamer import ensure_default_desktop

            ensure_default_desktop()
            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32

            BM_CLICK = 0x00F5
            BN_CLICKED = 0
            WM_COMMAND = 0x0111
            VK_RETURN = 0x0D

            WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

            def get_all_pica_controls():
                controls = []
                top_hwnds = []
                pica_pids = set()
                for p in psutil.process_iter(['pid', 'name']):
                    try:
                        if any(k in p.info['name'].lower() for k in ['pmclient', 'pmlc', 'pica']):
                            pica_pids.add(p.info['pid'])
                    except Exception:
                        pass

                def enum_top_proc(h, lp):
                    pid = wintypes.DWORD()
                    user32.GetWindowThreadProcessId(h, ctypes.byref(pid))
                    if pid.value in pica_pids and user32.IsWindowVisible(h) and not user32.IsIconic(h):
                        top_hwnds.append(h)
                    return True
                user32.EnumWindows(WNDENUMPROC(enum_top_proc), 0)

                for th in top_hwnds:
                    def enum_child_proc(ch, lp):
                        if not user32.IsWindowVisible(ch):
                            return True
                        c_cls = ctypes.create_unicode_buffer(256)
                        user32.GetClassNameW(ch, c_cls, 256)
                        c_txt = ctypes.create_unicode_buffer(256)
                        user32.GetWindowTextW(ch, c_txt, 256)
                        cid = user32.GetDlgCtrlID(ch)
                        cr = wintypes.RECT()
                        user32.GetWindowRect(ch, ctypes.byref(cr))
                        controls.append((ch, c_cls.value, c_txt.value.strip(), th, cid, (cr.left, cr.top, cr.right, cr.bottom)))
                        return True
                    user32.EnumChildWindows(th, WNDENUMPROC(enum_child_proc), 0)
                return controls

            def click_control(hwnd, parent, rect=None):
                user32.SendMessageW(hwnd, BM_CLICK, 0, 0)
                user32.PostMessageW(hwnd, BM_CLICK, 0, 0)
                if parent:
                    cid = user32.GetDlgCtrlID(hwnd)
                    wparam = ((BN_CLICKED & 0xFFFF) << 16) | (cid & 0xFFFF)
                    user32.PostMessageW(parent, WM_COMMAND, wparam, hwnd)
                if rect:
                    cx = (rect[0] + rect[2]) // 2
                    cy = (rect[1] + rect[3]) // 2
                    if cx > 0 and cy > 0:
                        user32.SetCursorPos(cx, cy)
                        time.sleep(0.04)
                        user32.mouse_event(2, 0, 0, 0, 0)
                        time.sleep(0.04)
                        user32.mouse_event(4, 0, 0, 0, 0)

            logger.info("🔒 [피카 잠금] '관리자 로그아웃' 버튼 탐색 및 복구 시도...")
            ctrls = get_all_pica_controls()

            # 만약 화면에 '관리자 페이지' 다이얼로그(취소 버튼)가 아직 떠 있다면 먼저 닫기
            has_admin_dlg = any(('관리자' in c[2].replace(' ', '') and ('변경' in c[2].replace(' ', '') or '모드' in c[2].replace(' ', ''))) for c in ctrls)
            has_cancel = False
            for ch, c_cls, c_txt, parent, cid, rect in ctrls:
                t = c_txt.replace(' ', '')
                if t in ['취소', '닫기', 'Cancel']:
                    has_cancel = True
                    logger.info(f"🧹 [피카 잠금] 열려있는 관리자 다이얼로그 취소 버튼(HWND:{ch}, '{c_txt}') 감지 -> 닫기 실행")
                    click_control(ch, parent, rect)
                    time.sleep(0.2)
                    break
            if has_admin_dlg or has_cancel:
                user32.keybd_event(0x1B, 0x01, 0, 0)
                time.sleep(0.05)
                user32.keybd_event(0x1B, 0x01, 2, 0)
                time.sleep(0.3)
                ctrls = get_all_pica_controls()

            logout_btn = None
            for ch, c_cls, c_txt, parent, cid, rect in ctrls:
                t = c_txt.replace(' ', '')
                if t in ['관리자로그아웃', '관리자로그아웃버튼']:
                    logout_btn = (ch, parent, rect, c_txt)
                    logger.info(f"🎯 1순위 '{c_txt}' 버튼(HWND:{ch}) 포착!")
                    break

            if not logout_btn:
                for ch, c_cls, c_txt, parent, cid, rect in ctrls:
                    t = c_txt.replace(' ', '')
                    if t in ['후불로그아웃', '로그아웃']:
                        logout_btn = (ch, parent, rect, c_txt)
                        logger.info(f"🎯 2순위 '{c_txt}' 버튼(HWND:{ch}) 포착!")
                        break

            if logout_btn:
                btn_hwnd, parent_hwnd, btn_rect, btn_title = logout_btn
                user32.SetForegroundWindow(parent_hwnd)
                time.sleep(0.05)
                click_control(btn_hwnd, parent_hwnd, btn_rect)
                logger.info(f"✅ '{btn_title}' 버튼 클릭 완료!")
                time.sleep(0.8)

                # 로그아웃 확인 다이얼로그 ("로그아웃 하시겠습니까?")
                ctrls2 = get_all_pica_controls()
                for ch, c_cls, c_txt, parent, cid, rect in ctrls2:
                    if c_txt in ['확인', '예', 'OK']:
                        logger.info(f"🎯 로그아웃 확인 다이얼로그 버튼('{c_txt}', HWND:{ch}) 클릭!")
                        click_control(ch, parent, rect)
                        break

                user32.keybd_event(VK_RETURN, 0x1C, 0, 0)
                time.sleep(0.05)
                user32.keybd_event(VK_RETURN, 0x1C, 2, 0)
                time.sleep(1.0)
                logger.info("🎉 [피카 잠금 완료] 관리자 로그아웃 완료 -> 화면보호기 잠금 정상 복귀!")
            else:
                logger.info("ℹ️ '관리자 로그아웃' 버튼이 없음 (이미 잠금 상태이거나 대기 화면)")
        except Exception as e:
            logger.error(f"피카 잠금 매크로 실행 오류: {e}")

    def show_update_complete_window(self):
        try:
            import tkinter as tk
            import os
            
            version_path = os.path.join(self.get_app_dir(), "version.txt")
            current_version = "알 수 없음"
            if os.path.exists(version_path):
                with open(version_path, "r", encoding="utf-8") as f:
                    current_version = f.read().strip()
            
            root = tk.Tk()
            root.title("업데이트 완료")
            root.geometry("380x100")
            root.attributes("-topmost", True)
            root.eval('tk::PlaceWindow . center')
            lbl = tk.Label(root, text=f"✅ 제우스 에이전트 v{current_version} 패치 완료!", font=("맑은 고딕", 10))
            lbl.pack(pady=20)
            root.after(2000, root.destroy)  # 2초 후 자동 소멸
            root.mainloop()
        except Exception as e:
            logger.warning(f"완료창 표시 생략: {e}")

    def start(self):
        """에이전트 전체 구동"""
        # 0. 자동 업데이트 체크
        try:
            self.check_and_apply_update()
        except Exception as e:
            logger.warning(f"업데이트 체크 중 예외: {e}")

        # 0.5 업데이트 완료 플래그 정리 (절대 자동 재부팅 금지 -> 무한 루프 원천 차단)
        try:
            flag_path = os.path.join(self.get_app_dir(), "just_updated.flag")
            if os.path.exists(flag_path):
                try:
                    os.remove(flag_path)
                except Exception:
                    pass
                logger.info("🛡️ [업데이트 완료] 최신 버전 정상 가동 시작!")
                # 완료 토스트 창을 백그라운드 스레드에서 2초간 표시 (통신 블로킹 없이 사용자에게 시각적 확인 제공)
                threading.Thread(target=self.show_update_complete_window, daemon=True).start()
        except Exception as e:
            logger.warning(f"업데이트 완료 플래그 확인 중 예외: {e}")

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
            self.tray = ClientTrayUI(on_restart_netflix=self.start_netflix_routine)
            threading.Thread(target=self.tray.run_tray, daemon=True).start()
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
