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
        """Bouw de Trinity Layout op."""
        yield Header(show_clock=True)

        # De Drie Pilaren (Soul, Mind, Body)
        with Horizontal():
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

        # De Sovereign Command Line
        yield Input(placeholder="Ω SOVEREIGN COMMAND >> Typ een opdracht voor de MIND of 'help'...", id="cmd_input")

        # Vaste Statusbalk onderaan
        self.status_bar = Static("🟢 ONLINE | 18 Agents | CPU: 3.6% | RAM: 42% | GPU: 2% | VRAM: 3724MB", id="status-bar")
        yield self.status_bar
        yield Footer()

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

        # Boot Brain + Soul sequentieel (voorkomt import lock deadlock)
        self._boot_brain_and_soul()

        # Start BODY telemetrie op achtergrond (geen brain imports)
        self._boot_body_telemetry()

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

        # 3. Route commando
        if commando.lower() in ("clear", "cls"):
            self.action_clear_logs()
        elif commando.lower() == "help":
            self.log_mind.write(
                "[bold cyan]Commando's:[/]\n"
                "  [green]clear[/]     — Wis alle logs (of Ctrl+L)\n"
                "  [green]help[/]      — Toon deze hulp\n"
                "  [green]status[/]    — Engine status\n"
                "  [green]swarm:[/]    — Forceer SwarmEngine (optioneel)\n"
                "  [green]<tekst>[/]   — Auto-Router beslist: stream of swarm\n"
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

    # Queries die ALTIJD naar MIND/CentralBrain moeten (tool executie via LLM)
    _MIND_OVERRIDE_PATTERNS = (
        "poort", "localhost", "sane bridge", "observatie",
        "local_bridge", "gap analysis",
    )

    async def _bepaal_intentie(self, prompt: str) -> str:
        """Bepaalt PRAAT of ACTIE — keyword check eerst, LLM als tiebreaker."""
        # PRIORITEIT 1: MIND override — deze queries hebben CentralBrain tools nodig
        prompt_lower = prompt.lower()
        if any(term in prompt_lower for term in self._MIND_OVERRIDE_PATTERNS):
            return "PRAAT"

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

if __name__ == "__main__":
    app = OmegaDashboardV4()
    app.run()
