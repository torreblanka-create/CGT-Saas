import os
import sqlite3
import unicodedata
from datetime import datetime

import pandas as pd
import streamlit as st

from src.infrastructure.archivos import obtener_ruta_entidad
from config.config import DOCS_OBLIGATORIOS
from src.infrastructure.database import ejecutar_query, obtener_dataframe, upsert_registro
from core.excel_master import cargar_maestro_filtrado
from core.reports import generar_qr
from core.utils import is_valid_context, show_context_warning


def normalizar(txt):
    if pd.isna(txt) or txt is None: return ""
    s = str(txt).strip().upper()
    return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')

def render_trazabilidad_instrumentos(DB_PATH):
    categoria_seleccionada = "Instrumentos y Metrología"
    filtros = st.session_state.get('filtros', {'empresa_id': 0, 'empresa_nom': None, 'contrato_id': 0, 'contrato_nom': None, 'busqueda_global': ''})
    st.markdown(f"<h2 style='color: var(--cgt-blue);'>🛡️ Trazabilidad: Instrumentos y Metrología</h2>", unsafe_allow_html=True)

    if filtros.get('empresa_nom'):
        st.info(f"🔍 Filtrado Activo: **{filtros['empresa_nom']}**" + (f" | **{filtros['contrato_nom']}**" if filtros.get('contrato_nom') else ""))
    st.divider()

    df_full = cargar_maestro_filtrado(
        categoria_seleccionada,
        empresa_sel=filtros.get('empresa_nom'),
        contrato_sel=filtros.get('contrato_nom')
    )
    df_f = df_full.copy()

    col_id, col_nom = "Identificador", "Nombre"
    id_final, nombre_final, empresa_final, contrato_final, detalle_final = "", "", "", "", ""

    opciones_doc = ["Certificado de calibración", "Pauta de chequeo", "Otros"]

    with st.container(border=True):
        st.markdown("### 🗃️ Directorio Rápido (Activos Registrados)")
        query_sql = "SELECT DISTINCT identificador, nombre FROM registros WHERE categoria=?"
        params_sql = [categoria_seleccionada]

        is_master = st.session_state.get('role') == "Global Admin"
        if not is_master:
            query_sql += " AND empresa_id = ?"
            params_sql.append(st.session_state.empresa_id)
        elif filtros.get('empresa_id'):
            query_sql += " AND empresa_id = ?"
            params_sql.append(filtros['empresa_id'])

        if filtros.get('contrato_id'):
            query_sql += " AND contrato_id = ?"
            params_sql.append(filtros['contrato_id'])

        df_creados = obtener_dataframe(DB_PATH, query_sql, tuple(params_sql))

        seleccion_rapida = None
        if not df_creados.empty:
            df_creados['pildora'] = df_creados['identificador'] + " - " + df_creados['nombre']
            seleccion_rapida = st.pills("Selecciona un instrumento ya registrado:", df_creados['pildora'].tolist(), key="pills_inst")
        else:
            st.info("Aún no hay instrumentos con expedientes en esta base de datos.")

        st.divider()
        modo = st.radio("🛠️ O buscar / ingresar nuevo registro:", ["🔍 Buscar en Base Maestra (Excel)", "➕ Ingreso Manual"], horizontal=True)

        if seleccion_rapida:
            id_final = seleccion_rapida.split(" - ")[0]
            nombre_final = seleccion_rapida.split(" - ")[1]

            # Recuperar empresa y contrato desde la base de datos
            row_db = ejecutar_query(DB_PATH, "SELECT empresa_id, contrato_id, detalle FROM registros WHERE identificador = ? AND categoria = ? LIMIT 1", (id_final, categoria_seleccionada))
            if row_db:
                emp_db = str(row_db[0][0]).strip() if row_db[0][0] else ""
                con_db = str(row_db[0][1]).strip() if row_db[0][1] else ""
                det_db = str(row_db[0][2]).strip() if row_db[0][2] else ""
                if emp_db and emp_db not in ["None", "nan"]: empresa_final = emp_db
                if con_db and con_db not in ["None", "nan"]: contrato_final = con_db
                if det_db and det_db not in ["None", "nan"]: detalle_final = det_db

            st.success(f"✅ Cargando expediente activo de: **{nombre_final}**")

        elif modo == "🔍 Buscar en Base Maestra (Excel)":
            if df_f.empty:
                st.warning("⚠️ No se encontraron registros para los filtros aplicados en el Excel.")
            else:
                with st.expander(f"⚡ Sincronización Masiva (Cargar a todos desde el Excel)"):
                    if not is_valid_context(filtros):
                        show_context_warning()
                    else:
                        st.info(f"Esta acción revisará las {len(df_f)} filas del Excel y creará las tarjetas 'Pendientes' (Rojas) para todos los elementos que aún no estén en el sistema.")

                        docs_masivos_exigidos = st.multiselect("📌 Selecciona qué documentos serán críticos para todos:", opciones_doc, key="multi_masivo")

                    con_destino_masivo = filtros.get('contrato_nom')
                    if not con_destino_masivo or con_destino_masivo in ["Sin Contrato", "Todos los Contratos"]:
                        from core.excel_master import obtener_contratos_por_empresa
                        listado_contratos = obtener_contratos_por_empresa(filtros.get('empresa_nom', ''))
                        con_destino_masivo = st.selectbox("🎯 Asignar estos registros al contrato:", ["--- Seleccione ---"] + listado_contratos, key="con_masivo_sel")

                    if st.button(f"🚀 Crear Tarjetas para TODOS en Instrumentos", use_container_width=True):
                        if not docs_masivos_exigidos:
                            st.warning("⚠️ Debes seleccionar al menos un documento exigible para crear las tarjetas.")
                        elif con_destino_masivo == "--- Seleccione ---":
                            st.warning("⚠️ Debes seleccionar un contrato de destino para la carga masiva.")
                        else:
                            count_nuevos = 0
                            col_det_excel = next((c for c in df_f.columns if any(x in str(c).lower() for x in ['cargo', 'detalle', 'tipo'])), None)

                            for _, row in df_f.iterrows():
                                id_masivo = str(row[col_id]).strip()
                                nom_masivo = str(row[col_nom]).strip()
                                emp_masivo = str(row['Empresa']).strip() if 'Empresa' in df_f.columns else filtros.get('empresa_nom', '')
                                con_masivo = str(row['Contrato']).strip() if 'Contrato' in df_f.columns else con_destino_masivo
                                det_masivo = str(row[col_det_excel]).strip() if col_det_excel else "No Especificado"

                                res_e = ejecutar_query(DB_PATH, "SELECT id FROM registros WHERE identificador=? LIMIT 1", (id_masivo,))
                                if not res_e:
                                    for doc_req in docs_masivos_exigidos:
                                        upsert_registro(DB_PATH, {
                                            "identificador": id_masivo, "nombre": nom_masivo, "tipo_doc": doc_req,
                                            "categoria": categoria_seleccionada, "estado_obs": "Pendiente",
                                            "empresa": emp_masivo, "contrato": con_masivo,
                                            "fecha_carga": str(datetime.now().date()), "fecha_vencimiento": "2000-01-01",
                                            "observaciones": "Falta documento oficial", "detalle": det_masivo,
                                            "session_empresa_id": filtros.get('empresa_id', 0),
                                            "session_contrato_id": filtros.get('contrato_id', 0)
                                        })
                                    count_nuevos += 1

                            if count_nuevos > 0:
                                st.success(f"✅ ¡Éxito! Se inyectaron {count_nuevos} tarjetas rojas.")
                            else:
                                st.info("👍 Todos los registros de este Excel ya tenían sus tarjetas base creadas.")

                if col_id in df_f.columns and col_nom in df_f.columns:
                    df_f['display'] = df_f[col_id].astype(str) + " | " + df_f[col_nom].astype(str)
                    busqueda = filtros.get('busqueda_global', '').strip().upper()
                    if busqueda: df_f = df_f[df_f['display'].str.upper().str.contains(busqueda, na=False)]

                    if df_f.empty: st.warning(f"No hay resultados para la búsqueda: '{busqueda}'")
                    else:
                        st.markdown("---")
                        st.write("🔍 Buscar un elemento específico desde la Base Maestra:")
                        sel = st.selectbox(f"🎯 Seleccionar de la lista completa:", ["-- Seleccione --"] + df_f['display'].tolist())
                        if sel != "-- Seleccione --":
                            row = df_f[df_f['display'] == sel].iloc[0]
                            id_final = str(row[col_id]).strip()
                            nombre_final = str(row[col_nom]).strip()
                            empresa_final = str(row['Empresa']).strip() if 'Empresa' in df_f.columns else filtros.get('empresa_nom', '')
                            contrato_final = str(row['Contrato']).strip() if 'Contrato' in df_f.columns else filtros.get('contrato_nom', '')
                            col_det_excel = next((c for c in df_f.columns if any(x in str(c).lower() for x in ['cargo', 'detalle', 'tipo'])), None)
                            detalle_final = str(row[col_det_excel]).strip() if col_det_excel else ""
                            st.success(f"✅ Cargando expediente de: **{nombre_final}**")
                else:
                    st.error(f"❌ Faltan las columnas '{col_id}' o '{col_nom}' en la hoja de Excel.")

        elif modo == "➕ Ingreso Manual":
            if not is_valid_context(filtros):
                show_context_warning()
            else:
                st.info(f"📝 Ingreso manual de datos para: Instrumentos")
                c1, c2, c3 = st.columns([1, 1.5, 1])
                with c1: id_final = st.text_input(f"🔢 {col_id}:")
                with c2: nombre_final = st.text_input(f"📋 {col_nom}:")
                with c3: detalle_final = st.text_input("💼 Tipo:")

                c4, c5 = st.columns(2)
                with c4: empresa_final = st.text_input("🏢 Empresa:", value=filtros.get('empresa_nom') if filtros.get('empresa_nom') else "", disabled=True)
                with c5: contrato_final = st.text_input("📄 Contrato:", value=filtros.get('contrato_nom') if filtros.get('contrato_nom') else "", disabled=True)

    if id_final and nombre_final:
        st.divider()
        st.markdown(f"### 🪪 Perfil del Instrumento", unsafe_allow_html=True)

        with st.container(border=True):
            df_existentes = obtener_dataframe(DB_PATH, "SELECT tipo_doc FROM registros WHERE identificador=?", (id_final,))

            if df_existentes.empty:
                st.info("💡 Este elemento no tiene documentos obligatorios asignados. Define qué documentos son **Críticos** para habilitarlo.")
                docs_exigidos = st.multiselect("📌 Seleccionar Documentos Exigibles Iniciales:", opciones_doc)
                if st.button("🚀 Asignar Exigencias y Crear Perfil", use_container_width=True):
                    if docs_exigidos:
                        for doc_req in docs_exigidos:
                            upsert_registro(DB_PATH, {
                                "identificador": id_final,
                                "nombre": nombre_final,
                                "tipo_doc": doc_req,
                                "categoria": categoria_seleccionada,
                                "fecha_carga": datetime.now().date(),
                                "fecha_vencimiento": "2000-01-01",
                                "observaciones": "Falta documento oficial",
                                "detalle": detalle_final,
                                "empresa": empresa_final,
                                "contrato": contrato_final,
                                "session_empresa_id": filtros.get('empresa_id', 0),
                                "session_contrato_id": filtros.get('contrato_id', 0)
                            })

                        # --- MEJORA: ESCRITURA INVERSA EN EXCEL MAESTRO ---
                        if col_id in df_f.columns:
                            ids_excel = df_f[col_id].astype(str).str.strip().tolist()
                            if str(id_final).strip() not in ids_excel:
                                from core.excel_master import (
                                    anexar_registro_maestro_excel,
                                )
                                anexar_registro_maestro_excel(id_final, nombre_final, detalle_final, categoria_seleccionada, empresa_final, contrato_final)
                        # --------------------------------------------------

                        st.success("✅ Exigencias asignadas con éxito. Ahora puedes subir los documentos.")
                        st.rerun()
                    else:
                        st.warning("Selecciona al menos un documento para crear el perfil base.")
            else:
                with st.expander("➕ Añadir nuevas exigencias (Tarjetas Rojas) a este perfil"):
                    docs_ya_exigidos = df_existentes['tipo_doc'].tolist()
                    opciones_restantes = [d for d in opciones_doc if d not in docs_ya_exigidos]

                    docs_exigidos_extra = st.multiselect("📌 Seleccionar Nuevas Exigencias:", opciones_restantes, key="extra_docs")
                    if st.button("➕ Asignar Exigencias Extra", use_container_width=True):
                        if docs_exigidos_extra:
                            for doc_req in docs_exigidos_extra:
                                upsert_registro(DB_PATH, {
                                    "identificador": id_final,
                                    "nombre": nombre_final,
                                    "tipo_doc": doc_req,
                                    "categoria": categoria_seleccionada,
                                    "fecha_carga": datetime.now().date(),
                                    "fecha_vencimiento": "2000-01-01",
                                    "observaciones": "Falta documento oficial",
                                    "detalle": detalle_final,
                                    "empresa": empresa_final,
                                    "contrato": contrato_final,
                                    "session_empresa_id": filtros.get('empresa_id', 0),
                                    "session_contrato_id": filtros.get('contrato_id', 0)
                                })
                            st.success("✅ Exigencias extra asignadas con éxito.")
                            st.rerun()

            # Intento de Recuperación de Empresa si es Administrador Global sin filtros
            if not empresa_final or empresa_final == "--- TODAS LAS EMPRESAS ---" or empresa_final == "None":
                res_eid = ejecutar_query(DB_PATH, "SELECT empresa_id FROM registros WHERE identificador = ? LIMIT 1", (id_final,))
                if res_eid:
                    res_enom = ejecutar_query(DB_PATH, "SELECT nombre FROM empresas WHERE id = ?", (res_eid[0][0] if isinstance(res_eid[0], (list, tuple)) else res_eid[0],))
                    if res_enom:
                        empresa_final = res_enom[0][0] if isinstance(res_enom[0], (list, tuple)) else res_enom[0]

            # Validación Final para evitar EMPRESA_NO_DEFINIDA
            if not empresa_final or empresa_final in ["None", "", "--- TODAS LAS EMPRESAS ---"]:
                st.warning("⚠️ No se puede determinar la Empresa para este activo. Por favor, selecciona una Empresa en el Filtro Lateral.")
                return

            # Validación estricta de Contrato para evitar generación de 'Sin Contrato'
            if not contrato_final or str(contrato_final).strip() in ["None", "", "nan", "Todos los Contratos", "TODOS LOS CONTRATOS", "Sin Contrato", "SIN_CONTRATO"]:
                if filtros.get('contrato_nom') and str(filtros['contrato_nom']).strip() not in ["None", "", "nan", "Todos los Contratos", "TODOS LOS CONTRATOS", "Sin Contrato", "SIN_CONTRATO"]:
                    contrato_final = filtros['contrato_nom']
                else:
                    from core.excel_master import obtener_contratos_por_empresa
                    listado_c = obtener_contratos_por_empresa(empresa_final) if empresa_final else []
                    contrato_final = st.selectbox("⚠️ Este registro no tiene un contrato asignado. Seleccione uno para continuar:", ["-- Seleccione --"] + listado_c)
                    if contrato_final == "-- Seleccione --":
                        st.warning("Por favor, seleccione un contrato válido para poder crear o acceder a los documentos de este perfil.")
                        return


            # Generación de Carpetas y Perfil Visual
            ruta_base_entidad = obtener_ruta_entidad(empresa_final, categoria_seleccionada, id_final, contrato=contrato_final)
            ruta_fotos = os.path.join(ruta_base_entidad, "Fotos")
            os.makedirs(ruta_fotos, exist_ok=True)

            foto_perfil = None
            for file in os.listdir(ruta_fotos):
                if file.lower().startswith(f"perfil_{id_final}".lower()):
                    foto_perfil = os.path.join(ruta_fotos, file)
                    break

            st.markdown("<br>", unsafe_allow_html=True)
            col_foto, col_info, col_actions = st.columns([1.5, 3, 1.5])

            with col_foto:
                st.markdown("<div style='display:flex; justify-content:center;'>", unsafe_allow_html=True)
                if foto_perfil:
                    st.image(foto_perfil, use_container_width=True)
                else:
                    st.info("📷 Sin foto")
                    foto_up = st.file_uploader("Subir Fotografía", type=['jpg', 'png', 'jpeg'], key=f"up_foto_{id_final}", label_visibility="collapsed")

                    if foto_up is not None:
                        if st.button("💾 Guardar y Actualizar Foto", type="primary", key=f"btn_foto_{id_final}"):
                            extension = os.path.splitext(foto_up.name)[1]
                            path_foto = os.path.join(ruta_fotos, f"perfil_{id_final}{extension}")
                            with open(path_foto, "wb") as f:
                                f.write(foto_up.getbuffer())
                            st.success("¡Foto actualizada!")
                            st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)

            with col_info:
                st.markdown(f"**Descripción:** {nombre_final}")
                st.markdown(f"**Código Serie:** {id_final}")
                st.markdown(f"**Tipo:** `{detalle_final}`" if detalle_final else "**Tipo:** N/A")
                st.markdown(f"**Empresa:** {empresa_final}")

            with col_actions:
                st.markdown("<b>🆘 Acceso Rápido</b>", unsafe_allow_html=True)
                with st.popover("🔲 Generar QR", use_container_width=True):
                    st.write("Generar código de acceso rápido:")
                    if st.button("Crear QR", key=f"btn_qr_{id_final}", use_container_width=True):
                        texto_qr = f"CGT | {empresa_final} | {categoria_seleccionada} | ID: {id_final} | {nombre_final} | Tipo: {detalle_final}"
                        qr_img = generar_qr(texto_qr)
                        st.image(qr_img, width=150)
                        st.download_button("📥 Descargar", data=qr_img, file_name=f"QR_{id_final}.png", mime="image/png", key=f"dl_qr_{id_final}", use_container_width=True)

        st.markdown(f"### 📂 Gestor Documental", unsafe_allow_html=True)
        tab_estado, tab_carga = st.tabs(["📊 Estado Documental Actual", "➕ Cargar / Renovar Documentos"])

        with tab_estado:
            st.caption("💡 **Guía de estados:** 🟢 Vigente | 🟡 Alerta / Condicionada | 🔴 Vencida / Pendiente")
            with st.container(border=True):
                df_docs = obtener_dataframe(DB_PATH, "SELECT id, tipo_doc, fecha_vencimiento, estado_obs, fecha_condicion, path FROM registros WHERE identificador=?", (id_final,))

                if not df_docs.empty:
                    hoy = datetime.now().date()
                    for _, row_doc in df_docs.iterrows():
                        tipo = row_doc['tipo_doc']
                        vto_str = str(row_doc['fecha_vencimiento'])
                        cond_str = str(row_doc['fecha_condicion'])
                        estado_obs = str(row_doc['estado_obs'])
                        ruta_doc = str(row_doc['path'])
                        doc_id = row_doc['id']

                        # Lógica de Color / Estado
                        icono = "✅"
                        color_alerta = "success"
                        txt_estado = "Vigente"
                        fecha_mostrar = vto_str

                        try:
                            f_vto = datetime.strptime(vto_str, '%Y-%m-%d').date()
                            if f_vto < hoy and f_vto != datetime(2000, 1, 1).date():
                                icono, color_alerta, txt_estado = "🚨", "error", "Vencido"
                            elif f_vto == datetime(2000, 1, 1).date() or "Sin archivo" in ruta_doc:
                                icono, color_alerta, txt_estado, fecha_mostrar = "🟥", "error", "Pendiente de Carga", "N/A"
                            elif estado_obs == "Pendiente":
                                icono, color_alerta, txt_estado = "⚠️", "warning", "Condicionado"
                                if cond_str and cond_str != 'None':
                                    f_cond = datetime.strptime(cond_str, '%Y-%m-%d').date()
                                    fecha_mostrar = f"{vto_str} (Límite: {cond_str})"
                                    if f_cond < hoy:
                                        icono, color_alerta, txt_estado = "🚨", "error", "Condición Vencida"
                        except: pass

                        with st.container(border=True):
                            col_st, col_tit, col_f, col_btn1, col_btn2 = st.columns([0.6, 3, 2, 1.2, 0.5])
                            with col_st:
                                if color_alerta == "success": st.success(icono)
                                elif color_alerta == "warning": st.warning(icono)
                                else: st.error(icono)
                            with col_tit: st.markdown(f"**{tipo}**<br><small>{txt_estado}</small>", unsafe_allow_html=True)
                            with col_f: st.markdown(f"🗓️ Vto: `{fecha_mostrar}`")

                            with col_btn1:
                                if ruta_doc and "Sin archivo" not in ruta_doc and os.path.exists(ruta_doc):
                                    with open(ruta_doc, "rb") as file:
                                        ext = os.path.splitext(ruta_doc)[1]
                                        st.download_button(label="📥 Descargar", data=file, file_name=f"{tipo.replace(' ', '_')}_{id_final}{ext}", mime="application/octet-stream", key=f"dl_{doc_id}", use_container_width=True)
                                else:
                                    st.button("📄 Sin Archivo", disabled=True, key=f"dl_dis_{doc_id}", use_container_width=True)

                            with col_btn2:
                                # Botón para borrar exigencia
                                if st.button("🗑️", key=f"del_{doc_id}", help="Eliminar este documento del perfil"):
                                    ejecutar_query(DB_PATH, "DELETE FROM registros WHERE id=?", (doc_id,), commit=True)
                                    if os.path.exists(ruta_doc) and "Sin archivo" not in ruta_doc:
                                        try: os.remove(ruta_doc)
                                        except: pass
                                    st.rerun()
                else:
                    st.info("No hay documentos registrados para este activo.")



        with tab_carga:
            if not is_valid_context(filtros):
                show_context_warning()
            else:
                with st.container(border=True):
                    st.info("💡 Selecciona los tipos de documentos que vas a cargar para habilitar sus casillas correspondientes.")
                    docs_a_cargar = st.multiselect("📋 Seleccionar Documentos a Subir:", opciones_doc)

                if docs_a_cargar:
                    st.markdown("#### ⚙️ Adjuntar respaldos")
                    datos_a_guardar = []

                    for doc in docs_a_cargar:
                        safe_doc_key = "".join([c for c in doc if c.isalnum()])
                        with st.expander(f"📄 Configurar: {doc}", expanded=True):
                            c1, c2 = st.columns([1, 1])
                            with c1: archivo_ind = st.file_uploader(f"📎 Respaldo de {doc}:", type=['pdf', 'jpg', 'png'], key=f"file_{safe_doc_key}_{id_final}")
                            with c2: fecha_vto_ind = st.date_input("📅 Fecha de Vencimiento:", key=f"vto_{safe_doc_key}_{id_final}")

                            observaciones_ind, fecha_cond_ind = "", None
                            estado_obs_ind, tiene_obs_ind = "Resuelta", "No"

                            if doc in ["Certificado de calibración"]:
                                st.caption("⚠️ ¿Este documento fue aprobado con observaciones o condiciones?")
                                es_condicionado = st.checkbox("🚩 Marcar como Vigencia Condicionada", key=f"cond_{safe_doc_key}_{id_final}")
                                if es_condicionado:
                                    fecha_cond_ind = st.date_input("📅 Fecha Límite para Subsanar:", key=f"f_cond_{safe_doc_key}_{id_final}")
                                    observaciones_ind = st.text_area("📝 Motivo:", key=f"obs_c_{safe_doc_key}_{id_final}")
                                    estado_obs_ind, tiene_obs_ind = "Pendiente", "Sí"
                                else: observaciones_ind = st.text_area("📝 Observaciones Generales (Opcional):", key=f"obs_g_{safe_doc_key}_{id_final}")

                            datos_a_guardar.append({
                                "tipo_doc": doc, "file_obj": archivo_ind, "fecha_vto": fecha_vto_ind,
                                "observaciones": observaciones_ind, "fecha_cond": fecha_cond_ind,
                                "estado_obs": estado_obs_ind, "tiene_obs": tiene_obs_ind
                            })

                    st.divider()
                    if st.button("💾 GUARDAR DOCUMENTOS EN EL EXPEDIENTE", use_container_width=True, type="primary"):
                        faltan_archivos = [d["tipo_doc"] for d in datos_a_guardar if d["file_obj"] is None]
                        if faltan_archivos: st.error(f"❌ Falta adjuntar el respaldo para: **{', '.join(faltan_archivos)}**")
                        else:
                            try:
                                for dato in datos_a_guardar:
                                    ruta_base = obtener_ruta_entidad(empresa_final, categoria_seleccionada, id_final, contrato=contrato_final)
                                    ruta_documentos = os.path.join(ruta_base, "Documentos_Vigentes")
                                    os.makedirs(ruta_documentos, exist_ok=True)

                                    extension = os.path.splitext(dato["file_obj"].name)[1]
                                    nombre_archivo_final = f"{id_final}_{dato['tipo_doc'].replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{extension}"
                                    path = os.path.join(ruta_documentos, nombre_archivo_final)

                                    with open(path, "wb") as f: f.write(dato["file_obj"].getbuffer())

                                    upsert_registro(DB_PATH, {
                                        "identificador": id_final,
                                        "nombre": nombre_final,
                                        "tipo_doc": dato["tipo_doc"],
                                        "path": path,
                                        "categoria": categoria_seleccionada,
                                        "fecha_carga": datetime.now().date(),
                                        "fecha_vencimiento": dato["fecha_vto"],
                                        "observaciones": dato["observaciones"],
                                        "fecha_condicion": dato["fecha_cond"],
                                        "estado_obs": dato["estado_obs"],
                                        "tiene_observacion": dato["tiene_obs"],
                                        "detalle": detalle_final,
                                        "empresa": empresa_final,
                                        "contrato": contrato_final,
                                        "session_empresa_id": filtros.get('empresa_id', 0),
                                        "session_contrato_id": filtros.get('contrato_id', 0)
                                    })

                                st.success(f"✅ ¡Éxito! Se guardaron {len(datos_a_guardar)} documento(s).")
                            except Exception as e: st.error(f"❌ Ocurrió un error al guardar: {e}")
