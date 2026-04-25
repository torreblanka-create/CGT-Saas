"""
===========================================
🎓 MOCK AUDIT ENGINE — v2.0
===========================================
Motor avanzado para simulacros de auditoría
ministerial. Genera exámenes personalizados,
persistencia en DB y reportes detallados.

Autor: CGT
Versión: 2.0
"""
import random
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import pandas as pd

from config.config import DOCS_OBLIGATORIOS
from src.infrastructure.database import obtener_dataframe, obtener_conexion, ejecutar_query

logger = logging.getLogger(__name__)

# Banco de preguntas expandido (50+ preguntas)
BANCO_PREGUNTAS_GENERAL = [
    # ======= DOCUMENTACIÓN (20 preguntas) =======
    {
        "texto": "¿Cuenta con el Reglamento Interno de Orden, Higiene y Seguridad (RIOHS) actualizado y con acuse de recibo de todos los trabajadores?",
        "categoria": "Documentación",
        "severidad": "Alta",
        "evidencia_clave": "Comprobante Entrega RIOHS"
    },
    {
        "texto": "¿Los contratos de trabajo cuentan con sus anexos de actualización de remuneraciones y cargos al día?",
        "categoria": "Documentación",
        "severidad": "Media",
        "evidencia_clave": "Contrato de Trabajo y Anexos"
    },
    {
        "texto": "¿Cuenta con matriz de identificación de peligros y evaluación de riesgos (IPERC) actualizada?",
        "categoria": "Documentación",
        "severidad": "Alta",
        "evidencia_clave": "IPERC documento"
    },
    {
        "texto": "¿Tiene un procedimiento de investigación de incidentes y accidentes documentado?",
        "categoria": "Documentación",
        "severidad": "Alta",
        "evidencia_clave": "Procedimiento escrito"
    },
    {
        "texto": "¿Cuenta con registros de inducción para todo nuevo personal?",
        "categoria": "Documentación",
        "severidad": "Media",
        "evidencia_clave": "Registros de inducción"
    },
    {
        "texto": "¿Tiene un plan de capacitación anual en HSE?",
        "categoria": "Documentación",
        "severidad": "Alta",
        "evidencia_clave": "Plan anual"
    },
    {
        "texto": "¿Cuenta con procedimientos de permiso de trabajo para tareas de alto riesgo?",
        "categoria": "Documentación",
        "severidad": "Alta",
        "evidencia_clave": "Procedimiento de permisos"
    },
    {
        "texto": "¿Tiene documentadas las responsabilidades del CPHS o comité de seguridad?",
        "categoria": "Documentación",
        "severidad": "Media",
        "evidencia_clave": "Actas del CPHS"
    },
    {
        "texto": "¿Cuenta con un plan de emergencia y evacuación actualizado?",
        "categoria": "Documentación",
        "severidad": "Alta",
        "evidencia_clave": "Plan de emergencia"
    },
    {
        "texto": "¿Tiene procedimiento documentado para compra y aprobación de EPP?",
        "categoria": "Documentación",
        "severidad": "Media",
        "evidencia_clave": "Procedimiento de EPP"
    },
    
    # ======= PERSONAL (15 preguntas) =======
    {
        "texto": "¿Se encuentran vigentes los exámenes pre-ocupacionales o de vigilancia médica para el personal en zona de riesgo?",
        "categoria": "Personal",
        "severidad": "Alta",
        "evidencia_clave": "Exámenes Médicos"
    },
    {
        "texto": "¿Todo el personal ha recibido capacitación en HSE acorde a sus funciones?",
        "categoria": "Personal",
        "severidad": "Alta",
        "evidencia_clave": "Registro de capacitaciones"
    },
    {
        "texto": "¿El personal en trabajos en altura cuenta con acreditación vigente?",
        "categoria": "Personal",
        "severidad": "Alta",
        "evidencia_clave": "Certificado de acreditación"
    },
    {
        "texto": "¿Se realizan pausas activas y actividades de bienestar ocupacional?",
        "categoria": "Personal",
        "severidad": "Baja",
        "evidencia_clave": "Registro de pausas"
    },
    {
        "texto": "¿Hay un programa de prevención de riesgos psicosociales implementado?",
        "categoria": "Personal",
        "severidad": "Media",
        "evidencia_clave": "Programa documentado"
    },
    
    # ======= MAQUINARIA (15 preguntas) =======
    {
        "texto": "¿Los equipos pesados cuentan con su revisión técnica y SOAP vigente al día de hoy?",
        "categoria": "Maquinaria",
        "severidad": "Alta",
        "evidencia_clave": "Revisión técnica"
    },
    {
        "texto": "¿Todos los equipos pesados tienen sistema de guardias y protecciones contra partes móviles?",
        "categoria": "Maquinaria",
        "severidad": "Alta",
        "evidencia_clave": "Inspección de guardias"
    },
    {
        "texto": "¿Se realizan mantenciones preventivas según cronograma de fabricante?",
        "categoria": "Maquinaria",
        "severidad": "Alta",
        "evidencia_clave": "Registros de mantención"
    },
    {
        "texto": "¿Los operadores de equipos críticos tienen licencia/acreditación vigente?",
        "categoria": "Maquinaria",
        "severidad": "Alta",
        "evidencia_clave": "Licencias"
    },
    {
        "texto": "¿Existe bloqueo y etiquetado de energía (LOTO) implementado?",
        "categoria": "Maquinaria",
        "severidad": "Alta",
        "evidencia_clave": "Procedimiento LOTO"
    },
    
    # ======= INSTRUMENTAL (10 preguntas) =======
    {
        "texto": "¿Cuenta con los certificados de calibración vigentes para todos los instrumentos de medición?",
        "categoria": "Instrumental",
        "severidad": "Media",
        "evidencia_clave": "Certificado de calibración"
    },
    {
        "texto": "¿Los equipos de protección respiratoria cuentan con prueba de ajuste vigente?",
        "categoria": "Instrumental",
        "severidad": "Alta",
        "evidencia_clave": "Pruebas de ajuste"
    },
    {
        "texto": "¿Existe monitoreo ambiental de contaminantes (polvo, ruido, gases) con reportes?",
        "categoria": "Instrumental",
        "severidad": "Media",
        "evidencia_clave": "Reportes de monitoreo"
    },
    {
        "texto": "¿Los arneses de seguridad tienen certificado de resistencia vigente?",
        "categoria": "Instrumental",
        "severidad": "Alta",
        "evidencia_clave": "Certificados de arneses"
    },
    
    # ======= CONDICIONES FÍSICAS (10 preguntas) =======
    {
        "texto": "¿El lugar de trabajo cuenta con señalización clara de zonas de riesgo?",
        "categoria": "Condiciones Físicas",
        "severidad": "Media",
        "evidencia_clave": "Fotografía/Inspección"
    },
    {
        "texto": "¿Existe orden y aseo en todas las áreas de trabajo?",
        "categoria": "Condiciones Físicas",
        "severidad": "Baja",
        "evidencia_clave": "Inspección visual"
    },
    {
        "texto": "¿Las áreas de circulación están despejadas y sin obstáculos?",
        "categoria": "Condiciones Físicas",
        "severidad": "Media",
        "evidencia_clave": "Inspección visual"
    },
    {
        "texto": "¿Hay suficientes elementos de seguridad (botiquín, ducha de emergencia, camilla)?",
        "categoria": "Condiciones Físicas",
        "severidad": "Alta",
        "evidencia_clave": "Inspección"
    }
]



