"""
==========================================
📈 FORECAST ENGINE — v2.0 MEJORADO
==========================================
Predictor de vencimientos y riesgos.

CARACTERÍSTICAS v2.0:
✅ Pronósticos de vencimientos
✅ Análisis de patrones de riesgo
✅ Índice de riesgo inteligente
✅ Reportes predictivos
✅ Alertas proactivas
✅ Histórico de pronósticos
✅ Tendencias por categoría
"""
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass

import pandas as pd
from dateutil.relativedelta import relativedelta

from src.infrastructure.database import (
    ejecutar_query,
    guardar_config,
    obtener_config,
    obtener_dataframe,
    obtener_conexion,
)

logger = logging.getLogger(__name__)


# ============ DATA MODELS ============

@dataclass
class PronosticoVencimiento:
    """Pronóstico de vencimientos para un mes"""
    id: str
    mes_pronostico: str
    cantidad_vencimientos: int
    indice_riesgo: float  # 0-100
    categorias_afectadas: Dict[str, int]
    narrativa: str
    fecha_generacion: str


@dataclass
class AnalisisRiesgoCritico:
    """Análisis de riesgos críticos inmediatos"""
    id: str
    documentos_bloqueados: int
    documentos_en_alerta: int
    mes_critico: str
    categorias_criticas: List[str]
    recomendaciones: List[str]


