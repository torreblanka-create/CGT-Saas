"""
==========================================
TURSO ADAPTER — v2.1 HTTP API (sync real)
==========================================
Adaptador SQLite local + Turso Cloud via HTTP API.

MODOS:
- "local" → SQLite puro (sin red)
- "sync"  → SQLite local + push/pull a Turso vía HTTP requests

Usa la API HTTP de Turso (/v2/pipeline) en lugar de libsql_client
para compatibilidad total con Python 3.11/3.12/3.13 y sin asyncio.
"""

import os
import sqlite3
import json
import logging
from contextlib import contextmanager

import requests

logger = logging.getLogger(__name__)


def _get_turso_credentials():
    """Lee credenciales de env vars o st.secrets."""
    url = os.getenv("LIBSQL_DB_URL", "")
    token = os.getenv("LIBSQL_DB_AUTH_TOKEN", "")
    if not url or not token:
        try:
            import streamlit as st
            url = url or st.secrets.get("LIBSQL_DB_URL", "")
            token = token or st.secrets.get("LIBSQL_DB_AUTH_TOKEN", "")
        except Exception:
            pass
    return url, token


def _turso_http_url(libsql_url: str) -> str:
    """Convierte libsql://... a https://... para la API HTTP."""
    return libsql_url.replace("libsql://", "https://", 1)


