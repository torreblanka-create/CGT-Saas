import json
import os
import time
from datetime import datetime

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from intelligence.agents.action_planner_engine import (
    crear_plan_desde_alerta,
    obtener_resumen_planes_activos,
)
from src.infrastructure.archivos import (
    organizar_carpetas_sistema,
    sincronizar_directorios_desde_excel,
)
from intelligence.agents.backup_engine import crear_backup, obtener_listado_respaldos, restaurar_db
from intelligence.agents.coaching_engine import generar_coaching_personalizado
from intelligence.agents.code_quality_engine import (
    aplicar_fixes_seguros,
    generar_narrativa_reporte,
    generar_reporte_calidad,
)
from intelligence.agents.context7_engine import descargar_todas_normativas, obtener_estado_biblioteca
from intelligence.agents.data_audit_engine import escanear_anomalias, generar_recomendaciones_data
from src.infrastructure.database import (
    ejecutar_query,
    guardar_config,
    normalizar_texto,
    obtener_config,
    obtener_dataframe,
    registrar_log,
)
from core.diagnostics import run_auto_patch, run_full_system_audit
from core.excel_master import (
    exportar_maestro_a_excel,
    obtener_contratos_por_empresa,
    obtener_listas_unicas,
    sincronizar_maestro_desde_excel,
)
from intelligence.agents.forecast_engine import generar_forecast_vencimientos, obtener_top_criticos
from intelligence.agents.intelligence_engine import ULTRON_CORE_DIRECTIVE, ask_ultron
from intelligence.agents.mock_audit_engine import calificar_resumen_simulacro, generar_examen_simulacro
from core.normativa_watcher import (
    obtener_estado_normativas,
    verificar_actualizaciones_normativas,
)
from core.notification_agent import generar_briefing_diario
from intelligence.agents.ocr_engine import obtener_historial_ocr, validar_documento_ocr
from intelligence.agents.prediction_engine import (
    obtener_benchmarking_cumplimiento,
    proyectar_mantenimiento_maquinaria,
)
from src.services.report_generator import generar_briefing_ejecutivo
from intelligence.agents.sequential_thinking_engine import analizar_consulta_con_thinking
from intelligence.agents.vision_engine import analizar_epp_en_imagen, generar_veredicto_vision
from intelligence.agents.voice_engine import sintetizar_voz_ultron


def render_tab_diag(DB_PATH, filtros):
    f_emp_id = filtros.get('empresa_id', 0)
    query = f"SELECT id, categoria, fecha_vencimiento FROM registros"
    if f_emp_id > 0: query += f" WHERE empresa_id = {f_emp_id}"
    df = obtener_dataframe(DB_PATH, query)
    if df.empty: st.info("No hay datos operativos suficientes.")
    else:
        hoy = pd.to_datetime(datetime.now().date())
        df['fecha_vencimiento'] = pd.to_datetime(df['fecha_vencimiento'], errors='coerce')
        def get_st(v):
            if pd.isna(v): return "Operativo"
            d = (v - hoy).days
            return "Bloqueado" if d < 0 else ("Alerta" if d <= 15 else "Operativo")
        df['Estado'] = df['fecha_vencimiento'].apply(get_st)
        c1, c2 = st.columns(2)
        with c1: st.plotly_chart(px.pie(df, names='Estado', hole=0.5, color='Estado', color_discrete_map={"Operativo":"#10B981","Alerta":"#F59E0B","Bloqueado":"#EF4444"}), use_container_width=True)
        with c2: st.plotly_chart(px.bar(df.groupby(['categoria', 'Estado']).size().reset_index(name='c'), x='categoria', y='c', color='Estado', barmode='stack', color_discrete_map={"Operativo":"#10B981","Alerta":"#F59E0B","Bloqueado":"#EF4444"}), use_container_width=True)

    # ── TAB 3: VALIDACIÓN OCR ──
