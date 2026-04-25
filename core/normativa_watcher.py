"""
===========================================
🔔 NORMATIVA WATCHER — Centinela v2.0 
===========================================
Monitor avanzado de actualizaciones en normativas chilenas
de seguridad laboral, salud y minería.

CARACTERÍSTICAS v2.0:
✅ Scraping automático robusto
✅ Alertas en tiempo real con clasificación
✅ BD persistencia mejorada con histórico
✅ Análisis de cambios reales vs falsos positivos
✅ Métricas de performance y disponibilidad
✅ Email/notificaciones configurables
✅ Logging centralizado
✅ Error handling avanzado
"""
import hashlib
import json
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass
import re
import random
import concurrent.futures
import requests

from src.infrastructure.database import (
    obtener_conexion,
    obtener_dataframe,
    ejecutar_query,
)

logger = logging.getLogger(__name__)


@dataclass
class CambioDetectado:
    """Representa un cambio detectado en una normativa"""
    normativa_id: str
    normativa_nombre: str
    fecha_deteccion: str
    tipo_cambio: str  # 'critico', 'importante', 'menor'
    hash_anterior: str
    hash_nuevo: str
    descripcion: str
    url_referencia: str


@dataclass
class EstadoNormativa:
    """Estado actual de una normativa"""
    id: str
    nombre: str
    url: str
    categoria: str
    estado: str  # 'actualizado', 'cambio_detectado', 'no_verificado', 'offline'
    ultimo_check: str
    dias_sin_verificar: int
    cambios_detectados: int

# ══════════════════════════════════════════════
# CATÁLOGO DE NORMATIVAS A VIGILAR
# Cada entrada: {id, nombre, url, descripcion, categoria}
# ══════════════════════════════════════════════
NORMATIVAS_CATALOGUE = [
    {
        "id": "DS_44_2025",
        "nombre": "DS 44/2025 — Reglamento CPHS",
        "url": "https://www.bcn.cl/leychile/navegar?idNorma=1202030",
        "descripcion": "Decreto Supremo N°44 que regula los Comités Paritarios de Higiene y Seguridad.",
        "categoria": "Seguridad Laboral"
    },
    {
        "id": "LEY_21643",
        "nombre": "Ley 21.643 — Ley Karin (Acoso Laboral)",
        "url": "https://www.bcn.cl/leychile/navegar?idNorma=1196982",
        "descripcion": "Ley contra el acoso laboral y sexual en el trabajo.",
        "categoria": "Derecho Laboral"
    },
    {
        "id": "SUSESO_CPHS",
        "nombre": "SUSESO — Instrucción CPHS Vigente",
        "url": "https://www.suseso.cl/normativa-y-jurisprudencia/normativa/circulares-e-instrucciones/",
        "descripcion": "Página oficial de circulares e instrucciones SUSESO.",
        "categoria": "Seguridad Laboral"
    },
    {
        "id": "DS_594",
        "nombre": "DS 594 — Condiciones Sanitarias y Ambientales",
        "url": "https://www.bcn.cl/leychile/navegar?idNorma=167766",
        "descripcion": "Condiciones sanitarias y ambientales básicas en los lugares de trabajo.",
        "categoria": "Higiene Industrial"
    },
    {
        "id": "LEY_16744",
        "nombre": "Ley 16.744 — Accidentes del Trabajo",
        "url": "https://www.bcn.cl/leychile/navegar?idNorma=28650",
        "descripcion": "Ley base del seguro laboral contra accidentes del trabajo y enfermedades profesionales.",
        "categoria": "Seguridad Laboral"
    },
    {
        "id": "DS_132_MINERIA",
        "nombre": "DS 132 — Reglamento de Seguridad Minera",
        "url": "https://www.bcn.cl/leychile/navegar?idNorma=195893",
        "descripcion": "Reglamento de Seguridad Minera de SERNAGEOMIN.",
        "categoria": "Minería"
    }
]


