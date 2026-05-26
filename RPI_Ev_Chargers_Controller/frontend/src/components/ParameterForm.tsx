import { Minus, Plus, Save } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import type { ChargerParameters, ChargerParametersUpdate } from "../types/parameters";
import { ConfirmModal } from "./ConfirmModal";

function clamp(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value));
}

function numberValue(value: string) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

function decimalPlaces(step: number) {
  const [, decimals = ""] = String(step).split(".");
  return decimals.length;
}

function snapToStep(value: number, step: number) {
  const decimals = decimalPlaces(step);
  return Number((Math.round(value / step) * step).toFixed(decimals));
}

interface ParameterFormProps {
  parameters: ChargerParameters;
  saving: boolean;
  error?: string | null;
  success?: string | null;
  onApply: (update: ChargerParametersUpdate) => Promise<void>;
  onEdit?: () => void;
}

type AdjustableKey =
  | "requested_power_kw"
  | "target_voltage_v"
  | "charge_current_limit_a"
  | "discharge_current_limit_a"
  | "voltage_min_v"
  | "voltage_max_v";

interface ParameterControl {
  key: AdjustableKey;
  label: string;
  unit: string;
  min: number;
  max: number;
  step: number;
  digits: number;
  currentValue: number;
}

function formatValue(value: number, digits: number) {
  return Number.isFinite(value) ? value.toFixed(digits) : "--";
}

