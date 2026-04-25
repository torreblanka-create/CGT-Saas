# CGT Routes - Forced Reload v1.5.3 (UI Update)
import streamlit as st

from config.config import LOGO_APP, DB_PATH_GLOBAL, obtener_logo_cliente, SUPPORT_DIR

# --- IMPORTACIONES DE VISTAS (UI) - Con manejo de excepciones ---
from vistas.control_operativo.landing import render_landing_control_operativo
from vistas.control_operativo.gestion_capacitaciones import render_gestion_capacitaciones
from vistas.gestion_preventiva.auditoria_resso import render_auditoria_resso
from vistas.gestion_preventiva.cumplimiento_normativo import render_cumplimiento_normativo
from vistas.gestion_preventiva.gestion_art import render_gestion_art
from vistas.gestion_preventiva.gestion_incidentes import render_gestion_incidentes
from vistas.gestion_preventiva.inspecciones import render_inspecciones
from vistas.gestion_preventiva.registros_comunicaciones import render_registros_comunicaciones
from vistas.ingenieria_y_operaciones.activos_asignados import render_activos_asignados
from vistas.ingenieria_y_operaciones.calculadora_izaje import render_calculadora_izaje
from vistas.ingenieria_y_operaciones.confiabilidad import render_confiabilidad_activos
from vistas.ingenieria_y_operaciones.informes_calidad import render_informes_calidad
from vistas.ingenieria_y_operaciones.ingenieria_confiabilidad import render_confiabilidad_energetica

# Importaciones opcionales de inteligencia
try:
    from vistas.inteligencia.auditoria_sistema import render_auditoria_sistema
    from vistas.inteligencia.chat_ultron import render_chat_ultron
    from vistas.inteligencia.dashboard_maestro import render_dashboard_maestro
    from vistas.inteligencia.inbox_ultron import render_inbox_ultron
except (ImportError, ModuleNotFoundError):
    render_auditoria_sistema = None
    render_chat_ultron = None
    render_dashboard_maestro = None
    render_inbox_ultron = None

from vistas.landing_dashboards import (
    render_landing_operaciones_hse,
    render_landing_activos_ingenieria,
    render_landing_gobierno_sgi,
    render_landing_salud_vigilancia,
    render_landing_inteligencia_ultron,
    render_landing_auditorias_normas,
    render_landing_fundamentos_base
)
from vistas.salud_ocupacional.auditoria_ds44 import render_auditoria_ds44
from vistas.salud_ocupacional.auditoria_cphs import render_auditoria_cphs
from vistas.salud_ocupacional.auditoria_minsal import render_auditoria_minsal
from vistas.salud_ocupacional.dashboard import render_salud_ocupacional

# Importaciones opcionales de SGI
try:
    from vistas.sgi.control_documental import render_control_documental_sgi
    from vistas.sgi.indicadores_sgi import render_indicadores_sgi
    from vistas.sgi.mapa_procesos import render_mapa_procesos
    from vistas.sgi.no_conformidades import render_no_conformidades
    from vistas.sgi.revision_direccion import render_revision_direccion
except (ImportError, ModuleNotFoundError):
    render_control_documental_sgi = None
    render_indicadores_sgi = None
    render_mapa_procesos = None
    render_no_conformidades = None
    render_revision_direccion = None

from vistas.sistema.mantenimiento import render_mantenimiento
from vistas.sistema.usuarios import render_gestion_usuarios
from vistas.operaciones.fire_intelligence import render_fire_intelligence
from vistas.trazabilidad.trazabilidad_emergencia import render_trazabilidad_emergencia
from vistas.trazabilidad.trazabilidad_instrumentos import render_trazabilidad_instrumentos
from vistas.trazabilidad.trazabilidad_izaje import render_trazabilidad_izaje
from vistas.trazabilidad.trazabilidad_personal import render_trazabilidad_personal
from vistas.trazabilidad.trazabilidad_epp import render_trazabilidad_epp
from vistas.trazabilidad.trazabilidad_vehiculos import render_trazabilidad_vehiculos
from vistas.trazabilidad_y_gestion.control_center import render_control_center
from vistas.trazabilidad_y_gestion.control_pts import render_control_pts
from vistas.trazabilidad_y_gestion.dashboard import render_dashboard
from vistas.trazabilidad_y_gestion.mi_perfil import render_mi_perfil
from vistas.trazabilidad_y_gestion.seguimiento_planes import render_seguimiento_planes
from vistas.trazabilidad_y_gestion.soporte import render_material_soporte
from vistas.trazabilidad_y_gestion.terminos import render_terminos_condiciones
from vistas.sistema.tecktur_admin import render_tecktur_admin

