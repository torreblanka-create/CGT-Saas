import json
from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st

from src.infrastructure.database import ejecutar_query, obtener_dataframe
from core.utils import obtener_listado_personal, render_name_input_combobox

# ==========================================
# 1. SEMILLA: PLANTILLAS POR DEFECTO
# ==========================================
PLANTILLAS_BASE = [
  {
    "nombre": "Manipulador de Cables",
    "categoria": "Vehículos y Maquinarias",
    "preguntas": [
      "Sistema de Frenos: Los frenos de servicio y de estacionamiento responden de manera inmediata y sin deslizamientos durante la prueba.",
      "Integridad Hidráulica: Se verifica que cilindros, mangueras y cañerías hidráulicas no presentan fugas de aceite, fisuras ni desgaste por roce.",
      "Elementos de Levante: La garra de levante y el carrete operan con fluidez y responden con precisión a los comandos del control remoto.",
      "Sistemas de Advertencia: La baliza, la pértiga, la alarma sonora de retroceso y las luces de emergencia se encuentran 100% operativas."
    ]
  },
  {
    "nombre": "Camioneta",
    "categoria": "Vehículos y Maquinarias",
    "preguntas": [
      "Sistema Anticolisión (CAS): Se comprueba el funcionamiento sin errores de la antena, el display, el led de proximidad y el botón de reconocimiento de alarma.",
      "Estándar Rajo Mina: El vehículo cuenta con su Autorización (Letra 'A') visible, pértiga luminosa operativa, baliza y radio de telecomunicaciones en la frecuencia correcta.",
      "Seguridad Estructural: La barra antivuelco (interior y exterior), la malla del pick up y los cinturones de seguridad no presentan daños estructurales.",
      "Aptitud y Somnolencia: El conductor declara haber tenido un descanso ininterrumpido mínimo de 6 horas y confirma no estar bajo los efectos de medicamentos que induzcan sueño."
    ]
  },
  {
    "nombre": "EPP Simple",
    "categoria": "Equipos de Protección Personal",
    "preguntas": [
      "Protección Básica Intacta: Casco, barbiquejo y protección auditiva se inspeccionan y no presentan grietas, deformaciones ni desgaste severo.",
      "EPP Específico Validado: El calzado dieléctrico, el buzo ignífugo (incluyendo costuras y cierres) y el protector facial están en condiciones óptimas para su uso.",
      "Protección de Manos: El trabajador cuenta con los guantes exactos requeridos para la maniobra (anticorte, cabritilla, etc.) tras validarlos en el probador de guantes.",
      "Elementos de Bloqueo (LOTOTO): Candado, tarjeta y pinzas de bloqueo están físicamente disponibles, íntegros y listos para la desenergización."
    ]
  },
  {
    "nombre": "Camión Pluma",
    "categoria": "Vehículos y Maquinarias",
    "preguntas": [
      "Documentación y Certificación: La certificación de la pluma, la del capacho y la revisión técnica están vigentes y a bordo del equipo.",
      "Sistemas de Estabilización: Los estabilizadores se despliegan, bajan y fijan el equipo correctamente al terreno, sin presentar fugas hidráulicas.",
      "Operación de Izaje: El mando de la pluma (joysticks), los ganchos y sus seguros operativos funcionan sin trabas ni movimientos erráticos.",
      "Control de Emergencia: Se prueban las paradas de emergencia, verificando que cortan instantáneamente toda la energía y movimiento del sistema."
    ]
  }
]

def sembrar_plantillas_base(db_path):
    res = ejecutar_query(db_path, "SELECT COUNT(*) FROM checklists_templates")
    if res and res[0] == 0:
        for p in PLANTILLAS_BASE:
            ejecutar_query(db_path, """
                INSERT INTO checklists_templates (nombre, categoria, preguntas_json)
                VALUES (?, ?, ?)
            """, (p["nombre"], p["categoria"], json.dumps(p["preguntas"])), commit=True)

