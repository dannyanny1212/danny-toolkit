"""
OMEGA SOVEREIGN APP -- Native Desktop Dashboard v3.0
=====================================================

Standalone desktop applicatie (CustomTkinter + matplotlib).
10-tab neon dashboard met het volledige Omega ecosystem:

  Tab 1:  DASHBOARD    — 6-panel overzicht (Vanguard, Cortex, Pulse, Fuel, Omega Terminal, Listener)
  Tab 2:  AGENTS       — Per-agent health, circuit breakers, pipeline metrics, routing
  Tab 3:  BRAIN        — Cortex graph, Synapse pathways, Phantom predictions, Singularity
  Tab 4:  IMMUNE       — BlackBox antibodies, HallucinatieSchild, Governor, Tribunal
  Tab 5:  MEMORY       — CorticalStack events, DB metrics, semantic recall
  Tab 6:  OBSERVATORY  — Model leaderboard, auction history, provider health, cost analysis
  Tab 7:  TERMINAL     — Real subprocess shell (PowerShell/bash)
  Tab 8:  APPS         — 29 app buttons with status indicators, quick launch
  Tab 9:  MAINTENANCE  — Dreamer REM, DevOpsDaemon CI, GhostWriter, Shadow Governance
  Tab 10: PREDICTIONS  — OracleEye forecasts, Phantom predictions, trend data, TheMirror

Gebruik: python omega_sovereign_app.py
"""

import io
import os
import re
import sys
import math
import time
import logging
import threading
import subprocess
from datetime import datetime
from collections import deque
from contextlib import redirect_stdout
from dataclasses import dataclass
from typing import Callable

# UTF-8 voor Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

import tkinter as tk
import customtkinter as ctk
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np

logger = logging.getLogger(__name__)

# ── THEME ────────────────────────────────────────────────────────

BG_DEEP = "#0a0e17"
BG_PANEL = "#0d1220"
BG_CARD = "#111827"
BORDER = "#1e293b"
NEON_CYAN = "#00d4ff"
NEON_GREEN = "#00ff88"
NEON_ORANGE = "#ff6b35"
NEON_RED = "#ff3366"
NEON_PURPLE = "#a855f7"
NEON_YELLOW = "#facc15"
TEXT_PRIMARY = "#e0e6ed"
TEXT_DIM = "#64748b"

FONT_MONO = ("Consolas", 10)
FONT_MONO_SM = ("Consolas", 9)
FONT_MONO_XS = ("Consolas", 8)
FONT_TITLE = ("Consolas", 11, "bold")

plt.rcParams.update({
    "figure.facecolor": BG_PANEL, "axes.facecolor": BG_DEEP,
    "axes.edgecolor": BORDER, "axes.labelcolor": TEXT_DIM,
    "xtick.color": TEXT_DIM, "ytick.color": TEXT_DIM,
    "text.color": TEXT_PRIMARY, "grid.color": BORDER,
    "grid.alpha": 0.5, "font.family": "monospace", "font.size": 8,
})

# ── PANEL DESCRIPTOR ─────────────────────────────────────────────

@dataclass
class PanelDescriptor:
    """Registry entry for panels that can be added to the dashboard."""
    panel_id: str           # "agents.health"
    title: str              # "Agent Health Report"
    tab_origin: str         # "Agents"
    create_fn: Callable     # factory(parent) -> InfoPanel
    update_fn: Callable     # update(panel) -> refresh content


# ── SAFE IMPORTS ─────────────────────────────────────────────────

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

try:
    from danny_toolkit.core.config import Config
    HAS_CONFIG = True
except ImportError:
    HAS_CONFIG = False

try:
    from danny_toolkit.core.neural_bus import get_bus, EventTypes
    HAS_BUS = True
except ImportError:
    HAS_BUS = False

try:
    from danny_toolkit.core.key_manager import SmartKeyManager
    HAS_KEY_MANAGER = True
except ImportError:
    HAS_KEY_MANAGER = False

try:
    from danny_toolkit.brain.cortical_stack import get_cortical_stack
    HAS_CORTICAL = True
except ImportError:
    HAS_CORTICAL = False

try:
    from danny_toolkit.brain.waakhuis import get_waakhuis
    HAS_WAAKHUIS = True
except ImportError:
    HAS_WAAKHUIS = False

try:
    from danny_toolkit.brain.trinity_models import CosmicRole, NodeTier
    HAS_TRINITY = True
except ImportError:
    HAS_TRINITY = False

try:
    from danny_toolkit.brain.black_box import get_black_box
    HAS_BLACKBOX = True
except ImportError:
    HAS_BLACKBOX = False

try:
    from danny_toolkit.brain.hallucination_shield import get_hallucination_shield
    HAS_SCHILD = True
except ImportError:
    HAS_SCHILD = False

try:
    from danny_toolkit.brain.adversarial_tribunal import get_adversarial_tribunal
    HAS_TRIBUNAL = True
except ImportError:
    HAS_TRIBUNAL = False

try:
    from danny_toolkit.brain.model_sync import get_model_registry
    HAS_MODELS = True
except ImportError:
    HAS_MODELS = False

try:
    from danny_toolkit.brain.observatory_sync import get_observatory_sync
    HAS_OBSERVATORY = True
except ImportError:
    HAS_OBSERVATORY = False

try:
    from danny_toolkit.brain.introspector import get_introspector
    HAS_INTROSPECTOR = True
except ImportError:
    HAS_INTROSPECTOR = False

try:
    from danny_toolkit.daemon.limbic_system import LimbicSystem
    HAS_LIMBIC = True
except ImportError:
    HAS_LIMBIC = False

try:
    from danny_toolkit.brain.trinity_omega import PrometheusBrain
    HAS_PROMETHEUS = True
except ImportError:
    HAS_PROMETHEUS = False

try:
    from danny_toolkit.brain.arbitrator import get_arbitrator
    HAS_ARBITRATOR = True
except ImportError:
    HAS_ARBITRATOR = False


# ── REALTIME DATA CACHE (background thread fills, UI reads) ──────

class _DataCache:
    """Thread-safe cache — background fetcher writes, UI reads instantly."""

    def __init__(self):
        self._lock = threading.Lock()
        self._data = {}
        self._running = False
        self._thread = None

    def get(self, key, default=None):
        with self._lock:
            return self._data.get(key, default)

    def put(self, key, value):
        with self._lock:
            self._data[key] = value

    def start(self, interval=1.0):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, args=(interval,), daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False

    def _loop(self, interval):
        while self._running:
            t0 = time.time()
            try:
                self._fetch_all()
            except Exception as e:
                logger.debug("DataCache fetch error: %s", e)
            elapsed = time.time() - t0
            sleep_time = max(0.1, interval - elapsed)
            time.sleep(sleep_time)

    def _fetch_all(self):
        """Fetch all data sources in background — UI never blocks.

        Diamond Polish: every except logs to logger.debug (no silent pass).
        """
        # System metrics
        if HAS_PSUTIL:
            self.put("cpu", psutil.cpu_percent(interval=0.05))
            self.put("ram", psutil.virtual_memory().percent)

        # Engine stats
        eng_tuple = _load_engine()
        eng = eng_tuple[0] if eng_tuple else None
        if eng:
            try:
                self.put("engine_stats", eng.get_stats())
            except Exception as e:
                logger.debug("cache engine_stats: %s", e)
            try:
                self.put("swarm_metrics", dict(eng._swarm_metrics))
            except Exception as e:
                logger.debug("cache swarm_metrics: %s", e)

        # Waakhuis
        if HAS_WAAKHUIS:
            try:
                wh = get_waakhuis()
                self.put("waakhuis_rapport", wh.gezondheidsrapport())
                self.put("hardware_status", wh.hardware_status())
            except Exception as e:
                logger.debug("cache waakhuis: %s", e)

        # NeuralBus (public API only — no _lock/_history access)
        if HAS_BUS:
            try:
                bus = get_bus()
                self.put("bus_stats", bus.statistieken())
                self.put("bus_stream", bus.get_context_stream(count=15))
                type_counts = bus.get_event_type_counts()
                self.put("bus_event_counts", list(type_counts.values())[:20])
            except Exception as e:
                logger.debug("cache bus: %s", e)

        # CorticalStack
        if HAS_CORTICAL:
            try:
                stack = get_cortical_stack()
                self.put("cortical_events", stack.get_recent_events(count=25))
                self.put("cortical_db_metrics", stack.get_db_metrics())
                self.put("cortical_stats", stack.get_stats())
                self.put("cortical_facts", stack.recall_all())
            except Exception as e:
                logger.debug("cache cortical: %s", e)

        # BlackBox
        if HAS_BLACKBOX:
            try:
                bb = get_black_box()
                self.put("blackbox_stats", bb.get_stats())
                self.put("blackbox_antibodies", bb.get_antibodies())
            except Exception as e:
                logger.debug("cache blackbox: %s", e)

        # Shield
        if HAS_SCHILD:
            try:
                self.put("shield_stats", get_hallucination_shield().get_stats())
            except Exception as e:
                logger.debug("cache shield: %s", e)

        # Tribunal
        if HAS_TRIBUNAL:
            try:
                self.put("tribunal_stats", get_adversarial_tribunal().get_stats())
            except Exception as e:
                logger.debug("cache tribunal: %s", e)

        # Key Manager
        if HAS_KEY_MANAGER:
            try:
                km = SmartKeyManager()
                now = time.time()
                key_data = {"count": len(km._keys)}
                agents = {}
                with km._metrics_lock:
                    for name, a in km._agents.items():
                        rpm = sum(1 for ts in a.request_timestamps if now - ts < 60)
                        agents[name] = {
                            "req": a.totaal_requests, "tok": a.totaal_tokens,
                            "rpm": rpm, "429s": a.totaal_429s,
                            "tpm": a.tokens_deze_minuut,
                        }
                    key_data["agents"] = agents
                    key_data["rpm_total"] = sum(a["rpm"] for a in agents.values())
                    key_data["tpm_total"] = sum(a["tpm"] for a in agents.values())
                try:
                    key_data["cooldown"] = km.get_agents_in_cooldown()
                except Exception as e:
                    logger.debug("cache cooldown: %s", e)
                    key_data["cooldown"] = set()
                rpm_limit = getattr(km, 'RPM_LIMIT', 30) * max(1, len(km._keys))
                tpm_limit = getattr(km, 'TPM_LIMIT', 30000) * max(1, len(km._keys))
                key_data["rpm_limit"] = rpm_limit
                key_data["tpm_limit"] = tpm_limit
                self.put("key_data", key_data)
            except Exception as e:
                logger.debug("cache key_manager: %s", e)

        # Circuit breakers
        if eng:
            try:
                from swarm_engine import get_circuit_state
                self.put("circuit_state", get_circuit_state())
            except Exception as e:
                logger.debug("cache circuit: %s", e)

        # GPU
        try:
            from danny_toolkit.core.vram_manager import vram_rapport
            self.put("vram", vram_rapport())
        except Exception as e:
            logger.debug("cache vram: %s", e)

        # Model Registry
        if HAS_MODELS:
            try:
                reg = get_model_registry()
                self.put("model_stats", reg.get_stats())
                self.put("model_workers", reg.get_all_workers())
            except Exception as e:
                logger.debug("cache model_registry: %s", e)

        # Observatory
        if HAS_OBSERVATORY:
            try:
                obs = get_observatory_sync()
                self.put("leaderboard", obs.get_model_leaderboard())
                self.put("cost_analysis", obs.get_cost_analysis())
                self.put("auction_history", obs.get_auction_history())
                self.put("failure_analysis", obs.get_failure_analysis())
                self.put("trend_data", obs.get_trend_data())
            except Exception as e:
                logger.debug("cache observatory: %s", e)

        # Brain: Synapse
        try:
            if not hasattr(self, '_synapse'):
                from danny_toolkit.brain.synapse import TheSynapse
                self._synapse = TheSynapse()
            self.put("synapse_stats", self._synapse.get_stats())
            self.put("synapse_pathways", self._synapse.get_top_pathways(limit=10))
        except Exception as e:
            logger.debug("cache synapse: %s", e)

        # Brain: Phantom
        try:
            if not hasattr(self, '_phantom'):
                from danny_toolkit.brain.phantom import ThePhantom
                self._phantom = ThePhantom()
            self.put("phantom_accuracy", self._phantom.get_accuracy())
            self.put("phantom_predictions", self._phantom.get_predictions(max_results=5))
        except Exception as e:
            logger.debug("cache phantom: %s", e)

        # Brain: Singularity
        try:
            if not hasattr(self, '_singularity'):
                from danny_toolkit.brain.singularity import SingularityEngine
                self._singularity = SingularityEngine()
            self.put("singularity_status", self._singularity.get_status())
        except Exception as e:
            logger.debug("cache singularity: %s", e)

        # Brain: Introspector
        if HAS_INTROSPECTOR:
            try:
                self.put("introspector_report", get_introspector().get_health_report())
            except Exception as e:
                logger.debug("cache introspector: %s", e)

        # Immune: Governor
        try:
            if not hasattr(self, '_governor'):
                from danny_toolkit.brain.governor import OmegaGovernor
                self._governor = OmegaGovernor()
            self.put("governor_health", self._governor.get_health_report())
        except Exception as e:
            logger.debug("cache governor: %s", e)

        # Config Auditor
        try:
            from danny_toolkit.brain.config_auditor import get_config_auditor
            self.put("config_audit", get_config_auditor().audit())
        except Exception as e:
            logger.debug("cache config_audit: %s", e)

        # ── Phase 54: New cache keys for v3.0 tabs ──

        # Dreamer — last REM report
        try:
            if not hasattr(self, '_dreamer'):
                from danny_toolkit.brain.dreamer import Dreamer
                self._dreamer = Dreamer()
            dr = self._dreamer
            stats = {}
            if hasattr(dr, 'last_rem_report'):
                stats["last_rem"] = dr.last_rem_report
            if hasattr(dr, '_backup_ok'):
                stats["backup_ok"] = dr._backup_ok
            if hasattr(dr, '_last_cycle'):
                stats["last_cycle"] = dr._last_cycle
            stats["next_run"] = "04:00"
            self.put("dreamer_stats", stats)
        except Exception as e:
            logger.debug("cache dreamer: %s", e)

        # DevOpsDaemon — CI stats
        try:
            if not hasattr(self, '_devops'):
                from danny_toolkit.brain.devops_daemon import DevOpsDaemon
                self._devops = DevOpsDaemon()
            self.put("devops_stats", self._devops.get_stats())
        except Exception as e:
            logger.debug("cache devops: %s", e)

        # GhostWriter — token stats
        try:
            if not hasattr(self, '_ghost_writer'):
                from danny_toolkit.brain.ghost_writer import GhostWriter
                self._ghost_writer = GhostWriter()
            self.put("ghost_writer_stats", self._ghost_writer.get_token_stats())
        except Exception as e:
            logger.debug("cache ghost_writer: %s", e)

        # GhostAmplifier — amplification stats
        try:
            from danny_toolkit.brain.ghost_amplifier import get_ghost_amplifier
            self.put("ghost_amplifier_stats", get_ghost_amplifier().get_stats())
        except Exception as e:
            logger.debug("cache ghost_amplifier: %s", e)

        # ShadowGovernance — zone status
        try:
            if not hasattr(self, '_shadow_gov'):
                from danny_toolkit.brain.shadow_governance import ShadowGovernance
                self._shadow_gov = ShadowGovernance()
            self.put("shadow_status", self._shadow_gov.get_stats())
        except Exception as e:
            logger.debug("cache shadow: %s", e)

        # OracleEye — forecasts
        try:
            from danny_toolkit.brain.oracle_eye import get_oracle_eye
            oracle = get_oracle_eye()
            forecasts = oracle.forecast_next_hours(hours=4)
            self.put("oracle_predictions", [
                {"hour": f.hour, "cpu": f.cpu, "ram": f.ram, "queries": f.queries}
                for f in forecasts
            ] if forecasts else [])
            self.put("oracle_peaks", oracle.get_peak_hours())
        except Exception as e:
            logger.debug("cache oracle: %s", e)

        # TheMirror — user profile
        try:
            if not hasattr(self, '_mirror'):
                from danny_toolkit.brain.the_mirror import TheMirror
                self._mirror = TheMirror()
            self.put("mirror_profile", self._mirror.load_profile())
        except Exception as e:
            logger.debug("cache mirror: %s", e)


_cache = _DataCache()

# ── WAV-LOOP STATS (persistent across queries) ─────────────────
_wav_stats = {
    "queries": 0, "total_time": 0.0, "schild_blocks": 0,
    "schild_warns": 0, "v_scores": deque(maxlen=50),
}

# ── OMEGA MODE STATE ────────────────────────────────────────────
_omega_mode = {
    "active": False,
    "awakening": False,
    "engine": None,
    "arbitrator": None,
    "systems_ok": [],
    "systems_fail": [],
    "activated_at": None,
    "omega_queries": 0,
}

_omega_bus_seen = {}  # {event_hash: timestamp} — dedup window


def _omega_bus_publish(bus, event_type, data, bron="omega"):
    """Dedup NeuralBus publish — voorkomt duplicate events binnen 5s."""
    import hashlib
    import json as _json
    key = hashlib.md5(
        f"{event_type}:{_json.dumps(data, default=str, sort_keys=True)[:200]}".encode()
    ).hexdigest()
    now = time.time()
    for k in list(_omega_bus_seen):
        if now - _omega_bus_seen[k] > 5.0:
            del _omega_bus_seen[k]
    if key in _omega_bus_seen:
        return
    _omega_bus_seen[key] = now
    bus.publish(event_type, data, bron=bron)


# ── LAZY LOADERS ─────────────────────────────────────────────────

_engine_cache = None
_engine_lock = threading.Lock()

_brain_cache = None
_brain_lock = threading.Lock()


def _load_brain():
    global _brain_cache
    if _brain_cache is not None:
        return _brain_cache
    with _brain_lock:
        if _brain_cache is not None:
            return _brain_cache
        try:
            buf = io.StringIO()
            with redirect_stdout(buf):
                from danny_toolkit.brain.central_brain import CentralBrain
                _brain_cache = CentralBrain()
        except Exception as e:
            logger.debug("CentralBrain load fail: %s", e)
            _brain_cache = None
    return _brain_cache


def _load_engine():
    global _engine_cache
    if _engine_cache is not None:
        return _engine_cache
    with _engine_lock:
        if _engine_cache is not None:
            return _engine_cache
        try:
            buf = io.StringIO()
            with redirect_stdout(buf):
                from swarm_engine import SwarmEngine
                eng = SwarmEngine()
            _engine_cache = (eng, buf.getvalue())
        except Exception as e:
            logger.debug("SwarmEngine load fail: %s", e)
            _engine_cache = (None, str(e))
    return _engine_cache


def _safe(factory):
    """Call factory, return None on failure."""
    try:
        return factory()
    except Exception:
        return None


