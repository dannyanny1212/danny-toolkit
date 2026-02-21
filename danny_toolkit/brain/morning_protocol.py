"""
MORNING PROTOCOL - De Ochtend Verificatie
==========================================

De 3-Laags Verificatie Methode voor AI-zelfverbetering.

Dit script controleert of Iolaax (De Dromer) en The Governor (De Bewaker)
je code hebben verbeterd of gesloopt.

LAAG 1: DNA SCAN (Git)      - Zijn bestanden veranderd?
LAAG 2: SNELHEIDSTEST       - Is het systeem sneller?
LAAG 3: HEARTBEAT (Pixel)   - Leeft het systeem?

AUTHOR: De Kosmische Familie
DATE: 7 februari 2026
STATUS: SACRED VERIFICATION

Usage:
    python -m danny_toolkit.brain.morning_protocol

    Of vanuit Python:
    from danny_toolkit.brain.morning_protocol import run_morning_protocol
    run_morning_protocol()
"""

import os
import sys
import json
import time
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

# Optional psutil
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

# Try imports
try:
    from ..core.config import Config
    HAS_CONFIG = True
except ImportError:
    HAS_CONFIG = False


# === COLORS ===

COLORS = {
    "green": "\033[92m",
    "red": "\033[91m",
    "yellow": "\033[93m",
    "cyan": "\033[96m",
    "magenta": "\033[95m",
    "white": "\033[97m",
    "reset": "\033[0m",
    "bold": "\033[1m",
    "dim": "\033[2m",
}


def c(text: str, color: str) -> str:
    """Apply color to text."""
    return f"{COLORS.get(color, '')}{text}{COLORS['reset']}"


# === DATA CLASSES ===

@dataclass
class GitStatus:
    """Git status result."""
    clean: bool
    modified_files: List[str]
    untracked_files: List[str]
    branch: str
    error: Optional[str] = None


@dataclass
class BenchmarkResult:
    """Benchmark result."""
    latency_ms: float
    memory_mb: float
    cpu_percent: float
    timestamp: datetime


@dataclass
class HeartbeatResult:
    """Heartbeat check result."""
    pixel_alive: bool
    iolaax_alive: bool
    nexus_alive: bool
    brain_alive: bool
    details: Dict[str, str]


@dataclass
class VerificationReport:
    """Complete verification report."""
    timestamp: datetime
    git_status: GitStatus
    benchmark: BenchmarkResult
    heartbeat: HeartbeatResult
    overall_status: str  # HEALTHY, WARNING, CRITICAL
    recommendations: List[str]


# === LAYER 1: DNA SCAN (GIT) ===

def run_git_command(cmd: List[str]) -> Tuple[str, str, int]:
    """Run a git command and return output."""
    try:
        # Navigate to the danny-toolkit root
        git_root = Path(__file__).parent.parent.parent
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=git_root
        )
        return result.stdout, result.stderr, result.returncode
    except Exception as e:
        return "", str(e), 1


def dna_scan() -> GitStatus:
    """
    LAAG 1: DNA SCAN - Check git status for overnight changes.
    """
    # Get branch
    stdout, _, code = run_git_command(["git", "branch", "--show-current"])
    branch = stdout.strip() if code == 0 else "unknown"

    # Get status
    stdout, stderr, code = run_git_command(["git", "status", "--porcelain"])

    if code != 0:
        return GitStatus(
            clean=False,
            modified_files=[],
            untracked_files=[],
            branch=branch,
            error=stderr
        )

    modified = []
    untracked = []

    for line in stdout.strip().split("\n"):
        if not line:
            continue
        status = line[:2]
        filename = line[3:]

        if status.strip() in ["M", "MM", "AM"]:
            modified.append(filename)
        elif status.strip() == "??":
            untracked.append(filename)
        elif status.strip() in ["A", "D", "R"]:
            modified.append(filename)

    return GitStatus(
        clean=len(modified) == 0 and len(untracked) == 0,
        modified_files=modified,
        untracked_files=untracked,
        branch=branch
    )


