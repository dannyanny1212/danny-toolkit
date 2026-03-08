# danny_toolkit/brain/arbitrator.py
"""
TaskArbitrator — Swarm Sovereignty (Phase 40, Invention #24).
=============================================================
Autonome goal decomposition + auction-based agent assignment + parallel execution.

Flow:
    1. DECOMPOSE  — Goal → sub-taken via LLM
    2. AUCTION    — Agents bieden op taken: S = context_match / (load + 1)
    3. EXECUTE    — Parallel dispatch via asyncio.gather
    4. SYNTHESIZE — Resultaten samengevoegd tot coherent antwoord

Gebruik:
    from danny_toolkit.brain.arbitrator import get_arbitrator

    arb = get_arbitrator()
    manifest = await arb.decompose("Audit de BlackBox en herstel zwakke links")
    manifest = await arb.execute(manifest)
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from danny_toolkit.brain.model_sync import ModelBid

from danny_toolkit.core.config import Config
from danny_toolkit.core.utils import Kleur

logger = logging.getLogger(__name__)

try:
    from groq import Groq
    HAS_GROQ = True
except ImportError:
    HAS_GROQ = False

try:
    from danny_toolkit.core.key_manager import get_key_manager
    HAS_KEY_MANAGER = True
except ImportError:
    HAS_KEY_MANAGER = False

try:
    from danny_toolkit.core.neural_bus import get_bus, EventTypes
    HAS_BUS = True
except ImportError:
    HAS_BUS = False


# ── Datamodellen ──

@dataclass
class SwarmTask:
    """Eén sub-taak binnen een GoalManifest."""
    task_id: str
    beschrijving: str
    categorie: str
    prioriteit: int = 1
    toegewezen_agent: str = ""
    status: str = "pending"
    resultaat: Any = None  # SwarmPayload na executie

    def to_dict(self) -> dict:
        """Serialiseer SwarmTask naar dict (voor JSON/API)."""
        return {
            "task_id": self.task_id,
            "beschrijving": self.beschrijving,
            "categorie": self.categorie,
            "prioriteit": self.prioriteit,
            "toegewezen_agent": self.toegewezen_agent,
            "status": self.status,
            "resultaat_preview": (
                str(getattr(self.resultaat, "display_text", ""))[:200]
                if self.resultaat else ""
            ),
        }


@dataclass
class GoalManifest:
    """Container voor een volledig goal met sub-taken."""
    goal: str
    taken: List[SwarmTask] = field(default_factory=list)
    status: str = "planning"
    trace_id: str = ""
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        """Serialiseer GoalManifest naar dict (voor JSON/API)."""
        return {
            "goal": self.goal,
            "status": self.status,
            "trace_id": self.trace_id,
            "taken": [t.to_dict() for t in self.taken],
            "created_at": self.created_at,
        }


@dataclass
class AuctionBid:
    """Resultaat van een agent-auction voor een taak."""
    agent: str
    score: float
    context_match: float
    current_load: float


# ── Decompose Prompt ──

_DECOMPOSE_SYSTEM = (
    "Je bent een taak-ontleder. Decomponeer het gegeven doel in 2-5 concrete, "
    "uitvoerbare sub-taken. Elke sub-taak moet een duidelijke beschrijving en "
    "categorie hebben.\n\n"
    "Categorieën: research, code, verificatie, pruning, analyse, reparatie, monitoring\n\n"
    "Antwoord ALLEEN met een JSON array:\n"
    '[{"beschrijving": "...", "categorie": "...", "prioriteit": 1}]\n\n'
    "Prioriteit: 1=hoog, 2=middel, 3=laag.\n"
    "Geen uitleg, geen markdown, alleen de JSON array."
)


# ── TaskArbitrator ──

class TaskArbitrator:
    """
    THE TASK ARBITRATOR — Swarm Sovereignty Engine
    ===============================================
    Decomponeert high-level goals in sub-taken, wijst ze via auction toe
    aan de best passende agents, en voert ze parallel uit.

    Formule:
        S_agent = context_match / (current_load + 1)
    """

    def __init__(self, brain=None):
        """### Docstring

Initializes an Arbitrator instance.

#### Args

*   **brain** (optional): The brain component associated with the Arbitrator. Defaults to `None`.
*   **None**: No explicit return value.

#### Attributes