def _run_self_diagnostic():
    """Test alle brain componenten en return status dict."""
    results = {}

    # ── T1 TRINITY ──
    for name, path, cls in [
        ("PrometheusBrain", "danny_toolkit.brain.trinity_omega", "PrometheusBrain"),
        ("TaskArbitrator", "danny_toolkit.brain.arbitrator", "TaskArbitrator"),
        ("CorticalStack", "danny_toolkit.brain.cortical_stack", "get_cortical_stack"),
    ]:
        try:
            mod = __import__(path, fromlist=[cls])
            obj = getattr(mod, cls)
            if callable(obj) and cls.startswith("get_"):
                instance = obj()
            else:
                instance = obj
            results[name] = {"status": "OK", "type": type(instance).__name__}
        except Exception as e:
            results[name] = {"status": "FOUT", "error": str(e)[:100]}

    # ── T2 GUARDIANS ──
    for name, path, cls in [
        ("OmegaGovernor", "danny_toolkit.brain.governor", "OmegaGovernor"),
        ("HallucinatieSchild", "danny_toolkit.brain.hallucination_shield", "get_hallucination_shield"),
        ("AdversarialTribunal", "danny_toolkit.brain.adversarial_tribunal", "get_adversarial_tribunal"),
    ]:
        try:
            mod = __import__(path, fromlist=[cls])
            obj = getattr(mod, cls)
            instance = obj() if callable(obj) else obj
            results[name] = {"status": "OK"}
        except Exception as e:
            results[name] = {"status": "FOUT", "error": str(e)[:100]}

    # ── T3 SPECIALISTS ──
    for name, path, cls in [
        ("Strategist", "danny_toolkit.brain.strategist", "Strategist"),
        ("VoidWalker", "danny_toolkit.brain.void_walker", "VoidWalker"),
        ("Artificer", "danny_toolkit.brain.artificer", "Artificer"),
        ("Dreamer", "danny_toolkit.brain.dreamer", "Dreamer"),
        ("GhostWriter", "danny_toolkit.brain.ghost_writer", "GhostWriter"),
        ("GhostAmplifier", "danny_toolkit.brain.ghost_amplifier", "GhostAmplifier"),
    ]:
        try:
            mod = __import__(path, fromlist=[cls])
            getattr(mod, cls)
            results[name] = {"status": "OK"}
        except Exception as e:
            results[name] = {"status": "FOUT", "error": str(e)[:100]}

    # ── T4 INFRA ──
    for name, path, cls in [
        ("TheSynapse", "danny_toolkit.brain.synapse", "TheSynapse"),
        ("ThePhantom", "danny_toolkit.brain.phantom", "ThePhantom"),
        ("OracleEye", "danny_toolkit.brain.oracle_eye", "TheOracleEye"),
        ("DevOpsDaemon", "danny_toolkit.brain.devops_daemon", "DevOpsDaemon"),
        ("ModelRegistry", "danny_toolkit.brain.model_sync", "get_model_registry"),
        ("WaakhuisMonitor", "danny_toolkit.brain.waakhuis", "get_waakhuis"),
        ("TheMirror", "danny_toolkit.brain.the_mirror", "TheMirror"),
    ]:
        try:
            mod = __import__(path, fromlist=[cls])
            obj = getattr(mod, cls)
            if callable(obj) and cls.startswith("get_"):
                instance = obj()
            results[name] = {"status": "OK"}
        except Exception as e:
            results[name] = {"status": "FOUT", "error": str(e)[:100]}

    # ── T5 SINGULARITY ──
    try:
        from danny_toolkit.brain.singularity import SingularityEngine
        results["SingularityEngine"] = {"status": "OK"}
    except Exception as e:
        results["SingularityEngine"] = {"status": "FOUT", "error": str(e)[:100]}

    # ── CORE INFRA ──
    for name, path, cls in [
        ("SwarmEngine", "swarm_engine", "SwarmEngine"),
        ("NeuralBus", "danny_toolkit.core.neural_bus", "get_bus"),
        ("BlackBox", "danny_toolkit.brain.black_box", "get_black_box"),
        ("ConfigAuditor", "danny_toolkit.brain.config_auditor", "get_config_auditor"),
        ("UnifiedMemory", "danny_toolkit.brain.unified_memory", "UnifiedMemory"),
    ]:
        try:
            mod = __import__(path, fromlist=[cls])
            obj = getattr(mod, cls)
            if callable(obj) and cls.startswith("get_"):
                obj()
            results[name] = {"status": "OK"}
        except Exception as e:
            results[name] = {"status": "FOUT", "error": str(e)[:100]}

    # ── OLLAMA (GPU) ──
    try:
        import urllib.request
        resp = urllib.request.urlopen("http://localhost:11434/api/tags", timeout=3)
        import json as _json
        models = _json.loads(resp.read()).get("models", [])
        results["Ollama"] = {"status": "OK", "models": [m["name"] for m in models]}
    except Exception as e:
        results["Ollama"] = {"status": "FOUT", "error": str(e)[:100]}

    # ── GROQ API ──
    try:
        from danny_toolkit.core.config import Config
        key = Config.GROQ_API_KEY
        results["Groq API"] = {"status": "OK" if key else "FOUT", "key_set": bool(key)}
    except Exception as e:
        results["Groq API"] = {"status": "FOUT", "error": str(e)[:100]}

    # Samenvatting
    ok = sum(1 for v in results.values() if v["status"] == "OK")
    fout = sum(1 for v in results.values() if v["status"] == "FOUT")
    results["_samenvatting"] = {"totaal": len(results), "ok": ok, "fout": fout}

    # ── Schrijf naar logbestand ──
    try:
        from danny_toolkit.core.config import Config
        log_dir = Config.DATA_DIR / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "diagnostic.log"

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        lines = [f"\n{'='*60}", f"SELF-DIAGNOSTIC  {timestamp}", f"{'='*60}"]
        lines.append(f"Resultaat: {ok}/{ok + fout} OK, {fout} FOUT\n")

        for comp, info in sorted(results.items()):
            if comp.startswith("_"):
                continue
            status = info.get("status", "?")
            mark = "[OK]  " if status == "OK" else "[FOUT]"
            line = f"  {mark} {comp}"
            err = info.get("error", "")
            if err:
                line += f" — {err}"
            extra = {k: v for k, v in info.items() if k not in ("status", "error")}
            if extra:
                line += f"  {extra}"
            lines.append(line)

        lines.append("")

        with open(log_file, "a", encoding="utf-8") as f:
            f.write("\n".join(lines))

        logger.info("Diagnostic log written to %s", log_file)
    except Exception as e:
        logger.warning("Failed to write diagnostic log: %s", e)

    return results


_DIAGNOSTIC_KEYWORDS = [
    "diagnose", "diagnostic", "zelftest", "self-test", "health check",
    "wat werkt", "welke functies", "niet werkend", "kapot", "stuk",
    "system check", "status check", "controleer systeem", "check jezelf",
    "welke modules", "wat is stuk", "wat werkt niet", "systeem status",
]


