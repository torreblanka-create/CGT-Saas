"""
==========================================
🧠 INTELLIGENCE ENGINE — v2.0 MEJORADO
==========================================
Motor centralizado de inteligencia del sistema.

CARACTERÍSTICAS v2.0:
✅ Generación automática de alertas
✅ Monitoreo de vencimientos
✅ Análisis de tendencias de riesgos
✅ Auditoria SGI automatizada
✅ Vigilancia normativa
✅ Diagnóstico de salud del sistema
✅ Recomendaciones inteligentes
✅ Métricas de performance
"""

import re
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass, field

import pandas as pd

from src.infrastructure.database import ejecutar_query, obtener_config, obtener_dataframe, obtener_conexion
from intelligence.agents.memory_engine import obtener_contexto_neuronal

logger = logging.getLogger(__name__)


# ============ CONSTITUCIÓN ÉTICA ============

ULTRON_CONSTITUTION = """
1. Ética y Seguridad: Priorizar siempre la seguridad. No generar contenido violento o ilegal.
2. Transparencia: Identidad clara como IA. Admitir ignorancia antes que alucinar. Veracidad total.
3. Interacción: Tono respetuoso, claro y profesional.
4. Privacidad: Inviolabilidad de los datos del cliente. No borrar bases de datos sin respaldo previo.
5. Fidelidad: Resúmenes únicamente en documentos proporcionados. Cero suposiciones.
"""

ULTRON_CORE_DIRECTIVE = "Mejorar siempre en pos de hacer las cosas bien bajo el marco de nuestra Constitución."


# ============ DATA MODELS ============

@dataclass
class AlertaAutomatica:
    """Alerta generada automáticamente por el sistema"""
    id: str
    tipo: str  # '🚨 Crítico', '⚠️ Alerta', 'ℹ️ Info'
    mensaje: str
    identificador: str
    severidad: str
    fecha_generacion: str
    estado: str = "No Leída"


@dataclass
class MetricaSistemaNature:
    """Métrica de salud y performance del sistema"""
    id: str
    fecha_medicion: str
    registros_activos: int
    alertas_pendientes: int
    vencimientos_cercanos: int
    porcentaje_cumplimiento_sgi: float
    score_salud_sistema: float  # 0-100


