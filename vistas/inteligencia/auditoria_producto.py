import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from src.infrastructure.database import ejecutar_query, obtener_dataframe, registrar_log
from core.tech_audit_data import DEFAULT_MODULES

def init_tech_audit_db(DB_PATH):
    """Seed the database with default modules if they don't exist."""
    exist = ejecutar_query(DB_PATH, "SELECT COUNT(*) FROM technical_audit_scores")[0][0]
    if exist == 0:
        for mod in DEFAULT_MODULES:
            nota = (mod['func'] + mod['ui'] + mod['codigo'] + mod['datos']) / 4 if (mod['func'] + mod['ui'] + mod['codigo'] + mod['datos']) > 0 else 0
            # If some are 0 (like UI in CI/CD), adjust weight
            valid_metrics = [v for v in [mod['func'], mod['ui'], mod['codigo'], mod['datos']] if v > 0]
            nota = sum(valid_metrics) / len(valid_metrics) if valid_metrics else 0
            
            ejecutar_query(DB_PATH, """
                INSERT INTO technical_audit_scores (mod_id, nombre, archivo, func, ui, codigo, datos, nota_global, estado)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (mod['id'], mod['nombre'], mod['archivo'], mod['func'], mod['ui'], mod['codigo'], mod['datos'], nota, mod['estado']), commit=True)

def render_auditoria_producto(DB_PATH, filtros):
    st.markdown("<h2 style='color: #00D4FF;'>📋 CGT Audit Plan — Evaluación de Producto</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color: #8B98B8;'>Ranking de madurez técnica y funcional de los módulos del ecosistema CGT.pro.</p>", unsafe_allow_html=True)

    init_tech_audit_db(DB_PATH)

    # Botón de Sincronización IA
    with st.sidebar:
        st.markdown("---")
        if st.button("🧠 Recalcular Auditoría con IA", use_container_width=True, help="Restaura los valores iniciales de la auditoría basados en el último análisis profundo de Ultron."):
            ejecutar_query(DB_PATH, "DELETE FROM technical_audit_scores", commit=True)
            init_tech_audit_db(DB_PATH)
            st.success("Auditoría reiniciada con éxito.")
            st.rerun()

    if st.session_state.role != "Global Admin":
        st.error("Acceso restringido: Solo para Auditoría de Producto.")
        return

    # 1. Cargar Datos
    df = obtener_dataframe(DB_PATH, "SELECT * FROM technical_audit_scores ORDER BY CAST(mod_id AS INTEGER) ASC")
    
    # 2. Resumen de Madurez (KPIs)
    avg_global = df['nota_global'].mean()
    max_nota = df['nota_global'].max()
    min_nota = df['nota_global'].min()

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Índice de Madurez Global", f"{avg_global:.2f}/20", delta=f"{(avg_global/20*100):.1f}%")
    with c2:
        st.metric("Módulo más Maduro", f"{max_nota:.1f}")
    with c3:
        st.metric("Oportunidad de Mejora", f"{min_nota:.1f}")
    with c4:
        st.metric("Módulos Auditados", len(df))

    st.divider()

    tab_ranking, tab_eval, tab_graficos = st.tabs(["🏆 Ranking de Módulos", "✍️ Evaluar Módulo", "📊 Análisis de Radar"])

    with tab_ranking:
        st.markdown("### Ranking Técnico (Escala 1-20)")
        
        # Estilización de la tabla
        def color_score(val):
            if val >= 18: color = '#00FF41' # Neon Green
            elif val >= 15: color = '#00D4FF' # Neon Blue
            elif val >= 10: color = '#FFD700' # Gold
            else: color = '#FF3131' # Red
            return f'color: {color}; font-weight: bold;'

        styled_df = df[['mod_id', 'nombre', 'archivo', 'func', 'ui', 'codigo', 'datos', 'nota_global', 'estado']].copy()
        styled_df.columns = ['#', 'Módulo', 'Archivo', 'Func.', 'UI', 'Código', 'Datos', 'Nota Global', 'Estado']
        
        st.dataframe(styled_df.style.applymap(color_score, subset=['Func.', 'UI', 'Código', 'Datos', 'Nota Global']), 
                     use_container_width=True, hide_index=True)

    with tab_eval:
        st.markdown("### Actualizar Evaluación Técnica")
        col_sel, col_form = st.columns([0.3, 0.7])
        
        with col_sel:
            mod_options = {f"[{r['mod_id']}] {r['nombre']}": r['mod_id'] for _, r in df.iterrows()}
            sel_mod_name = st.selectbox("Seleccionar Módulo:", list(mod_options.keys()))
            mod_id = mod_options[sel_mod_name]
            
            # Obtener datos actuales del elegido
            current = df[df['mod_id'] == mod_id].iloc[0]

        with col_form:
            with st.form("form_eval_tech"):
                st.write(f"Editando: **{current['nombre']}** ({current['archivo']})")
                fc = st.slider("Funcionalidad (1-20)", 1, 20, int(current['func']))
                ui = st.slider("UI / UX (1-20)", 0, 20, int(current['ui']))
                cd = st.slider("Código (1-20)", 1, 20, int(current['codigo']))
                dt = st.slider("Datos / Integridad (1-20)", 0, 20, int(current['datos']))
                est = st.text_input("Estado / Nota", value=current['estado'])
                
                if st.form_submit_button("Guardar Cambios en Auditoría"):
                    # Recalcular Nota Global
                    metrics = [v for v in [fc, ui, cd, dt] if v > 0]
                    new_nota = sum(metrics) / len(metrics) if metrics else 0
                    
                    ejecutar_query(DB_PATH, """
                        UPDATE technical_audit_scores 
                        SET func=?, ui=?, codigo=?, datos=?, nota_global=?, estado=?, ultima_actualizacion=CURRENT_TIMESTAMP
                        WHERE mod_id=?
                    """, (fc, ui, cd, dt, new_nota, est, mod_id), commit=True)
                    
                    registrar_log(DB_PATH, st.session_state.user_login, "TECH_AUDIT_UPDATE", f"Actualizado módulo {mod_id}: {new_nota:.2f}")
                    st.success(f"✅ Evaluación de '{current['nombre']}' actualizada.")
                    st.rerun()

    with tab_graficos:
        st.markdown("### Huella Digital de Madurez")
        
        # Selector múltiple para comparar
        comparar = st.multiselect("Comparar Módulos:", df['nombre'].tolist(), default=df['nombre'].tolist()[:3])
        
        if comparar:
            fig = go.Figure()
            categories = ['Funcionalidad', 'UI', 'Código', 'Datos']
            
            for mod_name in comparar:
                r = df[df['nombre'] == mod_name].iloc[0]
                fig.add_trace(go.Scatterpolar(
                    r=[r['func'], r['ui'], r['codigo'], r['datos']],
                    theta=categories,
                    fill='toself',
                    name=mod_name
                ))

            fig.update_layout(
                polar=dict(
                    radialaxis=dict(visible=True, range=[0, 20], gridcolor="#444"),
                    bgcolor="rgba(0,0,0,0)"
                ),
                showlegend=True,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="white"),
                template="plotly_dark",
                height=500
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Selecciona módulos para visualizar su huella técnica.")

        st.divider()
        st.markdown("#### Histograma de Calidad")
        fig_hist = px.histogram(df, x="nota_global", nbins=10, 
                               title="Distribución de Módulos por Calidad Global",
                               color_discrete_sequence=['#00D4FF'],
                               labels={'nota_global': 'Nota Global (1-20)'})
        st.plotly_chart(fig_hist, use_container_width=True)
