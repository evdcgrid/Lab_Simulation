from __future__ import annotations

from app.models.commands import ChargerCommand, ChargerCommandResult


class CommandPublisher:
    async def publish(self, charger_id: str, command: ChargerCommand) -> ChargerCommandResult:
        raise NotImplementedError

    async def close(self) -> None:
        return None
