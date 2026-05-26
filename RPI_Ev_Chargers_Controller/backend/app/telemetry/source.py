from __future__ import annotations

from collections.abc import Awaitable, Callable

from app.models.telemetry import ChargerTelemetry


TelemetryCallback = Callable[[ChargerTelemetry], Awaitable[None]]
SourceStatusCallback = Callable[[bool, str | None], Awaitable[None]]


class TelemetrySource:
    async def run(self) -> None:
        raise NotImplementedError

    async def stop(self) -> None:
        raise NotImplementedError

