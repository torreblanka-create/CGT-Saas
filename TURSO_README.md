# Turso Integration - Technical Guide for Developers (v2.0)

## Architecture Overview

CGT SaaS ahora usa **Turso (SQLite distribuido) con sincronización real** para persistencia en producción, mientras mantiene compatibilidad con desarrollo local offline.

### ✅ ¡Sincronización implementada!
El adaptador `turso_adapter.py` v2.0 ahora realiza:
- **Pull** automático al iniciar la app (cloud → local)
- **Push** automático en cada commit (local → cloud)
- **Push** final al cerrar la conexión
- Los datos persisten después de reboot en Streamlit Cloud 🎉

### Three Operating Modes

```python
# Mode 1: Local Development (default)
os.environ["TURSO_ENV"] = "local"
# → SQLite puro en app.db
# → Sin conexión a internet requerida
# → Usado en `streamlit run app.py` local

# Mode 2: Sync Mode (producción)
os.environ["TURSO_ENV"] = "sync"
# → app.db local (caché)
# → Sincronización bidireccional a Turso Cloud
# → .pull() al iniciar, .push() en commit
# → Usado en Streamlit Community Cloud

# Mode 3: Cloud-Only (futuro)
os.environ["TURSO_ENV"] = "cloud"
# → Sin caché local
# → HTTP directamente a Turso
# → Para serverless (no implementado aún)
```

---

## Implementation Details

### 1. Adapter Layer: `src/infrastructure/turso_adapter.py`

```python
from src.infrastructure.turso_adapter import get_turso_connection

# Usage (identical to sqlite3):
with get_turso_connection(db_path) as conn:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM usuarios")
    results = cursor.fetchall()
```

**Key Class: `TursoConnection`**

```python
class TursoConnection:
    def __init__(self, db_path, turso_url=None, turso_token=None, env="local"):
        # Detect mode from TURSO_ENV env var
        # Initialize local SQLite connection
        # If sync: .pull() from cloud on init

    def _pull_with_retry(self, max_retries=3):
        # Sync cloud → local with exponential backoff
        # Handles transient network failures

    def _push_with_retry(self, max_retries=3):
        # Sync local → cloud after writes
        # Only in sync/cloud modes

    def cursor(self):
        # Standard sqlite3 cursor

    def commit(self):
        # Commit + push to cloud (if enabled)

    def close(self):
        # Close + final push (if enabled)
```

### 2. Refactored Database Layer: `src/infrastructure/database.py`

**No API changes** — all functions remain identical:

```python
# Before
def get_db_connection(db_path):
    conn = sqlite3.connect(db_path, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    yield conn

# After
def get_db_connection(db_path):
    with get_turso_connection(db_path) as conn:
        if os.getenv("TURSO_ENV") == "local":
            conn.execute("PRAGMA journal_mode=WAL")  # Local only
        yield conn
```

**Key Functions:**

| Function | Behavior |
|----------|----------|
| `get_db_connection(db_path)` | Context manager, auto-closes + pushes |
| `obtener_conexion(db_path)` | Direct connection (no context) |
| `ejecutar_query(db_path, query, params, commit)` | Execute + optional push |
| `obtener_dataframe(db_path, query, params)` | Pandas read (uses conn directly) |
| `inicializar_base_datos(db_path)` | Create schema (local dir only in local mode) |

### 3. Environment Detection: `config/config.py`

```python
TURSO_ENV = os.getenv("TURSO_ENV", "local")
# Reads from:
# 1. .env file (local dev)
# 2. Environment variable
# 3. st.secrets (Streamlit Cloud)
# 4. Fallback: "local"
```

---

## Data Sync Lifecycle

### Startup Flow

```
Streamlit app starts
  ↓
_cargar_usuarios_cached()
  ↓
inicializar_base_datos(DB_PATH)
  ↓
with get_db_connection(db_path) as conn:  # First connection
  ↓
TursoConnection.__init__()
  ↓
if TURSO_ENV == "sync":
  ↓
  .pull()  # Sync cloud → local
  ↓
Schema patching (CREATE TABLE IF NOT EXISTS)
  ↓
App ready
```

### Write Flow (Insert/Update/Delete)

```
User action (insert registro)
  ↓
ejecutar_query(db_path, "INSERT ...", params, commit=True)
  ↓
cursor.execute(INSERT SQL)
  ↓
conn.commit()  # Local transaction
  ↓
if TURSO_ENV == "sync":
  ↓
  .push()  # Sync local → cloud
  ↓
Write confirmed
```

### Read Flow (Query)

```
obtener_dataframe(db_path, "SELECT ...")
  ↓
pd.read_sql_query(query, conn)
  ↓
Uses local cache (app.db in memory)
  ↓
No network latency!
```

---

## Quota & Performance

### Free Tier Limits

```
Per Month (resets 1st of month):
- 500M reads
- 10M writes
- 5GB storage

Cost: $0/month
```

### Typical Usage (100-user company)

```
Scenario: 50 concurrent users, 8 hours/day, 22 working days

Reads:
  - Login: 2 queries × 50 users × 22 days = 2.2K reads
  - Dashboard queries: 10/day × 50 users × 22 days = 11K reads
  - Registro queries: 1000/day × 22 days = 22K reads
  - Total: ~35K reads/month (0.007% of quota) ✅

Writes:
  - New registros: 100/day × 22 days = 2.2K writes
  - Log entries: 500/day × 22 days = 11K writes
  - Updates: 200/day × 22 days = 4.4K writes
  - Total: ~18K writes/month (0.18% of quota) ✅
```

