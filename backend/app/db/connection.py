from __future__ import annotations

import atexit

import psycopg
from psycopg_pool import ConnectionPool

from app.config import settings

_pool: ConnectionPool | None = None


def _conninfo() -> str:
    return (
        f"host={settings.postgres_host} port={settings.postgres_port} "
        f"dbname={settings.postgres_db} user={settings.postgres_user} "
        f"password={settings.postgres_password} "
        f"options='-c search_path={settings.postgres_schema}'"
    )


def get_pool() -> ConnectionPool:
    global _pool
    if _pool is None:
        _pool = ConnectionPool(conninfo=_conninfo(), min_size=1, max_size=4)
        atexit.register(_pool.close)
    return _pool


def get_connection() -> psycopg.Connection:
    """Conexión con autocommit desactivado (default de psycopg): el llamador controla
    el commit/rollback para poder tratar cada solicitud como una transacción atómica."""
    return get_pool().getconn()


def release_connection(conn: psycopg.Connection) -> None:
    """Devuelve la conexión al pool. A diferencia de oracledb, psycopg_pool no libera la
    conexión con conn.close() (eso la descarta del pool): hay que usar pool.putconn()."""
    get_pool().putconn(conn)
