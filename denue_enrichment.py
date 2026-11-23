"""Official INEGI DENUE establishment contact enrichment.

Only retrieves public fields returned by the DENUE Ficha endpoint. It does not
infer consent, scrape third-party websites, or make a contact campaign-eligible.
"""
from __future__ import annotations

from urllib.parse import quote

import requests

DENUE_API_BASE = "https://www.inegi.org.mx/app/api/denue/v1/consulta"
DENUE_DOC_URL = "https://www.inegi.org.mx/servicios/api-denue/"


class DenueEnrichmentError(RuntimeError):
    """Safe-to-display DENUE lookup error."""


def fetch_denue_ficha(establishment_id: str, token: str, *, http=requests):
    establishment_id = str(establishment_id or "").strip()
    token = str(token or "").strip()
    if not establishment_id or not establishment_id.isdigit():
        raise DenueEnrichmentError("El ID DENUE debe ser numérico.")
    if not token:
        raise DenueEnrichmentError("Falta configurar DENUE_API_TOKEN en Streamlit Secrets.")

    url = (
        f"{DENUE_API_BASE}/Ficha/{quote(establishment_id, safe='')}/"
        f"{quote(token, safe='')}"
    )
    try:
        response = http.get(url, timeout=20)
    except requests.RequestException as exc:
        raise DenueEnrichmentError("No fue posible conectar con la API oficial del INEGI.") from exc
    if response.status_code != 200:
        raise DenueEnrichmentError(
            f"INEGI DENUE respondió HTTP {response.status_code}. Verifica el token y vuelve a intentar."
        )
    try:
        payload = response.json()
    except (ValueError, TypeError) as exc:
        raise DenueEnrichmentError("La API DENUE devolvió una respuesta que no es JSON válido.") from exc
    if not isinstance(payload, list) or not payload:
        raise DenueEnrichmentError("DENUE no devolvió una ficha para ese establecimiento.")
    record = payload[0]
    if not isinstance(record, dict):
        raise DenueEnrichmentError("El formato de la ficha DENUE no es válido.")
    returned_id = str(record.get("Id", "")).strip()
    if returned_id and returned_id != establishment_id:
        raise DenueEnrichmentError("El ID devuelto por DENUE no coincide con el establecimiento consultado.")

    return {
        "denue_id": establishment_id,
        "empresa": str(record.get("Nombre") or "").strip(),
        "razon_social": str(record.get("Razon_social") or "").strip(),
        "correo": str(record.get("Correo_e") or "").strip().lower(),
        "sitio_web": str(record.get("Sitio_internet") or "").strip(),
        "telefono": str(record.get("Telefono") or "").strip(),
        "actividad": str(record.get("Clase_actividad") or "").strip(),
        "ubicacion": str(record.get("Ubicacion") or "").strip(),
        "fuente": DENUE_DOC_URL,
        "tipo_fuente": "INEGI_DENUE_FICHA",
        "estado_correo": "PUBLICADO_EN_DENUE" if record.get("Correo_e") else "SIN_CORREO_EN_DENUE",
        "autorizado": False,
        "apto": False,
    }