def _ollama_verify(prompt, timeout=45):
    """Verify via local Ollama — zero latency, no rate limits.
    Tries gemma3:4b first, falls back to llava:latest."""
    import json
    import urllib.request
    for model in ("gemma3:4b", "llava:latest"):
        try:
            url = "http://localhost:11434/api/generate"
            data = json.dumps({
                "model": model,
                "prompt": prompt,
                "stream": False,
                "keep_alive": "10m",
                "options": {"num_predict": 20},
            }).encode()
            req = urllib.request.Request(url, data, {"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                result = json.loads(resp.read()).get("response", "")
                if result and result.strip():
                    return result
        except Exception as e:
            logger.warning("Ollama verify failed (%s): %s", model, e)
            continue
    return None


# ── HELPER: chart in tk.Frame (avoid CTk _canvas conflict) ──────

def _make_chart(parent, figsize=(4, 3), **subplot_kw):
    """Create fig, ax, host_frame, mpl_canvas — safe for CTk."""
    fig, ax = plt.subplots(figsize=figsize, **subplot_kw)
    host = tk.Frame(parent, bg=BG_PANEL)
    host.pack(fill="both", expand=True)
    canvas = FigureCanvasTkAgg(fig, host)
    canvas.get_tk_widget().pack(fill="both", expand=True)
    return fig, ax, canvas


# ── NEON PANEL BASE ──────────────────────────────────────────────

class NeonPanel(ctk.CTkFrame):
    def __init__(self, master, title, dockable=True, **kw):
        super().__init__(master, fg_color=BG_PANEL, border_color=BORDER,
                         border_width=1, corner_radius=8, **kw)
        self._title = title
        self._float_window = None
        self._original_info = None

        # Title bar with optional float button
        title_bar = ctk.CTkFrame(self, fg_color="transparent", height=24)
        title_bar.pack(fill="x", padx=8, pady=(6, 2))
        ctk.CTkLabel(title_bar, text=f"  {title.upper()}",
                      font=("Consolas", 10, "bold"),
                      text_color=NEON_CYAN, anchor="w"
                      ).pack(side="left", fill="x", expand=True)
        if dockable:
            self._float_btn = ctk.CTkButton(
                title_bar, text="\u2197", width=24, height=20,
                font=("Consolas", 12), fg_color="transparent",
                hover_color=BG_CARD, text_color=TEXT_DIM,
                command=self._toggle_float)
            self._float_btn.pack(side="right")

        ctk.CTkFrame(self, height=1, fg_color=BORDER).pack(fill="x", padx=8, pady=(0, 4))
        self.content = ctk.CTkFrame(self, fg_color="transparent")
        self.content.pack(fill="both", expand=True, padx=4, pady=(0, 4))

    def _toggle_float(self):
        if self._float_window:
            self._dock_back()
        else:
            self._float_out()

    def _float_out(self):
        parent = self.master
        # Determine current geometry manager and save info
        if isinstance(parent, tk.PanedWindow):
            panes = list(parent.panes())
            idx = panes.index(str(self)) if str(self) in panes else -1
            self._original_info = ('pane', parent, idx)
            parent.forget(self)
        else:
            try:
                info = self.grid_info()
                if info:
                    self._original_info = ('grid', {k: v for k, v in info.items() if k != 'in'})
                    self.grid_forget()
                else:
                    raise tk.TclError("empty")
            except tk.TclError:
                try:
                    info = self.pack_info()
                    self._original_info = ('pack', {k: v for k, v in info.items() if k != 'in'})
                    self.pack_forget()
                except tk.TclError:
                    return

        # Turn frame into standalone window via Tk wm manage
        self.tk.call('wm', 'manage', self._w)
        self.tk.call('wm', 'title', self._w, self._title)
        self.tk.call('wm', 'geometry', self._w, '500x350')
        self.tk.call('wm', 'minsize', self._w, '200', '150')
        self._dock_back_tcl = self.register(self._dock_back)
        self.tk.call('wm', 'protocol', self._w, 'WM_DELETE_WINDOW', self._dock_back_tcl)
        self._float_window = True
        self._float_btn.configure(text="\u2199")

    def _dock_back(self):
        if not self._float_window:
            return
        # Revert to normal frame
        self.tk.call('wm', 'forget', self._w)
        self._float_window = None
        if self._original_info:
            method = self._original_info[0]
            if method == 'pane':
                _, paned, idx = self._original_info
                paned.add(self, minsize=60)
            elif method == 'grid':
                self.grid(**self._original_info[1])
            else:
                self.pack(**self._original_info[1])
            self._original_info = None
        self._float_btn.configure(text="\u2197")


# ── SCROLLABLE TEXT PANEL ────────────────────────────────────────

class InfoPanel(NeonPanel):
    """Panel met scrollable text output."""
    def __init__(self, master, title):
        super().__init__(master, title)
        self._text = ctk.CTkTextbox(
            self.content, fg_color="#050810", text_color=NEON_GREEN,
            font=FONT_MONO_SM, border_color=BORDER, border_width=1,
            corner_radius=4, wrap="word", state="disabled",
        )
        self._text.pack(fill="both", expand=True)

    def clear(self):
        self._text.configure(state="normal")
        self._text.delete("1.0", "end")
        self._text.configure(state="disabled")

    def write(self, text, color=None):
        self._text.configure(state="normal")
        self._text.insert("end", text + "\n")
        self._text.see("end")
        self._text.configure(state="disabled")

    def write_lines(self, lines):
        self._text.configure(state="normal")
        for line in lines:
            self._text.insert("end", line + "\n")
        self._text.see("end")
        self._text.configure(state="disabled")


# ╔══════════════════════════════════════════════════════════════════╗
# ║  TAB 1: DASHBOARD (original 6 panels)                          ║
# ╚══════════════════════════════════════════════════════════════════╝

class DashboardTab(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self._extra_panels = []  # (panel, update_fn) tuples from panel picker
        # Dirty-flag cache for chart optimization
        self._prev_fuel_pct = None
        self._prev_listener_counts = None

        # ── Outer horizontal paned: left | center | right ──
        outer = tk.PanedWindow(self, orient=tk.HORIZONTAL, sashwidth=5,
                               sashrelief=tk.FLAT, bg=BG_DEEP,
                               opaqueresize=True, borderwidth=0)
        outer.pack(fill="both", expand=True)
        self._outer_paned = outer

        # Left: Vanguard (full height)
        self.vanguard = self._build_vanguard(outer)
        outer.add(self.vanguard, minsize=60, width=280)

        # Center: Cortex + Terminal (vertical split)
        center = tk.PanedWindow(outer, orient=tk.VERTICAL, sashwidth=5,
                                sashrelief=tk.FLAT, bg=BG_DEEP,
                                opaqueresize=True, borderwidth=0)
        outer.add(center, minsize=60, width=550)
        self._center_paned = center

        self.cortex_panel = NeonPanel(center, "\U0001f9e0 Cortex Knowledge Core")
        center.add(self.cortex_panel, minsize=60, height=300)
        self._cortex_fig, self._cortex_ax, self._cortex_cv = _make_chart(
            self.cortex_panel.content, figsize=(5, 3))
        self._draw_cortex()

        self.omega_term = self._build_omega_terminal(center)
        center.add(self.omega_term, minsize=60, height=350)

        # Right: Pulse + Fuel + Listener + mini panels (vertical split)
        right = tk.PanedWindow(outer, orient=tk.VERTICAL, sashwidth=5,
                               sashrelief=tk.FLAT, bg=BG_DEEP,
                               opaqueresize=True, borderwidth=0)
        outer.add(right, minsize=60, width=320)
        self._right_paned = right

        # Pulse Protocol
        self.pulse_panel = NeonPanel(right, "\u2764 Pulse Protocol")
        right.add(self.pulse_panel, minsize=60)
        self._pulse_fig, self._pulse_ax, self._pulse_cv = _make_chart(
            self.pulse_panel.content, figsize=(3.2, 1.2))
        self._pulse_samples = deque(maxlen=60)
        self._pulse_metrics = ctk.CTkFrame(self.pulse_panel.content, fg_color="transparent")
        self._pulse_metrics.pack(fill="x", padx=4)
        self._cpu_lbl = ctk.CTkLabel(self._pulse_metrics, text="CPU: --%",
                                      font=FONT_MONO_XS, text_color=NEON_GREEN)
        self._cpu_lbl.pack(side="left", padx=4)
        self._ram_lbl = ctk.CTkLabel(self._pulse_metrics, text="RAM: --%",
                                      font=FONT_MONO_XS, text_color=NEON_CYAN)
        self._ram_lbl.pack(side="right", padx=4)

        # API Fuel Gauge
        self.fuel_panel = NeonPanel(right, "\u26fd API Fuel Gauge")
        right.add(self.fuel_panel, minsize=60)
        self._fuel_fig, self._fuel_ax, self._fuel_cv = _make_chart(
            self.fuel_panel.content, figsize=(3.2, 1.4),
            subplot_kw={"projection": "polar"})
        self._fuel_metrics = ctk.CTkFrame(self.fuel_panel.content, fg_color="transparent")
        self._fuel_metrics.pack(fill="x", padx=4)
        self._rpm_lbl = ctk.CTkLabel(self._fuel_metrics, text="RPM: 0/30",
                                      font=FONT_MONO_XS, text_color=NEON_CYAN)
        self._rpm_lbl.pack(side="left", padx=4)
        self._tpm_lbl = ctk.CTkLabel(self._fuel_metrics, text="TPM: 0/30K",
                                      font=FONT_MONO_XS, text_color=NEON_CYAN)
        self._tpm_lbl.pack(side="right", padx=4)

        # The Listener
        self.listener_panel = NeonPanel(right, "\U0001f3a7 The Listener")
        right.add(self.listener_panel, minsize=60)
        self._list_fig, self._list_ax, self._list_cv = _make_chart(
            self.listener_panel.content, figsize=(3.2, 1.0))
        self._list_metrics = ctk.CTkFrame(self.listener_panel.content, fg_color="transparent")
        self._list_metrics.pack(fill="x", padx=4)
        self._ev_lbl = ctk.CTkLabel(self._list_metrics, text="Events: 0",
                                     font=FONT_MONO_XS, text_color=NEON_CYAN)
        self._ev_lbl.pack(side="left", padx=4)
        self._sub_lbl = ctk.CTkLabel(self._list_metrics, text="Subs: 0",
                                      font=FONT_MONO_XS, text_color=NEON_CYAN)
        self._sub_lbl.pack(side="right", padx=4)

        # Mini panels
        self._mini_events = InfoPanel(right, "\U0001f4dc Recent Events")
        right.add(self._mini_events, minsize=60)

        self._mini_circuits = InfoPanel(right, "\u26a1 Circuit Breakers")
        right.add(self._mini_circuits, minsize=60)

        self._mini_immune = InfoPanel(right, "\U0001f6e1 Immune Status")
        right.add(self._mini_immune, minsize=60)

        # ── Panel picker "+" button (top-right corner) ──
        self._add_btn = ctk.CTkButton(
            self, text="+", width=28, height=28,
            font=("Consolas", 16, "bold"), fg_color=BG_CARD,
            hover_color="#1a3a5c", text_color=NEON_CYAN, corner_radius=14,
            command=self._show_panel_picker)
        self._add_btn.place(relx=1.0, rely=0.0, x=-36, y=4, anchor="ne")

    def _show_panel_picker(self):
        """Show popup menu to add panels from other tabs."""
        app = self.winfo_toplevel()
        if not hasattr(app, '_panel_registry') or not app._panel_registry:
            return
        menu = tk.Menu(self, tearoff=0, bg=BG_CARD, fg=TEXT_PRIMARY,
                       activebackground="#1a3a5c", activeforeground=NEON_CYAN,
                       font=FONT_MONO_SM)
        by_tab = {}
        for desc in app._panel_registry:
            by_tab.setdefault(desc.tab_origin, []).append(desc)
        for tab_name, descriptors in sorted(by_tab.items()):
            sub = tk.Menu(menu, tearoff=0, bg=BG_CARD, fg=TEXT_PRIMARY,
                          activebackground="#1a3a5c", activeforeground=NEON_CYAN,
                          font=FONT_MONO_SM)
            for desc in descriptors:
                sub.add_command(
                    label=desc.title,
                    command=lambda d=desc: self._add_panel_from_registry(d))
            menu.add_cascade(label=tab_name, menu=sub)
        x = self._add_btn.winfo_rootx()
        y = self._add_btn.winfo_rooty() + self._add_btn.winfo_height()
        menu.tk_popup(x, y)

    def _add_panel_from_registry(self, desc):
        """Add a new panel instance from the registry to the right paned."""
        panel = desc.create_fn(self._right_paned)
        self._right_paned.add(panel, minsize=60)
        self._extra_panels.append((panel, desc.update_fn))

    # ── Vanguard ──
    def _build_vanguard(self, parent):
        panel = NeonPanel(parent, "\u269b Vanguard Status")
        self._vang_fig, self._vang_ax, self._vang_cv = _make_chart(
            panel.content, figsize=(3.2, 3.2))
        return panel

    def update_vanguard(self):
        ax = self._vang_ax
        ax.clear()
        data = []
        eng = _load_engine()[0]
        rapport = _cache.get("waakhuis_rapport", {})
        if eng and hasattr(eng, "agents"):
            for name in eng.agents:
                h, s = 100, "ok"
                info = rapport.get("agents", {}).get(name, {})
                if info:
                    h = info.get("score", 100)
                    s = "dead" if h < 30 else ("warn" if h < 70 else "ok")
                data.append((name, h, s))
        if not data:
            data = [("NO_LIVE_DATA", 0, "dead")]
        data.sort(key=lambda x: x[1])
        colors = [NEON_RED if s == "dead" else (NEON_ORANGE if s == "warn" else NEON_GREEN)
                  for _, _, s in data]
        ax.barh([d[0] for d in data], [d[1] for d in data],
                color=colors, height=0.6, edgecolor=colors, linewidth=0.5)
        for i, (_, h, _) in enumerate(data):
            if h > 10:
                ax.text(h - 2, i, f"{h}%", va="center", ha="right",
                        fontsize=7, color=BG_DEEP, fontweight="bold")
        ax.set_xlim(0, 105)
        ax.set_xlabel("Health %", fontsize=8)
        ax.tick_params(axis="y", labelsize=6)
        ax.grid(axis="x", alpha=0.3)
        self._vang_fig.tight_layout(pad=0.5)
        self._vang_cv.draw_idle()

    # ── Omega Terminal (command dispatch) ──

    # Terminal kleur-tags
    _OT_COLORS = {
        "input":   "#ffffff",      # Wit — user input
        "output":  NEON_GREEN,     # Groen — normaal antwoord
        "error":   NEON_RED,       # Rood — fouten
        "process": NEON_ORANGE,    # Oranje — verwerken/bezig
        "tool":    NEON_CYAN,      # Cyaan — tool calls, debug
        "dim":     TEXT_DIM,       # Grijs — stats, metadata
        "system":  NEON_CYAN,      # Cyaan — systeem info
        "warn":    NEON_YELLOW,    # Geel — waarschuwingen
        "verify":  NEON_PURPLE,    # Paars — verificatie
    }

    def _build_omega_terminal(self, parent):
        # Horizontal PanedWindow holding Omega (left) + Claude (right)
        terminal_row = tk.PanedWindow(parent, orient=tk.HORIZONTAL, sashwidth=5,
                                      sashrelief=tk.FLAT, bg=BG_DEEP,
                                      opaqueresize=True, borderwidth=0)

        # ── LEFT: Omega Brain Terminal ──
        omega_panel = NeonPanel(terminal_row, "\u2126 Omega Brain")
        self._ot_text = ctk.CTkTextbox(
            omega_panel.content, fg_color="#050810", text_color=NEON_GREEN,
            font=FONT_MONO_SM, border_color=BORDER, border_width=1,
            corner_radius=4, wrap="word", state="disabled")
        self._ot_text.pack(fill="both", expand=True, padx=4, pady=(0, 4))
        for tag_name, color in self._OT_COLORS.items():
            self._ot_text._textbox.tag_configure(tag_name, foreground=color)

        self._ot_write("\u2126 OMEGA BRAIN \u2014 Direct Link", "system")
        self._ot_write("Commands: status, agents, health, metrics, bus, events, keys,", "dim")
        self._ot_write("          cortical, apps, brain, immune, rag, diag, vram,", "dim")
        self._ot_write("          config, uptime, clear, help  |\u2191\u2193 history", "dim")
        self._ot_write("Default: typ een vraag \u2192 Omega Brain (WAV-Loop)\n", "dim")

        ot_inp = ctk.CTkFrame(omega_panel.content, fg_color="transparent")
        ot_inp.pack(fill="x", padx=4, pady=(0, 2))
        ctk.CTkLabel(ot_inp, text="\u2126 >", font=("Consolas", 11, "bold"),
                      text_color=NEON_CYAN).pack(side="left", padx=(4, 4))
        self._ot_entry = ctk.CTkEntry(
            ot_inp, fg_color=BG_CARD, text_color="#ffffff",
            font=FONT_MONO_SM, border_color=BORDER, border_width=1,
            placeholder_text="System command or brain question...",
            placeholder_text_color=TEXT_DIM)
        self._ot_entry.pack(side="left", fill="x", expand=True, padx=(0, 4))
        self._ot_entry.bind("<Return>", self._ot_on_enter)
        self._ot_history = deque(maxlen=100)
        self._ot_hist_idx = -1
        self._ot_entry.bind("<Up>", self._ot_hist_up)
        self._ot_entry.bind("<Down>", self._ot_hist_down)
        terminal_row.add(omega_panel, minsize=60, width=275)

        # ── RIGHT: Claude Code Terminal ──
        claude_panel = NeonPanel(terminal_row, "\U0001f916 Claude Code")
        self._ct_text = ctk.CTkTextbox(
            claude_panel.content, fg_color="#050810", text_color=NEON_GREEN,
            font=FONT_MONO_SM, border_color=BORDER, border_width=1,
            corner_radius=4, wrap="word", state="disabled")
        self._ct_text.pack(fill="both", expand=True, padx=4, pady=(0, 4))
        for tag_name, color in self._OT_COLORS.items():
            self._ct_text._textbox.tag_configure(tag_name, foreground=color)

        self._ct_write("\U0001f916 CLAUDE CODE \u2014 venv311 (Python 3.11.9)", "system")
        self._ct_write("cwd: C:\\Users\\danny\\danny-toolkit", "dim")
        self._ct_write("Commands: new, clear, login, apikey sk-...  |\u2191\u2193 history", "dim")
        self._ct_write("Default: typ een vraag \u2192 Claude Code CLI\n", "dim")
        self._claude_has_session = False

        ct_inp = ctk.CTkFrame(claude_panel.content, fg_color="transparent")
        ct_inp.pack(fill="x", padx=4, pady=(0, 2))
        ctk.CTkLabel(ct_inp, text="\U0001f916 >", font=("Consolas", 11, "bold"),
                      text_color=NEON_PURPLE).pack(side="left", padx=(4, 4))
        self._ct_entry = ctk.CTkEntry(
            ct_inp, fg_color=BG_CARD, text_color="#ffffff",
            font=FONT_MONO_SM, border_color=BORDER, border_width=1,
            placeholder_text="Ask Claude anything...",
            placeholder_text_color=TEXT_DIM)
        self._ct_entry.pack(side="left", fill="x", expand=True, padx=(0, 4))
        self._ct_entry.bind("<Return>", self._ct_on_enter)
        self._ct_history = deque(maxlen=100)
        self._ct_hist_idx = -1
        self._ct_entry.bind("<Up>", self._ct_hist_up)
        self._ct_entry.bind("<Down>", self._ct_hist_down)
        terminal_row.add(claude_panel, minsize=60, width=275)

        return terminal_row

    def _ot_write(self, text, tag="output"):
        """Schrijf tekst naar Omega Terminal met kleur-tag.

        Tags: input, output, error, process, tool, dim, system, warn, verify
        """
        self._ot_text.configure(state="normal")
        self._ot_text._textbox.insert("end", text + "\n", tag)
        self._ot_text.see("end")
        self._ot_text.configure(state="disabled")

    def _ct_write(self, text, tag="output"):
        """Schrijf tekst naar Claude Terminal met kleur-tag."""
        self._ct_text.configure(state="normal")
        self._ct_text._textbox.insert("end", text + "\n", tag)
        self._ct_text.see("end")
        self._ct_text.configure(state="disabled")

    def _ot_write_captured(self, line):
        """Schrijf een captured stdout regel met automatische kleurdetectie.

        Strips ANSI codes en kiest kleur op basis van inhoud.
        """
        import re
        clean = re.sub(r'\x1b\[[0-9;]*m', '', line).strip()
        if not clean:
            return
        if "[ERROR]" in clean or "[CRASH]" in clean:
            self._ot_write(f"  {clean}", "error")
        elif "[TOOL]" in clean or "[PREFETCH]" in clean:
            self._ot_write(f"  {clean}", "tool")
        elif "[FALLBACK]" in clean or "[SAFETY-NET]" in clean or "[DEBUG]" in clean:
            self._ot_write(f"  {clean}", "process")
        else:
            self._ot_write(f"  {clean}", "dim")

    def _ot_hist_up(self, _=None):
        if self._ot_history:
            self._ot_hist_idx = min(self._ot_hist_idx + 1, len(self._ot_history) - 1)
            self._ot_entry.delete(0, "end")
            self._ot_entry.insert(0, list(self._ot_history)[-(self._ot_hist_idx + 1)])
        return "break"

    def _ot_hist_down(self, _=None):
        if self._ot_hist_idx > 0:
            self._ot_hist_idx -= 1
            self._ot_entry.delete(0, "end")
            self._ot_entry.insert(0, list(self._ot_history)[-(self._ot_hist_idx + 1)])
        elif self._ot_hist_idx == 0:
            self._ot_hist_idx = -1
            self._ot_entry.delete(0, "end")
        return "break"

    def _ct_hist_up(self, _=None):
        if self._ct_history:
            self._ct_hist_idx = min(self._ct_hist_idx + 1, len(self._ct_history) - 1)
            self._ct_entry.delete(0, "end")
            self._ct_entry.insert(0, list(self._ct_history)[-(self._ct_hist_idx + 1)])
        return "break"

    def _ct_hist_down(self, _=None):
        if self._ct_hist_idx > 0:
            self._ct_hist_idx -= 1
            self._ct_entry.delete(0, "end")
            self._ct_entry.insert(0, list(self._ct_history)[-(self._ct_hist_idx + 1)])
        elif self._ct_hist_idx == 0:
            self._ct_hist_idx = -1
            self._ct_entry.delete(0, "end")
        return "break"

    def _ct_on_enter(self, _=None):
        """Input handler voor Claude Code terminal."""
        cmd = self._ct_entry.get().strip()
        if not cmd:
            return
        self._ct_entry.delete(0, "end")
        self._ct_history.append(cmd)
        self._ct_hist_idx = -1
        self._ct_write(f"\u25b6 {cmd}", "input")
        low = cmd.lower().strip("/")
        if low == "new":
            self._claude_has_session = False
            self._ct_write("  \U0001f504 Nieuwe conversatie gestart.", "system")
            self._ct_write("  Volgende vraag begint met verse context.", "dim")
        elif low == "clear":
            self._ct_text.configure(state="normal")
            self._ct_text.delete("1.0", "end")
            self._ct_text.configure(state="disabled")
            self._ct_write("Cleared.\n", "system")
        elif low == "login":
            import webbrowser
            webbrowser.open("https://console.anthropic.com/")
            self._ct_write("  Opening Anthropic Console...", "system")
        elif low.startswith("apikey "):
            raw_key = cmd.strip().split(None, 1)[1] if " " in cmd.strip() else ""
            if raw_key and raw_key.startswith("sk-"):
                self._claude_api_key = raw_key
                self._ct_write(f"  \u2705 API key ingesteld: {raw_key[:7]}...{raw_key[-4:]}", "system")
            else:
                self._ct_write("  \u26d4 Ongeldige key. Verwacht: apikey sk-ant-...", "error")
        elif low == "omega":
            self._omega_activate(self._ct_write)
        elif low == "status":
            sid = getattr(self, '_claude_session_id', None)
            self._ct_write(f"  Session: {sid[:12] + '...' if sid else 'geen'}", "system")
            self._ct_write(f"  Continuity: {'actief' if getattr(self, '_claude_has_session', False) else 'nieuw'}", "output")
            model = getattr(self, '_claude_model', 'default')
            self._ct_write(f"  Model: {model}", "output")
        elif low == "help":
            self._ct_write("  Claude Terminal Commands:", "system")
            for c, d in [
                ("new", "Nieuwe conversatie (reset session)"),
                ("clear", "Terminal wissen"),
                ("status", "Session info tonen"),
                ("login", "Anthropic Console openen"),
                ("apikey sk-...", "API key instellen"),
                ("wav <vraag>", "Gebruik Groq WAV-Loop"),
                ("omega", "Sovereign activatie"),
                ("help", "Dit overzicht"),
            ]:
                self._ct_write(f"    {c:18s} {d}", "dim")
            self._ct_write("\n  Typ direct een vraag voor Claude Code.", "output")
        elif low.startswith("wav "):
            # WAV-Loop shortcut vanuit Claude terminal
            vraag = cmd[4:].strip()
            if vraag:
                self._ot_write(f"\u2126 > {vraag}", "input")
                self._ot_write("\u2126 Processing... (WAV-Loop)", "process")
                threading.Thread(target=self._ot_ask_brain, args=(vraag,), daemon=True).start()
                self._ct_write(f"  \u21aa Doorgestuurd naar Omega Brain WAV-Loop", "system")
            else:
                self._ct_write("  Gebruik: wav <je vraag>", "dim")
        elif re.match(r'^(sk-|key-|api[_-])', cmd, re.IGNORECASE):
            self._ct_write("  \u26d4 Gebruik: apikey sk-ant-...", "error")
        else:
            self._ct_write("\U0001f916 [Claude] Processing...", "process")
            self._ct_entry.configure(state="disabled")
            threading.Thread(target=self._ot_ask_claude, args=(cmd,), daemon=True).start()

    def _omega_activate(self, writer):
        """Sovereign activatie banner in een terminal."""
        writer("", "system")
        writer("  \u2126\u2126\u2126  OMEGA SOVEREIGN CORE  \u2126\u2126\u2126", "system")
        writer("  \u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501", "system")
        writer("  176 modules | 48K lines | 5 Tiers | 32 tools", "output")
        writer("  T1 Trinity | T2 Guardians | T3 Specialists", "output")
        writer("  T4 Infra   | T5 Singularity", "output")
        writer("  \u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501", "system")
        writer("  Prime Executor ONLINE. Alle systemen actief.", "verify")
        writer("  Wat kan ik voor je doen, Commandant?", "verify")
        writer("", "system")

    def _omega_awaken(self):
        """Background thread: sequentieel alle subsystemen activeren."""
        w = lambda txt, tag="output": self._ot_text.after(0, self._ot_write, txt, tag)
        _omega_mode["awakening"] = True
        _omega_mode["systems_ok"].clear()
        _omega_mode["systems_fail"].clear()
        t0 = time.time()

        # Banner
        self._ot_text.after(0, self._omega_activate, self._ot_write)
        time.sleep(0.3)
        w("\n  OMEGA AWAKENING SEQUENCE INITIATED", "system")
        w("  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", "system")

        def _step(label, fn):
            w(f"  [{label}] initializing...", "process")
            try:
                result = fn()
                _omega_mode["systems_ok"].append(label)
                w(f"  [{label}] ONLINE", "verify")
                return result
            except Exception as e:
                _omega_mode["systems_fail"].append(label)
                w(f"  [{label}] FAILED: {e}", "error")
                return None

        # [1/6] SOUL — CorticalStack + NeuralBus
        cs = _step("SOUL: CorticalStack", lambda: get_cortical_stack() if HAS_CORTICAL else None)
        bus = _step("SOUL: NeuralBus", lambda: get_bus() if HAS_BUS else None)

        # [2/6] BODY — SwarmEngine
        def _init_engine():
            eng_tuple = _load_engine()
            eng = eng_tuple[0] if eng_tuple else None
            if eng is None:
                raise RuntimeError("SwarmEngine load failed")
            _omega_mode["engine"] = eng
            return eng
        engine = _step("BODY: SwarmEngine", _init_engine)

        # [3/6] MIND — CentralBrain + PrometheusBrain
        brain = _step("MIND: CentralBrain", lambda: _load_brain() or (_ for _ in ()).throw(RuntimeError("load failed")))
        if HAS_PROMETHEUS:
            _step("MIND: PrometheusBrain", lambda: PrometheusBrain)

        # [4/6] IMMUNE — BlackBox + HallucinatieSchild + AdversarialTribunal
        if HAS_BLACKBOX:
            _step("IMMUNE: BlackBox", get_black_box)
        if HAS_SCHILD:
            _step("IMMUNE: HallucinatieSchild", get_hallucination_shield)
        if HAS_TRIBUNAL:
            _step("IMMUNE: AdversarialTribunal", get_adversarial_tribunal)

        # [5/6] COMMAND — TaskArbitrator
        if HAS_ARBITRATOR:
            arb = _step("COMMAND: TaskArbitrator", lambda: get_arbitrator(brain=brain))
            _omega_mode["arbitrator"] = arb

        # [6/6] MONITORING — Waakhuis + Introspector
        if HAS_WAAKHUIS:
            _step("MONITORING: Waakhuis", get_waakhuis)
        if HAS_INTROSPECTOR:
            _step("MONITORING: Introspector", get_introspector)

        # Summary
        elapsed = time.time() - t0
        ok = len(_omega_mode["systems_ok"])
        fail = len(_omega_mode["systems_fail"])
        total = ok + fail

        w("")
        w("  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", "system")
        if fail == 0:
            w(f"  OMEGA FULLY OPERATIONAL — {ok}/{total} systems", "verify")
        else:
            w(f"  OMEGA PARTIAL — {ok}/{total} OK, {fail} FAILED", "warn")
            for s in _omega_mode["systems_fail"]:
                w(f"    FAIL: {s}", "error")
        w(f"  Awakening time: {elapsed:.1f}s", "dim")
        w(f"  All questions now route through FULL PIPELINE", "system")
        w("  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", "system")
        w("")

        _omega_mode["active"] = True
        _omega_mode["awakening"] = False
        _omega_mode["activated_at"] = time.time()

        # NeuralBus event
        if bus:
            _omega_bus_publish(bus, "OMEGA_AWAKENED", {
                "systems_ok": ok, "systems_fail": fail,
                "elapsed": round(elapsed, 2),
            })

        # Re-enable entry
        self._ot_text.after(0, lambda: self._ot_entry.configure(state="normal"))

    def _dedup_payloads(self, payloads):
        """Merge duplicate agent antwoorden (>75% similarity)."""
        from difflib import SequenceMatcher
        seen = []
        for p in payloads:
            txt = (getattr(p, "display_text", "") or str(getattr(p, "content", ""))).strip()
            if not txt:
                continue
            merged = False
            for s in seen:
                ratio = SequenceMatcher(None, s["text"][:500], txt[:500]).ratio()
                if ratio > 0.75:
                    s["agents"].append(getattr(p, "agent", "?"))
                    if len(txt) > len(s["text"]):
                        s["text"] = txt
                        s["payload"] = p
                    merged = True
                    break
            if not merged:
                seen.append({"text": txt, "payload": p, "agents": [getattr(p, "agent", "?")]})
        return seen

    def _ot_ask_omega(self, question):
        """OMEGA Pipeline: Full SwarmEngine dispatch met dedup + Arbitrator fallback."""
        t0 = time.time()
        w = lambda txt, tag="output": self._ot_text.after(0, self._ot_write, txt, tag)

        try:
            engine = _omega_mode.get("engine")
            brain = _load_brain()

            if engine is None:
                w("[OMEGA] Engine niet beschikbaar — fallback naar WAV-Loop", "warn")
                self._ot_ask_brain(question)
                return

            # Check for complex goal keywords → Arbitrator decomposition
            _GOAL_KEYWORDS = {"plan", "analyseer alles", "missie", "decompose",
                              "strategie", "audit", "full scan", "volledige analyse"}
            q_lower = question.lower()
            use_arbitrator = (
                _omega_mode.get("arbitrator") is not None
                and any(kw in q_lower for kw in _GOAL_KEYWORDS)
            )

            if use_arbitrator:
                w("\u2126 [ARBITRATOR] Decomposing goal...", "process")
                arb = _omega_mode["arbitrator"]
                try:
                    import asyncio
                    loop = asyncio.new_event_loop()
                    manifest = loop.run_until_complete(arb.decompose(question))
                    task_count = len(manifest.taken) if hasattr(manifest, "taken") else 0
                    w(f"\u2126 [ARBITRATOR] {task_count} sub-taken gedecomponeerd", "system")
                    manifest = loop.run_until_complete(arb.execute(manifest, engine=engine))
                    loop.close()

                    # Show results
                    for task in getattr(manifest, "taken", []):
                        status = getattr(task, "status", "?")
                        desc = getattr(task, "beschrijving", getattr(task, "description", str(task)))[:120]
                        tag = "verify" if status == "DONE" else "warn"
                        w(f"  [{status}] {desc}", tag)

                    elapsed = time.time() - t0
                    _omega_mode["omega_queries"] += 1
                    _wav_stats["queries"] += 1
                    _wav_stats["total_time"] += elapsed
                    w(f"\n  [OMEGA ARBITRATOR: {elapsed:.1f}s | {task_count} tasks]", "dim")
                    w("")
                    return
                except Exception as e:
                    w(f"[ARBITRATOR] Decompose failed: {e} — using SwarmEngine direct", "warn")

            # Standard SwarmEngine pipeline
            w("\u2126 [OMEGA] Full Pipeline Processing...", "process")

            try:
                import asyncio

                # Hergebruik de gecachte engine uit OMEGA awakening
                loop = asyncio.new_event_loop()
                if brain and hasattr(engine, "brain"):
                    engine.brain = brain
                payloads = loop.run_until_complete(engine.run(question))
                loop.close()
            except Exception as e:
                w(f"[OMEGA] SwarmEngine.run() failed: {e}", "error")
                w("[OMEGA] Fallback naar WAV-Loop...", "warn")
                self._ot_ask_brain(question)
                return

            if not payloads:
                w("[OMEGA] Geen resultaten — fallback naar WAV-Loop", "warn")
                self._ot_ask_brain(question)
                return

            # Dedup payloads
            deduped = self._dedup_payloads(payloads)
            dup_count = len(payloads) - len(deduped)
            if dup_count > 0:
                w(f"  [DEDUP] {dup_count} duplicate antwoorden gemerged", "warn")

            # Display results
            w("")
            for entry in deduped:
                agents = entry["agents"]
                agent_label = " + ".join(agents)
                txt = entry["text"]
                w(f"  [{agent_label}]", "system")
                for line in txt.strip().split("\n")[:20]:
                    w(f"    {line}", "output")
                if len(txt.strip().split("\n")) > 20:
                    w(f"    ... (+{len(txt.strip().split(chr(10))) - 20} lines)", "dim")
                w("")

            elapsed = time.time() - t0
            _omega_mode["omega_queries"] += 1
            _wav_stats["queries"] += 1
            _wav_stats["total_time"] += elapsed
            w(f"  [OMEGA: {elapsed:.1f}s | {len(payloads)} payloads | {len(deduped)} unique | {len(deduped[0]['agents']) if deduped else 0} primary]", "dim")
            w("")

            # NeuralBus event
            if HAS_BUS:
                bus = get_bus()
                _omega_bus_publish(bus, "OMEGA_QUERY", {
                    "question": question[:100],
                    "payloads": len(payloads),
                    "elapsed": round(elapsed, 2),
                })

        except Exception as e:
            w(f"[OMEGA ERROR] {e}", "error")
            w("[OMEGA] Fallback naar WAV-Loop...", "warn")
            try:
                self._ot_ask_brain(question)
            except Exception as e2:
                w(f"[WAV-LOOP ERROR] {e2}", "error")
        finally:
            self._ot_text.after(0, lambda: self._ot_entry.configure(state="normal"))

    def _ot_on_enter(self, _=None):
        cmd = self._ot_entry.get().strip()
        if not cmd:
            return
        self._ot_entry.delete(0, "end")
        self._ot_history.append(cmd)
        self._ot_hist_idx = -1
        self._ot_write(f"\u2126 > {cmd}", "input")
        known = {"help", "clear", "status", "agents", "health",
                 "metrics", "bus", "events", "keys", "cortical",
                 "apps", "brain", "immune", "rag", "diag",
                 "vram", "config", "uptime",
                 "shadow", "dreamer", "oracle", "devops"}
        low = cmd.lower().strip("/")
        if low == "omega":
            if _omega_mode["active"]:
                # Already active — show status
                uptime = int(time.time() - (_omega_mode["activated_at"] or time.time()))
                m, s = divmod(uptime, 60)
                ok = len(_omega_mode["systems_ok"])
                fail = len(_omega_mode["systems_fail"])
                self._ot_write("  OMEGA MODE: ACTIVE", "verify")
                self._ot_write(f"  Systems: {ok} OK / {fail} FAIL", "output")
                self._ot_write(f"  Uptime: {m:02d}:{s:02d}", "output")
                self._ot_write(f"  Omega queries: {_omega_mode['omega_queries']}", "output")
            elif _omega_mode["awakening"]:
                self._ot_write("  OMEGA AWAKENING in progress...", "process")
            else:
                self._ot_entry.configure(state="disabled")
                threading.Thread(target=self._omega_awaken, daemon=True).start()
        elif low in known:
            self._ot_dispatch(low)
            self._ot_write("")
        elif low.startswith("search "):
            query = cmd[7:].strip()
            if query:
                self._ot_dispatch_search(query)
            else:
                self._ot_write("  Gebruik: search <zoekterm>", "dim")
        elif low.startswith("open "):
            app_name = cmd[5:].strip()
            if app_name:
                self._ot_dispatch_open(app_name)
            else:
                self._ot_write("  Gebruik: open <app_naam>", "dim")
        else:
            # Default routing: OMEGA pipeline if active, WAV-Loop otherwise
            if _omega_mode["active"]:
                self._ot_write("\u2126 [OMEGA] Processing...", "process")
                self._ot_entry.configure(state="disabled")
                threading.Thread(target=self._ot_ask_omega, args=(cmd,), daemon=True).start()
            else:
                self._ot_write("\u2126 Processing...", "process")
                self._ot_entry.configure(state="disabled")
                threading.Thread(target=self._ot_ask_brain, args=(cmd,), daemon=True).start()

    def _ot_dispatch(self, cmd):
        eng = _load_engine()[0]
        if cmd == "help":
            self._ot_write("  System commands:", "system")
            for c in ["status", "agents", "health", "metrics", "bus",
                       "events", "keys", "cortical", "apps", "brain",
                       "immune", "rag", "diag", "vram", "config", "uptime"]:
                self._ot_write(f"    {c}", "dim")
            self._ot_write("\n  v3.0 commands:", "system")
            for c, d in [("omega", "AWAKEN all systems (full pipeline)"),
                         ("shadow", "Shadow Governance zones"),
                         ("dreamer", "REM cycle + backup status"),
                         ("oracle", "OracleEye resource predictions"),
                         ("devops", "DevOpsDaemon CI status"),
                         ("search <q>", "CorticalStack zoeken"),
                         ("open <app>", "App tools opzoeken")]:
                self._ot_write(f"    {c:16s} {d}", "dim")
            mode = "OMEGA PIPELINE" if _omega_mode["active"] else "WAV-Loop"
            self._ot_write(f"\n  Question routing ({mode}):", "system")
            if _omega_mode["active"]:
                self._ot_write("    Typ een vraag \u2014 FULL SwarmEngine pipeline.", "dim")
                self._ot_write("    Complexe goals \u2192 TaskArbitrator decompose.", "dim")
            else:
                self._ot_write("    Typ een vraag \u2014 WAV-Loop (CentralBrain).", "dim")
                self._ot_write("    Typ 'omega' om FULL PIPELINE te activeren.", "dim")
        elif cmd == "clear":
            self._ot_text.configure(state="normal")
            self._ot_text.delete("1.0", "end")
            self._ot_text.configure(state="disabled")
            self._ot_write("\u2126 Cleared.\n", "system")
        elif cmd == "status":
            self._ot_write(f"Time: {datetime.now().isoformat()}", "system")
            if eng:
                s = eng.get_stats()
                self._ot_write(f"Queries: {s.get('queries_processed', 0)}", "output")
                self._ot_write(f"Agents: {s.get('active_agents', 0)}", "output")
                self._ot_write(f"Avg: {s.get('avg_response_ms', 0):.1f}ms", "output")
            if HAS_PSUTIL:
                self._ot_write(f"CPU: {psutil.cpu_percent():.1f}%  RAM: {psutil.virtual_memory().percent:.1f}%", "output")
        elif cmd == "agents":
            if eng and hasattr(eng, "agents"):
                for n in sorted(eng.agents):
                    self._ot_write(f"  [{n}]", "output")
                self._ot_write(f"Total: {len(eng.agents)}", "system")
        elif cmd == "health":
            wh = _safe(get_waakhuis) if HAS_WAAKHUIS else None
            if wh:
                for n, i in wh.gezondheidsrapport().get("agents", {}).items():
                    self._ot_write(f"  {n}: {i.get('score', '?')}%", "output")
            else:
                self._ot_write("Waakhuis unavailable", "error")
        elif cmd == "metrics":
            if eng:
                for k, v in eng._swarm_metrics.items():
                    self._ot_write(f"  {k}: {v}", "output")
        elif cmd == "bus":
            bus = _safe(get_bus) if HAS_BUS else None
            if bus:
                for k, v in bus.statistieken().items():
                    self._ot_write(f"  {k}: {v}", "output")
        elif cmd == "events":
            bus = _safe(get_bus) if HAS_BUS else None
            if bus:
                s = bus.get_context_stream(count=10)
                self._ot_write(s if s else "No events.", "output")
        elif cmd == "keys":
            km = _safe(SmartKeyManager) if HAS_KEY_MANAGER else None
            if km:
                self._ot_write(f"Keys: {len(km._keys)}", "system")
                with km._metrics_lock:
                    for n, a in km._agents.items():
                        self._ot_write(f"  {n}: {a.totaal_requests}req {a.totaal_tokens}tok", "output")
        elif cmd == "cortical":
            if HAS_CORTICAL:
                for k, v in get_cortical_stack().get_db_metrics().items():
                    self._ot_write(f"  {k}: {v}", "output")
        elif cmd == "apps":
            if eng and hasattr(eng, "app_registry"):
                apps = sorted(eng.app_registry.keys()) if hasattr(eng.app_registry, "keys") else []
                self._ot_write(f"  Registered apps: {len(apps)}", "system")
                for a in apps:
                    self._ot_write(f"    {a}", "output")
            else:
                try:
                    from danny_toolkit.brain.app_tools import TOOL_DEFINITIONS
                    self._ot_write(f"  Available tools: {len(TOOL_DEFINITIONS)}", "system")
                    for td in TOOL_DEFINITIONS[:15]:
                        name = td.get("function", {}).get("name", "?")
                        self._ot_write(f"    {name}", "output")
                    if len(TOOL_DEFINITIONS) > 15:
                        self._ot_write(f"    ... and {len(TOOL_DEFINITIONS) - 15} more", "dim")
                except Exception:
                    self._ot_write("  App registry not available", "error")
        elif cmd == "brain":
            brain = _brain_cache
            if brain:
                self._ot_write(f"  CentralBrain: ACTIVE", "system")
                tools = getattr(brain, '_tools', getattr(brain, 'tools', []))
                self._ot_write(f"  Tools loaded: {len(tools)}", "output")
                self._ot_write(f"  Provider: {getattr(brain, 'provider', '?')}", "output")
                self._ot_write(f"  Model: {getattr(brain, 'model', '?')}", "output")
            else:
                self._ot_write("  CentralBrain: NOT LOADED", "error")
        elif cmd == "immune":
            if HAS_BLACKBOX:
                try:
                    bb = get_black_box()
                    stats = bb.get_stats()
                    self._ot_write(f"  BlackBox: {stats.get('total_antibodies', 0)} antibodies", "output")
                except Exception:
                    self._ot_write("  BlackBox: error", "error")
            if HAS_SCHILD:
                try:
                    schild = get_hallucination_shield()
                    stats = schild.get_stats()
                    self._ot_write(f"  Shield: {stats.get('beoordeeld', 0)} checks, {stats.get('geblokkeerd', 0)} blocked", "output")
                except Exception:
                    self._ot_write("  Shield: error", "error")
            if HAS_TRIBUNAL:
                try:
                    trib = get_adversarial_tribunal()
                    stats = trib.get_stats()
                    self._ot_write(f"  Tribunal: {stats.get('verdicts', stats.get('total', 0))} verdicts", "output")
                except Exception:
                    self._ot_write("  Tribunal: error", "error")
        elif cmd == "rag":
            try:
                from danny_toolkit.core.vector_store import VectorStore
                vs = VectorStore()
                stats = vs.get_stats()
                for k, v in stats.items():
                    self._ot_write(f"  {k}: {v}", "output")
            except Exception as e:
                self._ot_write(f"  VectorStore: {e}", "error")
        elif cmd == "diag":
            self._ot_write("  Running self-diagnostic...", "process")
            threading.Thread(target=self._ot_run_diag, daemon=True).start()
        elif cmd == "vram":
            vr = _cache.get("vram")
            if vr and vr.get("beschikbaar"):
                self._ot_write(f"  GPU: {vr['gpu_naam']}", "system")
                self._ot_write(f"  Totaal:  {vr['totaal_mb']:,} MB", "output")
                self._ot_write(f"  Gebruik: {vr['in_gebruik_mb']:,} MB", "output")
                self._ot_write(f"  Vrij:    {vr['vrij_mb']:,} MB", "output")
                pct = round(vr['in_gebruik_mb'] / vr['totaal_mb'] * 100, 1)
                bar_len = int(pct / 5)
                bar = "#" * bar_len + "." * (20 - bar_len)
                gc = "output" if vr['gezond'] else "error"
                self._ot_write(f"  [{bar}] {pct}%", gc)
            else:
                self._ot_write("  CUDA not available", "error")
        elif cmd == "config":
            rapport = _cache.get("config_audit")
            if rapport:
                self._ot_write(f"  Veilig: {rapport.veilig}", "output")
                self._ot_write(f"  Gecontroleerd: {rapport.gecontroleerd}", "output")
                self._ot_write(f"  Drift: {rapport.drift_gedetecteerd}", "output")
                if rapport.schendingen:
                    self._ot_write(f"  Schendingen: {len(rapport.schendingen)}", "error")
                    for s in rapport.schendingen[:5]:
                        self._ot_write(f"    [{s.ernst}] {s.beschrijving}", "warn")
                else:
                    self._ot_write("  Geen schendingen", "output")
            else:
                self._ot_write("  ConfigAuditor: loading...", "dim")
        elif cmd == "uptime":
            up_s = int(time.time() - self.winfo_toplevel()._start_time)
            m_up, s_up = divmod(up_s, 60)
            h_up, m_up = divmod(m_up, 60)
            self._ot_write(f"  Dashboard uptime: {h_up:02d}:{m_up:02d}:{s_up:02d}", "system")
            self._ot_write(f"  WAV queries: {_wav_stats['queries']}", "output")
            self._ot_write(f"  Schild blocks: {_wav_stats['schild_blocks']}", "output")
            if _wav_stats['queries'] > 0:
                avg = _wav_stats['total_time'] / _wav_stats['queries']
                self._ot_write(f"  Avg response: {avg:.1f}s", "output")
        elif cmd == "shadow":
            try:
                from danny_toolkit.brain.shadow_governance import ShadowGovernance
                sg = ShadowGovernance()
                self._ot_write("  Shadow Governance Status:", "system")
                self._ot_write(f"  Zones: ROOD (locked) | GEEL (restricted) | GROEN (open)", "output")
                rules = getattr(sg, '_rules', getattr(sg, 'regels', []))
                self._ot_write(f"  Regels: {len(rules) if rules else '9 (default)'}", "output")
                locks = getattr(sg, '_lockdowns', getattr(sg, 'lockdowns', []))
                self._ot_write(f"  Lockdowns: {len(locks) if locks else '2 (default)'}", "output")
            except Exception as e:
                self._ot_write(f"  ShadowGovernance: {e}", "error")
        elif cmd == "dreamer":
            try:
                from danny_toolkit.brain.dreamer import Dreamer
                d = Dreamer.__new__(Dreamer)
                self._ot_write("  Dreamer REM Status:", "system")
                self._ot_write(f"  Schedule: 04:00 (heartbeat)", "output")
                self._ot_write(f"  Cycles: backup, vacuum, retention, compress,", "output")
                self._ot_write(f"          GhostWriter, anticipate, OracleEye", "output")
                # Check last backup
                import glob as _g
                backups = sorted(_g.glob(os.path.join(
                    r"C:\Users\danny\danny-toolkit\data", "cortical_backup_*.db*")))
                if backups:
                    last = os.path.basename(backups[-1])
                    self._ot_write(f"  Last backup: {last}", "output")
                else:
                    self._ot_write(f"  Last backup: none found", "warn")
            except Exception as e:
                self._ot_write(f"  Dreamer: {e}", "error")
        elif cmd == "oracle":
            try:
                from danny_toolkit.brain.oracle_eye import TheOracleEye
                oe = TheOracleEye.__new__(TheOracleEye)
                self._ot_write("  OracleEye Predictions:", "system")
                if HAS_PSUTIL:
                    cpu = psutil.cpu_percent(interval=0.5)
                    ram = psutil.virtual_memory()
                    self._ot_write(f"  CPU: {cpu:.1f}%  {'HIGH' if cpu > 80 else 'OK'}", "output")
                    self._ot_write(f"  RAM: {ram.percent:.1f}%  ({ram.available // (1024**2)} MB vrij)", "output")
                vr = _cache.get("vram")
                if vr and vr.get("beschikbaar"):
                    pct = round(vr['in_gebruik_mb'] / max(vr['totaal_mb'], 1) * 100, 1)
                    self._ot_write(f"  VRAM: {pct}%  ({vr['vrij_mb']} MB vrij)", "output")
                    if pct > 85:
                        self._ot_write(f"  \u26a0 VRAM pressure — GPU workloads at risk", "warn")
                self._ot_write(f"  Scaling: adaptive (CPU-aware pools)", "dim")
            except Exception as e:
                self._ot_write(f"  OracleEye: {e}", "error")
        elif cmd == "devops":
            try:
                from danny_toolkit.brain.devops_daemon import DevOpsDaemon
                self._ot_write("  DevOpsDaemon CI Status:", "system")
                self._ot_write(f"  Loop: test \u2192 analyze \u2192 BlackBox \u2192 NeuralBus", "output")
                self._ot_write(f"  Schedule: ~5 min (heartbeat)", "output")
                # Check BlackBox for recent CI entries
                if HAS_BLACKBOX:
                    bb = get_black_box()
                    stats = bb.get_stats()
                    self._ot_write(f"  Immune antibodies: {stats.get('total_antibodies', 0)}", "output")
            except Exception as e:
                self._ot_write(f"  DevOpsDaemon: {e}", "error")

    def _ot_dispatch_search(self, query):
        """CorticalStack semantic search via Omega terminal."""
        self._ot_write(f"  Searching: \"{query}\"...", "process")
        try:
            if HAS_CORTICAL:
                cs = get_cortical_stack()
                if hasattr(cs, 'search'):
                    results = cs.search(query, top_k=5)
                    if results:
                        for i, r in enumerate(results[:5], 1):
                            tekst = str(r.get("tekst", r.get("content", r.get("action", ""))))[:100]
                            score = r.get("score", r.get("relevance", ""))
                            self._ot_write(f"  {i}. {tekst}", "output")
                            if score:
                                self._ot_write(f"     score: {score}", "dim")
                    else:
                        self._ot_write("  Geen resultaten.", "dim")
                else:
                    # Fallback: zoek in recent events
                    events = cs.get_recent_events(count=50)
                    matches = [e for e in events if query.lower() in str(e).lower()][:5]
                    if matches:
                        for m in matches:
                            self._ot_write(f"  {str(m)[:100]}", "output")
                    else:
                        self._ot_write("  Geen matches in recente events.", "dim")
            else:
                self._ot_write("  CorticalStack niet beschikbaar.", "error")
        except Exception as e:
            self._ot_write(f"  Search error: {e}", "error")

    def _ot_dispatch_open(self, app_name):
        """Open een app via brain function calling."""
        self._ot_write(f"  Opening: {app_name}...", "process")
        try:
            # Zoek matching app in tool definitions
            from danny_toolkit.brain.app_tools import TOOL_DEFINITIONS
            app_lower = app_name.lower().replace(" ", "_")
            matches = [td for td in TOOL_DEFINITIONS
                       if app_lower in td.get("function", {}).get("name", "").lower()]
            if matches:
                tool_names = [td["function"]["name"] for td in matches[:5]]
                self._ot_write(f"  Found {len(matches)} tools:", "system")
                for tn in tool_names:
                    self._ot_write(f"    {tn}", "output")
                self._ot_write(f"\n  Gebruik via brain: typ een vraag met \"{app_name}\"", "dim")
            else:
                self._ot_write(f"  App \"{app_name}\" niet gevonden.", "warn")
                self._ot_write("  Typ 'apps' voor beschikbare apps.", "dim")
        except Exception as e:
            self._ot_write(f"  Open error: {e}", "error")

    def _ot_run_diag(self):
        """Run self-diagnostic in background thread."""
        w = lambda txt, tag="output": self._ot_text.after(0, self._ot_write, txt, tag)
        try:
            results = _run_self_diagnostic()
            samenv = results.pop("_samenvatting", {})
            ok = samenv.get("ok", 0)
            fout = samenv.get("fout", 0)
            totaal = samenv.get("totaal", 0)
            w(f"  Scan complete: {ok}/{totaal} OK, {fout} FOUT", "system")
            for comp, info in sorted(results.items()):
                status = info.get("status", "?")
                mark = "[OK]" if status == "OK" else "[!!]"
                tag = "output" if status == "OK" else "error"
                err = info.get("error", "")
                line = f"  {mark} {comp}"
                if err:
                    line += f" — {err[:60]}"
                w(line, tag)
            w("")
        except Exception as e:
            w(f"  Diagnostic error: {e}", "error")

    def _ot_ask_claude(self, question):
        """Execute question via Claude Code CLI — exact als PowerShell ervaring.

        Ondersteunt:
        - Real-time streaming text (content_block_delta events)
        - Volledige tool gebruik + resultaten weergave
        - Session ID tracking voor --resume (persistente conversatie)
        - Auth/credit error detectie met recovery opties
        """
        t0 = time.time()
        w = lambda txt, tag="output": self._ct_text.after(0, self._ct_write, txt, tag)
        try:
            import shutil
            import json as _json
            claude_path = shutil.which("claude")
            if not claude_path:
                winget_path = os.path.expandvars(
                    r"%LOCALAPPDATA%\Microsoft\WinGet\Links\claude.exe")
                if os.path.isfile(winget_path):
                    claude_path = winget_path
            if not claude_path:
                w("[WARN] Claude CLI not found \u2014 fallback to WAV-Loop", "warn")
                self._ot_ask_brain(question)
                return

            # Environment: venv311 + toolkit cwd
            toolkit_dir = r"C:\Users\danny\danny-toolkit"
            venv_dir = os.path.join(toolkit_dir, "venv311")
            venv_scripts = os.path.join(venv_dir, "Scripts")
            env = os.environ.copy()
            env.pop("ANTHROPIC_API_KEY", None)
            env.pop("CLAUDECODE", None)
            env["PATH"] = venv_scripts + os.pathsep + env.get("PATH", "")
            env["VIRTUAL_ENV"] = venv_dir
            env["PYTHONPATH"] = toolkit_dir
            api_key = getattr(self, "_claude_api_key", None)
            if api_key:
                env["ANTHROPIC_API_KEY"] = api_key

            # Build command — stream-json voor real-time output
            cmd = [claude_path, "-p", question, "--output-format", "stream-json", "--verbose",
                   "--allowedTools", "Edit", "Write", "Bash", "Read", "Glob", "Grep",
                   "WebFetch", "Grep", "NotebookEdit", "TodoRead", "TodoWrite"]

            # Session continuity: --resume met echte session ID
            session_id = getattr(self, '_claude_session_id', None)
            if session_id:
                cmd.extend(["--resume", session_id])
            elif getattr(self, '_claude_has_session', False):
                cmd.append("--continue")

            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                cwd=toolkit_dir,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=env,
                creationflags=(subprocess.CREATE_NO_WINDOW
                               if sys.platform == "win32" else 0),
            )

            output_lines = 0
            collected = []
            _streaming_line = []  # Buffer voor delta streaming

            for raw_line in iter(proc.stdout.readline, ''):
                line = raw_line.strip()
                if not line:
                    continue
                try:
                    event = _json.loads(line)
                except _json.JSONDecodeError:
                    w(f"  {line}", "output")
                    output_lines += 1
                    collected.append(line)
                    continue

                etype = event.get("type", "")

                # ── System init: capture session ID + model ──
                if etype == "system":
                    sid = event.get("session_id", "")
                    if sid:
                        self._claude_session_id = sid
                    model = event.get("model", "")
                    if model:
                        w(f"  [{model}]", "dim")

                # ── Streaming text: real-time character output ──
                elif etype == "content_block_delta":
                    delta = event.get("delta", {})
                    text = delta.get("text", "")
                    if text:
                        # Accumuleer tot newline, dan flush
                        _streaming_line.append(text)
                        combined = "".join(_streaming_line)
                        if "\n" in combined:
                            parts = combined.split("\n")
                            for part in parts[:-1]:
                                w(f"  {part}", "output")
                                output_lines += 1
                                collected.append(part)
                            _streaming_line = [parts[-1]] if parts[-1] else []

                elif etype == "content_block_start":
                    _streaming_line = []  # Reset buffer

                elif etype == "content_block_stop":
                    # Flush remaining buffer
                    if _streaming_line:
                        remainder = "".join(_streaming_line).rstrip()
                        if remainder:
                            w(f"  {remainder}", "output")
                            output_lines += 1
                            collected.append(remainder)
                        _streaming_line = []

                # ── Full assistant message (fallback voor non-streaming) ──
                elif etype == "assistant":
                    for block in event.get("message", {}).get("content", []):
                        if block.get("type") == "text":
                            for tl in block["text"].splitlines():
                                w(f"  {tl}", "output")
                                output_lines += 1
                                collected.append(tl)

                # ── Tool gebruik: naam + input weergave ──
                elif etype == "tool_use":
                    tool_name = event.get("tool", event.get("name", "?"))
                    tool_input = event.get("input", {})
                    w(f"  \U0001f527 [{tool_name}]", "system")
                    # Toon relevante tool input (beknopt)
                    if isinstance(tool_input, dict):
                        for k, v in list(tool_input.items())[:3]:
                            v_str = str(v)[:80]
                            w(f"     {k}: {v_str}", "dim")

                # ── Tool resultaat: toon output (getrimd) ──
                elif etype == "tool_result":
                    tool_name = event.get("tool", event.get("name", ""))
                    content = event.get("content", "")
                    if isinstance(content, str) and content.strip():
                        # Toon eerste 5 regels van tool output
                        lines = content.strip().splitlines()
                        preview = lines[:5]
                        for pl in preview:
                            w(f"     {pl[:120]}", "dim")
                        if len(lines) > 5:
                            w(f"     ... ({len(lines) - 5} more lines)", "dim")

                # ── Finaal resultaat: session ID + cost ──
                elif etype == "result":
                    sid = event.get("session_id", "")
                    if sid:
                        self._claude_session_id = sid
                    result_text = event.get("result", "")
                    if result_text:
                        collected.append(str(result_text))
                    cost = event.get("cost_usd", 0)
                    if cost:
                        w(f"  [$: {cost:.4f}]", "dim")

            proc.wait()
            elapsed = time.time() - t0
            rc = proc.returncode

            if rc == 0:
                self._claude_has_session = True

            # ── Auth / credit error detectie ──
            full_output = " ".join(collected).lower()
            _AUTH_ERRORS = [
                "credit balance is too low",
                "invalid api key",
                "authentication failed",
                "unauthorized",
                "not authenticated",
                "session expired",
                "please log in",
            ]
            if rc != 0 and any(err in full_output for err in _AUTH_ERRORS):
                w(f"\n  \u26a0 Auth/credit probleem gedetecteerd.", "warn")
                w(f"  Opties:", "system")
                w(f"    1. login      \u2014 Open Anthropic Console", "dim")
                w(f"    2. apikey sk-ant-...  \u2014 Stel een API key in", "dim")
                w(f"    3. wav <vraag> \u2014 Gebruik Groq WAV-Loop (gratis)", "dim")
            elif rc != 0:
                w(f"  [Claude exit code: {rc}]", "error")

            sid_short = (self._claude_session_id or "")[:8]
            w(f"\n  [Claude: {elapsed:.1f}s | {output_lines} lines | sid:{sid_short}]", "dim")
            w("")

        except Exception as e:
            w(f"[ERROR] Claude: {e}", "error")
        finally:
            self._ct_text.after(0, lambda: self._ct_entry.configure(state="normal"))

    def _ot_ask_brain(self, question):
        """WAV-Loop: Will -> Action -> Verification via CentralBrain."""
        t0 = time.time()
        w = lambda txt, tag="output": self._ot_text.after(0, self._ot_write, txt, tag)
        wc = lambda line: self._ot_text.after(0, self._ot_write_captured, line)
        try:
            brain = _load_brain()
            if brain is None:
                w("[ERROR] CentralBrain not available", "error")
                return

            # Houd laatste 4 berichten (2 exchanges) voor follow-up context
            while len(brain.conversation_history) > 4:
                brain.conversation_history.popleft()

            # ── PRE-CHECK: Self-diagnostic als gevraagd ──
            q_lower = question.lower()
            diag_data = None
            if any(kw in q_lower for kw in _DIAGNOSTIC_KEYWORDS):
                w("\u2126 [D] Diagnostic \u2014 scanning all modules...", "process")
                diag_data = _run_self_diagnostic()
                samenv = diag_data.pop("_samenvatting", {})
                ok_count = samenv.get("ok", 0)
                fout_count = samenv.get("fout", 0)
                totaal = samenv.get("totaal", 0)
                w(f"\u2126 [D] Scan complete: {ok_count}/{totaal} OK, {fout_count} FOUT", "system")

                # Bouw diagnostic context voor de brain
                diag_lines = [f"SYSTEEM DIAGNOSTIC ({ok_count}/{totaal} modules OK):"]
                for comp, info in sorted(diag_data.items()):
                    status = info.get("status", "?")
                    err = info.get("error", "")
                    mark = "\u2705" if status == "OK" else "\u274c"
                    line = f"  {mark} {comp}: {status}"
                    if err:
                        line += f" — {err}"
                    diag_lines.append(line)
                diag_context = "\n".join(diag_lines)
                question = f"{question}\n\nHier zijn de ECHTE testresultaten:\n{diag_context}\n\nAnalyseer welke componenten werken en welke niet. Geef details over fouten."

            # ── PHASE 1: WILL (Plan + Execute via function calling) ──
            w("\u2126 [W] Will \u2014 planning & executing...", "process")

            # Capture stdout om [TOOL] en [FALLBACK] prints te vangen
            import io as _io
            from contextlib import redirect_stdout as _rs
            _stdout_buf = _io.StringIO()
            try:
                with _rs(_stdout_buf):
                    response = brain.process_request(question, use_tools=True, max_tokens=2000)
            except Exception as _brain_err:
                response = None
                w(f"[ERROR] Brain crash: {_brain_err}", "error")
            t_action = time.time() - t0

            # Toon captured debug/tool output in GUI (met automatische kleurdetectie)
            _captured = _stdout_buf.getvalue().strip()
            if _captured:
                for _dline in _captured.split("\n"):
                    if _dline.strip():
                        wc(_dline)

            if not response or not response.strip():
                w("[ERROR] Empty response from Brain", "error")
                return

            w(f"\u2126 [A] Action \u2014 completed in {t_action:.1f}s", "process")

            # ── PHASE 2: VERIFICATION ──
            w("\u2126 [V] Verify \u2014 checking response quality...", "process")
            t_v0 = time.time()

            verify_prompt = (
                f"Vraag: \"{question}\"\n"
                f"Antwoord: {response[:200]}\n"
                "Geef ALLEEN: Score: [0-100] en 1 zin waarom."
            )
            try:
                verification = _ollama_verify(verify_prompt, timeout=45)
                t_verify = time.time() - t_v0
            except Exception as e:
                logger.debug("Ollama verification failed: %s", e)
                verification = None
                t_verify = 0

            # ── PHASE 2.5: HALLUCINATIESCHILD ──
            # Extract Ollama verify score as truth_anchor_score
            _verify_score = None
            if verification:
                import re as _re
                _sm = _re.search(r'[Ss]core[:\s]*\[?(\d{1,3})\]?', verification)
                if _sm:
                    _verify_score = int(_sm.group(1)) / 100.0  # 0.0-1.0

            schild_label = ""
            schild_tag = "output"
            if HAS_SCHILD:
                try:
                    schild = get_hallucination_shield()
                    from types import SimpleNamespace
                    pseudo = SimpleNamespace(
                        content=response,
                        display_text=response,
                        type="text",
                        agent="CentralBrain",
                        metadata={"source": "wav_loop"},
                    )
                    rapport = schild.beoordeel(
                        [pseudo], question,
                        truth_anchor_score=_verify_score,
                    )
                    if rapport.geblokkeerd:
                        schild_label = f"\u26a0 GEBLOKKEERD (score {rapport.totaal_score:.2f}): {rapport.reden_blokkade}"
                        schild_tag = "error"
                    elif rapport.regel_schendingen:
                        schild_label = f"\u26a0 WAARSCHUWING (score {rapport.totaal_score:.2f}): {', '.join(rapport.regel_schendingen[:2])}"
                        schild_tag = "warn"
                    elif rapport.totaal_score < 0.55:
                        schild_label = f"\u26a0 ONZEKER (score {rapport.totaal_score:.2f})"
                        schild_tag = "warn"
                    else:
                        schild_label = f"\u2705 OK (score {rapport.totaal_score:.2f} | {len(rapport.claims)} claims)"
                        schild_tag = "output"
                except Exception as e:
                    logger.warning("Schild check error: %s", e)
                    schild_label = f"\u26a0 SCHILD FOUT: {e}"
                    schild_tag = "error"

            # ── OUTPUT ──
            w("")
            for line in response.strip().split("\n"):
                w(f"  {line}", "output")

            # Show verification result
            w("")
            if verification and verification.strip():
                w("\u2126 [V] Verificatie:", "verify")
                for line in verification.strip().split("\n")[:5]:
                    w(f"  \u2502 {line}", "verify")
            else:
                w("\u2126 [V] Verificatie: (geen respons van Ollama)", "dim")

            if schild_label:
                w(f"\u2126 [S] Schild: {schild_label}", schild_tag)

            elapsed = time.time() - t0

            # Track WAV stats
            _wav_stats["queries"] += 1
            _wav_stats["total_time"] += elapsed
            if schild_label and "GEBLOKKEERD" in schild_label:
                _wav_stats["schild_blocks"] += 1
            elif schild_label and "WAARSCHUWING" in schild_label:
                _wav_stats["schild_warns"] += 1

            avg_t = _wav_stats["total_time"] / _wav_stats["queries"]
            w(f"\n  [WAV: W={t_action:.1f}s V={t_verify:.1f}s | total={elapsed:.1f}s | {len(response)} chars]", "dim")
            w(f"  [Session: {_wav_stats['queries']} queries | avg {avg_t:.1f}s | S-blocks:{_wav_stats['schild_blocks']} warns:{_wav_stats['schild_warns']}]", "dim")
            w("")

        except Exception as e:
            w(f"[ERROR] {e}", "error")
        finally:
            self._ot_text.after(0, lambda: self._ot_entry.configure(state="normal"))

    # ── Cortex Network (LIVE — refreshes with waakhuis health) ──
    def _draw_cortex(self):
        ax = self._cortex_ax
        ax.clear()
        ax.set_xlim(-7, 7)
        ax.set_ylim(-1.0, 6.5)
        ax.set_aspect("equal")
        ax.axis("off")
        tc = {1: ("TRINITY", NEON_CYAN, 220, 4), 2: ("GUARDIANS", NEON_GREEN, 160, 3),
              3: ("SPECIALISTS", NEON_ORANGE, 120, 2), 4: ("INFRA", NEON_PURPLE, 100, 1),
              5: ("SINGULARITY", NEON_RED, 180, 5)}
        if not HAS_TRINITY:
            ax.text(0, 3, "trinity_models\nnot available", ha="center", color=TEXT_DIM, fontsize=10)
            self._cortex_cv.draw_idle()
            return
        # Get live health data
        rapport = _cache.get("waakhuis_rapport", {})
        agent_health = rapport.get("agents", {})
        tiers = {}
        for role in CosmicRole:
            tiers.setdefault(CosmicRole.get_tier(role), []).append(role)
        positions = {}
        for tn, roles in sorted(tiers.items()):
            name, col, sz, y = tc.get(tn, tc[4])
            for i, role in enumerate(roles):
                x = (i - (len(roles) - 1) / 2) * 1.5
                yy = y + (hash(role.name) % 100 - 50) * 0.002
                positions[role.name] = (x, yy)
                # Live color: match role name to waakhuis agents
                health = agent_health.get(role.name, {}).get("score", None)
                if health is not None:
                    node_col = NEON_GREEN if health >= 70 else (NEON_ORANGE if health >= 30 else NEON_RED)
                    node_alpha = 0.9
                else:
                    node_col = col
                    node_alpha = 0.6
                ax.scatter(x, yy, s=sz, color=node_col, alpha=node_alpha, zorder=3,
                           edgecolors=node_col, linewidths=1.5)
                ax.scatter(x, yy, s=sz * 2, color=node_col, alpha=0.08, zorder=2)
                label = role.name
                if health is not None:
                    label += f" {health:.0f}%"
                ax.text(x, yy + 0.35, label, ha="center", va="bottom",
                        fontsize=6, color=TEXT_PRIMARY, fontweight="bold")
        for tf, tt in [(1, 2), (2, 3), (3, 4), (5, 1)]:
            for ra in tiers.get(tf, []):
                for rb in tiers.get(tt, []):
                    pa, pb = positions[ra.name], positions[rb.name]
                    ax.plot([pa[0], pb[0]], [pa[1], pb[1]],
                            color=NEON_CYAN, alpha=0.07, linewidth=0.8, zorder=1)
        for tn, (name, col, _, y) in tc.items():
            ax.text(-6.5, y, f"T{tn}: {name}", fontsize=7, color=col,
                    va="center", fontweight="bold")
        # Live system health summary
        if agent_health:
            scores = [info.get("score", 100) for info in agent_health.values()]
            avg = sum(scores) / len(scores)
            hc = NEON_GREEN if avg >= 70 else (NEON_ORANGE if avg >= 30 else NEON_RED)
            ax.text(0, -0.7, f"SYSTEM HEALTH: {avg:.0f}% | {len(agent_health)} agents active",
                    ha="center", fontsize=9, color=hc, fontweight="bold")
        # WAV stats
        wq = _wav_stats["queries"]
        if wq > 0:
            avg_t = _wav_stats["total_time"] / wq
            ax.text(0, 6.2, f"WAV: {wq} queries | avg {avg_t:.1f}s | S-blocks: {_wav_stats['schild_blocks']}",
                    ha="center", fontsize=7, color=NEON_CYAN, fontstyle="italic")
        self._cortex_fig.tight_layout(pad=0.3)
        self._cortex_cv.draw_idle()

    # ── Pulse Protocol ──
    def update_pulse(self):
        cpu = _cache.get("cpu")
        ram = _cache.get("ram")
        if cpu is not None:
            self._pulse_samples.append(cpu)
            self._cpu_lbl.configure(text=f"CPU: {cpu:.0f}%")
            self._ram_lbl.configure(text=f"RAM: {ram:.0f}%" if ram else "RAM: --%")
        else:
            t = len(self._pulse_samples)
            self._pulse_samples.append(20 + 10 * math.sin(t / 5) +
                                       50 * math.exp(-((t % 20 - 5) ** 2) / 2))
        ax = self._pulse_ax
        ax.clear()
        d = list(self._pulse_samples)
        ax.fill_between(range(len(d)), d, alpha=0.08, color=NEON_GREEN)
        ax.plot(d, color=NEON_GREEN, linewidth=1.5)
        ax.set_ylim(0, 100)
        ax.set_xlim(0, 59)
        ax.set_ylabel("CPU %", fontsize=7)
        ax.set_xticks([])
        ax.tick_params(labelsize=6)
        ax.grid(axis="y", alpha=0.3)
        self._pulse_fig.tight_layout(pad=0.4)
        self._pulse_cv.draw_idle()

    # ── Fuel Gauge ──
    def update_fuel(self):
        kd = _cache.get("key_data")
        if kd:
            rpm_u = kd.get("rpm_total", 0)
            rpm_m = kd.get("rpm_limit", 30)
            tpm_u = kd.get("tpm_total", 0)
            tpm_m = kd.get("tpm_limit", 30000)
            pct = min(100, (rpm_u / rpm_m) * 100) if rpm_m else 0
        else:
            pct, rpm_u, rpm_m, tpm_u, tpm_m = 0, 0, 30, 0, 30000
        self._rpm_lbl.configure(text=f"RPM: {rpm_u}/{rpm_m}")
        tp = f"{tpm_u // 1000}K" if tpm_u >= 1000 else str(tpm_u)
        self._tpm_lbl.configure(text=f"TPM: {tp}/{tpm_m // 1000}K")
        # Skip chart redraw if percentage unchanged
        pct_rounded = round(pct, 1)
        if pct_rounded == self._prev_fuel_pct:
            return
        self._prev_fuel_pct = pct_rounded
        ax = self._fuel_ax
        ax.clear()
        th_bg = np.linspace(0, math.pi, 100)
        ax.plot(th_bg, [1] * 100, color=BORDER, linewidth=12, solid_capstyle="round")
        gc = NEON_GREEN if pct < 50 else (NEON_ORANGE if pct < 80 else NEON_RED)
        if pct > 0:
            th_f = np.linspace(0, (pct / 100) * math.pi, max(2, int(pct)))
            ax.plot(th_f, [1] * len(th_f), color=gc, linewidth=12, solid_capstyle="round")
        ax.text(math.pi / 2, 0.35, f"{pct:.0f}%", ha="center", va="center",
                fontsize=22, fontweight="bold", color=gc)
        ax.text(math.pi / 2, 0.0, "API USAGE", ha="center", va="center",
                fontsize=7, color=TEXT_DIM)
        ax.set_ylim(0, 1.4)
        ax.set_thetamin(0)
        ax.set_thetamax(180)
        ax.set_theta_direction(-1)
        ax.set_theta_offset(math.pi)
        ax.grid(False)
        ax.set_xticks([])
        ax.set_yticks([])
        ax.spines["polar"].set_visible(False)
        self._fuel_fig.tight_layout(pad=0.3)
        self._fuel_cv.draw_idle()

    # ── Listener ──
    def update_listener(self):
        counts = _cache.get("bus_event_counts", [])
        bus_stats = _cache.get("bus_stats")
        if bus_stats:
            self._ev_lbl.configure(text=f"Events: {bus_stats.get('events_gepubliceerd', 0)}")
            self._sub_lbl.configure(text=f"Subs: {bus_stats.get('subscribers', 0)}")
        # Skip chart redraw if counts unchanged
        if counts == self._prev_listener_counts:
            return
        self._prev_listener_counts = list(counts) if counts else None
        if not counts:
            counts = [0]
        ax = self._list_ax
        ax.clear()
        ax.fill_between(range(len(counts)), counts, alpha=0.1, color=NEON_CYAN)
        ax.plot(counts, color=NEON_CYAN, linewidth=1.5)
        ax.set_xlim(0, max(1, len(counts) - 1))
        ax.set_ylabel("Events", fontsize=7)
        ax.set_xticks([])
        ax.tick_params(labelsize=6)
        ax.grid(axis="y", alpha=0.3)
        self._list_fig.tight_layout(pad=0.4)
        self._list_cv.draw_idle()

    # ── Mini: Recent Events ──
    def _update_mini_events(self):
        self._mini_events.clear()
        events = _cache.get("cortical_events", [])
        if events:
            for ev in events[:6]:
                ts = ev.get("timestamp", "?")
                if isinstance(ts, str) and len(ts) > 16:
                    ts = ts[11:16]
                actor = ev.get("actor", "?")
                action = ev.get("action", "?")
                self._mini_events.write(f" {ts} {actor}: {action}")
        else:
            self._mini_events.write(" No events")

    # ── Mini: Circuit Breakers ──
    def _update_mini_circuits(self):
        self._mini_circuits.clear()
        cs = _cache.get("circuit_state")
        if cs:
            open_count = sum(1 for s in cs.values() if s.get("is_open"))
            closed_count = sum(1 for s in cs.values() if not s.get("is_open"))
            self._mini_circuits.write(f" CLOSED: {closed_count}  OPEN: {open_count}")
            for agent, state in sorted(cs.items()):
                if state.get("is_open") or state.get("consecutive_failures", 0) > 0:
                    fails = state.get("consecutive_failures", 0)
                    icon = "[OPEN]" if state.get("is_open") else "[WARN]"
                    self._mini_circuits.write(f" {icon} {agent}: {fails} fails")
            if open_count == 0 and all(
                    s.get("consecutive_failures", 0) == 0 for s in cs.values()):
                self._mini_circuits.write(" All circuits healthy")
        else:
            self._mini_circuits.write(" No circuit data")

    # ── Mini: Immune Status ──
    def _update_mini_immune(self):
        self._mini_immune.clear()
        bb_stats = _cache.get("blackbox_stats")
        if bb_stats:
            self._mini_immune.write(f" BlackBox: {bb_stats.get('total_antibodies', 0)} antibodies")
            self._mini_immune.write(f" Failures: {bb_stats.get('recorded_failures', 0)}")
        shield_stats = _cache.get("shield_stats")
        if shield_stats:
            self._mini_immune.write(f" Shield: {shield_stats.get('beoordeeld', 0)} checks")
            self._mini_immune.write(f" Blocked: {shield_stats.get('geblokkeerd', 0)}")
        if not bb_stats and not shield_stats:
            self._mini_immune.write(" Immune system N/A")

    def refresh(self):
        self.update_vanguard()
        self._draw_cortex()
        self.update_pulse()
        self.update_fuel()
        self.update_listener()
        self._update_mini_events()
        self._update_mini_circuits()
        self._update_mini_immune()
        # Refresh extra panels added via panel picker
        for panel, update_fn in list(self._extra_panels):
            try:
                if panel.winfo_exists():
                    update_fn(panel)
                else:
                    self._extra_panels.remove((panel, update_fn))
            except Exception as e:
                logger.debug("Extra panel refresh: %s", e)


# ╔══════════════════════════════════════════════════════════════════╗
# ║  TAB 2: AGENTS                                                 ║
# ╚══════════════════════════════════════════════════════════════════╝

class AgentsTab(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.health_panel = InfoPanel(self, "\u269b Agent Health Report")
        self.health_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 4), pady=(0, 4))
        self.circuit_panel = InfoPanel(self, "\u26a1 Circuit Breakers")
        self.circuit_panel.grid(row=0, column=1, sticky="nsew", padx=4, pady=(0, 4))
        self.gpu_panel = InfoPanel(self, "\U0001f3ae GPU / VRAM Status")
        self.gpu_panel.grid(row=0, column=2, sticky="nsew", padx=(4, 0), pady=(0, 4))
        self.metrics_panel = InfoPanel(self, "\U0001f4ca Pipeline Metrics")
        self.metrics_panel.grid(row=1, column=0, sticky="nsew", padx=(0, 4), pady=(4, 0))
        self.keys_panel = InfoPanel(self, "\U0001f511 API Key Status")
        self.keys_panel.grid(row=1, column=1, columnspan=2, sticky="nsew", padx=(4, 0), pady=(4, 0))

    def refresh(self):
        # Health — from cache
        self.health_panel.clear()
        rapport = _cache.get("waakhuis_rapport")
        if rapport:
            for name, info in sorted(rapport.get("agents", {}).items()):
                score = info.get("score", "?")
                lat = info.get("latency", {})
                disp = lat.get("count", 0) if isinstance(lat, dict) else 0
                errs_info = info.get("fouten", {})
                errs = errs_info.get("totaal", 0) if isinstance(errs_info, dict) else 0
                icon = "[OK]" if isinstance(score, (int, float)) and score >= 70 else (
                    "[!!]" if isinstance(score, (int, float)) and score >= 30 else "[XX]")
                self.health_panel.write(f"  {icon} {name:20s} {score:>3}%  disp:{disp}  err:{errs}")
            hw = _cache.get("hardware_status", {})
            self.health_panel.write(f"\n  Hardware: CPU {hw.get('cpu_percent', '?')}%  "
                                    f"RAM {hw.get('ram_percent', '?')}%")
        else:
            self.health_panel.write("Waakhuis not available")

        # Circuit breakers — from cache
        self.circuit_panel.clear()
        cs = _cache.get("circuit_state")
        if cs:
            for agent, state in sorted(cs.items()):
                is_open = state.get("is_open", False)
                fails = state.get("consecutive_failures", 0)
                cooldown = state.get("cooldown_remaining", 0)
                icon = "[OPEN]" if is_open else "[CLOSED]"
                self.circuit_panel.write(f"  {icon} {agent:20s} fails:{fails}  cd:{cooldown}")
        else:
            self.circuit_panel.write("Circuit data not available")

        # Pipeline metrics — from cache
        self.metrics_panel.clear()
        engine_stats = _cache.get("engine_stats")
        if engine_stats:
            am = engine_stats.get("agent_metrics", {})
            if am:
                for agent, m in sorted(am.items()):
                    calls = m.get("calls", 0)
                    avg = m.get("avg_latency_ms", m.get("avg_ms", 0))
                    rate = m.get("success_rate", 1.0)
                    self.metrics_panel.write(
                        f"  {agent:20s} calls:{calls:>4}  avg:{avg:>6.1f}ms  ok:{rate:.0%}")
            else:
                self.metrics_panel.write(f"  Queries: {engine_stats.get('queries_processed', 0)}")
                self.metrics_panel.write(f"  Agents: {engine_stats.get('active_agents', 0)}")
                self.metrics_panel.write(f"  Avg: {engine_stats.get('avg_response_ms', 0):.1f}ms")
        else:
            self.metrics_panel.write("  Engine not available")

        # GPU / VRAM — from cache
        self.gpu_panel.clear()
        vr = _cache.get("vram")
        if vr and vr.get("beschikbaar"):
            self.gpu_panel.write(f"  GPU:     {vr['gpu_naam']}")
            self.gpu_panel.write(f"  Totaal:  {vr['totaal_mb']:,} MB")
            self.gpu_panel.write(f"  Gebruikt:{vr['in_gebruik_mb']:,} MB")
            self.gpu_panel.write(f"  Vrij:    {vr['vrij_mb']:,} MB")
            totaal = vr['totaal_mb'] or 1
            pct = min(100, round(vr['in_gebruik_mb'] / totaal * 100, 1))
            bar_len = int(pct / 5)
            bar = "#" * bar_len + "." * (20 - bar_len)
            status = "[OK]" if vr['gezond'] else "[!!]"
            self.gpu_panel.write(f"\n  {status} [{bar}] {pct}%")
        else:
            self.gpu_panel.write("  CUDA not available")
        cpu = _cache.get("cpu")
        ram = _cache.get("ram")
        if cpu is not None:
            self.gpu_panel.write(f"\n  CPU:  {cpu:.0f}%")
            self.gpu_panel.write(f"  RAM:  {ram:.0f}%")

        # Key status — from cache
        self.keys_panel.clear()
        kd = _cache.get("key_data")
        if kd:
            self.keys_panel.write(f"  Keys loaded: {kd.get('count', 0)}")
            cd = kd.get("cooldown", set())
            if cd:
                self.keys_panel.write(f"  In cooldown: {', '.join(cd)}")
            for name, a in sorted(kd.get("agents", {}).items()):
                self.keys_panel.write(
                    f"  {name:20s} req:{a.get('req',0):>4}  tok:{a.get('tok',0):>6}  "
                    f"rpm:{a.get('rpm',0)}  429s:{a.get('429s',0)}")
        else:
            self.keys_panel.write("  Key manager not available")


# ╔══════════════════════════════════════════════════════════════════╗
# ║  TAB 3: BRAIN                                                  ║
# ╚══════════════════════════════════════════════════════════════════╝

class BrainTab(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.synapse_panel = InfoPanel(self, "\U0001f9ec Synapse Pathways")
        self.synapse_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 4), pady=(0, 4))
        self.phantom_panel = InfoPanel(self, "\U0001f47b Phantom Predictions")
        self.phantom_panel.grid(row=0, column=1, sticky="nsew", padx=(4, 0), pady=(0, 4))
        self.singularity_panel = InfoPanel(self, "\U0001f300 Singularity Engine")
        self.singularity_panel.grid(row=1, column=0, sticky="nsew", padx=(0, 4), pady=(4, 0))
        self.introspect_panel = InfoPanel(self, "\U0001f52d System Introspector")
        self.introspect_panel.grid(row=1, column=1, sticky="nsew", padx=(4, 0), pady=(4, 0))

    def refresh(self):
        # Synapse — from cache
        self.synapse_panel.clear()
        syn_stats = _cache.get("synapse_stats")
        if syn_stats:
            for k, v in syn_stats.items():
                self.synapse_panel.write(f"  {k}: {v}")
            top = _cache.get("synapse_pathways", [])
            if top:
                self.synapse_panel.write("\n  Top pathways:")
                for p in top:
                    self.synapse_panel.write(
                        f"    {p.get('category', '?')} -> {p.get('agent', '?')}: "
                        f"{p.get('strength', 0):.3f}")
        else:
            self.synapse_panel.write("  Synapse: loading...")

        # Phantom — from cache
        self.phantom_panel.clear()
        ph_acc = _cache.get("phantom_accuracy")
        if ph_acc:
            for k, v in ph_acc.items():
                self.phantom_panel.write(f"  {k}: {v}")
            preds = _cache.get("phantom_predictions", [])
            if preds:
                self.phantom_panel.write("\n  Recent predictions:")
                for p in preds:
                    self.phantom_panel.write(f"    {p.get('category', '?')}: {p.get('confidence', 0):.2f}")
        else:
            self.phantom_panel.write("  Phantom: loading...")

        # Singularity — from cache
        self.singularity_panel.clear()
        sing_status = _cache.get("singularity_status")
        if sing_status:
            for k, v in sing_status.items():
                self.singularity_panel.write(f"  {k}: {v}")
        else:
            self.singularity_panel.write("  Singularity: loading...")

        # Introspector — from cache
        self.introspect_panel.clear()
        intro_report = _cache.get("introspector_report")
        if intro_report:
            for k, v in intro_report.items():
                if isinstance(v, dict):
                    self.introspect_panel.write(f"  {k}:")
                    for kk, vv in v.items():
                        self.introspect_panel.write(f"    {kk}: {vv}")
                else:
                    self.introspect_panel.write(f"  {k}: {v}")
        else:
            self.introspect_panel.write("  Introspector: loading...")