export function ParameterForm({ parameters, saving, error, success, onApply, onEdit }: ParameterFormProps) {
  const [draft, setDraft] = useState(parameters);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [selectedKey, setSelectedKey] = useState<AdjustableKey>("requested_power_kw");

  useEffect(() => {
    setDraft(parameters);
    setSelectedKey("requested_power_kw");
  }, [parameters]);

  const editDraft = (updater: (current: ChargerParameters) => ChargerParameters) => {
    onEdit?.();
    setDraft(updater);
  };

  const parameterLimits = parameters.parameter_limits ?? {};
  const limitFor = (
    key: AdjustableKey,
    fallback: Pick<ParameterControl, "min" | "max" | "step">
  ) => ({
    ...fallback,
    ...(parameterLimits[key] ?? {})
  });
  const powerLimit = limitFor("requested_power_kw", { min: 0, max: parameters.max_allowed_power_kw, step: 0.1 });
  const maxPower = powerLimit.max;
  const powerPercent = maxPower > 0 ? (draft.requested_power_kw / maxPower) * 100 : 0;

  const validation = useMemo(() => {
    if (draft.requested_power_kw > maxPower) {
      return `Requested power ${draft.requested_power_kw.toFixed(1)} kW exceeds the allowed maximum of ${maxPower.toFixed(1)} kW.`;
    }
    if (draft.voltage_min_v >= draft.voltage_max_v) {
      return "Minimum voltage must be lower than maximum voltage.";
    }
    if (draft.target_voltage_v < draft.voltage_min_v || draft.target_voltage_v > draft.voltage_max_v) {
      return `Target voltage must be between ${draft.voltage_min_v.toFixed(0)} V and ${draft.voltage_max_v.toFixed(0)} V.`;
    }
    return null;
  }, [draft, maxPower]);

  const activePowerSetpointW = Math.round(draft.requested_power_kw * 1000);
  const chargeCurrentSetpointA = draft.target_voltage_v > 0 ? activePowerSetpointW / draft.target_voltage_v : 0;
  const chargeCurrentLimitA = draft.charge_current_limit_a ?? draft.current_limit_a;
  const dischargeCurrentLimitA = draft.discharge_current_limit_a ?? draft.current_limit_a;

  const controls = useMemo<ParameterControl[]>(
    () => {
      const requestedPowerLimit = limitFor("requested_power_kw", { min: 0, max: parameters.max_allowed_power_kw, step: 0.1 });
      const targetVoltageLimit = limitFor("target_voltage_v", { min: 0, max: 1000, step: 1 });
      const chargeCurrentLimit = limitFor("charge_current_limit_a", { min: 0, max: 300, step: 0.5 });
      const dischargeCurrentLimit = limitFor("discharge_current_limit_a", { min: 0, max: 300, step: 0.5 });
      const voltageMinLimit = limitFor("voltage_min_v", { min: 0, max: 999, step: 1 });
      const voltageMaxLimit = limitFor("voltage_max_v", { min: 1, max: 1000, step: 1 });

      return [
        {
          key: "requested_power_kw",
          label: "Power",
          unit: "kW",
          min: requestedPowerLimit.min,
          max: requestedPowerLimit.max,
          step: requestedPowerLimit.step,
          digits: 1,
          currentValue: parameters.applied_power_kw
        },
        {
          key: "target_voltage_v",
          label: "Target voltage",
          unit: "V",
          min: targetVoltageLimit.min,
          max: targetVoltageLimit.max,
          step: targetVoltageLimit.step,
          digits: 0,
          currentValue: parameters.target_voltage_v
        },
        {
          key: "charge_current_limit_a",
          label: "Charge current",
          unit: "A",
          min: chargeCurrentLimit.min,
          max: chargeCurrentLimit.max,
          step: chargeCurrentLimit.step,
          digits: 1,
          currentValue: parameters.charge_current_limit_a
        },
        {
          key: "discharge_current_limit_a",
          label: "Discharge current",
          unit: "A",
          min: dischargeCurrentLimit.min,
          max: dischargeCurrentLimit.max,
          step: dischargeCurrentLimit.step,
          digits: 1,
          currentValue: parameters.discharge_current_limit_a
        },
        {
          key: "voltage_min_v",
          label: "Minimum voltage",
          unit: "V",
          min: voltageMinLimit.min,
          max: voltageMinLimit.max,
          step: voltageMinLimit.step,
          digits: 0,
          currentValue: parameters.voltage_min_v
        },
        {
          key: "voltage_max_v",
          label: "Maximum voltage",
          unit: "V",
          min: voltageMaxLimit.min,
          max: voltageMaxLimit.max,
          step: voltageMaxLimit.step,
          digits: 0,
          currentValue: parameters.voltage_max_v
        }
      ];
    },
    [parameterLimits, parameters]
  );

  const selectedControl = controls.find((control) => control.key === selectedKey) ?? controls[0];
  const selectedValue = draft[selectedControl.key];
  const sliderValue = clamp(selectedValue, selectedControl.min, selectedControl.max);

  const update: ChargerParametersUpdate = {
    enabled: draft.enabled,
    target_voltage_v: draft.target_voltage_v,
    current_limit_a: chargeCurrentLimitA,
    charge_current_limit_a: chargeCurrentLimitA,
    discharge_current_limit_a: dischargeCurrentLimitA,
    requested_power_kw: draft.requested_power_kw,
    charge_current_setpoint_a: chargeCurrentSetpointA,
    active_power_setpoint_W: activePowerSetpointW,
    voltage_min_v: draft.voltage_min_v,
    voltage_max_v: draft.voltage_max_v,
    cc_cv_profile: draft.cc_cv_profile
  };

  const apply = async () => {
    if (validation) return;
    await onApply(update);
  };

  const onSubmit = () => {
    if (validation) return;
    if (powerPercent >= 90 || !draft.enabled) {
      setConfirmOpen(true);
      return;
    }
    void apply();
  };

  const setNumber = (key: AdjustableKey, value: number) => {
    editDraft((current) => ({ ...current, [key]: value }));
  };

  const setSelectedValue = (value: number) => {
    const clamped = clamp(value, selectedControl.min, selectedControl.max);
    setNumber(selectedControl.key, snapToStep(clamped, selectedControl.step));
  };

  const stepSelected = (direction: -1 | 1) => {
    setSelectedValue(selectedValue + selectedControl.step * direction);
  };

  return (
    <section className="parameter-form rounded-lg border border-white/10 bg-graphite-850 p-5 shadow-panel">
      <div className="parameter-form-header flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-xl font-semibold text-zinc-50">{parameters.charger_id}</h2>
          <div className="mt-1 text-sm text-zinc-400">
            Applied {parameters.applied_power_kw.toFixed(1)} kW
          </div>
        </div>
        <label className="flex min-h-12 items-center gap-3 rounded-md border border-white/10 bg-graphite-900 px-4">
          <input
            type="checkbox"
            className="h-6 w-6 accent-signal-green"
            checked={draft.enabled}
            onChange={(event) => editDraft((current) => ({ ...current, enabled: event.target.checked }))}
          />
          <span className="text-base font-semibold text-zinc-100">Enabled</span>
        </label>
      </div>

      <div className="parameter-editor mt-6 grid gap-4">
        <div className="parameter-slider-panel rounded-lg border border-white/10 bg-graphite-900 p-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <div className="text-sm text-zinc-400">{selectedControl.label}</div>
              <div className="mt-1 font-mono text-4xl font-semibold text-zinc-50">
                {formatValue(selectedValue, selectedControl.digits)}
                <span className="ml-2 text-lg text-zinc-400">{selectedControl.unit}</span>
              </div>
              <div className="mt-1 text-sm text-zinc-500">
                Current {formatValue(selectedControl.currentValue, selectedControl.digits)} {selectedControl.unit}
              </div>
            </div>
            <div className="text-right">
              <div className="text-sm text-zinc-400">Allowed range</div>
              <div className="font-mono text-lg font-semibold text-signal-cyan">
                {formatValue(selectedControl.min, selectedControl.digits)}-{formatValue(selectedControl.max, selectedControl.digits)} {selectedControl.unit}
              </div>
              {selectedControl.key === "requested_power_kw" ? (
                <div className={powerPercent >= 90 ? "text-sm text-signal-amber" : "text-sm text-zinc-400"}>
                  {powerPercent.toFixed(0)}% of limit
                </div>
              ) : null}
            </div>
          </div>

          <div className="parameter-power-control mt-5 grid grid-cols-[48px_1fr_112px_48px] items-center gap-3">
            <button className="grid h-12 place-items-center rounded-md bg-graphite-800 text-zinc-100" onClick={() => stepSelected(-1)}>
              <Minus size={20} />
            </button>
            <input
              type="range"
              min={selectedControl.min}
              max={selectedControl.max}
              step={selectedControl.step}
              value={sliderValue}
              onChange={(event) => setSelectedValue(numberValue(event.target.value))}
              className="power-slider"
            />
            <div className="grid h-12 place-items-center rounded-md border border-white/10 bg-graphite-800 px-3 text-center font-mono text-lg text-zinc-50">
              {formatValue(selectedValue, selectedControl.digits)}
            </div>
            <button className="grid h-12 place-items-center rounded-md bg-graphite-800 text-zinc-100" onClick={() => stepSelected(1)}>
              <Plus size={20} />
            </button>
          </div>

          {selectedControl.key === "requested_power_kw" ? (
            powerPercent >= 90 && !validation ? (
              <div className="mt-4 grid gap-2 text-sm">
                <div className="rounded-md border border-signal-amber/50 bg-signal-amber/10 p-3 text-signal-amber">
                  Near configured maximum power.
                </div>
              </div>
            ) : null
          ) : null}
        </div>

        <div className="parameter-options grid gap-2">
          {controls.map((control) => (
            <button
              key={control.key}
              className={`parameter-option flex min-h-12 items-center justify-between gap-3 rounded-md border px-3 text-left ${selectedControl.key === control.key
                ? "border-zinc-100 bg-zinc-100 text-graphite-950"
                : "border-white/10 bg-graphite-900 text-zinc-200"
                }`}
              onClick={() => setSelectedKey(control.key)}
            >
              <span className="text-sm font-semibold">{control.label}</span>
              <span className="font-mono text-sm">
                {formatValue(draft[control.key], control.digits)} {control.unit}
              </span>
            </button>
          ))}
        </div>
      </div>

      <div className="parameter-feedback mt-5 grid gap-3">
        {validation ? (
          <div className="rounded-md border border-signal-red/50 bg-signal-red/10 p-3 text-sm text-signal-red">
            {validation} Use valid values before applying.
          </div>
        ) : null}
        {error ? <div className="rounded-md border border-signal-red/50 bg-signal-red/10 p-3 text-sm text-signal-red">{error}</div> : null}
        {success ? <div className="rounded-md border border-signal-green/40 bg-signal-green/10 p-3 text-sm text-signal-green">{success}</div> : null}
      </div>

      <button
        className="parameter-apply mt-5 flex h-12 w-full items-center justify-center gap-2 rounded-md bg-zinc-100 font-semibold text-graphite-950 disabled:opacity-40"
        disabled={Boolean(validation) || saving}
        onClick={onSubmit}
      >
        <Save size={20} />
        {saving ? "Applying..." : "Apply changes"}
      </button>

      <ConfirmModal
        open={confirmOpen}
        title="Confirm changes"
        message={`Apply parameter changes to ${parameters.charger_id}?`}
        onCancel={() => setConfirmOpen(false)}
        onConfirm={() => {
          setConfirmOpen(false);
          void apply();
        }}
      />
    </section>
  );
}
