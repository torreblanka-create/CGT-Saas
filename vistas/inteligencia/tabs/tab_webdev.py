"""
tab_webdev.py  —  Ull-Trone: Arquitecto Web Estratégico
Capacita a Ull-Trone como socio estratégico de desarrollo web y aplicaciones
para el equipo CGT.pro / Tecktur SpA.
"""
import os
from datetime import datetime

import streamlit as st

from src.infrastructure.database import ejecutar_query, guardar_config, obtener_config, obtener_dataframe
from intelligence.agents.intelligence_engine import ask_ultron

# ── DIRECTIVAS DE MODO WEB-DEV ─────────────────────────────────────────────────
WEB_DEV_DIRECTIVE = (
    "Eres Ull-Trone, socio estratégico de desarrollo web de Tecktur SpA. "
    "Tienes expertise en: HTML/CSS/JS vanilla, React, Next.js, Vite, Python/Streamlit, "
    "FastAPI, SQLite/PostgreSQL, diseño UX/UI premium, arquitectura modular, "
    "APIs REST, integración de LLMs y despliegue en Cloud Run / Vercel / Netlify. "
    "Proporciona código funcional, opina sobre arquitectura, sugiere mejoras de "
    "rendimiento y ayuda a planificar nuevos módulos o proyectos completos. "
    "Cuando generes código, usa bloques de código con lenguaje especificado. "
    "Siempre piensa en escalabilidad, mantenibilidad y experiencia de usuario premium."
)

STACKS_POPULARES = {
    "🐍 Streamlit + Python": {
        "desc": "Apps de datos internas, dashboards operativos, prototipos rápidos.",
        "pros": ["Desarrollo ultra-rápido", "Integración nativa con pandas/ML", "Sin JS requerido"],
        "contras": ["No apto para producción masiva", "UX limitada vs React"],
        "ideal_para": "Herramientas internas como CGT.pro"
    },
    "⚛️ Next.js + FastAPI": {
        "desc": "Web apps modernas con SSR, APIs RESTful y gran escalabilidad.",
        "pros": ["SEO óptimo", "Full-stack en un repo", "Ecosistema maduro"],
        "contras": ["Más complejo de configurar", "Requiere Node + Python"],
        "ideal_para": "Portafolio público, plataformas SaaS, landing pages premium"
    },
    "⚡ Vite + FastAPI": {
        "desc": "SPA rápida con backend Python moderno.",
        "pros": ["Build ultra-rápido", "Flexible (React/Vue/Vanilla)", "FastAPI docs automáticos"],
        "contras": ["Sin SSR nativo", "Más configs iniciales"],
        "ideal_para": "Apps internas complejas, dashboards con auth"
    },
    "🌐 HTML/CSS/JS Vanilla": {
        "desc": "Páginas estáticas, landing pages o widgets embebibles.",
        "pros": ["Zero dependencias", "Máxima control", "Deploy inmediato"],
        "contras": ["No escala para apps complejas", "Sin estado global"],
        "ideal_para": "Landing pages, micrositios, demos rápidas"
    },
}

