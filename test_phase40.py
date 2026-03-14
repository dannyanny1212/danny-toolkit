#!/usr/bin/env python3
"""
Test Phase 40: Swarm Sovereignty — TaskArbitrator
==================================================
18 tests · 110 checks

Valideert:
  A. Datamodellen (SwarmTask, GoalManifest, AuctionBid)
  B. Singleton identity + concurrency
  C. Exports + __all__
  D. Decompose (mock LLM) + fallback
  E. Auction formule + hoogste-wint + fallback ECHO
  F. Synthesize resultaten
  G. Stats accumulatie
  H. _parse_tasks edge cases
  I. SwarmEngine.execute_goal() methode
  J. FastAPI models + route
  K. inspect.getsource() wiring + NeuralBus sovereignty
  L. Version 6.7.0

Gebruik:
    CUDA_VISIBLE_DEVICES=-1 DANNY_TEST_MODE=1 ANONYMIZED_TELEMETRY=False \
        python test_phase40.py
"""
from __future__ import annotations

import importlib
import inspect
import json
import logging
import os
import sys
import threading
import time
import unittest
import uuid

logger = logging.getLogger(__name__)

os.environ.setdefault("DANNY_TEST_MODE", "1")
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "-1")
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")

# Windows UTF-8
if os.name == "nt":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (ValueError, OSError):
        logger.debug("UTF-8 reconfigure niet mogelijk")

CHECK = 0


def c(ok: bool, label: str = "") -> None:
    """Verificatie helper voor test checks."""
    global CHECK
    CHECK += 1
    tag = f" ({label})" if label else ""
    status = "OK" if ok else "FAIL"
    print(f"  check {CHECK}: {status}{tag}")
    assert ok, f"Check {CHECK} failed{tag}"


