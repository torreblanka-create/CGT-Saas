import json
import os
import time
from datetime import datetime

import pandas as pd
import streamlit as st

from src.infrastructure.database import ejecutar_query, obtener_dataframe
from core.reports.legal import generar_pdf_compliance
from core.utils import (
    is_valid_context,
    obtener_listado_personal,
    registrar_no_conformidad_automatica,
    render_name_input_combobox,
    show_context_warning,
)
from intelligence.agents.intelligence_engine import UllTroneEngine
from vistas.salud_ocupacional.compliance_pautas import PAUTAS_PROTOCOLOS


def render_auditoria_minsal(DB_PATH, filtros):
    # --- UI ELITE NEON ONYX ---
    st.markdown("""
        <div style='background: #F5F3F0; color: #1F2937; padding: 2rem; border-radius: 15px; border: 1px solid rgba(212,212,216,0.3); margin-bottom: 2rem; box-shadow: 0 10px 15px -3px rgba(0,0,0,0.05);'>
            <div style='display: flex; align-items: center; gap: 20px;'>
                <div style='background: rgba(56, 189, 248, 0.1); padding: 15px; border-radius: 12px; border: 1px solid rgba(56, 189, 248, 0.2);'>
                    <span style='font-size: 2.5rem;'>🔎</span>
                </div>
                <div>
                    <h1 style='color: #F8FAFC; margin: 0; font-size: 1.8rem; font-family: "Outfit", sans-serif;'>Auditoría de Protocolos MINSAL</h1>
                    <p style='color: #94A3B8; margin: 5px 0 0 0; font-size: 1rem; opacity: 0.9;'>Verificación técnica de cumplimiento normativo y vigilancia epidemiológica.</p>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    if not is_valid_context(filtros):
        show_context_warning()
        return

    emp_id = filtros.get('empresa_id')
    con_id = filtros.get('contrato_id')

    # Protocolos con pautas definidas
    tabs_nombres = list(PAUTAS_PROTOCOLOS.keys())
    tabs = st.tabs([f"🛡️ {n}" for n in tabs_nombres])

    # Obtener listado de personal para selectores
    lista_personal = obtener_listado_personal(DB_PATH, filtros)

    for i, tab in enumerate(tabs):
        protocolo_actual = tabs_nombres[i]
        preguntas = PAUTAS_PROTOCOLOS[protocolo_actual]

        with tab:
            st.markdown(f"### Inspección de Campo: {protocolo_actual}")

            # --- CARGAR AUDITORÍA EXISTENTE ---
            tipo_minsal = f"MINSAL: {protocolo_actual}"
            df_hist_minsal = obtener_dataframe(DB_PATH, f"SELECT id, fecha, auditor, puntaje_final, datos_json FROM compliance_audits WHERE tipo='{tipo_minsal}' AND empresa_id={emp_id} ORDER BY id DESC")

            col_h1, col_h2 = st.columns([0.7, 0.3])
            with col_h1:
                with st.expander("📂 Historial de Hallazgos y Borradores", expanded=False):
                    if not df_hist_minsal.empty:
                        opciones_m = {row['id']: f"Folio {row['id']} | {row['fecha']} - {row['auditor']} ({row['puntaje_final']:.1f}%)" for _, row in df_hist_minsal.iterrows()}
                        sel_m = st.selectbox("Seleccione para cargar:", ["-- Nueva Inspección --"] + list(opciones_m.values()), key=f"load_m_{i}")
                        if st.button("📥 Recuperar Datos", key=f"btn_load_m_{i}"):
                            row_m = df_hist_minsal[df_hist_minsal['id'] == int(sel_m.split("Folio ")[1].split(" |")[0])].iloc[0]
                            loaded_m = json.loads(row_m['datos_json'])
                            st.session_state[f'audit_id_{i}'] = row_m['id']
                            st.session_state[f'auditor_val_{i}'] = loaded_m.get('auditor', '')
                            st.session_state[f'obs_val_{i}'] = loaded_m.get('observaciones', '')
                            # Respuestas
                            resp_m = loaded_m.get('respuestas', {})
                            for q_m, r_m in resp_m.items():
                                st.session_state[f"q_m_resp_{i}_{q_m}"] = r_m
                            st.success("Expediente cargado.")
                            st.rerun()
                    else:
                        st.caption("Sin registros previos para este centro de trabajo.")
            
            with col_h2:
                with st.popover("🧠 AI Compliance Review", use_container_width=True):
                    st.markdown("#### Consultoría Normativa Ull-Trone")
                    if st.button("Analizar Brechas de Salud", key=f"ai_minsal_{i}", type="primary", use_container_width=True):
                        with st.spinner("Ull-Trone auditando el historial..."):
                            count_audits = len(df_hist_minsal)
                            contexto = f"Protocolo: {protocolo_actual}. Auditorías registradas: {count_audits}."
                            prompt = f"Basado en {contexto}, genera 3 puntos críticos que una empresa chilena suele fallar en este protocolo y cómo prevenirlos."
                            reporte = UllTroneEngine.consultar_ia(prompt)
                            st.info(reporte)

            c1, c2 = st.columns([0.6, 0.4])

            with c1:
                st.markdown("<div class='card-glass'>#### 📋 Lista de Verificación</div>", unsafe_allow_html=True)
                respuestas = {}
                ambitos = {"General": []}
                current_ambito = "General"

                for q in preguntas:
                    if q.startswith("AMBITO"):
                        current_ambito = q
                        ambitos[current_ambito] = []
                    else:
                        if q.startswith("---"): continue
                        ambitos[current_ambito].append(q)

                st.caption("Responda cada ítem y adjunte la evidencia documental requerida.")

                idx_global = 0
                for ambito, q_list in ambitos.items():
                    with st.expander(f"📌 {ambito}", expanded=True):
                        for q in q_list:
                            idx_global += 1
                            key_q   = f"q_m_resp_{i}_{q}"
                            key_ev  = f"evid_up_{i}_{idx_global}"
                            key_path= f"evid_path_{i}_{idx_global}"

                            resp_actual = st.session_state.get(key_q, "N/A")

                            col_q, col_resp, col_evid = st.columns([3.5, 1.5, 2])
                            with col_q:
                                st.markdown(f"**{idx_global}. {q}**")
                            with col_resp:
                                resp = st.radio(
                                    f"Resp_{i}_{idx_global}",
                                    ["Sí", "No", "N/A"],
                                    key=key_q,
                                    label_visibility="collapsed",
                                    horizontal=True
                                )
                                respuestas[q] = resp
                            with col_evid:
                                path_guardado = st.session_state.get(key_path)
                                if path_guardado and os.path.exists(str(path_guardado)):
                                    st.success("📎 Adjunto", icon="✅")
                                else:
                                    archivo_ev = st.file_uploader(
                                        f"Respaldo #{idx_global}",
                                        type=['pdf', 'jpg', 'png', 'jpeg'],
                                        key=key_ev,
                                        label_visibility="collapsed"
                                    )
                                    if archivo_ev is not None:
                                        dir_ev = os.path.join("C:\\CGT_DATA", filtros.get('empresa_nom') or 'Empresa', "Auditorias_MINSAL", protocolo_actual.replace(' ', '_'), str(datetime.now().date()))
                                        os.makedirs(dir_ev, exist_ok=True)
                                        ext_ev = os.path.splitext(archivo_ev.name)[1]
                                        fname_ev = f"item_{idx_global}_{archivo_ev.name[:30]}{ext_ev}"
                                        path_ev = os.path.join(dir_ev, fname_ev)
                                        with open(path_ev, "wb") as f_ev:
                                            f_ev.write(archivo_ev.getbuffer())
                                        st.session_state[key_path] = path_ev
                                        st.success("Guardado")
                                    elif resp == "Sí":
                                        st.caption("⚠️ Requiere respaldo")

                # Formulario de Cierre de Auditoría
                with st.form(f"form_save_minsal_{i}"):
                    st.markdown("#### 🔘 Finalizar y Firmar Auditoría")
                    auditor = render_name_input_combobox("Auditor Responsable", lista_personal, key=f"auditor_{i}", default=st.session_state.get('user_nombre', ''))
                    fecha_aud = st.date_input("Fecha Inspección", value=datetime.now().date(), key=f"fecha_{i}")
                    obs_aud = st.text_area("Comentarios de Auditoría / Hallazgos Críticos", key=f"obs_{i}")

                    if st.form_submit_button("🚀 Emitir Certificado de Auditoría", type="primary", use_container_width=True):
                        if auditor:
                            si = sum(1 for r in respuestas.values() if r == "Sí")
                            no = sum(1 for r in respuestas.values() if r == "No")
                            total_evaluable = si + no
                            porcentaje = (si / total_evaluable * 100) if total_evaluable > 0 else 100.0

                            # Recopilar evidencias
                            evidencias_dict = {}
                            ev_idx = 0
                            for _, q_list_e in ambitos.items():
                                for q_e in q_list_e:
                                    ev_idx += 1
                                    p = st.session_state.get(f"evid_path_{i}_{ev_idx}")
                                    if p: evidencias_dict[q_e] = str(p)

                            datos_finales = {
                                "auditor": auditor,
                                "pauta": protocolo_actual,
                                "respuestas": respuestas,
                                "observaciones": obs_aud,
                                "evidencias": evidencias_dict
                            }

                            clasificacion = "Aceptable" if porcentaje >= 85 else ("Regular" if porcentaje >= 70 else "No Aceptable")
                            audit_id_cur = st.session_state.get(f'audit_id_{i}')

                            if audit_id_cur:
                                ejecutar_query(DB_PATH, "UPDATE compliance_audits SET fecha=?, auditor=?, datos_json=?, puntaje_final=?, clasificacion=? WHERE id=?",
                                              (str(fecha_aud), auditor, json.dumps(datos_finales), porcentaje, clasificacion, audit_id_cur), commit=True)
                            else:
                                new_id = ejecutar_query(DB_PATH, "INSERT INTO compliance_audits (fecha, auditor, tipo, empresa_id, contrato_id, datos_json, puntaje_final, clasificacion) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                                              (str(fecha_aud), auditor, tipo_minsal, emp_id, con_id, json.dumps(datos_finales), porcentaje, clasificacion), commit=True)
                                st.session_state[f'audit_id_{i}'] = new_id

                            # Alertas automáticas
                            if porcentaje < 70:
                                registrar_no_conformidad_automatica(DB_PATH, f"Bajo Cumplimiento MINSAL: {protocolo_actual}", f"Puntaje {porcentaje:.1f}% obtenido por {auditor}.", auditor, emp_id, con_id)

                            st.success(f"✅ Auditoría Registrada: {porcentaje:.1f}% ({clasificacion})")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("Identifique al auditor responsable.")

            with c2:
                # Telemetría de Cumplimiento
                si_total = sum(1 for r in respuestas.values() if r == "Sí")
                no_total = sum(1 for r in respuestas.values() if r == "No")
                total_ev = si_total + no_total
                pct_vivo = (si_total / total_ev * 100) if total_ev > 0 else 0

                st.markdown(f"""
                    <div style='background: #F5F3F0; padding: 20px; border-radius: 10px; border: 1px solid #d4d4d8; text-align: center; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);'>
                        <h4 style='color: #006B8F; margin:0; font-weight: 700;'>Telemetría en Vivo</h4>
                        <h1 style='color: #1F2937; margin:10px 0; font-size: 2.5rem;'>{pct_vivo:.1f}%</h1>
                        <p style='color: #4B5563; font-size: 0.9em; font-weight: 500;'>Cumplimiento Proyectado</p>
                    </div>
                """, unsafe_allow_html=True)

                st.divider()
                st.markdown("#### Historial Reciente")
                df_hist_aud = obtener_dataframe(DB_PATH, f"SELECT fecha, auditor, puntaje_final, clasificacion, id FROM compliance_audits WHERE tipo='{tipo_minsal}' AND empresa_id={emp_id} ORDER BY fecha DESC LIMIT 5")

                if not df_hist_aud.empty:
                    for _, row in df_hist_aud.iterrows():
                        with st.container(border=True):
                            cc1, cc2 = st.columns([3, 1])
                            cc1.markdown(f"**{row['fecha']}** - {row['auditor']}")
                            cc2.markdown(f"`{row['puntaje_final']:.1f}%`")
                            pdf_b = generar_pdf_compliance(row['id'], st.session_state.get('logo_app'), st.session_state.get('logo_cliente'))
                            st.download_button("📥 PDF", pdf_b, file_name=f"MINSAL_{protocolo_actual}_{row['fecha']}.pdf", key=f"dl_pdf_{row['id']}", use_container_width=True)
                else:
                    st.info("Sin auditorías históricas registradas.")

                # Sincronización de Brechas
                brechas_m = [q for q, r in respuestas.items() if r == "No"]
                if brechas_m:
                    st.divider()
                    st.warning(f"🚨 {len(brechas_m)} Hallazgos Detectados")
                    if st.button("🚀 Sincronizar Brechas con Centro de Control", use_container_width=True):
                        audit_id_ref = st.session_state.get(f'audit_id_{i}', 'MINSAL')
                        for bm in brechas_m:
                            ejecutar_query(DB_PATH, """
                                INSERT INTO planes_accion (codigo_plan, foco_intervencion, accion, responsable, fecha_inicio, fecha_cierre, kpi, estado, empresa_id, contrato_id)
                                VALUES (?,?,?,?,?,?,?,?,?,?)
                            """, (f"Brechas {protocolo_actual}", protocolo_actual, f"[{audit_id_ref}] {bm}", "Pendiente",
                                  str(datetime.now().date()), str(datetime.now().date()), f"Evidencia {protocolo_actual}", "Abierto", emp_id, con_id), commit=True)
                        st.success("Sincronizado.")
