"""
OMEGA COMMAND CENTER -- Live Terminal Dashboard

Real-time monitoring dashboard for the entire danny-toolkit ecosystem.
Uses Rich Live display with 1Hz auto-refresh.

Usage:
    python omega_command_center.py
"""

import io
import os
import sys
import time
import threading
from datetime import datetime
from pathlib import Path

# --- Windows UTF-8 fix ---
try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
except Exception:
    pass

# --- Ensure project root on sys.path ---
_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# --- Rich imports ---
from rich.console import Console, Group
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

# --- System monitoring ---
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

# --- GPU monitoring via pynvml ---
try:
    import pynvml
    pynvml.nvmlInit()
    _GPU_HANDLE = pynvml.nvmlDeviceGetHandleByIndex(0)
    HAS_GPU = True
except Exception:
    _GPU_HANDLE = None
    HAS_GPU = False

# --- Project imports (graceful degradation) ---
try:
    from danny_toolkit.core.config import Config
    HAS_CONFIG = True
except Exception:
    HAS_CONFIG = False

try:
    from danny_toolkit.brain.cortical_stack import get_cortical_stack
    HAS_CORTICAL = True
except Exception:
    HAS_CORTICAL = False

try:
    from danny_toolkit.core.neural_bus import get_bus
    HAS_BUS = True
except Exception:
    HAS_BUS = False

try:
    from danny_toolkit.core.key_manager import get_key_manager
    HAS_KEYS = True
except Exception:
    HAS_KEYS = False

try:
    from danny_toolkit.core.semantic_cache import get_semantic_cache
    HAS_SCACHE = True
except Exception:
    HAS_SCACHE = False

try:
    from swarm_engine import SwarmEngine as _SwarmEngine
    HAS_SWARM = True
except Exception:
    HAS_SWARM = False

try:
    from danny_toolkit.core.vector_store import VectorStore
    HAS_VSTORE = True
except Exception:
    HAS_VSTORE = False

try:
    from danny_toolkit.brain import __version__ as BRAIN_VERSION
except Exception:
    BRAIN_VERSION = "?.?.?"

# ------------------------------------------------------------------ #
# Constants                                                            #
# ------------------------------------------------------------------ #

BASE_DIR = Path(__file__).resolve().parent
DANNY_TOOLKIT = BASE_DIR / "danny_toolkit"
DATA_DIR = BASE_DIR / "data"
STARTUP_TIME = time.time()

OMEGA_LOGO = r"""[bold bright_cyan] ██████╗ ███╗   ███╗███████╗ ██████╗  █████╗
██╔═══██╗████╗ ████║██╔════╝██╔════╝ ██╔══██╗
██║   ██║██╔████╔██║█████╗  ██║  ███╗███████║
██║   ██║██║╚██╔╝██║██╔══╝  ██║   ██║██╔══██║
╚██████╔╝██║ ╚═╝ ██║███████╗╚██████╔╝██║  ██║
 ╚═════╝ ╚═╝     ╚═╝╚══════╝ ╚═════╝ ╚═╝  ╚═╝[/]"""

# Agent catalog: (name, role, style, status_type)
AGENT_CATALOG = [
    ("CentralBrain",      "Orchestrator",   "bold green",   "ready"),
    ("PrometheusBrain",   "17-Pillar",      "bold green",   "ready"),
    ("OmegaGovernor",     "Guardian",       "bold yellow",  "guardian"),
    ("TaskArbitrator",    "Auctioneer",     "bold green",   "ready"),
    ("Strategist",        "Planner",        "bold cyan",    "ready"),
    ("Artificer",         "Forge",          "bold cyan",    "ready"),
    ("VoidWalker",        "Research",       "bold cyan",    "ready"),
    ("Tribunal",          "Verifier",       "bold magenta", "verifier"),
    ("AdversarialTrib.",  "Skeptic-Judge",  "bold magenta", "verifier"),
    ("HallucinatieSchild","Anti-Halluc.",   "bold magenta", "verifier"),
    ("GhostWriter",       "Docstrings",    "bold blue",    "ready"),
    ("Dreamer",           "REM Cycle",     "dim",          "sleeper"),
    ("DevOpsDaemon",      "CI Loop",       "bold green",   "ready"),
    ("TheCortex",         "KnowledgeGraph","bold cyan",    "ready"),
    ("TheSynapse",        "Hebbian",       "bold cyan",    "ready"),
    ("ThePhantom",        "Anticipation",  "bold cyan",    "ready"),
    ("TheOracleEye",      "Predictor",     "bold blue",    "ready"),
    ("VirtualTwin",       "Sandbox",       "bold yellow",  "ready"),
    ("BlackBox",          "ImmuneMemory",  "bold magenta", "ready"),
    ("ShadowGovernance",  "Clone Zones",   "bold yellow",  "guardian"),
    ("WaakhuisMonitor",   "Health Score",  "bold green",   "watcher"),
    ("ConfigAuditor",     "Drift Detect",  "bold green",   "watcher"),
    ("ModelRegistry",     "Multi-Model",   "bold cyan",    "ready"),
]

