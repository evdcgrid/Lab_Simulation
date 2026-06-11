import { ChevronLeft, Play, RotateCcw, Square } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import type { ChargerCommandType } from "../api/commands";
import { getHistory } from "../api/client";
import { MetricCard } from "../components/MetricCard";
import { StatusBadge } from "../components/StatusBadge";
import { TelemetryChart, type ChartSeries } from "../components/TelemetryChart";
import { TimeRangeSelector, type TimeRange } from "../components/TimeRangeSelector";
import type { ChargerStatus, HistoryPoint } from "../types/telemetry";

const detailTabs: Record<string, ChartSeries[]> = {
  "Vin/Vout": [
    { key: "vin", name: "Vin", color: "#a7b0bc", unit: "V" },
    { key: "vout", name: "Vout", color: "#22d3ee", unit: "V" }
  ],
  "Iin/Iout": [
    { key: "iin", name: "Iin", color: "#a7b0bc", unit: "A" },
    { key: "iout", name: "Iout", color: "#36d399", unit: "A" }
  ],
  "Pin/Pout": [
    { key: "pin", name: "Pin", color: "#a7b0bc", unit: "kW", scale: (value) => value / 1000 },
    { key: "pout", name: "Pout", color: "#fbbf24", unit: "kW", scale: (value) => value / 1000 }
  ]
};

const rangeMs: Record<TimeRange, number> = {
  "1m": 60_000,
  "5m": 300_000,
  "15m": 900_000,
  "1h": 3_600_000
};

const historyLimitByRange: Record<TimeRange, number> = {
  "1m": 900,
  "5m": 1500,
  "15m": 1800,
  "1h": 2400
};

const chartPointLimitByRange: Record<TimeRange, number> = {
  "1m": 600,
  "5m": 900,
  "15m": 900,
  "1h": 900
};

const chartBucketMsByRange: Record<TimeRange, number> = {
  "1m": 500,
  "5m": 1000,
  "15m": 2000,
  "1h": 5000
};

const historyRefreshMsByRange: Record<TimeRange, number> = {
  "1m": 10_000,
  "5m": 20_000,
  "15m": 30_000,
  "1h": 60_000
};

const emptyPoints: HistoryPoint[] = [];

function fmt(value?: number | null, digits = 1) {
  return typeof value === "number" && Number.isFinite(value) ? value.toFixed(digits) : "--";
}

