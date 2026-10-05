# -*- coding: utf-8 -*-
r"""
제우스 HDD PROTECTOR - 중앙 관제 서버 시스템 트레이(Tray) 아이콘 UI
- 윈도우 작업표시줄 시계 옆 트레이에 번개 아이콘 표시
- 우클릭 메뉴: 대시보드 열기, 모바일 접속 주소 복사, 메모리 최적화, 서버 종료
"""
import os
import sys
import time
import logging
import threading
import webbrowser
from PIL import Image

try:
    import pystray
    import pystray._win32
except Exception:
    pystray = None

logger = logging.getLogger("ZeusServer")

class ServerTrayUI:
    def __init__(self, port: int = 8000):
        self.port = port
        self.icon = None
        self.dashboard_url = f"http://127.0.0.1:{port}"

    def get_icon_image(self) -> Image.Image:
        """서버 아이콘 이미지 로드 (없으면 동적 생성)"""
        icon_path = None
        # PyInstaller frozen 환경
        if getattr(sys, 'frozen', False):
            base_dir = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
            candidates = [
                os.path.join(base_dir, 'server', 'static', 'server.ico'),
                os.path.join(base_dir, 'static', 'server.ico'),
            ]
            for c in candidates:
                if os.path.exists(c):
                    icon_path = c
                    break

        if not icon_path:
            # 일반 개발 환경
            script_dir = os.path.dirname(os.path.abspath(__file__))
            candidates = [
                os.path.join(script_dir, 'static', 'server.ico'),
                os.path.join(os.path.dirname(script_dir), 'server', 'static', 'server.ico'),
                r"C:\Users\USER\Documents\HDDGOD\server\static\server.ico"
            ]
            for c in candidates:
                if os.path.exists(c):
                    icon_path = c
                    break

        if icon_path and os.path.exists(icon_path):
            try:
                return Image.open(icon_path)
            except Exception as e:
                logger.warning(f"아이콘 로드 실패, 동적 생성으로 대체: {e}")

        # 백업: 동적 원형 번개 아이콘 생성
        from PIL import ImageDraw
        img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        # 둥근 파란 배경
        draw.ellipse([2, 2, 62, 62], fill=(14, 165, 233, 255), outline=(255, 255, 255, 255), width=2)
        # 노란 번개
        pts = [(34, 10), (18, 34), (32, 34), (28, 54), (46, 28), (32, 28)]
        draw.polygon(pts, fill=(250, 204, 21, 255))
        return img

    def open_dashboard(self):
        """웹 대시보드 브라우저 열기"""
        try:
            webbrowser.open(self.dashboard_url)
        except Exception as e:
            logger.error(f"대시보드 열기 실패: {e}")

    def copy_mobile_url(self):
        """클라우드플레어 모바일 주소 클립보드 복사"""
        try:
            from server.tunnel_manager import tunnel_manager
            info = tunnel_manager.get_info()
            pub_url = info.get("public_url")
            target = f"{pub_url}/mobile" if pub_url else self.dashboard_url
            
            import tkinter as tk
            r = tk.Tk()
            r.withdraw()
            r.clipboard_clear()
            r.clipboard_append(target)
            r.update()
            r.destroy()
            logger.info(f"모바일 주소 복사 완료: {target}")
            if self.icon:
                self.icon.notify(f"주소가 복사되었습니다:\n{target}", "제우스 관제 센터")
        except Exception as e:
            logger.error(f"모바일 주소 복사 실패: {e}")

    def trigger_memory_optimization(self):
        """트레이에서 즉시 메모리 최적화 실행"""
        try:
            import ctypes, gc
            gc.collect()
            # 서버 자체 메모리 반환
            ctypes.windll.kernel32.SetProcessWorkingSetSize(ctypes.windll.kernel32.GetCurrentProcess(), -1, -1)
            
            # 전체 프로세스 유휴 메모리 트림
            import psutil
            trimmed = 0
            for p in psutil.process_iter(['pid', 'name']):
                try:
                    h = ctypes.windll.kernel32.OpenProcess(0x001F0FFF, False, p.pid)
                    if h:
                        ctypes.windll.psapi.EmptyWorkingSet(h)
                        ctypes.windll.kernel32.CloseHandle(h)
                        trimmed += 1
                except Exception:
                    pass
            
            mem = psutil.virtual_memory()
            if self.icon:
                self.icon.notify(f"메모리 청소 완료!\n• 정리된 프로세스: {trimmed}개\n• 현재 RAM: {mem.percent}% (여유: {mem.available / (1024**3):.1f} GB)", "제우스 메모리 최적화")
        except Exception as e:
            logger.error(f"메모리 최적화 실패: {e}")

    def exit_server(self):
        """관제 서버 안전 종료"""
        logger.info("트레이 메뉴를 통한 관제 서버 종료 요청 수신")
        if self.icon:
            self.icon.stop()
        os._exit(0)

    def build_menu(self):
        """트레이 우클릭 컨텍스트 메뉴 생성"""
        return pystray.Menu(
            pystray.MenuItem("⚡ 제우스 관제 센터 (정상 가동 중)", lambda: None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("🌐 관제 대시보드 열기", lambda: self.open_dashboard(), default=True),
            pystray.MenuItem("📱 스마트폰 접속 주소 복사", lambda: self.copy_mobile_url()),
            pystray.MenuItem("🧹 즉시 메모리 최적화", lambda: self.trigger_memory_optimization()),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("❌ 관제 서버 종료", lambda: self.exit_server())
        )

    def run_tray(self):
        """트레이 아이콘 루프 실행 (별도 데몬 스레드에서 호출)"""
        if not pystray:
            logger.warning("pystray 모듈이 없어 트레이 아이콘을 띄우지 못했습니다.")
            return

        try:
            image = self.get_icon_image()
            menu = self.build_menu()
            self.icon = pystray.Icon(
                "ZeusServer",
                image,
                "⚡ 제우스 HDD PROTECTOR - 관제 서버",
                menu
            )
            self.icon.run()
        except Exception as e:
            logger.error(f"서버 트레이 아이콘 실행 오류: {e}")

server_tray = ServerTrayUI()

def start_server_tray_thread(port: int = 8000):
    """서버 가동 시 트레이 아이콘 백그라운드 시작"""
    server_tray.port = port
    server_tray.dashboard_url = f"http://127.0.0.1:{port}"
    t = threading.Thread(target=server_tray.run_tray, daemon=True, name="ZeusServerTrayThread")
    t.start()
    return t
