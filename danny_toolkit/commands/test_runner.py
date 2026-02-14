# danny_toolkit/commands/test_runner.py — danny test & danny ci commands
"""
Lokale test runner die exact doet wat GitHub Actions CI doet.

Usage:
    danny test                    # Standaard tests (zonder stress)
    danny test --stress           # Inclusief stress/concurrency tests
    danny test --coverage         # Met coverage rapport (term-missing)
    danny test --html             # Coverage + HTML rapport in htmlcov/
    danny test --stress --html    # Alles

    danny ci                      # Volledige CI pipeline (= --stress --coverage)
"""
import subprocess
import sys
import time


def _run(cmd: list[str], label: str) -> int:
    """Draai een command en print status."""
    print(f"\n{'=' * 60}")
    print(f"  {label}")
    print(f"{'=' * 60}\n")
    result = subprocess.run(cmd)
    return result.returncode


def main():
    """Entry point voor `danny test`."""
    args = sys.argv[1:]

    stress = "--stress" in args
    coverage = "--coverage" in args
    html = "--html" in args

    cmd = [sys.executable, "-m", "pytest", "-v",
           "-o", "addopts="]  # Override pyproject.toml addopts

    # Marker filtering
    if not stress:
        cmd.extend(["-m", "not stress"])

    # Coverage
    if coverage or html:
        cmd.extend(["--cov=danny_toolkit", "--cov-report=term-missing"])
        if html:
            cmd.append("--cov-report=html")

    t0 = time.time()
    rc = _run(cmd, "danny test" + (" --stress" if stress else ""))
    dt = time.time() - t0

    print(f"\n  Klaar in {dt:.1f}s")
    if html and rc == 0:
        print("  HTML rapport: htmlcov/index.html")

    sys.exit(rc)


def ci():
    """Entry point voor `danny ci` — lokale CI pipeline.

    Draait exact wat GitHub Actions doet:
    1. Dependency check
    2. Alle tests (inclusief stress) met coverage
    """
    print("=" * 60)
    print("  DANNY CI — Lokale CI Pipeline")
    print("=" * 60)

    t0 = time.time()
    failures = []

    # Stap 1: Dependency check
    rc = _run(
        [sys.executable, "-m", "pip", "check"],
        "Stap 1/3: Dependency check",
    )
    if rc != 0:
        failures.append("dependency check")

    # Stap 2: Alle tests met coverage (inclusief stress)
    rc = _run(
        [
            sys.executable, "-m", "pytest", "-v",
            "-o", "addopts=",
            "--cov=danny_toolkit",
            "--cov-report=term-missing",
            "--cov-report=html",
        ],
        "Stap 2/3: Tests + coverage (alle markers)",
    )
    if rc != 0:
        failures.append("tests")

    # Stap 3: Lint check (als flake8 beschikbaar is)
    rc = _run(
        [sys.executable, "-m", "flake8",
         "--max-line-length=120",
         "--exclude=venv311,.git,__pycache__,htmlcov",
         "--count", "--statistics",
         "danny_toolkit/"],
        "Stap 3/3: Lint check (flake8)",
    )
    if rc != 0:
        failures.append("lint")

    dt = time.time() - t0

    # Samenvatting
    print(f"\n{'=' * 60}")
    print(f"  CI RESULTAAT")
    print(f"{'=' * 60}")
    print(f"  Tijd: {dt:.1f}s")
    print(f"  HTML coverage: htmlcov/index.html")

    if failures:
        print(f"  GEFAALD: {', '.join(failures)}")
        sys.exit(1)
    else:
        print("  ALLE STAPPEN GESLAAGD")
        sys.exit(0)
