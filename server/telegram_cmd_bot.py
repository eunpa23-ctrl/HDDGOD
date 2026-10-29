# -*- coding: utf-8 -*-
"""
제우스 관제 서버 - 텔레그램 양방향 원격 명령 수신 데몬
- 사장님 텔레그램 계정(CHAT_ID)에서 온 메시지만 안전하게 수신 및 처리
- 지원 명령어:
  1. 매출 / 오늘매출 / 보고서: 오늘 총매출 금액 회신 및 최신 화면 요약 사진 전송
  2. 좌석 / 상태: 손님 좌석(1~8번) 실시간 상태 (사용중/대기중/꺼짐) 회신
  3. 화면 / 캡처: 카운터 실시간 화면 캡처 전송
  4. N번 켜 / N번 재부팅 / N번 꺼: 지정 좌석 원격 전원 제어
  5. 도움말 / 명령어: 사용 가능한 명령어 안내
"""

import os
import sys
import time
import asyncio
import logging
import requests
from typing import Optional
from PIL import ImageGrab

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from common.config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from server.pica_counter_controller import get_counter_seat_states
from server.pica_sales_notifier import get_today_total_sales, capture_and_send_daily_closing, send_telegram_text

logger = logging.getLogger("TelegramBotDaemon")

class TelegramCommandBot:
    def __init__(self):
        self.bot_token = TELEGRAM_BOT_TOKEN
        self.chat_id = str(TELEGRAM_CHAT_ID)
        self.last_update_id = 0
        self.is_running = False

    def send_photo(self, photo_path: str, caption: str = ""):
        if not self.bot_token or not self.chat_id:
            return
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendPhoto"
            with open(photo_path, "rb") as f:
                requests.post(url, data={"chat_id": self.chat_id, "caption": caption}, files={"photo": f}, timeout=10)
        except Exception as e:
            logger.error(f"텔레그램 사진 전송 오류: {e}")

    def capture_screen_and_send(self, caption: str = "🖥️ [카운터 현재 실시간 화면]"):
        try:
            img = ImageGrab.grab()
            os.makedirs("scratch", exist_ok=True)
            path = "scratch/telegram_snap.png"
            img.save(path)
            self.send_photo(path, caption)
        except Exception as e:
            logger.error(f"화면 캡처 전송 오류: {e}")
            send_telegram_text(f"❌ 화면 캡처 실패: {e}")

    async def handle_command(self, text: str):
        text = text.strip()
        logger.info(f"📩 텔레그램 명령 수신: '{text}'")

        # 1. 매출 / 오늘매출
        if any(k in text for k in ["매출", "오늘매출", "얼마"]):
            sales = get_today_total_sales()
            msg = (
                f"💵 [제우스 오늘 매출 현황]\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"💰 오늘 총매출: {sales:,}원\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"※ 자세한 내역표가 필요하시면 '보고서'라고 입력해 주세요."
            )
            send_telegram_text(msg)

        # 2. 보고서
        elif "보고서" in text or "마감" in text:
            send_telegram_text("⏳ 피카 보고서 화면을 확인 중입니다. 잠시만 기다려주세요...")
            await asyncio.to_thread(capture_and_send_daily_closing)

        # 3. 좌석 / 상태
        elif any(k in text for k in ["좌석", "상태", "손님"]):
            states = await asyncio.to_thread(get_counter_seat_states)
            if not states:
                send_telegram_text("⚠️ 피카 매니저 좌석 상태를 읽지 못했습니다.")
                return

            lines = ["🪑 [손님 좌석 실시간 상태]", "━━━━━━━━━━━━━━━━━━"]
            using_count = 0
            for seat in sorted(states.keys()):
                st = states[seat]
                if st == "USING":
                    mark = "🟢 이용중"
                    using_count += 1
                elif st == "LOCKED":
                    mark = "⚪ 대기중"
                else:
                    mark = "🔴 꺼짐/오프라인"
                lines.append(f"• PC {seat}번: {mark}")

            lines.append("━━━━━━━━━━━━━━━━━━")
            lines.append(f"총 8대 중 이용 중: {using_count}대")
            send_telegram_text("\n".join(lines))

        # 4. 화면 / 캡처
        elif any(k in text for k in ["화면", "캡처", "스샷", "사진"]):
            send_telegram_text("📸 카운터 실시간 화면을 캡처하여 전송합니다...")
            await asyncio.to_thread(self.capture_screen_and_send)

        # 5. 좌석 원격 제어 (WOL 켜기)
        elif "켜" in text:
            # 예: '1번 켜', '1번켜', '전체 켜'
            import re
            m = re.search(r'(\d+)번?', text)
            if m:
                seat_num = int(m.group(1))
                from server.server_core import watchdog
                watchdog.wake_pc(seat_num)
                send_telegram_text(f"⚡ [PC {seat_num}번] 전원 켜기(WOL) 신호를 발송했습니다!")
            elif "전체" in text or "모두" in text or "다" in text:
                from server.server_core import watchdog
                for s in range(1, 9):
                    watchdog.wake_pc(s)
                    await asyncio.sleep(0.1)
                send_telegram_text("⚡ [전체 좌석 1~8번] 전원 켜기(WOL) 신호를 발송했습니다!")
            else:
                send_telegram_text("❓ 켜실 좌석 번호를 입력해 주세요. (예: 1번 켜, 전체 켜)")

        # 6. 도움말 / 명령어
        else:
            help_msg = (
                f"🤖 [제우스 관제 텔레그램 명령어 안내]\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"💬 '매출' : 오늘 총매출 금액 확인\n"
                f"📊 '보고서' : 피카 상세 매출표 캡처 전송\n"
                f"🪑 '좌석' : 1~8번 좌석 이용/대기 상태 확인\n"
                f"📸 '화면' : 카운터 실시간 화면 캡처 전송\n"
                f"⚡ '1번 켜' : 해당 PC 원격 부팅 (1~8번, 전체 켜)\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"원하시는 명령을 텍스트로 보내주세요!"
            )
            send_telegram_text(help_msg)

    async def run_loop(self):
        """텔레그램 getUpdates 롱폴링 루프"""
        if not self.bot_token or not self.chat_id:
            logger.warning("텔레그램 토큰 또는 Chat ID 미설정으로 명령 수신 데몬 중단")
            return

        self.is_running = True
        logger.info("🚀 텔레그램 원격 명령 수신 데몬 가동 시작 (사장님 전용)")

        # 기존 밀린 과거 메시지 오프셋 초기화
        try:
            init_url = f"https://api.telegram.org/bot{self.bot_token}/getUpdates?offset=-1"
            res = await asyncio.to_thread(requests.get, init_url, timeout=10)
            if res.status_code == 200:
                updates = res.json().get("result", [])
                if updates:
                    self.last_update_id = updates[-1]["update_id"] + 1
        except Exception as e:
            logger.warning(f"오프셋 초기화 예외: {e}")

        while self.is_running:
            try:
                url = f"https://api.telegram.org/bot{self.bot_token}/getUpdates?offset={self.last_update_id}&timeout=20"
                resp = await asyncio.to_thread(requests.get, url, timeout=25)
                if resp.status_code == 200:
                    data = resp.json()
                    for update in data.get("result", []):
                        self.last_update_id = update["update_id"] + 1
                        msg = update.get("message", {})
                        from_id = str(msg.get("chat", {}).get("id", ""))
                        text = msg.get("text", "")

                        # 사장님 계정 인증 확인
                        if from_id == self.chat_id and text:
                            asyncio.create_task(self.handle_command(text))
                        elif text:
                            logger.warning(f"미인가 사용자 접근 차단: ChatID={from_id}, Text={text}")
                elif resp.status_code != 200:
                    await asyncio.sleep(5)
            except Exception as e:
                # 타임아웃 등 일반적 네트워크 지연은 조용히 넘김
                await asyncio.sleep(3)

telegram_cmd_bot = TelegramCommandBot()
