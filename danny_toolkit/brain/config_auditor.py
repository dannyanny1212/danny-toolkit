"""
ConfigAuditor — Runtime configuratie-validatie voor Project Omega.

Valideert model allowlists, API URL patronen, key prefixen,
pad validiteit en detecteert config drift via SHA-256 snapshots.

Singleton via get_config_auditor().
"""

from __future__ import annotations

import hashlib
import logging
import os
import re
import threading
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

from danny_toolkit.core.config import Config

# ─── Dataclasses ─────────────────────────────────────

@dataclass
class AuditSchending:
    """Eén gedetecteerde configuratie-schending."""
    categorie: str          # "model", "url", "key", "pad", "drift"
    ernst: str              # "kritiek", "waarschuwing", "info"
    beschrijving: str
    sleutel: str            # Config-attribuut of env-var naam


@dataclass
class AuditRapport:
    """Resultaat van een volledige audit run."""
    veilig: bool
    schendingen: List[AuditSchending] = field(default_factory=list)
    drift_gedetecteerd: bool = False
    gecontroleerd: int = 0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


# ─── Allowlists ──────────────────────────────────────

GROQ_MODELS = {
    "meta-llama/llama-4-scout-17b-16e-instruct",
    "meta-llama/llama-4-maverick-17b-128e-instruct",
    "qwen/qwen3-32b",
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "llama3-70b-8192",
    "llama3-8b-8192",
    "mixtral-8x7b-32768",
    "gemma2-9b-it",
    "deepseek-r1-distill-llama-70b",
}

OLLAMA_MODELS = {
    "llava:latest",
    "llava",
    "llama3.2:3b",
    "llama3.1:8b",
    "mistral",
    "codellama",
    "phi3",
}

ANTHROPIC_MODELS = {
    "claude-sonnet-4-20250514",
    "claude-opus-4-20250514",
    "claude-3-5-sonnet-20241022",
    "claude-3-5-haiku-20241022",
    "claude-3-opus-20240229",
    "claude-3-sonnet-20240229",
    "claude-3-haiku-20240307",
}

NVIDIA_NIM_MODELS = {
    "qwen/qwen2.5-coder-32b-instruct",
    "meta/llama-3.1-405b-instruct",
    "nvidia/llama-3.1-nemotron-70b-instruct",
    "deepseek-ai/deepseek-r1",
}

PROVIDER_MODELS = {
    "groq": GROQ_MODELS,
    "ollama": OLLAMA_MODELS,
    "anthropic": ANTHROPIC_MODELS,
    "nvidia_nim": NVIDIA_NIM_MODELS,
}

# ─── Key prefixes ────────────────────────────────────

KEY_PREFIXES = {
    "GROQ_API_KEY": "gsk_",
    "ANTHROPIC_API_KEY": "sk-ant-",
    "VOYAGE_API_KEY": "pa-",
}

# Minimale key-lengte per provider
KEY_MIN_LEN = {
    "GROQ_API_KEY": 20,
    "ANTHROPIC_API_KEY": 20,
    "VOYAGE_API_KEY": 10,
}

# AgentKeyManager role keys (zelfde prefix als GROQ)
AGENT_KEY_VARS = [
    "GROQ_API_KEY_USER",
    "GROQ_API_KEY_VERIFY",
    "GROQ_API_KEY_RESEARCH",
    "GROQ_API_KEY_WALKER",
    "GROQ_API_KEY_FORGE",
    "GROQ_API_KEY_OVERNIGHT",
    "GROQ_API_KEY_KNOWLEDGE",
    "GROQ_API_KEY_RESERVE_1",
    "GROQ_API_KEY_RESERVE_2",
    "GROQ_API_KEY_RESERVE_3",
]

# ─── URL whitelist ───────────────────────────────────

URL_PATTERNS = {
    "NVIDIA_NIM_BASE_URL": re.compile(
        r"^https://(integrate\.api\.nvidia\.com|[a-z0-9.-]+\.nvidia\.com)/v\d+/?$"
    ),
}

# ─── Snapshot keys ───────────────────────────────────

SNAPSHOT_ENV_KEYS = [
    "GROQ_API_KEY", "ANTHROPIC_API_KEY", "VOYAGE_API_KEY",
    "NVIDIA_NIM_API_KEY", "NVIDIA_NIM_BASE_URL", "NVIDIA_NIM_MODEL",
    "FASTAPI_SECRET_KEY", "TELEGRAM_BOT_TOKEN",
    "ELEVENLABS_API_KEY", "OPENAI_API_KEY",
] + AGENT_KEY_VARS


