import os
import sqlite3
import unicodedata
from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st

from src.infrastructure.archivos import obtener_ruta_entidad, validar_archivo_seguro
from config.config import DOCS_OBLIGATORIOS
from src.infrastructure.database import ejecutar_query, obtener_dataframe, upsert_registro
from core.excel_master import cargar_maestro_filtrado
from core.reports import generar_qr
from core.utils import is_valid_context, show_context_warning
from intelligence.agents.intelligence_engine import UllTroneEngine
from config.config import LOGO_APP, obtener_logo_cliente


def normalizar(txt):
    if pd.isna(txt) or txt is None: return ""
    s = str(txt).strip().upper()
    return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')

# ─────────────────────────────────────────────────────────────────────────────
# TRINIDAD DE ACTIVOS — Mapeo de categorías y configuración por tipo
# ─────────────────────────────────────────────────────────────────────────────
_TRINITY_CONFIG = {
    "Vehiculo_Liviano": {
        "titulo": "🚛 Trazabilidad: Camionetas (Vehículos Livianos)",
        "icono_dir": "🚛",
        "doc_options": ["SOAP", "Revisión técnica", "Permiso de circulación",
                        "Mantención preventiva", "Certificado de torque",
                        "Certificado de accesorios", "Otros"],
        "categoria_db": "Vehiculo_Liviano",
    },
    "Camion_Transporte": {
        "titulo": "🚚 Trazabilidad: Camiones (Transporte y Logística)",
        "icono_dir": "🚚",
        "doc_options": ["SOAP", "Revisión técnica", "Permiso de circulación",
                        "Mantención preventiva", "Certificado de torque",
                        "Certificado de accesorios", "Otros"],
        "categoria_db": "Camion_Transporte",
    },
    "Equipo_Pesado": {
        "titulo": "🏗️ Trazabilidad: Equipos Pesados (Komatsu / Excavadoras)",
        "icono_dir": "🏗️",
        "doc_options": ["Mantención preventiva", "Mantención de Pluma",
                        "Sistema AFEX", "Certificado de torque",
                        "Certificado de accesorios", "Certificación de izaje",
                        "Permiso de operación", "Otros"],
        "categoria_db": "Equipo_Pesado",
    },
    # Categoría legacy — mantiene compatibilidad con datos existentes
    "Maquinaria Pesada & Vehículos": {
        "titulo": "🛡️ Trazabilidad: Vehículos y Maquinarias (General)",
        "icono_dir": "🏗️",
        "doc_options": ["SOAP", "Revisión técnica", "Permiso de circulación",
                        "Mantención preventiva", "Mantención de Pluma",
                        "Sistema AFEX", "Certificado de torque",
                        "Certificado de accesorios", "Otros"],
        "categoria_db": "Maquinaria Pesada & Vehículos",
    },
}