FEATURE_LIST = [
    ("AgentFactory",      "18 swarm agents"),
    ("ModelRegistry",     "5+ providers"),
    ("RAG Pipeline",      "3-tier security"),
    ("Sovereign Gate",    "7 iron laws"),
    ("Brain CLI",         "5-layer cmd"),
    ("NeuralBus",         "40+ events"),
    ("PatchDay",          "version mgmt"),
    ("CorticalStack",     "episodic+semantic"),
    ("GhostWriter",       "AST auto-docs"),
    ("HallucinationShield","claim scoring"),
    ("Dreamer REM",       "overnight cycle"),
    ("SemanticCache",     "vector 256d"),
]

STATUS_MAP = {
    "ready":    ("READY",    "bold green"),
    "guardian":  ("ARMED",    "bold yellow"),
    "verifier": ("STANDBY",  "bold magenta"),
    "sleeper":  ("SLEEPING", "dim blue"),
    "sleeper_active": ("REM ACTIVE", "bold magenta"),
    "watcher":  ("WATCHING", "bold green"),
    "cooldown": ("COOLDOWN", "bold red"),
}


# ------------------------------------------------------------------ #
# Cached data store                                                    #
# ------------------------------------------------------------------ #

class DataCache:
    def __init__(self):
        self._cache = {}
        self._timestamps = {}

    def get(self, key: str, func, ttl: float = 10.0):
        now = time.time()
        if key in self._cache and (now - self._timestamps.get(key, 0)) < ttl:
            return self._cache[key]
        try:
            val = func()
        except Exception:
            val = self._cache.get(key)
        self._cache[key] = val
        self._timestamps[key] = now
        return val


_cache = DataCache()


# ------------------------------------------------------------------ #
# Data collection helpers                                              #
# ------------------------------------------------------------------ #

