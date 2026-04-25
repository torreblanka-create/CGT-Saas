"""
==========================================
🤖 ANTHROPIC PROVIDER (Claude)
==========================================
Adaptador para Anthropic API (Claude)
"""

import logging
from typing import List

try:
    from anthropic import Anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

from .base import BaseProvider, ProviderConfig

logger = logging.getLogger(__name__)


class AnthropicProvider(BaseProvider):
    """Proveedor para Anthropic / Claude"""

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self.client = None
        self._initialize_client()

    def _validate_config(self) -> None:
        """Valida configuración de Anthropic"""
        if not ANTHROPIC_AVAILABLE:
            raise ImportError("anthropic no está instalado. Instálalo con: pip install anthropic")
        if not self.config.api_key:
            raise ValueError("Anthropic: API KEY requerida")
        if not self.config.model_name:
            raise ValueError("Anthropic: Nombre del modelo requerido")

    def _initialize_client(self) -> None:
        """Inicializa cliente de Anthropic"""
        try:
            self.client = Anthropic(api_key=self.config.api_key)
            logger.info(f"Anthropic Provider inicializado con modelo: {self.config.model_name}")
        except Exception as e:
            logger.error(f"Error inicializando Anthropic: {e}")
            raise

    def generate_response(self, prompt: str, **kwargs) -> str:
        """Genera respuesta con Anthropic/Claude"""
        try:
            message = self.client.messages.create(
                model=self.config.model_name,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                messages=[{"role": "user", "content": prompt}],
                **self.config.extra_params,
                **kwargs,
            )
            return message.content[0].text
        except Exception as e:
            logger.error(f"Error generando respuesta con Anthropic: {e}")
            raise

    def generate_response_stream(self, prompt: str, **kwargs):
        """Genera respuesta en streaming con Anthropic"""
        try:
            with self.client.messages.stream(
                model=self.config.model_name,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                messages=[{"role": "user", "content": prompt}],
                **self.config.extra_params,
                **kwargs,
            ) as stream:
                for text in stream.text_stream:
                    yield text
        except Exception as e:
            logger.error(f"Error en streaming de Anthropic: {e}")
            raise

    def get_available_models(self) -> List[str]:
        """Retorna modelos disponibles de Anthropic"""
        return [
            "claude-opus-4-1",
            "claude-opus-4",
            "claude-sonnet-4-20250514",
            "claude-sonnet-4",
            "claude-haiku-3",
            "claude-3-5-sonnet-20241022",
            "claude-3-5-haiku-20241022",
        ]

    def validate_connection(self) -> bool:
        """Valida conexión con Anthropic"""
        try:
            message = self.client.messages.create(
                model=self.config.model_name,
                max_tokens=10,
                messages=[{"role": "user", "content": "test"}],
            )
            return message.content[0].text is not None
        except Exception as e:
            logger.error(f"Error validando conexión con Anthropic: {e}")
            return False
