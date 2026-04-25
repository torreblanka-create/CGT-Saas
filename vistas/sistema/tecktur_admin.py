import streamlit as st
import pandas as pd
import plotly.express as px
from src.infrastructure.database import obtener_dataframe, ejecutar_query

def render_tecktur_admin(db_path):
    st.markdown("""
        <div class="premium-header">
            <h1 style='margin:0;'>🏭 Centro de Mando Tecktur Digital</h1>
            <p style='margin:0; opacity:0.8;'>Gestión Estratégica de Clientes y Salud del Ecosistema CGT.SaaS</p>
        </div>
    """, unsafe_allow_html=True)

    # ── KPIs GLOBALES ──
    col1, col2, col3, col4 = st.columns(4)
    
    df_emps = obtener_dataframe(db_path, "SELECT COUNT(*) as c FROM empresas")
    df_users = obtener_dataframe(db_path, "SELECT COUNT(*) as c FROM usuarios")
    df_logs = obtener_dataframe(db_path, "SELECT COUNT(*) as c FROM logs_actividad")
    
    with col1:
        st.metric("Empresas / Clientes", df_emps['c'].iloc[0] if not df_emps.empty else 0)
    with col2:
        st.metric("Usuarios Totales", df_users['c'].iloc[0] if not df_users.empty else 0)
    with col3:
        st.metric("Actividad (Logs)", df_logs['c'].iloc[0] if not df_logs.empty else 0)
    with col4:
        st.metric("Disponibilidad", "99.9%", "SaaS Ready")

    st.divider()

    t1, t2, t3 = st.tabs(["👥 Gestión de Tenants", "📊 Analítica de Uso", "📜 Auditoría Global"])

    with t1:
        st.markdown("### 🏢 Clientes Activos")
        query_t = """
            SELECT e.id, e.nombre, e.rut, (SELECT COUNT(*) FROM usuarios WHERE empresa_id = e.id) as num_usuarios
            FROM empresas e
        """
        df_tenants = obtener_dataframe(db_path, query_t)
        st.dataframe(df_tenants, use_container_width=True, hide_index=True)
        
        with st.expander("➕ Registrar Nuevo Cliente (Onboarding)"):
            with st.form("new_tenant"):
                n_nom = st.text_input("Nombre de la Empresa:")
                n_rut = st.text_input("RUT:")
                n_rep = st.text_input("Representante Legal:")
                if st.form_submit_button("🚀 Dar de Alta"):
                    if n_nom and n_rut:
                        ejecutar_query(db_path, "INSERT INTO empresas (nombre, rut, rep_legal) VALUES (?,?,?)", (n_nom, n_rut, n_rep), commit=True)
                        st.success(f"Empresa {n_nom} creada correctamente.")
                        st.rerun()

    with t2:
        st.markdown("### 📈 Distribución de Usuarios por Empresa")
        if not df_tenants.empty:
            fig = px.pie(df_tenants, values='num_usuarios', names='nombre', hole=0.4,
                         title="Cuota de Mercado Interna", color_discrete_sequence=px.colors.qualitative.Pastel)
            st.plotly_chart(fig, use_container_width=True)

    with t3:
        st.markdown("### 🕵️ Registro de Actividad Cruzada")
        df_audit = obtener_dataframe(db_path, "SELECT fecha, usuario, accion, detalle FROM logs_actividad ORDER BY id DESC LIMIT 50")
        st.table(df_audit)

def render_onboarding_wizard(db_path):
    st.info("Próximamente: Wizard de configuración inicial para nuevos clientes.")