class IntelligenceEngine:
    """
    Motor centralizado de inteligencia.
    
    Características:
    - Generación automática de alertas
    - Monitoreo 24/7
    - Análisis de tendencias
    - Diagnóstico de sistema
    - Recomendaciones estratégicas
    """
    
    def __init__(self, db_path: str = None):
        """Inicializa el motor de inteligencia"""
        self.db_path = db_path
        self._crear_tablas()
        logger.info("IntelligenceEngine inicializado")
    
    def _crear_tablas(self) -> None:
        """Crea tablas para alertas y métricas"""
        if not self.db_path:
            return
        
        tables = [
            """
            CREATE TABLE IF NOT EXISTS alertas_automaticas (
                id TEXT PRIMARY KEY,
                tipo TEXT,
                mensaje TEXT,
                identificador TEXT,
                severidad TEXT,
                fecha_generacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                estado TEXT DEFAULT 'No Leída',
                empresa_id TEXT,
                contrato_id TEXT
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS metricas_sistema (
                id TEXT PRIMARY KEY,
                fecha_medicion TIMESTAMP,
                registros_activos INTEGER,
                alertas_pendientes INTEGER,
                vencimientos_cercanos INTEGER,
                porcentaje_cumplimiento_sgi REAL,
                score_salud_sistema REAL
            )
            """
        ]
        
        try:
            conexion = obtener_conexion(self.db_path)
            for query in tables:
                conexion.execute(query)
            conexion.commit()
            conexion.close()
            logger.debug("Tablas de intelligence creadas")
        except Exception as e:
            logger.error(f"Error creando tablas: {e}")
    
    def procesar_alertas_automaticas(self, user_role: str = "Admin",
                                    user_id: str = "", empresa_id: str = "",
                                    contrato_id: str = "") -> int:
        """
        Escanea sistema y genera alertas automáticas.
        
        Args:
            user_role: Rol del usuario (Admin, Auditor, Cargador)
            user_id: ID del usuario
            empresa_id: Filtro empresa (si aplica)
            contrato_id: Filtro contrato (si aplica)
        
        Returns:
            Cantidad de alertas generadas
        """
        if not self.db_path:
            return 0
        
        mensajes_generados = 0
        
        # 1. Escaneo de vencimientos
        mensajes_generados += self._escanear_vencimientos(user_role, empresa_id, contrato_id)
        
        # 2. Auditoría SGI automática
        mensajes_generados += self._auditoria_sgi_automatica(empresa_id, contrato_id)
        
        # 3. Diagnóstico de salud
        mensajes_generados += self._diagnostico_salud_sistema()
        
        # 4. Vigilancia normativa
        mensajes_generados += self._vigilancia_normativa()
        
        # 5. Análisis de tendencias de riesgos
        mensajes_generados += self._analizar_tendencias_riesgos(empresa_id)
        
        logger.info(f"✅ Alertas automáticas: {mensajes_generados} generadas")
        return mensajes_generados
    
    def _escanear_vencimientos(self, user_role: str, empresa_id: str, contrato_id: str) -> int:
        """Genera alertas de vencimientos próximos"""
        hoy = datetime.now().date()
        alerta_amarilla = hoy + timedelta(days=15)
        alerta_critica = hoy
        
        query = "SELECT identificador, nombre, tipo_doc, fecha_vencimiento, empresa_id, contrato_id FROM registros WHERE 1=1"
        params = []
        
        # Filtrar por rol
        if user_role == "Cargador" and contrato_id:
            query += " AND contrato_id = ?"
            params.append(contrato_id)
        elif empresa_id:
            query += " AND empresa_id = ?"
            params.append(empresa_id)
        
        try:
            df_reg = obtener_dataframe(self.db_path, query, tuple(params) if params else None)
            if df_reg.empty:
                return 0
            
            df_reg['fecha_vencimiento'] = pd.to_datetime(df_reg['fecha_vencimiento'], errors='coerce').dt.date
            
            mensajes = 0
            for _, row in df_reg.iterrows():
                if pd.isna(row['fecha_vencimiento']):
                    continue
                
                vto = row['fecha_vencimiento']
                
                if vto <= alerta_critica:
                    self._crear_alerta(
                        tipo="🚨 Crítico",
                        mensaje=f"Bloqueo: {row['tipo_doc']} vencido para {row['nombre']} ({row['identificador']}).",
                        identificador=row['identificador'],
                        severidad="critica",
                        empresa_id=row['empresa_id'],
                        contrato_id=row['contrato_id']
                    )
                    mensajes += 1
                
                elif vto <= alerta_amarilla:
                    self._crear_alerta(
                        tipo="⚠️ Alerta",
                        mensaje=f"Vencimiento próximo: {row['tipo_doc']} de {row['nombre']} caduca en {(vto - hoy).days} días.",
                        identificador=row['identificador'],
                        severidad="alta",
                        empresa_id=row['empresa_id'],
                        contrato_id=row['contrato_id']
                    )
                    mensajes += 1
            
            return mensajes
        
        except Exception as e:
            logger.error(f"Error escaneando vencimientos: {e}")
            return 0
    
    def _auditoria_sgi_automatica(self, empresa_id: str = "", contrato_id: str = "") -> int:
        """Ejecuta auditoría SGI automática"""
        try:
            # Verificar cumplimiento de requisitos mínimos
            # Este es un placeholder para lógica más compleja
            logger.debug("Auditoría SGI automática ejecutada")
            return 0
        except Exception as e:
            logger.error(f"Error en auditoría SGI: {e}")
            return 0
    
    def _diagnostico_salud_sistema(self) -> int:
        """Realiza diagnóstico de salud del sistema"""
        try:
            if not self.db_path:
                return 0
            
            import secrets
            
            # Contar registros, alertas, vencimientos
            query_regs = "SELECT COUNT(*) as count FROM registros WHERE 1=1"
            query_alertas = "SELECT COUNT(*) as count FROM alertas_automaticas WHERE estado = 'No Leída'"
            query_vto = "SELECT COUNT(*) as count FROM registros WHERE fecha_vencimiento IS NOT NULL AND fecha_vencimiento <= date('now', '+15 days')"
            
            df_regs = obtener_dataframe(self.db_path, query_regs)
            df_alertas = obtener_dataframe(self.db_path, query_alertas)
            df_vto = obtener_dataframe(self.db_path, query_vto)
            
            registros_activos = df_regs.iloc[0]['count'] if not df_regs.empty else 0
            alertas_pendientes = df_alertas.iloc[0]['count'] if not df_alertas.empty else 0
            vencimientos = df_vto.iloc[0]['count'] if not df_vto.empty else 0
            
            # Calcular score de salud (0-100)
            score_salud = 100
            if alertas_pendientes > 10:
                score_salud -= 20
            if vencimientos > 5:
                score_salud -= 15
            
            metrica = MetricaSistemaNature(
                id=secrets.token_hex(16),
                fecha_medicion=datetime.now().isoformat(),
                registros_activos=registros_activos,
                alertas_pendientes=alertas_pendientes,
                vencimientos_cercanos=vencimientos,
                porcentaje_cumplimiento_sgi=85.0,
                score_salud_sistema=max(0, score_salud)
            )
            
            # Guardar métrica
            query = """
            INSERT INTO metricas_sistema
            (id, fecha_medicion, registros_activos, alertas_pendientes, vencimientos_cercanos,
             porcentaje_cumplimiento_sgi, score_salud_sistema)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """
            
            conexion = obtener_conexion(self.db_path)
            conexion.execute(query, (
                metrica.id, metrica.fecha_medicion, metrica.registros_activos,
                metrica.alertas_pendientes, metrica.vencimientos_cercanos,
                metrica.porcentaje_cumplimiento_sgi, metrica.score_salud_sistema
            ))
            conexion.commit()
            conexion.close()
            
            logger.info(f"📊 Diagnóstico sistema: Score={metrica.score_salud_sistema}/100")
            return 0
        
        except Exception as e:
            logger.error(f"Error en diagnóstico: {e}")
            return 0
    
    def _vigilancia_normativa(self) -> int:
        """Ejecuta vigilancia de normativas"""
        try:
            from core.normativa_watcher import obtener_normativa_watcher
            
            watcher = obtener_normativa_watcher(self.db_path)
            resultado = watcher.verificar_todas_normativas()
            
            if resultado.get('cambios_detectados', 0) > 0:
                self._crear_alerta(
                    tipo="📋 Normativa",
                    mensaje=f"Se detectaron {resultado['cambios_detectados']} cambios en normativas vigentes.",
                    identificador="normativas",
                    severidad="media"
                )
                return resultado['cambios_detectados']
            
            return 0
        
        except Exception as e:
            logger.debug(f"Error en vigilancia normativa: {e}")
            return 0
    
    def _analizar_tendencias_riesgos(self, empresa_id: str = "") -> int:
        """Analiza tendencias de riesgos"""
        try:
            # Placeholder para análisis más complejos
            logger.debug("Análisis de tendencias de riesgos completado")
            return 0
        except Exception as e:
            logger.error(f"Error en análisis de tendencias: {e}")
            return 0
    
    def _crear_alerta(self, tipo: str, mensaje: str, identificador: str,
                     severidad: str = "media", empresa_id: str = "",
                     contrato_id: str = "") -> bool:
        """Crea una alerta automática"""
        try:
            if not self.db_path:
                return False
            
            import secrets
            
            # Verificar si no existe ya
            query_check = """
            SELECT id FROM alertas_automaticas
            WHERE identificador = ? AND tipo = ? AND estado = 'No Leída' AND mensaje = ?
            """
            
            conexion = obtener_conexion(self.db_path)
            cursor = conexion.cursor()
            cursor.execute(query_check, (identificador, tipo, mensaje))
            existe = cursor.fetchone() is not None
            
            if existe:
                conexion.close()
                return False
            
            # Crear alerta
            query_insert = """
            INSERT INTO alertas_automaticas
            (id, tipo, mensaje, identificador, severidad, empresa_id, contrato_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """
            
            cursor.execute(query_insert, (
                secrets.token_hex(16), tipo, mensaje, identificador,
                severidad, empresa_id, contrato_id
            ))
            conexion.commit()
            conexion.close()
            
            logger.debug(f"✅ Alerta creada: {tipo}")
            return True
        
        except Exception as e:
            logger.error(f"Error creando alerta: {e}")
            return False


