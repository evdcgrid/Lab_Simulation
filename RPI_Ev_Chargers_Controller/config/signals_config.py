# config/signals_config.py
from .constants import STAND_BY, POWER_ON, CHARGING, VOLTAGE_CNTRL, POWER_CNTRL

# Tabelas de sinais por nó. Cada entrada "N0X" é usada pelo MessageSender
# para construir as mensagens RPDO/HB de arranque.
signals = {
    "N01": {
        "HB_boot": {"N01_MasterStatus": 0},
        "HB_on":   {"N01_MasterStatus": 5},

        "RPDO0": {
            "standby": {
                "N01_itfc_pfc_state_request": STAND_BY,
                "N01_itfc_pfc_mode_request": POWER_CNTRL,
                "N01_itfc_conf_request": 5,                 # CONF_DCDC
                "N01_itfc_v2l_frequency_setpoint": 50,
                "N01_itfc_v2l_voltage_setpoint": 230,
                "N01_itfc_output_voltage_setpoint": 450,
            },
            "power_on": {
                "N01_itfc_pfc_state_request": POWER_ON,
                "N01_itfc_pfc_mode_request": POWER_CNTRL,
                "N01_itfc_conf_request": 5,
                "N01_itfc_v2l_frequency_setpoint": 50,
                "N01_itfc_v2l_voltage_setpoint": 230,
                "N01_itfc_output_voltage_setpoint": 450,
            },
            "charging": {
                "N01_itfc_pfc_state_request": CHARGING,
                "N01_itfc_pfc_mode_request": POWER_CNTRL,
                "N01_itfc_conf_request": 5,
                "N01_itfc_v2l_frequency_setpoint": 50,
                "N01_itfc_v2l_voltage_setpoint": 230,
                "N01_itfc_output_voltage_setpoint": 500,
            },
        },

        "RPDO1": {
            "N01_itfc_i_charge_limit": 10,
            "N01_itfc_i_discharge_limit": 10,
            "N01_itfc_active_power_setpoint_W": 1000,
            "N01_itfc_reactive_power_setpoint_VAR": 0,
        },

        "RPDO2": {
            "N01_itfc_i_L1_limit": 180,
            "N01_itfc_i_L2_limit": 180,
            "N01_itfc_i_L3_limit": 180,
        },
    },

    "N02": {
        "HB_boot": {"N02_MasterStatus": 0},
        "HB_on":   {"N02_MasterStatus": 5},

        "RPDO0": {
            "standby": {
                "N02_itfc_pfc_state_request": STAND_BY,
                "N02_itfc_pfc_mode_request": POWER_CNTRL,
                "N02_itfc_conf_request": 5,                
                "N02_itfc_v2l_frequency_setpoint": 50,
                "N02_itfc_v2l_voltage_setpoint": 230,
                "N02_itfc_output_voltage_setpoint": 350,
            },
            "power_on": {
                "N02_itfc_pfc_state_request": POWER_ON,
                "N02_itfc_pfc_mode_request": POWER_CNTRL,
                "N02_itfc_conf_request": 5,
                "N02_itfc_v2l_frequency_setpoint": 50,
                "N02_itfc_v2l_voltage_setpoint": 230,
                "N02_itfc_output_voltage_setpoint": 350,
            },
            "charging": {
                "N02_itfc_pfc_state_request": CHARGING,
                "N02_itfc_pfc_mode_request": POWER_CNTRL,
                "N02_itfc_conf_request": 5,
                "N02_itfc_v2l_frequency_setpoint": 50,
                "N02_itfc_v2l_voltage_setpoint": 230,
                "N02_itfc_output_voltage_setpoint": 350,
            },
        },

        "RPDO1": {
            "N02_itfc_i_charge_limit": 30,
            "N02_itfc_i_discharge_limit": 30,
            "N02_itfc_active_power_setpoint_W": 0000,
            "N02_itfc_reactive_power_setpoint_VAR": 0,
        },

        "RPDO2": {
            "N02_itfc_i_L1_limit": 180,
            "N02_itfc_i_L2_limit": 180,
            "N02_itfc_i_L3_limit": 180,
        },
    },

    
    "N03": {
        "HB_boot": {"N03_MasterStatus": 0},
        "HB_on":   {"N03_MasterStatus": 5},

        "RPDO0": {
            "standby": {
                "N03_itfc_pfc_state_request": STAND_BY,
                "N03_itfc_pfc_mode_request": POWER_CNTRL,
                "N03_itfc_conf_request": 5,
                "N03_itfc_v2l_frequency_setpoint": 50,
                "N03_itfc_v2l_voltage_setpoint": 230,
                "N03_itfc_output_voltage_setpoint": 150,
            },
            "power_on": {
                "N03_itfc_pfc_state_request": POWER_ON,
                "N03_itfc_pfc_mode_request": POWER_CNTRL,
                "N03_itfc_conf_request": 5,
                "N03_itfc_v2l_frequency_setpoint": 50,
                "N03_itfc_v2l_voltage_setpoint": 230,
                "N03_itfc_output_voltage_setpoint": 150,
            },
            "charging": {
                "N03_itfc_pfc_state_request": CHARGING,
                "N03_itfc_pfc_mode_request": POWER_CNTRL,
                "N03_itfc_conf_request": 5,
                "N03_itfc_v2l_frequency_setpoint": 50,
                "N03_itfc_v2l_voltage_setpoint": 230,
                "N03_itfc_output_voltage_setpoint": 500,
            },
        },

        "RPDO1": {
            "N03_itfc_i_charge_limit": 30,
            "N03_itfc_i_discharge_limit": 30,
            "N03_itfc_active_power_setpoint_W": -100,
            "N03_itfc_reactive_power_setpoint_VAR": 0,
        },

        "RPDO2": {
            "N03_itfc_i_L1_limit": 180,
            "N03_itfc_i_L2_limit": 180,
            "N03_itfc_i_L3_limit": 180,
        },
    },

    "N04": {
        "HB_boot": {"N04_MasterStatus": 0},
        "HB_on":   {"N04_MasterStatus": 5},

        "RPDO0": {
            "standby": {
                "N04_itfc_pfc_state_request": STAND_BY,
                "N04_itfc_pfc_mode_request": POWER_CNTRL,
                "N04_itfc_conf_request": 5,
                "N04_itfc_v2l_frequency_setpoint": 50,
                "N04_itfc_v2l_voltage_setpoint": 230,
                "N04_itfc_output_voltage_setpoint": 150,
            },
            "power_on": {
                "N04_itfc_pfc_state_request": POWER_ON,
                "N04_itfc_pfc_mode_request": POWER_CNTRL,
                "N04_itfc_conf_request": 5,
                "N04_itfc_v2l_frequency_setpoint": 50,
                "N04_itfc_v2l_voltage_setpoint": 230,
                "N04_itfc_output_voltage_setpoint": 150,
            },
            "charging": {
                "N04_itfc_pfc_state_request": CHARGING,
                "N04_itfc_pfc_mode_request": POWER_CNTRL,
                "N04_itfc_conf_request": 5,
                "N04_itfc_v2l_frequency_setpoint": 50,
                "N04_itfc_v2l_voltage_setpoint": 230,
                "N04_itfc_output_voltage_setpoint": 150,
            },
        },

        "RPDO1": {
            "N04_itfc_i_charge_limit": 30,
            "N04_itfc_i_discharge_limit": 30,
            "N04_itfc_active_power_setpoint_W": 0000,
            "N04_itfc_reactive_power_setpoint_VAR": 0,
        },

        "RPDO2": {
            "N04_itfc_i_L1_limit": 180,
            "N04_itfc_i_L2_limit": 180,
            "N04_itfc_i_L3_limit": 180,
        },
    },

    "N05": {
        "HB_boot": {"N05_MasterStatus": 0},
        "HB_on":   {"N05_MasterStatus": 5},

        "RPDO0": {
            "standby": {
                "N05_itfc_pfc_state_request": STAND_BY,
                "N05_itfc_pfc_mode_request": VOLTAGE_CNTRL,
                "N05_itfc_conf_request": 4,
                "N05_itfc_v2l_frequency_setpoint": 50,
                "N05_itfc_v2l_voltage_setpoint": 230,
                "N05_itfc_output_voltage_setpoint": 150,
            },
            "power_on": {
                "N05_itfc_pfc_state_request": POWER_ON,
                "N05_itfc_pfc_mode_request": VOLTAGE_CNTRL,
                "N05_itfc_conf_request": 4,
                "N05_itfc_v2l_frequency_setpoint": 50,
                "N05_itfc_v2l_voltage_setpoint": 230,
                "N05_itfc_output_voltage_setpoint": 350,
            },
            "charging": {
                "N05_itfc_pfc_state_request": CHARGING,
                "N05_itfc_pfc_mode_request": VOLTAGE_CNTRL,
                "N05_itfc_conf_request": 4,
                "N05_itfc_v2l_frequency_setpoint": 50,
                "N05_itfc_v2l_voltage_setpoint": 230,
                "N05_itfc_output_voltage_setpoint": 350,
            },
        },

        "RPDO1": {
            "N05_itfc_i_charge_limit": 300,
            "N05_itfc_i_discharge_limit": 300,
            "N05_itfc_active_power_setpoint_W": 1000,
            "N05_itfc_reactive_power_setpoint_VAR": 0,
        },

        "RPDO2": {
            "N05_itfc_i_L1_limit": 180,
            "N05_itfc_i_L2_limit": 180,
            "N05_itfc_i_L3_limit": 180,
        },
    },
}