# ╔══════════════════════════════════════════════════════════════════╗
# ║  TAB 4: IMMUNE SYSTEM                                          ║
# ╚══════════════════════════════════════════════════════════════════╝

class ImmuneTab(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.blackbox_panel = InfoPanel(self, "\U0001f9ea BlackBox Immune Memory")
        self.blackbox_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 4), pady=(0, 4))
        self.schild_panel = InfoPanel(self, "\U0001f6e1 Hallucination Shield")
        self.schild_panel.grid(row=0, column=1, sticky="nsew", padx=(4, 0), pady=(0, 4))
        self.governor_panel = InfoPanel(self, "\U0001f46e Governor Health")
        self.governor_panel.grid(row=1, column=0, sticky="nsew", padx=(0, 4), pady=(4, 0))
        self.tribunal_panel = InfoPanel(self, "\u2696 Adversarial Tribunal")
        self.tribunal_panel.grid(row=1, column=1, sticky="nsew", padx=(4, 0), pady=(4, 0))

    def refresh(self):
        # BlackBox — from cache
        self.blackbox_panel.clear()
        bb_stats = _cache.get("blackbox_stats")
        if bb_stats:
            for k, v in bb_stats.items():
                self.blackbox_panel.write(f"  {k}: {v}")
            antibodies = _cache.get("blackbox_antibodies", [])
            if antibodies:
                self.blackbox_panel.write(f"\n  Antibodies ({len(antibodies)}):")
                for ab in antibodies[:8]:
                    sig = ab.get("signature", "?")[:40]
                    strength = ab.get("strength", 0)
                    self.blackbox_panel.write(f"    [{strength:.1f}] {sig}")
        else:
            self.blackbox_panel.write("  BlackBox not available")

        # Schild — from cache
        self.schild_panel.clear()
        shield_stats = _cache.get("shield_stats")
        if shield_stats:
            for k, v in shield_stats.items():
                self.schild_panel.write(f"  {k}: {v}")
        else:
            self.schild_panel.write("  Shield not available")

        # Governor — from cache
        self.governor_panel.clear()
        gov_report = _cache.get("governor_health")
        if gov_report:
            for k, v in gov_report.items():
                if isinstance(v, dict):
                    self.governor_panel.write(f"  {k}:")
                    for kk, vv in v.items():
                        self.governor_panel.write(f"    {kk}: {vv}")
                else:
                    self.governor_panel.write(f"  {k}: {v}")
        else:
            self.governor_panel.write("  Governor: loading...")

        # Tribunal — from cache
        self.tribunal_panel.clear()
        trib_stats = _cache.get("tribunal_stats")
        if trib_stats:
            for k, v in trib_stats.items():
                self.tribunal_panel.write(f"  {k}: {v}")
        else:
            self.tribunal_panel.write("  Tribunal not available")


