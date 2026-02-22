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

import atexit
import asyncio
import hashlib
import json
import logging
import math
import re
import random
import sys
import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any

# Max workers voor de per-loop thread pool.
_SWARM_MAX_WORKERS = 6
from dataclasses import dataclass, field
from datetime import datetime

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# ── PER-AGENT PIPELINE METRICS (module-level singleton) ──

import threading as _threading

_AGENT_PIPELINE_METRICS: Dict[str, Dict[str, Any]] = {}
_METRICS_LOCK = _threading.Lock()


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


# ── CUSTOM EXCEPTIONS ──

class TaskVerificationError(Exception):
    """Fout bij verificatie van een swarm taak."""

    def __init__(
        self, bericht, taak=None,
        agent=None, payload=None,
    ):
        super().__init__(bericht)
        self.taak = taak
        self.agent = agent
        self.payload = payload


# ── CONFIG ──
from danny_toolkit.core.config import Config

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
    except Exception as e:
        logger.debug("Cortical log failed: %s", e)


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
    except Exception as e:
        logger.debug("Fact extraction failed: %s", e)


def _shutdown():
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
    """Agentic RAG: plan → zoek ChromaDB → synthetiseer.

    Stap 1: LLM genereert zoektermen (plan).
    Stap 2: ChromaDB doorzoeken + CorticalStack (execute).
    Stap 3: LLM schrijft rapport met bronnen.

    ChromaDB = primaire bron (ingest.py knowledge base).
    CorticalStack = secundaire bron (runtime events).
    """

    _collection = None  # Lazy ChromaDB connectie

    def _get_collection(self):
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

    def _search_chromadb(self, query, n_results=10):
        """Doorzoek ChromaDB met bronweging.

        Haalt meer resultaten op (n_results=10),
        herwaardeert scores (.py krijgt bonus,
        .json krijgt penalty), en retourneert
        de top 5.
        """
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

    def _get_cortical_stack(self):
        """Haal CorticalStack op (lazy)."""
        try:
            from danny_toolkit.brain.cortical_stack import (
                get_cortical_stack,
            )
            return get_cortical_stack()
        except Exception as e:
            logger.debug("CorticalStack laden mislukt: %s", e)
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

    async def process(self, task, brain=None):
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

    async def process(self, task, brain=None):
        from danny_toolkit.daemon.coherentie import (
            CoherentieMonitor,
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
                    "data": chart_data,
                },
            },
        )