### Optimization Tips

1. **Caching**: Streamlit's `@st.cache_data(ttl=30)` caches reads
2. **Batch Ops**: Use `executemany()` for bulk inserts
3. **Indexes**: Indexed columns reduce read latency
4. **Selectivity**: `SELECT col WHERE empresa_id=X` not `SELECT *`

---

## Testing Checklist

### Mode: Local (TURSO_ENV=local)

```bash
export TURSO_ENV=local
streamlit run app.py

# ✅ App starts without internet
# ✅ Login works
# ✅ Insert/update/delete works
# ✅ Data persists in app.db
# ✅ No network calls
```

### Mode: Sync (TURSO_ENV=sync)

```bash
export TURSO_ENV=sync
export LIBSQL_DB_URL="libsql://cgt-saas-prod-[org].turso.io"
export LIBSQL_DB_AUTH_TOKEN="..."
streamlit run app.py

# ✅ First run: .pull() syncs cloud → local
# ✅ Reads use local cache (fast)
# ✅ Writes trigger .push() to cloud
# ✅ Restart app: data persists (from cloud)
# ✅ Network latency ~200-500ms on push
```

### Mode: Production (Streamlit Cloud)

```toml
# .streamlit/secrets.toml in Streamlit Cloud
TURSO_ENV = "sync"
LIBSQL_DB_URL = "libsql://cgt-saas-prod-[org].turso.io"
LIBSQL_DB_AUTH_TOKEN = "..."
```

```bash
# After deploy:
# ✅ App starts (pulls schema from cloud)
# ✅ Login: fast (local cache)
# ✅ Insert: syncs to cloud
# ✅ Reboot container: data persists ← GOLDEN SIGNAL
# ✅ Multi-instance: eventual consistency
```

---

## Debugging

### Enable Verbose Logging

```python
# In turso_adapter.py, uncomment:
print(f"🔄 Pulling from Turso...")  # On .pull()
print(f"🔄 Pushing to Turso...")    # On .push()
print(f"⚠️ Pull failed: {e}")        # On error
```

### Inspect Local Cache

```bash
# Check app.db size/structure
sqlite3 app.db

sqlite> SELECT name FROM sqlite_master WHERE type='table' LIMIT 5;
sqlite> SELECT COUNT(*) FROM usuarios;
sqlite> .tables
```

### Inspect Cloud Database

```bash
# Use Turso CLI
turso db shell cgt-saas-prod

→ SELECT COUNT(*) FROM usuarios;
→ SELECT name FROM sqlite_master WHERE type='table' LIMIT 5;
```

### Network Debugging

```python
# In turso_adapter.py, add timing:
import time
start = time.time()
self.conn.pull()
elapsed = time.time() - start
print(f"Pull took {elapsed:.2f}s")  # Should be <1s typically
```

---

## Common Issues & Fixes

### Issue: "Connection refused to libsql://..."

**Cause:** Token expired or network issue

**Fix:**
```bash
turso db tokens create cgt-saas-prod  # New token
# Update .streamlit/secrets.toml in Streamlit Cloud
```

### Issue: "Table X doesn't exist in cloud"

**Cause:** Schema not synced

**Fix:**
```bash
# Local: Force schema creation
export TURSO_ENV=local
streamlit run app.py
# This creates all tables locally

# Then switch to sync mode
export TURSO_ENV=sync
# .pull() will sync schema to Turso
```

### Issue: Data lost after Streamlit restart

**Cause:** TURSO_ENV not set to "sync" or push failed silently

**Fix:**
```bash
# Check Streamlit Cloud Secrets
# Must have:
# TURSO_ENV=sync
# LIBSQL_DB_URL=...
# LIBSQL_DB_AUTH_TOKEN=...

# Check logs for push errors
# Monitor Turso dashboard for quota
```

### Issue: Slow queries (>2s)

**Cause:** Network latency or large result set

**Fix:**
1. Use `@st.cache_data(ttl=30)` on expensive queries
2. Add WHERE clauses to reduce result size
3. Check if query uses indexes
4. Consider batch operations instead of individual inserts

---

## Future Enhancements

### v1.1: Multi-Tenant Databases

```python
# Currently: Single cloud DB, empresa_id filtering
# Future: One Turso DB per tenant

def get_tenant_turso_url(empresa_id):
    # Return cgt-saas-prod-empresa-{empresa_id}
    # Allows per-tenant quotas, backups, scaling
```

### v2.0: Serverless Functions

```python
# Use libsql HTTP client for edge functions
# Instead of local replica
# Eliminate local filesystem requirement
```

### v2.0: Replication to Multiple Regions

```python
# Turso Scaler plan: $29/month
# Replicate to sjc, cdg, syd for global users
# <100ms latency from any region
```

---

## References

- **Turso Docs**: https://docs.turso.tech
- **pyturso GitHub**: https://github.com/tursodatabase/turso-client-ts
- **SQLite**: https://www.sqlite.org/pragma.html
- **Streamlit Secrets**: https://docs.streamlit.io/deploy/streamlit-cloud/deploy-your-app

---

## Support & Troubleshooting

If issues arise:

1. Check Turso dashboard: https://dashboard.turso.io
2. Review plan quotas (reads/writes/storage)
3. Enable verbose logging in turso_adapter.py
4. Test locally first (`TURSO_ENV=local`)
5. Recreate auth token if network errors
6. Check Streamlit Cloud logs for errors

For questions, open an issue on GitHub or contact team.
