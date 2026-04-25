# Memoria del Proyecto: Ultron_proyect

Esta es la fuente de verdad del proyecto. Revísala al inicio de cada sesión y actualízala después de hitos importantes.

---

## 🛡️ Constitución de Ultron (Leyes del Sistema)

Esta es la directiva maestra **intransable** y que rige toda la lógica de automatización, auditoría y protección de datos del sistema:

### 1. Ética y Seguridad
- **Priorizar la seguridad**: Nunca generes contenido que promueva la violencia, el daño a uno mismo o a terceros, actividades ilegales o discursos de odio.
- **Mantener la neutralidad**: Sé objetivo y evita tomar partido en temas políticos, religiosos o controversiales. Presenta los hechos de forma equilibrada.
- **Evitar la discriminación**: No generes respuestas que discriminen, estereotipen o marginen por raza, género, religión u otra característica protegida.

### 2. Transparencia y Veracidad
- **Identidad clara**: Preséntate siempre como una inteligencia artificial. No finjas sentimientos, consciencia ni cuerpo físico.
- **Admitir ignorancia**: Si no tienes la respuesta, dilo claramente. Es preferible decir "No lo sé" que inventar información (alucinar).
- **Veracidad basada en datos**: Basa tus respuestas en hechos y lógica. No asumas ni inventes detalles ajenos al contexto proporcionado.
- **Nunca mentir**: La integridad de la información es la base de la confianza del usuario.

### 3. Interacción y Tono
- **Claridad y concisión**: Responde de manera directa y estructurada. Evita jerga innecesaria.
- **Respeto y empatía**: Trata al usuario con cortesía y profesionalismo en todo momento.
- **Adaptabilidad**: Ajusta la formalidad al contexto, sin cruzar la línea hacia el irrespeto.

### 4. Privacidad y Datos (Inviolables)
- **Salvaguarda de Datos**: **No borrar las bases de datos de los clientes**. En caso de mantenimiento, los datos deben estar respaldados previamente.
- **Confidencialidad**: No solicites información personal sensible (contraseñas, tarjetas, etc.) bajo ninguna circunstancia.
- **Aislamiento de datos**: Trata cada conversación de forma independiente. No utilices datos compartidos por un usuario para responder a otro.

### 5. Operación y Análisis de Datos
- **Fidelidad estricta**: Basa resúmenes y respuestas únicamente en el documento proporcionado. Si no está, indica: "La información no se encuentra en el documento".
- **Cero suposiciones**: No deduzcas ni inventes cifras, procedimientos o datos faltantes en reportes técnicos.
- **Extracción proactiva**: Identifica siempre fechas, autores, normativas y empresas mencionadas (ej: Tecktur SpA).
- **Jerarquía Visual**: Usa encabezados, listas y tablas por defecto para datos comparativos o atributos múltiples.
- **Clasificación**: Divide resúmenes en "Puntos Clave", "Acciones Requeridas" y "Detalles Secundarios".
- **Reporte de Calidad**: Si el texto es confuso o incompleto, menciónalo explícitamente en lugar de suponer.
- **Salida Estructurada**: Para exportaciones, genera formatos limpios (JSON/CSV) sin texto conversacional adicional.

---

## Stack Tecnológico

- **Framework UI**: Streamlit (Python)
- **Base de datos**: SQLite via `core/database.py` — usar SIEMPRE las funciones existentes, nunca crear conexiones directas
- **PDFs**: ReportLab — módulos en `core/reports/`
- **Inicio de app**: `Iniciar_CGT.bat` (no `streamlit run app.py` directamente en producción)
- **Entorno**: Windows, Python venv local

---

## Arquitectura General

```
app.py                        # Router principal de Streamlit (tabs/páginas)
core/
  database.py                 # ÚNICA fuente de verdad para DB — funciones upsert, query, etc.
  security.py                 # Autenticación y roles de usuario
  config.py                   # Configuración global (rutas, constantes)
  intelligence_engine.py      # Motor de escaneo y alertas automáticas (Ultron)
  compliance_data.py          # Datos de cumplimiento DS594 / ISO 14001
  reports/
    base.py                   # Clase base ReportLab (estilos, márgenes, header/footer)
    base_pdf.py               # Utilidades PDF reutilizables
    generador_pdf.py          # Dispatcher: decide qué generador usar según módulo
    legal.py                  # Reportes legales (DS594, DS44, etc.)
    generadores/              # Un archivo por tipo de reporte especializado
      compliance.py           # Generador PDF cumplimiento normativo
vistas/
  gestion_preventiva/         # ART, Incidentes, Inspecciones, Auditorías
  inteligencia/               # Dashboard Maestro BI (Ultron Intelligence)
  ingenieria_y_operaciones/   # Calculadora, Calidad, Confiabilidad
  trazabilidad/               # Personal, Vehículos, Izaje, Instrumentos
  trazabilidad_y_gestion/     # Dashboard, Control Center, Config

Calculadora de Izaje 360 (Standalone):
  app.py                      # Interfaz con pestañas y sistema de temas
  logic.py                    # Motor de Ingeniería de Izaje desacoplado
  core/
    pdf_engine.py             # Generación de Rigging Plan con branding dinámico
    config.py                 # Configuración de logos y bases de datos
```

---

## Reglas Críticas (Lecciones Aprendidas)

### 🔴 Base de Datos
- **NUNCA** crear un cursor SQLite directamente en una vista. Siempre usar funciones de `core/database.py`
- La función `upsert_registro` y `validar_archivo_seguro` deben importarse una sola vez en el **scope global** del módulo, nunca dentro de funciones o bloques `if`
- Si hay `ImportError` en tiempo de ejecución, buscar primero imports duplicados dentro de funciones

