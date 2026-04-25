"""
===========================================
⚠️ OTHER RISKS ENGINE - v2.0
===========================================
Motor de evaluación de riesgos no fatales.
Expandido a 45+ riesgos categorizados con
severidad, medidas preventivas y normativa.

Autor: CGT
Versión: 2.0
"""

from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

# Categorías de riesgos
CATEGORIAS_RIESGOS = {
    "Ambiental": "Exposición a factores ambientales",
    "Ergonómico": "Factores que afectan postura y movimiento",
    "Biológico": "Exposición a agentes biológicos",
    "Químico": "Exposición a sustancias químicas",
    "Psicosocial": "Factores organizacionales y de estrés",
    "Vehículos": "Riesgos de tránsito y circulación",
    "Herramientas": "Riesgos de manejo de herramientas",
    "Otros": "Riesgos diversos"
}

# Severidad de riesgos
SEVERIDAD = {
    "Baja": "Lesiones leves",
    "Media": "Incapacidad temporal",
    "Alta": "Incapacidad prolongada/permanente"
}

OTHER_RISKS_EXPANDIDO = [
    # ======= RIESGOS AMBIENTALES (10 riesgos) =======
    {
        "id": "AR01",
        "riesgo": "Exposición a radiación UV (Sol)",
        "categoria": "Ambiental",
        "severidad": "Media",
        "normativa": "DS 594",
        "medida": "Uso obligatorio de bloqueador solar (reaplicar cada 2-3 horas), legionario, lentes con filtro UV y ropa de manga larga.",
        "periodo_revision": "Semestral"
    },
    {
        "id": "AR02",
        "riesgo": "Exposición a polvo en suspensión o fuertes vientos",
        "categoria": "Ambiental",
        "severidad": "Media",
        "normativa": "DS 594",
        "medida": "Uso de protección respiratoria (mascarilla o respirador medio rostro), uso de antiparras herméticas y transitar alejado de zonas de levantamiento de polvo.",
        "periodo_revision": "Trimestral"
    },
    {
        "id": "AR03",
        "riesgo": "Estrés térmico (Por frío al amanecer/calor en el día)",
        "categoria": "Ambiental",
        "severidad": "Baja",
        "normativa": "DS 594",
        "medida": "Mantener hidratación constante (beber agua frecuentemente), uso de ropa por capas (sistema cebolla) y programar pausas en áreas climatizadas o bajo sombra.",
        "periodo_revision": "Mensual"
    },
    {
        "id": "AR04",
        "riesgo": "Iluminación deficiente",
        "categoria": "Ambiental",
        "severidad": "Baja",
        "normativa": "DS 594",
        "medida": "Instalar luminarias de al menos 500 lux en áreas de trabajo, mantener equipos de iluminación en buen estado y limpios.",
        "periodo_revision": "Trimestral"
    },
    {
        "id": "AR05",
        "riesgo": "Ruido excesivo (> 85 dB)",
        "categoria": "Ambiental",
        "severidad": "Media",
        "normativa": "DS 594",
        "medida": "Uso obligatorio de protección auditiva (tapones o orejeras), realizar audiometrías anuales y mapear zonas de riesgo auditivo.",
        "periodo_revision": "Semestral"
    },
    {
        "id": "AR06",
        "riesgo": "Vibración de equipos o maquinaria",
        "categoria": "Ambiental",
        "severidad": "Media",
        "normativa": "DS 594",
        "medida": "Usar equipos con sistemas anti-vibración, limitar tiempo de exposición, usar guantes de absorción y realizar rotación de tareas.",
        "periodo_revision": "Trimestral"
    },
    {
        "id": "AR07",
        "riesgo": "Humedad excesiva en áreas de trabajo",
        "categoria": "Ambiental",
        "severidad": "Baja",
        "normativa": "DS 594",
        "medida": "Mantener ventilación adecuada, usar drenajes, instalar sistemas de deshumidificación si es necesario.",
        "periodo_revision": "Mensual"
    },
    {
        "id": "AR08",
        "riesgo": "Contaminación por aguas residuales",
        "categoria": "Ambiental",
        "severidad": "Alta",
        "normativa": "DS 594 + ISO 14001",
        "medida": "Usar EPP impermeables, vacunas contra hepatitis A/B, duchas y cambio de ropa después del turno.",
        "periodo_revision": "Mensual"
    },
    {
        "id": "AR09",
        "riesgo": "Contaminación por gases tóxicos (gases sin olor)",
        "categoria": "Ambiental",
        "severidad": "Alta",
        "normativa": "DS 594",
        "medida": "Monitoreo continuo con detectores de gases, respirador con filtros específicos, evacuación inmediata si se detecta.",
        "periodo_revision": "Semanal"
    },
    {
        "id": "AR10",
        "riesgo": "Contaminación por agentes biológicos (bacterias, hongos)",
        "categoria": "Biológico",
        "severidad": "Media",
        "normativa": "DS 594",
        "medida": "Usar guantes desechables, mascarilla N95, higiene de manos frecuente, vacunaciones al día.",
        "periodo_revision": "Trimestral"
    },
    
    # ======= RIESGOS ERGONÓMICOS (10 riesgos) =======
    {
        "id": "ER01",
        "riesgo": "Caídas al mismo nivel (Terreno irregular, piedras, desniveles)",
        "categoria": "Ergonómico",
        "severidad": "Media",
        "normativa": "DS 594",
        "medida": "Transitar solo por vías peatonales habilitadas y señalizadas, mantener la vista en el camino, no usar celular al caminar, calzado de seguridad caña alta.",
        "periodo_revision": "Diaria"
    },
    {
        "id": "ER02",
        "riesgo": "Manejo manual de cargas (Sobreesfuerzo, lumbago)",
        "categoria": "Ergonómico",
        "severidad": "Media",
        "normativa": "DS 594",
        "medida": "Evaluar peso antes de levantar (máx. 25 kg hombres / 20 kg mujeres), flexionar rodillas, pedir ayuda o usar equipos mecánicos.",
        "periodo_revision": "Mensual"
    },
    {
        "id": "ER03",
        "riesgo": "Ergonomía (Posturas forzadas, movimientos repetitivos)",
        "categoria": "Ergonómico",
        "severidad": "Media",
        "normativa": "DS 594",
        "medida": "Realizar pausas activas cada hora, rotación de tareas, mantener posturas neutras, solicitar ayuda para cargas.",
        "periodo_revision": "Diaria"
    },
    {
        "id": "ER04",
        "riesgo": "Trabajo en posiciones de rodillas prolongadas",
        "categoria": "Ergonómico",
        "severidad": "Baja",
        "normativa": "DS 594",
        "medida": "Usar rodilleras de protección, realizar pausas cada 30 min, fortalecer rodillas con ejercicios.",
        "periodo_revision": "Mensual"
    },
    {
        "id": "ER05",
        "riesgo": "Trabajo en altura con fatiga acumulada",
        "categoria": "Ergonómico",
        "severidad": "Alta",
        "normativa": "DS 594",
        "medida": "Limitar jornadas a 8 horas, pausas de descanso cada 2 horas, evaluación médica de resistencia.",
        "periodo_revision": "Trimestral"
    },
    {
        "id": "ER06",
        "riesgo": "Presión de aire y descompresión (en trabajos subacuáticos)",
        "categoria": "Ergonómico",
        "severidad": "Alta",
        "normativa": "DS 594",
        "medida": "Seguir estrictamente tablas de descompresión, médico buzo disponible, cámara de recompresión cercana.",
        "periodo_revision": "Semanal"
    },
    {
        "id": "ER07",
        "riesgo": "Síndrome del túnel carpiano (Movimientos repetitivos)",
        "categoria": "Ergonómico",
        "severidad": "Media",
        "normativa": "DS 594",
        "medida": "Ejercicios de estiramiento, rotación de tareas, ajuste de puesto de trabajo, evaluación ocupacional.",
        "periodo_revision": "Mensual"
    },
    {
        "id": "ER08",
        "riesgo": "Distensión muscular por esfuerzos repentinos",
        "categoria": "Ergonómico",
        "severidad": "Media",
        "normativa": "DS 594",
        "medida": "Calentamiento previo, técnica correcta, progresión gradual de carga, estiramiento post-trabajo.",
        "periodo_revision": "Diaria"
    },
    {
        "id": "ER09",
        "riesgo": "Dolor de espalda crónico (Posturas sedentarias)",
        "categoria": "Ergonómico",
        "severidad": "Media",
        "normativa": "DS 594",
        "medida": "Escritorio ergonómico, descansos frecuentes, ejercicio de fortalecimiento, fisioterapia preventiva.",
        "periodo_revision": "Mensual"
    },
    {
        "id": "ER10",
        "riesgo": "Tendinitis (Sobrecarga de tendones)",
        "categoria": "Ergonómico",
        "severidad": "Media",
        "normativa": "DS 594",
        "medida": "Limitar actividades repetitivas, usar apoyo de muñeca, ejercicios de fortalecimiento, descanso recuperador.",
        "periodo_revision": "Mensual"
    },
    
    # ======= RIESGOS DE VEHÍCULOS (10 riesgos) =======
    {
        "id": "VE01",
        "riesgo": "Atropello por vehículos o maquinaria móvil",
        "categoria": "Vehículos",
        "severidad": "Alta",
        "normativa": "DS 594",
        "medida": "Respetar pasos peatonales, asegurar contacto visual con conductores, usar chaleco reflectante en todo momento.",
        "periodo_revision": "Diaria"
    },
    {
        "id": "VE02",
        "riesgo": "Accidente de tránsito (Conducción de vehículos)",
        "categoria": "Vehículos",
        "severidad": "Alta",
        "normativa": "Ley de tránsito",
        "medida": "Licencia de conducir vigente, entrenamiento defensivo, limite de velocidad, no usar teléfono al conducir.",
        "periodo_revision": "Semestral"
    },
    {
        "id": "VE03",
        "riesgo": "Choque entre equipos móviles",
        "categoria": "Vehículos",
        "severidad": "Alta",
        "normativa": "DS 594",
        "medida": "Señalización clara en maniobras, retrovisores en buen estado, velocidad controlada en zonas de trabajo.",
        "periodo_revision": "Diaria"
    },
    {
        "id": "VE04",
        "riesgo": "Volcamiento de vehículo o maquinaria",
        "categoria": "Vehículos",
        "severidad": "Alta",
        "normativa": "DS 594",
        "medida": "Mantener velocidades seguras en curvas, terreno nivelado, arnés de seguridad en operador.",
        "periodo_revision": "Diaria"
    },
    {
        "id": "VE05",
        "riesgo": "Caída de carga desde vehículo",
        "categoria": "Vehículos",
        "severidad": "Alta",
        "normativa": "DS 594",
        "medida": "Aseguramiento correcto de carga, inspección de amarres, cobertura de carga volátil.",
        "periodo_revision": "Diaria"
    },
    {
        "id": "VE06",
        "riesgo": "Inhalación de gases de escape (Espacios cerrados)",
        "categoria": "Vehículos",
        "severidad": "Media",
        "normativa": "DS 594",
        "medida": "Ventilación forzada en recintos cerrados, no dejar motores encendidos en zonas de trabajo.",
        "periodo_revision": "Diaria"
    },
    {
        "id": "VE07",
        "riesgo": "Quemaduras por superficies calientes (Motor en funcionamiento)",
        "categoria": "Vehículos",
        "severidad": "Media",
        "normativa": "DS 594",
        "medida": "Esperar a que motor enfríe, usar protección térmica, señalización de área caliente.",
        "periodo_revision": "Diaria"
    },
    {
        "id": "VE08",
        "riesgo": "Atrapamiento en mecanismos del vehículo",
        "categoria": "Vehículos",
        "severidad": "Alta",
        "normativa": "DS 594",
        "medida": "Motor apagado para mantenimiento, máquinas paradas, guardias en lugar, señalización.",
        "periodo_revision": "Semanal"
    },
    {
        "id": "VE09",
        "riesgo": "Pérdida de estabilidad en terrenos irregulares",
        "categoria": "Vehículos",
        "severidad": "Media",
        "normativa": "DS 594",
        "medida": "Reconocimiento previo del terreno, velocidad reducida, monitores de inclinación.",
        "periodo_revision": "Diaria"
    },
    {
        "id": "VE10",
        "riesgo": "Exposición a polvo durante transporte en terreno sin pavimentar",
        "categoria": "Vehículos",
        "severidad": "Baja",
        "normativa": "DS 594",
        "medida": "Cabina sellada con filtros, uso de mascarilla, riego de caminos.",
        "periodo_revision": "Diaria"
    },
    
    # ======= RIESGOS CON HERRAMIENTAS (8 riesgos) =======
    {
        "id": "HE01",
        "riesgo": "Uso de herramientas manuales (Golpes, cortes, pellizcos)",
        "categoria": "Herramientas",
        "severidad": "Media",
        "normativa": "DS 594",
        "medida": "Inspección pre-uso (cinta de color), guantes de cabritilla o anticorte, prohibición de herramientas hechizas.",
        "periodo_revision": "Diaria"
    },
    {
        "id": "HE02",
        "riesgo": "Proyección de partículas (tareas cercanas)",
        "categoria": "Herramientas",
        "severidad": "Media",
        "normativa": "DS 594",
        "medida": "Uso de protección ocular de seguridad (lentes o careta), mantener distancia de seguridad, biombos si aplica.",
        "periodo_revision": "Diaria"
    },
    {
        "id": "HE03",
        "riesgo": "Cortes con sierra circular o cuchillo",
        "categoria": "Herramientas",
        "severidad": "Media",
        "normativa": "DS 594",
        "medida": "Guardias de seguridad ajustadas, botones de parada de emergencia, usar empujadores de madera.",
        "periodo_revision": "Semanal"
    },
    {
        "id": "HE04",
        "riesgo": "Atrapamiento en taladro",
        "categoria": "Herramientas",
        "severidad": "Alta",
        "normativa": "DS 594",
        "medida": "Usar broca correcta, apretar bien la pieza, lentes de seguridad, manos alejadas de broca.",
        "periodo_revision": "Semanal"
    },
    {
        "id": "HE05",
        "riesgo": "Vibración crónica de herramienta neumática",
        "categoria": "Herramientas",
        "severidad": "Media",
        "normativa": "DS 594",
        "medida": "Límite de 2 horas diarias, guantes anti-vibración, ejercicios de recuperación.",
        "periodo_revision": "Mensual"
    },
    {
        "id": "HE06",
        "riesgo": "Pérdida de sujeción de herramienta eléctrica",
        "categoria": "Herramientas",
        "severidad": "Media",
        "normativa": "DS 594",
        "medida": "Cable con línea de vida, mangos ergonómicos, mantener área seca.",
        "periodo_revision": "Trimestral"
    },
    {
        "id": "HE07",
        "riesgo": "Quemadura por herramienta caliente",
        "categoria": "Herramientas",
        "severidad": "Baja",
        "normativa": "DS 594",
        "medida": "Dejar enfriar antes de tocar, guantes de protección térmica, señalizar área.",
        "periodo_revision": "Diaria"
    },
    {
        "id": "HE08",
        "riesgo": "Descarga eléctrica por herramienta mojada",
        "categoria": "Herramientas",
        "severidad": "Alta",
        "normativa": "DS 594",
        "medida": "Usar herramientas con doble aislamiento, conectar a interruptor diferencial, no usar en lluvia.",
        "periodo_revision": "Diaria"
    },
    
    # ======= RIESGOS PSICOSOCIALES (7 riesgos) =======
    {
        "id": "PS01",
        "riesgo": "Estrés laboral y síndrome de burnout",
        "categoria": "Psicosocial",
        "severidad": "Media",
        "normativa": "DS 594",
        "medida": "Programas de bienestar, pausas de descanso, comunicación clara, apoyo psicológico disponible.",
        "periodo_revision": "Trimestral"
    },
    {
        "id": "PS02",
        "riesgo": "Acoso laboral o discriminación",
        "categoria": "Psicosocial",
        "severidad": "Media",
        "normativa": "Ley 20.005",
        "medida": "Canales de denuncia confidenciales, protocolo de acción, investigación imparcial.",
        "periodo_revision": "Trimestral"
    },
    {
        "id": "PS03",
        "riesgo": "Sobrecarga de trabajo",
        "categoria": "Psicosocial",
        "severidad": "Baja",
        "normativa": "DS 594",
        "medida": "Redistribución de tareas, límite de jornadas, planificación realista.",
        "periodo_revision": "Mensual"
    },
    {
        "id": "PS04",
        "riesgo": "Falta de comunicación e información",
        "categoria": "Psicosocial",
        "severidad": "Baja",
        "normativa": "DS 594",
        "medida": "Reuniones periódicas, boletines internos, buzón de sugerencias.",
        "periodo_revision": "Mensual"
    },
    {
        "id": "PS05",
        "riesgo": "Inseguridad laboral (Inestabilidad contractual)",
        "categoria": "Psicosocial",
        "severidad": "Baja",
        "normativa": "Código del Trabajo",
        "medida": "Contratos claros y estables, comunicación de cambios organizacionales.",
        "periodo_revision": "Trimestral"
    },
    {
        "id": "PS06",
        "riesgo": "Conflicto trabajo-vida personal",
        "categoria": "Psicosocial",
        "severidad": "Baja",
        "normativa": "DS 594",
        "medida": "Flexibilidad horaria, teletrabajo cuando sea posible, programas de conciliación.",
        "periodo_revision": "Trimestral"
    },
    {
        "id": "PS07",
        "riesgo": "Violencia en el trabajo (Agresión de clientes o público)",
        "categoria": "Psicosocial",
        "severidad": "Alta",
        "normativa": "DS 594",
        "medida": "Protocolo de seguridad, entrenamiento de desescalada, apoyo psicológico post-incidente.",
        "periodo_revision": "Semestral"
    },
    
    # Original de la v1 sin duplicados
    {
        "id": "OT01",
        "riesgo": "Interacción con fauna local (Perros asilvestrados, insectos)",
        "categoria": "Otros",
        "severidad": "Baja",
        "normativa": "DS 594",
        "medida": "No alimentar ni acercarse a animales, mantener orden y aseo, reportar fauna al supervisor.",
        "periodo_revision": "Diaria"
    }
]


