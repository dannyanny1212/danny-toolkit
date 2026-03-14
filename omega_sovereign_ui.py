"""
OMEGA SOVEREIGN UI -- Hyper-Modern Streamlit Dashboard v1.0
============================================================

Futuristisch neon dashboard met 6 live panels:
  - Vanguard Status:    Agent health cards met circuit breakers
  - Cortex Knowledge:   Neural network visualisatie (Prometheus nodes)
  - Pulse Protocol:     ECG-style CPU heartbeat
  - API Fuel Gauge:     Circulaire Groq API budget meter
  - Terminal:           Command interface met omega dispatch
  - The Listener:       NeuralBus event waveform

Dark space aesthetic (#0a0e17) met neon cyan/green accenten.
Gebruik: streamlit run omega_sovereign_ui.py --server.port 8502
"""

import io
import os
import sys
import time
import math
import logging
import subprocess
from datetime import datetime
from contextlib import redirect_stdout

# UTF-8 voor Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        logger.debug("UTF-8 stdout reconfigure not available")

import streamlit as st

logger = logging.getLogger(__name__)

# ── PAGE CONFIG ──────────────────────────────────────────────────

st.set_page_config(
    page_title="OMEGA // Sovereign UI",
    page_icon="\u2126",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── NEON CSS THEME ───────────────────────────────────────────────

NEON_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Fira+Code:wght@300;400;500;600;700&display=swap');
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;500;600&display=swap');

    :root {
        --bg-deep: #0a0e17;
        --bg-panel: #0d1220;
        --bg-card: #111827;
        --border: #1e293b;
        --neon-cyan: #00d4ff;
        --neon-green: #00ff88;
        --neon-orange: #ff6b35;
        --neon-red: #ff3366;
        --neon-purple: #a855f7;
        --text-primary: #e0e6ed;
        --text-dim: #64748b;
    }

    .stApp {
        background-color: var(--bg-deep) !important;
        color: var(--text-primary);
        font-family: 'Fira Code', 'JetBrains Mono', monospace;
    }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #080c14 !important;
    }

    /* Headers */
    h1, h2, h3, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
        color: var(--neon-cyan) !important;
        font-family: 'JetBrains Mono', monospace !important;
        text-shadow: 0 0 10px rgba(0,212,255,0.3);
    }

    /* Panels */
    .omega-panel {
        background: var(--bg-panel);
        border: 1px solid var(--border);
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 12px;
        box-shadow: 0 0 15px rgba(0,212,255,0.08),
                    inset 0 1px 0 rgba(0,212,255,0.05);
    }

    .omega-panel-title {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.75em;
        font-weight: 600;
        color: var(--neon-cyan);
        letter-spacing: 3px;
        text-transform: uppercase;
        margin-bottom: 12px;
        padding-bottom: 8px;
        border-bottom: 1px solid rgba(0,212,255,0.15);
        text-shadow: 0 0 8px rgba(0,212,255,0.4);
    }

    /* Agent cards */
    .agent-card {
        background: var(--bg-card);
        border: 1px solid var(--border);
        border-radius: 6px;
        padding: 8px 12px;
        margin-bottom: 6px;
        font-size: 0.8em;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .agent-card:hover {
        border-color: var(--neon-cyan);
        box-shadow: 0 0 10px rgba(0,212,255,0.15);
    }

    .agent-name {
        color: var(--neon-cyan);
        font-weight: 600;
        font-family: 'Fira Code', monospace;
    }
    .agent-ok { color: var(--neon-green); }
    .agent-warn { color: var(--neon-orange); }
    .agent-dead { color: var(--neon-red); }

    /* Terminal */
    .omega-terminal {
        background: #050810;
        border: 1px solid var(--border);
        border-radius: 6px;
        padding: 12px;
        font-family: 'Fira Code', monospace;
        font-size: 0.8em;
        color: var(--neon-green);
        max-height: 250px;
        overflow-y: auto;
        white-space: pre-wrap;
    }

    .terminal-prompt {
        color: var(--neon-cyan);
        font-weight: bold;
    }

    /* Metrics override */
    div[data-testid="stMetric"] {
        background-color: var(--bg-card);
        padding: 8px 12px;
        border-radius: 6px;
        border-left: 3px solid var(--neon-cyan);
    }
    div[data-testid="stMetric"] label {
        color: var(--text-dim) !important;
        font-family: 'Fira Code', monospace !important;
    }
    div[data-testid="stMetric"] [data-testid="stMetricValue"] {
        color: var(--neon-cyan) !important;
        font-family: 'JetBrains Mono', monospace !important;
    }

    /* Plotly chart backgrounds */
    .stPlotlyChart {
        border-radius: 6px;
        overflow: hidden;
    }

    /* Input fields */
    .stTextInput input {
        background-color: var(--bg-card) !important;
        color: var(--neon-green) !important;
        border-color: var(--border) !important;
        font-family: 'Fira Code', monospace !important;
    }
    .stTextInput input:focus {
        border-color: var(--neon-cyan) !important;
        box-shadow: 0 0 8px rgba(0,212,255,0.3) !important;
    }

    /* Scrollbar */
    ::-webkit-scrollbar { width: 6px; }
    ::-webkit-scrollbar-track { background: var(--bg-deep); }
    ::-webkit-scrollbar-thumb {
        background: var(--border);
        border-radius: 3px;
    }
    ::-webkit-scrollbar-thumb:hover { background: var(--neon-cyan); }

    /* Top banner glow line */
    .glow-line {
        height: 2px;
        background: linear-gradient(90deg,
            transparent 0%,
            var(--neon-cyan) 20%,
            var(--neon-green) 50%,
            var(--neon-cyan) 80%,
            transparent 100%
        );
        margin-bottom: 20px;
        box-shadow: 0 0 12px rgba(0,212,255,0.5);
    }

    /* Hide default streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
</style>
"""

st.markdown(NEON_CSS, unsafe_allow_html=True)

# ── IMPORTS (alle met try/except) ────────────────────────────────

try:
    import plotly.graph_objects as go
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

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
    from danny_toolkit.core.key_manager import (
        SmartKeyManager, MODEL_LIMITS, DEFAULT_LIMITS,
    )
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
    from danny_toolkit.brain.trinity_models import (
        CosmicRole, NodeTier, AgentNode,
    )
    HAS_TRINITY = True
except ImportError:
    HAS_TRINITY = False


# ── LAZY BACKEND LOADERS (gecachet) ─────────────────────────────

@st.cache_resource(show_spinner="Sovereign Core wordt gewekt...")
def _load_swarm_engine():
    """Laad SwarmEngine eenmalig."""
    try:
        buf = io.StringIO()
        with redirect_stdout(buf):
            from swarm_engine import SwarmEngine
            engine = SwarmEngine()
        return engine, buf.getvalue()
    except Exception as e:
        logger.debug("SwarmEngine laden mislukt: %s", e)
        return None, str(e)


def _get_bus_safe():
    """Verkrijg NeuralBus singleton (safe)."""
    if HAS_BUS:
        try:
            return get_bus()
        except Exception:
            logger.debug("Suppressed exception in omega_sovereign_ui")
    return None


def _get_key_manager_safe():
    """Verkrijg SmartKeyManager singleton (safe)."""
    if HAS_KEY_MANAGER:
        try:
            return SmartKeyManager()
        except Exception:
            logger.debug("Suppressed exception in omega_sovereign_ui")
    return None


def _get_waakhuis_safe():
    """Verkrijg WaakhuisMonitor singleton (safe)."""
    if HAS_WAAKHUIS:
        try:
            return get_waakhuis()
        except Exception:
            logger.debug("Suppressed exception in omega_sovereign_ui")
    return None


# ── PLOTLY DEFAULTS ──────────────────────────────────────────────

PLOTLY_BG = "#0a0e17"
PLOTLY_PAPER = "#0d1220"
PLOTLY_GRID = "#1e293b"
PLOTLY_CYAN = "#00d4ff"
PLOTLY_GREEN = "#00ff88"
PLOTLY_ORANGE = "#ff6b35"
PLOTLY_RED = "#ff3366"
PLOTLY_PURPLE = "#a855f7"


def _base_layout(**kwargs):
    """Base plotly layout met neon theme."""
    layout = dict(
        paper_bgcolor=PLOTLY_PAPER,
        plot_bgcolor=PLOTLY_BG,
        font=dict(family="Fira Code, monospace", color="#e0e6ed", size=11),
        margin=dict(l=40, r=20, t=30, b=30),
        xaxis=dict(
            gridcolor=PLOTLY_GRID, zerolinecolor=PLOTLY_GRID,
            showgrid=True, gridwidth=1,
        ),
        yaxis=dict(
            gridcolor=PLOTLY_GRID, zerolinecolor=PLOTLY_GRID,
            showgrid=True, gridwidth=1,
        ),
    )
    layout.update(kwargs)
    return layout


# ── HEADER ───────────────────────────────────────────────────────

st.markdown('<div class="glow-line"></div>', unsafe_allow_html=True)

hdr_left, hdr_center, hdr_right = st.columns([2, 5, 2])
with hdr_left:
    st.markdown(
        '<span style="color:#00d4ff;font-size:0.7em;letter-spacing:4px;'
        'font-family:JetBrains Mono,monospace">'
        '\u2126 SOVEREIGN CORE</span>',
        unsafe_allow_html=True,
    )
with hdr_center:
    st.markdown(
        '<h1 style="text-align:center;margin:0;font-size:1.8em;'
        'letter-spacing:6px;color:#00d4ff !important;'
        'text-shadow:0 0 20px rgba(0,212,255,0.5)">'
        'O M E G A &nbsp; D A S H B O A R D</h1>',
        unsafe_allow_html=True,
    )
with hdr_right:
    now = datetime.now()
    st.markdown(
        f'<span style="color:#64748b;font-size:0.7em;'
        f'font-family:Fira Code,monospace;float:right">'
        f'{now.strftime("%Y-%m-%d %H:%M:%S")}</span>',
        unsafe_allow_html=True,
    )

st.markdown('<div class="glow-line"></div>', unsafe_allow_html=True)


# ── MAIN LAYOUT ──────────────────────────────────────────────────

col_left, col_center, col_right = st.columns([3, 5, 3])


# ╔══════════════════════════════════════════════════════════════════╗
# ║  PANEL 1: VANGUARD STATUS (links-boven)                        ║
# ╚══════════════════════════════════════════════════════════════════╝

with col_left:
    st.markdown(
        '<div class="omega-panel">'
        '<div class="omega-panel-title">'
        '\u269b Vanguard Status</div></div>',
        unsafe_allow_html=True,
    )

    engine, _boot_log = _load_swarm_engine()
    waakhuis = _get_waakhuis_safe()

    # Verzamel agent data
    agent_data = []

    if engine and hasattr(engine, "agents"):
        for name, _handler in engine.agents.items():
            health = 100
            status = "ok"

            # Waakhuis health scoring
            if waakhuis:
                try:
                    rapport = waakhuis.gezondheidsrapport()
                    agent_info = rapport.get("agents", {}).get(name, {})
                    if agent_info:
                        health = agent_info.get("gezondheid", 100)
                        if health < 30:
                            status = "dead"
                        elif health < 70:
                            status = "warn"
                except Exception:
                    logger.debug("Suppressed exception in omega_sovereign_ui")

            agent_data.append({
                "name": name,
                "health": health,
                "status": status,
            })
    else:
        # Fallback: toon CosmicRole-based nodes
        if HAS_TRINITY:
            for role in CosmicRole:
                agent_data.append({
                    "name": role.name,
                    "health": 85,
                    "status": "ok",
                })

    if agent_data and HAS_PLOTLY:
        # Sorteer: slechtste bovenaan
        agent_data.sort(key=lambda x: x["health"])

        names = [a["name"] for a in agent_data]
        healths = [a["health"] for a in agent_data]
        colors = []
        for a in agent_data:
            if a["status"] == "dead":
                colors.append(PLOTLY_RED)
            elif a["status"] == "warn":
                colors.append(PLOTLY_ORANGE)
            else:
                colors.append(PLOTLY_GREEN)

        fig_agents = go.Figure(go.Bar(
            y=names,
            x=healths,
            orientation="h",
            marker=dict(
                color=colors,
                line=dict(color=colors, width=1),
            ),
            text=[f"{h}%" for h in healths],
            textposition="inside",
            textfont=dict(
                color="#0a0e17", size=10,
                family="Fira Code, monospace",
            ),
            hovertemplate="%{y}: %{x}%<extra></extra>",
        ))
        fig_agents.update_layout(
            **_base_layout(
                height=max(280, len(names) * 22),
                yaxis=dict(
                    gridcolor=PLOTLY_GRID,
                    categoryorder="array",
                    categoryarray=names,
                    tickfont=dict(size=9),
                ),
                xaxis=dict(
                    gridcolor=PLOTLY_GRID,
                    range=[0, 105],
                    title="Health %",
                ),
                showlegend=False,
            )
        )
        st.plotly_chart(fig_agents, use_container_width=True, key="agents")
    elif agent_data:
        for a in agent_data:
            icon = "\U0001f7e2" if a["status"] == "ok" else (
                "\U0001f7e1" if a["status"] == "warn" else "\U0001f534"
            )
            st.markdown(f"{icon} **{a['name']}** — {a['health']}%")


# ╔══════════════════════════════════════════════════════════════════╗
# ║  PANEL 2: CORTEX KNOWLEDGE CORE (center)                       ║
# ╚══════════════════════════════════════════════════════════════════╝

with col_center:
    st.markdown(
        '<div class="omega-panel">'
        '<div class="omega-panel-title">'
        '\U0001f9e0 Cortex Knowledge Core</div></div>',
        unsafe_allow_html=True,
    )

    if HAS_PLOTLY and HAS_TRINITY:
        # Build neural network graph from CosmicRole tiers
        tier_config = {
            1: {"name": "TRINITY", "color": PLOTLY_CYAN, "size": 28, "y": 4},
            2: {"name": "GUARDIANS", "color": PLOTLY_GREEN, "size": 22, "y": 3},
            3: {"name": "SPECIALISTS", "color": PLOTLY_ORANGE, "size": 18, "y": 2},
            4: {"name": "INFRA", "color": PLOTLY_PURPLE, "size": 16, "y": 1},
            5: {"name": "SINGULARITY", "color": "#ff3366", "size": 24, "y": 5},
        }

        # Groepeer roles per tier
        tiers = {}
        for role in CosmicRole:
            t = CosmicRole.get_tier(role)
            tiers.setdefault(t, []).append(role)

        node_x, node_y, node_text, node_color, node_size = [], [], [], [], []
        node_positions = {}

        for tier_num, roles in sorted(tiers.items()):
            tc = tier_config.get(tier_num, tier_config[4])
            count = len(roles)
            for i, role in enumerate(roles):
                x = (i - (count - 1) / 2) * 1.5
                y = tc["y"]
                # Add slight jitter for visual interest
                if HAS_NUMPY:
                    y += float(np.random.uniform(-0.15, 0.15))

                node_x.append(x)
                node_y.append(y)
                node_text.append(role.name)
                node_color.append(tc["color"])
                node_size.append(tc["size"])
                node_positions[role.name] = (x, y)

        # Build edges: connect tiers hierarchically
        edge_x, edge_y = [], []

        # Trinity connects to Guardians
        for t_role in tiers.get(1, []):
            tx, ty = node_positions[t_role.name]
            for g_role in tiers.get(2, []):
                gx, gy = node_positions[g_role.name]
                edge_x.extend([tx, gx, None])
                edge_y.extend([ty, gy, None])

        # Guardians connect to Specialists
        for g_role in tiers.get(2, []):
            gx, gy = node_positions[g_role.name]
            for s_role in tiers.get(3, []):
                sx, sy = node_positions[s_role.name]
                edge_x.extend([gx, sx, None])
                edge_y.extend([gy, sy, None])

        # Specialists connect to Infra
        for s_role in tiers.get(3, []):
            sx, sy = node_positions[s_role.name]
            for i_role in tiers.get(4, []):
                ix, iy = node_positions[i_role.name]
                edge_x.extend([sx, ix, None])
                edge_y.extend([sy, iy, None])

        # Singularity connects to Trinity (feedback loop)
        for sg_role in tiers.get(5, []):
            sgx, sgy = node_positions[sg_role.name]
            for t_role in tiers.get(1, []):
                tx, ty = node_positions[t_role.name]
                edge_x.extend([sgx, tx, None])
                edge_y.extend([sgy, ty, None])

        fig_cortex = go.Figure()

        # Edges trace
        fig_cortex.add_trace(go.Scatter(
            x=edge_x, y=edge_y,
            mode="lines",
            line=dict(color="rgba(0,212,255,0.12)", width=1),
            hoverinfo="none",
        ))

        # Nodes trace
        fig_cortex.add_trace(go.Scatter(
            x=node_x, y=node_y,
            mode="markers+text",
            marker=dict(
                size=node_size,
                color=node_color,
                line=dict(color=node_color, width=2),
                opacity=0.85,
            ),
            text=node_text,
            textposition="top center",
            textfont=dict(
                size=8, color="#e0e6ed",
                family="Fira Code, monospace",
            ),
            hovertemplate="%{text}<br>Tier %{customdata}<extra></extra>",
            customdata=[CosmicRole.get_tier(role) for role in CosmicRole],
        ))

        # Tier labels
        for tier_num, tc in tier_config.items():
            fig_cortex.add_annotation(
                x=-6, y=tc["y"],
                text=f"T{tier_num}: {tc['name']}",
                showarrow=False,
                font=dict(
                    size=9, color=tc["color"],
                    family="JetBrains Mono, monospace",
                ),
                xanchor="left",
            )

        fig_cortex.update_layout(
            **_base_layout(
                height=420,
                showlegend=False,
                xaxis=dict(
                    showgrid=False, zeroline=False,
                    showticklabels=False, range=[-7, 7],
                ),
                yaxis=dict(
                    showgrid=False, zeroline=False,
                    showticklabels=False, range=[0, 6],
                ),
            )
        )
        st.plotly_chart(fig_cortex, use_container_width=True, key="cortex")
    else:
        st.info("Plotly of trinity_models niet beschikbaar.")


# ╔══════════════════════════════════════════════════════════════════╗
# ║  PANEL 3: PULSE PROTOCOL (rechts-boven)                        ║
# ╚══════════════════════════════════════════════════════════════════╝

with col_right:
    st.markdown(
        '<div class="omega-panel">'
        '<div class="omega-panel-title">'
        '\U0001f49a Pulse Protocol</div></div>',
        unsafe_allow_html=True,
    )

    @st.fragment(run_every=3)
    def _render_pulse():
        """ECG-style heartbeat from CPU usage samples."""
        samples = []
        if HAS_PSUTIL:
            for _ in range(40):
                samples.append(psutil.cpu_percent(interval=0.05))
        else:
            # Fallback: synthetic ECG waveform
            for i in range(40):
                t = i / 40 * 4 * math.pi
                base = 20 + 10 * math.sin(t)
                spike = 50 * math.exp(-((t % (2 * math.pi) - 1.2) ** 2) / 0.05)
                samples.append(base + spike)

        if HAS_PLOTLY:
            x_vals = list(range(len(samples)))
            fig_pulse = go.Figure(go.Scatter(
                x=x_vals, y=samples,
                mode="lines",
                line=dict(
                    color=PLOTLY_GREEN, width=2,
                    shape="spline", smoothing=0.8,
                ),
                fill="tozeroy",
                fillcolor="rgba(0,255,136,0.06)",
                hovertemplate="CPU: %{y:.1f}%<extra></extra>",
            ))
            fig_pulse.update_layout(
                **_base_layout(
                    height=180,
                    xaxis=dict(
                        showgrid=False, showticklabels=False,
                        zeroline=False,
                    ),
                    yaxis=dict(
                        gridcolor=PLOTLY_GRID,
                        range=[0, 100],
                        title=dict(text="CPU %", font=dict(size=9)),
                    ),
                    margin=dict(l=40, r=10, t=10, b=20),
                )
            )
            st.plotly_chart(fig_pulse, use_container_width=True, key="pulse")
        else:
            st.line_chart(samples)

        # CPU/RAM metrics
        if HAS_PSUTIL:
            mc1, mc2 = st.columns(2)
            with mc1:
                st.metric("CPU", f"{psutil.cpu_percent():.0f}%")
            with mc2:
                ram = psutil.virtual_memory()
                st.metric("RAM", f"{ram.percent:.0f}%")

    _render_pulse()


# ╔══════════════════════════════════════════════════════════════════╗
# ║  PANEL 4: API FUEL GAUGE (rechts-midden)                       ║
# ╚══════════════════════════════════════════════════════════════════╝

    st.markdown(
        '<div class="omega-panel">'
        '<div class="omega-panel-title">'
        '\u26fd API Fuel Gauge</div></div>',
        unsafe_allow_html=True,
    )

    @st.fragment(run_every=5)
    def _render_fuel_gauge():
        """Circulaire gauge voor Groq API budget."""
        usage_pct = 0
        rpm_used = 0
        rpm_max = 30
        tpm_used = 0
        tpm_max = 30000

        km = _get_key_manager_safe()
        if km:
            try:
                with km._metrics_lock:
                    total_requests = sum(
                        a.totaal_requests for a in km._agents.values()
                    )
                    total_tokens = sum(
                        a.totaal_tokens for a in km._agents.values()
                    )
                    # Calculate RPM from current minute
                    now = time.time()
                    rpm_used = sum(
                        sum(1 for ts in a.request_timestamps if now - ts < 60)
                        for a in km._agents.values()
                    )
                    tpm_used = sum(
                        a.tokens_deze_minuut for a in km._agents.values()
                    )

                # Usage based on RPM (most constrained)
                if rpm_max > 0:
                    usage_pct = min(100, (rpm_used / rpm_max) * 100)
            except Exception:
                logger.debug("Suppressed exception in omega_sovereign_ui")

        if HAS_PLOTLY:
            # Gauge color based on usage
            if usage_pct < 50:
                bar_color = PLOTLY_GREEN
            elif usage_pct < 80:
                bar_color = PLOTLY_ORANGE
            else:
                bar_color = PLOTLY_RED

            fig_gauge = go.Figure(go.Indicator(
                mode="gauge+number",
                value=usage_pct,
                number=dict(
                    suffix="%",
                    font=dict(size=36, color=bar_color),
                ),
                gauge=dict(
                    axis=dict(
                        range=[0, 100],
                        tickwidth=1,
                        tickcolor=PLOTLY_GRID,
                        tickfont=dict(size=9, color="#64748b"),
                    ),
                    bar=dict(color=bar_color, thickness=0.75),
                    bgcolor=PLOTLY_BG,
                    borderwidth=1,
                    bordercolor=PLOTLY_GRID,
                    steps=[
                        dict(range=[0, 50], color="rgba(0,255,136,0.08)"),
                        dict(range=[50, 80], color="rgba(255,107,53,0.08)"),
                        dict(range=[80, 100], color="rgba(255,51,102,0.08)"),
                    ],
                    threshold=dict(
                        line=dict(color=PLOTLY_CYAN, width=2),
                        thickness=0.8,
                        value=usage_pct,
                    ),
                ),
            ))
            fig_gauge.update_layout(
                paper_bgcolor=PLOTLY_PAPER,
                font=dict(
                    family="Fira Code, monospace",
                    color="#e0e6ed",
                ),
                height=200,
                margin=dict(l=20, r=20, t=30, b=10),
            )
            st.plotly_chart(fig_gauge, use_container_width=True, key="gauge")
        else:
            st.metric("API Usage", f"{usage_pct:.0f}%")

        # Rate stats
        rc1, rc2 = st.columns(2)
        with rc1:
            st.metric("RPM", f"{rpm_used}/{rpm_max}")
        with rc2:
            tpm_display = f"{tpm_used // 1000}K" if tpm_used >= 1000 else str(tpm_used)
            tpm_max_display = f"{tpm_max // 1000}K"
            st.metric("TPM", f"{tpm_display}/{tpm_max_display}")

    _render_fuel_gauge()


# ╔══════════════════════════════════════════════════════════════════╗
# ║  PANEL 5: TERMINAL (links-onder)                               ║
# ╚══════════════════════════════════════════════════════════════════╝

with col_left:
    st.markdown(
        '<div class="omega-panel">'
        '<div class="omega-panel-title">'
        '\u2328 Terminal</div></div>',
        unsafe_allow_html=True,
    )

    # Session state voor terminal output
    if "term_history" not in st.session_state:
        st.session_state.term_history = [
            "\u2126 OMEGA SOVEREIGN CORE v1.0",
            "Type 'help' for available commands.",
            "",
        ]

    def _execute_command(cmd):
        """Dispatch terminal commando's."""
        cmd = cmd.strip().lower()
        lines = []

        if cmd == "help":
            lines = [
                "Available commands:",
                "  status    - System overview",
                "  agents    - List all registered agents",
                "  health    - Waakhuis health report",
                "  metrics   - Swarm metrics",
                "  bus       - NeuralBus statistics",
                "  events    - Recent bus events",
                "  keys      - API key status",
                "  cortical  - CorticalStack stats",
                "  clear     - Clear terminal",
            ]
        elif cmd == "clear":
            st.session_state.term_history = ["\u2126 Terminal cleared.", ""]
            return
        elif cmd == "status":
            lines.append(f"Timestamp: {datetime.now().isoformat()}")
            if engine:
                stats = engine.get_stats()
                lines.append(f"Queries processed: {stats.get('queries_processed', 0)}")
                lines.append(f"Active agents: {stats.get('active_agents', 0)}")
                lines.append(f"Avg response: {stats.get('avg_response_ms', 0):.1f}ms")
            else:
                lines.append("SwarmEngine: NOT LOADED")
            if HAS_PSUTIL:
                lines.append(f"CPU: {psutil.cpu_percent():.1f}%")
                lines.append(f"RAM: {psutil.virtual_memory().percent:.1f}%")
        elif cmd == "agents":
            if engine and hasattr(engine, "agents"):
                for name in sorted(engine.agents.keys()):
                    lines.append(f"  [{name}]")
                lines.append(f"Total: {len(engine.agents)} agents")
            else:
                lines.append("No agents loaded.")
        elif cmd == "health":
            wh = _get_waakhuis_safe()
            if wh:
                try:
                    rapport = wh.gezondheidsrapport()
                    for name, info in rapport.get("agents", {}).items():
                        score = info.get("gezondheid", "?")
                        dispatches = info.get("dispatches", 0)
                        lines.append(f"  {name}: {score}% ({dispatches} dispatches)")
                except Exception as e:
                    lines.append(f"Error: {e}")
            else:
                lines.append("Waakhuis not available.")
        elif cmd == "metrics":
            if engine:
                for k, v in engine._swarm_metrics.items():
                    lines.append(f"  {k}: {v}")
            else:
                lines.append("SwarmEngine not loaded.")
        elif cmd == "bus":
            bus = _get_bus_safe()
            if bus:
                stats = bus.statistieken()
                for k, v in stats.items():
                    lines.append(f"  {k}: {v}")
            else:
                lines.append("NeuralBus not available.")
        elif cmd == "events":
            bus = _get_bus_safe()
            if bus:
                stream = bus.get_context_stream(count=10)
                if stream:
                    lines.extend(stream.split("\n"))
                else:
                    lines.append("No recent events.")
            else:
                lines.append("NeuralBus not available.")
        elif cmd == "keys":
            km = _get_key_manager_safe()
            if km:
                lines.append(f"Keys loaded: {len(km._keys)}")
                with km._metrics_lock:
                    for name, agent in km._agents.items():
                        lines.append(
                            f"  {name}: {agent.totaal_requests} req, "
                            f"{agent.totaal_tokens} tok, "
                            f"{agent.totaal_429s} rate-limits"
                        )
            else:
                lines.append("KeyManager not available.")
        elif cmd == "cortical":
            if HAS_CORTICAL:
                try:
                    stack = get_cortical_stack()
                    metrics = stack.get_db_metrics()
                    for k, v in metrics.items():
                        lines.append(f"  {k}: {v}")
                except Exception as e:
                    lines.append(f"Error: {e}")
            else:
                lines.append("CorticalStack not available.")
        else:
            lines.append(f"Unknown command: '{cmd}'")
            lines.append("Type 'help' for available commands.")

        st.session_state.term_history.append(f"\u2126 > {cmd}")
        st.session_state.term_history.extend(lines)
        st.session_state.term_history.append("")

    # Input
    cmd_input = st.text_input(
        "\u2126 >",
        key="terminal_input",
        placeholder="Enter command...",
        label_visibility="collapsed",
    )
    if cmd_input:
        _execute_command(cmd_input)

    # Output
    term_output = "\n".join(st.session_state.term_history[-50:])
    st.markdown(
        f'<div class="omega-terminal">{term_output}</div>',
        unsafe_allow_html=True,
    )


# ╔══════════════════════════════════════════════════════════════════╗
# ║  PANEL 6: THE LISTENER (rechts-onder)                          ║
# ╚══════════════════════════════════════════════════════════════════╝

with col_right:
    st.markdown(
        '<div class="omega-panel">'
        '<div class="omega-panel-title">'
        '\U0001f3a7 The Listener</div></div>',
        unsafe_allow_html=True,
    )

    @st.fragment(run_every=4)
    def _render_listener():
        """NeuralBus event frequency waveform."""
        bus = _get_bus_safe()

        # Collect event frequency data
        event_counts = []
        event_labels = []

        if bus:
            try:
                with bus._lock:
                    all_types = list(bus._history.keys())

                for et in all_types[:15]:  # Top 15 event types
                    events = bus.get_history(et, count=100)
                    event_counts.append(len(events))
                    # Short label
                    label = et.replace("_", " ").title()
                    if len(label) > 15:
                        label = label[:12] + "..."
                    event_labels.append(label)
            except Exception:
                logger.debug("Suppressed exception in omega_sovereign_ui")

        if not event_counts:
            # Synthetic waveform fallback
            if HAS_NUMPY:
                t = np.linspace(0, 4 * math.pi, 60)
                wave = np.abs(np.sin(t) * np.cos(t * 0.7)) * 50
                wave += np.random.uniform(0, 10, len(t))
                event_counts = wave.tolist()
                event_labels = [f"t{i}" for i in range(len(event_counts))]
            else:
                event_counts = [
                    abs(math.sin(i / 10 * math.pi) * 30) + 5
                    for i in range(30)
                ]
                event_labels = [f"t{i}" for i in range(30)]

        if HAS_PLOTLY:
            fig_listener = go.Figure(go.Scatter(
                x=list(range(len(event_counts))),
                y=event_counts,
                mode="lines",
                line=dict(
                    color=PLOTLY_CYAN, width=2,
                    shape="spline", smoothing=1.0,
                ),
                fill="tozeroy",
                fillcolor="rgba(0,212,255,0.08)",
                hovertemplate="%{text}: %{y}<extra></extra>",
                text=event_labels,
            ))
            fig_listener.update_layout(
                **_base_layout(
                    height=180,
                    xaxis=dict(
                        showgrid=False, showticklabels=False,
                        zeroline=False,
                    ),
                    yaxis=dict(
                        gridcolor=PLOTLY_GRID,
                        title=dict(text="Events", font=dict(size=9)),
                    ),
                    margin=dict(l=40, r=10, t=10, b=20),
                )
            )
            st.plotly_chart(fig_listener, use_container_width=True, key="listener")
        else:
            st.bar_chart(event_counts)

        # Bus stats summary
        if bus:
            stats = bus.statistieken()
            bc1, bc2 = st.columns(2)
            with bc1:
                st.metric("Events", stats.get("events_gepubliceerd", 0))
            with bc2:
                st.metric("Subscribers", stats.get("subscribers", 0))

    _render_listener()


# ── BOTTOM STATUS BAR ────────────────────────────────────────────

st.markdown('<div class="glow-line"></div>', unsafe_allow_html=True)

sb1, sb2, sb3, sb4 = st.columns(4)
with sb1:
    if engine:
        stats = engine.get_stats()
        st.markdown(
            f'<span style="color:#00ff88;font-size:0.75em;'
            f'font-family:Fira Code,monospace">'
            f'\u25cf ONLINE | {stats.get("active_agents", 0)} agents</span>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<span style="color:#ff3366;font-size:0.75em;'
            'font-family:Fira Code,monospace">'
            '\u25cb OFFLINE</span>',
            unsafe_allow_html=True,
        )
with sb2:
    if HAS_PSUTIL:
        cpu = psutil.cpu_percent()
        st.markdown(
            f'<span style="color:#64748b;font-size:0.75em;'
            f'font-family:Fira Code,monospace">'
            f'CPU {cpu:.0f}% | RAM {psutil.virtual_memory().percent:.0f}%'
            f'</span>',
            unsafe_allow_html=True,
        )
with sb3:
    if HAS_CORTICAL:
        try:
            stack = get_cortical_stack()
            recent = stack.get_recent_events(count=1)
            if recent:
                last_event = recent[0].get("event_type", "?")
                st.markdown(
                    f'<span style="color:#64748b;font-size:0.75em;'
                    f'font-family:Fira Code,monospace">'
                    f'Last: {last_event}</span>',
                    unsafe_allow_html=True,
                )
        except Exception:
            logger.debug("Suppressed exception in omega_sovereign_ui")
with sb4:
    st.markdown(
        f'<span style="color:#64748b;font-size:0.75em;'
        f'font-family:Fira Code,monospace;float:right">'
        f'\u2126 SOVEREIGN CORE // {datetime.now().strftime("%H:%M:%S")}'
        f'</span>',
        unsafe_allow_html=True,
    )
