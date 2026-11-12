#!/usr/bin/env python3
"""Busca informacion en internet y genera un Markdown citable.

Pensado para el flujo de desarrollo: cuando la respuesta no esta en el repo
(documentacion de una libreria, un error concreto, una version, una API
reciente), este script busca, descarga y resume las fuentes para incluirlas en
el contexto del modelo.

Uso:
    python scripts/web_context.py --query "Django 4.2 DRF @api_view documentation"
    python scripts/web_context.py --url https://docs.djangoproject.com/en/4.2/
    python scripts/web_context.py --query "..." --no-fetch

Seguridad:
    - Solo permite http/https.
    - Bloquea localhost, IPs privadas, link-local y metadatos cloud.
    - Limita tamano y tiempo de descarga.
    - No ejecuta JavaScript.

No necesita dependencias obligatorias. Si `ddgs` esta instalado, busca en
DuckDuckGo. Si `requests` esta instalado, lo usa para descargar; si no, usa
`urllib` de la biblioteca estandar.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import html
import ipaddress
import os
import re
import socket
import sys
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

USER_AGENT = (
    "Mozilla/5.0 (compatible; context-pack/1.0; +local-development-tool)"
)
BLOCK_TAGS = {
    "p",
    "li",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "br",
    "div",
    "tr",
    "td",
    "th",
    "section",
    "article",
    "blockquote",
    "dt",
    "dd",
    "table",
    "ul",
    "ol",
}
SKIP_TAGS = {
    "script",
    "style",
    "nav",
    "footer",
    "header",
    "aside",
    "form",
    "svg",
    "noscript",
    "template",
    "iframe",
}
STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "from",
    "that",
    "this",
    "into",
    "about",
    "como",
    "para",
    "con",
    "del",
    "las",
    "los",
    "una",
    "uno",
    "por",
    "que",
    "los",
    "una",
    "sus",
    "mas",
    "pero",
    "sobre",
    "entre",
    "desde",
    "hasta",
    "cuando",
    "donde",
    "documentation",
    "documentacion",
    "official",
    "oficial",
    "guide",
    "guia",
    "example",
    "ejemplo",
}


@dataclass
class WebResult:
    title: str
    url: str
    snippet: str = ""
    excerpt: str = ""
    code: List[str] = field(default_factory=list)
    error: str = ""
    fetched: bool = False


class _TextExtractor(HTMLParser):
    """Extrae texto legible sin dependencias externas."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: List[str] = []
        self.skip_depth = 0
        self.in_pre = False
        self.in_title = False
        self.title_parts: List[str] = []

    def handle_starttag(self, tag: str, attrs: Sequence[Tuple[str, Optional[str]]]) -> None:
        tag = tag.lower()
        if tag in SKIP_TAGS:
            self.skip_depth += 1
            return
        if tag == "title":
            self.in_title = True
        if tag == "pre":
            self.in_pre = True
            self.parts.append("\n")
        elif tag in BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in SKIP_TAGS:
            if self.skip_depth:
                self.skip_depth -= 1
            return
        if tag == "title":
            self.in_title = False
        if tag == "pre":
            self.in_pre = False
            self.parts.append("\n")
        elif tag in BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self.skip_depth:
            return
        if self.in_title:
            self.title_parts.append(data)
            return
        if self.in_pre:
            self.parts.append(data)
        else:
            self.parts.append(re.sub(r"\s+", " ", data))

    def text(self) -> str:
        raw = "".join(self.parts)
        raw = re.sub(r"[ \t]+\n", "\n", raw)
        raw = re.sub(r"\n{3,}", "\n\n", raw)
        return raw.strip()

    def title(self) -> str:
        return re.sub(r"\s+", " ", "".join(self.title_parts)).strip()


def _query_terms(query: str) -> List[str]:
    terms: List[str] = []
    for token in re.findall(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9_][A-Za-z0-9ÁÉÍÓÚÜÑáéíóúüñ_.-]*", query):
        low = token.lower()
        if len(low) >= 3 and low not in STOPWORDS:
            terms.append(low)
    return list(dict.fromkeys(terms))


def _extract_title(raw_html: str) -> str:
    match = re.search(r"<title[^>]*>(.*?)</title>", raw_html, re.IGNORECASE | re.DOTALL)
    if not match:
        return ""
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", match.group(1)))).strip()


