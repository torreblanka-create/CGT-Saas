# CGT SaaS - Forced Reload v1.5.3 (UI Update)
import base64
import os
import random
from datetime import datetime

import bcrypt
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from src.infrastructure.archivos import asegurar_estructura_base

# --- 1. IMPORTACIONES DEL NÚCLEO (CORE) ---
from config.config import (
    DB_PATH,
    DB_PATH_GLOBAL,
    LOGO_APP,
    LOGO_CLIENTE,
    LOGO_PORTADA,
    SUPPORT_DIR,
    UI_CATEGORY_MAPPING,
    obtener_logo_cliente,
    get_tenant_db_path,
)
from config.themes import (
    get_global_css,
    get_current_theme,
)
from src.infrastructure.database import (
    cargar_usuarios,
    ejecutar_query,
    generar_hash,
    inicializar_base_datos,
    obtener_dataframe,
    registrar_log,
)

from routes import dispatch_view_cgt
from vistas.trazabilidad_y_gestion.terminos import render_terminos_condiciones

# --- 3. CONFIGURACIÓN ESTÉTICA Y COMPONENTES ---
# ==============================================================================
st.set_page_config(page_title="CGT - Control Gestión Total", layout="wide", page_icon="🛡️")

# Inicialización de estado para recuperación
if "show_recovery" not in st.session_state:
    st.session_state.show_recovery = False

