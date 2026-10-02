# -*- coding: utf-8 -*-
r"""
제우스 HDD PROTECTOR - 공통 환경설정 모듈
G:\내 드라이브\PROJECT\HDDGOD\common\config.py
"""
import os
import configparser

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE_DIR, "deploy", "ClientDeploy", "core", "config.ini")

config = configparser.ConfigParser()

# 기본값
config['SERVER'] = {
    'SERVER_HOST': '0.0.0.0',
    'SERVER_PORT': '8000',
    'SECRET_KEY': 'zeus_hdd_god_secret_2026'
}

config['CLIENT'] = {
    'SERVER_IP': '192.168.0.100',
    'SERVER_PORT': '8000',
    'HEARTBEAT_INTERVAL': '3',
    'ADMIN_PASSWORD': '1234'
}

config['NETFLIX'] = {
    'EMAIL': '',
    'PASSWORD': '',
    'CHROME_CDP_PORT': '9222',
    'START_URL': 'https://www.netflix.com',
    'PROFILE_DIR': r'C:\ProgramData\NetflixProfile'
}

config['OTP_MAIL'] = {
    'IMAP_SERVER': 'imap.naver.com',
    'IMAP_PORT': '993',
    'EMAIL': '',
    'PASSWORD': '',
    'CHECK_INTERVAL_SEC': '2',
    'TIMEOUT_SEC': '40'
}

config['NATE_MAIL'] = {
    'IMAP_SERVER': 'imap.nate.com',
    'IMAP_PORT': '993',
    'EMAIL': '',
    'PASSWORD': '',
    'CHECK_INTERVAL_SEC': '2',
    'TIMEOUT_SEC': '40'
}

config['POWER_POLICY'] = {
    'AUTO_WOL_AFTER_SEC': '10',
    'FAST_STARTUP_DISABLE': 'true',
    'NO_CLOSE_REGISTRY': 'true',
    'DEFAULT_VOLUME_PERCENT': '100',
    'MONITOR_SLEEP_DISABLE': 'true',
    'DISABLE_WINDOWS_UPDATE_REBOOT': 'true'
}

if os.path.exists(CONFIG_PATH):
    config.read(CONFIG_PATH, encoding='utf-8')

# 편리한 변수 노출
SERVER_HOST = config.get('SERVER', 'SERVER_HOST', fallback='0.0.0.0')
SERVER_PORT = config.getint('SERVER', 'SERVER_PORT', fallback=8000)

CLIENT_SERVER_IP = config.get('CLIENT', 'SERVER_IP', fallback='192.168.0.100')
CLIENT_SERVER_PORT = config.getint('CLIENT', 'SERVER_PORT', fallback=8000)
HEARTBEAT_INTERVAL = config.getint('CLIENT', 'HEARTBEAT_INTERVAL', fallback=3)
ADMIN_PASSWORD = config.get('CLIENT', 'ADMIN_PASSWORD', fallback='1234')

NETFLIX_EMAIL = config.get('NETFLIX', 'EMAIL', fallback='eunpa23@naver.com')
NETFLIX_PASSWORD = config.get('NETFLIX', 'PASSWORD', fallback='@Greendayfe')
CHROME_CDP_PORT = config.getint('NETFLIX', 'CHROME_CDP_PORT', fallback=9222)
NETFLIX_PROFILE_DIR = config.get('NETFLIX', 'PROFILE_DIR', fallback=r'C:\ProgramData\NetflixProfile')

# 네이버 메일 기반 4자리 OTP 자동 추출 설정
OTP_MAIL_SERVER = config.get('OTP_MAIL', 'IMAP_SERVER', fallback='imap.naver.com')
OTP_MAIL_PORT = config.getint('OTP_MAIL', 'IMAP_PORT', fallback=993)
OTP_MAIL_EMAIL = config.get('OTP_MAIL', 'EMAIL', fallback='eunpa23')
OTP_MAIL_PASSWORD = config.get('OTP_MAIL', 'PASSWORD', fallback='UDT766M1ZSCP')

# 하위 호환
NATE_EMAIL = OTP_MAIL_EMAIL
NATE_PASSWORD = OTP_MAIL_PASSWORD
NATE_IMAP_SERVER = OTP_MAIL_SERVER
NATE_IMAP_PORT = OTP_MAIL_PORT

DEFAULT_VOLUME = config.getint('POWER_POLICY', 'DEFAULT_VOLUME_PERCENT', fallback=100)

# Telegram Alerts
TELEGRAM_BOT_TOKEN = config.get('TELEGRAM', 'BOT_TOKEN', fallback='')
TELEGRAM_CHAT_ID = config.get('TELEGRAM', 'CHAT_ID', fallback='')
TELEGRAM_ALERT_THRESHOLD = config.getint('TELEGRAM', 'ALERT_THRESHOLD_PERCENT', fallback=5)
