import type { ChargerParameters } from "./parameters";

export type ChargerState =
  | "offline"
  | "idle"
  | "init"
  | "standby"
  | "power_on"
  | "charging"
  | "safe_d"
  | "stopping"
  | "lock_dsp"
  | "fault_ack"
  | "warning"
  | "fault"
  | "stale";

export interface ChargerTelemetry {
  charger_id: string;
  timestamp: string;
  state: ChargerState;
  vin?: number | null;
  iin?: number | null;
  pin?: number | null;
  vout?: number | null;
  iout?: number | null;
  pout?: number | null;
  efficiency?: number | null;
  energy_session_kwh?: number | null;
  fault_code?: string | null;
  warning_code?: string | null;
  raw?: Record<string, unknown>;
}

export interface ChargerStatus {
  charger_id: string;
  state: ChargerState;
  telemetry?: ChargerTelemetry | null;
  stale: boolean;
  offline: boolean;
  last_update?: string | null;
  seconds_since_last_message?: number | null;
  fault_code?: string | null;
  warning_code?: string | null;
  updated_at: string;
}

export interface HistoryPoint {
  charger_id: string;
  timestamp: string;
  state?: ChargerState;
  vin?: number | null;
  iin?: number | null;
  pin?: number | null;
  vout?: number | null;
  iout?: number | null;
  pout?: number | null;
  efficiency?: number | null;
  energy_session_kwh?: number | null;
}

export interface ChargerEvent {
  id: string;
  timestamp: string;
  charger_id?: string | null;
  severity: "info" | "warning" | "fault" | "error" | string;
  kind: string;
  message: string;
}

export interface TelemetrySummary {
  total_power_kw: number;
  total_energy_kwh: number;
  active_chargers: number;
  active_alarms: number;
  charger_count: number;
}

export interface TelemetryConnection {
  source: string;
  endpoint?: string | null;
  connected: boolean;
  active: boolean;
  last_message_at?: string | null;
  message_count: number;
  invalid_message_count: number;
  last_error?: string | null;
}

export interface TelemetrySnapshot {
  chargers: ChargerStatus[];
  parameters: ChargerParameters[];
  live_points: Record<string, HistoryPoint[]>;
  events: ChargerEvent[];
  summary: TelemetrySummary;
  connection: TelemetryConnection;
}

export interface ChargersResponse {
  chargers: ChargerStatus[];
  parameters: ChargerParameters[];
  summary: TelemetrySummary;
  connection: TelemetryConnection;
}

export interface WsTelemetryMessage {
  type: "snapshot" | "telemetry" | "status" | "event" | "events" | "parameters" | "connection" | "pong";
  data?: unknown;
  point?: HistoryPoint;
  event?: ChargerEvent | null;
  events?: ChargerEvent[];
  summary?: TelemetrySummary;
  connection?: TelemetryConnection;
}
