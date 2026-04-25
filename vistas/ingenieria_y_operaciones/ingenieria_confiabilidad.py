import io
import os
from datetime import datetime, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st

from config.config import LOGO_APP, LOGO_CLIENTE, get_scoped_path, obtener_logo_cliente
from src.infrastructure.database import ejecutar_query, obtener_dataframe

# Nuevos imports para reportabilidad
from core.reports.generador_pdf import pdf_engine


def render_confiabilidad_energetica(db_path, filtros):
    st.markdown("<h2 style='color: var(--cgt-blue);'>⚡ Control de Confiabilidad Operacional (CCO)</h2>", unsafe_allow_html=True)
    st.write("Registro de eventos de falla, análisis de disponibilidad y tendencias operativas.")
    st.divider()

    tab_registro, tab_dashboard, tab_historico = st.tabs([
        "📝 Registro de Eventos",
        "📊 Dashboard de Confiabilidad",
        "📥 Histórico y Reportes"
    ])

    # --- DATOS COMPARTIDOS ---
    empresa_id = filtros.get('empresa_id', 0)
    contrato_id = filtros.get('contrato_id', 0)

    with tab_registro:
        st.markdown("### 📋 Nuevo Reporte de Falla")

        from core.utils import is_valid_context, show_context_warning
        if not is_valid_context(filtros):
            show_context_warning()
        else:
            with st.form("form_evento_falla", clear_on_submit=True):
                col1, col2 = st.columns(2)

                with col1:
                    # Obtener equipos de la BD filtrados por empresa y contrato desde REGISTROS
                    query_equipos = "SELECT DISTINCT identificador, nombre, detalle FROM registros WHERE categoria != 'Personal'"
                    params_q = []

                    is_master = st.session_state.get('role') in ["Global Admin", "Admin", "Administrador"]
                    if not is_master:
                        query_equipos += " AND empresa_id = ?"
                        params_q.append(st.session_state.get('empresa_id', 0))
                    else:
                        if empresa_id > 0:
                            query_equipos += " AND empresa_id = ?"
                            params_q.append(empresa_id)

                    if contrato_id > 0:
                        query_equipos += " AND contrato_id = ?"
                        params_q.append(contrato_id)

                    df_equipos = obtener_dataframe(db_path, query_equipos, tuple(params_q), use_cache=True)

                    opciones_equipos = ["-- Seleccione --"]
                    if not df_equipos.empty:
                        df_equipos['display'] = df_equipos['identificador'] + " - " + df_equipos['nombre'] + " (" + df_equipos['detalle'].fillna('N/A') + ")"
                        opciones_equipos += df_equipos['display'].tolist()

                    equipo_sel = st.selectbox("🎯 Equipo / Sistema Afectado:", opciones_equipos)

                    tipo_falla = st.selectbox("⚠️ Tipo de Falla / Detención:", [
                        "Falla Eléctrica / Cortocircuito",
                        "Falla Mecánica / Estructural",
                        "Sobrecalentamiento / Sobrecarga",
                        "Falla de Sensores / Control",
                        "Desgaste Prematuro",
                        "Falla de Aislación / Fuga",
                        "Pérdida de Fase / Voltaje",
                        "Error de Operación",
                        "Mantenimiento Correctivo Urgente",
                        "Otro"
                    ])

                with col2:
                    fecha_evento = st.date_input("📅 Fecha del Evento:", value=datetime.now().date())
                    duracion = st.number_input("⏱️ Duración de la Detención (Minutos):", min_value=1, value=30)

                descripcion = st.text_area("🗒️ Descripción técnica y acciones tomadas:")
                foto_upload = st.file_uploader("📸 Adjuntar Evidencia Fotográfica (Opcional):", type=['png', 'jpg', 'jpeg'])

                if st.form_submit_button("🚀 Registrar Evento de Falla", use_container_width=True):
                    if equipo_sel == "-- Seleccione --":
                        st.error("Por favor, selecciona un equipo.")
                    elif not descripcion:
                        st.warning("Agregue una breve descripción.")
                    else:
                        id_equipo = equipo_sel.split(" - ")[0]

                        # Manejo de Foto
                        foto_final_path = None
                        if foto_upload:
                            # Crear ruta jerárquica
                            ruta_base = get_scoped_path(filtros.get('empresa_nom', 'Otros'), filtros.get('contrato_nom', 'Sin Contrato'), "Confiabilidad/Fallas")
                            nombre_archivo = f"FALLA_{id_equipo}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                            foto_final_path = os.path.join(ruta_base, nombre_archivo)
                            with open(foto_final_path, "wb") as f:
                                f.write(foto_upload.getbuffer())

                        # Guardar en BD de forma segura
                        query_ins = """
                            INSERT INTO eventos_confiabilidad 
                            (fecha, identificador, tipo_falla, descripcion, duracion_min, foto_path, empresa_id, contrato_id)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """
                        params_ins = (str(fecha_evento), id_equipo, tipo_falla, descripcion, duracion, foto_final_path, empresa_id, contrato_id)
                        ejecutar_query(db_path, query_ins, params_ins, commit=True)
                        st.success(f"✅ Evento registrado exitosamente para el equipo {id_equipo}.")
                        st.rerun()

    with tab_dashboard:
        st.markdown("### 📈 Análisis de Tendencias y Pareto")

        # Cargar Datos de forma segura
        query_data = "SELECT * FROM eventos_confiabilidad"
        params_d = []
        if empresa_id > 0:
            query_data += " WHERE empresa_id = ?"
            params_d.append(empresa_id)
            if contrato_id != 0:
                query_data += " AND contrato_id = ?"
                params_d.append(contrato_id)
        elif contrato_id != 0:
            query_data += " WHERE contrato_id = ?"
            params_d.append(contrato_id)

        df_ev = obtener_dataframe(db_path, query_data, tuple(params_d))

        if df_ev.empty:
            st.info("Aún no hay eventos registrados para mostrar estadísticas.")
        else:
            df_ev['fecha'] = pd.to_datetime(df_ev['fecha'])

            st.markdown("#### ⚡ KPIs Operacionales (Mes Actual)")
            mes_actual = datetime.now().strftime('%Y-%m')
            df_mes = df_ev[df_ev['fecha'].dt.strftime('%Y-%m') == mes_actual]
            minutos_mes_actual = 30 * 24 * 60 # Aprox 43200

            col_k1, col_k2, col_k3 = st.columns(3)
            with col_k1:
                st.metric("Total Eventos Interrupción", len(df_mes))
            with col_k2:
                minutos_caidos = int(df_mes['duracion_min'].sum())
                horas_caidas = round(minutos_caidos / 60, 1)
                st.metric("Tiempo de Detención (Hrs)", f"{horas_caidas} h")
            with col_k3:
                # Contamos cuántos activos únicos existen mapeados en este contrato/empresa desde REGISTROS
                query_activos = "SELECT COUNT(DISTINCT identificador) as c FROM registros WHERE categoria != 'Personal'"
                params_activos = []
                if not is_master:
                    query_activos += " AND empresa_id=?"
                    params_activos.append(st.session_state.get('empresa_id', 0))
                else:
                    if empresa_id > 0:
                        query_activos += " AND empresa_id=?"
                        params_activos.append(empresa_id)
                if contrato_id > 0:
                    query_activos += " AND contrato_id=?"
                    params_activos.append(contrato_id)

                res_act = obtener_dataframe(db_path, query_activos, tuple(params_activos))
                total_equipos = res_act.iloc[0]['c'] if not res_act.empty else 0

                if total_equipos > 0:
                    min_totales = total_equipos * minutos_mes_actual
                    uptime = max(0, ((min_totales - minutos_caidos) / min_totales) * 100)
                    st.metric("Uptime / Disponibilidad Global", f"{uptime:.2f}%", help="Calculado sobre 30 días operacionales (24/7) de los equipos registrados.")
                else:
                    st.metric("Uptime / Disponibilidad Global", "N/A", help="No hay activos asignados registrados o filtrados.")

            st.divider()

            c1, c2 = st.columns(2)

            with c1:
                st.markdown("#### 🔝 Top Equipos con Fallas (Pareto)")
                pareto_data = df_ev.groupby('identificador').size().reset_index(name='frecuencia').sort_values('frecuencia', ascending=False)
                fig_pareto = px.bar(pareto_data, x='identificador', y='frecuencia',
                                   title="Frecuencia de Fallas por Equipo",
                                   color='frecuencia', color_continuous_scale='Reds')
                st.plotly_chart(fig_pareto, use_container_width=True)

            with c2:
                st.markdown("#### 📉 Distribución por Tipo de Falla")
                pie_data = df_ev.groupby('tipo_falla').size().reset_index(name='count')
                fig_pie = px.pie(pie_data, values='count', names='tipo_falla', title="Tipos de Falla más Recuentes", hole=0.4)
                st.plotly_chart(fig_pie, use_container_width=True)

            st.markdown("#### 📅 Tendencia Mensual de Eventos")
            df_ev['mes'] = df_ev['fecha'].dt.strftime('%Y-%m')
            tendencia_data = df_ev.groupby('mes').size().reset_index(name='eventos')
            fig_trend = px.line(tendencia_data, x='mes', y='eventos', markers=True,
                               title="Evolución de Fallas en el Tiempo",
                               line_shape='spline', render_mode='svg')
            st.plotly_chart(fig_trend, use_container_width=True)

    with tab_historico:
        st.markdown("### 📂 Histórico de Eventos y Exportación")

        if df_ev.empty:
            st.warning("No hay datos para exportar.")
        else:
            # Mostrar Tabla
            st.dataframe(df_ev.sort_values('fecha', ascending=False), use_container_width=True, hide_index=True)

            st.divider()
            col_exp1, col_exp2 = st.columns(2)

            with col_exp1:
                # Exportar a Excel
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df_ev.to_excel(writer, index=False, sheet_name='Historico_Confiabilidad')
                excel_data = output.getvalue()
                st.download_button(
                    label="📥 Descargar Histórico (Excel)",
                    data=excel_data,
                    file_name=f"Historico_CCE_{datetime.now().strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )

            with col_exp2:
                # Generar PDF de un evento específico
                df_ev['display_pdf'] = df_ev['fecha'].dt.strftime('%Y-%m-%d') + " - " + df_ev['identificador'] + " (" + df_ev['tipo_falla'] + ")"
                event_to_pdf = st.selectbox("🎯 Seleccionar Evento para Informe PDF:", df_ev['display_pdf'].tolist())

                if event_to_pdf:
                    # Recuperar fila seleccionada
                    row_pdf = df_ev[df_ev['display_pdf'] == event_to_pdf].iloc[0]
                    pdf_bytes = pdf_engine.generar('FALLA_CONFIABILIDAD', row_pdf.to_dict(), LOGO_APP, obtener_logo_cliente(st.session_state.filtros.get('empresa_nom')))

                    st.download_button(
                        label="📄 Descargar Informe PDF Técnico",
                        data=pdf_bytes,
                        file_name=f"Reporte_Tecnico_{row_pdf['identificador']}_{row_pdf['fecha'].strftime('%Y%m%d')}.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )

            # --- SECCIÓN DE ELIMINACIÓN (SOLO ADMINS) ---
            rol_usuario = st.session_state.get('role', '') # Corregido: 'role' en lugar de 'rol'
            if rol_usuario in ['Global Admin', 'Admin', 'Administrador']:
                st.divider()
                st.markdown("### 🗑️ Zona de Depuración (Administradores)")
                with st.expander("Haz clic aquí para gestionar la eliminación de registros"):
                    evento_a_eliminar = st.selectbox("⚠️ Seleccione el evento que desea eliminar PERMANENTEMENTE:",
                                                   ["-- Seleccione --"] + df_ev['display_pdf'].tolist(),
                                                   key="delete_event_sel")

                    if evento_a_eliminar != "-- Seleccione --":
                        row_del = df_ev[df_ev['display_pdf'] == evento_a_eliminar].iloc[0]
                        st.warning(f"¿Estás seguro de que deseas eliminar el registro del {row_del['fecha'].strftime('%Y-%m-%d')} para el equipo {row_del['identificador']}?")

                        if st.button("🔥 Confirmar ELIMINACIÓN DEFINITIVA", use_container_width=True, type="primary"):
                            try:
                                # 1. Borrar Foto Física si existe
                                if row_del['foto_path'] and os.path.exists(row_del['foto_path']):
                                    os.remove(row_del['foto_path'])

                                # 2. Borrar de la BD de forma segura
                                ejecutar_query(db_path, "DELETE FROM eventos_confiabilidad WHERE id = ?", (int(row_del['id']),), commit=True)

                                st.success("✅ Registro y archivo de evidencia eliminados con éxito.")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error al eliminar: {e}")
