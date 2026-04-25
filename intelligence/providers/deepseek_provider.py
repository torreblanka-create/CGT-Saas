"""
==========================================
🌊 DEEPSEEK PROVIDER
==========================================
Adaptador para DeepSeek API
"""

import logging
from typing import List

try:
    from openai import OpenAI
    DEEPSEEK_AVAILABLE = True
except ImportError:
    DEEPSEEK_AVAILABLE = False

from .base import BaseProvider, ProviderConfig

logger = logging.getLogger(__name__)


class DeepseekProvider(BaseProvider):
    """Proveedor para DeepSeek (usa compatible OpenAI API)"""

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self.client = None
        self._initialize_client()

    def _validate_config(self) -> None:
        """Valida configuración de DeepSeek"""
        if not DEEPSEEK_AVAILABLE:
            raise ImportError("openai no está instalado. Instálalo con: pip install openai")
        if not self.config.api_key:
            raise ValueError("DeepSeek: API KEY requerida")
        if not self.config.model_name:
            raise ValueError("DeepSeek: Nombre del modelo requerido")

    def _initialize_client(self) -> None:
        """Inicializa cliente de DeepSeek"""
        try:
            self.client = OpenAI(
                api_key=self.config.api_key,
                base_url="https://api.deepseek.com",
            )
            logger.info(f"DeepSeek Provider inicializado con modelo: {self.config.model_name}")
        except Exception as e:
            logger.error(f"Error inicializando DeepSeek: {e}")
            raise

    def generate_response(self, prompt: str, **kwargs) -> str:
        """Genera respuesta con DeepSeek"""
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
            logger.error(f"Error generando respuesta con DeepSeek: {e}")
            raise

    def generate_response_stream(self, prompt: str, **kwargs):
        """Genera respuesta en streaming con DeepSeek"""
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
            logger.error(f"Error en streaming de DeepSeek: {e}")
            raise

    def get_available_models(self) -> List[str]:
        """Retorna modelos disponibles de DeepSeek"""
        return [
            "deepseek-chat",
            "deepseek-coder",
        ]

    def validate_connection(self) -> bool:
        """Valida conexión con DeepSeek"""
        try:
            response = self.client.chat.completions.create(
                model=self.config.model_name,
                messages=[{"role": "user", "content": "test"}],
                max_tokens=10,
            )
            return response.choices[0].message.content is not None
        except Exception as e:
            logger.error(f"Error validando conexión con DeepSeek: {e}")
            return False
