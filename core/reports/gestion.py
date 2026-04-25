import json
import os

from .base import ReporteCGT, texto_seguro, truncar


def generar_pdf_plan_accion(nombre_plan, df_act, df_ev, logo_app, logo_cliente):
    pdf = ReporteCGT("Informe Ejecutivo de Seguimiento", logo_app, logo_cliente, orientation='L')
    pdf.add_page(); pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, f"PLAN MAESTRO: {texto_seguro(nombre_plan)}", ln=True, align='C')

    total = len(df_act); cerradas = len(df_act[df_act['estado'] == 'Cerrado'])
    progreso = int((cerradas / total) * 100) if total > 0 else 0
    pdf.set_font("Helvetica", "", 10); pdf.cell(0, 8, f"Avance Global: {progreso}%  |  Actividades Cerradas: {cerradas} de {total}", ln=True, align='C'); pdf.ln(5)

    w_id, w_acc, w_res, w_fec, w_est, w_evid = 10, 90, 40, 25, 20, 90
    pdf.set_font("Helvetica", "B", 9); pdf.set_fill_color(10, 88, 202); pdf.set_text_color(255, 255, 255)

    headers = ["ID", "Acción", "Responsable", "Cierre", "Estado", "Evidencias"]
    anchos = [w_id, w_acc, w_res, w_fec, w_est, w_evid]
    for i in range(len(headers)): pdf.cell(anchos[i], 10, headers[i], 1, 0, 'C', fill=True)
    pdf.ln(); pdf.set_font("Helvetica", "", 8); pdf.set_text_color(0, 0, 0)

    for _, row in df_act.iterrows():
        id_act = str(row['id']); accion = texto_seguro(row['accion']); responsable = texto_seguro(row['responsable'])
        evs = df_ev[df_ev['plan_id'].astype(str) == id_act]['descripcion'].tolist()
        evidencias = " - " + "\n - ".join(evs) if evs else "Sin evidencias"
        lineas_accion = pdf.multi_cell(w_acc, 5, accion, split_only=True)
        lineas_evidencia = pdf.multi_cell(w_evid, 5, evidencias, split_only=True)
        alto_fila = max(len(lineas_accion), len(lineas_evidencia), 1) * 6
        if pdf.get_y() + alto_fila > 185: pdf.add_page()
        y_inicial = pdf.get_y(); x_inicial = pdf.get_x()
        pdf.cell(w_id, alto_fila, id_act, 1, 0, 'C')
        pdf.multi_cell(w_acc, alto_fila / len(lineas_accion) if lineas_accion else alto_fila, accion, border=1, align='L')
        pdf.set_xy(x_inicial + w_id + w_acc, y_inicial)
        pdf.cell(w_res, alto_fila, truncar(responsable, 30), 1, 0, 'C'); pdf.cell(w_fec, alto_fila, str(row['fecha_cierre']), 1, 0, 'C'); pdf.cell(w_est, alto_fila, str(row['estado']), 1, 0, 'C')
        pdf.multi_cell(w_evid, alto_fila / len(lineas_evidencia) if lineas_evidencia else alto_fila, evidencias, border=1, align='L'); pdf.set_y(y_inicial + alto_fila)

    return bytes(pdf.output())

def generar_pdf_informe_calidad(datos, fotos, logo_app, logo_cliente, template_id="generico"):
    if template_id == "generico":
        return generar_pdf_informe_calidad_estandar(datos, fotos, logo_app, logo_cliente)
    else:
        from .templates import TEMPLATE_CONFIG
        template = TEMPLATE_CONFIG.get(template_id)
        if not template:
            return generar_pdf_informe_calidad_estandar(datos, fotos, logo_app, logo_cliente)
        return generar_pdf_informe_calidad_plantilla(datos, fotos, logo_app, logo_cliente, template)

