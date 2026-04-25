"""
==========================================
🎯 RESSO ENGINE — v2.0 MEJORADO
==========================================
Motor de gestión RESSO (Requisitos Específicos del SG).

CARACTERÍSTICAS v2.0:
✅ Evaluaciones RESSO automáticas (48 puntos)
✅ Seguimiento de cobertura de personal
✅ Mapeo de requisitos a trabajadores
✅ Cálculo de semáforos (rojo/amarillo/verde)
✅ Reportes de trazabilidad
✅ Auditoría de cambios
✅ Integración con registros personales
✅ Histórico de evaluaciones
"""

import os
import shutil
import logging
import json
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime

from src.infrastructure.database import ejecutar_query, obtener_dataframe, obtener_conexion, upsert_registro

logger = logging.getLogger(__name__)


# ============ DATA MODELS ============

@dataclass
class PuntoResso:
    """Representa un punto/requisito RESSO"""
    numero: int
    titulo: str
    requerimiento_doc: str
    descripcion: str
    categoria: str


@dataclass
class CoberturaPersonal:
    """Registro de cobertura de capacitación/evaluación"""
    punto_resso_id: int
    trabajador_id: str
    trabajador_nombre: str
    cumple: bool
    fecha_cumplimiento: str
    evidencia_path: str
    auditor_id: str


@dataclass
class ReporteRessoCoberturaClass:
    """Reporte de cobertura RESSO"""
    id: str
    empresa_id: str
    contrato_id: str
    fecha_reporte: str
    punto_numero: int
    total_trabajadores: int
    trabajadores_cumplimiento: int
    porcentaje_cobertura: float
    semaforo: str  # 'verde' (90%+), 'amarillo' (50-89%), 'rojo' (<50%)
    brechas: List[str]


