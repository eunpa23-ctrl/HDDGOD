# -*- coding: utf-8 -*-
r"""
제우스 에이전트 - 작업표시줄 트레이 아이콘 및 관리자 인증 GUI
G:\내 드라이브\PROJECT\HDDGOD\client\client_tray.py
"""
import os
import sys
import logging
import threading
import tkinter as tk
from tkinter import simpledialog, messagebox
from PIL import Image, ImageDraw
try:
    import pystray
    import pystray._win32
except Exception:
    pystray = None
from common.config import ADMIN_PASSWORD

logger = logging.getLogger("ZeusTray")

class ClientTrayUI:
    """작업표시줄 트레이 아이콘 및 관리자 인증 관리자"""

    def __init__(self, on_reboot=None, on_restart_netflix=None):
        self.icon = None
        self.on_reboot = on_reboot or (lambda: os.system("shutdown /r /t 0 /f"))
        self.on_restart_netflix = on_restart_netflix

    def create_tray_image(self) -> Image.Image:
        """제우스 에이전트 트레이 아이콘 동적 생성 (에메랄드 번개 배지)"""
        width, height = 64, 64
        image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)

        # 둥근 원형 배경 (에메랄드 그린)
        draw.ellipse([4, 4, 60, 60], fill=(16, 185, 129, 255), outline=(255, 255, 255, 255), width=3)

        # 제우스 번개 모양 (화이트)
        bolt_pts = [
            (36, 10),
            (20, 32),
            (32, 32),
            (26, 54),
            (46, 26),
            (34, 26)
        ]
        draw.polygon(bolt_pts, fill=(255, 255, 255, 255))
        return image

    def prompt_admin_auth(self) -> bool:
        """손님 조작 방지 관리자 비밀번호 팝업 창 (마스터 PW: 1234)"""
        root = tk.Tk()
        root.attributes("-topmost", True)
        sw = root.winfo_screenwidth()
        sh = root.winfo_screenheight()
        root.geometry(f"0x0+{sw // 2}+{sh // 2}")
        root.lift()
        root.focus_force()
        root.update()

        pwd = simpledialog.askstring(
            "제우스 관리자 인증",
            "관리자 마스터 비밀번호를 입력하세요:",
            show="*",
            parent=root
        )
        root.destroy()

        if pwd == ADMIN_PASSWORD:
            return True
        elif pwd is not None:
            messagebox.showerror("인증 실패", "마스터 비밀번호가 일치하지 않습니다.")
        return False

    def handle_reboot_click(self) -> None:
        """관리자 인증 후 PC 재부팅"""
        if self.prompt_admin_auth():
            if messagebox.askyesno("PC 재부팅", "컴퓨터를 다시 시작(재부팅)하시겠습니까?"):
                self.on_reboot()

    def handle_netflix_click(self) -> None:
        """관리자 인증 후 넷플릭스 다시 실행"""
        if self.prompt_admin_auth() and self.on_restart_netflix:
            self.on_restart_netflix()

    def handle_open_deploy_folder(self) -> None:
        """설치/배포 폴더(네트워크 공유 또는 로컬 설치 폴더) 탐색기 열기"""
        share_path = r"\\192.168.0.100\HDDGOD\deploy\ClientDeploy"
        local_path = r"C:\ZeusAgent"
        target = share_path if os.path.exists(share_path) else local_path
        try:
            os.system(f'start "" explorer.exe "{target}"')
        except Exception:
            pass

    def handle_open_dashboard(self) -> None:
        """카운터 관제 대시보드 브라우저 열기"""
        import webbrowser
        try:
            webbrowser.open("http://192.168.0.100:8000")
        except Exception:
            pass

    def handle_exit_click(self) -> None:
        """관리자 인증 후 클라이언트 프로그램 완전 종료"""
        if self.prompt_admin_auth():
            if messagebox.askyesno("프로그램 종료", "제우스 에이전트를 종료하시겠습니까?\n\n(종료 후에는 원격 제어 및 관제 서비스가 중단됩니다)"):
                if self.icon:
                    self.icon.stop()
                os._exit(0)

    def get_version(self) -> str:
        """현재 클라이언트 버전 읽어오기"""
        if getattr(sys, "frozen", False):
            app_dir = os.path.dirname(os.path.abspath(sys.executable))
        else:
            app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        ver_path1 = os.path.join(app_dir, "core", "version.txt")
        ver_path2 = os.path.join(app_dir, "version.txt")
        
        for path in [ver_path1, ver_path2]:
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        return f.read().strip().replace('"', '').replace("'", "").replace('\ufeff', '').strip()
                except Exception:
                    pass
        return "Unknown"

    def build_menu(self):
        """우클릭 트레이 메뉴 생성"""
        version = self.get_version()
        items = [
            pystray.MenuItem(f"제우스 에이전트 (v{version})", lambda: None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("🔄 [PC 재부팅] 컴퓨터 다시 시작", lambda: self.handle_reboot_click()),
            pystray.MenuItem("🎬 [넷플릭스] 다시 실행", lambda: self.handle_netflix_click()),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("📁 [설치/배포 폴더 열기]", lambda: self.handle_open_deploy_folder()),
            pystray.MenuItem("🌐 [관제 대시보드 열기]", lambda: self.handle_open_dashboard()),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("❌ 프로그램 종료", lambda: self.handle_exit_click()),
        ]
        return pystray.Menu(*items)

    def run_tray(self) -> None:
        """트레이 아이콘 백그라운드 구동"""
        if not pystray:
            logger.error("pystray 라이브러리가 로드되지 않아 트레이 아이콘을 시작할 수 없습니다.")
            return
        try:
            image = self.create_tray_image()
            menu = self.build_menu()
            version = self.get_version()
            title = f"제우스 에이전트 (v{version})"

            self.icon = pystray.Icon("ZeusAgent", image, title, menu)
            self.icon.run()
        except Exception as e:
            logger.error(f"트레이 아이콘 실행 실패: {e}")

if __name__ == "__main__":
    tray = ClientTrayUI()
    tray.run_tray()
