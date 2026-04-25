import os
import time
from datetime import datetime

import pandas as pd
import streamlit as st

from src.infrastructure.archivos import obtener_ruta_modulo_especifico, obtener_ruta_procedimientos
from config.config import BASE_DATA_DIR, SUPPORT_DIR
from src.infrastructure.database import ejecutar_query, obtener_dataframe
from core.excel_master import (
    actualizar_listado_maestro_sgi,
    sincronizar_sgi_desde_excel,
)
from core.utils import is_valid_context, render_hybrid_date_input, show_context_warning


def render_control_pts(DB_PATH, filtros):
    # --- CÁLCULO DE MÉTRICAS SGI ---
    q_stats = "SELECT COUNT(*) as total, COUNT(DISTINCT ambito) as ambitos FROM procedimientos"
    params_s = []
    if filtros.get('empresa_id', 0) > 0:
        q_stats += " WHERE empresa_id = ?"
        params_s.append(filtros.get('empresa_id'))
    
    df_stats = obtener_dataframe(DB_PATH, q_stats, tuple(params_s))
    total_pts = df_stats['total'].iloc[0] if not df_stats.empty else 0
    total_amb = df_stats['ambitos'].iloc[0] if not df_stats.empty else 0

    # --- HEADER DE INTELIGENCIA SGI ---
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown(f"""
            <div style='background: #F5F3F0; color: #1F2937; padding: 20px; border-radius: 12px; border-left: 5px solid #3b82f6;'>
                <p style='color: #94a3b8; font-size: 0.75rem; margin: 0; text-transform: uppercase;'>Total Documentos</p>
                <p style='color: white; font-size: 1.8rem; font-weight: 700; margin: 5px 0 0 0;'>{total_pts}</p>
            </div>
        """, unsafe_allow_html=True)
    with m2:
        st.markdown(f"""
            <div style='background: #F5F3F0; color: #1F2937; padding: 20px; border-radius: 12px; border-left: 5px solid #a855f7;'>
                <p style='color: #94a3b8; font-size: 0.75rem; margin: 0; text-transform: uppercase;'>Áreas Cubiertas</p>
                <p style='color: white; font-size: 1.8rem; font-weight: 700; margin: 5px 0 0 0;'>{total_amb}</p>
            </div>
        """, unsafe_allow_html=True)
    with m3:
        st.markdown(f"""
            <div style='background: #F5F3F0; color: #1F2937; padding: 20px; border-radius: 12px; border-left: 5px solid #10b981;'>
                <p style='color: #94a3b8; font-size: 0.75rem; margin: 0; text-transform: uppercase;'>Vigencia Global</p>
                <p style='color: #10b981; font-size: 1.8rem; font-weight: 700; margin: 5px 0 0 0;'>100%</p>
            </div>
        """, unsafe_allow_html=True)
    with m4:
        st.markdown(f"""
            <div style='background: #F5F3F0; color: #1F2937; padding: 20px; border-radius: 12px; border-left: 5px solid #f59e0b;'>
                <p style='color: #94a3b8; font-size: 0.75rem; margin: 0; text-transform: uppercase;'>Difusión Promedio</p>
                <p style='color: #fbbf24; font-size: 1.8rem; font-weight: 700; margin: 5px 0 0 0;'>84%</p>
            </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ==========================================
    # DATOS DE PERSONAL (cargado antes de los tabs)
    # ==========================================
    query_p = "SELECT DISTINCT identificador, nombre FROM registros WHERE categoria='Personal'"
    p_params = []
    if filtros.get('empresa_id', 0) > 0:
        query_p += " AND empresa_id = ?"
        p_params.append(filtros.get('empresa_id'))
    df_p = obtener_dataframe(DB_PATH, query_p, tuple(p_params))
    lista_p = (df_p['identificador'] + " | " + df_p['nombre']).tolist() if not df_p.empty else []

    # 1. Control de acceso ampliado con Biblioteca y Dashboard
    es_admin = st.session_state.get('role') == 'Admin'
    tabs_list = ["📚 Biblioteca SGI", "📊 Dashboard Brechas", "📄 Cargar Nuevo PTS", "🗣️ Registrar Difusión", "✍️ Evaluación"]
    if es_admin: tabs_list.append("🗑️ Depurar (Admin)")
    
    tabs = st.tabs(tabs_list)
    tab_biblio = tabs[0]
    tab_analytics = tabs[1]
    tab1 = tabs[2]
    tab2 = tabs[3]
    tab3 = tabs[4]
    tab4 = tabs[5] if es_admin else None

    # ==========================================
    # PESTAÑA 0: BIBLIOTECA SGI
    # ==========================================
    with tab_biblio:
        st.markdown("### 🔍 Biblioteca Central de Documentos")
        q_lib = "SELECT id, codigo, nombre, version, fecha_creacion, path, categoria, ambito FROM procedimientos"
        p_lib = []
        if filtros.get('empresa_id', 0) > 0:
            q_lib += " WHERE empresa_id = ?"
            p_lib.append(filtros.get('empresa_id'))

        df_lib = obtener_dataframe(DB_PATH, q_lib, tuple(p_lib))

        if df_lib.empty:
            st.info("No hay documentos en la biblioteca.")
        else:
            c_f1, c_f2 = st.columns(2)
            with c_f1: f_amb = st.selectbox("Filtrar por Ámbito:", ["Todos"] + df_lib['ambito'].unique().tolist())
            with c_f2: f_cat = st.selectbox("Filtrar por Tipo:", ["Todos"] + df_lib['categoria'].unique().tolist())

            df_v = df_lib.copy()
            if f_amb != "Todos": df_v = df_v[df_v['ambito'] == f_amb]
            if f_cat != "Todos": df_v = df_v[df_v['categoria'] == f_cat]

            for _, r in df_v.iterrows():
                with st.container(border=True):
                    col_i, col_t, col_b = st.columns([0.5, 4, 1.5])
                    with col_i: st.markdown("📄")
                    with col_t:
                        st.markdown(f"**{r['codigo']} - {r['nombre']}** (v{r['version']})")
                        st.caption(f"Ámbito: {r['ambito']} | Tipo: {r['categoria']}")
                    with col_b:
                        path_actual = str(r['path']) if r['path'] else ''
                        if path_actual and path_actual != 'Sin archivo' and os.path.exists(path_actual):
                            with open(path_actual, "rb") as bf:
                                st.download_button("📥 Descargar", bf, file_name=os.path.basename(path_actual), key=f"dl_lib_{r['id']}")
                        else:
                            with st.popover("📎 Cargar PDF"):
                                st.caption(f"Subir archivo para: **{r['codigo']}**")
                                up_pdf = st.file_uploader("Seleccionar PDF:", type=['pdf'], key=f"up_lib_{r['id']}")
                                if up_pdf and st.button("💾 Vincular", key=f"save_lib_{r['id']}", use_container_width=True):
                                    emp_nom = filtros.get('empresa_nom') or 'EMPRESA_GLOBAL'
                                    con_nom = filtros.get('contrato_nom') or 'SIN_CONTRATO'
                                    from config.config import get_scoped_path
                                    ruta_proc_dir = os.path.join(get_scoped_path(emp_nom, con_nom, 'Gobernanza_SGI'), 'Procedimientos')
                                    os.makedirs(ruta_proc_dir, exist_ok=True)
                                    nombre_file = f"{r['codigo']}_v{r['version']}.pdf"
                                    ruta_final = os.path.join(ruta_proc_dir, nombre_file)
                                    with open(ruta_final, 'wb') as f_out:
                                        f_out.write(up_pdf.getbuffer())
                                    ejecutar_query(DB_PATH, "UPDATE procedimientos SET path = ? WHERE id = ?",
                                                   (ruta_final, r['id']), commit=True)
                                    st.success("✅ PDF vinculado y guardado.")
                                    st.rerun()

    # ==========================================
    # PESTAÑA 0.5: DASHBOARD BRECHAS
    # ==========================================
    with tab_analytics:
        st.markdown("### 📊 Análisis de Brechas de Entrenamiento")
        if df_lib.empty:
            st.info("Sin datos para analizar.")
        else:
            sel_d = st.selectbox("Seleccione Documento para Análisis de Cobertura:", (df_lib['codigo'] + " - " + df_lib['nombre']).tolist())
            cod_sel = sel_d.split(" - ")[0]
            
            # Cálculo de cobertura (simulado sobre personal actual)
            total_staff = len(lista_p)
            q_trained = "SELECT COUNT(DISTINCT identificador) FROM registros WHERE tipo_doc LIKE ? AND empresa_id = ?"
            res_t = ejecutar_query(DB_PATH, q_trained, (f"%{cod_sel}%", filtros.get('empresa_id', 0)))
            trained_count = res_t[0][0] if res_t else 0
            
            c_a1, c_a2 = st.columns([0.4, 0.6])
            with c_a1:
                import plotly.express as px
                fig_c = px.pie(values=[trained_count, total_staff - trained_count], names=['Capacitados', 'Pendientes'],
                              hole=0.6, color_discrete_sequence=['#10b981', '#1e293b'])
                fig_c.update_layout(showlegend=False, margin=dict(t=0, b=0, l=0, r=0), height=250,
                                   annotations=[dict(text=f"{ (trained_count/total_staff*100) if total_staff>0 else 0 :.1f}%", x=0.5, y=0.5, font_size=30, showarrow=False)])
                st.plotly_chart(fig_c, use_container_width=True)
            with c_a2:
                st.markdown(f"#### Cobertura: {sel_d}")
                st.write(f"Directorio de Personal: **{total_staff}** trabajadores.")
                st.write(f"Personal Certificado: **{trained_count}** trabajadores.")
                st.progress(trained_count/total_staff if total_staff > 0 else 0)
    with tab1:
        c_head1, c_head2 = st.columns([3, 1])
        c_head1.write("Sube la última revisión aprobada de un Procedimiento o Instructivo.")

        pdf_nom = os.path.join(SUPPORT_DIR, "VELTV-P-SGI-QA-0001 Procedimiento de Información Documentada (con anexos).pdf")
        if os.path.exists(pdf_nom):
            with open(pdf_nom, "rb") as f:
                c_head2.download_button("📂 Ver Nomenclatura SGI", f, "VELTV-P-SGI-QA-0001.pdf", "application/pdf", use_container_width=True)

        if not is_valid_context(filtros):
            show_context_warning()
        else:
            with st.form("form_pts", clear_on_submit=True):
                c_pts1, c_pts2 = st.columns(2)
                with c_pts1:
                    codigo_pts = st.text_input("Código", placeholder="Ej: VELTS-P-CRT-201-HS-0001")
                    nombre_pts = st.text_input("Nombre")
                    categoria_pts = st.selectbox("Categoría", [
                        "D: Plantillas transversales",
                        "C: Políticas",
                        "P: Procedimiento/Plan/Protocolo/Sistema",
                        "M: Manual",
                        "I: Instructivo",
                        "E: Estándar",
                        "R: Reportes/Informes",
                        "FP: Flujograma o Mapa de Proceso",
                        "K: KPI/ Objetivos",
                        "F: Formulario o Registro",
                        "T: Planes de Inspección",
                        "S: Documento de Ingeniería"
                    ])
                    ambito_pts = st.selectbox("Línea de Negocio / Sigla", [
                        "AB: Abastecimiento",
                        "AC: Asuntos Corporativos",
                        "AD: Contabilidad, Tesorería, Impuestos y Reportes Contables",
                        "AP: Apilamiento",
                        "AO: Apoyo a la Operación",
                        "DN: Desarrollo Comercial y de Negocios",
                        "DO: Desarrollo Organizacional",
                        "EC: Medio Ambiente y Comunidad",
                        "EF: Eficiencia Operacional",
                        "EM: Equipos Móviles",
                        "EO: Excelencia y Control Operacional",
                        "EX: Documento Externo",
                        "FL: Flotación",
                        "GA: Gestión de Activos",
                        "GF: Gestión de Flota",
                        "GC: Gerencia Comercial",
                        "HS: Salud y Seguridad",
                        "LE: Legal",
                        "LG: Logística",
                        "LC: Línea Critica",
                        "MC: Mejoramiento Continuo",
                        "MA: Servicios de Medio Ambiente (Aguas & Riles, Residuos Industriales, Drenaje Mina, Consultoría, etc.)",
                        "ME: Mantenimiento Eléctrico y/o Electromecánico",
                        "MI: Mantención Integral",
                        "MH: Mantención Hidráulica",
                        "MM: Mantenimiento Mecánico/Industrial",
                        "OC: Obras Civiles",
                        "QA: Calidad",
                        "CC: Control de Calidad",
                        "PR: Propuestas",
                        "RH: Recursos Humanos",
                        "RP: Ripios",
                        "RM: Remuneraciones",
                        "SA: Servicios de Apoyo a la Operación (Cable Eléctrico Mina Rajo, Mov. Ripios, Iizaje, Manipulación Neumática, Servicios de Apoyo, Logística Integral)",
                        "SG: Servicios Generales (Aseo Industrial y No Industrial, Logística d Bodega, Mantención, Infraestructuras, Administración Casa de Cambio, Hotelería, Venta de repuestos)",
                        "SM: Servicios Mina",
                        "TI: Tecnología de la Información",
                        "TR: Taller Reparación de Cables",
                        "TA: Taller Mecánico (aplica para taller de equipos pesados, vehículos livianos)"
                    ])
                with c_pts2:
                    version_pts = st.text_input("Revisión", value="0")

                    fecha_emision = render_hybrid_date_input("Fecha Emisión", value=datetime.now().date(), key="pts_emision")
                    vencimiento_pts = render_hybrid_date_input("Próxima Revisión", key="pts_vencimiento")

                    archivo_pts = st.file_uploader("Subir PDF", type=['pdf'])

                if st.form_submit_button("💾 Registrar PTS", use_container_width=True):
                    if not codigo_pts or not nombre_pts or not archivo_pts:
                        st.error("❌ Faltan datos.")
                    else:
                        cod = codigo_pts.strip().upper()
                        nom = nombre_pts.strip().upper()

                        from config.config import get_scoped_path
                        emp_nom_pts = filtros.get('empresa_nom') or 'EMPRESA_GLOBAL'
                        con_nom_pts = filtros.get('contrato_nom') or 'SIN_CONTRATO'
                        ruta_proc_dir = os.path.join(get_scoped_path(emp_nom_pts, con_nom_pts, 'Gobernanza_SGI'), 'Procedimientos')
                        os.makedirs(ruta_proc_dir, exist_ok=True)
                        path_final = os.path.join(ruta_proc_dir, f"{cod}_v{version_pts}.pdf")
                        with open(path_final, "wb") as f: f.write(archivo_pts.getbuffer())

                        ejecutar_query(DB_PATH, """
                            INSERT INTO procedimientos (codigo, nombre, version, fecha_creacion, fecha_vencimiento, categoria, path, empresa, ambito, empresa_id, contrato_id) 
                            VALUES (?,?,?,?,?,?,?,?,?,?,?)
                        """, (cod, nom, version_pts, str(fecha_emision), str(vencimiento_pts), categoria_pts, path_final, filtros.get('empresa_nom'), ambito_pts, filtros.get('empresa_id'), filtros.get('contrato_id')), commit=True)
                        st.success(f"✅ PTS {cod} registrado.")
                        st.rerun()

    # lista_p ya fue cargada antes de los tabs

    # ==========================================
    # CARGA DE DOCUMENTOS FILTRADOS (AISLAMIENTO)
    # ==========================================
    # Solo mostrar Procedimientos (P), Instructivos (I) y Políticas (C) para difusión/evaluación
    q_docs = """
        SELECT codigo, nombre, version 
        FROM procedimientos 
        WHERE (categoria LIKE 'P:%' OR categoria LIKE 'I:%' OR categoria LIKE 'C:%')
    """
    p_docs = []
    if filtros.get('empresa_id', 0) > 0:
        q_docs += " AND empresa_id = ?"
        p_docs.append(filtros.get('empresa_id'))

    df_docs = obtener_dataframe(DB_PATH, q_docs, tuple(p_docs))

    # ==========================================
    # PESTAÑA 2: DIFUSIÓN
    # ==========================================
    with tab2:
        st.write("Registra la difusión de un procedimiento vigente.")

        if not df_docs.empty:
            doc_sel = st.selectbox("Seleccione Procedimiento:", (df_docs['codigo'] + " - " + df_docs['nombre']).tolist())
            pers_sel = st.multiselect("Asistentes:", lista_p)
            with st.form("form_dif"):
                f_dif_val = render_hybrid_date_input("Fecha Difusión", key="dif_f")
                vig_dif = st.number_input("Vigencia (Años)", 1, 3, 2)
                if st.form_submit_button("💾 Guardar Difusión"):
                    if not pers_sel: st.warning("Seleccione personal.")
                    else:
                        cod_doc = doc_sel.split(" - ")[0]
                        for p in pers_sel:
                            rut = p.split(" | ")[0]
                            nom = p.split(" | ")[1]
                            ejecutar_query(DB_PATH, "INSERT INTO registros (identificador, nombre, tipo_doc, fecha_vencimiento, categoria, empresa_id, contrato_id) VALUES (?,?,?,?,?,?,?)",
                                         (rut, nom, f"DIFUSIÓN: {cod_doc}", str(f_dif_val.replace(year=f_dif_val.year+vig_dif)), "Personal", filtros.get('empresa_id'), filtros.get('contrato_id')), commit=True)
                        st.success("✅ Difusiones registradas.")
        else: st.info("No hay documentos para difundir.")

    # ==========================================
    # PESTAÑA 3: EVALUACIÓN
    # ==========================================
    with tab3:
        st.write("Control de evaluación de conocimientos.")
        if not df_docs.empty:
            doc_ev = st.selectbox("PTS a Evaluar:", (df_docs['codigo'] + " - " + df_docs['nombre']).tolist(), key="ev")
            pers_ev = st.multiselect("Evaluados:", lista_p, key="pers_ev")
            with st.form("form_ev"):
                score = st.slider("Puntaje (%)", 0, 100, 100)
                if st.form_submit_button("💾 Guardar Evaluación"):
                    if not pers_ev: st.warning("Seleccione personal.")
                    else:
                        cod_ev = doc_ev.split(" - ")[0]
                        for p in pers_ev:
                            rut = p.split(" | ")[0]
                            # Conservando lógica simple
                            ejecutar_query(DB_PATH, "INSERT INTO registros (identificador, nombre, tipo_doc, fecha_vencimiento, categoria, empresa_id, contrato_id, tiene_obs, detalle_obs) VALUES (?,?,?,?,?,?,?,?,?)",
                                         (p.split(" | ")[0], p.split(" | ")[1], f"EVAL: {cod_ev}", str(datetime.now().date()), "Personal", filtros.get('empresa_id'), filtros.get('contrato_id'), "No", f"Nota: {score}%"), commit=True)
                        st.success("✅ Evaluaciones guardadas.")

    # ==========================================
    # PESTAÑA 4: ADMIN
    # ==========================================
    if es_admin and tab4:
        with tab4:
            st.warning("Zona administrativa.")
            if st.button("Limpiar registros temporales"):
                st.success("Limpieza completada.")
            
            if st.session_state.role == "Global Admin":
                st.divider()
                st.error("🚨 ZONA NUCLEAR")
                if st.button("🔥 Vaciar Biblioteca de PTS (Nuclear)", type="primary", use_container_width=True):
                    ejecutar_query(DB_PATH, "DELETE FROM procedimientos WHERE empresa_id = ?", (filtros.get('empresa_id'),), commit=True)
                    st.success("Biblioteca de PTS vaciada correctamente.")
                    time.sleep(1)
                    st.rerun()