def _uptime() -> str:
    delta = int(time.time() - STARTUP_TIME)
    h, rem = divmod(delta, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def _count_modules(subdir: str) -> int:
    target = DANNY_TOOLKIT / subdir
    if not target.is_dir():
        return 0
    count = 0
    for root, _dirs, files in os.walk(target):
        if "__pycache__" in root:
            continue
        count += sum(1 for f in files if f.endswith(".py") and f != "__init__.py")
    return count


def _count_apps() -> int:
    apps_dir = DANNY_TOOLKIT / "apps"
    if not apps_dir.is_dir():
        return 0
    return sum(
        1 for f in apps_dir.iterdir()
        if f.suffix == ".py" and f.name not in ("__init__.py", "base_app.py")
    )


def _count_ai() -> int:
    ai_dir = DANNY_TOOLKIT / "ai"
    if not ai_dir.is_dir():
        return 0
    return sum(1 for f in ai_dir.iterdir() if f.suffix == ".py" and f.name != "__init__.py")


def _count_quests() -> int:
    q_dir = DANNY_TOOLKIT / "quests"
    if not q_dir.is_dir():
        return 0
    return sum(1 for f in q_dir.iterdir() if f.suffix == ".py" and f.name != "__init__.py")


def _count_skills() -> int:
    s_dir = DANNY_TOOLKIT / "skills"
    if not s_dir.is_dir():
        return 0
    return sum(
        1 for f in s_dir.rglob("*.py")
        if f.name != "__init__.py" and "__pycache__" not in str(f)
    )


def _get_ecosystem_counts() -> dict:
    return _cache.get("ecosystem", lambda: {
        "brain":    _count_modules("brain"),
        "core":     _count_modules("core"),
        "daemon":   _count_modules("daemon"),
        "agents":   _count_modules("agents"),
        "apps":     _count_apps(),
        "ai":       _count_ai(),
        "quests":   _count_quests(),
        "skills":   _count_skills(),
        "learning": _count_modules("learning"),
    }, ttl=30.0) or {}


def _get_cpu_ram() -> tuple:
    if not HAS_PSUTIL:
        return (0.0, 0.0, 0.0)
    cpu = psutil.cpu_percent(interval=0)
    mem = psutil.virtual_memory()
    return (cpu, mem.used / (1024**3), mem.total / (1024**3))


def _get_gpu_info() -> dict:
    """Get GPU utilization and VRAM via pynvml."""
    if not HAS_GPU:
        return {}
    try:
        info = pynvml.nvmlDeviceGetMemoryInfo(_GPU_HANDLE)
        util = pynvml.nvmlDeviceGetUtilizationRates(_GPU_HANDLE)
        name = pynvml.nvmlDeviceGetName(_GPU_HANDLE)
        if isinstance(name, bytes):
            name = name.decode("utf-8", errors="replace")
        # Shorten name
        name = name.replace("NVIDIA GeForce ", "")
        return {
            "name": name,
            "gpu_util": util.gpu,
            "vram_used_gb": info.used / (1024**3),
            "vram_total_gb": info.total / (1024**3),
        }
    except Exception:
        return {}


def _make_bar(value: float, max_val: float, width: int = 20, color: str = "green") -> Text:
    if max_val <= 0:
        frac = 0.0
    else:
        frac = min(value / max_val, 1.0)
    filled = int(frac * width)
    empty = width - filled

    if frac > 0.85:
        color = "red"
    elif frac > 0.65:
        color = "yellow"

    bar = Text()
    bar.append("\u2588" * filled, style=color)
    bar.append("\u2591" * empty, style="dim")
    return bar


def _get_provider_status() -> list:
    providers = []
    groq_count = 0
    key_names = ["", "USER", "VERIFY", "RESEARCH", "WALKER", "FORGE", "OVERNIGHT", "KNOWLEDGE"]
    if os.environ.get("GROQ_API_KEY") or os.environ.get("GROQ_API_KEY_USER"):
        groq_count += 1
    for name in key_names[2:]:
        if os.environ.get(f"GROQ_API_KEY_{name}"):
            groq_count += 1
    for i in range(1, 4):
        if os.environ.get(f"GROQ_API_KEY_RESERVE_{i}"):
            groq_count += 1
    providers.append((
        f"Groq ({groq_count}k)", groq_count, 10,
        "bold green" if groq_count > 0 else "dim red",
    ))
    checks = [
        ("Gemini",    ["GEMINI_API_KEY", "GOOGLE_API_KEY"]),
        ("NVIDIA NIM",["NVIDIA_NIM_API_KEY"]),
        ("Voyage",    ["VOYAGE_API_KEY"]),
        ("Anthropic", ["ANTHROPIC_API_KEY"]),
    ]
    for pname, env_keys in checks:
        has = any(os.environ.get(k) for k in env_keys)
        providers.append((pname, 5 if has else 0, 5, "bold green" if has else "dim red"))
    providers.append(("Ollama", 3, 5, "bold blue"))
    return providers


def _get_cortical_info() -> dict:
    if not HAS_CORTICAL:
        return {}
    return _cache.get("cortical", lambda: get_cortical_stack().get_stats(), ttl=5.0) or {}


def _get_bus_stats() -> dict:
    if not HAS_BUS:
        return {}
    try:
        return get_bus().statistieken()
    except Exception:
        return {}


def _get_bus_events(count: int = 6) -> list:
    if not HAS_BUS:
        return []
    try:
        bus = get_bus()
        stream = bus.get_context_stream(count=count)
        if stream:
            return stream.strip().split("\n")[:count]
    except Exception:
        pass
    return []


def _get_key_stats() -> dict:
    if not HAS_KEYS:
        return {}
    return _cache.get("key_stats", lambda: get_key_manager().get_status(), ttl=3.0) or {}


def _get_cooldown_agents() -> set:
    if not HAS_KEYS:
        return set()
    try:
        return get_key_manager().get_agents_in_cooldown()
    except Exception:
        return set()


def _get_chromadb_count() -> int:
    def _count():
        chroma_dir = DATA_DIR / "rag" / "chromadb"
        if not chroma_dir.is_dir():
            return 0
        return sum(1 for f in chroma_dir.rglob("*") if f.is_file())
    return _cache.get("chromadb_count", _count, ttl=30.0) or 0


def _get_data_size_mb() -> float:
    def _calc():
        return sum(f.stat().st_size for f in DATA_DIR.rglob("*") if f.is_file()) / (1024 * 1024)
    return _cache.get("data_size", _calc, ttl=30.0) or 0.0


def _get_db_size(filename: str) -> str:
    path = DATA_DIR / filename
    if not path.exists():
        return "N/A"
    size = path.stat().st_size
    if size >= 1024 * 1024:
        return f"{size / (1024 * 1024):.1f} MB"
    if size >= 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size} B"


