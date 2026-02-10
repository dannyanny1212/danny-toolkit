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
import base64
import json
import re
import random
import time
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
        try:
            import chromadb
            from chromadb.utils.embedding_functions import (
                SentenceTransformerEmbeddingFunction,
            )
            from pathlib import Path

            chroma_dir = str(
                Path(__file__).parent
                / "data" / "rag" / "chromadb"
            )
            client = chromadb.PersistentClient(
                path=chroma_dir
            )
            embed_fn = (
                SentenceTransformerEmbeddingFunction(
                    model_name="all-MiniLM-L6-v2"
                )
            )
            self._collection = (
                client.get_collection(
                    name="danny_knowledge",
                    embedding_function=embed_fn,
                )
            )
            return self._collection
        except Exception:
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
        except Exception:
            return [], []

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
            f"Vraag: '{task}'\n"
            "Geef 3 zoektermen voor een"
            " vector database. Behoud de"
            " naam uit de vraag.\n"
            'Alleen JSON: ["term1","term2","term3"]'
        )
        plan_raw, _, _ = await asyncio.to_thread(
            brain._execute_with_role,
            self.cosmic_role, plan_prompt,
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
            except Exception:
                pass

        if all_fragments:
            context = "\n".join(
                all_fragments[:15]
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


class PixelAgent(Agent):
    """THE EYES: Multimodal Vision Agent.

    Maakt screenshots en analyseert ze via Brain.
    Closed Loop: Legion doet → Pixel kijkt →
    Brain oordeelt → Legion corrigeert.

    Vision models (LLaVA/GPT-4o) kunnen later
    de simulatie vervangen.
    """

    VISION_TRIGGERS = [
        "kijk", "zie", "screenshot", "check",
        "bekijk", "toon scherm", "wat zie",
    ]

    def __init__(self, name, role, model=None):
        super().__init__(name, role, model)
        from kinesis import KineticUnit
        self.eyes = KineticUnit()

    def _encode_image(self, image_path):
        """Encode screenshot als base64 (voor vision API)."""
        with open(image_path, "rb") as f:
            return base64.b64encode(
                f.read()
            ).decode("utf-8")

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

        # 1. ACTIE: Kijk naar het scherm
        img_path = await asyncio.to_thread(
            self.eyes.capture_screen
        )

        # 2. PERCEPTIE: Analyseer via LLaVA (True Sight)
        analysis = None
        vision_status = "unknown"

        try:
            import ollama as _ollama

            vision_prompt = (
                "Analyseer dit beeld in detail."
                f" De gebruiker vraagt: '{task}'."
                " Als je tekst ziet, lees die"
                " letterlijk voor. Antwoord"
                " in het Nederlands."
            )

            response = await asyncio.to_thread(
                _ollama.chat,
                model="llava",
                messages=[{
                    "role": "user",
                    "content": vision_prompt,
                    "images": [img_path],
                }],
            )
            analysis = response.message.content
            vision_status = "Real Vision (LLaVA)"

        except Exception as e:
            # Fallback: Brain tekst-analyse
            vision_status = f"LLaVA fallback: {e}"
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
                result, _, _ = (
                    await asyncio.to_thread(
                        brain._execute_with_role,
                        CosmicRole.PIXEL,
                        fallback_prompt,
                    )
                )
                analysis = str(result) if result else None
                vision_status = "Brain fallback"
            except Exception:
                pass

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
    """

    def __init__(self, name, role, model=None):
        super().__init__(name, role, model)
        from kinesis import KineticUnit
        self.body = KineticUnit()

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
        "LEGION": [
            "open", "start", "launch", "typ",
            "app", "scherm", "pc", "notepad",
            "calculator", "chrome", "spotify",
            "screenshot",
        ],
        "CHRONOS_AGENT": [
            "schedule", "cronjob", "timer", "ritme",
            "planning", "agenda", "deadline",
            "wanneer", "herinnering",
        ],
        "PIXEL": [
            "help", "uitleg", "interface", "praat",
            "emotie", "gevoel", "dashboard", "menu",
            "teken", "visualiseer", "kijk", "zie",
            "bekijk", "check scherm", "wat zie",
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
            "LEGION": LegionAgent(
                "Legion", "Infrastructure",
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