# ╔══════════════════════════════════════════════════════════════════╗
# ║  TAB 5: MEMORY                                                 ║
# ╚══════════════════════════════════════════════════════════════════╝

class MemoryTab(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.events_panel = InfoPanel(self, "\U0001f4dc Recent Events (CorticalStack)")
        self.events_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 4), pady=(0, 4))
        self.dbmetrics_panel = InfoPanel(self, "\U0001f4be DB Metrics")
        self.dbmetrics_panel.grid(row=0, column=1, sticky="nsew", padx=(4, 0), pady=(0, 4))
        self.bus_panel = InfoPanel(self, "\U0001f4e1 NeuralBus Live Stream")
        self.bus_panel.grid(row=1, column=0, sticky="nsew", padx=(0, 4), pady=(4, 0))
        self.facts_panel = InfoPanel(self, "\U0001f9e0 Semantic Facts")
        self.facts_panel.grid(row=1, column=1, sticky="nsew", padx=(4, 0), pady=(4, 0))

    def refresh(self):
        # Events — from cache
        self.events_panel.clear()
        events = _cache.get("cortical_events", [])
        if events:
            for ev in events:
                ts = ev.get("timestamp", "?")
                if isinstance(ts, str) and len(ts) > 19:
                    ts = ts[:19]
                actor = ev.get("actor", "?")
                etype = ev.get("action", "?")
                self.events_panel.write(f"  [{ts}] {actor}: {etype}")
        else:
            self.events_panel.write("  No events")

        # DB Metrics — from cache
        self.dbmetrics_panel.clear()
        db_metrics = _cache.get("cortical_db_metrics")
        if db_metrics:
            for k, v in db_metrics.items():
                self.dbmetrics_panel.write(f"  {k}: {v}")
            cortical_stats = _cache.get("cortical_stats", {})
            if cortical_stats:
                self.dbmetrics_panel.write("\n  Memory stats:")
                for k, v in cortical_stats.items():
                    self.dbmetrics_panel.write(f"    {k}: {v}")
        else:
            self.dbmetrics_panel.write("  CorticalStack: loading...")

        # NeuralBus — from cache
        self.bus_panel.clear()
        bus_stats = _cache.get("bus_stats")
        if bus_stats:
            for k, v in bus_stats.items():
                self.bus_panel.write(f"  {k}: {v}")
            stream = _cache.get("bus_stream", "")
            if stream and isinstance(stream, str):
                self.bus_panel.write("")
                for line in stream.split("\n"):
                    self.bus_panel.write(f"  {line}")
        else:
            self.bus_panel.write("  NeuralBus: loading...")

        # Semantic facts — from cache
        self.facts_panel.clear()
        facts = _cache.get("cortical_facts", [])
        if facts:
            self.facts_panel.write(f"  Total facts: {len(facts)}")
            for f in facts[:20]:
                key = f.get("key", "?")
                val = str(f.get("value", "?"))[:60]
                conf = f.get("confidence", 0)
                self.facts_panel.write(f"  [{conf:.1f}] {key}: {val}")
        else:
            self.facts_panel.write("  No facts")


