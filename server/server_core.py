# -*- coding: utf-8 -*-
r"""
제우스 HDD PROTECTOR - FastAPI & WebSocket 통합 중앙 관제 서버
G:\내 드라이브\PROJECT\HDDGOD\server\server_core.py
"""
import os
import json
import logging
import asyncio
import threading
from contextlib import asynccontextmanager
from typing import Dict, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
import time
import psutil
import requests
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from common.config import (
    SERVER_HOST, SERVER_PORT, config,
    TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, TELEGRAM_ALERT_THRESHOLD
)
from common.protocol import (
    PacketType, CommandType, make_packet, parse_packet
)
from server.wol_watchdog import WOLWatchdog
from server.mail_otp_extractor import NateMailOTPExtractor
from server.kakao_notifier import KakaoNotifier
from server.remote_relay import RemoteRelay
from server.tunnel_manager import tunnel_manager

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [SERVER] %(levelname)s: %(message)s"
)
logger = logging.getLogger("ZeusServer")

async def send_telegram_msg(msg: str):
    """텔레그램 메시지 발송 헬퍼"""
    from common.config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        try:
            import requests
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            await asyncio.to_thread(requests.post, url, json={"chat_id": TELEGRAM_CHAT_ID, "text": msg}, timeout=5)
        except Exception as e:
            logger.error(f"텔레그램 발송 실패: {e}")

import sys
def get_resource_dir():
    if getattr(sys, 'frozen', False):
        return os.path.join(sys._MEIPASS, 'server')
    return os.path.dirname(os.path.abspath(__file__))

def get_root_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

BASE_DIR = get_resource_dir()
PROJECT_ROOT = get_root_dir()

# pc_mapping.json과 아이콘 폴더 등은 실제 실행 파일 옆에 저장되어야 함 (읽기/쓰기)
MAPPING_FILE = os.path.join(PROJECT_ROOT, "server", "pc_mapping.json")
os.makedirs(os.path.join(PROJECT_ROOT, "server"), exist_ok=True)
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

def check_windows_autostart() -> bool:
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_READ)
        val, _ = winreg.QueryValueEx(key, "ZeusServer")
        winreg.CloseKey(key)
        return bool(val)
    except Exception:
        return False

def set_windows_autostart(enable: bool) -> bool:
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
        if enable:
            exe_target = r"C:\Users\USER\Documents\HDDGOD\dist\ZeusServer.exe"
            if getattr(sys, 'frozen', False):
                exe_target = sys.executable
            elif os.path.exists(os.path.join(PROJECT_ROOT, "dist", "ZeusServer.exe")):
                exe_target = os.path.join(PROJECT_ROOT, "dist", "ZeusServer.exe")
            cmd = f'"{exe_target}"'
            winreg.SetValueEx(key, "ZeusServer", 0, winreg.REG_SZ, cmd)
            logger.info(f"윈도우 시작프로그램 등록 완료: {cmd}")
        else:
            try:
                winreg.DeleteValue(key, "ZeusServer")
                logger.info("윈도우 시작프로그램 등록 해제 완료")
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)
        return True
    except Exception as e:
        logger.error(f"시작프로그램 설정 실패: {e}")
        return False

