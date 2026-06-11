from __future__ import annotations

from .can_startup_defaults import can_startup_value, parameter_fallback
from .constants import CHARGING, FAULT_ACK, POWER_ON, STAND_BY
from .hmi_parameter_defaults import parameter_default


NODES = ("N01", "N02", "N03", "N04", "N05")
STATE_VALUES = {
    "standby": STAND_BY,
    "power_on": POWER_ON,
    "charging": CHARGING,
    "fault_ack": FAULT_ACK,
}


def _parameter(node: str, key: str) -> float:
    return parameter_default(node, key, parameter_fallback(node, key))


def _rpdo0(node: str, state: int) -> dict[str, float | int]:
    return {
        f"{node}_itfc_pfc_state_request": state,
        f"{node}_itfc_pfc_mode_request": can_startup_value(node, "pfc_mode_request"),
        f"{node}_itfc_conf_request": can_startup_value(node, "conf_request"),
        f"{node}_itfc_v2l_frequency_setpoint": can_startup_value(node, "v2l_frequency_setpoint"),
        f"{node}_itfc_v2l_voltage_setpoint": can_startup_value(node, "v2l_voltage_setpoint"),
        f"{node}_itfc_output_voltage_setpoint": _parameter(node, "target_voltage_v"),
    }


def _rpdo1(node: str) -> dict[str, float | int]:
    return {
        f"{node}_itfc_i_charge_limit": _parameter(node, "charge_current_limit_a"),
        f"{node}_itfc_i_discharge_limit": _parameter(node, "discharge_current_limit_a"),
        f"{node}_itfc_active_power_setpoint_W": _parameter(node, "requested_power_kw") * 1000.0,
        f"{node}_itfc_reactive_power_setpoint_VAR": can_startup_value(node, "reactive_power_setpoint_var"),
    }


def _rpdo2(node: str) -> dict[str, float | int]:
    limit = can_startup_value(node, "phase_current_limit_a")
    return {
        f"{node}_itfc_i_L1_limit": limit,
        f"{node}_itfc_i_L2_limit": limit,
        f"{node}_itfc_i_L3_limit": limit,
    }


def _node_signals(node: str) -> dict:
    return {
        "HB_boot": {f"{node}_MasterStatus": 0},
        "HB_on": {f"{node}_MasterStatus": 5},
        "RPDO0": {name: _rpdo0(node, state) for name, state in STATE_VALUES.items()},
        "RPDO1": _rpdo1(node),
        "RPDO2": _rpdo2(node),
    }


# Public table used by the CAN sender, old GUI and ZMQ command server.
signals = {node: _node_signals(node) for node in NODES}
