# -*- coding: utf-8 -*-
r"""
제우스 HDD PROTECTOR - 실시간 화면 스트리밍 및 원격 제어 입력 모듈
G:\내 드라이브\PROJECT\HDDGOD\client\screen_streamer.py
"""
import io
import base64
import logging
import ctypes
import threading
from PIL import Image

try:
    import mss
    HAS_MSS = True
except ImportError:
    HAS_MSS = False

try:
    import pyautogui
    pyautogui.FAILSAFE = False
    HAS_PYAUTOGUI = True
except ImportError:
    HAS_PYAUTOGUI = False

logger = logging.getLogger("ScreenStreamer")
_thread_local = threading.local()

def ensure_default_desktop():
    """백그라운드/가상 데스크톱 환경에서도 실제 물리 화면(WinSta0\\default 데스크톱)에 스레드를 바인딩"""
    try:
        user32 = ctypes.windll.user32
        hwinsta = user32.OpenWindowStationW("WinSta0", False, 0x037F)
        if hwinsta:
            user32.SetProcessWindowStation(hwinsta)
        hDesk = user32.OpenDesktopW("default", 0, False, 0x01FF) # GENERIC_ALL
        if hDesk:
            user32.SetThreadDesktop(hDesk)
    except Exception:
        pass

def get_thread_sct():
    """스레드별 독립적인 mss 인스턴스 반환 (Windows GDI 스레드 제약 완벽 해결)"""
    if not HAS_MSS:
        return None
    ensure_default_desktop()
    if not hasattr(_thread_local, 'sct') or _thread_local.sct is None:
        try:
            _thread_local.sct = mss.mss()
        except Exception as e:
            logger.error(f"mss init failed: {e}")
            _thread_local.sct = None
    return _thread_local.sct

