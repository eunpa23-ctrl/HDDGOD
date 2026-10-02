# -*- coding: utf-8 -*-
r"""
제우스 HDD PROTECTOR - 24시간 하트비트 감시 및 비정상 꺼짐 자동 WOL 모듈
G:\내 드라이브\PROJECT\HDDGOD\server\wol_watchdog.py
"""
import time
import socket
import logging
import asyncio

try:
    from wakeonlan import send_magic_packet
    HAS_WOL_LIB = True
except ImportError:
    HAS_WOL_LIB = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("WOLWatchdog")

class WOLWatchdog:
    """3초 하트비트 생존 신호 감시 및 10초 비정상 꺼짐 시 자동 WOL 전원 켜기 관리자"""

    def __init__(self, timeout_sec: int = 10):
        self.timeout_sec = timeout_sec
        # client_id -> { "ip": ..., "mac": ..., "last_seen": ..., "is_normal_shutdown": False }
        self.clients = {}
        self.running = False

    @staticmethod
    def send_wol_packet(mac_addr: str) -> bool:
        """WOL 매직 패킷 브로드캐스트 발송"""
        if not mac_addr or mac_addr == "00:00:00:00:00:00":
            logger.warning("유효하지 않은 MAC 주소로 WOL 전송 취소")
            return False

        try:
            if HAS_WOL_LIB:
                send_magic_packet(mac_addr)
                logger.info(f"WOL 매직 패킷 발송 완료 (wakeonlan): {mac_addr}")
                return True
        except Exception:
            pass

        # 원시 소켓 소켓 대안 발송 (UDP 포트 9)
        try:
            clean_mac = mac_addr.replace(":", "").replace("-", "")
            data = bytes.fromhex("FFFFFFFFFFFF" + clean_mac * 16)
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.sendto(data, ("<broadcast>", 9))
            sock.close()
            logger.info(f"원시 UDP 소켓을 통한 WOL 매직 패킷 발송 완료: {mac_addr}")
            return True
        except Exception as e:
            logger.error(f"WOL 패킷 발송 실패: {e}")
            return False

    def update_heartbeat(self, client_id: str, ip: str, mac: str, uwf_status: str, netflix_status: str) -> None:
        """클라이언트로부터 수신된 생존 신호 기록"""
        self.clients[client_id] = {
            "client_id": client_id,
            "ip": ip,
            "mac": mac,
            "uwf_status": uwf_status,
            "netflix_status": netflix_status,
            "last_seen": time.time(),
            "status": "ONLINE",
            "is_normal_shutdown": False
        }

    def set_normal_shutdown(self, client_id: str) -> None:
        """관리자가 직접 종료한 경우 WOL 자동 켜기 방지 플래그 설정"""
        if client_id in self.clients:
            self.clients[client_id]["is_normal_shutdown"] = True
            self.clients[client_id]["status"] = "SHUTDOWN"

    async def run_watchdog_loop(self):
        """24시간 무중단 감시 루프: 10초 이상 신호 끊기면 자동 WOL 켜기"""
        self.running = True
        logger.info(f"24시간 비정상 꺼짐 감시 및 자동 WOL 데몬 가동 (감지 임계치: {self.timeout_sec}초)")

        while self.running:
            now = time.time()
            for cid, info in list(self.clients.items()):
                # 관리자가 직접 끈 게 아닌데 온라인 상태에서 타임아웃 초과
                elapsed = now - info.get("last_seen", 0)
                if not info.get("is_normal_shutdown") and elapsed > self.timeout_sec:
                    if info.get("status") != "ABNORMAL_SHUTDOWN":
                        info["status"] = "ABNORMAL_SHUTDOWN"
                        mac = info.get("mac")
                        logger.warning(f"🚨 [경고] {cid} 비정상 꺼짐 감지! (경과시간: {int(elapsed)}초) -> 자동 WOL 전원 켜기 실행!")
                        self.send_wol_packet(mac)

            await asyncio.sleep(2)

if __name__ == "__main__":
    dog = WOLWatchdog()
    print("WOL Watchdog 초기화 성공")
