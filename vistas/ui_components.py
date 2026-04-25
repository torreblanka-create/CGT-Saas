import streamlit as st


def render_pillar_grid(title, description, modules):
    """
    Renders a premium card-based dashboard for a Pillar.
    'modules' is a list of dicts: {'label': str, 'icon': str, 'desc': str, 'route': str}
    """
    st.markdown(f"""
        <div style='margin-bottom: 2rem;'>
            <h1 style='color: var(--primary-calipso); font-family: "Outfit", sans-serif; margin-bottom: 0.5rem;'>{title}</h1>
            <p style='color: var(--text-muted); font-size: 1.1rem;'>{description}</p>
        </div>
    """, unsafe_allow_html=True)

    # Grid logic
    cols = st.columns(3)
    for i, mod in enumerate(modules):
        with cols[i % 3]:
            # Each card is a clean, focused container
            with st.container(border=True):
                # Determinar si es emoji o lucide
                icon_html = f"<div class='cgt-icon-preview'>{mod['icon']}</div>"
                if len(mod['icon']) > 2: # Probablemente un nombre de icono Lucide
                    icon_html = f"""
                    <div class='cgt-icon-lucide'>
                        <i data-lucide='{mod['icon']}'></i>
                    </div>
                    """

                # Header with icon and title
                st.markdown(f"""
                    <div class='cgt-pillar-card-header'>
                        {icon_html}
                        <h3 class='cgt-pillar-card-title'>{mod['label']}</h3>
                    </div>
                """, unsafe_allow_html=True)
                
                # Description
                st.markdown(f"""
                    <p class='cgt-pillar-card-desc'>
                        {mod['desc']}
                    </p>
                """, unsafe_allow_html=True)

                # Integrated primary action button
                if st.button(f"Sincronizar {mod['icon'] if len(mod['icon'])<=2 else ''}", key=f"btn_p_{mod['label']}_{i}", use_container_width=True, type="primary"):
                    st.session_state.menu_activo = mod['route']
                    st.rerun()

    # Scripts para inicializar Lucide si se usaron nombres de iconos
    st.markdown("<script>if(window.lucide) { lucide.createIcons(); }</script>", unsafe_allow_html=True)

def render_glass_metric(label, value, icon="📊", color="#38BDF8"):
    """
    Renders a premium glassmorphism metric card.
    """
    st.markdown(f"""
        <div class="metric-card-cgt" style="border-left: 4px solid {color};">
            <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 5px;">
                <span style="font-size: 1.2rem;">{icon}</span>
                <p class="metric-label-cgt">{label}</p>
            </div>
            <p style="font-size: 1.8rem; font-weight: 800; margin: 0; color: var(--text-heading);">{value}</p>
        </div>
    """, unsafe_allow_html=True)

def render_tool_box(title, tools):
    """
    Renders a sidebar-like tool box within a page.
    'tools' is a list of functions/lambdas.
    """
    with st.expander(f"🛠️ Herramientas Especializadas: {title}", expanded=False):
        for tool_name, tool_func in tools.items():
            if st.button(tool_name, use_container_width=True, key=f"tool_{tool_name}"):
                tool_func()
