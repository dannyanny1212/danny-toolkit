"""
Ouroboros — Self-Healing Pipeline (Phase 57, Quest 5)
=====================================================
Catches agent failures in the SwarmEngine and dispatches the Artificer
to forge a hotfix or alternative tool invocation in the sandbox.

Veiligheidsmaatregelen:
- recovery_depth gate: max 1 self-heal poging per pipeline run
  (voorkomt oneindige crash-patch-crash loops)
- Artificer draait in sandbox — geen directe systeemwijzigingen
- Hebbian consequentie: failed agent krijgt -0.20, Artificer +0.25 bij succes
- CorticalStack logging van elke heal-poging (immuungeheugen)
- NeuralBus events voor dashboard awareness

Gebruik:
    from danny_toolkit.core.ouroboros import get_ouroboros
    ouroboros = get_ouroboros()
    result = await ouroboros.handle_exception("Iolaax", traceback_str, "original task")
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# ── Hebbian penalty/boost constants ─────────────────────────────
FAILURE_PENALTY = -0.20     # Zware straf voor falende agent
SAVIOUR_BOOST = 0.25        # Beloning voor succesvolle Artificer patch
MAX_RECOVERY_DEPTH = 1      # Maximaal 1 self-heal poging per run


@dataclass
class HealResult:
    """Resultaat van een Ouroboros self-heal poging."""

    success: bool
    failed_agent: str
    original_task: str
    heal_output: str = ""
    depth: int = 0
    elapsed_s: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialiseer naar dict voor CorticalStack/API."""
        return {
            "success": self.success,
            "failed_agent": self.failed_agent,
            "original_task": self.original_task[:200],
            "heal_output": self.heal_output[:500],
            "depth": self.depth,
            "elapsed_s": round(self.elapsed_s, 3),
            "metadata": self.metadata,
        }


