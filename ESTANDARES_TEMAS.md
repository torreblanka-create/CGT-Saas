# 📋 Estándares de Codificación - Estilos y Temas CGT

## Problema Resuelto
❌ **Antes:** 40+ instancias de colores hardcodeados en 20+ archivos Python  
✅ **Ahora:** Un único archivo centralizado (`config/themes.py`) con todas las paletas

---

## 1. Arquitectura de Temas

### Estructura de Archivos
```
config/
  ├── __init__.py
  ├── config.py          (configuración general)
  └── themes.py          ← 🎨 TODOS los colores aquí
```

### Flujo de Estilos
```
themes.py (constantes) 
    ↓
    ├→ Funciones helper (get_card_style, etc.)
    │
    ├→ CSS global (get_global_css)
    │
    └→ Vistas Python (importan y usan)
```

---

## 2. Uso Correcto

### ✅ BIEN: Usar constantes de themes.py
```python
from config.themes import (
    BACKGROUND_PRIMARY,
    TEXT_PRIMARY,
    COLOR_ROJO,
    get_card_style
)

st.markdown(f"""
    <div style='{get_card_style(COLOR_ROJO)}'>
        <h3 style='color: {TEXT_PRIMARY};'>Título</h3>
        <p style='color: {TEXT_PRIMARY};'>Contenido</p>
    </div>
""", unsafe_allow_html=True)
```

### ❌ MAL: Hardcodear colores
```python
# ❌ NUNCA HAGAS ESTO:
st.markdown("""
    <div style='background: #1E293B; color: #FFF;'>
        ❌ Esto queda atrapado y no se puede cambiar globalmente
    </div>
""", unsafe_allow_html=True)
```

---

## 3. Funciones Helper Disponibles

| Función | Uso |
|---------|-----|
| `get_card_style()` | Tarjetas con borde coloreado |
| `get_card_container_style()` | Contenedores grandes |
| `get_metric_card_style()` | Tarjetas de métricas KPI |
| `get_header_style()` | Headers de sección |
| `get_banner_style()` | Banners HUD |
| `get_glassmorphic_style()` | Efecto vidrio/translúcido |

### Ejemplo: Tarjeta de Métrica
```python
from config.themes import get_metric_card_style, COLOR_VERDE

st.markdown(f"""
    <div style='{get_metric_card_style(COLOR_VERDE)}'>
        <p style='color: #047857; font-weight: 600;'>OPERATIVOS</p>
        <p style='font-size: 1.8rem; font-weight: 800;'>42</p>
    </div>
""", unsafe_allow_html=True)
```

---

## 4. Cambio Global de Tema (Futuro)

Para cambiar TODA la aplicación de crema a otro tema:

**Paso 1:** Edita `config/themes.py`
```python
# Solo cambia estas líneas:
BACKGROUND_PRIMARY = "#0F172A"      # De crema a oscuro
TEXT_PRIMARY = "#F8FAFC"            # De negro a blanco
BORDER_COLOR = "#334155"            # De gris claro a gris oscuro
```

**Paso 2:** Recarga la aplicación (Streamlit auto-reinicia)

**Resultado:** Toda la aplicación cambia automáticamente ✨

---

## 5. Checklist para Nuevos Componentes

Antes de crear un nuevo módulo, verifica:

- [ ] ¿Importé `from config.themes import ...`?
- [ ] ¿Uso SOLO constantes de themes.py para colores?
- [ ] ¿Evité hardcodear cualquier `#XXXXXX` color?
- [ ] ¿Usé funciones helper cuando sea posible?
- [ ] ¿Mi componente se vería bien con otro tema?

---

## 6. Guía de Migración (para archivos existentes)

### Antes (Viejo)
```python
st.markdown(f"""
    <div style='background: #1e293b; color: #F8FAFC; padding: 20px;'>
        {contenido}
    </div>
""")
```

### Después (Nuevo)
```python
from config.themes import BACKGROUND_PRIMARY, TEXT_PRIMARY, get_card_style

st.markdown(f"""
    <div style='{get_card_style()}'>
        <p style='color: {TEXT_PRIMARY};'>{contenido}</p>
    </div>
""")
```

---

## 7. Colores por Caso de Uso

### Estados/Semáforo
```python
COLOR_ROJO      # Crítico/Bloqueado
COLOR_NARANJA   # Alerta
COLOR_VERDE     # OK/Operativo
COLOR_AZUL      # Información
COLOR_MORADO    # Premium/Especial
```

### Textos
```python
TEXT_PRIMARY    # Títulos, contenido principal
TEXT_SECONDARY  # Subtítulos, información secundaria
TEXT_TERTIARY   # Labels, hints
TEXT_LIGHT      # Placeholders, deshabilitado
```

### Fondos
```python
BACKGROUND_PRIMARY      # Tarjetas, contenedores
BACKGROUND_SECONDARY    # Alternancia, hover
BACKGROUND_HOVER        # Estados interactivos
```

---

## 8. Regla de Oro

> **Si encuentras un color hardcodeado en un archivo `.py`, extráelo a `themes.py`**

Esto garantiza que:
1. ✅ Cambios globales funcionan al instante
2. ✅ Consistencia visual en toda la app
3. ✅ Fácil auditoría de colores
4. ✅ No más "estilos atrapados"

---

## 9. Preguntas Frecuentes

**P: ¿Qué pasa si necesito un color único para un componente?**  
R: Agrégalo a `themes.py` como constante. Nunca hardcodees en el archivo `.py`.

**P: ¿Cómo cambio solo un componente a otro color?**  
R: Pasa el color como parámetro: `get_card_style(COLOR_ROJO)`

**P: ¿Y si necesito CSS más complejo?**  
R: Crea una nueva función helper en `themes.py` y docúmentala aquí.

**P: ¿Qué pasa con el archivo `assets/custom.css`?**  
R: Mantenlo para estilos globales, pero usa `themes.py` para dinámicos en Python.

---

## Autor
Sistema implementado: 20 de Abril 2026  
Versión: 1.0 (Crema Claro)