# ╔══════════════════════════════════════════════════════════════════╗
# ║  TAB 6: OBSERVATORY                                            ║
# ╚══════════════════════════════════════════════════════════════════╝

class ObservatoryTab(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self.models_panel = InfoPanel(self, "\U0001f916 Model Registry")
        self.models_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 4), pady=(0, 4))
        self.leaderboard_panel = InfoPanel(self, "\U0001f3c6 Model Leaderboard")
        self.leaderboard_panel.grid(row=0, column=1, sticky="nsew", padx=(4, 0), pady=(0, 4))
        self.cost_panel = InfoPanel(self, "\U0001f4b0 Cost Analysis")
        self.cost_panel.grid(row=1, column=0, sticky="nsew", padx=(0, 4), pady=4)
        self.config_panel = InfoPanel(self, "\u2699 Config Audit")
        self.config_panel.grid(row=1, column=1, sticky="nsew", padx=(4, 0), pady=4)
        self.auction_panel = InfoPanel(self, "\U0001f3af Auction History")
        self.auction_panel.grid(row=2, column=0, sticky="nsew", padx=(0, 4), pady=(4, 0))
        self.failure_panel = InfoPanel(self, "\u26a0 Failure Analysis")
        self.failure_panel.grid(row=2, column=1, sticky="nsew", padx=(4, 0), pady=(4, 0))

    def refresh(self):
        # Model Registry — from cache
        self.models_panel.clear()
        model_stats = _cache.get("model_stats")
        if model_stats:
            for k, v in model_stats.items():
                self.models_panel.write(f"  {k}: {v}")
            workers = _cache.get("model_workers", [])
            self.models_panel.write(f"\n  Workers ({len(workers)}):")
            for w in workers:
                try:
                    perf = w.get_perf()
                    profile = getattr(w, "profile", None)
                    prov = perf.get("provider", getattr(profile, "provider", "?") if profile else "?")
                    self.models_panel.write(
                        f"    {prov:12s} ok:{perf.get('success_rate', 0):.0%}  "
                        f"lat:{perf.get('avg_latency_ms', 0):.0f}ms")
                except Exception as e:
                    logger.debug("model worker perf: %s", e)
        else:
            self.models_panel.write("  ModelRegistry not available")

        # Leaderboard — from cache
        self.leaderboard_panel.clear()
        lb = _cache.get("leaderboard", [])
        if lb:
            for i, entry in enumerate(lb[:10]):
                name = entry.get("model_id", "?")
                rate = entry.get("success_rate", 0)
                lat = entry.get("avg_latency_ms", 0)
                self.leaderboard_panel.write(
                    f"  #{i + 1} {name:30s} ok:{rate:.0%}  lat:{lat:.0f}ms")
        else:
            self.leaderboard_panel.write("  Observatory not available")

        # Cost — from cache
        self.cost_panel.clear()
        cost = _cache.get("cost_analysis")
        if cost:
            pp = cost.get("per_provider", {})
            if pp:
                self.cost_panel.write("  Per provider:")
                for prov, info in pp.items():
                    if isinstance(info, dict):
                        tok = info.get("tokens", info.get("total_tokens", 0))
                        calls = info.get("calls", 0)
                        self.cost_panel.write(f"    {prov:12s} tok:{tok:>6}  calls:{calls}")
                    else:
                        self.cost_panel.write(f"    {prov}: {info}")
            pm = cost.get("per_model", [])
            if pm:
                self.cost_panel.write(f"\n  Per model (top {min(5, len(pm))}):")
                for m in pm[:5]:
                    if isinstance(m, dict):
                        mid = m.get("model_id", m.get("model", "?"))
                        tok = m.get("total_tokens", 0)
                        self.cost_panel.write(f"    {mid}: {tok} tokens")
                    else:
                        self.cost_panel.write(f"    {m}")
            recs = cost.get("aanbevelingen", [])
            if recs:
                self.cost_panel.write(f"\n  Aanbevelingen:")
                for r in recs[:3]:
                    self.cost_panel.write(f"    {r}")
            if not pp and not pm:
                self.cost_panel.write("  No cost data yet")
        else:
            self.cost_panel.write("  Cost analysis: loading...")

        # Config Audit — from cache
        self.config_panel.clear()
        rapport = _cache.get("config_audit")
        if rapport:
            self.config_panel.write(f"  Veilig: {rapport.veilig}")
            self.config_panel.write(f"  Gecontroleerd: {rapport.gecontroleerd}")
            self.config_panel.write(f"  Drift: {rapport.drift_gedetecteerd}")
            if rapport.schendingen:
                self.config_panel.write(f"\n  Schendingen ({len(rapport.schendingen)}):")
                for s in rapport.schendingen[:8]:
                    self.config_panel.write(f"    [{s.ernst}] {s.beschrijving}")
            else:
                self.config_panel.write("\n  Geen schendingen gevonden")
        else:
            self.config_panel.write("  ConfigAuditor: loading...")

        # Auction History — from cache
        self.auction_panel.clear()
        auctions = _cache.get("auction_history", [])
        if auctions:
            self.auction_panel.write(f"  Recent auctions ({len(auctions)}):")
            for a in auctions[:8]:
                task_id = a.get("task_id", "?")[:16]
                winner = a.get("winner_model", a.get("winner", "?"))
                latency = a.get("latency_ms", 0)
                self.auction_panel.write(
                    f"    {task_id:16s}  \u2192 {winner}  {latency:.0f}ms")
        else:
            self.auction_panel.write("  No auction data yet")

        # Failure Analysis — from cache
        self.failure_panel.clear()
        failures = _cache.get("failure_analysis")
        if failures:
            total_f = failures.get("totaal_failures", 0)
            total_b = failures.get("totaal_barrier_rejections", 0)
            circuits = failures.get("circuit_open_count", 0)
            self.failure_panel.write(f"  Failures: {total_f}  Barrier: {total_b}  Circuits open: {circuits}")
            problemen = failures.get("probleemmodellen", [])
            if problemen:
                self.failure_panel.write(f"\n  Problem models ({len(problemen)}):")
                for p in problemen[:6]:
                    mid = p.get("model_id", "?")
                    fails = p.get("failures", 0)
                    rate = p.get("success_rate", 0)
                    self.failure_panel.write(
                        f"    {mid:30s}  fail:{fails}  ok:{rate:.0%}")
            else:
                self.failure_panel.write("\n  No problem models detected")
        else:
            self.failure_panel.write("  Failure analysis: loading...")