class RessóEngine:
    """
    Motor de gestión de requisitos RESSO.
    
    Características:
    - Evaluaciones de 48 puntos RESSO
    - Seguimiento de cobertura
    - Semáforos inteligentes
    - Reportes de trazabilidad
    - Auditoría completa
    """
    
    # Mapeo oficial de puntos RESSO
    PUNTOS_RESSO = {
        0: "Certificaciones empresa",
        1: "Programa SST",
        2: "Política",
        3: "Indicadores del Prog SST",
        4: "IPER legal",
        5: "Visitas fiscalizadores",
        6: "IPER",
        7: "Programa validado OAL",
        8: "GES",
        9: "Mapa de riesgo higiene",
        10: "Autoevaluación ECF y RC",
        11: "Autoevaluación EST",
        12: "Liderazgo",
        13: "Seguridad conductual",
        14: "Aprendizaje",
        15: "Investigación de incidentes",
        16: "Plan de emergencias",
        17: "Programa Simulacro",
        18: "Capacitación plan emergencias",
        19: "Simulacro documental",
        20: "IRL",
        21: "Programa BEL",
        22: "Participación y consulta",
        23: "Participación CPHS de Faena",
        24: "Requisitos RESSO titulo VI",
        25: "LOD",
        26: "Libro Sernageomin",
        27: "Revisión documental",
        28: "PTS del contrato",
        29: "Responsables ECF, EST",
        30: "Auditorias ECF. EST y RC",
        31: "Comunicación fiscalización entidades via LOD",
        32: "Programa entidades fiscalizadoras",
        33: "Categorización",
        34: "Capacitación métodos investigación",
        35: "Proc gestión accidentes",
        36: "Plan ident, difusión y control",
        37: "Reglamento interno",
        38: "Difusión PTS y normativa",
        39: "Riesgos inherentes altos",
        40: "Reunión inicio",
        41: "Reunión Arranque",
        42: "CPHS",
        43: "Informe mensual",
        44: "Estadísticas Mensuales",
        45: "Plan de capacitación faltas - infracciones",
        46: "ADC",
        47: "RESSO sin número"
    }
    
    def __init__(self, db_path: str = None):
        """Inicializa el motor RESSO"""
        self.db_path = db_path
        self._crear_tablas()
        logger.info("RessóEngine inicializado")
    
    def _crear_tablas(self) -> None:
        """Crea tablas para seguimiento RESSO"""
        if not self.db_path:
            return
        
        tables = [
            """
            CREATE TABLE IF NOT EXISTS puntos_resso (
                id TEXT PRIMARY KEY,
                numero INTEGER UNIQUE,
                titulo TEXT,
                requerimiento_doc TEXT,
                descripcion TEXT,
                categoria TEXT,
                fecha_ingreso TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS cobertura_resso (
                id TEXT PRIMARY KEY,
                punto_numero INTEGER,
                trabajador_id TEXT,
                trabajador_nombre TEXT,
                empresa_id TEXT,
                contrato_id TEXT,
                cumple BOOLEAN,
                fecha_cumplimiento TIMESTAMP,
                evidencia_path TEXT,
                auditor_id TEXT,
                fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS reportes_resso_cobertura (
                id TEXT PRIMARY KEY,
                empresa_id TEXT,
                contrato_id TEXT,
                fecha_reporte TIMESTAMP,
                punto_numero INTEGER,
                total_trabajadores INTEGER,
                trabajadores_cumplimiento INTEGER,
                porcentaje_cobertura REAL,
                semaforo TEXT,
                brechas TEXT  -- JSON
            )
            """
        ]
        
        try:
            conexion = obtener_conexion(self.db_path)
            for query in tables:
                conexion.execute(query)
            conexion.commit()
            conexion.close()
            logger.debug("Tablas RESSO creadas")
        except Exception as e:
            logger.error(f"Error creando tablas: {e}")
    
    def registrar_cobertura(self, punto_numero: int, trabajador_id: str,
                           trabajador_nombre: str, empresa_id: str,
                           contrato_id: str, cumple: bool,
                           evidencia_path: str = "", auditor_id: str = "system") -> str:
        """
        Registra cobertura de trabajador en un punto RESSO.
        
        Args:
            punto_numero: Número del punto RESSO (0-47)
            trabajador_id: ID del trabajador
            trabajador_nombre: Nombre del trabajador
            empresa_id: ID de la empresa
            contrato_id: ID del contrato
            cumple: True si cumple el requisito
            evidencia_path: Ruta de evidencia
            auditor_id: ID del auditor
        
        Returns:
            ID del registro de cobertura
        """
        try:
            import secrets
            cobertura_id = secrets.token_hex(16)
            
            if not self.db_path:
                return cobertura_id
            
            query = """
            INSERT INTO cobertura_resso
            (id, punto_numero, trabajador_id, trabajador_nombre, empresa_id, contrato_id,
             cumple, fecha_cumplimiento, evidencia_path, auditor_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            conexion = obtener_conexion(self.db_path)
            conexion.execute(query, (
                cobertura_id, punto_numero, trabajador_id, trabajador_nombre,
                empresa_id, contrato_id, cumple, datetime.now().isoformat(),
                evidencia_path, auditor_id
            ))
            conexion.commit()
            conexion.close()
            
            logger.debug(f"✅ Cobertura registrada: {trabajador_nombre} - Punto {punto_numero}")
            return cobertura_id
        
        except Exception as e:
            logger.error(f"Error registrando cobertura: {e}")
            return None
    
    def calcular_cobertura_punto(self, punto_numero: int, empresa_id: str,
                                contrato_id: str) -> ReporteRessoCoberturaClass:
        """
        Calcula cobertura total para un punto RESSO.
        
        Args:
            punto_numero: Número del punto RESSO
            empresa_id: ID de la empresa
            contrato_id: ID del contrato
        
        Returns:
            ReporteRessoCoberturaClass con semáforo
        """
        if not self.db_path:
            return None
        
        try:
            # Contar trabajadores activos
            query_total = """
            SELECT COUNT(DISTINCT identificador) as count
            FROM registros
            WHERE categoria = 'Personal' AND empresa_id = ? AND contrato_id = ?
            """
            
            # Contar cumplimiento
            query_cumplidos = """
            SELECT COUNT(DISTINCT trabajador_id) as count
            FROM cobertura_resso
            WHERE punto_numero = ? AND empresa_id = ? AND contrato_id = ? AND cumple = 1
            """
            
            # Identificar brechas
            query_brechas = """
            SELECT DISTINCT r.nombre
            FROM registros r
            LEFT JOIN cobertura_resso cr 
              ON r.identificador = cr.trabajador_id 
              AND cr.punto_numero = ?
              AND cr.empresa_id = ?
              AND cr.contrato_id = ?
            WHERE r.categoria = 'Personal' 
              AND r.empresa_id = ? 
              AND r.contrato_id = ?
              AND cr.id IS NULL
            """
            
            df_total = obtener_dataframe(self.db_path, query_total, (empresa_id, contrato_id))
            df_cumplidos = obtener_dataframe(self.db_path, query_cumplidos, 
                                            (punto_numero, empresa_id, contrato_id))
            df_brechas = obtener_dataframe(self.db_path, query_brechas,
                                          (punto_numero, empresa_id, contrato_id, 
                                           empresa_id, contrato_id))
            
            total = df_total.iloc[0]['count'] if not df_total.empty else 0
            cumplidos = df_cumplidos.iloc[0]['count'] if not df_cumplidos.empty else 0
            brechas = df_brechas['nombre'].tolist() if not df_brechas.empty else []
            
            porcentaje = (cumplidos / total * 100) if total > 0 else 0
            
            # Determinar semáforo
            if porcentaje >= 90:
                semaforo = "verde"
            elif porcentaje >= 50:
                semaforo = "amarillo"
            else:
                semaforo = "rojo"
            
            reporte = ReporteRessoCoberturaClass(
                id=f"RESSO_{punto_numero}_{empresa_id}_{datetime.now().strftime('%Y%m%d')}",
                empresa_id=empresa_id,
                contrato_id=contrato_id,
                fecha_reporte=datetime.now().isoformat(),
                punto_numero=punto_numero,
                total_trabajadores=total,
                trabajadores_cumplimiento=cumplidos,
                porcentaje_cobertura=round(porcentaje, 1),
                semaforo=semaforo,
                brechas=brechas
            )
            
            # Guardar reporte
            query_insert = """
            INSERT INTO reportes_resso_cobertura
            (id, empresa_id, contrato_id, fecha_reporte, punto_numero, total_trabajadores,
             trabajadores_cumplimiento, porcentaje_cobertura, semaforo, brechas)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            conexion = obtener_conexion(self.db_path)
            conexion.execute(query_insert, (
                reporte.id, empresa_id, contrato_id, reporte.fecha_reporte,
                punto_numero, total, cumplidos, reporte.porcentaje_cobertura,
                semaforo, json.dumps(brechas)
            ))
            conexion.commit()
            conexion.close()
            
            emoji = "🟢" if semaforo == "verde" else "🟡" if semaforo == "amarillo" else "🔴"
            logger.info(f"{emoji} Punto {punto_numero}: {porcentaje:.1f}% ({cumplidos}/{total})")
            
            return reporte
        
        except Exception as e:
            logger.error(f"Error calculando cobertura: {e}")
            return None
    
    def generar_reporte_global_resso(self, empresa_id: str, contrato_id: str) -> Dict:
        """
        Genera reporte global de todos los 48 puntos RESSO.
        
        Args:
            empresa_id: ID de empresa
            contrato_id: ID de contrato
        
        Returns:
            Dict con estadísticas globales
        """
        if not self.db_path:
            return {}
        
        try:
            resultados = {}
            total_puntos = len(self.PUNTOS_RESSO)
            puntos_verde = 0
            puntos_amarillo = 0
            puntos_rojo = 0
            
            for numero, titulo in self.PUNTOS_RESSO.items():
                reporte = self.calcular_cobertura_punto(numero, empresa_id, contrato_id)
                if reporte:
                    resultados[numero] = {
                        "titulo": titulo,
                        "cobertura": reporte.porcentaje_cobertura,
                        "semaforo": reporte.semaforo,
                        "cumplidos": reporte.trabajadores_cumplimiento,
                        "total": reporte.total_trabajadores
                    }
                    
                    if reporte.semaforo == "verde":
                        puntos_verde += 1
                    elif reporte.semaforo == "amarillo":
                        puntos_amarillo += 1
                    else:
                        puntos_rojo += 1
            
            reporte_global = {
                "fecha_reporte": datetime.now().isoformat(),
                "empresa_id": empresa_id,
                "contrato_id": contrato_id,
                "total_puntos": total_puntos,
                "puntos_verde": puntos_verde,
                "puntos_amarillo": puntos_amarillo,
                "puntos_rojo": puntos_rojo,
                "porcentaje_cumplimiento_general": round((puntos_verde / total_puntos * 100), 1),
                "detalles": resultados
            }
            
            logger.info(f"✅ Reporte RESSO global: {puntos_verde}/{total_puntos} puntos verdes")
            return reporte_global
        
        except Exception as e:
            logger.error(f"Error generando reporte global: {e}")
            return {}


