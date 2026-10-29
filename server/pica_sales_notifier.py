# -*- coding: utf-8 -*-
"""
피카 매니저 실시간 손님 입퇴실 & 결제 금액 감지 및 자정 마감 보고서 발송 모듈
- 손님 로그인 감지: 좌석(1~8번) LOCKED/OFFLINE -> USING 전이 시 결제 금액 차액 계산 후 텔레그램 발송
- 손님 로그아웃 감지: 좌석 USING -> LOCKED/OFFLINE 전이 시 텔레그램 발송
- 자정 직전(23:59) 일일 마감: 피카 [보고서] 탭 자동 캡처 후 사진 + 종합합계 텔레그램 전송
"""

import os
import sys
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
import time
import asyncio
import logging
import ctypes
from ctypes import wintypes
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
from PIL import ImageGrab
import requests

from common.config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from server.pica_counter_controller import ensure_desktop, get_pica_hwnd, get_counter_seat_states, _action_lock

logger = logging.getLogger("PicaSalesNotifier")
user32 = ctypes.windll.user32

# 탭 버튼 화면 좌표 (1920x1080 기준)
TAB_COORDS = {
    "STORE": (310, 65),   # [매장관리]
    "REPORT": (750, 65),  # [보고서]
}

def get_pica_vault_amounts() -> Dict[str, int]:
    """
    피카 매니저 하단 상태표시줄 Win32 컨트롤에서 실시간 금고 잔액 추출
    - counter: 카운터 금고 (예: 641,200)
    - kiosk: 판매기기(선불기) 금고 (예: 6,107,000)
    - total: 총 합계 (예: 6,748,200)
    """
    ensure_desktop()
    pica = get_pica_hwnd()
    if not pica:
        return {"counter": 0, "kiosk": 0, "total": 0}

    amounts = {"counter": 0, "kiosk": 0, "total": 0}

    def enum_bottom(h, lp):
        r = wintypes.RECT()
        user32.GetWindowRect(h, ctypes.byref(r))
        # 하단 상태표시줄 영역 (y: 1000~1035)
        if 1000 <= r.top <= 1035:
            length = user32.GetWindowTextLengthW(h)
            if length > 0:
                buf = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(h, buf, length + 1)
                txt = buf.value.replace(",", "").strip()
                if txt.isdigit():
                    val = int(txt)
                    # 위치에 따라 구분 (x좌표 기준)
                    # 450 <= x <= 620: 카운터 금고
                    # 680 <= x <= 850: 판매기기 금고
                    # 880 <= x <= 1020: 합계 금고
                    center_x = (r.left + r.right) // 2
                    if 450 <= center_x <= 630 and amounts["counter"] == 0:
                        amounts["counter"] = val
                    elif 680 <= center_x <= 850 and amounts["kiosk"] == 0:
                        amounts["kiosk"] = val
                    elif 880 <= center_x <= 1030 and amounts["total"] == 0:
                        amounts["total"] = val
        return True

    W = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_size_t, ctypes.c_size_t)
    user32.EnumChildWindows(pica, W(enum_bottom), 0)

    # total이 0이고 counter/kiosk가 있으면 합산 보정
    if amounts["total"] == 0 and (amounts["counter"] > 0 or amounts["kiosk"] > 0):
        amounts["total"] = amounts["counter"] + amounts["kiosk"]

    return amounts

REPORT_DIGIT_TEMPLATES = {
    '0': ['.####.', '##..##', '##..##', '##..##', '##..##', '##..##', '##..##', '##..##', '##..##', '.####.'],
    '1': ['.##', '###', '.##', '.##', '.##', '.##', '.##', '.##', '.##', '.##'],
    '2': ['.####.', '##..##', '##..##', '....##', '...##.', '..##..', '.##...', '##....', '##....', '######'],
    '3': ['.####.', '##..##', '....##', '....##', '.####.', '....##', '....##', '....##', '##..##', '.####.'],
    '4': ['...##.', '..###.', '..###.', '.##.##', '.##.##', '##..##', '##..##', '######', '...##.', '...##.'],
    '5': ['######', '##....', '##....', '##....', '#####.', '##..##', '....##', '....##', '##..##', '.####.'],
    '6': ['.####.', '##..##', '##....', '##....', '#####.', '##..##', '##..##', '##..##', '##..##', '.####.'],
    '7': ['######', '....##', '....##', '...##.', '...##.', '...##.', '..##..', '..##..', '..##..', '..##..'],
    '8': ['.####.', '##..##', '##..##', '##..##', '.####.', '##..##', '##..##', '##..##', '##..##', '.####.'],
    '9': ['.####.', '##..##', '##..##', '##..##', '##..##', '.#####', '....##', '....##', '##..##', '.####.'],
}

