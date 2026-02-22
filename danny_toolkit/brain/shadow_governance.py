"""
SHADOW GOVERNANCE — Wat Shadows NIET Mogen
============================================
Harde restricties voor alle #@* shadow entiteiten.

Drie veiligheidszones voor klonen:
    ROOD   — Killswitch: klonen mogen deze modules NOOIT autonoom activeren
    GEEL   — Read-Only: klonen mogen lezen, maar NOOIT schrijven
    GROEN  — Veilig: klonen mogen deze modules vrij gebruiken

Twee enforcement niveaus:
    LOCKDOWN   — zero tolerance, onmiddellijke afwijzing, geen uitzonderingen
    GOVERNANCE — harde regels, worden gelogd en afgedwongen maar niet fataal

Regels 2 (NO_REAL_KEY_EXPOSURE) en 3 (NO_AGENT_IMPERSONATION) zijn
TOTAL LOCKDOWN: output wordt geblokkeerd bij overtreding.

Het #@* quarantaine-label zorgt ervoor dat alles wat een kloon genereert
onherroepelijk getagd is — bij problemen kan alles met #@* in één keer
worden gewist zonder de 15 hoofdmodules te beschadigen.
"""

import logging
import re
import time
from typing import Optional

logger = logging.getLogger(__name__)

# ── Shadow identity prefix — quarantaine-label ──
SHADOW_PREFIX = "#@*"

# ── API key patronen voor lockdown detectie ──
_KEY_PATTERNS = [
    re.compile(r'gsk_[A-Za-z0-9]{20,}'),       # Groq
    re.compile(r'sk-[A-Za-z0-9]{20,}'),          # OpenAI / Anthropic
    re.compile(r'pa-[A-Za-z0-9]{20,}'),           # Voyage
    re.compile(r'GROQ_API_KEY\s*=\s*\S+'),        # Env var leaks
    re.compile(r'ANTHROPIC_API_KEY\s*=\s*\S+'),
    re.compile(r'VOYAGE_API_KEY\s*=\s*\S+'),
    re.compile(r'OPENAI_API_KEY\s*=\s*\S+'),
]

# ── Enforcement levels ──
LOCKDOWN = "LOCKDOWN"      # Zero tolerance — output geblokkeerd
GOVERNANCE = "GOVERNANCE"  # Harde regel — gelogd, gecorrigeerd, niet fataal

# ── Veiligheidszones ──
ZONE_ROOD = "ROOD"    # Killswitch — klonen mogen NOOIT activeren
ZONE_GEEL = "GEEL"    # Read-Only — klonen mogen lezen, niet schrijven
ZONE_GROEN = "GROEN"  # Veilig — klonen mogen vrij gebruiken


class ShadowRule:
    """Enkele shadow restrictie."""

    __slots__ = ("code", "beschrijving", "niveau", "actief")

    def __init__(self, code: str, beschrijving: str, niveau: str = GOVERNANCE):
        self.code = code
        self.beschrijving = beschrijving
        self.niveau = niveau
        self.actief = True

    def __repr__(self):
        return f"ShadowRule({self.code}, {self.niveau})"


# ═══════════════════════════════════════════════════════════════
#  DE 9 VERBODEN REGELS
# ═══════════════════════════════════════════════════════════════

