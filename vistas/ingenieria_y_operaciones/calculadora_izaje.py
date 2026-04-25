import base64
import json
import math
import os
from datetime import datetime

import pandas as pd
import streamlit as st

from config.config import BASE_DATA_DIR, LOGO_APP, LOGO_CLIENTE, obtener_logo_cliente
from src.infrastructure.database import ejecutar_query, obtener_dataframe
from core.reports.generador_pdf import pdf_engine
from core.visuals_izaje import draw_lmi_chart, draw_rigging_diagram

# --- CONSTANTES DE INGENIERÍA RIGGER 360 ---
FACTORES_ANGULO = {90: 1.0, 60: 1.2, 50: 1.305, 45: 1.414, 30: 2.0}
FACTORES_MODO = {"Axial (1.0)": 1.0, "Lazo (0.8)": 0.8, "Cesto/U (2.0)": 2.0}
FACTORES_MATERIAL = {"Eslinga Sintética (SF 7:1)": 7.0, "Estrobo Acero (SF 5:1)": 5.0, "Cadena Aleación (SF 4:1)": 4.0}
FACTORES_VELA = {"Normal": 1.0, "Media (Cajas)": 1.5, "Alta (Paneles)": 2.5}
FV = {"Normal": 1.0, "Media": 1.5, "Alta": 2.5}

class MotorIngenieriaIzaje:
    """Clase para desacoplar la lógica matemática de la UI."""
    @staticmethod
    def calcular_maniobra(config_global, cfg_equipo):
        if not cfg_equipo: return None

        viento = config_global.get('viento', 0)
        vela = config_global.get('vela', "Normal")
        p_neto_total = config_global.get('p_neto', 0)
        es_tandem = config_global.get('es_tandem', False)

        f_tandem = 1.25 if es_tandem else 1.0
        neta_prop = p_neto_total * (cfg_equipo['dist_p'] / 100)
        bruta = neta_prop + cfg_equipo['rigging']

        red_viento = ((viento - 15) * FV.get(vela, 1.0)) * (cfg_equipo['capacidad'] * 0.01) if viento > 15 else 0
        cap_efectiva = cfg_equipo['capacidad'] - red_viento
        utilizacion = (bruta * f_tandem / cap_efectiva * 100) if cap_efectiva > 0 else 999

        fm = FACTORES_MODO.get(cfg_equipo['tipo_amarre'], 1.0)
        fa = FACTORES_ANGULO.get(cfg_equipo['angulo'], 1.0)
        sf = FACTORES_MATERIAL.get(cfg_equipo.get('material', "Eslinga Sintética (SF 7:1)"), 7.0)
        ram_seguros = min(cfg_equipo['ramales'], 3)
        cap_sistema = (cfg_equipo['wll_base'] * fm) * ram_seguros
        ruptura_estimada = cfg_equipo['wll_base'] * sf

        if config_global.get('cg_asim') and not es_tandem:
            d1, d2 = config_global.get('d1', 1.0), config_global.get('d2', 1.0)
            t_max_base = max(bruta * (d2 / (d1 + d2)), bruta * (d1 / (d1 + d2)))
            tension_ramal = t_max_base * fa
        else:
            tension_ramal = (bruta * fa) / ram_seguros

        util_rigging = (tension_ramal * ram_seguros / cap_sistema * 100) if cap_sistema > 0 else 999

        return {
            **cfg_equipo, "bruta": bruta, "cap_efectiva": cap_efectiva,
            "utilizacion": utilizacion, "util_rigging": util_rigging, "tension": tension_ramal,
            "cap_real_wll": cap_sistema / ram_seguros, "red_viento": red_viento,
            "factor_angulo": fa, "factor_tandem": f_tandem, "ruptura_estimada": ruptura_estimada
        }