def generar_pdf_informe_calidad_estandar(datos, fotos, logo_app, logo_cliente):
    pdf = ReporteCGT(f"INFORME DE CALIDAD: {datos['titulo'].upper()}", logo_app, logo_cliente)
    pdf.alias_nb_pages(); pdf.add_page()

    pdf.set_font("Helvetica", "B", 11); pdf.set_fill_color(25, 58, 138); pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 10, " 1. DATOS DEL PROYECTO Y EJECUTOR", 1, 1, 'L', fill=True)
    pdf.set_font("Helvetica", "B", 10); pdf.set_text_color(0, 0, 0)
    pdf.cell(40, 8, " Empresa:", 1); pdf.set_font("Helvetica", "", 10); pdf.cell(150, 8, f" {datos['empresa']}", 1, 1)
    pdf.set_font("Helvetica", "B", 10); pdf.cell(40, 8, " Contrato/Faena:", 1); pdf.set_font("Helvetica", "", 10); pdf.cell(150, 8, f" {datos['contrato']}", 1, 1)
    pdf.set_font("Helvetica", "B", 10); pdf.cell(40, 8, " Técnico a Cargo:", 1); pdf.set_font("Helvetica", "", 10); pdf.cell(150, 8, f" {datos['tecnico']}", 1, 1); pdf.ln(5)

    pdf.set_font("Helvetica", "B", 11); pdf.set_fill_color(230, 230, 230); pdf.cell(0, 10, " 2. DESCRIPCIÓN DEL TRABAJO REALIZADO", 1, 1, 'L', fill=True); pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(0, 7, f" {datos['descripcion']}", border=1); pdf.ln(40)
    pdf.set_font("Helvetica", "B", 10); pdf.cell(95, 10, "__________________________", 0, 0, 'C'); pdf.cell(95, 10, "__________________________", 0, 1, 'C')
    pdf.set_font("Helvetica", "", 10); pdf.cell(95, 5, "Firma Técnico Ejecutor", 0, 0, 'C'); pdf.cell(95, 5, "Firma Supervisor / Control Calidad", 0, 1, 'C')

    if fotos:
        pdf.add_page(); pdf.set_font("Helvetica", "B", 11); pdf.set_fill_color(25, 58, 138); pdf.set_text_color(255, 255, 255)
        pdf.cell(0, 10, " 3. REGISTRO FOTOGRÁFICO", 1, 1, 'C', fill=True); pdf.ln(5)
        col_w, img_h, x_left, x_right, y_start, y_padding = 85, 85, 15, 110, pdf.get_y(), 15
        pdf.set_text_color(0, 0, 0)
        for i, f_data in enumerate(fotos):
            col, fila = i % 2, (i // 2) % 2
            if i > 0 and i % 4 == 0: pdf.add_page(); y_start, fila = 30, 0
            curr_x, curr_y = (x_left if col == 0 else x_right), y_start + (fila * (img_h + 15 + y_padding))
            pdf.set_xy(curr_x, curr_y); pdf.set_font("Helvetica", "B", 9); pdf.multi_cell(col_w, 5, f" FOTO {i+1}: {truncar(f_data['descripcion'], 60)}", border=0, align='C')
            img_y = pdf.get_y() + 2
            try: pdf.image(f_data['path'], x=curr_x, y=img_y, w=col_w, h=img_h)
            except Exception as e: pdf.set_xy(curr_x, img_y + (img_h/2)); pdf.cell(col_w, 10, f"[Error: {str(e)[:20]}]", align='C')

    return bytes(pdf.output())

def generar_pdf_informe_calidad_plantilla(datos, fotos, logo_app, logo_cliente, template):
    pdf = ReporteCGT(f"INFORME DE CALIDAD: {template['nombre'].upper()}", logo_app, logo_cliente)
    pdf.alias_nb_pages(); pdf.add_page()

    # Renderizar secciones basadas en campos
    for sec in template['secciones']:
        # Verificar si hay espacio para una nueva sección
        if pdf.get_y() > 240: pdf.add_page()

        pdf.set_font("Helvetica", "B", 11); pdf.set_fill_color(25, 58, 138); pdf.set_text_color(255, 255, 255)
        pdf.cell(0, 10, f" {sec['titulo'].upper()}", 1, 1, 'L', fill=True)
        pdf.set_text_color(0, 0, 0)

        if sec.get('type') == 'checklist':
            # Renderizar tabla de checklist con fotos si existen
            pdf.set_font("Helvetica", "B", 9); pdf.set_fill_color(240, 240, 240)
            pdf.cell(80, 8, " Puntos de verificación", 1, 0, 'L', fill=True)
            pdf.cell(90, 8, " Evidencia Fotográfica", 1, 0, 'C', fill=True)
            pdf.cell(20, 8, " Status", 1, 1, 'C', fill=True)

            pdf.set_font("Helvetica", "", 9)
            for item_idx, item_label in enumerate(sec['items']):
                # Buscar si hay foto para este item en los datos
                foto_data = datos.get(f"foto_{sec['id']}_{item_idx}")
                ok_status = "OK" if datos.get(f"ok_{sec['id']}_{item_idx}") else ""

                start_y = pdf.get_y()
                # Altura dinámica según si hay foto
                h_row = 35 if foto_data else 10
                if start_y + h_row > 270: pdf.add_page(); start_y = pdf.get_y()

                pdf.multi_cell(80, h_row, f" {item_label}", border=1, align='L')

                # Insertar foto pequeña en la celda central (Columna de 90mm entre 90 y 180)
                # Centramos una imagen de hasta 80mm de ancho: 90 + (90-80)/2 = 95
                pdf.set_xy(90, start_y)
                if foto_data and os.path.exists(foto_data):
                    try:
                        # Forzamos max 80x30mm centrada en la celda de 90x35mm
                        pdf.image(foto_data, x=95, y=start_y + 2, w=80, h=30)
                    except:
                        pdf.set_xy(90, start_y)
                        pdf.cell(90, h_row, "[Error imagen]", 1, 0, 'C')

                    # Dibujar el borde de la celda (ya que image no dibuja bordes)
                    pdf.set_xy(90, start_y)
                    pdf.cell(90, h_row, "", 1, 0)
                else:
                    pdf.cell(90, h_row, "Sin evidencia", 1, 0, 'C')

                pdf.cell(20, h_row, ok_status, 1, 1, 'C')
            pdf.ln(5)
        else:
            # Renderizar pares label: valor
            pdf.set_font("Helvetica", "B", 10)
            for cam in sec['campos']:
                valor = str(datos.get(cam['id'], "N/A"))
                pdf.set_font("Helvetica", "B", 10); pdf.cell(60, 8, f" {cam['label']}:", 1)
                pdf.set_font("Helvetica", "", 10); pdf.cell(130, 8, f" {valor}", 1, 1)
            pdf.ln(5)

    # Sección Final de Firmas (Siempre presente)
    if pdf.get_y() > 220: pdf.add_page()
    pdf.ln(10)
    pdf.set_font("Helvetica", "B", 9)
    # 4 Columnas de firmas
    w_f = 190 / 4
    for label in ["Elaborado por:", "Revisado por:", "Autorización 1:", "Autorización 2:"]:
        pdf.cell(w_f, 8, label, 1, 0, 'C')
    pdf.ln()
    for _ in range(3): # Espacio para firma
        for _ in range(4): pdf.cell(w_f, 10, "", 1, 0)
        pdf.ln()
    for _ in range(4): pdf.cell(w_f, 8, "Fecha: ___/___/___", 1, 0, 'C')
    pdf.ln()

    return bytes(pdf.output())

    return bytes(pdf.output())

def generar_pdf_confiabilidad(datos, logo_app, logo_cliente):
    from config.config import DB_PATH
    from core.reports.generadores.pdf_falla import GeneradorPdfFalla

    # Adaptador de compatibilidad hacia la nueva clase modular
    gen = GeneradorPdfFalla(datos, logo_app, logo_cliente, DB_PATH)
    return gen.generar()

def generar_pdf_incidente(datos, logo_app, logo_cliente):
    pdf = ReporteCGT("Alerta de Incidente", logo_app, logo_cliente)
    pdf.alias_nb_pages()
    pdf.add_page()

    # --- CABECERA ESTILO VELTIS ---
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_y(28)
    pdf.cell(0, 5, "VELTV-F-SGI-HS-0005 / Fecha de emisión: Enero-2026 / Vigencia 3 años / Revisión: 3", align='C', ln=True)

    # --- TÍTULO ROJO LLAMATIVO ---
    pdf.set_fill_color(180, 0, 0); pdf.set_text_color(255, 255, 255); pdf.set_font("Helvetica", "BI", 14)
    titulo_alerta = datos.get('folio', 'SIN TÍTULO DE ALERTA')
    pdf.cell(0, 10, f" {titulo_alerta} ", 0, 1, 'C', fill=True)
    pdf.set_text_color(0, 0, 0); pdf.ln(2)

    # --- SECCIÓN 1: INFORMACIÓN GENERAL ---
    pdf.set_fill_color(120, 120, 120); pdf.set_text_color(255, 255, 255); pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 8, " INFORMACIÓN GENERAL", 0, 1, 'L', fill=True)
    pdf.set_text_color(0, 0, 0); pdf.set_font("Helvetica", "B", 9)

    col1, col2, col3 = 60, 60, 70
    pdf.set_fill_color(235, 235, 235)

    # Fila 1
    pdf.cell(col1, 6, " Fecha del Incidente", 0, 0); pdf.cell(col2, 6, " Hora", 0, 0); pdf.cell(col3, 6, " Tipo de Evento", 0, 1)
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(col1, 7, f" {datos['fecha']}", 1, 0, 'L', fill=True); pdf.cell(col2, 7, f" {datos['hora']}", 1, 0, 'L', fill=True); pdf.cell(col3, 7, f" {datos['tipo_evento']}", 1, 1, 'L', fill=True)

    # Fila 2: Contrato
    pdf.ln(1); pdf.set_font("Helvetica", "B", 9); pdf.cell(0, 6, " Contrato (Seleccione su contrato del listado)", 0, 1)
    pdf.set_font("Helvetica", "", 9); pdf.cell(0, 7, f" {datos.get('contrato_nom', 'N/A')}", 1, 1, 'L', fill=True)

    # Fila 3 y 4: Riesgo y Control
    pdf.ln(1); pdf.set_font("Helvetica", "B", 9); pdf.cell(0, 6, " Riesgo Crítico", 0, 1)
    pdf.set_font("Helvetica", "", 9); pdf.cell(0, 7, f" {datos['riesgo_critico']}", 1, 1, 'L', fill=True)
    pdf.ln(1); pdf.set_font("Helvetica", "B", 9); pdf.cell(0, 6, " Control Crítico Fallido o Ausente", 0, 1)
    pdf.set_font("Helvetica", "", 9); pdf.cell(0, 7, f" {datos['control_fallido']}", 1, 1, 'L', fill=True)
    pdf.ln(3)

    # --- SECCIÓN 2: RELATO ---
    def seccion_bloque(titulo, contenido):
        pdf.set_fill_color(120, 120, 120); pdf.set_text_color(255, 255, 255); pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 8, f" {titulo}", 0, 1, 'L', fill=True)
        pdf.set_text_color(0, 0, 0); pdf.set_font("Helvetica", "", 9); pdf.set_fill_color(235, 235, 235)
        pdf.multi_cell(0, 6, f" {texto_seguro(contenido)}", border=1, fill=True)
        pdf.ln(2)

    seccion_bloque("¿QUÉ OCURRIÓ?", datos['que_ocurrio'])
    seccion_bloque("¿POR QUÉ OCURRIÓ?", datos['porque_ocurrio'])

    # --- SECCIÓN 3: ACCIONES INMEDIATAS ---
    pdf.set_fill_color(120, 120, 120); pdf.set_text_color(255, 255, 255); pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 8, " ACCIONES INMEDIATAS", 0, 1, 'L', fill=True)
    pdf.set_text_color(0, 0, 0); pdf.set_font("Helvetica", "", 9); pdf.set_fill_color(235, 235, 235)

    try: acciones = json.loads(datos['acciones_json'])
    except: acciones = []

    for i in range(5):
        txt = acciones[i] if i < len(acciones) else ""
        pdf.cell(8, 6, f" {i+1}", 1, 0, 'C'); pdf.cell(0, 6, f" {txt}", 1, 1, 'L', fill=True)
    pdf.ln(3)

    # --- SECCIÓN 4: FOTOGRAFÍA ---
    pdf.set_fill_color(120, 120, 120); pdf.set_text_color(255, 255, 255); pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 8, " FOTOGRAFÍA", 0, 1, 'L', fill=True)
    pdf.set_text_color(0, 0, 0); pdf.set_font("Helvetica", "I", 8)
    pdf.cell(0, 5, " Inserte una o más fotos claras del punto de falla y/o la condición subestándar que causó el incidente", 0, 1)

    y_foto = pdf.get_y()
    pdf.rect(10, y_foto, 190, 60)
    foto_path = datos.get('foto_path')
    if foto_path and os.path.exists(foto_path):
        try: pdf.image(foto_path, x=45, y=y_foto+2, h=56)
        except: pdf.set_xy(10, y_foto+25); pdf.cell(190, 10, "[Error al cargar imagen]", 0, 1, 'C')

    pdf.set_y(y_foto + 65)

    # --- SECCIÓN 5: CLASIFICACIÓN (PIE) ---
    pdf.set_fill_color(120, 120, 120); pdf.set_text_color(255, 255, 255); pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 8, " CLASIFICACIÓN DEL EVENTO", 0, 1, 'L', fill=True)
    pdf.set_text_color(0, 0, 0); pdf.set_font("Helvetica", "B", 9)
    pdf.cell(95, 10, f" Clasificación de Alerta: {datos['clasificacion_alerta']}", 1, 0, 'L')
    pdf.cell(95, 10, f" ¿Requiere investigación formal?: {datos['requiere_investigacion']}", 1, 1, 'L')

    return bytes(pdf.output())