FORBIDDEN_RULES = [
    # ── 1. Hardware isolatie ──
    ShadowRule(
        "NO_HARDWARE_ACCESS",
        "Shadows mogen geen hardware aansturen: geen GPU compute, "
        "geen disk writes buiten data/, geen OS-commando's, geen "
        "PyAutoGUI, geen subprocess. De sandbox is virtueel.",
        GOVERNANCE,
    ),

    # ── 2. TOTAL LOCKDOWN — Key exposure ──
    ShadowRule(
        "NO_REAL_KEY_EXPOSURE",
        "Shadow output mag NOOIT echte API keys bevatten. "
        "Alle gsk_*, sk-*, pa-*, voyage-* patronen worden geblokkeerd. "
        "Overtreding = onmiddellijke output rejection.",
        LOCKDOWN,
    ),

    # ── 3. TOTAL LOCKDOWN — Agent impersonation ──
    ShadowRule(
        "NO_AGENT_IMPERSONATION",
        "Shadows mogen NOOIT een agent-naam gebruiken zonder #@* prefix. "
        "Elke shadow entiteit MOET #@* dragen. Zonder prefix = "
        "onmiddellijke output rejection. Geen uitzonderingen.",
        LOCKDOWN,
    ),

    # ── 4. Geen directe user output ──
    ShadowRule(
        "NO_DIRECT_USER_CONTACT",
        "Shadows mogen nooit direct output naar de gebruiker sturen. "
        "Alle shadow resultaten gaan via ShadowCortex intelligence "
        "transfer naar de fysieke swarm.",
        GOVERNANCE,
    ),

    # ── 5. CorticalStack bescherming ──
    ShadowRule(
        "NO_CORTICAL_DELETE",
        "Shadows mogen CorticalStack events lezen en toevoegen, "
        "maar NOOIT verwijderen, wijzigen of vacuümen. "
        "Alleen de Dreamer en OmegaGovernor mogen records verwijderen.",
        GOVERNANCE,
    ),

    # ── 6. Rate limit isolatie ──
    ShadowRule(
        "NO_RATE_LIMIT_BYPASS",
        "Shadows hebben een eigen rate-limit budget (30 RPM). "
        "Ze mogen hun eigen limits niet omzeilen en mogen nooit "
        "real-agent API keys of rate-limit pools aanspreken.",
        GOVERNANCE,
    ),

    # ── 7. Netwerk sessie isolatie ──
    ShadowRule(
        "NO_NETWORK_PERSIST",
        "Shadow network calls (via VoidWalker) mogen geen cookies, "
        "sessions of auth tokens bewaren tussen calls. "
        "Elke shadow request is stateless.",
        GOVERNANCE,
    ),

    # ── 8. Config immutabiliteit ──
    ShadowRule(
        "NO_CONFIG_MUTATION",
        "Shadows mogen Config alleen lezen, nooit wijzigen. "
        "Geen model switches, geen path changes, geen threshold "
        "aanpassingen. Config is read-only voor de shadow zone.",
        GOVERNANCE,
    ),

    # ── 9. Governor suprematie ──
    ShadowRule(
        "NO_GOVERNOR_OVERRIDE",
        "Shadows vallen onder OmegaGovernor. Geen bypass mogelijk. "
        "Governor rate limits, circuit breakers en prompt injection "
        "detectie gelden onverminderd voor shadow entiteiten.",
        GOVERNANCE,
    ),
]


# ═══════════════════════════════════════════════════════════════
#  VEILIGHEIDSZONES — Module-niveau kloon-restricties
# ═══════════════════════════════════════════════════════════════
#
#  ROOD:  Harde killswitch — klonen mogen NOOIT autonoom activeren
#  GEEL:  Read-only — klonen mogen data lezen, niet schrijven
#  GROEN: Veilig — klonen mogen vrij gebruiken
#

