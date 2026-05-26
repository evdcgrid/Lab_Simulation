from __future__ import annotations

import json
import os
from copy import deepcopy
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PARAMETER_CONFIG = REPO_ROOT / "config" / "charger_parameter_limits.json"


def load_parameter_config() -> dict[str, Any]:
    path = _parameter_config_path()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def parameter_default(charger_id: str, parameter: str, fallback: float) -> float:
    config = load_parameter_config()
    value = _get_parameter_value(config.get("chargers", {}).get(charger_id), parameter)
    if value is None:
        value = _get_parameter_value(config.get("defaults"), parameter)
    return fallback if value is None else value


def apply_hmi_defaults(charger_id: str, rpdo0: dict[str, Any], rpdo1: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    rpdo0 = deepcopy(rpdo0)
    rpdo1 = deepcopy(rpdo1)

    target_voltage = parameter_default(
        charger_id,
        "target_voltage_v",
        float(rpdo0.get(f"{charger_id}_itfc_output_voltage_setpoint", 0)),
    )
    requested_power_kw = parameter_default(
        charger_id,
        "requested_power_kw",
        float(rpdo1.get(f"{charger_id}_itfc_active_power_setpoint_W", 0)) / 1000.0,
    )
    charge_current = parameter_default(
        charger_id,
        "charge_current_limit_a",
        float(rpdo1.get(f"{charger_id}_itfc_i_charge_limit", 0)),
    )
    discharge_current = parameter_default(
        charger_id,
        "discharge_current_limit_a",
        float(rpdo1.get(f"{charger_id}_itfc_i_discharge_limit", 0)),
    )

    rpdo0[f"{charger_id}_itfc_output_voltage_setpoint"] = target_voltage
    rpdo1[f"{charger_id}_itfc_active_power_setpoint_W"] = requested_power_kw * 1000.0
    rpdo1[f"{charger_id}_itfc_i_charge_limit"] = charge_current
    rpdo1[f"{charger_id}_itfc_i_discharge_limit"] = discharge_current
    return rpdo0, rpdo1


def _parameter_config_path() -> Path:
    raw = os.getenv("PARAMETER_CONFIG_PATH")
    if raw:
        path = Path(raw).expanduser()
        if path.is_absolute():
            return path
        repo_candidate = REPO_ROOT / path
        if repo_candidate.exists():
            return repo_candidate
        backend_candidate = REPO_ROOT / "backend" / path
        if backend_candidate.exists():
            return backend_candidate
    return DEFAULT_PARAMETER_CONFIG


def _get_parameter_value(section: Any, parameter: str) -> float | None:
    if not isinstance(section, dict):
        return None
    values = section.get(parameter)
    if not isinstance(values, dict) or "default" not in values:
        return None
    try:
        return float(values["default"])
    except (TypeError, ValueError):
        return None
