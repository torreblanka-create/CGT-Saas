import streamlit as st
from datetime import datetime
from vistas.ui_components import render_pillar_grid, render_glass_metric
from src.infrastructure.database import obtener_dataframe

# ─────────────────────────────────────────────────────────────────────────────
# PILAR 0: Fundamentos Base — Trinity + Activos del Cliente
# ─────────────────────────────────────────────────────────────────────────────
def render_landing_fundamentos_base(db_path, filtros):
    st.markdown("<h3 style='color: #64748b; margin-bottom: 0px;'>Telemetría en Tiempo Real</h3>", unsafe_allow_html=True)
    
    # Queries
    query_p = "SELECT COUNT(DISTINCT identificador) as c FROM registros WHERE categoria='Personal'"
    query_v = "SELECT COUNT(DISTINCT identificador) as c FROM registros WHERE categoria IN ('Vehiculo_Liviano', 'Camion_Transporte', 'Equipo_Pesado')"
    query_e = "SELECT COUNT(DISTINCT identificador) as c FROM registros WHERE categoria='EPP'"
    
    df_p = obtener_dataframe(db_path, query_p)
    df_v = obtener_dataframe(db_path, query_v)
    df_e = obtener_dataframe(db_path, query_e)
    
    total_personal = df_p['c'].iloc[0] if not df_p.empty else 0
    total_vehiculos = df_v['c'].iloc[0] if not df_v.empty else 0
    total_epp = df_e['c'].iloc[0] if not df_e.empty else 0
    
    col1, col2, col3, col4 = st.columns(4)
    with col1: render_glass_metric("Personal Enrolado", total_personal, "👷", "#3b82f6")
    with col2: render_glass_metric("Vehículos Activos", total_vehiculos, "🚛", "#a855f7")
    with col3: render_glass_metric("EPP Críticos", total_epp, "🦺", "#10b981")
    with col4: render_glass_metric("Estado Sistema", "Operativo", "🚨", "#f59e0b")
    st.divider()

    modules = [
        {"label": "👷 Personal",                  "icon": "👷", "desc": "Trazabilidad de perfiles, cargos y habilitación laboral.",           "route": "👷 Personal"},
        {"label": "🚛 Camionetas",                 "icon": "🚛", "desc": "Expedientes técnicos y trazabilidad de vehículos livianos.",         "route": "🚛 Camionetas"},
        {"label": "🚚 Camiones",                   "icon": "🚚", "desc": "Trazabilidad de transporte y logística pesada.",                      "route": "🚚 Camiones"},
        {"label": "🏗️ Equipos Pesados",            "icon": "🏗️", "desc": "Komatsu WA500/600, excavadoras y maquinaria de movimiento.",         "route": "🏗️ Equipos Pesados"},
        {"label": "🧰 Instrumentos",               "icon": "🧰", "desc": "Gestión de calibración y vigencia de equipos de medida.",            "route": "🧰 Instrumentos"},
        {"label": "⛓️ Elementos de Izaje",         "icon": "⛓️", "desc": "Control de aparejos, certificaciones y estado de carga.",            "route": "⛓️ Elementos de Izaje"},
        {"label": "🦺 Gestión de EPP",            "icon": "🦺", "desc": "Control de certificaciones de EPP (Dieléctricos, Líneas de Vida).",   "route": "🦺 Gestión de EPP"},
        {"label": "🚨 Emergencia",                 "icon": "🚨", "desc": "Recursos y trazabilidad de equipamiento crítico de emergencia.",      "route": "🚨 Emergencia"},
        {"label": "⚙️ Activos Asignados (Cliente)","icon": "⚙️", "desc": "Expediente técnico de activos críticos asignados por el cliente.",  "route": "⚙️ Activos Asignados (Cliente)"},
    ]
    render_pillar_grid("0. Fundamentos Base", "Base de datos maestra de activos y personas que alimenta todo el sistema.", modules)

