from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ChargerState(str, Enum):
    OFFLINE = "offline"
    IDLE = "idle"
    INIT = "init"
    STANDBY = "standby"
    POWER_ON = "power_on"
    CHARGING = "charging"
    SAFE_D = "safe_d"
    STOPPING = "stopping"
    LOCK_DSP = "lock_dsp"
    FAULT_ACK = "fault_ack"
    WARNING = "warning"
    FAULT = "fault"
    STALE = "stale"


class ChargerTelemetry(BaseModel):
    charger_id: str
    timestamp: datetime = Field(default_factory=utc_now)
    state: ChargerState = ChargerState.IDLE
    vin: float | None = None
    iin: float | None = None
    pin: float | None = None
    vout: float | None = None
    iout: float | None = None
    pout: float | None = None
    efficiency: float | None = None
    energy_session_kwh: float | None = None
    fault_code: str | None = None
    warning_code: str | None = None
    raw: dict[str, Any] = Field(default_factory=dict)


class ChargerStatus(BaseModel):
    charger_id: str
    state: ChargerState = ChargerState.OFFLINE
    telemetry: ChargerTelemetry | None = None
    stale: bool = False
    offline: bool = True
    last_update: datetime | None = None
    seconds_since_last_message: float | None = None
    fault_code: str | None = None
    warning_code: str | None = None
    updated_at: datetime = Field(default_factory=utc_now)


class ChargerEvent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = Field(default_factory=utc_now)
    charger_id: str | None = None
    severity: str = "info"
    kind: str = "event"
    message: str


class HistorySample(BaseModel):
    charger_id: str
    timestamp: datetime
    vin: float | None = None
    iin: float | None = None
    pin: float | None = None
    vout: float | None = None
    iout: float | None = None
    pout: float | None = None
    efficiency: float | None = None
    energy_session_kwh: float | None = None
    state: ChargerState = ChargerState.IDLE


class TelemetryConnection(BaseModel):
    source: str = "mock"
    endpoint: str | None = None
    connected: bool = False
    active: bool = False
    last_message_at: datetime | None = None
    message_count: int = 0
    invalid_message_count: int = 0
    last_error: str | None = None
