from __future__ import annotations

import asyncio
import logging
import time
from collections import deque
from datetime import datetime, timezone
from typing import Any

from app.config import Settings
from app.models.parameters import ChargerParameters, ChargerParametersUpdate
from app.models.telemetry import (
    ChargerEvent,
    ChargerState,
    ChargerStatus,
    ChargerTelemetry,
    HistorySample,
    TelemetryConnection,
)


LOGGER = logging.getLogger(__name__)
FAULT_LIKE_STATES = {
    ChargerState.FAULT,
    ChargerState.SAFE_D,
    ChargerState.LOCK_DSP,
}


class ParameterValidationError(ValueError):
    def __init__(self, message: str, *, charger_id: str | None = None) -> None:
        super().__init__(message)
        self.charger_id = charger_id


class TelemetryStore:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._lock = asyncio.Lock()
        self._statuses: dict[str, ChargerStatus] = {}
        self._parameters: dict[str, ChargerParameters] = {}
        self._live_points: dict[str, deque[HistorySample]] = {}
        self._last_history_ms: dict[str, float] = {}
        self._events: deque[ChargerEvent] = deque(maxlen=settings.max_events)
        self._configured_chargers = set(settings.charger_ids)
        self._ignored_chargers_logged: set[str] = set()
        self._connection = TelemetryConnection(
            source=settings.telemetry_source,
            endpoint=settings.zmq_endpoint,
        )

    async def bootstrap(self) -> None:
        async with self._lock:
            for charger_id in self.settings.charger_ids:
                self._ensure_charger_locked(charger_id)

    def _ensure_charger_locked(self, charger_id: str) -> None:
        if charger_id not in self._parameters:
            limits = self.settings.parameter_limits_for(charger_id)
            power_limits = limits["requested_power_kw"]
            target_voltage = limits["target_voltage_v"]["default"]
            initial_power_kw = power_limits["default"]
            charge_current_limit_a = limits["charge_current_limit_a"]["default"]
            discharge_current_limit_a = limits["discharge_current_limit_a"]["default"]
            self._parameters[charger_id] = ChargerParameters(
                charger_id=charger_id,
                target_voltage_v=target_voltage,
                current_limit_a=charge_current_limit_a,
                charge_current_limit_a=charge_current_limit_a,
                discharge_current_limit_a=discharge_current_limit_a,
                requested_power_kw=initial_power_kw,
                charge_current_setpoint_a=self._charge_current_setpoint(
                    requested_power_kw=initial_power_kw,
                    target_voltage=target_voltage,
                ),
                active_power_setpoint_W=initial_power_kw * 1000.0,
                max_allowed_power_kw=power_limits["max"],
                applied_power_kw=initial_power_kw,
                voltage_min_v=limits["voltage_min_v"]["default"],
                voltage_max_v=limits["voltage_max_v"]["default"],
                parameter_limits=limits,
            )

        if charger_id not in self._statuses:
            self._statuses[charger_id] = ChargerStatus(charger_id=charger_id)

        if charger_id not in self._live_points:
            self._live_points[charger_id] = deque(maxlen=self.settings.live_buffer_points)

    def _is_allowed_charger_locked(self, charger_id: str) -> bool:
        return (
            self.settings.allow_unknown_chargers
            or not self._configured_chargers
            or charger_id in self._configured_chargers
        )

    async def set_source_status(self, connected: bool, error: str | None = None) -> None:
        async with self._lock:
            self._connection.connected = connected
            self._connection.last_error = error
            if not connected:
                self._connection.active = False

    async def record_invalid_message(self, error: str) -> ChargerEvent:
        async with self._lock:
            LOGGER.warning("Invalid telemetry message: %s", error)
            self._connection.invalid_message_count += 1
            self._connection.last_error = error
            return self._append_event_locked(
                ChargerEvent(
                    severity="warning",
                    kind="telemetry_parse_error",
                    message=f"Invalid telemetry message: {error}",
                )
            )

    async def ingest(self, telemetry: ChargerTelemetry) -> dict[str, Any] | None:
        now = datetime.now(timezone.utc)
        now_ms = time.monotonic() * 1000

        async with self._lock:
            if not self._is_allowed_charger_locked(telemetry.charger_id):
                if telemetry.charger_id not in self._ignored_chargers_logged:
                    self._ignored_chargers_logged.add(telemetry.charger_id)
                    LOGGER.info(
                        "Ignoring telemetry for unconfigured charger %s. Configure CHARGER_IDS or set ALLOW_UNKNOWN_CHARGERS=true.",
                        telemetry.charger_id,
                    )
                self._connection.connected = True
                self._connection.active = True
                self._connection.last_message_at = now
                self._connection.message_count += 1
                return None

            self._ensure_charger_locked(telemetry.charger_id)
            previous = self._statuses[telemetry.charger_id]
            previous_telemetry = previous.telemetry
            if previous_telemetry is not None:
                telemetry = self._merge_partial_telemetry(previous_telemetry, telemetry)

            effective_state = telemetry.state
            if telemetry.fault_code and effective_state not in FAULT_LIKE_STATES:
                effective_state = ChargerState.FAULT
            elif telemetry.warning_code and effective_state not in FAULT_LIKE_STATES:
                effective_state = ChargerState.WARNING

            telemetry.state = effective_state
            status = ChargerStatus(
                charger_id=telemetry.charger_id,
                state=effective_state,
                telemetry=telemetry,
                stale=False,
                offline=False,
                last_update=telemetry.timestamp,
                seconds_since_last_message=0,
                fault_code=telemetry.fault_code,
                warning_code=telemetry.warning_code,
                updated_at=now,
            )
            self._statuses[telemetry.charger_id] = status

            self._connection.connected = True
            self._connection.active = True
            self._connection.last_message_at = now
            self._connection.message_count += 1
            self._connection.last_error = None
            LOGGER.debug("Telemetry received for %s", telemetry.charger_id)

            sample = HistorySample(
                charger_id=telemetry.charger_id,
                timestamp=telemetry.timestamp,
                vin=telemetry.vin,
                iin=telemetry.iin,
                pin=telemetry.pin,
                vout=telemetry.vout,
                iout=telemetry.iout,
                pout=telemetry.pout,
                efficiency=telemetry.efficiency,
                energy_session_kwh=telemetry.energy_session_kwh,
                state=effective_state,
            )
            should_persist = (
                now_ms - self._last_history_ms.get(telemetry.charger_id, 0)
                >= self.settings.history_sample_period_ms
            )
            if should_persist:
                self._last_history_ms[telemetry.charger_id] = now_ms
                self._live_points[telemetry.charger_id].append(sample)

            event = None
            if previous.state != effective_state:
                severity = "info"
                if effective_state == ChargerState.WARNING:
                    severity = "warning"
                elif effective_state in {*FAULT_LIKE_STATES, ChargerState.OFFLINE}:
                    severity = "fault"
                event = self._append_event_locked(
                    ChargerEvent(
                        charger_id=telemetry.charger_id,
                        severity=severity,
                        kind="state_change",
                        message=f"{telemetry.charger_id} state changed to {effective_state.value}",
                    )
                )

            return {
                "status": status,
                "point": sample if should_persist else None,
                "history_sample": sample if should_persist else None,
                "event": event,
                "summary": self._summary_locked(),
                "connection": self._connection,
            }

    def _merge_partial_telemetry(
        self,
        previous: ChargerTelemetry,
        current: ChargerTelemetry,
    ) -> ChargerTelemetry:
        update = {}
        for field in (
            "vin",
            "iin",
            "pin",
            "vout",
            "iout",
            "pout",
            "efficiency",
            "energy_session_kwh",
            "fault_code",
            "warning_code",
        ):
            if getattr(current, field) is None:
                update[field] = getattr(previous, field)

        merged_raw = {**previous.raw, **current.raw}
        update["raw"] = merged_raw
        state_keys = (
            f"{current.charger_id}_SystemState",
            f"{current.charger_id}_SystemDcdcState",
            f"{current.charger_id}_itfc_critical_fault_word",
            f"{current.charger_id}_warning_code",
            f"{current.charger_id}_itfc_warning_word",
            f"{current.charger_id}_itfc_warning_code",
        )
        if not any(key in current.raw for key in state_keys):
            update["state"] = previous.state

        return current.model_copy(update=update)

    async def check_timeouts(self) -> list[dict[str, Any]]:
        now = datetime.now(timezone.utc)
        changed: list[dict[str, Any]] = []

        async with self._lock:
            if self._connection.last_message_at is not None:
                source_age = (now - self._connection.last_message_at).total_seconds()
                self._connection.active = source_age < self.settings.stale_timeout_seconds

            for charger_id, status in list(self._statuses.items()):
                if status.last_update is None:
                    continue

                age = max(0.0, (now - status.last_update).total_seconds())
                was_state = status.state
                was_stale = status.stale
                was_offline = status.offline

                status.seconds_since_last_message = age
                if age >= self.settings.offline_timeout_seconds:
                    status.state = ChargerState.OFFLINE
                    status.offline = True
                    status.stale = False
                elif age >= self.settings.stale_timeout_seconds:
                    status.state = ChargerState.STALE
                    status.offline = False
                    status.stale = True
                else:
                    status.offline = False
                    status.stale = False
                    if status.telemetry is not None:
                        status.state = status.telemetry.state

                status.updated_at = now
                if (status.state, status.stale, status.offline) != (was_state, was_stale, was_offline):
                    LOGGER.warning("Charger %s marked %s after %.1fs without telemetry", charger_id, status.state.value, age)
                    event = self._append_event_locked(
                        ChargerEvent(
                            charger_id=charger_id,
                            severity="warning" if status.stale else "fault",
                            kind="timeout",
                            message=f"{charger_id} is {status.state.value}",
                        )
                    )
                    changed.append(
                        {
                            "status": status,
                            "event": event,
                            "summary": self._summary_locked(),
                            "connection": self._connection,
                        }
                    )

        return changed

    async def list_statuses(self) -> list[ChargerStatus]:
        async with self._lock:
            self._refresh_ages_locked()
            return list(self._statuses.values())

    async def list_parameters(self) -> list[ChargerParameters]:
        async with self._lock:
            return list(self._parameters.values())

    async def get_status(self, charger_id: str) -> ChargerStatus | None:
        async with self._lock:
            self._refresh_ages_locked()
            return self._statuses.get(charger_id)

    async def get_parameters(self, charger_id: str) -> ChargerParameters:
        async with self._lock:
            self._ensure_charger_locked(charger_id)
            return self._parameters[charger_id]

    async def prepare_parameter_update(self, charger_id: str, update: ChargerParametersUpdate) -> ChargerParameters:
        async with self._lock:
            self._ensure_charger_locked(charger_id)
            current = self._parameters[charger_id]
            changes = update.model_dump(exclude_unset=True)
            if "active_power_setpoint_W" in changes and "requested_power_kw" not in changes:
                changes["requested_power_kw"] = changes["active_power_setpoint_W"] / 1000.0

            voltage_min = changes.get("voltage_min_v", current.voltage_min_v)
            voltage_max = changes.get("voltage_max_v", current.voltage_max_v)
            target_voltage = changes.get("target_voltage_v", current.target_voltage_v)
            requested_power_kw = changes.get("requested_power_kw", current.requested_power_kw)
            charge_current_limit_a = changes.get(
                "charge_current_limit_a",
                changes.get("current_limit_a", current.charge_current_limit_a),
            )
            discharge_current_limit_a = changes.get(
                "discharge_current_limit_a",
                changes.get("current_limit_a", current.discharge_current_limit_a),
            )
            active_power_setpoint_w = requested_power_kw * 1000.0
            charge_current_setpoint_a = self._charge_current_setpoint(
                requested_power_kw=requested_power_kw,
                target_voltage=target_voltage,
            )

            limits = current.parameter_limits or self.settings.parameter_limits_for(charger_id)
            self._validate_parameter_limit(charger_id, limits, "requested_power_kw", requested_power_kw, "Power", "kW")
            self._validate_parameter_limit(charger_id, limits, "target_voltage_v", target_voltage, "Target voltage", "V")
            self._validate_parameter_limit(charger_id, limits, "charge_current_limit_a", charge_current_limit_a, "Charge current", "A")
            self._validate_parameter_limit(charger_id, limits, "discharge_current_limit_a", discharge_current_limit_a, "Discharge current", "A")
            self._validate_parameter_limit(charger_id, limits, "voltage_min_v", voltage_min, "Minimum voltage", "V")
            self._validate_parameter_limit(charger_id, limits, "voltage_max_v", voltage_max, "Maximum voltage", "V")

            if voltage_min >= voltage_max:
                raise ParameterValidationError(
                    "Minimum voltage must be lower than maximum voltage.",
                    charger_id=charger_id,
                )

            if not voltage_min <= target_voltage <= voltage_max:
                raise ParameterValidationError(
                    f"Target voltage {target_voltage:.1f} V must be between {voltage_min:.1f} V and {voltage_max:.1f} V.",
                    charger_id=charger_id,
                )

            updated = current.model_copy(
                update={
                    **changes,
                    "requested_power_kw": requested_power_kw,
                    "current_limit_a": charge_current_limit_a,
                    "charge_current_limit_a": charge_current_limit_a,
                    "discharge_current_limit_a": discharge_current_limit_a,
                    "charge_current_setpoint_a": charge_current_setpoint_a,
                    "active_power_setpoint_W": active_power_setpoint_w,
                    "max_allowed_power_kw": limits["requested_power_kw"]["max"],
                    "applied_power_kw": requested_power_kw,
                    "parameter_limits": limits,
                    "updated_at": datetime.now(timezone.utc),
                }
            )
            return updated

    async def apply_parameters(self, parameters: ChargerParameters) -> ChargerParameters:
        async with self._lock:
            self._ensure_charger_locked(parameters.charger_id)
            self._parameters[parameters.charger_id] = parameters
            self._append_event_locked(
                ChargerEvent(
                    charger_id=parameters.charger_id,
                    severity="info",
                    kind="parameters_applied",
                    message=(
                        f"{parameters.charger_id} setpoints applied: "
                        f"P={parameters.active_power_setpoint_W:.0f} W, "
                        f"Ichg={parameters.charge_current_limit_a:.1f} A, "
                        f"Idis={parameters.discharge_current_limit_a:.1f} A"
                    ),
                )
            )
            return parameters

    async def update_parameters(self, charger_id: str, update: ChargerParametersUpdate) -> ChargerParameters:
        parameters = await self.prepare_parameter_update(charger_id, update)
        return await self.apply_parameters(parameters)

    async def add_command_event(self, charger_id: str, message: str, severity: str = "info") -> ChargerEvent:
        async with self._lock:
            return self._append_event_locked(
                ChargerEvent(
                    charger_id=charger_id,
                    severity=severity,
                    kind="command",
                    message=message,
                )
            )

    async def clear_events(self) -> None:
        async with self._lock:
            self._events.clear()

    async def snapshot(self) -> dict[str, Any]:
        async with self._lock:
            self._refresh_ages_locked()
            return {
                "chargers": list(self._statuses.values()),
                "parameters": list(self._parameters.values()),
                "live_points": {key: list(value) for key, value in self._live_points.items()},
                "events": list(self._events),
                "summary": self._summary_locked(),
                "connection": self._connection,
            }

    async def summary(self) -> dict[str, Any]:
        async with self._lock:
            self._refresh_ages_locked()
            return self._summary_locked()

    async def events(self) -> list[ChargerEvent]:
        async with self._lock:
            return list(self._events)

    def _append_event_locked(self, event: ChargerEvent) -> ChargerEvent:
        self._events.appendleft(event)
        return event

    def _refresh_ages_locked(self) -> None:
        now = datetime.now(timezone.utc)
        for status in self._statuses.values():
            if status.last_update is None:
                continue
            status.seconds_since_last_message = max(0.0, (now - status.last_update).total_seconds())

        if self._connection.last_message_at is not None:
            source_age = (now - self._connection.last_message_at).total_seconds()
            self._connection.active = source_age < self.settings.stale_timeout_seconds

    def _summary_locked(self) -> dict[str, Any]:
        total_power_w = 0.0
        total_energy_kwh = 0.0
        active = 0
        alarms = 0

        for status in self._statuses.values():
            telemetry = status.telemetry
            if telemetry is None:
                continue

            if status.state == ChargerState.CHARGING and not status.stale and not status.offline:
                active += 1

            if telemetry.pout is not None and not status.offline:
                total_power_w += telemetry.pout

            if telemetry.energy_session_kwh is not None:
                total_energy_kwh += telemetry.energy_session_kwh

            if status.state in {ChargerState.WARNING, *FAULT_LIKE_STATES} or status.fault_code or status.warning_code:
                alarms += 1

        return {
            "total_power_kw": total_power_w / 1000,
            "total_energy_kwh": total_energy_kwh,
            "active_chargers": active,
            "active_alarms": alarms,
            "charger_count": len(self._statuses),
        }

    def _charge_current_setpoint(self, *, requested_power_kw: float, target_voltage: float) -> float:
        if target_voltage <= 0:
            return 0.0
        return requested_power_kw * 1000.0 / target_voltage

    def _validate_parameter_limit(
        self,
        charger_id: str,
        limits: dict[str, dict[str, float]],
        key: str,
        value: float,
        label: str,
        unit: str,
    ) -> None:
        limit = limits.get(key)
        if not limit:
            return

        minimum = float(limit.get("min", 0.0))
        maximum = float(limit.get("max", value))
        if minimum <= value <= maximum:
            return

        message = f"{label} {value:.1f} {unit} must be between {minimum:.1f} and {maximum:.1f} {unit}"
        if key == "requested_power_kw" and value > maximum:
            message = f"Potência pedida {value:.1f} kW excede o máximo permitido de {maximum:.1f} kW"

        LOGGER.warning("Rejected parameter for %s: %s", charger_id, message)
        self._append_event_locked(
            ChargerEvent(
                charger_id=charger_id,
                severity="warning",
                kind="parameter_rejected",
                message=message,
            )
        )
        raise ParameterValidationError(message, charger_id=charger_id)