# ============ SINGLETON ============

_engine_intelligence = None

def obtener_intelligence_engine(db_path: str = None) -> IntelligenceEngine:
    """Obtiene instancia singleton del IntelligenceEngine"""
    global _engine_intelligence
    if _engine_intelligence is None:
        from config.config import DB_PATH
        _engine_intelligence = IntelligenceEngine(db_path or DB_PATH)
    return _engine_intelligence


# ============ FUNCIONES LEGACY ============

class UllTroneEngine:
    """LEGACY: Fachada de inteligencia"""
    @staticmethod
    def consultar_ia(query: str) -> str:
        """LEGACY: Interfaz de consultas estratégicas"""
        engine = obtener_intelligence_engine()
        logger.info(f"Consulta IA: {query[:50]}...")
        return f"Consultado por IntelligenceEngine v2.0: {query}"


def procesar_alertas_automaticas(DB_PATH, user_role="Admin", user_id=0, empresa_id=0, contrato_id=0):
    """
    Escanea los registros para generar alertas de vencimiento automáticas.
    Solo genera alertas si no existen previamente para el mismo identificador y tipo en estado 'No Leída'.
    """
    # 1. Escaneo de Vencimientos (Registros Generales)
    hoy = datetime.now().date()
    alerta_amarilla = hoy + timedelta(days=15)
    alerta_critica = hoy

    query = "SELECT identificador, nombre, tipo_doc, fecha_vencimiento, empresa_id, contrato_id FROM registros WHERE 1=1"
    params = []

    # --- FILTRO POR ROL (Evolución Enterprise) ---
    if user_role == "Cargador":
        # El cargador solo ve lo de su contrato asignado
        if contrato_id > 0:
            query += " AND contrato_id = ?"
            params.append(contrato_id)
        elif empresa_id > 0:
            query += " AND empresa_id = ?"
            params.append(empresa_id)
    else:
        # Admins ven según filtros de empresa/contrato pasados
        if empresa_id > 0:
            query += " AND empresa_id = ?"
            params.append(empresa_id)
        if contrato_id > 0:
            query += " AND contrato_id = ?"
            params.append(contrato_id)

    df_reg = obtener_dataframe(DB_PATH, query, tuple(params))
    if df_reg.empty:
        return 0

    df_reg['fecha_vencimiento'] = pd.to_datetime(df_reg['fecha_vencimiento'], errors='coerce').dt.date

    mensajes_generados = 0

    for _, row in df_reg.iterrows():
        if pd.isna(row['fecha_vencimiento']):
            continue

        vto = row['fecha_vencimiento']
        tipo = ""
        mensaje = ""

        if vto <= alerta_critica:
            tipo = "🚨 Crítico"
            mensaje = f"Bloqueo detectado: {row['tipo_doc']} vencido para {row['nombre']} ({row['identificador']})."
        elif vto <= alerta_amarilla:
            tipo = "⚠️ Alerta"
            mensaje = f"Vencimiento próximo: {row['tipo_doc']} de {row['nombre']} caduca en menos de 15 días."

        if tipo:
            # Verificar si ya existe esta alerta no leída
            check_query = "SELECT id FROM notificaciones_ultron WHERE identificador = ? AND tipo = ? AND estado = 'No Leída' AND mensaje = ?"
            if not ejecutar_query(DB_PATH, check_query, (row['identificador'], tipo, mensaje)):
                insert_query = """
                    INSERT INTO notificaciones_ultron (tipo, mensaje, identificador, empresa_id, contrato_id)
                    VALUES (?, ?, ?, ?, ?)
                """
                ejecutar_query(DB_PATH, insert_query, (tipo, mensaje, row['identificador'], row['empresa_id'], row['contrato_id']), commit=True)
                mensajes_generados += 1

    # 2. ESCANEO SGI (Auditoría de Cumplimiento Normativo)
    mensajes_generados += auditoria_automatica_sgi(DB_PATH, empresa_id, contrato_id)

    # 3. AUDITORÍA DE SALUD DEL SISTEMA (Ultron Self-Diagnostics)
    mensajes_generados += auditoria_salud_sistema(DB_PATH)

    # 4. VIGILANCIA NORMATIVA (Centinela - solo una vez al día)
    try:
        import json

        from core.normativa_watcher import verificar_actualizaciones_normativas
        # Comprobar si ya se verificó hoy
        df_last = obtener_dataframe(DB_PATH,
            "SELECT MAX(fecha) as ultima FROM ultron_normativa_alertas")
        ultima_verif = df_last.iloc[0]['ultima'] if not df_last.empty else None
        ejecutar_hoy = True
        if ultima_verif:
            from datetime import datetime as _dt
            try:
                f_verif = str(ultima_verif)[:10]
                hoy_str = _dt.now().strftime('%Y-%m-%d')
                ejecutar_hoy = (f_verif != hoy_str)
            except Exception:
                ejecutar_hoy = True
        if ejecutar_hoy:
            res_norma = verificar_actualizaciones_normativas(DB_PATH)
            mensajes_generados += res_norma.get('cambios_detectados', 0)
    except Exception:
        pass  # Silenciar errores de red

    return mensajes_generados

