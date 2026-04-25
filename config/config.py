import os

# ==========================================
# 1. RUTAS Y DIRECTORIOS DEL SISTEMA
# ==========================================
# Esto asegura que el sistema encuentre las carpetas sin importar desde dónde lo ejecutes.
BASE_PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# Directorio Principal de Datos
BASE_DATA_DIR = os.path.join(BASE_PROJECT_DIR, "CGT_DATA")

# Bases de Datos y Excel
DB_PATH_GLOBAL = os.path.join(BASE_DATA_DIR, "cgt_control.db") # Catálogo Maestro (Usuarios Globales)
DB_PATH = DB_PATH_GLOBAL # Por defecto

EXCEL_MAESTRO_PATH = os.path.join(BASE_DATA_DIR, "CGT_Master_Database.xlsx")

# Carpetas Estáticas
ASSETS_DIR = os.path.join(BASE_PROJECT_DIR, "assets")
SUPPORT_DIR = os.path.join(BASE_PROJECT_DIR, "Material de Soporte")

# Logos del Sistema
LOGO_PORTADA = os.path.join(ASSETS_DIR, "logo_portada.jpg")
LOGO_APP = os.path.join(ASSETS_DIR, "logo_app.png")
LOGO_CLIENTE = os.path.join(ASSETS_DIR, "logo_app.png") # Por defecto usa el de la app si no hay específico

def obtener_logo_cliente(empresa_nombre):
    """Obtiene dinámicamente el logo de la carpeta assets según el nombre de la empresa activa"""
    if not empresa_nombre or str(empresa_nombre).strip() in ["--- TODAS LAS EMPRESAS ---", "Otros", "EMPRESA_NO_DEFINIDA"]:
        return LOGO_APP

    s = str(empresa_nombre).strip().lower()
    import re
    import unicodedata
    s = ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')

    # Remover palabras comunes como spa, ltda, s.a. y dejar solo alfanuméricos puros
    s = re.sub(r'ltd\.?|ltda\.?|spa\.?|s\.p\.a\.?|s\.a\.?| ', '', s)
    s_clean = re.sub(r'[^a-z0-9]', '', s)

    if not s_clean: return LOGO_APP

    if os.path.exists(ASSETS_DIR):
        for file in os.listdir(ASSETS_DIR):
            f_lower = file.lower()
            if f_lower.endswith((".png", ".jpg", ".jpeg")):
                f_name = f_lower.rsplit('.', 1)[0]
                f_clean = re.sub(r'[^a-z0-9]', '', f_name)
                # Buscar si el nombre de la empresa está contenido en el nombre del archivo purificado
                if s_clean in f_clean or f_clean in s_clean:
                    return os.path.join(ASSETS_DIR, file)

    return LOGO_APP

# ==========================================
# 2. RUTAS DINÁMICAS (Multi-Empresa)
# ==========================================
def _normalize_empresa_dir_name(empresa_nom):
    """
    Retorna el nombre de CARPETA consistente para una empresa.
    Usa el nombre tal cual (con espacios) para máxima compatibilidad
    y consistencia. NUNCA normaliza con underscores para evitar
    carpetas duplicadas (ej: 'STEEL INGENIERIA' vs 'STEEL_INGENIERIA').
    """
    return str(empresa_nom).strip()

def get_scoped_path(empresa_nombre, contrato_nombre=None, modulo=None):
    """
    Genera una ruta absoluta dentro de CGT_DATA siguiendo la jerarquía:
    CGT_DATA / [Empresa] / [Contrato] / [Módulo]
    """
    path = os.path.join(BASE_DATA_DIR, _normalize_empresa_dir_name(empresa_nombre))
    if contrato_nombre:
        path = os.path.join(path, str(contrato_nombre))
    if modulo:
        path = os.path.join(path, str(modulo))

    os.makedirs(path, exist_ok=True)
    return path

