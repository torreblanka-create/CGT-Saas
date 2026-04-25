import os
from datetime import datetime

import pandas as pd
import streamlit as st

from src.infrastructure.archivos import obtener_ruta_entidad, validar_archivo_seguro
from config.config import LOGO_APP, LOGO_CLIENTE, get_scoped_path
from src.infrastructure.database import ejecutar_query, obtener_dataframe, registrar_log
from core.logic import calcular_estado_registro
from core.utils import render_hybrid_date_input

# ── Configuración de categorías del sistema ───────────────────────────────────
CATEGORIAS_CONFIG = {
    "Personal":               {"icono": "👷", "alias": ["Personal", "Trabajador", "persona"]},
    "Vehículo Liviano":       {"icono": "🚛", "alias": ["Vehiculo_Liviano", "Camioneta", "Liviano"]},
    "Camión de Transporte":   {"icono": "🚚", "alias": ["Camion_Transporte", "Camion", "Transporte"]},
    "Equipo Pesado":          {"icono": "🏗️", "alias": ["Equipo_Pesado", "Maquinaria Pesada", "Equipo"]},
    "Elementos de Izaje":     {"icono": "⛓️", "alias": ["Elementos de Izaje", "Izaje"]},
    "Instrumentos":           {"icono": "🧰", "alias": ["Instrumentos", "Herramienta", "Metrología"]},
    "Emergencia":             {"icono": "🚨", "alias": ["Emergencia", "Sistemas de Emergencia"]},
    "Maquinaria & Vehículos": {"icono": "🚛", "alias": ["Maquinaria Pesada & Vehículos", "Vehiculo", "Maquinaria"]}, # Legacy
}

def _mapear_categoria(cat_raw: str) -> str:
    """Normaliza el nombre de categoría al grupo canónico."""
    if not cat_raw or pd.isna(cat_raw):
        return "Personal"
    cat_raw = str(cat_raw).strip()
    for canon, cfg in CATEGORIAS_CONFIG.items():
        if cat_raw == canon or cat_raw in cfg["alias"]:
            return canon
    return cat_raw