# ╔══════════════════════════════════════════════════════════════════╗
# ║  TAB 7: REAL TERMINAL                                          ║
# ╚══════════════════════════════════════════════════════════════════╝

class RealTerminalTab(ctk.CTkFrame):
    """Echte subprocess terminal (PowerShell op Windows)."""

    def __init__(self, master):
        super().__init__(master, fg_color="transparent")

        # Output
        self._output = ctk.CTkTextbox(
            self, fg_color="#050810", text_color=NEON_GREEN,
            font=("Consolas", 10), border_color=BORDER, border_width=1,
            corner_radius=4, wrap="word", state="disabled",
        )
        self._output.pack(fill="both", expand=True, padx=8, pady=(8, 4))

        # Input row
        inp_frame = ctk.CTkFrame(self, fg_color="transparent")
        inp_frame.pack(fill="x", padx=8, pady=(0, 8))

        # CWD label
        cwd = os.getcwd()
        self._cwd_label = ctk.CTkLabel(
            inp_frame, text=f"{cwd}>",
            font=("Consolas", 10, "bold"), text_color=NEON_CYAN,
        )
        self._cwd_label.pack(side="left", padx=(4, 4))

        self._entry = ctk.CTkEntry(
            inp_frame, fg_color=BG_CARD, text_color=NEON_GREEN,
            font=("Consolas", 10), border_color=BORDER, border_width=1,
            placeholder_text="Type shell command...",
            placeholder_text_color=TEXT_DIM,
        )
        self._entry.pack(side="left", fill="x", expand=True, padx=(0, 4))
        self._entry.bind("<Return>", self._on_enter)

        # History
        self._history = deque(maxlen=100)
        self._hist_idx = -1

        self._entry.bind("<Up>", self._hist_up)
        self._entry.bind("<Down>", self._hist_down)

        self._write("OMEGA SOVEREIGN SHELL v3.0")
        self._write(f"Working directory: {cwd}")
        self._write("Real subprocess execution (PowerShell). Type commands below.\n")

        self._proc = None
        self._cwd = cwd

    def _write(self, text):
        self._output.configure(state="normal")
        self._output.insert("end", text + "\n")
        self._output.see("end")
        self._output.configure(state="disabled")

    def _hist_up(self, _=None):
        if self._history:
            self._hist_idx = min(self._hist_idx + 1, len(self._history) - 1)
            self._entry.delete(0, "end")
            self._entry.insert(0, list(self._history)[-(self._hist_idx + 1)])
        return "break"

    def _hist_down(self, _=None):
        if self._hist_idx > 0:
            self._hist_idx -= 1
            self._entry.delete(0, "end")
            self._entry.insert(0, list(self._history)[-(self._hist_idx + 1)])
        elif self._hist_idx == 0:
            self._hist_idx = -1
            self._entry.delete(0, "end")
        return "break"

    def _on_enter(self, _=None):
        cmd = self._entry.get().strip()
        if not cmd:
            return
        self._entry.delete(0, "end")
        self._history.append(cmd)
        self._hist_idx = -1
        self._write(f"{self._cwd}> {cmd}")

        # Handle cd specially
        if cmd.lower().startswith("cd "):
            target = cmd[3:].strip().strip('"').strip("'")
            try:
                new_cwd = os.path.abspath(os.path.join(self._cwd, target))
                if os.path.isdir(new_cwd):
                    self._cwd = new_cwd
                    self._cwd_label.configure(text=f"{self._cwd}>")
                    self._write(f"Changed to: {self._cwd}")
                else:
                    self._write(f"Directory not found: {new_cwd}")
            except Exception as e:
                self._write(f"Error: {e}")
            self._write("")
            return

        if cmd.lower() == "cls" or cmd.lower() == "clear":
            self._output.configure(state="normal")
            self._output.delete("1.0", "end")
            self._output.configure(state="disabled")
            return

        # Run in background thread
        threading.Thread(target=self._run_cmd, args=(cmd,), daemon=True).start()

    def _run_cmd(self, cmd):
        try:
            # Use powershell on Windows
            if sys.platform == "win32":
                full_cmd = ["powershell", "-NoProfile", "-Command", cmd]
            else:
                full_cmd = ["bash", "-c", cmd]

            proc = subprocess.Popen(
                full_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                cwd=self._cwd, text=True, encoding="utf-8", errors="replace",
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
            )
            self._proc = proc

            for line in proc.stdout:
                line = line.rstrip("\n\r")
                # Schedule GUI update from main thread
                self._output.after(0, self._write, line)

            proc.wait()
            rc = proc.returncode
            if rc != 0:
                self._output.after(0, self._write, f"[Exit code: {rc}]")
            self._output.after(0, self._write, "")
        except Exception as e:
            self._output.after(0, self._write, f"Error: {e}\n")
        finally:
            self._proc = None

    def refresh(self):
        pass  # Terminal doesn't need periodic refresh


# ╔══════════════════════════════════════════════════════════════════╗
# ║  TAB 8: APPS                                                    ║
# ╚══════════════════════════════════════════════════════════════════╝

# Canonical app list — matches danny_toolkit/apps/
_APP_REGISTRY = [
    ("Agenda", "agenda_planner"), ("Boodschappen", "boodschappenlijst"),
    ("Calculator", "rekenmachine"), ("Code Analyse", "code_analyse"),
    ("Code Snippets", "code_snippets"), ("Citaten", "citaten_generator"),
    ("Decision", "decision_maker"), ("Dream Journal", "dream_journal"),
    ("Energie", "energie_vs_tech"), ("Expenses", "expense_tracker"),
    ("Fitness", "fitness_tracker"), ("Flashcards", "flashcards"),
    ("Goals", "goals_tracker"), ("Habits", "habit_tracker"),
    ("Language", "language_tutor"), ("Mood", "mood_tracker"),
    ("Music", "music_composer"), ("Notities", "notitie_app"),
    ("Pomodoro", "pomodoro_timer"), ("Recepten", "recipe_generator"),
    ("Room Plan", "room_planner"), ("Schatzoek", "schatzoek"),
    ("Tijd Info", "tijd_info"), ("Time Capsule", "time_capsule"),
    ("Units", "unit_converter"), ("Pixel", "virtueel_huisdier"),
    ("Wachtwoord", "wachtwoord_generator"), ("Weer", "watchtower"),
    ("Prism", "prism_dashboard"),
]


class AppsTab(ctk.CTkFrame):
    """Tab 8: Grid of 29 app buttons with status indicators."""

    def __init__(self, master):
        super().__init__(master, fg_color="transparent")

        # Title
        ctk.CTkLabel(self, text="\U0001f4e6 APPS ECOSYSTEM (29)",
                     font=FONT_TITLE, text_color=NEON_CYAN).pack(anchor="w", padx=8, pady=(4, 2))

        # Quick actions bar
        bar = ctk.CTkFrame(self, fg_color=BG_PANEL, height=32, corner_radius=6)
        bar.pack(fill="x", padx=4, pady=(0, 4))
        self._quick_lbl = ctk.CTkLabel(bar, text="", font=FONT_MONO_XS, text_color=TEXT_DIM)
        self._quick_lbl.pack(side="left", padx=8)

        # Scrollable grid
        self._scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self._scroll.pack(fill="both", expand=True, padx=4)
        for i in range(6):
            self._scroll.grid_columnconfigure(i, weight=1)

        self._btns = {}
        self._status_labels = {}
        for idx, (label, module) in enumerate(_APP_REGISTRY):
            row, col = divmod(idx, 6)
            card = ctk.CTkFrame(self._scroll, fg_color=BG_CARD, corner_radius=8,
                                border_width=1, border_color=BORDER)
            card.grid(row=row, column=col, padx=3, pady=3, sticky="nsew")
            card.grid_columnconfigure(0, weight=1)

            btn = ctk.CTkButton(
                card, text=label, font=FONT_MONO_SM,
                fg_color="transparent", hover_color="#1a3a5c",
                text_color=TEXT_PRIMARY, height=28,
                command=lambda m=module: self._launch_app(m),
            )
            btn.grid(row=0, column=0, sticky="ew", padx=4, pady=(4, 0))

            status = ctk.CTkLabel(card, text="\u25cb", font=FONT_MONO_XS, text_color=TEXT_DIM)
            status.grid(row=1, column=0, pady=(0, 4))
            self._btns[module] = btn
            self._status_labels[module] = status

    def _launch_app(self, module_name):
        """Launch app via brain.process_request()."""
        brain = _load_brain()
        if not brain:
            return
        threading.Thread(
            target=lambda: brain.process_request(f"open {module_name}"),
            daemon=True,
        ).start()

    def refresh(self):
        # Check data file presence for each app
        active = 0
        for label, module in _APP_REGISTRY:
            lbl = self._status_labels.get(module)
            if not lbl:
                continue
            try:
                from danny_toolkit.core.config import Config
                data_file = Config.DATA_DIR / "apps" / f"{module}.json"
                if data_file.exists():
                    lbl.configure(text="\u25cf", text_color=NEON_GREEN)
                    active += 1
                else:
                    lbl.configure(text="\u25cb", text_color=TEXT_DIM)
            except Exception:
                lbl.configure(text="\u25cb", text_color=TEXT_DIM)
        self._quick_lbl.configure(text=f"Active: {active}/{len(_APP_REGISTRY)} apps with data")


# ╔══════════════════════════════════════════════════════════════════╗
# ║  TAB 9: MAINTENANCE                                             ║
# ╚══════════════════════════════════════════════════════════════════╝

class MaintenanceTab(ctk.CTkFrame):
    """Tab 9: Dreamer REM, DevOpsDaemon CI, GhostWriter AST, Shadow Governance."""

    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.dreamer_panel = InfoPanel(self, "\U0001f4a4 Dreamer REM Cycle")
        self.dreamer_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 4), pady=(0, 4))
        self.devops_panel = InfoPanel(self, "\u2699 DevOpsDaemon CI")
        self.devops_panel.grid(row=0, column=1, sticky="nsew", padx=(4, 0), pady=(0, 4))
        self.ghost_panel = InfoPanel(self, "\U0001f47b GhostWriter + Amplifier")
        self.ghost_panel.grid(row=1, column=0, sticky="nsew", padx=(0, 4), pady=(4, 0))
        self.shadow_panel = InfoPanel(self, "\U0001f3ad Shadow Governance")
        self.shadow_panel.grid(row=1, column=1, sticky="nsew", padx=(4, 0), pady=(4, 0))

    def refresh(self):
        # Dreamer
        self.dreamer_panel.clear()
        ds = _cache.get("dreamer_stats")
        if ds:
            self.dreamer_panel.write(f"  Next REM: {ds.get('next_run', '04:00')}")
            last = ds.get("last_cycle")
            if last:
                self.dreamer_panel.write(f"  Last cycle: {last}")
            self.dreamer_panel.write(f"  Backup OK: {ds.get('backup_ok', '?')}")
            rem = ds.get("last_rem")
            if rem and isinstance(rem, dict):
                for k, v in list(rem.items())[:8]:
                    self.dreamer_panel.write(f"  {k}: {v}")
            elif rem:
                self.dreamer_panel.write(f"  {str(rem)[:200]}")
        else:
            self.dreamer_panel.write("  Dreamer: loading...")

        # DevOps
        self.devops_panel.clear()
        devs = _cache.get("devops_stats")
        if devs:
            for k, v in devs.items():
                if isinstance(v, dict):
                    self.devops_panel.write(f"  {k}:")
                    for kk, vv in list(v.items())[:5]:
                        self.devops_panel.write(f"    {kk}: {vv}")
                else:
                    self.devops_panel.write(f"  {k}: {v}")
        else:
            self.devops_panel.write("  DevOps: loading...")

        # GhostWriter + Amplifier
        self.ghost_panel.clear()
        gw = _cache.get("ghost_writer_stats")
        if gw:
            self.ghost_panel.write("  [GhostWriter]")
            for k, v in gw.items():
                self.ghost_panel.write(f"    {k}: {v}")
        else:
            self.ghost_panel.write("  GhostWriter: no data")
        ga = _cache.get("ghost_amplifier_stats")
        if ga:
            self.ghost_panel.write("  [GhostAmplifier]")
            for k, v in ga.items():
                self.ghost_panel.write(f"    {k}: {v}")

        # Shadow Governance
        self.shadow_panel.clear()
        sg = _cache.get("shadow_status")
        if sg:
            for k, v in sg.items():
                if isinstance(v, dict):
                    self.shadow_panel.write(f"  {k}:")
                    for kk, vv in list(v.items())[:6]:
                        color = NEON_RED if "ROOD" in str(vv) else (
                            NEON_YELLOW if "GEEL" in str(vv) else NEON_GREEN)
                        self.shadow_panel.write(f"    {kk}: {vv}")
                elif isinstance(v, list):
                    self.shadow_panel.write(f"  {k}: {len(v)} items")
                else:
                    self.shadow_panel.write(f"  {k}: {v}")
        else:
            self.shadow_panel.write("  Shadow: loading...")


# ╔══════════════════════════════════════════════════════════════════╗
# ║  TAB 10: PREDICTIONS                                            ║
# ╚══════════════════════════════════════════════════════════════════╝

class PredictionsTab(ctk.CTkFrame):
    """Tab 10: OracleEye forecasts, Phantom predictions, trend charts."""

    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.oracle_panel = InfoPanel(self, "\U0001f52e OracleEye Forecasts")
        self.oracle_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 4), pady=(0, 4))
        self.phantom_panel = InfoPanel(self, "\U0001f47b Phantom Predictions")
        self.phantom_panel.grid(row=0, column=1, sticky="nsew", padx=(4, 0), pady=(0, 4))
        self.trends_panel = InfoPanel(self, "\U0001f4c8 Trend Data")
        self.trends_panel.grid(row=1, column=0, sticky="nsew", padx=(0, 4), pady=(4, 0))
        self.mirror_panel = InfoPanel(self, "\U0001fa9e TheMirror Profile")
        self.mirror_panel.grid(row=1, column=1, sticky="nsew", padx=(4, 0), pady=(4, 0))

    def refresh(self):
        # OracleEye
        self.oracle_panel.clear()
        preds = _cache.get("oracle_predictions")
        peaks = _cache.get("oracle_peaks")
        if preds:
            self.oracle_panel.write("  Next 4h forecast:")
            for f in preds:
                self.oracle_panel.write(
                    f"    H+{f.get('hour', '?')}: CPU={f.get('cpu', '?'):.0f}%"
                    f" RAM={f.get('ram', '?'):.0f}% Q={f.get('queries', '?'):.0f}")
            if peaks:
                self.oracle_panel.write(f"  Peak hours: {peaks}")
        else:
            self.oracle_panel.write("  OracleEye: loading...")

        # Phantom
        self.phantom_panel.clear()
        ph_acc = _cache.get("phantom_accuracy")
        ph_pred = _cache.get("phantom_predictions")
        if ph_acc:
            for k, v in ph_acc.items():
                self.phantom_panel.write(f"  {k}: {v}")
        if ph_pred:
            self.phantom_panel.write(f"\n  Active predictions ({len(ph_pred)}):")
            for p in ph_pred[:5]:
                if isinstance(p, dict):
                    what = p.get("prediction", p.get("what", "?"))[:50]
                    conf = p.get("confidence", "?")
                    self.phantom_panel.write(f"    [{conf}] {what}")
                else:
                    self.phantom_panel.write(f"    {str(p)[:60]}")
        if not ph_acc and not ph_pred:
            self.phantom_panel.write("  Phantom: loading...")

        # Trends
        self.trends_panel.clear()
        td = _cache.get("trend_data")
        if td:
            if isinstance(td, dict):
                for k, v in list(td.items())[:10]:
                    if isinstance(v, list):
                        self.trends_panel.write(f"  {k}: {len(v)} points")
                    else:
                        self.trends_panel.write(f"  {k}: {v}")
            elif isinstance(td, list):
                for item in td[:10]:
                    self.trends_panel.write(f"  {item}")
        else:
            self.trends_panel.write("  Trends: loading...")

        # Mirror profile
        self.mirror_panel.clear()
        mp = _cache.get("mirror_profile")
        if mp and isinstance(mp, dict):
            for k, v in list(mp.items())[:12]:
                val = str(v)[:60] if not isinstance(v, (dict, list)) else f"({type(v).__name__})"
                self.mirror_panel.write(f"  {k}: {val}")
        else:
            self.mirror_panel.write("  Mirror: no profile data")


# ╔══════════════════════════════════════════════════════════════════╗
# ║  MAIN APPLICATION                                              ║
# ╚══════════════════════════════════════════════════════════════════╝