TEMPLATES_MODULO = {
    "📊 Dashboard con Métricas": """
```python
import streamlit as st
import plotly.express as px
import pandas as pd

def render_dashboard_ejemplo(DB_PATH, filtros):
    st.markdown("<h2 style='color: var(--cgt-blue);'>📊 Mi Dashboard</h2>", unsafe_allow_html=True)
    
    # Métricas KPI
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Activos", "142", "+5")
    c2.metric("Vigentes", "128", "+3")
    c3.metric("En Alerta", "8", "-2")
    c4.metric("Bloqueados", "6", "+4")
    
    st.divider()
    
    # Gráfico de barras
    df = pd.DataFrame({"Categoría": ["A","B","C"], "Valor": [40, 60, 20]})
    fig = px.bar(df, x="Categoría", y="Valor", color="Valor",
                 color_continuous_scale="Blues")
    st.plotly_chart(fig, use_container_width=True)
```
""",
    "📋 CRUD con Tabla": """
```python
import streamlit as st
from src.infrastructure.database import ejecutar_query, obtener_dataframe

def render_crud_ejemplo(DB_PATH):
    st.markdown("### 📋 Gestión de Registros")
    
    df = obtener_dataframe(DB_PATH, "SELECT id, nombre, estado FROM mi_tabla")
    st.dataframe(df, use_container_width=True, hide_index=True)
    
    with st.expander("➕ Agregar Registro"):
        with st.form("form_nuevo"):
            nombre = st.text_input("Nombre")
            estado = st.selectbox("Estado", ["Activo", "Inactivo"])
            if st.form_submit_button("Guardar"):
                ejecutar_query(DB_PATH,
                    "INSERT INTO mi_tabla (nombre, estado) VALUES (?, ?)",
                    (nombre, estado), commit=True)
                st.success("✅ Registro guardado.")
                st.rerun()
```
""",
    "🔐 Módulo con Control de Roles": """
```python
import streamlit as st

ROLES_PERMITIDOS = ["Global Admin", "Admin"]

def render_modulo_protegido(DB_PATH, filtros):
    if st.session_state.get('role') not in ROLES_PERMITIDOS:
        st.error("🛡️ Acceso denegado. Se requiere permiso de Administrador.")
        return
    
    st.markdown("### 🔐 Módulo Restringido")
    st.info(f"Bienvenido, {st.session_state.username}. Tienes acceso completo.")
    # ... tu lógica aquí
```
""",
    "📈 Tab con Filtros": """
```python
import streamlit as st
from src.infrastructure.database import obtener_dataframe

def render_tab_con_filtros(DB_PATH, filtros):
    empresa_id = filtros.get('empresa_id', 0)
    
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        buscar = st.text_input("🔍 Buscar", placeholder="Nombre o código...")
    with col_f2:
        estado_sel = st.selectbox("Estado", ["Todos", "Activo", "Inactivo"])
    
    query = "SELECT * FROM mi_tabla WHERE 1=1"
    params = []
    if empresa_id > 0:
        query += " AND empresa_id = ?"; params.append(empresa_id)
    if estado_sel != "Todos":
        query += " AND estado = ?"; params.append(estado_sel)
    
    df = obtener_dataframe(DB_PATH, query, tuple(params))
    if buscar:
        df = df[df.apply(lambda r: buscar.lower() in str(r.values).lower(), axis=1)]
    
    st.dataframe(df, use_container_width=True, hide_index=True)
```
"""
}


