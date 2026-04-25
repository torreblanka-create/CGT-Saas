import time
from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st

from src.infrastructure.database import ejecutar_query, obtener_dataframe, registrar_log
from core.utils import is_valid_context, render_hybrid_date_input, show_context_warning


def render_salud_ocupacional(DB_PATH, filtros):
    st.markdown("<h2 style='color: var(--cgt-blue);'>⚕️ Salud Ocupacional (Vigilancia y Protocolos MINSAL)</h2>", unsafe_allow_html=True)
    st.write("Control integral de factores de riesgo ambiental y vigilancia biológica de los trabajadores.")

    if not is_valid_context(filtros):
        show_context_warning()
        return

    emp_id = filtros.get('empresa_id')
    con_id = filtros.get('contrato_id')

    # Garantizar que existan los protocolos base (PREXOR, PLANESI) en la DB
    protocolos_default = [("PREXOR (Ruido)", "Exposición ocupacional a ruido."), ("PLANESI (Sílice)", "Erradicación de silicosis en lugar de trabajo.")]
    for prot, desc in protocolos_default:
        try:
            ejecutar_query(DB_PATH, "INSERT INTO protocolos_minsal (nombre, descripcion) VALUES (?, ?)", (prot, desc), commit=True)
        except:
            pass # Ya existe (UNIQUE constraint)

    df_protocolos = obtener_dataframe(DB_PATH, "SELECT id, nombre FROM protocolos_minsal WHERE activo = 1")
    cat_protocolos = {row['nombre']: row['id'] for _, row in df_protocolos.iterrows()}

    tab_dash, tab_ges, tab_medica, tab_mutual, tab_planes = st.tabs(["📊 Radar Ull-Trone (Dashboard)", "🏭 Vigilancia Ambiental (GES)", "🏥 Vigilancia Médica (Clínica)", "📁 Gestor Mutual", "📋 Planes de Gestión"])

    # ==========================================
    # TAB 1: RADAR ULTRON (DASHBOARD)
    # ==========================================
    # ==========================================
    # TAB 1: RADAR ULL-TRONE (DASHBOARD)
    # ==========================================
    with tab_dash:
        # --- CÁLCULO DE MÉTRICAS DE SALUD ---
        q_m1 = "SELECT COUNT(*) FROM ges_ambiental WHERE empresa_id = ?"
        q_m2 = "SELECT COUNT(*) FROM vigilancia_medica_trabajadores WHERE empresa_id = ?"
        q_m3 = "SELECT COUNT(*) FROM vigilancia_medica_trabajadores WHERE empresa_id = ? AND resultado IN ('No Apto', 'Alterado (Derivación)')"
        
        ges_count = ejecutar_query(DB_PATH, q_m1, (emp_id,))[0]
        med_count = ejecutar_query(DB_PATH, q_m2, (emp_id,))[0]
        riesgo_count = ejecutar_query(DB_PATH, q_m3, (emp_id,))[0]

        st.markdown("<p style='color: #94a3b8; font-size: 0.9rem;'>Motor de vigilancia predictiva y control biológico — Ull-Trone v4.0</p>", unsafe_allow_html=True)
        
        # KPIs dinámicos con contraste mejorado
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.markdown(f"""
                <div style='background: #F5F3F0; padding: 15px; border-radius: 10px; border-top: 4px solid #3b82f6; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);'>
                    <p style='color: #1e40af; font-size: 0.75rem; font-weight: 600; margin:0;'>GES MAPEADOS</p>
                    <p style='color: #1F2937; font-size: 1.8rem; font-weight: 800; margin:0;'>{ges_count}</p>
                </div>
            """, unsafe_allow_html=True)
        with c2:
            st.markdown(f"""
                <div style='background: #F5F3F0; padding: 15px; border-radius: 10px; border-top: 4px solid #10b981; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);'>
                    <p style='color: #047857; font-size: 0.75rem; font-weight: 600; margin:0;'>EXÁMENES VIGENTES</p>
                    <p style='color: #1F2937; font-size: 1.8rem; font-weight: 800; margin:0;'>{med_count}</p>
                </div>
            """, unsafe_allow_html=True)
        with c3:
            st.markdown(f"""
                <div style='background: #F5F3F0; padding: 15px; border-radius: 10px; border-top: 4px solid #f59e0b; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);'>
                    <p style='color: #b45309; font-size: 0.75rem; font-weight: 600; margin:0;'>VENCIMIENTOS (30D)</p>
                    <p style='color: #1F2937; font-size: 1.8rem; font-weight: 800; margin:0;'>0</p>
                </div>
            """, unsafe_allow_html=True)
        with c4:
            st.markdown(f"""
                <div style='background: #F5F3F0; padding: 15px; border-radius: 10px; border-top: 4px solid #ef4444; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);'>
                    <p style='color: #dc2626; font-size: 0.75rem; font-weight: 600; margin:0;'>ALERTA DE EXPOSICIÓN</p>
                    <p style='color: #1F2937; font-size: 1.8rem; font-weight: 800; margin:0;'>{riesgo_count}</p>
                </div>
            """, unsafe_allow_html=True)

        st.divider()
        # Grilla para futuros gráficos (Plotly/Streamlit)
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            st.markdown("#### Cumplimiento de Vigilancia Clínica por Protocolo")
            df_chart_p = obtener_dataframe(DB_PATH, """
                SELECT p.nombre, COUNT(*) as cantidad 
                FROM vigilancia_medica_trabajadores v 
                JOIN protocolos_minsal p ON v.protocolo_id = p.id 
                WHERE v.empresa_id = ? 
                GROUP BY p.nombre
            """, (emp_id,))
            if not df_chart_p.empty:
                fig_p = px.bar(df_chart_p, x='nombre', y='cantidad', color='cantidad', color_continuous_scale="Viridis")
                fig_p.update_layout(template="plotly_dark", showlegend=False, height=300)
                st.plotly_chart(fig_p, use_container_width=True)
            else:
                st.info("Sin registros clínicos para graficar.")

        with col_g2:
            st.markdown("#### Distribución de Resultados Médicos")
            df_chart_r = obtener_dataframe(DB_PATH, """
                SELECT resultado, COUNT(*) as cantidad 
                FROM vigilancia_medica_trabajadores 
                WHERE empresa_id = ? 
                GROUP BY resultado
            """, (emp_id,))
            if not df_chart_r.empty:
                fig_r = px.pie(df_chart_r, names='resultado', values='cantidad', hole=0.4, color_discrete_sequence=px.colors.sequential.RdBu)
                fig_r.update_layout(template="plotly_dark", height=300)
                st.plotly_chart(fig_r, use_container_width=True)
            else:
                st.info("Sin data de resultados.")


    # ==========================================
    # TAB 2: VIGILANCIA AMBIENTAL (GES)
    # ==========================================
    with tab_ges:
        st.markdown("### Configuración de Grupos de Exposición Similar (GES)")

        c_ges_1, c_ges_2 = st.columns([0.4, 0.6])
        with c_ges_1:
            st.markdown("#### Crear Nuevo GES")
            with st.form("form_crear_ges", clear_on_submit=True):
                nombre_ges = st.text_input("Nombre del GES", placeholder="Ej: Operadores de Perforadora")
                area_ges = st.text_input("Área/Sector", placeholder="Ej: Mina Rajo")
                desc_ges = st.text_area("Descripción de Tareas")

                if st.form_submit_button("Guardar GES", type="primary", use_container_width=True):
                    if nombre_ges:
                        ejecutar_query(DB_PATH, "INSERT INTO ges_ambiental (nombre_ges, descripcion, area, empresa_id, contrato_id) VALUES (?, ?, ?, ?, ?)",
                                      (nombre_ges, desc_ges, area_ges, emp_id, con_id), commit=True)
                        st.success("✅ GES creado correctamente.")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("El nombre del GES es obligatorio.")

        with c_ges_2:
            st.markdown("#### Registro de Evaluaciones Ambientales (Mediciones)")
            # Need to get existing GES
            df_ges = obtener_dataframe(DB_PATH, "SELECT id, nombre_ges, area FROM ges_ambiental WHERE empresa_id = ?", (emp_id,))

            if not df_ges.empty:
                ges_opciones = {f"{row['nombre_ges']} ({row['area']})": row['id'] for _, row in df_ges.iterrows()}
                with st.form("form_eval_amb"):
                    sel_ges = st.selectbox("Seleccionar GES", list(ges_opciones.keys()))
                    sel_prot = st.selectbox("Protocolo Aplicable", list(cat_protocolos.keys()))

                    ca_1, ca_2 = st.columns(2)
                    with ca_1:
                        f_eval = render_hybrid_date_input("Fecha Evaluación (Medición)", key="f_eval_amb")
                        nivel_riesgo = st.selectbox("Nivel de Exposición (Riesgo)", ["Bajo (Bajo Mitad Dosis)", "Medio (Acción)", "Alto (Sobre Límite)"])
                    with ca_2:
                        f_prox = render_hybrid_date_input("Próxima Evaluación (Vencimiento)", key="f_prox_amb")
                        doc_path = st.text_input("Ruta Informe Técnico (Opcional)")

                    obs_amb = st.text_input("Observaciones")

                    if st.form_submit_button("Registrar Medición", use_container_width=True):
                        ges_id = ges_opciones[sel_ges]
                        prot_id = cat_protocolos[sel_prot]
                        ejecutar_query(DB_PATH, "INSERT INTO evaluaciones_ambientales (ges_id, protocolo_id, fecha_evaluacion, nivel_riesgo, proxima_evaluacion, documento_path, observaciones, empresa_id, contrato_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                                      (ges_id, prot_id, str(f_eval), nivel_riesgo, str(f_prox), doc_path, obs_amb, emp_id, con_id), commit=True)
                        st.success("✅ Medición Ambiental registrada.")
                        time.sleep(1)
                        st.rerun()
            else:
                st.warning("⚠️ Debes crear un GES primero en el panel izquierdo.")

            st.divider()
            if not df_ges.empty:
                st.markdown("#### GES y Mediciones Actuales")
                q_evals = """
                SELECT g.nombre_ges as "GES", p.nombre as "Protocolo", e.fecha_evaluacion as "Fecha Medición", 
                       e.nivel_riesgo as "Riesgo", e.proxima_evaluacion as "Próx. Medición"
                FROM evaluaciones_ambientales e
                JOIN ges_ambiental g ON e.ges_id = g.id
                JOIN protocolos_minsal p ON e.protocolo_id = p.id
                WHERE e.empresa_id = ?
                ORDER BY e.fecha_evaluacion DESC
                """
                df_evals_view = obtener_dataframe(DB_PATH, q_evals, (emp_id,))
                st.dataframe(df_evals_view, use_container_width=True, hide_index=True)


    # ==========================================
    # TAB 3: VIGILANCIA MÉDICA (CLÍNICA)
    # ==========================================
    with tab_medica:
        st.markdown("### Registro de Control de Salud de Trabajadores (Exámenes Médicos)")

        # Here we connect personal (from registros or from somewhere)
        # Assuming we just type Rut or name for now, or fetch from trazabilidad if available
        # Let's fetch from table `registros` where categoria involves "Personal"
        q_pers = "SELECT DISTINCT identificador as rut, nombre FROM registros WHERE categoria LIKE '%Personal%' AND empresa_id = ?"
        df_pers = obtener_dataframe(DB_PATH, q_pers, (emp_id,))

        cb1, cb2 = st.columns([0.4, 0.6])

        with cb1:
            st.markdown("#### Nuevo Examen Médico")
            with st.form("form_nuevo_examen"):
                if not df_pers.empty:
                    pers_opc = {f"{row['nombre']} ({row['rut']})": row['rut'] for _, row in df_pers.iterrows()}
                    sel_trab_str = st.selectbox("Trabajador", list(pers_opc.keys()))
                    trab_rut = pers_opc[sel_trab_str]
                else:
                    st.info("No hay personal en el módulo de trazabilidad. Ingresa Rut Manual:")
                    trab_rut = st.text_input("RUT Trabajador")
                    trab_nombre = st.text_input("Nombre Trabajador")

                sel_prot_med = st.selectbox("Protocolo MINSAL", list(cat_protocolos.keys()))

                cd1, cd2 = st.columns(2)
                with cd1:
                    f_ex = render_hybrid_date_input("Fecha Examen", key="f_ex_med")
                    resultado = st.selectbox("Resultado", ["Normal", "Apto con Observaciones", "Alterado (Derivación)", "No Apto"])
                with cd2:
                    vigencia_m = st.number_input("Vigencia (Meses)", min_value=1, max_value=60, value=12)
                    # La proxima se calcula con Ultron posteriormente, pero pedimos fecha por ahora.
                    f_prox_ex = render_hybrid_date_input("Vencimiento (Próx. Examen)", key="f_prox_med")

                obs_med = st.text_area("Comentarios del Policlínico/Mutual")

                if st.form_submit_button("Guardar Examen Clínico", type="primary", use_container_width=True):
                    if trab_rut:
                        prot_id_med = cat_protocolos[sel_prot_med]
                        # Buscar GES asociado si existe (esto se puede perfeccionar después)
                        ges_id_def = 1 # Placeholder o None
                        ejecutar_query(DB_PATH, "INSERT INTO vigilancia_medica_trabajadores (trabajador_id, protocolo_id, fecha_examen, resultado, vigencia_meses, proximo_examen, estado, observaciones, empresa_id, contrato_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                                      (trab_rut, prot_id_med, str(f_ex), resultado, vigencia_m, str(f_prox_ex), "Vigente", obs_med, emp_id, con_id), commit=True)
                        st.success("✅ Examen Médico Registrado.")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("Rut de trabajador requerido.")

        with cb2:
            st.markdown("#### Historial Clínico de Protocolos")
            q_meds = """
            SELECT v.trabajador_id as "RUT", p.nombre as "Protocolo", v.fecha_examen as "F. Examen", 
                   v.resultado as "Resultado Clínico", v.proximo_examen as "Vencimiento"
            FROM vigilancia_medica_trabajadores v
            JOIN protocolos_minsal p ON v.protocolo_id = p.id
            WHERE v.empresa_id = ?
            ORDER BY v.proximo_examen DESC
            """
            df_meds = obtener_dataframe(DB_PATH, q_meds, (emp_id,))

            if not df_meds.empty:
                # Semáforo para tabla médica (Ultron Alert)
                hoy = datetime.now().date()
                def calc_estado(f_v_str):
                    try:
                        f_v = datetime.strptime(str(f_v_str).split(" ")[0], '%Y-%m-%d').date()
                        if f_v < hoy: return "🔴 Vencido (N/Apto)"
                        if (f_v - hoy).days < 45: return "🟡 Aviso: Cita Policlínico"
                        return "🟢 Vigente"
                    except: return "⚪ Error"

                df_meds['Estado (Ull-Trone)'] = df_meds['Vencimiento'].apply(calc_estado)
                st.dataframe(df_meds, use_container_width=True, hide_index=True)
            else:
                st.info("Sin registros clínicos ingresados aún.")

        st.divider()
        st.markdown("#### 📈 Tendencia Clínica de Trabajador")
        st.caption("Visualiza el progreso o deterioro del nivel de exposición clínica a través del tiempo.")
        
        # Filtramos para tener suficiente data de gráficos
        q_trend = """
            SELECT v.trabajador_id as "RUT", p.nombre as "Protocolo", v.fecha_examen as "Fecha", 
                   v.resultado as "Resultado"
            FROM vigilancia_medica_trabajadores v
            JOIN protocolos_minsal p ON v.protocolo_id = p.id
            WHERE v.empresa_id = ?
            ORDER BY v.fecha_examen ASC
        """
        df_trend = obtener_dataframe(DB_PATH, q_trend, (emp_id,))
        if not df_trend.empty and len(df_trend) > 0:
            trut_sel = st.selectbox("Seleccione Trabajador para Análisis", df_trend['RUT'].unique())
            df_t_filt = df_trend[df_trend['RUT'] == trut_sel].copy()
            
            # Mapeo de gravedad para graficar (1 = Peor, 4 = Optimo)
            score_map = {"No Apto": 1, "Alterado (Derivación)": 2, "Apto con Observaciones": 3, "Normal": 4}
            df_t_filt['Score'] = df_t_filt['Resultado'].map(score_map)
            df_t_filt = df_t_filt.dropna(subset=['Score'])
            
            if len(df_t_filt) > 1:
                fig_t = px.line(df_t_filt, x="Fecha", y="Score", color="Protocolo", markers=True,
                               title=f"Evolución Clínica - RUT: {trut_sel}",
                               labels={'Score': 'Salud Clínica (4=Normal, 1=No Apto)'})
                fig_t.update_yaxes(tickvals=[1, 2, 3, 4], ticktext=["No Apto", "Alterado", "Apto c/Obs", "Normal"])
                st.plotly_chart(fig_t, use_container_width=True)
            else:
                st.info("📉 Se requieren al menos 2 mediciones históricas del mismo trabajador para trazar una tendencia de mejora/empeoramiento.")
        else:
            st.info("No hay datos históricos registrados para generar tendencias.")

    # ==========================================
    # TAB 4: GESTOR LEGAL MUTUALIDAD
    # ==========================================
    with tab_mutual:
        st.markdown("### Repositorio Estructurado de Mutualidad")
        st.write("Centraliza las Cartas de Aplicación, Screenings e Informes Técnicos por protocolo.")

        col_m1, col_m2 = st.columns([0.4, 0.6])

        with col_m1:
            with st.form("form_mutual_doc", clear_on_submit=True):
                st.markdown("#### Subir Documento Mutual")
                sel_prot_mut = st.selectbox("Protocolo / Agente", list(cat_protocolos.keys()), key="prot_mut")

                # Opcional ligarlo a un GES
                ges_mut_ops = {"Aplica a toda la Faena / Global": None}
                df_ges_mut = obtener_dataframe(DB_PATH, "SELECT id, nombre_ges, area FROM ges_ambiental WHERE empresa_id = ?", (emp_id,))
                if not df_ges_mut.empty:
                    for _, row in df_ges_mut.iterrows():
                        ges_mut_ops[f"{row['nombre_ges']} ({row['area']})"] = row['id']

                sel_ges_mut = st.selectbox("Grupo de Exposición Similar (Opcional)", list(ges_mut_ops.keys()))

                tipo_doc = st.selectbox("Tipo de Documento", [
                    "Carta de Aplicación / No Aplicación",
                    "Informe de Screening (Barrido)",
                    "Evaluación Cualitativa (Listas de Chequeo)",
                    "Evaluación Cuantitativa (Dosis)"
                ])

                entidad_ev = st.text_input("Entidad Evaluadora", value="Mutual de Seguridad / ACHS / IST")
                f_doc_mut = render_hybrid_date_input("Fecha del Documento", key="f_doc_mut")
                file_mut = st.file_uploader("Subir PDF (Evidencia Legal)")
                obs_mut = st.text_area("Consideraciones Críticas / Resumen")

                if st.form_submit_button("Guardar en Repositorio", type="primary", use_container_width=True):
                    id_p = cat_protocolos[sel_prot_mut]
                    id_g = ges_mut_ops[sel_ges_mut]

                    # Logica basica de guardado de archivo dummy por ahora
                    path_mut = file_mut.name if file_mut else "Sin PDF"

                    ejecutar_query(DB_PATH, "INSERT INTO repositorio_minsal (protocolo_id, ges_id, tipo_documento, entidad_evaluadora, fecha_documento, documento_path, consideraciones, empresa_id, contrato_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                                  (id_p, id_g, tipo_doc, entidad_ev, str(f_doc_mut), path_mut, obs_mut, emp_id, con_id), commit=True)
                    st.success("✅ Documento alojado en el sistema.")
                    time.sleep(1)
                    st.rerun()

        with col_m2:
            st.markdown("#### Historial Documental")
            q_mut = """
                SELECT p.nombre as Protocolo, m.tipo_documento as "Tipo de Informe", 
                       m.entidad_evaluadora as Mutual, m.fecha_documento as Fecha, m.documento_path as "Archivo"
                FROM repositorio_minsal m
                JOIN protocolos_minsal p ON m.protocolo_id = p.id
                WHERE m.empresa_id = ?
                ORDER BY m.fecha_documento DESC
            """
            df_hist_mut = obtener_dataframe(DB_PATH, q_mut, (emp_id,))
            if not df_hist_mut.empty:
                st.dataframe(df_hist_mut, use_container_width=True, hide_index=True)
            else:
                st.info("El repositorio de la mutual está vacío.")

    # ==========================================
    # TAB 5: PLANES DE GESTIÓN (JERARQUÍA)
    # ==========================================
    with tab_planes:
        st.markdown("### Programas de Control y Gestión")
        st.write("Genera planes de acción correctivos basados en la Jerarquía de Control de Riesgos exigida por MINSAL.")

        ca_p1, ca_p2 = st.columns([0.4, 0.6])

        with ca_p1:
            with st.form("form_plan_gestion"):
                st.markdown("#### Nueva Tarea de Control")
                sel_prot_plan = st.selectbox("Aplica a Protocolo", list(cat_protocolos.keys()), key="prot_plan")
                titulo_plan = st.text_input("Acción Requerida", placeholder="Ej: Instalar ventilación forzada taller mecánico")

                # Jerarquía estricta según normativa EHS
                jerarquia = st.selectbox("Jerarquía de Control Aplicada (Eficacia)", [
                    "5. Eliminación Técnica del Riesgo",
                    "4. Sustitución de Agente Causal",
                    "3. Control de Ingeniería (Rediseño, Ventilación, Aislación)",
                    "2. Control Administrativo (Rotación, Letreros, Difusión Art 21)",
                    "1. Elemento de Protección Personal (Respirador, Tapones)"
                ], index=2)

                resp_plan = st.text_input("Responsable Tarea", placeholder="Ej: Jefe de Mantención")
                f_venc_plan = render_hybrid_date_input("Fecha Límite (Auditable)", key="f_venc_plan")

                if st.form_submit_button("Añadir al Plan de Gestión", use_container_width=True):
                    if titulo_plan and resp_plan:
                        id_p_plan = cat_protocolos[sel_prot_plan]
                        # Limpiamos el texto de la jerarquía para que no quede tan largo
                        clase_jer = jerarquia.split(". ")[1]

                        ejecutar_query(DB_PATH, "INSERT INTO planes_gestion_salud (protocolo_id, titulo, tipo_jerarquia, responsable, fecha_vencimiento, empresa_id, contrato_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
                                      (id_p_plan, titulo_plan, clase_jer, resp_plan, str(f_venc_plan), emp_id, con_id), commit=True)
                        st.success("✅ Tarea ingresada. Ull-Trone monitorizará la fecha.")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("Título y responsable son obligatorios.")

        with ca_p2:
            st.markdown("#### Planes de Gestión Activos")
            q_plan = """
                SELECT p.nombre as Protocolo, g.titulo as "Acción / Tarea", g.tipo_jerarquia as "Jerarquía Control", 
                       g.responsable as Responsable, g.fecha_vencimiento as Vencimiento, g.estado as Estado
                FROM planes_gestion_salud g
                JOIN protocolos_minsal p ON g.protocolo_id = p.id
                WHERE g.empresa_id = ?
                ORDER BY g.fecha_vencimiento ASC
            """
            df_plan = obtener_dataframe(DB_PATH, q_plan, (emp_id,))
            if not df_plan.empty:
                def alert_plan(f_v_str, est):
                    if est == 'Cerrado': return "✅ Terminado"
                    try:
                        f_v = datetime.strptime(str(f_v_str).split(" ")[0], '%Y-%m-%d').date()
                        hoy = datetime.now().date()
                        if f_v < hoy: return "🔴 Atrasado"
                        if (f_v - hoy).days <= 7: return "🟡 Crítico"
                        return "🟢 A tiempo"
                    except: return "⚪ Error"

                df_plan['Estado Ull-Trone'] = df_plan.apply(lambda r: alert_plan(r['Vencimiento'], r['Estado']), axis=1)
                st.dataframe(df_plan, use_container_width=True, hide_index=True)
            else:
                st.info("Excelente, no hay planes de gestión atrasados documentados.")
