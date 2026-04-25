"""
==========================================
🧠 MEMORY ENGINE — v2.0 MEJORADO
==========================================
Motor de memoria y aprendizaje del sistema.

CARACTERÍSTICAS v2.0:
✅ Histórico de proyectos y desarrollos
✅ Almacenamiento de patrones y decisiones
✅ Knowledge base centralizada
✅ Búsqueda semántica de aprendizajes
✅ Recomendaciones basadas en historial
✅ Análisis de tendencias de desarrollo
✅ Caché inteligente de resultados
✅ Métricas de performance
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
import sqlite3

from src.infrastructure.database import get_db_connection, ejecutar_query, obtener_dataframe

logger = logging.getLogger(__name__)

MEMORY_DB_PATH = "ultron_memory.db"


# ============ DATA MODELS ============

@dataclass
class ProyectoMemoria:
    """Registro de proyecto desarrollado"""
    id: str
    nombre_modulo: str
    descripcion: str
    stack: str
    lineas_codigo: int
    fecha_inicio: str
    fecha_fin: str
    metas_estrategicas: str
    resultado_final: float  # Score 0-20


@dataclass
class PatronAprendizaje:
    """Patrón o best practice aprendido"""
    id: str
    categoria: str  # 'arquitectura', 'testing', 'performance', 'seguridad'
    titulo: str
    descripcion: str
    cuando_usar: str
    ejemplo_codigo: str
    tags: List[str]
    efectividad: float  # 0-100


@dataclass
class ResultadoCache:
    """Resultado cacheado para reuso"""
    id: str
    tipo_consulta: str
    parametros: Dict
    resultado: str
    fecha_creacion: str
    veces_usado: int


class MemoryEngine:
    """
    Motor de memoria y aprendizaje del sistema.
    
    Almacena:
    - Histórico de desarrollos
    - Patrones exitosos
    - Decisiones de arquitectura
    - Resultados cacheados
    - Métricas de performance
    """
    
    def __init__(self, memory_db_path: str = MEMORY_DB_PATH):
        """Inicializa el motor de memoria"""
        self.memory_db_path = memory_db_path
        self.init_memory_db()
        logger.info("MemoryEngine inicializado")
    
    def init_memory_db(self):
        """Inicializa la base de datos de memoria"""
        with get_db_connection(self.memory_db_path) as conn:
            cursor = conn.cursor()
            
            # Tabla histórico de proyectos
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS proyectos_desarrollados (
                    id TEXT PRIMARY KEY,
                    nombre_modulo TEXT,
                    descripcion TEXT,
                    stack TEXT,
                    lineas_codigo INTEGER,
                    fecha_inicio TIMESTAMP,
                    fecha_fin TIMESTAMP,
                    metas_estrategicas TEXT,
                    resultado_final REAL,
                    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Tabla patrones aprendidos
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS patrones_aprendizaje (
                    id TEXT PRIMARY KEY,
                    categoria TEXT,
                    titulo TEXT,
                    descripcion TEXT,
                    cuando_usar TEXT,
                    ejemplo_codigo TEXT,
                    tags TEXT,
                    efectividad REAL,
                    fecha_descubrimiento TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    veces_usado INTEGER DEFAULT 0
                )
            """)
            
            # Tabla caché de resultados
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cache_resultados (
                    id TEXT PRIMARY KEY,
                    tipo_consulta TEXT,
                    parametros TEXT,
                    resultado TEXT,
                    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    fecha_expiracion TIMESTAMP,
                    veces_usado INTEGER DEFAULT 0
                )
            """)
            
            # Tabla knowledge base (glosario, decisiones)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS global_knowledge (
                    id TEXT PRIMARY KEY,
                    keyword TEXT UNIQUE,
                    contexto TEXT,
                    valor TEXT,
                    categoria TEXT,
                    confianza REAL,
                    ultima_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Tabla métricas de desarrollo
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS metricas_desarrollo (
                    id TEXT PRIMARY KEY,
                    fecha_periodo TIMESTAMP,
                    modulos_mejorados INTEGER,
                    lineas_codigo_total INTEGER,
                    score_promedio REAL,
                    tiempo_promedio_horas REAL,
                    eficiencia_lineas_por_hora REAL
                )
            """)
            
            conn.commit()
        
        logger.debug("BD de memoria inicializada")
    
    # ============ HISTÓRICO DE PROYECTOS ============
    
    def registrar_proyecto(self, nombre: str, descripcion: str, stack: str,
                          lineas_codigo: int, metas: str = "",
                          resultado_final: float = 0.0) -> str:
        """
        Registra un proyecto completado en la memoria.
        
        Args:
            nombre: Nombre del módulo/proyecto
            descripcion: Descripción del trabajo
            stack: Stack tecnológico usado
            lineas_codigo: LOC generadas
            metas: Metas estratégicas
            resultado_final: Score final (0-20)
        
        Returns:
            ID del proyecto registrado
        """
        try:
            import secrets
            proyecto_id = secrets.token_hex(16)
            
            with get_db_connection(self.memory_db_path) as conn:
                conn.execute("""
                    INSERT INTO proyectos_desarrollados
                    (id, nombre_modulo, descripcion, stack, lineas_codigo,
                     fecha_inicio, fecha_fin, metas_estrategicas, resultado_final)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (proyecto_id, nombre, descripcion, stack, lineas_codigo,
                      datetime.now().isoformat(), datetime.now().isoformat(),
                      metas, resultado_final))
                conn.commit()
            
            logger.info(f"✅ Proyecto registrado: {nombre} ({lineas_codigo} LOC, score={resultado_final})")
            return proyecto_id
        
        except Exception as e:
            logger.error(f"Error registrando proyecto: {e}")
            return None
    
    def obtener_historial_proyectos(self, limite: int = 50) -> List[Dict]:
        """
        Obtiene historial de proyectos desarrollados.
        
        Args:
            limite: Máximo de registros
        
        Returns:
            Lista de proyectos
        """
        try:
            df = obtener_dataframe(self.memory_db_path,
                f"SELECT * FROM proyectos_desarrollados ORDER BY fecha_fin DESC LIMIT {limite}")
            return df.to_dict('records') if not df.empty else []
        except Exception as e:
            logger.error(f"Error obteniendo historial: {e}")
            return []
    
    def obtener_estadisticas_desarrollos(self) -> Dict:
        """Obtiene estadísticas de todos los desarrollos"""
        try:
            df = obtener_dataframe(self.memory_db_path, "SELECT * FROM proyectos_desarrollados")
            
            if df.empty:
                return {}
            
            return {
                "total_proyectos": len(df),
                "lineas_codigo_total": int(df['lineas_codigo'].sum()),
                "score_promedio": round(df['resultado_final'].mean(), 2),
                "score_maximo": round(df['resultado_final'].max(), 2),
                "modulos_por_stack": df['stack'].value_counts().to_dict(),
                "lineas_promedio_por_proyecto": int(df['lineas_codigo'].mean())
            }
        except Exception as e:
            logger.error(f"Error en estadísticas: {e}")
            return {}
    
    # ============ PATRONES APRENDIDOS ============
    
    def registrar_patron(self, categoria: str, titulo: str, descripcion: str,
                        cuando_usar: str, ejemplo_codigo: str = "",
                        tags: List[str] = None, efectividad: float = 0.8) -> str:
        """
        Registra un patrón o best practice aprendido.
        
        Args:
            categoria: Categoría del patrón
            titulo: Título del patrón
            descripcion: Descripción detallada
            cuando_usar: Cuándo se recomienda usar
            ejemplo_codigo: Código de ejemplo
            tags: Lista de tags
            efectividad: Efectividad (0-100)
        
        Returns:
            ID del patrón
        """
        try:
            import secrets
            patron_id = secrets.token_hex(16)
            
            with get_db_connection(self.memory_db_path) as conn:
                conn.execute("""
                    INSERT INTO patrones_aprendizaje
                    (id, categoria, titulo, descripcion, cuando_usar, ejemplo_codigo, tags, efectividad)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (patron_id, categoria, titulo, descripcion, cuando_usar,
                      ejemplo_codigo, json.dumps(tags or []), efectividad))
                conn.commit()
            
            logger.info(f"✅ Patrón registrado: {titulo} (efectividad={efectividad}%)")
            return patron_id
        
        except Exception as e:
            logger.error(f"Error registrando patrón: {e}")
            return None
    
    def buscar_patrones(self, termino: str = "", categoria: str = "") -> List[Dict]:
        """
        Busca patrones por término o categoría.
        
        Args:
            termino: Término a buscar
            categoria: Categoría a filtrar
        
        Returns:
            Lista de patrones encontrados
        """
        try:
            query = "SELECT * FROM patrones_aprendizaje WHERE 1=1"
            
            if categoria:
                query += f" AND categoria = '{categoria}'"
            
            if termino:
                query += f" AND (titulo LIKE '%{termino}%' OR descripcion LIKE '%{termino}%')"
            
            query += " ORDER BY efectividad DESC"
            
            df = obtener_dataframe(self.memory_db_path, query)
            return df.to_dict('records') if not df.empty else []
        
        except Exception as e:
            logger.error(f"Error buscando patrones: {e}")
            return []
    
    # ============ CACHÉ INTELIGENTE ============
    
    def guardar_en_cache(self, tipo_consulta: str, parametros: Dict,
                        resultado: str, ttl_horas: int = 24) -> str:
        """
        Guarda un resultado en caché para reuso futuro.
        
        Args:
            tipo_consulta: Tipo de consulta (ej: 'busqueda_normas', 'analisis_riesgos')
            parametros: Parámetros de la consulta
            resultado: Resultado a cachear
            ttl_horas: Tiempo de vida en horas
        
        Returns:
            ID del caché
        """
        try:
            import secrets
            cache_id = secrets.token_hex(16)
            fecha_expiracion = datetime.now() + timedelta(hours=ttl_horas)
            
            with get_db_connection(self.memory_db_path) as conn:
                conn.execute("""
                    INSERT INTO cache_resultados
                    (id, tipo_consulta, parametros, resultado, fecha_expiracion)
                    VALUES (?, ?, ?, ?, ?)
                """, (cache_id, tipo_consulta, json.dumps(parametros),
                      resultado, fecha_expiracion.isoformat()))
                conn.commit()
            
            logger.debug(f"✅ Resultado en caché: {tipo_consulta}")
            return cache_id
        
        except Exception as e:
            logger.error(f"Error guardando en caché: {e}")
            return None
    
    def buscar_en_cache(self, tipo_consulta: str, parametros: Dict) -> Optional[str]:
        """
        Busca resultado en caché.
        
        Args:
            tipo_consulta: Tipo de consulta
            parametros: Parámetros a buscar
        
        Returns:
            Resultado cacheado o None
        """
        try:
            # Buscar resultado válido
            query = f"""
            SELECT id, resultado FROM cache_resultados
            WHERE tipo_consulta = ? AND fecha_expiracion > datetime('now')
            """
            
            with get_db_connection(self.memory_db_path) as conn:
                cursor = conn.execute(query, (tipo_consulta,))
                resultado = cursor.fetchone()
            
            if resultado:
                cache_id, resultado_str = resultado
                # Incrementar contador de uso
                with get_db_connection(self.memory_db_path) as conn:
                    conn.execute(
                        "UPDATE cache_resultados SET veces_usado = veces_usado + 1 WHERE id = ?",
                        (cache_id,)
                    )
                    conn.commit()
                
                logger.debug(f"✅ Resultado del caché usado")
                return resultado_str
        
        except Exception as e:
            logger.error(f"Error buscando en caché: {e}")
        
        return None
    
    # ============ KNOWLEDGE BASE ============
    
    def guardar_conocimiento(self, keyword: str, contexto: str, valor: str,
                            categoria: str = "general", confianza: float = 0.8) -> bool:
        """
        Guarda un conocimiento en la base.
        
        Args:
            keyword: Palabra clave
            contexto: Contexto de aplicación
            valor: Valor del conocimiento
            categoria: Categoría
            confianza: Nivel de confianza (0-1)
        
        Returns:
            True si se guardó exitosamente
        """
        try:
            import secrets
            with get_db_connection(self.memory_db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO global_knowledge
                    (id, keyword, contexto, valor, categoria, confianza)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (secrets.token_hex(16), keyword, contexto, valor,
                      categoria, confianza))
                conn.commit()
            
            logger.debug(f"✅ Conocimiento guardado: {keyword}")
            return True
        
        except Exception as e:
            logger.error(f"Error guardando conocimiento: {e}")
            return False