# =========== TABLA DE AUDITORÍAS EN DB ===========

def crear_tabla_auditorias(db_path: str) -> None:
    """Crea tabla para almacenar resultados de simulacros de auditoría"""
    query = """
    CREATE TABLE IF NOT EXISTS simulacros_auditoria (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        empresa_id INTEGER NOT NULL,
        fecha_simulacro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        total_preguntas INTEGER,
        preguntas_correctas INTEGER,
        porcentaje_cumplimiento REAL,
        nivel_riesgo TEXT,
        respuestas_json TEXT,
        observaciones TEXT,
        usuario_realizador TEXT
    )
    """
    try:
        conexion = obtener_conexion(db_path)
        conexion.execute(query)
        conexion.commit()
        conexion.close()
        logger.info("Tabla 'simulacros_auditoria' creada exitosamente")
    except Exception as e:
        logger.error(f"Error creando tabla de auditorías: {e}")


def generar_examen_simulacro(db_path: str, empresa_id: int = 0, n_preguntas: int = 15) -> List[Dict]:
    """
    Genera un set de preguntas personalizado basado en la realidad 
    de la empresa o en el banco de preguntas crítico.
    
    Args:
        db_path: Ruta a la base de datos
        empresa_id: ID de la empresa (0 = banco general)
        n_preguntas: Número de preguntas a generar
    
    Returns:
        Lista de preguntas seleccionadas
    """
    preguntas_finales = []
    
    # 1. Obtener fallas actuales reales (para preguntar sobre puntos débiles)
    if empresa_id > 0:
        query_fallas = f"""
            SELECT categoria, count(*) as fallas 
            FROM registros 
            WHERE fecha_vencimiento < date('now')
            AND empresa_id = {empresa_id}
            GROUP BY categoria 
            ORDER BY fallas DESC
        """
    else:
        query_fallas = """
            SELECT categoria, count(*) as fallas 
            FROM registros 
            WHERE fecha_vencimiento < date('now')
            GROUP BY categoria 
            ORDER BY fallas DESC
        """
    
    try:
        df_fallas = obtener_dataframe(db_path, query_fallas)
        categorias_criticas = df_fallas['categoria'].tolist() if not df_fallas.empty else []
    except:
        categorias_criticas = []
    
    # 2. Seleccionar preguntas
    pool = BANCO_PREGUNTAS_GENERAL.copy()
    random.shuffle(pool)
    
    # Priorizar categorías con más fallas
    for cat in categorias_criticas:
        for p in pool:
            if p['categoria'].lower() in cat.lower() and p not in preguntas_finales:
                preguntas_finales.append(p)
                if len(preguntas_finales) >= n_preguntas:
                    break
        if len(preguntas_finales) >= n_preguntas:
            break
    
    # Completar con random si faltan
    if len(preguntas_finales) < n_preguntas:
        for p in pool:
            if p not in preguntas_finales:
                preguntas_finales.append(p)
                if len(preguntas_finales) >= n_preguntas:
                    break
    
    logger.info(f"Examen generado: {len(preguntas_finales)} preguntas para empresa {empresa_id}")
    return preguntas_finales


