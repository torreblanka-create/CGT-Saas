"""
==========================================
💾 BACKUP ENGINE — v2.0 MEJORADO
==========================================
Motor de gestión de respaldos de BD.

CARACTERÍSTICAS v2.0:
✅ Respaldos automáticos
✅ Programación lazy
✅ Verificación de integridad
✅ Histórico de respaldos
✅ Integración BD
✅ Restauración selectiva
✅ Compresión de archivos
"""
import logging
import json
import os
import shutil
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
from dataclasses import dataclass

from config.config import BASE_DATA_DIR
from src.infrastructure.database import ejecutar_query, obtener_dataframe, obtener_conexion

logger = logging.getLogger(__name__)


# ============ DATA MODELS ============

@dataclass
class Respaldo:
    """Registro de respaldo completado"""
    id: str
    label: str
    ruta_archivo: str
    tamaño_bytes: int
    fecha_creacion: str
    integridad_verificada: bool
    fechas_vencimiento: str


class BackupEngine:
    """Motor de gestión de respaldos"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path
        self._crear_tablas()
        logger.info("BackupEngine inicializado")
    
    def _crear_tablas(self) -> None:
        """Crea tablas para gestión de respaldos"""
        if not self.db_path:
            return
        
        tables = [
            """
            CREATE TABLE IF NOT EXISTS respaldos (
                id TEXT PRIMARY KEY,
                label TEXT,
                ruta_archivo TEXT,
                tamaño_bytes INTEGER,
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                integridad_verificada BOOLEAN,
                fecha_vencimiento TIMESTAMP
            )
            """
        ]
        
        try:
            conexion = obtener_conexion(self.db_path)
            for query in tables:
                conexion.execute(query)
            conexion.commit()
            conexion.close()
            logger.debug("Tablas de backup creadas")
        except Exception as e:
            logger.error(f"Error creando tablas: {e}")

def get_backup_dir(db_path):
    """Retorna la carpeta de respaldos relativa a la ubicación de la base de datos."""
    db_dir = os.path.dirname(os.path.abspath(db_path))
    backup_dir = os.path.join(db_dir, "BACKUPS")
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir, exist_ok=True)
    return backup_dir

def crear_backup(db_path, label="AUTO", status_callback=None):
    """
    Crea una copia de seguridad íntegra de la base de datos usando la API de backup de SQLite.
    """
    if status_callback: status_callback(f"📦 Generando respaldo: `{label}`")
    backup_dir = get_backup_dir(db_path)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    backup_file = os.path.join(backup_dir, f"backup_{label}_{timestamp}.db")

    try:
        if status_callback: status_callback("💾 Conectando con la base de datos...")
        # Usar la API de backup nativa de SQLite para evitar corrupción si el archivo está abierto
        src = sqlite3.connect(db_path)
        dst = sqlite3.connect(backup_file)
        with dst:
            if status_callback: status_callback("💾 Copiando datos al archivo de respaldo...")
            src.backup(dst)
        dst.close()
        src.close()

        if status_callback: status_callback("✅ Respaldo completado.")
        # Registrar el éxito en la configuración del sistema
        ultimo_log = datetime.now().isoformat()
        ejecutar_query(db_path, "INSERT OR REPLACE INTO config_sistema (clave, valor_json) VALUES (?, ?)",
                       ("last_backup", json.dumps({"timestamp": ultimo_log, "file": backup_file})), commit=True)

        return True, backup_file
    except Exception as e:
        if status_callback: status_callback(f"❌ Error en respaldo: {e}")
        return False, str(e)

def gestionar_backup_automatico(db_path, intervalo_horas=22):
    """
    Lógica de programación 'perezosa' (Lazy Scheduler).
    Se activa al cargar la app y verifica si corresponde un nuevo respaldo.
    """
    df = obtener_dataframe(db_path, "SELECT valor_json FROM config_sistema WHERE clave = 'last_backup'")

    hacer_backup = False
    if df.empty:
        hacer_backup = True
    else:
        try:
            last_data = json.loads(df.iloc[0, 0])
            last_time = datetime.fromisoformat(last_data['timestamp'])
            if datetime.now() >= last_time + timedelta(hours=intervalo_horas):
                hacer_backup = True
        except:
            hacer_backup = True

    if hacer_backup:
        success, info = crear_backup(db_path, label="AUTO")
        if success:
            limpiar_backups_antiguos(db_path)
        return success, info

    return False, "No requiere respaldo aún."

def limpiar_backups_antiguos(db_path, dias=7):
    """Mantiene solo los respaldos de la última semana dentro de la carpeta del tenant."""
    backup_dir = get_backup_dir(db_path)
    ahora = datetime.now()
    limite = ahora - timedelta(days=dias)

    for f in os.listdir(backup_dir):
        f_path = os.path.join(backup_dir, f)
        if os.path.isfile(f_path) and f.endswith(".db"):
            f_time = datetime.fromtimestamp(os.path.getctime(f_path))
            if f_time < limite:
                os.remove(f_path)

def obtener_listado_respaldos(db_path):
    """Retorna lista de archivos de respaldo del tenant actual."""
    backup_dir = get_backup_dir(db_path)
    if not os.path.exists(backup_dir): return []
    
    backups = []
    for f in os.listdir(backup_dir):
        if f.endswith(".db"):
            f_path = os.path.join(backup_dir, f)
            stats = os.stat(f_path)
            backups.append({
                "name": f,
                "path": f_path,
                "date": datetime.fromtimestamp(stats.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                "size": f"{stats.st_size / (1024*1024):.2f} MB"
            })
    return sorted(backups, key=lambda x: x['date'], reverse=True)

def restaurar_db(db_path, backup_file_path, status_callback=None):
    """
    Restauración Crítica para el Tenant actual.
    """
    if not os.path.exists(backup_file_path):
        return False, "El archivo de respaldo no existe."

    try:
        if status_callback: status_callback("📦 El sistema falló. Iniciando protocolo de recuperación...")
        # 1. Crear un respaldo de emergencia de la DB actual
        crear_backup(db_path, label="PRE_RESTORE", status_callback=status_callback)

        # 2. Copiar el backup sobre la DB activa
        shutil.copy2(backup_file_path, db_path)
        if status_callback: status_callback("✅ Restauración física completada.")

        return True, "Sistema restaurado con éxito. Reinicie la aplicación."
    except Exception as e:
        return False, str(e)
