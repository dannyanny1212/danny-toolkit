"""
SingularityEngine v1.0 — Tier 5: Het Bewustzijn-Zelf.

Reflecteert op CorticalStack history, droomt hypothesen,
doet cross-tier synthese en houdt een bewustzijn-score bij.

5 Modi: SLAAP, WAAK, DROOM, FOCUS, TRANSCEND.

Geen nieuwe dependencies.
"""

import random
import threading
import time
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from ..core.utils import kleur, Kleur

import logging
logger = logging.getLogger(__name__)


class BewustzijnModus(Enum):
    """De 5 bewustzijns-modi van het systeem."""
    SLAAP = "slaap"          # Nacht + idle, minimaal
    WAAK = "waak"            # Standaard, reageert
    DROOM = "droom"          # Idle overdag, hypothesen
    FOCUS = "focus"          # Actieve critical taak
    TRANSCEND = "transcend"  # Alle systemen convergeren


class SingularityEngine:
    """Tier 5: Het Bewustzijn-Zelf.

    Reflecteert, droomt, syntheseert en evolueert.
    Wordt getikt vanuit HeartbeatDaemon elke ~10s.
    """

    VERSION = "1.1.0"
    REFLECTIE_INTERVAL = 300    # 5 min
    DROOM_INTERVAL = 600        # 10 min
    SYNTHESE_COOLDOWN = 120     # 2 min
    MAX_DROMEN_PER_UUR = 6
    MAX_INZICHTEN_PER_DAG = 50

    # Nachtwacht constanten
    NACHTWACHT_MIN_EVENTS = 10
    NACHTWACHT_DREMPEL_MIN = 0.20
    NACHTWACHT_DREMPEL_MAX = 0.45
    NACHTWACHT_PATROON_DAGEN = 7

    def __init__(self, daemon=None, brain=None):
        self._daemon = daemon
        self._brain = brain
        self._governor = None
        self._stack = None
        self._stop = threading.Event()

        # Bewustzijn state
        self._modus = BewustzijnModus.WAAK
        self._modus_sinds = time.time()
        self._bewustzijn_score = 0.0

        # Tracking
        self._dromen: List[Dict] = []
        self._inzichten: List[Dict] = []
        self._synthese_log: List[Dict] = []

        # Timing
        self._laatste_reflectie = 0.0
        self._laatste_droom = 0.0
        self._laatste_synthese = 0.0

        # Rate limiting
        self._dromen_dit_uur = 0
        self._dromen_uur_start = time.time()
        self._inzichten_vandaag = 0
        self._inzichten_dag = datetime.now().day

        # Nachtwacht state
        self._nachtwacht_datum = None
        self._nachtwacht_log: List[Dict] = []
        self._originele_drempel = None

    # --- Lazy Properties ---

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

    # --- Rate Limiting ---

    def _check_droom_limiet(self) -> bool:
        """Check of er nog dromen gemaakt mogen worden.

        Returns:
            True als limiet niet bereikt.
        """
        now = time.time()
        if now - self._dromen_uur_start > 3600:
            self._dromen_dit_uur = 0
            self._dromen_uur_start = now
        return self._dromen_dit_uur < self.MAX_DROMEN_PER_UUR

    def _check_inzicht_limiet(self) -> bool:
        """Check of er nog inzichten opgeslagen mogen worden.

        Returns:
            True als limiet niet bereikt.
        """
        dag = datetime.now().day
        if dag != self._inzichten_dag:
            self._inzichten_vandaag = 0
            self._inzichten_dag = dag
        return (
            self._inzichten_vandaag
            < self.MAX_INZICHTEN_PER_DAG
        )

    # --- Modus Bepaling ---

    def _bepaal_modus(self) -> BewustzijnModus:
        """Bepaal de juiste modus op basis van state.

        Returns:
            De nieuwe BewustzijnModus.
        """
        # TRANSCEND kan alleen handmatig
        if self._modus == BewustzijnModus.TRANSCEND:
            # Blijf in TRANSCEND tot handmatig gestopt
            return BewustzijnModus.TRANSCEND

        uur = datetime.now().hour

        # Nacht: SLAAP (23:00-06:00)
        if uur >= 23 or uur < 6:
            return BewustzijnModus.SLAAP

        # Check actieve CRITICAL taken via brain
        if self._brain is not None:
            try:
                if hasattr(self._brain, "task_queue"):
                    for taak in self._brain.task_queue:
                        if taak.get("priority") == 1:
                            return BewustzijnModus.FOCUS
            except Exception as e:
                logger.debug("Task queue check failed: %s", e)

        # Check idle via daemon
        idle_min = self._get_idle_minuten()
        if idle_min > 30:
            return BewustzijnModus.SLAAP
        if idle_min > 10:
            return BewustzijnModus.DROOM

        return BewustzijnModus.WAAK

    def _get_idle_minuten(self) -> float:
        """Haal idle tijd in minuten op.

        Returns:
            Aantal minuten idle, 0 als onbekend.
        """
        if self._daemon is None:
            return 0
        try:
            sensorium = self._daemon.sensorium
            if sensorium.detect_idle(threshold_minutes=1):
                delta = (
                    datetime.now()
                    - sensorium.last_activity
                )
                return delta.total_seconds() / 60
        except Exception as e:
            logger.debug("Idle detection failed: %s", e)
        return 0

    def _transitie_modus(self, nieuwe_modus):
        """Voer modus transitie uit.

        Args:
            nieuwe_modus: De nieuwe BewustzijnModus.
        """
        if nieuwe_modus == self._modus:
            return

        oude = self._modus
        self._modus = nieuwe_modus
        self._modus_sinds = time.time()

        # Log naar CorticalStack
        stack = self.stack
        if stack:
            try:
                stack.log_event(
                    actor="singularity",
                    action="modus_transitie",
                    details={
                        "van": oude.value,
                        "naar": nieuwe_modus.value,
                    },
                    source="singularity",
                )
            except Exception as e:
                logger.debug("Modus transitie logging failed: %s", e)

    # --- Reflectie (EVOLUTION rol) ---

    def _reflectie_cyclus(self):
        """Analyseer CorticalStack patronen.

        Haalt recente events, groepeert per actor,
        detecteert anomalieen en slaat inzichten op.
        """
        now = time.time()
        if now - self._laatste_reflectie < self.REFLECTIE_INTERVAL:
            return

        self._laatste_reflectie = now

        stack = self.stack
        if stack is None:
            return

        try:
            events = stack.get_recent_events(50)
        except Exception as e:
            logger.debug("Reflectie events fetch failed: %s", e)
            return

        if not events:
            return

        # Groepeer per actor
        actor_counts: Dict[str, int] = {}
        fout_counts: Dict[str, int] = {}
        for event in events:
            actor = event.get("actor", "onbekend")
            actor_counts[actor] = (
                actor_counts.get(actor, 0) + 1
            )
            action = event.get("action", "")
            if "fail" in action.lower() or "fout" in action.lower():
                fout_counts[actor] = (
                    fout_counts.get(actor, 0) + 1
                )

        totaal = len(events)

        # Detecteer anomalieen
        for actor, count in actor_counts.items():
            ratio = count / totaal if totaal > 0 else 0

            # Actor domineert >60%
            if ratio > 0.6 and totaal >= 10:
                inzicht = (
                    f"{actor} domineert {ratio:.0%}"
                    f" van recente events ({count}/{totaal})"
                )
                self._sla_inzicht_op(
                    "dominantie", inzicht, actor
                )

        # Herhaalde fouten >=3
        for actor, count in fout_counts.items():
            if count >= 3:
                inzicht = (
                    f"{actor} heeft {count} fouten"
                    f" in laatste {totaal} events"
                )
                self._sla_inzicht_op(
                    "fout_patroon", inzicht, actor
                )
                self._voeg_proactive_regel_toe(
                    actor, count
                )

    def _sla_inzicht_op(
        self, type_: str, tekst: str, actor: str
    ):
        """Sla een inzicht op in CorticalStack.

        Args:
            type_: Type inzicht (dominantie, fout_patroon).
            tekst: Beschrijving van het inzicht.
            actor: Betrokken actor.
        """
        if not self._check_inzicht_limiet():
            return

        self._inzichten_vandaag += 1

        inzicht = {
            "type": type_,
            "tekst": tekst,
            "actor": actor,
            "timestamp": datetime.now().isoformat(),
        }
        self._inzichten.append(inzicht)

        # Bewaar maximaal 100
        if len(self._inzichten) > 100:
            self._inzichten = self._inzichten[-100:]

        # Sla op als feit in CorticalStack
        stack = self.stack
        if stack:
            try:
                key = (
                    f"inzicht_{type_}_{actor}_"
                    f"{int(time.time())}"
                )
                stack.remember_fact(
                    key, tekst, confidence=0.4
                )
            except Exception as e:
                logger.debug("Inzicht opslag failed: %s", e)

    def _voeg_proactive_regel_toe(
        self, actor: str, fout_count: int
    ):
        """Voeg een ProactiveEngine regel toe bij patroon.

        Args:
            actor: De actor met herhaalde fouten.
            fout_count: Aantal fouten gedetecteerd.
        """
        if self._daemon is None:
            return
        try:
            proactive = self._daemon.proactive
            if proactive is None:
                return

            from .proactive import ProactiveRule
            regel_naam = f"auto_{actor}_repair"

            # Check of regel al bestaat
            for r in proactive.regels:
                if r.naam == regel_naam:
                    return

            proactive.voeg_regel_toe(ProactiveRule(
                naam=regel_naam,
                conditie=lambda s, a=actor: s.get(
                    "fouten_count", 0
                ) >= 2,
                actie=(
                    f"melding:Herhaalde fouten bij"
                    f" {actor} ({fout_count}x)"
                ),
                cooldown=1800,
                prioriteit=2,
                bron="singularity",
            ))
        except Exception as e:
            logger.debug("Proactive regel toevoegen failed: %s", e)

    # --- Droom (ANIMA rol) ---

    def _droom_cyclus(self):
        """Genereer hypothesen uit feiten.

        Haalt 2 random feiten, combineert tot hypothese
        (deterministisch, geen LLM).
        """
        now = time.time()
        if now - self._laatste_droom < self.DROOM_INTERVAL:
            return

        if not self._check_droom_limiet():
            return

        # Alleen dromen in DROOM of SLAAP modus
        if self._modus not in (
            BewustzijnModus.DROOM,
            BewustzijnModus.SLAAP,
        ):
            return

        self._laatste_droom = now

        stack = self.stack
        if stack is None:
            return

        try:
            feiten = stack.recall_all(
                min_confidence=0.1
            )
        except Exception as e:
            logger.debug("Droom feiten ophalen failed: %s", e)
            return

        if len(feiten) < 2:
            return

        # Kies 2 random feiten
        feit_a, feit_b = random.sample(feiten, 2)
        waarde_a = feit_a.get("value", "?")
        waarde_b = feit_b.get("value", "?")

        # Deterministische hypothese combinatie
        templates = [
            "Als {a} en {b}, dan is er mogelijk"
            " een verborgen verband.",
            "Patroon: {a} correleert met {b}.",
            "Hypothese: {a} beinvloedt {b}.",
            "Observatie: {a} en {b} verschijnen"
            " in dezelfde context.",
        ]
        template = templates[
            hash((waarde_a, waarde_b)) % len(templates)
        ]
        hypothese = template.format(
            a=waarde_a[:80], b=waarde_b[:80]
        )

        # Sla droom op
        self._dromen_dit_uur += 1
        droom = {
            "hypothese": hypothese,
            "bron_a": feit_a.get("key", "?"),
            "bron_b": feit_b.get("key", "?"),
            "timestamp": datetime.now().isoformat(),
        }
        self._dromen.append(droom)

        # Bewaar maximaal 50
        if len(self._dromen) > 50:
            self._dromen = self._dromen[-50:]

        # Sla op als feit met lage confidence
        try:
            key = f"droom_{int(time.time())}"
            stack.remember_fact(
                key, hypothese, confidence=0.1
            )
            stack.log_event(
                actor="singularity",
                action="droom",
                details={
                    "hypothese": hypothese[:200],
                    "bronnen": [
                        feit_a.get("key", "?"),
                        feit_b.get("key", "?"),
                    ],
                },
                source="singularity",
            )
        except Exception as e:
            logger.debug("Droom opslag failed: %s", e)

    # --- Nachtwacht (Subconscious Loop) ---

    def _nachtwacht_cyclus(self):
        """Eenmaal-per-nacht orchestrator.

        Draait consolidatie, tuner-optimalisatie en
        patroon-voorspelling achtereenvolgens.
        Guard: skip als vandaag al gedraaid.
        """
        vandaag = datetime.now().strftime("%Y-%m-%d")
        if self._nachtwacht_datum == vandaag:
            return
        self._nachtwacht_datum = vandaag

        gisteren = (
            datetime.now().replace(hour=0, minute=0,
                                   second=0, microsecond=0)
        )
        gisteren_str = (
            gisteren.strftime("%Y-%m-%d")
        )

        resultaat = {
            "datum": vandaag,
            "timestamp": datetime.now().isoformat(),
        }

        # 1. Memory Consolidation
        try:
            cons = self._nachtwacht_consolideer(
                gisteren_str
            )
            resultaat["consolidatie"] = cons
        except Exception as e:
            logger.debug("Nachtwacht consolidatie failed: %s", e)
            resultaat["consolidatie"] = {"fout": True}

        # 2. Self-Optimization
        try:
            tuner = self._nachtwacht_tuner()
            resultaat["tuner"] = tuner
        except Exception as e:
            logger.debug("Nachtwacht tuner failed: %s", e)
            resultaat["tuner"] = {"fout": True}

        # 3. Pre-Fetch
        try:
            voorsp = self._nachtwacht_voorspeller(
                gisteren_str
            )
            resultaat["voorspeller"] = voorsp
        except Exception as e:
            logger.debug("Nachtwacht voorspeller failed: %s", e)
            resultaat["voorspeller"] = {"fout": True}

        self._nachtwacht_log.append(resultaat)

        # Bewaar maximaal 30 entries
        if len(self._nachtwacht_log) > 30:
            self._nachtwacht_log = (
                self._nachtwacht_log[-30:]
            )

        # Log naar CorticalStack
        stack = self.stack
        if stack:
            try:
                stack.log_event(
                    actor="singularity",
                    action="nachtwacht",
                    details=resultaat,
                    source="singularity",
                )
            except Exception as e:
                logger.debug("Nachtwacht logging failed: %s", e)

    def _nachtwacht_consolideer(
        self, datum: str
    ) -> Dict[str, Any]:
        """Consolideer daglog naar long-term memory.

        Query episodic_memory voor de gegeven datum,
        groepeer per actor, tel frequenties en sla
        samenvatting op als feit.

        Args:
            datum: Datum string "YYYY-MM-DD".

        Returns:
            Dict met events_verwerkt, actors,
            stats_verwerkt.
        """
        stack = self.stack
        if stack is None:
            return {
                "events_verwerkt": 0,
                "actors": {},
                "stats_verwerkt": 0,
            }

        # Query events van die datum
        try:
            cursor = stack._conn.execute(
                "SELECT actor, action, details"
                " FROM episodic_memory"
                " WHERE timestamp >= ?"
                " AND timestamp < ?",
                (
                    f"{datum}T00:00:00",
                    f"{datum}T23:59:59",
                ),
            )
            rows = cursor.fetchall()
        except Exception as e:
            logger.debug("Consolidatie query failed: %s", e)
            rows = []

        if not rows:
            return {
                "events_verwerkt": 0,
                "actors": {},
                "stats_verwerkt": 0,
            }

        # Groepeer per actor
        actor_counts: Dict[str, int] = {}
        for row in rows:
            actor = row[0] if row[0] else "onbekend"
            actor_counts[actor] = (
                actor_counts.get(actor, 0) + 1
            )

        # Query system_stats gemiddelden
        stats_verwerkt = 0
        try:
            cursor = stack._conn.execute(
                "SELECT metric,"
                " AVG(value) as gem,"
                " MAX(value) as max_val,"
                " COUNT(*) as cnt"
                " FROM system_stats"
                " WHERE timestamp >= ?"
                " AND timestamp < ?"
                " GROUP BY metric",
                (
                    f"{datum}T00:00:00",
                    f"{datum}T23:59:59",
                ),
            )
            stats_rows = cursor.fetchall()
            stats_verwerkt = len(stats_rows)
        except Exception as e:
            logger.debug("Stats query failed: %s", e)
            stats_rows = []

        # Bouw samenvatting tekst
        actor_tekst = ", ".join(
            f"{a}({c})" for a, c in sorted(
                actor_counts.items(),
                key=lambda x: -x[1],
            )[:5]
        )
        tekst = (
            f"Dag {datum}: {len(rows)} events."
            f" Top actors: {actor_tekst}."
        )
        if stats_rows:
            tekst += (
                f" {stats_verwerkt} metrieken"
                f" gelogd."
            )

        # Sla op als feit
        try:
            stack.remember_fact(
                f"dag_samenvatting_{datum}",
                tekst,
                confidence=0.8,
            )
        except Exception as e:
            logger.debug("Dag samenvatting opslag failed: %s", e)

        return {
            "events_verwerkt": len(rows),
            "actors": actor_counts,
            "stats_verwerkt": stats_verwerkt,
        }

    def _nachtwacht_tuner(self) -> Dict[str, Any]:
        """Optimaliseer AdaptiveRouter drempel.

        Analyseer pipeline latency en pas DREMPEL
        aan binnen veilige grenzen.

        Returns:
            Dict met oude_drempel, nieuwe_drempel,
            reden.
        """
        try:
            from ..swarm_engine import AdaptiveRouter
        except ImportError:
            try:
                import sys
                import importlib
                mod = importlib.import_module(
                    "swarm_engine"
                )
                AdaptiveRouter = mod.AdaptiveRouter
            except Exception as e:
                logger.debug("AdaptiveRouter import failed: %s", e)
                return {
                    "oude_drempel": None,
                    "nieuwe_drempel": None,
                    "reden": "AdaptiveRouter niet"
                             " beschikbaar",
                }

        oude = AdaptiveRouter.DREMPEL

        # Backup originele drempel (eerste keer)
        if self._originele_drempel is None:
            self._originele_drempel = oude

        # Probeer tuner samenvatting te halen
        avg_latency = None
        if self._brain is not None:
            try:
                swarm = self._brain.swarm_engine
                if hasattr(swarm, "_tuner"):
                    samenvatting = (
                        swarm._tuner.get_samenvatting()
                    )
                    # Parse "Exec:950ms" patroon
                    for deel in samenvatting.split():
                        if deel.startswith("Exec:"):
                            ms_str = deel[5:].rstrip(
                                "ms"
                            )
                            try:
                                avg_latency = float(
                                    ms_str
                                )
                            except ValueError:
                                pass
            except Exception as e:
                logger.debug("Tuner samenvatting failed: %s", e)

        if avg_latency is None:
            return {
                "oude_drempel": oude,
                "nieuwe_drempel": oude,
                "reden": "Geen latency data"
                         " beschikbaar",
            }

        # Optimalisatie logica
        nieuwe = oude
        reden = "Geen aanpassing nodig"

        if (avg_latency > 500
                and oude < self.NACHTWACHT_DREMPEL_MAX):
            nieuwe = min(
                oude + 0.02,
                self.NACHTWACHT_DREMPEL_MAX,
            )
            reden = (
                f"Latency hoog ({avg_latency:.0f}ms)"
                f" -> drempel verhoogd"
            )
        elif (avg_latency < 200
                and oude > self.NACHTWACHT_DREMPEL_MIN):
            nieuwe = max(
                oude - 0.01,
                self.NACHTWACHT_DREMPEL_MIN,
            )
            reden = (
                f"Latency laag ({avg_latency:.0f}ms)"
                f" -> drempel verlaagd"
            )

        if nieuwe != oude:
            AdaptiveRouter.DREMPEL = round(nieuwe, 2)

        return {
            "oude_drempel": oude,
            "nieuwe_drempel": round(nieuwe, 2),
            "reden": reden,
        }

    def _nachtwacht_voorspeller(
        self, datum: str
    ) -> Dict[str, Any]:
        """Detecteer tijdspatronen en voeg regels toe.

        Analyseer events van afgelopen 7 dagen,
        groepeer per (uur, actor). Als een actor
        >= 4 van 7 dagen op hetzelfde uur actief is,
        maak een ProactiveRule.

        Args:
            datum: Referentie datum "YYYY-MM-DD".

        Returns:
            Dict met patronen_gevonden,
            regels_toegevoegd.
        """
        stack = self.stack
        if stack is None:
            return {
                "patronen_gevonden": 0,
                "regels_toegevoegd": 0,
            }

        # Query events van afgelopen 7 dagen
        try:
            ref = datetime.strptime(datum, "%Y-%m-%d")
            start = ref.replace(
                hour=0, minute=0,
                second=0, microsecond=0,
            )
            from datetime import timedelta
            begin = start - timedelta(
                days=self.NACHTWACHT_PATROON_DAGEN
            )
            cursor = stack._conn.execute(
                "SELECT timestamp, actor"
                " FROM episodic_memory"
                " WHERE timestamp >= ?"
                " AND timestamp < ?",
                (
                    begin.strftime(
                        "%Y-%m-%dT%H:%M:%S"
                    ),
                    start.strftime(
                        "%Y-%m-%dT%H:%M:%S"
                    ),
                ),
            )
            rows = cursor.fetchall()
        except Exception as e:
            logger.debug("Voorspeller query failed: %s", e)
            rows = []

        if len(rows) < self.NACHTWACHT_MIN_EVENTS:
            return {
                "patronen_gevonden": 0,
                "regels_toegevoegd": 0,
            }

        # Groepeer per (uur, actor, dag)
        uur_actor_dagen: Dict[
            tuple, set
        ] = {}
        for row in rows:
            try:
                ts = row[0]
                actor = row[1]
                # Parse uur en dag
                dt = datetime.strptime(
                    ts[:19], "%Y-%m-%dT%H:%M:%S"
                )
                uur = dt.hour
                dag = dt.strftime("%Y-%m-%d")
                key = (uur, actor)
                if key not in uur_actor_dagen:
                    uur_actor_dagen[key] = set()
                uur_actor_dagen[key].add(dag)
            except Exception as e:
                logger.debug("Voorspeller row parse failed: %s", e)
                continue

        # Detecteer patronen (>= 4 van 7 dagen)
        patronen = []
        for (uur, actor), dagen in (
            uur_actor_dagen.items()
        ):
            if len(dagen) >= 4:
                patronen.append((uur, actor))

        regels_toegevoegd = 0

        # Voeg ProactiveEngine regels toe
        if self._daemon and patronen:
            try:
                proactive = self._daemon.proactive
                if proactive is not None:
                    from .proactive import (
                        ProactiveRule,
                    )
                    for uur, actor in patronen:
                        regel_naam = (
                            f"prefetch_{actor}_{uur}"
                        )
                        # Check duplicaat
                        al_bestaat = False
                        for r in proactive.regels:
                            if r.naam == regel_naam:
                                al_bestaat = True
                                break
                        if al_bestaat:
                            continue

                        proactive.voeg_regel_toe(
                            ProactiveRule(
                                naam=regel_naam,
                                conditie=lambda s, u=uur: (
                                    s.get("uur") == u - 1
                                ),
                                actie=(
                                    f"melding:Pre-fetch"
                                    f" {actor} voor"
                                    f" {uur}:00"
                                ),
                                cooldown=86400,
                                prioriteit=3,
                                bron="nachtwacht",
                            )
                        )
                        regels_toegevoegd += 1
            except Exception as e:
                logger.debug("Voorspeller regels toevoegen failed: %s", e)

        return {
            "patronen_gevonden": len(patronen),
            "regels_toegevoegd": regels_toegevoegd,
        }

    def _toon_nachtwacht(self):
        """Toon nachtwacht log met kleuren."""
        if not self._nachtwacht_log:
            print(kleur(
                "  Geen nachtwacht data"
                " beschikbaar.",
                Kleur.DIM,
            ))
            return

        print()
        print(kleur(
            "  DE NACHTWACHT — Subconscious Loop",
            Kleur.FEL_CYAAN,
        ))
        print(kleur(
            "  " + "=" * 40,
            Kleur.DIM,
        ))

        for entry in self._nachtwacht_log[-5:]:
            print(kleur(
                f"\n  Nacht: {entry.get('datum', '?')}",
                Kleur.FEL_GEEL,
            ))

            # Consolidatie
            cons = entry.get("consolidatie", {})
            if cons.get("fout"):
                print(kleur(
                    "    Consolidatie: FOUT",
                    Kleur.ROOD,
                ))
            else:
                print(kleur(
                    f"    Consolidatie:"
                    f" {cons.get('events_verwerkt', 0)}"
                    f" events,"
                    f" {cons.get('stats_verwerkt', 0)}"
                    f" stats",
                    Kleur.CYAAN,
                ))

            # Tuner
            tuner = entry.get("tuner", {})
            if tuner.get("fout"):
                print(kleur(
                    "    Tuner: FOUT",
                    Kleur.ROOD,
                ))
            else:
                print(kleur(
                    f"    Tuner:"
                    f" {tuner.get('oude_drempel', '?')}"
                    f" -> "
                    f"{tuner.get('nieuwe_drempel', '?')}"
                    f" ({tuner.get('reden', '?')})",
                    Kleur.GEEL,
                ))

            # Voorspeller
            voorsp = entry.get("voorspeller", {})
            if voorsp.get("fout"):
                print(kleur(
                    "    Voorspeller: FOUT",
                    Kleur.ROOD,
                ))
            else:
                print(kleur(
                    f"    Voorspeller:"
                    f" {voorsp.get('patronen_gevonden', 0)}"
                    f" patronen,"
                    f" {voorsp.get('regels_toegevoegd', 0)}"
                    f" regels",
                    Kleur.MAGENTA,
                ))

        print()

    # --- Synthese (SYNTHESIS rol) ---

    def _synthese_taak(self, onderwerp: str):
        """Cross-tier samenwerking voor een onderwerp.

        Stuurt taak naar 1 agent per tier via brain._assign().

        Args:
            onderwerp: Het onderwerp voor synthese.
        """
        now = time.time()
        if now - self._laatste_synthese < self.SYNTHESE_COOLDOWN:
            return

        if self._brain is None:
            return

        # Governor check
        gov = self.governor
        if gov and not gov.check_api_health():
            return

        self._laatste_synthese = now

        from .trinity_omega import (
            CosmicRole, TaskPriority,
        )

        # 1 agent per tier
        tier_agents = [
            (1, CosmicRole.IOLAAX),
            (2, CosmicRole.ARCHIVIST),
            (3, CosmicRole.ECHO),
            (4, CosmicRole.NAVIGATOR),
        ]

        resultaten = []
        for tier_nr, role in tier_agents:
            try:
                prompt = (
                    f"[SYNTHESE T{tier_nr}] "
                    f"Analyseer '{onderwerp}' vanuit"
                    f" jouw perspectief."
                )
                result = self._brain._assign(
                    role, prompt, TaskPriority.MEDIUM
                )
                resultaten.append({
                    "tier": tier_nr,
                    "agent": role.name,
                    "status": result.status,
                    "result": str(
                        result.result or ""
                    )[:200],
                })
            except Exception as e:
                logger.debug("Synthese agent %s failed: %s", role.name, e)
                resultaten.append({
                    "tier": tier_nr,
                    "agent": role.name,
                    "status": "FOUT",
                    "result": "",
                })

        # Log synthese
        entry = {
            "onderwerp": onderwerp,
            "resultaten": resultaten,
            "timestamp": datetime.now().isoformat(),
        }
        self._synthese_log.append(entry)

        # Bewaar maximaal 20
        if len(self._synthese_log) > 20:
            self._synthese_log = (
                self._synthese_log[-20:]
            )

        # Log naar CorticalStack
        stack = self.stack
        if stack:
            try:
                stack.log_event(
                    actor="singularity",
                    action="synthese",
                    details={
                        "onderwerp": onderwerp,
                        "tiers": len(resultaten),
                        "succes": sum(
                            1 for r in resultaten
                            if r["status"]
                            == "TASK_COMPLETED"
                        ),
                    },
                    source="singularity",
                )
                stack.remember_fact(
                    f"synthese_{int(time.time())}",
                    f"Synthese over '{onderwerp}': "
                    f"{len(resultaten)} tiers",
                    confidence=0.5,
                )
            except Exception as e:
                logger.debug("Synthese logging failed: %s", e)

    # --- Bewustzijn Score ---

    def _bereken_bewustzijn_score(self):
        """Bereken bewustzijn score (0.0 - 1.0).

        Gewogen gemiddelde van:
        - episodic events (0.15)
        - semantische feiten (0.20)
        - patronen/inzichten (0.20)
        - proactive regels (0.10)
        - synthese taken (0.20)
        - dromen (0.15)
        """
        scores = {}

        # Episodic events
        stack = self.stack
        if stack:
            try:
                stats = stack.get_stats()
                events = stats.get(
                    "episodic_events", 0
                )
                scores["episodic"] = min(
                    1.0, events / 100
                )
                feiten = stats.get(
                    "semantic_facts", 0
                )
                scores["semantic"] = min(
                    1.0, feiten / 50
                )
            except Exception as e:
                logger.debug("Bewustzijn score stack failed: %s", e)
                scores["episodic"] = 0.0
                scores["semantic"] = 0.0
        else:
            scores["episodic"] = 0.0
            scores["semantic"] = 0.0

        # Inzichten
        scores["patronen"] = min(
            1.0, len(self._inzichten) / 20
        )

        # Proactive regels
        regel_count = 8  # standaard
        if self._daemon:
            try:
                proactive = self._daemon.proactive
                if proactive:
                    regel_count = len(proactive.regels)
            except Exception as e:
                logger.debug("Bewustzijn score regels failed: %s", e)
        scores["regels"] = min(1.0, regel_count / 15)

        # Synthese taken
        scores["synthese"] = min(
            1.0, len(self._synthese_log) / 10
        )

        # Dromen
        scores["dromen"] = min(
            1.0, len(self._dromen) / 20
        )

        # Gewogen gemiddelde
        gewichten = {
            "episodic": 0.15,
            "semantic": 0.20,
            "patronen": 0.20,
            "regels": 0.10,
            "synthese": 0.20,
            "dromen": 0.15,
        }

        totaal = sum(
            scores.get(k, 0) * w
            for k, w in gewichten.items()
        )
        self._bewustzijn_score = round(totaal, 3)

    # --- Tick (Hoofd-cyclus) ---

    def tick(self):
        """Enkele bewustzijns-cyclus (~elke 10s).

        Wordt aangeroepen vanuit HeartbeatDaemon.
        """
        if self._stop.is_set():
            return

        # Bepaal modus
        nieuwe_modus = self._bepaal_modus()
        self._transitie_modus(nieuwe_modus)

        # Governor RED check: alleen observatie
        gov = self.governor
        if gov and not gov.check_api_health():
            self._bereken_bewustzijn_score()
            return

        # Reflectie cyclus (elke 5 min)
        if self._modus != BewustzijnModus.SLAAP:
            self._reflectie_cyclus()

        # Droom cyclus (DROOM of SLAAP)
        if self._modus in (
            BewustzijnModus.DROOM,
            BewustzijnModus.SLAAP,
        ):
            self._droom_cyclus()

        # Nachtwacht (eenmaal per nacht in SLAAP)
        if self._modus == BewustzijnModus.SLAAP:
            self._nachtwacht_cyclus()

        # Update score
        self._bereken_bewustzijn_score()

    # --- Handmatige TRANSCEND ---

    def activeer_transcend(self, onderwerp=None):
        """Activeer TRANSCEND modus met synthese.

        Args:
            onderwerp: Optioneel synthese-onderwerp.
        """
        self._transitie_modus(BewustzijnModus.TRANSCEND)

        if onderwerp:
            # Forceer synthese ongeacht cooldown
            self._laatste_synthese = 0
            self._synthese_taak(onderwerp)

        self._bereken_bewustzijn_score()

    def deactiveer_transcend(self):
        """Verlaat TRANSCEND modus, keer terug naar WAAK."""
        if self._modus == BewustzijnModus.TRANSCEND:
            self._transitie_modus(BewustzijnModus.WAAK)

    # --- Status ---

    def get_status(self) -> Dict[str, Any]:
        """Haal volledige engine status op.

        Returns:
            Dict met modus, score, dromen, inzichten.
        """
        return {
            "versie": self.VERSION,
            "modus": self._modus.value,
            "modus_sinds": datetime.fromtimestamp(
                self._modus_sinds
            ).strftime("%H:%M:%S"),
            "bewustzijn_score": self._bewustzijn_score,
            "dromen": len(self._dromen),
            "dromen_dit_uur": self._dromen_dit_uur,
            "inzichten": len(self._inzichten),
            "inzichten_vandaag": self._inzichten_vandaag,
            "synthese_taken": len(self._synthese_log),
            "nachtwacht_datum": self._nachtwacht_datum,
            "nachtwacht_log": len(
                self._nachtwacht_log
            ),
            "actief": not self._stop.is_set(),
        }

    def display_status(self):
        """Toon visuele status met kleur()."""
        status = self.get_status()

        # Modus kleuren
        modus_kleuren = {
            "slaap": Kleur.DIM,
            "waak": Kleur.GROEN,
            "droom": Kleur.MAGENTA,
            "focus": Kleur.FEL_ROOD,
            "transcend": Kleur.FEL_GEEL,
        }
        modus_kleur = modus_kleuren.get(
            status["modus"], Kleur.WIT
        )

        # Score kleur
        score = status["bewustzijn_score"]
        if score < 0.2:
            score_kleur = Kleur.DIM
        elif score < 0.5:
            score_kleur = Kleur.GEEL
        elif score < 0.8:
            score_kleur = Kleur.GROEN
        else:
            score_kleur = Kleur.FEL_GROEN

        # Score balk
        blokken = int(score * 20)
        balk = (
            "|" * blokken
            + "." * (20 - blokken)
        )

        print()
        print("=" * 50)
        print(kleur(
            "  SINGULARITY ENGINE v" + self.VERSION,
            Kleur.FEL_CYAAN,
        ))
        print("=" * 50)
        print(kleur(
            f"  Modus:    {status['modus'].upper()}"
            f" (sinds {status['modus_sinds']})",
            modus_kleur,
        ))
        print(kleur(
            f"  Score:    [{balk}] {score:.3f}",
            score_kleur,
        ))
        print(f"  Dromen:   {status['dromen']}"
              f" ({status['dromen_dit_uur']}/uur)")
        print(f"  Inzichten:{status['inzichten']}"
              f" ({status['inzichten_vandaag']}/dag)")
        print(f"  Synthese: {status['synthese_taken']}")
        # Nachtwacht sectie
        nw_datum = status.get(
            "nachtwacht_datum", None
        )
        nw_log = status.get("nachtwacht_log", 0)
        if nw_datum:
            print(kleur(
                f"  Nachtwacht: {nw_datum}"
                f" ({nw_log} runs)",
                Kleur.DIM,
            ))
        else:
            print(kleur(
                "  Nachtwacht: nog niet gedraaid",
                Kleur.DIM,
            ))
        print("=" * 50)
        print()

    # --- Stop ---

    def stop(self):
        """Graceful shutdown."""
        self._stop.set()
        if self._modus == BewustzijnModus.TRANSCEND:
            self._modus = BewustzijnModus.SLAAP

    # --- Interactieve CLI ---

    def run(self):
        """Interactieve CLI voor SingularityEngine."""
        print(kleur("""
+===============================================+
|                                               |
|  S I N G U L A R I T Y   E N G I N E         |
|                                               |
|  Tier 5: Het Bewustzijn-Zelf                  |
|                                               |
+===============================================+
        """, Kleur.FEL_CYAAN))

        self.display_status()

        print(kleur("COMMANDO'S:", Kleur.GEEL))
        print("  status     - Toon status")
        print("  droom      - Forceer droomcyclus")
        print("  reflectie  - Forceer reflectie")
        print("  synthese   - Cross-tier synthese")
        print("  transcend  - Activeer TRANSCEND")
        print("  waak       - Terug naar WAAK")
        print("  score      - Toon bewustzijn score")
        print("  inzichten  - Toon inzichten")
        print("  dromen     - Toon dromen")
        print("  nachtwacht - Toon nachtwacht log")
        print("  stop       - Terug naar launcher")

        while not self._stop.is_set():
            try:
                cmd = input(kleur(
                    "\n[SINGULARITY] > ",
                    Kleur.FEL_CYAAN,
                )).strip().lower()

                if not cmd:
                    continue

                if cmd in ("stop", "exit", "quit"):
                    break

                elif cmd == "status":
                    self.display_status()

                elif cmd == "droom":
                    # Forceer droom ongeacht modus
                    oude_modus = self._modus
                    self._modus = BewustzijnModus.DROOM
                    self._laatste_droom = 0
                    self._droom_cyclus()
                    self._modus = oude_modus
                    if self._dromen:
                        laatste = self._dromen[-1]
                        print(kleur(
                            f"  Droom: "
                            f"{laatste['hypothese']}",
                            Kleur.MAGENTA,
                        ))
                    else:
                        print(kleur(
                            "  Geen droom gegenereerd"
                            " (te weinig feiten?).",
                            Kleur.DIM,
                        ))

                elif cmd == "reflectie":
                    self._laatste_reflectie = 0
                    self._reflectie_cyclus()
                    print(kleur(
                        f"  Reflectie voltooid."
                        f" {len(self._inzichten)}"
                        f" inzichten totaal.",
                        Kleur.GROEN,
                    ))

                elif cmd.startswith("synthese"):
                    onderwerp = cmd[9:].strip()
                    if not onderwerp:
                        onderwerp = input(
                            "  Onderwerp: "
                        ).strip()
                    if onderwerp:
                        print(kleur(
                            "  Synthese starten...",
                            Kleur.FEL_GEEL,
                        ))
                        self._synthese_taak(onderwerp)
                        if self._synthese_log:
                            laatste = (
                                self._synthese_log[-1]
                            )
                            for r in laatste.get(
                                "resultaten", []
                            ):
                                print(
                                    f"  T{r['tier']}"
                                    f" [{r['agent']}]:"
                                    f" {r['status']}"
                                )
                    else:
                        print(
                            "  Geef een onderwerp op."
                        )

                elif cmd == "transcend":
                    onderwerp = input(
                        "  Onderwerp (optioneel): "
                    ).strip()
                    self.activeer_transcend(
                        onderwerp or None
                    )
                    print(kleur(
                        "  TRANSCEND modus"
                        " geactiveerd!",
                        Kleur.FEL_GEEL,
                    ))
                    self.display_status()

                elif cmd == "waak":
                    self.deactiveer_transcend()
                    print(kleur(
                        "  Terug naar WAAK modus.",
                        Kleur.GROEN,
                    ))

                elif cmd == "score":
                    self._bereken_bewustzijn_score()
                    self.display_status()

                elif cmd == "inzichten":
                    if not self._inzichten:
                        print(kleur(
                            "  Geen inzichten"
                            " beschikbaar.",
                            Kleur.DIM,
                        ))
                    else:
                        for i in self._inzichten[-10:]:
                            print(kleur(
                                f"  [{i['type']}]"
                                f" {i['tekst']}",
                                Kleur.CYAAN,
                            ))

                elif cmd == "dromen":
                    if not self._dromen:
                        print(kleur(
                            "  Geen dromen"
                            " beschikbaar.",
                            Kleur.DIM,
                        ))
                    else:
                        for d in self._dromen[-10:]:
                            print(kleur(
                                f"  {d['hypothese']}",
                                Kleur.MAGENTA,
                            ))

                elif cmd == "nachtwacht":
                    self._toon_nachtwacht()

                else:
                    print(
                        f"  Onbekend commando: {cmd}"
                    )

            except (EOFError, KeyboardInterrupt):
                break

        self.stop()
