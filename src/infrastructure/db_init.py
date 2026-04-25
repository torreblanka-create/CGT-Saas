"""
==========================================
🗄️ DATABASE INITIALIZATION — Inicialización robusta de BD
==========================================
Maneja la inicialización de BD en diferentes entornos:
- Local development (SQLite puro)
- Streamlit Cloud (BD local + opcional Turso)
- Producción (Turso Cloud si credenciales disponibles)
"""

import os
import sqlite3
import logging

logger = logging.getLogger(__name__)


def ensure_db_exists(db_path: str) -> bool:
    """
    Crea directorio y BD básica si no existen.

    Returns:
        True si la BD existe o fue creada exitosamente
        False si hay error irrecuperable
    """
    try:
        # Asegurar directorio
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
            logger.info(f"Creado directorio: {db_dir}")

        # Conectar o crear BD
        conn = sqlite3.connect(db_path, timeout=30)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        conn.execute("PRAGMA foreign_keys=ON")

        # Tabla mínima para probar
        conn.execute("""
            CREATE TABLE IF NOT EXISTS _db_init (
                id INTEGER PRIMARY KEY,
                initialized_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()

        logger.info(f"✅ BD inicializada: {db_path}")
        return True

    except Exception as e:
        logger.error(f"❌ Error inicializando BD {db_path}: {e}")
        return False


def initialize_environment():
    """
    Inicializa el entorno de BD según variables de entorno.

    Llama esto al inicio de app.py o run_dashboard.py
    """
    from config.config import DB_PATH, DB_PATH_GLOBAL

    turso_env = os.getenv("TURSO_ENV", "local")
    libsql_url = os.getenv("LIBSQL_DB_URL", "")
    libsql_token = os.getenv("LIBSQL_DB_AUTH_TOKEN", "")

    logger.info(f"🔧 Inicializando entorno BD: TURSO_ENV={turso_env}")

    # 1. Asegurar BDs locales existen
    for db_path in [DB_PATH_GLOBAL, DB_PATH]:
        ensure_db_exists(db_path)

    # 2. Informar estado de Turso
    if turso_env == "sync":
        if libsql_url and libsql_token:
            logger.info(f"✅ Turso sync: credenciales disponibles")
        else:
            logger.warning(
                "⚠️  TURSO_ENV=sync pero no hay credenciales. "
                "Funcionando en modo local (SQLite)."
            )
    else:
        logger.info(f"✅ Modo local: usando SQLite puro")

    logger.info("🎯 Inicialización de BD completada")


def handle_db_error(error: Exception, context: str = "") -> str:
    """
    Convierte error de BD a mensaje amigable.

    Args:
        error: Excepción de BD
        context: Contexto de donde ocurrió el error

    Returns:
        Mensaje de log apropiado
    """
    error_str = str(error).lower()

    if "unable to open database file" in error_str:
        return f"⚠️  BD no accesible{' en ' + context if context else ''}. Usando modo degradado."

    elif "foreign key constraint failed" in error_str:
        return f"⚠️  Restricción de integridad{' en ' + context if context else ''}. Saltando esta operación."

    elif "database is locked" in error_str:
        return f"⚠️  BD bloqueada{' en ' + context if context else ''}. Reintentando..."

    elif "no such table" in error_str:
        return f"ℹ️  Tabla no existe{' en ' + context if context else ''}. Se creará automáticamente."

    else:
        return f"⚠️  Error de BD{' en ' + context if context else ''}: {error}"
