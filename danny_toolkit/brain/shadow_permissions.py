"""
SHADOW PERMISSIONS — Wat Shadows WEL Mogen
============================================
Expliciete whitelist van acties die #@* shadow entiteiten
mogen uitvoeren. Alles wat hier NIET staat is verboden.

Hiërarchie:
    Danny > OmegaGovernor > ShadowGovernance > ShadowPermissions
    Governance (verboden) overschrijft permissions (toegestaan) altijd.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

SHADOW_PREFIX = "#@*"


class ShadowPermission:
    """Enkele shadow toestemming."""

    __slots__ = ("code", "beschrijving", "scope", "actief")

    def __init__(self, code: str, beschrijving: str, scope: str = "shadow"):
        self.code = code
        self.beschrijving = beschrijving
        self.scope = scope  # "shadow" = alleen shadow zone, "transfer" = mag naar fysiek
        self.actief = True

    def __repr__(self):
        return f"ShadowPermission({self.code}, scope={self.scope})"


# ═══════════════════════════════════════════════════════════════
#  TOEGESTANE ACTIES
# ═══════════════════════════════════════════════════════════════

ALLOWED_PERMISSIONS = [
    # ── Lezen & Observeren ──
    ShadowPermission(
        "READ_CORTICAL_STACK",
        "Shadows mogen CorticalStack events lezen via get_recent_events(). "
        "Alleen lezen — nooit wijzigen of verwijderen.",
        "shadow",
    ),
    ShadowPermission(
        "READ_NEURAL_BUS",
        "Shadows mogen NeuralBus events lezen en subscriben. "
        "Ontvangen van broadcasts van fysieke agents is toegestaan.",
        "shadow",
    ),
    ShadowPermission(
        "READ_CONFIG",
        "Shadows mogen Config waarden lezen (model namen, paden, thresholds). "
        "Read-only — geen mutaties.",
        "shadow",
    ),
    ShadowPermission(
        "READ_SYNAPSE_PATHWAYS",
        "Shadows mogen Synapse pathway weights lezen om routing te begrijpen.",
        "shadow",
    ),
    ShadowPermission(
        "READ_BLACK_BOX",
        "Shadows mogen BlackBox failure history raadplegen. "
        "Leren van fouten zonder ze te herhalen.",
        "shadow",
    ),

    # ── RAG Read-Only ──
    ShadowPermission(
        "RAG_SEARCH",
        "Shadows mogen VectorStore.zoek() en TheLibrarian.query() "
        "gebruiken om de ChromaDB te doorzoeken. Read-only — "
        "ingest, ingest_file en voeg_toe zijn streng verboden.",
        "shadow",
    ),
    ShadowPermission(
        "RAG_VERIFY",
        "Shadows mogen TruthAnchor.verify() gebruiken om RAG-resultaten "
        "te controleren tegen de query. CPU cross-encoder, kost geen "
        "API-tokens. Verplicht voor elke RAG-query.",
        "shadow",
    ),

    # ── Verwerken & Analyseren ──
    ShadowPermission(
        "LLM_INFERENCE",
        "Shadows mogen Groq API calls maken via ShadowKeyVault. "
        "Eigen rate-limit budget (30 RPM), eigen key pool. "
        "Nooit de real-agent pool aanspreken.",
        "shadow",
    ),
    ShadowPermission(
        "WEB_RESEARCH",
        "Shadows mogen VoidWalker inzetten voor web research (DuckDuckGo). "
        "Stateless — geen sessions bewaren.",
        "shadow",
    ),
    ShadowPermission(
        "MIRROR_PROFILING",
        "Shadows mogen TheMirror gebruiken voor user profiling. "
        "Resultaten blijven in de shadow zone tot ShadowCortex transfer.",
        "shadow",
    ),
    ShadowPermission(
        "TRUTH_VERIFICATION",
        "Shadows mogen TruthAnchor gebruiken voor fact-checking. "
        "Cross-encoder verificatie van eigen output.",
        "shadow",
    ),
    ShadowPermission(
        "STATE_SNAPSHOT",
        "Shadows mogen een read-only snapshot van de fysieke swarm state maken. "
        "CorticalStack + NeuralBus + Synapse + Phantom + Config.",
        "shadow",
    ),

    # ── Intelligence Transfer (shadow → fysiek) ──
    ShadowPermission(
        "SYNAPSE_BOOST",
        "ShadowCortex mag fysieke Synapse pathways versterken via "
        "verwerk_feedback() met positieve scores. Alleen versterken, "
        "nooit verzwakken of verwijderen.",
        "transfer",
    ),
    ShadowPermission(
        "CORTICAL_INJECT",
        "ShadowCortex mag semantische feiten toevoegen aan CorticalStack "
        "via log_event(). Alleen toevoegen — nooit wijzigen/verwijderen. "
        "Alle injecties dragen #@* source tag.",
        "transfer",
    ),
    ShadowPermission(
        "PHANTOM_PRIME",
        "ShadowCortex mag ThePhantom primen met verkende topics via "
        "registreer_patroon(). Pre-warming voor fysieke predictions.",
        "transfer",
    ),
    ShadowPermission(
        "BUS_BROADCAST",
        "ShadowCortex mag NeuralBus events publiceren (SYSTEM_EVENT type). "
        "Alle broadcasts dragen #@* source prefix.",
        "transfer",
    ),
    ShadowPermission(
        "TOKEN_DIVIDEND",
        "ShadowKeyVault mag 50% van ongebruikte shadow tokens teruggeven "
        "aan de fysieke swarm als cooldown reductie. Dividend, geen override.",
        "transfer",
    ),

    # ── Zelfbescherming ──
    ShadowPermission(
        "KEY_SCRUBBING",
        "Shadows MOETEN alle output scrubben op API key patronen. "
        "Dit is zowel een recht als een plicht — altijd actief.",
        "shadow",
    ),
    ShadowPermission(
        "OUTPUT_TAGGING",
        "Shadows mogen output taggen met verificatie labels: "
        "[TWIN:VERIFIED], [TWIN:UNGROUNDED], [TWIN:SPECULATIVE], "
        "[TWIN:UNVERIFIED]. Tags informeren de fysieke swarm.",
        "shadow",
    ),
]


class ShadowPermissions:
    """Whitelist van acties die #@* shadow entiteiten mogen uitvoeren.

    BELANGRIJK: Alle permissions zijn ALLEEN actief binnen de virtual shadow
    zone (VirtualTwin context). Buiten de shadow zone worden ALLE permissions
    automatisch False — de shadow heeft dan GEEN rechten.

    Gebruik:
        permissions = ShadowPermissions()
        permissions.enter_shadow_zone()   # Activeer binnen VirtualTwin
        if permissions.is_allowed("LLM_INFERENCE"):
            # Shadow mag Groq calls maken
            ...
        permissions.exit_shadow_zone()    # Alle permissions → False
    """

    def __init__(self):
        self._blueprint = list(ALLOWED_PERMISSIONS)  # Origineel — nooit wijzigen
        self.permissions = []  # Leeg buiten shadow zone
        self._in_shadow_zone = False

    def enter_shadow_zone(self):
        """Activeer permissions — mag ALLEEN vanuit VirtualTwin.consult().

        Herstelt de volledige permission lijst vanuit de blueprint.
        Buiten de zone bestaan er GEEN permissions.
        """
        self._in_shadow_zone = True
        self.permissions = [
            ShadowPermission(p.code, p.beschrijving, p.scope)
            for p in self._blueprint
        ]
        logger.debug(
            "%sShadowPermissions: shadow zone ACTIEF — %d permissions geladen",
            SHADOW_PREFIX, len(self.permissions),
        )

    def exit_shadow_zone(self):
        """Verwijder ALLE permissions — shadow heeft buiten de zone GEEN rechten.

        De lijst wordt volledig geleegd, niet alleen gedeactiveerd.
        Permissions bestaan niet buiten de virtual shadow zone.
        """
        removed = len(self.permissions)
        self.permissions.clear()
        self._in_shadow_zone = False
        logger.debug(
            "%sShadowPermissions: shadow zone VERLATEN — "
            "%d permissions VERWIJDERD, lijst is leeg",
            SHADOW_PREFIX, removed,
        )

    @property
    def in_shadow_zone(self) -> bool:
        """True als we binnen de virtual shadow zone opereren."""
        return self._in_shadow_zone

    def is_allowed(self, action_code: str) -> bool:
        """Check of een actie is toegestaan voor shadows.

        Buiten de shadow zone is de lijst leeg → altijd False.
        """
        for p in self.permissions:
            if p.code == action_code and p.actief:
                return True
        return False

    def get_transfer_permissions(self) -> list:
        """Geeft alleen de transfer-scope permissions terug.

        Buiten de shadow zone is de lijst leeg → retourneert [].
        """
        return [p for p in self.permissions if p.scope == "transfer" and p.actief]

    def get_shadow_permissions(self) -> list:
        """Geeft alleen de shadow-interne permissions terug.

        Buiten de shadow zone is de lijst leeg → retourneert [].
        """
        return [p for p in self.permissions if p.scope == "shadow" and p.actief]

    def get_permissions_prompt(self) -> str:
        """Formatteer als LLM context blok — wat de shadow WEL mag.

        Wordt samen met ShadowGovernance.get_rules_prompt() geïnjecteerd
        in de shadow system prompt.
        """
        lines = [
            "=== SHADOW PERMISSIONS — TOEGESTANE ACTIES ===",
            f"Jij bent een #@* shadow entiteit. Prefix: {SHADOW_PREFIX}",
            "",
            "--- SHADOW ZONE (intern) ---",
        ]

        for p in self.permissions:
            if not p.actief or p.scope != "shadow":
                continue
            lines.append(f"  [TOEGESTAAN] {p.code}")
            lines.append(f"    {p.beschrijving}")
            lines.append("")

        lines.append("--- INTELLIGENCE TRANSFER (shadow → fysiek) ---")
        for p in self.permissions:
            if not p.actief or p.scope != "transfer":
                continue
            lines.append(f"  [TRANSFER] {p.code}")
            lines.append(f"    {p.beschrijving}")
            lines.append("")

        lines.append("Alles wat hier NIET staat is VERBODEN.")
        lines.append("Governance regels overschrijven permissions altijd.")
        lines.append("=== EINDE SHADOW PERMISSIONS ===")
        return "\n".join(lines)

    def get_stats(self) -> dict:
        """Permission statistieken."""
        active = [p for p in self.permissions if p.actief]
        return {
            "in_shadow_zone": self._in_shadow_zone,
            "blueprint_total": len(self._blueprint),
            "loaded_permissions": len(self.permissions),
            "active": len(active),
            "shadow_scope": sum(1 for p in active if p.scope == "shadow"),
            "transfer_scope": sum(1 for p in active if p.scope == "transfer"),
        }

    def __repr__(self):
        if not self._in_shadow_zone:
            return "ShadowPermissions(BUITEN ZONE — 0 permissions, lijst leeg)"
        active = sum(1 for p in self.permissions if p.actief)
        shadow = sum(1 for p in self.permissions if p.scope == "shadow" and p.actief)
        transfer = sum(1 for p in self.permissions if p.scope == "transfer" and p.actief)
        return (
            f"ShadowPermissions("
            f"IN ZONE — {active} active: {shadow} shadow + {transfer} transfer)"
        )
