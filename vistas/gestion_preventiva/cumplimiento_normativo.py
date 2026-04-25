import json
import os
from datetime import datetime

import pandas as pd
import streamlit as st

from core.compliance_data import COMPLIANCE_TEMPLATES
from config.config import LOGO_APP, obtener_logo_cliente
from src.infrastructure.database import ejecutar_query, obtener_dataframe
from core.reports.generador_pdf import pdf_engine
from src.infrastructure.security import validar_archivo_binario


def render_cumplimiento_normativo(db_path, filtros, tipo_def=None):
    titulo_vista = tipo_def if tipo_def else "Módulos de Cumplimiento Normativo (DS 594 / ISO 14001)"
    st.markdown(f"<h2 style='color: var(--cgt-blue);'>⚖️ {titulo_vista}</h2>", unsafe_allow_html=True)
    st.caption("Estandarización de auditorías legales y ambientales con gestión automática de brechas.")

    is_master = st.session_state.role == "Global Admin"
    emp_id = filtros.get('empresa_id', 0)
    con_id = filtros.get('contrato_id', 0)
    emp_nom = filtros.get('empresa_nom', 'N/A')
    con_nom = filtros.get('contrato_nom', 'N/A')

    logo_actual = obtener_logo_cliente(emp_nom)

    tab_ejecutar, tab_historial, tab_brechas = st.tabs([
        "📝 Ejecutar Auditoría",
        "🗃️ Historial de Inspecciones",
        "🎯 Gestión de Brechas (Planes de Acción)"
    ])

    with tab_ejecutar:
        if tipo_def:
            tipo_auditoria = tipo_def
        else:
            col_sel1, col_sel2 = st.columns(2)
            tipo_auditoria = col_sel1.selectbox("Seleccione el Tipo de Auditoría:", list(COMPLIANCE_TEMPLATES.keys()))

        plantilla = COMPLIANCE_TEMPLATES[tipo_auditoria]

        with st.form("form_compliance"):
            st.markdown(f"### 📋 {tipo_auditoria}")
            st.info(f"📍 **Ubicación:** {emp_nom} | {con_nom}")

            # --- Ajuste Terminológico Dinámico ---
            es_iso = "ISO" in tipo_auditoria
            opciones_eval = ["Conforme", "No Conformidad", "N/A"] if es_iso else ["Cumple", "No Cumple", "N/A"]
            lbl_falla = "No Conformidad" if es_iso else "No Cumple"
            lbl_exito = "Conforme" if es_iso else "Cumple"
            lbl_warn = "⚠️ Se requiere Plan de Acción (Levantamiento de No Conformidad)." if es_iso else "⚠️ Se requiere Plan de Acción para gestionar la desviación."
            idx_na = 2

            respuestas = {}
            fotos = {}
            brechas_data = {}

            for i_sec, seccion in enumerate(plantilla):
                col_sec_hdr, col_sec_na = st.columns([5, 1])
                # Redujimos la fuente y dimos más ancho a la columna para evitar quiebre de línea
                col_sec_hdr.markdown(f"<h5 style='margin-top: 0.4rem; margin-bottom: 0px; font-size: 1.15rem;'>🔹 {seccion['titulo']}</h5>", unsafe_allow_html=True)
                seccion_na = col_sec_na.checkbox(
                    "⛔ Sección N/A",
                    key=f"na_sec_{i_sec}",
                    help="Marca toda esta sección como No Aplica de una vez"
                )
                if seccion_na:
                    st.caption("✨ _Esta sección ha sido silenciada porque no aplica para la auditoría._")

                with st.expander(f"🔽 Evaluar / Revisar los {len(seccion['items'])} ítems de esta sección", expanded=False):
                    for i, item in enumerate(seccion['items']):
                        q_id = f"{seccion['titulo']}_{i}"

                        # Soporte para ítems nuevos (dict) y legacy (string)
                        if isinstance(item, dict):
                            requisito  = item.get("requisito", "")
                            norma      = item.get("norma", "")
                            orientacion = item.get("orientacion", "")
                            texto_brecha = requisito
                        else:
                            requisito  = item
                            norma      = ""
                            orientacion = ""
                            texto_brecha = item

                        with st.container(border=True):
                            # Pregunta principal
                            st.markdown(f"**{requisito}**")

                            # Acordeón con norma y orientación
                            if norma or orientacion:
                                with st.expander("📖 Ver norma y evidencia esperada"):
                                    if norma:
                                        st.markdown(f"📌 **Norma legal:** `{norma}`")
                                    if orientacion:
                                        st.markdown(f"🔍 **Orientación / Evidencia:** {orientacion}")

                            c1, c2 = st.columns([2, 2])
                            if seccion_na:
                                respuestas[q_id] = "N/A"
                                c1.radio(
                                    "Evaluación:", opciones_eval,
                                    key=f"rad_{q_id}", horizontal=True,
                                    index=idx_na, disabled=True
                                )
                            else:
                                respuestas[q_id] = c1.radio(
                                    "Evaluación:", opciones_eval,
                                    key=f"rad_{q_id}", horizontal=True
                                )
                            fotos[q_id] = c2.file_uploader(
                                "Adjuntar Evidencia (Opcional):",
                                type=["pdf", "jpg", "jpeg", "png"], key=f"file_{q_id}"
                            )

                            if not seccion_na and respuestas[q_id] == lbl_falla:
                                st.warning(lbl_warn)
                                col_b1, col_b2, col_b3 = st.columns(3)
                                brechas_data[q_id] = {
                                    "pregunta": texto_brecha,
                                    "accion":   col_b1.text_input("Acción Correctiva:", key=f"acc_{q_id}"),
                                    "responsable": col_b2.text_input("Responsable:", key=f"res_{q_id}"),
                                    "fecha_limite": col_b3.date_input("Fecha Límite:", key=f"fec_{q_id}")
                                }

            st.divider()
            submit = st.form_submit_button("✅ Finalizar y Guardar Auditoría", type="primary", use_container_width=True)

            if submit:
                # Validar Fotos (Binario)
                err_fotos = []
                fotos_paths = {}
                for k, f_obj in fotos.items():
                    if f_obj:
                        valido, msg = validar_archivo_binario(f_obj, os.path.splitext(f_obj.name)[1])
                        if not valido:
                            err_fotos.append(f"{f_obj.name}: {msg}")
                        else:
                            # Guardar foto
                            save_dir = os.path.join("CGT_DATA", "compliance", str(datetime.now().year), k)
                            os.makedirs(save_dir, exist_ok=True)
                            path = os.path.join(save_dir, f_obj.name)
                            with open(path, "wb") as f: f.write(f_obj.getbuffer())
                            fotos_paths[k] = path

                if err_fotos:
                    for e in err_fotos: st.error(f"❌ Error en adjunto: {e}")
                else:
                    # Calcular Porcentaje
                    sitios_evaluados = 0
                    sitios_cumplen = 0
                    for k, v in respuestas.items():
                        if v != "N/A":
                            sitios_evaluados += 1
                            if v == lbl_exito: sitios_cumplen += 1

                    pct = (sitios_cumplen / sitios_evaluados * 100) if sitios_evaluados > 0 else 100.0

                    # Clasificación de Colores
                    if pct >= 95:
                        clasificacion = "Aceptable"
                        color_hex = "#10B981" # Green
                    elif pct >= 80:
                        clasificacion = "Moderado"
                        color_hex = "#F59E0B" # Yellow
                    else:
                        clasificacion = "Inaceptable"
                        color_hex = "#EF4444" # Red

                    # Guardar Auditoría
                    datos_completos = {
                        "respuestas": respuestas,
                        "fotos": fotos_paths,
                        "brechas": {k: {"accion": v["accion"], "responsable": v["responsable"], "fecha_limite": str(v["fecha_limite"])} for k, v in brechas_data.items()}
                    }

                    query_audit = """
                        INSERT INTO compliance_audits (fecha, auditor, tipo, empresa_id, contrato_id, datos_json, puntaje_final, clasificacion)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """
                    audit_id = ejecutar_query(db_path, query_audit, (
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"), st.session_state.username,
                        tipo_auditoria, emp_id, con_id, json.dumps(datos_completos), pct, clasificacion
                    ), commit=True)

                    # Guardar Brechas en tabla dedicada para seguimiento
                    for q_id, b in brechas_data.items():
                        query_gap = """
                            INSERT INTO compliance_gaps (audit_id, item_id, pregunta, accion_correctiva, responsable, fecha_limite)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """
                        ejecutar_query(db_path, query_gap, (
                            audit_id, q_id, b["pregunta"], b["accion"], b["responsable"], str(b["fecha_limite"])
                        ), commit=True)

                    st.markdown(f"""
                        <div style="background-color: {color_hex}20; border-left: 5px solid {color_hex}; padding: 20px; border-radius: 5px; margin-top: 10px;">
                            <h2 style="color: {color_hex}; margin: 0;">{pct:.1f}% - {clasificacion}</h2>
                            <p style="margin-top: 10px; font-size: 1.1em;">
                                Auditoría finalizada con éxito. Se han detectado {len(brechas_data)} brechas que requieren seguimiento.
                            </p>
                        </div>
                    """, unsafe_allow_html=True)
                    st.balloons()

    with tab_historial:
        st.write("Historial de auditorías normativas realizadas.")
        if tipo_def:
            query_h = "SELECT id, fecha, tipo, puntaje_final, clasificacion, auditor FROM compliance_audits WHERE empresa_id = ? AND tipo = ? ORDER BY id DESC"
            df_h = obtener_dataframe(db_path, query_h, (emp_id, tipo_def))
        else:
            query_h = "SELECT id, fecha, tipo, puntaje_final, clasificacion, auditor FROM compliance_audits WHERE empresa_id = ? ORDER BY id DESC"
            df_h = obtener_dataframe(db_path, query_h, (emp_id,))

        if df_h.empty:
            st.info("No hay auditorías registradas para esta empresa.")
        else:
            # Aplicar colores a la tabla de historial
            def color_clasif(val):
                color = "#10B981" if val == "Aceptable" else "#F59E0B" if val == "Moderado" else "#EF4444"
                return f'color: {color}; font-weight: bold'

            st.dataframe(df_h.style.applymap(color_clasif, subset=['clasificacion']), use_container_width=True, hide_index=True)

            sel_id = st.selectbox("Seleccione ID para ver detalle:", ["--"] + df_h['id'].tolist())
            if sel_id != "--":
                audit_row = obtener_dataframe(db_path, "SELECT tipo, datos_json, puntaje_final, clasificacion FROM compliance_audits WHERE id = ?", (sel_id,)).iloc[0]
                datos = json.loads(audit_row['datos_json'])

                c_det1, c_det2 = st.columns([3, 1])
                with c_det1:
                    st.markdown(f"#### Detalle: {audit_row['tipo']}")
                with c_det2:
                    if st.button("📊 Generar PDF", key=f"pdf_{sel_id}", use_container_width=True):
                        try:
                            pdf_bytes = pdf_engine.generar('COMPLIANCE', sel_id, LOGO_APP, logo_actual)
                            st.download_button(
                                label="📥 Descargar Informe PDF",
                                data=pdf_bytes,
                                file_name=f"Informe_Cumplimiento_{sel_id}.pdf",
                                mime="application/pdf",
                                use_container_width=True
                            )
                        except Exception as e:
                            st.error(f"Error al generar PDF: {e}")

                st.divider()
                for q_id, resp in datos['respuestas'].items():
                    with st.container(border=True):
                        st.write(f"**Punto:** {q_id}")
                        st.write(f"Resultado: `{resp}`")
                        if q_id in datos['fotos']:
                            st.image(datos['fotos'][q_id], width=300, caption="Evidencia Adjunta")
                        if q_id in datos['brechas']:
                            b = datos['brechas'][q_id]
                            st.error(f"⚠️ **Brecha Detectada:** {b['accion']} (Resp: {b['responsable']} | Plazo: {b['fecha_limite']})")

    with tab_brechas:
        st.markdown("#### 🎯 Seguimiento de Hallazgos y Acciones Correctivas")
        st.info("En esta pestaña se consolidan todos los ítems marcados como 'No Cumple'.")

        if tipo_def:
            query_g = """
                SELECT g.id, a.fecha, a.tipo, g.pregunta, g.accion_correctiva, g.responsable, g.fecha_limite, g.estado
                FROM compliance_gaps g
                JOIN compliance_audits a ON g.audit_id = a.id
                WHERE a.empresa_id = ? AND a.tipo = ?
                ORDER BY g.fecha_limite ASC
            """
            df_g = obtener_dataframe(db_path, query_g, (emp_id, tipo_def))
        else:
            query_g = """
                SELECT g.id, a.fecha, a.tipo, g.pregunta, g.accion_correctiva, g.responsable, g.fecha_limite, g.estado
                FROM compliance_gaps g
                JOIN compliance_audits a ON g.audit_id = a.id
                WHERE a.empresa_id = ?
                ORDER BY g.fecha_limite ASC
            """
            df_g = obtener_dataframe(db_path, query_g, (emp_id,))

        if df_g.empty:
            st.success("✅ ¡Excelente! No hay brechas pendientes para esta empresa.")
        else:
            # Mostrar métricas de brechas
            total_g = len(df_g)
            abiertas = len(df_g[df_g['estado'] == 'Abierto'])
            cerradas = len(df_g[df_g['estado'] == 'Cerrado'])

            m1, m2, m3 = st.columns(3)
            m1.metric("Total de Hallazgos", total_g)
            m2.metric("Pendientes", abiertas, delta_color="inverse", delta=f"{abiertas} items")
            m3.metric("Cerradas", cerradas)

            st.divider()
            st.dataframe(df_g, use_container_width=True, hide_index=True)

            st.markdown("#### 📝 Gestionar Compromiso")
            with st.form("form_update_gap"):
                gap_id = st.selectbox("Seleccione ID de Brecha a Actualizar:", df_g[df_g['estado'] != 'Cerrado']['id'].tolist() if not df_g[df_g['estado'] != 'Cerrado'].empty else ["--"])
                nuevo_estado = st.selectbox("Actualizar Estado:", ["En Proceso", "Cerrado"])
                obs = st.text_area("Observaciones de Cierre / Avance:")

                if st.form_submit_button("Actualizar Hallazgo"):
                    if gap_id != "--":
                        ejecutar_query(db_path, "UPDATE compliance_gaps SET estado = ? WHERE id = ?", (nuevo_estado, gap_id), commit=True)
                        st.success(f"Hallazgo #{gap_id} actualizado a {nuevo_estado}.")
                        st.rerun()
                    else:
                        st.warning("No hay brechas pendientes seleccionables.")
