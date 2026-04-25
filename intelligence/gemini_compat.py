"""
==========================================
🔄 GEMINI COMPATIBILITY LAYER
==========================================
Compatibilidad entre google-genai (nueva) y google-generativeai (antigua/deprecada)
Proporciona interfaz uniforme para ambas librerías
"""

import logging

logger = logging.getLogger(__name__)

# Variables globales para el módulo compatible
_genai = None
_library_type = None  # "genai" o "generativeai"


def initialize_gemini(api_key: str):
    """
    Inicializa la librería de Gemini (nueva o antigua, según disponibilidad)

    Args:
        api_key: La API Key de Google
    """
    global _genai, _library_type

    # Intentar con la nueva librería primero
    try:
        import google.genai as genai
        genai.configure(api_key=api_key)
        _genai = genai
        _library_type = "genai"
        logger.info("✅ Usando google.genai (nueva librería recomendada)")
        return
    except Exception as e:
        logger.debug(f"google.genai no disponible: {e}")

    # Fallback a la antigua
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        _genai = genai
        _library_type = "generativeai"
        logger.warning(
            "⚠️ Usando google-generativeai (deprecada). "
            "Se recomienda actualizar a: pip install google-genai"
        )
        return
    except Exception as e:
        logger.error(f"❌ No se pudo inicializar Gemini: {e}")
        raise ImportError(
            "Gemini no está disponible. Instala con: "
            "pip install google-genai (recomendado) o pip install google-generativeai"
        )


def create_model(model_name: str):
    """
    Crea un modelo Generativo compatible

    Args:
        model_name: Nombre del modelo (ej: "gemini-1.5-pro")

    Returns:
        Objeto de modelo compatible
    """
    if _genai is None:
        raise RuntimeError("Gemini no inicializado. Llama a initialize_gemini() primero.")

    if _library_type == "genai":
        # Nueva librería
        return GeminiModelWrapper_New(_genai, model_name)
    else:
        # Antigua librería
        return GeminiModelWrapper_Old(_genai, model_name)


class GeminiModelWrapper_Old:
    """Wrapper para google-generativeai (antigua)"""

    def __init__(self, genai, model_name: str):
        self.genai = genai
        self.model_name = model_name
        self.client = genai.GenerativeModel(model_name)

    def generate_content(self, prompt: str, stream: bool = False, **kwargs):
        """Genera contenido"""
        config = kwargs.pop("generation_config", None)
        return self.client.generate_content(
            prompt,
            generation_config=config,
            stream=stream,
            **kwargs,
        )


class GeminiModelWrapper_New:
    """Wrapper para google-genai (nueva)"""

    def __init__(self, genai, model_name: str):
        self.genai = genai
        self.model_name = model_name
        self.client = genai.Client()

    def generate_content(self, prompt: str, stream: bool = False, **kwargs):
        """Genera contenido con nueva API"""
        config = kwargs.pop("generation_config", None)

        if stream:
            return self.client.models.generate_content_stream(
                model=self.model_name,
                contents=prompt,
                config=config,
            )
        else:
            return self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=config,
            )


def is_available() -> bool:
    """Verifica si Gemini está disponible"""
    try:
        import google.genai
        return True
    except ImportError:
        try:
            import google.generativeai
            return True
        except ImportError:
            return False
