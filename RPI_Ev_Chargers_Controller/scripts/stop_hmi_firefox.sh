#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="${HMI_ROOT:-/home/pi/Documents/Lab_Simulation/RPI_Ev_Chargers_Controller}"
ENV_FILE="$ROOT/hmi.env"

if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck source=/dev/null
  source "$ENV_FILE"
  set +a
fi

PROFILE_DIR="${HMI_KIOSK_PROFILE:-/home/pi/.mozilla/hmi-kiosk}"
MATCHED_PIDS=()

for cmdline in /proc/[0-9]*/cmdline; do
  [[ -r "$cmdline" ]] || continue
  pid="${cmdline%/cmdline}"
  pid="${pid##*/}"
  [[ "$pid" == "$$" ]] && continue

  args="$(tr '\0' '\n' < "$cmdline" || true)"
  if grep -Fxq -- "$PROFILE_DIR" <<<"$args" && grep -Eq '(^|/)(firefox|firefox-esr)$' <<<"$args"; then
    MATCHED_PIDS+=("$pid")
  fi
done

if ((${#MATCHED_PIDS[@]} == 0)); then
  exit 0
fi

echo "Stopping HMI Firefox kiosk: ${MATCHED_PIDS[*]}"
for pid in "${MATCHED_PIDS[@]}"; do
  kill -TERM "$pid" 2>/dev/null || true
done

deadline=$((SECONDS + 5))
while ((SECONDS < deadline)); do
  still_running=0
  for pid in "${MATCHED_PIDS[@]}"; do
    if kill -0 "$pid" 2>/dev/null; then
      still_running=1
      break
    fi
  done
  ((still_running)) || exit 0
  sleep 0.2
done

for pid in "${MATCHED_PIDS[@]}"; do
  kill -KILL "$pid" 2>/dev/null || true
done