export function ChargerDetail({
  status,
  chargers,
  points,
  onBack,
  onSelectCharger,
  onCommand,
  onParameters
}: {
  status?: ChargerStatus;
  chargers: ChargerStatus[];
  points: HistoryPoint[];
  onBack: () => void;
  onSelectCharger: (chargerId: string) => void;
  onCommand: (chargerId: string, command: ChargerCommandType) => void;
  onParameters: (chargerId: string) => void;
}) {
  const [tab, setTab] = useState("Pin/Pout");
  const [range, setRange] = useState<TimeRange>("5m");
  const [historyPoints, setHistoryPoints] = useState<HistoryPoint[]>([]);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const telemetry = status?.telemetry;
  const selectedChargerId = status?.charger_id;
  const activeSeries = detailTabs[tab];

  useEffect(() => {
    if (!selectedChargerId) {
      setHistoryPoints([]);
      setHistoryError(null);
      return;
    }

    let cancelled = false;
    let controller: AbortController | null = null;

    const loadHistory = () => {
      controller?.abort();
      controller = new AbortController();
      const to = new Date();
      const from = new Date(to.getTime() - rangeMs[range]);

      getHistory({
        chargerId: selectedChargerId,
        from: from.toISOString(),
        to: to.toISOString(),
        signals: activeSeries.map((item) => String(item.key)),
        limit: historyLimitByRange[range],
        signal: controller.signal
      })
        .then((response) => {
          if (cancelled) return;
          setHistoryPoints(response.samples);
          setHistoryError(null);
        })
        .catch((err: Error) => {
          if (cancelled || err.name === "AbortError") return;
          setHistoryError(err.message);
        });
    };

    loadHistory();
    const timer = window.setInterval(loadHistory, historyRefreshMsByRange[range]);

    return () => {
      cancelled = true;
      window.clearInterval(timer);
      controller?.abort();
    };
  }, [activeSeries, range, selectedChargerId]);

  const livePointsForChart = range === "1m" || range === "5m" ? points : emptyPoints;

  const chartPoints = useMemo(() => {
    const cutoff = Date.now() - rangeMs[range];
    const byTimestamp = new Map<string, HistoryPoint>();

    for (const point of [...historyPoints, ...livePointsForChart]) {
      if (selectedChargerId && point.charger_id !== selectedChargerId) continue;
      const timestampMs = new Date(point.timestamp).getTime();
      if (!Number.isFinite(timestampMs) || timestampMs < cutoff) continue;
      byTimestamp.set(point.timestamp, point);
    }

    return [...byTimestamp.values()].sort(
      (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
    );
  }, [historyPoints, livePointsForChart, range, selectedChargerId]);

  if (!status) {
    return (
      <div className="rounded-lg border border-white/10 bg-graphite-850 p-6 text-zinc-300">
        No charger selected
      </div>
    );
  }

  return (
    <div className="grid gap-4 xl:grid-cols-[1fr_320px]">
      <div className="grid gap-4">
        <div className="flex flex-wrap items-center gap-3">
          <button className="grid h-12 w-12 place-items-center rounded-md border border-white/10 bg-graphite-850" onClick={onBack}>
            <ChevronLeft size={24} />
          </button>
          <div>
            <h2 className="text-2xl font-semibold text-zinc-50">{status.charger_id}</h2>
            <div className="mt-1 text-sm text-zinc-400">Updated {status.seconds_since_last_message?.toFixed(1) ?? "--"} s ago</div>
          </div>
          <select
            value={status.charger_id}
            className="h-12 min-w-[120px] rounded-md border border-white/10 bg-graphite-850 px-3 text-base font-semibold text-zinc-50 outline-none"
            onChange={(event) => onSelectCharger(event.target.value)}
          >
            {chargers.map((charger) => (
              <option key={charger.charger_id} value={charger.charger_id}>
                {charger.charger_id}
              </option>
            ))}
          </select>
          <div className="ml-auto">
            <StatusBadge state={status.state} />
          </div>
        </div>

        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <MetricCard label="Vout" value={fmt(telemetry?.vout)} unit="V" />
          <MetricCard label="Iout" value={fmt(telemetry?.iout)} unit="A" />
          <MetricCard label="Pout" value={fmt((telemetry?.pout ?? 0) / 1000)} unit="kW" tone="good" />
          <MetricCard label="Efficiency" value={fmt(telemetry?.efficiency)} unit="%" />
        </div>

        <section className="rounded-lg border border-white/10 bg-graphite-850 p-4 shadow-panel">
          <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
            <div className="grid grid-cols-3 rounded-lg border border-white/10 bg-graphite-900 p-1">
              {Object.keys(detailTabs).map((item) => (
                <button
                  key={item}
                  className={`h-12 rounded-md px-3 text-sm font-semibold ${
                    tab === item ? "bg-zinc-100 text-graphite-950" : "text-zinc-300"
                  }`}
                  onClick={() => setTab(item)}
                >
                  {item}
                </button>
              ))}
            </div>
            <TimeRangeSelector value={range} onChange={setRange} />
          </div>
          <TelemetryChart
            points={chartPoints}
            series={activeSeries}
            height={330}
            maxPoints={chartPointLimitByRange[range]}
            bucketMs={chartBucketMsByRange[range]}
            showDots={false}
          />
          {historyError ? (
            <div className="mt-3 rounded-md border border-signal-amber/40 bg-signal-amber/10 p-3 text-sm text-signal-amber">
              History unavailable: {historyError}
            </div>
          ) : null}
        </section>
      </div>

      <aside className="rounded-lg border border-white/10 bg-graphite-850 p-4 shadow-panel">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-zinc-50">Controls</h3>
          <StatusBadge state={status.state} />
        </div>

        <div className="mt-5 grid gap-3">
          <button className="flex h-12 items-center justify-center gap-2 rounded-md bg-signal-green font-semibold text-graphite-950" onClick={() => onCommand(status.charger_id, "start")}>
            <Play size={18} />
            Start
          </button>
          <button className="flex h-12 items-center justify-center gap-2 rounded-md bg-signal-red font-semibold text-graphite-950" onClick={() => onCommand(status.charger_id, "stop")}>
            <Square size={18} />
            Stop
          </button>
          <button className="flex h-12 items-center justify-center gap-2 rounded-md border border-white/10 bg-graphite-800 text-zinc-100" onClick={() => onCommand(status.charger_id, "reset_fault")}>
            <RotateCcw size={18} />
            Reset Fault
          </button>
          <button className="h-12 rounded-md border border-white/10 bg-zinc-100 font-semibold text-graphite-950" onClick={() => onParameters(status.charger_id)}>
            Edit Parameters
          </button>
        </div>

        <div className="mt-6 grid gap-3 text-sm">
          <InfoRow label="Fault" value={status.fault_code ?? "None"} danger={Boolean(status.fault_code)} />
          <InfoRow label="Warning" value={status.warning_code ?? "None"} danger={Boolean(status.warning_code)} />
          <InfoRow label="Last update" value={status.last_update ? new Date(status.last_update).toLocaleTimeString() : "--"} />
        </div>
      </aside>
    </div>
  );
}

function InfoRow({ label, value, danger = false }: { label: string; value: string; danger?: boolean }) {
  return (
    <div className="flex items-center justify-between rounded-md border border-white/10 bg-graphite-900 p-3">
      <span className="text-zinc-400">{label}</span>
      <span className={danger ? "font-semibold text-signal-red" : "font-semibold text-zinc-100"}>{value}</span>
    </div>
  );
}
