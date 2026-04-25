import os
from datetime import datetime

import pandas as pd
import streamlit as st

from intelligence.agents.action_planner_engine import crear_plan_desde_alerta
from src.infrastructure.database import ejecutar_query, obtener_dataframe
from intelligence.agents.intelligence_engine import (
    ULTRON_CORE_DIRECTIVE,
    marcar_notificacion_leida,
    procesar_alertas_automaticas,
)


def render_inbox_ultron(DB_PATH, filtros):
    st.markdown("<h2 style='text-align: center; color: #00BCD4;'>🔔 Alertas</h2>", unsafe_allow_html=True)

    # ── Ejecución de escaneo automático ──
    with st.spinner("Ull-Trone escaneando riesgos..."):
        nuevas = procesar_alertas_automaticas(
            DB_PATH,
            user_role=st.session_state.role,
            empresa_id=filtros.get('empresa_id', 0),
            contrato_id=filtros.get('contrato_id', 0)
        )
        if nuevas:
            st.toast(f"🚀 Ull-Trone detectó {nuevas} nuevas alertas de seguridad.", icon="🛡️")

    # ── Barra de Acciones Globales (Miguel Style) ──
    c_acc1, c_acc2, c_acc3 = st.columns([1, 1, 2])
    with c_acc1:
        if st.button("✅ Marcar Todas Leídas", use_container_width=True):
            ejecutar_query(DB_PATH, "UPDATE notificaciones_ultron SET estado = 'Leída' WHERE estado = 'No Leída'", commit=True)
            st.success("Bandeja actualizada.")
            st.rerun()
    with c_acc2:
        if st.button("🗑️ Borrar Leídas", use_container_width=True):
            ejecutar_query(DB_PATH, "DELETE FROM notificaciones_ultron WHERE estado = 'Leída'", commit=True)
            st.success("Historial limpio.")
            st.rerun()

    st.markdown("---")

    # ── Filtros y Gestión ──
    query = "SELECT * FROM notificaciones_ultron WHERE 1=1"
    params = []

    # Mostrar solo no leídas por defecto o todas
    ver_todas = st.toggle("Ver historial completo (incluyendo leídas)", value=False)
    if not ver_todas:
        query += " AND estado = 'No Leída'"

    query += " ORDER BY fecha DESC"

    df_notif = obtener_dataframe(DB_PATH, query, tuple(params))

    if df_notif.empty:
        st.success("✅ No hay alertas críticas pendientes. ¡Buen trabajo!")
        return

    # ── Renderizado de Alertas Estilo Moderno ──
    for index, row in df_notif.iterrows():
        # Estilo según tipo
        bg_col = "#EF4444" if "Crítico" in row['tipo'] else "#F59E0B"
        border_col = "rgba(239, 68, 68, 0.2)" if "Crítico" in row['tipo'] else "rgba(245, 158, 11, 0.2)"

        with st.container(border=True):
            cols = st.columns([0.1, 0.7, 0.2])

            with cols[0]:
                st.markdown(f"<h3 style='margin:0;'>{row['tipo'][0]}</h3>", unsafe_allow_html=True)

            with cols[1]:
                st.markdown(f"**{row['tipo']}** - <span style='font-size:0.8rem; color:#8B98B8;'>{row['fecha']}</span>", unsafe_allow_html=True)
                st.markdown(f"<p style='margin:0; font-size:1rem;'>{row['mensaje']}</p>", unsafe_allow_html=True)
                st.markdown(f"<span style='font-size:0.7rem; color:#00BCD4;'>ID: {row['identificador']}</span>", unsafe_allow_html=True)

            with cols[2]:
                if row['estado'] == 'No Leída':
                    if st.button("Marcar Leída", key=f"btn_{row['id']}", use_container_width=True):
                        marcar_notificacion_leida(DB_PATH, row['id'])
                        st.rerun()

                    if st.button("📝 Crear Plan", key=f"plan_{row['id']}", use_container_width=True, type="primary"):
                        success, msg = crear_plan_desde_alerta(DB_PATH, row['id'], responsable=st.session_state.user_login)
                        if success: st.success(msg)
                        else: st.error(msg)
                        st.rerun()
                else:
                    st.markdown("<span style='color:#10B981; font-size:0.8rem;'>✓ Leída</span>", unsafe_allow_html=True)

    if st.button("Limpiar Notificaciones Leídas", type="secondary"):
        ejecutar_query(DB_PATH, "DELETE FROM notificaciones_ultron WHERE estado = 'Leída'", commit=True)
        st.rerun()
