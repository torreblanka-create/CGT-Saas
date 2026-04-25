"""
==========================================
🎓 COACHING ENGINE — v2.0 MEJORADO
==========================================
Motor de coaching personalizado de seguridad.

CARACTERÍSTICAS v2.0:
✅ Base de conocimiento estructurada
✅ Consejos contextualizados
✅ Normativas asociadas
✅ Histórico de coaching
✅ Análisis de tendencias
✅ Integración BD
✅ Recomendaciones inteligentes
"""
import logging
import random
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass

from src.infrastructure.database import obtener_dataframe, obtener_conexion

logger = logging.getLogger(__name__)


# ============ DATA MODELS ============

@dataclass
class ConsejoCaching:
    """Consejo personalizado de seguridad"""
    id: str
    categoria: str
    contenido: str
    norma_asociada: str
    nivel_severidad: str  # Preventivo, Normativo, Crítico
    contexto_aplicacion: str


@dataclass
class SesionCoaching:
    """Sesión de coaching registrada"""
    id: str
    trabajador_id: str
    categoria: str
    consejo_id: str
    fecha_sesion: str
    retroalimentacion: str


class CoachingEngine:
    """Motor de coaching personalizado"""
    
    # Base de conocimiento estática curada
    COACHING_DB = {
        "Personal": [
            {
                "tip": "Programa las renovaciones de licencias con al menos 45 días de anticipación.",
                "norma": "DS 132 Art. 256 / Reglamento Interno",
                "nivel": "Preventivo"
            },
            {
                "tip": "Los exámenes pre-ocupacionales son obligatorios antes del ingreso.",
                "norma": "Ley 16.744 / DS 44 Art. 18",
                "nivel": "Crítico"
            },
            {
                "tip": "La IRL debe actualizarse cuando cambian las condiciones del trabajo.",
                "norma": "Art. 21 Ley 16.744",
                "nivel": "Crítico"
            }
        ],
        "Maquinaria": [
            {
                "tip": "El SOAP vencido implica circulación ilegal.",
                "norma": "Ley 18.490",
                "nivel": "Crítico"
            },
            {
                "tip": "La mantención preventiva debe documentarse con fecha y firma.",
                "norma": "DS 132 Art. 265",
                "nivel": "Preventivo"
            },
            {
                "tip": "Después de una falla de confiabilidad, el equipo debe tener una revisión técnica extraordinaria antes de reiniciar operaciones.",
                "norma": "DS 132 Art. 267",
                "nivel": "Crítico"
            }
        ],
        "Elementos de izaje": [
            {
                "tip": "Los certificados de operatividad de elementos de izaje son trimestrales. No esperes al último día: programa con 3 semanas de margen.",
                "norma": "DS 132 Art. 275",
                "nivel": "Crítico"
            },
            {
                "tip": "Nunca uses un elemento de izaje sin identificación de capacidad de carga máxima visible y legible.",
                "norma": "NCh 2369 / DS 132",
                "nivel": "Crítico"
            },
            {
                "tip": "Inspecciona visualmente los grilletes y eslingas antes de cada izaje. Documenta y rechaza todo elemento con deformación o corrosión.",
                "norma": "DS 132 Art. 278",
                "nivel": "Preventivo"
            },
            {
                "tip": "El plan de izaje debe estar aprobado por un Rigger certificado antes de iniciar cualquier operación crítica.",
                "norma": "DS 132 Art. 279",
                "nivel": "Crítico"
            }
        ],
        "Instrumentos y Metrología": [
            {
                "tip": "Un instrumento descalibrado no solo genera datos inválidos: puede provocar accidentes graves. Nunca uses equipos fuera de su fecha de calibración.",
                "norma": "NCh-ISO 9001:2015 / DS 594",
                "nivel": "Crítico"
            },
            {
                "tip": "Los certificados de calibración deben provenir de laboratorios acreditados por el INN. Verifica el número de acreditación en cada certificado.",
                "norma": "NCh-ISO/IEC 17025",
                "nivel": "Normativo"
            },
            {
                "tip": "Si un instrumento falla, retíralo inmediatamente del servicio y etiquétalo como 'FUERA DE SERVICIO'. No lo dejes disponible sin aviso.",
                "norma": "ISO 9001:2015 Cláusula 7.1.5",
                "nivel": "Preventivo"
            }
        ],
        "Sistemas de Emergencia": [
            {
                "tip": "Los extintores deben inspeccionarse mensualmente (inspección visual) y tener revisión técnica anual con registro sellado.",
                "norma": "DS 594 Art. 45 / NCh 1430",
                "nivel": "Crítico"
            },
            {
                "tip": "Un extintor con el seguro roto o el manómetro en rojo debe reemplazarse de inmediato. No esperes la revisión anual.",
                "norma": "DS 594 Art. 46",
                "nivel": "Crítico"
            },
            {
                "tip": "Los equipos de respiración autónoma (SCBA) requieren prueba de presión hidrostática según fabricante (generalmente cada 5 años).",
                "norma": "NFPA 1852 / DS 132",
                "nivel": "Normativo"
            }
        ],
        "ART": [
            {
                "tip": "Una ART firmada antes de iniciar la tarea es tu primera línea de defensa legal. Sin ella, el accidente puede no estar cubierto.",
                "norma": "DS 132 Art. 37 / Ley 16.744",
                "nivel": "Crítico"
            },
            {
                "tip": "La ART debe identificar todos los controles de cada peligro, no solo enumerarlos. 'Usar casco' sin especificar el riesgo que mitiga es inválido.",
                "norma": "ISO 45001:2018 Cláusula 8.1.2",
                "nivel": "Preventivo"
            },
            {
                "tip": "Si cambian las condiciones de trabajo durante la tarea, detén la actividad y emite una nueva ART. La original ya no aplica.",
                "norma": "DS 132 Art. 38",
                "nivel": "Crítico"
            },
            {
                "tip": "El supervisor de turno siempre debe firmar la ART. Su firma certifica que revisó y aprobó los controles propuestos.",
                "norma": "DS 132 / Procedimiento Interno",
                "nivel": "Normativo"
            }
        ],
        "General": [
            {
                "tip": "El principio de 'Gestión del Cambio' exige que cualquier modificación al proceso productivo active una nueva evaluación de riesgos.",
                "norma": "ISO 45001:2018 Cláusula 8.1.3",
                "nivel": "Normativo"
            },
            {
                "tip": "Toda no conformidad detectada es una oportunidad de mejora. Regístrala en el sistema antes de 24 horas para asegurar trazabilidad.",
                "norma": "ISO 9001:2015 Cláusula 10.2",
                "nivel": "Preventivo"
            },
            {
                "tip": "Las inspecciones planificadas deben tener evidencia fotográfica y estar firmadas por el inspector. Sin evidencia, no ocurrieron.",
                "norma": "ISO 45001:2018 Cláusula 9.1.2",
                "nivel": "Preventivo"
            },
            {
                "tip": "El liderazgo es el principal factor de cultura de seguridad. Si el supervisor no cumple, el equipo tampoco lo hará.",
                "norma": "ISO 45001:2018 Cláusula 5.1",
                "nivel": "Estratégico"
            }
        ]
    }
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path
        self._crear_tablas()
        logger.info("CoachingEngine inicializado")
    
    def _crear_tablas(self) -> None:
        """Crea tablas para coaching"""
        if not self.db_path:
            return
        
        tables = [
            """
            CREATE TABLE IF NOT EXISTS sesiones_coaching (
                id TEXT PRIMARY KEY,
                trabajador_id TEXT,
                categoria TEXT,
                consejo_id TEXT,
                fecha_sesion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                retroalimentacion TEXT,
                empresa_id TEXT
            )
            """
        ]
        
        try:
            conexion = obtener_conexion(self.db_path)
            for query in tables:
                conexion.execute(query)
            conexion.commit()
            conexion.close()
            logger.debug("Tablas de coaching creadas")
        except Exception as e:
            logger.error(f"Error creando tablas: {e}")
    
    def obtener_consejo_aleatorio(self, categoria: str = None) -> Dict:
        """Obtiene un consejo aleatorio de la base de conocimiento"""
        if categoria and categoria in self.COACHING_DB:
            consejos = self.COACHING_DB[categoria]
        else:
            # Si no hay categoría, combinar todos los consejos
            consejos = []
            for cat in self.COACHING_DB.values():
                consejos.extend(cat)
        
        if consejos:
            return random.choice(consejos)
        return {"tip": "Consulta con tu supervisor", "norma": "Interna", "nivel": "Preventivo"}


