from __future__ import annotations

from .constants import POWER_CNTRL, VOLTAGE_CNTRL


# Defaults that are not user-facing HMI parameters. Keep target voltage,
# active power and charge/discharge current defaults in
# config/charger_parameter_limits.json.
CAN_STARTUP_DEFAULTS = {
    "pfc_mode_request": POWER_CNTRL,
    "conf_request": 5,
    "v2l_frequency_setpoint": 50,
    "v2l_voltage_setpoint": 230,
    "reactive_power_setpoint_var": 0,
    "phase_current_limit_a": 180,
}


CAN_STARTUP_BY_NODE = {
    # N05 is the ACDC/VSI node in the existing setup.
    "N05": {
        "pfc_mode_request": VOLTAGE_CNTRL,
        "conf_request": 4,
        "charge_current_limit_a_fallback": 300,
        "discharge_current_limit_a_fallback": 300,
    },
}


PARAMETER_FALLBACKS_BY_NODE = {
    # Used only if a value is missing from charger_parameter_limits.json.
    "N01": {"target_voltage_v": 450, "requested_power_kw": 1.0, "charge_current_limit_a": 10, "discharge_current_limit_a": 10},
    "N02": {"target_voltage_v": 450, "requested_power_kw": 0.0, "charge_current_limit_a": 10, "discharge_current_limit_a": 10},
    "N03": {"target_voltage_v": 150, "requested_power_kw": -0.1, "charge_current_limit_a": 30, "discharge_current_limit_a": 30},
    "N04": {"target_voltage_v": 150, "requested_power_kw": 0.0, "charge_current_limit_a": 30, "discharge_current_limit_a": 30},
    "N05": {"target_voltage_v": 150, "requested_power_kw": 1.0, "charge_current_limit_a": 300, "discharge_current_limit_a": 300},
}


def can_startup_value(node: str, key: str):
    if node in CAN_STARTUP_BY_NODE and key in CAN_STARTUP_BY_NODE[node]:
        return CAN_STARTUP_BY_NODE[node][key]
    return CAN_STARTUP_DEFAULTS[key]


def parameter_fallback(node: str, key: str, default: float = 0.0) -> float:
    node_values = PARAMETER_FALLBACKS_BY_NODE.get(node, {})
    return float(node_values.get(key, default))
