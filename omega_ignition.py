"""Omega Ignition v7.0 — Async Bootstrap with Lifespan Manager & Graceful Shutdown.

Upgrade van v6.0: asynccontextmanager lifespan, 5-fase boot, transparante logging,
SwarmEngine deploy, graceful shutdown met Ouroboros self-preservation.

Gebruik: python omega_ignition.py
"""

from __future__ import annotations

import asyncio
import atexit
import json
import logging
import os
import shutil
import signal
import sqlite3
import subprocess
import sys
import time
import urllib.request
from contextlib import asynccontextmanager
from typing import AsyncIterator

# Windows UTF-8 fix (project conventie)
if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Forceer het pad
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from danny_toolkit.core.utils import Kleur
from danny_toolkit.core.config import Config

# Transparante logger (ter preventie van swallowed exceptions)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("Omega.Genesis")

_ROOT_DIR = os.path.dirname(os.path.abspath(__file__))


# ═══════════════════════════════════════════════════════════════
#  PHASE 1: DATA/SOUL LAYER
# ═══════════════════════════════════════════════════════════════

def _check_databases() -> tuple[int, list[str]]:
    """Verify 4 SQLite WAL databases. Returns (error_count, status_lines)."""
    errors = 0
    lines = []
    dbs = {
        "cortical_stack.db": "Episodic + Semantic Memory",
        "waakhuis_metrics.db": "Health Monitoring",
        "semantic_cache.db": "Vector Response Cache",
        "self_pruning.db": "Fragment Access Tracking",
    }
    data_dir = os.path.join(_ROOT_DIR, "data")

    for db_file, purpose in dbs.items():
        db_path = os.path.join(data_dir, db_file)
        if not os.path.exists(db_path):
            lines.append(f"  {Kleur.GEEL}~ {db_file}: Niet gevonden (wordt aangemaakt bij eerste gebruik){Kleur.RESET}")
            continue
        try:
            conn = sqlite3.connect(db_path)
            Config.apply_sqlite_perf(conn)
            integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
            journal = conn.execute("PRAGMA journal_mode").fetchone()[0]
            tables = conn.execute("SELECT count(*) FROM sqlite_master WHERE type='table'").fetchone()[0]
            size_kb = os.path.getsize(db_path) // 1024
            conn.close()
            if integrity.lower() == "ok":
                lines.append(
                    f"  {Kleur.GROEN}✔ {db_file}: {integrity.upper()} | "
                    f"{journal.upper()} | {tables} tables | {size_kb}KB — {purpose}{Kleur.RESET}"
                )
            else:
                lines.append(f"  {Kleur.ROOD}❌ {db_file}: INTEGRITY FAILED — {integrity}{Kleur.RESET}")
                errors += 1
        except Exception as e:
            lines.append(f"  {Kleur.ROOD}❌ {db_file}: {e}{Kleur.RESET}")
            errors += 1

    # ChromaDB check
    chroma_dir = os.path.join(data_dir, "rag", "chromadb")
    if os.path.isdir(chroma_dir):
        collections = [d for d in os.listdir(chroma_dir) if os.path.isdir(os.path.join(chroma_dir, d))]
        lines.append(f"  {Kleur.GROEN}✔ ChromaDB: {len(collections)} collection dirs{Kleur.RESET}")
    else:
        lines.append(f"  {Kleur.GEEL}~ ChromaDB: Directory niet gevonden{Kleur.RESET}")

    return errors, lines


# ═══════════════════════════════════════════════════════════════
#  PHASE 2: HARDWARE & API
# ═══════════════════════════════════════════════════════════════

def _check_hardware_api() -> tuple[int, list[str]]:
    """Check Groq API keys + Ollama. Returns (error_count, status_lines)."""
    errors = 0
    lines = []

    # Groq keys (10-key isolation)
    groq_main = os.getenv("GROQ_API_KEY")
    groq_count = sum(1 for i in range(1, 11) if os.getenv(f"GROQ_API_KEY_{['USER','VERIFY','RESEARCH','WALKER','FORGE','OVERNIGHT','KNOWLEDGE','RESERVE_1','RESERVE_2','RESERVE_3'][i-1]}"))
    if groq_main:
        lines.append(f"  {Kleur.GROEN}✔ Groq API: Actief (main + {groq_count} role keys){Kleur.RESET}")
    else:
        lines.append(f"  {Kleur.ROOD}❌ Groq API Key: ONTBREEKT{Kleur.RESET}")
        errors += 1

    # Voyage embeddings
    if os.getenv("VOYAGE_API_KEY"):
        lines.append(f"  {Kleur.GROEN}✔ Voyage Embeddings: Actief{Kleur.RESET}")
    else:
        lines.append(f"  {Kleur.GEEL}~ Voyage API Key: niet gevonden (fallback embeddings){Kleur.RESET}")

    # Ollama (vision)
    try:
        req = urllib.request.Request("http://localhost:11434/api/tags")
        with urllib.request.urlopen(req, timeout=2) as response:
            if response.status == 200:
                data = json.loads(response.read().decode())
                models = [m["name"] for m in data.get("models", [])]
                has_llava = any("llava" in m for m in models)
                if has_llava:
                    lines.append(f"  {Kleur.GROEN}✔ Visual Cortex (Ollama/Llava): Online{Kleur.RESET}")
                else:
                    lines.append(f"  {Kleur.GEEL}~ Ollama draait ({len(models)} models), maar 'llava' ontbreekt{Kleur.RESET}")
    except Exception as e:
        logger.debug("Ollama check: %s", e)
        lines.append(f"  {Kleur.GEEL}~ Visual Cortex (Ollama): Offline (niet vereist){Kleur.RESET}")

    return errors, lines


