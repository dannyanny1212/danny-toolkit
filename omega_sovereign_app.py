"""
OMEGA SOVEREIGN APP -- Native Desktop Dashboard v2.0
=====================================================

Standalone desktop applicatie (CustomTkinter + matplotlib).
7-tab neon dashboard met het volledige Omega ecosystem:

  Tab 1: DASHBOARD   — 6-panel overzicht (Vanguard, Cortex, Pulse, Fuel, Omega Terminal, Listener)
  Tab 2: AGENTS      — Per-agent health, circuit breakers, pipeline metrics, routing
  Tab 3: BRAIN       — Cortex graph, Synapse pathways, Phantom predictions, Singularity
  Tab 4: IMMUNE      — BlackBox antibodies, HallucinatieSchild, Governor, Tribunal
  Tab 5: MEMORY      — CorticalStack events, DB metrics, semantic recall
  Tab 6: OBSERVATORY — Model leaderboard, auction history, provider health, cost analysis
  Tab 7: TERMINAL    — Real subprocess shell (PowerShell/bash)

Gebruik: python omega_sovereign_app.py
"""

import io
import os
import sys
import math
import time
import logging
import threading
import subprocess
from datetime import datetime
from collections import deque
from contextlib import redirect_stdout

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
        """Fetch all data sources in background — UI never blocks."""
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
            except Exception:
                pass
            try:
                self.put("swarm_metrics", dict(eng._swarm_metrics))
            except Exception:
                pass

        # Waakhuis
        if HAS_WAAKHUIS:
            try:
                wh = get_waakhuis()
                self.put("waakhuis_rapport", wh.gezondheidsrapport())
                self.put("hardware_status", wh.hardware_status())
            except Exception:
                pass

        # NeuralBus
        if HAS_BUS:
            try:
                bus = get_bus()
                self.put("bus_stats", bus.statistieken())
                self.put("bus_stream", bus.get_context_stream(count=15))
                with bus._lock:
                    types = list(bus._history.keys())
                counts = []
                for et in types[:20]:
                    counts.append(len(bus.get_history(et, count=100)))
                self.put("bus_event_counts", counts)
            except Exception:
                pass

        # CorticalStack
        if HAS_CORTICAL:
            try:
                stack = get_cortical_stack()
                self.put("cortical_events", stack.get_recent_events(count=25))
                self.put("cortical_db_metrics", stack.get_db_metrics())
                self.put("cortical_stats", stack.get_stats())
                self.put("cortical_facts", stack.recall_all())
            except Exception:
                pass

        # BlackBox
        if HAS_BLACKBOX:
            try:
                bb = get_black_box()
                self.put("blackbox_stats", bb.get_stats())
                self.put("blackbox_antibodies", bb.get_antibodies())
            except Exception:
                pass

        # Shield
        if HAS_SCHILD:
            try:
                self.put("shield_stats", get_hallucination_shield().get_stats())
            except Exception:
                pass

        # Tribunal
        if HAS_TRIBUNAL:
            try:
                self.put("tribunal_stats", get_adversarial_tribunal().get_stats())
            except Exception:
                pass

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
                except Exception:
                    key_data["cooldown"] = set()
                rpm_limit = getattr(km, 'RPM_LIMIT', 30) * max(1, len(km._keys))
                tpm_limit = getattr(km, 'TPM_LIMIT', 30000) * max(1, len(km._keys))
                key_data["rpm_limit"] = rpm_limit
                key_data["tpm_limit"] = tpm_limit
                self.put("key_data", key_data)
            except Exception:
                pass

        # Circuit breakers
        if eng:
            try:
                from swarm_engine import get_circuit_state
                self.put("circuit_state", get_circuit_state())
            except Exception:
                pass

        # GPU
        try:
            from danny_toolkit.core.vram_manager import vram_rapport
            self.put("vram", vram_rapport())
        except Exception:
            pass

        # Model Registry
        if HAS_MODELS:
            try:
                reg = get_model_registry()
                self.put("model_stats", reg.get_stats())
                self.put("model_workers", reg.get_all_workers())
            except Exception:
                pass

        # Observatory
        if HAS_OBSERVATORY:
            try:
                obs = get_observatory_sync()
                self.put("leaderboard", obs.get_model_leaderboard())
                self.put("cost_analysis", obs.get_cost_analysis())
            except Exception:
                pass

        # Brain: Synapse
        try:
            if not hasattr(self, '_synapse'):
                from danny_toolkit.brain.synapse import TheSynapse
                self._synapse = TheSynapse()
            syn = self._synapse
            self.put("synapse_stats", syn.get_stats())
            self.put("synapse_pathways", syn.get_top_pathways(limit=10))
        except Exception:
            pass

        # Brain: Phantom
        try:
            if not hasattr(self, '_phantom'):
                from danny_toolkit.brain.phantom import ThePhantom
                self._phantom = ThePhantom()
            self.put("phantom_accuracy", self._phantom.get_accuracy())
            self.put("phantom_predictions", self._phantom.get_predictions(max_results=5))
        except Exception:
            pass

        # Brain: Singularity
        try:
            if not hasattr(self, '_singularity'):
                from danny_toolkit.brain.singularity import SingularityEngine
                self._singularity = SingularityEngine()
            self.put("singularity_status", self._singularity.get_status())
        except Exception:
            pass

        # Brain: Introspector
        if HAS_INTROSPECTOR:
            try:
                self.put("introspector_report", get_introspector().get_health_report())
            except Exception:
                pass

        # Immune: Governor
        try:
            if not hasattr(self, '_governor'):
                from danny_toolkit.brain.governor import OmegaGovernor
                self._governor = OmegaGovernor()
            self.put("governor_health", self._governor.get_health_report())
        except Exception:
            pass

        # Config Auditor
        try:
            from danny_toolkit.brain.config_auditor import get_config_auditor
            self.put("config_audit", get_config_auditor().audit())
        except Exception:
            pass


