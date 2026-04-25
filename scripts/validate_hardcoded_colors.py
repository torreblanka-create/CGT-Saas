#!/usr/bin/env python3
"""
VALIDADOR DE ESTILOS - CGT
==========================
Detecta colores hardcodeados en archivos Python y alerta al desarrollador.

Uso:
    python scripts/validate_hardcoded_colors.py        # Escanea todo
    python scripts/validate_hardcoded_colors.py vistas # Escanea carpeta
"""

import re
import sys
from pathlib import Path
from typing import List, Tuple

# Patrones de colores a detectar (colores "atrapados")
COLOR_PATTERNS = [
    r"#[0-9a-fA-F]{6}",              # Colores hex: #RRGGBB
    r"#[0-9a-fA-F]{3}",              # Colores hex cortos: #RGB
    r"rgba?\([^)]*\)",               # rgba() y rgb()
]

# Colores PERMITIDOS (del sistema de temas)
ALLOWED_COLORS = {
    # Colores de themes.py
    "#F5F3F0",      # BACKGROUND_PRIMARY
    "#FAF8F6",      # BACKGROUND_SECONDARY
    "#faf8f6",      # BACKGROUND_HOVER
    "#1F2937",      # TEXT_PRIMARY
    "#4B5563",      # TEXT_SECONDARY
    "#6b7280",      # TEXT_TERTIARY
    "#9ca3af",      # TEXT_LIGHT
    "#d4d4d8",      # BORDER_COLOR
    "#e5e7eb",      # BORDER_COLOR_LIGHT
    "#ef4444",      # COLOR_ROJO
    "#f59e0b",      # COLOR_NARANJA
    "#10b981",      # COLOR_VERDE
    "#3b82f6",      # COLOR_AZUL
    "#a855f7",      # COLOR_MORADO
    "#06b6d4",      # COLOR_CIAN
    "#dc2626",      # TEXT_ROJO
    "#b45309",      # TEXT_NARANJA
    "#047857",      # TEXT_VERDE
    "#1e40af",      # TEXT_AZUL
    "#7c3aed",      # TEXT_MORADO
}

# Archivos/patrones a IGNORAR
IGNORE_PATTERNS = [
    "themes.py",              # El archivo de temas en sí
    "custom.css",             # CSS global
    "test_",                  # Tests
    "__pycache__",
    ".git",
    "node_modules",
    "ESTANDARES_TEMAS.md",   # Documentación
]

# Colores IGNORABLES (sombras, opacidades, etc.)
IGNORE_RGBA = [
    "rgba(0,0,0,",           # Sombras negras
    "rgba(255,255,255,",     # Sombras blancas
    "rgba(0, 0, 0,",         # Versión con espacios
    "rgba(255, 255, 255,",
]


def is_ignored_file(filepath: str) -> bool:
    """Verifica si un archivo debe ser ignorado"""
    for pattern in IGNORE_PATTERNS:
        if pattern in filepath:
            return True
    return False


def is_forbidden_color(color: str) -> bool:
    """Verifica si un color es 'malo' (no debería estar hardcodeado)"""
    color_clean = color.lower().strip()
    
    # Colores muy oscuros (problema original)
    dark_colors = {
        "#1e293b", "#0f172a", "#111827", "#1a1a1a", "#1e2227",
        "#000", "#000000", "#001219", "#002535", "#0a3161",
        "#0e4aa0", "#101214", "#2d333b", "#252a30",
    }
    
    if color_clean in dark_colors:
        return True
    
    # Si está en ALLOWED_COLORS, no es forbidden
    if color_clean in {c.lower() for c in ALLOWED_COLORS}:
        return False
    
    # RGBA que son sombras (permitidas)
    for ignore_rgba in IGNORE_RGBA:
        if color_clean.startswith(ignore_rgba.lower()):
            return False
    
    return True


def scan_file(filepath: Path) -> List[Tuple[int, str, str]]:
    """
    Escanea un archivo y retorna lista de (línea, color, contexto)
    """
    issues = []
    
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
    except Exception as e:
        print(f"⚠️  Error leyendo {filepath}: {e}")
        return issues
    
    for line_num, line in enumerate(lines, 1):
        # Saltarse comments
        if line.strip().startswith('#') or line.strip().startswith('//'):
            continue
        
        # Buscar colores
        for pattern in COLOR_PATTERNS:
            matches = re.finditer(pattern, line)
            for match in matches:
                color = match.group()
                
                # Si es un color "malo", reportar
                if is_forbidden_color(color):
                    context = line.strip()[:80]
                    issues.append((line_num, color, context))
    
    return issues


def main():
    workspace_root = Path(__file__).parent.parent
    
    # Determinar qué carpeta escanear
    if len(sys.argv) > 1:
        target = sys.argv[1]
        scan_path = workspace_root / target
    else:
        scan_path = workspace_root / "vistas"
    
    print(f"\n🔍 Escaneando colores hardcodeados en: {scan_path}\n")
    print("="*70)
    
    total_issues = 0
    
    # Escanear archivos
    for filepath in scan_path.rglob("*.py"):
        if is_ignored_file(str(filepath)):
            continue
        
        issues = scan_file(filepath)
        
        if issues:
            total_issues += len(issues)
            print(f"\n⚠️  {filepath.relative_to(workspace_root)}")
            print(f"   Encontrados {len(issues)} color(es) hardcodeado(s):\n")
            
            for line_num, color, context in issues:
                print(f"   Línea {line_num:4d}: {color:12s} | {context}")
    
    print("\n" + "="*70)
    
    if total_issues == 0:
        print("✅ ¡Excelente! No se encontraron colores hardcodeados.")
        print("\n💡 Tu código sigue los estándares de temas centralizados.")
    else:
        print(f"\n❌ Se encontraron {total_issues} problema(s).")
        print("\n💡 CÓMO ARREGLARLO:")
        print("   1. Importa desde config.themes:")
        print("      from config.themes import BACKGROUND_PRIMARY, TEXT_PRIMARY, etc")
        print("\n   2. Reemplaza colores hardcodeados:")
        print("      ❌ background: #1e293b;")
        print("      ✅ background: {BACKGROUND_PRIMARY};")
        print("\n   3. Re-ejecuta este script para validar:")
        print("      python scripts/validate_hardcoded_colors.py\n")
    
    return 0 if total_issues == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
