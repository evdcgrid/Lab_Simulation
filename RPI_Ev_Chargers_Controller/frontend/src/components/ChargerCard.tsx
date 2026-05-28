import { BarChart3, Minus, Play, Plus, Save, SlidersHorizontal, Square } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import type { ChargerCommandType } from "../api/commands";
import { useDisplayValue } from "../hooks/useDisplayValue";
import type { ChargerParameters } from "../types/parameters";
import type { ChargerStatus } from "../types/telemetry";
import { StatusBadge } from "./StatusBadge";

function fmt(value?: number | null, digits = 1) {
  return typeof value === "number" && Number.isFinite(value) ? value.toFixed(digits) : "--";
}

const DASHBOARD_POWER_STEP_KW = 0.25;

function clamp(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value));
}

function decimalPlaces(step: number) {
  const [, decimals = ""] = String(step).split(".");
  return decimals.length;
}

function snapToStep(value: number, step: number) {
  const decimals = decimalPlaces(step);
  return Number((Math.round(value / step) * step).toFixed(decimals));
}

interface ChargerCardProps {
  status: ChargerStatus;
  parameters?: ChargerParameters;
  onCommand: (chargerId: string, command: ChargerCommandType) => void;
  onDetails: (chargerId: string) => void;
  onParameters: (chargerId: string) => void;
  onPowerSetpoint: (chargerId: string, requestedPowerKw: number) => Promise<void>;
  powerSaving?: boolean;
  powerError?: string | null;
}

