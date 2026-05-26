from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any

from app.models.telemetry import ChargerState, ChargerTelemetry


NODE_PREFIX_RE = re.compile(r"^(N\d{2})_")
SHIFT2DC_TELEMETRY_FIELDS = {
    "SystemState",
    "SystemSubState",
    "SystemDcdcState",
    "SystemMode",
    "SystemConfiguration",
    "DcdcOnFlag",
    "PfcOnFlag",
    "ThermalLimitationFlag",
    "itfc_critical_fault_word",
    "itfc_v_batt_max",
    "itfc_i_batt_max",
    "itfc_i_grid_max",
    "itfc_P_max",
    "itfc_v_grid",
    "itfc_i_grid",
    "itfc_P_grid",
    "itfc_Q_grid",
    "itfc_v_batt",
    "itfc_i_batt",
    "itfc_P_batt",
    "itfc_available_i_batt",
    "itfc_v_L1mL4_rms",
    "itfc_i_L1_rms",
    "itfc_P_L1",
    "itfc_v_L2mL4_rms",
    "itfc_i_L2_rms",
    "itfc_P_L2",
    "itfc_v_L3mL4_rms",
    "itfc_i_L3_rms",
    "itfc_P_L3",
}


class IgnoredTelemetryMessage(ValueError):
    """Raised for valid JSON frames that are intentionally ignored."""


def parse_zmq_message(raw_msg: bytes) -> ChargerTelemetry:
    """Parse one ZMQ payload into the normalized HMI telemetry model.

    The first supported format is the target JSON contract from the HMI prompt.
    The second supported format is the current Shift2DC flat CAN JSON stream
    with keys like N03_itfc_v_batt.
    """
    try:
        payload = json.loads(raw_msg.decode("utf-8"))
    except UnicodeDecodeError as exc:
        raise ValueError("message is not valid UTF-8") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"message is not valid JSON: {exc}") from exc

    if not isinstance(payload, dict):
        raise ValueError("JSON payload must be an object")

    if "charger_id" in payload:
        return _parse_hmi_contract(payload)

    return _parse_shift2dc_flat(payload)


def _parse_hmi_contract(payload: dict[str, Any]) -> ChargerTelemetry:
    state = _state_from_value(payload.get("state"))
    fault_code = _nullable_str(payload.get("fault_code"))
    warning_code = _nullable_str(payload.get("warning_code"))

    if fault_code:
        state = ChargerState.FAULT
    elif warning_code and state != ChargerState.FAULT:
        state = ChargerState.WARNING

    return ChargerTelemetry(
        charger_id=str(payload["charger_id"]),
        timestamp=_parse_timestamp(payload.get("timestamp")),
        state=state,
        vin=_float_or_none(payload.get("vin")),
        iin=_float_or_none(payload.get("iin")),
        pin=_float_or_none(payload.get("pin")),
        vout=_float_or_none(payload.get("vout")),
        iout=_float_or_none(payload.get("iout")),
        pout=_float_or_none(payload.get("pout")),
        efficiency=_float_or_none(payload.get("efficiency")),
        energy_session_kwh=_float_or_none(payload.get("energy_session_kwh")),
        fault_code=fault_code,
        warning_code=warning_code,
        raw=payload,
    )


def _parse_shift2dc_flat(payload: dict[str, Any]) -> ChargerTelemetry:
    node_id = _detect_node_id(payload)
    if node_id is None:
        raise ValueError("could not detect charger/node id from flat payload")
    if not _has_shift2dc_telemetry(payload, node_id):
        raise IgnoredTelemetryMessage(f"payload for {node_id} does not contain TPDO telemetry fields")

    fault_word = _get(payload, node_id, "itfc_critical_fault_word")
    warning_code = _first_present(
        payload,
        f"{node_id}_warning_code",
        f"{node_id}_itfc_warning_word",
        f"{node_id}_itfc_warning_code",
    )

    state = _state_from_system_state(
        system_state=_get(payload, node_id, "SystemState"),
        dcdc_state=_get(payload, node_id, "SystemDcdcState"),
        fault_word=fault_word,
        warning_code=warning_code,
    )

    # The Shift2DC ZMQ stream is already decoded by cantools, so the DBC
    # scaling is already applied before PlotJuggler and the HMI receive it.
    vin = _float_or_none(_get(payload, node_id, "itfc_v_grid"))
    iin = _float_or_none(_get(payload, node_id, "itfc_i_grid"))
    pin = _float_or_none(_get(payload, node_id, "itfc_P_grid"))
    vout = _float_or_none(_get(payload, node_id, "itfc_v_batt"))
    iout = _float_or_none(_get(payload, node_id, "itfc_i_batt"))
    pout = _float_or_none(_get(payload, node_id, "itfc_P_batt"))
    efficiency = _efficiency(pin, pout)

    fault_code = _nullable_str(fault_word) if _float_or_none(fault_word) not in (None, 0.0) else None
    warning = _nullable_str(warning_code) if _float_or_none(warning_code) not in (None, 0.0) else None

    return ChargerTelemetry(
        charger_id=node_id,
        timestamp=datetime.now(timezone.utc),
        state=state,
        vin=vin,
        iin=iin,
        pin=pin,
        vout=vout,
        iout=iout,
        pout=pout,
        efficiency=efficiency,
        energy_session_kwh=_float_or_none(payload.get(f"{node_id}_energy_session_kwh")),
        fault_code=fault_code,
        warning_code=warning,
        raw=payload,
    )


