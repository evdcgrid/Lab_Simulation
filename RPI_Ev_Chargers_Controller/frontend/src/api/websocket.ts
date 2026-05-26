import type { WsTelemetryMessage } from "../types/telemetry";

type MessageHandler = (message: WsTelemetryMessage) => void;
type StatusHandler = (connected: boolean) => void;

function wsUrl() {
  const configured = import.meta.env.VITE_WS_URL;
  if (configured) return configured;

  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${window.location.host}/ws/telemetry`;
}

export function connectTelemetry(onMessage: MessageHandler, onStatus: StatusHandler) {
  let socket: WebSocket | null = null;
  let closedByClient = false;
  let reconnectTimer: number | undefined;

  const connect = () => {
    socket = new WebSocket(wsUrl());

    socket.onopen = () => {
      onStatus(true);
      socket?.send("ping");
    };

    socket.onmessage = (event) => {
      try {
        onMessage(JSON.parse(event.data));
      } catch {
        // Ignore malformed WebSocket frames.
      }
    };

    socket.onclose = () => {
      onStatus(false);
      if (!closedByClient) {
        reconnectTimer = window.setTimeout(connect, 1200);
      }
    };

    socket.onerror = () => {
      onStatus(false);
      socket?.close();
    };
  };

  connect();

  return {
    close() {
      closedByClient = true;
      if (reconnectTimer) window.clearTimeout(reconnectTimer);
      socket?.close();
    }
  };
}

