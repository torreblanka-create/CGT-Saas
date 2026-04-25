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

# Intentar importar módulos opcionales
try:
    from intelligence.agents.vision_engine import analizar_epp_en_imagen, generar_veredicto_vision
except (ImportError, ModuleNotFoundError):
    analizar_epp_en_imagen = None
    generar_veredicto_vision = None

try:
    from intelligence.agents.voice_engine import sintetizar_voz_ultron
except (ImportError, ModuleNotFoundError):
    sintetizar_voz_ultron = None



def render_tab_chat(DB_PATH, filtros):
    # Inicialización persistente de la API Key (Sincronizada con ULLTRONE_BRAIN_CONFIG)
    if 'gemini_api_key' not in st.session_state or not st.session_state['gemini_api_key']:
        brain_cfg = obtener_config(DB_PATH, "ULLTRONE_BRAIN_CONFIG", {})
        st.session_state['gemini_api_key'] = brain_cfg.get("api_key", "")

    col_c_t, col_c_api = st.columns([3, 1])
    with col_c_t:
        st.caption(f"🎯 **Directiva:** {ULTRON_CORE_DIRECTIVE[:60]}...")
    with col_c_api:
        with st.popover("🧠 Cerebro", use_container_width=True):
            a_key = st.text_input("Gemini API Key:", type="password", value=st.session_state['gemini_api_key'])
            if st.button("💾 Guardar"):
                st.session_state['gemini_api_key'] = a_key
                brain_cfg = obtener_config(DB_PATH, "ULLTRONE_BRAIN_CONFIG", {})
                brain_cfg["api_key"] = a_key
                guardar_config(DB_PATH, "ULLTRONE_BRAIN_CONFIG", brain_cfg)
                st.success("Guardado.")
                st.rerun()

    if "ultron_messages" not in st.session_state:
        query = "SELECT role, content FROM chat_ultron_history ORDER BY fecha ASC LIMIT 50"
        df_hist = obtener_dataframe(DB_PATH, query)
        st.session_state.ultron_messages = df_hist.to_dict('records') if not df_hist.empty else [{"role": "assistant", "content": "Conexión establecida. Ull-Trone en línea."}]

    chat_container = st.container(height=750)
    with chat_container:
        for i, msg in enumerate(st.session_state.ultron_messages):
            with st.chat_message(msg["role"]):
                st.write(msg["content"])
                if msg["role"] == "assistant":
                    if st.button("🔊 Voz", key=f"voice_{i}"):
                        audio_path = sintetizar_voz_ultron(msg["content"])
                        if audio_path: st.audio(audio_path, format="audio/mp3", autoplay=True)

    if prompt := st.chat_input("Escribe tu instrucción o comando..."):
        st.session_state.ultron_messages.append({"role": "user", "content": prompt})
        ejecutar_query(DB_PATH, "INSERT INTO chat_ultron_history (usuario, role, content) VALUES (?, ?, ?)", (st.session_state.user_login, "user", prompt), commit=True)
        with chat_container:
            with st.chat_message("user"): st.write(prompt)
            with st.chat_message("assistant"):
                with st.status("Ull-Trone analizando...", expanded=False) as status:
                    response = ask_ultron(DB_PATH, prompt, st.session_state.user_login, api_key=st.session_state.get('gemini_api_key', ''))
                    status.update(label="Procesado", state="complete")
                st.write(response["content"])
                if response.get("type") == "action_request":
                    if st.button("🚀 APLICAR PARCHES", use_container_width=True):
                        with st.status("Reparando...", expanded=True) as s:
                            fixes = run_auto_patch(DB_PATH, response["details"], status_callback=s.write)
                            s.update(label="Sincronizado", state="complete")
                        st.success(f"Sistema parchado. ({fixes} cambios)")
                        st.rerun()

    # ── TAB 2: DIAGNÓSTICO (KPIs) ──
