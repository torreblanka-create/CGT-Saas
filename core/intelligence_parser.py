import json
import os
import logging

import pandas as pd

logger = logging.getLogger(__name__)

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

# Intenta usar nueva librería, fallback a antigua
genai = None
try:
    import google.genai as genai
except ImportError:
    try:
        import google.generativeai as genai
    except ImportError:
        genai = None

def extract_text_from_pdf(file_obj):
    """Extrae texto de un objeto de archivo PDF."""
    if not fitz:
        return "Error: PyMuPDF no instalado."
    try:
        doc = fitz.open(stream=file_obj.read(), filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        return text
    except Exception as e:
        return f"Error leyendo PDF: {str(e)}"

def extract_text_from_excel(file_obj):
    """Extrae texto de un objeto de archivo Excel."""
    try:
        df = pd.read_excel(file_obj)
        return df.to_string()
    except Exception as e:
        return f"Error leyendo Excel: {str(e)}"

def parse_incident_with_gemini(text, api_key):
    """
    Usa Gemini para extraer datos estructurados de un reporte de incidente.
    """
    if not genai:
        return {"error": "Librería google-generativeai no instalada."}
    if not api_key:
        return {"error": "API Key de Gemini no configurada."}

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')

        prompt = f"""
        Eres un asistente experto en seguridad industrial (HSE). 
        Analiza el siguiente texto extraído de un reporte de incidente y extrae la información en formato JSON.
        
        IMPORTANTE: Responde ÚNICAMENTE con el objeto JSON, sin texto explicativo.
        
        Estructura esperada:
        {{
            "folio": "texto",
            "fecha": "YYYY-MM-DD",
            "hora": "HH:MM",
            "tipo_evento": "Selecciona uno de: STP, CTP, Primera Atención, Trayecto, Cuasi Accidente, Hallazgo, Falla Operacional, Daño Material, Daño Ambiental",
            "riesgo_critico": "Nombre del riesgo crítico (ej: Vehículos, Energía Eléctrica, etc.)",
            "control_fallido": "Breve descripción del control que falló",
            "reportante": "Nombre de la persona que reporta",
            "afectado": "Nombre de la persona involucrada",
            "que_ocurrio": "Descripción de los hechos (sin nombres)",
            "porque_ocurrio": "Análisis preliminar de causas",
            "acciones": ["acción 1", "acción 2", "acción 3"],
            "clasificacion": "Uno de: BP, L4, L3, L2, L1"
        }}

        TEXTO A ANALIZAR:
        \"\"\"
        {text[:30000]}
        \"\"\"
        """

        response = model.generate_content(prompt)
        # Limpiar respuesta por si incluye ```json ... ```
        raw_text = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(raw_text)
    except Exception as e:
        return {"error": f"Error en procesamiento IA: {str(e)}"}