# ─────────────────────────────────────────────────────────────────────────────
# PILAR 1: Operaciones HSE
# ─────────────────────────────────────────────────────────────────────────────
def render_landing_operaciones_hse(db_path, filtros):
    st.markdown("<h3 style='color: #64748b; margin-bottom: 0px;'>Telemetría Operacional</h3>", unsafe_allow_html=True)
    
    hoy_str = datetime.now().strftime("%Y-%m-%d")
    mes_str = datetime.now().strftime("%Y-%m")
    
    q_art = "SELECT COUNT(*) as c FROM registros_art WHERE fecha = ?"
    q_insp = "SELECT COUNT(*) as c FROM checklists_registros WHERE strftime('%Y-%m', fecha) = ?"
    q_inc = "SELECT COUNT(*) as c FROM reportes_incidentes WHERE strftime('%Y-%m', fecha) = ?"
    
    df_art = obtener_dataframe(db_path, q_art, (hoy_str,))
    df_insp = obtener_dataframe(db_path, q_insp, (mes_str,))
    df_inc = obtener_dataframe(db_path, q_inc, (mes_str,))
    
    total_art = df_art['c'].iloc[0] if not df_art.empty else 0
    total_insp = df_insp['c'].iloc[0] if not df_insp.empty else 0
    total_inc = df_inc['c'].iloc[0] if not df_inc.empty else 0
    
    col1, col2, col3 = st.columns(3)
    with col1: render_glass_metric("ARTs Hoy", total_art, "📝", "#3b82f6")
    with col2: render_glass_metric("Inspecciones (Mes)", total_insp, "📋", "#10b981")
    with col3: render_glass_metric("Incidentes (Mes)", total_inc, "⚠️", "#ef4444")
    st.divider()

    modules = [
        {"label": "📝 Confección ART",        "icon": "📝", "desc": "Análisis de Riesgos del Trabajo en terreno.",                  "route": "📝 Confección ART"},
        {"label": "📋 Inspecciones Terreno",  "icon": "📋", "desc": "Chequeos rápidos y evidencias de campo.",                      "route": "📋 Inspecciones Terreno"},
        {"label": "⚠️ Reporte de Incidentes", "icon": "⚠️", "desc": "Notificación de cuasi-accidentes y fallas.",                   "route": "⚠️ Reporte de Incidentes"},
        {"label": "🎓 Capacitaciones",        "icon": "🎓", "desc": "Gestión de competencias, programas y asistencia.",              "route": "🎓 Capacitaciones"},
        {"label": "📢 Charlas 5 minutos",     "icon": "📢", "desc": "Registro de charlas de 5 min y comunicaciones de turno.",       "route": "📝 Charlas 5 minutos"},
        {"label": "🔥 Ingeniería de Fuego",   "icon": "🔥", "desc": "Cálculo de carga combustible y gestión de planimetría técnica.", "route": "🔥 Ingeniería & Inteligencia de Fuego"},
    ]
    render_pillar_grid("1. Operaciones HSE", "Gestión proactiva de la seguridad y control de riesgos en faena.", modules)

# ─────────────────────────────────────────────────────────────────────────────
# PILAR 2: Activos & Ingeniería — Confiabilidad segmentada por tipo
# ─────────────────────────────────────────────────────────────────────────────
def render_landing_activos_ingenieria(db_path, filtros):
    st.markdown("<h3 style='color: #64748b; margin-bottom: 0px;'>Telemetría de Activos</h3>", unsafe_allow_html=True)
    
    q_mant = "SELECT COUNT(*) as c FROM eventos_confiabilidad WHERE strftime('%Y-%m', fecha) = ?"
    mes_str = datetime.now().strftime("%Y-%m")
    df_mant = obtener_dataframe(db_path, q_mant, (mes_str,))
    total_mant = df_mant['c'].iloc[0] if not df_mant.empty else 0
    
    col1, col2, col3 = st.columns(3)
    with col1: render_glass_metric("Confiabilidad Global", "98.5%", "⚙️", "#10b981")
    with col2: render_glass_metric("Eventos Confiabilidad", total_mant, "🔧", "#a855f7")
    with col3: render_glass_metric("Informes Calidad", "Al día", "📑", "#3b82f6")
    st.divider()

    modules = [
        {"label": "📊 Confiabilidad: Camionetas",      "icon": "🚛", "desc": "Disponibilidad mecánica y bitácora de mantención — Vehículos Livianos.",  "route": "📊 Confiabilidad: Camionetas"},
        {"label": "📊 Confiabilidad: Camiones",         "icon": "🚚", "desc": "Disponibilidad mecánica y bitácora de mantención — Transporte.",           "route": "📊 Confiabilidad: Camiones"},
        {"label": "📊 Confiabilidad: Equipos Pesados",  "icon": "🏗️", "desc": "Disponibilidad mecánica y bitácora de mantención — Maquinaria pesada.",   "route": "📊 Confiabilidad: Equipos Pesados"},
        {"label": "🏗️ Calculadora Izaje",              "icon": "🏗️", "desc": "Herramienta técnica para planificación de maniobras de izaje.",            "route": "🏗️ Calculadora Izaje"},
        {"label": "📑 Informes de Calidad",             "icon": "📑", "desc": "Gestión de registros y certificados de calidad operativa.",                 "route": "📑 Informes de Calidad"},
    ]
    render_pillar_grid("2. Activos & Ingeniería", "Control de hardware, mantenimiento predictivo y soporte técnico especializado.", modules)

