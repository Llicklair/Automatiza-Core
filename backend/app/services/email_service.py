"""
Servicio de correo electrónico real usando IMAP (lectura) y SMTP (envío).
Soporta Gmail, Outlook, y cualquier servidor IMAP/SMTP estándar.
Sin dependencias externas — usa las librerías nativas de Python.
"""
import email
import imaplib
import smtplib
import ssl
from dataclasses import dataclass, field
from email.header import decode_header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


# ─── Configuraciones predefinidas por proveedor ────────────────────────────────

PROVIDER_PRESETS = {
    "gmail": {
        "imap_host": "imap.gmail.com",
        "imap_port": 993,
        "smtp_host": "smtp.gmail.com",
        "smtp_port": 587,
    },
    "outlook": {
        "imap_host": "outlook.office365.com",
        "imap_port": 993,
        "smtp_host": "smtp.office365.com",
        "smtp_port": 587,
    },
    "yahoo": {
        "imap_host": "imap.mail.yahoo.com",
        "imap_port": 993,
        "smtp_host": "smtp.mail.yahoo.com",
        "smtp_port": 587,
    },
}


@dataclass
class EmailMessage:
    id: str
    from_address: str
    to: str
    subject: str
    body: str
    date: str
    is_read: bool = False


@dataclass
class EmailCredentials:
    email_address: str
    password: str                  # Contraseña de aplicación (app password)
    imap_host: str = "imap.gmail.com"
    imap_port: int = 993
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    provider: str = "gmail"


# ─── Decodificación segura de cabeceras ───────────────────────────────────────

def _decode_header_value(value: str | None) -> str:
    if not value:
        return ""
    parts = decode_header(value)
    decoded = []
    for part, charset in parts:
        if isinstance(part, bytes):
            try:
                decoded.append(part.decode(charset or "utf-8", errors="replace"))
            except Exception:
                decoded.append(part.decode("latin-1", errors="replace"))
        else:
            decoded.append(str(part))
    return " ".join(decoded)


def _extract_body(msg: email.message.Message) -> str:
    """Extrae el cuerpo del correo (text/plain preferido sobre text/html)."""
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            disposition = str(part.get("Content-Disposition", ""))
            if "attachment" in disposition:
                continue
            if content_type == "text/plain":
                try:
                    charset = part.get_content_charset() or "utf-8"
                    body = part.get_payload(decode=True).decode(charset, errors="replace")
                    break
                except Exception:
                    pass
            elif content_type == "text/html" and not body:
                try:
                    charset = part.get_content_charset() or "utf-8"
                    raw_html = part.get_payload(decode=True).decode(charset, errors="replace")
                    # Strip básico de HTML sin dependencias
                    import re
                    body = re.sub(r"<[^>]+>", " ", raw_html).strip()
                except Exception:
                    pass
    else:
        try:
            charset = msg.get_content_charset() or "utf-8"
            body = msg.get_payload(decode=True).decode(charset, errors="replace")
        except Exception:
            body = str(msg.get_payload())
    return body.strip()


# ─── Lectura de correos vía IMAP ──────────────────────────────────────────────

def read_inbox(credentials: EmailCredentials, max_results: int = 10, folder: str = "INBOX") -> list[EmailMessage]:
    """
    Lee los correos más recientes de la bandeja de entrada vía IMAP SSL.
    Devuelve lista de EmailMessage ordenados del más reciente al más antiguo.
    """
    messages: list[EmailMessage] = []

    try:
        ctx = ssl.create_default_context()
        with imaplib.IMAP4_SSL(credentials.imap_host, credentials.imap_port, ssl_context=ctx) as imap:
            imap.login(credentials.email_address, credentials.password)
            imap.select(folder, readonly=True)

            # Buscar todos los mensajes (los últimos max_results)
            status, data = imap.search(None, "ALL")
            if status != "OK":
                return messages

            mail_ids = data[0].split()
            # Tomar los más recientes
            recent_ids = mail_ids[-max_results:][::-1]

            for mail_id in recent_ids:
                try:
                    status, msg_data = imap.fetch(mail_id, "(RFC822 FLAGS)")
                    if status != "OK":
                        continue

                    raw_email = msg_data[0][1]
                    msg = email.message_from_bytes(raw_email)

                    # Detectar si está leído
                    flags_data = msg_data[1] if len(msg_data) > 1 else b""
                    is_read = b"\\Seen" in flags_data if flags_data else False

                    messages.append(EmailMessage(
                        id=mail_id.decode(),
                        from_address=_decode_header_value(msg.get("From", "")),
                        to=_decode_header_value(msg.get("To", "")),
                        subject=_decode_header_value(msg.get("Subject", "(Sin asunto)")),
                        body=_extract_body(msg),
                        date=_decode_header_value(msg.get("Date", "")),
                        is_read=is_read,
                    ))
                except Exception:
                    continue

    except imaplib.IMAP4.error as e:
        raise ConnectionError(f"Error IMAP al conectar con {credentials.imap_host}: {e}")

    return messages


