"""
==========================================
🦙 OLLAMA PROVIDER
==========================================
Adaptador para Ollama (local LLM)
"""

import logging
from typing import List

try:
    import requests
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False

from .base import BaseProvider, ProviderConfig

logger = logging.getLogger(__name__)


class OllamaProvider(BaseProvider):
    """Proveedor para Ollama (modelos locales)"""

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        # Para Ollama, el api_key es opcional (puede ser URL local)
        # Usamos api_key para almacenar la URL base si es necesario
        self.base_url = config.api_key or "http://localhost:11434"
        self._initialize_client()

    def _validate_config(self) -> None:
        """Valida configuración de Ollama"""
        if not OLLAMA_AVAILABLE:
            raise ImportError("requests no está instalado. Instálalo con: pip install requests")
        if not self.config.model_name:
            raise ValueError("Ollama: Nombre del modelo requerido")

    def _initialize_client(self) -> None:
        """Inicializa cliente de Ollama"""
        try:
            # Validar que Ollama esté disponible
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code != 200:
                raise ConnectionError(f"No se puede conectar a Ollama en {self.base_url}")
            logger.info(f"Ollama Provider inicializado en {self.base_url} con modelo: {self.config.model_name}")
        except Exception as e:
            logger.warning(f"Advertencia inicializando Ollama: {e}")
            # No lanzamos error porque Ollama podría iniciarse después

    def generate_response(self, prompt: str, **kwargs) -> str:
        """Genera respuesta con Ollama"""
        try:
            payload = {
                "model": self.config.model_name,
                "prompt": prompt,
                "temperature": self.config.temperature,
                "top_p": self.config.top_p,
                "stream": False,
                **self.config.extra_params,
                **kwargs,
            }

            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=300,  # Timeout más largo para operaciones locales
            )
            response.raise_for_status()
            return response.json().get("response", "")
        except Exception as e:
            logger.error(f"Error generando respuesta con Ollama: {e}")
            raise

    def generate_response_stream(self, prompt: str, **kwargs):
        """Genera respuesta en streaming con Ollama"""
        try:
            payload = {
                "model": self.config.model_name,
                "prompt": prompt,
                "temperature": self.config.temperature,
                "top_p": self.config.top_p,
                "stream": True,
                **self.config.extra_params,
                **kwargs,
            }

            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                stream=True,
                timeout=300,
            )
            response.raise_for_status()

            for line in response.iter_lines():
                if line:
                    import json
                    data = json.loads(line)
                    if "response" in data:
                        yield data["response"]
        except Exception as e:
            logger.error(f"Error en streaming de Ollama: {e}")
            raise

    def get_available_models(self) -> List[str]:
        """Retorna modelos disponibles en Ollama"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            response.raise_for_status()
            data = response.json()
            return [model["name"] for model in data.get("models", [])]
        except Exception as e:
            logger.error(f"Error obteniendo modelos de Ollama: {e}")
            return []

    def validate_connection(self) -> bool:
        """Valida conexión con Ollama"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Error validando conexión con Ollama: {e}")
            return False
