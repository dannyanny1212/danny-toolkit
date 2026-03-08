from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, Container
from textual.widgets import Header, Footer, RichLog, Static, Label, Input
from textual import work
from rich.text import Text
import asyncio
import re
import time as _time
import sys
import os
import psutil
from pathlib import Path

try:
    import pynvml
    pynvml.nvmlInit()
    _GPU_HANDLE = pynvml.nvmlDeviceGetHandleByIndex(0)
    _HAS_GPU = True
except Exception:
    _HAS_GPU = False

# Zorg dat danny-toolkit root op sys.path staat voor imports
_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


# --- V4.0 CYBER-MINIMALIST CSS ---
OMEGA_CSS = """
Screen {
    background: #0B0F19; /* Diep donkerblauw/zwart */
}

Header {
    background: #00E5FF; /* Cyan */
    color: #0B0F19;
    text-style: bold;
}

Footer {
    background: #0B0F19;
    color: #00E5FF;
}

.pillar-container {
    height: 100%;
    border: round #00E5FF;
    margin: 0 1;
    background: #111827;
}

.pillar-side {
    width: 1fr;
}

.pillar-center {
    width: 2fr;
}

.pillar-container:focus-within {
    border: double #FFAB00; /* Goud/Oranje focus */
}

.pillar-title {
    content-align: center middle;
    width: 100%;
    background: #00E5FF 15%;
    color: #00E5FF;
    text-style: bold;
    padding: 1;
}

RichLog {
    padding: 1 2; /* Ademruimte voor de tekst! */
    height: 1fr;
    scrollbar-color: #00E5FF;
    scrollbar-color-hover: #FFAB00;
}

#status-bar {
    dock: bottom;
    height: 1;
    background: #000000;
    color: #00FF00;
    content-align: center middle;
}

Input {
    dock: bottom;
    width: 100%;
    margin: 1 1;
    border: tall #00E5FF;
    background: #0B0F19;
    color: #00FF00;
    text-style: bold;
}

Input:focus {
    border: double #FFAB00;
}

#mind_live_buffer {
    padding: 1 2;
    color: #00FF00;
    background: #0B0F19;
    text-style: bold;
    height: auto;
    max-height: 12;
    overflow-y: auto;
}

.trinity-row {
    height: 3fr;
}

.rag-row {
    height: 2fr;
}

.rag-container {
    height: 100%;
    border: round #FF6EC7;
    margin: 0 1;
    background: #111827;
}

.rag-title {
    content-align: center middle;
    width: 100%;
    background: #FF6EC7 15%;
    color: #FF6EC7;
    text-style: bold;
    padding: 1;
}

#log_rag {
    padding: 1 2;
    height: 1fr;
    scrollbar-color: #FF6EC7;
    scrollbar-color-hover: #FFAB00;
}

.rag-status {
    dock: top;
    height: 1;
    background: #0B0F19;
    color: #FF6EC7;
    padding: 0 2;
}
"""

