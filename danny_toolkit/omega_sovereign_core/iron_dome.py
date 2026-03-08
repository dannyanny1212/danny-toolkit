"""
Iron Dome — Default-Deny Network Perimeter (IJzeren Wet #7).

Beheert een whitelist van toegestane uitgaande netwerk-endpoints.
Audit alle connecties en blokkeer/log ongeautoriseerd verkeer.
Werkt als software-laag bovenop de OS firewall.

Gebruik:
    from danny_toolkit.omega_sovereign_core.iron_dome import (
        get_iron_dome, IronDome
    )
    dome = get_iron_dome()
    allowed, reason = dome.check_endpoint("api.groq.com", 443)
"""

from __future__ import annotations

import logging
import socket
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Deque, Dict, FrozenSet, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

try:
    from danny_toolkit.core.utils import Kleur
except ImportError:
    class Kleur:
        GROEN = ROOD = GEEL = CYAAN = RESET = ""


# ── Default Whitelist ──

_DEFAULT_WHITELIST: FrozenSet[str] = frozenset({
    # LLM Providers
    "api.groq.com",
    "api.anthropic.com",
    "api.voyageai.com",
    "integrate.api.nvidia.com",
    "api-inference.huggingface.co",
    "huggingface.co",
    # Local Ollama
    "localhost",
    "127.0.0.1",
    "0.0.0.0",
    # Code & Packages
    "github.com",
    "api.github.com",
    "raw.githubusercontent.com",
    "pypi.org",
    "files.pythonhosted.org",
    # Telegram Bot
    "api.telegram.org",
    # DuckDuckGo (VoidWalker)
    "duckduckgo.com",
    "html.duckduckgo.com",
    "links.duckduckgo.com",
    # DNS (Windows resolver)
    "dns.google",
    "1.1.1.1",
    "8.8.8.8",
})

_BLOCKED_PORTS: FrozenSet[int] = frozenset({
    # Gevaarlijke poorten die nooit nodig zijn
    25,    # SMTP (spam/relay)
    135,   # RPC
    137, 138, 139,  # NetBIOS
    445,   # SMB
    3389,  # RDP (inkomend is al geblokt, uitgaand ook weigeren)
    5985, 5986,  # WinRM
})


@dataclass
class ConnectionAudit:
    """Record van een gecontroleerde connectie."""
    timestamp: str
    host: str
    port: int
    allowed: bool
    reason: str
    resolved_ip: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """To dict."""
        return {
            "timestamp": self.timestamp,
            "host": self.host,
            "port": self.port,
            "allowed": self.allowed,
            "reason": self.reason,
            "resolved_ip": self.resolved_ip,
        }