# ============ FUNCIONES AUXILIARES v2 ============

def obtener_riesgos_por_categoria(categoria: str) -> List[Dict]:
    """Obtiene todos los riesgos de una categoría"""
    return [r for r in OTHER_RISKS_EXPANDIDO if r['categoria'] == categoria]


def obtener_riesgos_por_severidad(severidad: str) -> List[Dict]:
    """Obtiene riesgos por nivel de severidad"""
    return [r for r in OTHER_RISKS_EXPANDIDO if r['severidad'] == severidad]


def buscar_riesgo(termino: str) -> List[Dict]:
    """Busca riesgos por término en nombre o descripción"""
    termino_lower = termino.lower()
    return [r for r in OTHER_RISKS_EXPANDIDO 
            if termino_lower in r['riesgo'].lower() or 
               termino_lower in r['medida'].lower()]


def obtener_estadisticas() -> Dict:
    """Retorna estadísticas del catálogo de riesgos"""
    return {
        "total_riesgos": len(OTHER_RISKS_EXPANDIDO),
        "categorias": list(CATEGORIAS_RIESGOS.keys()),
        "riesgos_por_categoria": {
            cat: len(obtener_riesgos_por_categoria(cat)) 
            for cat in CATEGORIAS_RIESGOS.keys()
        },
        "riesgos_por_severidad": {
            sev: len(obtener_riesgos_por_severidad(sev))
            for sev in SEVERIDAD.keys()
        }
    }


