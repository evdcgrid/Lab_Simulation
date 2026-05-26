from __future__ import annotations

from app.commands.publisher import CommandPublisher
from app.models.commands import ChargerCommand, ChargerCommandResult


class MockCommandPublisher(CommandPublisher):
    """Placeholder command channel.

    TODO: replace with the real command transport (ZMQ PUB/REQ, CAN or HTTP)
    once the charger command path is defined. Telemetry reception must remain
    separate from command transmission.
    """

    def __init__(self) -> None:
        self.commands: list[tuple[str, ChargerCommand]] = []

    async def publish(self, charger_id: str, command: ChargerCommand) -> ChargerCommandResult:
        self.commands.append((charger_id, command))
        return ChargerCommandResult(
            charger_id=charger_id,
            command=command.command,
            accepted=True,
            message=f"Mock command accepted: {command.command.value}",
        )