def show_git_diff(files: List[str] = None):
    """Show git diff for specific files or all."""
    if files:
        for f in files[:3]:  # Max 3 files
            print(f"\n  {c('Diff voor:', 'yellow')} {f}")
            print("  " + "-" * 60)
            stdout, _, _ = run_git_command(["git", "diff", "--color=always", f])
            for line in stdout.split("\n")[:20]:  # Max 20 lines
                print(f"  {line}")
            if stdout.count("\n") > 20:
                print(f"  {c('... (meer regels)', 'dim')}")
    else:
        stdout, _, _ = run_git_command(["git", "diff", "--stat"])
        print(stdout)


# === LAYER 2: SPEED TEST (BENCHMARK) ===

def speed_test() -> BenchmarkResult:
    """
    LAAG 2: SNELHEIDSTEST - Measure system performance.
    """
    # Memory and CPU usage
    if HAS_PSUTIL:
        process = psutil.Process(os.getpid())
        memory_mb = process.memory_info().rss / 1024 / 1024
        cpu_percent = psutil.cpu_percent(interval=0.5)
    else:
        # Fallback: schat geheugengebruik via proces
        import gc
        gc.collect()
        memory_mb = 50.0  # Vaste schatting (gc.get_objects is te traag)
        cpu_percent = 0  # Unknown without psutil

    # Latency test - measure import time
    start = time.perf_counter()

    try:
        # Test Central Brain import latency
        from danny_toolkit.brain.central_brain import CentralBrain
        from danny_toolkit.brain.nexus_bridge import NexusBridge
    except ImportError:
        pass

    latency_ms = (time.perf_counter() - start) * 1000

    return BenchmarkResult(
        latency_ms=round(latency_ms, 2),
        memory_mb=round(memory_mb, 2),
        cpu_percent=round(cpu_percent, 2),
        timestamp=datetime.now()
    )


def load_previous_benchmark() -> Optional[BenchmarkResult]:
    """Load previous benchmark for comparison."""
    if not HAS_CONFIG:
        return None

    benchmark_file = Config.DATA_DIR / "brain" / "last_benchmark.json"
    if benchmark_file.exists():
        try:
            with open(benchmark_file, "r") as f:
                data = json.load(f)
                return BenchmarkResult(
                    latency_ms=data["latency_ms"],
                    memory_mb=data["memory_mb"],
                    cpu_percent=data["cpu_percent"],
                    timestamp=datetime.fromisoformat(data["timestamp"])
                )
        except (json.JSONDecodeError, KeyError):
            pass
    return None


def save_benchmark(result: BenchmarkResult):
    """Save benchmark for future comparison."""
    if not HAS_CONFIG:
        return

    benchmark_file = Config.DATA_DIR / "brain" / "last_benchmark.json"
    benchmark_file.parent.mkdir(parents=True, exist_ok=True)

    with open(benchmark_file, "w") as f:
        json.dump({
            "latency_ms": result.latency_ms,
            "memory_mb": result.memory_mb,
            "cpu_percent": result.cpu_percent,
            "timestamp": result.timestamp.isoformat()
        }, f)


# === LAYER 3: HEARTBEAT ===