# ============ COACHING_DB GLOBAL (Para funciones independientes) ============
COACHING_DB = {
    "Personal": [
        {
            "tip": "Programa las renovaciones de licencias con al menos 45 días de anticipación.",
            "norma": "DS 132 Art. 256 / Reglamento Interno",
            "nivel": "Preventivo"
        },
        {
            "tip": "Los exámenes pre-ocupacionales son obligatorios antes del ingreso.",
            "norma": "Ley 16.744 / DS 44 Art. 18",
            "nivel": "Crítico"
        },
        {
            "tip": "La IRL debe actualizarse cuando cambian las condiciones del trabajo.",
            "norma": "Art. 21 Ley 16.744",
            "nivel": "Crítico"
        }
    ],
    "Maquinaria": [
        {
            "tip": "El SOAP vencido implica circulación ilegal.",
            "norma": "Ley 18.490",
            "nivel": "Crítico"
        },
        {
            "tip": "La mantención preventiva debe documentarse con fecha y firma.",
            "norma": "DS 132 Art. 265",
            "nivel": "Preventivo"
        }
    ],
    "General": [
        {
            "tip": "El principio de 'Gestión del Cambio' exige que cualquier modificación al proceso productivo active una nueva evaluación de riesgos.",
            "norma": "ISO 45001:2018 Cláusula 8.1.3",
            "nivel": "Normativo"
        },
        {
            "tip": "Toda no conformidad detectada es una oportunidad de mejora. Regístrala en el sistema antes de 24 horas para asegurar trazabilidad.",
            "norma": "ISO 9001:2015 Cláusula 10.2",
            "nivel": "Preventivo"
        }
    ]
}


