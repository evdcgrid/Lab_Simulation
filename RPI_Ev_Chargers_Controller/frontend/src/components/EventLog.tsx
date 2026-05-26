import { AlertTriangle, Info, Trash2, Zap } from "lucide-react";
import type { ChargerEvent } from "../types/telemetry";

function iconFor(severity: string) {
  if (severity === "fault" || severity === "error") return <AlertTriangle size={18} />;
  if (severity === "warning") return <Zap size={18} />;
  return <Info size={18} />;
}

function toneFor(severity: string) {
  if (severity === "fault" || severity === "error") return "text-signal-red";
  if (severity === "warning") return "text-signal-amber";
  return "text-signal-cyan";
}

export function EventLog({ events, onClear }: { events: ChargerEvent[]; onClear: () => void }) {
  return (
    <section className="event-log rounded-lg border border-white/10 bg-graphite-850 p-4 shadow-panel">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-zinc-50">Events</h2>
        <div className="flex items-center gap-2">
          <span className="text-sm text-zinc-500">{events.length}</span>
          <button
            className="grid h-10 w-10 place-items-center rounded-md border border-white/10 bg-graphite-800 text-zinc-200 disabled:opacity-40"
            title="Clear events"
            disabled={events.length === 0}
            onClick={onClear}
          >
            <Trash2 size={18} />
          </button>
        </div>
      </div>
      <div className="event-list space-y-2 overflow-hidden pr-1">
        {events.length === 0 ? (
          <div className="rounded-md border border-white/10 bg-graphite-900 px-3 py-4 text-sm text-zinc-400">
            No events
          </div>
        ) : (
          events.slice(0, 5).map((event) => (
            <div key={event.id} className="event-item rounded-md border border-white/10 bg-graphite-900 p-3">
              <div className={`flex items-center gap-2 text-sm font-semibold ${toneFor(event.severity)}`}>
                {iconFor(event.severity)}
                <span>{event.charger_id ?? "System"}</span>
                <span className="ml-auto text-xs text-zinc-500">
                  {new Date(event.timestamp).toLocaleTimeString([], {
                    hour: "2-digit",
                    minute: "2-digit",
                    second: "2-digit"
                  })}
                </span>
              </div>
              <div className="mt-2 text-sm text-zinc-300">{event.message}</div>
            </div>
          ))
        )}
      </div>
    </section>
  );
}
