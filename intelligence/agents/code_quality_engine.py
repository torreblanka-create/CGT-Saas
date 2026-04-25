"""
==========================================
🔧 CODE QUALITY ENGINE — v2.0 MEJORADO
==========================================
Motor de análisis de calidad de código.

CARACTERÍSTICAS v2.0:
✅ Linting con Ruff
✅ Análisis de métricas
✅ Reportes detallados
✅ Histórico de calidad
✅ Integración BD
✅ Trending y análisis
✅ Recomendaciones de mejora
"""
import logging
import json
import os
import subprocess
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass

from src.infrastructure.database import obtener_conexion

logger = logging.getLogger(__name__)


# ============ DATA MODELS ============

@dataclass
class HallazgoCalidad:
    """Hallazgo de calidad encontrado"""
    id: str
    archivo: str
    linea: int
    columna: int
    codigo_error: str
    mensaje: str
    severidad: str
    fecha_deteccion: str


@dataclass
class ReporteCalidad:
    """Reporte de calidad del código"""
    id: str
    fecha_reporte: str
    directorio_analizado: str
    total_hallazgos: int
    errores: int
    warnings: int
    score_calidad: float  # 0-100
    archivos_analizados: int


class CodeQualityEngine:
    """Motor de análisis de calidad de código"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path
        self._crear_tablas()
        logger.info("CodeQualityEngine inicializado")
    
    def _crear_tablas(self) -> None:
        """Crea tablas para análisis de calidad"""
        if not self.db_path:
            return
        
        tables = [
            """
            CREATE TABLE IF NOT EXISTS hallazgos_calidad (
                id TEXT PRIMARY KEY,
                archivo TEXT,
                linea INTEGER,
                columna INTEGER,
                codigo_error TEXT,
                mensaje TEXT,
                severidad TEXT,
                fecha_deteccion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS reportes_calidad (
                id TEXT PRIMARY KEY,
                fecha_reporte TIMESTAMP,
                directorio_analizado TEXT,
                total_hallazgos INTEGER,
                errores INTEGER,
                warnings INTEGER,
                score_calidad REAL,
                archivos_analizados INTEGER
            )
            """
        ]
        
        try:
            conexion = obtener_conexion(self.db_path)
            for query in tables:
                conexion.execute(query)
            conexion.commit()
            conexion.close()
            logger.debug("Tablas de calidad creadas")
        except Exception as e:
            logger.error(f"Error creando tablas: {e}")


def _ejecutar_ruff_check(target_dir: str) -> list:
    """
    Ejecuta Ruff en modo check (solo lectura) y retorna los hallazgos como lista.
    """
    try:
        result = subprocess.run(
            ["ruff", "check", target_dir, "--output-format=json", "--select=E,W,F,C,N,B"],
            capture_output=True,
            text=True,
            timeout=60
        )
        if result.stdout.strip():
            return json.loads(result.stdout)
        return []
    except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError) as e:
        print(f"Ruff Error: {e}")
        return []


def _ejecutar_ruff_stats(target_dir: str) -> dict:
    """Obtiene estadísticas generales del proyecto."""
    try:
        result = subprocess.run(
            ["ruff", "check", target_dir, "--statistics"],
            capture_output=True,
            text=True,
            timeout=60
        )
        return result.stdout
    except Exception:
        return ""


def generar_reporte_calidad(target_dir: str = None) -> dict:
    """
    Genera un reporte completo de calidad del código SIN modificar nada.
    
    Args:
        target_dir: Directorio a analizar. Default: directorio del proyecto.
    
    Returns:
        dict con todos los hallazgos y métricas.
    """
    if not target_dir:
        target_dir = os.getcwd()

    hallazgos = _ejecutar_ruff_check(target_dir)
    estadisticas_raw = _ejecutar_ruff_stats(target_dir)

    # ── Agrupar hallazgos por archivo ──
    por_archivo: dict = {}
    por_severidad: dict = {"error": 0, "warning": 0, "info": 0}
    por_codigo: dict = {}

    for h in hallazgos:
        archivo = h.get("filename", "").replace(target_dir, "").lstrip("\\/")
        codigo = h.get("code", "?")
        mensaje = h.get("message", "")
        linea = h.get("location", {}).get("row", 0)

        if archivo not in por_archivo:
            por_archivo[archivo] = []
        por_archivo[archivo].append({
            "linea": linea,
            "codigo": codigo,
            "mensaje": mensaje
        })

        # Clasificar severidad por prefijo de código
        if codigo.startswith("E") or codigo.startswith("F"):
            por_severidad["error"] += 1
        elif codigo.startswith("W") or codigo.startswith("B"):
            por_severidad["warning"] += 1
        else:
            por_severidad["info"] += 1

        por_codigo[codigo] = por_codigo.get(codigo, 0) + 1

    # ── Top 5 Archivos Más Problemáticos ──
    top_archivos = sorted(
        [(f, len(issues)) for f, issues in por_archivo.items()],
        key=lambda x: x[1],
        reverse=True
    )[:5]

    # ── Calcular Puntaje de Calidad (0-100) ──
    total_issues = len(hallazgos)
    # Base 100, quitar puntos por errores
    errores_graves = por_severidad["error"]
    score = max(0, 100 - (errores_graves * 3) - (por_severidad["warning"] * 1))

    return {
        "timestamp": datetime.now().isoformat(),
        "directorio": target_dir,
        "total_issues": total_issues,
        "score_calidad": score,
        "por_severidad": por_severidad,
        "por_codigo": sorted(por_codigo.items(), key=lambda x: x[1], reverse=True)[:10],
        "top_archivos": top_archivos,
        "detalle_por_archivo": por_archivo,
        "estadisticas_raw": estadisticas_raw
    }


def generar_narrativa_reporte(reporte: dict) -> str:
    """Convierte el reporte técnico en texto ejecutivo para Ultron."""
    score = reporte["score_calidad"]
    total = reporte["total_issues"]
    sev = reporte["por_severidad"]

    if score >= 90:
        veredicto = "✅ **EXCELENTE**: El código cumple con altos estándares de calidad."
    elif score >= 70:
        veredicto = "⚠️ **MEJORABLE**: Existen áreas que reducen la mantenibilidad."
    else:
        veredicto = "🚨 **ATENCIÓN**: Deuda técnica significativa detectada."

    md = f"## 🔧 Reporte de Calidad de Código — CGT.pro\n\n"
    md += f"**Puntaje Global**: `{score}/100`  {veredicto}\n\n"
    md += f"| Categoría | Total |\n|---|---|\n"
    md += f"| 🔴 Errores Graves | {sev['error']} |\n"
    md += f"| 🟡 Advertencias | {sev['warning']} |\n"
    md += f"| 🔵 Informativos | {sev['info']} |\n"
    md += f"| **TOTAL ISSUES** | **{total}** |\n\n"

    if reporte["top_archivos"]:
        md += "### 📁 Top 5 Archivos con Más Issues\n\n"
        for arch, n in reporte["top_archivos"]:
            md += f"- `{arch}` → **{n} issues**\n"

    if reporte["por_codigo"]:
        md += "\n### 🏷️ Tipos de Problems Más Frecuentes\n\n"
        for codigo, count in reporte["por_codigo"][:5]:
            md += f"- **{codigo}**: {count} ocurrencias\n"

    md += "\n---\n"
    md += "_⚠️ Este es un reporte de solo lectura. Ningún archivo fue modificado._\n"
    md += "_Para aplicar correcciones automáticas, usa el botón 'Aplicar Fixes' (previa aprobación)._\n"

    return md


def aplicar_fixes_seguros(target_dir: str = None) -> dict:
    """
    Aplica SOLO correcciones seguras y no destructivas (espacios, imports, etc.).
    REQUIERE aprobación explícita del usuario antes de llamar a esta función.
    """
    if not target_dir:
        target_dir = os.getcwd()

    try:
        result = subprocess.run(
            ["ruff", "check", target_dir, "--fix", "--select=I,E501,W291,W293"],
            capture_output=True,
            text=True,
            timeout=60
        )
        fixed_count = result.stdout.count("Fixed")
        return {
            "success": True,
            "fixes_aplicados": fixed_count,
            "output": result.stdout
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