# ═══════════════════════════════════════════════════════════════
#  PHASE 3: NEURAL LINK (Brain imports)
# ═══════════════════════════════════════════════════════════════

def _check_neural_link() -> tuple[int, list[str]]:
    """Verify critical brain module imports. Returns (error_count, status_lines)."""
    errors = 0
    lines = []

    # Suppress stdout during imports (Governor/Daemon banners)
    _real_stdout = sys.stdout
    _devnull = open(os.devnull, "w", encoding="utf-8")

    # Core brain modules
    modules = {
        "NeuralBus": ("danny_toolkit.core.neural_bus", "get_bus"),
        "CorticalStack": ("danny_toolkit.brain.cortical_stack", "get_cortical_stack"),
        "TheSynapse": ("danny_toolkit.brain.synapse", "get_synapse"),
        "HallucinatieSchild": ("danny_toolkit.brain.hallucination_shield", "get_hallucination_shield"),
        "BlackBox": ("danny_toolkit.brain.black_box", "get_black_box"),
        "Waakhuis": ("danny_toolkit.brain.waakhuis", "get_waakhuis"),
    }

    for name, (module_path, factory) in modules.items():
        try:
            sys.stdout = _devnull
            mod = __import__(module_path, fromlist=[factory])
            instance = getattr(mod, factory)()
            sys.stdout = _real_stdout
            lines.append(f"  {Kleur.GROEN}✔ {name}: Online{Kleur.RESET}")
        except Exception as e:
            sys.stdout = _real_stdout
            lines.append(f"  {Kleur.GEEL}~ {name}: {e}{Kleur.RESET}")

    # SwarmEngine import check
    try:
        sys.stdout = _devnull
        from swarm_engine import SwarmEngine
        sys.stdout = _real_stdout
        lines.append(f"  {Kleur.GROEN}✔ SwarmEngine: Importeerbaar (18 agents){Kleur.RESET}")
    except Exception as e:
        sys.stdout = _real_stdout
        lines.append(f"  {Kleur.ROOD}❌ SwarmEngine: {e}{Kleur.RESET}")
        errors += 1

    _devnull.close()
    return errors, lines


# ═══════════════════════════════════════════════════════════════
#  PHASE 4: SWARM DEPLOY
# ═══════════════════════════════════════════════════════════════

def _deploy_swarm() -> tuple[int, list[str], object]:
    """Instantiate SwarmEngine + PrometheusBrain. Returns (errors, lines, engine)."""
    errors = 0
    lines = []
    engine = None

    _real_stdout = sys.stdout
    _devnull = open(os.devnull, "w", encoding="utf-8")

    try:
        sys.stdout = _devnull
        from swarm_engine import SwarmEngine
        from danny_toolkit.brain.trinity_omega import PrometheusBrain
        brain = PrometheusBrain()
        engine = SwarmEngine(brain=brain)
        sys.stdout = _real_stdout

        agent_count = len(engine.agents)
        agent_names = sorted(engine.agents.keys())
        lines.append(f"  {Kleur.GROEN}✔ PrometheusBrain: Initialized{Kleur.RESET}")
        lines.append(f"  {Kleur.GROEN}✔ SwarmEngine: {agent_count} agents deployed{Kleur.RESET}")
        lines.append(f"  {Kleur.CYAAN}    Agents: {', '.join(agent_names[:9])}{Kleur.RESET}")
        lines.append(f"  {Kleur.CYAAN}            {', '.join(agent_names[9:])}{Kleur.RESET}")

        # Verify routing
        route_map_count = len(engine.ROUTE_MAP)
        lines.append(f"  {Kleur.GROEN}✔ ROUTE_MAP: {route_map_count} entries | AdaptiveRouter: Ready{Kleur.RESET}")

    except Exception as e:
        sys.stdout = _real_stdout
        lines.append(f"  {Kleur.ROOD}❌ Swarm Deploy Failed: {e}{Kleur.RESET}")
        errors += 1

    _devnull.close()
    return errors, lines, engine


