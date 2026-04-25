"""
Módulo: Auditoría DS 44/2025 (Decreto Supremo SST)
Separado desde auditorias.py como módulo independiente.
"""
import json
import time
from datetime import datetime

import streamlit as st

from src.infrastructure.database import ejecutar_query, obtener_dataframe
from core.reports.legal import generar_pdf_fuf_ds44
from core.utils import (
    is_valid_context,
    obtener_listado_personal,
    registrar_no_conformidad_automatica,
    render_name_input_combobox,
    show_context_warning,
)

# Importar pauta desde módulo maestro
from vistas.salud_ocupacional.compliance_pautas import PAUTA_DS44


def render_auditoria_ds44(DB_PATH, filtros):
    st.markdown("<h2 style='color: var(--cgt-blue);'>⚖️ Auditoría DS 44/2025 (Reglamento SST)</h2>", unsafe_allow_html=True)
    st.write("Instrumento de auditoría basado en el Formulario Único de Fiscalización (FUF) de la SUSESO.")

    if not is_valid_context(filtros):
        show_context_warning()
        return

    emp_id = filtros.get('empresa_id')
    con_id = filtros.get('contrato_id')
    lista_personal = obtener_listado_personal(DB_PATH, filtros)

    tipo_audit = "MINSAL: DS 44/2025 (Reglamento SST)"
    preguntas = PAUTA_DS44

    c1, c2 = st.columns([0.5, 0.5])

    with c1:
        st.markdown("#### Nueva Auditoría DS 44")

        df_hist = obtener_dataframe(DB_PATH, f"SELECT id, fecha, auditor, puntaje_final, datos_json FROM compliance_audits WHERE tipo='{tipo_audit}' AND empresa_id={emp_id} ORDER BY id DESC")
        with st.expander("📂 Cargar Historial / Borrador", expanded=False):
            if not df_hist.empty:
                opciones = {row['id']: f"ID {row['id']} | {row['fecha']} - {row['auditor']} ({row['puntaje_final']:.1f}%)" for _, row in df_hist.iterrows()}
                sel = st.selectbox("Seleccione para cargar:", ["-- Nueva --"] + list(opciones.values()), key="load_ds44")
                if st.button("📥 Cargar", key="btn_load_ds44"):
                    row = df_hist[df_hist['id'] == int(sel.split("ID ")[1].split(" |")[0])].iloc[0]
                    loaded = json.loads(row['datos_json'])
                    st.session_state['ds44_audit_id'] = row['id']
                    for q, r in loaded.get('respuestas', {}).items():
                        st.session_state[f"ds44_q_{q}"] = r
                    st.success("Cargado correctamente.")
                    st.rerun()
            else:
                st.caption("No hay registros previos.")

        with st.form("form_ds44"):
            auditor = render_name_input_combobox("Nombre del Auditor", lista_personal, key="auditor_ds44", default=st.session_state.get('user_nombre', ''))
            fecha_aud = st.date_input("Fecha Auditoría", value=datetime.now().date())
            st.divider()

            respuestas = {}
            real_idx = 1
            ambitos = {}
            current_ambito = "General"
            for q in preguntas:
                if q.startswith("AMBITO"):
                    current_ambito = q
                    ambitos[current_ambito] = []
                else:
                    ambitos[current_ambito].append(q)

            for ambito, q_list in ambitos.items():
                with st.expander(f"📌 {ambito}", expanded=True):
                    for q in q_list:
                        st.write(f"**{real_idx}. {q}**")
                        key_q = f"ds44_q_{q}"
                        resp = st.radio(f"Opt_DS44_{real_idx}", ["Sí", "No", "N/A"], key=key_q, label_visibility="collapsed", horizontal=True)
                        respuestas[q] = resp
                        real_idx += 1

            obs_aud = st.text_area("Hallazgos u Observaciones Críticas", key="ds44_obs")

            if st.form_submit_button("Guardar Auditoría DS 44", type="primary", use_container_width=True):
                if auditor:
                    si = sum(1 for r in respuestas.values() if r == "Sí")
                    no = sum(1 for r in respuestas.values() if r == "No")
                    total_evaluable = si + no
                    porcentaje = (si / total_evaluable * 100) if total_evaluable > 0 else 100.0

                    datos_finales = {"auditor": auditor, "pauta": "DS 44/2025", "respuestas": respuestas, "observaciones": obs_aud}
                    clasificacion = "Cumple" if porcentaje >= 90 else "No Cumple"

                    audit_id = st.session_state.get('ds44_audit_id')
                    if audit_id:
                        ejecutar_query(DB_PATH, "UPDATE compliance_audits SET fecha=?, auditor=?, datos_json=?, puntaje_final=?, clasificacion=? WHERE id=?",
                                      (str(fecha_aud), auditor, json.dumps(datos_finales), porcentaje, clasificacion, audit_id), commit=True)
                    else:
                        new_id = ejecutar_query(DB_PATH, "INSERT INTO compliance_audits (fecha, auditor, tipo, empresa_id, contrato_id, datos_json, puntaje_final, clasificacion) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                                      (str(fecha_aud), auditor, tipo_audit, emp_id, con_id, json.dumps(datos_finales), porcentaje, clasificacion), commit=True)
                        st.session_state['ds44_audit_id'] = new_id

                    st.success(f"✅ Auditoría DS 44 Guardada: {porcentaje:.1f}% ({clasificacion})")

                    if clasificacion == "No Cumple":
                        ok_nc, _ = registrar_no_conformidad_automatica(
                            DB_PATH,
                            origen="Auditoría DS 44/2025 (SGSST)",
                            descripcion=f"DS 44 obtuvo {porcentaje:.1f}% — no supera el 90% mínimo. Auditor: {auditor}.",
                            responsable=auditor,
                            empresa_id=emp_id,
                            contrato_id=con_id
                        )
                        if ok_nc:
                            st.warning("⚠️ NCR generada automáticamente en Gobernanza & SGI.")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Nombre del auditor requerido.")

        brechas = [q for q, r in respuestas.items() if r == "No"]
        if brechas:
            st.divider()
            st.markdown(f"#### ⚡ Sincronización de {len(brechas)} Brechas")
            with st.form("form_ds44_sync"):
                sync_list = []
                for b in brechas:
                    with st.expander(f"🔴 {b}", expanded=True):
                        cc1, cc2 = st.columns(2)
                        a = cc1.text_input("Corrección", key=f"ds44_acc_{b}")
                        r = cc2.text_input("Responsable", key=f"ds44_res_{b}")
                        f = st.date_input("Fecha", key=f"ds44_dat_{b}")
                        sync_list.append({"item": b, "acc": a, "res": r, "fec": str(f)})
                if st.form_submit_button("🚀 Enviar a Centro de Control"):
                    plan_nom = f"Brechas DS 44 - {datetime.now().strftime('%d/%m/%Y')}"
                    ref_id = st.session_state.get('ds44_audit_id', 'DS44')
                    c_count = 0
                    for item in sync_list:
                        if item['acc'] and item['res']:
                            ejecutar_query(DB_PATH, """
                                INSERT INTO planes_accion (codigo_plan, foco_intervencion, accion, responsable, fecha_inicio, fecha_cierre, kpi, estado, empresa_id, contrato_id)
                                VALUES (?,?,?,?,?,?,?,?,?,?)
                            """, (plan_nom, "DS 44", f"[{ref_id}] {item['item']}: {item['acc']}", item['res'],
                                  str(datetime.now().date()), item['fec'], "Evidencia DS44", "Abierto", emp_id, con_id), commit=True)
                            c_count += 1
                    if c_count > 0:
                        st.success(f"✅ {c_count} brechas enviadas.")
                        st.balloons()

    with c2:
        st.markdown("#### Historial DS 44")
        q_h = f"""
            SELECT id, fecha as Fecha, auditor as Auditor, puntaje_final as Cumplimiento, clasificacion as Estado, datos_json
            FROM compliance_audits WHERE tipo = '{tipo_audit}' AND empresa_id = {emp_id} ORDER BY fecha DESC
        """
        df_h = obtener_dataframe(DB_PATH, q_h)
        if not df_h.empty:
            df_v = df_h[['Fecha', 'Auditor', 'Cumplimiento', 'Estado']].copy()
            df_v['Cumplimiento'] = df_v['Cumplimiento'].apply(lambda x: f"{x:.1f}%")
            st.dataframe(df_v, use_container_width=True, hide_index=True)

            for _, row_a in df_h.head(5).iterrows():
                with st.expander(f"📄 {row_a['Fecha']} - {row_a['Auditor']} ({row_a['Cumplimiento']:.1f}%)"):
                    pdf_b = generar_pdf_fuf_ds44(row_a['id'], st.session_state.get('logo_app'), st.session_state.get('logo_cliente'))
                    st.download_button(f"📥 Descargar FUF Oficial", pdf_b, file_name=f"FUF_DS44_{row_a['Fecha']}.pdf", key=f"dl_ds44_{row_a['id']}")
                    st.divider()
                    det_d = json.loads(row_a['datos_json'])
                    for q_t, r_v in det_d['respuestas'].items():
                        icon = "✅" if r_v == "Sí" else ("❌" if r_v == "No" else "⚪")
                        st.write(f"{icon} {q_t}")
        else:
            st.info("Sin registros de DS 44.")
