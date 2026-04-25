import os
import sqlite3
import unicodedata
from datetime import datetime, timedelta
import pandas as pd
import streamlit as st

from src.infrastructure.archivos import obtener_ruta_entidad, validar_archivo_seguro
from src.infrastructure.database import ejecutar_query, obtener_dataframe, upsert_registro
from core.excel_master import cargar_maestro_filtrado
from core.utils import is_valid_context, show_context_warning, get_scoping_params

def normalizar(txt):
    if pd.isna(txt) or txt is None: return ""
    s = str(txt).strip().upper()
    return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')

def render_trazabilidad_epp(DB_PATH):
    categoria_seleccionada = "EPP"
    filtros = st.session_state.get('filtros', {'empresa_id': 0, 'empresa_nom': None, 'contrato_id': 0, 'contrato_nom': None, 'busqueda_global': ''})
    # Scoping y Filtros
    es_master, scoped_emp_id, where_clause = get_scoping_params(filtros)
    
    st.markdown(f"<h2 style='color: var(--cgt-blue);'>🦺 Gestión de EPP y Certificaciones</h2>", unsafe_allow_html=True)
    st.write("Control de vida útil para EPP críticos (Dieléctricos, Líneas de Vida, etc.)")

    if filtros.get('empresa_nom'):
        st.info(f"🔍 Filtrado Activo: **{filtros['empresa_nom']}**" + (f" | **{filtros['contrato_nom']}**" if filtros.get('contrato_nom') else ""))
    st.divider()

    # ── RESUMEN EJECUTIVO DE EPP ──
    st.markdown("### 📊 Inventario y Estado de Certificaciones")
    
    query_inv = f"SELECT identificador, nombre, estado_obs, asignado_a, fecha_vencimiento FROM registros WHERE categoria=? {where_clause}"
    params_inv = [categoria_seleccionada]
    if scoped_emp_id > 0: params_inv.append(scoped_emp_id)
        
    df_inv = obtener_dataframe(DB_PATH, query_inv, tuple(params_inv))
    
    if not df_inv.empty:
        # Formatear para visualización premium
        df_inv['fecha_vencimiento'] = pd.to_datetime(df_inv['fecha_vencimiento']).dt.date
        hoy = datetime.now().date()
        
        def semaforo_epp(f_v):
            if pd.isna(f_v): return "⚪ Sin Fecha"
            if f_v < hoy: return "🔴 VENCIDO"
            if (f_v - hoy).days < 30: return "🟡 POR VENCER"
            return "🟢 VIGENTE"
            
        df_inv['Salud'] = df_inv['fecha_vencimiento'].apply(semaforo_epp)
        
        st.dataframe(df_inv, use_container_width=True, hide_index=True, column_config={
            "identificador": "ID/Serie",
            "nombre": "Descripción",
            "estado_obs": "Ubicación/Estado",
            "asignado_a": "Responsable",
            "fecha_vencimiento": "Vencimiento",
            "Salud": st.column_config.TextColumn("Salud 🛡️", help="Estado de certificación Ull-Trone")
        })
    else:
        st.info("No hay elementos de EPP registrados aún. Utilice el formulario inferior para comenzar.")

    st.divider()

    # 1. Selector de Activo / Nuevo
    with st.container(border=True):
        st.markdown("### 🗃️ Registro de EPP")
        
        query_sql = f"SELECT DISTINCT identificador, nombre FROM registros WHERE categoria=? {where_clause}"
        params_sql = [categoria_seleccionada]
        if scoped_emp_id > 0: params_sql.append(scoped_emp_id)

        df_creados = obtener_dataframe(DB_PATH, query_sql, tuple(params_sql))
        
        id_final, nombre_final = "", ""
        if not df_creados.empty:
            df_creados['pildora'] = df_creados['identificador'] + " - " + df_creados['nombre']
            seleccion = st.selectbox("Seleccionar EPP registrado:", ["-- Nuevo --"] + df_creados['pildora'].tolist())
            if seleccion != "-- Nuevo --":
                id_final = seleccion.split(" - ")[0]
                nombre_final = seleccion.split(" - ")[1]
        
        if not id_final:
            st.info("Ingresa un nuevo elemento (Ej: Guante Dieléctrico #001)")
            c1, c2 = st.columns(2)
            id_final = c1.text_input("Código Único / Serie:")
            nombre_final = c2.text_input("Descripción (Ej: Guantes Clase 2):")

    if id_final and nombre_final:
        st.divider()
        
        # Cargar datos actuales del registro
        df_reg = obtener_dataframe(DB_PATH, "SELECT * FROM registros WHERE identificador = ? AND categoria = ? LIMIT 1", (id_final, categoria_seleccionada))
        
        current_state = "En Bodega"
        current_worker = "N/A"
        current_fecha_cert = datetime.now().date()
        current_fecha_uso = None
        
        if not df_reg.empty:
            current_state = df_reg.iloc[0].get('estado_obs', 'En Bodega')
            current_worker = df_reg.iloc[0].get('asignado_a', 'N/A')
            try: current_fecha_cert = pd.to_datetime(df_reg.iloc[0].get('fecha_condicion')).date()
            except: pass
            try: current_fecha_uso = pd.to_datetime(df_reg.iloc[0].get('fecha_carga')).date()
            except: pass

        st.markdown(f"### 📋 Estado de: {nombre_final} ({id_final})")
        
        with st.form("form_epp_logic"):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                nuevo_estado = st.selectbox("Estado Actual:", ["En Bodega", "Asignado a Trabajador"], index=0 if current_state == "En Bodega" else 1)
            
            with col2:
                # Cargar lista de personal para asignar
                df_personal = obtener_dataframe(DB_PATH, "SELECT DISTINCT nombre FROM registros WHERE categoria = 'Personal'")
                listado_p = ["N/A"] + df_personal['nombre'].tolist() if not df_personal.empty else ["N/A"]
                idx_p = listado_p.index(current_worker) if current_worker in listado_p else 0
                nuevo_trabajador = st.selectbox("Asignado a:", listado_p, index=idx_p, disabled=(nuevo_estado == "En Bodega"))
            
            with col3:
                fecha_cert = st.date_input("Fecha Certificación / Ingreso Bodega:", value=current_fecha_cert)
            
            col4, col5 = st.columns(2)
            with col4:
                # Streamlit date_input doesn't like None, we default to today if not set
                def_uso = current_fecha_uso if current_fecha_uso else datetime.now().date()
                fecha_uso = st.date_input("Fecha Inicio de Uso (Si aplica):", value=def_uso)
            
            with col5:
                # Cálculo de Vencimiento
                if nuevo_estado == "En Bodega":
                    vencimiento = fecha_cert + timedelta(days=365) # 1 año
                    st.info(f"💡 Vencimiento en Bodega (1 año): **{vencimiento}**")
                else:
                    ref_fecha = fecha_uso if fecha_uso else datetime.now().date()
                    vencimiento = ref_fecha + timedelta(days=180) # 6 meses
                    st.info(f"💡 Vencimiento en Uso (6 meses): **{vencimiento}**")

            if st.form_submit_button("Actualizar Trazabilidad y Certificación"):
                # Upsert
                upsert_registro(DB_PATH, {
                    "identificador": id_final,
                    "nombre": nombre_final,
                    "tipo_doc": "Certificación Técnica",
                    "categoria": categoria_seleccionada,
                    "fecha_vencimiento": vencimiento,
                    "fecha_condicion": fecha_cert, # Usamos esto para cert
                    "fecha_carga": fecha_uso, # Usamos esto para inicio uso
                    "estado_obs": nuevo_estado,
                    "asignado_a": nuevo_trabajador,
                    "empresa": filtros.get('empresa_nom', 'EMPRESA_GENERAL'),
                    "contrato": filtros.get('contrato_nom', 'CONTRATO_GENERAL'),
                    "session_empresa_id": filtros.get('empresa_id', 0),
                    "session_contrato_id": filtros.get('contrato_id', 0)
                })
                st.success("✅ Datos de EPP actualizados.")
                st.rerun()
        
        st.caption("ℹ️ Los cambios realizados aquí se consolidan en la base de datos central. Puede exportar el listado actualizado desde el Centro de Reportes.")
        st.divider()
        st.markdown("### 📂 Documentación")
        # Mostrar y subir PDF de certificación
        df_docs = obtener_dataframe(DB_PATH, "SELECT id, path FROM registros WHERE identificador = ? AND tipo_doc = 'Certificación Técnica'", (id_final,))
        
        if not df_docs.empty and df_docs.iloc[0]['path'] and os.path.exists(df_docs.iloc[0]['path']):
            st.success("📄 Certificado cargado correctamente.")
            with open(df_docs.iloc[0]['path'], "rb") as f:
                st.download_button("📥 Descargar Certificado", f, f"Certificado_{id_final}.pdf", use_container_width=True)
        else:
            st.warning("⚠️ Falta cargar el certificado PDF.")
            up_cert = st.file_uploader("Subir Certificado (PDF/Imagen):", type=['pdf', 'jpg', 'png'])
            if up_cert and st.button("Guardar Certificado"):
                ruta_base = obtener_ruta_entidad(filtros.get('empresa_nom'), categoria_seleccionada, id_final, contrato=filtros.get('contrato_nom'))
                os.makedirs(ruta_base, exist_ok=True)
                path_dest = os.path.join(ruta_base, f"Cert_{id_final}_{datetime.now().strftime('%Y%m%d')}.pdf")
                with open(path_dest, "wb") as f: f.write(up_cert.getbuffer())
                ejecutar_query(DB_PATH, "UPDATE registros SET path = ? WHERE identificador = ? AND tipo_doc = 'Certificación Técnica'", (path_dest, id_final), commit=True)
                st.success("Certificado guardado.")
                st.rerun()
