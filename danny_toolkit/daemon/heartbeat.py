"""
Heartbeat Daemon - Autonome Achtergrond-Daemon.

CPU/RAM monitoring, reflectie-cycli en autonome groei.
Draait naast de bestaande DigitalDaemon (app 39).

Gebruik:
    python -m danny_toolkit.daemon.heartbeat

Of via launcher: app 52 / sneltoets 'hb'.

Geen nieuwe dependencies: psutil is optioneel (zelfde
patroon als morning_protocol.py), Rich is al geinstalleerd.
"""

import random
import threading
import time
from datetime import datetime, timedelta

from rich.align import Align
from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

# psutil optioneel (zelfde patroon als morning_protocol.py)
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False


class HeartbeatDaemon:
    """Autonome heartbeat daemon met Rich Live display.

    Monitort systeem, reflecteert op recente events en
    groeit autonoom met een kleine kans per cyclus.
    """

    HEARTBEAT_INTERVAL = 1.0    # seconden
    REFLECTION_INTERVAL = 10.0  # seconden
    GROWTH_CHANCE = 0.05        # 5% per reflectie

    VERSION = "1.0.0"

    def __init__(self):
        self._stack = None
        self._running = False
        self._stop_event = threading.Event()

        # Counters
        self._pulse_count = 0
        self._reflection_count = 0
        self._growth_count = 0
        self._start_time = None

        # System metrics
        self._cpu = 0.0
        self._ram = 0.0

        # Activity log (laatste 8 entries)
        self._activity = []

        # Timing
        self._last_reflection = 0.0
        self._last_stat_log = 0.0

    def _get_stack(self):
        """Lazy import CorticalStack."""
        if self._stack is None:
            try:
                from ..brain.cortical_stack import (
                    get_cortical_stack,
                )
                self._stack = get_cortical_stack()
            except Exception:
                self._stack = None
        return self._stack

    # ─── Monitor ───

    def _monitor_system(self):
        """Lees CPU en RAM gebruik."""
        if HAS_PSUTIL:
            self._cpu = psutil.cpu_percent(interval=0)
            self._ram = psutil.virtual_memory().percent
        else:
            # Simuleer waarden als fallback
            self._cpu = random.uniform(5.0, 45.0)
            self._ram = random.uniform(30.0, 70.0)

    def _log_heartbeat(self):
        """Log stats naar CorticalStack elke 5 beats."""
        if self._pulse_count % 5 != 0:
            return

        stack = self._get_stack()
        if stack is None:
            return

        try:
            stack.log_stat(
                "cpu_percent", self._cpu,
                tags={"source": "heartbeat"},
            )
            stack.log_stat(
                "ram_percent", self._ram,
                tags={"source": "heartbeat"},
            )
        except Exception:
            pass

    # ─── Reflectie ───

    def _reflection_cycle(self):
        """Review recente events uit CorticalStack."""
        now = time.time()
        if now - self._last_reflection < self.REFLECTION_INTERVAL:
            return

        self._last_reflection = now
        self._reflection_count += 1

        stack = self._get_stack()
        if stack is None:
            self._log_activity(
                "reflectie", "Geen stack beschikbaar"
            )
            return

        try:
            events = stack.get_recent_events(5)
            event_count = len(events)

            if event_count > 0:
                laatste = events[0]
                actor = laatste.get("actor", "?")
                action = laatste.get("action", "?")
                self._log_activity(
                    "reflectie",
                    f"{event_count} events, "
                    f"laatste: {actor}/{action}",
                )
            else:
                self._log_activity(
                    "reflectie", "Geen recente events"
                )

            # Log reflectie event
            stack.log_event(
                actor="heartbeat",
                action="reflection",
                details={
                    "events_reviewed": event_count,
                    "pulse": self._pulse_count,
                },
                source="daemon",
            )
        except Exception:
            self._log_activity(
                "reflectie", "Fout bij lezen events"
            )

    # ─── Groei ───

    def _autonomous_growth(self):
        """5% kans: re-index of leer nieuwe feiten."""
        if random.random() > self.GROWTH_CHANCE:
            return

        self._growth_count += 1
        stack = self._get_stack()
        if stack is None:
            self._log_activity("groei", "Geen stack")
            return

        try:
            # Haal stats op en sla inzicht op
            db_stats = stack.get_stats()
            totaal = db_stats.get("total", 0)

            inzicht = (
                f"Systeem bevat {totaal} records "
                f"na {self._pulse_count} pulsen"
            )

            stack.remember_fact(
                f"groei_inzicht_{self._growth_count}",
                inzicht,
                confidence=0.3,
            )

            stack.log_event(
                actor="heartbeat",
                action="growth",
                details={
                    "growth_nr": self._growth_count,
                    "db_total": totaal,
                },
                source="daemon",
            )

            self._log_activity("groei", inzicht)

        except Exception:
            self._log_activity("groei", "Fout bij groei")

    # ─── Display ───

    def _log_activity(self, type_: str, bericht: str):
        """Voeg toe aan activity log (max 8)."""
        now = datetime.now().strftime("%H:%M:%S")
        self._activity.append(
            f"[dim]{now}[/dim] "
            f"[bold cyan]{type_}[/bold cyan] {bericht}"
        )
        if len(self._activity) > 8:
            self._activity = self._activity[-8:]

    def _build_display(self) -> Layout:
        """Bouw Rich Layout voor Live display."""
        layout = Layout()

        # Uptime berekenen
        if self._start_time:
            delta = datetime.now() - self._start_time
            uren, rest = divmod(int(delta.total_seconds()), 3600)
            minuten, seconden = divmod(rest, 60)
            uptime = f"{uren:02d}:{minuten:02d}:{seconden:02d}"
        else:
            uptime = "00:00:00"

        # Header
        header_text = (
            f"[bold magenta]HEARTBEAT DAEMON[/bold magenta]"
            f" v{self.VERSION}"
            f"  |  Uptime: [cyan]{uptime}[/cyan]"
            f"  |  Pulsen: [green]{self._pulse_count}[/green]"
        )

        # Systeem panel
        psutil_status = (
            "[green]ACTIEF[/green]"
            if HAS_PSUTIL
            else "[yellow]SIMULATIE[/yellow]"
        )

        sys_table = Table(
            show_header=False, expand=True,
            border_style="cyan", padding=(0, 1),
        )
        sys_table.add_column("label", width=14)
        sys_table.add_column("waarde")

        cpu_kleur = (
            "green" if self._cpu < 50
            else "yellow" if self._cpu < 80
            else "red"
        )
        ram_kleur = (
            "green" if self._ram < 60
            else "yellow" if self._ram < 85
            else "red"
        )

        sys_table.add_row(
            "CPU",
            f"[{cpu_kleur}]{self._cpu:.1f}%[/{cpu_kleur}]",
        )
        sys_table.add_row(
            "RAM",
            f"[{ram_kleur}]{self._ram:.1f}%[/{ram_kleur}]",
        )
        sys_table.add_row(
            "Heartbeats",
            f"[green]{self._pulse_count}[/green]",
        )
        sys_table.add_row(
            "Reflecties",
            f"[cyan]{self._reflection_count}[/cyan]",
        )
        sys_table.add_row(
            "Groei events",
            f"[magenta]{self._growth_count}[/magenta]",
        )

        sys_panel = Panel(
            sys_table,
            title="[bold cyan]SYSTEEM[/bold cyan]",
            border_style="cyan",
        )

        # Activiteit panel
        if self._activity:
            activity_text = "\n".join(self._activity)
        else:
            activity_text = "[dim]Wachten op activiteit...[/dim]"

        act_panel = Panel(
            activity_text,
            title="[bold yellow]ACTIVITEIT[/bold yellow]",
            border_style="yellow",
        )

        # Footer
        footer_text = (
            f"  psutil: {psutil_status}"
            f"  |  [dim]Ctrl+C om te stoppen[/dim]"
        )

        # Layout samenstellen
        layout.split_column(
            Layout(
                Panel(
                    Align.center(
                        Text.from_markup(header_text)
                    ),
                    border_style="magenta",
                    padding=(0, 1),
                ),
                name="header",
                size=3,
            ),
            Layout(name="body"),
            Layout(
                Panel(
                    Text.from_markup(footer_text),
                    border_style="dim",
                    padding=(0, 0),
                ),
                name="footer",
                size=3,
            ),
        )

        layout["body"].split_row(
            Layout(sys_panel, name="systeem", ratio=1),
            Layout(act_panel, name="activiteit", ratio=2),
        )

        return layout

    # ─── Main Loop ───

    def start(self):
        """Start de heartbeat daemon met Rich Live."""
        self._running = True
        self._start_time = datetime.now()
        self._stop_event.clear()

        console = Console()

        # Log start event
        stack = self._get_stack()
        if stack:
            try:
                stack.log_event(
                    actor="heartbeat",
                    action="daemon_start",
                    details={"version": self.VERSION},
                    source="daemon",
                )
            except Exception:
                pass

        self._log_activity("start", "Heartbeat Daemon gestart")

        try:
            with Live(
                self._build_display(),
                console=console,
                refresh_per_second=2,
                screen=True,
            ) as live:
                while not self._stop_event.is_set():
                    # Pulse
                    self._pulse_count += 1
                    self._monitor_system()
                    self._log_heartbeat()

                    # Reflectie check
                    self._reflection_cycle()

                    # Groei check (alleen tijdens reflectie)
                    if self._reflection_count > 0:
                        self._autonomous_growth()

                    # Update display
                    live.update(self._build_display())

                    # Wacht
                    self._stop_event.wait(
                        self.HEARTBEAT_INTERVAL
                    )

        except KeyboardInterrupt:
            pass
        finally:
            self._running = False
            self._log_activity(
                "stop", "Heartbeat Daemon gestopt"
            )

            # Log stop event
            if stack:
                try:
                    stack.log_event(
                        actor="heartbeat",
                        action="daemon_stop",
                        details={
                            "pulses": self._pulse_count,
                            "reflections":
                                self._reflection_count,
                            "growths": self._growth_count,
                        },
                        source="daemon",
                    )
                except Exception:
                    pass

            console.print(
                "\n[bold magenta]Heartbeat Daemon gestopt."
                "[/bold magenta]"
            )

    def stop(self):
        """Stop de daemon."""
        self._stop_event.set()
        self._running = False


def main():
    """Entry point voor heartbeat daemon."""
    daemon = HeartbeatDaemon()
    daemon.start()


if __name__ == "__main__":
    main()
