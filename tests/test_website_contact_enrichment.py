from types import SimpleNamespace

from website_contact_enrichment import find_public_business_emails


class FakeResponse:
    def __init__(self, text, url, status=200, content_type="text/html"):
        self.text = text
        self.url = url
        self.status_code = status
        self.headers = {"Content-Type": content_type}


class FakeHTTP:
    def __init__(self, pages):
        self.pages = pages
        self.calls = []

    def get(self, url, timeout, headers=None, allow_redirects=True):
        self.calls.append(url)
        return self.pages.get(url, FakeResponse("", url, status=404))


def test_finds_mailto_and_text_emails_on_home_and_contact_page():
    home = "https://empresa.mx/"
    contact = "https://empresa.mx/contacto"
    http = FakeHTTP({
        home: FakeResponse(
            '<a href="/contacto">Contacto</a><p>ventas@empresa.mx</p>',
            home,
        ),
        contact: FakeResponse(
            '<a href="mailto:compras@empresa.mx">Enviar</a>',
            contact,
        ),
    })

    found = find_public_business_emails(home, http=http)

    assert {row["correo"] for row in found} == {
        "ventas@empresa.mx", "compras@empresa.mx"
    }
    assert all(row["tipo_fuente"] == "SITIO_WEB_EMPRESARIAL" for row in found)
    assert {row["fuente"] for row in found} == {home, contact}


def test_does_not_follow_external_domains_or_accept_external_redirects():
    home = "https://empresa.mx/"
    external = "https://otra.mx/contacto"
    http = FakeHTTP({
        home: FakeResponse(
            '<a href="https://otra.mx/contacto">Contacto</a><p>info@empresa.mx</p>',
            home,
        ),
        external: FakeResponse("<p>malicious@otra.mx</p>", external),
    })

    found = find_public_business_emails(home, http=http)

    assert [row["correo"] for row in found] == ["info@empresa.mx"]
    assert all("otra.mx" not in url for url in http.calls)


def test_rejects_local_and_ip_literal_websites_without_request():
    class NoCalls:
        def get(self, *args, **kwargs):
            raise AssertionError("No debe consultar hosts locales o IP")

    assert find_public_business_emails("http://127.0.0.1", http=NoCalls()) == []
    assert find_public_business_emails("http://localhost", http=NoCalls()) == []
