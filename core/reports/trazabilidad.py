import os

from fpdf import FPDF

from .base import texto_seguro


def generar_pdf_trazabilidad(datos, participantes, logo_cgt, logo_cliente=None):
    class ReporteTrazabilidad(FPDF):
        def header(self):
            # LOGO SUPERIOR IZQUIERDA
            if os.path.exists(logo_cgt):
                self.image(logo_cgt, 10, 8, 30)

            # TÍTULO
            self.set_xy(45, 12)
            self.set_font("Helvetica", "B", 12)
            self.set_text_color(100, 100, 100)
            self.cell(0, 5, "CAPACITACION, COMUNICACION, INDUCCION Y/O DIFUSION", ln=True, align="C")
            self.set_font("Helvetica", "B", 10)
            self.set_x(45)
            self.cell(0, 5, "VELTS-SGI-QA-0011", ln=True, align="C")
            self.set_text_color(0, 0, 0)
            self.set_y(42)  # Forzar inicio debajo del logo (logo y=8, h=30 -> 38)

        def footer(self):
            self.set_y(-15)
            self.set_font("Helvetica", "I", 8)
            self.cell(0, 10, f'Página {self.page_no()}/{{nb}}', align="C")

    pdf = ReporteTrazabilidad("P", "mm", "A4")
    pdf.alias_nb_pages()
    pdf.add_page()

    # Colores
    pdf.set_draw_color(50, 50, 50)
    pdf.set_line_width(0.3)

    # 1. ENCABEZADO DE DATOS (FAENA, ADMIN, TEMA, FECHA)
    pdf.set_font("Helvetica", "B", 9)
    # Fila 1
    pdf.cell(70, 8, f" FAENA: {texto_seguro(datos.get('faena', ''))[:30]}", border=1)
    pdf.cell(80, 8, f" ADMINISTRADOR: {texto_seguro(datos.get('administrador', ''))[:35]}", border=1)
    pdf.cell(40, 8, f" FECHA: {texto_seguro(datos.get('fecha', ''))}", border=1, ln=True)
    # Fila 2
    pdf.cell(190, 8, f" TEMA: {texto_seguro(datos.get('tema', ''))[:100]}", border=1, ln=True)

    # 2. CAJA DE DESCRIPCIÓN (Dinámica)
    pdf.set_font("Helvetica", "", 9)
    desc_txt = texto_seguro(datos.get('descripcion', ''))

    # Borde superior
    pdf.cell(190, 3, "", border="LTR", ln=True)

    if desc_txt.strip():
        # multi_cell con bordes laterales maneja saltos de línea y de página automáticamente
        pdf.multi_cell(190, 5, desc_txt, border="LR")
        pdf.cell(190, 3, "", border="LR", ln=True) # Un poco de espacio extra
    else:
        # Si no hay texto, dejamos un recuadro en blanco razonable
        pdf.cell(190, 30, "", border="LR", ln=True)

    # Borde inferior
    pdf.cell(190, 2, "", border="LBR", ln=True)

    # 3. RELATOR Y FIRMA
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(130, 8, f" RELATOR: {texto_seguro(datos.get('relator', ''))}", border=1)
    pdf.cell(60, 8, " FIRMA:", border=1, ln=True)

    # 4. HORARIOS
    pdf.cell(65, 8, f" HORA INICIO: {texto_seguro(datos.get('hora_inicio', ''))}", border=1)
    pdf.cell(65, 8, f" HORA TERMINO: {texto_seguro(datos.get('hora_termino', ''))}", border=1)
    pdf.cell(60, 8, f" HH TOTALES: {texto_seguro(str(datos.get('hh_totales', '')))}", border=1, ln=True)

    # 5. DOCUMENTOS O MATERIAL ANEXOS
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(190, 6, " DOCUMENTOS O MATERIAL ANEXOS", border=1, ln=True, fill=True)

    opciones = [
        ("AST", "REGLAMENTACIONES"),
        ("CHARLA", "VIDEO"),
        ("INSTRUCTIVO", "PRESENTACIÓN"),
        ("PROCEDIMIENTO", "OTRO:")
    ]

    tipo_sel = datos.get("tipo_documento", "OTRO").upper()

    for row in opciones:
        pdf.set_font("Helvetica", "", 8)
        # Columna 1
        pdf.cell(35, 6, f" {row[0]}", border=1)
        val_1 = " X " if tipo_sel == row[0] or (row[0]=="OTRO:" and tipo_sel not in ["AST", "CHARLA", "INSTRUCTIVO", "PROCEDIMIENTO", "REGLAMENTACIONES", "VIDEO", "PRESENTACIÓN"]) else ""
        pdf.cell(60, 6, val_1, border=1, align="C")

        # Columna 2
        pdf.cell(35, 6, f" {row[1]}", border=1)
        val_2 = " X " if tipo_sel == row[1] else ""
        pdf.cell(60, 6, val_2, border=1, align="C", ln=True)

    pdf.ln(2)

    # 6. TABLA DE PARTICIPANTES
    # Encabezados
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_fill_color(220, 220, 220)
    w_num = 10
    w_nom = 65
    w_car = 55
    w_rut = 25
    w_fir = 35

    pdf.cell(w_num, 8, "", border=1, fill=True)
    pdf.cell(w_nom, 8, " NOMBRE Y APELLIDO", border=1, align="C", fill=True)
    pdf.cell(w_car, 8, " CARGO", border=1, align="C", fill=True)
    pdf.cell(w_rut, 8, " RUT", border=1, align="C", fill=True)
    pdf.cell(w_fir, 8, " FIRMA", border=1, align="C", fill=True, ln=True)

    pdf.set_font("Helvetica", "", 8)

    # Llenar participantes (mínimo 10 filas, o la cantidad que venga)
    min_filas = max(10, len(participantes))

    for i in range(min_filas):
        if pdf.get_y() > 270:
            pdf.add_page()
            # Reimprimir headers
            pdf.set_font("Helvetica", "B", 8)
            pdf.cell(w_num, 8, "", border=1, fill=True)
            pdf.cell(w_nom, 8, " NOMBRE Y APELLIDO", border=1, align="C", fill=True)
            pdf.cell(w_car, 8, " CARGO", border=1, align="C", fill=True)
            pdf.cell(w_rut, 8, " RUT", border=1, align="C", fill=True)
            pdf.cell(w_fir, 8, " FIRMA", border=1, align="C", fill=True, ln=True)
            pdf.set_font("Helvetica", "", 8)

        nombre = ""
        cargo = ""
        rut = ""
        if i < len(participantes):
            p = participantes[i]
            nombre = texto_seguro(p.get("nombre", ""))[:35]  # Cortar si es muy largo
            cargo = texto_seguro(p.get("cargo", ""))[:30]
            rut = texto_seguro(p.get("rut", ""))

        pdf.cell(w_num, 8, str(i + 1), border=1, align="C")
        pdf.cell(w_nom, 8, f" {nombre}", border=1)
        pdf.cell(w_car, 8, f" {cargo}", border=1)
        pdf.cell(w_rut, 8, f" {rut}", border=1, align="C")
        pdf.cell(w_fir, 8, "", border=1, ln=True) # Firma vacía para llenar a mano

    return bytes(pdf.output())
