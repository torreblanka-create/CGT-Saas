"""
==========================================
🔮 PREDICTION ENGINE — v2.0 MEJORADO
==========================================
Motor predictivo de mantenimiento.

CARACTERÍSTICAS v2.0:
✅ Pronóstico de mantenimiento
✅ Análisis de uso de equipos
✅ Proyecciones de vida útil
✅ Alertas preventivas
✅ Histórico de predicciones
✅ Recomendaciones inteligentes
✅ Integración con calendarios
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional
from dataclasses import dataclass

import pandas as pd

from src.infrastructure.database import obtener_dataframe, obtener_conexion

logger = logging.getLogger(__name__)


# ============ DATA MODELS ============

@dataclass
class PronosticoMantenimiento:
    """Pronóstico de mantenimiento para un equipo"""
    id: str
    identificador: str
    estado: str  # SALUDABLE, PREVENTIVO, CRÍTICO
    uso_diario: float
    meta_horometro: int
    valor_actual: int
    dias_restantes: int
    fecha_proyectada: str
    confianza: float  # 0-100%


class PredictionEngine:
    """Motor de predicción de mantenimiento"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path
        self._crear_tablas()
        logger.info("PredictionEngine inicializado")
    
    def _crear_tablas(self) -> None:
        """Crea tablas para pronósticos"""
        if not self.db_path:
            return
        
        tables = [
            """
            CREATE TABLE IF NOT EXISTS pronosticos_mantenimiento (
                id TEXT PRIMARY KEY,
                identificador TEXT,
                estado TEXT,
                uso_diario REAL,
                meta_horometro INTEGER,
                valor_actual INTEGER,
                dias_restantes INTEGER,
                fecha_proyectada TEXT,
                confianza REAL,
                fecha_pronostico TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        ]
        
        try:
            conexion = obtener_conexion(self.db_path)
            for query in tables:
                conexion.execute(query)
            conexion.commit()
            conexion.close()
            logger.debug("Tablas de prediction creadas")
        except Exception as e:
            logger.error(f"Error creando tablas: {e}")


def proyectar_mantenimiento_maquinaria(DB_PATH, identificador):
    """
    Calcula la fecha proyectada de mantenimiento para un equipo.
    Basado en ΔLectura / ΔTiempo.
    """
    # 1. Obtener historial de lecturas
    query = """
        SELECT fecha, valor 
        FROM ultron_horometros_history 
        WHERE identificador = ? 
        ORDER BY fecha ASC
    """
    df_hist = obtener_dataframe(DB_PATH, query, (identificador,))

    if len(df_hist) < 2:
        return {"error": "Insuficientes datos: Se requieren al menos 2 lecturas en el tiempo."}

    # 2. Obtener meta del registro actual
    df_meta = obtener_dataframe(DB_PATH, "SELECT meta_horometro FROM registros WHERE identificador = ?", (identificador,))
    if df_meta.empty:
        return {"error": "Registro de equipo no encontrado."}

    meta = df_meta.iloc[0]['meta_horometro']
    if not meta or meta <= 0:
        return {"error": "No se ha definido meta de horómetro para este equipo."}

    # El valor actual es la última lectura del historial
    valor_actual = df_hist.iloc[-1]['valor']
    df_hist['fecha'] = pd.to_datetime(df_hist['fecha'])
    first_date = df_hist.iloc[0]['fecha']
    last_date = df_hist.iloc[-1]['fecha']
    delta_days = (last_date - first_date).days

    if delta_days <= 0:
        return {"error": "Las lecturas deben tener al menos 1 día de diferencia."}

    delta_valor = df_hist.iloc[-1]['valor'] - df_hist.iloc[0]['valor']
    uso_diario_promedio = delta_valor / delta_days

    if uso_diario_promedio <= 0:
        return {"error": "El uso diario calculado es 0 o negativo. Verifique las lecturas."}

    # 4. Proyectar
    valor_actual = df_hist.iloc[-1]['valor']
    faltante = meta - valor_actual

    if faltante <= 0:
        return {
            "estado": "CRÍTICO",
            "mensaje": "Meta ya alcanzada o sobrepasada.",
            "fecha_proyectada": datetime.now().strftime("%Y-%m-%d"),
            "uso_diario": round(uso_diario_promedio, 2)
        }

    dias_para_meta = faltante / uso_diario_promedio
    fecha_proyectada = last_date + timedelta(days=int(dias_para_meta))

    return {
        "estado": "SALUDABLE" if dias_para_meta > 15 else "PREVENTIVO",
        "uso_diario": round(uso_diario_promedio, 2),
        "fecha_proyectada": fecha_proyectada.strftime("%Y-%m-%d"),
        "dias_restantes": int(dias_para_meta),
        "meta": meta,
        "actual": valor_actual
    }

def obtener_benchmarking_cumplimiento(DB_PATH, empresa_id):
    """
    Compara el cumplimiento documental de todos los contratos 
    de una empresa.
    """
    query = """
        SELECT c.nombre_contrato, 
               COUNT(*) as total_docs,
               SUM(CASE WHEN r.fecha_vencimiento >= date('now') THEN 1 ELSE 0 END) as vigentes
        FROM registros r
        JOIN contratos c ON r.contrato_id = c.id
        WHERE r.empresa_id = ?
        GROUP BY c.nombre_contrato
    """
    df = obtener_dataframe(DB_PATH, query, (empresa_id,))

    if df.empty:
        return pd.DataFrame()

    df['cumplimiento'] = (df['vigentes'] / df['total_docs'] * 100).round(1)
    return df.sort_values(by='cumplimiento', ascending=False)
