"""
Sistema Centralizado de Temas Dinámicos CGT
===========================================
Soporte para múltiples paletas (Día/Noche) con cambio dinámico.

USO BÁSICO:
    from config.themes import get_card_style, COLOR_ROJO, get_TEXT_PRIMARY
    
    # Los colores cambian automáticamente según el tema activo
    st.markdown(f"<div style='{get_card_style(COLOR_ROJO)}'>{content}</div>")
"""

import streamlit as st

# ============================================================================
# PALETAS DE COLORES
# ============================================================================

PALETAS = {
    "claro": {
        "name": "☀️ Claro",
        "emoji": "☀️",
        "bg_primary": "#F5F3F0",
        "bg_secondary": "#FAF8F6",
        "bg_hover": "#faf8f6",
        "text_primary": "#1F2937",
        "text_secondary": "#4B5563",
        "text_tertiary": "#6b7280",
        "text_light": "#9ca3af",
        "border": "#d4d4d8",
        "border_light": "#e5e7eb",
        "shadow": "rgba(0,0,0,0.05)",
        "shadow_hover": "rgba(59,130,246,0.1)",
    },
    "oscuro": {
        "name": "🌙 Oscuro",
        "emoji": "🌙",
        "bg_primary": "#1E293B",
        "bg_secondary": "#0F172A",
        "bg_hover": "#252A30",
        "text_primary": "#F8FAFC",
        "text_secondary": "#CBD5E1",
        "text_tertiary": "#94A3B8",
        "text_light": "#64748B",
        "border": "#334155",
        "border_light": "#475569",
        "shadow": "rgba(0,0,0,0.3)",
        "shadow_hover": "rgba(59,130,246,0.3)",
    }
}

# Colores semáforo (invariables en ambos temas)
SEMAFORO = {
    "rojo": "#ef4444",
    "naranja": "#f59e0b",
    "verde": "#10b981",
    "azul": "#3b82f6",
    "morado": "#a855f7",
    "cian": "#06b6d4",
}

SEMAFORO_TEXT = {
    "rojo": "#dc2626",
    "naranja": "#b45309",
    "verde": "#047857",
    "azul": "#1e40af",
    "morado": "#7c3aed",
}

# Constantes de colores semáforo (siempre iguales)
COLOR_ROJO = SEMAFORO["rojo"]
COLOR_NARANJA = SEMAFORO["naranja"]
COLOR_VERDE = SEMAFORO["verde"]
COLOR_AZUL = SEMAFORO["azul"]
COLOR_MORADO = SEMAFORO["morado"]
COLOR_CIAN = SEMAFORO["cian"]

TEXT_ROJO = SEMAFORO_TEXT["rojo"]
TEXT_NARANJA = SEMAFORO_TEXT["naranja"]
TEXT_VERDE = SEMAFORO_TEXT["verde"]
TEXT_AZUL = SEMAFORO_TEXT["azul"]
TEXT_MORADO = SEMAFORO_TEXT["morado"]


# ============================================================================
# FUNCIONES DE ACCESO DINÁMICO
# ============================================================================

def get_current_theme():
    """Obtiene el tema actual del session_state"""
    if "app_theme" not in st.session_state:
        st.session_state.app_theme = "claro"
    return st.session_state.app_theme


def set_theme(theme_name):
    """Cambia el tema actual"""
    if theme_name in PALETAS:
        st.session_state.app_theme = theme_name
        st.rerun()


def get_theme_colors():
    """Retorna la paleta completa del tema actual"""
    theme = get_current_theme()
    return PALETAS[theme]


def get_color(color_key):
    """Obtiene un color específico del tema actual"""
    colors = get_theme_colors()
    return colors.get(color_key, "#000000")


# ============================================================================
# FUNCIONES GETTER PARA COLORES DINÁMICOS
# ============================================================================

def get_BACKGROUND_PRIMARY():
    return get_color("bg_primary")

def get_BACKGROUND_SECONDARY():
    return get_color("bg_secondary")

def get_BACKGROUND_HOVER():
    return get_color("bg_hover")

def get_TEXT_PRIMARY():
    return get_color("text_primary")

def get_TEXT_SECONDARY():
    return get_color("text_secondary")

def get_TEXT_TERTIARY():
    return get_color("text_tertiary")

def get_TEXT_LIGHT():
    return get_color("text_light")

def get_BORDER_COLOR():
    return get_color("border")

def get_BORDER_COLOR_LIGHT():
    return get_color("border_light")

def get_SHADOW_COLOR():
    return get_color("shadow")