# ═══════════════════════════════════════════════════════
# ConfigAuditor
# ═══════════════════════════════════════════════════════

class ConfigAuditor:
    """Runtime configuratie-auditor.

    Valideert model allowlists, API URLs, key formaten,
    paden en detecteert env-var drift via SHA-256.
    """

    def __init__(self) -> None:
        """Initializes the object with default state.

 Sets up the baseline and last rapport attributes.

 Attributes:
  _baseline: A dictionary of baseline data, where keys and values are strings.
  _last_rapport: The last AuditRapport object."""
        self._baseline: Optional[Dict[str, str]] = None
        self._last_rapport: Optional[AuditRapport] = None

    # ─── Model validatie ─────────────────────────────

    def _check_models(self) -> List[AuditSchending]:
        """Controleer of configuratie-modellen in de allowlist staan."""
        schendingen = []
        checks = [
            ("LLM_MODEL", Config.LLM_MODEL, "groq"),
            ("LLM_FALLBACK_MODEL", Config.LLM_FALLBACK_MODEL, "groq"),
            ("VISION_MODEL", Config.VISION_MODEL, "ollama"),
            ("CLAUDE_MODEL", Config.CLAUDE_MODEL, "anthropic"),
            ("NVIDIA_NIM_MODEL", Config.NVIDIA_NIM_MODEL, "nvidia_nim"),
        ]
        for attr, waarde, provider in checks:
            if not waarde:
                continue
            allowlist = PROVIDER_MODELS.get(provider, set())
            if waarde not in allowlist:
                schendingen.append(AuditSchending(
                    categorie="model",
                    ernst="waarschuwing",
                    beschrijving=(
                        f"{attr}='{waarde}' niet in {provider} allowlist"
                    ),
                    sleutel=attr,
                ))
        return schendingen

    # ─── URL validatie ───────────────────────────────

    def _check_urls(self) -> List[AuditSchending]:
        """Controleer API URL patronen."""
        schendingen = []
        for attr, pattern in URL_PATTERNS.items():
            waarde = getattr(Config, attr, "")
            if not waarde:
                continue
            if not pattern.match(waarde):
                schendingen.append(AuditSchending(
                    categorie="url",
                    ernst="kritiek",
                    beschrijving=(
                        f"{attr}='{waarde}' matcht geen bekend patroon"
                    ),
                    sleutel=attr,
                ))
        return schendingen

    # ─── Key validatie ───────────────────────────────

    def _check_keys(self) -> List[AuditSchending]:
        """Controleer API key prefixen en minimale lengte."""
        schendingen = []

        # Hoofd-keys
        for env_var, prefix in KEY_PREFIXES.items():
            waarde = os.environ.get(env_var, "")
            if not waarde:
                continue
            if not waarde.startswith(prefix):
                schendingen.append(AuditSchending(
                    categorie="key",
                    ernst="kritiek",
                    beschrijving=(
                        f"{env_var} mist verwachte prefix '{prefix}'"
                    ),
                    sleutel=env_var,
                ))
            min_len = KEY_MIN_LEN.get(env_var, 10)
            if len(waarde) < min_len:
                schendingen.append(AuditSchending(
                    categorie="key",
                    ernst="waarschuwing",
                    beschrijving=(
                        f"{env_var} te kort ({len(waarde)} < {min_len})"
                    ),
                    sleutel=env_var,
                ))

        # AgentKeyManager role keys
        for env_var in AGENT_KEY_VARS:
            waarde = os.environ.get(env_var, "")
            if not waarde:
                continue
            if not waarde.startswith("gsk_"):
                schendingen.append(AuditSchending(
                    categorie="key",
                    ernst="waarschuwing",
                    beschrijving=(
                        f"{env_var} mist Groq prefix 'gsk_'"
                    ),
                    sleutel=env_var,
                ))

        return schendingen

    # ─── Pad validatie ───────────────────────────────

    def _check_paden(self) -> List[AuditSchending]:
        """Controleer of kritieke paden bestaan en leesbaar zijn."""
        schendingen = []
        paden = {
            "DATA_DIR": Config.DATA_DIR,
            "RAG_DATA_DIR": Config.RAG_DATA_DIR,
            "APPS_DATA_DIR": Config.APPS_DATA_DIR,
            "LOG_DIR": Config.LOG_DIR,
            "BACKUP_DIR": Config.BACKUP_DIR,
        }
        for naam, pad in paden.items():
            if not pad.exists():
                schendingen.append(AuditSchending(
                    categorie="pad",
                    ernst="waarschuwing",
                    beschrijving=f"{naam} bestaat niet: {pad}",
                    sleutel=naam,
                ))
            elif not os.access(str(pad), os.R_OK):
                schendingen.append(AuditSchending(
                    categorie="pad",
                    ernst="kritiek",
                    beschrijving=f"{naam} niet leesbaar: {pad}",
                    sleutel=naam,
                ))
        return schendingen

    # ─── Snapshot & Drift ────────────────────────────

    def snapshot(self) -> Dict[str, str]:
        """Maak SHA-256 snapshot van huidige env vars.

        Returns:
            Dict van env-var naam -> SHA-256 hash (of 'ABSENT').
        """
        snap = {}
        for key in SNAPSHOT_ENV_KEYS:
            waarde = os.environ.get(key, "")
            if waarde:
                snap[key] = hashlib.sha256(
                    waarde.encode("utf-8")
                ).hexdigest()
            else:
                snap[key] = "ABSENT"
        return snap

    def detect_drift(self) -> List[AuditSchending]:
        """Vergelijk huidige env met opgeslagen baseline.

        Returns:
            Lijst van drift-schendingen, leeg als geen baseline.
        """
        if self._baseline is None:
            return []

        huidig = self.snapshot()
        schendingen = []

        for key in SNAPSHOT_ENV_KEYS:
            oud = self._baseline.get(key, "ABSENT")
            nieuw = huidig.get(key, "ABSENT")
            if oud != nieuw:
                if oud == "ABSENT":
                    actie = "toegevoegd"
                elif nieuw == "ABSENT":
                    actie = "verwijderd"
                else:
                    actie = "gewijzigd"
                schendingen.append(AuditSchending(
                    categorie="drift",
                    ernst="waarschuwing",
                    beschrijving=f"{key} is {actie} sinds baseline",
                    sleutel=key,
                ))

        return schendingen

    # ─── Volledige audit ─────────────────────────────

    def audit(self) -> AuditRapport:
        """Voer volledige configuratie-audit uit.

        Returns:
            AuditRapport met alle bevindingen.
        """
        alle_schendingen: List[AuditSchending] = []
        gecontroleerd = 0

        # Model checks
        model_s = self._check_models()
        alle_schendingen.extend(model_s)
        gecontroleerd += 5

        # URL checks
        url_s = self._check_urls()
        alle_schendingen.extend(url_s)
        gecontroleerd += len(URL_PATTERNS)

        # Key checks
        key_s = self._check_keys()
        alle_schendingen.extend(key_s)
        gecontroleerd += len(KEY_PREFIXES) + len(AGENT_KEY_VARS)

        # Pad checks
        pad_s = self._check_paden()
        alle_schendingen.extend(pad_s)
        gecontroleerd += 5

        # Drift checks
        drift_s = self.detect_drift()
        alle_schendingen.extend(drift_s)
        drift_gedetecteerd = len(drift_s) > 0
        gecontroleerd += len(SNAPSHOT_ENV_KEYS)

        # Sla baseline op bij eerste audit
        if self._baseline is None:
            self._baseline = self.snapshot()

        heeft_kritiek = any(
            s.ernst == "kritiek" for s in alle_schendingen
        )

        rapport = AuditRapport(
            veilig=not heeft_kritiek,
            schendingen=alle_schendingen,
            drift_gedetecteerd=drift_gedetecteerd,
            gecontroleerd=gecontroleerd,
        )
        self._last_rapport = rapport

        # NeuralBus events
        self._publiceer_events(rapport)

        # CorticalStack logging
        self._log_to_cortical(rapport)

        # BlackBox failure memory (alleen bij kritieke schendingen)
        if heeft_kritiek:
            self._log_to_blackbox(rapport)

        # Alerter (alleen bij kritieke schendingen)
        if heeft_kritiek:
            self._alert(rapport)

        return rapport

    # ─── Integraties ─────────────────────────────────

    def _publiceer_events(self, rapport: AuditRapport) -> None:
        """Publiceer audit resultaten naar NeuralBus."""
        try:
            from danny_toolkit.core.neural_bus import (
                get_bus, EventTypes,
            )
            bus = get_bus()

            bus.publish(
                EventTypes.CONFIG_AUDIT_COMPLETE,
                {
                    "veilig": rapport.veilig,
                    "schendingen": len(rapport.schendingen),
                    "gecontroleerd": rapport.gecontroleerd,
                },
                bron="ConfigAuditor",
            )

            if rapport.drift_gedetecteerd:
                drift_items = [
                    s.sleutel for s in rapport.schendingen
                    if s.categorie == "drift"
                ]
                bus.publish(
                    EventTypes.CONFIG_DRIFT_DETECTED,
                    {
                        "gewijzigde_keys": drift_items,
                        "aantal": len(drift_items),
                    },
                    bron="ConfigAuditor",
                )
        except Exception as e:
            logger.debug("ConfigAuditor NeuralBus fout: %s", e)

    _last_cortical_log: float = 0.0  # sampling: max 1x per 5 min

    def _log_to_cortical(self, rapport: AuditRapport) -> None:
        """Log audit resultaat naar CorticalStack (sampled: 1x/5min)."""
        import time as _time
        now = _time.time()
        if now - self._last_cortical_log < 300 and rapport.veilig:
            return  # Skip — te frequent en geen schendingen
        self.__class__._last_cortical_log = now
        try:
            from danny_toolkit.brain.cortical_stack import (
                get_cortical_stack,
            )
            stack = get_cortical_stack()
            stack.log_event(
                actor="ConfigAuditor",
                action="audit_complete",
                details={
                    "veilig": rapport.veilig,
                    "schendingen": len(rapport.schendingen),
                    "drift": rapport.drift_gedetecteerd,
                    "gecontroleerd": rapport.gecontroleerd,
                },
            )
        except Exception as e:
            logger.debug("ConfigAuditor CorticalStack fout: %s", e)

    def _log_to_blackbox(self, rapport: AuditRapport) -> None:
        """Registreer kritieke schendingen in BlackBox failure memory."""
        try:
            from danny_toolkit.brain.black_box import get_black_box
            bb = get_black_box()
            kritiek = [
                s for s in rapport.schendingen
                if s.ernst == "kritiek"
            ]
            if kritiek:
                bb.record_crash(
                    user_prompt="config_audit",
                    bad_response="; ".join(
                        s.beschrijving for s in kritiek
                    ),
                    critique="Kritieke configuratie-schendingen gedetecteerd",
                    source="ConfigAuditor",
                )
        except Exception as e:
            logger.debug("ConfigAuditor BlackBox fout: %s", e)

    def _alert(self, rapport: AuditRapport) -> None:
        """Stuur alert bij kritieke schendingen."""
        try:
            from danny_toolkit.core.alerter import (
                get_alerter, AlertLevel,
            )
            alerter = get_alerter()
            kritiek_count = sum(
                1 for s in rapport.schendingen
                if s.ernst == "kritiek"
            )
            alerter.alert(
                AlertLevel.KRITIEK,
                f"ConfigAudit: {kritiek_count} kritieke schendingen",
                bron="ConfigAuditor",
            )
        except Exception as e:
            logger.debug("ConfigAuditor alerter fout: %s", e)

    # ─── Rapport weergave ────────────────────────────

    def toon_rapport(self, rapport: Optional[AuditRapport] = None) -> None:
        """Print leesbaar audit rapport naar console."""
        rapport = rapport or self._last_rapport
        if not rapport:
            print("  [ConfigAuditor] Geen rapport beschikbaar. Draai eerst audit().")
            return

        status = "VEILIG" if rapport.veilig else "ONVEILIG"
        print(f"\n  {'='*50}")
        print(f"  CONFIG AUDIT RAPPORT — {status}")
        print(f"  {'='*50}")
        print(f"  Tijdstip:      {rapport.timestamp}")
        print(f"  Gecontroleerd: {rapport.gecontroleerd}")
        print(f"  Schendingen:   {len(rapport.schendingen)}")
        print(f"  Drift:         {'Ja' if rapport.drift_gedetecteerd else 'Nee'}")

        if rapport.schendingen:
            print(f"\n  {'─'*50}")
            for s in rapport.schendingen:
                icon = "[!!]" if s.ernst == "kritiek" else "[??]" if s.ernst == "waarschuwing" else "[ii]"
                print(f"  {icon} [{s.categorie}] {s.beschrijving}")
        else:
            print(f"\n  [OK] Geen schendingen gevonden.")

        print(f"  {'='*50}\n")


# ─── Singleton ───────────────────────────────────────

_auditor_instance: Optional[ConfigAuditor] = None
_auditor_lock = threading.Lock()


def get_config_auditor() -> ConfigAuditor:
    """Verkrijg de singleton ConfigAuditor instantie."""
    global _auditor_instance
    if _auditor_instance is None:
        with _auditor_lock:
            if _auditor_instance is None:
                _auditor_instance = ConfigAuditor()
    return _auditor_instance
