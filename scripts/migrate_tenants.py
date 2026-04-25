import sqlite3
import os
import sys

# Añadir directorio raíz al path para importar core
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config.config import DB_PATH_GLOBAL, get_tenant_db_path
from src.infrastructure.database import inicializar_base_datos, get_db_connection

def migrate_data():
    if not os.path.exists(DB_PATH_GLOBAL):
        print(f"[!] Error: No se encuentra la base de datos global en {DB_PATH_GLOBAL}")
        return

    # 1. Obtener lista de empresas
    with get_db_connection(DB_PATH_GLOBAL) as conn_global:
        companies = conn_global.execute("SELECT id, nombre FROM empresas").fetchall()
    
    print(f"[*] Iniciando migracion para {len(companies)} empresas...")

    for emp_id, emp_nom in companies:
        if emp_id == 0 and emp_nom == "CGT":
            continue # Saltar la administración global
            
        print(f"\n--- Migrando: {emp_nom} (ID: {emp_id}) ---")
        
        tenant_db = get_tenant_db_path(emp_nom)
        print(f"    Archivo Destino: {tenant_db}")
        
        # Asegurar estructura
        try:
            inicializar_base_datos(tenant_db)
        except Exception as e:
            print(f"    Error al inicializar {tenant_db}: {e}")
            continue
        
        with get_db_connection(DB_PATH_GLOBAL) as conn_src:
            # Obtener tablas
            tables = conn_src.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
            
            with get_db_connection(tenant_db) as conn_dst:
                for (table_name,) in tables:
                    if table_name in ['sqlite_sequence', 'empresas', 'config_sistema']:
                        continue
                    
                    cursor_src = conn_src.cursor()
                    cursor_dst = conn_dst.cursor()
                    
                    try:
                        # Obtener columnas de fuente
                        cursor_src.execute(f"PRAGMA table_info({table_name})")
                        cols_src = [c[1] for c in cursor_src.fetchall()]
                        
                        # Obtener columnas de destino
                        cursor_dst.execute(f"PRAGMA table_info({table_name})")
                        cols_dst = [c[1] for c in cursor_dst.fetchall()]
                        
                        # Intersección de columnas
                        common_cols = [c for c in cols_src if c in cols_dst]
                        
                        if 'empresa_id' in common_cols:
                            # Migración filtrada
                            query = f"SELECT {', '.join(common_cols)} FROM {table_name} WHERE empresa_id = ?"
                            src_data = cursor_src.execute(query, (emp_id,)).fetchall()
                            
                            if src_data:
                                placeholders = ", ".join(["?"] * len(common_cols))
                                # Limpiar destino
                                conn_dst.execute(f"DELETE FROM {table_name} WHERE empresa_id = ?", (emp_id,))
                                conn_dst.executemany(f"INSERT INTO {table_name} ({', '.join(common_cols)}) VALUES ({placeholders})", src_data)
                                print(f"    [OK] {table_name}: {len(src_data)} registros.")
                        elif table_name == "usuarios":
                            # Usuarios tambien se filtran por empresa_id
                            query = f"SELECT {', '.join(common_cols)} FROM {table_name} WHERE empresa_id = ?"
                            src_data = cursor_src.execute(query, (emp_id,)).fetchall()
                            if src_data:
                                placeholders = ", ".join(["?"] * len(common_cols))
                                conn_dst.execute(f"DELETE FROM {table_name} WHERE empresa_id = ?", (emp_id,))
                                conn_dst.executemany(f"INSERT INTO {table_name} ({', '.join(common_cols)}) VALUES ({placeholders})", src_data)
                                print(f"    [OK] {table_name}: {len(src_data)} registros.")
                                
                    except Exception as e:
                        print(f"    [!] Error en tabla {table_name}: {str(e)[:100]}")
                
                conn_dst.commit()
    
    print("\n[FIN] Migracion finalizada con exito.")

if __name__ == "__main__":
    migrate_data()
