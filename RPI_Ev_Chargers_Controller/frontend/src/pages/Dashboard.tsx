import { useMemo, useState } from "react";
import type { ChargerCommandType } from "../api/commands";
import { ChargerCard } from "../components/ChargerCard";
import { ConnectionIndicator } from "../components/ConnectionIndicator";
import { EventLog } from "../components/EventLog";
import { MetricCard } from "../components/MetricCard";
import { TelemetryChart, type ChartPoint, type ChartSeries, type ChartYAxisDomain } from "../components/TelemetryChart";
import type { ChargerParameters } from "../types/parameters";
import type { ChargerEvent, ChargerStatus, HistoryPoint, TelemetryConnection, TelemetrySummary } from "../types/telemetry";

const chargerColors = [
  "#22d3ee",
  "#36d399",
  "#fbbf24",
  "#fb7185",
  "#a78bfa",
  "#f97316"
];

const chartWindowOptions = [
  { label: "1 min", ms: 60_000, bucketMs: 1000 },
  { label: "5 min", ms: 300_000, bucketMs: 2000 },
  { label: "15 min", ms: 900_000, bucketMs: 5000 }
] as const;

const minScaledVoltage = 10;

function fmt(value: number | undefined, digits = 1) {
  return typeof value === "number" && Number.isFinite(value) ? value.toFixed(digits) : "--";
}

function voltageDomain(points: ChartPoint[], chargerIds: string[], keySuffix: "vin" | "vout"): ChartYAxisDomain | undefined {
  const values = points.flatMap((point) =>
    chargerIds
      .map((chargerId) => (point as Record<string, unknown>)[`${chargerId}_${keySuffix}`])
      .filter((value): value is number => (
        typeof value === "number"
        && Number.isFinite(value)
        && value > minScaledVoltage
      ))
  );

  if (values.length === 0) return undefined;

  const dataMin = Math.min(...values);
  const dataMax = Math.max(...values);
  const span = Math.max(0, dataMax - dataMin);
  const reference = Math.max(Math.abs(dataMin), Math.abs(dataMax), 1);
  const padding = span > 0 ? Math.max(span * 0.12, reference * 0.02) : Math.max(reference * 0.02, 1);

  return [dataMin - padding, dataMax + padding];
};

