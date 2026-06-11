import { Radio, Server, Wifi, WifiOff } from "lucide-react";
import type { TelemetryConnection } from "../types/telemetry";

interface Props {
  backendConnected: boolean;
  connection?: TelemetryConnection | null;
}

export function ConnectionIndicator({ backendConnected, connection }: Props) {
  const zmqActive = Boolean(connection?.active);
  const zmqConnected = Boolean(connection?.connected);

  return (
    <div className="flex items-center gap-2 text-sm">
      <span
        className={`inline-flex min-h-10 items-center gap-2 rounded-md border px-3 ${
          backendConnected
            ? "border-signal-green/40 bg-signal-green/10 text-signal-green"
            : "border-signal-red/50 bg-signal-red/10 text-signal-red"
        }`}
      >
        {backendConnected ? <Wifi size={18} /> : <WifiOff size={18} />}
        Backend
      </span>
      <span
        className={`inline-flex min-h-10 items-center gap-2 rounded-md border px-3 ${
          zmqActive
            ? "border-signal-green/40 bg-signal-green/10 text-signal-green"
            : zmqConnected
              ? "border-signal-amber/50 bg-signal-amber/10 text-signal-amber"
              : "border-zinc-600 bg-zinc-800 text-zinc-300"
        }`}
      >
        {zmqActive ? <Radio size={18} /> : <Server size={18} />}
        {zmqActive ? "ZMQ active" : "No telemetry source"}
      </span>
    </div>
  );
}
