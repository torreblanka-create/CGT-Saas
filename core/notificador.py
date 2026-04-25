import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

def enviar_correo_smtp(destinatario, asunto, mensaje_html):
    """
    Función base para envío de correos vía SMTP.
    Requiere variables de entorno: SMTP_SERVER, SMTP_PORT, SMTP_USER, SMTP_PASS
    """
    server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    port = int(os.getenv("SMTP_PORT", 587))
    user = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASS")

    if not user or not password:
        print("⚠️ Advertencia: Credenciales SMTP no configuradas en .env. El correo no se enviará.")
        return False, "Credenciales SMTP no configuradas"

    try:
        msg = MIMEMultipart()
        msg['From'] = user
        msg['To'] = destinatario
        msg['Subject'] = asunto

        msg.attach(MIMEText(mensaje_html, 'html'))

        with smtplib.SMTP(server, port) as smtp:
            smtp.starttls()
            smtp.login(user, password)
            smtp.send_message(msg)
            
        return True, "Correo enviado con éxito"
    except Exception as e:
        print(f"❌ Error enviando correo: {e}")
        return False, str(e)

def enviar_correo_recuperacion(email, nombre_usuario, nueva_clave):
    """Envía los detalles de acceso al usuario."""
    asunto = "🔑 Recuperación de Acceso - CGT.pro"
    
    html = f"""
    <html>
    <body style="font-family: sans-serif; color: #333;">
        <div style="max-width: 600px; margin: 20px auto; border: 1px solid #eee; padding: 20px; border-radius: 10px;">
            <h2 style="color: #2E5BFF;">Recuperación de Contraseña</h2>
            <p>Hola <strong>{nombre_usuario}</strong>,</p>
            <p>Has solicitado la recuperación de tu acceso al sistema <strong>CGT.pro</strong>.</p>
            <div style="background: #f9f9f9; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <p style="margin: 5px 0;"><strong>Usuario:</strong> {nombre_usuario}</p>
                <p style="margin: 5px 0;"><strong>Nueva Contraseña Temporal:</strong> <span style="color: #2E5BFF; font-size: 1.2em; font-weight: bold;">{nueva_clave}</span></p>
            </div>
            <p style="color: #FFC107; font-weight: bold;">⚠️ Importante: Por seguridad, descarga tus archivos y cambia esta clave apenas inicies sesión.</p>
            <hr style="border: 0; border-top: 1px solid #eee; margin: 20px 0;">
            <p style="font-size: 0.8em; color: #888;">Este es un correo automático, por favor no respondas.</p>
        </div>
    </body>
    </html>
    """
    return enviar_correo_smtp(email, asunto, html)