def check_supervisor_active() -> bool:
    status_file = os.path.join(PROJECT_ROOT, "server", ".supervisor_status.json")
    if os.path.exists(status_file):
        try:
            with open(status_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if data.get("is_running", False) and (time.time() - data.get("last_heartbeat", 0) < 60):
                    return True
                pid = data.get("supervisor_pid")
                if pid:
                    import psutil
                    if psutil.pid_exists(pid):
                        return True
        except Exception:
            pass
    return False

def kill_duplicate_servers():
    """현재 PID를 제외한 다른 ZeusServer 프로세스를 모두 강제 종료 (중복 실행 방지)"""
    current_pid = os.getpid()
    current_exe = sys.executable  # 현재 실행 EXE 경로
    killed = []
    try:
        for proc in psutil.process_iter(['pid', 'name', 'exe', 'create_time']):
            try:
                if proc.pid == current_pid:
                    continue
                pname = (proc.info.get('name') or '').lower()
                pexe  = (proc.info.get('exe')  or '').lower()
                if 'zeusserver' in pname or 'zeusserver' in pexe:
                    proc.kill()
                    killed.append(proc.pid)
                    logger.warning(f"🔪 중복 ZeusServer 프로세스 강제 종료: PID {proc.pid}")
            except Exception:
                pass
    except Exception as e:
        logger.error(f"중복 프로세스 제거 실패: {e}")
    if killed:
        import time as _t; _t.sleep(1)  # 포트 해제 대기


@asynccontextmanager
async def lifespan(app):
    # ── 서버 시작 ────────────────────────────────────────────────
    asyncio.create_task(watchdog.run_watchdog_loop())
    asyncio.create_task(tunnel_manager.start())
    asyncio.create_task(notify_tunnel_url_to_telegram())
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        asyncio.create_task(telegram_alert_loop())
    asyncio.create_task(auto_optimize_loop())
    from server.pica_watchdog import pica_dog
    from common.config import config as cfg
    pica_dog.load_config(cfg)
    pica_dog.telegram_callback = send_telegram_msg
    if pica_dog.is_enabled:
        pica_dog.start()

    # 윈도우 작업표시줄 시스템 트레이 아이콘 백그라운드 구동
    try:
        from server.server_tray import start_server_tray_thread
        start_server_tray_thread(SERVER_PORT)
        logger.info("⚡ 제우스 관제 서버 트레이 아이콘 데몬 가동 완료")
    except Exception as e:
        logger.warning(f"트레이 아이콘 시작 건너뜀: {e}")

    logger.info(f"🚀 제우스 중앙 관제 서버 가동 완료: http://{SERVER_HOST}:{SERVER_PORT}")
    yield
    # ── 서버 종료 ────────────────────────────────────────────────
    try:
        from server.server_tray import server_tray
        if server_tray.icon:
            server_tray.icon.stop()
    except Exception:
        pass
    pica_dog.stop()
    tunnel_manager.stop()
    logger.info("🛑 제우스 중앙 관제 서버 종료 및 터널 정리 완료")

app = FastAPI(title="제우스 HDD PROTECTOR 통합 관제 서버", lifespan=lifespan)

MASTER_ICONS_DIR = os.path.join(PROJECT_ROOT, "server", "master_icons")
os.makedirs(MASTER_ICONS_DIR, exist_ok=True)
app.mount("/icons", StaticFiles(directory=MASTER_ICONS_DIR), name="icons")

STATIC_DIR = os.path.join(BASE_DIR, "static")
os.makedirs(STATIC_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    from fastapi.responses import FileResponse
    favicon_path = os.path.join(STATIC_DIR, "favicon.ico")
    if os.path.exists(favicon_path):
        return FileResponse(favicon_path, media_type="image/x-icon")
    return HTMLResponse("", status_code=404)

@app.get("/api/icons/list")
async def get_icons_list():
    """서버의 마스터 아이콘 폴더 파일 목록 반환 API"""
    if os.path.exists(MASTER_ICONS_DIR):
        items = os.listdir(MASTER_ICONS_DIR)
        return {"icons": [item for item in items if os.path.isfile(os.path.join(MASTER_ICONS_DIR, item))]}
    return {"icons": []}

watchdog = WOLWatchdog(timeout_sec=10)
mail_extractor = NateMailOTPExtractor()
kakao_notifier = KakaoNotifier()
remote_relay = RemoteRelay()

def load_pc_mapping():
    """저장된 PC 매핑 목록 불러오기 (없으면 기본 10대 생성 및 영구 보존)"""
    if os.path.exists(MAPPING_FILE):
        try:
            with open(MAPPING_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list) and len(data) > 0:
                    return data
        except Exception as e:
            logger.warning(f"pc_mapping.json 읽기 오류: {e}")

    default_list = []
    for i in range(1, 11):
        default_list.append({
            "seat": i,
            "id": f"PC-{str(i).zfill(2)}",
            "name": f"PC {i}번",
            "ip": f"192.168.0.{10 + i}",
            "mac": "00:00:00:00:00:00",
            "status": "OFFLINE",
            "uwf": "UNKNOWN",
            "netflix": "CLOSED"
        })
    save_pc_mapping(default_list)
    return default_list

mapping_lock = threading.Lock()

def save_pc_mapping(mapping_data):
    """PC 매핑 목록 파일로 영구 저장 (동시성 락 및 원자적 교체로 손상 방지)"""
    with mapping_lock:
        try:
            temp_file = MAPPING_FILE + ".tmp"
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(mapping_data, f, ensure_ascii=False, indent=2)
            os.replace(temp_file, MAPPING_FILE)
            return True
        except Exception as e:
            logger.error(f"pc_mapping.json 저장 실패: {e}")
            return False

def get_actual_client_id(target_id: str) -> str:
    """좌석 ID(PC-01 등) 또는 호스트명을 실제 WebSocket 연결된 active_clients ID로 변환"""
    if target_id in active_clients:
        return target_id

    pcs = load_pc_mapping()
    target_ip = None
    target_mac = None
    for p in pcs:
        if p.get("id") == target_id or str(p.get("seat")) == target_id or p.get("name") == target_id:
            target_ip = p.get("ip")
            target_mac = p.get("mac")
            break

    # 1. IP 매칭
    if target_ip:
        for cid in active_clients:
            c_info = watchdog.clients.get(cid, {})
            if c_info.get("ip") == target_ip:
                return cid

    # 2. MAC 매칭
    if target_mac and target_mac != "00:00:00:00:00:00":
        for cid in active_clients:
            c_info = watchdog.clients.get(cid, {})
            if c_info.get("mac", "").lower() == target_mac.lower():
                return cid

    # 3. 로컬 테스트 및 단일 클라이언트 매핑 (1번방 열었을 때 접속자가 1명이면 자동 매칭)
    if len(active_clients) == 1 and (target_id in ["PC-01", "1", "PC-1"] or target_id not in watchdog.clients):
        return next(iter(active_clients.keys()))

    return target_id

def get_client_ws(target_id: str) -> Optional[WebSocket]:
    """target_id에 해당하는 실제 WebSocket 세션 반환"""
    actual_id = get_actual_client_id(target_id)
    return active_clients.get(actual_id)

# client_id -> WebSocket connection
active_clients: Dict[str, WebSocket] = {}
dashboard_subscribers: set = set()

# --- 웹 페이지 라우트 ---

@app.get("/", response_class=HTMLResponse)
async def get_dashboard(request: Request):
    """중앙 관제 및 IP 매핑 대시보드 (저장된 PC 목록 주입)"""
    pc_list = load_pc_mapping()
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "initial_pc_list": json.dumps(pc_list, ensure_ascii=False),
            "pc_count": len(pc_list)
        }
    )


@app.get("/mobile", response_class=HTMLResponse)
async def get_mobile_dashboard(request: Request):
    """스마트폰 전용 모바일 관제 대시보드"""
    pc_list = load_pc_mapping()
    return templates.TemplateResponse(
        request=request,
        name="mobile_dashboard.html",
        context={
            "initial_pc_list": json.dumps(pc_list, ensure_ascii=False),



            "pc_count": len(pc_list)
        }
    )

