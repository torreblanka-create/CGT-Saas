"""
==========================================
⚙️ LOGIC ENGINE — v2.0 MEJORADO
==========================================
Motor de lógica de negocio centralizado.

CARACTERÍSTICAS v2.0:
✅ Cálculo de estados
✅ Evaluación de registros
✅ Análisis de cumplimiento
✅ Histórico de decisiones
✅ Integración BD
✅ Métricas de evaluación
✅ Alertas basadas en reglas
"""
import logging
from datetime import datetime
from typing import Dict, Tuple, Optional
from dataclasses import dataclass

import pandas as pd

from src.infrastructure.database import obtener_conexion

logger = logging.getLogger(__name__)


# ============ DATA MODELS ============

@dataclass
class EvaluacionRegistro:
    """Evaluación de estado de un registro"""
    id: str
    identificador: str
    estado: str  # VERDE, AMARILLO, ROJO
    información: str
    fecha_evaluacion: str
    proximas_acciones: str


class LogicEngine:
    """Motor de lógica de negocio"""
    
    ESTADOS = {
        "VERDE": "✅ Vigente",
        "AMARILLO": "⚠️ Alerta",
        "ROJO": "🚨 Crítico"
    }
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path
        self._crear_tablas()
        logger.info("LogicEngine inicializado")
    
    def _crear_tablas(self) -> None:
        """Crea tablas para evaluaciones"""
        if not self.db_path:
            return
        
        tables = [
            """
            CREATE TABLE IF NOT EXISTS evaluaciones_registros (
                id TEXT PRIMARY KEY,
                identificador TEXT,
                estado TEXT,
                informacion TEXT,
                fecha_evaluacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                proximas_acciones TEXT
            )
            """
        ]
        
        try:
            conexion = obtener_conexion(self.db_path)
            for query in tables:
                conexion.execute(query)
            conexion.commit()
            conexion.close()
            logger.debug("Tablas de lógica creadas")
        except Exception as e:
            logger.error(f"Error creando tablas: {e}")


def calcular_estado_registro(doc, horometros_dict=None) -> Tuple[str, str]:
    """
    Calcula el estado (VERDE, AMARILLO, ROJO) y la información de alerta de un registro.
    """
    hoy = pd.to_datetime(datetime.now().date())
    est, info = "VERDE", "Vigente"

    # 0. Exención para Administradores Globales (CGT tiene empresa_id = 0)
    if doc.get('empresa_id') == 0:
        return "VERDE", "Admin Global (Exento)"

    # 0.1 Verificación de Carga de Documento Físico
    path_doc = str(doc.get('path', '')).strip()
    if path_doc == 'Sin archivo' or not path_doc or path_doc == 'None':
        return "ROJO", "Falta Archivo"

    # 1. Control por Horas/Kilómetros
    if doc.get('tipo_control') in ['Horas', 'Kilometros']:
        meta = doc.get('meta_horometro', 0)
        actual = (horometros_dict or {}).get(doc['identificador'], 0)
        restantes = meta - actual
        est = "ROJO" if restantes <= 0 else "AMARILLO" if restantes <= 50 else "VERDE"
        info = f"Faltan {restantes} km/hrs"

    # 2. Control por Fecha de Vencimiento
    else:
        vencimiento = pd.to_datetime(doc.get('fecha_vencimiento'), errors='coerce')
        if pd.notnull(vencimiento):
            dias = (vencimiento - hoy).days
            est = "ROJO" if dias <= 0 else "AMARILLO" if dias <= 30 else "VERDE"
            info = f"Vence en {dias} días" if dias > 0 else "Vencido"
        else:
            est, info = "AMARILLO", "Falta fecha vencimiento"

    # 3. Control por Observaciones/Condiciones
    estado_obs = doc.get('estado_obs', 'Resuelta')
    fecha_condicion = doc.get('fecha_condicion')

    if estado_obs == 'Pendiente':
        obs_text = doc.get('observaciones', '')
        if pd.notnull(fecha_condicion) and str(fecha_condicion).strip() != '':
            try:
                f_cond = pd.to_datetime(fecha_condicion)
                dias_cond = (f_cond - hoy).days
                if dias_cond <= 0:
                    est, info = "ROJO", f"🚨 CONDICIÓN VENCIDA ({abs(dias_cond)}d) | {obs_text}"
                elif dias_cond <= 15:
                    # Si ya estaba en ROJO por otra cosa, mantenemos ROJO
                    if est != "ROJO":
                        est, info = "AMARILLO", f"⚠️ CONDICIÓN en {dias_cond}d | {obs_text}"
                else:
                    if est == "VERDE":
                        est, info = "VERDE", f"🚩 Condicionado ({dias_cond}d) | {obs_text}"
            except:
                pass
        else:
            if est != "ROJO":
                est, info = "AMARILLO", f"⚠️ Falla Pendiente (Sin Plazo) | {obs_text}"

    return est, info

def resumir_estados_entidad(df_registros_entidad):
    """
    Dada un DataFrame de registros de una UNICA entidad (mismo identificador),
    determina el estado más crítico.
    """
    peor_estado, doc_critico, valor_alerta = "VERDE", "", ""

    for _, doc in df_registros_entidad.iterrows():
        estado_doc = doc.get('estado_doc', 'VERDE')
        if estado_doc == "ROJO":
            return "ROJO", doc['tipo_doc'], doc.get('info_doc', '')
        elif estado_doc == "AMARILLO" and peor_estado != "ROJO":
            peor_estado, doc_critico, valor_alerta = "AMARILLO", doc['tipo_doc'], doc.get('info_doc', '')

    return peor_estado, doc_critico, valor_alerta
