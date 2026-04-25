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


def render_tab_forecast(DB_PATH, filtros):
    f_emp_id = filtros.get('empresa_id', 0)
    f_con_id = filtros.get('contrato_id', 0)

    st.markdown("### 📈 Forecast Predictivo de Vencimientos")

    col_f_btn, col_f_meses = st.columns([1, 1])
    with col_f_meses:
        n_meses = st.slider("Meses a proyectar:", 2, 6, 4)
    with col_f_btn:
        st.markdown("<br>", unsafe_allow_html=True)
        run_forecast = st.button("🔄 Actualizar Análisis", use_container_width=True)

    with st.spinner("Ull-Trone calculando proyecciones..."):
        forecast_data = generar_forecast_vencimientos(DB_PATH, f_emp_id, f_con_id, meses=n_meses)

    # Narrativa gerencial
    st.markdown(f"""
        <div class="cc-narrative">
            {forecast_data['narrativa'].replace(chr(10), '<br>')}
        </div>
    """, unsafe_allow_html=True)

    # Gráfico de barras del forecast
    if forecast_data['meses']:
        try:
            from datetime import datetime as dt
            meses_label = [dt.strptime(m, '%Y-%m').strftime('%B %Y').capitalize() for m in forecast_data['meses']]
        except Exception:
            meses_label = forecast_data['meses']

        df_forecast_chart = pd.DataFrame({
            'Mes': meses_label,
            'Vencimientos': forecast_data['conteos'],
            'Índice de Riesgo (%)': forecast_data['indice_riesgo']
        })

        colors_bars = []
        for idx in forecast_data['indice_riesgo']:
            colors_bars.append('#EF4444' if idx > 30 else ('#F59E0B' if idx > 15 else '#10B981'))

        fig_fc = go.Figure()
        fig_fc.add_trace(go.Bar(
            x=df_forecast_chart['Mes'],
            y=df_forecast_chart['Vencimientos'],
            marker_color=colors_bars,
            text=df_forecast_chart['Vencimientos'],
            textposition='outside',
            name='Vencimientos'
        ))
        fig_fc.update_layout(
            template='plotly_dark',
            title='Proyección de Vencimientos por Mes',
            yaxis_title='N° Documentos',
            showlegend=False,
            margin=dict(t=40, b=20)
        )
        st.plotly_chart(fig_fc, use_container_width=True)

    # Top críticos
    st.markdown("#### 🚨 Top 5 Documentos Más Urgentes")
    df_top = obtener_top_criticos(DB_PATH, f_emp_id, f_con_id, top_n=5)
    if not df_top.empty:
        df_top['fecha_vencimiento'] = pd.to_datetime(df_top['fecha_vencimiento'], errors='coerce')
        df_top['Días'] = (df_top['fecha_vencimiento'] - pd.Timestamp(datetime.now().date())).dt.days
        st.dataframe(
            df_top[['identificador', 'nombre', 'tipo_doc', 'categoria', 'fecha_vencimiento', 'Días']],
            use_container_width=True, hide_index=True
        )
    else:
        st.success("✅ No hay documentos con vencimientos registrados próximos.")

    # Botón PDF
    st.divider()
    st.markdown("#### 📄 Generar Briefing Ejecutivo PDF")
    col_pdf1, col_pdf2 = st.columns([2, 1])
    with col_pdf1:
        emp_nombre_pdf = st.text_input("Empresa (para el PDF):", value="CGT.pro", key="pdf_emp")
        con_nombre_pdf = st.text_input("Contrato (opcional):", key="pdf_con")
    with col_pdf2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        if st.button("📄 Generar PDF", use_container_width=True, type="primary"):
            with st.spinner("Ull-Trone generando el briefing..."):
                pdf_bytes = generar_briefing_ejecutivo(DB_PATH, f_emp_id, f_con_id, emp_nombre_pdf, con_nombre_pdf)
            if pdf_bytes:
                st.session_state['_briefing_pdf'] = pdf_bytes
                st.success("✅ PDF generado. Usa el botón de descarga abajo.")
            else:
                st.error("❌ No se pudo generar el PDF. Instala `fpdf2` (`pip install fpdf2`) o `reportlab`.")

    if st.session_state.get('_briefing_pdf'):
        nombre_pdf = f"Briefing_UllTrone_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
        st.download_button(
            "📥 Descargar Briefing PDF",
            data=st.session_state['_briefing_pdf'],
            file_name=nombre_pdf,
            mime="application/pdf",
            use_container_width=True
        )

    # ── TAB 5: VIGILANCIA NORMATIVA ──