@app.get("/api/get_mapping")
async def get_mapping():
    """저장된 PC 목록 조회 API"""
    return load_pc_mapping()

@app.get("/remote/{client_id}", response_class=HTMLResponse)
async def get_remote_view(request: Request, client_id: str):
    """모바일 및 PC 터치 원격 제어 화면"""
    actual_cid = get_actual_client_id(client_id)
    ws = get_client_ws(client_id)
    is_online = (ws is not None)

    # 클라이언트 PC 정보 조회 (이름 및 실제 IP)
    c_info = watchdog.clients.get(actual_cid, {})
    client_ip = c_info.get("ip", "")
    client_name = client_id
    for p in load_pc_mapping():
        if p.get("id") == client_id or str(p.get("seat")) == client_id:
            if not client_ip:
                client_ip = p.get("ip", "")
            client_name = p.get("name", client_id)
            break

    if is_online:
        cmd = make_packet(PacketType.COMMAND, {"action": CommandType.START_SCREEN_STREAM})
        await ws.send_text(cmd)
        logger.info(f"[{actual_cid}] 화면 스트리밍 시작 명령 전달 성공 (요청 ID: {client_id})")
    else:
        logger.warning(f"[{client_id}] 원격 제어 대상 클라이언트를 찾을 수 없음 (오프라인)")

    return templates.TemplateResponse(
        request=request,
        name="remote_view.html",
        context={
            "client_id": client_id,
            "actual_client_id": actual_cid,
            "client_name": client_name,
            "client_ip": client_ip,
            "is_online": is_online
        }
    )

@app.get("/api/rdp/{client_id}")
async def get_rdp_file(client_id: str):
    """윈도우 기본 원격 데스크톱(mstsc) 연결용 .rdp 파일 생성 및 다운로드"""
    from fastapi.responses import Response
    actual_cid = get_actual_client_id(client_id)
    c_info = watchdog.clients.get(actual_cid, {})
    target_ip = c_info.get("ip")
    if not target_ip:
        for p in load_pc_mapping():
            if p.get("id") == client_id or str(p.get("seat")) == client_id:
                target_ip = p.get("ip")
                break
    if not target_ip:
        target_ip = "127.0.0.1"

    rdp_content = f"""full address:s:{target_ip}
prompt for credentials:i:1
screen mode id:i:2
use multimon:i:0
session bpp:i:32
compression:i:1
keyboardhook:i:2
audiomode:i:0
redirectclipboard:i:1
"""
    return Response(
        content=rdp_content.encode("utf-16le"),
        media_type="application/x-rdp",
        headers={"Content-Disposition": f'attachment; filename="{client_id}_{target_ip}.rdp"'}
    )

@app.get("/otp/{client_id}", response_class=HTMLResponse)
async def get_otp_page(request: Request, client_id: str):
    """예비 넷플릭스 4자리 OTP 입력 페이지"""
    return templates.TemplateResponse(request=request, name="otp_input.html", context={"client_id": client_id})

# --- WebSocket 라우트 ---

@app.websocket("/ws/client/{client_id}")
async def client_websocket(websocket: WebSocket, client_id: str):
    """클라이언트 PC 에이전트 전용 통신 채널"""
    await websocket.accept()
    active_clients[client_id] = websocket
    logger.info(f"클라이언트 연결 승인: {client_id}")

    try:
        while True:
            raw_msg = await websocket.receive_text()
            packet = parse_packet(raw_msg)
            p_type = packet.get("type")
            data = packet.get("data", {})

            if p_type == PacketType.HEARTBEAT:
                # 3초 하트비트 수신 및 감시자 업데이트
                ip = data.get("ip", "")
                mac = data.get("mac", "")
                uwf_st = data.get("uwf_status", "")
                netflix_st = data.get("netflix_status", "")
                watchdog.update_heartbeat(client_id, ip, mac, uwf_st, netflix_st)

            elif p_type == PacketType.OTP_REQUIRED:
                # 넷플릭스 4자리 인증번호 필요 감지!
                logger.info(f"[{client_id}] 넷플릭스 OTP 요청 수신! 네이버 메일 자동 조회 트리거...")
                asyncio.create_task(handle_auto_otp_flow(client_id))

            elif p_type == PacketType.CREDENTIAL_REQUEST:
                # 넷플릭스 다중 계정 자동 분배 및 보안(Zero-Trust) 요청
                from server.netflix_account_manager import account_manager
                acc = await account_manager.get_credential(client_id)
                if acc:
                    await websocket.send_text(make_packet(PacketType.CREDENTIAL_RESPONSE, {
                        "email": acc["email"],
                        "password": acc["password"]
                    }))

            elif p_type == PacketType.SCREEN_FRAME:
                # 원격 제어 화면 프레임 릴레이 (실제 ID 및 매핑된 모든 좌석 채널로 동시 중계)
                frame = data.get("frame", "")
                await remote_relay.broadcast_frame(client_id, frame)
                try:
                    for p in load_pc_mapping():
                        if get_actual_client_id(p.get("id")) == client_id:
                            await remote_relay.broadcast_frame(p.get("id"), frame)
                except Exception:
                    pass

            elif p_type == PacketType.ERROR_REPORT:
                error_msg = data.get("error", "Unknown error")
                trace = data.get("traceback", "")
                log_entry = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Client: {client_id} | Error: {error_msg}\n{trace}\n"
                logger.error(f"🚨 [텔레메트리] 클라이언트 {client_id} 오류 보고 수신:\n{error_msg}")
                with open(os.path.join(PROJECT_ROOT, "server", "error_reports.log"), "a", encoding="utf-8") as f:
                    f.write(log_entry + "-"*60 + "\n")

            elif p_type == PacketType.LOG_STREAM:
                # 실시간 로그 스트리밍: 대시보드로 중계 + 파일 저장
                level = data.get("level", "INFO")
                msg = data.get("message", "")
                ts = data.get("timestamp", time.strftime("%H:%M:%S"))
                log_entry = {
                    "type": "log",
                    "client_id": client_id,
                    "level": level,
                    "message": msg,
                    "timestamp": ts
                }
                # 대시보드 WebSocket으로 실시간 중계
                import json as _json
                await asyncio.gather(
                    *[ws.send_text(_json.dumps(log_entry, ensure_ascii=False))
                      for ws in list(dashboard_subscribers) if ws],
                    return_exceptions=True
                )
                # 파일 저장 (PC별 로그 파일)
                log_dir = os.path.join(PROJECT_ROOT, "server", "client_logs")
                os.makedirs(log_dir, exist_ok=True)
                log_path = os.path.join(log_dir, f"{client_id}.log")
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(f"[{ts}] [{level}] {msg}\n")

    except WebSocketDisconnect:
        logger.warning(f"클라이언트 연결 종료: {client_id}")
    finally:
        if client_id in active_clients:
            del active_clients[client_id]

