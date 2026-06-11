from __future__ import annotations

import sqlite3
from pathlib import Path


def connect(sqlite_path: Path) -> sqlite3.Connection:
    sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(sqlite_path, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("PRAGMA synchronous=NORMAL")
    return connection

