"""
SmartKeyManager — Intelligent Groq API key management.

Werkt optimaal met 1 key (rate tracking, throttling, cooldown).
Schaalt automatisch naar multi-key wanneer extra keys beschikbaar zijn.

Singleton via get_key_manager(). Thread-safe.

Groq free tier limieten per key:
  - llama-4-scout:  30 RPM / 30K TPM / 500K TPD
  - qwen3-32b:      60 RPM / 6K TPM / 500K TPD
"""

import asyncio
import os
import time
import logging
import threading
from collections import defaultdict, deque
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# Groq rate limits per model familie (free tier)
try:
    from danny_toolkit.core.alerter import get_alerter, AlertLevel
    HAS_ALERTER = True
except ImportError:
    HAS_ALERTER = False

try:
    from danny_toolkit.core.config import Config as _Cfg
    _PRIMARY = _Cfg.LLM_MODEL
    _FALLBACK = _Cfg.LLM_FALLBACK_MODEL
except ImportError:
    _PRIMARY = "meta-llama/llama-4-scout-17b-16e-instruct"
    _FALLBACK = "qwen/qwen3-32b"

MODEL_LIMITS = {
    _PRIMARY: {
        "rpm": 30, "tpm": 30_000, "tpd": 500_000,
    },
    _FALLBACK: {
        "rpm": 60, "tpm": 6_000, "tpd": 500_000,
    },
}

# Standaard limieten voor onbekende modellen
DEFAULT_LIMITS = {"rpm": 30, "tpm": 6_000, "tpd": 500_000}

# Agent prioriteiten: hoe lager, hoe belangrijker (user-facing eerst)
AGENT_PRIORITY = {
    "CentralBrain": 0,       # User-facing — hoogste prioriteit
    "Tribunal": 1,            # Verificatie — realtime pipeline
    "AdversarialTribunal": 1,
    "Strategist": 2,          # Planning — kan wachten
    "VoidWalker": 3,          # Research — zwaarste verbruiker
    "Artificer": 3,           # Code forge — zwaar
    "TheCortex": 4,           # Knowledge graph — batch
    "DevOpsDaemon": 5,        # CI loop — laagste prioriteit
    "Dreamer": 5,             # Overnight — geen haast
    "GhostWriter": 5,         # Auto-docstring — geen haast
    "TheMirror": 5,           # Profiling — geen haast
}

# Cooldown per prioriteit (seconden wachten na rate limit hit)
PRIORITY_COOLDOWN = {
    0: 2.0,     # CentralBrain: minimale vertraging
    1: 5.0,     # Tribunal: korte cooldown
    2: 10.0,    # Strategist: matige cooldown
    3: 15.0,    # VoidWalker/Artificer: langere cooldown
    4: 20.0,    # TheCortex: kan wachten
    5: 30.0,    # Overnight agents: geen haast
}


@dataclass
class AgentMetrics:
    """Verbruiksmetrieken per agent."""

    naam: str
    prioriteit: int = 5
    # Sliding window requests (timestamps)
    request_timestamps: deque = field(default_factory=lambda: deque(maxlen=120))
    # Token tellers
    tokens_deze_minuut: int = 0
    tokens_dit_uur: int = 0
    tokens_vandaag: int = 0
    # Tijdstempels voor reset
    minuut_start: float = 0.0
    uur_start: float = 0.0
    dag_start: float = 0.0
    # Rate limit tracking
    laatste_429: float = 0.0
    cooldown_tot: float = 0.0
    totaal_429s: int = 0
    # Verbruik stats
    totaal_requests: int = 0
    totaal_tokens: int = 0


