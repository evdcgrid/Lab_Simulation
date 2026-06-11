from __future__ import annotations

from fastapi import APIRouter, Request


router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("")
async def get_settings(request: Request) -> dict:
    settings = request.app.state.settings
    return {
        "app_name": settings.app_name,
        "telemetry_source": settings.telemetry_source,
        "zmq_endpoint": settings.zmq_endpoint,
        "zmq_topic": settings.zmq_topic,
        "telemetry_rate_limit_ms": settings.telemetry_rate_limit_ms,
        "history_sample_period_ms": settings.history_sample_period_ms,
        "stale_timeout_seconds": settings.stale_timeout_seconds,
        "offline_timeout_seconds": settings.offline_timeout_seconds,
        "charger_ids": settings.charger_ids,
        "allow_unknown_chargers": settings.allow_unknown_chargers,
        "charger_max_power_kw": settings.charger_max_power_kw,
        "charger_power_limits": settings.charger_power_limits,
        "command_publisher": settings.command_publisher,
        "zmq_command_endpoint": settings.zmq_command_endpoint,
        "command_timeout_ms": settings.command_timeout_ms,
    }
