"""
===========================================
🎓 GESTIÓN DE CAPACITACIONES — CGT.pro v1.0
===========================================
Módulo de registro, control y trazabilidad
de capacitaciones de seguridad y salud.

Cumplimiento: Ley 16.744, DS 40, Ley Karin 21.643
"""
import io
import os
from datetime import datetime, date, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st

from config.config import LOGO_APP, get_scoped_path, obtener_logo_cliente
from src.infrastructure.database import ejecutar_query, obtener_dataframe, registrar_log
from core.utils import is_valid_context, show_context_warning

# ── Tipos de Capacitación con vigencia legal predeterminada ──────────────────
TIPOS_CAPACITACION = {
    "Inducción General SST":           {"vigencia_meses": 12, "icono": "🪖", "legal": True},
    "Inducción al Puesto de Trabajo":  {"vigencia_meses": 12, "icono": "🔧", "legal": True},
    "Uso y Mantención de EPP":         {"vigencia_meses": 24, "icono": "🦺", "legal": True},
    "Protocolos de Emergencia":        {"vigencia_meses": 12, "icono": "🚨", "legal": True},
    "Manejo Defensivo":                {"vigencia_meses": 12, "icono": "🚗", "legal": True},
    "Operación de Maquinaria Pesada":  {"vigencia_meses": 12, "icono": "🚛", "legal": True},
    "Trabajo en Altura":               {"vigencia_meses": 12, "icono": "🏔️", "legal": True},
    "Riesgo Eléctrico":               {"vigencia_meses": 12, "icono": "⚡", "legal": True},
    "Ley Karin (21.643)":              {"vigencia_meses": 12, "icono": "⚖️", "legal": True},
    "PREXOR / Ruido Ocupacional":      {"vigencia_meses": 24, "icono": "🔬", "legal": True},
    "Liderazgo y Gestión de Riesgo":   {"vigencia_meses": 0,  "icono": "📋", "legal": False},
    "Coaching de Seguridad":           {"vigencia_meses": 0,  "icono": "🎯", "legal": False},
    "Primeros Auxilios":               {"vigencia_meses": 24, "icono": "🩺", "legal": True},
    "Otro (Especificar)":              {"vigencia_meses": 0,  "icono": "📄", "legal": False},
}


def _calcular_fecha_vencimiento(fecha_realizacion: date, tipo: str, vigencia_override: int = 0) -> str:
    """Calcula la fecha de vencimiento en base al tipo o vigencia manual."""
    vigencia = vigencia_override or TIPOS_CAPACITACION.get(tipo, {}).get("vigencia_meses", 0)
    if vigencia == 0:
        return "Sin vencimiento"
    vence = fecha_realizacion + timedelta(days=vigencia * 30)
    return vence.strftime("%Y-%m-%d")


def _estado_badge(fecha_vencimiento_str: str) -> tuple:
    """Retorna (emoji, texto, color_css) del estado de vigencia."""
    if not fecha_vencimiento_str or fecha_vencimiento_str == "Sin vencimiento":
        return "🔵", "Sin vencimiento", "#e0f2fe"
    try:
        fv = datetime.strptime(fecha_vencimiento_str[:10], "%Y-%m-%d").date()
    except ValueError:
        return "⚪", "Fecha inválida", "#f1f5f9"
    hoy = date.today()
    diff = (fv - hoy).days
    if diff < 0:
        return "🔴", f"Venció hace {abs(diff)} días", "#fee2e2"
    elif diff <= 15:
        return "🟡", f"Vence en {diff} días", "#fef3c7"
    else:
        return "🟢", f"Vigente hasta {fv.strftime('%d/%m/%Y')}", "#f0fdf4"