class SmartKeyManager:
    """
    Intelligente API key manager met per-agent rate tracking.

    Features:
    - Per-agent verbruiksmetrieken (RPM, TPM, TPD)
    - Prioriteit-gebaseerde cooldowns (user-facing < background)
    - Automatische throttle detectie
    - Multi-key support (schaalt wanneer keys beschikbaar)
    - Thread-safe singleton
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._metrics_lock = threading.Lock()

        # Laad alle beschikbare keys
        self._keys = self._discover_keys()
        self._primary_key = self._keys[0] if self._keys else ""

        # Per-agent metrieken
        self._agents: dict[str, AgentMetrics] = {}

        # Globale rate limit state
        self._global_429_count = 0
        self._global_cooldown_tot = 0.0

        logger.info(
            f"SmartKeyManager init: {len(self._keys)} key(s) geladen"
        )

    # ------------------------------------------------------------------
    # Key Discovery
    # ------------------------------------------------------------------

    @staticmethod
    def _discover_keys() -> list[str]:
        """Ontdek alle GROQ_API_KEY varianten uit environment."""
        keys = []

        # Primaire key
        primary = os.getenv("GROQ_API_KEY", "")
        if primary and primary.startswith("gsk_"):
            keys.append(primary)

        # Benoemde keys (role-based, voor toekomstige uitbreiding)
        named_vars = [
            "GROQ_API_KEY_USER",
            "GROQ_API_KEY_VERIFY",
            "GROQ_API_KEY_RESEARCH",
            "GROQ_API_KEY_WALKER",
            "GROQ_API_KEY_FORGE",
            "GROQ_API_KEY_OVERNIGHT",
            "GROQ_API_KEY_KNOWLEDGE",
        ]
        for var in named_vars:
            val = os.getenv(var, "")
            if val and val.startswith("gsk_") and val not in keys:
                keys.append(val)

        # Genummerde keys (GROQ_API_KEY_2 .. GROQ_API_KEY_20)
        for i in range(2, 21):
            val = os.getenv(f"GROQ_API_KEY_{i}", "")
            if val and val.startswith("gsk_") and val not in keys:
                keys.append(val)

        # Reserve keys
        for i in range(1, 4):
            val = os.getenv(f"GROQ_API_KEY_RESERVE_{i}", "")
            if val and val.startswith("gsk_") and val not in keys:
                keys.append(val)

        return keys

    # ------------------------------------------------------------------
    # Agent Registratie & Metrieken
    # ------------------------------------------------------------------

    def _get_agent(self, naam: str) -> AgentMetrics:
        """Haal of maak agent metrieken (thread-safe)."""
        with self._metrics_lock:
            if naam not in self._agents:
                prio = AGENT_PRIORITY.get(naam, 5)
                now = time.time()
                self._agents[naam] = AgentMetrics(
                    naam=naam,
                    prioriteit=prio,
                    minuut_start=now,
                    uur_start=now,
                    dag_start=now,
                )
            return self._agents[naam]

    def _reset_windows(self, agent: AgentMetrics):
        """Reset verlopen tijdvensters."""
        now = time.time()

        # Minuut-venster (60s)
        if now - agent.minuut_start >= 60:
            agent.tokens_deze_minuut = 0
            agent.minuut_start = now
            # Verwijder oude request timestamps
            cutoff = now - 60
            agent.request_timestamps = deque(
                (t for t in agent.request_timestamps if t > cutoff),
                maxlen=120,
            )

        # Uur-venster (3600s)
        if now - agent.uur_start >= 3600:
            agent.tokens_dit_uur = 0
            agent.uur_start = now

        # Dag-venster (86400s)
        if now - agent.dag_start >= 86400:
            agent.tokens_vandaag = 0
            agent.dag_start = now

    # ------------------------------------------------------------------
    # Throttle Check
    # ------------------------------------------------------------------

    def check_throttle(self, agent_naam: str, model: str = None) -> tuple[bool, str]:
        """
        Check of een agent mag requesten.

        Returns: (mag_door, reden)
        - (True, "") = vrij om te requesten
        - (False, reden) = moet wachten
        """
        agent = self._get_agent(agent_naam)
        now = time.time()

        with self._metrics_lock:
            self._reset_windows(agent)

            # 1. Cooldown na 429
            if now < agent.cooldown_tot:
                wacht = agent.cooldown_tot - now
                return False, f"Cooldown: {wacht:.1f}s resterend"

            # 2. Globale cooldown
            if now < self._global_cooldown_tot:
                wacht = self._global_cooldown_tot - now
                return False, f"Globale cooldown: {wacht:.1f}s"

            # 3. RPM check (requests per minuut)
            limits = MODEL_LIMITS.get(model, DEFAULT_LIMITS) if model else DEFAULT_LIMITS
            rpm_limit = limits["rpm"]
            current_rpm = len(agent.request_timestamps)
            if current_rpm >= rpm_limit:
                return False, f"RPM limiet ({rpm_limit})"

            # 4. TPM check (tokens per minuut)
            tpm_limit = limits["tpm"]
            if agent.tokens_deze_minuut >= tpm_limit * 0.9:
                return False, f"TPM limiet ({tpm_limit})"

            # 5. TPD check (tokens per dag)
            tpd_limit = limits["tpd"]
            if agent.tokens_vandaag >= tpd_limit * 0.95:
                return False, f"TPD limiet ({tpd_limit})"

            return True, ""

    # ------------------------------------------------------------------
    # Rate Limit Queue — wait instead of drop
    # ------------------------------------------------------------------

    MAX_QUEUE_WAIT = 30.0  # Maximum seconds to wait in queue

    async def async_enqueue(self, agent_naam: str, model: str = None) -> tuple:
        """Wait for rate limit clearance instead of dropping.

        Returns: (mag_door, reden)
        - (True, "OK") = cleared to request
        - (False, reason) = timed out after MAX_QUEUE_WAIT
        """
        start = time.time()
        while time.time() - start < self.MAX_QUEUE_WAIT:
            mag, reden = self.check_throttle(agent_naam, model)
            if mag:
                return True, "OK"
            wait_time = min(1.0, self.MAX_QUEUE_WAIT - (time.time() - start))
            if wait_time <= 0:
                break
            await asyncio.sleep(wait_time)
        return False, f"Queue timeout ({self.MAX_QUEUE_WAIT}s)"

    # ------------------------------------------------------------------
    # Registratie
    # ------------------------------------------------------------------

    def registreer_request(self, agent_naam: str):
        """Registreer dat een agent een API request doet."""
        agent = self._get_agent(agent_naam)
        with self._metrics_lock:
            agent.request_timestamps.append(time.time())
            agent.totaal_requests += 1

    def registreer_tokens(self, agent_naam: str, tekst: str):
        """Registreer tokenverbruik na response (char/4 schatting)."""
        tokens = len(tekst) // 4
        agent = self._get_agent(agent_naam)
        with self._metrics_lock:
            self._reset_windows(agent)
            agent.tokens_deze_minuut += tokens
            agent.tokens_dit_uur += tokens
            agent.tokens_vandaag += tokens
            agent.totaal_tokens += tokens

    def registreer_429(self, agent_naam: str):
        """Registreer een 429 rate limit hit."""
        agent = self._get_agent(agent_naam)
        now = time.time()
        cooldown = PRIORITY_COOLDOWN.get(agent.prioriteit, 30.0)

        with self._metrics_lock:
            agent.laatste_429 = now
            agent.totaal_429s += 1
            agent.cooldown_tot = now + cooldown
            self._global_429_count += 1

            # Escalerend: bij herhaalde 429s, langere globale cooldown
            if self._global_429_count >= 5:
                self._global_cooldown_tot = now + 60.0
                logger.warning(
                    f"SmartKeyManager: 5+ rate limits — globale cooldown 60s"
                )
                if HAS_ALERTER:
                    try:
                        get_alerter().alert(
                            AlertLevel.KRITIEK,
                            f"Globale rate limit: {self._global_429_count}x 429 — 60s cooldown",
                            bron="key_manager",
                        )
                    except Exception as e:
                        logger.debug("Alerter error: %s", e)
            elif self._global_429_count >= 3:
                self._global_cooldown_tot = now + 15.0

        logger.info(
            f"SmartKeyManager: 429 voor {agent_naam} — "
            f"cooldown {cooldown}s (prioriteit {agent.prioriteit})"
        )

    # ------------------------------------------------------------------
    # Key Selectie
    # ------------------------------------------------------------------

    def get_key(self, agent_naam: str = "") -> str:
        """
        Geef de beste API key voor een agent.

        Bij 1 key: altijd die ene key.
        Bij meerdere keys: round-robin of role-based.
        """
        if not self._keys:
            return os.getenv("GROQ_API_KEY", "")

        # Enkele key — simpel
        if len(self._keys) == 1:
            return self._keys[0]

        # Meerdere keys — verdeel op basis van prioriteit
        # Lage prioriteit agents krijgen latere keys
        agent = self._get_agent(agent_naam)
        idx = agent.prioriteit % len(self._keys)
        return self._keys[idx]

    # ------------------------------------------------------------------
    # Client Factories
    # ------------------------------------------------------------------

    def create_async_client(self, agent_naam: str = ""):
        """
        Maak een AsyncGroq client voor een agent.

        Gebruikt de optimale key op basis van agent prioriteit.
        Fallback: os.getenv("GROQ_API_KEY") als geen keys gevonden.
        """
        try:
            from groq import AsyncGroq
        except ImportError:
            logger.warning("groq package niet beschikbaar")
            return None

        key = self.get_key(agent_naam)
        if not key:
            logger.warning(
                f"Geen Groq key voor {agent_naam or 'onbekend'}"
            )
            return None

        return AsyncGroq(api_key=key)

    def create_sync_client(self, agent_naam: str = ""):
        """
        Maak een synchrone Groq client voor een agent.

        Gebruikt door CentralBrain (user-facing, sync pipeline).
        """
        try:
            from groq import Groq
        except ImportError:
            logger.warning("groq package niet beschikbaar")
            return None

        key = self.get_key(agent_naam)
        if not key:
            logger.warning(
                f"Geen Groq key voor {agent_naam or 'onbekend'}"
            )
            return None

        return Groq(api_key=key)

    # ------------------------------------------------------------------
    # Status & Diagnostiek
    # ------------------------------------------------------------------

    def get_status(self) -> dict:
        """Volledige status voor diagnostiek."""
        with self._metrics_lock:
            agents_status = {}
            for naam, agent in self._agents.items():
                self._reset_windows(agent)
                agents_status[naam] = {
                    "prioriteit": agent.prioriteit,
                    "rpm_huidig": len(agent.request_timestamps),
                    "tpm_huidig": agent.tokens_deze_minuut,
                    "tpd_huidig": agent.tokens_vandaag,
                    "totaal_requests": agent.totaal_requests,
                    "totaal_tokens": agent.totaal_tokens,
                    "totaal_429s": agent.totaal_429s,
                    "in_cooldown": time.time() < agent.cooldown_tot,
                }

            return {
                "keys_beschikbaar": len(self._keys),
                "globale_429s": self._global_429_count,
                "in_globale_cooldown": time.time() < self._global_cooldown_tot,
                "agents": agents_status,
            }

    def get_agent_summary(self, agent_naam: str) -> str:
        """Korte samenvatting voor een agent (voor logging)."""
        agent = self._get_agent(agent_naam)
        with self._metrics_lock:
            self._reset_windows(agent)
            return (
                f"{agent_naam}: {agent.totaal_requests} reqs, "
                f"{agent.totaal_tokens} tokens, "
                f"{agent.totaal_429s} rate limits"
            )

    def reset_counters(self):
        """Reset alle tellers (voor tests of dagelijkse reset)."""
        with self._metrics_lock:
            self._agents.clear()
            self._global_429_count = 0
            self._global_cooldown_tot = 0.0


# ------------------------------------------------------------------
# Singleton accessor
# ------------------------------------------------------------------

_manager_instance = None
_manager_lock = threading.Lock()


def get_key_manager() -> SmartKeyManager:
    """Singleton accessor voor SmartKeyManager."""
    global _manager_instance
    if _manager_instance is None:
        with _manager_lock:
            if _manager_instance is None:
                _manager_instance = SmartKeyManager()
    return _manager_instance
