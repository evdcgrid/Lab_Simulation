from __future__ import annotations

import json
import os
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
