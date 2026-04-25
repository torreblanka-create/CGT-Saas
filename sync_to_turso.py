# -*- coding: utf-8 -*-
"""
Sincronizar datos LOCALES -> Turso Cloud
Ejecutar: python sync_to_turso.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
os.chdir(os.path.dirname(__file__))

# ⚠️ ATENCIÓN: Las credenciales deben estar en variables de entorno, NO hardcodeadas.
# 
# Antes de ejecutar, asegúrate de tener estas variables definidas:
#   set LIBSQL_DB_URL=libsql://cgt-saas-prod-tu-org.turso.io
#   set LIBSQL_DB_AUTH_TOKEN=eyJ...
#
# O crea un archivo .env con:
#   LIBSQL_DB_URL=libsql://cgt-saas-prod-tu-org.turso.io
#   LIBSQL_DB_AUTH_TOKEN=eyJ...
#
# El token actual caduca: 2026-04-24 (exp:1777180501)
# Si caduca, genera uno nuevo en: https://console.turso.io

# Cargar .env local si existe (opcional, no crítico)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv no instalado, confiar en vars de entorno del sistema

# Si no hay variables de entorno, forzar sincronización local
if not os.getenv("LIBSQL_DB_URL") or not os.getenv("LIBSQL_DB_AUTH_TOKEN"):
    print("[WARN] LIBSQL_DB_URL o LIBSQL_DB_AUTH_TOKEN no están definidos.")
    print("[WARN] Usando modo 'local' (sin sincronización Turso).")
    os.environ['TURSO_ENV'] = 'local'
else:
    os.environ['TURSO_ENV'] = 'sync'

from src.infrastructure.turso_adapter import get_turso_connection
import sqlite3

os.environ["PYTHONIOENCODING"] = "utf-8"

db_path = os.path.join(".", "cgt_control.db")
print(f"[DB] Local: {db_path}")
print(f"[DB] Existe: {os.path.exists(db_path)}")
print(f"[DB] Tamano: {os.path.getsize(db_path) if os.path.exists(db_path) else 0} bytes")

conn_local = sqlite3.connect(db_path)
cursor = conn_local.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
tables = [row[0] for row in cursor.fetchall()]
print(f"[TABLES] {tables}")

if not tables:
    print("[ERROR] No hay tablas en la base local.")
    conn_local.close()
    exit(1)

print("[SYNC] Conectando a Turso Cloud (sync mode)...")
try:
    with get_turso_connection(db_path) as conn:
        print("[OK] Conectado a Turso! (pull inicial completado)")

        for table in tables:
            cursor.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{table}'")
            create_sql = cursor.fetchone()
            if create_sql and create_sql[0]:
                try:
                    conn.execute(create_sql[0])
                    print(f"[OK] Tabla '{table}' verificada/creada")
                except Exception as e:
                    if "already exists" in str(e):
                        print(f"[OK] Tabla '{table}' ya existe")
                    else:
                        print(f"[WARN] {table}: {e}")

        for table in tables:
            cursor.execute(f"SELECT * FROM '{table}'")
            rows = cursor.fetchall()
            col_names = [desc[0] for desc in cursor.description]

            if rows:
                placeholders = ",".join(["?" for _ in col_names])
                cols = ",".join(col_names)
                conn.execute(f"DELETE FROM '{table}'")
                for row in rows:
                    conn.execute(f"INSERT INTO '{table}' ({cols}) VALUES ({placeholders})", row)
                print(f"[OK] {table}: {len(rows)} registros -> Turso Cloud")
            else:
                print(f"[OK] {table}: sin datos")

        conn.commit()
        print()
        print("=" * 50)
        print("SINCRONIZACION COMPLETADA!")
        print("=" * 50)
        print("Tus datos locales AHORA estan en Turso Cloud.")
        print("La app en Streamlit Cloud los vera tras el reboot.")

except Exception as e:
    print(f"\n[ERROR] {e}")
    import traceback
    traceback.print_exc()

conn_local.close()