@st.dialog("📋 Perfil de Expediente", width="large")
def _modal_perfil_expediente(row, df_reg, DB_PATH):
    """Muestra el perfil detallado y los documentos del expediente en un modal flotante."""
    id_val   = row['ID_Patente']
    nombre   = row['Nombre']
    cat      = row.get('CategoriaRaw', row['Categoria'])
    empresa  = row['Empresa']
    contrato = row['Contrato']

    ruta_entidad = obtener_ruta_entidad(empresa, cat, id_val, nombre_entidad=nombre, contrato=contrato, crear_directorios=False)
    ruta_fotos   = os.path.join(ruta_entidad, "Fotos")
    foto_perfil  = None

    if os.path.exists(ruta_fotos):
        # 1. Intentar buscar específicamente el archivo de perfil exacto
        id_clean_match = str(id_val).strip().replace("-", "").replace(".", "").upper()
        for ext in ['.jpg', '.png', '.jpeg', '.JPG', '.PNG', '.JPEG', '.webp']:
            # Probar con y sin guiones
            for pattern in [f"perfil_{id_val}{ext}", f"perfil_{id_clean_match}{ext}"]:
                pth = os.path.join(ruta_fotos, pattern)
                if os.path.exists(pth):
                    foto_perfil = pth
                    break
            if foto_perfil: break

        # 2. Buscar cualquier archivo que contenga el identificador limpio en el nombre
        if not foto_perfil:
            valid_exts = ('.jpg', '.png', '.jpeg', '.webp')
            archivos = [f for f in os.listdir(ruta_fotos) if id_clean_match in f.replace("-", "").replace(".", "").upper() and f.lower().endswith(valid_exts)]
            if archivos:
                foto_perfil = os.path.join(ruta_fotos, archivos[0])

        # 3. Fallback: Primera imagen
        if not foto_perfil:
            valid_exts = ('.jpg', '.png', '.jpeg', '.webp')
            archivos = [f for f in os.listdir(ruta_fotos) if f.lower().endswith(valid_exts)]
            if archivos:
                foto_perfil = os.path.join(ruta_fotos, archivos[0])

    c_f, c_i = st.columns([1, 2.5])
    with c_f:
        if foto_perfil:
            import base64
            ext = os.path.splitext(foto_perfil)[1].lower().replace(".", "")
            mime = f"image/{ext if ext != 'jpg' else 'jpeg'}"
            with open(foto_perfil, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode()

            st.markdown(f"""
                <div style='text-align:center;'>
                    <img src='data:{mime};base64,{encoded_string}' 
                         style='width:100%; max-width:200px; border-radius:12px; border:2px solid #E2E8F0; object-fit:cover; aspect-ratio:3/4;'/>
                </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(
                f"<div style='background-color:#F1F5F9;color:#94a3b8;height:200px;max-width:200px;margin:auto;"
                "border-radius:12px;display:flex;flex-direction:column;align-items:center;"
                "justify-content:center;font-size:1em;'>👤<br><span style='font-size:0.6em;'>Sin Foto</span></div>",
                unsafe_allow_html=True
            )

    with c_i:
        st.markdown(f"### {nombre}")
        st.markdown(f"**Cargo / Detalle:** <span style='color:var(--cgt-gold);font-weight:700;'>{row['Detalle']}</span>", unsafe_allow_html=True)
        st.markdown(f"**ID/RUT/Patente:** {id_val}")
        st.markdown(f"**Empresa:** {empresa} | **Contrato:** {contrato}")

    st.divider()
    st.markdown("#### 📄 Documentos Asociados")

    docs_activo = df_reg[(df_reg['identificador'] == id_val) & (df_reg['nombre'] == nombre)]

    if docs_activo.empty:
        st.info("Sin registros documentales.")
        return

    for _, doc in docs_activo.iterrows():
        color_clase  = "doc-rojo" if doc['estado_doc'] == "ROJO" else "doc-amarillo" if doc['estado_doc'] == "AMARILLO" else "doc-verde"
        f_venc = doc['fecha_vencimiento']
        if pd.notnull(f_venc) and f_venc != '':
            if hasattr(f_venc, 'strftime'):
                venc_formato = f_venc.strftime('%d/%m/%y')
            else:
                try:
                    venc_formato = datetime.strptime(str(f_venc)[:10], '%Y-%m-%d').strftime('%d/%m/%y')
                except:
                    venc_formato = str(f_venc)
        else:
            venc_formato = 'N/A'

        # Layout de documento con botón de descarga
        col_doc_info, col_doc_btn = st.columns([4, 1.2])

        with col_doc_info:
            st.markdown(f"""
                <div class="doc-item {color_clase}" style="margin-bottom:0px;">
                    <div style="flex:1;">
                        <div style="font-weight:600;font-size:0.95em;">{doc['tipo_doc']}</div>
                        <div style="font-size:0.8em;opacity:0.8;">Vence: {venc_formato}</div>
                    </div>
                    <div style="font-weight:700;font-size:0.85em;">● {doc['info_doc']}</div>
                </div>
            """, unsafe_allow_html=True)

        with col_doc_btn:
            ruta_doc = doc.get('path')
            if ruta_doc and os.path.exists(ruta_doc) and "Sin archivo" not in str(ruta_doc):
                with open(ruta_doc, "rb") as f_doc:
                    st.download_button(
                        label="📄 Abrir",
                        data=f_doc,
                        file_name=os.path.basename(ruta_doc),
                        key=f"dl_{doc['id']}_{id_val}",
                        use_container_width=True,
                        help=f"Descargar/Abrir {doc['tipo_doc']}"
                    )
            else:
                st.button("🚫 N/A", disabled=True, use_container_width=True, key=f"none_{doc['id']}_{id_val}", help="El archivo físico no está disponible en el servidor.")
            
            # --- NUEVA FUNCIONALIDAD: SUBIR DOCUMENTO PARA CERRAR BRECHA ---
            with st.popover("📤 Subir", use_container_width=True):
                st.markdown(f"**Cargar {doc['tipo_doc']}**")
                with st.form(key=f"form_up_{doc['id']}_{id_val}", clear_on_submit=True):
                    new_file = st.file_uploader("Seleccionar archivo", type=['pdf', 'jpg', 'png', 'jpeg'], key=f"file_up_{doc['id']}")
                    new_venc = st.date_input("Fecha de Vencimiento", value=datetime.now().date(), key=f"venc_up_{doc['id']}")
                    
                    if st.form_submit_button("Confirmar Carga", use_container_width=True):
                        if new_file:
                            # 1. Guardar archivo
                            ext = new_file.name.split('.')[-1]
                            filename = f"{doc['tipo_doc'].replace(' ', '_')}_{id_val.replace('-', '')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{ext}"
                            ruta_dest = os.path.join(ruta_entidad, "Documentos_Vigentes", filename)
                            
                            with open(ruta_dest, "wb") as f:
                                f.write(new_file.getbuffer())
                            
                            # 2. Actualizar DB
                            q_upd = """
                                UPDATE registros 
                                SET path = ?, fecha_vencimiento = ?, estado_obs = 'Resuelta'
                                WHERE id = ?
                            """
                            ejecutar_query(DB_PATH, q_upd, (ruta_dest, str(new_venc), doc['id']), commit=True)
                            
                            registrar_log(DB_PATH, st.session_state.user_login, "UPLOAD_EXPEDIENTE", f"Subido {doc['tipo_doc']} para {id_val}")
                            st.success("✅ Documento cargado exitosamente.")
                            st.rerun()
                        else:
                            st.error("Seleccione un archivo.")

        st.markdown("<div style='margin-bottom:8px;'></div>", unsafe_allow_html=True)

        # Lógica de resolución de fallas
        if doc.get('estado_obs') == 'Pendiente' and st.session_state.role in ['Admin', 'Cargador']:
            es_pinchazo = "Pinchazo" in str(doc.get('observaciones', ''))
            with st.popover(f"✅ Resolver {doc['tipo_doc']}", use_container_width=True):
                with st.form(key=f"form_res_{doc['identificador']}_{doc['tipo_doc']}", clear_on_submit=True):
                    st.markdown("📝 **Registro de Resolución**")
                    detalle_res = st.text_area("Detalle (Ej: OT #1234, se cambió pieza...)")

                    st.markdown("📅 **Fecha de Validez / Próxima Revisión**")
                    f_final_val = render_hybrid_date_input("Nueva Vcto/Validez", key=f"res_{doc['id']}")

                    arch_evid   = st.file_uploader("Subir Evidencia (OT / Informe)", type=['pdf', 'jpg', 'png'])
                    if es_pinchazo:
                        st.divider()
                        st.markdown("🛞 **Protocolo de Neumáticos (Obligatorio)**")
                        st.warning("Esta falla requiere un Certificado de Torque para habilitar el equipo.")
                        posiciones = [
                            "Posición 1 (Delantera Izquierda)", "Posición 2 (Delantera Derecha)",
                            "Posición 3 (Trasera Izquierda)", "Posición 4 (Trasera Derecha)",
                            "Eje 2 - Izquierda", "Eje 2 - Derecha", "Eje 3 - Izquierda", "Eje 3 - Derecha", "Otra"
                        ]
                        pos_sel     = st.selectbox("Posición del Neumático reemplazado:", posiciones)
                        arch_torque = st.file_uploader("Adjuntar Certificado de Torque", type=['pdf', 'jpg', 'png'])
                        fecha_torque = st.date_input("Fecha del Torque")
                    else:
                        arch_torque = None

                    if st.form_submit_button("Guardar y Desbloquear", use_container_width=True):
                        try:
                            if not detalle_res.strip():
                                st.error("🛑 Debes ingresar el detalle de la resolución.")
                            elif es_pinchazo and not arch_torque:
                                st.error("🛑 Sernageomin: No se puede habilitar sin Certificado de Torque.")
                            elif arch_evid and not validar_archivo_seguro(arch_evid)[0]:
                                st.error("🛑 Archivo de evidencia no válido o corrupto.")
                            else:
                                ruta_evidencia = "Sin archivo"
                                if arch_evid:
                                    ext = arch_evid.name.split('.')[-1]
                                    # Limpiar identificador para la ruta de archivo
                                    id_clean = str(doc['identificador']).replace("/", "-").replace("\\", "-")
                                    # Generar ruta dinámica por empresa/contrato
                                    ruta_evidencias_base = get_scoped_path(empresa, contrato, "Evidencias_Resolucion")
                                    ruta_evidencia = os.path.join(
                                        ruta_evidencias_base,
                                        f"OT_{id_clean}_{datetime.now().strftime('%Y%m%d%H%M%S')}.{ext}"
                                    )
                                    with open(ruta_evidencia, "wb") as f: f.write(arch_evid.getbuffer())

                                if es_pinchazo and arch_torque:
                                    ext_t  = arch_torque.name.split('.')[-1]
                                    id_clean_t = str(doc['identificador']).replace("/", "-").replace("\\", "-")
                                    # Generar ruta dinámica por empresa/contrato
                                    ruta_torque_base = get_scoped_path(empresa, contrato, "Certificados_Torque")
                                    ruta_t = os.path.join(
                                        ruta_torque_base,
                                        f"torque_{id_clean_t}_{fecha_torque.strftime('%Y%m%d')}.{ext_t}"
                                    )
                                    with open(ruta_t, "wb") as f: f.write(arch_torque.getbuffer())
                                    ejecutar_query(DB_PATH, "INSERT INTO registro_torques (identificador, fecha_torque, ruta_archivo, posicion) VALUES (?, ?, ?, ?)", (doc['identificador'], fecha_torque.strftime("%Y-%m-%d"), ruta_t, pos_sel), commit=True)

                                # 1. Actualizar el registro original con la nueva fecha y estado (Multi-empresa)
                                id_emp_act = st.session_state.filtros.get('empresa_id', 0)
                                q_upd = "UPDATE registros SET estado_obs='Resuelta', fecha_vencimiento=? WHERE identificador=? AND tipo_doc=?"
                                par_upd = [str(f_final_val), doc['identificador'], doc['tipo_doc']]
                                if id_emp_act > 0:
                                    q_upd += " AND empresa_id = ?"
                                    par_upd.append(id_emp_act)

                                ejecutar_query(DB_PATH, q_upd, tuple(par_upd), commit=True)

                                # 2. Registrar en historial
                                f_res = datetime.now().strftime("%Y-%m-%d %H:%M")
                                q_hist = "UPDATE historial_fallas SET estado='Resuelto', fecha_resolucion=?, detalle_resolucion=?, evidencia_path=? WHERE identificador=? AND estado='Pendiente' AND id = (SELECT MAX(id) FROM historial_fallas WHERE identificador=? AND estado='Pendiente')"
                                par_hist = [f_res, detalle_res, ruta_evidencia, doc['identificador'], doc['identificador']]
                                ejecutar_query(DB_PATH, q_hist, tuple(par_hist), commit=True)

                                registrar_log(DB_PATH, st.session_state.user_login, "RESOLUCIÓN", f"Resuelto doc {doc['tipo_doc']} para {doc['identificador']} con nueva fecha {f_final_val}.")
                                st.success(f"✅ Resolución registrada (Vence: {f_final_val}). Recarga la página.")
                                st.rerun()
                        except Exception as e:
                            st.error(f"❌ Error al guardar resolución: {str(e)}")

def render_control_center(DB_PATH, filtros):
    st.markdown("<h2 class='titulo-dashboard'>🗂️ Centro de Control Organizacional</h2>", unsafe_allow_html=True)
    st.markdown("Visualiza, busca y acceda ágilmente al perfil completo de cualquier activo o trabajador.")

    f_emp_id = filtros.get('empresa_id', 0)
    f_con_id = filtros.get('contrato_id', 0)

    # ── 1. Cargar Datos Globales (Versión más reciente de cada documento) ───
    query_sql = """
        SELECT r.id, r.identificador, r.nombre, r.detalle, r.tipo_doc, r.fecha_vencimiento,
               r.categoria, r.tipo_control, r.meta_horometro, r.estado_obs, r.observaciones,
               r.fecha_condicion, r.empresa_id, r.contrato_id, r.path,
               e.nombre as empresa_val, c.nombre_contrato as contrato_val
        FROM registros r
        JOIN (
            SELECT MAX(id) as max_id 
            FROM registros 
            GROUP BY identificador, tipo_doc
        ) latest ON r.id = latest.max_id
        LEFT JOIN empresas e ON r.empresa_id = e.id
        LEFT JOIN contratos c ON r.contrato_id = c.id
        WHERE 1=1
    """
    params_sql = []
    is_master  = st.session_state.role == "Global Admin"

    if not is_master:
        query_sql += " AND r.empresa_id = ?"
        params_sql.append(st.session_state.empresa_id)
    elif f_emp_id > 0:
        query_sql += " AND r.empresa_id = ?"
        params_sql.append(f_emp_id)

    if f_con_id:
        query_sql += " AND r.contrato_id = ?"
        params_sql.append(f_con_id)

    df_reg = obtener_dataframe(DB_PATH, query_sql, tuple(params_sql))

    try:
        df_horometros  = obtener_dataframe(DB_PATH, "SELECT * FROM horometros_actuales")
        dict_horometros = dict(zip(df_horometros['identificador'], df_horometros['horas_actuales']))
    except:
        dict_horometros = {}

    # Aplicar estado dinámico
    df_reg['estado_doc'] = df_reg.apply(lambda r: calcular_estado_registro(r, dict_horometros.get(r['identificador'], 0))[0], axis=1)
    df_reg['info_doc'] = df_reg.apply(lambda r: calcular_estado_registro(r, dict_horometros.get(r['identificador'], 0))[1], axis=1)

    # ── ⚕️ BADGES DE SALUD OCUPACIONAL (independientes del semáforo documental) ──
    # No modifican el color del activo; son alertas clínicas paralelas
    dict_salud_badges = {}
    try:
        df_salud = obtener_dataframe(DB_PATH, """
            SELECT v.trabajador_id, v.resultado, p.nombre as prot_nombre
            FROM vigilancia_medica_trabajadores v
            JOIN protocolos_minsal p ON v.protocolo_id = p.id
            WHERE v.resultado IN ('Alterado (Derivación)', 'No Apto')
        """)
        for _, row_s in df_salud.iterrows():
            rut = str(row_s['trabajador_id'])
            res = row_s['resultado']
            prot = row_s['prot_nombre'].split(" ")[0] # e.g. "PREXOR"
            
            badge = f"⚠️ Riesgo {prot}" if res == "Alterado (Derivación)" else f"🚑 Rechazo {prot}"
            dict_salud_badges[rut] = dict_salud_badges.get(rut, []) + [badge]
    except Exception:
        pass  # Silenciar si la tabla no existe aún

    # ── 2. Filtros y Búsqueda ──────────────────────────────────────────────
    c1, c2, c3 = st.columns([2, 1, 1])
    search = c1.text_input("🔍 Buscar por Nombre, RUT o Patente...", placeholder="Ej: Felix, 1294..., SF-102")
    cat_filter = c2.selectbox("🏷️ Categoría", ["Todas"] + list(CATEGORIAS_CONFIG.keys()))
    status_filter = c3.selectbox("🚥 Estado", ["Todos", "🔴 Vencidos/Críticos", "🟡 Preventivos", "🟢 Al Día"])

    # ── 3. Lógica de Filtrado ──────────────────────────────────────────────
    df_f = df_reg.copy()
    if search:
        s = search.lower()
        df_f = df_f[(df_f['nombre'].astype(str).str.lower().str.contains(s, na=False)) |
                    (df_f['identificador'].astype(str).str.lower().str.contains(s, na=False))]

    if cat_filter != "Todas":
        df_f['cat_mapped'] = df_f['categoria'].apply(_mapear_categoria)
        df_f = df_f[df_f['cat_mapped'] == cat_filter]

    if status_filter != "Todos":
        if status_filter == "🔴 Vencidos/Críticos": df_f = df_f[df_f['estado_doc'] == "ROJO"]
        elif status_filter == "🟡 Preventivos": df_f = df_f[df_f['estado_doc'] == "AMARILLO"]
        elif status_filter == "🟢 Al Día": df_f = df_f[df_f['estado_doc'] == "VERDE"]

    # Agrupar para vista de tarjetas (1 tarjeta por activo/persona)
    df_cards = df_f.groupby(['identificador', 'nombre', 'detalle', 'empresa_val', 'contrato_val', 'categoria']).agg({
        'estado_doc': lambda x: 'ROJO' if 'ROJO' in x.values else ('AMARILLO' if 'AMARILLO' in x.values else 'VERDE')
    }).reset_index()

    df_cards.columns = ['ID_Patente', 'Nombre', 'Detalle', 'Empresa', 'Contrato', 'Categoria', 'EstadoGeneral']

    if df_cards.empty:
        st.warning("No se encontraron resultados para los filtros aplicados.")
        return

    col_count, col_export = st.columns([3, 1])
    col_count.write(f"Mostrando **{len(df_cards)}** expedientes encontrados.")

    # ── 📥 EXPORT EXCEL ──
    with col_export:
        import io
        # Preparar DataFrame detallado para el Excel (1 fila por documento, no por activo)
        df_export = df_f[['identificador', 'nombre', 'detalle', 'tipo_doc', 'fecha_vencimiento',
                           'estado_doc', 'info_doc', 'empresa_val', 'contrato_val', 'categoria']].copy()
        df_export.columns = ['ID/RUT/Patente', 'Nombre', 'Cargo/Detalle', 'Tipo Documento',
                             'Vencimiento', 'Estado', 'Info Estado', 'Empresa', 'Contrato', 'Categoría']
        # Mapear estado a emoji legible
        df_export['Estado'] = df_export['Estado'].map({'ROJO': '🔴 VENCIDO/CRÍTICO', 'AMARILLO': '🟡 PREVENTIVO', 'VERDE': '🟢 AL DÍA'}).fillna(df_export['Estado'])
        # Agregar columna de Badge Salud
        df_export['Alerta Salud'] = df_export['ID/RUT/Patente'].apply(
            lambda x: ' '.join(dict_salud_badges.get(str(x), [])) or '—'
        )
        excel_buf = io.BytesIO()
        with pd.ExcelWriter(excel_buf, engine='openpyxl') as writer:
            df_export.to_excel(writer, index=False, sheet_name='Estado Semáforo')
            # Segundo sheet con solo los críticos para la reunión semanal
            df_criticos = df_export[df_export['Estado'].str.contains('VENCIDO', na=False)]
            if not df_criticos.empty:
                df_criticos.to_excel(writer, index=False, sheet_name='🔴 Críticos Hoy')
        st.download_button(
            label="📥 Exportar Excel",
            data=excel_buf.getvalue(),
            file_name=f"Centro_Control_{datetime.now().strftime('%d%m%Y')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            type="primary"
        )

    # Grid de 3 columnas
    cols = st.columns(3)
    for i, (_, row) in enumerate(df_cards.iterrows()):
        idx_col = i % 3
        with cols[idx_col]:
            color_border = "#f87171" if row['EstadoGeneral'] == "ROJO" else "#fbbf24" if row['EstadoGeneral'] == "AMARILLO" else "#34d399"

            # Badges de salud (independientes del semáforo)
            badges_salud = dict_salud_badges.get(str(row['ID_Patente']), [])
            badge_html = ""
            if badges_salud:
                txt = " ".join(set(badges_salud))
                badge_html = f"<span title='Alerta de Salud Ocupacional' style='font-size:0.8em; background:#fef3c7; color:#92400e; padding:1px 6px; border-radius:10px; margin-left:4px;'>{txt} Salud</span>"

            st.markdown(f"""
                <div class="card-expediente" style="border-left: 5px solid {color_border}; background:white; padding:15px; border-radius:10px; box-shadow:0 2px 5px rgba(0,0,0,0.05); margin-bottom:15px;">
                    <div style="display:flex; align-items:center; gap:10px; margin-bottom:8px;">
                        <span style="font-size:1.2em;">{CATEGORIAS_CONFIG.get(_mapear_categoria(row['Categoria']), {}).get('icono', '📄')}</span>
                        <div style="font-weight:700; color:#1e293b; font-size:1em;">{row['Nombre']}{badge_html}</div>
                    </div>
                    <div style="font-size:0.8em; color:#64748b; margin-bottom:3px;">{row['Detalle']}</div>
                    <div style="font-size:0.75em; color:#94a3b8;">ID: {row['ID_Patente']} · {row['Empresa']}</div>
                </div>
            """, unsafe_allow_html=True)

            if st.button(f"Ver Perfil Completo", key=f"btn_{row['ID_Patente']}_{i}", use_container_width=True):
                _modal_perfil_expediente(row, df_reg, DB_PATH)

    # Estilos CSS Adicionales
    st.markdown("""
        <style>
        .doc-item {
            display: flex;
            align-items: center;
            padding: 8px 12px;
            border-radius: 6px;
            margin-bottom: 6px;
            border: 1px solid transparent;
        }
        .doc-rojo { background-color: #fef2f2; border-color: #fecaca; color: #991b1b; }
        .doc-amarillo { background-color: #fffbeb; border-color: #fef3c7; color: #92400e; }
        .doc-verde { background-color: #f0fdf4; border-color: #dcfce7; color: #166534; }
        </style>
    """, unsafe_allow_html=True)
