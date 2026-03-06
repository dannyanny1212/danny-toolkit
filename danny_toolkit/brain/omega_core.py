"""
OmegaCore — Unified introspection interface voor alle Omega tiers.

Wraps T1-T5 modules + subsystemen als callable methods zodat
CentralBrain ze via function calling kan aanroepen.
"""

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class OmegaCore:
    """Unified gateway naar alle Omega Sovereign tiers en subsystemen.

    Lazy-loading: modules worden pas geïmporteerd bij eerste gebruik.
    Elk import-falen degradeert graceful (returns error dict).
    """

    def __init__(self):
        self._cache = {}

    # ── Helpers ──────────────────────────────────────────────────

    def _safe(self, factory, *args, **kwargs):
        """Roep factory aan, return None bij falen."""
        try:
            return factory(*args, **kwargs)
        except Exception as e:
            logger.debug("OmegaCore safe call failed: %s", e)
            return None

    # ── TOOL 1: system_scan ──────────────────────────────────────

    def system_scan(self) -> Dict[str, Any]:
        """Volledige systeem scan: alle tiers, modules, health, wirings."""
        result = {"tiers": {}, "subsystems": {}}

        # Introspector snapshot
        try:
            from danny_toolkit.brain.introspector import get_introspector
            intro = get_introspector()
            snap = intro.take_snapshot()
            result["total_modules"] = snap.totaal_modules
            result["active_modules"] = snap.actieve_modules
            result["health_score"] = f"{snap.gezondheid_score:.1%}"
            result["security"] = snap.security_status

            # Per-tier grouping
            tier_map = {"T1": [], "T2": [], "T3": [], "T4": [], "T5": []}
            tier_keywords = {
                "T1": ["prometheus", "arbitrator", "trinity"],
                "T2": ["governor", "tribunal", "hallucin", "truth_anchor", "schild"],
                "T3": ["strategist", "void_walker", "artificer", "dreamer",
                        "ghost_writer", "devops"],
                "T4": ["synapse", "phantom", "cortex", "oracle_eye"],
                "T5": ["singularity"],
            }
            for mod in snap.modules:
                name_lower = mod.naam.lower()
                placed = False
                for tier, keywords in tier_keywords.items():
                    if any(kw in name_lower for kw in keywords):
                        tier_map[tier].append({
                            "name": mod.naam,
                            "loaded": mod.geladen,
                            "singleton": mod.singleton_actief,
                            "fault": mod.fout,
                        })
                        placed = True
                        break
                if not placed:
                    tier_map.setdefault("subsystem", []).append({
                        "name": mod.naam,
                        "loaded": mod.geladen,
                    })

            result["tiers"] = tier_map

            # Wirings
            active_wirings = sum(1 for w in snap.wirings if w.actief)
            total_wirings = len(snap.wirings)
            result["wirings"] = f"{active_wirings}/{total_wirings} actief"

        except Exception as e:
            result["error"] = f"Introspector unavailable: {e}"

        return result

    # ── TOOL 2: tier_detail ──────────────────────────────────────

    def tier_detail(self, tier: int = 1) -> Dict[str, Any]:
        """Diepgaande info over een specifieke tier (1-5)."""
        result = {"tier": f"T{tier}"}

        if tier == 1:
            result["name"] = "TRINITY — Het Bewustzijn"
            result["nodes"] = self._t1_trinity()
        elif tier == 2:
            result["name"] = "GUARDIANS — De Beschermers"
            result["nodes"] = self._t2_guardians()
        elif tier == 3:
            result["name"] = "SPECIALISTS — De Werkers"
            result["nodes"] = self._t3_specialists()
        elif tier == 4:
            result["name"] = "INFRA — De Fundering"
            result["nodes"] = self._t4_infra()
        elif tier == 5:
            result["name"] = "SINGULARITY — Het Bewustzijn-Zelf"
            result["nodes"] = self._t5_singularity()
        else:
            result["error"] = f"Ongeldige tier: {tier}. Kies 1-5."

        return result

    def _t1_trinity(self) -> Dict:
        nodes = {}
        # PrometheusBrain
        try:
            from danny_toolkit.brain.trinity_models import CosmicRole, NodeTier
            from danny_toolkit.brain.trinity_omega import PrometheusBrain
            nodes["PrometheusBrain"] = {
                "status": "LOADED",
                "roles": [r.value for r in CosmicRole],
                "tiers": [t.name for t in NodeTier],
                "description": "17-pillar federated swarm, Chain of Command pipeline",
            }
        except Exception as e:
            nodes["PrometheusBrain"] = {"status": "ERROR", "error": str(e)}

        # TaskArbitrator
        try:
            from danny_toolkit.brain.arbitrator import TaskArbitrator
            nodes["TaskArbitrator"] = {
                "status": "LOADED",
                "description": "Goal decomposition + auction-based agent assignment",
            }
        except Exception as e:
            nodes["TaskArbitrator"] = {"status": "ERROR", "error": str(e)}

        return nodes

    def _t2_guardians(self) -> Dict:
        nodes = {}
        # Governor
        try:
            from danny_toolkit.brain.governor import OmegaGovernor
            nodes["OmegaGovernor"] = {
                "status": "LOADED",
                "description": "Rate limits, injection detectie, PII scrubbing, circuit breaker",
            }
        except Exception as e:
            nodes["OmegaGovernor"] = {"status": "ERROR", "error": str(e)}

        # HallucinatieSchild
        try:
            from danny_toolkit.brain.hallucination_shield import get_hallucination_shield
            schild = self._safe(get_hallucination_shield)
            if schild:
                stats = schild.get_stats()
                nodes["HallucinatieSchild"] = {
                    "status": "ACTIVE",
                    "checks": stats.get("beoordeeld", 0),
                    "blocked": stats.get("geblokkeerd", 0),
                    "description": "Anti-hallucinatie gate: claim-scoring, contradictie-detectie",
                }
            else:
                nodes["HallucinatieSchild"] = {"status": "LOADED"}
        except Exception as e:
            nodes["HallucinatieSchild"] = {"status": "ERROR", "error": str(e)}

        # Tribunal
        try:
            from danny_toolkit.brain.adversarial_tribunal import get_adversarial_tribunal
            trib = self._safe(get_adversarial_tribunal)
            if trib:
                stats = trib.get_stats()
                nodes["Tribunal"] = {
                    "status": "ACTIVE",
                    "verdicts": stats.get("verdicts", stats.get("total", 0)),
                    "description": "Generator-Skeptic-Judge consensus verificatie",
                }
            else:
                nodes["Tribunal"] = {"status": "LOADED"}
        except Exception as e:
            nodes["Tribunal"] = {"status": "ERROR", "error": str(e)}

        # BlackBox
        try:
            from danny_toolkit.brain.black_box import get_black_box
            bb = self._safe(get_black_box)
            if bb:
                stats = bb.get_stats()
                nodes["BlackBox"] = {
                    "status": "ACTIVE",
                    "antibodies": stats.get("total_antibodies", 0),
                    "description": "Immune memory — leert van fouten, voorkomt herhalingen",
                }
            else:
                nodes["BlackBox"] = {"status": "LOADED"}
        except Exception as e:
            nodes["BlackBox"] = {"status": "ERROR", "error": str(e)}

        return nodes

    def _t3_specialists(self) -> Dict:
        nodes = {}
        specs = {
            "Strategist": ("danny_toolkit.brain.strategist", "Strategist",
                           "Recursieve task planner met search-query meta-filter"),
            "VoidWalker": ("danny_toolkit.brain.void_walker", "VoidWalker",
                           "Autonome web researcher via DuckDuckGo + scraper"),
            "Artificer": ("danny_toolkit.brain.artificer", "Artificer",
                          "Skill forge-verify-execute loop"),
            "Dreamer": ("danny_toolkit.brain.dreamer", "Dreamer",
                        "Overnight REM cycle: backup, vacuum, GhostWriter, anticipatie"),
            "GhostWriter": ("danny_toolkit.brain.ghost_writer", "GhostWriter",
                            "AST scanner + auto-docstring generatie via Groq"),
            "DevOpsDaemon": ("danny_toolkit.brain.devops_daemon", "DevOpsDaemon",
                             "Ouroboros CI loop: test→analyze→BlackBox→NeuralBus"),
        }
        for name, (module, cls, desc) in specs.items():
            try:
                __import__(module)
                nodes[name] = {"status": "LOADED", "description": desc}
            except Exception as e:
                nodes[name] = {"status": "ERROR", "error": str(e)}
        return nodes

    def _t4_infra(self) -> Dict:
        nodes = {}

        # TheSynapse
        try:
            from danny_toolkit.brain.synapse import TheSynapse
            syn = TheSynapse()
            stats = syn.get_stats()
            nodes["TheSynapse"] = {
                "status": "ACTIVE",
                "pathways": stats.get("pathway_count", 0),
                "interactions": stats.get("interaction_count", 0),
                "avg_strength": round(stats.get("avg_strength", 0), 3),
                "description": "Hebbian routing — leert welke routes het beste werken",
            }
        except Exception as e:
            nodes["TheSynapse"] = {"status": "ERROR", "error": str(e)}

        # ThePhantom
        try:
            from danny_toolkit.brain.phantom import ThePhantom
            ph = ThePhantom()
            acc = ph.get_accuracy()
            preds = ph.get_predictions(max_results=3)
            nodes["ThePhantom"] = {
                "status": "ACTIVE",
                "accuracy": acc,
                "top_predictions": preds[:3],
                "description": "Anticipatory intelligence — voorspelt queries, pre-warmt context",
            }
        except Exception as e:
            nodes["ThePhantom"] = {"status": "ERROR", "error": str(e)}

        # TheCortex
        try:
            from danny_toolkit.brain.cortex import TheCortex
            cx = TheCortex()
            stats = cx.get_stats()
            nodes["TheCortex"] = {
                "status": "ACTIVE",
                "nodes": stats.get("nodes", stats.get("graph_nodes", 0)),
                "edges": stats.get("edges", stats.get("graph_edges", 0)),
                "description": "Knowledge Graph (SQLite+NetworkX) hybrid search",
            }
        except Exception as e:
            nodes["TheCortex"] = {"status": "ERROR", "error": str(e)}

        # OracleEye
        try:
            from danny_toolkit.brain.oracle_eye import TheOracleEye
            oe = TheOracleEye()
            peak = oe.get_peak_hours(days=7)
            nodes["OracleEye"] = {
                "status": "ACTIVE",
                "peak_hours": peak,
                "description": "Predictive resource scaler — CPU/geheugen/API monitoring",
            }
        except Exception as e:
            nodes["OracleEye"] = {"status": "ERROR", "error": str(e)}

        return nodes

    def _t5_singularity(self) -> Dict:
        nodes = {}
        try:
            from danny_toolkit.brain.singularity import SingularityEngine
            se = SingularityEngine()
            status = se.get_status()
            nodes["SingularityEngine"] = {
                "status": "ACTIVE",
                "modus": status.get("modus", "?"),
                "bewustzijn_score": status.get("bewustzijn_score", 0),
                "dromen": status.get("dromen", 0),
                "inzichten": status.get("inzichten", 0),
                "description": "Consciousness — reflect, dream, cross-tier synthese",
            }
        except Exception as e:
            nodes["SingularityEngine"] = {"status": "ERROR", "error": str(e)}
        return nodes

    # ── TOOL 3: query_knowledge ──────────────────────────────────

    def query_knowledge(self, query: str = "omega") -> Dict[str, Any]:
        """Doorzoek de Cortex Knowledge Graph."""
        result = {}
        try:
            from danny_toolkit.brain.cortex import TheCortex
            cx = TheCortex()
            hits = cx.hybrid_search(query, top_k=5)
            result["query"] = query
            result["results"] = hits[:5]
            stats = cx.get_stats()
            result["graph_size"] = stats
        except Exception as e:
            result["error"] = f"Cortex unavailable: {e}"
        return result

    # ── TOOL 4: memory_recall ────────────────────────────────────

    def memory_recall(self, query: str = "", count: int = 10) -> Dict[str, Any]:
        """Doorzoek CorticalStack episodic memory."""
        result = {}
        try:
            from danny_toolkit.brain.cortical_stack import get_cortical_stack
            cs = get_cortical_stack()
            result["db_metrics"] = cs.get_db_metrics()
            events = cs.get_recent_events(count=count)
            result["recent_events"] = events[:count]
            if query:
                # Semantic search in cortical stack
                search_results = cs.search(query, top_k=5) if hasattr(cs, 'search') else []
                result["search_results"] = search_results
        except Exception as e:
            result["error"] = f"CorticalStack unavailable: {e}"
        return result

    # ── TOOL 5: immune_report ────────────────────────────────────

    def immune_report(self) -> Dict[str, Any]:
        """BlackBox + HallucinatieSchild + Governor + Tribunal status."""
        result = {}

        # BlackBox
        try:
            from danny_toolkit.brain.black_box import get_black_box
            bb = self._safe(get_black_box)
            if bb:
                result["blackbox"] = bb.get_stats()
        except Exception:
            result["blackbox"] = {"status": "unavailable"}

        # Schild
        try:
            from danny_toolkit.brain.hallucination_shield import get_hallucination_shield
            schild = self._safe(get_hallucination_shield)
            if schild:
                result["hallucination_shield"] = schild.get_stats()
        except Exception:
            result["hallucination_shield"] = {"status": "unavailable"}

        # Tribunal
        try:
            from danny_toolkit.brain.adversarial_tribunal import get_adversarial_tribunal
            trib = self._safe(get_adversarial_tribunal)
            if trib:
                result["tribunal"] = trib.get_stats()
        except Exception:
            result["tribunal"] = {"status": "unavailable"}

        # Waakhuis
        try:
            from danny_toolkit.brain.waakhuis import get_waakhuis
            wh = self._safe(get_waakhuis)
            if wh:
                result["waakhuis"] = wh.gezondheidsrapport()
        except Exception:
            result["waakhuis"] = {"status": "unavailable"}

        return result

    # ── TOOL 6: neural_activity ──────────────────────────────────

    def neural_activity(self, event_count: int = 10) -> Dict[str, Any]:
        """NeuralBus events + Synapse routing + Phantom predictions."""
        result = {}

        # NeuralBus
        try:
            from danny_toolkit.core.neural_bus import get_bus
            bus = self._safe(get_bus)
            if bus:
                result["bus_stats"] = bus.statistieken()
                result["recent_events"] = bus.get_context_stream(count=event_count)
        except Exception:
            result["bus"] = {"status": "unavailable"}

        # Synapse
        try:
            from danny_toolkit.brain.synapse import TheSynapse
            syn = TheSynapse()
            result["synapse"] = syn.get_stats()
            result["top_pathways"] = syn.get_top_pathways(limit=5)
        except Exception:
            result["synapse"] = {"status": "unavailable"}

        # Phantom
        try:
            from danny_toolkit.brain.phantom import ThePhantom
            ph = ThePhantom()
            result["phantom_accuracy"] = ph.get_accuracy()
            result["phantom_predictions"] = ph.get_predictions(max_results=3)
        except Exception:
            result["phantom"] = {"status": "unavailable"}

        # ModelRegistry
        try:
            from danny_toolkit.brain.model_sync import get_model_registry
            mr = self._safe(get_model_registry)
            if mr:
                result["model_registry"] = mr.get_stats()
        except Exception:
            result["model_registry"] = {"status": "unavailable"}

        return result