def dispatch_view_cgt(menu):
    """Router Pattern: Despacho centralizado de vistas con control de acceso por rol."""
    logo_actual = obtener_logo_cliente(st.session_state.filtros.get('empresa_nom'))
    filtros = st.session_state.filtros
    active_db = st.session_state.get('current_db_path', DB_PATH_GLOBAL)
    rol = st.session_state.get('role', '')

    # ── Guard de acceso: vistas restringidas por rol ────────────────────────
    # Si el menú solicitado no corresponde al rol, redirigir al Dashboard
    SOLO_ADMIN = {
        "🤖 Ull-Trone", "🤖 Ull-Trone Inteligente", "📊 Dashboard Maestro",
        "🛡️ Auditoría del Sistema", "🔔 Alertas",
        "🧠 Canal Directo (Chat)", "📊 Analítica Predictiva", "🔬 Tools & Diagnóstico",
        "🩺 Salud & Dev", "⚙️ Núcleo Central"
    }
    SOLO_ADMIN_USUARIOS = {"👥 Gestión de Usuarios"}
    SOLO_GLOBAL = {"⚙️ Mantenimiento"}
    NO_VISITA = {
        "🗂️ Centro de Control", "👷 Personal", "🚛 Camionetas", "🚚 Camiones",
        "🏗️ Equipos Pesados", "🧰 Instrumentos", "⛓️ Elementos de Izaje",
        "🦺 Gestión de EPP", "🚨 Emergencia", "⚙️ Activos Asignados (Cliente)",
        "📝 Confección ART", "📋 Inspecciones Terreno", "⚠️ Reporte de Incidentes",
        "🎓 Capacitaciones", "📝 Charlas 5 minutos", "🔥 Ingeniería & Inteligencia de Fuego",
        "📊 Confiabilidad: Camionetas", "📊 Confiabilidad: Camiones",
        "📊 Confiabilidad: Equipos Pesados", "🏗️ Calculadora Izaje", "📑 Informes de Calidad",
        "🗺️ Mapa de Procesos ISO", "📄 Control Documental SGI", "📚 Procedimientos (PTS)",
        "📈 Indicadores SGI", "🤝 Revisiones de Dirección", "⚠️ No Conformidades (Hallazgos)",
        "📋 Planes de Brechas", "⚖️ Auditoría DS 594", "📋 Auditoría RESSO",
        "⚖️ ISO 14001 (Medio Ambiente)", "⭐ ISO 9001 (Calidad)", "🛡️ ISO 45001 (Seg. y Salud)",
        "⚕️ Protocolos MINSAL (Vigilancia)", "🔎 Auditoría Protocolos",
        "⚖️ DS 44 / SGSST", "🛡️ Certificación CPHS"
    }
    MODULOS_RIGGER = {"⛓️ Elementos de Izaje", "🏗️ Equipos Pesados", "🏗️ Calculadora Izaje"}
    MODULOS_CARGADOR = {
        "🗂️ Centro de Control", "👷 Personal", "🚛 Camionetas", "🚚 Camiones",
        "🏗️ Equipos Pesados", "🧰 Instrumentos", "⛓️ Elementos de Izaje",
        "🦺 Gestión de EPP", "🚨 Emergencia", "⚙️ Activos Asignados (Cliente)",
        "📝 Confección ART", "📋 Inspecciones Terreno", "⚠️ Reporte de Incidentes",
        "🎓 Capacitaciones", "📝 Charlas 5 minutos",
        "📊 Dashboard", "👤 Mi Perfil", "📚 Soporte"
    }
    # Vistas base que todos ven
    BASE_TODAS = {"📊 Dashboard", "👤 Mi Perfil", "📚 Soporte"}

    acceso_denegado = False
    if rol == "Visita" and menu in NO_VISITA:
        acceso_denegado = True
    elif rol == "Rigger" and menu not in MODULOS_RIGGER | BASE_TODAS:
        acceso_denegado = True
    elif rol == "Cargador" and menu not in MODULOS_CARGADOR:
        acceso_denegado = True
    elif rol == "Auditor" and menu in SOLO_ADMIN | SOLO_ADMIN_USUARIOS | SOLO_GLOBAL:
        acceso_denegado = True
    elif rol == "Admin" and menu in SOLO_GLOBAL:
        acceso_denegado = True
    elif rol not in ("Admin", "Global Admin") and menu in SOLO_ADMIN:
        acceso_denegado = True

    if acceso_denegado:
        st.warning("No tienes permisos para acceder a esta sección.")
        st.session_state.menu_activo = "📊 Dashboard"
        st.rerun()

    def _set_ull_mod(key):
        """Helper: pre-selecciona un módulo de Ull-Trone y activa el menu."""
        st.session_state['ull_modulo_activo'] = key
        st.session_state['menu_activo'] = "🤖 Ull-Trone"

    router = {
        "📊 Dashboard": lambda: render_dashboard(active_db, filtros, LOGO_APP, logo_actual),
        "🔔 Alertas": lambda: render_inbox_ultron(active_db, filtros),
        "📊 Dashboard Maestro": lambda: render_dashboard_maestro(active_db, filtros),
        "👤 Mi Perfil": lambda: render_mi_perfil(active_db),
        "🗂️ Centro de Control": lambda: render_control_center(active_db, filtros),
        "📊 0. Fundamentos Base": lambda: render_landing_fundamentos_base(active_db, filtros),
        "🛡️ 1. Operaciones HSE": lambda: render_landing_operaciones_hse(active_db, filtros),
        "⚙️ 2. Activos & Ingeniería": lambda: render_landing_activos_ingenieria(active_db, filtros),
        "📄 3. Gobernanza & SGI": lambda: render_landing_gobierno_sgi(active_db, filtros),
        "⚕️ 4. Salud & Vigilancia": lambda: render_landing_salud_vigilancia(active_db, filtros),
        "🤖 6. Ull-Trone Command": lambda: render_landing_inteligencia_ultron(active_db, filtros),
        "🧠 Canal Directo (Chat)": lambda: render_chat_ultron(active_db, filtros, tab_idx=0),
        "📊 Analítica Predictiva": lambda: render_chat_ultron(active_db, filtros, tab_idx=1),
        "🔬 Tools & Diagnóstico": lambda: render_chat_ultron(active_db, filtros, tab_idx=2),
        "🩺 Salud & Dev": lambda: render_chat_ultron(active_db, filtros, tab_idx=3),
        "⚙️ Núcleo Central": lambda: render_chat_ultron(active_db, filtros, tab_idx=4),
        "🛡️ Auditoría del Sistema": lambda: render_auditoria_sistema(active_db),
        "🔎 5. Auditorías ISO & Externas": lambda: render_landing_auditorias_normas(active_db, filtros),
        "👷 Personal": lambda: render_trazabilidad_personal(active_db),
        "🚛 Camionetas": lambda: render_trazabilidad_vehiculos(active_db, categoria='Vehiculo_Liviano'),
        "🚚 Camiones": lambda: render_trazabilidad_vehiculos(active_db, categoria='Camion_Transporte'),
        "🏗️ Equipos Pesados": lambda: render_trazabilidad_vehiculos(active_db, categoria='Equipo_Pesado'),
        "🧰 Instrumentos": lambda: render_trazabilidad_instrumentos(active_db),
        "⛓️ Elementos de Izaje": lambda: render_trazabilidad_izaje(active_db),
        "🦺 Gestión de EPP": lambda: render_trazabilidad_epp(active_db),
        "🚨 Emergencia": lambda: render_trazabilidad_emergencia(active_db),
        "🔥 Ingeniería & Inteligencia de Fuego": lambda: render_fire_intelligence(active_db),
        "📝 Confección ART": lambda: render_gestion_art(active_db),
        "📋 Inspecciones Terreno": lambda: render_inspecciones(active_db, filtros),
        "⚠️ Reporte de Incidentes": lambda: render_gestion_incidentes(active_db, filtros),
        "🎓 Capacitaciones": lambda: render_gestion_capacitaciones(active_db, filtros),
        "📝 Charlas 5 minutos": lambda: render_registros_comunicaciones(active_db, filtros),
        "⚙️ Activos Asignados (Cliente)": lambda: render_activos_asignados(active_db, filtros),
        "📊 Confiabilidad: Camionetas": lambda: render_confiabilidad_activos(active_db, filtros, categoria='Vehiculo_Liviano'),
        "📊 Confiabilidad: Camiones": lambda: render_confiabilidad_activos(active_db, filtros, categoria='Camion_Transporte'),
        "📊 Confiabilidad: Equipos Pesados": lambda: render_confiabilidad_activos(active_db, filtros, categoria='Equipo_Pesado'),
        "🏗️ Calculadora Izaje": lambda: render_calculadora_izaje(active_db, filtros),
        "📑 Informes de Calidad": lambda: render_informes_calidad(active_db, filtros),
        "🗺️ Mapa de Procesos ISO": lambda: render_mapa_procesos(active_db, filtros),
        "📄 Control Documental SGI": lambda: render_control_documental_sgi(active_db, filtros),
        "📚 Procedimientos (PTS)": lambda: render_control_pts(active_db, filtros),
        "📈 Indicadores SGI": lambda: render_indicadores_sgi(active_db, filtros),
        "🤝 Revisiones de Dirección": lambda: render_revision_direccion(active_db, filtros),
        "⚠️ No Conformidades (Hallazgos)": lambda: render_no_conformidades(active_db, filtros),
        "📋 Planes de Brechas": lambda: render_seguimiento_planes(active_db, filtros),
        "⚖️ Auditoría DS 594": lambda: render_cumplimiento_normativo(active_db, filtros, tipo_def="DS 594 - Condiciones Sanitarias y Ambientales"),
        "📋 Auditoría RESSO": lambda: render_auditoria_resso(active_db, filtros),
        "⚖️ ISO 14001 (Medio Ambiente)": lambda: render_cumplimiento_normativo(active_db, filtros, tipo_def="ISO 14001 - Gestión Medioambiental"),
        "⭐ ISO 9001 (Calidad)": lambda: render_cumplimiento_normativo(active_db, filtros, tipo_def="ISO 9001 - Gestión de Calidad"),
        "🛡️ ISO 45001 (Seg. y Salud)": lambda: render_cumplimiento_normativo(active_db, filtros, tipo_def="ISO 45001 - Seguridad y Salud"),
        "⚕️ Protocolos MINSAL (Vigilancia)": lambda: render_salud_ocupacional(active_db, filtros),
        "🔎 Auditoría Protocolos": lambda: render_auditoria_minsal(active_db, filtros),
        "⚖️ DS 44 / SGSST": lambda: render_auditoria_ds44(active_db, filtros),
        "🛡️ Certificación CPHS": lambda: render_auditoria_cphs(active_db, filtros),
        "📚 Soporte": lambda: render_material_soporte(SUPPORT_DIR),
        "👥 Gestión de Usuarios": lambda: render_gestion_usuarios(active_db),
        "⚙️ Mantenimiento": lambda: render_mantenimiento(active_db),
        "🚀 Panel Tecktur": lambda: render_tecktur_admin(active_db)
    }
    view = router.get(menu)
    if view: 
        view()
    else:
        st.error(f"La sección '{menu}' no tiene una función de renderizado asignada.")
