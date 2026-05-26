#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="${HMI_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
SERVICE_NAME="ev-hmi-stack.service"

cd "$ROOT"

echo "Installing Python dependencies in $ROOT/.venv"
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements-hmi.txt

echo "Installing frontend dependencies"
cd "$ROOT/frontend"
npm install
npm run build

echo "Ensuring HMI scripts are executable"
chmod +x \
  "$ROOT/scripts/run_hmi_stack.sh" \
  "$ROOT/scripts/start_hmi_firefox.sh" \
  "$ROOT/scripts/restart_hmi_firefox.sh" \
  "$ROOT/scripts/stop_hmi_firefox.sh"

echo "Installing systemd service"
sudo cp "$ROOT/systemd/$SERVICE_NAME" "/etc/systemd/system/$SERVICE_NAME"
sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE_NAME"

echo "Installing desktop kiosk autostart"
mkdir -p "$HOME/.config/autostart"
cp "$ROOT/desktop/ev-hmi-kiosk.desktop" "$HOME/.config/autostart/ev-hmi-kiosk.desktop"

if [[ -d "$HOME/.config/lxsession/rpd-x" ]]; then
  LX_AUTOSTART="$HOME/.config/lxsession/rpd-x/autostart"
  touch "$LX_AUTOSTART"
  if ! grep -Fq "$ROOT/scripts/start_hmi_firefox.sh" "$LX_AUTOSTART"; then
    printf '\n@%s/scripts/start_hmi_firefox.sh\n' "$ROOT" >> "$LX_AUTOSTART"
  fi
fi

echo "Done."
echo "Start with: sudo systemctl start $SERVICE_NAME"
echo "Logs:       journalctl -u $SERVICE_NAME -f"
