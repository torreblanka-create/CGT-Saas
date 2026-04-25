from datetime import datetime

import pandas as pd

from .base import ReporteCGT, texto_seguro, truncar


def generar_pdf_bloqueados(df_rojos, logo_cgt, logo_cliente):
    pdf = ReporteCGT("REPORTE EJECUTIVO DE BLOQUEOS", logo_cgt, logo_cliente)
    pdf.alias_nb_pages()
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 11)
    if df_rojos.empty:
        pdf.set_fill_color(220, 255, 220)
        pdf.set_text_color(0, 100, 0)
        pdf.cell(0, 10, " ESTADO EXCELENTE: 0 Activos o Personal bloqueado.", border=1, fill=True, align="C", ln=True)
        return bytes(pdf.output())

    pdf.set_fill_color(255, 220, 220)
    pdf.set_text_color(150, 0, 0)
    pdf.cell(0, 10, texto_seguro(f" ALERTA CRÍTICA: {len(df_rojos)} bloqueos operativos detectados."), border=1, fill=True, align="C", ln=True)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(5)

    for empresa, df_emp in df_rojos.groupby('Empresa'):
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_fill_color(25, 58, 138)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(0, 8, texto_seguro(f" EMPRESA: {empresa.upper()} ({len(df_emp)} Bloqueos)"), fill=True, ln=True)

        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(0, 0, 0)
        pdf.set_fill_color(230, 230, 230)
        pdf.cell(35, 7, "ID / Patente", border=1, fill=True)
        pdf.cell(65, 7, "Nombre / Modelo", border=1, fill=True)
        pdf.cell(90, 7, "Motivo del Bloqueo (Alerta)", border=1, fill=True, ln=True)

        pdf.set_font("Helvetica", "", 8)
        for _, row in df_emp.iterrows():
            pdf.cell(35, 7, truncar(row['ID_Patente'], 20), border=1)
            pdf.cell(65, 7, truncar(row['Nombre'], 35), border=1)
            pdf.set_text_color(200, 0, 0)
            pdf.cell(90, 7, truncar(f"{row['Doc_Critico']} ({row['Alerta']})", 50), border=1, ln=True)
            pdf.set_text_color(0, 0, 0)
        pdf.ln(8)

    return bytes(pdf.output())

def generar_pdf_verdes(df_verdes, logo_cgt, logo_cliente):
    pdf = ReporteCGT("REPORTE DE ACTIVOS OPERATIVOS", logo_cgt, logo_cliente)
    pdf.alias_nb_pages()
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 11)
    if df_verdes.empty:
        pdf.set_fill_color(255, 220, 220); pdf.set_text_color(150, 0, 0)
        pdf.cell(0, 10, " ALERTA: No se registran activos operativos.", border=1, fill=True, align="C", ln=True)
        return bytes(pdf.output())

    pdf.set_fill_color(220, 255, 220); pdf.set_text_color(0, 100, 0)
    pdf.cell(0, 10, texto_seguro(f" ESTADO ÓPTIMO: {len(df_verdes)} activos 100% operativos."), border=1, fill=True, align="C", ln=True)
    pdf.set_text_color(0, 0, 0); pdf.ln(5)

    for empresa, df_emp in df_verdes.groupby('Empresa'):
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_fill_color(25, 58, 138); pdf.set_text_color(255, 255, 255)
        pdf.cell(0, 8, texto_seguro(f" EMPRESA: {empresa.upper()} ({len(df_emp)} Operativos)"), fill=True, ln=True)

        pdf.set_font("Helvetica", "B", 9); pdf.set_text_color(0, 0, 0); pdf.set_fill_color(230, 230, 230)
        pdf.cell(35, 7, "ID / Patente", border=1, fill=True)
        pdf.cell(75, 7, "Nombre / Modelo", border=1, fill=True)
        pdf.cell(80, 7, "Categoría", border=1, fill=True, ln=True)

        pdf.set_font("Helvetica", "", 8)
        for _, row in df_emp.iterrows():
            pdf.cell(35, 7, truncar(row['ID_Patente'], 20), border=1)
            pdf.cell(75, 7, truncar(row['Nombre'], 40), border=1)
            pdf.set_text_color(0, 128, 0)
            pdf.cell(80, 7, truncar(row['Categoria'], 40), border=1, ln=True)
            pdf.set_text_color(0, 0, 0)
        pdf.ln(8)

    return bytes(pdf.output())