def render_trazabilidad_vehiculos(DB_PATH, categoria=None):
    """Renderiza el módulo de trazabilidad de maquinaria filtrado por tipo de activo.

    Args:
        categoria: Clave de tipo de activo. Valores válidos:
            - 'Vehiculo_Liviano'    → Camionetas
            - 'Camion_Transporte'   → Camiones
            - 'Equipo_Pesado'       → Equipos Pesados
            - None                  → Muestra todos (comportamiento legado)
    """
    # Resolver configuración según categoría
    if categoria and categoria in _TRINITY_CONFIG:
        cfg = _TRINITY_CONFIG[categoria]
    else:
        cfg = _TRINITY_CONFIG["Maquinaria Pesada & Vehículos"]

    categoria_seleccionada = cfg["categoria_db"]
    opciones_doc = cfg["doc_options"]

    filtros = st.session_state.get('filtros', {'empresa_id': 0, 'empresa_nom': None, 'contrato_id': 0, 'contrato_nom': None, 'busqueda_global': ''})
    
    # --- UI ELITE NEON ONYX ---
    st.markdown(f"""
        <div class='premium-header'>
            <div style='display: flex; align-items: center; gap: 20px;'>
                <div style='background: rgba(14, 165, 233, 0.1); padding: 15px; border-radius: 12px; border: 1px solid var(--border-glass);'>
                    <span style='font-size: 2.5rem;'>{cfg['icono_dir']}</span>
                </div>
                <div>
                    <h1 style='color: var(--text-heading); margin: 0; font-size: 1.8rem; font-family: "Outfit", sans-serif;'>{cfg['titulo']}</h1>
                    <p style='color: var(--text-muted); margin: 5px 0 0 0; font-size: 1rem; opacity: 0.9;'>Telemetría en tiempo real y trazabilidad técnica de activos críticos.</p>
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

    with st.container(border=True):
        col_v1, col_v2 = st.columns([0.7, 0.3])
        with col_v1:
            st.markdown("### 🗃️ Directorio Rápido (Activos Registrados)")
            st.caption("Filtre y visualice el estado operativo de su flota.")
        
        with col_v2:
            with st.popover("🧠 Strategic Fleet Analysis", use_container_width=True):
                st.markdown("#### Consultoría Ull-Trone (Logística & Mantenimiento)")
                if st.button("Analizar Estado de Flota", type="primary", use_container_width=True):
                    with st.spinner("Procesando telemetría de activos..."):
                        total_v = len(df_f)
                        contexto = f"Activos en {filtros.get('empresa_nom')}: {total_v} unidades. Tipo: {categoria_seleccionada}."
                        prompt = f"Basado en {contexto}, genera una recomendación estratégica (40 palabras) sobre la gestión de mantenimiento preventivo y disponibilidad de flota."
                        reporte = UllTroneEngine.consultar_ia(prompt)
                        st.info(reporte)
        query_sql = "SELECT DISTINCT identificador, nombre, detalle FROM registros WHERE categoria=?"
        params_sql = [categoria_seleccionada]

        is_master = st.session_state.get('role') == "Global Admin"
        if not is_master:
            query_sql += " AND empresa_id = ?"
            params_sql.append(st.session_state.empresa_id)
        elif filtros.get('empresa_id') and filtros['empresa_id'] > 0:
            query_sql += " AND empresa_id = ?"
            params_sql.append(filtros['empresa_id'])

        if filtros.get('contrato_id'):
            query_sql += " AND contrato_id = ?"
            params_sql.append(filtros['contrato_id'])

        df_creados = obtener_dataframe(DB_PATH, query_sql, tuple(params_sql))

        seleccion_rapida = None
        if not df_creados.empty:
            # --- Agrupación por Tipo de Vehículo ---
            tipos = sorted([str(t) for t in df_creados['detalle'].unique() if pd.notnull(t) and str(t).strip() != ""])
            if not tipos: tipos = ["General"]

            for tipo in tipos:
                st.markdown(f"**🏗️ {tipo}**")
                df_tipo = df_creados[df_creados['detalle'] == tipo] if tipo != "General" else df_creados[df_creados['detalle'].isna() | (df_creados['detalle'] == "")]
                if not df_tipo.empty:
                    df_tipo['pildora'] = df_tipo['identificador'] + " - " + df_tipo['nombre']
                    p_sel = st.pills(f"Activos ({tipo})", df_tipo['pildora'].tolist(), key=f"pills_v_{tipo}", label_visibility="collapsed")
                    if p_sel: seleccion_rapida = p_sel
        else:
            st.info("Aún no hay vehículos/maquinarias con expedientes en esta base de datos.")

        st.divider()
        modo = st.radio("🛠️ O buscar / ingresar nuevo registro:", ["🔍 Buscar en Base Maestra (Excel)", "➕ Ingreso Manual"], horizontal=True)

        if seleccion_rapida:
            id_final = seleccion_rapida.split(" - ")[0]
            nombre_final = seleccion_rapida.split(" - ")[1]

            # Recuperar el detalle del equipo desde el DataFrame de búsqueda
            row_sel = df_creados[df_creados['identificador'] == id_final].iloc[0]
            detalle_final = str(row_sel['detalle']).strip() if pd.notnull(row_sel['detalle']) else "No Especificado"

            # Recuperar empresa y contrato desde la base de datos
            row_db = ejecutar_query(DB_PATH, "SELECT empresa_id, contrato_id FROM registros WHERE identificador = ? AND categoria = ? LIMIT 1", (id_final, categoria_seleccionada))
            if row_db:
                emp_db = str(row_db[0][0]).strip() if row_db[0][0] else ""
                con_db = str(row_db[0][1]).strip() if row_db[0][1] else ""
                if emp_db and emp_db not in ["None", "nan"]: empresa_final = emp_db
                if con_db and con_db not in ["None", "nan"]: contrato_final = con_db

            st.success(f"✅ Cargando expediente activo de: **{nombre_final}** (Tipo: {detalle_final})")

        elif modo == "🔍 Buscar en Base Maestra (Excel)":
            if df_f.empty:
                st.warning("⚠️ No se encontraron registros para los filtros aplicados en el Excel.")
            else:
                with st.expander(f"⚡ Sincronización Masiva (Cargar a todos desde el Excel)"):
                    if not is_valid_context(filtros):
                        show_context_warning()
                    else:
                        st.info(f"Esta acción revisará las {len(df_f)} filas del Excel y creará las tarjetas 'Pendientes' (Rojas) para todos los vehículos que aún no estén en el sistema.")

                        docs_masivos_exigidos = st.multiselect("📌 Selecciona qué documentos serán críticos para todos:", opciones_doc, key="multi_masivo")

                    con_destino_masivo = filtros.get('contrato_nom')
                    if not con_destino_masivo or con_destino_masivo in ["Sin Contrato", "Todos los Contratos"]:
                        from core.excel_master import obtener_contratos_por_empresa
                        listado_contratos = obtener_contratos_por_empresa(filtros.get('empresa_nom', ''))
                        con_destino_masivo = st.selectbox("🎯 Asignar estos registros al contrato:", ["--- Seleccione ---"] + listado_contratos, key="con_masivo_sel")

                    if st.button(f"🚀 Crear Tarjetas para TODOS en Vehículos", use_container_width=True):
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
                        st.write("🔍 Buscar un vehículo/maquinaria específica desde la Base Maestra:")
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
                st.info(f"📝 Ingreso manual de datos para: Vehículos")
                c1, c2, c3 = st.columns([1, 1.5, 1])
                with c1: id_final = st.text_input(f"🔢 {col_id}:")
                with c2: nombre_final = st.text_input(f"📋 {col_nom}:")
                with c3: detalle_final = st.text_input("💼 Tipo:")

                c4, c5 = st.columns(2)
                with c4: empresa_final = st.text_input("🏢 Empresa:", value=filtros.get('empresa_nom') if filtros.get('empresa_nom') else "", disabled=True)
                with c5: contrato_final = st.text_input("📄 Contrato:", value=filtros.get('contrato_nom') if filtros.get('contrato_nom') else "", disabled=True)

    if id_final and nombre_final:
        st.divider()
        st.markdown(f"### 🪪 Perfil del Vehículo / Maquinaria", unsafe_allow_html=True)

        with st.container(border=True):
            df_existentes = obtener_dataframe(DB_PATH, "SELECT tipo_doc FROM registros WHERE identificador=?", (id_final,))

            if df_existentes.empty:
                st.info("💡 Este vehículo no tiene documentos obligatorios asignados. Define qué documentos son **Críticos** para habilitarlo.")
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
                with st.expander("➕ Añadir nuevas exigencias (Tarjetas Rojas) a este equipo"):
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

            # Intento de Recuperación Opcional desde DB si hay filtros genéricos
            res_eid = ejecutar_query(DB_PATH, "SELECT empresa_id, contrato_id FROM registros WHERE identificador = ? LIMIT 1", (id_final,))
            if res_eid:
                db_emp_id = res_eid[0][0] if isinstance(res_eid[0], (list, tuple)) else res_eid[0]
                db_con_id = res_eid[0][1] if isinstance(res_eid[0], (list, tuple)) else (res_eid[1] if len(res_eid)>1 else 0)

                # Rescatar Empresa si no existe
                if not empresa_final or empresa_final in ["--- TODAS LAS EMPRESAS ---", "None", ""]:
                    res_enom = ejecutar_query(DB_PATH, "SELECT nombre FROM empresas WHERE id = ?", (db_emp_id,))
                    if res_enom: empresa_final = res_enom[0][0] if isinstance(res_enom[0], (list, tuple)) else res_enom[0]

                # Rescatar Contrato si no existe o es "Todos los Contratos"
                if not contrato_final or str(contrato_final).strip() in ["None", "", "nan", "Todos los Contratos", "TODOS LOS CONTRATOS", "Sin Contrato", "SIN_CONTRATO"]:
                    if db_con_id and db_con_id > 0:
                        res_cnom = ejecutar_query(DB_PATH, "SELECT nombre_contrato FROM contratos WHERE id = ?", (db_con_id,))
                        if res_cnom: contrato_final = res_cnom[0][0] if isinstance(res_cnom[0], (list, tuple)) else res_cnom[0]

            # Validación Final para evitar EMPRESA_NO_DEFINIDA
            if not empresa_final or empresa_final in ["None", "", "--- TODAS LAS EMPRESAS ---"]:
                st.warning("⚠️ No se puede determinar la Empresa para este activo. Por favor, selecciona una Empresa en el Filtro Lateral.")
                return

            # Validación estricta de Contrato
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

            st.markdown(f"""
                <div class='glass-card' style='margin-bottom: 25px;'>
                    <div style='display: flex; align-items: flex-start; gap: 20px;'>
                        <div style='width: 140px; height: 140px; border-radius: 15px; border: 2px solid var(--accent-neon); overflow: hidden; background: var(--bg-main); flex-shrink: 0;'>
                            <div style='display:flex; justify-content:center; align-items:center; height:100%; color:var(--accent-neon); font-size:2em;'>{cfg['icono_dir']}</div>
                        </div>
                        <div style='flex-grow: 1;'>
                            <h2 style='color: var(--text-heading); margin: 0;'>{nombre_final}</h2>
                            <p style='color: var(--accent-neon); margin: 5px 0;'>PATENTE / ID: {id_final}</p>
                            <div style='display: flex; gap: 10px; margin-top: 10px;'>
                                <span style='background: rgba(14, 165, 233, 0.1); color: var(--accent-neon); padding: 4px 12px; border-radius: 20px; font-size: 0.85em;'>⚙️ {detalle_final or 'Tipo pendiente'}</span>
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
                st.caption("Cargar nueva imagen del activo:")
                foto_up = st.file_uploader("Subir", type=['jpg', 'png', 'jpeg'], key=f"up_foto_{id_final}", label_visibility="collapsed")
                if foto_up is not None:
                    if st.button("💾 Actualizar Foto", type="primary", key=f"btn_foto_{id_final}", use_container_width=True):
                        extension = os.path.splitext(foto_up.name)[1]
                        path_foto = os.path.join(ruta_fotos, f"perfil_{id_final}{extension}")
                        with open(path_foto, "wb") as f:
                            f.write(foto_up.getbuffer())
                        st.success("¡Imagen sincronizada!")
                        st.rerun()

            with col_info:
                st.markdown(f"**Vigencia Documental:** 100% (Vigente)")
                st.markdown(f"**Bitácora Digital:** `{id_final}_{nombre_final.replace(' ', '_')}`")

            with col_actions:
                st.markdown("<b>Acciones Técnicas</b>", unsafe_allow_html=True)
                with st.popover("🔲 Identidad QR Activo", use_container_width=True):
                    if st.button("Generar Código QR", key=f"btn_qr_{id_final}", use_container_width=True):
                        texto_qr = f"CGT | ACTIVO | {empresa_final} | ID: {id_final}"
                        st.image(generar_qr(texto_qr), width=150)


        st.markdown(f"### ⚙️ Centro de Operaciones del Equipo", unsafe_allow_html=True)
        # Ajuste dinámico de pestañas según tipo de equipo
        # Se agregan "CARGADOR" y "MANIPULADOR" a la lógica de Tabla de Carga
        es_pluma = any(x in str(detalle_final).upper() for x in ["PLUMA", "MANIPULADOR", "CARGADOR"])

        titulos_tabs = [
            "📊 Gestor Documental",
            "➕ Cargar Docs.",
            "⏱️ Uso (Hrs/Km)",
            "⚠️ Falla",
            "🔧 Torque",
            "📈 Disponibilidad"
        ]
        if es_pluma:
            titulos_tabs.append("📋 Tabla de Carga de Pluma")

        tabs = st.tabs(titulos_tabs)
        tab_estado = tabs[0]
        tab_carga = tabs[1]
        tab_uso = tabs[2]
        tab_falla = tabs[3]
        tab_torque = tabs[4]
        tab_disp = tabs[5]
        tab_ficha = tabs[6] if es_pluma else None

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
                                                    ruta_base = obtener_ruta_entidad(empresa_final, categoria_seleccionada, id_final, contrato=contrato_final)
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
                                                    st.success("¡Documento guardado!")
                                                    st.rerun()
                                            else: st.warning("Adjunta un archivo.")

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

                            fecha_vto_ind = datetime.strptime("2000-01-01", "%Y-%m-%d").date()
                            tipo_control_ind = "Fecha"
                            meta_hor_ind = 0
                            uso_actual_ind = 0

                            es_mantencion = doc.lower().startswith("mantención") or doc.lower().startswith("mantenimiento")

                            with c2:
                                if es_mantencion:
                                    modo_ctrl = st.radio(f"Control de Vigencia ({doc}):", ["Por Fecha", "Por Uso (Km/Hrs)"], key=f"rad_{safe_doc_key}_{id_final}", horizontal=True)
                                    if modo_ctrl == "Por Fecha":
                                        fecha_vto_ind = st.date_input("📅 Fecha de Vencimiento:", key=f"vto_{safe_doc_key}_{id_final}")
                                    else:
                                        opc_uso = st.selectbox("Unidad de Medida:", ["Kilómetros", "Horas (Horómetro)"], key=f"unidad_{safe_doc_key}_{id_final}")
                                        tipo_control_ind = "Kilometros" if "Kilómetros" in opc_uso else "Horas"

                                        col_u1, col_u2 = st.columns(2)
                                        with col_u1:
                                            # Recuperar valor actual para referencia
                                            res_val = ejecutar_query(DB_PATH, "SELECT horas_actuales FROM horometros_actuales WHERE identificador=?", (id_final,))
                                            val_v = res_val[0][0] if res_val else 0
                                            uso_actual_ind = st.number_input(f"Uso Actual en {doc} ({tipo_control_ind}):", min_value=int(val_v), value=int(val_v), step=1, key=f"uso_act_{safe_doc_key}_{id_final}")
                                        with col_u2:
                                            meta_hor_ind = st.number_input(f"Próxima Mantención (Meta en {tipo_control_ind}):", min_value=int(uso_actual_ind), value=int(uso_actual_ind) + 5000 if "Kilometros" in tipo_control_ind else int(uso_actual_ind) + 250, step=1, key=f"meta_{safe_doc_key}_{id_final}")
                                else:
                                    fecha_vto_ind = st.date_input("📅 Fecha de Vencimiento:", key=f"vto_{safe_doc_key}_{id_final}")

                            observaciones_ind, fecha_cond_ind = "", None
                            estado_obs_ind, tiene_obs_ind = "Resuelta", "No"

                            if doc in ["Mantención de Pluma", "Sistema AFEX"]:
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
                                "estado_obs": estado_obs_ind, "tiene_obs": tiene_obs_ind,
                                "meta_horometro": meta_hor_ind, "tipo_control": tipo_control_ind,
                                "uso_actual": uso_actual_ind
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
                                        "meta_horometro": dato.get("meta_horometro", 0),
                                        "tipo_control": dato.get("tipo_control", "Fecha"),
                                        "session_empresa_id": filtros.get('empresa_id', 0),
                                        "session_contrato_id": filtros.get('contrato_id', 0)
                                    })

                                    # Actualización automática de Horómetro/Kilometraje si se ingresó un valor
                                    if dato.get("uso_actual", 0) > 0:
                                        fecha_hoy = datetime.now().strftime("%Y-%m-%d")
                                        res_h = ejecutar_query(DB_PATH, "SELECT id FROM horometros_actuales WHERE identificador=?", (id_final,))
                                        if res_h:
                                            ejecutar_query(DB_PATH, "UPDATE horometros_actuales SET horas_actuales=?, ultima_actualizacion=? WHERE identificador=?", (dato["uso_actual"], fecha_hoy, id_final), commit=True)
                                        else:
                                            ejecutar_query(DB_PATH, "INSERT INTO horometros_actuales (identificador, horas_actuales, ultima_actualizacion) VALUES (?, ?, ?)", (id_final, dato["uso_actual"], fecha_hoy), commit=True)

                                st.success(f"✅ ¡Éxito! Se guardaron {len(datos_a_guardar)} documento(s).")
                            except Exception as e: st.error(f"❌ Ocurrió un error al guardar: {e}")

        # PESTAÑA 3: USO
        with tab_uso:
            res_h_all = ejecutar_query(DB_PATH, "SELECT horas_actuales, ultima_actualizacion FROM horometros_actuales WHERE identificador=?", (id_final,))
            res_h = res_h_all[0] if res_h_all else None
            valor_actual = res_h[0] if res_h else 0
            ultima_fecha = res_h[1] if res_h else "Sin registros previos"

            st.metric("Valor Actual (Hrs/Km)", f"{valor_actual}", f"Última act: {ultima_fecha}")
            with st.form(f"form_actualizacion_uso_{id_final}", clear_on_submit=True):
                nuevo_valor = st.number_input("Ingresar Nuevo Valor Acumulado (Hrs/Km)", min_value=int(valor_actual), value=int(valor_actual), step=1)
                if st.form_submit_button("💾 Guardar Actualización", use_container_width=True):
                    fecha_hoy = datetime.now().strftime("%Y-%m-%d")
                    emp_id_ctx = filtros.get('empresa_id', 0)
                    con_id_ctx = filtros.get('contrato_id', 0)
                    
                    if res_h:
                        ejecutar_query(DB_PATH, "UPDATE horometros_actuales SET horas_actuales=?, ultima_actualizacion=? WHERE identificador=?", (nuevo_valor, fecha_hoy, id_final), commit=True)
                    else:
                        ejecutar_query(DB_PATH, "INSERT INTO horometros_actuales (identificador, horas_actuales, ultima_actualizacion) VALUES (?, ?, ?)", (id_final, nuevo_valor, fecha_hoy), commit=True)
                    
                    # 📈 Guardar en historial para la curva
                    ejecutar_query(DB_PATH, "INSERT INTO ultron_horometros_history (identificador, fecha, valor, empresa_id, contrato_id) VALUES (?, ?, ?, ?, ?)", 
                                   (id_final, fecha_hoy, nuevo_valor, emp_id_ctx, con_id_ctx), commit=True)
                    
                    st.success(f"✅ ¡Actualización guardada con éxito para el equipo {id_final}!")
                    st.rerun()

            st.divider()
            st.markdown("#### 📈 Curva de Utilización Histórica")
            df_hist_uso = obtener_dataframe(DB_PATH, "SELECT fecha, valor FROM ultron_horometros_history WHERE identificador=? ORDER BY fecha ASC", (id_final,))
            if not df_hist_uso.empty:
                fig_uso = px.line(df_hist_uso, x="fecha", y="valor", title=f"Evolución de Uso: {id_final}", 
                                  labels={"fecha": "Fecha", "valor": "Acumulado (Hrs/Km)"},
                                  markers=True, line_shape="hv")
                fig_uso.update_traces(line_color="#00A8E8")
                st.plotly_chart(fig_uso, use_container_width=True)
            else:
                st.info("No hay datos históricos suficientes para generar la curva de utilización.")

        # PESTAÑA 4: FALLAS
        with tab_falla:
            st.markdown(f"**Reportar problema para el equipo:** {nombre_final}")
            with st.form(f"form_reporte_falla_{id_final}", clear_on_submit=True):
                tipo_falla = st.selectbox("Clasificación Crítica de la Falla:", [
                    "Pinchazo / Daño en Neumático",
                    "Mecánica / Hidráulica (Frenos, Dirección, Fugas)",
                    "Sistemas de Seguridad (Extintores, Alarmas)",
                    "Eléctrica / Electrónica",
                    "Falla Estructural",
                    "Otra"
                ])
                descripcion_falla = st.text_area("Descripción detallada (Ej: Neumático del eje 2 pinchado):")
                bloquear_equipo = st.checkbox("Bloquear equipo (Generará alerta roja en Dashboard)", value=True)

                if st.form_submit_button("🚨 Reportar y Registrar Falla", use_container_width=True) and descripcion_falla:
                    fecha_hora_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    usuario_actual = st.session_state.get('username', 'Usuario Desconocido')

                    ejecutar_query(DB_PATH, """
                        INSERT INTO historial_fallas (identificador, fecha, descripcion, reportado_por, estado, tipo_falla) 
                        VALUES (?, ?, ?, ?, 'Pendiente', ?)
                    """, (id_final, fecha_hora_actual, descripcion_falla, usuario_actual, tipo_falla), commit=True)

                    if bloquear_equipo:
                        obs_formateada = f"[{tipo_falla}] {descripcion_falla}"
                        ejecutar_query(DB_PATH, """
                            INSERT INTO registros (identificador, nombre, empresa, categoria, detalle, tipo_doc, fecha_condicion, estado_obs, observaciones, tiene_observacion, empresa_id, contrato_id)
                            VALUES (?, ?, ?, ?, ?, '🚨 REPORTE DE FALLA', '2000-01-01', 'Pendiente', ?, 'Sí', (SELECT id FROM empresas WHERE nombre=?), (SELECT id FROM contratos WHERE empresa_id=(SELECT id FROM empresas WHERE nombre=?) AND nombre_contrato=?))
                        """, (id_final, nombre_final, empresa_final, categoria_seleccionada, detalle_final, obs_formateada, empresa_final, empresa_final, contrato_final), commit=True)

                    st.error(f"⚠️ Falla reportada. Equipo {id_final} bloqueado.")
                    st.rerun()

        # PESTAÑA 5: TORQUES INDEPENDIENTES
        with tab_torque:
            st.markdown(f"**Subir respaldo de torque para:** {nombre_final}")
            with st.form(f"form_torque_{id_final}", clear_on_submit=True):
                pos_sel = st.selectbox("🎯 Especificar Posición:", [
                    "Posición 1 (Delantera Izquierda)", "Posición 2 (Delantera Derecha)",
                    "Posición 3 (Trasera Izquierda)", "Posición 4 (Trasera Derecha)",
                    "Eje 2 - Izquierda", "Eje 2 - Derecha", "Eje 3 - Izquierda", "Eje 3 - Derecha", "Otra..."
                ])
                archivo_torque = st.file_uploader("Adjuntar Certificado", type=['pdf', 'jpg', 'jpeg', 'png'])
                fecha_torque = st.date_input("Fecha")

                if st.form_submit_button("📎 Guardar Certificado", use_container_width=True) and archivo_torque:
                    from src.infrastructure.archivos import obtener_ruta_torques
                    ruta_carpeta_torques = obtener_ruta_torques(empresa_final, id_final, contrato=contrato_final)
                    ext = archivo_torque.name.split('.')[-1]
                    # Validación de seguridad
                    es_valido, msg_error = validar_archivo_seguro(archivo_torque, [f".{ext}"])
                    if not es_valido:
                        st.error(f"❌ {msg_error}")
                        st.stop()
                    ruta_guardado = os.path.join(ruta_carpeta_torques, f"torque_{id_final}_{fecha_torque.strftime('%Y%m%d')}.{ext}")
                    with open(ruta_guardado, "wb") as f: f.write(archivo_torque.getbuffer())

                    ejecutar_query(DB_PATH, "INSERT INTO registro_torques (identificador, fecha_torque, ruta_archivo, posicion) VALUES (?, ?, ?, ?)", (id_final, str(fecha_torque), ruta_guardado, pos_sel), commit=True)
                    st.success(f"✅ Certificado guardado en {pos_sel}.")
                    st.rerun()

        # PESTAÑA: DISPONIBILIDAD
        with tab_disp:
            st.markdown(f"### 📈 Reporte de Disponibilidad: {id_final}")
            st.write("Cálculo basado en 720 horas mensuales (30 días x 24 hrs) menos el tiempo fuera de servicio reportado.")

            # Obtener fallas/eventos del mes actual para este equipo
            mes_actual = datetime.now().strftime("%Y-%m")
            query_disp = """
                SELECT fecha, tipo_falla, duracion_min, descripcion 
                FROM eventos_confiabilidad 
                WHERE identificador = ? AND strftime('%Y-%m', fecha) = ?
            """
            df_fallas_mes = obtener_dataframe(DB_PATH, query_disp, (id_final, mes_actual))

            minutos_totales = 30 * 24 * 60 # 43200 min
            minutos_fuera = int(df_fallas_mes['duracion_min'].sum()) if not df_fallas_mes.empty else 0
            horas_fuera = round(minutos_fuera / 60, 1)
            disponibilidad = max(0.0, ((minutos_totales - minutos_fuera) / minutos_totales) * 100)

            col_d1, col_d2, col_d3 = st.columns(3)
            with col_d1:
                st.metric("Disponibilidad Mes", f"{disponibilidad:.1f}%", help="Base: 720 hrs mensuales")
            with col_d2:
                st.metric("Fuera de Servicio", f"{horas_fuera} hrs", delta=f"{len(df_fallas_mes)} eventos", delta_color="inverse")
            with col_d3:
                color_disp = "🟢" if disponibilidad >= 90 else "🟡" if disponibilidad >= 75 else "🔴"
                st.markdown(f"**Estado Operativo:** {color_disp}")
                if disponibilidad < 85:
                    st.warning("⚠️ Disponibilidad bajo el objetivo (85%)")

            if not df_fallas_mes.empty:
                st.markdown("#### Detalle de Interrupciones (Mes Actual)")
                st.dataframe(df_fallas_mes, use_container_width=True, hide_index=True)
            else:
                st.success("✅ No se registran fallas en el mes actual. Disponibilidad al 100%.")

        # PESTAÑA: TABLA DE CARGA (Solo para Camiones Pluma / Manipuladores)
        if es_pluma and tab_ficha:
            with tab_ficha:
                st.markdown("### 📝 Capacidades y Tabla de Izaje/Carga")
                st.info("Configura los límites del equipo y registra su tabla de carga según el manual del fabricante. Puedes pegar directo desde Excel.")
                with st.form(f"form_specs_equipo_{id_final}"):
                    c_f1, c_f2, c_f3 = st.columns(3)
                    with c_f1: marca_mod = st.text_input("Modelo Específico", value=nombre_final)
                    with c_f2: p_gancho = st.number_input("Peso Aparejos/Gancho (Kg)", min_value=0.0, value=65.0)
                    with c_f3: cap_ton = st.number_input("Capacidad Máx. Estructural (Ton)", min_value=0.1, value=10.0)

                    # Fetch existing loads if any
                    df_existentes_tabla = obtener_dataframe(DB_PATH, "SELECT radio_m as 'Radio_Trabajo_Metros', largo_pluma_m as 'Largo_Pluma_Metros', capacidad_kg as 'Capacidad_Bruta_Kg' FROM tablas_carga_equipos WHERE identificador=?", (id_final,))

                    if df_existentes_tabla.empty:
                        df_existentes_tabla = pd.DataFrame(columns=["Radio_Trabajo_Metros", "Largo_Pluma_Metros", "Capacidad_Bruta_Kg"])

                    tabla_cargas_editada = st.data_editor(
                        df_existentes_tabla,
                        num_rows="dynamic",
                        use_container_width=True,
                        hide_index=True
                    )

                    st.write("")
                    if st.form_submit_button("💾 Guardar Ficha y Tabla de Carga", use_container_width=True):
                        ejecutar_query(DB_PATH, "CREATE TABLE IF NOT EXISTS tablas_carga_equipos (id INTEGER PRIMARY KEY AUTOINCREMENT, identificador TEXT NOT NULL, radio_m REAL NOT NULL, largo_pluma_m REAL NOT NULL, capacidad_kg REAL NOT NULL)", commit=True)
                        ejecutar_query(DB_PATH, "INSERT OR REPLACE INTO especificaciones_equipos (identificador, marca_modelo, capacidad_max_ton, peso_gancho_kg) VALUES (?, ?, ?, ?)", (id_final, marca_mod, cap_ton, p_gancho), commit=True)
                        ejecutar_query(DB_PATH, "DELETE FROM tablas_carga_equipos WHERE identificador = ?", (id_final,), commit=True)

                        for index, row in tabla_cargas_editada.iterrows():
                            if pd.notnull(row['Radio_Trabajo_Metros']) and pd.notnull(row['Capacidad_Bruta_Kg']):
                                params_t = (id_final, float(row['Radio_Trabajo_Metros']), float(row['Largo_Pluma_Metros'] if pd.notnull(row['Largo_Pluma_Metros']) else 0), float(row['Capacidad_Bruta_Kg']))
                                ejecutar_query(DB_PATH, "INSERT INTO tablas_carga_equipos (identificador, radio_m, largo_pluma_m, capacidad_kg) VALUES (?, ?, ?, ?)", params_t, commit=True)

                        st.success(f"✅ Tabla de carga vinculada exitosamente a {id_final}")
                        st.rerun()

    # Eliminación centralizada en Mantenimiento
