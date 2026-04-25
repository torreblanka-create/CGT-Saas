# -*- coding: utf-8 -*-
"""
Sincronizar datos LOCALES -> Turso Cloud
Usa la API HTTP de Turso (sin libsql_client async).
Ejecutar: python sync_to_turso.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__) or ".")
os.chdir(os.path.dirname(os.path.abspath(__file__)))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

LIBSQL_DB_URL = os.getenv("LIBSQL_DB_URL", "")
LIBSQL_DB_AUTH_TOKEN = os.getenv("LIBSQL_DB_AUTH_TOKEN", "")

if not LIBSQL_DB_URL or not LIBSQL_DB_AUTH_TOKEN:
    print("[WARN] LIBSQL_DB_URL o LIBSQL_DB_AUTH_TOKEN no definidos.")
    print("[WARN] Configura .env y vuelve a ejecutar.")
    sys.exit(1)

os.environ["TURSO_ENV"] = "sync"

from src.infrastructure.turso_adapter import turso_push, _turso_http_url, _turso_execute

import sqlite3

os.environ["PYTHONIOENCODING"] = "utf-8"

# BD real con todos los datos
db_path = os.path.join(".", "CGT_DATA", "cgt_control.db")
print(f"[DB] {db_path}")
print(f"[DB] Existe: {os.path.exists(db_path)}")
print(f"[DB] Tamano: {os.path.getsize(db_path) if os.path.exists(db_path) else 0} bytes")

if not os.path.exists(db_path):
    print("[ERROR] No se encontro la base de datos local.")
    sys.exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
tables = [r[0] for r in cursor.fetchall()]
conn.close()
print(f"[TABLES] {len(tables)} tablas encontradas")

http_url = _turso_http_url(LIBSQL_DB_URL)
token = LIBSQL_DB_AUTH_TOKEN

print("\n[SYNC] Verificando conexion a Turso Cloud...")
try:
    result = _turso_execute(http_url, token, [
        {"type": "execute", "stmt": {"sql": "SELECT 1 as ping"}}
    ])
    print("[OK] Conectado a Turso Cloud!")
except Exception as e:
    print(f"[ERROR] No se pudo conectar a Turso: {e}")
    sys.exit(1)

print("\n[SYNC] Iniciando sincronizacion...")

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row

synced = 0
skipped = 0

for table in tables:
    try:
        # 1. Crear tabla en Turso si no existe
        schema = conn.execute(
            f"SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table,)
        ).fetchone()
        if schema and schema[0]:
            try:
                _turso_execute(http_url, token, [
                    {"type": "execute", "stmt": {"sql": schema[0]}}
                ])
            except Exception:
                pass  # ya existe

        # 2. Leer datos locales
        cursor = conn.execute(f'SELECT * FROM "{table}"')
        rows = cursor.fetchall()
        cols = [d[0] for d in cursor.description]

        if not rows:
            print(f"  [--] {table}: sin datos")
            continue

        # 3. DELETE primero
        col_names = ", ".join(f'"{c}"' for c in cols)
        placeholders = ", ".join(["?" for _ in cols])
        insert_sql = f'INSERT OR REPLACE INTO "{table}" ({col_names}) VALUES ({placeholders})'

        _turso_execute(http_url, token, [
            {"type": "execute", "stmt": {"sql": f'DELETE FROM "{table}"'}}
        ])

        # 4. INSERTs en chunks de 50 para evitar límite de Turso
        CHUNK = 50
        for i in range(0, len(rows), CHUNK):
            chunk = rows[i:i + CHUNK]
            batch = []
            for row in chunk:
                args = []
                for v in row:
                    if v is None:
                        args.append({"type": "null"})
                    elif isinstance(v, bool):
                        args.append({"type": "integer", "value": "1" if v else "0"})
                    elif isinstance(v, int):
                        args.append({"type": "integer", "value": str(v)})
                    elif isinstance(v, float):
                        args.append({"type": "float", "value": v})
                    elif isinstance(v, bytes):
                        import base64
                        args.append({"type": "blob", "base64": base64.b64encode(v).decode()})
                    else:
                        args.append({"type": "text", "value": str(v)})
                batch.append({"type": "execute", "stmt": {"sql": insert_sql, "args": args}})
            _turso_execute(http_url, token, batch)

        print(f"  [OK] {table}: {len(rows)} registros -> Turso Cloud")
        synced += 1

    except Exception as e:
        print(f"  [WARN] {table}: {e}")
        skipped += 1

conn.close()

print()
print("=" * 50)
print("SINCRONIZACION COMPLETADA!")
print(f"  Tablas sincronizadas: {synced}")
print(f"  Tablas sin datos:     {len(tables) - synced - skipped}")
print(f"  Errores:              {skipped}")
print("=" * 50)
print("Haz Reboot en Streamlit Cloud para ver los cambios.")
