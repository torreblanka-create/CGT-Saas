import os

import pandas as pd
from fpdf import FPDF

from .base import ReporteCGT, texto_seguro


def generar_pdf_irl(datos, df_riesgos, logo_cgt, logo_cliente):
    """
    Genera el Certificado de Conformidad (IRL) DS 44 basado en el formato exacto de Steel Ingeniería.
    """
    # Redefinimos cabecera para apagar título por defecto
    class FormatoDS44(FPDF):
        def header(self):
            if os.path.exists(logo_cliente):
                self.image(logo_cliente, 160, 8, 40)
            self.ln(20)

        def footer(self):
            self.set_y(-25)
            self.set_font("Helvetica", "B", 8)
            self.cell(100, 5, "Enero 2025", border=0, align="R", ln=True)
            self.cell(100, 5, "Revisión 1", border=0, align="R")

            # Cuadro firma
            self.set_y(-28)
            self.set_x(120)
            self.cell(80, 20, "", border=1) # Caja vacía
            self.set_y(-18)
            self.set_x(120)
            self.cell(80, 5, "FIRMA", border=0, align="C", ln=True)
            self.set_x(120)
            self.cell(80, 5, f"Página {self.page_no()}/{{nb}}", border=0, align="C")

    pdf = FormatoDS44("P")
    pdf.alias_nb_pages()

    # ---------------- HOJA 1: Antecedentes ----------------
    pdf.add_page()

    # TITULO PRINCIPAL
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 7, "CERTIFICADO DE CONFORMIDAD DE LA INFORMACION DE LOS RIESGOS LABORALES", align="C", ln=True)
    pdf.cell(0, 7, "RECIBIDA POR LA PERSONA TRABAJADORA (Art 15. DS 44)", align="C", ln=True)
    pdf.ln(5)

    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(0, 5, "El Decreto Supremo N° 44, en su párrafo 4, articulo N° 15, dispone que:\n\n\"La entidad empleadora deberá garantizar que cada persona trabajadora, previo al inicio de las labores, reciba de forma oportuna y adecuada información acerca de los riesgos que entrañan sus labores, de las medidas preventivas y los métodos o procedimientos de trabajo correctos, determinados conforme a la matriz de riesgos y el programa de trabajo preventivo\".")
    pdf.ln(5)

    # 1. Antecedentes Generales de la entidad empleadora.
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 8, "1. Antecedentes Generales de la entidad empleadora.", ln=True)
    pdf.set_font("Helvetica", "", 10)

    h_c = 7
    pdf.cell(120, h_c, f" Empresa: {datos['empresa_principal']}", border=1)
    pdf.cell(0, h_c, f" R.U.T: {datos['rut_empresa']}", border=1, ln=True)
    pdf.cell(0, h_c, f" Rep. Legal: {datos['rep_legal']}", border=1, ln=True)
    pdf.cell(0, h_c, f" Dirección Casa Matriz: {datos['direccion']}", border=1, ln=True)
    pdf.ln(5)

    # 2. Antecedentes Generales de la persona Trabajadora
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 8, "2. Antecedentes Generales de la persona Trabajadora", ln=True)
    pdf.set_font("Helvetica", "I", 9)
    pdf.multi_cell(0, 5, "> Registre los antecedentes personales y datos debidamente verificados de la persona trabajadora que recibirá la Información de los Riesgos Profesionales específicos y generales:")
    pdf.ln(2)

    pdf.set_font("Helvetica", "B", 10)
    w1, w2 = 60, 130

    # Tabla Trabajador
    campos_trab = [
        ("NOMBRE", datos['nombre_trab']),
        ("R.U.T.", datos['rut_trab']),
        ("CARGO / PUESTO DE TRABAJO", datos['cargo']),
        ("Nombre Contacto Emergencia", ""),
        ("Teléfono Contacto Emergencia", ""),
        ("ÁREA DE TRABAJO", datos['area']),
        ("SERVICIO", datos['servicio']),
        ("FECHA", datos['fecha'])
    ]

    for titulo, valor in campos_trab:
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(w1, h_c, f" {titulo}", border=1)
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(w2, h_c, f" {valor}", border=1, ln=True)

    pdf.ln(5)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 6, "Información de los Riesgos Profesionales a la persona Trabajadora por:", ln=True)

    # Cajas de checkbox (simuladas)
    cajas = ["[ ] Trabajador Nuevo", "[ ] Nuevas Tareas/Actividades", "[ ] Reubicación", "[ ] Desempeño en Área Única"]
    # Marcar el correcto
    for i in range(len(cajas)):
        if datos['motivo'].split()[0] in cajas[i]: cajas[i] = cajas[i].replace("[ ]", "[X]")

    pdf.set_font("Helvetica", "", 10)
    pdf.cell(60, 6, cajas[0])
    pdf.cell(70, 6, cajas[1])
    pdf.cell(60, 6, cajas[2], ln=True)

    # ---------------- HOJA 2: RIESGOS Y MEDIDAS (DINÁMICO SEGÚN BASE DE DATOS) ----------------
    pdf.add_page()

    # --- SECCIÓN 6.5 TARJETA VERDE ---
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_fill_color(230, 230, 230)
    pdf.cell(0, 8, "6.5 TARJETA VERDE Y REPORTE DE PELIGRO", ln=True, fill=True)
    pdf.set_font("Helvetica", "", 9)
    txt_65 = "La TARJETA VERDE Y EL REPORTE DE PELIGRO es un respaldo que la Corporación otorga a sus trabajadores para detener un trabajo cuando considere que los riesgos no están controlados en su totalidad. El principal sustento de esta herramienta preventiva es el primer valor 'El respeto a la vida y dignidad de las personas'.\n\nSus objetivos específicos son: Empoderar y respaldar a los trabajadores para no realizar una actividad si consideran que los riesgos no están controlados; Posibilita que el trabajador se haga cargo de su seguridad y la de sus compañeros."
    pdf.multi_cell(0, 5, texto_seguro(txt_65))
    pdf.ln(5)

    # --- SECCIÓN 6.6 ART ---
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 8, "6.6 ANÁLISIS DE RIESGO DE LA TAREA (ART)", ln=True, fill=True)
    pdf.set_font("Helvetica", "", 9)
    txt_66 = "El ART is a preventive tool that can save your life, identifies hazards of each task, evaluates risks, defines control measures for each case. It must always be used before starting a task and when a change in activity occurs."
    pdf.multi_cell(0, 5, texto_seguro(txt_66))
    pdf.ln(5)

    # --- SECCIÓN 6.7 PROCEDIMIENTOS ---
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 8, "6.7 Procedimientos de Trabajo", ln=True, fill=True)
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(140, 6, " Procedimientos Criticos de la Organización / Control de Riesgos Operacionales", border=1)
    pdf.cell(50, 6, " Código Asignado", border=1, ln=True, align="C")
    pdf.cell(140, 6, " Aplicable según Matriz de Procedimientos de la Empresa", border=1)
    pdf.cell(50, 6, " N/A", border=1, ln=True, align="C")
    pdf.ln(10)

    # Función auxiliar para renderizar tablas robustas
    def dibujar_tabla_riesgos(df_seccion, titulo, bajada, w_p=40, w_r=45, w_m=105, texto_vacio="NO APLICA. SECCIÓN SIN RESULTADOS EN MATRIZ."):
        pdf.set_font("Helvetica", "B", 10)
        pdf.multi_cell(190, 6, texto_seguro(titulo))
        pdf.set_font("Helvetica", "I", 9)
        pdf.multi_cell(190, 5, texto_seguro(bajada))
        pdf.ln(2)

        pdf.set_fill_color(220, 220, 220)
        pdf.set_font("Helvetica", "B", 8)

        # Headers
        h_x = pdf.get_x()
        h_y = pdf.get_y()
        pdf.rect(h_x, h_y, w_p, 8, 'DF')
        pdf.rect(h_x + w_p, h_y, w_r, 8, 'DF')
        pdf.rect(h_x + w_p + w_r, h_y, w_m, 8, 'DF')

        pdf.set_xy(h_x, h_y)
        pdf.cell(w_p, 8, "Actividad / Categoría", align="C")
        pdf.cell(w_r, 8, "Peligros Potenciales / Riesgos", align="C")
        pdf.cell(w_m, 8, "Medidas de Prevención and/or Control", align="C", ln=True)
        pdf.set_y(h_y + 8)

        pdf.set_font("Helvetica", "", 8)

        if df_seccion.empty:
            x_init = pdf.get_x()
            y_init = pdf.get_y()
            pdf.rect(x_init, y_init, w_p + w_r + w_m, 10)
            pdf.cell(0, 10, texto_seguro(texto_vacio), align="C", ln=True)
            pdf.ln(5)
            return

        for _, row in df_seccion.iterrows():
            actividad = texto_seguro(row['actividad'])
            peligro = texto_seguro(row['peligros_riesgos'])
            medida = texto_seguro(row['medidas_control'])

            # Calcular líneas
            lineas_a = pdf.multi_cell(w_p, 4, actividad, split_only=True)
            lineas_p = pdf.multi_cell(w_r, 4, peligro, split_only=True)
            lineas_m = pdf.multi_cell(w_m, 4, medida, split_only=True)

            max_l = max(len(lineas_a), len(lineas_p), len(lineas_m), 1)
            alto_fila = max_l * 4 + 4 # 4 de padding (2 arriba 2 abajo)

            if pdf.get_y() + alto_fila > 240:
                pdf.add_page()
                # Reimprimir headers si hay salto
                h_x = pdf.get_x()
                h_y = pdf.get_y()
                pdf.set_font("Helvetica", "B", 8)
                pdf.rect(h_x, h_y, w_p, 8, 'DF')
                pdf.rect(h_x + w_p, h_y, w_r, 8, 'DF')
                pdf.rect(h_x + w_p + w_r, h_y, w_m, 8, 'DF')
                pdf.set_xy(h_x, h_y)
                pdf.cell(w_p, 8, "Actividad / Categoría", align="C")
                pdf.cell(w_r, 8, "Peligros Potenciales / Riesgos", align="C")
                pdf.cell(w_m, 8, "Medidas de Prevención y/o Control", align="C", ln=True)
                pdf.set_y(h_y + 8)
                pdf.set_font("Helvetica", "", 8)

            x_init = pdf.get_x()
            y_init = pdf.get_y()

            # Dibujar rectángulos maestros (Bordes)
            pdf.rect(x_init, y_init, w_p, alto_fila)
            pdf.rect(x_init + w_p, y_init, w_r, alto_fila)
            pdf.rect(x_init + w_p + w_r, y_init, w_m, alto_fila)

            # Imprimir textos (sin borde propio) a 2 units del borde superior
            pdf.set_xy(x_init, y_init + 2)
            pdf.multi_cell(w_p, 4, actividad, border=0, align="L")

            pdf.set_xy(x_init + w_p, y_init + 2)
            pdf.multi_cell(w_r, 4, peligro, border=0, align="L")

            pdf.set_xy(x_init + w_p + w_r, y_init + 2)
            pdf.multi_cell(w_m, 4, medida, border=0, align="L")

            # Mover cursor abajo para la próxima fila
            pdf.set_y(y_init + alto_fila)

        pdf.ln(5)

    # Fraccionamiento de matrices
    df_esp = df_riesgos[df_riesgos['tipo_riesgo'].isin(['Riesgos Específicos Operativos', 'Manipulación Manual de Cargas'])]
    df_594 = df_riesgos[df_riesgos['tipo_riesgo'] == 'Agentes Físicos/Químicos (DS 594)']
    # Sustancias químicas lo dejamos vacío forzado según imagen 3 (NO UTILIZA)
    df_gen = df_riesgos[df_riesgos['tipo_riesgo'] == 'Peligros Generales (Clima, Incendio)']

    # --- SECCIÓN 7: ESPECÍFICOS ---
    dibujar_tabla_riesgos(
        df_esp,
        "7. Indique los Peligros Potenciales, Riesgos Profesionales Específicos y Medidas de Prevención.",
        "> Identifique e informe los peligros asociados a la función o puesto de trabajo y de las medidas de control."
    )

    # --- SECCIÓN 8: DS 594 ---
    dibujar_tabla_riesgos(
        df_594,
        "8. Riesgos a la Salud Ocupacional por Agentes Físicos, Químicos y Biológicos (DS 594).",
        "> Identifique en forma individual los agentes sobre límites de exposición permisibles o que generan enfermedad profesional."
    )

    # --- SECCIÓN 9: SUSTANCIAS ---
    dibujar_tabla_riesgos(
        pd.DataFrame(), # Pasamos vacío a propósito para esta sección default
        "9. Peligros Profesionales por Productos y Sustancias Peligrosas.",
        "> Identifique, registre e informe los elementos que deba utilizar en los procesos.",
        texto_vacio="NO UTILIZA SUSTANCIAS PELIGROSAS"
    )

    # --- SECCIÓN 10: GENERALES ---
    dibujar_tabla_riesgos(
        df_gen,
        "10. Peligros / Riesgos Generales que afecten la integridad física.",
        "> Identifique aquellos aplicables al entorno laboral como emergencias, sismos, clima."
    )

    # ---------------- HOJA FINAL: FIRMAS ----------------
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 10, "DECLARACIÓN FINAL (DS 44)", align="C", ln=True)
    pdf.ln(5)

    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(0, 5, "Declaro que he sido informado acerca de los riesgos que entrañan o son inherentes a las labores que desempeñaré y sobre las medidas preventivas que deberé aplicar en el desempeño de mis labores.\n\nDeclaro que he sido instruido sobre los métodos de trabajo correctos y el uso adecuado de los Elementos de Protección Personal (EPP).")

    pdf.ln(30)
    pdf.set_font("Helvetica", "B", 10)

    # Cuadros de firma formales
    h_f = 20
    pdf.cell(60, h_f, "", border=1)
    pdf.cell(10, h_f, "", border=0)
    pdf.cell(60, h_f, "", border=1)
    pdf.cell(10, h_f, "", border=0)
    pdf.cell(50, h_f, "", border=1, ln=True)

    pdf.cell(60, 5, "Firma de la Persona Trabajadora", border=0, align="C")
    pdf.cell(10, 5, "", border=0)
    pdf.cell(60, 5, f"Firma del Instructor", border=0, align="C")
    pdf.cell(10, 5, "", border=0)
    pdf.cell(50, 5, "Firma Empresa", border=0, align="C", ln=True)

    pdf.cell(60, 5, f"RUT: {datos['rut_trab']}", border=0, align="C")
    pdf.cell(10, 5, "", border=0)
    pdf.cell(60, 5, f"Nombre: {datos['instructor']}", border=0, align="C")

    # Guardar y retornar PDF
def generar_pdf_art(datos, logo_app, logo_cliente):
    from config.config import DB_PATH
    from core.reports.generadores.pdf_art import GeneradorPdfART

    # Adaptador de compatibilidad hacia la nueva clase modular
    gen = GeneradorPdfART(datos, logo_app, logo_cliente, DB_PATH)
    return gen.generar()

def generar_pdf_compliance(audit_id, logo_app, logo_cliente):
    from config.config import DB_PATH
    from core.reports.generadores.compliance import GeneradorPdfCompliance

    gen = GeneradorPdfCompliance(audit_id, DB_PATH, logo_app, logo_cliente)
    return gen.generar()

def generar_pdf_fuf_ds44(audit_id, logo_app, logo_cliente):
    from config.config import DB_PATH
    from core.reports.generadores.fuf_ds44 import GeneradorPdfFUF

    gen = GeneradorPdfFUF(audit_id, DB_PATH, logo_app, logo_cliente)
    return gen.generar()
