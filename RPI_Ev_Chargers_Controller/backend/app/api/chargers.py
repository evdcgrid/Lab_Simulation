from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from app.models.commands import ChargerCommand, ChargerCommandType
from app.models.parameters import ChargerParametersUpdate
from app.telemetry.store import ParameterValidationError


router = APIRouter(prefix="/chargers", tags=["chargers"])


@router.get("")
async def list_chargers(request: Request) -> dict:
    store = request.app.state.store
    snapshot = await store.snapshot()
    return {
        "chargers": snapshot["chargers"],
        "parameters": snapshot["parameters"],
        "summary": snapshot["summary"],
        "connection": snapshot["connection"],
    }


@router.get("/{charger_id}")
async def get_charger(charger_id: str, request: Request):
    store = request.app.state.store
    status = await store.get_status(charger_id)
    if status is None:
        raise HTTPException(status_code=404, detail=f"Unknown charger '{charger_id}'")
    return status


@router.get("/{charger_id}/parameters")
async def get_charger_parameters(charger_id: str, request: Request):
    store = request.app.state.store
    return await store.get_parameters(charger_id)


@router.post("/{charger_id}/parameters")
async def update_charger_parameters(
    charger_id: str,
    update: ChargerParametersUpdate,
    request: Request,
):
    store = request.app.state.store
    hub = request.app.state.hub
    publisher = request.app.state.command_publisher

    try:
        parameters = await store.prepare_parameter_update(charger_id, update)
    except ParameterValidationError as exc:
        events = await store.events()
        if events:
            await hub.broadcast({"type": "event", "data": events[0], "summary": await store.summary()})
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    command = ChargerCommand(
        command=ChargerCommandType.APPLY_PARAMETERS,
        payload=parameters.model_dump(mode="json"),
    )
    result = await publisher.publish(charger_id, command)
    if not result.accepted:
        event = await store.add_command_event(charger_id, result.message, severity="warning")
        await hub.broadcast({"type": "event", "data": event, "summary": await store.summary()})
        raise HTTPException(status_code=502, detail=result.message)

    parameters = await store.apply_parameters(parameters)
    await hub.broadcast(
        {
            "type": "parameters",
            "data": parameters,
            "result": result,
            "events": await store.events(),
            "summary": await store.summary(),
        }
    )
    return {"parameters": parameters, "command": result}
