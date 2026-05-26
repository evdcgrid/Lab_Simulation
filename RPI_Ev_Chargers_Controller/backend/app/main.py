from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.api import chargers, commands, events, history, settings as settings_api
from app.commands.mock_publisher import MockCommandPublisher
from app.commands.zmq_publisher import ZmqCommandPublisher
from app.config import get_settings
from app.db.history_repository import HistoryRepository
from app.telemetry.mock_source import MockTelemetrySource
from app.telemetry.store import TelemetryStore
from app.telemetry.zmq_subscriber import ZmqSubscriber
from app.websocket.telemetry_ws import TelemetryHub, router as telemetry_ws_router


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
LOGGER = logging.getLogger(__name__)


settings = get_settings()
FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    store = TelemetryStore(settings)
    await store.bootstrap()

    history_repository = HistoryRepository(settings.sqlite_path)
    await history_repository.initialize()

    hub = TelemetryHub()
    if settings.command_publisher == "zmq":
        command_publisher = ZmqCommandPublisher(settings.zmq_command_endpoint, settings.command_timeout_ms)
    else:
        command_publisher = MockCommandPublisher()

    app.state.settings = settings
    app.state.store = store
    app.state.history_repository = history_repository
    app.state.hub = hub
    app.state.command_publisher = command_publisher

    async def handle_telemetry(telemetry):
        update = await store.ingest(telemetry)
        if update is None:
            return
        if update["history_sample"] is not None:
            await history_repository.insert_sample(update["history_sample"])
        await hub.broadcast(
            {
                "type": "telemetry",
                "data": update["status"],
                "point": update["point"],
                "event": update["event"],
                "summary": update["summary"],
                "connection": update["connection"],
            }
        )

    async def handle_source_status(connected: bool, error: str | None) -> None:
        await store.set_source_status(connected, error)
        await hub.broadcast(
            {
                "type": "connection",
                "data": (await store.snapshot())["connection"],
                "summary": await store.summary(),
            }
        )

    async def handle_invalid_message(_connected: bool, error: str | None) -> None:
        event = await store.record_invalid_message(error or "unknown parser error")
        await hub.broadcast(
            {
                "type": "event",
                "data": event,
                "summary": await store.summary(),
                "connection": (await store.snapshot())["connection"],
            }
        )

    sources = []
    source_mode = settings.telemetry_source
    if source_mode in {"mock", "both"}:
        sources.append(MockTelemetrySource(settings, handle_telemetry))
    if source_mode in {"zmq", "both"}:
        sources.append(
            ZmqSubscriber(
                settings,
                handle_telemetry,
                handle_source_status,
                handle_invalid_message,
            )
        )

    if not sources and source_mode != "none":
        LOGGER.warning("Unknown TELEMETRY_SOURCE=%s; falling back to mock", source_mode)
        sources.append(MockTelemetrySource(settings, handle_telemetry))

    async def timeout_monitor() -> None:
        while True:
            for change in await store.check_timeouts():
                await hub.broadcast(
                    {
                        "type": "status",
                        "data": change["status"],
                        "event": change["event"],
                        "summary": change["summary"],
                        "connection": change["connection"],
                    }
                )
            await asyncio.sleep(1.0)

    tasks = [asyncio.create_task(source.run()) for source in sources]
    tasks.append(asyncio.create_task(timeout_monitor()))
    LOGGER.info("EV Charger HMI backend started with telemetry_source=%s", source_mode)

    try:
        yield
    finally:
        for source in sources:
            await source.stop()
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        await command_publisher.close()
        await history_repository.close()
        LOGGER.info("EV Charger HMI backend stopped")


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chargers.router, prefix=settings.api_prefix)
app.include_router(commands.router, prefix=settings.api_prefix)
app.include_router(events.router, prefix=settings.api_prefix)
app.include_router(history.router, prefix=settings.api_prefix)
app.include_router(settings_api.router, prefix=settings.api_prefix)
app.include_router(telemetry_ws_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/{full_path:path}", include_in_schema=False)
async def serve_frontend(full_path: str):
    api_path = settings.api_prefix.strip("/")
    if full_path == api_path or full_path.startswith((f"{api_path}/", "ws/")):
        raise HTTPException(status_code=404, detail="Not found")

    index_path = FRONTEND_DIST / "index.html"
    if not index_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Frontend build not found. Run `npm run build` in frontend/.",
        )

    requested_path = (FRONTEND_DIST / full_path).resolve()
    try:
        requested_path.relative_to(FRONTEND_DIST.resolve())
    except ValueError:
        raise HTTPException(status_code=404, detail="Not found") from None

    if full_path and requested_path.is_file():
        return FileResponse(requested_path)

    return FileResponse(
        index_path,
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
        },
    )
