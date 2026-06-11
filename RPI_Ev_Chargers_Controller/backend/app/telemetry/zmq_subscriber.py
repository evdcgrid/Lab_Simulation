from __future__ import annotations

import asyncio
import logging
import time

import zmq
import zmq.asyncio

from app.config import Settings
from app.telemetry.parsers import IgnoredTelemetryMessage, parse_zmq_message
from app.telemetry.source import SourceStatusCallback, TelemetryCallback, TelemetrySource


LOGGER = logging.getLogger(__name__)


class ZmqSubscriber(TelemetrySource):
    def __init__(
        self,
        settings: Settings,
        on_telemetry: TelemetryCallback,
        on_source_status: SourceStatusCallback,
        on_invalid_message: SourceStatusCallback,
    ) -> None:
        self.settings = settings
        self.on_telemetry = on_telemetry
        self.on_source_status = on_source_status
        self.on_invalid_message = on_invalid_message
        self._stop = asyncio.Event()
        self._context = zmq.asyncio.Context.instance()
        self._last_emit_ms: dict[str, float] = {}

    async def run(self) -> None:
        while not self._stop.is_set():
            socket = self._context.socket(zmq.SUB)
            try:
                topic = self.settings.zmq_topic.encode("utf-8")
                socket.setsockopt(zmq.SUBSCRIBE, topic)
                socket.connect(self.settings.zmq_endpoint)
                await self.on_source_status(True, None)
                LOGGER.info("ZMQ subscriber connected to %s", self.settings.zmq_endpoint)

                while not self._stop.is_set():
                    try:
                        frames = await asyncio.wait_for(socket.recv_multipart(), timeout=1.0)
                    except asyncio.TimeoutError:
                        continue

                    if not frames:
                        continue

                    raw_payload = self._payload_from_frames(frames)
                    try:
                        telemetry = parse_zmq_message(raw_payload)
                    except IgnoredTelemetryMessage as exc:
                        LOGGER.debug("Ignored ZMQ frame: %s", exc)
                        continue
                    except ValueError as exc:
                        LOGGER.warning("Invalid ZMQ telemetry message: %s", exc)
                        await self.on_invalid_message(False, str(exc))
                        continue

                    if not self._has_measurements(telemetry):
                        now_ms = time.monotonic() * 1000
                        previous_ms = self._last_emit_ms.get(telemetry.charger_id, 0)
                        if now_ms - previous_ms < self.settings.telemetry_rate_limit_ms:
                            continue
                        self._last_emit_ms[telemetry.charger_id] = now_ms

                    await self.on_telemetry(telemetry)

            except Exception as exc:
                LOGGER.exception("ZMQ subscriber error")
                await self.on_source_status(False, str(exc))
                await asyncio.sleep(1.0)
            finally:
                socket.close(linger=0)

    async def stop(self) -> None:
        self._stop.set()

    def _payload_from_frames(self, frames: list[bytes]) -> bytes:
        if len(frames) == 1:
            frame = frames[0]
            if self.settings.zmq_topic and frame.startswith(self.settings.zmq_topic.encode("utf-8")):
                topic = self.settings.zmq_topic.encode("utf-8")
                return frame[len(topic) :].strip()
            return frame
        return frames[-1]

    def _has_measurements(self, telemetry) -> bool:
        return any(
            getattr(telemetry, field) is not None
            for field in ("vin", "iin", "pin", "vout", "iout", "pout", "efficiency")
        )
