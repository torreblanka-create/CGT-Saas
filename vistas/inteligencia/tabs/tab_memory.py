import streamlit as st
from intelligence.agents.memory_engine import get_all_projects_memory, get_project_details

def render_tab_memory(DB_PATH, filtros):
    st.markdown("""
        <div style='background: rgba(168, 85, 247, 0.1); padding: 20px; border-radius: 15px; border: 1px solid #a855f7; margin-bottom: 25px;'>
            <h2 style='color: #a855f7; margin-top: 0;'>📑 Memoria de Proyectos de Ull-Trone</h2>
            <p>Este es el repositorio de conocimiento de Ull-Trone. Aquí recuerda cada módulo diseñado y cada decisión estratégica tomada.</p>
        </div>
    """, unsafe_allow_html=True)

    history = get_all_projects_memory()

    if not history:
        st.info("🌑 La memoria de proyectos está vacía. Comienza a generar módulos en el Laboratorio para que Ull-Trone empiece a recordar.")
        return

    st.markdown("### 🏺 Línea de Tiempo de Desarrollo")
    
    for rid, fecha, nombre, desc, stack in history:
        with st.expander(f"📦 {nombre} ({fecha})"):
            col1, col2 = st.columns([2, 1])
            with col1:
                st.markdown(f"**Descripción:** {desc}")
                st.markdown(f"**Stack:** `{stack}`")
            with col2:
                if st.button("🔍 Ver Código Detallado", key=f"btn_mem_{rid}"):
                    full_data = get_project_details(rid)
                    st.code(full_data[5], language="python") # Código generado
            
            st.markdown("---")
            st.caption("Ull-Trone utiliza esta memoria para mantener consistencia en futuras iteraciones de CGT.pro.")

    if st.button("🧹 Purgar Memoria (Nivel Crítico)", use_container_width=True):
        st.warning("Esta acción borrará el conocimiento histórico de Ull-Trone. ¿Confirmar?")
        if st.button("Confirmar Borrado"):
            st.error("Funcionalidad de purga deshabilitada por Directiva de Resiliencia.")
