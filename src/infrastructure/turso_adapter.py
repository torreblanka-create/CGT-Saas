"""
==========================================
🌐 TURSO ADAPTER — v2.0 SINCRONIZACIÓN REAL
==========================================
Adaptador que conecta SQLite local con Turso Cloud.

MODOS DE OPERACIÓN:
- "local" → SQLite puro (desarrollo local, sin internet)
- "sync"  → SQLite local + sincronización bidireccional con Turso Cloud
- "cloud" → Solo Turso Cloud vía HTTP (sin caché local)

Flujo:
  .pull() al iniciar → descarga datos de Turso → caché local
  .commit() → escribe en local + .push() a Turso
  .close() → .push() final
"""

import os
import sqlite3
import logging
from contextlib import contextmanager
from datetime import datetime

logger = logging.getLogger(__name__)


class TursoConnection:
    """
    Conexión SQLite con sincronización a Turso Cloud.
    
    En modo "sync":
    - .pull() al iniciar: descarga datos desde Turso → local
    - .commit(): escribe en local + .push() a Turso
    - .close(): .push() final antes de cerrar
    """
    
    def __init__(self, db_path, turso_url=None, turso_token=None, env="local"):
        self.db_path = db_path
        self.turso_url = turso_url or os.getenv("LIBSQL_DB_URL")
        self.turso_token = turso_token or os.getenv("LIBSQL_DB_AUTH_TOKEN")
        self.env = env or os.getenv("TURSO_ENV", "local")
        self._conn = None
        self._turso_db = None
        self._dirty = False  # Track if there are pending writes
        
        # Inicializar conexión local
        self._init_local()
        
        # En modo sync/cloud, conectar a Turso y hacer pull inicial
        if self.env in ("sync", "cloud"):
            self._init_turso()
            if self.env == "sync":
                self._pull()
    
    def _init_local(self):
        """Inicializa conexión SQLite local"""
        self._conn = sqlite3.connect(self.db_path, timeout=30)
        self._conn.row_factory = sqlite3.Row
        if self.env == "local":
            try:
                self._conn.execute("PRAGMA journal_mode=WAL")
                self._conn.execute("PRAGMA busy_timeout=5000")
            except Exception:
                pass
    
    def _init_turso(self):
        """Inicializa conexión a Turso Cloud"""
        if not self.turso_url or not self.turso_token:
            logger.warning("⚠️ Turso: Faltan LIBSQL_DB_URL o LIBSQL_DB_AUTH_TOKEN")
            return
        
        try:
            from libsql_client import create_client
            self._turso_db = create_client(
                url=self.turso_url,
                auth_token=self.turso_token
            )
            logger.info("✅ Turso: Conexión establecida")
        except ImportError:
            logger.error("❌ Turso: libsql_client no instalado. pip install libsql-client")
        except Exception as e:
            logger.error(f"❌ Turso: Error conectando: {e}")
    
    def _pull(self):
        """
        Sincroniza Turso Cloud → SQLite local.
        Descarga todas las tablas y las escribe en la base local.
        """
        if not self._turso_db:
            return
        
        try:
            logger.info("🔄 Turso: Pull iniciado (cloud → local)")
            
            # Obtener lista de tablas desde Turso
            result = self._turso_db.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row['name'] for row in result.rows if not row['name'].startswith('sqlite_')]
            
            if not tables:
                logger.info("ℹ️ Turso: No hay tablas en la nube (primera vez)")
                return
            
            for table in tables:
                try:
                    # Obtener datos desde Turso
                    rows = self._turso_db.execute(f"SELECT * FROM \"{table}\"")
                    
                    if not rows.rows:
                        continue
                    
                    # Obtener nombres de columnas
                    columns = [col['name'] for col in rows.columns]
                    
                    # Limpiar tabla local e insertar datos de Turso
                    placeholders = ", ".join(["?"] * len(columns))
                    col_names = ", ".join(f'"{c}"' for c in columns)
                    
                    self._conn.execute(f"DELETE FROM \"{table}\"")
                    
                    for row in rows.rows:
                        values = [row[col] for col in columns]
                        self._conn.execute(
                            f"INSERT INTO \"{table}\" ({col_names}) VALUES ({placeholders})",
                            values
                        )
                    
                    self._conn.commit()
                    logger.debug(f"  ✅ Tabla '{table}': {len(rows.rows)} registros sincronizados")
                    
                except Exception as e:
                    logger.debug(f"  ⚠️ Tabla '{table}': {e}")
            
            logger.info("✅ Turso: Pull completado")
            
        except Exception as e:
            logger.error(f"❌ Turso: Error en pull: {e}")
    
    def _push(self):
        """
        Sincroniza SQLite local → Turso Cloud.
        Sube todas las tablas locales a Turso.
        """
        if not self._turso_db or not self._dirty:
            return
        
        try:
            logger.info("🔄 Turso: Push iniciado (local → cloud)")
            
            # Obtener lista de tablas locales
            cursor = self._conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row['name'] for row in cursor.fetchall() if not row['name'].startswith('sqlite_')]
            
            for table in tables:
                try:
                    # Obtener datos locales
                    cursor = self._conn.execute(f"SELECT * FROM \"{table}\"")
                    rows = cursor.fetchall()
                    columns = [desc[0] for desc in cursor.description]
                    
                    if not rows:
                        continue
                    
                    # Limpiar tabla en Turso e insertar datos locales
                    self._turso_db.execute(f"DELETE FROM \"{table}\"")
                    
                    placeholders = ", ".join(["?"] * len(columns))
                    col_names = ", ".join(f'"{c}"' for c in columns)
                    
                    for row in rows:
                        values = [row[col] for col in columns]
                        self._turso_db.execute(
                            f"INSERT INTO \"{table}\" ({col_names}) VALUES ({placeholders})",
                            values
                        )
                    
                    logger.debug(f"  ✅ Tabla '{table}': {len(rows)} registros subidos")
                    
                except Exception as e:
                    logger.debug(f"  ⚠️ Tabla '{table}': {e}")
            
            self._dirty = False
            logger.info("✅ Turso: Push completado")
            
        except Exception as e:
            logger.error(f"❌ Turso: Error en push: {e}")
    
    def cursor(self):
        """Retorna cursor SQLite estándar"""
        return self._conn.cursor()
    
    def execute(self, sql, params=None):
        """Ejecuta SQL directamente sobre la conexión local"""
        if params is None:
            return self._conn.execute(sql)
        return self._conn.execute(sql, params)
    
    def commit(self):
        """Commit local + push a Turso (si hay cambios)"""
        self._conn.commit()
        self._dirty = True
        if self.env in ("sync", "cloud"):
            self._push()
    
    def close(self):
        """Cierra conexiones: push final + close local"""
        try:
            if self.env in ("sync", "cloud"):
                self._push()
        except Exception as e:
            logger.error(f"❌ Turso: Error en push final: {e}")
        
        try:
            if self._conn:
                self._conn.close()
        except Exception:
            pass
        
        try:
            if self._turso_db:
                self._turso_db.close()
        except Exception:
            pass


@contextmanager
def get_turso_connection(db_path, turso_url=None, turso_token=None):
    """
    Context manager para conexión Turso.
    
    Uso:
        with get_turso_connection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM usuarios")
    
    En modo "sync":
    - Pull automático al conectar
    - Push automático al hacer commit
    - Push final al cerrar
    """
    env = os.getenv("TURSO_ENV", "local")
    
    # Fallback a st.secrets si está disponible
    if not turso_url:
        turso_url = os.getenv("LIBSQL_DB_URL")
        try:
            import streamlit as st
            if not turso_url:
                turso_url = st.secrets.get("LIBSQL_DB_URL")
        except Exception:
            pass
    
    if not turso_token:
        turso_token = os.getenv("LIBSQL_DB_AUTH_TOKEN")
        try:
            import streamlit as st
            if not turso_token:
                turso_token = st.secrets.get("LIBSQL_DB_AUTH_TOKEN")
        except Exception:
            pass
    
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
