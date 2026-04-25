import os
import streamlit as st
from config.config import DOCUMENTOS_SOPORTE


def render_material_soporte(SUPPORT_DIR):
    st.markdown("<h2 style='color: var(--cgt-blue);'>📚 Centro de Soporte y Documentación</h2>", unsafe_allow_html=True)
    st.write("Acceda a los manuales oficiales, políticas y guías técnicas de la plataforma.")
    st.divider()

    # Usar el listado centralizado en config.py
    for nombre, archivo in DOCUMENTOS_SOPORTE.items():
        ruta = os.path.join(SUPPORT_DIR, archivo)

        if os.path.exists(ruta):
            ext = os.path.splitext(archivo)[1].lower()
            
            with st.expander(f"📄 {nombre}", expanded=(ext == ".md")):
                if ext == ".md":
                    # Visualización DIRECTA para Markdown
                    with open(ruta, "r", encoding="utf-8") as f:
                        st.markdown(f.read())
                    st.divider()
                
                # Botón de Descarga Universal
                with open(ruta, "rb") as f:
                    st.download_button(
                        label=f"📥 Descargar {nombre} ({ext.replace('.','').upper()})",
                        data=f,
                        file_name=archivo,
                        mime="application/octet-stream",
                        use_container_width=True,
                        key=f"dl_{archivo}"
                    )
        else:
            st.error(f"Archivo no encontrado: {archivo}")
