"""
PRISM DASHBOARD — Omega Sovereign Command UI v1.0.


===================================================

Live monitoring dashboard voor het Omega Sovereign Core.
Vier panelen bieden real-time inzicht in het systeem:

  1. THE PULSE   — NeuralBus event stream (Tri-Color Symphony)
  2. THE SHIELD  — Aegis stats (EventSigner, HallucinatieSchild)
  3. THE VAULT   — Hash-Chain integriteit & Memory Interface
  4. THE SWARM   — Agent health scores & hardware status

Beveiligingsconstraint:
  - Alleen localhost (IronDome Wet #4 compliant)
  - NeuralBus READ-ONLY — geen publish vanuit dashboard
  - Geen externe verbindingen

Gebruik:
    streamlit run danny_toolkit/apps/prism_dashboard.py --server.port 8501
"""

from __future__ import annotations

import os
import sys
import time
from datetime import datetime
from pathlib import Path

# ── Pad setup voor imports ──
_ROOT = Path(__file__).parent.parent.parent.resolve()
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

try:
    import streamlit as st
except ImportError:
    print("Streamlit niet geïnstalleerd: pip install streamlit")
    sys.exit(1)


# ══════════════════════════════════════════════════════════════
#  PAGE CONFIG
# ══════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="Ω PRISM // Sovereign Core",
    page_icon="🔱",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Custom CSS ──
