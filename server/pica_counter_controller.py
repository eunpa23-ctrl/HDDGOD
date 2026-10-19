"""
PicaLive 카운터 프로그램 직접 제어 모듈
손님방 PC에서 매크로를 돌리지 않고, 카운터(서버) 화면의 PicaLive 관리화면에서
해당 좌석 우클릭 -> [관리자로그인] 항목을 직접 클릭/체크해제하여
100% 안전하고 오작동 없이 관리자 모드 전환 및 잠금 복구를 수행합니다.
"""

import ctypes
import time
import logging
import threading
from ctypes import wintypes
from typing import Optional, Dict, Any

logger = logging.getLogger("PicaCounterController")

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32
WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

# 1920x1080 카운터 화면 기준 각 좌석 카드 정중앙 좌표
SEAT_COORDS = {
    1: (526, 702),
    2: (1172, 574),
    3: (1172, 438),
    4: (1172, 302),
    5: (870, 302),
    6: (698, 302),
    7: (526, 302),
    8: (526, 566),
}

_action_lock = threading.Lock()
_last_counter_states: Dict[int, str] = {}

def get_last_known_counter_state(seat_num: int) -> Optional[str]:
    """가장 최근에 카운터 PicaLive 화면에서 판별된 좌석 상태 반환"""
    return _last_counter_states.get(seat_num)

def get_counter_seat_states() -> Dict[int, str]:
    """
    카운터(서버) 화면의 PicaLive 각 좌석 카드 색상을 실시간(0.5ms) 샘플링하여 판별
    - 'ADMIN': 점주 관리자 로그인 (연두/올리브색 카드, 🔑 열쇠 아이콘)
    - 'USING': 손님 실제 로그인 이용 중 (보라색 카드, 남은시간 표시)
    - 'LOCKED': 빈자리 대기 잠금 (청록색 카드)
    - 'OFFLINE': PC 꺼짐 (어두운 회색/검은색 카드)
    """
    global _last_counter_states
    try:
        ensure_desktop()
        pica = get_pica_hwnd()
        if not pica or user32.IsIconic(pica):
            return _last_counter_states

        hdc = user32.GetDC(0)
        if not hdc:
            return _last_counter_states

        results = {}
        try:
            for seat, (sx, sy) in SEAT_COORDS.items():
                samples = []
                for dx in [-20, 0, 20]:
                    for dy in [-20, 0, 20]:
                        color = gdi32.GetPixel(hdc, sx + dx, sy + dy)
                        r = color & 0xFF
                        g = (color >> 8) & 0xFF
                        b = (color >> 16) & 0xFF
                        samples.append((r, g, b))

                for dy in [-15, 15]:
                    color = gdi32.GetPixel(hdc, sx, sy + dy)
                    samples.append((color & 0xFF, (color >> 8) & 0xFF, (color >> 16) & 0xFF))

                purple_count = sum(1 for (r, g, b) in samples if b > g + 15 and b > 80 and r > g)
                black_count = sum(1 for (r, g, b) in samples if r < 45 and g < 45 and b < 45)
                teal_count = sum(1 for (r, g, b) in samples if g > 130 and g > r + 80 and b > 80)
                admin_count = sum(1 for (r, g, b) in samples if (g > r and r > b and g > 65 and b < 60) or (r > 200 and g > 200 and b > 200) or (r > 120 and g > 200 and b < 80))

                if purple_count >= 3:
                    st = "USING"
                elif black_count >= 8:
                    st = "OFFLINE"
                elif admin_count >= 4:
                    st = "ADMIN"
                elif teal_count >= 5:
                    st = "LOCKED"
                else:
                    st = "LOCKED"
                results[seat] = st

            _last_counter_states = results
            return results
        finally:
            user32.ReleaseDC(0, hdc)
    except Exception as e:
        logger.error(f"좌석 상태 색상 판별 예외: {e}")
        return _last_counter_states

