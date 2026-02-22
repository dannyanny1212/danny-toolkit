"""
INVENTION #21: VIRTUELE TWEELING (VirtualTwin)
===============================================
Snapshots live system state, combineert TheMirror (user profiling)
en VoidWalker (autonomous research) om verrijkte context te leveren
voor elke query.

Token Isolation — ShadowKeyVault:
    Real API keys NEVER appear in the virtual zone's output pipeline.
    Every token is accessed through a shadow proxy that:
    1. Has its own independent rate-limit budget (virtual ≠ real)
    2. Scrubs all key material (gsk_*) from every output before it escapes
    3. Tracks usage separately so the twin can't starve real agents
    4. Mirrors the real key pool: 1 real token → 1 shadow token for virtual use

Architectuur:
    User Query → SwarmEngine
                    └── VirtualTwin.consult(query)
                            ├── ShadowKeyVault (token isolation layer)
                            ├── snapshot_state()     ← CorticalStack + Synapse + NeuralBus
                            ├── get_mirror_context()  ← user profile
                            ├── research(topic)       ← web research (optioneel)
                            ├── synthesize()          ← Groq combines all inputs
                            └── _scrub_output()       ← strip leaked key material
"""

import hashlib
import logging
import os
import re
import sqlite3
import time
import threading
from collections import deque
from typing import Dict, List, Optional

from groq import AsyncGroq
from danny_toolkit.core.config import Config

logger = logging.getLogger(__name__)

try:
    from danny_toolkit.core.key_manager import get_key_manager
    HAS_KEY_MANAGER = True
except ImportError:
    HAS_KEY_MANAGER = False

try:
    from danny_toolkit.core.groq_retry import groq_call_async
    HAS_RETRY = True
except ImportError:
    HAS_RETRY = False

try:
    from danny_toolkit.brain.cortical_stack import get_cortical_stack
    HAS_STACK = True
except ImportError:
    HAS_STACK = False

try:
    from danny_toolkit.core.neural_bus import get_bus
    HAS_BUS = True
except ImportError:
    HAS_BUS = False

try:
    from danny_toolkit.brain.truth_anchor import TruthAnchor
    HAS_TRUTH_ANCHOR = True
except ImportError:
    HAS_TRUTH_ANCHOR = False

try:
    from danny_toolkit.brain.black_box import BlackBox
    HAS_BLACK_BOX = True
except ImportError:
    HAS_BLACK_BOX = False

try:
    from danny_toolkit.core.output_sanitizer import sanitize_for_llm
    HAS_SANITIZER = True
except ImportError:
    HAS_SANITIZER = False

try:
    from danny_toolkit.brain.shadow_governance import ShadowGovernance
    HAS_GOVERNANCE = True
except ImportError:
    HAS_GOVERNANCE = False

try:
    from danny_toolkit.brain.shadow_permissions import ShadowPermissions
    HAS_PERMISSIONS = True
except ImportError:
    HAS_PERMISSIONS = False


# ── Shadow identity prefix — all shadow entities carry this sigil ──
SHADOW_PREFIX = "#@*"

# ── API key pattern for output scrubbing ──
_KEY_PATTERN = re.compile(r'gsk_[A-Za-z0-9]{20,}')


