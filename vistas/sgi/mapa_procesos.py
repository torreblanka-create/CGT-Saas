import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from src.infrastructure.database import obtener_dataframe
from core.utils import is_valid_context, show_context_warning

def _get_documentos_proceso(db_path, empresa_id, ambito):
    """Obtiene los documentos de un proceso específico."""
    try:
        df = obtener_dataframe(db_path, "SELECT titulo, codigo FROM procedimientos WHERE empresa_id=? AND ambito=?", (empresa_id, ambito))
        return df
    except:
        return pd.DataFrame()

def render_mapa_procesos(DB_PATH, filtros):
    # --- UI ELITE NEON ONYX ---
    st.markdown("""
        <div style='background: #F5F3F0; 
                    padding: 25px; border-radius: 15px; border-left: 5px solid #8b5cf6; 
                    margin-bottom: 25px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);'>
            <div style='display: flex; align-items: center; gap: 15px;'>
                <div style='background: rgba(139,92,246,0.15); padding: 10px; border-radius: 10px;'>
                    <span style='font-size: 2rem;'>🗺️</span>
                </div>
                <div>
                    <h2 style='color: #7c3aed; margin:0; font-family:Outfit, sans-serif;'>
                        Mapa de Procesos & Arquitectura SGI
                    </h2>
                    <p style='color: #94A3B8; margin:5px 0 0 0; font-size: 0.95rem;'>
                        Visualización dinámica de la cadena de valor y repositorio documental normativo.
                    </p>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    if not is_valid_context(filtros):
        show_context_warning()
        return

    emp_id = filtros.get('empresa_id')

    # Estilos CSS de las cajas para el Mapa de Procesos
    st.markdown("""
    <style>
    .proc-box {
        background-color: var(--background-color, #ffffff);
        border: 2px solid;
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 20px;
        text-align: center;
        font-weight: 600;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        transition: transform 0.2s;
    }
    .proc-box:hover { transform: scale(1.02); }
    .proc-estrategico { border-color: #3b82f6; border-top-width: 6px; }
    .proc-operativo { border-color: #10b981; border-top-width: 6px; }
    .proc-soporte { border-color: #8b5cf6; border-top-width: 6px; }
    .proc-mejora { border-color: #f59e0b; border-top-width: 6px; }
    .proc-cliente { background-color: #f8fafc; border: 2px dashed #94a3b8; padding: 50px 10px; color: #475569; writing-mode: vertical-rl; transform: rotate(180deg); height: 100%; border-radius: 8px;}
    </style>
    """, unsafe_allow_html=True)

    tab_mapa, tab_interaccion = st.tabs(["🧩 Mapa Visual y Documentación", "🕸️ Matriz de Interacción (Sankey)"])

    with tab_mapa:
        st.markdown("### Arquitectura de Procesos de la Organización")
        
        # Grid layout (Cliente In -> Procesos -> Cliente Out)
        col_in, col_core, col_out = st.columns([1, 8, 1])
        
        with col_in:
            st.markdown("<div class='proc-cliente'>REQUISITOS DEL CLIENTE Y PARTES INTERESADAS</div>", unsafe_allow_html=True)
            
        with col_core:
            # Estratégicos
            st.markdown("<div class='proc-box proc-estrategico'>PROCESOS ESTRATÉGICOS<br><span style='font-weight:400; font-size:0.9em; color:gray;'>Planificación SGI • Revisión por la Dirección • Gestión de Riesgos Corporativos</span></div>", unsafe_allow_html=True)
            
            # Operativos / Cadena de Valor (Side by side)
            c_op1, c_op2, c_op3 = st.columns(3)
            with c_op1: st.markdown("<div class='proc-box proc-operativo'>Ventas & Licitaciones</div>", unsafe_allow_html=True)
            with c_op2: st.markdown("<div class='proc-box proc-operativo'>Planificación y Diseño HSE</div>", unsafe_allow_html=True)
            with c_op3: st.markdown("<div class='proc-box proc-operativo'>Ejecución de Servicios / Operaciones Terreno</div>", unsafe_allow_html=True)
            
            # Soporte
            st.markdown("<div class='proc-box proc-soporte'>PROCESOS DE SOPORTE<br><span style='font-weight:400; font-size:0.9em; color:gray;'>Recursos Humanos • Mantenimiento de Activos • Adquisiciones • SSOMAC</span></div>", unsafe_allow_html=True)
            
            # Mejora
            st.markdown("<div class='proc-box proc-mejora'>MEJORA CONTINUA<br><span style='font-weight:400; font-size:0.9em; color:gray;'>Auditorías Internas • Gestión de Hallazgos (NCR) • Acciones Correctivas</span></div>", unsafe_allow_html=True)
            
        with col_out:
            st.markdown("<div class='proc-cliente' style='transform: none; writing-mode: vertical-rl;'>SATISFACCIÓN DEL CLIENTE Y ENTREGA DE VALOR</div>", unsafe_allow_html=True)

        st.divider()
        st.markdown("#### 📂 Repositorio Dinámico de Procesos")
        st.caption("Documentación vinculada directamente desde la base de datos SGI.")
        
        ambitos = ["Estratégico", "Operativo", "Soporte", "Mejora Continua"]
        c_r1, c_r2 = st.columns(2)
        
        for i, amb in enumerate(ambitos):
            target_col = c_r1 if i % 2 == 0 else c_r2
            with target_col:
                with st.expander(f"Ver Documentos: {amb}", expanded=False):
                    df_docs = _get_documentos_proceso(DB_PATH, emp_id, amb)
                    if df_docs.empty:
                        st.caption("Sin documentos vinculados actualmente.")
                    else:
                        for _, doc in df_docs.iterrows():
                            st.markdown(f"📄 **{doc['codigo']}** - {doc['titulo']}")

    with tab_interaccion:
       st.markdown("### Flujo de Entradas y Salidas de la Organización")
       fig = go.Figure(data=[go.Sankey(
           node = dict(
               pad = 25, thickness = 20, line = dict(color = "black", width = 0.5),
               label = ["Requisitos Cliente (Entrada)", "Liderazgo y Planificación", "Cadena de Valor (Operación)", "Soporte y Recursos", "Evaluación de Desempeño y Mejora", "Satisfacción Cliente (Salida)", "Partes Interesadas (Legal)"],
               color = ["#94a3b8", "#3b82f6", "#10b981", "#8b5cf6", "#f59e0b", "#94a3b8", "#ef4444"]
           ),
           link = dict(
               source = [0, 6, 1, 3, 2, 2, 4, 1, 4, 2],
               target = [2, 1, 2, 2, 5, 4, 1, 4, 3, 1],
               value =  [5, 2, 2, 3, 5, 2, 2, 1, 1, 1],
               color = ["rgba(148,163,184,0.3)"] * 10
           )
       )])
       fig.update_layout(height=450, font_size=13, margin=dict(t=30, b=10, l=10, r=10), paper_bgcolor="rgba(0,0,0,0)")
       st.plotly_chart(fig, use_container_width=True)
