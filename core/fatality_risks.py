"""
===========================================
⚠️ FATALITY RISKS ENGINE - v3.0 (SaaS Avanzado)
===========================================
Motor de evaluación de riesgos fatales unificado.
Integra Risk Manager (RF01-RF30), y proporciona evaluación
avanzada con separación de CCP y CCM.

Autor: CGT
Versión: 3.0
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional

from dataclasses import dataclass
from src.services.risk_manager import obtener_risk_manager
from src.infrastructure.database import obtener_conexion, obtener_dataframe

logger = logging.getLogger(__name__)


@dataclass
class ResultadoEvaluacion:
    """Resultado de evaluación avanzada de un riesgo fatal (CCP/CCM)"""
    rf_id: str
    nombre_riesgo: str
    ccp_totales: int
    ccp_correctos: int
    ccm_totales: int
    ccm_correctos: int
    porcentaje_ccp: float
    porcentaje_ccm: float
    porcentaje_promedio: float
    nivel_riesgo: str
    brechas_ccp: List[str]
    brechas_ccm: List[str]
    recomendaciones: List[str]
    timestamp: str


class FatalityRisksEngine:
    """
    Motor avanzado de evaluación de riesgos fatales.
    
    Proporciona:
    - Integración total con Risk Manager
    - Evaluación independiente de CCP y CCM
    - Reportes avanzados de brechas
    - Persistencia en BD
    """
    
    def __init__(self, db_path: str = None):
        """Inicializa el motor de riesgos fatales."""
        self.db_path = db_path
        self.risk_manager = obtener_risk_manager()
        self._crear_tabla_evaluaciones()
        logger.info("FatalityRisksEngine inicializado")
    
    def _crear_tabla_evaluaciones(self) -> None:
        """Crea tabla para almacenar evaluaciones de riesgos v2 (CCP/CCM)"""
        if not self.db_path:
            return
        
        query = """
        CREATE TABLE IF NOT EXISTS evaluaciones_riesgos_v2 (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            rf_id TEXT NOT NULL,
            fecha_evaluacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ccp_totales INTEGER,
            ccp_correctos INTEGER,
            ccm_totales INTEGER,
            ccm_correctos INTEGER,
            porcentaje_promedio REAL,
            nivel_riesgo TEXT,
            respuestas_json TEXT,
            brechas_json TEXT,
            usuario_evaluador TEXT
        )
        """
        try:
            conexion = obtener_conexion(self.db_path)
            conexion.execute(query)
            conexion.commit()
            conexion.close()
            logger.debug("Tabla 'evaluaciones_riesgos_v2' creada")
        except Exception as e:
            logger.error(f"Error creando tabla: {e}")
    
    # ============ EVALUACIÓN DE RIESGOS ============
    
    def evaluar_riesgo(self, rf_id: str, respuestas: Dict[str, bool], 
                      empresa_id: int = 0) -> Optional[ResultadoEvaluacion]:
        """
        Evalúa cumplimiento de un riesgo con lógica CCP y CCM.
        
        Args:
            rf_id: ID del riesgo (ej: "RF 01 ENERGÍA ELÉCTRICA")
            respuestas: Dict {pregunta_texto: True/False} o {índice: True/False}
            empresa_id: ID de empresa (para BD)
        
        Returns:
            ResultadoEvaluacion con análisis avanzado
        """
        # Obtener preguntas del riesgo usando Risk Manager
        todas_preguntas = self.risk_manager.obtener_todas_preguntas(rf_id)
        preguntas_lista = todas_preguntas["Trabajador"] + todas_preguntas["Supervisor"]
        
        if not preguntas_lista:
            logger.warning(f"RF {rf_id} no encontrado o sin preguntas")
            return None
            
        # Normalizar respuestas (si vienen como índice int, convertir a texto)
        respuestas_norm = {}
        for k, v in respuestas.items():
            if isinstance(k, int) and k < len(preguntas_lista):
                respuestas_norm[preguntas_lista[k]] = v
            else:
                respuestas_norm[k] = v

        # Evaluar CCP
        preguntas_ccp = [p for p in preguntas_lista if "CCP" in p]
        ccp_totales = len(preguntas_ccp)
        ccp_correctos = sum(1 for p in preguntas_ccp if respuestas_norm.get(p) is True)
        
        # Evaluar CCM
        preguntas_ccm = [p for p in preguntas_lista if "CCM" in p]
        ccm_totales = len(preguntas_ccm)
        ccm_correctos = sum(1 for p in preguntas_ccm if respuestas_norm.get(p) is True)

        # Si no hay clasificación explícita, se evalúa el total general
        if ccp_totales == 0 and ccm_totales == 0:
            ccp_totales = len(preguntas_lista)
            ccp_correctos = sum(1 for v in respuestas_norm.values() if v is True)
            ccm_totales = 0
            ccm_correctos = 0

        pct_ccp = (ccp_correctos / ccp_totales * 100) if ccp_totales > 0 else 0
        pct_ccm = (ccm_correctos / ccm_totales * 100) if ccm_totales > 0 else 0
        
        if ccp_totales > 0 and ccm_totales > 0:
            pct_promedio = (pct_ccp + pct_ccm) / 2
        else:
            pct_promedio = pct_ccp if ccp_totales > 0 else pct_ccm
        
        nivel = self._clasificar_riesgo(pct_promedio)
        
        brechas_ccp = [p for p in preguntas_ccp if respuestas_norm.get(p) is False]
        brechas_ccm = [p for p in preguntas_ccm if respuestas_norm.get(p) is False]
        
        # Si no había CCP/CCM explícitos
        if not brechas_ccp and not brechas_ccm and ccp_totales > 0 and not preguntas_ccp:
            brechas_ccp = [p for p in preguntas_lista if respuestas_norm.get(p) is False]

        recomendaciones = self._generar_recomendaciones(nivel, brechas_ccp + brechas_ccm)
        
        resultado = ResultadoEvaluacion(
            rf_id=rf_id,
            nombre_riesgo=self._extraer_nombre_riesgo(rf_id),
            ccp_totales=ccp_totales,
            ccp_correctos=ccp_correctos,
            ccm_totales=ccm_totales,
            ccm_correctos=ccm_correctos,
            porcentaje_ccp=round(pct_ccp, 1),
            porcentaje_ccm=round(pct_ccm, 1),
            porcentaje_promedio=round(pct_promedio, 1),
            nivel_riesgo=nivel,
            brechas_ccp=brechas_ccp[:5],
            brechas_ccm=brechas_ccm[:5],
            recomendaciones=recomendaciones,
            timestamp=datetime.now().isoformat()
        )
        
        if self.db_path and empresa_id > 0:
            self._guardar_evaluacion(empresa_id, resultado, respuestas_norm)
        
        return resultado
    
    def evaluar_todos_riesgos(self, respuestas_por_rf: Dict[str, Dict[str, bool]], 
                             empresa_id: int = 0) -> List[ResultadoEvaluacion]:
        """Evalúa múltiples riesgos simultáneamente."""
        resultados = []
        for rf_id, respuestas in respuestas_por_rf.items():
            resultado = self.evaluar_riesgo(rf_id, respuestas, empresa_id)
            if resultado:
                resultados.append(resultado)
        return resultados
    
    def _clasificar_riesgo(self, porcentaje: float) -> str:
        """Clasifica nivel de riesgo por cumplimiento"""
        if porcentaje >= 90:
            return "CUMPLE ✅"
        elif porcentaje >= 75:
            return "PARCIAL ⚠️"
        elif porcentaje >= 50:
            return "DEFICIENTE 🚨"
        else:
            return "CRÍTICO 🔴"
    
    def _extraer_nombre_riesgo(self, rf_id: str) -> str:
        """Extrae nombre del RF ID"""
        try:
            return rf_id.split(" ", 2)[2]
        except:
            return rf_id
    
    def _generar_recomendaciones(self, nivel: str, brechas: List[str]) -> List[str]:
        """Genera recomendaciones según nivel de riesgo"""
        recomendaciones = []
        
        if nivel == "CRÍTICO 🔴":
            recomendaciones.append("URGENTE: Intervención inmediata requerida")
            recomendaciones.append("Suspender trabajo hasta implementar controles")
        elif nivel == "DEFICIENTE 🚨":
            recomendaciones.append("Implementar correcciones en 1 semana")
            recomendaciones.append("Aumentar supervisión")
        elif nivel == "PARCIAL ⚠️":
            recomendaciones.append("Revisar brechas identificadas")
            recomendaciones.append("Auditoría de seguimiento en 2 semanas")
        else:
            recomendaciones.append("Mantener estándares actuales")
            
        return recomendaciones
    
    def _guardar_evaluacion(self, empresa_id: int, resultado: ResultadoEvaluacion,
                           respuestas: Dict[str, bool]) -> bool:
        """Guarda evaluación avanzada en base datos"""
        try:
            query = """
            INSERT INTO evaluaciones_riesgos_v2
            (empresa_id, rf_id, ccp_totales, ccp_correctos, ccm_totales, ccm_correctos,
             porcentaje_promedio, nivel_riesgo, respuestas_json, brechas_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            valores = (
                empresa_id,
                resultado.rf_id,
                resultado.ccp_totales,
                resultado.ccp_correctos,
                resultado.ccm_totales,
                resultado.ccm_correctos,
                resultado.porcentaje_promedio,
                resultado.nivel_riesgo,
                json.dumps(respuestas),
                json.dumps({"ccp": resultado.brechas_ccp, "ccm": resultado.brechas_ccm})
            )
            
            conexion = obtener_conexion(self.db_path)
            conexion.execute(query, valores)
            conexion.commit()
            conexion.close()
            return True
        except Exception as e:
            logger.error(f"Error guardando evaluación v2: {e}")
            return False
            
    # ============ CONSULTAS Y REPORTES ============

    def generar_reporte_riesgo(self, resultado: ResultadoEvaluacion) -> str:
        lines = ["=" * 60, f"REPORTE - {resultado.rf_id}",
                 f"Riesgo: {resultado.nombre_riesgo}",
                 f"Nivel: {resultado.nivel_riesgo}",
                 f"CCP: {resultado.porcentaje_ccp}% | CCM: {resultado.porcentaje_ccm}%",
                 f"Promedio: {resultado.porcentaje_promedio}%"]
        if resultado.recomendaciones:
            lines.append("RECOMENDACIONES")
            for r in resultado.recomendaciones:
                lines.append(f"  - {r}")
        lines.append("=" * 60)
        return "\n".join(lines)

    def generar_resumen_empresa(self, evaluaciones: List[ResultadoEvaluacion]) -> Dict:
        total = len(evaluaciones)
        if total == 0:
            return {'total_riesgos': 0, 'riesgos_en_cumple': 0, 'riesgos_criticos': 0, 'promedio_cumplimiento': 0}
        en_cumple = sum(1 for e in evaluaciones if "CUMPLE" in str(getattr(e, 'nivel_riesgo', '')))
        criticos = sum(1 for e in evaluaciones if "CRÍTICO" in str(getattr(e, 'nivel_riesgo', '')) or "CRITICO" in str(getattr(e, 'nivel_riesgo', '')))
        promedio = sum(getattr(e, 'porcentaje_promedio', 0) for e in evaluaciones) / total
        return {'total_riesgos': total, 'riesgos_en_cumple': en_cumple,
                'riesgos_criticos': criticos, 'promedio_cumplimiento': round(promedio, 1)}

    def obtener_historico_empresa(self, empresa_id: int, ultimas_n: int = 10) -> List[Dict]:
        """Obtiene histórico de evaluaciones de una empresa"""
        if not self.db_path:
            return []
        try:
            query = f"""
            SELECT * FROM evaluaciones_riesgos_v2 
            WHERE empresa_id = {empresa_id}
            ORDER BY fecha_evaluacion DESC
            LIMIT {ultimas_n}
            """
            df = obtener_dataframe(self.db_path, query)
            return df.to_dict('records') if not df.empty else []
        except Exception as e:
            logger.error(f"Error obteniendo histórico v2: {e}")
            return []

# ============ FUNCIONES DE CONVENIENCIA ============

_engine = None


def cargar_riesgos() -> Dict:
    """
    Carga todos los riesgos fatales desde los módulos RF01-RF30.
    Útil para tests y para acceso directo a la data de riesgos.
    
    Returns:
        Dict con todos los riesgos fatales disponibles
    """
    from core.fatality_risks_rf01_rf10 import FATALITY_RISKS_RF01_RF10
    from core.fatality_risks_rf11_rf20 import FATALITY_RISKS_RF11_RF20
    from core.fatality_risks_rf21_rf30 import FATALITY_RISKS_RF21_RF30
    
    riesgos = {}
    riesgos.update(FATALITY_RISKS_RF01_RF10)
    riesgos.update(FATALITY_RISKS_RF11_RF20)
    riesgos.update(FATALITY_RISKS_RF21_RF30)
    return riesgos


def obtener_fatality_engine(db_path: str = None) -> FatalityRisksEngine:
    """Obtiene instancia singleton del motor de riesgos fatales unificado"""
    global _engine
    if _engine is None:
        _engine = FatalityRisksEngine(db_path)
    return _engine


# Proxy para UI Legacy (Mantiene compatibilidad con módulos como gestion_art.py)
FATALITY_RISKS = obtener_risk_manager().riesgos
