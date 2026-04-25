"""
tab_modgen.py  —  Ull-Trone: Generador de Módulos CGT.pro
Motor de scaffolding inteligente para crear nuevos módulos, vistas e integraciones
directamente dentro del sistema CGT.pro.
"""
import os
from datetime import datetime

import streamlit as st

from src.infrastructure.database import ejecutar_query, obtener_dataframe, registrar_log
from intelligence.agents.intelligence_engine import ask_ultron

# ── CATÁLOGO DE CAPACIDADES DISPONIBLES ────────────────────────────────────────
CAPACIDADES_ULLTRONE = {
    "🛡️ Seguridad & Compliance": [
        "Análisis de normativa chilena (DS 44, DS 594, RESSO, SUSESO)",
        "Auditorías automáticas basadas en checklists ISO 9001/14001/45001",
        "Generación de informes de cumplimiento en PDF",
        "Monitoreo de cambios normativos en tiempo real",
        "Scoring de riesgo por empresa/contrato",
    ],
    "📊 Analítica & BI": [
        "Dashboards interactivos con Plotly",
        "Forecast de vencimientos documentales",
        "Benchmarking de cumplimiento entre empresas",
        "Detección de anomalías en datos",
        "Exportación automatizada a Excel/PDF",
    ],
    "🤖 Inteligencia Artificial": [
        "Chat contextual con Google Gemini LLM",
        "OCR + validación de documentos",
        "Análisis de imágenes (detección EPP con visión computacional)",
        "Sequential Thinking (razonamiento encadenado visible)",
        "Coaching personalizado basado en historial de fallas",
    ],
    "🌐 Desarrollo Web": [
        "Generación de código Streamlit/Python funcional",
        "Scaffolding de módulos CGT.pro con arquitectura estándar",
        "Evaluación de stacks tecnológicos (Next.js, FastAPI, etc.)",
        "Planificación de proyectos web con hitos y fases",
        "Revisión y mejora de código existente",
    ],
    "📁 Gestión Documental": [
        "Auto-clasificación de documentos subidos",
        "Trazabilidad completa de expedientes (Personal, Maquinaria, Izaje, Instrumentos)",
        "Control de vencimientos con alertas automáticas",
        "QR de acceso rápido por trabajador/activo",
        "Sincronización masiva desde Excel maestro",
    ],
    "🔧 Operaciones del Sistema": [
        "Diagnóstico estructural de la base de datos",
        "Auto-reparación de columnas faltantes",
        "Backup automático cada 2 horas",
        "Restauración a puntos de recuperación",
        "Log de auditoría de acciones de usuario",
    ],
}

IDEAS_MODULOS = [
    {
        "nombre": "📡 Portal de Clientes (Multi-Tenant Web)",
        "desc": "Interfaz web pública donde cada empresa ve su propio estado de cumplimiento, descargar informes y comunicarse con el equipo CGT.",
        "stack": "Next.js + FastAPI + PostgreSQL",
        "impacto": "Alto",
        "esfuerzo": "Alto (2-3 meses)"
    },
    {
        "nombre": "📬 Motor de Notificaciones Email/WhatsApp",
        "desc": "Envío automático de alertas por vencimientos próximos, incidentes o nuevas no conformidades a responsables vía correo y WhatsApp Business API.",
        "stack": "Python (FastAPI + Celery) + Twilio / SendGrid",
        "impacto": "Alto",
        "esfuerzo": "Medio (3 semanas)"
    },
    {
        "nombre": "📱 App Mobile (PWA)",
        "desc": "Versión Progressive Web App del portal para uso en terreno: cargar fotos de EPP, reportar incidentes y consultar expedientes desde el celular.",
        "stack": "Next.js PWA",
        "impacto": "Alto",
        "esfuerzo": "Medio-Alto (1-2 meses)"
    },
    {
        "nombre": "🔑 SSO / Auth Empresarial",
        "desc": "Integración con Google Workspace, Microsoft Azure AD o sistemas LDAP para login corporativo unificado.",
        "stack": "FastAPI + OAuth2/OIDC",
        "impacto": "Medio",
        "esfuerzo": "Medio (3-4 semanas)"
    },
    {
        "nombre": "📊 API REST Pública CGT",
        "desc": "Exponer datos de cumplimiento vía API para integrarse con ERPs, Power BI u otros sistemas de los clientes.",
        "stack": "FastAPI + JWT Auth",
        "impacto": "Alto",
        "esfuerzo": "Medio (1 mes)"
    },
    {
        "nombre": "🧮 Calculadora de Multas y Sanciones",
        "desc": "Módulo que estima el costo potencial de incumplimientos normativos según la legislación vigente (DS 40, 594, etc.).",
        "stack": "Streamlit interno",
        "impacto": "Medio",
        "esfuerzo": "Bajo (1 semana)"
    },
    {
        "nombre": "🗺️ Mapa Geoespacial de Obras",
        "desc": "Visualización en mapa de todas las obras/contratos activos con geolocalización, estado de cumplimiento y alertas por zona.",
        "stack": "Streamlit + Folium/Deck.gl",
        "impacto": "Medio",
        "esfuerzo": "Bajo-Medio (2 semanas)"
    },
    {
        "nombre": "🤝 Módulo de Subcontratistas",
        "desc": "Gestión de empresas subcontratistas de cada contrato principal: documentación, requisitos RESSO propios y trazabilidad de su personal.",
        "stack": "Streamlit interno",
        "impacto": "Alto",
        "esfuerzo": "Medio (3-4 semanas)"
    },
]