def _get_semantic_cache_stats() -> dict:
    if not HAS_SCACHE:
        return {}
    return _cache.get("scache", lambda: get_semantic_cache().stats(), ttl=5.0) or {}


def _get_vector_store_stats() -> dict:
    if not HAS_VSTORE:
        return {}
    def _fetch():
        vs = VectorStore()
        return vs.statistieken()
    return _cache.get("vstore", _fetch, ttl=10.0) or {}


def _get_swarm_stats() -> dict:
    if not HAS_SWARM:
        return {}
    def _fetch():
        se = _SwarmEngine()
        return se.get_stats()
    return _cache.get("swarm", _fetch, ttl=5.0) or {}


def _get_api_status() -> str:
    """Check if FastAPI server is running on :8000."""
    import urllib.request
    def _check():
        try:
            req = urllib.request.Request("http://localhost:8000/docs", method="HEAD")
            urllib.request.urlopen(req, timeout=1)
            return "ONLINE"
        except Exception:
            return "OFFLINE"
    return _cache.get("api_status", _check, ttl=5.0) or "OFFLINE"


def _get_git_log(count: int = 5) -> list:
    import subprocess
    def _fetch():
        env = os.environ.copy()
        env["LC_ALL"] = "C.UTF-8"
        result = subprocess.run(
            ["git", "-c", "core.quotepath=false", "log", "--oneline",
             f"-{count}", "--no-color"],
            capture_output=True, cwd=str(BASE_DIR), timeout=3, env=env,
        )
        if result.returncode == 0:
            return result.stdout.decode("utf-8", errors="replace").strip().split("\n")
        return []
    return _cache.get(f"git_log_{count}", _fetch, ttl=15.0) or []


# ------------------------------------------------------------------ #
# Panel builders                                                       #
# ------------------------------------------------------------------ #

def build_header() -> Panel:
    cpu, ram_used, ram_total = _get_cpu_ram()
    gpu = _get_gpu_info()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    eco = _get_ecosystem_counts()
    total = sum(eco.values())

    # Left: identity
    left = Text()
    left.append("  \u03a9 OMEGA COMMAND CENTER", style="bold bright_cyan")
    left.append(f"  v{BRAIN_VERSION}\n", style="dim cyan")
    left.append(f"  {total} modules", style="bold white")
    left.append("  |  ", style="dim")
    left.append("SOVEREIGN", style="bold green")
    left.append(f"  |  {now}\n", style="dim")
    left.append(f"  Uptime: {_uptime()}", style="dim cyan")

    # Right: system bars (CPU, RAM, GPU, DSK)
    right = Text()
    right.append("CPU ", style="bold white")
    right.append_text(_make_bar(cpu, 100.0, 16))
    right.append(f" {cpu:5.1f}%\n", style="bold white")

    right.append("RAM ", style="bold white")
    right.append_text(_make_bar(ram_used, ram_total, 16))
    right.append(f" {ram_used:.1f}/{ram_total:.1f}G\n", style="bold white")

    if gpu:
        vu = gpu["vram_used_gb"]
        vt = gpu["vram_total_gb"]
        gu = gpu["gpu_util"]
        right.append("GPU ", style="bold bright_green")
        right.append_text(_make_bar(gu, 100.0, 16, "bright_green"))
        right.append(f" {gu}% {gpu['name']}\n", style="bold bright_green")
        right.append("VRM ", style="bold bright_green")
        right.append_text(_make_bar(vu, vt, 16, "bright_green"))
        right.append(f" {vu:.1f}/{vt:.1f}G", style="bold bright_green")
    elif HAS_PSUTIL:
        disk = psutil.disk_usage(str(BASE_DIR))
        du, dt = disk.used / (1024**3), disk.total / (1024**3)
        right.append("DSK ", style="bold white")
        right.append_text(_make_bar(du, dt, 16))
        right.append(f" {du:.0f}/{dt:.0f}G", style="bold white")

    grid = Table.grid(padding=(0, 3))
    grid.add_column(ratio=3)
    grid.add_column(ratio=2)
    grid.add_row(left, right)

    return Panel(grid, title="[bold bright_cyan]\u03a9 OMEGA COMMAND CENTER[/]",
                 border_style="bright_cyan", box=box.DOUBLE)


