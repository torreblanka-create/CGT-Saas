import io
import os
from datetime import datetime

import pandas as pd
import qrcode
from fpdf import FPDF


def texto_seguro(texto):
    """Limpia emojis y caracteres no compatibles con FPDF (Helvetica)."""
    texto_limpio = str(texto).replace('🚫', '').replace('🔴', '').replace('🟢', '').replace('🟡', '').strip()
    return texto_limpio.encode('latin-1', 'ignore').decode('latin-1')

def truncar(texto, limite):
    """Acorta el texto para que no rompa las celdas de la tabla."""
    texto_str = texto_seguro(texto)
    return texto_str[:limite] + "..." if len(texto_str) > limite else texto_str

def generar_qr(texto_datos):
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(texto_datos)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

def generar_excel_gerencial(df_resumen, df_detalle):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_resumen.to_excel(writer, index=False, sheet_name='Semáforo Global')
        df_detalle.to_excel(writer, index=False, sheet_name='Base de Datos Completa')
        for i, col in enumerate(df_resumen.columns): writer.sheets['Semáforo Global'].set_column(i, i, 20)
        for i, col in enumerate(df_detalle.columns): writer.sheets['Base de Datos Completa'].set_column(i, i, 22)
    return output.getvalue()

def obtener_columnas_seguras(df):
    cols = df.columns
    col_nom = next((c for c in cols if 'nombre' in str(c).lower() or 'descripcion' in str(c).lower()), cols[0])
    posibles_id = [c for c in cols if any(x in str(c).lower() for x in ['rut', 'patente', 'serie', 'id', 'interno'])]
    col_id = posibles_id[0] if posibles_id else (cols[1] if len(cols)>1 else cols[0])
    if col_id == col_nom and len(cols) > 1: col_id = cols[0] if col_nom == cols[1] else cols[1]
    posibles_det = [c for c in cols if any(x in str(c).lower() for x in ['cargo', 'detalle', 'tipo', 'marca', 'modelo'])]
    col_det = posibles_det[0] if posibles_det else (cols[2] if len(cols)>2 else cols[0])
    return col_id, col_nom, col_det

class ReporteCGT(FPDF):
    def __init__(self, titulo, logo_cgt, logo_cliente, orientation='P', sub_titulo=None):
        super().__init__(orientation=orientation)
        self.titulo = titulo
        self.logo_cgt = logo_cgt
        self.logo_cliente = logo_cliente
        self.sub_titulo = sub_titulo

    def header(self):
        ancho_pagina = self.w

        # 1. Logos (Posicionados de forma absoluta)
        # Altura fija de 20mm para los logos para que no ocupen toda la cabecera
        if self.logo_cgt and os.path.exists(self.logo_cgt):
            self.image(self.logo_cgt, 10, 8, h=20)

        if self.logo_cliente and self.logo_cliente != self.logo_cgt and os.path.exists(self.logo_cliente):
            self.image(self.logo_cliente, ancho_pagina - 35, 8, w=25, h=15, keep_aspect_ratio=True)

        # 2. Títulos con Restricción de Área
        self.set_y(10)

        # Reducimos el ancho útil para el texto calculándolo (dejamos 35mm a cada lado)
        w_texto = ancho_pagina - 70

        self.set_font("Helvetica", "B", 14)
        self.set_x(35)
        self.multi_cell(w_texto, 7, texto_seguro(self.titulo), align="C")

        if self.sub_titulo:
            self.set_font("Helvetica", "I", 10)
            self.set_x(35)
            self.multi_cell(w_texto, 5, texto_seguro(self.sub_titulo), align="C")

        self.set_font("Helvetica", "", 9)
        self.set_x(35)
        self.cell(w_texto, 5, "CGT - Control de Gestión Total", align="C", ln=True)
        self.set_text_color(100, 100, 100)
        self.set_x(35)
        self.cell(w_texto, 4, f"Fecha de Emisión: {datetime.now().strftime('%d/%m/%Y %H:%M')}", align="C", ln=True)

        self.ln(2)
        self.set_draw_color(25, 58, 138)
        self.set_line_width(0.5)
        self.line(10, self.get_y(), ancho_pagina - 10, self.get_y())
        self.ln(8)
        self.set_text_color(0, 0, 0)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f"Generado por Plataforma CGT  |  Página {self.page_no()}/{{nb}}", align="C")
