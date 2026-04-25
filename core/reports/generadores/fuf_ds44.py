import json
import os
from datetime import datetime

from core.reports.base import ReporteCGT, texto_seguro, truncar


class GeneradorPdfFUF:
    """
    Generador de reportes de alta fidelidad para el Formulario Único de Fiscalización (FUF) 
    del Decreto Supremo 44/2025.
    """
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

        # Configuración del PDF (Horizontal para mejor legibilidad de 60 ítems)
        pdf = ReporteCGT(
            titulo="FORMULARIO ÚNICO de FISCALIZACIÓN (FUF)",
            logo_cgt=self.logo_app,
            logo_cliente=self.logo_cliente,
            sub_titulo=f"Cumplimiento Normativo DS 44/2025 | {datos['empresa']}"
        )
        pdf.alias_nb_pages()
        pdf.add_page()

        # 1. Información General de la Auditoría
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_fill_color(220, 230, 250)
        pdf.cell(0, 8, " 1. ANTECEDENTES GENERALES", border=1, ln=True, fill=True)
        pdf.set_font("Helvetica", "", 9)

        h_c = 7
        pdf.cell(40, h_c, " Empresa:", border=1)
        pdf.cell(100, h_c, f" {datos['empresa']}", border=1)
        pdf.cell(20, h_c, " Fecha:", border=1)
        pdf.cell(0, h_c, f" {datos['fecha']}", border=1, ln=True)

        pdf.cell(40, h_c, " Auditor:", border=1)
        pdf.cell(100, h_c, f" {datos['auditor']}", border=1)
        pdf.cell(20, h_c, " Puntaje:", border=1)

        pct = datos['puntaje_final']
        color = (16, 185, 129) if pct >= 90 else (245, 158, 11) if pct >= 75 else (239, 68, 68)
        pdf.set_text_color(*color)
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, h_c, f" {pct:.1f}% ({datos['clasificacion']})", border=1, ln=True)
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Helvetica", "", 9)
        pdf.ln(5)

        # 2. Resumen por Ámbito
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 8, " 2. BALANCE POR ÁMBITOS DE FISCALIZACIÓN", border=1, ln=True, fill=True)
        pdf.ln(2)

        audit_json = json.loads(datos['datos_json'])
        respuestas = audit_json.get('respuestas', {})

        # Agrupar respuestas por ámbitos (detectar por texto)
        ambitos_score = {}
        curr_a = "Gestión"
        for q, r in respuestas.items():
            if "AMBITO I" in q or "Gestión" in q: curr_a = "SGSST"
            elif "AMBITO II" in q or "MIPER" in q: curr_a = "MIPER"
            elif "AMBITO III" in q or "Planificación" in q: curr_a = "Planificación"
            elif "AMBITO IV" in q or "Organización" in q: curr_a = "Organización"
            elif "AMBITO V" in q or "Capacitación" in q: curr_a = "Capacitación"
            elif "AMBITO VI" in q or "Protección" in q: curr_a = "Protección"
            elif "AMBITO VII" in q or "Accidentes" in q: curr_a = "Accidentes"

            if curr_a not in ambitos_score: ambitos_score[curr_a] = {"si": 0, "total": 0}
            if r != "N/A":
                ambitos_score[curr_a]["total"] += 1
                if r == "Sí": ambitos_score[curr_a]["si"] += 1

        # Dibujar Gráfico/Tabla de Ámbitos
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(80, 7, " Ámbito de Control", border=1, fill=True)
        pdf.cell(30, 7, " Cumplimiento", border=1, fill=True, align="C")
        pdf.cell(80, 7, " Estado Visual", border=1, fill=True, align="C", ln=True)
        pdf.set_font("Helvetica", "", 9)

        for amb, val in ambitos_score.items():
            res = (val['si'] / val['total'] * 100) if val['total'] > 0 else 100
            pdf.cell(80, 6, f" {amb}", border=1)
            pdf.cell(30, 6, f" {res:.1f}%", border=1, align="C")

            # Barra de progreso visual
            x_b = pdf.get_x()
            y_b = pdf.get_y()
            pdf.rect(x_b + 5, y_b + 1.5, 70, 3)
            # Relleno proporcional
            if res >= 90: pdf.set_fill_color(16, 185, 129)
            elif res >= 75: pdf.set_fill_color(245, 158, 11)
            else: pdf.set_fill_color(239, 68, 68)
            pdf.rect(x_b + 5, y_b + 1.5, (res/100)*70, 3, 'F')
            pdf.set_fill_color(220, 230, 250) # Reset color
            pdf.cell(80, 6, "", border=1, ln=True)

        pdf.ln(8)

        # 3. Detalle de los 60 Ítems (Tabla Extendida)
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 8, " 3. DESGLOSE TÉCNICO DE FISCALIZACIÓN (FULL FUF)", border=1, ln=True, fill=True)
        pdf.ln(2)

        pdf.set_font("Helvetica", "B", 8)
        w_n = 10
        w_q = 150
        w_r = 30
        pdf.cell(w_n, 7, " N°", border=1, align="C", fill=True)
        pdf.cell(w_q, 7, " Requisito / Punto de Control", border=1, fill=True)
        pdf.cell(w_r, 7, " Resultado", border=1, align="C", fill=True, ln=True)

        pdf.set_font("Helvetica", "", 7)
        idx = 1
        for q, r in respuestas.items():
            if q.startswith("AMBITO"):
                pdf.set_font("Helvetica", "B", 8)
                pdf.set_fill_color(240, 240, 240)
                pdf.cell(0, 6, f" {q}", border=1, ln=True, fill=True)
                pdf.set_font("Helvetica", "", 7)
                pdf.set_fill_color(220, 230, 250)
                continue

            # Altura dinámica
            lineas = pdf.multi_cell(w_q, 4, texto_seguro(q), split_only=True)
            h_row = max(len(lineas) * 4 + 2, 7)

            if pdf.get_y() + h_row > 270:
                pdf.add_page()
                # Headers nuevamente
                pdf.set_font("Helvetica", "B", 8)
                pdf.cell(w_n, 7, " N°", border=1, align="C", fill=True)
                pdf.cell(w_q, 7, " Requisito / Punto de Control", border=1, fill=True)
                pdf.cell(w_r, 7, " Resultado", border=1, align="C", fill=True, ln=True)
                pdf.set_font("Helvetica", "", 7)

            x_pos = pdf.get_x()
            y_pos = pdf.get_y()
            pdf.rect(x_pos, y_pos, w_n, h_row)
            pdf.cell(w_n, h_row, str(idx), align="C")

            pdf.set_xy(x_pos + w_n, y_pos)
            pdf.multi_cell(w_q, 4, texto_seguro(q), border=1)

            pdf.set_xy(x_pos + w_n + w_q, y_pos)
            if r == "Sí": pdf.set_text_color(0, 128, 0)
            elif r == "No": pdf.set_text_color(200, 0, 0)
            else: pdf.set_text_color(100, 100, 100)

            pdf.cell(w_r, h_row, r, border=1, align="C", ln=True)
            pdf.set_text_color(0, 0, 0)
            idx += 1

        # 4. Declaración y Firmas
        if pdf.get_y() > 220: pdf.add_page()
        pdf.ln(10)
        pdf.set_font("Helvetica", "B", 10)
        pdf.multi_cell(0, 6, "DECLARACIÓN DE VERACIDAD:\nEl presente informe constituye un registro fidedigno de las condiciones observadas durante la inspección de cumplimiento DS 44/2025. Los resultados obtenidos reflejan el estado del Sistema de Gestión de SST a la fecha de emisión.")

        pdf.ln(20)
        pdf.set_font("Helvetica", "B", 9)
        w_f = 90
        pdf.cell(w_f, 25, "", border=1)
        pdf.cell(10, 25, "")
        pdf.cell(w_f, 25, "", border=1, ln=True)
        pdf.cell(w_f, 5, " Firma Auditor Responsable", align="C")
        pdf.cell(10, 5, "")
        pdf.cell(w_f, 5, " Firma Representante Empresa", align="C", ln=True)

        return bytes(pdf.output(dest='S'))