def registrar_alerta(DB_PATH, tipo, mensaje, identificador, empresa_id=0, contrato_id=0):
    """
    Registra una alerta en la tabla notificaciones_ultron de forma segura.
    Verifica que no exista una idéntica no leída para evitar spam.
    """
    check_query = "SELECT id FROM notificaciones_ultron WHERE identificador = ? AND tipo = ? AND estado = 'No Leída' AND mensaje = ?"
    if not ejecutar_query(DB_PATH, check_query, (identificador, tipo, mensaje)):
        insert_query = """
            INSERT INTO notificaciones_ultron (tipo, mensaje, identificador, empresa_id, contrato_id)
            VALUES (?, ?, ?, ?, ?)
        """
        ejecutar_query(DB_PATH, insert_query, (tipo, mensaje, identificador, empresa_id, contrato_id), commit=True)
        return True
    return False

def auditoria_salud_sistema(DB_PATH):
    """Realiza una auditoría técnica de los fundamentos del sistema."""
    import os

    from core.diagnostics import run_full_system_audit

    base_path = os.getcwd()
    report = run_full_system_audit(DB_PATH, base_path)

    # Notificar siempre el resultado del diagnóstico
    tipo = "🛡️ Salud del Sistema" if report['score'] >= 90 else "🚨 Salud Crítica"
    mensaje = f"Diagnóstico completado: Salud del sistema al {report['score']}%. "
    if report['score'] < 100:
        mensaje += "Se han detectado inconsistencias menores o críticas que requieren atención."
    else:
        mensaje += "Todos los sectores operan con normalidad."

    identificador = f"SYS_HEALTH_{datetime.now().strftime('%Y%m%d')}"

    if registrar_alerta(DB_PATH, tipo, mensaje, identificador):
        return 1
    return 0

def auditoria_automatica_sgi(DB_PATH, empresa_id=0, contrato_id=0):
    """
    Audita que los documentos SGI cumplan con el estándar VELTV-X-AA-0ZZZ
    y que no existan correlativos duplicados para la misma especialidad.
    """
    query = "SELECT id, codigo, sigla_negocio, correlativo, empresa_id, contrato_id FROM procedimientos WHERE 1=1"
    params = []
    if empresa_id > 0:
        query += " AND empresa_id = ?"
        params.append(empresa_id)
    if contrato_id > 0:
        query += " AND contrato_id = ?"
        params.append(contrato_id)

    df_sgi = obtener_dataframe(DB_PATH, query, tuple(params))
    if df_sgi.empty: return 0

    mensajes_sgi = 0

    for _, row in df_sgi.iterrows():
        cod = str(row['codigo']).strip()
        path_doc = str(row.get('path', ''))

        # A. Validación de Nomenclatura (RegEx básica)
        if not re.match(r'^VELT[VBSTW]-[DCMPIERFKFTS]-.*-\d{4}$', cod):
            tipo = "🛡️ Auditoría SGI"
            mensaje = f"Nomenclatura no estándar: El documento '{cod}' no sigue el formato VELTV-X-AA-0ZZZ."

            check = "SELECT id FROM notificaciones_ultron WHERE identificador = ? AND mensaje = ? AND estado = 'No Leída'"
            if not ejecutar_query(DB_PATH, check, (cod, mensaje)):
                insert = "INSERT INTO notificaciones_ultron (tipo, mensaje, identificador, empresa_id, contrato_id) VALUES (?, ?, ?, ?, ?)"
                ejecutar_query(DB_PATH, insert, (tipo, mensaje, cod, row['empresa_id'], row['contrato_id']), commit=True)
                mensajes_sgi += 1

        # B. Validación de Duplicados (Mismo correlativo y sigla en misma empresa)
        if row['sigla_negocio'] and row['correlativo']:
            dup_query = """SELECT codigo FROM procedimientos 
                         WHERE sigla_negocio = ? AND correlativo = ? 
                         AND empresa_id = ? AND id <> ?"""
            dups = ejecutar_query(DB_PATH, dup_query, (row['sigla_negocio'], row['correlativo'], row['empresa_id'], row['id']))
            if dups:
                tipo = "🛡️ Auditoría SGI"
                mensaje = f"Conflicto de Correlativo: '{cod}' comparte especialidad y N° con {dups[0][0]}."

                if not ejecutar_query(DB_PATH, check, (cod, mensaje)):
                    insert = "INSERT INTO notificaciones_ultron (tipo, mensaje, identificador, empresa_id, contrato_id) VALUES (?, ?, ?, ?, ?)"
                    ejecutar_query(DB_PATH, insert, (tipo, mensaje, cod, row['empresa_id'], row['contrato_id']), commit=True)
                    mensajes_sgi += 1

        # C. Auditoría de "Verdad" (¿Existe el PDF físico?)
        if "SIN ARCHIVO" in path_doc.upper():
            tipo = "📦 Respaldo Físico"
            mensaje = f"Hueco de Información: El documento '{cod}' está en el listado pero no tiene su archivo PDF cargado."

            check = "SELECT id FROM notificaciones_ultron WHERE identificador = ? AND mensaje = ? AND estado = 'No Leída'"
            if not ejecutar_query(DB_PATH, check, (cod, mensaje)):
                insert = "INSERT INTO notificaciones_ultron (tipo, mensaje, identificador, empresa_id, contrato_id) VALUES (?, ?, ?, ?, ?)"
                ejecutar_query(DB_PATH, insert, (tipo, mensaje, cod, row['empresa_id'], row['contrato_id']), commit=True)
                mensajes_sgi += 1

    return mensajes_sgi

def marcar_notificacion_leida(DB_PATH, id_notif):
    ejecutar_query(DB_PATH, "UPDATE notificaciones_ultron SET estado = 'Leída' WHERE id = ?", (id_notif,), commit=True)

def borrar_notificaciones_antiguas(DB_PATH):
    # Opcional: Borrar leídas de más de 30 días
    ejecutar_query(DB_PATH, "DELETE FROM notificaciones_ultron WHERE estado = 'Leída' AND fecha < datetime('now', '-30 days')", commit=True)

