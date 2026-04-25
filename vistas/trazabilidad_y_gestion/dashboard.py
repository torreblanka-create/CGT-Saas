import os
from datetime import datetime

import pandas as pd
import streamlit as st

from src.infrastructure.archivos import obtener_ruta_entidad, validar_archivo_seguro
from config.config import DB_PATH, LOGO_APP, LOGO_CLIENTE
from src.infrastructure.database import ejecutar_query, obtener_dataframe, registrar_log
from core.logic import calcular_estado_registro, resumir_estados_entidad
from core.reports import generar_excel_gerencial
from core.reports.generador_pdf import pdf_engine

# ── Configuración de categorías del sistema ───────────────────────────────────
CATEGORIAS_CONFIG = {
    "Personal":               {"icono": "👷", "alias": ["Personal", "Trabajador", "persona"]},
    "Maquinaria & Vehículos": {"icono": "🚛", "alias": ["Maquinaria Pesada & Vehículos", "Vehiculo", "Maquinaria"]},
    "Elementos de Izaje":     {"icono": "🏗️", "alias": ["Elementos de Izaje", "Izaje"]},
    "Instrumentos":           {"icono": "🔧", "alias": ["Instrumentos", "Herramienta"]},
    "Emergencia":             {"icono": "🚨", "alias": ["Emergencia", "EPP", "Extintores"]},
}

COLORES_ESTADO = {
    "VERDE":    {"bg": "rgba(16,185,129,0.1)",  "border": "#10B981", "text": "#059669", "label": "Operativos",  "emoji": "🟢"},
    "AMARILLO": {"bg": "rgba(245,158,11,0.1)",   "border": "#F59E0B", "text": "#D97706", "label": "En Alerta",   "emoji": "🟡"},
    "ROJO":     {"bg": "rgba(239,68,68,0.1)",    "border": "#EF4444", "text": "#DC2626", "label": "Bloqueados",  "emoji": "🔴"},
}

def _mapear_categoria(cat_raw: str) -> str:
    """Normaliza el nombre de categoría al grupo canónico."""
    if not cat_raw or pd.isna(cat_raw):
        return "Personal"
    cat_raw = str(cat_raw).strip()
    for canon, cfg in CATEGORIAS_CONFIG.items():
        if cat_raw == canon or cat_raw in cfg["alias"]:
            return canon
    return cat_raw  # Devuelve tal cual si no hace match

