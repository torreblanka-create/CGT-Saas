import json
import os
from datetime import datetime

import bcrypt
import pandas as pd
import streamlit as st
from PIL import Image

from src.infrastructure.database import (
    ejecutar_query,
    generar_hash,
    normalizar_texto,
    obtener_dataframe,
)
from core.excel_master import obtener_contratos_por_empresa, obtener_listas_unicas


def render_gestion_usuarios(DB_PATH):
    # Inyectar Lucide
    st.markdown("<h2 style='color: var(--cgt-blue);'><i data-lucide='users'></i> Gestión de Usuarios e Identidades</h2>", unsafe_allow_html=True)
    st.write("Administre perfiles, asigne roles y controle el acceso a la plataforma de forma granular.")
    st.divider()

    is_master = st.session_state.role == "Global Admin"

    # --- 1. LISTADO DE USUARIOS ---
    try:
        if is_master:
            query = "SELECT username, rol, nombre, email, cargo, departamento, empresa_id FROM usuarios"
            df_users = obtener_dataframe(DB_PATH, query)
        else:
            query = "SELECT username, rol, nombre, email, cargo, departamento, empresa_id FROM usuarios WHERE empresa_id = ? AND rol != 'Global Admin'"
            df_users = obtener_dataframe(DB_PATH, query, (st.session_state.empresa_id,))

        # Enriquecer con nombre de empresa
        df_emps = obtener_dataframe(DB_PATH, "SELECT id, nombre as Empresa FROM empresas")
        df_display = df_users.merge(df_emps, left_on='empresa_id', right_on='id', how='left').drop('id', axis=1)

        # Renombrar para visualización mas profesional
        df_ui = df_display.rename(columns={
            'username': 'Usuario',
            'nombre': 'Nombre Real',
            'rol': 'Nivel de Autorización',
            'email': 'Correo Corporativo',
            'cargo': 'Cargo',
            'departamento': 'Departamento'
        })

        st.markdown("### 📋 Usuarios Activos")
        selected_user = st.selectbox("Consultar/Editar Expediente Técnico:", ["-- Seleccionar Usuario --"] + list(df_display['username']))

        st.dataframe(df_ui[['Usuario', 'Nombre Real', 'Nivel de Autorización', 'Empresa', 'Correo Corporativo', 'Cargo', 'Departamento']], 
                     use_container_width=True, hide_index=True)

    except Exception as e:
        st.error(f"Error al cargar usuarios: {e}")
        return

    if selected_user != "-- Seleccionar Usuario --":
        render_user_editor_form(DB_PATH, selected_user, is_master)

    st.markdown("<br>### ➕ Registro de Nuevo Acceso", unsafe_allow_html=True)
    with st.expander("Abrir Formulario de Creación"):
        render_new_user_form(DB_PATH, is_master)

