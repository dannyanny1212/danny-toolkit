
"""
SANCTUARY INTERFACE — The Glass Box UI v5.0
============================================

Mission Control Dashboard voor de Prometheus Federation.
Live Hub & Spoke pipeline visualisatie:
  Links:   The Feed (Weaver synthese output)
  Rechts:  Swarm Activity (LIVE pipeline log)
  Sidebar: System State (Governor, Chronos, Agents)

v5.0: Rich Media Protocol — contextual charts en code
      blocks naast tekst-output. CRYPTO → line_chart,
      HEALTH → area_chart, DATA → bar_chart,
      CODE → code block.

Gebruik: streamlit run sanctuary_ui.py
"""

import streamlit as st
import io
import os
from pathlib import Path
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


# --- BRAIN LADEN ---
brain, boot_log = laad_brain()

# Imports die brain nodig hebben
from danny_toolkit.brain.trinity_omega import NodeTier
from swarm_engine import run_swarm_sync, SwarmPayload
from swarm_core import run_chain_pipeline


def render_media(container, media):
    """Render rich media (chart/code) in container.

    Args:
        container: st of st.chat_message context.
        media: dict met type/data/extra/code keys,
               of None (geen visual).
    """
    if not media:
        return

    media_type = media.get("type")

    if media_type == "metrics":
        container.caption(
            "\U0001f4c8 Cipher Market Live-Feed"
        )
        metrics = media.get("metrics", [])
        if metrics:
            cols = container.columns(len(metrics))
            for idx, metric in enumerate(metrics):
                cols[idx].metric(
                    label=metric["label"],
                    value=metric["value"],
                    delta=metric["delta"],
                    delta_color=metric.get(
                        "delta_color", "normal"
                    ),
                )
        # 30d chart onder de tickers
        if "data" in media:
            container.line_chart(media["data"])
        if "extra" in media:
            container.bar_chart(media["extra"])
    elif media_type == "line_chart":
        container.line_chart(media["data"])
        if "extra" in media:
            container.bar_chart(media["extra"])
    elif media_type == "area_chart":
        container.area_chart(media["data"])
    elif media_type == "bar_chart":
        container.bar_chart(media["data"])
    elif media_type == "code":
        container.code(
            media.get("code", ""), language="python"
        )


