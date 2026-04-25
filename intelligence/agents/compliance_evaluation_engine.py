"""
===========================================
📋 COMPLIANCE EVALUATOR ENGINE - v2.0
===========================================
Motor de evaluación de cumplimiento normativo.
Utiliza templates de compliance_data.py para
auditoría de DS 594 y otras normativas.

Integra evaluación automática de requisitos
normativos con persistencia en BD.

Autor: CGT
Versión: 2.0
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from core.compliance_data import COMPLIANCE_TEMPLATES
from src.infrastructure.database import obtener_conexion, obtener_dataframe

logger = logging.getLogger(__name__)


@dataclass
class ResultadoComplianceAuditoria:
    """Resultado de auditoría de cumplimiento"""
    normativa: str
    titulo_seccion: str
    items_totales: int
    items_conformes: int
    items_no_conformes: int
    porcentaje_cumplimiento: float
    nivel_riesgo: str
    no_conformidades: List[str]
    recomendaciones: List[str]
    timestamp: str


class ComplianceEvaluationEngine:
    """
    Motor de evaluación de cumplimiento normativo.
    
    Proporciona:
    - Evaluación de templates de compliance
    - Cálculo de porcentajes de cumplimiento
    - Identificación de no conformidades
    - Generación de reportes
    - Persistencia de auditorías
    
    Normas soportadas:
    - DS 594 (Condiciones Sanitarias y Ambientales)
    - DS 40 (SGSST - Sistema Gestión Seguridad)
    - ISO 14001 (Gestión Ambiental)
    """
    
    def __init__(self, db_path: str = None):
        """
        Inicializa el motor.
        
        Args:
            db_path: Ruta a base datos
        """
        self.db_path = db_path
        self.templates = COMPLIANCE_TEMPLATES
        self._crear_tablas()
        logger.info("ComplianceEvaluationEngine inicializado")
    
    def _crear_tablas(self) -> None:
        """Crea tablas para auditorías de cumplimiento"""
        if not self.db_path:
            return
        
        # Tabla de auditorías
        query1 = """
        CREATE TABLE IF NOT EXISTS auditorias_compliance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            normativa TEXT NOT NULL,
            seccion TEXT NOT NULL,
            fecha_auditoria TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            items_totales INTEGER,
            items_conformes INTEGER,
            items_no_conformes INTEGER,
            porcentaje_cumplimiento REAL,
            nivel_riesgo TEXT,
            respuestas_json TEXT,
            no_conformidades_json TEXT,
            usuario_auditor TEXT
        )
        """
        
        # Tabla de no conformidades
        query2 = """
        CREATE TABLE IF NOT EXISTS no_conformidades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            auditoria_id INTEGER NOT NULL,
            empresa_id INTEGER NOT NULL,
            requisito TEXT NOT NULL,
            norma TEXT NOT NULL,
            descripcion_no_conformidad TEXT,
            severidad TEXT,  -- 'crítica', 'mayor', 'menor'
            fecha_vencimiento_corrección DATE,
            estado TEXT,  -- 'abierta', 'en_progreso', 'cerrada'
            FOREIGN KEY(auditoria_id) REFERENCES auditorias_compliance(id)
        )
        """
        
        try:
            conexion = obtener_conexion(self.db_path)
            conexion.execute(query1)
            conexion.execute(query2)
            conexion.commit()
            conexion.close()
            logger.debug("Tablas compliance creadas")
        except Exception as e:
            logger.error(f"Error creando tablas: {e}")
    
    # ============ OBTENCIÓN DE PLANTILLAS ============
    
    def obtener_normativas_disponibles(self) -> List[str]:
        """Retorna normativas disponibles"""
        return list(self.templates.keys())
    
    def obtener_secciones(self, normativa: str) -> List[Dict]:
        """
        Obtiene secciones de una normativa.
        
        Args:
            normativa: Nombre de la normativa
        
        Returns:
            Lista de secciones con items
        """
        if normativa not in self.templates:
            logger.warning(f"Normativa {normativa} no encontrada")
            return []
        
        return self.templates[normativa]
    
    # ============ EVALUACIÓN ============
    
    def evaluar_seccion(self, normativa: str, titulo_seccion: str,
                       respuestas: Dict[int, bool],
                       empresa_id: int = 0) -> ResultadoComplianceAuditoria:
        """
        Evalúa cumplimiento de una sección.
        
        Args:
            normativa: Nombre de normativa (ej: "DS 594 - ...")
            titulo_seccion: Título de la sección
            respuestas: Dict {índice_item: True/False}
            empresa_id: ID de empresa
        
        Returns:
            ResultadoComplianceAuditoria
        """
        secciones = self.obtener_secciones(normativa)
        
        # Buscar la sección
        seccion_encontrada = None
        for sec in secciones:
            if titulo_seccion in sec.get('titulo', ''):
                seccion_encontrada = sec
                break
        
        if not seccion_encontrada:
            logger.warning(f"Sección {titulo_seccion} no encontrada")
            return None
        
        items = seccion_encontrada.get('items', [])
        total_items = len(items)
        conformes = sum(1 for idx, val in respuestas.items() if val and idx < total_items)
        no_conformes = total_items - conformes
        pct_cumplimiento = (conformes / total_items * 100) if total_items > 0 else 0
        
        # Identificar no conformidades
        no_conformidades = []
        for idx, es_conforme in respuestas.items():
            if not es_conforme and idx < total_items:
                item = items[idx]
                no_conf_desc = f"{item['requisito']} ({item['norma']})"
                no_conformidades.append(no_conf_desc)
        
        # Clasificar riesgo
        nivel = self._clasificar_riesgo(pct_cumplimiento)
        
        # Generar recomendaciones
        recomendaciones = self._generar_recomendaciones(pct_cumplimiento, normativa)
        
        resultado = ResultadoComplianceAuditoria(
            normativa=normativa,
            titulo_seccion=titulo_seccion,
            items_totales=total_items,
            items_conformes=conformes,
            items_no_conformes=no_conformes,
            porcentaje_cumplimiento=round(pct_cumplimiento, 1),
            nivel_riesgo=nivel,
            no_conformidades=no_conformidades[:10],
            recomendaciones=recomendaciones,
            timestamp=datetime.now().isoformat()
        )
        
        # Guardar en BD
        if self.db_path and empresa_id > 0:
            self._guardar_auditoria(empresa_id, resultado, respuestas)
        
        return resultado
    
    def evaluar_normativa_completa(self, normativa: str,
                                  respuestas_por_seccion: Dict[str, Dict[int, bool]],
                                  empresa_id: int = 0) -> Dict:
        """
        Evalúa todas las secciones de una normativa.
        
        Args:
            normativa: Nombre normativa
            respuestas_por_seccion: Dict {título_sección: respuestas}
            empresa_id: ID empresa
        
        Returns:
            Dict con resultados agregados
        """
        secciones = self.obtener_secciones(normativa)
        resultados_secciones = []
        
        for seccion in secciones:
            titulo = seccion.get('titulo', '')
            if titulo in respuestas_por_seccion:
                respuestas = respuestas_por_seccion[titulo]
                resultado = self.evaluar_seccion(normativa, titulo, respuestas, empresa_id)
                if resultado:
                    resultados_secciones.append(resultado)
        
        # Calcular promedio general
        if resultados_secciones:
            pct_promedio = sum(r.porcentaje_cumplimiento for r in resultados_secciones) / len(resultados_secciones)
            nivel_general = self._clasificar_riesgo(pct_promedio)
        else:
            pct_promedio = 0
            nivel_general = "NO EVALUADA"
        
        return {
            "normativa": normativa,
            "secciones_evaluadas": len(resultados_secciones),
            "cumplimiento_promedio": round(pct_promedio, 1),
            "nivel_general": nivel_general,
            "secciones": [
                {
                    "titulo": r.titulo_seccion,
                    "cumplimiento": r.porcentaje_cumplimiento,
                    "conformes": r.items_conformes,
                    "total": r.items_totales
                }
                for r in resultados_secciones
            ]
        }
    
    def _clasificar_riesgo(self, porcentaje: float) -> str:
        """Clasifica nivel de cumplimiento"""
        if porcentaje >= 90:
            return "CONFORME ✅"
        elif porcentaje >= 75:
            return "PARCIALMENTE CONFORME ⚠️"
        elif porcentaje >= 50:
            return "NO CONFORME 🚨"
        else:
            return "CRÍTICO 🔴"
    
    def _generar_recomendaciones(self, pct: float, normativa: str) -> List[str]:
        """Genera recomendaciones según porcentaje"""
        recomendaciones = []
        
        if pct < 50:
            recomendaciones.append("🔴 ACCIÓN URGENTE: Implementar plan correctivo inmediato")
            recomendaciones.append(f"Auditoría interna urgente de {normativa}")
        elif pct < 75:
            recomendaciones.append("🚨 Implementar correcciones en 2-4 semanas")
            recomendaciones.append("Capacitación de personal involucrado")
        elif pct < 90:
            recomendaciones.append("⚠️ Revisar no conformidades menores")
            recomendaciones.append("Auditoría de seguimiento en 30 días")
        else:
            recomendaciones.append("✅ Mantener estándares actuales")
            recomendaciones.append("Continuar con auditorías periódicas")
        
        return recomendaciones[:3]
    
    def _guardar_auditoria(self, empresa_id: int, resultado: ResultadoComplianceAuditoria,
                          respuestas: Dict[int, bool]) -> bool:
        """Guarda auditoría en BD"""
        try:
            query = """
            INSERT INTO auditorias_compliance
            (empresa_id, normativa, seccion, items_totales, items_conformes,
             items_no_conformes, porcentaje_cumplimiento, nivel_riesgo,
             respuestas_json, no_conformidades_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            valores = (
                empresa_id,
                resultado.normativa,
                resultado.titulo_seccion,
                resultado.items_totales,
                resultado.items_conformes,
                resultado.items_no_conformes,
                resultado.porcentaje_cumplimiento,
                resultado.nivel_riesgo,
                json.dumps(respuestas),
                json.dumps(resultado.no_conformidades)
            )
            
            conexion = obtener_conexion(self.db_path)
            conexion.execute(query, valores)
            conexion.commit()
            conexion.close()
            
            logger.info(f"Auditoría guardada: {resultado.normativa}")
            return True
        
        except Exception as e:
            logger.error(f"Error guardando: {e}")
            return False
    
    # ============ REPORTES ============
    
    def generar_reporte_auditoria(self, resultado: ResultadoComplianceAuditoria) -> str:
        """Genera reporte de auditoría"""
        lineas = [
            "=" * 90,
            "📋 REPORTE DE AUDITORÍA DE CUMPLIMIENTO NORMATIVO",
            "=" * 90,
            f"Normativa: {resultado.normativa}",
            f"Sección: {resultado.titulo_seccion}",
            f"Fecha: {resultado.timestamp}",
            "",
            "RESULTADO",
            "-" * 90,
            f"Items Totales:        {resultado.items_totales}",
            f"Items Conformes:      {resultado.items_conformes}",
            f"Items No Conformes:   {resultado.items_no_conformes}",
            f"Cumplimiento:         {resultado.porcentaje_cumplimiento}%",
            f"Nivel:                {resultado.nivel_riesgo}",
            "",
            "NO CONFORMIDADES IDENTIFICADAS",
            "-" * 90,
        ]
        
        for nc in resultado.no_conformidades:
            lineas.append(f"❌ {nc}")
        
        lineas.extend([
            "",
            "RECOMENDACIONES",
            "-" * 90,
        ])
        
        for rec in resultado.recomendaciones:
            lineas.append(f"→ {rec}")
        
        lineas.append("=" * 90)
        
        return "\n".join(lineas)
    
    def obtener_historico_auditorias(self, empresa_id: int, ultimas_n: int = 10) -> List[Dict]:
        """Obtiene histórico de auditorías"""
        if not self.db_path:
            return []
        
        try:
            query = f"""
            SELECT * FROM auditorias_compliance
            WHERE empresa_id = {empresa_id}
            ORDER BY fecha_auditoria DESC
            LIMIT {ultimas_n}
            """
            
            df = obtener_dataframe(self.db_path, query)
            return df.to_dict('records') if not df.empty else []
        
        except Exception as e:
            logger.error(f"Error obteniendo histórico: {e}")
            return []


# ============ SINGLETON ============

_engine_compliance = None

def obtener_compliance_engine(db_path: str = None) -> ComplianceEvaluationEngine:
    """Obtiene instancia singleton"""
    global _engine_compliance
    if _engine_compliance is None:
        _engine_compliance = ComplianceEvaluationEngine(db_path)
    return _engine_compliance
