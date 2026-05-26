from __future__ import annotations

import asyncio
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Iterable

from app.db.database import connect
from app.models.telemetry import ChargerState, HistorySample


class HistoryRepository:
    def __init__(self, sqlite_path: Path) -> None:
        self.sqlite_path = sqlite_path
        self._connection: sqlite3.Connection | None = None
        self._lock = asyncio.Lock()

    async def initialize(self) -> None:
        self._connection = connect(self.sqlite_path)
        self._create_schema()

    async def close(self) -> None:
        if self._connection is not None:
            self._connection.close()

    async def insert_sample(self, sample: HistorySample) -> None:
        async with self._lock:
            self._insert_sample_sync(sample)

    async def query(
        self,
        *,
        charger_id: str | None = None,
        from_ts: datetime | None = None,
        to_ts: datetime | None = None,
        signals: Iterable[str] | None = None,
        limit: int = 2500,
    ) -> list[dict]:
        async with self._lock:
            rows = self._query_sync(charger_id, from_ts, to_ts, limit)

        wanted = set(signals or [])
        samples = [self._row_to_dict(row) for row in rows]
        if not wanted:
            return samples

        base = {"charger_id", "timestamp", "state"}
        allowed = base | wanted
        return [{key: value for key, value in sample.items() if key in allowed} for sample in samples]

    def _create_schema(self) -> None:
        assert self._connection is not None
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS history_samples (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                charger_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                state TEXT NOT NULL,
                vin REAL,
                iin REAL,
                pin REAL,
                vout REAL,
                iout REAL,
                pout REAL,
                efficiency REAL,
                energy_session_kwh REAL
            )
            """
        )
        self._connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_history_charger_time ON history_samples (charger_id, timestamp)"
        )
        self._connection.commit()

    def _insert_sample_sync(self, sample: HistorySample) -> None:
        assert self._connection is not None
        self._connection.execute(
            """
            INSERT INTO history_samples (
                charger_id, timestamp, state, vin, iin, pin, vout, iout, pout,
                efficiency, energy_session_kwh
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                sample.charger_id,
                sample.timestamp.isoformat(),
                sample.state.value if isinstance(sample.state, ChargerState) else str(sample.state),
                sample.vin,
                sample.iin,
                sample.pin,
                sample.vout,
                sample.iout,
                sample.pout,
                sample.efficiency,
                sample.energy_session_kwh,
            ),
        )
        self._connection.commit()

    def _query_sync(
        self,
        charger_id: str | None,
        from_ts: datetime | None,
        to_ts: datetime | None,
        limit: int,
    ) -> list[sqlite3.Row]:
        assert self._connection is not None
        clauses: list[str] = []
        params: list[str | int] = []

        if charger_id:
            clauses.append("charger_id = ?")
            params.append(charger_id)
        if from_ts:
            clauses.append("timestamp >= ?")
            params.append(from_ts.isoformat())
        if to_ts:
            clauses.append("timestamp <= ?")
            params.append(to_ts.isoformat())

        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        params.append(limit)
        cursor = self._connection.execute(
            f"""
            SELECT charger_id, timestamp, state, vin, iin, pin, vout, iout, pout,
                   efficiency, energy_session_kwh
            FROM history_samples
            {where}
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            params,
        )
        rows = list(cursor.fetchall())
        rows.reverse()
        return rows

    def _row_to_dict(self, row: sqlite3.Row) -> dict:
        return {
            "charger_id": row["charger_id"],
            "timestamp": row["timestamp"],
            "state": row["state"],
            "vin": row["vin"],
            "iin": row["iin"],
            "pin": row["pin"],
            "vout": row["vout"],
            "iout": row["iout"],
            "pout": row["pout"],
            "efficiency": row["efficiency"],
            "energy_session_kwh": row["energy_session_kwh"],
        }
