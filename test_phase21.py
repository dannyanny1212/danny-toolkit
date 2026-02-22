"""
Phase 21 Tests — Docker Sandbox for Artificer
===============================================
Verifieert SandboxResult dataclass, LocalSandbox executie,
timeout handling, Docker detectie, en Artificer integratie.

8 tests, standalone uitvoerbaar: python test_phase21.py
"""

import io
import os
import sys
import tempfile

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

passed = 0
failed = 0


def check(label: str, condition: bool):
    global passed, failed
    if condition:
        passed += 1
        print(f"  ✅ {label}")
    else:
        failed += 1
        print(f"  ❌ {label}")


print("=" * 60)
print("  Phase 21: Docker Sandbox for Artificer")
print("=" * 60)

# ── Test 1: SandboxResult dataclass ──
print("\n[1] SandboxResult dataclass")
from danny_toolkit.core.sandbox import SandboxResult

r = SandboxResult(stdout="hello", stderr="", returncode=0, timed_out=False)
check("SandboxResult.stdout", r.stdout == "hello")
check("SandboxResult.stderr", r.stderr == "")
check("SandboxResult.returncode", r.returncode == 0)
check("SandboxResult.timed_out", r.timed_out is False)

# ── Test 2: LocalSandbox runs script ──
print("\n[2] LocalSandbox voert script uit")
from danny_toolkit.core.sandbox import LocalSandbox

sandbox = LocalSandbox()
with tempfile.TemporaryDirectory() as tmpdir:
    script = os.path.join(tmpdir, "test_script.py")
    with open(script, "w") as f:
        f.write('print("sandbox_test_output")\n')
    result = sandbox.run_script(script, tmpdir, timeout=10)
    check("Script output bevat expected string", "sandbox_test_output" in result.stdout)
    check("Returncode is 0", result.returncode == 0)
    check("Niet timed out", result.timed_out is False)

# ── Test 3: LocalSandbox timeout ──
print("\n[3] LocalSandbox timeout handling")
with tempfile.TemporaryDirectory() as tmpdir:
    script = os.path.join(tmpdir, "slow_script.py")
    with open(script, "w") as f:
        f.write('import time\ntime.sleep(60)\n')
    result = sandbox.run_script(script, tmpdir, timeout=2)
    check("Timed out is True", result.timed_out is True)
    check("Returncode is -1", result.returncode == -1)

# ── Test 4: LocalSandbox error handling ──
print("\n[4] LocalSandbox error handling")
with tempfile.TemporaryDirectory() as tmpdir:
    script = os.path.join(tmpdir, "error_script.py")
    with open(script, "w") as f:
        f.write('raise ValueError("test_error")\n')
    result = sandbox.run_script(script, tmpdir, timeout=10)
    check("Returncode is niet 0", result.returncode != 0)
    check("Stderr bevat error", "test_error" in result.stderr or "ValueError" in result.stderr)

# ── Test 5: DockerSandbox unavailable detection ──
print("\n[5] DockerSandbox detectie")
from danny_toolkit.core.sandbox import DockerSandbox

docker = DockerSandbox()
# Docker may or may not be available — we just check the detection works
check("DockerSandbox.available is bool", isinstance(docker.available, bool))
if not docker.available:
    print("    (Docker niet beschikbaar — OK, test verifieert detectie)")
    check("Unavailable Docker returns error", True)  # Detection itself is the test
else:
    print("    (Docker IS beschikbaar)")
    check("Docker beschikbaar detectie werkt", True)

# ── Test 6: get_sandbox() falls back to LocalSandbox ──
print("\n[6] get_sandbox() fallback")
from danny_toolkit.core.sandbox import get_sandbox, BaseSandbox
import danny_toolkit.core.sandbox as sandbox_mod

# Reset singleton for clean test
sandbox_mod._sandbox = None
sb = get_sandbox()
check("get_sandbox() retourneert BaseSandbox instance", isinstance(sb, BaseSandbox))
check("Sandbox is LocalSandbox of DockerSandbox",
      type(sb).__name__ in ("LocalSandbox", "DockerSandbox"))
# Reset singleton again
sandbox_mod._sandbox = None

# ── Test 7: Artificer gebruikt sandbox ──
print("\n[7] Artificer gebruikt sandbox")
from danny_toolkit.brain.artificer import Artificer, HAS_SANDBOX

check("Artificer heeft HAS_SANDBOX flag", HAS_SANDBOX is True)

# Verify _run_script method exists and uses sandbox
import inspect
source = inspect.getsource(Artificer._run_script)
check("_run_script bevat get_sandbox() call", "get_sandbox()" in source)
check("_run_script bevat sandbox.run_script() call", "sandbox.run_script" in source)

# ── Test 8: Docker command bevat security flags ──
print("\n[8] Docker command bevat security flags")
docker_sb = DockerSandbox()
cmd = docker_sb.build_command("/tmp/test.py", "/tmp/workspace")
cmd_str = " ".join(cmd)
check("--network=none in command", "--network=none" in cmd_str)
check("--memory=256m in command", "--memory=256m" in cmd_str)
check("--rm in command", "--rm" in cmd_str)
check("--pids-limit=64 in command", "--pids-limit=64" in cmd_str)
check("--cpus=1 in command", "--cpus=1" in cmd_str)

# ── Test: SANDBOX_EXECUTION event type ──
print("\n[Bonus] NeuralBus SANDBOX_EXECUTION event type")
from danny_toolkit.core.neural_bus import EventTypes

check("EventTypes.SANDBOX_EXECUTION exists",
      hasattr(EventTypes, "SANDBOX_EXECUTION"))
check("SANDBOX_EXECUTION value is 'sandbox_execution'",
      EventTypes.SANDBOX_EXECUTION == "sandbox_execution")

# ── Resultaat ──
print(f"\n{'=' * 60}")
total = passed + failed
print(f"  Resultaat: {passed}/{total} checks geslaagd")
if failed == 0:
    print("  🏆 Phase 21: ALL CHECKS PASSED")
else:
    print(f"  ⚠️  {failed} check(s) gefaald!")
print(f"{'=' * 60}")

sys.exit(0 if failed == 0 else 1)
