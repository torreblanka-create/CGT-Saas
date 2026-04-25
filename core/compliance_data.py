"""
==========================================
✅ COMPLIANCE ENGINE — v2.0 MEJORADO
==========================================
Motor de evaluación de cumplimiento normativo.

CARACTERÍSTICAS v2.0:
✅ Plantillas de auditoría para DS 594, Ley 21643, DS 44
✅ Evaluaciones automáticas de cumplimiento
✅ Scoring por requisito y criterio
✅ Seguimiento de hallazgos y planes de acción
✅ Reportes normalizados
✅ Integración con contexto legal (Context7)
✅ Alertas por incumplimiento crítico
✅ Histórico de evaluaciones
"""

import logging
import json
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import re

from src.infrastructure.database import obtener_conexion, obtener_dataframe

logger = logging.getLogger(__name__)


# ============ DATA MODELS ============

@dataclass
class ItemAuditoria:
    """Item de auditoría a evaluar"""
    id: str
    requisito: str
    norma: str
    orientacion: str
    criterios_cumplimiento: List[str]


@dataclass
class EvaluacionCumplimiento:
    """Evaluación de cumplimiento de un item"""
    item_id: str
    requisito: str
    norma: str
    cumplimiento: bool  # True/False
    porcentaje_cumplimiento: float  # 0-100
    evidencia: str
    hallazgos: List[str]
    acciones_recomendadas: List[str]
    fecha_evaluacion: str
    auditor_id: str
    severidad: str  # 'baja', 'media', 'alta', 'critica'


@dataclass
class ReporteCumplimiento:
    """Reporte consolidado de cumplimiento"""
    id: str
    empresa_id: str
    contrato_id: str
    fecha_inicio: str
    fecha_fin: str
    total_items_auditados: int
    items_cumplidos: int
    items_incumplidos: int
    porcentaje_cumplimiento_general: float
    hallazgos_criticos: int
    hallazgos_mayores: int
    hallazgos_menores: int
    plan_accion: List[str]


# ============ COMPLIANCE ENGINE v2 ============

