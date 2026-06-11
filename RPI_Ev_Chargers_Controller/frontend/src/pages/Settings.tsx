import { useEffect, useState } from "react";
import { getBackendSettings } from "../api/client";
import { ConnectionIndicator } from "../components/ConnectionIndicator";
import type { ChargerStatus, TelemetryConnection } from "../types/telemetry";

const protectionFlags = [
  ["CurrentRegulationFlag", "Current regulation"],
  ["VoltageRegulationFlag", "Voltage regulation"],
  ["ActivePowerRegulationFlag", "Active power regulation"],
  ["ReactivePowerRegulationFlag", "Reactive power regulation"],
  ["MaxBatteryChargingCurrentFlag", "Max charging current"],
  ["MaxBatteryDishargingCurrentFlag", "Max discharging current"],
  ["InputCurrentLimitationFlag", "Input current limitation"],
  ["LoadImpedanceLimitationFlag", "Load impedance limitation"],
  ["ThermalLimitationFlag", "Thermal limitation"],
  ["SafeCFlag", "Safe C"],
] as const;

const faultBits = [
  [1, "Over current L1"],
  [2, "Over current L2"],
  [4, "Over current L3"],
  [8, "Over current L4"],
  [2048, "DC bus overvoltage"],
  [4096, "Battery overvoltage"],
  [8192, "Battery undervoltage"],
  [16384, "Battery overcurrent"],
  [32768, "DCDC primary overtemp"],
  [65536, "DCDC secondary overtemp"],
  [131072, "PFC overtemp"],
  [262144, "Transformer overtemp"],
  [524288, "Ambient overtemp"],
  [268435456, "Charge permission"],
  [536870912, "Address selection"],
  [1073741824, "Precharge failure"],
  [0x80000000, "Battery voltage regulation OV"],
] as const;

export function Settings({
  backendConnected,
  connection,
  chargers
}: {
  backendConnected: boolean;
  connection?: TelemetryConnection | null;
  chargers: ChargerStatus[];
}) {
  const [settings, setSettings] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getBackendSettings()
      .then((data) => {
        setSettings(data);
        setError(null);
      })
      .catch((err: Error) => setError(err.message));
  }, []);

  return (
    <div className="grid gap-4 xl:grid-cols-[1fr_360px]">
      <div className="grid gap-4">
        <ProtectionPanel chargers={chargers} />

        <section className="rounded-lg border border-white/10 bg-graphite-850 p-5 shadow-panel">
          <h2 className="text-xl font-semibold text-zinc-50">Settings</h2>
          {error ? <div className="mt-4 rounded-md border border-signal-red/50 bg-signal-red/10 p-3 text-sm text-signal-red">{error}</div> : null}
          <div className="mt-5 grid gap-3 md:grid-cols-2">
            {settings
              ? Object.entries(settings).map(([key, value]) => (
                  <div key={key} className="rounded-md border border-white/10 bg-graphite-900 p-3">
                    <div className="text-sm text-zinc-500">{key}</div>
                    <div className="mt-1 break-words font-mono text-sm text-zinc-100">{JSON.stringify(value)}</div>
                  </div>
                ))
              : null}
          </div>
        </section>
      </div>

      <aside className="rounded-lg border border-white/10 bg-graphite-850 p-5 shadow-panel">
        <h3 className="mb-4 text-lg font-semibold text-zinc-50">Connection</h3>
        <ConnectionIndicator backendConnected={backendConnected} connection={connection} />
        <div className="mt-5 grid gap-3 text-sm">
          <InfoRow label="Messages" value={String(connection?.message_count ?? 0)} />
          <InfoRow label="Invalid" value={String(connection?.invalid_message_count ?? 0)} />
          <InfoRow label="Endpoint" value={connection?.endpoint ?? "--"} />
          <InfoRow label="Last error" value={connection?.last_error ?? "None"} danger={Boolean(connection?.last_error)} />
        </div>
      </aside>
    </div>
  );
}

function ProtectionPanel({ chargers }: { chargers: ChargerStatus[] }) {
  return (
    <section className="rounded-lg border border-white/10 bg-graphite-850 p-5 shadow-panel">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-xl font-semibold text-zinc-50">Protections</h2>
        <div className="text-sm text-zinc-400">Feedback from TPDO0 fault word and limitation flags</div>
      </div>

      <div className="mt-5 grid gap-3 md:grid-cols-2">
        {chargers.map((charger) => (
          <ProtectionCard key={charger.charger_id} charger={charger} />
        ))}
      </div>
    </section>
  );
}

