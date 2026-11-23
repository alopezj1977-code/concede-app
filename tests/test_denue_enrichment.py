from types import SimpleNamespace

import pytest

from denue_enrichment import DenueEnrichmentError, fetch_denue_ficha


class FakeHTTP:
    def __init__(self, payload=None, status_code=200):
        self.payload = payload
        self.status_code = status_code
        self.called_url = None

    def get(self, url, timeout):
        self.called_url = url
        return SimpleNamespace(
            status_code=self.status_code,
            json=lambda: self.payload,
        )


def test_ficha_returns_public_email_and_never_grants_authorization():
    http = FakeHTTP([{
        "Id": "12345",
        "Nombre": "EMPRESA PRUEBA",
        "Razon_social": "EMPRESA PRUEBA SA DE CV",
        "Correo_e": "CONTACTO@EMPRESA.MX",
        "Sitio_internet": "https://empresa.mx",
        "Telefono": "5555555555",
        "Clase_actividad": "Servicios",
        "Ubicacion": "CDMX",
    }])

    result = fetch_denue_ficha("12345", "secret-token", http=http)

    assert result["correo"] == "contacto@empresa.mx"
    assert result["sitio_web"] == "https://empresa.mx"
    assert result["estado_correo"] == "PUBLICADO_EN_DENUE"
    assert result["autorizado"] is False
    assert result["apto"] is False
    assert "secret-token" in http.called_url


def test_ficha_rejects_non_numeric_id_without_request():
    http = FakeHTTP([])
    with pytest.raises(DenueEnrichmentError, match="numérico"):
        fetch_denue_ficha("abc", "secret-token", http=http)
    assert http.called_url is None


def test_ficha_rejects_http_error():
    http = FakeHTTP([], status_code=403)
    with pytest.raises(DenueEnrichmentError, match="HTTP 403"):
        fetch_denue_ficha("12345", "secret-token", http=http)
