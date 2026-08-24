from email.message import EmailMessage

from app.email_ingest.parser import parse_email, truncate_description


def _build_raw_email(with_html: bool = False, with_attachment: bool = False) -> bytes:
    msg = EmailMessage()
    msg["Subject"] = "Nueva solicitud - Reporte de gastos"
    msg["From"] = "Mesa de Ayuda <mesa.ayuda@dovela.com>"
    msg["To"] = "solicitudes@dovela.com"
    msg["Message-ID"] = "<test-123@dovela.com>"

    if with_html:
        msg.set_content("Version texto plano")
        msg.add_alternative("<p>Cliente: <b>Chantilly</b></p>", subtype="html")
    else:
        msg.set_content("Cliente: Chantilly\n\nNecesito un reporte de gastos.")

    if with_attachment:
        msg.add_attachment(b"contenido", maintype="text", subtype="plain", filename="nota.txt")

    return bytes(msg)


def test_extracts_sender_and_message_id():
    parsed = parse_email(_build_raw_email())
    assert parsed.sender_email == "mesa.ayuda@dovela.com"
    assert parsed.message_id == "<test-123@dovela.com>"


def test_prefers_plain_text_body_over_html():
    parsed = parse_email(_build_raw_email(with_html=True))
    assert "Version texto plano" in parsed.body_text


def test_extracts_attachments():
    parsed = parse_email(_build_raw_email(with_attachment=True))
    assert len(parsed.attachments) == 1
    assert parsed.attachments[0].filename == "nota.txt"
    assert parsed.attachments[0].content == b"contenido"


def test_no_attachments_when_none_present():
    parsed = parse_email(_build_raw_email())
    assert parsed.attachments == []


def test_truncate_description_respects_max_length():
    text = "a" * 5000
    truncated = truncate_description(text, max_length=100)
    assert len(truncated) == 100
