import json
import os
from datetime import datetime, timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.infrastructure.database import ejecutar_query, obtener_dataframe
from core.utils import render_hybrid_date_input, is_valid_context, show_context_warning


# ─────────────────────────────────────────────────────────────────────────────
# Mapeo de categorías para Confiabilidad (espeja Trinity de Activos)
# ─────────────────────────────────────────────────────────────────────────────
_CONF_CATEGORY_MAP = {
    'Vehiculo_Liviano':  {'titulo': '🚛 Confiabilidad: Camionetas',          'icono': '🚛', 'cats': ['Vehiculo_Liviano']},
    'Camion_Transporte': {'titulo': '🚚 Confiabilidad: Camiones',             'icono': '🚚', 'cats': ['Camion_Transporte']},
    'Equipo_Pesado':     {'titulo': '🏗️ Confiabilidad: Equipos Pesados',      'icono': '🏗️', 'cats': ['Equipo_Pesado', 'Izaje']},
    None:                {'titulo': '⚙️ Confiabilidad y Mantenimiento (CMMS)', 'icono': '⚙️', 'cats': ['Equipos', 'Izaje', 'Vehiculo_Liviano', 'Camion_Transporte', 'Equipo_Pesado', 'Maquinaria Pesada & Vehículos']},
}


