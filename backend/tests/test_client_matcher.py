from app.email_ingest.client_matcher import detect_cliente, extract_explicit_cliente


def test_extracts_explicit_pattern():
    assert extract_explicit_cliente("Hola,\nCliente: Chantilly\nGracias") == "Chantilly"


def test_explicit_pattern_case_insensitive_and_with_dash():
    assert extract_explicit_cliente("cliente - Chantilly") == "Chantilly"


def test_detect_cliente_normalizes_to_catalog_spelling():
    body = "Cliente: chantilly"
    assert detect_cliente(body, ["Chantilly", "Otra Empresa"]) == "Chantilly"


def test_detect_cliente_uses_explicit_text_when_not_in_catalog():
    body = "Cliente: Nuevo Cliente SA"
    assert detect_cliente(body, ["Chantilly"]) == "Nuevo Cliente SA"


def test_detect_cliente_matches_catalog_name_in_free_text_when_no_pattern():
    body = "Esto es para el cliente Chantilly, es urgente"
    assert detect_cliente(body, ["Chantilly"]) == "Chantilly"


def test_detect_cliente_returns_none_when_no_match():
    assert detect_cliente("Sin ninguna referencia a un cliente conocido", ["Chantilly"]) is None
