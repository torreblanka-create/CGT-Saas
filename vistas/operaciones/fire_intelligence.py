import os
import json
import pandas as pd
import streamlit as st
from datetime import datetime
from src.infrastructure.database import ejecutar_query, obtener_dataframe
from src.infrastructure.archivos import obtener_ruta_entidad

def render_fire_intelligence(DB_PATH):
    filtros = st.session_state.get('filtros', {'empresa_id': 0, 'empresa_nom': None, 'contrato_id': 0, 'contrato_nom': None})
    categoria_seleccionada = "Sistemas de Emergencia" # Los mapas se asocian a esta categoría base
    
    st.markdown("""
        <div class='premium-header'>
            <div style='display: flex; align-items: center; gap: 20px;'>
                <div style='background: rgba(239, 68, 68, 0.1); padding: 15px; border-radius: 12px; border: 1px solid rgba(239, 68, 68, 0.2);'>
                    <span style='font-size: 2.5rem;'>🔥</span>
                </div>
                <div>
                    <h1 style='color: var(--text-heading); margin: 0; font-size: 1.8rem; font-family: "Outfit", sans-serif;'>Ingeniería & Inteligencia de Fuego</h1>
                    <p style='color: var(--text-muted); margin: 5px 0 0 0; font-size: 1rem; opacity: 0.9;'>Cálculo de carga combustible (NCh 1916) y gestión estratégica de planimetría de emergencia.</p>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    if not filtros.get('empresa_nom'):
        st.warning("⚠️ Por favor, seleccione una Empresa en el panel lateral para acceder a las herramientas de ingeniería de fuego.")
        return

    tab_carga_combustible, tab_mapas = st.tabs([
        "🔥 Cálculo Carga Combustible (NCh 1916)",
        "🗺️ Mapas de Emergencia y Planos"
    ])

    with tab_carga_combustible:
        st.markdown("#### 🔥 Estudio de Carga Combustible (NCh 1916 / OGUC)")
        st.write("Determine la densidad de carga combustible para clasificar el nivel de riesgo y la resistencia al fuego requerida.")
        
        with st.container(border=True):
            col_m1, col_m2 = st.columns([2, 1])
            with col_m1:
                sector_nombre = st.text_input("Nombre del Sector o Bodega", placeholder="Ej: Bodega Sustancias Peligrosas")
                area_estudio = st.number_input("Superficie del Sector (m²)", min_value=1.0, value=10.0)
            
            # Diccionario de Poderes Caloríficos (MJ/kg) - Valores referenciales NCh 1916
            materiales_mj = {
                "Madera (Promedio)": 18.4,
                "Papel / Cartón": 17.5,
                "Plástico (PVC)": 18.8,
                "Plástico (PE/PP/PS)": 44.0,
                "Goma / Caucho": 31.4,
                "Algodón / Textiles": 16.7,
                "Líquidos Inflamables (Petróleo/Gasoil)": 44.8,
                "Líquidos Inflamables (Alcoholes)": 28.0,
                "Mobiliario de Oficina (Carga Mixta)": 18.0,
                "Otro (Ingreso Manual)": 1.0
            }
            
            if "fire_calc_list" not in st.session_state:
                st.session_state.fire_calc_list = []
            
            with st.form("form_material_fire"):
                c_mat1, c_mat2, c_mat3 = st.columns([2, 1, 1])
                with c_mat1: mat_sel = st.selectbox("Material / Sustancia", list(materiales_mj.keys()))
                with c_mat2: peso_mat = st.number_input("Masa (Kg)", min_value=0.1, value=10.0)
                with c_mat3: 
                    p_cal = materiales_mj[mat_sel]
                    if mat_sel == "Otro (Ingreso Manual)":
                        p_cal = st.number_input("MJ/Kg", min_value=0.1, value=1.0)
                    
                    add_mat = st.form_submit_button("➕ Añadir Item", use_container_width=True)
                    if add_mat:
                        st.session_state.fire_calc_list.append({
                            "material": mat_sel,
                            "peso": peso_mat,
                            "mj_kg": p_cal,
                            "total_mj": round(peso_mat * p_cal, 2)
                        })
            
            if st.session_state.fire_calc_list:
                df_mat = pd.DataFrame(st.session_state.fire_calc_list)
                st.dataframe(df_mat, use_container_width=True, hide_index=True)
                
                total_mj_sector = df_mat['total_mj'].sum()
                densidad_mj_m2 = round(total_mj_sector / area_estudio, 2)
                
                # Clasificación OGUC Art. 4.3.4
                if densidad_mj_m2 <= 500: clasif = "Categoría 5 (Baja)"
                elif densidad_mj_m2 <= 1000: clasif = "Categoría 4 (Media)"
                elif densidad_mj_m2 <= 2000: clasif = "Categoría 3 (Alta)"
                elif densidad_mj_m2 <= 4000: clasif = "Categoría 2 (Muy Alta)"
                else: clasif = "Categoría 1 (Extrema)"
                
                c_res1, c_res2, c_res3 = st.columns(3)
                c_res1.metric("Carga Total", f"{total_mj_sector:.1f} MJ")
                c_res2.metric("Densidad Media", f"{densidad_mj_m2} MJ/m²")
                c_res3.metric("Clasificación OGUC", clasif)
                
                if st.button("💾 Guardar Estudio en Historial", use_container_width=True, type="primary"):
                    if not sector_nombre:
                        st.error("Debe ingresar un nombre para el sector.")
                    else:
                        datos_json = json.dumps(st.session_state.fire_calc_list)
                        ejecutar_query(DB_PATH, """
                            INSERT INTO estudios_carga_combustible 
                            (fecha, area_sector, superficie_m2, carga_mj_m2, clasificacion_oguc, datos_json, empresa_id, contrato_id) 
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, (str(datetime.now().date()), sector_nombre, area_estudio, densidad_mj_m2, clasif, datos_json, filtros.get('empresa_id', 0), filtros.get('contrato_id', 0)), commit=True)
                        st.success("✅ Estudio guardado y registrado exitosamente.")
                        st.session_state.fire_calc_list = []
                        st.rerun()
                
                if st.button("🗑️ Limpiar Calculadora", use_container_width=True):
                    st.session_state.fire_calc_list = []
                    st.rerun()
            else:
                st.info("Añada materiales para comenzar el cálculo de carga combustible.")

        st.markdown("---")
        st.markdown("### 📜 Historial de Estudios Realizados")
        df_historial = obtener_dataframe(DB_PATH, "SELECT id, fecha, area_sector, superficie_m2, carga_mj_m2, clasificacion_oguc FROM estudios_carga_combustible WHERE empresa_id = ?", (filtros.get('empresa_id', 0),))
        if not df_historial.empty:
            st.dataframe(df_historial, use_container_width=True, hide_index=True)
        else:
            st.caption("No se registran estudios previos para esta empresa.")

    with tab_mapas:
        st.markdown("#### 🗺️ Mapas de Emergencia y Planimetría")
        st.write("Gestione planos de evacuación, ubicación de extintores y redes húmedas.")
        
        with st.expander("🖼️ Cargar Nuevo Mapa / Plano", expanded=False):
            map_nom = st.text_input("Nombre del Plano (Ej: Planta Piso 1)")
            map_tipo = st.selectbox("Tipo de Mapa", ["Evacuación", "Red Incendio", "Zonas de Riesgo", "General"])
            map_file = st.file_uploader("Subir Imagen del Plano (JPG/PNG)", type=['jpg', 'png', 'jpeg'])
            
            if st.button("💾 Registrar Mapa", use_container_width=True, type="primary"):
                if map_nom and map_file:
                    # Usamos una ruta genérica para la empresa
                    ruta_base = os.path.join("CGT_DATA", filtros['empresa_nom'], "Fire_Intelligence")
                    os.makedirs(ruta_base, exist_ok=True)
                    
                    ext = os.path.splitext(map_file.name)[1]
                    filename = f"MAP_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"
                    path = os.path.join(ruta_base, filename).replace("\\", "/")
                    
                    with open(path, "wb") as f:
                        f.write(map_file.getbuffer())
                        
                    ejecutar_query(DB_PATH, """
                        INSERT INTO mapas_emergencia (fecha, nombre, tipo, imagen_path, empresa_id, contrato_id) 
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (str(datetime.now().date()), map_nom, map_tipo, path, filtros.get('empresa_id', 0), filtros.get('contrato_id', 0)), commit=True)
                    st.success(f"✅ Mapa '{map_nom}' guardado correctamente.")
                    st.rerun()
                else:
                    st.warning("Complete el nombre y adjunte un archivo.")

        st.divider()
        # Listado de mapas existentes
        df_mapas = obtener_dataframe(DB_PATH, "SELECT id, fecha, nombre, tipo, imagen_path FROM mapas_emergencia WHERE empresa_id = ?", (filtros.get('empresa_id', 0),))
        
        if not df_mapas.empty:
            for idx, row in df_mapas.iterrows():
                with st.container(border=True):
                    cm1, cm2 = st.columns([3, 1])
                    with cm1:
                        st.markdown(f"**{row['nombre']}** ({row['tipo']})")
                        st.caption(f"Registrado el: {row['fecha']}")
                    with cm2:
                        if st.button("🗑️", key=f"del_map_fire_{row['id']}"):
                            ejecutar_query(DB_PATH, "DELETE FROM mapas_emergencia WHERE id = ?", (row['id'],), commit=True)
                            if os.path.exists(row['imagen_path']):
                                try: os.remove(row['imagen_path'])
                                except: pass
                            st.rerun()
                    
                    if os.path.exists(row['imagen_path']):
                        st.image(row['imagen_path'], use_container_width=True)
        else:
            st.info("No hay mapas de emergencia registrados aún.")
