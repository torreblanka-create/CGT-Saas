import os
from datetime import datetime

import pandas as pd
import streamlit as st

from src.infrastructure.archivos import sincronizar_directorios_desde_excel
from src.infrastructure.database import (
    ejecutar_query,
    normalizar_texto,
    obtener_dataframe,
    registrar_log,
)
from intelligence.agents.backup_engine import (
    crear_backup,
    obtener_listado_respaldos,
    restaurar_db,
)
from core.excel_master import (
    exportar_maestro_a_excel,
    obtener_contratos_por_empresa,
    obtener_listas_unicas,
    sincronizar_maestro_desde_excel,
)


def render_mantenimiento(db_path):
    st.markdown("<h2 style='color: var(--cgt-blue);'><i data-lucide='settings'></i> Herramientas de Mantenimiento</h2>", unsafe_allow_html=True)
    st.write("Panel técnico para la integridad de datos, seguridad y trazabilidad del sistema.")
    
    t1, t2 = st.tabs(["🛠️ Gestión e Integridad", "📜 Bitácora de Actividad"])

    with t1:
        st.divider()

    # --- 1. HERRAMIENTAS DE INTEGRIDAD ---
    st.markdown("### 🛠️ Integridad y Resiliencia")
    c1, c2 = st.columns(2)
    with c2:
        if os.path.exists(db_path):
            with open(db_path, "rb") as f:
                btn_label = "📥 Descargar Estructura SaaS" if "cgt_control" not in db_path else "📥 Descargar Maestro Global"
                st.download_button(btn_label, f, f"Backup_{os.path.basename(db_path)}", use_container_width=True, icon=":material/download:")

    st.markdown("<br>### 📦 Resiliencia SaaS (Respaldos)", unsafe_allow_html=True)
    cb1, cb2 = st.columns([1, 2])
    
    with cb1:
        st.write("Crea un punto de restauración inmediato para la instancia activa.")
        if st.button("📦 Crear Respaldo Ahora", use_container_width=True, type="primary"):
            with st.status("Generando respaldo...", expanded=True) as status:
                success, info = crear_backup(db_path, label="MANUAL", status_callback=status.write)
                if success:
                    status.update(label="✅ Respaldo exitoso", state="complete")
                    registrar_log(db_path, st.session_state.user_login, "DB_BACKUP_MANUAL", f"Archivo: {os.path.basename(info)}")
                    st.success("Copia de seguridad generada con éxito.")
                    st.rerun()
                else:
                    status.update(label="❌ Error en respaldo", state="error")
                    st.error(info)
    
    with cb2:
        backups = obtener_listado_respaldos(db_path)
        if not backups:
            st.info("No se registran respaldos para esta empresa aún.")
        else:
            selected_bk = st.selectbox("Historial de Restauración (Tenant):", 
                                     [f"{b['date']} - {b['name']} ({b['size']})" for b in backups[:10]])
            
            if st.button("🔥 Restaurar a este punto", use_container_width=True):
                bk_name = selected_bk.split(" - ")[1].split(" (")[0]
                bk_full_path = next(b['path'] for b in backups if b['name'] == bk_name)
                
                with st.status("Restaurando datos...", expanded=True) as status:
                    success, msg = restaurar_db(db_path, bk_full_path, status_callback=status.write)
                    if success:
                        status.update(label="✅ Sistema restaurado", state="complete")
                        registrar_log(db_path, st.session_state.user_login, "DB_RESTORE", f"Desde: {bk_name}")
                        st.success("Restauración completa. Reiniciando...")
                        import time; time.sleep(2)
                        st.rerun()
                    else:
                        status.update(label="❌ Error", state="error")
                        st.error(msg)

    st.markdown("<br>### 🧹 Utilidades Críticas (Limpieza)", unsafe_allow_html=True)
    cu1, cu2 = st.columns(2)
    with cu1:
        st.info("Borrar la caché resuelve problemas visuales de inconsistencia en listas desplegables.")
        if st.button("🔥 Purgar Memoria Temporaria", use_container_width=True, type="primary", icon=":material/cleaning_services:"):
            st.cache_data.clear()
            st.cache_resource.clear()
            st.success("Caché purgada con éxito.")
            import time; time.sleep(1)
            st.rerun()

    with cu2:
        st.info("Unifica empresas y contratos con nombres duplicados o mal escritos.")
        if st.button("🧼 Consolidar Maestros (Fantasmas)", use_container_width=True, icon=":material/auto_fix_high:"):
            with st.spinner("Limpiando base de datos..."):
                merged_count = 0
                df_emps = obtener_dataframe(db_path, "SELECT id, UPPER(nombre) as unom FROM empresas")
                if not df_emps.empty:
                    for unom, group in df_emps.groupby('unom'):
                        if len(group) > 1:
                            primary_id = int(group.iloc[0]['id'])
                            for _, row in group.iloc[1:].iterrows():
                                ghost_id = int(row['id'])
                                tables = ["registros", "contratos", "usuarios", "procedimientos", "reportes_incidentes"]
                                for tab in tables:
                                    try: ejecutar_query(db_path, f"UPDATE {tab} SET empresa_id = ? WHERE empresa_id = ?", (primary_id, ghost_id), commit=True)
                                    except: pass
                                ejecutar_query(db_path, "DELETE FROM empresas WHERE id = ?", (ghost_id,), commit=True)
                                merged_count += 1
                st.success(f"Se han consolidado {merged_count} registros fantasmas.")

    # --- 2. VACIADO DE CATEGORÍAS ---
    st.markdown("<br>### 🚨 Zonas de Peligro (Vaciado)", unsafe_allow_html=True)
    with st.expander("Acciones Irreversibles"):
        st.warning("⚠️ El vaciado eliminará de forma irreversible **TODOS LOS EXPEDIENTES Y EL LISTADO MAESTRO** de la categoría seleccionada.")
        # Mapeo de Etiquetas UI -> Categorías en Base de Datos
        mapeo_vaciado = {
            "---": [],
            "👷 Personal": ["Personal"],
            "🚛 Camionetas (Vehículo Liviano)": ["Vehiculo_Liviano"],
            "🚚 Camiones (Transporte)": ["Camion_Transporte"],
            "🏗️ Equipos Pesados (Maquinaria)": ["Equipo_Pesado"],
            "♻️ TODO MAQUINARIA Y VEHÍCULOS (Global)": ["Vehiculo_Liviano", "Camion_Transporte", "Equipo_Pesado", "Maquinaria Pesada & Vehículos"],
            "⛓️ Elementos de izaje": ["Elementos de izaje"],
            "🧰 Instrumentos y Metrología": ["Instrumentos y Metrología"],
            "🚨 Sistemas de Emergencia": ["Sistemas de Emergencia"],
            "🛡️ EPP": ["EPP"]
        }
        
        cat_del_label = st.selectbox("Categoría a Vaciar:", list(mapeo_vaciado.keys()))
        cats_to_delete = mapeo_vaciado[cat_del_label]
        
        if st.button("💥 EJECUTAR VACIADO ABSOLUTO 💥", use_container_width=True, disabled=(not cats_to_delete)):
            placeholders = ",".join(["?"] * len(cats_to_delete))
            # Eliminar de registros
            ejecutar_query(db_path, f"DELETE FROM registros WHERE categoria IN ({placeholders})", tuple(cats_to_delete), commit=True)
            # Eliminar de maestro_entidades (para que no vuelvan a aparecer)
            ejecutar_query(db_path, f"DELETE FROM maestro_entidades WHERE categoria IN ({placeholders})", tuple(cats_to_delete), commit=True)
            # Eliminar de horometros si aplica
            if any(c in cats_to_delete for c in ["Vehiculo_Liviano", "Camion_Transporte", "Equipo_Pesado"]):
                ejecutar_query(db_path, f"DELETE FROM horometros_actuales WHERE identificador IN (SELECT identificador FROM registros WHERE categoria IN ({placeholders}))", tuple(cats_to_delete), commit=True)
            
            st.error(f"Se han eliminado todos los datos de '{cat_del_label}'.")
            st.rerun()

    # --- ☢️ PROTOCOLO DE REINICIO TOTAL ---
    if st.session_state.role == "Global Admin":
        st.markdown("<br>### ☢️ Protocolo de Reinicio Total (Admin Global)", unsafe_allow_html=True)
        with st.expander("☢️ ÁREA RESTRINGIDA: WIPE TOTAL DE DATOS"):
            st.error("⚠️ Esta acción eliminará **TODOS** los datos operativos de la plataforma: registros, documentos, auditorías, planes de acción, salud y personal. Solo se conservará la estructura de Usuarios y Empresas.")
            
            with st.form("form_nuclear_reset"):
                st.write("Para proceder, ingrese su contraseña de administrador dos veces:")
                p1 = st.text_input("Contraseña de Administrador:", type="password")
                p2 = st.text_input("Confirme Contraseña:", type="password")
                
                if st.form_submit_button("☢️ INICIAR WIPE TOTAL DEL SISTEMA ☢️", type="primary", use_container_width=True):
                    if p1 != p2:
                        st.error("Las contraseñas no coinciden.")
                    elif not p1:
                        st.error("Debe ingresar su contraseña.")
                    else:
                        # Verificar contra DB
                        import bcrypt
                        res = ejecutar_query(db_path, "SELECT pw FROM usuarios WHERE username = ?", (st.session_state.user_login,))
                        if res and bcrypt.checkpw(p1.encode('utf-8'), res[0][0].encode('utf-8')):
                            # EJECUTAR WIPE
                            tablas_wipe = [
                                "registros", "maestro_entidades", "horometros_actuales", 
                                "historial_fallas", "planes_accion", "compliance_audits", 
                                "cumplimiento_documental", "evaluaciones_ambientales", 
                                "vigilancia_medica_trabajadores", "repositorio_minsal", 
                                "planes_gestion_salud", "ges_ambiental"
                            ]
                            for t in tablas_wipe:
                                try: ejecutar_query(db_path, f"DELETE FROM {t}", commit=True)
                                except: pass
                            
                            registrar_log(db_path, st.session_state.user_login, "NUCLEAR_RESET", "Wipe total de datos operativos ejecutado con éxito.")
                            st.success("💥 SISTEMA REINICIADO. Todos los datos operativos han sido eliminados.")
                            import time; time.sleep(3)
                            st.rerun()
                        else:
                            st.error("Contraseña incorrecta. Acceso denegado.")

        # --- ACCIONES DE MANTENIMIENTO ---
        st.markdown("### 🛠️ Acciones de Mantenimiento")
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            if st.button("🧹 Limpiar Caché del Sistema", use_container_width=True):
                st.cache_data.clear()
                st.success("Caché limpiada exitosamente.")
                st.rerun()
        st.divider()

        # --- BOTÓN NUCLEAR: RESET TOTAL DEL SISTEMA ---
        if st.session_state.role == "Global Admin":
            st.divider()
            st.markdown("#### ☢️ RESET MAESTRO DEL SISTEMA")
            st.error("Esta acción eliminará **TODOS LOS DATOS OPERATIVOS** de la plataforma (Registros, Auditorías, Reportes, etc.). Solo se mantendrán las Empresas, Contratos y Usuarios.")
            
            with st.popover("🚨 INICIAR SECUENCIA DE RESET TOTAL"):
                st.warning("Para proceder, ingresa tu contraseña de Administrador Global dos veces.")
                p1 = st.text_input("Contraseña (1):", type="password", key="reset_p1")
                p2 = st.text_input("Contraseña (2):", type="password", key="reset_p2")
                
                if st.button("🧨 CONFIRMAR DESTRUCCIÓN DE DATOS", type="primary", use_container_width=True):
                    if p1 != p2:
                        st.error("Las contraseñas no coinciden.")
                    else:
                        import bcrypt
                        # Verificar contra la DB
                        res = ejecutar_query(db_path, "SELECT pw FROM usuarios WHERE username = ?", (st.session_state.user_login,))
                        if res and bcrypt.checkpw(p1.encode('utf-8'), res[0][0].encode('utf-8')):
                            # SECUENCIA DE DESTRUCCIÓN
                            tablas_a_limpiar = [
                                "registros", "maestro_entidades", "historial_fallas", "notificaciones_ultron",
                                "reportes_incidentes", "procedimientos", "capacitaciones", "asistencia_capacitacion",
                                "entregas_epp_actas", "entregas_epp_items", "registros_art", "planes_accion",
                                "evidencias_planes", "trazabilidad_documental", "auditorias_resso", "compliance_audits",
                                "compliance_gaps", "eventos_confiabilidad", "alertas_automaticas", "metricas_sistema",
                                "checklists_registros", "horometros_actuales", "registro_torques"
                            ]
                            for tabla in tablas_a_limpiar:
                                try: ejecutar_query(db_path, f"DELETE FROM {tabla}", commit=True)
                                except: pass
                            
                            registrar_log(db_path, st.session_state.user_login, "NUCLEAR_RESET", "Se ha realizado un reset total de datos operativos.")
                            st.success("💥 Sistema reseteado a cero. Redirigiendo...")
                            import time; time.sleep(2)
                            st.rerun()
                        else:
                            st.error("Contraseña incorrecta.")

    # --- 3. CARGA MASIVA ---
    st.divider()
    st.markdown("### 📊 Ingesta de Datos Maestros (Carga Masiva)")
    st.info("Paso 1: Seleccione destino. Paso 2: Suba el archivo Excel.")

    ci1, ci2 = st.columns(2)
    with ci1:
        emp_sync = st.selectbox("Empresa Destino:", obtener_listas_unicas("EMPRESA"), key="m_emp")
    with ci2:
        con_sync = st.selectbox("Contrato Destino:", obtener_contratos_por_empresa(emp_sync) if emp_sync else [], key="m_con")

    archivo = st.file_uploader("📥 Subir Matriz Unificada", type=["xlsx", "xls"])

    c_btn1, c_btn2 = st.columns(2)
    with c_btn1:
        if st.button("🚀 Inyectar Datos a Producción", use_container_width=True, disabled=not (emp_sync and con_sync and archivo)):
            e_id = ejecutar_query(db_path, "SELECT id FROM empresas WHERE nombre = ?", (normalizar_texto(emp_sync),))
            if e_id:
                c_id = ejecutar_query(db_path, "SELECT id FROM contratos WHERE empresa_id = ? AND nombre_contrato = ?", (e_id[0][0], normalizar_texto(con_sync)))
                if c_id:
                    success, msg = sincronizar_maestro_desde_excel(e_id[0][0], c_id[0][0], archivo)
                    if success: st.success(msg)
                    else: st.error(msg)
    with c_btn2:
        df_exp = exportar_maestro_a_excel()
        if not df_exp.empty:
            import io
            out = io.BytesIO()
            df_exp.to_excel(out, index=False)
            st.download_button("📥 Exportar Maestro Actual", out.getvalue(), "Maestro_Export.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)

    with t2:
        st.markdown("### 📜 Historial de Cambios y Accesos")
        st.write("Trazabilidad completa de las acciones realizadas en la plataforma.")
        
        # Filtros de Bitácora
        c_f1, c_f2 = st.columns(2)
        with c_f1:
            f_usr = st.text_input("Filtrar por Usuario:", placeholder="Ej: miguel")
        with c_f2:
            f_acc = st.selectbox("Filtrar por Acción:", ["Todas", "LOGIN", "LOGOUT", "UPLOAD", "DELETE", "UPDATE", "DELETE_SNAPSHOT"])

        query = "SELECT fecha, usuario, accion, detalle FROM logs_actividad WHERE 1=1"
        params = []
        if f_usr:
            query += " AND usuario LIKE ?"
            params.append(f"%{f_usr}%")
        if f_acc != "Todas":
            query += " AND accion = ?"
            params.append(f_acc)
        
        query += " ORDER BY fecha DESC LIMIT 500"
        
        df_logs = obtener_dataframe(db_path, query, params)
        
        if not df_logs.empty:
            st.dataframe(df_logs, use_container_width=True, hide_index=True)
            
            # Exportar logs
            import io
            out_logs = io.BytesIO()
            df_logs.to_excel(out_logs, index=False)
            st.download_button("📥 Descargar Reporte de Auditoría", out_logs.getvalue(), "Bitacora_Auditoria.xlsx", use_container_width=True)
        else:
            st.info("No se encontraron registros en la bitácora con los filtros seleccionados.")