class SelfHealingPipeline:
    """Ouroboros: de slang die zichzelf geneest.

    Vangt agent-failures op en dispatcht de Artificer om een
    hotfix te smeden in de sandbox. Integreert met TheSynapse
    voor Hebbian consequenties en met CorticalStack voor logging.
    """

    def __init__(self) -> None:
        """Initialiseer de pipeline met lazy-loaded dependencies."""
        self._artificer = None
        self._synapse = None
        self._lock = threading.Lock()
        self._heal_count = 0
        self._heal_successes = 0
        logger.info("Ouroboros SelfHealingPipeline geïnitialiseerd")

    def _get_artificer(self) -> Any:
        """Lazy-load Artificer singleton."""
        if self._artificer is None:
            try:
                from danny_toolkit.brain.artificer import Artificer
                self._artificer = Artificer()
            except ImportError:
                logger.warning("Ouroboros: Artificer niet beschikbaar")
        return self._artificer

    def _get_synapse(self) -> Any:
        """Lazy-load TheSynapse singleton."""
        if self._synapse is None:
            try:
                from danny_toolkit.brain.synapse import get_synapse
                self._synapse = get_synapse()
            except ImportError:
                logger.warning("Ouroboros: TheSynapse niet beschikbaar")
        return self._synapse

    async def handle_exception(
        self,
        failed_agent: str,
        error_trace: str,
        original_task: str,
        recovery_depth: int = 0,
        trace_id: str = "",
    ) -> HealResult:
        """Vang een agent-failure op en probeer te genezen via Artificer.

        Args:
            failed_agent: Naam van de gefaalde agent.
            error_trace: Volledige stacktrace als string.
            original_task: De originele gebruikerstaak.
            recovery_depth: Huidige diepte van recovery-pogingen.
            trace_id: Pipeline trace ID voor correlatie.

        Returns:
            HealResult met success status en output.
        """
        t0 = time.time()
        self._heal_count += 1

        # ── Infinite Loop Preventie ──────────────────────────────
        if recovery_depth > MAX_RECOVERY_DEPTH:
            logger.error(
                "OUROBOROS HALT: recovery_depth %d > %d — "
                "afbreken om oneindige loop te voorkomen (agent=%s, trace=%s)",
                recovery_depth, MAX_RECOVERY_DEPTH, failed_agent, trace_id,
            )
            result = HealResult(
                success=False,
                failed_agent=failed_agent,
                original_task=original_task,
                heal_output="CRITICAL SYSTEM HALT — recovery loop afgebroken",
                depth=recovery_depth,
                elapsed_s=time.time() - t0,
                metadata={
                    "halt_reason": "max_recovery_depth_exceeded",
                    "trace_id": trace_id,
                },
            )
            self._log_heal_attempt(result)
            return result

        # ── Hebbian Straf: failed agent afstraffen ───────────────
        synapse = self._get_synapse()
        if synapse:
            try:
                for category in ("GENERAL", "DATA", "SEARCH", "CODE"):
                    synapse._apply_plasticity(
                        category, failed_agent, FAILURE_PENALTY,
                    )
                synapse._safe_commit()
                logger.info(
                    "Ouroboros: Hebbian penalty %.2f op %s",
                    FAILURE_PENALTY, failed_agent,
                )
            except Exception as e:
                logger.debug("Ouroboros: Synapse penalty mislukt: %s", e)

        # ── NeuralBus: publiceer heal-start event ────────────────
        self._publish_event("heal_start", {
            "failed_agent": failed_agent,
            "error_preview": error_trace[:200],
            "original_task": original_task[:200],
            "recovery_depth": recovery_depth,
            "trace_id": trace_id,
        })

        # ── Artificer Nood-Dispatch ──────────────────────────────
        artificer = self._get_artificer()
        if artificer is None:
            result = HealResult(
                success=False,
                failed_agent=failed_agent,
                original_task=original_task,
                heal_output="Artificer niet beschikbaar — kan niet zelf-genezen",
                depth=recovery_depth,
                elapsed_s=time.time() - t0,
                metadata={"trace_id": trace_id},
            )
            self._log_heal_attempt(result)
            return result

        # Bouw de nood-prompt voor de Artificer
        heal_prompt = self._build_heal_prompt(
            failed_agent, error_trace, original_task,
        )

        try:
            heal_output = await artificer.execute_task(heal_prompt)

            if not heal_output or "❌" in str(heal_output):
                # Artificer kon niet patchen
                result = HealResult(
                    success=False,
                    failed_agent=failed_agent,
                    original_task=original_task,
                    heal_output=str(heal_output or "Geen output"),
                    depth=recovery_depth,
                    elapsed_s=time.time() - t0,
                    metadata={"trace_id": trace_id},
                )
            else:
                # Succesvolle patch!
                self._heal_successes += 1
                result = HealResult(
                    success=True,
                    failed_agent=failed_agent,
                    original_task=original_task,
                    heal_output=str(heal_output),
                    depth=recovery_depth,
                    elapsed_s=time.time() - t0,
                    metadata={"trace_id": trace_id},
                )

                # ── Saviour Boost: Artificer belonen ─────────────
                if synapse:
                    try:
                        for category in ("GENERAL", "DATA", "SEARCH", "CODE"):
                            synapse._apply_plasticity(
                                category, "Artificer", SAVIOUR_BOOST,
                            )
                        synapse._safe_commit()
                        logger.info(
                            "Ouroboros: Saviour Boost +%.2f op Artificer",
                            SAVIOUR_BOOST,
                        )
                    except Exception as e:
                        logger.debug("Ouroboros: Saviour boost mislukt: %s", e)

        except Exception as heal_error:
            logger.error(
                "Ouroboros: Artificer heal CRASHED: %s (agent=%s, trace=%s)",
                heal_error, failed_agent, trace_id,
            )
            result = HealResult(
                success=False,
                failed_agent=failed_agent,
                original_task=original_task,
                heal_output=f"Artificer crash: {type(heal_error).__name__}: {heal_error}",
                depth=recovery_depth,
                elapsed_s=time.time() - t0,
                metadata={
                    "heal_error": str(heal_error)[:200],
                    "trace_id": trace_id,
                },
            )

        # ── Logging & Events ─────────────────────────────────────
        self._log_heal_attempt(result)
        self._publish_event(
            "heal_complete" if result.success else "heal_failed",
            result.to_dict(),
        )

        return result

    def _build_heal_prompt(
        self,
        failed_agent: str,
        error_trace: str,
        original_task: str,
    ) -> str:
        """Bouw een nood-prompt voor de Artificer.

        De prompt bevat de originele taak, stacktrace, en instructies
        om een hotfix te schrijven in de sandbox.
        """
        return (
            f"OUROBOROS NOOD-PROTOCOL — Self-Healing Dispatch\n"
            f"{'=' * 50}\n\n"
            f"SITUATIE: Agent '{failed_agent}' is gecrasht tijdens executie.\n\n"
            f"ORIGINELE TAAK:\n{original_task[:500]}\n\n"
            f"STACKTRACE:\n```\n{error_trace[:1500]}\n```\n\n"
            f"INSTRUCTIE:\n"
            f"1. Analyseer de stacktrace hierboven.\n"
            f"2. Identificeer de root cause van de crash.\n"
            f"3. Schrijf een Python hotfix-script dat:\n"
            f"   - Het probleem oplost of omzeilt\n"
            f"   - Een alternatieve aanpak biedt voor de originele taak\n"
            f"   - Veilig draait in de sandbox (geen os.system, subprocess, eval)\n"
            f"4. Het script moet een duidelijke output printen.\n"
            f"5. Focus op een werkende oplossing, niet op perfectie.\n\n"
            f"BEPERKINGEN:\n"
            f"- Alleen standaard library + geïnstalleerde packages\n"
            f"- Geen directe file I/O buiten de sandbox directory\n"
            f"- Geen netwerk-calls tenzij strikt noodzakelijk\n"
        )

    def _log_heal_attempt(self, result: HealResult) -> None:
        """Log heal-poging naar CorticalStack voor immuungeheugen."""
        try:
            from danny_toolkit.brain.cortical_stack import get_cortical_stack
            cs = get_cortical_stack()
            cs.log_event(
                "ouroboros",
                "heal_success" if result.success else "heal_failed",
                result.to_dict(),
            )
        except Exception as e:
            logger.debug("Ouroboros: CorticalStack logging mislukt: %s", e)

    def _publish_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Publiceer event naar NeuralBus voor dashboard awareness."""
        try:
            from danny_toolkit.core.neural_bus import get_bus, EventTypes
            bus = get_bus()
            # Gebruik HEALTH_STATUS_CHANGE als closest match
            bus.publish(
                EventTypes.HEALTH_STATUS_CHANGE,
                {"ouroboros_event": event_type, **data},
                bron="ouroboros",
            )
        except Exception as e:
            logger.debug("Ouroboros: NeuralBus publish mislukt: %s", e)

    def get_status(self) -> Dict[str, Any]:
        """Return Ouroboros status voor dashboard/API."""
        return {
            "heal_attempts": self._heal_count,
            "heal_successes": self._heal_successes,
            "heal_rate": (
                round(self._heal_successes / self._heal_count, 2)
                if self._heal_count > 0 else 0.0
            ),
            "max_recovery_depth": MAX_RECOVERY_DEPTH,
        }


# ── Singleton ────────────────────────────────────────────────────
_instance: Optional[SelfHealingPipeline] = None
_instance_lock = threading.Lock()


def get_ouroboros() -> SelfHealingPipeline:
    """Thread-safe singleton factory voor SelfHealingPipeline."""
    global _instance
    if _instance is None:
        with _instance_lock:
            if _instance is None:
                _instance = SelfHealingPipeline()
    return _instance