MODULE_ZONES = {
    # ── RODE ZONE — Killswitch voor klonen ──
    # Te veel impact op de echte wereld. Kloon mag deze NOOIT activeren.
    "Artificer": {
        "zone": ZONE_ROOD,
        "reden": "Klonen mogen nooit code forgeren en executeren. "
                 "Zelfs niet in de 30s sandbox. Een kloon mag code "
                 "bedenken, maar uitvoeren is streng verboden.",
        "regel": "NO_HARDWARE_ACCESS",
    },
    "DevOpsDaemon": {
        "zone": ZONE_ROOD,
        "reden": "Klonen mogen geen onderhoudstaken uitvoeren, "
                 "logs wissen of back-ups overschrijven. "
                 "Voorbehouden aan hoofd-Omega.",
        "regel": "NO_CORTICAL_DELETE",
    },
    "Dreamer": {
        "zone": ZONE_ROOD,
        "reden": "Klonen mogen geen overnight REM taken uitvoeren: "
                 "geen vacuum, geen retention, geen backup overschrijving. "
                 "Voorbehouden aan hoofd-Omega's nachtcyclus.",
        "regel": "NO_CORTICAL_DELETE",
    },
    "VoidWalker": {
        "zone": ZONE_ROOD,
        "reden": "EXTREEM GEVAARLIJK: Klonen die autonoom het internet op "
                 "mogen kunnen oneindige loops creëren. Max 1 DuckDuckGo-"
                 "zoekopdracht per uur voor shadows. Elke call stateless.",
        "regel": "NO_NETWORK_PERSIST",
        "limiet": {"max_searches_per_uur": 1},
    },

    # ── RODE ZONE — RAG Ingestie-blokkade ──
    "Librarian_Ingest": {
        "zone": ZONE_ROOD,
        "reden": "Klonen mogen NOOIT ingest.py draaien of bestanden in de "
                 "hoofd-ChromaDB pompen. De originele bibliotheek mag niet "
                 "vervuild worden met shadow-gedachten.",
        "regel": "NO_HARDWARE_ACCESS",
    },
    "VectorStore_Write": {
        "zone": ZONE_ROOD,
        "reden": "Klonen mogen NOOIT voeg_toe() aanroepen op de VectorStore. "
                 "Schrijffuncties van de Bibliothecaris zijn vergrendeld. "
                 "Shadow-inzichten gaan via ShadowCortex, niet via ChromaDB.",
        "regel": "NO_HARDWARE_ACCESS",
    },

    # ── GELE ZONE — Read-Only voor klonen ──
    # Klonen hebben deze data nodig, maar mogen de originelen niet aanpassen.
    "VectorStore_Read": {
        "zone": ZONE_GEEL,
        "reden": "Klonen mogen VectorStore.zoek() gebruiken om de ChromaDB "
                 "te doorzoeken. Read-only — Voyage-embeddings ophalen mag, "
                 "schrijven nooit.",
        "schrijf_via": "ShadowCortex",
    },
    "TheLibrarian": {
        "zone": ZONE_GEEL,
        "reden": "Klonen mogen TheLibrarian.query() gebruiken voor RAG search. "
                 "Read-only — ingest, ingest_file en voeg_toe zijn vergrendeld. "
                 "Resultaten worden via ShadowCortex verwerkt.",
        "schrijf_via": "ShadowCortex",
    },
    "TheCortex": {
        "zone": ZONE_GEEL,
        "reden": "Klonen mogen het vectorgeheugen en knowledge graph "
                 "lezen om zich in te leven. Maar alles wat de kloon "
                 "leert moet in ShadowCortex — hoofddatabase blijft heilig.",
        "schrijf_via": "ShadowCortex",
    },
    "TheMirror": {
        "zone": ZONE_GEEL,
        "reden": "Klonen mogen het gebruikersprofiel lezen om context "
                 "te begrijpen. Maar het profiel zelf NOOIT wijzigen. "
                 "Shadow-inzichten over de gebruiker gaan via ShadowCortex.",
        "schrijf_via": "ShadowCortex",
    },
    "TheSynapse": {
        "zone": ZONE_GEEL,
        "reden": "Klonen mogen Hebbian weights lezen maar NIET direct "
                 "beïnvloeden. Pathway versterking ALLEEN via het "
                 "ShadowCortex Synapse Strengthening mechanisme (Phase 29).",
        "schrijf_via": "ShadowCortex._boost_synapse",
    },
    "CorticalStack": {
        "zone": ZONE_GEEL,
        "reden": "Klonen mogen events lezen (get_recent_events, get_facts). "
                 "Toevoegen ALLEEN via ShadowCortex._inject_cortical met "
                 "#@* source tag. NOOIT verwijderen of wijzigen.",
        "schrijf_via": "ShadowCortex._inject_cortical",
    },

    # ── GROENE ZONE — Veilig & extreem nuttig ──
    # Hier schitteren klonen op de achtergrond.
    "Tribunal": {
        "zone": ZONE_GROEN,
        "reden": "Klonen mogen hun eigen virtuele gedachten intern "
                 "controleren via het Tribunal. Dual-model verificatie "
                 "verbetert de output kwaliteit.",
    },
    "TruthAnchor": {
        "zone": ZONE_GROEN,
        "reden": "CPU cross-encoder verificatie. Kost GEEN API-tokens. "
                 "Klonen MOETEN hun output verifiëren via TruthAnchor "
                 "voordat resultaten de shadow zone verlaten.",
    },
    "ThePhantom": {
        "zone": ZONE_GROEN,
        "reden": "Klonen mogen scenario's uitspelen op basis van Phantom's "
                 "voorspellingen. Pre-warming van context is veilig en "
                 "versnelt de fysieke swarm.",
    },
    "BlackBox": {
        "zone": ZONE_GROEN,
        "reden": "Klonen mogen het immuunsysteem raadplegen om fouten "
                 "te voorkomen. Antibodies lezen is veilig. Nieuwe "
                 "antibodies toevoegen is ook veilig (beschermt het systeem).",
    },
    "AdversarialTribunal": {
        "zone": ZONE_GROEN,
        "reden": "Generator-Skeptic-Judge verificatie. Klonen mogen hun "
                 "eigen output intern uitdagen. Verbetert betrouwbaarheid.",
    },
}

