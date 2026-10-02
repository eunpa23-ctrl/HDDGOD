# -*- coding: utf-8 -*-
r"""
제우스 HDD PROTECTOR - 웹 브라우저/스마트폰 원격 제어 스트리밍 중계기
G:\내 드라이브\PROJECT\HDDGOD\server\remote_relay.py
"""
import logging
from typing import Dict
from fastapi import WebSocket

logger = logging.getLogger("RemoteRelay")

class RemoteRelay:
    """스마트폰 웹 브라우저(Controller)와 클라이언트 PC(Agent) 간 실시간 화면 및 터치 입력 중계"""

    def __init__(self):
        # client_id -> set of viewer WebSockets
        self.viewers: Dict[str, set] = {}

    def add_viewer(self, client_id: str, ws: WebSocket):
        if client_id not in self.viewers:
            self.viewers[client_id] = set()
        self.viewers[client_id].add(ws)
        logger.info(f"원격 뷰어 추가: {client_id} (총 {len(self.viewers[client_id])}명)")

    def remove_viewer(self, client_id: str, ws: WebSocket):
        if client_id in self.viewers and ws in self.viewers[client_id]:
            self.viewers[client_id].remove(ws)
            if not self.viewers[client_id]:
                del self.viewers[client_id]

    async def broadcast_frame(self, client_id: str, frame_base64: str):
        """클라이언트 PC에서 전송된 화면 프레임을 모든 뷰어에게 중계"""
        if client_id not in self.viewers:
            return
        dead_sockets = set()
        msg = frame_base64
        for ws in self.viewers[client_id]:
            try:
                await ws.send_text(msg)
            except Exception:
                dead_sockets.add(ws)
        for dead in dead_sockets:
            self.remove_viewer(client_id, dead)
