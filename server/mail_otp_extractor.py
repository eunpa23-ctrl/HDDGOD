# -*- coding: utf-8 -*-
r"""
제우스 HDD PROTECTOR - 메일함(네이버/네이트) 4자리 OTP 실시간 자동 추출 모듈
G:\내 드라이브\PROJECT\HDDGOD\server\mail_otp_extractor.py
"""
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import imaplib
import email
from email.header import decode_header
import re
import time
import asyncio
import logging
from common.config import (
    OTP_MAIL_SERVER, OTP_MAIL_PORT, OTP_MAIL_EMAIL, OTP_MAIL_PASSWORD
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MailOTPExtractor")

class NateMailOTPExtractor:
    """메일함(IMAP)에 접속하여 넷플릭스 4자리 로그인 코드를 실시간 자동 추출"""

    def __init__(self):
        self.server = OTP_MAIL_SERVER
        self.port = OTP_MAIL_PORT
        self.user = OTP_MAIL_EMAIL
        self.password = OTP_MAIL_PASSWORD

    def _decode_str(self, s) -> str:
        if not s:
            return ""
        try:
            dh = decode_header(s)
            res = ""
            for part, enc in dh:
                if isinstance(part, bytes):
                    res += part.decode(enc or 'utf-8', errors='ignore')
                else:
                    res += str(part)
            return res
        except Exception:
            return str(s)

    def _get_body_text(self, msg) -> str:
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_dispo = str(part.get('Content-Disposition'))
                if content_type == 'text/plain' and 'attachment' not in content_dispo:
                    try:
                        body += part.get_payload(decode=True).decode('utf-8', errors='ignore')
                    except Exception:
                        pass
                elif content_type == 'text/html' and not body and 'attachment' not in content_dispo:
                    try:
                        body += part.get_payload(decode=True).decode('utf-8', errors='ignore')
                    except Exception:
                        pass
        else:
            try:
                body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
            except Exception:
                body = str(msg.get_payload())
        return body

    def _search_inbox_for_otp(self, mail: imaplib.IMAP4_SSL) -> str:
        """현재 열린 IMAP 세션에서 최신 넷플릭스 4자리 OTP 검색"""
        try:
            mail.select("INBOX")
            status, messages = mail.search(None, 'ALL')
            if status != "OK" or not messages[0]:
                return ""

            mail_ids = messages[0].split()
            # 가장 최근 20개 메일 역순 검사
            for m_id in reversed(mail_ids[-20:]):
                _, msg_data = mail.fetch(m_id, '(RFC822)')
                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])
                        subject = self._decode_str(msg.get("Subject", ""))
                        sender = self._decode_str(msg.get("From", ""))
                        body = self._get_body_text(msg)

                        # 넷플릭스 발신 및 로그인 코드 관련 메일 확인
                        is_netflix = ("netflix" in sender.lower() or "netflix" in subject.lower() or "넷플릭스" in subject)
                        is_code_mail = ("로그인 코드" in subject or "임시 접속 코드" in subject or "인증 코드" in subject or "코드를 입력하고" in body)

                        if is_netflix and is_code_mail:
                            logger.info(f"넷플릭스 인증 메일 발견! 제목: {subject}")

                            # 1순위: 넷플릭스 공식 형식 (한 줄 단독 4자리 숫자, 예: \n3579\n)
                            line_matches = re.findall(r'^\s*([0-9]{4})\s*$', body, re.MULTILINE)
                            if line_matches:
                                otp = line_matches[0]
                                logger.info(f"🎉 넷플릭스 4자리 인증코드 정밀 추출 성공: [{otp}]")
                                return otp

                            # 2순위: '코드' 키워드 근처의 4자리 숫자 매칭
                            keyword_matches = re.findall(r'(?:코드|번호|code|login)[^\d]{0,25}(\b[0-9]{4}\b)', body, re.IGNORECASE)
                            if keyword_matches:
                                otp = keyword_matches[0]
                                logger.info(f"🎉 키워드 매칭 4자리 코드 추출 성공: [{otp}]")
                                return otp

                            # 3순위: 일반 4자리 숫자 (전화번호 0161, 연도 2026 등 제외)
                            candidates = re.findall(r'\b([0-9]{4})\b', body)
                            filtered = [c for c in candidates if c not in ["0161", "2026", "2025", "2024"]]
                            if filtered:
                                otp = filtered[0]
                                logger.info(f"🎉 4자리 후보군 추출 성공: [{otp}]")
                                return otp
        except Exception as e:
            logger.debug(f"IMAP 검색 중 오류: {e}")
        return ""

    def find_latest_netflix_otp_sync(self) -> str:
        """단발성 1회 메일함 조회 (기존 호환성 유지)"""
        mail = None
        try:
            logger.info(f"메일함 IMAP({self.server}:{self.port}) 접속 시도: {self.user}")
            mail = imaplib.IMAP4_SSL(self.server, self.port, timeout=10)
            mail.login(self.user, self.password)
            return self._search_inbox_for_otp(mail)
        except Exception as e:
            logger.error(f"메일함 IMAP 조회 중 오류: {e}")
            return ""
        finally:
            if mail:
                try:
                    mail.logout()
                except Exception:
                    pass

    async def poll_netflix_otp(self, timeout_sec: int = 40, interval_sec: int = 2) -> str:
        """단일 세션을 유지하며 최대 timeout_sec 동안 메일 감시 (Rate Limit 및 계정 차단 방지)"""
        start_time = time.time()
        logger.info(f"메일함 4자리 OTP 단일 세션 실시간 감시 시작 (최대 {timeout_sec}초 대기)...")

        def _poll_sync():
            mail = None
            try:
                mail = imaplib.IMAP4_SSL(self.server, self.port, timeout=10)
                mail.login(self.user, self.password)
                while time.time() - start_time < timeout_sec:
                    otp = self._search_inbox_for_otp(mail)
                    if otp:
                        return otp
                    time.sleep(interval_sec)
                    try:
                        mail.noop()
                    except Exception:
                        pass
            except Exception as e:
                logger.error(f"메일함 실시간 폴링 중 오류: {e}")
            finally:
                if mail:
                    try:
                        mail.logout()
                    except Exception:
                        pass
            return ""

        otp = await asyncio.to_thread(_poll_sync)
        if otp:
            return otp

        logger.warning(f"메일함 {timeout_sec}초 초과: 신규 넷플릭스 인증 메일 수신 대기 시간 종료")
        return ""

# 하위 호환 별칭
MailOTPExtractor = NateMailOTPExtractor

if __name__ == "__main__":
    extractor = NateMailOTPExtractor()
    code = extractor.find_latest_netflix_otp_sync()
    print("최신 추출된 코드:", code)
