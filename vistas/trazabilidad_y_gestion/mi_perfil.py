import json
import os
from datetime import datetime

import pandas as pd
import streamlit as st
from PIL import Image

from src.infrastructure.database import ejecutar_query, generar_hash, obtener_dataframe


def render_mi_perfil(DB_PATH):
    # --- UI ELITE NEON ONYX ---
    st.markdown("""
        <div style='background: #F5F3F0; color: #1F2937; padding: 2rem; border-radius: 15px; border: 1px solid rgba(212,212,216,0.3); margin-bottom: 2rem; box-shadow: 0 10px 15px -3px rgba(0,0,0,0.05);'>
            <div style='display: flex; align-items: center; gap: 20px;'>
                <div style='background: rgba(56, 189, 248, 0.1); padding: 15px; border-radius: 12px; border: 1px solid rgba(56, 189, 248, 0.2);'>
                    <span style='font-size: 2.5rem;'>👤</span>
                </div>
                <div>
                    <h1 style='color: #F8FAFC; margin: 0; font-size: 1.8rem; font-family: "Outfit", sans-serif;'>Perfil de Usuario y Configuraciones</h1>
                    <p style='color: #94A3B8; margin: 5px 0 0 0; font-size: 1rem; opacity: 0.9;'>Gestión de identidad, permisos y preferencias del sistema.</p>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    username = st.session_state.user_login

    # --- 1. CARGAR DATOS ACTUALES ---
    query = "SELECT * FROM usuarios WHERE username = ?"
    df_u = obtener_dataframe(DB_PATH, query, (username,))

    if df_u.empty:
        st.error("No se pudo cargar la información del perfil.")
        return

    usr = df_u.iloc[0]

    # Parsear preferencias
    try:
        prefs = json.loads(usr['pref_notificaciones']) if usr['pref_notificaciones'] else {"silenciar": False}
    except:
        prefs = {"silenciar": False}

    # --- 2. LAYOUT: FOTO Y DATOS BÁSICOS ---
    c1, c2 = st.columns([1, 2])

    with c1:
        st.markdown("### 📸 Fotografía")
        foto_path = usr['foto_path']
        if foto_path and os.path.exists(foto_path):
            st.image(foto_path, width=200)
        else:
            st.info("Sin foto de perfil.")

        nueva_foto = st.file_uploader("Actualizar foto", type=["jpg", "png", "jpeg"])
        if nueva_foto:
            # Guardado local en assets/profiles/
            os.makedirs("assets/profiles", exist_ok=True)
            save_path = f"assets/profiles/{username}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            img = Image.open(nueva_foto)
            img.save(save_path)
            ejecutar_query(DB_PATH, "UPDATE usuarios SET foto_path = ? WHERE username = ?", (save_path, username), commit=True)
            st.success("¡Foto actualizada!")
            st.rerun()

    with c2:
        with st.form("perfil_form", border=False):
            new_nombre = st.text_input("Nombre Real de la Persona", value=usr['nombre'])
            new_email = st.text_input("Correo Corporativo", value=usr['email'] if usr['email'] else "")
            new_tel = st.text_input("Teléfono de Contacto", value=usr['telefono'] if usr['telefono'] else "")
            new_cargo = st.text_input("Cargo / Posición", value=usr['cargo'] if usr['cargo'] else "")
            new_depto = st.text_input("Departamento / Área", value=usr['departamento'] if usr['departamento'] else "")

            st.markdown("---")
            st.markdown("### 🏛️ Adscripción Organizacional")
            # Obtener nombre de empresa
            df_e = obtener_dataframe(DB_PATH, "SELECT nombre FROM empresas WHERE id = ?", (usr['empresa_id'],))
            emp_nom = df_e.iloc[0]['nombre'] if not df_e.empty else "N/A"
            
            c_info1, c_info2 = st.columns(2)
            with c_info1:
                st.text_input("Empresa", value=emp_nom, disabled=True)
            with c_info2:
                st.text_input("Nivel de Autorización", value=usr['rol'], disabled=True)

            st.markdown("---")
            st.markdown("### 🔔 Preferencias de Ull-Trone")
            silenciar = st.toggle("🔕 Modo Silencio (Solo alertas en app)", value=prefs.get("silenciar", False))

            if st.form_submit_button("Guardar Cambios", use_container_width=True):
                # Validar email unico si cambió
                if new_email and new_email != usr['email']:
                    check_e = ejecutar_query(DB_PATH, "SELECT username FROM usuarios WHERE email = ? AND username != ?", (new_email, username))
                    if check_e:
                        st.error("Este correo ya está registrado por otro usuario.")
                        return

                new_prefs = json.dumps({"silenciar": silenciar})
                query_up = "UPDATE usuarios SET nombre=?, email=?, telefono=?, cargo=?, departamento=?, pref_notificaciones=? WHERE username=?"
                ejecutar_query(DB_PATH, query_up, (new_nombre, new_email, new_tel, new_cargo, new_depto, new_prefs, username), commit=True)

                # Actualizar session_state
                st.session_state.users_name = new_nombre
                st.success("✅ Perfil actualizado correctamente.")
                st.rerun()

    st.divider()

    # --- 3. CAMBIO DE CONTRASEÑA ---
    st.markdown("### 🔐 Seguridad y Acceso")
    with st.expander("Cambiar mi contraseña"):
        with st.form("form_pw"):
            old_pw = st.text_input("Contraseña Actual", type="password")
            new_pw = st.text_input("Nueva Contraseña", type="password")
            new_pw_conf = st.text_input("Confirmar Nueva Contraseña", type="password")

            if st.form_submit_button("Actualizar Clave"):
                import bcrypt
                if bcrypt.checkpw(old_pw.encode('utf-8'), usr['pw'].encode('utf-8')):
                    if new_pw == new_pw_conf and len(new_pw) >= 6:
                        hashed = generar_hash(new_pw)
                        ejecutar_query(DB_PATH, "UPDATE usuarios SET pw = ?, pw_reset_req = 0 WHERE username = ?", (hashed, username), commit=True)
                        st.success("✅ Contraseña actualizada con éxito.")
                    else:
                        st.error("Las contraseñas no coinciden o son demasiado cortas (mín. 6 caracteres).")
                else:
                    st.error("La contraseña actual es incorrecta.")

    # Mensaje de Reset Obligatorio
    if usr.get('pw_reset_req', 0) == 1:
        st.warning("⚠️ **Nota**: El administrador ha solicitado que cambies tu contraseña por seguridad.")
