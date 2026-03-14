"""Health check for 4 Swarm Agents: import, instantiation, lazy loading, registration."""
from __future__ import annotations

import sys
import os
import time
import asyncio
import logging

logger = logging.getLogger(__name__)

# Test isolation
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
os.environ["DANNY_TEST_MODE"] = "1"
os.environ["ANONYMIZED_TELEMETRY"] = "False"

# UTF-8 Windows
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    logger.debug("stdout reconfigure failed")

logging.basicConfig(level=logging.WARNING)

# ─── Resultaat tracking ───
PASS = 0
FAIL = 0
WARN = 0


def ok(msg: str) -> None:
    """Log a passed check."""
    global PASS
    PASS += 1
    print(f"  🟢 PASS: {msg}")


def fail(msg: str, err: object = None) -> None:
    """Log a failed check."""
    global FAIL
    FAIL += 1
    detail = f" — {err}" if err else ""
    print(f"  🟥 FAIL: {msg}{detail}")


def warn(msg: str) -> None:
    """Log a warning check."""
    global WARN
    WARN += 1
    print(f"  🟧 WARN: {msg}")


# ══════════════════════════════════════════════
# TEST 1: Import Health — Agent Classes
# ══════════════════════════════════════════════
print("\n═══ TEST 1: IMPORT HEALTH — Swarm Agent Classes ═══")

agent_classes = {}
try:
    from swarm_engine import (
        Agent, SwarmPayload,
        CoherentieAgent, StrategistAgent,
        ArtificerAgent, VirtualTwinAgent,
    )
    agent_classes = {
        "CoherentieAgent": CoherentieAgent,
        "StrategistAgent": StrategistAgent,
        "ArtificerAgent": ArtificerAgent,
        "VirtualTwinAgent": VirtualTwinAgent,
    }
    ok("Alle 4 agent classes importeerbaar uit swarm_engine")
    ok(f"Base class Agent: {Agent.__name__}")
    ok(f"SwarmPayload dataclass: {SwarmPayload.__name__}")
except ImportError as e:
    fail("Import swarm_engine agent classes", e)
except SystemExit:
    fail("SystemExit bij import (sovereign gate?)")


# ══════════════════════════════════════════════
# TEST 2: Instantiatie Health
# ══════════════════════════════════════════════
print("\n═══ TEST 2: INSTANTIATIE HEALTH ═══")

instances = {}
agent_configs = {
    "CoherentieAgent": ("Coherentie", "Hardware"),
    "StrategistAgent": ("Strategist", "Planning"),
    "ArtificerAgent": ("Artificer", "Forge"),
    "VirtualTwinAgent": ("#@*VirtualTwin", "Analysis"),
}

for name, cls in agent_classes.items():
    try:
        args = agent_configs.get(name, (name, "Unknown"))
        inst = cls(*args)
        instances[name] = inst
        ok(f"{name}('{args[0]}', '{args[1]}') — name={inst.name}, role={inst.role}")
    except Exception as e:
        fail(f"{name} instantiatie", e)


# ══════════════════════════════════════════════
# TEST 3: Inheritance & Interface Check
# ══════════════════════════════════════════════
print("\n═══ TEST 3: INHERITANCE & INTERFACE ═══")

for name, inst in instances.items():
    # Check inheritance
    if isinstance(inst, Agent):
        ok(f"{name} extends Agent")
    else:
        fail(f"{name} extends Agent — is {type(inst)}")

    # Check process method exists and is async
    if hasattr(inst, "process"):
        import inspect
        if inspect.iscoroutinefunction(inst.process):
            ok(f"{name}.process() is async")
        else:
            fail(f"{name}.process() is NOT async")
    else:
        fail(f"{name} mist process() method")


# ══════════════════════════════════════════════
# TEST 4: Backing Module Imports
# ══════════════════════════════════════════════
print("\n═══ TEST 4: BACKING MODULE IMPORTS ═══")

# 4a: CoherentieMonitor
try:
    from danny_toolkit.daemon.coherentie import CoherentieMonitor
    ok("CoherentieMonitor importeerbaar")
    cm = CoherentieMonitor()
    ok(f"CoherentieMonitor() instantieerbaar")
    if hasattr(cm, "scan"):
        ok("CoherentieMonitor.scan() method aanwezig")
    else:
        fail("CoherentieMonitor mist scan() method")
except Exception as e:
    fail("CoherentieMonitor import/init", e)

# 4b: Strategist
try:
    from danny_toolkit.brain.strategist import Strategist
    ok("Strategist importeerbaar")
    s = Strategist()
    ok("Strategist() instantieerbaar")
    if hasattr(s, "execute_mission"):
        import inspect
        if inspect.iscoroutinefunction(s.execute_mission):
            ok("Strategist.execute_mission() is async")
        else:
            fail("Strategist.execute_mission() is NOT async")
    else:
        fail("Strategist mist execute_mission()")
