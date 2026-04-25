"""
==========================================
🧠 AI ENGINE — Motor unificado de IA
==========================================
Interfaz simplificada para usar cualquier proveedor de IA
"""

import logging
from typing import Optional, Dict, Any

from intelligence.providers import (
    create_provider,
    BaseProvider,
    ProviderConfig,
)

logger = logging.getLogger(__name__)


class AIEngine:
    """
    Motor unificado de IA que simplifica el uso de múltiples proveedores.

    Proporciona una interfaz única para generar respuestas usando cualquier proveedor.
    """

    def __init__(self, config_dict: Dict[str, Any]):
        """
        Inicializa el motor de IA con una configuración

        Args:
            config_dict: Diccionario con la configuración
                - api_provider: Nombre del proveedor
                - api_key: API KEY del proveedor
                - model_name: Nombre del modelo
                - temperature: Temperatura
                - max_output_tokens: Máximo de tokens
                - top_p: Top P (opcional)
        """
        self.config_dict = config_dict
        self.provider: Optional[BaseProvider] = None
        self._initialize()

    def _initialize(self) -> None:
        """Inicializa el proveedor"""
        try:
            config = ProviderConfig(
                api_key=self.config_dict.get("api_key", ""),
                model_name=self.config_dict.get("model_name", ""),
                temperature=float(self.config_dict.get("temperature", 0.7)),
                max_tokens=int(self.config_dict.get("max_output_tokens", 4096)),
                top_p=float(self.config_dict.get("top_p", 1.0)),
            )

            provider_name = self.config_dict.get("api_provider", "Google Gemini")
            self.provider = create_provider(provider_name, config)
            logger.info(f"AIEngine inicializado con {provider_name}")
        except Exception as e:
            logger.error(f"Error inicializando AIEngine: {e}")
            raise

    def generate(self, prompt: str, **kwargs) -> str:
        """
        Genera una respuesta

        Args:
            prompt: El texto del prompt
            **kwargs: Parámetros adicionales

        Returns:
            La respuesta generada
        """
        if not self.provider:
            raise RuntimeError("Motor de IA no inicializado")

        try:
            return self.provider.generate_response(prompt, **kwargs)
        except Exception as e:
            logger.error(f"Error generando respuesta: {e}")
            raise

    def generate_stream(self, prompt: str, **kwargs):
        """
        Genera una respuesta en streaming

        Args:
            prompt: El texto del prompt
            **kwargs: Parámetros adicionales

        Yields:
            Fragmentos de la respuesta
        """
        if not self.provider:
            raise RuntimeError("Motor de IA no inicializado")

        try:
            for chunk in self.provider.generate_response_stream(prompt, **kwargs):
                yield chunk
        except Exception as e:
            logger.error(f"Error generando respuesta en streaming: {e}")
            raise

    def validate(self) -> bool:
        """Valida que el motor esté funcionando correctamente"""
        if not self.provider:
            return False
        return self.provider.validate_connection()

    def get_info(self) -> Dict[str, str]:
        """Retorna información del motor"""
        if not self.provider:
            return {"status": "no_inicializado"}
        return self.provider.get_provider_info()


class AIEngineFactory:
    """Factory para crear motores de IA desde configuración"""

    @staticmethod
    def create_from_db_config(config_dict: Dict[str, Any]) -> AIEngine:
        """
        Crea un motor de IA desde una configuración de base de datos

        Args:
            config_dict: Configuración desde obtener_config()

        Returns:
            Instancia de AIEngine lista para usar
        """
        return AIEngine(config_dict)

    @staticmethod
    def create_default() -> AIEngine:
        """Crea un motor con configuración por defecto"""
        default_config = {
            "api_provider": "Google Gemini",
            "api_key": "",
            "model_name": "gemini-1.5-pro",
            "temperature": 0.7,
            "max_output_tokens": 4096,
            "top_p": 1.0,
        }
        return AIEngine(default_config)
