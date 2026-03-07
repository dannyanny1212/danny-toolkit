from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, Container
from textual.widgets import Header, Footer, RichLog, Static, Label, Input
from textual import work
from rich.text import Text
import asyncio
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
    width: 1fr;
    height: 100%;
    border: round #00E5FF;
    margin: 0 1;
    background: #111827;
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
        ("q", "quit", "Afsluiten"),
        ("c", "clear_logs", "Clear Logs"),
        ("t", "toggle_dark", "Thema Wisselen"),
        ("f2", "toggle_select", "Select Mode"),
    ]

    _select_mode = False

    def compose(self) -> ComposeResult:
        """Bouw de Trinity Layout op."""
        yield Header(show_clock=True)

        # De Drie Pilaren (Soul, Mind, Body)
        with Horizontal():
            # LEFT: SOUL (Memory, RAG, Cortex)
            with Vertical(classes="pillar-container"):
                yield Label("Ω SOVEREIGN SOUL — Geheugen & RAG", classes="pillar-title")
                self.log_soul = RichLog(id="log_soul", highlight=True, markup=True)
                yield self.log_soul

            # CENTER: MIND (Reasoning, LLM, Decisions)
            with Vertical(classes="pillar-container"):
                yield Label("Ω SOVEREIGN MIND — Groq & NIM Reasoning", classes="pillar-title")
                self.log_mind = RichLog(id="log_mind", highlight=True, markup=True)
                yield self.log_mind
                # Live Buffer — typewriter streaming
                self.mind_live_buffer = Static("", id="mind_live_buffer")
                yield self.mind_live_buffer

            # RIGHT: BODY (Terminal, SwarmEngine, Hardware)
            with Vertical(classes="pillar-container"):
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
        """Boot BODY kolom — hardware telemetrie + Governor check."""
        # Governor startup
        self.app.call_from_thread(
            self.log_body.write,
            Text.from_ansi("\033[96m[GOVERNOR] Startup check gestart...\033[0m"),
        )

        # Hardware metrics
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

        self.app.call_from_thread(
            self.log_body.write,
            Text.from_ansi("\033[32m[GOVERNOR] Startup check voltooid: OK\033[0m"),
        )

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
                "[bold cyan]Beschikbare commando's:[/]\n"
                "  [green]clear[/]   — Wis alle logs\n"
                "  [green]help[/]    — Toon deze hulp\n"
                "  [green]status[/]  — Engine status\n"
                "  [green]swarm:[/]  — Multi-agent pipeline (SwarmEngine)\n"
                "  [green]<tekst>[/] — Live streaming via CentralBrain"
            )
        elif commando.lower() == "status":
            brain_status = "ONLINE" if self._brain else "BOOTING..."
            engine_status = "ONLINE" if self._engine_ready else "STANDBY"
            self.log_mind.write(
                f"[cyan]CentralBrain: {brain_status} | SwarmEngine: {engine_status}[/]"
            )
        elif commando.lower().startswith("swarm:"):
            # Multi-agent pipeline via SwarmEngine
            self.verwerk_swarm(commando[6:].strip())
        else:
            # Live streaming via CentralBrain (typewriter effect)
            self.stream_commando(commando)

    @work(exclusive=True)
    async def stream_commando(self, commando: str) -> None:
        """Streamt tokens live naar het scherm — typewriter effect."""
        if self._brain is None:
            self.log_mind.write("[yellow]CentralBrain nog niet gereed, even geduld...[/]")
            return

        try:
            self.mind_live_buffer.update("[italic cyan]Ω MIND is aan het nadenken... ⠧[/]")
            t0 = _time.time()

            opgebouwde_tekst = ""

            # --- START DE NEURALE STROOM ---
            async for token in self._brain.genereer_stream(commando):
                opgebouwde_tekst += token

                # --- COGNITIVE FILTER ---
                # <think> blokken dimmen, echte output helder houden
                display_tekst = opgebouwde_tekst.replace(
                    "<think>", "[dim italic]🧠 "
                ).replace(
                    "</think>", "[/dim italic]\n"
                )

                self.mind_live_buffer.update(
                    f"[bold green]Ω OMEGA:[/] {display_tekst}"
                )

            # --- STREAM COMPLEET ---
            elapsed = _time.time() - t0
            self.mind_live_buffer.update("")

            # Strip <think> blokken uit permanente log (alleen het antwoord)
            import re
            schone_tekst = re.sub(r"<think>.*?</think>\s*", "", opgebouwde_tekst, flags=re.DOTALL)
            if not schone_tekst.strip():
                schone_tekst = opgebouwde_tekst  # Fallback: toon alles als er geen clean output is
            self.log_mind.write(f"\n[bold green]Ω OMEGA:[/] {schone_tekst.strip()}")
            self.log_mind.write(f"[dim]Gestreamd in {elapsed:.1f}s[/]")

        except Exception as e:
            self.mind_live_buffer.update("")
            self.log_mind.write(f"\n[bold red]STREAM ERROR:[/] {e}")

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
        if self._select_mode:
            # Schakel Textual mouse tracking UIT — terminal krijgt muis terug
            if hasattr(self, "console") and hasattr(self.console, "file"):
                f = self.console.file
            else:
                f = sys.stdout
            # Disable mouse tracking escape sequences
            f.write("\033[?1000l\033[?1003l\033[?1015l\033[?1006l")
            f.flush()
            self.status_bar.update("SELECT MODE — Selecteer tekst + rechtermuisklik → Copy | F2 = terug")
        else:
            # Heractiveer Textual mouse tracking
            if hasattr(self, "console") and hasattr(self.console, "file"):
                f = self.console.file
            else:
                f = sys.stdout
            f.write("\033[?1000h\033[?1003h\033[?1015h\033[?1006h")
            f.flush()
            self.status_bar.update("🟢 ONLINE | 18 Agents | Select Mode UIT")

    def action_clear_logs(self) -> None:
        """Maakt alle schermen schoon met de 'C' toets."""
        self.log_soul.clear()
        self.log_mind.clear()
        self.log_body.clear()

if __name__ == "__main__":
    app = OmegaDashboardV4()
    app.run()
