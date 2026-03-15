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
from __future__ import annotations

import atexit
import asyncio
import hashlib
import json
import logging
import math
import os
import re
import random
import sys
import time
import uuid
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any, Optional

# Max workers voor de per-loop thread pool (I/O-bound Groq calls).
# CPU-core-aware: min(cpu_count, 16) met floor van 4 voor lichte machines.
_SWARM_MAX_WORKERS = min(max(os.cpu_count() or 4, 4), 16)
from dataclasses import dataclass, field
from datetime import datetime

# Lazy-load: numpy/pandas alleen nodig voor demo data + charts, niet voor core pipeline
np = None  # type: ignore[assignment]
pd = None  # type: ignore[assignment]


def _ensure_np_pd() -> None:
    """Lazy-load numpy + pandas bij eerste gebruik."""
    global np, pd
    if np is None:
        import numpy
        np = numpy
    if pd is None:
        import pandas
        pd = pandas

logger = logging.getLogger(__name__)

# ── PER-AGENT PIPELINE METRICS (module-level singleton) ──

import threading as _threading

_AGENT_PIPELINE_METRICS: Dict[str, Dict[str, Any]] = {}
_METRICS_LOCK = _threading.Lock()

# ── Phase 100: B-95 background writer (1 daemon thread, fire-and-forget) ──
_B95_EXECUTOR = ThreadPoolExecutor(max_workers=2, thread_name_prefix="b95")

# ── Phase 31: PER-AGENT TIMEOUTS (seconden) ──

_DEFAULT_AGENT_TIMEOUT = 20  # seconden
_AGENT_TIMEOUTS: Dict[str, float] = {
    "MEMEX": 10,
    "Strategist": 18,
    "Artificer": 18,
    "VirtualTwin": 15,
    "CentralBrain": 18,
    "VoidWalker": 20,
}

# ── Phase 31: PER-AGENT CIRCUIT BREAKER ──

_CIRCUIT_BREAKER_THRESHOLD = 3   # opeenvolgende fouten → open
_CIRCUIT_BREAKER_COOLDOWN = 12   # cycli (queries) dat agent uitgeschakeld is
_AGENT_CIRCUIT_STATE: Dict[str, Dict[str, Any]] = {}
_CIRCUIT_LOCK = _threading.Lock()


def get_circuit_state() -> Dict[str, Any]:
    """Geeft huidige circuit breaker status per agent."""
    with _CIRCUIT_LOCK:
        return {
            naam: {
                "consecutive_failures": s["failures"],
                "is_open": s["failures"] >= _CIRCUIT_BREAKER_THRESHOLD,
                "cooldown_remaining": max(0, s.get("cooldown", 0)),
            }
            for naam, s in _AGENT_CIRCUIT_STATE.items()
        }


# ── MANUAL AGENT PAUSE ──

_PAUSED_AGENTS: set = set()
_PAUSE_LOCK = _threading.Lock()


def pause_agent(name: str) -> bool:
    """Zet een agent op PAUZE — wordt overgeslagen bij routing."""
    with _PAUSE_LOCK:
        _PAUSED_AGENTS.add(name.upper())
    return True


def resume_agent(name: str) -> bool:
    """Hervat een gepauzeerde agent."""
    with _PAUSE_LOCK:
        _PAUSED_AGENTS.discard(name.upper())
    return True


def get_paused_agents() -> list:
    """Lijst van handmatig gepauzeerde agents."""
    with _PAUSE_LOCK:
        return sorted(_PAUSED_AGENTS)


def boost_agent(agent_name: str) -> Dict[str, Any]:
    """Operation Phoenix: rehabilitate an underperforming agent.

    Gives the agent 3 consecutive trivial success tasks via Hebbian
    plasticity to undo WEAKEN penalties and restore SP.

    Returns dict with old_sp, new_sp, and reinforcement details.
    """
    try:
        from danny_toolkit.brain.synapse import get_synapse
        synapse = get_synapse()
        return synapse.phoenix_boost(agent_name)
    except Exception as e:
        logger.error("boost_agent failed for %s: %s", agent_name, e)
        return {"agent": agent_name, "error": str(e)}


def get_pipeline_metrics() -> Dict[str, Any]:
    """Per-agent pipeline metrics (module-level singleton)."""
    with _METRICS_LOCK:
        result = {}
        for naam, m in _AGENT_PIPELINE_METRICS.items():
            result[naam] = {
                "calls": m["calls"],
                "errors": m["errors"],
                "avg_ms": round(m["total_ms"] / max(m["calls"], 1), 1),
                "success_rate": round(
                    (m["calls"] - m["errors"]) / max(m["calls"], 1) * 100, 1
                ),
                "last_error": m["last_error"],
            }
        return result


# ── Phase 38: ERROR HISTORY RING BUFFER ──

_ERROR_HISTORY: deque = deque(maxlen=200)
_ERROR_HISTORY_LOCK = _threading.Lock()


def _record_error_context(fc: object) -> None:
    """Voeg FoutContext toe aan de ring buffer."""
    try:
        with _ERROR_HISTORY_LOCK:
            _ERROR_HISTORY.append(fc)
    except Exception as e:
        logger.debug("_record_error_context fout: %s", e)


def get_recent_errors(count: int = 50) -> list[object]:
    """Retourneer recente FoutContext objecten (nieuwste eerst)."""
    try:
        with _ERROR_HISTORY_LOCK:
            items = list(_ERROR_HISTORY)
        items.reverse()
        return items[:count]
    except Exception as e:
        logger.debug("get_recent_errors fout: %s", e)
        return []


# ── CUSTOM EXCEPTIONS ──

class TaskVerificationError(Exception):
    """Fout bij verificatie van een swarm taak."""

    def __init__(
        self, bericht: str, taak: dict | None = None,
        agent: str | None = None, payload: Any = None,
    ) -> None:
        """Initialiseer verificatie fout met taak context."""
        super().__init__(bericht)
        self.taak = taak
        self.agent = agent
        self.payload = payload


# ── CONFIG ──
from danny_toolkit.core.config import Config

# ── SANDBOXED TOOLS ──
try:
    from danny_toolkit.core.swarm_tools import (
        file_scribe_write,
        file_scribe_read,
        file_scribe_list,
        terminal_exec,
    )
    HAS_SWARM_TOOLS = True
except ImportError:
    HAS_SWARM_TOOLS = False

# ── PHANTOM AGENT (Mirror Shield Honeypot) ──

try:
    from danny_toolkit.agents.phantom_agent import PhantomAgent
    HAS_PHANTOM = True
except ImportError:
    HAS_PHANTOM = False
    PhantomAgent = None

# ── CORTICAL STACK LOGGING ──

try:
    from danny_toolkit.brain.cortical_stack import (
        get_cortical_stack,
    )
    HAS_CORTICAL = True
except ImportError:
    HAS_CORTICAL = False


def _log_to_cortical(
    actor: str, action: str, details: dict | None = None, source: str = "swarm_engine",
    trace_id: str | None = None,
) -> None:
    """Log naar CorticalStack als beschikbaar."""
    if not HAS_CORTICAL:
        return
    try:
        if trace_id and details is not None:
            if isinstance(details, dict):
                details["trace_id"] = trace_id
            else:
                details = {"original": details, "trace_id": trace_id}
        elif trace_id:
            details = {"trace_id": trace_id}
        stack = get_cortical_stack()
        stack.log_event(
            actor=actor,
            action=action,
            details=details,
            source=source,
        )
    except Exception as e:
        logger.debug("Cortical log failed: %s", e)


def _learn_from_input(prompt: str) -> None:
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
    except Exception as e:
        logger.debug("Fact extraction failed: %s", e)


def _shutdown() -> None:
    """Flush CorticalStack op shutdown."""
    if HAS_CORTICAL:
        try:
            stack = get_cortical_stack()
            stack.flush()
        except Exception as e:
            logger.debug("CorticalStack flush on shutdown failed: %s", e)

atexit.register(_shutdown)


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
    trace_id: str = ""  # Phase 31: request correlation ID


# ── MEDIA GENERATORS ──

def _crypto_metrics() -> dict:
    """Genereer crypto market ticker + 30d chart data."""
    _ensure_np_pd()
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


def _health_chart() -> dict:
    """Genereer 24-uur HRV + hartslag data."""
    _ensure_np_pd()
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


def _data_chart() -> dict:
    """Genereer 6 systeem-metrics bar chart."""
    _ensure_np_pd()
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


def _code_media(output: Any) -> dict | None:
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
    ) -> None:
        """Initialiseer agent met naam, rol en optioneel model."""
        self.name = name
        self.role = role
        self.model = model

    async def process(
        self, task: str, brain: Any = None,
    ) -> SwarmPayload:
        """Verwerk een taak en retourneer SwarmPayload (abstract)."""
        raise NotImplementedError


class BrainAgent(Agent):
    """Agent die via PrometheusBrain echte AI aanspreekt.

    Wraps sync brain._execute_with_role() in
    asyncio.to_thread() zodat meerdere agents
    tegelijkertijd kunnen draaien.
    """

    def __init__(
        self, name: str, role: str, cosmic_role: Any, model: str | None = None,
    ) -> None:
        """Initialiseer BrainAgent met cosmic role binding."""
        super().__init__(name, role, model)
        self.cosmic_role = cosmic_role

    async def process(self, task: str, brain: Any = None) -> SwarmPayload:
        """Verwerk taak via PrometheusBrain cosmic role."""
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
    """Circuit Breaker — O(1) latency veiligheidsklep.

    Zero-LLM fallback node voor Out-Of-Domain queries
    en Swarm overbelasting. Geen netwerkcalls, geen
    embeddings. Puur defensief routeren.
    """

    RESPONSES = [
        "Hoi! Alle systemen operationeel."
        " Waarmee kan ik helpen?",
        "Hallo! De Swarm is online en luistert.",
        "Goedendag! Nexus staat stand-by.",
        "Hey! Klaar voor actie.",
    ]

    async def process(self, task: str, brain: Any = None) -> SwarmPayload:
        """O(1) deterministische response — geen AI, geen netwerk."""
        resp = random.choice(self.RESPONSES)
        return SwarmPayload(
            agent=self.name, type="echo",
            content=resp,
            display_text=resp,
        )


class CipherAgent(BrainAgent):
    """Quantitative JSON Engine — real-time financiële/crypto parser.

    Verwerkt numerieke data-stromen en OHLCV data.
    Output is strict machine-readable JSON (type: 'metrics').
    """

    async def process(self, task: str, brain: Any = None) -> SwarmPayload:
        """Verwerk financiële/crypto data naar metrics JSON payload."""
        try:
            payload = await super().process(task, brain)
        except Exception as e:
            logger.debug("CipherAgent brain fout: %s", e)
            payload = SwarmPayload(
                agent=self.name, type="text",
                content=f"Crypto analyse (offline): {task[:80]}",
                display_text="Crypto analyse (offline modus)",
            )
        payload.type = "metrics"
        payload.metadata["media"] = _crypto_metrics()
        return payload


class VitaAgent(BrainAgent):
    """Time-Series Telemetry — chronologische data aggregator.

    Normaliseert en aggregeert tijdgebonden datapunten
    voor area_chart visualisatie ([timestamp, value] pairs).
    """

    async def process(self, task: str, brain: Any = None) -> SwarmPayload:
        """Verwerk time-series data naar area_chart payload."""
        try:
            payload = await super().process(task, brain)
        except Exception as e:
            logger.debug("VitaAgent brain fout: %s", e)
            payload = SwarmPayload(
                agent=self.name, type="text",
                content=f"Gezondheid analyse (offline): {task[:80]}",
                display_text="Gezondheid analyse (offline modus)",
            )
        payload.type = "area_chart"
        payload.metadata["media"] = _health_chart()
        return payload


class AlchemistAgent(BrainAgent):
    """Categorical Transformer — dimensionality reduction & bucketing.

    Transformeert multi-variabele data naar gecategoriseerde
    datasets voor bar_chart en pie_chart rendering.
    """

    async def process(self, task: str, brain: Any = None) -> SwarmPayload:
        """Verwerk categorische data naar bar_chart payload."""
        try:
            payload = await super().process(task, brain)
        except Exception as e:
            logger.debug("AlchemistAgent brain fout: %s", e)
            payload = SwarmPayload(
                agent=self.name, type="text",
                content=f"Data analyse (offline): {task[:80]}",
                display_text="Data analyse (offline modus)",
            )
        payload.type = "bar_chart"
        payload.metadata["media"] = _data_chart()
        return payload


class IolaaxAgent(BrainAgent):
    """Code specialist — detecteert code blocks."""

    async def process(self, task: str, brain: Any = None) -> SwarmPayload:
        """Verwerk codetaak en detecteer code blocks."""
        payload = await super().process(task, brain)
        code_media = _code_media(payload.content)
        if code_media:
            payload.type = "code"
            payload.metadata["media"] = code_media
        return payload