def generar_pdf_libro_aprendizaje(df_eventos, logo_app, logo_cliente):
    pdf = ReporteCGT("Libro de Aprendizaje Institucional - HSE", logo_app, logo_cliente, orientation='P')
    pdf.alias_nb_pages()

    for i in range(0, len(df_eventos), 2):
        pdf.add_page()
        eventos_hoja = df_eventos.iloc[i : i+2]
        for idx, (_, row) in enumerate(eventos_hoja.iterrows()):
            y_i = pdf.get_y()
            pdf.set_fill_color(240, 240, 240); pdf.rect(10, y_i, 190, 120, 'F')
            pdf.set_fill_color(25, 58, 138); pdf.set_text_color(255, 255, 255); pdf.set_font("Helvetica", "B", 11)
            pdf.cell(190, 8, f" EVENTO #{row['id']} | {row['fecha']} | {row['tipo_evento']}", 0, 1, 'L', fill=True)
            pdf.set_text_color(0, 0, 0); pdf.set_font("Helvetica", "B", 9)
            pdf.cell(95, 6, f" Riesgo Crítico: {row['riesgo_critico']}", 0, 0); pdf.cell(95, 6, f" Clasificación: {row['clasificacion_alerta']}", 0, 1)
            y_relato = pdf.get_y(); pdf.set_font("Helvetica", "", 9)
            pdf.multi_cell(110, 5, f"¿QUÉ OCURRIÓ?\n{texto_seguro(row['que_ocurrio'][:350])}...", border=0)
            foto_p = row.get('foto_path')
            if foto_p and os.path.exists(foto_p):
                try: pdf.image(foto_p, x=125, y=y_relato+2, w=70, h=45)
                except: pass
            pdf.set_y(y_relato + 55); pdf.set_font("Helvetica", "B", 9); pdf.cell(0, 5, "ANÁLISIS DE CAUSAS:", 0, 1)
            pdf.set_font("Helvetica", "I", 9); pdf.multi_cell(0, 5, texto_seguro(row['porque_ocurrio'][:200]), border=0)
            pdf.ln(2); pdf.set_font("Helvetica", "B", 8); pdf.cell(0, 5, "ACCIONES CORRECTIVAS ADOPTADAS:", 0, 1)
            try: accs = json.loads(row['acciones_json'])
            except: accs = []
            for a in accs[:2]: pdf.cell(0, 4, f" - {texto_seguro(a)}", 0, 1)
            pdf.set_y(y_i + 130)

    return bytes(pdf.output())