def read_unread(credentials: EmailCredentials, max_results: int = 10) -> list[EmailMessage]:
    """Devuelve solo los correos no leídos."""
    messages: list[EmailMessage] = []
    try:
        ctx = ssl.create_default_context()
        with imaplib.IMAP4_SSL(credentials.imap_host, credentials.imap_port, ssl_context=ctx) as imap:
            imap.login(credentials.email_address, credentials.password)
            imap.select("INBOX", readonly=True)

            status, data = imap.search(None, "UNSEEN")
            if status != "OK":
                return messages

            mail_ids = data[0].split()
            recent_ids = mail_ids[-max_results:][::-1]

            for mail_id in recent_ids:
                try:
                    status, msg_data = imap.fetch(mail_id, "(RFC822)")
                    if status != "OK":
                        continue
                    raw_email = msg_data[0][1]
                    msg = email.message_from_bytes(raw_email)
                    messages.append(EmailMessage(
                        id=mail_id.decode(),
                        from_address=_decode_header_value(msg.get("From", "")),
                        to=_decode_header_value(msg.get("To", "")),
                        subject=_decode_header_value(msg.get("Subject", "(Sin asunto)")),
                        body=_extract_body(msg),
                        date=_decode_header_value(msg.get("Date", "")),
                        is_read=False,
                    ))
                except Exception:
                    continue
    except imaplib.IMAP4.error as e:
        raise ConnectionError(f"Error IMAP: {e}")
    return messages


# ─── Envío de correos vía SMTP ────────────────────────────────────────────────

def send_email_smtp(
    credentials: EmailCredentials,
    to: str,
    subject: str,
    body: str,
    reply_to: str | None = None,
    attachment_paths: list[str] | None = None,
) -> dict:
    """
    Envía un correo electrónico vía SMTP con STARTTLS y soporte para adjuntos.
    Devuelve dict con status y mensaje de resultado.
    """
    import os
    import mimetypes
    from email import encoders
    from email.mime.base import MIMEBase

    try:
        msg = MIMEMultipart("mixed")
        msg["From"] = credentials.email_address
        msg["To"] = to
        msg["Subject"] = subject
        if reply_to:
            msg["Reply-To"] = reply_to

        # Cuerpo del mensaje (en un contenedor alternative para que el cliente elija texto plano)
        msg_body = MIMEMultipart("alternative")
        msg_body.attach(MIMEText(body, "plain", "utf-8"))
        msg.attach(msg_body)

        # Adjuntar archivos
        if attachment_paths:
            for path in attachment_paths:
                if not os.path.exists(path):
                    continue
                
                filename = os.path.basename(path)
                ctype, encoding = mimetypes.guess_type(path)
                if ctype is None or encoding is not None:
                    ctype = "application/octet-stream"
                
                maintype, subtype = ctype.split("/", 1)
                with open(path, "rb") as f:
                    part = MIMEBase(maintype, subtype)
                    part.set_payload(f.read())
                
                encoders.encode_base64(part)
                part.add_header(
                    "Content-Disposition",
                    f"attachment; filename={filename}",
                )
                msg.attach(part)

        ctx = ssl.create_default_context()
        with smtplib.SMTP(credentials.smtp_host, credentials.smtp_port) as server:
            server.ehlo()
            server.starttls(context=ctx)
            server.login(credentials.email_address, credentials.password)
            server.sendmail(credentials.email_address, to, msg.as_string())

        return {
            "success": True,
            "message": f"Correo enviado correctamente a {to}" + (f" con {len(attachment_paths)} adjuntos" if attachment_paths else ""),
            "to": to,
            "subject": subject,
            "attachments_count": len(attachment_paths) if attachment_paths else 0
        }

    except smtplib.SMTPAuthenticationError:
        return {
            "success": False,
            "message": "Error de autenticación SMTP. Verifica la contraseña de aplicación.",
        }
    except smtplib.SMTPException as e:
        return {
            "success": False,
            "message": f"Error SMTP al enviar el correo: {e}",
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error inesperado: {e}",
        }


# ─── Test de conexión ─────────────────────────────────────────────────────────

def test_imap_connection(credentials: EmailCredentials) -> bool:
    """Verifica que las credenciales IMAP son correctas. Devuelve True si OK."""
    try:
        ctx = ssl.create_default_context()
        with imaplib.IMAP4_SSL(credentials.imap_host, credentials.imap_port, ssl_context=ctx) as imap:
            imap.login(credentials.email_address, credentials.password)
            return True
    except Exception:
        return False


def credentials_from_dict(data: dict) -> EmailCredentials:
    """Construye EmailCredentials desde un dict (como el que viene de decrypt_credentials)."""
    provider = data.get("provider", "gmail")
    preset = PROVIDER_PRESETS.get(provider, PROVIDER_PRESETS["gmail"])
    return EmailCredentials(
        email_address=data["email_address"],
        password=data["password"],
        imap_host=data.get("imap_host", preset["imap_host"]),
        imap_port=int(data.get("imap_port", preset["imap_port"])),
        smtp_host=data.get("smtp_host", preset["smtp_host"]),
        smtp_port=int(data.get("smtp_port", preset["smtp_port"])),
        provider=provider,
    )