def generar_pdf_fallas(df_fallas, logo_cgt, logo_cliente):
    pdf = ReporteCGT("HISTORIAL DE FALLAS EN TERRENO", logo_cgt, logo_cliente)
    pdf.alias_nb_pages(); pdf.add_page()

    if df_fallas.empty:
        pdf.set_font("Helvetica", "B", 11); pdf.set_fill_color(220, 255, 220); pdf.set_text_color(0, 100, 0)
        pdf.cell(0, 10, " Excelente: No hay registro de fallas en los equipos.", border=1, fill=True, align="C", ln=True)
        return bytes(pdf.output())

    for empresa, df_emp in df_fallas.groupby('empresa'):
        pdf.set_font("Helvetica", "B", 12); pdf.set_fill_color(25, 58, 138); pdf.set_text_color(255, 255, 255)
        pdf.cell(0, 8, texto_seguro(f" EMPRESA: {empresa.upper()}"), fill=True, ln=True)

        pdf.set_font("Helvetica", "B", 9); pdf.set_text_color(0, 0, 0); pdf.set_fill_color(230, 230, 230)
        pdf.cell(35, 7, "Patente", border=1, fill=True)
        pdf.cell(45, 7, "Equipo", border=1, fill=True)
        pdf.cell(85, 7, "Detalle Novedad", border=1, fill=True)
        pdf.cell(25, 7, "Estado", border=1, fill=True, align="C", ln=True)

        pdf.set_font("Helvetica", "", 8)
        for _, row in df_emp.iterrows():
            estado = "RESUELTA" if row['estado_obs'] == 'Resuelta' else "ACTIVA"
            pdf.cell(35, 7, truncar(row['identificador'], 18), border=1)
            pdf.cell(45, 7, truncar(row['nombre'], 25), border=1)
            pdf.cell(85, 7, truncar(row['detalle_observacion'], 45), border=1)
            pdf.set_text_color(0, 128, 0) if estado == "RESUELTA" else pdf.set_text_color(200, 0, 0)
            pdf.cell(25, 7, estado, border=1, align="C", ln=True); pdf.set_text_color(0, 0, 0)
        pdf.ln(8)

    return bytes(pdf.output())

def generar_pdf_historico_fallas(df_historial, logo_cgt, logo_cliente):
    pdf = ReporteCGT("REGISTRO HISTÓRICO DE FALLAS Y RESOLUCIONES", logo_cgt, logo_cliente, orientation='L')
    pdf.alias_nb_pages(); pdf.add_page()

    if df_historial.empty:
        pdf.set_font("Helvetica", "B", 11); pdf.set_fill_color(220, 255, 220); pdf.set_text_color(0, 100, 0)
        pdf.cell(0, 10, " Excelente: No existen fallas ni bloqueos registrados en el historial.", border=1, fill=True, align="C", ln=True)
        return bytes(pdf.output())

    pdf.set_font("Helvetica", "B", 8); pdf.set_fill_color(25, 58, 138); pdf.set_text_color(255, 255, 255)
    w_fecha, w_eq, w_falla, w_res, w_rep = 25, 40, 75, 100, 37
    pdf.cell(w_fecha, 8, " Fecha", 1, 0, fill=True); pdf.cell(w_eq, 8, " Equipo (ID)", 1, 0, fill=True); pdf.cell(w_falla, 8, " Falla Reportada", 1, 0, fill=True); pdf.cell(w_res, 8, " Estado y Resolución (OT)", 1, 0, fill=True); pdf.cell(w_rep, 8, " Reportado Por", 1, 1, fill=True)

    pdf.set_font("Helvetica", "", 7); pdf.set_text_color(0, 0, 0)
    for _, row in df_historial.iterrows():
        fecha = str(row['fecha'])[:10] if pd.notna(row.get('fecha')) else ""
        equipo = f"{row.get('identificador','')} - {str(row.get('nombre',''))[:15]}"
        falla = str(row.get('descripcion',''))
        reportado = str(row.get('reportado_por',''))
        estado = row.get('estado', 'Desconocido'); det_res = str(row.get('detalle_resolucion', '')); fecha_res = str(row.get('fecha_resolucion', ''))[:10]

        texto_resolucion = f"[RESUELTO el {fecha_res}] OT/Detalle: {det_res}" if estado == 'Resuelto' else "[PENDIENTE DE RESOLUCIÓN]"
        pdf.cell(w_fecha, 8, f" {truncar(fecha, 12)}", 1); pdf.cell(w_eq, 8, f" {truncar(equipo, 25)}", 1); pdf.cell(w_falla, 8, f" {truncar(falla, 60)}", 1)
        pdf.set_text_color(0, 100, 0) if estado == 'Resuelto' else pdf.set_text_color(200, 0, 0)
        pdf.cell(w_res, 8, f" {truncar(texto_resolucion, 85)}", 1); pdf.set_text_color(0, 0, 0); pdf.cell(w_rep, 8, f" {truncar(reportado, 20)}", 1, 1)

    return bytes(pdf.output())

