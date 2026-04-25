"""
===========================================
RF Engine: RF01-RF10
===========================================
Engine de evaluacion para riesgos fatales RF01 a RF10.
Wrappeo sobre core/fatality_risks_rf01_rf10.py con API completa.
"""
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime

from core.fatality_risks_rf01_rf10 import FATALITY_RISKS_RF01_RF10

logger = logging.getLogger(__name__)


@dataclass
class EvaluacionRF:
    """Resultado de evaluacion de un Riesgo Fatal"""
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


class RiskEvaluationEngineRF01_RF10:
    """Motor de evaluacion de riesgos fatales RF01-RF10"""
    
    def __init__(self):
        self.riesgos = FATALITY_RISKS_RF01_RF10
        logger.info(f"RF01-RF10 Engine inicializado con {len(self.riesgos)} riesgos")
    
    def obtener_todos_riesgos(self) -> List[str]:
        """Retorna lista de nombres de riesgos"""
        return list(self.riesgos.keys())
    
    def obtener_preguntas_rf(self, rf_id: str, tipo: str = "trabajador") -> List[str]:
        """
        Obtiene preguntas para un RF especifico.
        
        Args:
            rf_id: ID del riesgo (ej: "RF 01 ENERGIA ELECTRICA")
            tipo: "trabajador" o "supervisor"
        
        Returns:
            Lista de preguntas
        """
        rf_data = self.riesgos.get(rf_id, {})
        if tipo.lower() == "trabajador":
            return rf_data.get("Trabajador", [])
        else:
            return rf_data.get("Supervisor", [])
    
    def evaluar_rf(self, rf_id: str, respuestas: Dict[int, bool]) -> EvaluacionRF:
        """
        Evalua un riesgo fatal con respuestas dadas.
        
        Args:
            rf_id: ID del riesgo
            respuestas: Dict {indice_pregunta: True/False}
        
        Returns:
            EvaluacionRF con resultado completo
        """
        # Obtener todas las preguntas
        trabajador = self.riesgos.get(rf_id, {}).get("Trabajador", [])
        supervisor = self.riesgos.get(rf_id, {}).get("Supervisor", [])
        todas_preguntas = trabajador + supervisor
        
        if not todas_preguntas:
            return EvaluacionRF(
                rf_id=rf_id,
                nombre_riesgo=rf_id,
                ccp_totales=0, ccp_correctos=0,
                ccm_totales=0, ccm_correctos=0,
                porcentaje_ccp=0, porcentaje_ccm=0, porcentaje_promedio=0,
                nivel_riesgo="SIN DATOS",
                brechas_ccp=[], brechas_ccm=[],
                recomendaciones=["No hay datos para este riesgo"],
                timestamp=datetime.now().isoformat()
            )
        
        # Normalizar respuestas
        respuestas_norm = {}
        for k, v in respuestas.items():
            if isinstance(k, int) and k < len(todas_preguntas):
                respuestas_norm[todas_preguntas[k]] = v
            else:
                respuestas_norm[k] = v
        
        # Separar CCP y CCM
        preguntas_ccp = [p for p in todas_preguntas if p.startswith("CCP")]
        preguntas_ccm = [p for p in todas_preguntas if p.startswith("CCM")]
        
        ccp_totales = len(preguntas_ccp)
        ccp_correctos = sum(1 for p in preguntas_ccp if respuestas_norm.get(p) is True)
        ccm_totales = len(preguntas_ccm)
        ccm_correctos = sum(1 for p in preguntas_ccm if respuestas_norm.get(p) is True)
        
        if ccp_totales == 0 and ccm_totales == 0:
            ccp_totales = len(todas_preguntas)
            ccp_correctos = sum(1 for v in respuestas_norm.values() if v is True)
        
        pct_ccp = (ccp_correctos / ccp_totales * 100) if ccp_totales > 0 else 0
        pct_ccm = (ccm_correctos / ccm_totales * 100) if ccm_totales > 0 else 0
        
        if ccp_totales > 0 and ccm_totales > 0:
            pct_promedio = (pct_ccp + pct_ccm) / 2
        else:
            pct_promedio = pct_ccp if ccp_totales > 0 else pct_ccm
        
        nivel = self._clasificar(pct_promedio)
        
        brechas_ccp = [p for p in preguntas_ccp if respuestas_norm.get(p) is False]
        brechas_ccm = [p for p in preguntas_ccm if respuestas_norm.get(p) is False]
        
        recos = self._generar_recomendaciones(nivel, brechas_ccp + brechas_ccm)
        
        return EvaluacionRF(
            rf_id=rf_id,
            nombre_riesgo=self._extraer_nombre(rf_id),
            ccp_totales=ccp_totales, ccp_correctos=ccp_correctos,
            ccm_totales=ccm_totales, ccm_correctos=ccm_correctos,
            porcentaje_ccp=round(pct_ccp, 1),
            porcentaje_ccm=round(pct_ccm, 1),
            porcentaje_promedio=round(pct_promedio, 1),
            nivel_riesgo=nivel,
            brechas_ccp=brechas_ccp[:5], brechas_ccm=brechas_ccm[:5],
            recomendaciones=recos,
            timestamp=datetime.now().isoformat()
        )
    
    def generar_reporte_rf(self, evaluacion: EvaluacionRF) -> str:
        """Genera reporte textual de una evaluacion"""
        lines = []
        lines.append("=" * 60)
        lines.append(f"EVALUACION DE RIESGO FATAL")
        lines.append("=" * 60)
        lines.append(f"RF: {evaluacion.rf_id}")
        lines.append(f"Riesgo: {evaluacion.nombre_riesgo}")
        lines.append(f"Fecha: {evaluacion.timestamp}")
        lines.append("-" * 60)
        lines.append(f"RESULTADO: {evaluacion.nivel_riesgo}")
        lines.append(f"CCP: {evaluacion.ccp_correctos}/{evaluacion.ccp_totales} ({evaluacion.porcentaje_ccp}%)")
        lines.append(f"CCM: {evaluacion.ccm_correctos}/{evaluacion.ccm_totales} ({evaluacion.porcentaje_ccm}%)")
        lines.append(f"Promedio: {evaluacion.porcentaje_promedio}%")
        lines.append("-" * 60)
        lines.append("BRECHAS:")
        for b in evaluacion.brechas_ccp + evaluacion.brechas_ccm:
            lines.append(f"  - {b[:80]}...")
        lines.append("-" * 60)
        lines.append("RECOMENDACIONES:")
        for r in evaluacion.recomendaciones:
            lines.append(f"  * {r}")
        lines.append("=" * 60)
        return "\n".join(lines)
    
    def _clasificar(self, pct: float) -> str:
        if pct >= 90: return "CUMPLE \u2705"
        elif pct >= 75: return "PARCIAL \u26a0\ufe0f"
        elif pct >= 50: return "DEFICIENTE \ud83d\udea8"
        else: return "CRITICO \ud83d\udd34"
    
    def _extraer_nombre(self, rf_id: str) -> str:
        try:
            return rf_id.split(" ", 2)[2]
        except:
            return rf_id
    
    def _generar_recomendaciones(self, nivel: str, brechas: List[str]) -> List[str]:
        recos = []
        if "CRITICO" in nivel:
            recos.append("URGENTE: Intervencion inmediata requerida")
            recos.append("Suspender trabajo hasta implementar controles")
        elif "DEFICIENTE" in nivel:
            recos.append("Implementar correcciones en 1 semana")
            recos.append("Aumentar supervision")
        elif "PARCIAL" in nivel:
            recos.append("Revisar brechas identificadas")
            recos.append("Auditoria de seguimiento en 2 semanas")
        else:
            recos.append("Mantener estandares actuales")
        return recos


_engine_rf01_rf10 = None


def obtener_engine_rf01_rf10() -> RiskEvaluationEngineRF01_RF10:
    """Singleton del engine RF01-RF10"""
    global _engine_rf01_rf10
    if _engine_rf01_rf10 is None:
        _engine_rf01_rf10 = RiskEvaluationEngineRF01_RF10()
    return _engine_rf01_rf10
