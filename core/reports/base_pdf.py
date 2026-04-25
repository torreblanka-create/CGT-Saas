import os
from datetime import datetime

from fpdf import FPDF

from src.infrastructure.database import obtener_dataframe


def texto_seguro(texto):
    """Limpia emojis y caracteres no compatibles con FPDF (Helvetica)."""
    if texto is None: return ""
    texto_limpio = str(texto).replace('🚫', '').replace('🔴', '').replace('🟢', '').replace('🟡', '').strip()
    return texto_limpio.encode('latin-1', 'ignore').decode('latin-1')

def truncar(texto, limite):
    """Acorta el texto para que no rompa las celdas de la tabla."""
    texto_str = texto_seguro(texto)
    return texto_str[:limite] + "..." if len(texto_str) > limite else texto_str

class ReporteBase(FPDF):
    """
    Clase base modular para todos los nuevos reportes PDF del sistema CGT.
    Maneja la estructura común (Header, Footer) y provee métodos utilitarios
    para dibujar tablas, firmas y consultar la base de datos relacional.
    """
    def __init__(self, titulo, logo_app, logo_cliente, db_path, orientation='P'):
        super().__init__(orientation=orientation)
        self.titulo = titulo
        self.logo_app = logo_app
        self.logo_cliente = logo_cliente
        self.db_path = db_path

    def header(self):
        ancho_pagina = self.w

        # Logos
        if os.path.exists(self.logo_app):
            self.image(self.logo_app, 10, 8, h=20)
        if os.path.exists(self.logo_cliente) and self.logo_cliente != self.logo_app:
            self.image(self.logo_cliente, ancho_pagina - 38, 8, h=20)

        # Título
        old_m_l = self.l_margin
        old_m_r = self.r_margin
        self.set_left_margin(35)
        self.set_right_margin(35)
        self.set_y(10)

        self.set_font("Helvetica", "B", 14)
        self.multi_cell(0, 7, texto_seguro(self.titulo), align="C")

        self.set_font("Helvetica", "", 9)
        self.cell(0, 5, "CGT - Control de Gestión Total", align="C", ln=True)
        self.set_text_color(100, 100, 100)
        self.cell(0, 4, f"Fecha de Emisión: {datetime.now().strftime('%d/%m/%Y %H:%M')}", align="C", ln=True)

        self.set_left_margin(old_m_l)
        self.set_right_margin(old_m_r)

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

    # --- Métodos Utilitarios Compartidos ---

    def obtener_entidad_maestro(self, identificador, empresa_id, contrato_id):
        """Busca un registro (Personal, Equipo, etc) en maestro_entidades usando la relación corporativa."""
        query = "SELECT * FROM maestro_entidades WHERE identificador = ? AND empresa_id = ? AND contrato_id = ?"
        df = obtener_dataframe(self.db_path, query, (identificador, empresa_id, contrato_id))
        if not df.empty:
            return df.iloc[0].to_dict()
        return None

    def dibujar_seccion_firmas(self, etiquetas_firmantes):
        """
        Dibuja una cuadrícula de firmas al final del documento.
        `etiquetas_firmantes` es una lista de strings. Ej: ['Elaborado por', 'Revisado por'].
        """
        if self.get_y() > 220:
            self.add_page()

        self.ln(10)
        self.set_font("Helvetica", "B", 9)

        num_firmas = len(etiquetas_firmantes)
        if num_firmas == 0: return
        w_f = 190 / num_firmas

        # Cabecera de firmas
        for label in etiquetas_firmantes:
            self.cell(w_f, 8, label, 1, 0, 'C')
        self.ln()

        # Espacio para firma (3 filas de alto)
        for _ in range(3):
            for _ in range(num_firmas):
                self.cell(w_f, 10, "", 1, 0)
            self.ln()

        # Fecha
        for _ in range(num_firmas):
            self.cell(w_f, 8, "Fecha / Hora:", 1, 0, 'L')
        self.ln()