def parse_report_amount_from_image(im) -> int:
    """피카 [보고서] 화면 캡처에서 '오늘매출 종합합계' 금액을 도트 매칭으로 정확히 파싱"""
    try:
        # 종합합계 금액 좌표 영역: x: 920~1000, y: 175~198 (1920x1080 기준)
        crop = im.crop((920, 175, 1000, 198)).convert('L')
        w, h = crop.size
        cols = [any(crop.getpixel((x, y)) < 128 for y in range(h)) for x in range(w)]
        segments = []
        in_seg = False
        start_x = 0
        for x in range(w):
            if cols[x] and not in_seg:
                in_seg = True
                start_x = x
            elif not cols[x] and in_seg:
                in_seg = False
                segments.append((start_x, x - 1))
        if in_seg:
            segments.append((start_x, w - 1))

        parsed = []
        for sx, ex in segments:
            seg_w = ex - sx + 1
            lines = []
            for y in range(h):
                row = ''.join('#' if crop.getpixel((x, y)) < 128 else '.' for x in range(sx, ex + 1))
                if '#' in row:
                    lines.append(row)
            if len(lines) <= 3:  # 쉼표(,) 건너뛰기
                continue
            best_ch = '?'
            best_diff = 999
            for ch, tmpl in REPORT_DIGIT_TEMPLATES.items():
                th, tw = len(tmpl), len(tmpl[0])
                diff = sum(
                    1 for r in range(max(len(lines), th)) for c in range(max(seg_w, tw))
                    if (lines[r][c] if r < len(lines) and c < seg_w else '.') != (tmpl[r][c] if r < th and c < tw else '.')
                )
                if diff < best_diff:
                    best_diff = diff
                    best_ch = ch
            if best_diff <= 15:
                parsed.append(best_ch)
        res = ''.join(parsed)
        return int(res) if res.isdigit() else 0
    except Exception as e:
        logger.error(f"보고서 금액 파싱 오류: {e}")
        return 0

def get_today_total_sales() -> int:
    """
    피카 매니저 [보고서] 탭에서 오늘 실제 '종합합계 총매출' 실시간 추출
    - [보고서] 탭으로 0.3초 순간 전환 후 캡처 및 파싱, 즉시 [매장관리] 좌석 화면으로 복귀
    """
    with _action_lock:
        ensure_desktop()
        pica = get_pica_hwnd()
        if not pica:
            return 0

        orig_pt = wintypes.POINT()
        user32.GetCursorPos(ctypes.byref(orig_pt))
        try:
            user32.keybd_event(0x12, 0, 0, 0); user32.keybd_event(0x12, 0, 2, 0)
            user32.ShowWindow(pica, 9)
            user32.ShowWindow(pica, 3)
            user32.SetForegroundWindow(pica)
            user32.BringWindowToTop(pica)
            time.sleep(0.15)
            click_coords(*TAB_COORDS['REPORT'])
            time.sleep(0.3)
            im = ImageGrab.grab()
            click_coords(*TAB_COORDS['STORE'])
            val = parse_report_amount_from_image(im)
            logger.info(f"피카 [보고서] 실시간 오늘 총매출 추출 성공: {val:,}원")
            return val
        except Exception as e:
            logger.error(f"오늘 총매출 추출 오류: {e}")
            return 0
        finally:
            user32.SetCursorPos(orig_pt.x, orig_pt.y)

def click_coords(x: int, y: int):
    """지정 좌표 마우스 클릭"""
    user32.SetCursorPos(x, y)
    time.sleep(0.04)
    user32.mouse_event(2, 0, 0, 0, 0) # LEFTDOWN
    time.sleep(0.04)
    user32.mouse_event(4, 0, 0, 0, 0) # LEFTUP
    time.sleep(0.08)