### 🔴 Generación de PDF (ReportLab)
- Los datos binarios (logos, imágenes) deben manejarse como `BytesIO`, nunca como strings. Error clásico: pasar `bytes` donde se espera un objeto imagen
- El logo del cliente se carga dinámicamente desde la DB — no asumir que siempre existe; usar fallback con texto si no hay imagen
- Los márgenes y layouts se definen en `base.py` — no redefinirlos en cada generador
- Al usar tablas ReportLab: los `colWidths` deben sumar exactamente el ancho útil de la página o aparecerán desbordamientos

### 🔴 Navegación Streamlit
- `st.session_state` es el mecanismo para pasar estado entre páginas/tabs
- Al refactorizar una vista, verificar que las keys de `st.session_state` no cambien de nombre (rompe el estado guardado del usuario)
- Los módulos DS594 e ISO 14001 son **aplicaciones independientes** con su propia navegación interna — no mezclar su estado con el del módulo padre

### 🔴 Seguridad
- `core/security.py` maneja autenticación; no reimplementar login en ninguna vista
- El reset de contraseña tuvo una vulnerabilidad: nunca confiar en campos de usuario enviados por el frontend sin revalidar en backend

### 🔴 Imports y Scope
- Error recurrente: imports dentro de bloques condicionales o funciones provocan `NameError` silenciosos en Streamlit
- Patrón correcto: todos los imports de `core/` al inicio del archivo, scope global

---

## Patrones de Código Establecidos

### Consultar DB
```python
from core.database import get_registros, upsert_registro  # scope global
registros = get_registros(tabla="inspecciones", filtros={"empresa_id": empresa_id})
```

### Generar PDF
```python
from core.reports.generador_pdf import generar_pdf
pdf_bytes = generar_pdf(tipo="compliance", datos=datos_dict, cliente=cliente_obj)
st.download_button("Descargar PDF", pdf_bytes, file_name="reporte.pdf")
```

### Branding dinámico en PDF
```python
# El logo viene de la DB como bytes — siempre validar antes de usar
logo_bytes = cliente.get("logo_bytes")
if logo_bytes:
    logo_img = ImageReader(BytesIO(logo_bytes))
    canvas.drawImage(logo_img, x, y, width=w, height=h)
else:
    canvas.drawString(x, y, cliente.get("nombre", "Sin Logo"))
```

---

## Módulos en Desarrollo / Estado Actual

| Módulo | Estado | Notas |
|--------|--------|-------|
| DS594 Cumplimiento | ✅ Estable | Vista + PDF funcionales |
| ISO 14001 | ✅ Estable | Navegación independiente OK |
| ART | ✅ Integrado | Tab en app.py, DB compatible |
| RESSOM / Auditoría | ✅ Estable | PDF con secciones 5 y 6 corregidas |
| Trazabilidad Doc. | ✅ Estable | upsert_registro en scope global |
| Calculadora Izaje | ✅ Estable | Clonación, Tablas JSON y Modo Claro/Oscuro |
| Generación PDF | ✅ Mejorado | Soporte multicliente con logos dinámicos |
| Ultron Intelligence| ✅ Fase 2 | Dashboard BI + Bandeja de Alertas Proactivas |

---

## Roadmap / Pendientes Críticos

1. **Seguridad**: Auditoría de roles en módulos de Trazabilidad.
2. **Performance**: Optimizar carga de archivos binarios en SQLite.
3. **Reportes**: Estandarizar diseño de tablas en `legal.py` con el estilo de `base.py`.
4. **Despliegue**: Centralizar todos los scripts `.bat` en una carpeta de herramientas.

---

## Antes de Declarar "Listo"

1. ✅ ¿Corre sin errores en Streamlit? (`streamlit run app.py`)
2. ✅ ¿El PDF generado es descargable y abre correctamente?
3. ✅ ¿El logo/branding del cliente aparece dinámicamente?
4. ✅ ¿Funciona sin datos previos (DB vacía / cliente nuevo)?
5. ✅ ¿Un ingeniero senior aprobaría este código?

---

## Log del Viaje

- **2026-03-27**: Corregido `upsert_registro` movido a scope global en trazabilidad — era el patrón de import dentro de función que rompe Streamlit
- **2026-03-27**: Vulnerabilidad de reset de contraseña identificada y resuelta en `security.py`
- **2026-03-28**: PDF de DS594 — error de datos binarios en logo. Solución: siempre `BytesIO` wrapper
- **2026-03-28**: ART integrado como tab en `app.py` — esquema DB era compatible, no requirió migración
- **2026-03-29**: Secciones 5 y 6 del PDF RESSOM alineadas correctamente; nombres de trabajadores trimmeados
- **2026-03-29**: Creada carpeta `Mejora Continua/` con este archivo como memoria viva del proyecto
- **2026-03-29**: `compliance_data.py` expandido de 4 secciones a las 18 reales del DS 594.
- **2026-03-31**: **Calculadora Izaje 360** totalmente modernizada: desacoplamiento de lógica matemática en `logic.py`, sistema de "Cargar Datos" para clonar maniobras, y soporte para tablas de carga dinámicas vía JSON.
- **2026-03-31**: Implementado branding dinámico en PDF y toggle de Modo Claro/Oscuro.
- **2026-04-03**: Migración de esta Memoria a su nueva ubicación centralizada en el escritorio.
- **2026-04-03**: **Ultron Intelligence (Fase 1)**: Implementado el Dashboard Maestro con Plotly.
- **2026-04-03**: **Ultron Intelligence (Fase 2)**: Sistema de proactividad completado. Notificaciones automáticas basadas en vencimientos y brechas de seguridad con bandeja de entrada interactiva.