def get_SHADOW_HOVER():
    return get_color("shadow_hover")


# ============================================================================
# FUNCIONES HELPER PARA ESTILOS
# ============================================================================

def get_card_style(border_color=None, padding="20px"):
    """Genera HTML style para tarjetas estándar"""
    if border_color is None:
        border_color = COLOR_AZUL
    
    return f"""
        background: {get_BACKGROUND_PRIMARY()};
        color: {get_TEXT_PRIMARY()};
        padding: {padding};
        border-radius: 12px;
        border-left: 5px solid {border_color};
        box-shadow: 0 4px 6px -1px {get_SHADOW_COLOR()};
    """

def get_card_container_style():
    """Genera HTML style para contenedores de tarjetas grandes"""
    return f"""
        background: {get_BACKGROUND_PRIMARY()};
        color: {get_TEXT_PRIMARY()};
        padding: 2rem;
        border-radius: 15px;
        border: 1px solid {get_BORDER_COLOR_LIGHT()};
        margin-bottom: 2rem;
        box-shadow: 0 10px 15px -3px {get_SHADOW_COLOR()};
    """

def get_metric_card_style(border_color=None):
    """Genera HTML style para tarjetas de métricas"""
    if border_color is None:
        border_color = COLOR_AZUL
    
    return f"""
        background: {get_BACKGROUND_PRIMARY()};
        padding: 15px;
        border-radius: 10px;
        border-top: 4px solid {border_color};
        box-shadow: 0 4px 6px -1px {get_SHADOW_COLOR()};
    """

def get_header_style(border_color=None):
    """Genera HTML style para headers"""
    if border_color is None:
        border_color = COLOR_AZUL
    
    return f"""
        background: {get_BACKGROUND_PRIMARY()};
        color: {get_TEXT_PRIMARY()};
        padding: 2rem;
        border-radius: 15px;
        border-left: 5px solid {border_color};
        margin-bottom: 2rem;
        box-shadow: 0 4px 6px -1px {get_SHADOW_COLOR()};
    """

def get_banner_style(border_color=None):
    """Genera HTML style para banners"""
    if border_color is None:
        border_color = COLOR_AZUL
    
    return f"""
        background: {get_BACKGROUND_PRIMARY()};
        border-left: 5px solid {border_color};
        border-radius: 15px;
        padding: 25px;
        margin-bottom: 20px;
        box-shadow: 0 4px 6px -1px {get_SHADOW_COLOR()};
    """

def get_metric_label_style(label_color=None):
    """Genera HTML style para etiquetas de métricas"""
    if label_color is None:
        label_color = get_TEXT_SECONDARY()
    
    return f"""
        color: {label_color};
        font-size: 0.75rem;
        font-weight: 600;
        margin: 0;
    """

def get_metric_value_style():
    """Genera HTML style para valores de métricas"""
    return f"""
        color: {get_TEXT_PRIMARY()};
        font-size: 1.8rem;
        font-weight: 800;
        margin: 0;
    """

def get_glassmorphic_style(bg_opacity=0.95):
    """Genera HTML style para tarjetas glassmorphic"""
    # Obtener el bg_primary y ajustar opacidad
    theme = get_current_theme()
    is_dark = theme == "oscuro"
    
    if is_dark:
        bg_rgba = f"rgba(30, 41, 59, {bg_opacity})"
    else:
        bg_rgba = f"rgba(245, 243, 240, {bg_opacity})"
    
    return f"""
        background: {bg_rgba};
        backdrop-filter: blur(10px);
        padding: 25px;
        border-radius: 20px;
        border: 1px solid {get_BORDER_COLOR()};
        box-shadow: 0 4px 6px -1px {get_SHADOW_COLOR()};
        margin-bottom: 25px;
    """


# ============================================================================
# CSS GLOBAL DINÁMICO
# ============================================================================

