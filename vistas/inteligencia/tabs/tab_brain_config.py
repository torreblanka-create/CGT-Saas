import streamlit as st
import os
import json
from src.infrastructure.database import obtener_config, guardar_config

def render_tab_brain_config(db_path, filtros):
    st.markdown("""
        <div style='background: rgba(0, 210, 255, 0.1); padding: 20px; border-radius: 15px; border: 1px solid #00d2ff; margin-bottom: 25px;'>
            <h2 style='color: #00d2ff; margin-top: 0;'>🧠 Configuración del Cerebro Central</h2>
            <p>Aquí puedes conectar a Ull-Trone con modelos de lenguaje avanzados para potenciar su razonamiento estratégico.</p>
        </div>
    """, unsafe_allow_html=True)

    # Cargar config actual
    config_brain = obtener_config(db_path, "ULLTRONE_BRAIN_CONFIG", {
        "api_provider": "Google Gemini",
        "api_key": "",
        "model_name": "gemini-1.5-pro",
        "temperature": 0.7,
        "max_output_tokens": 4096
    })

    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("Conectores")
        provider = st.selectbox("Proveedor de IA", ["Google Gemini", "OpenAI (Próximamente)", "Anthropic (Próximamente)"], index=0)
        
        api_key = st.text_input("API KEY", value=config_brain.get("api_key", ""), type="password", help="Tu llave privada para acceder al modelo.")
        
        model = st.selectbox("Modelo", ["gemini-1.5-pro", "gemini-1.5-flash"], index=0 if config_brain.get("model_name") == "gemini-1.5-pro" else 1)

    with col2:
        st.subheader("Parámetros de Razonamiento")
        temp = st.slider("Temperatura (Creatividad)", 0.0, 1.0, float(config_brain.get("temperature", 0.7)), 0.1)
        tokens = st.number_input("Máx. Tokens de Salida", 1024, 8192, int(config_brain.get("max_output_tokens", 4096)), 512)
        
        st.info("💡 **Consejo:** Usa una temperatura baja (0.2 - 0.4) para generación de código y alta (0.7 - 0.9) para brainstorming estratégico.")

    if st.button("💾 Guardar Configuración de Inteligencia", use_container_width=True):
        new_config = {
            "api_provider": provider,
            "api_key": api_key,
            "model_name": model,
            "temperature": temp,
            "max_output_tokens": tokens
        }
        guardar_config(db_path, "ULLTRONE_BRAIN_CONFIG", new_config)
        st.session_state['gemini_api_key'] = api_key # Sincronización inmediata
        st.success("✅ ¡Cerebro configurado! Ull-Trone ahora tiene acceso a nuevas capacidades cognitivas.")
        st.balloons()

    st.markdown("---")
    st.markdown("### 🛠️ Estado de la Conexión")
    if api_key:
        st.write("🟢 **Conector Gemini:** Listo para inicializar")
    else:
        st.write("🔴 **Conector Gemini:** Requiere API KEY")