def render_tab_modgen(DB_PATH, filtros):
    st.markdown("""
    <div style="background: linear-gradient(135deg, rgba(99,102,241,0.12), rgba(168,85,247,0.08));
                border-left: 5px solid #6366F1; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
        <p style="margin:0; font-size: 0.85rem; color: #6366F1; font-weight: bold;">
            🧩 MODO: GENERADOR DE MÓDULOS & ROADMAP
        </p>
        <p style="margin:4px 0 0; color: #8B98B8; font-size: 0.85rem;">
            Expande el potencial de CGT.pro. Analiza el catálogo, diseña nuevos módulos y genera código listo para integrar.
        </p>
    </div>
    """, unsafe_allow_html=True)

    subtab_cap, subtab_ideas, subtab_gen, subtab_roadmap = st.tabs([
        "⚡ Capacidades Actuales", "💡 Ideas de Expansión", "🛠️ Generar Módulo", "🗺️ Roadmap Estratégico"
    ])

    # ── SUBTAB 1: Catálogo de capacidades actuales ──────────────────────────────
    with subtab_cap:
        st.markdown("#### ⚡ Qué puede hacer Ull-Trone hoy")
        st.caption("Inventario completo de capacidades disponibles en CGT.pro v3.1")

        for categoria, habilidades in CAPACIDADES_ULLTRONE.items():
            with st.expander(categoria, expanded=False):
                for h in habilidades:
                    st.markdown(f"✅ {h}")

        st.divider()
        st.markdown("#### 🔍 Buscar Capacidad")
        busqueda = st.text_input("Buscar en el catálogo:", placeholder="Ej: PDF, email, QR, ISO...")
        if busqueda.strip():
            encontradas = []
            for cat, habs in CAPACIDADES_ULLTRONE.items():
                for h in habs:
                    if busqueda.lower() in h.lower() or busqueda.lower() in cat.lower():
                        encontradas.append((cat, h))
            if encontradas:
                for cat, h in encontradas:
                    st.markdown(f"- **{cat}** → {h}")
            else:
                st.info("No se encontraron capacidades con ese término. ¿Quieres que Ull-Trone la cree?")
                if st.button(f"🚀 Generar capacidad: '{busqueda}'", key="btn_cap_gen"):
                    p = (
                        f"El equipo de Tecktur SpA quiere agregar esta capacidad a CGT.pro: '{busqueda}'.\n"
                        "Propón cómo implementarla: qué librerías usar, cómo integrarla en la arquitectura actual "
                        "(Streamlit + SQLite + core modules), qué datos necesita, y genera el esqueleto de código."
                    )
                    with st.spinner("Ull-Trone diseñando implementación..."):
                        resp = ask_ultron(DB_PATH, p, st.session_state.user_login,
                                         api_key=st.session_state.get('gemini_api_key', ''))
                    st.markdown(resp.get("content", ""))

    # ── SUBTAB 2: Ideas de expansión priorizadas ────────────────────────────────
    with subtab_ideas:
        st.markdown("#### 💡 Ideas de Expansión — Próximos Módulos")
        st.caption("Oportunidades estratégicas identificadas para maximizar el valor de CGT.pro")

        for idea in IDEAS_MODULOS:
            with st.container(border=True):
                col_info, col_meta = st.columns([3, 1])
                with col_info:
                    st.markdown(f"### {idea['nombre']}")
                    st.markdown(idea['desc'])
                    st.caption(f"**Stack sugerido:** `{idea['stack']}`")
                with col_meta:
                    impacto_color = "#10B981" if idea['impacto'] == "Alto" else "#F59E0B"
                    st.markdown(f"""
                    <div style='text-align:center;'>
                        <div style='background: {impacto_color}22; border: 1px solid {impacto_color};
                                    border-radius: 6px; padding: 6px; margin-bottom: 8px;'>
                            <span style='color:{impacto_color}; font-weight:bold; font-size:0.8rem;'>
                                Impacto: {idea['impacto']}
                            </span>
                        </div>
                        <div style='background: rgba(99,102,241,0.1); border: 1px solid #6366F1;
                                    border-radius: 6px; padding: 6px;'>
                            <span style='color:#6366F1; font-size:0.75rem;'>
                                ⏱️ {idea['esfuerzo']}
                            </span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                if st.button(f"🤖 Analizar & Diseñar", key=f"btn_idea_{idea['nombre'][:10]}", use_container_width=True):
                    p = (
                        f"Diseña en detalle el módulo: '{idea['nombre']}'\n"
                        f"Descripción: {idea['desc']}\n"
                        f"Stack sugerido: {idea['stack']}\n\n"
                        "Proporciona:\n"
                        "1. Arquitectura técnica detallada\n"
                        "2. Esquema de base de datos (tablas SQL)\n"
                        "3. Prototipo de código (función render principal)\n"
                        "4. Plan de integración con CGT.pro existente\n"
                        "5. Estimado de desarrollo"
                    )
                    with st.spinner(f"Ull-Trone diseñando {idea['nombre']}..."):
                        resp = ask_ultron(DB_PATH, p, st.session_state.user_login,
                                         api_key=st.session_state.get('gemini_api_key', ''))
                    with st.expander("📋 Diseño generado", expanded=True):
                        st.markdown(resp.get("content", ""))

    # ── SUBTAB 3: Generador de Módulo Custom ────────────────────────────────────
    with subtab_gen:
        st.markdown("#### 🛠️ Generador de Módulo Custom para CGT.pro")
        st.caption("Describe el módulo que necesitas y Ull-Trone genera el código completo listo para integrar.")

        with st.form("form_gen_modulo"):
            nombre_mod = st.text_input("📦 Nombre del Módulo:", placeholder="Ej: Gestión de Contratos")
            desc_mod = st.text_area(
                "📝 Descripción funcional:",
                placeholder=(
                    "Qué hace el módulo, qué datos maneja, qué usuarios lo usan, "
                    "qué acciones permite (CRUD, reportes, filtros, etc.)"
                ),
                height=100
            )
            col1, col2 = st.columns(2)
            with col1:
                tiene_tabla = st.checkbox("Necesita nueva tabla en BD", value=True)
                tiene_filtros = st.checkbox("Requiere filtros por empresa/contrato", value=True)
            with col2:
                tiene_roles = st.checkbox("Control de acceso por rol", value=True)
                tiene_exportacion = st.checkbox("Exportar a Excel/PDF", value=False)

            complejidad = st.select_slider(
                "Complejidad:",
                options=["Simple", "Media", "Compleja", "Enterprise"],
                value="Media"
            )

            if st.form_submit_button("🚀 Generar Módulo Completo", use_container_width=True):
                if nombre_mod and desc_mod:
                    reqs = []
                    if tiene_tabla: reqs.append("Incluir CREATE TABLE SQL para la nueva tabla")
                    if tiene_filtros: reqs.append("Respetar filtros de empresa_id y contrato_id del session_state")
                    if tiene_roles: reqs.append("Incluir control de acceso con st.session_state.role")
                    if tiene_exportacion: reqs.append("Incluir función de exportación a Excel usando pandas")

                    prompt_gen = (
                        f"[GENERADOR DE MÓDULO CGT.PRO]\n"
                        f"Genera el código Python/Streamlit COMPLETO y funcional para el módulo: '{nombre_mod}'\n\n"
                        f"Descripción: {desc_mod}\n"
                        f"Complejidad: {complejidad}\n"
                        f"Requerimientos técnicos específicos:\n"
                        + "\n".join(f"- {r}" for r in reqs) +
                        "\n\nARQUITECTURA OBLIGATORIA:\n"
                        "- El módulo debe ser una función: render_[nombre](DB_PATH, filtros)\n"
                        "- Usar: from src.infrastructure.database import ejecutar_query, obtener_dataframe\n"
                        "- Usar st.container(border=True) para secciones principales\n"
                        "- Encabezado: st.markdown('<h2 style=color:var(--cgt-blue)>...</h2>') \n"
                        "- Comentarios claros en cada sección del código\n"
                        "- Manejo de errores con try/except\n"
                        "- Incluir también las instrucciones de integración en app.py"
                    )
                    with st.spinner("🧩 Ull-Trone generando módulo completo..."):
                        resp = ask_ultron(DB_PATH, prompt_gen, st.session_state.user_login,
                                         api_key=st.session_state.get('gemini_api_key', ''))
                        st.session_state['last_mod_gen'] = {
                            "nombre": nombre_mod,
                            "content": resp.get("content", "No se pudo generar el código.")
                        }
                else:
                    st.warning("Completa el nombre y la descripción del módulo.")

        # Visualización fuera del FORM para evitar StreamlitAPIException
        if 'last_mod_gen' in st.session_state:
            res = st.session_state['last_mod_gen']
            st.markdown("---")
            st.markdown(f"### 📦 Módulo Generado: {res['nombre']}")
            st.markdown(res['content'])

            st.download_button(
                "📥 Descargar como .py",
                data=res['content'],
                file_name=f"modulo_{res['nombre'].lower().replace(' ', '_')}.py",
                mime="text/plain",
                key="dl_modulo"
            )

    # ── SUBTAB 4: Roadmap Estratégico ───────────────────────────────────────────
    with subtab_roadmap:
        st.markdown("#### 🗺️ Roadmap Estratégico CGT.pro")
        st.caption("Genera un roadmap de desarrollo personalizado basado en tus metas y recursos.")

        # Roadmap visual estático del estado actual
        fases_actuales = [
            ("✅ v1.0 — Core Operativo", "Trazabilidad Personal/Maquinaria/Izaje, ART, Incidentes", "Completado"),
            ("✅ v2.0 — Compliance & SGI", "ISO 9001/14001/45001, DS 44, Control Documental, PTS", "Completado"),
            ("✅ v3.0 — Inteligencia Operativa", "Ull-Trone AI, OCR, Forecast, Analytics, Dev Tools", "Completado"),
            ("🚧 v3.5 — Expansión Estratégica", "Portal de Clientes, Notificaciones Email/WA, PWA Mobile", "En Planificación"),
            ("🔮 v4.0 — Enterprise Platform", "SSO Corporativo, API REST Pública, Multi-región, BI Avanzado", "Visión Futura"),
        ]

        for fase, desc, estado in fases_actuales:
            color = "#10B981" if estado == "Completado" else "#F59E0B" if estado == "En Planificación" else "#6366F1"
            icon = "✅" if estado == "Completado" else "🚧" if estado == "En Planificación" else "🔮"
            st.markdown(f"""
            <div style="border-left: 4px solid {color}; padding: 10px 15px; margin-bottom: 10px;
                        background: {color}11; border-radius: 0 8px 8px 0;">
                <strong style="color: {color};">{fase}</strong>
                <p style="margin: 4px 0 0; font-size: 0.85rem; color: #8B98B8;">{desc}</p>
                <span style="font-size: 0.75rem; color: {color};">{icon} {estado}</span>
            </div>
            """, unsafe_allow_html=True)

        st.divider()
        st.markdown("#### 🤖 Generar Roadmap Personalizado con Ull-Trone")

        meta = st.text_area(
            "¿Cuál es tu meta para los próximos 6 meses?",
            placeholder=(
                "Ej: Quiero tener 20 clientes usando el sistema, necesito app mobile, "
                "y generar reportes automáticos para cada cliente mensualmente."
            )
        )
        recursos = st.text_input(
            "¿Con qué recursos cuentas?",
            placeholder="Ej: 1 developer part-time, presupuesto limitado, 10 hrs/semana"
        )

        if st.button("🗺️ Generar Roadmap Estratégico", use_container_width=True, key="btn_roadmap"):
            if meta.strip():
                p = (
                    f"[PLANIFICADOR ESTRATÉGICO CGT.PRO]\n\n"
                    f"CGT.pro es un sistema de gestión HSE/compliance industrial en Python/Streamlit "
                    f"con las capacidades actuales documentadas en el sistema.\n\n"
                    f"Meta del equipo: {meta}\n"
                    f"Recursos disponibles: {recursos or 'No especificado'}\n\n"
                    "Genera un roadmap estratégico de 6 meses que incluya:\n"
                    "1. Análisis de gaps entre situación actual y meta\n"
                    "2. Módulos/features prioritarios (con justificación de ROI)\n"
                    "3. Plan mensual detallado (Mes 1, 2, 3, 4, 5, 6)\n"
                    "4. Hitos de entrega clave\n"
                    "5. KPIs para medir el éxito\n"
                    "6. Riesgos y contingencias\n"
                    "7. Recomendación de stack para el próximo módulo"
                )
                with st.spinner("Ull-Trone elaborando roadmap estratégico..."):
                    resp = ask_ultron(DB_PATH, p, st.session_state.user_login,
                                     api_key=st.session_state.get('gemini_api_key', ''))
                st.markdown("---")
                st.markdown("### 🗺️ Tu Roadmap Estratégico")
                st.markdown(resp.get("content", "No se pudo generar el roadmap."))

                content_dl = resp.get("content", "")
                st.download_button(
                    "📥 Descargar Roadmap",
                    data=content_dl,
                    file_name=f"Roadmap_CGT_{datetime.now().strftime('%Y%m')}.md",
                    mime="text/markdown",
                    key="dl_roadmap"
                )
            else:
                st.warning("Describe tu meta para generar el roadmap.")