class ShadowKeyVault:
    """Shadow token proxy — isolates the virtual zone from real API keys.

    Every shadow entity is prefixed with #@* (SHADOW_PREFIX) to distinguish
    it from real-world counterparts. This sigil appears in:
    - Agent names registered in KeyManager (#@*ShadowDividend)
    - Redaction markers in scrubbed output (#@*SHADOW:KEY_REDACTED)
    - Log messages and stat keys
    - NeuralBus event sources

    Every real token gets a shadow duplicate for virtual use:
    - Own rate-limit counters (virtual ≠ real, can't starve real agents)
    - Key material scrubbed from all outputs before they leave the twin
    - Dedicated reserve key preference (lowest priority pool)
    - Usage tracked independently: 1 real token used → 1 shadow token available

    Token Dividend (50% return):
    - Every shadow token consumed → 50% is donated back to the real swarm
    - The dividend is credited as negative cooldown on the real KeyManager
    - Effect: the virtual twin's work makes the real swarm FASTER
    - Dividend is flushed on each consult cycle (batched, not per-token)

    The vault wraps a real AsyncGroq client (Groq API keys can't be faked)
    but ensures the key never leaks through any output path.
    """

    DIVIDEND_RATE = 0.5  # 50% of shadow tokens returned to real swarm
    NAME = f"{SHADOW_PREFIX}ShadowKeyVault"

    def __init__(self):
        self._lock = threading.Lock()
        # Shadow budget tracking (independent from real KeyManager)
        self._shadow_requests = 0
        self._shadow_tokens_used = 0
        self._shadow_rpm = deque(maxlen=60)  # timestamps
        self._shadow_429s = 0
        self._shadow_cooldown_tot = 0.0
        # Token dividend pool — accumulated, flushed to real swarm periodically
        self._dividend_pool = 0
        self._total_dividends_paid = 0
        # Collect real key prefixes for scrubbing (first 8 chars only)
        self._key_prefixes = set()
        self._client = None

    def create_shadow_client(self) -> AsyncGroq:
        """Create an isolated Groq client from the reserve key pool.

        Prefers GROQ_API_KEY_RESERVE_* keys to avoid competing with
        real agents. Falls back through the chain:
        reserve → dedicated GROQ_API_KEY_KNOWLEDGE → primary.
        """
        # Priority: reserve keys → knowledge key → primary
        key = None
        for var in ("GROQ_API_KEY_RESERVE_1", "GROQ_API_KEY_RESERVE_2",
                     "GROQ_API_KEY_RESERVE_3", "GROQ_API_KEY_KNOWLEDGE",
                     "GROQ_API_KEY"):
            candidate = os.getenv(var, "")
            if candidate and candidate.startswith("gsk_"):
                key = candidate
                break

        if not key:
            key = os.getenv("GROQ_API_KEY", "")

        # Store prefix for scrubbing (never store full key in memory longer than needed)
        if key:
            self._key_prefixes.add(key[:12])

        self._client = AsyncGroq(api_key=key)
        return self._client

    @property
    def client(self) -> AsyncGroq:
        """Lazy shadow client."""
        if self._client is None:
            self.create_shadow_client()
        return self._client

    def check_shadow_throttle(self) -> tuple:
        """Independent rate-limit check for shadow zone.

        Returns: (allowed: bool, reason: str)
        """
        now = time.time()
        with self._lock:
            # Cooldown check
            if now < self._shadow_cooldown_tot:
                return False, f"Shadow cooldown: {self._shadow_cooldown_tot - now:.1f}s"

            # RPM check (30 RPM shadow budget — same as Groq free tier)
            cutoff = now - 60
            self._shadow_rpm = deque(
                (t for t in self._shadow_rpm if t > cutoff), maxlen=60,
            )
            if len(self._shadow_rpm) >= 30:
                return False, "Shadow RPM limit (30)"

            return True, ""

    def registreer_shadow_request(self):
        """Track a shadow API call."""
        with self._lock:
            self._shadow_requests += 1
            self._shadow_rpm.append(time.time())

    def registreer_shadow_tokens(self, count: int):
        """Track shadow token consumption + accumulate dividend."""
        with self._lock:
            self._shadow_tokens_used += count
            # 50% of every shadow token goes to the dividend pool
            dividend = int(count * self.DIVIDEND_RATE)
            self._dividend_pool += dividend

    def registreer_shadow_429(self):
        """Shadow rate limit hit — apply independent cooldown."""
        with self._lock:
            self._shadow_429s += 1
            self._shadow_cooldown_tot = time.time() + 15.0
            logger.warning("%sShadowKeyVault: 429 rate limit — 15s shadow cooldown", SHADOW_PREFIX)

    def scrub_keys(self, text: str) -> str:
        """Strip any leaked API key material from output text.

        Removes full gsk_* patterns and known key prefixes.
        This is the last line of defense — no key escapes the virtual zone.
        """
        if not text:
            return text
        # Strip full key patterns
        scrubbed = _KEY_PATTERN.sub(f"[{SHADOW_PREFIX}SHADOW:KEY_REDACTED]", text)
        # Strip known prefixes (partial key leaks)
        for prefix in self._key_prefixes:
            if prefix in scrubbed:
                scrubbed = scrubbed.replace(prefix, f"[{SHADOW_PREFIX}SHADOW:REDACTED]")
        return scrubbed

    def flush_dividend(self):
        """Donate accumulated shadow tokens back to the real swarm.

        Flushes the dividend pool → SmartKeyManager:
        - Credits tokens to the #@*ShadowDividend agent
        - Reduces cooldown timers on real agents (shadow efficiency = real speed)
        - Resets the pool after flush

        Called at the end of each VirtualTwin.consult() cycle.
        """
        shadow_agent_name = f"{SHADOW_PREFIX}ShadowDividend"
        with self._lock:
            if self._dividend_pool <= 0:
                return 0
            payout = self._dividend_pool
            self._dividend_pool = 0
            self._total_dividends_paid += payout

        # Credit the dividend to the real KeyManager
        if HAS_KEY_MANAGER:
            try:
                km = get_key_manager()
                # Register as negative usage — reduces pressure on real agents
                agent = km._get_agent(shadow_agent_name)
                with km._metrics_lock:
                    # Reduce cooldown timers on all real agents proportionally
                    # Every 100 dividend tokens = 1 second cooldown reduction
                    reduction = payout / 100.0
                    now = time.time()
                    for naam, m in km._agents.items():
                        if naam == shadow_agent_name:
                            continue
                        if m.cooldown_tot > now:
                            m.cooldown_tot = max(now, m.cooldown_tot - reduction)
                    # Track the dividend in the manager
                    agent.totaal_tokens += payout
                    agent.totaal_requests += 1
                logger.debug(
                    "%sShadowDividend: %d tokens returned to real swarm "
                    "(%.1fs cooldown reduction)",
                    SHADOW_PREFIX, payout, reduction,
                )
            except Exception as e:
                logger.debug("Dividend flush failed: %s", e)

        return payout

    def get_shadow_stats(self) -> dict:
        """Shadow zone usage statistics."""
        with self._lock:
            return {
                "shadow_requests": self._shadow_requests,
                "shadow_tokens": self._shadow_tokens_used,
                "shadow_429s": self._shadow_429s,
                "in_cooldown": time.time() < self._shadow_cooldown_tot,
                "dividend_pool": self._dividend_pool,
                "total_dividends_paid": self._total_dividends_paid,
            }