def inyectar_estilos_cgt():
    """Capa de presentación: Centraliza toda la estética del sistema desde assets/custom.css."""
    # Lucide Icons Injector
    st.markdown('<script src="https://unpkg.com/lucide@latest"></script>', unsafe_allow_html=True)

    # Inyectar CSS dinámico del sistema de temas
    st.markdown(get_global_css(), unsafe_allow_html=True)

    css_path = os.path.join(os.path.dirname(__file__), "assets", "custom.css")
    if os.path.exists(css_path):
        with open(css_path, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    else:
        st.warning("⚠️ No se encontró el archivo de estilos (assets/custom.css)")

def inyectar_reloj_cgt():
    """Componente flotante: Reloj en tiempo real + toggle modo oscuro."""
    components.html("""
    <script>
        const doc = window.parent.document;
        if (!doc.getElementById('cgt-theme-css')) {
            const s = doc.createElement('style');
            s.id = 'cgt-theme-css';
            s.textContent = `
                .stApp, .main, [data-testid="stAppViewContainer"], [data-testid="stAppViewBlockContainer"], [data-testid="stHeader"] { transition: background 0.3s ease, color 0.3s ease !important; }
            `;
            doc.head.appendChild(s);
        }
        let r = doc.getElementById('reloj-cgt');
        if (!r) {
            r = doc.createElement('div');
            r.id = 'reloj-cgt';
            r.style.cssText = 'position:fixed; top:12px; right:20px; z-index:9999999; padding:6px 14px; border-radius:12px; display:flex; align-items:center; gap:10px; font-family:sans-serif; backdrop-filter:blur(10px); border:1px solid rgba(128,130,137,0.15); transition:all 0.3s ease;';
            r.innerHTML = '<div style="display:flex; flex-direction:column;"><div id="h-cgt" style="font-weight:700; font-size:1rem;"></div><div id="f-cgt" style="font-size:0.7rem; opacity:0.8;"></div></div><button id="btn-theme-cgt" style="border:none; background:transparent; cursor:pointer; font-size:1.2rem;">🌙</button>';
            doc.body.appendChild(r);
        }
        const btn = doc.getElementById('btn-theme-cgt');
        const isDark = () => localStorage.getItem('cgt-theme') === 'dark';
        const apply = (d) => {
            doc.documentElement.classList.toggle('cgt-dark', d);
            btn.textContent = d ? "☀️" : "🌙";
            r.style.background = d ? 'rgba(30,41,59,0.95)' : 'rgba(255,255,255,0.92)';
            r.style.color = d ? '#E2E8F0' : '#1A1D21';
        };
        btn.onclick = () => { 
            const n = !isDark(); 
            localStorage.setItem('cgt-theme', n ? 'dark' : 'light'); 
            apply(n);
        };
        apply(isDark());
        setInterval(() => {
            const n = new Date();
            const h_el = doc.getElementById('h-cgt');
            const f_el = doc.getElementById('f-cgt');
            if (h_el) h_el.innerText = n.toLocaleTimeString('es-CL');
            if (f_el) f_el.innerText = n.toLocaleDateString('es-CL',{weekday:'long',day:'numeric',month:'short'});
        }, 1000);
    </script>
    """, height=0)

def get_base64_img(path):
    if os.path.exists(path):
        import base64
        with open(path, 'rb') as f: return base64.b64encode(f.read()).decode()
    return None

# Inicialización Base (se ejecuta UNA VEZ al arrancar el servidor)
asegurar_estructura_base()
inicializar_base_datos(DB_PATH)

@st.cache_resource
def _cargar_usuarios_cached():
    """Cache de usuarios a nivel de servidor — bcrypt solo corre al arrancar."""
    return cargar_usuarios(DB_PATH)

USUARIOS = _cargar_usuarios_cached()

@st.cache_data(ttl=30)
def _query_cache(query, params=()):
    """Cache de 30 seg para queries de solo lectura frecuentes (sidebar)."""
    return obtener_dataframe(DB_PATH, query, params)

if 'logged_in' not in st.session_state:
    st.session_state.update({
        'logged_in': False, 'role': None, 'username': "", 'user_login': "",
        'empresa_id': 0, 'contrato_id': 0,
        'current_db_path': DB_PATH_GLOBAL,
        'must_accept_terms': False, 'menu_activo': "📊 Dashboard",
        'users': USUARIOS,
        'filtros': {"empresa_id": 0, "empresa_nom": None, "contrato_id": 0, "contrato_nom": None, "busqueda_global": ""}
    })

def limpiar_estado_formularios():
    """Limpia variables temporales de st.session_state para optimizar memoria."""
    # Lista de prefijos o llaves exactas que son temporales de formularios
    prefijos_a_borrar = [
        "file_", "vto_", "cond_", "f_cond_", "obs_c_", "obs_g_",
        "up_foto_", "extra_docs", "multi_masivo", "pills_", "form_em_", "form_torque",
        "risk_", "ctrl_", "q_s", "q_t", "extra_", "sim_q", "sel_pts", "nom_proc",
        "ncr_", "sgi_", "pts_", "dif_", "ev_"
    ]
    keys_to_delete = []
    for key in st.session_state.keys():
        if any(key.startswith(p) for p in prefijos_a_borrar):
            keys_to_delete.append(key)

    for key in keys_to_delete:
        del st.session_state[key]

# ==============================================================================
# --- 4. COMPONENTES DE UI Y NAVEGACIÓN ---
# ==============================================================================

def render_sidebar_cgt():
    """Sidebar modularizado con llamadas explícitas a st.sidebar para evitar errores de contexto."""
    # Logos y Perfil
    logo_actual = obtener_logo_cliente(st.session_state.filtros.get('empresa_nom'))
    if os.path.exists(LOGO_APP):
        # Espacio para el reloj fijo en la parte superior
        st.sidebar.markdown('<div style="height: 60px;"></div>', unsafe_allow_html=True)

        if LOGO_APP == logo_actual:
            st.sidebar.image(LOGO_APP, use_container_width=True)
        else:
            c1, c2 = st.sidebar.columns([0.4, 0.6])
            c1.image(LOGO_APP)
            c2.image(logo_actual)

    st.sidebar.markdown(f"""
        <div class="profile-card" style="margin-top:-10px;">
            <div class="profile-avatar">👤</div>
            <div>
                <p class="profile-name">{st.session_state.username}</p>
                <span class="profile-rol">{st.session_state.role.upper()}</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

    PILARES = {
        "📊 0. Fundamentos Base": [
            "👷 Personal",
            "🚛 Camionetas",
            "🚚 Camiones",
            "🏗️ Equipos Pesados",
            "🧰 Instrumentos",
            "⛓️ Elementos de Izaje",
            "🦺 Gestión de EPP",
            "🚨 Emergencia",
            "⚙️ Activos Asignados (Cliente)",   # ← Activos del cliente: base de datos de referencia
        ],
        "🛡️ 1. Operaciones HSE": [
            "📝 Confección ART",
            "📋 Inspecciones Terreno",
            "⚠️ Reporte de Incidentes",
            "🎓 Capacitaciones",
            "📝 Charlas 5 minutos",
            "🔥 Ingeniería & Inteligencia de Fuego"
        ],
        "⚙️ 2. Activos & Ingeniería": [
            "📊 Confiabilidad: Camionetas",
            "📊 Confiabilidad: Camiones",
            "📊 Confiabilidad: Equipos Pesados",
            "🏗️ Calculadora Izaje",
            "📑 Informes de Calidad"
        ],
        "📄 3. Gobernanza & SGI": [
            "🗺️ Mapa de Procesos ISO",
            "📄 Control Documental SGI",
            "📚 Procedimientos (PTS)",
            "📈 Indicadores SGI",
            "🤝 Revisiones de Dirección",
            "⚠️ No Conformidades (Hallazgos)",
            "📋 Planes de Brechas",
        ],
        "⚕️ 4. Salud & Vigilancia": [
            "⚕️ Protocolos MINSAL (Vigilancia)",
            "🔎 Auditoría Protocolos",
            "⚖️ DS 44 / SGSST",
            "🛡️ Certificación CPHS"
        ],
        "🔎 5. Auditorías ISO & Externas": [
            "📋 Auditoría RESSO",
            "⚖️ Auditoría DS 594",
            "⚖️ ISO 14001 (Medio Ambiente)",
            "⭐ ISO 9001 (Calidad)",
            "🛡️ ISO 45001 (Seg. y Salud)",
        ],
        "🤖 6. Ull-Trone Command": [
            "🧠 Canal Directo (Chat)",
            "📊 Analítica Predictiva",
            "🔬 Tools & Diagnóstico",
            "🩺 Salud & Dev",
            "⚙️ Núcleo Central",
        ],
    }

    with st.sidebar:
        st.markdown("<p class='gold-subtitle' style='margin-top:0;'>Alcance Operativo</p>", unsafe_allow_html=True)

        # 1. Selector de Empresa
        is_global = st.session_state.role == "Global Admin"

        if is_global:
            df_e = _query_cache("SELECT id, nombre FROM empresas")
            opciones_e = {"--- TODAS LAS EMPRESAS ---": 0}
            for _, r in df_e.iterrows(): opciones_e[r['nombre']] = r['id']

            lista_nombres = list(opciones_e.keys())
            nom_actual = st.session_state.filtros.get('empresa_nom')
            default_idx = lista_nombres.index(nom_actual) if nom_actual in lista_nombres else 0

            sel_e = st.selectbox("Empresa:", lista_nombres, index=default_idx, label_visibility="collapsed")
            st.session_state.filtros.update({'empresa_id': opciones_e[sel_e], 'empresa_nom': sel_e})
        else:
            df_mi_e = _query_cache("SELECT nombre FROM empresas WHERE id = ?", (st.session_state.empresa_id,))
            mi_empresa = df_mi_e.iloc[0]['nombre'] if not df_mi_e.empty else "N/A"
            st.info(f"🏢 {mi_empresa}")
            st.session_state.filtros.update({'empresa_id': st.session_state.empresa_id, 'empresa_nom': mi_empresa})

        # 2. Selector de Contrato
        id_emp_actual = st.session_state.filtros['empresa_id']
        df_c = _query_cache("SELECT id, nombre_contrato FROM contratos WHERE empresa_id = ?", (id_emp_actual,))

        if st.session_state.role in ["Admin", "Visita", "Global Admin"]:
            if st.session_state.role == "Visita" and st.session_state.contrato_id > 0:
                 df_mi_c = _query_cache("SELECT nombre_contrato FROM contratos WHERE id = ?", (st.session_state.contrato_id,))
                 mi_contrato = df_mi_c.iloc[0]['nombre_contrato'] if not df_mi_c.empty else "Contrato No Definido - Contacte Soporte"
                 st.info(f"📝 {mi_contrato}")
                 st.session_state.filtros.update({'contrato_id': st.session_state.contrato_id, 'contrato_nom': mi_contrato})
            else:
                opciones_c = {"TODOS LOS CONTRATOS": 0}
                for _, r in df_c.iterrows(): opciones_c[r['nombre_contrato']] = r['id']

                # Intentar pre-seleccionar el contrato del filtro si existe
                lista_n_c = list(opciones_c.keys())
                con_actual = st.session_state.filtros.get('contrato_nom')
                def_idx_c = lista_n_c.index(con_actual) if con_actual in lista_n_c else 0

                sel_c = st.sidebar.selectbox("Contrato:", lista_n_c, index=def_idx_c, label_visibility="collapsed")
                st.session_state.filtros.update({'contrato_id': opciones_c[sel_c], 'contrato_nom': None if sel_c == "TODOS LOS CONTRATOS" else sel_c})
        else:
            # Para Cargador, forzar el uso del contrato_id asignado
            df_mi_c = obtener_dataframe(DB_PATH, "SELECT nombre_contrato FROM contratos WHERE id = ?", (st.session_state.contrato_id,))
            if df_mi_c.empty and st.session_state.contrato_id > 0:
                mi_contrato = "Contrato Inexistente"
            else:
                mi_contrato = df_mi_c.iloc[0]['nombre_contrato'] if not df_mi_c.empty else "Contrato No Definido - Contacte Soporte"

            st.info(f"📝 {mi_contrato}")
            st.session_state.filtros.update({'contrato_id': st.session_state.contrato_id, 'contrato_nom': mi_contrato})

        st.divider()

        # --- NAVEGACIÓN CON CONTROL DE ACCESO POR ROL ---
        # Matriz de permisos:
        # Global Admin  → todo sin restricción
        # Admin         → todo su empresa (todos los pilares + Ull-Trone + Gestión Usuarios empresa)
        # Cargador      → Fundamentos Base + Operaciones HSE (carga por contrato asignado)
        # Rigger        → Solo Equipos Pesados + Izaje + Calculadora Izaje
        # Auditor       → Lectura de todos los pilares + PDF. Sin crear/editar/Ull-Trone/Usuarios
        # Visita        → Solo Dashboard + descarga PDF estado activos de su contrato

        st.markdown("<p class='gold-subtitle'>Estructura de Mando</p>", unsafe_allow_html=True)
        st.session_state.current_db_path = DB_PATH_GLOBAL

        rol = st.session_state.role

        # Módulos que Rigger puede ver dentro de Fundamentos Base
        MODULOS_RIGGER = {"⛓️ Elementos de Izaje", "🏗️ Equipos Pesados"}

        # Pilares que Auditor ve (todos, solo lectura — control en las vistas)
        PILARES_AUDITOR = list(PILARES.keys())

        # ── Dashboard: todos lo ven ──────────────────────────────────────────
        if st.sidebar.button("📊 Dashboard", use_container_width=True,
                             type="primary" if st.session_state.menu_activo == "📊 Dashboard" else "secondary"):
            st.session_state.menu_activo = "📊 Dashboard"
            st.rerun()

        # ── Centro de Control: todos excepto Visita ──────────────────────────
        if rol != "Visita":
            if st.sidebar.button("🗂️ Centro de Control", use_container_width=True,
                                 type="primary" if st.session_state.menu_activo == "🗂️ Centro de Control" else "secondary"):
                st.session_state.menu_activo = "🗂️ Centro de Control"
                st.rerun()

        # ── Pilares de módulos ───────────────────────────────────────────────
        if rol in ("Global Admin", "Admin", "Cargador", "Auditor"):
            # Cargador solo ve pilares 0 y 1
            pilares_visibles = PILARES if rol in ("Global Admin", "Admin", "Auditor") else {
                k: v for k, v in PILARES.items()
                if k in ("📊 0. Fundamentos Base", "🛡️ 1. Operaciones HSE")
            }
            for pillar_name, modules in pilares_visibles.items():
                is_active_pillar = st.session_state.menu_activo in modules or st.session_state.menu_activo == pillar_name
                if st.sidebar.button(pillar_name, key=f"p_{pillar_name}", use_container_width=True,
                                     type="primary" if st.session_state.menu_activo == pillar_name else "secondary"):
                    st.session_state.menu_activo = pillar_name
                    st.rerun()
                if is_active_pillar:
                    for mod in modules:
                        col_indent, col_mod = st.sidebar.columns([0.15, 0.85])
                        with col_mod:
                            if st.button(mod, key=f"m_{mod}", use_container_width=True,
                                         type="primary" if st.session_state.menu_activo == mod else "secondary"):
                                st.session_state.menu_activo = mod
                                st.rerun()

        elif rol == "Rigger":
            # Rigger: solo Equipos Pesados + Izaje dentro de Fundamentos Base
            pillar_name = "📊 0. Fundamentos Base"
            is_active_pillar = st.session_state.menu_activo in MODULOS_RIGGER or st.session_state.menu_activo == pillar_name
            if st.sidebar.button(pillar_name, key=f"p_{pillar_name}", use_container_width=True,
                                 type="primary" if st.session_state.menu_activo == pillar_name else "secondary"):
                st.session_state.menu_activo = pillar_name
                st.rerun()
            if is_active_pillar:
                for mod in MODULOS_RIGGER:
                    col_indent, col_mod = st.sidebar.columns([0.15, 0.85])
                    with col_mod:
                        if st.button(mod, key=f"m_{mod}", use_container_width=True,
                                     type="primary" if st.session_state.menu_activo == mod else "secondary"):
                            st.session_state.menu_activo = mod
                            st.rerun()
            # Calculadora de izaje en Activos & Ingeniería
            if st.sidebar.button("🏗️ Calculadora Izaje", use_container_width=True,
                                 type="primary" if st.session_state.menu_activo == "🏗️ Calculadora Izaje" else "secondary"):
                st.session_state.menu_activo = "🏗️ Calculadora Izaje"
                st.rerun()


        # ── Administración y Soporte ─────────────────────────────────────────
        # Visita no tiene sección de administración
        if rol != "Visita":
            st.markdown("<p class='gold-subtitle'>Soporte</p>", unsafe_allow_html=True)
            is_admin_mod = st.session_state.menu_activo in ["📚 Soporte", "👤 Mi Perfil", "👥 Gestión de Usuarios", "⚙️ Mantenimiento"]
            with st.sidebar.expander("🛠️ Gestión y Soporte", expanded=is_admin_mod):
                if st.button("📚 Soporte", use_container_width=True,
                             type="primary" if st.session_state.menu_activo == "📚 Soporte" else "secondary"):
                    st.session_state.menu_activo = "📚 Soporte"
                    st.rerun()
                if st.button("👤 Mi Perfil", use_container_width=True,
                             type="primary" if st.session_state.menu_activo == "👤 Mi Perfil" else "secondary"):
                    st.session_state.menu_activo = "👤 Mi Perfil"
                    st.rerun()
                # Gestión de usuarios: Admin ve solo su empresa, Global Admin ve todos
                if rol in ("Admin", "Global Admin"):
                    if st.button("👥 Usuarios", use_container_width=True,
                                 type="primary" if st.session_state.menu_activo == "👥 Gestión de Usuarios" else "secondary"):
                        st.session_state.menu_activo = "👥 Gestión de Usuarios"
                        st.rerun()
                # Mantenimiento del sistema: solo Global Admin
                if rol == "Global Admin":
                    if st.button("⚙️ Mant.", use_container_width=True,
                                 type="primary" if st.session_state.menu_activo == "⚙️ Mantenimiento" else "secondary"):
                        st.session_state.menu_activo = "⚙️ Mantenimiento"
                        st.rerun()
                    if st.button("🚀 Panel Tecktur", use_container_width=True,
                                 type="primary" if st.session_state.menu_activo == "🚀 Panel Tecktur" else "secondary"):
                        st.session_state.menu_activo = "🚀 Panel Tecktur"
                        st.rerun()

        st.divider()
        if st.sidebar.button("🚪 Cerrar Sesión", use_container_width=True):
            registrar_log(DB_PATH, st.session_state.user_login, "LOGOUT", "Usuario cerró sesión manualmente")
            st.session_state.logged_in = False
            st.rerun()

# (Router extraído a routes.py)

from intelligence.agents.backup_engine import gestionar_backup_automatico

# ==============================================================================
# --- 5. FLUJO PRINCIPAL ---
# ==============================================================================
def run_cgt_app():
    inyectar_estilos_cgt()
    inyectar_reloj_cgt()

    try: gestionar_backup_automatico(DB_PATH)
    except: pass

    if not st.session_state.logged_in:
        # ── 1. Selección Aleatoria de Fondo ──
        bg_dir = os.path.join(os.path.dirname(__file__), "assets", "backgrounds")
        bg_files = [f for f in os.listdir(bg_dir) if f.endswith(('.png', '.jpg', '.jpeg'))] if os.path.exists(bg_dir) else []
        
        if bg_files:
            bg_path = os.path.join(bg_dir, random.choice(bg_files))
            b64_bg = get_base64_img(bg_path)
        else:
            b64_bg = get_base64_img(LOGO_PORTADA) # Fallback

        b64_logo = get_base64_img(LOGO_APP)
        
        # Inyectar estilos específicos para login
        st.markdown(f"""
            <style>
            [data-testid="stAppViewContainer"] {{
                background: linear-gradient(rgba(15, 23, 42, 0.4), rgba(15, 23, 42, 0.4)), url("data:image/png;base64,{b64_bg}") center/cover no-repeat !important;
                background-attachment: fixed !important;
            }}
            header, [data-testid="stSidebar"], [data-testid="stHeader"] {{ visibility: hidden !important; }}
            
            /* Animación de entrada para el login */
            .stForm {{
                animation: fadeIn 0.8s ease-out;
            }}
            @keyframes fadeIn {{
                from {{ opacity: 0; transform: translateY(20px); }}
                to {{ opacity: 1; transform: translateY(0); }}
            }}
            </style>
        """, unsafe_allow_html=True)

        _, c, _ = st.columns([1, 1.5, 1]) # Columnas ajustadas para el nuevo ancho del form
        with c:
            with st.form("login_premium", border=False):
                # Header personalizado
                st.markdown(f"""
                    <div class="login-header">
                        <img src="data:image/png;base64,{b64_logo}" class="login-logo">
                        <h1 class="login-title">CGT Pro</h1>
                        <p class="login-subtitle">Sistema de Control de Gestión Total - Elite SaaS</p>
                    </div>
                """, unsafe_allow_html=True)
                
                # Campos de entrada
                username = st.text_input("Identificador de Usuario", placeholder="Ej: j.perez")
                password = st.text_input("Clave de Acceso", type="password", placeholder="••••••••")
                
                st.markdown('<div style="height: 10px;"></div>', unsafe_allow_html=True)
                
                # Botón con clase personalizada via CSS inyectado en assets
                submit = st.form_submit_button("Ingresar al Portal", use_container_width=True, type="primary")
                
                if submit:
                    login_input = username.strip().lower()
                    u = None
                    for usr_key, usr_val in st.session_state.users.items():
                        if usr_key.lower() == login_input: 
                            u = usr_val
                            username = usr_key
                            break
                    
                    if u and bcrypt.checkpw(password.encode('utf-8'), u['pw'].encode('utf-8')):
                        st.session_state.update({
                            'logged_in': True, 'role': u["rol"], 'username': u["nombre"], 'user_login': username,
                            'empresa_id': u.get("empresa_id", 0), 'contrato_id': u.get("contrato_asignado_id", 0),
                            'must_accept_terms': (u.get("terminos_aceptados", 0) == 0)
                        })
                        registrar_log(DB_PATH, username, "LOGIN", "Acceso exitoso")
                        st.rerun()
                    else:
                        st.error("Credenciales inválidas. Por favor intente de nuevo.")
        st.stop()

    if st.session_state.must_accept_terms:
        render_terminos_condiciones(DB_PATH, st.session_state.user_login)
        st.stop()

    render_sidebar_cgt()
    dispatch_view_cgt(st.session_state.menu_activo)

if __name__ == "__main__":
    run_cgt_app()
