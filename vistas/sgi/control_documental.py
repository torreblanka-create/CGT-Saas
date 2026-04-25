import io
import os
import time
from datetime import datetime

import pandas as pd
import streamlit as st

from src.infrastructure.archivos import obtener_ruta_procedimientos
from config.config import BASE_DATA_DIR, SUPPORT_DIR
from src.infrastructure.database import ejecutar_query, obtener_dataframe, registrar_log
from core.excel_master import (
    actualizar_listado_maestro_sgi,
    sincronizar_sgi_desde_excel,
)
from core.utils import is_valid_context, render_hybrid_date_input, show_context_warning


def render_control_documental_sgi(DB_PATH, filtros):
    # --- UI ELITE NEON ONYX ---
    st.markdown("""
        <div style='background: #F5F3F0; color: #1F2937; padding: 2rem; border-radius: 15px; border: 1px solid rgba(212,212,216,0.3); margin-bottom: 2rem; box-shadow: 0 10px 15px -3px rgba(0,0,0,0.05);'>
            <div style='display: flex; align-items: center; gap: 20px;'>
                <div style='background: rgba(56, 189, 248, 0.1); padding: 15px; border-radius: 12px; border: 1px solid rgba(56, 189, 248, 0.2);'>
                    <span style='font-size: 2.5rem;'>📄</span>
                </div>
                <div>
                    <h1 style='color: #F8FAFC; margin: 0; font-size: 1.8rem; font-family: "Outfit", sans-serif;'>Documentación SGI (Master List)</h1>
                    <p style='color: #94A3B8; margin: 5px 0 0 0; font-size: 1rem; opacity: 0.9;'>Repositorio maestro de documentos normativos bajo estándares ISO.</p>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    if not is_valid_context(filtros):
        show_context_warning()
        return

    emp_nom = filtros.get('empresa_nom', 'N/A')
    con_nom = filtros.get('contrato_nom', 'GLOBAL')
    emp_id = filtros.get('empresa_id')

    # 0. Preparar Datos
    q_all = "SELECT * FROM procedimientos WHERE empresa_id = ? ORDER BY CAST(correlativo AS INTEGER) ASC"
    df_raw = obtener_dataframe(DB_PATH, q_all, (emp_id,))

    # --- PESTAÑAS PRINCIPALES ---
    tab_dash, tab_lista, tab_gestion = st.tabs(["📊 Inteligencia Documental", "📋 Listado Maestro y Archivos", "📂 Emisión y Carga"])

    # ==========================================
    # TAB 1: DASHBOARD
    # ==========================================
    with tab_dash:
        stats = {"🟢 Vigentes": 0, "🟡 Por Vencer (30d)": 0, "🔴 Vencidos": 0, "📝 En Revisión": 0, "⚫ Obsoletos": 0}
        hoy = datetime.now().date()
        cat_counts = {}

        if not df_raw.empty:
            for _, r in df_raw.iterrows():
                estado_actual = str(r.get('estado_doc', '')).strip()
                cat = r.get('categoria', 'Sin Categoría')
                cat_counts[cat] = cat_counts.get(cat, 0) + 1
                
                if estado_actual == "Obsoleto":
                    stats["⚫ Obsoletos"] += 1
                elif estado_actual == "En Revisión":
                    stats["📝 En Revisión"] += 1
                else:
                    f_v_str = r.get('fecha_vencimiento')
                    if not f_v_str or str(f_v_str).lower() == 'none': 
                        stats["🟢 Vigentes"] += 1
                        continue
                        
                    try:
                        f_v_str = str(f_v_str).split(" ")[0]
                        f_v = datetime.strptime(f_v_str, '%Y-%m-%d').date()
                        if f_v < hoy: stats["🔴 Vencidos"] += 1
                        elif (f_v - hoy).days < 30: stats["🟡 Por Vencer (30d)"] += 1
                        else: stats["🟢 Vigentes"] += 1
                    except: 
                        stats["🟢 Vigentes"] += 1

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Documentos", len(df_raw))
        c2.metric("Vigentes/Aprobados", stats["🟢 Vigentes"])
        c3.metric("En Revisión/Borrador", stats["📝 En Revisión"])
        c4.metric("Desactualizados", stats["🔴 Vencidos"] + stats["⚫ Obsoletos"])

        if len(df_raw) > 0:
            st.divider()
            col_g1, col_g2 = st.columns(2)
            with col_g1:
                st.markdown("#### Matriz de Vigencia")
                df_chart = pd.DataFrame({'Estado': stats.keys(), 'Cantidad': stats.values()})
                st.bar_chart(df_chart.set_index('Estado'), color="#00539C")
            
            with col_g2:
                st.markdown("#### Distribución por Categoría")
                df_cat = pd.DataFrame({'Categoría': cat_counts.keys(), 'Total': cat_counts.values()})
                st.bar_chart(df_cat.set_index('Categoría'), color="#C27C3A")

    # ==========================================
    # TAB 2: LISTADO MAESTRO
    # ==========================================
    with tab_lista:
        if not df_raw.empty:
            # Filtros en contenedor
            with st.container(border=True):
                st.markdown("**Filtros de Búsqueda SGI**")
                c_f1, c_f2, c_f3 = st.columns(3)
                with c_f1:
                    amb_filt = st.multiselect("Línea de Negocio:", options=df_raw['ambito'].dropna().unique())
                with c_f2:
                    tipo_filt = st.multiselect("Categoría de Documento:", options=df_raw['categoria'].dropna().unique())
                with c_f3:
                    busq = st.text_input("Buscador Universal (Código/Nombre):", placeholder="Ej: PTS-001, Trabajo en Altura")

            df_lista = df_raw.copy()
            if amb_filt: df_lista = df_lista[df_lista['ambito'].isin(amb_filt)]
            if tipo_filt: df_lista = df_lista[df_lista['categoria'].isin(tipo_filt)]
            if busq:
                df_lista = df_lista[df_lista['codigo'].str.contains(busq, case=False, na=False) | df_lista['nombre'].str.contains(busq, case=False, na=False)]

            # SEMAFFORIZACIÓN
            def color_semaforo(f_v_str, estado):
                if estado == "Obsoleto": return "⚫ Obsoleto"
                if estado == "En Revisión": return "📝 En Revisión"
                if not f_v_str or str(f_v_str).lower() == 'none' or str(f_v_str).lower() == 'nat': return "🟢 N/A"
                try:
                    f_v_str = str(f_v_str).split(" ")[0]
                    f_v = datetime.strptime(f_v_str, '%Y-%m-%d').date()
                    if f_v < hoy: return "🔴 Vencido"
                    if (f_v - hoy).days < 30: return "🟡 Por Vencer"
                    return "🟢 Vigente"
                except: return "⚪ S/I"

            df_lista['Compliance'] = df_lista.apply(lambda row: color_semaforo(row['fecha_vencimiento'], row['estado_doc']), axis=1)

            # Presentación
            df_show = df_lista[[
                'codigo', 'nombre', 'categoria', 'version', 'fecha_vencimiento', 'Compliance'
            ]].rename(columns={
                'codigo': 'Código SGI', 'nombre': 'Título del Documento',
                'categoria': 'Tipo', 'version': 'Rev.', 'fecha_vencimiento': 'Vencimiento'
            })

            st.dataframe(df_show, use_container_width=True, hide_index=True)

            # --- ACCIONES DE LISTADO (ADMIN) ---
            st.divider()
            c_desc, c_admin, _ = st.columns([2, 2, 4])

            with c_desc:
                # EXPORTAR A EXCEL
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                    df_lista.to_excel(writer, index=False, sheet_name='Listado_Maestro')
                st.download_button(
                    label="📥 Exportar Matriz a Excel",
                    data=buffer.getvalue(),
                    file_name=f"Listado_Maestro_SGI_{datetime.now().strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.ms-excel",
                    use_container_width=True
                )

            with c_admin:
                if st.session_state.get("role") in ["Global Admin", "Admin", "Auditor"]:
                    with st.popover("⚙️ Acciones de Administrador"):
                        st.warning("⚠️ Estas acciones afectan la base documental directamente.")
                        cod_del = st.selectbox("Código a dar de baja:", options=["---"] + list(df_raw['codigo'].unique()))
                        if st.button("❌ Borrar Registro", type="primary"):
                            if cod_del != "---":
                                ejecutar_query(DB_PATH, "DELETE FROM procedimientos WHERE codigo = ? AND empresa_id = ?", (cod_del, emp_id), commit=True)
                                registrar_log(DB_PATH, st.session_state.user_login, "SGI_DELETE_SINGLE", f"Borro: {cod_del}")
                                st.success("Documento dado de baja de la matriz.")
                                time.sleep(1)
                                st.rerun()
                        
                        if st.session_state.role == "Global Admin":
                            st.divider()
                            st.error("🚨 ZONA NUCLEAR")
                            if st.button("🔥 Vaciar Matriz SGI (Nuclear)", type="primary", use_container_width=True):
                                ejecutar_query(DB_PATH, "DELETE FROM procedimientos WHERE empresa_id = ?", (emp_id,), commit=True)
                                st.success("Matriz SGI vaciada correctamente.")
                                time.sleep(1)
                                st.rerun()

            st.divider()
            with st.expander("🕒 Control de Cambios e Historial de Versiones (Trazabilidad ISO)"):
                df_hist = obtener_dataframe(DB_PATH, "SELECT codigo_doc, version_antigua, fecha_cambio, motivo_cambio, modificado_por FROM sgi_historial_versiones WHERE empresa_id=? ORDER BY fecha_cambio DESC", (emp_id,))
                if not df_hist.empty:
                    df_hist.columns = ['Código', 'Versión Archivada', 'Fecha Reemplazo', 'Motivo Cambio', 'Aprobado Por']
                    st.dataframe(df_hist, use_container_width=True, hide_index=True)
                else:
                    st.info("No se han registrado migraciones de versión en el sistema.")

        else:
            st.info("No hay documentos registrados en el Listado Maestro SGI para esta operación.")

    # ==========================================
    # TAB 3: GESTIÓN Y CARGA
    # ==========================================
    with tab_gestion:
        c_g1, c_g2 = st.columns([0.4, 0.6])

        with c_g1:
            st.markdown("### 📥 Sincronización Masiva")
            st.write("Sube la matriz oficial VELTV-F-SGI-QA-0001 (Excel).")
            archivo_sgi = st.file_uploader("Listado Maestro Excel", type=['xlsx'], key="up_sgi_tabs")

            if st.button("🚀 Importar Listado", use_container_width=True):
                if archivo_sgi:
                    with st.spinner("Integrando datos..."):
                        success, msg = sincronizar_sgi_desde_excel(emp_nom, con_nom, archivo_sgi)
                        if success:
                            st.success(f"✅ {msg}")
                            time.sleep(1)
                            st.rerun()
                        else: st.error(f"❌ {msg}")
                else: st.warning("Selecciona al menos un archivo válido.")

            st.divider()
            st.markdown("### 📂 Enlace de PDFs en Bulk")
            st.info("El sistema asocia automáticamente los PDFs subidos al Listado si coinciden los nùmeros de código.")
            pdfs_bulk = st.file_uploader("Cargar PDFs (Lote)", type=['pdf'], accept_multiple_files=True, key="up_pdfs_tabs")

            if st.button("🔗 Iniciar Enlace", use_container_width=True):
                if not pdfs_bulk: st.warning("Suba los PDFs primero.")
                else:
                    with st.spinner("Procesando indexación..."):
                        votos_ok = 0
                        ruta_base = obtener_ruta_procedimientos(emp_nom, contrato=con_nom)
                        for pdf in pdfs_bulk:
                            nombre_archivo = str(pdf.name).upper().replace(".PDF", "").strip()
                            res_db = ejecutar_query(DB_PATH, "SELECT codigo FROM procedimientos WHERE UPPER(codigo) = ? AND empresa_id = ?", (nombre_archivo, emp_id))
                            if res_db:
                                cod_found = res_db[0][0]
                                path_final = os.path.join(ruta_base, f"{pdf.name}")
                                with open(path_final, "wb") as f: f.write(pdf.getbuffer())
                                ejecutar_query(DB_PATH, "UPDATE procedimientos SET path = ? WHERE codigo = ? AND empresa_id = ?", (path_final, cod_found, emp_id), commit=True)
                                votos_ok += 1
                        st.success(f"✅ Se completó la vinculación para {votos_ok} documentos.")
                        time.sleep(1)
                        st.rerun()

        with c_g2:
            st.markdown("### 📝 Emisión y Modificación Unitaria")
            with st.form("form_sgi_tabs_ind", clear_on_submit=True):
                nombre_doc = st.text_input("1.- Título Oficial del Documento", placeholder="Ej: Procedimiento General de Bloqueo de Energías")
                emp_sigla = st.selectbox("Acrónimo Entidad", ["VELTV", "VELTS", "STEEL"])

                c_gi_1, c_gi_2 = st.columns(2)
                with c_gi_1:
                    cat_full = st.selectbox("Jerarquía Documental", [
                        "P: Procedimiento Operativo", 
                        "I: Instructivo Técnico", 
                        "E: Estándar/Política", 
                        "F: Formulario/Registro", 
                        "R: Reporte/Acta"
                    ])
                    sub_area = st.text_input("Sub-Área/Ubicación", placeholder="Opcional")
                    neg_sigla = st.text_input("Sigla Proceso/Negocio", placeholder="Ej: HSE, QA, OP")
                with c_gi_2:
                    correlativo = st.text_input("N° Correlativo", value="0001", help="Número de la jerarquía.")
                    version = st.text_input("Revisión Actual", value="0", help="Usa valores numéricos enteros (ej: 0, 1, 2)")
                    estado_doc = st.selectbox("Estado de Aprobación", ["Vigente", "En Revisión", "Obsoleto"])

                c_fec1, c_fec2 = st.columns(2)
                with c_fec1:
                    f_c = render_hybrid_date_input("Fecha Creación/Emisión", value=datetime.now().date(), key="sgi_c_tab")
                with c_fec2:
                    f_v = render_hybrid_date_input("Fecha Vencimiento Esperada", key="sgi_v_tab")

                st.markdown("#### Configuración de Control de Cambios")
                tipo_cambio = st.radio("Flujo de ISO 9001. Si el documento ya existe:", [
                    "A) Obsolecer anterior, guardar snapshot y subir de versión (Trazable)", 
                    "B) Cambio de formato menor/corrección typo (Sobrescribir sin marcar historial)"
                ])
                motivo = st.text_input("Motivo Central de la Revisión (Solo para opción A)", placeholder="Actualización por cambio en DS594")
                archivo_ind = st.file_uploader("Subir Archivo Definitivo (PDF firmado)", type=['pdf'])

                if st.form_submit_button("Aprobar e Incorporar al SGI", use_container_width=True, type="primary"):
                    if not nombre_doc:
                        st.error("El Título del documento es obligatorio.")
                    else:
                        sub_area_cl = sub_area.upper().strip() if sub_area else "S/A"
                        sig_cl = neg_sigla.upper().strip() if neg_sigla else "GEN"
                        cod_to_save = f"{emp_sigla}-{cat_full.split(':')[0]}-{sub_area_cl}-{sig_cl}-{correlativo}".upper()
                        
                        path_final = ""
                        if archivo_ind:
                            ruta_base = obtener_ruta_procedimientos(emp_nom, contrato=con_nom)
                            path_final = os.path.join(ruta_base, f"{cod_to_save}_Rev{version}.pdf")
                            with open(path_final, "wb") as f: f.write(archivo_ind.getbuffer())

                        # Buscar si documento existe
                        ex_check = ejecutar_query(DB_PATH, "SELECT version FROM procedimientos WHERE codigo = ?", (cod_to_save,))
                        
                        if ex_check:
                            old_version = ex_check[0][0]
                            if "A) Obsolecer" in tipo_cambio:
                                # Guardar histórico
                                ejecutar_query(DB_PATH, "INSERT INTO sgi_historial_versiones (codigo_doc, version_antigua, motivo_cambio, modificado_por, empresa_id) VALUES (?, ?, ?, ?, ?)",
                                              (cod_to_save, old_version, motivo if motivo else "Actualización General/Anual", st.session_state.user_login, emp_id), commit=True)
                            
                            query_upd = """UPDATE procedimientos SET nombre=?, version=?, fecha_creacion=?, fecha_vencimiento=?, categoria=?, ambito=?, sigla_negocio=?, correlativo=?, sub_area=?, estado_doc=?, empresa=?, empresa_id=?, contrato_id=? """
                            params_upd = [nombre_doc.upper(), version, str(f_c), str(f_v), cat_full, sig_cl, sig_cl, correlativo, sub_area_cl, estado_doc, emp_nom, emp_id, filtros.get('contrato_id')]
                            
                            if path_final:
                                query_upd += ", path=? WHERE codigo = ?"
                                params_upd.extend([path_final, cod_to_save])
                            else:
                                query_upd += " WHERE codigo = ?"
                                params_upd.append(cod_to_save)
                                
                            ejecutar_query(DB_PATH, query_upd, tuple(params_upd), commit=True)
                            registrar_log(DB_PATH, st.session_state.user_login, "SGI_UPDATE_VERSION", f"Rev {version} de {cod_to_save}")
                            st.success(f"Documento matriz sobrescrito para {cod_to_save}.")
                        else:
                            query_ins = """INSERT INTO procedimientos (codigo, nombre, version, fecha_creacion, fecha_vencimiento, categoria, ambito, sigla_negocio, correlativo, sub_area, estado_doc, path, empresa, empresa_id, contrato_id) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"""
                            params_ins = (cod_to_save, nombre_doc.upper(), version, str(f_c), str(f_v), cat_full, sig_cl, sig_cl, correlativo, sub_area_cl, estado_doc, path_final, emp_nom, emp_id, filtros.get('contrato_id'))
                            ejecutar_query(DB_PATH, query_ins, params_ins, commit=True)
                            registrar_log(DB_PATH, st.session_state.user_login, "SGI_UPLOAD", f"Alta documental: {cod_to_save}")
                            st.success("Nuevo documento central integrado al SGI.")
                        
                        time.sleep(1)
                        st.rerun()
