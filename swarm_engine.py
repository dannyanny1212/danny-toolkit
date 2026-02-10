"""
SWARM ENGINE v5.0 — OOP + Asyncio Orchestrator
================================================

Vervangt de procedurele Hub & Spoke pipeline door:
  - Agent base class met async process()
  - Gespecialiseerde agents (Echo, Cipher, Vita, etc.)
  - SwarmEngine orchestrator met asyncio.gather()
  - Multi-intent keyword routing (parallel executie)

swarm_core.py blijft ongewijzigd (backward compat).

Gebruik:
    from swarm_engine import run_swarm_sync, SwarmPayload

    payloads = run_swarm_sync("bitcoin prijs", brain)
    for p in payloads:
        print(p.agent, p.type, p.content)
"""

import asyncio
import json
import re
import random
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime

import numpy as np
import pandas as pd


# ── CORTICAL STACK LOGGING ──

try:
    from danny_toolkit.brain.cortical_stack import (
        get_cortical_stack,
    )
    HAS_CORTICAL = True
except ImportError:
    HAS_CORTICAL = False


def _log_to_cortical(
    actor, action, details=None, source="swarm_engine"
):
    """Log naar CorticalStack als beschikbaar."""
    if not HAS_CORTICAL:
        return
    try:
        stack = get_cortical_stack()
        stack.log_event(
            actor=actor,
            action=action,
            details=details,
            source=source,
        )
    except Exception:
        pass


def _learn_from_input(prompt):
    """Extraheer feiten uit user input."""
    if not HAS_CORTICAL:
        return
    try:
        stack = get_cortical_stack()
        lower = prompt.lower().strip()

        if "mijn naam is " in lower:
            naam = prompt[
                lower.index("mijn naam is ") + 13:
            ]
            naam = naam.split(".")[0].split(",")[0].strip()
            if naam and len(naam) < 50:
                stack.remember_fact(
                    "user_name", naam, 0.9
                )

        for trigger in [
            "ik hou van ", "ik houd van "
        ]:
            if trigger in lower:
                val = prompt[
                    lower.index(trigger) + len(trigger):
                ]
                val = (
                    val.split(".")[0].split(",")[0].strip()
                )
                if val and len(val) < 100:
                    stack.remember_fact(
                        f"voorkeur_{hash(val) % 10000}",
                        f"Houdt van: {val}",
                        0.7,
                    )
                break
    except Exception:
        pass


# ── SWARM PAYLOAD ──

@dataclass
class SwarmPayload:
    """Gestandaardiseerd pakket dat door de Swarm reist."""
    agent: str
    type: str       # "text", "code", "metrics",
                    # "area_chart", "bar_chart"
    content: Any
    display_text: str = ""  # Wat de gebruiker ziet
    timestamp: float = field(
        default_factory=lambda: datetime.now().timestamp()
    )
    metadata: Dict[str, Any] = field(
        default_factory=dict
    )


# ── MEDIA GENERATORS ──

def _crypto_metrics():
    """Genereer crypto market ticker + 30d chart data."""
    np.random.seed(42)
    dagen = pd.date_range(
        end=datetime.now(), periods=30, freq="D"
    )
    prijs = 42000 + np.cumsum(
        np.random.randn(30) * 800
    )
    volume = np.abs(
        np.random.randn(30) * 500 + 2000
    )

    delta_pct = (
        (prijs[-1] - prijs[-2]) / prijs[-2] * 100
    )

    return {
        "type": "metrics",
        "category": "CRYPTO",
        "metrics": [
            {
                "label": "Bitcoin (BTC)",
                "value": f"${prijs[-1]:,.2f}",
                "delta": f"{delta_pct:+.2f}%",
            },
            {
                "label": "Ethereum (ETH)",
                "value": "$2,850.10",
                "delta": "-1.12%",
            },
            {
                "label": "Dominance",
                "value": "54.2%",
                "delta": "+0.4%",
            },
            {
                "label": "Fear & Greed",
                "value": "78",
                "delta": "Extreme Greed",
                "delta_color": "off",
            },
        ],
        "data": pd.DataFrame(
            {"Prijs (USD)": prijs}, index=dagen
        ),
        "extra": pd.DataFrame(
            {"Volume": volume}, index=dagen
        ),
    }


