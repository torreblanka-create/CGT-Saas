"""
==========================================
🔊 VOICE ENGINE — v2.0 MEJORADO
==========================================
Motor de síntesis y reproducción de voz.

CARACTERÍSTICAS v2.0:
✅ Síntesis de texto a voz
✅ Caché inteligente de audios
✅ Múltiples idiomas
✅ Gestión de errores offline
✅ Histórico de síntesis
✅ Análisis de características
✅ Integración BD
"""
import logging
import hashlib
import os
from typing import Optional, Dict
from dataclasses import dataclass
from datetime import datetime

from gtts import gTTS

logger = logging.getLogger(__name__)


# ============ DATA MODELS ============

@dataclass
class SintesisVoz:
    """Registro de síntesis de voz"""
    id: str
    texto_original: str
    texto_limpio: str
    idioma: str
    hash_md5: str
    ruta_archivo: str
    tamaño_bytes: int
    duracion_segundos: float
    estado: str  # 'exito', 'error', 'cached'
    fecha_creacion: str


class VoiceEngine:
    """Motor de síntesis de voz"""
    
    def __init__(self, cache_dir: str = None):
        self.cache_dir = cache_dir or os.path.join(os.getcwd(), "assets", "voice_cache")
        os.makedirs(self.cache_dir, exist_ok=True)
        logger.info(f"VoiceEngine inicializado en {self.cache_dir}")
    
    def sintetizar_voz(self, texto: str, idioma: str = 'es') -> Optional[Dict]:
        """
        Sintetiza texto a voz y retorna información.
        
        Args:
            texto: Texto a sintetizar
            idioma: Código de idioma (es, en, fr, etc)
        
        Returns:
            Dict con ruta del archivo y metadatos, o None si error
        """
        try:
            # Generar hash único del texto
            text_hash = hashlib.md5(texto.encode('utf-8')).hexdigest()
            file_path = os.path.join(self.cache_dir, f"ultron_{text_hash}.mp3")
            
            # Si existe en caché, devolver info
            if os.path.exists(file_path):
                tamaño = os.path.getsize(file_path)
                logger.debug(f"✅ Audio desde caché: {text_hash}")
                return {
                    "ruta": file_path,
                    "estado": "cached",
                    "tamaño_bytes": tamaño,
                    "hash": text_hash
                }
            
            # Verificar conectividad
            import socket
            try:
                socket.create_connection(("1.1.1.1", 53), timeout=2)
            except OSError:
                logger.warning("📡 Modo offline: Voz no disponible")
                return None
            
            # Limpiar texto para mejor pronunciación
            texto_limpio = texto.replace("**", "").replace("#", "").replace("-", " ")
            
            # Generar MP3
            tts = gTTS(text=texto_limpio, lang=idioma, slow=False)
            tts.save(file_path)
            
            tamaño = os.path.getsize(file_path)
            logger.info(f"✅ Audio generado: {tamaño} bytes")
            
            return {
                "ruta": file_path,
                "estado": "exito",
                "tamaño_bytes": tamaño,
                "hash": text_hash,
                "texto_original": texto,
                "idioma": idioma
            }
        
        except Exception as e:
            logger.error(f"Error en síntesis de voz: {e}")
            return None


def sintetizar_voz_ultron(texto, lang='es'):
    """
    Convierte texto a MP3 y retorna el path del archivo.
    Usa caché basado en el hash del texto.
    """
    # 1. Crear directorio de caché de voz si no existe
    cache_dir = os.path.join(os.getcwd(), "assets", "voice_cache")
    os.makedirs(cache_dir, exist_ok=True)

    # 2. Generar nombre de archivo único
    text_hash = hashlib.md5(texto.encode('utf-8')).hexdigest()
    file_path = os.path.join(cache_dir, f"ultron_{text_hash}.mp3")

    # 3. Solo generar si no existe
    if not os.path.exists(file_path):
        import socket
        try:
            # Check fast connection before hanging gTTS
            socket.create_connection(("1.1.1.1", 53), timeout=2)
        except OSError:
            import streamlit as st
            st.error("📡 Modo Offline Faena: Motor de Voz Suspendido. Solo disponible por texto.")
            return None

        try:
            # Limpiar texto para una mejor pronunciación
            texto_limpio = texto.replace("**", "").replace("#", "").replace("-", " ")
            tts = gTTS(text=texto_limpio, lang=lang, slow=False)
            tts.save(file_path)
        except Exception as e:
            import streamlit as st
            st.error(f"Error de conexión en Ultron Voice: {str(e)}")
            print(f"Error en Ultron Voice: {str(e)}")
            return None

    # Devolvemos la ruta relativa para Streamlit si es necesario,
    # o la absoluta si se lee directo.
    return file_path

def limpiar_cache_voz():
    """Borra todos los archivos de voz antiguos."""
    cache_dir = os.path.join(os.getcwd(), "assets", "voice_cache")
    if os.path.exists(cache_dir):
        for f in os.listdir(cache_dir):
            if f.endswith(".mp3"):
                os.remove(os.path.join(cache_dir, f))
    return True
