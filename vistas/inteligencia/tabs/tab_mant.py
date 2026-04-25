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


def render_tab_mant(DB_PATH, filtros):
    st.markdown("### 🛠️ Herramientas de Mantenimiento Crítico")
    c_m1, c_m2 = st.columns(2)
    with c_m1:
        if st.button("🔄 Sincronizar Carpetas desde Excel", use_container_width=True):
            with st.spinner("Sincronizando directorios..."): st.info(sincronizar_directorios_desde_excel())

        st.divider()
        st.markdown("#### 📂 Reorganización Profesional")
        if st.button("📁 Ejecutar Reorganización Estructural", use_container_width=True, type="secondary"):
            with st.status("Ull-Trone reorganizando archivos...", expanded=True) as status:
                resultado = organizar_carpetas_sistema(DB_PATH, status_callback=status.write)
                status.update(label="Proceso Finalizado", state="complete")
            st.success(resultado)
            st.rerun()
    with c_m2:
        if os.path.exists(DB_PATH):
            with open(DB_PATH, "rb") as f:
                st.download_button("📥 Descargar Respaldo BD", f, f"Backup_CGT_{datetime.now().strftime('%Y%m%d')}.db", use_container_width=True)

    st.divider()
    st.markdown("#### 🧹 Utilidades de Limpieza")
    c_u1, c_u2 = st.columns(2)
    with c_u1:
        if st.button("🔥 Limpiar Caché / Borrar Memoria", use_container_width=True, type="primary"):
            st.cache_data.clear(); st.cache_resource.clear()
            st.success("✅ Caché borrada."); time.sleep(1); st.rerun()
        if st.button("🧹 Consolidar y Purgar Empresas Fantasmas", use_container_width=True):
            with st.spinner("Purgando fantasmas..."):
                df_emps = obtener_dataframe(DB_PATH, "SELECT id, UPPER(nombre) as unom FROM empresas")
                if not df_emps.empty:
                    for unom, group in df_emps.groupby('unom'):
                        if len(group) > 1:
                            p_id = int(group.iloc[0]['id'])
                            for _, row in group.iloc[1:].iterrows():
                                g_id = int(row['id'])
                                for t in ["registros", "contratos", "usuarios"]:
                                    try: ejecutar_query(DB_PATH, f"UPDATE {t} SET empresa_id = ? WHERE empresa_id = ?", (p_id, g_id), commit=True)
                                    except: pass
                                ejecutar_query(DB_PATH, "DELETE FROM empresas WHERE id = ?", (g_id,), commit=True)
            st.success("✅ Limpieza completada."); time.sleep(1); st.rerun()

    with c_u2:
        st.warning("⚠️ El vaciado eliminará de forma irreversible **TODOS LOS EXPEDIENTES** de la categoría.")
        opciones_cat = ["---", "Personal", "Maquinaria Pesada & Vehículos", "Elementos de izaje", "Instrumentos y Metrología", "Sistemas de Emergencia", "EPP"]
        cat_del = st.selectbox("Categoría a Vaciar:", opciones_cat)
        if st.button("🚨 VACIAR LA CATEGORÍA ENTERA 🚨", use_container_width=True, disabled=(cat_del == "---")):
            ejecutar_query(DB_PATH, "DELETE FROM registros WHERE categoria = ?", (cat_del,), commit=True)
            st.success(f"💀 Categoría '{cat_del}' vaciada."); time.sleep(2); st.rerun()

    st.divider()
    st.markdown("#### 📊 Gestión de Datos Maestros (Carga Masiva)")
    c_up1, c_up2 = st.columns(2)
    with c_up1: emp_sync = st.selectbox("Empresa Destino:", obtener_listas_unicas("EMPRESA"), key="sync_emp")
    with c_up2: con_sync = st.selectbox("Contrato Destino:", obtener_contratos_por_empresa(emp_sync) if emp_sync else [], key="sync_con")
    archivo = st.file_uploader("📥 Subir Excel de Maestro", type=["xlsx", "xls"])

    if st.button("🚀 Procesar e Inyectar Maestro", use_container_width=True, disabled=not (emp_sync and con_sync)):
        with st.spinner("Inyectando..."):
            e_res = ejecutar_query(DB_PATH, "SELECT id FROM empresas WHERE nombre = ?", (normalizar_texto(emp_sync),))
            if e_res:
                c_res = ejecutar_query(DB_PATH, "SELECT id FROM contratos WHERE empresa_id = ? AND nombre_contrato = ?", (e_res[0][0], normalizar_texto(con_sync)))
                if c_res:
                    success, msg = sincronizar_maestro_desde_excel(e_res[0][0], c_res[0][0], archivo)
                    if success: st.success(msg)
                    else: st.error(msg)

    df_exp = exportar_maestro_a_excel()
    if not df_exp.empty:
        import io
        out = io.BytesIO()
        with pd.ExcelWriter(out, engine='openpyxl') as writer: df_exp.to_excel(writer, index=False, sheet_name='EXPORT')
        st.download_button("📥 Exportar Maestro Completo", out.getvalue(), f"Maestro_CGT_{datetime.now().strftime('%Y%m%d')}.xlsx", use_container_width=True)

    # ── TAB 12: DEV TOOLS (Ultron v3.1) ──
