"""Official INEGI DENUE establishment contact enrichment.

Uses the official Ficha endpoint first. If the ID returns no record, it may
resolve the establishment through the official Nombre endpoint, but only when
the returned name and geographic identity match the source row. Public emails
are data found, never consent.
"""
from __future__ import annotations

from difflib import SequenceMatcher
from urllib.parse import quote
import json
import re
import unicodedata

import requests

DENUE_API_BASE = "https://www.inegi.org.mx/app/api/denue/v1/consulta"
DENUE_DOC_URL = "https://www.inegi.org.mx/servicios/api-denue/"


class DenueEnrichmentError(RuntimeError):
    """Safe-to-display DENUE lookup error."""


def _normalize(value: str) -> str:
    value = unicodedata.normalize("NFKD", str(value or ""))
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    return " ".join(re.findall(r"[a-z0-9]+", value.casefold()))


def _request_json(http, url: str):
    try:
        response = http.get(
            url,
            timeout=20,
            headers={
                "Accept": "application/json",
                "User-Agent": "CONCEDE-Motor-V3/1.0 (INEGI DENUE API client)",
            },
        )
    except requests.RequestException as exc:
        raise DenueEnrichmentError(
            "No fue posible conectar con la API oficial del INEGI."
        ) from exc
    if response.status_code != 200:
        raise DenueEnrichmentError(
            f"INEGI DENUE respondió HTTP {response.status_code}. Verifica el token y vuelve a intentar."
        )
    try:
        try:
            payload = response.json()
        except (ValueError, TypeError):
            raw_body = str(getattr(response, "text", "") or "").lstrip("\ufeff").strip()
            payload = json.loads(raw_body)
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        content_type = str(getattr(response, "headers", {}).get("Content-Type", "no informado"))
        raw_body = str(getattr(response, "text", "") or "").lstrip("\ufeff").strip()
        preview = re.sub(r"<[^>]+>", " ", raw_body)
        preview = re.sub(r"\s+", " ", preview)[:100]
        preview = preview.replace(str(url).rsplit("/", 1)[-1], "[TOKEN REDACTADO]")
        if not preview:
            preview = "cuerpo vacío"
        raise DenueEnrichmentError(
            "INEGI respondió HTTP 200, pero el contenido no es JSON. "
            f"Content-Type: {content_type}. Respuesta: {preview}. "
            "Esto permite identificar una página HTML/intermediaria o un rechazo del servicio."
        ) from exc
    if not isinstance(payload, list):
        raise DenueEnrichmentError("INEGI devolvió una estructura inesperada; se esperaba una lista.")
    return payload


def _name_matches(expected: str, actual: str) -> bool:
    left, right = _normalize(expected), _normalize(actual)
    if not left or not right:
        return False
    if left == right:
        return True
    left_tokens, right_tokens = set(left.split()), set(right.split())
    overlap = len(left_tokens & right_tokens) / max(1, min(len(left_tokens), len(right_tokens)))
    return overlap >= 0.80 or SequenceMatcher(None, left, right).ratio() >= 0.84


def _location_matches(record: dict, expected_state: str, expected_municipality: str) -> bool:
    location = _normalize(record.get("Ubicacion", ""))
    state = _normalize(expected_state)
    municipality = _normalize(expected_municipality)
    if state and state not in location:
        return False
    if municipality and municipality not in location:
        return False
    return bool(location)


def _to_contact(record: dict, requested_id: str = "") -> dict:
    returned_id = str(record.get("Id", "")).strip()
    if requested_id and returned_id and returned_id != requested_id:
        raise DenueEnrichmentError(
            "El ID devuelto por DENUE no coincide con el establecimiento consultado."
        )
    denue_id = returned_id or requested_id
    if not denue_id:
        raise DenueEnrichmentError("La ficha DENUE no contiene un ID de establecimiento.")
    email = str(record.get("Correo_e") or "").strip().lower()
    return {
        "denue_id": denue_id,
        "empresa": str(record.get("Nombre") or "").strip(),
        "razon_social": str(record.get("Razon_social") or "").strip(),
        "correo": email,
        "sitio_web": str(record.get("Sitio_internet") or "").strip(),
        "telefono": str(record.get("Telefono") or "").strip(),
        "actividad": str(record.get("Clase_actividad") or "").strip(),
        "ubicacion": str(record.get("Ubicacion") or "").strip(),
        "fuente": DENUE_DOC_URL,
        "tipo_fuente": "INEGI_DENUE_FICHA",
        "estado_correo": "PUBLICADO_EN_DENUE" if email else "SIN_CORREO_EN_DENUE",
        "autorizado": False,
        "apto": False,
    }


def fetch_denue_ficha(
    establishment_id: str,
    token: str,
    *,
    establishment_name: str = "",
    entity: str = "",
    municipality: str = "",
    http=requests,
):
    establishment_id = str(establishment_id or "").strip()
    token = str(token or "").strip()
    if not establishment_id or not establishment_id.isdigit():
        raise DenueEnrichmentError("El ID DENUE debe ser numérico.")
    if not token:
        raise DenueEnrichmentError("Falta configurar DENUE_API_TOKEN en Streamlit Secrets.")

    ficha_url = (
        f"{DENUE_API_BASE}/Ficha/{quote(establishment_id, safe='')}/"
        f"{quote(token, safe='')}"
    )
    payload = _request_json(http, ficha_url)
    if payload:
        record = payload[0]
        if not isinstance(record, dict):
            raise DenueEnrichmentError("El formato de la ficha DENUE no es válido.")
        return _to_contact(record, requested_id=establishment_id)

    # Some source exports contain IDs that are no longer resolvable by Ficha.
    # Resolve through INEGI's documented Nombre method, then verify name,
    # state and municipality before accepting a result.
    if not str(establishment_name or "").strip():
        raise DenueEnrichmentError(
            "DENUE no devolvió ficha por ID y la base no contiene el nombre para buscarla."
        )
    name_url = (
        f"{DENUE_API_BASE}/Nombre/{quote(str(establishment_name).strip(), safe='')}/"
        f"00/1/100/{quote(token, safe='')}"
    )
    candidates = _request_json(http, name_url)
    matches = [
        row for row in candidates
        if isinstance(row, dict)
        and _name_matches(establishment_name, row.get("Nombre", ""))
        and _location_matches(row, entity, municipality)
    ]
    if len(matches) == 1:
        return _to_contact(matches[0])
    if len(matches) > 1:
        raise DenueEnrichmentError(
            "La búsqueda por nombre encontró varias fichas con identidad geográfica coincidente. "
            "Se requiere revisión manual; no se guardó ninguna."
        )
    if candidates and not entity:
        raise DenueEnrichmentError(
            "DENUE encontró coincidencias por nombre, pero falta la entidad de la base para verificar la identidad."
        )
    raise DenueEnrichmentError(
        "DENUE no devolvió ficha por ID ni una coincidencia inequívoca por nombre y ubicación. "
        "No se guardó ningún dato."
    )
