import os
import time
import shutil
import ctypes
import logging

logger = logging.getLogger(__name__)

class DesktopGuard:
    def __init__(self):
        self.base_dir = r"C:\ZeusAgent"
        self.wallpaper_backup = os.path.join(self.base_dir, "saved_wallpaper.jpg")
        
    def get_current_wallpaper(self) -> str:
        """현재 윈도우 배경화면 경로 가져오기"""
        ubuf = ctypes.create_unicode_buffer(512)
        # SPI_GETDESKWALLPAPER = 0x0073 (115)
        ctypes.windll.user32.SystemParametersInfoW(115, len(ubuf), ubuf, 0)
        return ubuf.value

    def set_wallpaper(self, path: str):
        """배경화면 강제 설정"""
        # SPI_SETDESKWALLPAPER = 20
        # SPIF_UPDATEINIFILE = 1, SPIF_SENDWININICHANGE = 2 => 3
        ctypes.windll.user32.SystemParametersInfoW(20, 0, path, 3)

    def restore_wallpaper(self):
        """백업된 배경화면이 있으면 부팅 시 즉시 적용"""
        if os.path.exists(self.wallpaper_backup):
            current = self.get_current_wallpaper()
            if current != self.wallpaper_backup:
                self.set_wallpaper(self.wallpaper_backup)
                logger.info("🛡️ [DesktopGuard] 바탕화면 배경화면 영구 복구 완료!")

    def monitor_wallpaper_loop(self):
        """배경화면 변경 감지 루프 (데몬 스레드용)"""
        last_wallpaper = self.get_current_wallpaper()
        while True:
            time.sleep(5)
            try:
                current = self.get_current_wallpaper()
                if current and current != last_wallpaper and current != self.wallpaper_backup:
                    # 배경화면이 바뀌었다면 즉시 백업
                    if os.path.exists(current):
                        shutil.copy2(current, self.wallpaper_backup)
                        last_wallpaper = current
                        logger.info(f"🛡️ [DesktopGuard] 새로운 배경화면 감지 및 영구 보존 백업 완료: {current}")
            except Exception:
                pass
