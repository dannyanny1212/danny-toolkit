import json
import logging
import time
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from danny_toolkit.core.config import Config
from danny_toolkit.core.utils import Kleur

logger = logging.getLogger(__name__)

try:
    from danny_toolkit.core.vector_store import VectorStore
    from danny_toolkit.core.embeddings import get_torch_embedder
    HAS_VECTOR = True
except ImportError:
    HAS_VECTOR = False

try:
    from danny_toolkit.core.neural_bus import get_bus, EventTypes
    HAS_BUS = True
except ImportError:
    HAS_BUS = False


# ── Immunity Tiers ──

class Severity(Enum):
    """Antibody severity — escalates on repeat encounters."""
    MILD = 1       # Eerste keer gezien — informatief
    SEVERE = 2     # Herhaald — actieve blokkade
    CRITICAL = 3   # Structureel patroon — systemische vaccinatie


@dataclass
class Antibody:
    """Een geleerde verdediging tegen een specifiek faalpatroon.

    signature:  Korte beschrijving van het aanvalspatroon
    antidote:   Hoe het voorkomen moet worden (geïnjecteerd in prompts)
    severity:   Escalatieniveau (MILD → SEVERE → CRITICAL)
    encounters: Aantal keer dat dit patroon gezien is
    created_at: Eerste detectie timestamp
    last_seen:  Laatste detectie timestamp
    half_life:  Vervalsnelheid in seconden (standaard 7 dagen)
    source:     Welk subsysteem de antibody genereerde
    """
    signature: str
    antidote: str
    severity: Severity = Severity.MILD
    encounters: int = 1
    created_at: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)
    half_life: float = 604800.0  # 7 dagen
    source: str = "unknown"

    @property
    def strength(self) -> float:
        """Huidige sterkte (0.0-1.0) met exponentieel verval.

        Verse antibodies zijn sterk (1.0), vergeten na ~3 halveringstijden.
        Herhaalde encounters resetten de klok → antibody wordt sterker.
        """
        age = time.time() - self.last_seen
        decay = 0.5 ** (age / self.half_life) if self.half_life > 0 else 0.0
        # Encounters boost: base 1.0, elke extra encounter +0.2, max 2.0
        boost = min(0.8 + self.encounters * 0.2, 2.0)
        return min(decay * boost, 1.0)

    @property
    def alive(self) -> bool:
        """Antibody is nog actief (sterkte > 5%)."""
        return self.strength > 0.05

    def reinforce(self):
        """Herhaalde encounter — escaleer severity + reset klok."""
        self.encounters += 1
        self.last_seen = time.time()
        if self.encounters >= 5 and self.severity == Severity.MILD:
            self.severity = Severity.SEVERE
        elif self.encounters >= 10 and self.severity == Severity.SEVERE:
            self.severity = Severity.CRITICAL

    def to_dict(self) -> dict:
        return {
            "signature": self.signature,
            "antidote": self.antidote,
            "severity": self.severity.name,
            "encounters": self.encounters,
            "created_at": self.created_at,
            "last_seen": self.last_seen,
            "half_life": self.half_life,
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Antibody":
        return cls(
            signature=d["signature"],
            antidote=d["antidote"],
            severity=Severity[d.get("severity", "MILD")],
            encounters=d.get("encounters", 1),
            created_at=d.get("created_at", time.time()),
            last_seen=d.get("last_seen", time.time()),
            half_life=d.get("half_life", 604800.0),
            source=d.get("source", "unknown"),
        )


class BlackBox:
    """
    INVENTION #13: THE BLACK BOX — Adaptive Immune System
    =====================================================
    Formerly a passive failure log. Now an active immune system that:

    1. DETECT    — Records failures as vector embeddings (original behavior)
    2. ANTIBODY  — Extracts attack signatures + antidotes from each failure
    3. ESCALATE  — Repeated patterns escalate: MILD → SEVERE → CRITICAL
    4. VACCINATE — Broadcasts immunity events on NeuralBus so ALL agents learn
    5. DECAY     — Old antibodies fade (half-life), reinforced on re-encounter
    6. PREDICT   — Cross-references signatures for predictive immunity

    The more the system fails, the stronger its immune response becomes.
    Asymptotically approaches zero repeated mistakes.
    """

    ANTIBODY_FILE = "immune_memory.json"

    def __init__(self):
        self.db_path = Config.DATA_DIR / "memory" / "black_box.json"
        self._antibody_path = Config.DATA_DIR / "memory" / self.ANTIBODY_FILE
        self._store = None
        self._embedder = None
        # Immune memory: signature → Antibody
        self._antibodies: Dict[str, Antibody] = {}

        if HAS_VECTOR:
            try:
                self._embedder = get_torch_embedder()
                self._store = VectorStore(
                    embedding_provider=self._embedder,
                    db_file=self.db_path,
                )
            except Exception as e:
                logger.debug("VectorStore init failed: %s", e)

        self._load_immune_memory()

    # ── Persistence ──

    def _load_immune_memory(self):
        """Laad antibodies van schijf."""
        if not self._antibody_path.exists():
            return
        try:
            with open(self._antibody_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for sig, ab_dict in data.items():
                ab = Antibody.from_dict(ab_dict)
                if ab.alive:
                    self._antibodies[sig] = ab
        except (json.JSONDecodeError, IOError, KeyError) as e:
            logger.debug("Immune memory load failed: %s", e)

    def _save_immune_memory(self):
        """Bewaar actieve antibodies naar schijf."""
        Config.ensure_dirs()
        (Config.DATA_DIR / "memory").mkdir(parents=True, exist_ok=True)
        data = {}
        for sig, ab in self._antibodies.items():
            if ab.alive:
                data[sig] = ab.to_dict()
        try:
            with open(self._antibody_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except IOError as e:
            logger.debug("Immune memory save failed: %s", e)

    # ── Core: Record + Immunize ──

    def record_crash(
        self,
        user_prompt: str,
        bad_response: str,
        critique: str,
        source: str = "unknown",
    ):
        """Record a failure AND generate/reinforce an antibody.

        1. Store in VectorStore (original behavior)
        2. Extract antibody signature from the critique
        3. If signature exists → reinforce (escalate severity)
        4. If new → create fresh antibody
        5. Vaccinate all agents via NeuralBus broadcast
        """
        # 1. Original vector storage
        if self._store:
            failure_id = f"failure_{int(time.time())}"
            failure_entry = {
                "id": failure_id,
                "tekst": user_prompt,
                "metadata": {
                    "type": "failure_lesson",
                    "timestamp": time.time(),
                    "hallucination": bad_response[:500],
                    "lesson": critique,
                    "source": source,
                },
            }
            self._store.voeg_toe([failure_entry])

        # 2. Extract antibody signature (normalized key from critique)
        signature = self._extract_signature(critique)

        # 3. Reinforce or create
        if signature in self._antibodies:
            ab = self._antibodies[signature]
            old_severity = ab.severity
            ab.reinforce()
            if ab.severity != old_severity:
                print(f"{Kleur.ROOD}🛡️  IMMUNE ESCALATION: "
                      f"'{signature}' → {ab.severity.name}{Kleur.RESET}")
        else:
            ab = Antibody(
                signature=signature,
                antidote=self._generate_antidote(critique),
                source=source,
            )
            self._antibodies[signature] = ab
            print(f"{Kleur.GEEL}🧬 New antibody: '{signature}'{Kleur.RESET}")

        # 4. Persist
        self._save_immune_memory()

        # 5. Vaccinate — broadcast to all agents
        self._vaccinate(ab, user_prompt)

    def _extract_signature(self, critique: str) -> str:
        """Extract een genormaliseerde signature uit een fout-beschrijving.

        Neemt de eerste 80 chars, lowercase, gestript. Dit is de
        unieke identifier voor een type fout.
        """
        sig = critique.strip().lower()[:80]
        # Verwijder niet-alfanumerieke tekens voor consistente matching
        sig = "".join(c for c in sig if c.isalnum() or c == " ")
        return sig.strip() or f"unknown_{int(time.time())}"

    @staticmethod
    def _generate_antidote(critique: str) -> str:
        """Genereer een prompt-injecteerbaar tegengif uit de critique."""
        return (
            f"IMMUNE CONSTRAINT: A previous failure was caused by: "
            f'"{critique[:200]}". '
            f"Do NOT repeat this pattern. If uncertain, say so explicitly."
        )

    def _vaccinate(self, antibody: Antibody, context: str = ""):
        """Broadcast immunity event op NeuralBus.

        Alle agents die luisteren naar IMMUNE_RESPONSE krijgen de
        antibody zodat ze dezelfde fout nooit maken.
        """
        if not HAS_BUS:
            return
        try:
            event_type = getattr(EventTypes, "IMMUNE_RESPONSE", EventTypes.SYSTEM_EVENT)
            get_bus().publish(
                event_type,
                {
                    "signature": antibody.signature,
                    "antidote": antibody.antidote,
                    "severity": antibody.severity.name,
                    "encounters": antibody.encounters,
                    "strength": round(antibody.strength, 2),
                    "source": antibody.source,
                    "context": context[:200],
                },
                bron="black_box_immune",
            )
            logger.debug(
                "Vaccination broadcast: %s (severity=%s, encounters=%d)",
                antibody.signature[:40], antibody.severity.name, antibody.encounters,
            )
        except Exception as e:
            logger.debug("Vaccination broadcast failed: %s", e)

    # ── Query: Warnings + Predictive Immunity ──

    def retrieve_warnings(
        self,
        current_prompt: str,
        min_score: float = 0.5,
    ) -> str:
        """Check past failures AND active antibodies.

        Combines:
        1. Original vector-similarity warning (specific to this prompt)
        2. Active antibody scan (broad pattern immunity)
        """
        warnings = []

        # 1. Vector-based warning (original behavior)
        if self._store and self._store.documenten:
            results = self._store.zoek(
                query=current_prompt,
                top_k=1,
                filter_fn=lambda d: d.get("metadata", {}).get("type") == "failure_lesson",
                min_score=min_score,
            )
            if results:
                best = results[0]
                lesson = best.get("metadata", {}).get("lesson", "")
                if lesson:
                    warnings.append(
                        f"PAST MISTAKE: When asked about this topic previously, "
                        f'you failed by: "{lesson}".\n'
                        f"CONSTRAINT: Do not repeat this mistake."
                    )

        # 2. Active antibody scan — inject all relevant antidotes
        lower_prompt = current_prompt.lower()
        for sig, ab in self._antibodies.items():
            if not ab.alive:
                continue
            # Broad match: check if any signature words appear in the prompt
            sig_words = sig.split()
            match_count = sum(1 for w in sig_words if w in lower_prompt)
            if match_count >= max(1, len(sig_words) // 3):
                severity_prefix = {
                    Severity.MILD: "ADVISORY",
                    Severity.SEVERE: "WARNING",
                    Severity.CRITICAL: "CRITICAL BLOCK",
                }[ab.severity]
                warnings.append(
                    f"[{severity_prefix}] {ab.antidote} "
                    f"(strength={ab.strength:.0%}, encounters={ab.encounters})"
                )

        if not warnings:
            return ""

        return "[SYSTEM WARNING - IMMUNE MEMORY]\n" + "\n".join(warnings)

    # ── Maintenance ──

    def purge_dead(self) -> int:
        """Verwijder vervallen antibodies (strength < 5%)."""
        before = len(self._antibodies)
        self._antibodies = {
            sig: ab for sig, ab in self._antibodies.items() if ab.alive
        }
        removed = before - len(self._antibodies)
        if removed:
            self._save_immune_memory()
            logger.debug("Immune purge: %d dead antibodies removed", removed)
        return removed

    # ── Stats ──

    def get_stats(self) -> dict:
        """Immune system status."""
        count = len(self._store.documenten) if self._store else 0
        alive = [ab for ab in self._antibodies.values() if ab.alive]
        by_severity = {s.name: 0 for s in Severity}
        for ab in alive:
            by_severity[ab.severity.name] += 1
        return {
            "recorded_failures": count,
            "active_antibodies": len(alive),
            "total_antibodies": len(self._antibodies),
            "by_severity": by_severity,
            "strongest": max(
                (ab.signature for ab in alive),
                key=lambda s: self._antibodies[s].strength,
                default=None,
            ) if alive else None,
            "total_encounters": sum(ab.encounters for ab in alive),
        }

    def get_antibodies(self) -> List[dict]:
        """Return alle actieve antibodies als dicts (voor UI/diagnostiek)."""
        return [
            {**ab.to_dict(), "strength": round(ab.strength, 2)}
            for ab in self._antibodies.values()
            if ab.alive
        ]