class ForecastEngine:
    """Motor predictivo de vencimientos y riesgos"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path
        self._crear_tablas()
        logger.info("ForecastEngine inicializado")
    
    def _crear_tablas(self) -> None:
        """Crea tablas para pronósticos"""
        if not self.db_path:
            return
        
        tables = [
            """
            CREATE TABLE IF NOT EXISTS pronosticos_vencimientos (
                id TEXT PRIMARY KEY,
                empresa_id TEXT,
                contrato_id TEXT,
                mes_pronostico TEXT,
                cantidad_vencimientos INTEGER,
                indice_riesgo REAL,
                categorias_afectadas TEXT,
                narrativa TEXT,
                fecha_generacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS analisis_riesgos_criticos (
                id TEXT PRIMARY KEY,
                empresa_id TEXT,
                documentos_bloqueados INTEGER,
                documentos_en_alerta INTEGER,
                mes_critico TEXT,
                categorias_criticas TEXT,
                recomendaciones TEXT,
                fecha_analisis TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        ]
        
        try:
            conexion = obtener_conexion(self.db_path)
            for query in tables:
                conexion.execute(query)
            conexion.commit()
            conexion.close()
            logger.debug("Tablas de forecast creadas")
        except Exception as e:
            logger.error(f"Error creando tablas: {e}")


def _meses_futuros(n: int = 4) -> list:
    """Genera una lista de N meses futuros como strings 'YYYY-MM'."""
    hoy = datetime.now()
    return [(hoy + relativedelta(months=i)).strftime('%Y-%m') for i in range(1, n + 1)]


def generar_forecast_vencimientos(DB_PATH: str, empresa_id: int = 0, contrato_id: int = 0, meses: int = 4) -> dict:
    """
    Analiza la BD y genera un forecast de vencimientos por mes.

    Returns:
        dict con: meses[], conteos[], indice_riesgo[], narrativa (str), mes_critico (str)
    """
    query = """
        SELECT identificador, nombre, categoria, fecha_vencimiento, empresa_id, contrato_id
        FROM registros
        WHERE fecha_vencimiento IS NOT NULL AND fecha_vencimiento != ''
    """
    params = []
    if empresa_id > 0:
        query += " AND empresa_id = ?"
        params.append(empresa_id)
    if contrato_id > 0:
        query += " AND contrato_id = ?"
        params.append(contrato_id)

    df = obtener_dataframe(DB_PATH, query, tuple(params))

    resultado_vacio = {
        "meses": [], "conteos": [], "indice_riesgo": [],
        "narrativa": "No hay suficientes datos de vencimiento para generar un forecast.",
        "mes_critico": None, "detalle_categorias": {},
        "total_documentos": 0, "documentos_en_riesgo": 0
    }

    if df.empty:
        return resultado_vacio

    df['fecha_vencimiento'] = pd.to_datetime(df['fecha_vencimiento'], errors='coerce')
    df = df.dropna(subset=['fecha_vencimiento'])

    if df.empty:
        return resultado_vacio

    hoy = pd.Timestamp(datetime.now().date())
    meses_futuros = _meses_futuros(meses)

    conteos = []
    indices = []
    detalle_categorias = {}
    total_docs = len(df)

    for mes_str in meses_futuros:
        df_mes = df[df['fecha_vencimiento'].dt.strftime('%Y-%m') == mes_str]
        n = len(df_mes)
        indice = round((n / total_docs * 100), 1) if total_docs > 0 else 0
        conteos.append(n)
        indices.append(indice)

        # Desglose por categoría para ese mes
        if n > 0:
            cats = df_mes.groupby('categoria').size().to_dict()
            detalle_categorias[mes_str] = cats

    # ── Narrativa gerencial ──────────────────
    max_conteo = max(conteos) if conteos else 0
    mes_critico = meses_futuros[conteos.index(max_conteo)] if conteos else None

    # Documentos vencidos actualmente (bloqueados)
    docs_bloqueados = len(df[df['fecha_vencimiento'] < hoy])
    # Documentos en alerta (próximos 30 días)
    limite_alerta = hoy + pd.Timedelta(days=30)
    docs_alerta = len(df[(df['fecha_vencimiento'] >= hoy) & (df['fecha_vencimiento'] <= limite_alerta)])

    narrativa_partes = []

    if docs_bloqueados > 0:
        narrativa_partes.append(
            f"🚨 **Situación Actual Crítica**: Existen **{docs_bloqueados} documentos vencidos** que representan un bloqueo operativo inmediato."
        )

    if docs_alerta > 0:
        narrativa_partes.append(
            f"⚠️ **Alerta Próxima (30 días)**: **{docs_alerta} documentos** vencen dentro del próximo mes. Inicia los procesos de renovación hoy."
        )

    if mes_critico and max_conteo > 0:
        try:
            mes_f = datetime.strptime(mes_critico, '%Y-%m').strftime('%B %Y').capitalize()
        except Exception:
            mes_f = mes_critico

        nivel = "🔴 MÁXIMO" if indices[conteos.index(max_conteo)] > 30 else ("🟡 MODERADO" if indices[conteos.index(max_conteo)] > 15 else "🟢 BAJO")
        narrativa_partes.append(
            f"📈 **Mes más crítico**: **{mes_f}** concentra **{max_conteo} vencimientos** ({indices[conteos.index(max_conteo)]}% del total). Riesgo: {nivel}."
        )

        if mes_critico in detalle_categorias:
            cats_str = ", ".join([f"{k}: {v}" for k, v in detalle_categorias[mes_critico].items()])
            narrativa_partes.append(f"   _Desglose: {cats_str}_")

    if not narrativa_partes:
        narrativa_partes.append("✅ El calendario de vencimientos está distribuido con bajo riesgo para los próximos meses.")

    narrativa_partes.append("\n_Análisis generado por Ultron Forecast Engine en tiempo real._")

    # Cachear en DB
    try:
        cache_data = json.dumps({
            "meses": meses_futuros,
            "conteos": conteos,
            "indice_riesgo": indices,
            "mes_critico": mes_critico,
            "timestamp": datetime.now().isoformat()
        })
        ejecutar_query(DB_PATH, """
            INSERT INTO ultron_forecast_cache (empresa_id, contrato_id, datos_json)
            VALUES (?, ?, ?)
        """, (empresa_id, contrato_id, cache_data), commit=True)
    except Exception:
        pass  # No interrumpir si el cache falla

    return {
        "meses": meses_futuros,
        "conteos": conteos,
        "indice_riesgo": indices,
        "narrativa": "\n\n".join(narrativa_partes),
        "mes_critico": mes_critico,
        "detalle_categorias": detalle_categorias,
        "total_documentos": total_docs,
        "documentos_en_riesgo": docs_bloqueados + docs_alerta
    }


def obtener_top_criticos(DB_PATH: str, empresa_id: int = 0, contrato_id: int = 0, top_n: int = 5) -> pd.DataFrame:
    """Retorna los N documentos más urgentes (vencidos o próximos a vencer)."""
    query = """
        SELECT identificador, nombre, tipo_doc, categoria, fecha_vencimiento
        FROM registros
        WHERE fecha_vencimiento IS NOT NULL AND fecha_vencimiento != ''
    """
    params = []
    if empresa_id > 0:
        query += " AND empresa_id = ?"
        params.append(empresa_id)
    if contrato_id > 0:
        query += " AND contrato_id = ?"
        params.append(contrato_id)
    query += " ORDER BY fecha_vencimiento ASC LIMIT ?"
    params.append(top_n)

    return obtener_dataframe(DB_PATH, query, tuple(params))