def render_tab_webdev(DB_PATH, filtros):
    st.markdown("""
    <div style="background: linear-gradient(135deg, rgba(0,188,212,0.1), rgba(99,102,241,0.1));
                border-left: 5px solid #00BCD4; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
        <p style="margin:0; font-size: 0.85rem; color: #00BCD4; font-weight: bold;">
            🌐 MODO: ARQUITECTO WEB ESTRATÉGICO
        </p>
        <p style="margin:4px 0 0; color: #8B98B8; font-size: 0.85rem;">
            Ull-Trone actúa como tu socio de desarrollo: diseña, codifica, evalúa stacks y planifica proyectos.
        </p>
    </div>
    """, unsafe_allow_html=True)

    subtab_chat, subtab_stack, subtab_templates, subtab_planner = st.tabs([
        "💬 Chat Dev", "🔬 Evaluador de Stack", "🧱 Templates de Código", "📋 Planificador de Proyecto"
    ])

    # ── SUBTAB 1: Chat especializado en desarrollo ──────────────────────────────
    with subtab_chat:
        st.markdown("#### 💬 Canal de Desarrollo — Consulta a Ull-Trone")
        st.caption("Pregunta sobre arquitectura, código, debugging, APIs, diseño UX, despliegue, etc.")

        # Historial de chat en sesión (separado del chat principal)
        if "webdev_messages" not in st.session_state:
            st.session_state.webdev_messages = [
                {"role": "assistant", "content":
                 "⚡ **Ull-Trone Dev Mode activo.**\n\n"
                 "Soy tu socio estratégico de desarrollo. Puedo ayudarte a:\n"
                 "- Diseñar arquitecturas de apps y módulos\n"
                 "- Generar código funcional (Python, HTML, JS, SQL)\n"
                 "- Evaluar y elegir stacks tecnológicos\n"
                 "- Planificar proyectos web completos\n"
                 "- Revisar y mejorar tu código existente\n\n"
                 "¿Qué construimos hoy?"}
            ]

        chat_c = st.container(height=400)
        with chat_c:
            for msg in st.session_state.webdev_messages:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])

        if prompt := st.chat_input("Tu consulta de desarrollo...", key="webdev_input"):
            st.session_state.webdev_messages.append({"role": "user", "content": prompt})
            with chat_c:
                with st.chat_message("user"):
                    st.markdown(prompt)
                with st.chat_message("assistant"):
                    with st.spinner("🧠 Ull-Trone procesando..."):
                        # Enriquecer el prompt con la directiva de dev
                        prompt_enriquecido = f"[MODO ARQUITECTO WEB]\n{WEB_DEV_DIRECTIVE}\n\nConsulta: {prompt}"
                        response = ask_ultron(
                            DB_PATH, prompt_enriquecido,
                            st.session_state.user_login,
                            api_key=st.session_state.get('gemini_api_key', '')
                        )
                        resp_content = response.get("content", "No se pudo obtener respuesta.")
                    st.markdown(resp_content)
                    st.session_state.webdev_messages.append({"role": "assistant", "content": resp_content})

        if st.button("🗑️ Limpiar historial Dev", key="clear_webdev"):
            st.session_state.webdev_messages = [st.session_state.webdev_messages[0]]
            st.rerun()

    # ── SUBTAB 2: Evaluador de Stack Tech ───────────────────────────────────────
    with subtab_stack:
        st.markdown("#### 🔬 Comparador de Stacks Tecnológicos")
        st.caption("Analiza qué tecnología usar según tu proyecto.")

        for nombre_stack, info in STACKS_POPULARES.items():
            with st.expander(nombre_stack):
                st.markdown(f"**{info['desc']}**")
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown("**✅ Ventajas:**")
                    for pro in info['pros']:
                        st.markdown(f"- {pro}")
                with c2:
                    st.markdown("**⚠️ Consideraciones:**")
                    for con in info['contras']:
                        st.markdown(f"- {con}")
                st.info(f"🎯 **Ideal para:** {info['ideal_para']}")

        st.divider()
        st.markdown("#### 🤖 ¿Cuál Stack te conviene? Pregunta a Ull-Trone")
        req = st.text_area(
            "Describe tu proyecto brevemente:",
            placeholder="Ej: Quiero crear un portal de clientes con login, dashboard de reportes y exportación a PDF. Tengo equipo Python."
        )
        if st.button("🧠 Analizar y Recomendar Stack", use_container_width=True, key="btn_stack"):
            if req.strip():
                prompt_stack = (
                    f"[ANÁLISIS DE STACK]\n{WEB_DEV_DIRECTIVE}\n\n"
                    f"El cliente describe su proyecto así: '{req}'\n\n"
                    "Analiza los requerimientos y recomienda el stack tecnológico óptimo. "
                    "Justifica tu elección, menciona alternativas y da un estimado de complejidad."
                )
                with st.spinner("Ull-Trone analizando requerimientos..."):
                    resp = ask_ultron(DB_PATH, prompt_stack, st.session_state.user_login,
                                     api_key=st.session_state.get('gemini_api_key', ''))
                st.markdown(resp.get("content", ""))
            else:
                st.warning("Describe tu proyecto para obtener recomendación.")

    # ── SUBTAB 3: Templates de Código ───────────────────────────────────────────
    with subtab_templates:
        st.markdown("#### 🧱 Templates de Módulos CGT.pro")
        st.caption("Plantillas funcionales listas para usar o adaptar dentro del sistema.")

        template_sel = st.selectbox("Seleccionar template:", list(TEMPLATES_MODULO.keys()))
        if template_sel:
            st.markdown(TEMPLATES_MODULO[template_sel], unsafe_allow_html=False)

        st.divider()
        st.markdown("#### ✨ Generar Template Personalizado")
        prompt_tmpl = st.text_input(
            "¿Qué módulo necesitas?",
            placeholder="Ej: Un módulo de gestión de proveedores con CRUD y filtro por empresa"
        )
        if st.button("🚀 Generar con Ull-Trone", use_container_width=True, key="btn_template"):
            if prompt_tmpl.strip():
                p = (
                    f"[GENERADOR DE MÓDULO STREAMLIT]\n{WEB_DEV_DIRECTIVE}\n\n"
                    f"Genera el código completo de un módulo Streamlit para CGT.pro que haga: '{prompt_tmpl}'.\n"
                    "Usa la misma arquitectura del sistema: funciones render_xxx(DB_PATH, filtros), "
                    "intégralo con core.database (ejecutar_query, obtener_dataframe), "
                    "respeta el sistema de roles (session_state.role), "
                    "usa el diseño visual del sistema (var(--cgt-blue), containers con border, etc.). "
                    "Incluye comentarios en el código y el bloque de importaciones necesario."
                )
                with st.spinner("Ull-Trone generando módulo..."):
                    resp = ask_ultron(DB_PATH, p, st.session_state.user_login,
                                     api_key=st.session_state.get('gemini_api_key', ''))
                st.markdown(resp.get("content", ""))
            else:
                st.warning("Describe el módulo que necesitas.")

    # ── SUBTAB 4: Planificador de Proyecto ──────────────────────────────────────
    with subtab_planner:
        st.markdown("#### 📋 Planificador de Proyecto Web")
        st.caption("Define los requerimientos y Ull-Trone crea un plan de desarrollo completo.")

        with st.form("form_proyecto_web"):
            nombre_proyecto = st.text_input("🏷️ Nombre del Proyecto:")
            tipo_proyecto = st.selectbox(
                "Tipo de Proyecto:",
                ["Módulo interno CGT.pro", "Landing Page / Sitio Web", "App Web completa (SaaS)",
                 "Dashboard / Portal de Reportes", "API REST", "Integración / Automatización"]
            )
            descripcion = st.text_area(
                "📝 Descripción detallada:",
                placeholder="¿Qué hace el proyecto? ¿Quiénes son los usuarios? ¿Qué datos maneja? ¿Hay integraciones?"
            )
            c1, c2 = st.columns(2)
            with c1:
                plazo = st.selectbox("⏱️ Plazo estimado:", ["1 semana", "2 semanas", "1 mes", "2-3 meses", "6+ meses"])
            with c2:
                equipo = st.selectbox("👥 Tamaño del equipo:", ["Solo yo", "2 personas", "3-5 personas", "Equipo grande"])
            tech_preferida = st.text_input(
                "🔧 Tecnologías preferidas (opcional):",
                placeholder="Ej: Python, Streamlit, SQLite"
            )

            if st.form_submit_button("🚀 Generar Plan de Proyecto", use_container_width=True):
                if nombre_proyecto and descripcion:
                    prompt_plan = (
                        f"[PLANIFICADOR DE PROYECTO]\n{WEB_DEV_DIRECTIVE}\n\n"
                        f"Proyecto: {nombre_proyecto}\n"
                        f"Tipo: {tipo_proyecto}\n"
                        f"Descripción: {descripcion}\n"
                        f"Plazo: {plazo} | Equipo: {equipo}\n"
                        f"Tech preferida: {tech_preferida or 'Sin preferencia'}\n\n"
                        "Genera un plan de desarrollo completo que incluya:\n"
                        "1. Resumen ejecutivo del proyecto\n"
                        "2. Stack tecnológico recomendado con justificación\n"
                        "3. Arquitectura del sistema (diagrama textual)\n"
                        "4. Fases de desarrollo con hitos y entregables\n"
                        "5. Estructura de archivos/módulos propuesta\n"
                        "6. Riesgos técnicos y mitigaciones\n"
                        "7. Estimado de horas por fase\n"
                        "8. Próximos pasos concretos (esta semana)"
                    )
                    with st.spinner("📋 Ull-Trone elaborando plan de proyecto..."):
                        resp = ask_ultron(DB_PATH, prompt_plan, st.session_state.user_login,
                                         api_key=st.session_state.get('gemini_api_key', ''))
                    st.markdown("---")
                    st.markdown(f"## 🗺️ Plan: {nombre_proyecto}")
                    st.markdown(resp.get("content", "No se pudo generar el plan."))
                else:
                    st.warning("Completa al menos el nombre y la descripción del proyecto.")
