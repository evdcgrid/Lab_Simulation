#!/usr/bin/env python3
from __future__ import annotations

import sys
import os
import tempfile
import asyncio
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("TELEMETRY_SOURCE", "none")
os.environ.setdefault("SQLITE_PATH", tempfile.mktemp(prefix="hmi-smoke-", suffix=".sqlite3"))
os.environ["CHARGER_IDS"] = "charger_1,charger_2"
os.environ["CHARGER_MAX_POWER_KW"] = "6.6"
os.environ["CHARGER_POWER_LIMITS"] = "charger_1=6.6,charger_2=6.6"
parameter_config = tempfile.NamedTemporaryFile("w", delete=False, suffix=".json")
parameter_config.write(
    """
{
  "defaults": {
    "requested_power_kw": {"default": 3.3, "min": 0.0, "max": 6.6, "step": 0.1},
    "target_voltage_v": {"default": 400.0, "min": 250.0, "max": 500.0, "step": 1.0},
    "charge_current_limit_a": {"default": 16.0, "min": 0.0, "max": 300.0, "step": 0.5},
    "discharge_current_limit_a": {"default": 16.0, "min": 0.0, "max": 300.0, "step": 0.5},
    "voltage_min_v": {"default": 250.0, "min": 0.0, "max": 499.0, "step": 1.0},
    "voltage_max_v": {"default": 450.0, "min": 251.0, "max": 1000.0, "step": 1.0}
  }
}
"""
)
parameter_config.close()
os.environ["PARAMETER_CONFIG_PATH"] = parameter_config.name
os.environ["COMMAND_PUBLISHER"] = "mock"

from app.main import app


async def run() -> None:
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            health = await client.get("/health")
            health.raise_for_status()

            chargers = await client.get("/api/chargers")
            chargers.raise_for_status()

            params = await client.get("/api/chargers/charger_1/parameters")
            params.raise_for_status()

            invalid_power = await client.post(
                "/api/chargers/charger_1/parameters",
                json={"requested_power_kw": 8.0},
            )
            assert invalid_power.status_code == 400, invalid_power.text

            valid_power = await client.post(
                "/api/chargers/charger_1/parameters",
                json={
                    "requested_power_kw": 3.5,
                    "charge_current_limit_a": 12.0,
                    "discharge_current_limit_a": 7.5,
                },
            )
            valid_power.raise_for_status()
            parameters = valid_power.json()["parameters"]
            assert parameters["active_power_setpoint_W"] == 3500.0, parameters
            assert parameters["charge_current_setpoint_a"] == 8.75, parameters
            assert parameters["charge_current_limit_a"] == 12.0, parameters
            assert parameters["discharge_current_limit_a"] == 7.5, parameters

            print("health", health.json())
            print("chargers", len(chargers.json()["chargers"]))
            print("invalid_power", invalid_power.status_code, invalid_power.json()["detail"])
            print("active_power_setpoint_W", parameters["active_power_setpoint_W"])
            print("charge_current_setpoint_a", parameters["charge_current_setpoint_a"])
            print("charge_current_limit_a", parameters["charge_current_limit_a"])
            print("discharge_current_limit_a", parameters["discharge_current_limit_a"])


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
