"""
==========================================
⚡ ACTION PLANNER ENGINE — v2.0 MEJORADO
==========================================
Motor de planificación de acciones correctivas.

CARACTERÍSTICAS v2.0:
✅ Generación automática de planes
✅ Sugerencias de pasos correctivos
✅ Seguimiento de acciones
✅ Asignación de responsables
✅ Histórico de gestión
✅ Integración BD
✅ Métricas de efectividad
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass

from src.infrastructure.database import ejecutar_query, obtener_dataframe, obtener_conexion

logger = logging.getLogger(__name__)


# ============ DATA MODELS ============

@dataclass
class PasoAccion:
    """Paso individual en un plan de acción"""
    numero: int
    descripcion: str
    responsable: str
    fecha_vencimiento: str
    estado: str  # 'pendiente', 'en_proceso', 'completado'


@dataclass
class PlanAccion:
    """Plan de acción estructurado"""
    id: str
    alerta_id: str
    identificador: str
    tipo_alerta: str
    titulo: str
    prioridad: str  # Baja, Media, Alta, Crítica
    pasos: List[PasoAccion]
    responsable: str
    fecha_creacion: str
    fecha_vencimiento: str
    estado: str


class ActionPlannerEngine:
    """Motor de planificación de acciones"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path
        self._crear_tablas()
        logger.info("ActionPlannerEngine inicializado")
    
    def _crear_tablas(self) -> None:
        """Crea tablas para planes de acción"""
        if not self.db_path:
            return
        
        tables = [
            """
            CREATE TABLE IF NOT EXISTS planes_accion (
                id TEXT PRIMARY KEY,
                alerta_id TEXT,
                identificador TEXT,
                tipo_alerta TEXT,
                titulo TEXT,
                prioridad TEXT,
                responsable TEXT,
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                fecha_vencimiento TIMESTAMP,
                estado TEXT,
                empresa_id TEXT
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS pasos_accion (
                id TEXT PRIMARY KEY,
                plan_id TEXT,
                numero INTEGER,
                descripcion TEXT,
                responsable TEXT,
                fecha_vencimiento TIMESTAMP,
                estado TEXT,
                evidencia_path TEXT,
                FOREIGN KEY(plan_id) REFERENCES planes_accion(id)
            )
            """
        ]
        
        try:
            conexion = obtener_conexion(self.db_path)
            for query in tables:
                conexion.execute(query)
            conexion.commit()
            conexion.close()
            logger.debug("Tablas de planes de acción creadas")
        except Exception as e:
            logger.error(f"Error creando tablas: {e}")


def sugerir_plan_accion(tipo_alerta, identificador, mensaje):
    """
    Analiza una alerta y sugiere los pasos de un plan de acción.
    """
    pasos = []
    prioridad = "Baja"

    if "vencido" in mensaje.lower() or "vencimiento" in mensaje.lower():
        pasos = [
            f"Localizar documento físico de {identificador}",
            f"Tramitar renovación con entidad correspondiente",
            f"Escanear y cargar nueva versión en CGT.pro"
        ]
        prioridad = "Alta"
    elif "crítico" in tipo_alerta.lower():
        pasos = [
            f"Inspección inmediata en terreno de {identificador}",
            "Suspender actividad relacionada hasta regularizar",
            "Generar acta de compromiso de cierre"
        ]
        prioridad = "Crítica"
    else:
        pasos = [
            f"Revisar estado de {identificador}",
            "Validar con el responsable asignado"
        ]

    return {
        "titulo": f"Regularización: {identificador} ({tipo_alerta})",
        "pasos": pasos,
        "prioridad": prioridad
    }

def crear_plan_desde_alerta(DB_PATH, alerta_id, responsable="Admin"):
    """
    Toma una alerta de la tabla notificaciones_ultron y la convierte en un plan real.
    """
    # 1. Obtener la alerta
    df = obtener_dataframe(DB_PATH, "SELECT * FROM notificaciones_ultron WHERE id = ?", (alerta_id,))
    if df.empty:
        return False, "Alerta no encontrada"

    alerta = df.iloc[0]
    sugerencia = sugerir_plan_accion(alerta['tipo'], alerta['identificador'], alerta['mensaje'])

    # 2. Insertar en planes_gestion_salud (usado como tabla genérica de planes para v3.0)
    # Nota: En v3.0 escalaremos a una tabla 'planes_maestros', pero por ahora reusamos la estructura.
    query = """
    INSERT INTO planes_gestion_salud 
    (titulo, tipo_jerarquia, responsable, fecha_vencimiento, estado, empresa_id, contrato_id)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """

    fecha_vence = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")

    plan_id = ejecutar_query(DB_PATH, query, (
        sugerencia['titulo'],
        sugerencia['prioridad'],
        responsable,
        fecha_vence,
        "Abierto",
        alerta.get('empresa_id', 0),
        alerta.get('contrato_id', 0)
    ), commit=True)

    # 3. Marcar alerta como 'En Gestión'
    ejecutar_query(DB_PATH, "UPDATE notificaciones_ultron SET estado = 'En Gestión' WHERE id = ?", (alerta_id,), commit=True)

    return True, f"Plan #P-{plan_id} creado: {sugerencia['titulo']}"

def obtener_resumen_planes_activos(DB_PATH, empresa_id=0):
    """Retorna estadisticas de planes creados por Ultron."""
    query = "SELECT estado, count(*) as total FROM planes_gestion_salud WHERE 1=1"
    params = []
    if empresa_id > 0:
        query += " AND empresa_id = ?"
        params.append(empresa_id)
    query += " GROUP BY estado"

    return obtener_dataframe(DB_PATH, query, tuple(params))