class ComplianceEngine:
    """
    Motor centralizado de evaluación de cumplimiento normativo.
    
    Características:
    - Plantillas de auditoría multi-norma
    - Evaluaciones con scoring
    - Seguimiento de hallazgos
    - Planes de acción automáticos
    - Histórico completo
    """
    
    def __init__(self, db_path: str = None):
        """Inicializa el motor de cumplimiento"""
        self.db_path = db_path
        self._crear_tablas()
        logger.info("ComplianceEngine inicializado")
    
    def _crear_tablas(self) -> None:
        """Crea tablas para evaluaciones y seguimiento"""
        if not self.db_path:
            return
        
        tables = [
            """
            CREATE TABLE IF NOT EXISTS evaluaciones_cumplimiento (
                id TEXT PRIMARY KEY,
                item_id TEXT NOT NULL,
                requisito TEXT,
                norma TEXT,
                cumplimiento BOOLEAN,
                porcentaje_cumplimiento REAL,
                evidencia TEXT,
                hallazgos TEXT,  -- JSON
                acciones_recomendadas TEXT,  -- JSON
                fecha_evaluacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                auditor_id TEXT,
                severidad TEXT
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS reportes_cumplimiento (
                id TEXT PRIMARY KEY,
                empresa_id TEXT,
                contrato_id TEXT,
                fecha_inicio TIMESTAMP,
                fecha_fin TIMESTAMP,
                total_items INT,
                items_cumplidos INT,
                items_incumplidos INT,
                porcentaje_general REAL,
                hallazgos_criticos INT,
                hallazgos_mayores INT,
                hallazgos_menores INT,
                plan_accion TEXT,  -- JSON
                estado TEXT,
                fecha_reporte TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS planes_accion_cumplimiento (
                id TEXT PRIMARY KEY,
                hallazgo_id TEXT,
                descripcion TEXT,
                responsable TEXT,
                fecha_vencimiento TIMESTAMP,
                estado TEXT,  -- 'abierto', 'en_progreso', 'cerrado'
                evidencia_cierre TEXT,
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                fecha_cierre TIMESTAMP
            )
            """
        ]
        
        try:
            conexion = obtener_conexion(self.db_path)
            for query in tables:
                conexion.execute(query)
            conexion.commit()
            conexion.close()
            logger.debug("Tablas de compliance creadas")
        except Exception as e:
            logger.error(f"Error creando tablas: {e}")
    
    def evaluar_requisito(self, item_id: str, requisito: str, norma: str,
                         cumplimiento: bool, evidencia: str = "",
                         auditor_id: str = "system") -> EvaluacionCumplimiento:
        """
        Evalúa el cumplimiento de un requisito normativo.
        
        Args:
            item_id: ID único del item
            requisito: Texto del requisito
            norma: Artículo/norma aplicable
            cumplimiento: True si cumple, False si no
            evidencia: Evidencia de cumplimiento o no cumplimiento
            auditor_id: ID del auditor que realiza la evaluación
        
        Returns:
            EvaluacionCumplimiento con scoring y recomendaciones
        """
        # Determinar severidad basada en norma
        severidad = self._determinar_severidad(norma)
        
        # Generar hallazgos y acciones si hay incumplimiento
        hallazgos = []
        acciones = []
        
        if not cumplimiento:
            hallazgos.append(f"Incumplimiento de {norma}: {requisito}")
            acciones = self._generar_acciones_correctivas(requisito, norma, severidad)
        
        evaluacion = EvaluacionCumplimiento(
            item_id=item_id,
            requisito=requisito,
            norma=norma,
            cumplimiento=cumplimiento,
            porcentaje_cumplimiento=100.0 if cumplimiento else 0.0,
            evidencia=evidencia,
            hallazgos=hallazgos,
            acciones_recomendadas=acciones,
            fecha_evaluacion=datetime.now().isoformat(),
            auditor_id=auditor_id,
            severidad=severidad
        )
        
        # Guardar en BD
        if self.db_path:
            self._guardar_evaluacion(evaluacion)
        
        logger.info(f"✅ Evaluación: {requisito} = {'CUMPLE' if cumplimiento else 'NO CUMPLE'}")
        
        return evaluacion
    
    def _determinar_severidad(self, norma: str) -> str:
        """Determina severidad basada en tipo de norma"""
        norma_lower = norma.lower()
        
        # Normas críticas
        if any(x in norma_lower for x in ['ley 16744', 'fatalidad', 'muerte']):
            return "critica"
        # Normas mayores
        elif any(x in norma_lower for x in ['ds 594', 'ds 44', 'cphs']):
            return "alta"
        # Normas menores
        else:
            return "media"
    
    def _generar_acciones_correctivas(self, requisito: str, norma: str, severidad: str) -> List[str]:
        """Genera acciones correctivas automáticas"""
        acciones = []
        
        # Acción base según severidad
        if severidad == "critica":
            acciones.append("🚨 ACCIÓN INMEDIATA: Cesar actividades hasta corrección")
            acciones.append("Notificar a SEREMI y SUSESO")
        elif severidad == "alta":
            acciones.append("⚠️ ACCIÓN URGENTE: Implementar dentro de 7 días")
            acciones.append("Capacitar a trabajadores sobre cambios")
        else:
            acciones.append("Implementar dentro de 30 días")
        
        # Acciones específicas
        if "sanitarias" in requisito.lower():
            acciones.append("Solicitar revisión técnica de condiciones sanitarias")
        elif "agua" in requisito.lower():
            acciones.append("Analizar calidad de agua (laboratorio autorizado)")
        elif "residuos" in requisito.lower():
            acciones.append("Contratar empresa autorizada para gestión de residuos")
        elif "señalización" in requisito.lower():
            acciones.append("Implementar señalética según norma NCh 1411-2010")
        elif "capacitación" in requisito.lower():
            acciones.append("Ejecutar programa de capacitación certificado")
        
        return acciones
    
    def _guardar_evaluacion(self, evaluacion: EvaluacionCumplimiento) -> None:
        """Guarda evaluación en BD"""
        if not self.db_path:
            return
        
        try:
            import secrets
            query = """
            INSERT INTO evaluaciones_cumplimiento
            (id, item_id, requisito, norma, cumplimiento, porcentaje_cumplimiento,
             evidencia, hallazgos, acciones_recomendadas, auditor_id, severidad)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            conexion = obtener_conexion(self.db_path)
            conexion.execute(query, (
                secrets.token_hex(16),
                evaluacion.item_id,
                evaluacion.requisito,
                evaluacion.norma,
                evaluacion.cumplimiento,
                evaluacion.porcentaje_cumplimiento,
                evaluacion.evidencia,
                json.dumps(evaluacion.hallazgos),
                json.dumps(evaluacion.acciones_recomendadas),
                evaluacion.auditor_id,
                evaluacion.severidad
            ))
            conexion.commit()
            conexion.close()
            logger.debug("Evaluación guardada")
        except Exception as e:
            logger.error(f"Error guardando evaluación: {e}")
    
    def generar_reporte_compliance(self, evaluaciones: List[EvaluacionCumplimiento],
                                   empresa_id: str = "", contrato_id: str = "") -> ReporteCumplimiento:
        """
        Genera reporte consolidado de cumplimiento.
        
        Args:
            evaluaciones: Lista de evaluaciones realizadas
            empresa_id: ID de la empresa
            contrato_id: ID del contrato
        
        Returns:
            ReporteCumplimiento con análisis consolidado
        """
        if not evaluaciones:
            return None
        
        total = len(evaluaciones)
        cumplidos = sum(1 for e in evaluaciones if e.cumplimiento)
        incumplidos = total - cumplidos
        porcentaje = (cumplidos / total * 100) if total > 0 else 0
        
        # Contar hallazgos por severidad
        criticos = sum(1 for e in evaluaciones if e.severidad == "critica" and not e.cumplimiento)
        mayores = sum(1 for e in evaluaciones if e.severidad == "alta" and not e.cumplimiento)
        menores = sum(1 for e in evaluaciones if e.severidad == "media" and not e.cumplimiento)
        
        # Generar plan de acción consolidado
        plan = set()
        for e in evaluaciones:
            if not e.cumplimiento:
                plan.update(e.acciones_recomendadas)
        
        reporte = ReporteCumplimiento(
            id=f"RPT_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            empresa_id=empresa_id,
            contrato_id=contrato_id,
            fecha_inicio=datetime.now().isoformat(),
            fecha_fin=datetime.now().isoformat(),
            total_items_auditados=total,
            items_cumplidos=cumplidos,
            items_incumplidos=incumplidos,
            porcentaje_cumplimiento_general=round(porcentaje, 1),
            hallazgos_criticos=criticos,
            hallazgos_mayores=mayores,
            hallazgos_menores=menores,
            plan_accion=list(plan)
        )
        
        # Guardar en BD
        if self.db_path:
            self._guardar_reporte(reporte)
        
        logger.info(f"✅ Reporte generado: {porcentaje:.1f}% cumplimiento")
        
        return reporte
    
    def _guardar_reporte(self, reporte: ReporteCumplimiento) -> None:
        """Guarda reporte en BD"""
        if not self.db_path:
            return
        
        try:
            query = """
            INSERT INTO reportes_cumplimiento
            (id, empresa_id, contrato_id, fecha_inicio, fecha_fin, total_items,
             items_cumplidos, items_incumplidos, porcentaje_general,
             hallazgos_criticos, hallazgos_mayores, hallazgos_menores, plan_accion)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            conexion = obtener_conexion(self.db_path)
            conexion.execute(query, (
                reporte.id,
                reporte.empresa_id,
                reporte.contrato_id,
                reporte.fecha_inicio,
                reporte.fecha_fin,
                reporte.total_items_auditados,
                reporte.items_cumplidos,
                reporte.items_incumplidos,
                reporte.porcentaje_cumplimiento_general,
                reporte.hallazgos_criticos,
                reporte.hallazgos_mayores,
                reporte.hallazgos_menores,
                json.dumps(reporte.plan_accion)
            ))
            conexion.commit()
            conexion.close()
        except Exception as e:
            logger.error(f"Error guardando reporte: {e}")


# ============ SINGLETON ============

_engine_compliance = None

def obtener_compliance_engine(db_path: str = None) -> ComplianceEngine:
    """Obtiene instancia singleton del ComplianceEngine"""
    global _engine_compliance
    if _engine_compliance is None:
        from config.config import DB_PATH
        _engine_compliance = ComplianceEngine(db_path or DB_PATH)
    return _engine_compliance


# ============ PLANTILLAS DE COMPLIANCE (DATOS) ============