# ============ NEW ARCHITECTURE: OtherRisksEngine v2 ============

from dataclasses import dataclass, field
from datetime import datetime, timedelta
import json

@dataclass
class EvaluacionRiesgo:
    """Evaluación de exposición a un riesgo específico"""
    riesgo_id: str
    riesgo_nombre: str
    trabajador_id: str
    categoria: str
    severidad_potencial: str
    score_exposicion: float  # 0.0-1.0
    periodo_exposicion: str
    controles_implementados: List[str]
    fecha_evaluacion: str
    acciones_recomendadas: List[str]
    prioridad: str  # 'baja', 'media', 'alta', 'critica'


@dataclass
class AlertaRiesgo:
    """Alerta generada cuando exposición es crítica"""
    id: str
    riesgo_id: str
    trabajador_id: str
    tipo: str
    severidad: str
    descripcion: str
    fecha_generacion: str
    estado: str = "abierta"
    acciones_tomadas: List[str] = field(default_factory=list)


class OtherRisksEngine:
    """
    Motor avanzado de evaluación de riesgos no fatales.
    
    Características:
    - Evaluaciones automáticas de exposición
    - Scoring dinámico basado en duración y tipo
    - Recomendaciones contextuales
    - Alertas inteligentes
    - Histórico de evaluaciones
    - Reportes por trabajador/categoría
    - Integración BD completa
    """
    
    def __init__(self, db_path: str = None):
        """Inicializa el motor de riesgos no fatales"""
        self.db_path = db_path
        self._crear_tablas()
        logger.info("OtherRisksEngine inicializado")
    
    def _crear_tablas(self) -> None:
        """Crea tablas para persistencia de evaluaciones"""
        if not self.db_path:
            return
        
        # Tabla histórico de evaluaciones
        query1 = """
        CREATE TABLE IF NOT EXISTS evaluaciones_riesgos_otros (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            riesgo_id TEXT NOT NULL,
            trabajador_id TEXT,
            categoria TEXT,
            severidad_potencial TEXT,
            score_exposicion REAL,
            periodo_exposicion TEXT,
            controles_implementados TEXT,  -- JSON list
            fecha_evaluacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            acciones_recomendadas TEXT,     -- JSON list
            prioridad TEXT
        )
        """
        
        # Tabla alertas
        query2 = """
        CREATE TABLE IF NOT EXISTS alertas_riesgos_otros (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            riesgo_id TEXT NOT NULL,
            trabajador_id TEXT,
            tipo TEXT,
            severidad TEXT,
            descripcion TEXT,
            fecha_generacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            estado TEXT,
            acciones_tomadas TEXT  -- JSON list
        )
        """
        
        # Tabla métricas de riesgo
        query3 = """
        CREATE TABLE IF NOT EXISTS metricas_riesgos_otros (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            total_riesgos_evaluados INTEGER,
            riesgos_altos INTEGER,
            score_promedio REAL,
            alertas_generadas INTEGER
        )
        """
        
        try:
            from src.infrastructure.database import obtener_conexion
            conexion = obtener_conexion(self.db_path)
            conexion.execute(query1)
            conexion.execute(query2)
            conexion.execute(query3)
            conexion.commit()
            conexion.close()
            logger.debug("Tablas de other_risks creadas")
        except Exception as e:
            logger.error(f"Error creando tablas: {e}")
    
    def evaluar_exposicion(self, riesgo_id: str, trabajador_id: str,
                          horas_exposicion: float, controles: List[str] = None) -> EvaluacionRiesgo:
        """
        Evalúa la exposición de un trabajador a un riesgo específico.
        
        Args:
            riesgo_id: ID del riesgo (ej: 'AR01')
            trabajador_id: ID del trabajador
            horas_exposicion: Horas de exposición en el período
            controles: Controles implementados
        
        Returns:
            EvaluacionRiesgo con scoring y recomendaciones
        """
        riesgo = next((r for r in OTHER_RISKS_EXPANDIDO if r['id'] == riesgo_id), None)
        if not riesgo:
            logger.warning(f"Riesgo no encontrado: {riesgo_id}")
            return None
        
        # Calcular score de exposición (0-1)
        score_base = self._mapear_severidad_a_score(riesgo['severidad'])
        score_tiempo = min(horas_exposicion / 8.0, 1.0)  # Max 8h = 1.0
        
        # Aplicar factor de controles
        factor_controles = 1.0
        if controles:
            factor_controles = max(0.2, 1.0 - (len(controles) * 0.15))
        
        score_exposicion = (score_base * 0.5 + score_tiempo * 0.35 + (1 - factor_controles) * 0.15)
        
        # Determinar prioridad
        if score_exposicion >= 0.8:
            prioridad = "critica"
        elif score_exposicion >= 0.6:
            prioridad = "alta"
        elif score_exposicion >= 0.4:
            prioridad = "media"
        else:
            prioridad = "baja"
        
        # Generar recomendaciones
        recomendaciones = self._generar_recomendaciones(riesgo, score_exposicion, controles)
        
        evaluacion = EvaluacionRiesgo(
            riesgo_id=riesgo_id,
            riesgo_nombre=riesgo['riesgo'],
            trabajador_id=trabajador_id,
            categoria=riesgo['categoria'],
            severidad_potencial=riesgo['severidad'],
            score_exposicion=round(score_exposicion, 3),
            periodo_exposicion=f"{horas_exposicion}h",
            controles_implementados=controles or [],
            fecha_evaluacion=datetime.now().isoformat(),
            acciones_recomendadas=recomendaciones,
            prioridad=prioridad
        )
        
        # Guardar en BD
        self._guardar_evaluacion(evaluacion)
        
        # Generar alerta si prioridad es alta o crítica
        if prioridad in ['alta', 'critica']:
            self._generar_alerta_exposicion(evaluacion)
        
        logger.info(f"✅ Evaluación: {riesgo['riesgo']} = {prioridad.upper()} ({score_exposicion:.1%})")
        
        return evaluacion
    
    def _mapear_severidad_a_score(self, severidad: str) -> float:
        """Mapea severidad a score base (0-1)"""
        mapeo = {
            "Baja": 0.3,
            "Media": 0.6,
            "Alta": 0.9
        }
        return mapeo.get(severidad, 0.5)
    
    def _generar_recomendaciones(self, riesgo: Dict, score: float, controles: List[str]) -> List[str]:
        """Genera recomendaciones contextuales basadas en la evaluación"""
        recomendaciones = []
        
        # Recomendación base del riesgo
        recomendaciones.append(f"Implementar: {riesgo['medida']}")
        
        # Recomendaciones adicionales si score alto
        if score >= 0.7:
            recomendaciones.append("🚨 ALERTA: Alto nivel de exposición - Requiere acción inmediata")
            recomendaciones.append(f"Revisar cada {riesgo['periodo_revision']} o más frecuentemente")
            recomendaciones.append("Considerar rotación de tareas o reducción de exposición")
        
        if score >= 0.5 and not controles:
            recomendaciones.append("Implementar controles técnicos o administrativos")
        
        if score >= 0.6:
            recomendaciones.append("Capacitar al trabajador sobre este riesgo específico")
            recomendaciones.append("Realizar seguimiento médico ocupacional")
        
        return recomendaciones
    
    def _guardar_evaluacion(self, evaluacion: EvaluacionRiesgo) -> None:
        """Guarda evaluación en BD"""
        if not self.db_path:
            return
        
        try:
            from src.infrastructure.database import obtener_conexion
            
            query = """
            INSERT INTO evaluaciones_riesgos_otros
            (riesgo_id, trabajador_id, categoria, severidad_potencial, score_exposicion,
             periodo_exposicion, controles_implementados, acciones_recomendadas, prioridad)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            conexion = obtener_conexion(self.db_path)
            conexion.execute(query, (
                evaluacion.riesgo_id,
                evaluacion.trabajador_id,
                evaluacion.categoria,
                evaluacion.severidad_potencial,
                evaluacion.score_exposicion,
                evaluacion.periodo_exposicion,
                json.dumps(evaluacion.controles_implementados),
                json.dumps(evaluacion.acciones_recomendadas),
                evaluacion.prioridad
            ))
            conexion.commit()
            conexion.close()
        except Exception as e:
            logger.error(f"Error guardando evaluación: {e}")
    
    def _generar_alerta_exposicion(self, evaluacion: EvaluacionRiesgo) -> None:
        """Genera alerta si exposición es crítica"""
        if not self.db_path:
            return
        
        severidad = "roja" if evaluacion.prioridad == "critica" else "amarilla"
        tipo = "EXPOSICION_CRITICA" if evaluacion.prioridad == "critica" else "EXPOSICION_ALTA"
        
        descripcion = f"Exposición {evaluacion.prioridad.upper()} a {evaluacion.riesgo_nombre} (Score: {evaluacion.score_exposicion:.1%})"
        
        try:
            from src.infrastructure.database import obtener_conexion
            
            query = """
            INSERT INTO alertas_riesgos_otros
            (riesgo_id, trabajador_id, tipo, severidad, descripcion)
            VALUES (?, ?, ?, ?, ?)
            """
            
            conexion = obtener_conexion(self.db_path)
            conexion.execute(query, (
                evaluacion.riesgo_id,
                evaluacion.trabajador_id,
                tipo,
                severidad,
                descripcion
            ))
            conexion.commit()
            conexion.close()
            logger.warning(f"⚠️ Alerta generada: {tipo}")
        except Exception as e:
            logger.error(f"Error generando alerta: {e}")
    
    def obtener_riesgos_prioritarios(self, categoria: str = None) -> List[Dict]:
        """Obtiene riesgos ordenados por prioridad de exposición"""
        if categoria:
            riesgos = obtener_riesgos_por_categoria(categoria)
        else:
            riesgos = OTHER_RISKS_EXPANDIDO
        
        # Ordenar por severidad
        orden_severidad = {"Alta": 0, "Media": 1, "Baja": 2}
        riesgos_sorted = sorted(riesgos, 
                               key=lambda r: orden_severidad.get(r['severidad'], 3))
        
        return riesgos_sorted
    
    def generar_reporte_evaluaciones(self, trabajador_id: str = None) -> Dict:
        """Genera reporte de evaluaciones para trabajador o global"""
        if not self.db_path:
            return {}
        
        try:
            from src.infrastructure.database import obtener_dataframe
            
            if trabajador_id:
                query = f"SELECT * FROM evaluaciones_riesgos_otros WHERE trabajador_id = '{trabajador_id}' ORDER BY fecha_evaluacion DESC"
            else:
                query = "SELECT * FROM evaluaciones_riesgos_otros ORDER BY fecha_evaluacion DESC LIMIT 100"
            
            df = obtener_dataframe(self.db_path, query)
            
            if df.empty:
                return {"total": 0, "evaluaciones": []}
            
            # Análisis
            resumen = {
                "total": len(df),
                "por_prioridad": df['prioridad'].value_counts().to_dict(),
                "score_promedio": df['score_exposicion'].mean(),
                "categorias": df['categoria'].unique().tolist(),
                "evaluaciones": df.to_dict('records')
            }
            
            return resumen
        
        except Exception as e:
            logger.error(f"Error generando reporte: {e}")
            return {}
    
    def registrar_metricas(self, total_evaluadas: int, riesgos_altos: int, 
                          score_promedio: float, alertas: int) -> None:
        """Registra métricas de evaluación"""
        if not self.db_path:
            return
        
        try:
            from src.infrastructure.database import obtener_conexion
            
            query = """
            INSERT INTO metricas_riesgos_otros
            (total_riesgos_evaluados, riesgos_altos, score_promedio, alertas_generadas)
            VALUES (?, ?, ?, ?)
            """
            
            conexion = obtener_conexion(self.db_path)
            conexion.execute(query, (total_evaluadas, riesgos_altos, score_promedio, alertas))
            conexion.commit()
            conexion.close()
        except Exception as e:
            logger.error(f"Error registrando métricas: {e}")


# ============ SINGLETON ============

_engine_other_risks = None

def obtener_other_risks_engine(db_path: str = None) -> OtherRisksEngine:
    """Obtiene instancia singleton del OtherRisksEngine"""
    global _engine_other_risks
    if _engine_other_risks is None:
        _engine_other_risks = OtherRisksEngine(db_path)
    return _engine_other_risks


# Compatibilidad con versión anterior
OTHER_RISKS_BASE = OTHER_RISKS_EXPANDIDO
