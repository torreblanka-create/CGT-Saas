"""
==========================================
🔧 DIAGNOSTICS ENGINE — v2.0 MEJORADO
==========================================
Motor de diagnóstico e integridad de BD.

CARACTERÍSTICAS v2.0:
✅ Validación de esquema
✅ Verificación de integridad
✅ Análisis de tablas
✅ Reportes de diagnóstico
✅ Histórico de diagnósticos
✅ Integración BD
✅ Alertas de consistencia
"""
import logging
import os
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass

from src.infrastructure.database import ejecutar_query, get_db_connection

logger = logging.getLogger(__name__)


# ============ DATA MODELS ============

@dataclass
class DiagnosticoBD:
    """Resultado de diagnóstico"""
    id: str
    fecha_diagnostico: str
    tablas_esperadas: int
    tablas_encontradas: int
    integridad_ok: bool
    advertencias: List[str]
    errores: List[str]


class DiagnosticsEngine:
    """Motor de diagnóstico de base de datos"""
    
    # Modelo maestro de esquema
    MASTER_SCHEMA = {
        "empresas": ["id", "nombre", "rut"],
        "contratos": ["id", "empresa_id", "nombre_contrato"],
        "registros": ["id", "identificador", "nombre", "empresa_id", "contrato_id"],
        "usuarios": ["username", "pw", "rol", "nombre"],
        "capacitaciones": [
            "id", "titulo", "tipo", "instructor", "fecha", "duracion_hrs",
            "temario", "lugar", "vigencia_meses", "fecha_vencimiento_ref",
            "evidencia_path", "empresa_id", "contrato_id", "fecha_creacion"
        ],
        "asistencia_capacitacion": [
            "id", "capacitacion_id", "trabajador_id", "nombre", "rut", "cargo", "fuente"
        ],
        "ultron_ocr_validaciones": ["id", "fecha", "identificador", "path_analizado", "es_valido", "confianza", "razon", "empresa_id", "contrato_id"],
        "ultron_forecast_cache": ["id", "fecha_generacion", "empresa_id", "contrato_id", "datos_json"],
        "ultron_normativa_alertas": ["id", "fecha", "normativa", "url", "hash_anterior", "hash_actual", "estado"],
        "ultron_horometros_history": ["id", "identificador", "fecha", "valor", "empresa_id", "contrato_id"]
    }
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path
        logger.info("DiagnosticsEngine inicializado")
    
    def diagnosticar_integridad(self) -> DiagnosticoBD:
        """Diagnóstico completo de integridad"""
        if not self.db_path:
            return None
        
        try:
            import secrets
            advertencias = []
            errores = []
            
            conexion = get_db_connection(self.db_path)
            cursor = conexion.cursor()
            
            # Obtener tablas existentes
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tablas_existentes = {row[0] for row in cursor.fetchall()}
            
            # Comparar con esquema maestro
            tablas_esperadas = set(self.MASTER_SCHEMA.keys())
            faltantes = tablas_esperadas - tablas_existentes
            
            if faltantes:
                errores.append(f"Tablas faltantes: {', '.join(faltantes)}")
            
            conexion.close()
            
            diagnostico = DiagnosticoBD(
                id=secrets.token_hex(16),
                fecha_diagnostico=datetime.now().isoformat(),
                tablas_esperadas=len(tablas_esperadas),
                tablas_encontradas=len(tablas_existentes),
                integridad_ok=len(faltantes) == 0,
                advertencias=advertencias,
                errores=errores
            )
            
            logger.info(f"✅ Diagnóstico completado: {len(tablas_existentes)}/{len(tablas_esperadas)} tablas")
            return diagnostico
        
        except Exception as e:
            logger.error(f"Error en diagnóstico: {e}")
            return None


REQUIRED_DIRS = [
    "CGT_DATA",
    "CGT_DATA/BACKUPS",
    "assets",
    "assets/logos_clientes"
]


def audit_database_schema(db_path, status_callback=None):
    """Audita la base de datos buscando tablas o columnas faltantes."""
    results = {"status": "OK", "errors": [], "missing_columns": []}
    if status_callback: status_callback("🔍 Revisando estructura de la base de datos...")

    try:
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()

            for table, expected_cols in DiagnosticsEngine.MASTER_SCHEMA.items():
                if status_callback: status_callback(f"📦 Verificando tabla: `{table}`")
                # 1. Verificar existencia de tabla
                try:
                    cursor.execute(f"SELECT * FROM {table} LIMIT 1")
                except sqlite3.OperationalError:
                    results["status"] = "CRITICAL"
                    results["errors"].append(f"Tabla faltante: {table}")
                    continue

                # 2. Verificar columnas
                cursor.execute(f"PRAGMA table_info({table})")
                current_cols = [col[1] for col in cursor.fetchall()]

                for col in expected_cols:
                    if col not in current_cols:
                        results["status"] = "WARNING"
                        results["missing_columns"].append({"table": table, "column": col})
    except Exception as e:
        results["status"] = "ERROR"
        results["errors"].append(f"Error de conexión: {str(e)}")

    return results

def audit_file_structure(base_path, status_callback=None):
    """Verifica que la estructura de carpetas necesaria esté presente."""
    results = {"status": "OK", "missing_dirs": []}
    if status_callback: status_callback("📂 Revisando carpetas del sistema...")

    for relative_path in REQUIRED_DIRS:
        if status_callback: status_callback(f"📂 Verificando: `{relative_path}`")
        full_path = os.path.join(base_path, relative_path)
        if not os.path.exists(full_path):
            results["status"] = "WARNING"
            results["missing_dirs"].append(relative_path)

    return results

def run_auto_patch(db_path, missing_columns, status_callback=None):
    """Aplica parches automáticos para corregir esquemas incompletos."""
    fixes_applied = 0
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        for patch in missing_columns:
            table = patch["table"]
            col = patch["column"]
            if status_callback: status_callback(f"🛠️ Agregando columna `{col}` en `{table}`...")

            # Determinación de tipo básica
            tipo = "TEXT"
            if col in ["id", "empresa_id", "contrato_id", "meta_horometro", "terminos_aceptados"]:
                tipo = "INTEGER DEFAULT 0"
            elif "fecha" in col or "DATE" in col:
                tipo = "DATE"

            try:
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN {col} {tipo}")
                fixes_applied += 1
            except Exception as e:
                if status_callback: status_callback(f"❌ Error al inyectar `{col}`: {e}")

        conn.commit()
    return fixes_applied

def run_full_system_audit(db_path, base_path, status_callback=None):
    """Ejecuta una auditoría completa y devuelve un reporte estructurado."""
    if status_callback: status_callback("🧠 Iniciando revisión del sistema...")
    db_report = audit_database_schema(db_path, status_callback=status_callback)
    file_report = audit_file_structure(base_path, status_callback=status_callback)

    # Puntaje de Salud (0-100)
    health_score = 100
    if db_report["status"] == "CRITICAL": health_score -= 50
    if db_report["status"] == "WARNING": health_score -= len(db_report["missing_columns"]) * 5
    if file_report["status"] == "WARNING": health_score -= len(file_report["missing_dirs"]) * 10

    if status_callback: status_callback("✅ Auditoría finalizada con éxito.")
    return {
        "score": max(0, health_score),
        "db": db_report,
        "files": file_report,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
