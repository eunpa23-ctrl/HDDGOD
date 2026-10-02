# -*- coding: utf-8 -*-
r"""
제우스 HDD PROTECTOR - 실시간 화면 스트리밍 및 원격 제어 입력 모듈
G:\내 드라이브\PROJECT\HDDGOD\client\screen_streamer.py
"""
import io
import base64
import logging
import ctypes
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

class ScreenStreamer:
    """초고속 화면 캡처 및 모바일 터치/마우스 원격 제어 처리기"""

    def __init__(self, target_width: int = 1920, quality: int = 75):
        self.target_width = target_width
        self.quality = quality
        self.sct = mss.mss() if HAS_MSS else None
        user32 = ctypes.windll.user32
        self.screen_w = user32.GetSystemMetrics(0)
        self.screen_h = user32.GetSystemMetrics(1)

    def capture_frame_base64(self) -> str:
        """화면을 캡처하여 최적화된 JPEG base64 문자열로 반환"""
        try:
            img = None
            if self.sct:
                try:
                    monitor = self.sct.monitors[1]
                    sct_img = self.sct.grab(monitor)
                    img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
                except Exception:
                    img = None

            if not img:
                try:
                    from PIL import ImageGrab
                    img = ImageGrab.grab()
                except Exception:
                    pass

            if not img:
                w = self.screen_w if self.screen_w > 0 else 1920
                h = self.screen_h if self.screen_h > 0 else 1080
                img = Image.new("RGB", (w, h), color=(15, 23, 42))

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
        try:
            # 좌표 비율 (0.0 ~ 1.0) -> 실제 모니터 해상도 픽셀 변환
            x_ratio = data.get("x", 0.0)
            y_ratio = data.get("y", 0.0)
            real_x = int(x_ratio * self.screen_w)
            real_y = int(y_ratio * self.screen_h)

            if event_type == "CLICK":
                btn = data.get("button", "left")
                if HAS_PYAUTOGUI:
                    pyautogui.click(real_x, real_y, button=btn)
                else:
                    ctypes.windll.user32.SetCursorPos(real_x, real_y)
                    ctypes.windll.user32.mouse_event(2, 0, 0, 0, 0) # Down
                    ctypes.windll.user32.mouse_event(4, 0, 0, 0, 0) # Up

            elif event_type == "MOVE":
                if HAS_PYAUTOGUI:
                    pyautogui.moveTo(real_x, real_y)
                else:
                    ctypes.windll.user32.SetCursorPos(real_x, real_y)

            elif event_type == "TEXT":
                text = data.get("text", "")
                if HAS_PYAUTOGUI and text:
                    pyautogui.write(text)

            elif event_type == "KEY":
                key = data.get("key", "")
                if HAS_PYAUTOGUI and key:
                    pyautogui.press(key)

        except Exception as e:
            logger.error(f"원격 입력 처리 오류: {e}")

if __name__ == "__main__":
    streamer = ScreenStreamer()
    b64 = streamer.capture_frame_base64()
    print("캡처 성공 길이:", len(b64))
