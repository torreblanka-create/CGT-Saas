import os
import re
from datetime import datetime

import pandas as pd
import streamlit as st

from src.infrastructure.archivos import obtener_ruta_planes_accion
from config.config import BASE_DATA_DIR, LOGO_APP, LOGO_CLIENTE, obtener_logo_cliente
from src.infrastructure.database import ejecutar_query, eliminar_registro_con_log, obtener_dataframe
from core.reports.generador_pdf import pdf_engine
from core.utils import is_valid_context, show_context_warning


def render_seguimiento_planes(db_path, filtros):
    st.markdown("<h2 style='color: var(--cgt-blue);'>🎯 Track central de Planes de Acción (Brechas)</h2>", unsafe_allow_html=True)
    st.write("Gestiona, prioriza y haz seguimiento a todos los planes de acción correctiva y de mejora en la organización.")
    st.divider()

    # Cargar datos base con filtros de alcance
    query_p = "SELECT * FROM planes_accion"
    params_p = []
    conds = []
    if filtros.get('empresa_id'):
        conds.append("empresa_id = ?")
        params_p.append(filtros['empresa_id'])
    if filtros.get('contrato_id'):
        conds.append("contrato_id = ?")
        params_p.append(filtros['contrato_id'])

    if conds: query_p += " WHERE " + " AND ".join(conds)
    df_bd = obtener_dataframe(db_path, query_p, tuple(params_p))
    # Convertir las fechas a tipo datetime de pandas para poder operar con ellas
    if not df_bd.empty:
        df_bd['fecha_inicio'] = pd.to_datetime(df_bd['fecha_inicio'], errors='coerce')
        df_bd['fecha_cierre'] = pd.to_datetime(df_bd['fecha_cierre'], errors='coerce')

    df_evidencias = obtener_dataframe(db_path, "SELECT * FROM evidencias_planes")
    if df_evidencias.empty:
        df_evidencias = pd.DataFrame(columns=['plan_id', 'descripcion', 'fecha_subida', 'ruta_archivo'])


    lista_planes_existentes = sorted(df_bd['codigo_plan'].unique().tolist()) if not df_bd.empty else []

    # --- MÉTRICAS DE RESUMEN ---
    if not df_bd.empty:
        total_acciones = len(df_bd)
        cerradas_total = len(df_bd[df_bd['estado'] == 'Cerrado'])
        abiertas_total = total_acciones - cerradas_total

        hoy = pd.Timestamp.now().normalize()
        atrasadas = len(df_bd[(df_bd['estado'] == 'Abierto') & (df_bd['fecha_cierre'] < hoy)])

        # Estilo Dashboard Custom
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("📂 Maestros de Plan", len(lista_planes_existentes))
        c2.metric("📋 Total Tareas", total_acciones)
        c3.metric("⏳ Acciones Abiertas", abiertas_total)
        c4.metric("🚨 Tareas Atrasadas", atrasadas)
        st.divider()

    # --- FILTROS LOCALES DEL MÓDULO ---
    with st.expander("🔍 Buscador y Filtros Avanzados", expanded=False):
        c_f1, c_f2 = st.columns(2)
        with c_f1:
            filtro_estado = st.selectbox("Estado de la Acción", ["Todos", "Abierto", "Cerrado"])
        with c_f2:
            resp_list = ["Todos"] + sorted(df_bd['responsable'].dropna().unique().tolist()) if not df_bd.empty else ["Todos"]
            filtro_responsable = st.selectbox("Responsable Asignado", resp_list)

    if not df_bd.empty:
        df_filtrado = df_bd.copy()
        if filtro_estado != "Todos": df_filtrado = df_filtrado[df_filtrado['estado'] == filtro_estado]
        if filtro_responsable != "Todos": df_filtrado = df_filtrado[df_filtrado['responsable'] == filtro_responsable]
    else:
        df_filtrado = df_bd

    tab_activos, tab_nuevo, tab_evidencias = st.tabs(["🚦 Hub de Planes de Acción", "➕ Asignar Nueva Acción", "📎 Central de Evidencias"])

    # --- NUEVA ACCIÓN ---
    with tab_nuevo:
        if not is_valid_context(filtros):
            show_context_warning()
        else:
            with st.container(border=True):
                st.markdown("#### Formulario de Asignación de Acción")
                with st.form("form_nuevo_plan", clear_on_submit=True):
                    c_p1, c_p2 = st.columns(2)
                    with c_p1:
                        opcion_plan = st.selectbox("Perteneciente al Master Plan:", ["-- Crear Nuevo Master Plan --"] + lista_planes_existentes)
                    with c_p2:
                        nuevo_plan = st.text_input("Definir nombre si es nuevo:")

                    nombre_plan = nuevo_plan if opcion_plan == "-- Crear Nuevo Master Plan --" else opcion_plan

                    st.markdown("---")
                    c1, c2 = st.columns(2)
                    with c1:
                        foco = st.text_input("Foco de Intervención / Área", placeholder="Ej: Operación Mina")
                        accion = st.text_area("Descripción de la Brecha / Acción Requerida")
                        responsable = st.text_input("Responsable Principal")
                    with c2:
                        kpi = st.text_input("Entregable / Medio de Verificación", placeholder="Evidencia Objetiva")
                        f_ini = st.date_input("Fecha Inicio", value=datetime.now())
                        f_cie = st.date_input("Fecha Límite (Deadline)")

                    if st.form_submit_button("🚀 Emitir Acción", type="primary", use_container_width=True):
                        if nombre_plan and accion:
                            e_id = filtros.get('empresa_id', 0)
                            c_id = filtros.get('contrato_id', 0)
                            ejecutar_query(db_path, """
                                INSERT INTO planes_accion 
                                (codigo_plan, foco_intervencion, accion, responsable, fecha_inicio, fecha_cierre, kpi, empresa_id, contrato_id) 
                                VALUES (?,?,?,?,?,?,?,?,?)
                            """, (nombre_plan, foco, accion, responsable, f_ini, f_cie, kpi, e_id, c_id), commit=True)
                            st.success(f"✅ Tarea asignada exitosamente al plan: {nombre_plan}")
                            st.rerun()

    # --- TARJETAS ACTIVAS ---
    with tab_activos:
        if df_filtrado.empty:
            st.info("No hay planes en seguimiento activo con esos filtros.")
        else:
            hoy = pd.Timestamp.now().normalize()

            for plan, grupo_filtrado in df_filtrado.groupby('codigo_plan'):
                grupo_padre = df_bd[df_bd['codigo_plan'] == plan]
                total = len(grupo_padre)
                cerradas = len(grupo_padre[grupo_padre['estado'] == 'Cerrado'])
                progreso = int((cerradas/total)*100) if total > 0 else 0

                # Color progress bar custom based on progression
                color_prog = "green" if progreso == 100 else "orange" if progreso > 50 else "red"

                with st.expander(f"📁 Master Plan: {plan}", expanded=True):
                    # Cabecera interactiva del plan
                    col_p1, col_p2, col_p3, col_p4 = st.columns([1, 2, 1, 1])
                    with col_p1:
                        st.markdown(f"**Progreso Global: {progreso}%**")
                    with col_p2:
                        st.progress(progreso)
                    with col_p3:
                        pdf_data = pdf_engine.generar('PLAN_ACCION', plan, grupo_padre, df_evidencias, LOGO_APP, obtener_logo_cliente(st.session_state.filtros.get('empresa_nom')))
                        st.download_button("📄 PDF de Status", pdf_data, f"Status_{plan}.pdf", "application/pdf", key=f"pdf_{plan}", use_container_width=True)

                    with col_p4:
                        if st.session_state.role == 'Admin':
                            with st.popover("⚙️ Ajustes"):
                                if st.button("✏️ Renombrar", key=f"rename_btn_{plan}"):
                                    st.session_state[f"renombrando_{plan}"] = not st.session_state.get(f"renombrando_{plan}", False)
                                if st.button("🗑️ Destruir Plan", key=f"del_plan_{plan}", type="secondary"):
                                    ids = grupo_padre['id'].tolist()
                                    if ids:
                                        placeholders = ','.join(['?']*len(ids))
                                        ejecutar_query(db_path, f"DELETE FROM evidencias_planes WHERE plan_id IN ({placeholders})", tuple(ids), commit=True)
                                    ejecutar_query(db_path, "DELETE FROM planes_accion WHERE codigo_plan=?", (plan,), commit=True)
                                    st.rerun()

                    # Renombrado de Plan
                    if st.session_state.get(f"renombrando_{plan}", False):
                        with st.form(f"form_rename_{plan}"):
                            nuevo_nombre_plan = st.text_input("Nuevo nombre para Master Plan:", value=plan)
                            if st.form_submit_button("Guardar Cambios"):
                                if nuevo_nombre_plan and nuevo_nombre_plan != plan:
                                    ejecutar_query(db_path, "UPDATE planes_accion SET codigo_plan=? WHERE codigo_plan=?", (nuevo_nombre_plan, plan), commit=True)
                                    st.session_state[f"renombrando_{plan}"] = False
                                    st.rerun()
                                else:
                                    st.warning("Nombre idéntico al actual.")

                    st.markdown("---")

                    # Iterar acciones de este plan
                    for _, row in grupo_filtrado.iterrows():
                        estado = row['estado']
                        if estado == 'Cerrado':
                            est_color = "#dcfce7"
                            ico_estado = "✅"
                            txt_estado = "Cerrada"
                        else:
                            fcierre = row['fecha_cierre']
                            if pd.isna(fcierre):
                                est_color = "#e0f2fe"
                                ico_estado = "🔵"
                                txt_estado = "Planificada"
                            else:
                                dias_restantes = (fcierre - hoy).days
                                if dias_restantes < 0:
                                    est_color = "#fee2e2"
                                    ico_estado = "💥"
                                    txt_estado = f"Vencida ({-dias_restantes} d)"
                                elif dias_restantes <= 7:
                                    est_color = "#fef08a"
                                    ico_estado = "⏳"
                                    txt_estado = f"Crítico (Vence en {dias_restantes} d)"
                                else:
                                    est_color = "#e0f2fe"
                                    ico_estado = "🔵"
                                    txt_estado = f"En plazo ({dias_restantes} d)"

                        with st.container(border=True):
                            tc1, tc2, tc3 = st.columns([6, 2, 2])
                            with tc1:
                                st.markdown(f"**ID-{row['id']}**: {row['accion']}")
                                st.caption(f"**Asignada a:** {row['responsable']} | **Foco:** {row['foco_intervencion']}")
                            with tc2:
                                st.markdown(f"<div style='background-color:{est_color}; color:#000; padding:4px 8px; border-radius:4px; font-weight:bold; font-size:13px; text-align:center;'>{ico_estado} {txt_estado}</div>", unsafe_allow_html=True)
                                st.caption(f"Cierre: {row['fecha_cierre'].strftime('%d-%m-%Y') if pd.notnull(row['fecha_cierre']) else 'N/A'}")
                            with tc3:
                                # Mini botones de acción
                                if estado == 'Abierto':
                                    if st.button("✔️ Cerrar Tarea", key=f"close_{row['id']}", use_container_width=True, type="primary"):
                                        ejecutar_query(db_path, "UPDATE planes_accion SET estado='Cerrado' WHERE id=?", (row['id'],), commit=True)
                                        st.rerun()
                                else:
                                    if st.button("🔄 Reabrir Tarea", key=f"reopen_{row['id']}", use_container_width=True):
                                        ejecutar_query(db_path, "UPDATE planes_accion SET estado='Abierto' WHERE id=?", (row['id'],), commit=True)
                                        st.rerun()

                                with st.popover("⚙️ Editar/Eliminar"):
                                    if st.button("✏️ Editar", key=f"edit_{row['id']}", use_container_width=True):
                                        st.session_state[f"editando_{row['id']}"] = not st.session_state.get(f"editando_{row['id']}", False)
                                    if st.session_state.role == 'Admin':
                                        if st.button("🗑️ Borrar", key=f"dela_{row['id']}", use_container_width=True):
                                            eliminar_registro_con_log(db_path, "evidencias_planes", "plan_id", row['id'], st.session_state.user_login)
                                            eliminar_registro_con_log(db_path, "planes_accion", "id", row['id'], st.session_state.user_login)
                                            st.rerun()

                            # Lógica de Edición en línea
                            if st.session_state.get(f"editando_{row['id']}", False):
                                st.markdown("**(Editando Parámetros)**")
                                with st.form(f"form_edit_{row['id']}"):
                                    ne_acc = st.text_area("Acción a intervenir", row['accion'])
                                    ne_resp = st.text_input("Nuevo Encargado", row['responsable'])
                                    d_cie_val = row['fecha_cierre'].date() if pd.notnull(row['fecha_cierre']) else datetime.now().date()
                                    ne_cie = st.date_input("Modificar Deadline", value=d_cie_val)

                                    if st.form_submit_button("Reescribir Tarea", type="primary"):
                                        ejecutar_query(db_path, "UPDATE planes_accion SET accion=?, responsable=?, fecha_cierre=? WHERE id=?",
                                                     (ne_acc, ne_resp, ne_cie, row['id']), commit=True)
                                        st.session_state[f"editando_{row['id']}"] = False
                                        st.rerun()

                            # Manejo visual de evidencias
                            evs_act = df_evidencias[df_evidencias['plan_id'] == row['id']]
                            if not evs_act.empty:
                                for ev_idx, ev_row in evs_act.iterrows():
                                    if pd.notna(ev_row.get('ruta_archivo')) and os.path.exists(ev_row['ruta_archivo']):
                                        st.markdown(f"- 📎 **Evidencia:** {ev_row['descripcion']} (Asociada al entregable)")
                                    else:
                                        st.markdown(f"- ⚠️ **Evidencia Perdida:** {ev_row['descripcion']}")

    # --- CARGA EVIDENCIAS ---
    with tab_evidencias:
        if not is_valid_context(filtros):
            show_context_warning()
        else:
            if not df_bd.empty:
                st.markdown("### Repositorio de Evidencias de Cierre")
                p_sel = st.selectbox("1. Selecciona el Master Plan Objetivo:", lista_planes_existentes)
                acciones_abiertas = df_bd[(df_bd['codigo_plan'] == p_sel) & (df_bd['estado'] == 'Abierto')]

                if not acciones_abiertas.empty:
                    acciones_abiertas['label'] = "ID " + acciones_abiertas['id'].astype(str) + ": " + acciones_abiertas['accion'].str[:80] + "..."
                    a_sel = st.selectbox("2. Selecciona la Tarea Específica:", acciones_abiertas['label'].tolist())

                    with st.form("form_ev", clear_on_submit=True):
                        desc_base = st.text_input("Asunto de las evidencias (Ej: Certificados, fotos reparación, firma manual)")
                        archivos = st.file_uploader("Adjuntos Oficiales (PDF, JPG, PNG)", type=['pdf','jpg','png','jpeg'], accept_multiple_files=True)
                        if st.form_submit_button("📎 Consignar Evidencias al Sistema", type="primary", use_container_width=True):
                            if desc_base and archivos:
                                id_a = a_sel.split(":")[0].replace("ID ","")
                                kpi_str = acciones_abiertas[acciones_abiertas['id'].astype(str) == id_a]['kpi'].values[0]
                                kpi_limpio = "Evidencia"
                                if pd.notna(kpi_str) and str(kpi_str).strip():
                                    kpi_limpio = re.sub(r'[^a-zA-Z0-9]', '_', str(kpi_str).strip())

                                emp_curr = filtros.get('empresa_nom', 'EMPRESA_GLOBAL')
                                con_curr = filtros.get('contrato_nom', 'GLOBAL')
                                path_dir = obtener_ruta_planes_accion(emp_curr, con_curr, p_sel)
                                fecha_actualStr = datetime.now().strftime('%Y%m%d_%H%M%S')

                                guardados = 0
                                for idx, f in enumerate(archivos):
                                    ext = os.path.splitext(f.name)[1]
                                    nombre_archivo = f"{kpi_limpio}_{fecha_actualStr}_{idx}{ext}"
                                    path_f = os.path.join(path_dir, nombre_archivo)

                                    with open(path_f, "wb") as output_file:
                                        output_file.write(f.getbuffer())

                                    desc_final = f"{desc_base} - {f.name}" if len(archivos) > 1 else desc_base

                                    ejecutar_query(db_path, "INSERT INTO evidencias_planes (plan_id, fecha_subida, descripcion, ruta_archivo) VALUES (?,?,?,?)",
                                                 (id_a, datetime.now().date(), desc_final, path_f), commit=True)
                                    guardados += 1
                                if guardados > 0:
                                    st.success(f"✅ {guardados} archivos almacenados exitósamente. Trazabilidad preservada.")
                                st.rerun()
                            else:
                                st.warning("Por favor define el asunto y adjunta archivos antes de subir.")
                else:
                    st.info("Genial, no quedan tareas pendientes ni abiertas en este plan base.")
