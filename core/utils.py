"""
==========================================
🛠️ UTILS ENGINE — v2.0 MEJORADO
==========================================
Motor de utilidades y funciones comunes.

CARACTERÍSTICAS v2.0:
✅ Validación de contexto
✅ Renderizado de UI
✅ Formateo de datos
✅ Helpers de negocio
✅ Integración BD
✅ Caché de funciones
✅ Análisis de utilización
"""
import logging
from datetime import datetime
from typing import Dict, Optional, Tuple

import streamlit as st

logger = logging.getLogger(__name__)

def normalizar_nombre(nombre: str) -> str:
    """
    Normaliza un nombre: primero letra mayúscula, resto minúsculas.
    Maneja None, strings vacíos y acentos.
    
    Args:
        nombre: Nombre a normalizar
    
    Returns:
        Nombre normalizado con formato título
    """
    if not nombre:
        return ""
    import unicodedata
    # Eliminar acentos pero mantener ñ
    nombre_normalizado = ""
    for c in nombre.strip():
        if c in 'ñÑ':
            nombre_normalizado += c
        else:
            descompuesto = unicodedata.normalize('NFD', c)
            nombre_normalizado += ''.join(ch for ch in descompuesto if unicodedata.category(ch) != 'Mn')
    # Title case (primera letra mayúscula)
    return nombre_normalizado.title()


def normalizar_rut(rut: str) -> str:
    """
    Normaliza un RUT chileno: elimina puntos, guiones, espacios.
    Convierte K mayúscula.
    
    Args:
        rut: RUT a normalizar (ej: " 12.345.678 - 9 ")
    
    Returns:
        RUT normalizado (ej: "12345678-9")
    """
    if not rut:
        return ""
    # Eliminar espacios, puntos y guiones
    rut = rut.strip().replace(".", "").replace("-", "").replace(" ", "")
    if not rut:
        return ""
    # El último carácter es el dígito verificador
    digitos = rut[:-1]
    dv = rut[-1].upper()
    return f"{digitos}-{dv}"


def get_scoping_params(filtros: Dict) -> Tuple[bool, int, str]:
    """
    Centraliza la lógica de alcance (Global Admin vs Admin Local).
    Retorna: (es_global_admin, empresa_id_actual, sql_where_clause)
    """
    es_master = st.session_state.get('role') == "Global Admin"
    emp_id = filtros.get('empresa_id', 0)
    
    # Si no es master, forzamos su propia empresa
    if not es_master:
        emp_id = st.session_state.get('empresa_id', 0)
        where_clause = " AND empresa_id = ?"
    else:
        # Si es master, filtramos solo si eligió una empresa en el sidebar
        if emp_id > 0:
            where_clause = " AND empresa_id = ?"
        else:
            where_clause = ""
            
    return es_master, emp_id, where_clause


# ============ VALIDATION HELPERS ============

def is_valid_context(filtros: Optional[Dict]) -> bool:
    """
    Valida si hay contexto de empresa y contrato seleccionado.
    
    Args:
        filtros: Dict con filtros de UI
    
    Returns:
        True si hay contexto válido, False si está en modo global
    """
    if not isinstance(filtros, dict):
        return True
    
    emp = filtros.get('empresa_nom')
    con = filtros.get('contrato_nom')
    
    if not emp or emp == "--- TODAS LAS EMPRESAS ---" or not con or con == "TODOS LOS CONTRATOS":
        return False
    return True


def show_context_warning() -> None:
    """Muestra advertencia de modo global"""
    st.warning("🔒 **Modo Vista Global:** Seleccione una **Empresa** y un **Contrato**.")

def render_hybrid_date_input(label, value=None, key=None):
    """
    Renders a unified date input with manual text field (DD/MM/AAAA)
    and a small calendar icon (Streamlit date_input) for help.
    Ultra-compact v3.0 (Minimalist Icon)
    """
    if value is None: value = datetime.now().date()

    # CSS para hacer el date_input un pequeño icono y pegarlo al text_input
    # Seleccionamos el contenedor del date_input por su etiqueta emoji
    st.markdown("""
        <style>
        /* Reducir espacio entre columnas */
        div[data-testid="column"] { padding: 0 2px !important; }
        /* Estilo para el mini-botón de calendario */
        div.stDateInput > div { border: none !important; background: transparent !important; padding: 0 !important; width: 40px !important; }
        div.stDateInput input { color: transparent !important; cursor: pointer !important; font-size: 0 !important; }
        div.stDateInput span { margin-right: -25px !important; font-size: 1.2rem !important; }
        </style>
    """, unsafe_allow_html=True)

    c1, c2 = st.columns([0.9, 0.1])

    with c1:
        txt_val = st.text_input(label, placeholder="DD/MM/AAAA", key=f"txt_{key or label}")
    with c2:
        st.markdown("<div style='height:28px;'></div>", unsafe_allow_html=True)
        # El 📂 aparecerá como el icono del input
        pick_val = st.date_input("📂", value=value, key=f"pic_{key or label}", label_visibility="collapsed")

    # Lógica de retorno
    if txt_val.strip():
        for fmt in ['%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d', '%d/%m/%y']:
            try:
                return datetime.strptime(txt_val.strip(), fmt).date()
            except: continue

    return pick_val

