from __future__ import annotations

import copy
import json
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any


DEFAULT_PARAMETER_LIMITS: dict[str, dict[str, float]] = {
    "requested_power_kw": {"default": 3.3, "min": 0.0, "max": 6.6, "step": 0.1},
    "target_voltage_v": {"default": 400.0, "min": 250.0, "max": 500.0, "step": 1.0},
    "charge_current_limit_a": {"default": 16.0, "min": 0.0, "max": 300.0, "step": 0.5},
    "discharge_current_limit_a": {"default": 16.0, "min": 0.0, "max": 300.0, "step": 0.5},
    "voltage_min_v": {"default": 250.0, "min": 0.0, "max": 499.0, "step": 1.0},
    "voltage_max_v": {"default": 500.0, "min": 251.0, "max": 1000.0, "step": 1.0},
}


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return

    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def _get_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _get_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def _get_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default


def _get_csv(name: str, default: str) -> list[str]:
    raw = os.getenv(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


def _parse_power_limits(raw: str | None) -> dict[str, float]:
    limits: dict[str, float] = {}
    if not raw:
        return limits

    for item in raw.split(","):
        if "=" not in item:
            continue
        charger_id, value = item.split("=", 1)
        try:
            limits[charger_id.strip()] = float(value.strip())
        except ValueError:
            continue
    return limits


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _merge_limits(base: dict[str, dict[str, float]], override: dict[str, Any]) -> dict[str, dict[str, float]]:
    merged = copy.deepcopy(base)
    for parameter, values in override.items():
        if not isinstance(values, dict):
            continue
        target = merged.setdefault(parameter, {})
        for key in ("default", "min", "max", "step"):
            if key in values:
                try:
                    target[key] = float(values[key])
                except (TypeError, ValueError):
                    pass
    return merged


@dataclass(frozen=True)
class Settings:
    app_name: str
    api_prefix: str
    telemetry_source: str
    cors_origins: list[str]

    zmq_endpoint: str
    zmq_topic: str
    zmq_message_format: str
    telemetry_rate_limit_ms: int
    history_sample_period_ms: int
    stale_timeout_seconds: int
    offline_timeout_seconds: int

    sqlite_path: Path
    live_buffer_points: int
    max_events: int

    charger_ids: list[str]
    allow_unknown_chargers: bool
    charger_max_power_kw: float
    charger_power_limits: dict[str, float]
    parameter_config_path: Path
    parameter_config: dict[str, Any]

    mock_interval_ms: int

    command_publisher: str
    zmq_command_endpoint: str
    command_timeout_ms: int

    def max_power_for(self, charger_id: str) -> float:
        return self.parameter_limits_for(charger_id)["requested_power_kw"]["max"]

    def parameter_limits_for(self, charger_id: str) -> dict[str, dict[str, float]]:
        limits = _merge_limits(DEFAULT_PARAMETER_LIMITS, self.parameter_config.get("defaults", {}))
        charger_overrides = self.parameter_config.get("chargers", {}).get(charger_id, {})
        if isinstance(charger_overrides, dict):
            limits = _merge_limits(limits, charger_overrides)

        power = limits.setdefault("requested_power_kw", {})
        power.setdefault("min", 0.0)
        power.setdefault("max", self.charger_power_limits.get(charger_id, self.charger_max_power_kw))
        power.setdefault("default", min(3.3, power["max"]))
        power.setdefault("step", 0.1)
        power["default"] = min(max(power["default"], power["min"]), power["max"])

        for values in limits.values():
            values.setdefault("min", 0.0)
            values.setdefault("max", values.get("default", 0.0))
            values.setdefault("default", values["min"])
            values.setdefault("step", 1.0)
            values["default"] = min(max(values["default"], values["min"]), values["max"])

        return limits


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    backend_root = Path(__file__).resolve().parents[1]
    repo_root = backend_root.parent

    _load_env_file(repo_root / ".env")
    _load_env_file(backend_root / ".env")

    sqlite_default = backend_root / "data" / "hmi.sqlite3"
    parameter_config_default = repo_root / "config" / "charger_parameter_limits.json"
    parameter_config_path = Path(os.getenv("PARAMETER_CONFIG_PATH", str(parameter_config_default))).expanduser()

    return Settings(
        app_name=os.getenv("APP_NAME", "EV Charger HMI"),
        api_prefix=os.getenv("API_PREFIX", "/api"),
        telemetry_source=os.getenv("TELEMETRY_SOURCE", "mock").strip().lower(),
        cors_origins=_get_csv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"),
        zmq_endpoint=os.getenv("ZMQ_ENDPOINT", "tcp://127.0.0.1:3333"),
        zmq_topic=os.getenv("ZMQ_TOPIC", ""),
        zmq_message_format=os.getenv("ZMQ_MESSAGE_FORMAT", "json").strip().lower(),
        telemetry_rate_limit_ms=_get_int("TELEMETRY_RATE_LIMIT_MS", 250),
        history_sample_period_ms=_get_int("HISTORY_SAMPLE_PERIOD_MS", 1000),
        stale_timeout_seconds=_get_int("STALE_TIMEOUT_SECONDS", 3),
        offline_timeout_seconds=_get_int("OFFLINE_TIMEOUT_SECONDS", 10),
        sqlite_path=Path(os.getenv("SQLITE_PATH", str(sqlite_default))).expanduser(),
        live_buffer_points=_get_int("LIVE_BUFFER_POINTS", 1200),
        max_events=_get_int("MAX_EVENTS", 120),
        charger_ids=_get_csv("CHARGER_IDS", "charger_1,charger_2"),
        allow_unknown_chargers=_get_bool("ALLOW_UNKNOWN_CHARGERS", False),
        charger_max_power_kw=_get_float("CHARGER_MAX_POWER_KW", 6.6),
        charger_power_limits=_parse_power_limits(os.getenv("CHARGER_POWER_LIMITS")),
        parameter_config_path=parameter_config_path,
        parameter_config=_load_json(parameter_config_path),
        mock_interval_ms=_get_int("MOCK_INTERVAL_MS", 500),
        command_publisher=os.getenv("COMMAND_PUBLISHER", "mock").strip().lower(),
        zmq_command_endpoint=os.getenv("ZMQ_COMMAND_ENDPOINT", "tcp://127.0.0.1:3334"),
        command_timeout_ms=_get_int("COMMAND_TIMEOUT_MS", 1000),
    )
