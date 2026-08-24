from __future__ import annotations

import smtplib
from email.message import EmailMessage

from app.config import settings


def enviar_correo(destinatario: str, asunto: str, cuerpo_texto: str) -> None:
    mensaje = EmailMessage()
    mensaje["From"] = settings.smtp_from
    mensaje["To"] = destinatario
    mensaje["Subject"] = asunto
    mensaje.set_content(cuerpo_texto)

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
        if settings.smtp_use_tls:
            smtp.starttls()
        if settings.smtp_user:
            smtp.login(settings.smtp_user, settings.smtp_password)
        smtp.send_message(mensaje)
