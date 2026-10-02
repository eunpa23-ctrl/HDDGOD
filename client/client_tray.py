# -*- coding: utf-8 -*-
r"""
제우스 HDD PROTECTOR - 트레이 방패 아이콘 및 비밀번호 인증 GUI
G:\내 드라이브\PROJECT\HDDGOD\client\client_tray.py
"""
import time
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
from client.uwf_controller import UWFController
from common.protocol import UWFStatus

class ClientTrayUI:
    """작업표시줄 트레이 아이콘 및 관리자 인증 창 관리자"""

    def __init__(self, on_reboot_restore=None, on_reboot_maintenance=None, on_reboot_protect=None, on_restart_netflix=None):
        self.icon = None
        self.on_reboot_restore = on_reboot_restore or UWFController.reboot_restore
        self.on_reboot_maintenance = on_reboot_maintenance or UWFController.reboot_to_maintenance
        self.on_reboot_protect = on_reboot_protect or UWFController.reboot_and_protect
        self.on_restart_netflix = on_restart_netflix

    def create_shield_image(self, is_protected: bool = True) -> Image.Image:
        """초록 방패(보호 중) 또는 주황 방패(유지보수 모드) 아이콘 동적 생성"""
        width, height = 64, 64
        image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        # 방패 색상: 초록색(보호) / 주황색(유지보수)
        fill_color = (46, 204, 113, 255) if is_protected else (230, 126, 34, 255)
        outline_color = (255, 255, 255, 255)

        # 방패 모양 그리기
        shield_pts = [
            (32, 4),
            (56, 16),
            (52, 44),
            (32, 60),
            (12, 44),
            (8, 16)
        ]
        draw.polygon(shield_pts, fill=fill_color, outline=outline_color)
        return image

    def prompt_admin_auth(self) -> bool:
        """손님 조작 방지 관리자 비밀번호 팝업 창 (마스터 PW: 1234)"""
        root = tk.Tk()
        root.attributes("-topmost", True)
        # 화면 중앙 계산 후 그 위치에 0픽셀 창 배치 → 자식 다이얼로그가 중앙에 뜸
        sw = root.winfo_screenwidth()
        sh = root.winfo_screenheight()
        root.geometry(f"0x0+{sw // 2}+{sh // 2}")
        root.lift()
        root.focus_force()
        root.update()

        pwd = simpledialog.askstring(
            "제우스 HDD PROTECTOR 관리자 인증",
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

    def handle_maintenance_click(self) -> None:
        if self.prompt_admin_auth():
            if messagebox.askyesno("유지보수 모드 전환", "순간복구를 끄고 유지보수 모드로 재부팅하시겠습니까?\n\n(재부팅 후 새 프로그램 설치 및 패치가 영구 저장됩니다)"):
                self.on_reboot_maintenance()

    def handle_protect_click(self) -> None:
        if self.prompt_admin_auth():
            if messagebox.askyesno("세팅저장 및 보호", "현재 PC 상태를 새로운 '기본 상태(디폴트)'로 저장하고\n순간복구 보호 모드로 재부팅하시겠습니까?\n\n(재부팅 후 지금 상태가 영구 고정되어 1초 복구 기준점이 됩니다)"):
                self.on_reboot_protect()

    def handle_restore_click(self) -> None:
        if self.prompt_admin_auth():
            if messagebox.askyesno("1초 복구 재부팅", "현재 PC의 모든 변경사항을 버리고\n기본 상태로 깨끗하게 초기화 재부팅하시겠습니까?"):
                self.on_reboot_restore()

    def handle_netflix_click(self) -> None:
        if self.prompt_admin_auth() and self.on_restart_netflix:
            self.on_restart_netflix()

    def handle_exit_click(self) -> None:
        """관리자 인증 후 클라이언트 프로그램 완전 종료"""
        if self.prompt_admin_auth():
            if messagebox.askyesno("프로그램 종료", "제우스 에이전트를 종료하시겠습니까?\n\n(종료 후에는 원격 제어 및 자동 복구가 비활성화됩니다)"):
                if self.icon:
                    self.icon.stop()
                import os
                os._exit(0)

    def get_version(self) -> str:
        """현재 클라이언트 버전 읽어오기"""
        import sys
        import os
        if getattr(sys, "frozen", False):
            app_dir = os.path.dirname(os.path.abspath(sys.executable))
        else:
            app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # 개발 환경 대비 core 경로 우선 탐색
        ver_path1 = os.path.join(app_dir, "core", "version.txt")
        ver_path2 = os.path.join(app_dir, "version.txt")
        
        for path in [ver_path1, ver_path2]:
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        return f.read().strip().replace('"', '').replace("'", "").replace('\ufeff', '').strip()
                except:
                    pass
        return "Unknown"

    def build_menu(self, is_protected: bool):
        """현재 보호/유지보수 상태에 맞춘 맞춤형 우클릭 트레이 메뉴 생성"""
        version = self.get_version()
        items = [
            pystray.MenuItem(f"🛡️ 제우스 HDD PROTECTOR (v{version})", lambda: None, enabled=False),
            pystray.Menu.SEPARATOR,
        ]
        if is_protected:
            items.append(pystray.MenuItem("🔧 [유지보수 모드] 보호 해제 후 재부팅", lambda: self.handle_maintenance_click()))
        else:
            items.append(pystray.MenuItem("💾 [세팅저장&보호] 현재상태 저장 후 보호 재부팅", lambda: self.handle_protect_click()))

        items.extend([
            pystray.MenuItem("⚡ [1초 복구] 즉시 재부팅 복구", lambda: self.handle_restore_click()),
            pystray.MenuItem("🎬 [넷플릭스] 다시 실행", lambda: self.handle_netflix_click()),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("🔒 상태: " + ("보호 중 (초록 방패)" if is_protected else "유지보수 모드 (주황 방패)"), lambda: None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("❌ 프로그램 종료", lambda: self.handle_exit_click()),
        ])
        return pystray.Menu(*items)

    def _dynamic_status_watcher(self) -> None:
        """서버 명령 또는 로컬 변경으로 UWF 상태가 바뀔 때 트레이 아이콘 및 메뉴 실시간 갱신"""
        last_state = None
        while True:
            time.sleep(2)
            if self.icon:
                st = UWFController.get_status()
                if st != last_state:
                    last_state = st
                    is_prot = (st == UWFStatus.PROTECTED)
                    try:
                        version = self.get_version()
                        self.icon.icon = self.create_shield_image(is_prot)
                        self.icon.title = f"제우스 (v{version}) - {'🛡️ 보호 중 (초록)' if is_prot else '🔧 유지보수 (주황)'}"
                        self.icon.menu = self.build_menu(is_prot)
                    except Exception:
                        pass

    def run_tray(self) -> None:
        """트레이 아이콘 백그라운드 구동"""
        if not pystray:
            logger.error("pystray 라이브러리가 로드되지 않아 트레이 아이콘을 시작할 수 없습니다.")
            return
        try:
            status = UWFController.get_status()
            is_protected = (status == UWFStatus.PROTECTED)
            image = self.create_shield_image(is_protected)
            menu = self.build_menu(is_protected)
            version = self.get_version()
            title = f"제우스 HDD PROTECTOR (v{version}) - 보호 중" if is_protected else f"제우스 HDD PROTECTOR (v{version}) - 유지보수"

            self.icon = pystray.Icon("ZeusProtector", image, title, menu)
            # 트레이 상태 동적 갱신 데몬 시작
            threading.Thread(target=self._dynamic_status_watcher, daemon=True).start()
            self.icon.run()
        except Exception as e:
            logger.error(f"트레이 아이콘 실행 실패: {e}")

if __name__ == "__main__":
    tray = ClientTrayUI()
    tray.run_tray()
