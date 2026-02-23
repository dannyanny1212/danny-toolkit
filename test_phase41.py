#!/usr/bin/env python3
"""
Test Phase 41: Multi-Model Sync — Generaal Mode
=================================================
16 tests · ~48 checks (111-158 cumulatief)

Valideert:
  A. ModelCapability enum (5 waarden)
  B. ModelProfile + ModelResponse + ModelBid dataclasses
  C. ModelWorker base: is_available(), circuit breaker
  D. ModelWorker performance tracking: success_rate(), avg_latency_ms()
  E. GroqModelWorker + AnthropicModelWorker instantieerbaar
  F. ModelRegistry singleton identity
  G. ModelRegistry auto_discover
  H. model_auction formule: S = (cap_match × success_rate) / (cost + latency)
  I. model_auction: hoogste score wint, success_rate boost
  J. model_auction: no models / all excluded → None
  K. execute_with_models: mock worker + shield → task done
  L. execute_with_models: barrier rejection → retry (ontslagen)
  M. SwarmEngine.execute_goal use_models param
  N. FastAPI: ModelRegistryResponse + /api/v1/models/registry
  O. brain exports + version 6.8.0
  P. R_final betrouwbaarheidsformule

Gebruik:
    CUDA_VISIBLE_DEVICES=-1 DANNY_TEST_MODE=1 ANONYMIZED_TELEMETRY=False \
        python test_phase41.py
"""

import asyncio
import importlib
import inspect
import os
import sys
import threading
import time
import unittest

os.environ.setdefault("DANNY_TEST_MODE", "1")
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "-1")
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")

# Windows UTF-8
if os.name == "nt":
    sys.stdout.reconfigure(encoding="utf-8")

CHECK = 0


def c(ok: bool, label: str = ""):
    global CHECK
    CHECK += 1
    tag = f" ({label})" if label else ""
    status = "OK" if ok else "FAIL"
    print(f"  check {CHECK}: {status}{tag}")
    assert ok, f"Check {CHECK} failed{tag}"


