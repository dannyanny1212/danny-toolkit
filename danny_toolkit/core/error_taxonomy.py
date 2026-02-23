"""
ErrorTaxonomy — Uniforme fout-classificatie voor Project Omega.

Centraliseert alle fouttypen, ernst-niveaus en herstelstrategieën.
Vervangt de verspreide _FOUT_CLASSIFICATIE patronen door één register.

Gebruik:
    from danny_toolkit.core.error_taxonomy import (
        classificeer, is_retry_safe, get_ernst, FoutContext,
    )

    definitie = classificeer("TimeoutError")
    if is_retry_safe("TimeoutError"):
        ...
"""

import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional, Union

logger = logging.getLogger(__name__)


# ─── Enums ───────────────────────────────────────────

class FoutErnst(str, Enum):
    """Ernst-niveau van een fout."""
    VOORBIJGAAND = "voorbijgaand"   # retry-safe (timeout, connection)
    HERSTELBAAR  = "herstelbaar"    # agent kan workaround (KeyError, ValueError)
    KRITIEK      = "kritiek"        # system-level (PermissionError, MemoryError)
    BEVEILIGING  = "beveiliging"    # injection/abuse detectie
    FATAAL       = "fataal"         # shutdown-worthy (disk full, corrupt DB)


class HerstelStrategie(str, Enum):
    """Aanbevolen actie bij een fout."""
    RETRY    = "retry"      # zelfde agent opnieuw
    FALLBACK = "fallback"   # alternatief agent/model
    SKIP     = "skip"       # overslaan, niet fataal
    BLOKKEER = "blokkeer"   # stop pipeline
    ESCALEER = "escaleer"   # alert + CorticalStack


# ─── FoutDefinitie ───────────────────────────────────

@dataclass
class FoutDefinitie:
    """Definitie van een fouttype in het register."""
    naam: str
    ernst: FoutErnst
    strategie: HerstelStrategie
    beschrijving: str
    retry_max: int = 0  # 0 = geen retry


# ─── FOUT_REGISTER ───────────────────────────────────

FOUT_REGISTER: Dict[str, FoutDefinitie] = {
    # ── VOORBIJGAAND (retry-safe) ──
    "TimeoutError": FoutDefinitie(
        "TimeoutError", FoutErnst.VOORBIJGAAND, HerstelStrategie.RETRY,
        "Agent of API timeout", retry_max=1,
    ),
    "asyncio.TimeoutError": FoutDefinitie(
        "asyncio.TimeoutError", FoutErnst.VOORBIJGAAND, HerstelStrategie.RETRY,
        "Asyncio timeout", retry_max=1,
    ),
    "ConnectionError": FoutDefinitie(
        "ConnectionError", FoutErnst.VOORBIJGAAND, HerstelStrategie.RETRY,
        "Netwerkverbinding mislukt", retry_max=2,
    ),
    "ConnectionResetError": FoutDefinitie(
        "ConnectionResetError", FoutErnst.VOORBIJGAAND, HerstelStrategie.RETRY,
        "Verbinding gereset door server", retry_max=2,
    ),
    "OSError": FoutDefinitie(
        "OSError", FoutErnst.VOORBIJGAAND, HerstelStrategie.RETRY,
        "OS-level I/O fout", retry_max=1,
    ),
    "RateLimitError": FoutDefinitie(
        "RateLimitError", FoutErnst.VOORBIJGAAND, HerstelStrategie.FALLBACK,
        "API rate limit bereikt",
    ),
    "APIStatusError": FoutDefinitie(
        "APIStatusError", FoutErnst.VOORBIJGAAND, HerstelStrategie.FALLBACK,
        "API retourneert fout status",
    ),
    "APIConnectionError": FoutDefinitie(
        "APIConnectionError", FoutErnst.VOORBIJGAAND, HerstelStrategie.RETRY,
        "API verbinding mislukt", retry_max=2,
    ),

    # ── HERSTELBAAR (skip/workaround) ──
    "ValueError": FoutDefinitie(
        "ValueError", FoutErnst.HERSTELBAAR, HerstelStrategie.SKIP,
        "Ongeldige waarde",
    ),
    "KeyError": FoutDefinitie(
        "KeyError", FoutErnst.HERSTELBAAR, HerstelStrategie.SKIP,
        "Ontbrekende sleutel",
    ),
    "TypeError": FoutDefinitie(
        "TypeError", FoutErnst.HERSTELBAAR, HerstelStrategie.SKIP,
        "Type mismatch",
    ),
    "AttributeError": FoutDefinitie(
        "AttributeError", FoutErnst.HERSTELBAAR, HerstelStrategie.SKIP,
        "Ontbrekend attribuut",
    ),
    "IndexError": FoutDefinitie(
        "IndexError", FoutErnst.HERSTELBAAR, HerstelStrategie.SKIP,
        "Index buiten bereik",
    ),
    "CircuitBreakerOpen": FoutDefinitie(
        "CircuitBreakerOpen", FoutErnst.HERSTELBAAR, HerstelStrategie.SKIP,
        "Agent circuit breaker staat open",
    ),
    "JSONDecodeError": FoutDefinitie(
        "JSONDecodeError", FoutErnst.HERSTELBAAR, HerstelStrategie.SKIP,
        "Ongeldig JSON formaat",
    ),

    # ── BEVEILIGING ──
    "PromptInjectionError": FoutDefinitie(
        "PromptInjectionError", FoutErnst.BEVEILIGING, HerstelStrategie.BLOKKEER,
        "Prompt injection gedetecteerd",
    ),
    "InputTooLongError": FoutDefinitie(
        "InputTooLongError", FoutErnst.BEVEILIGING, HerstelStrategie.BLOKKEER,
        "Input overschrijdt limiet",
    ),

    # ── KRITIEK ──
    "PermissionError": FoutDefinitie(
        "PermissionError", FoutErnst.KRITIEK, HerstelStrategie.ESCALEER,
        "Geen toegang tot bestand of resource",
    ),
    "RuntimeError": FoutDefinitie(
        "RuntimeError", FoutErnst.KRITIEK, HerstelStrategie.ESCALEER,
        "Runtime fout",
    ),

    # ── FATAAL ──
    "MemoryError": FoutDefinitie(
        "MemoryError", FoutErnst.FATAAL, HerstelStrategie.BLOKKEER,
        "Onvoldoende geheugen",
    ),
    "SystemExit": FoutDefinitie(
        "SystemExit", FoutErnst.FATAAL, HerstelStrategie.BLOKKEER,
        "Systeem shutdown",
    ),
}

