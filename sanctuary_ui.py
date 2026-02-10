"""
SANCTUARY INTERFACE — The Glass Box UI
=======================================

Mission Control Dashboard voor de Prometheus Federation.
Toont de Hub & Spoke pipeline live:
  Links:   System State (Governor, Chronos, Agents)
  Midden:  The Feed (Weaver synthese output)
  Rechts:  Swarm Activity (Nexus routing logs)

Gebruik: streamlit run sanctuary_ui.py
"""

import streamlit as st
import time
import io
import sys
from datetime import datetime
from contextlib import redirect_stdout


# --- CONFIGURATIE ---
st.set_page_config(
    page_title="Sanctuary // Nexus",
    page_icon="\U0001f9e0",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- CUSTOM CSS ---
st.markdown("""
<style>
    .stApp {
        background-color: #0e1117;
    }
    [data-testid="stSidebar"] {
        background-color: #161b22;
    }
    .agent-active {
        color: #00d4ff;
        font-weight: bold;
    }
    .agent-idle {
        color: #6c757d;
    }
    .log-line {
        font-family: 'Courier New', monospace;
        font-size: 0.85em;
        color: #8b949e;
        line-height: 1.4;
    }
    .hub-spoke-label {
        font-size: 0.75em;
        color: #58a6ff;
        letter-spacing: 2px;
        text-transform: uppercase;
    }
    div[data-testid="stMetric"] {
        background-color: #1e212b;
        padding: 8px 12px;
        border-radius: 6px;
        border-left: 3px solid #00d4ff;
    }
</style>
""", unsafe_allow_html=True)


# --- BACKEND LADEN (gecachet) ---
@st.cache_resource(show_spinner="Federation wordt gewekt...")
def laad_brain():
    """Laad PrometheusBrain eenmalig (gecachet)."""
    buf = io.StringIO()
    with redirect_stdout(buf):
        from danny_toolkit.brain.trinity_omega import (
            PrometheusBrain,
        )
        brain = PrometheusBrain()
    boot_log = buf.getvalue()
    return brain, boot_log


def vang_route_output(brain, prompt):
    """Voer route_task uit en vang stdout op."""
    buf = io.StringIO()
    with redirect_stdout(buf):
        result = brain.route_task(prompt)
    log = buf.getvalue()
    return result, log


def vang_chain_output(brain, prompt):
    """Voer chain_of_command uit en vang stdout op."""
    buf = io.StringIO()
    with redirect_stdout(buf):
        result = brain.chain_of_command(prompt)
    log = buf.getvalue()
    return result, log


def parse_pipeline_stappen(log_text):
    """Parse de Hub & Spoke log naar stappen."""
    stappen = []
    huidige = None

    for regel in log_text.split("\n"):
        regel_strip = regel.strip()
        if not regel_strip:
            continue

        if "[GOVERNOR]" in regel_strip:
            stappen.append({
                "agent": "Governor",
                "icon": "\U0001f6e1\ufe0f",
                "tekst": regel_strip,
                "type": "gate",
            })
        elif "[CHRONOS]" in regel_strip:
            stappen.append({
                "agent": "Chronos",
                "icon": "\u23f0",
                "tekst": regel_strip,
                "type": "enrich",
            })
        elif "[NEXUS]" in regel_strip:
            stappen.append({
                "agent": "Nexus",
                "icon": "\U0001f500",
                "tekst": regel_strip,
                "type": "classify",
            })
        elif "[ASSIGNED]" in regel_strip:
            stappen.append({
                "agent": "Specialist",
                "icon": "\u2699\ufe0f",
                "tekst": regel_strip,
                "type": "execute",
            })
        elif ">>> " in regel_strip and "result" in regel_strip:
            stappen.append({
                "agent": "Result",
                "icon": "\u2705",
                "tekst": regel_strip,
                "type": "result",
            })
        elif "[FALLBACK]" in regel_strip:
            stappen.append({
                "agent": "Fallback",
                "icon": "\u26a0\ufe0f",
                "tekst": regel_strip,
                "type": "fallback",
            })
        elif "HUB & SPOKE" in regel_strip:
            stappen.append({
                "agent": "Pipeline",
                "icon": "\U0001f680",
                "tekst": regel_strip,
                "type": "start",
            })

    return stappen


# --- BRAIN LADEN ---
brain, boot_log = laad_brain()


# --- SIDEBAR: SYSTEM STATE ---
with st.sidebar:
    st.markdown(
        '<p class="hub-spoke-label">'
        'System State</p>',
        unsafe_allow_html=True,
    )
    st.header("\U0001f6e1\ufe0f Governor & Chronos")

    # Governor health
    health = brain.governor.get_health_report()
    cb = health["circuit_breaker"]
    cb_status = cb["status"]
    if cb_status == "CLOSED":
        st.success(f"Governor: ONLINE ({cb_status})")
    elif cb_status == "HALF_OPEN":
        st.warning(f"Governor: HERSTEL ({cb_status})")
    else:
        st.error(f"Governor: GEBLOKKEERD ({cb_status})")

    # Chronos
    now = datetime.now()
    dag_namen = [
        "maandag", "dinsdag", "woensdag",
        "donderdag", "vrijdag", "zaterdag", "zondag",
    ]
    st.info(
        f"Chronos: {dag_namen[now.weekday()]} "
        f"{now.strftime('%d-%m-%Y %H:%M')}"
    )

    # System metrics
    st.divider()
    st.header("\U0001f9e0 Federation Status")

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Nodes", "17/17")
        st.metric("Swarm", "347")
    with col2:
        ai_status = "GROQ"
        if brain.brain and brain.brain.ai_provider:
            ai_status = brain.brain.ai_provider.upper()
        st.metric("Brain", ai_status)
        st.metric("Taken", brain._task_counter)

    # Agent status
    st.divider()
    st.header("\U0001f916 Agent Status")

    from danny_toolkit.brain.trinity_omega import (
        NodeTier,
    )

    for tier in NodeTier:
        nodes = brain.get_nodes_by_tier(tier)
        if nodes:
            with st.expander(
                f"{tier.value} ({len(nodes)} nodes)",
                expanded=(tier == NodeTier.TRINITY),
            ):
                for node in nodes:
                    status_kleur = (
                        "\U0001f7e2" if node.status == "ACTIVE"
                        else "\U0001f7e1"
                    )
                    st.markdown(
                        f"{status_kleur} **{node.name}** "
                        f"| Taken: {node.tasks_completed} "
                        f"| E: {node.energy}%"
                    )

    # Boot log
    st.divider()
    with st.expander("Boot Log", expanded=False):
        st.code(boot_log[-2000:], language="text")


# --- HOOFDSCHERM ---
st.markdown(
    '<p class="hub-spoke-label">'
    'Sanctuary // Nexus — The Glass Box UI</p>',
    unsafe_allow_html=True,
)
st.title("S A N C T U A R Y")

# Modus keuze
modus = st.radio(
    "Modus",
    ["Hub & Spoke (route_task)", "Chain of Command"],
    horizontal=True,
    label_visibility="collapsed",
)

# Chat history
if "messages" not in st.session_state:
    st.session_state.messages = []
if "swarm_logs" not in st.session_state:
    st.session_state.swarm_logs = []

# Layout: Feed (links) + Swarm Activity (rechts)
feed_col, swarm_col = st.columns([3, 2])

# --- THE FEED (links) ---
with feed_col:
    st.markdown(
        '<p class="hub-spoke-label">'
        'The Feed — Weaver Output</p>',
        unsafe_allow_html=True,
    )

    # Toon chat history
    for msg in st.session_state.messages:
        with st.chat_message(
            msg["role"], avatar=msg.get("avatar")
        ):
            st.markdown(msg["content"])

# --- SWARM ACTIVITY (rechts) ---
with swarm_col:
    st.markdown(
        '<p class="hub-spoke-label">'
        'Swarm Activity — Live Pipeline</p>',
        unsafe_allow_html=True,
    )

    if st.session_state.swarm_logs:
        # Toon laatste log
        laatste = st.session_state.swarm_logs[-1]
        stappen = parse_pipeline_stappen(
            laatste["log"]
        )

        for stap in stappen:
            kleur = {
                "gate": "\U0001f7e2",
                "enrich": "\U0001f535",
                "classify": "\U0001f7e3",
                "execute": "\U0001f7e0",
                "result": "\u2705",
                "fallback": "\U0001f7e1",
                "start": "\U0001f680",
            }.get(stap["type"], "\u26aa")

            st.markdown(
                f"{kleur} **{stap['agent']}** "
                f"` {stap['tekst'][:80]} `"
            )

        # Ruwe log in expander
        with st.expander(
            "Volledige Pipeline Log", expanded=False
        ):
            st.code(laatste["log"], language="text")
    else:
        st.markdown(
            "*Wacht op eerste instructie...*"
        )

    # Eerdere logs
    if len(st.session_state.swarm_logs) > 1:
        with st.expander(
            f"Eerdere logs "
            f"({len(st.session_state.swarm_logs) - 1})",
            expanded=False,
        ):
            for entry in reversed(
                st.session_state.swarm_logs[:-1]
            ):
                st.markdown(
                    f"**{entry['tijd']}** — "
                    f"`{entry['prompt'][:50]}...`"
                )
                st.code(
                    entry["log"][:500],
                    language="text",
                )
                st.divider()


# --- INPUT ---
if prompt := st.chat_input(
    "Geef instructies aan de Swarm..."
):
    # User bericht tonen
    st.session_state.messages.append({
        "role": "user",
        "content": prompt,
        "avatar": "\U0001f464",
    })

    # Uitvoeren
    if modus == "Hub & Spoke (route_task)":
        result, log = vang_route_output(brain, prompt)
        assigned = result.assigned_to
        status = result.status
        output = str(result.result) if result.result else status
    else:
        result, log = vang_chain_output(brain, prompt)
        assigned = " -> ".join(
            result.get("nodes_betrokken", [])
        )
        status = (
            f"{result.get('success_count', 0)}/"
            f"{len(result.get('sub_taken', []))}"
            f" sub-taken geslaagd"
        )
        output = str(
            result.get("antwoord", "Geen antwoord")
        )

    # Swarm log opslaan
    st.session_state.swarm_logs.append({
        "prompt": prompt,
        "log": log,
        "tijd": datetime.now().strftime("%H:%M:%S"),
        "assigned": assigned,
    })

    # Weaver response samenstellen
    response = (
        f"**[{assigned}]** | Status: `{status}`\n\n"
        f"{output}"
    )

    st.session_state.messages.append({
        "role": "assistant",
        "content": response,
        "avatar": "\U0001f916",
    })

    # Rerun om alles te tonen
    st.rerun()