_cache = _DataCache()


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
        ("SwarmEngine", "danny_toolkit.core.swarm_engine", "SwarmEngine"),
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
    results["_samenvatting"] = {"totaal": len(results) - 1, "ok": ok, "fout": fout}

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
    def __init__(self, master, title, **kw):
        super().__init__(master, fg_color=BG_PANEL, border_color=BORDER,
                         border_width=1, corner_radius=8, **kw)
        ctk.CTkLabel(self, text=f"  {title.upper()}",
                      font=("Consolas", 10, "bold"),
                      text_color=NEON_CYAN, anchor="w"
                      ).pack(fill="x", padx=8, pady=(6, 2))
        ctk.CTkFrame(self, height=1, fg_color=BORDER).pack(fill="x", padx=8, pady=(0, 4))
        self.content = ctk.CTkFrame(self, fg_color="transparent")
        self.content.pack(fill="both", expand=True, padx=4, pady=(0, 4))


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
        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=5)
        self.grid_columnconfigure(2, weight=3)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Left: Vanguard (full height)
        self.vanguard = self._build_vanguard(self)
        self.vanguard.grid(row=0, column=0, rowspan=2, sticky="nsew", padx=(0, 4))

        # Center top: Cortex Knowledge Core
        self.cortex_panel = NeonPanel(self, "\U0001f9e0 Cortex Knowledge Core")
        self.cortex_panel.grid(row=0, column=1, sticky="nsew", padx=4, pady=(0, 4))
        self._cortex_fig, self._cortex_ax, self._cortex_cv = _make_chart(
            self.cortex_panel.content, figsize=(5, 3))
        self._draw_cortex()

        # Center bottom: Omega Terminal
        self.omega_term = self._build_omega_terminal(self)
        self.omega_term.grid(row=1, column=1, sticky="nsew", padx=4, pady=(4, 0))

        # Right: Pulse + Fuel + Listener
        right = ctk.CTkFrame(self, fg_color="transparent")
        right.grid(row=0, column=2, rowspan=2, sticky="nsew", padx=(4, 0))
        for ri in range(6):
            right.grid_rowconfigure(ri, weight=1)

        # Row 0: Pulse Protocol
        self.pulse_panel = NeonPanel(right, "\u2764 Pulse Protocol")
        self.pulse_panel.grid(row=0, column=0, sticky="nsew", pady=(0, 2))
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

        # Row 1: API Fuel Gauge
        self.fuel_panel = NeonPanel(right, "\u26fd API Fuel Gauge")
        self.fuel_panel.grid(row=1, column=0, sticky="nsew", pady=2)
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

        # Row 2: The Listener
        self.listener_panel = NeonPanel(right, "\U0001f3a7 The Listener")
        self.listener_panel.grid(row=2, column=0, sticky="nsew", pady=2)
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

        # Row 3: Recent Events (from Memory tab)
        self._mini_events = InfoPanel(right, "\U0001f4dc Recent Events")
        self._mini_events.grid(row=3, column=0, sticky="nsew", pady=2)

        # Row 4: Circuit Breakers (from Agents tab)
        self._mini_circuits = InfoPanel(right, "\u26a1 Circuit Breakers")
        self._mini_circuits.grid(row=4, column=0, sticky="nsew", pady=2)

        # Row 5: Immune Status (from Immune tab)
        self._mini_immune = InfoPanel(right, "\U0001f6e1 Immune Status")
        self._mini_immune.grid(row=5, column=0, sticky="nsew", pady=(2, 0))

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
    def _build_omega_terminal(self, parent):
        panel = NeonPanel(parent, "\u2328 Omega Terminal")
        self._ot_text = ctk.CTkTextbox(
            panel.content, fg_color="#050810", text_color=NEON_GREEN,
            font=FONT_MONO_SM, border_color=BORDER, border_width=1,
            corner_radius=4, wrap="word", state="disabled")
        self._ot_text.pack(fill="both", expand=True, padx=4, pady=(0, 4))
        self._ot_write("\u2126 OMEGA SOVEREIGN CORE v2.0 \u2014 176 modules | 48K lines")
        self._ot_write("Commands: status, agents, health, metrics, bus, events,")
        self._ot_write("          keys, cortical, apps, brain, immune, rag, clear")
        self._ot_write("WAV-Loop: Will \u2192 Action \u2192 Verify (86 tools)")
        self._ot_write("Type any question \u2014 Oracle WAV will execute.\n")
        inp_frame = ctk.CTkFrame(panel.content, fg_color="transparent")
        inp_frame.pack(fill="x", padx=4, pady=(0, 2))
        ctk.CTkLabel(inp_frame, text="\u2126 >", font=("Consolas", 11, "bold"),
                      text_color=NEON_CYAN).pack(side="left", padx=(4, 4))
        self._ot_entry = ctk.CTkEntry(
            inp_frame, fg_color=BG_CARD, text_color=NEON_GREEN,
            font=FONT_MONO_SM, border_color=BORDER, border_width=1,
            placeholder_text="Command or question...", placeholder_text_color=TEXT_DIM)
        self._ot_entry.pack(side="left", fill="x", expand=True, padx=(0, 4))
        self._ot_entry.bind("<Return>", self._ot_on_enter)
        return panel

    def _ot_write(self, text):
        self._ot_text.configure(state="normal")
        self._ot_text.insert("end", text + "\n")
        self._ot_text.see("end")
        self._ot_text.configure(state="disabled")

    def _ot_on_enter(self, _=None):
        cmd = self._ot_entry.get().strip()
        if not cmd:
            return
        self._ot_entry.delete(0, "end")
        self._ot_write(f"\u2126 > {cmd}")
        known = {"help", "clear", "status", "agents", "health",
                 "metrics", "bus", "events", "keys", "cortical",
                 "apps", "brain", "immune", "rag"}
        if cmd.lower() in known:
            self._ot_dispatch(cmd.lower())
            self._ot_write("")
        else:
            # Free-text question → WAV-Loop via background thread
            self._ot_write("\u2126 WAV-Loop activating...")
            self._ot_entry.configure(state="disabled")
            threading.Thread(target=self._ot_ask_brain, args=(cmd,), daemon=True).start()

    def _ot_dispatch(self, cmd):
        eng = _load_engine()[0]
        if cmd == "help":
            self._ot_write("  System commands:")
            for c in ["status", "agents", "health", "metrics", "bus",
                       "events", "keys", "cortical", "apps", "brain",
                       "immune", "rag", "clear"]:
                self._ot_write(f"    {c}")
            self._ot_write("\n  AI mode (86 tools):")
            self._ot_write("    Just type any question or command in natural language.")
            self._ot_write("    The AI has access to all 31 apps + brain agents.")
        elif cmd == "clear":
            self._ot_text.configure(state="normal")
            self._ot_text.delete("1.0", "end")
            self._ot_text.configure(state="disabled")
            self._ot_write("\u2126 Cleared.\n")
        elif cmd == "status":
            self._ot_write(f"Time: {datetime.now().isoformat()}")
            if eng:
                s = eng.get_stats()
                self._ot_write(f"Queries: {s.get('queries_processed', 0)}")
                self._ot_write(f"Agents: {s.get('active_agents', 0)}")
                self._ot_write(f"Avg: {s.get('avg_response_ms', 0):.1f}ms")
            if HAS_PSUTIL:
                self._ot_write(f"CPU: {psutil.cpu_percent():.1f}%  RAM: {psutil.virtual_memory().percent:.1f}%")
        elif cmd == "agents":
            if eng and hasattr(eng, "agents"):
                for n in sorted(eng.agents):
                    self._ot_write(f"  [{n}]")
                self._ot_write(f"Total: {len(eng.agents)}")
        elif cmd == "health":
            wh = _safe(get_waakhuis) if HAS_WAAKHUIS else None
            if wh:
                for n, i in wh.gezondheidsrapport().get("agents", {}).items():
                    self._ot_write(f"  {n}: {i.get('score', '?')}%")
            else:
                self._ot_write("Waakhuis unavailable")
        elif cmd == "metrics":
            if eng:
                for k, v in eng._swarm_metrics.items():
                    self._ot_write(f"  {k}: {v}")
        elif cmd == "bus":
            bus = _safe(get_bus) if HAS_BUS else None
            if bus:
                for k, v in bus.statistieken().items():
                    self._ot_write(f"  {k}: {v}")
        elif cmd == "events":
            bus = _safe(get_bus) if HAS_BUS else None
            if bus:
                s = bus.get_context_stream(count=10)
                self._ot_write(s if s else "No events.")
        elif cmd == "keys":
            km = _safe(SmartKeyManager) if HAS_KEY_MANAGER else None
            if km:
                self._ot_write(f"Keys: {len(km._keys)}")
                with km._metrics_lock:
                    for n, a in km._agents.items():
                        self._ot_write(f"  {n}: {a.totaal_requests}req {a.totaal_tokens}tok")
        elif cmd == "cortical":
            if HAS_CORTICAL:
                for k, v in get_cortical_stack().get_db_metrics().items():
                    self._ot_write(f"  {k}: {v}")
        elif cmd == "apps":
            if eng and hasattr(eng, "app_registry"):
                apps = sorted(eng.app_registry.keys()) if hasattr(eng.app_registry, "keys") else []
                self._ot_write(f"  Registered apps: {len(apps)}")
                for a in apps:
                    self._ot_write(f"    {a}")
            else:
                try:
                    from danny_toolkit.brain.app_tools import TOOL_DEFINITIONS
                    self._ot_write(f"  Available tools: {len(TOOL_DEFINITIONS)}")
                    for td in TOOL_DEFINITIONS[:15]:
                        name = td.get("function", {}).get("name", "?")
                        self._ot_write(f"    {name}")
                    if len(TOOL_DEFINITIONS) > 15:
                        self._ot_write(f"    ... and {len(TOOL_DEFINITIONS) - 15} more")
                except Exception:
                    self._ot_write("  App registry not available")
        elif cmd == "brain":
            brain = _brain_cache
            if brain:
                self._ot_write(f"  CentralBrain: ACTIVE")
                tools = getattr(brain, '_tools', getattr(brain, 'tools', []))
                self._ot_write(f"  Tools loaded: {len(tools)}")
                self._ot_write(f"  Provider: {getattr(brain, 'provider', '?')}")
                self._ot_write(f"  Model: {getattr(brain, 'model', '?')}")
            else:
                self._ot_write("  CentralBrain: NOT LOADED")
        elif cmd == "immune":
            if HAS_BLACKBOX:
                try:
                    bb = get_black_box()
                    stats = bb.get_stats()
                    self._ot_write(f"  BlackBox: {stats.get('total_antibodies', 0)} antibodies")
                except Exception:
                    self._ot_write("  BlackBox: error")
            if HAS_SCHILD:
                try:
                    schild = get_hallucination_shield()
                    stats = schild.get_stats()
                    self._ot_write(f"  Shield: {stats.get('checks', 0)} checks, {stats.get('blocked', 0)} blocked")
                except Exception:
                    self._ot_write("  Shield: error")
            if HAS_TRIBUNAL:
                try:
                    trib = get_adversarial_tribunal()
                    stats = trib.get_stats()
                    self._ot_write(f"  Tribunal: {stats.get('verdicts', stats.get('total', 0))} verdicts")
                except Exception:
                    self._ot_write("  Tribunal: error")
        elif cmd == "rag":
            try:
                from danny_toolkit.core.vector_store import VectorStore
                vs = VectorStore()
                stats = vs.get_stats()
                for k, v in stats.items():
                    self._ot_write(f"  {k}: {v}")
            except Exception as e:
                self._ot_write(f"  VectorStore: {e}")

    def _ot_ask_brain(self, question):
        """WAV-Loop: Will -> Action -> Verification via CentralBrain."""
        t0 = time.time()
        w = lambda txt: self._ot_text.after(0, self._ot_write, txt)
        try:
            brain = _load_brain()
            if brain is None:
                w("[ERROR] CentralBrain not available")
                return

            # Houd laatste 4 berichten (2 exchanges) voor follow-up context
            if len(brain.conversation_history) > 4:
                brain.conversation_history[:] = brain.conversation_history[-4:]

            # ── PRE-CHECK: Self-diagnostic als gevraagd ──
            q_lower = question.lower()
            diag_data = None
            if any(kw in q_lower for kw in _DIAGNOSTIC_KEYWORDS):
                w("\u2126 [D] Diagnostic \u2014 scanning all modules...")
                diag_data = _run_self_diagnostic()
                samenv = diag_data.pop("_samenvatting", {})
                ok_count = samenv.get("ok", 0)
                fout_count = samenv.get("fout", 0)
                totaal = samenv.get("totaal", 0)
                w(f"\u2126 [D] Scan complete: {ok_count}/{totaal} OK, {fout_count} FOUT")

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
            w("\u2126 [W] Will \u2014 planning & executing...")
            response = brain.process_request(question, use_tools=True, max_tokens=2000)
            t_action = time.time() - t0

            if not response or not response.strip():
                w("[ERROR] Empty response from Brain")
                return

            w(f"\u2126 [A] Action \u2014 completed in {t_action:.1f}s")

            # ── PHASE 2: VERIFICATION ──
            w("\u2126 [V] Verify \u2014 checking response quality...")
            t_v0 = time.time()

            verify_prompt = (
                f"Vraag: \"{question}\"\n"
                f"Antwoord: {response[:200]}\n"
                "Geef ALLEEN: Score: [0-100] en 1 zin waarom."
            )
            try:
                verification = _ollama_verify(verify_prompt, timeout=45)
                t_verify = time.time() - t_v0
            except Exception:
                verification = None
                t_verify = 0

            # ── OUTPUT ──
            w("")
            for line in response.strip().split("\n"):
                w(f"  {line}")

            # Show verification result
            w("")
            if verification and verification.strip():
                w("\u2126 [V] Verificatie:")
                for line in verification.strip().split("\n")[:5]:
                    w(f"  \u2502 {line}")
            else:
                w("\u2126 [V] Verificatie: (geen respons van Ollama)")

            elapsed = time.time() - t0
            w(f"\n  [WAV: W={t_action:.1f}s V={t_verify:.1f}s | total={elapsed:.1f}s | {len(response)} chars]")
            w("")

        except Exception as e:
            w(f"[ERROR] {e}")
        finally:
            self._ot_text.after(0, lambda: self._ot_entry.configure(state="normal"))

    # ── Cortex Network ──
    def _draw_cortex(self):
        ax = self._cortex_ax
        ax.clear()
        ax.set_xlim(-7, 7)
        ax.set_ylim(-0.5, 6)
        ax.set_aspect("equal")
        ax.axis("off")
        tc = {1: ("TRINITY", NEON_CYAN, 220, 4), 2: ("GUARDIANS", NEON_GREEN, 160, 3),
              3: ("SPECIALISTS", NEON_ORANGE, 120, 2), 4: ("INFRA", NEON_PURPLE, 100, 1),
              5: ("SINGULARITY", NEON_RED, 180, 5)}
        if not HAS_TRINITY:
            ax.text(0, 3, "trinity_models\nnot available", ha="center", color=TEXT_DIM, fontsize=10)
            self._cortex_cv.draw_idle()
            return
        tiers = {}
        for role in CosmicRole:
            tiers.setdefault(CosmicRole.get_tier(role), []).append(role)
        positions = {}
        for tn, roles in sorted(tiers.items()):
            name, col, sz, y = tc.get(tn, tc[4])
            for i, role in enumerate(roles):
                x = (i - (len(roles) - 1) / 2) * 1.5
                yy = y + (hash(role.name) % 100 - 50) * 0.002  # deterministic jitter
                positions[role.name] = (x, yy)
                ax.scatter(x, yy, s=sz, color=col, alpha=0.8, zorder=3,
                           edgecolors=col, linewidths=1.5)
                ax.scatter(x, yy, s=sz * 2, color=col, alpha=0.08, zorder=2)
                ax.text(x, yy + 0.35, role.name, ha="center", va="bottom",
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
            self._mini_immune.write(f" Rejections: {bb_stats.get('total_rejections', 0)}")
        shield_stats = _cache.get("shield_stats")
        if shield_stats:
            self._mini_immune.write(f" Shield: {shield_stats.get('checks', 0)} checks")
            self._mini_immune.write(f" Blocked: {shield_stats.get('blocked', 0)}")
        if not bb_stats and not shield_stats:
            self._mini_immune.write(" Immune system N/A")

    def refresh(self):
        self.update_vanguard()
        self.update_pulse()
        self.update_fuel()
        self.update_listener()
        self._update_mini_events()
        self._update_mini_circuits()
        self._update_mini_immune()


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
            pct = round(vr['in_gebruik_mb'] / vr['totaal_mb'] * 100, 1)
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
                    self.phantom_panel.write(f"    {p.get('pattern', '?')}: {p.get('confidence', 0):.2f}")
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
            if stream:
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

        self.models_panel = InfoPanel(self, "\U0001f916 Model Registry")
        self.models_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 4), pady=(0, 4))
        self.leaderboard_panel = InfoPanel(self, "\U0001f3c6 Model Leaderboard")
        self.leaderboard_panel.grid(row=0, column=1, sticky="nsew", padx=(4, 0), pady=(0, 4))
        self.cost_panel = InfoPanel(self, "\U0001f4b0 Cost Analysis")
        self.cost_panel.grid(row=1, column=0, sticky="nsew", padx=(0, 4), pady=(4, 0))
        self.config_panel = InfoPanel(self, "\u2699 Config Audit")
        self.config_panel.grid(row=1, column=1, sticky="nsew", padx=(4, 0), pady=(4, 0))

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
                    prov = perf.get("provider", getattr(getattr(w, "profile", None), "provider", "?"))
                    self.models_panel.write(
                        f"    {prov:12s} ok:{perf.get('success_rate', 0):.0%}  "
                        f"lat:{perf.get('avg_latency_ms', 0):.0f}ms")
                except Exception:
                    pass
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

        self._write("OMEGA SOVEREIGN SHELL v2.0")
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
# ║  MAIN APPLICATION                                              ║
# ╚══════════════════════════════════════════════════════════════════╝

