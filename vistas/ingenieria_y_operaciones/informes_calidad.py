import json
import os
import sqlite3
from datetime import date, datetime

import pandas as pd
import plotly.express as px
import streamlit as st

from src.infrastructure.archivos import obtener_ruta_informes_calidad
from config.config import (
    BASE_DATA_DIR,
    DB_PATH,
    LOGO_APP,
    LOGO_CLIENTE,
    obtener_logo_cliente,
)
from src.infrastructure.database import ejecutar_query, obtener_dataframe
from core.reports.generador_pdf import pdf_engine
from core.reports.templates import TEMPLATE_CONFIG
from core.utils import is_valid_context, show_context_warning


def render_informes_calidad(DB_PATH, filtros):
    # --- MÉTRICAS DE GESTIÓN DE CALIDAD ---
    is_master = st.session_state.role == "Global Admin"
    q_stats = "SELECT COUNT(*) as total, COUNT(DISTINCT tecnico) as techs, COUNT(DISTINCT template_id) as tpls FROM historial_informes_calidad"
    p_s = []
    if not is_master:
        q_stats += " WHERE empresa_id = ?"
        p_s.append(st.session_state.empresa_id)
    elif filtros.get('empresa_id') and filtros.get('empresa_id') > 0:
        q_stats += " WHERE empresa_id = ?"
        p_s.append(filtros['empresa_id'])
    
    df_qc = obtener_dataframe(DB_PATH, q_stats, tuple(p_s))
    total_r = df_qc['total'].iloc[0] if not df_qc.empty else 0
    total_t = df_qc['techs'].iloc[0] if not df_qc.empty else 0
    total_tpls = df_qc['tpls'].iloc[0] if not df_qc.empty else 0

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown(f"""
            <div style='background: #F5F3F0; color: #1F2937; padding: 18px; border-radius: 12px; border-left: 5px solid #06b6d4; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);'>
                <p style='color: #94a3b8; font-size: 0.75rem; margin: 0; text-transform: uppercase; font-weight: 700;'>Informes Generados</p>
                <p style='color: white; font-size: 1.8rem; font-weight: 800; margin: 5px 0 0 0;'>{total_r}</p>
            </div>
        """, unsafe_allow_html=True)
    with m2:
        st.markdown(f"""
            <div style='background: #F5F3F0; color: #1F2937; padding: 18px; border-radius: 12px; border-left: 5px solid #a855f7; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);'>
                <p style='color: #94a3b8; font-size: 0.75rem; margin: 0; text-transform: uppercase; font-weight: 700;'>Técnicos Activos</p>
                <p style='color: white; font-size: 1.8rem; font-weight: 800; margin: 5px 0 0 0;'>{total_t}</p>
            </div>
        """, unsafe_allow_html=True)
    with m3:
        st.markdown(f"""
            <div style='background: #F5F3F0; color: #1F2937; padding: 18px; border-radius: 12px; border-left: 5px solid #ec4899; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);'>
                <p style='color: #94a3b8; font-size: 0.75rem; margin: 0; text-transform: uppercase; font-weight: 700;'>Plantillas en Uso</p>
                <p style='color: white; font-size: 1.8rem; font-weight: 800; margin: 5px 0 0 0;'>{total_tpls}</p>
            </div>
        """, unsafe_allow_html=True)
    with m4:
        st.markdown(f"""
            <div style='background: #F5F3F0; color: #1F2937; padding: 18px; border-radius: 12px; border-left: 5px solid #10b981; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);'>
                <p style='color: #94a3b8; font-size: 0.75rem; margin: 0; text-transform: uppercase; font-weight: 700;'>Disponibilidad PDF</p>
                <p style='color: #10b981; font-size: 1.3rem; font-weight: 800; margin: 5px 0 0 0;'>100% Online</p>
            </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Pestañas principales
    t1, t2, t3 = st.tabs(["🚀 Generar Nuevo Informe", "📚 Historial de Informes", "🛠️ Constructor de Plantillas"])

    # Cargar plantillas desde DB + Hardcoded
    try:
        df_db_tpl = obtener_dataframe(DB_PATH, "SELECT id_str, nombre, descripcion, estructura_json FROM informes_templates WHERE activo=1")
    except:
        df_db_tpl = pd.DataFrame() # Si falla la migración en vivo

    custom_templates = {}
    if not df_db_tpl.empty:
        for _, r in df_db_tpl.iterrows():
            try:
                custom_templates[r['id_str']] = {
                    "nombre": r['nombre'],
                    "descripcion": r['descripcion'],
                    "secciones": json.loads(r['estructura_json'])
                }
            except: pass

    combined_templates = {**TEMPLATE_CONFIG, **custom_templates}

    # Inicializar estado de edición si no existe
    if 'edit_report_data' not in st.session_state:
        st.session_state.edit_report_data = None

    # ---------------- TAB 1: GENERACIÓN ----------------
    with t1:
        if not is_valid_context(filtros):
            show_context_warning()
        else:
            # Selector de Plantilla
            template_options = {k: v['nombre'] for k, v in combined_templates.items()}
            sel_template_id = st.selectbox("Selecciona una Plantilla de Informe:",
                                         options=list(template_options.keys()),
                                         format_func=lambda x: template_options[x],
                                         index=0 if not st.session_state.edit_report_data else list(template_options.keys()).index(st.session_state.edit_report_data.get('template_id', 'generico')))

            template_data = combined_templates[sel_template_id]
            st.info(f"📋 **{template_data['nombre']}**: {template_data['descripcion']}")

            if st.session_state.edit_report_data:
                if st.button("❌ Cancelar Edición y volver a Nuevo"):
                    st.session_state.edit_report_data = None
                    st.rerun()

            with st.form("form_informe_calidad", clear_on_submit=False):
                datos_prellenos = st.session_state.edit_report_data.get('datos_json', {}) if st.session_state.edit_report_data else {}

                st.markdown("### 1. Datos del Informe")
                c1, c2, c3 = st.columns(3)
                with c1:
                    titulo = st.text_input("Título del Informe", value=datos_prellenos.get('titulo', ''), placeholder="Ej: Ensamblado de Copla Minera")
                    empresa = st.text_input("Empresa", value=datos_prellenos.get('empresa', st.session_state.filtros.get('empresa_nom', 'N/A')))
                with c2:
                    tecnico = st.text_input("Técnico a cargo", value=datos_prellenos.get('tecnico', st.session_state.username))
                    contrato = st.text_input("Contrato o Faena", value=datos_prellenos.get('contrato', st.session_state.filtros.get('contrato_nom', 'SIN_CONTRATO')))
                with c3:
                    st.info("💡 Estas fotografías y datos generarán un reporte ejecutivo para ser firmado por Calidad/Supervisión.")

                if sel_template_id == "generico":
                    st.markdown("### 2. Descripción de la Actividad")
                    descripcion = st.text_area("Detalla aquí los pasos realizados...", value=datos_prellenos.get('descripcion', ''), height=150)

                    st.markdown("### 3. Registro Fotográfico (Paso a Paso)")
                    st.caption("Sube hasta 10 fotografías en orden cronológico.")
                    fotos_data = []
                    for row_idx in range(4):
                        cols = st.columns(3)
                        for col_idx in range(3):
                            foto_num = (row_idx * 3) + col_idx + 1
                            if foto_num > 10: break
                            with cols[col_idx]:
                                f = st.file_uploader(f"Subir Foto {foto_num}", type=["jpg", "png", "jpeg"], key=f"fu{foto_num}")
                                d = st.text_input(f"Descripción F{foto_num}:", value=datos_prellenos.get(f"desc_{foto_num}", ""), key=f"dt{foto_num}")
                                if f: fotos_data.append({"file_obj": f, "desc": d})
                else:
                    # Lógica para Plantillas Específicas (Mufa, etc)
                    input_data = {} # Para guardar en JSON
                    for sec in template_data['secciones']:
                        st.divider()
                        st.markdown(f"#### {sec['titulo']}")
                        if sec.get('type') == 'checklist':
                            for item_idx, item_label in enumerate(sec['items']):
                                cc1, cc2, cc3 = st.columns([2, 1, 1])
                                with cc1: st.write(f"**{item_label}**")
                                with cc2:
                                    f_check = st.file_uploader("Evidencia", type=["jpg", "png", "jpeg"], key=f"fu_{sec['id']}_{item_idx}")
                                    if f_check: input_data[f"foto_obj_{sec['id']}_{item_idx}"] = f_check
                                with cc3:
                                    ok_val = st.checkbox("OK", value=datos_prellenos.get(f"ok_{sec['id']}_{item_idx}", False), key=f"ok_{sec['id']}_{item_idx}")
                                    input_data[f"ok_{sec['id']}_{item_idx}"] = ok_val
                        else:
                            cols = st.columns(2)
                            for i, cam in enumerate(sec['campos']):
                                with cols[i % 2]:
                                    v_def = datos_prellenos.get(cam['id'], '')
                                    if cam['type'] == 'text':
                                        input_data[cam['id']] = st.text_input(cam['label'], value=v_def, key=f"in_{cam['id']}")
                                    elif cam['type'] == 'date':
                                        try:
                                            v_date = date.fromisoformat(v_def) if isinstance(v_def, str) and v_def else date.today()
                                        except: v_date = date.today()
                                        input_data[cam['id']] = st.date_input(cam['label'], value=v_date, key=f"in_{cam['id']}")
                                    elif cam['type'] == 'multiselect':
                                        input_data[cam['id']] = st.multiselect(cam['label'], options=cam['options'], default=v_def if v_def else [], key=f"in_{cam['id']}")

                st.markdown("<br>", unsafe_allow_html=True)
                btn_generar = st.form_submit_button("🚀 Generar y Guardar Informe PDF", type="primary", use_container_width=True)

        if btn_generar:
            if not titulo:
                st.error("❌ El Título es obligatorio.")
            else:
                with st.spinner("Procesando Reporte..."):
                    storage_dir = obtener_ruta_informes_calidad(empresa, contrato)
                    temp_dir = os.path.join(BASE_DATA_DIR, "temp_images_calidad")
                    os.makedirs(temp_dir, exist_ok=True)

                    fotos_procesadas = []
                    datos_finales = {"titulo": titulo, "empresa": empresa, "contrato": contrato, "tecnico": tecnico}

                    if sel_template_id == "generico":
                            datos_finales["descripcion"] = descripcion
                            for i, f_item in enumerate(fotos_data):
                                f_ext = os.path.splitext(f_item["file_obj"].name)[1]
                                t_path = os.path.join(temp_dir, f"temp_{i}{f_ext}")
                                with open(t_path, "wb") as f: f.write(f_item["file_obj"].getbuffer())
                                fotos_procesadas.append({"path": t_path, "descripcion": f_item["desc"]})
                    else:
                        # Procesar fotos de checklist
                        for k, v in input_data.items():
                            if k.startswith("foto_obj_") and v is not None:
                                f_ext = os.path.splitext(v.name)[1]
                                t_path = os.path.join(temp_dir, f"{k}{f_ext}")
                                with open(t_path, "wb") as f: f.write(v.getbuffer())
                                # Mapear a la ruta en datos_finales para el generador PDF
                                datos_finales[k.replace("obj_", "")] = t_path
                            elif not k.startswith("foto_obj_"):
                                datos_finales[k] = v if not isinstance(v, (datetime, date, pd.Timestamp)) else str(v)

                    try:
                        pdf_bytes = pdf_engine.generar('CALIDAD', datos_finales, fotos_procesadas, LOGO_APP, obtener_logo_cliente(st.session_state.filtros.get('empresa_nom')), template_id=sel_template_id)
                        file_name_pdf = f"Inf_{sel_template_id}_{titulo.replace(' ', '_')}_{datetime.now().strftime('%m%d%H%M')}.pdf"
                        final_pdf_path = os.path.join(storage_dir, file_name_pdf)
                        with open(final_pdf_path, "wb") as pf: pf.write(pdf_bytes)

                        emp_id = st.session_state.filtros.get('empresa_id', 0)
                        con_id = st.session_state.filtros.get('contrato_id', 0)

                        # Limpiar campos de fotos de archivo antes de guardar JSON
                        json_storage = {k:v for k,v in datos_finales.items() if not str(v).startswith(temp_dir)}

                        query_ins = '''
                            INSERT INTO historial_informes_calidad (fecha, titulo, tecnico, empresa, contrato, ruta_archivo, empresa_id, contrato_id, template_id, datos_json) 
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        '''
                        params_ins = (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), titulo, tecnico, empresa, contrato, final_pdf_path, emp_id, con_id, sel_template_id, json.dumps(json_storage))
                        ejecutar_query(DB_PATH, query_ins, params_ins, commit=True)

                        st.success("✅ Informe Generado y Guardado Correctamente.")
                        st.download_button("📥 Descargar PDF", data=pdf_bytes, file_name=file_name_pdf, mime="application/pdf", type="primary")
                        st.session_state.edit_report_data = None # Limpiar edición
                    except Exception as e:
                        st.error(f"Error: {e}")

                    # Limpieza
                    for f in fotos_procesadas:
                        if os.path.exists(f["path"]): os.remove(f["path"])
                    for k,v in datos_finales.items():
                         if str(v).startswith(temp_dir) and os.path.exists(v): os.remove(v)


    # ---------------- TAB 2: HISTORIAL ----------------
    with t2:
        st.markdown("### 📚 Base de Datos de Informes de Calidad")

        try:
            # Filtro de historial por empresa/contrato de forma segura
            is_master = st.session_state.role == "Global Admin"
            query_hist = "SELECT * FROM historial_informes_calidad"
            condiciones = []
            params_h = []

            if not is_master:
                condiciones.append("empresa_id = ?")
                params_h.append(st.session_state.empresa_id)
            elif st.session_state.filtros.get('empresa_id') != 0:
                condiciones.append("empresa_id = ?")
                params_h.append(st.session_state.filtros['empresa_id'])

            if st.session_state.filtros.get('contrato_id') != 0:
                condiciones.append("contrato_id = ?")
                params_h.append(st.session_state.filtros['contrato_id'])

            if condiciones:
                query_hist += " WHERE " + " AND ".join(condiciones)
            query_hist += " ORDER BY id DESC"

            df_historial = obtener_dataframe(DB_PATH, query_hist, tuple(params_h))
        except Exception as e:
            df_historial = pd.DataFrame()
            st.error(f"⚠️ Error cargando el historial: {e}")

        if df_historial.empty:
            st.info("Aún no se han generado informes de calidad en el sistema.")
        else:
            # Gráficos de Historial
            c_h1, c_h2 = st.columns(2)
            with c_h1:
                df_counts = df_historial['tecnico'].value_counts().reset_index()
                fig_techs = px.bar(df_counts, x='tecnico', y='count', title="Informes por Técnico", color='count', color_continuous_scale="Purples")
                fig_techs.update_layout(template="plotly_dark", showlegend=False)
                st.plotly_chart(fig_techs, use_container_width=True)
            with c_h2:
                df_tpl_counts = df_historial['template_id'].value_counts().reset_index()
                fig_tpls = px.pie(df_tpl_counts, names='template_id', values='count', title="Distribución por Plantilla", hole=0.4)
                fig_tpls.update_layout(template="plotly_dark")
                st.plotly_chart(fig_tpls, use_container_width=True)

            # Resumen en tabla
            df_resumen = df_historial[['id', 'fecha', 'titulo', 'tecnico', 'empresa', 'template_id']]
            st.write(df_resumen.to_html(escape=False, index=False), unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)

            st.markdown("#### 📥 Acciones sobre Informes")
            # Para evitar que descargar cientos de items abrume, usamos un selectbox o paginación sencilla
            lista_opciones = df_historial.apply(lambda row: f"ID {row['id']} - {row['titulo']} ({row['fecha']})", axis=1).tolist()
            informe_seleccionado = st.selectbox("Selecciona un informe del historial:", lista_opciones)

            if informe_seleccionado:
                id_sel = int(informe_seleccionado.split(" ")[1])
                registro = df_historial[df_historial['id'] == id_sel].iloc[0]
                ruta_pdf = registro['ruta_archivo']

                c_d1, c_d2, c_d3 = st.columns([1, 1, 1])
                with c_d1:
                    if os.path.exists(ruta_pdf):
                        with open(ruta_pdf, "rb") as pdf_file:
                            pdf_data = pdf_file.read()
                        st.download_button(label=f"📄 Descargar PDF", data=pdf_data, file_name=os.path.basename(ruta_pdf), mime="application/pdf")
                    else: st.error("❌ Archivo no encontrado.")

                with c_d2:
                    if st.button("✏️ Editar Informe (Pre-llenar)", key=f"edit_{id_sel}", use_container_width=True):
                        try:
                            datos_cargados = json.loads(registro['datos_json']) if registro['datos_json'] else {}
                            st.session_state.edit_report_data = {
                                "id": id_sel,
                                "template_id": registro['template_id'] if registro['template_id'] else 'generico',
                                "datos_json": datos_cargados
                            }
                            st.success("✅ Datos cargados en la pestaña 'Generar'.")
                            st.info("Nota: Las fotografías deben ser subidas nuevamente por seguridad.")
                        except: st.error("Error cargando datos de edición.")

                with c_d3:
                    if is_master:
                        if st.button("🗑️ Eliminar Reporte", key=f"del_{id_sel}", type="primary", use_container_width=True):
                            try:
                                ejecutar_query(DB_PATH, "DELETE FROM historial_informes_calidad WHERE id = ?", (id_sel,), commit=True)
                                if os.path.exists(ruta_pdf): os.remove(ruta_pdf)
                                st.success("Reporte eliminado de la base de datos y servidor.")
                                st.rerun()
                            except Exception as e: st.error(f"Error eliminando: {e}")
                    else:
                        st.caption("Solo administradores pueden eliminar reportes.")

    # ---------------- TAB 3: CONSTRUCTOR DE PLANTILLAS ----------------
    with t3:
        if st.session_state.get('role') not in ["Admin", "Global Admin", "Cargador"]:
            st.error("🚫 No tienes permisos para crear o editar plantillas.")
        else:
            st.markdown("### 🏗️ Generador Dinámico de Plantillas (Report Builder)")
            st.info("Crea tus propios formatos de informe sin modificar el código fuente. Agrega secciones de campos de texto, o listas de chequeo con fotografía y firmas.")

            if 'builder_secs' not in st.session_state:
                st.session_state.builder_secs = []

            c_b1, c_b2 = st.columns([1, 2])
            with c_b1:
                with st.container(border=True):
                    st.markdown("#### Meta-Datos")
                    tpl_id = st.text_input("ID Interno (sin espacios)", placeholder="ej: insp_bomba")
                    tpl_nom = st.text_input("Nombre de la Plantilla", placeholder="Ej: Inspección Estándar")
                    tpl_desc = st.text_area("Descripción", placeholder="Propósito del reporte.")

                    st.markdown("#### Agregar Secciones")
                    if st.button("➕ Sección de Formulario", use_container_width=True):
                        st.session_state.builder_secs.append({"id": f"s_{len(st.session_state.builder_secs)}", "titulo": "", "type": "form", "campos": []})
                        st.rerun()
                    if st.button("➕ Sección Checklist (c/Foto)", use_container_width=True):
                        st.session_state.builder_secs.append({"id": f"s_{len(st.session_state.builder_secs)}", "titulo": "", "type": "checklist", "items": []})
                        st.rerun()

                    st.divider()
                    if st.button("💾 Guardar Plantilla", type="primary", use_container_width=True):
                        if not tpl_id or not tpl_nom:
                            st.error("ID y Nombre son obligatorios.")
                        else:
                            sec_finales = []
                            for sec in st.session_state.builder_secs:
                                s_dict = {"id": sec["id"], "titulo": sec["titulo"]}
                                if sec["type"] == "form":
                                    s_dict["campos"] = []
                                    s_dict["type"] = "form"
                                    for c in sec["campos"]:
                                        if c["label"].strip():
                                            s_dict["campos"].append({"id": c["id"], "label": c["label"], "type": c["type"]})
                                elif sec["type"] == "checklist":
                                    s_dict["type"] = "checklist"
                                    s_dict["items"] = [it for it in sec["items"] if it.strip()]
                                sec_finales.append(s_dict)

                            emp_id = st.session_state.filtros.get('empresa_id', 0)
                            try:
                                ejecutar_query(DB_PATH, "INSERT OR REPLACE INTO informes_templates (id_str, nombre, descripcion, estructura_json, empresa_id) VALUES (?,?,?,?,?)",
                                               (tpl_id.replace(" ", "_").lower(), tpl_nom, tpl_desc, json.dumps(sec_finales), emp_id), commit=True)
                                st.success(f"Plantilla '{tpl_nom}' guardada.")
                                st.session_state.builder_secs = []
                            except Exception as e: st.error(f"Error guardando: {e}")

            with c_b2:
                st.markdown("#### Estructura Actual del Documento")
                if not st.session_state.builder_secs:
                    st.caption("El documento está vacío. Agrega una sección desde la izquierda para comenzar a construir el PDF.")
                else:
                    for i, sec in enumerate(st.session_state.builder_secs):
                        with st.expander(f"Sección {i+1}: {sec.get('titulo', 'Sin Título')}", expanded=True):
                            sec["titulo"] = st.text_input(f"Título de la Sección", value=sec["titulo"], key=f"t_{i}")

                            if sec["type"] == "form":
                                st.caption("Campos de Formulario (Textos o Fechas):")
                                for j, c in enumerate(sec["campos"]):
                                    col1, col2 = st.columns([3, 1])
                                    c["label"] = col1.text_input("Pregunta / Label", value=c["label"], key=f"l_{i}_{j}")
                                    c["type"] = col2.selectbox("Tipo de Dato", ["text", "date"], index=0 if c["type"]=="text" else 1, key=f"ty_{i}_{j}")

                                if st.button("➕ Añadir Campo", key=f"cf_{i}"):
                                    sec["campos"].append({"id": f"c_{i}_{len(sec['campos'])}", "label": "", "type": "text"})
                                    st.rerun()

                            elif sec["type"] == "checklist":
                                st.caption("Ítems del Checklist (Generan opciones de Subir Foto + Checkbox OK):")
                                lineas = st.text_area("Ingresa un punto de revisión por línea", value="\n".join(sec["items"]), height=120, key=f"ta_{i}")
                                sec["items"] = lineas.split("\n")

                            if st.button("🗑️ Eliminar Sección", key=f"ds_{i}", type="secondary"):
                                st.session_state.builder_secs.pop(i)
                                st.rerun()

