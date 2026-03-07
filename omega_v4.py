from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, Container
from textual.widgets import Header, Footer, RichLog, Static, Label
from rich.text import Text
import asyncio

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
"""

class OmegaDashboardV4(App):
    """OMEGA SOVEREIGN CORE v4.0 - Trinity Interface"""

    CSS = OMEGA_CSS
    BINDINGS = [
        ("q", "quit", "Afsluiten"),
        ("c", "clear_logs", "Clear Logs"),
        ("t", "toggle_dark", "Thema Wisselen")
    ]

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

        # Start je asynchrone luisteraars hier
        # asyncio.create_task(self.luister_naar_jouw_omega_core())

    def action_clear_logs(self) -> None:
        """Maakt alle schermen schoon met de 'C' toets."""
        self.log_soul.clear()
        self.log_mind.clear()
        self.log_body.clear()

if __name__ == "__main__":
    app = OmegaDashboardV4()
    app.run()
