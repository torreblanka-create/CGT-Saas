"""
conftest.py — fuerza TURSO_ENV=local para todos los tests.
Debe ejecutarse ANTES de cualquier import de database/turso_adapter,
ya que load_dotenv() no sobreescribe variables ya establecidas.
"""
import os

# Forzar modo local — previene turso_pull() durante la recolección de tests
os.environ["TURSO_ENV"] = "local"