# ==========================================
# 2. RENDER PRINCIPAL DEL MÓDULO
# ==========================================
def render_inspecciones(DB_PATH, filtros):
    # Determinar si el usuario es administrador
    is_master = st.session_state.role == "Global Admin"

    # --- HEADER PREMIUM ---
    st.markdown("""
        <div class='premium-header'>
            <div style='display: flex; align-items: center; gap: 15px;'>
                <div style='background: linear-gradient(135deg, #3b82f6, #1e40af); padding: 12px; border-radius: 12px; box-shadow: 0 4px 15px rgba(59, 130, 246, 0.3);'>
                    <span style='font-size: 24px;'>📋</span>
                </div>
                <div>
                    <h1 style='margin: 0; color: #1F2937; font-size: 1.8rem;'>Inspecciones Terreno</h1>
                    <p style='margin: 0; color: #64748b; font-size: 0.9rem;'>Centro de Mando: Control Normativo y Verificación Operacional</p>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    # --- CÁLCULO DE MÉTRICAS GLOBALES ---
    query_stats = "SELECT COUNT(*) as total, AVG(porcentaje_cumplimiento) as avg_c, SUM(CASE WHEN estado='Rechazado' THEN 1 ELSE 0 END) as rechazos FROM checklists_registros"
    params_s = []
    if not is_master:
        query_stats += " WHERE empresa_id = ?"
        params_s.append(st.session_state.empresa_id)
    elif filtros.get('empresa_id') and filtros.get('empresa_id') > 0:
        query_stats += " WHERE empresa_id = ?"
        params_s.append(filtros['empresa_id'])
    
    df_stats = obtener_dataframe(DB_PATH, query_stats, tuple(params_s))
    total_i = df_stats['total'].iloc[0] if not df_stats.empty else 0
    avg_c = df_stats['avg_c'].iloc[0] if not df_stats.empty and df_stats['avg_c'].iloc[0] is not None else 0
    rechazos = df_stats['rechazos'].iloc[0] if not df_stats.empty else 0

    # --- MÉTRICAS ELITE ---
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown(f"""
            <div class='metric-card-cgt' style='border-left: 4px solid #3b82f6;'>
                <p class='metric-label-cgt'>Total Inspecciones</p>
                <p class='metric-value-cgt' style='color: #3b82f6;'>{total_i}</p>
            </div>
        """, unsafe_allow_html=True)
    with m2:
        st.markdown(f"""
            <div class='metric-card-cgt' style='border-left: 4px solid #10b981;'>
                <p class='metric-label-cgt'>Cumplimiento</p>
                <p class='metric-value-cgt' style='color: #10b981;'>{avg_c:.1f}%</p>
            </div>
        """, unsafe_allow_html=True)
    with m3:
        st.markdown(f"""
            <div class='metric-card-cgt' style='border-left: 4px solid #ef4444;'>
                <p class='metric-label-cgt'>Rechazos / NC</p>
                <p class='metric-value-cgt' style='color: #ef4444;'>{rechazos}</p>
            </div>
        """, unsafe_allow_html=True)
    with m4:
        st.markdown(f"""
            <div class='metric-card-cgt' style='border-left: 4px solid #f59e0b;'>
                <p class='metric-label-cgt'>Estatus Global</p>
                <p class='metric-value-cgt' style='color: #f59e0b;'>{"Crítico" if rechazos > 5 else "Estable" if avg_c > 90 else "En Alerta"}</p>
            </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    tab_ejecutar, tab_historial, tab_dashboard, tab_mantenedor = st.tabs([
        "📝 Ejecutar Inspección",
        "🗃️ Historial y Trazabilidad",
        "📊 Dashboard Analítico",
        "⚙️ Administrador de Plantillas"
    ])

    # ------------------------------------------
    # PESTAÑA 1: EJECUTAR INSPECCIÓN
    # ------------------------------------------
    with tab_ejecutar:
        st.write("Selecciona una plantilla para ejecutar un checklist en terreno.")

        df_templates = obtener_dataframe(DB_PATH, "SELECT id, nombre, categoria, preguntas_json FROM checklists_templates")

        if df_templates.empty:
            st.warning("No hay plantillas de inspección creadas. Ve al Administrador de Plantillas para crear una.")
        else:
            with st.container(border=True):
                col1, col2 = st.columns(2)
                with col1:
                    lista_cat = ["Todas"] + df_templates['categoria'].unique().tolist()
                    filtro_cat = st.selectbox("Filtrar por Categoría:", lista_cat, key="filtro_cat_ejecuta")

                df_filtrado = df_templates if filtro_cat == "Todas" else df_templates[df_templates['categoria'] == filtro_cat]

                with col2:
                    opciones_plantillas = {row['id']: f"{row['nombre']} ({row['categoria']})" for _, row in df_filtrado.iterrows()}
                    if not opciones_plantillas:
                        st.info("No hay plantillas en esta categoría.")
                        tpl_sel_id = None
                    else:
                        tpl_sel_id = st.selectbox("Seleccionar Plantilla:", options=list(opciones_plantillas.keys()), format_func=lambda x: opciones_plantillas[x], key="sel_tpl_ejecuta")

            # Mostrar Formulario de Checklist
            if tpl_sel_id is not None:
                row_tpl = df_filtrado[df_filtrado['id'] == tpl_sel_id].iloc[0]
                preguntas = json.loads(row_tpl['preguntas_json'])

                st.markdown(f"### 📋 Checklist: {row_tpl['nombre']}")
                st.caption(f"Categoría: {row_tpl['categoria']}")

                # Obtener listado de personal para Auditor/Inspector
                lista_personal = obtener_listado_personal(DB_PATH, filtros)

                with st.form("form_ejecutar_checklist"):
                    # Datos del contexto obtenidos de Filtros Globales
                    c_ctx1, c_ctx2 = st.columns(2)
                    with c_ctx1:
                        empresa_filtro = filtros.get('empresa_nom') or st.session_state.get('empresa_nom', 'N/A')
                        contrato_filtro = filtros.get('contrato_nom') or 'N/A'
                        st.info(f"🏢 **Empresa:** {empresa_filtro}")
                        emp_inspeccion = empresa_filtro
                        inspector = render_name_input_combobox("Inspector / Auditor", lista_personal, key="insp_persona", default=st.session_state.get('user_nombre', ''))
                    with c_ctx2:
                        st.info(f"📋 **Contrato / Faena:** {contrato_filtro}")
                        con_inspeccion = contrato_filtro
                        fecha_insp = st.date_input("Fecha Inspección", value=datetime.now().date())

                    # Mapeo Categoria Plantilla -> Categoria BD
                    cat_map = {
                        "Vehículos y Maquinarias": "Maquinaria Pesada & Vehículos",
                        "Equipos de Protección Personal": "Personal",
                        "Herramientas": "Instrumentos y Metrología",
                        "Instalaciones": "Instalaciones",
                        "Otros": "Otros"
                    }
                    categoria_db = cat_map.get(row_tpl['categoria'], row_tpl['categoria'])

                    # Conectar a Registros para Entidades Precargadas de forma segura
                    query_ent = "SELECT DISTINCT identificador, nombre FROM registros WHERE categoria = ?"
                    params_ent = [categoria_db]

                    if not is_master:
                        query_ent += " AND empresa_id = ?"
                        params_ent.append(st.session_state.empresa_id)
                    elif filtros.get('empresa_id') and filtros.get('empresa_id') > 0:
                        query_ent += " AND empresa_id = ?"
                        params_ent.append(filtros.get('empresa_id'))

                    if filtros.get('contrato_id'):
                        query_ent += " AND contrato_id = ?"
                        params_ent.append(filtros['contrato_id'])

                    df_entidades = obtener_dataframe(DB_PATH, query_ent, tuple(params_ent))

                    if not df_entidades.empty:
                        df_entidades['display'] = df_entidades['identificador'].astype(str) + " - " + df_entidades['nombre'].astype(str)
                        lista_entidades = df_entidades['display'].tolist()
                    else:
                        lista_entidades = []

                    st.markdown("#### Entidad a Inspeccionar")

                    if not lista_entidades:
                        st.warning(f"No se encontraron entidades registradas en esta categoria y empresa.")
                        entidad_inspeccionada = st.text_input("Ingresar manualmente:", key="insp_ent_man", help="Escribe manualmente la entidad si no existe en la base de datos.")
                    else:
                        entidad_inspeccionada = st.selectbox(
                            "Seleccione desde la Base de Datos Maestra (Precargados):",
                            ["-- Seleccione --", "➕ OTRO / MANUAL"] + lista_entidades,
                            key="insp_ent_sel",
                            help="Las entidades mostradas aquí provienen de los módulos de Trazabilidad y están filtradas por la Empresa actual."
                        )
                        if entidad_inspeccionada == "➕ OTRO / MANUAL":
                            entidad_inspeccionada = st.text_input("Ingresar manualmente (ID / Nombre):", key="insp_ent_man_fallback")

                    st.divider()
                    st.markdown("#### Puntos de Verificación")
                    st.info("💡 Evalúa cada ítem como Cumple (C), No Cumple (NC) o No Aplica (N/A).")

                    respuestas = {}
                    for i, preg in enumerate(preguntas):
                        with st.container(border=True):
                            st.markdown(f"**{i+1}. {preg}**")
                            # Radio actions
                            respuestas[i] = st.radio("Evaluación:", ["Cumple", "No Cumple", "N/A"], key=f"eval_{i}", horizontal=True)

                    st.divider()
                    sub_btn = st.form_submit_button("💾 Finalizar y Guardar Inspección", type="primary", use_container_width=True)

                    if sub_btn:
                        if not emp_inspeccion or not entidad_inspeccionada:
                            st.error("❌ Faltan datos (Empresa Evaluada y Entidad Inspeccionada son obligatorios).")
                        else:
                            # Cálculo de cumplimiento
                            ptos_max = 0
                            ptos_obt = 0
                            dict_respuestas = {}

                            for ix, p_txt in enumerate(preguntas):
                                val = respuestas[ix]
                                dict_respuestas[str(ix)] = {"pregunta": p_txt, "respuesta": val}
                                if val == "Cumple":
                                    ptos_max += 1
                                    ptos_obt += 1
                                elif val == "No Cumple":
                                    ptos_max += 1

                            porcentaje = (ptos_obt / ptos_max * 100.0) if ptos_max > 0 else 100.0
                            estado_final = "Aprobado" if porcentaje >= 100.0 else "Rechazado"

                            query_ins = """
                                INSERT INTO checklists_registros 
                                (template_id, fecha, inspector, empresa, contrato, entidad_inspeccionada, respuestas_json, porcentaje_cumplimiento, estado, empresa_id, contrato_id)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """
                            params_ins = (
                                tpl_sel_id, str(fecha_insp), inspector,
                                emp_inspeccion, con_inspeccion, entidad_inspeccionada,
                                json.dumps(dict_respuestas), porcentaje, estado_final,
                                filtros.get('empresa_id', 0), filtros.get('contrato_id', 0)
                            )
                            ejecutar_query(DB_PATH, query_ins, params_ins, commit=True)

                            st.success(f"✅ Inspección guardada exitosamente. Cumplimiento: {porcentaje:.1f}%")

    # ------------------------------------------
    # PESTAÑA 2: HISTORIAL Y TRAZABILIDAD
    # ------------------------------------------
    with tab_historial:
        st.write("Consulta el historial de todas las inspecciones realizadas.")
        query_h = """
            SELECT r.id, t.nombre as Plantilla, r.fecha as Fecha, r.inspector as Inspector, 
                   r.empresa as Empresa, r.entidad_inspeccionada as Entidad, 
                   r.porcentaje_cumplimiento as Cumplimiento, r.estado as Estado, r.respuestas_json,
                   r.empresa_id, r.contrato_id
            FROM checklists_registros r
            JOIN checklists_templates t ON r.template_id = t.id
        """
        params_h = []
        conds_h = []
        if not is_master:
            conds_h.append("r.empresa_id = ?")
            params_h.append(st.session_state.empresa_id)
        elif filtros.get('empresa_id') and filtros.get('empresa_id') > 0:
            conds_h.append("r.empresa_id = ?")
            params_h.append(filtros['empresa_id'])

        if filtros.get('contrato_id'):
            conds_h.append("r.contrato_id = ?")
            params_h.append(filtros['contrato_id'])

        if conds_h: query_h += " WHERE " + " AND ".join(conds_h)
        query_h += " ORDER BY r.id DESC"

        df_hist = obtener_dataframe(DB_PATH, query_h, tuple(params_h))

        if df_hist.empty:
            st.info("Aún no hay inspecciones ejecutadas y registradas en la base de datos.")
        else:
            col_f1, col_f2 = st.columns(2)
            with col_f1: f_empresa_h = st.selectbox("Filtrar por Empresa:", ["Todas"] + df_hist['Empresa'].unique().tolist())
            with col_f2: f_estado_h = st.selectbox("Filtrar por Estado:", ["Todos", "Aprobado", "Rechazado"])

            df_hist_view = df_hist.copy()
            if f_empresa_h != "Todas": df_hist_view = df_hist_view[df_hist_view['Empresa'] == f_empresa_h]
            if f_estado_h != "Todos": df_hist_view = df_hist_view[df_hist_view['Estado'] == f_estado_h]

            # Formateamos visualmente para la tabla
            df_display = df_hist_view.copy()
            
            def style_status(val):
                color = "#10b981" if val == 'Aprobado' else "#ef4444"
                return f'<span style="background-color: {color}22; color: {color}; padding: 4px 12px; border-radius: 12px; font-weight: 600; font-size: 0.8rem; border: 1px solid {color}44;">{val}</span>'

            df_display['Cumplimiento'] = df_display['Cumplimiento'].apply(lambda x: f"{x:.1f}%")
            df_display['Estado'] = df_display['Estado'].apply(style_status)
            
            df_display_clean = df_display[['id', 'Fecha', 'Plantilla', 'Empresa', 'Entidad', 'Inspector', 'Cumplimiento', 'Estado']]

            st.write(df_display_clean.to_html(escape=False, index=False), unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)

            st.markdown("#### 🔎 Detalle de Inspección")
            det_id = st.selectbox("Seleccione el ID de la inspección para ver el detalle exacto:", ["-- Seleccione --"] + df_display['id'].tolist())

            if det_id != "-- Seleccione --":
                row_det = df_hist_view[df_hist_view['id'] == det_id].iloc[0]
                st.markdown(f"**Plantilla:** {row_det['Plantilla']} | **Entidad:** {row_det['Entidad']} | **Resultado:** {row_det['Cumplimiento']:.1f}%")

                respuestas_dict = json.loads(row_det['respuestas_json'])
                for ix_str, data_resp in respuestas_dict.items():
                    val = data_resp['respuesta']
                    if val == "Cumple": icon = "✅"
                    elif val == "No Cumple": icon = "❌"
                    else: icon = "➖"

                    st.markdown(f"> {icon} **{data_resp['pregunta']}**: `{val}`")


    # ------------------------------------------
    # PESTAÑA 3: DASHBOARD ANALÍTICO
    # ------------------------------------------
    with tab_dashboard:
        st.markdown("### 📊 Inteligencia de Hallazgos")
        
        query_dash = "SELECT r.respuestas_json, t.categoria, r.porcentaje_cumplimiento, r.fecha FROM checklists_registros r JOIN checklists_templates t ON r.template_id = t.id"
        params_d = []
        if not is_master:
            query_dash += " WHERE r.empresa_id = ?"
            params_d.append(st.session_state.empresa_id)
        elif filtros.get('empresa_id') and filtros.get('empresa_id') > 0:
            query_dash += " WHERE r.empresa_id = ?"
            params_d.append(filtros['empresa_id'])
            
        df_dash = obtener_dataframe(DB_PATH, query_dash, tuple(params_d))

        if not df_dash.empty:
            c_d1, c_d2 = st.columns([0.4, 0.6])
            
            with c_d1:
                # Radial Gauge de Cumplimiento
                avg_val = df_dash['porcentaje_cumplimiento'].mean()
                fig_gauge = px.pie(values=[avg_val, 100-avg_val], names=['Cumplimiento', 'Brecha'], 
                                  hole=0.7, color_discrete_sequence=['#10b981', '#1e293b'])
                fig_gauge.update_layout(showlegend=False, margin=dict(t=0, b=0, l=0, r=0), height=300,
                                        annotations=[dict(text=f"{avg_val:.1f}%", x=0.5, y=0.5, font_size=40, showarrow=False, font_color="white")])
                st.markdown("<div style='text-align:center;'><strong>Cumplimiento Global</strong></div>", unsafe_allow_html=True)
                st.plotly_chart(fig_gauge, use_container_width=True)

            with c_d2:
                # Tendencia de Cumplimiento
                df_dash['fecha'] = pd.to_datetime(df_dash['fecha'])
                df_trend = df_dash.groupby('fecha')['porcentaje_cumplimiento'].mean().reset_index()
                fig_trend = px.line(df_trend, x='fecha', y='porcentaje_cumplimiento', markers=True,
                                    title="Evolución de Cumplimiento", color_discrete_sequence=['#3b82f6'])
                fig_trend.update_layout(yaxis_range=[0, 105], template="plotly_dark")
                st.plotly_chart(fig_trend, use_container_width=True)

            st.divider()
            
            # Pareto de Fallas
            fallas = []
            for _, r in df_dash.iterrows():
                try:
                    pJson = json.loads(r['respuestas_json'])
                    for k, v in pJson.items():
                        if v['respuesta'] == 'No Cumple':
                            fallas.append({"Pregunta (Falla)": v['pregunta'], "Categoría": r['categoria']})
                except: pass
            
            if fallas:
                df_fallas = pd.DataFrame(fallas)
                conteo = df_fallas['Pregunta (Falla)'].value_counts().reset_index()
                conteo.columns = ['Falla', 'Frecuencia']
                conteo = conteo.head(10)
                
                fig_pareto = px.bar(conteo, x='Frecuencia', y='Falla', orientation='h', 
                                    title="Top 10 Hallazgos más Frecuentes (No Cumple)",
                                    color='Frecuencia', color_continuous_scale="Reds")
                fig_pareto.update_layout(yaxis={'categoryorder':'total ascending'}, template="plotly_dark")
                st.plotly_chart(fig_pareto, use_container_width=True)
            else:
                st.success("🎉 No se registran fallas críticas (100% cumplimiento en las inspecciones actuales).")
        else:
            st.info("Sin data suficiente para generar analítica predictiva.")
            

    # ------------------------------------------
    # PESTAÑA 4: ADMINISTRADOR DE PLANTILLAS
    # ------------------------------------------
    with tab_mantenedor:
        if st.session_state.get('role') not in ["Admin", "Cargador"]:
            st.error("🚫 No tienes permisos para administrar plantillas.")
        else:
            st.write("Crea, edita y gestiona las plantillas maestras (Formatos de Checklists) de la plataforma.")

            df_t = obtener_dataframe(DB_PATH, "SELECT id, nombre, categoria, preguntas_json FROM checklists_templates")

            if not df_t.empty:
                df_t['Cant. Preguntas'] = df_t['preguntas_json'].apply(lambda x: len(json.loads(x)) if pd.notna(x) else 0)
                st.dataframe(df_t[['id', 'nombre', 'categoria', 'Cant. Preguntas']], hide_index=True, use_container_width=True)
            else:
                st.info("No hay plantillas.")

            with st.expander("➕ Creador de Nueva Plantilla", expanded=False):
                with st.form("form_nueva_plantilla"):
                    n_nom = st.text_input("Nombre / Referencia de la Plantilla:")
                    n_cat = st.selectbox("Categoría Sugerida:", ["Vehículos y Maquinarias", "Equipos de Protección Personal", "Herramientas", "Instalaciones", "Otros"])
                    n_pregs = st.text_area("Preguntas (Ingresa una pregunta por línea):", height=200, help="Escribe cada punto de chequeo en un renglón distinto. El sistema los separará automáticamente.")

                    sub_np = st.form_submit_button("Crear Plantilla", type="primary")
                    if sub_np:
                        if not n_nom or not n_pregs.strip():
                            st.error("❌ El nombre y al menos una pregunta son obligatorios.")
                        else:
                            lista_final = [p.strip() for p in n_pregs.split("\n") if p.strip()]
                            ejecutar_query(DB_PATH, "INSERT INTO checklists_templates (nombre, categoria, preguntas_json) VALUES (?,?,?)", (n_nom, n_cat, json.dumps(lista_final)), commit=True)
                            st.success(f"✅ Plantilla '{n_nom}' creada con {len(lista_final)} preguntas.")
                            st.rerun()

            with st.expander("🗑️ Eliminar Plantilla", expanded=False):
                if not df_t.empty:
                    opt_del = {row['id']: row['nombre'] for _, row in df_t.iterrows()}
                    del_id = st.selectbox("Seleccionar Plantilla a Eliminar:", list(opt_del.keys()), format_func=lambda x: opt_del[x])
                    if st.button("🔴 Eliminar Definitivamente"):
                        ejecutar_query(DB_PATH, "DELETE FROM checklists_templates WHERE id=?", (del_id,), commit=True)
                        st.success("Plantilla eliminada.")
                        st.rerun()