def capture_and_send_daily_closing() -> bool:
    """
    [자정 23:59 일일 마감] 피카 [보고서] 탭 자동 캡처 및 텔레그램 전송
    - 카운터 화면을 안전하게 [보고서] 탭으로 전환 후 캡처
    - 캡처 즉시 [매장관리] 좌석 화면으로 원복
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("텔레그램 설정(BOT_TOKEN, CHAT_ID)이 없어 마감 보고서를 발송할 수 없습니다.")
        return False

    with _action_lock:
        ensure_desktop()
        pica = get_pica_hwnd()
        if not pica:
            logger.error("피카 윈도우를 찾을 수 없어 마감 보고서를 생성할 수 없습니다.")
            return False

        orig_pt = wintypes.POINT()
        user32.GetCursorPos(ctypes.byref(orig_pt))

        try:
            # 1. 창 활성화
            is_iconic = user32.IsIconic(pica)
            user32.keybd_event(0x12, 0, 0, 0); user32.keybd_event(0x12, 0, 2, 0)
            user32.ShowWindow(pica, 9)
            user32.ShowWindow(pica, 3)
            user32.SetForegroundWindow(pica)
            user32.BringWindowToTop(pica)
            time.sleep(0.3)

            # 2. [보고서] 탭 클릭
            click_coords(*TAB_COORDS["REPORT"])
            time.sleep(0.6)

            # 3. 고화질 캡처 (매출현황 + 오늘매출 종합합계 테이블)
            full_img = ImageGrab.grab()
            summary_crop = full_img.crop((0, 35, 1050, 520))
            os.makedirs("scratch", exist_ok=True)
            save_path = "scratch/daily_closing_report.png"
            summary_crop.save(save_path)

            # 4. 원래 화면인 [매장관리] 탭으로 즉시 복귀
            click_coords(*TAB_COORDS["STORE"])
            time.sleep(0.3)

            # 5. 오늘 총매출 확인
            today_sales = get_today_total_sales()

            # 6. 텔레그램 발송
            now_str = datetime.now().strftime("%Y년 %m월 %d일 %H:%M")
            caption = (
                f"📊 [제우스 PC방 일일 최종 마감 보고서]\n"
                f"⏰ 마감 일시: {now_str}\n"
                f"🏢 대상: 피카 매니저 카운터\n"
                f"────────────────\n"
                f"💵 오늘 총매출: {today_sales:,}원\n"
                f"────────────────\n"
                f"※ 오늘 하루 상세 종합 매출은 첨부된 화면 캡처를 확인해 주세요."
            )

            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
            with open(save_path, "rb") as f:
                resp = requests.post(
                    url,
                    data={"chat_id": TELEGRAM_CHAT_ID, "caption": caption},
                    files={"photo": f},
                    timeout=10
                )
                if resp.status_code == 200:
                    logger.info("✅ 일일 마감 보고서 텔레그램 발송 성공!")
                    return True
                else:
                    logger.error(f"❌ 마감 보고서 텔레그램 발송 실패: {resp.text}")
                    return False
        except Exception as e:
            logger.error(f"마감 보고서 실행 중 예외 발생: {e}")
            return False
        finally:
            user32.SetCursorPos(orig_pt.x, orig_pt.y)

def send_telegram_text(msg: str):
    """동기식 텔레그램 단문 텍스트 발송"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("텔레그램 설정 누락으로 발송 생략")
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        resp = requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": msg}, timeout=5)
        if resp.status_code == 200:
            logger.info(f"✅ 텔레그램 발송 성공: {msg.splitlines()[0]}")
        else:
            logger.error(f"❌ 텔레그램 발송 실패 ({resp.status_code}): {resp.text}")
    except Exception as e:
        logger.error(f"텔레그램 발송 오류: {e}")