def _health_chart():
    """Genereer 24-uur HRV + hartslag data."""
    np.random.seed(7)
    uren = pd.date_range(
        end=datetime.now(), periods=24, freq="h"
    )
    hrv = np.abs(np.random.randn(24) * 15 + 55)
    hartslag = np.abs(np.random.randn(24) * 8 + 72)
    return {
        "type": "area_chart",
        "category": "HEALTH",
        "data": pd.DataFrame(
            {"HRV (ms)": hrv, "Hartslag": hartslag},
            index=uren,
        ),
    }


def _data_chart():
    """Genereer 6 systeem-metrics bar chart."""
    np.random.seed(13)
    labels = [
        "CPU", "RAM", "Disk", "Net",
        "GPU", "Cache",
    ]
    waarden = np.random.randint(20, 95, size=6)
    return {
        "type": "bar_chart",
        "category": "DATA",
        "data": pd.DataFrame(
            {"Gebruik (%)": waarden}, index=labels
        ),
    }


def _code_media(output):
    """Extraheer code blocks uit specialist output."""
    pattern = r"```(?:\w+)?\n(.*?)```"
    matches = re.findall(
        pattern, str(output), re.DOTALL
    )
    if matches:
        return {
            "type": "code",
            "category": "CODE",
            "code": matches[0].strip(),
        }
    return None


# ── AGENT CLASSES ──

class Agent:
    """Blauwdruk voor elke AI Agent."""

    def __init__(
        self, name: str, role: str,
        model: str = None,
    ):
        self.name = name
        self.role = role
        self.model = model

    async def process(
        self, task: str, brain=None,
    ) -> SwarmPayload:
        raise NotImplementedError


class BrainAgent(Agent):
    """Agent die via PrometheusBrain echte AI aanspreekt.

    Wraps sync brain._execute_with_role() in
    asyncio.to_thread() zodat meerdere agents
    tegelijkertijd kunnen draaien.
    """

    def __init__(
        self, name, role, cosmic_role, model=None,
    ):
        super().__init__(name, role, model)
        self.cosmic_role = cosmic_role

    async def process(self, task, brain=None):
        if not brain:
            return SwarmPayload(
                agent=self.name, type="text",
                content="Brain offline",
                display_text="Brain offline",
            )
        result, exec_time, status = (
            await asyncio.to_thread(
                brain._execute_with_role,
                self.cosmic_role, task,
            )
        )
        content = (
            str(result) if result
            else f"{self.name}: geen resultaat"
        )
        return SwarmPayload(
            agent=self.name,
            type="text",
            content=content,
            display_text=content,
            metadata={
                "execution_time": exec_time,
                "status": status,
            },
        )


class EchoAgent(Agent):
    """Fast-track smalltalk, geen AI nodig."""

    RESPONSES = [
        "Hoi! Alle systemen operationeel."
        " Waarmee kan ik helpen?",
        "Hallo! De Swarm is online en luistert.",
        "Goedendag! Nexus staat stand-by.",
        "Hey! Klaar voor actie.",
    ]

    async def process(self, task, brain=None):
        resp = random.choice(self.RESPONSES)
        return SwarmPayload(
            agent=self.name, type="text",
            content=resp,
            display_text=resp,
        )


class CipherAgent(BrainAgent):
    """Crypto specialist — levert metrics payload."""

    async def process(self, task, brain=None):
        payload = await super().process(task, brain)
        payload.type = "metrics"
        payload.metadata["media"] = _crypto_metrics()
        return payload


class VitaAgent(BrainAgent):
    """Health specialist — levert area_chart payload."""

    async def process(self, task, brain=None):
        payload = await super().process(task, brain)
        payload.type = "area_chart"
        payload.metadata["media"] = _health_chart()
        return payload


class AlchemistAgent(BrainAgent):
    """Data specialist — levert bar_chart payload."""

    async def process(self, task, brain=None):
        payload = await super().process(task, brain)
        payload.type = "bar_chart"
        payload.metadata["media"] = _data_chart()
        return payload


class IolaaxAgent(BrainAgent):
    """Code specialist — detecteert code blocks."""

    async def process(self, task, brain=None):
        payload = await super().process(task, brain)
        code_media = _code_media(payload.content)
        if code_media:
            payload.type = "code"
            payload.metadata["media"] = code_media
        return payload