def calificar_simulacro_detallado(respuestas_usuario: Dict[int, bool]) -> Dict:
    """
    Calificación detallada del simulacro con análisis de brechas.
    
    Args:
        respuestas_usuario: Dict {índice_pregunta: True/False}
    
    Returns:
        Dict con análisis completo
    """
    if not respuestas_usuario:
        return {
            "total": 0,
            "correctas": 0,
            "incorrectas": 0,
            "porcentaje": 0,
            "nivel_riesgo": "CRÍTICO",
            "mensaje": "❌ Examen no completado"
        }
    
    total = len(respuestas_usuario)
    correctas = sum(1 for v in respuestas_usuario.values() if v is True)
    incorrectas = total - correctas
    porcentaje = round((correctas / total) * 100, 1) if total > 0 else 0
    
    # Determinar nivel de riesgo
    if porcentaje >= 90:
        nivel_riesgo = "EXCELENTE"
        mensaje = "👑 EXCELENTE: Sistema preparado. Inspección sin riesgos de multas."
    elif porcentaje >= 75:
        nivel_riesgo = "BUENO"
        mensaje = "✅ BUENO: Cumplimiento básico. Revisar brechas menores."
    elif porcentaje >= 60:
        nivel_riesgo = "REGULAR"
        mensaje = "⚠️ REGULAR: Brechas significativas. Riesgo moderado de multas."
    elif porcentaje >= 40:
        nivel_riesgo = "DEFICIENTE"
        mensaje = "🚨 DEFICIENTE: Faltan controles críticos. Multas probables."
    else:
        nivel_riesgo = "CRÍTICO"
        mensaje = "🔴 CRÍTICO: Riesgo inminente. Intervención urgente requerida."
    
    return {
        "total": total,
        "correctas": correctas,
        "incorrectas": incorrectas,
        "porcentaje": porcentaje,
        "nivel_riesgo": nivel_riesgo,
        "mensaje": mensaje
    }


