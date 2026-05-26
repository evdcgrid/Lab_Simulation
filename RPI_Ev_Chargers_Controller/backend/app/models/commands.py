from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ChargerCommandType(str, Enum):
    START = "start"
    STOP = "stop"
    RESET_FAULT = "reset_fault"
    APPLY_PARAMETERS = "apply_parameters"


class ChargerCommand(BaseModel):
    command: ChargerCommandType
    payload: dict[str, Any] = Field(default_factory=dict)
    requested_by: str | None = None
    timestamp: datetime = Field(default_factory=utc_now)


class ChargerCommandResult(BaseModel):
    charger_id: str
    command: ChargerCommandType
    accepted: bool
    message: str
    timestamp: datetime = Field(default_factory=utc_now)

