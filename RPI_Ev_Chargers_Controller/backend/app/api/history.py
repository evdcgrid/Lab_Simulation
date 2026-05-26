from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Query, Request


router = APIRouter(prefix="/history", tags=["history"])


@router.get("")
async def get_history(
    request: Request,
    charger_id: str | None = None,
    from_ts: datetime | None = Query(default=None, alias="from"),
    to_ts: datetime | None = Query(default=None, alias="to"),
    signals: str | None = None,
    limit: int = Query(default=2500, ge=1, le=20000),
) -> dict:
    repository = request.app.state.history_repository
    signal_list = [item.strip() for item in signals.split(",")] if signals else None
    samples = await repository.query(
        charger_id=charger_id,
        from_ts=from_ts,
        to_ts=to_ts,
        signals=signal_list,
        limit=limit,
    )
    return {"samples": samples}

