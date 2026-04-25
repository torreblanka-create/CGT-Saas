import os

from core.reports.base_pdf import ReporteBase, texto_seguro


class GeneradorPdfART(ReporteBase):
    def __init__(self, datos, logo_app, logo_cliente, db_path):
        super().__init__(
            titulo="ANÁLISIS DE RIESGOS DEL TRABAJO (ART)",
            logo_app=logo_app,
            logo_cliente=logo_cliente,
            db_path=db_path
        )
        self.datos = datos
        self.sub_titulo = "Identificación de Riesgos y Controles Críticos (CCP)"

    def header(self):
        super().header()
        if self.sub_titulo:
            self.set_y(self.get_y() - 10)
            self.set_font("Helvetica", "I", 10)
            self.cell(0, 5, texto_seguro(self.sub_titulo), align="C", ln=True)
            self.ln(6)

    def generar(self):
        self.alias_nb_pages()
        self.add_page()

        datos = self.datos
        # COLORES CORPORATIVOS
        R_C, G_C, B_C = 10, 49, 97     # Azul Corporativo
        R_G, G_G, B_G = 212, 175, 55   # Oro Corporativo
        R_L, G_L, B_L = 240, 244, 248  # Azul Claro para celdas

        # --- 1. PLANIFICACIÓN Y ANTECEDENTES ---
        self.set_font("Helvetica", "B", 10)
        self.set_fill_color(R_C, G_C, B_C); self.set_text_color(255, 255, 255)
        self.cell(0, 8, " 1. PLANIFICACIÓN Y ANTECEDENTES DEL TRABAJO", 1, 1, 'L', fill=True)
        self.set_text_color(0, 0, 0)

        h_c = 7
        self.set_font("Helvetica", "B", 8); self.set_fill_color(R_L, G_L, B_L)
        self.cell(35, h_c, " TAREA / ACTIVIDAD", 1, 0, 'L', fill=True)
        self.set_font("Helvetica", "", 8)
        self.cell(65, h_c, f" {texto_seguro(datos['tarea'])[:45]}", 1, 0, 'L')

        self.set_font("Helvetica", "B", 8); self.set_fill_color(R_L, G_L, B_L)
        self.cell(35, h_c, " LUGAR / ÁREA", 1, 0, 'L', fill=True)
        self.set_font("Helvetica", "", 8)
        self.cell(55, h_c, f" {texto_seguro(datos['area'])[:35]}", 1, 1, 'L')

        self.set_font("Helvetica", "B", 8); self.set_fill_color(R_L, G_L, B_L)
        self.cell(35, h_c, " SUPERVISOR A CARGO", 1, 0, 'L', fill=True)
        self.set_font("Helvetica", "", 8)
        self.cell(65, h_c, f" {texto_seguro(datos['supervisor'])[:40]}", 1, 0, 'L')

        self.set_font("Helvetica", "B", 8); self.set_fill_color(R_L, G_L, B_L)
        self.cell(35, h_c, " FECHA Y HORA", 1, 0, 'L', fill=True)
        self.set_font("Helvetica", "", 8)
        self.cell(55, h_c, f" {datos['fecha']} | {datos['hora']}", 1, 1, 'L')
        self.ln(5)

        # --- 2. PREGUNTAS TRANSVERSALES ---
        self.set_font("Helvetica", "B", 10); self.set_fill_color(R_C, G_C, B_C); self.set_text_color(255, 255, 255)
        self.cell(0, 8, " 2. REQUISITOS TRANSVERSALES DE SEGURIDAD", 1, 1, 'L', fill=True)

        self.set_font("Helvetica", "B", 8); self.set_fill_color(R_G, G_G, B_G); self.set_text_color(0, 0, 0)
        self.cell(95, 6, " ROL: SUPERVISOR(A)", 1, 0, 'C', fill=True)
        self.cell(95, 6, " ROL: TRABAJADOR(A)", 1, 1, 'C', fill=True)

        q_sup = [
            f"¿Cuenta con estándar/procedimiento/instructivo? ({datos['transversales']['nombres_proc']['Supervisor'][:15]})",
            "¿Personal cuenta con capacitaciones, salud e idoneidad?",
            "¿Se tramitaron permisos (trabajos en caliente, energías, etc)?",
            "¿Verificó segregación, delimitación y señalización del área?",
            "¿Personal cuenta con sistema de comunicación de emergencia?",
            "¿Personal dispone de todos los EPP definidos en buen estado?"
        ]
        q_trab = [
            f"¿Conozco el estándar/procedimiento/instructivo? ({datos['transversales']['nombres_proc']['Trabajador'][:15]})",
            "¿Cuento con competencias, acreditaciones y salud compatible?",
            "¿Cuento con la autorización respectiva para ingresar al área?",
            "¿Segregué y señalicé mi área de trabajo según el estándar?",
            "¿Conozco los teléfonos y protocolos de emergencia?",
            "¿Uso de manera correcta los EPP definidos para la tarea?"
        ]

        self.set_font("Helvetica", "", 6)
        for i in range(6):
            startX = self.get_x()
            startY = self.get_y()
            self.multi_cell(85, 4, f" {q_sup[i]}", border=1, align='L')
            endY_s = self.get_y()
            self.set_xy(startX + 85, startY)
            self.cell(10, endY_s - startY, " SI " if datos['transversales']['Supervisor'][i] else " NO ", 1, 0, 'C')

            self.set_xy(startX + 95, startY)
            self.multi_cell(85, 4, f" {q_trab[i]}", border=1, align='L')
            endY_t = self.get_y()

            max_y = max(endY_s, endY_t)
            self.set_xy(startX + 180, startY)
            self.cell(10, max_y - startY, " SI " if datos['transversales']['Trabajador'][i] else " NO ", 1, 0, 'C')
            self.set_y(max_y)

        self.ln(5)

        # --- 3. RIESGOS CRÍTICOS (CCP GRID) ---
        self.set_font("Helvetica", "B", 10); self.set_fill_color(R_C, G_C, B_C); self.set_text_color(255, 255, 255)
        self.cell(0, 8, " 3. RIESGOS DE FATALIDAD Y VERIFICACIÓN DE CONTROLES CRÍTICOS (CCP)", 1, 1, 'L', fill=True)
        self.set_font("Helvetica", "I", 7)
        self.cell(0, 5, " Valide la implementación efectiva de los Controles Críticos (CCP) para las actividades de alto riesgo involucradas.", 1, 1, 'C', fill=True)
        self.set_text_color(0, 0, 0)

        margen_izq = 10
        w_col = 190 / 6
        riesgos_activos = list(datos['controles'].keys())

        for bloque in [("SUPERVISOR(A)", "Supervisor"), ("PERSONA TRABAJADORA", "Trabajador")]:
            rol_titulo, dict_key = bloque
            if self.get_y() > 220: self.add_page()

            self.set_font("Helvetica", "B", 8); self.set_fill_color(180, 180, 180)
            self.cell(190, 6, f" {rol_titulo}", 1, 1, 'L', fill=True)

            cur_y_rol = self.get_y()
            for i in range(6):
                x_box = margen_izq + (i * w_col)
                self.set_xy(x_box, cur_y_rol)

                riesgo_nom = riesgos_activos[i] if i < len(riesgos_activos) else ""
                self.set_font("Helvetica", "B", 7)
                self.rect(x_box, cur_y_rol, w_col, 10)
                self.multi_cell(w_col, 3.5, f" {riesgo_nom}", border=0, align='L')

                self.set_xy(x_box, cur_y_rol + 10)
                self.set_fill_color(240, 240, 240)
                self.set_font("Helvetica", "B", 5)
                w_cod = w_col * 0.35
                w_res = (w_col - w_cod) / 3
                self.cell(w_cod, 4, " Cód", 1, 0, 'C', fill=True)
                self.cell(w_res, 4, " SI", 1, 0, 'C', fill=True)
                self.cell(w_res, 4, " NO", 1, 0, 'C', fill=True)
                self.cell(w_res, 4, " N/A", 1, 0, 'C', fill=True)

                self.set_font("Helvetica", "", 6)
                for j in range(8):
                    self.set_xy(x_box, cur_y_rol + 14 + (j * 4.5))
                    ctrl_val = ""
                    if riesgo_nom and dict_key in datos['controles'][riesgo_nom]:
                        ctrl_list = list(datos['controles'][riesgo_nom][dict_key].items())
                        if j < len(ctrl_list):
                            _, val = ctrl_list[j]
                            ctrl_val = val

                    self.cell(w_cod, 4.5, f" CCP{j+1}", 1, 0, 'C')
                    self.cell(w_res, 4.5, " X " if ctrl_val == "SI" else "", 1, 0, 'C')
                    self.cell(w_res, 4.5, " X " if ctrl_val == "NO" else "", 1, 0, 'C')
                    self.cell(w_res, 4.5, " X " if ctrl_val == "N/A" else "", 1, 0, 'C')

            self.set_y(cur_y_rol + 50)
            self.ln(3)

        self.ln(2)

        # --- 4. OTROS RIESGOS ---
        if self.get_y() > 240: self.add_page()
        self.set_font("Helvetica", "B", 10); self.set_fill_color(R_C, G_C, B_C); self.set_text_color(255, 255, 255)
        self.cell(0, 8, " 4. OTROS RIESGOS (ENTORNO Y OPERATIVOS)", 1, 1, 'L', fill=True)

        self.set_font("Helvetica", "B", 8); self.set_fill_color(220, 220, 220); self.set_text_color(0, 0, 0)
        self.cell(70, 6, " FACTOR DE RIESGO / PELIGRO", 1, 0, 'L', fill=True)
        self.cell(120, 6, " MEDIDA PREVENTIVA / DE CONTROL", 1, 1, 'L', fill=True)

        self.set_font("Helvetica", "", 7)
        for r in datos.get('otros_riesgos', []):
            riesgo_txt = texto_seguro(r['riesgo'])
            medida_txt = texto_seguro(r['medida'])

            lineas_r = self.multi_cell(68, 4, f" {riesgo_txt}", split_only=True)
            lineas_m = self.multi_cell(118, 4, f" {medida_txt}", split_only=True)
            h_row = max(len(lineas_r), len(lineas_m), 1) * 4 + 4

            if self.get_y() + h_row > 270: self.add_page()
            cur_y = self.get_y()

            self.set_xy(10, cur_y)
            self.rect(10, cur_y, 70, h_row)
            self.multi_cell(70, 4, f" {riesgo_txt}", border=0, align='L')

            self.set_xy(80, cur_y)
            self.rect(80, cur_y, 120, h_row)
            self.multi_cell(120, 4, f" {medida_txt}", border=0, align='L')
            self.set_y(cur_y + h_row)

        if not datos.get('otros_riesgos'):
            for _ in range(2):
                self.cell(70, 6, "", 1)
                self.cell(120, 6, "", 1, 1)
        self.ln(5)

        # --- 5. TRABAJOS EN SIMULTÁNEO ---
        if self.get_y() > 250: self.add_page()
        self.set_font("Helvetica", "B", 10); self.set_fill_color(R_C, G_C, B_C); self.set_text_color(255, 255, 255)
        self.cell(0, 8, " 5. INTERFERENCIAS / TRABAJOS EN SIMULTÁNEO", 1, 1, 'L', fill=True)

        self.set_font("Helvetica", "B", 6); self.set_fill_color(220, 220, 220); self.set_text_color(0, 0, 0)
        w_sim = [28, 70, 30, 30, 32]
        y_header = self.get_y()

        self.set_xy(10, y_header)
        self.multi_cell(w_sim[0], 3.3, "¿Existen trabajos en el radio de influencia?", 1, 'C', fill=True)
        self.set_xy(10 + w_sim[0], y_header)
        self.multi_cell(w_sim[1], 3.3, "Contexto de la interferencia y trabajos cruzados:", 1, 'C', fill=True)
        self.set_xy(10 + w_sim[0] + w_sim[1], y_header)
        self.multi_cell(w_sim[2], 2.5, "¿Se realizó la coordinación operativa cruzada (líderes)?", 1, 'C', fill=True)
        self.set_xy(10 + sum(w_sim[:3]), y_header)
        self.multi_cell(w_sim[3], 3.3, "¿Verificación de Controles Críticos compartidos?", 1, 'C', fill=True)
        self.set_xy(10 + sum(w_sim[:4]), y_header)
        self.multi_cell(w_sim[4], 2.5, "¿La cuadrilla fue comunicada sobre esta interferencia?", 1, 'C', fill=True)

        # Calculate header height dynamically
        max_h = 0
        for txt, w in [("¿Existen trabajos en el radio de influencia?", w_sim[0]),
                       ("Contexto de la interferencia y trabajos cruzados:", w_sim[1]),
                       ("¿Se realizó la coordinación operativa cruzada (líderes)?", w_sim[2]),
                       ("¿Verificación de Controles Críticos compartidos?", w_sim[3]),
                       ("¿La cuadrilla fue comunicada sobre esta interferencia?", w_sim[4])]:
            lines = self.multi_cell(w, 3.3, txt, split_only=True)
            max_h = max(max_h, len(lines) * 3.3)
        max_h = max(max_h, 10)

        self.set_y(y_header + max_h)

        existe = datos['simultaneo']['existe']
        det = datos['simultaneo']['detalles']

        h_sim = 16
        row_y = self.get_y()

        # Col 1 – Existe (SI/NO split)
        self.set_font("Helvetica", "B", 8)
        self.rect(10, row_y, w_sim[0], h_sim)
        self.set_xy(10, row_y)
        self.cell(w_sim[0]/2, h_sim, "SI" if existe == "SI" else "", 1, 0, 'C')
        self.cell(w_sim[0]/2, h_sim, "NO" if existe == "NO" else "", 1, 0, 'C')

        # Col 2 – Contexto (multi_cell inside rect)
        x_ctx = 10 + w_sim[0]
        ctx_txt = texto_seguro(det.get('contexto', ''))
        self.set_font("Helvetica", "", 7)
        self.rect(x_ctx, row_y, w_sim[1], h_sim)
        self.set_xy(x_ctx + 1, row_y + 1)
        self.multi_cell(w_sim[1] - 2, 4, ctx_txt[:120], border=0, align='L')

        # Cols 3-5 – coordinacion / verificacion / comunicacion
        self.set_font("Helvetica", "B", 8)
        x_extra = x_ctx + w_sim[1]
        for q, w_cur in [('coordinacion', w_sim[2]), ('verificacion', w_sim[3]), ('comunicación', w_sim[4])]:
            self.set_xy(x_extra, row_y)
            self.cell(w_cur/2, h_sim, "SI" if det.get(q) == "SI" else "", 1, 0, 'C')
            self.cell(w_cur/2, h_sim, "NO" if det.get(q) == "NO" else "", 1, 0, 'C')
            x_extra += w_cur

        self.set_y(row_y + h_sim)
        self.ln(5)

        # --- 6. EQUIPO EJECUTOR ---
        if self.get_y() > 240: self.add_page()
        self.set_font("Helvetica", "B", 10); self.set_fill_color(R_C, G_C, B_C); self.set_text_color(255, 255, 255)
        self.cell(0, 8, " 6. EQUIPO EJECUTOR (TOMA DE CONOCIMIENTO)", 1, 1, 'L', fill=True)

        self.set_font("Helvetica", "B", 9); self.set_fill_color(R_L, G_L, B_L); self.set_text_color(0, 0, 0)
        self.cell(100, 8, " NOMBRE Y APELLIDO (PARTICIPANTES)", 1, 0, 'L', fill=True)
        self.cell(90, 8, " FIRMA INDIVIDUAL", 1, 1, 'C', fill=True)

        self.set_font("Helvetica", "B", 8)
        self.cell(100, 10, f" {texto_seguro(datos['ejecutor'])} (LÍDER/RESPONSABLE)", 1, 0, 'L')
        self.cell(90, 10, " ", 1, 1, 'C')

        self.set_font("Helvetica", "", 8)
        for t in datos['equipo']:
            if self.get_y() > 270: self.add_page()
            # Clean display: remove the verbose profile parenthetical, keep only ID - Nombre
            nombre_limpio = texto_seguro(t)
            if '(' in nombre_limpio:
                nombre_limpio = nombre_limpio[:nombre_limpio.index('(')].strip()
            self.cell(100, 8, f" {nombre_limpio}", 1, 0, 'L')
            self.cell(90, 8, " ", 1, 1, 'C')

        self.ln(8)
        self.set_font("Helvetica", "B", 9); self.set_text_color(200, 0, 0)
        self.multi_cell(0, 7, texto_seguro("🔴 SI EXISTE UN 'NO' EN LA VERIFICACIÓN DE CONTROLES CRÍTICOS (CCP), NO SE DEBE INICIAR LA TAREA.\\nLEVANTE TARJETA DE DETENCIÓN Y COMUNÍQUESE DE INMEDIATO CON SU SUPERVISION."), border=1, align='C')

        return bytes(self.output())