async def handle_auto_otp_flow(client_id: str):
    """1차: 네이트 메일 자동 추출 시도 -> 실패 시 2차: 카카오톡 알림 발송"""
    otp = await mail_extractor.poll_netflix_otp(timeout_sec=35, interval_sec=2)
    if otp:
        logger.info(f"🎉 네이트 메일에서 4자리 코드 [{otp}] 자동 추출 성공! {client_id}로 자동 전송...")
        ws = get_client_ws(client_id)
        if ws:
            pkt = make_packet(PacketType.OTP_SUBMIT, {"otp_code": otp})
            await ws.send_text(pkt)
            return

    # 35초 초과 시 2차 카카오 알림 fallback
    logger.warning(f"[{client_id}] 네이트 메일 자동 수신 타임아웃 -> 2차 카카오 알림톡 발송")
    otp_url = f"http://{SERVER_HOST}:{SERVER_PORT}/otp/{client_id}"
    kakao_notifier.send_otp_alert(client_id, otp_url)

@app.websocket("/ws/dashboard")
async def dashboard_websocket(websocket: WebSocket):
    """대시보드 실시간 상태 브로드캐스트 채널"""
    await websocket.accept()
    dashboard_subscribers.add(websocket)
    try:
        while True:
            cpu_usage = psutil.cpu_percent(interval=None)
            ram_info = psutil.virtual_memory()
            ram_usage = ram_info.percent
            server_ram_mb = round(psutil.Process().memory_info().rss / 1024 / 1024, 1)
            
            state_data = {
                "type": "FULL_STATE",
                "cpu": cpu_usage,
                "ram": ram_usage,
                "server_ram_mb": server_ram_mb,
                "auto_optimize": AUTO_OPTIMIZE_ENABLED,
                "clients": watchdog.clients
            }
            await websocket.send_text(json.dumps(state_data, ensure_ascii=False))
            await asyncio.sleep(2)
    except WebSocketDisconnect:
        dashboard_subscribers.remove(websocket)

@app.websocket("/ws/remote_view/{client_id}")
async def remote_view_websocket(websocket: WebSocket, client_id: str):
    """원격 제어 뷰어 연결 (좌석 ID / 실제 ID 스마트 브리지)"""
    await websocket.accept()
    actual_cid = get_actual_client_id(client_id)
    remote_relay.add_viewer(client_id, websocket)
    if actual_cid != client_id:
        remote_relay.add_viewer(actual_cid, websocket)

    # 뷰어 접속 즉시 클라이언트에 화면 스트리밍 시작 명령 발송
    ws = get_client_ws(client_id)
    if ws:
        cmd = make_packet(PacketType.COMMAND, {"action": CommandType.START_SCREEN_STREAM})
        await ws.send_text(cmd)
        logger.info(f"[{actual_cid}] 뷰어 접속 확인 -> 화면 스트리밍 즉각 시작 명령 전송!")

    try:
        while True:
            raw = await websocket.receive_text()
            evt_data = json.loads(raw)
            # 뷰어의 마우스/터치 이벤트를 클라이언트로 바이패스 전송
            target_ws = get_client_ws(client_id)
            if target_ws:
                pkt = make_packet(PacketType.REMOTE_INPUT, evt_data)
                await target_ws.send_text(pkt)
    except WebSocketDisconnect:
        remote_relay.remove_viewer(client_id, websocket)
        if actual_cid != client_id:
            remote_relay.remove_viewer(actual_cid, websocket)
        # 뷰어가 아무도 없으면 스트리밍 중지
        target_ws = get_client_ws(client_id)
        if target_ws and actual_cid not in remote_relay.viewers and client_id not in remote_relay.viewers:
            cmd = make_packet(PacketType.COMMAND, {"action": CommandType.STOP_SCREEN_STREAM})
            await target_ws.send_text(cmd)
            logger.info(f"[{actual_cid}] 모든 뷰어 퇴장 -> 화면 스트리밍 절전 중지")

# --- 제어 REST API ---

