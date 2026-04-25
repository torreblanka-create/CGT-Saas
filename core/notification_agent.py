"""
===========================================
🤖 ULTRON NOTIFICATION AGENT — v1.0
===========================================
Agente autónomo que consolida el estado del
sistema y genera briefings diarios para la
gerencia.
"""
from datetime import datetime, timedelta

import pandas as pd

from intelligence.agents.action_planner_engine import obtener_resumen_planes_activos
from intelligence.agents.data_audit_engine import escanear_anomalias
from src.infrastructure.database import obtener_dataframe


def generar_briefing_diario(DB_PATH, empresa_id=0):
    """
    Recopila datos de todos los motores para un resumen ejecutivo.
    """
    # 1. Resumen de Alertas Pendientes
    q_alertas = "SELECT tipo, count(*) as total FROM notificaciones_ultron WHERE estado = 'No Leída'"
    if empresa_id > 0: q_alertas += f" AND empresa_id = {empresa_id}"
    q_alertas += " GROUP BY tipo"
    df_alertas = obtener_dataframe(DB_PATH, q_alertas)

    # 2. Resumen de Planes de Gestión
    df_planes = obtener_resumen_planes_activos(DB_PATH, empresa_id)

    # 3. Anomalías de Datos
    res_data = escanear_anomalias(DB_PATH, empresa_id)

    # 4. Vencimientos de Mañana
    manana = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
    q_vto = "SELECT count(*) FROM registros WHERE fecha_vencimiento = ?"
    if empresa_id > 0: q_vto += f" AND empresa_id = {empresa_id}"
    df_vto = obtener_dataframe(DB_PATH, q_vto, (manana,))
    vtos_manana = df_vto.iloc[0,0] if not df_vto.empty else 0

    # Construcción de Narrativa
    briefing = f"📅 **Ultron Daily Briefing — {datetime.now().strftime('%d/%m/%Y')}**\n\n"

    if not df_alertas.empty:
        briefing += "🔥 **Alertas de Seguridad**: " + ", ".join([f"{row['tipo']}: {row['total']}" for _, row in df_alertas.iterrows()]) + ".\n"
    else:
        briefing += "✅ No hay alertas críticas nuevas.\n"

    briefing += f"🚜 **Vencimientos Mañana**: {vtos_manana} documentos caducarán en las próximas 24 horas.\n"
    briefing += f"🔍 **Calidad de Datos**: Se detectan {res_data['total_anomalias']} inconsistencias estructurales.\n"

    if not df_planes.empty:
        briefing += "📝 **Gestión**: " + ", ".join([f"{row['estado']}: {row['total']}" for _, row in df_planes.iterrows()]) + " planes en curso.\n"

    briefing += "\n---\n_Briefing generado autónomamente por Ultron Agent._"

    return briefing

def detectar_sentimiento_observacion(texto):
    """
    Analiza una cadena de texto buscando patrones de riesgo emocional 
    o urgencia.
    """
    palabras_riesgo = {
        "urgente": 3, "inmediato": 3, "peligro": 3, "grave": 3,
        "cansado": 2, "fatiga": 2, "agotado": 2, "estrés": 2, "estres": 2,
        "enojado": 1, "molesto": 1, "queja": 1
    }

    score = 0
    encontradas = []
    t = texto.lower()

    for palabra, peso in palabras_riesgo.items():
        if palabra in t:
            score += peso
            encontradas.append(palabra)

    return {
        "score": score,
        "nivel": "CRÍTICO" if score >= 3 else "MODERADO" if score > 0 else "NORMAL",
        "hallazgos": encontradas
    }
