"""
Turso Cloud Database Adapter - Abstracción para SQLite Local + Turso Cloud

Proporciona una capa de abstracción que permite:
- Desarrollo local: SQLite puro (app.db)
- Producción: Réplica local con sincronización a Turso Cloud
- Fallback: Totalmente compatible con sqlite3 (DB-API 2.0)

Uso:
    from src.infrastructure.turso_adapter import get_turso_connection

    # En modo local: usa SQLite directo
    # En modo sync: usa local + pull/push automático
    with get_turso_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM usuarios")
        results = cursor.fetchall()
"""

import os
import time
from contextlib import contextmanager

# Intenta importar turso; fallback a sqlite3 si no está disponible
try:
    import turso
    TURSO_AVAILABLE = True
except ImportError:
    import sqlite3 as turso
    TURSO_AVAILABLE = False


class TursoConnection:
    """Wrapper que encapsula conexión local+cloud con sincronización automática."""

    def __init__(self, db_path, turso_url=None, turso_token=None, env="local"):
        """
        Inicializa conexión Turso.

        Args:
            db_path: Ruta local a app.db
            turso_url: URL de Turso (libsql://...)
            turso_token: Token de autenticación
            env: "local" (SQLite puro) o "sync" (local + cloud)
        """
        self.db_path = db_path
        self.turso_url = turso_url
        self.turso_token = turso_token
        self.env = env
        self.is_sync = env == "sync"
        self.conn = None
        self.last_sync = None

        # Conectar a base de datos local
        if TURSO_AVAILABLE:
            self.conn = turso.connect(db_path)
        else:
            self.conn = turso.connect(db_path, timeout=30)

        # En modo sync, descargar cambios iniciales desde cloud
        if self.is_sync and TURSO_AVAILABLE and self.turso_url:
            self._pull_with_retry()

    def _pull_with_retry(self, max_retries=3):
        """Sincroniza cloud → local con reintentos."""
        if not hasattr(self.conn, 'pull'):
            return

        for attempt in range(max_retries):
            try:
                self.conn.pull()
                self.last_sync = time.time()
                return
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Backoff exponencial: 1s, 2s, 4s
                    time.sleep(wait_time)
                else:
                    print(f"⚠️ Pull fallido tras {max_retries} intentos: {e}")

    def _push_with_retry(self, max_retries=3):
        """Sincroniza local → cloud con reintentos."""
        if not self.is_sync or not hasattr(self.conn, 'push'):
            return

        for attempt in range(max_retries):
            try:
                self.conn.push()
                self.last_sync = time.time()
                return
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    time.sleep(wait_time)
                else:
                    print(f"⚠️ Push fallido tras {max_retries} intentos: {e}")

    def cursor(self):
        """Retorna cursor SQLite estándar."""
        return self.conn.cursor()

    def execute(self, sql, params=()):
        """Ejecuta SQL y retorna cursor."""
        return self.conn.execute(sql, params)

    def commit(self):
        """Confirma transacción y sincroniza a cloud si es sync mode."""
        self.conn.commit()
        if self.is_sync:
            self._push_with_retry()

    def rollback(self):
        """Revierte transacción."""
        self.conn.rollback()

    def close(self):
        """Cierra conexión y realiza sincronización final si es necesario."""
        if self.is_sync:
            self._push_with_retry()
        if self.conn:
            self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False


@contextmanager
def get_turso_connection(db_path, turso_url=None, turso_token=None):
    """
    Context manager que retorna una conexión TursoConnection.

    Ejemplo:
        with get_turso_connection(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM usuarios")
    """
    env = os.getenv("TURSO_ENV", "local")

    # En producción (Streamlit Cloud), las variables de entorno vienen de st.secrets
    if not turso_url:
        try:
            import streamlit as st
            turso_url = st.secrets.get("LIBSQL_DB_URL")
            turso_token = st.secrets.get("LIBSQL_DB_AUTH_TOKEN")
        except Exception:
            pass

    # Fallback a variables de entorno
    if not turso_url:
        turso_url = os.getenv("LIBSQL_DB_URL")
    if not turso_token:
        turso_token = os.getenv("LIBSQL_DB_AUTH_TOKEN")

    conn = TursoConnection(db_path, turso_url, turso_token, env)
    try:
        yield conn
    finally:
        conn.close()


def ensure_db_dir(db_path):
    """Asegura que el directorio de la base de datos existe."""
    db_dir = os.path.dirname(db_path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
