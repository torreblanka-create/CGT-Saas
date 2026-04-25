# 🔄 Actualización: Google Gemini - google-genai

## 📢 Aviso Importante

Google ha deprecado `google-generativeai` y ahora recomienda usar `google-genai`.

**Esto causa el warning que ves:**
```
FutureWarning: All support for the `google.generativeai` package has ended.
```

## ✅ Solución: Actualizar dependencias

```bash
pip install --upgrade -r requirements.txt
```

Esto instalará:
- `google-genai>=0.2.0` (nueva, recomendada)
- Mantiene compatibilidad con `google-generativeai` (antigua)

## 🔍 Cómo Funciona

El sistema ahora es **compatible con ambas librerías**:

1. **Intenta usar google-genai (nueva)** ✅
2. **Si no está disponible, fallback a google-generativeai (antigua)** ✅
3. **Interfaz uniforme** — El código funciona igual en ambos casos

### Archivos Actualizados

| Archivo | Cambio |
|---------|--------|
| `requirements.txt` | google-generativeai → google-genai |
| `intelligence/providers/gemini_provider.py` | Soporte dual |
| `intelligence/gemini_compat.py` | Capa de compatibilidad |

## 🚀 Después de Actualizar

```bash
# 1. Instalar dependencias
pip install --upgrade -r requirements.txt

# 2. Ejecutar app (debería funcionar sin warnings)
streamlit run app.py
```

## ✨ Beneficios

| Antes | Después |
|-------|---------|
| ⚠️ FutureWarning | ✅ Sin warnings |
| 🐢 Librería antigua | 🚀 Librería nueva |
| ❓ Mantenimiento incierto | ✅ Mantenimiento oficial |
| 📦 Una sola opción | ✅ Compatible con ambas |

## 🔧 Detalles Técnicos

### Nueva Librería (google-genai)

```python
import google.genai
client = google.genai.Client(api_key="...")
response = client.models.generate_content(...)
```

### Antigua Librería (google-generativeai)

```python
import google.generativeai as genai
genai.configure(api_key="...")
model = genai.GenerativeModel("gemini-1.5-pro")
response = model.generate_content(...)
```

### Nuestro Wrapper

```python
from intelligence.gemini_compat import initialize_gemini, create_model

initialize_gemini(api_key="...")
model = create_model("gemini-1.5-pro")
response = model.generate_content(prompt)

# Funciona con ambas librerías automáticamente ✨
```

## 📋 Checklist

- [ ] Ejecutar: `pip install --upgrade -r requirements.txt`
- [ ] Reiniciar app Streamlit
- [ ] Verificar que no hay FutureWarning
- [ ] Probar chat (debe funcionar igual)
- [ ] Confirmar: Config → Cerebro → Probar Conexión

## ❓ FAQs

### ¿Es obligatorio actualizar?
**No.** El sistema funciona con ambas. Pero `google-generativeai` dejará de recibir actualizaciones.

### ¿Se perderán cambios si cambio a google-genai?
**No.** La API es compatible. Cambio transparente.

### ¿Google-genai es estable?
**Sí.** Es la librería oficial recomendada por Google. Mucho más estable que la antigua.

### ¿Qué pasa si no instalo google-genai?
**Nada.** El fallback usa `google-generativeai` automáticamente (con warning).

## 📞 Soporte

**Documentación:**
- [Google Gemini API](https://ai.google.dev)
- [google-genai en PyPI](https://pypi.org/project/google-genai)

---

**Actualización:** 2026-04-25  
**Estado:** ✅ Lista para instalar
