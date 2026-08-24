"""Envía un correo de prueba contra el mailserver de pruebas ('greenmail') para
disparar manualmente el flujo de ingestión del Módulo 1.1.

Uso (con `docker compose --profile local-test up -d` corriendo):

    python backend/scripts/send_test_email.py
"""
from __future__ import annotations

import argparse
import smtplib
from email.message import EmailMessage
from email.utils import make_msgid


def build_message(to_addr: str, from_addr: str) -> EmailMessage:
    msg = EmailMessage()
    # A diferencia de un cliente/servidor de correo real, EmailMessage no agrega
    # Message-ID por sí solo; sin él, el worker no puede deduplicar el correo.
    msg["Message-ID"] = make_msgid(domain="dovela.com")
    msg["Subject"] = "Nueva solicitud - Reporte de gastos"
    msg["From"] = from_addr
    msg["To"] = to_addr
    msg.set_content(
        "Por fa necesito un reporte de gastos personalizado.\n\n"
        "Cliente: Chantilly\n\n"
        "Se espera primero la estimación de horas por el equipo de software y "
        "posterior la implementación."
    )
    msg.add_attachment(
        b"columna1,columna2\n1,2\n",
        maintype="text",
        subtype="csv",
        filename="ejemplo_reporte.csv",
    )
    return msg


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=3025)
    parser.add_argument("--to", default="solicitudes@dovela.com")
    parser.add_argument("--from-addr", dest="from_addr", default="mesa.ayuda@dovela.com")
    args = parser.parse_args()

    msg = build_message(args.to, args.from_addr)
    with smtplib.SMTP(args.host, args.port) as smtp:
        smtp.send_message(msg)
    print(f"Correo de prueba enviado a {args.to} via {args.host}:{args.port}")


if __name__ == "__main__":
    main()