def build_providers() -> Panel:
    table = Table(show_header=False, box=None, padding=(0, 1), expand=True)
    table.add_column("Name", style="bold", min_width=12)
    table.add_column("Status", min_width=12)

    for name, val, max_val, style in _get_provider_status():
        full = min(val, max_val)
        blocks_on = "\u25a0" * full
        blocks_off = "\u25a1" * (max_val - full)
        status = Text()
        if val > 0:
            status.append(blocks_on, style="green")
            status.append(blocks_off, style="dim")
        else:
            status.append(blocks_on + blocks_off, style="dim red")
            status.append(" OFF", style="dim red")
        table.add_row(Text(name, style=style), status)

    ks = _get_key_stats()
    if ks:
        cd = ks.get("in_globale_cooldown", False)
        s = "bold red" if cd else "green"
        table.add_row(
            Text("Rate", style="dim"),
            Text(f"429s:{ks.get('globale_429s', 0)} CD:{'Y' if cd else 'N'}", style=s),
        )

    return Panel(table, title="[bold green]PROVIDERS[/]",
                 border_style="green", box=box.ROUNDED)


def build_agents() -> Panel:
    cooldown = _get_cooldown_agents()
    now_hour = datetime.now().hour

    rows = []
    for name, role, style, stype in AGENT_CATALOG:
        if name in cooldown:
            st_text, st_style = STATUS_MAP["cooldown"]
        elif stype == "sleeper" and 3 <= now_hour <= 5:
            st_text, st_style = STATUS_MAP["sleeper_active"]
        else:
            st_text, st_style = STATUS_MAP.get(stype, ("READY", "bold green"))
        rows.append((name, role, style, st_text, st_style))

    table = Table(show_header=True, box=None, padding=(0, 1), expand=True)
    table.add_column("Agent", style="bold", ratio=2)
    table.add_column("St", justify="right", ratio=1)
    table.add_column("\u2502", style="dim", width=1)
    table.add_column("Agent", style="bold", ratio=2)
    table.add_column("St", justify="right", ratio=1)

    mid = (len(rows) + 1) // 2
    left_col = rows[:mid]
    right_col = rows[mid:]

    for i in range(mid):
        ln, lr, ls, lst, lss = left_col[i]
        if i < len(right_col):
            rn, rr, rs, rst, rss = right_col[i]
            table.add_row(
                Text(ln, style=ls), Text(lst, style=lss),
                Text("\u2502", style="dim"),
                Text(rn, style=rs), Text(rst, style=rss),
            )
        else:
            table.add_row(
                Text(ln, style=ls), Text(lst, style=lss),
                Text("\u2502", style="dim"),
                Text(""), Text(""),
            )

    return Panel(table, title=f"[bold cyan]BRAIN AGENTS ({len(AGENT_CATALOG)})[/]",
                 border_style="cyan", box=box.ROUNDED)