def render_payload(container, p):
    """Render een SwarmPayload in een Streamlit container.

    Args:
        container: st of st.chat_message context.
        p: SwarmPayload object.
    """
    if p.type == "code":
        container.caption(
            f"\U0001f4bb {p.agent}"
        )
        container.code(
            p.content, language="python",
        )
    elif p.type == "metrics":
        container.caption(
            f"\U0001f4c8 {p.agent} Ticker"
        )
        media = p.metadata.get("media")
        render_media(container, media)
    elif p.type in (
        "area_chart", "bar_chart", "line_chart",
    ):
        container.caption(
            f"\U0001f4ca {p.agent}"
        )
        media = p.metadata.get("media")
        render_media(container, media)
    elif p.type == "image_analysis":
        container.caption(
            f"\U0001f5bc {p.agent} | Vision"
        )
        content = p.content or {}
        if isinstance(content, dict):
            img_path = content.get("image_path", "")
            if img_path and os.path.isfile(img_path):
                container.image(img_path)
            elif img_path:
                container.info(
                    f"Afbeelding: {img_path}"
                )
        container.markdown(str(p.display_text))
    elif p.type == "research_report":
        container.markdown(
            "### \U0001f4da Memex Analyse"
        )
        container.markdown(str(p.display_text))
        data = p.content
        if isinstance(data, dict):
            with container.expander(
                "\U0001f50d Bekijk"
                " Onderzoeksdata & Bronnen"
            ):
                st.caption(
                    "\U0001f9e0 ZOEKSTRATEGIE (PLAN)"
                )
                tags = "".join(
                    "<span style='"
                    "background:#333;"
                    "padding:4px 8px;"
                    "border-radius:4px;"
                    "margin-right:5px;"
                    "font-size:0.85em'>"
                    f"\U0001f50d {q}</span>"
                    for q in data.get(
                        "queries", []
                    )
                )
                st.markdown(
                    tags,
                    unsafe_allow_html=True,
                )
                st.divider()
                src_count = data.get(
                    "sources_count", 0
                )
                frags = data.get(
                    "total_fragments",
                    src_count,
                )
                st.caption(
                    "\U0001f4c4 GEVONDEN"
                    f" BRONNEN ({src_count}"
                    f" documenten,"
                    f" {frags} fragmenten)"
                )
                src_list = data.get(
                    "sources_list", []
                )
                for s in src_list:
                    st.markdown(
                        f"- \U0001f4ce `{s}`"
                    )
                st.divider()
                if data.get("used_web"):
                    st.warning(
                        "\U0001f310 Kennisgat:"
                        " Navigator Web Search"
                        " ingezet."
                    )
                else:
                    st.info(
                        "\U0001f9e0 ChromaDB +"
                        " CorticalStack"
                        " \u2014 Dual Memory."
                    )
    else:
        container.markdown(
            f"**[{p.agent}]**\n"
            f"{p.display_text}"
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

    # --- FEED THE MIND ---
    st.divider()
    st.header("\U0001f4c2 FEED THE MIND")

    uploaded_files = st.file_uploader(
        "Upload Kennis (PDF/TXT/MD/PY)",
        accept_multiple_files=True,
        type=["pdf", "txt", "md", "py"],
    )

    if uploaded_files:
        if st.button(
            f"\U0001f4e5 Verwerk"
            f" {len(uploaded_files)} bestanden"
        ):
            progress_bar = st.progress(0)
            status_text = st.empty()

            # 1. Bestanden opslaan
            save_dir = str(
                Path(__file__).parent
                / "data" / "rag" / "documenten"
            )
            os.makedirs(save_dir, exist_ok=True)

            for i, uf in enumerate(uploaded_files):
                file_path = os.path.join(
                    save_dir, uf.name
                )
                with open(file_path, "wb") as f:
                    f.write(uf.getbuffer())
                status_text.text(
                    f"Opgeslagen: {uf.name}"
                )
                progress_bar.progress(
                    (i + 1)
                    / len(uploaded_files)
                    * 0.5
                )

            # 2. Ingesteren via TheLibrarian
            status_text.text(
                "The Librarian: Indexing Vectors..."
            )
            try:
                from ingest import TheLibrarian
                lib = TheLibrarian()
                lib.ingest(pad=save_dir)
                progress_bar.progress(1.0)
                count = lib.collection.count()
                status_text.success(
                    f"Kennis geabsorbeerd!"
                    f" ({count} chunks in DB)"
                )
                st.balloons()
            except Exception as e:
                status_text.error(
                    f"Fout bij ingest: {e}"
                )


# --- HOOFDSCHERM ---
st.markdown(
    '<p class="hub-spoke-label">'
    'Sanctuary // Nexus — The Glass Box UI v5.0</p>',
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
            if msg.get("payloads"):
                # v5.0 per-payload replay
                st.markdown(msg["content"].split(
                    "\n\n"
                )[0])
                for p in msg["payloads"]:
                    render_payload(st, p)
            else:
                st.markdown(msg["content"])


# --- SWARM ACTIVITY (rechts) — Opgeslagen logs ---
with swarm_col:
    st.markdown(
        '<p class="hub-spoke-label">'
        'Swarm Activity — Live Pipeline</p>',
        unsafe_allow_html=True,
    )

    if st.session_state.swarm_logs:
        # Toon laatste pipeline log
        laatste = st.session_state.swarm_logs[-1]
        log_tekst = laatste.get("log", "")

        if log_tekst:
            st.code(log_tekst, language="bash")
        else:
            st.markdown(
                "*Geen log beschikbaar.*"
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
                st.code(
                    entry.get("log", "")[:500],
                    language="bash",
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
        with st.chat_message(
            "user", avatar="\U0001f464"
        ):
            st.markdown(prompt)

    # Live pipeline log in rechterkolom
    with swarm_col:
        log_placeholder = st.empty()
        logs = []

        def update_ui_log(message):
            """Callback: voegt regel toe en update
            de live log in de rechterkolom."""
            logs.append(message)
            log_text = "\n".join(
                f"> {line}" for line in logs
            )
            log_placeholder.code(
                log_text, language="bash"
            )

        # ===========================================
        # HUB & SPOKE — Callback Pipeline
        # ===========================================
        swarm_error = None
        if modus == "Hub & Spoke (route_task)":
            try:
                with st.spinner(
                    "\U0001f680 Swarm Processing..."
                ):
                    payloads = run_swarm_sync(
                        prompt, brain,
                        callback=update_ui_log,
                    )
            except Exception as e:
                swarm_error = str(e)
                payloads = []

            # Aggregeer header info uit payloads
            agents = [p.agent for p in payloads]
            assigned = " \u2192 ".join(agents)
            status_tekst = (
                f"{len(payloads)} agent(s)"
            )

        # ===========================================
        # CHAIN OF COMMAND — Callback Pipeline
        # ===========================================
        else:
            try:
                with st.spinner(
                    "\u26d3\ufe0f Chain Processing..."
                ):
                    chain_result = run_chain_pipeline(
                        prompt, brain,
                        callback=update_ui_log,
                    )
            except Exception as e:
                swarm_error = str(e)
                chain_result = {}

            # 1.4: Chain result validatie
            if not isinstance(chain_result, dict):
                chain_result = {}

            nodes = chain_result.get(
                "nodes_betrokken", []
            ) or []
            sub_taken = chain_result.get(
                "sub_taken", []
            ) or []
            success_count = chain_result.get(
                "success_count", 0
            )
            total_sub = len(sub_taken)

            assigned = " \u2192 ".join(
                str(n) for n in nodes
            )
            output = str(
                chain_result.get(
                    "antwoord", "Geen antwoord"
                )
            )
            status_tekst = (
                f"{success_count}/{total_sub} "
                f"sub-taken geslaagd"
            )
            media = None

    # Sla pipeline log op in session_state
    st.session_state.swarm_logs.append({
        "prompt": prompt,
        "log": "\n".join(logs),
        "stappen": [],
        "tijd": datetime.now().strftime("%H:%M:%S"),
        "assigned": assigned,
    })

    # 1.3: Toon foutmelding bij swarm/chain error
    if swarm_error:
        with feed_col:
            st.error(
                f"Fout tijdens executie: {swarm_error}"
            )

    # Toon resultaat in feed
    if modus == "Hub & Spoke (route_task)":
        # Per-payload rendering (v5.0)
        header = (
            f"**[{assigned}]** | "
            f"Status: `{status_tekst}`"
        )
        # Bouw content voor history
        history_text = header
        for p in payloads:
            history_text += (
                f"\n\n**[{p.agent}]**\n"
                f"{p.display_text}"
            )

        st.session_state.messages.append({
            "role": "assistant",
            "content": history_text,
            "avatar": "\U0001f916",
            "payloads": payloads,
        })

        with feed_col:
            with st.chat_message(
                "assistant", avatar="\U0001f916"
            ):
                st.markdown(header)
                for p in payloads:
                    render_payload(st, p)
    else:
        # Chain of Command rendering
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
