"""
===========================================
📦 ULTRON SMART INGEST — Clasificador v1.0
===========================================
Vista que permite subir múltiples PDFs y que
Ultron los clasifique y vincule automáticamente
con los registros de la base de datos.
"""
import os
import re
import shutil
from datetime import datetime

import pandas as pd
import streamlit as st

from config.config import BASE_DATA_DIR
from src.infrastructure.database import ejecutar_query, obtener_dataframe


def _extraer_texto_pdf_bytes(pdf_bytes: bytes) -> str:
    """Extrae texto de bytes de un PDF usando PyMuPDF."""
    try:
        import fitz
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        texto = ""
        for pag in doc:
            texto += pag.get_text("text") + "\n"
        doc.close()
        return texto[:30000]  # max 30k chars
    except ImportError:
        return "__NOFITZ__"
    except Exception as e:
        return f"__ERROR__{str(e)}"


def _normalizar(s: str) -> str:
    """Normaliza texto para búsqueda: mayúsculas, sin puntuación extra."""
    if not s:
        return ""
    import unicodedata
    s = str(s).upper().strip()
    s = ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')
    return re.sub(r'[.\-\s]', '', s)


def _buscar_coincidencias(texto: str, df_registros: pd.DataFrame) -> list:
    """
    Busca en el texto del PDF coincidencias con registros de la BD.
    Retorna lista de candidatos ordenados por confianza descending.
    """
    texto_norm = _normalizar(texto)
    texto_upper = texto.upper()
    candidatos = []

    for _, row in df_registros.iterrows():
        score = 0
        razones = []

        id_norm = _normalizar(str(row.get('identificador', '')))
        nombre_upper = str(row.get('nombre', '')).upper()

        # 1. Identificador (RUT / Patente / código)
        if id_norm and len(id_norm) >= 5 and id_norm in texto_norm:
            score += 70
            razones.append(f"✅ ID '{row['identificador']}' encontrado")

        # 2. Nombre (al menos 2 palabras)
        palabras = [p for p in nombre_upper.split() if len(p) > 3]
        if palabras:
            encontradas = sum(1 for p in palabras if p in texto_upper)
            ratio = encontradas / len(palabras)
            if ratio >= 0.6:
                puntos_nombre = int(ratio * 30)
                score += puntos_nombre
                razones.append(f"✅ Nombre '{row['nombre']}' ({encontradas}/{len(palabras)} palabras)")

        if score >= 40:
            candidatos.append({
                "id": row['id'],
                "identificador": row['identificador'],
                "nombre": row['nombre'],
                "tipo_doc": row.get('tipo_doc', ''),
                "categoria": row.get('categoria', ''),
                "path_actual": row.get('path', ''),
                "empresa_id": row.get('empresa_id', 0),
                "contrato_id": row.get('contrato_id', 0),
                "confianza": score,
                "razones": razones
            })

    return sorted(candidatos, key=lambda x: x['confianza'], reverse=True)


def _guardar_archivo_pdf(uploaded_file, registro: dict, tipo_doc: str, DB_PATH: str) -> str:
    """
    Guarda el PDF subido en la carpeta CGT_DATA correspondiente,
    siguiendo la jerarquía real: CGT_DATA / [Empresa] / [Contrato] / [Módulo].
    Retorna la ruta donde se guardó.
    """
    import sqlite3

    from config.config import get_scoped_path

    empresa_id = int(registro.get('empresa_id', 0))
    contrato_id = int(registro.get('contrato_id', 0))
    categoria = str(registro.get('categoria', 'Documentos')).strip()

    # Obtener nombres reales desde la BD
    empresa_nombre = f"empresa_{empresa_id}"
    contrato_nombre = f"contrato_{contrato_id}"

    try:
        from src.infrastructure.database import get_db_connection
        with get_db_connection(DB_PATH) as conn:
            cur = conn.cursor()
            cur.execute("SELECT nombre FROM empresas WHERE id = ?", (empresa_id,))
            r_emp = cur.fetchone()
            if r_emp:
                empresa_nombre = str(r_emp[0]).strip()

            cur.execute("SELECT nombre_contrato FROM contratos WHERE id = ?", (contrato_id,))
            r_con = cur.fetchone()
            if r_con:
                contrato_nombre = str(r_con[0]).strip()
    except Exception:
        pass  # Fallback a nombres genéricos si la BD no responde

    # Mapear categoría a nombre de módulo de carpeta
    CATEGORIA_MODULO = {
        "Personal": "01.-Personal",
        "Maquinaria Pesada & Vehículos": "02.-Maquinaria",
        "Elementos de izaje": "03.-Izaje",
        "Instrumentos y Metrología": "04.-Instrumentos",
        "Sistemas de Emergencia": "05.-Emergencia",
        "EPP": "06.-EPP",
    }
    modulo_carpeta = CATEGORIA_MODULO.get(categoria, f"07.-{categoria[:20]}")

    destino = get_scoped_path(empresa_nombre, contrato_nombre, modulo_carpeta)

    identificador = str(registro.get('identificador', 'SIN_ID')).replace('/', '_').replace('\\', '_')
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    nombre_archivo = f"{identificador}_{_normalizar(tipo_doc)[:20]}_{timestamp}.pdf"
    ruta_final = os.path.join(destino, nombre_archivo)

    with open(ruta_final, 'wb') as f:
        f.write(uploaded_file.getbuffer())

    return ruta_final



