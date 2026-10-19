import os
import asyncio
import psutil
import subprocess
import logging
import time
import ctypes
from ctypes import wintypes
from typing import Optional, List

import win32gui
import win32con
import win32process
import pyautogui
import pyperclip

logger = logging.getLogger("ZeusServer")
user32 = ctypes.windll.user32
WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)


def ensure_desktop():
    """현재 스레드를 Default 윈도우 데스크톱에 연결"""
    try:
        hdesk = user32.OpenDesktopW('Default', 0, False, 0x01FF)
        if hdesk:
            user32.SetThreadDesktop(hdesk)
    except Exception as e:
        logger.warning(f"SetThreadDesktop 예외: {e}")


class PicaWatchdog:
    def __init__(self, telegram_callback=None):
        self.program_path = r"C:\Program Files (x86)\PicaLive\LiveStarter.exe"
        self.process_name = "PicaLive.exe"
        self.watch_interval = 5
        self.restart_delay = 5
        self.auto_login_enabled = True
        self.password = "@Oep0325"
        self.is_enabled = True
        self.is_running = False
        self.telegram_callback = telegram_callback
        self.task: Optional[asyncio.Task] = None
        
        # 상태 모니터링 필드
        self.recovery_count = 0
        self.last_check_time = 0.0
        self.last_status_msg = "초기화 대기 중"
        self.is_recovering = False

    def load_config(self, cfg):
        if cfg.has_section("PICA"):
            self.is_enabled = cfg.getboolean("PICA", "ENABLED", fallback=True)
            self.program_path = cfg.get("PICA", "PATH", fallback=r"C:\Program Files (x86)\PicaLive\LiveStarter.exe")
            self.process_name = cfg.get("PICA", "PROCESS_NAME", fallback="PicaLive.exe")
            self.auto_login_enabled = cfg.getboolean("PICA", "AUTO_LOGIN", fallback=True)
            saved_pwd = cfg.get("PICA", "PASSWORD", fallback="")
            if saved_pwd and saved_pwd != "testpassword":
                self.password = saved_pwd
            else:
                self.password = "@Oep0325"

    def get_picalive_pids(self) -> List[int]:
        """실행 중인 PicaLive.exe 프로세스 PID 목록 반환"""
        pids = []
        try:
            for proc in psutil.process_iter(['name', 'pid']):
                pname = proc.info['name']
                if pname and pname.lower() == "picalive.exe":
                    pids.append(proc.info['pid'])
        except Exception:
            pass
        return pids

    def is_process_running(self) -> bool:
        """PicaLive 메인 프로세스가 살아있는지 검사"""
        return len(self.get_picalive_pids()) > 0

    def get_main_window_hwnd(self) -> Optional[int]:
        """PicaLive 정상 영업 메인 화면(카운터 그리드) HWND 반환 (w > 800 and h > 600)"""
        ensure_desktop()
        pids = self.get_picalive_pids()
        if not pids:
            return None

        found_hwnd = None
        def enum(h, _):
            nonlocal found_hwnd
            pid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(h, ctypes.byref(pid))
            if pid.value in pids and user32.IsWindowVisible(h):
                r = wintypes.RECT()
                user32.GetWindowRect(h, ctypes.byref(r))
                w = r.right - r.left
                hh = r.bottom - r.top
                # 메인 카운터 창은 해상도 대부분을 차지함 (1920x1080 기준 1900+ x 1000+)
                if w > 800 and hh > 600:
                    found_hwnd = h
                    return False
            return True

        user32.EnumWindows(WNDENUMPROC(enum), 0)
        return found_hwnd

    def get_login_window_hwnd(self) -> Optional[int]:
        """PicaLive 로그인 또는 확인 대화상자 HWND 반환"""
        ensure_desktop()
        pids = self.get_picalive_pids()
        if not pids:
            return None

        found_hwnd = None
        def enum(h, _):
            nonlocal found_hwnd
            pid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(h, ctypes.byref(pid))
            if pid.value in pids and user32.IsWindowVisible(h):
                r = wintypes.RECT()
                user32.GetWindowRect(h, ctypes.byref(r))
                w = r.right - r.left
                hh = r.bottom - r.top
                # 로그인 창은 보통 크기가 200~700 사이의 다이얼로그임
                if 100 < w <= 800 and 50 < hh <= 600:
                    found_hwnd = h
                    return False
            return True

        user32.EnumWindows(WNDENUMPROC(enum), 0)
        return found_hwnd

    async def send_alert(self, msg: str):
        """텔레그램 알림 전송 (콜백 우선, 실패 시 직접 발송)"""
        sent = False
        if self.telegram_callback:
            try:
                res = self.telegram_callback(msg)
                if asyncio.iscoroutine(res):
                    await res
                sent = True
            except Exception as e:
                logger.error(f"콜백 알림 실패: {e}")
        
        if not sent:
            try:
                import configparser, requests
                from common.config import CONFIG_PATH
                cfg = configparser.ConfigParser()
                cfg.read(CONFIG_PATH, encoding="utf-8")
                token = cfg.get("TELEGRAM", "BOT_TOKEN", fallback="")
                chat_id = cfg.get("TELEGRAM", "CHAT_ID", fallback="")
                if token and chat_id:
                    url = f"https://api.telegram.org/bot{token}/sendMessage"
                    await asyncio.to_thread(requests.post, url, json={"chat_id": chat_id, "text": msg}, timeout=5)
            except Exception as e:
                logger.error(f"직접 텔레그램 발송 실패: {e}")

    def perform_login(self, max_wait_sec: int = 15) -> bool:
        """
        PicaLive 로그인 창을 감지하여 비밀번호를 자동 입력하고 Enter를 전송합니다.
        클립보드 붙여넣기를 사용하여 한/영 키 상태에 영향받지 않습니다.
        """
        ensure_desktop()
        logger.info("🔑 PicaLive 자동 로그인 시도 중...")

        # 1. 로그인 창 대기
        login_hwnd = None
        for _ in range(max_wait_sec):
            # 메인 창이 이미 떴다면 이미 로그인 완료 상태
            if self.get_main_window_hwnd():
                logger.info("✅ PicaLive 메인 창 감지됨 (이미 로그인 완료 상태)")
                return True
            
            login_hwnd = self.get_login_window_hwnd()
            if login_hwnd:
                break
            time.sleep(1)

        if not login_hwnd:
            logger.warning("⚠️ PicaLive 로그인 창을 찾지 못했습니다.")
            return False

        try:
            # 2. 창 활성화 및 최상위로 올리기
            win32gui.ShowWindow(login_hwnd, win32con.SW_RESTORE)
            time.sleep(0.2)
            user32.SetForegroundWindow(login_hwnd)
            time.sleep(0.4)

            # 3. 비밀번호 입력 (클립보드 복사 후 Ctrl+V)
            pyperclip.copy(self.password)
            time.sleep(0.2)
            
            # 전체 선택 후 붙여넣기
            pyautogui.hotkey('ctrl', 'a')
            time.sleep(0.1)
            pyautogui.hotkey('ctrl', 'v')
            time.sleep(0.3)

            # 4. 엔터 키 전송으로 로그인 확인
            pyautogui.press('enter')
            logger.info("🔑 PicaLive 비밀번호 입력 및 Enter 전송 완료")

            # 5. 메인 카운터 창이 나타나는지 최대 15초 확인
            for _ in range(15):
                time.sleep(1)
                if self.get_main_window_hwnd():
                    logger.info("🎉 PicaLive 메인 창 로딩 성공! 정상 영업 복구 완료")
                    return True

            logger.warning("⚠️ PicaLive 비밀번호 전송 후 메인 창 감지 대기 타임아웃")
            return False

        except Exception as e:
            logger.error(f"PicaLive 자동 로그인 실행 중 예외: {e}")
            return False

    async def recover_picalive(self):
        """PicaLive 비정상 종료 시 자동 재실행 및 로그인 복구 수행"""
        if self.is_recovering:
            return
        
        self.is_recovering = True
        self.recovery_count += 1
        self.last_status_msg = f"자동 복구 진행 중 (시도 #{self.recovery_count})"
        logger.warning(f"🚨 [PicaWatchdog] PicaLive 종료 감지! 자동 복구 시작 (#{self.recovery_count})")

        # 1. 텔레그램 긴급 알림 전송
        await self.send_alert(
            f"🚨 [카운터 PC 긴급알림]\n"
            f"PicaLive(피카) 관리프로그램 종료가 감지되었습니다!\n"
            f"즉시 자동 재실행 및 복구를 진행합니다. (복구 #{self.recovery_count})"
        )

        try:
            # 2. 잔류 프로세스 강제 정리
            for proc_name in ["LiveStarter.exe", "PicaLive.exe"]:
                subprocess.run(["taskkill", "/IM", proc_name, "/T", "/F"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            await asyncio.sleep(2)

            # 3. LiveStarter.exe 실행 (os.startfile 또는 ShellExecute로 안전하게 윈도우 셸에서 구동)
            program_dir = os.path.dirname(self.program_path)
            logger.info(f"🚀 LiveStarter 실행 중: {self.program_path}")
            
            try:
                os.startfile(self.program_path)
            except Exception as e:
                logger.warning(f"os.startfile 실패, ShellExecute 시도: {e}")
                ctypes.windll.shell32.ShellExecuteW(None, "open", self.program_path, None, program_dir, 1)

            # 4. PicaLive.exe 프로세스 기동 대기 (최대 30초)
            started = False
            for _ in range(30):
                await asyncio.sleep(1)
                if self.is_process_running():
                    started = True
                    break

            if not started:
                logger.error("❌ PicaLive.exe 프로세스가 기동되지 않았습니다.")
                self.last_status_msg = "프로세스 기동 실패"
                await self.send_alert("❌ [카운터 PC 복구실패] PicaLive 프로세스 기동에 실패했습니다. 수동 점검이 필요합니다.")
                return

            logger.info("✨ PicaLive.exe 프로세스 기동 확인됨")

            # 5. 자동 로그인 수행
            if self.auto_login_enabled and self.password:
                login_success = await asyncio.to_thread(self.perform_login, 20)
                if login_success:
                    self.last_status_msg = "정상 영업 중 (자동 복구 완료)"
                    await self.send_alert(
                        f"✅ [카운터 PC 복구성공]\n"
                        f"PicaLive 관리프로그램이 성공적으로 재실행되고 로그인되었습니다.\n"
                        f"정상 영업 상태로 복구되었습니다."
                    )
                else:
                    self.last_status_msg = "로그인 대기 또는 확인 필요"
                    await self.send_alert(
                        f"⚠️ [카운터 PC 복구경고]\n"
                        f"PicaLive 프로세스는 실행되었으나, 자동 로그인을 확인하지 못했습니다.\n"
                        f"화면을 확인해 주세요."
                    )
            else:
                self.last_status_msg = "프로세스 실행 완료 (자동로그인 비활성화)"

        except Exception as e:
            logger.error(f"PicaLive 자동 복구 중 예외 발생: {e}")
            self.last_status_msg = f"복구 에러: {e}"
        finally:
            self.is_recovering = False

    async def watch_loop(self):
        """절대 죽지 않는 백그라운드 무인 감시 데몬 루프"""
        self.is_running = True
        logger.info("🛡️ PicaLive 백그라운드 무인 감시 데몬 가동 시작")

        while self.is_running:
            self.last_check_time = time.time()
            try:
                if self.is_enabled and self.program_path and os.path.exists(self.program_path):
                    # 복구 작업 진행 중인 경우 대기
                    if not self.is_recovering:
                        # 1. 프로세스 실행 여부 확인
                        pids = self.get_picalive_pids()
                        if not pids:
                            # PicaLive.exe가 꺼진 경우 -> 즉시 자동 복구 트리거!
                            self.last_status_msg = "프로세스 종료 감지 -> 복구 시작"
                            await self.recover_picalive()
                        else:
                            # 2. 프로세스는 살아있는 경우
                            main_hwnd = self.get_main_window_hwnd()
                            if main_hwnd:
                                self.last_status_msg = f"정상 영업 중 (PID: {pids[0]}, HWND: {main_hwnd})"
                            else:
                                # 메인 창이 없고 로그인 창만 떠 있는 경우 -> 자동 로그인 지원
                                login_hwnd = self.get_login_window_hwnd()
                                if login_hwnd and self.auto_login_enabled and self.password:
                                    self.last_status_msg = f"로그인 창 감지됨 (HWND: {login_hwnd}) -> 로그인 시도"
                                    await asyncio.to_thread(self.perform_login, 5)
                                else:
                                    self.last_status_msg = f"프로세스 가동 중 (창 로딩 대기)"

            except asyncio.CancelledError:
                logger.info("🛑 PicaLive 감시 루프 태스크가 취소되었습니다.")
                break
            except Exception as e:
                logger.error(f"🚨 PicaLive 감시 루프 내부 예외 발생 (무시하고 계속 감시): {e}")
                self.last_status_msg = f"예외 발생 후 복구됨: {e}"

            await asyncio.sleep(self.watch_interval)

    def start(self):
        if self.task is None or self.task.done():
            self.task = asyncio.create_task(self.watch_loop())
            logger.info("🚀 PicaLive 와치독 태스크 생성됨")

    def stop(self):
        self.is_running = False
        if self.task:
            self.task.cancel()
            self.task = None
        logger.info("🛑 PicaLive 와치독 태스크 중지됨")


pica_dog = PicaWatchdog()
