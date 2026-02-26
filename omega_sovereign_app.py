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


# ── LAZY LOADERS ─────────────────────────────────────────────────

_engine_cache = None
_engine_lock = threading.Lock()


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

        # Left: Vanguard + OmegaTerminal
        left = ctk.CTkFrame(self, fg_color="transparent")
        left.grid(row=0, column=0, rowspan=2, sticky="nsew", padx=(0, 4))
        left.grid_rowconfigure(0, weight=1)
        left.grid_rowconfigure(1, weight=1)
        self.vanguard = self._build_vanguard(left)
        self.vanguard.grid(row=0, column=0, sticky="nsew", pady=(0, 4))
        self.omega_term = self._build_omega_terminal(left)
        self.omega_term.grid(row=1, column=0, sticky="nsew", pady=(4, 0))

        # Center: Cortex
        self.cortex_panel = NeonPanel(self, "\U0001f9e0 Cortex Knowledge Core")
        self.cortex_panel.grid(row=0, column=1, rowspan=2, sticky="nsew", padx=4)
        self._cortex_fig, self._cortex_ax, self._cortex_cv = _make_chart(
            self.cortex_panel.content, figsize=(5, 4))
        self._draw_cortex()

        # Right: Pulse + Fuel + Listener
        right = ctk.CTkFrame(self, fg_color="transparent")
        right.grid(row=0, column=2, rowspan=2, sticky="nsew", padx=(4, 0))
        right.grid_rowconfigure(0, weight=1)
        right.grid_rowconfigure(1, weight=1)
        right.grid_rowconfigure(2, weight=1)

        self.pulse_panel = NeonPanel(right, "\u2764 Pulse Protocol")
        self.pulse_panel.grid(row=0, column=0, sticky="nsew", pady=(0, 4))
        self._pulse_fig, self._pulse_ax, self._pulse_cv = _make_chart(
            self.pulse_panel.content, figsize=(3.2, 1.6))
        self._pulse_samples = deque(maxlen=60)
        self._pulse_metrics = ctk.CTkFrame(self.pulse_panel.content, fg_color="transparent")
        self._pulse_metrics.pack(fill="x", padx=4)
        self._cpu_lbl = ctk.CTkLabel(self._pulse_metrics, text="CPU: --%",
                                      font=FONT_MONO_SM, text_color=NEON_GREEN)
        self._cpu_lbl.pack(side="left", padx=6)
        self._ram_lbl = ctk.CTkLabel(self._pulse_metrics, text="RAM: --%",
                                      font=FONT_MONO_SM, text_color=NEON_CYAN)
        self._ram_lbl.pack(side="right", padx=6)

        self.fuel_panel = NeonPanel(right, "\u26fd API Fuel Gauge")
        self.fuel_panel.grid(row=1, column=0, sticky="nsew", pady=4)
        self._fuel_fig, self._fuel_ax, self._fuel_cv = _make_chart(
            self.fuel_panel.content, figsize=(3.2, 2.0),
            subplot_kw={"projection": "polar"})
        self._fuel_metrics = ctk.CTkFrame(self.fuel_panel.content, fg_color="transparent")
        self._fuel_metrics.pack(fill="x", padx=4)
        self._rpm_lbl = ctk.CTkLabel(self._fuel_metrics, text="RPM: 0/30",
                                      font=FONT_MONO_SM, text_color=NEON_CYAN)
        self._rpm_lbl.pack(side="left", padx=6)
        self._tpm_lbl = ctk.CTkLabel(self._fuel_metrics, text="TPM: 0/30K",
                                      font=FONT_MONO_SM, text_color=NEON_CYAN)
        self._tpm_lbl.pack(side="right", padx=6)

        self.listener_panel = NeonPanel(right, "\U0001f3a7 The Listener")
        self.listener_panel.grid(row=2, column=0, sticky="nsew", pady=(4, 0))
        self._list_fig, self._list_ax, self._list_cv = _make_chart(
            self.listener_panel.content, figsize=(3.2, 1.6))
        self._list_metrics = ctk.CTkFrame(self.listener_panel.content, fg_color="transparent")
        self._list_metrics.pack(fill="x", padx=4)
        self._ev_lbl = ctk.CTkLabel(self._list_metrics, text="Events: 0",
                                     font=FONT_MONO_SM, text_color=NEON_CYAN)
        self._ev_lbl.pack(side="left", padx=6)
        self._sub_lbl = ctk.CTkLabel(self._list_metrics, text="Subs: 0",
                                      font=FONT_MONO_SM, text_color=NEON_CYAN)
        self._sub_lbl.pack(side="right", padx=6)

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
        wh = _safe(get_waakhuis) if HAS_WAAKHUIS else None
        if eng and hasattr(eng, "agents"):
            for name in eng.agents:
                h, s = 100, "ok"
                if wh:
                    try:
                        info = wh.gezondheidsrapport().get("agents", {}).get(name, {})
                        if info:
                            h = info.get("gezondheid", 100)
                            s = "dead" if h < 30 else ("warn" if h < 70 else "ok")
                    except Exception:
                        pass
                data.append((name, h, s))
        elif HAS_TRINITY:
            data = [(r.name, 85, "ok") for r in CosmicRole]
        if not data:
            data = [("NO_DATA", 0, "dead")]
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
        self._ot_write("\u2126 OMEGA SOVEREIGN CORE v2.0")
        self._ot_write("Commands: status, agents, health, metrics, bus, events, keys, cortical, clear, help\n")
        inp_frame = ctk.CTkFrame(panel.content, fg_color="transparent")
        inp_frame.pack(fill="x", padx=4, pady=(0, 2))
        ctk.CTkLabel(inp_frame, text="\u2126 >", font=("Consolas", 11, "bold"),
                      text_color=NEON_CYAN).pack(side="left", padx=(4, 4))
        self._ot_entry = ctk.CTkEntry(
            inp_frame, fg_color=BG_CARD, text_color=NEON_GREEN,
            font=FONT_MONO_SM, border_color=BORDER, border_width=1,
            placeholder_text="Enter command...", placeholder_text_color=TEXT_DIM)
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
        self._ot_dispatch(cmd.lower())
        self._ot_write("")

    def _ot_dispatch(self, cmd):
        eng = _load_engine()[0]
        if cmd == "help":
            for c in ["status", "agents", "health", "metrics",
                       "bus", "events", "keys", "cortical", "clear"]:
                self._ot_write(f"  {c}")
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
                    self._ot_write(f"  {n}: {i.get('gezondheid', '?')}%")
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
        else:
            self._ot_write(f"Unknown: '{cmd}'")

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
                yy = y + np.random.uniform(-0.1, 0.1)
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
        if HAS_PSUTIL:
            self._pulse_samples.append(psutil.cpu_percent(interval=0.05))
            self._cpu_lbl.configure(text=f"CPU: {self._pulse_samples[-1]:.0f}%")
            self._ram_lbl.configure(text=f"RAM: {psutil.virtual_memory().percent:.0f}%")
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
        pct, rpm_u, rpm_m, tpm_u, tpm_m = 0, 0, 30, 0, 30000
        km = _safe(SmartKeyManager) if HAS_KEY_MANAGER else None
        if km:
            try:
                now = time.time()
                with km._metrics_lock:
                    rpm_u = sum(sum(1 for ts in a.request_timestamps if now - ts < 60)
                                for a in km._agents.values())
                    tpm_u = sum(a.tokens_deze_minuut for a in km._agents.values())
                pct = min(100, (rpm_u / rpm_m) * 100) if rpm_m else 0
            except Exception:
                pass
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
        bus = _safe(get_bus) if HAS_BUS else None
        counts = []
        if bus:
            try:
                with bus._lock:
                    types = list(bus._history.keys())
                for et in types[:20]:
                    counts.append(len(bus.get_history(et, count=100)))
                st = bus.statistieken()
                self._ev_lbl.configure(text=f"Events: {st.get('events_gepubliceerd', 0)}")
                self._sub_lbl.configure(text=f"Subs: {st.get('subscribers', 0)}")
            except Exception:
                pass
        if not counts:
            t = np.linspace(0, 4 * math.pi, 60)
            counts = (np.abs(np.sin(t) * np.cos(t * 0.7)) * 50 +
                      np.random.uniform(0, 8, len(t))).tolist()
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

    def refresh(self):
        self.update_pulse()
        self.update_fuel()
        self.update_listener()


