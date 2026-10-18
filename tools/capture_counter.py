import ctypes
import time
import os
from ctypes import wintypes
from PIL import Image

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32

try:
    hdesk = user32.OpenDesktopW('Default', 0, False, 0x01FF)
    if hdesk:
        user32.SetThreadDesktop(hdesk)
except Exception as e:
    print("OpenDesktop err:", e)

# 피카 창 찾아서 포그라운드 활성화
WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
pica_hwnd = None

def enum_windows(h, lp):
    global pica_hwnd
    if user32.IsWindowVisible(h):
        buf = ctypes.create_unicode_buffer(512)
        user32.GetWindowTextW(h, buf, 512)
        title = buf.value
        if 'picalive' in title.lower() or '피카' in title:
            pica_hwnd = h
            return False
    return True

user32.EnumWindows(WNDENUMPROC(enum_windows), 0)

if pica_hwnd:
    print(f"Found Pica window: HWND {pica_hwnd}")
    user32.ShowWindow(pica_hwnd, 3) # SW_MAXIMIZE
    user32.SetForegroundWindow(pica_hwnd)
    user32.BringWindowToTop(pica_hwnd)
    time.sleep(0.5)
else:
    print("Pica window not found by title, capturing current desktop")

width = user32.GetSystemMetrics(0)
height = user32.GetSystemMetrics(1)
if width <= 0 or height <= 0:
    width, height = 1920, 1080

hdc_screen = user32.GetDC(0)
hdc_mem = gdi32.CreateCompatibleDC(hdc_screen)
hbm = gdi32.CreateCompatibleBitmap(hdc_screen, width, height)
gdi32.SelectObject(hdc_mem, hbm)

gdi32.BitBlt(hdc_mem, 0, 0, width, height, hdc_screen, 0, 0, 0x00CC0020 | 0x40000000)

class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ('biSize', wintypes.DWORD),
        ('biWidth', wintypes.LONG),
        ('biHeight', wintypes.LONG),
        ('biPlanes', wintypes.WORD),
        ('biBitCount', wintypes.WORD),
        ('biCompression', wintypes.DWORD),
        ('biSizeImage', wintypes.DWORD),
        ('biXPelsPerMeter', wintypes.LONG),
        ('biYPelsPerMeter', wintypes.LONG),
        ('biClrUsed', wintypes.DWORD),
        ('biClrImportant', wintypes.DWORD),
    ]

bmi = BITMAPINFOHEADER()
bmi.biSize = ctypes.sizeof(BITMAPINFOHEADER)
bmi.biWidth = width
bmi.biHeight = -height
bmi.biPlanes = 1
bmi.biBitCount = 32

buf = ctypes.create_string_buffer(width * height * 4)
gdi32.GetDIBits(hdc_mem, hbm, 0, height, buf, ctypes.byref(bmi), 0)

im = Image.frombuffer('RGBA', (width, height), buf, 'raw', 'BGRA', 0, 1).convert('RGB')
art_dir = r'C:\Users\USER\.gemini\antigravity\brain\873170df-e274-4167-9f52-81820d74701b\artifacts'
os.makedirs(art_dir, exist_ok=True)
out_file = os.path.join(art_dir, 'counter_pica_latest.jpg')
im.save(out_file, 'JPEG', quality=95)
print(f'Successfully saved latest counter screen to: {out_file} ({width}x{height})')

# 좌석 그리드 줌 크롭
try:
    zoom_crop = im.crop((550, 200, 1400, 750))
    zoom_file = os.path.join(art_dir, 'pica_seats_latest_zoom.jpg')
    zoom_crop.save(zoom_file, 'JPEG', quality=95)
    print(f'Successfully saved zoom crop to: {zoom_file}')
except Exception as e:
    print('Zoom crop error:', e)

gdi32.DeleteObject(hbm)
gdi32.DeleteDC(hdc_mem)
user32.ReleaseDC(0, hdc_screen)