function ProtectionCard({ charger }: { charger: ChargerStatus }) {
  const raw = charger.telemetry?.raw ?? {};
  const feedbackOk = hasAnyRaw(raw, charger.charger_id, [
    "itfc_critical_fault_word",
    "CurrentRegulationFlag",
    "ThermalLimitationFlag",
  ]);
  const faultWord = rawNumber(raw, charger.charger_id, "itfc_critical_fault_word") ?? 0;
  const unsignedFaultWord = faultWord >>> 0;
  const activeFaults = faultBits.filter(([mask]) => (unsignedFaultWord & (mask >>> 0)) !== 0).map(([, label]) => label);
  const activeLimits = protectionFlags
    .filter(([key]) => Boolean(rawNumber(raw, charger.charger_id, key)))
    .map(([, label]) => label);
  const tone = !feedbackOk ? "unknown" : activeFaults.length > 0 ? "fault" : activeLimits.length > 0 ? "limit" : "ok";

  return (
    <div className="rounded-md border border-white/10 bg-graphite-900 p-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <div className="text-sm text-zinc-500">{charger.charger_id}</div>
          <div className="mt-1 font-mono text-sm text-zinc-300">SystemState {rawNumber(raw, charger.charger_id, "SystemState") ?? "--"}</div>
        </div>
        <ProtectionBadge tone={tone} />
      </div>

      <div className="mt-4 grid gap-2 text-sm">
        <InfoRow label="Protection feedback" value={feedbackOk ? "Monitored" : "Unknown"} danger={!feedbackOk} />
        <InfoRow label="Fault word" value={String(faultWord)} danger={activeFaults.length > 0} />
      </div>

      <ProtectionList title="Active limitations" items={activeLimits} empty="None" warn />
      <ProtectionList title="Critical faults" items={activeFaults} empty="None" danger />
    </div>
  );
}

function ProtectionBadge({ tone }: { tone: "ok" | "limit" | "fault" | "unknown" }) {
  const styles = {
    ok: "border-signal-green/40 bg-signal-green/10 text-signal-green",
    limit: "border-signal-amber/50 bg-signal-amber/10 text-signal-amber",
    fault: "border-signal-red/60 bg-signal-red/10 text-signal-red",
    unknown: "border-zinc-600 bg-zinc-700/40 text-zinc-200",
  };
  const labels = {
    ok: "OK",
    limit: "Limiting",
    fault: "Fault",
    unknown: "Unknown",
  };

  return <span className={`rounded-md border px-3 py-2 text-sm font-semibold ${styles[tone]}`}>{labels[tone]}</span>;
}

function ProtectionList({
  title,
  items,
  empty,
  warn = false,
  danger = false,
}: {
  title: string;
  items: string[];
  empty: string;
  warn?: boolean;
  danger?: boolean;
}) {
  const textClass = danger && items.length > 0 ? "text-signal-red" : warn && items.length > 0 ? "text-signal-amber" : "text-zinc-300";

  return (
    <div className="mt-4">
      <div className="text-sm text-zinc-500">{title}</div>
      <div className={`mt-2 flex flex-wrap gap-2 text-sm ${textClass}`}>
        {items.length > 0
          ? items.map((item) => (
              <span key={item} className="rounded-md border border-white/10 bg-graphite-850 px-2 py-1">
                {item}
              </span>
            ))
          : empty}
      </div>
    </div>
  );
}

function rawNumber(raw: Record<string, unknown>, chargerId: string, key: string) {
  const value = raw[`${chargerId}_${key}`];
  const number = Number(value);
  return Number.isFinite(number) ? number : undefined;
}

function hasAnyRaw(raw: Record<string, unknown>, chargerId: string, keys: string[]) {
  return keys.some((key) => `${chargerId}_${key}` in raw);
}

function InfoRow({ label, value, danger = false }: { label: string; value: string; danger?: boolean }) {
  return (
    <div className="rounded-md border border-white/10 bg-graphite-900 p-3">
      <div className="text-zinc-500">{label}</div>
      <div className={danger ? "mt-1 break-words font-semibold text-signal-red" : "mt-1 break-words font-semibold text-zinc-100"}>{value}</div>
    </div>
  );
}