# ============ FUNCIONES LEGACY ============

def init_memory_db(path=MEMORY_DB_PATH):
    """LEGACY: Compatibilidad con código antiguo"""
    engine = obtener_memory_engine(path)
    engine.init_memory_db()


def save_project_memory(nombre, desc, stack, codigo, metas=""):
    """LEGACY: Compatibilidad con código antiguo"""
    engine = obtener_memory_engine()
    lineas = len(codigo.split('\n')) if codigo else 0
    engine.registrar_proyecto(nombre, desc, stack, lineas, metas)


def get_all_projects_memory():
    """LEGACY: Compatibilidad con código antiguo"""
    engine = obtener_memory_engine()
    return engine.obtener_historial_proyectos()


def get_project_details(project_id):
    """LEGACY: Compatibilidad con código antiguo"""
    engine = obtener_memory_engine()
    proyectos = engine.obtener_historial_proyectos(limite=1000)
    return next((p for p in proyectos if p.get('id') == project_id), None)


# ============ SINGLETON ============

_engine_memory = None

def obtener_memory_engine(memory_db_path: str = MEMORY_DB_PATH) -> MemoryEngine:
    """Obtiene instancia singleton del MemoryEngine"""
    global _engine_memory
    if _engine_memory is None:
        _engine_memory = MemoryEngine(memory_db_path)
    return _engine_memory