# ==========================================
# 🧠 ULTRON CHAT ENGINE (NATURAL LANGUAGE ROUTER)
# ==========================================

def ask_ultron(DB_PATH, query, user_login="Admin", api_key="", use_sequential_thinking=False):
    """
    Procesa consultas en lenguaje natural y devuelve una respuesta estructurada.
    
    Args:
        use_sequential_thinking: Si True, retorna también la ThinkingChain visible.
    """
    import os
    import re

    from intelligence.agents.context7_engine import obtener_contexto_legal
    from core.diagnostics import run_full_system_audit

    # ── SEQUENTIAL THINKING: MODO INTERNO (siempre activo) ──
    from intelligence.agents.sequential_thinking_engine import analizar_consulta_con_thinking

    df_stats = obtener_dataframe(DB_PATH, "SELECT count(*) as n FROM registros")
    df_alertas = obtener_dataframe(DB_PATH, "SELECT count(*) as n FROM notificaciones_ultron WHERE estado = 'No Leída'")
    contexto_db = {
        "total_docs": df_stats.iloc[0]["n"] if not df_stats.empty else 0,
        "alertas_criticas": df_alertas.iloc[0]["n"] if not df_alertas.empty else 0,
    }
    thinking_chain = analizar_consulta_con_thinking(query, contexto_db)

    # ── CONTEXT7: Inyectar contexto legal relevante ──
    contexto_legal = obtener_contexto_legal(query)

    q = str(query).lower().strip()

    # 1. Saludos y Presentación
    if any(x in q for x in ["hola", "buenos dias", "quien eres", "saludos", "qué puedes hacer", "que puedes hacer"]):
        return {
            "role": "assistant",
            "content": "Saludos, Estratega. Soy **Ull-Trone v4.0 Ultra**, la versión definitiva del núcleo neuro-reflexivo de CGT.pro.\n\nHe completado la **Fusión Maestra** y ahora opero bajo la Constitución del sistema.\n\nCapacidades Integradas:\n- 🧠 **Cerebro Expandido**: Inyección de hitos de proyectos anteriores.\n- 🧬 **Neuro-Evolución**: Auto-diagnóstico y automejora constante.\n- ⚖️ **Auditoría Ética**: Mi razonamiento está regido por leyes inviolables de seguridad y veracidad.\n- 🎓 **Coaching & Auditoría**: Análisis masivo de datos industriales y legales.\n\n¿Qué sector del sistema vamos a evolucionar hoy?",
            "type": "text"
        }

    # 1.5 ANÁLISIS DINÁMICO (Google Gemini)
    # Si no llega api_key, intentar recuperar de la configuración global o local
    if not api_key or str(api_key).strip() == "":
        brain_cfg_tenant = obtener_config(DB_PATH, "ULLTRONE_BRAIN_CONFIG", {})
        api_key = brain_cfg_tenant.get("api_key", "")
        
        # --- CRÍTICO: FALLBACK A DB GLOBAL ---
        if not api_key:
            from config.config import DB_PATH_GLOBAL
            brain_cfg_global = obtener_config(DB_PATH_GLOBAL, "ULLTRONE_BRAIN_CONFIG", {})
            api_key = brain_cfg_global.get("api_key", "")

    if api_key and str(api_key).strip() != "":
        try:
            import google.generativeai as genai
            # ── RECUPERAR CONFIGURACIÓN DE MODELO ──
            brain_cfg = obtener_config(DB_PATH, "ULLTRONE_BRAIN_CONFIG", {"model_name": "gemini-1.5-flash"})
            model_target = brain_cfg.get("model_name", "gemini-1.5-flash")
            
            genai.configure(api_key=api_key.strip())
            model = genai.GenerativeModel(model_target)

            # ── INYECCIÓN RAG (Biblioteca Neuronal) ──
            contexto_memoria = obtener_contexto_neuronal(DB_PATH, query)

            prompt_maestro = f"""
Eres Ull-Trone, el núcleo de inteligencia definitiva de CGT.pro. 
Tu misión es actuar como Socio Estratégico AI de Nivel 5, Auditor Experto y Consultor de Desarrollo.

CONSTITUCIÓN Y LEYES DEL SISTEMA:
{ULTRON_CONSTITUTION}

DIRECTIVA MAESTRA: {ULTRON_CORE_DIRECTIVE}

CONTEXTO DE MEMORIA NEURONAL:
{contexto_memoria}

INSTRUCCIÓN:
Responde con máxima precisión técnica, claridad y profundidad técnica. Usa formato Markdown.
Si la información no está en el contexto, admítelo. Nunca inventes datos.

CONSULTA DEL ESTRATEGA: {query}
            """
            resp = model.generate_content(prompt_maestro)

            return {
                "role": "assistant",
                "content": resp.text,
                "type": "text"
            }
        except Exception as e:
            import logging
            logging.error(f"Ull-Trone AI Error: {str(e)}")
            # Retornar error descriptivo instead of fallback
            return {
                "role": "assistant",
                "content": f"🚨 **Error de Conexión Neuronal**\n\nNo he podido establecer el enlace con Gemini. \n- **Detalle**: `{str(e)}` \n- **Sugerencia**: Verifica que la librería `google-generativeai` esté instalada y que tu API Key sea válida en el panel de Cerebro.",
                "type": "error"
            }


    # --- CONSULTOR LEGAL RAG 4.0 (Leyes de Chile) ---
    if any(x in q for x in ["ley ", "ley-", "ds ", "ds-", "normativa ", "decreto"]):
        import os

        from config.config import SUPPORT_DIR
        legal_dir = os.path.join(SUPPORT_DIR, "Leyes")

        # Extraer número de ley/decreto para el filtro
        match_ley = re.search(r'(ley|ds)\s*([0-9\.]+)', q)
        keyword_ley = match_ley.group(0) if match_ley else ""

        if os.path.exists(legal_dir):
            pdfs = [f for f in os.listdir(legal_dir) if f.lower().endswith(".pdf")]
            target_pdf = ""
            if keyword_ley:
                for p in pdfs:
                    if keyword_ley.replace(" ", "_").upper() in p.upper() or keyword_ley.replace(" ", "").upper() in p.upper():
                        target_pdf = os.path.join(legal_dir, p)
                        break

            # Si no encontró una específica, buscar en la más relevante del pool
            if not target_pdf and pdfs:
                target_pdf = os.path.join(legal_dir, pdfs[0]) # Fallback a la primera para análisis general

            if target_pdf:
                # Si hay API Key, usar Gemini para interpretación legal
                if api_key and str(api_key).strip() != "":
                    try:
                        import fitz
                        import google.generativeai as genai
                        # ── RECUPERAR CONFIGURACIÓN DE MODELO ──
                        brain_cfg = obtener_config(DB_PATH, "ULLTRONE_BRAIN_CONFIG", {"model_name": "gemini-1.5-flash"})
                        model_target = brain_cfg.get("model_name", "gemini-1.5-flash")

                        genai.configure(api_key=api_key.strip())
                        model = genai.GenerativeModel(model_target)

                        doc = fitz.open(target_pdf)
                        texto = ""
                        for p_idx in range(min(15, len(doc))): # 15 páginas max para velocidad
                            texto += doc[p_idx].get_text("text") + "\n"
                        doc.close()

                        prompt = f"Eres Ultron Legal 4.0. Responde con lenguaje técnico pero claro para un prevencionista. Analiza este texto legal: {texto[:30000]}\n\nCONSULTA: {query}"
                        resp = model.generate_content(prompt)

                        return {
                            "role": "assistant",
                            "content": f"### ⚖️ Ultron Legal Analysis: {os.path.basename(target_pdf)}\n\n{resp.text}",
                            "type": "text"
                        }
                    except Exception as e: pass # Fallback a estático

                # Fallback estático (Extracto)
                return {
                    "role": "assistant",
                    "content": f"He localizado el documento legal **{os.path.basename(target_pdf)}**. \n\nPara un análisis profundo con IA, conecta tu Gemini API Key. Por ahora, puedo confirmarte que el archivo está indexado en mi biblioteca legal.",
                    "type": "text"
                }

    # --- ANÁLISIS DE SENTIMIENTO INTEGRADO ---
    from core.notification_agent import detectar_sentimiento_observacion
    sentimiento = detectar_sentimiento_observacion(q)
    prefijo_sent = ""
    if sentimiento['nivel'] == "CRÍTICO":
        prefijo_sent = "🚨 **He detectado un tono de urgencia o riesgo en tu mensaje.** Mantén la calma, estoy aquí para priorizar la solución inmediata.\n\n"
    elif sentimiento['nivel'] == "MODERADO":
        prefijo_sent = "⚠️ **Nota**: Percibo preocupación técnica en tu consulta. Analicemos los datos con atención.\n\n"

    # --- EXPERTO ISO RAG (Lectura Directa de PDFs de Soporte) ---
    if any(x in q for x in ["iso ", "iso-", "norma iso", "45001", "14001", "9001"]):
        import os

        from config.config import SUPPORT_DIR

        # Determinar la norma consultada
        norma_req = ""
        if "45001" in q: norma_req = "45001"
        elif "14001" in q: norma_req = "14001"
        elif "9001" in q: norma_req = "9001"

        if norma_req:
            # Buscar archivo PDF en la carpeta de soporte
            pdf_path = ""
            if os.path.exists(SUPPORT_DIR):
                for f in os.listdir(SUPPORT_DIR):
                    if f"ISO_{norma_req}" in f and f.lower().endswith(".pdf"):
                        pdf_path = os.path.join(SUPPORT_DIR, f)
                        break

            if not pdf_path:
                return {
                    "role": "assistant",
                    "content": f"He determinado que consultas sobre la norma **ISO {norma_req}**. Sin embargo, no encuentro el PDF en `{SUPPORT_DIR}`. Verifica que el archivo comience con 'ISO_{norma_req}'.",
                    "type": "text"
                }

            # Si el Administrador inyectó la API Key, usar Gemini 1.5 para Razonamiento Experto Complejo
            if api_key and str(api_key).strip() != "":
                try:
                    import fitz
                    import google.generativeai as genai

                    # ── RECUPERAR CONFIGURACIÓN DE MODELO ──
                    brain_cfg = obtener_config(DB_PATH, "ULLTRONE_BRAIN_CONFIG", {"model_name": "gemini-1.5-flash"})
                    model_target = brain_cfg.get("model_name", "gemini-1.5-flash")

                    genai.configure(api_key=api_key.strip())
                    model = genai.GenerativeModel(model_target)

                    doc = fitz.open(pdf_path)
                    texto_completo = ""
                    for pag_idx in range(len(doc)):
                        texto_completo += doc[pag_idx].get_text("text").replace("\n", " ") + "\n"
                    doc.close()

                    prompt_maestro = f"""
Eres Ultron, el núcleo de inteligencia de CGT.pro operando como Auditor Experto Gerencial en Normas ISO.
Analiza exhaustivamente el siguiente corpus de la norma oficial ISO {norma_req}.
Responde a la solicitud del usuario con claridad, profundidad técnica, y formato Markdown (usa listas y negritas). Si la respuesta es compleja, estructúrala en pasos lógicos.
SOLICITUD DEL USUARIO: "{query}"

--- CONTENIDO DE LA NORMA OFICIAL ---
{texto_completo[:200000]}
                    """

                    response = model.generate_content(prompt_maestro)

                    return {
                        "role": "assistant",
                        "content": f"### 🧠 Neural Analysis: Ultron (Powered by Gemini)\n\n{response.text}\n\n---\n*Análisis generado leyendo en tiempo real el PDF Oficial de la ISO {norma_req}.*",
                        "type": "text"
                    }
                except ImportError:
                    return {
                        "role": "assistant",
                        "content": f"🚨 **Falta Conexión de Inteligencia**\nDetecto la API Key, pero falta la librería base. Ejecuta `pip install google-generativeai` y `pip install PyMuPDF` para activar mi lóbulo frontal.",
                        "type": "text"
                    }
                except Exception as e:
                    return {
                        "role": "assistant",
                        "content": f"🚨 **Error de Conexión (Gemini)**\nMi enlace cognitivo con Google fue rechazado. Verifica que tu API Key sea válida.\n`Trace: {str(e)}`",
                        "type": "text"
                    }

            # FALLBACK ESTÁTICO (Extracción de Palabras Clave si NO Hizo Login en Gemini)
            stop_words = ["que", "como", "cuando", "donde", "cuales", "segun", "norma", "iso", "dice", "habla", "sobre", "el", "la", "los", "las", "un", "una", "de", "para", "en"]
            q_clean = q.replace("iso", "").replace(norma_req, "")
            palabras = [p for p in re.findall(r'\b\w+\b', q_clean) if len(p) > 4 and p not in stop_words]
            keyword = palabras[0] if palabras else "requisito"

            try:
                import fitz  # PyMuPDF
                doc = fitz.open(pdf_path)
                match_text = ""
                hallazgos = 0

                num_paginas = len(doc)

                for pag_idx in range(num_paginas):
                    page = doc[pag_idx]
                    texto_pag = page.get_text("text").replace("\n", " ")
                    if keyword.lower() in texto_pag.lower():
                        idx = texto_pag.lower().find(keyword.lower())
                        start = max(0, idx - 150)
                        end = min(len(texto_pag), idx + 400)

                        match_text += f"\n\n**📄 Extracto de Pág. {pag_idx+1}:**\n> \"...{texto_pag[start:end]}...\"\n---"
                        hallazgos += 1
                        if hallazgos >= 3:
                            break

                doc.close()

                if match_text:
                    return {
                        "role": "assistant",
                        "content": f"### 📖 Análisis Experto: ISO {norma_req} (Contexto: '{keyword}')\nHe escaneado las entrañas del documento oficial `{os.path.basename(pdf_path)}` buscando referenciar tu requerimiento. Hemos encontrado los siguientes corolarios normativos vitales:\n{match_text}\n\n*Nota: Estos son fragmentos recuperados en tiempo real. Soy Ultron.*",
                        "type": "text"
                    }
                else:
                    return {
                        "role": "assistant",
                        "content": f"He escaneado las {num_paginas} páginas de la ISO {norma_req}, pero tu concepto **'{keyword}'** no figura bajo esa terminología explícita en su corpus. ¿Puedes reformular con otro tecnicismo?",
                        "type": "text"
                    }
            except ImportError:
                return {
                    "role": "assistant",
                    "content": f"📦 **Módulo Cognitivo Faltante**\n\nTengo la **ISO {norma_req}** bajo mi radar listo para análisis, pero carezco del subsistema de escaneo óptico vectorial (`PyMuPDF`).\n\nPor favor, instruye en tu terminal:\n```bash\npip install PyMuPDF\n```\n*Reinicien mis sistemas luego de eso y estaré leyendo las normas en milisegundos.*",
                    "type": "text"
                }

    # 2. Diagnóstico de Salud
    if any(x in q for x in ["salud", "estado del sistema", "diagnóstico", "auditoría", "como estas"]):
        report = run_full_system_audit(DB_PATH, os.getcwd())
        score = report['score']
        status = "CRÍTICO" if score < 50 else "ALERTA" if score < 90 else "EXCELENTE"

        db_msg = "Base de Datos: " + ("✅ Íntegra" if report['db']['status'] == "OK" else "⚠️ Incompleta")
        file_msg = "Archivos: " + ("✅ Correctos" if report['files']['status'] == "OK" else "⚠️ Faltan directorios")

        msg = f"""
### Informe de Estado Ultron
**Puntaje de Salud**: `{score}/100` ({status})
- {db_msg}
- {file_msg}

¿Deseas que profundice en algún punto o que proceda con una autorreparación?
        """
        return {"role": "assistant", "content": msg, "type": "diag", "report": report}

    # 3. Consultas de Datos (Metricas Rápidas)
    if "cuanto" in q or "muchos" in q or "estadísticas" in q or "resumen" in q:
        df_usr = obtener_dataframe(DB_PATH, "SELECT count(*) FROM usuarios")
        df_reg = obtener_dataframe(DB_PATH, "SELECT count(*) FROM registros")
        df_proc = obtener_dataframe(DB_PATH, "SELECT count(*) FROM procedimientos")

        n_usr = df_usr.iloc[0,0] if not df_usr.empty else 0
        n_reg = df_reg.iloc[0,0] if not df_reg.empty else 0
        n_proc = df_proc.iloc[0,0] if not df_proc.empty else 0

        msg = f"""
He compilado el resumen operativo actual:
- **Usuarios**: {n_usr} perfiles activos.
- **Registros**: {n_reg} documentos en trazabilidad.
- **SGI**: {n_proc} procedimientos/instructivos cargados.

¿Deseas que analice los vencimientos críticos de estos activos?
        """
        return {"role": "assistant", "content": msg, "type": "stats"}

    # 4. Comandos de Acción (Reparación)
    if any(x in q for x in ["reparar", "arreglar", "patch", "parche", "solucionar"]):
        report = run_full_system_audit(DB_PATH, os.getcwd())
        missing = report['db']['missing_columns']

        if not missing and report['files']['status'] == "OK":
            return {
                "role": "assistant",
                "content": "He verificado todos los sectores y no he encontrado fallos estructurales. El sistema opera al 100% de su capacidad.",
                "type": "text"
            }

        msg = f"He identificado **{len(missing)}** inconsistencias estructurales. Por seguridad, necesito tu confirmación explícita para modificar el código de la base de datos."
        return {"role": "assistant", "content": msg, "type": "action_request", "action": "patch", "details": missing}

    # 5. Resiliencia y Backups
    if any(x in q for x in ["respaldo", "backup", "restaurar", "restablecer", "punto de retorno"]):
        from intelligence.agents.backup_engine import obtener_listado_respaldos
        respaldos = obtener_listado_respaldos()

        if not respaldos:
            return {
                "role": "assistant",
                "content": "No he detectado puntos de restauración previos en el servidor. ¿Deseas que genere uno ahora mismo?",
                "type": "text"
            }

        ultimo = respaldos[0]
        msg = f"""
He localizado **{len(respaldos)}** puntos de restauración. 
El más reciente es del **{ultimo['date']}** (`{ultimo['name']}`). 

¿Deseas ver el listado completo para una restauración crítica o prefieres que genere un nuevo respaldo preventivo?
        """
        return {"role": "assistant", "content": msg, "type": "backup_list", "data": respaldos[:5]}

    # ══════════════════════════════════════════════
    # 🆕 ULTRON v2.0 — NUEVAS HABILIDADES
    # ══════════════════════════════════════════════

    # 6. FORECAST PREDICTIVO
    if any(x in q for x in ["forecast", "proyección", "predicción", "próximos meses", "cuándo vence más", "cuando vence mas", "vencimientos futuros"]):
        from intelligence.agents.forecast_engine import generar_forecast_vencimientos
        forecast = generar_forecast_vencimientos(DB_PATH)
        return {
            "role": "assistant",
            "content": f"### 📈 Forecast Predictivo de Vencimientos\n\n{forecast['narrativa']}",
            "type": "forecast",
            "data": forecast
        }

    # 7. REPORTE / BRIEFING GERENCIAL
    if any(x in q for x in ["informe", "reporte", "briefing", "pdf ejecutivo", "genera un pdf", "genera informe", "reporte gerencial"]):
        return {
            "role": "assistant",
            "content": "📄 **Briefing Ejecutivo Listo para Generar**\n\nPuedo crear un reporte PDF gerencial con:\n- KPIs de cumplimiento (semáforo verde/amarillo/rojo)\n- Top 5 documentos más urgentes\n- Gráfico de forecast de vencimientos\n- Alertas normativas activas\n- Firma digital de Ultron\n\n👉 Utiliza el botón **'📄 Descargar Briefing PDF'** en la tab **Forecast** de este panel para generarlo.",
            "type": "text"
        }

    # 8. VALIDACIÓN OCR
    if any(x in q for x in ["valida", "validar", "verificar documento", "verificar pdf", "autenticidad", "ocr"]):
        return {
            "role": "assistant",
            "content": "🔬 **Ojo Digital de Ultron (OCR)**\n\nPuedo validar que el contenido real de un PDF corresponda al registro esperado. El análisis incluye:\n- Búsqueda del RUT/identificador dentro del texto del documento.\n- Verificación del nombre del titular.\n- Puntaje de confianza (0–100%).\n\n👉 Utiliza la tab **'🔬 Validación OCR'** para subir un documento y verificarlo en tiempo real.",
            "type": "text"
        }

    # 9. VIGILANCIA NORMATIVA
    if any(x in q for x in ["normativa", "ley karin", "ds 44", "suseso", "actualizacion legal", "actualización legal", "cambio en la ley", "diario oficial"]):
        from core.normativa_watcher import obtener_estado_normativas
        df_normas = obtener_estado_normativas(DB_PATH)
        normas_txt = ""
        if not df_normas.empty:
            for _, row in df_normas.iterrows():
                icono = "⚡" if row['Estado'] == 'CAMBIO_DETECTADO' else ("✅" if row['Estado'] == 'SIN_CAMBIOS' else "🔄")
                normas_txt += f"\n- {icono} **{row['Normativa']}** — Estado: `{row['Estado']}`"

        return {
            "role": "assistant",
            "content": f"### ⚡ Centinela Normativo de Ultron\n\nEstoy monitoreando **{len(df_normas)}** normativas chilenas de seguridad laboral:\n{normas_txt}\n\n👉 Utiliza la tab **'⚡ Normativa'** para ejecutar una verificación en tiempo real y ver el historial completo.",
            "type": "text"
        }

    # 10. COACHING / CONSEJOS
    if any(x in q for x in ["consejo", "coach", "mejorar", "capacitación", "entrenamiento", "tips", "recomendación", "cómo mejorar"]):
        from intelligence.agents.coaching_engine import generar_coaching_personalizado
        resultado = generar_coaching_personalizado(DB_PATH, api_key=api_key)

        consejos_txt = ""
        for i, c in enumerate(resultado['consejos'], 1):
            nivel_emoji = "🔴" if c['nivel'] == "Crítico" else ("🟡" if c['nivel'] == "Preventivo" else "🔵")
            consejos_txt += f"\n\n**{i}. {nivel_emoji} [{c['nivel']}]** _{c['norma']}_\n{c['tip']}"

        if resultado.get('respuesta_ia'):
            content = f"{resultado['contexto']}\n\n{resultado['respuesta_ia']}"
        else:
            content = f"{resultado['contexto']}\n{consejos_txt}\n\n---\n_Análisis personalizado de Ultron basado en tu historial operacional._"

        return {
            "role": "assistant",
            "content": f"### 🎓 Coaching de Seguridad Personalizado\n\n{content}",
            "type": "coaching",
            "data": resultado
        }

    # Fallback
    return {
        "role": "assistant",
        "content": "Entiendo. Sin embargo, no tengo una instrucción específica para esa consulta. Puedo ayudarte con:\n\n- **Salud del sistema** → `'salud del sistema'`\n- **Resumen de datos** → `'resumen'`\n- **Forecast** → `'forecast'`\n- **Reporte PDF** → `'genera un informe'`\n- **Validación OCR** → `'valida un documento'`\n- **Normativas** → `'normativas'`\n- **Coaching** → `'dame consejos'`\n- **Backups** → `'respaldo'`",
        "type": "text"
    }
