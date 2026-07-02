"""
Servicio de envío de email para recuperación de contraseña.
Si no hay SMTP configurado, imprime el enlace en consola (modo desarrollo).
"""

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config import settings

logger = logging.getLogger(__name__)


def send_password_reset_email(to_email: str, reset_url: str, user_name: str = "") -> bool:
    """
    Envía el email de recuperación. Devuelve True si tuvo éxito.
    Si SMTP no está configurado, loguea el enlace y devuelve True igualmente
    para no bloquear el flujo en desarrollo.
    """
    subject = "Recuperación de contraseña — AutomatizaCore"
    name_display = user_name or to_email

    html = f"""
    <!DOCTYPE html>
    <html>
    <body style="font-family: -apple-system, sans-serif; background: #09090b; color: #e4e4e7; padding: 40px 20px;">
      <div style="max-width: 480px; margin: 0 auto; background: #111113;
                  border: 1px solid #27272a; border-radius: 16px; padding: 40px;">
        <div style="text-align: center; margin-bottom: 32px;">
          <div style="display: inline-flex; background: #4f46e5; width: 48px; height: 48px;
                      border-radius: 12px; align-items: center; justify-content: center; margin-bottom: 16px;">
            <span style="color: white; font-size: 24px;">⚡</span>
          </div>
          <h1 style="margin: 0; font-size: 20px; font-weight: 700; color: white;">AutomatizaCore</h1>
        </div>

        <h2 style="font-size: 18px; font-weight: 600; color: white; margin-bottom: 8px;">
          Recupera tu contraseña
        </h2>
        <p style="color: #a1a1aa; font-size: 14px; line-height: 1.6; margin-bottom: 28px;">
          Hola {name_display}, recibimos una solicitud para restablecer la contraseña de tu cuenta.
          Este enlace es válido durante <strong style="color: #e4e4e7;">1 hora</strong>.
        </p>

        <a href="{reset_url}"
           style="display: block; text-align: center; background: #4f46e5; color: white;
                  text-decoration: none; padding: 14px 24px; border-radius: 12px;
                  font-weight: 600; font-size: 15px; margin-bottom: 24px;">
          Restablecer contraseña
        </a>

        <p style="color: #71717a; font-size: 12px; text-align: center; line-height: 1.6;">
          Si no solicitaste este cambio, ignora este email.<br>
          Tu contraseña no cambiará.
        </p>

        <hr style="border: none; border-top: 1px solid #27272a; margin: 24px 0;">
        <p style="color: #52525b; font-size: 11px; text-align: center;">
          O copia este enlace: <span style="color: #818cf8;">{reset_url}</span>
        </p>
      </div>
    </body>
    </html>
    """

    # Sin SMTP configurado (X1)
    if not settings.SMTP_HOST or not settings.SMTP_USER:
        if settings.ENVIRONMENT == "production":
            # En producción es una mala configuración: NO fingir que se envió ni
            # filtrar el token de reset (va en reset_url) en los logs.
            logger.error("SMTP no configurado: no se pudo enviar el email de reset a %s", to_email)
            return False
        # Modo desarrollo: mostrar el enlace en consola para poder probar el flujo.
        logger.info("[RESET PASSWORD dev] enlace de recuperación para %s: %s", to_email, reset_url)
        return True

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"AutomatizaCore <{settings.SMTP_USER}>"
        msg["To"] = to_email
        msg.attach(MIMEText(html, "html"))

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.ehlo()
            if settings.SMTP_TLS:
                server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.SMTP_USER, to_email, msg.as_string())

        logger.info("Email de reset enviado a %s", to_email)
        return True

    except Exception as e:
        logger.error("Error enviando email de reset a %s: %s", to_email, e)
        return False
