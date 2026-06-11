# core/mppt_power.py
import numpy as np
import time
import threading


class MPPTPowerController:
    """
    MPPT Perturb & Observe
    Saída: referência de potência (W)
    """

    def __init__(
        self,
        v_ref_init=450.0,
        step_v=2.0,
        v_min=200.0,
        v_max=500.0,
        p_min=0.0,
        p_max=11000.0,
    ):
        self.v_ref = v_ref_init
        self.step_v = step_v
        self.v_min = v_min
        self.v_max = v_max
        self.p_min = p_min
        self.p_max = p_max

        self.prev_p = None
        self.direction = +1

    def update(self, v_pv, i_pv):
        p_pv = v_pv * i_pv

        if self.prev_p is None:
            self.prev_p = p_pv
            return np.clip(p_pv, self.p_min, self.p_max)

        dp = p_pv - self.prev_p

        if dp > 0:
            self.v_ref += self.direction * self.step_v
        else:
            self.direction *= -1
            self.v_ref += self.direction * self.step_v

        self.v_ref = np.clip(self.v_ref, self.v_min, self.v_max)

        p_ref = self.v_ref * i_pv
        p_ref = np.clip(p_ref, self.p_min, self.p_max)

        self.prev_p = p_pv
        return p_ref


class MPPTTask(threading.Thread):
    """
    Thread MPPT integrada com CANInterface
    """

    def __init__(self, iface, node, measurements, period=0.1):
        super().__init__(daemon=True)
        self.iface = iface
        self.node = node
        self.measurements = measurements
        self.period = period

        self.mppt = MPPTPowerController()

    def run(self):
        while True:
            try:
                v_pv = self.measurements.get("v_pv")
                i_pv = self.measurements.get("i_pv")

                if v_pv is None or i_pv is None:
                    time.sleep(self.period)
                    continue

                p_ref = self.mppt.update(v_pv, i_pv)

                # BMPU usa LSB = 10 W
                self.iface.send_message(
                    f"{self.node}_RPDO1",
                    {
                        f"{self.node}_itfc_active_power_setpoint_W": int(p_ref / 10),
                    },
                )

            except Exception as e:
                print(f"❌ MPPT error ({self.node}): {e}")

            time.sleep(self.period)

