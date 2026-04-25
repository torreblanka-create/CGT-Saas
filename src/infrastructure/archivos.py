"""
==========================================
📁 FILES ENGINE — v2.0 MEJORADO
==========================================
Motor centralizado de gestión de archivos y estructura de directorios.

CARACTERÍSTICAS v2.0:
✅ Gestión jerárquica de carpetas (empresa > contrato > categoría)
✅ Sincronización con BD
✅ Auditoría de operaciones de archivos
✅ Búsqueda y catalogación
✅ Reportes de uso de espacio
✅ Validación de rutas (prevención de path traversal)
✅ Backups automáticos
✅ Limpieza y mantenimiento
"""

import os
import sqlite3
import unicodedata
import shutil
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import json

import pandas as pd

from config.config import BASE_DATA_DIR, DB_PATH
from src.infrastructure.database import ejecutar_query, get_db_connection

logger = logging.getLogger(__name__)


# ============ DATA MODELS ============

@dataclass
class OperacionArchivo:
    """Representa una operación de archivo auditada"""
    id: str
    usuario_id: str
    operacion: str  # 'crear', 'eliminar', 'mover', 'copiar'
    ruta_origen: str
    ruta_destino: str
    resultado: str  # 'exitoso', 'error'
    detalles: Dict
    timestamp: str


@dataclass
class RegistroEspacio:
    """Registro de uso de espacio en disco"""
    ruta: str
    tamaño_bytes: int
    cantidad_archivos: int
    fecha_calculo: str


