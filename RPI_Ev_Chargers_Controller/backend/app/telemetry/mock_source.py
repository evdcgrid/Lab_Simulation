from __future__ import annotations

import asyncio
import math
import random
from datetime import datetime, timezone

from app.config import Settings
from app.models.telemetry import ChargerState, ChargerTelemetry
from app.telemetry.source import TelemetryCallback, TelemetrySource


class MockTelemetrySource(TelemetrySource):
    def __init__(self, settings: Settings, on_telemetry: TelemetryCallback) -> None:
        self.settings = settings
        self.on_telemetry = on_telemetry
        self._stop = asyncio.Event()
        self._energy_kwh = {charger_id: 0.0 for charger_id in settings.charger_ids}
        self._tick = 0

    async def run(self) -> None:
        interval = max(0.05, self.settings.mock_interval_ms / 1000)
        while not self._stop.is_set():
            self._tick += 1
            for index, charger_id in enumerate(self.settings.charger_ids):
                await self.on_telemetry(self._make_sample(charger_id, index, interval))
            await asyncio.sleep(interval)

    async def stop(self) -> None:
        self._stop.set()

    def _make_sample(self, charger_id: str, index: int, interval: float) -> ChargerTelemetry:
        phase = self._tick / 18 + index
        base_power_kw = min(self.settings.max_power_for(charger_id) * 0.72, 5.4 + index * 0.6)
        power_kw = max(0.4, base_power_kw + math.sin(phase) * 0.45)
        voltage = 392 + math.sin(phase / 2) * 8 + index * 4
        current = (power_kw * 1000) / voltage
        input_power = power_kw * 1000 / 0.92
        efficiency = 91.5 + math.sin(phase / 3) * 1.5

        self._energy_kwh[charger_id] = self._energy_kwh.get(charger_id, 0.0) + power_kw * interval / 3600

        state = ChargerState.CHARGING
        warning_code = None
        fault_code = None
        if random.random() < 0.002:
            warning_code = "MOCK_LIMIT"
            state = ChargerState.WARNING

        return ChargerTelemetry(
            charger_id=charger_id,
            timestamp=datetime.now(timezone.utc),
            state=state,
            vin=430 + math.sin(phase / 3) * 6,
            iin=input_power / 430,
            pin=input_power,
            vout=voltage,
            iout=current,
            pout=power_kw * 1000,
            efficiency=efficiency,
            energy_session_kwh=self._energy_kwh[charger_id],
            fault_code=fault_code,
            warning_code=warning_code,
        )
