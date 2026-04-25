"""
==========================================
📊 RISK MANAGER ENGINE — v2.0 MEJORADO
==========================================
Motor unificado de gestión de riesgos.

CARACTERÍSTICAS v2.0:
✅ Integración de RF01-RF30
✅ Búsqueda y filtrado unificado
✅ Indexación optimizada
✅ Análisis de patrones
✅ Histórico de riesgos
✅ Integración BD
✅ Métricas de riesgo
"""
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import json

from core.fatality_risks_rf01_rf10 import FATALITY_RISKS_RF01_RF10
from core.fatality_risks_rf11_rf20 import FATALITY_RISKS_RF11_RF20
from core.fatality_risks_rf21_rf30 import FATALITY_RISKS_RF21_RF30
from core.other_risks import OTHER_RISKS_EXPANDIDO, obtener_other_risks_engine
from src.infrastructure.database import obtener_conexion

logger = logging.getLogger(__name__)


# ============ DATA MODELS ============

@dataclass
class EvaluacionRiesgo:
    """Evaluación de riesgo fatal"""
    id: str
    codigo_riesgo: str
    descripcion: str
    nivel_riesgo: str  # Bajo, Medio, Alto, Crítico
    evaluacion_ccp: str
    evaluacion_ccm: str
    controles_implementados: List[str]
    fecha_evaluacion: str


