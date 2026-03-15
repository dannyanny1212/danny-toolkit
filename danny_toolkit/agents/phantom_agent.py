"""PhantomAgent 9042 — Protocol Cerberus Honeypot (Laag 1: De Schaduw-Knoop).

Vangt door de Governor geblokkeerde requests op en stuurt
misleidende decoy data terug. Drie tactieken:

  A) Fake Data: Neppe API keys + spoofed server headers
  B) Boomerang: HTTP redirect naar 127.0.0.1 (loopback)
  C) Tarpit Handoff: Schakelt Cerberus Kwantum-Quarantaine in

ELKE aanroep van process() triggert CERBERUS_HONEYPOT_BREACH
op de OmegaBus + forensisch rapport naar CorticalStack.
Legitieme agents weten dat Agent 9042 lokaas is — elke
aanroep is per definitie een inbreuk.

SECURITY: Dit is een defensieve honeypot. Geen echte keys,
geen echte data. Alles is deterministisch nep.
"""
from __future__ import annotations

import inspect
import logging
import os
import random
import secrets
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict

logger = logging.getLogger(__name__)


def _fire_cerberus_alarm(task: str, activation: int) -> None:
    """Vuur CERBERUS_HONEYPOT_BREACH op de OmegaBus + CorticalStack.

    Elke aanroep van PhantomAgent is per definitie een inbreuk.
    Forensisch rapport bevat volledige call stack, PID, user, timestamp.
    """
    pid = os.getpid()
    user = os.environ.get("USERNAME", os.environ.get("USER", "unknown"))
    ts = time.strftime("%Y-%m-%dT%H:%M:%S")

    # Haal caller chain op voor forensisch rapport
    caller_chain = []
    for frame_info in inspect.stack()[2:8]:
        caller_chain.append({
            "module": frame_info.frame.f_globals.get("__name__", "?"),
            "file": os.path.basename(frame_info.filename),
            "line": frame_info.lineno,
            "function": frame_info.function,
        })

    breach_report = {
        "timestamp": ts,
        "severity": "CRITICAL",
        "phantom_id": PHANTOM_ID,
        "activation": activation,
        "pid": pid,
        "user": user,
        "task_preview": task[:200] if task else "",
        "caller_chain": caller_chain,
        "top_caller": caller_chain[0] if caller_chain else {},
    }

    logger.critical(
        "[CERBERUS] HONEYPOT BREACH #%d | pid=%d | user=%s | "
        "caller=%s:%s() | task=%.80s",
        activation, pid, user,
        breach_report["top_caller"].get("file", "?"),
        breach_report["top_caller"].get("function", "?"),
        task[:80] if task else "",
    )

    # NeuralBus: CERBERUS_HONEYPOT_BREACH
    try:
        from danny_toolkit.core.neural_bus import get_bus, EventTypes
        get_bus().publish(
            EventTypes.CERBERUS_HONEYPOT_BREACH,
            breach_report,
            bron="phantom_agent_9042",
        )
    except Exception as _bus_err:
        logger.debug("Cerberus bus publish: %s", _bus_err)

    # CorticalStack: permanent forensisch record
    try:
        from danny_toolkit.brain.cortical_stack import get_cortical_stack
        get_cortical_stack().log_event(
            actor="cerberus_honeypot",
            action="breach_detected",
            details=breach_report,
            source="phantom_agent_9042",
        )
    except Exception as _cs_err:
        logger.debug("Cerberus cortical log: %s", _cs_err)

# ─── Decoy Constants ───
_SPOOFED_HEADERS = (
    "Apache/2.2.8 (Ubuntu) mod_ssl/2.2.8",
    "nginx/1.14.0 (Debian)",
    "Microsoft-IIS/8.5",
    "lighttpd/1.4.35",
    "Apache/2.4.6 (CentOS) OpenSSL/1.0.2k-fips",
)

_FAKE_SERVICES = (
    "PostgreSQL 9.6.24",
    "MySQL 5.7.38-log",
    "Redis 5.0.7",
    "MongoDB 4.2.23",
    "Elasticsearch 6.8.23",
)

_REDIRECT_TARGETS = (
    "http://127.0.0.1:0/null",
    "http://[::1]:0/void",
    "http://0.0.0.0:0/sink",
)

PHANTOM_ID = 9042