# ============ SINGLETON ============

_engine_resso = None

def obtener_resso_engine(db_path: str = None) -> RessóEngine:
    """Obtiene instancia singleton del RessóEngine"""
    global _engine_resso
    if _engine_resso is None:
        from config.config import DB_PATH
        _engine_resso = RessóEngine(db_path or DB_PATH)
    return _engine_resso


# ============ FUNCIONES LEGACY (COMPONENTES STREAMLIT) ============

import os
import shutil
import streamlit as st

def clean_folder_name(texto):
    from src.infrastructure.archivos import normalizar_texto
    return normalizar_texto(texto).strip().replace(" ", "_")

def guardar_evidencia_local(archivo, empresa, contrato, numero_punto, texto_punto):
    if not archivo: return None
    from src.infrastructure.archivos import normalizar_texto
    emp_clean = normalizar_texto(empresa).strip().replace(" ", "_").upper()
    con_clean = normalizar_texto(contrato).strip().replace(" ", "_").upper() if contrato else "SIN_CONTRATO"

    # Exact folder mapping matching the original RESSO 2026 directory
    folder_mapping = {
        0: "0.-Certificaciones empresa", 1: "1.-Programa SST", 2: "2.-Politica", 3: "3.-Indicadores del Prog SST",
        4: "4.-IPER legal", 5: "5.-Visitas fiscalizadores", 6: "6.-IPER", 7: "7.-Programa validado OAL",
        8: "8.-GES", 9: "9.-Mapa de riesgo higiene", 10: "10.-Autoevaluación ECF y RC", 11: "11.-Autoevaluación EST",
        12: "12.-Liderazgo", 13: "13.-Seguridad conductual", 14: "14.-Aprendizaje", 15: "15.-Investigación de incidentes",
        16: "16.-Plan de emergencias", 17: "17.-Programa Simulacro", 18: "18.-Capacitación plan emergencias", 19: "19.-Simulacro documental",
        20: "20.-IRL", 21: "21.-Programa BEL", 22: "22.-Participación y consulta", 23: "23.-Participación CPHS de Faena",
        24: "24.-Requisitos RESSO titulo VI", 25: "25.-LOD", 26: "26.-libro Sernageomin", 27: "27.-Revisión documental",
        28: "28.-PTS del contrato", 29: "29.-Responsables ECF, EST", 30: "30.-Auditorias ECF. EST y RC", 31: "31.-Comunicación fiscalización entidades via LOD",
        32: "32.-Programa entidades fiscalizadoras", 33: "33.-Categorización", 34: "34.-Capacitación metodos investigación", 35: "35.-Proc gestion accidentes",
        36: "36.-Plan ident, difusión y control", 37: "37.-Reglamento interno", 38: "38.-Difusión PTS y normativa", 39: "39.-Riesgos inherentes altos",
        40: "40.-Reunión inicio", 41: "41.-Reunion Arranque", 42: "42.-CPHS", 43: "43.-Informe mensual", 44: "44.-Estadisticas Mensuales",
        45: "45.-Plan de capacitación faltas - infracciones", 46: "46.-ADC", 47: "47.- RESSO sin numero"
    }

    fecha_hoy = datetime.now().strftime("%Y-%m-%d")
    folder_name = folder_mapping.get(numero_punto, f"{numero_punto}.- {clean_folder_name(texto_punto)}")

    ruta_base = os.path.join(os.getcwd(), "CGT_DATA", emp_clean, con_clean, "Gestion_Preventiva", "Auditorias_RESSO", fecha_hoy, folder_name)
    os.makedirs(ruta_base, exist_ok=True)

    # Conservamos el nombre original del archivo aportado por el usuario
    safe_original_name = clean_folder_name(os.path.splitext(archivo.name)[0])
    extension = os.path.splitext(archivo.name)[1]
    filename = f"{datetime.now().strftime('%H%M%S')}_{safe_original_name}{extension}"
    full_path = os.path.join(ruta_base, filename).replace("\\", "/")

    with open(full_path, "wb") as f:
        f.write(archivo.getbuffer())
    return full_path