# ═══════════════════════════════════════════════════════════════
#  PHASE 5: MEMORY OPTIMALISATIE
# ═══════════════════════════════════════════════════════════════

def _optimize_memory() -> list[str]:
    """SQLite vacuum + cache clear. Returns status lines."""
    lines = []

    # SQLite vacuum on cortical_stack
    db_path = os.path.join(_ROOT_DIR, "data", "cortical_stack.db")
    if os.path.exists(db_path):
        try:
            conn = sqlite3.connect(db_path)
            conn.execute("VACUUM")
            conn.close()
            lines.append(f"  {Kleur.GROEN}✔ CorticalStack: Gedefragmenteerd{Kleur.RESET}")
        except Exception as e:
            lines.append(f"  {Kleur.GEEL}~ CorticalStack vacuum: {e}{Kleur.RESET}")

    # Clear __pycache__
    pycache = os.path.join(_ROOT_DIR, "danny_toolkit", "brain", "__pycache__")
    if os.path.exists(pycache):
        shutil.rmtree(pycache)
        lines.append(f"  {Kleur.GROEN}✔ Brain Cache: Geklaard{Kleur.RESET}")

    return lines


# ═══════════════════════════════════════════════════════════════
#  LIFESPAN MANAGER — Async Context Manager
# ═══════════════════════════════════════════════════════════════

@asynccontextmanager
async def omega_lifespan() -> AsyncIterator[object]:
    """Async lifespan manager: boot all subsystems, yield engine, graceful shutdown."""

    os.system("cls" if os.name == "nt" else "clear")
    print(f"{Kleur.CYAAN}")
    print("   ____  __  __ _____ ____    _      ___ ____ _   _ ___ _____ ___ ___  _   _ ")
    print("  / __ \\|  \\/  | ____/ ___|  / \\    |_ _/ ___| \\ | |_ _|_   _|_ _/ _ \\| \\ | |")
    print(" | |  | | |\\/| |  _|| |  _  / _ \\    | | |  _|  \\| || |  | |  | | | | |  \\| |")
    print(" | |__| | |  | | |__| |_| |/ ___ \\   | | |_| | |\\  || |  | |  | | |_| | |\\  |")
    print("  \\____/|_|  |_|_____|\\____/_/   \\_\\ |___|\\____|_| \\_|___| |_| |___|\\___/|_| \\_|")
    print(f"                                                       v7.0 Lifespan Manager{Kleur.RESET}")
    print()

    total_errors = 0
    t_start = time.time()

    # ── Phase 1: Data/Soul Layer ──
    logger.info("Phase 1: Waking Data/Soul layer (ChromaDB & 4 SQLite WAL databases)...")
    print(f"{Kleur.GEEL}[1/5] DATA/SOUL LAYER{Kleur.RESET}")
    db_errors, db_lines = _check_databases()
    total_errors += db_errors
    for line in db_lines:
        print(line)

    # ── Phase 2: Hardware & API ──
    logger.info("Phase 2: Hardware & API verification...")
    print(f"\n{Kleur.GEEL}[2/5] HARDWARE & API{Kleur.RESET}")
    hw_errors, hw_lines = _check_hardware_api()
    total_errors += hw_errors
    for line in hw_lines:
        print(line)

    # ── Phase 3: Neural Link ──
    logger.info("Phase 3: Neural Link — brain module verification...")
    print(f"\n{Kleur.GEEL}[3/5] NEURAL LINK{Kleur.RESET}")
    nl_errors, nl_lines = _check_neural_link()
    total_errors += nl_errors
    for line in nl_lines:
        print(line)

    # ── Phase 4: Swarm Deploy ──
    logger.info("Phase 4: Deploying SwarmEngine & 18 Agents (incl. WEAVER)...")
    print(f"\n{Kleur.GEEL}[4/5] SWARM DEPLOY{Kleur.RESET}")
    sw_errors, sw_lines, engine = _deploy_swarm()
    total_errors += sw_errors
    for line in sw_lines:
        print(line)

    # ── Phase 5: Memory Optimization ──
    logger.info("Phase 5: Memory optimization...")
    print(f"\n{Kleur.GEEL}[5/5] MEMORY OPTIMALISATIE{Kleur.RESET}")
    opt_lines = _optimize_memory()
    for line in opt_lines:
        print(line)

    # ── Boot Result ──
    elapsed = time.time() - t_start
    print()
    if total_errors > 0:
        print(
            f"{Kleur.ROOD}Boot completed with {total_errors} error(s) in {elapsed:.1f}s. "
            f"Systeem is mogelijk instabiel.{Kleur.RESET}"
        )
        logger.warning("Boot completed with %d errors in %.1fs", total_errors, elapsed)
    else:
        print(
            f"{Kleur.GROEN}All systems nominal. Boot completed in {elapsed:.1f}s.{Kleur.RESET}"
        )
        logger.info("Boot completed successfully in %.1fs", elapsed)

    print(f"\n{Kleur.CYAAN}{'='*60}{Kleur.RESET}")
    print(f"{Kleur.CYAAN}  OMEGA IS AWAKE. SOVEREIGN STATUS: ACTIVE.{Kleur.RESET}")
    print(f"{Kleur.CYAAN}{'='*60}{Kleur.RESET}\n")
    logger.info("OMEGA IS AWAKE. SOVEREIGN STATUS: ACTIVE.")

    # ── YIELD — System is live ──
    yield engine

    # ── GRACEFUL SHUTDOWN ──
    logger.info("Initiating graceful shutdown (Ouroboros self-preservation)...")
    print(f"\n{Kleur.MAGENTA}Graceful shutdown initiated...{Kleur.RESET}")

    # Flush CorticalStack
    try:
        from danny_toolkit.brain.cortical_stack import get_cortical_stack
        stack = get_cortical_stack()
        stack.flush()
        logger.info("CorticalStack flushed successfully")
        print(f"  {Kleur.GROEN}✔ CorticalStack: Flushed{Kleur.RESET}")
    except Exception as e:
        logger.debug("CorticalStack flush: %s", e)

    # Close key manager async clients
    try:
        from danny_toolkit.core.key_manager import get_key_manager
        km = get_key_manager()
        await km.close_all_clients()
        logger.info("KeyManager clients closed")
        print(f"  {Kleur.GROEN}✔ KeyManager: Clients closed{Kleur.RESET}")
    except Exception as e:
        logger.debug("KeyManager close: %s", e)

    # Synapse: persist weights
    try:
        from danny_toolkit.brain.synapse import get_synapse
        synapse = get_synapse()
        synapse._safe_commit()
        synapse._auto_export()
        logger.info("Synapse weights persisted")
        print(f"  {Kleur.GROEN}✔ Synapse: Weights persisted{Kleur.RESET}")
    except Exception as e:
        logger.debug("Synapse persist: %s", e)

    logger.info("Omega returned to offline storage. Goodbye, Commander.")
    print(f"  {Kleur.MAGENTA}Omega returned to offline storage.{Kleur.RESET}\n")


