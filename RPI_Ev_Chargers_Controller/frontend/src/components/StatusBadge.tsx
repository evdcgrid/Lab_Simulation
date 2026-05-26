import type { ChargerState } from "../types/telemetry";

const defaultStyle = "border-zinc-500 bg-zinc-600/30 text-zinc-100";

const styles: Partial<Record<ChargerState, string>> = {
  offline: "border-zinc-600 bg-zinc-700/40 text-zinc-200",
  idle: "border-signal-cyan/40 bg-signal-cyan/10 text-signal-cyan",
  init: "border-zinc-500 bg-zinc-600/30 text-zinc-100",
  standby: "border-sky-400/50 bg-sky-400/10 text-sky-300",
  power_on: "border-signal-amber/50 bg-signal-amber/10 text-signal-amber",
  charging: "border-signal-green/40 bg-signal-green/10 text-signal-green",
  safe_d: "border-signal-red/60 bg-signal-red/10 text-signal-red",
  stopping: "border-signal-amber/50 bg-signal-amber/10 text-signal-amber",
  lock_dsp: "border-signal-red/60 bg-signal-red/10 text-signal-red",
  fault_ack: "border-signal-amber/50 bg-signal-amber/10 text-signal-amber",
  warning: "border-signal-amber/50 bg-signal-amber/10 text-signal-amber",
  fault: "border-signal-red/60 bg-signal-red/10 text-signal-red",
  stale: "border-zinc-500 bg-zinc-600/30 text-zinc-100"
};

const labels: Partial<Record<ChargerState, string>> = {
  offline: "Offline",
  idle: "Idle",
  init: "Init",
  standby: "Standby",
  power_on: "Power On",
  charging: "Charging",
  safe_d: "Safe D",
  stopping: "Stopping",
  lock_dsp: "Lock DSP",
  fault_ack: "Fault Ack",
  warning: "Warning",
  fault: "Fault",
  stale: "Stale"
};

export function formatStateLabel(state: string) {
  return labels[state as ChargerState] ?? state.replace(/_/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export function StatusBadge({ state }: { state: ChargerState }) {
  return (
    <span className={`inline-flex min-h-8 items-center rounded-md border px-3 text-sm font-semibold ${styles[state] ?? defaultStyle}`}>
      {formatStateLabel(state)}
    </span>
  );
}
