"""
===========================================
RF Engine: RF11-RF20
===========================================
Engine de evaluacion para riesgos fatales RF11 a RF20.
"""
import logging
from typing import Dict, List
from datetime import datetime

from core.fatality_risks_rf11_rf20 import FATALITY_RISKS_RF11_RF20
from intelligence.agents.fatality_risks_rf01_rf10_engine import EvaluacionRF

logger = logging.getLogger(__name__)


class RiskEvaluationEngineRF11_RF20:
    """Motor de evaluacion de riesgos fatales RF11-RF20"""
    
    def __init__(self):
        self.riesgos = FATALITY_RISKS_RF11_RF20
        logger.info(f"RF11-RF20 Engine inicializado con {len(self.riesgos)} riesgos")
    
    def obtener_todos_riesgos(self) -> List[str]:
        return list(self.riesgos.keys())
    
    def obtener_preguntas_rf(self, rf_id: str, tipo: str = "trabajador") -> List[str]:
        rf_data = self.riesgos.get(rf_id, {})
        if tipo.lower() == "trabajador":
            return rf_data.get("Trabajador", [])
        else:
            return rf_data.get("Supervisor", [])
    
    def evaluar_rf(self, rf_id: str, respuestas: Dict[int, bool]) -> EvaluacionRF:
        trabajador = self.riesgos.get(rf_id, {}).get("Trabajador", [])
        supervisor = self.riesgos.get(rf_id, {}).get("Supervisor", [])
        todas_preguntas = trabajador + supervisor
        
        if not todas_preguntas:
            return EvaluacionRF(
                rf_id=rf_id, nombre_riesgo=rf_id,
                ccp_totales=0, ccp_correctos=0, ccm_totales=0, ccm_correctos=0,
                porcentaje_ccp=0, porcentaje_ccm=0, porcentaje_promedio=0,
                nivel_riesgo="SIN DATOS", brechas_ccp=[], brechas_ccm=[],
                recomendaciones=["No hay datos"], timestamp=datetime.now().isoformat()
            )
        
        respuestas_norm = {}
        for k, v in respuestas.items():
            if isinstance(k, int) and k < len(todas_preguntas):
                respuestas_norm[todas_preguntas[k]] = v
            else:
                respuestas_norm[k] = v
        
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
        pct_promedio = (pct_ccp + pct_ccm) / 2 if (ccp_totales > 0 and ccm_totales > 0) else (pct_ccp if ccp_totales > 0 else pct_ccm)
        
        nivel = self._clasificar(pct_promedio)
        brechas_ccp = [p for p in preguntas_ccp if respuestas_norm.get(p) is False]
        brechas_ccm = [p for p in preguntas_ccm if respuestas_norm.get(p) is False]
        recos = self._generar_recomendaciones(nivel, brechas_ccp + brechas_ccm)
        
        return EvaluacionRF(
            rf_id=rf_id, nombre_riesgo=self._extraer_nombre(rf_id),
            ccp_totales=ccp_totales, ccp_correctos=ccp_correctos,
            ccm_totales=ccm_totales, ccm_correctos=ccm_correctos,
            porcentaje_ccp=round(pct_ccp, 1), porcentaje_ccm=round(pct_ccm, 1),
            porcentaje_promedio=round(pct_promedio, 1), nivel_riesgo=nivel,
            brechas_ccp=brechas_ccp[:5], brechas_ccm=brechas_ccm[:5],
            recomendaciones=recos, timestamp=datetime.now().isoformat()
        )
    
    def generar_reporte_rf(self, evaluacion: EvaluacionRF) -> str:
        lines = []
        lines.append("=" * 60)
        lines.append("EVALUACION DE RIESGO FATAL RF11-RF20")
        lines.append("=" * 60)
        lines.append(f"RF: {evaluacion.rf_id}")
        lines.append(f"Riesgo: {evaluacion.nombre_riesgo}")
        lines.append("-" * 60)
        lines.append(f"RESULTADO: {evaluacion.nivel_riesgo}")
        lines.append(f"CCP: {evaluacion.ccp_correctos}/{evaluacion.ccp_totales}")
        lines.append(f"CCM: {evaluacion.ccm_correctos}/{evaluacion.ccm_totales}")
        lines.append(f"Promedio: {evaluacion.porcentaje_promedio}%")
        lines.append("-" * 60)
        lines.append("BRECHAS Y RECOMENDACIONES:")
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
        try: return rf_id.split(" ", 2)[2]
        except: return rf_id
    
    def _generar_recomendaciones(self, nivel: str, brechas: List[str]) -> List[str]:
        recos = []
        if "CRITICO" in nivel:
            recos.append("URGENTE: Intervencion inmediata requerida")
        elif "DEFICIENTE" in nivel:
            recos.append("Implementar correcciones en 1 semana")
        elif "PARCIAL" in nivel:
            recos.append("Revisar brechas identificadas")
        else:
            recos.append("Mantener estandares actuales")
        return recos


_engine_rf11_rf20 = None


def obtener_engine_rf11_rf20() -> RiskEvaluationEngineRF11_RF20:
    global _engine_rf11_rf20
    if _engine_rf11_rf20 is None:
        _engine_rf11_rf20 = RiskEvaluationEngineRF11_RF20()
    return _engine_rf11_rf20
