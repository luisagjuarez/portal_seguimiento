from __future__ import annotations

import email
from datetime import datetime, timezone
from email.header import decode_header
from email.message import Message
from email.utils import parseaddr, parsedate_to_datetime

from bs4 import BeautifulSoup

from app.models import ParsedAttachment, ParsedEmail

MAX_DESCRIPTION_LENGTH = 4000

# Marcadores comunes de firmas/citas de respuesta anterior (ES/EN). Todo lo que aparezca
# después del primer marcador encontrado se recorta, para no meter cadenas de respuesta
# completas dentro de la descripción de la solicitud.
_SIGNATURE_MARKERS = [
    "-----Mensaje original-----",
    "-----Original Message-----",
    "________________________________",
    "Enviado desde mi iPhone",
    "Enviado desde mi dispositivo",
    "Sent from my iPhone",
]


def decode_mime_header(raw_value: str) -> str:
    if not raw_value:
        return ""
    parts = decode_header(raw_value)
    decoded = []
    for text, charset in parts:
        if isinstance(text, bytes):
            decoded.append(text.decode(charset or "utf-8", errors="replace"))
        else:
            decoded.append(text)
    return "".join(decoded)


def _decode_part(part: Message) -> str:
    payload = part.get_payload(decode=True) or b""
    charset = part.get_content_charset() or "utf-8"
    try:
        return payload.decode(charset, errors="replace")
    except LookupError:
        return payload.decode("utf-8", errors="replace")


def _html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()
    text = soup.get_text(separator="\n")
    lines = [line.strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def _strip_quoted_reply(text: str) -> str:
    cut_at = len(text)
    for marker in _SIGNATURE_MARKERS:
        idx = text.find(marker)
        if idx > 0:
            cut_at = min(cut_at, idx)
    return text[:cut_at].strip()


def extract_body(msg: Message) -> tuple[str, str | None]:
    plain_parts: list[str] = []
    html_parts: list[str] = []

    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            disposition = str(part.get("Content-Disposition") or "")
            if "attachment" in disposition:
                continue
            if content_type == "text/plain":
                plain_parts.append(_decode_part(part))
            elif content_type == "text/html":
                html_parts.append(_decode_part(part))
    else:
        if msg.get_content_type() == "text/html":
            html_parts.append(_decode_part(msg))
        else:
            plain_parts.append(_decode_part(msg))

    html_body = "\n".join(html_parts) if html_parts else None
    if plain_parts:
        body_text = "\n".join(plain_parts)
    elif html_body:
        body_text = _html_to_text(html_body)
    else:
        body_text = ""

    return _strip_quoted_reply(body_text), html_body


def extract_attachments(msg: Message) -> list[ParsedAttachment]:
    attachments: list[ParsedAttachment] = []
    if not msg.is_multipart():
        return attachments

    for part in msg.walk():
        filename = part.get_filename()
        disposition = str(part.get("Content-Disposition") or "")
        if not filename or "attachment" not in disposition:
            continue
        content = part.get_payload(decode=True)
        if content is None:
            continue
        attachments.append(
            ParsedAttachment(
                filename=decode_mime_header(filename),
                content=content,
                content_type=part.get_content_type(),
            )
        )
    return attachments


def parse_email(raw_bytes: bytes) -> ParsedEmail:
    msg = email.message_from_bytes(raw_bytes)

    message_id = (msg.get("Message-ID") or "").strip()
    _, sender_email = parseaddr(msg.get("From", ""))
    subject = decode_mime_header(msg.get("Subject", ""))
    body_text, body_html = extract_body(msg)
    attachments = extract_attachments(msg)

    date_header = msg.get("Date")
    try:
        received_at = parsedate_to_datetime(date_header) if date_header else datetime.now(timezone.utc)
    except (TypeError, ValueError):
        received_at = datetime.now(timezone.utc)

    return ParsedEmail(
        message_id=message_id,
        sender_email=sender_email.lower(),
        subject=subject,
        body_text=body_text,
        body_html=body_html,
        received_at=received_at,
        attachments=attachments,
    )


def truncate_description(text: str, max_length: int = MAX_DESCRIPTION_LENGTH) -> str:
    """EBA_DEMO_MD_PROJECTS.DESCRIPTION es VARCHAR2(4000): el cuerpo original íntegro
    se conserva en el .md generado, no aquí."""
    if len(text) <= max_length:
        return text
    return text[: max_length - 1].rstrip() + "…"