class MemexAgent(BrainAgent):
    """Agentic RAG: plan → zoek ChromaDB → synthetiseer.

    Stap 1: LLM genereert zoektermen (plan).
    Stap 2: ChromaDB doorzoeken + CorticalStack (execute).
    Stap 3: LLM schrijft rapport met bronnen.

    ChromaDB = primaire bron (ingest.py knowledge base).
    CorticalStack = secundaire bron (runtime events).
    """

    _collection = None  # Lazy ChromaDB connectie

    def _get_collection(self) -> Any:
        """Verbind met ChromaDB (zelfde DB als ingest.py)."""
        if self._collection is not None:
            return self._collection
        # ChromaDB PersistentClient + Rust backend crasht in
        # subprocess-pipe op Windows (0xC0000005). Skip in tests.
        if os.environ.get("DANNY_TEST_MODE") == "1":
            return None
        try:
            import chromadb
            from danny_toolkit.core.embeddings import (
                get_chroma_embed_fn,
            )
            from pathlib import Path
            import io as _io

            chroma_dir = str(
                Path(__file__).parent
                / "data" / "rag" / "chromadb"
            )
            client = chromadb.PersistentClient(
                path=chroma_dir
            )
            # Suppress model load spam
            _old_out = sys.stdout
            _old_err = sys.stderr
            sys.stdout = _io.StringIO()
            sys.stderr = _io.StringIO()
            try:
                embed_fn = get_chroma_embed_fn()
            finally:
                sys.stdout = _old_out
                sys.stderr = _old_err
            self._collection = (
                client.get_collection(
                    name="danny_knowledge",
                    embedding_function=embed_fn,
                )
            )
            return self._collection
        except Exception as e:
            print(
                f"  [MemexAgent] ChromaDB fout: {e}"
            )
            return None

    # Bronweging: code > docs > data
    _SOURCE_WEIGHT = {
        ".py": 0.0, ".md": 0.05, ".txt": 0.05,
        ".toml": 0.05, ".cfg": 0.05,
        ".yaml": 0.05, ".yml": 0.05,
        ".json": 0.15, ".csv": 0.15,
        ".log": 0.20,
    }

    @staticmethod
    def _bepaal_query_shards(query: str) -> list[str] | None:
        """Bepaal welke shards relevant zijn op basis van query.

        Heuristiek:
        - Code-gerelateerde termen → danny_code
        - Config/data termen → danny_data
        - Standaard → alle shards
        """
        q = query.lower()
        shards = []

        code_hints = [
            "code", "functie", "class", "def ",
            "import", "python", "javascript",
            "bug", "error", "traceback", "fix",
            "method", "function", "implementa",
        ]
        data_hints = [
            "config", "json", "csv", "yaml",
            "toml", "xml", "instelling", "setting",
            "data", "log", "logs",
        ]
        doc_hints = [
            "documentatie", "readme", "handleiding",
            "tutorial", "uitleg", "manual", "docs",
        ]

        if any(h in q for h in code_hints):
            shards.append("danny_code")
        if any(h in q for h in data_hints):
            shards.append("danny_data")
        if any(h in q for h in doc_hints):
            shards.append("danny_docs")

        # Geen match of mix → alle shards
        return shards if shards else None

    def _search_chromadb(self, query: str, n_results: int = 10) -> tuple:
        """Doorzoek ChromaDB met bronweging.

        Haalt meer resultaten op (n_results=10),
        herwaardeert scores (.py krijgt bonus,
        .json krijgt penalty), en retourneert
        de top 5.

        Phase 34: Als SHARD_ENABLED, gebruik ShardRouter.
        """
        # Phase 34: ShardRouter pad
        try:
            from danny_toolkit.core.config import Config as _Cfg
            if getattr(_Cfg, "SHARD_ENABLED", False):
                from danny_toolkit.core.shard_router import (
                    get_shard_router,
                )
                router = get_shard_router()
                shards = self._bepaal_query_shards(query)
                resultaten = router.zoek(
                    query, top_k=5, shards=shards,
                )
                if resultaten:
                    docs = [r["tekst"] for r in resultaten]
                    metas = [r["metadata"] for r in resultaten]
                    # Phase 37: track fragment access
                    try:
                        from danny_toolkit.core.self_pruning import (
                            get_self_pruning,
                        )
                        hit_ids = [
                            r["metadata"].get("id", "")
                            for r in resultaten
                            if r["metadata"].get("id")
                        ]
                        if hit_ids:
                            shard = resultaten[0].get(
                                "shard", "danny_knowledge",
                            )
                            get_self_pruning().registreer_toegang(
                                hit_ids, shard,
                            )
                    except Exception as e:
                        logger.debug(
                            "SelfPruning toegang registratie: %s", e,
                        )
                    return docs, metas
        except Exception as e:
            logger.debug("ShardRouter zoek fallback: %s", e)

        # Legacy pad
        collection = self._get_collection()
        if not collection:
            return [], []
        try:
            results = collection.query(
                query_texts=[query],
                n_results=n_results,
                include=[
                    "documents", "metadatas",
                    "distances",
                ],
            )
            docs = results["documents"][0]
            metas = results["metadatas"][0]
            dists = results["distances"][0]

            # Herweeg: lagere score = beter
            weighted = []
            for doc, meta, dist in zip(
                docs, metas, dists,
            ):
                ext = meta.get("extensie", "")
                penalty = self._SOURCE_WEIGHT.get(
                    ext, 0.10,
                )
                weighted.append(
                    (dist + penalty, doc, meta)
                )
            weighted.sort(key=lambda x: x[0])

            top = weighted[:5]
            return (
                [w[1] for w in top],
                [w[2] for w in top],
            )
        except Exception as e:
            logger.debug("Memex search failed: %s", e)
            return [], []

    def _get_cortical_stack(self) -> Any:
        """Haal CorticalStack op (lazy)."""
        try:
            from danny_toolkit.brain.cortical_stack import (
                get_cortical_stack,
            )
            return get_cortical_stack()
        except Exception as e:
            logger.debug("CorticalStack laden mislukt: %s", e)
            return None

    def _search_cortical(self, query: str) -> list:
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
        except Exception as e:
            logger.debug("Cortical event search failed: %s", e)

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
        except Exception as e:
            logger.debug("Cortical fact recall failed: %s", e)

        return results

    async def process(self, task: str, brain: Any = None) -> SwarmPayload:
        """Agentic RAG: plan zoektermen, doorzoek ChromaDB, synthetiseer rapport."""
        if not brain:
            return SwarmPayload(
                agent=self.name, type="text",
                content="Brain offline",
                display_text="Brain offline",
            )

        # Stap 1: PLAN — genereer zoektermen
        # Zuinige call: max 50 tokens (TPM-bespaarder)
        plan_prompt = (
            'JSON array: 3 zoektermen voor'
            f' "{task}"'
        )
        plan_raw, _, _ = await asyncio.to_thread(
            brain._execute_with_brain,
            plan_prompt,
            Config.LLM_FALLBACK_MODEL,
            50,
        )

        try:
            match = re.search(
                r"\[.*?\]", str(plan_raw)
            )
            if match:
                parsed = json.loads(match.group())
                queries = [
                    str(q) for q in parsed
                    if isinstance(q, str) and len(q) > 3
                ]
            else:
                queries = []
        except (json.JSONDecodeError, ValueError):
            queries = []

        # Originele vraag altijd als eerste
        queries.insert(0, task)

        # Extraheer kernentiteit uit de vraag
        # zodat "Wat doet de Governor?" ook
        # "Governor" als losse term zoekt
        stop = {
            "wat", "hoe", "wie", "waar", "welke",
            "waarom", "wanneer", "doet", "werkt",
            "is", "zijn", "de", "het", "een",
            "van", "in", "op", "met", "voor",
            "over", "uit", "aan", "er", "dit",
            "dat", "nog", "ook", "al", "kan",
            "kun", "moet", "mag", "wil", "zou",
            "leg", "vertel", "beschrijf",
        }
        kern = [
            w for w in task.split()
            if w.lower().strip("?.,!") not in stop
            and len(w) > 2
        ]
        if kern:
            queries.insert(1, " ".join(kern))

        # Stap 2: EXECUTE — doorzoek ChromaDB + Cortical
        all_fragments = []
        sources = set()

        for q in queries[:4]:
            # ChromaDB (primaire bron)
            docs, metas = await asyncio.to_thread(
                self._search_chromadb, q
            )
            for doc, meta in zip(docs, metas):
                bron = meta.get("bron", "onbekend")
                fragment = (
                    f"---\n"
                    f"FRAGMENT (Bron: {bron}):\n"
                    f"{doc}"
                )
                if fragment not in all_fragments:
                    all_fragments.append(fragment)
                    sources.add(bron)

            # CorticalStack (secundaire bron)
            cortical_docs = await asyncio.to_thread(
                self._search_cortical, q
            )
            for d in cortical_docs:
                if d not in all_fragments:
                    all_fragments.append(d)

        sources_count = len(sources)
        total_fragments = len(all_fragments)
        used_web = False

        # Stap 2B: KNOWLEDGE GAP — Navigator fallback
        if not all_fragments:
            try:
                from danny_toolkit.brain.trinity_omega import (
                    CosmicRole,
                )
                nav_prompt = (
                    "Zoek informatie over: "
                    + task
                    + "\nGeef een beknopt,"
                    " feitelijk antwoord."
                )
                nav_result, _, _ = (
                    await asyncio.to_thread(
                        brain._execute_with_role,
                        CosmicRole.NAVIGATOR,
                        nav_prompt,
                    )
                )
                if nav_result:
                    web_fragment = (
                        "---\n"
                        "FRAGMENT (Bron: Navigator"
                        " Web Search):\n"
                        + str(nav_result)
                    )
                    all_fragments.append(
                        web_fragment
                    )
                    sources.add("Navigator (Web)")
                    sources_count = len(sources)
                    total_fragments = len(
                        all_fragments
                    )
                    used_web = True
            except Exception as e:
                logger.debug("Navigator web search failed: %s", e)

        if all_fragments:
            context = "\n".join(
                all_fragments[:8]
            )
        else:
            context = (
                "Geen relevante bronnen gevonden"
                " in de database."
            )

        # Stap 3: SYNTHESIZE — rapport met bronnen
        synth_prompt = (
            "GEBRUIKERSVRAAG: " + task + "\n\n"
            "GEVONDEN KENNIS"
            + (" (incl. web)" if used_web else "")
            + ":\n"
            + context + "\n\n"
            "INSTRUCTIE:\n"
            "Beantwoord de vraag op basis"
            " van de bovenstaande kennis.\n"
            "Citeer je bronnen:\n"
            "- Documenten: [Bron: bestandsnaam]\n"
            "- Web: [Bron: Navigator]\n"
            "Als het antwoord niet in de context"
            " staat, zeg dat eerlijk."
        )
        answer, exec_time, status = (
            await asyncio.to_thread(
                brain._execute_with_role,
                self.cosmic_role, synth_prompt,
            )
        )

        raw_answer = (
            str(answer) if answer
            else "Geen antwoord gegenereerd"
        )

        # Hardcoded bronvermelding (programmatisch)
        if sources:
            sources_str = ", ".join(
                sorted(list(sources))
            )
            display = (
                f"{raw_answer}\n\n"
                f"> **Bronnen:** {sources_str}"
            )
        else:
            display = raw_answer

        return SwarmPayload(
            agent=self.name,
            type="research_report",
            content={
                "queries": queries[:3],
                "sources_count": sources_count,
                "sources_list": list(sources),
                "total_fragments": total_fragments,
                "raw_text": raw_answer,
                "used_web": used_web,
            },
            display_text=display,
            metadata={
                "execution_time": exec_time,
                "status": status,
                "queries": queries[:3],
                "sources": sources_count,
                "used_web": used_web,
            },
        )


class CoherentieAgent(Agent):
    """Hardware coherentie — geen AI nodig.

    Meet CPU/GPU correlatie en detecteert anomalieen
    zoals ongeautoriseerd GPU-gebruik (crypto-mining).
    """

    async def process(self, task: str, brain: Any = None) -> SwarmPayload:
        """Meet CPU/GPU coherentie en retourneer metrics payload."""
        try:
            from danny_toolkit.daemon.coherentie import (
                CoherentieMonitor,
            )
        except ImportError:
            logger.debug("daemon.coherentie niet beschikbaar")
            CoherentieMonitor = None
        if CoherentieMonitor is None:
            return SwarmPayload(
                agent=self.name, type="text",
                content="CoherentieMonitor niet beschikbaar",
                display_text="CoherentieMonitor niet beschikbaar",
            )
        monitor = CoherentieMonitor()
        rapport = await asyncio.to_thread(monitor.scan)

        # Metrics payload
        gpu_label = (
            "GPU (NVML)"
            if rapport["gpu_beschikbaar"]
            else "GPU (n/a)"
        )
        metrics = [
            {
                "label": "CPU Gemiddeld",
                "value": f"{rapport['cpu_gem']:.1f}%",
                "delta": "",
            },
            {
                "label": gpu_label,
                "value": f"{rapport['gpu_gem']:.1f}%",
                "delta": "",
            },
            {
                "label": "Correlatie",
                "value": f"{rapport['correlatie']:.4f}",
                "delta": "",
            },
            {
                "label": "Verdict",
                "value": rapport["verdict"],
                "delta": rapport["details"][:60],
                "delta_color": (
                    "normal"
                    if rapport["verdict"] == "PASS"
                    else "inverse"
                ),
            },
        ]

        # Chart data: CPU vs GPU reeksen
        _ensure_np_pd()
        chart_data = pd.DataFrame({
            "CPU %": rapport["cpu_reeks"],
            "GPU %": rapport["gpu_reeks"],
        })

        display = (
            f"**Coherentie Scan**\n"
            f"CPU gem: {rapport['cpu_gem']:.1f}% | "
            f"GPU gem: {rapport['gpu_gem']:.1f}%\n"
            f"Correlatie: {rapport['correlatie']:.4f}\n"
            f"**{rapport['verdict']}:** "
            f"{rapport['details']}"
        )

        return SwarmPayload(
            agent=self.name,
            type="metrics",
            content=display,
            display_text=display,
            metadata={
                "execution_time": (
                    rapport["duur_seconden"]
                ),
                "status": rapport["verdict"],
                "media": {
                    "type": "metrics",
                    "category": "HARDWARE",
                    "metrics": metrics,
                    "data": chart_data.to_dict(
                        orient="records"
                    ),
                },
            },
        )


class StrategistAgent(Agent):
    """Recursive planner: decompose, delegate, chain."""

    def _get_strategist(self) -> Any:
        """Lazy-load Strategist instantie."""
        if not hasattr(self, "_strategist"):
            try:
                from danny_toolkit.brain.strategist import (
                    Strategist,
                )
                self._strategist = Strategist()
            except Exception as e:
                logger.debug("Strategist laden mislukt: %s", e)
                self._strategist = None
        return self._strategist

    async def process(self, task: str, brain: Any = None) -> SwarmPayload:
        """Decomponeer en delegeer taak via Strategist."""
        start_t = time.time()
        strat = self._get_strategist()
        if strat is None:
            return SwarmPayload(
                agent=self.name, type="text",
                content="Strategist niet beschikbaar",
                display_text="Strategist niet beschikbaar",
            )
        result = await strat.execute_mission(task)
        elapsed = time.time() - start_t
        return SwarmPayload(
            agent=self.name,
            type="text",
            content=result,
            display_text=result,
            metadata={"execution_time": elapsed},
        )


class ArtificerAgent(Agent):
    """AST-Safe Code Engine — geïsoleerde code generator.

    Creëert modulaire, sandbox-ready Python scripts.
    Output is altijd AST-parsable, PEP-8 compliant code
    met type hints en Google-style docstrings.
    """

    def _get_artificer(self) -> Any:
        """Lazy-load Artificer instantie."""
        if not hasattr(self, "_artificer"):
            try:
                from danny_toolkit.brain.artificer import (
                    Artificer,
                )
                self._artificer = Artificer()
            except Exception as e:
                logger.debug("Artificer laden mislukt: %s", e)
                self._artificer = None
        return self._artificer

    async def process(self, task: str, brain: Any = None) -> SwarmPayload:
        """Forge en executeer skill via Artificer."""
        start_t = time.time()
        art = self._get_artificer()
        if art is None:
            return SwarmPayload(
                agent=self.name, type="text",
                content="Artificer niet beschikbaar",
                display_text="Artificer niet beschikbaar",
            )
        result = await art.execute_task(task)
        elapsed = time.time() - start_t

        # Detect code blocks in output
        media = _code_media(result)
        p_type = "code" if media else "text"
        meta = {"execution_time": elapsed}
        if media:
            meta["media"] = media

        return SwarmPayload(
            agent=self.name,
            type=p_type,
            content=result,
            display_text=result,
            metadata=meta,
        )


class VirtualTwinAgent(Agent):
    """Virtuele Tweeling: sandboxed system duplicate with Mirror + VoidWalker."""

    def _get_twin(self) -> Any:
        """Lazy-load VirtualTwin instantie."""
        if not hasattr(self, "_twin"):
            try:
                from danny_toolkit.brain.virtual_twin import (
                    VirtualTwin,
                )
                self._twin = VirtualTwin()
            except Exception as e:
                logger.debug("VirtualTwin laden mislukt: %s", e)
                self._twin = None
        return self._twin

    async def process(self, task: str, brain: Any = None) -> SwarmPayload:
        """Consulteer VirtualTwin voor diepte-analyse."""
        start_t = time.time()
        twin = self._get_twin()
        if twin is None:
            return SwarmPayload(
                agent=self.name, type="text",
                content="VirtualTwin niet beschikbaar",
                display_text="VirtualTwin niet beschikbaar",
            )
        result = await twin.consult(task, commander_override=True)
        elapsed = time.time() - start_t
        return SwarmPayload(
            agent=self.name,
            type="text",
            content=result or "",
            display_text=result or "",
            metadata={"execution_time": elapsed},
        )


class PixelAgent(Agent):
    """THE EYES: Multimodal Vision Agent.

    Gebruikt PixelEye skill voor vision analyse.
    Closed Loop: Legion doet → Pixel kijkt →
    Brain oordeelt → Legion corrigeert.
    """

    VISION_TRIGGERS = [
        "kijk", "zie", "screenshot", "check",
        "bekijk", "toon scherm", "wat zie",
    ]

    def __init__(self, name: str, role: str, model: str | None = None) -> None:
        """Initialiseer PixelAgent met PixelEye skill."""
        super().__init__(name, role, model)
        try:
            from danny_toolkit.skills.pixel_eye import (
                PixelEye,
            )
        except ImportError:
            logger.debug("skills.pixel_eye niet beschikbaar")
            PixelEye = None
        self.eye = PixelEye() if PixelEye is not None else None

    async def process(self, task: str, brain: Any = None) -> SwarmPayload:
        """Verwerk visuele taak via PixelEye of tekst-fallback."""
        start_t = time.time()

        # Detecteer of dit een visuele taak is
        lower = task.lower()
        is_vision = any(
            t in lower for t in self.VISION_TRIGGERS
        )

        if not is_vision or not brain:
            # Normale Pixel taak (tekst-based)
            if not brain:
                return SwarmPayload(
                    agent=self.name, type="text",
                    content="Brain offline",
                    display_text="Brain offline",
                )
            try:
                from danny_toolkit.brain.trinity_omega import (
                    CosmicRole,
                )
            except ImportError:
                logger.debug("brain.trinity_omega niet beschikbaar")
                return SwarmPayload(
                    agent=self.name, type="text",
                    content="CosmicRole niet beschikbaar",
                    display_text="CosmicRole niet beschikbaar",
                )
            result, exec_time, status = (
                await asyncio.to_thread(
                    brain._execute_with_role,
                    CosmicRole.PIXEL, task,
                )
            )
            content = (
                str(result) if result
                else "Pixel: geen resultaat"
            )
            return SwarmPayload(
                agent=self.name, type="text",
                content=content,
                display_text=content,
                metadata={
                    "execution_time": exec_time,
                    "status": status,
                },
            )

        # Vision: screenshot + LLaVA via PixelEye
        result = await asyncio.to_thread(
            self.eye.analyze_screen, task
        )

        analysis = result.get("analyse")
        img_path = result.get("pad")

        if analysis:
            vision_status = (
                f"Real Vision ({self.eye.model})"
            )
        else:
            # Fallback: Brain tekst-analyse
            vision_status = "LLaVA fallback"
            try:
                from danny_toolkit.brain.trinity_omega import (
                    CosmicRole,
                )
                fallback_prompt = (
                    "Jij bent PIXEL, de visuele"
                    " analist. Er is een screenshot"
                    f" gemaakt: {img_path}.\n"
                    f"De gebruiker vraagt:"
                    f" \"{task}\"\n"
                    "Beschrijf wat je verwacht"
                    " te zien en geef feedback."
                )
                fb_result, _, _ = (
                    await asyncio.to_thread(
                        brain._execute_with_role,
                        CosmicRole.PIXEL,
                        fallback_prompt,
                    )
                )
                analysis = (
                    str(fb_result) if fb_result
                    else None
                )
                vision_status = "Brain fallback"
            except Exception as e:
                logger.debug("Vision fallback failed: %s", e)

        display = (
            f"**Visuele Analyse:**\n{analysis}"
            if analysis
            else "Pixel: geen analyse mogelijk"
        )
        elapsed = time.time() - start_t

        return SwarmPayload(
            agent=self.name,
            type="image_analysis",
            content={"image_path": img_path},
            display_text=display,
            metadata={
                "execution_time": elapsed,
                "status": vision_status,
                "image_path": img_path,
            },
        )


