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


class DenueUnexpectedPayload(DenueEnrichmentError):
    """INEGI returned valid JSON, but not the documented record/list shape."""


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
    # INEGI may return a JSON-encoded string for service errors (for example,
    # "No hay resultados" or an authentication/parameter message). Preserve
    # that exact diagnostic instead of reducing it to the Python type "str".
    if isinstance(payload, str):
        detail = re.sub(r"\s+", " ", payload).strip()[:240]
        token = str(url).rsplit("/", 1)[-1]
        if token and detail:
            detail = detail.replace(token, "[TOKEN REDACTADO]")
        if not detail:
            detail = "cadena vacía"
        raise DenueUnexpectedPayload(
            "INEGI respondió HTTP 200 con una cadena JSON, no con una lista. "
            f"Texto devuelto por INEGI: {detail}"
        )

    # The documented API returns arrays. Some intermediary/error responses are
    # JSON objects; unwrap only known list envelopes or a clearly identifiable
    # single establishment. Never treat an arbitrary error object as a record.
    if isinstance(payload, dict):
        for key in ("datos", "data", "results", "resultados", "establecimientos", "records"):
            nested = payload.get(key)
            if isinstance(nested, list):
                return nested
        if payload.get("Id") and payload.get("Nombre"):
            return [payload]
        keys = ", ".join(sorted(str(key) for key in payload.keys())[:12]) or "sin claves"
        detail = ""
        for key in ("mensaje", "message", "error", "Message", "Error", "descripcion"):
            value = payload.get(key)
            if isinstance(value, (str, int, float)) and str(value).strip():
                detail = re.sub(r"\s+", " ", str(value)).strip()[:180]
                break
        suffix = f" Detalle informado por INEGI: {detail}" if detail else ""
        raise DenueUnexpectedPayload(
            "INEGI respondió JSON tipo objeto, no la lista documentada. "
            f"Claves recibidas: {keys}.{suffix}"
        )
    if not isinstance(payload, list):
        raise DenueUnexpectedPayload(
            f"INEGI devolvió JSON de tipo {type(payload).__name__}; se esperaba una lista."
        )
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


_ENTITY_CODES = {
    "aguascalientes": "01", "baja california": "02", "baja california sur": "03",
    "campeche": "04", "coahuila": "05", "coahuila de zaragoza": "05",
    "colima": "06", "chiapas": "07", "chihuahua": "08",
    "ciudad de mexico": "09", "distrito federal": "09",
    "durango": "10", "guanajuato": "11", "guerrero": "12",
    "hidalgo": "13", "jalisco": "14", "mexico": "15", "estado de mexico": "15",
    "michoacan": "16", "michoacan de ocampo": "16", "morelos": "17",
    "nayarit": "18", "nuevo leon": "19", "oaxaca": "20", "puebla": "21",
    "queretaro": "22", "queretaro de arteaga": "22", "quintana roo": "23",
    "san luis potosi": "24", "sinaloa": "25", "sonora": "26",
    "tabasco": "27", "tamaulipas": "28", "tlaxcala": "29",
    "veracruz": "30", "veracruz de ignacio de la llave": "30",
    "yucatan": "31", "zacatecas": "32",
}


def _entity_code(entity: str) -> str:
    value = str(entity or "").strip()
    if value.isdigit() and 1 <= int(value) <= 32:
        return f"{int(value):02d}"
    return _ENTITY_CODES.get(_normalize(value), "")


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

    # INEGI documents Ficha/{id}/{token}; the ID precedes the token.
    ficha_url = (
        f"{DENUE_API_BASE}/Ficha/{quote(establishment_id, safe='')}/"
        f"{quote(token, safe='')}"
    )
    ficha_diagnostic = ""
    try:
        payload = _request_json(http, ficha_url)
    except DenueUnexpectedPayload as exc:
        # A JSON string/object is an upstream response shape, not proof that
        # the record does not exist. Keep its literal sanitized diagnostic
        # and proceed to the official geographic/name fallback.
        ficha_diagnostic = str(exc)
        payload = []
    if payload:
        record = payload[0]
        if not isinstance(record, dict):
            raise DenueEnrichmentError("El formato de la ficha DENUE no es válido.")
        return _to_contact(record, requested_id=establishment_id)

    if not str(establishment_name or "").strip():
        reason = ficha_diagnostic or "DENUE no devolvió ficha por ID."
        raise DenueEnrichmentError(
            reason + " La base tampoco contiene el nombre para realizar la búsqueda alternativa."
        )

    state_code = _entity_code(entity)
    if not state_code:
        reason = f" Respuesta de Ficha: {ficha_diagnostic}" if ficha_diagnostic else ""
        raise DenueEnrichmentError(
            "No se pudo convertir la entidad de la base a la clave oficial INEGI (01–32); "
            "no se consultó el país completo para evitar falsos positivos." + reason
        )

    encoded_name = quote(str(establishment_name).strip(), safe="")
    encoded_token = quote(token, safe="")
    # Official contracts:
    # Nombre/{nombre}/{clave_entidad}/{registro_inicial}/{registro_final}/{token}
    # BuscarEntidad/{condicion}/{clave_entidad}/{registro_inicial}/{registro_final}/{token}
    fallback_urls = [
        (
            "Nombre",
            f"{DENUE_API_BASE}/Nombre/{encoded_name}/{state_code}/1/100/{encoded_token}",
        ),
        (
            "BuscarEntidad",
            f"{DENUE_API_BASE}/BuscarEntidad/{encoded_name}/{state_code}/1/100/{encoded_token}",
        ),
    ]

    all_matches = {}
    fallback_diagnostics = []
    for method, fallback_url in fallback_urls:
        try:
            candidates = _request_json(http, fallback_url)
        except DenueEnrichmentError as exc:
            # Includes the literal sanitized text when response.json() is str.
            fallback_diagnostics.append(f"{method}: {exc}")
            continue

        for row in candidates:
            if (
                isinstance(row, dict)
                and _name_matches(establishment_name, row.get("Nombre", ""))
                and _location_matches(row, entity, municipality)
            ):
                row_id = str(row.get("Id", "")).strip()
                if row_id:
                    all_matches[row_id] = row

        if len(all_matches) == 1:
            matched = next(iter(all_matches.values()))
            return _to_contact(matched)
        # If Nombre did not yield a verified unique match, try BuscarEntidad.

    if len(all_matches) > 1:
        raise DenueEnrichmentError(
            "Las búsquedas oficiales por Nombre y BuscarEntidad encontraron varias fichas "
            "con identidad geográfica coincidente. Se requiere revisión manual; no se guardó ninguna."
        )

    details = []
    if ficha_diagnostic:
        details.append(f"Ficha: {ficha_diagnostic}")
    details.extend(fallback_diagnostics)
    detail_text = " Diagnósticos literales de INEGI: " + " | ".join(details) if details else ""
    raise DenueEnrichmentError(
        "DENUE no devolvió una coincidencia inequívoca por nombre, entidad y municipio. "
        "No se guardó ningún dato." + detail_text
    )
