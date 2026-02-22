"""
ProactiveEngine v1.0 — Van Reactief naar Levend.

Verbindt Sensorium, HeartbeatDaemon, PipelineTuner en
Governor tot een proactief systeem dat zelf acties triggert
op basis van regels met condities, cooldowns en prioriteiten.

Gebruik:
    engine = ProactiveEngine(daemon, brain)
    # Luistert automatisch naar Sensorium events
    # Timer-regels via _check_timer_regels() elke 60s

Geen nieuwe dependencies.
"""

import threading
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Dict, List, Any

import logging
logger = logging.getLogger(__name__)


@dataclass
class ProactiveRule:
    """Een proactieve regel: ALS conditie DAN actie.

    Attributes:
        naam: Unieke naam ("cpu_cleanup").
        conditie: Lambda die state dict ontvangt,
            retourneert bool.
        actie: Actie string:
            "swarm:prompt" → SwarmEngine taak
            "repair:" → SelfRepairProtocol
            "melding:tekst" → Melding aan Danny
        cooldown: Minimum seconden tussen triggers.
        prioriteit: 1=hoog, 2=medium, 3=laag.
        bron: "sensorium" | "timer" | "tuner".
    """
    naam: str
    conditie: Callable[[Dict], bool]
    actie: str
    cooldown: int = 3600
    prioriteit: int = 2
    bron: str = "sensorium"


