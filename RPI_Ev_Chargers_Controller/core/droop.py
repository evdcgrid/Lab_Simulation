#core/droop.py

def configure_droop_for_node(iface, canopen_node_id, cfg, enable_droop=True):
    """
    iface: CANInterface do nó
    canopen_node_id: node ID CANopen (ex: 0x50)
    cfg: dict com chaves:
         - "unom"
         - "U1"..."U7"
         - "Pmax", "Pmin"
         - "grid": 350 ou 700
    """

    # 1) Pmax / Pmin
    iface.sdo_download(canopen_node_id, 0x4300, 0x04, cfg["Pmax"], "f32")
    iface.sdo_download(canopen_node_id, 0x4300, 0x05, cfg["Pmin"], "f32")

    # 2) Forçar U_nom manual (em vez de auto-detectar)
    iface.sdo_download(canopen_node_id, 0x5300, 0x01, 1, "u16")         # usar valor manual
    iface.sdo_download(canopen_node_id, 0x5300, 0x02, cfg["unom"], "f32")

    # 3) Curva de droop (U1..U7)
    U = cfg
    if cfg["grid"] == 700:
        # 700 V
        iface.sdo_download(canopen_node_id, 0x5300, 0x05, U["U7"], "f32")  # U7
        iface.sdo_download(canopen_node_id, 0x5300, 0x06, U["U6"], "f32")  # U6
        iface.sdo_download(canopen_node_id, 0x5300, 0x07, U["U5"], "f32")  # U5
        iface.sdo_download(canopen_node_id, 0x5300, 0x08, U["U4"], "f32")  # U4
        iface.sdo_download(canopen_node_id, 0x5300, 0x09, U["U3"], "f32")  # U3
        iface.sdo_download(canopen_node_id, 0x5300, 0x0A, U["U2"], "f32")  # U2
        iface.sdo_download(canopen_node_id, 0x5300, 0x0B, U["U1"], "f32")  # U1
    elif cfg["grid"] == 350:
        # 350 V
        iface.sdo_download(canopen_node_id, 0x5300, 0x0C, U["U7"], "f32")  # U7
        iface.sdo_download(canopen_node_id, 0x5300, 0x0D, U["U6"], "f32")  # U6
        iface.sdo_download(canopen_node_id, 0x5300, 0x0E, U["U5"], "f32")  # U5
        iface.sdo_download(canopen_node_id, 0x5300, 0x0F, U["U4"], "f32")  # U4
        iface.sdo_download(canopen_node_id, 0x5300, 0x10, U["U3"], "f32")  # U3
        iface.sdo_download(canopen_node_id, 0x5300, 0x11, U["U2"], "f32")  # U2
        iface.sdo_download(canopen_node_id, 0x5300, 0x12, U["U1"], "f32")  # U1
    else:
        raise ValueError("cfg['grid'] deve ser 350 ou 700")

    # 4) Droop enable / disable
    iface.sdo_download(
        canopen_node_id, 0x5300, 0x14,
        1 if enable_droop else 0,
        "u16"
    )

    # Nao escrever masks de protecao aqui. As masks 0x5000:01 e
    # 0x4200:01 ficam configuradas pela interface oficial do conversor.