def _extract_meta_description(raw_html: str) -> str:
    match = re.search(
        r"<meta[^>]+name=[\"']description[\"'][^>]+content=[\"']([^\"']+)[\"']",
        raw_html,
        re.IGNORECASE | re.DOTALL,
    )
    if not match:
        return ""
    return re.sub(r"\s+", " ", html.unescape(match.group(1))).strip()


def _extract_code_blocks(raw_html: str) -> List[str]:
    blocks: List[str] = []
    for match in re.findall(r"<pre[^>]*>(.*?)</pre>", raw_html, re.IGNORECASE | re.DOTALL):
        code = re.sub(r"<br\s*/?>", "\n", match, flags=re.IGNORECASE)
        code = re.sub(r"<[^>]+>", "", code)
        code = html.unescape(code).strip("\n")
        code = re.sub(r"\n{3,}", "\n\n", code)
        if code and len(code) <= 4000:
            blocks.append(code)
    return blocks[:5]


def _extract_readable_text(raw_html: str) -> str:
    cleaned = re.sub(
        r"(?is)<(script|style|nav|footer|header|aside|form|svg|noscript|template|iframe)[^>]*>.*?</\1>",
        " ",
        raw_html,
    )
    cleaned = re.sub(r"(?is)<pre[^>]*>.*?</pre>", " ", cleaned)
    parser = _TextExtractor()
    try:
        parser.feed(cleaned)
    except Exception:
        return ""
    return parser.text()


def _score_block(block: str, terms: Sequence[str]) -> float:
    if not block:
        return 0.0
    low = block.lower()
    score = sum(low.count(term) for term in terms) * 2.0
    if 120 <= len(block) <= 2500:
        score += 1.0
    if block.startswith(("#", "-", "*", "1.", "2.")):
        score += 0.5
    return score


def _select_excerpt(text: str, query: str, max_chars: int) -> str:
    terms = _query_terms(query)
    blocks = [block.strip() for block in re.split(r"\n\s*\n", text) if block.strip()]
    if not blocks:
        return ""
    selected: List[Tuple[int, str]] = []
    used = 0
    # Conserva la introduccion de la pagina.
    for index, block in enumerate(blocks[:2]):
        if used + len(block) > max_chars:
            break
        selected.append((index, block))
        used += len(block)
    scored = sorted(
        ((_score_block(block, terms), index, block) for index, block in enumerate(blocks)),
        key=lambda item: (-item[0], item[1]),
    )
    for score, index, block in scored:
        if score <= 0:
            continue
        if any(index == existing for existing, _ in selected):
            continue
        if used + len(block) > max_chars:
            continue
        selected.append((index, block))
        used += len(block)
        if used >= max_chars * 0.9:
            break
    selected.sort(key=lambda item: item[0])
    return "\n\n".join(block for _index, block in selected)


def _is_private_host(host: str) -> bool:
    host = host.strip("[]").lower()
    if host in {"localhost", "localhost.localdomain", "metadata.google.internal"}:
        return True
    try:
        infos = socket.getaddrinfo(host, None)
    except (socket.gaierror, OSError):
        return True
    for info in infos:
        address = info[4][0]
        try:
            ip = ipaddress.ip_address(address)
        except ValueError:
            return True
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        ):
            return True
    return False


def is_safe_url(url: str, allow_private: bool = False) -> bool:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return False
    if not parsed.hostname:
        return False
    if allow_private:
        return True
    return not _is_private_host(parsed.hostname)


def _decode_response(raw: bytes, charset: Optional[str]) -> str:
    for encoding in [charset, "utf-8", "latin-1"]:
        if not encoding:
            continue
        try:
            return raw.decode(encoding, errors="replace")
        except LookupError:
            continue
    return raw.decode("utf-8", errors="replace")