class MemexAgent(BrainAgent):
    """Agentic RAG: plan → zoek → synthetiseer.

    Stap 1: LLM genereert zoektermen (plan).
    Stap 2: CorticalStack doorzoeken (execute).
    Stap 3: LLM schrijft rapport met bronnen.
    """

    def _get_cortical_stack(self):
        """Haal CorticalStack op (lazy)."""
        try:
            from danny_toolkit.brain.cortical_stack import (
                get_cortical_stack,
            )
            return get_cortical_stack()
        except Exception:
            return None

    def _search_cortical(self, query):
        """Doorzoek CorticalStack events + feiten."""
        stack = self._get_cortical_stack()
        if not stack:
            return []

        results = []
        try:
            events = stack.search_events(
                query, limit=5
            )
            for e in events:
                actor = e.get("actor", "?")
                action = e.get("action", "?")
                details = str(
                    e.get("details", "")
                )[:200]
                results.append(
                    f"[Event] {actor}/{action}:"
                    f" {details}"
                )
        except Exception:
            pass

        try:
            facts = stack.recall_all(
                min_confidence=0.3
            )
            lower = query.lower()
            for f in facts:
                val = str(f.get("value", ""))
                if (
                    lower in val.lower()
                    or any(
                        w in val.lower()
                        for w in lower.split()
                        if len(w) > 3
                    )
                ):
                    results.append(
                        f"[Feit] {f.get('key', '?')}:"
                        f" {val}"
                    )
        except Exception:
            pass

        return results

    async def process(self, task, brain=None):
        if not brain:
            return SwarmPayload(
                agent=self.name, type="text",
                content="Brain offline",
                display_text="Brain offline",
            )

        # Stap 1: PLAN — genereer zoektermen
        plan_prompt = (
            "Jij bent een Expert Onderzoeker."
            f" De gebruiker vraagt: '{task}'."
            " Genereer 3 specifieke zoektermen"
            " voor de database."
            ' Antwoord ALLEEN als JSON lijst:'
            ' ["term1", "term2", "term3"]'
        )
        plan_raw, _, _ = await asyncio.to_thread(
            brain._execute_with_role,
            self.cosmic_role, plan_prompt,
        )

        try:
            # Zoek JSON array in output
            match = re.search(
                r"\[.*?\]", str(plan_raw)
            )
            if match:
                queries = json.loads(match.group())
            else:
                queries = [task]
        except (json.JSONDecodeError, ValueError):
            queries = [task]

        # Stap 2: EXECUTE — doorzoek CorticalStack
        all_docs = []
        for q in queries[:3]:
            docs = await asyncio.to_thread(
                self._search_cortical, q
            )
            all_docs.extend(docs)

        # Deduplicate
        seen = set()
        unique_docs = []
        for d in all_docs:
            if d not in seen:
                seen.add(d)
                unique_docs.append(d)

        sources_count = len(unique_docs)
        if unique_docs:
            context = "\n".join(unique_docs[:15])
        else:
            context = (
                "Geen relevante bronnen gevonden"
                " in de database."
            )

        # Stap 3: SYNTHESIZE — rapport met bronnen
        synth_prompt = (
            "Gebruik UITSLUITEND deze context om"
            " de vraag te beantwoorden.\n"
            f"Vraag: {task}\n\n"
            f"Context:\n{context}\n\n"
            "Regels:\n"
            "1. Wees accuraat.\n"
            "2. Gebruik [Bron: X] waar mogelijk.\n"
            "3. Als het antwoord niet in de context"
            " staat, zeg dat eerlijk."
        )
        answer, exec_time, status = (
            await asyncio.to_thread(
                brain._execute_with_role,
                self.cosmic_role, synth_prompt,
            )
        )

        display = (
            str(answer) if answer
            else "Geen antwoord gegenereerd"
        )

        return SwarmPayload(
            agent=self.name,
            type="research",
            content={
                "queries": queries[:3],
                "sources_count": sources_count,
                "raw_text": display,
            },
            display_text=display,
            metadata={
                "execution_time": exec_time,
                "status": status,
                "queries": queries[:3],
                "sources": sources_count,
            },
        )


