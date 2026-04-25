import json
import time
from datetime import datetime

import pandas as pd
import streamlit as st

from src.infrastructure.database import ejecutar_query, obtener_dataframe
from core.utils import is_valid_context, render_hybrid_date_input, show_context_warning
from intelligence.agents.intelligence_engine import UllTroneEngine

# ─────────────────────────────────────────────────────────────────────────────
ORIGENES_NCR = [
    "Auditoría Interna",
    "Auditoría Externa (Certificación)",
    "Auditoría RESSO (Codelco)",
    "Auditoría MINSAL: PREXOR",
    "Auditoría MINSAL: PLANESI",
    "Auditoría MINSAL: HIC",
    "Auditoría MINSAL: UV",
    "Auditoría MINSAL: CEAL-SM",
    "Auditoría DS 44/2025 (SGSST)",
    "Inspección de Terreno",
    "Queja de Cliente",
    "Desviación de Proceso",
    "Incidente / Accidente",
    "Fiscalización SEREMI/SUSESO/DT",
    "Otro",
]

_ESTADO_COLORS = {
    "Abierta": "🔴",
    "En Proceso": "🟡",
    "Cerrada": "🟢",
    "Anulada": "⚪",
}


def render_no_conformidades(DB_PATH, filtros):
    # --- UI ELITE NEON ONYX ---
    st.markdown("""
        <div style='background: #F5F3F0; 
                    padding: 25px; border-radius: 15px; border-left: 5px solid #ef4444; 
                    margin-bottom: 25px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);'>
            <div style='display: flex; align-items: center; gap: 15px;'>
                <div style='background: rgba(239,68,68,0.15); padding: 10px; border-radius: 10px;'>
                    <span style='font-size: 2rem;'>⚠️</span>
                </div>
                <div>
                    <h2 style='color: #dc2626; margin:0; font-family:Outfit, sans-serif;'></h2>
                        Control de Desviaciones & Hallazgos
                    </h2>
                    <p style='color: #94A3B8; margin:5px 0 0 0; font-size: 0.95rem;'>
                        Gestión inteligente de No Conformidades y Mejora Continua Sistémica.
                    </p>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    if not is_valid_context(filtros):
        show_context_warning()
        return

    emp_id = filtros.get('empresa_id')
    con_id = filtros.get('contrato_id')

    # --- KPIs rápidos ---
    df_all = obtener_dataframe(
        DB_PATH,
        "SELECT estado FROM sgi_no_conformidades WHERE empresa_id=?",
        (emp_id,)
    )
    total = len(df_all)
    abiertas = len(df_all[df_all['estado'] == 'Abierta']) if not df_all.empty else 0
    en_proceso = len(df_all[df_all['estado'] == 'En Proceso']) if not df_all.empty else 0
    cerradas = len(df_all[df_all['estado'] == 'Cerrada']) if not df_all.empty else 0

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total NCR", total)
    m2.metric("🔴 Abiertas", abiertas, delta=f"Acción requerida" if abiertas > 0 else None,
              delta_color="inverse" if abiertas > 0 else "off")
    m3.metric("🟡 En Proceso", en_proceso)
    m4.metric("🟢 Cerradas", cerradas)

    st.divider()

    tab_nueva, tab_lista, tab_automaticas = st.tabs([
        "📝 Levantar Hallazgo",
        "📋 Registro Completo",
        "🤖 Generadas Automáticamente"
    ])

    # ── TAB 1: NUEVA NCR ──────────────────────────────────────────────────────
    with tab_nueva:
        st.markdown("#### Formulario de No Conformidad")
        with st.form("form_ncr_completo", clear_on_submit=False):
            c1, c2 = st.columns(2)
            with c1:
                f_ncr = render_hybrid_date_input("Fecha Detección", key="f_ncr")
                origen = st.selectbox("Origen del Hallazgo", ORIGENES_NCR)
                resp = st.text_input("Responsable del Cierre (Líder SAC)", placeholder="Ej: Jefe de Calidad")
                prioridad = st.select_slider("Prioridad", options=["Alta", "Media", "Baja"], value="Alta")
            with c2:
                desc = st.text_area("Descripción de la No Conformidad", height=130,
                                    placeholder="Describa con precisión el hallazgo, incluyendo evidencia observada...")
                f_vencimiento = render_hybrid_date_input("Fecha Límite de Cierre", key="f_vto_ncr")

            st.markdown("#### 🔬 Análisis y Plan Correctivo")
            cc1, cc2 = st.columns(2)
            with cc1:
                causa = st.text_area("Causa Raíz (5 Porqués / Ishikawa)", height=150,
                                     placeholder="Aplique la metodología de análisis de causa raíz...")
            with cc2:
                plan = st.text_area("Plan de Acción Correctora", height=150,
                                    placeholder="Acciones concretas, responsables y plazos...")

            if st.form_submit_button("✅ Registrar No Conformidad", use_container_width=True, type="primary"):
                if desc and causa and plan and resp:
                    datos_extra = json.dumps({"prioridad": prioridad, "fecha_limite": str(f_vencimiento)})
                    ejecutar_query(DB_PATH, """
                        INSERT INTO sgi_no_conformidades
                        (fecha, origen, descripcion, responsable, causa_raiz, plan_accion, estado, empresa_id, contrato_id)
                        VALUES (?, ?, ?, ?, ?, ?, 'Abierta', ?, ?)
                    """, (str(f_ncr), origen, desc, resp, causa, plan, emp_id, con_id), commit=True)
                    st.success("✅ No Conformidad registrada exitosamente.")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("⚠️ Todos los campos son obligatorios (Descripción, Causa Raíz, Plan de Acción, Responsable).")

        st.markdown("#### 🔬 Inteligencia de Causa Raíz")
        # --- AI 5 WHYS ASSISTANT (FUERA DEL FORM) ---
        with st.expander("🪄 Asistente AI: Brainstorming Causa Raíz (5 Porqués)"):
            st.caption("Ull-Trone analizará tu descripción y te propondrá una secuencia lógica de causas hasta llegar a la raíz.")
            # Necesitamos que la descripción esté fuera del form o usar st.session_state para capturarla
            temp_desc = st.text_area("Borrador de Descripción para IA:", placeholder="Escriba aquí para que la IA le ayude...", key="desc_ia_ncr")
            
            if st.button("🧠 Generar Análisis con IA", key="ai_5whys_btn"):
                if temp_desc:
                    with st.spinner("Ull-Trone analizando causalidad..."):
                        prompt = f"Basado en este hallazgo: '{temp_desc}', propón un análisis de '5 Porqués' para llegar a la causa raíz. Estructura la respuesta como una lista numerada de 5 porqués y termina con una 'Causa Raíz Final' y un 'Plan de Acción Sugerido'."
                        res = UllTroneEngine.consultar_ia(prompt)
                        st.session_state.temp_5whys = res
                else:
                    st.warning("Escribe primero una descripción en el campo de borrador arriba.")
            
            if 'temp_5whys' in st.session_state:
                st.info(st.session_state.temp_5whys)
                st.success("💡 Utilice esta sugerencia para completar el formulario oficial de arriba.")

    # ── TAB 2: REGISTRO COMPLETO ───────────────────────────────────────────────
    with tab_lista:
        st.markdown("#### Filtros")
        fc1, fc2, fc3 = st.columns(3)
        filtro_estado = fc1.selectbox("Estado", ["Todos", "Abierta", "En Proceso", "Cerrada", "Anulada"])
        filtro_origen = fc2.selectbox("Origen", ["Todos"] + ORIGENES_NCR)
        busqueda_ncr = fc3.text_input("🔍 Buscar en descripción", placeholder="Palabra clave...")

        query_list = """
            SELECT id, fecha, origen, descripcion, responsable, causa_raiz, plan_accion, estado
            FROM sgi_no_conformidades WHERE empresa_id=?
        """
        params_list = [emp_id]

        if filtro_estado != "Todos":
            query_list += " AND estado=?"
            params_list.append(filtro_estado)
        if filtro_origen != "Todos":
            query_list += " AND origen=?"
            params_list.append(filtro_origen)

        query_list += " ORDER BY id DESC"
        df_ncr = obtener_dataframe(DB_PATH, query_list, tuple(params_list))

        if busqueda_ncr.strip() and not df_ncr.empty:
            df_ncr = df_ncr[df_ncr['descripcion'].str.contains(busqueda_ncr.strip(), case=False, na=False)]

        if not df_ncr.empty:
            st.caption(f"Mostrando **{len(df_ncr)}** registros.")
            
            if st.session_state.role == "Global Admin":
                with st.popover("⚙️ Acciones Masivas"):
                    st.warning("🚨 Acción Irreversible")
                    if st.button("🔥 Borrar TODAS las NCR de esta Empresa", type="primary", use_container_width=True):
                        ejecutar_query(DB_PATH, "DELETE FROM sgi_no_conformidades WHERE empresa_id = ?", (emp_id,), commit=True)
                        st.success("Se han eliminado todos los registros de NCR.")
                        time.sleep(1)
                        st.rerun()
            st.divider()
            for _, r in df_ncr.iterrows():
                icono = _ESTADO_COLORS.get(r['estado'], "⚪")
                with st.expander(
                    f"{icono} NCR #{r['id']} | {r['origen']} | {r['fecha']} — {r['estado']}",
                    expanded=False
                ):
                    col_info, col_actions = st.columns([3, 1])

                    with col_info:
                        st.markdown(f"**📋 Descripción:**\n{r['descripcion']}")
                        st.markdown(f"**🔬 Causa Raíz:**\n{r['causa_raiz']}")
                        st.markdown(f"**🛠️ Plan de Acción:**\n{r['plan_accion']}")
                        st.markdown(f"**👤 Responsable:** {r['responsable']}")

                    with col_actions:
                        estado_actual = r['estado']
                        st.markdown("**Cambiar Estado:**")

                        if estado_actual == "Abierta":
                            if st.button("🟡 Poner En Proceso", key=f"enp_{r['id']}", use_container_width=True):
                                ejecutar_query(DB_PATH, "UPDATE sgi_no_conformidades SET estado='En Proceso' WHERE id=?",
                                              (r['id'],), commit=True)
                                st.rerun()

                        if estado_actual in ["Abierta", "En Proceso"]:
                            verdad = st.text_input("Evidencia de cierre:", key=f"ev_{r['id']}")
                            if st.button("🟢 Cerrar NCR", key=f"close_ncr_{r['id']}", use_container_width=True, type="primary"):
                                ejecutar_query(DB_PATH,
                                              "UPDATE sgi_no_conformidades SET estado='Cerrada', plan_accion=COALESCE(plan_accion,'') || ? WHERE id=?",
                                              (f"\n\n[CIERRE {datetime.now().strftime('%d/%m/%Y')}]: {verdad}", r['id']), commit=True)
                                st.success("NCR Cerrada.")
                                time.sleep(0.5)
                                st.rerun()

                        if estado_actual != "Anulada":
                            if st.button("⚪ Anular", key=f"anl_{r['id']}", use_container_width=True):
                                ejecutar_query(DB_PATH, "UPDATE sgi_no_conformidades SET estado='Anulada' WHERE id=?",
                                              (r['id'],), commit=True)
                                st.rerun()
        else:
            st.info("No se encontraron No Conformidades con los filtros aplicados.")

    # ── TAB 3: GENERADAS AUTOMÁTICAMENTE ──────────────────────────────────────
    with tab_automaticas:
        st.markdown("#### 🤖 NCR Generadas Automáticamente por Auditorías")
        st.info("Estas NCR fueron creadas de forma automática cuando una auditoría resultó bajo el umbral de aceptación. "
                "Deben ser validadas y gestionadas por el responsable del área.")

        origenes_auto = [o for o in ORIGENES_NCR if "Auditoría" in o]
        df_auto = obtener_dataframe(
            DB_PATH,
            f"SELECT id, fecha, origen, descripcion, responsable, estado FROM sgi_no_conformidades "
            f"WHERE empresa_id=? AND origen IN ({', '.join(['?']*len(origenes_auto))}) ORDER BY id DESC",
            tuple([emp_id] + origenes_auto)
        ) if origenes_auto else pd.DataFrame()

        if not df_auto.empty:
            for _, r in df_auto.iterrows():
                icono = _ESTADO_COLORS.get(r['estado'], "⚪")
                with st.container(border=True):
                    col_a, col_b = st.columns([3, 1])
                    col_a.markdown(f"{icono} **NCR #{r['id']}** — {r['origen']} ({r['fecha']})")
                    col_a.caption(r['descripcion'][:200] + "..." if len(r['descripcion']) > 200 else r['descripcion'])
                    col_a.markdown(f"👤 Responsable: **{r['responsable']}**")
                    if r['estado'] in ["Abierta", "En Proceso"]:
                        if col_b.button("🟢 Cerrar", key=f"auto_close_{r['id']}", use_container_width=True):
                            ejecutar_query(DB_PATH,
                                          "UPDATE sgi_no_conformidades SET estado='Cerrada' WHERE id=?",
                                          (r['id'],), commit=True)
                            st.rerun()
        else:
            st.success("✅ No hay NCR automáticas abiertas. Sistema de auditorías en cumplimiento.")
