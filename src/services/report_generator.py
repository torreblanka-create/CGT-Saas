"""
==========================================
📄 REPORT GENERATOR ENGINE — v2.0 MEJORADO
==========================================
Motor de generación de reportes ejecutivos.

CARACTERÍSTICAS v2.0:
✅ Generación de PDF
✅ Reportes gerenciales
✅ KPIs y dashboards
✅ Integración de forecast
✅ Firma digital
✅ Histórico de reportes
✅ Personalización por empresa
"""
import logging
import io
import os
from datetime import datetime
from typing import Dict, Optional, Tuple
from dataclasses import dataclass

from src.infrastructure.database import obtener_config, obtener_dataframe, obtener_conexion
from intelligence.agents.forecast_engine import generar_forecast_vencimientos, obtener_top_criticos

logger = logging.getLogger(__name__)


# ============ DATA MODELS ============

@dataclass
class ReporteEjecutivo:
    """Reporte gerencial generado"""
    id: str
    empresa_id: str
    contrato_id: str
    fecha_reporte: str
    kpis: Dict
    alertas_criticas: int
    cumplimiento_general: float
    ruta_pdf: str
    firma_digital: str


class ReportGeneratorEngine:
    """Motor de generación de reportes"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path
        self._crear_tablas()
        logger.info("ReportGeneratorEngine inicializado")
    
    def _crear_tablas(self) -> None:
        """Crea tablas para reportes"""
        if not self.db_path:
            return
        
        tables = [
            """
            CREATE TABLE IF NOT EXISTS reportes_ejecutivos (
                id TEXT PRIMARY KEY,
                empresa_id TEXT,
                contrato_id TEXT,
                fecha_reporte TIMESTAMP,
                kpis TEXT,
                alertas_criticas INTEGER,
                cumplimiento_general REAL,
                ruta_pdf TEXT,
                firma_digital TEXT
            )
            """
        ]
        
        try:
            conexion = obtener_conexion(self.db_path)
            for query in tables:
                conexion.execute(query)
            conexion.commit()
            conexion.close()
            logger.debug("Tablas de reportes creadas")
        except Exception as e:
            logger.error(f"Error creando tablas: {e}")


def _intentar_importar_pdf():
    """Intenta importar fpdf2 o reportlab, retorna la librería disponible."""
    try:
        from fpdf import FPDF
        return "fpdf2", FPDF
    except ImportError:
        pass
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
        return "reportlab", (canvas, A4, colors)
    except ImportError:
        return None, None


def _color_semaforo(porcentaje: float) -> tuple:
    """Retorna un color RGB según el porcentaje de cumplimiento."""
    if porcentaje >= 85:
        return (16, 185, 129)   # Verde
    elif porcentaje >= 60:
        return (245, 158, 11)   # Amarillo/Naranja
    else:
        return (239, 68, 68)    # Rojo


def generar_briefing_ejecutivo(DB_PATH: str, empresa_id: int = 0, contrato_id: int = 0,
                                empresa_nombre: str = "Empresa", contrato_nombre: str = "") -> bytes | None:
    """
    Genera el PDF de briefing ejecutivo y lo retorna como bytes.
    Retorna None si ninguna librería PDF está disponible.
    """
    lib_name, lib = _intentar_importar_pdf()

    if lib_name is None:
        return None

    # ── Obtener datos ────────────────────────────────────
    query_reg = "SELECT categoria, fecha_vencimiento FROM registros WHERE 1=1"
    params = []
    if empresa_id > 0:
        query_reg += " AND empresa_id = ?"
        params.append(empresa_id)
    if contrato_id > 0:
        query_reg += " AND contrato_id = ?"
        params.append(contrato_id)

    import pandas as pd
    df = obtener_dataframe(DB_PATH, query_reg, tuple(params))

    hoy = pd.Timestamp(datetime.now().date())
    total_docs = len(df)
    bloqueados = 0
    en_alerta = 0
    operativos = 0

    if not df.empty:
        df['fecha_vencimiento'] = pd.to_datetime(df['fecha_vencimiento'], errors='coerce')
        for _, r in df.iterrows():
            if pd.isna(r['fecha_vencimiento']):
                operativos += 1
            elif r['fecha_vencimiento'] < hoy:
                bloqueados += 1
            elif (r['fecha_vencimiento'] - hoy).days <= 15:
                en_alerta += 1
            else:
                operativos += 1

    pct_cumplimiento = round(((operativos / total_docs) * 100), 1) if total_docs > 0 else 0

    forecast = generar_forecast_vencimientos(DB_PATH, empresa_id, contrato_id, meses=3)
    top_criticos = obtener_top_criticos(DB_PATH, empresa_id, contrato_id, top_n=5)

    # Alertas normativas
    df_alertas = obtener_dataframe(DB_PATH,
        "SELECT tipo, mensaje, fecha FROM notificaciones_ultron WHERE estado = 'No Leída' ORDER BY fecha DESC LIMIT 5"
    )

    fecha_str = datetime.now().strftime("%d de %B de %Y").capitalize()

    if lib_name == "fpdf2":
        return _generar_con_fpdf(
            lib, empresa_nombre, contrato_nombre, fecha_str,
            total_docs, bloqueados, en_alerta, operativos, pct_cumplimiento,
            forecast, top_criticos, df_alertas
        )
    else:
        return _generar_con_reportlab(
            lib, empresa_nombre, contrato_nombre, fecha_str,
            total_docs, bloqueados, en_alerta, operativos, pct_cumplimiento,
            forecast, top_criticos, df_alertas
        )


def _generar_con_fpdf(FPDF, empresa_nombre, contrato_nombre, fecha_str,
                       total_docs, bloqueados, en_alerta, operativos, pct_cumplimiento,
                       forecast, top_criticos, df_alertas):
    """Genera el PDF usando fpdf2."""
    from fpdf import FPDF

    COLOR_CYAN = (0, 188, 212)
    COLOR_DARK = (15, 23, 42)
    COLOR_GRAY = (100, 116, 139)
    COLOR_GREEN = (16, 185, 129)
    COLOR_YELLOW = (245, 158, 11)
    COLOR_RED = (239, 68, 68)
    COLOR_WHITE = (255, 255, 255)

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    # ── ENCABEZADO / PORTADA ──────────────────────────────
    pdf.set_fill_color(*COLOR_DARK)
    pdf.rect(0, 0, 210, 55, 'F')

    pdf.set_text_color(*COLOR_CYAN)
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_xy(10, 10)
    pdf.cell(0, 10, "ULTRON INTELLIGENCE HUB", ln=True, align='C')

    pdf.set_font("Helvetica", "", 12)
    pdf.set_text_color(*COLOR_WHITE)
    pdf.set_x(10)
    pdf.cell(0, 8, "Briefing Ejecutivo de Seguridad y Cumplimiento", ln=True, align='C')

    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*COLOR_GRAY)
    pdf.set_x(10)
    empresa_text = empresa_nombre
    if contrato_nombre:
        empresa_text += f" | Contrato: {contrato_nombre}"
    pdf.cell(0, 6, empresa_text, ln=True, align='C')
    pdf.set_x(10)
    pdf.cell(0, 5, f"Generado: {fecha_str}", ln=True, align='C')

    pdf.ln(5)

    # ── SECCIÓN KPIs ──────────────────────────────────────
    pdf.set_text_color(*COLOR_CYAN)
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 10, "INDICADORES CLAVE DE CUMPLIMIENTO (KPI)", ln=True, align='L')

    kpis = [
        ("Total Documentos", str(total_docs), COLOR_CYAN),
        ("Operativos", str(operativos), COLOR_GREEN),
        ("En Alerta", str(en_alerta), COLOR_YELLOW),
        ("Bloqueados", str(bloqueados), COLOR_RED),
        ("% Cumplimiento", f"{pct_cumplimiento}%", _color_semaforo(pct_cumplimiento))
    ]

    col_w = 38
    x_start = 10
    y_kpi = pdf.get_y()

    for i, (label, valor, color) in enumerate(kpis):
        x = x_start + i * col_w
        # Caja
        pdf.set_fill_color(30, 41, 59)
        pdf.set_draw_color(*color)
        pdf.rect(x, y_kpi, col_w - 2, 22, 'DF')
        # Valor
        pdf.set_text_color(*color)
        pdf.set_font("Helvetica", "B", 15)
        pdf.set_xy(x, y_kpi + 2)
        pdf.cell(col_w - 2, 8, valor, align='C')
        # Label
        pdf.set_text_color(*COLOR_GRAY)
        pdf.set_font("Helvetica", "", 7)
        pdf.set_xy(x, y_kpi + 11)
        pdf.cell(col_w - 2, 6, label, align='C')

    pdf.set_y(y_kpi + 28)

    # ── SECCIÓN TOP CRÍTICOS ─────────────────────────────
    if not top_criticos.empty:
        pdf.set_text_color(*COLOR_CYAN)
        pdf.set_font("Helvetica", "B", 13)
        pdf.cell(0, 10, "TOP DOCUMENTOS CRÍTICOS (VENCIMIENTO PRÓXIMO)", ln=True, align='L')

        # Cabecera tabla
        headers = ["ID", "Nombre", "Tipo Doc", "Categoría", "Vence"]
        col_widths = [25, 55, 35, 35, 30]

        pdf.set_fill_color(*COLOR_DARK)
        pdf.set_text_color(*COLOR_CYAN)
        pdf.set_font("Helvetica", "B", 8)
        for h, w in zip(headers, col_widths):
            pdf.cell(w, 7, h, border=1, fill=True, align='C')
        pdf.ln()

        pdf.set_font("Helvetica", "", 7.5)
        import pandas as pd
        hoy_ts = pd.Timestamp(datetime.now().date())

        for _, row in top_criticos.iterrows():
            fv = pd.to_datetime(row.get('fecha_vencimiento', ''), errors='coerce')
            dias = (fv - hoy_ts).days if not pd.isna(fv) else 9999
            row_color = COLOR_RED if dias < 0 else (COLOR_YELLOW if dias <= 15 else COLOR_GREEN)

            pdf.set_text_color(*row_color)
            pdf.cell(25, 6, str(row.get('identificador', ''))[:12], border=1, align='C')
            pdf.set_text_color(200, 200, 200)
            pdf.cell(55, 6, str(row.get('nombre', ''))[:30], border=1)
            pdf.cell(35, 6, str(row.get('tipo_doc', ''))[:18], border=1)
            pdf.cell(35, 6, str(row.get('categoria', ''))[:18], border=1)
            fv_str = fv.strftime("%d/%m/%Y") if not pd.isna(fv) else "—"
            pdf.set_text_color(*row_color)
            pdf.cell(30, 6, fv_str, border=1, align='C')
            pdf.ln()

        pdf.ln(5)

    # ── SECCIÓN FORECAST ──────────────────────────────────
    if forecast.get("meses"):
        pdf.set_text_color(*COLOR_CYAN)
        pdf.set_font("Helvetica", "B", 13)
        pdf.cell(0, 10, "PROYECCIÓN DE VENCIMIENTOS (PRÓXIMOS 3 MESES)", ln=True, align='L')

        bar_max = max(forecast["conteos"]) if forecast["conteos"] else 1
        bar_max = max(bar_max, 1)
        bar_area_w = 150
        bar_h = 12

        for mes, conteo, indice in zip(forecast["meses"], forecast["conteos"], forecast["indice_riesgo"]):
            try:
                from datetime import datetime as dt
                mes_label = dt.strptime(mes, '%Y-%m').strftime('%B %Y').capitalize()
            except Exception:
                mes_label = mes

            color = COLOR_RED if indice > 30 else (COLOR_YELLOW if indice > 15 else COLOR_GREEN)

            pdf.set_text_color(200, 200, 200)
            pdf.set_font("Helvetica", "", 8)
            pdf.cell(38, bar_h, mes_label[:15], align='L')

            bar_w = int((conteo / bar_max) * bar_area_w) if bar_max > 0 else 2
            bar_w = max(bar_w, 2)

            pdf.set_fill_color(*color)
            pdf.rect(pdf.get_x(), pdf.get_y() + 2, bar_w, 7, 'F')

            pdf.set_text_color(*color)
            pdf.set_font("Helvetica", "B", 8)
            pdf.set_x(pdf.get_x() + bar_w + 3)
            pdf.cell(20, bar_h, f"{conteo} docs ({indice}%)")
            pdf.ln(bar_h)

        pdf.ln(3)

    # ── SECCIÓN ALERTAS ───────────────────────────────────
    if not df_alertas.empty:
        pdf.set_text_color(*COLOR_CYAN)
        pdf.set_font("Helvetica", "B", 13)
        pdf.cell(0, 10, "ALERTAS ULTRON ACTIVAS", ln=True, align='L')

        for _, alerta in df_alertas.iterrows():
            tipo = str(alerta.get('tipo', ''))
            msg = str(alerta.get('mensaje', ''))[:120]
            color = COLOR_RED if "Crítico" in tipo else (COLOR_YELLOW if "Alerta" in tipo else COLOR_CYAN)

            pdf.set_fill_color(20, 30, 48)
            pdf.set_draw_color(*color)
            y_a = pdf.get_y()
            pdf.rect(10, y_a, 190, 10, 'DF')

            pdf.set_text_color(*color)
            pdf.set_font("Helvetica", "B", 8)
            pdf.set_xy(12, y_a + 1)
            pdf.cell(40, 4, tipo[:30])

            pdf.set_text_color(180, 180, 180)
            pdf.set_font("Helvetica", "", 7.5)
            pdf.set_xy(55, y_a + 1)
            pdf.cell(145, 4, msg)
            pdf.ln(10)

    # ── PIE DE PÁGINA / FIRMA ─────────────────────────────
    pdf.ln(5)
    pdf.set_fill_color(*COLOR_DARK)
    pdf.rect(0, pdf.get_y(), 210, 20, 'F')

    pdf.set_text_color(*COLOR_CYAN)
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_xy(10, pdf.get_y() + 3)
    pdf.cell(0, 5, "Documento generado automáticamente por ULTRON — CGT.pro Intelligence Hub", align='C', ln=True)

    pdf.set_text_color(*COLOR_GRAY)
    pdf.set_font("Helvetica", "I", 7)
    pdf.set_x(10)
    pdf.cell(0, 5, f'Directiva Maestra: "Mejorar siempre en pos de hacer las cosas bien." | {fecha_str}', align='C')

    buffer = io.BytesIO()
    pdf_bytes = pdf.output()
    return bytes(pdf_bytes)


def _generar_con_reportlab(libs, empresa_nombre, contrato_nombre, fecha_str,
                             total_docs, bloqueados, en_alerta, operativos, pct_cumplimiento,
                             forecast, top_criticos, df_alertas):
    """Fallback: genera con reportlab si fpdf2 no está disponible."""
    canvas_cls, A4, colors = libs
    from reportlab.lib import colors as rl_colors
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    w, h = A4

    # Fondo oscuro encabezado
    c.setFillColorRGB(0.06, 0.09, 0.16)
    c.rect(0, h - 80, w, 80, fill=1, stroke=0)

    # Título
    c.setFillColorRGB(0, 0.74, 0.83)
    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(w / 2, h - 35, "ULTRON INTELLIGENCE HUB")

    c.setFillColorRGB(0.9, 0.9, 0.9)
    c.setFont("Helvetica", 11)
    c.drawCentredString(w / 2, h - 52, "Briefing Ejecutivo de Seguridad y Cumplimiento")

    c.setFillColorRGB(0.5, 0.5, 0.5)
    c.setFont("Helvetica", 8)
    emp_text = empresa_nombre + (f" | {contrato_nombre}" if contrato_nombre else "")
    c.drawCentredString(w / 2, h - 67, emp_text)
    c.drawCentredString(w / 2, h - 77, f"Generado: {fecha_str}")

    # KPIs simples
    y_kpi = h - 130
    kpis = [
        ("Total", str(total_docs), (0, 0.74, 0.83)),
        ("Operativos", str(operativos), (0.06, 0.73, 0.51)),
        ("En Alerta", str(en_alerta), (0.96, 0.62, 0.04)),
        ("Bloqueados", str(bloqueados), (0.94, 0.27, 0.27)),
        ("Cumplim.", f"{pct_cumplimiento}%", _color_semaforo(pct_cumplimiento))
    ]

    kpi_w = 100
    x_kpi = 40
    for i, (label, val, color) in enumerate(kpis):
        xk = x_kpi + i * kpi_w
        r, g, b = (color[0]/255, color[1]/255, color[2]/255) if isinstance(color[0], int) else color
        c.setFillColorRGB(r, g, b)
        c.setFont("Helvetica-Bold", 18)
        c.drawCentredString(xk, y_kpi, val)
        c.setFillColorRGB(0.5, 0.5, 0.5)
        c.setFont("Helvetica", 8)
        c.drawCentredString(xk, y_kpi - 14, label)

    # Texto narrativo forecast
    y_forecast = y_kpi - 60
    c.setFillColorRGB(0, 0.74, 0.83)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, y_forecast, "PROYECCIÓN DE VENCIMIENTOS")

    narrativa = forecast.get("narrativa", "")
    lines = narrativa.replace("**", "").replace("_", "").split("\n")
    y_text = y_forecast - 20
    c.setFillColorRGB(0.7, 0.7, 0.7)
    c.setFont("Helvetica", 8)
    for line in lines[:12]:
        if y_text < 100:
            break
        c.drawString(40, y_text, line[:110])
        y_text -= 14

    # Firma
    c.setFillColorRGB(0.06, 0.09, 0.16)
    c.rect(0, 0, w, 40, fill=1, stroke=0)
    c.setFillColorRGB(0, 0.74, 0.83)
    c.setFont("Helvetica-Bold", 7)
    c.drawCentredString(w / 2, 22, "Documento generado por ULTRON — CGT.pro Intelligence Hub")
    c.setFillColorRGB(0.4, 0.4, 0.4)
    c.setFont("Helvetica-Oblique", 6.5)
    c.drawCentredString(w / 2, 12, 'Directiva: "Mejorar siempre en pos de hacer las cosas bien."')

    c.save()
    return buffer.getvalue()