st.markdown("""
<style>
    .stApp { background-color: #0a0e14; }
    [data-testid="stSidebar"] { background-color: #0d1117; }
    div[data-testid="stMetric"] {
        background-color: #131820;
        padding: 10px 14px;
        border-radius: 8px;
        border-left: 3px solid #00d4ff;
    }
    .prism-header {
        font-size: 0.7em;
        letter-spacing: 3px;
        text-transform: uppercase;
        color: #58a6ff;
        font-family: monospace;
        margin-bottom: 4px;
    }
    .pulse-green { color: #3fb950; font-family: monospace; font-size: 0.85em; }
    .pulse-yellow { color: #d29922; font-family: monospace; font-size: 0.85em; }
    .pulse-red { color: #f85149; font-family: monospace; font-size: 0.85em; }
    .pulse-cyan { color: #58a6ff; font-family: monospace; font-size: 0.85em; }
    .vault-ok { color: #3fb950; font-weight: bold; }
    .vault-broken { color: #f85149; font-weight: bold; }
    .agent-healthy { color: #3fb950; }
    .agent-degraded { color: #d29922; }
    .agent-critical { color: #f85149; }
    .shield-stat {
        background-color: #131820;
        border-radius: 6px;
        padding: 8px;
        margin: 4px 0;
        border-left: 3px solid #8b5cf6;
    }
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
#  LAZY BACKEND LOADERS
# ══════════════════════════════════════════════════════════════

@st.cache_resource
def load_bus() -> None:
    """NeuralBus singleton — read-only."""
    try:
        from danny_toolkit.core.neural_bus import get_bus
        return get_bus()
    except ImportError:
        return None


@st.cache_resource
def load_waakhuis() -> None:
    """WaakhuisMonitor singleton."""
    try:
        from danny_toolkit.brain.waakhuis import get_waakhuis
        return get_waakhuis()
    except ImportError:
        return None


@st.cache_resource
def load_cortical_stack() -> None:
    """CorticalStack singleton."""
    try:
        from danny_toolkit.brain.cortical_stack import get_cortical_stack
        return get_cortical_stack()
    except ImportError:
        return None


@st.cache_resource
def load_memory_interface() -> None:
    """SecureMemoryInterface singleton."""
    try:
        from danny_toolkit.omega_sovereign_core.memory_interface import (
            get_memory_interface,
        )
        return get_memory_interface()
    except ImportError:
        return None


@st.cache_resource
def load_event_signer() -> None:
    """EventSigner singleton."""
    try:
        from danny_toolkit.omega_sovereign_core.event_signing import (
            get_event_signer,
        )
        return get_event_signer()
    except ImportError:
        return None


@st.cache_resource
def load_hallucination_shield() -> None:
    """HallucinatieSchild singleton."""
    try:
        from danny_toolkit.brain.hallucination_shield import (
            get_hallucination_shield,
        )
        return get_hallucination_shield()
    except ImportError:
        return None


@st.cache_resource
def load_lockdown_manager() -> None:
    """LockdownManager singleton."""
    try:
        from danny_toolkit.omega_sovereign_core.lockdown import (
            get_lockdown_manager,
        )
        return get_lockdown_manager()
    except ImportError:
        return None


# ══════════════════════════════════════════════════════════════
#  HEADER
# ══════════════════════════════════════════════════════════════

def render_header() -> None:
    """Top banner met systeemstatus."""
    lockdown = load_lockdown_manager()
    is_locked = lockdown.is_locked if lockdown else False

    status_color = "#f85149" if is_locked else "#3fb950"
    status_text = "LOCKDOWN" if is_locked else "SOVEREIGN"
    now = datetime.now().strftime("%H:%M:%S")

    col1, col2, col3 = st.columns([4, 4, 2])
    with col1:
        st.markdown(
            f"# <span style='color:#00d4ff'>&#937;</span> PRISM DASHBOARD",
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            f"<div style='text-align:center; padding-top:16px;'>"
            f"<span style='color:{status_color}; font-size:1.1em; "
            f"font-weight:bold; letter-spacing:2px;'>"
            f"&#9679; {status_text}</span></div>",
            unsafe_allow_html=True,
        )
    with col3:
        st.markdown(
            f"<div style='text-align:right; padding-top:16px; color:#8b949e; "
            f"font-family:monospace;'>{now}</div>",
            unsafe_allow_html=True,
        )
    st.divider()


# ══════════════════════════════════════════════════════════════
#  PANEL 1: THE PULSE — NeuralBus Event Stream
# ══════════════════════════════════════════════════════════════

_TRI_COLOR_MAP = {
    # Groen = succes, gezond, OK
    "HEALTH_STATUS_CHANGE": "green", "WAAKHUIS_HEALTH": "green",
    "FORGE_SUCCESS": "green", "AGENT_CIRCUIT_CLOSED": "green",
    "CONFIG_AUDIT_COMPLETE": "green", "PRUNING_COMPLETE": "green",
    # Geel = actie, bezig, verwerking
    "MISSION_STARTED": "yellow", "STEP_COMPLETED": "yellow",
    "LEARNING_CYCLE_STARTED": "yellow", "SYNAPSE_UPDATED": "yellow",
    "PHANTOM_PREDICTION": "yellow", "SANDBOX_EXECUTION": "yellow",
    "SHARD_QUERY_ROUTED": "yellow", "REQUEST_TRACE_COMPLETE": "yellow",
    "PRUNING_STARTED": "yellow",
    # Rood = alarm, fout, blokkade
    "HALLUCINATION_BLOCKED": "red", "ERROR_ESCALATED": "red",
    "AGENT_CIRCUIT_OPEN": "red", "CONFIG_DRIFT_DETECTED": "red",
    "IMMUNE_RESPONSE": "red", "WAAKHUIS_ALERT": "red",
    "ERROR_CLASSIFIED": "red",
}


def _event_color(event_type: str) -> str:
    """Bepaal Tri-Color klasse voor event type."""
    return _TRI_COLOR_MAP.get(event_type, "cyan")


def render_pulse() -> None:
    """Panel 1: Live NeuralBus event stream."""
    st.markdown('<div class="prism-header">THE PULSE &mdash; NEURAL BUS LIVE FEED</div>',
                unsafe_allow_html=True)

    bus = load_bus()
    if bus is None:
        st.warning("NeuralBus niet beschikbaar")
        return

    # Haal alle recente events op
    try:
        stats = bus.statistieken()
        type_count = stats.get("event_types_actief", 0)
        total_events = stats.get("events_in_history", 0)
        subscriber_count = stats.get("subscribers", 0)
    except Exception:
        stats = {}
        type_count = 0
        total_events = 0
        subscriber_count = 0

    # Metrics balk
    m1, m2, m3 = st.columns(3)
    m1.metric("Event Types", type_count)
    m2.metric("Events in Buffer", total_events)
    m3.metric("Subscribers", subscriber_count)

    # Event stream — haal context op (dict van event_type -> events)
    all_events = []
    try:
        context = bus.get_context(count=15)
        for _etype, event_list in context.items():
            for ev_dict in event_list:
                all_events.append(ev_dict)
    except Exception as _sup_err:
        logger.debug("Suppressed: %s", _sup_err)

    # Sorteer op timestamp (nieuwste eerst)
    all_events.sort(key=lambda e: e.get("timestamp", ""), reverse=True)

    # Render stream
    if not all_events:
        st.info("Geen events in buffer — systeem wacht op activiteit")
    else:
        lines = []
        for ev in all_events[:30]:
            ts_raw = ev.get("timestamp", "")
            ts_str = ts_raw[11:19] if len(ts_raw) >= 19 else "??:??:??"
            etype = ev.get("event_type", "?")
            bron = ev.get("bron", "?")
            color = _event_color(etype)
            css_class = f"pulse-{color}"

            # Data preview (eerste 80 chars)
            data = ev.get("data", {})
            preview = str(data)[:80].replace("<", "&lt;").replace(">", "&gt;")

            lines.append(
                f'<div class="{css_class}">'
                f'[{ts_str}] <b>{etype}</b> '
                f'<span style="color:#6c757d">via {bron}</span> '
                f'<span style="color:#484f58">{preview}</span>'
                f'</div>'
            )
        st.markdown("\n".join(lines), unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
#  PANEL 2: THE SHIELD — Signing & Hallucination Stats
# ══════════════════════════════════════════════════════════════

def render_shield() -> None:
    """Panel 2: EventSigner + HallucinatieSchild statistieken."""
    st.markdown('<div class="prism-header">THE SHIELD &mdash; AEGIS SECURITY LAYER</div>',
                unsafe_allow_html=True)

    # ── EventSigner Stats ──
    signer = load_event_signer()
    if signer:
        s_stats = signer.get_stats()
        st.markdown("**Event Signing (HMAC-SHA256)**")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Signed", s_stats.get("signed", 0))
        c2.metric("Verified OK", s_stats.get("verified_ok", 0))
        c3.metric("Rejected", s_stats.get("rejected", 0))
        c4.metric("Replay Blocked", s_stats.get("replay_blocked", 0))

        if s_stats.get("using_default_key"):
            st.error("SIGNING KEY IS DEFAULT — Stel OMEGA_BUS_SIGNING_KEY in via .env")
        else:
            st.success("Signing key: productie-key geladen")

        # Recente violations
        violations = signer.get_violations(count=5)
        if violations:
            st.markdown("**Recente Signing Violations:**")
            for v in violations:
                vtype = v.get("reason", "?")
                vtime = v.get("timestamp", "?")[:19]
                vbron = v.get("bron", "?")
                color = "#f85149" if "INVALID" in vtype else "#d29922"
                st.markdown(
                    f'<div class="shield-stat">'
                    f'<span style="color:{color}">{vtype}</span> '
                    f'<span style="color:#6c757d">{vtime} via {vbron}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
    else:
        st.warning("EventSigner niet beschikbaar")

    st.divider()

    # ── HallucinatieSchild Stats ──
    schild = load_hallucination_shield()
    if schild:
        h_stats = schild.get_stats()
        st.markdown("**HallucinatieSchild (Anti-Hallucination Gate)**")
        c1, c2, c3 = st.columns(3)
        c1.metric("Beoordeeld", h_stats.get("beoordeeld", 0))
        c2.metric("Geblokkeerd", h_stats.get("geblokkeerd", 0))
        blocked = h_stats.get("geblokkeerd", 0)
        total = h_stats.get("beoordeeld", 0)
        rate = (blocked / total * 100) if total > 0 else 0
        c3.metric("Block Rate", f"{rate:.1f}%")

        # Breakdown
        details = {k: v for k, v in h_stats.items()
                   if k not in ("beoordeeld", "geblokkeerd") and v > 0}
        if details:
            st.markdown("**Blokkade Redenen:**")
            for reason, count in sorted(details.items(), key=lambda x: -x[1]):
                st.markdown(
                    f'<div class="shield-stat">'
                    f'{reason}: <b>{count}</b>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
    else:
        st.info("HallucinatieSchild niet geladen")


# ══════════════════════════════════════════════════════════════
#  PANEL 3: THE VAULT — Hash-Chain & Memory Interface
# ══════════════════════════════════════════════════════════════

def render_vault() -> None:
    """Panel 3: Hash-chain integriteit & CorticalStack."""
    st.markdown('<div class="prism-header">THE VAULT &mdash; MEMORY INTEGRITY</div>',
                unsafe_allow_html=True)

    # ── Hash-Chain Status ──
    mi = load_memory_interface()
    if mi:
        chain_ok, chain_detail = mi.verify_chain_integrity()
        if chain_ok:
            st.markdown(
                f'<div class="vault-ok">CHAIN INTACT: {chain_detail}</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<div class="vault-broken">CHAIN BROKEN: {chain_detail}</div>',
                unsafe_allow_html=True,
            )

        mi_stats = mi.get_stats()
        c1, c2, c3 = st.columns(3)
        c1.metric("Stores", mi_stats.get("stores", 0))
        c2.metric("Retrieves", mi_stats.get("retrieves", 0))
        c3.metric("Receipts", mi_stats.get("receipt_count", 0))

        # Recente receipts
        receipts = mi.get_receipts(count=5)
        if receipts:
            st.markdown("**Recente State Saves:**")
            for r in receipts:
                comp = r.get("component", "?")
                ts = r.get("timestamp", "?")[:19]
                dhash = r.get("data_hash", "?")[:12]
                size = r.get("data_size", 0)
                st.markdown(
                    f'<div class="shield-stat">'
                    f'<b>{comp}</b> '
                    f'<span style="color:#6c757d">{ts}</span> '
                    f'<span style="color:#58a6ff">{dhash}...</span> '
                    f'<span style="color:#484f58">{size}B</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
    else:
        st.warning("MemoryInterface niet beschikbaar")

    st.divider()

    # ── CorticalStack DB Stats ──
    stack = load_cortical_stack()
    if stack:
        try:
            db_stats = stack.get_stats()
            db_metrics = stack.get_db_metrics()

            st.markdown("**CorticalStack (The Soul)**")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Episodic Events", db_stats.get("episodic_events", 0))
            c2.metric("Semantic Facts", db_stats.get("semantic_facts", 0))
            c3.metric("System Stats", db_stats.get("system_stats", 0))
            db_mb = db_metrics.get("db_size_mb", 0)
            c4.metric("DB Size", f"{db_mb:.1f} MB")
        except Exception as e:
            st.error(f"CorticalStack fout: {e}")
    else:
        st.info("CorticalStack niet geladen")


# ══════════════════════════════════════════════════════════════
#  PANEL 4: THE SWARM — Agent Health & Hardware
# ══════════════════════════════════════════════════════════════

_KNOWN_BRAIN_AGENTS = [
    "CentralBrain", "Tribunal", "AdversarialTribunal", "Strategist",
    "VoidWalker", "Artificer", "Dreamer", "GhostWriter", "TheMirror",
    "TheCortex", "DevOpsDaemon", "TheOracleEye", "TheSynapse",
    "ThePhantom", "VirtualTwin", "HallucinatieSchild", "WaakhuisMonitor",
]


def render_swarm() -> None:
    """Panel 4: Agent gezondheidsscores & hardware status."""
    st.markdown('<div class="prism-header">THE SWARM &mdash; AGENT HEALTH MONITOR</div>',
                unsafe_allow_html=True)

    waakhuis = load_waakhuis()
    if waakhuis is None:
        st.warning("WaakhuisMonitor niet beschikbaar")
        return

    # ── Hardware Status (altijd tonen) ──
    try:
        hw = waakhuis.hardware_status()
    except Exception:
        hw = {}

    if hw:
        st.markdown("**Hardware**")
        c1, c2, c3 = st.columns(3)
        cpu = hw.get("cpu_percent", -1)
        ram = hw.get("ram_percent", -1)
        ram_free = hw.get("ram_beschikbaar_mb", 0)
        c1.metric("CPU", f"{cpu:.0f}%" if cpu >= 0 else "N/A")
        c2.metric("RAM", f"{ram:.0f}%" if ram >= 0 else "N/A")
        c3.metric("RAM Vrij", f"{ram_free:.0f} MB")

        # GPU indien beschikbaar
        if "gpu_used_mb" in hw:
            g1, g2 = st.columns(2)
            g1.metric("GPU Used", f"{hw.get('gpu_used_mb', 0):.0f} MB")
            g2.metric("GPU Total", f"{hw.get('gpu_total_mb', 0):.0f} MB")

    st.divider()

    # ── Agent Scores ──
    try:
        dashboard = waakhuis.export_dashboard()
        rapport = dashboard.get("gezondheid", {})
        agents = rapport.get("agents", {})
        stale = dashboard.get("stale_agents", [])
        stats = dashboard.get("stats", {})
    except Exception:
        agents = {}
        stale = []
        stats = {}

    # Toon dispatches/fouten totalen
    c1, c2 = st.columns(2)
    c1.metric("Totaal Dispatches", stats.get("totaal_dispatches", 0))
    c2.metric("Totaal Fouten", stats.get("totaal_fouten", 0))

    if agents:
        st.markdown(f"**Actieve Agents ({len(agents)})**")

        # Sorteer op score (laagste eerst — problemen bovenaan)
        sorted_agents = sorted(agents.items(), key=lambda x: x[1].get("score", 100))

        for agent_name, info in sorted_agents:
            score = info.get("score", 0)
            latency = info.get("latency", {})
            fouten = info.get("fouten", {})

            if score >= 80:
                css = "agent-healthy"
                icon = "&#9679;"
            elif score >= 50:
                css = "agent-degraded"
                icon = "&#9670;"
            else:
                css = "agent-critical"
                icon = "&#9888;"

            p50 = latency.get("p50", 0)
            p95 = latency.get("p95", 0)
            err_total = fouten.get("totaal", 0) if isinstance(fouten, dict) else 0

            st.markdown(
                f'<div style="background:#131820; border-radius:6px; padding:8px 12px; '
                f'margin:4px 0;">'
                f'<span class="{css}">{icon} <b>{agent_name}</b></span> '
                f'<span style="color:#8b949e; float:right;">'
                f'Score: <b>{score:.0f}</b> &nbsp;|&nbsp; '
                f'p50: {p50:.0f}ms &nbsp;|&nbsp; '
                f'p95: {p95:.0f}ms &nbsp;|&nbsp; '
                f'Errors: {err_total}'
                f'</span></div>',
                unsafe_allow_html=True,
            )
    else:
        # Toon bekende agents als dormant
        st.markdown(f"**Brain Agents ({len(_KNOWN_BRAIN_AGENTS)}) — Dormant**")
        for name in _KNOWN_BRAIN_AGENTS:
            st.markdown(
                f'<div style="background:#131820; border-radius:6px; padding:8px 12px; '
                f'margin:3px 0;">'
                f'<span style="color:#484f58">&#9711; <b>{name}</b></span> '
                f'<span style="color:#30363d; float:right;">Standby</span>'
                f'</div>',
                unsafe_allow_html=True,
            )
        st.caption("Agents worden actief na de eerste SwarmEngine query")

    # ── Stale Agents ──
    try:
        stale = waakhuis.check_heartbeats()
        if stale:
            st.warning(f"Stale agents (>60s geen activiteit): {', '.join(stale)}")
    except Exception as _sup_err:
        logger.debug("Suppressed: %s", _sup_err)
import logging

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════
#  SIDEBAR
# ══════════════════════════════════════════════════════════════

def render_sidebar() -> None:
    """Sidebar met configuratie en acties."""
    with st.sidebar:
        st.markdown("### Prism Controls")

        # Auto-refresh
        refresh = st.selectbox(
            "Auto-refresh",
            options=[0, 5, 10, 30, 60],
            index=2,
            format_func=lambda x: "Uit" if x == 0 else f"{x}s",
        )
        if refresh > 0:
            time.sleep(0.1)  # Prevent race

        st.divider()

        # Lockdown controls
        lockdown = load_lockdown_manager()
        if lockdown:
            st.markdown("**Lockdown Manager**")
            if lockdown.is_locked:
                st.error("SYSTEEM IN LOCKDOWN")
                level = lockdown.current_level
                if level:
                    st.markdown(f"Level: **{level.value.upper()}**")
            else:
                st.success("Systeem operationeel")

            status = lockdown.get_status()
            st.markdown(f"Totaal events: **{status.get('total_events', 0)}**")
            st.markdown(f"Onopgelost: **{status.get('unresolved', 0)}**")

        st.divider()
        st.markdown(
            '<div style="color:#484f58; font-size:0.75em; text-align:center;">'
            'PRISM v1.0 // Omega Sovereign Core<br>'
            'Localhost Only // IronDome Compliant'
            '</div>',
            unsafe_allow_html=True,
        )

        return refresh


# ══════════════════════════════════════════════════════════════
#  MAIN LAYOUT
# ══════════════════════════════════════════════════════════════

def main() -> None:
    """Render het complete Prism Dashboard."""
    render_header()
    refresh_interval = render_sidebar()

    # 2x2 grid layout
    top_left, top_right = st.columns(2)
    bottom_left, bottom_right = st.columns(2)

    with top_left:
        render_pulse()

    with top_right:
        render_shield()

    with bottom_left:
        render_vault()

    with bottom_right:
        render_swarm()

    # Auto-refresh via Streamlit's native rerun
    if refresh_interval and refresh_interval > 0:
        time.sleep(refresh_interval)
        st.rerun()


if __name__ == "__main__":
    main()