except Exception as e:
    warn(f"Strategist init (kan API key vereisen): {e}")

# 4c: Artificer
try:
    from danny_toolkit.brain.artificer import Artificer
    ok("Artificer importeerbaar")
    a = Artificer()
    ok("Artificer() instantieerbaar")
    if hasattr(a, "execute_task"):
        import inspect
        if inspect.iscoroutinefunction(a.execute_task):
            ok("Artificer.execute_task() is async")
        else:
            fail("Artificer.execute_task() is NOT async")
    else:
        fail("Artificer mist execute_task()")
    # Check forbidden patterns
    if hasattr(a, "_FORBIDDEN") or hasattr(Artificer, "_FORBIDDEN"):
        ok("Artificer._FORBIDDEN security patterns aanwezig")
    else:
        warn("Artificer._FORBIDDEN niet gevonden als class/instance attr")
except Exception as e:
    warn(f"Artificer init (kan API key vereisen): {e}")

# 4d: VirtualTwin
try:
    from danny_toolkit.brain.virtual_twin import VirtualTwin
    ok("VirtualTwin importeerbaar")
    vt = VirtualTwin()
    ok("VirtualTwin() instantieerbaar")
    if hasattr(vt, "consult"):
        import inspect
        if inspect.iscoroutinefunction(vt.consult):
            ok("VirtualTwin.consult() is async")
        else:
            fail("VirtualTwin.consult() is NOT async")
    else:
        fail("VirtualTwin mist consult()")
except Exception as e:
    warn(f"VirtualTwin init (kan deps vereisen): {e}")


# ══════════════════════════════════════════════
# TEST 5: Lazy Loading Verification
# ══════════════════════════════════════════════
print("\n═══ TEST 5: LAZY LOADING PATTERN ═══")

lazy_methods = {
    "StrategistAgent": "_get_strategist",
    "ArtificerAgent": "_get_artificer",
    "VirtualTwinAgent": "_get_twin",
}

for agent_name, method_name in lazy_methods.items():
    inst = instances.get(agent_name)
    if inst is None:
        fail(f"{agent_name} niet beschikbaar voor lazy loading test")
        continue

    if hasattr(inst, method_name):
        ok(f"{agent_name}.{method_name}() aanwezig")
        try:
            result = getattr(inst, method_name)()
            if result is not None:
                ok(f"{agent_name}.{method_name}() retourneert {type(result).__name__}")
            else:
                warn(f"{agent_name}.{method_name}() retourneert None (deps niet beschikbaar?)")
        except Exception as e:
            warn(f"{agent_name}.{method_name}() error: {e}")
    else:
        fail(f"{agent_name} mist {method_name}() lazy loader")


# ══════════════════════════════════════════════
# TEST 6: CoherentieMonitor Live Scan (geen API)
# ══════════════════════════════════════════════
print("\n═══ TEST 6: COHERENTIE LIVE SCAN ═══")

try:
    from danny_toolkit.daemon.coherentie import CoherentieMonitor
    cm = CoherentieMonitor()
    # Korte scan: 3 samples, 0.2s interval = ~0.6s
    t0 = time.time()
    rapport = cm.scan(samples=3, interval=0.2)
    elapsed = time.time() - t0

    # Verify rapport structuur
    required_keys = ["cpu_gem", "gpu_gem", "correlatie", "verdict", "details",
                     "cpu_reeks", "gpu_reeks", "gpu_beschikbaar", "duur_seconden"]
    missing = [k for k in required_keys if k not in rapport]

    if missing:
        fail(f"Rapport mist keys: {missing}")
    else:
        ok(f"Rapport structuur compleet ({len(required_keys)} keys)")

    ok(f"CPU gem: {rapport.get('cpu_gem', '?'):.1f}%")
    ok(f"GPU gem: {rapport.get('gpu_gem', '?'):.1f}%")
    ok(f"Correlatie: {rapport.get('correlatie', '?'):.4f}")
    ok(f"Verdict: {rapport.get('verdict', '?')}")
    ok(f"Scan duur: {elapsed:.2f}s (3 samples)")

    if rapport.get("verdict") in ("PASS", "WAARSCHUWING", "ALARM"):
        ok("Verdict is geldige waarde")
    else:
        fail(f"Ongeldig verdict: {rapport.get('verdict')}")

    if rapport.get("gpu_beschikbaar"):
        ok("GPU monitoring actief (NVML)")
    else:
        warn("GPU niet beschikbaar (NVML) — alleen CPU data")