class OmegaSovereignApp(ctk.CTk):
    REFRESH_MS = 1000

    def __init__(self):
        super().__init__()
        self.title("\u2126 OMEGA SOVEREIGN DASHBOARD v3.0")
        self.geometry("1500x950")
        self.minsize(1200, 750)
        self.configure(fg_color=BG_DEEP)
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # ── Header ──
        header = ctk.CTkFrame(self, fg_color="transparent", height=45)
        header.pack(fill="x", padx=20, pady=(8, 2))
        ctk.CTkLabel(header, text="\u2126 SOVEREIGN CORE",
                      font=("Consolas", 9), text_color=NEON_CYAN).pack(side="left")
        ctk.CTkLabel(header, text="O M E G A   D A S H B O A R D   v 2 . 0",
                      font=("Consolas", 18, "bold"), text_color=NEON_CYAN
                      ).pack(side="left", expand=True)
        self._clock = ctk.CTkLabel(header, text="", font=FONT_MONO_SM, text_color=TEXT_DIM)
        self._clock.pack(side="right")

        # ── Glow line ──
        ctk.CTkFrame(self, height=2, fg_color=NEON_CYAN).pack(fill="x", padx=20, pady=(2, 4))

        # ── Tabview ──
        self._tabs = ctk.CTkTabview(
            self, fg_color=BG_DEEP, segmented_button_fg_color=BG_PANEL,
            segmented_button_selected_color="#1a3a5c",
            segmented_button_selected_hover_color="#1e4470",
            segmented_button_unselected_color=BG_CARD,
            segmented_button_unselected_hover_color="#1a2332",
            text_color=NEON_CYAN, corner_radius=8,
        )
        self._tabs.pack(fill="both", expand=True, padx=10, pady=(0, 2))

        # Add tabs
        tab_names = [
            "\u2126 Dashboard", "\U0001f916 Agents", "\U0001f9e0 Brain",
            "\U0001f6e1 Immune", "\U0001f4be Memory",
            "\U0001f52d Observatory", "\U0001f4bb Terminal",
            "\U0001f4e6 Apps", "\U0001f527 Maintenance", "\U0001f52e Predictions",
        ]
        for name in tab_names:
            self._tabs.add(name)

        # Build tab contents
        self.tab_dashboard = DashboardTab(self._tabs.tab(tab_names[0]))
        self.tab_dashboard.pack(fill="both", expand=True)
        self.tab_agents = AgentsTab(self._tabs.tab(tab_names[1]))
        self.tab_agents.pack(fill="both", expand=True)
        self.tab_brain = BrainTab(self._tabs.tab(tab_names[2]))
        self.tab_brain.pack(fill="both", expand=True)
        self.tab_immune = ImmuneTab(self._tabs.tab(tab_names[3]))
        self.tab_immune.pack(fill="both", expand=True)
        self.tab_memory = MemoryTab(self._tabs.tab(tab_names[4]))
        self.tab_memory.pack(fill="both", expand=True)
        self.tab_observatory = ObservatoryTab(self._tabs.tab(tab_names[5]))
        self.tab_observatory.pack(fill="both", expand=True)
        self.tab_terminal = RealTerminalTab(self._tabs.tab(tab_names[6]))
        self.tab_terminal.pack(fill="both", expand=True)
        self.tab_apps = AppsTab(self._tabs.tab(tab_names[7]))
        self.tab_apps.pack(fill="both", expand=True)
        self.tab_maintenance = MaintenanceTab(self._tabs.tab(tab_names[8]))
        self.tab_maintenance.pack(fill="both", expand=True)
        self.tab_predictions = PredictionsTab(self._tabs.tab(tab_names[9]))
        self.tab_predictions.pack(fill="both", expand=True)

        self._tab_map = {
            tab_names[0]: self.tab_dashboard,
            tab_names[1]: self.tab_agents,
            tab_names[2]: self.tab_brain,
            tab_names[3]: self.tab_immune,
            tab_names[4]: self.tab_memory,
            tab_names[5]: self.tab_observatory,
            tab_names[6]: self.tab_terminal,
            tab_names[7]: self.tab_apps,
            tab_names[8]: self.tab_maintenance,
            tab_names[9]: self.tab_predictions,
        }
        self._tab_names = tab_names

        # ── Panel Registry (panels available via "+" picker) ──
        self._panel_registry = []

        def _make_updater(cache_key):
            """Generic cache-to-panel updater."""
            def updater(panel):
                panel.clear()
                data = _cache.get(cache_key)
                if data is None:
                    panel.write("  Loading...")
                    return
                if isinstance(data, dict):
                    for k, v in data.items():
                        if isinstance(v, dict):
                            panel.write(f"  {k}:")
                            for kk, vv in list(v.items())[:8]:
                                panel.write(f"    {kk}: {vv}")
                        else:
                            panel.write(f"  {k}: {v}")
                elif isinstance(data, list):
                    for item in data[:15]:
                        if isinstance(item, dict):
                            parts = [f"{k}={v}" for k, v in list(item.items())[:3]]
                            panel.write(f"  {', '.join(parts)}")
                        else:
                            panel.write(f"  {item}")
                else:
                    panel.write(f"  {data}")
            return updater

        def _reg(pid, title, tab, cache_key):
            fn = _make_updater(cache_key)
            self._panel_registry.append(PanelDescriptor(
                pid, title, tab,
                create_fn=lambda parent, t=title: InfoPanel(parent, t),
                update_fn=fn))

        # Agents
        _reg("agents.health", "Agent Health Report", "Agents", "waakhuis_rapport")
        _reg("agents.circuits", "Circuit Breakers", "Agents", "circuit_state")
        _reg("agents.gpu", "GPU / VRAM Status", "Agents", "vram")
        _reg("agents.metrics", "Pipeline Metrics", "Agents", "engine_stats")
        _reg("agents.keys", "API Key Status", "Agents", "key_data")
        # Brain
        _reg("brain.synapse", "Synapse Pathways", "Brain", "synapse_stats")
        _reg("brain.phantom", "Phantom Predictions", "Brain", "phantom_accuracy")
        _reg("brain.singularity", "Singularity Engine", "Brain", "singularity_status")
        _reg("brain.introspector", "System Introspector", "Brain", "introspector_report")
        # Immune
        _reg("immune.blackbox", "BlackBox Immune Memory", "Immune", "blackbox_stats")
        _reg("immune.shield", "Hallucination Shield", "Immune", "shield_stats")
        _reg("immune.governor", "Governor Health", "Immune", "governor_health")
        _reg("immune.tribunal", "Adversarial Tribunal", "Immune", "tribunal_stats")
        # Memory
        _reg("memory.events", "Recent Events", "Memory", "cortical_events")
        _reg("memory.db", "DB Metrics", "Memory", "cortical_db_metrics")
        _reg("memory.bus", "NeuralBus Stream", "Memory", "bus_stats")
        _reg("memory.facts", "Semantic Facts", "Memory", "cortical_facts")
        # Observatory
        _reg("observatory.models", "Model Registry", "Observatory", "model_stats")
        _reg("observatory.leaderboard", "Model Leaderboard", "Observatory", "leaderboard")
        _reg("observatory.cost", "Cost Analysis", "Observatory", "cost_analysis")
        _reg("observatory.config", "Config Audit", "Observatory", "config_audit")
        _reg("observatory.auctions", "Auction History", "Observatory", "auction_history")
        _reg("observatory.failures", "Failure Analysis", "Observatory", "failure_analysis")
        _reg("observatory.trends", "Trend Data", "Observatory", "trend_data")
        # Maintenance
        _reg("maintenance.dreamer", "Dreamer REM Cycle", "Maintenance", "dreamer_stats")
        _reg("maintenance.devops", "DevOpsDaemon CI", "Maintenance", "devops_stats")
        _reg("maintenance.ghostwriter", "GhostWriter Stats", "Maintenance", "ghost_writer_stats")
        _reg("maintenance.shadow", "Shadow Governance", "Maintenance", "shadow_status")
        # Predictions
        _reg("predictions.oracle", "OracleEye Forecasts", "Predictions", "oracle_predictions")
        _reg("predictions.phantom", "Phantom Accuracy", "Predictions", "phantom_accuracy")
        _reg("predictions.trends", "Trend Charts", "Predictions", "trend_data")
        _reg("predictions.mirror", "TheMirror Profile", "Predictions", "mirror_profile")

        # ── Bottom glow + status ──
        ctk.CTkFrame(self, height=2, fg_color=NEON_CYAN).pack(fill="x", padx=20, pady=(2, 0))
        bar = ctk.CTkFrame(self, fg_color=BG_PANEL, height=26, corner_radius=0)
        bar.pack(fill="x", side="bottom")
        self._status = ctk.CTkLabel(bar, text="\u25cf INITIALIZING...",
                                     font=FONT_MONO_XS, text_color=NEON_GREEN)
        self._status.pack(side="left", padx=10)
        self._ai_lbl = ctk.CTkLabel(bar, text="AI: --",
                                     font=FONT_MONO_XS, text_color=TEXT_DIM)
        self._ai_lbl.pack(side="left", padx=8)
        self._hw = ctk.CTkLabel(bar, text="", font=FONT_MONO_XS, text_color=TEXT_DIM)
        self._hw.pack(side="left", padx=12)
        self._shield_lbl = ctk.CTkLabel(bar, text="", font=FONT_MONO_XS, text_color=TEXT_DIM)
        self._shield_lbl.pack(side="left", padx=8)
        self._bus_lbl = ctk.CTkLabel(bar, text="", font=FONT_MONO_XS, text_color=TEXT_DIM)
        self._bus_lbl.pack(side="left", padx=8)
        self._health_lbl = ctk.CTkLabel(bar, text="", font=FONT_MONO_XS, text_color=TEXT_DIM)
        self._health_lbl.pack(side="left", padx=8)
        self._wav_lbl = ctk.CTkLabel(bar, text="", font=FONT_MONO_XS, text_color=TEXT_DIM)
        self._wav_lbl.pack(side="left", padx=8)
        self._tribunal_lbl = ctk.CTkLabel(bar, text="", font=FONT_MONO_XS, text_color=TEXT_DIM)
        self._tribunal_lbl.pack(side="left", padx=8)
        self._cooldown_lbl = ctk.CTkLabel(bar, text="", font=FONT_MONO_XS, text_color=TEXT_DIM)
        self._cooldown_lbl.pack(side="left", padx=8)
        self._config_lbl = ctk.CTkLabel(bar, text="", font=FONT_MONO_XS, text_color=TEXT_DIM)
        self._config_lbl.pack(side="left", padx=8)
        self._time = ctk.CTkLabel(bar, text="", font=FONT_MONO_XS, text_color=TEXT_DIM)
        self._time.pack(side="right", padx=10)
        self._uptime_lbl = ctk.CTkLabel(bar, text="", font=FONT_MONO_XS, text_color=TEXT_DIM)
        self._uptime_lbl.pack(side="right", padx=8)
        self._start_time = time.time()

        # ── Keyboard shortcuts (Ctrl+1..9 for tabs 1-9, Ctrl+0 for tab 10) ──
        for i, name in enumerate(tab_names):
            key = (i + 1) if i < 9 else 0  # tab 10 → Ctrl+0
            self.bind(f"<Control-Key-{key}>",
                      lambda e, n=name: self._tabs.set(n))
        # F5 / Ctrl+R: force refresh
        self.bind("<F5>", lambda e: self._do_refresh())
        self.bind("<Control-r>", lambda e: self._do_refresh())
        # Ctrl+Tab / Ctrl+Shift+Tab: cycle tabs
        self.bind("<Control-Tab>", lambda e: self._cycle_tab(1))
        self.bind("<Control-Shift-Tab>", lambda e: self._cycle_tab(-1))
        # Escape: focus Omega terminal entry
        self.bind("<Escape>", lambda e: self._focus_omega_entry())

        # ── Initial load ──
        self.after(500, self._initial_load)
        self._schedule_refresh()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _cycle_tab(self, direction):
        """Cycle through tabs. direction: +1 forward, -1 backward."""
        current = self._tabs.get()
        try:
            idx = self._tab_names.index(current)
        except ValueError:
            idx = 0
        new_idx = (idx + direction) % len(self._tab_names)
        self._tabs.set(self._tab_names[new_idx])

    def _focus_omega_entry(self):
        """Focus the Omega terminal input entry."""
        self._tabs.set(self._tab_names[0])
        self.tab_dashboard._ot_entry.focus_set()

    def _initial_load(self):
        """Load SwarmEngine + CentralBrain + start data cache on startup."""
        _cache.start(interval=1.0)
        self.tab_dashboard.update_vanguard()
        # Pre-load CentralBrain in background so first AI question is fast
        threading.Thread(target=_load_brain, daemon=True).start()
        # Pre-warm Ollama into VRAM (cold start takes ~30s otherwise)
        threading.Thread(
            target=lambda: _ollama_verify("ok", timeout=60),
            daemon=True,
        ).start()
        # Periodic VRAM keepalive — prevents Ollama from unloading model after 5min idle
        self._start_vram_keepalive()
        # Launch Zesde Zintuig TUI in separate terminal
        self._launch_zintuig()

    def _start_vram_keepalive(self):
        """Ping Ollama every 4 min to keep model loaded in VRAM."""
        self._vram_alive = True
        def _keepalive_loop():
            import json, urllib.request
            while self._vram_alive:
                time.sleep(240)  # 4 minutes
                if not self._vram_alive:
                    break
                try:
                    data = json.dumps({
                        "model": "llava:latest",
                        "prompt": "ping",
                        "stream": False,
                        "keep_alive": "30m",
                        "options": {"num_predict": 1},
                    }).encode()
                    req = urllib.request.Request(
                        "http://localhost:11434/api/generate",
                        data, {"Content-Type": "application/json"})
                    urllib.request.urlopen(req, timeout=30)
                except Exception as e:
                    logger.debug("VRAM keepalive failed: %s", e)
        threading.Thread(target=_keepalive_loop, daemon=True).start()

    def _launch_zintuig(self):
        """Launch Zesde Zintuig TUI in a separate terminal window."""
        try:
            python = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "venv311", "Scripts", "python.exe",
            )
            script = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "run_zintuig.py",
            )
            if not os.path.isfile(script):
                logger.debug("run_zintuig.py not found, skipping")
                return
            self._zintuig_proc = subprocess.Popen(
                [python, script],
                creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0,
            )
            logger.info("Zesde Zintuig launched (PID %s)", self._zintuig_proc.pid)
        except Exception as e:
            logger.debug("Zintuig launch failed: %s", e)
            self._zintuig_proc = None

    def _on_close(self):
        """Clean shutdown — stop keepalive, stop cache, kill Zintuig, destroy window."""
        self._vram_alive = False
        _cache.stop()
        # Terminate Zesde Zintuig if running
        proc = getattr(self, "_zintuig_proc", None)
        if proc and proc.poll() is None:
            proc.terminate()
            logger.info("Zesde Zintuig terminated")
        self.destroy()

    def _schedule_refresh(self):
        try:
            self._do_refresh()
        except Exception as e:
            logger.debug("Refresh error: %s", e)
        self.after(self.REFRESH_MS, self._schedule_refresh)

    def _do_refresh(self):
        now = datetime.now()
        self._clock.configure(text=now.strftime("%Y-%m-%d %H:%M:%S"))
        self._time.configure(text=f"\u2126 SOVEREIGN // {now.strftime('%H:%M:%S')}")

        # Status bar — from cache
        engine_stats = _cache.get("engine_stats")
        brain = _brain_cache
        if engine_stats:
            q = engine_stats.get('queries_processed', 0)
            a = engine_stats.get('active_agents', 0)
            self._status.configure(
                text=f"\u25cf ONLINE | {a} agents | {q} queries",
                text_color=NEON_GREEN)
        else:
            self._status.configure(text="\u25cb OFFLINE", text_color=NEON_RED)

        # AI status
        if brain:
            tools = len(getattr(brain, '_tools', getattr(brain, 'tools', [])))
            self._ai_lbl.configure(text=f"AI:ON ({tools} tools)", text_color=NEON_GREEN)
        elif _brain_lock.locked():
            self._ai_lbl.configure(text="AI:loading...", text_color=NEON_YELLOW)
        else:
            self._ai_lbl.configure(text="AI:OFF", text_color=NEON_RED)

        # Uptime
        uptime_s = int(time.time() - self._start_time)
        m, s_r = divmod(uptime_s, 60)
        h, m = divmod(m, 60)
        self._uptime_lbl.configure(text=f"UP {h:02d}:{m:02d}:{s_r:02d}")

        cpu = _cache.get("cpu")
        ram = _cache.get("ram")
        if cpu is not None and ram is not None:
            cpu_color = NEON_GREEN if cpu < 60 else (NEON_ORANGE if cpu < 85 else NEON_RED)
            hw_text = f"CPU {cpu:.0f}% | RAM {ram:.0f}%"
            vr = _cache.get("vram")
            if vr and vr.get("beschikbaar"):
                totaal = vr['totaal_mb'] or 1
                pct = round(vr['in_gebruik_mb'] / totaal * 100)
                hw_text += f" | GPU {pct}%"
            self._hw.configure(text=hw_text, text_color=cpu_color)

        # Shield status
        shield_stats = _cache.get("shield_stats")
        if shield_stats:
            checked = shield_stats.get("beoordeeld", 0)
            blocked = shield_stats.get("geblokkeerd", 0)
            sc = NEON_GREEN if blocked == 0 else NEON_RED
            self._shield_lbl.configure(text=f"S:{checked}/{blocked}blk", text_color=sc)

        # Bus events
        bus_stats = _cache.get("bus_stats")
        if bus_stats:
            ev = bus_stats.get("events_gepubliceerd", 0)
            self._bus_lbl.configure(text=f"Bus:{ev}ev", text_color=NEON_CYAN)

        # System health from introspector
        intro = _cache.get("introspector_report")
        if intro:
            hp = intro.get("gezondheid_score", 0)
            ma = intro.get("modules_actief", 0)
            hc = NEON_GREEN if hp >= 80 else (NEON_ORANGE if hp >= 50 else NEON_RED)
            self._health_lbl.configure(text=f"{ma}mod {hp:.0f}%", text_color=hc)

        # WAV stats + OMEGA indicator
        wq = _wav_stats["queries"]
        if _omega_mode["active"]:
            oq = _omega_mode["omega_queries"]
            ok = len(_omega_mode["systems_ok"])
            self._wav_lbl.configure(
                text=f"OMEGA:{ok}sys {oq}q" + (f" WAV:{wq}q" if wq > 0 else ""),
                text_color=NEON_PURPLE)
        elif wq > 0:
            avg_t = _wav_stats["total_time"] / wq
            self._wav_lbl.configure(text=f"WAV:{wq}q {avg_t:.1f}s", text_color=NEON_GREEN)

        # Tribunal verdicts
        trib_stats = _cache.get("tribunal_stats")
        if trib_stats:
            verdicts = trib_stats.get("verdicts", trib_stats.get("total", 0))
            self._tribunal_lbl.configure(text=f"T:{verdicts}v", text_color=NEON_PURPLE)

        # Cooldown agents
        kd = _cache.get("key_data")
        if kd:
            cd = kd.get("cooldown", set())
            if cd:
                self._cooldown_lbl.configure(
                    text=f"CD:{len(cd)}", text_color=NEON_ORANGE)
            else:
                self._cooldown_lbl.configure(text="CD:0", text_color=NEON_GREEN)

        # Config audit status
        config_audit = _cache.get("config_audit")
        if config_audit:
            schendingen = getattr(config_audit, 'schendingen', None)
            n_viol = len(schendingen) if schendingen else 0
            if n_viol > 0:
                self._config_lbl.configure(text=f"CFG:{n_viol}!", text_color=NEON_RED)
            else:
                self._config_lbl.configure(text="CFG:OK", text_color=NEON_GREEN)

        # Refresh active tab only (performance)
        active = self._tabs.get()
        tab = self._tab_map.get(active)
        if tab:
            tab.refresh()

        # Also refresh dashboard if it has floating panels (charts need updating)
        if active != self._tab_names[0]:
            db = self.tab_dashboard
            has_floating = any(
                getattr(p, '_float_window', None)
                for p in [db.vanguard, db.cortex_panel, db.omega_term,
                          db.pulse_panel, db.fuel_panel, db.listener_panel,
                          db._mini_events, db._mini_circuits, db._mini_immune]
            )
            if has_floating or db._extra_panels:
                db.refresh()


# ── ENTRY POINT ──────────────────────────────────────────────────

if __name__ == "__main__":
    app = OmegaSovereignApp()
    app.mainloop()