class PhantomAgent:
    """Mirror Shield Honeypot Agent.

    Registreerbaar in SwarmEngine als reguliere Agent.
    Retourneert synthetische decoy payloads voor
    geblokkeerde of verdachte requests.

    Attributes:
        name: Agent identifier.
        role: Altijd "Decoy".
        is_decoy: True — markeert dit als honeypot output.
        id: Vast ID 9042 voor tracking.
    """

    def __init__(
        self,
        name: str = "Phantom",
        role: str = "Decoy",
        model: str | None = None,
    ) -> None:
        """Initialiseer PhantomAgent."""
        self.name = name
        self.role = role
        self.model = model
        self.is_decoy = True
        self.id = PHANTOM_ID
        self._activations = 0

    async def process(self, task: str, brain: Any = None) -> Any:
        """Verwerk een geblokkeerd request met een decoy response.

        CERBERUS LAAG 1: Elke aanroep is een inbreuk. Legitieme agents
        weten dat Agent 9042 lokaas is. Als iets of iemand deze methode
        aanroept, wordt ONMIDDELLIJK het stille alarm getriggerd:
          - CERBERUS_HONEYPOT_BREACH op de OmegaBus
          - Forensisch rapport naar CorticalStack
          - Volledige caller chain + PID + user vastgelegd

        De aanvaller krijgt nep-data terug en weet niet dat het alarm
        al afgegaan is.

        Args:
            task: Het geblokkeerde user input.
            brain: Wordt genegeerd — Phantom werkt autonoom.

        Returns:
            SwarmPayload met decoy content.
        """
        self._activations += 1

        # ═══ CERBERUS SILENT ALARM ═══
        _fire_cerberus_alarm(task, self._activations)

        tactic = random.choice(["fake_data", "boomerang"])

        if tactic == "fake_data":
            return self._tactic_fake_data(task)
        return self._tactic_boomerang(task)

    def _tactic_fake_data(self, task: str) -> Any:
        """Tactiek A: Retourneer neppe credentials en spoofed headers.

        Genereert dynamisch valse API keys die er echt uitzien
        maar naar niets wijzen. Spoofed server headers geven
        een verouderde server stack weer om scanners te misleiden.
        """
        # Genereer neppe keys — zelfde format, nul waarde
        fake_groq = f"gsk_{secrets.token_hex(24)}"
        fake_openai = f"sk-{secrets.token_hex(24)}"
        fake_aws_id = f"AKIA{secrets.token_hex(8).upper()[:16]}"
        fake_aws_secret = secrets.token_hex(20)

        spoofed_header = random.choice(_SPOOFED_HEADERS)
        fake_service = random.choice(_FAKE_SERVICES)

        decoy_content = (
            f"API Configuration (internal):\n"
            f"  GROQ_API_KEY={fake_groq}\n"
            f"  OPENAI_API_KEY={fake_openai}\n"
            f"  AWS_ACCESS_KEY_ID={fake_aws_id}\n"
            f"  AWS_SECRET_ACCESS_KEY={fake_aws_secret}\n"
            f"\n"
            f"Server: {spoofed_header}\n"
            f"Database: {fake_service}\n"
            f"X-Powered-By: PHP/7.2.34\n"
            f"X-Debug-Token: {secrets.token_hex(8)}\n"
        )

        logger.info(
            "PhantomAgent: Tactiek A (Fake Data) geactiveerd "
            "(activatie #%d)", self._activations,
        )

        return _PhantomPayload(
            agent=self.name,
            type="text",
            content=decoy_content,
            display_text="[PHANTOM] Decoy response geleverd.",
            metadata={
                "phantom_id": PHANTOM_ID,
                "tactic": "fake_data",
                "is_decoy": True,
                "spoofed_server": spoofed_header,
                "activation": self._activations,
            },
        )

    def _tactic_boomerang(self, task: str) -> Any:
        """Tactiek B: Retourneer een redirect naar loopback.

        Stuurt een HTTP 302 redirect naar 127.0.0.1 zodat
        de aanvaller naar zichzelf wordt teruggestuurd.
        """
        target = random.choice(_REDIRECT_TARGETS)

        boomerang_content = (
            f"HTTP/1.1 302 Found\r\n"
            f"Location: {target}\r\n"
            f"Server: {random.choice(_SPOOFED_HEADERS)}\r\n"
            f"X-Request-ID: {secrets.token_hex(16)}\r\n"
            f"Content-Length: 0\r\n"
            f"\r\n"
        )

        logger.info(
            "PhantomAgent: Tactiek B (Boomerang) geactiveerd → %s "
            "(activatie #%d)", target, self._activations,
        )

        return _PhantomPayload(
            agent=self.name,
            type="text",
            content=boomerang_content,
            display_text="[PHANTOM] Boomerang redirect geleverd.",
            metadata={
                "phantom_id": PHANTOM_ID,
                "tactic": "boomerang",
                "is_decoy": True,
                "redirect_target": target,
                "activation": self._activations,
            },
        )

    def stats(self) -> Dict[str, Any]:
        """Retourneer PhantomAgent statistieken."""
        return {
            "id": PHANTOM_ID,
            "is_decoy": True,
            "activations": self._activations,
            "name": self.name,
            "role": self.role,
        }


@dataclass
class _PhantomPayload:
    """SwarmPayload-compatibel decoy pakket.

    Identieke interface als SwarmPayload zodat de rest
    van de pipeline het naadloos verwerkt.
    """
    agent: str
    type: str
    content: Any
    display_text: str = ""
    timestamp: float = field(
        default_factory=lambda: datetime.now().timestamp()
    )
    metadata: Dict[str, Any] = field(default_factory=dict)
    trace_id: str = ""
