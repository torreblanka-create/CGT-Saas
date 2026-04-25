"""
==========================================
🔬 OCR ENGINE — v2.0 MEJORADO
==========================================
Motor de validación OCR de documentos PDF.

CARACTERÍSTICAS v2.0:
✅ Extracción de texto PDF
✅ Validación de contenido
✅ Detección de RUT/Patente
✅ Análisis de confianza
✅ Histórico de validaciones
✅ Integración BD
✅ Reporte de discrepancias
"""
import os
import re
import logging
from datetime import datetime
from typing import Dict, Optional, List
from dataclasses import dataclass

import pandas as pd

from src.infrastructure.database import ejecutar_query, obtener_dataframe, obtener_conexion

logger = logging.getLogger(__name__)


# ============ PATRONES ============

_RUT_PATTERN = re.compile(r'\b\d{1,2}[\.\s]?\d{3}[\.\s]?\d{3}[-]?[\dkK]\b')
_PATENTE_PATTERN = re.compile(r'\b[A-Z]{2,4}[\s.-]?\d{3,4}\b')


# ============ DATA MODELS ============

@dataclass
class ValidacionOCR:
    """Resultado de validación OCR"""
    id: str
    identificador: str
    nombre: str
    ruta_pdf: str
    score_confianza: float  # 0-100
    elementos_encontrados: List[str]
    elementos_faltantes: List[str]
    validacion_exitosa: bool
    fecha_validacion: str


class OCREngine:
    """Motor de validación OCR de documentos"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path
        self._crear_tablas()
        logger.info("OCREngine inicializado")
    
    def _crear_tablas(self) -> None:
        """Crea tablas para validaciones OCR"""
        if not self.db_path:
            return
        
        tables = [
            """
            CREATE TABLE IF NOT EXISTS validaciones_ocr (
                id TEXT PRIMARY KEY,
                identificador TEXT,
                nombre TEXT,
                ruta_pdf TEXT,
                score_confianza REAL,
                elementos_encontrados TEXT,
                elementos_faltantes TEXT,
                validacion_exitosa BOOLEAN,
                fecha_validacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        ]
        
        try:
            conexion = obtener_conexion(self.db_path)
            for query in tables:
                conexion.execute(query)
            conexion.commit()
            conexion.close()
            logger.debug("Tablas OCR creadas")
        except Exception as e:
            logger.error(f"Error creando tablas: {e}")


def _extraer_texto_pdf(pdf_path: str) -> str:
    """Extrae todo el texto de un PDF usando PyMuPDF."""
    try:
        import fitz
        doc = fitz.open(pdf_path)
        texto = ""
        for pag in doc:
            texto += pag.get_text("text") + "\n"
        doc.close()
        return texto
    except ImportError:
        return "__NOFITZ__"
    except Exception as e:
        return f"__ERROR__{str(e)}"


def _normalizar_rut(rut: str) -> str:
    """Quita puntos, guiones y espacios de un RUT para comparación."""
    return re.sub(r'[.\-\s]', '', str(rut)).upper()


def _calcular_confianza(texto: str, identificador: str, nombre: str) -> dict:
    """
    Calcula un puntaje de confianza (0–100) basado en cuántos
    elementos del registro se encuentran en el texto del documento.
    """
    score = 0
    evidencias = []

    texto_upper = texto.upper()
    id_norm = _normalizar_rut(identificador)

    # 1. Buscar identificador (RUT / Patente / Código)
    rutset = {_normalizar_rut(r.group()) for r in _RUT_PATTERN.finditer(texto)}
    if id_norm in rutset:
        score += 50
        evidencias.append(f"✅ Identificador '{identificador}' encontrado en el texto.")
    else:
        # Búsqueda directa (para patentes u otros ID)
        if id_norm in texto_upper.replace(" ", "").replace("-", "").replace(".", ""):
            score += 40
            evidencias.append(f"✅ ID '{identificador}' encontrado (búsqueda libre).")
        else:
            evidencias.append(f"❌ Identificador '{identificador}' NO encontrado en el documento.")

    # 2. Buscar nombre (al menos 2 palabras del nombre)
    palabras_nombre = [p for p in str(nombre).upper().split() if len(p) > 3]
    palabras_encontradas = sum(1 for p in palabras_nombre if p in texto_upper)

    if palabras_nombre:
        ratio = palabras_encontradas / len(palabras_nombre)
        puntaje_nombre = int(ratio * 40)
        score += puntaje_nombre
        if ratio >= 0.7:
            evidencias.append(f"✅ Nombre '{nombre}' coincide ({palabras_encontradas}/{len(palabras_nombre)} palabras).")
        else:
            evidencias.append(f"⚠️ Nombre parcial: {palabras_encontradas}/{len(palabras_nombre)} palabras de '{nombre}' encontradas.")

    # 3. Bonus: ¿Hay fecha en el documento?
    if re.search(r'\b20\d{2}\b', texto):
        score += 10
        evidencias.append("✅ Se detectó una fecha de vigencia en el documento.")

    return {
        "score": min(score, 100),
        "evidencias": evidencias
    }