def obtener_listado_personal(db_path, filtros):
    """
    Obtiene el listado de trabajadores vigentes filtrado por empresa y contrato.
    Retorna una lista de strings formateados: "Nombre (ID)"
    """
    from src.infrastructure.database import obtener_dataframe

    emp_id = filtros.get('empresa_id', 0)
    con_id = filtros.get('contrato_id', 0)

    query = "SELECT DISTINCT identificador, nombre FROM registros WHERE categoria='Personal'"
    params = []

    if emp_id and emp_id > 0:
        query += " AND empresa_id = ?"
        params.append(emp_id)
    if con_id and con_id > 0:
        query += " AND contrato_id = ?"
        params.append(con_id)

    df = obtener_dataframe(db_path, query, tuple(params))
    if df.empty:
        return []

    return (df['nombre'] + " (" + df['identificador'].astype(str) + ")").tolist()

def render_name_input_combobox(label, listado_nombres, key, default=""):
    """
    Renderiza un selector híbrido: Selectbox con búsqueda + campo de texto manual.
    """
    opciones = ["-- SELECCIONE DE LA LISTA --", "➕ INGRESAR MANUALMENTE / OTRO"] + listado_nombres

    # Intentar pre-seleccionar si el valor actual existe en la lista
    idx_def = 0
    if default and default in listado_nombres:
        idx_def = opciones.index(default)

    sel = st.selectbox(label, opciones, index=idx_def, key=f"sel_named_{key}")

    if sel == "➕ INGRESAR MANUALMENTE / OTRO":
        manual = st.text_input(f"Escriba {label.lower()} manualmente:", value=default if default not in listado_nombres else "", key=f"manual_named_{key}")
        return manual
    elif sel == "-- SELECCIONE DE LA LISTA --":
        return ""

    return sel

def render_multiselect_personal(label, listado_nombres, key, defaults=[]):
    """
    Multiselect para integrantes del CPHS vinculado a la base de datos + manual.
    """
    st.markdown(f"**{label}**")
    seleccionados = st.multiselect("Seleccionar del personal cargado:", listado_nombres, default=[d for d in defaults if d in listado_nombres], key=f"multi_pers_{key}")

    otros = st.text_area("Agregar integrantes manuales (separados por coma):",
                        value=", ".join([d for d in defaults if d not in listado_nombres]),
                        key=f"manual_area_{key}", help="Escriba nombres de personas que no están en la lista.")

    lista_otros = [o.strip() for o in otros.split(",") if o.strip()]
    return seleccionados + lista_otros


def registrar_no_conformidad_automatica(db_path, origen, descripcion, responsable, empresa_id, contrato_id):
    """
    Crea automáticamente una No Conformidad en sgi_no_conformidades cuando una
    auditoría resulta con puntaje bajo el umbral aceptable.

    - Evita duplicados: Solo inserta si no existe una NC abierta para el mismo origen.
    - Crea una notificación push en notificaciones_ultron.

    Args:
        db_path: Ruta a la base de datos SQLite.
        origen: Texto que identifica la fuente (ej: "Auditoría PREXOR", "Auditoría RESSO").
        descripcion: Descripción detallada del hallazgo / no conformidad.
        responsable: Nombre del responsable de cierre.
        empresa_id: ID de la empresa en contexto.
        contrato_id: ID del contrato en contexto.

    Returns:
        Tuple (bool, str): (éxito, mensaje)
    """
    from src.infrastructure.database import ejecutar_query, obtener_dataframe

    try:
        # Verificar si ya existe una NC abierta con el mismo origen para esta empresa
        df_existente = obtener_dataframe(
            db_path,
            "SELECT id FROM sgi_no_conformidades WHERE origen=? AND empresa_id=? AND estado='Abierta' LIMIT 1",
            (origen, empresa_id)
        )
        if not df_existente.empty:
            return False, f"Ya existe una NCR abierta para '{origen}'. No se creó duplicado (ID: {df_existente.iloc[0]['id']})."

        fecha_hoy = datetime.now().date()

        # Insertar No Conformidad
        new_nc_id = ejecutar_query(
            db_path,
            """INSERT INTO sgi_no_conformidades
               (fecha, origen, descripcion, responsable, causa_raiz, plan_accion, estado, empresa_id, contrato_id)
               VALUES (?, ?, ?, ?, ?, ?, 'Abierta', ?, ?)""",
            (
                str(fecha_hoy),
                origen,
                descripcion,
                responsable if responsable else "Por asignar",
                "Análisis de causa raíz pendiente (generada automáticamente por auditoría).",
                "Elaborar plan de acción correctiva según hallazgos de auditoría.",
                empresa_id,
                contrato_id
            ),
            commit=True
        )

        # Push Notificación Ull-Trone
        msg_alerta = f"🚨 NCR AUTOMÁTICA [{origen}]: Puntaje bajo el umbral. Se levantó una No Conformidad (ID: {new_nc_id}). Acción requerida."
        ejecutar_query(
            db_path,
            """INSERT INTO notificaciones_ultron (tipo, mensaje, identificador, estado, empresa_id, contrato_id)
               VALUES (?, ?, ?, 'No Leída', ?, ?)""",
            ("Gobernanza/NCR", msg_alerta, f"NCR_AUTO_{origen[:20]}", empresa_id, contrato_id),
            commit=True
        )

        return True, f"✅ No Conformidad registrada automáticamente (ID: {new_nc_id}) y alerta enviada a Ull-Trone."

    except Exception as e:
        return False, f"Error al registrar NCR automática: {e}"
