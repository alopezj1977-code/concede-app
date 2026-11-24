"""Bounded extraction of publicly listed business emails from official company websites."""
from __future__ import annotations

from html.parser import HTMLParser
from ipaddress import ip_address
from urllib.parse import urljoin, urlsplit, urlunsplit
import re

import requests

_EMAIL_RE = re.compile(r"(?i)(?<![\w.+-])[\w.+-]{1,64}@[\w.-]+\.[a-z]{2,24}(?![\w.-])")
_CONTACT_HINTS = ("contact", "contacto", "nosotros", "about", "empresa", "ubicacion", "ubicación", "sucursales", "corporativo")
_SKIP_EMAILS = {"example@example.com", "name@example.com", "email@example.com", "test@test.com"}


class _PageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links = []
        self.mailtos = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag.lower() == "a":
            href = str(attrs.get("href", "") or "").strip()
            if href.lower().startswith("mailto:"):
                self.mailtos.append(href[7:].split("?", 1)[0])
            elif href:
                self.links.append(href)


def _safe_base_url(value: str) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    if not re.match(r"^https?://", raw, flags=re.I):
        raw = "https://" + raw
    parts = urlsplit(raw)
    if parts.scheme not in {"http", "https"} or not parts.hostname or parts.username or parts.password:
        return ""
    host = parts.hostname.casefold().rstrip(".")
    if host in {"localhost", "localhost.localdomain"} or "." not in host:
        return ""
    try:
        address = ip_address(host)
        if address.is_private or address.is_loopback or address.is_link_local or address.is_reserved:
            return ""
    except ValueError:
        pass
    return urlunsplit((parts.scheme, parts.netloc, parts.path or "/", "", ""))


def _same_site(left: str, right: str) -> bool:
    left_host = (urlsplit(left).hostname or "").casefold().removeprefix("www.")
    right_host = (urlsplit(right).hostname or "").casefold().removeprefix("www.")
    return bool(left_host and left_host == right_host)


def _emails(text: str):
    found = []
    for match in _EMAIL_RE.findall(text or ""):
        email = match.strip(".,;:()[]{}<>").lower()
        if email not in _SKIP_EMAILS and not email.endswith((".png", ".jpg", ".jpeg", ".webp", ".svg")):
            if email not in found:
                found.append(email)
    return found


def find_public_business_emails(website: str, *, http=requests, max_pages: int = 6):
    """Visit homepage and a few same-domain contact/about pages; never submit forms."""
    base = _safe_base_url(website)
    if not base:
        return []
    host = urlsplit(base).hostname.casefold()
    origin = f"{urlsplit(base).scheme}://{urlsplit(base).netloc}"
    queue = [base]
    visited = set()
    results = {}
    headers = {
        "User-Agent": "CONCEDE-Motor-V3/1.0 (+public business contact discovery)",
        "Accept": "text/html,application/xhtml+xml",
    }
    while queue and len(visited) < max(1, min(int(max_pages), 8)):
        url = queue.pop(0)
        parts = urlsplit(url)
        normalized = urlunsplit((parts.scheme, parts.netloc, parts.path or "/", "", ""))
        if normalized in visited:
            continue
        visited.add(normalized)
        try:
            response = http.get(normalized, timeout=12, headers=headers, allow_redirects=True)
        except requests.RequestException:
            continue
        final_url = str(getattr(response, "url", "") or normalized)
        final_parts = urlsplit(final_url)
        if final_parts.scheme not in {"http", "https"} or not _same_site(final_url, base):
            continue
        if getattr(response, "status_code", 0) != 200:
            continue
        content_type = str(getattr(response, "headers", {}).get("Content-Type", ""))
        if content_type and "html" not in content_type.casefold():
            continue
        body = str(getattr(response, "text", "") or "")[:1_000_000]
        parser = _PageParser()
        try:
            parser.feed(body)
        except Exception:
            pass
        candidates = _emails(body)
        candidates.extend(e for raw in parser.mailtos for e in _emails(raw))
        for email in candidates:
            results.setdefault(email, final_url)
        if len(visited) == 1:
            # Try conventional public contact pages even when the homepage
            # omits a visible navigation link.
            for path in ("/contacto", "/contact", "/contact-us", "/contactanos", "/nosotros", "/about"):
                queue.append(origin + path)
            for href in parser.links:
                target = urljoin(final_url, href)
                target_parts = urlsplit(target)
                if target_parts.scheme not in {"http", "https"} or not _same_site(target, base):
                    continue
                path = target_parts.path.casefold()
                if any(hint in path for hint in _CONTACT_HINTS):
                    queue.append(urlunsplit((target_parts.scheme, target_parts.netloc, target_parts.path, "", "")))
    return [
        {"correo": email, "fuente": source, "tipo_fuente": "SITIO_WEB_EMPRESARIAL"}
        for email, source in results.items()
    ]
