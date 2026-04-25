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


def render_tab_devtools(DB_PATH, filtros):
    st.markdown("### 🔧 Centro de Desarrollo e Inteligencia Expandida")

    tab_ctx7, tab_quality, tab_thinking = st.tabs([
        "📚 Context7 Legal", "🔍 Calidad de Código", "🧠 Pensamiento Secuencial"
    ])

    # ── CONTEXT7: Biblioteca Legal BCN Chile ──
    with tab_ctx7:
        st.markdown("#### 📚 Biblioteca Legal Chilena (Context7 Engine)")
        st.caption("Descarga e indexa normativas oficiales desde **bcn.cl** para análisis RAG.")

        estado_bib = obtener_estado_biblioteca()
        col_m1, col_m2 = st.columns(2)
        col_m1.metric("Normativas Catalogadas", estado_bib["total_catalogadas"])
        col_m2.metric("Normativas Descargadas", estado_bib["total_descargadas"])

        st.divider()

        # Estado de cada normativa
        for norm in estado_bib["estados"]:
            status_icon = "✅" if norm["descargada"] else "⬜"
            fecha_txt = f"Descargada: {norm['fecha']}" if norm["descargada"] else "No descargada"
            with st.container(border=True):
                col_n1, col_n2, col_n3 = st.columns([0.1, 0.6, 0.3])
                col_n1.markdown(f"### {status_icon}")
                col_n2.markdown(f"**{norm['nombre']}**  \n_{fecha_txt}_")
                with col_n3:
                    if not norm["descargada"]:
                        if st.button(f"⬇️ Descargar", key=f"dl_{norm['id']}", use_container_width=True):
                            from intelligence.agents.context7_engine import descargar_normativa
                            with st.spinner("Conectando con bcn.cl..."):
                                res_dl = descargar_normativa(norm["id"])
                            if res_dl.get("success"):
                                st.success(f"✅ Descargada: {res_dl['nombre']}")
                                st.rerun()
                            else:
                                st.error(res_dl.get("error", "Error desconocido"))
                    else:
                        st.success("Indexada ✓")

        st.divider()
        if st.button("⬇️ Descargar Toda la Biblioteca", use_container_width=True, type="primary"):
            with st.status("Descargando desde bcn.cl...", expanded=True) as s:
                resultados_dl = descargar_todas_normativas(callback=s.write)
                ok = sum(1 for r in resultados_dl if r.get("success"))
                s.update(label=f"✅ {ok}/{len(resultados_dl)} normativas descargadas.", state="complete")
            st.rerun()

    # ── CODE QUALITY: Analizador de Código con Ruff ──
    with tab_quality:
        st.markdown("#### 🔍 Análisis de Calidad de Código (Ruff Engine)")
        st.caption("Análisis profundo del proyecto CGT.pro. **Ningún archivo será modificado.**")

        if st.button("🚀 Generar Reporte de Calidad", use_container_width=True, type="primary"):
            with st.spinner("Ruff escaneando el proyecto..."):
                reporte = generar_reporte_calidad(os.getcwd())
                narrativa = generar_narrativa_reporte(reporte)
            st.session_state["ultimo_reporte_calidad"] = reporte
            st.session_state["ultima_narrativa_calidad"] = narrativa
            st.rerun()

        if "ultima_narrativa_calidad" in st.session_state:
            st.markdown(st.session_state["ultima_narrativa_calidad"])
            reporte = st.session_state["ultimo_reporte_calidad"]

            with st.expander("📋 Ver Detalle Completo por Archivo"):
                det = reporte.get("detalle_por_archivo", {})
                for archivo, issues in list(det.items())[:10]:
                    st.markdown(f"**`{archivo}`** — {len(issues)} issues")
                    for iss in issues[:3]:
                        st.markdown(f"  - L{iss['linea']}: `{iss['codigo']}` — {iss['mensaje']}")

            st.warning("⚠️ Para aplicar correcciones automáticas (seguras), presiona el botón de abajo. Haz un backup antes.")
            if st.button("🛠️ Aplicar Fixes Seguros (espacios, imports)", use_container_width=True):
                res_fix = aplicar_fixes_seguros(os.getcwd())
                if res_fix["success"]:
                    st.success(f"✅ Se aplicaron {res_fix['fixes_aplicados']} correcciones de estilo.")
                else:
                    st.error(f"Error: {res_fix['error']}")

    # ── SEQUENTIAL THINKING: Visualizador de Razonamiento ──
    with tab_thinking:
        st.markdown("#### 🧠 Sequential Thinking (Pensamiento Visible de Ultron)")
        st.caption("Muestra la cadena de razonamiento de Ultron antes de generar su respuesta.")

        query_demo = st.text_area(
            "Escribe una consulta compleja para analizar:",
            placeholder="Ej: ¿Cuáles son los documentos que ve vencerán en los próximos 30 días según la Ley 16744?",
            height=80
        )
        if st.button("🧠 Iniciar Análisis Profundo", use_container_width=True, type="primary", disabled=not query_demo):
            df_stats = obtener_dataframe(DB_PATH, "SELECT count(*) as n FROM registros")
            df_alrt  = obtener_dataframe(DB_PATH, "SELECT count(*) as n FROM notificaciones_ultron WHERE estado = 'No Leída'")
            ctx_db = {
                "total_docs": df_stats.iloc[0]["n"] if not df_stats.empty else 0,
                "alertas_criticas": df_alrt.iloc[0]["n"] if not df_alrt.empty else 0,
            }
            chain = analizar_consulta_con_thinking(query_demo, ctx_db)
            st.markdown(chain.render_markdown())

            st.divider()
            if st.button("🔊 Escuchar Razonamiento", key="voice_thinking"):
                audio_p = sintetizar_voz_ultron(chain.conclusion)
                if audio_p: st.audio(audio_p, format="audio/mp3", autoplay=True)