class TestPhase41(unittest.TestCase):
    """Phase 41: Multi-Model Sync — Generaal Mode."""

    # ── Test 1: ModelCapability enum values (5) ──

    def test_01_model_capability_enum(self):
        """ModelCapability heeft 5 waarden: CODE, RESEARCH, ANALYSE, CREATIEF, VERIFICATIE."""
        print("\n[Test 1] ModelCapability enum")
        from danny_toolkit.brain.model_sync import ModelCapability

        c(ModelCapability.CODE == "code", "CODE == 'code'")
        c(ModelCapability.RESEARCH == "research", "RESEARCH == 'research'")
        c(ModelCapability.ANALYSE == "analyse", "ANALYSE == 'analyse'")
        c(ModelCapability.CREATIEF == "creatief", "CREATIEF == 'creatief'")
        c(ModelCapability.VERIFICATIE == "verificatie", "VERIFICATIE == 'verificatie'")

    # ── Test 2: Dataclasses ──

    def test_02_dataclasses(self):
        """ModelProfile + ModelResponse + ModelBid instantieerbaar met defaults."""
        print("\n[Test 2] Dataclasses")
        from danny_toolkit.brain.model_sync import (
            ModelProfile, ModelResponse, ModelBid, ModelCapability, ModelWorker,
        )

        profile = ModelProfile(
            provider="test",
            model_id="test-model",
            capabilities=[ModelCapability.CODE],
        )
        c(profile.provider == "test", "ModelProfile.provider")
        c(profile.cost_tier == 1, "ModelProfile.cost_tier default")

        response = ModelResponse(
            provider="test", model_id="test-model", content="Hallo",
        )
        c(response.content == "Hallo", "ModelResponse.content")
        c(response.passed_barrier is False, "ModelResponse.passed_barrier default")

        worker = ModelWorker(profile)
        bid = ModelBid(
            profile=profile, worker=worker,
            score=0.75, capability_match=1.0,
        )
        c(abs(bid.score - 0.75) < 1e-6, "ModelBid.score")

    # ── Test 3: ModelWorker base — is_available + circuit breaker ──

    def test_03_worker_circuit_breaker(self):
        """Circuit breaker: 3 failures → unavailable."""
        print("\n[Test 3] ModelWorker circuit breaker")
        from danny_toolkit.brain.model_sync import ModelProfile, ModelWorker

        profile = ModelProfile(provider="test", model_id="cb-test")
        worker = ModelWorker(profile)

        c(worker.is_available() is True, "initially available")

        worker._record_failure()
        worker._record_failure()
        c(worker.is_available() is True, "2 failures → still available")

        worker._record_failure()
        c(worker.is_available() is False, "3 failures → circuit open")
        c(worker._circuit_open is True, "_circuit_open flag set")

    # ── Test 4: Performance tracking ──

    def test_04_performance_tracking(self):
        """success_rate(), avg_latency_ms(), _record_barrier_rejection()."""
        print("\n[Test 4] Performance tracking")
        from danny_toolkit.brain.model_sync import ModelProfile, ModelWorker

        profile = ModelProfile(provider="test", model_id="perf-test")
        worker = ModelWorker(profile)

        # Default success rate bij 0 calls = 0.5
        c(abs(worker.success_rate() - 0.5) < 1e-6, "success_rate default 0.5")

        # Simuleer calls
        worker._perf["calls"] = 10
        worker._perf["successes"] = 8
        worker._perf["total_latency_ms"] = 5000.0
        c(abs(worker.success_rate() - 0.8) < 1e-6, "success_rate 8/10 = 0.8")
        c(abs(worker.avg_latency_ms() - 500.0) < 1e-6, "avg_latency 5000/10 = 500")

        worker._record_barrier_rejection()
        c(worker._perf["barrier_rejections"] == 1, "barrier_rejection counted")

    # ── Test 5: Provider workers instantieerbaar ──

    def test_05_provider_workers(self):
        """GroqModelWorker + AnthropicModelWorker instantieerbaar."""
        print("\n[Test 5] Provider workers")
        from danny_toolkit.brain.model_sync import (
            GroqModelWorker, AnthropicModelWorker,
        )

        groq_w = GroqModelWorker()
        c(groq_w.profile.provider == "groq", "GroqModelWorker.provider")

        anth_w = AnthropicModelWorker()
        c(anth_w.profile.provider == "anthropic", "AnthropicModelWorker.provider")

    # ── Test 6: ModelRegistry singleton ──

    def test_06_registry_singleton(self):
        """get_model_registry() retourneert dezelfde instantie."""
        print("\n[Test 6] ModelRegistry singleton")
        from danny_toolkit.brain.model_sync import get_model_registry

        a = get_model_registry()
        b = get_model_registry()
        c(a is b, "id(a) is id(b)")
        c(id(a) == id(b), "id(a) == id(b)")

    # ── Test 7: Auto-discover ──

    def test_07_auto_discover(self):
        """auto_discover registreert workers op basis van env vars."""
        print("\n[Test 7] Auto-discover")
        from danny_toolkit.brain.model_sync import ModelRegistry

        registry = ModelRegistry()
        registry.auto_discover()

        stats = registry.get_stats()
        c(isinstance(stats, dict), "get_stats() returns dict")
        c("total_workers" in stats, "total_workers in stats")
        # GROQ_API_KEY is altijd aanwezig in de test env
        c(stats["total_workers"] >= 0, f"total_workers >= 0: {stats['total_workers']}")

    # ── Test 8: model_auction formule ──

    def test_08_model_auction_formula(self):
        """S_model = (cap_match × success_rate) / (cost_tier + latency_class)."""
        print("\n[Test 8] model_auction formule")
        from danny_toolkit.brain.arbitrator import TaskArbitrator, SwarmTask
        from danny_toolkit.brain.model_sync import (
            ModelProfile, ModelWorker, ModelCapability,
            ModelRegistry, get_model_registry,
        )

        arb = TaskArbitrator()

        # Maak een verse registry met 2 bekende workers
        registry = ModelRegistry()

        profile_a = ModelProfile(
            provider="test_a", model_id="model-a",
            capabilities=[ModelCapability.CODE],
            cost_tier=1, latency_class=1,
        )
        worker_a = ModelWorker(profile_a)
        worker_a._perf["calls"] = 10
        worker_a._perf["successes"] = 8  # success_rate = 0.8
        registry.register(worker_a)

        profile_b = ModelProfile(
            provider="test_b", model_id="model-b",
            capabilities=[ModelCapability.ANALYSE],
            cost_tier=2, latency_class=2,
        )
        worker_b = ModelWorker(profile_b)
        worker_b._perf["calls"] = 10
        worker_b._perf["successes"] = 9  # success_rate = 0.9
        registry.register(worker_b)

        # Monkey-patch de registry
        import danny_toolkit.brain.model_sync as ms
        old_instance = ms._registry_instance
        ms._registry_instance = registry

        try:
            task = SwarmTask(task_id="ma1", beschrijving="code test", categorie="code")
            bid = arb.model_auction(task)

            c(bid is not None, "bid is not None")

            # Worker A: cap=CODE matches "code" → cap_match=1.0
            # S_a = (1.0 × 0.8) / (1 + 1) = 0.8 / 2 = 0.4
            # Worker B: cap=ANALYSE, no match "code" → cap_match=0.5
            # S_b = (0.5 × 0.9) / (2 + 2) = 0.45 / 4 = 0.1125
            expected_a = round((1.0 * 0.8) / (1 + 1), 4)
            expected_b = round((0.5 * 0.9) / (2 + 2), 4)

            c(bid.profile.provider == "test_a",
              f"winner: {bid.profile.provider} == test_a")
            c(abs(bid.score - expected_a) < 0.01,
              f"score: {bid.score} ≈ {expected_a}")
        finally:
            ms._registry_instance = old_instance

    # ── Test 9: Hoogste score wint, success_rate boost ──

    def test_09_auction_highest_wins(self):
        """Model met hogere success_rate stijgt in ranking."""
        print("\n[Test 9] model_auction: hoogste wint")
        from danny_toolkit.brain.arbitrator import TaskArbitrator, SwarmTask
        from danny_toolkit.brain.model_sync import (
            ModelProfile, ModelWorker, ModelCapability, ModelRegistry,
        )

        arb = TaskArbitrator()
        registry = ModelRegistry()

        # Beide matchen op "analyse" → cap_match=1.0, zelfde cost/latency
        p1 = ModelProfile(
            provider="slow", model_id="slow-model",
            capabilities=[ModelCapability.ANALYSE],
            cost_tier=1, latency_class=1,
        )
        w1 = ModelWorker(p1)
        w1._perf["calls"] = 20
        w1._perf["successes"] = 10  # 50%
        registry.register(w1)

        p2 = ModelProfile(
            provider="fast", model_id="fast-model",
            capabilities=[ModelCapability.ANALYSE],
            cost_tier=1, latency_class=1,
        )
        w2 = ModelWorker(p2)
        w2._perf["calls"] = 20
        w2._perf["successes"] = 19  # 95%
        registry.register(w2)

        import danny_toolkit.brain.model_sync as ms
        old = ms._registry_instance
        ms._registry_instance = registry

        try:
            task = SwarmTask(task_id="hw1", beschrijving="analyseer", categorie="analyse")
            bid = arb.model_auction(task)
            c(bid is not None, "bid is not None")
            c(bid.profile.provider == "fast",
              f"fast wint: {bid.profile.provider}")
        finally:
            ms._registry_instance = old

    # ── Test 10: No models / all excluded → None ──

    def test_10_auction_no_models(self):
        """Geen modellen of alle excluded → None."""
        print("\n[Test 10] model_auction: no models")
        from danny_toolkit.brain.arbitrator import TaskArbitrator, SwarmTask
        from danny_toolkit.brain.model_sync import ModelRegistry

        arb = TaskArbitrator()

        # Lege registry
        registry = ModelRegistry()
        import danny_toolkit.brain.model_sync as ms
        old = ms._registry_instance
        ms._registry_instance = registry

        try:
            task = SwarmTask(task_id="nm1", beschrijving="test", categorie="code")
            bid = arb.model_auction(task)
            c(bid is None, "lege registry → None")

            # Met excluded
            from danny_toolkit.brain.model_sync import (
                ModelProfile, ModelWorker, ModelCapability,
            )
            p = ModelProfile(
                provider="only", model_id="only-model",
                capabilities=[ModelCapability.CODE],
            )
            w = ModelWorker(p)
            registry.register(w)

            bid2 = arb.model_auction(task, exclude=["only-model"])
            c(bid2 is None, "all excluded → None")
        finally:
            ms._registry_instance = old

    # ── Test 11: execute_with_models — mock worker + shield → task done ──

    def test_11_execute_with_models_success(self):
        """Mock worker die content returnt → task status done, perf updated."""
        print("\n[Test 11] execute_with_models: success")
        from danny_toolkit.brain.arbitrator import (
            TaskArbitrator, GoalManifest, SwarmTask,
        )
        from danny_toolkit.brain.model_sync import (
            ModelProfile, ModelWorker, ModelCapability,
            ModelResponse, ModelRegistry,
        )

        arb = TaskArbitrator()

        class MockWorker(ModelWorker):
            async def generate(self, prompt, system=""):
                self._perf["calls"] += 1
                return ModelResponse(
                    provider="mock", model_id="mock-model",
                    content="Dit is een uitstekend antwoord op de vraag.",
                    tokens_used=50, latency_ms=100.0,
                )

        registry = ModelRegistry()
        p = ModelProfile(
            provider="mock", model_id="mock-model",
            capabilities=[ModelCapability.CODE, ModelCapability.ANALYSE],
            cost_tier=1, latency_class=1,
        )
        worker = MockWorker(p)
        registry.register(worker)

        import danny_toolkit.brain.model_sync as ms
        old = ms._registry_instance
        ms._registry_instance = registry

        try:
            manifest = GoalManifest(goal="Mock test", trace_id="mock123")
            manifest.taken = [
                SwarmTask(task_id="mt1", beschrijving="Analyseer iets", categorie="analyse"),
            ]
            manifest.status = "decomposed"

            result = asyncio.run(arb.execute_with_models(manifest))

            c(result.taken[0].status == "done", f"task status: {result.taken[0].status}")
            c(result.taken[0].resultaat is not None, "resultaat is not None")
            c(result.taken[0].resultaat.content != "", "resultaat content niet leeg")
            c(result.status in ("done", "partial"), f"manifest status: {result.status}")
        finally:
            ms._registry_instance = old

    # ── Test 12: execute_with_models — barrier rejection → retry ──

    def test_12_execute_with_models_retry(self):
        """Eerste model rejected door shield → retry met tweede model."""
        print("\n[Test 12] execute_with_models: barrier rejection + retry")
        from danny_toolkit.brain.arbitrator import (
            TaskArbitrator, GoalManifest, SwarmTask,
        )
        from danny_toolkit.brain.model_sync import (
            ModelProfile, ModelWorker, ModelCapability,
            ModelResponse, ModelRegistry,
        )

        arb = TaskArbitrator()
        call_log = []

        class BadWorker(ModelWorker):
            async def generate(self, prompt, system=""):
                self._perf["calls"] += 1
                call_log.append(f"bad:{self.profile.model_id}")
                return ModelResponse(
                    provider="bad", model_id=self.profile.model_id,
                    content="", tokens_used=0, latency_ms=50.0,
                )

        class GoodWorker(ModelWorker):
            async def generate(self, prompt, system=""):
                self._perf["calls"] += 1
                call_log.append(f"good:{self.profile.model_id}")
                return ModelResponse(
                    provider="good", model_id=self.profile.model_id,
                    content="Een goed en compleet antwoord.",
                    tokens_used=40, latency_ms=80.0,
                )

        registry = ModelRegistry()
        # Bad worker (hogere score door 0-calls → 0.5 default success_rate)
        p_bad = ModelProfile(
            provider="bad", model_id="bad-model",
            capabilities=[ModelCapability.CODE],
            cost_tier=1, latency_class=1,
        )
        bad_w = BadWorker(p_bad)
        bad_w._perf["calls"] = 10
        bad_w._perf["successes"] = 8  # 0.8 success
        registry.register(bad_w)

        p_good = ModelProfile(
            provider="good", model_id="good-model",
            capabilities=[ModelCapability.CODE],
            cost_tier=1, latency_class=1,
        )
        good_w = GoodWorker(p_good)
        good_w._perf["calls"] = 10
        good_w._perf["successes"] = 7  # 0.7 success (lager, kiest bad eerst)
        registry.register(good_w)

        import danny_toolkit.brain.model_sync as ms
        old = ms._registry_instance
        ms._registry_instance = registry

        try:
            manifest = GoalManifest(goal="Retry test", trace_id="retry1")
            manifest.taken = [
                SwarmTask(task_id="rt1", beschrijving="Code iets", categorie="code"),
            ]
            manifest.status = "decomposed"

            result = asyncio.run(arb.execute_with_models(manifest, retry_limit=2))

            # Bad model geeft lege content → retry naar good model
            c(len(call_log) >= 2, f"minstens 2 calls: {len(call_log)}")
            c(any("good:" in cl for cl in call_log), "good worker werd aangeroepen")
            c(result.taken[0].status == "done", f"uiteindelijk done: {result.taken[0].status}")
        finally:
            ms._registry_instance = old

    # ── Test 13: SwarmEngine.execute_goal use_models param ──

    def test_13_execute_goal_use_models(self):
        """SwarmEngine.execute_goal heeft use_models parameter."""
        print("\n[Test 13] SwarmEngine.execute_goal(use_models=)")
        from swarm_engine import SwarmEngine

        sig = inspect.signature(SwarmEngine.execute_goal)
        params = list(sig.parameters.keys())
        c("use_models" in params, f"use_models in params: {params}")
        c(sig.parameters["use_models"].default is False,
          "use_models default is False")

    # ── Test 14: FastAPI models + route ──

    def test_14_fastapi_models_and_route(self):
        """ModelRegistryResponse + GoalRequest.use_models + /api/v1/models/registry."""
        print("\n[Test 14] FastAPI models + route")
        from fastapi_server import (
            ModelRegistryResponse, GoalRequest, app,
        )

        # ModelRegistryResponse
        resp = ModelRegistryResponse(
            models=[{"provider": "test"}], total=1, available=1,
        )
        c(resp.total == 1, "ModelRegistryResponse.total")

        # GoalRequest has use_models
        gr = GoalRequest(goal="Test doel")
        c(gr.use_models is False, "GoalRequest.use_models default False")

        # Route exists
        routes = {}
        for r in app.routes:
            if hasattr(r, "methods"):
                routes[r.path] = r

        c("/api/v1/models/registry" in routes, "/api/v1/models/registry registered")

    # ── Test 15: brain exports + version 6.8.0 ──

    def test_15_exports_and_version(self):
        """ModelRegistry, get_model_registry in __all__ + version 6.8.0."""
        print("\n[Test 15] Exports + version")
        import danny_toolkit.brain as brain

        c("ModelRegistry" in brain.__all__, "ModelRegistry in __all__")
        c("get_model_registry" in brain.__all__, "get_model_registry in __all__")
        v = tuple(int(x) for x in brain.__version__.split("."))
        c(v >= (6, 8, 0), f"version: {brain.__version__} >= 6.8.0")

    # ── Test 16: R_final betrouwbaarheidsformule ──

    def test_16_betrouwbaarheid_formula(self):
        """R_final = 1 - (1 - P_ext) × (1 - P_shield)."""
        print("\n[Test 16] Betrouwbaarheidsformule")
        from danny_toolkit.brain.model_sync import betrouwbaarheid

        # P_ext=0.80, P_shield=0.95 → R = 1 - 0.20×0.05 = 0.99
        r1 = betrouwbaarheid(0.80, 0.95)
        c(abs(r1 - 0.99) < 1e-6, f"R(0.80,0.95) = {r1} ≈ 0.99")

        # P_ext=0.50, P_shield=0.50 → R = 1 - 0.50×0.50 = 0.75
        r2 = betrouwbaarheid(0.50, 0.50)
        c(abs(r2 - 0.75) < 1e-6, f"R(0.50,0.50) = {r2} ≈ 0.75")


if __name__ == "__main__":
    print("=" * 60)
    print("Phase 41: Multi-Model Sync — Generaal Mode")
    print("=" * 60)

    loader = unittest.TestLoader()
    loader.sortTestMethodsUsing = lambda a, b: (a > b) - (a < b)
    suite = loader.loadTestsFromTestCase(TestPhase41)

    runner = unittest.TextTestRunner(verbosity=0)
    result = runner.run(suite)

    print(f"\n{'=' * 60}")
    print(f"Checks: {CHECK}")
    print(f"Tests:  {result.testsRun} run, "
          f"{len(result.failures)} fail, "
          f"{len(result.errors)} error")
    print(f"{'=' * 60}")

    sys.exit(0 if result.wasSuccessful() else 1)
