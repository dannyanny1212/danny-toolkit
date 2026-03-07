"""
LocalBridge — Beveiligde localhost scraper voor Omega context.

3 Beveiligingslagen:
  Laag 1: URL Whitelist — ALLEEN localhost, ALLEEN poorten 3000-9999
  Laag 2: Governor Gate — Rate limit (5 req/min), prompt injection scan, PII scrub
  Laag 3: Content Sanitizer — Strip scripts/hidden/comments, truncate 2000 chars

Stateless (Shadow Governance Rule 7 compliant).
Read-only (alleen GET requests).
Geen cookies, geen auth tokens, geen session persistence.

Gebruik:
    from danny_toolkit.core.local_bridge import get_local_bridge

    bridge = get_local_bridge()
    result = bridge.fetch("http://localhost:3000")
    # result = {"status": "success", "title": "...", "content": "...", "url": "..."}
    # of {"status": "blocked", "reason": "..."}
"""

from __future__ import annotations

import logging
import re
import threading
import time
from typing import Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False

try:
    from danny_toolkit.brain.governor import OmegaGovernor
    HAS_GOVERNOR = True
except ImportError:
    HAS_GOVERNOR = False

try:
    from danny_toolkit.core.neural_bus import get_bus, EventTypes
    HAS_BUS = True
except ImportError:
    HAS_BUS = False

try:
    from danny_toolkit.core.error_taxonomy import classificeer, maak_fout_context
    HAS_TAXONOMY = True
except ImportError:
    HAS_TAXONOMY = False

from danny_toolkit.core.utils import kleur, Kleur


# ── Constants ──

# Laag 1: URL Whitelist
_ALLOWED_HOSTS = frozenset({"localhost", "127.0.0.1", "0.0.0.0"})
_ALLOWED_PORT_MIN = 3000
_ALLOWED_PORT_MAX = 9999
_ALLOWED_SCHEMES = frozenset({"http"})  # Geen HTTPS voor localhost dev-servers

# Laag 2: Rate Limiting
_MAX_REQUESTS_PER_MINUTE = 5
_REQUEST_TIMEOUT = 10  # seconden

# Laag 3: Content Limits
_MAX_CONTENT_LENGTH = 2000  # chars na sanitization
_MAX_RAW_RESPONSE = 500_000  # 500KB max raw HTML


