"""
===========================================
RF Engine: RF21-RF30 (Mas Critico)
===========================================
Engine de evaluacion para riesgos fatales RF21 a RF30.
"""
import logging
from typing import Dict, List
from datetime import datetime

from core.fatality_risks_rf21_rf30 import FATALITY_RISKS_RF21_RF30
from intelligence.agents.fatality_risks_rf01_rf10_engine import EvaluacionRF

logger = logging.getLogger(__name__)


class RiskEvaluationEngineRF21_RF30:
    """Motor de evaluacion de riesgos fatales RF21-RF30 (Mas Criticos)"""
    
    def __init__(self):
        self.riesgos = FATALITY_RISKS_RF21_RF30
        logger.info(f"RF21-RF30 Engine inicializado con {len(self.riesgos)} riesgos")
    
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
        recos = self._generar_recomendaciones(nivel, brechas_ccp + brechas_ccm, rf_id)
        
        return EvaluacionRF(
            rf_id=rf_id, nombre_riesgo=self._extraer_nombre(rf_id),
            ccp_totales=ccp_totales, ccp_correctos=ccp_correctos,
            ccm_totales=ccm_totales, ccm_correctos=ccm_correctos,
            porcentaje_ccp=round(pct_ccp, 1), porcentaje_ccm=round(pct_ccm, 1),
            porcentaje_promedio=round(pct_promedio, 1), nivel_riesgo=nivel,
            brechas_ccp=brechas_ccp[:5], brechas_ccm=brechas_ccm[:5],
            recomendaciones=recos, timestamp=datetime.now().isoformat()
        )
    
    def generar_reporte_completo(self, evaluacion: EvaluacionRF) -> str:
        lines = []
        lines.append("=" * 60)
        lines.append("EVALUACI\xd3N COMPLETA - RF21-RF30 (CR\xcdTICOS)")
        lines.append("=" * 60)
        lines.append(f"RF: {evaluacion.rf_id}")
        lines.append(f"Riesgo: {evaluacion.nombre_riesgo}")
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
        elif pct >= 50: return "DEFICIENTE \U0001F6A8"
        else: return "CR\xcdTICO \U0001F534"
    
    def _extraer_nombre(self, rf_id: str) -> str:
        try: return rf_id.split(" ", 2)[2]
        except: return rf_id
    
    def _generar_recomendaciones(self, nivel: str, brechas: List[str], rf_id: str = "") -> List[str]:
        recos = []
        if "CRITICO" in nivel:
            recos.append("URGENTE: Intervencion inmediata requerida")
        elif "DEFICIENTE" in nivel:
            recos.append("Implementar correcciones en 1 semana")
        elif "PARCIAL" in nivel:
            recos.append("Revisar brechas identificadas")
        else:
            recos.append("Mantener estandares actuales")
        
        # Recomendaciones especificas por tipo de riesgo
        rf_upper = rf_id.upper()
        if "ARSENICO" in rf_upper or "ARSÉNICO" in rf_upper:
            recos.append("Vigilancia medica obligatoria y monitoreo de exposicion a arsenico")
            recos.append("Monitoreo ambiental de niveles de arsenico en area de trabajo")
        if "COLAPSO" in rf_upper or "MACIZO" in rf_upper:
            recos.append("Monitoreo geotecnico continuo del macizo rocoso")
        if "MERCURIO" in rf_upper:
            recos.append("Implementar programa de vigilancia medica por mercurio")
        if "RADIACION" in rf_upper:
            recos.append("Implementar dosimetria personal y vigilancia medica")
        
        return recos


    def registrar_medicion_vigilancia(self, empresa_id: int, rf_id: str,
                                      tipo_vigilancia: str, resultado: float,
                                      unidad: str, rango_seguro: str) -> bool:
        """
        Registra una medicion de vigilancia (ambiental, biologica, etc.)
        Sin BD configurada retorna False.
        """
        logger.info(f"Medicion registrada: {rf_id}/{tipo_vigilancia}={resultado} {unidad}")
        # Sin BD retorna False
        return False


_engine_rf21_rf30 = None


def obtener_engine_rf21_rf30() -> RiskEvaluationEngineRF21_RF30:
    global _engine_rf21_rf30
    if _engine_rf21_rf30 is None:
        _engine_rf21_rf30 = RiskEvaluationEngineRF21_RF30()
    return _engine_rf21_rf30
