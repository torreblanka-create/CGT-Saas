import json
import os
import time
from datetime import datetime

import pandas as pd
import streamlit as st

from src.infrastructure.database import ejecutar_query, obtener_dataframe
from core.utils import (
    is_valid_context,
    obtener_listado_personal,
    render_multiselect_personal,
    show_context_warning,
)
from vistas.salud_ocupacional.compliance_pautas import PAUTA_CPHS_INICIAL


def render_auditoria_cphs(DB_PATH, filtros):
    """
    Módulo Élite de Certificación Comité Paritario (CPHS).
    Enfoque en Progresión Digital y Cumplimiento Normativo.
    """
    st.markdown("""
        <div style='background: #F5F3F0; padding: 20px; border-radius: 15px; border-left: 5px solid #10b981; margin-bottom: 20px;'>
            <h2 style='color: #065f46; margin:0;'>🛡️ Certificación Comité Paritario (CPHS)</h2>
            <p style='color: #4B5563; margin:5px 0 0 0;'>Gestión integral de niveles Inicial, Intermedio y Avanzado según DS 54.</p>
        </div>
    """, unsafe_allow_html=True)

    if not is_valid_context(filtros):
        show_context_warning()
        return

    emp_id = filtros.get('empresa_id')
    con_id = filtros.get('contrato_id')
    lista_personal = obtener_listado_personal(DB_PATH, filtros)

    # Obtener última auditoría para telemetría
    df_last = obtener_dataframe(DB_PATH, f"SELECT puntaje_final FROM compliance_audits WHERE tipo='CPHS: Inicial' AND empresa_id={emp_id} ORDER BY id DESC LIMIT 1")
    pct_vivo = df_last.iloc[0]['puntaje_final'] if not df_last.empty else 0.0

    tabs_cphs = st.tabs(["📊 Centro de Control", "👥 Constitución", "📋 Pauta Técnica", "📈 Progresión"])

    with tabs_cphs[0]:
        st.markdown("### Estado de Certificación Actual")
        c1, c2, c3, c4 = st.columns(4)
        
        # Obtener última auditoría
        df_hist = obtener_dataframe(DB_PATH, f"SELECT id, puntaje_final, clasificacion, fecha FROM compliance_audits WHERE tipo='CPHS: Inicial' AND empresa_id={emp_id} ORDER BY id DESC LIMIT 1")
        
        if not df_hist.empty:
            last = df_hist.iloc[0]
            c1.metric("🏅 Nivel Actual", "INICIAL" if last['puntaje_final'] >= 90 else "PENDIENTE")
            c2.metric("📈 Cumplimiento", f"{last['puntaje_final']:.1f}%")
            c3.metric("📅 Última Auditoría", last['fecha'])
            c4.metric("⚖️ Estado", last['clasificacion'])
        else:
            c1.metric("🏅 Nivel Actual", "NINGUNO")
            c1.caption("Sin registros")

        st.divider()
        st.markdown("#### Historial de Expedientes")
        if not df_hist.empty:
            st.dataframe(df_hist[['fecha', 'puntaje_final', 'clasificacion']], use_container_width=True, hide_index=True)
        
        if st.button("➕ Iniciar Nuevo Proceso de Certificación", type="primary", use_container_width=True):
            # Limpiar session state para nueva auditoría
            for key in list(st.session_state.keys()):
                if key.startswith("cphs_"): del st.session_state[key]
            st.rerun()

    with tabs_cphs[1]:
        st.markdown("### Identificación y Constitución del Comité")
        with st.container(border=True):
            col_id1, col_id2 = st.columns(2)
            with col_id1:
                st.text_input("🏢 Nombre del Centro de Trabajo / CPHS", key="cphs_ident_nom", placeholder="Ej: CPHS Planta Norte")
            with col_id2:
                st.date_input("📅 Fecha de Constitución Legal", key="cphs_ident_fecha")
            
            st.divider()
            st.markdown("#### Miembros del Comité")
            integrantes = render_multiselect_personal("Seleccione integrantes (Empresa y Trabajadores)", lista_personal, key="cphs_ident_miembros")
            st.session_state['cphs_integrantes'] = integrantes

    with tabs_cphs[2]:
        st.markdown("### Auditoría de Nivel Inicial")
        respuestas = {}
        real_idx = 1
        ambitos = {}
        current_ambito = "General"
        
        for q in PAUTA_CPHS_INICIAL:
            if q.startswith("AMBITO"):
                current_ambito = q; ambitos[current_ambito] = []
            else: ambitos[current_ambito].append(q)

        for ambito, q_list in ambitos.items():
            with st.expander(f"📌 {ambito}", expanded=True):
                for q in q_list:
                    c_q1, c_q2 = st.columns([3, 1])
                    with c_q1: st.write(f"**{real_idx}.** {q}")
                    with c_q2:
                        resp = st.radio(f"CPHS_Q_{real_idx}", ["Sí", "No", "N/A"], key=f"cphs_q_val_{real_idx}", label_visibility="collapsed", horizontal=True)
                    respuestas[q] = resp
                    real_idx += 1
        
        st.session_state['cphs_respuestas'] = respuestas

        if st.button("💾 Guardar y Evaluar Nivel Inicial", type="primary", use_container_width=True):
            si = sum(1 for r in respuestas.values() if r == "Sí")
            no = sum(1 for r in respuestas.values() if r == "No")
            total = si + no
            pct = (si / total * 100) if total > 0 else 0
            
            datos_finales = {
                "respuestas": respuestas,
                "ident": st.session_state.get('cphs_ident_nom', 'N/A'),
                "integrantes": st.session_state.get('cphs_integrantes', [])
            }
            clasificacion = "Certifica" if pct >= 90 else "No Certifica"
            
            new_id = ejecutar_query(DB_PATH, "INSERT INTO compliance_audits (fecha, auditor, tipo, empresa_id, contrato_id, datos_json, puntaje_final, clasificacion) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                          (str(datetime.now().date()), st.session_state.get('username', 'Sistema'), "CPHS: Inicial", emp_id, con_id, json.dumps(datos_finales), pct, clasificacion), commit=True)
            
            st.balloons()
            st.success(f"Proceso finalizado con {pct:.1f}%. Resultado: {clasificacion}")
            time.sleep(1)
            st.rerun()

    with tabs_cphs[3]:
        st.markdown("### Ruta de Madurez CPHS")
        st.info("Visualice los requisitos para avanzar al siguiente nivel de certificación.")
        
        col_m1, col_m2, col_m3 = st.columns(3)
        with col_m1:
            st.markdown("#### 🟢 Nivel Inicial")
            st.caption("Cumplimiento normativo base (DS 54).")
            st.progress(1.0 if pct_vivo >= 90 else 0.5)
        with col_m2:
            st.markdown("#### 🟡 Nivel Intermedio")
            st.caption("Gestión proactiva y preventiva avanzada.")
            st.progress(0.0)
        with col_m3:
            st.markdown("#### 🔴 Nivel Avanzado")
            st.caption("Excelencia operativa y referencial industrial.")
            st.progress(0.0)