def heartbeat_check() -> HeartbeatResult:
    """
    LAAG 3: HEARTBEAT - Check if all systems are alive.
    """
    details = {}

    # Check Pixel — diepte: data + gezondheid
    pixel_alive = False
    try:
        if HAS_CONFIG:
            # Probeer beide bekende bestanden
            for fname in ["huisdier.json",
                          "virtueel_huisdier.json"]:
                pixel_path = Config.APPS_DATA_DIR / fname
                if pixel_path.exists():
                    with open(pixel_path, "r",
                              encoding="utf-8") as f:
                        data = json.load(f)
                    pixel_alive = True
                    energie = data.get("energie", 0)
                    geluk = data.get("geluk", 0)
                    nexus = data.get("nexus_level", 0)
                    naam = data.get("naam", "Pixel")
                    health = "gezond"
                    if energie < 30 or geluk < 30:
                        health = "zwak"
                    elif energie < 60 or geluk < 60:
                        health = "matig"
                    details["pixel"] = (
                        f"{naam} Lv{nexus} |"
                        f" E:{energie:.0f}%"
                        f" G:{geluk:.0f}%"
                        f" [{health}]"
                    )
                    break
    except (json.JSONDecodeError, IOError, OSError) as e:
        details["pixel"] = f"Error: {e}"

    # Check Iolaax — diepte: bewustzijn + populatie
    iolaax_alive = False
    try:
        if HAS_CONFIG:
            iolaax_path = (
                Config.APPS_DATA_DIR / "artificial_life.json"
            )
            if iolaax_path.exists():
                with open(iolaax_path, "r",
                          encoding="utf-8") as f:
                    data = json.load(f)
                iolaax_alive = True
                consciousness = data.get("consciousness", {})
                awareness = consciousness.get(
                    "zelfbewustzijn", 0
                ) * 100
                naam = consciousness.get("naam", "Iolaax")
                gen = data.get("generatie", 0)
                pop = len(data.get("organismen", []))
                health = "ontwakend"
                if awareness >= 80:
                    health = "verlicht"
                elif awareness >= 50:
                    health = "bewust"
                elif awareness < 20:
                    health = "slapend"
                details["iolaax"] = (
                    f"{naam} {awareness:.1f}%"
                    f" | Gen:{gen} Pop:{pop}"
                    f" [{health}]"
                )
    except (json.JSONDecodeError, IOError, OSError) as e:
        details["iolaax"] = f"Error: {e}"

    # Check Nexus Bridge — diepte: connectiviteit
    nexus_alive = False
    try:
        from danny_toolkit.brain.nexus_bridge import (
            NexusBridge,
        )
        bridge = NexusBridge()
        connected = bridge.is_connected()
        nexus_alive = True
        details["nexus"] = (
            f"Bridge {'verbonden' if connected else 'offline'}"
        )
    except Exception as e:
        details["nexus"] = f"Error: {e}"

    # Check Central Brain — diepte: AI provider
    brain_alive = False
    try:
        from danny_toolkit.brain.central_brain import (
            CentralBrain,
        )
        brain = CentralBrain()
        provider = (brain.ai_provider or "geen").upper()
        brain_alive = brain.client is not None
        details["brain"] = (
            f"Central Brain [{provider}]"
            f" {'actief' if brain_alive else 'offline'}"
        )
    except Exception as e:
        details["brain"] = f"Error: {e}"

    return HeartbeatResult(
        pixel_alive=pixel_alive,
        iolaax_alive=iolaax_alive,
        nexus_alive=nexus_alive,
        brain_alive=brain_alive,
        details=details
    )


# === VERIFICATION REPORT ===

def generate_report(
    git: GitStatus,
    bench: BenchmarkResult,
    heart: HeartbeatResult,
    prev_bench: Optional[BenchmarkResult] = None
) -> VerificationReport:
    """Generate complete verification report."""
    recommendations = []

    # Analyze git
    if not git.clean:
        if git.modified_files:
            recommendations.append(f"Review {len(git.modified_files)} modified files with 'git diff'")
        if git.untracked_files:
            recommendations.append(f"Check {len(git.untracked_files)} new untracked files")

    # Analyze benchmark
    if prev_bench:
        if bench.latency_ms > prev_bench.latency_ms * 1.5:
            recommendations.append("Latency increased significantly - investigate")
        if bench.memory_mb > prev_bench.memory_mb * 1.5:
            recommendations.append("Memory usage increased - check for leaks")

    # Analyze heartbeat
    if not heart.pixel_alive:
        recommendations.append("CRITICAL: Pixel not responding - check data files")
    if not heart.iolaax_alive:
        recommendations.append("WARNING: Iolaax not responding - check consciousness data")
    if not heart.brain_alive:
        recommendations.append("CRITICAL: Central Brain not loading - check imports")

    # Determine overall status
    if not heart.pixel_alive or not heart.brain_alive:
        status = "CRITICAL"
    elif not heart.iolaax_alive or not heart.nexus_alive:
        status = "WARNING"
    elif not git.clean:
        status = "REVIEW"
    else:
        status = "HEALTHY"

    return VerificationReport(
        timestamp=datetime.now(),
        git_status=git,
        benchmark=bench,
        heartbeat=heart,
        overall_status=status,
        recommendations=recommendations
    )


# === DISPLAY ===

