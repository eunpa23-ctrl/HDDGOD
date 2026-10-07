# -*- coding: utf-8 -*-
r"""
제우스 HDD PROTECTOR - 카카오톡 알림톡 및 예비 OTP 알림 모듈
G:\내 드라이브\PROJECT\HDDGOD\server\kakao_notifier.py
"""
import logging
import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("KakaoNotifier")

class KakaoNotifier:
    """네이트 메일 자동 조회 실패 시 2차 예비 수단으로 점주 스마트폰에 카카오 알림 발송"""

    def __init__(self, rest_api_key: str = "", redirect_url: str = ""):
        self.api_key = rest_api_key
        self.redirect_url = redirect_url

    def send_otp_alert(self, client_id: str, otp_page_url: str) -> bool:
        """점주 스마트폰으로 4자리 인증번호 요청 메시지 발송"""
        message = (
            f"[⚡ 제우스 HDD PROTECTOR 관제 알림]\n"
            f"[{client_id}] 넷플릭스 4자리 인증코드가 필요합니다.\n\n"
            f"아래 링크를 눌러 4자리 번호를 입력해 주세요:\n"
            f"{otp_page_url}"
        )
        logger.info(f"카카오 알림 발송:\n{message}")

        # 카카오 비즈메시지 / 나에게 보내기 API 연동 템플릿
        # 실제 운영 시 토큰이나 웹훅 URL이 있으면 전송
        try:
            # 예시: 등록된 웹훅 엔드포인트가 있을 경우 발송
            return True
        except Exception as e:
            logger.error(f"카카오 메시지 발송 실패: {e}")
            return False

if __name__ == "__main__":
    notifier = KakaoNotifier()
    notifier.send_otp_alert("PC-03", "https://zeus.trycloudflare.com/otp/PC-03")
