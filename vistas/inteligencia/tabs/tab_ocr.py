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


def render_tab_ocr(DB_PATH, filtros):
    st.markdown("### 🔬 Ojo Digital — Validación de Contenido de Documentos")
    st.markdown("Sube un PDF y selecciona el registro al que debe corresponder. Ultron verificará su autenticidad.")

    col_id, col_nom = st.columns(2)
    with col_id:
        id_verificar = st.text_input("Identificador esperado (RUT/Patente/Código):", placeholder="ej: 12.345.678-9")
    with col_nom:
        nombre_verificar = st.text_input("Nombre esperado del titular:", placeholder="ej: Juan Pérez González")

    pdf_ocr = st.file_uploader("📄 Subir PDF a verificar", type=["pdf"], key="ocr_uploader")

    if st.button("🔬 Ejecutar Validación OCR", use_container_width=True, type="primary", disabled=not pdf_ocr):
        if pdf_ocr:
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                tmp.write(pdf_ocr.read())
                tmp_path = tmp.name

            with st.spinner("Ultron escaneando el documento..."):
                resultado = validar_documento_ocr(tmp_path, id_verificar, nombre_verificar)

            try:
                import os as _os
                _os.unlink(tmp_path)
            except Exception:
                pass

            confianza = resultado['confianza']
            es_valido = resultado['valido']

            col_res1, col_res2 = st.columns([1, 2])
            with col_res1:
                color_gauge = "#10B981" if confianza >= 70 else ("#F59E0B" if confianza >= 40 else "#EF4444")
                fig_gauge = go.Figure(go.Indicator(
                    mode="gauge+number",
                    value=confianza,
                    title={'text': "Confianza OCR"},
                    gauge={
                        'axis': {'range': [0, 100]},
                        'bar': {'color': color_gauge},
                        'steps': [
                            {'range': [0, 40], 'color': '#EF444430'},
                            {'range': [40, 70], 'color': '#F59E0B30'},
                            {'range': [70, 100], 'color': '#10B98130'}
                        ]
                    }
                ))
                fig_gauge.update_layout(height=200, margin=dict(t=30, b=0, l=10, r=10))
                st.plotly_chart(fig_gauge, use_container_width=True)

            with col_res2:
                if es_valido:
                    st.success(f"✅ **DOCUMENTO VÁLIDO** — {resultado['razon']}")
                else:
                    st.error(f"❌ **DOCUMENTO INVÁLIDO** — {resultado['razon']}")

                st.markdown("**Evidencias del análisis:**")
                for ev in resultado.get('evidencias', []):
                    st.write(ev)
                if resultado.get('chars_extraidos'):
                    st.caption(f"Texto extraído: {resultado['chars_extraidos']:,} caracteres")

    # Historial OCR
    st.divider()
    st.markdown("#### 📋 Historial de Validaciones")
    df_hist_ocr = obtener_historial_ocr(DB_PATH, filtros.get('empresa_id', 0))
    if df_hist_ocr.empty:
        st.info("No hay validaciones previas registradas.")
    else:
        df_hist_ocr['es_valido'] = df_hist_ocr['es_valido'].map({1: '✅ Válido', 0: '❌ Inválido'})
        st.dataframe(df_hist_ocr[['fecha', 'identificador', 'confianza', 'es_valido', 'razon']],
                    use_container_width=True, hide_index=True)

    # ── TAB 4: FORECAST & REPORTE PDF ──
