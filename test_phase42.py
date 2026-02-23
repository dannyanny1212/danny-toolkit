#!/usr/bin/env python3
"""
Test Phase 42: Observatory Sync — Generaal Controlekamer
=========================================================
20 tests · 120+ checks

Valideert:
  A. Datamodellen (ModelObservatoryEntry, AuctionLogEntry, ObservatoryDashboard)
  B. Singleton identity + concurrency
  C. Exports + __all__ + version
  D. Dashboard data aggregatie (leeg + met mock workers)
  E. Model leaderboard + sorteer-opties
  F. Auction history recording + ordering
  G. Cost analysis + aanbevelingen
  H. Failure analysis + probleemmodellen
  I. Trend data accumulatie
  J. Stats accumulatie
  K. Arbitrator _record_to_observatory wiring (inspect.getsource)
  L. FastAPI Pydantic models
  M. FastAPI routes (6 observatory + 1 UI partial)
  N. Bestaande routes intact (Phase 38-41)
  O. Dashboard template bevat observatory card
  P. Observatory partial template structuur

Gebruik:
    CUDA_VISIBLE_DEVICES=-1 DANNY_TEST_MODE=1 ANONYMIZED_TELEMETRY=False \
        python test_phase42.py
"""

import importlib
import inspect
import json
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