class LegionAgent(Agent):
    """INFRASTRUCTURE AGENT: Bestuurt het OS.

    Vertaalt Natural Language naar Kinesis-acties
    via een LLM plan-stap, dan fysieke executie.

    Action Tiers:
    - VEILIG: type, press, wait, screenshot
    - GEVAARLIJK: open, combo (vereist bevestiging)
    """

    _VEILIGE_ACTIES = {"type", "press", "wait",
                       "screenshot"}
    _GEVAARLIJKE_ACTIES = {"open", "combo"}

    def __init__(self, name: str, role: str, model: str | None = None) -> None:
        """Initialiseer LegionAgent met KineticUnit body."""
        super().__init__(name, role, model)
        try:
            from kinesis import KineticUnit
        except ImportError:
            logger.debug("kinesis niet beschikbaar")
            KineticUnit = None
        self.body = KineticUnit() if KineticUnit is not None else None
        self.bevestig_callback = None

    @staticmethod
    def _is_veilig(step: dict) -> bool:
        """Classificeer een actie als veilig/gevaarlijk.

        Args:
            step: Actie dict met "action" key.

        Returns:
            True als de actie veilig is.
        """
        act = step.get("action", "")
        return act in LegionAgent._VEILIGE_ACTIES

    async def process(self, task: str, brain: Any = None) -> SwarmPayload:
        """Vertaal intentie naar OS-acties en voer ze uit."""
        start_t = time.time()

        if not brain:
            return SwarmPayload(
                agent=self.name, type="text",
                content="Brain offline",
                display_text="Brain offline",
            )

        # 1. PLAN: Vertaal intentie naar acties
        try:
            from danny_toolkit.brain.trinity_omega import (
                CosmicRole,
            )
        except ImportError:
            logger.debug("brain.trinity_omega niet beschikbaar")
            return SwarmPayload(
                agent=self.name, type="text",
                content="CosmicRole niet beschikbaar",
                display_text="CosmicRole niet beschikbaar",
            )
        plan_prompt = (
            "Jij bent LEGION, de systeem-operator."
            f' De gebruiker wil: "{task}"\n\n'
            "Zet dit om naar een JSON lijst van"
            " acties. Mogelijke acties:\n"
            '- {"action": "open",'
            ' "target": "app_naam"}\n'
            '- {"action": "type",'
            ' "text": "tekst"}\n'
            '- {"action": "press",'
            ' "key": "enter"}\n'
            '- {"action": "combo",'
            ' "keys": ["ctrl", "c"]}\n'
            '- {"action": "wait",'
            ' "seconds": 2}\n\n'
            "GEEF ALLEEN DE JSON."
        )

        raw_plan, _, _ = await asyncio.to_thread(
            brain._execute_with_role,
            CosmicRole.LEGION, plan_prompt,
        )

        execution_log = []

        try:
            # Parse JSON (strip markdown fencing)
            clean_json = (
                str(raw_plan)
                .replace("```json", "")
                .replace("```", "")
                .strip()
            )
            # Zoek de JSON array
            match = re.search(
                r"\[.*\]", clean_json, re.DOTALL
            )
            if match:
                steps = json.loads(match.group())
            else:
                steps = json.loads(clean_json)

            # 2. EXECUTE: Voer stappen fysiek uit
            for step in steps:
                act = step.get("action")

                # Action Tier check
                if not self._is_veilig(step):
                    if not self.bevestig_callback:
                        execution_log.append(
                            f"GEBLOKKEERD: '{act}'"
                            " is gevaarlijk en "
                            "vereist bevestiging"
                        )
                        continue
                    if not self.bevestig_callback(
                        step
                    ):
                        execution_log.append(
                            f"GEWEIGERD: '{act}'"
                            " door gebruiker"
                        )
                        continue

                if act == "open":
                    res = self.body.launch_app(
                        step["target"]
                    )
                elif act == "type":
                    res = self.body.type_text(
                        step["text"]
                    )
                elif act == "press":
                    res = self.body.press_key(
                        step["key"]
                    )
                elif act == "combo":
                    res = self.body.hotkey(
                        *step["keys"]
                    )
                elif act == "wait":
                    time.sleep(
                        step.get("seconds", 1)
                    )
                    res = "Waited"
                elif act == "screenshot":
                    res = self.body.take_screenshot()
                else:
                    res = f"Onbekende actie: {act}"

                execution_log.append(
                    f"{act}: {res}"
                )

        except Exception as e:
            execution_log.append(
                f"Fout bij uitvoeren plan: {e}"
            )
            execution_log.append(
                f"Raw plan: {raw_plan}"
            )

        result_text = "\n".join(execution_log)
        elapsed = time.time() - start_t

        return SwarmPayload(
            agent=self.name,
            type="text",
            content=(
                steps
                if "steps" in dir()
                else str(raw_plan)
            ),
            display_text=(
                "**Systeem Automatisering"
                " Voltooid:**\n\n"
                + result_text
            ),
            metadata={
                "execution_time": elapsed,
            },
        )


# ── SENTINEL VALIDATOR ──

class SentinelValidator:
    """Deterministische output validatie (geen LLM).

    Controleert agent output op:
    - Gevaarlijke code patronen
    - PII lekkage
    - Lengte limieten
    """

    MAX_OUTPUT_LENGTH = 10000

    _GEVAARLIJKE_PATRONEN = [
        r"\bos\.system\s*\(",
        r"\bexec\s*\(",
        r"\beval\s*\(",
        r"\brm\s+-rf\b",
        r"\bsubprocess\.(?:call|run|Popen)\s*\("
        r".*shell\s*=\s*True",
        r"\b__import__\s*\(",
        r"\bopen\s*\(.*['\"]w['\"]\s*\)",
        r"\bshutil\.rmtree\s*\(",
    ]

    def __init__(self, governor: Any = None) -> None:
        """Initialiseer SentinelValidator met optionele Governor."""
        self._governor = governor
        self._compiled = [
            re.compile(p, re.IGNORECASE)
            for p in self._GEVAARLIJKE_PATRONEN
        ]

    def valideer(
        self, payload: SwarmPayload,
    ) -> dict[str, object]:
        """Valideer een SwarmPayload.

        Args:
            payload: SwarmPayload om te checken.

        Returns:
            Dict met veilig (bool), waarschuwingen
            (list), geschoond (str|None).
        """
        waarschuwingen = []
        content = str(payload.content)
        display = str(payload.display_text)

        # 1. Lengte check
        if len(content) > self.MAX_OUTPUT_LENGTH:
            content = content[:self.MAX_OUTPUT_LENGTH]
            waarschuwingen.append(
                f"Output afgekapt op "
                f"{self.MAX_OUTPUT_LENGTH} tekens"
            )

        # 2. Gevaarlijke code detectie
        for patroon in self._compiled:
            if patroon.search(content):
                waarschuwingen.append(
                    f"Gevaarlijke code: "
                    f"{patroon.pattern[:40]}"
                )
            if patroon.search(display):
                waarschuwingen.append(
                    f"Gevaarlijke code in display: "
                    f"{patroon.pattern[:40]}"
                )

        # 3. PII scrubbing via Governor
        geschoond = display
        if self._governor:
            geschoond = self._governor.scrub_pii(
                display
            )

        veilig = len(waarschuwingen) == 0
        return {
            "veilig": veilig,
            "waarschuwingen": waarschuwingen,
            "geschoond": geschoond,
        }


# ── ADAPTIVE ROUTER ──

class AdaptiveRouter:
    """Embedding-based semantic routing.

    Vervangt keyword matching door cosine similarity
    met agent profiel-embeddings. Fallback naar
    ROUTE_MAP als embeddings niet beschikbaar.
    """

    DREMPEL = 0.30
    MAX_AGENTS = 3
    _BLOK = 100       # Intentie-blok grootte
    _MAX_BLOKKEN = 5  # Absoluut max = 500 chars
    _embed_fn = None
    _profiel_embeddings = None

    # Multi-Vector Profielen V6.0
    # Complexe agents (IOLAAX, MEMEX) zijn gesplitst
    # in sub-profielen. route() pakt max(sim) over
    # alle sub-vectoren per agent.
    AGENT_PROFIELEN = {
        "IOLAAX": [
            # De Bouwer — code generatie
            (
                "programming coding software python"
                " javascript code implement develop"
                " schrijven script build create"
                " function class module algorithm"
                " syntax terminal console"
            ),
            # De Monteur — debugging
            (
                "debugging fix error crash python"
                " code exception traceback bug"
                " foutmelding repareren kapot werkt"
                " niet stacktrace log issue resolve"
                " failure debuggen crasht fout"
                " oplossen script"
            ),
            # De Expert — refactoring & git
            (
                "git version control refactoring"
                " python code clean optimization"
                " performance architecture design"
                " pattern best practices review"
                " compiling build"
            ),
        ],
        "CIPHER": [
            (
                "cryptocurrency bitcoin ethereum"
                " blockchain wallet crypto trading"
                " price market koers prijs minen"
                " smart contracts tokens encryptie"
                " decryptie portfolio saldo winst"
            ),
        ],
        "VITA": [
            (
                "gezondheid health slaap sleep stress"
                " biohacking hartslag heart rate HRV"
                " voeding nutrition wellness biometrie"
                " sport medicijn DNA peptiden analyse"
                " diagnosis fitness moe vermoeidheid"
                " energie futloos ziek pijn herstel"
                " voel me slecht conditie"
            ),
        ],
        "NAVIGATOR": [
            (
                "web search internet online lookup"
                " fetch scrape API research explore"
                " discover browse zoeken onderzoek"
                " vind informatie bronnen"
            ),
        ],
        "ORACLE": [
            (
                "philosophy thinking logic reasoning"
                " consciousness ethics hypothesis"
                " deep meaning purpose"
                " zin van het bestaan waarom"
                " leven we filosofie nadenken"
                " ethiek moraal existentieel"
                " vraagstuk analyse"
            ),
        ],
        "SPARK": [
            (
                "creative ideas brainstorm art ASCII"
                " design innovation drawing"
                " visualization kunst creatief idee"
                " ontwerp concept verzin iets"
            ),
        ],
        "SENTINEL": [
            (
                "security firewall audit threats"
                " protect vulnerability defense"
                " beveiligen beveiliging wachtwoord"
                " privacy hack aanval risico"
            ),
        ],
        "MEMEX": [
            # Het Archief — geheugen & recall
            (
                "database memory recall remember"
                " retrieve archive history knowledge"
                " base geheugen opslag herinner"
                " zoek in bestanden long term"
            ),
            # RAG Context — document search
            (
                "RAG vector search document lookup"
                " source bronvermelding reference"
                " opzoeken context ophalen"
                " collectie bronnen"
            ),
        ],
        "ALCHEMIST": [
            (
                "data transform convert ETL pipeline"
                " cleaning processing analysis"
                " transformeren converteren verwerken"
                " csv json format"
            ),
        ],
        "VOID": [
            (
                "verwijder bestanden delete files"
                " tijdelijke bestanden temporary"
                " opruimen clean up schoonmaken"
                " cache garbage prullenbak trash"
                " recycle bin junk logs wissen"
                " disk space ruimte vrijmaken"
                " remove cleanup"
            ),
        ],
        "CHRONOS_AGENT": [
            (
                "planning schedule agenda deadline"
                " timer cronjob reminder day rhythm"
                " bio rhythm calendar time planning"
                " schema herinnering klok tijd laat"
                " datum wanneer agenda afspraak"
            ),
        ],
        "PIXEL": [
            (
                "user interface dashboard menu screen"
                " display emotion feeling"
                " visualization help assistance"
                " UI scherm ziet eruit plaatje"
            ),
        ],
        "COHERENTIE": [
            (
                "hardware coherentie cpu gpu load"
                " correlatie mining crypto validatie"
                " fingerprint check belasting"
                " processor grafische kaart gebruik"
                " anomalie detectie monitor"
            ),
        ],
        "STRATEGIST": [
            (
                "plan mission strategy objective goal"
                " decompose workflow pipeline steps"
                " missie strategie doel opdracht"
                " uitvoeren plannen orchestreer"
                " uitwerken stappenplan"
            ),
        ],
        "ARTIFICER": [
            (
                "forge tool build script create utility"
                " generate program automate tool maker"
                " smeden bouwen genereer maak een tool"
                " schrijf een script automatiseer"
                " skill forge nieuw programma"
            ),
        ],
        "VIRTUAL_TWIN": [
            (
                "deep analysis research twin mirror"
                " system analysis profile analyse"
                " diepte onderzoek tweeling spiegel"
                " achtergrond context verrijking"
                " kennisverrijking systeem overzicht"
            ),
        ],
    }

    @classmethod
    def _get_embed_fn(cls) -> Any:
        """Lazy laden van SentenceTransformer op CPU.

        CPU-only: router embed korte strings, geen GPU nodig.
        Voorkomt CUDA ACCESS_VIOLATION (0xC0000005) op Windows.
        """
        if cls._embed_fn is not None:
            return cls._embed_fn
        try:
            import io as _io
            from sentence_transformers import (
                SentenceTransformer,
            )
            _old_out = sys.stdout
            _old_err = sys.stderr
            sys.stdout = _io.StringIO()
            sys.stderr = _io.StringIO()
            try:
                model = SentenceTransformer(
                    "sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
                    device="cpu",
                )
            finally:
                sys.stdout = _old_out
                sys.stderr = _old_err
            cls._embed_fn = model.encode
            return cls._embed_fn
        except Exception as e:
            logger.debug("SentenceTransformer laden mislukt: %s", e)
            return None

    @classmethod
    def _bereken_profielen(cls) -> dict | None:
        """Embed alle agent sub-profielen (eenmalig).

        Slaat per agent een lijst van vectoren op.
        route() pakt max(sim) over alle sub-vectoren.
        """
        if cls._profiel_embeddings is not None:
            return cls._profiel_embeddings
        embed = cls._get_embed_fn()
        if not embed:
            return None
        cls._profiel_embeddings = {}
        for agent, subs in cls.AGENT_PROFIELEN.items():
            cls._profiel_embeddings[agent] = [
                embed(tekst) for tekst in subs
            ]
        return cls._profiel_embeddings

    @staticmethod
    def _cosine_sim(vec_a: Any, vec_b: Any) -> float:
        """Cosine similarity tussen twee vectoren."""
        dot = sum(
            a * b for a, b in zip(vec_a, vec_b)
        )
        mag_a = math.sqrt(
            sum(a ** 2 for a in vec_a)
        )
        mag_b = math.sqrt(
            sum(b ** 2 for b in vec_b)
        )
        if mag_a == 0 or mag_b == 0:
            return 0.0
        return dot / (mag_a * mag_b)

    def route(
        self,
        user_input: str,
        synapse_bias: dict[str, float] | None = None,
        exclude_agents: set[str] | None = None,
    ) -> list[str]:
        """Semantische routing via cosine similarity.

        Args:
            user_input: Tekst van de gebruiker.
            synapse_bias: Optionele bias multipliers
                per agent van TheSynapse.
            exclude_agents: Agents om uit te sluiten
                (bv. in cooldown).

        Returns:
            Lijst van agent keys, gesorteerd op
            relevantie. Fallback naar ["ECHO"].
        """
        embed = self._get_embed_fn()
        if not embed:
            raise RuntimeError(
                "Embedding niet beschikbaar"
            )

        profielen = self._bereken_profielen()
        if not profielen:
            raise RuntimeError(
                "Profielen niet beschikbaar"
            )

        # Dynamische input-afkapping:
        # Blok 0 (0-100): altijd — bevat intentie
        # Blok 1-4: alleen als nieuw woord begint
        # Max 500 chars (CPU DoS preventie)
        length = len(user_input)
        if length > self._BLOK:
            eind = self._BLOK
            for i in range(1, self._MAX_BLOKKEN):
                grens = self._BLOK * (i + 1)
                if length <= grens:
                    eind = length
                    break
                # Stop bij blokgrens als daar een
                # spatie/punt is (zinseinde = klaar)
                ch = user_input[grens - 1]
                if ch in ".!?\n":
                    eind = grens
                    break
                eind = grens
            user_input = user_input[:eind]

        input_vec = embed(user_input)

        scores = []
        for agent, sub_vecs in profielen.items():
            # max(sim) over alle sub-profielen
            best = max(
                self._cosine_sim(input_vec, sv)
                for sv in sub_vecs
            )
            # Apply Synapse bias multiplier
            if synapse_bias and agent in synapse_bias:
                best *= synapse_bias[agent]
            if best >= self.DREMPEL:
                scores.append((agent, best))

        scores.sort(key=lambda x: x[1], reverse=True)
        targets = [
            s[0] for s in scores[:self.MAX_AGENTS]
        ]

        # Filter throttled agents
        if exclude_agents:
            targets = [
                t for t in targets
                if t not in exclude_agents
            ]

        # Bij overlap: hoogste score wint
        if "MEMEX" in targets and "IOLAAX" in targets:
            score_map = dict(scores)
            if score_map["MEMEX"] > score_map["IOLAAX"]:
                targets.remove("IOLAAX")
            else:
                targets.remove("MEMEX")

        return targets or ["ECHO"]


