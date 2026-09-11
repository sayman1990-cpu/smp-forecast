"""DuckDB 연결 + 스키마 초기화 (5절: DuckDB + Parquet, PK UPSERT로 멱등성 확보)."""

from __future__ import annotations

import os
from pathlib import Path

import duckdb

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "warehouse.duckdb"


def get_connection(db_path: Path | None = None) -> duckdb.DuckDBPyConnection:
    path = db_path or Path(os.environ.get("DUCKDB_PATH", DEFAULT_DB_PATH))
    path.parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(path))


def init_schema(conn: duckdb.DuckDBPyConnection) -> None:
    sql = SCHEMA_PATH.read_text(encoding="utf-8")
    conn.execute(sql)


def upsert(conn: duckdb.DuckDBPyConnection, table: str, df, pk_cols: list[str]) -> None:
    """DataFrame df를 table에 PK 기준 UPSERT. 재실행해도 중복 없음 (5절 멱등성)."""
    conn.register("_incoming", df)
    cols = ", ".join(df.columns)
    set_clause = ", ".join(f"{c}=excluded.{c}" for c in df.columns if c not in pk_cols)
    conflict_cols = ", ".join(pk_cols)
    conn.execute(
        f"""
        INSERT INTO {table} ({cols})
        SELECT {cols} FROM _incoming
        ON CONFLICT ({conflict_cols}) DO UPDATE SET {set_clause}
        """
    )
    conn.unregister("_incoming")


if __name__ == "__main__":
    conn = get_connection()
    init_schema(conn)
    print(f"스키마 초기화 완료: {DEFAULT_DB_PATH}")
