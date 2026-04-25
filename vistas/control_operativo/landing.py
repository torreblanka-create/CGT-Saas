import streamlit as st

from vistas.ui_components import render_pillar_grid


def render_landing_control_operativo(db_path, filtros):
    """
    Landing page for Pillar 1: Control Operativo.
    """
    modules = [
        {
            "label": "👷 Personal",
            "icon": "👷",
            "desc": "Capacitaciones, EPP y documentación legal de trabajadores.",
            "route": "👷 Personal"
        },
        {
            "label": "🚜 Maquinaria",
            "icon": "🚜",
            "desc": "Control de documentación, revisiones técnicas y horómetros.",
            "route": "🚜 Maquinaria"
        },
        {
            "label": "⛓️ Elementos de izaje",
            "icon": "⛓️",
            "desc": "Certificaciones y estado de eslingas, grilletes y accesorios.",
            "route": "⛓️ Elementos de izaje"
        },
        {
            "label": "🧰 Instrumentos",
            "icon": "🧰",
            "desc": "Calibraciones y trazabilidad de equipos de medición.",
            "route": "🧰 Instrumentos"
        },
        {
            "label": "🚨 Emergencias",
            "icon": "🚨",
            "desc": "Extintores, botiquines y equipos de primera respuesta.",
            "route": "🚨 Emergencias"
        }
    ]

    render_pillar_grid(
        title="1. Control Operativo",
        description="Gestión integral de activos industriales y personal de faena.",
        modules=modules
    )

    # Herramientas Administrativas del Pilar (Movidas de Configuración)
    with st.expander("🛠️ Herramientas Administrativas (Edición y Borrado)", expanded=False):
        tab_ed, tab_el = st.tabs(["✏️ Editar Perfiles", "🗑️ Eliminación Masiva"])

        with tab_ed:
            st.info("Corrige datos maestros de trabajadores o equipos del Pilar 1.")
            import pandas as pd

            from src.infrastructure.database import ejecutar_query, obtener_dataframe
            query_r = "SELECT identificador, nombre, categoria, empresa_id, contrato_id, detalle FROM registros WHERE categoria IN ('Personal', 'Maquinaria Pesada & Vehículos', 'Elementos de izaje', 'Instrumentos y Metrología', 'Sistemas de Emergencia')"
            df_edit = obtener_dataframe(db_path, query_r)
            if not df_edit.empty:
                df_edit['display'] = df_edit['identificador'].astype(str) + " | " + df_edit['nombre'].astype(str)
                sel_edit = st.selectbox("🎯 Perfil a Editar:", ["-- Seleccione --"] + df_edit['display'].tolist(), key="lp1_edit")
                if sel_edit != "-- Seleccione --":
                    id_edit = sel_edit.split(" | ")[0].strip()
                    row = df_edit[df_edit['identificador'].astype(str) == id_edit].iloc[0]
                    with st.form("form_lp1_edit"):
                        n_nom = st.text_input("Nombre", value=row['nombre'])
                        n_det = st.text_input("Detalle/Cargo", value=row['detalle'] if pd.notnull(row['detalle']) else "")
                        if st.form_submit_button("💾 Guardar Cambios"):
                            ejecutar_query(db_path, "UPDATE registros SET nombre=?, detalle=? WHERE identificador=?", (n_nom, n_det, id_edit), commit=True)
                            st.success("✅ Actualizado.")
                            st.rerun()

        with tab_el:
            st.warning("⚠️ Eliminación permanente de registros seleccionados.")
            if not df_edit.empty:
                to_del = st.multiselect("Seleccione registros a eliminar:", df_edit['display'].tolist(), key="lp1_del")
                if to_del and st.button("🗑️ Eliminar permanentemente", type="primary"):
                    for p in to_del:
                        id_del = p.split(" | ")[0].strip()
                        ejecutar_query(db_path, "DELETE FROM registros WHERE identificador = ?", (id_del,), commit=True)
                    st.success(f"✅ {len(to_del)} registros eliminados.")
                    st.rerun()
