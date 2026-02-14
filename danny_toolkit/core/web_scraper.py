# danny_toolkit/core/web_scraper.py — HTML Web Scraper voor RAG indexing
"""
Scrapet websites en zet HTML om naar schone tekst voor de RAG pipeline.
Ondersteunt:
  - Enkele URL scrapen
  - Meerdere URL's scrapen
  - Interne links volgen (--depth)
"""

import re
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


def scrape_url(url: str, chunk_size: int = 500, overlap: int = 50) -> list[dict]:
    """Fetch een URL en retourneer chunks klaar voor indexing.

    Returns list of dicts: {"text": str, "source": str, "chunk": int, "page": None}
    """
    print(f"  Scraping: {url}")
    html = _fetch(url)
    if not html:
        return []

    title, text = _parse_html(html)
    if not text.strip():
        print(f"  [!] Geen tekst gevonden op {url}")
        return []

    chunks = _chunk_text(text, chunk_size, overlap)
    source = title or url

    result = []
    for i, chunk in enumerate(chunks):
        result.append({
            "text": chunk,
            "source": url,
            "title": source,
            "chunk": i,
            "page": None,
        })

    print(f"  {len(result)} chunks van {url}")
    return result


def scrape_urls(urls: list[str], chunk_size: int = 500, overlap: int = 50) -> list[dict]:
    """Scrape meerdere URL's en retourneer alle chunks."""
    all_chunks = []
    for url in urls:
        chunks = scrape_url(url, chunk_size, overlap)
        all_chunks.extend(chunks)
    return all_chunks


def scrape_with_depth(start_url: str, depth: int = 0,
                      chunk_size: int = 500, overlap: int = 50) -> list[dict]:
    """Scrape een URL en volg interne links tot een bepaalde diepte.

    depth=0: alleen de opgegeven URL
    depth=1: de URL + alle interne links op die pagina
    depth=N: recursief tot N niveaus diep
    """
    visited = set()
    all_chunks = []

    def _crawl(url: str, current_depth: int):
        normalized = url.rstrip("/")
        if normalized in visited:
            return
        visited.add(normalized)

        # Scrape deze pagina
        chunks = scrape_url(url, chunk_size, overlap)
        all_chunks.extend(chunks)

        # Stop als we de maximale diepte bereikt hebben
        if current_depth >= depth:
            return

        # Haal interne links op
        html = _fetch(url)
        if not html:
            return

        links = _extract_internal_links(html, url)
        for link in links:
            _crawl(link, current_depth + 1)

    _crawl(start_url, 0)

    print(f"\n  Totaal: {len(visited)} pagina's gescraped, {len(all_chunks)} chunks")
    return all_chunks


# ═══════════════════════════════════════════
# Interne functies
# ═══════════════════════════════════════════

def _fetch(url: str) -> str | None:
    """Fetch een URL en retourneer de HTML."""
    headers = {
        "User-Agent": "DannyToolkit/5.0 RAG-Scraper",
        "Accept": "text/html,application/xhtml+xml",
    }
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding or "utf-8"
        return resp.text
    except requests.RequestException as e:
        print(f"  [!] Fout bij ophalen {url}: {e}")
        return None


def _parse_html(html: str) -> tuple[str, str]:
    """Parse HTML en retourneer (title, schone_tekst)."""
    soup = BeautifulSoup(html, "html.parser")

    # Haal titel op
    title = ""
    if soup.title and soup.title.string:
        title = soup.title.string.strip()

    # Verwijder ongewenste elementen
    for tag in soup(["script", "style", "nav", "footer", "header",
                     "aside", "form", "noscript", "iframe"]):
        tag.decompose()

    # Extraheer tekst
    text = soup.get_text(separator="\n", strip=True)

    # Clean up
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)

    return title, text.strip()


def _extract_internal_links(html: str, base_url: str) -> list[str]:
    """Extraheer interne links uit HTML."""
    soup = BeautifulSoup(html, "html.parser")
    base_domain = urlparse(base_url).netloc
    links = []

    for a in soup.find_all("a", href=True):
        href = a["href"]
        full_url = urljoin(base_url, href)

        # Alleen interne links (zelfde domein)
        parsed = urlparse(full_url)
        if parsed.netloc != base_domain:
            continue

        # Skip anchors, mailto, javascript
        if parsed.scheme not in ("http", "https"):
            continue

        # Strip fragment
        clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        if parsed.query:
            clean_url += f"?{parsed.query}"

        if clean_url not in links:
            links.append(clean_url)

    return links


def _chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Split tekst in overlappende chunks op basis van woordenaantal."""
    words = text.split()
    if len(words) <= chunk_size:
        return [text.strip()] if text.strip() else []

    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunk = " ".join(words[start:end])
        if chunk.strip():
            chunks.append(chunk.strip())
        start += chunk_size - overlap

    return chunks
