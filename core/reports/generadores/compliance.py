import json
import os
from datetime import datetime

from core.reports.base import ReporteCGT, texto_seguro, truncar


class GeneradorPdfCompliance:
    def __init__(self, audit_id, db_path, logo_app, logo_cliente):
        self.audit_id = audit_id
        self.db_path = db_path
        self.logo_app = logo_app
        self.logo_cliente = logo_cliente

    def obtener_datos(self):
        from src.infrastructure.database import obtener_dataframe
        query = """
            SELECT a.fecha, a.auditor, a.tipo, a.puntaje_final, a.clasificacion, a.datos_json,
                   e.nombre as empresa, c.nombre_contrato as contrato
            FROM compliance_audits a
            LEFT JOIN empresas e ON a.empresa_id = e.id
            LEFT JOIN contratos c ON a.contrato_id = c.id
            WHERE a.id = ?
        """
        df = obtener_dataframe(self.db_path, query, (self.audit_id,))
        if df.empty:
            return None
        return df.iloc[0].to_dict()

    def generar(self):
        datos = self.obtener_datos()
        if not datos:
            return None

        # Configuración del PDF
        pdf = ReporteCGT(
            titulo=f"INFORME DE CUMPLIMIENTO: {datos['tipo']}",
            logo_cgt=self.logo_app,
            logo_cliente=self.logo_cliente,
            sub_titulo=f"Empresa: {datos['empresa']} | Contrato: {datos['contrato']}"
        )
        pdf.alias_nb_pages()
        pdf.add_page()

        # 1. Resumen Ejecutivo
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 10, "1. RESUMEN EJECUTIVO", ln=True)
        pdf.set_font("Helvetica", "", 10)

        # Colores según clasificación
        pct = datos['puntaje_final']
        if pct >= 95: color = (16, 185, 129) # Green
        elif pct >= 80: color = (245, 158, 11) # Yellow
        else: color = (239, 68, 68) # Red

        pdf.set_fill_color(*color)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Helvetica", "B", 14)
        pdf.cell(0, 12, f" Resultado Global: {pct:.1f}% - {datos['clasificacion']}", border=0, ln=True, fill=True, align="C")
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Helvetica", "", 10)
        pdf.ln(5)

        # Información General
        h_c = 7
        pdf.cell(40, h_c, " Auditor:", border=1)
        pdf.cell(0, h_c, f" {datos['auditor']}", border=1, ln=True)
        pdf.cell(40, h_c, " Fecha:", border=1)
        pdf.cell(0, h_c, f" {datos['fecha']}", border=1, ln=True)
        pdf.ln(10)

        # 2. Detalle de Respuestas
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 10, "2. DETALLE DE EVALUACION POR ITEM", ln=True)
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_fill_color(230, 230, 230)

        w_item = 130
        w_eval = 60
        pdf.cell(w_item, 8, " Item / Pregunta Evaluada", border=1, fill=True)
        pdf.cell(w_eval, 8, " Resultado", border=1, fill=True, ln=True, align="C")

        pdf.set_font("Helvetica", "", 8)
        audit_json = json.loads(datos['datos_json'])
        respuestas = audit_json.get('respuestas', {})

        for item_id, resp in respuestas.items():
            # Intentar obtener el texto de la pregunta desde el ID (que incluye el nombre de la categoría)
            txt_q = item_id.replace("_", " - ")

            alto_fila = 8
            # Calcular si el texto es muy largo
            lineas = pdf.multi_cell(w_item, 4, texto_seguro(txt_q), split_only=True)
            alto_fila = max(len(lineas) * 4 + 2, 8)

            if pdf.get_y() + alto_fila > 260:
                pdf.add_page()

            x_ini = pdf.get_x()
            y_ini = pdf.get_y()

            pdf.rect(x_ini, y_ini, w_item, alto_fila)
            pdf.multi_cell(w_item, 4, texto_seguro(txt_q), border=0)

            pdf.set_xy(x_ini + w_item, y_ini)
            pdf.cell(w_eval, alto_fila, resp, border=1, align="C", ln=True)

        pdf.ln(10)

        # 3. Plan de Acción (Brechas)
        brechas = audit_json.get('brechas', {})
        if brechas:
            pdf.add_page()
            pdf.set_font("Helvetica", "B", 12)
            pdf.cell(0, 10, "3. PLAN DE ACCION (BRECHAS DETECTADAS)", ln=True)
            pdf.set_font("Helvetica", "I", 9)
            pdf.multi_cell(0, 5, "Los siguientes ítems fueron evaluados como 'No Cumple'. Se definen acciones correctivas para su regularización.")
            pdf.ln(3)

            pdf.set_font("Helvetica", "B", 8)
            pdf.set_fill_color(239, 68, 68) # Red for headers
            pdf.set_text_color(255, 255, 255)

            w_gap_q = 70
            w_gap_a = 60
            w_gap_r = 30
            w_gap_f = 30

            pdf.cell(w_gap_q, 8, " Hallazgo", border=1, fill=True)
            pdf.cell(w_gap_a, 8, " Acción Correctiva", border=1, fill=True)
            pdf.cell(w_gap_r, 8, " Responsable", border=1, fill=True)
            pdf.cell(w_gap_f, 8, " Plazo", border=1, fill=True, ln=True, align="C")

            pdf.set_text_color(0, 0, 0)
            pdf.set_font("Helvetica", "", 7)

            for k, b in brechas.items():
                txt_h = texto_seguro(k.replace("_", " - "))
                txt_a = texto_seguro(b['accion'])
                txt_r = texto_seguro(b['responsable'])
                txt_f = b['fecha_limite']

                # Calcular alto
                l_h = pdf.multi_cell(w_gap_q, 3.5, txt_h, split_only=True)
                l_a = pdf.multi_cell(w_gap_a, 3.5, txt_a, split_only=True)

                h_fila = max(len(l_h), len(l_a), 2) * 3.5 + 2

                if pdf.get_y() + h_fila > 270: pdf.add_page()

                curr_x = pdf.get_x()
                curr_y = pdf.get_y()

                pdf.rect(curr_x, curr_y, w_gap_q, h_fila)
                pdf.multi_cell(w_gap_q, 3.5, txt_h)

                pdf.set_xy(curr_x + w_gap_q, curr_y)
                pdf.rect(curr_x + w_gap_q, curr_y, w_gap_a, h_fila)
                pdf.multi_cell(w_gap_a, 3.5, txt_a)

                pdf.set_xy(curr_x + w_gap_q + w_gap_a, curr_y)
                pdf.cell(w_gap_r, h_fila, txt_r, border=1)
                pdf.cell(w_gap_f, h_fila, txt_f, border=1, ln=True, align="C")

        # 4. Galería de Evidencia
        fotos = audit_json.get('fotos', {})
        if fotos:
            pdf.add_page()
            pdf.set_font("Helvetica", "B", 12)
            pdf.cell(0, 10, "4. GALERIA DE EVIDENCIA", ln=True)
            pdf.ln(5)

            w_req = 90
            w_fot = 70
            w_res = 30

            # Cabecera Tabla de Fotos
            def imprimir_cabecera_fotos():
                pdf.set_font("Helvetica", "B", 9)
                pdf.set_fill_color(230, 230, 230)
                pdf.set_text_color(0, 0, 0)
                pdf.cell(w_req, 8, " Requisito / Pregunta Evaluada", border=1, fill=True)
                pdf.cell(w_fot, 8, " Evidencia Fotográfica", border=1, fill=True, align="C")
                pdf.cell(w_res, 8, " Resultado", border=1, fill=True, align="C", ln=True)
                pdf.set_font("Helvetica", "", 8)

            imprimir_cabecera_fotos()

            for q_id, f_path in fotos.items():
                if f_path and os.path.exists(f_path):
                    txt_q = texto_seguro(q_id.replace("_", " - "))
                    resp = respuestas.get(q_id, "N/A")

                    # Calcular alturas
                    lineas = pdf.multi_cell(w_req, 4, f" {txt_q}", split_only=True)
                    h_txt = len(lineas) * 4
                    h_img = 45 # Fijo referencial para la fila
                    h_row = max(h_txt, h_img) + 6

                    if pdf.get_y() + h_row > 270:
                        pdf.add_page()
                        imprimir_cabecera_fotos()

                    cur_y = pdf.get_y()
                    cur_x = pdf.get_x()

                    # Dibujar Rectángulos
                    pdf.rect(cur_x, cur_y, w_req, h_row)
                    pdf.rect(cur_x + w_req, cur_y, w_fot, h_row)
                    pdf.rect(cur_x + w_req + w_fot, cur_y, w_res, h_row)

                    # Col 1: Texto Requisito
                    pdf.set_xy(cur_x, cur_y + 3)
                    pdf.multi_cell(w_req, 4, f" {txt_q}", border=0, align="L")

                    # Col 2: Imagen
                    pdf.image(f_path, x=cur_x + w_req + 2.5, y=cur_y + 3, w=65, h=h_row - 6, keep_aspect_ratio=True)

                    # Col 3: Resultado (alineado al centro vertical)
                    pdf.set_xy(cur_x + w_req + w_fot, cur_y)
                    pdf.cell(w_res, h_row, resp, border=0, ln=True, align="C")

                    # Mover el cursor al final de la fila para la siguiente iteración
                    pdf.set_y(cur_y + h_row)

        # Retornar buffer
        return bytes(pdf.output(dest='S'))