# Fallback definitie voor onbekende fouten
_FALLBACK_DEFINITIE = FoutDefinitie(
    "Onbekend", FoutErnst.HERSTELBAAR, HerstelStrategie.SKIP,
    "Onbekend fouttype",
)


# ─── FoutContext ─────────────────────────────────────

@dataclass
class FoutContext:
    """Volledige context van een opgetreden fout.

    Bevat classificatie, trace info en herstelstatus.
    """
    fout_id: str
    fout_type: str
    agent: str
    ernst: FoutErnst
    strategie: HerstelStrategie
    bericht: str
    trace_id: str = ""
    timestamp: float = field(default_factory=time.time)
    herstel_geprobeerd: bool = False
    herstel_gelukt: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Serialiseer naar dict voor metadata/logging."""
        return {
            "fout_id": self.fout_id,
            "fout_type": self.fout_type,
            "agent": self.agent,
            "ernst": self.ernst.value,
            "strategie": self.strategie.value,
            "bericht": self.bericht,
            "trace_id": self.trace_id,
            "timestamp": self.timestamp,
            "herstel_geprobeerd": self.herstel_geprobeerd,
            "herstel_gelukt": self.herstel_gelukt,
        }


# ─── Publieke functies ───────────────────────────────

def classificeer(exception_or_name: Union[Exception, str]) -> FoutDefinitie:
    """Classificeer een fout op basis van exception of naam.

    Args:
        exception_or_name: Exception instantie of class naam string.

    Returns:
        FoutDefinitie uit FOUT_REGISTER, of fallback.
    """
    try:
        if isinstance(exception_or_name, Exception):
            naam = type(exception_or_name).__name__
        else:
            naam = str(exception_or_name)
        return FOUT_REGISTER.get(naam, _FALLBACK_DEFINITIE)
    except Exception as e:
        logger.debug("classificeer fout: %s", e)
        return _FALLBACK_DEFINITIE


def is_retry_safe(exception_or_name: Union[Exception, str]) -> bool:
    """Controleer of een fout veilig opnieuw geprobeerd kan worden.

    Returns:
        True als de fout VOORBIJGAAND is met RETRY strategie.
    """
    try:
        definitie = classificeer(exception_or_name)
        return (
            definitie.ernst == FoutErnst.VOORBIJGAAND
            and definitie.strategie == HerstelStrategie.RETRY
            and definitie.retry_max > 0
        )
    except Exception as e:
        logger.debug("is_retry_safe fout: %s", e)
        return False


def get_ernst(exception_or_name: Union[Exception, str]) -> FoutErnst:
    """Haal het ernst-niveau op van een fout.

    Returns:
        FoutErnst enum waarde.
    """
    try:
        return classificeer(exception_or_name).ernst
    except Exception as e:
        logger.debug("get_ernst fout: %s", e)
        return FoutErnst.HERSTELBAAR


def maak_fout_context(
    exception: Exception,
    agent: str,
    trace_id: str = "",
) -> FoutContext:
    """Maak een FoutContext aan voor een opgetreden fout.

    Args:
        exception: De opgetreden exception.
        agent: Naam van de agent waar de fout optrad.
        trace_id: Request trace ID.

    Returns:
        FoutContext met classificatie en metadata.
    """
    try:
        definitie = classificeer(exception)
        return FoutContext(
            fout_id=uuid.uuid4().hex[:8],
            fout_type=type(exception).__name__,
            agent=agent,
            ernst=definitie.ernst,
            strategie=definitie.strategie,
            bericht=str(exception)[:500],
            trace_id=trace_id,
        )
    except Exception as e:
        logger.debug("maak_fout_context fout: %s", e)
        return FoutContext(
            fout_id="fallback",
            fout_type="Onbekend",
            agent=agent,
            ernst=FoutErnst.HERSTELBAAR,
            strategie=HerstelStrategie.SKIP,
            bericht=str(exception)[:500],
        )