def render_semaforo_difusion(q_num, requerimiento_doc, filtros, db_path):
    st.markdown("---")
    st.markdown("#### 👥 Cobertura de Personal (Semáforo Inteligente)")
    st.caption(f"**Requisito a trazar en ficha del trabajador:** `{requerimiento_doc}`")

    emp_id = filtros.get('empresa_id', 0)
    con_id = filtros.get('contrato_id', 0)
    emp_nom = filtros.get('empresa_nom', 'N/A')
    con_nom = filtros.get('contrato_nom', 'N/A')

    archivos = st.file_uploader(f"📎 1. Sube el Registro de Asistencia / Evaluación", type=["pdf", "jpg", "png"], accept_multiple_files=True, key=f"file_sem_{q_num}")

    # Obtener Trabajadores Activos
    query_w = "SELECT DISTINCT identificador, nombre FROM registros WHERE categoria='Personal' AND empresa_id=? AND contrato_id=?"
    df_w = obtener_dataframe(db_path, query_w, (emp_id, con_id))

    if df_w.empty:
        st.warning("⚠️ No se encontraron trabajadores activos cargados para este contrato. El semáforo no puede operar hasta que los cargues en Trazabilidad de Personal.")
        return None

    df_w['pildora'] = df_w['identificador'] + " - " + df_w['nombre']
    lista_trabajadores = df_w['pildora'].tolist()

    seleccionados = st.multiselect("👥 2. Selecciona los asistentes (Cruzarán con Base de Datos):", lista_trabajadores, key=f"sel_{q_num}")

    faltantes = [t for t in lista_trabajadores if t not in seleccionados]
    st.session_state[f"brechas_q_{q_num}"] = faltantes

    total_activos = len(lista_trabajadores)
    total_sel = len(seleccionados)
    cobertura = (total_sel / total_activos * 100) if total_activos > 0 else 0

    c1, c2 = st.columns([1, 2])
    with c1:
        color = "🟢" if cobertura >= 90 else "🟡" if cobertura >= 50 else "🔴"
        st.markdown(f"### {color} {cobertura:.1f}%")
        st.caption(f"{total_sel} de {total_activos} trabajadores.")

    recomendacion = "100" if cobertura >= 90 else "50" if cobertura >= 50 else "0"
    with c2:
        if cobertura >= 90: st.success("Cobertura óptima. Sugerencia de puntaje: **100%**")
        elif cobertura >= 50: st.warning("Cobertura parcial. Sugerencia de puntaje: **50%**")
        else: st.error("Cobertura deficiente. Sugerencia de puntaje: **0%**")

    if st.button(f"🚀 Procesar Documento y Actualizar {total_sel} Fichas Reales", key=f"btn_sync_{q_num}"):
        if not archivos:
            st.error("Debes subir al menos un archivo primero.")
        elif total_sel == 0:
            st.error("Debes seleccionar al menos un trabajador.")
        else:
            rutas_evidencias = []
            for arch in archivos:
                p_ev = guardar_evidencia_local(arch, emp_nom, con_nom, q_num, requerimiento_doc)
                if p_ev: rutas_evidencias.append(p_ev)

            # Inyectar en maestro personal (Usamos el primer archivo como comprobante visual en la ficha)
            path_principal = rutas_evidencias[0] if rutas_evidencias else "Sin archivo"
            for sel in seleccionados:
                rut = sel.split(" - ")[0]
                nombre = sel.split(" - ")[1]
                upsert_registro(db_path, {
                    "identificador": rut,
                    "nombre": nombre,
                    "tipo_doc": requerimiento_doc,
                    "categoria": "Personal",
                    "estado_obs": "Resuelta",
                    "empresa_id": emp_id,
                    "contrato_id": con_id,
                    "empresa": emp_nom,
                    "contrato": con_nom,
                    "fecha_carga": str(datetime.now().date()),
                    "fecha_vencimiento": "2050-01-01",
                    "observaciones": "Inyectado vía Auditoría RESSO",
                    "detalle": "Auto-Sincronización RESSO",
                    "path": path_principal
                })
            st.success(f"✅ ¡Éxito! Expedientes actualizados de {total_sel} trabajadores.")
            return rutas_evidencias
    return None

