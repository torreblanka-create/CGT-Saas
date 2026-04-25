import json
import os
from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st

from config.config import get_scoped_path, obtener_logo_cliente
from src.infrastructure.database import ejecutar_query, obtener_dataframe
from core.reports.generador_pdf import pdf_engine
from core.utils import (
    is_valid_context,
    obtener_listado_personal,
    render_hybrid_date_input,
    render_multiselect_personal,
    render_name_input_combobox,
    show_context_warning,
)


def render_registros_comunicaciones(DB_PATH, filtros):
    # --- UI ELITE NEON ONYX ---
    st.markdown("""
        <div style='background: #F5F3F0; 
                    padding: 25px; border-radius: 15px; border-left: 5px solid #10B981; 
                    margin-bottom: 25px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);'>
            <div style='display: flex; align-items: center; gap: 15px;'>
                <div style='background: rgba(16,185,129,0.15); padding: 10px; border-radius: 10px;'>
                    <span style='font-size: 2rem;'>🎓</span>
                </div>
                <div>
                    <h2 style='color: #047857; margin:0; font-family:Outfit, sans-serif;'>
                        Gestión de Competencias & Academia
                    </h2>
                    <p style='color: #94A3B8; margin:5px 0 0 0; font-size: 0.95rem;'>
                        Control de capacitaciones, horas-hombre y registros de entrenamiento en terreno.
                    </p>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    if not is_valid_context(filtros):
        show_context_warning()
        return

    emp_id = filtros.get("empresa_id", 0)
    con_id = filtros.get("contrato_id", 0)
    emp_nom = filtros.get("empresa_nom", "E_Default")
    con_nom = filtros.get("contrato_nom", "C_Default")

    # Obtener listado de personal contextual
    lista_personal = obtener_listado_personal(DB_PATH, filtros)

    # Fetch global history early for dashboard metrics
    q_t = "SELECT id, fecha, faena, tema, relator, estado, tipo_documento, participantes_json, hh_totales FROM trazabilidad_documental WHERE empresa_id = ?"
    df_t = obtener_dataframe(DB_PATH, q_t, (emp_id,))

    tab_dash, tab1, tab_historial = st.tabs(["📊 Desempeño y Cobertura", "📝 Generar Acta (Terreno)", "🗂️ Historial y Cierre"])

    # ==========================================
    # TAB 0: DASHBOARD
    # ==========================================
    with tab_dash:
        if df_t.empty:
            st.info("No hay registros en terreno documentados.")
        else:
            total_charlas = len(df_t)
            cerradas = len(df_t[df_t['estado'] == 'Cerrado'])
            
            # Extract total participants and HH
            total_part = 0
            total_hh = df_t['hh_totales'].sum()
            for p_json in df_t['participantes_json'].dropna():
                try:
                    p_list = json.loads(p_json)
                    n_p = len([p for p in p_list if p.get('rut')])
                    total_part += n_p
                except: pass
            
            # Metric Cards
            st.markdown("<div style='margin-bottom: 20px;'>", unsafe_allow_html=True)
            c1, c2, c3, c4 = st.columns(4)
            c1.markdown(f"<div class='metric-card-elite'><h4>{total_charlas}</h4><p>Actas Emitidas</p></div>", unsafe_allow_html=True)
            c2.markdown(f"<div class='metric-card-elite'><h4>{total_part}</h4><p>Personas Cubiertas</p></div>", unsafe_allow_html=True)
            c3.markdown(f"<div class='metric-card-elite'><h4 style='color:#10B981;'>{total_hh:.1f}</h4><p>Total HH Formación</p></div>", unsafe_allow_html=True)
            c4.markdown(f"<div class='metric-card-elite'><h4 style='color:#F59E0B;'>{((cerradas/total_charlas)*100):.0f}%</h4><p>Tasa de Cierre</p></div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
            
            st.divider()
            
            c_g1, c_g2 = st.columns(2)
            with c_g1:
                st.markdown("#### 📊 Tipo de Documento Emitido")
                doc_counts = df_t['tipo_documento'].value_counts().reset_index()
                fig_doc = px.bar(doc_counts, x='tipo_documento', y='count', color='tipo_documento', 
                                 template="plotly_dark", color_discrete_sequence=px.colors.sequential.Viridis)
                st.plotly_chart(fig_doc, use_container_width=True)
            
            with c_g2:
                st.markdown("#### 🏅 Top Relatores EHS")
                rel_counts = df_t['relator'].value_counts().head(5).reset_index()
                fig_rel = px.pie(rel_counts, values='count', names='relator', 
                                 template="plotly_dark", hole=0.4)
                st.plotly_chart(fig_rel, use_container_width=True)

    # ==========================================
    # TAB 1: GENERAR TARJETA (TERRENO)
    # ==========================================
    with tab1:
        with st.container(border=True):
            st.markdown("#### Formulario de Actividad")
            with st.form("form_trazabilidad_merged"):
                c1, c2 = st.columns(2)
                # HÍBRIDO DE UBICACIÓN COMPACTO
                c_loc1, c_loc2 = st.columns([1, 1])
                with c_loc1:
                    loc_pre = st.selectbox("📍 Ubicación Predefinida", ["--- OTRO / MANUAL ---", "Instalación de Faena", "Taller", "Primario", "Secundario", "Terciario", "Planta de filtros", "Planta concentradora", "Planta tostación", "Horno Flash", "Patio de bodega", "Mina"], key="loc_pre_rc")
                with c_loc2:
                    loc_man = st.text_input("Ingresar manualmente", placeholder="Escriba lugar específico...", key="loc_man_rc", disabled=(loc_pre != "--- OTRO / MANUAL ---"))

                faena = loc_man if loc_pre == "--- OTRO / MANUAL ---" else loc_pre

                tema = c1.text_input("Tema a Tratar (Charla/Procedimiento)")
                fecha_t = render_hybrid_date_input("Fecha de Actividad", key="rc_terreno")
                relator = render_name_input_combobox("Relator / Supervisor", lista_personal, key="rc_relator", default=st.session_state.username)
                administrador = render_name_input_combobox("Administrador / APR", lista_personal, key="rc_admin")
                tipo_doc = c2.selectbox("Clasificación SGI", ["CHARLA / REUNIÓN", "INSTRUCTIVO", "PROCEDIMIENTO", "AST / ART", "REGLAMENTACIONES", "CAPACITACIÓN", "OTRO"])

                c3, c4, c5 = st.columns(3)
                hora_ini = c3.time_input("Hora Inicio", key="hi_t")
                hora_fin = c4.time_input("Hora Término", key="hf_t")
                hh_totales = c5.number_input("Horas Hombre Estandarizadas", min_value=0.0, value=0.5, step=0.5)

                descripcion = st.text_area("Notas / Observaciones del Terreno")
                seleccionados = render_multiselect_personal("Asistentes Previstos (opcional)", lista_personal, key="asist_t")
                filas_blanco = st.number_input("Espacios en blanco en PDF (Para rellenar en terreno)", min_value=0, max_value=40, value=10)

                if st.form_submit_button("🚀 Generar Acta y Registrar", type="primary", use_container_width=True):
                    if not faena or not tema:
                        st.error("⚠️ La Ubicación y el Tema son obligatorios.")
                    else:
                        participantes = []
                        for s in seleccionados:
                            if "(" in s:
                                rut = s.split("(")[-1].strip(")")
                                nombre = s.split("(")[0].strip()
                                participantes.append({"rut": rut, "nombre": nombre, "cargo": "N/A"})
                            else:
                                participantes.append({"rut": "MANUAL", "nombre": s, "cargo": "N/A"})

                        for _ in range(int(filas_blanco)): participantes.append({})

                        datos = {
                            "faena": faena, "administrador": administrador, "tema": tema,
                            "fecha": fecha_t.strftime("%d-%m-%Y"), "descripcion": descripcion,
                            "relator": relator, "hora_inicio": hora_ini.strftime("%H:%M"),
                            "hora_termino": hora_fin.strftime("%H:%M"), "hh_totales": hh_totales,
                            "tipo_documento": tipo_doc
                        }

                        with st.spinner("Compilando Documento PDF..."):
                            pdf_bytes = pdf_engine.generar('TARJETA', datos, participantes, obtener_logo_cliente(emp_nom), obtener_logo_cliente(emp_nom))
                            id_ins = ejecutar_query(DB_PATH, """
                                INSERT INTO trazabilidad_documental 
                                (faena, administrador, tema, fecha, descripcion, relator, hora_inicio, hora_termino, hh_totales, tipo_documento, participantes_json, estado, empresa_id, contrato_id) 
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, (faena, administrador, tema, fecha_t.strftime("%Y-%m-%d"), descripcion, relator,
                                   hora_ini.strftime("%H:%M"), hora_fin.strftime("%H:%M"), hh_totales, tipo_doc,
                                   json.dumps(participantes), "Abierto", emp_id, con_id), commit=True)

                            st.session_state.pdf_tmp_rc = {"bytes": pdf_bytes, "name": f"Acta_Terreno_{id_ins}_{tema.replace(' ','_')}.pdf"}
                            st.success(f"✅ Documento SGI #{id_ins} generado. Desplegando archivo...")

        if 'pdf_tmp_rc' in st.session_state and st.session_state.pdf_tmp_rc:
            st.download_button("📥 Descargar Archivo Físico para Recabar Firmas", st.session_state.pdf_tmp_rc["bytes"], st.session_state.pdf_tmp_rc["name"], use_container_width=True, type="primary")

    # ==========================================
    # TAB 2: HISTORIAL Y EVIDENCIA
    # ==========================================
    with tab_historial:
        st.markdown("#### Historial de Actas Abiertas")
        st.info("💡 Una vez recabadas las firmas en terreno escanea y sube el PDF aquí para dar por cerrado el ciclo. Sus horas se migrarán automáticamente.")

        if not df_t.empty:
            df_hist_show = df_t.copy().sort_values('id', ascending=False)
            
            # Colorear estado
            df_hist_show['Estado UI'] = df_hist_show['estado'].apply(lambda x: '🟢 Cerrado' if x == 'Cerrado' else '🔴 Abierto / Pendiente')
            
            st.dataframe(df_hist_show[['id','fecha','faena','tipo_documento','tema','relator','Estado UI']], use_container_width=True, hide_index=True)

            abiertos = df_t[df_t['estado'] == 'Abierto']
            if not abiertos.empty:
                st.divider()
                st.markdown("#### 📂 Clausurar Acta")
                sel_c = st.selectbox("Seleccione Documento Pendiente:", abiertos['id'].astype(str) + " - " + abiertos['tema'])
                if sel_c:
                    id_c = int(sel_c.split(" - ")[0])
                    up_c = st.file_uploader("Adjuntar Hoja Escaneada con Firmas (PDF/JPG)", type=["pdf","jpg"], key=f"up_c_{id_c}")
                    if st.button("Subir Respaldo e Integrar a HH Corporativas", type="primary", key=f"btn_c_{id_c}"):
                        if up_c:
                            f_path = os.path.join(get_scoped_path(emp_nom, "trazabilidad"), f"Resp_{id_c}_{up_c.name}")
                            with open(f_path, "wb") as f: f.write(up_c.getbuffer())

                            ejecutar_query(DB_PATH, "UPDATE trazabilidad_documental SET estado='Cerrado', archivo_respaldo=? WHERE id=?", (f_path, id_c), commit=True)

                            row_t = df_t[df_t['id'] == id_c].iloc[0]
                            cap_id = ejecutar_query(DB_PATH, """
                                INSERT INTO capacitaciones (fecha, titulo, tipo, duracion_hrs, lugar, instructor, evidencia_path, empresa_id, contrato_id)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, (row_t['fecha'], f"TERRENO SGI: {row_t['tema']}", row_t['tipo_documento'], 0.5, row_t['faena'], row_t['relator'], f_path, emp_id, con_id), commit=True, fetch_lastrowid=True)

                            try:
                                res_json = ejecutar_query(DB_PATH, "SELECT participantes_json FROM trazabilidad_documental WHERE id=?", (id_c,))
                                p_list = json.loads(res_json[0][0])
                                for p in p_list:
                                    if p.get('rut') and p.get('rut') != 'MANUAL':
                                        ejecutar_query(DB_PATH, "INSERT OR IGNORE INTO asistencia_capacitacion (capacitacion_id, trabajador_id, rut, nombre, fuente) VALUES (?, ?, ?, ?, ?)", (cap_id, p['rut'], p['rut'], p['nombre'], 'sistema'), commit=True)
                            except: pass

                            st.success("✅ Documento cerrado. Las firmas han sido procesadas digitalmente y las HH contabilizadas.")
                            st.rerun()
                        else:
                            st.error("Debes adjuntar el archivo físico escaneado para cerrar este documento.")
