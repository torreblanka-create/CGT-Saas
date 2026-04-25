import pandas as pd
import plotly.express as px
import streamlit as st

from src.infrastructure.database import obtener_dataframe


def render_auditoria_sistema(DB_PATH):
    st.markdown("<h2 style='color: #00BCD4;'>🛡️ Auditoría del Sistema e Historial de Actividad</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color: #8B98B8;'>Panel de supervisión avanzada para el Administrador Global (Miguel).</p>", unsafe_allow_html=True)

    if st.session_state.role != "Global Admin":
        st.error("Acceso restringido: Este módulo solo es accesible para el Administrador Global.")
        return

    tab_access, tab_activity = st.tabs(["🔑 Historial de Accesos", "📜 Auditoría de Actividad"])

    with tab_access:
        st.markdown("#### Registro de Logins y Logouts")
        query_access = """
            SELECT fecha, usuario, accion, detalle 
            FROM logs_actividad 
            WHERE accion IN ('LOGIN', 'LOGOUT') 
            ORDER BY fecha DESC
        """
        df_access = obtener_dataframe(DB_PATH, query_access)

        if df_access.empty:
            st.info("No se registran accesos recientes en la base de datos.")
        else:
            # Gráfico de accesos por día
            df_access['fecha_dt'] = pd.to_datetime(df_access['fecha'])
            df_daily = df_access.groupby(df_access['fecha_dt'].dt.date).size().reset_index(name='Accesos')
            fig = px.bar(df_daily, x='fecha_dt', y='Accesos', title="Frecuencia de Accesos Diarios",
                         color_discrete_sequence=['#00BCD4'])
            st.plotly_chart(fig, use_container_width=True)

            st.dataframe(df_access, use_container_width=True)

    with tab_activity:
        st.markdown("#### Registro Maestro de Operaciones")
        st.write("Visualiza cada acción técnica o de negocio realizada por los usuarios en el sistema.")

        # Filtros
        c1, c2 = st.columns(2)
        with c1:
            f_usuario = st.selectbox("Filtrar por Usuario:", ["Todos"] + list(obtener_dataframe(DB_PATH, "SELECT DISTINCT usuario FROM logs_actividad")['usuario'].tolist()))
        with c2:
            f_accion = st.selectbox("Filtrar por Acción:", ["Todas"] + list(obtener_dataframe(DB_PATH, "SELECT DISTINCT accion FROM logs_actividad")['accion'].tolist()))

        query_audit = "SELECT fecha, usuario, accion, detalle FROM logs_actividad WHERE 1=1"
        params = []
        if f_usuario != "Todos":
            query_audit += " AND usuario = ?"
            params.append(f_usuario)
        if f_accion != "Todas":
            query_audit += " AND accion = ?"
            params.append(f_accion)

        query_audit += " ORDER BY fecha DESC LIMIT 500"

        df_audit = obtener_dataframe(DB_PATH, query_audit, tuple(params))

        if df_audit.empty:
            st.info("No se encontraron registros que coincidan con los filtros.")
        else:
            st.dataframe(df_audit, use_container_width=True)

            # Resumen de tipos de acciones
            df_summary = df_audit.groupby('accion').size().reset_index(name='count')
            fig_pie = px.pie(df_summary, values='count', names='accion', title="Distribución de Acciones",
                             hole=0.4, color_discrete_sequence=px.colors.sequential.Teal)
            st.plotly_chart(fig_pie, use_container_width=True)
