import os
from datetime import datetime
import streamlit as st

# Imports de Tabs (Módulos Operativos)
from vistas.inteligencia.tabs.tab_chat import render_tab_chat
from vistas.inteligencia.tabs.tab_diag import render_tab_diag
from vistas.inteligencia.tabs.tab_ocr import render_tab_ocr
from vistas.inteligencia.tabs.tab_forecast import render_tab_forecast
from vistas.inteligencia.tabs.tab_normativa import render_tab_normativa
from vistas.inteligencia.tabs.tab_coaching import render_tab_coaching
from vistas.inteligencia.tabs.tab_audit import render_tab_audit
from vistas.inteligencia.tabs.tab_analytics import render_tab_analytics
from vistas.inteligencia.tabs.tab_health import render_tab_health
from vistas.inteligencia.tabs.tab_recovery import render_tab_recovery
from vistas.inteligencia.tabs.tab_mant import render_tab_mant
from vistas.inteligencia.tabs.tab_devtools import render_tab_devtools
from vistas.inteligencia.tabs.tab_webdev import render_tab_webdev
from vistas.inteligencia.tabs.tab_modgen import render_tab_modgen
from vistas.inteligencia.tabs.tab_brain_config import render_tab_brain_config
from vistas.inteligencia.tabs.tab_memory import render_tab_memory
from vistas.inteligencia.tabs.tab_evolution import render_tab_evolution

from src.infrastructure.database import obtener_config


def render_chat_ultron(DB_PATH, filtros, tab_idx=None):
    # ── Control de Acceso ──────────────────────────────────────
    if st.session_state.get('role') not in ["Global Admin", "Admin"]:
        st.error("🛡️ ACCESO DENEGADO: Módulo exclusivo para Administradores.")
        return

    # ── Sincronización API Key Inicial ─────────────────────────
    if 'gemini_api_key' not in st.session_state or not st.session_state['gemini_api_key']:
        brain_cfg = obtener_config(DB_PATH, "ULLTRONE_BRAIN_CONFIG", {})
        st.session_state['gemini_api_key'] = brain_cfg.get("api_key", "")

    # ── Tema CSS y Header ─────────────────────────────────────
    st.markdown("<p class='cc-header'>🤖 Ull-Trone Command Center (v4.0)</p>", unsafe_allow_html=True)
    st.markdown("<p class='cc-subtitle'>Orquestador Cognitivo: Chat Estratégico, Analítica Avanzada y Control del Ecosistema Integrados</p>", unsafe_allow_html=True)
    
    # ── LAYOUT DE MÓDULOS ESPECÍFICOS ──────────────────────────
    
    # Si no hay tab_idx, mostramos el chat por defecto
    if tab_idx is None: tab_idx = 0

    if tab_idx == 0: # 🧠 CANAL DIRECTO
        st.markdown("<h4 class='cc-tools-header'>Canal Directo de Comunicación</h4>", unsafe_allow_html=True)
        render_tab_chat(DB_PATH, filtros)

    elif tab_idx == 1: # 📊 ANALÍTICA PREDICTIVA
        st.markdown("<h4 class='cc-tools-header'>Analítica Predictiva & Estratégica</h4>", unsafe_allow_html=True)
        t1, t2, t3 = st.tabs(["📉 Forecast & Reportes", "📊 Analítica Avanzada", "🔍 Diagnóstico"])
        with t1:
            render_tab_forecast(DB_PATH, filtros)
        with t2:
            render_tab_analytics(DB_PATH, filtros)
        with t3:
            render_tab_diag(DB_PATH, filtros)

    elif tab_idx == 2: # 🔬 TOOLS & DIAGNÓSTICO
        st.markdown("<h4 class='cc-tools-header'>Laboratorio de Herramientas Operacionales</h4>", unsafe_allow_html=True)
        t1, t2, t3 = st.tabs(["🔬 Validador OCR", "🎓 Coaching Operacional", "📝 Auditoría & Simulacro"])
        with t1:
            render_tab_ocr(DB_PATH, filtros)
        with t2:
            render_tab_coaching(DB_PATH, filtros)
        with t3:
            render_tab_audit(DB_PATH, filtros)

    elif tab_idx == 3: # 🩺 SALUD & DEV
        st.markdown("<h4 class='cc-tools-header'>Centro de Resiliencia & Desarrollo</h4>", unsafe_allow_html=True)
        t1, t2, t3, t4 = st.tabs(["🩺 Salud Sistema", "🛡️ Resiliencia", "🛠️ Mantenimiento", "🔧 Dev Tools"])
        with t1:
            render_tab_health(DB_PATH, filtros)
        with t2:
            render_tab_recovery(DB_PATH, filtros)
        with t3:
            render_tab_mant(DB_PATH, filtros)
        with t4:
            with st.container(height=600):
                render_tab_devtools(DB_PATH, filtros)
                st.divider()
                render_tab_webdev(DB_PATH, filtros)
                st.divider()
                render_tab_modgen(DB_PATH, filtros)

    elif tab_idx == 4: # ⚙️ NÚCLEO CENTRAL
        st.markdown("<h4 class='cc-tools-header'>Configuración del Núcleo Cognitivo</h4>", unsafe_allow_html=True)
        t1, t2, t3, t4 = st.tabs(["⚙️ Cerebro (LLM)", "📑 Memoria", "⚡ Normativa", "🧬 Evolución"])
        with t1:
            render_tab_brain_config(DB_PATH, filtros)
        with t2:
            render_tab_memory(DB_PATH, filtros)
        with t3:
            render_tab_normativa(DB_PATH, filtros)
        with t4:
            render_tab_evolution(DB_PATH, filtros)