class PicaSalesNotifier:
    """피카 실시간 손님 입퇴실 & 결제 금액 & 자정 마감 통합 감시 데몬"""
    def __init__(self):
        self.prev_seat_states: Dict[int, str] = {}
        self.last_total_vault: int = 0
        self.last_closing_date: str = ""
        self.is_running: bool = False

    def init_baseline(self):
        """초기 상태 및 기준 금고 잔액 동기화"""
        try:
            self.prev_seat_states = get_counter_seat_states()
            vaults = get_pica_vault_amounts()
            self.last_total_vault = vaults.get("total", 0)
            today_sales = get_today_total_sales()
            logger.info(f"피카 감시 데몬 초기화 완료: 좌석상태={self.prev_seat_states}, 기준금고={self.last_total_vault:,}원, 오늘총매출={today_sales:,}원")
        except Exception as e:
            logger.error(f"초기화 예외: {e}")

    async def run_loop(self):
        """비동기 실시간 감시 메인 루프 (약 2.5초 주기)"""
        self.is_running = True
        self.init_baseline()
        logger.info("🚀 피카 실시간 손님 입퇴실 & 결제 금액 감시 루프 시작")

        while self.is_running:
            try:
                now = datetime.now()
                today_str = now.strftime("%Y-%m-%d")

                # 1. [자정 23:59 일일 마감 체크] (23시 59분에 하루 1회 실행)
                if now.hour == 23 and now.minute == 59 and self.last_closing_date != today_str:
                    logger.info("⏰ 23:59 자정 마감 시간 도달! 일일 마감 보고서 발송 시작")
                    success = await asyncio.to_thread(capture_and_send_daily_closing)
                    if success:
                        self.last_closing_date = today_str
                    await asyncio.sleep(5)
                    continue

                # 2. [실시간 좌석 상태 변화 확인]
                current_states = await asyncio.to_thread(get_counter_seat_states)
                if current_states and self.prev_seat_states:
                    for seat, cur_st in current_states.items():
                        prev_st = self.prev_seat_states.get(seat, "LOCKED")

                        # A. [손님 로그인 감지]: LOCKED/OFFLINE -> USING
                        if prev_st in ("LOCKED", "OFFLINE") and cur_st == "USING":
                            logger.info(f"🔔 [좌석 {seat}번] 손님 로그인 감지! ({prev_st} -> USING)")
                            # 선불기/카운터 결제 데이터 피카 창 반영 대기 (1.5초)
                            await asyncio.sleep(1.5)
                            new_vaults = await asyncio.to_thread(get_pica_vault_amounts)
                            curr_total = new_vaults.get("total", 0)

                            delta = 0
                            if self.last_total_vault > 0 and curr_total > self.last_total_vault:
                                delta = curr_total - self.last_total_vault
                            elif self.last_total_vault > 0 and curr_total <= self.last_total_vault:
                                # 결제가 1초 정도 더 늦게 들어오는 경우 대비 (추가 1.5초 후 재확인)
                                await asyncio.sleep(1.5)
                                retry_vaults = await asyncio.to_thread(get_pica_vault_amounts)
                                retry_total = retry_vaults.get("total", 0)
                                if retry_total > self.last_total_vault:
                                    curr_total = retry_total
                                    delta = curr_total - self.last_total_vault

                            today_sales = await asyncio.to_thread(get_today_total_sales)
                            now_time = datetime.now().strftime("%H:%M:%S")

                            if delta > 0:
                                msg = (
                                    f"🟢 [PC {seat}번] 손님 로그인\n"
                                    f"💳 결제 금액: {delta:,}원\n"
                                    f"⏰ 시간: {now_time}\n"
                                    f"💵 오늘 총매출: {today_sales:,}원"
                                )
                                self.last_total_vault = curr_total
                            else:
                                msg = (
                                    f"🟢 [PC {seat}번] 손님 로그인\n"
                                    f"⏰ 시간: {now_time} (기존 잔여시간 이용 또는 정액제)\n"
                                    f"💵 오늘 총매출: {today_sales:,}원"
                                )
                                if curr_total > 0:
                                    self.last_total_vault = curr_total

                            await asyncio.to_thread(send_telegram_text, msg)

                        # B. [손님 로그아웃 감지]: USING -> LOCKED/OFFLINE
                        elif prev_st == "USING" and cur_st in ("LOCKED", "OFFLINE"):
                            logger.info(f"🔔 [좌석 {seat}번] 손님 로그아웃 감지! (USING -> {cur_st})")
                            now_time = datetime.now().strftime("%H:%M:%S")
                            msg = (
                                f"🔴 [PC {seat}번] 손님 이용 종료 (로그아웃)\n"
                                f"⏰ 이용 종료 시간: {now_time}"
                            )
                            await asyncio.to_thread(send_telegram_text, msg)

                    self.prev_seat_states = current_states

            except Exception as e:
                logger.error(f"감시 루프 오류: {e}")

            await asyncio.sleep(2.5)

pica_sales_notifier = PicaSalesNotifier()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    # 금고 잔액 추출 테스트
    vaults = get_pica_vault_amounts()
    print("현재 금고 잔액:", vaults)
    # 23:59 마감 보고서 발송 테스트
    # capture_and_send_daily_closing()