# ─────────────────────────────────────────────────────────────────────────────
# PILAR 3: Gobernanza & SGI
# ─────────────────────────────────────────────────────────────────────────────
def render_landing_gobierno_sgi(db_path, filtros):
    st.markdown("<h3 style='color: #64748b; margin-bottom: 0px;'>Métricas de Gobernanza</h3>", unsafe_allow_html=True)
    
    q_nc = "SELECT COUNT(*) as c FROM sgi_no_conformidades WHERE estado != 'Cerrada'"
    df_nc = obtener_dataframe(db_path, q_nc)
    total_nc = df_nc['c'].iloc[0] if not df_nc.empty else 0
    
    col1, col2, col3 = st.columns(3)
    col1.metric("⚠️ No Conformidades Abiertas", total_nc, delta="Revisión Sugerida" if total_nc > 0 else "OK", delta_color="inverse")
    col2.metric("📄 Documentos Controlados", "Vigentes")
    col3.metric("📋 Planes de Brechas", "Activos")
    st.divider()

    modules = [
        {"label": "🗺️ Mapa de Procesos ISO",      "icon": "🗺️", "desc": "Visualización de la cadena de valor y arquitectura de procesos.",          "route": "🗺️ Mapa de Procesos ISO"},
        {"label": "📄 Control Documental SGI",    "icon": "📄", "desc": "Gestión de versiones y vigencia de documentos ISO.",                         "route": "📄 Control Documental SGI"},
        {"label": "📚 Procedimientos (PTS)",       "icon": "📚", "desc": "Repositorio de procedimientos de trabajo seguro.",                             "route": "📚 Procedimientos (PTS)"},
        {"label": "📈 Indicadores SGI",            "icon": "📊", "desc": "KPIs de desempeño del sistema de gestión integrado.",                          "route": "📈 Indicadores SGI"},
        {"label": "🤝 Revisiones de Dirección",   "icon": "🤝", "desc": "Actas y compromisos de las revisiones por la alta dirección.",                 "route": "🤝 Revisiones de Dirección"},
        {"label": "⚠️ No Conformidades",          "icon": "⚠️", "desc": "Gestión de hallazgos, causa raíz y acciones correctivas.",                    "route": "⚠️ No Conformidades (Hallazgos)"},
        {"label": "📋 Planes de Brechas",         "icon": "📋", "desc": "Seguimiento y cierre de planes de acción correctiva por contrato.",            "route": "📋 Planes de Brechas"},
        {"label": "⚖️ Auditoría DS 594",          "icon": "⚖️", "desc": "Condiciones sanitarias y ambientales básicas (DS 594).",                      "route": "⚖️ Auditoría DS 594"},
    ]
    render_pillar_grid("3. Gobernanza & SGI", "Marco normativo, estandarización y cumplimiento de compromisos contractuales.", modules)