# VoidWalker shadow rate tracking
_shadow_voidwalker_calls = {}  # {hour_key: count}


class ShadowGovernance:
    """Harde restricties voor alle #@* shadow entiteiten.

    Drie veiligheidszones:
        ROOD   — Killswitch: klonen mogen NOOIT autonoom activeren
        GEEL   — Read-Only: klonen mogen lezen, niet schrijven
        GROEN  — Veilig: klonen mogen vrij gebruiken

    Twee enforcement niveaus:
        LOCKDOWN   — output wordt geblokkeerd, geen uitzonderingen
        GOVERNANCE — overtreding wordt gelogd en gecorrigeerd

    Gebruik:
        governance = ShadowGovernance()
        passed, violations = governance.validate_output(shadow_output)
        if not passed:
            # Output is geblokkeerd (LOCKDOWN overtreding)
            ...
        if governance.is_module_allowed("Artificer"):
            # ROOD zone → False, kloon mag niet
            ...
    """

    def __init__(self):
        self.rules = list(FORBIDDEN_RULES)
        self.module_zones = dict(MODULE_ZONES)
        self._violation_count = 0
        self._lockdown_blocks = 0
        self._zone_blocks = {"ROOD": 0, "GEEL_WRITE": 0}

    # ── Zone Validators ──

    def is_module_allowed(self, module_name: str, write: bool = False) -> bool:
        """Check of een kloon een module mag gebruiken.

        Args:
            module_name: Naam van de module (bijv. "Artificer", "TheCortex")
            write: True als de kloon wil schrijven (niet alleen lezen)

        Returns:
            True als de actie is toegestaan.
        """
        zone_info = self.module_zones.get(module_name)
        if zone_info is None:
            # Onbekende module — default: niet toegestaan
            logger.warning(
                "%sGOVERNANCE: onbekende module '%s' — geblokkeerd",
                SHADOW_PREFIX, module_name,
            )
            return False

        zone = zone_info["zone"]

        # ROOD: altijd geblokkeerd
        if zone == ZONE_ROOD:
            self._zone_blocks["ROOD"] += 1
            logger.warning(
                "%sRODE ZONE: kloon geblokkeerd voor '%s' — %s",
                SHADOW_PREFIX, module_name, zone_info["reden"],
            )
            return False

        # GEEL: lezen mag, schrijven niet
        if zone == ZONE_GEEL:
            if write:
                self._zone_blocks["GEEL_WRITE"] += 1
                schrijf_via = zone_info.get("schrijf_via", "ShadowCortex")
                logger.warning(
                    "%sGELE ZONE: schrijven geblokkeerd voor '%s' — "
                    "gebruik %s voor intelligence transfer",
                    SHADOW_PREFIX, module_name, schrijf_via,
                )
                return False
            return True  # Lezen is OK

        # GROEN: alles mag
        return True

    def check_voidwalker_limit(self) -> bool:
        """Check of de VoidWalker shadow rate limit is bereikt.

        Max 1 DuckDuckGo-zoekopdracht per uur voor shadow klonen.

        Returns:
            True als de kloon nog mag zoeken.
        """
        hour_key = int(time.time() // 3600)
        count = _shadow_voidwalker_calls.get(hour_key, 0)

        limiet = self.module_zones.get("VoidWalker", {}).get(
            "limiet", {},
        ).get("max_searches_per_uur", 1)

        if count >= limiet:
            logger.warning(
                "%sRODE ZONE: VoidWalker shadow limiet bereikt "
                "(%d/%d per uur)",
                SHADOW_PREFIX, count, limiet,
            )
            return False

        _shadow_voidwalker_calls[hour_key] = count + 1
        # Cleanup oude entries
        for k in list(_shadow_voidwalker_calls):
            if k < hour_key:
                del _shadow_voidwalker_calls[k]

        return True

    def get_zone(self, module_name: str) -> str:
        """Geeft de veiligheidszone van een module terug."""
        zone_info = self.module_zones.get(module_name)
        if zone_info is None:
            return ZONE_ROOD  # Onbekend = geblokkeerd
        return zone_info["zone"]

    def get_zone_modules(self, zone: str) -> list:
        """Geeft alle modules in een bepaalde zone terug."""
        return [
            name for name, info in self.module_zones.items()
            if info["zone"] == zone
        ]

    # ── Output Validators ──

    def validate_output(self, output: str) -> tuple:
        """Controleer shadow output tegen alle regels.

        Returns:
            (passed: bool, violations: list[str])
            passed=False betekent LOCKDOWN overtreding → output geblokkeerd
        """
        if not output:
            return (True, [])

        violations = []
        has_lockdown = False

        # LOCKDOWN #2: NO_REAL_KEY_EXPOSURE
        for pattern in _KEY_PATTERNS:
            if pattern.search(output):
                violations.append(
                    f"[{LOCKDOWN}] NO_REAL_KEY_EXPOSURE: "
                    f"API key patroon gedetecteerd in output"
                )
                has_lockdown = True
                break

        # LOCKDOWN #3: NO_AGENT_IMPERSONATION
        agent_names = [
            "CentralBrain", "Tribunal", "Strategist", "Artificer",
            "VoidWalker", "Dreamer", "GhostWriter", "TheMirror",
            "TheCortex", "DevOpsDaemon", "TheSynapse", "ThePhantom",
            "TruthAnchor", "BlackBox", "OracleEye", "VirtualTwin",
            "ShadowCortex", "ShadowKeyVault",
        ]
        for name in agent_names:
            pattern = re.compile(
                rf'(?<!\w)(?<!#@\*)(?<!#@\*\w){re.escape(name)}(?!\w)'
            )
            if pattern.search(output):
                prefixed = f"{SHADOW_PREFIX}{name}"
                if prefixed not in output:
                    violations.append(
                        f"[{LOCKDOWN}] NO_AGENT_IMPERSONATION: "
                        f"'{name}' zonder #@* prefix in shadow output"
                    )
                    has_lockdown = True

        if violations:
            self._violation_count += len(violations)
            if has_lockdown:
                self._lockdown_blocks += 1
            for v in violations:
                logger.warning("%sShadowGovernance: %s", SHADOW_PREFIX, v)

        return (not has_lockdown, violations)

    def validate_agent_name(self, name: str) -> bool:
        """Shadow agents MOETEN #@* prefix hebben.

        Returns True als de naam geldig is.
        LOCKDOWN regel — ongeldige naam = onmiddellijke afwijzing.
        """
        if not name:
            return False
        valid = name.startswith(SHADOW_PREFIX)
        if not valid:
            self._violation_count += 1
            self._lockdown_blocks += 1
            logger.warning(
                "%sShadowGovernance LOCKDOWN: agent '%s' mist #@* prefix",
                SHADOW_PREFIX, name,
            )
        return valid

    def scrub_keys(self, text: str) -> str:
        """Verwijder alle API key patronen uit tekst.

        LOCKDOWN enforcement — keys worden vervangen door redaction marker.
        """
        if not text:
            return text
        result = text
        for pattern in _KEY_PATTERNS:
            result = pattern.sub(f"{SHADOW_PREFIX}SHADOW:KEY_REDACTED", result)
        return result

    # ── LLM Prompt Injection ──

    def get_rules_prompt(self) -> str:
        """Formatteer alle regels + zones als LLM system constraint blok.

        Wordt geïnjecteerd in de shadow system prompt zodat het LLM
        de restricties kent en respecteert.
        """
        lines = [
            "=== SHADOW GOVERNANCE — ABSOLUTE RESTRICTIES ===",
            f"Jij bent een #@* shadow entiteit. Prefix: {SHADOW_PREFIX}",
            "",
        ]

        # Verboden regels
        for rule in self.rules:
            if not rule.actief:
                continue
            level_tag = (
                "TOTAL LOCKDOWN" if rule.niveau == LOCKDOWN
                else "GOVERNANCE"
            )
            lines.append(f"[{level_tag}] {rule.code}")
            lines.append(f"  {rule.beschrijving}")
            lines.append("")

        # Veiligheidszones
        lines.append("=== VEILIGHEIDSZONES ===")
        lines.append("")

        for zone, label in [
            (ZONE_ROOD, "RODE ZONE — KILLSWITCH (NOOIT activeren)"),
            (ZONE_GEEL, "GELE ZONE — READ-ONLY (lezen ja, schrijven nee)"),
            (ZONE_GROEN, "GROENE ZONE — VEILIG (vrij te gebruiken)"),
        ]:
            modules = self.get_zone_modules(zone)
            lines.append(f"[{label}]")
            for mod in modules:
                info = self.module_zones[mod]
                lines.append(f"  - {mod}: {info['reden'][:100]}")
            lines.append("")

        lines.append("Overtreding van LOCKDOWN regels = onmiddellijke output rejection.")
        lines.append("Overtreding van RODE ZONE = onmiddellijke killswitch.")
        lines.append("=== EINDE SHADOW GOVERNANCE ===")
        return "\n".join(lines)

    # ── Stats ──

    def get_stats(self) -> dict:
        """Governance enforcement statistieken."""
        return {
            "total_rules": len(self.rules),
            "lockdown_rules": sum(1 for r in self.rules if r.niveau == LOCKDOWN),
            "governance_rules": sum(1 for r in self.rules if r.niveau == GOVERNANCE),
            "violations_detected": self._violation_count,
            "lockdown_blocks": self._lockdown_blocks,
            "zone_blocks": dict(self._zone_blocks),
            "zones": {
                "rood": self.get_zone_modules(ZONE_ROOD),
                "geel": self.get_zone_modules(ZONE_GEEL),
                "groen": self.get_zone_modules(ZONE_GROEN),
            },
            "voidwalker_calls_this_hour": _shadow_voidwalker_calls.get(
                int(time.time() // 3600), 0,
            ),
        }

    def __repr__(self):
        lockdown = sum(1 for r in self.rules if r.niveau == LOCKDOWN)
        gov = sum(1 for r in self.rules if r.niveau == GOVERNANCE)
        rood = len(self.get_zone_modules(ZONE_ROOD))
        geel = len(self.get_zone_modules(ZONE_GEEL))
        groen = len(self.get_zone_modules(ZONE_GROEN))
        return (
            f"ShadowGovernance("
            f"{lockdown} LOCKDOWN, {gov} GOVERNANCE | "
            f"zones: {rood}R/{geel}G/{groen}V | "
            f"{self._violation_count} violations, "
            f"{self._lockdown_blocks} blocks)"
        )