# ═══════════════════════════════════════════════════════════════
#  MAIN ENTRY POINT
# ═══════════════════════════════════════════════════════════════

async def main() -> None:
    """Entry point: boot Omega, optionally launch FastAPI or CLI."""
    async with omega_lifespan() as engine:
        if engine is None:
            logger.error("SwarmEngine failed to deploy. Aborting.")
            return

        # Determine mode from CLI args
        mode = "cli"
        if len(sys.argv) > 1:
            if sys.argv[1] in ("--api", "--fastapi", "--server"):
                mode = "api"
            elif sys.argv[1] in ("--omega", "--core"):
                mode = "omega"

        if mode == "api":
            # Launch FastAPI server
            logger.info("Starting FastAPI Cockpit on port 8001...")
            proc = await asyncio.create_subprocess_exec(
                sys.executable, "fastapi_server.py",
                cwd=_ROOT_DIR,
            )
            await proc.wait()
        elif mode == "omega":
            # Launch Omega Core (main_omega)
            logger.info("Handing over to Omega Core...")
            proc = await asyncio.create_subprocess_exec(
                sys.executable, "-m", "danny_toolkit.main_omega",
                cwd=_ROOT_DIR,
            )
            await proc.wait()
        else:
            # Interactive CLI mode — run SwarmEngine directly
            logger.info("Entering interactive CLI mode...")
            print(f"{Kleur.CYAAN}Type a query to send to SwarmEngine.run(), or 'exit' to quit.{Kleur.RESET}\n")
            while True:
                try:
                    user_input = input(f"{Kleur.GROEN}[OMEGA] > {Kleur.RESET}").strip()
                except (EOFError, KeyboardInterrupt):
                    break

                if not user_input or user_input.lower() in ("exit", "quit", "stop"):
                    break

                try:
                    results = await engine.run(
                        user_input,
                        callback=lambda msg: print(f"  {Kleur.GEEL}{msg}{Kleur.RESET}"),
                    )
                    for r in results:
                        display = r.display_text or r.content
                        print(f"\n{Kleur.CYAAN}[{r.agent}]{Kleur.RESET} {display}\n")
                except Exception as e:
                    logger.error("SwarmEngine.run() failed: %s", e)
                    print(f"  {Kleur.ROOD}Error: {e}{Kleur.RESET}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Manual override detected. Terminating process.")