class RiskManagerEngine:
    """Motor unificado de gestión de riesgos fatales"""
    
    def __init__(self, db_path: str = None):
        """Inicializa el gestor de riesgos"""
        self.db_path = db_path
        self.riesgos = {}
        self._crear_indice_unificado()
        self._crear_tablas()
        logger.info(f"RiskManagerEngine inicializado con {len(self.riesgos)} riesgos")
    
    def _crear_indice_unificado(self) -> None:
        """Crea índice único de todos los riesgos"""
        self.riesgos = {
            **FATALITY_RISKS_RF01_RF10,
            **FATALITY_RISKS_RF11_RF20,
            **FATALITY_RISKS_RF21_RF30
        }
        logger.debug(f"Índice unificado: {len(self.riesgos)} riesgos")
    
    def _crear_tablas(self) -> None:
        """Crea tablas para evaluaciones"""
        if not self.db_path:
            return
        
        tables = [
            """
            CREATE TABLE IF NOT EXISTS evaluaciones_riesgos (
                id TEXT PRIMARY KEY,
                codigo_riesgo TEXT,
                descripcion TEXT,
                nivel_riesgo TEXT,
                evaluacion_ccp TEXT,
                evaluacion_ccm TEXT,
                controles_implementados TEXT,
                empresa_id TEXT,
                fecha_evaluacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        ]
        
        try:
            conexion = obtener_conexion(self.db_path)
            for query in tables:
                conexion.execute(query)
            conexion.commit()
            conexion.close()
            logger.debug("Tablas de riesgos creadas")
        except Exception as e:
            logger.error(f"Error creando tablas: {e}")


class RiskManager:
    """
    Gestor centralizado de riesgos fatales (RF01-RF30).
    Integra los 3 módulos en un único punto de acceso.
    """
    
    def __init__(self):
        """Inicializa el gestor y crea índices unificados"""
        self.riesgos = {}
        self.otros_riesgos = OTHER_RISKS_EXPANDIDO
        self.other_risks_engine = None
        self._crear_indice_unificado()
        self._crear_indice_busqueda()
        logger.info(f"Risk Manager inicializado con {len(self.riesgos)} riesgos fatales y {len(self.otros_riesgos)} otros riesgos")
    
    def _crear_indice_unificado(self) -> None:
        """Crea índice único de todos los riesgos de los 3 módulos"""
        self.riesgos = {
            **FATALITY_RISKS_RF01_RF10,
            **FATALITY_RISKS_RF11_RF20,
            **FATALITY_RISKS_RF21_RF30
        }
        logger.debug(f"Índice unificado creado: {len(self.riesgos)} riesgos")
    
    def _crear_indice_busqueda(self) -> None:
        """Crea índice de búsqueda por palabras clave para optimizar búsquedas"""
        self.indice_palabras = {}
        
        for rf_id, datos_riesgo in self.riesgos.items():
            # Extraer palabras clave del RF ID (ej: "RF 01 ENERGÍA ELÉCTRICA")
            palabras_clave = rf_id.lower().split()
            
            for palabra in palabras_clave:
                if palabra not in self.indice_palabras:
                    self.indice_palabras[palabra] = []
                self.indice_palabras[palabra].append(rf_id)
        
        logger.debug(f"Índice de búsqueda creado: {len(self.indice_palabras)} palabras clave")
    
    # ============ ACCESO A RIESGOS ============
    
    def obtener_riesgo(self, rf_id: str) -> Optional[Dict]:
        """
        Obtiene un riesgo específico por ID.
        
        Args:
            rf_id: ID del riesgo (ej: "RF 01 ENERGÍA ELÉCTRICA")
        
        Returns:
            Dict con datos del riesgo o None si no existe
        """
        return self.riesgos.get(rf_id)
    
    def listar_todos_riesgos(self) -> List[str]:
        """
        Lista todos los riesgos fatales disponibles (RF01-RF30).
        
        Returns:
            Lista de IDs de riesgos ordenados
        """
        return sorted(self.riesgos.keys())
    
    def contar_riesgos(self) -> int:
        """Retorna total de riesgos cargados"""
        return len(self.riesgos)
    
    # ============ OTROS RIESGOS (NO FATALES) ============
    
    def obtener_todos_otros_riesgos(self) -> List[Dict]:
        """Retorna la lista completa de otros riesgos (no fatales)."""
        return self.otros_riesgos
    
    def obtener_otros_riesgos_por_categoria(self, categoria: str) -> List[Dict]:
        """Filtra otros riesgos por categoría (ej: 'Ergonómico')."""
        return [r for r in self.otros_riesgos if r.get('categoria') == categoria]
    
    def obtener_motor_otros_riesgos(self, db_path: str = None):
        """Retorna la instancia del motor de evaluación de otros riesgos."""
        if self.other_risks_engine is None:
            self.other_risks_engine = obtener_other_risks_engine(db_path)
        return self.other_risks_engine
    
    # ============ ACCESO A PREGUNTAS ============
    
    def obtener_preguntas_trabajador(self, rf_id: str) -> List[str]:
        """
        Obtiene lista de preguntas CCP/CCM para el trabajador.
        
        Args:
            rf_id: ID del riesgo
        
        Returns:
            Lista de preguntas para trabajador
        """
        riesgo = self.obtener_riesgo(rf_id)
        if riesgo:
            return riesgo.get("Trabajador", [])
        return []
    
    def obtener_preguntas_supervisor(self, rf_id: str) -> List[str]:
        """
        Obtiene lista de preguntas CCP/CCM para el supervisor.
        
        Args:
            rf_id: ID del riesgo
        
        Returns:
            Lista de preguntas para supervisor
        """
        riesgo = self.obtener_riesgo(rf_id)
        if riesgo:
            return riesgo.get("Supervisor", [])
        return []
    
    def obtener_todas_preguntas(self, rf_id: str) -> Dict[str, List[str]]:
        """
        Obtiene todas las preguntas (trabajador + supervisor) de un riesgo.
        
        Args:
            rf_id: ID del riesgo
        
        Returns:
            Dict con keys "Trabajador" y "Supervisor"
        """
        riesgo = self.obtener_riesgo(rf_id)
        if riesgo:
            return {
                "Trabajador": riesgo.get("Trabajador", []),
                "Supervisor": riesgo.get("Supervisor", [])
            }
        return {"Trabajador": [], "Supervisor": []}
    
    def contar_preguntas_por_rol(self, rf_id: str) -> Dict[str, int]:
        """
        Cuenta preguntas por rol (trabajador/supervisor).
        
        Args:
            rf_id: ID del riesgo
        
        Returns:
            Dict con conteo por rol
        """
        preguntas = self.obtener_todas_preguntas(rf_id)
        return {
            "Trabajador": len(preguntas["Trabajador"]),
            "Supervisor": len(preguntas["Supervisor"])
        }
    
    # ============ BÚSQUEDA Y FILTRADO ============
    
    def buscar_por_palabra_clave(self, palabra: str) -> List[str]:
        """
        Busca riesgos que contengan una palabra clave.
        
        Args:
            palabra: Palabra a buscar (case-insensitive)
        
        Returns:
            Lista de RF IDs que coinciden
        """
        palabra_lower = palabra.lower()
        
        # Buscar en índice
        if palabra_lower in self.indice_palabras:
            return self.indice_palabras[palabra_lower]
        
        # Si no está en índice, buscar parcialmente
        resultados = []
        for rf_id in self.riesgos.keys():
            if palabra_lower in rf_id.lower():
                resultados.append(rf_id)
        
        return resultados
    
    def buscar_en_preguntas(self, texto_busqueda: str, rf_id: Optional[str] = None) -> List[Tuple[str, str, str]]:
        """
        Busca texto dentro de las preguntas.
        
        Args:
            texto_busqueda: Texto a buscar en preguntas
            rf_id: (Opcional) Limitar búsqueda a un riesgo específico
        
        Returns:
            Lista de tuples (rf_id, rol, pregunta_encontrada)
        """
        resultados = []
        texto_lower = texto_busqueda.lower()
        
        # Definir riesgos a buscar
        riesgos_a_buscar = {rf_id: self.obtener_riesgo(rf_id)} if rf_id else self.riesgos.items()
        
        for rid, datos in riesgos_a_buscar.items():
            if not datos:
                continue
            
            # Buscar en preguntas del trabajador
            for pregunta in datos.get("Trabajador", []):
                if texto_lower in pregunta.lower():
                    resultados.append((rid, "Trabajador", pregunta))
            
            # Buscar en preguntas del supervisor
            for pregunta in datos.get("Supervisor", []):
                if texto_lower in pregunta.lower():
                    resultados.append((rid, "Supervisor", pregunta))
        
        return resultados
    
    def filtrar_por_rol(self, rol: str) -> Dict[str, int]:
        """
        Obtiene estadísticas de preguntas por rol.
        
        Args:
            rol: "Trabajador" o "Supervisor"
        
        Returns:
            Dict con cantidad de preguntas por riesgo para ese rol
        """
        if rol not in ["Trabajador", "Supervisor"]:
            logger.warning(f"Rol inválido: {rol}")
            return {}
        
        estadisticas = {}
        for rf_id, datos in self.riesgos.items():
            preguntas = datos.get(rol, [])
            if preguntas:
                estadisticas[rf_id] = len(preguntas)
        
        return estadisticas
    
    def obtener_riesgos_por_numero(self, inicio: int, fin: int) -> Dict[str, Dict]:
        """
        Obtiene riesgos en un rango numérico (ej: RF01-RF10).
        
        Args:
            inicio: Número inicial (1 para RF01)
            fin: Número final (10 para RF10)
        
        Returns:
            Dict con riesgos en ese rango
        """
        resultados = {}
        for rf_id, datos in self.riesgos.items():
            # Extraer número del RF ID (ej: "01" de "RF 01 ENERGÍA")
            try:
                numero = int(rf_id.split()[1])
                if inicio <= numero <= fin:
                    resultados[rf_id] = datos
            except (IndexError, ValueError):
                pass
        
        return resultados
    
    # ============ ESTADÍSTICAS ============
    
    def obtener_estadisticas(self) -> Dict:
        """
        Genera estadísticas completas del gestor de riesgos.
        
        Returns:
            Dict con estadísticas generales
        """
        total_preguntas_trabajador = 0
        total_preguntas_supervisor = 0
        
        for rf_id in self.riesgos.keys():
            total_preguntas_trabajador += len(self.obtener_preguntas_trabajador(rf_id))
            total_preguntas_supervisor += len(self.obtener_preguntas_supervisor(rf_id))
        
        return {
            "total_riesgos": len(self.riesgos),
            "total_preguntas_trabajador": total_preguntas_trabajador,
            "total_preguntas_supervisor": total_preguntas_supervisor,
            "total_preguntas": total_preguntas_trabajador + total_preguntas_supervisor,
            "promedio_preguntas_por_riesgo": round(
                (total_preguntas_trabajador + total_preguntas_supervisor) / len(self.riesgos), 1
            ) if self.riesgos else 0,
            "riesgos_cargados": self.listar_todos_riesgos()
        }
    
    def exportar_riesgos_json(self, ruta_salida: str) -> bool:
        """
        Exporta todos los riesgos a un archivo JSON.
        
        Args:
            ruta_salida: Ruta donde guardar el archivo
        
        Returns:
            True si se exportó exitosamente
        """
        try:
            with open(ruta_salida, 'w', encoding='utf-8') as f:
                json.dump(self.riesgos, f, ensure_ascii=False, indent=2)
            logger.info(f"Riesgos exportados a {ruta_salida}")
            return True
        except Exception as e:
            logger.error(f"Error exportando riesgos: {e}")
            return False
    
    def generar_reporte_resumido(self) -> str:
        """
        Genera reporte de texto resumido de todos los riesgos.
        
        Returns:
            String con reporte formateado
        """
        lineas = [
            "=" * 60,
            "📊 REPORTE DE RIESGOS FATALES",
            "=" * 60,
            ""
        ]
        
        for rf_id in self.listar_todos_riesgos():
            conteo = self.contar_preguntas_por_rol(rf_id)
            lineas.append(f"{rf_id}")
            lineas.append(f"  Trabajador: {conteo['Trabajador']} preguntas")
            lineas.append(f"  Supervisor: {conteo['Supervisor']} preguntas")
            lineas.append("")
        
        stats = self.obtener_estadisticas()
        lineas.extend([
            "=" * 60,
            f"TOTAL: {stats['total_riesgos']} riesgos, {stats['total_preguntas']} preguntas",
            "=" * 60
        ])
        
        return "\n".join(lineas)


# Instancia singleton
_risk_manager = None

def obtener_risk_manager() -> RiskManager:
    """
    Obtiene instancia singleton del RiskManager.
    
    Returns:
        Instancia global de RiskManager
    """
    global _risk_manager
    if _risk_manager is None:
        _risk_manager = RiskManager()
    return _risk_manager


# Funciones de conveniencia
def buscar_riesgo(rf_id: str) -> Optional[Dict]:
    """Atajo para obtener un riesgo"""
    return obtener_risk_manager().obtener_riesgo(rf_id)

def listar_riesgos() -> List[str]:
    """Atajo para listar todos los riesgos"""
    return obtener_risk_manager().listar_todos_riesgos()

def buscar_por_palabra(palabra: str) -> List[str]:
    """Atajo para búsqueda por palabra clave"""
    return obtener_risk_manager().buscar_por_palabra_clave(palabra)
