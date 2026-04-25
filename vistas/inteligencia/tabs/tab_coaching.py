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


def render_tab_coaching(DB_PATH, filtros):
    st.markdown("### 🎓 Entrenador de Seguridad Personalizado")
    st.markdown("Ull-Trone analiza tu historial de fallas y genera consejos de seguridad basados en las normativas aplicables.")

    col_c1, col_c2 = st.columns([1, 2])
    with col_c1:
        n_consejos = st.slider("N° de consejos:", 2, 5, 3)
        generar_coach = st.button("🎓 Generar Coaching", use_container_width=True, type="primary")

    with col_c2:
        st.info("💡 Ull-Trone revisa los registros vencidos o en alerta de tu empresa y selecciona los Tips más relevantes de su base de conocimiento. "
                "Con API Key de Gemini, los consejos son generados dinámicamente.")

    if generar_coach or 'ultron_coaching_result' not in st.session_state:
        with st.spinner("Ull-Trone analizando tu historial..."):
            coaching_result = generar_coaching_personalizado(
                DB_PATH,
                empresa_id=filtros.get('empresa_id', 0),
                contrato_id=filtros.get('contrato_id', 0),
                api_key=st.session_state.get('gemini_api_key', ''),
                n_consejos=n_consejos
            )
            st.session_state['ultron_coaching_result'] = coaching_result
    else:
        coaching_result = st.session_state.get('ultron_coaching_result', {})

    if coaching_result:
        # Contexto
        st.markdown(f"""
            <div style='background:rgba(0,188,212,0.08); border-left:4px solid #00BCD4;
                        padding:12px; border-radius:8px; margin-bottom:15px;'>
                {coaching_result.get('contexto', '')}
            </div>
        """, unsafe_allow_html=True)

        # Fallas detectadas
        if coaching_result.get('fallas_detectadas'):
            with st.expander("📊 Análisis de Fallas Detectadas"):
                df_fallas = pd.DataFrame(
                    list(coaching_result['fallas_detectadas'].items()),
                    columns=['Categoría', 'N° Documentos con Problemas']
                )
                fig_fallas = px.bar(df_fallas, x='N° Documentos con Problemas', y='Categoría',
                                   orientation='h', color='N° Documentos con Problemas',
                                   color_continuous_scale=['#10B981', '#F59E0B', '#EF4444'])
                st.plotly_chart(fig_fallas, use_container_width=True)

        # Si hay respuesta IA
        if coaching_result.get('respuesta_ia'):
            st.markdown("#### 🧠 Análisis Generado por IA (Gemini)")
            st.markdown(coaching_result['respuesta_ia'])
        else:
            # Consejos estáticos
            st.markdown("#### 💡 Consejos Personalizados")
            for i, consejo in enumerate(coaching_result.get('consejos', []), 1):
                nivel = consejo['nivel']
                nivel_color = "#EF4444" if nivel == "Crítico" else ("#F59E0B" if nivel == "Preventivo" else "#3B82F6")
                nivel_emoji = "🔴" if nivel == "Crítico" else ("🟡" if nivel == "Preventivo" else "🔵")

                st.markdown(f"""
                    <div style='background:rgba(30,41,59,0.8); border:1px solid {nivel_color}40;
                                border-left:4px solid {nivel_color}; padding:15px; 
                                border-radius:8px; margin-bottom:10px;'>
                        <div style='display:flex; justify-content:space-between; margin-bottom:8px;'>
                            <span style='font-weight:bold; color:#E2E8F0;'>{nivel_emoji} Consejo #{i}</span>
                            <span style='color:{nivel_color}; font-size:0.8rem; font-weight:bold;'>{nivel}</span>
                        </div>
                        <p style='color:#CBD5E1; margin:0 0 8px;'>{consejo['tip']}</p>
                        <span style='color:#64748B; font-size:0.75rem;'>📋 Norma: {consejo['norma']}</span>
                    </div>
                """, unsafe_allow_html=True)

        st.caption("_Coaching generado por Ultron en base a historial operacional real. No reemplaza la asesoría de un experto en seguridad certificado._")

    # ── TAB 6.1: AUDITORÍA & SIMULACRO (Ultron v3.0) ──
