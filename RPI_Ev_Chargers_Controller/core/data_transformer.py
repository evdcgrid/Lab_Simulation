# core/data_transformer.py
"""
Data Transformer

Converts flat averaged data from converters into nested structure
matching the database schema.
"""

from typing import Dict, Any, Optional


def transform_to_db_format(node_id: str, timestamp: str, aggregation_info: dict, averages: dict) -> dict:
    """
    Transform flat converter data into nested database structure.
    
    Args:
        node_id: Node identifier (N01, N02, N03, N04, or N05)
        timestamp: ISO timestamp
        aggregation_info: Aggregation metadata (period_start, period_end, sample_count, duration)
        averages: Flat dictionary of averaged values with N0X_ prefixes
    
    Returns:
        Nested dictionary matching database schema
    """
    
    # Helper to get value without node prefix
    def get_value(field_name: str) -> Optional[float]:
        full_name = f"{node_id}_{field_name}"
        return averages.get(full_name)
    
    # Build nested structure
    result = {
        "timestamp": timestamp,
        "node": node_id,
        "aggregation": {
            "period_start": aggregation_info.get("period_start"),
            "period_end": aggregation_info.get("period_end"),
            "sample_count": aggregation_info.get("sample_count"),
            "duration_seconds": aggregation_info.get("duration_seconds"),
        },
        "status": {},
        "flags": {},
        "limits": {},
        "available_power": {},
        "L1": {},
        "L2": {},
        "L3": {},
        "grid": {},
        "battery": {},
    }
    
    # Status fields
    status_fields = [
        "SystemState",
        "SystemSubState", 
        "SystemDcdcState",
        "SystemMode",
        "SystemConfiguration",
        "itfc_critical_fault_word",
    ]
    for field in status_fields:
        value = get_value(field)
        if value is not None:
            result["status"][field] = value
    
    # Flag fields
    flag_fields = [
        "CurrentRegulationFlag",
        "VoltageRegulationFlag",
        "ActivePowerRegulationFlag",
        "ReactivePowerRegulationFlag",
        "MaxBatteryChargingCurrentFlag",
        "MaxBatteryDishargingCurrentFlag",
        "SafeCFlag",
        "PfcOnFlag",
        "DcdcOnFlag",
        "InputCurrentLimitationFlag",
        "LoadImpedanceLimitationFlag",
        "ThermalLimitationFlag",
        "GridDetectionFlag",
        "AggregatedPlusFalg",
    ]
    for field in flag_fields:
        value = get_value(field)
        if value is not None:
            result["flags"][field] = value
    
    # Limits (apply 0.1 scaling for voltages and currents)
    limits_mapping = {
        "itfc_v_batt_max": "itfc_v_batt_max",
        "itfc_i_batt_max": "itfc_i_batt_max",
        "itfc_i_grid_max": "itfc_i_grid_max",
        "itfc_P_max": "itfc_P_max",
    }
    for field, key in limits_mapping.items():
        value = get_value(field)
        if value is not None:
            # Apply LSB=0.1 scaling for V and I (not for P)
            if field in ["itfc_v_batt_max", "itfc_i_batt_max", "itfc_i_grid_max"]:
                result["limits"][key] = value / 10.0
            else:
                result["limits"][key] = value
    
    # Available power
    power_mapping = {
        "itfc_pos_active_available_power": "itfc_pos_active_available_power",
        "itfc_neg_active_available_power": "itfc_neg_active_available_power",
        "itfc_pos_ractive_available_power": "itfc_pos_ractive_available_power",
        "itfc_neg_ractive_available_power": "itfc_neg_ractive_available_power",
    }
    for field, key in power_mapping.items():
        value = get_value(field)
        if value is not None:
            result["available_power"][key] = value
    
    # Phase L1 (apply 0.1 scaling for V and I)
    l1_v = get_value("itfc_v_L1mL4_rms")
    l1_i = get_value("itfc_i_L1_rms")
    l1_p = get_value("itfc_P_L1")
    l1_q = get_value("itfc_Q_L1")
    if l1_v is not None:
        result["L1"]["V"] = l1_v / 10.0  # Apply LSB=0.1
    if l1_i is not None:
        result["L1"]["I"] = l1_i / 10.0  # Apply LSB=0.1
    if l1_p is not None:
        result["L1"]["P"] = l1_p
    if l1_q is not None:
        result["L1"]["Q"] = l1_q
    
    # Phase L2 (apply 0.1 scaling for V and I)
    l2_v = get_value("itfc_v_L2mL4_rms")
    l2_i = get_value("itfc_i_L2_rms")
    l2_p = get_value("itfc_P_L2")
    l2_q = get_value("itfc_Q_L2")
    if l2_v is not None:
        result["L2"]["V"] = l2_v / 10.0  # Apply LSB=0.1
    if l2_i is not None:
        result["L2"]["I"] = l2_i / 10.0  # Apply LSB=0.1
    if l2_p is not None:
        result["L2"]["P"] = l2_p
    if l2_q is not None:
        result["L2"]["Q"] = l2_q
    
    # Phase L3 (apply 0.1 scaling for V and I)
    l3_v = get_value("itfc_v_L3mL4_rms")
    l3_i = get_value("itfc_i_L3_rms")
    l3_p = get_value("itfc_P_L3")
    l3_q = get_value("itfc_Q_L3")
    if l3_v is not None:
        result["L3"]["V"] = l3_v / 10.0  # Apply LSB=0.1
    if l3_i is not None:
        result["L3"]["I"] = l3_i / 10.0  # Apply LSB=0.1
    if l3_p is not None:
        result["L3"]["P"] = l3_p
    if l3_q is not None:
        result["L3"]["Q"] = l3_q
    
    # Grid (apply 0.1 scaling for V and I)
    grid_v = get_value("itfc_v_grid")
    grid_i = get_value("itfc_i_grid")
    grid_p = get_value("itfc_P_grid")
    grid_q = get_value("itfc_Q_grid")
    if grid_v is not None:
        result["grid"]["V"] = grid_v / 10.0  # Apply LSB=0.1
    if grid_i is not None:
        result["grid"]["I"] = grid_i / 10.0  # Apply LSB=0.1
    if grid_p is not None:
        result["grid"]["P"] = grid_p
    if grid_q is not None:
        result["grid"]["Q"] = grid_q
    
    # Battery (apply 0.1 scaling for V and I)
    batt_v = get_value("itfc_v_batt")
    batt_i = get_value("itfc_i_batt")
    batt_p = get_value("itfc_P_batt")
    batt_avail_i = get_value("itfc_available_i_batt")
    if batt_v is not None:
        result["battery"]["V"] = batt_v / 10.0  # Apply LSB=0.1
    if batt_i is not None:
        result["battery"]["I"] = batt_i / 10.0  # Apply LSB=0.1
    if batt_p is not None:
        result["battery"]["P"] = batt_p
    if batt_avail_i is not None:
        result["battery"]["available_I"] = batt_avail_i / 10.0  # Apply LSB=0.1
    
    # Remove empty sections
    result = {k: v for k, v in result.items() if v or k in ["timestamp", "node", "aggregation"]}
    
    return result