def render_evidencia_simple(q_id, empresa, contrato):
    st.markdown("---")
    archivos = st.file_uploader("📎 Adjuntar Evidencia Documental (Opcional)", type=["pdf", "jpg", "png", "docx", "xlsx"], accept_multiple_files=True, key=f"evid_{q_id}")
    if archivos:
        st.info("Los archivos se guardarán adjuntos a esta auditoría al presionar 'Calcular y Guardar'.")
    return archivos

def render_modulo_bel(q_id, empresa, contrato):
    st.markdown("---")
    st.markdown("#### 🎓 Sub-Módulo Trabajadores BEL (Baja Experiencia)")
    st.info("La auditoría verificará el ciclo documental BEL completo de al menos 1 trabajador de muestra.")
    c1, c2 = st.columns(2)
    evd_1 = c1.file_uploader("1. Carta Inicio de Programa", accept_multiple_files=True, key=f"bel1_{q_id}")
    evd_2 = c2.file_uploader("2. Asignación de Tutor", accept_multiple_files=True, key=f"bel2_{q_id}")
    c3, c4 = st.columns(2)
    evd_3 = c3.file_uploader("3. Evaluaciones (8 Semanas)", accept_multiple_files=True, key=f"bel3_{q_id}")
    evd_4 = c4.file_uploader("4. Carta de Egreso / Prueba", accept_multiple_files=True, key=f"bel4_{q_id}")

    st.caption("Los documentos se anexarán al expediente final de la auditoría.")
    all_files = []
    for lst in [evd_1, evd_2, evd_3, evd_4]:
        if lst: all_files.extend(lst)
    return all_files

