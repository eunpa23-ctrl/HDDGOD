# -*- coding: utf-8 -*-
r"""
바탕화면 넷플릭스 바로가기 전용 런처
G:\내 드라이브\PROJECT\HDDGOD\client\launch_netflix.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from client.netflix_bot import NetflixBot

if __name__ == "__main__":
    bot = NetflixBot()
    bot.launch_chrome_with_cdp()
