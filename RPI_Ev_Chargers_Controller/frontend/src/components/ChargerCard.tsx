import { BarChart3, Play, SlidersHorizontal, Square } from "lucide-react";
import type { ChargerCommandType } from "../api/commands";
import { useDisplayValue } from "../hooks/useDisplayValue";
import type { ChargerParameters } from "../types/parameters";
import type { ChargerStatus } from "../types/telemetry";
import { StatusBadge } from "./StatusBadge";

function fmt(value?: number | null, digits = 1) {
  return typeof value === "number" && Number.isFinite(value) ? value.toFixed(digits) : "--";
}

interface ChargerCardProps {
  status: ChargerStatus;
  parameters?: ChargerParameters;
  onCommand: (chargerId: string, command: ChargerCommandType) => void;
  onDetails: (chargerId: string) => void;
  onParameters: (chargerId: string) => void;
}

export function ChargerCard({ status, parameters, onCommand, onDetails, onParameters }: ChargerCardProps) {
  const telemetry = useDisplayValue(status.telemetry, 500);
  const isFault = ["fault", "safe_d", "lock_dsp"].includes(status.state);
  const setpointKw = parameters?.applied_power_kw ?? parameters?.requested_power_kw;
  const maxPowerKw = parameters?.max_allowed_power_kw;
  const setpointPercent = setpointKw !== undefined && maxPowerKw ? (setpointKw / maxPowerKw) * 100 : undefined;

  return (
    <section
      className={`charger-card rounded-lg border bg-graphite-850 p-4 shadow-panel ${
        isFault ? "border-signal-red/50" : "border-white/10"
      }`}
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="text-sm text-zinc-400">{status.charger_id}</div>
          <div className="mt-2">
            <StatusBadge state={status.state} />
          </div>
        </div>
      </div>

      <div className="charger-primary mt-5 grid grid-cols-3 gap-3">
        <div>
          <div className="text-xs uppercase text-zinc-500">Vout</div>
          <div className="mt-1 font-mono text-3xl font-semibold text-zinc-50">{fmt(telemetry?.vout)}</div>
          <div className="text-sm text-zinc-500">V</div>
        </div>
        <div>
          <div className="text-xs uppercase text-zinc-500">Iout</div>
          <div className="mt-1 font-mono text-3xl font-semibold text-zinc-50">{fmt(telemetry?.iout)}</div>
          <div className="text-sm text-zinc-500">A</div>
        </div>
        <div>
          <div className="text-xs uppercase text-zinc-500">Pout</div>
          <div className="mt-1 font-mono text-3xl font-semibold text-signal-green">
            {fmt((telemetry?.pout ?? 0) / 1000)}
          </div>
          <div className="text-sm text-zinc-500">kW</div>
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

      <div className="charger-setpoint mt-3 grid grid-cols-3 gap-3 rounded-md border border-white/10 bg-graphite-900/80 p-3">
        <div>
          <div className="text-xs text-zinc-500">Set</div>
          <div className="font-mono text-lg text-zinc-100">{fmt(setpointKw)} kW</div>
        </div>
        <div>
          <div className="text-xs text-zinc-500">Max</div>
          <div className="font-mono text-lg text-signal-cyan">{fmt(maxPowerKw)} kW</div>
        </div>
        <div>
          <div className="text-xs text-zinc-500">Limit</div>
          <div className={setpointPercent !== undefined && setpointPercent >= 90 ? "font-mono text-lg text-signal-amber" : "font-mono text-lg text-zinc-100"}>
            {fmt(setpointPercent, 0)}%
          </div>
        </div>
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
