import { Settings } from "lucide-react";
import { ConnectionIndicator } from "./ConnectionIndicator";
import type { TelemetryConnection } from "../types/telemetry";

interface HeaderProps {
  globalState: string;
  currentTime: Date;
  backendConnected: boolean;
  connection?: TelemetryConnection | null;
  onSettings: () => void;
}

export function Header({ globalState, currentTime, backendConnected, connection, onSettings }: HeaderProps) {
  return (
    <header className="kiosk-header sticky top-0 z-30 flex min-h-[72px] items-center gap-4 border-b border-white/10 bg-graphite-950/95 px-5 backdrop-blur">
      <div className="min-w-0">
        <h1 className="truncate text-2xl font-semibold text-zinc-50">EV Charger HMI</h1>
        <div className="mt-1 flex items-center gap-3 text-sm text-zinc-400">
          <span className="capitalize">{globalState}</span>
          <span>{currentTime.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })}</span>
        </div>
      </div>
      <div className="ml-auto hidden lg:block">
        <ConnectionIndicator backendConnected={backendConnected} connection={connection} />
      </div>
      <button
        className="grid h-12 w-12 place-items-center rounded-md border border-white/10 bg-graphite-850 text-zinc-100"
        title="Settings"
        onClick={onSettings}
      >
        <Settings size={22} />
      </button>
    </header>
  );
}