def get_tenant_db_path(empresa_nom):
    """Retorna la ruta a la base de datos específica de un tenant (empresa)."""
    if not empresa_nom or empresa_nom in ("--- TODAS LAS EMPRESAS ---", "CGT"):
        return DB_PATH_GLOBAL

    # Carpeta raíz de la empresa — siempre con el nombre original (espacios incluidos)
    emp_dir = os.path.join(BASE_DATA_DIR, _normalize_empresa_dir_name(empresa_nom))
    os.makedirs(emp_dir, exist_ok=True)

    # Nombre de archivo normalizado (sin espacios, minúsculas)
    import re
    db_name = re.sub(r'[^a-zA-Z0-9]', '_', str(empresa_nom)).lower()
    return os.path.join(emp_dir, f"cgt_{db_name}.db")


# ==========================================
# 3. CONFIGURACIONES DINÁMICAS (DB)
# ==========================================
def load_dynamic_config(clave, default):
    """Carga configuración desde la DB de forma segura."""
    try:
        from src.infrastructure.database import obtener_config
        return obtener_config(DB_PATH, clave, default)
    except:
        return default

# Categorías y Mapeos
UI_CATEGORY_MAPPING = load_dynamic_config("UI_CATEGORY_MAPPING", {
    "👷 Personal": "Personal",
    "🚜 Maquinaria": "Maquinaria Pesada & Vehículos",
    "⛓️ Elementos de izaje": "Elementos de izaje",
    "🧰 Instrumentos": "Instrumentos y Metrología",
    "🚨 Emergencias": "Sistemas de Emergencia"
})

EXCEL_SHEET_MAPPING = {
    # Nuevas categorías Trinity
    "Vehiculo_Liviano":          "LISTADO_MAESTRO",
    "Camion_Transporte":         "LISTADO_MAESTRO",
    "Equipo_Pesado":             "LISTADO_MAESTRO",
    # Categorías legacy (backward-compat)
    "Personal":                  "LISTADO_MAESTRO",
    "Maquinaria Pesada & Vehículos": "LISTADO_MAESTRO",
    "Elementos de izaje":        "LISTADO_MAESTRO",
    "Instrumentos y Metrología": "LISTADO_MAESTRO",
    "Sistemas de Emergencia":    "LISTADO_MAESTRO",
    "EPP":                       "LISTADO_MAESTRO"
}

# Mapa de aliases: valor Excel → categoría interna Trinity
# Permite que datos importados con nombres viejos queden normalizados en la DB
CATEGORIA_ALIAS_MAP = {
    # Legacy → Trinity
    "maquinaria pesada & vehículos": "Equipo_Pesado",
    "maquinaria": "Equipo_Pesado",
    "vehiculo": "Vehiculo_Liviano",
    "vehiculo liviano": "Vehiculo_Liviano",
    "camioneta": "Vehiculo_Liviano",
    "camionetas": "Vehiculo_Liviano",
    "camion": "Camion_Transporte",
    "camiones": "Camion_Transporte",
    "transporte": "Camion_Transporte",
    "equipo pesado": "Equipo_Pesado",
    "maquinaria pesada": "Equipo_Pesado",
    "excavadora": "Equipo_Pesado",
    "retroexcavadora": "Equipo_Pesado",
    "minicargador": "Equipo_Pesado",
    "manipulador": "Equipo_Pesado",
    # Directas ya correctas
    "vehiculo_liviano": "Vehiculo_Liviano",
    "camion_transporte": "Camion_Transporte",
    "equipo_pesado": "Equipo_Pesado",
}

# Nombre de las columnas estándar en el Excel Unificado
COL_EXCEL_ID = "Identificador"
COL_EXCEL_NOMBRE = "Nombre"
COL_EXCEL_DETALLE = "Detalle"
COL_EXCEL_CATEGORIA = "Categoría"

# Parámetros EPP
TIPOS_EPP_GLOBAL = load_dynamic_config("TIPOS_EPP_GLOBAL", [
    "Respirador Medio Rostro (Duración: 2 años)", "Filtro Mixto (Duración: 1 mes)",
    "Guantes Anti-Golpe (Duración: 3 meses)", "Guantes Dieléctricos (Duración: 6 meses)",
    "Cubre Guantes Dieléctrico (Duración: 6 meses)", "Zapatos de Seguridad (Duración: 6 meses)",
    "Buzo Ignífugo (Duración: 6 meses)", "Camisa Ignífuga (Duración: 6 meses)",
    "Pantalón Ignífugo (Duración: 6 meses)", "Lentes Oscuros (Duración: 3 meses)",
    "Lentes Blancos (Duración: 3 meses)", "Casco de Seguridad (Duración: 5 años)",
    "Barbiquejo (Duración: 1 año)", "Legionario (Duración: 1 año)",
    "Guantes Clase 2 (Duración: 6 meses)", "Cubre Guantes (Duración: 6 meses)",
    "Guante Anti Transpirante (Duración: 1 mes)", "Bloqueador / Labial (Duración: 6 meses)",
    "Primera Capa (Duración: 6 meses)", "Bolsa para Respirador (Duración: 1 año)",
    "Bolso de Ropa (Duración: 2 años)"
])

