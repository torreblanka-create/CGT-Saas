import io
import json
import os
import sqlite3
from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st

from src.infrastructure.archivos import validar_archivo_seguro

# Imports de núcleo
from config.config import (
    DB_PATH,
    LOGO_APP,
    LOGO_CLIENTE,
    get_scoped_path,
    obtener_logo_cliente,
)
from src.infrastructure.database import (
    ejecutar_query,
    obtener_config,
    obtener_dataframe,
    registrar_log,
)
from core.intelligence_parser import (
    extract_text_from_excel,
    extract_text_from_pdf,
    parse_incident_with_gemini,
)
from core.reports import (
    generar_pdf_confiabilidad,  # Usaremos la base para PDF si es necesario
)
from core.utils import (
    is_valid_context,
    obtener_listado_personal,
    render_name_input_combobox,
    show_context_warning,
)


def render_gestion_incidentes(db_path, filtros):
    # --- HEADER PREMIUM ---
    st.markdown("""
        <div class='premium-header'>
            <div style='display: flex; align-items: center; gap: 15px;'>
                <div style='background: var(--accent-neon); padding: 12px; border-radius: 12px; box-shadow: var(--shadow-premium);'>
                    <span style='font-size: 24px;'>⚠️</span>
                </div>
                <div>
                    <h1 style='margin: 0; color: var(--text-heading); font-size: 1.8rem;'>Reporte de Incidentes (HSE)</h1>
                    <p style='margin: 0; color: var(--text-muted); font-size: 0.9rem;'>Centro de Mando: Gestión Proactiva de Alertas y Riesgos Críticos</p>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    tab_dashboard, tab_registro, tab_historico = st.tabs([
        "📊 Dashboard de Riesgos",
        "📝 Registro de Alerta",
        "📂 Catastro Histórico"
    ])

    empresa_id = filtros.get('empresa_id', 0)
    contrato_id = filtros.get('contrato_id', 0)
    empresa_nom = filtros.get('empresa_nom', 'Otros')
    contrato_nom = filtros.get('contrato_nom', 'Sin Contrato')

    # --- DATOS GLOBALES PARA DASHBOARD ---
    query_dash = "SELECT * FROM reportes_incidentes"
    params_dash = []
    if empresa_id > 0:
        query_dash += " WHERE empresa_id = ?"
        params_dash.append(empresa_id)

    df_inc = obtener_dataframe(db_path, query_dash, tuple(params_dash))

    # --- CATÁLOGOS HSE ---
    tipos_evento = ["STP", "CTP", "Primera Atención", "Trayecto", "Cuasi Accidente", "Hallazgo", "Falla Operacional", "Daño Material", "Daño Ambiental"]
    riesgos_criticos = [
        "Vehículos", "Energía Eléctrica", "Trabajo En Altura", "Maniobras De Izaje",
        "Liberación Descontrolada De Energías", "Caída De Rocas En Mina Rajo", "Incendio",
        "Sustancias Peligrosas", "Tronaduras Y Explosivos", "Interacción Con Partes Móviles",
        "Exposición A Atmósferas Peligrosas En Espacios Confinados", "Contacto Con Material Fundido",
        "Caída De Objetos", "Operaciones Ferroviarias", "Exposición A Avalancha", "Caída A Piques",
        "Exposición Bombeo De Agua Barro", "Aplastamiento / Atrapamiento Por Caída De Rocas En Mina Subterránea",
        "Estallido De Roca", "Concentración Ambiental Peligrosa De Polvo Y Sílice", "Exposición A Arsénico Inorgánico",
        "Deformación, Inestabilidad Y Colapso De Componentes En Pasillos, Pisos Y Barandas",
        "Colapso Estructural En Mina Subterránea", "Desprendimiento Y Caída De Talud En Mina Cielo Abierto",
        "Choque / Colisión / Volcamiento De Maquinarias", "Choque / Colisión / Volcamiento De Equipos Autónomos",
        "Atropello", "Airblast (Golpe De Aire)"
    ]
    niveles_alerta = ["BP", "L4", "L3", "L2", "L1"]

    with tab_dashboard:
        if df_inc.empty:
            st.info("No hay incidentes reportados en esta operación.")
        else:
            # MÉTRICAS ELITE
            total_alertas = len(df_inc)
            invest_req = len(df_inc[df_inc['requiere_investigacion'] == 'Si'])
            l4_l3 = len(df_inc[df_inc['clasificacion_alerta'].isin(['L4', 'L3'])])
            rc_mas_repetido = df_inc['riesgo_critico'].mode()[0] if not df_inc['riesgo_critico'].empty else "N/A"

            m1, m2, m3, m4 = st.columns(4)
            with m1:
                st.markdown(f"""
                    <div class='metric-card-cgt' style='border-left: 4px solid #3b82f6;'>
                        <p class='metric-label-cgt'>Total Alertas SGI</p>
                        <p class='metric-value-cgt' style='color: #3b82f6;'>{total_alertas}</p>
                    </div>
                """, unsafe_allow_html=True)
            with m2:
                st.markdown(f"""
                    <div class='metric-card-cgt' style='border-left: 4px solid #ef4444;'>
                        <p class='metric-label-cgt'>Investigaciones</p>
                        <p class='metric-value-cgt' style='color: #ef4444;'>{invest_req}</p>
                    </div>
                """, unsafe_allow_html=True)
            with m3:
                st.markdown(f"""
                    <div class='metric-card-cgt' style='border-left: 4px solid #f59e0b;'>
                        <p class='metric-label-cgt'>Alto Potencial</p>
                        <p class='metric-value-cgt' style='color: #f59e0b;'>{l4_l3}</p>
                    </div>
                """, unsafe_allow_html=True)
            with m4:
                st.markdown(f"""
                    <div class='metric-card-cgt' style='border-left: 4px solid #10b981;'>
                        <p class='metric-label-cgt'>Riesgo Top 1</p>
                        <p style='font-size: 0.9rem; font-weight: 700; color: #10b981; margin: 5px 0 0 0;'>{rc_mas_repetido[:20] + '...' if len(rc_mas_repetido)>20 else rc_mas_repetido}</p>
                    </div>
                """, unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)

            col_d1, col_d2 = st.columns(2)
            with col_d1:
                # Pareto de Riesgos Fatales
                pareto_riesgo = df_inc.groupby('riesgo_critico').size().reset_index(name='frecuencia').sort_values('frecuencia', ascending=True)
                fig_r = px.bar(
                    pareto_riesgo.tail(10), 
                    x='frecuencia', 
                    y='riesgo_critico', 
                    orientation='h',
                    title="Top 10 Riesgos Fatales (Frecuencia)",
                    color='frecuencia', 
                    color_continuous_scale='Reds'
                )
                fig_r.update_layout(template="plotly_dark", height=400, showlegend=False, margin=dict(l=20, r=20, t=50, b=20))
                st.plotly_chart(fig_r, use_container_width=True)

            with col_d2:
                # Distribución por Gravedad
                fig_pie = px.pie(
                    df_inc, 
                    names='clasificacion_alerta', 
                    hole=0.4, 
                    title="Distribución por Gravedad de Alerta",
                    color_discrete_sequence=px.colors.sequential.OrRd_r
                )
                fig_pie.update_layout(template="plotly_dark", height=400, margin=dict(l=20, r=20, t=50, b=20))
                st.plotly_chart(fig_pie, use_container_width=True)

            # Tendencia Histórica
            df_inc['mes'] = pd.to_datetime(df_inc['fecha']).dt.strftime('%Y-%m')
            tendencia = df_inc.groupby('mes').size().reset_index(name='total')
            fig_l = px.line(
                tendencia, 
                x='mes', 
                y='total', 
                markers=True, 
                line_shape='spline',
                title="Tendencia Mensual de Incidentes"
            )
            fig_l.update_layout(template="plotly_dark", height=350, yaxis_title="Cant. Incidentes")
            fig_l.update_traces(line_color="#E11D48", line_width=3, marker=dict(size=8, color="#E11D48"))
            st.plotly_chart(fig_l, use_container_width=True)

    with tab_registro:
        # --- CARGA CON IA (Premium Container) ---
        st.markdown("""
            <div style='background: rgba(59, 130, 246, 0.05); border: 1px solid rgba(59, 130, 246, 0.2); padding: 20px; border-radius: 12px; margin-bottom: 25px;'>
                <div style='display: flex; align-items: center; gap: 10px; margin-bottom: 10px;'>
                    <span style='font-size: 20px;'>🤖</span>
                    <h4 style='margin: 0; color: #1e40af;'>Auto-llenado Inteligente</h4>
                </div>
                <p style='margin: 0; color: #64748b; font-size: 0.9rem;'>
                    Cargue un informe en papel escaneado (PDF) o un reporte en Excel. 
                    <b>Ull-Trone v4.0</b> extraerá los parámetros críticos y pre-llenará el formulario automáticamente.
                </p>
            </div>
        """, unsafe_allow_html=True)

        file_ai = st.file_uploader("Documento de Respaldo Original (PDF/Excel):", type=['pdf', 'xlsx', 'xls'], key="inc_ai_uploader", label_visibility="collapsed")

        if file_ai:
            if st.button("🧠 Procesar Documento con Ultron", type="primary", use_container_width=True):
                api_key = obtener_config(db_path, "gemini_api_key", "")
                if not api_key:
                    st.error("Debes configurar la Gemini API Key en 'Ull-Trone Inteligente' primero.")
                else:
                    with st.spinner("Ull-Trone extrayendo parámetros críticos..."):
                        if file_ai.name.endswith('.pdf'):
                            text = extract_text_from_pdf(file_ai)
                        else:
                            text = extract_text_from_excel(file_ai)

                        res_ai = parse_incident_with_gemini(text, api_key)
                        if "error" in res_ai:
                            st.error(res_ai["error"])
                        else:
                            st.session_state["inc_ai_data"] = res_ai
                            st.success("¡Datos extraídos con éxito! El formulario ha sido poblado.")
                            st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)
        # --- VALORES POR DEFECTO (DESDE IA O RESET) ---
        ai_data = st.session_state.get("inc_ai_data", {})
        if not is_valid_context(filtros):
            show_context_warning()
        else:
            lista_personal = obtener_listado_personal(db_path, filtros)
            with st.form("form_incidente", clear_on_submit=True):
                col1, col2 = st.columns(2)
                with col1:
                    folio = st.text_input("🔢 Folio Interno (Opcional):", value=ai_data.get("folio", ""), placeholder="Ej: VELTV-2026-001")

                    fecha_def = datetime.now().date()
                    if ai_data.get("fecha"):
                        try: fecha_def = datetime.strptime(ai_data["fecha"], "%Y-%m-%d").date()
                        except: pass
                    fecha = st.date_input("📅 Fecha del Incidente:", value=fecha_def)

                    idx_tipo = 0
                    if ai_data.get("tipo_evento") in tipos_evento:
                        idx_tipo = tipos_evento.index(ai_data["tipo_evento"]) + 1
                    tipo_ev = st.selectbox("🎯 Tipo de Evento:", ["-- Seleccione --"] + tipos_evento, index=idx_tipo)

                    reportante = render_name_input_combobox("Informante / Reportado por", lista_personal, key="inc_informante", default=ai_data.get("reportante", ""))
                with col2:
                    hora_def = datetime.now().time()
                    if ai_data.get("hora"):
                        try: hora_def = datetime.strptime(ai_data["hora"], "%H:%M").time()
                        except: pass
                    hora = st.time_input("⏰ Hora aproximada:", value=hora_def)

                    idx_riesgo = 0
                    if ai_data.get("riesgo_critico") in riesgos_criticos:
                        idx_riesgo = riesgos_criticos.index(ai_data["riesgo_critico"]) + 1
                    riesgo = st.selectbox("🔥 Riesgo Crítico Asociado:", ["-- Seleccione --"] + riesgos_criticos, index=idx_riesgo)

                    control = st.text_input("🛠️ Control Crítico Fallido/Ausente:", value=ai_data.get("control_fallido", ""), placeholder="Ej: Integridad Mecánica de Vehículo")
                    afectado = render_name_input_combobox("Personal Involucrado / Afectado", lista_personal, key="inc_afectado", default=ai_data.get("afectado", ""))

                st.divider()
                que_paso = st.text_area("❓ ¿QUÉ OCURRIÓ? (Describa los hechos sin nombres):", value=ai_data.get("que_ocurrio", ""))
                porque_paso = st.text_area("🧐 ¿POR QUÉ OCURRIÓ? (Análisis preliminar de causas):", value=ai_data.get("porque_paso", ""))

                st.markdown("#### ⚡ Acciones Inmediatas Implementadas")
                acc_ia = ai_data.get("acciones", ["", "", ""])
                acc1 = st.text_input("1.", value=acc_ia[0] if len(acc_ia)>0 else "", placeholder="Acción 1")
                acc2 = st.text_input("2.", value=acc_ia[1] if len(acc_ia)>1 else "", placeholder="Acción 2")
                acc3 = st.text_input("3.", value=acc_ia[2] if len(acc_ia)>2 else "", placeholder="Acción 3")

                st.divider()
                c_h1, c_h2 = st.columns(2)
                with c_h1:
                    idx_alerta = 0
                    if ai_data.get("clasificacion") in niveles_alerta:
                        idx_alerta = niveles_alerta.index(ai_data["clasificacion"])
                    clasificacion = st.selectbox("🏷️ Clasificación de Alerta (HSE):", niveles_alerta, index=idx_alerta)
                    investigacion = st.radio("🔍 ¿Requiere Investigación Formal?", ["No", "Si"], horizontal=True)
                with c_h2:
                    foto_hse = st.file_uploader("📸 Evidencia Fotográfica:", type=['jpg', 'jpeg', 'png'])

                if st.form_submit_button("🚀 Entrar Alerta Oficial al Sistema", use_container_width=True, type="primary"):
                    if tipo_ev == "-- Seleccione --" or riesgo == "-- Seleccione --":
                        st.error("Por favor completa los campos obligatorios (Tipo y Riesgo).")
                    elif not que_paso or not porque_paso:
                        st.warning("Debe describir qué y por qué ocurrió el evento.")
                    elif foto_hse and not validar_archivo_seguro(foto_hse)[0]:
                        st.error("🛑 El archivo de imagen no es válido o está corrupto.")
                    else:
                        # Guardar Foto
                        foto_final = None
                        if foto_hse:
                            ruta_ev = get_scoped_path(empresa_nom, contrato_nom, "HSE/Incidentes")
                            nombre_fn = f"INCIDENTE_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                            foto_final = os.path.join(ruta_ev, nombre_fn)
                            with open(foto_final, "wb") as f:
                                f.write(foto_hse.getbuffer())

                        # Empaquetar acciones
                        acciones = [a for a in [acc1, acc2, acc3] if a]
                        acciones_json = json.dumps(acciones)

                        # Guardar en Base de Datos de manera segura
                        query_ins = """
                            INSERT INTO reportes_incidentes 
                            (folio, fecha, hora, tipo_evento, riesgo_critico, control_fallido, que_ocurrio, porque_ocurrio, 
                             acciones_json, foto_path, clasificacion_alerta, requiere_investigacion, reportante, afectado, empresa_id, contrato_id)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """
                        params_ins = (
                            folio, str(fecha), str(hora), tipo_ev, riesgo, control, que_paso, porque_paso,
                            acciones_json, foto_final, clasificacion, investigacion, reportante, afectado, empresa_id, contrato_id
                        )
                        ejecutar_query(db_path, query_ins, params_ins, commit=True)
                        registrar_log(db_path, st.session_state.user_login, "INCIDENTE", f"Registrada alerta folio {folio} - Tipo: {tipo_ev}")

                        # Limpiar datos de IA después de guardar con éxito
                        if "inc_ai_data" in st.session_state:
                            del st.session_state["inc_ai_data"]

                        st.success("✅ Alerta de Incidente consolidada.")
                        st.rerun()

    with tab_historico:
        st.markdown("### 📂 Catastro Histórico de Incidentes")
        if df_inc.empty:
            st.warning("Catastro vacío.")
        else:
            # Vista rápida con opción de PDF
            st.dataframe(df_inc.sort_values('fecha', ascending=False), use_container_width=True, hide_index=True)

            st.divider()
            st.markdown("#### 📄 Generar Reportes Técnicos")
            sel_ev = st.selectbox("Seleccione un evento para descargar su Alerta de Incidente:",
                                  options=[f"{r['id']} - {r['fecha']} | {r['tipo_evento']} - {r['riesgo_critico']}" for _, r in df_inc.iterrows()])

            if sel_ev:
                ev_id = int(sel_ev.split(" - ")[0])
                row_sel = df_inc[df_inc['id'] == ev_id].iloc[0]

                from core.reports.generador_pdf import pdf_engine
                pdf_b = pdf_engine.generar('INCIDENTE', row_sel.to_dict(), LOGO_APP, obtener_logo_cliente(st.session_state.filtros.get('empresa_nom')))
                st.download_button(f"📥 Descargar Alerta de Incidente (ID: {ev_id})", pdf_b, f"Alerta_HSE_{ev_id}.pdf", "application/pdf", use_container_width=True)

            st.divider()
            c_exp1, c_exp2 = st.columns(2)
            with c_exp1:
                # Exportar Excel
                out = io.BytesIO()
                with pd.ExcelWriter(out, engine='xlsxwriter') as writer:
                    df_inc.to_excel(writer, index=False, sheet_name='HSE_Incidentes')
                st.download_button("📥 Descargar Catastro Completo (Excel)", out.getvalue(), "Catastro_HSE.xlsx", use_container_width=True)

            with c_exp2:
                # Libro de Aprendizaje
                from core.reports.generador_pdf import pdf_engine
                if st.button("📚 Generar Libro de Aprendizaje PDF", use_container_width=True):
                    pdf_libro = pdf_engine.generar('LIBRO_APRENDIZAJE', df_inc, LOGO_APP, obtener_logo_cliente(st.session_state.filtros.get('empresa_nom')))
                    st.download_button("⬇️ Descargar Libro Consolidado", pdf_libro, "Libro_Aprendizaje_HSE.pdf", "application/pdf", use_container_width=True)
                st.info("💡 Este reporte consolida todos los eventos en formato de 2 por página.")
