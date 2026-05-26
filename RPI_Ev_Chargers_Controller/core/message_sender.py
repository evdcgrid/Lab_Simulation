import time
from config.signals_config import signals


class MessageSender:

    def __init__(self, iface_map):
        """
        iface_map: dict {"N01": CANInterface, "N02": CANInterface, ...}
        """
        self.iface_map = iface_map

    def startup_sequence(self):
        print("🚀 Enviando sequência de inicialização para todos os nós...")

        # -------------------------------
        # MASTER (N01)
        # -------------------------------
        master_node = "N01"
        master_iface = self.iface_map[master_node]

        master_iface.send_message(
            f"{master_node}_Master_Heartbeat",
            signals[master_node]["HB_boot"]
        )
        time.sleep(1)

        master_iface.send_message(
            f"{master_node}_Master_Heartbeat",
            signals[master_node]["HB_on"],
            period=0.5
        )

        master_iface.send_message(
            f"{master_node}_Sync_message",
            {},
            period=0.05
        )

        # -------------------------------
        # Todos os nós (RPDOs)
        # -------------------------------
        for node, iface in self.iface_map.items():
            if node not in signals:
                print(f"⚠️ Sem sinais para {node}, ignorado.")
                continue

            cfg = signals[node]

            # RPDO0 → TODOS (estado)
            iface.send_message(
                f"{node}_RPDO0",
                cfg["RPDO0"]["standby"],
                period=0.5
            )

            # RPDO1 → EXCETO nó PV (MPPT controla)
            #if node != "N03":
            iface.send_message(
                f"{node}_RPDO1",
                cfg["RPDO1"],
                period=0.5
            )

            # RPDO2 → TODOS
            iface.send_message(
                f"{node}_RPDO2",
                cfg["RPDO2"],
                period=0.5
            )

        print("✅ Sequência de inicialização concluída.")
