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


def render_tab_normativa(DB_PATH, filtros):
    st.markdown("### ⚡ Centinela Normativo — Vigilancia Activa")
    st.markdown("Ull-Trone monitorea las principales normativas chilenas de seguridad laboral y detecta cambios en el contenido oficial.")

    col_n1, col_n2 = st.columns([1, 2])
    with col_n1:
        if st.button("🔄 Ejecutar Verificación Ahora", use_container_width=True, type="primary"):
            with st.status("Conectando con fuentes oficiales...", expanded=True) as s_norm:
                s_norm.write("🌐 Accediendo a portales BCN, SUSESO y Diario Oficial...")
                resultado_norm = verificar_actualizaciones_normativas(DB_PATH)
                s_norm.update(label="✅ Verificación completada", state="complete")

            if resultado_norm['estado'] == 'CAMBIOS_DETECTADOS':
                st.warning(f"⚡ **{resultado_norm['cambios_detectados']} cambio(s) detectado(s)** en normativas monitoreadas. Revisa el Inbox de Ull-Trone.")
            elif resultado_norm['estado'] == 'OFFLINE':
                st.info("📡 Sin conexión a internet. Verificación offline completada.")
            else:
                st.success(f"✅ **Sin cambios** — {resultado_norm['verificadas']} normativas verificadas.")

    with col_n2:
        st.caption(f"Normativas monitoreadas: 6 | Última verificación al cargar esta tab")

    # Tabla de estado
    st.divider()
    normas_list = obtener_estado_normativas(DB_PATH)
    if normas_list:
        for norm_obj in normas_list:
            estado = norm_obj.estado.upper() if norm_obj.estado else "NO_VERIFICADO"
            if estado in ('CAMBIO_DETECTADO', 'CRITICO', 'IMPORTANTE', 'MENOR'):
                icono = "⚡"
                color = "#F59E0B"
                estado_display = "CAMBIO DETECTADO"
            elif estado == 'SIN_CAMBIOS':
                icono = "✅"
                color = "#10B981"
                estado_display = "SIN CAMBIOS"
            else:
                icono = "🔄"
                color = "#8B98B8"
                estado_display = estado

            with st.container(border=True):
                c1, c2, c3 = st.columns([0.1, 0.6, 0.3])
                with c1:
                    st.markdown(f"<h3 style='margin:0'>{icono}</h3>", unsafe_allow_html=True)
                with c2:
                    st.markdown(f"**{norm_obj.nombre}**")
                    st.caption(f"Categoría: {norm_obj.categoria} | Último check: {norm_obj.ultimo_check}")
                with c3:
                    badge_color = color
                    st.markdown(
                        f"<span style='background:{badge_color}20; color:{badge_color}; border:1px solid {badge_color}; "
                        f"padding:3px 10px; border-radius:20px; font-size:0.75rem; font-weight:bold;'>{estado_display}</span>",
                        unsafe_allow_html=True
                    )
                    st.markdown(f"[🔗 Ver fuente]({norm_obj.url})")

    # ── TAB 6: COACHING ──