@app.post("/api/command/{client_id}/{action}")
async def send_command(client_id: str, action: str):
    ws = get_client_ws(client_id)
    actual_cid = get_actual_client_id(client_id)
    if ws:
        cmd = make_packet(PacketType.COMMAND, {"action": action})
        await ws.send_text(cmd)
        if action == CommandType.SHUTDOWN:
            watchdog.set_normal_shutdown(actual_cid)
        return {"status": "ok", "sent_to": actual_cid, "action": action}
    elif action == "WOL":
        mac = None
        for p in load_pc_mapping():
            if p.get("id") == client_id or str(p.get("seat")) == client_id:
                mac = p.get("mac")
                break
        if not mac:
            mac = watchdog.clients.get(actual_cid, {}).get("mac")
        if mac:
            watchdog.send_wol_packet(mac)
            return {"status": "ok", "wol_sent_mac": mac}
    return {"status": "error", "message": "클라이언트가 오프라인입니다."}

@app.post("/api/command_all/{action}")
async def send_command_all(action: str):
    for cid, ws in active_clients.items():
        cmd = make_packet(PacketType.COMMAND, {"action": action})
        await ws.send_text(cmd)
        if action == CommandType.SHUTDOWN:
            watchdog.set_normal_shutdown(cid)
    return {"status": "ok", "action": action, "count": len(active_clients)}


@app.post("/api/optimize_memory")
async def optimize_memory():
    """윈도우 OS의 전체 프로세스 유휴 캐시 메모리를 안전하게 회수 (EmptyWorkingSet)"""
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
    logger.info(f"⚡ [메모리 최적화 완료] {trimmed_count}개 프로세스 정리, {freed_mb}MB 메모리 즉시 확보 (현재 점유율: {after_vm.percent}%)")

    return {
        "status": "ok",
        "trimmed_count": trimmed_count,
        "freed_mb": freed_mb,
        "current_ram_percent": after_vm.percent,
        "available_gb": round(after_vm.available / (1024**3), 2)
    }

@app.post("/api/wol_all")
async def send_wol_all():
    count = 0
    for cid, info in watchdog.clients.items():
        mac = info.get("mac")
        if mac and mac != "00:00:00:00:00:00":
            watchdog.send_wol_packet(mac)
            count += 1
    return {"status": "ok", "wol_sent_count": count}

@app.post("/api/submit_otp/{client_id}")
async def manual_submit_otp(client_id: str, payload: dict):
    code = payload.get("otp_code", "")
    if client_id in active_clients:
        pkt = make_packet(PacketType.OTP_SUBMIT, {"otp_code": code})
        await active_clients[client_id].send_text(pkt)
        return {"status": "ok", "code": code}
    return {"status": "error", "message": "클라이언트가 오프라인입니다."}

@app.post("/api/save_mapping")
async def save_mapping(request: Request):
    mapping_data = await request.json()
    save_pc_mapping(mapping_data)
    return {"status": "ok", "saved_count": len(mapping_data)}

@app.get("/api/tunnel_info")
async def get_tunnel_info():
    """스마트폰 원격 접속 정보 및 QR코드용 네트워크 주소 반환"""
    return tunnel_manager.get_info()

# --- 서버 생명주기 (시작/종료 이벤트) ---


AUTO_OPTIMIZE_ENABLED = False

async def auto_optimize_loop():
    while True:
        await asyncio.sleep(3600)  # 1시간 대기
        if AUTO_OPTIMIZE_ENABLED:
            import gc
            import ctypes
            gc.collect()
            try:
                ctypes.windll.kernel32.SetProcessWorkingSetSize(ctypes.windll.kernel32.GetCurrentProcess(), -1, -1)
                logger.info("1시간 주기 자동 메모리 최적화 완료")
            except Exception as e:
                pass

@app.post("/api/toggle_auto_optimize")
async def toggle_auto_optimize():
    global AUTO_OPTIMIZE_ENABLED
    AUTO_OPTIMIZE_ENABLED = not AUTO_OPTIMIZE_ENABLED
    return {"status": "ok", "enabled": AUTO_OPTIMIZE_ENABLED}

@app.post("/api/command")
async def send_command_mobile(request: Request):
    """모바일 대시보드 전용 명령 API - JSON body: {target_id, command}"""
    body = await request.json()
    target_id = body.get("target_id", "")
    action = body.get("command", "")
    if target_id == "ALL":
        for cid, ws in active_clients.items():
            cmd = make_packet(PacketType.COMMAND, {"action": action})
            await ws.send_text(cmd)
            if action == CommandType.SHUTDOWN:
                watchdog.set_normal_shutdown(cid)
        return {"status": "ok", "action": action, "count": len(active_clients)}
    ws = get_client_ws(target_id)
    actual_cid = get_actual_client_id(target_id)
    if ws:
        cmd = make_packet(PacketType.COMMAND, {"action": action})
        await ws.send_text(cmd)
        if action == CommandType.SHUTDOWN:
            watchdog.set_normal_shutdown(actual_cid)
        return {"status": "ok", "sent_to": actual_cid, "action": action}
    return {"status": "error", "message": "클라이언트가 오프라인입니다."}

# ── 클라이언트 자동 업데이트 API ───────────────────────────────
@app.get("/api/version")
async def get_version():
    """최신 클라이언트 버전 반환"""
    version_path = os.path.join(PROJECT_ROOT, "deploy", "ClientDeploy", "core", "version.txt")
    if os.path.exists(version_path):
        try:
            with open(version_path, "r", encoding="utf-8") as f:
                return f.read().strip()
        except Exception:
            try:
                with open(version_path, "r", encoding="utf-16le") as f:
                    return f.read().strip()
            except Exception:
                pass
    return "1.0.0"