def render_calculadora_izaje(db_path, filtros):
    # --- HEADER PREMIUM - RIGGER 360 ---
    st.markdown("""
        <div class='premium-header'>
            <div style='display: flex; align-items: center; gap: 15px;'>
                <div style='background: linear-gradient(135deg, #3b82f6, #2563eb); padding: 12px; border-radius: 12px; box-shadow: 0 4px 15px rgba(59, 130, 246, 0.3);'>
                    <span style='font-size: 24px;'>🏗️</span>
                </div>
                <div>
                    <h1 style='margin: 0; color: #1F2937; font-size: 1.8rem;'>Rigger 360° | Ingeniería de Izaje</h1>
                    <p style='margin: 0; color: #64748b; font-size: 0.9rem;'>Cálculos Técnicos Bajo Norma ASME B30.9 / B30.5</p>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    is_master = st.session_state.role == "Global Admin"
    df_specs = obtener_dataframe(db_path, "SELECT * FROM especificaciones_equipos WHERE (empresa_id = ? OR empresa_id = 0 OR empresa_id IS NULL)", (st.session_state.empresa_id,))
    lista_ids = ["Manual"] + (df_specs['identificador'].tolist() if not df_specs.empty else [])
    
    # Obtener inventario de Elementos de Izaje del cliente
    df_eslingas = obtener_dataframe(db_path, "SELECT DISTINCT identificador, nombre FROM registros WHERE categoria='Elementos de izaje' AND (empresa_id=? OR empresa_id=0 OR empresa_id IS NULL)", (st.session_state.empresa_id,))
    lista_eslingas = ["Ingreso Manual"] + (df_eslingas['identificador'] + " - " + df_eslingas['nombre']).tolist() if not df_eslingas.empty else ["Ingreso Manual"]

    # Obtener inventario de Vehículos (Camiones / Equipos Pesados)
    df_gruas = obtener_dataframe(db_path, "SELECT DISTINCT identificador, nombre FROM registros WHERE categoria IN ('Camion_Transporte', 'Equipo_Pesado') AND (empresa_id=? OR empresa_id=0 OR empresa_id IS NULL)", (st.session_state.empresa_id,))
    lista_gruas_fisicas = ["Vehículo No Enrolado"] + (df_gruas['identificador'] + " - " + df_gruas['nombre']).tolist() if not df_gruas.empty else ["Vehículo No Enrolado"]

    if 'clone_data' not in st.session_state: st.session_state.clone_data = {}
    cd = st.session_state.clone_data

    tab_calc, tab_hist = st.tabs(["⚡ NUEVA MANIOBRA", "📋 SISTEMA DE REGISTROS"])

    with tab_calc:
        with st.expander("📦 DATOS DE LA CARGA", expanded=True):
            c1, c2 = st.columns(2)
            desc = c1.text_input("Trabajo / Descripción", cd.get("descripcion", "Izaje Estándar"))
            client = c2.text_input("Empresa Solicitante", cd.get("empresa", st.session_state.filtros.get('empresa_nom', "CGT")))

            p_neto = st.number_input("Peso Neto de la Carga (Kg)", 1.0, 500000.0, float(cd.get("p_neto_total", 1000.0)), step=100.0)
            viento = st.slider("Velocidad del Viento (Km/h)", 0, 60, int(cd.get("viento", 15)))
            vela = st.selectbox("Área de Vela", list(FV.keys()), index=list(FV.keys()).index(cd.get("tipo_carga", "Normal")) if cd.get("tipo_carga") in FV else 0)

            c_opts1, c_opts2 = st.columns(2)
            cg_asim = c_opts1.checkbox("CG Asimétrico", value=cd.get("cg_asim", False))
            es_tandem = c_opts2.checkbox("Maniobra Tándem (2 Grúas)", value=cd.get("es_tandem", False))

            d1, d2 = 1.0, 1.0
            if cg_asim:
                ca1, ca2 = st.columns(2)
                d1 = ca1.number_input("Distancia D1 (m)", 0.1, 100.0, float(cd.get("d1", 2.0)))
                d2 = ca2.number_input("Distancia D2 (m)", 0.1, 100.0, float(cd.get("d2", 1.0)))

            dist_a = st.number_input("% Carga Grúa A", 10.0, 90.0, float(cd.get("grua_a",{}).get("dist_p", 50.0)) if es_tandem else 50.0) if es_tandem else 100.0

        def gui_setup_equipo(label, key, pct):
            st.markdown(f"#### {label} ({pct}%)")
            ed = cd.get(f"grua_{key}", {})

            with st.container(border=True):
                st.markdown("**✅ Checklist Pre-Uso (ASME)**")
                ck1 = st.checkbox(f"Accesorios certificados y sin daños ({key})", key=f"ck1_{key}")
                ck2 = st.checkbox(f"Gancho con seguro y operativo ({key})", key=f"ck2_{key}")

                c_top1, c_top2 = st.columns([2, 3])
                curr_id = ed.get("id", "Manual")
                idx_sel = lista_ids.index(curr_id) if curr_id in lista_ids else 0
                
                curr_fisica = ed.get("id_fisico", "Vehículo No Enrolado")
                idx_fisica = lista_gruas_fisicas.index(curr_fisica) if curr_fisica in lista_gruas_fisicas else 0
                
                st.markdown("**Identificación del Equipo**")
                c_maq1, c_maq2 = st.columns(2)
                id_eq = c_maq1.selectbox("Modelo / Tabla LMI", lista_ids, key=f"id_{key}", index=idx_sel)
                id_fisico = c_maq2.selectbox("Máquina Física (Patente/Código)", lista_gruas_fisicas, key=f"id_fis_{key}", index=idx_fisica)
                
                up_fotos = st.file_uploader("Fotos Evidencia", type=['png','jpg'], key=f"u_{key}", accept_multiple_files=True)

                p_gancho, cap_tab = 50.0, 5000.0
                if id_eq != "Manual" and not df_specs.empty:
                    m = df_specs[df_specs['identificador'] == id_eq].iloc[0]
                    p_gancho, cap_tab = float(m['peso_gancho_kg']), float(m['capacidad_max_ton'])*1000

                c_b1, c_b2, c_b3 = st.columns(3)
                rig = c_b1.number_input("Aparejos (Kg)", 0.0, 50000.0, float(ed.get("rigging", p_gancho)), key=f"r_{key}")
                rad = c_b2.number_input("Radio (m)", 1.0, 150.0, float(ed.get("radio", 5.0)), key=f"rad_{key}")

                cap_sugerida = float(ed.get("capacidad", cap_tab))
                is_disabled = False
                radios_lmi = []
                caps_lmi = []
                if id_eq != "Manual":
                    df_t = obtener_dataframe(db_path, "SELECT radio_m, capacidad_kg FROM tablas_carga_equipos WHERE identificador=? ORDER BY radio_m", (id_eq,))
                    if not df_t.empty:
                        df_t['radio_m'] = pd.to_numeric(df_t['radio_m'], errors='coerce')
                        df_t['capacidad_kg'] = pd.to_numeric(df_t['capacidad_kg'], errors='coerce')
                        df_t = df_t.sort_values(by='radio_m')

                        radios_lmi = df_t['radio_m'].tolist()
                        caps_lmi = df_t['capacidad_kg'].tolist()

                        df_t_filter = df_t[df_t['radio_m'] >= rad]
                        if not df_t_filter.empty:
                            cap_sugerida = float(df_t_filter.iloc[0]["capacidad_kg"])
                            is_disabled = True
                            # Force Streamlit to update the widget cache since it's disabled.
                            st.session_state[f"ct_{key}"] = cap_sugerida

                ct = c_b3.number_input("Cap. Tabla (Kg)", 0.0, 1000000.0, cap_sugerida, disabled=is_disabled, key=f"ct_{key}")

                st.markdown("**Configuración Aparejos (Rigging)**")
                sel_eslinga = st.selectbox("Seleccionar Elemento del Pañol (Inventario CGT):", lista_eslingas, key=f"sel_esl_{key}", index=0)
                if sel_eslinga != "Ingreso Manual":
                    st.info(f"✅ Elemento Vinculado: {sel_eslinga}")

                c_r1, c_r2, c_r3, c_r4, c_r5 = st.columns(5)
                mat = c_r1.selectbox("Material", list(FACTORES_MATERIAL.keys()), key=f"mat_{key}")
                mod = c_r2.selectbox("Modo", list(FACTORES_MODO.keys()), key=f"m_{key}", index=list(FACTORES_MODO.keys()).index(ed.get("tipo_amarre", "Axial (1.0)")) if ed.get("tipo_amarre") in FACTORES_MODO else 0)
                wll = c_r3.number_input("WLL (Kg)", 100, 100000, int(ed.get("wll_base", 2000)), key=f"w_{key}", help="Carga Límite de Trabajo")
                ram = c_r4.selectbox("Ramales", [1,2,3,4], index=[1,2,3,4].index(ed.get("ramales", 2)) if ed.get("ramales") in [1,2,3,4] else 1, key=f"rm_{key}")
                ang = c_r5.selectbox("Ángulo (°)", [90,60,50,45,30], index=[90,60,50,45,30].index(ed.get("angulo", 60)) if ed.get("angulo") in [90,60,50,45,30] else 1, key=f"an_{key}")

                return {
                    "id": id_eq, "id_fisico": id_fisico, "rigging": rig, "radio": rad, "capacidad": ct, "elemento_pañol": sel_eslinga,
                    "material": mat, "tipo_amarre": mod, "wll_base": wll, "ramales": ram, "angulo": ang,
                    "dist_p": pct, "is_ok": ck1 and ck2,
                    "lmi_radios": radios_lmi, "lmi_caps": caps_lmi
                }

        cfg_global = {"p_neto": p_neto, "viento": viento, "vela": vela, "es_tandem": es_tandem, "cg_asim": cg_asim, "d1": d1, "d2": d2}
        cfg_a = gui_setup_equipo("UNIDAD A", "a", dist_a)
        cfg_b = gui_setup_equipo("UNIDAD B", "b", 100.0 - dist_a) if es_tandem else None

        if not cfg_a['is_ok'] or (cfg_b and not cfg_b['is_ok']):
            st.warning("⚠️ Validación Requerida: Confirme el Checklist de seguridad para habilitar el cálculo.")
        else:
            res_a = MotorIngenieriaIzaje.calcular_maniobra(cfg_global, cfg_a)
            res_b = MotorIngenieriaIzaje.calcular_maniobra(cfg_global, cfg_b) if cfg_b else None

            st.markdown("---")
            m_ue = max(res_a['utilizacion'], res_b['utilizacion'] if res_b else 0)
            m_ur = max(res_a['util_rigging'], res_b['util_rigging'] if res_b else 0)

            # --- RESULTADOS PREMIUM ---
            c_r1, c_r2 = st.columns(2)
            
            with c_r1:
                color_ue = '#ef4444' if m_ue > 80 else '#10b981'
                st.markdown(f"""
                    <div class='metric-card-cgt' style='border-top: 4px solid {color_ue};'>
                        <p class='metric-label-cgt'>Utilización del Equipo</p>
                        <p class='metric-value-cgt' style='color: {color_ue};'>{m_ue:.1f}%</p>
                        <div style='background: #e2e8f0; border-radius: 4px; height: 8px; margin-top: 10px;'>
                            <div style='background: {color_ue}; width: {min(m_ue, 100)}%; height: 100%; border-radius: 4px;'></div>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
                
            with c_r2:
                color_ur = '#ef4444' if m_ur > 80 else '#10b981'
                st.markdown(f"""
                    <div class='metric-card-cgt' style='border-top: 4px solid {color_ur};'>
                        <p class='metric-label-cgt'>Estrés del Aparejo</p>
                        <p class='metric-value-cgt' style='color: {color_ur};'>{m_ur:.1f}%</p>
                        <div style='background: #e2e8f0; border-radius: 4px; height: 8px; margin-top: 10px;'>
                            <div style='background: {color_ur}; width: {min(m_ur, 100)}%; height: 100%; border-radius: 4px;'></div>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
                if 'ruptura_estimada' in res_a:
                    st.caption(f"ℹ️ Tensión Ramal: {res_a['tension']:.1f} Kg | Límite Ruptura Est: {res_a['ruptura_estimada']:.1f} Kg")

            status_label, status_class = "OPERACIÓN SEGURA ✅", "status-safe"
            if m_ue > 100 or m_ur > 100 or viento >= 30: status_label, status_class = "IZAJE NO AUTORIZADO (NO-GO) ❌", "status-danger"
            elif m_ue > 75 or m_ur > 75: status_label, status_class = "IZAJE CRÍTICO (REFIERA A SUPERVISIÓN) ⚠️", "status-warning"
            st.markdown(f'<div class="status-badge {status_class}">{status_label}</div>', unsafe_allow_html=True)

            # Gráficos Visuales
            try:
                c_img1, c_img2 = st.columns(2)
                img_diag = draw_rigging_diagram(d1, d2, angulo=res_a['angulo'], asimetrico=cg_asim, tandem=es_tandem)
                c_img1.image(img_diag, caption="Esquema Teórico de la Maniobra", use_container_width=True)

                if res_a.get('lmi_radios'):
                    lmi_diag = draw_lmi_chart(res_a['lmi_radios'], res_a['lmi_caps'], res_a['radio'], res_a['bruta'])
                    if lmi_diag: c_img2.image(lmi_diag, caption="Curva LMI Grúa", use_container_width=True)
            except Exception as e: st.caption(f"Diagrama no disponible: {e}")

            obj_final = {**cfg_global, "p_neto_total": p_neto, "descripcion": desc, "empresa": client, "tipo_carga": vela, "grua_a": res_a, "grua_b": res_b, "es_critico": (m_ue > 75 or m_ur > 75)}

            ca1, ca2 = st.columns(2)
            try:
                p_bytes = pdf_engine.generar('RIGGING_PLAN', obj_final, LOGO_APP, obtener_logo_cliente(client))
                ca1.download_button("📥 DESCARGAR RIGGING PLAN (PDF)", p_bytes, f"RP_{desc}.pdf", use_container_width=True)
            except Exception as e: ca1.error(f"Error PDF: {e}")

            if ca2.button("💾 GUARDAR EN REGISTRO", use_container_width=True):
                ejecutar_query(db_path, "INSERT INTO historial_rigging_plans (descripcion, responsable, datos_json, empresa_id, contrato_id) VALUES (?,?,?,?,?)",
                             (desc, st.session_state.username, json.dumps(obj_final), filtros.get('empresa_id', 0), filtros.get('contrato_id', 0)), commit=True)
                st.success("Guardado exitosamente.")
                st.rerun()

    with tab_hist:
        st.markdown("### 📋 Archivo Histórico")
        query_h = "SELECT id, fecha, descripcion, responsable, datos_json FROM historial_rigging_plans ORDER BY id DESC LIMIT 20"
        df_hist = obtener_dataframe(db_path, query_h)
        if df_hist.empty: st.info("No hay registros previos.")
        else:
            for _, r in df_hist.iterrows():
                with st.expander(f"📦 #{r['id']} | {r['descripcion']} | {r['responsable']}"):
                    d_js = json.loads(r['datos_json'])
                    col_h1, col_h2 = st.columns(2)
                    if col_h1.button("🔄 Cargar Configuración", key=f"cl_{r['id']}"):
                        st.session_state.clone_data = d_js
                        st.rerun()
                    if col_h2.button("🗑️ Eliminar", key=f"dl_{r['id']}"):
                        ejecutar_query(db_path, "DELETE FROM historial_rigging_plans WHERE id = ?", (r['id'],), commit=True)
                        st.rerun()