def render_smart_ingest(DB_PATH: str, filtros: dict):
    """Vista principal del Smart Ingest de Ultron."""

    st.markdown("""
        <div style='background:rgba(0,188,212,0.08); border-left:5px solid #00BCD4; 
                    padding:15px; border-radius:8px; margin-bottom:20px;'>
            <h3 style='color:#00BCD4; margin:0;'>📦 Smart Ingest — Clasificador Automático</h3>
            <p style='color:#8B98B8; margin:5px 0 0;'>
                Sube múltiples archivos PDF. Ultron escaneará su contenido y los vinculará 
                automáticamente con los registros correctos de la base de datos.
            </p>
        </div>
    """, unsafe_allow_html=True)

    # ── Carga de archivos ───────────────────────────────────
    archivos = st.file_uploader(
        "📂 Arrastra aquí los PDFs a clasificar",
        type=["pdf"],
        accept_multiple_files=True,
        help="Puedes subir hasta 20 archivos a la vez. Ull-Trone analizará cada uno."
    )

    if not archivos:
        st.info("👆 Sube al menos un archivo PDF para comenzar el análisis.")
        return

    # ── Verificar PyMuPDF ───────────────────────────────────
    try:
        import fitz
        fitz_ok = True
    except ImportError:
        fitz_ok = False
        st.error("🚨 **Módulo PyMuPDF no instalado.** Ejecuta `pip install PyMuPDF` para activar el OCR de Ultron.")
        return

    # ── Cargar registros de referencia ──────────────────────
    f_emp_id = filtros.get('empresa_id', 0)
    f_con_id = filtros.get('contrato_id', 0)

    query = "SELECT id, identificador, nombre, tipo_doc, categoria, path, empresa_id, contrato_id FROM registros WHERE 1=1"
    params = []
    if f_emp_id > 0:
        query += " AND empresa_id = ?"
        params.append(f_emp_id)
    if f_con_id > 0:
        query += " AND contrato_id = ?"
        params.append(f_con_id)

    df_registros = obtener_dataframe(DB_PATH, query, tuple(params))

    if df_registros.empty:
        st.warning("⚠️ No hay registros en la BD con los filtros actuales para clasificar los archivos.")
        return

    st.markdown(f"**{len(archivos)} archivo(s) cargados** — Analizando con el Ojo Digital de Ull-Trone...")

    # ── Análisis de cada archivo ────────────────────────────
    resultados = []

    with st.status("🔬 Ull-Trone escaneando archivos...", expanded=True) as status:
        for i, archivo in enumerate(archivos):
            status.write(f"📄 Analizando: `{archivo.name}` ({i+1}/{len(archivos)})")
            bytes_pdf = archivo.read()
            texto = _extraer_texto_pdf_bytes(bytes_pdf)

            if texto.startswith("__NOFITZ__") or texto.startswith("__ERROR__"):
                resultados.append({
                    "archivo": archivo,
                    "nombre_archivo": archivo.name,
                    "texto_extraido": "",
                    "chars": 0,
                    "candidatos": [],
                    "error": texto
                })
                continue

            candidatos = _buscar_coincidencias(texto, df_registros)
            resultados.append({
                "archivo": archivo,
                "nombre_archivo": archivo.name,
                "texto_extraido": texto,
                "chars": len(texto),
                "candidatos": candidatos[:5],  # top 5 candidatos
                "error": None
            })

        status.update(label="✅ Análisis completado", state="complete")

    # ── Panel de resultados y aprobación ───────────────────
    st.markdown("---")
    st.markdown("### 📋 Resultados del Análisis — Aprobación")

    aprobaciones = {}  # {nombre_archivo: registro_seleccionado o None}

    for resultado in resultados:
        nombre_arch = resultado['nombre_archivo']

        with st.container(border=True):
            col_file, col_info = st.columns([0.3, 0.7])

            with col_file:
                st.markdown(f"**📄 {nombre_arch}**")
                if resultado['chars'] > 0:
                    st.caption(f"Texto extraído: {resultado['chars']:,} caracteres")
                else:
                    st.caption("⚠️ Sin texto extraíble (imagen escaneada)")

            with col_info:
                if resultado['error']:
                    st.error(f"Error: {resultado['error']}")
                    aprobaciones[nombre_arch] = None
                elif not resultado['candidatos']:
                    st.warning("🔍 Sin coincidencias en la BD. Posible documento nuevo o sin texto.")
                    aprobaciones[nombre_arch] = None
                else:
                    top = resultado['candidatos'][0]
                    confianza = top['confianza']
                    color_conf = "#10B981" if confianza >= 70 else "#F59E0B"

                    st.markdown(
                        f"**Mejor coincidencia:** `{top['identificador']}` — {top['nombre']} "
                        f"<span style='color:{color_conf}; font-weight:bold;'>({confianza}% confianza)</span>",
                        unsafe_allow_html=True
                    )
                    for r in top['razones']:
                        st.caption(r)

                    # Selector de registro destino
                    opciones = ["— No vincular —"] + [
                        f"{c['identificador']} | {c['nombre']} | {c['categoria']} ({c['confianza']}%)"
                        for c in resultado['candidatos']
                    ]
                    seleccion = st.selectbox(
                        "Vincular con:",
                        opciones,
                        key=f"sel_{nombre_arch}",
                        index=1 if confianza >= 60 else 0
                    )

                    if seleccion != "— No vincular —":
                        idx = opciones.index(seleccion) - 1
                        aprobaciones[nombre_arch] = resultado['candidatos'][idx]
                        aprobaciones[nombre_arch]['_archivo'] = resultado['archivo']
                    else:
                        aprobaciones[nombre_arch] = None

    # ── Botón de confirmación ────────────────────────────────
    st.markdown("---")
    n_aprobados = sum(1 for v in aprobaciones.values() if v is not None)
    col_btn, col_stat = st.columns([1, 2])

    with col_btn:
        confirmar = st.button(
            f"🚀 Confirmar y Vincular {n_aprobados} Archivo(s)",
            use_container_width=True,
            type="primary",
            disabled=(n_aprobados == 0)
        )

    with col_stat:
        st.info(f"**{n_aprobados}** de **{len(resultados)}** archivos listos para vincular.")

    if confirmar:
        exitos = 0
        errores = 0
        with st.status("💾 Guardando archivos...", expanded=True) as save_status:
            for nombre_arch, registro in aprobaciones.items():
                if registro is None:
                    continue
                try:
                    save_status.write(f"📁 Guardando `{nombre_arch}`...")
                    ruta = _guardar_archivo_pdf(registro['_archivo'], registro, registro.get('tipo_doc', 'DOC'), DB_PATH)
                    # Actualizar ruta en BD
                    ejecutar_query(DB_PATH,
                        "UPDATE registros SET path = ? WHERE id = ?",
                        (ruta, registro['id']),
                        commit=True
                    )
                    exitos += 1
                    save_status.write(f"✅ Vinculado: `{registro['identificador']}` → `{nombre_arch}`")
                except Exception as e:
                    errores += 1
                    save_status.write(f"❌ Error en `{nombre_arch}`: {e}")

            save_status.update(label=f"✅ Proceso completado: {exitos} éxitos, {errores} errores",
                               state="complete" if errores == 0 else "error")

        if exitos > 0:
            st.success(f"✅ **{exitos} archivos vinculados exitosamente** a sus registros en la BD.")
            st.balloons()
        if errores > 0:
            st.error(f"❌ {errores} archivos no pudieron ser procesados.")
        st.rerun()
