# -*- coding: utf-8 -*-
r"""
?쒖슦??제우스 HDD PROTECTOR - 怨듯넻 ?섍꼍?ㅼ젙 紐⑤뱢
G:\???쒕씪?대툕\PROJECT\HDDGOD\common\config.py
"""
import os
import configparser

import sys

candidates = []
if getattr(sys, 'frozen', False):
    exe_dir = os.path.dirname(sys.executable)
    candidates.append(os.path.join(exe_dir, "config.ini"))
    candidates.append(os.path.join(exe_dir, "deploy", "ClientDeploy", "core", "config.ini"))
    candidates.append(os.path.join(os.path.dirname(exe_dir), "deploy", "ClientDeploy", "core", "config.ini"))
    candidates.append(r"C:\ZeusAgent\config.ini")
    candidates.append(r"C:\ZeusAgent\core\config.ini")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
candidates.append(os.path.join(BASE_DIR, "deploy", "ClientDeploy", "core", "config.ini"))
candidates.append(r"C:\Users\USER\Documents\HDDGOD\deploy\ClientDeploy\core\config.ini")

CONFIG_PATH = next((p for p in candidates if os.path.exists(p)), candidates[0])

config = configparser.ConfigParser()

# 湲곕낯媛?
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
    'CHROME_CDP_PORT': '9222',
    'START_URL': 'https://www.netflix.com',
    'PROFILE_DIR': r'C:\ProgramData\NetflixProfile',
    'EMAIL': 'eunpa23@naver.com',
    'PASSWORD': '@Oep0325'
}

# 서버 전용: 넷플릭스 다중 계정 풀 (콤마로 구분하여 여러 개 등록 가능, ID|PW 형태)
config['NETFLIX_ACCOUNTS'] = {
    'ACCOUNTS': 'eunpa23@naver.com|@Oep0325'
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

# ?몃━??蹂???몄텧
SERVER_HOST = config.get('SERVER', 'SERVER_HOST', fallback='0.0.0.0')
SERVER_PORT = config.getint('SERVER', 'SERVER_PORT', fallback=8000)

CLIENT_SERVER_IP = config.get('CLIENT', 'SERVER_IP', fallback='192.168.0.100')
CLIENT_SERVER_PORT = config.getint('CLIENT', 'SERVER_PORT', fallback=8000)
HEARTBEAT_INTERVAL = config.getint('CLIENT', 'HEARTBEAT_INTERVAL', fallback=3)
ADMIN_PASSWORD = config.get('CLIENT', 'ADMIN_PASSWORD', fallback='1234')



CHROME_CDP_PORT = config.getint('NETFLIX', 'CHROME_CDP_PORT', fallback=9222)
NETFLIX_PROFILE_DIR = config.get('NETFLIX', 'PROFILE_DIR', fallback=r'C:\ProgramData\NetflixProfile')

# ?ㅼ씠踰?硫붿씪 湲곕컲 4?먮━ OTP ?먮룞 異붿텧 ?ㅼ젙
OTP_MAIL_SERVER = config.get('OTP_MAIL', 'IMAP_SERVER', fallback='imap.naver.com')
OTP_MAIL_PORT = config.getint('OTP_MAIL', 'IMAP_PORT', fallback=993)
OTP_MAIL_EMAIL = config.get('OTP_MAIL', 'EMAIL', fallback='eunpa23@naver.com')
OTP_MAIL_PASSWORD = config.get('OTP_MAIL', 'PASSWORD', fallback='UDT766M1ZSCP')

# ?섏쐞 ?명솚
NATE_EMAIL = OTP_MAIL_EMAIL
NATE_PASSWORD = OTP_MAIL_PASSWORD
NATE_IMAP_SERVER = OTP_MAIL_SERVER
NATE_IMAP_PORT = OTP_MAIL_PORT

DEFAULT_VOLUME = config.getint('POWER_POLICY', 'DEFAULT_VOLUME_PERCENT', fallback=100)

# Telegram Alerts
TELEGRAM_BOT_TOKEN = config.get('TELEGRAM', 'BOT_TOKEN', fallback='')
TELEGRAM_CHAT_ID = config.get('TELEGRAM', 'CHAT_ID', fallback='')
TELEGRAM_ALERT_THRESHOLD = config.getint('TELEGRAM', 'ALERT_THRESHOLD_PERCENT', fallback=85)

# Server Account Pool parsing
try:
    _acc_str = config.get('NETFLIX_ACCOUNTS', 'ACCOUNTS', fallback='eunpa23@naver.com|@Oep0325')
    NETFLIX_ACCOUNT_POOL = []
    for pair in _acc_str.split(','):
        if '|' in pair:
            em, pw = pair.strip().split('|', 1)
            NETFLIX_ACCOUNT_POOL.append({'email': em.strip(), 'password': pw.strip()})
except Exception:
    NETFLIX_ACCOUNT_POOL = [{'email': 'eunpa23@naver.com', 'password': '@Oep0325'}]