def generar_pdf_completo(df_registros, df_resumen, logo_cgt, logo_cliente, dict_horometros):
    pdf = ReporteCGT("REPORTE DETALLADO DE GESTIÓN (AUDITORÍA)", logo_cgt, logo_cliente)
    pdf.alias_nb_pages(); hoy = pd.to_datetime(datetime.now().date())
    df_resumen['sort'] = df_resumen['Estado'].map({"ROJO": 0, "AMARILLO": 1, "VERDE": 2}); df_resumen = df_resumen.sort_values('sort')

    for _, asset in df_resumen.iterrows():
        pdf.add_page(); pdf.set_font("Helvetica", "B", 12)
        color = (200, 0, 0) if asset['Estado'] == "ROJO" else (180, 100, 0) if asset['Estado'] == "AMARILLO" else (0, 128, 0)
        pdf.set_text_color(*color); pdf.cell(0, 10, texto_seguro(f"ESTADO GENERAL: {asset['Estado']} - {asset['Nombre']} ({asset['ID_Patente']})"), ln=True)
        pdf.set_text_color(0, 0, 0); pdf.set_font("Helvetica", "I", 10)
        pdf.cell(0, 6, texto_seguro(f"Empresa: {asset['Empresa']} | Categoría: {asset['Categoria']} | Cargo/Detalle: {asset['Detalle']}"), ln=True); pdf.ln(5)

        pdf.set_font("Helvetica", "B", 9); pdf.set_fill_color(25, 58, 138); pdf.set_text_color(255, 255, 255)
        pdf.cell(80, 7, " Control / Documento", 1, 0, fill=True); pdf.cell(45, 7, " Vencimiento / Meta", 1, 0, fill=True); pdf.cell(65, 7, " Estado Específico", 1, 1, fill=True)

        pdf.set_font("Helvetica", "", 8); pdf.set_text_color(0, 0, 0)
        docs_activo = df_registros[(df_registros['identificador'] == asset['ID_Patente']) & (df_registros['nombre'] == asset['Nombre'])]
        for _, doc in docs_activo.iterrows():
            venc_label, est_doc, info_doc = "N/A", "VERDE", "Vigente / Operativo"
            if doc['tipo_control'] in ['Horas', 'Kilometros']:
                uso = dict_horometros.get(asset['ID_Patente'], 0); restantes = doc['meta_horometro'] - uso; venc_label = f"{doc['meta_horometro']} {'hrs' if doc['tipo_control'] == 'Horas' else 'km'}"
                if restantes <= 0: est_doc, info_doc = "ROJO", f"Vencido por {abs(restantes)}"
                elif restantes <= (50 if doc['tipo_control'] == 'Horas' else 1000): est_doc, info_doc = "AMARILLO", f"Próximo ({restantes})"
            else:
                if pd.notnull(doc['fecha_vencimiento']):
                    venc_label = doc['fecha_vencimiento'].strftime('%Y-%m-%d'); dias = (doc['fecha_vencimiento'] - hoy).days
                    if dias <= 0: est_doc, info_doc = "ROJO", f"Vencido hace {abs(dias)} d"
                    elif dias <= 30: est_doc, info_doc = "AMARILLO", f"Vence en {dias} d"

            if doc['tiene_observacion'] == 'Sí' and doc['estado_obs'] == 'Pendiente': est_doc, info_doc = "ROJO", f"OBS: {truncar(doc['detalle_observacion'], 30)}"
            pdf.cell(80, 7, f" {truncar(doc['tipo_doc'], 45)}", 1)
            pdf.cell(45, 7, f" {venc_label}", 1)
            txt_color = (200, 0, 0) if est_doc == "ROJO" else (180, 100, 0) if est_doc == "AMARILLO" else (0, 128, 0)
            pdf.set_text_color(*txt_color); pdf.cell(65, 7, f" {info_doc}", 1, 1); pdf.set_text_color(0, 0, 0)

    return bytes(pdf.output())
