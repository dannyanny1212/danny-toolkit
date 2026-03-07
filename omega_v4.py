from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, Container
from textual.widgets import Header, Footer, RichLog, Static, Label, Input
from textual import work
from rich.text import Text
import asyncio
import time as _time
import sys
import os

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

        # Testberichtjes om de ANSI parsing te demonstreren
        self.log_soul.write("[bold cyan]CorticalStack[/] ONLINE. Kennisgraaf geladen (321 nodes).")
        self.log_mind.write("[bold yellow]WAV-Loop[/] Wachten op input van Commandant...")

        # HIER IS DE ANSI FIX VOOR JE RECHTERKANT (BODY)
        ruwe_terminal_output = "\033[96m[GOVERNOR] Startup check gestart...\033[0m\n\033[32m[GOVERNOR] Startup check voltooid: OK\033[0m"

        # Door Text.from_ansi() te gebruiken, verdwijnen de [0m codes en worden het échte kleuren!
        self.log_body.write(Text.from_ansi(ruwe_terminal_output))

        # Boot SwarmEngine (lazy — zware imports pas bij eerste gebruik)
        self._engine = None
        self._engine_ready = False

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
                "  [green]clear[/]  — Wis alle logs\n"
                "  [green]help[/]   — Toon deze hulp\n"
                "  [green]status[/] — Engine status\n"
                "  [green]<tekst>[/] — Stuur naar SwarmEngine"
            )
        elif commando.lower() == "status":
            status = "ONLINE" if self._engine_ready else "STANDBY (boot bij eerste query)"
            self.log_mind.write(f"[cyan]SwarmEngine: {status}[/]")
        else:
            # Start de achtergrond-denker (UI bevriest NIET)
            self.verwerk_commando(commando)

    @work(exclusive=True, thread=True)
    def verwerk_commando(self, commando: str) -> None:
        """Achtergrond worker — SwarmEngine draait in thread, UI blijft vloeiend."""
        self.app.call_from_thread(
            self.log_mind.write,
            "[italic cyan]Ω MIND is aan het nadenken...[/]",
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

            # SwarmEngine.run() is async — draai in eigen event loop
            loop = asyncio.new_event_loop()
            try:
                def _callback(msg):
                    """Live pipeline updates naar BODY kolom."""
                    self.app.call_from_thread(
                        self.log_body.write,
                        Text.from_ansi(str(msg)),
                    )

                payloads = loop.run_until_complete(
                    engine.run(commando, callback=_callback)
                )
            finally:
                loop.close()

            elapsed = _time.time() - t0

            # Resultaten naar MIND kolom — payload uitpakken
            if payloads:
                for payload in payloads:
                    agent = getattr(payload, "agent", "?")
                    # Prioriteit: display_text > content > str(payload)
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
                    # Trim extreem lange output
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
                f"[dim]Verwerkt in {elapsed:.1f}s[/]",
            )

        except Exception as e:
            self.app.call_from_thread(
                self.log_mind.write,
                f"\n[bold red]FATAL ERROR:[/] {e}",
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