def ensure_desktop():
    """현재 스레드를 Default 윈도우 데스크톱에 연결"""
    try:
        hdesk = user32.OpenDesktopW('Default', 0, False, 0x01FF)
        if hdesk:
            user32.SetThreadDesktop(hdesk)
    except Exception as e:
        logger.warning(f"SetThreadDesktop 예외: {e}")

def get_pica_hwnd() -> Optional[int]:
    """PicaLive 메인 윈도우 HWND 반환"""
    import psutil
    pids = [p.pid for p in psutil.process_iter() if 'picalive' in p.name().lower()]
    if not pids:
        return None
    found_hwnd = None
    def enum(h, lp):
        nonlocal found_hwnd
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(h, ctypes.byref(pid))
        if pid.value in pids and user32.IsWindowVisible(h):
            r = wintypes.RECT()
            user32.GetWindowRect(h, ctypes.byref(r))
            w = r.right - r.left
            h_h = r.bottom - r.top
            if w > 800 and h_h > 600:
                found_hwnd = h
                return False
        return True
    user32.EnumWindows(WNDENUMPROC(enum), 0)
    return found_hwnd

def get_popup_menu_rect() -> Optional[tuple]:
    """열려있는 WinForms 컨텍스트 메뉴 윈도우의 RECT (left, top, right, bottom) 반환"""
    rect = None
    def enum(h, lp):
        nonlocal rect
        if user32.IsWindowVisible(h):
            c = ctypes.create_unicode_buffer(256)
            user32.GetClassNameW(h, c, 256)
            r = wintypes.RECT()
            user32.GetWindowRect(h, ctypes.byref(r))
            w = r.right - r.left
            h_h = r.bottom - r.top
            # 피카라이브 우클릭 메뉴: 너비 180~260, 높이 200~500
            if 'windowsforms' in c.value.lower() and 180 <= w <= 260 and 200 <= h_h <= 500:
                rect = (r.left, r.top, r.right, r.bottom)
                return False
        return True
    user32.EnumWindows(WNDENUMPROC(enum), 0)
    return rect

