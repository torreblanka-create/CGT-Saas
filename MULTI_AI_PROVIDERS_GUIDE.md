# 🧠 Guía de Múltiples Proveedores de IA — CGT SaaS

## 📋 Descripción General

Este sistema permite integrar múltiples proveedores de IA en la aplicación CGT SaaS. Puedes cambiar entre diferentes modelos de lenguaje sin modificar el código, solo actualizando la configuración.

**Proveedores Soportados:**

- 💎 **Google Gemini** — Modelos de Google (recomendado para inicio)
- 🔴 **OpenAI (ChatGPT)** — GPT-4, GPT-4 Turbo, GPT-3.5
- 🤖 **Anthropic (Claude)** — Modelos Claude, especializado en razonamiento
- 🌊 **DeepSeek** — Alternativa open-source eficiente
- 🦙 **Ollama** — Modelos locales (sin API KEY necesaria)

## 🚀 Instalación

### 1. Actualizar dependencias

```bash
pip install --upgrade -r requirements.txt
```

Las nuevas librerías instaladas:
- `openai>=1.14.0` — Para OpenAI y DeepSeek
- `anthropic>=0.25.0` — Para Anthropic/Claude

### 2. Configurar en la interfaz

1. Entra a **Inteligencia → Cerebro → ⚙️ Configuración del Cerebro Central**
2. Selecciona el proveedor que deseas usar
3. Ingresa tu API KEY
4. Selecciona el modelo
5. Haz clic en **🧪 Probar Conexión** para validar
6. Guarda la configuración

## 🔑 Obtener API Keys

### Google Gemini

