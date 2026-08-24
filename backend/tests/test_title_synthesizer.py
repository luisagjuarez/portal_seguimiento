from datetime import datetime, timezone

from app.email_ingest.title_synthesizer import synthesize_title


def test_strips_nueva_solicitud_and_adds_folio():
    title = synthesize_title(
        "Nueva solicitud: Creación de nuevo reporte gastos",
        "<abc123@dovela.com>",
        datetime(2026, 8, 20, 10, 30, tzinfo=timezone.utc),
    )
    assert title.startswith("Creación de nuevo reporte gastos")
    assert "20260820-" in title


def test_falls_back_when_subject_empty():
    title = synthesize_title("", "<abc@dovela.com>", datetime(2026, 8, 20, tzinfo=timezone.utc))
    assert title.startswith("Solicitud sin asunto")


def test_never_exceeds_name_column_length():
    long_subject = "Nueva solicitud " + ("x" * 400)
    title = synthesize_title(long_subject, "<id@dovela.com>", datetime(2026, 8, 20, tzinfo=timezone.utc))
    assert len(title) <= 255


def test_same_message_id_and_date_produce_same_folio():
    received_at = datetime(2026, 8, 20, tzinfo=timezone.utc)
    title_a = synthesize_title("Nueva solicitud: A", "<same-id@dovela.com>", received_at)
    title_b = synthesize_title("Nueva solicitud: A", "<same-id@dovela.com>", received_at)
    assert title_a == title_b


def test_different_message_id_avoids_collision_on_equal_subject():
    received_at = datetime(2026, 8, 20, tzinfo=timezone.utc)
    title_a = synthesize_title("Nueva solicitud: Reporte", "<id-1@dovela.com>", received_at)
    title_b = synthesize_title("Nueva solicitud: Reporte", "<id-2@dovela.com>", received_at)
    assert title_a != title_b
