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


def render_tab_analytics(DB_PATH, filtros):
    st.markdown("### 📊 Inteligencia de Negocio y Predicción")

    tab_bench, tab_pred, tab_vision = st.tabs(["🚀 Benchmarking", "📈 Proyecciones", "👁️ Visión EPP"])

    with tab_bench:
        st.markdown("#### 🏢 Cumplimiento por Contrato")
        df_bench = obtener_benchmarking_cumplimiento(DB_PATH, filtros.get('empresa_id', 0))
        if not df_bench.empty:
            fig_bench = px.bar(df_bench, x='cumplimiento', y='nombre_contrato',
                              orientation='h', text='cumplimiento',
                              color='cumplimiento', color_continuous_scale='RdYlGn',
                              range_x=[0, 100], labels={'cumplimiento': '% Cumplimiento', 'nombre_contrato': 'Contrato'})
            st.plotly_chart(fig_bench, use_container_width=True)
            st.table(df_bench)
        else:
            st.info("ℹ️ No hay datos suficientes para generar comparativas.")

    with tab_pred:
        st.markdown("#### 🚜 Proyección de Mantenimiento (Horómetros)")

        # Formulario de Ingreso Rápido
        with st.expander("📥 Ingresar Nueva Lectura de Horómetro"):
            col_h1, col_h2, col_h3 = st.columns(3)
            with col_h1: h_id = st.text_input("Identificador (Patente/RUT)", placeholder="EJ: FX-JW-22")
            with col_h2: h_val = st.number_input("Lectura Actual (hrs)", min_value=0.0)
            with col_h3: h_fecha = st.date_input("Fecha Lectura")

            if st.button("💾 Guardar Lectura", use_container_width=True):
                if h_id and h_val > 0:
                    ejecutar_query(DB_PATH,
                        "INSERT INTO ultron_horometros_history (identificador, fecha, valor, empresa_id, contrato_id) VALUES (?, ?, ?, ?, ?)",
                        (h_id, h_fecha.strftime("%Y-%m-%d"), h_val, filtros.get('empresa_id', 0), filtros.get('contrato_id', 0)),
                        commit=True
                    )
                    st.success(f"Lectura de {h_id} registrada.")
                    st.rerun()

        # Buscador de Proyección
        st.divider()
        target_h = st.text_input("🔍 Consultar Proyección para Equipo:", placeholder="Ingrese patente o identificador...")
        if target_h:
            pred = proyectar_mantenimiento_maquinaria(DB_PATH, target_h)
            if "error" in pred:
                st.warning(pred['error'])
            else:
                col_p1, col_p2, col_p3 = st.columns(3)
                col_p1.metric("Uso Diario", f"{pred['uso_diario']} hrs")
                col_p2.metric("Días Restantes", pred['dias_restantes'])
                col_p3.metric("Fecha Estimada", pred['fecha_proyectada'])

                st.progress(min(1.0, pred['actual'] / pred['meta']),
                           text=f"Progreso hacia Meta ({pred['actual']} / {pred['meta']} hrs)")

    with tab_vision:
        st.markdown("#### 👁️ Auditoría por Visión Computacional")
        st.caption("Ull-Trone analiza fotos de evidencias buscando Casco y Chaleco Reflectante.")

        archivo_vision = st.file_uploader("🖼️ Subir imagen para análisis de seguridad:", type=["jpg", "png", "jpeg"])
        if archivo_vision:
            # Guardar temporalmente para análisis
            temp_path = os.path.join("temp_vision.jpg")
            with open(temp_path, "wb") as f:
                f.write(archivo_vision.getbuffer())

            with st.status("Ull-Trone analizando píxeles...", expanded=True) as s:
                res_v = analizar_epp_en_imagen(temp_path)
                s.write(generar_veredicto_vision(res_v))
                if "detalles" in res_v:
                    st.json(res_v['detalles'])
                s.update(label="Análisis Completo", state="complete")

            st.image(temp_path, caption="Imagen Analizada")
            os.remove(temp_path)

    # ── TAB 7: SALUD DEL SISTEMA ──