1. Ve a [Google AI Studio](https://aistudio.google.com)
2. Haz clic en "Get API Key"
3. Copia y pega la clave en la configuración

**Modelos disponibles:**
- `gemini-2.0-flash` (último, recomendado)
- `gemini-1.5-pro` (más potente)
- `gemini-1.5-flash` (más rápido, económico)

### OpenAI (ChatGPT)

1. Ve a [OpenAI Platform](https://platform.openai.com)
2. Crea una cuenta y ve a API keys
3. Crea una nueva clave
4. Copia y pega en la configuración

**Modelos disponibles:**
- `gpt-4-turbo` (más potente)
- `gpt-4o` (versión optimizada)
- `gpt-3.5-turbo` (económico, rápido)

### Anthropic (Claude)

1. Ve a [Anthropic Console](https://console.anthropic.com)
2. Crea una cuenta
3. Ve a API keys
4. Copia y pega la clave

**Modelos disponibles:**
- `claude-opus-4-1` (más potente)
- `claude-sonnet-4` (versión estable)
- `claude-3-5-sonnet-20241022` (versión nueva)
- `claude-haiku-3` (económico, rápido)

### DeepSeek

1. Ve a [DeepSeek API](https://api.deepseek.com)
2. Crea una cuenta
3. Genera una API key
4. Copia y pega en la configuración

**Modelos disponibles:**
- `deepseek-chat` (conversación)
- `deepseek-coder` (código)

### Ollama (Local)

1. Descarga e instala [Ollama](https://ollama.ai)
2. Inicia Ollama:
   ```bash
   ollama serve
   ```
3. Descarga un modelo:
   ```bash
   ollama pull llama2
   ollama pull mistral
   ```
4. Usa `http://localhost:11434` como URL en la configuración

**Modelos populares:**
- `llama2` — Meta LLaMA 2 (recomendado, 7B)
- `mistral` — Mistral 7B
- `neural-chat` — Intel Neural Chat
- `dolphin-mix` — Dolphin Mix

## 💻 Uso Programático

### Ejemplo 1: Usar el motor de IA directamente

```python
from intelligence.ai_engine import AIEngineFactory
from src.infrastructure.database import obtener_config

# Cargar configuración desde DB
db_path = "ruta/a/tu/db.db"
config = obtener_config(db_path, "ULLTRONE_BRAIN_CONFIG", {})

# Crear motor de IA
ai_engine = AIEngineFactory.create_from_db_config(config)

# Generar respuesta
response = ai_engine.generate("¿Cuáles son los riesgos laborales principales?")
print(response)
```

### Ejemplo 2: Streaming en tiempo real

```python
from intelligence.ai_engine import AIEngineFactory

config = {
    "api_provider": "Google Gemini",
    "api_key": "tu-api-key-aqui",
    "model_name": "gemini-1.5-pro",
    "temperature": 0.7,
    "max_output_tokens": 4096
}

ai_engine = AIEngineFactory.create_from_db_config(config)

# Streaming
for chunk in ai_engine.generate_stream("Escribe un análisis de riesgos..."):
    print(chunk, end="", flush=True)
```

### Ejemplo 3: Crear un proveedor específico

```python
from intelligence.providers import create_provider, ProviderConfig

# Crear configuración
config = ProviderConfig(
    api_key="sk-...",
    model_name="gpt-4-turbo",
    temperature=0.5,
    max_tokens=2048
)

# Crear proveedor de OpenAI
provider = create_provider("OpenAI (ChatGPT)", config)

# Generar respuesta
response = provider.generate_response("¿Cuál es el cumplimiento normativo?")
print(response)

# Validar conexión
if provider.validate_connection():
    print("✅ Conexión válida")
```

### Ejemplo 4: Listar modelos disponibles

```python
from intelligence.providers import get_provider_models

# Modelos de OpenAI
modelos_openai = get_provider_models("OpenAI (ChatGPT)")
print(modelos_openai)
# Salida: ['gpt-4-turbo', 'gpt-4', 'gpt-3.5-turbo', ...]

# Modelos de Claude
modelos_claude = get_provider_models("Anthropic (Claude)")
print(modelos_claude)
```

### Ejemplo 5: Dinámicamente cargar modelos de Ollama

```python
from intelligence.providers import OllamaProvider, ProviderConfig

config = ProviderConfig(
    api_key="http://localhost:11434",  # URL local
    model_name="llama2"
)

ollama = OllamaProvider(config)

# Obtener modelos disponibles localmente
modelos = ollama.get_available_models()
print(f"Modelos locales: {modelos}")

# Generar respuesta con modelo local
respuesta = ollama.generate_response("¿Hola?")
print(respuesta)
```

## ⚙️ Parámetros de Configuración

| Parámetro | Rango | Descripción |
|-----------|-------|-------------|
| **Temperature** | 0.0 - 1.0 | Controla creatividad. 0 = determinístico, 1 = muy creativo |
| **Top P** | 0.0 - 1.0 | Diversidad de tokens. Típicamente 0.9 - 1.0 |
| **Max Tokens** | 256 - 8192 | Límite de tokens en respuesta |

**Recomendaciones:**

- **Análisis de datos / Código:** Temperature 0.2-0.4
- **Resúmenes / Reportes:** Temperature 0.5-0.7
- **Brainstorming / Creatividad:** Temperature 0.8-1.0

## 🔍 Solución de Problemas

### Error: "API KEY requerida"

```
❌ Error: Gemini: API KEY requerida
```

**Solución:** Ve a ⚙️ Configuración del Cerebro y añade una API KEY válida.

### Error: "ModuleNotFoundError"

```
❌ Error: openai no está instalado
```

**Solución:**
```bash
pip install openai anthropic
```

### Error: "Invalid API Key"

```
❌ Error: InvalidRequest: Invalid authentication credentials
```

**Solución:**
- Verifica que la API KEY sea correcta (cópiala nuevamente del panel de control)
- Asegúrate de no tener espacios en blanco
- Verifica que la cuenta tenga créditos/suscripción activa

### Error: "Ollama no responde"

```
❌ Error: Connection refused en localhost:11434
```

**Solución:**
1. Asegúrate de que Ollama esté corriendo:
   ```bash
   ollama serve
   ```
2. Verifica que puedas acceder: http://localhost:11434/api/tags
3. Descarga un modelo:
   ```bash
   ollama pull mistral
   ```

### El chat no genera respuestas

```
🚨 Error: No he podido establecer el enlace con [Proveedor]
```

**Checklist:**
- ✅ ¿API KEY es válida?
- ✅ ¿Proveedor está activo?
- ✅ ¿Conexión a internet es estable?
- ✅ ¿Modelo está disponible?
- ✅ ¿Cuenta tiene créditos?

## 📊 Comparativa de Proveedores

| Aspecto | Gemini | OpenAI | Claude | DeepSeek | Ollama |
|---------|--------|--------|--------|----------|--------|
| **Costo** | 💚 Gratis* | ⚠️ Pago | ⚠️ Pago | 💚 Bajo | 💚 Gratis |
| **Potencia** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| **Latencia** | 🟢 Rápido | 🟡 Medio | 🟡 Medio | 🟢 Rápido | 🟢 Muy rápido** |
| **Privacidad** | 🟡 Nube | 🔴 Nube | 🟡 Nube | 🟡 Nube | 🟢 Local |
| **Contexto** | 1M tokens | 128K tokens | 200K tokens | 64K tokens | Varía |
| **Razonamiento** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |

*Gemini: Gratis hasta cierto límite de requests  
**Ollama: Depende del hardware local

## 🔄 Cambiar de Proveedor

El cambio es instantáneo desde la interfaz:

1. Ve a **Inteligencia → Cerebro → ⚙️**
2. Cambia el proveedor
3. Ingresa la nueva API KEY
4. Haz clic en **🧪 Probar Conexión**
5. Guarda

El siguiente mensaje que envíes usará el nuevo proveedor automáticamente.

## 🛠️ Para Desarrolladores

### Crear un nuevo proveedor

1. Crea un archivo en `intelligence/providers/tu_proveedor.py`:

```python
from .base import BaseProvider, ProviderConfig

class TuProveedorProvider(BaseProvider):
    def _validate_config(self) -> None:
        # Validación
        pass
    
    def _initialize_client(self) -> None:
        # Inicializar cliente
        pass
    
    def generate_response(self, prompt: str, **kwargs) -> str:
        # Implementar generación
        pass
    
    def generate_response_stream(self, prompt: str, **kwargs):
        # Implementar streaming
        yield chunk
    
    def get_available_models(self) -> list:
        # Retornar modelos
        return ["modelo1", "modelo2"]
    
    def validate_connection(self) -> bool:
        # Validar conexión
        return True
```

2. Registra en `intelligence/providers/__init__.py`:

```python
from .tu_proveedor import TuProveedorProvider

PROVIDER_REGISTRY["Tu Proveedor"] = TuProveedorProvider
PROVIDER_DISPLAY_NAMES["Tu Proveedor"] = "🎯 Tu Proveedor"
```

3. ¡Listo! Aparecerá en el selectbox de proveedores.

## 📞 Soporte

- **Documentación oficial:**
  - [Google Gemini](https://ai.google.dev)
  - [OpenAI](https://platform.openai.com/docs)
  - [Anthropic](https://docs.anthropic.com)
  - [DeepSeek](https://platform.deepseek.com/docs)
  - [Ollama](https://github.com/ollama/ollama)

## ✅ Checklist de Implementación

- [x] Arquitectura modular de proveedores
- [x] Interfaz de configuración unificada
- [x] Soporte para 5 proveedores principales
- [x] Validación de conexiones
- [x] Documentación completa
- [x] Ejemplos de uso
- [x] Manejo de errores robusto
- [x] Compatible con Ull-Trone existente

---

**Versión:** 1.0  
**Última actualización:** 2026-04-25  
**Mantenedor:** CGT SaaS Team
