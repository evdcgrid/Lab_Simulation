import type { ChargerCommandType } from "./commands";
import type { ChargerParameters, ChargerParametersUpdate } from "../types/parameters";
import type { ChargersResponse, HistoryPoint } from "../types/telemetry";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "/api";

async function fetchJson<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options?.headers ?? {})
    },
    ...options
  });

  if (!response.ok) {
    let message = `${response.status} ${response.statusText}`;
    try {
      const body = await response.json();
      message = body.detail ?? message;
    } catch {
      // Keep HTTP status text.
    }
    throw new Error(message);
  }

  return response.json() as Promise<T>;
}

export function getChargers() {
  return fetchJson<ChargersResponse>("/chargers");
}

export function getParameters(chargerId: string) {
  return fetchJson<ChargerParameters>(`/chargers/${encodeURIComponent(chargerId)}/parameters`);
}

export function updateParameters(chargerId: string, update: ChargerParametersUpdate) {
  return fetchJson<{ parameters: ChargerParameters }>(`/chargers/${encodeURIComponent(chargerId)}/parameters`, {
    method: "POST",
    body: JSON.stringify(update)
  });
}

export function sendCommand(chargerId: string, command: ChargerCommandType) {
  return fetchJson(`/chargers/${encodeURIComponent(chargerId)}/command`, {
    method: "POST",
    body: JSON.stringify({ command })
  });
}

export function getHistory(params: {
  chargerId?: string;
  from?: string;
  to?: string;
  signals?: string[];
  limit?: number;
  signal?: AbortSignal;
}) {
  const search = new URLSearchParams();
  if (params.chargerId) search.set("charger_id", params.chargerId);
  if (params.from) search.set("from", params.from);
  if (params.to) search.set("to", params.to);
  if (params.signals?.length) search.set("signals", params.signals.join(","));
  if (params.limit) search.set("limit", String(params.limit));
  return fetchJson<{ samples: HistoryPoint[] }>(`/history?${search.toString()}`, { signal: params.signal });
}

export function getBackendSettings() {
  return fetchJson<Record<string, unknown>>("/settings");
}

export function clearEvents() {
  return fetchJson<{ events: [] }>("/events", { method: "DELETE" });
}