class TestPhase42(unittest.TestCase):
    """Phase 42: Observatory Sync — Generaal Controlekamer."""

    # ── Test 1: Datamodellen instantieerbaar ──

    def test_01_datamodels(self):
        """ModelObservatoryEntry, AuctionLogEntry, ObservatoryDashboard velden + to_dict."""
        print("\n[Test 1] Datamodellen")
        from danny_toolkit.brain.observatory_sync import (
            ModelObservatoryEntry, AuctionLogEntry, ObservatoryDashboard,
        )

        # ModelObservatoryEntry
        entry = ModelObservatoryEntry(
            provider="groq",
            model_id="llama-4-scout",
            calls=100,
            successes=90,
            failures=5,
            barrier_rejections=5,
            total_tokens=50000,
            total_latency_ms=10000.0,
            avg_latency_ms=100.0,
            success_rate=0.9,
            cost_tier=1,
            latency_class=1,
        )
        c(entry.provider == "groq", "ModelObservatoryEntry.provider")
        c(entry.calls == 100, "ModelObservatoryEntry.calls")
        c(entry.success_rate == 0.9, "ModelObservatoryEntry.success_rate")
        c(entry.beschikbaar is True, "ModelObservatoryEntry.beschikbaar default")

        d = entry.to_dict()
        c(isinstance(d, dict), "ModelObservatoryEntry.to_dict()")
        c("provider" in d and "model_id" in d, "to_dict keys: provider, model_id")
        c("calls" in d and "success_rate" in d, "to_dict keys: calls, success_rate")
        c("barrier_rejections" in d, "to_dict keys: barrier_rejections")

        # AuctionLogEntry
        auction = AuctionLogEntry(
            timestamp=time.time(),
            task_id="t1",
            task_categorie="code",
            winnaar_provider="groq",
            winnaar_model_id="llama-4-scout",
            winnaar_score=0.85,
            deelnemers=3,
            barrier_pass=True,
        )
        c(auction.task_id == "t1", "AuctionLogEntry.task_id")
        c(auction.deelnemers == 3, "AuctionLogEntry.deelnemers")
        ad = auction.to_dict()
        c(isinstance(ad, dict), "AuctionLogEntry.to_dict()")
        c("winnaar_provider" in ad, "auction to_dict: winnaar_provider")

        # ObservatoryDashboard
        dash = ObservatoryDashboard(
            totaal_modellen=3,
            beschikbare_modellen=2,
            totaal_calls=50,
        )
        c(dash.totaal_modellen == 3, "ObservatoryDashboard.totaal_modellen")
        c(dash.beschikbare_modellen == 2, "ObservatoryDashboard.beschikbare_modellen")
        dd = dash.to_dict()
        c(isinstance(dd, dict), "ObservatoryDashboard.to_dict()")
        c("modellen" in dd and "recente_veilingen" in dd, "dashboard to_dict lists")

    # ── Test 2: Singleton identity ──

    def test_02_singleton_identity(self):
        """get_observatory_sync() retourneert dezelfde instantie."""
        print("\n[Test 2] Singleton identity")
        from danny_toolkit.brain.observatory_sync import get_observatory_sync

        a = get_observatory_sync()
        b = get_observatory_sync()
        c(a is b, "id(a) is id(b)")
        c(id(a) == id(b), "id(a) == id(b)")

    # ── Test 3: Singleton thread safety (50 threads) ──

    def test_03_singleton_concurrency(self):
        """50 threads → exact 1 uniek id."""
        print("\n[Test 3] Singleton concurrency (50 threads)")

        import danny_toolkit.brain.observatory_sync as obs_mod
        obs_mod._observatory_instance = None

        ids = []
        barrier = threading.Barrier(50)

        def grab():
            barrier.wait()
            from danny_toolkit.brain.observatory_sync import get_observatory_sync
            ids.append(id(get_observatory_sync()))

        threads = [threading.Thread(target=grab) for _ in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        unique = set(ids)
        c(len(unique) == 1, f"unique ids: {len(unique)} == 1")
        c(len(ids) == 50, f"total grabs: {len(ids)} == 50")

    # ── Test 4: Exports in brain __init__ + __all__ ──

    def test_04_exports(self):
        """ObservatorySync, get_observatory_sync in exports + __all__."""
        print("\n[Test 4] Exports")
        import danny_toolkit.brain as brain

        c(hasattr(brain, "ObservatorySync"), "ObservatorySync in brain")
        c(hasattr(brain, "get_observatory_sync"), "get_observatory_sync in brain")
        c("ObservatorySync" in brain.__all__, "ObservatorySync in __all__")
        c("get_observatory_sync" in brain.__all__, "get_observatory_sync in __all__")

    # ── Test 5: Version 6.10.0 ──

    def test_05_version(self):
        """Version >= 6.10.0."""
        print("\n[Test 5] Version")
        import danny_toolkit.brain as brain

        v_parts = tuple(int(x) for x in brain.__version__.split("."))
        c(v_parts >= (6, 10, 0), f"version: {brain.__version__} >= 6.10.0")

        major, minor, patch = brain.__version__.split(".")
        c(int(major) >= 6, "major >= 6")
        c(int(minor) >= 10 or int(major) > 6, "minor >= 10")

    # ── Test 6: Dashboard data (leeg) ──

    def test_06_dashboard_empty(self):
        """Dashboard data zonder ModelRegistry geregistreerde workers."""
        print("\n[Test 6] Dashboard data (leeg)")
        from danny_toolkit.brain.observatory_sync import ObservatorySync

        obs = ObservatorySync()
        dash = obs.get_dashboard_data()

        c(dash.totaal_modellen >= 0, "totaal_modellen >= 0")
        c(dash.totaal_calls >= 0, "totaal_calls >= 0")
        c(isinstance(dash.modellen, list), "modellen is list")
        c(isinstance(dash.recente_veilingen, list), "recente_veilingen is list")
        c(dash.timestamp != "", "timestamp niet leeg")
        c(dash.gemiddelde_latency_ms >= 0, "gem_latency >= 0")

    # ── Test 7: Dashboard with mock data ──

    def test_07_dashboard_with_models(self):
        """Dashboard aggregeert correct met mock ModelRegistry workers."""
        print("\n[Test 7] Dashboard met mock data")
        from danny_toolkit.brain.observatory_sync import ObservatorySync
        from danny_toolkit.brain.model_sync import (
            ModelWorker, ModelProfile, ModelCapability, ModelRegistry,
            get_model_registry,
        )

        # Setup mock registry
        registry = get_model_registry()
        profile_a = ModelProfile(
            provider="groq", model_id="test-llama",
            capabilities=[ModelCapability.CODE],
            cost_tier=1, latency_class=1,
        )
        worker_a = ModelWorker(profile_a)
        worker_a._perf["calls"] = 50
        worker_a._perf["successes"] = 45
        worker_a._perf["failures"] = 5
        worker_a._perf["total_tokens"] = 25000
        worker_a._perf["total_latency_ms"] = 5000.0

        profile_b = ModelProfile(
            provider="anthropic", model_id="test-claude",
            capabilities=[ModelCapability.CREATIEF],
            cost_tier=3, latency_class=2,
        )
        worker_b = ModelWorker(profile_b)
        worker_b._perf["calls"] = 30
        worker_b._perf["successes"] = 28
        worker_b._perf["failures"] = 2
        worker_b._perf["total_tokens"] = 60000
        worker_b._perf["total_latency_ms"] = 9000.0

        registry.register(worker_a)
        registry.register(worker_b)

        obs = ObservatorySync()
        dash = obs.get_dashboard_data()

        c(dash.totaal_modellen >= 2, f"totaal >= 2: {dash.totaal_modellen}")
        c(dash.totaal_calls >= 80, f"calls >= 80: {dash.totaal_calls}")
        c(dash.totaal_tokens >= 85000, f"tokens >= 85000: {dash.totaal_tokens}")
        c(dash.totaal_successen >= 73, f"successes >= 73: {dash.totaal_successen}")
        c(dash.gemiddelde_latency_ms > 0, f"avg latency > 0: {dash.gemiddelde_latency_ms}")
        c(len(dash.modellen) >= 2, f"modellen count >= 2: {len(dash.modellen)}")

        # to_dict round-trip
        dd = dash.to_dict()
        c(isinstance(dd, dict), "dashboard to_dict()")
        c(dd["totaal_calls"] == dash.totaal_calls, "to_dict calls match")

    # ── Test 8: Leaderboard sorteer-opties ──

    def test_08_leaderboard(self):
        """Leaderboard sorteert correct op verschillende criteria."""
        print("\n[Test 8] Leaderboard")
        from danny_toolkit.brain.observatory_sync import ObservatorySync

        obs = ObservatorySync()

        # success_rate (default)
        lb = obs.get_model_leaderboard(sort_by="success_rate")
        c(isinstance(lb, list), "leaderboard is list")
        if len(lb) >= 2:
            c(lb[0].get("rank", 0) == 1, "rank 1 first")
            c(lb[0]["success_rate"] >= lb[1]["success_rate"],
              "sorted by success_rate desc")

        # calls
        lb_calls = obs.get_model_leaderboard(sort_by="calls")
        if len(lb_calls) >= 2:
            c(lb_calls[0]["calls"] >= lb_calls[1]["calls"],
              "sorted by calls desc")

        # avg_latency_ms (ascending = beter)
        lb_lat = obs.get_model_leaderboard(sort_by="avg_latency_ms")
        if len(lb_lat) >= 2:
            c(lb_lat[0]["avg_latency_ms"] <= lb_lat[1]["avg_latency_ms"],
              "sorted by avg_latency asc")

        # failures (ascending = beter)
        lb_fail = obs.get_model_leaderboard(sort_by="failures")
        if len(lb_fail) >= 2:
            c(lb_fail[0]["failures"] <= lb_fail[1]["failures"],
              "sorted by failures asc")

    # ── Test 9: Auction history recording ──

    def test_09_auction_history(self):
        """record_auction() + get_auction_history() FIFO/LIFO."""
        print("\n[Test 9] Auction history")
        from danny_toolkit.brain.observatory_sync import ObservatorySync

        obs = ObservatorySync()

        obs.record_auction(
            task_id="t1", task_categorie="code",
            winnaar_provider="groq", winnaar_model_id="model-a",
            winnaar_score=0.9, deelnemers=3, barrier_pass=True,
        )
        obs.record_auction(
            task_id="t2", task_categorie="research",
            winnaar_provider="anthropic", winnaar_model_id="model-b",
            winnaar_score=0.7, deelnemers=2, barrier_pass=False,
        )
        obs.record_auction(
            task_id="t3", task_categorie="analyse",
            winnaar_provider="groq", winnaar_model_id="model-c",
            winnaar_score=0.85, deelnemers=4,
        )

        history = obs.get_auction_history(count=10)
        c(len(history) == 3, f"3 auctions: {len(history)}")
        c(history[0]["task_id"] == "t3", "nieuwste eerst: t3")
        c(history[1]["task_id"] == "t2", "dan: t2")
        c(history[2]["task_id"] == "t1", "dan: t1")
        c(history[0]["winnaar_score"] == 0.85, "score bewaard")
        c(history[1]["barrier_pass"] is False, "barrier_pass=False bewaard")
        c(history[2]["barrier_pass"] is True, "barrier_pass=True bewaard")

        # Count limiet
        limited = obs.get_auction_history(count=2)
        c(len(limited) == 2, f"count=2 limiet: {len(limited)}")

    # ── Test 10: Auction deque maxlen ──

    def test_10_auction_maxlen(self):
        """Auction log deque maxlen = 200."""
        print("\n[Test 10] Auction deque maxlen")
        from danny_toolkit.brain.observatory_sync import ObservatorySync

        obs = ObservatorySync()
        c(obs._auction_log.maxlen == 200, f"maxlen: {obs._auction_log.maxlen}")

    # ── Test 11: Cost analysis ──

    def test_11_cost_analysis(self):
        """Cost analysis per provider + aanbevelingen."""
        print("\n[Test 11] Cost analysis")
        from danny_toolkit.brain.observatory_sync import ObservatorySync

        obs = ObservatorySync()
        costs = obs.get_cost_analysis()

        c(isinstance(costs, dict), "costs is dict")
        c("per_provider" in costs, "per_provider key")
        c("per_model" in costs, "per_model key")
        c("aanbevelingen" in costs, "aanbevelingen key")
        c(isinstance(costs["per_model"], list), "per_model is list")
        c(isinstance(costs["aanbevelingen"], list), "aanbevelingen is list")

    # ── Test 12: Failure analysis ──

    def test_12_failure_analysis(self):
        """Failure analysis met probleemmodellen + circuit_open_count."""
        print("\n[Test 12] Failure analysis")
        from danny_toolkit.brain.observatory_sync import ObservatorySync

        obs = ObservatorySync()
        failures = obs.get_failure_analysis()

        c(isinstance(failures, dict), "failures is dict")
        c("modellen" in failures, "modellen key")
        c("probleemmodellen" in failures, "probleemmodellen key")
        c("totaal_failures" in failures, "totaal_failures key")
        c("totaal_barrier_rejections" in failures, "totaal_barrier_rejections key")
        c("circuit_open_count" in failures, "circuit_open_count key")

    # ── Test 13: Trend data ──

    def test_13_trend_data(self):
        """Trend data accumuleert bij dashboard queries."""
        print("\n[Test 13] Trend data")
        from danny_toolkit.brain.observatory_sync import ObservatorySync

        obs = ObservatorySync()

        # Neem twee snapshots
        obs.get_dashboard_data()
        time.sleep(0.01)
        obs.get_dashboard_data()

        trends = obs.get_trend_data()
        c(isinstance(trends, list), "trends is list")
        c(len(trends) >= 2, f"2+ trend punten: {len(trends)}")

        if trends:
            c("timestamp" in trends[0], "trend: timestamp key")
            c("totaal_calls" in trends[0], "trend: totaal_calls key")
            c("gem_latency_ms" in trends[0], "trend: gem_latency_ms key")

    # ── Test 14: Stats accumulatie ──

    def test_14_stats(self):
        """Stats incrementen na dashboard, leaderboard, en auction operaties."""
        print("\n[Test 14] Stats accumulatie")
        from danny_toolkit.brain.observatory_sync import ObservatorySync

        obs = ObservatorySync()

        obs.get_dashboard_data()
        obs.get_model_leaderboard()
        obs.record_auction(
            task_id="sx", task_categorie="x",
            winnaar_provider="p", winnaar_model_id="m",
            winnaar_score=0.5, deelnemers=1,
        )

        stats = obs.get_stats()
        c(isinstance(stats, dict), "stats is dict")
        c(stats["snapshots_taken"] >= 1, f"snapshots: {stats['snapshots_taken']}")
        c(stats["leaderboard_queries"] >= 1, f"leaderboard: {stats['leaderboard_queries']}")
        c(stats["auction_logs_recorded"] >= 1, f"auction_logs: {stats['auction_logs_recorded']}")
        c("auction_log_size" in stats, "auction_log_size key")
        c("snapshot_history_size" in stats, "snapshot_history_size key")

    # ── Test 15: Arbitrator observatory wiring (inspect) ──

    def test_15_arbitrator_wiring(self):
        """TaskArbitrator.model_auction() roept _record_to_observatory aan;
        _record_to_observatory importeert get_observatory_sync."""
        print("\n[Test 15] Arbitrator observatory wiring")
        from danny_toolkit.brain.arbitrator import TaskArbitrator

        src = inspect.getsource(TaskArbitrator)

        c("_record_to_observatory" in src, "_record_to_observatory in TaskArbitrator")
        c("get_observatory_sync" in src, "get_observatory_sync in TaskArbitrator")
        c("record_auction" in src, "record_auction call in TaskArbitrator")

        # model_auction roept _record_to_observatory aan
        auction_src = inspect.getsource(TaskArbitrator.model_auction)
        c("_record_to_observatory" in auction_src,
          "_record_to_observatory in model_auction")

    # ── Test 16: FastAPI Pydantic models ──

    def test_16_fastapi_models(self):
        """Pydantic response models bestaan en zijn instantieerbaar."""
        print("\n[Test 16] FastAPI Pydantic models")
        from fastapi_server import (
            ObservatoryDashboardResponse,
            ModelObservatoryEntryResponse,
            AuctionLogEntryResponse,
            CostAnalysisResponse,
            FailureAnalysisResponse,
            ObservatoryStatsResponse,
        )

        dash = ObservatoryDashboardResponse()
        c(dash.totaal_modellen == 0, "DashboardResponse defaults")
        c(isinstance(dash.modellen, list), "DashboardResponse.modellen is list")

        entry = ModelObservatoryEntryResponse(
            provider="groq", model_id="test", rank=1,
        )
        c(entry.provider == "groq", "EntryResponse.provider")
        c(entry.rank == 1, "EntryResponse.rank")

        auction = AuctionLogEntryResponse(task_id="t1")
        c(auction.task_id == "t1", "AuctionLogResponse.task_id")

        cost = CostAnalysisResponse()
        c(isinstance(cost.aanbevelingen, list), "CostResponse.aanbevelingen is list")

        fail = FailureAnalysisResponse()
        c(fail.totaal_failures == 0, "FailureResponse defaults")

        stats = ObservatoryStatsResponse()
        c(stats.snapshots_taken == 0, "StatsResponse defaults")

    # ── Test 17: FastAPI observatory routes (6 API + 1 UI partial) ──

    def test_17_fastapi_routes(self):
        """6 Observatory API routes + 1 UI partial geregistreerd."""
        print("\n[Test 17] FastAPI routes")
        from fastapi_server import app

        routes = {}
        for r in app.routes:
            if hasattr(r, "methods"):
                routes[r.path] = r

        expected_api = [
            "/api/v1/observatory/dashboard",
            "/api/v1/observatory/leaderboard",
            "/api/v1/observatory/auctions",
            "/api/v1/observatory/costs",
            "/api/v1/observatory/failures",
            "/api/v1/observatory/stats",
        ]
        for route in expected_api:
            c(route in routes, f"{route} geregistreerd")
            c("GET" in routes[route].methods, f"GET method op {route}")

        # Observatory tag
        for route in expected_api:
            tags = getattr(routes[route], "tags", []) or []
            c("Observatory" in tags, f"Observatory tag op {route}")

        # UI partial
        c("/ui/partials/observatory" in routes, "/ui/partials/observatory geregistreerd")

    # ── Test 18: Bestaande routes intact (Phase 38-41) ──

    def test_18_existing_routes_intact(self):
        """Alle eerdere Observatory + core routes nog aanwezig."""
        print("\n[Test 18] Existing routes intact")
        from fastapi_server import app

        routes = {r.path for r in app.routes if hasattr(r, "methods")}

        expected = [
            # Core
            "/api/v1/query",
            "/api/v1/health",
            "/api/v1/agents",
            # Phase 38
            "/api/v1/config/audit",
            "/api/v1/bus/stats",
            # Phase 39
            "/api/v1/schild/stats",
            "/api/v1/tribunal/stats",
            "/api/v1/blackbox/stats",
            "/api/v1/synapse/stats",
            "/api/v1/phantom/accuracy",
            "/api/v1/alerts/history",
            # Phase 40
            "/api/v1/swarm/goal",
            # Phase 41
            "/api/v1/models/registry",
            # Introspection
            "/api/v1/system/introspection",
            "/api/v1/system/wirings",
        ]
        for route in expected:
            c(route in routes, f"{route} intact")

    # ── Test 19: Dashboard template bevat observatory card ──

    def test_19_dashboard_template(self):
        """dashboard.html bevat de Generaal Controlekamer card + HTMX attributes."""
        print("\n[Test 19] Dashboard template")
        from pathlib import Path
        tmpl_path = (
            Path(__file__).parent
            / "danny_toolkit" / "web" / "templates" / "dashboard.html"
        )

        c(tmpl_path.exists(), "dashboard.html bestaat")
        content = tmpl_path.read_text(encoding="utf-8")

        c("Generaal Controlekamer" in content, "Generaal Controlekamer titel in template")
        c("/ui/partials/observatory" in content, "hx-get observatory URL in template")
        c("hx-trigger" in content, "hx-trigger aanwezig")
        c("every 10s" in content, "polling interval in template")

    # ── Test 20: Observatory partial template structuur ──

    def test_20_observatory_partial(self):
        """Observatory partial bevat model tabel + summary metrics."""
        print("\n[Test 20] Observatory partial template")
        from pathlib import Path
        tmpl_path = (
            Path(__file__).parent
            / "danny_toolkit" / "web" / "templates" / "partials" / "observatory.html"
        )

        c(tmpl_path.exists(), "observatory.html bestaat")
        content = tmpl_path.read_text(encoding="utf-8")

        c("provider" in content.lower(), "provider kolom in template")
        c("model_id" in content, "model_id kolom in template")
        c("success_rate" in content, "success_rate in template")
        c("circuit_open" in content, "circuit_open status in template")
        c("Totaal Calls" in content, "Totaal Calls summary metric")
        c("Tokens" in content, "Tokens summary metric")
        c("Gem. Latency" in content, "Gem. Latency summary metric")
        c("Success Rate" in content, "Success Rate summary metric")
        c("Goals:" in content or "goals_processed" in content, "Goals in template")
        c("Veilingen" in content or "model_auctions_held" in content,
          "Veilingen in template")


if __name__ == "__main__":
    print("=" * 60)
    print("Phase 42: Observatory Sync — Generaal Controlekamer")
    print("=" * 60)

    loader = unittest.TestLoader()
    loader.sortTestMethodsUsing = lambda a, b: (a > b) - (a < b)
    suite = loader.loadTestsFromTestCase(TestPhase42)

    runner = unittest.TextTestRunner(verbosity=0)
    result = runner.run(suite)

    print(f"\n{'=' * 60}")
    print(f"Checks: {CHECK}")
    print(f"Tests:  {result.testsRun} run, "
          f"{len(result.failures)} fail, "
          f"{len(result.errors)} error")
    print(f"{'=' * 60}")

    sys.exit(0 if result.wasSuccessful() else 1)