def validar_documento_ocr(pdf_path: str, identificador: str, nombre: str) -> dict:
    """
    Función principal. Abre el PDF y valida si su contenido
    corresponde al registro esperado.

    Returns:
        dict con keys: valido (bool), confianza (0-100), razon (str), evidencias (list)
    """
    if not pdf_path or not os.path.exists(pdf_path):
        return {
            "valido": False,
            "confianza": 0,
            "razon": f"Archivo no encontrado en la ruta: {pdf_path}",
            "evidencias": []
        }

    texto = _extraer_texto_pdf(pdf_path)

    if texto == "__NOFITZ__":
        return {
            "valido": False,
            "confianza": 0,
            "razon": "Módulo PyMuPDF no instalado. Ejecute: pip install PyMuPDF",
            "evidencias": []
        }

    if texto.startswith("__ERROR__"):
        return {
            "valido": False,
            "confianza": 0,
            "razon": f"Error al leer el PDF: {texto[9:]}",
            "evidencias": []
        }

    if len(texto.strip()) < 50:
        return {
            "valido": False,
            "confianza": 10,
            "razon": "El PDF parece ser una imagen escaneada sin texto extraíble (OCR nativo no disponible).",
            "evidencias": ["⚠️ Texto extraído insuficiente (<50 caracteres)."]
        }

    resultado = _calcular_confianza(texto, identificador, nombre)
    score = resultado["score"]

    return {
        "valido": score >= 50,
        "confianza": score,
        "razon": "Documento validado con éxito." if score >= 50 else f"Confianza insuficiente ({score}%). El documento puede no corresponder al registro.",
        "evidencias": resultado["evidencias"],
        "chars_extraidos": len(texto)
    }


def validar_y_registrar(DB_PATH: str, registro_id: int, empresa_id: int = 0, contrato_id: int = 0) -> dict:
    """
    Obtiene el registro de la BD, valida el PDF y guarda el resultado
    en la tabla ultron_ocr_validaciones.
    """
    df = obtener_dataframe(DB_PATH,
        "SELECT identificador, nombre, path FROM registros WHERE id = ?",
        (registro_id,)
    )
    if df.empty:
        return {"valido": False, "confianza": 0, "razon": "Registro no encontrado en la BD."}

    row = df.iloc[0]
    resultado = validar_documento_ocr(row['path'], row['identificador'], row['nombre'])

    # Persistir resultado
    ejecutar_query(DB_PATH, """
        INSERT INTO ultron_ocr_validaciones
            (identificador, path_analizado, es_valido, confianza, razon, empresa_id, contrato_id)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        row['identificador'],
        row['path'],
        1 if resultado['valido'] else 0,
        resultado['confianza'],
        resultado['razon'],
        empresa_id,
        contrato_id
    ), commit=True)

    return resultado


def obtener_historial_ocr(DB_PATH: str, empresa_id: int = 0) -> 'pd.DataFrame':
    """Retorna el historial de validaciones OCR."""
    query = "SELECT * FROM ultron_ocr_validaciones WHERE 1=1"
    params = []
    if empresa_id > 0:
        query += " AND empresa_id = ?"
        params.append(empresa_id)
    query += " ORDER BY fecha DESC LIMIT 100"
    return obtener_dataframe(DB_PATH, query, tuple(params))