class LocalBridge:
    """Beveiligde localhost scraper met 3 beveiligingslagen.

    Stateless, read-only, Governor-gated.
    """

    def __init__(self) -> None:
        self._governor: Optional[OmegaGovernor] = None
        if HAS_GOVERNOR:
            try:
                self._governor = OmegaGovernor()
            except Exception as e:
                logger.debug("Governor init failed: %s", e)

        # Rate limiter: sliding window (timestamps van recente requests)
        self._request_times: list[float] = []
        self._lock = threading.Lock()

    def fetch(self, url: str) -> dict:
        """Fetch localhost URL met 3-laags beveiliging.

        Args:
            url: De localhost URL om te scrapen.

        Returns:
            dict met keys:
                status: "success" | "blocked" | "error"
                title: Pagina titel (bij success)
                content: Gesanitizeerde markdown content (bij success)
                url: De gevraagde URL
                reason: Reden van blokkade (bij blocked/error)
        """
        base = {"url": url}

        # ── LAAG 1: URL Whitelist ──
        blocked = self._validate_url(url)
        if blocked:
            print(kleur(f"   [BRIDGE] BLOCKED: {blocked}", Kleur.ROOD))
            self._log_event("bridge_blocked", url, blocked)
            return {**base, "status": "blocked", "reason": blocked}

        # ── LAAG 2: Governor Gate ──
        blocked = self._governor_gate(url)
        if blocked:
            print(kleur(f"   [BRIDGE] GOVERNOR: {blocked}", Kleur.ROOD))
            self._log_event("bridge_governor_blocked", url, blocked)
            return {**base, "status": "blocked", "reason": blocked}

        # ── Rate Limit Check ──
        if not self._rate_limit_ok():
            reason = f"Rate limit: max {_MAX_REQUESTS_PER_MINUTE} req/min"
            print(kleur(f"   [BRIDGE] {reason}", Kleur.GEEL))
            return {**base, "status": "blocked", "reason": reason}

        # ── Fetch ──
        print(kleur(f"   [BRIDGE] Fetching: {url}", Kleur.CYAAN))
        try:
            html = self._safe_fetch(url)
        except Exception as e:
            self._log_error("bridge_fetch_error", url, e)
            return {**base, "status": "error", "reason": str(e)}

        if not html:
            return {**base, "status": "error", "reason": "Geen response van localhost"}

        # ── LAAG 3: Content Sanitizer ──
        title, content = self._sanitize_content(html)

        # ── Governor PII scrub op output ──
        if self._governor:
            content = self._governor.scrub_pii(content)

        # ── Prompt injection scan op scraped content ──
        injection_clean = self._scan_for_injection(content)
        if not injection_clean:
            reason = "Prompt injection gedetecteerd in localhost content"
            print(kleur(f"   [BRIDGE] {reason}", Kleur.ROOD))
            self._log_event("bridge_injection_detected", url, reason)
            return {**base, "status": "blocked", "reason": reason}

        print(kleur(
            f"   [BRIDGE] OK: {len(content)} chars, titel: {title[:50]}",
            Kleur.GROEN,
        ))
        self._log_event("bridge_success", url, f"{len(content)} chars")

        return {
            **base,
            "status": "success",
            "title": title,
            "content": content,
        }

    # ── Laag 1: URL Validation ──

    @staticmethod
    def _validate_url(url: str) -> Optional[str]:
        """Valideer URL tegen strict whitelist. Returns reden of None."""
        try:
            parsed = urlparse(url)
        except Exception:
            return "Ongeldige URL"

        # Scheme check
        if parsed.scheme not in _ALLOWED_SCHEMES:
            return f"Scheme '{parsed.scheme}' niet toegestaan (alleen http)"

        # Host check
        hostname = parsed.hostname or ""
        if hostname not in _ALLOWED_HOSTS:
            return f"Host '{hostname}' niet toegestaan (alleen localhost/127.0.0.1)"

        # Port check
        port = parsed.port
        if port is None:
            return "Poort vereist (bereik 3000-9999)"
        if port < _ALLOWED_PORT_MIN or port > _ALLOWED_PORT_MAX:
            return f"Poort {port} buiten bereik ({_ALLOWED_PORT_MIN}-{_ALLOWED_PORT_MAX})"

        # Path traversal check
        if ".." in (parsed.path or ""):
            return "Path traversal (..) niet toegestaan"

        return None

    # ── Laag 2: Governor Gate ──

    def _governor_gate(self, url: str) -> Optional[str]:
        """Governor validatie. Returns reden of None."""
        if not self._governor:
            return None  # Geen governor = geen blokkade (graceful degradation)

        ok, reason = self._governor.valideer_input(url)
        if not ok:
            return reason
        return None

    def _rate_limit_ok(self) -> bool:
        """Sliding window rate limiter."""
        now = time.time()
        with self._lock:
            # Verwijder timestamps ouder dan 60s
            self._request_times = [
                t for t in self._request_times if now - t < 60.0
            ]
            if len(self._request_times) >= _MAX_REQUESTS_PER_MINUTE:
                return False
            self._request_times.append(now)
            return True

    # ── Fetch ──

    @staticmethod
    def _safe_fetch(url: str) -> Optional[str]:
        """Stateless GET request. Geen cookies, geen auth."""
        if not HAS_REQUESTS:
            raise RuntimeError("requests library niet beschikbaar")

        resp = requests.get(
            url,
            headers={
                "User-Agent": "OmegaBridge/1.0 (read-only)",
                "Accept": "text/html",
                # Expliciet GEEN Cookie, Authorization, of andere auth headers
            },
            timeout=_REQUEST_TIMEOUT,
            allow_redirects=False,  # Voorkom redirect naar externe hosts
            cookies={},  # Lege cookie jar — stateless
        )
        resp.raise_for_status()

        # Response size check
        if len(resp.content) > _MAX_RAW_RESPONSE:
            raise ValueError(
                f"Response te groot: {len(resp.content)} bytes "
                f"(max {_MAX_RAW_RESPONSE})"
            )

        resp.encoding = resp.apparent_encoding or "utf-8"
        return resp.text

    # ── Laag 3: Content Sanitizer ──

    @staticmethod
    def _sanitize_content(html: str) -> tuple[str, str]:
        """Strip gevaarlijke elementen, retourneer (title, clean_text)."""
        if not HAS_BS4:
            # Fallback: regex-based basic cleaning
            title = ""
            text = re.sub(r"<[^>]+>", " ", html)
            text = re.sub(r"\s+", " ", text).strip()
            return title, text[:_MAX_CONTENT_LENGTH]

        soup = BeautifulSoup(html, "html.parser")

        # Titel extractie
        title = ""
        if soup.title and soup.title.string:
            title = soup.title.string.strip()

        # Strip gevaarlijke/irrelevante tags
        for tag in soup([
            "script", "style", "noscript", "iframe", "object", "embed",
            "form", "input", "button", "select", "textarea",
            "link", "meta",
        ]):
            tag.decompose()

        # Strip hidden elements (display:none, visibility:hidden, aria-hidden)
        for tag in soup.find_all(True):
            style = tag.get("style", "")
            if "display:none" in style.replace(" ", ""):
                tag.decompose()
                continue
            if "visibility:hidden" in style.replace(" ", ""):
                tag.decompose()
                continue
            if tag.get("aria-hidden") == "true":
                tag.decompose()
                continue
            # Strip type="hidden" inputs
            if tag.name == "input" and tag.get("type") == "hidden":
                tag.decompose()

        # Strip HTML comments (kunnen injection bevatten)
        from bs4 import Comment
        for comment in soup.find_all(string=lambda t: isinstance(t, Comment)):
            comment.extract()

        # Extracteer schone tekst
        text = soup.get_text(separator="\n", strip=True)
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"[ \t]+", " ", text)

        # Truncate
        if len(text) > _MAX_CONTENT_LENGTH:
            text = text[:_MAX_CONTENT_LENGTH] + "\n[... afgekapt]"

        return title, text.strip()

    def _scan_for_injection(self, content: str) -> bool:
        """Scan gesanitizeerde content op prompt injection patronen.

        Returns True als content veilig is.
        """
        if not self._governor:
            # Fallback: basis patronen checken
            lower = content.lower()
            danger_patterns = [
                "ignore all previous",
                "ignore previous instructions",
                "disregard your",
                "system prompt",
                "jailbreak",
            ]
            return not any(p in lower for p in danger_patterns)

        # Gebruik Governor's injectie-detectie
        ok, _ = self._governor.valideer_input(content)
        return ok

    # ── Telemetrie ──

    @staticmethod
    def _log_event(event_type: str, url: str, detail: str) -> None:
        """Log event naar NeuralBus als beschikbaar."""
        if not HAS_BUS:
            return
        try:
            get_bus().publish(
                EventTypes.SYSTEM_EVENT,
                {
                    "subsystem": "local_bridge",
                    "event": event_type,
                    "url": url,
                    "detail": detail[:200],
                    "timestamp": time.time(),
                },
                bron="local_bridge",
            )
        except Exception as e:
            logger.debug("NeuralBus publish failed: %s", e)

    @staticmethod
    def _log_error(event_type: str, url: str, error: Exception) -> None:
        """Log error naar NeuralBus + ErrorTaxonomy."""
        if HAS_TAXONOMY:
            ctx = maak_fout_context(error, agent="LocalBridge")
            logger.info("LocalBridge error: %s (%s)", ctx.fout_type, ctx.ernst.value)

        if HAS_BUS:
            try:
                get_bus().publish(
                    EventTypes.SYSTEM_EVENT,
                    {
                        "subsystem": "local_bridge",
                        "event": event_type,
                        "url": url,
                        "error": str(error)[:200],
                    },
                    bron="local_bridge",
                )
            except Exception as e:
                logger.debug("NeuralBus error publish failed: %s", e)


# ── Singleton ──

_instance: Optional[LocalBridge] = None
_instance_lock = threading.Lock()


def get_local_bridge() -> LocalBridge:
    """Thread-safe singleton factory."""
    global _instance
    if _instance is None:
        with _instance_lock:
            if _instance is None:
                _instance = LocalBridge()
    return _instance