# ============ INTEGRACIÓN NEURAL (CONTEXTO Y CHAT) ============

def obtener_contexto_neuronal(DB_PATH, query_usuario=""):
    """
    Recupera hitos de memoria, leyes relevantes y contexto de proyecto 
    para inyectar en el cerebro de Ull-Trone.
    """
    contexto = "\n--- 🧠 MEMORIA NEURONAL ACTIVA ---\n"
    
    # 1. Recuperar Hitos de Proyecto Recientes
    try:
        from src.infrastructure.database import obtener_dataframe
        df_p = obtener_dataframe(DB_PATH, "SELECT nombre_modulo, descripcion, fecha FROM projects_history ORDER BY fecha DESC LIMIT 3")
        if not df_p.empty:
            contexto += "\nPROYECTOS RECIENTES EN DESARROLLO:\n"
            for _, r in df_p.iterrows():
                contexto += f"- [{r['fecha']}] {r['nombre_modulo']}: {r['descripcion']}\n"
    except: pass

    # 2. Recuperar Fragmentos de Conversación Críticos (Memoria de corto plazo)
    try:
        from src.infrastructure.database import obtener_dataframe
        df_c = obtener_dataframe(DB_PATH, "SELECT role, content FROM chat_ultron_history ORDER BY fecha DESC LIMIT 5")
        if not df_c.empty:
            contexto += "\nCONTEXTO DE CONVERSACIÓN RECIENTE:\n"
            for _, r in df_c.iterrows():
                contexto += f"- {r['role'].upper()}: {r['content'][:200]}...\n"
    except: pass

    # 3. Escaneo de "Cerebro Legal" (Si existe carpeta de soporte)
    try:
        import os
        from config.config import SUPPORT_DIR
        legal_path = os.path.join(SUPPORT_DIR, "Leyes")
        if os.path.exists(legal_path):
            keywords = [w for w in query_usuario.lower().split() if len(w) > 3]
            archivos = os.listdir(legal_path)
            coincidencias = []
            for arc in archivos:
                if any(k in arc.lower() for k in keywords):
                    coincidencias.append(arc)
            
            if coincidencias:
                contexto += f"\nDOCUMENTACIÓN LEGAL RELACIONADA DETECTADA: {', '.join(coincidencias)}\n"
    except: pass

    contexto += "\n--- FIN DE CONTEXTO ---\n"
    return contexto

def guardar_hito_memoria(DB_PATH, nombre_modulo, descripcion):
    """Registra un hito importante en la base de datos de proyectos."""
    from src.infrastructure.database import ejecutar_query
    query = "INSERT INTO projects_history (nombre_modulo, descripcion) VALUES (?, ?)"
    ejecutar_query(DB_PATH, query, (nombre_modulo, descripcion), commit=True)