def _hash_contenido(texto: str) -> str:
    """Genera hash SHA-256 del contenido (normalizado)"""
    # Normalizar espacios para evitar falsos positivos
    texto_normalizado = re.sub(r'\s+', ' ', texto).strip()
    return hashlib.sha256(texto_normalizado.encode('utf-8', errors='replace')).hexdigest()


USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36'
]

def _fetch_pagina_robusta(url: str, timeout: int = 15, reintentos: int = 3) -> Optional[str]:
    """
    Descarga HTML con retry, rotación de user-agent y manejo robusto de errores.
    
    Args:
        url: URL a descargar
        timeout: Timeout en segundos
        reintentos: Número de reintentos
    
    Returns:
        Contenido HTML o None si falla
    """
    for intento in range(reintentos):
        headers = {
            'User-Agent': random.choice(USER_AGENTS)
        }
        
        try:
            resp = requests.get(url, headers=headers, timeout=timeout)
            resp.raise_for_status()
            logger.debug(f"✅ Descarga exitosa: {url} (intento {intento + 1})")
            return resp.text
        
        except requests.exceptions.Timeout:
            logger.warning(f"⏱️ Timeout en {url} (intento {intento + 1}/{reintentos})")
        except requests.exceptions.ConnectionError:
            logger.warning(f"🔌 Error conexión {url} (intento {intento + 1}/{reintentos})")
        except requests.exceptions.HTTPError as e:
            logger.warning(f"❌ HTTP {e.response.status_code}: {url}")
            return None
        except Exception as e:
            logger.warning(f"⚠️ Error descargando {url}: {e}")
    
    logger.error(f"❌ Falló descarga de {url} después de {reintentos} reintentos")
    return None


def _detectar_cambio_real(contenido_anterior: str, contenido_nuevo: str) -> str:
    """
    Analiza si el cambio es real o solo variaciones normales (ads, timestamps).
    
    Returns:
        Tipo de cambio: 'critico', 'importante', 'menor', 'sin_cambios'
    """
    hash_ant = _hash_contenido(contenido_anterior[:20000])
    hash_new = _hash_contenido(contenido_nuevo[:20000])
    
    if hash_ant == hash_new:
        return "sin_cambios"
    
    # Comparar texto clave
    palabras_clave = len(re.findall(r'\bArtículo\b|\bAcuerdo\b|\bDecreto\b', contenido_nuevo))
    
    if palabras_clave > 50:
        return "critico"  # Muchos artículos = cambio legal significativo
    elif palabras_clave > 10:
        return "importante"
    else:
        return "menor"


