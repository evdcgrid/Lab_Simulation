from __future__ import annotations

import json
import os
import threading
import time
from typing import Any

import zmq

from config.constants import CHARGING, FAULT_ACK, POWER_ON, STAND_BY
from config.signals_config import signals


class ZmqCommandServer:
    def __init__(self, iface_map: dict[str, Any], endpoint: str) -> None:
        self.iface_map = iface_map
        self.endpoint = endpoint
        self.charge_confirm_timeout_seconds = float(os.getenv("HMI_CHARGE_CONFIRM_TIMEOUT_SECONDS", "10"))
        self._context = zmq.Context.instance()
        self._socket: zmq.Socket | None = None
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._charge_watchdogs: dict[str, threading.Event] = {}
        self._state_requests: dict[str, int] = {}
        self._target_voltage_v: dict[str, float] = {}

    def start(self) -> None:
        self._socket = self._context.socket(zmq.REP)
        self._socket.linger = 0
        self._socket.bind(self.endpoint)
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        print(f"ZMQ command server listening on {self.endpoint}")

    def stop(self) -> None:
        self._stop.set()
        for cancel in self._charge_watchdogs.values():
            cancel.set()
        if self._thread is not None:
            self._thread.join(timeout=2)
        if self._socket is not None:
            self._socket.close(linger=0)

    def _run(self) -> None:
        assert self._socket is not None
        poller = zmq.Poller()
        poller.register(self._socket, zmq.POLLIN)

        while not self._stop.is_set():
            events = dict(poller.poll(100))
            if self._socket not in events:
                continue

            try:
                raw = self._socket.recv()
                request = json.loads(raw.decode("utf-8"))
                reply = self._handle(request)
            except Exception as exc:
                reply = {"accepted": False, "message": f"Command error: {exc}"}

            self._socket.send_json(reply)

    def _handle(self, request: dict[str, Any]) -> dict[str, Any]:
        charger_id = str(request.get("charger_id", "")).strip()
        if charger_id not in self.iface_map:
            return {"accepted": False, "message": f"Unknown charger {charger_id}"}

        command = request.get("command")
        payload = request.get("payload") or {}

        if command == "apply_parameters":
            return self._apply_parameters(charger_id, payload)
        if command == "start":
            self._send_state(charger_id, CHARGING)
            self._watch_charge_request(charger_id)
            return {
                "accepted": True,
                "message": (
                    f"{charger_id} start sent; waiting up to "
                    f"{self.charge_confirm_timeout_seconds:.1f}s for SystemState=3"
                ),
            }
        if command == "stop":
            self._cancel_charge_watchdog(charger_id)
            self._send_state(charger_id, STAND_BY)
            return {"accepted": True, "message": f"{charger_id} stop sent"}
        if command == "reset_fault":
            self._cancel_charge_watchdog(charger_id)
            self._send_state(charger_id, FAULT_ACK)
            return {"accepted": True, "message": f"{charger_id} fault reset sent"}

        return {"accepted": False, "message": f"Unsupported command {command}"}

    def _apply_parameters(self, charger_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        p_watt = self._power_setpoint_w(payload)
        target_voltage_v = self._optional_float(
            payload,
            "target_voltage_v",
            "target_voltage",
            "output_voltage_setpoint_v",
        )

        rpdo1 = dict(signals[charger_id]["RPDO1"])
        charge_current = self._optional_float(payload, "charge_current_limit_a", "current_limit_a")
        discharge_current = self._optional_float(payload, "discharge_current_limit_a", "current_limit_a")
        if charge_current is not None:
            rpdo1[f"{charger_id}_itfc_i_charge_limit"] = charge_current
        if discharge_current is not None:
            rpdo1[f"{charger_id}_itfc_i_discharge_limit"] = discharge_current
        rpdo1[f"{charger_id}_itfc_active_power_setpoint_W"] = p_watt

        self.iface_map[charger_id].send_message(f"{charger_id}_RPDO1", rpdo1, period=0.5)
        if target_voltage_v is not None:
            self._target_voltage_v[charger_id] = target_voltage_v
            self._send_state(charger_id, self._state_for_parameter_update(charger_id))

        target_voltage_msg = (
            f", Vtarget={target_voltage_v:.1f} V"
            if target_voltage_v is not None
            else ""
        )
        return {
            "accepted": True,
            "message": (
                f"{charger_id} RPDO1 set: P={p_watt:.0f} W, "
                f"Ichg={rpdo1[f'{charger_id}_itfc_i_charge_limit']} A, "
                f"Idis={rpdo1[f'{charger_id}_itfc_i_discharge_limit']} A"
                f"{target_voltage_msg}"
            ),
            "active_power_setpoint_W": p_watt,
            "charge_current_limit_a": rpdo1[f"{charger_id}_itfc_i_charge_limit"],
            "discharge_current_limit_a": rpdo1[f"{charger_id}_itfc_i_discharge_limit"],
            "target_voltage_v": target_voltage_v,
        }

    def _power_setpoint_w(self, payload: dict[str, Any]) -> float:
        if "active_power_setpoint_W" in payload:
            return float(payload["active_power_setpoint_W"])
        if "active_power_setpoint_w" in payload:
            return float(payload["active_power_setpoint_w"])
        if "requested_power_kw" in payload:
            return float(payload["requested_power_kw"]) * 1000.0
        raise ValueError("Missing active_power_setpoint_W/requested_power_kw")

    def _optional_float(self, payload: dict[str, Any], *keys: str) -> float | None:
        for key in keys:
            if key in payload and payload[key] is not None:
                return float(payload[key])
        return None

    def _send_state(self, charger_id: str, state_value: int) -> None:
        base = {f"{charger_id}_itfc_pfc_state_request": state_value}
        if charger_id in self._target_voltage_v:
            base[f"{charger_id}_itfc_output_voltage_setpoint"] = self._target_voltage_v[charger_id]
        payload = build_rpdo0_payload(charger_id, base)
        self._state_requests[charger_id] = state_value
        self.iface_map[charger_id].send_message(f"{charger_id}_RPDO0", payload, period=0.5)

    def _state_for_parameter_update(self, charger_id: str) -> int:
        if charger_id in self._state_requests:
            return self._state_requests[charger_id]

        latest_state = getattr(self.iface_map[charger_id], "latest_system_state", None)
        if latest_state in {STAND_BY, POWER_ON, CHARGING, FAULT_ACK}:
            return int(latest_state)
        return STAND_BY

    def _cancel_charge_watchdog(self, charger_id: str) -> None:
        cancel = self._charge_watchdogs.pop(charger_id, None)
        if cancel is not None:
            cancel.set()

    def _watch_charge_request(self, charger_id: str) -> None:
        self._cancel_charge_watchdog(charger_id)
        cancel = threading.Event()
        self._charge_watchdogs[charger_id] = cancel

        thread = threading.Thread(
            target=self._charge_watchdog_loop,
            args=(charger_id, cancel),
            daemon=True,
        )
        thread.start()

    def _charge_watchdog_loop(self, charger_id: str, cancel: threading.Event) -> None:
        deadline = time.monotonic() + self.charge_confirm_timeout_seconds
        iface = self.iface_map[charger_id]

        while not self._stop.is_set() and not cancel.is_set() and time.monotonic() < deadline:
            if getattr(iface, "latest_system_state", None) == CHARGING:
                print(f"✅ {charger_id} charge confirmed: SystemState=3")
                self._charge_watchdogs.pop(charger_id, None)
                return
            time.sleep(0.1)

        if self._stop.is_set() or cancel.is_set():
            return

        last_state = getattr(iface, "latest_system_state", None)
        print(
            f"⚠️ {charger_id} did not reach SystemState=3 within "
            f"{self.charge_confirm_timeout_seconds:.1f}s "
            f"(last SystemState={last_state}); requesting Standby."
        )
        self._send_state(charger_id, STAND_BY)
        self._charge_watchdogs.pop(charger_id, None)


def build_rpdo0_payload(node: str, base: dict[str, Any]) -> dict[str, Any]:
    state_key = f"{node}_itfc_pfc_state_request"
    state_val = base.get(state_key)
    rpdo0_cfg = signals.get(node, {}).get("RPDO0", {})

    if state_val == POWER_ON:
        template = rpdo0_cfg.get("power_on", {})
    elif state_val == CHARGING:
        template = rpdo0_cfg.get("charging", {})
    else:
        template = rpdo0_cfg.get("standby", {})

    payload = dict(template)
    payload.update(base)
    return payload