export function Dashboard({
  chargers,
  parameters,
  summary,
  livePoints,
  events,
  backendConnected,
  connection,
  onCommand,
  onDetails,
  onParameters,
  onPowerSetpoint,
  powerSaving,
  powerErrors,
  onClearEvents
}: {
  chargers: ChargerStatus[];
  parameters: Record<string, ChargerParameters>;
  summary?: TelemetrySummary | null;
  livePoints: Record<string, HistoryPoint[]>;
  events: ChargerEvent[];
  backendConnected: boolean;
  connection?: TelemetryConnection | null;
  onCommand: (chargerId: string, command: ChargerCommandType) => void;
  onDetails: (chargerId: string) => void;
  onParameters: (chargerId: string) => void;
  onPowerSetpoint: (chargerId: string, requestedPowerKw: number) => Promise<void>;
  powerSaving: Record<string, boolean>;
  powerErrors: Record<string, string | null>;
  onClearEvents: () => void;
}) {
  const [chartWindow, setChartWindow] = useState<(typeof chartWindowOptions)[number]>(chartWindowOptions[0]);

  const chartChargerIds = useMemo(() => {
    const ids = chargers.map((charger) => charger.charger_id);
    if (ids.length > 0) return ids;
    return Object.keys(livePoints).sort((a, b) => a.localeCompare(b));
  }, [chargers, livePoints]);

  const chartPoints = useMemo<ChartPoint[]>(() => {
    const latestTimestamp = Math.max(
      ...Object.values(livePoints)
        .flatMap((points) => points.map((point) => new Date(point.timestamp).getTime()))
        .filter(Number.isFinite)
    );
    const windowStart = Number.isFinite(latestTimestamp) ? latestTimestamp - chartWindow.ms : 0;

    return Object.entries(livePoints)
      .flatMap(([chargerId, points]) =>
        points
          .filter((point) => {
            const timestamp = new Date(point.timestamp).getTime();
            return Number.isFinite(timestamp) && timestamp >= windowStart;
          })
          .map((point) => ({
            charger_id: chargerId,
            timestamp: point.timestamp,
            state: point.state,
            [`${chargerId}_vin`]: point.vin,
            [`${chargerId}_iout`]: point.iout,
            [`${chargerId}_vout`]: point.vout,
            [`${chargerId}_pout`]: point.pout
          }))
      )
      .sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());
  }, [livePoints, chartWindow.ms]);

  const inputVoltageDomain = useMemo(
    () => voltageDomain(chartPoints, chartChargerIds, "vin"),
    [chartPoints, chartChargerIds]
  );

  const outputVoltageDomain = useMemo(
    () => voltageDomain(chartPoints, chartChargerIds, "vout"),
    [chartPoints, chartChargerIds]
  );

  const chartPanels = useMemo<Array<{ title: string; series: ChartSeries[]; yDomain?: ChartYAxisDomain; yAllowDataOverflow?: boolean }>>(
    () => [
      {
        title: "Output Current",
        series: chartChargerIds.map((chargerId, index) => ({
          key: `${chargerId}_iout`,
          name: chargerId,
          color: chargerColors[index % chargerColors.length],
          unit: "A"
        }))
      },
      {
        title: "Input Voltage",
        yDomain: inputVoltageDomain,
        yAllowDataOverflow: Boolean(inputVoltageDomain),
        series: chartChargerIds.map((chargerId, index) => ({
          key: `${chargerId}_vin`,
          name: chargerId,
          color: chargerColors[index % chargerColors.length],
          unit: "V"
        }))
      },
      {
        title: "Output Voltage",
        yDomain: outputVoltageDomain,
        yAllowDataOverflow: Boolean(outputVoltageDomain),
        series: chartChargerIds.map((chargerId, index) => ({
          key: `${chargerId}_vout`,
          name: chargerId,
          color: chargerColors[index % chargerColors.length],
          unit: "V"
        }))
      },
      {
        title: "Output Power",
        series: chartChargerIds.map((chargerId, index) => ({
          key: `${chargerId}_pout`,
          name: chargerId,
          color: chargerColors[index % chargerColors.length],
          unit: "kW",
          scale: (value) => value / 1000
        }))
      }
    ],
    [chartChargerIds, inputVoltageDomain, outputVoltageDomain]
  );

  return (
    <div className="dashboard-screen grid gap-4">
      <div className="dashboard-summary grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard label="Total Power" value={fmt(summary?.total_power_kw)} unit="kW" tone="good" />
        <MetricCard label="Energy" value={fmt(summary?.total_energy_kwh, 2)} unit="kWh" />
        <MetricCard label="Active" value={String(summary?.active_chargers ?? 0)} unit="chargers" />
        <MetricCard
          label="Alarms"
          value={String(summary?.active_alarms ?? 0)}
          tone={(summary?.active_alarms ?? 0) > 0 ? "danger" : "default"}
        />
      </div>

      <div className="dashboard-chargers grid gap-4 lg:grid-cols-2">
        {chargers.map((status) => (
          <ChargerCard
            key={status.charger_id}
            status={status}
            parameters={parameters[status.charger_id]}
            onCommand={onCommand}
            onDetails={onDetails}
            onParameters={onParameters}
            onPowerSetpoint={onPowerSetpoint}
            powerSaving={Boolean(powerSaving[status.charger_id])}
            powerError={powerErrors[status.charger_id]}
          />
        ))}
      </div>

      <section className="dashboard-chart rounded-lg border border-white/10 bg-graphite-850 p-4 shadow-panel">
        <div className="dashboard-chart-toolbar mb-2 flex items-center justify-between gap-3">
          <div className="text-sm font-semibold text-zinc-100">Live Trends</div>
          <div className="flex rounded-md border border-white/10 bg-graphite-900 p-1">
            {chartWindowOptions.map((option) => (
              <button
                key={option.label}
                className={`h-9 rounded px-3 text-sm font-semibold ${
                  chartWindow.label === option.label
                    ? "bg-zinc-100 text-graphite-950"
                    : "text-zinc-400"
                }`}
                onClick={() => setChartWindow(option)}
              >
                {option.label}
              </button>
            ))}
          </div>
        </div>
        <div className="dashboard-chart-grid grid grid-cols-2 gap-3 xl:grid-cols-4">
          {chartPanels.map((panel) => (
            <div key={panel.title} className="mini-chart grid min-h-[150px] min-w-0 grid-rows-[auto_minmax(0,1fr)] rounded-md border border-white/10 bg-graphite-900 p-2">
              <div className="mb-1 text-sm font-semibold text-zinc-100">{panel.title}</div>
              <TelemetryChart
                points={chartPoints}
                series={panel.series}
                height="100%"
                compact
                maxPoints={240}
                bucketMs={chartWindow.bucketMs}
                dropOpenBucket
                showDots={false}
                yDomain={panel.yDomain}
                yAllowDataOverflow={panel.yAllowDataOverflow}
              />
            </div>
          ))}
        </div>
      </section>

      <aside className="dashboard-side grid content-start gap-4">
        <div className="lg:hidden">
          <ConnectionIndicator backendConnected={backendConnected} connection={connection} />
        </div>
        <EventLog events={events} onClear={onClearEvents} />
      </aside>
    </div>
  );
}
