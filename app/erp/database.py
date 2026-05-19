import sqlite3
from pathlib import Path


DEFAULT_SEED_PATH = Path("data/northwind_seed.sql")


def create_sqlite_connection(database_path: str = ":memory:") -> sqlite3.Connection:
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def load_seed_sql(
    connection: sqlite3.Connection,
    seed_path: Path = DEFAULT_SEED_PATH,
) -> None:
    sql = seed_path.read_text(encoding="utf-8")
    connection.executescript(sql)
    connection.commit()
