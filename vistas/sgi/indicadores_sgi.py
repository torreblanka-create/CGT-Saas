"""
indicadores_sgi.py — Tablero de KPIs del Sistema de Gestión Integrado (SGI).

KPIs automáticos calculados en tiempo real desde la DB + KPIs manuales configurables.
Visualización con gauge charts, tendencias y semáforos por proceso.
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, date, timedelta
from src.infrastructure.database import ejecutar_query, obtener_dataframe
from core.utils import is_valid_context, show_context_warning
from intelligence.agents.intelligence_engine import UllTroneEngine
from config.config import LOGO_APP, obtener_logo_cliente
from core.reports.generador_pdf import pdf_engine


# ─────────────────────────────────────────────────────────────────────────────
# KPIs AUTOMÁTICOS — Calculados desde la DB sin entrada manual
# ─────────────────────────────────────────────────────────────────────────────
def _calcular_kpis_automaticos(DB_PATH, emp_id, con_id):
    """Extrae métricas reales de todas las tablas del sistema."""
    hoy = date.today()
    hace_30 = hoy - timedelta(days=30)
    hace_90 = hoy - timedelta(days=90)
    kpis = []

    # ── 1. Tasa de Cumplimiento de Auditorías ────────────────────────────────
    try:
        df_aud = obtener_dataframe(DB_PATH,
            "SELECT puntaje_final FROM compliance_audits WHERE empresa_id=? ORDER BY id DESC LIMIT 10",
            (emp_id,))
        if not df_aud.empty:
            avg_aud = df_aud['puntaje_final'].mean()
            kpis.append({"kpi": "Cumplimiento Auditorías", "valor": round(avg_aud, 1),
                         "meta": 90.0, "unidad": "%", "proceso": "Auditorías",
                         "descripcion": "Promedio últimas 10 auditorías registradas"})
    except: pass

    # ── 2. Tasa de Cierre de Brechas (compliance_gaps) ──────────────────────
    try:
        df_gaps = obtener_dataframe(DB_PATH,
            "SELECT estado FROM compliance_gaps g JOIN compliance_audits a ON g.audit_id=a.id WHERE a.empresa_id=?",
            (emp_id,))
        if not df_gaps.empty:
            total = len(df_gaps)
            cerradas = len(df_gaps[df_gaps['estado'].str.lower() == 'cerrado'])
            pct_cierre = (cerradas / total * 100) if total > 0 else 100.0
            kpis.append({"kpi": "Tasa Cierre de Brechas", "valor": round(pct_cierre, 1),
                         "meta": 80.0, "unidad": "%", "proceso": "Auditorías",
                         "descripcion": f"{cerradas}/{total} brechas cerradas"})
    except: pass

    # ── 3. Ejecución de Planes de Acción ─────────────────────────────────────
    try:
        base_q = "SELECT estado FROM planes_accion WHERE empresa_id=?"
        params = [emp_id]
        if con_id and con_id > 0:
            base_q += " AND contrato_id=?"
            params.append(con_id)
        df_planes = obtener_dataframe(DB_PATH, base_q, tuple(params))
        if not df_planes.empty:
            total_p = len(df_planes)
            cerrados_p = len(df_planes[df_planes['estado'].str.lower().isin(['cerrado', 'completado', 'finalizado'])])
            pct_planes = (cerrados_p / total_p * 100) if total_p > 0 else 100.0
            kpis.append({"kpi": "Ejecución Planes de Acción", "valor": round(pct_planes, 1),
                         "meta": 85.0, "unidad": "%", "proceso": "Mejora Continua",
                         "descripcion": f"{cerrados_p}/{total_p} planes cerrados"})
    except: pass

    # ── 4. Capacitaciones Ejecutadas vs Programadas ───────────────────────────
    try:
        df_cap = obtener_dataframe(DB_PATH,
            "SELECT COUNT(*) as n FROM capacitaciones WHERE empresa_id=? AND fecha >= ?",
            (emp_id, str(hace_90)))
        if not df_cap.empty and df_cap['n'].iloc[0] > 0:
            n_cap = int(df_cap['n'].iloc[0])
            # Meta referencial: al menos 1 por mes = 3 en 90 días
            meta_cap = max(3, n_cap)
            valor_cap = min(100.0, (n_cap / meta_cap * 100))
            kpis.append({"kpi": "Capacitaciones (90 días)", "valor": round(valor_cap, 1),
                         "meta": 75.0, "unidad": "%", "proceso": "RRHH & Competencias",
                         "descripcion": f"{n_cap} capacitaciones en últimos 3 meses"})
    except: pass

    # ── 5. Documentos Vigentes (Procedimientos) ───────────────────────────────
    try:
        df_pts = obtener_dataframe(DB_PATH,
            "SELECT estado_doc FROM procedimientos WHERE empresa_id=?", (emp_id,))
        if not df_pts.empty:
            total_docs = len(df_pts)
            vigentes = len(df_pts[df_pts['estado_doc'].str.upper().isin(['VIGENTE', 'ACTIVO', '🟢 VIGENTE', ''])])
            pct_docs = (vigentes / total_docs * 100) if total_docs > 0 else 100.0
            kpis.append({"kpi": "Documentos SGI Vigentes", "valor": round(pct_docs, 1),
                         "meta": 100.0, "unidad": "%", "proceso": "Control Documental",
                         "descripcion": f"{vigentes}/{total_docs} documentos vigentes"})
    except: pass

    # ── 6. Registros Maestros con Documentación Completa ─────────────────────
    try:
        df_reg = obtener_dataframe(DB_PATH,
            "SELECT COUNT(DISTINCT identificador) as n_total FROM registros WHERE empresa_id=?", (emp_id,))
        df_venc = obtener_dataframe(DB_PATH,
            "SELECT COUNT(DISTINCT identificador) as n_venc FROM registros WHERE empresa_id=? AND fecha_vencimiento < ?",
            (emp_id, str(hoy)))
        if not df_reg.empty:
            total_r = int(df_reg['n_total'].iloc[0])
            vencidos_r = int(df_venc['n_venc'].iloc[0]) if not df_venc.empty else 0
            vigentes_r = max(0, total_r - vencidos_r)
            pct_r = (vigentes_r / total_r * 100) if total_r > 0 else 100.0
            kpis.append({"kpi": "Documentos de Activos Vigentes", "valor": round(pct_r, 1),
                         "meta": 95.0, "unidad": "%", "proceso": "Fundamentos Base",
                         "descripcion": f"{vencidos_r} documentos vencidos de {total_r} activos"})
    except: pass

    return kpis


def _gauge_chart(valor, meta, titulo, unidad="%"):
    """Genera un gauge chart Plotly compacto con semáforo automático."""
    pct = (valor / meta * 100) if meta > 0 else 100
    if pct >= 100:
        color = "#10B981"
    elif pct >= 80:
        color = "#F59E0B"
    else:
        color = "#EF4444"

    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=valor,
        delta={"reference": meta, "valueformat": ".1f", "suffix": unidad},
        title={"text": titulo, "font": {"size": 13, "color": "#64748b"}},
        number={"suffix": unidad, "font": {"size": 22, "color": color}},
        gauge={
            "axis": {"range": [0, max(100, meta * 1.1)], "ticksuffix": unidad,
                     "tickcolor": "#94a3b8", "tickwidth": 1},
            "bar": {"color": color, "thickness": 0.3},
            "bgcolor": "rgba(0,0,0,0)",
            "borderwidth": 0,
            "steps": [
                {"range": [0, meta * 0.8], "color": "rgba(239,68,68,0.08)"},
                {"range": [meta * 0.8, meta], "color": "rgba(245,158,11,0.08)"},
                {"range": [meta, max(100, meta * 1.1)], "color": "rgba(16,185,129,0.08)"},
            ],
            "threshold": {
                "line": {"color": "#6366f1", "width": 3},
                "thickness": 0.85,
                "value": meta
            }
        }
    ))
    fig.update_layout(
        height=190,
        margin=dict(l=10, r=10, t=35, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        font={"family": "Inter, sans-serif"}
    )
    return fig


def render_indicadores_sgi(DB_PATH, filtros):
    # --- UI ELITE NEON ONYX ---
    st.markdown("""
        <div style='background: #F5F3F0; color: #1F2937; padding: 2rem; border-radius: 15px; border: 1px solid rgba(212,212,216,0.3); margin-bottom: 2rem; box-shadow: 0 10px 15px -3px rgba(0,0,0,0.05);'>
            <div style='display: flex; align-items: center; gap: 20px;'>
                <div style='background: rgba(56, 189, 248, 0.1); padding: 15px; border-radius: 12px; border: 1px solid rgba(56, 189, 248, 0.2);'>
                    <span style='font-size: 2.5rem;'>📈</span>
                </div>
                <div>
                    <h1 style='color: #F8FAFC; margin: 0; font-size: 1.8rem; font-family: "Outfit", sans-serif;'>Indicadores de Gestión (KPIs) - SGI</h1>
                    <p style='color: #94A3B8; margin: 5px 0 0 0; font-size: 1rem; opacity: 0.9;'>Monitoreo estratégico y visualización de métricas críticas en tiempo real.</p>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    if not is_valid_context(filtros):
        show_context_warning()
        return

    emp_id = filtros.get('empresa_id', 0)
    con_id = filtros.get('contrato_id', 0)
    emp_nom = filtros.get('empresa_nom', 'Global')

    tab_auto, tab_manual, tab_tendencia = st.tabs([
        "🤖 KPIs Automáticos (DB Live)",
        "📝 KPIs Manuales Configurables",
        "📊 Tendencias y Comparativa"
    ])

    # ── TAB 1: KPIs AUTOMÁTICOS ──────────────────────────────────────────────
    with tab_auto:
        st.markdown(f"### Métricas en tiempo real — `{emp_nom}`")
        
        # --- AI STRATEGIC ANALYSIS (Ull-Trone) ---
        kpis_auto = _calcular_kpis_automaticos(DB_PATH, emp_id, con_id)
        
        with st.container(border=True):
            col_ai1, col_ai2 = st.columns([0.7, 0.3])
            col_ai1.markdown("#### 🧠 Análisis Estratégico Ull-Trone")
            col_ai1.caption("La IA analiza tus KPIs actuales y detecta riesgos invisibles o desviaciones proyectadas.")
            
            if col_ai2.button("⚡ Ejecutar Consultoría IA", use_container_width=True, type="primary"):
                with st.spinner("Ull-Trone procesando telemetría..."):
                    contexto_kpis = "\n".join([f"- {k['kpi']}: {k['valor']}{k['unidad']} (Meta: {k['meta']}) -> {k['descripcion']}" for k in kpis_auto])
                    prompt = f"Analiza estos KPIs del Sistema de Gestión Integrado:\n{contexto_kpis}\n\nProporciona: 1. Diagnóstico de Salud Sistémica. 2. 3 Acciones de choque prioritarias. 3. Proyección de riesgo a 90 días."
                    insight = UllTroneEngine.consultar_ia(prompt, temp=0.5)
                    st.session_state.sgi_ai_insight = insight

            if 'sgi_ai_insight' in st.session_state:
                st.markdown(f"<div style='background: rgba(0,212,255,0.05); padding: 20px; border-radius: 10px; border: 1px solid rgba(0,212,255,0.2); font-family: Outfit, sans-serif; color: #E2E8F0;'>{st.session_state.sgi_ai_insight}</div>", unsafe_allow_html=True)
                if st.button("Limpiar Análisis", key="clear_ai_sgi"):
                    del st.session_state.sgi_ai_insight
                    st.rerun()

            # --- EXPORT REPORT ---
            if st.button("📥 Exportar Reporte Ejecutivo SGI (PDF)", use_container_width=True):
                try:
                    df_manual = obtener_dataframe(DB_PATH, "SELECT nombre, valor_actual, meta, responsable FROM sgi_indicadores WHERE empresa_id=?", (emp_id,))
                    ai_ins = st.session_state.get('sgi_ai_insight', '')
                    pdf_bytes = pdf_engine.generar('SGI', emp_nom, kpis_auto, df_manual, ai_ins, LOGO_APP, obtener_logo_cliente(emp_nom))
                    st.download_button(label="Click para Descargar PDF", data=pdf_bytes, file_name=f"Reporte_SGI_{emp_nom}_{date.today()}.pdf", mime="application/pdf", use_container_width=True)
                except Exception as e:
                    st.error(f"Error generando PDF: {e}")

        st.info("Estos KPIs se calculan automáticamente desde los datos registrados en el sistema.", icon="🤖")

        # kpis_auto = _calcular_kpis_automaticos(DB_PATH, emp_id, con_id) # Ya calculado arriba

        if not kpis_auto:
            st.warning("No hay suficientes datos registrados para calcular KPIs automáticos. Comience registrando auditorías, capacitaciones y documentos.")
        else:
            # Fila de métricas resumen
            n_verde = sum(1 for k in kpis_auto if k['valor'] >= k['meta'])
            n_amarillo = sum(1 for k in kpis_auto if k['meta'] * 0.8 <= k['valor'] < k['meta'])
            n_rojo = sum(1 for k in kpis_auto if k['valor'] < k['meta'] * 0.8)

            col_m1, col_m2, col_m3, col_m4 = st.columns(4)
            col_m1.metric("KPIs Totales", len(kpis_auto))
            col_m2.metric("✅ En Meta", n_verde)
            col_m3.metric("⚠️ En Riesgo", n_amarillo)
            col_m4.metric("🔴 Críticos", n_rojo)
            st.divider()

            # Gauges en grid de 3 columnas
            cols = st.columns(3)
            for i, kpi in enumerate(kpis_auto):
                with cols[i % 3]:
                    with st.container(border=True):
                        fig = _gauge_chart(kpi['valor'], kpi['meta'], kpi['kpi'], kpi['unidad'])
                        st.plotly_chart(fig, use_container_width=True, key=f"gauge_{i}")
                        st.caption(f"**Meta:** {kpi['meta']}{kpi['unidad']} | {kpi['descripcion']}")
                        proceso_color = {"Auditorías": "🔵", "Mejora Continua": "🟣", "RRHH & Competencias": "🟢",
                                         "Control Documental": "🟠", "Fundamentos Base": "⚫"}.get(kpi['proceso'], "⚪")
                        st.caption(f"{proceso_color} Proceso: **{kpi['proceso']}**")

    # ── TAB 2: KPIs MANUALES ─────────────────────────────────────────────────
    with tab_manual:
        c_form, c_tabla = st.columns([0.4, 0.6])

        with c_form:
            st.markdown("#### ➕ Registrar / Actualizar KPI")
            with st.form("form_kpi_manual"):
                nombre = st.text_input("Nombre del Indicador", placeholder="Ej: % Avance Programa Preventivo")
                proceso = st.selectbox("Proceso SGI", [
                    "Auditorías", "Mejora Continua", "RRHH & Competencias",
                    "Control Documental", "Operaciones HSE", "Gestión de Activos",
                    "Salud Ocupacional", "Gobernanza", "Otro"
                ])
                col_v, col_m = st.columns(2)
                valor = col_v.number_input("Valor Actual", min_value=0.0, step=0.1)
                meta = col_m.number_input("Meta", min_value=0.1, step=1.0, value=100.0)
                unidad = st.selectbox("Unidad", ["%", "N°", "Días", "Horas", "CLP", "Otro"])
                frecu = st.selectbox("Frecuencia", ["Mensual", "Trimestral", "Semestral", "Anual"])
                resp = st.text_input("Responsable del Proceso")

                if st.form_submit_button("💾 Guardar KPI", type="primary", use_container_width=True):
                    if nombre and resp:
                        ejecutar_query(DB_PATH, """
                            INSERT INTO sgi_indicadores (nombre, meta, frecuencia, responsable, valor_actual, empresa_id, contrato_id)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, (nombre, meta, frecu, resp, valor, emp_id, con_id), commit=True)
                        st.success("✅ KPI guardado.")
                        st.rerun()
                    else:
                        st.error("Complete Nombre y Responsable.")

        with c_tabla:
            st.markdown("#### 📊 KPIs Configurados")
            df_kpi = obtener_dataframe(DB_PATH,
                "SELECT id, nombre, valor_actual, meta, frecuencia, responsable FROM sgi_indicadores WHERE empresa_id=? ORDER BY id DESC",
                (emp_id,))

            if not df_kpi.empty:
                df_kpi['Cumplimiento'] = (df_kpi['valor_actual'] / df_kpi['meta'] * 100).clip(0, 200).round(1)
                df_kpi['Estado'] = df_kpi['Cumplimiento'].apply(
                    lambda x: "✅ En Meta" if x >= 100 else ("⚠️ En Riesgo" if x >= 80 else "🔴 Crítico"))

                st.dataframe(df_kpi[['nombre', 'valor_actual', 'meta', 'Cumplimiento', 'Estado', 'frecuencia', 'responsable']],
                             use_container_width=True, hide_index=True,
                             column_config={
                                 "nombre": "Indicador",
                                 "valor_actual": st.column_config.NumberColumn("Valor", format="%.1f"),
                                 "meta": st.column_config.NumberColumn("Meta", format="%.1f"),
                                 "Cumplimiento": st.column_config.ProgressColumn("Cumplimiento %", min_value=0, max_value=200, format="%.1f%%"),
                             })

                # Gráfico comparativo
                if len(df_kpi) >= 2:
                    fig_bar = px.bar(df_kpi, x="nombre", y=["valor_actual", "meta"],
                                     barmode="group", color_discrete_map={"valor_actual": "#6366f1", "meta": "#e2e8f0"},
                                     labels={"value": "Medición", "nombre": "Indicador", "variable": ""},
                                     title="Valor Actual vs Meta")
                    fig_bar.update_layout(height=300, margin=dict(t=35, b=10),
                                          paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                                          font={"family": "Inter, sans-serif"})
                    st.plotly_chart(fig_bar, use_container_width=True)

                # Eliminar KPI
                with st.expander("🗑️ Eliminar Indicador"):
                    del_id = st.selectbox("KPI a eliminar:", df_kpi['id'].tolist(),
                                          format_func=lambda x: df_kpi[df_kpi['id']==x]['nombre'].values[0])
                    if st.button("Eliminar", type="secondary"):
                        ejecutar_query(DB_PATH, "DELETE FROM sgi_indicadores WHERE id=?", (del_id,), commit=True)
                        st.rerun()
            else:
                st.info("Sin indicadores manuales. Cree el primero con el formulario.")

    # ── TAB 3: TENDENCIAS ────────────────────────────────────────────────────
    with tab_tendencia:
        st.markdown("### 📊 Evolución de Auditorías en el Tiempo")

        df_hist = obtener_dataframe(DB_PATH,
            "SELECT fecha, tipo, puntaje_final FROM compliance_audits WHERE empresa_id=? ORDER BY fecha ASC",
            (emp_id,))

        if df_hist.empty:
            st.info("No hay suficiente historial de auditorías para mostrar tendencias.")
        else:
            df_hist['fecha'] = pd.to_datetime(df_hist['fecha'], errors='coerce')
            df_hist = df_hist.dropna(subset=['fecha'])

            fig_line = px.line(df_hist, x="fecha", y="puntaje_final", color="tipo",
                               title="Evolución del % de Cumplimiento por Tipo de Auditoría",
                               labels={"puntaje_final": "Cumplimiento (%)", "fecha": "Fecha", "tipo": "Auditoría"},
                               markers=True)
            fig_line.add_hline(y=90, line_dash="dash", line_color="#EF4444",
                               annotation_text="Meta 90%", annotation_position="bottom right")
            fig_line.update_layout(height=380, paper_bgcolor="rgba(0,0,0,0)",
                                   plot_bgcolor="rgba(0,0,0,0)", font={"family": "Inter, sans-serif"})
            st.plotly_chart(fig_line, use_container_width=True)

            # Radar de procesos
            st.markdown("#### 🕸️ Radar de Madurez por Proceso")
            kpis_auto_r = _calcular_kpis_automaticos(DB_PATH, emp_id, con_id)
            if kpis_auto_r:
                labels_r = [k['kpi'] for k in kpis_auto_r]
                values_r = [min(100, (k['valor'] / k['meta'] * 100)) for k in kpis_auto_r]
                fig_radar = go.Figure(go.Scatterpolar(
                    r=values_r + [values_r[0]],
                    theta=labels_r + [labels_r[0]],
                    fill='toself',
                    line_color='#6366f1',
                    fillcolor='rgba(99,102,241,0.15)',
                    name='Cumplimiento'
                ))
                fig_radar.update_layout(
                    polar=dict(radialaxis=dict(visible=True, range=[0, 110],
                                              ticksuffix="%", tickcolor="#94a3b8")),
                    height=400, paper_bgcolor="rgba(0,0,0,0)",
                    font={"family": "Inter, sans-serif"},
                    showlegend=False
                )
                st.plotly_chart(fig_radar, use_container_width=True)
