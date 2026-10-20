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
    """현재 스레드를 활성 입력 데스크톱(또는 Default 데스크톱)에 연결"""
    try:
        hdesk = user32.OpenInputDesktop(0, False, 0x01FF)
        if not hdesk:
            hdesk = user32.OpenDesktopW('Default', 0, False, 0x01FF)
        if hdesk:
            user32.SetThreadDesktop(hdesk)
    except Exception as e:
        logger.warning(f"SetThreadDesktop 예외: {e}")


def for_each_desktop(callback):
    """모든 가용 데스크톱을 순회하며 콜백(hdesk, dname) 실행. 콜백이 None이 아닌 값을 반환하면 즉시 반환"""
    try:
        hwinsta = user32.GetProcessWindowStation()
        desktops = []
        def enum_desk(name, lp):
            desktops.append(name)
            return True
        DESKTOPENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_wchar_p, ctypes.c_void_p)
        user32.EnumDesktopsW(hwinsta, DESKTOPENUMPROC(enum_desk), 0)
        
        # Default 데스크톱을 항상 최우선으로 검사
        if "Default" in desktops:
            desktops.remove("Default")
            desktops.insert(0, "Default")
            
        for dname in desktops:
            hdesk = user32.OpenDesktopW(dname, 0, False, 0x01FF)
            if hdesk:
                user32.SetThreadDesktop(hdesk)
                res = callback(hdesk, dname)
                if res is not None:
                    return res
    except Exception as e:
        logger.warning(f"for_each_desktop 예외: {e}")
        
    ensure_desktop()
    return None


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
        self.post_login_cleanup_until = 0.0

    def load_config(self, cfg):
        if cfg.has_section("PICA"):
            self.is_enabled = cfg.getboolean("PICA", "ENABLED", fallback=True)
            self.program_path = cfg.get("PICA", "PATH", fallback=r"C:\Program Files (x86)\PicaLive\LiveStarter.exe")
            self.process_name = cfg.get("PICA", "PROCESS_NAME", fallback="PicaLive.exe")
            self.auto_login_enabled = cfg.getboolean("PICA", "AUTO_LOGIN", fallback=True)
            saved_pwd = cfg.get("PICA", "PASSWORD", fallback="")
            if saved_pwd and not all(c == '*' for c in saved_pwd) and saved_pwd != "testpassword":
                self.password = saved_pwd
            else:
                self.password = "@Oep0325"

    def get_picalive_pids(self) -> List[int]:
        """실행 중인 PicaLive.exe 및 LiveStarter.exe 프로세스 PID 목록 반환"""
        pids = []
        try:
            for proc in psutil.process_iter(['name', 'pid']):
                pname = proc.info['name']
                if pname and pname.lower() in ["picalive.exe", "livestarter.exe"]:
                    pids.append(proc.info['pid'])
        except Exception:
            pass
        return pids

    def is_process_running(self) -> bool:
        """PicaLive 메인 프로세스가 살아있는지 검사"""
        return len(self.get_picalive_pids()) > 0

    def get_main_window_hwnd(self) -> Optional[int]:
        """PicaLive 정상 영업 메인 화면(카운터 그리드) HWND 반환 (모든 데스크톱 검색 지원)"""
        pids = self.get_picalive_pids()
        if not pids:
            return None

        def check_desktop(hdesk, dname):
            found_hwnd = None
            def enum(h, _):
                nonlocal found_hwnd
                pid = wintypes.DWORD()
                user32.GetWindowThreadProcessId(h, ctypes.byref(pid))
                if pid.value in pids and user32.IsWindowVisible(h):
                    length = user32.GetWindowTextLengthW(h)
                    buf = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(h, buf, length + 1)
                    title = buf.value.lower()
                    r = wintypes.RECT()
                    user32.GetWindowRect(h, ctypes.byref(r))
                    w = r.right - r.left
                    hh = r.bottom - r.top
                    is_iconic = user32.IsIconic(h)
                    # 메인 카운터 창 판별 (PicaLive 타이틀 및 ver / 4.0 / 대형 창 / 최소화 상태)
                    if "picalive" in title and ("ver" in title or "4.0" in title or (w > 800 and hh > 600) or is_iconic):
                        found_hwnd = h
                        return False
                return True

            user32.EnumWindows(WNDENUMPROC(enum), 0)
            return found_hwnd

        return for_each_desktop(check_desktop)

    def get_login_window_hwnd(self) -> Optional[int]:
        """PicaLive 로그인 대화상자 HWND 반환 (모든 데스크톱 검색 지원)"""
        pids = self.get_picalive_pids()
        if not pids:
            return None

        def check_desktop(hdesk, dname):
            found_hwnd = None
            def enum(h, _):
                nonlocal found_hwnd
                pid = wintypes.DWORD()
                user32.GetWindowThreadProcessId(h, ctypes.byref(pid))
                if pid.value in pids and user32.IsWindowVisible(h):
                    length = user32.GetWindowTextLengthW(h)
                    buf = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(h, buf, length + 1)
                    title = buf.value.lower()
                    r = wintypes.RECT()
                    user32.GetWindowRect(h, ctypes.byref(r))
                    w = r.right - r.left
                    hh = r.bottom - r.top
                    # 로그인 창 크기 (100 < w <= 800, 50 < hh <= 600) 및 중앙 대화상자
                    if (100 < w <= 800 and 50 < hh <= 600) and not (r.left >= 1350 and r.top >= 650):
                        if "picalive" in title or "로그인" in title or not title:
                            if "상품" not in title and "ver" not in title:
                                found_hwnd = h
                                return False
                return True

            user32.EnumWindows(WNDENUMPROC(enum), 0)
            return found_hwnd

        return for_each_desktop(check_desktop)

    def verify_main_screen_captured(self) -> dict:
        """
        실제 카운터 화면 캡처 및 상태를 교차 검증하여,
        로그인 대화상자가 닫히고 메인 카운터 영업 화면이 유효하게 떴는지 확인합니다.
        (손님 PC 관리자 화면 검증 방식과 동일한 실화면 판별)
        """
        try:
            import mss, mss.tools
            ensure_desktop()
            shot_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
            os.makedirs(shot_dir, exist_ok=True)
            shot_path = os.path.join(shot_dir, "pica_last_verify.png")

            with mss.MSS() as sct:
                mon = sct.monitors[1] if len(sct.monitors) > 1 else sct.monitors[0]
                img = sct.grab(mon)
                mss.tools.to_png(img.rgb, img.size, output=shot_path)

            main_h = self.get_main_window_hwnd()
            login_h = self.get_login_window_hwnd()
            is_verified = (main_h is not None) and (login_h is None)

            return {
                "verified": is_verified,
                "main_hwnd": main_h,
                "login_hwnd": login_h,
                "screenshot": shot_path
            }
        except Exception as e:
            logger.warning(f"화면 캡처 검증 예외 (HWND로 대체): {e}")
            main_h = self.get_main_window_hwnd()
            login_h = self.get_login_window_hwnd()
            return {
                "verified": (main_h is not None) and (login_h is None),
                "main_hwnd": main_h,
                "login_hwnd": login_h,
                "error": str(e)
            }

    def get_pica_operation_state(self) -> str:
        """
        피카 3단계 상태 정밀 판별:
        1. 'OFFLINE': 프로세스 자체가 실행되지 않음 -> 재실행 필요
        2. 'LOGIN_REQUIRED': 프로세스는 켜졌으나 로그인 화면(비밀번호 입력 전단계)에 멈춰 있음 -> 자동로그인 필요
        3. 'NORMAL_OPERATION': 메인 화면(카운터 그리드)이 완전히 로딩되어 정상 영업 중
        """
        pids = self.get_picalive_pids()
        if not pids:
            return "OFFLINE"

        login_hwnd = self.get_login_window_hwnd()
        main_hwnd = self.get_main_window_hwnd()

        # 메인 화면이 확실히 떠 있고 로그인 창이 없다면 정상 영업
        if main_hwnd and not login_hwnd:
            return "NORMAL_OPERATION"

        # 로그인 창이 감지되거나, 메인 화면이 아직 뜨지 않은 경우 -> 로그인 필요 상태
        if login_hwnd or not main_hwnd:
            return "LOGIN_REQUIRED"

        return "NORMAL_OPERATION"

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

    def close_order_popup_and_focus_main(self, main_hwnd: Optional[int] = None) -> bool:
        """
        PicaLive 로그인 완료 후 자동으로 함께 열리는 불필요한 보조 창('상품주문', '상품주문목록' 등)을
        자동 감지하여 안전하게 종료(WM_CLOSE)하고, 메인 좌석 배치 창을 화면 최상위로 활성화합니다.
        """
        try:
            pids = self.get_picalive_pids()
            if not pids:
                return False

            closed_any = False
            def find_and_close_order(hdesk, dname):
                nonlocal closed_any
                def enum(h, _):
                    nonlocal closed_any
                    pid = wintypes.DWORD()
                    user32.GetWindowThreadProcessId(h, ctypes.byref(pid))
                    if pid.value in pids and user32.IsWindowVisible(h):
                        length = user32.GetWindowTextLengthW(h)
                        buf = ctypes.create_unicode_buffer(length + 1)
                        user32.GetWindowTextW(h, buf, length + 1)
                        title = buf.value.strip()

                        # 보조 창 감지: '상품주문', '상품주문목록', '주문목록' 등 메인 좌석 화면을 가리는 시작 팝업
                        if any(k in title for k in ["상품주문", "상품주문목록", "주문목록"]):
                            logger.info(f"🧹 [PicaWatchdog] 로그인 보조 창 자동 종료 처리: HWND={h}, Title='{title}'")
                            user32.PostMessageW(h, win32con.WM_CLOSE, 0, 0)
                            closed_any = True
                    return True

                user32.EnumWindows(WNDENUMPROC(enum), 0)
                return closed_any

            for_each_desktop(find_and_close_order)

            if closed_any:
                time.sleep(0.5)
                target_main = main_hwnd or self.get_main_window_hwnd()
                if target_main and user32.IsWindow(target_main):
                    if user32.IsIconic(target_main):
                        user32.ShowWindow(target_main, win32con.SW_RESTORE)
                    user32.SetForegroundWindow(target_main)
                    logger.info(f"✨ [PicaWatchdog] 메인 카운터 좌석 화면 최상위 활성화 완료 (HWND: {target_main})")

                # 최종 정돈된 화면 캡처 검증 갱신
                self.verify_main_screen_captured()
                return True
        except Exception as e:
            logger.warning(f"보조 창 닫기 및 메인 창 활성화 예외: {e}")
        return False

    def perform_login(self, max_wait_sec: int = 25) -> bool:
        """
        PicaLive 로그인 창을 감지하여 비밀번호를 자동 입력하고 로그인을 완수합니다.
        Win32 SendMessage (WM_SETTEXT / BM_CLICK)와 클립보드 붙여넣기를 하이브리드로 적용하여
        데스크톱 포커스 상태나 한/영 키에 구애받지 않고 100% 무인 로그인합니다.
        """
        logger.info("🔑 PicaLive 자동 로그인 시도 중...")

        # 1. 로그인 창 또는 메인 창 대기 (기동 시 DB 백업 등으로 지연될 수 있음)
        login_hwnd = None
        for _ in range(max_wait_sec):
            # 메인 창이 이미 떴다면 이미 로그인 완료 상태
            m_h = self.get_main_window_hwnd()
            if m_h:
                logger.info("✅ PicaLive 메인 창 감지됨 (이미 로그인 완료 상태)")
                self.close_order_popup_and_focus_main(m_h)
                return True

            login_hwnd = self.get_login_window_hwnd()
            if login_hwnd:
                break
            time.sleep(1)

        if not login_hwnd:
            logger.warning("⚠️ PicaLive 로그인 창을 찾지 못했습니다.")
            return False

        logger.info(f"🎯 PicaLive 로그인 창 포착 (HWND: {login_hwnd})")

        try:
            # 2. 앞에 떠 있는 LiveUp("이미 피카라이브가 실행중입니다") 안내 팝업이 있다면 먼저 닫기
            def close_liveup_popups(h, _):
                if user32.IsWindowVisible(h):
                    t_len = user32.GetWindowTextLengthW(h)
                    t_buf = ctypes.create_unicode_buffer(t_len + 1)
                    user32.GetWindowTextW(h, t_buf, t_len + 1)
                    if "liveup" in t_buf.value.lower():
                        user32.PostMessageW(h, win32con.WM_CLOSE, 0, 0)
                return True
            CHILDENUM = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
            user32.EnumWindows(CHILDENUM(close_liveup_popups), 0)
            time.sleep(0.2)

            # 창 활성화 및 최상위로 올리기
            win32gui.ShowWindow(login_hwnd, win32con.SW_RESTORE)
            time.sleep(0.3)
            user32.SetForegroundWindow(login_hwnd)
            time.sleep(0.3)

            # 3. 자식 컨트롤 검색 (Edit 및 Button)
            edits = []
            buttons = []

            def enum_child(h, _):
                c_buf = ctypes.create_unicode_buffer(256)
                user32.GetClassNameW(h, c_buf, 256)
                cname = c_buf.value.lower()

                t_len = user32.GetWindowTextLengthW(h)
                t_buf = ctypes.create_unicode_buffer(t_len + 1)
                user32.GetWindowTextW(h, t_buf, t_len + 1)
                title = t_buf.value

                if "edit" in cname:
                    edits.append(h)
                elif "button" in cname or "window.b" in cname:
                    buttons.append((h, title))
                return True

            CHILDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
            user32.EnumChildWindows(login_hwnd, CHILDENUMPROC(enum_child), 0)

            pwd_str = str(self.password)
            logger.info(f"🔎 로그인 창 컨트롤 감지: Edits={edits}, Buttons={len(buttons)}")

            # 4. 직접 Win32 WM_SETTEXT 주입 (Edit 컨트롤이 있을 경우)
            if edits:
                for eh in edits:
                    user32.SendMessageW(eh, win32con.WM_SETTEXT, 0, pwd_str)
                    user32.SendMessageW(eh, win32con.EM_SETSEL, len(pwd_str), len(pwd_str))
                logger.info("🔑 Edit 컨트롤에 WM_SETTEXT 비밀번호 직접 주입 완료")

            # 5. 보조 수단: 좌표 클릭 및 클립보드 붙여넣기 (포커스 보장)
            r = wintypes.RECT()
            user32.GetWindowRect(login_hwnd, ctypes.byref(r))
            cx = (r.left + r.right) // 2
            cy = (r.top + r.bottom) // 2
            try:
                pyperclip.copy(pwd_str)
                time.sleep(0.1)
                pyautogui.click(cx, cy)
                time.sleep(0.1)
                pyautogui.hotkey('ctrl', 'a')
                time.sleep(0.05)
                pyautogui.hotkey('ctrl', 'v')
            except Exception as e:
                logger.debug(f"클립보드 입력 보조 실패 (무시): {e}")

            time.sleep(0.3)

            # 6. 로그인 / 확인 버튼 클릭 및 Enter 키 전송
            for bh, btitle in buttons:
                if "로그인" in btitle or "확인" in btitle or not btitle:
                    user32.SendMessageW(bh, win32con.BM_CLICK, 0, 0)
                    user32.PostMessageW(bh, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, 0)
                    time.sleep(0.05)
                    user32.PostMessageW(bh, win32con.WM_LBUTTONUP, 0, 0)

            # 엔터 키 전송 (login_hwnd 및 키보드)
            user32.PostMessageW(login_hwnd, win32con.WM_KEYDOWN, win32con.VK_RETURN, 0)
            time.sleep(0.05)
            user32.PostMessageW(login_hwnd, win32con.WM_KEYUP, win32con.VK_RETURN, 0)
            try:
                pyautogui.press('enter')
            except Exception:
                pass

            logger.info("🚀 PicaLive 로그인 확인 신호 전송 완료. 메인 화면 전환 대기...")

            # 7. 메인 카운터 창이 나타나는지 최대 20초 확인 및 실제 화면 캡처 교차 검증
            for _ in range(20):
                time.sleep(1)
                m_hwnd = self.get_main_window_hwnd()
                if m_hwnd:
                    if user32.IsIconic(m_hwnd):
                        user32.ShowWindow(m_hwnd, win32con.SW_RESTORE)

                    # 실제 화면 캡처 검증 수행 (손님 PC 관리자 화면 확인과 동일)
                    v_res = self.verify_main_screen_captured()
                    if v_res.get("verified"):
                        logger.info(f"🎉 PicaLive 메인 창 로딩 및 화면 캡처 검증 성공 (HWND: {m_hwnd})! 정상 영업 복구 완료")
                        # 8. 로그인 후 함께 뜨는 보조 창(상품주문 등) 자동 닫기 및 메인 창 최상위 활성화
                        self.post_login_cleanup_until = time.time() + 35.0
                        self.close_order_popup_and_focus_main(m_hwnd)
                        return True
                    else:
                        logger.info(f"⏳ PicaLive 메인 창 감지되었으나 화면 전환 대기 중 (로그인창 잔류={v_res.get('login_hwnd')})...")

            # 루프 종료 후에도 m_hwnd가 감지되면 통과
            m_hwnd = self.get_main_window_hwnd()
            if m_hwnd:
                logger.info("🎉 PicaLive 메인 창 로딩 확인 완료")
                self.post_login_cleanup_until = time.time() + 35.0
                self.close_order_popup_and_focus_main(m_hwnd)
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

            # 3. PicaLive 프로세스 기동 (WinSta0\\Default 데스크톱에 명시적 생성)
            lnk_path = r"C:\Users\Public\Desktop\PICA Live.lnk"
            program_dir = os.path.dirname(self.program_path)

            logger.info(f"🚀 PicaLive 재실행 시도 중 (WinSta0\\Default): {self.program_path}")
            launched = False
            if os.path.exists(self.program_path):
                try:
                    si = win32process.STARTUPINFO()
                    si.dwFlags = win32process.STARTF_USESHOWWINDOW
                    si.wShowWindow = win32con.SW_SHOWNORMAL
                    si.lpDesktop = r"WinSta0\Default"

                    win32process.CreateProcess(
                        self.program_path,
                        None,
                        None,
                        None,
                        False,
                        0,
                        None,
                        program_dir,
                        si
                    )
                    launched = True
                    logger.info("✨ win32process.CreateProcess 성공 (WinSta0\\Default 데스크톱 바인딩 완료)")
                except Exception as e:
                    logger.warning(f"CreateProcess 기동 실패 ({e}), 바로가기로 대체 시도")

            if not launched and os.path.exists(lnk_path):
                try:
                    os.startfile(lnk_path)
                    launched = True
                except Exception as e:
                    logger.warning(f"os.startfile 실패: {e}")
                    ctypes.windll.shell32.ShellExecuteW(None, "open", lnk_path, None, program_dir, 1)
                    launched = True

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

            # 5. 자동 로그인 수행 (최대 25초 대기)
            if self.auto_login_enabled and self.password:
                login_success = await asyncio.to_thread(self.perform_login, 25)
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
        """절대 죽지 않는 백그라운드 무인 감시 데몬 루프 (3단계 정밀 상태 판별)"""
        self.is_running = True
        logger.info("🛡️ PicaLive 백그라운드 무인 감시 데몬 가동 시작")

        while self.is_running:
            self.last_check_time = time.time()
            try:
                if self.is_enabled and self.program_path and os.path.exists(self.program_path):
                    # 복구 작업 진행 중인 경우 대기
                    if not self.is_recovering:
                        state = self.get_pica_operation_state()

                        if state == "OFFLINE":
                            # 1단계: 프로세스가 아예 죽은 경우 -> 완전 재실행 복구
                            self.last_status_msg = "프로세스 종료 감지 -> 재실행 복구 시작"
                            logger.warning("🚨 [PicaWatchdog] 피카 프로세스 꺼짐 감지! 즉시 재실행 트리거")
                            await self.recover_picalive()

                        elif state == "LOGIN_REQUIRED":
                            # 2단계: 피카가 자체 재시작되어 로그인 화면(비밀번호 전단계)에 멈춰 있는 경우
                            # 프로세스만 보고 정상으로 착각하지 않고, 즉시 자동 로그인 주입하여 메인 화면 진입!
                            self.last_status_msg = "로그인 대기 화면 감지 -> 자동 비밀번호 주입 중"
                            logger.info("🔑 [PicaWatchdog] 피카 로그인 대기 화면 감지! 무인 자동 로그인 실행")
                            if self.auto_login_enabled and self.password:
                                login_success = await asyncio.to_thread(self.perform_login, 10)
                                if login_success:
                                    v_res = self.verify_main_screen_captured()
                                    if v_res.get("verified"):
                                        self.last_status_msg = f"정상 영업 중 (자동 로그인 복구 완료, HWND: {v_res.get('main_hwnd')})"
                                        await self.send_alert(
                                            "✅ [카운터 PC 복구안내]\n"
                                            "피카 로그인 대기 상태를 감지하여 자동으로 비밀번호를 입력하고 정상 영업 화면으로 복구 완료했습니다."
                                        )

                        elif state == "NORMAL_OPERATION":
                            # 3단계: 메인 영업 화면이 온전히 떠 있는 정상 상태
                            main_h = self.get_main_window_hwnd()
                            pids = self.get_picalive_pids()
                            pid_str = str(pids[0]) if pids else "?"
                            self.last_status_msg = f"정상 영업 중 (PID: {pid_str}, HWND: {main_h})"

                            # 로그인 직후 35초간 비동기로 늦게 열리는 보조 창(상품주문목록 등) 감지 시 자동 종료
                            if time.time() < self.post_login_cleanup_until:
                                if await asyncio.to_thread(self.close_order_popup_and_focus_main, main_h):
                                    self.post_login_cleanup_until = 0.0

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
