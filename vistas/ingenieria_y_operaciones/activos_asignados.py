import os
import sqlite3
import unicodedata
from datetime import datetime

import pandas as pd
import streamlit as st

from src.infrastructure.archivos import obtener_ruta_entidad
from src.infrastructure.database import ejecutar_query, obtener_dataframe, upsert_registro
from core.reports import generar_qr


def render_activos_asignados(DB_PATH, filtros):
    # Categoria extraida de filtros o valor por defecto
    categoria_seleccionada = filtros.get('categoria', 'ACTIVOS_ASIGNADOS')
    
    # --- CÁLCULO DE MÉTRICAS DE ACTIVOS ---
    is_master = st.session_state.role in ["Global Admin", "Admin", "Administrador"]
    q_stats = "SELECT COUNT(DISTINCT identificador) as total, COUNT(*) as total_docs, SUM(CASE WHEN path IS NOT NULL AND path != '' AND path != 'Sin archivo' THEN 1 ELSE 0 END) as docs_ok FROM registros WHERE categoria=?"
    p_s = [categoria_seleccionada]
    if not is_master:
        q_stats += " AND empresa_id = ?"
        p_s.append(st.session_state.empresa_id)
    elif filtros.get('empresa_id') and filtros['empresa_id'] > 0:
        q_stats += " AND empresa_id = ?"
        p_s.append(filtros['empresa_id'])
    
    df_astats = obtener_dataframe(DB_PATH, q_stats, tuple(p_s))
    total_a = df_astats['total'].iloc[0] if not df_astats.empty else 0
    total_docs = df_astats['total_docs'].iloc[0] if not df_astats.empty else 0
    docs_ok = df_astats['docs_ok'].iloc[0] if not df_astats.empty else 0
    health_score = (docs_ok / total_docs * 100) if total_docs > 0 else 0

    # --- HEADER DE CONTROL DE ACTIVOS ---
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown(f"""
            <div style='background: #F5F3F0; color: #1F2937; padding: 20px; border-radius: 12px; border-left: 5px solid #3b82f6;'>
                <p style='color: #94a3b8; font-size: 0.75rem; margin: 0; text-transform: uppercase;'>Activos Totales</p>
                <p style='color: white; font-size: 1.8rem; font-weight: 700; margin: 5px 0 0 0;'>{total_a}</p>
            </div>
        """, unsafe_allow_html=True)
    with m2:
        st.markdown(f"""
            <div style='background: #F5F3F0; color: #1F2937; padding: 20px; border-radius: 12px; border-left: 5px solid #10b981;'>
                <p style='color: #94a3b8; font-size: 0.75rem; margin: 0; text-transform: uppercase;'>Health Score</p>
                <p style='color: #10b981; font-size: 1.8rem; font-weight: 700; margin: 5px 0 0 0;'>{health_score:.1f}%</p>
            </div>
        """, unsafe_allow_html=True)
    with m3:
        st.markdown(f"""
            <div style='background: #F5F3F0; color: #1F2937; padding: 20px; border-radius: 12px; border-left: 5px solid #f59e0b;'>
                <p style='color: #94a3b8; font-size: 0.75rem; margin: 0; text-transform: uppercase;'>Documentación OK</p>
                <p style='color: white; font-size: 1.8rem; font-weight: 700; margin: 5px 0 0 0;'>{docs_ok}</p>
            </div>
        """, unsafe_allow_html=True)
    with m4:
        st.markdown(f"""
            <div style='background: #F5F3F0; color: #1F2937; padding: 20px; border-radius: 12px; border-left: 5px solid #06b6d4;'>
                <p style='color: #94a3b8; font-size: 0.75rem; margin: 0; text-transform: uppercase;'>QR Cobertura</p>
                <p style='color: #06b6d4; font-size: 1.8rem; font-weight: 700; margin: 5px 0 0 0;'>92%</p>
            </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    col_id = "TAG / Código SAP"
    col_nom = "Sistema / Equipo"

    id_final, nombre_final, empresa_final, contrato_final, detalle_final = "", "", "", "", ""
    opciones_doc = ["Planos As-Built", "Certificado de Aislación", "Pauta de Mantenimiento", "Manual de Operación", "Certificado de Calibración", "Memoria de Cálculo", "Otros"]

    with st.container(border=True):
        st.markdown("### 🗃️ Directorio Rápido (Activos Críticos)")
        query_sql = "SELECT DISTINCT identificador, nombre FROM registros WHERE categoria=?"
        params_sql = [categoria_seleccionada]

        is_master = st.session_state.get('role') in ["Global Admin", "Admin", "Administrador"]
        if not is_master:
            query_sql += " AND empresa_id = ?"
            params_sql.append(st.session_state.empresa_id)
        elif filtros.get('empresa_id') and filtros['empresa_id'] > 0:
            query_sql += " AND empresa_id = ?"
            params_sql.append(filtros['empresa_id'])

        if filtros.get('contrato_id') and filtros['contrato_id'] > 0:
            query_sql += " AND contrato_id = ?"
            params_sql.append(filtros['contrato_id'])

        df_creados = obtener_dataframe(DB_PATH, query_sql, tuple(params_sql))

        seleccion_rapida = None
        if not df_creados.empty:
            df_creados['pildora'] = df_creados['identificador'] + " - " + df_creados['nombre']
            seleccion_rapida = st.pills("Selecciona un activo ya registrado:", df_creados['pildora'].tolist(), key="pills_activos")
        else:
            st.info("Aún no hay activos críticos asignados en esta base de datos.")

        st.divider()
        st.info("📝 Ingreso manual de datos para: Activos del Cliente")

        if seleccion_rapida:
            id_final = seleccion_rapida.split(" - ")[0]
            nombre_final = seleccion_rapida.split(" - ")[1]
            st.success(f"✅ Cargando expediente activo de: **{nombre_final}**")
        else:
            c1, c2, c3 = st.columns([1, 1.5, 1])
            with c1: id_final = st.text_input(f"🔢 {col_id}:")
            with c2: nombre_final = st.text_input(f"📋 {col_nom}:")
            with c3: detalle_final = st.text_input("💼 Sub-Tipo / Área:")

            c4, c5 = st.columns(2)
            with c4: empresa_final = st.text_input("🏢 Empresa de Cargo:", value=filtros.get('empresa_nom') if filtros.get('empresa_nom') else "", disabled=True)
            with c5: contrato_final = st.text_input("📄 Contrato de Cargo:", value=filtros.get('contrato_nom') if filtros.get('contrato_nom') else "", disabled=True)

    if id_final and nombre_final:
        st.divider()
        st.markdown(f"### 🪪 Perfil del Activo Asignado", unsafe_allow_html=True)

        with st.container(border=True):
            df_existentes = obtener_dataframe(DB_PATH, "SELECT tipo_doc FROM registros WHERE identificador=?", (id_final,))

            if df_existentes.empty:
                st.info("💡 Este activo no tiene documentos técnicos asociados. Define qué documentos son **Críticos** para su operación.")
                docs_exigidos = st.multiselect("📌 Seleccionar Documentos Técnicos Exigibles:", opciones_doc)
                if st.button("🚀 Crear Perfil de Activo", use_container_width=True):
                    if docs_exigidos:
                        for doc_req in docs_exigidos:
                            upsert_registro(DB_PATH, {
                                "identificador": id_final,
                                "nombre": nombre_final,
                                "tipo_doc": doc_req,
                                "categoria": categoria_seleccionada,
                                "fecha_carga": datetime.now().date(),
                                "fecha_vencimiento": "2000-01-01",
                                "observaciones": "Falta documento técnico",
                                "detalle": detalle_final,
                                "empresa": empresa_final,
                                "contrato": contrato_final,
                                "session_empresa_id": filtros.get('empresa_id', 0),
                                "session_contrato_id": filtros.get('contrato_id', 0)
                            })
                        st.success("✅ Activo creado con éxito.")
                        st.rerun()
                    else:
                        st.warning("Selecciona al menos un documento para crear el perfil base.")
            else:
                with st.expander("➕ Añadir nuevos requerimientos técnicos a este activo"):
                    docs_ya_exigidos = df_existentes['tipo_doc'].tolist()
                    opciones_restantes = [d for d in opciones_doc if d not in docs_ya_exigidos]

                    docs_exigidos_extra = st.multiselect("📌 Seleccionar Nuevas Exigencias:", opciones_restantes, key="extra_docs_act")
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
                                    "observaciones": "Falta documento técnico",
                                    "detalle": detalle_final,
                                    "empresa": empresa_final,
                                    "contrato": contrato_final,
                                    "session_empresa_id": filtros.get('empresa_id', 0),
                                    "session_contrato_id": filtros.get('contrato_id', 0)
                                })
                            st.success("✅ Exigencias extra asignadas con éxito.")
                            st.rerun()

            if not empresa_final or empresa_final in ["None", "", "--- TODAS LAS EMPRESAS ---"]:
                res_eid = ejecutar_query(DB_PATH, "SELECT empresa_id FROM registros WHERE identificador = ? LIMIT 1", (id_final,))
                if res_eid:
                    res_enom = ejecutar_query(DB_PATH, "SELECT nombre FROM empresas WHERE id = ?", (res_eid[0][0] if isinstance(res_eid[0], (list, tuple)) else res_eid[0],))
                    if res_enom:
                        empresa_final = res_enom[0][0] if isinstance(res_enom[0], (list, tuple)) else res_enom[0]

            if not empresa_final or empresa_final in ["None", "", "--- TODAS LAS EMPRESAS ---"]:
                st.warning("⚠️ No se puede determinar la Empresa a cargo de este activo. Por favor, selecciona una Empresa en el Filtro Lateral.")
                return

            ruta_base_entidad = obtener_ruta_entidad(empresa_final, categoria_seleccionada, id_final, contrato=contrato_final)
            ruta_fotos = os.path.join(ruta_base_entidad, "Fotos")
            os.makedirs(ruta_fotos, exist_ok=True)

            foto_perfil = None
            for file in os.listdir(ruta_fotos):
                if file.lower().startswith(f"perfil_{id_final}".lower()):
                    foto_perfil = os.path.join(ruta_fotos, file)
                    break

            st.markdown("<br>", unsafe_allow_html=True)
            # --- CARD PREMIUM DEL ACTIVO ---
            st.markdown(f"""
                <div style='background: #F5F3F0; color: #1F2937; padding: 25px; border-radius: 15px; border: 1px solid #d4d4d8; margin-bottom: 20px;'>
                    <div style='display: flex; justify-content: space-between; align-items: flex-start;'>
                        <div style='display: flex; gap: 20px;'>
                            <div style='width: 120px; height: 120px; background: #334155; border-radius: 10px; overflow: hidden; display: flex; align-items: center; justify-content: center;'>
                                {"<img src='data:image/png;base64,...' style='width:100%; height:100%; object-fit:cover;'>" if foto_perfil else "<span style='color:#94a3b8; font-size:2rem;'>⚙️</span>"}
                            </div>
                            <div>
                                <h3 style='color: white; margin: 0; font-size: 1.5rem;'>{nombre_final}</h3>
                                <p style='color: #3b82f6; font-weight: 600; margin: 5px 0;'>TAG: {id_final}</p>
                                <p style='color: #94a3b8; font-size: 0.85rem; margin: 2px 0;'>📦 Tipo: {detalle_final if detalle_final else 'N/A'}</p>
                                <p style='color: #94a3b8; font-size: 0.85rem; margin: 2px 0;'>🏢 Empresa: {empresa_final}</p>
                            </div>
                        </div>
                        <div style='text-align: right;'>
                            <span style='background: #10b98122; color: #10b981; padding: 5px 15px; border-radius: 20px; font-size: 0.75rem; font-weight: 700; border: 1px solid #10b981;'>ESTADO: OPERATIVO</span>
                        </div>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            
            c_qr, c_ph = st.columns([1, 1])
            with c_qr:
                if st.button("🔲 Generar Código QR (Control Terreno)", use_container_width=True):
                    texto_qr = f"CGT | {empresa_final} | {categoria_seleccionada} | TAG: {id_final} | {nombre_final}"
                    qr_img = generar_qr(texto_qr)
                    st.image(qr_img, width=150)
                    st.download_button("📥 Descargar QR", data=qr_img, file_name=f"QR_{id_final}.png", mime="image/png", use_container_width=True)
            with c_ph:
                foto_up = st.file_uploader("Actualizar Fotografía Técnica", type=['jpg', 'png', 'jpeg'], key=f"up_foto_{id_final}")
                if foto_up and st.button("💾 Guardar Foto"):
                    extension = os.path.splitext(foto_up.name)[1]
                    path_foto = os.path.join(ruta_fotos, f"perfil_{id_final}{extension}")
                    with open(path_foto, "wb") as f: f.write(foto_up.getbuffer())
                    st.success("Foto guardada.")
                    st.rerun()

        st.markdown(f"### 📂 Expediente Técnico Documental", unsafe_allow_html=True)
        tab_estado, tab_carga = st.tabs(["📊 Estado de Documentos", "➕ Cargar / Actualizar Documentos"])

        with tab_estado:
            with st.container(border=True):
                df_docs = obtener_dataframe(DB_PATH, "SELECT id, tipo_doc, fecha_vencimiento, estado_obs, fecha_condicion, path FROM registros WHERE identificador=?", (id_final,))

                if not df_docs.empty:
                    hoy = datetime.now().date()
                    for _, row_doc in df_docs.iterrows():
                        tipo = row_doc['tipo_doc']
                        vto_str = str(row_doc['fecha_vencimiento'])
                        estado_obs = str(row_doc['estado_obs'])
                        ruta_doc = str(row_doc['path'])
                        doc_id = row_doc['id']

                        icono, color_alerta, txt_estado, fecha_mostrar = "✅", "success", "Vigente", vto_str

                        try:
                            f_vto = datetime.strptime(vto_str, '%Y-%m-%d').date()
                            if f_vto < hoy and f_vto != datetime(2000, 1, 1).date():
                                icono, color_alerta, txt_estado = "🚨", "error", "Vencido"
                            elif f_vto == datetime(2000, 1, 1).date() or "Sin archivo" in ruta_doc:
                                icono, color_alerta, txt_estado, fecha_mostrar = "🟥", "error", "Pendiente de Carga", "N/A"
                        except: pass

                        with st.container(border=True):
                            col_st, col_tit, col_f, col_btn1, col_btn2 = st.columns([0.6, 3, 2, 1.2, 0.5])
                            with col_st:
                                if color_alerta == "success": st.success(icono)
                                elif color_alerta == "warning": st.warning(icono)
                                else: st.error(icono)
                            with col_tit: st.markdown(f"**{tipo}**<br><small>{txt_estado}</small>", unsafe_allow_html=True)
                            with col_f: st.markdown(f"🗓️ Válido hasta: `{fecha_mostrar}`")

                            with col_btn1:
                                if ruta_doc and "Sin archivo" not in ruta_doc and os.path.exists(ruta_doc):
                                    with open(ruta_doc, "rb") as file:
                                        ext = os.path.splitext(ruta_doc)[1]
                                        st.download_button("📥 Descargar", data=file, file_name=f"{tipo.replace(' ', '_')}_{id_final}{ext}", mime="application/octet-stream", key=f"dl_{doc_id}", use_container_width=True)
                                else:
                                    st.button("📄 Sin Archivo", disabled=True, key=f"dl_dis_{doc_id}", use_container_width=True)

                            with col_btn2:
                                if st.button("🗑️", key=f"del_{doc_id}", help="Eliminar requerimiento técnico"):
                                    ejecutar_query(DB_PATH, "DELETE FROM registros WHERE id=?", (doc_id,), commit=True)
                                    if os.path.exists(ruta_doc) and "Sin archivo" not in ruta_doc:
                                        try: os.remove(ruta_doc)
                                        except: pass
                                    st.rerun()
                else:
                    st.info("No hay documentos registrados para este activo.")

        with tab_carga:
            with st.container(border=True):
                docs_a_cargar = st.multiselect("📋 Seleccionar Documentos a Subir:", opciones_doc)

                if docs_a_cargar:
                    datos_a_guardar = []
                    for doc in docs_a_cargar:
                        safe_doc_key = "".join([c for c in doc if c.isalnum()])
                        with st.expander(f"📄 Subir archivo para: {doc}", expanded=True):
                            c1, c2 = st.columns([1, 1])
                            with c1: archivo_ind = st.file_uploader(f"📎 PDF/Img de {doc}:", type=['pdf', 'jpg', 'png'], key=f"file_{safe_doc_key}_{id_final}")
                            with c2: fecha_vto_ind = st.date_input("📅 Fecha de Vencimiento / Caducidad:", key=f"vto_{safe_doc_key}_{id_final}")
                            observaciones_ind = st.text_area("📝 Notas Técnicas (Opcional):", key=f"obs_g_{safe_doc_key}_{id_final}")

                            datos_a_guardar.append({
                                "tipo_doc": doc, "file_obj": archivo_ind, "fecha_vto": fecha_vto_ind,
                                "observaciones": observaciones_ind, "estado_obs": "Resuelta", "tiene_obs": "No"
                            })

                    st.divider()
                    if st.button("💾 GUARDAR DOCUMENTOS TÉCNICOS", use_container_width=True, type="primary"):
                        faltan_archivos = [d["tipo_doc"] for d in datos_a_guardar if d["file_obj"] is None]
                        if faltan_archivos: st.error(f"❌ Falta adjuntar el archivo para: **{', '.join(faltan_archivos)}**")
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
                                        "identificador": id_final, "nombre": nombre_final, "tipo_doc": dato["tipo_doc"],
                                        "path": path, "categoria": categoria_seleccionada, "fecha_carga": datetime.now().date(),
                                        "fecha_vencimiento": dato["fecha_vto"], "observaciones": dato["observaciones"],
                                        "fecha_condicion": None, "estado_obs": dato["estado_obs"], "tiene_observacion": dato["tiene_obs"],
                                        "detalle": detalle_final, "empresa": empresa_final, "contrato": contrato_final,
                                        "session_empresa_id": filtros.get('empresa_id', 0),
                                        "session_contrato_id": filtros.get('contrato_id', 0)
                                    })
                                st.success(f"✅ ¡Éxito! Se guardaron {len(datos_a_guardar)} documento(s).")
                                st.rerun()
                            except Exception as e: st.error(f"❌ Ocurrió un error al guardar: {e}")