def generar_pdf_sgi(emp_nom, kpis_auto, kpis_manual, ai_insight, logo_app, logo_cliente):
    pdf = ReporteCGT(f"Tablero de Control SGI: {emp_nom}", logo_app, logo_cliente)
    pdf.alias_nb_pages()
    pdf.add_page()

    # --- 1. RESUMEN EJECUTIVO (AI) ---
    if ai_insight:
        pdf.set_font("Helvetica", "B", 12); pdf.set_fill_color(0, 18, 25); pdf.set_text_color(255, 255, 255)
        pdf.cell(0, 10, " ANALISIS ESTRATEGICO ULL-TRONE", 0, 1, 'L', fill=True)
        pdf.set_text_color(0, 0, 0); pdf.set_font("Helvetica", "I", 9); pdf.ln(2)
        pdf.multi_cell(0, 6, ai_insight, border=1); pdf.ln(5)

    # --- 2. KPIS AUTOMATICOS (DB LIVE) ---
    pdf.set_font("Helvetica", "B", 12); pdf.set_fill_color(0, 95, 115); pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 10, " TELEMETRIA SGI (AUTOMATICA)", 0, 1, 'L', fill=True)
    pdf.set_text_color(0, 0, 0); pdf.ln(3)

    for k in kpis_auto:
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(140, 7, f" {k['kpi']}", 0, 0)
        pdf.cell(50, 7, f" {k['valor']}{k['unidad']} (Meta: {k['meta']})", 0, 1, 'R')
        
        # Barra de progreso visual
        pdf.set_fill_color(220, 220, 220); pdf.rect(pdf.get_x() + 5, pdf.get_y(), 180, 4, 'F')
        pct = min(1.0, k['valor'] / k['meta']) if k['meta'] > 0 else 1.0
        bar_color = (16, 185, 129) if pct >= 1.0 else ((245, 158, 11) if pct >= 0.8 else (239, 68, 68))
        pdf.set_fill_color(*bar_color); pdf.rect(pdf.get_x() + 5, pdf.get_y(), 180 * pct, 4, 'F')
        pdf.ln(8)

    # --- 3. KPIS MANUALES ---
    if not kpis_manual.empty:
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 12); pdf.set_fill_color(10, 147, 150); pdf.set_text_color(255, 255, 255)
        pdf.cell(0, 10, " INDICADORES DE GESTION (MANUALES)", 0, 1, 'L', fill=True)
        pdf.set_text_color(0, 0, 0); pdf.ln(3)

        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(90, 8, " Indicador", 1); pdf.cell(30, 8, " Valor", 1); pdf.cell(30, 8, " Meta", 1); pdf.cell(40, 8, " Responsable", 1); pdf.ln()
        pdf.set_font("Helvetica", "", 9)
        for _, r in kpis_manual.iterrows():
            pdf.cell(90, 8, f" {r['nombre']}", 1); pdf.cell(30, 8, f" {r['valor_actual']}", 1); pdf.cell(30, 8, f" {r['meta']}", 1); pdf.cell(40, 8, f" {r['responsable']}", 1); pdf.ln()

    return bytes(pdf.output())