@app.get("/api/download/update")
async def download_update():
    """최신 클라이언트 실행 파일 또는 패키지 다운로드"""
    from fastapi.responses import FileResponse
    zip_path = os.path.join(PROJECT_ROOT, "deploy", "ClientDeploy", "ZeusAgent.zip")
    if os.path.exists(zip_path):
        return FileResponse(zip_path, filename="ZeusAgent.zip")
    exe_path = os.path.join(PROJECT_ROOT, "deploy", "ClientDeploy", "core", "ZeusAgent.exe")
    if os.path.exists(exe_path):
        return FileResponse(exe_path, filename="ZeusAgent.exe")
    return HTMLResponse("Update file not found", status_code=404)

# ── 환경설정(Settings) 통합 관리 REST API ───────────────────────
@app.get("/api/settings")
async def get_settings():
    """서버/클라이언트 설정값 및 상태 일괄 조회"""
    version_path = os.path.join(PROJECT_ROOT, "deploy", "ClientDeploy", "core", "version.txt")
    exe_path = os.path.join(PROJECT_ROOT, "deploy", "ClientDeploy", "core", "ZeusAgent.exe")
    
    client_version = "1.0.0"
    if os.path.exists(version_path):
        try:
            with open(version_path, "r", encoding="utf-8") as f:
                client_version = f.read().strip().replace('\ufeff', '')
        except Exception:
            try:
                with open(version_path, "r", encoding="utf-16le") as f:
                    client_version = f.read().strip().replace('\ufeff', '')
            except Exception:
                pass

    exe_exists = os.path.exists(exe_path)
    exe_size_str = "0 MB"
    if exe_exists:
        exe_size_str = f"{os.path.getsize(exe_path) / (1024 * 1024):.1f} MB"

    cfg_file = os.path.join(PROJECT_ROOT, "deploy", "ClientDeploy", "core", "config.ini")
    import configparser
    cfg = configparser.ConfigParser()
    if os.path.exists(cfg_file):
        cfg.read(cfg_file, encoding="utf-8")

    return {
        "status": "ok",
        "server_host": cfg.get("SERVER", "SERVER_HOST", fallback="0.0.0.0"),
        "server_port": cfg.getint("SERVER", "SERVER_PORT", fallback=8000),
        "client_server_ip": cfg.get("CLIENT", "SERVER_IP", fallback="192.168.0.100"),
        "client_server_port": cfg.getint("CLIENT", "SERVER_PORT", fallback=8000),
        "admin_password": cfg.get("CLIENT", "ADMIN_PASSWORD", fallback="1234"),
        "client_version": client_version,
        "agent_file_exists": exe_exists,
        "agent_file_size": exe_size_str,
        "windows_autostart": check_windows_autostart(),
        "supervisor_active": check_supervisor_active(),
        "telegram_bot_token": cfg.get("TELEGRAM", "BOT_TOKEN", fallback=""),
        "telegram_chat_id": cfg.get("TELEGRAM", "CHAT_ID", fallback=""),
        "telegram_threshold": cfg.getint("TELEGRAM", "ALERT_THRESHOLD_PERCENT", fallback=80),
        "connected_clients_count": len(active_clients)
    }

@app.post("/api/settings")
async def save_settings(request: Request):
    """환경설정 저장 API"""
    data = await request.json()
    cfg_file = os.path.join(PROJECT_ROOT, "deploy", "ClientDeploy", "core", "config.ini")
    import configparser
    cfg = configparser.ConfigParser()
    if os.path.exists(cfg_file):
        cfg.read(cfg_file, encoding="utf-8")

    if not cfg.has_section("SERVER"):
        cfg.add_section("SERVER")
    if not cfg.has_section("CLIENT"):
        cfg.add_section("CLIENT")
    if not cfg.has_section("TELEGRAM"):
        cfg.add_section("TELEGRAM")

    if "server_host" in data:
        cfg.set("SERVER", "SERVER_HOST", str(data["server_host"]).strip())
    if "server_port" in data:
        cfg.set("SERVER", "SERVER_PORT", str(data["server_port"]).strip())
    if "client_server_ip" in data:
        cfg.set("CLIENT", "SERVER_IP", str(data["client_server_ip"]).strip())
    if "client_server_port" in data:
        cfg.set("CLIENT", "SERVER_PORT", str(data["client_server_port"]).strip())
    if "admin_password" in data:
        cfg.set("CLIENT", "ADMIN_PASSWORD", str(data["admin_password"]).strip())
    if "telegram_bot_token" in data:
        cfg.set("TELEGRAM", "BOT_TOKEN", str(data["telegram_bot_token"]).strip())
    if "telegram_chat_id" in data:
        cfg.set("TELEGRAM", "CHAT_ID", str(data["telegram_chat_id"]).strip())
    if "telegram_threshold" in data:
        cfg.set("TELEGRAM", "ALERT_THRESHOLD_PERCENT", str(data["telegram_threshold"]).strip())

    # G드라이브 및 C드라이브 config.ini 이중 동기화
    for cf in [cfg_file, r"C:\Users\USER\Documents\HDDGOD\deploy\ClientDeploy\core\config.ini"]:
        try:
            os.makedirs(os.path.dirname(cf), exist_ok=True)
            with open(cf, "w", encoding="utf-8") as f:
                cfg.write(f)
        except Exception:
            pass

    # 대시보드 바로가기(.url) URL 최신화 (G:, C: 및 바탕화면)
    t_ip = str(data.get("client_server_ip", "")).strip() or "192.168.0.100"
    t_port = str(data.get("server_port", "")).strip() or "8000"
    sc_content = f"[InternetShortcut]\nURL=http://{t_ip}:{t_port}\n"
    for sc_dir in [PROJECT_ROOT, r"C:\Users\USER\Documents\HDDGOD", os.path.join(os.path.expanduser("~"), "Desktop")]:
        try:
            with open(os.path.join(sc_dir, "제우스 HDD PROTECTOR_관제_대시보드.url"), "w", encoding="utf-8") as sf:
                sf.write(sc_content)
        except Exception:
            pass

    # 윈도우 시작프로그램 설정 동기화
    if "windows_autostart" in data:
        set_windows_autostart(bool(data["windows_autostart"]))

    return {"status": "ok", "message": "설정이 성공적으로 저장되었습니다."}