EPP_DURATION_MAPPING = load_dynamic_config("EPP_DURATION_MAPPING", {
    "Respirador": 24, "Filtro": 1, "Guante": 3, "Zapato": 6, "Buzo": 6,
    "Camisa": 6, "Pantalon": 6, "Lentes": 3, "Casco": 60, "Barbiquejo": 12,
    "Legionario": 12, "Bloqueador": 6, "Primera Capa": 6, "Bolsa": 12, "Bolso": 24
})

# Documentos Obligatorios
DOCS_OBLIGATORIOS = load_dynamic_config("DOCS_OBLIGATORIOS", {
    "Personal": [
        "Contrato de Trabajo y Anexos", "IRL información de riesgos laborales",
        "Comprobante Entrega RIOHS", "Exámenes Médicos Pre u Ocupacionales"
    ],
    "Vehiculo_Liviano": [
        "SOAP", "Revisión técnica", "Permiso de circulación", "Mantención preventiva"
    ],
    "Camion_Transporte": [
        "SOAP", "Revisión técnica", "Permiso de circulación", "Mantención preventiva", "Certificado de torque"
    ],
    "Equipo_Pesado": [
        "Mantención preventiva", "Mantención de Pluma", "Sistema AFEX", "Certificado de torque"
    ],
    "Maquinaria Pesada & Vehículos": [
        "SOAP", "Revisión técnica", "Permiso de circulación", "Mantención preventiva"
    ],
    "Elementos de izaje": ["Certificado de operatividad (Trimestral)"],
    "Instrumentos y Metrología": ["Certificado de calibración"],
    "Sistemas de Emergencia": ["Revisión técnica anual", "Prueba hidrostática"],
    "Default": ["Documento General"]
})

# Soporte
DOCUMENTOS_SOPORTE = load_dynamic_config("DOCUMENTOS_SOPORTE", {
    "Procedimiento: Manual Técnico y de Usuario (Cod.CGT-PR-0001)": "CGT-PR-0001 Manual tecnico y de usuario.md",
    "Guía Rápida Operativa (Cod.CGT-GU-0001)": "CGT-GU-0001 Guía Rápida Operativa.md",
    "Carta de Presentación Corporativa (Cod.CGT-CP-0001)": "CGT-CP-0001 Carta de Presentación.md",
    "Política de Privacidad para Datos Sensibles": "CGT Politica de Privacidad para datos Sensibles.pdf",
    "Términos y Condiciones de Uso": "CGT Terminos y Condiciones.pdf"
})

# ==========================================
# 4. MAPEO AUDITORÍA RESSO 2026
# ==========================================
MAPEO_RESSO = load_dynamic_config("MAPEO_RESSO", {
    "IRL información de riesgos laborales": "20.-IRL",
    "Contrato de Trabajo y Anexos": "47.- RESSO sin numero",
    "Comprobante Entrega RIOHS": "37.-Reglamento interno",
    "Exámenes Médicos Pre u Ocupacionales": "47.- RESSO sin numero",
    "Curso de Trabajo en Altura": "45.-Plan de capacitación faltas - infracciones",
    "Curso de Primeros Auxilios": "18.-Capacitación plan emergencias",
    "Curso de Manejo de Extintores": "18.-Capacitación plan emergencias",
    "Certificación de Operador": "0.-Certificaciones empresa",
    "Difusión de Procedimientos": "38.-Difusión PTS y normativa",
    "Planes de Emergencia": "16.-Plan de emergencias",
    "Planes de Riesgo de Higiene": "9.-Mapa de riesgo higiene",
    "Políticas Corporativas": "2.-Politica",
    "Programa SST": "1.-Programa SST"
})
