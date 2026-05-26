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

BACKEND_PORT="${HMI_BACKEND_PORT:-8000}"
FRONTEND_MODE="${HMI_FRONTEND_MODE:-static}"
FRONTEND_PORT="${HMI_FRONTEND_PORT:-5173}"
if [[ -n "${HMI_KIOSK_URL:-}" ]]; then
  URL="$HMI_KIOSK_URL"
elif [[ "$FRONTEND_MODE" == "static" ]]; then
  URL="http://127.0.0.1:${BACKEND_PORT}"
else
  URL="http://127.0.0.1:${FRONTEND_PORT}"
fi
BROWSER="${HMI_KIOSK_BROWSER:-/usr/bin/firefox}"
PROFILE_DIR="${HMI_KIOSK_PROFILE:-/home/pi/.mozilla/hmi-kiosk}"
WAIT_SECONDS="${HMI_KIOSK_WAIT_SECONDS:-120}"
LOCK_FILE="${XDG_RUNTIME_DIR:-/tmp}/ev-hmi-kiosk.lock"

if [[ -z "${XDG_RUNTIME_DIR:-}" && -d "/run/user/$(id -u)" ]]; then
  export XDG_RUNTIME_DIR="/run/user/$(id -u)"
  LOCK_FILE="$XDG_RUNTIME_DIR/ev-hmi-kiosk.lock"
fi

if [[ -z "${DISPLAY:-}" && -S /tmp/.X11-unix/X0 ]]; then
  export DISPLAY="${HMI_KIOSK_DISPLAY:-:0}"
fi

if [[ -z "${XAUTHORITY:-}" && -f "$HOME/.Xauthority" ]]; then
  export XAUTHORITY="$HOME/.Xauthority"
fi

if [[ -z "${DISPLAY:-}" && -z "${WAYLAND_DISPLAY:-}" ]]; then
  echo "No graphical display found. Start the Raspberry Pi desktop first, or run with DISPLAY=:0." >&2
  exit 1
fi

exec 9>"$LOCK_FILE"
if ! flock -n 9; then
  exit 0
fi

if [[ ! -x "$BROWSER" ]]; then
  BROWSER="$(command -v firefox || command -v firefox-esr || true)"
fi

if [[ -z "$BROWSER" || ! -x "$BROWSER" ]]; then
  echo "Firefox not found. Set HMI_KIOSK_BROWSER in hmi.env." >&2
  exit 1
fi

mkdir -p "$PROFILE_DIR"
cat > "$PROFILE_DIR/user.js" <<'EOF'
user_pref("browser.shell.checkDefaultBrowser", false);
user_pref("browser.startup.homepage_override.mstone", "ignore");
user_pref("browser.sessionstore.resume_from_crash", false);
user_pref("browser.tabs.warnOnClose", false);
user_pref("toolkit.telemetry.reportingpolicy.firstRun", false);

user_pref("browser.display.background_color", "#000000");
user_pref("browser.display.foreground_color", "#ffffff");
user_pref("browser.theme.content-theme", 0);
user_pref("browser.theme.toolbar-theme", 0);
user_pref("ui.systemUsesDarkTheme", 1);
EOF

deadline=$((SECONDS + WAIT_SECONDS))
while (( SECONDS < deadline )); do
  if curl -fsS --max-time 2 "$URL" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

if command -v unclutter >/dev/null 2>&1; then
  pkill unclutter 2>/dev/null || true
  DISPLAY="${DISPLAY:-:0}" unclutter -idle 0 -root &
fi

exec "$BROWSER" --new-instance --profile "$PROFILE_DIR" --kiosk "$URL"