class IronDome:
    """
    Default-Deny uitgaand netwerk perimeter.

    Elke connectie wordt gecontroleerd tegen de whitelist.
    Onbekende hosts worden gelogd en geweigerd.
    Poort-blacklist voorkomt laterale beweging.
    """

    _MAX_AUDIT_LOG = 1000

    def __init__(
        self,
        extra_whitelist: Optional[Set[str]] = None,
        strict_mode: bool = True,
    ) -> None:
        """Init  ."""
        self._lock = threading.Lock()
        self._whitelist: Set[str] = set(_DEFAULT_WHITELIST)
        if extra_whitelist:
            self._whitelist.update(extra_whitelist)
        self._strict = strict_mode
        self._audit_log: Deque[ConnectionAudit] = deque(maxlen=self._MAX_AUDIT_LOG)
        self._stats = {
            "checked": 0,
            "allowed": 0,
            "blocked": 0,
            "port_blocked": 0,
        }
        self._stack = None
        self._init_cortical()

    def _init_cortical(self) -> None:
        """Lazy CorticalStack verbinding."""
        try:
            from danny_toolkit.brain.cortical_stack import get_cortical_stack
            self._stack = get_cortical_stack()
        except ImportError:
            logger.debug("CorticalStack niet beschikbaar voor Iron Dome")

    # ── Whitelist Management ──

    def add_to_whitelist(self, host: str) -> None:
        """Voeg een host toe aan de whitelist (runtime)."""
        with self._lock:
            self._whitelist.add(host.lower().strip())
        logger.info("Iron Dome: '%s' toegevoegd aan whitelist", host)

    def remove_from_whitelist(self, host: str) -> None:
        """Verwijder een host van de whitelist."""
        with self._lock:
            self._whitelist.discard(host.lower().strip())
        logger.info("Iron Dome: '%s' verwijderd van whitelist", host)

    def get_whitelist(self) -> List[str]:
        """Haal de huidige whitelist op."""
        with self._lock:
            return sorted(self._whitelist)

    # ── Endpoint Check ──

    def check_endpoint(self, host: str, port: int = 443) -> Tuple[bool, str]:
        """
        Controleer of een uitgaande connectie is toegestaan.

        Args:
            host: Doel-hostname of IP
            port: Doel-poort

        Returns:
            (True, "ALLOWED: reden") of (False, "BLOCKED: reden")
        """
        host_lower = host.lower().strip()
        now = datetime.now().isoformat()

        with self._lock:
            self._stats["checked"] += 1

        # ── Poort blacklist ──
        if port in _BLOCKED_PORTS:
            reason = f"BLOCKED: poort {port} is op de blacklist"
            self._record_audit(now, host_lower, port, False, reason)
            with self._lock:
                self._stats["port_blocked"] += 1
                self._stats["blocked"] += 1
            return False, reason

        # ── Whitelist check ──
        with self._lock:
            is_whitelisted = host_lower in self._whitelist

        if is_whitelisted:
            reason = "ALLOWED: host op whitelist"
            self._record_audit(now, host_lower, port, True, reason)
            with self._lock:
                self._stats["allowed"] += 1
            return True, reason

        # ── Subdomain check (*.github.com etc.) ──
        with self._lock:
            for wl_host in self._whitelist:
                if host_lower.endswith(f".{wl_host}"):
                    reason = f"ALLOWED: subdomain van {wl_host}"
                    self._record_audit(now, host_lower, port, True, reason)
                    self._stats["allowed"] += 1
                    return True, reason

        # ── DNS reverse lookup (optioneel) ──
        resolved_ip = ""
        try:
            resolved_ip = socket.gethostbyname(host_lower)
            with self._lock:
                if resolved_ip in self._whitelist:
                    reason = f"ALLOWED: resolved IP {resolved_ip} op whitelist"
                    self._record_audit(now, host_lower, port, True, reason, resolved_ip)
                    self._stats["allowed"] += 1
                    return True, reason
        except socket.gaierror:
            logger.debug("DNS lookup mislukt voor: %s", host_lower)

        # ── BLOCKED ──
        reason = f"BLOCKED: '{host_lower}:{port}' niet op whitelist (default-deny)"
        self._record_audit(now, host_lower, port, False, reason, resolved_ip)
        with self._lock:
            self._stats["blocked"] += 1

        if self._strict:
            print(f"{Kleur.ROOD}[IRON DOME] Geblokkeerd: {host_lower}:{port}{Kleur.RESET}")

        return False, reason

    def check_url(self, url: str) -> Tuple[bool, str]:
        """
        Controleer een volledige URL (extract host + port).

        Args:
            url: Volledige URL (https://api.groq.com/v1/chat)

        Returns:
            (allowed, reason)
        """
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            host = parsed.hostname or ""
            port = parsed.port or (443 if parsed.scheme == "https" else 80)
            return self.check_endpoint(host, port)
        except Exception as e:
            return False, f"BLOCKED: URL parse fout: {e}"

    # ── Active Connection Scanning ──

    def scan_active_connections(self) -> List[Dict[str, Any]]:
        """
        Scan actieve TCP-connecties en rapporteer onbekende endpoints.
        Gebruikt psutil als beschikbaar, anders netstat fallback.
        """
        unknown = []
        try:
            import psutil
            for conn in psutil.net_connections(kind="tcp"):
                if conn.status == "ESTABLISHED" and conn.raddr:
                    remote_ip = conn.raddr.ip
                    remote_port = conn.raddr.port
                    allowed, reason = self.check_endpoint(remote_ip, remote_port)
                    if not allowed:
                        unknown.append({
                            "pid": conn.pid,
                            "remote": f"{remote_ip}:{remote_port}",
                            "status": conn.status,
                            "reason": reason,
                        })
        except ImportError:
            logger.debug("psutil niet beschikbaar voor connection scanning")
        except Exception as e:
            logger.debug("Connection scan fout: %s", e)
        return unknown

    # ── Audit Log ──

    def _record_audit(
        self,
        timestamp: str,
        host: str,
        port: int,
        allowed: bool,
        reason: str,
        resolved_ip: str = "",
    ) -> None:
        """Registreer een connectie-controle."""
        audit = ConnectionAudit(
            timestamp=timestamp,
            host=host,
            port=port,
            allowed=allowed,
            reason=reason,
            resolved_ip=resolved_ip,
        )
        with self._lock:
            self._audit_log.append(audit)

        # Log geblokkeerde connecties naar CorticalStack
        if not allowed and self._stack:
            try:
                self._stack.log_event(
                    bron="IronDome",
                    event_type="sovereign.network.blocked",
                    data=audit.to_dict(),
                )
            except Exception as e:
                logger.debug("CorticalStack audit log mislukt: %s", e)

    def get_audit_log(self, count: int = 50, blocked_only: bool = False) -> List[Dict]:
        """Haal recente audit records op."""
        with self._lock:
            entries = list(self._audit_log)
        if blocked_only:
            entries = [e for e in entries if not e.allowed]
        return [e.to_dict() for e in entries[-count:]]

    # ── Stats ──

    def get_stats(self) -> Dict[str, Any]:
        """Haal Iron Dome statistieken op."""
        with self._lock:
            return {
                **self._stats,
                "whitelist_size": len(self._whitelist),
                "audit_log_size": len(self._audit_log),
                "strict_mode": self._strict,
            }


# ── Singleton ──

_dome_instance: Optional[IronDome] = None
_dome_lock = threading.Lock()


def get_iron_dome(
    extra_whitelist: Optional[Set[str]] = None,
    strict_mode: bool = True,
) -> IronDome:
    """Verkrijg de singleton IronDome instantie."""
    global _dome_instance
    if _dome_instance is None:
        with _dome_lock:
            if _dome_instance is None:
                _dome_instance = IronDome(
                    extra_whitelist=extra_whitelist,
                    strict_mode=strict_mode,
                )
    return _dome_instance
