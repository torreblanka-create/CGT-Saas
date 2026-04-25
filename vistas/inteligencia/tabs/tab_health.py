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


def render_tab_health(DB_PATH, filtros):
    with st.status("Auditando integridad...", expanded=True) as status:
        audit = run_full_system_audit(DB_PATH, os.getcwd(), status_callback=status.write)
        status.update(label="Auditoría Finalizada", state="complete", expanded=False)
    st.metric("Puntaje de Integridad", f"{audit['score']}%")
    col_db, col_fs = st.columns(2)
    with col_db:
        st.markdown("#### 💾 Base de Datos")
        if audit['db']['status'] == "OK": st.success("Estructura Íntegra")
        else:
            st.error(f"Inconsistencias: {len(audit['db']['missing_columns'])}")
            if st.button("🛠️ Aplicar Autocorrección", use_container_width=True): run_auto_patch(DB_PATH, audit['db']['missing_columns']); st.rerun()
    with col_fs:
        st.markdown("#### 📁 Estructura de Archivos")
        if audit['files']['status'] == "OK": st.success("Directorios Correctos")
        else:
            st.warning(f"Faltan {len(audit['files']['missing_dirs'])} carpetas")
            if st.button("📂 Restaurar Carpetas", use_container_width=True):
                for d in audit['files']['missing_dirs']: os.makedirs(os.path.join(os.getcwd(), d), exist_ok=True)
                st.rerun()


    # ── TAB 4: RESILIENCIA (BACKUPS) ──
