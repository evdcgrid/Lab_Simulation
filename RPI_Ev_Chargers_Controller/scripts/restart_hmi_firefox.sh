#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="${HMI_ROOT:-/home/pi/Documents/Lab_Simulation/RPI_Ev_Chargers_Controller}"
LOG_FILE="${HMI_KIOSK_LOG:-/tmp/ev-hmi-kiosk.log}"

"$ROOT/scripts/stop_hmi_firefox.sh" || true

nohup "$ROOT/scripts/start_hmi_firefox.sh" >>"$LOG_FILE" 2>&1 &
echo "HMI Firefox kiosk start requested; logs: $LOG_FILE"
