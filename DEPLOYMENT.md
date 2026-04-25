# Guía de Despliegue: Turso + Streamlit Cloud

Esta guía cubre cómo desplegar CGT SaaS con datos persistentes en Turso (SQLite distribuido).

## Problema Resuelto

Streamlit Community Cloud tiene filesystem efímero que se reinicia con cada despliegue, **causando pérdida permanente de datos**. Turso resuelve esto proporcionando SQLite distribuido con:

- **500M lecturas/mes** (free tier)
- **10M escrituras/mes** (suficiente para pequeña-mediana empresa)
- **5GB storage**
- **Sin tarjeta de crédito requerida**

---

## Arquitectura: Local-First + Cloud Sync

```
Desarrollo Local:              Producción (Streamlit Cloud):
  app.db (SQLite)              app.db (cache local)
    ↓                              ↓↑
    │                          .pull()/.push()
    │                              ↓↑
  (local reads/writes)        Turso Cloud DB
                              (persistent storage)
```

**Ventajas:**
- ✅ Desarrollo offline sin cambios de código
- ✅ Producción con datos persistentes tras restart
- ✅ Fast local reads (cache automático)
- ✅ Cloud backup automático

---

## Pre-requisitos

1. Cuenta GitHub
2. Cuenta Streamlit Community Cloud
3. Turso CLI (opcional, para setup manual)

```bash
# Instalar Turso CLI (opcional)
# macOS/Linux
brew install turso

# o descargar desde https://github.com/tursodatabase/turso-cli/releases
```

---

## Paso 1: Crear Base de Datos en Turso

### Opción A: Via Dashboard (Recomendado)

1. Ir a https://dashboard.turso.io
2. Registrarse con GitHub (es libre)
3. Click "Create Database"
4. Nombre: `cgt-saas-prod`
5. Región: Seleccionar cercana a tus usuarios (ej: `sjc` para USA Oeste, `cdg` para Europa)
6. Click "Create"

### Opción B: Via CLI

```bash
# Login
turso auth login

# Crear database
turso db create cgt-saas-prod

# Obtener URL
turso db show --url cgt-saas-prod
# Output: libsql://cgt-saas-prod-[tu-org].turso.io

# Crear token
turso db tokens create cgt-saas-prod
# Output: eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9...
```

**Guarda estos valores:**
```
LIBSQL_DB_URL = libsql://cgt-saas-prod-[tu-org].turso.io
LIBSQL_DB_AUTH_TOKEN = eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9...
```

---

## Paso 2: Migrar Datos (Opcional)

Si tienes datos existentes en `CGT_DATA/cgt_control.db`:

```bash
# Importar datos locales a Turso
turso db import cgt-saas-prod ./CGT_DATA/cgt_control.db

# Verificar
turso db show cgt-saas-prod
# Output: Name: cgt-saas-prod
#         URL: libsql://cgt-saas-prod-[org].turso.io
#         Size: 2.5 MB (después del import)
```

**Sin datos existentes:** Turso creará schema vacío en primer access, y los usuarios iniciales se crearán automáticamente.

---

## Paso 3: Configurar en Streamlit Cloud

1. Ir a https://share.streamlit.io
2. Dashboard → "New App" → seleccionar tu repo CGT-SaaS
3. Branch: `main`
4. Main file: `app.py`
5. Click "Deploy"
6. Una vez deployado, ir a **Settings** (⚙️ abajo a la derecha)
7. Click "Secrets"
8. Pegar contenido de `.streamlit/secrets.toml.example` con tus valores reales:

```toml
# ─────────────────────────────────────────────────────────────────────
# Turso Database (SQLite Distribuido - Producción)
# ─────────────────────────────────────────────────────────────────────

LIBSQL_DB_URL = "libsql://cgt-saas-prod-[tu-org].turso.io"
LIBSQL_DB_AUTH_TOKEN = "eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9..."
TURSO_ENV = "sync"

# Credenciales iniciales
ADMIN_PASSWORD = "cambia_esto_en_produccion"
RIGGER_PASSWORD = "cambia_esto_en_produccion"
VISITA_PASSWORD = "cambia_esto_en_produccion"
AUDITOR_PASSWORD = "cambia_esto_en_produccion"

# Google Gemini (opcional)
GEMINI_API_KEY = ""
```

9. Click "Save"
10. Streamlit automáticamente reinicia la app

---

## Paso 4: Verificar Deploy

1. Tu app ahora está disponible en `https://[nombre-app].streamlit.app`
2. Login con usuario `miguel` + password (que configuraste)
3. Verificar que puedes crear registros
4. Reiniciar app (Settings → "Reboot app")
5. **Los datos deben persistir** ← ¡Esto es lo que valida el fix!

---

## Desarrollo Local

Para trabajar localmente sin internet:

### Configurar .env

```bash
# Crear archivo .env en raíz del proyecto
TURSO_ENV=local
```

O simplemente:

```bash
export TURSO_ENV=local
python -m streamlit run app.py
```

**En local mode:**
- ✅ App usa SQLite local puro (`app.db`)
- ✅ Cero datos sincronizados a cloud
- ✅ Funciona offline completamente
- ✅ Idéntico al desarrollo pre-Turso

