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

    def get_viewer_count(self, client_id: str) -> int:
        return len(self.viewers.get(client_id, set()))

    async def broadcast_frame(self, client_id: str, frame_base64: str):
        """단일 client_id에 등록된 뷰어에게 프레임 전송"""
        await self.broadcast_frame_to_targets([client_id], frame_base64)

    async def broadcast_frame_to_targets(self, target_ids: list, frame_base64: str):
        """다중 식별자(좌석ID, 호스트명, 세션키)에 등록된 모든 뷰어에게 중복 없이 안전하게 1회만 프레임 전송"""
        unique_viewers = set()
        for tid in target_ids:
            if tid and tid in self.viewers:
                unique_viewers.update(self.viewers[tid])

        if not unique_viewers:
            return

        dead_sockets = set()
        import json
        msg = json.dumps({"frame": frame_base64, "dpr": 1.0})
        for ws in unique_viewers:
            try:
                await ws.send_text(msg)
            except Exception as e:
                logger.warning(f"🚨 [RemoteRelay] 뷰어({ws.client}) 프레임 송신 실패 ({type(e).__name__}): {e}")
                dead_sockets.add(ws)

        if dead_sockets:
            for tid in list(self.viewers.keys()):
                for dead in dead_sockets:
                    self.remove_viewer(tid, dead)