def render_planes_emergencia(q_id, empresa, contrato):
    st.markdown("---")
    st.markdown("#### 🚨 Sub-Módulo Planes de Emergencia")
    st.info("Para este punto, el RESSO evalúa 3 niveles de planes.")
    c1, c2, c3 = st.columns(3)
    evd_1 = c1.file_uploader("📄 Plan Propio Empresa", accept_multiple_files=True, key=f"pe1_{q_id}")
    evd_2 = c2.file_uploader("📄 Plan del Sector (Ej. Mina)", accept_multiple_files=True, key=f"pe2_{q_id}")
    evd_3 = c3.file_uploader("📄 Plan de Emergencia Divisional", accept_multiple_files=True, key=f"pe3_{q_id}")
    all_files = []
    for lst in [evd_1, evd_2, evd_3]:
        if lst: all_files.extend(lst)
    return all_files

def render_cphs(q_id, empresa, contrato):
    st.markdown("---")
    st.markdown("#### 👷 Sub-Módulo Gestión Paritario (CPHS)")
    c1, c2, c3 = st.columns(3)
    evd_1 = c1.file_uploader("📄 Actas / Constitución", accept_multiple_files=True, key=f"cphs1_{q_id}")
    evd_2 = c2.file_uploader("📄 Programa e Inspecciones", accept_multiple_files=True, key=f"cphs2_{q_id}")
    evd_3 = c3.file_uploader("📄 Cartas y Resoluciones", accept_multiple_files=True, key=f"cphs3_{q_id}")
    all_files = []
    for lst in [evd_1, evd_2, evd_3]:
        if lst: all_files.extend(lst)
    return all_files
def render_titulo_vi(q_id, empresa, contrato):
    st.markdown("---")
    st.markdown("#### 📁 Sub-Módulo Título VI: Sistema de Gestión (24 Requisitos)")
    st.info("Sube la evidencia fraccionada por punto del requerimiento (Punto 1 al 24). Los archivos vacíos serán ignorados.")

    # 4 columns for a compact 24-element grid
    cols = st.columns(4)
    all_files = []

    for i in range(1, 25):
        c_idx = (i - 1) % 4
        evd = cols[c_idx].file_uploader(f"Punto {i}", accept_multiple_files=True, key=f"tvi_{i}_{q_id}")
        if evd:
            all_files.extend(evd)

    st.caption("Los documentos se guardarán individualmente en la carpeta del Punto 24.")
    return all_files