def _detect_node_id(payload: dict[str, Any]) -> str | None:
    for key in payload:
        match = NODE_PREFIX_RE.match(key)
        if match:
            return match.group(1)
    return None


def _get(payload: dict[str, Any], node_id: str, field: str) -> Any:
    return payload.get(f"{node_id}_{field}")


def _has_shift2dc_telemetry(payload: dict[str, Any], node_id: str) -> bool:
    return any(f"{node_id}_{field}" in payload for field in SHIFT2DC_TELEMETRY_FIELDS)


def _first_present(payload: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in payload:
            return payload[key]
    return None


def _first_float(payload: dict[str, Any], *keys: str) -> float | None:
    for key in keys:
        value = _float_or_none(payload.get(key))
        if value is not None:
            return value
    return None


def _parse_timestamp(value: Any) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    if isinstance(value, datetime):
        return value
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=timezone.utc)

    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return datetime.now(timezone.utc)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _state_from_value(value: Any) -> ChargerState:
    if value is None:
        return ChargerState.IDLE
    text = str(value).strip().lower()
    for state in ChargerState:
        if text == state.value:
            return state
    return ChargerState.IDLE


def _state_from_system_state(
    *,
    system_state: Any,
    dcdc_state: Any,
    fault_word: Any,
    warning_code: Any,
) -> ChargerState:
    # SystemDcdcState can remain 0 in multi-PU configurations, according to
    # the DBC. Prefer the high-level SystemState and use DCDC state only if
    # SystemState is absent from the decoded frame.
    state = _state_code(system_state)
    if state is None:
        state = _state_code(dcdc_state)
    if state is None:
        return ChargerState.IDLE

    state_from_code = {
        0: ChargerState.INIT,
        1: ChargerState.STANDBY,
        2: ChargerState.POWER_ON,
        3: ChargerState.CHARGING,
        4: ChargerState.SAFE_D,
        6: ChargerState.STOPPING,
        7: ChargerState.LOCK_DSP,
        8: ChargerState.FAULT_ACK,
    }.get(state)

    if state_from_code in {ChargerState.SAFE_D, ChargerState.LOCK_DSP, ChargerState.FAULT_ACK}:
        return state_from_code

    if _float_or_none(fault_word) not in (None, 0.0):
        return ChargerState.FAULT
    if _float_or_none(warning_code) not in (None, 0.0):
        return ChargerState.WARNING

    if state_from_code is not None:
        return state_from_code

    return ChargerState.IDLE


def _state_code(value: Any) -> int | None:
    numeric = _float_or_none(value)
    if numeric is not None:
        return int(numeric)

    if value is None:
        return None

    text = str(value).strip().upper().replace(" ", "_")
    text = text.replace("STATE__DCDC_", "STATE_DCDC_").replace("STATE__PFC_", "STATE_PFC_")
    for prefix in ("STATE_DCDC_", "STATE_PFC_", "STATE_"):
        if text.startswith(prefix):
            text = text[len(prefix):]
            break

    return {
        "INIT": 0,
        "STANDBY": 1,
        "STAND_BY": 1,
        "POWER_ON": 2,
        "POWERON": 2,
        "CHARGE": 3,
        "CHARGING": 3,
        "SAFE_D": 4,
        "SAFED": 4,
        "STOPPING": 6,
        "LOCK_DSP": 7,
        "FAULT_ACK": 8,
    }.get(text)


def _float_or_none(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _efficiency(pin: float | None, pout: float | None) -> float | None:
    if pin is None or pout is None or abs(pin) < 1e-6:
        return None
    return max(0.0, min(100.0, abs(pout / pin) * 100.0))


def _nullable_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in {"none", "null", "0", "0.0"}:
        return None
    return text