def _analizar_fallas_usuario(DB_PATH: str, empresa_id: int = 0, contrato_id: int = 0) -> dict:
    """
    Analiza la BD para detectar las categorías con más fallas.
    Retorna un dict de categorías ordenadas por cantidad de problemas.
    """
    from datetime import timedelta

    import pandas as pd

    hoy = datetime.now().date()
    limite_alerta = hoy + timedelta(days=15)

    query = """
        SELECT categoria, cuenta
        FROM (
            SELECT categoria, COUNT(*) as cuenta
            FROM registros
            WHERE (fecha_vencimiento <= ? OR fecha_vencimiento IS NULL)
    """
    params = [str(limite_alerta)]
    if empresa_id > 0:
        query += " AND empresa_id = ? "
        params.append(empresa_id)
    if contrato_id > 0:
        query += " AND contrato_id = ? "
        params.append(contrato_id)
    query += " GROUP BY categoria ORDER BY cuenta DESC LIMIT 5)"

    df = obtener_dataframe(DB_PATH, query, tuple(params))

    if df.empty:
        return {}

    return dict(zip(df['categoria'], df['cuenta']))


def generar_coaching_personalizado(DB_PATH: str, empresa_id: int = 0, contrato_id: int = 0,
                                    api_key: str = "", n_consejos: int = 3) -> dict:
    """
    Genera N consejos de seguridad personalizados basados en el historial de fallas.

    Returns:
        dict con: consejos (list), contexto (str), categoria_critica (str)
    """
    fallas = _analizar_fallas_usuario(DB_PATH, empresa_id, contrato_id)
    categoria_critica = list(fallas.keys())[0] if fallas else "General"
    n_fallas_critica = fallas.get(categoria_critica, 0)

    # Determinar pools de tips a usar (prioridad: categoría crítica → general)
    pool_tips = []

    for cat, n in fallas.items():
        cat_key = cat
        # Mapeo de nombres de BD a claves del COACHING_DB
        for key in COACHING_DB.keys():
            if key.lower() in cat.lower() or cat.lower() in key.lower():
                cat_key = key
                break
        pool_tips.extend(COACHING_DB.get(cat_key, []))

    # Siempre añadir tips generales
    pool_tips.extend(COACHING_DB.get("General", []))

    # Si no hay datos de fallas, tips aleatorios mixtos
    if not pool_tips:
        for tips in COACHING_DB.values():
            pool_tips.extend(tips)

    # Deduplificar y seleccionar aleatoriamente
    seen = set()
    unique_tips = []
    for t in pool_tips:
        if t['tip'] not in seen:
            seen.add(t['tip'])
            unique_tips.append(t)

    random.shuffle(unique_tips)
    consejos_seleccionados = unique_tips[:n_consejos]

    # Contexto narrativo
    if fallas:
        contexto = (
            f"He analizado tu gestión documental y detecté que la categoría **{categoria_critica}** "
            f"presenta **{n_fallas_critica} documentos** vencidos o próximos a vencer. "
            f"Basándome en ese patrón, aquí tienes mis recomendaciones prioritarias:"
        )
    else:
        contexto = (
            "No detecté fallas críticas en tu gestión. ¡Excelente trabajo! "
            "Sin embargo, aquí tienes algunos consejos para mantener ese nivel de excelencia:"
        )

    # Si hay API Key, enriquecer con LLM
    respuesta_ia = None
    if api_key and str(api_key).strip():
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key.strip())
            model = genai.GenerativeModel('gemini-1.5-flash')

            tips_texto = "\n".join([f"- {t['tip']} (Norma: {t['norma']})" for t in consejos_seleccionados])
            fallas_texto = "\n".join([f"- {k}: {v} documentos con problemas" for k, v in fallas.items()]) if fallas else "Sin fallas detectadas"

            prompt = f"""
Eres Ultron, el asesor experto en Seguridad y Salud Ocupacional de CGT.pro.
El administrador tiene la siguiente situación de gestión:

FALLAS DETECTADAS:
{fallas_texto}

CONSEJOS BASE SELECCIONADOS:
{tips_texto}

Con base en el análisis anterior, genera exactamente 3 consejos breves, directos y accionables 
para mejorar la gestión de seguridad. Usa formato markdown con negritas. 
Cada consejo debe mencionar la norma aplicable y tener máximo 2 oraciones.
Responde solo los 3 consejos, sin introducción.
"""
            response = model.generate_content(prompt)
            respuesta_ia = response.text
        except Exception:
            respuesta_ia = None

    return {
        "consejos": consejos_seleccionados,
        "contexto": contexto,
        "categoria_critica": categoria_critica,
        "n_fallas": n_fallas_critica,
        "fallas_detectadas": fallas,
        "respuesta_ia": respuesta_ia
    }
