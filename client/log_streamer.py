# -*- coding: utf-8 -*-
"""
제우스 HDD PROTECTOR - 실시간 로그 스트리머
클라이언트의 모든 Python 로그를 WebSocket을 통해 관제 서버 대시보드로 실시간 전송
"""
import logging
import json
import time
import threading


class WebSocketLogHandler(logging.Handler):
    """
    Python logging 시스템에 붙이는 WebSocket 전송 핸들러.
    agent의 ws_conn을 참조해 모든 log 레코드를 LOG_STREAM 패킷으로 전송.

    사용법:
        ws_log_handler = WebSocketLogHandler(agent_ref=self)
        logging.getLogger().addHandler(ws_log_handler)
    """

    def __init__(self, agent_ref, level=logging.DEBUG):
        super().__init__(level)
        self.agent = agent_ref          # ZeusClientAgent 인스턴스 참조
        self._lock = threading.Lock()
        self._queue = []                # ws 연결 전 버퍼 (최대 50개)
        self._max_queue = 50

        # 포맷: [레벨] 메시지
        self.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))

    def emit(self, record: logging.LogRecord):
        """로그 레코드를 WebSocket으로 전송 (비동기 없이 즉시)"""
        try:
            msg = self.format(record)
            payload = {
                "client_id": getattr(self.agent, "client_id", "unknown"),
                "level": record.levelname,
                "message": msg,
                "timestamp": time.strftime("%H:%M:%S"),
                "logger": record.name
            }

            ws = getattr(self.agent, "ws_conn", None)
            if ws:
                # WebSocket 연결 중이면 즉시 전송
                try:
                    from common.protocol import PacketType, make_packet
                    pkt = make_packet(PacketType.LOG_STREAM, payload)
                    # 비동기 send를 스레드 안전하게 호출
                    import asyncio
                    loop = None
                    try:
                        loop = asyncio.get_event_loop()
                    except RuntimeError:
                        pass

                    if loop and loop.is_running():
                        # 이미 asyncio 루프 안이면 create_task로 큐잉
                        loop.call_soon_threadsafe(
                            lambda p=pkt: asyncio.ensure_future(self._send(ws, p))
                        )
                    # 버퍼에 쌓인 것도 함께 비움
                    with self._lock:
                        self._queue.clear()
                except Exception:
                    self._buffer(payload)
            else:
                # WebSocket 없으면 버퍼에 보관
                self._buffer(payload)

        except Exception:
            pass  # 로그 핸들러 자체 오류는 무시

    def _buffer(self, payload):
        """연결 전 로그를 최대 50개까지 임시 보관"""
        with self._lock:
            if len(self._queue) < self._max_queue:
                self._queue.append(payload)
            else:
                self._queue.pop(0)  # 오래된 것 제거
                self._queue.append(payload)

    async def flush_buffer(self, ws):
        """WebSocket 연결 직후 버퍼에 쌓인 로그 일괄 전송"""
        from common.protocol import PacketType, make_packet
        with self._lock:
            pending = list(self._queue)
            self._queue.clear()

        for payload in pending:
            try:
                pkt = make_packet(PacketType.LOG_STREAM, payload)
                await ws.send(pkt)
                await __import__("asyncio").sleep(0.02)  # 속도 조절
            except Exception:
                break

    @staticmethod
    async def _send(ws, pkt: str):
        try:
            await ws.send(pkt)
        except Exception:
            pass