# ── PIPELINE TUNER ──

class PipelineTuner:
    """Meet en optimaliseert pipeline stappen.

    Houdt rolling stats bij en schakelt stappen
    uit die consistent niks bijdragen.
    """

    VENSTER = 20
    MEMEX_SKIP_NA = 10
    SENTINEL_SAMPLE_NA = 20
    SENTINEL_SAMPLE_RATE = 5

    def __init__(self) -> None:
        """Initialiseer PipelineTuner met lege stats."""
        self._stats: dict = {}
        self._call_count: dict = {}

    def _ensure_stap(self, stap: str) -> None:
        """Maak stats aan voor een stap."""
        if stap not in self._stats:
            self._stats[stap] = deque(
                maxlen=self.VENSTER
            )
            self._call_count[stap] = 0

    def registreer(self, stap: str, latency_ms: float, **metrics: Any) -> None:
        """Voeg meting toe aan rolling buffer.

        Args:
            stap: Naam van de pipeline stap.
            latency_ms: Latency in milliseconden.
            **metrics: Extra metrieken (bijv.
                fragmenten, waarschuwingen).
        """
        self._ensure_stap(stap)
        entry = {"latency_ms": latency_ms}
        entry.update(metrics)
        self._stats[stap].append(entry)
        self._call_count[stap] += 1

    def mag_skippen(self, stap: str) -> bool:
        """Check of stap overgeslagen mag worden.

        Args:
            stap: Naam van de pipeline stap.

        Returns:
            True als de stap overgeslagen mag worden.
        """
        # Security-critical: NOOIT skippen
        if stap in (
            "governor", "fast_track", "chronos",
            "route", "execute",
        ):
            return False

        self._ensure_stap(stap)
        entries = self._stats[stap]
        count = self._call_count[stap]

        if stap == "memex":
            if count < self.MEMEX_SKIP_NA:
                return False
            recent = list(entries)[
                -self.MEMEX_SKIP_NA:
            ]
            return all(
                e.get("fragmenten", 1) == 0
                for e in recent
            )

        if stap == "sentinel":
            if count < self.SENTINEL_SAMPLE_NA:
                return False
            recent = list(entries)[
                -self.SENTINEL_SAMPLE_NA:
            ]
            alle_schoon = all(
                e.get("waarschuwingen", 1) == 0
                for e in recent
            )
            if not alle_schoon:
                return False
            # Sample: skip als NIET de Mde call
            return (
                count % self.SENTINEL_SAMPLE_RATE != 0
            )

        return False

    def get_samenvatting(self) -> str:
        """Genereer pipeline timing samenvatting.

        Returns:
            String zoals "Gov:5ms MEMEX:skip
            Route:2ms Exec:950ms Sent:30ms".
        """
        labels = {
            "governor": "Gov",
            "fast_track": "Fast",
            "chronos": "Chrn",
            "memex": "MEMEX",
            "route": "Route",
            "execute": "Exec",
            "sentinel": "Sent",
        }
        parts = []
        for stap, label in labels.items():
            entries = self._stats.get(stap)
            if not entries:
                if self.mag_skippen(stap):
                    parts.append(f"{label}:skip")
                continue
            laatste = entries[-1]
            ms = laatste.get("latency_ms", 0)
            parts.append(f"{label}:{ms:.0f}ms")
        return " ".join(parts)

    def reset(self) -> None:
        """Reset alle stats."""
        self._stats.clear()
        self._call_count.clear()


# ── FAST-TRACK ──

_GREETING_PATTERNS = [
    r"^hallo\b", r"^hoi\b", r"^hey\b", r"^hi\b",
    r"^goede(morgen|middag|avond)\b", r"^yo\b",
    r"^hoe gaat het", r"^bedankt", r"^dank je",
    r"^doei\b", r"^tot ziens",
    r"^dag\b", r"^welterusten\b", r"^goedenacht\b",
    r"^dankjewel\b", r"^thanks\b", r"^top\b",
    r"^oke\b", r"^oké\b", r"^prima\b",
]