def _turso_execute(http_url: str, token: str, statements: list) -> list:
    """
    Ejecuta una lista de statements en Turso vía HTTP pipeline.
    statements: [{"type": "execute", "stmt": {"sql": "...", "args": [...]}}, ...]
    Retorna lista de ResultSets o lanza excepción.
    """
    requests_body = statements + [{"type": "close"}]
    resp = requests.post(
        f"{http_url}/v2/pipeline",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json={"requests": requests_body},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()

    results = []
    for item in data.get("results", []):
        if item.get("type") == "error":
            raise RuntimeError(f"Turso error: {item.get('error', {}).get('message', item)}")
        if item.get("type") == "ok":
            results.append(item.get("response", {}).get("result", {}))
    return results


def turso_pull(local_db_path: str):
    """
    Descarga todas las tablas de Turso Cloud → SQLite local.
    Sobreescribe solo tablas que existen en Turso.
    Solo activo si TURSO_ENV=sync Y hay credenciales.
    """
    url, token = _turso_credentials()
    if not url or not token:
        return

    env = os.getenv("TURSO_ENV", "local")
    if env != "sync":
        return  # No hacer nada si no estamos en sync mode

    # Asegurar que el directorio existe antes de intentar abrir la BD
    ensure_db_dir(local_db_path)

    http_url = _turso_http_url(url)
    try:
        # 1. Obtener lista de tablas en Turso
        results = _turso_execute(http_url, token, [
            {"type": "execute", "stmt": {"sql": "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"}}
        ])
        if not results or not results[0].get("rows"):
            logger.info("Turso: sin tablas en cloud (primera vez)")
            return

        tables = [row[0]["value"] for row in results[0]["rows"]]
        conn = sqlite3.connect(local_db_path, timeout=30)
        conn.row_factory = sqlite3.Row

        for table in tables:
            try:
                # Obtener schema
                schema_r = _turso_execute(http_url, token, [
                    {"type": "execute", "stmt": {"sql": f"SELECT sql FROM sqlite_master WHERE type='table' AND name=?", "args": [{"type": "text", "value": table}]}}
                ])
                if schema_r and schema_r[0].get("rows"):
                    create_sql = schema_r[0]["rows"][0][0]["value"]
                    try:
                        conn.execute(create_sql)
                    except Exception:
                        pass  # tabla ya existe

                # Obtener datos
                data_r = _turso_execute(http_url, token, [
                    {"type": "execute", "stmt": {"sql": f'SELECT * FROM "{table}"'}}
                ])
                if not data_r or not data_r[0].get("cols"):
                    continue

                cols = [c["name"] for c in data_r[0]["cols"]]
                rows = data_r[0].get("rows", [])

                if not rows:
                    continue

                placeholders = ", ".join(["?" for _ in cols])
                col_names = ", ".join(f'"{c}"' for c in cols)
                conn.execute(f'DELETE FROM "{table}"')
                for row in rows:
                    vals = [v.get("value") for v in row]
                    conn.execute(f'INSERT INTO "{table}" ({col_names}) VALUES ({placeholders})', vals)

                conn.commit()
                logger.debug(f"Turso pull: {table} ({len(rows)} filas)")
            except Exception as e:
                logger.debug(f"Turso pull skip {table}: {e}")

        conn.close()
        logger.info("Turso: pull completado")
    except Exception as e:
        logger.warning(f"Turso pull falló: {e}")


def turso_push(local_db_path: str):
    """
    Sube todas las tablas de SQLite local → Turso Cloud.
    Solo activo si TURSO_ENV=sync Y hay credenciales.
    """
    url, token = _turso_credentials()
    if not url or not token:
        return

    env = os.getenv("TURSO_ENV", "local")
    if env != "sync":
        return  # No hacer nada si no estamos en sync mode

    # Asegurar que el directorio existe antes de intentar abrir la BD
    ensure_db_dir(local_db_path)

    http_url = _turso_http_url(url)
    conn = sqlite3.connect(local_db_path, timeout=30)
    conn.row_factory = sqlite3.Row

    try:
        # Desactivar FK para evitar conflictos
        _turso_execute(http_url, token, [
            {"type": "execute", "stmt": {"sql": "PRAGMA foreign_keys = OFF"}}
        ])

        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        tables = [r[0] for r in cursor.fetchall()]

        for table in tables:
            try:
                # Schema
                schema_r = conn.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{table}'").fetchone()
                if schema_r and schema_r[0]:
                    stmts = [
                        {"type": "execute", "stmt": {"sql": schema_r[0]}}
                    ]
                    try:
                        _turso_execute(http_url, token, stmts)
                    except Exception:
                        pass  # tabla ya existe

                # Datos
                cursor2 = conn.execute(f'SELECT * FROM "{table}"')
                rows = cursor2.fetchall()
                if not rows:
                    continue
                cols = [d[0] for d in cursor2.description]

                # Batch: DELETE + INSERTs
                batch = [{"type": "execute", "stmt": {"sql": f'DELETE FROM "{table}"'}}]
                col_names = ", ".join(f'"{c}"' for c in cols)
                placeholders = ", ".join(["?" for _ in cols])

                for row in rows:
                    args = []
                    for v in row:
                        if v is None:
                            args.append({"type": "null"})
                        elif isinstance(v, bool):
                            args.append({"type": "integer", "value": "1" if v else "0"})
                        elif isinstance(v, int):
                            args.append({"type": "integer", "value": str(v)})
                        elif isinstance(v, float):
                            args.append({"type": "float", "value": v})
                        elif isinstance(v, bytes):
                            import base64
                            args.append({"type": "blob", "base64": base64.b64encode(v).decode()})
                        else:
                            args.append({"type": "text", "value": str(v)})
                    batch.append({
                        "type": "execute",
                        "stmt": {
                            "sql": f'INSERT OR REPLACE INTO "{table}" ({col_names}) VALUES ({placeholders})',
                            "args": args
                        }
                    })

                _turso_execute(http_url, token, batch)
                logger.debug(f"Turso push: {table} ({len(rows)} filas)")
            except Exception as e:
                logger.warning(f"Turso push skip {table}: {e}")

        logger.info("Turso: push completado")
    except Exception as e:
        logger.warning(f"Turso push falló: {e}")
    finally:
        try:
            # Reactivar FKs al finalizar
            _turso_execute(http_url, token, [
                {"type": "execute", "stmt": {"sql": "PRAGMA foreign_keys = ON"}}
            ])
        except Exception:
            pass
        conn.close()


def _turso_credentials():
    return _get_turso_credentials()


class TursoConnection:
    """
    Conexión SQLite con pull automático de Turso al iniciar
    y push a Turso en cada commit.
    """

    def __init__(self, db_path, env="local"):
        self.db_path = db_path
        self.env = env or os.getenv("TURSO_ENV", "local")
        # Asegurar que el directorio existe antes de conectar
        ensure_db_dir(db_path)
        self._conn = sqlite3.connect(db_path, timeout=30)
        self._conn.row_factory = sqlite3.Row
        if self.env == "local":
            try:
                self._conn.execute("PRAGMA journal_mode=WAL")
                self._conn.execute("PRAGMA busy_timeout=5000")
            except Exception:
                pass

        # Pull NO se hace aquí — solo en get_turso_connection (sesión Streamlit)

    def cursor(self):
        return self._conn.cursor()

    def execute(self, sql, params=None):
        if params is None:
            return self._conn.execute(sql)
        return self._conn.execute(sql, params)

    def commit(self):
        self._conn.commit()
        # Solo hacer push si está explícitamente en sync mode Y tiene credenciales
        if self.env == "sync":
            url, token = _get_turso_credentials()
            if url and token:
                try:
                    turso_push(self.db_path)
                except Exception as e:
                    logger.warning(f"Push fallido (datos guardados local): {e}")

    def close(self):
        try:
            self._conn.close()
        except Exception:
            pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False


@contextmanager
def get_turso_connection(db_path, turso_url=None, turso_token=None):
    """
    Context manager para conexión Turso/SQLite.
    Hace pull de Turso al entrar (solo en modo sync).
    Push ocurre en cada commit().
    """
    env = os.getenv("TURSO_ENV", "local")
    try:
        import streamlit as st
        env = env or st.secrets.get("TURSO_ENV", "local")
    except Exception:
        pass

    # Pull al inicio de la sesión (trae datos frescos de Turso)
    # SOLO si está en sync mode Y tiene credenciales
    if env == "sync":
        url, token = _get_turso_credentials()
        if url and token:
            try:
                turso_pull(db_path)
            except Exception as e:
                logger.warning(f"Pull inicial fallido (continuando en local): {e}")

    conn = TursoConnection(db_path, env)
    try:
        yield conn
    finally:
        conn.close()


def ensure_db_dir(db_path):
    """Asegura que el directorio de la base de datos existe."""
    db_dir = os.path.dirname(db_path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
