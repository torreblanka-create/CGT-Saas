"""
==========================================
🔌 PROVIDERS MODULE — Factory de proveedores de IA
==========================================
"""

from .base import BaseProvider, ProviderConfig
from .gemini_provider import GeminiProvider
from .openai_provider import OpenAIProvider
from .anthropic_provider import AnthropicProvider
from .deepseek_provider import DeepseekProvider
from .ollama_provider import OllamaProvider

import logging

logger = logging.getLogger(__name__)


PROVIDER_REGISTRY = {
    "Google Gemini": GeminiProvider,
    "OpenAI (ChatGPT)": OpenAIProvider,
    "Anthropic (Claude)": AnthropicProvider,
    "DeepSeek": DeepseekProvider,
    "Ollama": OllamaProvider,
}

PROVIDER_DISPLAY_NAMES = {
    "Google Gemini": "💎 Google Gemini",
    "OpenAI (ChatGPT)": "🔴 OpenAI (ChatGPT)",
    "Anthropic (Claude)": "🤖 Anthropic (Claude)",
    "DeepSeek": "🌊 DeepSeek",
    "Ollama": "🦙 Ollama (Local)",
}


def create_provider(provider_name: str, config: ProviderConfig) -> BaseProvider:
    """
    Factory para crear un proveedor de IA

    Args:
        provider_name: Nombre del proveedor
        config: Configuración del proveedor

    Returns:
        Instancia del proveedor

    Raises:
        ValueError: Si el proveedor no existe
    """
    if provider_name not in PROVIDER_REGISTRY:
        raise ValueError(
            f"Proveedor desconocido: {provider_name}. "
            f"Disponibles: {', '.join(PROVIDER_REGISTRY.keys())}"
        )

    try:
        provider_class = PROVIDER_REGISTRY[provider_name]
        return provider_class(config)
    except Exception as e:
        logger.error(f"Error creando proveedor {provider_name}: {e}")
        raise


def get_available_providers() -> dict:
    """Retorna diccionario de proveedores disponibles con sus display names"""
    return PROVIDER_DISPLAY_NAMES


def get_provider_models(provider_name: str) -> list:
    """
    Retorna lista de modelos disponibles para un proveedor

    Args:
        provider_name: Nombre del proveedor

    Returns:
        Lista de nombres de modelos
    """
    if provider_name not in PROVIDER_REGISTRY:
        return []

    try:
        provider_class = PROVIDER_REGISTRY[provider_name]
        # Crear instancia temporal solo para obtener modelos
        temp_config = ProviderConfig(api_key="", model_name="")
        # Algunos proveedores necesitan API KEY para inicializar
        # Retornamos modelos por defecto en su lugar
        return _get_default_models(provider_name)
    except Exception as e:
        logger.error(f"Error obteniendo modelos para {provider_name}: {e}")
        return _get_default_models(provider_name)


def _get_default_models(provider_name: str) -> list:
    """Retorna modelos por defecto para cada proveedor"""
    default_models = {
        "Google Gemini": [
            "gemini-2.0-flash",
            "gemini-2.0-flash-exp",
            "gemini-1.5-pro",
            "gemini-1.5-flash",
            "gemini-1.5-pro-vision",
            "gemini-1.5-flash-vision",
        ],
        "OpenAI (ChatGPT)": [
            "gpt-4-turbo",
            "gpt-4",
            "gpt-3.5-turbo",
            "gpt-4o",
            "gpt-4o-mini",
        ],
        "Anthropic (Claude)": [
            "claude-opus-4-1",
            "claude-opus-4",
            "claude-sonnet-4-20250514",
            "claude-sonnet-4",
            "claude-haiku-3",
            "claude-3-5-sonnet-20241022",
            "claude-3-5-haiku-20241022",
        ],
        "DeepSeek": [
            "deepseek-chat",
            "deepseek-coder",
        ],
        "Ollama": [],  # Se cargan dinámicamente
    }
    return default_models.get(provider_name, [])


__all__ = [
    "BaseProvider",
    "ProviderConfig",
    "GeminiProvider",
    "OpenAIProvider",
    "AnthropicProvider",
    "DeepseekProvider",
    "OllamaProvider",
    "create_provider",
    "get_available_providers",
    "get_provider_models",
    "PROVIDER_REGISTRY",
    "PROVIDER_DISPLAY_NAMES",
]