def build_system_status() -> Panel:
    """Build the SYSTEM STATUS panel — Swarm, RAG, Vector, Cache, Services."""
    table = Table(show_header=False, box=None, padding=(0, 1), expand=True)
    table.add_column("System", style="bold", ratio=3)
    table.add_column("Status", justify="right", ratio=3)

    # --- Swarm Engine ---
    sw = _get_swarm_stats()
    if sw:
        agents = sw.get("active_agents", 0)
        queries = sw.get("queries_processed", 0)
        avg_ms = sw.get("avg_response_ms", 0)
        avg_str = f"{avg_ms:.0f}ms" if avg_ms > 0 else "idle"
        table.add_row(
            Text("SwarmEngine", style="bold bright_cyan"),
            Text(f"{agents} agents | {queries} queries | {avg_str}", style="white"),
        )
        # Swarm subsystems
        gov_blocks = sw.get("governor_blocks", 0)
        schild = sw.get("schild_blocks", 0)
        tribunal = sw.get("tribunal_verified", 0)
        t_warn = sw.get("tribunal_warnings", 0)
        synapse = sw.get("synapse_adjustments", 0)
        phantom = sw.get("phantom_predictions", 0)
        p_hits = sw.get("phantom_hits", 0)
        cortex_e = sw.get("cortex_enrichments", 0)
        table.add_row(
            Text("  Governor", style="dim"),
            Text(f"{gov_blocks} blocks | Schild: {schild}", style="dim white"),
        )
        table.add_row(
            Text("  Tribunal", style="dim"),
            Text(f"{tribunal} verified | {t_warn} warn", style="dim white"),
        )
        table.add_row(
            Text("  Synapse", style="dim"),
            Text(f"{synapse} adj | Cortex: {cortex_e}", style="dim white"),
        )
        table.add_row(
            Text("  Phantom", style="dim"),
            Text(f"{phantom} pred | {p_hits} hits", style="dim white"),
        )
        # Errors & resilience
        errs = sw.get("agent_errors", 0)
        timeouts = sw.get("agent_timeouts", 0)
        cb_trips = sw.get("circuit_breaker_trips", 0)
        retries = sw.get("error_retries_attempted", 0)
        r_ok = sw.get("error_retries_succeeded", 0)
        err_style = "bold red" if errs > 0 else "green"
        table.add_row(
            Text("  Errors", style="dim"),
            Text(f"{errs} err | {timeouts} timeout | {cb_trips} CB trips", style=err_style),
        )
        if retries > 0:
            table.add_row(
                Text("  Retries", style="dim"),
                Text(f"{retries} tried | {r_ok} ok", style="dim white"),
            )
        # Cache stats from swarm
        rc = sw.get("response_cache", {})
        sc_hits = sw.get("semantic_cache_hits", 0)
        sc_miss = sw.get("semantic_cache_misses", 0)
        ft = sw.get("fast_track_hits", 0)
        table.add_row(
            Text("  Cache", style="dim"),
            Text(f"resp:{rc.get('entries',0)} | sem:{sc_hits}h/{sc_miss}m | fast:{ft}", style="dim white"),
        )
    else:
        table.add_row(Text("SwarmEngine", style="dim"), Text("not loaded", style="dim"))

    # --- RAG / ChromaDB ---
    chroma = _get_chromadb_count()
    table.add_row(
        Text("ChromaDB RAG", style="bold magenta"),
        Text(f"{chroma} files | 3 shards", style="white"),
    )

    # --- SemanticCache ---
    sc = _get_semantic_cache_stats()
    if sc:
        entries = sc.get("total_entries", 0)
        hit_rate = sc.get("session_hit_rate", 0)
        db_kb = sc.get("db_size_kb", 0)
        table.add_row(
            Text("SemanticCache", style="bold green"),
            Text(f"{entries} entries | {hit_rate:.0f}% hit | {db_kb:.0f}KB", style="white"),
        )
    else:
        table.add_row(Text("SemanticCache", style="bold green"), Text("standby", style="dim"))

    # --- NeuralBus ---
    bus = _get_bus_stats()
    if bus:
        subs = bus.get("subscribers", 0)
        pub = bus.get("events_gepubliceerd", 0)
        errs = bus.get("fouten", 0)
        err_txt = f" | {errs} err" if errs else ""
        table.add_row(
            Text("NeuralBus", style="bold yellow"),
            Text(f"{subs} subs | {pub} events{err_txt}", style="white"),
        )

    # --- Services ---
    api = _get_api_status()
    api_style = "bold green" if api == "ONLINE" else "bold red"
    ollama_style = "bold green"
    try:
        import urllib.request
        urllib.request.urlopen("http://127.0.0.1:11434", timeout=1)
        ollama_status = "ONLINE"
    except Exception:
        ollama_status = "OFFLINE"
        ollama_style = "bold red"
    table.add_row(
        Text("Services", style="bold blue"),
        Text(f"API:{api}  Ollama:{ollama_status}", style=f"{api_style}"),
    )

    # --- GPU summary ---
    gpu = _get_gpu_info()
    if gpu:
        table.add_row(
            Text(f"GPU {gpu['name']}", style="bold bright_green"),
            Text(f"{gpu['vram_used_gb']:.1f}/{gpu['vram_total_gb']:.1f}G | {gpu['gpu_util']}%", style="white"),
        )

    return Panel(table, title="[bold bright_red]SYSTEM STATUS[/]",
                 border_style="bright_red", box=box.ROUNDED)


