"""
SANCTUARY INTERFACE — The Glass Box UI v2.0
============================================

Mission Control Dashboard voor de Prometheus Federation.
Live Hub & Spoke pipeline visualisatie:
  Links:   The Feed (Weaver synthese output)
  Rechts:  Swarm Activity (LIVE pipeline stappen)
  Sidebar: System State (Governor, Chronos, Agents)

v2.0: Live pipeline — st.status containers tonen elke
      stap TERWIJL de pipeline draait, niet achteraf.

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
    .pipeline-step {
        border-left: 2px solid #30363d;
        padding-left: 12px;
        margin-bottom: 6px;
    }
    .step-ok {
        color: #3fb950;
    }
    .step-active {
        color: #f0883e;
    }
    .step-error {
        color: #f85149;
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


def vang_chain_output(brain, prompt):
    """Voer chain_of_command uit en vang stdout op."""
    buf = io.StringIO()
    with redirect_stdout(buf):
        result = brain.chain_of_command(prompt)
    log = buf.getvalue()
    return result, log


# --- BRAIN LADEN ---
brain, boot_log = laad_brain()

# Imports die brain nodig hebben
from danny_toolkit.brain.trinity_omega import (
    CosmicRole,
    TaskPriority,
    NodeTier,
    TaskResult,
)


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
    'Sanctuary // Nexus — The Glass Box UI v2.0</p>',
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

# Session state
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


# --- SWARM ACTIVITY (rechts) — Opgeslagen logs ---
with swarm_col:
    st.markdown(
        '<p class="hub-spoke-label">'
        'Swarm Activity — Live Pipeline</p>',
        unsafe_allow_html=True,
    )

    if st.session_state.swarm_logs:
        # Toon laatste pipeline-stappen
        laatste = st.session_state.swarm_logs[-1]
        stappen = laatste.get("stappen", [])

        if stappen:
            for stap in stappen:
                icoon = stap.get("icoon", "\u26aa")
                agent = stap.get("agent", "?")
                detail = stap.get("detail", "")
                st.markdown(
                    f"{icoon} **{agent}** — {detail}"
                )
        else:
            # Fallback: ruwe log tonen
            st.code(
                laatste.get("log", ""),
                language="text",
            )

        # Volledige log in expander
        with st.expander(
            "Volledige Pipeline Log", expanded=False
        ):
            st.code(
                laatste.get("log", ""),
                language="text",
            )
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
                e_stappen = entry.get("stappen", [])
                if e_stappen:
                    for stap in e_stappen:
                        st.markdown(
                            f"  {stap['icoon']} "
                            f"{stap['agent']}: "
                            f"{stap['detail']}"
                        )
                else:
                    st.code(
                        entry.get("log", "")[:500],
                        language="text",
                    )
                st.divider()


# --- INPUT ---
if prompt := st.chat_input(
    "Geef instructies aan de Swarm..."
):
    # User bericht toevoegen aan history
    st.session_state.messages.append({
        "role": "user",
        "content": prompt,
        "avatar": "\U0001f464",
    })

    # User bericht direct tonen in feed
    with feed_col:
        with st.chat_message("user", avatar="\U0001f464"):
            st.markdown(prompt)

    # ============================================
    # HUB & SPOKE — Live Pipeline Visualisatie
    # ============================================
    if modus == "Hub & Spoke (route_task)":
        pipeline_stappen = []
        pipeline_log_lines = []
        assigned = "?"
        output = ""
        status_tekst = ""

        with swarm_col:
            with st.status(
                "\U0001f680 Hub & Spoke Pipeline...",
                expanded=True,
            ) as pipeline_status:

                # ── STAP 1: Governor Gate ──
                st.write(
                    "\U0001f6e1\ufe0f **Stap 1: "
                    "Governor Gate**"
                )
                safe, reason = brain._governor_gate(
                    prompt
                )

                if safe:
                    st.write(
                        "\u2003\u2003\u2705 Doorgelaten"
                    )
                    pipeline_stappen.append({
                        "icoon": "\U0001f7e2",
                        "agent": "Governor",
                        "detail": "Doorgelaten",
                    })
                    pipeline_log_lines.append(
                        "[GOVERNOR] OK - Doorgelaten"
                    )
                else:
                    st.write(
                        f"\u2003\u2003\u274c "
                        f"GEBLOKKEERD: {reason}"
                    )
                    pipeline_stappen.append({
                        "icoon": "\U0001f534",
                        "agent": "Governor",
                        "detail": f"GEBLOKKEERD: "
                                  f"{reason}",
                    })
                    pipeline_log_lines.append(
                        f"[GOVERNOR] BLOCKED - {reason}"
                    )
                    pipeline_status.update(
                        label="\u274c Pipeline "
                              "Geblokkeerd",
                        state="error",
                        expanded=True,
                    )
                    # Sla fout op en toon
                    assigned = "Governor"
                    output = (
                        f"Pipeline geblokkeerd: "
                        f"{reason}"
                    )
                    status_tekst = "BLOCKED"

                    st.session_state.swarm_logs.append({
                        "prompt": prompt,
                        "log": "\n".join(
                            pipeline_log_lines
                        ),
                        "stappen": pipeline_stappen,
                        "tijd": datetime.now().strftime(
                            "%H:%M:%S"
                        ),
                        "assigned": assigned,
                    })
                    response = (
                        f"**[{assigned}]** | "
                        f"Status: `{status_tekst}`"
                        f"\n\n{output}"
                    )
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": response,
                        "avatar": "\U0001f916",
                    })
                    with feed_col:
                        with st.chat_message(
                            "assistant",
                            avatar="\U0001f916",
                        ):
                            st.markdown(response)
                    st.stop()

                time.sleep(0.4)

                # ── STAP 2: Chronos Context ──
                st.write(
                    "\u23f0 **Stap 2: "
                    "Chronos Context Injectie**"
                )
                enriched = brain._chronos_enrich(prompt)
                chronos_prefix = enriched[
                    :enriched.index("]") + 1
                ]
                st.write(
                    f"\u2003\u2003\u2705 "
                    f"`{chronos_prefix}`"
                )
                pipeline_stappen.append({
                    "icoon": "\U0001f535",
                    "agent": "Chronos",
                    "detail": chronos_prefix,
                })
                pipeline_log_lines.append(
                    f"[CHRONOS] {chronos_prefix}"
                )
                time.sleep(0.4)

                # ── STAP 3: Nexus Classificatie ──
                st.write(
                    "\U0001f500 **Stap 3: "
                    "Nexus Classificatie**"
                )
                buf = io.StringIO()
                with redirect_stdout(buf):
                    category = brain._nexus_classify(
                        enriched
                    )
                nexus_log = buf.getvalue()

                role = brain.NEXUS_CATEGORIES.get(
                    category, CosmicRole.ECHO
                )
                st.write(
                    f"\u2003\u2003\u2705 Categorie: "
                    f"**{category}** \u2192 "
                    f"**{role.name}**"
                )
                pipeline_stappen.append({
                    "icoon": "\U0001f7e3",
                    "agent": "Nexus",
                    "detail": (
                        f"{category} \u2192 "
                        f"{role.name}"
                    ),
                })
                pipeline_log_lines.append(
                    f"[NEXUS] {category} -> "
                    f"{role.name}"
                )
                time.sleep(0.4)

                # ── STAP 4: Specialist Uitvoering ──
                st.write(
                    f"\u2699\ufe0f **Stap 4: "
                    f"{role.name} Uitvoering**"
                )
                st.write(
                    f"\u2003\u2003\u23f3 "
                    f"*{role.name} denkt na...*"
                )

                buf = io.StringIO()
                with redirect_stdout(buf):
                    if category == "SYSTEM":
                        result = brain._deploy_swarm(
                            enriched,
                            TaskPriority.MEDIUM,
                        )
                    else:
                        result = brain._assign(
                            role,
                            enriched,
                            TaskPriority.MEDIUM,
                        )
                specialist_log = buf.getvalue()

                if result.status == "TASK_COMPLETED":
                    st.write(
                        f"\u2003\u2003\u2705 "
                        f"{result.assigned_to}: "
                        f"voltooid "
                        f"({result.execution_time:.1f}s)"
                    )
                else:
                    st.write(
                        f"\u2003\u2003\u26a0\ufe0f "
                        f"{result.assigned_to}: "
                        f"{result.status}"
                    )

                pipeline_stappen.append({
                    "icoon": "\U0001f7e0",
                    "agent": result.assigned_to,
                    "detail": (
                        f"{result.status} "
                        f"({result.execution_time:.1f}s)"
                    ),
                })
                pipeline_log_lines.append(
                    f"[SPECIALIST] {result.assigned_to}"
                    f" -> {result.status}"
                )
                if specialist_log.strip():
                    pipeline_log_lines.append(
                        specialist_log.strip()
                    )

                assigned = result.assigned_to
                output = (
                    str(result.result)
                    if result.result
                    else result.status
                )
                status_tekst = result.status
                time.sleep(0.3)

                # ── STAP 5: Weaver Synthese ──
                if (
                    category != "CASUAL"
                    and result.status == "TASK_COMPLETED"
                    and result.result
                ):
                    st.write(
                        "\U0001f9f5 **Stap 5: "
                        "Weaver Synthese**"
                    )
                    st.write(
                        "\u2003\u2003\u23f3 "
                        "*Weaver formatteert...*"
                    )

                    buf = io.StringIO()
                    with redirect_stdout(buf):
                        synthesized = (
                            brain._weaver_synthesize(
                                str(result.result),
                                prompt,
                            )
                        )
                    weaver_log = buf.getvalue()

                    if synthesized:
                        output = synthesized
                        assigned = (
                            f"{result.assigned_to}"
                            f" \u2192 Weaver"
                        )
                        st.write(
                            "\u2003\u2003\u2705 "
                            "Synthese voltooid"
                        )
                    else:
                        st.write(
                            "\u2003\u2003\u26a0\ufe0f "
                            "Synthese overgeslagen "
                            "(raw output)"
                        )

                    pipeline_stappen.append({
                        "icoon": "\U0001f7e2",
                        "agent": "Weaver",
                        "detail": "Synthese voltooid",
                    })
                    pipeline_log_lines.append(
                        "[WEAVER] Synthese voltooid"
                    )
                    if weaver_log.strip():
                        pipeline_log_lines.append(
                            weaver_log.strip()
                        )

                # Pipeline voltooid
                pipeline_status.update(
                    label="\u2705 Pipeline Voltooid "
                          f"— {assigned}",
                    state="complete",
                    expanded=False,
                )

        # Sla pipeline op in session_state
        st.session_state.swarm_logs.append({
            "prompt": prompt,
            "log": "\n".join(pipeline_log_lines),
            "stappen": pipeline_stappen,
            "tijd": datetime.now().strftime("%H:%M:%S"),
            "assigned": assigned,
        })

        # Toon resultaat in feed
        response = (
            f"**[{assigned}]** | "
            f"Status: `{status_tekst}`\n\n"
            f"{output}"
        )
        st.session_state.messages.append({
            "role": "assistant",
            "content": response,
            "avatar": "\U0001f916",
        })

        with feed_col:
            with st.chat_message(
                "assistant", avatar="\U0001f916"
            ):
                st.markdown(response)

    # ============================================
    # CHAIN OF COMMAND — Live Stap Visualisatie
    # ============================================
    else:
        coc_stappen = []
        coc_log_lines = []

        with swarm_col:
            with st.status(
                "\u26d3\ufe0f Chain of Command...",
                expanded=True,
            ) as coc_status:

                # Stap 1: Pixel ontvangt
                st.write(
                    "\U0001f4e1 **Stap 1: Pixel "
                    "ontvangt opdracht**"
                )
                coc_stappen.append({
                    "icoon": "\U0001f4e1",
                    "agent": "Pixel",
                    "detail": "Opdracht ontvangen",
                })
                time.sleep(0.3)

                # Stap 2: Iolaax analyseert
                st.write(
                    "\U0001f9e0 **Stap 2: Iolaax "
                    "analyseert domeinen**"
                )
                st.write(
                    "\u2003\u2003\u23f3 "
                    "*Domein-detectie actief...*"
                )
                coc_stappen.append({
                    "icoon": "\U0001f9e0",
                    "agent": "Iolaax",
                    "detail": "Analyseert domeinen",
                })
                time.sleep(0.3)

                # Voer chain uit
                result, log = vang_chain_output(
                    brain, prompt
                )

                # Stap 3: Toon betrokken nodes
                nodes = result.get(
                    "nodes_betrokken", []
                )
                sub_taken = result.get("sub_taken", [])

                st.write(
                    "\u2699\ufe0f **Stap 3: "
                    "Specialisten actief**"
                )
                for st_item in sub_taken:
                    node_naam = st_item.get("node", "?")
                    node_status = st_item.get(
                        "status", "?"
                    )
                    icoon = (
                        "\u2705"
                        if "COMPLETED" in node_status
                        else "\u26a0\ufe0f"
                    )
                    st.write(
                        f"\u2003\u2003{icoon} "
                        f"**{node_naam}**: "
                        f"{node_status}"
                    )
                    coc_stappen.append({
                        "icoon": icoon,
                        "agent": node_naam,
                        "detail": node_status,
                    })

                time.sleep(0.3)

                # Stap 4: Synthese
                success_count = result.get(
                    "success_count", 0
                )
                total_sub = len(sub_taken)
                st.write(
                    f"\U0001f9f5 **Stap 4: Synthese** "
                    f"— {success_count}/{total_sub} "
                    f"sub-taken geslaagd"
                )
                coc_stappen.append({
                    "icoon": "\U0001f9f5",
                    "agent": "Synthese",
                    "detail": (
                        f"{success_count}/"
                        f"{total_sub} geslaagd"
                    ),
                })

                coc_log_lines.append(log)

                coc_status.update(
                    label=(
                        f"\u2705 Chain Voltooid — "
                        f"{success_count}/{total_sub}"
                        f" geslaagd"
                    ),
                    state="complete",
                    expanded=False,
                )

        # Sla op
        assigned = " \u2192 ".join(nodes)
        status_tekst = (
            f"{success_count}/{total_sub} "
            f"sub-taken geslaagd"
        )
        output = str(
            result.get("antwoord", "Geen antwoord")
        )

        st.session_state.swarm_logs.append({
            "prompt": prompt,
            "log": "\n".join(coc_log_lines),
            "stappen": coc_stappen,
            "tijd": datetime.now().strftime("%H:%M:%S"),
            "assigned": assigned,
        })

        response = (
            f"**[{assigned}]** | "
            f"Status: `{status_tekst}`\n\n"
            f"{output}"
        )
        st.session_state.messages.append({
            "role": "assistant",
            "content": response,
            "avatar": "\U0001f916",
        })

        with feed_col:
            with st.chat_message(
                "assistant", avatar="\U0001f916"
            ):
                st.markdown(response)
