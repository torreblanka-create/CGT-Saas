"""
==========================================
💎 GOOGLE GEMINI PROVIDER
==========================================
Adaptador para Google Gemini API
"""

import logging
from typing import List, Dict, Any

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

from .base import BaseProvider, ProviderConfig

logger = logging.getLogger(__name__)


class GeminiProvider(BaseProvider):
    """Proveedor para Google Gemini"""

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self.client = None
        self._initialize_client()

    def _validate_config(self) -> None:
        """Valida configuración de Gemini"""
        if not GEMINI_AVAILABLE:
            raise ImportError("google-generativeai no está instalado. Instálalo con: pip install google-generativeai")
        if not self.config.api_key:
            raise ValueError("Gemini: API KEY requerida")
        if not self.config.model_name:
            raise ValueError("Gemini: Nombre del modelo requerido")

    def _initialize_client(self) -> None:
        """Inicializa cliente de Gemini"""
        try:
            genai.configure(api_key=self.config.api_key)
            self.client = genai.GenerativeModel(self.config.model_name)
            logger.info(f"Gemini Provider inicializado con modelo: {self.config.model_name}")
        except Exception as e:
            logger.error(f"Error inicializando Gemini: {e}")
            raise

    def generate_response(self, prompt: str, **kwargs) -> str:
        """Genera respuesta con Gemini"""
        try:
            generation_config = {
                "temperature": self.config.temperature,
                "top_p": self.config.top_p,
                "max_output_tokens": self.config.max_tokens,
            }
            generation_config.update(self.config.extra_params)
            generation_config.update(kwargs)

            response = self.client.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(**generation_config),
            )
            return response.text
        except Exception as e:
            logger.error(f"Error generando respuesta con Gemini: {e}")
            raise

    def generate_response_stream(self, prompt: str, **kwargs):
        """Genera respuesta en streaming con Gemini"""
        try:
            generation_config = {
                "temperature": self.config.temperature,
                "top_p": self.config.top_p,
                "max_output_tokens": self.config.max_tokens,
            }
            generation_config.update(self.config.extra_params)
            generation_config.update(kwargs)

            response = self.client.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(**generation_config),
                stream=True,
            )

            for chunk in response:
                if chunk.text:
                    yield chunk.text
        except Exception as e:
            logger.error(f"Error en streaming de Gemini: {e}")
            raise

    def get_available_models(self) -> List[str]:
        """Retorna modelos disponibles de Gemini"""
        return [
            "gemini-2.0-flash",
            "gemini-2.0-flash-exp",
            "gemini-1.5-pro",
            "gemini-1.5-flash",
            "gemini-1.5-pro-vision",
            "gemini-1.5-flash-vision",
        ]

    def validate_connection(self) -> bool:
        """Valida conexión con Gemini"""
        try:
            response = self.client.generate_content("test")
            return response.text is not None
        except Exception as e:
            logger.error(f"Error validando conexión con Gemini: {e}")
            return False