def get_global_css():
    """Retorna el bloque CSS centralizado con variables para ambos temas."""
    c = PALETAS["claro"]
    d = PALETAS["oscuro"]
    
    return f"""
    <style>
    /* VARIABLES GLOBALES (MODO CLARO POR DEFECTO) */
    :root {{
        --bg-main:      {c['bg_primary']};
        --bg-sidebar:   {c['bg_secondary']};
        --bg-card:      {c['bg_secondary']};
        --text-main:    {c['text_primary']};
        --text-muted:   {c['text_secondary']};
        --text-heading: {c['text_primary']};
        --border-color: {c['border']};
        --border-glass: {c['border_light']};
        --shadow-premium: 0 4px 6px -1px {c['shadow']};
        --primary-calipso: #0F172A;
        --accent-neon:     #0EA5E9;
    }}
    
    /* VARIABLES MODO OSCURO (ACTIVADO POR CLASE .cgt-dark) */
    .cgt-dark, [data-theme="dark"] {{
        --bg-main:      {d['bg_secondary']};
        --bg-sidebar:   #020617;
        --bg-card:      {d['bg_primary']};
        --text-main:    {d['text_primary']};
        --text-muted:   {d['text_tertiary']};
        --text-heading: {d['text_primary']};
        --border-color: {d['border']};
        --border-glass: {d['border_light']};
        --shadow-premium: 0 10px 15px -3px {d['shadow']};
        --primary-calipso: #38BDF8;
        --accent-neon:     #38BDF8;
    }}

    /* APLICACIÓN DE VARIABLES A STREAMLIT */
    .stApp {{
        background-color: var(--bg-main) !important;
        color: var(--text-main) !important;
    }}
    
    [data-testid="stSidebar"] {{
        background-color: var(--bg-sidebar) !important;
    }}

    /* Estilos de Tarjetas Dinámicas */
    .card-cgt, .glass-card {{
        background: var(--bg-card) !important;
        color: var(--text-main) !important;
        border: 1px solid var(--border-glass) !important;
        box-shadow: var(--shadow-premium) !important;
    }}
    
    .text-primary {{ color: var(--text-main) !important; }}
    .text-secondary {{ color: var(--text-muted) !important; }}
    
    /* UI ESPECÍFICA: ULL-TRONE COMMAND CENTER */
    .cc-header {{ 
        color: var(--accent-neon) !important; 
        font-weight: 800; 
        font-size: 1.6rem; 
        margin-bottom: 0px;
    }}
    .cc-subtitle {{ 
        color: var(--text-muted); 
        font-size: 0.95rem; 
        margin-top: -5px; 
        margin-bottom: 25px; 
        font-weight: 500;
    }}
    .cc-tools-header {{ 
        color: var(--text-heading) !important; 
        margin-top:0; 
        border-bottom: 1px solid var(--border-glass); 
        padding-bottom: 8px;
    }}
    
    /* Mejoras en st.tabs */
    .stTabs [data-baseweb="tab-list"] {{ gap: 8px; }}
    .stTabs [data-baseweb="tab"] {{ padding-top: 10px; padding-bottom: 10px; border-radius: 4px 4px 0 0;}}
    
    /* Métricas Premium (Dashboard) */
    .metric-card-cgt {{
        background: var(--bg-card) !important;
        padding: 15px;
        border-radius: 12px;
        border: 1px solid var(--border-glass);
        box-shadow: var(--shadow-premium);
        transition: all 0.3s ease;
    }}
    .metric-label-cgt {{
        color: var(--text-muted) !important;
        font-size: 0.75rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin: 0 !important;
    }}
    /* Headers Premium de Módulos */
    .premium-header {{
        background: var(--bg-card) !important;
        color: var(--text-main) !important;
        padding: 2rem;
        border-radius: 15px;
        border-left: 5px solid var(--accent-neon);
        margin-bottom: 2rem;
        box-shadow: var(--shadow-premium);
    }}
    </style>
    """

# Eliminar selectores redundantes (serán manejados por el reloj)
def render_theme_selector(): pass
def render_theme_selector_sidebar(): pass


# ============================================================================
# GUÍA DE USO
# ============================================================================

MIGRATION_GUIDE = """
SISTEMA DE TEMAS DINÁMICO

1. IMPORTAR:
   from config.themes import (
       get_card_style, COLOR_ROJO, 
       get_TEXT_PRIMARY, render_theme_selector_sidebar
   )

2. USAR COLORES DINÁMICOS (cambian con el tema):
   st.markdown(f'''
       <div style='{get_card_style(COLOR_ROJO)}'>
           <p style='color: {get_TEXT_PRIMARY()};'>Texto dinámico</p>
       </div>
   ''', unsafe_allow_html=True)

3. AGREGAR SELECTOR EN LA APP:
   render_theme_selector_sidebar()  # En app.py

4. CAMBIO AUTOMÁTICO:
   - El CSS se actualiza automáticamente
   - st.rerun() recarga la aplicación
   - Todos los estilos se sincronizan

5. COLORES QUE NUNCA CAMBIAN:
   - Semáforo: COLOR_ROJO, COLOR_VERDE, COLOR_NARANJA, etc.
   - Estos son constantes en ambos temas
"""