# ── FAST-TRACK ──

_GREETING_PATTERNS = [
    r"^hallo\b", r"^hoi\b", r"^hey\b", r"^hi\b",
    r"^goede(morgen|middag|avond)\b", r"^yo\b",
    r"^hoe gaat het", r"^bedankt", r"^dank je",
    r"^doei\b", r"^tot ziens",
]


def _fast_track_check(prompt):
    """Regex check voor simpele begroetingen."""
    lower = prompt.lower().strip()
    if len(lower.split()) < 6:
        if any(
            re.search(p, lower)
            for p in _GREETING_PATTERNS
        ):
            resp = random.choice(
                EchoAgent.RESPONSES
            )
            return SwarmPayload(
                agent="Echo", type="text",
                content=resp,
                display_text=resp,
            )
    return None


# ── SWARM ENGINE ──

class SwarmEngine:
    """Async orchestrator met multi-intent routing."""

    # Keyword → Agent mapping (uit NEXUS_KEYWORD_MAP)
    ROUTE_MAP = {
        "IOLAAX": [
            "code", "debug", "refactor", "git",
            "functie", "class", "programmeer", "build",
            "compile", "test", "script", "python",
            "javascript",
        ],
        "CIPHER": [
            "blockchain", "crypto", "encrypt",
            "decrypt", "smart contract", "bitcoin",
            "wallet", "token", "ethereum",
        ],
        "VITA": [
            "health", "hrv", "biohack", "biodata",
            "biometr", "peptide", "gezondheid",
            "slaap", "eiwit", "dna", "stress",
        ],
        "NAVIGATOR": [
            "zoek op", "search", "fetch", "scrape",
            "api call", "onderzoek", "explore",
            "discover", "research",
        ],
        "ORACLE": [
            "denk na", "logica", "redeneer", "droom",
            "bewustzijn", "evolve", "filosofie",
            "ethiek", "waarom", "hypothese",
        ],
        "SPARK": [
            "creatief", "idee", "brainstorm",
            "ascii", "kunst", "innovate", "design",
        ],
        "SENTINEL": [
            "beveilig", "security", "firewall",
            "audit", "threat",
        ],
        "ARCHIVIST": [
            "zoek kennis", "herinner", "rag",
            "vector", "semantic", "geheugen",
            "knowledge",
        ],
        "ALCHEMIST": [
            "convert", "transform", "data_clean",
            "etl",
        ],
        "VOID": [
            "cleanup", "clean", "delete", "opruim",
            "cache", "garbage",
        ],
        "CHRONOS_AGENT": [
            "schedule", "cronjob", "timer", "ritme",
            "planning", "agenda", "deadline",
            "wanneer", "herinnering",
        ],
        "PIXEL": [
            "help", "uitleg", "interface", "praat",
            "emotie", "gevoel", "dashboard", "menu",
            "teken", "visualiseer",
        ],
    }

    def __init__(self, brain=None):
        self.brain = brain
        self.agents = self._register_agents()

    def _register_agents(self):
        from danny_toolkit.brain.trinity_omega import (
            CosmicRole,
        )
        return {
            "IOLAAX": IolaaxAgent(
                "Iolaax", "Engineer",
                CosmicRole.IOLAAX,
            ),
            "CIPHER": CipherAgent(
                "Cipher", "Finance",
                CosmicRole.CIPHER,
            ),
            "VITA": VitaAgent(
                "Vita", "Health",
                CosmicRole.VITA,
            ),
            "ECHO": EchoAgent(
                "Echo", "Interface",
            ),
            "NAVIGATOR": BrainAgent(
                "Navigator", "Search",
                CosmicRole.NAVIGATOR,
            ),
            "ORACLE": BrainAgent(
                "Oracle", "Reasoning",
                CosmicRole.ORACLE,
            ),
            "SPARK": BrainAgent(
                "Spark", "Creative",
                CosmicRole.SPARK,
            ),
            "SENTINEL": BrainAgent(
                "Sentinel", "Security",
                CosmicRole.SENTINEL,
            ),
            "ARCHIVIST": MemexAgent(
                "Memex", "Memory",
                CosmicRole.ARCHIVIST,
            ),
            "CHRONOS_AGENT": BrainAgent(
                "Chronos", "Schedule",
                CosmicRole.CHRONOS,
            ),
            "WEAVER": BrainAgent(
                "Weaver", "Synthesis",
                CosmicRole.WEAVER,
            ),
            "PIXEL": BrainAgent(
                "Pixel", "Interface",
                CosmicRole.PIXEL,
            ),
            "ALCHEMIST": AlchemistAgent(
                "Alchemist", "Data",
                CosmicRole.ALCHEMIST,
            ),
            "VOID": BrainAgent(
                "Void", "Cleanup",
                CosmicRole.VOID,
            ),
        }

    async def route(self, user_input: str) -> List[str]:
        """Multi-intent keyword routing.

        Scant input op keywords voor meerdere agents
        tegelijkertijd. Fallback naar ECHO.
        """
        lower = user_input.lower()
        targets = []
        for agent_key, keywords in self.ROUTE_MAP.items():
            if any(kw in lower for kw in keywords):
                targets.append(agent_key)
        return targets or ["ECHO"]

    async def run(
        self, user_input: str, callback=None,
    ) -> List[SwarmPayload]:
        """Hoofdloop: route -> parallel execute.

        Args:
            user_input: Tekst van de gebruiker.
            callback: Functie(str) voor live updates.

        Returns:
            Lijst van SwarmPayloads (1 per agent).
        """
        def log(msg):
            if callback:
                callback(msg)

        # Cortical Stack logging
        _log_to_cortical(
            "user", "query",
            {"prompt": user_input[:500]},
        )
        _learn_from_input(user_input)

        # 1. Governor gate
        if self.brain:
            safe, reason = (
                self.brain._governor_gate(user_input)
            )
            if not safe:
                log(
                    f"\u274c Governor: BLOCKED"
                    f" \u2014 {reason}"
                )
                blocked = f"BLOCKED: {reason}"
                return [SwarmPayload(
                    agent="Governor", type="text",
                    content=blocked,
                    display_text=blocked,
                )]
            log(
                "\U0001f6e1\ufe0f Governor:"
                " Input SAFE \u2713"
            )

        # 2. Fast-Track check
        fast = _fast_track_check(user_input)
        if fast:
            log("\u26a1 [FAST-TRACK] Echo")
            _log_to_cortical(
                "swarm", "fast_track",
                {"agent": "Echo",
                 "prompt": user_input[:200]},
            )
            log("\u2705 SWARM COMPLETE (fast-track)")
            return [fast]

        # 3. Chronos enrichment
        if self.brain:
            enriched = self.brain._chronos_enrich(
                user_input
            )
            try:
                prefix = enriched[
                    :enriched.index("]") + 1
                ]
            except ValueError:
                prefix = enriched[:40]
            log(f"\u23f3 Chronos: {prefix} \u2713")
        else:
            enriched = user_input

        # 4. Route (multi-intent)
        targets = await self.route(user_input)
        log(
            f"\U0001f9e0 Nexus \u2192"
            f" {', '.join(targets)}"
        )

        # 5. Parallel executie via asyncio.gather
        tasks = []
        for name in targets:
            agent = self.agents[name]
            log(f"\u26a1 {agent.name}: gestart...")
            tasks.append(
                agent.process(enriched, self.brain)
            )

        results = await asyncio.gather(*tasks)

        # 6. Callback per resultaat
        for res in results:
            t = res.metadata.get(
                "execution_time", 0
            )
            log(
                f"\u2705 {res.agent}: klaar"
                f" ({t:.1f}s)"
            )

        # 7. Cortical Stack logging
        _log_to_cortical(
            "swarm", "response",
            {
                "agents": [r.agent for r in results],
                "output_preview": str(
                    results[0].content
                )[:300],
            },
        )

        log("\u2705 SWARM COMPLETE")
        return results


# ── SYNC WRAPPER ──

def run_swarm_sync(
    user_input, brain=None, callback=None,
):
    """Sync wrapper voor Streamlit/CLI.

    Args:
        user_input: Tekst van de gebruiker.
        brain: PrometheusBrain instantie.
        callback: Functie(str) voor live updates.

    Returns:
        Lijst van SwarmPayloads.
    """
    engine = SwarmEngine(brain=brain)
    return asyncio.run(
        engine.run(user_input, callback)
    )
