import io
import json
import os
import re
import zipfile
from datetime import datetime

import pandas as pd
import streamlit as st

from config.config import load_dynamic_config
from src.infrastructure.database import ejecutar_query, obtener_dataframe
from core.utils import registrar_no_conformidad_automatica
from core.resso_components import (
    guardar_evidencia_local,
    render_cphs,
    render_evidencia_simple,
    render_modulo_bel,
    render_planes_emergencia,
    render_semaforo_difusion,
    render_titulo_vi,
)


def extract_options(criterio_text):
    """Extrae los porcentajes mencionados en el texto del criterio para usarlos como opciones."""
    matches = re.findall(r'(\d+)\s*%', criterio_text)
    if matches:
        opts = sorted(list(set([int(m) for m in matches])), reverse=True)
        return ['N/A'] + [str(o) for o in opts]
    return ['N/A', '100', '50', '30', '0']

def render_auditoria_resso(db_path, filtros):
    st.markdown("## 📋 Auditoría Digital RESSO (45 Puntos)")
    st.markdown("Sistema de evaluación de cumplimiento basado en el estándar corporativo RESSO.")

    # Cargar datos JSON
    json_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "resso_points.json")
    if not os.path.exists(json_path):
        st.error(f"No se encontró el archivo de configuración de puntos RESSO en {json_path}")
        return

    with open(json_path, 'r', encoding='utf-8') as f:
        secciones = json.load(f)

    # --- CABECERA DE LA AUDITORÍA ---
    with st.container():
        st.markdown("<div class='premium-card'>", unsafe_allow_html=True)
        # Filtros de empresa/contrato
        emp_id = filtros.get('empresa_id', 0)
        con_id = filtros.get('contrato_id', 0)
        emp_nom = filtros.get('empresa_nom', 'Empresa Default')
        con_nom = filtros.get('contrato_nom', 'Contrato Default')

        st.markdown("### 📋 1. ANTECEDENTES GENERALES")
        st.caption("Complete los antecedentes de la empresa y contrato para la emisión de la auditoría.")

        c1, c2 = st.columns(2)
        c1.text_input("Nombre EECC", value=emp_nom, disabled=True)
        rut_eecc = c2.text_input("RUT EECC", value="")

        c3, c4 = st.columns(2)
        c3.text_input("Nombre Contrato", value=con_nom, disabled=True)
        n_contrato = c4.text_input("N° Contrato", value="")

        c5, c6 = st.columns(2)
        fecha_inicio = c5.date_input("Fecha Inicio Contrato", value=datetime.today())
        fecha_termino = c6.date_input("Fecha de Termino del Contrato", value=datetime.today())

        c7, c8 = st.columns(2)
        gerencia = c7.text_input("Gerencia", value="")

        # Fetch active personnel
        query_w = "SELECT DISTINCT identificador, nombre FROM registros WHERE categoria='Personal' AND empresa_id=? AND contrato_id=?"
        df_w = obtener_dataframe(db_path, query_w, (emp_id, con_id))

        if not df_w.empty:
            lista_personal = [""] + sorted(df_w['nombre'].tolist())
            dotacion_calc = len(df_w)
        else:
            lista_personal = [""]
            dotacion_calc = 0

        dotacion = c8.number_input("Dotación Total (Autocalculada desde Trazabilidad)", min_value=0, value=dotacion_calc)

        st.markdown("**Responsables:**")
        c9, c10, c11 = st.columns(3)

        admin_opt = c9.selectbox("Administrador EECC", options=lista_personal + ["✏️ Ingresar Manualmente..."])
        if admin_opt == "✏️ Ingresar Manualmente...":
            admin_eecc = c9.text_input("Escribir Nombre Admin EECC")
        else:
            admin_eecc = admin_opt

        correo_admin_eecc = c9.text_input("Correo Admin EECC", value="")

        exp_opt = c10.selectbox("Experto Prevención EECC", options=lista_personal + ["✏️ Ingresar Manualmente..."])
        if exp_opt == "✏️ Ingresar Manualmente...":
            experto_eecc = c10.text_input("Escribir Nombre Experto")
        else:
            experto_eecc = exp_opt

        correo_experto = c10.text_input("Correo Experto", value="")

        admin_cod = c11.text_input("Administrador Codelco", value="")
        correo_cod = c11.text_input("Correo Codelco", value="")

        st.markdown("---")
        ca, cb, cc = st.columns(3)
        fecha = ca.date_input("Fecha de Auditoría", datetime.now())
        auditor = cb.text_input("Auditor / Evaluador", value=st.session_state.get('username', ''))
        st.markdown("</div>", unsafe_allow_html=True)

    # Inicializar estado para los puntajes si no existe
    if 'resso_scores' not in st.session_state:
        st.session_state.resso_scores = {}

    # --- PESTAÑAS PRINCIPALES TIPO DS 594 ---
    tab_ejecutar, tab_historial, tab_brechas_global, tab_export = st.tabs([
        "📝 Ejecutar Auditoría",
        "🗃️ Historial de Informes",
        "🎯 Gestión de Brechas RESSO",
        "📂 Data Room (Exportar)"
    ])

    with tab_ejecutar:
        st.markdown("### 📝 Puntos a Evaluar")

        # Tabs de Ejecución Interna (Para no contaminar la principal)
        subtab_eval, subtab_lod, subtab_plan = st.tabs([
            "🔍 Evaluación General",
            "📨 Check LOD / Cartas",
            "🎯 Plan de Acción en Vivo"
        ])

        with subtab_eval:
            st.info("Seleccione el porcentaje de cumplimiento para Documental y Terreno basándose en los criterios mostrados.")

            for i_sec, seccion in enumerate(secciones):
                if not seccion['preguntas']:
                    continue

                col_sec_hdr, col_sec_na = st.columns([5, 1])
                # Redujimos la fuente y dimos más ancho a la columna para evitar el quiebre de línea antiestético
                col_sec_hdr.markdown(f"<h5 style='margin-top: 0.4rem; margin-bottom: 0px; font-size: 1.15rem;'>🔹 {seccion['letra']} - {seccion['titulo']}</h5>", unsafe_allow_html=True)
                seccion_na = col_sec_na.checkbox(
                    "⛔ Sección N/A",
                    key=f"na_sec_resso_{i_sec}",
                    help="Marca toda esta letra/sección como No Aplica de una vez"
                )

                if seccion_na:
                    st.caption("✨ _Esta sección ha sido silenciada porque no aplica para la auditoría._")

                with st.expander(f"🔽 Evaluar / Revisar los {len(seccion['preguntas'])} ítems de esta sección", expanded=False):
                    for p in seccion['preguntas']:
                        q_id = f"q_{p['numero']}"
                        opts = extract_options(p['criterio'])

                        with st.container(border=True):
                            st.markdown(f"**Pto {p['numero']}:** {p['texto']} (Ponderación: {p['ponderacion']*100:.2f}%)")

                            with st.expander("📖 Ver Criterios de Evaluación detallados"):
                                st.markdown(f"```text\n{p['criterio']}\n```")

                            # --- SECCIÓN: FORMATO TIPO (ESTÁNDAR) ---
                            fmt_query = "SELECT id, nombre_archivo, path_archivo FROM audit_formatos_tipo WHERE punto_id=? AND (empresa_id=0 OR empresa_id=?)"
                            fmt_result = obtener_dataframe(db_path, fmt_query, (str(p['numero']), emp_id))

                            st.markdown("<div style='background-color: rgba(0, 188, 212, 0.05); padding: 10px; border-radius: 8px; margin-bottom: 15px;'>", unsafe_allow_html=True)
                            c_d1, c_d2 = st.columns([2,1])
                            if not fmt_result.empty:
                                fmt_row = fmt_result.iloc[-1]
                                f_path = fmt_row['path_archivo']
                                f_name = fmt_row['nombre_archivo']
                                if os.path.exists(f_path):
                                    with open(f_path, "rb") as f_std:
                                        c_d1.download_button(f"📥 Descargar Formato Estándar", f_std, file_name=f_name, key=f"dl_fmt_{q_id}", help=f"Archivo: {f_name}")
                                else:
                                    c_d1.caption("⚠️ Formato registrado no encontrado en el servidor.")
                            else:
                                c_d1.markdown("*Ningún formato tipo cargado para este punto.*", unsafe_allow_html=True)

                            if st.session_state.get('role') in ['Global Admin', 'Admin']:
                                with c_d2.popover("⚙️ Gestionar Formato", use_container_width=True):
                                    st.markdown("Sube una plantilla en Word/PDF/Excel:")
                                    uploaded_fmt = st.file_uploader("", key=f"up_fmt_{q_id}", label_visibility="collapsed")
                                    if uploaded_fmt:
                                        if st.button("Guardar Formato", key=f"btn_fmt_{q_id}", type="primary", use_container_width=True):
                                            fmt_dir = os.path.join(os.path.dirname(db_path), "formatos_auditoria")
                                            os.makedirs(fmt_dir, exist_ok=True)
                                            s_path = os.path.join(fmt_dir, f"pto_{p['numero']}_{uploaded_fmt.name}")
                                            with open(s_path, "wb") as fu:
                                                fu.write(uploaded_fmt.getbuffer())
                                            up_emp_id = st.session_state.get('empresa_id', 0)
                                            try: ejecutar_query(db_path, "DELETE FROM audit_formatos_tipo WHERE punto_id=? AND empresa_id=?", (str(p['numero']), up_emp_id))
                                            except: pass
                                            ejecutar_query(db_path, "INSERT INTO audit_formatos_tipo (punto_id, empresa_id, nombre_archivo, path_archivo) VALUES (?,?,?,?)", (str(p['numero']), up_emp_id, uploaded_fmt.name, s_path), commit=True)
                                            st.rerun()
                            st.markdown("</div>", unsafe_allow_html=True)
                            # --- FIN FORMATO TIPO ---

                            col_doc, col_ter = st.columns(2)

                            if seccion_na:
                                # Forzar N/A y deshabilitar
                                doc_val = col_doc.selectbox(f"Revisión Documental (%) - {q_id}", options=opts, key=f"doc_{q_id}", index=0, disabled=True)
                                ter_val = col_ter.selectbox(f"Auditoría Terreno (%) - {q_id}", options=opts, key=f"ter_{q_id}", index=0, disabled=True)
                            else:
                                doc_val = col_doc.selectbox(f"Revisión Documental (%) - {q_id}", options=opts, key=f"doc_{q_id}")
                                ter_val = col_ter.selectbox(f"Auditoría Terreno (%) - {q_id}", options=opts, key=f"ter_{q_id}")

                            # --- MOTOR DE MÓDULOS AVANZADOS ---
                            evidencia_generada = None

                            # Difusión y Prueba cruzados (Semáforo)
                            if p['numero'] in [2, 4, 6, 9, 14, 19, 20, 36, 37]:
                                req_map = {
                                    2: "Políticas Corporativas",
                                    4: "IPER Legal",
                                    6: "IPER / Matriz Riesgos",
                                    9: "Mapas Higiénicos",
                                    14: "Registro Aprendizajes e Incidentes",
                                    19: "Simulacros y Difusión",
                                    20: "IRL información de riesgos laborales",
                                    36: "Difusión de Obligaciones (Tít. IX)",
                                    37: "Reglamento interno de Orden, Higiene y Seg"
                                }
                                req_str = req_map.get(p['numero'], f"Requisito Punto {p['numero']}")
                                path_bd = render_semaforo_difusion(p['numero'], req_str, filtros, db_path)
                                if path_bd:
                                    st.session_state[f"evid_path_{q_id}"] = path_bd

                            elif p['numero'] == 21: # BEL
                                obj_list = render_modulo_bel(q_id, emp_nom, con_nom)
                                st.session_state[f"evid_objlist_{q_id}"] = obj_list

                            elif p['numero'] == 18: # Planes Emergencia
                                obj_list = render_planes_emergencia(q_id, emp_nom, con_nom)
                                st.session_state[f"evid_objlist_{q_id}"] = obj_list

                            elif p['numero'] == 42: # Paritario CPHS
                                obj_list = render_cphs(q_id, emp_nom, con_nom)
                                st.session_state[f"evid_objlist_{q_id}"] = obj_list

                            elif p['numero'] == 24: # Requisitos Título VI
                                obj_list = render_titulo_vi(q_id, emp_nom, con_nom)
                                st.session_state[f"evid_objlist_{q_id}"] = obj_list

                            else: # Simple Extender
                                evd_files = render_evidencia_simple(q_id, emp_nom, con_nom)
                                if evd_files:
                                    st.session_state[f"evid_objlist_{q_id}"] = evd_files

        # --- PESTAÑA LOD DEDICADA ---
        with subtab_lod:
            st.markdown("#### 📨 Documentos Obligatorios de Enviar Vía LOD / Carta Contractual")
            st.info("El RESSO exige que múltiples eventos se formalicen explícitamente a través del Administrador de Codelco.")

            # Filter questions dynamically if they mention LOD
            lod_questions = []
            for s in secciones:
                for px in s['preguntas']:
                    txt_eval = (px['texto'] + px['criterio']).upper()
                    if any(k in txt_eval for k in ["LOD", "LIBRO DE OBR", "CARTA CONTRACTUAL"]):
                        lod_questions.append(px)

            st.markdown(f"**Se encontraron {len(lod_questions)} obligaciones de notificación formal:**")

            lod_templates = {
                5: "Estimado Administrador de Codelco / VP,\nPor medio de la presente, informamos el levantamiento y cierre de las observaciones emanadas por el organismo fiscalizador correspondientes a [...]. Se adjuntan las evidencias respectivas para su conocimiento y fines pertinentes.",
                7: "Estimado Administrador de Codelco / VP,\nAdjunto a la presente remitimos el Programa de Seguridad y Salud en el Trabajo (SST) de nuestra empresa, el cual se encuentra debidamente validado por nuestro organismo administrador de la Ley 16.744, dando cumplimiento a lo exigido en el estándar RESSO.",
                26: "Estimado Administrador de Codelco / VP,\nInformamos que hemos gestionado y cerrado las observaciones detectadas por SERNAGEOMIN en la pasada fiscalización. Adjunto remitimos el plan de acción con las evidencias de cierre para su revisión.",
                31: "Estimado Administrador de Codelco / VP,\nCumpliendo con los lineamientos del RESSO, comunicamos a usted y a la Dirección de Seguridad y Salud en el Trabajo los resultados de la reciente fiscalización por parte de [ENTIDAD/ORGANISMO]. Adjuntamos informe detallado.",
                33: "Estimado Administrador de Codelco / VP,\nPor medio de la presente, solicitamos formalmente la notificación de la categorización de nuestra empresa de acuerdo a los criterios vigentes en materia de Seguridad y Salud Ocupacional.",
                35: "Estimado Administrador de Codelco / VP,\nInformamos la ocurrencia de un incidente [CLASIFICACIÓN] en nuestras instalaciones/faena. Se están aplicando los lineamientos del Procedimiento de Gestión de Incidentes. Adjuntamos reporte preliminar/flash.",
                39: "Estimado Administrador de Codelco / VP,\nInformamos la ejecución de trabajos que implican Riesgos Inherentes Altos en nuestra área de responsabilidad. Adjuntamos nuestro plan de trabajo y los métodos seguros (PTS) que se implementarán para el desarrollo de la tarea crítica.",
                41: "Estimado Administrador de Codelco / VP,\nAdjuntamos la declaración formal de las empresas subcontratistas que prestarán servicios bajo nuestro alero en el presente contrato, incluyendo las actas de arranque formal y toma de conocimiento del RESSO."
            }

            for px in lod_questions:
                with st.expander(f"📖 **Pto. {px['numero']}** - " + px['texto'][:120] + "..."):
                    st.checkbox("Marcar como Verificado / Enviado", key=f"chk_lod_{px['numero']}")
                    msg = lod_templates.get(px['numero'], f"Estimado Administrador de Codelco / VP,\nJunto con saludar, y dando cumplimiento a lo estipulado en el estándar corporativo RESSO (Punto {px['numero']}), adjuntamos la documentación formal asociada al requerimiento. Quedamos a su disposición.")
                    st.text_area("💡 Sugerencia de Redacción (Puedes editar antes de copiar):", value=msg, height=130, key=f"txt_lod_{px['numero']}")

            st.caption("Esta pestaña es un check referencial y de ayuda para el administrador/auditor.")

        # --- PESTAÑA PLAN DE BRECHAS Y ACCIÓN ---
        with subtab_plan:
            st.markdown("#### 🎯 Plan de Brechas y Tratamiento (Evaluación actual)")
            st.info("Este radar detecta en tiempo real los puntos evaluados con 0% o con personal faltante. Define el tratamiento para justificar la brecha temporal.")

            brechas_vivas = 0
            for s in secciones:
                for p in s['preguntas']:
                    q_num = p['numero']
                    q_id = f"q_{q_num}"

                    faltantes = st.session_state.get(f"brechas_q_{q_num}", [])
                    doc_val = st.session_state.get(f"doc_{q_id}", "")
                    ter_val = st.session_state.get(f"ter_{q_id}", "")

                    # Heurística temporal de brecha mientras se llena el formulario
                    es_brecha = False
                    razon_brecha = ""

                    if faltantes:
                        es_brecha = True
                        razon_brecha = f"Personal faltante por capacitar ({len(faltantes)} personas)."
                    elif doc_val == "0" and ter_val == "0":
                        es_brecha = True
                        razon_brecha = "Punto evaluado preventivamente con 0% (Crítico)."

                    if es_brecha:
                        brechas_vivas += 1
                        with st.expander(f"⚠️ Brecha Detectada: Pto. {q_num} - {razon_brecha}", expanded=True):
                            st.markdown(f"**Requisito:** {p['texto']}")
                            if faltantes:
                                st.caption(f"Faltan: {', '.join(faltantes[:3])}...")

                            c1, c2 = st.columns([3, 1])
                            c1.text_area("✍️ Definir Plan de Acción / Tratamiento:", key=f"plan_accion_{q_num}")
                            c2.date_input("📅 Fecha Compromiso:", key=f"fecha_accion_{q_num}")

            if brechas_vivas == 0:
                st.success("¡Excelente! No se han detectado brechas de personal ni notas críticas en la evaluación hasta el momento.")

        st.markdown("---")
        submit_btn = st.button("✅ Calcular y Guardar Auditoría", type="primary", use_container_width=True)

        if submit_btn:
            # Calcular resultados
            puntaje_total_ponderado = 0.0
            max_ponderacion_posible = 0.0
            resultados_json = {}

            # Guardamos la metadata estructural
            resultados_json["antecedentes_generales"] = {
                "rut_eecc": rut_eecc,
                "n_contrato": n_contrato,
                "fecha_inicio": str(fecha_inicio),
                "fecha_termino": str(fecha_termino),
                "gerencia": gerencia,
                "dotacion": dotacion,
                "admin_eecc": admin_eecc,
                "correo_admin_eecc": correo_admin_eecc,
                "experto_eecc": experto_eecc,
                "correo_experto": correo_experto,
                "admin_codelco": admin_cod,
                "correo_codelco": correo_cod
            }

            for seccion in secciones:
                for p in seccion['preguntas']:
                    q_id = f"q_{p['numero']}"
                    doc_v = st.session_state.get(f"doc_{q_id}", 'N/A')
                    ter_v = st.session_state.get(f"ter_{q_id}", 'N/A')

                    def extract_pct(text):
                        if text == 'N/A': return None
                        match = re.search(r'(\d+(?:\.\d+)?)%', text)
                        return float(match.group(1)) if match else 0.0

                    doc_num = extract_pct(doc_v)
                    ter_num = extract_pct(ter_v)

                    # Calcular promedio de la pregunta
                    if doc_num is not None and ter_num is not None:
                        promedio_q = (doc_num + ter_num) / 2.0
                    elif doc_num is not None:
                        promedio_q = doc_num
                    elif ter_num is not None:
                        promedio_q = ter_num
                    else:
                        promedio_q = None # N/A completo

                    if promedio_q is not None:
                        max_ponderacion_posible += p['ponderacion']
                        puntaje_ponderado_q = (promedio_q / 100.0) * p['ponderacion']
                        puntaje_total_ponderado += puntaje_ponderado_q

                        # Get faltantes for this question, if any
                        faltantes_dif = st.session_state.get(f"brechas_q_{p['numero']}", [])

                        # Get plan de accion and fecha de accion
                        plan_accion_val = st.session_state.get(f"plan_accion_{p['numero']}", "")
                        fecha_accion_val = st.session_state.get(f"fecha_accion_{p['numero']}", None)

                        resultados_json[f"Punto_{p['numero']}"] = { # Changed q_id to Punto_{p['numero']} for consistency
                            "documental": doc_v,
                            "terreno": ter_v,
                            "promedio": promedio_q,
                            "ponderado_obtenido": puntaje_ponderado_q,
                            "texto_pregunta": p['texto'],
                            "obtenido": promedio_q, # Assuming 'obtenido' refers to the average score
                            "maximo": 100, # Max score for a question is 100%
                            "ponderacion_pregunta": p['ponderacion'], # Store the question's weight
                            "observaciones": "", # Placeholder for future observations
                            "evidencias": [], # Will be populated below
                            "faltantes_difusion": faltantes_dif,
                            "plan_accion": plan_accion_val,
                            "fecha_accion": str(fecha_accion_val) if fecha_accion_val else ""
                        }

                        # Extraer y grabar en JSON las evidencias temporales
                        if f"evid_path_{q_id}" in st.session_state:
                            resultados_json[f"Punto_{p['numero']}"]["evidencias"].append(st.session_state[f"evid_path_{q_id}"])

                        if f"evid_objlist_{q_id}" in st.session_state:
                            obj_list = st.session_state[f"evid_objlist_{q_id}"]
                            for ev_obj in obj_list:
                                if ev_obj is not None:
                                    path_save = guardar_evidencia_local(ev_obj, emp_nom, con_nom, p['numero'], p['texto'][:30])
                                    resultados_json[q_id]["evidencias"].append(path_save)

            # Normalizar al 100% en caso de N/A en algunas preguntas
            if max_ponderacion_posible > 0:
                resultado_final_pct = (puntaje_total_ponderado / max_ponderacion_posible) * 100.0
            else:
                resultado_final_pct = 0.0

            # Clasificación
            if resultado_final_pct >= 90:
                clasificacion = "Aceptable"
            elif resultado_final_pct >= 75:
                clasificacion = "Moderado"
            else:
                clasificacion = "Inaceptable"

            # Guardar en BD (Sobrescribe si ya existe una auditoría hoy para esta empresa/contrato)
            datos_str = json.dumps(resultados_json)
            try:
                fecha_str = fecha.strftime("%Y-%m-%d")
                audit_existente = ejecutar_query(db_path, "SELECT id FROM auditorias_resso WHERE empresa_id=? AND contrato_id=? AND fecha=?", (emp_id, con_id, fecha_str))

                if audit_existente:
                    audit_id = audit_existente[0] if not isinstance(audit_existente[0], (list, tuple)) else audit_existente[0][0]
                    ejecutar_query(db_path, '''
                        UPDATE auditorias_resso 
                        SET auditor=?, datos_json=?, puntaje_final=?, clasificacion=?, estado=?
                        WHERE id=?
                    ''', (auditor, datos_str, resultado_final_pct, clasificacion, "Actualizada", audit_id), commit=True)
                    st.success(f"✅ Auditoría RESSO actualizada. Puntaje: {resultado_final_pct:.1f}% ({clasificacion})")
                else:
                    ejecutar_query(db_path, '''
                        INSERT INTO auditorias_resso 
                        (fecha, auditor, empresa, contrato, datos_json, puntaje_final, clasificacion, estado, empresa_id, contrato_id)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (fecha_str, auditor, emp_nom, con_nom, datos_str, resultado_final_pct, clasificacion, "Completada", emp_id, con_id), commit=True)
                    st.success(f"✅ Auditoría RESSO Guardada. Puntaje: {resultado_final_pct:.1f}% ({clasificacion})")

                # ➔ Gobernanza: No Conformidad automática si clasificación es Inaceptable
                if clasificacion == "Inaceptable":
                    ok_nc, msg_nc = registrar_no_conformidad_automatica(
                        db_path,
                        origen="Auditoría RESSO (Codelco)",
                        descripcion=f"RESSO obtuvo {resultado_final_pct:.1f}% — clasificado como Inaceptable. "
                                    f"Auditor: {auditor}. Empresa: {emp_nom} / Contrato: {con_nom}.",
                        responsable=auditor,
                        empresa_id=emp_id,
                        contrato_id=con_id
                    )
                    if ok_nc:
                        st.warning("⚠️ NCR automática generada en Gobernanza & SGI por puntaje Inaceptable.")

                st.session_state['last_audit_result'] = {
                    "puntaje": resultado_final_pct,
                    "clasificacion": clasificacion
                }
                st.rerun()
            except Exception as e:
                st.error(f"Error al guardar: {e}")

    # Mostrar resultado de la última auditoría procesada en sesión
    if 'last_audit_result' in st.session_state:
        res = st.session_state['last_audit_result']
        st.markdown("### 📊 Resultado Obtenido")
        color = "#10B981" if res['clasificacion'] == 'Aceptable' else "#F59E0B" if res['clasificacion'] == 'Moderado' else "#EF4444"

        st.markdown(f"""
        <div style="background-color: {color}20; border-left: 5px solid {color}; padding: 20px; border-radius: 5px; margin-top: 10px;">
            <h2 style="color: {color}; margin: 0;">{res['puntaje']:.1f}% - {res['clasificacion']}</h2>
            <p style="margin-top: 10px; font-size: 1.1em;">
                De acuerdo con la evaluación realizada y la evidencia presentada, el sistema de gestión obtiene una clasificación <strong>{res['clasificacion']}</strong>.
            </p>
        </div>
        """, unsafe_allow_html=True)

    with tab_historial:
        st.markdown("### 🗃️ Historial de Auditorías RESSO")
        df_historial = obtener_dataframe(db_path, "SELECT id, fecha, auditor, empresa_id, puntaje_final, clasificacion FROM auditorias_resso WHERE empresa_id = ?", (filtros.get('empresa_id', 0),))
        if not df_historial.empty:
            df_historial['puntaje_final'] = df_historial['puntaje_final'].apply(lambda x: f"{x:.1f}%")

            # UI Selector para borrar
            df_historial.insert(0, "Seleccionar", False)
            st.markdown("**Selecciona auditorías de la tabla inferior para eliminarlas (Peligro).**")
            edited_df = st.data_editor(
                df_historial,
                hide_index=True,
                column_config={"Seleccionar": st.column_config.CheckboxColumn("Seleccionar", default=False)},
                disabled=["id", "fecha", "auditor", "empresa", "puntaje_final", "clasificacion"],
                use_container_width=True
            )

            seleccionados_para_borrar = edited_df[edited_df['Seleccionar'] == True]['id'].tolist()
            if seleccionados_para_borrar:
                if st.button(f"🗑️ Eliminar {len(seleccionados_para_borrar)} Auditoría(s) permanentemente", type="primary"):
                    placeholders = ','.join(['?'] * len(seleccionados_para_borrar))
                    ejecutar_query(db_path, f"DELETE FROM auditorias_resso WHERE id IN ({placeholders})", tuple(seleccionados_para_borrar), commit=True)
                    st.success("Auditorías eliminadas. Actualizando...")
                    st.rerun()
        else:
            st.info("No hay auditorías registradas para esta empresa.")

    with tab_brechas_global:
        st.markdown("#### 🎯 Seguimiento Global de Brechas RESSO")

        if not df_historial.empty:
            audit_id_brechas = st.selectbox("Selecciona una auditoría histórica para cargar y revisar su Plan de Brechas:", ["- Seleccionar -"] + df_historial['id'].tolist())

            if audit_id_brechas != "- Seleccionar -":
                df_audi = obtener_dataframe(db_path, "SELECT datos_json FROM auditorias_resso WHERE id = ?", (audit_id_brechas,))
                if not df_audi.empty:
                    datos = json.loads(df_audi.iloc[0]['datos_json'])

                    with st.expander(f"📊 Reporte de Brechas Guardado - Auditoría #{audit_id_brechas}", expanded=True):
                        st.info("Este reporte consolida a todo el personal detectado como ausente en los puntos de difusión obligatoria, y los puntos críticos reportados.")

                        brechas_detectadas = False
                        for key, val in datos.items():
                            if key.startswith("Punto_"):
                                num = key.split("_")[1]
                                texto = val.get("texto_pregunta", f"Punto {num}")
                                faltantes = val.get("faltantes_difusion", [])
                                obtenido = val.get("obtenido", 0)
                                maximo = val.get("maximo", 0)
                                plan_accion = val.get("plan_accion", "").strip()
                                fecha_accion = val.get("fecha_accion", "")

                                # Condición de Brecha: Tiene personal faltante o sacó 0% de puntaje siendo un punto evaluado
                                if faltantes or (obtenido == 0 and maximo > 0):
                                    brechas_detectadas = True
                                    st.markdown(f"**🔴 Punto {num}:** {texto[:100]}...")

                                    if plan_accion:
                                        st.info(f"🟢 **En Tratamiento:** {plan_accion} (Plazo: {fecha_accion})")
                                    else:
                                        st.warning(f"⚠️ **Sin Plan de Acción definido:** Esta brecha está expuesta a multas o tarjetas rojas.")

                                    if faltantes:
                                        st.markdown(f"**Personal Faltante por Capacitar/Difundir ({len(faltantes)} trabajadores):**")
                                        # Render in columns for compactness
                                        c1, c2 = st.columns(2)
                                        mid = len(faltantes) // 2 + 1
                                        c1.code("\n".join(faltantes[:mid]))
                                        if len(faltantes) > mid:
                                            c2.code("\n".join(faltantes[mid:]))
                                    elif obtenido == 0:
                                        st.error(f"Brecha Documental: Requisito evaluado en 0%. Observaciones: {val.get('observaciones', 'Ninguna')}")
                                    st.write("---")

                        if not brechas_detectadas:
                            st.success("Felicidades! Esta auditoría no arrojó ninguna brecha de personal ni puntos en 0%.")

        else:
            st.info("No hay auditorías registradas para esta empresa.")

    with tab_export:
        st.markdown("### 📂 Data Room (Espejado Virtual de Auditoría)")
        st.info("Visualización jerárquica del cumplimiento RESSO organizada por los 6 Pilares del SGI.")

        # Mapeo de Puntos RESSO a los 6 Pilares
        PILAR_MAP = {
            "1. CONTROL OPERATIVO": [46],
            "2. SISTEMA DE GESTIÓN (SGI)": [0, 1, 2, 3, 7, 24, 27],
            "3. TRAZABILIDAD Y GESTIÓN": [4, 5, 12, 13, 21, 22, 23, 25, 42, 43, 44],
            "4. GESTIÓN PREVENTIVA": [6, 8, 9, 10, 11, 14, 15, 16, 17, 18, 19, 20, 28, 29, 30, 34, 35, 38, 39],
            "5. AUDITORÍAS Y NORMATIVAS": [26, 31, 32, 33, 36, 37, 40, 41, 45],
            "6. INGENIERÍA DE OPERACIONES": [] # Reservado para planes de izaje y confiabilidad
        }

        mapeo_resso = load_dynamic_config("MAPEO_RESSO", {})

        # Diccionario para guardar qué archivos van en qué carpeta para el ZIP global
        global_zip_structure = {}

        for pilar_nom, puntos in PILAR_MAP.items():
            with st.expander(f"📁 {pilar_nom}", expanded=False):
                puntos_presentes = 0
                total_puntos = len(puntos) if puntos else 1

                for p_num in puntos:
                    # Buscar la carpeta RESSO que corresponde a este número
                    # El mapeo en la DB asocia "Tipo Doc" -> "Nombre Carpeta"
                    # Necesitamos saber qué tipos de doc pertenecen a cada Punto X.
                    # Por simplicidad, buscamos carpetas que EMPIECEN con el número del punto.
                    folder_pattern = f"{p_num}.-"
                    tipos_doc_puntos = [k for k, v in mapeo_resso.items() if v.startswith(folder_pattern)]

                    st.markdown(f"**Punto {p_num}**")
                    if not tipos_doc_puntos:
                        st.caption("⚠️ No hay mapeo configurado para este punto.")
                        continue

                    placeholders = ','.join(['?'] * len(tipos_doc_puntos))
                    params = tuple(tipos_doc_puntos + [filtros.get('empresa_id', 0), filtros.get('contrato_id', 0)])
                    df_p = obtener_dataframe(db_path, f"SELECT identificador, nombre, tipo_doc, path FROM registros WHERE tipo_doc IN ({placeholders}) AND empresa_id = ? AND contrato_id = ?", params)

                    if not df_p.empty:
                        puntos_presentes += 1
                        st.success(f"✅ {len(df_p)} documentos encontrados.")
                        st.dataframe(df_p[['identificador', 'nombre', 'tipo_doc']], use_container_width=True, hide_index=True)
                        # Guardar para el ZIP
                        for _, row in df_p.iterrows():
                            folder_path = os.path.join(pilar_nom, f"Punto_{p_num}")
                            if folder_path not in global_zip_structure: global_zip_structure[folder_path] = []
                            global_zip_structure[folder_path].append(row['path'])
                    else:
                        st.error("❌ PENDIENTE: Sin archivos en el sistema.")

                prog = puntos_presentes / total_puntos
                st.progress(prog, text=f"Preparación del Pilar: {prog*100:.1f}%")

        st.markdown("---")
        if st.button("🚀 EXPORTAR DATA ROOM COMPLETO (.ZIP)", type="primary", use_container_width=True):
            if not global_zip_structure:
                st.warning("No hay documentos disponibles para exportar.")
            else:
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                    for folder, files in global_zip_structure.items():
                        for f_path in files:
                            if f_path and os.path.exists(f_path):
                                arc_name = os.path.join(folder, os.path.basename(f_path))
                                zip_file.write(f_path, arcname=arc_name)

                zip_buffer.seek(0)
                st.download_button(
                    "⬇️ DESCARGAR TODA LA AUDITORÍA",
                    zip_buffer,
                    f"DATA_ROOM_SGI_{emp_nom.replace(' ', '_')}.zip",
                    "application/zip",
                    use_container_width=True
                )
