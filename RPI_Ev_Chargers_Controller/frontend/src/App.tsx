import { Activity, BarChart3, LayoutDashboard, SlidersHorizontal } from "lucide-react";
import type { ReactNode } from "react";
import { useEffect, useMemo, useState } from "react";
import type { ChargerCommandType } from "./api/commands";
import { clearEvents, getChargers, sendCommand } from "./api/client";
import { connectTelemetry } from "./api/websocket";
import { Header } from "./components/Header";
import { ChargerDetail } from "./pages/ChargerDetail";
import { Dashboard } from "./pages/Dashboard";
import { Parameters } from "./pages/Parameters";
import { Settings } from "./pages/Settings";
import type { ChargerParameters } from "./types/parameters";
import type {
  ChargerEvent,
  ChargerStatus,
  HistoryPoint,
  TelemetryConnection,
  TelemetrySnapshot,
  TelemetrySummary,
  WsTelemetryMessage
} from "./types/telemetry";

type Page = "dashboard" | "detail" | "parameters" | "settings";

const emptySummary: TelemetrySummary = {
  total_power_kw: 0,
  total_energy_kwh: 0,
  active_chargers: 0,
  active_alarms: 0,
  charger_count: 0
};

function upsertStatus(items: ChargerStatus[], status: ChargerStatus) {
  const index = items.findIndex((item) => item.charger_id === status.charger_id);
  if (index === -1) return [...items, status].sort((a, b) => a.charger_id.localeCompare(b.charger_id));
  const next = [...items];
  next[index] = status;
  return next;
}

function appendPoint(points: Record<string, HistoryPoint[]>, point: HistoryPoint) {
  const current = points[point.charger_id] ?? [];
  return {
    ...points,
    [point.charger_id]: [...current, point].slice(-600)
  };
}

function upsertParameters(items: ChargerParameters[], parameters: ChargerParameters) {
  const index = items.findIndex((item) => item.charger_id === parameters.charger_id);
  if (index === -1) return [...items, parameters].sort((a, b) => a.charger_id.localeCompare(b.charger_id));
  const next = [...items];
  next[index] = parameters;
  return next;
}

function globalState(chargers: ChargerStatus[]) {
  if (chargers.some((charger) => ["fault", "safe_d", "lock_dsp"].includes(charger.state))) return "fault";
  if (chargers.some((charger) => charger.state === "warning")) return "warning";
  if (chargers.some((charger) => charger.state === "charging")) return "charging";
  if (chargers.some((charger) => charger.state === "power_on")) return "power on";
  if (chargers.some((charger) => charger.state === "stopping")) return "stopping";
  if (chargers.length > 0 && chargers.every((charger) => charger.state === "offline")) return "offline";
  if (chargers.length > 0 && chargers.every((charger) => charger.state === "standby")) return "standby";
  return "idle";
}