def build_ecosystem() -> Panel:
    eco = _get_ecosystem_counts()
    table = Table(show_header=False, box=None, padding=(0, 1), expand=True)
    table.add_column("Dir", style="bold cyan", ratio=2)
    table.add_column("Count", justify="right", ratio=2)

    unit_map = {
        "apps": "apps", "ai": "systems", "quests": "protocols",
        "skills": "skills",
    }
    display = [
        ("brain",    "bold cyan"),
        ("core",     "bold green"),
        ("daemon",   "bold yellow"),
        ("agents",   "bold blue"),
        ("apps",     "bold magenta"),
        ("ai",       "bold red"),
        ("quests",   "bold yellow"),
        ("skills",   "dim cyan"),
        ("learning", "dim green"),
    ]

    total = 0
    for name, style in display:
        count = eco.get(name, 0)
        total += count
        unit = unit_map.get(name, "modules")
        table.add_row(
            Text(f"/{name}/", style=style),
            Text(f"{count} {unit}", style="bold white"),
        )

    table.add_row(Text(""), Text(""))
    table.add_row(
        Text("TOTAL", style="bold bright_cyan"),
        Text(f"{total} components", style="bold bright_cyan"),
    )

    return Panel(table, title="[bold green]ECOSYSTEM[/]",
                 border_style="green", box=box.ROUNDED)


def build_events() -> Panel:
    bus_stats = _get_bus_stats()
    events = _get_bus_events(4)
    git_log = _get_git_log(4)

    lines = Text()

    if events:
        for ev in events:
            lines.append(f" \u25b8 {ev}\n", style="white")
    else:
        lines.append(" (awaiting events...)\n", style="dim")

    if git_log:
        lines.append("\n ")
        lines.append("Commits:\n", style="bold yellow")
        for c in git_log:
            lines.append(f"  {c}\n", style="dim yellow")

    return Panel(lines, title="[bold yellow]LIVE FEED[/]",
                 border_style="yellow", box=box.ROUNDED)


def build_memory() -> Panel:
    table = Table(show_header=False, box=None, padding=(0, 1), expand=True)
    table.add_column("Store", style="bold", ratio=3)
    table.add_column("Value", justify="right", ratio=2)

    cortical = _get_cortical_info()
    if cortical:
        table.add_row(
            Text("CorticalStack", style="bold cyan"),
            Text(f"{cortical.get('db_size_mb', 0):.1f} MB", style="bold white"),
        )
        table.add_row(
            Text("  episodic", style="dim"),
            Text(f"{cortical.get('episodic_events', 0):,}", style="white"),
        )
        table.add_row(
            Text("  semantic", style="dim"),
            Text(f"{cortical.get('semantic_facts', 0):,}", style="white"),
        )
        pending = cortical.get("pending_writes", 0)
        if pending:
            table.add_row(Text("  pending", style="dim yellow"), Text(str(pending), style="yellow"))
    else:
        table.add_row(Text("CorticalStack", style="dim"), Text(_get_db_size("cortical_stack.db")))

    table.add_row(Text("ChromaDB", style="bold magenta"), Text(f"{_get_chromadb_count()} files"))
    table.add_row(Text("Embeddings", style="bold blue"), Text(f"Voyage {os.environ.get('EMBEDDING_DIM', '256')}d"))
    table.add_row(Text("SemanticCache", style="bold green"), Text("Active", style="green"))
    table.add_row(Text("/data/ total", style="dim"), Text(f"{_get_data_size_mb():.0f} MB", style="bold white"))

    return Panel(table, title="[bold magenta]MEMORY[/]",
                 border_style="magenta", box=box.ROUNDED)


