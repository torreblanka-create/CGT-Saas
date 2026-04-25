import sys
import os

# Add the root directory to sys.path so we can import core
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.utils import normalizar_nombre, normalizar_rut

def test_normalizar_nombre():
    """Test the name normalization function."""
    assert normalizar_nombre("JUAN PEREZ") == "Juan Perez"
    assert normalizar_nombre("  maria lopez  ") == "Maria Lopez"
    assert normalizar_nombre("JOSÉ MARTÍNEZ") == "Jose Martinez"
    assert normalizar_nombre("") == ""
    assert normalizar_nombre(None) == ""

def test_normalizar_rut():
    """Test the RUT normalization function."""
    assert normalizar_rut(" 12.345.678 - 9 ") == "12345678-9"
    assert normalizar_rut("123456789") == "12345678-9"
    assert normalizar_rut("12345678-k") == "12345678-K"
    assert normalizar_rut("") == ""