# ═══════════════════════════════════════════════════════════════════════════════
def render_dashboard(DB_PATH, filtros, LOGO_APP, LOGO_CLIENTE):

    col_title, col_logo = st.columns([4, 1])
    with col_title:
        st.markdown("<h2 class='titulo-dashboard'>📊 Panel de Control Gestión Total (CGT)</h2>",
                    unsafe_allow_html=True)
    with col_logo:
        if LOGO_CLIENTE and LOGO_CLIENTE != LOGO_APP and os.path.exists(LOGO_CLIENTE):
            st.image(LOGO_CLIENTE, use_container_width=True)

    f_emp_id = filtros.get('empresa_id', 0)
    f_con_id = filtros.get('contrato_id', 0)

    # ── Consulta principal ────────────────────────────────────────────────────
    query_sql = """
        SELECT r.id, r.identificador, r.nombre, r.detalle, r.tipo_doc, r.fecha_vencimiento,
               r.categoria, r.tipo_control, r.meta_horometro, r.estado_obs, r.observaciones,
               r.fecha_condicion, r.tiene_observacion, r.detalle_observacion, r.empresa_id, r.contrato_id, r.path,
               e.nombre as empresa_val, c.nombre_contrato as contrato_val
        FROM registros r
        JOIN (
            SELECT MAX(id) as max_id 
            FROM registros 
            GROUP BY identificador, tipo_doc
        ) latest ON r.id = latest.max_id
        LEFT JOIN empresas e ON r.empresa_id = e.id
        LEFT JOIN contratos c ON r.contrato_id = c.id
        WHERE 1=1
    """
    params_sql = []
    is_master  = st.session_state.role == "Global Admin"

    if not is_master:
        query_sql += " AND r.empresa_id = ?"
        params_sql.append(st.session_state.empresa_id)
    elif f_emp_id > 0:
        query_sql += " AND r.empresa_id = ?"
        params_sql.append(f_emp_id)

    if f_con_id:
        query_sql += " AND r.contrato_id = ?"
        params_sql.append(f_con_id)

    df_reg = obtener_dataframe(DB_PATH, query_sql, tuple(params_sql))

    try:
        df_horometros  = obtener_dataframe(DB_PATH, "SELECT * FROM horometros_actuales")
        dict_horometros = dict(zip(df_horometros['identificador'], df_horometros['horas_actuales']))
    except:
        dict_horometros = {}

    if df_reg.empty or 'nombre' not in df_reg.columns:
        st.warning("⚠️ No hay registros documentales en la base de datos.")
        return

    # ── Calcular estados (Optimización de Rendimiento O(N)) ───────────────────
    hoy = pd.to_datetime(datetime.now().date())
    df_reg['fecha_vencimiento'] = pd.to_datetime(df_reg['fecha_vencimiento'], errors='coerce')

    dict_records = df_reg.to_dict('records')
    doc_estados = []
    doc_infos = []

    summary_dict = {}

    # 1. Pasada única para calcular todos los estados individuales y agrupar al vuelo
    for i, doc in enumerate(dict_records):
        # Calcular estado individual
        est, info = calcular_estado_registro(doc, dict_horometros)
        doc_estados.append(est)
        doc_infos.append(info)

        # Agrupar por entidad
        id_val = doc['identificador']
        nombre = doc['nombre']
        key = (id_val, nombre)

        if key not in summary_dict:
            cat_raw = doc.get('categoria', 'Personal')
            det_val = doc.get('detalle', 'No Especificado')
            emp_val = doc.get('empresa_val', 'GLOBAL')
            con_val = doc.get('contrato_val', 'N/A')

            summary_dict[key] = {
                "Nombre": nombre,
                "Estado": "VERDE",
                "Alerta": "",
                "Detalle": str(det_val) if pd.notnull(det_val) and det_val != "" else "No Especificado",
                "ID_Patente": id_val,
                "Categoria": _mapear_categoria(cat_raw),
                "Doc_Critico": "",
                "Empresa": str(emp_val) if pd.notnull(emp_val) and str(emp_val).strip() != "" else "GLOBAL",
                "Contrato": str(con_val).upper() if pd.notnull(con_val) and str(con_val).strip() != "" else "N/A",
                "prioridad": 3  # 1: ROJO, 2: AMARILLO, 3: VERDE
            }

        # Determinar si este documento empeora el estado global
        current = summary_dict[key]
        if est == "ROJO":
            if current["prioridad"] > 1:
                current["Estado"] = "ROJO"
                current["prioridad"] = 1
                current["Doc_Critico"] = doc['tipo_doc']
                current["Alerta"] = info
        elif est == "AMARILLO":
            if current["prioridad"] > 2:
                current["Estado"] = "AMARILLO"
                current["prioridad"] = 2
                current["Doc_Critico"] = doc['tipo_doc']
                current["Alerta"] = info

    # 2. Re-asignar arrays calculados de vuelta al DataFrame
    df_reg['estado_doc'] = doc_estados
    df_reg['info_doc']   = doc_infos

    # 3. Construir res_df eliminando columna auxiliar
    res_df = pd.DataFrame(list(summary_dict.values()))
    if not res_df.empty: res_df.drop('prioridad', axis=1, inplace=True)

    df_rojos = res_df[res_df['Estado'] == 'ROJO'] if not res_df.empty else pd.DataFrame(columns=res_df.columns)

    # Calcular contadores
    n_verde    = len(res_df[res_df['Estado'] == 'VERDE'])
    n_amarillo = len(res_df[res_df['Estado'] == 'AMARILLO'])
    n_rojo     = len(df_rojos)

    # ════════════════════════════════════════════════════════════════════════
    # SECCIÓN 1 — Visión de Bloqueos y Resumen Ejecutivo
    # ════════════════════════════════════════════════════════════════════════
    st.markdown("### 🚨 Estado Actual de Bloqueos")

    # --- ESTILOS PREMIUM (GLASSMORPHISM & DASHBOARD) ---
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap');
        
        .stApp {
            font-family: 'Outfit', sans-serif !important;
        }

        /* Contenedor Glassmorphism para KPIs */
        .kpi-container {
            display: flex;
            gap: 15px;
            margin-bottom: 25px;
        }
        
        .glass-card {
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 16px;
            padding: 20px;
            flex: 1;
            transition: transform 0.3s ease, box-shadow 0.3s ease;
            box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.07);
        }
        
        .glass-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 12px 40px 0 rgba(31, 38, 135, 0.12);
            border: 1px solid rgba(255, 255, 255, 0.2);
        }

        .kpi-label {
            font-size: 0.75rem;
            font-weight: 600;
            color: #64748b;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 5px;
        }

        .kpi-value {
            font-size: 2.2rem;
            font-weight: 800;
            background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin: 0;
        }
        
        .dark .kpi-value {
            background: linear-gradient(135deg, #f8fafc 0%, #cbd5e1 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        /* Cristal Flotante para Resumen */
        .crystal-panel {
            background: rgba(255, 255, 255, 0.4);
            backdrop-filter: blur(20px);
            border: 1px solid rgba(255, 255, 255, 0.3);
            border-radius: 20px;
            padding: 25px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.03);
            height: 100%;
        }

        /* Tarjetas de Acción de Reportes */
        .report-action-card {
            background: white;
            border-radius: 12px;
            padding: 15px;
            border: 1px solid #f1f5f9;
            transition: all 0.2s ease;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 10px;
        }
        
        .report-action-card:hover {
            background: #f8fafc;
            border-color: #3b82f6;
            transform: scale(1.02);
        }
        
        .report-icon {
            font-size: 1.5rem;
            background: #eff6ff;
            width: 45px;
            height: 45px;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 10px;
        }

        /* Heatmap Table */
        .heatmap-cell {
            padding: 10px;
            border-radius: 8px;
            text-align: center;
            font-weight: bold;
        }
        
        .h-rojo { background: #fee2e2; color: #991b1b; }
        .h-amarillo { background: #fef3c7; color: #92400e; }
        .h-verde { background: #dcfce7; color: #166534; }
        
        </style>
    """, unsafe_allow_html=True)

    def render_kpi_card(label, value, border_color, emoji):
        st.markdown(f"""
            <div class="glass-card" style="border-top: 4px solid {border_color};">
                <div class="kpi-label">{emoji} {label}</div>
                <div class="kpi-value">{value}</div>
            </div>
        """, unsafe_allow_html=True)

    col_kpi1, col_kpi2, col_kpi3, col_kpi4 = st.columns(4)
    with col_kpi1: render_kpi_card("Operativos", n_verde, "#10b981", "🟢")
    with col_kpi2: render_kpi_card("En Alerta", n_amarillo, "#f59e0b", "🟡")
    with col_kpi3: render_kpi_card("Bloqueados", n_rojo, "#ef4444", "🔴")
    with col_kpi4: render_kpi_card("Total Analizados", len(res_df), "#3b82f6", "📊")

    df_block_details = df_rojos[['ID_Patente', 'Nombre', 'Categoria', 'Doc_Critico', 'Alerta', 'Empresa', 'Contrato', 'Detalle']].copy()
    df_block_details.columns = ['Identificador', 'Nombre', 'Categoría', 'Documento Crítico', 'Alerta', 'Empresa', 'Contrato', 'Detalle']

    st.markdown("#### 🔎 Detalle de Entidades Bloqueadas")
    if df_block_details.empty:
        st.success("✅ No hay entidades bloqueadas actualmente.")
    else:
        c_det1, c_det2 = st.columns([2.5, 1.2])
        with c_det1:
            st.dataframe(df_block_details, use_container_width=True, hide_index=True)
        with c_det2:
            st.markdown("""
                <div class="crystal-panel">
                    <h4 style="margin-top:0; color:#1e293b;">💎 Inteligencia de Bloqueos</h4>
                    <p style="font-size:0.85rem; color:#64748b; margin-bottom:15px;">Distribución de brechas críticas por categoría.</p>
            """, unsafe_allow_html=True)
            
            bloques_por_categoria = df_block_details.groupby('Categoría').size().sort_values(ascending=False)
            total_b = bloques_por_categoria.sum()
            
            for categoria, count in bloques_por_categoria.items():
                pct = (count / total_b) * 100
                st.markdown(f"""
                    <div style="margin-bottom:10px;">
                        <div style="display:flex; justify-content:space-between; font-size:0.8rem; font-weight:600;">
                            <span>{categoria}</span>
                            <span>{count}</span>
                        </div>
                        <div style="background:#e2e8f0; height:6px; border-radius:3px; margin-top:4px;">
                            <div style="background:#ef4444; width:{pct}%; height:100%; border-radius:3px;"></div>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
            
            st.markdown("<hr style='border:0; border-top:1px solid rgba(0,0,0,0.05); margin:15px 0;'>", unsafe_allow_html=True)
            
            top_docs = df_reg[df_reg['estado_doc'] == 'ROJO'].groupby('tipo_doc').size().sort_values(ascending=False).head(3)
            if not top_docs.empty:
                st.markdown("<p style='font-size:0.75rem; font-weight:700; color:#94a3b8; text-transform:uppercase;'>Documentos más Críticos</p>", unsafe_allow_html=True)
                for tipo_doc, count in top_docs.items():
                    st.markdown(f"""
                        <div style="display:flex; align-items:center; gap:8px; margin-bottom:5px; font-size:0.85rem;">
                            <span style="color:#ef4444;">●</span>
                            <span style="flex:1;">{tipo_doc}</span>
                            <span style="font-weight:bold;">{count}</span>
                        </div>
                    """, unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

    # ── RESUMEN DE COBERTURA (HEATMAP) ──
    st.markdown("### 📊 Resumen de Cobertura y Salud Documental")
    if res_df.empty:
        st.info("No hay entidades para mostrar en el resumen de cobertura.")
    else:
        df_cat = res_df.groupby('Categoria')['Estado'].value_counts().unstack(fill_value=0)
        
        # Heatmap manual con HTML
        st.markdown("""
            <div style="background:white; border:1px solid #e2e8f0; border-radius:12px; padding:20px;">
                <table style="width:100%; border-collapse: collapse;">
                    <thead>
                        <tr style="text-align:left; border-bottom:2px solid #f1f5f9;">
                            <th style="padding:10px; color:#64748b; font-size:0.85rem;">CATEGORÍA</th>
                            <th style="padding:10px; color:#ef4444; font-size:0.85rem; text-align:center;">🔴 BLOQUEADOS</th>
                            <th style="padding:10px; color:#f59e0b; font-size:0.85rem; text-align:center;">🟡 ALERTA</th>
                            <th style="padding:10px; color:#10b981; font-size:0.85rem; text-align:center;">🟢 OPERATIVOS</th>
                        </tr>
                    </thead>
                    <tbody>
        """, unsafe_allow_html=True)
        
        for cat_name, row in df_cat.iterrows():
            n_r = row.get('ROJO', 0)
            n_a = row.get('AMARILLO', 0)
            n_v = row.get('VERDE', 0)
            
            st.markdown(f"""
                <tr style="border-bottom:1px solid #f8fafc;">
                    <td style="padding:12px; font-weight:600; color:#1e293b;">{cat_name}</td>
                    <td style="padding:8px;"><div class="heatmap-cell h-rojo" style="opacity:{min(1, n_r/max(1,n_r+n_a+n_v)+0.2)};">{n_r}</div></td>
                    <td style="padding:8px;"><div class="heatmap-cell h-amarillo" style="opacity:{min(1, n_a/max(1,n_r+n_a+n_v)+0.2)};">{n_a}</div></td>
                    <td style="padding:8px;"><div class="heatmap-cell h-verde" style="opacity:{min(1, n_v/max(1,n_r+n_a+n_v)+0.2)};">{n_v}</div></td>
                </tr>
            """, unsafe_allow_html=True)
            
        st.markdown("</tbody></table></div>", unsafe_allow_html=True)

    # ── CENTRO DE REPORTES ──
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### 📑 Centro de Reportes y Auditoría")
    st.markdown("Descargue reportes oficiales consolidados para su revisión gerencial.")
    
    col_rep_a, col_rep_b = st.columns(2)
    with col_rep_a:
        st.markdown("""
            <div class="report-action-card">
                <div class="report-icon">🚨</div>
                <div style="flex:1;">
                    <div style="font-weight:700; color:#1e293b;">Reporte de Bloqueos</div>
                    <div style="font-size:0.8rem; color:#64748b;">PDF detallado con brechas críticas.</div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        try:
            pdf_bloqueados = pdf_engine.generar('BLOQUEADOS', df_rojos, LOGO_APP, LOGO_CLIENTE)
            st.download_button("Descargar PDF Bloqueos", pdf_bloqueados, f"CGT_Bloqueos_{hoy.strftime('%Y%m%d')}.pdf", use_container_width=True, key="dl_b_pdf")
        except: st.error("Error al generar PDF")

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("""
            <div class="report-action-card">
                <div class="report-icon">🗂️</div>
                <div style="flex:1;">
                    <div style="font-weight:700; color:#1e293b;">Informe de Auditoría</div>
                    <div style="font-size:0.8rem; color:#64748b;">Trazabilidad total de documentos.</div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        try:
            pdf_maestro = pdf_engine.generar('COMPLETO', df_reg, res_df, LOGO_APP, LOGO_CLIENTE, dict_horometros)
            st.download_button("Descargar PDF Auditoría", pdf_maestro, f"CGT_Auditoria_{hoy.strftime('%Y%m%d')}.pdf", use_container_width=True, key="dl_a_pdf")
        except: st.error("Error al generar PDF")

    with col_rep_b:
        st.markdown("""
            <div class="report-action-card">
                <div class="report-icon">🛠️</div>
                <div style="flex:1;">
                    <div style="font-weight:700; color:#1e293b;">Histórico de Fallas</div>
                    <div style="font-size:0.8rem; color:#64748b;">Trazabilidad de reparaciones técnicas.</div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        try:
            query_historial = """
                SELECT h.fecha, h.identificador, r.nombre, h.descripcion, h.reportado_por,
                       h.estado, h.fecha_resolucion, h.detalle_resolucion
                FROM historial_fallas h
                LEFT JOIN (SELECT DISTINCT identificador, nombre FROM registros) r
                       ON h.identificador = r.identificador
                ORDER BY h.fecha DESC
            """
            df_historial = obtener_dataframe(DB_PATH, query_historial)
            pdf_fallas_bytes = pdf_engine.generar('HISTORICO_FALLAS', df_historial, LOGO_APP, LOGO_CLIENTE)
            st.download_button("Descargar PDF Historial", pdf_fallas_bytes, f"Historico_Fallas_{hoy.strftime('%Y%m%d')}.pdf", use_container_width=True, key="dl_h_pdf")
        except: st.button("Descargar PDF Historial (Sin Datos)", disabled=True, use_container_width=True, key="dl_h_none")

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("""
            <div class="report-action-card">
                <div class="report-icon">📊</div>
                <div style="flex:1;">
                    <div style="font-weight:700; color:#1e293b;">Base de Datos (Excel)</div>
                    <div style="font-size:0.8rem; color:#64748b;">Exportación completa de registros.</div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        try:
            cols_export = [c for c in ['empresa', 'identificador', 'nombre', 'detalle', 'categoria', 'tipo_doc', 'fecha_vencimiento'] if c in df_reg.columns]
            df_export = df_reg[cols_export].copy()
            if 'fecha_vencimiento' in df_export.columns:
                df_export['fecha_vencimiento'] = df_export['fecha_vencimiento'].dt.strftime('%Y-%m-%d')
            excel_data = generar_excel_gerencial(res_df, df_export)
            st.download_button("Descargar Base Excel", excel_data, f"CGT_Base_{hoy.strftime('%Y%m%d')}.xlsx", use_container_width=True, key="dl_base_xlsx")
        except: st.error("Error al generar Excel")

    st.divider()

    # ════════════════════════════════════════════════════════════════════════
    # SECCIÓN 3 — Control de Brechas Críticas (Planes de Acción)
    # ════════════════════════════════════════════════════════════════════════
    st.markdown("### ⚠️ Control de Brechas Críticas (Planes de Acción)")

    query_p = "SELECT id, codigo_plan, accion, responsable, fecha_cierre, estado FROM planes_accion WHERE estado = 'Abierto'"
    params_p = []
    if not is_master:
        query_p += " AND empresa_id = ?"
        params_p.append(st.session_state.empresa_id)
    elif f_emp_id > 0:
        query_p += " AND empresa_id = ?"
        params_p.append(f_emp_id)

    if f_con_id:
        query_p += " AND contrato_id = ?"
        params_p.append(f_con_id)

    df_p = obtener_dataframe(DB_PATH, query_p, tuple(params_p))

    if df_p.empty:
        st.success("✅ No hay brechas críticas abiertas pendientes de atención.")
    else:
        df_p['fecha_cierre'] = pd.to_datetime(df_p['fecha_cierre'], errors='coerce')
        hoy_ts = pd.Timestamp.now().normalize()

        # Clasificar
        df_p['prioridad'] = df_p['fecha_cierre'].apply(
            lambda x: "VENCIDA" if pd.notnull(x) and x < hoy_ts
            else ("POR VENCER" if pd.notnull(x) and (x - hoy_ts).days <= 7
            else "A TIEMPO")
        )

        # Solo mostrar las urgentes
        df_urgente = df_p[df_p['prioridad'] != "A TIEMPO"].copy()

        if df_urgente.empty:
            st.info("💡 Existen brechas abiertas, pero todas están dentro del plazo programado.")
        else:
            col_u1, col_u2 = st.columns(2)

            vencidas = df_urgente[df_urgente['prioridad'] == "VENCIDA"]
            por_vencer = df_urgente[df_urgente['prioridad'] == "POR VENCER"]

            with col_u1:
                st.markdown(f"#### 🚨 Vencidas ({len(vencidas)})")
                for _, row in vencidas.iterrows():
                    dias = (hoy_ts - row['fecha_cierre']).days
                    st.markdown(f"""
                        <div style="background: rgba(239,68,68,0.1); border-left: 4px solid #EF4444; padding: 10px; border-radius: 4px; margin-bottom: 8px;">
                            <p style="margin:0; font-weight:bold; color:#EF4444;">{row['codigo_plan']} (Acción #{row['id']})</p>
                            <p style="margin:0; font-size:0.9rem;">{row['accion']}</p>
                            <p style="margin:0; font-size:0.8rem; opacity:0.8;">Responsable: {row['responsable']} | <b>Atraso: {dias} días</b></p>
                        </div>
                    """, unsafe_allow_html=True)

            with col_u2:
                st.markdown(f"#### ⏳ Por Vencer ({len(por_vencer)})")
                for _, row in por_vencer.iterrows():
                    dias = (row['fecha_cierre'] - hoy_ts).days
                    st.markdown(f"""
                        <div style="background: rgba(245,158,11,0.1); border-left: 4px solid #F59E0B; padding: 10px; border-radius: 4px; margin-bottom: 8px;">
                            <p style="margin:0; font-weight:bold; color:#F59E0B;">{row['codigo_plan']} (Acción #{row['id']})</p>
                            <p style="margin:0; font-size:0.9rem;">{row['accion']}</p>
                            <p style="margin:0; font-size:0.8rem; opacity:0.8;">Responsable: {row['responsable']} | <b>Faltan: {dias} días</b></p>
                        </div>
                    """, unsafe_allow_html=True)
