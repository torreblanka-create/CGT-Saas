import streamlit as st

from src.infrastructure.database import ejecutar_query


def render_terminos_condiciones(db_path, user_login):
    st.markdown("<h2 style='text-align: center; color: var(--cgt-blue);'>🛡️ ACUERDO DE LICENCIA Y PRIVACIDAD CGT</h2>", unsafe_allow_html=True)
    st.divider()

    with st.container(height=450):
        st.markdown(f"""
        ### 1. PROPIEDAD INTELECTUAL Y AUTORÍA
        La plataforma **CGT (Control Gestión Total)** es una obra de software original desarrollada y de propiedad exclusiva de **Miguel Yonadab Rivera Cerda**. Todos los derechos, incluyendo código fuente, lógica de **Semáforo Doble** y bases de datos, pertenecen únicamente al autor.

        ### 2. LICENCIA DE USO Y ALCANCE
        Su implementación en contratos industriales constituye un entorno de validación operativa bajo licencia. El uso por parte de entidades contratantes o terceros no otorga derechos de comercialización, sub-licenciamiento o transferencia de propiedad intelectual.

        ### 3. PROTECCIÓN DE DATOS (LEY N° 19.628)
        En cumplimiento con la **Ley N° 19.628 sobre Protección de la Vida Privada** en Chile, los datos personales y registros de salud ingresados serán utilizados exclusivamente para fines de trazabilidad y Seguridad y Salud Ocupacional (S&SO).

        ### 4. RESPONSABILIDAD DEL USUARIO Y VERACIDAD DE DATOS
        El usuario es el único responsable de la veracidad, exactitud y vigencia de la información ingresada (RUT, fechas, horómetros, archivos PDF). La Aplicación es una herramienta de apoyo; la decisión final de permitir o detener una operación recae exclusivamente en el personal de supervisión humano.

        ### 5. LIMITACIÓN DE RESPONSABILIDAD
        El autor no será responsable por perjuicios derivados de ingresos de datos erróneos, detenciones operacionales basadas en el estado del semáforo o fallos derivados de infraestructura externa.

        ### 6. NO EXCLUSIVIDAD Y ESCALABILIDAD
        La implementación en un contrato específico no implica exclusividad. El autor se reserva el derecho de licenciar esta tecnología a cualquier otra entidad o rubro industrial de manera independiente.

        ### 7. MODIFICACIONES Y ACTUALIZACIONES
        El autor puede actualizar o modificar funciones para mejorar el rendimiento o seguridad. Los cambios significativos en estos términos serán notificados a través de la interfaz.

        ### 8. RESPONSABILIDAD OPERATIVA
        El usuario es responsable de la veracidad de la información ingresada. CGT es una herramienta de apoyo; la decisión final de operación recae en el personal de supervisión humano.

        ### 9. JURISDICCIÓN
        Cualquier controversia será resuelta bajo las leyes de la República de Chile, en los tribunales competentes de la ciudad de Calama.
        """)

    st.write("")
    aceptar_check = st.checkbox("He leído y acepto los términos de propiedad y privacidad de la plataforma.")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Aceptar y Entrar", disabled=not aceptar_check, use_container_width=True):
            ejecutar_query(db_path, "UPDATE usuarios SET terminos_aceptados = 1 WHERE username = ?", (user_login,), commit=True)
            st.session_state.must_accept_terms = False
            st.rerun()
    with col2:
        if st.button("❌ Rechazar", use_container_width=True):
            st.session_state.logged_in = False
            st.rerun()