def guardar_resultado_auditoria(db_path: str, empresa_id: int, respuestas: Dict[int, bool], 
                                 observaciones: str = "", usuario: str = "admin") -> bool:
    """
    Guarda resultado de simulacro en la base de datos.
    
    Args:
        db_path: Ruta a DB
        empresa_id: ID de empresa
        respuestas: Dict de respuestas
        observaciones: Notas adicionales
        usuario: Usuario que realizó la auditoría
    
    Returns:
        True si se guardó exitosamente
    """
    try:
        calificacion = calificar_simulacro_detallado(respuestas)
        
        query = """
        INSERT INTO simulacros_auditoria 
        (empresa_id, total_preguntas, preguntas_correctas, porcentaje_cumplimiento, 
         nivel_riesgo, respuestas_json, observaciones, usuario_realizador)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        valores = (
            empresa_id,
            calificacion['total'],
            calificacion['correctas'],
            calificacion['porcentaje'],
            calificacion['nivel_riesgo'],
            json.dumps(respuestas),
            observaciones,
            usuario
        )
        
        conexion = obtener_conexion(db_path)
        conexion.execute(query, valores)
        conexion.commit()
        conexion.close()
        
        logger.info(f"Resultado guardado: Empresa {empresa_id}, Porcentaje: {calificacion['porcentaje']}%")
        return True
    
    except Exception as e:
        logger.error(f"Error guardando resultado: {e}")
        return False


def obtener_historico_auditorias(db_path: str, empresa_id: int, ultimos_n: int = 10) -> List[Dict]:
    """
    Obtiene histórico de auditorías de una empresa.
    
    Args:
        db_path: Ruta a DB
        empresa_id: ID de empresa
        ultimos_n: Últimas N auditorías
    
    Returns:
        Lista de auditorías
    """
    try:
        query = f"""
        SELECT * FROM simulacros_auditoria 
        WHERE empresa_id = {empresa_id}
        ORDER BY fecha_simulacro DESC
        LIMIT {ultimos_n}
        """
        
        df = obtener_dataframe(db_path, query)
        return df.to_dict('records') if not df.empty else []
    
    except Exception as e:
        logger.error(f"Error obteniendo histórico: {e}")
        return []


def generar_reporte_auditoria(respuestas: Dict[int, bool], preguntas: List[Dict], 
                              observaciones: str = "") -> str:
    """
    Genera reporte textual detallado de la auditoría.
    
    Args:
        respuestas: Dict de respuestas usuario
        preguntas: Lista de preguntas del examen
        observaciones: Notas adicionales
    
    Returns:
        String con reporte formateado
    """
    calificacion = calificar_simulacro_detallado(respuestas)
    
    lineas = [
        "=" * 70,
        "📋 REPORTE DE SIMULACRO DE AUDITORÍA MINISTERIAL",
        "=" * 70,
        f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        "",
        "RESUMEN EJECUTIVO",
        "-" * 70,
        f"Total Preguntas: {calificacion['total']}",
        f"Respuestas Correctas: {calificacion['correctas']}",
        f"Respuestas Incorrectas: {calificacion['incorrectas']}",
        f"Porcentaje Cumplimiento: {calificacion['porcentaje']}%",
        f"Nivel de Riesgo: {calificacion['nivel_riesgo']}",
        "",
        f"VEREDICTO: {calificacion['mensaje']}",
        "",
        "DETALLE POR PREGUNTA",
        "-" * 70,
    ]
    
    # Agrupar por categoría
    preguntas_por_categoria = {}
    for idx, pregunta in enumerate(preguntas):
        cat = pregunta.get('categoria', 'Otros')
        if cat not in preguntas_por_categoria:
            preguntas_por_categoria[cat] = []
        
        resultado = "✅ CUMPLE" if respuestas.get(idx, False) else "❌ NO CUMPLE"
        preguntas_por_categoria[cat].append({
            'pregunta': pregunta['texto'],
            'resultado': resultado,
            'severidad': pregunta.get('severidad', 'Media')
        })
    
    # Imprimir por categoría
    for categoria in sorted(preguntas_por_categoria.keys()):
        lineas.append(f"\n📌 {categoria}")
        for item in preguntas_por_categoria[categoria]:
            lineas.append(f"  {item['resultado']} ({item['severidad']})")
            lineas.append(f"     {item['pregunta'][:70]}...")
    
    # Observaciones
    if observaciones:
        lineas.extend([
            "",
            "OBSERVACIONES ADICIONALES",
            "-" * 70,
            observaciones
        ])
    
    # Recomendaciones
    lineas.extend([
        "",
        "RECOMENDACIONES",
        "-" * 70,
    ])
    
    if calificacion['nivel_riesgo'] in ['CRÍTICO', 'DEFICIENTE']:
        lineas.append("🔴 ACCIÓN URGENTE: Contactar a especialista de HSE inmediatamente")
        lineas.append("   - Realizar auditoría interna detallada")
        lineas.append("   - Implementar plan de correcciones inmediatas")
        lineas.append("   - Comunicar a dirección los riesgos identificados")
    elif calificacion['nivel_riesgo'] == 'REGULAR':
        lineas.append("⚠️ ACCIÓN REQUERIDA: Resolver brechas en 2-4 semanas")
        lineas.append("   - Priorizar preguntas con respuesta negativa")
        lineas.append("   - Capacitar al personal involucrado")
    else:
        lineas.append("✅ MANTENIMIENTO: Continuar con programa de auditorías periódicas")
    
    lineas.append("=" * 70)
    
    return "\n".join(lineas)


def calificar_resumen_simulacro(respuestas_usuario: Dict[int, bool]) -> Tuple[float, str]:
    """
    Retorna versión simplificada de calificación.
    (Mantiene compatibilidad con versión anterior)
    
    Args:
        respuestas_usuario: Dict de respuestas
    
    Returns:
        Tuple (porcentaje, mensaje)
    """
    resultado = calificar_simulacro_detallado(respuestas_usuario)
    return resultado['porcentaje'], resultado['mensaje']


# ============ PDF EXPORT (REPORTLAB) ============

def generar_pdf_auditoria(respuestas: Dict[int, bool], preguntas: List[Dict],
                          empresa_nombre: str = "Empresa", 
                          archivo_salida: str = None) -> Optional[bytes]:
    """
    Genera PDF profesional del reporte de auditoría.
    
    Args:
        respuestas: Dict de respuestas usuario
        preguntas: Lista de preguntas
        empresa_nombre: Nombre de empresa
        archivo_salida: Ruta destino (si None, retorna bytes)
    
    Returns:
        Bytes del PDF o None
    """
    try:
        from reportlab.lib.pagesizes import A4, letter
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle, Paragraph,
                                       Spacer, PageBreak, KeepTogether)
        from reportlab.lib.units import inch
        
        from io import BytesIO
        
        # Preparar datos
        calificacion = calificar_simulacro_detallado(respuestas)
        buffer = BytesIO() if not archivo_salida else None
        
        # Crear PDF
        filename = archivo_salida or buffer
        doc = SimpleDocTemplate(filename, pagesize=letter,
                              rightMargin=0.75*inch, leftMargin=0.75*inch,
                              topMargin=0.75*inch, bottomMargin=0.75*inch)
        
        # Estilos
        styles = getSampleStyleSheet()
        style_titulo = ParagraphStyle('CustomTitle',
                                     parent=styles['Heading1'],
                                     fontSize=16,
                                     textColor=colors.HexColor('#1F4788'),
                                     spaceAfter=10,
                                     alignment=1)  # Center
        
        style_heading = ParagraphStyle('CustomHeading',
                                      parent=styles['Heading2'],
                                      fontSize=12,
                                      textColor=colors.HexColor('#2E5C8A'),
                                      spaceAfter=6,
                                      spaceBefore=12)
        
        # Contenido
        elementos = []
        
        # Título
        elementos.append(Paragraph("📋 REPORTE DE SIMULACRO DE AUDITORÍA MINISTERIAL", 
                                   style_titulo))
        elementos.append(Spacer(1, 0.15*inch))
        
        # Info empresa
        info_empresa = f"Empresa: <b>{empresa_nombre}</b> | Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        elementos.append(Paragraph(info_empresa, styles['Normal']))
        elementos.append(Spacer(1, 0.2*inch))
        
        # Resumen ejecutivo
        elementos.append(Paragraph("RESUMEN EJECUTIVO", style_heading))
        
        resumen_data = [
            ['Métrica', 'Resultado'],
            ['Total Preguntas', str(calificacion['total'])],
            ['Respuestas Correctas', str(calificacion['correctas'])],
            ['Respuestas Incorrectas', str(calificacion['incorrectas'])],
            ['Porcentaje Cumplimiento', f"{calificacion['porcentaje']}%"],
            ['Nivel de Riesgo', calificacion['nivel_riesgo']],
        ]
        
        # Color según nivel de riesgo
        color_fondo = colors.HexColor('#FFE5E5')  # Rojo suave
        if 'CUMPLE' in calificacion['nivel_riesgo']:
            color_fondo = colors.HexColor('#E5FFE5')  # Verde suave
        elif 'PARCIAL' in calificacion['nivel_riesgo']:
            color_fondo = colors.HexColor('#FFFFE5')  # Amarillo suave
        
        tabla_resumen = Table(resumen_data, colWidths=[2.5*inch, 2.5*inch])
        tabla_resumen.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1F4788')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), color_fondo),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        elementos.append(tabla_resumen)
        elementos.append(Spacer(1, 0.2*inch))
        
        # Veredicto
        color_veredicto = colors.HexColor('#2E5C8A')
        if 'CRÍTICO' in calificacion['nivel_riesgo']:
            color_veredicto = colors.HexColor('#CC0000')
        elif 'CUMPLE' in calificacion['nivel_riesgo']:
            color_veredicto = colors.HexColor('#007700')
        
        style_veredicto = ParagraphStyle('Veredicto',
                                        parent=styles['Normal'],
                                        fontSize=11,
                                        textColor=color_veredicto,
                                        alignment=1)
        
        elementos.append(Paragraph(f"<b>VEREDICTO: {calificacion['mensaje']}</b>", 
                                   style_veredicto))
        elementos.append(Spacer(1, 0.3*inch))
        
        # Detalle por categoría
        elementos.append(Paragraph("DETALLE POR CATEGORÍA", style_heading))
        
        preguntas_por_categoria = {}
        for idx, pregunta in enumerate(preguntas):
            cat = pregunta.get('categoria', 'Otros')
            if cat not in preguntas_por_categoria:
                preguntas_por_categoria[cat] = {'cumple': 0, 'total': 0, 'preguntas': []}
            
            es_correcto = respuestas.get(idx, False)
            if es_correcto:
                preguntas_por_categoria[cat]['cumple'] += 1
            preguntas_por_categoria[cat]['total'] += 1
            
            resultado_str = "✅ CUMPLE" if es_correcto else "❌ NO CUMPLE"
            preguntas_por_categoria[cat]['preguntas'].append({
                'texto': pregunta['texto'][:100] + '...',
                'resultado': resultado_str
            })
        
        # Tabla de categorías
        tabla_categorias = [['Categoría', 'Cumple', 'Total', 'Porcentaje']]
        for cat in sorted(preguntas_por_categoria.keys()):
            cumple = preguntas_por_categoria[cat]['cumple']
            total = preguntas_por_categoria[cat]['total']
            pct = (cumple / total * 100) if total > 0 else 0
            tabla_categorias.append([cat, str(cumple), str(total), f"{pct:.0f}%"])
        
        tabla_cat = Table(tabla_categorias)
        tabla_cat.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2E5C8A')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey)
        ]))
        
        elementos.append(tabla_cat)
        elementos.append(Spacer(1, 0.3*inch))
        
        # Recomendaciones
        elementos.append(Paragraph("RECOMENDACIONES", style_heading))
        
        recomendaciones_texto = ""
        if 'CRÍTICO' in calificacion['nivel_riesgo']:
            recomendaciones_texto = "🔴 ACCIÓN URGENTE: Contactar especialista HSE inmediatamente. Suspender operaciones si es necesario."
        elif 'DEFICIENTE' in calificacion['nivel_riesgo']:
            recomendaciones_texto = "🚨 ACCIÓN REQUERIDA: Implementar correcciones en 1 semana. Capacitación obligatoria."
        elif 'REGULAR' in calificacion['nivel_riesgo']:
            recomendaciones_texto = "⚠️ MEJORA NECESARIA: Resolver brechas en 2-4 semanas. Auditoría de seguimiento requerida."
        else:
            recomendaciones_texto = "✅ MANTENIMIENTO: Sistema bajo control. Continuar auditorías periódicas."
        
        elementos.append(Paragraph(recomendaciones_texto, styles['Normal']))
        elementos.append(Spacer(1, 0.2*inch))
        
        # Pie de página
        pie = f"Reporte generado automáticamente por CGT - {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        elementos.append(Paragraph(f"<i>{pie}</i>", styles['Normal']))
        
        # Construir PDF
        doc.build(elementos)
        
        if archivo_salida:
            logger.info(f"PDF guardado: {archivo_salida}")
            return True
        else:
            pdf_bytes = buffer.getvalue()
            buffer.close()
            logger.info(f"PDF generado en memoria ({len(pdf_bytes)} bytes)")
            return pdf_bytes
    
    except ImportError:
        logger.warning("reportlab no disponible, instalando...")
        return None
    except Exception as e:
        logger.error(f"Error generando PDF: {e}")
        return None


def guardar_pdf_auditoria(respuestas: Dict[int, bool], preguntas: List[Dict],
                         empresa_id: int, empresa_nombre: str,
                         db_path: str, archivo_salida: str = None) -> str:
    """
    Guarda reporte de auditoría como PDF y registra en BD.
    
    Args:
        respuestas: Dict de respuestas
        preguntas: Lista de preguntas
        empresa_id: ID de empresa
        empresa_nombre: Nombre de empresa
        db_path: Ruta a BD
        archivo_salida: Ruta del PDF (auto-generada si vacío)
    
    Returns:
        Ruta del archivo guardado
    """
    # Generar nombre de archivo
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if not archivo_salida:
        archivo_salida = f"reporte_auditoria_{empresa_id}_{timestamp}.pdf"
    
    # Generar PDF
    resultado_pdf = generar_pdf_auditoria(respuestas, preguntas, empresa_nombre, archivo_salida)
    
    if resultado_pdf:
        # Registrar en BD
        calificacion = calificar_simulacro_detallado(respuestas)
        query = f"""
        INSERT INTO simulacros_auditoria
        (empresa_id, fecha_simulacro, respuestas_json, porcentaje_cumplimiento, 
         nivel_riesgo, archivo_pdf)
        VALUES ({empresa_id}, '{datetime.now().isoformat()}', '{json.dumps(respuestas)}',
                {calificacion['porcentaje']}, '{calificacion['nivel_riesgo']}', '{archivo_salida}')
        """
        
        try:
            ejecutar_query(db_path, query)
            logger.info(f"PDF registrado en BD: {archivo_salida}")
        except Exception as e:
            logger.warning(f"PDF guardado pero no registrado en BD: {e}")
        
        return archivo_salida
    
    return None
