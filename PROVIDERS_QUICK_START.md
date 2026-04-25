# 🚀 Inicio Rápido - Múltiples Proveedores de IA

## 📦 Instalación en 3 pasos

### 1. Actualizar dependencias
```bash
pip install --upgrade -r requirements.txt
```

### 2. Verificar instalación
```bash
python test_multi_providers.py
```

Deberías ver: ✅ 6/7 tests pasados

### 3. Ir a la interfaz
En Streamlit:
- **Inteligencia** → **Ull-Trone Command Center**
- **Tab: ⚙️ Núcleo Central** → **Cerebro (LLM)**
- Selecciona tu proveedor favorito
- Ingresa API KEY
- ¡Listo!

## 🆓 Opción 1: Google Gemini (Recomendado para empezar)

### Obtener API KEY (gratis)
1. Ve a https://aistudio.google.com
2. Haz clic en **"Get API Key"**
3. Copia la clave

### Configurar
```
Proveedor: 💎 Google Gemini
API KEY: [Tu clave aquí]
Modelo: gemini-2.0-flash (recomendado)
```

**Ventajas:**
- ✅ Gratis (primeras llamadas)
- ✅ Muy rápido
- ✅ Excelente calidad
- ✅ 1M de tokens de contexto

## 💬 Opción 2: OpenAI (ChatGPT)

### Obtener API KEY (pago)
1. Ve a https://platform.openai.com
2. Crear cuenta y añadir método de pago
3. Ir a **API keys** → **Create new secret key**
4. Copia la clave

### Configurar
```
Proveedor: 🔴 OpenAI (ChatGPT)
API KEY: sk-...
Modelo: gpt-4o (recomendado) o gpt-3.5-turbo (económico)
```

**Ventajas:**
- 🔥 Mejor razonamiento
- 🔥 Mejor en código
- ⚡ Más rápido

## 🤖 Opción 3: Anthropic (Claude)

### Obtener API KEY (pago)
1. Ve a https://console.anthropic.com
2. Crear cuenta
3. Ir a **API keys**
4. Copia la clave

### Configurar
```
Proveedor: 🤖 Anthropic (Claude)
API KEY: sk-ant-...
Modelo: claude-opus-4-1 (mejor) o claude-haiku-3 (rápido)
```

**Ventajas:**
- 🧠 Mejor razonamiento profundo
- 📊 Análisis complejos
- 200K contexto

## 🌊 Opción 4: DeepSeek

### Obtener API KEY (bajo costo)
1. Ve a https://platform.deepseek.com
2. Registrarse
3. Crear API key
4. Copia la clave

### Configurar
```
Proveedor: 🌊 DeepSeek
API KEY: sk-...
Modelo: deepseek-chat (conversación) o deepseek-coder
```

**Ventajas:**
- 💰 Muy económico
- 💪 Buena calidad
- 🔥 Especializado en código

## 🦙 Opción 5: Ollama (Local - ¡Sin API KEY!)

### Instalar Ollama
1. Descarga desde https://ollama.ai
2. Instala
3. Abre terminal y ejecuta:
   ```bash
   ollama serve
   ```

### Descargar modelo
En otra terminal:
```bash
ollama pull mistral
```

### Configurar en app
```
Proveedor: 🦙 Ollama (Local)
API KEY: [Dejar vacío o http://localhost:11434]
Modelo: mistral (o cualquier modelo que tengas)
```

**Ventajas:**
- 💚 Completamente gratis
- 🔐 Privacidad total (local)
- ⚡ Muy rápido
- 📴 Sin conexión requerida

## ✅ Prueba rápida

Después de configurar, ve al **Tab Chat** y envía un mensaje:

```
¿Quién eres?
```

Deberías recibir respuesta del proveedor configurado.

## 🧪 Verificar que funciona

### En Python (para desarrolladores)

```python
from intelligence.ai_engine import AIEngineFactory
from src.infrastructure.database import obtener_config
from config.config import DB_PATH

# Cargar config
config = obtener_config(DB_PATH, "ULLTRONE_BRAIN_CONFIG", {})

# Crear motor
engine = AIEngineFactory.create_from_db_config(config)

# Generar respuesta
print(engine.generate("¿Hola?"))
```

### En CLI

```bash
# Ejecutar tests
python test_multi_providers.py

# Deberías ver ✅ 6/7 tests pasados
```

## 🐛 Troubleshooting

### "API KEY requerida"
→ Verifica que copiaste bien la clave y no tiene espacios

### "ModuleNotFoundError: openai"
```bash
pip install openai anthropic
```

### "Ollama no responde"
```bash
# En terminal nueva:
ollama serve

# En otra terminal:
ollama pull mistral
```

### El chat no genera respuestas
Checklist:
- ✅ ¿API KEY copiada correctamente?
- ✅ ¿Cuenta tiene créditos? (OpenAI, etc.)
- ✅ ¿Conexión a internet?
- ✅ Haz clic en "🧪 Probar Conexión"

## 📚 Recursos Útiles

| Proveedor | Documentación | Precios |
|-----------|---------------|---------|
| Google Gemini | [ai.google.dev](https://ai.google.dev) | Gratis* |
| OpenAI | [platform.openai.com](https://platform.openai.com/docs) | Pago |
| Anthropic | [docs.anthropic.com](https://docs.anthropic.com) | Pago |
| DeepSeek | [platform.deepseek.com](https://platform.deepseek.com) | Bajo costo |
| Ollama | [ollama.ai](https://ollama.ai) | Gratis |

## 🎯 Recomendación para cada caso

| Caso | Recomendación |
|------|---------------|
| 🎓 Aprendizaje | **Gemini** (gratis) |
| 💼 Empresa | **Claude** o **GPT-4** |
| 💰 Presupuesto limitado | **DeepSeek** |
| 🔐 Privacidad máxima | **Ollama** (local) |
| ⚡ Velocidad | **Gemini Flash** o **Mistral** |
| 🧠 Razonamiento | **Claude Opus** o **GPT-4** |

---

**¿Necesitas ayuda?** Revisar [MULTI_AI_PROVIDERS_GUIDE.md](./MULTI_AI_PROVIDERS_GUIDE.md) para documentación completa.