class OmegaDashboardV4(App):
    """OMEGA SOVEREIGN CORE v4.0 - Trinity Interface"""

    CSS = OMEGA_CSS
    BINDINGS = [
        ("ctrl+q", "quit", "Afsluiten"),
        ("ctrl+l", "clear_logs", "Clear Logs"),
        ("ctrl+t", "toggle_dark", "Thema"),
        ("ctrl+s", "toggle_select", "Select"),
    ]

    _select_mode = False

    def compose(self) -> ComposeResult:
        """Bouw de Trinity + RAG Layout op."""
        yield Header(show_clock=True)

        # De Drie Pilaren (Soul, Mind, Body)
        with Horizontal(classes="trinity-row"):
            # LEFT: SOUL (Memory, RAG, Cortex) — smal
            with Vertical(classes="pillar-container pillar-side"):
                yield Label("Ω SOUL", classes="pillar-title")
                self.log_soul = RichLog(id="log_soul", highlight=True, markup=True)
                yield self.log_soul

            # CENTER: MIND (Reasoning, LLM, Decisions) — breed
            with Vertical(classes="pillar-container pillar-center"):
                yield Label("Ω SOVEREIGN MIND — Groq & NIM Reasoning", classes="pillar-title")
                self.log_mind = RichLog(id="log_mind", highlight=True, markup=True)
                yield self.log_mind
                # Live Buffer — typewriter streaming
                self.mind_live_buffer = Static("", id="mind_live_buffer")
                yield self.mind_live_buffer

            # RIGHT: BODY (Terminal, SwarmEngine, Hardware) — smal
            with Vertical(classes="pillar-container pillar-side"):
                yield Label("Ω SOVEREIGN BODY — Swarm & Executie", classes="pillar-title")
                self.log_body = RichLog(id="log_body", highlight=True, markup=True)
                yield self.log_body

        # BOTTOM: RAG SEARCH — 4de Kader (full width)
        with Horizontal(classes="rag-row"):
            with Vertical(classes="rag-container"):
                yield Label("🔍 RAG SEARCH + GHOSTWRITER — Vector Store Zoeken & LLM Synthese", classes="rag-title")
                self.rag_status = Static(
                    "[dim]Store: Brain Memory | Docs: ... | Top-K: 5 | Min: 0.00[/]",
                    classes="rag-status",
                )
                yield self.rag_status
                self.log_rag = RichLog(id="log_rag", highlight=True, markup=True)
                yield self.log_rag

        # De Sovereign Command Line
        yield Input(placeholder="Ω COMMAND >> 'help' | rag <query> | rag:store | rag:topk N | rag:min 0.5", id="cmd_input")

        # Vaste Statusbalk onderaan
        self.status_bar = Static("🟢 ONLINE | 18 Agents | CPU: 3.6% | RAM: 42% | GPU: 2% | VRAM: 3724MB", id="status-bar")
        yield self.status_bar
        yield Footer()

    # --- RAG Store definities ---
    _RAG_STORES = {
        "brain": Path(_ROOT) / "data" / "brain_memory" / "unified_vectors.json",
        "rag": Path(_ROOT) / "data" / "rag" / "vector_db.json",
        "knowledge": Path(_ROOT) / "data" / "knowledge_companion_vectors.json",
        "legendary": Path(_ROOT) / "data" / "legendary_companion_vectors.json",
    }
    _RAG_STORE_LABELS = {
        "brain": "Brain Memory (unified_vectors)",
        "rag": "RAG Documenten (vector_db)",
        "knowledge": "Knowledge Companion",
        "legendary": "Legendary Companion",
    }

    def on_mount(self) -> None:
        """Start de background tasks zodra de UI is geladen."""
        self.title = "O M E G A   S O V E R E I G N   v 4 . 0"

        self.log_mind.write("[bold yellow]WAV-Loop[/] Wachten op input van Commandant...")

        # Auto-focus op Input zodat toetsen altijd naar het invoerveld gaan
        self.query_one("#cmd_input", Input).focus()

        # Boot SwarmEngine (lazy — zware imports pas bij eerste gebruik)
        self._engine = None
        self._engine_ready = False
        self._brain = None

        # RAG Search state
        self._rag_store_key = "brain"
        self._rag_top_k = 5
        self._rag_min_score = 0.0
        self._rag_embedder = None
        self._rag_store = None
        self._rag_groq_client = None  # Eigen Groq key via AgentKeyManager
        self._rag_ghost = True        # GhostWriter synthese aan/uit

        # Boot Brain + Soul sequentieel (voorkomt import lock deadlock)
        self._boot_brain_and_soul()

        # Start BODY telemetrie op achtergrond (geen brain imports)
        self._boot_body_telemetry()

        # Boot RAG Search panel
        self._boot_rag_panel()

        # 1-seconde real-time hardware monitor
        self.set_interval(1.0, self.update_status_bar)

    @work(thread=True)
    def _boot_brain_and_soul(self) -> None:
        """Boot Brain + Soul sequentieel in één thread.

        Voorkomt Python import lock deadlock: twee threads die tegelijk
        modules uit danny_toolkit.brain importeren deadlocken op
        _ModuleLock. Door alles in één thread te doen is er geen contention.
        """
        # --- FASE 1: CentralBrain (streaming) ---
        try:
            from danny_toolkit.brain.central_brain import CentralBrain
            self._brain = CentralBrain()
            self.app.call_from_thread(
                self.log_mind.write,
                "[bold green]CentralBrain ONLINE[/] — Live streaming gereed.",
            )
        except Exception as e:
            self.app.call_from_thread(
                self.log_mind.write,
                f"[bold red]CentralBrain boot failed:[/] {e}",
            )

        # --- FASE 2: SOUL (CorticalStack + NeuralBus) ---
        # 1. CorticalStack status
        try:
            from danny_toolkit.brain.cortical_stack import get_cortical_stack
            cs = get_cortical_stack()
            recent = cs.get_recent_events(count=5)
            self.app.call_from_thread(
                self.log_soul.write,
                f"[bold cyan]CorticalStack[/] ONLINE. {len(recent)} recente herinneringen.",
            )
            for evt in recent[:3]:
                if not isinstance(evt, dict):
                    continue
                ts = evt.get("timestamp", "")[:19]
                actor = evt.get("actor", "SYSTEEM")
                action = evt.get("action", "event").upper()
                self.app.call_from_thread(
                    self.log_soul.write,
                    f"[dim]  {ts}[/] [cyan][{actor}][/] {action}",
                )
        except Exception as e:
            self.app.call_from_thread(
                self.log_soul.write,
                f"[yellow]CorticalStack: {e}[/]",
            )

        # 2. NeuralBus — subscribe op SOUL-relevante events
        try:
            from danny_toolkit.core.neural_bus import get_bus
            bus = get_bus()

            _SOUL_EVENTS = [
                "knowledge_graph_update", "system_event",
                "hallucination_blocked", "immune_response",
                "synapse_updated", "phantom_prediction", "phantom_hit",
                "pruning_started", "pruning_complete",
                "fragment_archived", "fragment_destroyed",
            ]

            def _soul_handler(event):
                etype = getattr(event, "event_type", "?")
                data = getattr(event, "data", {})
                bron = getattr(event, "bron", "")
                if isinstance(data, dict):
                    bron = bron or data.get("bron", "")
                    detail = data.get("detail", data.get("reason", data.get("query", "")))
                else:
                    detail = str(data)[:100] if data else ""
                msg = f"[cyan][{etype}][/]"
                if bron:
                    msg += f" [dim]({bron})[/]"
                if detail:
                    msg += f" {str(detail)[:120]}"
                self.app.call_from_thread(self.log_soul.write, msg)

            for evt_type in _SOUL_EVENTS:
                bus.subscribe(evt_type, _soul_handler)

            self.app.call_from_thread(
                self.log_soul.write,
                f"[green]NeuralBus[/] Luistert op {len(_SOUL_EVENTS)} event types.",
            )
        except Exception as e:
            self.app.call_from_thread(
                self.log_soul.write,
                f"[yellow]NeuralBus: {e}[/]",
            )

    @work(thread=True)
    def _boot_body_telemetry(self) -> None:
        """Boot BODY kolom — hardware telemetrie + ECHTE security checks."""
        # ── Governor startup_check (ECHT, niet nep) ──
        self.app.call_from_thread(
            self.log_body.write,
            Text.from_ansi("\033[96m[GOVERNOR] Startup check gestart...\033[0m"),
        )
        try:
            from danny_toolkit.brain.governor import OmegaGovernor
            gov = OmegaGovernor()
            gov_rapport = gov.startup_check()
            gov_status = gov_rapport.get("status", "?")
            color = "\033[32m" if gov_status == "OK" else "\033[33m"
            self.app.call_from_thread(
                self.log_body.write,
                Text.from_ansi(f"{color}[GOVERNOR] Startup check voltooid: {gov_status}\033[0m"),
            )
        except Exception as e:
            self.app.call_from_thread(
                self.log_body.write,
                Text.from_ansi(f"\033[31m[GOVERNOR] Startup FAILED: {e}\033[0m"),
            )

        # ── FileGuard integrity check ──
        try:
            from danny_toolkit.brain.file_guard import FileGuard
            fg = FileGuard()
            fg_rapport = fg.startup_check()
            fg_status = fg_rapport.get("status", "?") if isinstance(fg_rapport, dict) else ("OK" if fg_rapport else "WARN")
            color = "\033[32m" if fg_status == "OK" else "\033[33m"
            self.app.call_from_thread(
                self.log_body.write,
                Text.from_ansi(f"{color}[FILEGUARD] Integriteit: {fg_status}\033[0m"),
            )
        except Exception as e:
            self.app.call_from_thread(
                self.log_body.write,
                Text.from_ansi(f"\033[33m[FILEGUARD] Skip: {e}\033[0m"),
            )

        # ── ConfigAuditor ──
        try:
            from danny_toolkit.brain.config_auditor import get_config_auditor
            auditor = get_config_auditor()
            audit = auditor.audit()
            a_status = "VEILIG" if audit.veilig else f"{len(audit.schendingen)} schendingen"
            color = "\033[32m" if audit.veilig else "\033[33m"
            self.app.call_from_thread(
                self.log_body.write,
                Text.from_ansi(f"{color}[CONFIG AUDIT] {a_status}\033[0m"),
            )
        except Exception as e:
            self.app.call_from_thread(
                self.log_body.write,
                Text.from_ansi(f"\033[33m[CONFIG AUDIT] Skip: {e}\033[0m"),
            )

        # ── Hardware metrics ──
        try:
            import psutil
            cpu = psutil.cpu_percent(interval=1)
            ram = psutil.virtual_memory()
            self.app.call_from_thread(
                self.log_body.write,
                Text.from_ansi(
                    f"\033[32m[HARDWARE] CPU: {cpu}% | "
                    f"RAM: {ram.percent}% ({ram.used // (1024**3)}/{ram.total // (1024**3)} GB)\033[0m"
                ),
            )
        except ImportError:
            pass

        # GPU/VRAM
        try:
            from danny_toolkit.core.vram_manager import vram_rapport
            vram = vram_rapport()
            if vram.get("beschikbaar"):
                gpu = vram.get("gpu_naam", "?")
                used = vram.get("in_gebruik_mb", 0)
                total = vram.get("totaal_mb", 0)
                free = vram.get("vrij_mb", 0)
                self.app.call_from_thread(
                    self.log_body.write,
                    Text.from_ansi(
                        f"\033[32m[GPU] {gpu} | {used}/{total} MB (vrij: {free} MB)\033[0m"
                    ),
                )
        except Exception:
            pass

        # Hardware refresh nu via set_interval(1s) in on_mount()

    def update_status_bar(self) -> None:
        """1-seconde real-time hardware telemetrie."""
        try:
            cpu = psutil.cpu_percent(interval=None)
            ram = psutil.virtual_memory()

            # Color-coded warnings
            cpu_str = f"[red]{cpu}%[/]" if cpu > 85 else f"{cpu}%"
            ram_str = f"[red]{ram.percent}%[/]" if ram.percent > 90 else f"{ram.percent}%"

            status = f"🟢 ONLINE | CPU: {cpu_str} | RAM: {ram_str} ({ram.used // (1024**3)}/{ram.total // (1024**3)} GB)"

            if _HAS_GPU:
                try:
                    util = pynvml.nvmlDeviceGetUtilizationRates(_GPU_HANDLE)
                    mem = pynvml.nvmlDeviceGetMemoryInfo(_GPU_HANDLE)
                    gpu_pct = util.gpu
                    vram_used = mem.used // (1024**2)
                    vram_total = mem.total // (1024**2)
                    vram_free = (mem.total - mem.used) // (1024**2)
                    status += f" | GPU: {gpu_pct}% | VRAM: {vram_used}/{vram_total} MB (vrij: {vram_free})"
                except Exception:
                    status += " | GPU: N/A"

            self.status_bar.update(status)
        except Exception:
            pass

    def _get_engine(self):
        """Lazy-init SwarmEngine + CentralBrain."""
        if self._engine is not None:
            return self._engine
        try:
            from danny_toolkit.brain.central_brain import CentralBrain
            from swarm_engine import SwarmEngine
            brain = CentralBrain()
            self._engine = SwarmEngine(brain=brain)
            self._engine_ready = True
            self.app.call_from_thread(
                self.log_body.write,
                Text.from_ansi("\033[32m[ENGINE] SwarmEngine + CentralBrain ONLINE\033[0m"),
            )
        except Exception as e:
            self.app.call_from_thread(
                self.log_body.write,
                f"[bold red][ENGINE] Boot failed:[/] {e}",
            )
        return self._engine

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Wordt getriggerd wanneer de Commandant op Enter drukt."""
        commando = event.value.strip()
        if not commando:
            return

        # 1. Print commando in de MIND kolom
        self.log_mind.write(f"\n[bold #FFAB00]Commandant:[/] {commando}")

        # 2. Maak invoerveld leeg
        event.input.value = ""

        # 3. Route commando — RAG commands eerst
        if self._handle_rag_command(commando):
            return
        elif commando.lower() in ("clear", "cls"):
            self.action_clear_logs()
        elif commando.lower() == "help":
            self.log_mind.write(
                "[bold cyan]Commando's:[/]\n"
                "  [green]clear[/]       — Wis alle logs (of Ctrl+L)\n"
                "  [green]help[/]        — Toon deze hulp\n"
                "  [green]status[/]      — Engine status\n"
                "  [green]swarm:[/]      — Forceer SwarmEngine (optioneel)\n"
                "  [green]<tekst>[/]     — Auto-Router beslist: stream of swarm\n"
                "\n[bold #FF6EC7]RAG Search + GhostWriter:[/]\n"
                "  [#FF6EC7]rag <query>[/]      — Zoek + GhostWriter synthese\n"
                "  [#FF6EC7]rag:ghost[/]        — Toggle GhostWriter synthese (on/off)\n"
                "  [#FF6EC7]rag:store[/]        — Toon/wissel stores (brain|rag|knowledge|legendary)\n"
                "  [#FF6EC7]rag:topk <n>[/]     — Stel top-K in (1-50)\n"
                "  [#FF6EC7]rag:min <score>[/]  — Stel min score in (0.0-1.0)\n"
                "  [#FF6EC7]rag:stats[/]        — Toon store statistieken\n"
                "\n[bold cyan]Sneltoetsen:[/]\n"
                "  [green]Ctrl+S[/]    — Select Mode (tekst selecteren + copy)\n"
                "  [green]Ctrl+L[/]    — Wis alle logs\n"
                "  [green]Ctrl+Q[/]    — Afsluiten\n"
                "\n[bold cyan]Copy-Paste:[/]\n"
                "  [green]Shift+klik+sleep[/] — Tekst selecteren (altijd)\n"
                "  [green]Rechtermuisklik[/]  — Copy/Paste menu\n"
                "  [green]Ctrl+V[/]           — Plakken in invoerveld"
            )
        elif commando.lower() == "status":
            brain_status = "ONLINE" if self._brain else "BOOTING..."
            engine_status = "ONLINE" if self._engine_ready else "STANDBY"
            self.log_mind.write(
                f"[cyan]CentralBrain: {brain_status} | SwarmEngine: {engine_status}[/]"
            )
        elif commando.lower().startswith("swarm:"):
            # Handmatige override — forceer SwarmEngine
            self.verwerk_swarm(commando[6:].strip())
        else:
            # Auto-Router beslist: PRAAT → stream, ACTIE → swarm
            self.routeer_commando(commando)

    # Nederlandse actiewoorden voor snelle keyword pre-check
    _ACTIE_KEYWORDS = frozenset({
        "start", "stop", "scan", "download", "export", "exporteer",
        "importeer", "maak", "genereer", "bewaar", "opslaan", "sla op",
        "verwijder", "delete", "backup", "herstel", "restore",
        "installeer", "update", "upgrade", "activeer", "deactiveer",
        "automatiseer", "voer uit", "execute", "run", "draai",
        "stuur", "send", "push", "deploy", "build", "test",
        "create", "open", "sluit", "herstart", "restart", "reboot",
    })

    def _snelle_actie_check(self, prompt: str) -> bool:
        """Keyword pre-check — vangt duidelijke acties zonder LLM call."""
        woorden = prompt.lower().split()
        return bool(self._ACTIE_KEYWORDS & set(woorden))

    async def _bepaal_intentie(self, prompt: str) -> str:
        """Bepaalt PRAAT of ACTIE — keyword check eerst, LLM als tiebreaker."""
        # Snelle keyword pre-check (0ms, geen API call)
        if self._snelle_actie_check(prompt):
            return "ACTIE"

        if self._brain is None:
            return "PRAAT"
        try:
            chain = self._brain._build_stream_chain()
            if not chain:
                return "PRAAT"
            client, mdl, _label, kwargs_extra = chain[0]
            resp = await client.chat.completions.create(
                model=mdl,
                messages=[
                    {"role": "system", "content": (
                        "You are a strict binary intent router. "
                        "Does the user need a PHYSICAL ACTION (create file, download, scan, "
                        "export, execute tool, modify system, start app, save data, generate "
                        "report, automate, search web, run code, build, deploy, install)? "
                        "Answer with EXACTLY one word: ACTION or CHAT. "
                        "No explanation. No punctuation. Just one word.\n"
                        "NOTE: The user may write in Dutch. 'automatiseer'=ACTION, "
                        "'exporteer'=ACTION, 'start'=ACTION, 'maak'=ACTION, "
                        "'wat is'=CHAT, 'leg uit'=CHAT, 'vertel'=CHAT."
                    )},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=5,
                temperature=0.0,
            )
            intent = resp.choices[0].message.content.strip().upper()
            return "ACTIE" if ("ACTION" in intent or "ACTIE" in intent) else "PRAAT"
        except Exception:
            return "PRAAT"

    @work(exclusive=True)
    async def routeer_commando(self, commando: str) -> None:
        """Auto-Router: beslist autonoom of het naar MIND of BODY gaat."""
        self.mind_live_buffer.update("[dim]🔍 Poortwachter analyseert...[/]")
        intentie = await self._bepaal_intentie(commando)
        self.mind_live_buffer.update("")

        if intentie == "ACTIE":
            self.log_mind.write(
                "[dim]Routing:[/] [bold yellow]ACTIE[/] [dim]→ BODY pipeline[/]"
            )
            self.log_body.write(
                f"[bold yellow]⚡ AUTO-ROUTER:[/] Actie gedetecteerd voor: [cyan]{commando}[/]"
            )
            self.verwerk_swarm(commando)
        else:
            # Smart routing: check of query tools nodig heeft
            needs_tools = False
            if self._brain and getattr(self._brain, "_tool_dispatcher", None):
                try:
                    matched = self._brain._tool_dispatcher._keyword_match(commando.lower())
                    if matched - {"omega_core"}:
                        needs_tools = True
                        self.log_mind.write(
                            f"[dim]Routing:[/] [bold magenta]DATA[/] [dim]→ tools ({len(matched)} apps)[/]"
                        )
                        self.log_body.write(
                            f"[bold magenta]🔧 TOOL-ROUTER:[/] {', '.join(sorted(matched))}"
                        )
                except Exception:
                    pass

            if needs_tools:
                self.verwerk_met_tools(commando)
            else:
                self.log_mind.write(
                    "[dim]Routing:[/] [bold cyan]PRAAT[/] [dim]→ MIND stream[/]"
                )
                if self._brain is None:
                    self.log_mind.write("[yellow]CentralBrain nog niet gereed...[/]")
                    return
                try:
                    self.mind_live_buffer.update("[italic cyan]Ω MIND is aan het nadenken... ⠧[/]")
                    t0 = _time.time()
                    opgebouwde_tekst = ""

                    async for token in self._brain.genereer_stream(commando):
                        opgebouwde_tekst += token
                        display_tekst = opgebouwde_tekst.replace(
                            "<think>", "[dim italic]🧠 "
                        ).replace(
                            "</think>", "[/dim italic]\n"
                        )
                        self.mind_live_buffer.update(
                            f"[bold green]Ω OMEGA:[/] {display_tekst}"
                        )

                    elapsed = _time.time() - t0
                    self.mind_live_buffer.update("")
                    schone_tekst = re.sub(
                        r"<think>.*?</think>\s*", "", opgebouwde_tekst, flags=re.DOTALL
                    )
                    if not schone_tekst.strip():
                        schone_tekst = opgebouwde_tekst
                    self.log_mind.write(f"\n[bold green]Ω OMEGA:[/] {schone_tekst.strip()}")
                    self.log_mind.write(f"[dim]Gestreamd in {elapsed:.1f}s[/]")
                except Exception as e:
                    self.mind_live_buffer.update("")
                    self.log_mind.write(f"\n[bold red]STREAM ERROR:[/] {e}")

    @work(exclusive=True, thread=True)
    def verwerk_met_tools(self, commando: str) -> None:
        """Tool-aware verwerking — process_request met function calling."""
        self.app.call_from_thread(
            self.mind_live_buffer.update,
            "[italic magenta]Ω MIND denkt na met tools... ⠧[/]",
        )
        t0 = _time.time()
        try:
            if self._brain is None:
                self.app.call_from_thread(
                    self.log_mind.write,
                    "[yellow]CentralBrain nog niet gereed...[/]",
                )
                return
            result = self._brain.process_request(commando)
            elapsed = _time.time() - t0
            self.app.call_from_thread(self.mind_live_buffer.update, "")
            if result:
                self.app.call_from_thread(
                    self.log_mind.write,
                    f"\n[bold green]Ω OMEGA:[/] {result}",
                )
            else:
                self.app.call_from_thread(
                    self.log_mind.write,
                    "[yellow]Geen resultaat van tools.[/]",
                )
            self.app.call_from_thread(
                self.log_mind.write,
                f"[dim]Tool-verwerkt in {elapsed:.1f}s[/]",
            )
        except Exception as e:
            self.app.call_from_thread(self.mind_live_buffer.update, "")
            self.app.call_from_thread(
                self.log_mind.write,
                f"\n[bold red]TOOL ERROR:[/] {e}",
            )

    @work(exclusive=True, thread=True)
    def verwerk_swarm(self, commando: str) -> None:
        """Achtergrond worker — SwarmEngine multi-agent pipeline."""
        self.app.call_from_thread(
            self.log_mind.write,
            "[italic cyan]Ω SWARM pipeline actief...[/]",
        )

        t0 = _time.time()

        try:
            engine = self._get_engine()
            if engine is None:
                self.app.call_from_thread(
                    self.log_mind.write,
                    "[bold red]Engine niet beschikbaar — check BODY log[/]",
                )
                return

            if not hasattr(self, "_worker_loop") or self._worker_loop.is_closed():
                self._worker_loop = asyncio.new_event_loop()
            loop = self._worker_loop

            def _callback(msg):
                """Live pipeline updates naar BODY kolom."""
                self.app.call_from_thread(
                    self.log_body.write,
                    Text.from_ansi(str(msg)),
                )

            payloads = loop.run_until_complete(
                engine.run(commando, callback=_callback)
            )

            elapsed = _time.time() - t0

            if payloads:
                for payload in payloads:
                    agent = getattr(payload, "agent", "?")
                    tekst = getattr(payload, "display_text", "") or ""
                    if not tekst.strip():
                        raw = getattr(payload, "content", None)
                        if isinstance(raw, str):
                            tekst = raw
                        elif isinstance(raw, dict):
                            tekst = raw.get("text", raw.get("result", str(raw)))
                        elif raw is not None:
                            tekst = str(raw)
                        else:
                            tekst = str(payload)
                    if len(tekst) > 2000:
                        tekst = tekst[:2000] + "..."
                    self.app.call_from_thread(
                        self.log_mind.write,
                        f"\n[bold green]Ω {agent}:[/] {tekst}",
                    )
            else:
                self.app.call_from_thread(
                    self.log_mind.write,
                    "[yellow]Geen resultaat van SwarmEngine.[/]",
                )

            self.app.call_from_thread(
                self.log_mind.write,
                f"[dim]Swarm verwerkt in {elapsed:.1f}s[/]",
            )

        except Exception as e:
            self.app.call_from_thread(
                self.log_mind.write,
                f"\n[bold red]SWARM ERROR:[/] {e}",
            )

    # =========================================================================
    # RAG SEARCH TERMINAL — 4de Kader
    # =========================================================================

    @work(thread=True)
    def _boot_rag_panel(self) -> None:
        """Boot RAG panel — laad embedder + Groq client + standaard store."""
        self.app.call_from_thread(
            self.log_rag.write,
            "[bold #FF6EC7]RAG SEARCH TERMINAL[/] booting...",
        )

        # --- Embedder ---
        try:
            from danny_toolkit.core.embeddings import get_embedder
            self._rag_embedder = get_embedder(gebruik_voyage=True, gebruik_cache=True)
            self.app.call_from_thread(
                self.log_rag.write,
                "[green]Embedder ONLINE[/] (Voyage 256d MRL)",
            )
        except Exception as e:
            self.app.call_from_thread(
                self.log_rag.write,
                f"[bold red]Embedder FAILED:[/] {e}",
            )
            return

        # --- Groq Client via AgentKeyManager (eigen key: GROQ_API_KEY_RAG) ---
        try:
            from danny_toolkit.core.key_manager import get_key_manager
            km = get_key_manager()
            self._rag_groq_client = km.create_sync_client("RAGSearch")
            if self._rag_groq_client:
                self.app.call_from_thread(
                    self.log_rag.write,
                    "[green]GhostWriter LLM ONLINE[/] (RAGSearch key, prio 2)",
                )
            else:
                raise RuntimeError("Geen key beschikbaar")
        except Exception as e:
            # Fallback: directe Groq client
            try:
                from groq import Groq
                key = os.getenv("GROQ_API_KEY", "")
                if key:
                    self._rag_groq_client = Groq(api_key=key)
                    self.app.call_from_thread(
                        self.log_rag.write,
                        "[yellow]GhostWriter LLM ONLINE[/] (fallback key)",
                    )
                else:
                    self.app.call_from_thread(
                        self.log_rag.write,
                        f"[yellow]GhostWriter LLM OFFLINE[/] — geen Groq key ({e})",
                    )
            except ImportError:
                self.app.call_from_thread(
                    self.log_rag.write,
                    "[yellow]GhostWriter LLM OFFLINE[/] — groq package niet gevonden",
                )

        # --- Store laden ---
        self._rag_load_store()

        # Toon beschikbare stores
        beschikbaar = []
        for key, path in self._RAG_STORES.items():
            exists = "✓" if path.exists() else "✗"
            beschikbaar.append(f"  [{key}] {self._RAG_STORE_LABELS[key]} {exists}")
        ghost_status = "[green]AAN[/]" if self._rag_ghost else "[red]UIT[/]"
        self.app.call_from_thread(
            self.log_rag.write,
            "[cyan]Beschikbare stores:[/]\n" + "\n".join(beschikbaar),
        )
        self.app.call_from_thread(
            self.log_rag.write,
            f"\n[dim]GhostWriter synthese: {ghost_status}[/]"
            "\n[dim]Commands: rag <query> | rag:ghost | rag:store | rag:topk N | rag:min 0.5 | rag:stats[/]",
        )

    def _rag_load_store(self) -> None:
        """Laad de geselecteerde vector store."""
        db_path = self._RAG_STORES[self._rag_store_key]
        if not db_path.exists():
            self.app.call_from_thread(
                self.log_rag.write,
                f"[yellow]Store '{self._rag_store_key}' niet gevonden: {db_path.name}[/]",
            )
            self._rag_store = None
            self._rag_update_status()
            return

        try:
            from danny_toolkit.core.vector_store import VectorStore
            self._rag_store = VectorStore(
                embedding_provider=self._rag_embedder, db_file=db_path,
            )
            stats = self._rag_store.statistieken()
            self.app.call_from_thread(
                self.log_rag.write,
                f"[green]Store geladen:[/] [bold]{self._RAG_STORE_LABELS[self._rag_store_key]}[/] "
                f"— {stats['totaal_documenten']} docs, "
                f"{stats.get('embedding_dimensies', '?')}d embeddings",
            )
        except Exception as e:
            self.app.call_from_thread(
                self.log_rag.write,
                f"[bold red]Store load failed:[/] {e}",
            )
            self._rag_store = None

        self._rag_update_status()

    def _rag_update_status(self) -> None:
        """Update de RAG statusbalk."""
        label = self._RAG_STORE_LABELS.get(self._rag_store_key, "?")
        doc_count = self._rag_store.count() if self._rag_store else 0
        ghost = "ON" if self._rag_ghost else "OFF"
        llm = "LIVE" if self._rag_groq_client else "OFF"
        status = (
            f"[bold #FF6EC7]Store:[/] {label} | "
            f"[bold]Docs:[/] {doc_count} | "
            f"[bold]Top-K:[/] {self._rag_top_k} | "
            f"[bold]Min:[/] {self._rag_min_score:.2f} | "
            f"[bold]Ghost:[/] {ghost} | "
            f"[bold]LLM:[/] {llm}"
        )
        self.app.call_from_thread(self.rag_status.update, status)

    @work(thread=True)
    def _rag_zoek(self, query: str) -> None:
        """Voer RAG vector search uit — GhostWriter typewriter cast."""
        if not self._rag_store:
            self.app.call_from_thread(
                self.log_rag.write,
                "[bold red]Geen store geladen.[/] Gebruik: rag:store brain|rag|knowledge|legendary",
            )
            return

        self.app.call_from_thread(
            self.log_rag.write,
            f"\n[bold #FFAB00]🔍 Zoekquery:[/] {query}",
        )

        t0 = _time.time()
        try:
            resultaten = self._rag_store.zoek(
                query, top_k=self._rag_top_k, min_score=self._rag_min_score,
            )
        except Exception as e:
            self.app.call_from_thread(
                self.log_rag.write,
                f"[bold red]Search ERROR:[/] {e}",
            )
            return

        elapsed = _time.time() - t0

        if not resultaten:
            self.app.call_from_thread(
                self.log_rag.write,
                f"[yellow]Geen resultaten[/] (top_k={self._rag_top_k}, min={self._rag_min_score:.2f}) [{elapsed:.2f}s]",
            )
            return

        self.app.call_from_thread(
            self.log_rag.write,
            f"[bold green]{len(resultaten)} resultaten[/] in {elapsed:.2f}s",
        )

        # GhostWriter Cast — resultaten één voor één met typewriter delay
        for i, res in enumerate(resultaten, 1):
            score = res["score"]
            score_pct = score * 100

            # Tri-Color score indicator
            if score >= 0.8:
                kleur = "green"
                indicator = "●"
            elif score >= 0.5:
                kleur = "yellow"
                indicator = "●"
            else:
                kleur = "red"
                indicator = "●"

            doc_id = res["id"]
            if len(doc_id) > 50:
                doc_id = doc_id[:47] + "..."

            # Header lijn
            self.app.call_from_thread(
                self.log_rag.write,
                f"[{kleur}]{indicator}[/] [bold]#{i}[/] [{kleur}]{score_pct:.1f}%[/] — [cyan]{doc_id}[/]",
            )

            # Tekst preview (max 300 chars voor compactheid in terminal)
            tekst = res["tekst"].replace("\n", " ").strip()
            if len(tekst) > 300:
                tekst = tekst[:297] + "..."
            self.app.call_from_thread(
                self.log_rag.write,
                f"  [dim]{tekst}[/]",
            )

            # Metadata op één lijn
            meta = res.get("metadata", {})
            if meta:
                meta_parts = [f"{k}={v}" for k, v in meta.items() if k != "embedding"]
                if meta_parts:
                    meta_str = " | ".join(meta_parts[:5])
                    if len(meta_str) > 120:
                        meta_str = meta_str[:117] + "..."
                    self.app.call_from_thread(
                        self.log_rag.write,
                        f"  [dim italic]meta: {meta_str}[/]",
                    )

            # GhostWriter typewriter delay tussen resultaten
            _time.sleep(0.05)

        # --- GhostWriter Synthese — LLM cast van RAG resultaten ---
        if self._rag_ghost and self._rag_groq_client and resultaten:
            self._rag_ghost_cast(query, resultaten)

        self._rag_update_status()

    def _rag_ghost_cast(self, query: str, resultaten: list) -> None:
        """GhostWriter Cast — LLM synthese van RAG zoekresultaten.

        Bouwt een context-prompt van de gevonden documenten, stuurt het
        naar Groq via de eigen RAGSearch key, en cast het antwoord
        token-voor-token (typewriter effect) in het RAG panel.
        """
        self.app.call_from_thread(
            self.log_rag.write,
            "\n[bold #FF6EC7]═══ GHOSTWRITER SYNTHESE ═══[/]",
        )

        # Bouw context van de top resultaten
        context_parts = []
        for i, res in enumerate(resultaten[:10], 1):
            tekst = res["tekst"].strip()
            if len(tekst) > 600:
                tekst = tekst[:597] + "..."
            score_pct = res["score"] * 100
            context_parts.append(f"[Doc {i} | {score_pct:.0f}% match]\n{tekst}")

        context = "\n\n".join(context_parts)

        try:
            from danny_toolkit.core.config import Config
            model = Config.LLM_MODEL
        except ImportError:
            model = "meta-llama/llama-4-scout-17b-16e-instruct"

        try:
            # Track via KeyManager
            try:
                from danny_toolkit.core.key_manager import get_key_manager
                km = get_key_manager()
                km.registreer_request("RAGSearch")
            except Exception:
                pass

            t0 = _time.time()
            response = self._rag_groq_client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Je bent de Omega GhostWriter — een RAG synthese-agent. "
                            "Je krijgt zoekresultaten uit een vector store en een gebruikersquery. "
                            "Geef een beknopt, helder antwoord gebaseerd op de documenten. "
                            "Gebruik Nederlands. Verwijs naar documenten met [Doc N]. "
                            "Als de documenten het antwoord niet bevatten, zeg dat eerlijk."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"QUERY: {query}\n\n"
                            f"GEVONDEN DOCUMENTEN:\n{context}\n\n"
                            "Geef een synthese-antwoord op basis van bovenstaande documenten."
                        ),
                    },
                ],
                temperature=0.3,
                max_tokens=1024,
                stream=True,
            )

            # Typewriter cast — token voor token
            full_text = ""
            for chunk in response:
                delta = chunk.choices[0].delta
                token = getattr(delta, "content", None) or ""
                if token:
                    full_text += token
                    # Verwijder <think> tags voor display
                    display = re.sub(
                        r"<think>.*?</think>\s*", "", full_text, flags=re.DOTALL,
                    )
                    if not display.strip():
                        display = full_text
                    self.app.call_from_thread(
                        self.log_rag.write,
                        f"\r[bold green]Ω GhostWriter:[/] {display.strip()[-200:]}",
                    )
                    _time.sleep(0.01)  # Typewriter snelheid

            elapsed = _time.time() - t0

            # Final clean output
            clean_text = re.sub(
                r"<think>.*?</think>\s*", "", full_text, flags=re.DOTALL,
            ).strip()
            if not clean_text:
                clean_text = full_text.strip()

            # Clear incremental lines en schrijf final result
            self.app.call_from_thread(
                self.log_rag.write,
                f"\n[bold green]Ω GHOSTWRITER ANTWOORD:[/]\n{clean_text}",
            )
            self.app.call_from_thread(
                self.log_rag.write,
                f"[dim]Synthese in {elapsed:.1f}s | model: {model}[/]",
            )

            # Track tokens
            try:
                km.registreer_tokens("RAGSearch", full_text)
            except Exception:
                pass

        except Exception as e:
            self.app.call_from_thread(
                self.log_rag.write,
                f"[bold red]GhostWriter ERROR:[/] {e}",
            )

    def _handle_rag_command(self, commando: str) -> bool:
        """Route RAG commands. Returns True als het een RAG command was."""
        cmd_lower = commando.lower().strip()

        # rag:store <name> — wissel van store
        if cmd_lower.startswith("rag:store"):
            parts = commando.split(maxsplit=1)
            if len(parts) < 2 or parts[1].strip().replace("rag:store", "").strip() == "":
                # Toon beschikbare stores
                self.log_rag.write("[cyan]Beschikbare stores:[/]")
                for key, label in self._RAG_STORE_LABELS.items():
                    path = self._RAG_STORES[key]
                    active = " [bold green]◄ ACTIEF[/]" if key == self._rag_store_key else ""
                    exists = "[green]✓[/]" if path.exists() else "[red]✗[/]"
                    self.log_rag.write(f"  {exists} [bold]{key}[/] — {label}{active}")
                return True

            store_key = parts[1].strip().split()[-1].lower()
            if store_key not in self._RAG_STORES:
                self.log_rag.write(
                    f"[red]Onbekende store: '{store_key}'[/] — kies uit: {', '.join(self._RAG_STORES.keys())}"
                )
                return True
            self._rag_store_key = store_key
            self.log_rag.write(f"[#FF6EC7]Switching to:[/] {self._RAG_STORE_LABELS[store_key]}")
            self._boot_rag_store_switch()
            return True

        # rag:topk <n>
        if cmd_lower.startswith("rag:topk"):
            parts = commando.split()
            if len(parts) >= 2:
                try:
                    val = int(parts[-1])
                    self._rag_top_k = max(1, min(val, 50))
                    self.log_rag.write(f"[green]Top-K ingesteld op {self._rag_top_k}[/]")
                    self._rag_update_status()
                except ValueError:
                    self.log_rag.write("[red]Gebruik: rag:topk <getal>[/]")
            return True

        # rag:min <score>
        if cmd_lower.startswith("rag:min"):
            parts = commando.split()
            if len(parts) >= 2:
                try:
                    val = float(parts[-1])
                    self._rag_min_score = max(0.0, min(val, 1.0))
                    self.log_rag.write(f"[green]Min score ingesteld op {self._rag_min_score:.2f}[/]")
                    self._rag_update_status()
                except ValueError:
                    self.log_rag.write("[red]Gebruik: rag:min <0.0-1.0>[/]")
            return True

        # rag:ghost — toggle GhostWriter synthese
        if cmd_lower.startswith("rag:ghost"):
            parts = commando.lower().split()
            if len(parts) >= 2 and parts[-1] in ("on", "aan"):
                self._rag_ghost = True
            elif len(parts) >= 2 and parts[-1] in ("off", "uit"):
                self._rag_ghost = False
            else:
                self._rag_ghost = not self._rag_ghost
            status = "[green]AAN[/]" if self._rag_ghost else "[red]UIT[/]"
            llm = "LIVE" if self._rag_groq_client else "OFFLINE"
            self.log_rag.write(f"[#FF6EC7]GhostWriter synthese:[/] {status} (LLM: {llm})")
            self._rag_update_status()
            return True

        # rag:stats — toon store statistieken
        if cmd_lower == "rag:stats":
            if self._rag_store:
                stats = self._rag_store.statistieken()
                self.log_rag.write("[bold cyan]═══ STORE STATISTIEKEN ═══[/]")
                self.log_rag.write(f"  Documenten:    {stats['totaal_documenten']}")
                self.log_rag.write(f"  Embedding dim: {stats.get('embedding_dimensies', 'N/A')}")
                self.log_rag.write(f"  Queries:       {stats['queries_uitgevoerd']}")
                self.log_rag.write(f"  Gem. tekstlen: {stats.get('gem_tekst_lengte', 'N/A')} chars")
                grootte = stats.get("db_grootte_bytes", 0)
                if grootte > 1024 * 1024:
                    self.log_rag.write(f"  DB grootte:    {grootte / 1024 / 1024:.1f} MB")
                elif grootte > 0:
                    self.log_rag.write(f"  DB grootte:    {grootte / 1024:.1f} KB")
                meta_velden = stats.get("metadata_velden", [])
                if meta_velden:
                    self.log_rag.write(f"  Meta-velden:   {', '.join(meta_velden[:10])}")
            else:
                self.log_rag.write("[yellow]Geen store geladen.[/]")
            return True

        # rag <query> — zoek
        if cmd_lower.startswith("rag "):
            query = commando[4:].strip()
            if query:
                self._rag_zoek(query)
            else:
                self.log_rag.write("[yellow]Gebruik: rag <zoekopdracht>[/]")
            return True

        return False

    @work(thread=True)
    def _boot_rag_store_switch(self) -> None:
        """Herlaad store na switch (in worker thread)."""
        self._rag_load_store()

    def action_toggle_select(self) -> None:
        """Toggle Select Mode — schakelt muisvangst uit zodat je tekst kunt selecteren."""
        self._select_mode = not self._select_mode
        f = getattr(getattr(self, "console", None), "file", None) or sys.stdout
        if self._select_mode:
            # Schakel Textual mouse tracking UIT — terminal krijgt muis terug
            f.write("\033[?1000l\033[?1003l\033[?1015l\033[?1006l")
            f.flush()
            self.status_bar.update(
                "SELECT MODE — Selecteer tekst + rechtermuisklik → Copy | Ctrl+S = terug"
            )
        else:
            # Heractiveer Textual mouse tracking
            f.write("\033[?1000h\033[?1003h\033[?1015h\033[?1006h")
            f.flush()
            self.status_bar.update("🟢 ONLINE | Select Mode UIT")

    def action_clear_logs(self) -> None:
        """Maakt alle schermen schoon met de 'C' toets."""
        self.log_soul.clear()
        self.log_mind.clear()
        self.log_body.clear()
        self.log_rag.clear()

if __name__ == "__main__":
    app = OmegaDashboardV4()
    app.run()