class ScreenStreamer:
    """초고속 화면 캡처 및 모바일 터치/마우스 원격 제어 처리기"""

    def __init__(self, target_width: int = 1280, quality: int = 55):
        self.target_width = target_width
        self.quality = quality
        
        # 윈도우 OS 디스플레이 배율(DPI 125%, 150% 등)에 의한 마우스 좌표 왜곡 100% 방지
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2) # Per-monitor DPI aware
        except Exception:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass

        ensure_default_desktop()
        user32 = ctypes.windll.user32
        self.screen_w = user32.GetSystemMetrics(0)
        self.screen_h = user32.GetSystemMetrics(1)
        if self.screen_w <= 0: self.screen_w = 1920
        if self.screen_h <= 0: self.screen_h = 1080

    def capture_frame_base64(self) -> str:
        """화면을 캡처하여 최적화된 JPEG base64 문자열로 반환"""
        ensure_default_desktop()
        try:
            img = None
            sct = get_thread_sct()
            if sct:
                try:
                    monitor = sct.monitors[1]
                    sct_img = sct.grab(monitor)
                    img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
                except Exception as e1:
                    try:
                        _thread_local.sct = mss.mss()
                        sct = _thread_local.sct
                        monitor = sct.monitors[1]
                        sct_img = sct.grab(monitor)
                        img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
                    except Exception as e2:
                        logger.error(f"mss grab failed: e1={e1}, e2={e2}")
                        img = None

            if not img:
                try:
                    from PIL import ImageGrab
                    img = ImageGrab.grab()
                except Exception as e_grab:
                    logger.error(f"ImageGrab failed: {e_grab}")
                    pass

            if not img:
                w = self.screen_w if self.screen_w > 0 else 1920
                h = self.screen_h if self.screen_h > 0 else 1080
                img = Image.new("RGB", (w, h), color=(15, 23, 42))

            # 캡처된 원본 모니터 크기로 해상도 동기화 (DPI 오차 0%)
            self.screen_w = img.width
            self.screen_h = img.height

            # 화면 위에 실제 마우스 커서 화살표 선명하게 합성
            try:
                class POINT(ctypes.Structure):
                    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]
                pt = POINT()
                if ctypes.windll.user32.GetCursorPos(ctypes.byref(pt)):
                    cx, cy = pt.x, pt.y
                    if 0 <= cx < img.width and 0 <= cy < img.height:
                        from PIL import ImageDraw
                        draw = ImageDraw.Draw(img)
                        points = [
                            (cx, cy),
                            (cx, cy + 18),
                            (cx + 5, cy + 14),
                            (cx + 9, cy + 21),
                            (cx + 12, cy + 19),
                            (cx + 8, cy + 12),
                            (cx + 14, cy + 12)
                        ]
                        draw.polygon(points, fill="white", outline="black")
            except Exception:
                pass

            # 가로 폭 리사이즈 (대역폭 절약 및 모바일 최적화)
            if img.width > self.target_width:
                ratio = self.target_width / float(img.width)
                new_height = int(float(img.height) * ratio)
                img = img.resize((self.target_width, new_height), Image.Resampling.BILINEAR)

            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=self.quality, optimize=True)
            return base64.b64encode(buf.getvalue()).decode("utf-8")
        except Exception as e:
            logger.error(f"화면 캡처 실패: {e}")
            return ""

    def handle_remote_input(self, event_type: str, data: dict) -> None:
        """모바일 터치 및 마우스/키보드 입력 이벤트 실행"""
        ensure_default_desktop()
        try:
            # 좌표 비율 (0.0 ~ 1.0) -> 실제 모니터 해상도 픽셀 변환
            x_ratio = data.get("x", 0.0)
            y_ratio = data.get("y", 0.0)
            real_x = int(x_ratio * self.screen_w)
            real_y = int(y_ratio * self.screen_h)

            if event_type == "MOUSE_DOWN":
                btn = data.get("button", "left")
                ctypes.windll.user32.SetCursorPos(real_x, real_y)
                if btn == "right":
                    ctypes.windll.user32.mouse_event(8, 0, 0, 0, 0) # Right Down
                else:
                    ctypes.windll.user32.mouse_event(2, 0, 0, 0, 0) # Left Down

            elif event_type == "MOUSE_UP":
                btn = data.get("button", "left")
                ctypes.windll.user32.SetCursorPos(real_x, real_y)
                if btn == "right":
                    ctypes.windll.user32.mouse_event(16, 0, 0, 0, 0) # Right Up
                else:
                    ctypes.windll.user32.mouse_event(4, 0, 0, 0, 0) # Left Up

            elif event_type == "CLICK":
                btn = data.get("button", "left")
                ctypes.windll.user32.SetCursorPos(real_x, real_y)
                import time
                if btn == "right":
                    time.sleep(0.015)
                    ctypes.windll.user32.mouse_event(8, 0, 0, 0, 0) # Right Down
                    time.sleep(0.015)
                    ctypes.windll.user32.mouse_event(16, 0, 0, 0, 0) # Right Up
                elif btn == "double":
                    ctypes.windll.user32.mouse_event(2, 0, 0, 0, 0)
                    time.sleep(0.01)
                    ctypes.windll.user32.mouse_event(4, 0, 0, 0, 0)
                    time.sleep(0.01)
                    ctypes.windll.user32.mouse_event(2, 0, 0, 0, 0)
                    time.sleep(0.01)
                    ctypes.windll.user32.mouse_event(4, 0, 0, 0, 0)
                else:
                    time.sleep(0.005)
                    ctypes.windll.user32.mouse_event(2, 0, 0, 0, 0) # Left Down
                    time.sleep(0.005)
                    ctypes.windll.user32.mouse_event(4, 0, 0, 0, 0) # Left Up

            elif event_type == "MOVE":
                ctypes.windll.user32.SetCursorPos(real_x, real_y)

            elif event_type == "WHEEL":
                delta = int(data.get("delta", 0))
                ctypes.windll.user32.mouse_event(0x0800, 0, 0, delta, 0) # MOUSEEVENTF_WHEEL

            elif event_type == "TEXT":
                text = data.get("text", "")
                if HAS_PYAUTOGUI and text:
                    pyautogui.write(text)

            elif event_type == "KEY":
                key = data.get("key", "")
                if HAS_PYAUTOGUI and key:
                    pyautogui.press(key)

            elif event_type == "HOTKEY":
                keys = data.get("keys", [])
                if HAS_PYAUTOGUI and keys:
                    pyautogui.hotkey(*keys)

        except Exception as e:
            logger.error(f"원격 입력 처리 오류: {e}")

if __name__ == "__main__":
    streamer = ScreenStreamer()
    b64 = streamer.capture_frame_base64()
    print("캡처 성공 길이:", len(b64))
