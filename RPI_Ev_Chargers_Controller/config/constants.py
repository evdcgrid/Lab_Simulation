BITRATE = 500000
CHANNEL = 0
SEND_PERIOD = 0.5
PUB_BIND = "tcp://*:3333"
SUB_CONNECT  = "tcp://127.0.0.1:3333"
COMMAND_BIND = "tcp://*:3334"
COMMAND_CONNECT = "tcp://127.0.0.1:3334"

STAND_BY = 1
POWER_ON = 2
CHARGING = 3
FAULT_ACK = 8
POWER_CNTRL = 2
VOLTAGE_CNTRL = 3

# IDs CAN de cada nó (ajusta se na tua instalação forem outros)
NODE_ID_1 = 0
NODE_ID_2 = 31
NODE_ID_3 = 62
NODE_ID_4 = 93
NODE_ID_5 = 124

CANOPEN_NODEID_N01 = 0x80
CANOPEN_NODEID_N02 = 0x81
CANOPEN_NODEID_N03 = 0x82
CANOPEN_NODEID_N04 = 0x83
CANOPEN_NODEID_N05 = 0x111

# Ficheiros DBC por nó (garante que estes ficheiros existem na mesma pasta)
DBC_FILE_1 = "SingleBMPU_v1_DCDC1.dbc"
DBC_FILE_2 = "SingleBMPU_v1_DCDC2.dbc"
DBC_FILE_3 = "SingleBMPU_v1_DCDC3.dbc"  
DBC_FILE_4 = "SingleBMPU_v1_DCDC4.dbc" 
DBC_FILE_5 = "SingleBMPU_v1_ACDC1.dbc"  

# Lista conveniente com todos os nós
NODES = [
    ("N01", DBC_FILE_1, NODE_ID_1, CANOPEN_NODEID_N01),
    ("N02", DBC_FILE_2, NODE_ID_2, CANOPEN_NODEID_N02),
    ("N03", DBC_FILE_3, NODE_ID_3, CANOPEN_NODEID_N03),
    ("N04", DBC_FILE_4, NODE_ID_4, CANOPEN_NODEID_N04),
    ("N05", DBC_FILE_5, NODE_ID_5, CANOPEN_NODEID_N05),
]

DROOP_DEFAULT_350 = {
    "unom": 350.0,
    "U1": 250.0,
    "U2": 320.0,
    "U3": 345.0,
    "U4": 355.0,
    "U5": 380.0,
    "U6": 400.0,
    "U7": 420.0,
    "Pmax":  11040.0,
    "Pmin": -11040.0,
}

DROOP_DEFAULT_700 = {
    "unom": 700.0,
    "U1": 500.0,
    "U2": 640.0,
    "U3": 690.0,
    "U4": 710.0,
    "U5": 760.0,
    "U6": 800.0,
    "U7": 844.0,
    "Pmax":  11040.0,
    "Pmin": -11040.0,
}


DROOP_CONFIG = {
    "N01": {
        **DROOP_DEFAULT_350,
        "grid": 350,
    },
    "N02": {
        **DROOP_DEFAULT_350,
        "grid": 350,
    },
    "N03": {
        **DROOP_DEFAULT_350,
        "grid": 350,
    },
    "N04": {
        **DROOP_DEFAULT_350,
        "grid": 350,
    },
    "N05": {
        **DROOP_DEFAULT_350,
        "grid": 350,
    },
}

# Buffer simples de medições PV
PV_MEASUREMENTS = {
    "v_pv": None,
    "i_pv": None,
}