@app.post("/api/settings/autostart")
async def toggle_autostart(request: Request):
    """윈도우 시작 시 서버 자동 실행 토글 API"""
    data = await request.json()
    enable = bool(data.get("enabled", False))
    success = set_windows_autostart(enable)
    return {"status": "ok" if success else "error", "enabled": check_windows_autostart()}

@app.post("/api/settings/update_client")
async def trigger_client_update(request: Request):
    """클라이언트 에이전트 OTA 업데이트 강제 배포 API"""
    data = await request.json()
    new_version = data.get("new_version", "").strip()
    
    version_path = os.path.join(PROJECT_ROOT, "deploy", "ClientDeploy", "core", "version.txt")
    if new_version:
        with open(version_path, "w", encoding="utf-8") as f:
            f.write(new_version)

    current_version = "1.0.0"
    if os.path.exists(version_path):
        try:
            with open(version_path, "r", encoding="utf-8") as f:
                current_version = f.read().strip()
        except Exception:
            try:
                with open(version_path, "r", encoding="utf-16le") as f:
                    current_version = f.read().strip()
            except Exception:
                pass

    # 전체 클라이언트에 UPDATE_AGENT 명령 전송
    count = 0
    for cid, ws in active_clients.items():
        cmd = make_packet(PacketType.COMMAND, {"action": CommandType.UPDATE_AGENT})
        await ws.send_text(cmd)
        count += 1

    return {
        "status": "ok",
        "version": current_version,
        "sent_count": count,
        "message": f"버전 {current_version} 업데이트 명령이 {count}대 PC로 전송되었습니다."
    }

@app.post("/api/settings/test_telegram")
async def test_telegram(request: Request):
    """텔레그램 봇 테스트 메시지 전송 API"""
    data = await request.json()
    token = data.get("bot_token") or TELEGRAM_BOT_TOKEN
    chat_id = data.get("chat_id") or TELEGRAM_CHAT_ID

    if not token or not chat_id:
        return {"status": "error", "message": "텔레그램 봇 토큰 또는 Chat ID가 비어있습니다."}

    test_msg = "🔔 [제우스 HDD PROTECTOR] 텔레그램 연동 테스트 메시지가 성공적으로 도착했습니다!"
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        r = requests.post(url, json={"chat_id": chat_id, "text": test_msg}, timeout=5)
        if r.status_code == 200:
            return {"status": "ok", "message": "텔레그램 메시지 발송 성공!"}
        else:
            return {"status": "error", "message": f"발송 실패 (상태코드 {r.status_code}): {r.text}"}
    except Exception as e:
        return {"status": "error", "message": f"텔레그램 통신 오류: {e}"}
# ─────────────────────────────────────────────────────────

async def telegram_alert_loop():
    """서버 CPU/RAM 사용량 정밀 감시 및 지능형 알림/자동 최적화 데몬
    - 0.001초 순간 스파이크(착시) 필터링 (최소 30초 이상 실제 초과 시에만 발송)
    - RAM 85% 초과 감지 시 자동으로 EmptyWorkingSet 최적화 1차 선제 실행
    - CPU와 RAM 알림을 명확히 분리하여 오해 방지
    """
    RAM_ALERT_THRESHOLD = 85.0   # RAM 경고 임계치 (%)
    CPU_ALERT_THRESHOLD = 85.0   # CPU 경고 임계치 (%)

    last_cpu_alert_time = 0
    last_ram_alert_time = 0
    consecutive_high_cpu = 0
    consecutive_high_ram = 0

    while True:
        try:
            # 1초 평균 CPU 측정 (interval=None의 찰나 스파이크 제거)
            cpu_usage = await asyncio.to_thread(psutil.cpu_percent, 1.0)
            ram_info = psutil.virtual_memory()
            ram_usage = ram_info.percent
            ram_used_gb = round(ram_info.used / (1024**3), 2)
            ram_total_gb = round(ram_info.total / (1024**3), 2)
            current_time = time.time()

            # 매 사이클 실측값 로깅 (이걸로 왜 알림이 왔는지 정확히 추적 가능)
            logger.info(f"[모니터] CPU: {cpu_usage}% | RAM: {ram_used_gb}GB/{ram_total_gb}GB ({ram_usage}%) | 연속고CPU: {consecutive_high_cpu} | 연속고RAM: {consecutive_high_ram}")

            # 1. CPU 고부하 감시 (임계치 이상이 3회 연속 = 30초 이상 지속될 때만)
            if cpu_usage >= CPU_ALERT_THRESHOLD:
                consecutive_high_cpu += 1
            else:
                consecutive_high_cpu = 0

            if consecutive_high_cpu >= 3:
                if current_time - last_cpu_alert_time > 600:  # 10분 쿨타임
                    msg = (
                        f"⚠️ [제우스 서버 경고 - CPU 지속 과부하]\n"
                        f"카운터 PC CPU가 30초 이상 고부하 상태입니다!\n\n"
                        f"💻 실측 CPU: {cpu_usage}% (지속)\n"
                        f"🧠 현재 RAM: {ram_used_gb}GB / {ram_total_gb}GB ({ram_usage}%)"
                    )
                    await send_telegram_msg(msg)
                    logger.warning(f"텔레그램 CPU 과부하 알림 발송: CPU {cpu_usage}%")
                    last_cpu_alert_time = current_time
                    consecutive_high_cpu = 0

            # 2. RAM 고부하 감시 (임계치 이상이 3회 연속 = 30초 이상 지속될 때만)
            if ram_usage >= RAM_ALERT_THRESHOLD:
                consecutive_high_ram += 1
            else:
                consecutive_high_ram = 0

            if consecutive_high_ram >= 3:
                # 임계치 초과 시 먼저 안전 메모리 트림(EmptyWorkingSet) 자동 실행 시도!
                logger.warning(f"🚨 RAM 사용량 {ram_usage}% 감지! 자동 메모리 비우기 선제 실행...")
                try:
                    await optimize_memory()
                    # 최적화 후 재측정
                    after_ram = psutil.virtual_memory().percent
                    logger.info(f"선제 메모리 최적화 완료: {ram_usage}% -> {after_ram}%")
                    if after_ram < 80.0:
                        # 최적화로 해결되었으면 사장님께 경고 문자 안 보내고 조용히 해결!
                        consecutive_high_ram = 0
                        await asyncio.sleep(10)
                        continue
                except Exception as opt_err:
                    logger.error(f"선제 최적화 실패: {opt_err}")

                if current_time - last_ram_alert_time > 600:  # 10분 쿨타임
                    msg = (
                        f"⚠️ [제우스 서버 경고 - RAM 부족 위험]\n"
                        f"카운터 PC 물리 메모리가 지속적으로 {RAM_ALERT_THRESHOLD}%를 초과했습니다!\n\n"
                        f"🧠 실제 사용 RAM: {ram_used_gb}GB / {ram_total_gb}GB ({ram_usage}%)\n"
                        f"💻 현재 CPU: {cpu_usage}%\n"
                        f"💡 서버가 유휴 메모리 자동 회수를 시도했습니다."
                    )
                    await send_telegram_msg(msg)
                    logger.warning(f"텔레그램 RAM 부족 알림 발송: RAM {ram_usage}%")
                    last_ram_alert_time = current_time
                    consecutive_high_ram = 0

        except Exception as e:
            logger.error(f"텔레그램 알림 루프 오류: {e}")
        await asyncio.sleep(10)