*   **brain**: The brain component associated with the Arbitrator.
*   **_lock**: A threading lock for synchronization.
*   **_stats**: A dictionary containing statistics on the Arbitrator's performance, including:
    *   **goals_processed**: The number of goals processed.
    *   **tasks_decomposed**: The number of tasks decomposed.
    *   **auctions_held**: The number of auctions held.
    *   **tasks_completed**: The number of tasks completed.
    *   **tasks_failed**: The number of tasks failed.
    *   **model_auctions_held**: The number of model auctions held (Phase 41: Generaal Mode).
    *   **model_tasks_completed**: The number of model tasks completed (Phase 41: Generaal Mode).
    *   **model_tasks_failed**: The number of model tasks failed (Phase 41: Generaal Mode).
    *   **barrier_rejections**: The number of barrier rejections.
*   **_synapse**: A synapse component (not initialized in `__init__`).
*   **_waakhuis**: A waakhuis component (not initialized in `__init__`).
*   **_groq_client**: A Groq client instance, initialized lazily if possible.

#### Notes

The Groq client is initialized lazily, attempting to create a synchronous client using `AgentKeyManager` if available, and falling back to using an API key from the environment if not. Any exceptions during initialization are caught and logged at the debug level."""
        self.brain = brain
        self._lock = threading.Lock()
        self._stats = {
            "goals_processed": 0,
            "tasks_decomposed": 0,
            "auctions_held": 0,
            "tasks_completed": 0,
            "tasks_failed": 0,
            # Phase 41: Generaal Mode
            "model_auctions_held": 0,
            "model_tasks_completed": 0,
            "model_tasks_failed": 0,
            "barrier_rejections": 0,
        }
        self._synapse = None
        self._waakhuis = None
        self._groq_client = None

        # Lazy Groq client
        try:
            if HAS_KEY_MANAGER:
                km = get_key_manager()
                self._groq_client = km.create_sync_client("Arbitrator")
            if not self._groq_client and HAS_GROQ:
                self._groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        except Exception as e:
            logger.debug("Arbitrator Groq client init: %s", e)

    def _get_synapse(self):
        """Lazy TheSynapse."""
        if self._synapse is None:
            try:
                from danny_toolkit.brain.synapse import TheSynapse
                self._synapse = TheSynapse()
            except Exception as e:
                logger.debug("Synapse init: %s", e)
        return self._synapse

    def _get_waakhuis(self):
        """Lazy WaakhuisMonitor."""
        if self._waakhuis is None:
            try:
                from danny_toolkit.brain.waakhuis import get_waakhuis
                self._waakhuis = get_waakhuis()
            except Exception as e:
                logger.debug("Waakhuis init: %s", e)
        return self._waakhuis

    # ── DECOMPOSE ──

    async def decompose(self, goal: str) -> GoalManifest:
        """Decomponeer een goal string in sub-taken via LLM.

        Returns:
            GoalManifest met SwarmTask objecten.
        """
        manifest = GoalManifest(
            goal=goal,
            trace_id=uuid.uuid4().hex[:12],
        )

        print(f"\n{Kleur.BLAUW}[ARBITRATOR]{Kleur.RESET} Decomposing: {goal[:80]}")

        tasks_json = await self._call_decompose_llm(goal)
        tasks = self._parse_tasks(tasks_json, goal)

        manifest.taken = tasks
        manifest.status = "decomposed"

        with self._lock:
            self._stats["goals_processed"] += 1
            self._stats["tasks_decomposed"] += len(tasks)

        for t in tasks:
            print(f"  {Kleur.GEEL}[TASK]{Kleur.RESET} {t.task_id}: {t.beschrijving[:60]}"
                  f" ({t.categorie})")

        return manifest

    async def _call_decompose_llm(self, goal: str) -> str:
        """Roep LLM aan voor goal decomposition."""
        if not self._groq_client:
            return "[]"

        try:
            response = await asyncio.to_thread(
                self._groq_client.chat.completions.create,
                model=Config.LLM_FALLBACK_MODEL,
                messages=[
                    {"role": "system", "content": _DECOMPOSE_SYSTEM},
                    {"role": "user", "content": goal},
                ],
                max_tokens=500,
                temperature=0.3,
            )
            return response.choices[0].message.content or "[]"
        except Exception as e:
            logger.debug("Decompose LLM call failed: %s", e)
            return "[]"

    def _parse_tasks(self, raw: str, goal: str) -> List[SwarmTask]:
        """Parse JSON array naar SwarmTask lijst. Fallback: single task."""
        try:
            # Extract JSON array uit response
            match = re.search(r'\[.*\]', raw, re.DOTALL)
            if match:
                data = json.loads(match.group())
            else:
                data = json.loads(raw)

            if not isinstance(data, list) or len(data) == 0:
                raise ValueError("Geen geldige array")

            tasks = []
            for item in data[:5]:  # Max 5 taken
                tasks.append(SwarmTask(
                    task_id=uuid.uuid4().hex[:8],
                    beschrijving=item.get("beschrijving", str(item)),
                    categorie=item.get("categorie", "analyse"),
                    prioriteit=int(item.get("prioriteit", 2)),
                ))
            return tasks

        except (json.JSONDecodeError, ValueError, TypeError) as e:
            logger.debug("Task parse fallback (raw=%s...): %s", raw[:80], e)
            return [SwarmTask(
                task_id=uuid.uuid4().hex[:8],
                beschrijving=goal,
                categorie="analyse",
                prioriteit=1,
            )]

    # ── AUCTION ──

    def auction(self, task: SwarmTask, available_agents: List[str] = None) -> AuctionBid:
        """Auction Loop: vind de best passende agent voor een taak.

        Formule: S_agent = context_match / (current_load + 1)
        """
        with self._lock:
            self._stats["auctions_held"] += 1

        # Verzamel biedingen
        bids: List[AuctionBid] = []
        synapse = self._get_synapse()
        waakhuis = self._get_waakhuis()

        # Context match via Synapse routing bias
        bias_map: Dict[str, float] = {}
        if synapse:
            try:
                bias_map = synapse.get_routing_bias(task.beschrijving)
            except Exception as e:
                logger.debug("Synapse routing bias: %s", e)

        # Fallback: AdaptiveRouter als Synapse geen data heeft
        if not bias_map:
            try:
                from danny_toolkit.core.engine import AdaptiveRouter
                router = AdaptiveRouter()
                routed = router.route(task.beschrijving)
                for i, agent in enumerate(routed):
                    bias_map[agent] = max(0.5, 1.0 - i * 0.15)
            except Exception as e:
                logger.debug("AdaptiveRouter fallback: %s", e)

        # Filter op beschikbare agents
        if available_agents:
            bias_map = {k: v for k, v in bias_map.items() if k in available_agents}

        # Bied per agent
        for agent, context_match in bias_map.items():
            current_load = 0.0
            if waakhuis:
                try:
                    rapport = waakhuis.latency_rapport(agent)
                    current_load = rapport.get("count", 0) / 100.0
                except Exception as e:
                    logger.debug("Waakhuis load voor %s: %s", agent, e)

            score = context_match / (current_load + 1.0)
            bids.append(AuctionBid(
                agent=agent,
                score=round(score, 4),
                context_match=round(context_match, 4),
                current_load=round(current_load, 4),
            ))

        # Sorteer op score, hoogste wint
        bids.sort(key=lambda b: b.score, reverse=True)

        if bids:
            winner = bids[0]
            print(f"  {Kleur.GROEN}[AUCTION]{Kleur.RESET} {task.task_id} → "
                  f"{winner.agent} (S={winner.score:.3f})")
            return winner

        # Geen bids → fallback naar ECHO
        return AuctionBid(agent="ECHO", score=0.0, context_match=0.0, current_load=0.0)

    # ── EXECUTE ──

    async def execute(self, manifest: GoalManifest, engine=None) -> GoalManifest:
        """Voer alle taken in een manifest parallel uit.

        Args:
            manifest: GoalManifest met gedecomponeerde taken.
            engine: Optioneel SwarmEngine instance voor dispatch.
        """
        manifest.status = "executing"

        print(f"\n{Kleur.BLAUW}[ARBITRATOR]{Kleur.RESET} Executing "
              f"{len(manifest.taken)} tasks...")

        # Auction: wijs agents toe
        for task in manifest.taken:
            bid = self.auction(task)
            task.toegewezen_agent = bid.agent
            task.status = "running"

        # Parallel dispatch
        if engine is None:
            try:
                from danny_toolkit.core.engine import SwarmEngine
                engine = SwarmEngine(self.brain)
            except Exception as e:
                logger.debug("SwarmEngine init for execute: %s", e)
                manifest.status = "failed"
                return manifest

        async def _dispatch_task(task: SwarmTask):
            """Dispatch een enkele taak naar de toegewezen agent."""
            try:
                result = await engine._timed_dispatch(
                    task.toegewezen_agent,
                    task.beschrijving,
                    trace_id=manifest.trace_id,
                )
                task.resultaat = result
                task.status = "done"
                with self._lock:
                    self._stats["tasks_completed"] += 1
            except Exception as e:
                logger.debug("Task %s dispatch failed: %s", task.task_id, e)
                task.status = "failed"
                with self._lock:
                    self._stats["tasks_failed"] += 1

        # asyncio.gather voor parallelle uitvoering
        tasks = [asyncio.create_task(_dispatch_task(t))
                 for t in manifest.taken]
        await asyncio.gather(*tasks)

        # Status bepalen
        failed = sum(1 for t in manifest.taken if t.status == "failed")
        if failed == len(manifest.taken):
            manifest.status = "failed"
        elif failed > 0:
            manifest.status = "partial"
        else:
            manifest.status = "done"

        print(f"  {Kleur.GROEN}[ARBITRATOR]{Kleur.RESET} "
              f"Done: {len(manifest.taken) - failed}/{len(manifest.taken)} succeeded")

        # Log naar CorticalStack
        self._log_to_cortical(manifest)

        # Publiceer GOAL_COMPLETED op NeuralBus
        self._publiceer_event(manifest)

        return manifest

    def synthesize(self, manifest: GoalManifest) -> str:
        """Synthetiseer alle resultaten tot één coherent antwoord."""
        parts = []
        for task in manifest.taken:
            if task.resultaat and task.status == "done":
                text = str(
                    getattr(task.resultaat, "display_text", "")
                    or getattr(task.resultaat, "content", "")
                )
                if text.strip():
                    parts.append(f"[{task.toegewezen_agent}] {text.strip()}")

        if not parts:
            return f"Goal '{manifest.goal}' kon niet worden uitgevoerd."

        return "\n\n".join(parts)

    # ── MODEL AUCTION (Phase 41: Generaal Mode) ──

    def model_auction(
        self, task: "SwarmTask", exclude: List[str] = None,
    ) -> Optional["ModelBid"]:
        """Model Auction: vind het beste externe model voor een taak.

        Formule: S_model = (capability_match × success_rate) / (cost_tier + latency_class)

        Args:
            task: De SwarmTask waarvoor een model gezocht wordt.
            exclude: Lijst van model_id's die uitgesloten worden (ontslagen).

        Returns:
            ModelBid of None als geen modellen beschikbaar zijn.
        """
        try:
            from danny_toolkit.brain.model_sync import (
                ModelBid, ModelCapability, get_model_registry,
            )
        except ImportError:
            logger.debug("model_sync niet beschikbaar")
            return None

        with self._lock:
            self._stats["model_auctions_held"] += 1

        registry = get_model_registry()
        available = registry.get_available()
        exclude = exclude or []

        # Categorie → capability mapping
        cat_map = {
            "code": ModelCapability.CODE,
            "research": ModelCapability.RESEARCH,
            "analyse": ModelCapability.ANALYSE,
            "creatief": ModelCapability.CREATIEF,
            "verificatie": ModelCapability.VERIFICATIE,
        }
        required_cap = cat_map.get(task.categorie)

        bids: List["ModelBid"] = []
        for worker in available:
            if worker.profile.model_id in exclude:
                continue

            # Capability match
            if required_cap and required_cap in worker.profile.capabilities:
                cap_match = 1.0
            else:
                cap_match = 0.5

            # S_model = (cap_match × success_rate) / (cost_tier + latency_class)
            sr = worker.success_rate()
            cost = worker.profile.cost_tier
            latency = worker.profile.latency_class
            score = (cap_match * sr) / (cost + latency)

            bids.append(ModelBid(
                profile=worker.profile,
                worker=worker,
                score=round(score, 4),
                capability_match=cap_match,
            ))

        # Sorteer op score, hoogste wint
        bids.sort(key=lambda b: b.score, reverse=True)

        if bids:
            winner = bids[0]
            print(f"  {Kleur.GEEL}[MODEL AUCTION]{Kleur.RESET} {task.task_id} → "
                  f"{winner.profile.provider}/{winner.profile.model_id} "
                  f"(S={winner.score:.3f})")

            # Phase 42: Observatory Sync — registreer veiling
            self._record_to_observatory(
                task, winner, deelnemers=len(bids),
            )

            return winner

        return None

    # ── EXECUTE WITH MODELS (Phase 41: Generaal Mode) ──

    async def execute_with_models(
        self, manifest: "GoalManifest", retry_limit: int = 2,
    ) -> "GoalManifest":
        """Generaal Mode: dispatcht taken naar externe AI-modellen.

        Trust, but Verify — elk modelresultaat gaat door de HallucinatieSchild
        95% Barrière. Gefaalde modellen worden ontslagen en vervangen.

        Args:
            manifest: GoalManifest met gedecomponeerde taken.
            retry_limit: Max herhaalpogingen per taak (model wisselen).

        Returns:
            GoalManifest met resultaten.
        """
        manifest.status = "executing_models"

        print(f"\n{Kleur.BLAUW}[GENERAAL]{Kleur.RESET} Dispatching "
              f"{len(manifest.taken)} tasks to external models...")

        # Lazy imports
        shield = None
        try:
            from danny_toolkit.brain.hallucination_shield import (
                get_hallucination_shield,
            )
            shield = get_hallucination_shield()
        except Exception as e:
            logger.debug("HallucinatieSchild voor Generaal: %s", e)

        async def _dispatch_model_task(task: SwarmTask):
            """Dispatch één taak naar externe modellen met retry/fire logic."""
            tried_models: List[str] = []

            for attempt in range(retry_limit + 1):
                bid = self.model_auction(task, exclude=tried_models)
                if not bid:
                    # Geen modellen meer → taak faalt
                    task.status = "failed"
                    with self._lock:
                        self._stats["model_tasks_failed"] += 1
                    break

                response = await bid.worker.generate(task.beschrijving)

                # 95% Barrière via HallucinatieSchild
                if shield and response.content:
                    try:
                        # Importeer SwarmPayload lokaal om circulaire imports te vermijden
                        from danny_toolkit.core.engine import SwarmPayload
                        probe = SwarmPayload(
                            agent=f"EXT:{response.provider}/{response.model_id}",
                            type="text",
                            content=response.content,
                            display_text=response.content,
                        )
                        rapport = shield.beoordeel([probe], task.beschrijving)
                        response.barrier_score = rapport.totaal_score
                        response.passed_barrier = not rapport.geblokkeerd

                        if not rapport.geblokkeerd:
                            # Passed 95% Barrier
                            bid.worker._record_success()
                            task.resultaat = response
                            task.status = "done"
                            with self._lock:
                                self._stats["model_tasks_completed"] += 1
                            break

                        # Ontslagen — model faalde de Barrière
                        bid.worker._record_barrier_rejection()
                        tried_models.append(bid.profile.model_id)
                        with self._lock:
                            self._stats["barrier_rejections"] += 1
                        logger.info(
                            "Model %s ontslagen (score=%.3f), retry %d/%d",
                            bid.profile.model_id, rapport.totaal_score,
                            attempt + 1, retry_limit,
                        )
                    except Exception as e:
                        logger.debug("Barrière check: %s", e)
                        # Bij fout in schild → neem response aan
                        bid.worker._record_success()
                        task.resultaat = response
                        task.status = "done"
                        with self._lock:
                            self._stats["model_tasks_completed"] += 1
                        break
                elif response.content:
                    # Geen schild → neem response aan
                    bid.worker._record_success()
                    task.resultaat = response
                    task.status = "done"
                    with self._lock:
                        self._stats["model_tasks_completed"] += 1
                    break
                else:
                    # Lege response → probeer volgend model
                    tried_models.append(bid.profile.model_id)
                    continue
            else:
                # Alle retries uitgeput
                if task.status != "done":
                    task.status = "failed"
                    with self._lock:
                        self._stats["model_tasks_failed"] += 1

        # Parallel dispatch via asyncio.gather
        tasks = [asyncio.create_task(_dispatch_model_task(t))
                 for t in manifest.taken]
        await asyncio.gather(*tasks)

        # Status bepalen
        failed = sum(1 for t in manifest.taken if t.status == "failed")
        done = sum(1 for t in manifest.taken if t.status == "done")
        if failed == len(manifest.taken):
            manifest.status = "failed"
        elif failed > 0:
            manifest.status = "partial"
        else:
            manifest.status = "done"

        print(f"  {Kleur.GROEN}[GENERAAL]{Kleur.RESET} "
              f"Done: {done}/{len(manifest.taken)} succeeded")

        # Log naar CorticalStack
        self._log_to_cortical_model(manifest)

        # Publiceer MODEL_TASK_COMPLETED op NeuralBus
        self._publiceer_model_event(manifest)

        return manifest

    def _log_to_cortical_model(self, manifest: GoalManifest):
        """Log Generaal Mode manifest naar CorticalStack."""
        try:
            from danny_toolkit.brain.cortical_stack import get_cortical_stack
            stack = get_cortical_stack()
            stack.log_event(
                actor="generaal",
                action="model_goal_executed",
                source="arbitrator",
                data={
                    "goal": manifest.goal[:200],
                    "tasks": len(manifest.taken),
                    "status": manifest.status,
                    "models": [
                        f"{getattr(t.resultaat, 'provider', '?')}"
                        f"/{getattr(t.resultaat, 'model_id', '?')}"
                        for t in manifest.taken if t.resultaat
                    ],
                },
            )
        except Exception as e:
            logger.debug("CorticalStack log (Generaal): %s", e)

    def _publiceer_model_event(self, manifest: GoalManifest):
        """Publiceer MODEL_TASK_COMPLETED event op NeuralBus."""
        if not HAS_BUS:
            return
        try:
            event_type = getattr(
                EventTypes, "MODEL_TASK_COMPLETED", EventTypes.SYSTEM_EVENT,
            )
            get_bus().publish(
                event_type,
                {
                    "goal": manifest.goal[:200],
                    "status": manifest.status,
                    "tasks": len(manifest.taken),
                },
                bron="generaal",
            )
        except Exception as e:
            logger.debug("NeuralBus publish (Generaal): %s", e)

    # ── LOGGING ──

    def _log_to_cortical(self, manifest: GoalManifest):
        """Log manifest naar CorticalStack."""
        try:
            from danny_toolkit.brain.cortical_stack import get_cortical_stack
            stack = get_cortical_stack()
            stack.log_event(
                actor="arbitrator",
                action="goal_executed",
                source="arbitrator",
                data={
                    "goal": manifest.goal[:200],
                    "tasks": len(manifest.taken),
                    "status": manifest.status,
                    "agents": [t.toegewezen_agent for t in manifest.taken],
                },
            )
        except Exception as e:
            logger.debug("CorticalStack log: %s", e)

    def _publiceer_event(self, manifest: GoalManifest):
        """Publiceer GOAL_COMPLETED event op NeuralBus."""
        if not HAS_BUS:
            return
        try:
            event_type = getattr(EventTypes, "GOAL_COMPLETED", EventTypes.SYSTEM_EVENT)
            get_bus().publish(
                event_type,
                {
                    "goal": manifest.goal[:200],
                    "status": manifest.status,
                    "tasks": len(manifest.taken),
                    "agents": [t.toegewezen_agent for t in manifest.taken],
                },
                bron="arbitrator",
            )
        except Exception as e:
            logger.debug("NeuralBus publish: %s", e)

    # ── OBSERVATORY SYNC (Phase 42) ──

    def _record_to_observatory(
        self, task: SwarmTask, winner, deelnemers: int,
        barrier_pass: bool = None,
    ):
        """Registreer veiling bij ObservatorySync (Phase 42)."""
        try:
            from danny_toolkit.brain.observatory_sync import get_observatory_sync
            obs = get_observatory_sync()
            obs.record_auction(
                task_id=task.task_id,
                task_categorie=task.categorie,
                winnaar_provider=winner.profile.provider,
                winnaar_model_id=winner.profile.model_id,
                winnaar_score=winner.score,
                deelnemers=deelnemers,
                barrier_pass=barrier_pass,
            )
        except Exception as e:
            logger.debug("ObservatorySync record_auction: %s", e)

    # ── STATS ──

    def get_stats(self) -> dict:
        """Return arbitrator statistieken."""
        with self._lock:
            return dict(self._stats)


# ── Singleton Factory ──

_arbitrator_instance: Optional["TaskArbitrator"] = None
_arbitrator_lock = threading.Lock()


def get_arbitrator(brain=None) -> "TaskArbitrator":
    """Return the process-wide TaskArbitrator singleton (double-checked locking)."""
    global _arbitrator_instance
    if _arbitrator_instance is None:
        with _arbitrator_lock:
            if _arbitrator_instance is None:
                _arbitrator_instance = TaskArbitrator(brain=brain)
    return _arbitrator_instance