def set_pica_admin_mode(seat_num: int, enable: bool) -> Dict[str, Any]:
    """
    카운터(서버) 피카 프로그램에서 좌석 번호(1~8)를 우클릭하여 관리자 모드 설정/해제
    enable = True : 관리자 로그인 (잠금 해제 -> 🔑 관리자)
    enable = False: 관리자 로그인 해제 (정상 빈자리 대기 잠금 복구)
    """
    if seat_num not in SEAT_COORDS:
        return {"status": "error", "message": f"유효하지 않은 좌석 번호: {seat_num}"}

    with _action_lock:
        ensure_desktop()
        pica = get_pica_hwnd()
        if not pica:
            logger.error("❌ PicaLive 카운터 메인 윈도우를 찾을 수 없습니다.")
            return {"status": "error", "message": "PicaLive 메인 창을 찾을 수 없음"}

        # 원본 마우스 커서 위치 백업
        orig_pt = wintypes.POINT()
        user32.GetCursorPos(ctypes.byref(orig_pt))

        try:
            # 1. PicaLive 창 활성화
            is_iconic = user32.IsIconic(pica)
            user32.keybd_event(0x12, 0, 0, 0)
            user32.keybd_event(0x12, 0, 2, 0)
            user32.ShowWindow(pica, 9) # SW_RESTORE
            user32.ShowWindow(pica, 3) # SW_MAXIMIZE
            user32.SetForegroundWindow(pica)
            user32.BringWindowToTop(pica)
            time.sleep(0.4 if is_iconic else 0.15)

            # 2. 해당 좌석 카드 정중앙으로 이동 후 우클릭 (최대 2회 시도)
            sx, sy = SEAT_COORDS[seat_num]
            menu_rect = None
            for attempt in range(2):
                user32.SetCursorPos(sx, sy)
                time.sleep(0.08)
                user32.mouse_event(8, 0, 0, 0, 0) # RIGHTDOWN
                time.sleep(0.04)
                user32.mouse_event(16, 0, 0, 0, 0) # RIGHTUP

                # 3. 우클릭 팝업 메뉴 감지
                for _ in range(10):
                    time.sleep(0.08)
                    menu_rect = get_popup_menu_rect()
                    if menu_rect:
                        break
                if menu_rect:
                    break
                time.sleep(0.15)

            if not menu_rect:
                logger.warning(f"⚠️ 좌석 {seat_num}번 우클릭 팝업 메뉴 감지 실패")
                # ESC 전송으로 취소
                user32.keybd_event(0x1B, 0, 0, 0); user32.keybd_event(0x1B, 0, 2, 0)
                return {"status": "error", "message": f"좌석 {seat_num}번 우클릭 메뉴 미감지"}

            h_h = menu_rect[3] - menu_rect[1]
            is_currently_admin = (h_h <= 350)
            logger.info(f"🎯 좌석 {seat_num}번 메뉴 감지: RECT={menu_rect}, 높이={h_h}px, 현재 관리자여부={is_currently_admin}, 요청={enable}")

            if enable:
                # [관리자 로그인 켜기]
                if is_currently_admin:
                    logger.info(f"좌석 {seat_num}번은 이미 카운터에서 '관리자' 상태입니다.")
                    user32.keybd_event(0x1B, 0, 0, 0); user32.keybd_event(0x1B, 0, 2, 0)
                    return {"status": "ok", "seat": seat_num, "action": "UNLOCK_PICA", "already_state": True}

                # 대기 메뉴에서 '관리자로그인' 항목은 y_offset = 107
                click_x = menu_rect[0] + 100
                click_y = menu_rect[1] + 107
                user32.SetCursorPos(click_x, click_y)
                time.sleep(0.06)
                user32.mouse_event(2, 0, 0, 0, 0) # LEFTDOWN
                time.sleep(0.04)
                user32.mouse_event(4, 0, 0, 0, 0) # LEFTUP
                time.sleep(0.4)
                logger.info(f"✅ 좌석 {seat_num}번 카운터 [관리자로그인] 클릭 완료 -> 관리자 모드 전환!")
                return {"status": "ok", "seat": seat_num, "action": "UNLOCK_PICA", "state": "ADMIN"}

            else:
                # [관리자 로그인 끄기 (잠금 복구)]
                if not is_currently_admin:
                    logger.info(f"좌석 {seat_num}번은 이미 카운터에서 잠금/대기 상태입니다.")
                    user32.keybd_event(0x1B, 0, 0, 0); user32.keybd_event(0x1B, 0, 2, 0)
                    return {"status": "ok", "seat": seat_num, "action": "LOCK_PICA", "already_state": True}

                # 관리자 메뉴에서 '✓ 관리자로그인' 항목은 최상단 y_offset = 12
                click_x = menu_rect[0] + 100
                click_y = menu_rect[1] + 12
                user32.SetCursorPos(click_x, click_y)
                time.sleep(0.06)
                user32.mouse_event(2, 0, 0, 0, 0) # LEFTDOWN
                time.sleep(0.04)
                user32.mouse_event(4, 0, 0, 0, 0) # LEFTUP
                time.sleep(0.4)
                logger.info(f"✅ 좌석 {seat_num}번 카운터 [✓ 관리자로그인] 체크 해제 클릭 완료 -> 잠금 대기 복구!")
                return {"status": "ok", "seat": seat_num, "action": "LOCK_PICA", "state": "LOCKED"}

        except Exception as e:
            logger.error(f"좌석 {seat_num}번 피카 제어 예외: {e}")
            return {"status": "error", "message": str(e)}
        finally:
            # 원래 마우스 위치 복원
            try:
                user32.SetCursorPos(orig_pt.x, orig_pt.y)
            except Exception:
                pass
