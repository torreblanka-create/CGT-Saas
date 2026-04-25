"""
==========================================
🔌 BASE PROVIDER — Clase base para todos los proveedores de IA
==========================================
Define la interfaz estándar que todos los proveedores deben implementar.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, List, Any
from dataclasses import dataclass


@dataclass
class ProviderConfig:
    """Configuración estándar de un proveedor"""
    api_key: str
    model_name: str
    temperature: float = 0.7
    max_tokens: int = 4096
    top_p: float = 1.0
    extra_params: Dict[str, Any] = None

    def __post_init__(self):
        if self.extra_params is None:
            self.extra_params = {}


class BaseProvider(ABC):
    """
    Clase base abstracta para todos los proveedores de IA.

    Todos los proveedores deben heredar de esta clase e implementar los métodos abstractos.
    """

    def __init__(self, config: ProviderConfig):
        self.config = config
        self.name = self.__class__.__name__
        self._validate_config()

    @abstractmethod
    def _validate_config(self) -> None:
        """Valida que la configuración sea correcta"""
        if not self.config.api_key:
            raise ValueError(f"{self.name}: API KEY requerida")

    @abstractmethod
    def _initialize_client(self) -> None:
        """Inicializa el cliente del proveedor"""
        pass

    @abstractmethod
    def generate_response(self, prompt: str, **kwargs) -> str:
        """
        Genera una respuesta basada en el prompt

        Args:
            prompt: El texto del prompt
            **kwargs: Parámetros adicionales específicos del proveedor

        Returns:
            La respuesta generada como string
        """
        pass

    @abstractmethod
    def generate_response_stream(self, prompt: str, **kwargs):
        """
        Genera una respuesta en streaming

        Args:
            prompt: El texto del prompt
            **kwargs: Parámetros adicionales

        Yields:
            Fragmentos de la respuesta
        """
        pass

    @abstractmethod
    def get_available_models(self) -> List[str]:
        """Retorna lista de modelos disponibles para este proveedor"""
        pass

    @abstractmethod
    def validate_connection(self) -> bool:
        """Valida que la conexión con el proveedor sea correcta"""
        pass

    def get_provider_info(self) -> Dict[str, str]:
        """Retorna información del proveedor"""
        return {
            "name": self.name,
            "model": self.config.model_name,
            "temperature": str(self.config.temperature),
            "max_tokens": str(self.config.max_tokens),
        }
