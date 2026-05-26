from __future__ import annotations

from fastapi import APIRouter, Request


router = APIRouter(prefix="/events", tags=["events"])


@router.delete("")
async def clear_events(request: Request) -> dict:
    store = request.app.state.store

    await store.clear_events()
    return {"events": []}