def render_user_editor_form(DB_PATH, username, is_master):
    st.markdown(f"---")
    st.markdown(f"### 👤 Expediente Técnico: **{username}**")

    # Cargar datos completos
    res = ejecutar_query(DB_PATH, "SELECT * FROM usuarios WHERE username = ?", (username,))
    if not res: return

    # Mapear columnas (id, user, pw, rol, nombre, terminos, emp_id, cont_id, email, tel, foto, prefs, reset)
    # Nota: Usar df es más seguro para mapeo
    usr = obtener_dataframe(DB_PATH, "SELECT * FROM usuarios WHERE username = ?", (username,)).iloc[0]

    col1, col2 = st.columns([1, 2.5])

    with col1:
        st.markdown("**Identidad Visual**")
        foto = usr['foto_path']
        if foto and os.path.exists(foto):
            st.image(foto, width=180)
        else:
            st.info("Sin imagen de perfil.")

        nueva_foto = st.file_uploader("Actualizar Imagen (Admin)", type=["jpg", "png"], key=f"adm_up_{username}")
        if nueva_foto:
            os.makedirs("assets/profiles", exist_ok=True)
            path = f"assets/profiles/{username}.png"
            Image.open(nueva_foto).save(path)
            ejecutar_query(DB_PATH, "UPDATE usuarios SET foto_path = ? WHERE username = ?", (path, username), commit=True)
            st.success("Imagen actualizada.")

    with col2:
        with st.form(f"f_edit_{username}"):
            c1, c2 = st.columns(2)
            c1, c2 = st.columns(2)
            with c1:
                n_nombre = st.text_input("Nombre Real de la Persona", value=usr['nombre'])
                n_email = st.text_input("Correo Corporativo", value=usr['email'] if usr['email'] else "")
                n_tel = st.text_input("Teléfono de Contacto", value=usr['telefono'] if usr['telefono'] else "")
                n_cargo = st.text_input("Cargo / Posición", value=usr['cargo'] if usr['cargo'] else "")

            with c2:
                n_depto = st.text_input("Departamento / Área", value=usr['departamento'] if usr['departamento'] else "")
                roles = ["Global Admin", "Admin", "Cargador", "Visita", "Auditor", "Rigger"]
                n_rol = st.selectbox("Nivel de Autorización", roles, index=roles.index(usr['rol']) if usr['rol'] in roles else 2)

                df_e = obtener_dataframe(DB_PATH, "SELECT id, nombre FROM empresas")
                emps_dict = {r['nombre']: r['id'] for _, r in df_e.iterrows()}
                lista_e = list(emps_dict.keys())
                curr_e_nom = next((k for k, v in emps_dict.items() if v == usr['empresa_id']), lista_e[0] if lista_e else "N/A")
                n_emp_nom = st.selectbox("Empresa Asignada", lista_e, index=lista_e.index(curr_e_nom) if curr_e_nom in lista_e else 0)

                # Contrato
                df_c = obtener_dataframe(DB_PATH, "SELECT id, nombre_contrato FROM contratos WHERE empresa_id = ?", (emps_dict.get(n_emp_nom, 0),))
                con_dict = {"TODOS LOS CONTRATOS": 0}
                for _, r in df_c.iterrows(): con_dict[r['nombre_contrato']] = r['id']
                lista_c = list(con_dict.keys())
                curr_c_nom = next((k for k, v in con_dict.items() if v == usr['contrato_asignado_id']), "TODOS LOS CONTRATOS")
                n_con_nom = st.selectbox("Contrato Asignado", lista_c, index=lista_c.index(curr_c_nom) if curr_c_nom in lista_c else 0)

            st.markdown("**🔐 Seguridad y Contraseñas**")
            sc1, sc2 = st.columns(2)
            with sc1:
                n_pw = st.text_input("Reasignar Nueva Contraseña (Sobreescribir)", type="password", help="Deje vacío para mantener la actual.")
            with sc2:
                n_reset = st.checkbox("Solicitar cambio obligatorio al ingresar", value=bool(usr['pw_reset_req']))

            if st.form_submit_button("💾 Aplicar Cambios en Servidor", use_container_width=True):
                query = "UPDATE usuarios SET nombre=?, email=?, telefono=?, cargo=?, departamento=?, rol=?, empresa_id=?, contrato_asignado_id=?, pw_reset_req=? WHERE username=?"
                params = [n_nombre, n_email, n_tel, n_cargo, n_depto, n_rol, emps_dict.get(n_emp_nom, 0), con_dict.get(n_con_nom, 0), 1 if n_reset else 0, username]

                if n_pw:
                    query = query.replace("WHERE", ", pw=? WHERE")
                    params.insert(-1, generar_hash(n_pw))

                ejecutar_query(DB_PATH, query, params, commit=True)
                st.success(f"✅ Los cambios para {username} han sido guardados.")
                st.rerun()

    # --- 3. DANGER ZONE ---
    if is_master and username != st.session_state.user_login:
        st.markdown("<br><br>", unsafe_allow_html=True)
        with st.expander("🚨 Zona de Peligro: Acciones Irreversibles"):
            st.warning(f"Está a punto de eliminar permanentemente el acceso de **{username}**.")
            confirm = st.text_input(f"Escriba ELIMINAR para confirmar la baja de {username}:")
            if st.button(f"💥 Eliminar Perfil de {username}", type="primary", use_container_width=True, disabled=(confirm != "ELIMINAR")):
                ejecutar_query(DB_PATH, "DELETE FROM usuarios WHERE username = ?", (username,), commit=True)
                st.success(f"🔥 El perfil de {username} ha sido eliminado del sistema.")
                import time; time.sleep(1)
                st.rerun()

def render_new_user_form(DB_PATH, is_master):
    # Formulario completo de creación técnica
    with st.form("new_user"):
        c1, c2 = st.columns(2)
        with c1:
            u = st.text_input("Nombre de Usuario (ID Logístico)")
            p = st.text_input("Contraseña Inicial", type="password")
            n = st.text_input("Nombre Real de la Persona")
            e = st.text_input("Correo Corporativo")
        with c2:
            roles = ["Global Admin", "Admin", "Cargador", "Visita", "Auditor", "Rigger"]
            r = st.selectbox("Nivel de Autorización", roles)
            
            # Selector de empresa robusto
            df_e = obtener_dataframe(DB_PATH, "SELECT id, nombre FROM empresas")
            emps_dict = {r['nombre']: r['id'] for _, r in df_e.iterrows()}
            emp = st.selectbox("Empresa", list(emps_dict.keys()))
            
            car = st.text_input("Cargo / Posición")
            dep = st.text_input("Departamento / Área")

        if st.form_submit_button("✨ Generar Nuevo Acceso"):
            if u and p and n:
                e_id = emps_dict.get(emp, 0)
                ejecutar_query(DB_PATH, "INSERT INTO usuarios (username, pw, rol, nombre, empresa_id, email, cargo, departamento, terminos_aceptados) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)",
                               (u, generar_hash(p), r, n, e_id, e, car, dep), commit=True)
                st.success(f"✅ Usuario {u} creado con éxito.")
                st.rerun()
            else: st.warning("Faltan campos obligatorios (Usuario, Password, Nombre).")
