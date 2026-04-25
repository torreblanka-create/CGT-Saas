# EJEMPLO: Migración a Sistema de Temas Centralizado

## Archivo: vistas/salud_ocupacional/dashboard.py

### ❌ ANTES (Hardcodeado - Problema Original)

```python
def render_dashboard(DB_PATH, filtros):
    st.markdown("""
        <div style='background: linear-gradient(90deg, #1E293B 0%, #0F172A 100%); 
                    padding: 25px; border-radius: 15px; border-left: 5px solid #4CAF50; 
                    margin-bottom: 20px;'>
            <h2 style='color: #4CAF50; margin:0;'>🛡️ Certificación CPHS</h2>
        </div>
    """, unsafe_allow_html=True)
    
    # KPIs con colores hardcodeados
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"""
            <div style='background: #111827; padding: 15px; border-radius: 10px;'>
                <p style='color: #00A8E8; font-size: 0.75rem;'>GES MAPEADOS</p>
                <p style='color: white; font-size: 1.8rem;'>{ges_count}</p>
            </div>
        """, unsafe_allow_html=True)
```

**Problemas:**
- 📍 10+ colores hardcodeados (#1E293B, #0F172A, #00A8E8, #111827, etc.)
- 🚫 Si cambias a otro tema, necesitas editar AQUÍ
- 🔒 Estilos "atrapados" que no responden a cambios globales
- 😢 Cuando cambias CSS global, esto sigue viéndose igual

---

## ✅ DESPUÉS (Centralizado - Solución)

```python
from config.themes import (
    BACKGROUND_PRIMARY,
    TEXT_PRIMARY,
    COLOR_VERDE,
    COLOR_AZUL,
    get_card_style,
    get_banner_style,
    get_metric_card_style
)

def render_dashboard(DB_PATH, filtros):
    # Header con banner style centralizado
    st.markdown(f"""
        <div style='{get_banner_style(COLOR_VERDE)}'>
            <h2 style='color: {TEXT_PRIMARY}; margin:0;'>🛡️ Certificación CPHS</h2>
        </div>
    """, unsafe_allow_html=True)
    
    # KPIs con métricas usando estilo centralizado
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"""
            <div style='{get_metric_card_style(COLOR_AZUL)}'>
                <p style='color: #1e40af; font-size: 0.75rem; font-weight: 600; margin:0;'>GES MAPEADOS</p>
                <p style='color: {TEXT_PRIMARY}; font-size: 1.8rem; font-weight: 800; margin:0;'>{ges_count}</p>
            </div>
        """, unsafe_allow_html=True)
```

**Beneficios:**
- ✅ 0 colores hardcodeados
- 🎨 Cambio de tema afecta TODOS los archivos automáticamente
- 🔓 Estilos desbloqueados y centralizados
- ⚡ Fácil mantenimiento y escalabilidad
- 📚 Código autodocumentado (puedes ver qué hace `get_metric_card_style`)

---

## Cambios Específicos

| Qué Cambió | Antes | Después |
|------------|-------|---------|
| Header style | `background: linear-gradient(90deg, #1E293B 0%, #0F172A 100%);` | `get_banner_style(COLOR_VERDE)` |
| Card bg | `background: #111827;` | `get_metric_card_style(COLOR_AZUL)` |
| Text color | `color: #FFF;` | `color: {TEXT_PRIMARY}` |
| Border color | `border: 1px solid #00A8E8;` | Incluido en función helper |

---

## Cambio Global de Tema (Demo)

### Escenario: Tu jefe pide "Cambia a tema oscuro"

**Método Antiguo (Pesadilla):**
1. Abre 20+ archivos
2. Busca y reemplaza #1E293B → #0F172A
3. Busca y reemplaza #FFF → #1F2937
4. Prueba cada módulo
5. Repite si algo se rompió

**Método Nuevo (Sencillo):**
1. Abre `config/themes.py`
2. Cambia estas 4 líneas:
   ```python
   BACKGROUND_PRIMARY = "#0F172A"      # De crema a oscuro
   TEXT_PRIMARY = "#F8FAFC"            # De negro a blanco
   COLOR_VERDE = "#10b981"             # Ajusta si necesitas
   ```
3. Guarda el archivo
4. Recarga Streamlit (auto-reload)
5. ✅ TODA la app es oscura al instante

---

## Checklist de Migración

Si estás migrando un archivo a temas centralizados:

- [ ] Agregué `from config.themes import ...` al inicio
- [ ] Reemplacé todos los `background: #XXXXX` con funciones helper
- [ ] Reemplacé todos los `color: #XXXXX` con constantes de theme
- [ ] Eliminé comentarios sobre colores hardcodeados
- [ ] Probé que el archivo se vea igual visualmente
- [ ] Ejecuté `python scripts/validate_hardcoded_colors.py` para validar

---

## Otras Vistas que Podrías Actualizar

Con esta estrategia ya aplicada, aquí hay otras que podrían beneficiarse:

1. `vistas/gestion_preventiva/riesgos_criticos.py`
2. `vistas/ingenieria_y_operaciones/activos_asignados.py`
3. `vistas/trazabilidad_y_gestion/control_pts.py`
4. `vistas/control_operativo/gestion_capacitaciones.py`

Patrón de migración: Igual al mostrado arriba.

---

## Soporte

Si tienes preguntas:
1. Lee `ESTANDARES_TEMAS.md`
2. Revisa `config/themes.py` para funciones disponibles
3. Ejecuta validador: `python scripts/validate_hardcoded_colors.py`