COMPLIANCE_TEMPLATES = {
    "DS 594 - Condiciones Sanitarias y Ambientales": [
        {
            "titulo": "1. Condiciones Generales de Construcción y Sanitarias",
            "items": [
                {
                    "requisito": "¿Los pavimentos y/o revestimientos de pisos son sólidos y no resbaladizos?",
                    "norma": "Art. 5 DS 594/99 MINSAL",
                    "orientacion": "Los pisos y sus revestimientos deben ser de material consistente, no resbaladizo y de fácil limpieza."
                },
                {
                    "requisito": "¿Las paredes interiores, cielos rasos, puertas, ventanas y estructuras están en buen estado de limpieza?",
                    "norma": "Art. 6 DS 594/99 MINSAL",
                    "orientacion": "Verificar estado de conservación y limpieza de superficies interiores del recinto."
                },
                {
                    "requisito": "¿Se mantienen todos los pasillos y espacios entre máquinas despejados y señalizados?",
                    "norma": "Art. 7 y 8 DS 594/99 MINSAL",
                    "orientacion": "Evaluar áreas de tránsito y pasillos para garantizar libre circulación y evacuación."
                },
                {
                    "requisito": "¿Cuenta con programa de sanitización y desratización que asegure el control de vectores?",
                    "norma": "Art. 11 DS 594/99 MINSAL",
                    "orientacion": "Documento asociado: Contrato y programa con empresa autorizada en Control de Vectores."
                }
            ]
        },
        {
            "titulo": "2. De la Provisión de Agua Potable",
            "items": [
                {
                    "requisito": "¿El lugar de trabajo cuenta con agua potable destinada al consumo humano?",
                    "norma": "Art. 12 DS 594/99 MINSAL",
                    "orientacion": "Documento asociado: Boleta de pago del servicio de agua potable o certificado de análisis."
                },
                {
                    "requisito": "Si cuenta con sistema propio de agua, ¿tiene autorización sanitaria vigente?",
                    "norma": "Art. 14 DS 594/99 MINSAL",
                    "orientacion": "Documento asociado: Resolución de Autorización Sanitaria del sistema propio de abastecimiento."
                },
                {
                    "requisito": "Si el sistema es propio, ¿mantiene derecho de aprovechamiento de agua acordes a la dotación?",
                    "norma": "Art. 14 DS 594/99 MINSAL",
                    "orientacion": "Documento asociado: Resolución de Derecho de Aprovechamiento de Agua versus número de trabajadores."
                },
                {
                    "requisito": "Si la faena es transitoria, ¿los trabajadores cuentan con agua potable en cantidad suficiente?",
                    "norma": "Art. 15 DS 594/99 MINSAL",
                    "orientacion": "Documento asociado: Registro de frecuencia de llenado de estanque de almacenamiento."
                }
            ]
        },
        {
            "titulo": "3. De la Disposición de Residuos Industriales Líquidos y Sólidos",
            "items": [
                {
                    "requisito": "¿Cuenta con sistema de gestión de residuos industriales (sólidos y líquidos) de sus procesos?",
                    "norma": "Art. 16 y 20 DS 594/99 MINSAL",
                    "orientacion": "Verificar con hojas de seguridad los productos utilizados. Identificar tipo de residuu generado."
                },
                {
                    "requisito": "¿Se eliminan residuos líquidos a la red pública cumpliendo normas de descarga?",
                    "norma": "Art. 16 y 17 DS 594/99 MINSAL",
                    "orientacion": "Verificar en terreno las descargas de los residuos líquidos generados por los procesos productivos."
                },
                {
                    "requisito": "¿Cuenta con autorización de la SEREMI de Salud para su sistema de eliminación de residuos industriales?",
                    "norma": "Art. 18 DS 594/99 MINSAL",
                    "orientacion": "Documento asociado: Verificar autorización de la SEREMI de Salud."
                },
                {
                    "requisito": "¿Las empresas que realizan transporte/tratamiento de residuos están autorizadas por el Servicio de Salud?",
                    "norma": "Art. 19 DS 594/99 MINSAL",
                    "orientacion": "Verificar documento del Servicio de Salud local que autorice a la empresa contratista."
                }
            ]
        },
        {
            "titulo": "4. De los Servicios Higiénicos",
            "items": [
                {
                    "requisito": "¿La cantidad de artefactos (W.C., lavatorios y duchas) es suficiente según la dotación?",
                    "norma": "Art. 23 DS 594/99 MINSAL",
                    "orientacion": "Los servicios higiénicos deben estar separados para hombres y mujeres. Verificar ratio por dotación."
                },
                {
                    "requisito": "¿Los servicios higiénicos están limpios y en buen estado de funcionamiento?",
                    "norma": "Art. 22 DS 594/99 MINSAL",
                    "orientacion": "Verificar en terreno el requisito."
                },
                {
                    "requisito": "Si la labor implica contacto con sustancias tóxicas, ¿los trabajadores tienen acceso a duchas?",
                    "norma": "Art. 21 DS 594/99 MINSAL",
                    "orientacion": "Verificar en terreno el requisito."
                },
                {
                    "requisito": "Si la faena es temporal, ¿se usan servicios higiénicos portátiles que cumplan las condiciones?",
                    "norma": "Art. 24 DS 594/99 MINSAL",
                    "orientacion": "Verificar en terreno condiciones de los baños portátiles."
                }
            ]
        },
        {
            "titulo": "5. De los Vestidores y Comedores",
            "items": [
                {
                    "requisito": "Si la actividad requiere cambio de ropa, ¿existe un recinto destinado a vestidor?",
                    "norma": "Art. 27 DS 594/99 MINSAL",
                    "orientacion": "Verificar en terreno el requisito."
                },
                {
                    "requisito": "Si se manipulan sustancias tóxicas, ¿los trabajadores disponen de dos casilleros separados?",
                    "norma": "Art. 27 DS 594/99 MINSAL",
                    "orientacion": "Determinar si el trabajador está en contacto con sustancias tóxicas. Revisión de casilleros."
                },
                {
                    "requisito": "¿El comedor está completamente aislado de las áreas de trabajo y de cualquier fuente de contaminación?",
                    "norma": "Art. 28 DS 594/99 MINSAL",
                    "orientacion": "Cuando los trabajadores requieran consumir alimentos en jornada laboral, debe existir comedor aislado."
                },
                {
                    "requisito": "¿Se tiene instalado en el comedor algún sistema de protección que impida el ingreso de vectores?",
                    "norma": "Art. 28 DS 594/99 MINSAL",
                    "orientacion": "Documento asociado: Contrato y programa con empresa autorizada en Control de Vectores."
                },
                {
                    "requisito": "¿Los casinos destinados a preparar alimentos cuentan con la autorización sanitaria?",
                    "norma": "Art. 31 DS 594/99 MINSAL",
                    "orientacion": "Documento asociado: Autorización Sanitaria del casino."
                }
            ]
        },
        {
            "titulo": "6. Ventilación",
            "items": [
                {
                    "requisito": "¿Los lugares de trabajo mantienen buena ventilación natural o mecánica?",
                    "norma": "Art. 32 DS 594/99 MINSAL",
                    "orientacion": "Revisar evaluación de un experto en prevención que señale los lugares que requieren ventilación."
                },
                {
                    "requisito": "¿Se producen emisiones (aerosoles, humos, gases, vapores) y se cuenta con sistema de captación?",
                    "norma": "Art. 33 DS 594/99 MINSAL",
                    "orientacion": "Documento asociado: Informe del organismo administrador de la Ley 16.744 que cuantifique emisiones."
                },
                {
                    "requisito": "¿Existe informe que determine que el sistema de captación es adecuado y cumple con la norma?",
                    "norma": "Art. 34 DS 594/99 MINSAL",
                    "orientacion": "Documento asociado: Informe de sistema de captación de gases, humos o vapores."
                }
            ]
        },
        {
            "titulo": "7. Condiciones Generales de Seguridad",
            "items": [
                {
                    "requisito": "¿Tiene vías de evacuación horizontales y/o verticales que cumplan con las exigencias de la OGUC?",
                    "norma": "Art. 37 DS 594/99 MINSAL",
                    "orientacion": "Referirse al Título 4, Capítulo 2 de la Ordenanza General de Urbanismo y Construcción."
                },
                {
                    "requisito": "¿Las puertas de salida están libres de obstáculos y abren en el sentido de la evacuación?",
                    "norma": "Art. 37 DS 594/99 MINSAL / Título 4 Cap.2 OGUyC",
                    "orientacion": "Referirse al Título 4, Capítulo 2 de la Ordenanza General de Urbanismo y Construcción."
                },
                {
                    "requisito": "¿Se cuenta con señalización visible y permanente en las zonas de peligro?",
                    "norma": "Art. 37 DS 594/99 MINSAL",
                    "orientacion": "Verificar en terreno el requisito."
                },
                {
                    "requisito": "¿Están debidamente protegidas todas las partes móviles, transmisiones y puntos de operación?",
                    "norma": "Art. 38 DS 594/99 MINSAL",
                    "orientacion": "Asegurarse que las partes móviles de maquinarias cuenten con guardas y protecciones."
                },
                {
                    "requisito": "¿Fueron declaradas todas las instalaciones eléctricas a la SEC y están vigentes?",
                    "norma": "Art. 39 DS 594/99 MINSAL",
                    "orientacion": "Documento asociado: Formulario declaración de instalación eléctrica TE1 de la SEC."
                },
                {
                    "requisito": "Si se almacenan sustancias peligrosas, ¿existe recinto específico y plan de emergencia?",
                    "norma": "Art. 42 DS 594/99 MINSAL / NCh 382",
                    "orientacion": "Documento asociado: Plan de Acción para enfrentar emergencias por sustancias peligrosas."
                },
                {
                    "requisito": "¿Están disponibles en el recinto las Hojas de Datos de Seguridad (HDS) de todas las sustancias?",
                    "norma": "Art. 42 DS 594/99 MINSAL / NCh 2245",
                    "orientacion": "Documento asociado: Hojas de Datos de Seguridad de las sustancias peligrosas que se utilizan."
                },
                {
                    "requisito": "Si se usan maquinarias automotrices (grúas, tractores), ¿los operadores tienen licencia vigente?",
                    "norma": "Art. 43 DS 594/99 MINSAL",
                    "orientacion": "Documento asociado: Licencia de conductor según el tipo de maquinaria automotriz."
                }
            ]
        },
        {
            "titulo": "8. De la Prevención y Protección contra Incendios",
            "items": [
                {
                    "requisito": "¿Existe Programa de Prevención de Incendios?",
                    "norma": "Art. 44 DS 594/99 MINSAL",
                    "orientacion": "Documento asociado: Programa de Prevención de Incendios o Plan de Emergencia vigente."
                },
                {
                    "requisito": "¿El tipo, número y distribución de extintores portátiles cumple con la norma?",
                    "norma": "Art. 45 y 46 DS 594/99 MINSAL",
                    "orientacion": "Art. 46 establece los potenciales de extinción mínimos por superficie. Verificar revisión vigente."
                },
                {
                    "requisito": "¿Los extintores portátiles cumplen los requisitos del Decreto 369/96?",
                    "norma": "Art. 45 y 51 DS 594/99 MINSAL",
                    "orientacion": "DS 369/1996 se refiere a la revisión técnica anual, señalización y registro de mantenimiento."
                },
                {
                    "requisito": "¿El personal tiene instrucción teórica Y práctica en el manejo de extintores?",
                    "norma": "Art. 48 DS 594/99 MINSAL",
                    "orientacion": "La instrucción debe ser efectuada por personal idóneo (Bomberos, ACHS, IST, etc.). Verificar registro."
                },
                {
                    "requisito": "¿La Autoridad Sanitaria ha revisado si se requiere sistema automático de extinción?",
                    "norma": "Art. 52 DS 594/99 MINSAL",
                    "orientacion": "La autoridad sanitaria determina si corresponde exigir sistema automático según tipo de instalación."
                }
            ]
        },
        {
            "titulo": "9. De los Contaminantes Químicos",
            "items": [
                {
                    "requisito": "¿Existen evaluaciones de exposición a contaminantes químicos según los límites permisibles?",
                    "norma": "Art. 61 DS 594/99 MINSAL",
                    "orientacion": "Documento asociado: Informe de evaluación de exposición a agentes químicos del organismo administrador."
                },
                {
                    "requisito": "¿Si existen trabajadores expuestos sobre los límites permisibles, existen medidas de control?",
                    "norma": "Art. 65 DS 594/99 MINSAL",
                    "orientacion": "Documento asociado: Programa de control de contaminantes químicos con medidas de ingeniería o EPP."
                },
                {
                    "requisito": "¿Los trabajadores expuestos a contaminantes químicos están en programa de vigilancia de salud?",
                    "norma": "Art. 68 DS 594/99 MINSAL",
                    "orientacion": "Documento asociado: Programa de Vigilancia Médica del organismo administrador."
                }
            ]
        },
        {
            "titulo": "10. Ruido",
            "items": [
                {
                    "requisito": "¿Existe informe de evaluación de exposición ocupacional al ruido (dosimetría)?",
                    "norma": "Art. 70 DS 594/99 MINSAL",
                    "orientacion": "Documento asociado: Informe de dosimetría realizado por el organismo administrador."
                },
                {
                    "requisito": "Si existen trabajadores expuestos sobre los 85 dB, ¿existen medidas de control implementadas?",
                    "norma": "Art. 75 DS 594/99 MINSAL",
                    "orientacion": "Jerarquía de controles: ingeniería → administración → EPP (protector auditivo). Verificar evidencia."
                },
                {
                    "requisito": "¿Los trabajadores expuestos a ruido están en programa de vigilancia auditiva (audiometrías)?",
                    "norma": "Art. 82 DS 594/99 MINSAL",
                    "orientacion": "Documento asociado: Registros de audiometría vigente de cada trabajador expuesto."
                }
            ]
        },
        {
            "titulo": "11. Vibraciones",
            "items": [
                {
                    "requisito": "¿Existe informe de evaluación de exposición a vibraciones (cuerpo entero y/o mano-brazo)?",
                    "norma": "Art. 83 DS 594/99 MINSAL",
                    "orientacion": "Documento asociado: Informe de evaluación de vibraciones del organismo administrador."
                },
                {
                    "requisito": "¿Se han implementado medidas de control para los trabajadores sobre los límites de vibraciones?",
                    "norma": "Art. 88 DS 594/99 MINSAL",
                    "orientacion": "Documento asociado: Programa de control de exposición a vibraciones."
                }
            ]
        },
        {
            "titulo": "12. De la Exposición Ocupacional al Calor",
            "items": [
                {
                    "requisito": "¿Existe informe de evaluación de exposición ocupacional al calor (TGBH)?",
                    "norma": "Art. 96 DS 594/99 MINSAL",
                    "orientacion": "Documento asociado: Informe de evaluación al calor con índice WBGT del organismo administrador."
                },
                {
                    "requisito": "¿Los valores de exposición al calor son iguales o inferiores a los del DS 594?",
                    "norma": "Art. 97 DS 594/99 MINSAL",
                    "orientacion": "Los valores deben compararse con la tabla de límites del DS 594 según tipo de trabajo (liviano/moderado/pesado)."
                },
                {
                    "requisito": "¿Existen planes de mejoramiento para disminuir la exposición al calor?",
                    "norma": "Art. 96, 97 y 98 DS 594/99 MINSAL",
                    "orientacion": "Documento asociado: Plan para solucionar la exposición a calor de los trabajadores."
                }
            ]
        },
        {
            "titulo": "13. De la Exposición Ocupacional al Frío",
            "items": [
                {
                    "requisito": "¿Existe informe de evaluación de exposición ocupacional al frío?",
                    "norma": "Art. 99, 100 y 101 DS 594/99 MINSAL",
                    "orientacion": "Las condiciones de exposición al frío deben ser evaluadas para su control y registro."
                },
                {
                    "requisito": "¿Los valores de exposición al frío son inferiores a los establecidos en el DS 594?",
                    "norma": "Art. 99, 100 y 101 DS 594/99 MINSAL",
                    "orientacion": "Comparar con valores límites de la norma."
                },
                {
                    "requisito": "¿Existen planes para solucionar la exposición al frío de los trabajadores?",
                    "norma": "Art. 99, 100 y 101 DS 594/99 MINSAL",
                    "orientacion": "Documento asociado: Planes para solucionar la exposición al frío de los trabajadores."
                },
                {
                    "requisito": "¿Las cámaras frigoríficas cuentan con sistema de seguridad y vigilancia adecuado?",
                    "norma": "Art. 102 DS 594/99 MINSAL",
                    "orientacion": "Referido a salas frigoríficas donde los trabajadores permanecen al interior."
                }
            ]
        },
        {
            "titulo": "14. De la Iluminación",
            "items": [
                {
                    "requisito": "¿Existe informe de evaluación del nivel de iluminación general y localizada en los puestos de trabajo?",
                    "norma": "Art. 103 y 104 DS 594/99 MINSAL",
                    "orientacion": "Documento asociado: Informe de evaluación de iluminación por puesto de trabajo (en lux)."
                },
                {
                    "requisito": "¿Los valores de iluminación cumplen con los mínimos establecidos en el DS 594?",
                    "norma": "Art. 103 y 104 DS 594/99 MINSAL",
                    "orientacion": "Comparar valores medidos con los exigidos por la legislación vigente según tipo de tarea."
                },
                {
                    "requisito": "¿Existen planes para solucionar los problemas de iluminación detectados?",
                    "norma": "Art. 103 y 104 DS 594/99 MINSAL",
                    "orientacion": "Documento asociado: Planes para solucionar los problemas de iluminación en los puestos afectados."
                }
            ]
        },
        {
            "titulo": "15. De las Radiaciones",
            "items": [
                {
                    "requisito": "¿Existe informe de evaluación de la exposición a radiaciones no ionizantes?",
                    "norma": "Art. 107, 108 y 109 DS 594/99 MINSAL",
                    "orientacion": "Documento asociado: Informe de evaluación de exposición a radiaciones no ionizantes."
                },
                {
                    "requisito": "¿Los valores de radiación son menores a los que exige la norma?",
                    "norma": "Art. 107, 108 y 109 DS 594/99 MINSAL",
                    "orientacion": "Comparar valores de las evaluaciones con los límites establecidos en el DS 594."
                },
                {
                    "requisito": "¿Los equipos con radiaciones ionizantes cuentan con autorización de funcionamiento de la Autoridad Sanitaria?",
                    "norma": "Art. 2 DS 133/84",
                    "orientacion": "Documento asociado: Autorización de equipos radiológicos."
                }
            ]
        },
        {
            "titulo": "16. Exposición a Radiación UV",
            "items": [
                {
                    "requisito": "¿La organización publica diariamente en lugar visible las medidas de control para radiación UV?",
                    "norma": "Art. 109b DS 594/99 MINSAL",
                    "orientacion": "Verificar en terreno el requisito: cartelería, pantallas u otro medio de comunicación visible."
                },
                {
                    "requisito": "¿Existe programa de medidas de protección adicionales para puestos de trabajo expuestos al sol?",
                    "norma": "Art. 109b DS 594/99 MINSAL",
                    "orientacion": "Documento asociado: Programa de protección a exposición de radiación UV de origen solar."
                },
                {
                    "requisito": "¿Existe programa de instrucción teórico-práctico para los trabajadores sobre radiación UV?",
                    "norma": "Art. 109b DS 594/99 MINSAL",
                    "orientacion": "Documento asociado: Programa de capacitación dirigido a trabajadores sobre exposición UV."
                },
                {
                    "requisito": "¿Los trabajadores expuestos usan ropa protectora adecuada (polera manga larga, protector solar, etc.)?",
                    "norma": "Art. 109b DS 594/99 MINSAL",
                    "orientacion": "Documento asociado: Registro de entrega de EPP (protector solar, ropa, lentes, sombrero)."
                }
            ]
        },
        {
            "titulo": "17. Control de Riesgos MMC y TMERT (Ergonomía)",
            "items": [
                {
                    "requisito": "¿El empleador vela porque se utilicen medios adecuados para el manejo manual de cargas?",
                    "norma": "Art. 211-G Ley 20001/05 MINTRAB",
                    "orientacion": "Verificar en terreno si los trabajadores están expuestos a manejo manual de cargas y las medidas adoptadas."
                },
                {
                    "requisito": "¿Se prohíbe levantar cargas superiores a 25 kg sin ayuda mecánica?",
                    "norma": "Art. 211-H Ley 20001/05 MINTRAB",
                    "orientacion": "Facilitar al trabajador un sistema de manejo mecánico de cargas (grúa, carro, etc.)."
                },
                {
                    "requisito": "¿Se prohíbe las operaciones de carga y descarga manual para la mujer embarazada?",
                    "norma": "Art. 211-I Ley 20001/05 MINTRAB",
                    "orientacion": "Contar con registro de casos de embarazo y prohibirles cualquier tipo de manipulación de cargas."
                },
                {
                    "requisito": "¿Se prohíbe que los menores de 18 años y mujeres lleven cargas superiores a los límites legales?",
                    "norma": "Art. 211-J Ley 20001/05 MINTRAB",
                    "orientacion": "Capacitar a mujeres y menores de edad, otorgandoles también un sistema de manejo mecánico."
                },
                {
                    "requisito": "¿Existe programa de control para eliminar o mitigar los riesgos ergonómicos detectados?",
                    "norma": "Art. 110 a.2 DS 594/99 MINSAL",
                    "orientacion": "Crear un programa de control estableciendo las medidas ergonómicas necesarias para cada puesto de trabajo."
                }
            ]
        },
        {
            "titulo": "18. Sobre los Agentes Biológicos",
            "items": [
                {
                    "requisito": "¿Los trabajadores con indicadores biológicos alterados están en Programa de Vigilancia Médica?",
                    "norma": "Art. 115 y 116 DS 594/99 MINSAL",
                    "orientacion": "Documento asociado: Programa de Vigilancia Médica de Indicadores biológicos."
                },
                {
                    "requisito": "¿Se han considerado valores límites biológicos para las sustancias con indicador biológico?",
                    "norma": "Art. 111 y 112 DS 594/99 MINSAL",
                    "orientacion": "Si los valores de evaluaciones biológicas están sobrepasando los límites, tomar medidas de control."
                },
                {
                    "requisito": "¿Se han realizado evaluaciones y tomado medidas necesarias para agentes biológicos del ambiente laboral?",
                    "norma": "Informes y guías técnicas MINSAL",
                    "orientacion": "Identificar las posibles fuentes de intoxicaciones y enfermedades. Realizar un plan de acción."
                },
                {
                    "requisito": "¿Cuenta con programa de sanitización y desratización que asegure el control de vectores y plagas?",
                    "norma": "Art. 11 DS 594/99 MINSAL",
                    "orientacion": "Documento asociado: Contrato y programa con empresa autorizada en Control de Vectores."
                }
            ]
        }
    ],

    "ISO 14001 - Gestión Medioambiental": [
        {
            "titulo": "1. Manejo de Residuos",
            "items": [
                {
                    "requisito": "¿Los residuos peligrosos (RESPEL) se almacenan cumpliendo DS 148 (piso impermeable, pretil, señalética)?",
                    "norma": "DS 148/2004 MINSAL",
                    "orientacion": "Verificar en terreno: piso impermeable, pretil de contención, señalética de peligro y fichas de seguridad disponibles."
                },
                {
                    "requisito": "¿Los residuos no peligrosos están segregados en origen y en contenedores identificados por código de colores?",
                    "norma": "ISO 14001:2015 / NCh 3267",
                    "orientacion": "Verificar segregación en origen: orgánicos, reciclables, y no reciclables en contenedores diferenciados."
                },
                {
                    "requisito": "¿Se cuenta con hojas de ruta o manifiestos de transporte de residuos actualizados?",
                    "norma": "DS 148/2004 / DS 4/1992 MINSAL",
                    "orientacion": "Documento asociado: Manifiestos de retiro de residuos peligrosos con firma del receptor autorizado."
                }
            ]
        },
        {
            "titulo": "2. Control de Derrames y Sustancias Peligrosas",
            "items": [
                {
                    "requisito": "¿Los kits antiderrames están ubicados cerca de puntos críticos y completos?",
                    "norma": "ISO 14001:2015 / DS 148",
                    "orientacion": "Verificar en terreno: ubicación, absorbentes, cucharones, bolsas y EPP de respuesta incluidos."
                },
                {
                    "requisito": "¿Las bodegas de sustancias peligrosas están ventiladas y con incompatibilidades segregadas?",
                    "norma": "NCh 382 / DS 148/2004",
                    "orientacion": "Verificar pretiles de contención operativos y volúmenes de los pretiles acordes a la cantidad almacenada."
                },
                {
                    "requisito": "¿Las Hojas de Datos de Seguridad (HDS/SDS) están disponibles físicamente en español para todas las sustancias?",
                    "norma": "NCh 2245 / DS 594 Art. 42",
                    "orientacion": "Documento asociado: HDS en español, vigentes, accesibles al trabajador sin requerirlo a supervisión."
                }
            ]
        },
        {
            "titulo": "3. Cumplimiento de Compromisos Ambientales (RCA)",
            "items": [
                {
                    "requisito": "¿Se evidencia cumplimiento de las medidas de mitigación o compensación de la RCA?",
                    "norma": "Ley 19.300 / DS 40/2012 MMA",
                    "orientacion": "Documento asociado: Resolución de Calificación Ambiental vigente y registros de cumplimiento de compromisos."
                },
                {
                    "requisito": "¿Existe seguimiento del consumo de agua y energía para identificar oportunidades de mejora?",
                    "norma": "ISO 14001:2015 Cláusula 9.1",
                    "orientacion": "Documento asociado: Registros mensuales de consumo de agua y energía para seguimiento de indicadores."
                }
            ]
        },
        {
            "titulo": "4. Preparación y Respuesta ante Emergencias Ambientales",
            "items": [
                {
                    "requisito": "¿Los Planes de Emergencia Ambiental están actualizados y son conocidos por el personal del área?",
                    "norma": "ISO 14001:2015 Cláusula 8.2",
                    "orientacion": "Documento asociado: Plan de Emergencia Ambiental con fecha de actualización vigente y difusión registrada."
                },
                {
                    "requisito": "¿Se han realizado simulacros de derrame o fuga con informe de lecciones aprendidas?",
                    "norma": "ISO 14001:2015 Cláusula 8.2",
                    "orientacion": "Documento asociado: Registro de simulacro con fecha, participantes y lecciones aprendidas."
                }
            ]
        },
        {
            "titulo": "5. Emisiones a la Atmósfera (Control de Material Particulado y Gases)",
            "items": [
                {
                    "requisito": "¿Se aplican medidas para el control de material particulado (polvo en suspensión) como humectación de caminos?",
                    "norma": "DS 138/2005 MINSAL",
                    "orientacion": "Verificar en terreno: camiones aljibe humectando caminos, encapsulamiento de correas o malla rachel cortaviento en acopios."
                },
                {
                    "requisito": "¿Los grupos electrógenos o fuentes fijas cuentan con la declaración de emisiones en línea (RETC)?",
                    "norma": "DS 4/1992 MINSAL",
                    "orientacion": "Revisar los certificados históricos del sistema RETC (Registro de Emisiones y Transferencias de Contaminantes)."
                }
            ]
        },
        {
            "titulo": "6. Gestión de Residuos Líquidos (RILes) y Aguas Servidas",
            "items": [
                {
                    "requisito": "¿Las fosas sépticas o baños químicos aseguran su limpieza mensual por empresas autorizadas y con su respectivo manifiesto?",
                    "norma": "DS 594 Art. 24",
                    "orientacion": "Exigir los certificados de disposición final visados por el prestador de servicios sanitarios autorizado."
                },
                {
                    "requisito": "¿Las áreas de talleres de taller o lavado de maquinarias cuentan con trampas de grasas o separadores de hidrocarburos operativos?",
                    "norma": "DS 90/2000 SEGPRES",
                    "orientacion": "Verificar en terreno que las sentinas no estén saturadas de lodos o grasas y tengan mantenimiento al día."
                }
            ]
        },
        {
            "titulo": "7. Ruido Comunitario o Perimetral",
            "items": [
                {
                    "requisito": "¿Las operaciones que generan ruido hacia la comunidad cuentan con monitoreo perimetral homologado (NSCEDS)?",
                    "norma": "DS 38 MMA",
                    "orientacion": "Típicamente aplicable cerca de zonas urbanas o de nidificación sensible. Solicitar estudio de impacto o de ruido basal a laboratorios autorizados."
                }
            ]
        },
        {
            "titulo": "8. Liderazgo, Capacitación y Cultura Ambiental",
            "items": [
                {
                    "requisito": "¿Se ha difundido y se encuentra visible la Política Integrada o Política de Medio Ambiente de la organización?",
                    "norma": "ISO 14001:2015",
                    "orientacion": "Cerciorarse de que el personal de primera línea entienda cómo su tarea contamina y los objetivos anuales (Ej. reciclaje)."
                },
                {
                    "requisito": "¿Existe registro de 'Charlas de 5 Minutos' o capacitaciones enfocadas exclusivamente en la concientización ambiental?",
                    "norma": "ISO 14001:2015 Cláusula 7.3",
                    "orientacion": "Solicitar listado de capacitaciones ambientales (manejo de extintores y segregación) con la firma de los trabajadores involucrados."
                }
            ]
        }
    ],

    "ISO 9001 - Gestión de Calidad": [
        {
            "titulo": "1. Contexto, Liderazgo y Apoyo",
            "items": [
                {
                    "requisito": "¿La Política de Calidad está publicada, vigente y es comprendida por el personal de la instalación?",
                    "norma": "ISO 9001:2015 Cláusula 5.2.2",
                    "orientacion": "Consultar a trabajadores al azar si conocen el propósito de la política y cómo su trabajo afecta a la calidad."
                },
                {
                    "requisito": "¿Se mantiene un control estricto de las versiones vigentes de los procedimientos y formatos utilizados en terreno?",
                    "norma": "ISO 9001:2015 Cláusula 7.5",
                    "orientacion": "Verificar que el personal no use formatos obsoletos impresos. Solicitar lista maestra de documentos vigentes."
                },
                {
                    "requisito": "¿Los equipos de medición (torquímetros, multitesters, pie de metro) cuentan con certificados de calibración vigentes y trazables?",
                    "norma": "ISO 9001:2015 Cláusula 7.1.5",
                    "orientacion": "Solicitar certificado y constatar en terreno la etiqueta de calibración pegada en el equipo."
                }
            ]
        },
        {
            "titulo": "2. Operación y Control de Procesos",
            "items": [
                {
                    "requisito": "¿La prestación del servicio se ejecuta basándose estrictamente en los Planes de Calidad (PAC / PPI) aprobados?",
                    "norma": "ISO 9001:2015 Cláusula 8.5.1",
                    "orientacion": "Plan de Inspección y Ensayo debidamente firmado en terreno por los ejecutores y mandantes."
                },
                {
                    "requisito": "¿Se evaluó a los proveedores o contratistas críticos que están ejecutando labores operativas?",
                    "norma": "ISO 9001:2015 Cláusula 8.4",
                    "orientacion": "Control de proveedores externos. Evidencia de que cumplen los criterios de calidad pactados."
                },
                {
                    "requisito": "¿Existe correcta trazabilidad y preservación de los materiales o productos críticos en bodega/terreno?",
                    "norma": "ISO 9001:2015 Cláusula 8.5.2 y 8.5.4",
                    "orientacion": "Verificar limpieza, etiquetado de componentes, lote, fecha de vencimiento y condiciones de guardado."
                }
            ]
        },
        {
            "titulo": "3. Control de Salidas No Conformes",
            "items": [
                {
                    "requisito": "¿Existen registros formales físicos o digitales para el tratamiento de productos, servicios o procesos no conformes?",
                    "norma": "ISO 9001:2015 Cláusula 8.7",
                    "orientacion": "Qué sucede si un entregable falla o hay un reclamo técnico. ¿Se levantan acciones correctivas y se segrega el elemento?"
                },
                {
                    "requisito": "¿Se segregan físicamente los productos o repuestos defectuosos para evitar su uso accidental?",
                    "norma": "ISO 9001:2015 Cláusula 8.7",
                    "orientacion": "Visitar pañol o bodega y observar si hay un sector demarcado y aislado para material 'No Conforme' o 'Scrap'."
                }
            ]
        },
        {
            "titulo": "4. Desempeño y Mejora Continua",
            "items": [
                {
                    "requisito": "¿Se toman acciones correctivas fundamentadas en análisis de causa raíz ante las no conformidades previas?",
                    "norma": "ISO 9001:2015 Cláusula 10.2",
                    "orientacion": "Revisar un reporte de Hallazgo anterior y verificar si se abordó la causa base y no solo el síntoma."
                },
                {
                    "requisito": "¿El personal tiene conocimiento de los Objetivos de Calidad del área y de su desempeño actual?",
                    "norma": "ISO 9001:2015 Cláusula 6.2 y 9.1",
                    "orientacion": "Visualización de KPIs de Calidad en paneles del área o conocimiento general de las metas operacionales."
                }
            ]
        }
    ],

    "ISO 45001 - Seguridad y Salud": [
        {
            "titulo": "1. Liderazgo, Participación y Consulta",
            "items": [
                {
                    "requisito": "¿Se evidencia liderazgo activo gerencial mediante inspecciones planeadas y caminatas gerenciales?",
                    "norma": "ISO 45001:2018 Cláusula 5.1",
                    "orientacion": "Caminatas de Liderazgo (LPI), firmas de la alta administración y toma de conocimiento del terreno."
                },
                {
                    "requisito": "¿El Comité Paritario de Higiene y Seguridad funciona activamente y gestiona inspecciones formales?",
                    "norma": "ISO 45001:2018 Cláusula 5.4",
                    "orientacion": "Revisar la última acta del CPHS y constatar si participaron en la investigación de accidentes."
                },
                {
                    "requisito": "¿Se consulta y hace partícipe a los trabajadores no directivos en la selección de controles y evaluación de EPP?",
                    "norma": "ISO 45001:2018 Cláusula 5.4",
                    "orientacion": "Encuestas de seguridad de clima preventivo o actas de votación durante el testeo de elementos de protección."
                }
            ]
        },
        {
            "titulo": "2. Planificación y Evaluación de Riesgos",
            "items": [
                {
                    "requisito": "¿La matriz de Identificación de Peligros y Evaluación de Riesgos (IPERC) está actualizada y disponible en terreno?",
                    "norma": "ISO 45001:2018 Cláusula 6.1.2",
                    "orientacion": "Los trabajadores de la instalación deben conocer formalmente sus riesgos residuales inaceptables."
                },
                {
                    "requisito": "¿Existe una matriz / registro actualizado para asegurar el cumplimiento de Requisitos Legales vigentes?",
                    "norma": "ISO 45001:2018 Cláusula 6.1.3",
                    "orientacion": "Matriz Legal de Cumplimiento firmada y validada por el asesor del sistema de gestión u organismo experto."
                }
            ]
        },
        {
            "titulo": "3. Control Operacional y Contratistas",
            "items": [
                {
                    "requisito": "¿Las labores con riesgo crítico en terreno están amparadas bajo un Procedimiento de Trabajo Seguro (PTS) riguroso?",
                    "norma": "ISO 45001:2018 Cláusula 8.1.1",
                    "orientacion": "Verificar en terreno si los trabajadores portan su Análisis de Riesgo del Trabajo (ART) firmado y el PTS aplicable."
                },
                {
                    "requisito": "¿Los trabajadores de las empresas subcontratistas cumplen con los mismos estándares operacionales de SST que la empresa principal?",
                    "norma": "ISO 45001:2018 Cláusula 8.1.4",
                    "orientacion": "Verificación del Reglamento Especial para Contratistas, charlas de inducción y acreditación del personal subcontratista."
                }
            ]
        },
        {
            "titulo": "4. Preparación y Respuesta ante Emergencias",
            "items": [
                {
                    "requisito": "¿Se ha ejecutado y archivado el Programa Anual de Simulacros para escenarios de emergencia reales (Fuego, Derrumbo, Rescate)?",
                    "norma": "ISO 45001:2018 Cláusula 8.2",
                    "orientacion": "Protocolo de Evacuación o Plan de Emergencia (PEE) y el informe del último simulacro de brigadas."
                },
                {
                    "requisito": "¿Los equipos de respuesta a emergencias (Camillas, Lavaojos, Botiquines extintores) están inspeccionados y accesibles?",
                    "norma": "ISO 45001:2018 Cláusula 8.2",
                    "orientacion": "Verificar el checklist de lavaojos autónomos y el sello inviolable o fecha de caducidad de insumos del botiquín."
                }
            ]
        },
        {
            "titulo": "5. Evaluación de Desempeño y Mejora",
            "items": [
                {
                    "requisito": "¿Los incidentes o casi incidentes de seguridad resultaron investigados utilizando metodología estructurada (ICAM, Ishikawa)?",
                    "norma": "ISO 45001:2018 Cláusula 10.2",
                    "orientacion": "Trazabilidad del levantamiento de eventos. Si no hubo incidentes, evidenciar 'Reportes de Desvíos'."
                },
                {
                    "requisito": "¿El programa de Auditorías Internas y el avance de cierres de hallazgos previos están al día?",
                    "norma": "ISO 45001:2018 Cláusula 9.2",
                    "orientacion": "Revisar que la organización efectivamente está ejecutando su programa de verificación anual."
                }
            ]
        }
    ]
}