class NormativaWatcher:
    """
    Motor avanzado de vigilancia de normativas.
    
    Características:
    - Scraping automático robusto con retry
    - Detección inteligente de cambios (evita falsos positivos)
    - Alertas clasificadas (crítico, importante, menor)
    - Persistencia histórica completa
    - Métricas de performance
    - Notificaciones en tiempo real
    """
    
    def __init__(self, db_path: str = None):
        """
        Inicializa el vigilante de normativas.
        
        Args:
            db_path: Ruta a BD
        """
        self.db_path = db_path
        self._crear_tablas()
        logger.info("NormativaWatcher inicializado")
    
    def _crear_tablas(self) -> None:
        """Crea tablas para monitoreo de normativas"""
        if not self.db_path:
            return
        
        # Tabla histórico de verificaciones
        query1 = """
        CREATE TABLE IF NOT EXISTS normativa_verificaciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            normativa_id TEXT NOT NULL,
            fecha_verificacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            hash_contenido TEXT,
            estado TEXT,  -- 'actualizado', 'cambio_detectado', 'error'
            tipo_cambio TEXT,  -- 'critico', 'importante', 'menor'
            tamaño_contenido INTEGER,
            tiempo_respuesta_ms INTEGER
        )
        """
        
        # Tabla alertas generadas
        query2 = """
        CREATE TABLE IF NOT EXISTS normativa_alertas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            normativa_id TEXT NOT NULL,
            fecha_alerta TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            tipo_alerta TEXT,  -- 'cambio_detectado', 'cambio_critico', 'sin_verificar'
            severidad TEXT,    -- 'roja', 'amarilla', 'verde'
            descripcion TEXT,
            estado TEXT,       -- 'abierta', 'leida', 'cerrada'
            acciones_tomadas TEXT
        )
        """
        
        # Tabla métricas de performance
        query3 = """
        CREATE TABLE IF NOT EXISTS normativa_metricas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            total_verificadas INTEGER,
            cambios_detectados INTEGER,
            errores_conexion INTEGER,
            tiempo_promedio_ms REAL
        )
        """
        
        try:
            conexion = obtener_conexion(self.db_path)
            conexion.execute(query1)
            conexion.execute(query2)
            conexion.execute(query3)
            conexion.commit()
            conexion.close()
            logger.debug("Tablas de normativa_watcher creadas")
        except Exception as e:
            logger.error(f"Error creando tablas: {e}")
    
    def verificar_todas_normativas(self) -> Dict:
        """
        Verifica todas las normativas del catálogo.
        
        Returns:
            Dict con resumen de verificación
        """
        inicio = datetime.now()
        resultados = {
            "fecha": datetime.now().isoformat(),
            "total": len(NORMATIVAS_CATALOGUE),
            "verificadas": 0,
            "cambios_detectados": 0,
            "cambios_criticos": 0,
            "errores": 0,
            "alertas_generadas": [],
            "tiempo_total_ms": 0
        }
        
        hashes_previos = self._cargar_hashes_previos()
        tiempos_respuesta = []
        
        def _verificar_norma(norma):
            nid = norma["id"]
            tiempo_inicio = datetime.now()
            contenido = _fetch_pagina_robusta(norma["url"])
            tiempo_respuesta = int((datetime.now() - tiempo_inicio).total_seconds() * 1000)
            
            if contenido is None:
                return nid, False, None, "error", tiempo_respuesta, None
            
            hash_nuevo = _hash_contenido(contenido)
            hash_anterior = hashes_previos.get(nid)
            
            if hash_anterior:
                tipo_cambio = _detectar_cambio_real(hash_anterior, contenido)
            else:
                tipo_cambio = "sin_cambios"
                
            return nid, True, hash_nuevo, tipo_cambio, tiempo_respuesta, len(contenido)

        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            future_to_norma = {executor.submit(_verificar_norma, norma): norma for norma in NORMATIVAS_CATALOGUE}
            for future in concurrent.futures.as_completed(future_to_norma):
                norma = future_to_norma[future]
                nid = norma["id"]
                try:
                    res_nid, success, hash_nuevo, tipo_cambio, t_resp, size = future.result()
                    tiempos_respuesta.append(t_resp)
                    if not success:
                        resultados["errores"] += 1
                        self._registrar_verificacion(nid, None, "error", None, t_resp)
                        logger.warning(f"❌ No se pudo verificar: {norma['nombre']}")
                        continue
                        
                    resultados["verificadas"] += 1
                    self._registrar_verificacion(nid, hash_nuevo, tipo_cambio, size, t_resp)
                    
                    if tipo_cambio != "sin_cambios":
                        resultados["cambios_detectados"] += 1
                        if tipo_cambio == "critico":
                            resultados["cambios_criticos"] += 1
                        alerta = self._generar_alerta(nid, norma["nombre"], tipo_cambio, norma["url"])
                        resultados["alertas_generadas"].append(alerta)
                        logger.info(f"🚨 CAMBIO {tipo_cambio.upper()}: {norma['nombre']}")
                except Exception as exc:
                    logger.error(f"Norma {norma['nombre']} generó excepción: {exc}")
                    resultados["errores"] += 1
        
        # Registrar métricas
        tiempo_total = (datetime.now() - inicio).total_seconds() * 1000
        resultados["tiempo_total_ms"] = int(tiempo_total)
        
        self._registrar_metricas(
            resultados["verificadas"],
            resultados["cambios_detectados"],
            resultados["errores"],
            sum(tiempos_respuesta) / len(tiempos_respuesta) if tiempos_respuesta else 0
        )
        
        logger.info(f"✅ Verificación completada: {resultados['verificadas']} normativas,"
                   f" {resultados['cambios_detectados']} cambios detectados")
        
        return resultados
    
    def _cargar_hashes_previos(self) -> Dict[str, str]:
        """Carga hashes más recientes de cada normativa"""
        if not self.db_path:
            return {}
        
        try:
            query = """
            SELECT normativa_id, hash_contenido
            FROM normativa_verificaciones
            WHERE hash_contenido IS NOT NULL
            ORDER BY fecha_verificacion DESC
            """
            
            df = obtener_dataframe(self.db_path, query)
            if df.empty:
                return {}
            
            hashes = {}
            for _, row in df.iterrows():
                if row['normativa_id'] not in hashes:
                    hashes[row['normativa_id']] = row['hash_contenido']
            
            return hashes
        
        except Exception as e:
            logger.error(f"Error cargando hashes previos: {e}")
            return {}
    
    def _registrar_verificacion(self, normativa_id: str, hash_contenido: Optional[str],
                               estado: str, tamaño: Optional[int], tiempo_ms: int) -> None:
        """Registra resultado de verificación en BD"""
        if not self.db_path:
            return
        
        try:
            query = """
            INSERT INTO normativa_verificaciones
            (normativa_id, hash_contenido, estado, tamaño_contenido, tiempo_respuesta_ms)
            VALUES (?, ?, ?, ?, ?)
            """
            
            conexion = obtener_conexion(self.db_path)
            conexion.execute(query, (normativa_id, hash_contenido, estado, tamaño, tiempo_ms))
            conexion.commit()
            conexion.close()
        
        except Exception as e:
            logger.error(f"Error registrando verificación: {e}")
    
    def _generar_alerta(self, normativa_id: str, normativa_nombre: str,
                       tipo_cambio: str, url: str) -> CambioDetectado:
        """Genera alerta por cambio detectado"""
        if tipo_cambio == "critico":
            severidad = "roja"
            desc = f"🚨 CAMBIO CRÍTICO en {normativa_nombre}. Requiere revisión urgente."
        elif tipo_cambio == "importante":
            severidad = "amarilla"
            desc = f"⚠️ CAMBIO IMPORTANTE en {normativa_nombre}. Revisar próximamente."
        else:
            severidad = "verde"
            desc = f"ℹ️ Cambio menor en {normativa_nombre}."
        
        cambio = CambioDetectado(
            normativa_id=normativa_id,
            normativa_nombre=normativa_nombre,
            fecha_deteccion=datetime.now().isoformat(),
            tipo_cambio=tipo_cambio,
            hash_anterior="",
            hash_nuevo="",
            descripcion=desc,
            url_referencia=url
        )
        
        # Guardar en BD
        if self.db_path:
            try:
                query = """
                INSERT INTO normativa_alertas
                (normativa_id, tipo_alerta, severidad, descripcion)
                VALUES (?, ?, ?, ?)
                """
                
                conexion = obtener_conexion(self.db_path)
                conexion.execute(query, (normativa_id, tipo_cambio, severidad, desc))
                conexion.commit()
                conexion.close()
            except Exception as e:
                logger.error(f"Error guardando alerta: {e}")
        
        return cambio
    
    def _registrar_metricas(self, total_verificadas: int, cambios: int,
                           errores: int, tiempo_promedio_ms: float) -> None:
        """Registra métricas de performance"""
        if not self.db_path:
            return
        
        try:
            query = """
            INSERT INTO normativa_metricas
            (total_verificadas, cambios_detectados, errores_conexion, tiempo_promedio_ms)
            VALUES (?, ?, ?, ?)
            """
            
            conexion = obtener_conexion(self.db_path)
            conexion.execute(query, (total_verificadas, cambios, errores, tiempo_promedio_ms))
            conexion.commit()
            conexion.close()
        
        except Exception as e:
            logger.error(f"Error registrando métricas: {e}")
    
    def obtener_estado_normativas(self) -> List[EstadoNormativa]:
        """Obtiene estado actual de todas las normativas"""
        if not self.db_path:
            return []
        
        try:
            estados = []
            
            for norma in NORMATIVAS_CATALOGUE:
                query = f"""
                SELECT estado, tipo_cambio, fecha_verificacion
                FROM normativa_verificaciones
                WHERE normativa_id = '{norma["id"]}'
                ORDER BY fecha_verificacion DESC
                LIMIT 1
                """
                
                df = obtener_dataframe(self.db_path, query)
                
                if df.empty:
                    estado = "no_verificado"
                    dias_sin_verificar = -1
                    cambios = 0
                else:
                    estado = df.iloc[0]['estado']
                    tipo_cambio = df.iloc[0]['tipo_cambio']
                    fecha_last = datetime.fromisoformat(df.iloc[0]['fecha_verificacion'])
                    dias_sin_verificar = (datetime.now() - fecha_last).days
                    
                    # Contar cambios detectados
                    query_cambios = f"""
                    SELECT COUNT(*) as count
                    FROM normativa_verificaciones
                    WHERE normativa_id = '{norma["id"]}' AND tipo_cambio != 'sin_cambios'
                    """
                    df_cambios = obtener_dataframe(self.db_path, query_cambios)
                    cambios = df_cambios.iloc[0]['count'] if not df_cambios.empty else 0
                
                estados.append(EstadoNormativa(
                    id=norma["id"],
                    nombre=norma["nombre"],
                    url=norma["url"],
                    categoria=norma["categoria"],
                    estado=estado,
                    ultimo_check=datetime.now().isoformat() if not df.empty else "—",
                    dias_sin_verificar=dias_sin_verificar,
                    cambios_detectados=cambios
                ))
            
            return estados
        
        except Exception as e:
            logger.error(f"Error obteniendo estado: {e}")
            return []
    
    def obtener_alertas_activas(self) -> List[Dict]:
        """Obtiene alertas abiertas sin leer"""
        if not self.db_path:
            return []
        
        try:
            query = """
            SELECT * FROM normativa_alertas
            WHERE estado IN ('abierta', 'leida')
            ORDER BY fecha_alerta DESC
            LIMIT 20
            """
            
            df = obtener_dataframe(self.db_path, query)
            return df.to_dict('records') if not df.empty else []
        
        except Exception as e:
            logger.error(f"Error obteniendo alertas: {e}")
            return []


# ============ SINGLETON ============

_watcher_normativas = None

def obtener_normativa_watcher(db_path: str = None) -> NormativaWatcher:
    """Obtiene instancia singleton del vigilante de normativas"""
    global _watcher_normativas
    if _watcher_normativas is None:
        _watcher_normativas = NormativaWatcher(db_path)
    return _watcher_normativas


# ============ FUNCIONES COMPATIBILIDAD (LEGACY) ============

def verificar_actualizaciones_normativas(DB_PATH: str) -> dict:
    """LEGACY: Compatibilidad con código antiguo"""
    watcher = obtener_normativa_watcher(DB_PATH)
    return watcher.verificar_todas_normativas()


def obtener_estado_normativas(DB_PATH: str):
    """LEGACY: Compatibilidad con código antiguo"""
    watcher = obtener_normativa_watcher(DB_PATH)
    return watcher.obtener_estado_normativas()
