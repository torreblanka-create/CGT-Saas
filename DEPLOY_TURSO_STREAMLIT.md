# Deploy en Turso + Streamlit Cloud

## PASO 1: Crear Base de Datos en Turso

### 1.1 Instalar Turso CLI
```bash
# En Windows (con Chocolatey)
choco install turso-cli

# O descargar desde: https://docs.turso.tech/cli/installation
```

### 1.2 Autenticarse en Turso
```bash
turso auth login
# → Se abre navegador para autenticarse
# → Copiar el token de CLI
```

### 1.3 Crear Base de Datos
```bash
turso db create cgt-saas-prod

# Resultado esperado:
# Database 'cgt-saas-prod' created
# URL: libsql://cgt-saas-prod-[org].turso.io
```

### 1.4 Obtener Credenciales

```bash
# URL de la base de datos
turso db show cgt-saas-prod
# → Copiar el URL (libsql://cgt-saas-prod-[org].turso.io)

# Token de autenticación
turso db tokens create cgt-saas-prod
# → Copiar el token largo
```

**Guardar estas credenciales:**
```
LIBSQL_DB_URL = "libsql://cgt-saas-prod-[org].turso.io"
LIBSQL_DB_AUTH_TOKEN = "[token-largo-aqui]"
TURSO_ENV = "sync"
```

---

## PASO 2: Deploy en Streamlit Cloud

### 2.1 Conectar GitHub a Streamlit
1. Ir a https://share.streamlit.io
2. Click en "New app"
3. Seleccionar:
   - Repository: `torreblanka-create/CGT-Saas`
   - Branch: `main`
   - Main file path: `app.py`

### 2.2 Configurar Secretos (Secrets)
1. En Streamlit Cloud → App settings → Secrets
2. Copiar el contenido de `.streamlit/secrets.toml`:

```toml
# .streamlit/secrets.toml
TURSO_ENV = "sync"
LIBSQL_DB_URL = "libsql://cgt-saas-prod-[org].turso.io"
LIBSQL_DB_AUTH_TOKEN = "[token-aqui]"

# Contraseñas de sistema
ADMIN_PASSWORD = "ADMIN_CGT_2024"
RIGGER_PASSWORD = "RIGGER_CGT_2024"
VISITA_PASSWORD = "VISITA_CGT_2024"
AUDITOR_PASSWORD = "AUDITOR_CGT_2024"

# Google API (si es necesario)
GEMINI_API_KEY = "[api-key-aqui]"
```

### 2.3 Deploy
1. Streamlit detecta cambios en `main` automáticamente
2. Ir a: https://cgt-saas.streamlit.app
3. La app hará .pull() al iniciar (trae datos de Turso)

---

## PASO 3: Inicializar Turso con Datos

### 3.1 Sincronizar Datos de Local a Turso

Una vez en Streamlit Cloud con `TURSO_ENV=sync`:

**Opción A: Automático (cuando la app inicia)**
- La app hace `.pull()` al iniciar
- Luego hace `.push()` en cada operación
- Los datos se sincronizan automáticamente

**Opción B: Manual (si quieres forzar)**
```bash
# Localmente con sync mode activado
export TURSO_ENV=sync
export LIBSQL_DB_URL="libsql://cgt-saas-prod-[org].turso.io"
export LIBSQL_DB_AUTH_TOKEN="[token]"

streamlit run app.py
# → Hace pull + push automáticamente
```

### 3.2 Verificar Sincronización

```bash
# Ver datos en Turso Cloud
turso db shell cgt-saas-prod

→ SELECT COUNT(*) FROM usuarios;
→ SELECT COUNT(*) FROM empresas;
→ .quit
```

---

## PASO 4: Monitoreo y Debugging

### 4.1 Ver Logs en Streamlit Cloud
- Streamlit Dashboard → App settings → View logs

### 4.2 Comprobar Cuota de Turso
```bash
turso db show cgt-saas-prod
# Ver: reads/writes/storage usage
```

### 4.3 Si algo falla
```bash
# Regenerar token (si expiró)
turso db tokens create cgt-saas-prod

# Actualizar en Streamlit Cloud secrets → redeploy
```

---

## CHECKLIST DE DEPLOYMENT

- [ ] 1. Instalar Turso CLI
- [ ] 2. Autenticarse en Turso (`turso auth login`)
- [ ] 3. Crear BD (`turso db create cgt-saas-prod`)
- [ ] 4. Obtener URL y Token
- [ ] 5. Conectar GitHub a Streamlit Cloud
- [ ] 6. Crear App en Streamlit Cloud
- [ ] 7. Configurar Secrets en Streamlit Cloud
- [ ] 8. Verificar que los datos sincronizaron
- [ ] 9. Hacer login en https://cgt-saas.streamlit.app
- [ ] 10. Probar CRUD (crear empresa, registro, etc)

---

## URLS ÚTILES

- **GitHub Repo**: https://github.com/torreblanka-create/CGT-Saas
- **Turso Dashboard**: https://dashboard.turso.io
- **Streamlit App**: https://cgt-saas.streamlit.app (después de deploy)
- **Turso Docs**: https://docs.turso.tech

---

## SOPORTE

Si hay errores:

1. **"Connection refused"** → Token expirado, regenerar con `turso db tokens create`
2. **"Table doesn't exist"** → Ejecutar app localmente primero en sync mode
3. **"Data lost after restart"** → Verificar que TURSO_ENV=sync en secrets
4. **Queries lentas** → Usar `@st.cache_data(ttl=30)` para cachear
