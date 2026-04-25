import os
import shutil
import sqlite3
import unicodedata
from contextlib import contextmanager
from datetime import datetime

import bcrypt
import pandas as pd
from dotenv import load_dotenv

# Cargar variables de entorno — .env local tiene prioridad; en Streamlit Cloud se usan st.secrets
load_dotenv()

def _get_secret(key: str, default: str = None):
    """Lee un secreto desde st.secrets (Streamlit Cloud) o variables de entorno."""
    val = os.getenv(key)
    if val:
        return val
    try:
        import streamlit as st
        return st.secrets.get(key, default)
    except Exception:
        return default

def normalizar_texto(texto):
    """Convierte a mayúsculas, recorta espacios y elimina tildes/acentos."""
    if not isinstance(texto, str) and texto is not None:
        texto = str(texto)
    if not texto:
        return ""
    texto = texto.strip().upper()
    texto = ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')
    return ' '.join(texto.split())


# Configuración Global
TIMEOUT_DB = 30
def respaldar_base_datos(db_path, max_backups=10):
    """Crea una copia de seguridad con marca de tiempo en la carpeta BACKUPS."""
    try:
        if not os.path.exists(db_path): return

        base_dir = os.path.dirname(db_path)
        backup_dir = os.path.join(base_dir, "BACKUPS")
        os.makedirs(backup_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"cgt_control_backup_{timestamp}.db"
        backup_path = os.path.join(backup_dir, backup_name)

        shutil.copy2(db_path, backup_path)

        # Limpieza de retención
        backups = sorted([os.path.join(backup_dir, f) for f in os.listdir(backup_dir) if f.startswith("cgt_control_backup_")])
        if len(backups) > max_backups:
            for old_backup in backups[:-max_backups]:
                os.remove(old_backup)
    except Exception as e:
        print(f"❌ Error al respaldar base de datos: {e}")

@contextmanager
def get_db_connection(db_path):
    """Gestor de contexto para conexiones SQLite con WAL habilitado."""
    conn = sqlite3.connect(db_path, timeout=TIMEOUT_DB)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        yield conn
    finally:
        conn.close()

def obtener_conexion(db_path):
    """Retorna una conexión SQLite directa (sin context manager)."""
    conn = sqlite3.connect(db_path, timeout=TIMEOUT_DB)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def ejecutar_query(db_path, query, params=(), commit=False):
    """Ejecuta una consulta SQL de forma segura y parametrizada."""
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        if commit:
            conn.commit()
            return cursor.lastrowid
        return cursor.fetchall()

def obtener_dataframe(db_path, query, params=(), use_cache=False):
    """Retorna un DataFrame de pandas a partir de una consulta SQL."""
    with get_db_connection(db_path) as conn:
        return pd.read_sql_query(query, conn, params=params)

def generar_hash(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def inicializar_base_datos(db_path):
    """Crea y actualiza la estructura completa de las tablas de CGT."""
    db_dir = os.path.dirname(db_path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

    # RESPALDO PREVENTIVO (Constitución de Ultron - Ley 4.1)
    try: respaldar_base_datos(db_path)
    except Exception as e: print(f"⚠️ Error en respaldo preventivo: {e}")

    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()

        tablas = {
            "empresas": '''id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT UNIQUE, rut TEXT, 
                            rep_legal TEXT, direccion TEXT, logo_path TEXT''',
            "checklists_registros": "id INTEGER PRIMARY KEY AUTOINCREMENT, template_id INTEGER, fecha TEXT, inspector TEXT, empresa TEXT, contrato TEXT, entidad_inspeccionada TEXT, respuestas_json TEXT, porcentaje_cumplimiento REAL, estado TEXT, empresa_id INTEGER, contrato_id INTEGER",
            "contratos": '''id INTEGER PRIMARY KEY AUTOINCREMENT, empresa_id INTEGER, nombre_contrato TEXT, 
                            detalle TEXT, FOREIGN KEY(empresa_id) REFERENCES empresas(id)''',
            "registros": '''id INTEGER PRIMARY KEY AUTOINCREMENT, identificador TEXT, nombre TEXT, detalle TEXT, 
                            tipo_doc TEXT, fecha_vencimiento DATE, path TEXT, categoria TEXT, asignado_a TEXT, 
                            tipo_control TEXT, meta_horometro INTEGER, 
                            empresa_id INTEGER, contrato_id INTEGER,
                            tiene_observacion TEXT DEFAULT 'No', detalle_observacion TEXT DEFAULT '',
                            fecha_limite_obs DATE, estado_obs TEXT DEFAULT 'N/A',
                            observaciones TEXT, fecha_carga DATE, fecha_condicion DATE,
                            FOREIGN KEY(empresa_id) REFERENCES empresas(id),
                            FOREIGN KEY(contrato_id) REFERENCES contratos(id)''',
            "usuarios": '''username TEXT PRIMARY KEY, pw TEXT, rol TEXT, nombre TEXT, 
                            terminos_aceptados INTEGER DEFAULT 0, 
                            empresa_id INTEGER DEFAULT 0, 
                            contrato_asignado_id INTEGER DEFAULT 0,
                            email TEXT UNIQUE,
                            telefono TEXT,
                            foto_path TEXT,
                            cargo TEXT,
                            departamento TEXT,
                            pref_notificaciones TEXT DEFAULT '{"silenciar": false}',
                            pw_reset_req INTEGER DEFAULT 0''',
            "historial_rigging_plans": '''id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                          descripcion TEXT, responsable TEXT, datos_json TEXT,
                                          empresa_id INTEGER, contrato_id INTEGER''',
            "especificaciones_equipos": '''identificador TEXT PRIMARY KEY, marca_modelo TEXT,
                                           capacidad_max_ton REAL, peso_gancho_kg REAL,
                                           tabla_carga_json TEXT, empresa_id INTEGER''',
            "procedimientos": '''id INTEGER PRIMARY KEY AUTOINCREMENT, codigo TEXT UNIQUE, nombre TEXT, 
                                 version TEXT, fecha_creacion DATE, fecha_vencimiento DATE, 
                                 categoria TEXT DEFAULT 'Procedimiento', path TEXT, empresa TEXT,
                                 empresa_id INTEGER, contrato_id INTEGER,
                                 ambito TEXT, sub_area TEXT, sigla_negocio TEXT, correlativo TEXT''',
            "historial_informes_calidad": '''id INTEGER PRIMARY KEY AUTOINCREMENT, fecha DATE, titulo TEXT, 
                                             tecnico TEXT, empresa TEXT, contrato TEXT, ruta_archivo TEXT,
                                             empresa_id INTEGER, contrato_id INTEGER,
                                             template_id TEXT, datos_json TEXT''',
            "reportes_incidentes": '''id INTEGER PRIMARY KEY AUTOINCREMENT, folio TEXT, fecha DATE, hora TEXT,
                                       tipo_evento TEXT, riesgo_critico TEXT, control_fallido TEXT,
                                       que_ocurrio TEXT, porque_ocurrio TEXT, acciones_json TEXT,
                                       foto_path TEXT, clasificacion_alerta TEXT, requiere_investigacion TEXT,
                                       reportante TEXT, afectado TEXT,
                                       empresa_id INTEGER, contrato_id INTEGER''',
            "eventos_confiabilidad": '''id INTEGER PRIMARY KEY AUTOINCREMENT, 
                                         fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                         identificador TEXT, tipo_falla TEXT, descripcion TEXT,
                                         duracion_min INTEGER, estado TEXT DEFAULT 'Abierto',
                                         foto_path TEXT,
                                         empresa_id INTEGER, contrato_id INTEGER''',
            "entregas_epp_actas": '''id INTEGER PRIMARY KEY AUTOINCREMENT, trabajador_id TEXT, 
                                     fecha_entrega TEXT, firma_path TEXT, instructor TEXT,
                                     empresa_id INTEGER, contrato_id INTEGER''',
            "entregas_epp_items": '''id INTEGER PRIMARY KEY AUTOINCREMENT, acta_id INTEGER, 
                                     tipo_epp TEXT, talla TEXT, cantidad INTEGER, 
                                     marca TEXT, modelo TEXT, fecha_vencimiento TEXT,
                                     FOREIGN KEY(acta_id) REFERENCES entregas_epp_actas(id)''',
            "registros_art": '''id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, hora TEXT, 
                                tarea TEXT, area TEXT, supervisor TEXT, ejecutor TEXT,
                                datos_json TEXT, ruta_pdf TEXT,
                                empresa_id INTEGER, contrato_id INTEGER''',
            "planes_accion": '''id INTEGER PRIMARY KEY AUTOINCREMENT, codigo_plan TEXT, 
                                foco_intervencion TEXT, objetivo TEXT, accion TEXT, 
                                responsable TEXT, fecha_inicio DATE, fecha_cierre DATE, 
                                kpi TEXT, estado TEXT DEFAULT 'Abierto', 
                                empresa_id INTEGER, contrato_id INTEGER''',
            "evidencias_planes": '''id INTEGER PRIMARY KEY AUTOINCREMENT, plan_id INTEGER, 
                                   fecha_subida DATE, descripcion TEXT, ruta_archivo TEXT, 
                                   empresa_id INTEGER, contrato_id INTEGER,
                                   FOREIGN KEY(plan_id) REFERENCES planes_accion(id)''',
            "maestro_entidades": '''identificador TEXT PRIMARY KEY, nombre TEXT, detalle TEXT, 
                                     categoria TEXT, empresa_id INTEGER, contrato_id INTEGER''',
            "config_sistema": "clave TEXT PRIMARY KEY, valor_json TEXT",
            "logs_actividad": "id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP, usuario TEXT, accion TEXT, detalle TEXT",
            "informes_templates": '''id_str TEXT PRIMARY KEY, nombre TEXT, descripcion TEXT, 
                                     estructura_json TEXT, empresa_id INTEGER, activo INTEGER DEFAULT 1''',
            "trazabilidad_documental": '''id INTEGER PRIMARY KEY AUTOINCREMENT, faena TEXT, 
                                          administrador TEXT, tema TEXT, fecha TEXT, 
                                          descripcion TEXT, relator TEXT, hora_inicio TEXT, 
                                          hora_termino TEXT, hh_totales REAL, tipo_documento TEXT, 
                                          participantes_json TEXT, estado TEXT, 
                                          archivo_respaldo TEXT, empresa_id INTEGER, contrato_id INTEGER''',
            "auditorias_resso": '''id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, auditor TEXT, 
                                   empresa TEXT, contrato TEXT, datos_json TEXT, puntaje_documental REAL, 
                                   puntaje_terreno REAL, descuento_hallazgo REAL, puntaje_final REAL, 
                                   clasificacion TEXT, estado TEXT, empresa_id INTEGER, contrato_id INTEGER''',
            "compliance_audits": '''id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, auditor TEXT, 
                                     tipo TEXT, empresa_id INTEGER, contrato_id INTEGER, 
                                     datos_json TEXT, puntaje_final REAL, clasificacion TEXT''',
            "compliance_gaps": '''id INTEGER PRIMARY KEY AUTOINCREMENT, audit_id INTEGER, 
                                   item_id TEXT, pregunta TEXT, accion_correctiva TEXT, 
                                   responsable TEXT, fecha_limite TEXT, estado TEXT DEFAULT 'Abierto',
                                   FOREIGN KEY(audit_id) REFERENCES compliance_audits(id)''',
            "notificaciones_ultron": '''id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                         tipo TEXT, mensaje TEXT, identificador TEXT, 
                                         estado TEXT DEFAULT 'No Leída', empresa_id INTEGER, contrato_id INTEGER''',
            "chat_ultron_history": '''id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP, 
                                       usuario TEXT, role TEXT, content TEXT, 
                                       type TEXT DEFAULT 'text' ''',
            "riesgos_criticos_cumplimiento": '''id INTEGER PRIMARY KEY AUTOINCREMENT,
                                                 rf_num TEXT, nombre_rf TEXT, evento_top TEXT,
                                                 codigo_cc TEXT, nombre_cc TEXT, objetivo_cc TEXT,
                                                 clasificacion TEXT, codigo_requisito TEXT, requisito TEXT,
                                                 codigo_evidencia TEXT, evidencia TEXT, fila_cc_id TEXT,
                                                 monitoreo TEXT, cumplimiento REAL DEFAULT 0,
                                                 brecha TEXT, plan_accion TEXT, responsable TEXT,
                                                 fecha_prog TEXT, fecha_cierre TEXT, estatus TEXT,
                                                 responsable_1_nombre TEXT, responsable_1_email TEXT,
                                                 responsable_2_nombre TEXT, responsable_2_email TEXT,
                                                 brecha_detectada TEXT, plan_accion_detalle TEXT,
                                                 fecha_inicio TEXT, fecha_cierre_real TEXT,
                                                 esta_activo INTEGER DEFAULT 1,
                                                 empresa_id INTEGER, contrato_id INTEGER''',
            "evidencias_riesgos": '''id INTEGER PRIMARY KEY AUTOINCREMENT,
                                      riesgo_cumplimiento_id INTEGER,
                                      file_path TEXT,
                                      file_name TEXT,
                                      fecha_carga TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                      FOREIGN KEY(riesgo_cumplimiento_id) REFERENCES riesgos_criticos_cumplimiento(id)''',
            "audit_formatos_tipo": '''id INTEGER PRIMARY KEY AUTOINCREMENT,
                                      punto_id TEXT,
                                      empresa_id INTEGER,
                                      nombre_archivo TEXT,
                                      path_archivo TEXT,
                                      fecha_carga TIMESTAMP DEFAULT CURRENT_TIMESTAMP''',
            "protocolos_minsal": '''id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT UNIQUE, 
                                    descripcion TEXT, activo INTEGER DEFAULT 1''',
            "ges_ambiental": '''id INTEGER PRIMARY KEY AUTOINCREMENT, nombre_ges TEXT, 
                                 descripcion TEXT, area TEXT, empresa_id INTEGER, contrato_id INTEGER''',
            "evaluaciones_ambientales": '''id INTEGER PRIMARY KEY AUTOINCREMENT, ges_id INTEGER, 
                                            protocolo_id INTEGER, fecha_evaluacion DATE, 
                                            nivel_riesgo TEXT, proxima_evaluacion DATE, 
                                            documento_path TEXT, observaciones TEXT, 
                                            empresa_id INTEGER, contrato_id INTEGER,
                                            FOREIGN KEY(ges_id) REFERENCES ges_ambiental(id),
                                            FOREIGN KEY(protocolo_id) REFERENCES protocolos_minsal(id)''',
            "vigilancia_medica_trabajadores": '''id INTEGER PRIMARY KEY AUTOINCREMENT, trabajador_id TEXT, 
                                                  protocolo_id INTEGER, ges_id INTEGER, 
                                                  fecha_examen DATE, resultado TEXT, 
                                                   vigencia_meses INTEGER, proximo_examen DATE, 
                                                   estado TEXT, documento_path TEXT, observaciones TEXT,
                                                   empresa_id INTEGER, contrato_id INTEGER,
                                                   FOREIGN KEY(protocolo_id) REFERENCES protocolos_minsal(id),
                                                   FOREIGN KEY(trabajador_id) REFERENCES maestro_entidades(identificador)''',
            "estudios_carga_combustible": '''id INTEGER PRIMARY KEY AUTOINCREMENT, fecha DATE, area_sector TEXT, 
                                             superficie_m2 REAL, carga_mj_m2 REAL, clasificacion_oguc TEXT, 
                                             datos_json TEXT, informe_pdf_path TEXT, 
                                             empresa_id INTEGER, contrato_id INTEGER''',
            "mapas_emergencia": '''id INTEGER PRIMARY KEY AUTOINCREMENT, fecha DATE, nombre TEXT, 
                                   tipo TEXT, imagen_path TEXT, datos_json TEXT, 
                                   empresa_id INTEGER, contrato_id INTEGER''',
            "repositorio_minsal": '''id INTEGER PRIMARY KEY AUTOINCREMENT, protocolo_id INTEGER, 
                                      ges_id INTEGER, tipo_documento TEXT, entidad_evaluadora TEXT, 
                                      fecha_documento DATE, documento_path TEXT, consideraciones TEXT,
                                      empresa_id INTEGER, contrato_id INTEGER,
                                      FOREIGN KEY(protocolo_id) REFERENCES protocolos_minsal(id)''',
            "planes_gestion_salud": '''id INTEGER PRIMARY KEY AUTOINCREMENT, repositorio_id INTEGER, 
                                        protocolo_id INTEGER, titulo TEXT, tipo_jerarquia TEXT, 
                                        responsable TEXT, fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP, 
                                        fecha_vencimiento DATE, fecha_cierre_real DATE, estado TEXT DEFAULT 'Abierto',
                                        empresa_id INTEGER, contrato_id INTEGER,
                                        FOREIGN KEY(repositorio_id) REFERENCES repositorio_minsal(id),
                                        FOREIGN KEY(protocolo_id) REFERENCES protocolos_minsal(id)''',
            # ── Ultron v2.0 Tables ──
            "ultron_ocr_validaciones": '''id INTEGER PRIMARY KEY AUTOINCREMENT,
                                           fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                           identificador TEXT, path_analizado TEXT,
                                           es_valido INTEGER DEFAULT 0, confianza REAL DEFAULT 0,
                                           razon TEXT, empresa_id INTEGER DEFAULT 0,
                                           contrato_id INTEGER DEFAULT 0''',
            "ultron_forecast_cache": '''id INTEGER PRIMARY KEY AUTOINCREMENT,
                                         fecha_generacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                         empresa_id INTEGER DEFAULT 0,
                                         contrato_id INTEGER DEFAULT 0,
                                         datos_json TEXT''',
            "ultron_normativa_alertas": '''id INTEGER PRIMARY KEY AUTOINCREMENT,
                                            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                            normativa TEXT, url TEXT,
                                            hash_anterior TEXT DEFAULT '',
                                            hash_actual TEXT,
                                            estado TEXT DEFAULT 'SIN_CAMBIOS' ''',
            "ultron_horometros_history": '''id INTEGER PRIMARY KEY AUTOINCREMENT,
                                             identificador TEXT, fecha DATE, valor REAL,
                                             empresa_id INTEGER DEFAULT 0,
                                             contrato_id INTEGER DEFAULT 0''',
            # ── Capacitaciones v1.0 ──
            "capacitaciones": '''id INTEGER PRIMARY KEY AUTOINCREMENT,
                                  titulo TEXT NOT NULL,
                                  tipo TEXT,
                                  instructor TEXT,
                                  fecha DATE,
                                  duracion_hrs REAL DEFAULT 1.0,
                                  temario TEXT,
                                  lugar TEXT,
                                  vigencia_meses INTEGER DEFAULT 0,
                                  fecha_vencimiento_ref TEXT,
                                  evidencia_path TEXT DEFAULT 'Sin archivo',
                                  empresa_id INTEGER DEFAULT 0,
                                  contrato_id INTEGER DEFAULT 0,
                                  fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP''',
            "asistencia_capacitacion": '''id INTEGER PRIMARY KEY AUTOINCREMENT,
                                           capacitacion_id INTEGER,
                                           trabajador_id TEXT,
                                           nombre TEXT,
                                           rut TEXT,
                                           cargo TEXT,
                                           fuente TEXT DEFAULT 'sistema',
                                           FOREIGN KEY(capacitacion_id) REFERENCES capacitaciones(id)''',
            "datos_emergencia": '''id INTEGER PRIMARY KEY AUTOINCREMENT,
                                    identificador TEXT UNIQUE,
                                    tipo_sangre TEXT,
                                    contacto TEXT,
                                    alergias TEXT,
                                    fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP''',
            "sgi_no_conformidades": '''id INTEGER PRIMARY KEY AUTOINCREMENT, fecha DATE, 
                                       origen TEXT, descripcion TEXT, responsable TEXT,
                                       causa_raiz TEXT, plan_accion TEXT, estado TEXT DEFAULT 'Abierta',
                                       empresa_id INTEGER, contrato_id INTEGER''',
            "sgi_indicadores": '''id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, meta REAL,
                                  frecuencia TEXT, responsable TEXT, valor_actual REAL,
                                  empresa_id INTEGER, contrato_id INTEGER''',
            "sgi_revision_direccion": '''id INTEGER PRIMARY KEY AUTOINCREMENT, fecha DATE,
                                         participantes TEXT, acuerdos TEXT, estado TEXT,
                                         empresa_id INTEGER, contrato_id INTEGER''',
            "sgi_historial_versiones": '''id INTEGER PRIMARY KEY AUTOINCREMENT, codigo_doc TEXT,
                                          version_antigua TEXT, fecha_cambio TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                          motivo_cambio TEXT, modificado_por TEXT,
                                          empresa_id INTEGER'''
        }

        for tabla, esquema in tablas.items():
            cursor.execute(f"CREATE TABLE IF NOT EXISTS {tabla} ({esquema})")

        # Auto-parche dinámico
        for table in ["registros", "procedimientos", "historial_informes_calidad", "historial_rigging_plans", "checklists_registros", "usuarios", "especificaciones_equipos", "eventos_confiabilidad", "reportes_incidentes", "trazabilidad_documental", "planes_accion", "evidencias_planes", "auditorias_resso", "compliance_audits", "ges_ambiental", "evaluaciones_ambientales", "vigilancia_medica_trabajadores", "repositorio_minsal", "planes_gestion_salud"]:
            for col in ["empresa_id", "contrato_id"]:
                if col == "contrato_id" and table in ["especificaciones_equipos", "usuarios"]:
                    continue
                try: cursor.execute(f"ALTER TABLE {table} ADD COLUMN {col} INTEGER DEFAULT 0")
                except sqlite3.OperationalError: pass

        # Parches específicos para Incidentes
        for col_inc in ["reportante", "afectado"]:
            try: cursor.execute(f"ALTER TABLE reportes_incidentes ADD COLUMN {col_inc} TEXT")
            except sqlite3.OperationalError: pass

        # Parches específicos para SGI (Trazabilidad y Gestión v2.0)
        for col_sgi, tipo_sgi in {"path": "TEXT", "ambito": "TEXT", "sub_area": "TEXT", "sigla_negocio": "TEXT", "correlativo": "TEXT", "empresa": "TEXT", "estado_doc": "TEXT"}.items():
            try: cursor.execute(f"ALTER TABLE procedimientos ADD COLUMN {col_sgi} {tipo_sgi}")
            except sqlite3.OperationalError: pass

        # Parches específicos para tabla usuarios (por si ya existe)
        columnas_usuarios = {
            "email": "TEXT",
            "telefono": "TEXT",
            "foto_path": "TEXT",
            "cargo": "TEXT",
            "departamento": "TEXT",
            "pref_notificaciones": "TEXT DEFAULT '{\"silenciar\": false}'",
            "pw_reset_req": "INTEGER DEFAULT 0",
            "terminos_aceptados": "INTEGER DEFAULT 0",
            "intentos_fallidos": "INTEGER DEFAULT 0",
            "ultimo_intento": "TIMESTAMP"
        }
        for col, tip in columnas_usuarios.items():
            try:
                cursor.execute(f"SELECT {col} FROM usuarios LIMIT 1")
            except sqlite3.OperationalError:
                try: cursor.execute(f"ALTER TABLE usuarios ADD COLUMN {col} {tip}")
                except sqlite3.OperationalError: pass

        # Crear índice único para email si no existe
        try: cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_usuarios_email ON usuarios(email)")
        except sqlite3.OperationalError: pass

        # Saneamiento Proactivo SGI (ON CONFLICT Fix)
        try:
            cursor.execute("DELETE FROM procedimientos WHERE rowid NOT IN (SELECT MIN(rowid) FROM procedimientos GROUP BY codigo, empresa_id)")
            cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_procedimientos_codigo ON procedimientos(codigo)")
        except sqlite3.OperationalError: pass

        columnas_proc = {
            "fecha_creacion": "DATE",
            "categoria": "TEXT DEFAULT 'Procedimiento'",
            "ambito": "TEXT",
            "sub_area": "TEXT",
            "sigla_negocio": "TEXT",
            "correlativo": "TEXT"
        }
        for col, tip in columnas_proc.items():
            try:
                cursor.execute(f"SELECT {col} FROM procedimientos LIMIT 1")
            except sqlite3.OperationalError:
                try: cursor.execute(f"ALTER TABLE procedimientos ADD COLUMN {col} {tip}")
                except sqlite3.OperationalError: pass

        for col in ["template_id", "datos_json"]:
            try: cursor.execute(f"ALTER TABLE historial_informes_calidad ADD COLUMN {col} TEXT")
            except sqlite3.OperationalError: pass

        # Parche Riesgos Críticos v4.7
        cols_rf = {
            "tipo_cc": "TEXT", 
            "periodicidad": "TEXT",
            "resp1_nom": "TEXT",
            "resp1_email": "TEXT",
            "resp2_nom": "TEXT",
            "resp2_email": "TEXT"
        }
        for col_rf, tip_rf in cols_rf.items():
            try: cursor.execute(f"ALTER TABLE riesgos_criticos_cumplimiento ADD COLUMN {col_rf} {tip_rf}")
            except sqlite3.OperationalError: pass

        try:
            cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_asistencia_unica ON asistencia_capacitacion(capacitacion_id, trabajador_id)")
        except sqlite3.OperationalError: pass

        conn.commit()

    # ── Inicializar Memoria de Ull-Trone (Independiente) ──
    try:
        from intelligence.agents.memory_engine import init_memory_db
        init_memory_db()
    except Exception as e: print(f"⚠️ Error al inicializar Memoria Ull-Trone: {e}")

def cargar_usuarios(db_path):
    """Carga los usuarios y sincroniza perfiles globales obligatorios."""
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()

        # Saneamiento de empresas vitales (Evita IntegrityError: UNIQUE constraint failed: empresas.nombre)
        # 1. Empresa 0: CGT (Administración Global)
        cursor.execute("""
            INSERT INTO empresas (id, nombre, rut, rep_legal, direccion) 
            VALUES (0, 'CGT', 'N/A', 'Directorio CGT', 'Global')
            ON CONFLICT(id) DO NOTHING
        """)

        # 2. Empresa 1: Steel Ingeniería
        emp_nombre = normalizar_texto('Steel Ingeniería')
        cursor.execute("""
            INSERT INTO empresas (id, nombre, rut, rep_legal, direccion) 
            VALUES (1, ?, '76.123.456-7', 'Miguel Rivera', 'Sector Industrial S/N, Calama')
            ON CONFLICT(id) DO NOTHING
        """, (emp_nombre,))

        # Credenciales Iniciales: se leen desde .env, st.secrets, o fallback seguro.
        # Solo se aplican si el usuario NO existe para no sobreescribir cambios manuales.
        admin_pw = _get_secret("ADMIN_PASSWORD")
        rigger_pw = _get_secret("RIGGER_PASSWORD")
        visita_pw = _get_secret("VISITA_PASSWORD")
        auditor_pw = _get_secret("AUDITOR_PASSWORD")

        usuarios_base = [
            ("miguel", admin_pw, "Global Admin", "Miguel Rivera", 0, 0, "mrivera@steel.cl", "Gerente de Operaciones", "Directorio"),
            ("francisco", admin_pw, "Global Admin", "Francisco Salvatierra", 0, 0, "fsalvatierra@steel.cl", "Director de Proyectos", "Directorio"),
            ("macarena", admin_pw, "Global Admin", "Macarena Santander", 0, 0, "msantander@steel.cl", "Jefa de Administración", "Finanzas"),
            ("rigger.cgt", rigger_pw, "Rigger", "Operador Especialista", 1, 0, "rigger@cgt.pro", "Rigger de Izaje", "Operaciones"),
            ("visita", visita_pw, "Visita", "Supervisor Cliente", 1, 0, "visita@cliente.cl", "Inspector HSE", "Seguridad"),
            ("auditor", auditor_pw, "Auditor", "Auditor Experto", 1, 0, "auditor@cgt.pro", "Auditor SGI", "Calidad")
        ]

        for u in usuarios_base:
            username, plain_pw, rol, nombre, emp_id, cont_id, email, cargo, depto = u
            
            # Verificar si el usuario ya existe
            cursor.execute("SELECT username FROM usuarios WHERE username = ?", (username,))
            exists = cursor.fetchone()

            if not exists:
                # Solo si no existe y tenemos una password (env o fallback temporal)
                effective_pw = plain_pw if plain_pw else "cgt_init_2026"
                pw_hashed = generar_hash(effective_pw)
                cursor.execute("""
                    INSERT INTO usuarios (username, pw, rol, nombre, empresa_id, contrato_asignado_id, email, cargo, departamento, terminos_aceptados)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                """, (username, pw_hashed, rol, nombre, emp_id, cont_id, email, cargo, depto))
            else:
                # Si existe, NO tocamos nada para permitir la persistencia de cambios manuales desde la UI
                pass

        conn.commit()
        df_usr = pd.read_sql_query("SELECT * FROM usuarios", conn)
        return df_usr.set_index('username').to_dict('index')

def upsert_registro(db_path, data):
    """Inserta o actualiza un registro documental asegurando la integridad de empresa/contrato."""
    with get_db_connection(db_path) as conn:
        cur = conn.cursor()

        # 1. Resolución de IDs (Prioridad: data > database > session_state)
        emp_id = data.get('empresa_id', 0)
        con_id = data.get('contrato_id', 0)

        # Si no hay empresa_id, buscar por nombre
        if not emp_id or emp_id == 0:
            emp_nom = str(data.get('empresa', '')).strip()
            if emp_nom:
                cur.execute("SELECT id FROM empresas WHERE UPPER(nombre) = UPPER(?)", (emp_nom,))
                res_e = cur.fetchone()
                emp_id = res_e[0] if res_e else 0

        # Si no hay contrato_id, buscar por nombre y empresa_id
        if not con_id or con_id == 0:
            con_nom = str(data.get('contrato', '')).strip()
            if con_nom and emp_id:
                cur.execute("SELECT id FROM contratos WHERE empresa_id = ? AND UPPER(nombre_contrato) = UPPER(?)", (emp_id, con_nom))
                res_c = cur.fetchone()
                con_id = res_c[0] if res_c else 0

        # Fallback a IDs proporcionados (Desacoplado de Streamlit)
        if not emp_id or emp_id == 0:
            emp_id = data.get('session_empresa_id', 0)
        if not con_id or con_id == 0:
            con_id = data.get('session_contrato_id', 0)

        # 2. Sincronización Global de Atributos (Nombre y Detalle)
        # Si el nombre o detalle vienen definidos, los propagamos a todos los registros históricos de este ID
        # para evitar que convivan nombres antiguos/genéricos con nuevos.
        nuevo_nombre = data.get('nombre')
        nuevo_detalle = data.get('detalle')

        if nuevo_nombre and str(nuevo_nombre).strip():
            cur.execute("UPDATE registros SET nombre=? WHERE identificador=? AND categoria=?", (nuevo_nombre, data['identificador'], data['categoria']))
            # Sincronizar también en el Maestro
            cur.execute("UPDATE maestro_entidades SET nombre=? WHERE identificador=? AND categoria=?", (nuevo_nombre, data['identificador'], data['categoria']))

        if nuevo_detalle and str(nuevo_detalle).strip():
            cur.execute("UPDATE registros SET detalle=? WHERE identificador=? AND categoria=?", (nuevo_detalle, data['identificador'], data['categoria']))
            # Sincronizar también en el Maestro
            cur.execute("UPDATE maestro_entidades SET detalle=? WHERE identificador=? AND categoria=?", (nuevo_detalle, data['identificador'], data['categoria']))

        # 3. Operación Atómica: Eliminar anterior e insertar nuevo
        cur.execute("DELETE FROM registros WHERE identificador=? AND tipo_doc=? AND empresa_id=? AND contrato_id=?",
                   (data['identificador'], data['tipo_doc'], emp_id, con_id))

        columnas = [
            'identificador', 'nombre', 'tipo_doc', 'path', 'categoria',
            'empresa_id', 'contrato_id', 'fecha_carga', 'fecha_vencimiento',
            'observaciones', 'fecha_condicion', 'estado_obs', 'tiene_observacion', 'detalle',
            'meta_horometro', 'tipo_control'
        ]

        valores = [
            data['identificador'], nuevo_nombre if nuevo_nombre else data.get('nombre'), 
            data['tipo_doc'], data.get('path', 'Sin archivo'),
            data['categoria'], emp_id, con_id, data.get('fecha_carga'), data.get('fecha_vencimiento'),
            data.get('observaciones', ''), data.get('fecha_condicion'), data.get('estado_obs', 'Resuelta'),
            data.get('tiene_observacion', 'No'), nuevo_detalle if nuevo_detalle else data.get('detalle', 'No Especificado'),
            data.get('meta_horometro', 0), data.get('tipo_control', 'Fecha')
        ]

        placeholder = ", ".join(["?"] * len(columnas))
        cur.execute(f"INSERT INTO registros ({', '.join(columnas)}) VALUES ({placeholder})", valores)
        conn.commit()

def obtener_config(db_path, clave, default=None):
    """Obtiene una configuración JSON desde la tabla config_sistema."""
    import json
    res = ejecutar_query(db_path, "SELECT valor_json FROM config_sistema WHERE clave = ?", (clave,))
    if res:
        return json.loads(res[0][0])
    return default

def guardar_config(db_path, clave, valor):
    """Guarda una configuración JSON en la tabla config_sistema."""
    import json
    valor_json = json.dumps(valor)
    ejecutar_query(db_path, """
        INSERT INTO config_sistema (clave, valor_json) VALUES (?, ?)
        ON CONFLICT(clave) DO UPDATE SET valor_json=excluded.valor_json
    """, (clave, valor_json), commit=True)

def registrar_log(db_path, usuario, accion, detalle):
    """Registra una acción en la tabla logs_actividad."""
    ejecutar_query(db_path, "INSERT INTO logs_actividad (usuario, accion, detalle) VALUES (?, ?, ?)",
                   (usuario, accion, detalle), commit=True)

def eliminar_registro_con_log(db_path, tabla, id_col, id_val, usuario):
    """
    Elimina un registro pero guarda una captura JSON en el log de auditoría.
    """
    import json

    # 1. Obtener los datos antes de borrar
    query_sel = f"SELECT * FROM {tabla} WHERE {id_col} = ?"
    df = obtener_dataframe(db_path, query_sel, (id_val,))

    if df.empty:
        return False, "Registro no encontrado para auditoría."

    # 2. Convertir a JSON
    snapshot = df.to_json(orient='records')

    # 3. Registrar Log con Snapshot (La 'Copia Fantasma')
    registrar_log(db_path, usuario, "DELETE_SNAPSHOT", f"Eliminación en {tabla} ({id_col}={id_val}). Datos: {snapshot}")

    # 4. Proceder con el borrado físico
    query_del = f"DELETE FROM {tabla} WHERE {id_col} = ?"
    ejecutar_query(db_path, query_del, (id_val,), commit=True)

    return True, "Registro eliminado y auditado con éxito."
