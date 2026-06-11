import argparse
import tkinter as tk

from core.can_interface import CANInterface
from core.message_sender import MessageSender
from core.message_receiver import MessageReceiver
from core.zmq_publisher import create_publisher
from core.gui import BMPUGUI
from core.data_forwarder import create_forwarder

from config.constants import NODES, DROOP_CONFIG, PV_MEASUREMENTS
from core.droop import configure_droop_for_node
from core.mppt_power import MPPTTask
from config.signals_config import signals


def main():
    parser = argparse.ArgumentParser(description="Shift2DC Converter Control System (5 Converters)")
    parser.add_argument(
        "--forward-data",
        action="store_true",
        help="Enable data forwarding to remote database",
    )
    args = parser.parse_args()

    socket = create_publisher()

    # Criar uma interface CAN por nó definido em config.constants.NODES
    iface_map = {}  # ex: {"N01": CANInterface(...), "N02": ...}

    for node_name, dbc_file, node_id, canopen_node_id in NODES:
        # cria a interface CAN para este nó
        iface = CANInterface(dbc_file, node_id)
        iface_map[node_name] = iface

        # se houver configuração de droop para este nó, aplica-a
        #if node_name in DROOP_CONFIG:
        #    configure_droop_for_node(
        #        iface,
        #        canopen_node_id,
        #        DROOP_CONFIG[node_name],
        #        enable_droop=True,
        #    )


    
    
    # Sender conhece o mapa completo de nós
    sender = MessageSender(iface_map)

    # Receiver recebe de todas as interfaces e publica via ZMQ
    receiver = MessageReceiver(list(iface_map.values()), socket)
    receiver.start()
    sender.startup_sequence()

    # -------------------------------
    # MPPT para o nó PV (N03)
    # -------------------------------
    pv_node = "N03"
    pv_iface = iface_map[pv_node]

    mppt_task = MPPTTask(
        iface=pv_iface,
        node=pv_node,
        measurements=PV_MEASUREMENTS,
        period=0.5,
    )

    #mppt_task.start()
    #print("🌞 MPPT ativo no nó", pv_node)

    # -------------------------------
    # Optional: Start data forwarder to send data to remote DB
    # -------------------------------
    forwarder = None
    if args.forward_data:
        forwarder = create_forwarder()
        forwarder.start()
        print("📡 Data forwarder para base de dados remota ativo (5 conversores).")

    # GUI com todos os nós disponíveis
    root = tk.Tk()
    app = BMPUGUI(root, iface_map)
    try:
        root.mainloop()
    except KeyboardInterrupt:
        print("🛑 Encerrado pelo utilizador.")
    finally:
        if forwarder:
            forwarder.stop()
            forwarder.join(timeout=5)  # Wait for thread to complete cleanup
            print("📊 Forwarder stats:", forwarder.get_stats())


if __name__ == "__main__":
    main()
