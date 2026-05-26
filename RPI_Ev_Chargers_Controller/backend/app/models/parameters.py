from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ChargerParameters(BaseModel):
    charger_id: str
    enabled: bool = True
    target_voltage_v: float = Field(default=400.0, ge=0)
    current_limit_a: float = Field(default=16.0, ge=0)
    charge_current_limit_a: float = Field(default=16.0, ge=0)
    discharge_current_limit_a: float = Field(default=16.0, ge=0)
    requested_power_kw: float = Field(default=3.3, ge=0)
    charge_current_setpoint_a: float = Field(default=8.25, ge=0)
    active_power_setpoint_W: float = Field(default=3300.0, ge=0)
    max_allowed_power_kw: float = Field(default=6.6, ge=0)
    applied_power_kw: float = Field(default=3.3, ge=0)
    voltage_min_v: float = Field(default=250.0, ge=0)
    voltage_max_v: float = Field(default=450.0, ge=0)
    parameter_limits: dict[str, dict[str, float]] = Field(default_factory=dict)
    cc_cv_profile: dict[str, Any] = Field(
        default_factory=lambda: {
            "cc_current_a": 16.0,
            "cv_voltage_v": 400.0,
            "termination_current_a": 1.0,
        }
    )
    updated_at: datetime = Field(default_factory=utc_now)


class ChargerParametersUpdate(BaseModel):
    enabled: bool | None = None
    target_voltage_v: float | None = Field(default=None, ge=0)
    current_limit_a: float | None = Field(default=None, ge=0)
    charge_current_limit_a: float | None = Field(default=None, ge=0)
    discharge_current_limit_a: float | None = Field(default=None, ge=0)
    requested_power_kw: float | None = Field(default=None, ge=0)
    charge_current_setpoint_a: float | None = Field(default=None, ge=0)
    active_power_setpoint_W: float | None = Field(default=None, ge=0)
    voltage_min_v: float | None = Field(default=None, ge=0)
    voltage_max_v: float | None = Field(default=None, ge=0)
    cc_cv_profile: dict[str, Any] | None = None