### Sincronizar cambios locales a cloud (opcional)

Si desarrollas features localmente y quieres probar en prod:

```bash
# 1. Cambiar a sync mode
export TURSO_ENV=sync
export LIBSQL_DB_URL=libsql://cgt-saas-prod-[org].turso.io
export LIBSQL_DB_AUTH_TOKEN=...

# 2. Ejecutar app
streamlit run app.py

# 3. Hacer cambios, datos se syncan automáticamente a Turso
```

---

## Monitoreo & Quotas

### Dashboard Turso

Ir a https://dashboard.turso.io → tu database:

- **Reads**: Cuántas lecturas realizadas este mes (quota: 500M)
- **Writes**: Cuántas escrituras realizadas este mes (quota: 10M)
- **Storage**: GB usados (quota: 5GB)

### Estimaciones de Quota

Para una empresa pequeña-mediana:

```
Lecturas (500M/mes):
  - 100 usuarios × 20 logins/día × 30 días = 60K reads (muy bajo)
  - 1K registros consultados/día × 30 días = 30K reads
  - Total: ~100K reads/mes (0.02% de quota) ✅

Escrituras (10M/mes):
  - 50 registros nuevos/día × 30 días = 1.5K writes
  - 100 audits/día × 30 días = 3K writes
  - Total: ~5K writes/mes (0.05% de quota) ✅
```

**Si se acerca al límite:**
- Opción 1: Upgrade a plan de pago ($4.99/mes)
- Opción 2: Implementar caché local más agresivo
- Opción 3: Migrar a otro proveedor de base de datos (Render, Railway, etc.)

---

## Troubleshooting

### "Error: Connection refused"

**Causa:** LIBSQL_DB_URL o LIBSQL_DB_AUTH_TOKEN incorrecto o expirado.

**Solución:**
```bash
# Verificar valores en Streamlit Cloud Secrets
# Recrear token
turso db tokens create cgt-saas-prod
# Copiar nuevo token a Secrets en Streamlit Cloud
```

### "Error: BLOCKED - Quota exceeded"

**Causa:** Superaste límite mensual de reads/writes.

**Solución:**
- Upgrade a plan paid ($4.99/mes)
- O esperar a que se resetee el mes siguiente (cota mensual)

### "Error: Table doesn't exist"

**Causa:** Schema no fue initializado en Turso.

**Solución:**
```bash
# Trigger initialización ejecutando la app una vez
streamlit run app.py

# Luego en cloud
# Ir a Settings → Reboot app
```

### Datos no persisten tras restart

**Causa:** TURSO_ENV no está en "sync" en Streamlit Secrets.

**Solución:**
```toml
# Verificar que Secrets tiene:
TURSO_ENV = "sync"  # No "local" ni vacío
LIBSQL_DB_URL = "libsql://..."
LIBSQL_DB_AUTH_TOKEN = "..."
```

---

## Rollback: Volver a SQLite Local

Si necesitas revertir a SQLite local (no recomendado en producción):

```bash
# 1. Exportar datos desde Turso
turso db export cgt-saas-prod > backup.sql

# 2. En app.py, cambiar:
# DB_PATH = os.path.join(BASE_DATA_DIR, "cgt_control.db")
# Sin cambios en Streamlit, ya que detecta env automáticamente

# 3. Exportar datos a SQLite
sqlite3 CGT_DATA/cgt_control.db < backup.sql

# 4. Deploy a Streamlit Cloud SIN TURSO_ENV en Secrets
# La app detectará que no hay Turso y usará SQL local ephemeral
```

---

## Preguntas Frecuentes

**P: ¿Dónde se guardan los datos?**
R: En servidores Turso (SQLite distribuido), con copias replicadas automáticamente. Free tier sin replicación geográfica (una región).

**P: ¿Es seguro?**
R: Sí, Turso encripta en tránsito y en reposo, con tokens JWT que expiran. Usa HTTPS always.

**P: ¿Qué pasa si Turso se cae?**
R: Los datos siguen en cloud. La app intentará reconectarse con retry automático. Durante outage, la app será offline en Streamlit Cloud.

**P: ¿Puedo usar múltiples ambientes (dev, staging, prod)?**
R: Sí, crea 3 databases en Turso:
```
- cgt-saas-dev
- cgt-saas-staging
- cgt-saas-prod

Y 3 repos/branches en GitHub con Streamlit Cloud config separada.
```

**P: ¿Cómo hago respaldos?**
R: Turso free tier incluye snapshots automáticos (24h). Para respaldos manuales:
```bash
turso db export cgt-saas-prod > backup-$(date +%Y%m%d).sql
```

---

## Soporte

- 📚 Docs Turso: https://docs.turso.tech
- 💬 Comunidad: https://discord.gg/turso
- 🐛 Issues CGT: GitHub Issues en este repo

---

## Próximos Pasos (v2.0)

Mejoras planeadas:
- [ ] Replicación geográfica multi-región (Turso Scaler plan)
- [ ] Presigned URLs para archivos en S3/Blob Storage
- [ ] Caching distribuido con Redis (para quotas altas)
- [ ] GraphQL API (para mobile clients)
- [ ] Migración a base de datos por tenant (Turso Clusters)
