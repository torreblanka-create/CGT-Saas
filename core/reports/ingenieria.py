import logging
import os
import tempfile
from datetime import datetime

from .base import ReporteCGT, texto_seguro, truncar


def generar_pdf_rigging_plan(d, logo_app, logo_cliente):
    """Genera un Rigging Plan blindado contra errores de datos y fallos de IO."""
    try:
        pdf = ReporteCGT(
            "RIGGING PLAN - INGENIERÍA DE IZAJE",
            logo_app,
            logo_cliente,
            sub_titulo="Calculadora de Ingeniería Rigger 360"
        )
        pdf.alias_nb_pages()
        pdf.add_page()

        # 1. INFORMACIÓN GENERAL (Uso de .get() con defaults)
        p_neto = d.get('p_neto_total', 0)
        es_tandem = d.get('es_tandem', False)
        viento = d.get('viento', 0)

        pdf.set_font("Helvetica", "B", 11)
        pdf.set_fill_color(0, 209, 255) # Electric Cyan
        pdf.set_text_color(0, 0, 0)
        pdf.cell(0, 8, " 1. INFORMACIÓN GENERAL", fill=True, ln=True)
        pdf.set_font("Helvetica", "", 10)

        pdf.cell(95, 8, f" Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}", 1)
        pdf.cell(95, 8, f" Tipo: {'TÁNDEM (Dual)' if es_tandem else 'SIMPLE'}", 1, 1)
        pdf.cell(95, 8, f" Empresa: {texto_seguro(d.get('empresa', 'CGT'))}", 1)
        pdf.cell(95, 8, f" Carga: {p_neto:,} Kg | Viento: {viento} Km/h", 1, 1)
        pdf.ln(5)

        # 2. ANÁLISIS DE CAPACIDAD Y RIGGING
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_fill_color(0, 209, 255)
        pdf.cell(0, 8, " 2. ANÁLISIS DE CAPACIDAD Y RIGGING", fill=True, ln=True)

        equipos = [d.get('grua_a', {})]
        if es_tandem and d.get('grua_b'):
            equipos.append(d.get('grua_b', {}))

        for i, eq in enumerate(equipos):
            if not eq: continue

            # Pre-extracción de datos con validación
            bruta = eq.get('bruta', 0)
            util = eq.get('utilizacion', 0)
            tension = eq.get('tension', 0)
            cap_efectiva = eq.get('cap_efectiva', 1) or 1 # Evitar div por cero

            pdf.set_font("Helvetica", "B", 10)
            pdf.set_fill_color(220, 220, 220)
            pdf.cell(0, 7, f" EQUIPO {'A' if i==0 else 'B'}: {eq.get('id', 'N/A')}", 1, 1, fill=True)

            # Encabezados de Tabla de Auditoría (Cabecera Negra)
            pdf.set_font("Helvetica", "B", 8)
            pdf.set_fill_color(0, 0, 0); pdf.set_text_color(255, 255, 255)
            pdf.cell(95, 6, " DATO DE CAMPO (NOMINAL)", 1, 0, 'C', fill=True)
            pdf.cell(95, 6, " AUDITORÍA MATEMÁTICA", 1, 1, 'C', fill=True)
            pdf.set_text_color(0, 0, 0); pdf.set_font("Helvetica", "", 7.5)

            # Fila 1: Carga Proporcional
            pdf.cell(95, 6, f" Carga Proporcional: {bruta:,.0f} Kg", 1, 0)
            form_carga = f"({p_neto}*{eq.get('dist_p',0):.0f}%) + {eq.get('rigging',0)}kg"
            pdf.cell(95, 6, f" Verif: {form_carga} = {bruta:,.0f} Kg", 1, 1)

            # Fila 2: Capacidad y Viento
            pdf.cell(95, 6, f" Cap. Tabla: {eq.get('capacidad',0):.0f} Kg | Radio: {eq.get('radio',0)} m", 1, 0)
            v_red = eq.get('red_viento', 0)
            form_cap = f"Cap.Nom - Viento({v_red:.0f}kg)"
            pdf.cell(95, 6, f" Verif: {form_cap} = {eq.get('capacidad',0) - v_red:.0f} Kg", 1, 1)

            # Fila 3: Seguridad del Equipo (Utilización)
            fill_c = (16, 185, 129) if util < 75 else (245, 158, 11) if util < 90 else (239, 68, 68)
            pdf.set_fill_color(*fill_c); pdf.set_text_color(255, 255, 255); pdf.set_font("Helvetica", "B", 8)
            pdf.cell(95, 7, f" UTILIZACIÓN EQUIPO: {util:.1f}%", 1, 0, 'C', fill=True)
            f_tandem = eq.get('factor_tandem', 1.0)
            form_util = f"({bruta:.0f}kg * {f_tandem})/Cap.Neta({cap_efectiva:.0f})"
            pdf.cell(95, 7, f" {form_util}", 1, 1, 'C', fill=True)

            # Fila 4: Análisis de Rigging
            pdf.set_text_color(0, 0, 0); pdf.set_font("Helvetica", "", 7)
            pdf.set_fill_color(245, 245, 245)
            pdf.cell(95, 6, f" Modo:{eq.get('tipo_amarre','?')}|Ang:{eq.get('angulo',0)}\xb0|Ram:{eq.get('ramales',1)}", 1, 0, 'L', fill=True)
            pdf.cell(95, 6, f" Cap.Sistema: WLL*FM*Ram_Efect = {eq.get('cap_real_wll', 0)*eq.get('ramales',1):.0f} Kg", 1, 1, 'L', fill=True)

            # Fila 5: Tensión Máxima
            util_r = eq.get('util_rigging', 0)
            fill_r = (16, 185, 129) if util_r < 75 else (245, 158, 11) if util_r < 90 else (239, 68, 68)
            pdf.cell(95, 6, f" Tensión Máx/Ramal: {tension:,.0f} Kg", 1, 0)
            f_ang = eq.get('factor_angulo', 1.0)
            ram_calc = min(eq.get('ramales',1), 3)
            form_tens = f"Verif: (Bruta * {f_ang}) / {ram_calc} Ram."
            pdf.cell(95, 6, f" {form_tens} = {tension:,.0f} Kg", 1, 1)

            pdf.set_fill_color(*fill_r); pdf.set_text_color(255, 255, 255); pdf.set_font("Helvetica", "B", 8)
            pdf.cell(0, 7, f" UTILIZACIÓN RIGGING: {util_r:.1f}%", 1, 1, 'C', fill=True)
            pdf.set_text_color(0, 0, 0); pdf.ln(1)

        # 3. GRÁFICOS MATEMÁTICOS (LMI & ESQUEMA)
        pdf.ln(5)
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_fill_color(0, 209, 255); pdf.set_text_color(0, 0, 0)
        pdf.cell(0, 8, " 3. GRÁFICOS DE INGENIERÍA", fill=True, ln=True)
        pdf.ln(2)

        y_img = pdf.get_y()
        x_img = 15

        # Importar dinámicamente los dibujadores
        from core.visuals_izaje import draw_lmi_chart, draw_rigging_diagram

        # DIBUJAR ESQUEMA
        try:
            d1 = d.get('d1', 1.0)
            d2 = d.get('d2', 1.0)
            cg_asim = d.get('cg_asim', False)
            ang_a = equipos[0].get('angulo', 60) if equipos else 60

            diag_bytes = draw_rigging_diagram(d1, d2, angulo=ang_a, asimetrico=cg_asim)
            with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp_rig:
                tmp_rig.write(diag_bytes)
                tmp_rig_path = tmp_rig.name
            pdf.image(tmp_rig_path, x=x_img, y=y_img, w=85)
            os.unlink(tmp_rig_path)
            x_img += 90
        except Exception as e:
            logging.error(f"Error Rigging Diagram PDF: {e}")

        # DIBUJAR LMI CHART
        if equipos[0].get('lmi_radios'):
            try:
                eq = equipos[0]
                lmi_bytes = draw_lmi_chart(eq['lmi_radios'], eq['lmi_caps'], eq['radio'], eq['bruta'])
                if lmi_bytes:
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp_lmi:
                        tmp_lmi.write(lmi_bytes)
                        tmp_lmi_path = tmp_lmi.name
                    pdf.image(tmp_lmi_path, x=x_img, y=y_img, w=85)
                    os.unlink(tmp_lmi_path)
            except Exception as e:
                logging.error(f"Error LMI Chart PDF: {e}")

        pdf.set_y(y_img + 65) # Espacio para las imágenes (Altura 60 + Margen 5)

        # 4. EVIDENCIAS
        pdf.ln(2)
        y_footer = pdf.get_y()

        pdf.set_font("Helvetica", "B", 8)
        pdf.set_xy(10, y_footer)
        pdf.set_fill_color(0, 209, 255); pdf.set_text_color(0, 0, 0)
        pdf.cell(90, 6, " 4. EVIDENCIA FOTOGRÁFICA", fill=True, ln=True)

        y_photos = pdf.get_y() + 2
        x_img = 10
        all_photos = []
        for eq in equipos:
            paths = eq.get('path_foto', [])
            if isinstance(paths, str): paths = [paths]
            all_photos.extend([p for p in paths if p])

        for p in all_photos[:2]:
            if os.path.exists(p):
                try:
                    pdf.image(p, x=x_img, y=y_photos, w=40, h=35)
                    x_img += 45
                except Exception as e:
                    logging.error(f"Error cargando imagen PDF: {e}")
                    pdf.rect(x_img, y_photos, 40, 35)
                    pdf.set_xy(x_img, y_photos + 15)
                    pdf.set_font("Helvetica", "I", 6)
                    pdf.cell(40, 5, "Imagen Corrupta / Formato No Soportado", 0, 0, 'C')
                    x_img += 45

        # Aprobaciones
        pdf.set_xy(110, y_footer)
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_fill_color(0, 209, 255); pdf.set_text_color(0, 0, 0)
        pdf.cell(90, 6, " 5. APROBACIONES", fill=True, ln=True)

        y_sig = pdf.get_y() + 2
        pdf.set_font("Helvetica", "B", 7)
        pdf.set_xy(110, y_sig)
        pdf.cell(20, 5, "Cargo", 1, 0, 'C')
        pdf.cell(35, 5, "Nombre", 1, 0, 'C')
        pdf.cell(35, 5, "Firma", 1, 1, 'C')

        firmas = ["Rigger", "Operador", "Supervisor"]
        pdf.set_font("Helvetica", "", 7)
        for cargo in firmas:
            pdf.set_x(110)
            pdf.cell(20, 12, cargo, 1, 0, 'C')
            pdf.cell(35, 12, "", 1, 0, 'C')
            pdf.cell(35, 12, "", 1, 1, 'C')

        # 4. PROTOCOLO CRÍTICO Y NOTAS
        y_final = max(y_photos + 42, pdf.get_y() + 2)
        pdf.set_y(y_final)

        util_e_max = max([eq.get('utilizacion',0) for eq in equipos])
        util_r_max = max([eq.get('util_rigging',0) for eq in equipos])
        v_actual = d.get('viento', 0)

        if util_e_max > 80 or util_r_max > 80 or v_actual >= 30:
            pdf.set_font("Helvetica", "B", 8)
            pdf.set_fill_color(220, 0, 0); pdf.set_text_color(255, 255, 255)
            pdf.cell(0, 6, " (!) IZAJE NO AUTORIZADO: Se excede el límite de seguridad permitido (>80%).", 1, 1, 'C', fill=True)
            pdf.set_text_color(0, 0, 0)
        elif util_e_max > 75 or util_r_max > 75 or v_actual > 20:
            pdf.set_font("Helvetica", "B", 8)
            pdf.set_fill_color(255, 235, 235); pdf.set_text_color(200, 0, 0)
            pdf.cell(0, 6, " (!) PROTOCOLO CRÍTICO (75-80%): El Supervisor NO puede retirarse de la maniobra.", 1, 1, 'C', fill=True)
            pdf.set_text_color(0, 0, 0)

        pdf.set_font("Helvetica", "I", 7)
        pdf.set_text_color(100, 100, 100)
        pdf.multi_cell(0, 3.5, "NOTAS TÉCNICAS: Cálculos ASME B30.9. Configuración de 4 ramales se calcula sobre 3. Prohibido: Viento > 30 Km/h | Ángulo < 30°.")

        return bytes(pdf.output())
    except Exception as fatal_e:
        logging.critical(f"Falla total en generación de Rigging Plan: {fatal_e}")
        raise # El sistema debe manejar la excepción en la capa superior
