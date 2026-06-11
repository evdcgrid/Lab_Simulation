from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.encoders import jsonable_encoder


class TelemetryHub:
    def __init__(self) -> None:
        self._clients: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._clients.add(websocket)

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._clients.discard(websocket)

    async def broadcast(self, message: dict[str, Any]) -> None:
        payload = jsonable_encoder(message)
        async with self._lock:
            clients = list(self._clients)

        for websocket in clients:
            try:
                await websocket.send_json(payload)
            except Exception:
                await self.disconnect(websocket)


router = APIRouter()


@router.websocket("/ws/telemetry")
async def telemetry_websocket(websocket: WebSocket) -> None:
    hub: TelemetryHub = websocket.app.state.hub
    store = websocket.app.state.store

    await hub.connect(websocket)
    try:
        await websocket.send_json(
            jsonable_encoder(
                {
                    "type": "snapshot",
                    "data": await store.snapshot(),
                }
            )
        )
        while True:
            message = await websocket.receive_text()
            if message == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        pass
    finally:
        await hub.disconnect(websocket)

