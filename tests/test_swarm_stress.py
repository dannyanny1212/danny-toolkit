# tests/test_swarm_stress.py — Stress & concurrency tests voor SwarmEngine
import asyncio
import time

import pytest

from swarm_engine import SwarmEngine

pytestmark = pytest.mark.stress


class TestSwarmConcurrencyStress:
    """50 parallelle requests door de SwarmEngine."""

    def test_swarm_concurrency_stress(self):
        engine = SwarmEngine(brain=None)
        n = 50

        async def run_one(i):
            return await engine.run(f"bitcoin analyse {i}")

        async def run_all():
            tasks = [asyncio.create_task(run_one(i)) for i in range(n)]
            return await asyncio.gather(*tasks)

        t0 = time.time()
        results = asyncio.run(run_all())
        dt = time.time() - t0

        assert len(results) == n
        assert all(len(r) >= 1 for r in results)
        assert dt < 30, f"Stress test duurde te lang: {dt:.1f}s"


class TestSwarmNoBrainStress:
    """30 parallelle requests zonder brain."""

    def test_swarm_no_brain_stress(self):
        engine = SwarmEngine(brain=None)

        async def run_one(i):
            return await engine.run("bitcoin prijs en web search nieuws")

        async def run_all():
            tasks = [asyncio.create_task(run_one(i)) for i in range(30)]
            return await asyncio.gather(*tasks)

        results = asyncio.run(run_all())
        assert len(results) == 30
        assert all(len(r) >= 1 for r in results)


class TestSwarmRoutingStress:
    """Routing onder load — 100 route calls parallel."""

    def test_routing_stress(self):
        engine = SwarmEngine(brain=None)
        queries = [
            "bitcoin prijs", "debug mijn code", "gezondheid check",
            "web search nieuws", "verwijder bestanden", "plan mijn agenda",
            "brainstorm ideeën", "beveilig systeem", "hallo", "blorp florp",
        ]
        n = 100

        async def run_one(i):
            return await engine.route(queries[i % len(queries)])

        async def run_all():
            tasks = [asyncio.create_task(run_one(i)) for i in range(n)]
            return await asyncio.gather(*tasks)

        t0 = time.time()
        results = asyncio.run(run_all())
        dt = time.time() - t0

        assert len(results) == n
        assert all(isinstance(r, list) for r in results)
        assert all(len(r) >= 1 for r in results)
        assert dt < 30, f"Routing stress duurde te lang: {dt:.1f}s"


class TestSwarmMixedLoad:
    """Gemixte workload: fast-track + routed requests samen."""

    def test_mixed_load(self):
        engine = SwarmEngine(brain=None)

        async def fast_track(i):
            return await engine.run("hallo")

        async def heavy(i):
            return await engine.run(f"bitcoin analyse {i}")

        async def run_all():
            fast = [asyncio.create_task(fast_track(i)) for i in range(20)]
            heavy_tasks = [asyncio.create_task(heavy(i)) for i in range(20)]
            return await asyncio.gather(*fast, *heavy_tasks)

        results = asyncio.run(run_all())
        assert len(results) == 40
        assert all(len(r) >= 1 for r in results)