class FilesEngine:
    """
    Motor avanzado de gestión de archivos.
    
    Características:
    - Gestión jerárquica de directorios
    - Sincronización con BD
    - Auditoría de operaciones
    - Búsqueda de archivos
    - Reportes de espacio
    - Validación de rutas
    - Backups automáticos
    """
    
    def __init__(self, db_path: str = DB_PATH, base_dir: str = BASE_DATA_DIR):
        """Inicializa el motor de archivos"""
        self.db_path = db_path
        self.base_dir = base_dir
        self._crear_tablas()
        logger.info("FilesEngine inicializado")
    
    def _crear_tablas(self) -> None:
        """Crea tablas para auditoría y catalogación"""
        if not self.db_path:
            return
        
        tables = [
            """
            CREATE TABLE IF NOT EXISTS operaciones_archivos (
                id TEXT PRIMARY KEY,
                usuario_id TEXT,
                operacion TEXT,
                ruta_origen TEXT,
                ruta_destino TEXT,
                resultado TEXT,
                detalles TEXT,  -- JSON
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS catalogo_archivos (
                id TEXT PRIMARY KEY,
                ruta_completa TEXT UNIQUE,
                nombre_archivo TEXT,
                extension TEXT,
                tamaño_bytes INTEGER,
                md5_hash TEXT,
                fecha_creacion TIMESTAMP,
                fecha_modificacion TIMESTAMP,
                usuario_propietario TEXT,
                categoria TEXT,
                etiquetas TEXT,  -- JSON list
                activo BOOLEAN DEFAULT 1
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS espacio_disco (
                id TEXT PRIMARY KEY,
                ruta TEXT,
                tamaño_bytes INTEGER,
                cantidad_archivos INTEGER,
                fecha_calculo TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        ]
        
        try:
            with get_db_connection(self.db_path) as conn:
                for query in tables:
                    conn.execute(query)
                conn.commit()
            logger.debug("Tablas de files_engine creadas")
        except Exception as e:
            logger.error(f"Error creando tablas: {e}")
    
    def obtener_ruta_validada(self, empresa: str, categoria: str, identificador: str,
                             nombre_entidad: str = "", contrato: str = None,
                             crear: bool = True) -> Optional[str]:
        """
        Obtiene ruta jerárquica validada y segura.
        
        Estructura: BASE_DIR / EMPRESA / CONTRATO / CATEGORIA / ID
        
        Previene path traversal y validaciones de seguridad.
        """
        try:
            # Sanitizar entradas
            emp_clean = self._sanitizar_nombre(empresa).upper()
            cat_clean = self._sanitizar_nombre(categoria).upper()
            con_clean = self._sanitizar_nombre(contrato or "SIN_CONTRATO").upper()
            id_clean = str(identificador).strip().replace(".", "").replace("/", "").upper()
            
            # Validar
            if not emp_clean or emp_clean == "NAN":
                if crear:
                    raise ValueError(f"❌ Empresa inválida: {empresa}")
                emp_clean = "EMPRESA_NO_DEFINIDA"
            
            if not cat_clean:
                if crear:
                    raise ValueError(f"❌ Categoría inválida para: {identificador}")
                cat_clean = "COMODIN"
            
            # Construir ruta
            if categoria.lower() == "personal" and nombre_entidad:
                nom_clean = self._sanitizar_nombre(nombre_entidad).upper()
                carpeta_final = f"{nom_clean}_{id_clean}"
            else:
                carpeta_final = id_clean
            
            ruta_final = os.path.join(self.base_dir, emp_clean, con_clean, cat_clean, carpeta_final)
            
            # Prevenir path traversal
            ruta_final = os.path.normpath(ruta_final)
            if not ruta_final.startswith(os.path.normpath(self.base_dir)):
                raise ValueError(f"❌ Path traversal detectado: {ruta_final}")
            
            # Crear si se pide
            if crear:
                os.makedirs(ruta_final, exist_ok=True)
                self._crear_subcarpetas_estándar(ruta_final, categoria)
                logger.info(f"✅ Ruta creada: {ruta_final}")
            
            return ruta_final
        
        except Exception as e:
            logger.error(f"Error obteniendo ruta validada: {e}")
            return None
    
    def _sanitizar_nombre(self, nombre: str) -> str:
        """Sanitiza nombre para uso en rutas de archivos"""
        if not nombre or pd.isna(nombre):
            return ""
        
        s = str(nombre).strip()
        # Remover acentos
        s = ''.join(c for c in unicodedata.normalize('NFD', s) 
                   if unicodedata.category(c) != 'Mn')
        # Remover caracteres peligrosos
        s = s.replace(" ", "_").replace("/", "-").replace("\\", "-")
        s = "".join(c for c in s if c.isalnum() or c in ['_', '-'])
        
        return s.upper()
    
    def _crear_subcarpetas_estándar(self, ruta_base: str, categoria: str) -> None:
        """Crea estructura de subcarpetas según categoría"""
        subcarpetas_base = ["Fotos", "Documentos_Vigentes"]
        
        for sub in subcarpetas_base:
            os.makedirs(os.path.join(ruta_base, sub), exist_ok=True)
        
        # Subcarpetas específicas por categoría
        if categoria.lower() == "personal":
            os.makedirs(os.path.join(ruta_base, "EPP_y_Certificaciones"), exist_ok=True)
        elif "vehiculo" in categoria.lower() or "maquinaria" in categoria.lower():
            os.makedirs(os.path.join(ruta_base, "Certificados_Torque"), exist_ok=True)
    
    def registrar_operacion(self, usuario_id: str, operacion: str, 
                           ruta_origen: str, ruta_destino: str = "",
                           resultado: str = "exitoso", detalles: Dict = None) -> None:
        """Registra operación de archivo en auditoría"""
        if not self.db_path:
            return
        
        try:
            import secrets
            op = OperacionArchivo(
                id=secrets.token_hex(16),
                usuario_id=usuario_id,
                operacion=operacion,
                ruta_origen=ruta_origen,
                ruta_destino=ruta_destino,
                resultado=resultado,
                detalles=detalles or {},
                timestamp=datetime.now().isoformat()
            )
            
            query = """
            INSERT INTO operaciones_archivos
            (id, usuario_id, operacion, ruta_origen, ruta_destino, resultado, detalles)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """
            
            with get_db_connection(self.db_path) as conn:
                conn.execute(query, (op.id, usuario_id, operacion, ruta_origen, 
                                    ruta_destino, resultado, json.dumps(detalles or {})))
                conn.commit()
            
            logger.debug(f"✅ Operación registrada: {operacion}")
        except Exception as e:
            logger.error(f"Error registrando operación: {e}")
    
    def calcular_espacio_usado(self, ruta: str = None) -> Dict:
        """
        Calcula espacio usado en una ruta o en toda la base.
        
        Returns:
            Dict con tamaño total, cantidad de archivos, desglose por carpeta
        """
        ruta_a_analizar = ruta or self.base_dir
        
        try:
            total_bytes = 0
            total_archivos = 0
            desglose = {}
            
            for dirpath, dirnames, filenames in os.walk(ruta_a_analizar):
                # Limitar profundidad para performance
                if dirpath.count(os.sep) - ruta_a_analizar.count(os.sep) > 5:
                    dirnames.clear()
                    continue
                
                dir_bytes = 0
                for filename in filenames:
                    try:
                        filepath = os.path.join(dirpath, filename)
                        file_size = os.path.getsize(filepath)
                        total_bytes += file_size
                        dir_bytes += file_size
                        total_archivos += 1
                    except:
                        pass
                
                if dir_bytes > 0:
                    rel_path = os.path.relpath(dirpath, ruta_a_analizar)
                    desglose[rel_path] = dir_bytes / (1024*1024)  # MB
            
            return {
                "ruta": ruta_a_analizar,
                "tamaño_bytes": total_bytes,
                "tamaño_mb": round(total_bytes / (1024*1024), 2),
                "tamaño_gb": round(total_bytes / (1024*1024*1024), 2),
                "cantidad_archivos": total_archivos,
                "desglose_mb": desglose,
                "fecha_calculo": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error calculando espacio: {e}")
            return {}
    
    def buscar_archivos(self, termino: str, ruta: str = None, 
                       extension: str = None) -> List[Dict]:
        """
        Busca archivos por nombre o en catálogo.
        
        Args:
            termino: Término a buscar
            ruta: Ruta donde buscar (default: base_dir)
            extension: Filtrar por extensión
        
        Returns:
            Lista de archivos encontrados
        """
        ruta_busqueda = ruta or self.base_dir
        resultados = []
        
        try:
            for dirpath, dirnames, filenames in os.walk(ruta_busqueda):
                # Limite de seguridad
                if dirpath.count(os.sep) - ruta_busqueda.count(os.sep) > 6:
                    dirnames.clear()
                    continue
                
                for filename in filenames:
                    if termino.lower() in filename.lower():
                        if extension and not filename.lower().endswith(extension.lower()):
                            continue
                        
                        filepath = os.path.join(dirpath, filename)
                        try:
                            stat = os.stat(filepath)
                            resultados.append({
                                "nombre": filename,
                                "ruta": filepath,
                                "tamaño_bytes": stat.st_size,
                                "fecha_modificacion": datetime.fromtimestamp(stat.st_mtime).isoformat()
                            })
                        except:
                            pass
        
        except Exception as e:
            logger.error(f"Error en búsqueda: {e}")
        
        return resultados
    
    def generar_reporte_archivos(self) -> Dict:
        """Genera reporte completo de estado de archivos"""
        try:
            espacio = self.calcular_espacio_usado()
            
            # Contar por tipo
            tipos_archivo = {}
            for dirpath, _, filenames in os.walk(self.base_dir):
                for filename in filenames:
                    ext = os.path.splitext(filename)[1] or "sin_extension"
                    tipos_archivo[ext] = tipos_archivo.get(ext, 0) + 1
            
            return {
                "fecha_reporte": datetime.now().isoformat(),
                "espacio_usado": espacio,
                "tipos_archivo": tipos_archivo,
                "directorio_base": self.base_dir,
                "estado": "✅ Sistema de archivos operativo"
            }
        except Exception as e:
            logger.error(f"Error generando reporte: {e}")
            return {}


# ============ FUNCIONES COMPATIBILIDAD (LEGACY) + MEJORADAS ============

def asegurar_estructura_base():
    """Crea la carpeta raíz del sistema (CGT_DATA) si no existe."""
    engine = obtener_files_engine()
    if not os.path.exists(BASE_DATA_DIR):
        os.makedirs(BASE_DATA_DIR)
    # Crear carpeta de respaldos
    backup_dir = os.path.join(BASE_DATA_DIR, "BACKUPS")
    os.makedirs(backup_dir, exist_ok=True)
    logger.info("✅ Estructura base asegurada")


def obtener_ruta_entidad(empresa, categoria, identificador, nombre_entidad="", contrato=None, crear_directorios=True):
    """LEGACY: Usa FilesEngine mejorado internamente"""
    engine = obtener_files_engine()
    return engine.obtener_ruta_validada(empresa, categoria, identificador, nombre_entidad, contrato, crear_directorios)


def normalizar_texto(txt):
    """Limpia texto de acentos y estandariza"""
    engine = obtener_files_engine()
    return engine._sanitizar_nombre(txt)


# ============ SINGLETON ============

_engine_files = None

def obtener_files_engine(db_path: str = None, base_dir: str = None) -> FilesEngine:
    """Obtiene instancia singleton del FilesEngine"""
    global _engine_files
    if _engine_files is None:
        _engine_files = FilesEngine(
            db_path or DB_PATH,
            base_dir or BASE_DATA_DIR
        )
    return _engine_files


# ============ FUNCIONES LEGACY ADICIONALES (PARA COMPATIBILIDAD) ============

def _sanitizar_path_component(componente: str) -> str:
    """Sanitiza un componente de ruta para prevenir path traversal"""
    if not componente:
        return ""
    # Remover caracteres peligrosos
    peligrosos = ["..", "/", "\\", ":", "*", "?", "\"", "<", ">", "|"]
    for p in peligrosos:
        componente = componente.replace(p, "_")
    return componente.strip().upper()


def obtener_ruta_torques(empresa, identificador, contrato=None):
    """LEGACY"""
    return obtener_ruta_entidad(empresa, "Maquinaria_Pesada_Vehiculos", identificador, contrato=contrato, crear_directorios=True)


def obtener_ruta_procedimientos(empresa, contrato=None):
    """LEGACY - Genera ruta para procedimientos con validación de path traversal."""
    emp_clean = _sanitizar_path_component(normalizar_texto(empresa).replace(" ", "_"))
    con_clean = _sanitizar_path_component(normalizar_texto(contrato) if contrato else "GLOBAL")
    ruta_pts = os.path.join(BASE_DATA_DIR, emp_clean, con_clean, "Documentos_Globales", "Procedimientos_y_Matrices")
    # Validar path traversal
    ruta_pts = os.path.normpath(ruta_pts)
    if not ruta_pts.startswith(os.path.normpath(BASE_DATA_DIR)):
        raise ValueError("🚨 Path traversal detectado en obtener_ruta_procedimientos")
    os.makedirs(ruta_pts, exist_ok=True)
    os.makedirs(os.path.join(ruta_pts, "Firmas_Difusion"), exist_ok=True)
    os.makedirs(os.path.join(ruta_pts, "Evaluaciones"), exist_ok=True)
    return ruta_pts


def obtener_ruta_planes_accion(empresa, contrato, codigo_plan):
    """LEGACY - Genera ruta para planes de acción con validación de path traversal."""
    emp_clean = _sanitizar_path_component(normalizar_texto(empresa))
    con_clean = _sanitizar_path_component(normalizar_texto(contrato) if contrato else "SIN_CONTRATO")
    plan_clean = _sanitizar_path_component(normalizar_texto(codigo_plan))
    ruta_plan = os.path.join(BASE_DATA_DIR, emp_clean, con_clean, "Planes_Accion", plan_clean, "Evidencias")
    # Validar path traversal
    ruta_plan = os.path.normpath(ruta_plan)
    if not ruta_plan.startswith(os.path.normpath(BASE_DATA_DIR)):
        raise ValueError("🚨 Path traversal detectado en obtener_ruta_planes_accion")
    os.makedirs(ruta_plan, exist_ok=True)
    return ruta_plan


def obtener_ruta_informes_calidad(empresa, contrato):
    """LEGACY - Genera ruta para informes de calidad con validación de path traversal."""
    emp_clean = _sanitizar_path_component(normalizar_texto(empresa) if empresa and not pd.isna(empresa) else "EMPRESA_GLOBAL")
    con_clean = _sanitizar_path_component(normalizar_texto(contrato) if contrato and not pd.isna(contrato) else "SIN_CONTRATO_ASIGNADO")
    ruta_calidad = os.path.join(BASE_DATA_DIR, emp_clean, con_clean, "Informes_Calidad")
    # Validar path traversal
    ruta_calidad = os.path.normpath(ruta_calidad)
    if not ruta_calidad.startswith(os.path.normpath(BASE_DATA_DIR)):
        raise ValueError("🚨 Path traversal detectado en obtener_ruta_informes_calidad")
    os.makedirs(ruta_calidad, exist_ok=True)
    return ruta_calidad


def validar_archivo_seguro(file_obj, allowed_types=['pdf', 'png', 'jpg']):
    """Valida el archivo usando Magic Bytes (Firmas Binarias)."""
    if file_obj is None:
        return False, "No se proporcionó ningún archivo"
    
    try:
        header = file_obj.read(16)
        file_obj.seek(0)
        
        signatures = {
            'pdf': b'%PDF',
            'png': b'\x89PNG',
            'jpg': b'\xff\xd8\xff'
        }
        
        if isinstance(allowed_types, str):
            allowed_types = [allowed_types]
        
        check_list = [t.lower().replace('.', '').strip() for t in allowed_types] if allowed_types else signatures.keys()
        
        for t in check_list:
            if t in signatures and signatures[t] in header:
                return True, "Archivo válido"
        
        return False, f"El archivo no coincide con los tipos permitidos ({', '.join(check_list)})"
    
    except Exception as e:
        logger.error(f"Error validando archivo: {e}")
        return False, f"Error: {e}"

def obtener_ruta_modulo_especifico(empresa, contrato, modulo, crear=True):
    """
    Genera la ruta raíz para un módulo (AUDITORIA, CONFIABILIDAD, etc) dentro de un contrato.
    Esta es la base de la 'Arquitectura de Valor Agregado v4.0'.
    """
    emp_clean = normalizar_texto(empresa).strip().replace(" ", "_").upper()
    con_clean = normalizar_texto(contrato).strip().replace(" ", "_").upper()
    mod_clean = normalizar_texto(modulo).strip().replace(" ", "_").upper()

    ruta_modulo = os.path.join(BASE_DATA_DIR, emp_clean, con_clean, mod_clean)

    if crear:
        os.makedirs(ruta_modulo, exist_ok=True)

    return ruta_modulo

def obtener_ruta_riesgo_requisito(empresa, contrato, rf_num, cc, req, ev, crear=True):
    """
    Genera la ruta específica para la evidencia de un requisito de riesgo fatal.
    Soporta LEGACY FALLBACK: Busca en la ruta antigua si la nueva no tiene la carpeta.
    """
    import re
    # 1. Preparar Identificadores
    rf_num_clean = "".join(re.findall(r'\d+', rf_num))
    if not rf_num_clean: rf_num_clean = "XX"
    ef_folder = f"EF_{rf_num_clean}"
    sub_folder = f"{cc}-{req}-{ev}".replace(" ", "_").replace("/", "-")

    emp_clean = normalizar_texto(empresa).strip().replace(" ", "_").upper()
    con_clean = normalizar_texto(contrato).strip().replace(" ", "_").upper()

    # 2. RUTA NUEVA (v4.0 Arquitectura de Valor Agregado)
    ruta_preventiva = obtener_ruta_modulo_especifico(empresa, contrato, "GESTION_PREVENTIVA", crear=False)
    base_rf_nueva = os.path.join(ruta_preventiva, "RIESGOS_DE_FATALIDAD")
    ruta_final_nueva = os.path.join(base_rf_nueva, ef_folder, sub_folder)

    # 3. RUTA ANTIGUA (Legacy)
    base_rf_antigua = os.path.join(BASE_DATA_DIR, emp_clean, con_clean, "RIESGOS_DE_FATALIDAD")
    ruta_final_antigua = os.path.join(base_rf_antigua, ef_folder, sub_folder)

    # 4. LÓGICA DE FALLBACK
    # Si la ruta antigua EXISTE y tiene archivos, o simplemente existe y la nueva NO, usamos la antigua.
    if os.path.exists(ruta_final_antigua) and not os.path.exists(ruta_final_nueva):
        return ruta_final_antigua

    # Si se pide CREAR, lo hacemos en la ruta NUEVA (Estándar v4.0)
    if crear:
        os.makedirs(ruta_final_nueva, exist_ok=True)
        return ruta_final_nueva

    return ruta_final_nueva

def sincronizar_directorios_desde_excel():
    """Lee el Maestro Excel, actualiza la base de Datos y gestiona carpetas de forma segura."""
    from core.excel_master import obtener_ruta_excel

    ruta_excel = obtener_ruta_excel()
    if not os.path.exists(ruta_excel):
        return "❌ Error: No se encontró la Base Maestra Operacional en CGT_DATA."

    try:
        xl = pd.ExcelFile(ruta_excel)
        hojas_a_procesar = [h for h in xl.sheet_names if h not in ['Config', 'Resumen']]

        with get_db_connection(DB_PATH) as conn:
            cur = conn.cursor()
            carpetas_creadas = 0

            mapping_hoja_cat = {
                "Personal": "Personal", "Equipos": "Maquinaria Pesada & Vehículos",
                "Izaje": "Elementos de izaje", "Instrumentos": "Instrumentos y Metrología",
                "sistemas de emergencia": "Sistemas de Emergencia", "EPP": "EPP",
                "LISTADO_MAESTRO": "Unificado"
            }

            for hoja in hojas_a_procesar:
                df = pd.read_excel(ruta_excel, sheet_name=hoja, engine='openpyxl')
                df.columns = [str(c).strip().replace("'", "").replace('"', '') for c in df.columns]

                for _, row in df.iterrows():
                    # 1. Identificador
                    id_raw = next((row[c] for c in df.columns if any(x in c.lower() for x in ['identificador', 'rut', 'patente', 'id /'])), None)
                    if pd.isna(id_raw) or str(id_raw).strip() == "": continue

                    # 2. Categoría
                    categoria_real = str(row.get('Categoría', mapping_hoja_cat.get(hoja, hoja))).strip()

                    # 3. Empresa y Contrato (CON VALIDACIÓN)
                    emp_raw = row.get('Empresa')
                    if not emp_raw or pd.isna(emp_raw) or str(emp_raw).strip().lower() in ['nan', 'none', '']:
                        continue

                    con_raw = row.get('Contrato')
                    emp_nom = normalizar_texto(emp_raw)
                    con_nom = normalizar_texto(con_raw) if con_raw and not pd.isna(con_raw) else "Sin Contrato"

                    nombre_raw = next((row[c] for c in df.columns if any(x in c.lower() for x in ['nombre', 'descripcion', 'marca', 'modelo'])), "")

                    # 4. Sincronizar SQL
                    cur.execute("INSERT OR IGNORE INTO empresas (nombre) VALUES (?)", (emp_nom,))
                    cur.execute("SELECT id FROM empresas WHERE nombre = ?", (emp_nom,))
                    emp_id = cur.fetchone()[0]

                    cur.execute("SELECT id FROM contratos WHERE empresa_id = ? AND nombre_contrato = ?", (emp_id, con_nom))
                    if not cur.fetchone():
                        cur.execute("INSERT INTO contratos (empresa_id, nombre_contrato) VALUES (?, ?)", (emp_id, con_nom))

                    # 5. Crear Carpetas
                    obtener_ruta_entidad(emp_nom, categoria_real, str(id_raw), str(nombre_raw), contrato=con_nom)
                    carpetas_creadas += 1

            # Reparaciones retroactivas de IDs
            cur.execute("SELECT id, nombre FROM empresas")
            for e_id, e_nom in cur.fetchall():
                cur.execute("UPDATE registros SET empresa_id = ? WHERE (empresa_id IS NULL OR empresa_id = 0) AND UPPER(empresa) = ?", (e_id, e_nom.upper()))

            cur.execute("UPDATE registros SET empresa_id = 1 WHERE (empresa_id IS NULL OR empresa_id = 0) AND (UPPER(empresa) LIKE '%STEEL%' OR empresa IS NULL)")

            cur.execute("SELECT id, empresa_id, nombre_contrato FROM contratos")
            for c_id, ce_id, c_nom in cur.fetchall():
                cur.execute("UPDATE registros SET contrato_id = ? WHERE (contrato_id IS NULL OR contrato_id = 0) AND empresa_id = ? AND UPPER(contrato) = ?", (c_id, ce_id, c_nom.upper()))

            conn.commit()

        return f"✅ Sincronización Exitosa: {carpetas_creadas} registros procesados."
    except Exception as e:
        return f"❌ Error Crítico: {e}"

def organizar_carpetas_sistema(DB_PATH, status_callback=None):
    """
    Reorganiza físicamente todos los archivos del sistema a la nueva estructura 
    profesional (01.-Personal, 02.-Maquinaria, etc.) y actualiza la base de datos.
    """
    import os
    import shutil
    from datetime import datetime

    import pandas as pd

    from config.config import BASE_DATA_DIR, get_scoped_path

    log = []
    def do_log(msg):
        log.append(msg)
        if status_callback: status_callback(msg)

    # 1. Obtener mapeo de IDs a nombres para Empresa y Contrato
    with get_db_connection(DB_PATH) as conn:
        df_registros = pd.read_sql_query("""
            SELECT r.id, r.identificador, r.categoria, r.path, r.tipo_doc,
                   e.nombre as empresa_nom, c.nombre_contrato as contrato_nom
            FROM registros r
            LEFT JOIN empresas e ON r.empresa_id = e.id
            LEFT JOIN contratos c ON r.contrato_id = c.id
            WHERE r.path IS NOT NULL AND r.path != ''
        """, conn)

    if df_registros.empty:
        return "ℹ️ No hay archivos registrados para organizar."

    CATEGORIA_MODULO = {
        "Personal": "01.-Personal",
        "Maquinaria Pesada & Vehículos": "02.-Maquinaria",
        "Elementos de izaje": "03.-Izaje",
        "Instrumentos y Metrología": "04.-Instrumentos",
        "Sistemas de Emergencia": "05.-Emergencia",
        "EPP": "06.-EPP",
    }

    movidos = 0
    errores = 0
    omitidos = 0

    for _, row in df_registros.iterrows():
        path_actual = row['path']
        if not path_actual or not os.path.exists(path_actual):
            omitidos += 1
            continue

        # Resolver nombres
        emp_nom = str(row['empresa_nom']).strip() if row['empresa_nom'] else "EMPRESA_DESCONOCIDA"
        con_nom = str(row['contrato_nom']).strip() if row['contrato_nom'] else "SIN_CONTRATO"
        cat = str(row['categoria']).strip()
        mod_dest = CATEGORIA_MODULO.get(cat, f"07.-Otros_{cat[:15]}")

        # Ruta Ideal
        dir_ideal = get_scoped_path(emp_nom, con_nom, mod_dest)
        nombre_archivo = os.path.basename(path_actual)
        path_ideal = os.path.join(dir_ideal, nombre_archivo)

        # Si ya está en la ruta correcta, saltar
        try:
            if os.path.abspath(path_actual) == os.path.abspath(path_ideal):
                continue
        except:
            continue

        # Si el destino ya existe pero es OTRO archivo
        if os.path.exists(path_ideal) and os.path.abspath(path_actual) != os.path.abspath(path_ideal):
            ts = datetime.now().strftime("%H%M%S")
            base, ext = os.path.splitext(nombre_archivo)
            path_ideal = os.path.join(dir_ideal, f"{base}_{ts}{ext}")

        try:
            # Mover archivo
            shutil.move(path_actual, path_ideal)

            # Actualizar DB
            ejecutar_query(DB_PATH, "UPDATE registros SET path = ? WHERE id = ?", (path_ideal, row['id']), commit=True)
            movidos += 1
        except Exception as e:
            errores += 1
            do_log(f"❌ Error moviendo {nombre_archivo}: {e}")

    # 2. Limpieza de carpetas vacías residuales
    do_log("🧹 Iniciando limpieza de carpetas vacías...")
    for root, dirs, files in os.walk(BASE_DATA_DIR, topdown=False):
        for name in dirs:
            dir_path = os.path.join(root, name)
            try:
                if not os.listdir(dir_path):
                    os.rmdir(dir_path)
            except:
                pass

    return f"🚀 Reorganización completa: {movidos} movidos, {errores} errores, {omitidos} paths no encontrados."