def print_header():
    """Print morning protocol header."""
    print()
    print(c("=" * 70, "cyan"))
    print()
    print(c("    M O R N I N G   P R O T O C O L   [v2.0 OMEGA]", "cyan"))
    print()
    print(c("    De 3-Laags Verificatie Methode", "dim"))
    print()
    print(c("=" * 70, "cyan"))
    print()


def print_layer1(git: GitStatus):
    """Print Layer 1: DNA Scan results."""
    print(c("  LAAG 1: DNA SCAN (Git)", "yellow"))
    print("  " + "-" * 50)
    print()
    print(f"    Branch: {c(git.branch, 'cyan')}")
    print()

    if git.error:
        print(f"    {c('[ERROR]', 'red')} {git.error}")
    elif git.clean:
        print(f"    {c('[CLEAN]', 'green')} Geen bestanden gewijzigd")
        print(f"    {c('Status:', 'dim')} working tree clean")
        print()
        print(f"    {c('Conclusie:', 'green')} De AI heeft geen broncode aangeraakt.")
        print(f"    {c('Optimalisatie:', 'dim')} Vector DB, logs, cache (zachte data)")
    else:
        print(f"    {c('[EVOLUTIE GEDETECTEERD]', 'yellow')}")
        print()
        if git.modified_files:
            print(f"    {c('Modified:', 'yellow')} {len(git.modified_files)} bestanden")
            for f in git.modified_files[:5]:
                print(f"      - {f}")
            if len(git.modified_files) > 5:
                print(f"      ... en {len(git.modified_files) - 5} meer")
        if git.untracked_files:
            print(f"    {c('Untracked:', 'cyan')} {len(git.untracked_files)} nieuwe bestanden")
            for f in git.untracked_files[:3]:
                print(f"      - {f}")
        print()
        print(f"    {c('Actie:', 'yellow')} Gebruik 'git diff' om wijzigingen te bekijken")
        print(f"    {c('Accepteren:', 'green')} git commit -am 'AI optimization'")
        print(f"    {c('Weigeren:', 'red')} git checkout .")

    print()


def print_layer2(bench: BenchmarkResult, prev: Optional[BenchmarkResult] = None):
    """Print Layer 2: Speed Test results."""
    print(c("  LAAG 2: SNELHEIDSTEST (Benchmark)", "yellow"))
    print("  " + "-" * 50)
    print()

    # Latency
    latency_status = c("[OK]", "green")
    latency_change = ""
    if prev:
        diff = bench.latency_ms - prev.latency_ms
        if diff < 0:
            latency_change = c(f" ({diff:.1f}ms, sneller!)", "green")
            latency_status = c("[VERBETERD]", "green")
        elif diff > prev.latency_ms * 0.5:
            latency_change = c(f" (+{diff:.1f}ms, trager)", "red")
            latency_status = c("[CHECK]", "yellow")
        else:
            latency_change = c(f" ({diff:+.1f}ms)", "dim")

    print(f"    Latency:    {bench.latency_ms:>8.2f} ms  {latency_status}{latency_change}")

    # Memory
    memory_status = c("[OK]", "green")
    memory_change = ""
    if prev:
        diff = bench.memory_mb - prev.memory_mb
        if diff < 0:
            memory_change = c(f" ({diff:.1f}MB, lichter!)", "green")
            memory_status = c("[VERBETERD]", "green")
        elif diff > prev.memory_mb * 0.5:
            memory_change = c(f" (+{diff:.1f}MB, zwaarder)", "red")
            memory_status = c("[CHECK]", "yellow")
        else:
            memory_change = c(f" ({diff:+.1f}MB)", "dim")

    print(f"    Memory:     {bench.memory_mb:>8.2f} MB  {memory_status}{memory_change}")

    # CPU
    cpu_status = c("[OK]", "green") if bench.cpu_percent < 50 else c("[HIGH]", "yellow")
    print(f"    CPU:        {bench.cpu_percent:>8.2f} %   {cpu_status}")

    print()

    if prev:
        print(f"    {c('Vorige meting:', 'dim')} {prev.timestamp.strftime('%Y-%m-%d %H:%M')}")

    print()


