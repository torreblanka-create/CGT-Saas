"""
==========================================
🔴 OPENAI PROVIDER (ChatGPT)
==========================================
Adaptador para OpenAI API (ChatGPT)
"""

import logging
from typing import List

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

from .base import BaseProvider, ProviderConfig

logger = logging.getLogger(__name__)


class OpenAIProvider(BaseProvider):
    """Proveedor para OpenAI / ChatGPT"""

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self.client = None
        self._initialize_client()

    def _validate_config(self) -> None:
        """Valida configuración de OpenAI"""
        if not OPENAI_AVAILABLE:
            raise ImportError("openai no está instalado. Instálalo con: pip install openai")
        if not self.config.api_key:
            raise ValueError("OpenAI: API KEY requerida")
        if not self.config.model_name:
            raise ValueError("OpenAI: Nombre del modelo requerido")

    def _initialize_client(self) -> None:
        """Inicializa cliente de OpenAI"""
        try:
            self.client = OpenAI(api_key=self.config.api_key)
            logger.info(f"OpenAI Provider inicializado con modelo: {self.config.model_name}")
        except Exception as e:
            logger.error(f"Error inicializando OpenAI: {e}")
            raise

    def generate_response(self, prompt: str, **kwargs) -> str:
        """Genera respuesta con OpenAI"""
        try:
            messages = [{"role": "user", "content": prompt}]

            response = self.client.chat.completions.create(
                model=self.config.model_name,
                messages=messages,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                top_p=self.config.top_p,
                **self.config.extra_params,
                **kwargs,
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Error generando respuesta con OpenAI: {e}")
            raise

    def generate_response_stream(self, prompt: str, **kwargs):
        """Genera respuesta en streaming con OpenAI"""
        try:
            messages = [{"role": "user", "content": prompt}]

            stream = self.client.chat.completions.create(
                model=self.config.model_name,
                messages=messages,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                top_p=self.config.top_p,
                stream=True,
                **self.config.extra_params,
                **kwargs,
            )

            for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            logger.error(f"Error en streaming de OpenAI: {e}")
            raise

    def get_available_models(self) -> List[str]:
        """Retorna modelos disponibles de OpenAI"""
        return [
            "gpt-4-turbo",
            "gpt-4",
            "gpt-3.5-turbo",
            "gpt-4o",
            "gpt-4o-mini",
        ]

    def validate_connection(self) -> bool:
        """Valida conexión con OpenAI"""
        try:
            response = self.client.chat.completions.create(
                model=self.config.model_name,
                messages=[{"role": "user", "content": "test"}],
                max_tokens=10,
            )
            return response.choices[0].message.content is not None
        except Exception as e:
            logger.error(f"Error validando conexión con OpenAI: {e}")
            return False
