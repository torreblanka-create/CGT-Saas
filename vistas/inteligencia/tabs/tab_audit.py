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


def render_tab_audit(DB_PATH, filtros):
    st.markdown("### 🎓 Centro de Entrenamiento y Auditoría")

    col_audit1, col_audit2 = st.columns([1, 1])

    with col_audit1:
        st.markdown("#### 🔍 Auditoría de Calidad de Datos")
        if st.button("🚀 Iniciar Escaneo de Anomalías", use_container_width=True):
            resumen_data = escanear_anomalias(DB_PATH, filtros.get('empresa_id', 0))
            st.markdown(generar_recomendaciones_data(resumen_data))
            if resumen_data['total_anomalias'] > 0:
                with st.expander("📋 Ver detalle de inconsistencias"):
                    st.table(pd.DataFrame(resumen_data['detalles']))
        else:
            st.info("💡 Ejecuta un escaneo para encontrar RUTs inválidos o archivos perdidos.")

    with col_audit2:
        st.markdown("#### 🎭 Simulador de Auditoría (Mock Audit)")
        if st.button("🏁 Comenzar Nuevo Simulacro", use_container_width=True, type="primary"):
            st.session_state.mock_exam = generar_examen_simulacro(DB_PATH, filtros.get('empresa_id', 0))
            st.session_state.mock_answers = {}
            st.session_state.mock_finished = False
            st.rerun()

    if "mock_exam" in st.session_state and not st.session_state.mock_finished:
        st.divider()
        st.markdown("#### 📝 Examen de Preparación en curso")
        for i, p in enumerate(st.session_state.mock_exam):
            st.markdown(f"**Pregunta {i+1}:** {p['texto']}")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ Sí (Correcto)", key=f"ans_y_{i}"):
                    st.session_state.mock_answers[i] = True
            with col2:
                if st.button("❌ No / Pendiente", key=f"ans_n_{i}"):
                    st.session_state.mock_answers[i] = False
            st.markdown("---")

        if len(st.session_state.mock_answers) == len(st.session_state.mock_exam):
            if st.button("📤 Finalizar y Calificar", use_container_width=True):
                st.session_state.mock_finished = True
                st.rerun()

    if st.session_state.get("mock_finished"):
        st.divider()
        score, msg = calificar_resumen_simulacro(st.session_state.mock_answers)
        st.metric("Puntaje Final", f"{score}%")
        st.markdown(msg)
        if st.button("🔄 Reiniciar", use_container_width=True):
            del st.session_state.mock_exam
            st.session_state.mock_finished = False
            st.rerun()

    # ── TAB 6.2: ANALÍTICA AVANZADA (Ultron v3.0) ──