# ─────────────────────────────────────────────────────────────────────────────
# PILAR 4: Salud & Vigilancia
# ─────────────────────────────────────────────────────────────────────────────
def render_landing_salud_vigilancia(db_path, filtros):
    st.markdown("<h3 style='color: #64748b; margin-bottom: 0px;'>Vigilancia y Auditorías</h3>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    with col1: render_glass_metric("Protocolos MINSAL", "Activos", "⚕️", "#3b82f6")
    with col2: render_glass_metric("Cumplimiento DS 44", "Evaluado", "⚖️", "#10b981")
    with col3: render_glass_metric("Certificación CPHS", "Vigente", "🛡️", "#a855f7")
    st.divider()

    modules = [
        {"label": "⚕️ Protocolos MINSAL",    "icon": "⚕️", "desc": "Vigilancia de salud y protocolos técnicos (PREXOR, PLANESI, UV, etc.).", "route": "⚕️ Protocolos MINSAL (Vigilancia)"},
        {"label": "🔎 Auditoría Protocolos", "icon": "🔎", "desc": "Verificación de cumplimiento de protocolos MINSAL en terreno.",           "route": "🔎 Auditoría Protocolos"},
        {"label": "⚖️ DS 44 / SGSST",       "icon": "⚖️", "desc": "Auditoría FUF según Decreto Supremo 44/2025 (SUSESO).",                   "route": "⚖️ DS 44 / SGSST"},
        {"label": "🛡️ Certificación CPHS",  "icon": "🛡️", "desc": "Gestión y actas del Comité Paritario de Higiene y Seguridad.",            "route": "🛡️ Certificación CPHS"},
    ]
    render_pillar_grid("4. Salud & Vigilancia", "Monitoreo de higiene ocupacional, vigilancia médica y certificación CPHS.", modules)

# ─────────────────────────────────────────────────────────────────────────────
def render_landing_inteligencia_ultron(db_path, filtros):
    st.markdown("<h3 style='color: #64748b; margin-bottom: 0px;'>Orquestador de Inteligencia</h3>", unsafe_allow_html=True)
    st.markdown("<p style='color: #94a3b8; font-size: 0.95rem; margin-bottom: 25px;'>Selecciona un área de comando para interactuar con Ull-Trone.</p>", unsafe_allow_html=True)
    
    modules = [
        {"label": "🧠 Canal Directo (Chat)", "icon": "🧠", "desc": "Interacción directa con la IA para asistencia y comandos operativos.", "route": "🧠 Canal Directo (Chat)"},
        {"label": "📊 Analítica Predictiva", "icon": "📊", "desc": "Forecast de vencimientos, analítica de datos y diagnóstico de fallas.", "route": "📊 Analítica Predictiva"},
        {"label": "🔬 Tools & Diagnóstico",  "icon": "🔬", "desc": "Validación OCR, coaching operacional y simulacros de auditoría.",   "route": "🔬 Tools & Diagnóstico"},
        {"label": "🩺 Salud & Dev",          "icon": "🩺", "desc": "Monitor de salud del sistema, resiliencia y herramientas de desarrollo.", "route": "🩺 Salud & Dev"},
        {"label": "⚙️ Núcleo Central",       "icon": "⚙️", "desc": "Configuración del cerebro LLM, memoria neural y vigilancia normativa.", "route": "⚙️ Núcleo Central"},
    ]
    render_pillar_grid("6. Inteligencia Ull-Trone", "Capacidades cognitivas de Ull-Trone v4.0 para el control total del ecosistema.", modules)

# PILAR 5: Auditorías ISO & Externas
# ─────────────────────────────────────────────────────────────────────────────
def render_landing_auditorias_normas(db_path, filtros):
    st.markdown("<h3 style='color: #64748b; margin-bottom: 0px;'>Cumplimiento Normativo Externo</h3>", unsafe_allow_html=True)
    modules = [
        {"label": "📋 Auditoría RESSO",            "icon": "📋", "desc": "Reglamento Especial de Seguridad y Salud Ocupacional (Codelco).",  "route": "📋 Auditoría RESSO"},
        {"label": "⚖️ Auditoría DS 594",          "icon": "⚖️", "desc": "Condiciones sanitarias y ambientales básicas en los lugares de trabajo.", "route": "⚖️ Auditoría DS 594"},
        {"label": "🌿 ISO 14001 (Ambiente)",       "icon": "🌿", "desc": "Auditoría de gestión ambiental según norma ISO 14001.",            "route": "⚖️ ISO 14001 (Medio Ambiente)"},
        {"label": "⭐ ISO 9001 (Calidad)",          "icon": "⭐", "desc": "Auditoría de sistema de gestión de calidad ISO 9001.",             "route": "⭐ ISO 9001 (Calidad)"},
        {"label": "🛡️ ISO 45001 (SST)",            "icon": "🛡️", "desc": "Auditoría de seguridad y salud ocupacional ISO 45001.",           "route": "🛡️ ISO 45001 (Seg. y Salud)"},
    ]
    render_pillar_grid("5. Auditorías ISO & Externas", "Verificación formal de cumplimiento de estándares internacionales y normas contractuales externas.", modules)