export function ChargerCard({
  status,
  parameters,
  onCommand,
  onDetails,
  onParameters,
  onPowerSetpoint,
  powerSaving = false,
  powerError = null
}: ChargerCardProps) {
  const telemetry = useDisplayValue(status.telemetry, 500);
  const isFault = ["fault", "safe_d", "lock_dsp"].includes(status.state);
  const setpointKw = parameters?.applied_power_kw ?? parameters?.requested_power_kw;
  const powerLimit = parameters?.parameter_limits?.requested_power_kw;
  const minPowerKw = powerLimit?.min ?? 0;
  const maxPowerKw = powerLimit?.max ?? parameters?.max_allowed_power_kw;
  const powerStepKw = DASHBOARD_POWER_STEP_KW;
  const [draftPowerKw, setDraftPowerKw] = useState(setpointKw ?? 0);

  useEffect(() => {
    setDraftPowerKw(setpointKw ?? 0);
  }, [setpointKw]);

  const sliderPowerKw = useMemo(() => {
    if (maxPowerKw === undefined) return draftPowerKw;
    return clamp(draftPowerKw, minPowerKw, maxPowerKw);
  }, [draftPowerKw, maxPowerKw, minPowerKw]);

  const setpointPercent = setpointKw !== undefined && maxPowerKw ? (setpointKw / maxPowerKw) * 100 : undefined;
  const draftPercent = maxPowerKw ? (sliderPowerKw / maxPowerKw) * 100 : 0;
  const powerChanged = parameters ? Math.abs(sliderPowerKw - (parameters.requested_power_kw ?? 0)) >= powerStepKw / 2 : false;
  const powerDisabled = !parameters || maxPowerKw === undefined || powerSaving;

  const setPower = (value: number) => {
    if (maxPowerKw === undefined) return;
    setDraftPowerKw(snapToStep(clamp(value, minPowerKw, maxPowerKw), powerStepKw));
  };

  const applyPower = () => {
    if (powerDisabled || !powerChanged) return;
    void onPowerSetpoint(status.charger_id, sliderPowerKw);
  };

  return (
    <section
      className={`charger-card rounded-lg border bg-graphite-850 p-4 shadow-panel ${
        isFault ? "border-signal-red/50" : "border-white/10"
      }`}
    >
      <div className="charger-head flex items-start justify-between gap-3">
        <div>
          <div className="charger-id text-sm text-zinc-400">{status.charger_id}</div>
          <div className="charger-status mt-2">
            <StatusBadge state={status.state} />
          </div>
        </div>
      </div>

      <div className="charger-primary mt-5 grid grid-cols-3 gap-3">
        <div>
          <div className="charger-primary-label text-xs uppercase text-zinc-500">Vout</div>
          <div className="charger-primary-value">
            <span className="font-mono text-3xl font-semibold text-zinc-50">{fmt(telemetry?.vout)}</span>
            <span className="charger-primary-unit text-sm text-zinc-500">V</span>
          </div>
        </div>
        <div>
          <div className="charger-primary-label text-xs uppercase text-zinc-500">Iout</div>
          <div className="charger-primary-value">
            <span className="font-mono text-3xl font-semibold text-zinc-50">{fmt(telemetry?.iout)}</span>
            <span className="charger-primary-unit text-sm text-zinc-500">A</span>
          </div>
        </div>
        <div>
          <div className="charger-primary-label text-xs uppercase text-zinc-500">Pout</div>
          <div className="charger-primary-value">
            <span className="font-mono text-3xl font-semibold text-signal-green">
              {fmt((telemetry?.pout ?? 0) / 1000)}
            </span>
            <span className="charger-primary-unit text-sm text-zinc-500">kW</span>
          </div>
        </div>
      </div>

      <div className="charger-secondary mt-4 grid grid-cols-3 gap-3 rounded-md border border-white/10 bg-graphite-900 p-3">
        <div>
          <div className="text-xs text-zinc-500">Vin</div>
          <div className="font-mono text-lg text-zinc-100">{fmt(telemetry?.vin)} V</div>
        </div>
        <div>
          <div className="text-xs text-zinc-500">Eff</div>
          <div className="font-mono text-lg text-zinc-100">{fmt(telemetry?.efficiency)}%</div>
        </div>
        <div>
          <div className="text-xs text-zinc-500">Energy</div>
          <div className="font-mono text-lg text-zinc-100">{fmt(telemetry?.energy_session_kwh, 2)} kWh</div>
        </div>
      </div>

      <div className="charger-setpoint mt-3 rounded-md border border-white/10 bg-graphite-900/80 p-3">
        <div className="grid grid-cols-3 gap-3">
          <div>
            <div className="text-xs text-zinc-500">Set</div>
            <div className="font-mono text-lg text-zinc-100">{fmt(setpointKw, 2)} kW</div>
          </div>
          <div>
            <div className="text-xs text-zinc-500">Max</div>
            <div className="font-mono text-lg text-signal-cyan">{fmt(maxPowerKw, 2)} kW</div>
          </div>
          <div>
            <div className="text-xs text-zinc-500">Limit</div>
            <div className={setpointPercent !== undefined && setpointPercent >= 90 ? "font-mono text-lg text-signal-amber" : "font-mono text-lg text-zinc-100"}>
              {fmt(setpointPercent, 0)}%
            </div>
          </div>
        </div>

        <div className="charger-power-control mt-3 grid grid-cols-[42px_1fr_78px_42px_48px] items-center gap-2">
          <button
            className="grid h-11 place-items-center rounded-md bg-graphite-800 text-zinc-100 disabled:opacity-40"
            disabled={powerDisabled}
            onClick={() => setPower(sliderPowerKw - powerStepKw)}
            title="Decrease power"
          >
            <Minus size={18} />
          </button>
          <input
            type="range"
            min={minPowerKw}
            max={maxPowerKw ?? 0}
            step={powerStepKw}
            value={sliderPowerKw}
            tabIndex={-1}
            aria-readonly="true"
            onChange={() => undefined}
            className="power-slider power-slider-indicator"
          />
          <div className={draftPercent >= 90 ? "charger-power-readout grid h-11 place-items-center rounded-md border border-signal-amber/40 bg-signal-amber/10 px-2 text-center font-mono text-sm text-signal-amber" : "charger-power-readout grid h-11 place-items-center rounded-md border border-white/10 bg-graphite-800 px-2 text-center font-mono text-sm text-zinc-50"}>
            {fmt(sliderPowerKw, 2)} kW
          </div>
          <button
            className="grid h-11 place-items-center rounded-md bg-graphite-800 text-zinc-100 disabled:opacity-40"
            disabled={powerDisabled}
            onClick={() => setPower(sliderPowerKw + powerStepKw)}
            title="Increase power"
          >
            <Plus size={18} />
          </button>
          <button
            className="grid h-11 place-items-center rounded-md bg-zinc-100 text-graphite-950 disabled:opacity-40"
            disabled={powerDisabled || !powerChanged}
            onClick={applyPower}
            title="Apply power"
          >
            <Save size={18} />
          </button>
        </div>

        {powerError ? <div className="mt-2 text-xs font-semibold text-signal-red">{powerError}</div> : null}
      </div>

      {(status.fault_code || status.warning_code) && (
        <div className="mt-3 rounded-md border border-signal-red/50 bg-signal-red/10 p-3 text-sm text-signal-red">
          {status.fault_code ? `Fault ${status.fault_code}` : `Warning ${status.warning_code}`}
        </div>
      )}

      <div className="charger-actions mt-4 grid grid-cols-4 gap-2">
        <button
          className="flex h-12 items-center justify-center gap-2 rounded-md bg-signal-green font-semibold text-graphite-950"
          onClick={() => onCommand(status.charger_id, "start")}
        >
          <Play size={18} />
          Start
        </button>
        <button
          className="flex h-12 items-center justify-center gap-2 rounded-md bg-signal-red font-semibold text-graphite-950"
          onClick={() => onCommand(status.charger_id, "stop")}
        >
          <Square size={18} />
          Stop
        </button>
        <button
          className="flex h-12 items-center justify-center gap-2 rounded-md border border-white/10 bg-graphite-800 text-zinc-100"
          onClick={() => onDetails(status.charger_id)}
        >
          <BarChart3 size={18} />
          Details
        </button>
        <button
          className="grid h-12 place-items-center rounded-md border border-white/10 bg-graphite-800 text-zinc-100"
          title="Parameters"
          onClick={() => onParameters(status.charger_id)}
        >
          <SlidersHorizontal size={20} />
        </button>
      </div>
    </section>
  );
}