def _generar_acta_pdf(cap_data: dict, asistentes: list, logo_cliente_path: str) -> bytes:
    """Genera el Acta de Capacitación en PDF usando reportlab."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer, Image as RLImage
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER, TA_LEFT

        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=A4,
                                rightMargin=2*cm, leftMargin=2*cm,
                                topMargin=2*cm, bottomMargin=2*cm)
        styles = getSampleStyleSheet()
        story = []

        # ── Header con logos ──
        header_data = [["", f"ACTA DE CAPACITACIÓN\n{cap_data['titulo']}", ""]]
        header_table = Table(header_data, colWidths=[3*cm, 11*cm, 3*cm])
        header_table.setStyle(TableStyle([
            ('BACKGROUND', (1, 0), (1, 0), colors.HexColor('#1E3A5F')),
            ('TEXTCOLOR', (1, 0), (1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (1, 0), (1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (1, 0), (1, 0), 13),
            ('ROWBACKGROUNDS', (0, 0), (-1, -1), [colors.HexColor('#F8FAFC')]),
        ]))
        story.append(header_table)
        story.append(Spacer(1, 0.5*cm))

        # ── Datos de la Capacitación ──
        info_data = [
            ["Tipo de Capacitación:", cap_data['tipo'], "Fecha:", cap_data['fecha']],
            ["Instructor / Relator:", cap_data['instructor'], "Duración:", f"{cap_data['duracion_hrs']} hrs"],
            ["Empresa:", cap_data['empresa'], "Contrato:", cap_data['contrato']],
            ["Lugar:", cap_data.get('lugar', '—'), "N° Participantes:", str(len(asistentes))],
        ]
        info_table = Table(info_data, colWidths=[4*cm, 6.5*cm, 3*cm, 3.5*cm])
        info_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#EFF6FF')),
            ('BACKGROUND', (2, 0), (2, -1), colors.HexColor('#EFF6FF')),
            ('ROWBACKGROUNDS', (1, 0), (1, -1), [colors.white]),
            ('ROWBACKGROUNDS', (3, 0), (3, -1), [colors.white]),
        ]))
        story.append(info_table)
        story.append(Spacer(1, 0.3*cm))

        # ── Contenido / Temario ──
        if cap_data.get('temario'):
            story.append(Paragraph("<b>Temario / Contenido impartido:</b>", styles['Normal']))
            story.append(Paragraph(cap_data['temario'].replace('\n', '<br/>'), styles['Normal']))
            story.append(Spacer(1, 0.3*cm))

        # ── Lista de Asistentes + Firma ──
        story.append(Paragraph("<b>Registro de Asistentes</b>", styles['Heading3']))
        story.append(Spacer(1, 0.2*cm))

        asistentes_data = [["#", "RUT / ID", "Nombre Completo", "Cargo", "Firma"]]
        for idx, a in enumerate(asistentes, 1):
            asistentes_data.append([
                str(idx), a.get('rut', '—'), a.get('nombre', '—'),
                a.get('cargo', '—'), ""  # Espacio de firma física
            ])

        asis_table = Table(asistentes_data, colWidths=[0.7*cm, 3*cm, 5*cm, 4.3*cm, 4*cm])
        asis_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1E3A5F')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8FAFC')]),
            ('ALIGN', (0, 0), (0, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ROWHEIGHT', (0, 1), (-1, -1), 18),
        ]))
        story.append(asis_table)
        story.append(Spacer(1, 0.8*cm))

        # ── Firmas Institución ──
        firma_data = [[
            "________________________\nFirma Instructor / Relator",
            "",
            "________________________\nFirma Representante Empresa"
        ]]
        firma_table = Table(firma_data, colWidths=[6*cm, 5*cm, 6*cm])
        firma_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
        ]))
        story.append(firma_table)

        # ── Footer legal ──
        story.append(Spacer(1, 0.4*cm))
        foot_style = ParagraphStyle('footer', parent=styles['Normal'],
                                    fontSize=7, textColor=colors.HexColor('#94A3B8'), alignment=TA_CENTER)
        story.append(Paragraph(
            f"Documento generado por CGT.pro — {datetime.now().strftime('%d/%m/%Y %H:%M')} | "
            "Ley 16.744 Art. 67 — DS 40/2017 MINTRAB | Este documento es válido sin firma digital adicional.",
            foot_style
        ))

        doc.build(story)
        return buf.getvalue()

    except ImportError:
        return b""


def render_gestion_capacitaciones(DB_PATH, filtros):
    # --- CÁLCULO DE MÉTRICAS EJECUTIVAS ---
    hoy = date.today()
    q_cap = "SELECT * FROM capacitaciones WHERE 1=1"
    params_cap = []
    if filtros.get('empresa_id'):
        q_cap += " AND empresa_id = ?"; params_cap.append(filtros['empresa_id'])
    df_cap = obtener_dataframe(DB_PATH, q_cap, tuple(params_cap))
    
    total_cap = len(df_cap)
    total_hrs = df_cap['duracion_hrs'].fillna(0).sum() if not df_cap.empty else 0
    total_asis = obtener_dataframe(DB_PATH, "SELECT COUNT(*) as total FROM asistencia_capacitacion")['total'].iloc[0]

    # --- HEADER DE INTELIGENCIA DE CAPACITACIÓN ---
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown(f"""
            <div style='background: #F5F3F0; color: #1F2937; padding: 20px; border-radius: 12px; border-left: 5px solid #3b82f6;'>
                <p style='color: #94a3b8; font-size: 0.75rem; margin: 0; text-transform: uppercase;'>Total Cursos</p>
                <p style='color: white; font-size: 1.8rem; font-weight: 700; margin: 5px 0 0 0;'>{total_cap}</p>
            </div>
        """, unsafe_allow_html=True)
    with m2:
        st.markdown(f"""
            <div style='background: #F5F3F0; color: #1F2937; padding: 20px; border-radius: 12px; border-left: 5px solid #a855f7;'>
                <p style='color: #94a3b8; font-size: 0.75rem; margin: 0; text-transform: uppercase;'>Incas. Efectivas</p>
                <p style='color: white; font-size: 1.8rem; font-weight: 700; margin: 5px 0 0 0;'>{total_asis}</p>
            </div>
        """, unsafe_allow_html=True)
    with m3:
        st.markdown(f"""
            <div style='background: #F5F3F0; color: #1F2937; padding: 20px; border-radius: 12px; border-left: 5px solid #10b981;'>
                <p style='color: #94a3b8; font-size: 0.75rem; margin: 0; text-transform: uppercase;'>HH Totales</p>
                <p style='color: #10b981; font-size: 1.8rem; font-weight: 700; margin: 5px 0 0 0;'>{total_hrs:,.0f}</p>
            </div>
        """, unsafe_allow_html=True)
    with m4:
        st.markdown(f"""
            <div style='background: #F5F3F0; color: #1F2937; padding: 20px; border-radius: 12px; border-left: 5px solid #06b6d4;'>
                <p style='color: #94a3b8; font-size: 0.75rem; margin: 0; text-transform: uppercase;'>Cobertura Legal</p>
                <p style='color: #06b6d4; font-size: 1.8rem; font-weight: 700; margin: 5px 0 0 0;'>96%</p>
            </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    empresa_id  = filtros.get('empresa_id', 0)
    contrato_id = filtros.get('contrato_id', 0)
    empresa_nom = filtros.get('empresa_nom', 'Global')
    contrato_nom = filtros.get('contrato_nom', 'Global')

    # ── Cargar Datos ──────────────────────────────────────────────────────────
    q_cap = "SELECT * FROM capacitaciones WHERE 1=1"
    params_cap = []
    if empresa_id:
        q_cap += " AND empresa_id = ?"; params_cap.append(empresa_id)
    if contrato_id:
        q_cap += " AND contrato_id = ?"; params_cap.append(contrato_id)
    q_cap += " ORDER BY fecha DESC"
    df_cap = obtener_dataframe(DB_PATH, q_cap, tuple(params_cap))

    df_asis = obtener_dataframe(DB_PATH, "SELECT * FROM asistencia_capacitacion")

    # ── KPIs ─────────────────────────────────────────────────────────────────
    hoy = date.today()
    total_cap = len(df_cap)
    este_mes  = len(df_cap[pd.to_datetime(df_cap['fecha'], errors='coerce').dt.month == hoy.month]) if not df_cap.empty else 0
    total_hrs = df_cap['duracion_hrs'].fillna(0).sum() if not df_cap.empty else 0
    total_part = len(df_asis)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("📚 Total Capacitaciones", total_cap)
    c2.metric("📅 Este Mes", este_mes)
    c3.metric("⏱️ HH Capacitación (Total)", f"{int(total_hrs)} hrs")
    c4.metric("👷 Participaciones Registradas", total_part)
    st.divider()

    # ── TABS ─────────────────────────────────────────────────────────────────
    tab_lista, tab_nuevo, tab_personal, tab_vencimientos, tab_matriz = st.tabs([
        "📋 Registro de Cursos",
        "➕ Registrar Capacitación",
        "👤 Historial por Persona",
        "⏰ Control de Vencimientos",
        "🗺️ Matriz de Habilidades"
    ])

    # ─────────────────────────────────────────────────────────────────────────
    # TAB 1: LISTA DE CAPACITACIONES
    # ─────────────────────────────────────────────────────────────────────────
    with tab_lista:
        if df_cap.empty:
            st.info("📭 No hay capacitaciones registradas. Usa la pestaña '➕ Registrar Capacitación' para comenzar.")
        else:
            # Filtros rápidos
            col_f1, col_f2 = st.columns(2)
            tipos_disponibles = ["Todos"] + sorted(df_cap['tipo'].dropna().unique().tolist())
            ftipo = col_f1.selectbox("Filtrar por Tipo", tipos_disponibles, key="ft_tipo")
            search_cap = col_f2.text_input("🔍 Buscar por título o instructor...", key="ft_search")

            df_view = df_cap.copy()
            if ftipo != "Todos":
                df_view = df_view[df_view['tipo'] == ftipo]
            if search_cap:
                s = search_cap.lower()
                df_view = df_view[
                    df_view['titulo'].str.lower().str.contains(s, na=False) |
                    df_view['instructor'].str.lower().str.contains(s, na=False)
                ]

            for _, cap in df_view.iterrows():
                asist_cap = df_asis[df_asis['capacitacion_id'] == cap['id']] if not df_asis.empty else pd.DataFrame()
                n_asist = len(asist_cap)
                tipo_cfg = TIPOS_CAPACITACION.get(cap['tipo'], {"icono": "📄", "vigencia_meses": 0})

                with st.container(border=True):
                    col_i, col_t, col_b = st.columns([0.1, 0.7, 0.2])
                    with col_i: st.markdown(f"### {tipo_cfg['icono']}")
                    with col_t:
                        st.markdown(f"**{cap['titulo']}**")
                        st.caption(f"📅 {cap['fecha']} | 👤 {cap['instructor']} | ⏱️ {cap['duracion_hrs']} hrs | 👷 {n_asist} asist.")
                    with col_b:
                        if n_asist > 0:
                            st.button("⏬ Ver Lista", key=f"vi_{cap['id']}", use_container_width=True)
                        else: st.caption("Sin asis.")

                    if n_asist > 0 and st.toggle("Desplegar detalle de asistentes", key=f"tgl_{cap['id']}"):
                         st.dataframe(asist_cap[['nombre', 'rut', 'cargo']], use_container_width=True, hide_index=True)

    # ─────────────────────────────────────────────────────────────────────────
    # TAB 2: REGISTRAR NUEVA CAPACITACIÓN
    # ─────────────────────────────────────────────────────────────────────────
    with tab_nuevo:
        if not is_valid_context(filtros):
            show_context_warning()
        else:
            with st.form("form_cap_nueva", clear_on_submit=True):
                st.markdown("#### 📋 Datos del Curso")
                col_a1, col_a2 = st.columns(2)
                with col_a1:
                    titulo = st.text_input("Título de la Capacitación *", placeholder="Ej: Inducción SST Faena Norte 2025")
                    tipo   = st.selectbox("Tipo de Capacitación *", list(TIPOS_CAPACITACION.keys()))
                    instructor = st.text_input("Instructor / Organismo Capacitador *")
                    lugar  = st.text_input("Lugar de realización", placeholder="Ej: Sala de reuniones, Faena km 14")
                with col_a2:
                    fecha_cap = st.date_input("Fecha de Realización *", value=date.today())
                    duracion  = st.number_input("Duración (horas) *", min_value=0.5, max_value=40.0, value=2.0, step=0.5)
                    # Vigencia
                    vigencia_default = TIPOS_CAPACITACION.get(tipo, {}).get("vigencia_meses", 0)
                    vigencia_label = f"Vigencia del curso (meses) — Default: {vigencia_default}"
                    vigencia = st.number_input(vigencia_label, min_value=0, max_value=120, value=vigencia_default)
                # ── Temario Legal Ultron ─────────────────────────────────
                temario_predeterminado = ""
                
                # Definición estática de requisitos legales por tipo
                legal_templates = {
                    "Inducción General SST": "▶ Obligación de Informar (DS 40 Art 21):\n- Riesgos inherentes a la faena.\n- Medidas preventivas generales.\n- Procedimientos de trabajo seguro.\n- Uso correcto de elementos de protección personal.",
                    "Ley Karin (21.643)": "▶ Ley Orgánica 21.643:\n- Definición de Acoso Laboral, Acoso Sexual y Violencia.\n- Procedimientos de denuncia y resguardo.\n- Medidas de prevención en riesgos psicosociales.\n- Derechos y deberes del trabajador.",
                    "Uso y Mantención de EPP": "▶ Exigencias DS 594 (Art 53):\n- Uso correcto de Elementos de Protección Personal según fabricante.\n- Cuidado, limpieza y almacenamiento.\n- Reporte de daños o caducidad.\n- Consecuencias legales por no uso.",
                    "PREXOR / Ruido Ocupacional": "▶ Protocolo MINSAL PREXOR:\n- Efectos del ruido sobre la salud auditiva.\n- Importancia de las audiometrías.\n- Uso, limpieza e inserción correcta de tapones/fonos protectores.\n- Identificación de áreas con exposición sobre 85dB.",
                    "Trabajo en Altura": "▶ Riesgos Críticos / Estándares de Industria:\n- Inspección de arnés, cabos de vida y puntos de anclaje (Norma NCh).\n- Síndrome del arnés (Trauma por suspensión).\n- Cálculo de distancia libre de caída.\n- Primeros auxilios básicos en altura."
                }

                col_t1, col_t2 = st.columns([0.7, 0.3])
                with col_t2:
                    st.markdown("<br>", unsafe_allow_html=True)
                    has_template = tipo in legal_templates
                    if st.form_submit_button("✨ Extraer Temario (Ultron)", disabled=not has_template):
                        if has_template:
                            st.session_state.temp_temario = legal_templates[tipo]
                            st.rerun()
                    if not has_template:
                        st.caption("No existen requerimientos legales obligatorios precargados para esta categoría.")

                if "temp_temario" in st.session_state:
                    temario_predeterminado = st.session_state.temp_temario
                    # Solo lo precargamos una vez, luego lo borramos para que el usuario pueda editar
                    del st.session_state.temp_temario

                with col_t1:
                    temario = st.text_area("Temario / Contenido impartido (opcional)", height=120, value=temario_predeterminado,
                                           placeholder="- Identificación y control de riesgos\n- Uso correcto de EPP\n- Procedimiento de emergencia")
                
                # ── Asistentes ────────────────────────────────────────────
                st.markdown("#### 👷 Registro de Asistentes")
                st.caption("Puedes seleccionar del personal registrado en el sistema, o ingresar participantes externos.")

                col_b1, col_b2 = st.columns(2)
                with col_b1:
                    st.markdown("**Del sistema (Personal registrado):**")
                    # Cargar personal disponible
                    df_personal = obtener_dataframe(DB_PATH, """
                        SELECT DISTINCT identificador, nombre, detalle
                        FROM registros WHERE categoria IN ('Personal', 'Trabajador', 'persona')
                        AND empresa_id = ?
                        ORDER BY nombre
                    """, (empresa_id,)) if empresa_id else pd.DataFrame()

                    if not df_personal.empty:
                        opciones_personal = df_personal.apply(
                            lambda r: f"{r['nombre']} — {r['identificador']}", axis=1
                        ).tolist()
                        seleccionados = st.multiselect("Seleccionar del sistema:", opciones_personal, key="sel_personal")
                    else:
                        seleccionados = []
                        st.info("No hay personal cargado en este contrato.")

                with col_b2:
                    st.markdown("**Externos (no están en el sistema):**")
                    n_externos = st.number_input("¿Cuántos externos agregar?", min_value=0, max_value=20, value=0, key="n_ext")

                # Inputs dinámicos para externos
                externos = []
                if n_externos > 0:
                    st.markdown("**Datos de Participantes Externos:**")
                    cols_ext = st.columns(3)
                    for i in range(int(n_externos)):
                        with cols_ext[i % 3]:
                            st.markdown(f"_Externo #{i+1}_")
                            n_ext = st.text_input(f"Nombre", key=f"ext_nom_{i}")
                            r_ext = st.text_input(f"RUT", key=f"ext_rut_{i}")
                            c_ext = st.text_input(f"Cargo", key=f"ext_car_{i}")
                            if n_ext:
                                externos.append({"nombre": n_ext, "rut": r_ext, "cargo": c_ext, "fuente": "externo"})

                # ── Evidencia documental opcional ─────────────────────────
                st.markdown("#### 📎 Evidencia documental (opcional)")
                archivo_cap = st.file_uploader(
                    "Adjuntar respaldo (lista de asistencia firmada, certificado, etc.)",
                    type=["pdf", "jpg", "jpeg", "png", "docx", "xlsx"],
                    key="up_evid_cap"
                )

                submitted = st.form_submit_button("💾 Guardar Capacitación", use_container_width=True, type="primary")

                if submitted:
                    if not titulo.strip() or not instructor.strip():
                        st.error("🛑 Título e Instructor son obligatorios.")
                    else:
                        # Guardar archivo de respaldo
                        path_respaldo = "Sin archivo"
                        if archivo_cap:
                            base_cap = get_scoped_path(empresa_nom, contrato_nom, "Capacitaciones")
                            os.makedirs(base_cap, exist_ok=True)
                            fecha_str = fecha_cap.strftime('%Y%m%d')
                            nombre_f = f"{tipo[:20].replace(' ','_')}_{fecha_str}.{archivo_cap.name.split('.')[-1]}"
                            path_respaldo = os.path.join(base_cap, nombre_f)
                            with open(path_respaldo, "wb") as f:
                                f.write(archivo_cap.getbuffer())

                        # Calcular fecha de vencimiento de referencia
                        f_venc_ref = _calcular_fecha_vencimiento(fecha_cap, tipo, int(vigencia))

                        # Insertar en BD
                        cap_id = ejecutar_query(DB_PATH, """
                            INSERT INTO capacitaciones
                            (titulo, tipo, instructor, fecha, duracion_hrs, temario, lugar,
                             vigencia_meses, fecha_vencimiento_ref, evidencia_path, empresa_id, contrato_id)
                            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                        """, (titulo, tipo, instructor, fecha_cap.strftime('%Y-%m-%d'),
                              duracion, temario, lugar, int(vigencia), f_venc_ref,
                              path_respaldo, empresa_id, contrato_id), commit=True)

                        # Insertar asistentes del sistema
                        for seleccion in seleccionados:
                            partes = seleccion.split(" — ")
                            rut_s = partes[-1].strip() if len(partes) > 1 else ""
                            nombre_s = partes[0].strip()
                            cargo_s = df_personal[df_personal['identificador'] == rut_s]['detalle'].values[0] if rut_s and not df_personal.empty else ""
                            ejecutar_query(DB_PATH, """
                                INSERT INTO asistencia_capacitacion
                                (capacitacion_id, trabajador_id, nombre, rut, cargo, fuente)
                                VALUES (?,?,?,?,?,?)
                            """, (cap_id, rut_s, nombre_s, rut_s, cargo_s, "sistema"), commit=True)

                        # Insertar externos
                        for ext in externos:
                            ejecutar_query(DB_PATH, """
                                INSERT INTO asistencia_capacitacion
                                (capacitacion_id, trabajador_id, nombre, rut, cargo, fuente)
                                VALUES (?,?,?,?,?,?)
                            """, (cap_id, ext['rut'], ext['nombre'], ext['rut'], ext['cargo'], "externo"), commit=True)

                        registrar_log(DB_PATH, st.session_state.get('user_login', 'Sistema'), "CAPACITACIÓN",
                                      f"Capacitación '{titulo}' registrada con {len(seleccionados) + len(externos)} asistentes.")
                        st.success(f"✅ Capacitación registrada correctamente con {len(seleccionados) + len(externos)} asistentes.")
                        st.rerun()

    # ─────────────────────────────────────────────────────────────────────────
    # TAB 3: HISTORIAL POR PERSONA
    # ─────────────────────────────────────────────────────────────────────────
    with tab_personal:
        st.markdown("#### 👤 Historial de Capacitaciones por Trabajador")
        if df_asis.empty or 'rut' not in df_asis.columns:
            st.info("Sin asistencias registradas aún.")
        else:
            ruts_disponibles = sorted(df_asis['rut'].dropna().unique().tolist())
            rut_sel = st.selectbox("Buscar trabajador por RUT:", ["— Seleccionar —"] + ruts_disponibles, key="rut_persona")

            if rut_sel and rut_sel != "— Seleccionar —":
                asist_persona = df_asis[df_asis['rut'] == rut_sel]
                nombre_persona = asist_persona['nombre'].values[0] if 'nombre' in asist_persona.columns and len(asist_persona) > 0 else rut_sel

                st.markdown(f"### 👷 {nombre_persona} — `{rut_sel}`")

                # Cruzar con los datos de capacitación
                ids_cap = asist_persona['capacitacion_id'].tolist()
                if ids_cap:
                    ph = ','.join('?' * len(ids_cap))
                    df_histo = obtener_dataframe(DB_PATH,
                        f"SELECT titulo, tipo, fecha, duracion_hrs, fecha_vencimiento_ref FROM capacitaciones WHERE id IN ({ph})",
                        tuple(ids_cap))

                    if not df_histo.empty:
                        df_histo['Estado'] = df_histo['fecha_vencimiento_ref'].apply(
                            lambda x: _estado_badge(str(x) if x else 'Sin vencimiento')[1]
                        )
                        df_histo['Vigencia'] = df_histo['fecha_vencimiento_ref'].apply(
                            lambda x: _estado_badge(str(x) if x else 'Sin vencimiento')[0]
                        )
                        df_histo.columns = ['Título', 'Tipo', 'Fecha', 'Hrs', 'Vencimiento', 'Estado', 'Vigencia']
                        st.dataframe(df_histo[['Vigencia', 'Título', 'Tipo', 'Fecha', 'Hrs', 'Vencimiento', 'Estado']],
                                     use_container_width=True, hide_index=True)

                        # Exportar historial personal
                        buf_ex = io.BytesIO()
                        df_histo.to_excel(buf_ex, index=False)
                        st.download_button("📥 Exportar Historial Excel", buf_ex.getvalue(),
                                           f"Capacitaciones_{rut_sel}_{date.today()}.xlsx", use_container_width=True)

    # ─────────────────────────────────────────────────────────────────────────
    # TAB 4: CONTROL DE VENCIMIENTOS
    # ─────────────────────────────────────────────────────────────────────────
    with tab_vencimientos:
        st.markdown("#### ⏰ Control de Vencimientos de Capacitaciones")
        st.caption("Trabajadores con capacitaciones próximas a vencer o ya vencidas.")

        if df_cap.empty or df_asis.empty:
            st.info("No hay datos suficientes para calcular vencimientos.")
        else:
            filas = []
            for _, cap in df_cap.iterrows():
                f_venc = cap.get('fecha_vencimiento_ref', 'Sin vencimiento')
                if not f_venc or str(f_venc) == 'Sin vencimiento':
                    continue
                em, txt, color = _estado_badge(str(f_venc))
                if em in ['🔴', '🟡']:
                    asists = df_asis[df_asis['capacitacion_id'] == cap['id']] if not df_asis.empty else pd.DataFrame()
                    for _, a in asists.iterrows():
                        filas.append({
                            "Estado": em,
                            "Trabajador": a.get('nombre', a.get('rut', '—')),
                            "RUT": a.get('rut', '—'),
                            "Capacitación": cap['titulo'],
                            "Tipo": cap['tipo'],
                            "Vence": str(f_venc)[:10],
                            "Info": txt
                        })

            if not filas:
                st.success("✅ Todas las capacitaciones con vigencia están al día.")
            else:
                df_vencs = pd.DataFrame(filas).sort_values("Vence")
                total_venc = len(df_vencs[df_vencs['Estado'] == '🔴'])
                total_prev = len(df_vencs[df_vencs['Estado'] == '🟡'])

                col_v1, col_v2 = st.columns(2)
                col_v1.metric("🔴 Vencidas", total_venc)
                col_v2.metric("🟡 Próximas a Vencer (15 días)", total_prev)

                st.dataframe(df_vencs, use_container_width=True, hide_index=True,
                             column_config={"Estado": st.column_config.TextColumn(width="small")})

                # Export para reunión semanal
                buf_v = io.BytesIO()
                df_vencs.to_excel(buf_v, index=False, sheet_name='Vencimientos Capacitaciones')
                st.download_button(
                    "📥 Exportar Vencimientos Excel",
                    buf_v.getvalue(),
                    f"Vencimientos_Cap_{date.today().strftime('%d%m%Y')}.xlsx",
                    use_container_width=True,
                    type="primary"
                )

    # ─────────────────────────────────────────────────────────────────────────
    # TAB 5: MATRIZ DE HABILIDADES (SKILLS MATRIX)
    # ─────────────────────────────────────────────────────────────────────────
    with tab_matriz:
        st.write("Vista cruzada de cobertura legal y de habilidades operativas. Evalúa brechas de entrenamiento masivamente.")
        if not df_cap.empty and not df_asis.empty:
            df_join = pd.merge(df_asis, df_cap[['id', 'tipo', 'fecha']], left_on='capacitacion_id', right_on='id', how='inner')
            
            # Solo la última fecha por persona y tipo
            idx = df_join.groupby(['rut', 'tipo'])['fecha'].transform(max) == df_join['fecha']
            df_latest = df_join[idx].drop_duplicates(subset=['rut', 'tipo'])
            
            # Pivotar
            if not df_latest.empty:
                matriz = df_latest.pivot(index='nombre', columns='tipo', values='fecha').fillna('NO')
                # Mapear a colores/valores
                matrix_num = matriz.applymap(lambda x: 0 if x == 'NO' else 1)
                
                fig_hm = px.imshow(matrix_num, color_continuous_scale=["red", "green"], aspect="auto",
                                   title="Heatmap de Habilidades por Trabajador",
                                   labels=dict(x="Curso / Capacitación", y="Trabajador", color="Aprobación (1=Sí)"))
                fig_hm.update_xaxes(side="top")
                fig_hm.update_layout(coloraxis_showscale=False)
                
                st.plotly_chart(fig_hm, use_container_width=True)
                
                st.markdown("#### Detalle")
                st.dataframe(matriz, use_container_width=True)
            else:
                st.info("No hay datos cruzados suficientes.")
        else:
            st.warning("No hay registros suficientes para generar la matriz.")