export default function App() {
  const [page, setPage] = useState<Page>("dashboard");
  const [chargers, setChargers] = useState<ChargerStatus[]>([]);
  const [parameters, setParameters] = useState<ChargerParameters[]>([]);
  const [summary, setSummary] = useState<TelemetrySummary>(emptySummary);
  const [connection, setConnection] = useState<TelemetryConnection | null>(null);
  const [backendConnected, setBackendConnected] = useState(false);
  const [events, setEvents] = useState<ChargerEvent[]>([]);
  const [livePoints, setLivePoints] = useState<Record<string, HistoryPoint[]>>({});
  const [selectedChargerId, setSelectedChargerId] = useState<string | undefined>();
  const [currentTime, setCurrentTime] = useState(new Date());

  useEffect(() => {
    getChargers()
      .then((response) => {
        setChargers(response.chargers);
        setParameters(response.parameters ?? []);
        setSummary(response.summary);
        setConnection(response.connection);
        setBackendConnected(true);
      })
      .catch(() => setBackendConnected(false));
  }, []);

  useEffect(() => {
    const timer = window.setInterval(() => setCurrentTime(new Date()), 1000);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    if (!selectedChargerId && chargers.length > 0) {
      setSelectedChargerId(chargers[0].charger_id);
    }
  }, [chargers, selectedChargerId]);

  useEffect(() => {
    const client = connectTelemetry(handleMessage, setBackendConnected);
    return () => client.close();
  }, []);

  const selectedStatus = useMemo(
    () => chargers.find((charger) => charger.charger_id === selectedChargerId) ?? chargers[0],
    [chargers, selectedChargerId]
  );

  const handleMessage = (message: WsTelemetryMessage) => {
    if (message.type === "snapshot" && message.data) {
      const snapshot = message.data as TelemetrySnapshot;
      setChargers(snapshot.chargers);
      setParameters(snapshot.parameters ?? []);
      setSummary(snapshot.summary);
      setConnection(snapshot.connection);
      setEvents(snapshot.events ?? []);
      setLivePoints(snapshot.live_points ?? {});
      return;
    }

    if ((message.type === "telemetry" || message.type === "status") && message.data) {
      const status = message.data as ChargerStatus;
      setChargers((current) => upsertStatus(current, status));
      if (message.point) setLivePoints((current) => appendPoint(current, message.point!));
    }

    if (message.summary) setSummary(message.summary);
    if (message.connection) setConnection(message.connection);
    if (message.type === "parameters" && message.data) {
      setParameters((current) => upsertParameters(current, message.data as ChargerParameters));
    }
    if (message.event) setEvents((current) => [message.event!, ...current].slice(0, 120));
    if (message.events) setEvents(message.events);
    if (message.type === "connection" && message.data) setConnection(message.data as TelemetryConnection);
    if (message.type === "event" && message.data) setEvents((current) => [message.data as ChargerEvent, ...current].slice(0, 120));
  };

  const runCommand = (chargerId: string, command: ChargerCommandType) => {
    sendCommand(chargerId, command).catch((err: Error) => {
      setEvents((current) => [
        {
          id: crypto.randomUUID(),
          timestamp: new Date().toISOString(),
          charger_id: chargerId,
          severity: "error",
          kind: "command_error",
          message: err.message
        },
        ...current
      ]);
    });
  };

  const clearEventLog = () => {
    setEvents([]);
    clearEvents().catch((err: Error) => {
      setEvents((current) => [
        {
          id: crypto.randomUUID(),
          timestamp: new Date().toISOString(),
          severity: "error",
          kind: "events_clear_error",
          message: err.message
        },
        ...current
      ]);
    });
  };

  const openDetail = (chargerId: string) => {
    setSelectedChargerId(chargerId);
    setPage("detail");
  };

  const openParameters = (chargerId: string) => {
    setSelectedChargerId(chargerId);
    setPage("parameters");
  };

  const parametersByCharger = useMemo(
    () => Object.fromEntries(parameters.map((item) => [item.charger_id, item])),
    [parameters]
  );

  const content = (() => {
    if (page === "detail") {
      return (
        <ChargerDetail
          status={selectedStatus}
          chargers={chargers}
          points={selectedStatus ? livePoints[selectedStatus.charger_id] ?? [] : []}
          onBack={() => setPage("dashboard")}
          onSelectCharger={setSelectedChargerId}
          onCommand={runCommand}
          onParameters={openParameters}
        />
      );
    }
    if (page === "parameters") {
      return (
        <Parameters
          chargers={chargers}
          selectedChargerId={selectedStatus?.charger_id}
          onSelectCharger={setSelectedChargerId}
          onBack={() => setPage("dashboard")}
        />
      );
    }
    if (page === "settings") {
      return <Settings backendConnected={backendConnected} connection={connection} chargers={chargers} />;
    }
    return (
      <Dashboard
        chargers={chargers}
        parameters={parametersByCharger}
        summary={summary}
        livePoints={livePoints}
        events={events}
        backendConnected={backendConnected}
        connection={connection}
        onCommand={runCommand}
        onDetails={openDetail}
        onParameters={openParameters}
        onClearEvents={clearEventLog}
      />
    );
  })();

  return (
    <div className="app-root min-h-screen bg-graphite-950 text-zinc-100">
      <Header
        globalState={globalState(chargers)}
        currentTime={currentTime}
        backendConnected={backendConnected}
        connection={connection}
        onSettings={() => setPage("settings")}
      />

      <div className="app-shell">
        <Navigation page={page} onPage={setPage} />
        <main className="kiosk-main min-w-0 flex-1 p-4 pb-24 md:pb-4">{content}</main>
      </div>
      <BottomNavigation page={page} onPage={setPage} />
    </div>
  );
}

function Navigation({ page, onPage }: { page: Page; onPage: (page: Page) => void }) {
  return (
    <nav className="hidden w-20 shrink-0 border-r border-white/10 bg-graphite-900 p-3 md:grid md:content-start md:gap-3">
      <NavButton active={page === "dashboard"} label="Dashboard" icon={<LayoutDashboard size={22} />} onClick={() => onPage("dashboard")} />
      <NavButton active={page === "detail"} label="Detail" icon={<BarChart3 size={22} />} onClick={() => onPage("detail")} />
      <NavButton active={page === "parameters"} label="Parameters" icon={<SlidersHorizontal size={22} />} onClick={() => onPage("parameters")} />
      <NavButton active={page === "settings"} label="Settings" icon={<Activity size={22} />} onClick={() => onPage("settings")} />
    </nav>
  );
}

function BottomNavigation({ page, onPage }: { page: Page; onPage: (page: Page) => void }) {
  return (
    <nav className="fixed bottom-0 left-0 right-0 z-40 grid grid-cols-4 border-t border-white/10 bg-graphite-900 p-2 md:hidden">
      <NavButton active={page === "dashboard"} label="Dash" icon={<LayoutDashboard size={22} />} onClick={() => onPage("dashboard")} />
      <NavButton active={page === "detail"} label="Detail" icon={<BarChart3 size={22} />} onClick={() => onPage("detail")} />
      <NavButton active={page === "parameters"} label="Params" icon={<SlidersHorizontal size={22} />} onClick={() => onPage("parameters")} />
      <NavButton active={page === "settings"} label="Set" icon={<Activity size={22} />} onClick={() => onPage("settings")} />
    </nav>
  );
}

function NavButton({
  active,
  icon,
  label,
  onClick
}: {
  active: boolean;
  icon: ReactNode;
  label: string;
  onClick: () => void;
}) {
  return (
    <button
      className={`nav-button flex min-h-14 flex-col items-center justify-center gap-1 rounded-md text-xs font-semibold ${
        active ? "bg-zinc-100 text-graphite-950" : "text-zinc-400"
      }`}
      title={label}
      onClick={onClick}
    >
      {icon}
      <span>{label}</span>
    </button>
  );
}
