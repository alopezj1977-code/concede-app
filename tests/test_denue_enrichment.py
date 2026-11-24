from types import SimpleNamespace

import pytest

from denue_enrichment import DenueEnrichmentError, fetch_denue_ficha


class FakeHTTP:
    def __init__(self, payload=None, status_code=200, text="", content_type="application/json"):
        self.payload = payload
        self.status_code = status_code
        self.text = text
        self.headers = {"Content-Type": content_type}
        self.called_url = None
        self.called_headers = None

    def get(self, url, timeout, headers=None):
        self.called_url = url
        self.called_headers = headers
        def parse_json():
            if self.payload is not None:
                return self.payload
            raise ValueError("not json")
        return SimpleNamespace(
            status_code=self.status_code,
            text=self.text,
            headers=self.headers,
            json=parse_json,
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



def test_ficha_reports_http_200_html_response_without_leaking_token():
    http = FakeHTTP(
        payload=None,
        text="<html><title>Access denied</title><body>proxy page</body></html>",
        content_type="text/html; charset=utf-8",
    )
    with pytest.raises(DenueEnrichmentError, match="Content-Type: text/html"):
        fetch_denue_ficha("12345", "secret-token", http=http)
    assert "secret-token" not in str(http.text)
    assert http.called_headers["Accept"] == "application/json"


class SequenceHTTP:
    def __init__(self, payloads):
        self.payloads = list(payloads)
        self.urls = []

    def get(self, url, timeout, headers=None):
        self.urls.append(url)
        payload = self.payloads.pop(0)
        return SimpleNamespace(
            status_code=200,
            text="",
            headers={"Content-Type": "application/json"},
            json=lambda: payload,
        )


def test_empty_ficha_falls_back_to_name_and_verifies_location_without_granting_consent():
    ficha = []
    search = [{
        "Id": "9876543",
        "Nombre": "GPS GLOBAL PACKAGING SUPPLIER",
        "Razon_social": "GPS GLOBAL PACKAGING SUPPLIER SA DE CV",
        "Correo_e": "ventas@example.mx",
        "Ubicacion": "GUADALUPE, Nuevo León, NUEVO LEÓN",
    }]
    http = SequenceHTTP([ficha, search])

    result = fetch_denue_ficha(
        "12269699",
        "secret-token",
        establishment_name="GPS GLOBAL PACKAGING SUPPLIER",
        entity="Nuevo León",
        municipality="Guadalupe",
        http=http,
    )

    assert len(http.urls) == 2
    assert "/Ficha/12269699/" in http.urls[0]
    assert "/Nombre/GPS%20GLOBAL%20PACKAGING%20SUPPLIER/19/1/100/" in http.urls[1]
    assert result["denue_id"] == "9876543"
    assert result["correo"] == "ventas@example.mx"
    assert result["autorizado"] is False
    assert result["apto"] is False


def test_name_fallback_rejects_a_different_state():
    http = SequenceHTTP([
        [],
        [{
            "Id": "9876543",
            "Nombre": "GPS GLOBAL PACKAGING SUPPLIER",
            "Ubicacion": "GUADALAJARA, JALISCO, JALISCO",
            "Correo_e": "ventas@example.mx",
        }],
    ])

    with pytest.raises(DenueEnrichmentError, match="coincidencia inequívoca"):
        fetch_denue_ficha(
            "12269699",
            "secret-token",
            establishment_name="GPS GLOBAL PACKAGING SUPPLIER",
            entity="Nuevo León",
            municipality="Guadalupe",
            http=http,
        )



def test_ficha_json_error_object_triggers_verified_name_fallback():
    ficha_error = {"error": "registro no disponible", "codigo": 404}
    name_result = [{
        "Id": "9876543",
        "Nombre": "GPS GLOBAL PACKAGING SUPPLIER",
        "Razon_social": "GPS GLOBAL PACKAGING SUPPLIER SA DE CV",
        "Correo_e": "ventas@example.mx",
        "Ubicacion": "GUADALUPE, NUEVO LEÓN, NUEVO LEÓN",
    }]
    http = SequenceHTTP([ficha_error, name_result])

    result = fetch_denue_ficha(
        "12269699",
        "secret-token",
        establishment_name="GPS GLOBAL PACKAGING SUPPLIER",
        entity="Nuevo León",
        municipality="Guadalupe",
        http=http,
    )

    assert len(http.urls) == 2
    assert "/Ficha/12269699/" in http.urls[0]
    assert "/Nombre/GPS%20GLOBAL%20PACKAGING%20SUPPLIER/" in http.urls[1]
    assert result["denue_id"] == "9876543"
    assert result["autorizado"] is False
    assert result["apto"] is False


def test_ficha_accepts_a_single_official_record_object():
    http = FakeHTTP({
        "Id": "12345",
        "Nombre": "EMPRESA PRUEBA",
        "Ubicacion": "GUADALUPE, NUEVO LEÓN",
        "Correo_e": "contacto@empresa.mx",
    })

    result = fetch_denue_ficha("12345", "secret-token", http=http)

    assert result["denue_id"] == "12345"
    assert result["correo"] == "contacto@empresa.mx"
    assert result["autorizado"] is False
    assert result["apto"] is False


def test_name_endpoint_object_error_reports_keys_and_message():
    http = SequenceHTTP([
        [],
        {"error": "token no válido", "codigo": 401},
        [],
    ])

    with pytest.raises(DenueEnrichmentError, match="Claves recibidas: codigo, error"):
        fetch_denue_ficha(
            "12269699",
            "secret-token",
            establishment_name="GPS GLOBAL PACKAGING SUPPLIER",
            entity="Nuevo León",
            municipality="Guadalupe",
            http=http,
        )



def test_ficha_json_string_message_falls_back_to_name_and_returns_verified_record():
    ficha_message = "No hay resultados"
    name_result = [{
        "Id": "6420100",
        "Nombre": "AGRIBRANDS PURINA MEXICO PLANTA MONTERREY",
        "Correo_e": "contacto@example.mx",
        "Ubicacion": "MONTERREY, NUEVO LEÓN, NUEVO LEÓN",
    }]
    http = SequenceHTTP([ficha_message, name_result])

    result = fetch_denue_ficha(
        "6420100",
        "secret-token",
        establishment_name="AGRIBRANDS PURINA MEXICO PLANTA MONTERREY",
        entity="Nuevo León",
        municipality="Monterrey",
        http=http,
    )

    assert len(http.urls) == 2
    assert "/Ficha/6420100/" in http.urls[0]
    assert "/Nombre/AGRIBRANDS%20PURINA%20MEXICO%20PLANTA%20MONTERREY/19/1/100/" in http.urls[1]
    assert result["denue_id"] == "6420100"
    assert result["autorizado"] is False
    assert result["apto"] is False


def test_name_json_string_message_is_reported_without_exposing_token():
    http = SequenceHTTP([
        "No hay resultados",
        "No hay resultados",
        "Token no válido: secret-token",
    ])

    with pytest.raises(DenueEnrichmentError) as exc:
        fetch_denue_ficha(
            "6420100",
            "secret-token",
            establishment_name="AGRIBRANDS PURINA MEXICO PLANTA MONTERREY",
            entity="Nuevo León",
            municipality="Monterrey",
            http=http,
        )

    message = str(exc.value)
    assert "cadena JSON" in message
    assert "Token no válido" in message
    assert "secret-token" not in message
    assert "[TOKEN REDACTADO]" in message
    assert "No hay resultados" in message
    assert "BuscarEntidad:" in message
    assert len(http.urls) == 3
    assert "/BuscarEntidad/AGRIBRANDS%20PURINA%20MEXICO%20PLANTA%20MONTERREY/19/1/100/" in http.urls[2]