def render_confiabilidad_activos(db_path, filtros, categoria=None):
    cfg = _CONF_CATEGORY_MAP.get(categoria, _CONF_CATEGORY_MAP[None])
    st.markdown(f"<h2 style='color: var(--cgt-blue);'>{cfg['titulo']}</h2>", unsafe_allow_html=True)
    st.write("Gestión integral de disponibilidad mecánica, horómetros y estado legal de la flota.")

    if not is_valid_context(filtros):
        show_context_warning()
        return

    emp_id = filtros.get('empresa_id', 0)
    con_id = filtros.get('contrato_id', 0)

    # 1. Obtener Maestro de Equipos — filtrado por categoría
    cats = cfg['cats']
    placeholders = ','.join(['?'] * len(cats))
    q_equipos = f"SELECT identificador, nombre, tipo_doc, fecha_vencimiento FROM registros WHERE categoria IN ({placeholders}) AND empresa_id = ?"
    df_equipos = obtener_dataframe(db_path, q_equipos, tuple(cats) + (emp_id,))

    if df_equipos.empty:
        st.warning(f"No se encontraron registros de {cfg['titulo']} para esta empresa.")
        return

    lista_identificadores = df_equipos['identificador'].unique().tolist()
    dic_nombres = df_equipos.set_index('identificador')['nombre'].to_dict()

    tab_dash, tab_mant, tab_horo, tab_legal = st.tabs([
        "📊 Dashboard Disponibilidad", 
        "🔧 Bitácora de Mantenimiento", 
        "⏱️ Control Horómetros",
        "📑 Salud Legal (Documental)"
    ])

    # ── TAB 1: DASHBOARD DISPONIBILIDAD MECÁNICA ──
    with tab_dash:
        # Traer Eventos Abiertos (Equipos en Taller)
        q_abiertos = "SELECT identificador FROM eventos_confiabilidad WHERE estado = 'Abierto' AND empresa_id = ?"
        df_abiertos = obtener_dataframe(db_path, q_abiertos, (emp_id,))
        
        equipos_detenidos_ids = df_abiertos['identificador'].tolist() if not df_abiertos.empty else []
        
        total_eq = len(lista_identificadores)
        detenidos = len(set(equipos_detenidos_ids))
        operativos = total_eq - detenidos
        disponibilidad = (operativos / total_eq * 100) if total_eq > 0 else 0.0

        # Traer MTTR
        q_mttr = "SELECT AVG(duracion_min) as mttr_min FROM eventos_confiabilidad WHERE estado = 'Cerrado' AND empresa_id = ?"
        df_mttr = obtener_dataframe(db_path, q_mttr, (emp_id,))
        mttr_hrs = (df_mttr.iloc[0]['mttr_min'] / 60.0) if not df_mttr.empty and pd.notnull(df_mttr.iloc[0]['mttr_min']) else 0.0

        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        col_m1.metric("Disponibilidad de Flota", f"{disponibilidad:.1f}%")
        col_m2.metric("Equipos Operativos", operativos)
        col_m3.metric("En Taller (Detenidos)", detenidos, delta_color="inverse")
        col_m4.metric("MTTR (Histórico)", f"{mttr_hrs:.1f} hrs", help="Mean Time To Repair (Promedio de horas para reparar)")

        st.divider()
        c_graf1, c_graf2 = st.columns(2)
        
        with c_graf1:
            st.markdown("### 🧬 Estado en Tiempo Real")
            fig_st = px.pie(
                values=[operativos, detenidos], 
                names=["Operativos", "Detenidos (En Mantención)"],
                color=["Operativos", "Detenidos (En Mantención)"],
                color_discrete_map={"Operativos":"#10B981", "Detenidos (En Mantención)":"#EF4444"},
                hole=0.6
            )
            fig_st.update_layout(margin=dict(t=0, b=0, l=0, r=0))
            st.plotly_chart(fig_st, use_container_width=True)

        with c_graf2:
            st.markdown("### 📉 Frecuencia de Fallas por Sistema")
            q_fallas = "SELECT tipo_falla, count(*) as cantidad FROM eventos_confiabilidad WHERE empresa_id = ? GROUP BY tipo_falla"
            df_fallas = obtener_dataframe(db_path, q_fallas, (emp_id,))
            if not df_fallas.empty:
                fig_bar = px.bar(df_fallas, x="cantidad", y="tipo_falla", orientation='h', color="tipo_falla")
                fig_bar.update_layout(showlegend=False, xaxis_title="N° de Eventos", yaxis_title="")
                st.plotly_chart(fig_bar, use_container_width=True)
            else:
                st.info("Sin registros de fallas para graficar.")

    # ── TAB 2: BITÁCORA DE MANTENIMIENTO ──
    with tab_mant:
        st.markdown("#### 🛠️ Registro de Evento de Confiabilidad (Detención)")
        with st.form("form_falla_equipo"):
            c1, c2 = st.columns([1, 2])
            with c1:
                eq_sel = st.selectbox("Seleccione Equipo", lista_identificadores, format_func=lambda x: f"{x} - {dic_nombres.get(x, '')}")
                fecha_falla = render_hybrid_date_input("Fecha de Detención", key="fecha_fall")
                tipo_f = st.selectbox("Clasificación del Evento", [
                    "Correctivo - Falla Mecánica", "Correctivo - Falla Eléctrica", 
                    "Correctivo - Sistema Hidráulico", "Correctivo - Neumáticos/Orugas",
                    "Preventivo - Pauta Regular", "Preventivo - Gran Componente", "Daño por Operación"
                ])
            with c2:
                desc_falla = st.text_area("Descripción de la Falla / Síntomas", height=130)
            
            foto_falla = st.file_uploader("Evidencia de Falla (Opcional)", type=["jpg", "png"])
            
            if st.form_submit_button("🚨 Reportar Detención (Abrir OT)", type="primary"):
                if eq_sel and desc_falla:
                    path_foto = ""
                    if foto_falla:
                        import uuid
                        dir_fallas = os.path.join("C:\\\\CGT_DATA", "Mantencion")
                        os.makedirs(dir_fallas, exist_ok=True)
                        path_foto = os.path.join(dir_fallas, f"Falla_{eq_sel}_{uuid.uuid4().hex[:6]}.jpg")
                        with open(path_foto, "wb") as f: f.write(foto_falla.getbuffer())

                    ejecutar_query(db_path, """
                        INSERT INTO eventos_confiabilidad (identificador, tipo_falla, descripcion, estado, duracion_min, foto_path, empresa_id, contrato_id)
                        VALUES (?, ?, ?, 'Abierto', 0, ?, ?, ?)
                    """, (eq_sel, tipo_f, desc_falla, path_foto, emp_id, con_id), commit=True)
                    st.success(f"✅ Se ha detenido el equipo {eq_sel} en el sistema.")
                    st.rerun()

        st.divider()
        st.markdown("#### 🔧 Órdenes de Trabajo Abiertas (Equipos Detenidos)")
        df_ab = obtener_dataframe(db_path, "SELECT id, fecha, identificador, tipo_falla, descripcion FROM eventos_confiabilidad WHERE estado='Abierto' AND empresa_id=?", (emp_id,))
        if not df_ab.empty:
            for _, rot in df_ab.iterrows():
                with st.expander(f"🔴 OT #{rot['id']} | {rot['identificador']} | {rot['tipo_falla']}"):
                    st.write(f"**Fecha Falla:** {rot['fecha']} \n\n**Descripción:** {rot['descripcion']}")
                    c_cierre1, c_cierre2 = st.columns([1, 1])
                    downtime = c_cierre1.number_input("Tiempo total de parada (Horas)", min_value=0.1, value=1.0, step=0.5, key=f"dt_{rot['id']}")
                    if c_cierre2.button("✅ Cerrar Reparación y Liberar Equipo", key=f"btn_c_{rot['id']}", use_container_width=True):
                        mins = int(downtime * 60)
                        ejecutar_query(db_path, "UPDATE eventos_confiabilidad SET estado='Cerrado', duracion_min=? WHERE id=?", (mins, rot['id']), commit=True)
                        st.success(f"Equipo liberado. MTTR registrado: {downtime} horas.")
                        st.rerun()
        else:
            st.success("✅ No hay equipos detenidos en taller.")

    # ── TAB 3: CONTROL DE HORÓMETROS ──
    with tab_horo:
        st.markdown("#### ⏱️ Ingreso de Lecturas")
        with st.form("form_horometro"):
            ch1, ch2, ch3 = st.columns(3)
            with ch1: h_eq = st.selectbox("Equipo", lista_identificadores, format_func=lambda x: f"{x}", key="h_eq")
            with ch2: h_val = st.number_input("Lectura (Hrs o Km)", min_value=0.0, step=1.0)
            with ch3: h_fec = render_hybrid_date_input("Fecha de Lectura", key="h_fec")
            
            if st.form_submit_button("💾 Guardar Lectura", type="primary", use_container_width=True):
                ejecutar_query(db_path, "INSERT INTO ultron_horometros_history (identificador, fecha, valor, empresa_id, contrato_id) VALUES (?, ?, ?, ?, ?)",
                               (h_eq, h_fec.strftime("%Y-%m-%d"), h_val, emp_id, con_id), commit=True)
                st.success("Lectura guardada.")
                st.rerun()

        st.divider()
        st.markdown("#### 📈 Curva de Utilización Histórica")
        df_h = obtener_dataframe(db_path, "SELECT identificador, fecha, valor FROM ultron_horometros_history WHERE empresa_id=? ORDER BY fecha ASC", (emp_id,))
        if not df_h.empty:
            view_eq = st.selectbox("Seleccionar Curva a Visualizar", ["Todos"] + lista_identificadores)
            if view_eq != "Todos":
                df_h = df_h[df_h['identificador'] == view_eq]
            
            fig_h = px.line(df_h, x='fecha', y='valor', color='identificador', markers=True)
            st.plotly_chart(fig_h, use_container_width=True)
        else:
            st.info("Sin registros de horómetros.")

    # ── TAB 4: SALUD DOCUMENTAL (Legal) ──
    with tab_legal:
        st.markdown("#### 📑 Radar de Vencimientos Legales de Activos")
        st.caption("Control estricto de Revisiones Técnicas, Certificaciones de Izaje, Pólizas, etc.")
        
        df_doc = df_equipos.copy()
        df_doc['fecha_vencimiento'] = pd.to_datetime(df_doc['fecha_vencimiento'], errors='coerce')
        hoy_dt = datetime.now()
        prox_30 = hoy_dt + timedelta(days=30)
        
        def doc_status(v):
            if pd.isnull(v): return "Indefinido"
            if v < hoy_dt: return "Caducado (Ilegal)"
            if v <= prox_30: return "Alerta (Por vencer)"
            return "Vigente"
            
        df_doc['Estatus Legal'] = df_doc['fecha_vencimiento'].apply(doc_status)
        
        col_d1, col_d2 = st.columns(2)
        with col_d1:
            fig_d = px.bar(
                df_doc['Estatus Legal'].value_counts().reset_index(), 
                x='Estatus Legal', y='count', 
                color='Estatus Legal',
                color_discrete_map={"Vigente":"#10B981", "Alerta (Por vencer)":"#F59E0B", "Caducado (Ilegal)":"#EF4444", "Indefinido":"#64748B"}
            )
            st.plotly_chart(fig_d, use_container_width=True)
        
        with col_d2:
            criticos = df_doc[df_doc['Estatus Legal'].isin(['Caducado (Ilegal)', 'Alerta (Por vencer)'])]
            if not criticos.empty:
                st.warning("⚠️ Documentos Críticos / Vencidos")
                st.dataframe(criticos[['identificador', 'tipo_doc', 'Estatus Legal', 'fecha_vencimiento']], use_container_width=True, hide_index=True)
            else:
                st.success("✅ La flota se encuentra sana a nivel documental.")
