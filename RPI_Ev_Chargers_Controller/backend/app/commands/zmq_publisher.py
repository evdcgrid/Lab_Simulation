from __future__ import annotations

import asyncio
import logging
from typing import Any

import zmq
import zmq.asyncio

from app.commands.publisher import CommandPublisher
from app.models.commands import ChargerCommand, ChargerCommandResult


LOGGER = logging.getLogger(__name__)


class ZmqCommandPublisher(CommandPublisher):
    def __init__(self, endpoint: str, timeout_ms: int = 1000) -> None:
        self.endpoint = endpoint
        self.timeout_seconds = timeout_ms / 1000
        self._context = zmq.asyncio.Context.instance()
        self._socket: zmq.asyncio.Socket | None = None
        self._lock = asyncio.Lock()

    def _ensure_socket(self) -> zmq.asyncio.Socket:
        if self._socket is None or self._socket.closed:
            socket = self._context.socket(zmq.REQ)
            socket.linger = 0
            socket.connect(self.endpoint)
            self._socket = socket
            LOGGER.info("ZMQ command publisher connected to %s", self.endpoint)
        return self._socket

    def _reset_socket(self) -> None:
        if self._socket is not None:
            self._socket.close(linger=0)
        self._socket = None

    async def publish(self, charger_id: str, command: ChargerCommand) -> ChargerCommandResult:
        payload = command.model_dump(mode="json")
        payload["charger_id"] = charger_id
        payload["payload"] = self._command_payload(command.payload)

        async with self._lock:
            socket = self._ensure_socket()
            try:
                await socket.send_json(payload)
                reply = await asyncio.wait_for(socket.recv_json(), timeout=self.timeout_seconds)
            except Exception as exc:
                self._reset_socket()
                message = f"ZMQ command failed on {self.endpoint}: {exc}"
                LOGGER.warning(message)
                return ChargerCommandResult(
                    charger_id=charger_id,
                    command=command.command,
                    accepted=False,
                    message=message,
                )

        return ChargerCommandResult(
            charger_id=charger_id,
            command=command.command,
            accepted=bool(reply.get("accepted")),
            message=str(reply.get("message", "No command response")),
        )

    def _command_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        normalized = dict(payload)
        if "requested_power_kw" in normalized:
            normalized["active_power_setpoint_W"] = float(normalized["requested_power_kw"]) * 1000.0
        return normalized

    async def close(self) -> None:
        self._reset_socket()
