# -*- coding: utf-8 -*-
r"""
제우스 HDD PROTECTOR - 통신 프로토콜 및 규격 정의
G:\내 드라이브\PROJECT\HDDGOD\common\protocol.py
"""
import json
import time

class PacketType:
    HEARTBEAT = "HEARTBEAT"
    COMMAND = "COMMAND"
    STATUS_UPDATE = "STATUS_UPDATE"
    OTP_REQUIRED = "OTP_REQUIRED"
    OTP_SUBMIT = "OTP_SUBMIT"
    SCREEN_FRAME = "SCREEN_FRAME"
    REMOTE_INPUT = "REMOTE_INPUT"
    ERROR_REPORT = "ERROR_REPORT"
    LOG_STREAM = "LOG_STREAM"
    CREDENTIAL_REQUEST = "CREDENTIAL_REQUEST"
    CREDENTIAL_RESPONSE = "CREDENTIAL_RESPONSE"

class CommandType:
    REBOOT = "REBOOT"
    REBOOT_RECOVER = "REBOOT_RECOVER"
    REBOOT_MAINTENANCE = "REBOOT_MAINTENANCE"
    SHUTDOWN = "SHUTDOWN"
    WOL = "WOL"
    ENABLE_UWF = "ENABLE_UWF"
    DISABLE_UWF = "DISABLE_UWF"
    RESTART_NETFLIX = "RESTART_NETFLIX"
    START_SCREEN_STREAM = "START_SCREEN_STREAM"
    STOP_SCREEN_STREAM = "STOP_SCREEN_STREAM"
    UPDATE_AGENT = "UPDATE_AGENT"

class UWFStatus:
    PROTECTED = "PROTECTED"       # UWF 보호 활성화 (초록 방패)
    MAINTENANCE = "MAINTENANCE"   # 유지보수/해제 모드 (주황 방패)
    DISABLED = "DISABLED"
    UNKNOWN = "UNKNOWN"

class NetflixStatus:
    LOGGED_IN = "LOGGED_IN"       # 정상 로그인 완료
    LOGGED_OUT = "LOGGED_OUT"     # 로그아웃 상태
    OTP_WAITING = "OTP_WAITING"   # 4자리 인증번호 대기 중
    RUNNING = "RUNNING"           # 브라우저 실행 중
    CLOSED = "CLOSED"             # 브라우저 꺼짐
    ERROR = "ERROR"

def make_packet(p_type: str, data: dict) -> str:
    payload = {
        "type": p_type,
        "timestamp": time.time(),
        "data": data
    }
    return json.dumps(payload, ensure_ascii=False)

def parse_packet(raw_json: str) -> dict:
    try:
        return json.loads(raw_json)
    except Exception:
        return {}