# ╔══════════════════════════════════════════════════════════════════╗
# ║  TAB 2: AGENTS                                                 ║
# ╚══════════════════════════════════════════════════════════════════╝

class AgentsTab(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.health_panel = InfoPanel(self, "\u269b Agent Health Report")
        self.health_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 4), pady=(0, 4))
        self.circuit_panel = InfoPanel(self, "\u26a1 Circuit Breakers")
        self.circuit_panel.grid(row=0, column=1, sticky="nsew", padx=(4, 0), pady=(0, 4))
        self.metrics_panel = InfoPanel(self, "\U0001f4ca Pipeline Metrics")
        self.metrics_panel.grid(row=1, column=0, sticky="nsew", padx=(0, 4), pady=(4, 0))
        self.keys_panel = InfoPanel(self, "\U0001f511 API Key Status")
        self.keys_panel.grid(row=1, column=1, sticky="nsew", padx=(4, 0), pady=(4, 0))

    def refresh(self):
        # Health
        self.health_panel.clear()
        wh = _safe(get_waakhuis) if HAS_WAAKHUIS else None
        if wh:
            try:
                r = wh.gezondheidsrapport()
                for name, info in sorted(r.get("agents", {}).items()):
                    score = info.get("gezondheid", "?")
                    disp = info.get("dispatches", 0)
                    errs = info.get("fouten", 0)
                    icon = "[OK]" if score >= 70 else ("[!!]" if score >= 30 else "[XX]")
                    self.health_panel.write(f"  {icon} {name:20s} {score:>3}%  disp:{disp}  err:{errs}")
                hw = wh.hardware_status()
                self.health_panel.write(f"\n  Hardware: CPU {hw.get('cpu_percent', '?')}%  "
                                        f"RAM {hw.get('ram_percent', '?')}%")
            except Exception as e:
                self.health_panel.write(f"Error: {e}")
        else:
            self.health_panel.write("Waakhuis not available")

        # Circuit breakers
        self.circuit_panel.clear()
        eng = _load_engine()[0]
        if eng:
            try:
                from swarm_engine import get_circuit_state
                cs = get_circuit_state()
                for agent, state in sorted(cs.items()):
                    is_open = state.get("is_open", False)
                    fails = state.get("failures", 0)
                    icon = "[OPEN]" if is_open else "[CLOSED]"
                    self.circuit_panel.write(f"  {icon} {agent:20s} fails:{fails}")
            except Exception:
                for k, v in eng._swarm_metrics.items():
                    if "circuit" in k:
                        self.circuit_panel.write(f"  {k}: {v}")
        else:
            self.circuit_panel.write("SwarmEngine not loaded")

        # Pipeline metrics
        self.metrics_panel.clear()
        if eng:
            try:
                from swarm_engine import get_pipeline_metrics
                pm = get_pipeline_metrics()
                for agent, m in sorted(pm.items()):
                    calls = m.get("calls", 0)
                    avg = m.get("avg_ms", 0)
                    rate = m.get("success_rate", 1.0)
                    self.metrics_panel.write(
                        f"  {agent:20s} calls:{calls:>4}  avg:{avg:>6.1f}ms  ok:{rate:.0%}")
            except Exception:
                s = eng.get_stats()
                for k, v in s.items():
                    self.metrics_panel.write(f"  {k}: {v}")

        # Key status
        self.keys_panel.clear()
        km = _safe(SmartKeyManager) if HAS_KEY_MANAGER else None
        if km:
            self.keys_panel.write(f"  Keys loaded: {len(km._keys)}")
            try:
                cooldown = km.get_agents_in_cooldown()
                if cooldown:
                    self.keys_panel.write(f"  In cooldown: {', '.join(cooldown)}")
            except Exception:
                pass
            now = time.time()
            with km._metrics_lock:
                for name, a in sorted(km._agents.items()):
                    rpm = sum(1 for ts in a.request_timestamps if now - ts < 60)
                    self.keys_panel.write(
                        f"  {name:20s} req:{a.totaal_requests:>4}  tok:{a.totaal_tokens:>6}  "
                        f"rpm:{rpm}  429s:{a.totaal_429s}")


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
        # Synapse
        self.synapse_panel.clear()
        try:
            from danny_toolkit.brain.synapse import TheSynapse
            syn = TheSynapse()
            stats = syn.get_stats()
            for k, v in stats.items():
                self.synapse_panel.write(f"  {k}: {v}")
            top = syn.get_top_pathways(limit=10)
            if top:
                self.synapse_panel.write("\n  Top pathways:")
                for p in top:
                    self.synapse_panel.write(
                        f"    {p.get('from', '?')} -> {p.get('to', '?')}: "
                        f"{p.get('strength', 0):.3f}")
        except Exception as e:
            self.synapse_panel.write(f"  Synapse: {e}")

        # Phantom
        self.phantom_panel.clear()
        try:
            from danny_toolkit.brain.phantom import ThePhantom
            ph = ThePhantom()
            acc = ph.get_accuracy()
            for k, v in acc.items():
                self.phantom_panel.write(f"  {k}: {v}")
            preds = ph.get_predictions(max_results=5)
            if preds:
                self.phantom_panel.write("\n  Recent predictions:")
                for p in preds:
                    self.phantom_panel.write(f"    {p.get('pattern', '?')}: {p.get('confidence', 0):.2f}")
        except Exception as e:
            self.phantom_panel.write(f"  Phantom: {e}")

        # Singularity
        self.singularity_panel.clear()
        try:
            from danny_toolkit.brain.singularity import SingularityEngine
            se = SingularityEngine()
            status = se.get_status()
            for k, v in status.items():
                self.singularity_panel.write(f"  {k}: {v}")
        except Exception as e:
            self.singularity_panel.write(f"  Singularity: {e}")

        # Introspector
        self.introspect_panel.clear()
        if HAS_INTROSPECTOR:
            try:
                intro = get_introspector()
                report = intro.get_health_report()
                for k, v in report.items():
                    if isinstance(v, dict):
                        self.introspect_panel.write(f"  {k}:")
                        for kk, vv in v.items():
                            self.introspect_panel.write(f"    {kk}: {vv}")
                    else:
                        self.introspect_panel.write(f"  {k}: {v}")
            except Exception as e:
                self.introspect_panel.write(f"  Introspector: {e}")


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
        # BlackBox
        self.blackbox_panel.clear()
        if HAS_BLACKBOX:
            try:
                bb = get_black_box()
                stats = bb.get_stats()
                for k, v in stats.items():
                    self.blackbox_panel.write(f"  {k}: {v}")
                antibodies = bb.get_antibodies()
                if antibodies:
                    self.blackbox_panel.write(f"\n  Antibodies ({len(antibodies)}):")
                    for ab in antibodies[:8]:
                        sig = ab.get("error_signature", "?")[:40]
                        strength = ab.get("strength", 0)
                        self.blackbox_panel.write(f"    [{strength:.1f}] {sig}")
            except Exception as e:
                self.blackbox_panel.write(f"  Error: {e}")
        else:
            self.blackbox_panel.write("  BlackBox not available")

        # Schild
        self.schild_panel.clear()
        if HAS_SCHILD:
            try:
                schild = get_hallucination_shield()
                stats = schild.get_stats()
                for k, v in stats.items():
                    self.schild_panel.write(f"  {k}: {v}")
            except Exception as e:
                self.schild_panel.write(f"  Error: {e}")
        else:
            self.schild_panel.write("  Shield not available")

        # Governor
        self.governor_panel.clear()
        eng = _load_engine()[0]
        if eng and hasattr(eng, "brain") and eng.brain:
            try:
                brain = eng.brain
                if hasattr(brain, "governor"):
                    report = brain.governor.get_health_report()
                    for k, v in report.items():
                        if isinstance(v, dict):
                            self.governor_panel.write(f"  {k}:")
                            for kk, vv in v.items():
                                self.governor_panel.write(f"    {kk}: {vv}")
                        else:
                            self.governor_panel.write(f"  {k}: {v}")
            except Exception as e:
                self.governor_panel.write(f"  Error: {e}")
        else:
            self.governor_panel.write("  Governor not available (no brain)")

        # Tribunal
        self.tribunal_panel.clear()
        if HAS_TRIBUNAL:
            try:
                trib = get_adversarial_tribunal()
                stats = trib.get_stats()
                for k, v in stats.items():
                    self.tribunal_panel.write(f"  {k}: {v}")
            except Exception as e:
                self.tribunal_panel.write(f"  Error: {e}")
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
        # Events
        self.events_panel.clear()
        if HAS_CORTICAL:
            try:
                stack = get_cortical_stack()
                events = stack.get_recent_events(count=25)
                for ev in events:
                    ts = ev.get("timestamp", "?")
                    if isinstance(ts, str) and len(ts) > 19:
                        ts = ts[:19]
                    actor = ev.get("actor", "?")
                    etype = ev.get("event_type", "?")
                    self.events_panel.write(f"  [{ts}] {actor}: {etype}")
            except Exception as e:
                self.events_panel.write(f"  Error: {e}")

        # DB Metrics
        self.dbmetrics_panel.clear()
        if HAS_CORTICAL:
            try:
                m = get_cortical_stack().get_db_metrics()
                for k, v in m.items():
                    self.dbmetrics_panel.write(f"  {k}: {v}")
                stats = get_cortical_stack().get_stats()
                self.dbmetrics_panel.write("\n  Memory stats:")
                for k, v in stats.items():
                    self.dbmetrics_panel.write(f"    {k}: {v}")
            except Exception as e:
                self.dbmetrics_panel.write(f"  Error: {e}")

        # NeuralBus
        self.bus_panel.clear()
        bus = _safe(get_bus) if HAS_BUS else None
        if bus:
            st = bus.statistieken()
            for k, v in st.items():
                self.bus_panel.write(f"  {k}: {v}")
            stream = bus.get_context_stream(count=15)
            if stream:
                self.bus_panel.write("")
                for line in stream.split("\n"):
                    self.bus_panel.write(f"  {line}")

        # Semantic facts
        self.facts_panel.clear()
        if HAS_CORTICAL:
            try:
                facts = get_cortical_stack().recall_all()
                self.facts_panel.write(f"  Total facts: {len(facts)}")
                for f in facts[:20]:
                    key = f.get("key", "?")
                    val = str(f.get("value", "?"))[:60]
                    conf = f.get("confidence", 0)
                    self.facts_panel.write(f"  [{conf:.1f}] {key}: {val}")
            except Exception as e:
                self.facts_panel.write(f"  Error: {e}")


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
        # Model Registry
        self.models_panel.clear()
        if HAS_MODELS:
            try:
                reg = get_model_registry()
                stats = reg.get_stats()
                for k, v in stats.items():
                    self.models_panel.write(f"  {k}: {v}")
                workers = reg.get_all_workers()
                self.models_panel.write(f"\n  Workers ({len(workers)}):")
                for w in workers:
                    perf = w.get_perf()
                    self.models_panel.write(
                        f"    {w.provider:12s} ok:{perf.get('success_rate', 0):.0%}  "
                        f"lat:{perf.get('latency', 0):.0f}ms")
            except Exception as e:
                self.models_panel.write(f"  Error: {e}")
        else:
            self.models_panel.write("  ModelRegistry not available")

        # Leaderboard
        self.leaderboard_panel.clear()
        if HAS_OBSERVATORY:
            try:
                obs = get_observatory_sync()
                lb = obs.get_model_leaderboard()
                for i, entry in enumerate(lb[:10]):
                    name = entry.get("model", "?")
                    rate = entry.get("success_rate", 0)
                    lat = entry.get("latency", 0)
                    self.leaderboard_panel.write(
                        f"  #{i + 1} {name:30s} ok:{rate:.0%}  lat:{lat:.0f}ms")
            except Exception as e:
                self.leaderboard_panel.write(f"  Error: {e}")
        else:
            self.leaderboard_panel.write("  Observatory not available")

        # Cost
        self.cost_panel.clear()
        if HAS_OBSERVATORY:
            try:
                obs = get_observatory_sync()
                cost = obs.get_cost_analysis()
                for k, v in cost.items():
                    self.cost_panel.write(f"  {k}: {v}")
            except Exception as e:
                self.cost_panel.write(f"  Error: {e}")

        # Config Audit
        self.config_panel.clear()
        try:
            from danny_toolkit.brain.config_auditor import get_config_auditor
            auditor = get_config_auditor()
            drift = auditor.detect_drift()
            if drift:
                self.config_panel.write(f"  Drift detected ({len(drift)} items):")
                for d in drift[:10]:
                    self.config_panel.write(f"    {d}")
            else:
                self.config_panel.write("  No config drift detected")
        except Exception as e:
            self.config_panel.write(f"  ConfigAuditor: {e}")


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
    REFRESH_MS = 3000

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
        self._hw = ctk.CTkLabel(bar, text="", font=FONT_MONO_XS, text_color=TEXT_DIM)
        self._hw.pack(side="left", padx=20)
        self._time = ctk.CTkLabel(bar, text="", font=FONT_MONO_XS, text_color=TEXT_DIM)
        self._time.pack(side="right", padx=10)

        # ── Initial load ──
        self.after(500, self._initial_load)
        self._schedule_refresh()

    def _initial_load(self):
        """Load SwarmEngine + initial vanguard chart on startup."""
        self.tab_dashboard.update_vanguard()

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

        # Status bar
        eng = _load_engine()[0]
        if eng:
            s = eng.get_stats()
            self._status.configure(
                text=f"\u25cf ONLINE | {s.get('active_agents', 0)} agents",
                text_color=NEON_GREEN)
        else:
            self._status.configure(text="\u25cb OFFLINE", text_color=NEON_RED)

        if HAS_PSUTIL:
            self._hw.configure(
                text=f"CPU {psutil.cpu_percent():.0f}% | "
                     f"RAM {psutil.virtual_memory().percent:.0f}%")

        # Refresh active tab only (performance)
        active = self._tabs.get()
        tab = self._tab_map.get(active)
        if tab:
            tab.refresh()


# ── ENTRY POINT ──────────────────────────────────────────────────

if __name__ == "__main__":
    app = OmegaSovereignApp()
    app.mainloop()