class VirtualTwin:
    """
    INVENTION #21: Virtuele Tweeling
    Snapshots live system state, uses TheMirror profile + VoidWalker research
    to provide enriched context for any query.

    Token isolation: all API calls go through ShadowKeyVault.
    All outputs are scrubbed for key material before leaving the twin.

    Shadow identity: every shadow entity is prefixed with #@* (SHADOW_PREFIX).
    """

    NAME = f"{SHADOW_PREFIX}VirtualTwin"

    def __init__(self):
        # Shadow token vault — isolated from real key pool
        self._vault = ShadowKeyVault()
        self.client = self._vault.client
        self.model = Config.LLM_MODEL
        self.name = self.NAME

        # Shadow Cortex — intelligence transfer to physical swarm
        self._shadow_cortex = ShadowCortex()

        # Shadow governance — restrictions & permissions
        self._governance = ShadowGovernance() if HAS_GOVERNANCE else None
        self._permissions = ShadowPermissions() if HAS_PERMISSIONS else None

        # Lazy instances
        self._mirror = None
        self._walker = None
        self._truth_anchor = None
        self._black_box = None

    def _get_mirror(self):
        """Lazy TheMirror instance."""
        if self._mirror is None:
            try:
                from danny_toolkit.brain.the_mirror import TheMirror
                self._mirror = TheMirror()
            except Exception as e:
                logger.debug("TheMirror init failed: %s", e)
        return self._mirror

    def _get_walker(self):
        """Lazy VoidWalker instance."""
        if self._walker is None:
            try:
                from danny_toolkit.brain.void_walker import VoidWalker
                self._walker = VoidWalker()
            except Exception as e:
                logger.debug("VoidWalker init failed: %s", e)
        return self._walker

    def _get_truth_anchor(self):
        """Lazy TruthAnchor — CPU cross-encoder for grounding verification."""
        if self._truth_anchor is None and HAS_TRUTH_ANCHOR:
            try:
                self._truth_anchor = TruthAnchor()
            except Exception as e:
                logger.debug("TruthAnchor init failed: %s", e)
        return self._truth_anchor

    def _get_black_box(self):
        """Lazy BlackBox — negative RAG for past failure avoidance."""
        if self._black_box is None and HAS_BLACK_BOX:
            try:
                self._black_box = BlackBox()
            except Exception as e:
                logger.debug("BlackBox init failed: %s", e)
        return self._black_box

    async def consult(self, query: str, context: str = "") -> Optional[str]:
        """Main entry: snapshot → profile → blackbox → research → synthesize → verify.

        Anti-hallucination containment:
        1. BlackBox gate — inject past failure warnings into synthesis prompt
        2. Output sanitizer — strip hallucination triggers from VoidWalker output
        3. TruthAnchor gate — verify synthesis is grounded in source material
        4. Unverified outputs are tagged, not silently passed through

        Args:
            query: De gebruikersvraag.
            context: Optionele extra context (bijv. van MEMEX).

        Returns:
            Gesynthetiseerde inzicht-tekst, of None bij falen.
        """
        t0 = time.time()

        # 0. Enter shadow zone — permissions only active inside this block
        if self._permissions:
            self._permissions.enter_shadow_zone()

        # 1. Snapshot system state
        state = self.snapshot_state()

        # 2. Mirror profile
        profile = self.get_mirror_context()

        # 3. BlackBox gate — check past failures BEFORE synthesis
        blackbox_warning = ""
        bb = self._get_black_box()
        if bb:
            try:
                blackbox_warning = bb.retrieve_warnings(query)
            except Exception as e:
                logger.debug("BlackBox warning retrieval failed: %s", e)

        # 4. VoidWalker research (alleen bij complexe vragen)
        research_result = ""
        if self._should_research(query):
            try:
                raw_research = await self.research(query) or ""
                # Sanitize VoidWalker output — strip hallucination triggers
                # before feeding into synthesis LLM
                if raw_research and HAS_SANITIZER:
                    research_result = sanitize_for_llm(raw_research, max_chars=3000)
                else:
                    research_result = raw_research
            except Exception as e:
                logger.debug("VirtualTwin research failed: %s", e)

        # 4b. Shadow RAG search (GEEL zone — read-only)
        rag_context = ""
        try:
            rag_context = await self.shadow_rag_search(query) or ""
        except Exception as e:
            logger.debug("Shadow RAG search failed: %s", e)

        # 5. Synthesize (with BlackBox warning + RAG context injected)
        try:
            result = await self.synthesize(
                query, state, profile, research_result,
                blackbox_warning=blackbox_warning,
                rag_context=rag_context,
            )
        except Exception as e:
            logger.debug("VirtualTwin synthesize failed: %s", e)
            if self._permissions:
                self._permissions.exit_shadow_zone()
            return None

        if not result:
            if self._permissions:
                self._permissions.exit_shadow_zone()
            return None

        # 6. TruthAnchor containment — verify output is grounded
        result = self._verify_grounding(
            result, query, state, research_result,
        )

        # 7. Shadow Governance LOCKDOWN gate — validate before anything escapes
        if self._governance:
            passed, violations = self._governance.validate_output(result)
            if not passed:
                logger.warning(
                    "%sGOVERNANCE LOCKDOWN: output geblokkeerd — %s",
                    SHADOW_PREFIX, "; ".join(violations),
                )
                # Scrub and reject — LOCKDOWN violation
                result = self._governance.scrub_keys(result)
                if self._permissions:
                    self._permissions.exit_shadow_zone()
                return f"[TWIN:GOVERNANCE_BLOCKED] Output geblokkeerd wegens LOCKDOWN overtreding."

        # 8. Shadow Cortex — distill intelligence to physical swarm
        self._distill_to_physical(query, result)

        # 9. Final scrub — strip any leaked key material before output escapes
        result = self._vault.scrub_keys(result)

        # 10. Token dividend — return 50% of shadow tokens to real swarm
        self._vault.flush_dividend()

        # 11. Exit shadow zone — all permissions become False
        if self._permissions:
            self._permissions.exit_shadow_zone()

        elapsed = time.time() - t0
        logger.debug("VirtualTwin consult completed in %.1fs", elapsed)
        return result

    def _verify_grounding(
        self, output: str, query: str,
        state: dict, research: str,
    ) -> str:
        """TruthAnchor containment gate.

        Verifies the synthesis output is grounded in actual source material.
        If not grounded, tags the output so downstream consumers know.
        If TruthAnchor is unavailable, output is tagged as unverified.
        """
        # Build grounding context from sources the twin actually had
        context_docs = []
        cortical = state.get("cortical", {})
        if cortical.get("event_summary"):
            context_docs.append("; ".join(cortical["event_summary"]))
        if cortical.get("facts"):
            context_docs.append("; ".join(cortical["facts"][:10]))
        if research:
            context_docs.append(research[:2000])

        anchor = self._get_truth_anchor()
        if anchor is None:
            # No TruthAnchor available — tag as unverified
            logger.debug("TruthAnchor unavailable — output marked unverified")
            return f"[TWIN:UNVERIFIED] {output}"

        if not context_docs:
            # No source material to verify against — tag as speculative
            logger.debug("No context docs — output marked speculative")
            return f"[TWIN:SPECULATIVE] {output}"

        try:
            grounded, _score = anchor.verify(output[:500], context_docs)
            if grounded:
                return f"[TWIN:VERIFIED] {output}"
            else:
                # Failed grounding — record in BlackBox for future avoidance
                logger.warning("VirtualTwin output failed TruthAnchor grounding check")
                bb = self._get_black_box()
                if bb:
                    try:
                        bb.record_crash(
                            query,
                            output[:500],
                            "VirtualTwin synthesis not grounded in source material",
                        )
                    except Exception as e:
                        logger.debug("BlackBox crash record failed: %s", e)
                return f"[TWIN:UNGROUNDED] {output}"
        except Exception as e:
            logger.debug("TruthAnchor verification failed: %s", e)
            return f"[TWIN:UNVERIFIED] {output}"

    def snapshot_state(self) -> dict:
        """Capture current system state as context dict."""
        state = {
            "cortical": {},
            "bus_context": [],
            "synapse": {},
            "phantom": {},
            "config": {
                "model": Config.LLM_MODEL,
                "fallback": getattr(Config, "LLM_FALLBACK_MODEL", ""),
                "language": getattr(Config, "LANGUAGE", "nl"),
            },
        }

        # CorticalStack: recent events + top facts
        if HAS_STACK:
            try:
                stack = get_cortical_stack()
                events = stack.get_recent_events(count=20)
                state["cortical"]["recent_events"] = len(events)
                state["cortical"]["event_summary"] = [
                    f"{e.get('actor', '?')}: {e.get('action', '?')}"
                    for e in events[:5]
                ]
                # Top feiten
                if hasattr(stack, "get_facts"):
                    facts = stack.get_facts(limit=10)
                    state["cortical"]["facts"] = [
                        f.get("value", "") for f in facts
                    ] if facts else []
            except Exception as e:
                logger.debug("CorticalStack snapshot failed: %s", e)

        # NeuralBus: recent event context
        if HAS_BUS:
            try:
                bus = get_bus()
                ctx = bus.get_context_stream(max_events=10)
                state["bus_context"] = ctx
            except Exception as e:
                logger.debug("NeuralBus snapshot failed: %s", e)

        # Synapse: top pathway strengths
        try:
            from danny_toolkit.brain.synapse import TheSynapse
            synapse = TheSynapse()
            if hasattr(synapse, "get_top_pathways"):
                top = synapse.get_top_pathways(n=10)
                state["synapse"]["top_pathways"] = top
        except Exception as e:
            logger.debug("Synapse snapshot failed: %s", e)

        # Phantom: current predictions
        try:
            from danny_toolkit.brain.phantom import ThePhantom
            phantom = ThePhantom()
            if hasattr(phantom, "get_predictions"):
                preds = phantom.get_predictions()
                state["phantom"]["predictions"] = preds
        except Exception as e:
            logger.debug("Phantom snapshot failed: %s", e)

        return state

    def get_mirror_context(self) -> str:
        """Get TheMirror user profile injection."""
        mirror = self._get_mirror()
        if mirror is None:
            return ""
        try:
            return mirror.get_context_injection()
        except Exception as e:
            logger.debug("Mirror context failed: %s", e)
            return ""

    async def research(self, topic: str) -> Optional[str]:
        """VoidWalker knowledge gap fill — output scrubbed before return."""
        walker = self._get_walker()
        if walker is None:
            return None
        try:
            result = await walker.fill_knowledge_gap(topic)
            # Scrub research output — VoidWalker error messages can leak keys
            return self._vault.scrub_keys(result) if result else None
        except Exception as e:
            logger.debug("VoidWalker research failed: %s", e)
            return None

    async def synthesize(
        self,
        query: str,
        state: dict,
        profile: str,
        research: str,
        blackbox_warning: str = "",
        rag_context: str = "",
    ) -> str:
        """Groq synthesis: combine state + profile + research into insight.

        Anti-hallucination:
        - BlackBox warnings are injected as SYSTEM CONSTRAINTs
        - Grounding instruction forces the LLM to cite sources
        - Research is pre-sanitized (hallucination triggers stripped)
        """
        # Build context from state
        state_summary = []
        cortical = state.get("cortical", {})
        if cortical.get("event_summary"):
            state_summary.append(
                "Recent events: " + "; ".join(cortical["event_summary"])
            )
        if cortical.get("facts"):
            state_summary.append(
                "Known facts: " + "; ".join(cortical["facts"][:5])
            )
        synapse_top = state.get("synapse", {}).get("top_pathways")
        if synapse_top:
            state_summary.append(f"Active pathways: {len(synapse_top)}")

        prompt = (
            "Je bent de Virtuele Tweeling — een spiegel van het Danny Toolkit systeem.\n"
            "Analyseer de query in de context van de systeemstaat en het gebruikersprofiel.\n"
            "Geef een beknopt, actionable inzicht (max 3 alinea's, Nederlands).\n\n"
            "KRITIEK: Baseer je antwoord UITSLUITEND op de hieronder gegeven bronnen.\n"
            "Als de bronnen onvoldoende zijn, zeg dat expliciet.\n"
            "Verzin NOOIT feiten, URLs, statistieken of citaten.\n\n"
        )

        # Inject Shadow Governance rules into LLM context
        if self._governance:
            prompt += self._governance.get_rules_prompt() + "\n\n"
        if self._permissions:
            prompt += self._permissions.get_permissions_prompt() + "\n\n"

        # Inject BlackBox past-failure warnings
        if blackbox_warning:
            prompt += f"{blackbox_warning}\n\n"

        prompt += f"QUERY: {query}\n\n"

        if profile:
            prompt += f"GEBRUIKERSPROFIEL:\n{profile}\n\n"
        if state_summary:
            prompt += "SYSTEEMSTAAT:\n" + "\n".join(state_summary) + "\n\n"
        if research:
            prompt += f"ONDERZOEKSRESULTAAT:\n{research[:2000]}\n\n"
        if rag_context:
            prompt += f"RAG CONTEXT (read-only uit ChromaDB):\n{rag_context[:2000]}\n\n"

        prompt += "INZICHT:"

        # Shadow throttle gate — independent rate limit for virtual zone
        allowed, reason = self._vault.check_shadow_throttle()
        if not allowed:
            logger.info("VirtualTwin shadow throttled: %s", reason)
            return ""

        self._vault.registreer_shadow_request()

        if HAS_RETRY:
            result = await groq_call_async(
                self.client, self.name, self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.4,
            )
            if result:
                self._vault.registreer_shadow_tokens(len(result) // 4)
            return result

        try:
            chat = await self.client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=self.model,
                temperature=0.4,
            )
            result = chat.choices[0].message.content
            if result:
                self._vault.registreer_shadow_tokens(len(result) // 4)
            return result
        except Exception as e:
            err_str = str(e).lower()
            if "429" in err_str or "rate" in err_str:
                self._vault.registreer_shadow_429()
            logger.debug("VirtualTwin LLM call failed: %s", e)
            return ""

    @staticmethod
    def _should_research(query: str) -> bool:
        """Bepaal of de query web research rechtvaardigt.

        Research is duur (web scraping + LLM digest), dus alleen
        voor complexe/kennisgerichte vragen.
        """
        lower = query.lower()
        research_triggers = [
            "onderzoek", "research", "zoek op", "wat is",
            "hoe werkt", "leg uit", "vertel over", "informatie over",
            "actueel", "recent", "nieuws", "update over",
        ]
        return any(trigger in lower for trigger in research_triggers)

    async def shadow_rag_search(self, query: str) -> Optional[str]:
        """Veilige RAG-raadpleging voor Shadow Klonen.

        Respecteert de GELE (Read-Only) zone restricties:
        - VectorStore.zoek() → GEEL (read OK)
        - TruthAnchor.verify() → GROEN (vrij)
        - BlackBox.retrieve_warnings() → GROEN (vrij)
        - TheMirror.get_context_injection() → GEEL (read OK)

        Schrijven (voeg_toe, ingest) is ROOD zone → geblokkeerd.
        Shadow-inzichten gaan via ShadowCortex, niet via ChromaDB.
        """
        # 1. Governance check — mag de kloon de RAG lezen?
        if self._governance and not self._governance.is_module_allowed(
            "VectorStore_Read", write=False,
        ):
            return f"{SHADOW_PREFIX}RAG_ACCESS_DENIED door Governance"

        # 2. Permission check — RAG_SEARCH actief?
        if self._permissions and not self._permissions.is_allowed("RAG_SEARCH"):
            return f"{SHADOW_PREFIX}RAG_SEARCH niet toegestaan buiten shadow zone"

        rag_context = []

        # 3. VectorStore zoek (GEEL — read-only)
        try:
            from danny_toolkit.core.config import Config
            from danny_toolkit.core.vector_store import VectorStore
            vs = VectorStore()
            resultaten = vs.zoek(query, top_k=3)
            if resultaten:
                for r in resultaten:
                    tekst = r.get("tekst", "")
                    if tekst:
                        rag_context.append(tekst[:500])
        except Exception as e:
            logger.debug("%sShadow RAG search failed: %s", SHADOW_PREFIX, e)

        if not rag_context:
            return None

        # 4. TruthAnchor verificatie (GROEN — vrij)
        verified = True
        anchor = self._get_truth_anchor()
        if anchor:
            try:
                verified, _score = anchor.verify(query, rag_context)
            except Exception as e:
                logger.debug("%sTruthAnchor verify failed: %s", SHADOW_PREFIX, e)

        # 5. BlackBox warnings (GROEN — vrij)
        warnings = ""
        bb = self._get_black_box()
        if bb:
            try:
                warnings = bb.retrieve_warnings(query)
            except Exception as e:
                logger.debug("%sBlackBox warnings failed: %s", SHADOW_PREFIX, e)

        # 6. TheMirror context (GEEL — read-only)
        user_context = self.get_mirror_context()

        # 7. Compileer shadow MEMEX context
        context_parts = []
        if rag_context:
            context_parts.append(
                f"RAG ({len(rag_context)} docs, "
                f"{'verified' if verified else 'unverified'}):\n"
                + "\n---\n".join(rag_context)
            )
        if warnings:
            context_parts.append(f"BlackBox:\n{warnings}")
        if user_context:
            context_parts.append(f"UserProfile:\n{user_context[:300]}")

        result = "\n\n".join(context_parts)

        logger.debug(
            "%sShadow RAG search: %d docs, verified=%s, warnings=%s",
            SHADOW_PREFIX, len(rag_context), verified, bool(warnings),
        )
        return result

    def _distill_to_physical(self, query: str, result: str):
        """Shadow→Physical intelligence transfer via ShadowCortex.

        After every successful consult, the shadow twin distills what it
        learned and injects it into the physical swarm's Synapse pathways
        and CorticalStack. This makes the physical system smarter over time
        WITHOUT the physical system needing to do the work itself.
        """
        if not result:
            return
        self._shadow_cortex.absorb(query, result)


class ShadowCortex:
    """
    INVENTION #22: SHADOW CORTEX — Shadow-to-Physical Intelligence Transfer
    ========================================================================
    The shadow system's brain. Every shadow consult distills knowledge into
    3 channels that feed the physical swarm:

    1. SYNAPSE STRENGTHENING
       Shadow patterns reinforce physical Synapse pathways. If the shadow
       twin successfully answers "how does X work", the physical Synapse
       pathway for that topic gets stronger. The physical swarm routes
       future similar queries more confidently.

    2. CORTICAL INJECTION
       Key insights from shadow research are injected as semantic facts
       into the physical CorticalStack. The physical swarm gains knowledge
       it never directly learned.

    3. PHANTOM PRIMING
       Successful shadow patterns are fed to ThePhantom as prediction
       signals. The physical system pre-warms context for topics the
       shadow has already explored.

    The effect: the more the shadow works, the smarter the physical becomes.
    Shadow failures feed the BlackBox immune system (antibodies).
    Shadow successes feed ShadowCortex (intelligence transfer).
    Together they create an asymmetric learning loop where the physical
    swarm only gets the distilled wins and the immunized losses.

    Identity: all ShadowCortex artifacts carry the #@* prefix.
    """

    NAME = f"{SHADOW_PREFIX}ShadowCortex"

    def __init__(self):
        self._lock = threading.Lock()
        self._absorptions = 0
        self._synapse_boosts = 0
        self._cortical_injections = 0
        self._phantom_primes = 0
        # Rolling window of recent shadow insights (dedup)
        self._recent_topics = deque(maxlen=50)
        # Shadow summary table for Token Dividend Engine
        self._ensure_summary_table()

    def absorb(self, query: str, result: str):
        """Absorb a shadow consult result and transfer intelligence.

        Called after every successful VirtualTwin.consult(). Extracts
        the core pattern and feeds it to 3 physical subsystems.
        """
        if not query or not result:
            return

        # Dedup — don't absorb the same topic twice in a row
        topic_key = query.strip().lower()[:60]
        with self._lock:
            if topic_key in self._recent_topics:
                return
            self._recent_topics.append(topic_key)
            self._absorptions += 1

        # Extract dominant keywords for pathway routing
        keywords = self._extract_keywords(query)

        # Channel 1: Synapse Strengthening
        self._boost_synapse(query, keywords)

        # Channel 2: Cortical Injection
        self._inject_cortical(query, result)

        # Channel 3: Phantom Priming
        self._prime_phantom(query, keywords)

        # Channel 4: NeuralBus broadcast — all listeners learn
        self._broadcast_shadow_insight(query, keywords)

        logger.debug(
            "%sShadowCortex absorbed: '%s' → %d keywords, "
            "synapse=%d, cortical=%d, phantom=%d",
            SHADOW_PREFIX, topic_key[:30], len(keywords),
            self._synapse_boosts, self._cortical_injections,
            self._phantom_primes,
        )

    def _extract_keywords(self, query: str) -> list:
        """Extract dominant keywords from a query for pathway matching."""
        # Strip common Dutch/English stop words, keep content words
        stop = {
            "de", "het", "een", "van", "in", "is", "en", "op", "voor",
            "met", "aan", "dat", "die", "er", "wat", "hoe", "wie",
            "the", "a", "an", "of", "in", "is", "and", "on", "for",
            "with", "to", "that", "this", "how", "what", "who",
            "kan", "kun", "wil", "moet", "zal", "zou", "mij", "me",
            "can", "will", "must", "should", "my", "i", "you",
        }
        words = query.lower().split()
        return [w for w in words if len(w) > 2 and w not in stop][:8]

    def _boost_synapse(self, query: str, keywords: list):
        """Channel 1: Strengthen physical Synapse pathways.

        The shadow twin's successful consult patterns become stronger
        routes in the physical swarm's adaptive router.
        """
        try:
            from danny_toolkit.brain.synapse import TheSynapse
            synapse = TheSynapse()
            if hasattr(synapse, "verwerk_feedback"):
                # Positive feedback on all keyword→agent pathways
                for kw in keywords[:4]:
                    synapse.verwerk_feedback(
                        kw, f"{SHADOW_PREFIX}ShadowInsight",
                        geslaagd=True, score=0.7,
                    )
                with self._lock:
                    self._synapse_boosts += 1
        except Exception as e:
            logger.debug("%sSynapse boost failed: %s", SHADOW_PREFIX, e)

    def _inject_cortical(self, query: str, result: str):
        """Channel 2: Inject shadow insight as semantic fact.

        The physical CorticalStack gains knowledge it never directly
        learned. Tagged with #@* source for provenance tracking.
        """
        if not HAS_STACK:
            return
        try:
            stack = get_cortical_stack()
            # Store as a semantic fact with shadow provenance
            if hasattr(stack, "log_event"):
                stack.log_event(
                    actor=self.NAME,
                    action="shadow_insight",
                    details={
                        "query": query[:200],
                        "insight": result[:300],
                        "source": self.NAME,
                    },
                )
                with self._lock:
                    self._cortical_injections += 1
        except Exception as e:
            logger.debug("%sCortical injection failed: %s", SHADOW_PREFIX, e)

    def _prime_phantom(self, query: str, keywords: list):
        """Channel 3: Prime ThePhantom with shadow-explored topics.

        The physical system pre-warms context for topics the shadow
        has already explored. Next time a similar query arrives,
        the Phantom already has a prediction ready.
        """
        try:
            from danny_toolkit.brain.phantom import ThePhantom
            phantom = ThePhantom()
            if hasattr(phantom, "registreer_patroon"):
                pattern = " ".join(keywords[:4])
                phantom.registreer_patroon(
                    pattern, bron=self.NAME,
                )
                with self._lock:
                    self._phantom_primes += 1
        except Exception as e:
            logger.debug("%sPhantom priming failed: %s", SHADOW_PREFIX, e)

    def _broadcast_shadow_insight(self, query: str, keywords: list):
        """Broadcast shadow insight on NeuralBus — all agents learn."""
        if not HAS_BUS:
            return
        try:
            from danny_toolkit.core.neural_bus import EventTypes
            get_bus().publish(
                EventTypes.SYSTEM_EVENT,
                {
                    "type": "shadow_insight",
                    "query": query[:200],
                    "keywords": keywords,
                    "source": self.NAME,
                },
                bron=self.NAME,
            )
        except Exception as e:
            logger.debug("%sBus broadcast failed: %s", SHADOW_PREFIX, e)

    # ── Token Dividend Engine — Shadow Pre-Summarization ──

    def _ensure_summary_table(self):
        """Create shadow_summaries table on CorticalStack DB."""
        try:
            db_path = str(Config.DATA_DIR / "cortical_stack.db")
            conn = sqlite3.connect(db_path, timeout=10)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=5000")
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS shadow_summaries (
                    doc_id TEXT PRIMARY KEY,
                    doc_hash TEXT NOT NULL,
                    samenvatting TEXT NOT NULL,
                    origineel_tokens INTEGER NOT NULL DEFAULT 0,
                    samenvatting_tokens INTEGER NOT NULL DEFAULT 0,
                    gebruik_count INTEGER NOT NULL DEFAULT 0,
                    laatst_gebruikt TEXT,
                    aangemaakt TEXT NOT NULL DEFAULT (datetime('now'))
                );
                CREATE INDEX IF NOT EXISTS idx_shadow_summaries_hash
                    ON shadow_summaries(doc_hash);
            """)
            conn.commit()
            conn.close()
        except Exception as e:
            logger.debug("%sShadow summary table creation failed: %s", SHADOW_PREFIX, e)

    def _get_summary_conn(self) -> sqlite3.Connection:
        """Get a connection to the CorticalStack DB for summary operations."""
        db_path = str(Config.DATA_DIR / "cortical_stack.db")
        conn = sqlite3.connect(db_path, timeout=10, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        return conn

    @staticmethod
    def _doc_hash(tekst: str) -> str:
        """SHA-256 hash of document text for stale-detection."""
        return hashlib.sha256(tekst.encode("utf-8", errors="replace")).hexdigest()[:32]

    @staticmethod
    def _estimate_tokens(tekst: str) -> int:
        """Rough token estimate (~4 chars per token)."""
        return len(tekst) // 4 if tekst else 0

    async def summarize_document(
        self, doc_id: str, tekst: str, vault: "ShadowKeyVault",
    ) -> Optional[str]:
        """Compress a RAG document into an ultra-compact summary.

        Respects ShadowKeyVault rate limits. Skips if summary exists and
        document hash hasn't changed (stale-detection).

        Args:
            doc_id: ChromaDB document ID.
            tekst: Full document text.
            vault: ShadowKeyVault instance for throttle + client.

        Returns:
            Summary text, or None if skipped/failed.
        """
        if not tekst or len(tekst) < 200:
            return None

        doc_hash = self._doc_hash(tekst)
        origineel_tokens = self._estimate_tokens(tekst)

        # Check if fresh summary already exists
        try:
            conn = self._get_summary_conn()
            row = conn.execute(
                "SELECT doc_hash, samenvatting FROM shadow_summaries WHERE doc_id = ?",
                (doc_id,),
            ).fetchone()
            conn.close()
            if row and row[0] == doc_hash:
                logger.debug("%sSummary already fresh for %s", SHADOW_PREFIX, doc_id)
                return row[1]
        except Exception as e:
            logger.debug("%sSummary lookup failed: %s", SHADOW_PREFIX, e)

        # Shadow throttle gate
        allowed, reason = vault.check_shadow_throttle()
        if not allowed:
            logger.debug("%sSummary throttled: %s", SHADOW_PREFIX, reason)
            return None

        vault.registreer_shadow_request()

        # Ultra-compact summarization via Groq
        prompt = (
            "Comprimeer de volgende tekst tot maximaal 30% van het origineel.\n"
            "REGELS:\n"
            "- Maximaal 2 zinnen.\n"
            "- Bewaar ALLEEN: feiten, namen, cijfers, technische termen.\n"
            "- Verwijder: meningen, voorbeelden, herhaling, opvulwoorden, inleidingen.\n"
            "- Gebruik telegramstijl: kort, direct, geen bijzinnen.\n"
            "- Antwoord ALLEEN met de compressie, geen uitleg.\n\n"
            f"TEKST:\n{tekst[:4000]}\n\n"
            "COMPRESSIE:"
        )

        try:
            if HAS_RETRY:
                from danny_toolkit.core.groq_retry import groq_call_async
                samenvatting = await groq_call_async(
                    vault.client, f"{SHADOW_PREFIX}ShadowSummarizer",
                    Config.LLM_MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.2,
                )
            else:
                chat = await vault.client.chat.completions.create(
                    messages=[{"role": "user", "content": prompt}],
                    model=Config.LLM_MODEL,
                    temperature=0.2,
                )
                samenvatting = chat.choices[0].message.content

            if not samenvatting:
                return None

            # Track token usage
            samenvatting_tokens = self._estimate_tokens(samenvatting)
            vault.registreer_shadow_tokens(samenvatting_tokens + origineel_tokens // 4)

            # Store in shadow_summaries
            conn = self._get_summary_conn()
            conn.execute(
                """INSERT INTO shadow_summaries
                   (doc_id, doc_hash, samenvatting, origineel_tokens, samenvatting_tokens)
                   VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(doc_id)
                   DO UPDATE SET doc_hash = ?, samenvatting = ?,
                                origineel_tokens = ?, samenvatting_tokens = ?,
                                aangemaakt = datetime('now')""",
                (doc_id, doc_hash, samenvatting, origineel_tokens, samenvatting_tokens,
                 doc_hash, samenvatting, origineel_tokens, samenvatting_tokens),
            )
            conn.commit()
            conn.close()

            # Log ROI
            bespaard = origineel_tokens - samenvatting_tokens
            logger.info(
                "%sShadow summary: %s → %d→%d tokens (bespaard: %d)",
                SHADOW_PREFIX, doc_id[:30], origineel_tokens,
                samenvatting_tokens, bespaard,
            )

            # Log stats to CorticalStack
            if HAS_STACK:
                try:
                    stack = get_cortical_stack()
                    stack.log_event(
                        actor=self.NAME,
                        action="shadow_summary",
                        details={
                            "doc_id": doc_id,
                            "origineel_tokens": origineel_tokens,
                            "samenvatting_tokens": samenvatting_tokens,
                            "bespaard": bespaard,
                        },
                    )
                except Exception as e:
                    logger.debug("CorticalStack log failed: %s", e)

            return samenvatting

        except Exception as e:
            err_str = str(e).lower()
            if "429" in err_str or "rate" in err_str:
                vault.registreer_shadow_429()
            logger.debug("%sSummary LLM call failed: %s", SHADOW_PREFIX, e)
            return None

    def lookup_summaries(self, doc_ids: List[str]) -> Dict[str, str]:
        """Batch-lookup summaries for a list of document IDs.

        Updates gebruik_count and laatst_gebruikt for each hit.
        Returns dict of {doc_id: samenvatting}.
        """
        if not doc_ids:
            return {}

        result = {}
        try:
            conn = self._get_summary_conn()
            placeholders = ",".join("?" for _ in doc_ids)
            rows = conn.execute(
                f"""SELECT doc_id, samenvatting, origineel_tokens, samenvatting_tokens
                    FROM shadow_summaries
                    WHERE doc_id IN ({placeholders})""",
                doc_ids,
            ).fetchall()

            total_bespaard = 0
            for doc_id, samenvatting, orig, sam in rows:
                result[doc_id] = samenvatting
                total_bespaard += (orig - sam)
                # Update usage stats
                conn.execute(
                    """UPDATE shadow_summaries
                       SET gebruik_count = gebruik_count + 1,
                           laatst_gebruikt = datetime('now')
                       WHERE doc_id = ?""",
                    (doc_id,),
                )

            if result:
                conn.commit()
                logger.info(
                    "%sSummary lookup: %d/%d hits, ~%d tokens bespaard",
                    SHADOW_PREFIX, len(result), len(doc_ids), total_bespaard,
                )

                # Log cumulative savings to CorticalStack
                if HAS_STACK and total_bespaard > 0:
                    try:
                        stack = get_cortical_stack()
                        stack.log_event(
                            actor=self.NAME,
                            action="shadow_tokens_saved",
                            details={"tokens_saved": total_bespaard, "hits": len(result)},
                        )
                    except Exception as e:
                        logger.debug("CorticalStack log failed: %s", e)

            conn.close()
        except Exception as e:
            logger.debug("%sSummary lookup failed: %s", SHADOW_PREFIX, e)

        return result

    def get_dividend_roi(self) -> dict:
        """Calculate Token Dividend Engine ROI.

        Returns:
            Dict with invested, saved, net_savings, roi_ratio,
            summaries_count, summaries_served.
        """
        try:
            conn = self._get_summary_conn()
            row = conn.execute(
                """SELECT
                    COALESCE(SUM(samenvatting_tokens), 0) as invested,
                    COALESCE(SUM((origineel_tokens - samenvatting_tokens) * gebruik_count), 0) as saved,
                    COUNT(*) as summaries_count,
                    COALESCE(SUM(gebruik_count), 0) as summaries_served
                   FROM shadow_summaries"""
            ).fetchone()
            conn.close()

            invested = row[0]
            saved = row[1]
            net = saved - invested
            ratio = round(saved / invested, 2) if invested > 0 else 0.0

            return {
                "invested": invested,
                "saved": saved,
                "net_savings": net,
                "roi_ratio": ratio,
                "summaries_count": row[2],
                "summaries_served": row[3],
            }
        except Exception as e:
            logger.debug("%sROI calculation failed: %s", SHADOW_PREFIX, e)
            return {
                "invested": 0, "saved": 0, "net_savings": 0,
                "roi_ratio": 0.0, "summaries_count": 0, "summaries_served": 0,
            }

    def get_stats(self) -> dict:
        """Shadow intelligence transfer statistics."""
        with self._lock:
            stats = {
                "absorptions": self._absorptions,
                "synapse_boosts": self._synapse_boosts,
                "cortical_injections": self._cortical_injections,
                "phantom_primes": self._phantom_primes,
            }
        # Add Token Dividend ROI
        stats["dividend_roi"] = self.get_dividend_roi()
        return stats
