# -*- coding: utf-8 -*-
r"""
제우스 HDD PROTECTOR - Cloudflare 원격 터널 관리자
G:\내 드라이브\PROJECT\HDDGOD\server\tunnel_manager.py

매장 외부나 스마트폰(LTE/5G)에서 포트포워딩이나 복잡한 공유기 설정 없이
원클릭/QR코드로 제우스 대시보드에 실시간 접속할 수 있도록 지원합니다.
"""
import os
import re
import socket
import logging
import asyncio
import subprocess
from typing import Optional, Dict

logger = logging.getLogger("ZeusTunnel")

class TunnelManager:
    def __init__(self, port: int = 8000):
        self.port = port
        self.public_url: Optional[str] = None
        self.status: str = "stopped"  # stopped, starting, ready, error
        self.process: Optional[asyncio.subprocess.Process] = None
        self._task: Optional[asyncio.Task] = None

        # tools/cloudflared.exe 경로 탐색
        base_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(base_dir)
        self.bin_path = os.path.join(project_root, "tools", "cloudflared.exe")

    @staticmethod
    def get_local_ip() -> str:
        """매장 내부망(Wi-Fi) 접속용 로컬 IP 확인"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    async def start(self):
        """Cloudflare 터널 백그라운드 구동"""
        if not os.path.exists(self.bin_path):
            logger.warning(f"cloudflared.exe 실행 파일을 찾을 수 없습니다: {self.bin_path}")
            self.status = "error"
            return

        self.status = "starting"
        self.public_url = None
        cmd = [self.bin_path, "tunnel", "--url", f"http://127.0.0.1:{self.port}"]

        import atexit
        atexit.register(self.stop)

        try:
            # 혹시 남아있을 수 있는 이전 cloudflared 프로세스 정리
            if os.name == "nt":
                subprocess.run(["taskkill", "/F", "/IM", "cloudflared.exe"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

        try:
            logger.info(f"🌐 Cloudflare 스마트폰 원격 터널 가동 시작 (포트: {self.port})...")
            # Windows에서 콘솔 창 숨김 플래그
            creationflags = 0
            if os.name == "nt":
                creationflags = subprocess.CREATE_NO_WINDOW

            self.process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                creationflags=creationflags
            )

            # stderr 스트림 비동기 모니터링 (cloudflared는 로그를 stderr로 출력)
            asyncio.create_task(self._read_stream(self.process.stderr))
            asyncio.create_task(self._read_stream(self.process.stdout))

        except Exception as e:
            logger.error(f"Cloudflare 터널 프로세스 실행 실패: {e}")
            self.status = "error"

    async def _read_stream(self, stream):
        if not stream:
            return
        
        url_pattern = re.compile(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com")

        while True:
            line = await stream.readline()
            if not line:
                break
            text = line.decode("utf-8", errors="ignore").strip()
            if not text:
                continue

            match = url_pattern.search(text)
            if match and not self.public_url:
                self.public_url = match.group(0)
                self.status = "ready"
                logger.info(f"🎉 [스마트폰 원격 접속 URL 생성 성공]: {self.public_url}")
                logger.info(f"📱 스마트폰 카메라로 QR 코드를 스캔하여 매장 밖에서도 즉시 접속 가능합니다.")

        # 스트림 종료 = 터널 프로세스 비정상 종료 → 자동 재시작
        if self.status != "stopped":
            logger.warning("⚠️ Cloudflare 터널 연결이 끊어졌습니다. 10초 후 자동 재시작합니다...")
            self.status = "stopped"
            self.public_url = None
            self.process = None
            await asyncio.sleep(10)
            logger.info("🔄 Cloudflare 터널 자동 재시작 중...")
            await self.start()

    def stop(self):
        """서버 종료 시 터널 프로세스 안전 종료"""
        if self.process:
            try:
                self.process.terminate()
                logger.info("Cloudflare 원격 터널 프로세스가 정상 종료되었습니다.")
            except Exception as e:
                logger.warning(f"터널 프로세스 종료 중 예외: {e}")
            self.process = None

        if os.name == "nt":
            try:
                subprocess.run(["taskkill", "/F", "/IM", "cloudflared.exe"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass

        self.status = "stopped"
        self.public_url = None

    def get_info(self) -> Dict:
        """대시보드 프론트엔드 연동용 네트워크 정보 반환"""
        local_ip = self.get_local_ip()
        return {
            "status": self.status,
            "public_url": self.public_url,
            "lan_url": f"http://{local_ip}:{self.port}",
            "local_ip": local_ip,
            "port": self.port
        }

# 싱글톤 인스턴스
tunnel_manager = TunnelManager()