def build_features() -> Panel:
    table = Table(show_header=False, box=None, padding=(0, 1), expand=True)
    table.add_column("Feature", style="bold cyan", ratio=3)
    table.add_column("Info", ratio=3)

    for name, info in FEATURE_LIST:
        table.add_row(Text(name, style="bold"), Text(info, style="white"))

    table.add_row(Text(""), Text(""))
    table.add_row(Text("...30+ more", style="dim"), Text("SOVEREIGN CORE", style="bold bright_cyan"))

    return Panel(table, title="[bold blue]FEATURES[/]",
                 border_style="blue", box=box.ROUNDED)


def build_footer() -> Panel:
    now = datetime.now().strftime("%H:%M:%S")
    t = Text()
    t.append("  [q]", style="bold white")
    t.append(" Quit  ", style="dim")
    t.append("[r]", style="bold white")
    t.append(" Refresh  ", style="dim")
    t.append("  |  ", style="dim")
    t.append(f"Tick: {now}", style="dim cyan")
    t.append("  |  ", style="dim")
    t.append("GLORY TO THE SOVEREIGN CORE", style="bold bright_cyan")
    return Panel(t, border_style="dim cyan", box=box.HORIZONTALS)


# ------------------------------------------------------------------ #
# Layout assembly                                                      #
# ------------------------------------------------------------------ #

def build_dashboard() -> Layout:
    layout = Layout()

    layout.split_column(
        Layout(name="header", size=6),
        Layout(name="body"),
        Layout(name="footer", size=3),
    )

    # Body: 3 columns
    layout["body"].split_row(
        Layout(name="col_left", ratio=2),
        Layout(name="col_mid", ratio=2),
        Layout(name="col_right", ratio=3),
    )

    # Left column: providers + memory
    layout["col_left"].split_column(
        Layout(name="providers", ratio=2),
        Layout(name="memory", ratio=2),
    )

    # Middle column: ecosystem + features
    layout["col_mid"].split_column(
        Layout(name="ecosystem", ratio=2),
        Layout(name="features", ratio=2),
    )

    # Right column: agents + system_status + events
    layout["col_right"].split_column(
        Layout(name="agents", ratio=2),
        Layout(name="system_status", ratio=3),
        Layout(name="events", ratio=2),
    )

    # Fill
    layout["header"].update(build_header())
    layout["providers"].update(build_providers())
    layout["memory"].update(build_memory())
    layout["ecosystem"].update(build_ecosystem())
    layout["features"].update(build_features())
    layout["agents"].update(build_agents())
    layout["system_status"].update(build_system_status())
    layout["events"].update(build_events())
    layout["footer"].update(build_footer())

    return layout


# ------------------------------------------------------------------ #
# Keyboard listener (Windows msvcrt)                                   #
# ------------------------------------------------------------------ #

class KeyListener:
    def __init__(self):
        self.quit_requested = False
        self._thread = threading.Thread(target=self._listen, daemon=True)
        self._thread.start()

    def _listen(self):
        try:
            import msvcrt
            while not self.quit_requested:
                if msvcrt.kbhit():
                    ch = msvcrt.getch()
                    if ch in (b"q", b"Q", b"\x1b"):
                        self.quit_requested = True
                time.sleep(0.05)
        except ImportError:
            try:
                while not self.quit_requested:
                    time.sleep(0.5)
            except KeyboardInterrupt:
                self.quit_requested = True


# ------------------------------------------------------------------ #
# Entry point                                                          #
# ------------------------------------------------------------------ #

def main():
    console = Console()
    console.clear()

    console.print(OMEGA_LOGO)
    console.print("\n  [bold bright_cyan]COMMAND CENTER[/] initializing...\n", highlight=False)
    time.sleep(0.6)

    keys = KeyListener()

    try:
        with Live(build_dashboard(), console=console, refresh_per_second=1, screen=True) as live:
            while not keys.quit_requested:
                time.sleep(1)
                live.update(build_dashboard())
    except KeyboardInterrupt:
        pass
    finally:
        console.clear()
        console.print("\n  [bold bright_cyan]\u03a9 OMEGA COMMAND CENTER[/] [dim]-- session ended.[/]\n")
        if HAS_GPU:
            try:
                pynvml.nvmlShutdown()
            except Exception:
                pass


if __name__ == "__main__":
    main()