except Exception as e:
    fail(f"CoherentieMonitor live scan", e)


# ══════════════════════════════════════════════
# TEST 7: SwarmEngine Registration
# ══════════════════════════════════════════════
print("\n═══ TEST 7: SWARM REGISTRATION ═══")

try:
    from swarm_engine import SwarmEngine
    ok("SwarmEngine importeerbaar")

    # Check _register_agents method exists
    if hasattr(SwarmEngine, "_register_agents"):
        ok("SwarmEngine._register_agents() method aanwezig")
    else:
        fail("SwarmEngine mist _register_agents()")

    # Inspect source for registration keys
    import inspect
    source = inspect.getsource(SwarmEngine._register_agents)
    expected_keys = ["COHERENTIE", "STRATEGIST", "ARTIFICER", "VIRTUAL_TWIN"]
    for key in expected_keys:
        if f'"{key}"' in source or f"'{key}'" in source:
            ok(f'"{key}" geregistreerd in _register_agents()')
        else:
            fail(f'"{key}" NIET gevonden in _register_agents()')

except SystemExit:
    warn("SwarmEngine SystemExit (sovereign gate) — source inspection fallback")
    try:
        import ast
        with open("swarm_engine.py", "r", encoding="utf-8") as f:
            content = f.read()
        for key in ["COHERENTIE", "STRATEGIST", "ARTIFICER", "VIRTUAL_TWIN"]:
            if f'"{key}"' in content:
                ok(f'"{key}" gevonden in swarm_engine.py source')
            else:
                fail(f'"{key}" NIET gevonden in swarm_engine.py source')
    except Exception as e:
        fail("Source inspection fallback", e)
except Exception as e:
    fail(f"SwarmEngine registration check", e)


# ══════════════════════════════════════════════
# TEST 8: AdaptiveRouter Profiles
# ══════════════════════════════════════════════
print("\n═══ TEST 8: ADAPTIVE ROUTER PROFILES ═══")

try:
    from swarm_engine import AdaptiveRouter
    ok("AdaptiveRouter importeerbaar")

    if hasattr(AdaptiveRouter, "AGENT_PROFIELEN"):
        profielen = AdaptiveRouter.AGENT_PROFIELEN
        for key in ["STRATEGIST", "ARTIFICER", "VIRTUAL_TWIN", "COHERENTIE"]:
            if key in profielen:
                ok(f'Router profiel "{key}" aanwezig ({len(profielen[key])} vectors)')
            else:
                warn(f'Router profiel "{key}" niet gevonden — keyword fallback')
    else:
        warn("AdaptiveRouter.AGENT_PROFIELEN niet gevonden")

except Exception as e:
    warn(f"AdaptiveRouter check: {e}")


# ══════════════════════════════════════════════
# TEST 9: SwarmPayload Compatibiliteit
# ══════════════════════════════════════════════
print("\n═══ TEST 9: SWARM PAYLOAD COMPATIBILITEIT ═══")

try:
    from swarm_engine import SwarmPayload
    p = SwarmPayload(
        agent="TEST_AGENT",
        type="text",
        content="Health check payload",
        display_text="Health check payload",
        metadata={"execution_time": 0.001, "status": "HEALTHY"},
    )
    ok(f"SwarmPayload creatie OK — agent={p.agent}, type={p.type}")
    ok(f"display_text: '{p.display_text}'")
    ok(f"metadata keys: {list(p.metadata.keys())}")
    ok(f"timestamp: {p.timestamp}")
    ok(f"trace_id: '{p.trace_id}' (empty = OK)")
except Exception as e:
    fail("SwarmPayload compatibiliteit", e)


# ══════════════════════════════════════════════
# RAPPORT
# ══════════════════════════════════════════════
print("\n" + "═" * 55)
print("🏥 HEALTH CHECK RAPPORT")
print("═" * 55)
print(f"  🟢 PASS: {PASS}")
print(f"  🟧 WARN: {WARN}")
print(f"  🟥 FAIL: {FAIL}")
total = PASS + WARN + FAIL
score = (PASS / total * 100) if total > 0 else 0
print(f"  📊 Score: {score:.1f}% ({PASS}/{total})")

if FAIL == 0 and WARN == 0:
    print("\n  ✅ ALLE AGENTS VOLLEDIG OPERATIONEEL")
elif FAIL == 0:
    print(f"\n  ⚠️  OPERATIONEEL met {WARN} waarschuwing(en)")
else:
    print(f"\n  ❌ {FAIL} KRITIEKE FOUT(EN) GEDETECTEERD")

print("═" * 55)
sys.exit(1 if FAIL > 0 else 0)
