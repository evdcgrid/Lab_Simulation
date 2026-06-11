from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from app.models.commands import ChargerCommand


router = APIRouter(prefix="/chargers", tags=["commands"])


@router.post("/{charger_id}/command")
async def send_charger_command(charger_id: str, command: ChargerCommand, request: Request):
    publisher = request.app.state.command_publisher
    store = request.app.state.store
    hub = request.app.state.hub

    result = await publisher.publish(charger_id, command)
    if not result.accepted:
        event = await store.add_command_event(charger_id, result.message, severity="warning")
        await hub.broadcast({"type": "event", "data": event, "summary": await store.summary()})
        raise HTTPException(status_code=502, detail=result.message)

    event = await store.add_command_event(charger_id, f"{charger_id} command: {command.command.value}")
    await hub.broadcast({"type": "event", "data": event, "summary": await store.summary()})
    return result