def fetch_url(
    url: str,
    timeout: int = 15,
    max_bytes: int = 2_000_000,
    allow_private: bool = False,
) -> Tuple[str, str]:
    if not is_safe_url(url, allow_private=allow_private):
        raise ValueError("URL no permitida (solo http/https publicos)")

    try:
        import requests  # type: ignore
    except ImportError:
        requests = None  # type: ignore

    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,text/plain;q=0.9,*/*;q=0.1",
    }

    if requests is not None:
        response = requests.get(
            url,
            headers=headers,
            timeout=timeout,
            allow_redirects=True,
            stream=True,
        )
        response.raise_for_status()
        final_url = response.url
        if not is_safe_url(final_url, allow_private=allow_private):
            raise ValueError("redireccion a URL no permitida")
        content_type = (response.headers.get("content-type") or "").lower()
        if not any(
            allowed in content_type
            for allowed in ("text/html", "application/xhtml", "text/plain")
        ):
            raise ValueError("el contenido no es HTML o texto")
        chunks: List[bytes] = []
        total = 0
        for chunk in response.iter_content(65536):
            total += len(chunk)
            if total > max_bytes:
                break
            chunks.append(chunk)
        raw = b"".join(chunks)
        charset = response.encoding or response.apparent_encoding
        return final_url, _decode_response(raw, charset)

    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        final_url = response.geturl()
        if not is_safe_url(final_url, allow_private=allow_private):
            raise ValueError("redireccion a URL no permitida")
        content_type = response.headers.get("content-type", "").lower()
        if not any(
            allowed in content_type
            for allowed in ("text/html", "application/xhtml", "text/plain")
        ):
            raise ValueError("el contenido no es HTML o texto")
        raw = response.read(max_bytes + 1)[:max_bytes]
        charset = response.headers.get_content_charset()
        return final_url, _decode_response(raw, charset)


def search_web(query: str, max_results: int = 5) -> List[WebResult]:
    try:
        from ddgs import DDGS  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "ddgs no esta instalado; usa --url o instala con `pip install ddgs`"
        ) from exc

    errors: List[str] = []
    raw: List[Dict] = []
    # DDGS puede fallar segun el motor elegido por "auto"; probamos varios.
    for backend in ("auto", "duckduckgo", "brave", "bing", "yandex", "mojeek"):
        try:
            raw = DDGS().text(query, max_results=max_results, backend=backend)
            if raw:
                break
        except Exception as exc:  # noqa: BLE001
            errors.append("%s: %s" % (backend, exc))
    if not raw:
        detail = "; ".join(errors[-3:]) if errors else "sin resultados"
        raise RuntimeError("busqueda sin resultados (%s). Prueba una consulta mas corta o usa --url" % detail)

    results: List[WebResult] = []
    for item in raw:
        url = item.get("href") or item.get("url") or ""
        if not url:
            continue
        results.append(
            WebResult(
                title=(item.get("title") or url).strip(),
                url=url.strip(),
                snippet=(item.get("body") or item.get("snippet") or "").strip()[:600],
            )
        )
    return results


def build_web_context(
    query: str = "",
    urls: Sequence[str] = (),
    max_results: int = 5,
    fetch_results: int = 3,
    max_chars_per_page: int = 6000,
    max_total_chars: int = 24000,
    no_fetch: bool = False,
    allow_private: bool = False,
    timeout: int = 15,
) -> str:
    results: List[WebResult] = []
    errors: List[str] = []

    if query.strip():
        try:
            results.extend(search_web(query, max_results=max_results))
        except Exception as exc:
            errors.append("busqueda: %s" % exc)

    seen = {result.url for result in results}
    for url in urls:
        url = url.strip()
        if not url or url in seen:
            continue
        seen.add(url)
        results.append(WebResult(title=url, url=url, snippet="URL indicada por el usuario"))

    if not results:
        if errors:
            raise RuntimeError("; ".join(errors))
        raise RuntimeError("no hay resultados web; indica --query o --url")

    fetched = 0
    if not no_fetch:
        for result in results:
            if fetched >= fetch_results:
                break
            try:
                final_url, raw_html = fetch_url(
                    result.url,
                    timeout=timeout,
                    allow_private=allow_private,
                )
                title = _extract_title(raw_html) or result.title
                description = _extract_meta_description(raw_html)
                readable = _extract_readable_text(raw_html)
                excerpt = _select_excerpt(readable, query or title, max_chars_per_page)
                result.title = title
                result.url = final_url
                result.excerpt = excerpt
                result.code = _extract_code_blocks(raw_html)
                if not result.snippet and description:
                    result.snippet = description
                result.fetched = True
                fetched += 1
            except Exception as exc:
                result.error = str(exc)

    now = _dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    lines: List[str] = [
        "# Web context" + (": " + query if query else ""),
        "",
        "- Generado: " + now,
        "- Fuentes consultadas: %d" % len(results),
        "- Descargadas: %d" % fetched,
    ]
    if query:
        lines.append("- Query: `" + query + "`")
    lines.extend(
        [
            "",
            "## Como usar este contexto",
            "",
            "- Cita siempre la URL de la fuente que uses.",
            "- Verifica la version y la fecha: la web puede estar desactualizada.",
            "- Prioriza documentacion oficial, repositorios y RFCs.",
            "- Si una fuente no responde al problema, dilo y busca otra.",
            "",
        ]
    )
    if errors:
        lines.append("## Avisos")
        lines.append("")
        for error in errors:
            lines.append("- " + error)
        lines.append("")

    total_chars = 0
    for index, result in enumerate(results, 1):
        if total_chars >= max_total_chars:
            lines.append("... (mas resultados omitidos por presupuesto)")
            break
        lines.append("## %d. %s" % (index, result.title or result.url))
        lines.append("")
        lines.append("- URL: " + result.url)
        if result.snippet:
            lines.append("- Snippet: " + result.snippet.replace("\n", " "))
        if result.error:
            lines.append("- Error al descargar: " + result.error)
        if result.excerpt:
            excerpt = result.excerpt
            remaining = max_total_chars - total_chars
            if remaining <= 0:
                break
            if len(excerpt) > remaining:
                excerpt = excerpt[:remaining] + "\n... (truncado)"
            lines.append("")
            lines.append("### Extracto")
            lines.append("")
            lines.append(excerpt)
            total_chars += len(excerpt)
        if result.code and total_chars < max_total_chars:
            code_budget = max_total_chars - total_chars
            for block in result.code:
                if code_budget <= 0:
                    break
                block = block[:code_budget]
                lines.append("")
                lines.append("### Codigo")
                lines.append("")
                lines.append("```")
                lines.append(block)
                lines.append("```")
                total_chars += len(block)
                code_budget -= len(block)
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Busca y resume fuentes web para el contexto de desarrollo.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--query", "-q", default="", help="Consulta de busqueda")
    parser.add_argument(
        "--url",
        "-u",
        action="append",
        default=[],
        help="URL concreta a descargar (repetible)",
    )
    parser.add_argument("--max-results", type=int, default=5)
    parser.add_argument("--fetch-results", type=int, default=3)
    parser.add_argument("--max-chars-per-page", type=int, default=6000)
    parser.add_argument("--max-total-chars", type=int, default=24000)
    parser.add_argument("--no-fetch", action="store_true", help="Solo snippets, sin descargar")
    parser.add_argument(
        "--allow-private",
        action="store_true",
        help="Permite localhost/IPs privadas (usar con cuidado)",
    )
    parser.add_argument("--timeout", type=int, default=15)
    parser.add_argument("--out", "-o", default="", help="Archivo Markdown de salida")
    parser.add_argument("--quiet", action="store_true")
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    if not args.query and not args.url:
        print("Indica --query o --url.", file=sys.stderr)
        return 2

    if not args.quiet:
        print("[web-context] query=%s" % (args.query or "(sin query)"), file=sys.stderr)
        print("[web-context] urls=%d" % len(args.url), file=sys.stderr)

    try:
        markdown = build_web_context(
            query=args.query,
            urls=args.url,
            max_results=args.max_results,
            fetch_results=args.fetch_results,
            max_chars_per_page=args.max_chars_per_page,
            max_total_chars=args.max_total_chars,
            no_fetch=args.no_fetch,
            allow_private=args.allow_private,
            timeout=args.timeout,
        )
    except Exception as exc:
        print("[web-context] error: %s" % exc, file=sys.stderr)
        return 1

    output = markdown

    if args.out:
        out_path = os.path.abspath(args.out)
        os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as handle:
            handle.write(output)
        if not args.quiet:
            print("[web-context] escrito %s" % out_path, file=sys.stderr)
    else:
        sys.stdout.write(output)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