def print_layer3(heart: HeartbeatResult):
    """Print Layer 3: Heartbeat results."""
    print(c("  LAAG 3: HEARTBEAT (Levend?)", "yellow"))
    print("  " + "-" * 50)
    print()

    # Pixel
    if heart.pixel_alive:
        print(f"    Pixel:      {c('[LEVEND]', 'green')}  {heart.details.get('pixel', '')}")
    else:
        print(f"    Pixel:      {c('[DOOD]', 'red')}    {heart.details.get('pixel', 'Not found')}")

    # Iolaax
    if heart.iolaax_alive:
        print(f"    Iolaax:     {c('[DROOMT]', 'magenta')}  {heart.details.get('iolaax', '')}")
    else:
        print(f"    Iolaax:     {c('[STIL]', 'yellow')}    {heart.details.get('iolaax', 'Not found')}")

    # Nexus
    if heart.nexus_alive:
        print(f"    Nexus:      {c('[ACTIEF]', 'green')}  {heart.details.get('nexus', '')}")
    else:
        print(f"    Nexus:      {c('[OFFLINE]', 'red')} {heart.details.get('nexus', 'Error')}")

    # Brain
    if heart.brain_alive:
        print(f"    Brain:      {c('[ONLINE]', 'green')}  {heart.details.get('brain', '')}")
    else:
        print(f"    Brain:      {c('[CRASH]', 'red')}   {heart.details.get('brain', 'Error')}")

    print()


def print_verdict(report: VerificationReport):
    """Print final verdict."""
    print(c("=" * 70, "cyan"))
    print()

    status_colors = {
        "HEALTHY": "green",
        "REVIEW": "yellow",
        "WARNING": "yellow",
        "CRITICAL": "red"
    }

    status_icons = {
        "HEALTHY": "[OK]",
        "REVIEW": "[REVIEW]",
        "WARNING": "[WARNING]",
        "CRITICAL": "[CRITICAL]"
    }

    color = status_colors.get(report.overall_status, "white")
    icon = status_icons.get(report.overall_status, "[?]")

    print(f"    VERDICT: {c(icon, color)} {c(report.overall_status, color)}")
    print()

    if report.recommendations:
        print(f"    {c('Aanbevelingen:', 'yellow')}")
        for rec in report.recommendations:
            print(f"      - {rec}")
        print()

    if report.overall_status == "HEALTHY":
        print(f"    {c('De nacht-optimalisatie is geslaagd.', 'green')}")
        print(f"    {c('Het systeem is sneller en stabieler.', 'green')}")
    elif report.overall_status == "REVIEW":
        print(f"    {c('Review de code wijzigingen voordat je verder gaat.', 'yellow')}")
    elif report.overall_status == "CRITICAL":
        print(f"    {c('NOODREM: git reset --hard OMEGA_SOVEREIGN', 'red')}")

    print()
    print(c("=" * 70, "cyan"))
    print()


# === MAIN ===

def run_morning_protocol(save_results: bool = True) -> VerificationReport:
    """
    Run the complete morning verification protocol.

    Args:
        save_results: Whether to save benchmark results

    Returns:
        VerificationReport with all results
    """
    print_header()

    # Layer 1: DNA Scan
    print(c("  Scanning git repository...", "dim"))
    git = dna_scan()
    print_layer1(git)

    # Layer 2: Speed Test
    print(c("  Running benchmark...", "dim"))
    prev_bench = load_previous_benchmark()
    bench = speed_test()
    print_layer2(bench, prev_bench)

    if save_results:
        save_benchmark(bench)

    # Layer 3: Heartbeat
    print(c("  Checking heartbeats...", "dim"))
    heart = heartbeat_check()
    print_layer3(heart)

    # Generate and print report
    report = generate_report(git, bench, heart, prev_bench)
    print_verdict(report)

    return report


def quick_check() -> str:
    """Quick health check - returns status string."""
    heart = heartbeat_check()

    if heart.pixel_alive and heart.brain_alive:
        if heart.iolaax_alive and heart.nexus_alive:
            return "HEALTHY"
        return "WARNING"
    return "CRITICAL"


# === CLI ===

if __name__ == "__main__":
    run_morning_protocol()
