from __future__ import annotations

import re

# Reconoce una línea explícita "Cliente: <nombre>" (o con guion) en el cuerpo del correo.
_CLIENTE_PATTERN = re.compile(r"(?im)^\s*cliente\s*[:\-]\s*(.+?)\s*$")


def extract_explicit_cliente(body_text: str) -> str | None:
    match = _CLIENTE_PATTERN.search(body_text)
    if not match:
        return None
    candidate = match.group(1).strip().rstrip(".").strip()
    return candidate or None


def match_cliente_from_catalog(text: str, catalog_names: list[str]) -> str | None:
    """Busca el nombre de cliente del catálogo (CLIENTES.NOMBRE) que aparezca como
    substring de `text` (case-insensitive). CLIENTES no tiene UNIQUE en NOMBRE, por lo
    que esta comparación es por texto, no por constraint de BD. Si varios nombres
    calzan, se prefiere el más largo (más específico)."""
    upper_text = text.upper()
    best_match: str | None = None
    for name in catalog_names:
        if not name:
            continue
        if name.upper() in upper_text:
            if best_match is None or len(name) > len(best_match):
                best_match = name
    return best_match


def detect_cliente(body_text: str, catalog_names: list[str]) -> str | None:
    """Heurística de detección de cliente para el MVP (catálogo + patrón explícito):
    1. Si hay un patrón "Cliente: X" explícito, se usa X (normalizado a la ortografía
       del catálogo si X ya existe ahí).
    2. Si no hay patrón explícito, se busca cualquier nombre del catálogo mencionado en
       el cuerpo.
    3. Si no hay ninguna coincidencia, se retorna None (no se inventa un cliente; la
       solicitud queda sin cliente para revisión manual).
    """
    explicit = extract_explicit_cliente(body_text)
    if explicit:
        catalog_match = match_cliente_from_catalog(explicit, catalog_names)
        return catalog_match or explicit
    return match_cliente_from_catalog(body_text, catalog_names)