class OmegaSovereignApp(ctk.CTk):
    REFRESH_MS = 1000

    def __init__(self):
        super().__init__()
        self.title("\u2126 OMEGA SOVEREIGN DASHBOARD v2.0")
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

        self._tab_map = {
            tab_names[0]: self.tab_dashboard,
            tab_names[1]: self.tab_agents,
            tab_names[2]: self.tab_brain,
            tab_names[3]: self.tab_immune,
            tab_names[4]: self.tab_memory,
            tab_names[5]: self.tab_observatory,
            tab_names[6]: self.tab_terminal,
        }

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
        self._hw.pack(side="left", padx=20)
        self._time = ctk.CTkLabel(bar, text="", font=FONT_MONO_XS, text_color=TEXT_DIM)
        self._time.pack(side="right", padx=10)
        self._uptime_lbl = ctk.CTkLabel(bar, text="", font=FONT_MONO_XS, text_color=TEXT_DIM)
        self._uptime_lbl.pack(side="right", padx=8)
        self._start_time = time.time()

        # ── Keyboard shortcuts (Ctrl+1..7 for tabs) ──
        for i, name in enumerate(tab_names):
            self.bind(f"<Control-Key-{i + 1}>",
                      lambda e, n=name: self._tabs.set(n))

        # ── Initial load ──
        self.after(500, self._initial_load)
        self._schedule_refresh()

    def _initial_load(self):
        """Load SwarmEngine + CentralBrain + start data cache on startup."""
        _cache.start(interval=1.0)
        self.tab_dashboard.update_vanguard()
        # Pre-load CentralBrain in background so first AI question is fast
        threading.Thread(target=_load_brain, daemon=True).start()
        # Pre-warm Ollama gemma3:4b into VRAM (cold start takes ~30s otherwise)
        threading.Thread(
            target=lambda: _ollama_verify("ok", timeout=60),
            daemon=True,
        ).start()

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
        if cpu is not None:
            cpu_color = NEON_GREEN if cpu < 60 else (NEON_ORANGE if cpu < 85 else NEON_RED)
            hw_text = f"CPU {cpu:.0f}% | RAM {ram:.0f}%"
            vr = _cache.get("vram")
            if vr and vr.get("beschikbaar"):
                pct = round(vr['in_gebruik_mb'] / vr['totaal_mb'] * 100)
                hw_text += f" | GPU {pct}%"
            self._hw.configure(text=hw_text, text_color=cpu_color)

        # Refresh active tab only (performance)
        active = self._tabs.get()
        tab = self._tab_map.get(active)
        if tab:
            tab.refresh()


# ── ENTRY POINT ──────────────────────────────────────────────────

if __name__ == "__main__":
    app = OmegaSovereignApp()
    app.mainloop()