async def notify_tunnel_url_to_telegram():
    import requests
    logger.info("텔레그램 주소 알림 스레드 시작!")
    for i in range(15):
        await asyncio.sleep(2)
        info = tunnel_manager.get_info()
        logger.info(f"터널 상태 확인 중... [{i}/15] {info}")
        if info.get("status") == "ready" and info.get("public_url"):
            url = info["public_url"]
            msg = f"""📱 [제우스 모바일 관제소]
서버가 시작되었습니다! 외부 주소가 발급되었습니다.

👇 아래 링크를 눌러 모바일 대시보드에 바로 접속하세요:
{url}/mobile"""
            if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
                try:
                    r = requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", json={"chat_id": TELEGRAM_CHAT_ID, "text": msg}, timeout=5)
                    logger.info(f"텔레그램 발송 응답: {r.status_code}")
                except Exception as e:
                    logger.error(f"발송 실패: {e}")
            break


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server_core:app", host=SERVER_HOST, port=SERVER_PORT, reload=False)
@app.get("/api/pica/status")
async def get_pica_status():
    from server.pica_watchdog import pica_dog
    return {
        "is_enabled": pica_dog.is_enabled,
        "is_running": pica_dog.is_running,
        "process_running": pica_dog.is_process_running(),
        "program_path": pica_dog.program_path,
        "process_name": pica_dog.process_name,
        "watch_interval": pica_dog.watch_interval,
        "restart_delay": pica_dog.restart_delay,
        "auto_login_enabled": pica_dog.auto_login_enabled,
        "password_masked": "*" * len(pica_dog.password) if pica_dog.password else ""
    }

@app.post("/api/pica/settings")
async def save_pica_settings(request: Request):
    data = await request.json()
    cfg_file = os.path.join(PROJECT_ROOT, "deploy", "ClientDeploy", "core", "config.ini")
    main_cfg_file = r"C:\Users\USER\Documents\HDDGOD\deploy\ClientDeploy\core\config.ini"
    
    import configparser
    cfg = configparser.ConfigParser()
    target_read = cfg_file if os.path.exists(cfg_file) else main_cfg_file
    if os.path.exists(target_read):
        cfg.read(target_read, encoding="utf-8")
        
    if not cfg.has_section("PICA"):
        cfg.add_section("PICA")
        
    cfg.set("PICA", "ENABLED", str(data.get("is_enabled", False)))
    if "program_path" in data and data["program_path"]:
        cfg.set("PICA", "PATH", data["program_path"])
    if "process_name" in data and data["process_name"]:
        cfg.set("PICA", "PROCESS_NAME", data["process_name"])
    if "auto_login_enabled" in data:
        cfg.set("PICA", "AUTO_LOGIN", str(data["auto_login_enabled"]))
    if "password" in data and data["password"] and data["password"] != "***":
        cfg.set("PICA", "PASSWORD", data["password"])
        
    for cf in set([cfg_file, main_cfg_file]):
        try:
            os.makedirs(os.path.dirname(cf), exist_ok=True)
            with open(cf, "w", encoding="utf-8") as f:
                cfg.write(f)
        except Exception as e:
            logger.error(f"PICA config 저장 실패 ({cf}): {e}")
        
    from server.pica_watchdog import pica_dog
    pica_dog.load_config(cfg)
    
    if pica_dog.is_enabled:
        pica_dog.start()
    else:
        pica_dog.stop()
        
    return {"status": "ok"}


