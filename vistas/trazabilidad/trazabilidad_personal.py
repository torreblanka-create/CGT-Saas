import os
import sqlite3
import unicodedata
from datetime import datetime

import pandas as pd
import streamlit as st

from src.infrastructure.archivos import obtener_ruta_entidad, validar_archivo_seguro
from config.config import DOCS_OBLIGATORIOS, EPP_DURATION_MAPPING, TIPOS_EPP_GLOBAL
from src.infrastructure.database import ejecutar_query, obtener_dataframe, registrar_log, upsert_registro
from core.excel_master import cargar_maestro_filtrado
from core.reports import generar_qr
from core.utils import is_valid_context, show_context_warning
from intelligence.agents.intelligence_engine import UllTroneEngine
from config.config import LOGO_APP, obtener_logo_cliente


def normalizar(txt):
    if pd.isna(txt) or txt is None: return ""
    s = str(txt).strip().upper()
    return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')

def render_trazabilidad_personal(DB_PATH):
    categoria_seleccionada = "Personal"
    filtros = st.session_state.get('filtros', {'empresa_id': 0, 'empresa_nom': None, 'contrato_id': 0, 'contrato_nom': None, 'busqueda_global': ''})
    
    # --- UI ELITE NEON ONYX ---
    st.markdown("""
        <div class='premium-header'>
            <div style='display: flex; align-items: center; gap: 20px;'>
                <div style='background: rgba(14, 165, 233, 0.1); padding: 15px; border-radius: 12px; border: 1px solid var(--border-glass);'>
                    <span style='font-size: 2.5rem;'>👷</span>
                </div>
                <div>
                    <h1 style='color: var(--text-heading); margin: 0; font-size: 1.8rem; font-family: "Outfit", sans-serif;'>Trazabilidad: Personal y Capital Humano</h1>
                    <p style='color: var(--text-muted); margin: 5px 0 0 0; font-size: 1rem; opacity: 0.9;'>Gestión técnica de acreditaciones, competencias y vigencia de la fuerza laboral.</p>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    if filtros.get('empresa_nom'):
        st.markdown(f"""
            <div style='background: rgba(0, 168, 232, 0.1); padding: 10px; border-radius: 8px; border: 1px solid #00A8E8;'>
                <span style='color: #00A8E8;'>🔍 Centro de Trabajo Activo:</span> 
                <b style='color: #FFF;'>{filtros['empresa_nom']}</b> 
                {f" | <b style='color: #FFF;'>{filtros['contrato_nom']}</b>" if filtros.get('contrato_nom') else ""}
            </div>
            <br>
        """, unsafe_allow_html=True)

    df_full = cargar_maestro_filtrado(
        categoria_seleccionada,
        empresa_sel=filtros.get('empresa_nom'),
        contrato_sel=filtros.get('contrato_nom')
    )
    df_f = df_full.copy()

    col_id, col_nom = "Identificador", "Nombre"
    id_final, nombre_final, empresa_final, contrato_final, detalle_final = "", "", "", "", ""

    opciones_doc = [
        "Contrato de Trabajo y Anexos", "IRL información de riesgos laborales", "Comprobante Entrega RIOHS",
        "Exámenes Médicos Pre u Ocupacionales", "Licencia Municipal", "Licencia Interna",
        "Curso de Trabajo en Altura", "Curso de Primeros Auxilios", "Curso de Manejo de Extintores",
        "Certificación de Operador", "Difusión de Procedimientos", "Planes de Emergencia",
        "Planes de Riesgo de Higiene", "Otros"
    ]

    with st.container(border=True):
        col_t1, col_t2 = st.columns([0.7, 0.3])
        with col_t1:
            st.markdown("### 🗃️ Directorio Rápido (Expedientes Activos)")
            st.caption("Fuerza Laboral actualmente desplegada en los contratos seleccionados.")
        
        with col_t2:
            with st.popover("🧠 Strategic Force Analysis", use_container_width=True):
                st.markdown("#### Consultoría Ull-Trone (Recursos Humanos)")
                if st.button("Analizar Fuerza Laboral (Beta)", type="primary", use_container_width=True):
                    with st.spinner("Escaneando competencias y brechas..."):
                        # Sample count logic
                        total_p = len(df_f)
                        contexto = f"Empresa: {filtros.get('empresa_nom')}. Total Personal: {total_p}. "
                        prompt = f"Analiza esta fuerza laboral: {contexto}. Genera un informe breve (50 palabras) sobre el riesgo de continuidad operacional basado en el cumplimiento documental."
                        reporte = UllTroneEngine.consultar_ia(prompt)
                        st.info(reporte)
        query_sql = "SELECT DISTINCT r.identificador, r.nombre, r.detalle FROM registros r WHERE r.categoria=?"
        params_sql = [categoria_seleccionada]

        is_master = st.session_state.get('role') == "Global Admin"
        if not is_master:
            # Non-master: only their company, never empresa_id=0 which represents Global Admins
            query_sql += " AND r.empresa_id = ?"
            params_sql.append(st.session_state.empresa_id)
        elif filtros.get('empresa_id') and filtros['empresa_id'] > 0:
            # Global Admin with a specific company filter: exact match only (exclude empresa_id=0 system records)
            query_sql += " AND r.empresa_id = ?"
            params_sql.append(filtros['empresa_id'])

        if filtros.get('contrato_id'):
            query_sql += " AND (r.contrato_id = ? OR r.contrato_id = 0 OR r.contrato_id IS NULL)"
            params_sql.append(filtros['contrato_id'])

        df_creados = obtener_dataframe(DB_PATH, query_sql, tuple(params_sql))

        seleccion_rapida = None
        if not df_creados.empty:
            # --- Agrupación por Cargos en GRID de 3 columnas ---
            cargos = sorted([str(c) for c in df_creados['detalle'].unique() if pd.notnull(c) and str(c).strip() != ""])
            if not cargos: cargos = ["General"]

            NUM_COLS = 3
            for i in range(0, len(cargos), NUM_COLS):
                grupo_cargos = cargos[i:i + NUM_COLS]
                cols = st.columns(NUM_COLS)
                for col_idx, cargo in enumerate(grupo_cargos):
                    with cols[col_idx]:
                        df_cargo = df_creados[df_creados['detalle'] == cargo] if cargo != "General" else df_creados[df_creados['detalle'].isna() | (df_creados['detalle'] == "")]
                        if not df_cargo.empty:
                            total = len(df_cargo)
                            st.markdown(f"**💼 {cargo}** `{total}`")
                            df_cargo = df_cargo.copy()
                            df_cargo['pildora'] = df_cargo['identificador'] + " - " + df_cargo['nombre']
                            p_sel = st.pills(f"Integrantes ({cargo})", df_cargo['pildora'].tolist(), key=f"pills_p_{cargo}", label_visibility="collapsed")
                            if p_sel: seleccion_rapida = p_sel

            if not seleccion_rapida and "pills_personal" in st.session_state:
                pass
        else:
            st.info("Aún no hay trabajadores con expedientes en esta base de datos.")

        st.divider()
        modo = st.radio("🛠️ O buscar / ingresar nuevo registro:", ["🔍 Buscar en Base Maestra (Excel)", "➕ Ingreso Manual"], horizontal=True)

        if seleccion_rapida:
            # Si seleccionó del pill, forzar los datos
            id_final = seleccion_rapida.split(" - ")[0]
            nombre_final = seleccion_rapida.split(" - ")[1]

            # Recuperar empresa, contrato y detalle desde la base de datos
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
                        st.info(f"Esta acción revisará las {len(df_f)} filas del Excel y creará las tarjetas 'Pendientes' (Rojas) para todos los trabajadores que aún no estén en el sistema.")

                        # --- INICIO INTEGRACIÓN RESSO ---
                        st.markdown("**🛡️ Configuración Rápida RESSO:**")
                        if st.button("📋 Pre-seleccionar Exigencias Obligatorias RESSO", help="Selecciona automáticamente: IRL, Procedimientos, Emergencia, Higiene"):
                            st.session_state['multi_masivo'] = [
                                "IRL información de riesgos laborales",
                                "Difusión de Procedimientos",
                                "Planes de Emergencia",
                                "Planes de Riesgo de Higiene"
                            ]
                            st.rerun()
                        # --- FIN INTEGRACIÓN RESSO ---

                        docs_masivos_exigidos = st.multiselect("📌 Selecciona qué documentos serán críticos para todos:", opciones_doc, key="multi_masivo")

                    con_destino_masivo = filtros.get('contrato_nom')
                    if not con_destino_masivo or con_destino_masivo in ["Sin Contrato", "Todos los Contratos"]:
                        from core.excel_master import obtener_contratos_por_empresa
                        listado_contratos = obtener_contratos_por_empresa(filtros.get('empresa_nom', ''))
                        con_destino_masivo = st.selectbox("🎯 Asignar estos registros al contrato:", ["--- Seleccione ---"] + listado_contratos, key="con_masivo_sel")

                    if st.button(f"🚀 Crear Tarjetas para TODOS en Personal", use_container_width=True):
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

                                # Verificar si ya existe
                                res_e = ejecutar_query(DB_PATH, "SELECT id FROM registros WHERE identificador=? LIMIT 1", (id_masivo,))
                                if not res_e:
                                    for doc_req in docs_masivos_exigidos:
                                        upsert_registro(DB_PATH, {
                                            "identificador": id_masivo,
                                            "nombre": nom_masivo,
                                            "tipo_doc": doc_req,
                                            "categoria": categoria_seleccionada,
                                            "estado_obs": "Pendiente",
                                            "empresa": emp_masivo,
                                            "contrato": con_masivo,
                                            "fecha_carga": str(datetime.now().date()),
                                            "fecha_vencimiento": "2000-01-01",
                                            "observaciones": "Falta documento oficial",
                                            "detalle": det_masivo,
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
                        st.write("🔍 Buscar un trabajador específico desde la Base Maestra:")
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
                st.info(f"📝 Ingreso manual de datos para: Personal")
                c1, c2, c3 = st.columns([1, 1.5, 1])
                with c1: id_final = st.text_input(f"🔢 {col_id}:")
                with c2: nombre_final = st.text_input(f"📋 {col_nom}:")
                with c3: detalle_final = st.text_input("💼 Cargo / Tipo:")

                c4, c5 = st.columns(2)
                with c4: empresa_final = st.text_input("🏢 Empresa:", value=filtros.get('empresa_nom') if filtros.get('empresa_nom') else "", disabled=True)
                with c5: contrato_final = st.text_input("📄 Contrato:", value=filtros.get('contrato_nom') if filtros.get('contrato_nom') else "", disabled=True)

    if id_final and nombre_final:
        st.divider()
        st.markdown(f"### 🪪 Perfil del Trabajador", unsafe_allow_html=True)

        # Contenedor Tarjeta de Identidad
        with st.container(border=True):
            df_existentes = obtener_dataframe(DB_PATH, "SELECT tipo_doc FROM registros WHERE identificador=?", (id_final,))

            if df_existentes.empty:
                st.info("💡 Este trabajador no tiene documentos obligatorios asignados. Define qué documentos son **Críticos** para habilitarlo.")

                if st.button("📋 Pre-seleccionar Exigencias RESSO", key=f"btn_resso_{id_final}"):
                    st.session_state[f'docs_req_{id_final}'] = [
                        "IRL información de riesgos laborales",
                        "Difusión de Procedimientos",
                        "Planes de Emergencia",
                        "Planes de Riesgo de Higiene"
                    ]
                    st.rerun()

                docs_exigidos = st.multiselect("📌 Seleccionar Documentos Exigibles Iniciales:", opciones_doc, key=f"docs_req_{id_final}")
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

                        registrar_log(DB_PATH, st.session_state.get('user_login', 'Desconocido'), "PERS_CREATE_PROFILE", f"Creado perfil base para {nombre_final} ({id_final})")
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

            # Generación de Carpetas y Perfil Visual
            # Intento de Recuperación de Empresa si es Administrador Global sin filtros
            if not empresa_final or empresa_final == "--- TODAS LAS EMPRESAS ---" or empresa_final == "None":
                res_eid = ejecutar_query(DB_PATH, "SELECT empresa_id FROM registros WHERE identificador = ? LIMIT 1", (id_final,))
                if res_eid:
                    emp_id_val = res_eid[0][0] if isinstance(res_eid[0], (list, tuple)) else res_eid[0]
                    res_enom = ejecutar_query(DB_PATH, "SELECT nombre FROM empresas WHERE id = ?", (emp_id_val,))
                    if res_enom:
                        empresa_final = res_enom[0][0] if isinstance(res_enom[0], (list, tuple)) else res_enom[0]

            # Validación Final para evitar EMPRESA_NO_DEFINIDA
            if not empresa_final or empresa_final in ["None", "", "--- TODAS LAS EMPRESAS ---"]:
                st.warning("⚠️ No se puede determinar la Empresa para esta persona. Por favor, selecciona una Empresa en el Filtro Lateral.")
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


            # Generación de Carpetas y Perfil Visual (Con la corrección de nombre de entidad)
            ruta_base_entidad = obtener_ruta_entidad(empresa_final, categoria_seleccionada, id_final, nombre_entidad=nombre_final, contrato=contrato_final)
            ruta_fotos = os.path.join(ruta_base_entidad, "Fotos")
            os.makedirs(ruta_fotos, exist_ok=True)

            foto_perfil = None
            for file in os.listdir(ruta_fotos):
                if file.lower().startswith(f"perfil_{id_final}".lower()):
                    foto_perfil = os.path.join(ruta_fotos, file)
                    break

            st.markdown(f"""
                <div class='glass-card' style='margin-bottom: 25px;'>
                    <div style='display: flex; align-items: flex-start; gap: 20px;'>
                        <div style='width: 140px; height: 140px; border-radius: 15px; border: 2px solid var(--accent-neon); overflow: hidden; background: var(--bg-main); flex-shrink: 0;'>
                            <div style='display:flex; justify-content:center; align-items:center; height:100%; color:var(--accent-neon);'>📷 Sin Foto</div>
                        </div>
                        <div style='flex-grow: 1;'>
                            <h2 style='color: var(--text-heading); margin: 0;'>{nombre_final}</h2>
                            <p style='color: var(--accent-neon); margin: 5px 0;'>RUT: {id_final}</p>
                            <div style='display: flex; gap: 10px; margin-top: 10px;'>
                                <span style='background: rgba(14, 165, 233, 0.1); color: var(--accent-neon); padding: 4px 12px; border-radius: 20px; font-size: 0.85em;'>💼 {detalle_final or 'Cargo pendiente'}</span>
                                <span style='background: rgba(107, 114, 128, 0.1); color: var(--text-muted); padding: 4px 12px; border-radius: 20px; font-size: 0.85em;'>🏢 {empresa_final}</span>
                            </div>
                        </div>
                        <div style='text-align: right;'>
                            <div style='font-size: 0.85em; color: var(--text-muted); font-weight: 600; letter-spacing: 1px;'>ESTADO TÉCNICO</div>
                            <div style='font-size: 1.6em; color: #10B981; font-weight: 800;'>OPERATIVO</div>
                        </div>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            
            col_foto, col_info, col_actions = st.columns([1.5, 3, 1.5])

            with col_foto:
                st.caption("Cargar nueva imagen de perfil:")
                foto_up = st.file_uploader("Subir", type=['jpg', 'png', 'jpeg'], key=f"up_foto_{id_final}", label_visibility="collapsed")
                if foto_up is not None:
                    if st.button("💾 Actualizar Foto", type="primary", key=f"btn_foto_{id_final}", use_container_width=True):
                        extension = os.path.splitext(foto_up.name)[1]
                        es_valido, msg_error = validar_archivo_seguro(foto_up, [extension])
                        if not es_valido:
                            st.error(f"❌ {msg_error}")
                            st.stop()
                        path_foto = os.path.join(ruta_fotos, f"perfil_{id_final}{extension}")
                        with open(path_foto, "wb") as f:
                            f.write(foto_up.getbuffer())
                        st.success("¡Imagen sincronizada!")
                        st.rerun()

            with col_info:
                st.markdown(f"**Gestión de Contrato:** {contrato_final}")
                st.markdown(f"**Carpeta Digital:** `{id_final}_{nombre_final.replace(' ', '_')}`")

            with col_actions:
                st.markdown("<b>Acciones Estratégicas</b>", unsafe_allow_html=True)
                row_em_results = ejecutar_query(DB_PATH, "SELECT tipo_sangre, contacto, alergias FROM datos_emergencia WHERE identificador=?", (id_final,))
                row_em = row_em_results[0] if row_em_results else None

                with st.popover("🆘 Ficha Médica", use_container_width=True):
                    with st.form(f"form_em_{id_final}"):
                        t_sangre = st.text_input("🩸 Tipo de Sangre", value=row_em[0] if row_em else "")
                        t_contacto = st.text_input("📞 Emergencia (Nombre y Tel)", value=row_em[1] if row_em else "")
                        t_alergias = st.text_input("⚕️ Alergias / Medicamentos", value=row_em[2] if row_em else "")
                        if st.form_submit_button("💾 Guardar Datos", use_container_width=True):
                            ejecutar_query(DB_PATH, "INSERT OR REPLACE INTO datos_emergencia (identificador, tipo_sangre, contacto, alergias) VALUES (?, ?, ?, ?)", (id_final, t_sangre, t_contacto, t_alergias), commit=True)
                            st.rerun()

                with st.popover("🔲 Identidad Digital QR", use_container_width=True):
                    if st.button("Generar Código QR", key=f"btn_qr_{id_final}", use_container_width=True):
                        texto_qr = f"CGT | {empresa_final} | ID: {id_final} | {nombre_final}"
                        st.image(generar_qr(texto_qr), width=150)


        st.markdown(f"### 📂 Gestor Documental", unsafe_allow_html=True)
        tab_estado, tab_carga, tab_epp = st.tabs(["📊 Estado Documental Actual", "➕ Cargar / Renovar Documentos", "🦺 Control EPP"])

        with tab_estado:
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

                with st.container():
                    col_st, col_tit, col_f, col_btn1, col_btn2 = st.columns([0.5, 3, 2, 1, 0.5])
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
                            with st.popover("➕ Subir", use_container_width=True):
                                st.markdown(f"**Subir: {tipo}**")
                                quick_up = st.file_uploader("Seleccionar Archivo:", type=['pdf', 'jpg', 'png'], key=f"qup_{doc_id}")
                                quick_vto = st.date_input("Fecha Vencimiento:", value=datetime.now().date(), key=f"qvto_{doc_id}")
                                if st.button("💾 Guardar", key=f"qsave_{doc_id}", use_container_width=True, type="primary"):
                                    if quick_up:
                                        ext_q = os.path.splitext(quick_up.name)[1]
                                        es_valido, msg_v = validar_archivo_seguro(quick_up, [ext_q])
                                        if not es_valido:
                                            st.error(msg_v)
                                        else:
                                            ruta_base = obtener_ruta_entidad(empresa_final, categoria_seleccionada, id_final, nombre_entidad=nombre_final, contrato=contrato_final)
                                            ruta_docs = os.path.join(ruta_base, "Documentos_Vigentes")
                                            os.makedirs(ruta_docs, exist_ok=True)
                                            nombre_fn = f"{id_final}_{tipo.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext_q}"
                                            path_fn = os.path.join(ruta_docs, nombre_fn)
                                            with open(path_fn, "wb") as f: f.write(quick_up.getbuffer())

                                            upsert_registro(DB_PATH, {
                                                "id": doc_id, "identificador": id_final, "nombre": nombre_final, "tipo_doc": tipo,
                                                "path": path_fn, "categoria": categoria_seleccionada, "fecha_carga": datetime.now().date(),
                                                "fecha_vencimiento": quick_vto, "estado_obs": "Resuelta", "detalle": detalle_final,
                                                "empresa": empresa_final, "contrato": contrato_final,
                                                "session_empresa_id": filtros.get('empresa_id', 0), "session_contrato_id": filtros.get('contrato_id', 0)
                                            })
                                            registrar_log(DB_PATH, st.session_state.get('user_login', 'Desconocido'), "PERS_UPLOAD_SINGLE", f"Subido: {tipo} para {nombre_final}")
                                            st.success("¡Documento guardado!")
                                            st.rerun()
                                    else: st.warning("Adjunta un archivo.")

                    with col_btn2:
                        # Botón para borrar exigencia
                        if st.button("🗑️", key=f"del_{doc_id}", help="Eliminar este documento del perfil"):
                            ejecutar_query(DB_PATH, "DELETE FROM registros WHERE id=?", (doc_id,), commit=True)
                            st.rerun()
            else:
                st.info("No hay documentos registrados para este perfil.")



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

                            if doc in ["Curso de Trabajo en Altura", "Curso de Primeros Auxilios", "Curso de Manejo de Extintores", "Certificación de Operador", "Licencia Interna", "Exámenes Médicos Pre u Ocupacionales"]:
                                st.caption("⚠️ ¿Este documento fue aprobado con observaciones o condiciones?")
                                es_condicionado = st.checkbox("🚩 Marcar como Vigencia Condicionada", key=f"cond_{safe_doc_key}_{id_final}")
                                if es_condicionado:
                                    fecha_cond_ind = st.date_input("📅 Fecha Límite para Subsanar:", key=f"f_cond_{safe_doc_key}_{id_final}")
                                    observaciones_ind = st.text_area("📝 Motivo (Ej: Cambio de lentes / Subsanar hallazgo):", key=f"obs_c_{safe_doc_key}_{id_final}")
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
                                    ruta_base = obtener_ruta_entidad(empresa_final, categoria_seleccionada, id_final, nombre_entidad=nombre_final, contrato=contrato_final)
                                    ruta_documentos = os.path.join(ruta_base, "Documentos_Vigentes")
                                    os.makedirs(ruta_documentos, exist_ok=True)

                                    extension = os.path.splitext(dato["file_obj"].name)[1]
                                    # Validación de seguridad
                                    es_valido, msg_error = validar_archivo_seguro(dato["file_obj"], [extension])
                                    if not es_valido:
                                        st.error(f"❌ {msg_error}")
                                        continue

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

                                    registrar_log(DB_PATH, st.session_state.get('user_login', 'Desconocido'), "PERS_UPLOAD_BULK", f"Carga de {len(datos_a_guardar)} documentos para {nombre_final}")
                                st.success(f"✅ ¡Éxito! Se guardaron {len(datos_a_guardar)} documento(s).")
                            except Exception as e: st.error(f"❌ Ocurrió un error al guardar: {e}")

        with tab_epp:
            st.markdown("#### Historial y Entrega de EPP")
            sub_tab_1, sub_tab_2 = st.tabs(["✍️ Entregar Nuevo Kit", "📋 Historial Entregas"])

            with sub_tab_1:
                st.markdown("##### 📦 Seleccionar Elementos a Entregar")
                fecha_entrega = st.date_input("📅 Fecha de Entrega", value=datetime.now().date(), key=f"f_entrega_{id_final}")
                epps_seleccionados = st.multiselect("Seleccione los EPPs del Kit:", TIPOS_EPP_GLOBAL, key=f"epp_sel_{id_final}")

                items_a_registrar = []
                if epps_seleccionados:
                    for epp in epps_seleccionados:
                        clean_name = epp.split(" (")[0]
                        with st.expander(f"⚙️ Configurar: {clean_name}", expanded=True):
                            c1, c2, c3, c4, c5 = st.columns([1.5, 1, 1.5, 1.5, 1.5])
                            talla = c1.text_input("Talla", placeholder="Ej: M, 42, N/A", key=f"talla_{epp}_{id_final}")
                            cantidad = c2.number_input("Cant.", min_value=1, value=1, key=f"cant_{epp}_{id_final}")
                            marca = c3.text_input("Marca", placeholder="Ej: 3M, Steelpro", key=f"marca_{epp}_{id_final}")
                            modelo = c4.text_input("Modelo", placeholder="Ej: 7502", key=f"modelo_{epp}_{id_final}")

                            duracion_meses = 3
                            for key, months in EPP_DURATION_MAPPING.items():
                                if key.lower() in clean_name.lower():
                                    duracion_meses = months
                                    break
                            venc_sug = pd.to_datetime(fecha_entrega) + pd.DateOffset(months=duracion_meses)
                            vencimiento = c5.date_input("Vencimiento", value=venc_sug.date(), key=f"venc_{epp}_{id_final}")

                            items_a_registrar.append({
                                "tipo_epp": clean_name, "talla": talla, "cantidad": cantidad,
                                "marca": marca, "modelo": modelo, "vencimiento": vencimiento
                            })

                    st.divider()
                    archivo_acta = st.file_uploader("Subir Acta Firmada (PDF/JPG/PNG)", type=['pdf', 'jpg', 'png', 'jpeg'], key=f"acta_{id_final}")
                    if st.button("💾 GUARDAR ACTA Y REGISTRAR ENTREGA", type="primary", use_container_width=True, key=f"btn_epp_{id_final}"):
                        if not archivo_acta:
                            st.error("Es obligatorio subir el acta firmada.")
                        else:
                            try:
                                path_base = obtener_ruta_entidad(empresa_final, "Personal", id_final, nombre_entidad=nombre_final, contrato=contrato_final)
                                epp_folder = os.path.join(path_base, "EPP")
                                os.makedirs(epp_folder, exist_ok=True)

                                ext = os.path.splitext(archivo_acta.name)[1]
                                filename = f"Acta_EPP_{id_final}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"
                                final_path = os.path.join(epp_folder, filename).replace("\\", "/")

                                with open(final_path, "wb") as f:
                                    f.write(archivo_acta.getbuffer())

                                emp_id = st.session_state.get('filtros', {}).get('empresa_id', 0)
                                con_id = st.session_state.get('filtros', {}).get('contrato_id', 0)

                                query_acta = "INSERT INTO entregas_epp_actas (trabajador_id, fecha_entrega, firma_path, instructor, empresa_id, contrato_id) VALUES (?, ?, ?, ?, ?, ?)"
                                acta_id = ejecutar_query(DB_PATH, query_acta, (id_final, str(fecha_entrega), final_path, st.session_state.username, emp_id, con_id), commit=True)

                                for it in items_a_registrar:
                                    ejecutar_query(DB_PATH, "INSERT INTO entregas_epp_items (acta_id, tipo_epp, talla, cantidad, marca, modelo, fecha_vencimiento) VALUES (?, ?, ?, ?, ?, ?, ?)",
                                                   (acta_id, it['tipo_epp'], it['talla'], it['cantidad'], it['marca'], it['modelo'], str(it['vencimiento'])), commit=True)

                                    desc_epp = f"EPP: {it['tipo_epp']} ({it['marca']} {it['modelo']})"
                                    query_registro = "INSERT INTO registros (identificador, nombre, detalle, tipo_doc, fecha_vencimiento, path, categoria, empresa_id, contrato_id, fecha_carga) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
                                    ejecutar_query(DB_PATH, query_registro, (id_final, nombre_final, it['talla'], desc_epp, str(it['vencimiento']), final_path, "Personal", emp_id, con_id, str(datetime.now().date())), commit=True)

                                registrar_log(DB_PATH, st.session_state.get('user_login', 'Desconocido'), "PERS_EPP_DELIVERY", f"Entrega de {len(items_a_registrar)} EPPs para {nombre_final}")
                                st.success(f"✅ Entrega registrada con éxito. {len(items_a_registrar)} elementos.")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error técnico al guardar: {e}")
            with sub_tab_2:
                query_h = "SELECT a.id, a.fecha_entrega, a.firma_path, a.instructor FROM entregas_epp_actas a WHERE a.trabajador_id = ? ORDER BY a.fecha_entrega DESC"
                df_h = obtener_dataframe(DB_PATH, query_h, (id_final,))
                if not df_h.empty:
                    for idx, row in df_h.iterrows():
                        with st.expander(f"📦 Acta #{row['id']} - {row['fecha_entrega']}"):
                            c_act1, c_act2 = st.columns([3, 1])
                            with c_act1:
                                df_items = obtener_dataframe(DB_PATH, "SELECT tipo_epp, talla, cantidad, marca, modelo, fecha_vencimiento FROM entregas_epp_items WHERE acta_id = ?", (row['id'],))
                                st.table(df_items)
                            with c_act2:
                                st.write(f"Instructor: {row['instructor']}")
                                if row['firma_path'] and os.path.exists(row['firma_path']):
                                    with open(row['firma_path'], "rb") as f:
                                        st.download_button("📄 Bajar Acta Firmada", f, file_name=os.path.basename(row['firma_path']), key=f"dl_epp_{row['id']}_{id_final}", use_container_width=True)
                else:
                    st.info("No hay historial de entregas para este trabajador.")

    # Eliminación centralizada en Mantenimiento
