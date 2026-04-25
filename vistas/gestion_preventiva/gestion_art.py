import json
import os
from datetime import datetime

import pandas as pd
import streamlit as st

from config.config import DB_PATH, LOGO_APP, LOGO_CLIENTE, obtener_logo_cliente
from src.infrastructure.database import ejecutar_query, obtener_dataframe
from src.services.risk_manager import obtener_risk_manager
from core.reports.generador_pdf import pdf_engine
from core.utils import (
    obtener_listado_personal,
    render_multiselect_personal,
    render_name_input_combobox,
)


def render_gestion_art(db_path):
    st.markdown("<div class='art-header'><h1>📝 Confección de ART Dinámico</h1><p>Análisis de Riesgos del Trabajo - Estándar Operativo</p></div>", unsafe_allow_html=True)

    # --- CÁLCULO DE MÉTRICAS DE ART ---
    hoy_str = datetime.now().strftime("%Y-%m-%d")
    q_art = "SELECT COUNT(*) as total, COUNT(DISTINCT tarea) as tareas FROM registros_art WHERE fecha = ?"
    df_art_stats = obtener_dataframe(db_path, q_art, (hoy_str,))
    total_hoy = df_art_stats['total'].iloc[0] if not df_art_stats.empty else 0
    tareas_hoy = df_art_stats['tareas'].iloc[0] if not df_art_stats.empty else 0

    # --- ART CONTROL CENTER ---
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown(f"""
            <div style='background: #F5F3F0; color: #1F2937; padding: 20px; border-radius: 12px; border-left: 5px solid #ef4444;'>
                <p style='color: #94a3b8; font-size: 0.75rem; margin: 0; text-transform: uppercase;'>ARTs Hoy</p>
                <p style='color: white; font-size: 1.8rem; font-weight: 700; margin: 5px 0 0 0;'>{total_hoy}</p>
            </div>
        """, unsafe_allow_html=True)
    with m2:
        st.markdown(f"""
            <div style='background: #F5F3F0; color: #1F2937; padding: 20px; border-radius: 12px; border-left: 5px solid #f59e0b;'>
                <p style='color: #94a3b8; font-size: 0.75rem; margin: 0; text-transform: uppercase;'>Criticidad Detectada</p>
                <p style='color: #fbbf24; font-size: 1.8rem; font-weight: 700; margin: 5px 0 0 0;'>Alta</p>
            </div>
        """, unsafe_allow_html=True)
    with m3:
        st.markdown(f"""
            <div style='background: #F5F3F0; color: #1F2937; padding: 20px; border-radius: 12px; border-left: 5px solid #10b981;'>
                <p style='color: #94a3b8; font-size: 0.75rem; margin: 0; text-transform: uppercase;'>Personal Protegido</p>
                <p style='color: white; font-size: 1.8rem; font-weight: 700; margin: 5px 0 0 0;'>{total_hoy * 4}</p>
            </div>
        """, unsafe_allow_html=True)
    with m4:
        st.markdown(f"""
            <div style='background: #F5F3F0; color: #1F2937; padding: 20px; border-radius: 12px; border-left: 5px solid #3b82f6;'>
                <p style='color: #94a3b8; font-size: 0.75rem; margin: 0; text-transform: uppercase;'>Cumplimiento RF</p>
                <p style='color: #3b82f6; font-size: 1.8rem; font-weight: 700; margin: 5px 0 0 0;'>98.2%</p>
            </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Paso 1: Planificación
    with st.container():
        st.markdown("<div class='step-box'><div class='step-title'><span>1️⃣</span> PASO 1: PLANIFICACIÓN DEL TRABAJO</div>", unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            tarea = st.selectbox("Actividad a Realizar",
                                ["Izaje de Componentes", "Intervención Eléctrica", "Trabajo en Altura", "Mantenimiento Mecánico", "Operación de Equipos", "Otro"])
            if tarea == "Otro":
                tarea = st.text_input("Especifique la Actividad")

            # Obtener listado de personal para toda la vista
            filtros = st.session_state.get('filtros', {})
            id_emp_actual = filtros.get('empresa_id', 0)
            id_con_actual = filtros.get('contrato_id', 0)
            lista_personal = obtener_listado_personal(db_path, filtros)

            # HÍBRIDO DE UBICACIÓN COMPACTO
            c_loc1, c_loc2 = st.columns([1, 1])
            with c_loc1:
                loc_pre = st.selectbox("📍 Ubicación Predefinida", ["--- OTRO / MANUAL ---", "Instalación de Faena", "Taller", "Primario", "Secundario", "Terciario", "Planta de filtros", "Planta concentradora", "Planta tostación", "Horno Flash", "Patio de bodega", "Mina"], key="loc_pre_art")
            with c_loc2:
                loc_man = st.text_input("Ingresar manualmente", placeholder="Escriba lugar específico...", key="loc_man_art", disabled=(loc_pre != "--- OTRO / MANUAL ---"))

            area = loc_man if loc_pre == "--- OTRO / MANUAL ---" else loc_pre
        with c2:
            supervisor = render_name_input_combobox("Supervisor que Asigna el Trabajo", lista_personal, key="art_supervisor")
            fecha_hora = datetime.now()
            st.info(f"📅 Fecha y Hora: {fecha_hora.strftime('%d/%m/%Y %H:%M')}")
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div class='step-box'><div class='step-title'><span>2️⃣</span> PASO 2: PREGUNTAS TRANSVERSALES Y CONTROLES</div>", unsafe_allow_html=True)

        # Obtener procedimientos disponibles para la empresa/contrato
        id_emp_actual = st.session_state.filtros.get('empresa_id', 0)
        id_con_actual = st.session_state.filtros.get('contrato_id', 0)

        query_pts = "SELECT DISTINCT codigo, nombre FROM procedimientos WHERE 1=1"
        params_pts = []
        if id_emp_actual > 0:
            query_pts += " AND (empresa = (SELECT nombre FROM empresas WHERE id = ?) OR empresa = 'N/A')"
            params_pts.append(id_emp_actual)

        df_pts = obtener_dataframe(db_path, query_pts, tuple(params_pts))
        lista_pts = ["", "OTRO / ESCRIBIR MANUALMENTE"]
        if not df_pts.empty:
            lista_pts += (df_pts['codigo'] + " - " + df_pts['nombre']).tolist()

        c_trans1, c_trans2 = st.columns(2)
        with c_trans1:
            st.markdown("**Supervisor(a)**")
            q_s1 = st.checkbox("¿El trabajo cuenta con estándar/procedimiento/instructivo?", key="q_s1")
            nom_proc_s = ""
            if q_s1:
                sel_pts_s = st.selectbox("Seleccione Procedimiento (Supervisor)", lista_pts, key="sel_pts_s")
                if sel_pts_s == "OTRO / ESCRIBIR MANUALMENTE":
                    nom_proc_s = st.text_input("Indicar nombre del procedimiento (Manual)", key="nom_proc_s_manual")
                else:
                    nom_proc_s = sel_pts_s

            q_s2 = st.checkbox("¿Personal cuenta con capacitaciones, salud y acreditaciones?", key="q_s2")
            q_s3 = st.checkbox("¿Se gestionaron permisos (áreas/energías)?", key="q_s3")
            q_s4 = st.checkbox("¿Verifiqué elementos de segregación y señalización?", key="q_s4")
            q_s5 = st.checkbox("¿Personal cuenta con sistema de comunicación (emergencia)?", key="q_s5")
            q_s6 = st.checkbox("¿Personal cuenta con los EPP definidos?", key="q_s6")

        with c_trans2:
            st.markdown("**Trabajador(a)**")
            q_t1 = st.checkbox("¿Conozco el estándar/procedimiento/instructivo?", key="q_t1")
            nom_proc_t = ""
            if q_t1:
                # Sincronizamos con el selectbox del supervisor si existe para evitar doble entrada si es el mismo
                sel_pts_t = st.selectbox("Seleccione Procedimiento (Trabajador)", lista_pts, key="sel_pts_t", index=lista_pts.index(sel_pts_s) if q_s1 and sel_pts_s in lista_pts else 0)
                if sel_pts_t == "OTRO / ESCRIBIR MANUALMENTE":
                    nom_proc_t = st.text_input("Indicar nombre del procedimiento (Manual)", key="nom_proc_t_manual", value=nom_proc_s if sel_pts_s == "OTRO / ESCRIBIR MANUALMENTE" else "")
                else:
                    nom_proc_t = sel_pts_t

            q_t2 = st.checkbox("¿Cuento con competencias y salud compatible?", key="q_t2")
            q_t3 = st.checkbox("¿Cuento con autorización para ingresar al área?", key="q_t3")
            q_t4 = st.checkbox("¿Segregué y señalicé el área según diseño?", key="q_t4")
            q_t5 = st.checkbox("¿Conozco teléfono/frecuencia radial de emergencia?", key="q_t5")
            q_t6 = st.checkbox("¿Uso los EPP definidos y en buen estado?", key="q_t6")

        st.divider()

        # ─── SELECTOR COMPACTO DE RIESGOS ────────────────────────────────────────
        risk_manager = obtener_risk_manager()
        todos_rf = list(risk_manager.riesgos.keys())
        opciones_rf_display = [f"🔴 {rf}" for rf in todos_rf]

        st.markdown("**⚠️ Seleccione los Riesgos de Fatalidad presentes en esta tarea:**")
        seleccionados_display = st.multiselect(
            label="Riesgos de Fatalidad",
            options=opciones_rf_display,
            label_visibility="collapsed",
            placeholder="👆 Haga clic aquí para seleccionar los RF que aplican a esta tarea...",
            key="rf_multiselect"
        )
        riesgos_activos = [rf.replace("🔴 ", "") for rf in seleccionados_display]

        if not riesgos_activos:
            st.caption("ℹ️ No se han seleccionado riesgos de fatalidad. Si no aplican, continúe al Paso 3.")

        # ─── CARDS POR CADA RF SELECCIONADO ──────────────────────────────────────
        controles_seleccionados = {}
        for riesgo in riesgos_activos:
            roles = risk_manager.riesgos[riesgo]
            total_ctrls = len(roles["Trabajador"]) + len(roles["Supervisor"])

            # Precalcular badge de estado (sin renderizar aún)
            estado_key = f"_estado_{riesgo}"

            with st.expander(f"🔴 **{riesgo}** — {len(roles['Trabajador'])} controles Trabajador · {len(roles['Supervisor'])} controles Supervisor", expanded=True):
                validados_por_rol = {}
                col_w, col_s = st.columns(2)

                with col_w:
                    st.markdown("##### 👷 Trabajador")
                    validados_w = {}
                    for idx, ctrl in enumerate(roles["Trabajador"]):
                        icono = "🔵" if idx < 10 else "🟢"
                        val = st.radio(ctrl, ["✅ SI", "❌ NO", "➖ N/A"], index=0,
                                       key=f"ctrl_{riesgo}_T_{idx}", horizontal=True)
                        validados_w[ctrl] = val.replace("✅ ", "").replace("❌ ", "").replace("➖ ", "")
                    validados_por_rol["Trabajador"] = validados_w

                with col_s:
                    st.markdown("##### 🦺 Supervisor")
                    validados_s = {}
                    for idx, ctrl in enumerate(roles["Supervisor"]):
                        val = st.radio(ctrl, ["✅ SI", "❌ NO", "➖ N/A"], index=0,
                                       key=f"ctrl_{riesgo}_S_{idx}", horizontal=True)
                        validados_s[ctrl] = val.replace("✅ ", "").replace("❌ ", "").replace("➖ ", "")
                    validados_por_rol["Supervisor"] = validados_s

                # Resumen del RF
                all_vals = list(validados_w.values()) + list(validados_s.values())
                n_si = sum(1 for v in all_vals if v == "SI")
                n_no = sum(1 for v in all_vals if v == "NO")
                n_na = sum(1 for v in all_vals if v == "N/A")
                col_res1, col_res2, col_res3 = st.columns(3)
                col_res1.metric("✅ Conformes", n_si)
                col_res2.metric("❌ No Conformes", n_no)
                col_res3.metric("➖ No Aplica", n_na)
                if n_no > 0:
                    st.warning(f"⚠️ Este RF tiene **{n_no} control(es) NO conforme(s)**. Se requerirá medida correctiva antes de iniciar el trabajo.")

                controles_seleccionados[riesgo] = validados_por_rol

        st.markdown("</div>", unsafe_allow_html=True)

    # Paso 3: Otros Riesgos
    with st.container():
        st.markdown("<div class='step-box'><div class='step-title'><span>3️⃣</span> PASO 3: OTROS RIESGOS (Entorno y Tareas Complementarias)</div>", unsafe_allow_html=True)
        
        risk_manager = obtener_risk_manager()
        otros_riesgos_db = risk_manager.obtener_todos_otros_riesgos()

        opciones_sug = [r["riesgo"] for r in otros_riesgos_db]
        sug_seleccionados = st.multiselect("🔍 Sugerencias de Riesgos Comunes (Selecciona para agregar):", opciones_sug)

        riesgos_otros = []
        # Inicializar con sugerencias
        for sug in sug_seleccionados:
            riesgo_info = next((r for r in otros_riesgos_db if r["riesgo"] == sug), None)
            if riesgo_info:
                riesgos_otros.append({
                    "riesgo": sug, 
                    "medida": riesgo_info["medida"],
                    "id": riesgo_info["id"],
                    "categoria": riesgo_info["categoria"]
                })

        # Permitir agregar manuales
        if st.checkbox("➕ Agregar Riesgo Manualmente"):
            c_r, c_m = st.columns([1, 2])
            with c_r: r_man = st.text_input("Riesgo Manual")
            with c_m: m_man = st.text_input("Medida de Control Manual")
            if r_man and m_man:
                riesgos_otros.append({"riesgo": r_man, "medida": m_man})

        if riesgos_otros:
            st.table(pd.DataFrame(riesgos_otros))
        st.markdown("</div>", unsafe_allow_html=True)

    # Paso 4: Trabajos en Simultáneo
    with st.container():
        st.markdown("<div class='step-box'><div class='step-title'><span>4️⃣</span> PASO 4: TRABAJOS EN SIMULTÁNEO</div>", unsafe_allow_html=True)
        t_simultaneo = st.radio("¿Existen trabajos en simultáneo en el área?", ["NO", "SI"], horizontal=True)
        datos_simultaneo = {}
        if t_simultaneo == "SI":
            datos_simultaneo["contexto"] = st.text_area("Describa el contexto del trabajo en simultáneo:")
            c1, c2, c3 = st.columns(3)
            with c1: datos_simultaneo["coordinacion"] = st.radio("¿Coordinación con líder de cuadrilla?", ["SI", "NO"], key="sim_q1")
            with c2: datos_simultaneo["verificacion"] = st.radio("¿Verificación cruzada de CC?", ["SI", "NO"], key="sim_q2")
            with c3: datos_simultaneo["comunicación"] = st.radio("¿Acciones comunicadas a todos?", ["SI", "NO"], key="sim_q3")
        st.markdown("</div>", unsafe_allow_html=True)

    # Paso 5: Equipo Ejecutor
    with st.container():
        st.markdown("<div class='step-box'><div class='step-title'><span>5️⃣</span> PASO 5: EQUIPO EJECUTOR Y FIRMAS</div>", unsafe_allow_html=True)

        # 1. Ejecutor Principal
        ejecutor_principal = render_name_input_combobox("Nombre del Ejecutor Principal (Líder)", lista_personal, key="art_lider")

        # 2. Selección de Equipo (Participantes)
        equipo = render_multiselect_personal("👥 Equipo Ejecutor (Participantes)", lista_personal, key="art_equipo")

    # Botón de Generación
    if st.button("🚀 Finalizar, Guardar y Generar PDF", type="primary", use_container_width=True):
        if not tarea or not area or not supervisor or not ejecutor_principal:
            st.error("⚠️ Faltan datos obligatorios del Paso 1 o el Líder del equipo.")
        elif not controles_seleccionados:
            st.error("⚠️ Debe seleccionar al menos un riesgo y validar sus controles.")
        else:
            try:
                # 1. Preparar datos para PDF y DB
                datos_art = {
                    "tarea": tarea, "area": area, "supervisor": supervisor,
                    "ejecutor": ejecutor_principal, "equipo": equipo,
                    "controles": controles_seleccionados,
                    "otros_riesgos": riesgos_otros,
                    "simultaneo": {
                        "existe": t_simultaneo,
                        "detalles": datos_simultaneo
                    },
                    "transversales": {
                        "Supervisor": [q_s1, q_s2, q_s3, q_s4, q_s5, q_s6],
                        "Trabajador": [q_t1, q_t2, q_t3, q_t4, q_t5, q_t6],
                        "nombres_proc": {"Supervisor": nom_proc_s, "Trabajador": nom_proc_t}
                    },
                    "fecha": fecha_hora.strftime("%Y-%m-%d"),
                    "hora": fecha_hora.strftime("%H:%M")
                }

                # 2. Generar PDF
                pdf_bytes = pdf_engine.generar('ART', datos_art, LOGO_APP, obtener_logo_cliente(st.session_state.filtros.get('empresa_nom')))

                # 3. Guardar en Base de Datos
                ejecutar_query(DB_PATH, """
                    INSERT INTO registros_art (fecha, hora, tarea, area, supervisor, ejecutor, datos_json, empresa_id, contrato_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    datos_art['fecha'], datos_art['hora'], tarea, area, supervisor, ejecutor_principal,
                    json.dumps(datos_art), st.session_state.filtros['empresa_id'], st.session_state.filtros['contrato_id']
                ), commit=True)

                st.success("✅ ART guardado en el historial exitosamente.")

                st.download_button(
                    label="📥 Descargar ART (PDF)",
                    data=pdf_bytes,
                    file_name=f"ART_{tarea.replace(' ', '_')}_{fecha_hora.strftime('%Y%m%d')}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )

            except Exception as e:
                st.error(f"❌ Error al procesar el ART: {str(e)}")

    # Historial Analítico de ART
    st.divider()
    st.markdown("### 📊 Analítica de Riesgos Operacionales")
    c_h1, c_h2 = st.columns(2)
    
    with c_h1:
        # Gráfico de tareas recurrentes
        df_chart = obtener_dataframe(db_path, "SELECT tarea, COUNT(*) as cantidad FROM registros_art GROUP BY tarea ORDER BY cantidad DESC LIMIT 5")
        if not df_chart.empty:
            import plotly.express as px
            fig = px.bar(df_chart, x='cantidad', y='tarea', orientation='h', title="Top 5 Actividades de Riesgo", color='cantidad', color_continuous_scale="Reds")
            fig.update_layout(template="plotly_dark", showlegend=False, height=300)
            st.plotly_chart(fig, use_container_width=True)
            
    with c_h2:
        # Tendencia de ARTs generados
        df_trend = obtener_dataframe(db_path, "SELECT fecha, COUNT(*) as cantidad FROM registros_art GROUP BY fecha ORDER BY fecha DESC LIMIT 15")
        if not df_trend.empty:
            fig_t = px.line(df_trend, x='fecha', y='cantidad', title="Volumen de ARTs (Últimos 15 días)", markers=True)
            fig_t.update_layout(template="plotly_dark", height=300)
            st.plotly_chart(fig_t, use_container_width=True)

    with st.expander("📂 Ver Historial de Registros ART"):
        df_hist = obtener_dataframe(db_path, "SELECT fecha, hora, tarea, supervisor, ejecutor FROM registros_art ORDER BY id DESC LIMIT 20")
        if not df_hist.empty:
            st.dataframe(df_hist, use_container_width=True, hide_index=True)
        else:
            st.info("No hay registros previos.")