class TestPhase40(unittest.TestCase):
    """Phase 40: Swarm Sovereignty — TaskArbitrator."""

    # ── Test 1: Datamodellen instantieerbaar ──

    def test_01_datamodels(self) -> None:
        """SwarmTask + GoalManifest + AuctionBid velden + defaults + to_dict."""
        print("\n[Test 1] Datamodellen")
        try:
            from danny_toolkit.brain.arbitrator import (
                AuctionBid, GoalManifest, SwarmTask,
            )
        except ImportError:
            logger.debug("arbitrator import niet beschikbaar")
            raise

        t = SwarmTask(
            task_id="abc123",
            beschrijving="Test taak",
            categorie="analyse",
            prioriteit=1,
        )
        c(t.task_id == "abc123", "SwarmTask.task_id")
        c(t.status == "pending", "SwarmTask.status default")
        c(t.resultaat is None, "SwarmTask.resultaat default")
        c(t.toegewezen_agent == "", "SwarmTask.toegewezen_agent default")
        c(t.prioriteit == 1, "SwarmTask.prioriteit")

        d = t.to_dict()
        c(isinstance(d, dict), "SwarmTask.to_dict()")
        c("task_id" in d and "beschrijving" in d, "to_dict keys")

        m = GoalManifest(goal="Test goal")
        c(m.goal == "Test goal", "GoalManifest.goal")
        c(m.status == "planning", "GoalManifest.status default")
        c(isinstance(m.taken, list) and len(m.taken) == 0, "GoalManifest.taken empty")
        c(m.created_at > 0, "GoalManifest.created_at")

        md = m.to_dict()
        c(isinstance(md, dict), "GoalManifest.to_dict()")
        c("goal" in md and "taken" in md and "status" in md, "manifest to_dict keys")

        bid = AuctionBid(agent="ECHO", score=0.85, context_match=0.9, current_load=0.05)
        c(bid.agent == "ECHO", "AuctionBid.agent")
        c(abs(bid.score - 0.85) < 1e-6, "AuctionBid.score")

    # ── Test 2: Singleton identity ──

    def test_02_singleton_identity(self) -> None:
        """Get_arbitrator() retourneert dezelfde instantie."""
        print("\n[Test 2] Singleton identity")
        try:
            from danny_toolkit.brain.arbitrator import get_arbitrator
        except ImportError:
            logger.debug("arbitrator import niet beschikbaar")
            raise

        a = get_arbitrator()
        b = get_arbitrator()
        c(a is b, "id(a) is id(b)")
        c(id(a) == id(b), "id(a) == id(b)")

    # ── Test 3: Singleton thread safety (50 threads) ──

    def test_03_singleton_concurrency(self) -> None:
        """50 threads naar exact 1 uniek id."""
        print("\n[Test 3] Singleton concurrency (50 threads)")

        try:
            import danny_toolkit.brain.arbitrator as arb_mod
        except ImportError:
            logger.debug("arbitrator import niet beschikbaar")
            raise
        arb_mod._arbitrator_instance = None

        ids = []
        barrier = threading.Barrier(50)

        def grab() -> None:
            """Grab arbitrator instance na barrier."""
            barrier.wait()
            from danny_toolkit.brain.arbitrator import get_arbitrator
            ids.append(id(get_arbitrator()))

        threads = [threading.Thread(target=grab) for _ in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        unique = set(ids)
        c(len(unique) == 1, f"unique ids: {len(unique)} == 1")
        c(len(ids) == 50, f"total grabs: {len(ids)} == 50")

    # ── Test 4: Exports in brain __init__ + __all__ ──

    def test_04_exports(self) -> None:
        """TaskArbitrator, get_arbitrator, GoalManifest, SwarmTask in exports."""
        print("\n[Test 4] Exports")
        try:
            import danny_toolkit.brain as brain
        except ImportError:
            logger.debug("brain import niet beschikbaar")
            raise

        c(hasattr(brain, "TaskArbitrator"), "TaskArbitrator in brain")
        c(hasattr(brain, "get_arbitrator"), "get_arbitrator in brain")
        c(hasattr(brain, "GoalManifest"), "GoalManifest in brain")
        c(hasattr(brain, "SwarmTask"), "SwarmTask in brain")

        c("TaskArbitrator" in brain.__all__, "TaskArbitrator in __all__")
        c("get_arbitrator" in brain.__all__, "get_arbitrator in __all__")
        c("GoalManifest" in brain.__all__, "GoalManifest in __all__")
        c("SwarmTask" in brain.__all__, "SwarmTask in __all__")

    # ── Test 5: Decompose met mock LLM ──

    def test_05_decompose_mock(self) -> None:
        """Decompose met valide JSON naar SwarmTask lijst + trace_id."""
        print("\n[Test 5] Decompose (mock LLM)")
        import asyncio
        try:
            from danny_toolkit.brain.arbitrator import TaskArbitrator, GoalManifest
        except ImportError:
            logger.debug("arbitrator import niet beschikbaar")
            raise

        arb = TaskArbitrator()

        mock_json = json.dumps([
            {"beschrijving": "Analyseer BlackBox integriteit", "categorie": "analyse", "prioriteit": 1},
            {"beschrijving": "Verifieer antibodies", "categorie": "verificatie", "prioriteit": 2},
            {"beschrijving": "Pruning van oude entries", "categorie": "pruning", "prioriteit": 3},
        ])

        async def fake_llm(goal: str) -> str:
            """Mock LLM die JSON teruggeeft."""
            return mock_json
        arb._call_decompose_llm = fake_llm

        manifest = asyncio.run(arb.decompose("Audit de BlackBox"))
        c(isinstance(manifest, GoalManifest), "manifest is GoalManifest")
        c(manifest.status == "decomposed", "status == decomposed")
        c(len(manifest.taken) == 3, f"3 taken: {len(manifest.taken)}")
        c(manifest.taken[0].categorie == "analyse", "eerste taak categorie")
        c(manifest.taken[1].categorie == "verificatie", "tweede taak categorie")
        c(manifest.taken[2].prioriteit == 3, "derde taak prioriteit")
        c(len(manifest.trace_id) == 12, f"trace_id len: {len(manifest.trace_id)}")

    # ── Test 6: Decompose fallback (bad JSON) ──

    def test_06_decompose_fallback(self) -> None:
        """Decompose met ongeldige JSON naar single fallback task."""
        print("\n[Test 6] Decompose fallback")
        import asyncio
        try:
            from danny_toolkit.brain.arbitrator import TaskArbitrator
        except ImportError:
            logger.debug("arbitrator import niet beschikbaar")
            raise

        arb = TaskArbitrator()

        async def bad_llm(goal: str) -> str:
            """Mock LLM die ongeldige JSON teruggeeft."""
            return "Dit is geen JSON helemaal niet"
        arb._call_decompose_llm = bad_llm

        manifest = asyncio.run(arb.decompose("Doe iets"))
        c(len(manifest.taken) == 1, "fallback: 1 taak")
        c(manifest.taken[0].beschrijving == "Doe iets", "fallback beschrijving == goal")
        c(manifest.taken[0].categorie == "analyse", "fallback categorie == analyse")

    # ── Test 7: Auction formule correctheid ──

    def test_07_auction_formula(self) -> None:
        """S_agent = context_match / (current_load + 1) voor alle agents."""
        print("\n[Test 7] Auction formule")
        try:
            from danny_toolkit.brain.arbitrator import TaskArbitrator, SwarmTask, AuctionBid
        except ImportError:
            logger.debug("arbitrator import niet beschikbaar")
            raise

        arb = TaskArbitrator()

        class FakeSynapse:
            """Mock synapse voor routing bias."""

            def get_routing_bias(self, text: str) -> dict:
                """Retourneer mock routing bias."""
                return {"ECHO": 0.9, "MEMEX": 0.7, "STRATEGIST": 0.5}

        class FakeWaakhuis:
            """Mock waakhuis voor latency rapport."""

            def latency_rapport(self, agent: str) -> dict:
                """Retourneer mock latency rapport."""
                loads = {"ECHO": 10, "MEMEX": 50, "STRATEGIST": 0}
                return {"count": loads.get(agent, 0)}

        arb._synapse = FakeSynapse()
        arb._waakhuis = FakeWaakhuis()

        task = SwarmTask(task_id="t1", beschrijving="test", categorie="analyse")
        bid = arb.auction(task)

        c(isinstance(bid, AuctionBid), "bid is AuctionBid")

        # Verwachte scores:
        # ECHO:       0.9 / (10/100 + 1) = 0.9 / 1.1  ~ 0.8182
        # MEMEX:      0.7 / (50/100 + 1) = 0.7 / 1.5  ~ 0.4667
        # STRATEGIST: 0.5 / (0/100 + 1)  = 0.5 / 1.0  = 0.5
        echo_exp = round(0.9 / 1.1, 4)
        memex_exp = round(0.7 / 1.5, 4)
        strat_exp = round(0.5 / 1.0, 4)

        c(bid.agent == "ECHO", f"winnaar: {bid.agent} == ECHO")
        c(abs(bid.score - echo_exp) < 0.01, f"ECHO score: {bid.score} ~ {echo_exp}")

        # ECHO > STRATEGIST > MEMEX
        c(echo_exp > strat_exp, f"ECHO ({echo_exp}) > STRATEGIST ({strat_exp})")
        c(strat_exp > memex_exp, f"STRATEGIST ({strat_exp}) > MEMEX ({memex_exp})")

    # ── Test 8: Auction hoogste score wint ──

    def test_08_auction_highest_wins(self) -> None:
        """Agent met hoogste S wint altijd, context_match bewaard."""
        print("\n[Test 8] Auction: hoogste wint")
        try:
            from danny_toolkit.brain.arbitrator import TaskArbitrator, SwarmTask
        except ImportError:
            logger.debug("arbitrator import niet beschikbaar")
            raise

        arb = TaskArbitrator()

        class HighBiasSynapse:
            """Mock synapse met hoge bias voor AGENT_B."""

            def get_routing_bias(self, text: str) -> dict:
                """Retourneer mock routing bias."""
                return {"AGENT_A": 0.3, "AGENT_B": 0.99, "AGENT_C": 0.5}

        class NoLoadWaakhuis:
            """Mock waakhuis zonder load."""

            def latency_rapport(self, agent: str) -> dict:
                """Retourneer mock latency rapport zonder load."""
                return {"count": 0}

        arb._synapse = HighBiasSynapse()
        arb._waakhuis = NoLoadWaakhuis()

        task = SwarmTask(task_id="t2", beschrijving="test2", categorie="code")
        bid = arb.auction(task)

        c(bid.agent == "AGENT_B", f"AGENT_B wint: {bid.agent}")
        c(bid.score >= 0.99, f"score >= 0.99: {bid.score}")
        c(bid.context_match >= 0.99, f"context_match bewaard: {bid.context_match}")
        c(abs(bid.current_load) < 0.01, f"load ~ 0: {bid.current_load}")

    # ── Test 9: Auction fallback → ECHO ──

    def test_09_auction_fallback_echo(self) -> None:
        """Geen synapse/router data naar fallback naar ECHO agent."""
        print("\n[Test 9] Auction fallback ECHO")
        try:
            from danny_toolkit.brain.arbitrator import TaskArbitrator, SwarmTask, AuctionBid
        except ImportError:
            logger.debug("arbitrator import niet beschikbaar")
            raise

        arb = TaskArbitrator()

        class EmptySynapse:
            """Mock synapse zonder data."""

            def get_routing_bias(self, text: str) -> dict:
                """Retourneer lege routing bias."""
                return {}

        arb._synapse = EmptySynapse()
        arb._waakhuis = None

        task = SwarmTask(task_id="t3", beschrijving="onbekend", categorie="analyse")
        bid = arb.auction(task, available_agents=["NONEXISTENT"])

        c(isinstance(bid, AuctionBid), "bid is AuctionBid")
        c(bid.agent == "ECHO", f"fallback agent: {bid.agent} == ECHO")
        c(bid.score == 0.0, f"fallback score: {bid.score} == 0.0")
        c(bid.context_match == 0.0, "fallback context_match == 0.0")

    # ── Test 10: Synthesize resultaten ──

    def test_10_synthesize(self) -> None:
        """Synthesize combineert resultaten van voltooide taken."""
        print("\n[Test 10] Synthesize")
        try:
            from danny_toolkit.brain.arbitrator import (
                TaskArbitrator, GoalManifest, SwarmTask,
            )
        except ImportError:
            logger.debug("arbitrator import niet beschikbaar")
            raise
        from dataclasses import dataclass

        @dataclass
        class FakePayload:
            """Mock payload voor test resultaten."""
            display_text: str = ""
            content: str = ""

        arb = TaskArbitrator()

        manifest = GoalManifest(goal="Test synthese")
        manifest.taken = [
            SwarmTask(task_id="s1", beschrijving="t1", categorie="a",
                      toegewezen_agent="ECHO", status="done",
                      resultaat=FakePayload(display_text="Resultaat A")),
            SwarmTask(task_id="s2", beschrijving="t2", categorie="b",
                      toegewezen_agent="MEMEX", status="done",
                      resultaat=FakePayload(display_text="Resultaat B")),
            SwarmTask(task_id="s3", beschrijving="t3", categorie="c",
                      toegewezen_agent="STRAT", status="failed",
                      resultaat=None),
        ]

        synthese = arb.synthesize(manifest)
        c(isinstance(synthese, str), "synthese is str")
        c("Resultaat A" in synthese, "Resultaat A in synthese")
        c("Resultaat B" in synthese, "Resultaat B in synthese")
        c("[ECHO]" in synthese, "[ECHO] agent tag in synthese")
        c("[MEMEX]" in synthese, "[MEMEX] agent tag in synthese")

        # Leeg manifest → fallback bericht
        empty = GoalManifest(goal="Leeg doel")
        empty_synthese = arb.synthesize(empty)
        c("kon niet" in empty_synthese.lower() or "leeg doel" in empty_synthese.lower(),
          "lege synthese bevat fallback")

    # ── Test 11: Stats accumulatie ──

    def test_11_stats_accumulation(self) -> None:
        """Stats incrementen na decompose + auction operaties."""
        print("\n[Test 11] Stats accumulatie")
        import asyncio
        try:
            from danny_toolkit.brain.arbitrator import TaskArbitrator, SwarmTask
        except ImportError:
            logger.debug("arbitrator import niet beschikbaar")
            raise

        arb = TaskArbitrator()

        # Nulpunt
        stats_before = arb.get_stats()
        goals_before = stats_before["goals_processed"]
        tasks_before = stats_before["tasks_decomposed"]
        auctions_before = stats_before["auctions_held"]

        # Decompose
        async def fake_llm(goal: str) -> str:
            """Mock LLM voor stats test."""
            return json.dumps([
                {"beschrijving": "taak1", "categorie": "code", "prioriteit": 1},
                {"beschrijving": "taak2", "categorie": "analyse", "prioriteit": 2},
            ])
        arb._call_decompose_llm = fake_llm

        manifest = asyncio.run(arb.decompose("Stats test"))
        stats_after_decompose = arb.get_stats()
        c(stats_after_decompose["goals_processed"] == goals_before + 1,
          "goals_processed +1")
        c(stats_after_decompose["tasks_decomposed"] == tasks_before + 2,
          "tasks_decomposed +2")

        # Auction
        class SimpleSynapse:
            """Mock synapse voor auction test."""

            def get_routing_bias(self, text: str) -> dict:
                """Retourneer simpele routing bias."""
                return {"ECHO": 0.8}
        arb._synapse = SimpleSynapse()

        task = SwarmTask(task_id="st1", beschrijving="x", categorie="y")
        arb.auction(task)
        stats_after_auction = arb.get_stats()
        c(stats_after_auction["auctions_held"] == auctions_before + 1,
          "auctions_held +1")

    # ── Test 12: _parse_tasks edge cases ──

    def test_12_parse_tasks_edge(self) -> None:
        """Max 5 taken cap, embedded JSON, empty array."""
        print("\n[Test 12] _parse_tasks edge cases")
        try:
            from danny_toolkit.brain.arbitrator import TaskArbitrator
        except ImportError:
            logger.debug("arbitrator import niet beschikbaar")
            raise

        arb = TaskArbitrator()

        # 7 taken → max 5
        big = json.dumps([
            {"beschrijving": f"taak{i}", "categorie": "code", "prioriteit": 1}
            for i in range(7)
        ])
        tasks = arb._parse_tasks(big, "overflow test")
        c(len(tasks) == 5, f"max 5 cap: {len(tasks)}")
        c(tasks[0].beschrijving == "taak0", "eerste taak intact")

        # Embedded JSON in tekst
        task_data = json.dumps([{"beschrijving": "sub", "categorie": "analyse"}])
        embedded = f"Hier is het plan: {task_data}"
        tasks2 = arb._parse_tasks(embedded, "embedded test")
        c(len(tasks2) >= 1, f"embedded parse: {len(tasks2)} taken")

        # Lege array → fallback
        tasks3 = arb._parse_tasks("[]", "leeg goal")
        c(len(tasks3) == 1, "lege array -> 1 fallback taak")
        c(tasks3[0].beschrijving == "leeg goal", "fallback = oorspronkelijk goal")

        # Helemaal geen JSON → fallback
        tasks4 = arb._parse_tasks("gewoon tekst", "tekst goal")
        c(len(tasks4) == 1, "geen JSON -> 1 fallback taak")

    # ── Test 13: SwarmEngine.execute_goal() methode ──

    def test_13_execute_goal_exists(self) -> None:
        """SwarmEngine heeft execute_goal() async methode met goal param."""
        print("\n[Test 13] SwarmEngine.execute_goal()")
        try:
            from swarm_engine import SwarmEngine
        except ImportError:
            logger.debug("swarm_engine import niet beschikbaar")
            raise

        c(hasattr(SwarmEngine, "execute_goal"), "execute_goal exists")
        c(callable(getattr(SwarmEngine, "execute_goal", None)), "execute_goal callable")

        sig = inspect.signature(SwarmEngine.execute_goal)
        params = list(sig.parameters.keys())
        c("goal" in params, f"'goal' param: {params}")
        c(inspect.iscoroutinefunction(SwarmEngine.execute_goal), "execute_goal is async")

    # ── Test 14: FastAPI models ──

    def test_14_fastapi_models(self) -> None:
        """GoalRequest, GoalResponse, SwarmTaskResponse Pydantic models."""
        print("\n[Test 14] FastAPI models")
        try:
            from fastapi_server import GoalRequest, GoalResponse, SwarmTaskResponse
        except ImportError:
            logger.debug("fastapi_server import niet beschikbaar")
            raise

        gr = GoalRequest(goal="Test doel")
        c(gr.goal == "Test doel", "GoalRequest.goal")

        st = SwarmTaskResponse(
            task_id="x1", beschrijving="taak", categorie="code",
            toegewezen_agent="ECHO", status="done",
        )
        c(st.task_id == "x1", "SwarmTaskResponse.task_id")
        c(st.toegewezen_agent == "ECHO", "SwarmTaskResponse.agent")
        c(st.resultaat_preview == "", "SwarmTaskResponse.resultaat_preview default")

        resp = GoalResponse(
            goal="doel", status="done",
            taken=[st], synthese="resultaat",
            execution_time=1.23, trace_id="abc",
        )
        c(resp.goal == "doel", "GoalResponse.goal")
        c(len(resp.taken) == 1, "GoalResponse.taken count")
        c(resp.synthese == "resultaat", "GoalResponse.synthese")
        c(resp.execution_time == 1.23, "GoalResponse.execution_time")
        c(resp.trace_id == "abc", "GoalResponse.trace_id")

    # ── Test 15: FastAPI /api/v1/swarm/goal route ──

    def test_15_fastapi_route(self) -> None:
        """POST /api/v1/swarm/goal route geregistreerd met Swarm tag."""
        print("\n[Test 15] FastAPI route")
        try:
            from fastapi_server import app
        except ImportError:
            logger.debug("fastapi_server import niet beschikbaar")
            raise

        routes = {}
        for r in app.routes:
            if hasattr(r, "methods"):
                routes[r.path] = r

        c("/api/v1/swarm/goal" in routes, "/api/v1/swarm/goal registered")
        c("POST" in routes["/api/v1/swarm/goal"].methods,
          "POST method on /api/v1/swarm/goal")

        # Verify Swarm tag
        route = routes["/api/v1/swarm/goal"]
        tags = getattr(route, "tags", None) or []
        c("Swarm" in tags, f"Swarm tag: {tags}")

    # ── Test 16: Bestaande routes intact (Phase 38+39) ──

    def test_16_existing_routes_intact(self) -> None:
        """Alle Phase 38+39 Observatory + core routes nog aanwezig."""
        print("\n[Test 16] Existing routes intact")
        try:
            from fastapi_server import app
        except ImportError:
            logger.debug("fastapi_server import niet beschikbaar")
            raise

        routes = {r.path for r in app.routes if hasattr(r, "methods")}

        expected = [
            "/api/v1/schild/stats",
            "/api/v1/tribunal/stats",
            "/api/v1/alerts/history",
            "/api/v1/blackbox/stats",
            "/api/v1/synapse/stats",
            "/api/v1/phantom/accuracy",
            "/api/v1/query",
            "/api/v1/health",
        ]
        for route in expected:
            c(route in routes, f"{route} intact")

    # ── Test 17: inspect.getsource() wiring ──

    def test_17_source_wiring(self) -> None:
        """Execute_goal bevat Arbitrator+Schild; TaskArbitrator broadcast via NeuralBus."""
        print("\n[Test 17] Source wiring (inspect)")
        try:
            from swarm_engine import SwarmEngine
            from danny_toolkit.brain.arbitrator import TaskArbitrator
        except ImportError:
            logger.debug("swarm_engine of arbitrator import niet beschikbaar")
            raise

        # SwarmEngine.execute_goal wiring
        src = inspect.getsource(SwarmEngine.execute_goal)
        c("get_arbitrator" in src, "get_arbitrator in execute_goal")
        c("get_hallucination_shield" in src, "get_hallucination_shield in execute_goal")
        c("arbitrator.decompose" in src, "arbitrator.decompose call")
        c("arbitrator.execute" in src, "arbitrator.execute call")
        c("arbitrator.synthesize" in src, "arbitrator.synthesize call")

        # TaskArbitrator NeuralBus sovereignty
        arb_src = inspect.getsource(TaskArbitrator)
        c("get_bus" in arb_src, "get_bus() in TaskArbitrator")
        c("publish" in arb_src, "publish() in TaskArbitrator")
        c("GOAL_COMPLETED" in arb_src, "GOAL_COMPLETED event in TaskArbitrator")

        # CorticalStack persistence
        c("cortical_stack" in arb_src.lower(), "CorticalStack in TaskArbitrator")
        c("log_event" in arb_src, "log_event call in TaskArbitrator")

        # Auction formule
        c("context_match" in arb_src, "context_match in Auction")
        c("current_load" in arb_src, "current_load in Auction")

    # ── Test 18: Version 6.7.0 + module integrity ──

    def test_18_version_and_integrity(self) -> None:
        """Version 6.7.0, module importeerbaar, stats compleet."""
        print("\n[Test 18] Version + integrity")
        try:
            import danny_toolkit.brain as brain
        except ImportError:
            logger.debug("brain import niet beschikbaar")
            raise

        v_parts = tuple(int(x) for x in brain.__version__.split("."))
        c(v_parts >= (6, 7, 0), f"version: {brain.__version__} >= 6.7.0")

        try:
            from danny_toolkit.brain.arbitrator import get_arbitrator
        except ImportError:
            logger.debug("arbitrator import niet beschikbaar")
            raise
        arb = get_arbitrator()
        stats = arb.get_stats()
        c(isinstance(stats, dict), "get_stats() returns dict")
        c("goals_processed" in stats, "goals_processed in stats")
        c("tasks_decomposed" in stats, "tasks_decomposed in stats")
        c("auctions_held" in stats, "auctions_held in stats")
        c("tasks_completed" in stats, "tasks_completed in stats")
        c("tasks_failed" in stats, "tasks_failed in stats")

        major, minor, patch = brain.__version__.split(".")
        c(int(major) >= 6, "major >= 6")
        c(int(minor) >= 7 or int(major) > 6, "minor >= 7")


if __name__ == "__main__":
    print("=" * 60)
    print("Phase 40: Swarm Sovereignty — TaskArbitrator")
    print("=" * 60)

    loader = unittest.TestLoader()
    loader.sortTestMethodsUsing = lambda a, b: (a > b) - (a < b)
    suite = loader.loadTestsFromTestCase(TestPhase40)

    runner = unittest.TextTestRunner(verbosity=0)
    result = runner.run(suite)

    print(f"\n{'=' * 60}")
    print(f"Checks: {CHECK}")
    print(f"Tests:  {result.testsRun} run, "
          f"{len(result.failures)} fail, "
          f"{len(result.errors)} error")
    print(f"{'=' * 60}")

    sys.exit(0 if result.wasSuccessful() else 1)
