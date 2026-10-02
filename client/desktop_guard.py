# -*- coding: utf-8 -*-
r"""
제우스 HDD PROTECTOR - 바탕화면 아이콘 자동 설치 & 배경화면 영구 유지 관리자
G:\내 드라이브\PROJECT\HDDGOD\client\desktop_guard.py
"""
import os
import sys
import time
import shutil
import ctypes
import logging
import threading

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DesktopGuard")

class DesktopGuard:
    r"""
    1. 아이콘 마스터 폴더(C:\ZeusAgent\DesktopIcons)의 아이콘들을 부팅 시 바탕화면에 자동 설치/동기화
    2. 바탕화면 배경화면(Wallpaper) 변경 시 자동 감지하여 백업하고, 재부팅 시에도 영구 유지
    """
    ICON_SOURCE_DIR = r"C:\ZeusAgent\DesktopIcons"
    WALLPAPER_BACKUP = r"C:\ZeusAgent\saved_wallpaper.jpg"

    @classmethod
    def get_public_desktop(cls) -> str:
        return os.path.join(os.environ.get("PUBLIC", r"C:\Users\Public"), "Desktop")

    @classmethod
    def get_user_desktop(cls) -> str:
        return os.path.join(os.environ.get("USERPROFILE", ""), "Desktop")

    @classmethod
    def ensure_directories(cls) -> None:
        """아이콘 보관 폴더 및 ZeusAgent 기본 디렉터리 보장"""
        if not os.path.exists(cls.ICON_SOURCE_DIR):
            try:
                os.makedirs(cls.ICON_SOURCE_DIR, exist_ok=True)
                logger.info(f"아이콘 마스터 폴더 생성 완료: {cls.ICON_SOURCE_DIR}")
            except Exception as e:
                logger.warning(f"아이콘 폴더 생성 실패: {e}")

    @classmethod
    def sync_desktop_icons(cls) -> None:
        r"""
        부팅 시 실행: 서버(master_icons)의 아이콘 목록을 조회하여
        바탕화면으로 다운로드/설치 (손님이 지워도 100% 원상복구)
        """
        # 1. 넷플릭스 바로가기는 클라이언트에서 직접 바탕화면에 생성 보장
        try:
            from client.netflix_bot import NetflixBot
            bot = NetflixBot()
            bot.ensure_desktop_shortcut()
        except Exception as e:
            logger.warning(f"넷플릭스 바로가기 생성 실패: {e}")

        # 2. 서버에서 마스터 아이콘 다운로드
        target_desktops = [cls.get_public_desktop()]
        u_desktop = cls.get_user_desktop()
        if os.path.exists(u_desktop) and u_desktop not in target_desktops:
            target_desktops.append(u_desktop)

        from common.config import CLIENT_SERVER_IP, CLIENT_SERVER_PORT
        import urllib.request
        import urllib.parse
        import json
        
        url_list = f"http://{CLIENT_SERVER_IP}:{CLIENT_SERVER_PORT}/api/icons/list"
        try:
            req = urllib.request.Request(url_list)
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode('utf-8'))
                icons = data.get("icons", [])
        except Exception as e:
            logger.warning(f"서버 아이콘 목록 조회 실패 (오프라인): {e}")
            return

        logger.info(f"서버 마스터 아이콘 보관소에서 {len(icons)}개 항목 감지 -> 바탕화면 다운로드 시작")

        for item in icons:
            download_url = f"http://{CLIENT_SERVER_IP}:{CLIENT_SERVER_PORT}/icons/{urllib.parse.quote(item)}"
            for t_dir in target_desktops:
                if not os.path.exists(t_dir):
                    continue
                dst_path = os.path.join(t_dir, item)
                try:
                    urllib.request.urlretrieve(download_url, dst_path)
                    logger.debug(f"서버 아이콘 다운로드 완료: {item} -> {t_dir}")
                except Exception as e:
                    logger.warning(f"서버 아이콘 다운로드 실패 ({item}): {e}")

        logger.info("🎉 서버 동기화 기반 바탕화면 필수 아이콘 설치 완료!")

    @classmethod
    def save_current_wallpaper(cls) -> bool:
        r"""현재 윈도우 배경화면 이미지를 C:\ZeusAgent\saved_wallpaper.jpg 로 영구 백업"""
        try:
            transcoded = os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Themes\TranscodedWallpaper")
            if os.path.exists(transcoded) and os.path.getsize(transcoded) > 0:
                os.makedirs(os.path.dirname(cls.WALLPAPER_BACKUP), exist_ok=True)
                shutil.copy2(transcoded, cls.WALLPAPER_BACKUP)
                logger.info(f"현재 배경화면 영구 백업 완료: {cls.WALLPAPER_BACKUP}")
                return True
        except Exception as e:
            logger.debug(f"배경화면 백업 실패: {e}")
        return False

    @classmethod
    def restore_saved_wallpaper(cls) -> bool:
        """부팅 시 실행: 백업된 배경화면을 즉시 윈도우 바탕화면으로 재적용 (순간복구 롤백 차단)"""
        if not os.path.exists(cls.WALLPAPER_BACKUP):
            return False

        try:
            SPI_SETDESKWALLPAPER = 20
            SPIF_UPDATEINIFILE = 0x01
            SPIF_SENDCHANGE = 0x02

            # Win32 API 호출로 바탕화면 즉시 갱신
            ret = ctypes.windll.user32.SystemParametersInfoW(
                SPI_SETDESKWALLPAPER,
                0,
                cls.WALLPAPER_BACKUP,
                SPIF_UPDATEINIFILE | SPIF_SENDCHANGE
            )
            if ret:
                logger.info("🎨 저장된 사용자 배경화면 재적용 완료 (재부팅 유지 성공)")
                return True
        except Exception as e:
            logger.warning(f"배경화면 복원 실패: {e}")
        return False

    @classmethod
    def start_wallpaper_watcher(cls) -> None:
        """배경화면 변경 실시간 감시 스레드 (손님/점주가 배경을 바꾸면 즉시 자동 백업)"""
        def watcher_loop():
            last_mtime = 0
            transcoded = os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Themes\TranscodedWallpaper")
            while True:
                try:
                    if os.path.exists(transcoded):
                        mtime = os.path.getmtime(transcoded)
                        if mtime != last_mtime:
                            last_mtime = mtime
                            # 배경화면이 변경되었으면 즉시 백업
                            time.sleep(1)  # 쓰기 완료 대기
                            cls.save_current_wallpaper()
                except Exception:
                    pass
                time.sleep(5)

        t = threading.Thread(target=watcher_loop, daemon=True)
        t.start()

if __name__ == "__main__":
    DesktopGuard.sync_desktop_icons()
    DesktopGuard.save_current_wallpaper()
    DesktopGuard.restore_saved_wallpaper()