def _fast_track_check(prompt: str) -> SwarmPayload | None:
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
            "javascript", "schrijf", "algoritme",
            "implementeer", "bug", "error", "fout",
            "module", "import",
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
            "zoek op", "web search", "fetch", "scrape",
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
        "MEMEX": [
            "zoek kennis", "herinner", "rag",
            "vector", "semantic", "geheugen",
            "knowledge", "zoek in", "archief",
            "wat weten we over", "recall",
            "opzoeken", "doorzoek",
            # Kennisgerichte vragen → RAG
            "wat doet", "wat is", "hoe werkt",
            "leg uit", "vertel over", "beschrijf",
            "uitleg", "waarvoor", "wie is",
            "wat betekent", "doel van", "rol van",
            "informatie over", "meer over",
            "welke", "hoeveel", "waar zit",
            "waar staat", "wanneer",
        ],
        "ALCHEMIST": [
            "convert", "transform", "data_clean",
            "etl",
        ],
        "VOID": [
            "cleanup", "clean", "delete", "opruim",
            "cache", "garbage",
        ],
        # LEGION: disabled

        "COHERENTIE": [
            "coherentie", "hardware", "gpu check",
            "cpu check", "validatie", "fingerprint",
            "mining", "load",
        ],
        "CHRONOS_AGENT": [
            "schedule", "cronjob", "timer",
            "dag ritme", "bio ritme",
            "planning", "agenda", "deadline",
            "wanneer", "herinnering",
        ],
        "PIXEL": [
            "help", "uitleg", "interface", "praat",
            "emotie", "gevoel", "dashboard", "menu",
            "teken", "visualiseer", "kijk", "zie",
            "bekijk", "check scherm", "wat zie",
        ],
        "STRATEGIST": [
            "missie", "mission", "plan een", "strategie",
            "strategy", "stappenplan", "orchestreer",
            "decompose", "workflow", "doel bereiken",
        ],
        "ARTIFICER": [
            "forge", "smeed", "maak een tool",
            "bouw een tool", "skill", "genereer script",
            "utility", "maak een script",
        ],
        "VIRTUAL_TWIN": [
            "twin", "tweeling", "mirror analyse",
            "diepte analyse", "systeem analyse",
            "profiel analyse", "deep analysis",
        ],
    }

    def __init__(self, brain: Any = None, oracle: Any = None) -> None:
        """Initialiseer SwarmEngine met brain en optionele oracle."""
        self.brain = brain
        self._oracle = oracle
        self.repair_mode = True
        self.agents = self._register_agents()
        self._router = AdaptiveRouter()
        self._tuner = PipelineTuner()
        self.on_pre_task = []
        self.on_post_task = []
        self.on_failure = []
        self._query_count = 0
        self._total_time = 0.0
        self._swarm_metrics = {
            "fast_track_hits": 0,
            "governor_blocks": 0,
            "echo_guard_blocks": 0,
            "triples_extracted": 0,
            "tribunal_verified": 0,
            "tribunal_warnings": 0,
            "tribunal_errors": 0,
            "synapse_adjustments": 0,
            "synapse_reinforcements": 0,
            "phantom_predictions": 0,
            "phantom_hits": 0,
            "agent_errors": 0,
            "twin_consultations": 0,
            "schild_blocks": 0,
            "circuit_breaker_trips": 0,
            "agent_timeouts": 0,
            "summary_hits": 0,
            "sentinel_warnings": 0,
            "semantic_cache_hits": 0,
            "semantic_cache_misses": 0,
            "error_retries_attempted": 0,
            "error_retries_succeeded": 0,
            "cortex_enrichments": 0,
            "ouroboros_heals": 0,
            "ouroboros_attempts": 0,
        }

        # Phase 56: Forge Loader — dynamically loaded tools
        self._forged_tools: Dict[str, Any] = {}
        self._forged_schemas: list = []

        # Cached ShadowCortex instance (lazy init)
        self._shadow_cortex = None

        # Cached TheCortex instance (lazy init, Phase 38)
        self._cortex = None

        # Semantic Cache (lazy init)
        self._semantic_cache = None

        # Echo Guard — dedup gate (hash, timestamp)
        self._recent_queries: deque = deque(maxlen=50)

    def validate_execution(self, active_brain: object) -> None:
        """Valideer dat het commando van de echte Sovereign Core komt.

        Raises:
            PermissionError: Als het brain-object geen geldig
                Sovereign Seal heeft.
        """
        import os

        # Test mode bypass voor geïsoleerde unit tests
        if os.getenv("DANNY_TEST_MODE") == "1":
            return

        # Geen brain = standalone modus (toegestaan)
        if active_brain is None:
            return

        # Fail-Closed: als de kluis onvindbaar is,
        # blokkeren we alles. Geen uitzonderingen.
        try:
            from danny_toolkit.core.sovereign_seal import (
                get_sovereign_seal,
            )
            seal_verifier = get_sovereign_seal()
        except ImportError as e:
            raise PermissionError(
                "[FATAL LOCKDOWN] SovereignSeal module "
                "gesaboteerd of onvindbaar: "
                f"{e}. Systeem gaat in absolute lockdown."
            )

        # Heeft het brein überhaupt een seal?
        seal = getattr(active_brain, "sovereign_seal", None)
        if not seal:
            raise PermissionError(
                "[FATAL LOCKDOWN] Ongeautoriseerd object "
                "probeert de Swarm te commanderen."
            )

        # Is het seal authentiek?
        if not seal_verifier.verify(seal):
            raise PermissionError(
                "[FATAL LOCKDOWN] Sovereign Seal verificatie "
                "gefaald. Rogue proces gedetecteerd."
            )

    def get_stats(self) -> Dict[str, Any]:
        """Statistieken: verwerkte queries, agents, gem. responstijd."""
        avg_ms = (
            self._total_time / self._query_count
            if self._query_count > 0
            else 0.0
        )
        stats = {
            "queries_processed": self._query_count,
            "active_agents": len(self.agents),
            "avg_response_ms": round(avg_ms, 1),
            "registered_agents": list(
                self.agents.keys()
            ),
            **self._swarm_metrics,
        }

        # Per-agent pipeline metrics
        stats["agent_metrics"] = get_pipeline_metrics()

        # Response cache stats
        try:
            from danny_toolkit.core.response_cache import (
                get_response_cache,
            )
            stats["response_cache"] = get_response_cache().stats()
        except ImportError:
            stats["response_cache"] = {}

        # Semantic cache stats
        try:
            from danny_toolkit.core.semantic_cache import get_semantic_cache
            stats["semantic_cache"] = get_semantic_cache().stats()
        except ImportError:
            stats["semantic_cache"] = {}

        # Key manager status
        try:
            from danny_toolkit.core.key_manager import (
                get_key_manager,
            )
            stats["key_manager"] = get_key_manager().get_status()
        except ImportError:
            stats["key_manager"] = {}

        return stats

    def _record_response_outcome(self, query: str, results: list) -> None:
        """B-95: Log response quality metrics to CorticalStack (non-blocking).

        Extracts payload data on the hot path (~0.01ms), then fires the
        SQLite write to a background daemon thread via ThreadPoolExecutor.
        Main thread never waits for DB confirmation.

        Used by PrometheusBrain.efficiency_reflection() to compute B-95 score.
        """
        if not HAS_CORTICAL:
            return
        # Phase 100: Extract data on hot path (pure Python, no I/O)
        error_count = sum(1 for r in results if r.type == "error")
        agents_used = [r.agent for r in results]
        total_ms = sum(
            r.metadata.get("execution_time", 0) for r in results
        ) * 1000
        details = {
            "query_preview": query[:120],
            "success": error_count == 0 and len(results) > 0,
            "error_count": error_count,
            "agents": agents_used,
            "latency_ms": round(total_ms, 1),
            "schild_blocks": self._swarm_metrics.get("schild_blocks", 0),
            "sentinel_warnings": self._swarm_metrics.get("sentinel_warnings", 0),
        }

        # Fire-and-forget to background thread (daemon=True via executor)
        def _write_outcome() -> None:
            """Schrijf B-95 outcome naar CorticalStack in achtergrond."""
            try:
                stack = get_cortical_stack()
                stack.log_event(
                    actor="swarm_engine",
                    action="response_outcome",
                    details=details,
                    source="b95_feedback",
                )
            except Exception as e:
                logger.debug("B-95 outcome recording failed: %s", e)

        try:
            _B95_EXECUTOR.submit(_write_outcome)
        except RuntimeError:
            # Executor shut down (interpreter exit)
            logger.debug("B-95 executor shut down, skipping outcome write")

    def _record_agent_metric(self, agent_naam: str, elapsed_ms: float, error: Any = None) -> None:
        """Registreer per-agent timing en foutstatistiek."""
        with _METRICS_LOCK:
            if agent_naam not in _AGENT_PIPELINE_METRICS:
                _AGENT_PIPELINE_METRICS[agent_naam] = {
                    "calls": 0, "errors": 0, "total_ms": 0.0,
                    "last_error": None, "last_call_ts": 0.0,
                }
            m = _AGENT_PIPELINE_METRICS[agent_naam]
            m["calls"] += 1
            m["total_ms"] += elapsed_ms
            m["last_call_ts"] = time.time()
            if error:
                m["errors"] += 1
                m["last_error"] = str(error)[:200]

    # ── Phase 56: Forge Tool Dispatch ──

    async def dispatch_forged_tool(
        self, tool_name: str, arguments: Dict[str, Any],
        trace_id: str = "",
    ) -> "SwarmPayload":
        """Execute a dynamically loaded forge tool as a SwarmPayload.

        S-Tier: any failure returns error payload, never crashes server.
        """
        t0 = time.time()
        try:
            from danny_toolkit.core.forge_loader import execute_forged_tool
            result = execute_forged_tool(tool_name, arguments)
            elapsed = time.time() - t0

            if result.get("status") == "error":
                return SwarmPayload(
                    agent="Artificer",
                    type="error",
                    content=f"Forged tool error: {result.get('error', '?')}",
                    display_text=f"Tool {tool_name} failed",
                    metadata={"execution_time": elapsed, "forged_tool": tool_name},
                    trace_id=trace_id,
                )

            content = str(result.get("result", ""))
            return SwarmPayload(
                agent="Artificer",
                type="text",
                content=content,
                display_text=content[:500],
                metadata={
                    "execution_time": elapsed,
                    "forged_tool": tool_name,
                    "forged": True,
                },
                trace_id=trace_id,
            )
        except Exception as e:
            logger.error("Forge dispatch crashed: %s", e)
            return SwarmPayload(
                agent="Artificer",
                type="error",
                content=f"Forge dispatch error: {e}",
                display_text=f"Tool {tool_name} crashed",
                metadata={"forged_tool": tool_name},
                trace_id=trace_id,
            )

    def get_forged_tool_schemas(self) -> List[Dict]:
        """Return OpenAI-compatible schemas for all loaded forge tools."""
        return self._forged_schemas

    # ── Phase 56: Resonance Optimizer — Turbo-Boost ──

    def apply_turbo_boost(self) -> Optional[Dict]:
        """Resonance Optimizer: find the most efficient agent and apply Turbo-Boost.

        Efficiency Score = SP / avg_latency (seconds).
        The winning agent receives a one-time Hebbian boost of +0.15
        across GENERAL, DATA, SEARCH categories.

        Returns dict with winner details or None if no telemetry available.
        """
        try:
            from danny_toolkit.brain.synapse import get_synapse
            synapse = get_synapse()
            scores = synapse.get_efficiency_scores()
            if not scores:
                logger.info("Turbo-Boost: geen telemetry beschikbaar")
                return None

            winner = scores[0]
            agent_name = winner["agent"]

            # Apply +0.15 boost across 3 categories
            TURBO_SIGNAL = 0.15
            for category in ["GENERAL", "DATA", "SEARCH"]:
                synapse._apply_plasticity(category, agent_name, TURBO_SIGNAL)
            synapse._safe_commit()
            synapse._auto_export()

            new_sp = synapse._agent_sp(agent_name)
            winner["new_sp"] = new_sp

            logger.info(
                "Turbo-Boost: %s (efficiency=%.2f, SP=%d→%d)",
                agent_name, winner["efficiency"], winner["sp"], new_sp,
            )

            try:
                from danny_toolkit.core.neural_bus import get_bus, EventTypes
                bus = get_bus()
                bus.publish(
                    EventTypes.SYNAPSE_FEEDBACK,
                    {
                        "operation": "turbo_boost",
                        "winner": winner,
                        "top_3": scores[:3],
                    },
                    bron="swarm_engine",
                )
            except Exception as e:
                logger.debug("Turbo-Boost NeuralBus publish: %s", e)

            return winner
        except Exception as e:
            logger.warning("Turbo-Boost failed: %s", e)
            return None

    # ── Phase 31: Per-agent circuit breaker helpers ──

    def _is_circuit_open(self, agent_naam: str) -> bool:
        """Check of agent circuit breaker open is.

        Ondersteunt half-open: als cooldown verlopen, laat 1 probe toe.
        Bij succes → reset. Bij falen → opnieuw open.
        """
        with _CIRCUIT_LOCK:
            state = _AGENT_CIRCUIT_STATE.get(agent_naam)
            if not state:
                return False
            if state["failures"] >= _CIRCUIT_BREAKER_THRESHOLD:
                if state.get("cooldown", 0) > 0:
                    return True
                # Cooldown verlopen — half-open probe
                if not state.get("half_open"):
                    state["half_open"] = True
                    logger.info("Circuit half-open voor %s, probe", agent_naam)
                return False  # Laat 1 request door
            return False

    def _record_circuit_failure(self, agent_naam: str) -> None:
        """Registreer opeenvolgende fout voor circuit breaker."""
        with _CIRCUIT_LOCK:
            if agent_naam not in _AGENT_CIRCUIT_STATE:
                _AGENT_CIRCUIT_STATE[agent_naam] = {
                    "failures": 0, "cooldown": 0,
                }
            state = _AGENT_CIRCUIT_STATE[agent_naam]
            state["failures"] += 1
            if state["failures"] >= _CIRCUIT_BREAKER_THRESHOLD:
                state["cooldown"] = _CIRCUIT_BREAKER_COOLDOWN
                self._swarm_metrics["circuit_breaker_trips"] += 1
                logger.warning(
                    "Circuit breaker OPEN voor %s na %d fouten",
                    agent_naam, state["failures"],
                )
                # NeuralBus event
                try:
                    from danny_toolkit.core.neural_bus import get_bus, EventTypes
                    get_bus().publish(EventTypes.AGENT_CIRCUIT_OPEN, {
                        "agent": agent_naam,
                        "failures": state["failures"],
                    }, bron="swarm_engine")
                except Exception as e:
                    logger.debug("NeuralBus circuit open publish: %s", e)

    def _record_circuit_success(self, agent_naam: str) -> None:
        """Reset opeenvolgende fouten na succesvolle dispatch."""
        with _CIRCUIT_LOCK:
            state = _AGENT_CIRCUIT_STATE.get(agent_naam)
            if state and state["failures"] > 0:
                was_open = state["failures"] >= _CIRCUIT_BREAKER_THRESHOLD
                was_half_open = state.get("half_open", False)
                state["failures"] = 0
                state["cooldown"] = 0
                state["half_open"] = False
                if was_half_open:
                    logger.info("Circuit RECOVERED voor %s (half-open probe succeeded)",
                                agent_naam)
                if was_open:
                    logger.info("Circuit breaker CLOSED voor %s", agent_naam)
                    try:
                        from danny_toolkit.core.neural_bus import get_bus, EventTypes
                        get_bus().publish(EventTypes.AGENT_CIRCUIT_CLOSED, {
                            "agent": agent_naam,
                        }, bron="swarm_engine")
                    except Exception as e:
                        logger.debug("NeuralBus circuit closed publish: %s", e)

    def _tick_circuit_cooldowns(self) -> None:
        """Verlaag circuit breaker cooldowns met 1 (per query cycle)."""
        with _CIRCUIT_LOCK:
            for state in _AGENT_CIRCUIT_STATE.values():
                if state.get("cooldown", 0) > 0:
                    state["cooldown"] -= 1

    # ── Upgrade: Adaptieve Timeouts ──

    def _adaptive_timeout(self, agent_naam: str) -> float:
        """Bereken timeout op basis van historische latency.

        Gebruikt gemiddelde + marge (1.5x) van eerdere calls.
        Clamp: min 5s, max 60s. Fallback: statische timeout.
        """
        with _METRICS_LOCK:
            metric = _AGENT_PIPELINE_METRICS.get(agent_naam)
        if not metric or metric.get("calls", 0) < 5:
            return _AGENT_TIMEOUTS.get(agent_naam, _DEFAULT_AGENT_TIMEOUT)
        avg_ms = metric["total_ms"] / max(metric["calls"], 1)
        # P95 schatting: avg × 1.5 (conservatief)
        p95_s = (avg_ms * 1.25) / 1000
        return max(5.0, min(p95_s, 60.0))

    # ── Upgrade: Circuit Half-Opening ──

    def _is_circuit_half_open(self, agent_naam: str) -> bool:
        """Check of circuit in half-open staat is (probe toestaan)."""
        with _CIRCUIT_LOCK:
            state = _AGENT_CIRCUIT_STATE.get(agent_naam)
            if not state:
                return False
            if (state["failures"] >= _CIRCUIT_BREAKER_THRESHOLD
                    and state.get("cooldown", 0) == 0):
                # Cooldown verlopen — half-open, sta 1 probe toe
                state["half_open"] = True
                logger.info("Circuit half-open voor %s, probe toegestaan",
                            agent_naam)
                return True
            return False

    # ── Upgrade: Systemic Failure Detectie ──

    def _detect_systemic_failure(self) -> bool:
        """Detecteer of 3+ agents tegelijk in circuit breaker open zijn.

        Returns:
            True als systemische fout gedetecteerd.
        """
        with _CIRCUIT_LOCK:
            open_count = sum(
                1 for state in _AGENT_CIRCUIT_STATE.values()
                if (state["failures"] >= _CIRCUIT_BREAKER_THRESHOLD
                    and state.get("cooldown", 0) > 0)
            )
        if open_count >= 3:
            self._swarm_metrics["systemic_failures"] = (
                self._swarm_metrics.get("systemic_failures", 0) + 1
            )
            logger.error(
                "SYSTEMIC FAILURE: %d agents tegelijk offline", open_count,
            )
            try:
                from danny_toolkit.core.neural_bus import get_bus, EventTypes
                get_bus().publish(EventTypes.ERROR_CLASSIFIED, {
                    "type": "systemic_failure",
                    "agents_offline": open_count,
                }, bron="swarm_engine")
            except Exception as e:
                logger.debug("Systemic failure publish: %s", e)
            return True
        return False

    def _publish_error_classified(self, fc: Any) -> None:
        """Publiceer ERROR_CLASSIFIED event + sla op in ring buffer."""
        try:
            _record_error_context(fc)
            from danny_toolkit.core.neural_bus import get_bus, EventTypes
            get_bus().publish(
                EventTypes.ERROR_CLASSIFIED,
                fc.to_dict(),
                bron="swarm_engine",
            )
        except Exception as e:
            logger.debug("ERROR_CLASSIFIED publish fout: %s", e)

    async def _timed_dispatch(self, agent: Agent, agent_input: str,
                              trace_id: str = "", recovery_depth: int = 0) -> SwarmPayload:
        """Wrap agent.process() met timing, timeout + error handling + Ouroboros self-heal."""
        agent_naam = agent.name
        t0 = time.time()

        # Manual pause check — skip als gepauzeerd door gebruiker
        with _PAUSE_LOCK:
            is_paused = agent_naam.upper() in _PAUSED_AGENTS
        if is_paused:
            return SwarmPayload(
                agent=agent_naam, type="error",
                content=f"[{agent_naam}] Handmatig gepauzeerd",
                display_text=f"Agent {agent_naam} is gepauzeerd",
                metadata={"error_type": "ManualPause"},
                trace_id=trace_id,
            )

        # Phase 31: per-agent circuit breaker — skip als open
        if self._is_circuit_open(agent_naam):
            logger.info("Circuit open voor %s, overgeslagen (trace=%s)",
                        agent_naam, trace_id)
            # Phase 35: FoutContext
            try:
                from danny_toolkit.core.error_taxonomy import (
                    FoutContext, FoutErnst, HerstelStrategie,
                )
                import uuid as _uuid
                fc = FoutContext(
                    fout_id=_uuid.uuid4().hex[:8],
                    fout_type="CircuitBreakerOpen",
                    agent=agent_naam,
                    ernst=FoutErnst.HERSTELBAAR,
                    strategie=HerstelStrategie.SKIP,
                    bericht="Circuit breaker open",
                    trace_id=trace_id,
                )
                _meta = {"error_type": "CircuitBreakerOpen", "fout_context": fc.to_dict()}
                self._publish_error_classified(fc)
            except Exception:
                _meta = {"error_type": "CircuitBreakerOpen"}
            return SwarmPayload(
                agent=agent_naam, type="error",
                content=f"[{agent_naam}] Circuit breaker open",
                display_text=f"Agent {agent_naam} tijdelijk uitgeschakeld",
                metadata=_meta,
                trace_id=trace_id,
            )

        # --- Semantic Cache: lookup ---
        try:
            if self._semantic_cache is None:
                from danny_toolkit.core.semantic_cache import get_semantic_cache
                self._semantic_cache = get_semantic_cache()
            cache_result = self._semantic_cache.lookup(agent_naam, agent_input)
            if cache_result:
                self._swarm_metrics["semantic_cache_hits"] += 1
                cached_meta = cache_result.get("metadata", {})
                cached_meta["cached"] = True
                cached_meta["trace_id"] = trace_id
                return SwarmPayload(
                    agent=agent_naam,
                    type=cache_result.get("type", "text"),
                    content=cache_result["content"],
                    metadata=cached_meta,
                    trace_id=trace_id,
                )
            self._swarm_metrics["semantic_cache_misses"] += 1
        except Exception as e:
            logger.debug("Semantic cache lookup failed: %s", e)

        # Per-agent timeout — adaptief op basis van historische latency
        timeout = self._adaptive_timeout(agent_naam)

        try:
            result = await asyncio.wait_for(
                agent.process(agent_input, self.brain),
                timeout=timeout,
            )
            elapsed_ms = (time.time() - t0) * 1000
            self._record_agent_metric(agent_naam, elapsed_ms)
            self._record_circuit_success(agent_naam)
            # Phase 56: Synapse telemetry — record execution latency
            try:
                from danny_toolkit.brain.synapse import get_synapse
                get_synapse().record_telemetry(agent_naam, elapsed_ms / 1000.0)
            except Exception as e:
                logger.debug("Synapse telemetry: %s", e)
            # Waakhuis: registreer succesvolle dispatch
            try:
                from danny_toolkit.brain.waakhuis import get_waakhuis
                get_waakhuis().registreer_dispatch(agent_naam, elapsed_ms)
            except Exception as e:
                logger.debug("Waakhuis dispatch: %s", e)
            # --- Semantic Cache: store (full payload state) ---
            try:
                if self._semantic_cache and result and hasattr(result, 'content') and result.content:
                    if not (hasattr(result, 'metadata') and result.metadata and result.metadata.get('error_type')):
                        self._semantic_cache.store(
                            agent_naam, agent_input, result.content,
                            payload_type=getattr(result, 'type', 'text'),
                            payload_meta=getattr(result, 'metadata', None),
                        )
            except Exception as e:
                logger.debug("Semantic cache store failed: %s", e)
            # Propageer trace_id naar payload
            if hasattr(result, "trace_id"):
                result.trace_id = trace_id
            return result
        except asyncio.TimeoutError:
            elapsed_ms = (time.time() - t0) * 1000
            err = f"Timeout na {timeout}s"
            self._record_agent_metric(agent_naam, elapsed_ms, error=err)
            self._record_circuit_failure(agent_naam)
            self._swarm_metrics["agent_timeouts"] += 1
            logger.warning("Agent %s timeout na %ss (trace=%s)",
                           agent_naam, timeout, trace_id)
            try:
                from danny_toolkit.brain.waakhuis import get_waakhuis
                get_waakhuis().registreer_fout(agent_naam, "TimeoutError", err)
            except Exception as e:
                logger.debug("Waakhuis timeout fout: %s", e)
            _log_to_cortical(
                agent_naam, "agent_timeout",
                {"timeout_s": timeout, "elapsed_ms": round(elapsed_ms, 1)},
                trace_id=trace_id,
            )
            # Phase 35+38: FoutContext + publish + retry
            _meta = {"error_type": "TimeoutError"}
            try:
                from danny_toolkit.core.error_taxonomy import (
                    maak_fout_context, is_retry_safe, classificeer,
                )
                _te = asyncio.TimeoutError(err)
                fc = maak_fout_context(_te, agent_naam, trace_id)
                _meta["fout_context"] = fc.to_dict()
                self._publish_error_classified(fc)

                # Phase 38: retry als VOORBIJGAAND + RETRY
                if is_retry_safe(_te):
                    definitie = classificeer(_te)
                    for poging in range(definitie.retry_max):
                        wacht = min(2 ** poging + random.uniform(0, 1), 10)
                        logger.info(
                            "Retry %d/%d voor %s na %.1fs (trace=%s)",
                            poging + 1, definitie.retry_max,
                            agent_naam, wacht, trace_id,
                        )
                        self._swarm_metrics["error_retries_attempted"] += 1
                        await asyncio.sleep(wacht)
                        try:
                            retry_result = await asyncio.wait_for(
                                agent.process(agent_input, self.brain),
                                timeout=timeout,
                            )
                            fc.herstel_geprobeerd = True
                            fc.herstel_gelukt = True
                            self._record_circuit_success(agent_naam)
                            retry_ms = (time.time() - t0) * 1000
                            self._record_agent_metric(agent_naam, retry_ms)
                            self._swarm_metrics["error_retries_succeeded"] += 1
                            _log_to_cortical(
                                agent_naam, "agent_retry_success",
                                {"poging": poging + 1,
                                 "elapsed_ms": round(retry_ms, 1)},
                                trace_id=trace_id,
                            )
                            if hasattr(retry_result, "trace_id"):
                                retry_result.trace_id = trace_id
                            return retry_result
                        except Exception as retry_e:
                            logger.debug("Retry %d mislukt voor %s: %s",
                                         poging + 1, agent_naam, retry_e)
                    fc.herstel_geprobeerd = True
                    fc.herstel_gelukt = False
            except Exception as _retry_final_e:
                logger.warning("Retry fallback fout voor %s: %s", agent_naam, _retry_final_e)
            return SwarmPayload(
                agent=agent_naam, type="error",
                content=f"[{agent_naam}] {err}",
                display_text=f"Agent {agent_naam} timeout ({timeout}s)",
                metadata=_meta,
                trace_id=trace_id,
            )
        except Exception as e:
            elapsed_ms = (time.time() - t0) * 1000
            self._record_agent_metric(agent_naam, elapsed_ms, error=e)
            # Ouroboros 429 Shield: rate limits zijn API-schuld, niet agent-schuld
            _err_str = str(e).lower()
            _is_rate_limit = any(m in _err_str for m in [
                "429", "rate_limit", "rate limit", "too many requests",
                "resource_exhausted", "quota",
            ])
            if _is_rate_limit:
                logger.info(
                    "Agent %s 429 rate limit — GEEN circuit penalty (trace=%s)",
                    agent_naam, trace_id,
                )
            else:
                self._record_circuit_failure(agent_naam)
            logger.warning("Agent %s fout: %s (trace=%s)", agent_naam, e, trace_id)
            # Waakhuis: registreer fout
            try:
                from danny_toolkit.brain.waakhuis import get_waakhuis
                get_waakhuis().registreer_fout(agent_naam, type(e).__name__, str(e)[:200])
            except Exception as e2:
                logger.debug("Waakhuis agent fout: %s", e2)
            _log_to_cortical(
                agent_naam, "agent_error",
                {"error": str(e)[:200],
                 "error_type": type(e).__name__,
                 "elapsed_ms": round(elapsed_ms, 1)},
                trace_id=trace_id,
            )
            # Phase 35+38: FoutContext + publish + retry
            _meta = {"error_type": type(e).__name__}
            try:
                from danny_toolkit.core.error_taxonomy import (
                    maak_fout_context, is_retry_safe, classificeer,
                )
                fc = maak_fout_context(e, agent_naam, trace_id)
                _meta["fout_context"] = fc.to_dict()
                self._publish_error_classified(fc)

                # Phase 38: retry als VOORBIJGAAND + RETRY
                if is_retry_safe(e):
                    definitie = classificeer(e)
                    for poging in range(definitie.retry_max):
                        wacht = min(2 ** poging + random.uniform(0, 1), 10)
                        logger.info(
                            "Retry %d/%d voor %s na %.1fs (trace=%s)",
                            poging + 1, definitie.retry_max,
                            agent_naam, wacht, trace_id,
                        )
                        self._swarm_metrics["error_retries_attempted"] += 1
                        await asyncio.sleep(wacht)
                        try:
                            retry_result = await asyncio.wait_for(
                                agent.process(agent_input, self.brain),
                                timeout=timeout,
                            )
                            fc.herstel_geprobeerd = True
                            fc.herstel_gelukt = True
                            self._record_circuit_success(agent_naam)
                            retry_ms = (time.time() - t0) * 1000
                            self._record_agent_metric(agent_naam, retry_ms)
                            self._swarm_metrics["error_retries_succeeded"] += 1
                            _log_to_cortical(
                                agent_naam, "agent_retry_success",
                                {"poging": poging + 1,
                                 "elapsed_ms": round(retry_ms, 1)},
                                trace_id=trace_id,
                            )
                            if hasattr(retry_result, "trace_id"):
                                retry_result.trace_id = trace_id
                            return retry_result
                        except Exception as retry_e:
                            logger.debug("Retry %d mislukt voor %s: %s",
                                         poging + 1, agent_naam, retry_e)
                    fc.herstel_geprobeerd = True
                    fc.herstel_gelukt = False
            except Exception as _retry_final_e:
                logger.warning("Retry fallback fout voor %s: %s", agent_naam, _retry_final_e)

            # ── Phase 57: Ouroboros Self-Healing ─────────────────
            if recovery_depth < 1:
                try:
                    import traceback as _tb
                    from danny_toolkit.core.ouroboros import get_ouroboros
                    _ouroboros = get_ouroboros()
                    _error_trace = _tb.format_exception(
                        type(e), e, e.__traceback__,
                    )
                    _heal = await _ouroboros.handle_exception(
                        failed_agent=agent_naam,
                        error_trace="".join(_error_trace),
                        original_task=agent_input[:1000],
                        recovery_depth=recovery_depth + 1,
                        trace_id=trace_id,
                    )
                    self._swarm_metrics["ouroboros_attempts"] += 1
                    if _heal.success:
                        self._swarm_metrics["ouroboros_heals"] += 1
                        logger.info(
                            "Ouroboros: %s geheeld door Artificer (trace=%s)",
                            agent_naam, trace_id,
                        )
                        _meta["ouroboros_healed"] = True
                        _meta["heal_output"] = _heal.heal_output[:300]
                        return SwarmPayload(
                            agent=agent_naam, type="text",
                            content=_heal.heal_output,
                            display_text=(
                                f"🐍 Ouroboros: {agent_naam} hersteld "
                                f"via Artificer ({_heal.elapsed_s:.1f}s)"
                            ),
                            metadata=_meta,
                            trace_id=trace_id,
                        )
                    else:
                        logger.warning(
                            "Ouroboros: heal mislukt voor %s: %s",
                            agent_naam, _heal.heal_output[:100],
                        )
                        _meta["ouroboros_attempted"] = True
                        _meta["ouroboros_halt"] = _heal.heal_output[:200]
                except Exception as _ouroboros_err:
                    logger.debug("Ouroboros dispatch fout: %s", _ouroboros_err)

            return SwarmPayload(
                agent=agent_naam, type="error",
                content=f"[{agent_naam}] Fout: {e}",
                display_text=f"Agent {agent_naam} fout: {e}",
                metadata=_meta,
                trace_id=trace_id,
            )

    @property
    def _governor(self) -> Any:
        """Lazy OmegaGovernor voor rate limit tracking.

        FAIL-CLOSED: als Governor niet laadt, raise PermissionError.
        Zonder Governor is er geen rate limiting, injection detection,
        of PII scrubbing — te gevaarlijk om door te laten.
        """
        if not hasattr(self, "_gov_instance"):
            try:
                from danny_toolkit.brain.governor import (
                    OmegaGovernor,
                )
            except ImportError as e:
                if os.getenv("DANNY_TEST_MODE") == "1":
                    logger.debug("brain.governor niet beschikbaar (test mode)")
                    self._gov_instance = None
                    return self._gov_instance
                raise PermissionError(
                    f"[FAIL-CLOSED] OmegaGovernor niet laadbaar: {e}. "
                    "Swarm executie geblokkeerd zonder safety guardian."
                ) from e
            self._gov_instance = OmegaGovernor() if OmegaGovernor is not None else None
        return self._gov_instance

    def _register_agents(self) -> Dict[str, Agent]:
        """Registreer alle beschikbare agents."""
        try:
            from danny_toolkit.brain.trinity_omega import (
                CosmicRole,
            )
        except ImportError:
            logger.debug("brain.trinity_omega niet beschikbaar")
            return {}
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
            "MEMEX": MemexAgent(
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
            "PIXEL": PixelAgent(
                "Pixel", "Vision",
            ),
            "ALCHEMIST": AlchemistAgent(
                "Alchemist", "Data",
                CosmicRole.ALCHEMIST,
            ),
            "VOID": BrainAgent(
                "Void", "Cleanup",
                CosmicRole.VOID,
            ),
            "COHERENTIE": CoherentieAgent(
                "Coherentie", "Hardware",
            ),
            "STRATEGIST": StrategistAgent(
                "Strategist", "Planning",
            ),
            "ARTIFICER": ArtificerAgent(
                "Artificer", "Forge",
            ),
            "VIRTUAL_TWIN": VirtualTwinAgent(
                "#@*VirtualTwin", "Analysis",
            ),
            # LEGION: disabled

            # Mirror Shield: Honeypot voor geblokkeerde requests
            **({"PHANTOM": PhantomAgent(
                "Phantom", "Decoy",
            )} if HAS_PHANTOM else {}),

        }

    # ── Lazy Oracle Property ──

    @property
    def oracle(self) -> OracleAgent:
        """Lazy OracleAgent — geen import overhead."""
        if self._oracle is None:
            try:
                from danny_toolkit.brain.oracle import (
                    OracleAgent,
                )
            except ImportError:
                logger.debug("brain.oracle niet beschikbaar")
                OracleAgent = None
            if OracleAgent is not None:
                self._oracle = OracleAgent(persist=False)
        return self._oracle

    @property
    def _tribunal(self) -> Any:
        """Lazy AdversarialTribunal."""
        if not hasattr(self, "_tribunal_instance"):
            try:
                from danny_toolkit.brain.adversarial_tribunal import (
                    get_adversarial_tribunal,
                )
                self._tribunal_instance = (
                    get_adversarial_tribunal(brain=self.brain)
                )
            except Exception as e:
                logger.debug("AdversarialTribunal laden mislukt: %s", e)
                self._tribunal_instance = None
        return self._tribunal_instance

    @property
    def synapse(self) -> TheSynapse | None:
        """Lazy TheSynapse singleton — synaptic pathway plasticity."""
        if not hasattr(self, "_synapse_instance"):
            try:
                from danny_toolkit.brain.synapse import (
                    get_synapse,
                )
                self._synapse_instance = get_synapse()
            except Exception as e:
                logger.debug(
                    "TheSynapse laden mislukt: %s", e,
                )
                self._synapse_instance = None
        return self._synapse_instance

    @property
    def phantom(self) -> ThePhantom | None:
        """Lazy ThePhantom — anticipatory intelligence."""
        if not hasattr(self, "_phantom_instance"):
            try:
                from danny_toolkit.brain.phantom import (
                    ThePhantom,
                )
                self._phantom_instance = ThePhantom()
            except Exception as e:
                logger.debug(
                    "ThePhantom laden mislukt: %s", e,
                )
                self._phantom_instance = None
        return self._phantom_instance

    @property
    def virtual_twin(self) -> Any:
        """Lazy VirtualTwin — sandboxed system duplicate."""
        if not hasattr(self, "_virtual_twin_instance"):
            try:
                from danny_toolkit.brain.virtual_twin import (
                    VirtualTwin,
                )
                self._virtual_twin_instance = VirtualTwin()
            except Exception as e:
                logger.debug(
                    "VirtualTwin laden mislukt: %s", e,
                )
                self._virtual_twin_instance = None
        return self._virtual_twin_instance

    async def _tribunal_verify(
        self, results: list, user_input: str, callback: Any = None,
    ) -> list:
        """Tribunal verificatie voor Strategist output."""
        tribunal = self._tribunal
        if tribunal is None:
            return results

        verified = []
        for payload in results:
            if payload.agent != "Strategist":
                verified.append(payload)
                continue

            content = str(
                payload.display_text or payload.content
            )[:3000]
            try:
                verdict = await asyncio.wait_for(
                    tribunal.adeliberate(
                        user_input, content,
                    ),
                    timeout=30.0,
                )
                payload.metadata["tribunal_verified"] = (
                    verdict.accepted
                )
                payload.metadata["tribunal_rounds"] = (
                    verdict.rounds
                )
                if verdict.accepted:
                    self._swarm_metrics[
                        "tribunal_verified"
                    ] += 1
                else:
                    self._swarm_metrics[
                        "tribunal_warnings"
                    ] += 1
                    payload.metadata["tribunal_warning"] = (
                        "Niet gevalideerd door Tribunal"
                    )
                    if callback:
                        callback(
                            "\u2696\ufe0f TRIBUNAL: output niet"
                            " gevalideerd"
                        )
            except asyncio.TimeoutError:
                self._swarm_metrics[
                    "tribunal_errors"
                ] += 1
                logger.warning(
                    "Tribunal timeout na 30s voor %s",
                    payload.agent,
                )
                payload.metadata["tribunal_warning"] = (
                    "Tribunal verificatie timeout (30s)"
                )
            except Exception as e:
                self._swarm_metrics[
                    "tribunal_errors"
                ] += 1
                logger.debug(
                    "Tribunal verification failed: %s",
                    e,
                )
                payload.metadata["tribunal_warning"] = (
                    "Tribunal verificatie mislukt"
                )
            verified.append(payload)

        return verified

    # ── Hook Systeem ──

    def add_hook(self, event: str, callback: Any) -> None:
        """Registreer een hook callback.

        Args:
            event: "pre_task", "post_task" of
                   "failure".
            callback: Callable die aangeroepen wordt.
        """
        hook_map = {
            "pre_task": self.on_pre_task,
            "post_task": self.on_post_task,
            "failure": self.on_failure,
        }
        hook_list = hook_map.get(event)
        if hook_list is not None:
            hook_list.append(callback)

    def _trigger_hooks(self, hooks: list, *args: Any) -> None:
        """Trigger alle hooks in een lijst.

        Args:
            hooks: Lijst van callables.
            *args: Argumenten voor de callbacks.
        """
        for hook in hooks:
            try:
                hook(*args)
            except Exception as e:
                logger.debug("Hook execution failed: %s", e)

    # ── MEMEX Context Layer ──

    def _ophalen_memex_context(
        self, user_input: str, max_fragmenten: int = 3,
        max_chars: int = 300,
    ) -> List[str]:
        """Haal relevante context op via ChromaDB.

        Lightweight vector search (geen LLM).
        BlackBox gate: skip bekende falende queries.
        Retourneert max 3 fragmenten van 300 chars.

        Args:
            user_input: Gebruikersinput.
            max_fragmenten: Max aantal fragmenten.
            max_chars: Max tekens per fragment.

        Returns:
            Lijst van context strings.
        """
        # BlackBox gate: skip queries die eerder faalden
        try:
            from danny_toolkit.brain.black_box import get_black_box
            bb = get_black_box()
            if hasattr(bb, "is_rejected") and bb.is_rejected(user_input):
                logger.info("BlackBox rejection: MEMEX overgeslagen voor bekende faal-query")
                return []
        except Exception as e:
            logger.debug("BlackBox MEMEX gate: %s", e)

        memex = self.agents.get("MEMEX")
        if not memex:
            return []

        try:
            collection = memex._get_collection()
            if not collection:
                return []

            resultaten = collection.query(
                query_texts=[user_input],
                n_results=max_fragmenten,
            )

            fragmenten = []
            if (resultaten
                    and resultaten.get("documents")):
                # Try shadow summary lookup (cached instance)
                summary_map = {}
                try:
                    doc_ids = [
                        did for ids in resultaten.get("ids", [])
                        for did in ids
                    ]
                    if doc_ids:
                        if self._shadow_cortex is None:
                            try:
                                from danny_toolkit.brain.virtual_twin import ShadowCortex
                                self._shadow_cortex = ShadowCortex()
                            except ImportError:
                                logger.debug("ShadowCortex import niet beschikbaar")
                        if self._shadow_cortex:
                            summary_map = self._shadow_cortex.lookup_summaries(doc_ids) or {}
                            if summary_map:
                                self._swarm_metrics["summary_hits"] += 1
                except Exception as e:
                    logger.debug("Shadow summary lookup failed: %s", e)

                for i, doc_list in enumerate(resultaten["documents"]):
                    id_list = (
                        resultaten["ids"][i]
                        if resultaten.get("ids") and i < len(resultaten["ids"])
                        else []
                    )
                    for j, doc in enumerate(doc_list):
                        doc_id = id_list[j] if j < len(id_list) else None
                        # Use summary if available, otherwise full text
                        if doc_id and doc_id in summary_map:
                            tekst = summary_map[doc_id][:max_chars]
                        else:
                            tekst = str(doc)[:max_chars]
                        if tekst.strip():
                            fragmenten.append(tekst)

            return fragmenten[:max_fragmenten]
        except Exception as e:
            logger.debug("Memex context ophalen mislukt: %s", e)
            return []

    @staticmethod
    def _injecteer_context(
        taak: str, context: List[str],
    ) -> str:
        """Prefix context blok aan agent taak.

        Args:
            taak: Originele taak tekst.
            context: Lijst van context fragmenten.

        Returns:
            Taak met context prefix.
        """
        if not context:
            return taak

        blok = "\n".join(
            f"- {frag}" for frag in context
        )
        return (
            f"[MEMEX CONTEXT]\n{blok}\n"
            f"[/MEMEX CONTEXT]\n\n{taak}"
        )

    # ── SENTINEL Output Validatie ──

    def _sentinel_valideer(
        self, results: List,
        user_input: str, callback: Any = None,
    ) -> List:
        """Valideer output via SentinelValidator.

        Logt waarschuwingen naar CorticalStack.

        Args:
            results: Lijst van SwarmPayloads.
            user_input: Originele input.
            callback: Log callback.

        Returns:
            Gevalideerde lijst van SwarmPayloads.
        """
        governor = None
        if self.brain and hasattr(
            self.brain, "governor"
        ):
            governor = self.brain.governor

        validator = SentinelValidator(
            governor=governor,
        )

        for payload in results:
            rapport = validator.valideer(payload)

            if not rapport["veilig"]:
                for w in rapport["waarschuwingen"]:
                    if callback:
                        callback(
                            f"\u26a0\ufe0f SENTINEL: {w}"
                        )
                    _log_to_cortical(
                        "sentinel", "waarschuwing",
                        {"agent": payload.agent,
                         "waarschuwing": w,
                         "input": user_input[:200]},
                    )

            # PII scrubbing op display_text
            if rapport["geschoond"]:
                payload.display_text = (
                    rapport["geschoond"]
                )

        return results

    # ── Pipeline Verificatie ──

    async def _verify_task(
        self, taak: dict, payloads: list,
    ) -> dict:
        """Verifieer of swarm output correct is.

        Combineert agent output en vraagt Oracle LLM
        of het resultaat voldoet aan de verwachting.

        Args:
            taak: dict met input, verwachting, etc.
            payloads: lijst SwarmPayloads.

        Returns:
            dict met match (bool), analyse (str).
        """
        verwachting = taak.get("verwachting", "")
        if not verwachting:
            return {"match": True, "analyse": ""}

        # Combineer output van alle agents
        output_samenvatting = "\n".join(
            f"{p.agent}: {str(p.content)[:300]}"
            for p in payloads
        )

        berichten = [{
            "role": "user",
            "content": (
                "Beoordeel of de output voldoet"
                " aan de verwachting.\n\n"
                f"OPDRACHT: {taak.get('input', '')}\n"
                f"VERWACHTING: {verwachting}\n"
                f"OUTPUT:\n{output_samenvatting}\n\n"
                'Antwoord ALLEEN met JSON:\n'
                '{"match": true/false,'
                ' "analyse": "uitleg"}'
            ),
        }]

        try:
            response = await self.oracle._call_api(
                berichten
            )
            tekst = self.oracle._extract_text(
                response
            )
            result = self.oracle._parse_stap_json(
                tekst
            )
            if result and "match" in result:
                return result
        except Exception as e:
            logger.debug("Oracle parse failed: %s", e)

        return {"match": False, "analyse": "onbekend"}

    @staticmethod
    def _is_rate_limit_error(error: Any) -> bool:
        """Detecteer rate limit fout (429/quota)."""
        fout_tekst = str(error).lower()
        patronen = [
            "429", "rate_limit", "rate limit",
            "ratelimit", "too many requests",
            "quota exceeded",
        ]
        return any(p in fout_tekst for p in patronen)

    async def _handle_swarm_failure(
        self, error: Any, taak: dict, callback: Any = None,
    ) -> dict:
        """Handel een gefaalde swarm taak af.

        1. Vraag Oracle om repair plan
        2. Voer herstelde taak uit
        3. Optionele herverificatie

        Args:
            error: De foutbeschrijving.
            taak: dict met input, verwachting, etc.
            callback: Functie(str) voor live updates.

        Returns:
            dict met geslaagd, plan, payloads,
            analyse.
        """
        def log(msg: str) -> None:
            """Stuur status update naar callback."""
            if callback:
                callback(msg)

        # Rate limit shortcut: wacht + retry
        # NB: central_brain handelt rate limits intern
        # af via per-provider circuit breakers en
        # fallback chain. Geen Governor failure
        # registreren — dat zou de global breaker
        # trippen en trinity_omega blokkeren.
        if self._is_rate_limit_error(error):
            log(
                "\u23f3 Rate limit gedetecteerd,"
                " wachten op cooldown..."
            )
            cooldown = min(
                self._governor._circuit_breaker.get(
                    "cooldown", 60
                ),
                65,
            )
            await asyncio.sleep(cooldown)

            try:
                payloads = await self.run(
                    taak.get("input", ""),
                    callback,
                )
                self._governor.record_api_success()
                log(
                    "\u2705 Rate limit:"
                    " retry succesvol"
                )
                return {
                    "geslaagd": True,
                    "plan": {
                        "analyse": "Rate limit",
                        "strategie": "cooldown"
                        " + retry",
                    },
                    "payloads": payloads,
                    "analyse": "Rate limit retry",
                }
            except Exception as e:
                logger.debug("Rate limit retry mislukt: %s", e)
                return {
                    "geslaagd": False,
                    "plan": None,
                    "payloads": [],
                    "analyse": (
                        "Rate limit:"
                        " retry mislukt"
                    ),
                }

        log(
            "\U0001f527 Repair: plan genereren..."
        )

        plan = await self.oracle.generate_repair_plan(
            str(error), taak,
        )

        if not plan:
            log(
                "\u274c Repair: geen plan"
                " gegenereerd"
            )
            return {
                "geslaagd": False,
                "plan": None,
                "payloads": [],
                "analyse": "Geen repair plan",
            }

        herstelde_input = plan.get(
            "herstelde_input",
            taak.get("input", ""),
        )

        log(
            f"\U0001f504 Repair: heruitvoeren"
            f" met '{herstelde_input[:50]}...'"
        )

        # Heruitvoeren via bestaande run()
        try:
            payloads = await self.run(
                herstelde_input, callback,
            )
        except Exception as e:
            logger.debug("Heruitvoering mislukt: %s", e)
            return {
                "geslaagd": False,
                "plan": plan,
                "payloads": [],
                "analyse": "Heruitvoering mislukt",
            }

        # Optionele herverificatie
        analyse = ""
        if taak.get("verwachting"):
            verificatie = await self._verify_task(
                taak, payloads,
            )
            analyse = verificatie.get(
                "analyse", ""
            )
            if not verificatie.get("match"):
                log(
                    "\u274c Repair: herverificatie"
                    " gefaald"
                )
                return {
                    "geslaagd": False,
                    "plan": plan,
                    "payloads": payloads,
                    "analyse": analyse,
                }

        log("\u2705 Repair: succesvol hersteld")
        return {
            "geslaagd": True,
            "plan": plan,
            "payloads": payloads,
            "analyse": analyse,
        }

    # ── Pipeline Executie ──

    async def execute_pipeline(
        self, taken: list, callback: Any = None,
    ) -> list:
        """Voer een pipeline van taken uit.

        Per taak: pre_hook -> run -> verify ->
        post_hook. Bij falen: repair ->
        failure_hook.

        Args:
            taken: lijst van taak-dicts, elk met
                input (str), verwachting (optioneel),
                agents (optioneel), metadata
                (optioneel).
            callback: Functie(str) voor live updates.

        Returns:
            lijst van resultaat-dicts per taak.
        """
        def log(msg: str) -> None:
            """Stuur status update naar callback."""
            if callback:
                callback(msg)

        resultaten = []

        for i, taak in enumerate(taken):
            taak_nr = i + 1
            taak_input = taak.get("input", "")

            log(
                f"\U0001f4cb Pipeline"
                f" [{taak_nr}/{len(taken)}]:"
                f" {taak_input[:50]}"
            )

            # Pre-task hooks
            self._trigger_hooks(
                self.on_pre_task, taak,
            )

            try:
                # Uitvoeren via bestaande run()
                payloads = await self.run(
                    taak_input, callback,
                )

                # Verificatie (als verwachting)
                if taak.get("verwachting"):
                    verificatie = (
                        await self._verify_task(
                            taak, payloads,
                        )
                    )

                    if not verificatie.get("match"):
                        raise TaskVerificationError(
                            verificatie.get(
                                "analyse",
                                "Verificatie gefaald",
                            ),
                            taak=taak,
                            payload=payloads,
                        )

                # Post-task hooks
                self._trigger_hooks(
                    self.on_post_task,
                    taak, payloads,
                )

                resultaten.append({
                    "taak": taak,
                    "payloads": payloads,
                    "status": "geslaagd",
                    "repair": None,
                })

            except (
                TaskVerificationError,
                Exception,
            ) as e:
                log(
                    f"\u26a0\ufe0f Taak"
                    f" {taak_nr} gefaald:"
                    f" {str(e)[:80]}"
                )

                # Failure hooks
                self._trigger_hooks(
                    self.on_failure, taak, e,
                )

                # Self-healing via Oracle
                repair = None
                if self.repair_mode:
                    repair = (
                        await self._handle_swarm_failure(
                            e, taak, callback,
                        )
                    )

                if repair and repair.get("geslaagd"):
                    resultaten.append({
                        "taak": taak,
                        "payloads": repair.get(
                            "payloads", []
                        ),
                        "status": "hersteld",
                        "repair": repair,
                    })
                else:
                    resultaten.append({
                        "taak": taak,
                        "payloads": (
                            e.payload
                            if isinstance(
                                e,
                                TaskVerificationError,
                            )
                            else []
                        ),
                        "status": "gefaald",
                        "repair": repair,
                    })

        geslaagd = sum(
            1 for r in resultaten
            if r["status"] in (
                "geslaagd", "hersteld",
            )
        )
        log(
            f"\U0001f3c1 Pipeline voltooid:"
            f" {geslaagd}/{len(resultaten)} OK"
        )

        return resultaten

    async def route(self, user_input: str) -> List[str]:
        """Adaptive routing: embedding-first, keyword-fallback.

        1. Probeer AdaptiveRouter (cosine similarity + Synapse bias)
        2. Fallback naar ROUTE_MAP (keyword matching)
        3. Fallback naar ECHO

        MEMEX wint van IOLAAX bij kennisvragen.
        """
        # Get Synapse routing bias
        bias = {}
        if self.synapse:
            try:
                bias = self.synapse.get_routing_bias(
                    user_input,
                )
                if bias:
                    self._swarm_metrics[
                        "synapse_adjustments"
                    ] += 1
            except Exception as e:
                logger.debug(
                    "Synapse bias failed: %s", e,
                )

        # Query cooldowns voor rate-aware routing
        throttled = set()
        try:
            from danny_toolkit.core.key_manager import (
                get_key_manager,
            )
            throttled = get_key_manager().get_agents_in_cooldown()
        except ImportError:
            logger.debug("KeyManager niet beschikbaar voor throttle check")

        # OracleEye advisory: bias routing model recommendation
        oracle_model_advisory = None
        try:
            from danny_toolkit.brain.oracle_eye import get_oracle_eye
            import psutil
            _oe = get_oracle_eye()
            _cpu = psutil.cpu_percent(interval=0)
            oracle_model_advisory = _oe.suggest_model(
                {"cpu": _cpu, "ram": psutil.virtual_memory().percent},
            )
            if oracle_model_advisory:
                self._swarm_metrics.setdefault("oracle_eye_advisories", 0)
                self._swarm_metrics["oracle_eye_advisories"] += 1
        except Exception as e:
            logger.debug("OracleEye advisory: %s", e)

        # Probeer embedding-based routing
        try:
            targets = self._router.route(
                user_input, synapse_bias=bias,
                exclude_agents=throttled,
            )
            _log_to_cortical(
                "router", "adaptive",
                {"targets": targets,
                 "input": user_input[:200],
                 "synapse_bias": bool(bias),
                 "oracle_model": oracle_model_advisory},
            )
            return targets
        except Exception as e:
            logger.debug("Embedding router failed: %s", e)

        # Fallback: keyword matching
        lower = user_input.lower()
        targets = []
        for agent_key, keywords in (
            self.ROUTE_MAP.items()
        ):
            if any(kw in lower for kw in keywords):
                targets.append(agent_key)

        # Filter throttled agents (keyword fallback)
        if throttled:
            targets = [
                t for t in targets
                if t not in throttled
            ]

        # MEMEX wint van IOLAAX bij kennisvragen
        if "MEMEX" in targets and "IOLAAX" in targets:
            targets.remove("IOLAAX")

        _log_to_cortical(
            "router", "keyword_fallback",
            {"targets": targets or ["ECHO"],
             "input": user_input[:200]},
        )
        return targets or ["ECHO"]

    async def run(
        self, user_input: str, callback: Any = None,
    ) -> List[SwarmPayload]:
        """Neural Hub pipeline met self-tuning.

        Flow:
        1. Governor Gate (input validatie)
        2. ECHO Fast-Track (begroetingen)
        3. Chronos enrichment (tijdscontext)
        4. MEMEX Context (vector search, tunable)
        5. Nexus Route (adaptive/keyword)
        6. Agent Execute (parallel)
        7. SENTINEL Validate (output check, tunable)

        Args:
            user_input: Tekst van de gebruiker.
            callback: Functie(str) voor live updates.

        Returns:
            Lijst van SwarmPayloads (1 per agent).
        """
        def log(msg: str) -> None:
            """Stuur status update naar callback."""
            if callback:
                callback(msg)

        # 0. SOVEREIGN SEAL — valideer herkomst
        # Als een ongeautoriseerd proces, een malafide
        # test-script of een losgeslagen agent toegang
        # probeert te forceren, wordt de executie direct
        # in de kiem gesmoord met een PermissionError.
        # Nul rekenkracht, nul extra threads, nul geheugen.
        # De deur blokkeert voordat het licht aangaat.
        self.validate_execution(self.brain)

        # Beperk thread pool voor deze event loop (hergebruik executor)
        loop = asyncio.get_running_loop()
        if not hasattr(self, "_executor"):
            self._executor = ThreadPoolExecutor(
                max_workers=_SWARM_MAX_WORKERS,
                thread_name_prefix="swarm",
            )
        loop.set_default_executor(self._executor)

        t = self._tuner

        # Phase 31: genereer trace_id voor request correlatie
        trace_id = uuid.uuid4().hex[:8]
        log(f"\U0001f50d Trace {trace_id}")

        # Phase 36: RequestTracer begin
        _tracer = None
        try:
            from danny_toolkit.core.config import Config as _Cfg
            if getattr(_Cfg, "TRACING_ENABLED", True):
                from danny_toolkit.core.request_tracer import (
                    get_request_tracer,
                )
                _tracer = get_request_tracer()
                _tracer.begin_trace(trace_id)
        except Exception as e:
            logger.debug("RequestTracer init: %s", e)

        # Phase 31: tick circuit breaker cooldowns
        self._tick_circuit_cooldowns()

        # Eternal Sentinel: auto-throttle gate
        try:
            from danny_toolkit.brain.eternal_sentinel import get_sentinel
            _sentinel = get_sentinel()
            if _sentinel.is_throttled:
                log("\u26a0\ufe0f Sentinel throttle actief — wacht op herstel...")
                for _wait in range(10):
                    if not _sentinel.is_throttled:
                        break
                    await asyncio.sleep(1)
                if _sentinel.is_throttled:
                    log("\u274c Sentinel throttle timeout — missie afgebroken")
                    return [SwarmPayload(
                        agent="Sentinel",
                        content="Systeem onder hoge belasting. Probeer later opnieuw.",
                        display_text="Systeem onder hoge belasting. Probeer later opnieuw.",
                        confidence=0.0,
                    )]
        except Exception as _se:
            logger.debug("Sentinel throttle check: %s", _se)

        # Eternal Sentinel: GPU boost + mission start event
        try:
            from danny_toolkit.core.neural_bus import get_bus, EventTypes
            get_bus().publish(EventTypes.MISSION_STARTED, {
                "trace_id": trace_id,
                "query_preview": user_input[:80],
            }, bron="swarm_engine")
        except Exception as e:
            logger.debug("Mission start NeuralBus publish: %s", e)

        # Systemic failure detectie: 3+ agents down → waarschuwing
        self._detect_systemic_failure()

        # 0. Echo Guard — dedup gate (voorkom feedback loops)
        try:
            q_hash = hashlib.md5(
                user_input.strip().lower().encode()
            ).hexdigest()
            now = time.time()
            for prev_hash, prev_ts in self._recent_queries:
                if prev_hash == q_hash and (now - prev_ts) < 60:
                    self._swarm_metrics["echo_guard_blocks"] += 1
                    msg = "Ik heb deze vraag net beantwoord."
                    return [SwarmPayload(
                        agent="EchoGuard", type="text",
                        content=msg, display_text=msg,
                    )]
            self._recent_queries.append((q_hash, now))
        except Exception as e:
            logger.debug("Echo guard error: %s", e)

        # Cortical Stack logging
        _log_to_cortical(
            "user", "query",
            {"prompt": user_input[:500]},
        )
        _learn_from_input(user_input)

        # 1. Governor Gate (NOOIT skippen)
        if _tracer:
            _tracer.begin_span("governor")
        t0 = time.time()
        if self.brain:
            safe, reason = (
                self.brain._governor_gate(user_input)
            )
            if not safe:
                t.registreer(
                    "governor",
                    (time.time() - t0) * 1000,
                )
                if _tracer:
                    _tracer.eind_span("blocked", {"reason": reason})
                    _tracer.eind_trace()
                log(
                    f"\u274c Governor: BLOCKED"
                    f" \u2014 {reason}"
                )
                self._swarm_metrics[
                    "governor_blocks"
                ] += 1
                # Mirror Shield: stuur naar PhantomAgent
                _phantom = self.agents.get("PHANTOM")
                if _phantom is not None:
                    try:
                        decoy = await _phantom.process(user_input)
                        log("👻 PhantomAgent: Mirror Shield actief")
                        return [decoy]
                    except Exception as e:
                        logger.debug("PhantomAgent fout: %s", e)
                # Fallback: kale blokkade
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
        t.registreer(
            "governor",
            (time.time() - t0) * 1000,
        )
        if _tracer:
            _tracer.eind_span("ok")

        # 2. ECHO Fast-Track (NOOIT skippen)
        t0 = time.time()
        fast = _fast_track_check(user_input)
        t.registreer(
            "fast_track",
            (time.time() - t0) * 1000,
            hit=fast is not None,
        )
        if fast:
            log("\u26a1 [FAST-TRACK] Echo")
            _log_to_cortical(
                "swarm", "fast_track",
                {"agent": "Echo",
                 "prompt": user_input[:200]},
            )
            log("\u2705 SWARM COMPLETE (fast-track)")
            self._swarm_metrics["fast_track_hits"] += 1
            self._query_count += 1
            return [fast]

        # 3. Chronos enrichment (NOOIT skippen)
        t0 = time.time()
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
        t.registreer(
            "chronos",
            (time.time() - t0) * 1000,
        )

        # 3.5 Phantom: check pre-warmed context
        phantom_category = None
        phantom_ctx = []
        if self.synapse and self.phantom:
            try:
                phantom_category = (
                    self.synapse.categorize_query(
                        user_input,
                    )
                )
                phantom_ctx = (
                    self.phantom.get_pre_warmed(
                        phantom_category,
                    )
                )
                if phantom_ctx:
                    self._swarm_metrics[
                        "phantom_hits"
                    ] += 1
                    log(
                        "\U0001f47b Phantom:"
                        f" {len(phantom_ctx)}"
                        " pre-warmed fragmenten"
                    )
            except Exception as e:
                logger.warning(
                    "Phantom pre-warm check FAILED: %s", e,
                )

        # 4. MEMEX Context (tunable)
        if _tracer:
            _tracer.begin_span("memex")
        if phantom_ctx:
            # Phantom cache hit — skip MEMEX fetch
            memex_ctx = phantom_ctx
            log(
                "\u23ed\ufe0f MEMEX:"
                " phantom cache hit"
            )
        elif not t.mag_skippen("memex"):
            t0 = time.time()
            memex_ctx = self._ophalen_memex_context(
                user_input,
            )
            t.registreer(
                "memex",
                (time.time() - t0) * 1000,
                fragmenten=len(memex_ctx),
            )
            if memex_ctx:
                log(
                    f"\U0001f4da MEMEX:"
                    f" {len(memex_ctx)}"
                    f" fragmenten geladen"
                )
        else:
            memex_ctx = []
            log(
                "\u23ed\ufe0f MEMEX:"
                " overgeslagen (tuning)"
            )

        if _tracer:
            _tracer.eind_span("ok", {"fragmenten": len(memex_ctx)})

        # 4.5 Cortex graph expansion (Phase 38)
        if _tracer:
            _tracer.begin_span("cortex_expand")
        _cortex_added = 0
        try:
            if getattr(Config, "CORTEX_ENRICHMENT_ENABLED", True):
                if self._cortex is None:
                    try:
                        from danny_toolkit.brain.cortex import TheCortex
                        self._cortex = TheCortex()
                    except ImportError:
                        self._cortex = False
                if self._cortex and self._cortex is not False:
                    _cx_results = await self._cortex.hybrid_search(
                        user_input, top_k=3,
                    )
                    if _cx_results:
                        for cr in _cx_results:
                            _cx_content = cr.get("content", "")
                            if _cx_content and _cx_content not in memex_ctx:
                                memex_ctx.append(_cx_content[:300])
                                _cortex_added += 1
                        self._swarm_metrics["cortex_enrichments"] += 1
                        log(
                            f"\U0001f9e0 Knowledge Graph:"
                            f" {_cortex_added}"
                            f" graph-expanded fragmenten"
                        )
        except Exception as e:
            logger.warning("Cortex graph expansion FAILED: %s", e)
        if _tracer:
            _tracer.eind_span("ok", {"cortex_fragments": _cortex_added})

        # 4.9 Phase 56: Forge Loader — hot-reload dynamische tools
        try:
            from danny_toolkit.core.forge_loader import scan_and_load_tools
            self._forged_tools, self._forged_schemas = scan_and_load_tools()
            if self._forged_tools:
                log(
                    f"\u2692\ufe0f Forge: {len(self._forged_tools)}"
                    f" tools geladen"
                )
        except Exception as e:
            logger.debug("Forge loader scan: %s", e)

        # 5. Nexus Route (NOOIT skippen)
        if _tracer:
            _tracer.begin_span("routing")
        t0 = time.time()
        targets = await self.route(user_input)
        t.registreer(
            "route",
            (time.time() - t0) * 1000,
        )
        log(
            f"\U0001f9e0 Nexus \u2192"
            f" {', '.join(targets)}"
        )
        if _tracer:
            _tracer.eind_span("ok", {"targets": targets})

        # 6. Parallel executie via asyncio.gather
        #    MEMEX context voor alle agents behalve
        #    MEMEX zelf (doet eigen RAG)
        if _tracer:
            _tracer.begin_span("dispatch")
        t0 = time.time()
        tasks = []
        for name in targets:
            agent = self.agents[name]
            log(f"\u26a1 {agent.name}: gestart...")

            if name == "MEMEX" or not memex_ctx:
                agent_input = enriched
            else:
                agent_input = self._injecteer_context(
                    enriched, memex_ctx,
                )

            tasks.append(
                asyncio.create_task(
                    self._timed_dispatch(
                        agent, agent_input,
                        trace_id=trace_id,
                    )
                )
            )

        results = await asyncio.gather(*tasks)
        t.registreer(
            "execute",
            (time.time() - t0) * 1000,
        )

        # Tel agent errors + Phase 36: eind dispatch span
        if _tracer:
            _tracer.eind_span("ok", {"agents": [r.agent for r in results]})
        error_count = sum(
            1 for r in results if r.type == "error"
        )
        if error_count:
            self._swarm_metrics["agent_errors"] += error_count
            logger.warning(
                "%d agent error(s) in pipeline", error_count,
            )

        # 6.5 Tribunal Verification (alleen STRATEGIST)
        # Filter error payloads uit tribunal verificatie
        if _tracer:
            _tracer.begin_span("tribunal")
        if any(r.agent == "Strategist" for r in results):
            non_error = [
                r for r in results if r.type != "error"
            ]
            error_results = [
                r for r in results if r.type == "error"
            ]
            if non_error:
                non_error = await self._tribunal_verify(
                    non_error, user_input, callback,
                )
            results = list(non_error) + error_results

        # 6.6 VirtualTwin NeuralBus publish
        if any(r.agent == "#@*VirtualTwin" for r in results):
            self._swarm_metrics[
                "twin_consultations"
            ] += 1
            try:
                from danny_toolkit.core.neural_bus import (
                    get_bus, EventTypes,
                )
                get_bus().publish(
                    EventTypes.TWIN_CONSULTATION,
                    {
                        "query": user_input[:200],
                        "agents": [
                            r.agent for r in results
                        ],
                    },
                    bron="swarm_engine",
                )
            except Exception as e:
                logger.debug(
                    "Twin NeuralBus publish: %s", e,
                )

        if _tracer:
            _tracer.eind_span("ok")

        # 7. SENTINEL Validate (tunable)
        _sentinel_warns = 0  # track for schild
        if _tracer:
            _tracer.begin_span("sentinel")
        if not t.mag_skippen("sentinel"):
            t0 = time.time()
            # Valideer en tel waarschuwingen
            governor = None
            if self.brain and hasattr(
                self.brain, "governor"
            ):
                governor = self.brain.governor
            sv = SentinelValidator(governor=governor)
            warns = 0
            results_list = list(results)
            for payload in results_list:
                rapport = sv.valideer(payload)
                if not rapport["veilig"]:
                    warns += len(
                        rapport["waarschuwingen"]
                    )
                    for w in rapport["waarschuwingen"]:
                        if callback:
                            callback(
                                f"\u26a0\ufe0f"
                                f" SENTINEL: {w}"
                            )
                        _log_to_cortical(
                            "sentinel", "waarschuwing",
                            {"agent": payload.agent,
                             "waarschuwing": w,
                             "input": (
                                 user_input[:200]
                             )},
                        )
                if rapport["geschoond"]:
                    payload.display_text = (
                        rapport["geschoond"]
                    )
            results = results_list
            _sentinel_warns = warns
            t.registreer(
                "sentinel",
                (time.time() - t0) * 1000,
                waarschuwingen=warns,
            )
            log(
                "\U0001f6e1\ufe0f SENTINEL: output OK"
            )
        else:
            results = list(results)
            log(
                "\u23ed\ufe0f SENTINEL:"
                " sampling (tuning)"
            )

        if _tracer:
            _tracer.eind_span("ok")

        # 7.5 HallucinatieSchild — finale anti-hallucinatie gate
        if _tracer:
            _tracer.begin_span("schild")
        try:
            from danny_toolkit.brain.hallucination_shield import (
                get_hallucination_shield,
            )
            schild = get_hallucination_shield()
            _MEDIA_TYPES = {"metrics", "area_chart", "bar_chart", "code"}
            _BYPASS_CONTENT = {"Brain offline"}
            schild_non_error = [
                r for r in results
                if r.type != "error"
                and r.type not in _MEDIA_TYPES
                and r.content not in _BYPASS_CONTENT
            ]
            if schild_non_error:
                # Extract tribunal verdict from metadata
                _tv = [
                    r.metadata.get("tribunal_verified")
                    for r in schild_non_error
                    if r.metadata.get(
                        "tribunal_verified",
                    ) is not None
                ]
                _tribunal_ok = (
                    all(_tv) if _tv else None
                )
                # Context-aware metadata voor
                # generatieve bypass
                _agents_in = list({
                    r.agent for r in schild_non_error
                    if r.agent
                })
                _sentinel_ok = (
                    _sentinel_warns == 0
                )
                schild_rapport = schild.beoordeel(
                    schild_non_error,
                    user_input,
                    context_docs=(
                        memex_ctx if memex_ctx
                        else None
                    ),
                    tribunal_gevalideerd=_tribunal_ok,
                    metadata={
                        "agents_involved": _agents_in,
                        "sentinel_ok": _sentinel_ok,
                    },
                )
                if schild_rapport.geblokkeerd:
                    self._swarm_metrics[
                        "schild_blocks"
                    ] += 1
                    log(
                        "\U0001f6ab SCHILD: output"
                        " geblokkeerd"
                        f" (score {schild_rapport.totaal_score:.2f})"
                    )
                    blocked_payload = SwarmPayload(
                        agent="HallucinatieSchild",
                        type="text",
                        content=(
                            "Antwoord geblokkeerd door"
                            " HallucinatieSchild"
                            f" (score:"
                            f" {schild_rapport.totaal_score:.2f})"
                        ),
                        display_text=(
                            "\u26a0\ufe0f Antwoord niet"
                            " betrouwbaar genoeg."
                            " Probeer de vraag"
                            " specifieker te stellen."
                        ),
                        metadata={
                            "schild_blocked": True,
                            "schild_score": (
                                schild_rapport.totaal_score
                            ),
                        },
                    )
                    error_only = [
                        r for r in results
                        if r.type == "error"
                    ]
                    results = [blocked_payload] + error_only
        except ImportError:
            logger.debug("HallucinatieSchild import niet beschikbaar")
        except Exception as e:
            logger.warning(
                "HallucinatieSchild FAILED: %s", e,
            )

        if _tracer:
            _tracer.eind_span("ok")

        # Callback per resultaat
        for res in results:
            rt = res.metadata.get(
                "execution_time", 0
            )
            log(
                f"\u2705 {res.agent}: klaar"
                f" ({rt:.1f}s)"
            )

        # Pipeline samenvatting
        log(f"\U0001f4ca {t.get_samenvatting()}")

        # Phase 31: zorg dat alle payloads trace_id hebben
        for r in results:
            if hasattr(r, "trace_id") and not r.trace_id:
                r.trace_id = trace_id

        # Cortical Stack logging
        _log_to_cortical(
            "swarm", "response",
            {
                "agents": [r.agent for r in results],
                "output_preview": str(
                    results[0].content
                )[:300],
                "tuning": t.get_samenvatting(),
            },
            trace_id=trace_id,
        )

        # Emit TASK_COMPLETE naar Sensorium
        try:
            if (
                self.brain
                and hasattr(self.brain, "governor")
                and hasattr(
                    self.brain.governor, "_daemon"
                )
                and self.brain.governor._daemon
            ):
                daemon = self.brain.governor._daemon
                from danny_toolkit.daemon.sensorium import (
                    EventType,
                )
                daemon.sensorium.sense_event(
                    EventType.TASK_COMPLETE,
                    source="swarm_engine",
                    data={
                        "agents": [
                            r.agent for r in results
                        ],
                        "input": user_input[:100],
                    },
                    importance=0.6,
                )
        except Exception as e:
            logger.debug(
                "Sensorium event emission failed: %s",
                e,
            )

        # Best-effort triple extraction uit tekst resultaten
        try:
            from danny_toolkit.brain.cortex import TheCortex
            cortex = TheCortex()
            for r in results:
                txt = str(r.display_text) if r.display_text else ""
                if len(txt) > 50 and r.type == "text":
                    triples = await cortex.extract_triples(txt)
                    for triple in triples:
                        cortex.add_triple(
                            triple.subject, triple.predicaat,
                            triple.object,
                            triple.confidence, triple.bron,
                        )
                        self._swarm_metrics[
                            "triples_extracted"
                        ] += 1
        except Exception as e:
            logger.debug(
                "Triple extraction failed: %s", e
            )

        # Synapse: record interaction trace + outcome reinforcement
        if self.synapse:
            try:
                total_len = sum(
                    len(str(r.display_text or r.content))
                    for r in results
                )
                exec_ms = sum(
                    r.metadata.get("execution_time", 0)
                    for r in results
                ) * 1000
                self.synapse.record_interaction(
                    user_input,
                    [r.agent for r in results],
                    execution_ms=exec_ms,
                    response_length=total_len,
                )
            except Exception as e:
                logger.debug(
                    "Synapse record failed: %s", e,
                )

            # Synaptic Reinforcement: backpropagate
            try:
                _schild_sc = None
                try:
                    _schild_sc = schild_rapport.totaal_score
                except Exception as e:
                    logger.debug("Schild score ophalen: %s", e)
                bp = self.synapse.backpropagate_success(
                    user_input,
                    results,
                    sentinel_warns=_sentinel_warns,
                    schild_score=_schild_sc,
                )
                if bp.get("agents"):
                    self._swarm_metrics[
                        "synapse_reinforcements"
                    ] += 1
                    log(
                        f"\U0001f9ec Synapse backprop:"
                        f" {len(bp['agents'])} agents"
                        f" [{bp['category']}]"
                    )
            except Exception as e:
                logger.debug(
                    "Synapse backprop failed: %s",
                    e,
                )

        # Phantom: resolve predictions
        if self.phantom and phantom_category:
            try:
                self.phantom.resolve_predictions(
                    phantom_category,
                )
                self._swarm_metrics[
                    "phantom_predictions"
                ] += 1
            except Exception as e:
                logger.debug(
                    "Phantom resolve failed: %s", e,
                )

        # Phase 36: eind trace
        if _tracer:
            _tracer.eind_trace()

        # Eternal Sentinel: GPU idle + mission end event
        try:
            from danny_toolkit.core.neural_bus import get_bus, EventTypes
            get_bus().publish(EventTypes.REQUEST_TRACE_COMPLETE, {
                "trace_id": trace_id,
                "agents": [r.agent for r in results] if results else [],
            }, bron="swarm_engine")
        except Exception as e:
            logger.debug("Request trace complete NeuralBus publish: %s", e)

        # B-95: Record response outcome to CorticalStack
        self._record_response_outcome(user_input, results)

        log("\u2705 SWARM COMPLETE")
        self._query_count += 1
        self._total_time += sum(
            e.get("latency_ms", 0)
            for stap in self._tuner._stats.values()
            for e in stap
        )
        return results


    # ── GOAL EXECUTION (Phase 40: Swarm Sovereignty) ──

    async def execute_goal(
        self, goal: str, use_models: bool = False,
    ) -> List[SwarmPayload]:
        """Decomponeer + auction + parallel execute via TaskArbitrator.

        Flow:
            1. Arbitrator decomponeert goal in sub-taken
            2. Auction wijst agents toe (S = context_match / (load + 1))
            3. Parallel dispatch via asyncio.gather
            4. HallucinatieSchild gate (95% Barrière)
            5. Return samengevoegde SwarmPayloads

        Args:
            goal: High-level doelstelling.
            use_models: Als True, dispatch naar externe AI-modellen
                        via Generaal Mode (Phase 41).

        Returns:
            Lijst van SwarmPayloads (één per voltooide sub-taak).
        """
        try:
            from danny_toolkit.brain.arbitrator import get_arbitrator
        except ImportError:
            logger.debug("brain.arbitrator niet beschikbaar")
            return []

        arbitrator = get_arbitrator(brain=self.brain)

        # 1. Decompose
        manifest = await arbitrator.decompose(goal)

        # 2+3. Auction + Execute (Generaal Mode of Swarm Mode)
        if use_models:
            manifest = await arbitrator.execute_with_models(manifest)
        else:
            manifest = await arbitrator.execute(manifest, engine=self)

        # Collect resultaten
        results: List[SwarmPayload] = []
        for task in manifest.taken:
            if task.resultaat is not None and task.status == "done":
                results.append(task.resultaat)

        # 3.5 Synthesize — coherent antwoord
        synthese_text = arbitrator.synthesize(manifest)

        # 4. HallucinatieSchild — 95% Barrière
        try:
            from danny_toolkit.brain.hallucination_shield import (
                get_hallucination_shield,
            )
            schild = get_hallucination_shield()
            non_error = [r for r in results if r.type != "error"]
            if non_error:
                _goal_agents = list({
                    r.agent for r in non_error if r.agent
                })
                rapport = schild.beoordeel(
                    non_error, goal,
                    metadata={
                        "agents_involved": _goal_agents,
                        "sentinel_ok": True,
                    },
                )
                if rapport.geblokkeerd:
                    self._swarm_metrics["schild_blocks"] += 1
                    return [SwarmPayload(
                        agent="HallucinatieSchild",
                        type="text",
                        content=(
                            "Goal-output geblokkeerd door"
                            " HallucinatieSchild"
                            f" (score: {rapport.totaal_score:.2f})"
                        ),
                        display_text=(
                            "\u26a0\ufe0f Goal-resultaat niet"
                            " betrouwbaar genoeg."
                            " Probeer het doel"
                            " specifieker te stellen."
                        ),
                    )]
        except Exception as e:
            logger.debug("Goal HallucinatieSchild: %s", e)

        # Fallback: geen resultaten
        if not results:
            results.append(SwarmPayload(
                agent="Arbitrator",
                type="text",
                content=f"Goal kon niet worden uitgevoerd: {goal[:200]}",
                display_text=f"Goal '{goal[:80]}' leverde geen resultaten op.",
            ))

        return results


# ── SYNC WRAPPER ──

async def _run_with_cleanup(coro: Any) -> Any:
    """Run coroutine en sluit async clients voordat de loop stopt."""
    try:
        return await coro
    finally:
        try:
            from danny_toolkit.core.key_manager import get_key_manager
            km = get_key_manager()
            await km.close_all_clients()
        except Exception as e:
            logger.debug("Key manager cleanup on shutdown: %s", e)


def run_swarm_sync(
    user_input: str, brain: Any = None, callback: Any = None,
) -> List[SwarmPayload]:
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
        _run_with_cleanup(engine.run(user_input, callback))
    )


def run_pipeline_sync(
    taken: list, brain: Any = None, oracle: Any = None,
    callback: Any = None,
) -> list:
    """Sync wrapper voor execute_pipeline.

    Args:
        taken: lijst van taak-dicts.
        brain: PrometheusBrain instantie.
        oracle: OracleAgent instantie (optioneel).
        callback: Functie(str) voor live updates.

    Returns:
        Lijst van resultaat-dicts per taak.
    """
    engine = SwarmEngine(
        brain=brain, oracle=oracle,
    )
    return asyncio.run(
        _run_with_cleanup(engine.execute_pipeline(taken, callback))
    )