class StrategistAgent(Agent):
    """Recursive planner: decompose, delegate, chain."""

    def _get_strategist(self):
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

    async def process(self, task, brain=None):
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
    """Autonomous skill forge-verify-execute loop."""

    def _get_artificer(self):
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

    async def process(self, task, brain=None):
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

    def _get_twin(self):
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

    async def process(self, task, brain=None):
        start_t = time.time()
        twin = self._get_twin()
        if twin is None:
            return SwarmPayload(
                agent=self.name, type="text",
                content="VirtualTwin niet beschikbaar",
                display_text="VirtualTwin niet beschikbaar",
            )
        result = await twin.consult(task)
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

    def __init__(self, name, role, model=None):
        super().__init__(name, role, model)
        from danny_toolkit.skills.pixel_eye import (
            PixelEye,
        )
        self.eye = PixelEye()

    async def process(self, task, brain=None):
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
            from danny_toolkit.brain.trinity_omega import (
                CosmicRole,
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

    def __init__(self, name, role, model=None):
        super().__init__(name, role, model)
        from kinesis import KineticUnit
        self.body = KineticUnit()
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

    async def process(self, task, brain=None):
        start_t = time.time()

        if not brain:
            return SwarmPayload(
                agent=self.name, type="text",
                content="Brain offline",
                display_text="Brain offline",
            )

        # 1. PLAN: Vertaal intentie naar acties
        from danny_toolkit.brain.trinity_omega import (
            CosmicRole,
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

    def __init__(self, governor=None):
        self._governor = governor
        self._compiled = [
            re.compile(p, re.IGNORECASE)
            for p in self._GEVAARLIJKE_PATRONEN
        ]

    def valideer(
        self, payload,
    ) -> dict:
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
    def _get_embed_fn(cls):
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
    def _bereken_profielen(cls):
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
    def _cosine_sim(vec_a, vec_b):
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
        synapse_bias: Dict[str, float] = None,
        exclude_agents: set = None,
    ) -> List[str]:
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

    def __init__(self):
        self._stats = {}
        self._call_count = {}

    def _ensure_stap(self, stap):
        """Maak stats aan voor een stap."""
        if stap not in self._stats:
            self._stats[stap] = deque(
                maxlen=self.VENSTER
            )
            self._call_count[stap] = 0

    def registreer(self, stap, latency_ms, **metrics):
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

    def mag_skippen(self, stap) -> bool:
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

    def reset(self):
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

    def __init__(self, brain=None, oracle=None):
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
            "phantom_predictions": 0,
            "phantom_hits": 0,
            "agent_errors": 0,
            "twin_consultations": 0,
        }

        # Echo Guard — dedup gate (hash, timestamp)
        self._recent_queries: deque = deque(maxlen=50)

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

        # Key manager status
        try:
            from danny_toolkit.core.key_manager import (
                get_key_manager,
            )
            stats["key_manager"] = get_key_manager().get_status()
        except ImportError:
            stats["key_manager"] = {}

        return stats

    def _record_agent_metric(self, agent_naam, elapsed_ms, error=None):
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

    async def _timed_dispatch(self, agent, agent_input):
        """Wrap agent.process() met timing + error handling."""
        t0 = time.time()
        try:
            result = await agent.process(agent_input, self.brain)
            elapsed_ms = (time.time() - t0) * 1000
            self._record_agent_metric(agent.name, elapsed_ms)
            return result
        except Exception as e:
            elapsed_ms = (time.time() - t0) * 1000
            self._record_agent_metric(agent.name, elapsed_ms, error=e)
            logger.warning("Agent %s fout: %s", agent.name, e)
            _log_to_cortical(
                agent.name, "agent_error",
                {"error": str(e)[:200],
                 "error_type": type(e).__name__,
                 "elapsed_ms": round(elapsed_ms, 1)},
            )
            return SwarmPayload(
                agent=agent.name,
                type="error",
                content=f"[{agent.name}] Fout: {e}",
                display_text=f"Agent {agent.name} fout: {e}",
                metadata={"error_type": type(e).__name__},
            )

    @property
    def _governor(self):
        """Lazy OmegaGovernor voor rate limit tracking."""
        if not hasattr(self, "_gov_instance"):
            from danny_toolkit.brain.governor import (
                OmegaGovernor,
            )
            self._gov_instance = OmegaGovernor()
        return self._gov_instance

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

        }

    # ── Lazy Oracle Property ──

    @property
    def oracle(self):
        """Lazy OracleAgent — geen import overhead."""
        if self._oracle is None:
            from danny_toolkit.core.oracle import (
                OracleAgent,
            )
            self._oracle = OracleAgent(persist=False)
        return self._oracle

    @property
    def _tribunal(self):
        """Lazy AdversarialTribunal."""
        if not hasattr(self, "_tribunal_instance"):
            try:
                from danny_toolkit.brain.adversarial_tribunal import (
                    AdversarialTribunal,
                )
                self._tribunal_instance = (
                    AdversarialTribunal(brain=self.brain)
                )
            except Exception as e:
                logger.debug("AdversarialTribunal laden mislukt: %s", e)
                self._tribunal_instance = None
        return self._tribunal_instance

    @property
    def synapse(self):
        """Lazy TheSynapse — synaptic pathway plasticity."""
        if not hasattr(self, "_synapse_instance"):
            try:
                from danny_toolkit.brain.synapse import (
                    TheSynapse,
                )
                self._synapse_instance = TheSynapse()
            except Exception as e:
                logger.debug(
                    "TheSynapse laden mislukt: %s", e,
                )
                self._synapse_instance = None
        return self._synapse_instance

    @property
    def phantom(self):
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
    def virtual_twin(self):
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
        self, results, user_input, callback=None,
    ):
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
                verdict = await tribunal.adeliberate(
                    user_input, content,
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

    def add_hook(self, event, callback):
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

    def _trigger_hooks(self, hooks, *args):
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
        self, user_input: str, max_fragmenten=3,
        max_chars=300,
    ) -> List[str]:
        """Haal relevante context op via ChromaDB.

        Lightweight vector search (geen LLM).
        Retourneert max 3 fragmenten van 300 chars.

        Args:
            user_input: Gebruikersinput.
            max_fragmenten: Max aantal fragmenten.
            max_chars: Max tekens per fragment.

        Returns:
            Lijst van context strings.
        """
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
                for doc_list in resultaten["documents"]:
                    for doc in doc_list:
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
        user_input: str, callback=None,
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
        self, taak, payloads,
    ):
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
    def _is_rate_limit_error(error):
        """Detecteer rate limit fout (429/quota)."""
        fout_tekst = str(error).lower()
        patronen = [
            "429", "rate_limit", "rate limit",
            "ratelimit", "too many requests",
            "quota exceeded",
        ]
        return any(p in fout_tekst for p in patronen)

    async def _handle_swarm_failure(
        self, error, taak, callback=None,
    ):
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
        def log(msg):
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
        self, taken, callback=None,
    ):
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
        def log(msg):
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
            pass

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
                 "synapse_bias": bool(bias)},
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
        self, user_input: str, callback=None,
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
        def log(msg):
            if callback:
                callback(msg)

        # Beperk thread pool voor deze event loop
        loop = asyncio.get_running_loop()
        loop.set_default_executor(ThreadPoolExecutor(
            max_workers=_SWARM_MAX_WORKERS,
            thread_name_prefix="swarm",
        ))

        t = self._tuner

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
                log(
                    f"\u274c Governor: BLOCKED"
                    f" \u2014 {reason}"
                )
                self._swarm_metrics[
                    "governor_blocks"
                ] += 1
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
                logger.debug(
                    "Phantom pre-warm check: %s", e,
                )

        # 4. MEMEX Context (tunable)
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

        # 5. Nexus Route (NOOIT skippen)
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

        # 6. Parallel executie via asyncio.gather
        #    MEMEX context voor alle agents behalve
        #    MEMEX zelf (doet eigen RAG)
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
                self._timed_dispatch(
                    agent, agent_input,
                )
            )

        results = await asyncio.gather(*tasks)
        t.registreer(
            "execute",
            (time.time() - t0) * 1000,
        )

        # Tel agent errors
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

        # 7. SENTINEL Validate (tunable)
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

        # Synapse: record interaction trace
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

        log("\u2705 SWARM COMPLETE")
        self._query_count += 1
        self._total_time += sum(
            e.get("latency_ms", 0)
            for stap in self._tuner._stats.values()
            for e in stap
        )
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


def run_pipeline_sync(
    taken, brain=None, oracle=None,
    callback=None,
):
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
        engine.execute_pipeline(taken, callback)
    )
