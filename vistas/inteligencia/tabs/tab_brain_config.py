import streamlit as st
import os
import json
from src.infrastructure.database import obtener_config, guardar_config
from intelligence.providers import (
    create_provider,
    get_available_providers,
    get_provider_models,
    ProviderConfig,
)

def render_tab_brain_config(db_path, filtros):
    st.markdown("""
        <div style='background: rgba(0, 210, 255, 0.1); padding: 20px; border-radius: 15px; border: 1px solid #00d2ff; margin-bottom: 25px;'>
            <h2 style='color: #00d2ff; margin-top: 0;'>🧠 Configuración del Cerebro Central</h2>
            <p>Aquí puedes conectar a Ull-Trone con múltiples modelos de lenguaje para potenciar su razonamiento estratégico.</p>
        </div>
    """, unsafe_allow_html=True)

    # Cargar config actual
    config_brain = obtener_config(db_path, "ULLTRONE_BRAIN_CONFIG", {
        "api_provider": "Google Gemini",
        "api_key": "",
        "model_name": "gemini-1.5-pro",
        "temperature": 0.7,
        "max_output_tokens": 4096,
        "top_p": 1.0
    })

    # Obtener proveedores disponibles
    available_providers = get_available_providers()
    provider_list = list(available_providers.keys())
    provider_display = list(available_providers.values())

    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("🔌 Conectores")

        # Selectbox de proveedor
        provider_index = 0
        if config_brain.get("api_provider") in provider_list:
            provider_index = provider_list.index(config_brain.get("api_provider"))

        selected_display = st.selectbox(
            "Proveedor de IA",
            provider_display,
            index=provider_index,
            help="Elige el proveedor de IA que deseas utilizar"
        )
        selected_provider = provider_list[provider_display.index(selected_display)]

        # API KEY input
        api_key = st.text_input(
            "API KEY",
            value=config_brain.get("api_key", ""),
            type="password",
            help="Tu llave privada para acceder al modelo. Para Ollama local, puedes dejar esto vacío."
        )

        # Cargar modelos disponibles
        available_models = get_provider_models(selected_provider)

        # Si Ollama, intentar cargar modelos dinámicamente
        if selected_provider == "Ollama" and api_key:
            try:
                temp_config = ProviderConfig(api_key=api_key, model_name="")
                from intelligence.providers import OllamaProvider
                ollama = OllamaProvider(temp_config)
                available_models = ollama.get_available_models()
            except:
                available_models = ["Carga Ollama primero..."]

        # Selectbox de modelo
        current_model = config_brain.get("model_name", "")
        model_index = 0
        if current_model in available_models:
            model_index = available_models.index(current_model)

        model = st.selectbox(
            "Modelo",
            available_models if available_models else ["Sin modelos disponibles"],
            index=min(model_index, len(available_models) - 1) if available_models else 0
        )

    with col2:
        st.subheader("⚙️ Parámetros de Razonamiento")
        temp = st.slider(
            "Temperatura (Creatividad)",
            0.0, 1.0,
            float(config_brain.get("temperature", 0.7)),
            0.05,
            help="Valores bajos = más determinístico, Valores altos = más creativo"
        )
        top_p = st.slider(
            "Top P (Diversidad)",
            0.0, 1.0,
            float(config_brain.get("top_p", 1.0)),
            0.05,
            help="Controla la diversidad de tokens considerados"
        )
        tokens = st.number_input(
            "Máx. Tokens de Salida",
            1024, 8192,
            int(config_brain.get("max_output_tokens", 4096)),
            512,
            help="Límite máximo de tokens en la respuesta"
        )

        st.info(
            "💡 **Consejo:** Usa temperatura baja (0.2-0.4) para código/análisis, "
            "alta (0.7-0.9) para brainstorming estratégico."
        )

    # Test conexión
    st.markdown("---")
    col_test, col_save = st.columns([1, 1])

    with col_test:
        if st.button("🧪 Probar Conexión", use_container_width=True):
            if not api_key and selected_provider != "Ollama":
                st.error("❌ Se requiere API KEY para este proveedor")
            else:
                try:
                    with st.spinner(f"Conectando a {selected_display}..."):
                        config = ProviderConfig(
                            api_key=api_key,
                            model_name=model,
                            temperature=temp,
                            max_tokens=tokens,
                            top_p=top_p
                        )
                        provider = create_provider(selected_provider, config)
                        is_valid = provider.validate_connection()

                        if is_valid:
                            st.success(f"✅ Conexión exitosa con {selected_display}")
                        else:
                            st.error(f"❌ No se pudo validar la conexión")
                except Exception as e:
                    st.error(f"❌ Error de conexión: {str(e)}")

    with col_save:
        if st.button("💾 Guardar Configuración", use_container_width=True, type="primary"):
            if not api_key and selected_provider != "Ollama":
                st.error("❌ Se requiere API KEY para este proveedor")
            elif not model:
                st.error("❌ Debe seleccionar un modelo")
            else:
                try:
                    new_config = {
                        "api_provider": selected_provider,
                        "api_key": api_key,
                        "model_name": model,
                        "temperature": temp,
                        "max_output_tokens": tokens,
                        "top_p": top_p
                    }
                    guardar_config(db_path, "ULLTRONE_BRAIN_CONFIG", new_config)
                    st.session_state['gemini_api_key'] = api_key
                    st.success(f"✅ Cerebro configurado con {selected_display}")
                    st.balloons()
                except Exception as e:
                    st.error(f"❌ Error al guardar: {str(e)}")

    # Estado de la conexión
    st.markdown("---")
    st.markdown("### 🛠️ Estado de la Configuración")

    col_status1, col_status2, col_status3, col_status4 = st.columns(4)

    with col_status1:
        status = "🟢" if api_key or selected_provider == "Ollama" else "🔴"
        st.metric("API KEY", "✓ Configurada" if (api_key or selected_provider == "Ollama") else "✗ Requerida")

    with col_status2:
        st.metric("Proveedor", selected_display.replace("💎 ", "").replace("🔴 ", "").replace("🤖 ", "").replace("🌊 ", "").replace("🦙 ", ""))

    with col_status3:
        st.metric("Modelo", model if model else "Sin seleccionar")

    with col_status4:
        temp_display = f"{temp:.2f}"
        st.metric("Temperatura", temp_display)