class ProactiveEngine:
    """Verbindt Sensorium → Regels → SwarmEngine.

    Luistert naar events, evalueert regels, triggert
    acties met Governor-goedkeuring en cooldowns.
    """

    def __init__(self, daemon, brain=None):
        """Initialiseer de ProactiveEngine.

        Args:
            daemon: DigitalDaemon instantie.
            brain: PrometheusBrain instantie (optioneel).
        """
        self.daemon = daemon
        self.brain = brain
        self.regels: List[ProactiveRule] = []
        self._cooldowns: Dict[str, float] = {}
        self._governor = None
        self._stack = None
        self._stop = threading.Event()
        self._meldingen: List[str] = []
        self._lock = threading.Lock()

        # CPU spike tracking (3 metingen boven 90%)
        self._cpu_hoog_teller = 0

        # Error tracking
        self._recente_fouten: List[str] = []

        # Heartbeat tracking
        self._laatste_heartbeat = time.time()

        self._registreer_standaard_regels()
        self._verbind_sensorium()

    # ─── Lazy Properties ───

    @property
    def governor(self):
        """Lazy OmegaGovernor."""
        if self._governor is None:
            try:
                from .governor import OmegaGovernor
                self._governor = OmegaGovernor()
            except Exception as e:
                logger.debug("OmegaGovernor init failed: %s", e)
        return self._governor

    @property
    def stack(self):
        """Lazy CorticalStack."""
        if self._stack is None:
            try:
                from .cortical_stack import (
                    get_cortical_stack,
                )
                self._stack = get_cortical_stack()
            except Exception as e:
                logger.debug("CorticalStack init failed: %s", e)
        return self._stack

    # ─── Standaard Regels ───

    def _registreer_standaard_regels(self):
        """Registreer de 8 standaard proactieve regels."""
        self.regels = [
            # 1. CPU cleanup
            ProactiveRule(
                naam="cpu_cleanup",
                conditie=lambda s: s.get("cpu_hoog", 0) >= 3,
                actie="swarm:Ruim cache en temp bestanden op",
                cooldown=3600,
                prioriteit=2,
                bron="sensorium",
            ),
            # 2. Error repair
            ProactiveRule(
                naam="error_repair",
                conditie=lambda s: s.get(
                    "fouten_count", 0
                ) >= 3,
                actie="repair:",
                cooldown=1800,
                prioriteit=1,
                bron="sensorium",
            ),
            # 3. Morning brief
            ProactiveRule(
                naam="morning_brief",
                conditie=lambda s: s.get("uur") == 8
                and s.get("minuut", 99) < 2,
                actie=(
                    "swarm:Geef een korte ochtend briefing"
                    " met systeem status en planning"
                ),
                cooldown=86400,
                prioriteit=2,
                bron="timer",
            ),
            # 4. Evening reflect
            ProactiveRule(
                naam="evening_reflect",
                conditie=lambda s: s.get("uur") == 22
                and s.get("minuut", 99) < 2,
                actie=(
                    "swarm:Geef een samenvatting van"
                    " vandaag en suggesties voor morgen"
                ),
                cooldown=86400,
                prioriteit=3,
                bron="timer",
            ),
            # 5. MEMEX ledig
            ProactiveRule(
                naam="memex_ledig",
                conditie=lambda s: s.get(
                    "memex_skips", 0
                ) > 20,
                actie=(
                    "swarm:Indexeer nieuwe kennis"
                    " in de MEMEX vectorstore"
                ),
                cooldown=14400,
                prioriteit=3,
                bron="tuner",
            ),
            # 6. Sentinel alert
            ProactiveRule(
                naam="sentinel_alert",
                conditie=lambda s: s.get(
                    "governor_status"
                ) == "RED",
                actie=(
                    "melding:Governor status ROOD —"
                    " circuit breaker actief!"
                ),
                cooldown=900,
                prioriteit=1,
                bron="sensorium",
            ),
            # 7. Idle growth
            ProactiveRule(
                naam="idle_growth",
                conditie=lambda s: s.get(
                    "idle_min", 0
                ) > 30 and s.get(
                    "energie_ok", False
                ),
                actie=(
                    "swarm:Leer autonome feiten uit"
                    " de kennisbank voor zelfgroei"
                ),
                cooldown=7200,
                prioriteit=3,
                bron="sensorium",
            ),
            # 8. Heartbeat check
            ProactiveRule(
                naam="heartbeat_check",
                conditie=lambda s: s.get(
                    "geen_heartbeat_sec", 0
                ) > 300,
                actie=(
                    "melding:Heartbeat niet ontvangen"
                    " in 5+ minuten — systeem check"
                ),
                cooldown=600,
                prioriteit=1,
                bron="timer",
            ),
        ]

    # ─── Sensorium Binding ───

    def _verbind_sensorium(self):
        """Registreer listeners bij Sensorium."""
        try:
            from ..daemon.sensorium import EventType
            sensorium = self.daemon.sensorium

            event_types = [
                EventType.IDLE,
                EventType.MORNING,
                EventType.EVENING,
                EventType.NIGHT,
                EventType.TASK_COMPLETE,
                EventType.QUERY_ASKED,
                EventType.APP_OPENED,
                EventType.APP_CLOSED,
            ]

            for et in event_types:
                sensorium.register_listener(
                    et, self._on_event
                )
        except Exception as e:
            logger.debug("Sensorium binding failed: %s", e)

    # ─── Event Handler ───

    def _on_event(self, event):
        """Ontvang Sensorium event en evalueer regels.

        Args:
            event: SensoryEvent van Sensorium.
        """
        state = self._bouw_state(event)
        self._evalueer_regels(state)

    def _bouw_state(self, event=None) -> Dict[str, Any]:
        """Bouw state dict vanuit alle subsystemen.

        Args:
            event: Optioneel SensoryEvent voor context.

        Returns:
            Dict met alle relevante state waarden.
        """
        now = datetime.now()
        state = {
            "uur": now.hour,
            "minuut": now.minute,
            "timestamp": time.time(),
        }

        # CPU spike tracking
        try:
            import psutil
            cpu = psutil.cpu_percent(interval=0)
            if cpu > 90:
                self._cpu_hoog_teller += 1
            else:
                self._cpu_hoog_teller = max(
                    0, self._cpu_hoog_teller - 1
                )
            state["cpu"] = cpu
            state["cpu_hoog"] = self._cpu_hoog_teller
        except ImportError:
            state["cpu"] = 0
            state["cpu_hoog"] = 0

        # Daemon state
        try:
            limbic = self.daemon.limbic.get_status()
            energy = limbic["state"]["energy"]
            state["energie_ok"] = energy not in (
                "exhausted", "zombie"
            )
            state["mood"] = limbic["state"]["mood"]
        except Exception as e:
            logger.debug("Limbic status failed: %s", e)
            state["energie_ok"] = True
            state["mood"] = "neutral"

        # Idle detectie
        try:
            idle = self.daemon.sensorium.detect_idle(
                threshold_minutes=1
            )
            if idle:
                delta = (
                    datetime.now()
                    - self.daemon.sensorium.last_activity
                )
                state["idle_min"] = (
                    delta.total_seconds() / 60
                )
            else:
                state["idle_min"] = 0
        except Exception as e:
            logger.debug("Idle detectie failed: %s", e)
            state["idle_min"] = 0

        # Governor status
        try:
            gov = self.governor
            if gov:
                health = gov.check_api_health()
                state["governor_status"] = (
                    "GREEN" if health else "RED"
                )
            else:
                state["governor_status"] = "GREEN"
        except Exception as e:
            logger.debug("Governor status check failed: %s", e)
            state["governor_status"] = "GREEN"

        # Error tracking
        state["fouten_count"] = len(
            self._recente_fouten
        )

        # PipelineTuner memex skips
        state["memex_skips"] = 0
        try:
            if self.brain:
                from swarm_engine import SwarmEngine
                engine = SwarmEngine(brain=self.brain)
                samenvatting = (
                    engine._tuner.get_samenvatting()
                )
                if "memex" in samenvatting.lower():
                    # Tel "skip" woorden in samenvatting
                    state["memex_skips"] = (
                        samenvatting.lower().count(
                            "skip"
                        )
                    )
        except Exception as e:
            logger.debug("Memex skips check failed: %s", e)

        # Heartbeat tracking
        state["geen_heartbeat_sec"] = (
            time.time() - self._laatste_heartbeat
        )

        return state

    # ─── Evaluatie ───

    def _evalueer_regels(self, state: Dict):
        """Evalueer alle regels tegen de state.

        Args:
            state: Dict met systeem-state waarden.
        """
        # Sorteer op prioriteit (1 eerst)
        gesorteerd = sorted(
            self.regels, key=lambda r: r.prioriteit
        )

        for regel in gesorteerd:
            if self._stop.is_set():
                return

            try:
                # Check conditie
                if not regel.conditie(state):
                    continue

                # Check cooldown
                laatste = self._cooldowns.get(
                    regel.naam, 0
                )
                if (
                    time.time() - laatste
                    < regel.cooldown
                ):
                    continue

                # Check Governor goedkeuring
                if not self._governor_check(regel):
                    continue

                # Voer uit
                self._voer_uit(regel, state)

            except Exception as e:
                logger.debug("Regel %s evaluatie failed: %s", regel.naam, e)

    def _governor_check(self, regel) -> bool:
        """Check of Governor de actie toestaat.

        Args:
            regel: ProactiveRule om te checken.

        Returns:
            True als actie mag, False als geblokkeerd.
        """
        gov = self.governor
        if gov is None:
            return True

        # Bij RED status: alleen prioriteit 1 regels
        try:
            if not gov.check_api_health():
                return regel.prioriteit == 1
        except Exception as e:
            logger.debug("Governor health check failed: %s", e)

        return True

    # ─── Uitvoering ───

    def _voer_uit(self, regel, state: Dict):
        """Voer een getriggerde regel uit.

        Args:
            regel: De ProactiveRule die triggerde.
            state: De huidige state dict.
        """
        actie = regel.actie

        try:
            if actie.startswith("swarm:"):
                prompt = actie[6:]
                self._run_swarm(prompt)

            elif actie.startswith("repair:"):
                self._run_repair()

            elif actie.startswith("melding:"):
                tekst = actie[8:]
                self._voeg_melding_toe(tekst)

        except Exception as e:
            logger.debug("Regel uitvoering failed: %s", e)

        # Registreer cooldown
        self._cooldowns[regel.naam] = time.time()

        # Log naar CorticalStack
        self._log_actie(regel, state)

    def _run_swarm(self, prompt: str):
        """Voer een SwarmEngine taak uit.

        Args:
            prompt: De taak voor SwarmEngine.
        """
        try:
            from swarm_engine import run_swarm_sync
            run_swarm_sync(prompt, self.brain)
        except Exception as e:
            logger.debug("Swarm taak failed: %s", e)
            self._voeg_melding_toe(
                f"Swarm taak mislukt: {prompt[:50]}"
            )

    def _run_repair(self):
        """Voer SelfRepairProtocol diagnose uit."""
        try:
            from ..core.self_repair import (
                SelfRepairProtocol,
            )
            protocol = SelfRepairProtocol()
            diagnose = protocol.diagnose()

            status = diagnose.get("status", "ONBEKEND")
            self._voeg_melding_toe(
                f"Diagnose: {status}"
            )

            if status == "KRITIEK":
                protocol.repair()
                self._voeg_melding_toe(
                    "Auto-repair uitgevoerd"
                )

            # Reset error teller na repair
            self._recente_fouten.clear()

        except Exception as e:
            logger.debug("SelfRepair failed: %s", e)
            self._voeg_melding_toe(
                "SelfRepair niet beschikbaar"
            )

    def _voeg_melding_toe(self, tekst: str):
        """Voeg melding toe aan de queue.

        Args:
            tekst: Meldingstekst voor Danny.
        """
        with self._lock:
            tijdstip = datetime.now().strftime(
                "%H:%M"
            )
            self._meldingen.append(
                f"[{tijdstip}] {tekst}"
            )

    def _log_actie(self, regel, state: Dict):
        """Log proactieve actie naar CorticalStack.

        Args:
            regel: De uitgevoerde regel.
            state: De state bij uitvoering.
        """
        stack = self.stack
        if stack is None:
            return

        try:
            stack.log_event(
                actor="proactive_engine",
                action=f"regel_triggered:{regel.naam}",
                details={
                    "actie": regel.actie[:200],
                    "prioriteit": regel.prioriteit,
                    "bron": regel.bron,
                    "cpu": state.get("cpu", 0),
                    "mood": state.get("mood", "?"),
                },
                source="proactive",
            )
        except Exception as e:
            logger.debug("Actie logging failed: %s", e)

    # ─── Timer Regels ───

    def _check_timer_regels(self):
        """Check tijd-gebaseerde regels.

        Moet elke 60s gecalled worden vanuit
        HeartbeatDaemon of DigitalDaemon _main_loop.
        """
        if self._stop.is_set():
            return

        # Update heartbeat timestamp
        self._laatste_heartbeat = time.time()

        state = self._bouw_state()
        self._evalueer_regels(state)

    # ─── Publieke API ───

    def haal_meldingen(self) -> List[str]:
        """Haal meldingen op en leeg de queue.

        Returns:
            Lijst van meldingsstrings.
        """
        with self._lock:
            meldingen = list(self._meldingen)
            self._meldingen.clear()
            return meldingen

    def voeg_regel_toe(self, regel: ProactiveRule):
        """Voeg een custom regel toe.

        Args:
            regel: ProactiveRule instantie.

        Raises:
            ValueError: Als cooldown < 60 seconden.
        """
        if regel.cooldown < 60:
            raise ValueError(
                "Cooldown moet minimaal 60 seconden"
                f" zijn, kreeg {regel.cooldown}"
            )
        self.regels.append(regel)

    def registreer_fout(self, fout_tekst: str):
        """Registreer een fout voor error tracking.

        Args:
            fout_tekst: Beschrijving van de fout.
        """
        self._recente_fouten.append(fout_tekst)
        # Houd maximaal 20 recente fouten bij
        if len(self._recente_fouten) > 20:
            self._recente_fouten = (
                self._recente_fouten[-20:]
            )

    def stop(self):
        """Stop de engine gracefully."""
        self._stop.set()

    def get_status(self) -> Dict[str, Any]:
        """Haal engine status op.

        Returns:
            Dict met actieve regels, meldingen,
            cooldown info.
        """
        now = time.time()
        return {
            "actief": not self._stop.is_set(),
            "regels": len(self.regels),
            "meldingen_wachtend": len(
                self._meldingen
            ),
            "fouten_getrackt": len(
                self._recente_fouten
            ),
            "cooldowns": {
                naam: round(now - ts)
                for naam, ts in self._cooldowns.items()
            },
        }
