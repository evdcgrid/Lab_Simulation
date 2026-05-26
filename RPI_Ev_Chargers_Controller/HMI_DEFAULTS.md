# HMI Defaults

This project has four places where defaults live. Use this as the map.

## 1. Service/process defaults

File: `hmi.env`

Controls what the systemd service starts:

- `HMI_NODES`: CAN nodes opened by `run_zmq_server.py`, for example `N01` or `N01,N02`.
- `HMI_STARTUP_SEQUENCE`: `1` sends heartbeat/sync/RPDO startup messages.
- `HMI_COMMAND_SERVER`: `1` enables HMI setpoint commands on ZMQ port `3334`.
- `HMI_BACKEND_PORT`: FastAPI backend port, default `8000`.
- `HMI_FRONTEND_MODE`: `static` by default. FastAPI serves `frontend/dist` on the backend port.
- `HMI_FRONTEND_PORT`: Vite frontend port, default `5173`, used only with `HMI_FRONTEND_MODE=dev` or `preview`.
- `HMI_KIOSK_URL`: URL opened by Firefox in fullscreen, default `http://127.0.0.1:8000`.
- `HMI_KIOSK_BROWSER`: browser binary, default `/usr/bin/firefox`.
- `HMI_KIOSK_WAIT_SECONDS`: how long Firefox waits for the frontend before opening.
- `HMI_KIOSK_DISPLAY`: X display used when launching from SSH/systemd-like shells, default `:0`.

Keep `HMI_NODES` aligned with `backend/.env` `CHARGER_IDS`.

## 2. Backend/HMI defaults

File: `backend/.env`

Controls what the HMI backend sees and allows:

- `TELEMETRY_SOURCE=zmq`: backend subscribes to real ZMQ telemetry.
- `ZMQ_ENDPOINT=tcp://127.0.0.1:3333`: telemetry from `run_zmq_server.py`.
- `COMMAND_PUBLISHER=zmq`: backend sends commands/setpoints by ZMQ.
- `ZMQ_COMMAND_ENDPOINT=tcp://127.0.0.1:3334`: command channel.
- `CHARGER_IDS=N01`: chargers shown/accepted by the HMI. Add `N02` only if it is physically present.
- `CHARGER_MAX_POWER_KW`: default max power if a charger has no specific limit.
- `CHARGER_POWER_LIMITS=N01=11.04, N02=11.04`: max power per charger.
- `PARAMETER_CONFIG_PATH=../config/charger_parameter_limits.json`: simple per-node defaults/min/max/step for the Parameters tab.
- `STALE_TIMEOUT_SECONDS` and `OFFLINE_TIMEOUT_SECONDS`: when UI marks a charger stale/offline.
- `SQLITE_PATH=data/hmi.sqlite3`: history database path, relative to the `backend/` folder.

Fallback defaults are in `backend/app/config.py`, but in normal use edit `backend/.env` and `config/charger_parameter_limits.json`.

## 2.1. Parameter defaults and min/max per node

File: `config/charger_parameter_limits.json`

This is the simplest place to define the default value, slider minimum, slider maximum and slider step per converter.

Example:

```json
{
  "defaults": {
    "requested_power_kw": {
      "default": 3.3,
      "min": 0.0,
      "max": 11.04,
      "step": 0.1
    },
    "target_voltage_v": {
      "default": 400.0,
      "min": 250.0,
      "max": 500.0,
      "step": 1.0
    }
  },
  "chargers": {
    "N01": {
      "requested_power_kw": {
        "default": 3.3,
        "max": 11.04
      }
    },
    "N02": {
      "requested_power_kw": {
        "default": 2.0,
        "max": 6.6
      }
    }
  }
}
```

Supported keys:

- `requested_power_kw`
- `target_voltage_v`
- `charge_current_limit_a`
- `discharge_current_limit_a`
- `voltage_min_v`
- `voltage_max_v`

The backend is the authority: if the frontend sends a value outside these limits, the backend rejects it.

## 3. CAN/ZMQ low-level defaults

File: `config/constants.py`

Controls the CAN/ZMQ plumbing:

- `PUB_BIND=tcp://*:3333`: telemetry publisher bind address.
- `SUB_CONNECT=tcp://127.0.0.1:3333`: local subscriber address.
- `COMMAND_BIND=tcp://*:3334`: command server bind address.
- `DBC_FILE_1`, `DBC_FILE_2`, etc.: DBC files per node.
- `NODES`: maps `N01`, `N02`, etc. to DBC files and node IDs.

## 4. CAN command/default signal values

File: `config/signals_config.py`

Controls what is sent to the charger on startup and when applying setpoints:

- `RPDO0`: state/mode/config/output voltage templates.
- `RPDO1`: current limits, active power setpoint and reactive power setpoint.
- `RPDO2`: L1/L2/L3 current limits.
- `HB_boot` and `HB_on`: heartbeat values.

For the power setpoint flow, the HMI writes these RPDO1 signals:

- `Nxx_itfc_active_power_setpoint_W`
- `Nxx_itfc_i_charge_limit`
- `Nxx_itfc_i_discharge_limit`
- `Nxx_itfc_reactive_power_setpoint_VAR`

## Typical N01-only setup

Use these together:

`hmi.env`

```env
HMI_NODES=N01
```

`backend/.env`

```env
CHARGER_IDS=N01
CHARGER_POWER_LIMITS=N01=11.04
```

If you later connect `N02`, change both files:

`hmi.env`

```env
HMI_NODES=N01,N02
```

`backend/.env`

```env
CHARGER_IDS=N01,N02
CHARGER_POWER_LIMITS=N01=11.04,N02=11.04
```

## Install service

From the project root:

```bash
scripts/install_hmi_stack.sh
```

Or manually:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-hmi.txt
cd frontend
npm install
npm run build
cd ..
sudo cp systemd/ev-hmi-stack.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable ev-hmi-stack.service
sudo systemctl start ev-hmi-stack.service
```

Logs:

```bash
journalctl -u ev-hmi-stack.service -f
```

Stop:

```bash
sudo systemctl stop ev-hmi-stack.service
```

## Firefox fullscreen/kiosk

The desktop autostart opens:

```bash
scripts/start_hmi_firefox.sh
```

It waits for `HMI_KIOSK_URL` and then runs:

```bash
firefox --kiosk http://127.0.0.1:8000
```

The autostart file is installed at:

```text
~/.config/autostart/ev-hmi-kiosk.desktop
```

On this Raspberry Pi image there is also an LXSession autostart file:

```text
~/.config/lxsession/rpd-x/autostart
```

If Firefox does not open after a reboot, make sure the Pi is configured to boot into desktop with auto-login:

```bash
sudo raspi-config
```

Choose `System Options` -> `Boot / Auto Login` -> `Desktop Autologin`.
