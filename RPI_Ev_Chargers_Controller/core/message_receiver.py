import json
import threading
from core.mppt_power import MPPTTask
from config.constants import PV_MEASUREMENTS

class MessageReceiver(threading.Thread):
    def __init__(self, ifaces, socket):
        """ifaces: lista de instâncias CANInterface"""
        super().__init__(daemon=True)
        self.ifaces = list(ifaces)
        self.socket = socket

    def _publish(self, decoded):
        try:
            self.socket.send_string(json.dumps(decoded))
        except Exception as e:
            print(f"Erro ao enviar via ZMQ: {e}")

    def run(self):
        while True:
            for iface in self.ifaces:
                decoded = iface.receive_message()
                if decoded:
                    # print(f"[ZMQ PUB] {decoded}")
                    self._publish(decoded)
                        
                    # PV data:
                    if "N03_itfc_v_batt" in decoded:
                        PV_MEASUREMENTS["v_pv"] = decoded["N03_itfc_v_batt"] / 10  # V

                    if "N03_itfc_i_batt" in decoded:
                        PV_MEASUREMENTS["i_pv"] = decoded["N03_itfc_i_batt"] / 10  # A
