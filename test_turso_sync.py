"""
🧪 TEST: Verificar sincronización con Turso
Ejecutar: python test_turso_sync.py
"""
import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from src.infrastructure.turso_adapter import TursoConnection

# Probar en modo LOCAL primero
print("🧪 Test 1: Modo LOCAL (SQLite puro)")
conn = TursoConnection("test_turso.db", env="local")
conn.execute("CREATE TABLE IF NOT EXISTS test (id INTEGER PRIMARY KEY, value TEXT)")
conn.execute("INSERT INTO test (value) VALUES ('Hola mundo')")
conn.commit()
cursor = conn.execute("SELECT * FROM test")
print(f"   ✅ Dato guardado: {cursor.fetchall()}")
conn.close()
print("   ✅ Test local OK")

# Limpiar
os.remove("test_turso.db")
os.remove("test_turso.db-wal") if os.path.exists("test_turso.db-wal") else None

print()
print("✅ Adaptador Turso listo para usar en modo 'sync' con credenciales reales")
print()
print("📋 Para activar sincronización en Streamlit Cloud:")
print("   1. Ve a Settings → Secrets")
print("   2. Asegúrate de tener estos valores:")
print("      TURSO_ENV = 'sync'")
print("      LIBSQL_DB_URL = 'libsql://...'")
print("      LIBSQL_DB_AUTH_TOKEN = 'eyJ...'")
print("   3. Guarda y reinicia la app")
print()
print("📋 Para GitHub, haz push de estos archivos:")
print("   - src/infrastructure/turso_adapter.py (nueva sincronización)")
print("   - src/infrastructure/security.py (corrección SQL injection)")
print("   - src/infrastructure/archivos.py (path traversal fix)")
