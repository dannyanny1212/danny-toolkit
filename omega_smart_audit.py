import os
import sys
import time
from pathlib import Path

# Windows encoding fix
if os.name == "nt":
    os.system("")  # Enable ANSI on Windows
    sys.stdout.reconfigure(encoding="utf-8")

# Probeer rich te laden
try:
    from rich.console import Console
    from rich.table import Table
    from rich.progress import track
    from rich.panel import Panel
    console = Console(force_terminal=True)
    RICH_AVAILABLE = True
except ImportError:
    print("TIP: Installeer 'rich' (pip install rich)")
    RICH_AVAILABLE = False

# --- DE SLIMME ZOEKER ---
def find_file_in_project(filename):
    """Zoekt recursief door je hele projectmap naar een bestand."""
    start_dir = "."
    for root, dirs, files in os.walk(start_dir):
        if filename in files:
            return os.path.join(root, filename)
    return None

# --- DE 9 PILAREN (Op Bestandsnaam, niet Pad) ---
PILLARS = [
    {
        "id": "I",
        "name": "THE GENESIS",
        "target": "main_omega.py",
        "fallback": "main.py",
        "desc": "Modulariteit & Main Loop"
    },
    {
        "id": "II",
        "name": "THE SOUL (Pets)",
        "target": "limbic_system.py",
        "desc": "Emotionele UI & ASCII"
    },
    {
        "id": "III",
        "name": "THE MEMORY",
        "target": "tracker.py",
        "fallback": "rag_system.py",
        "desc": "RAG & Vector Database"
    },
    {
        "id": "IV",
        "name": "THE SWARM",
        "target": "roles.py",
        "desc": "344 Agents & Schaalbaarheid"
    },
    {
        "id": "V",
        "name": "THE SHIELD",
        "target": "config.py",
        "desc": "Beveiliging & Config"
    },
    {
        "id": "VI",
        "name": "THE NEXUS",
        "target": "virtueel_huisdier.json",
        "desc": "Dashboard & Verbindingen"
    },
    {
        "id": "VII",
        "name": "EVOLUTION",
        "target": "self_improvement.py",
        "desc": "Anti-Fragiliteit"
    },
    {
        "id": "VIII",
        "name": "THE DREAM",
        "target": "morning_protocol.py",
        "desc": "Nachtelijke Optimalisatie"
    },
    {
        "id": "IX",
        "name": "THE PULSE",
        "target": "pulse_protocol.py",
        "desc": "Bio-Hash Security"
    },
    {
        "id": "X",
        "name": "THE VOICE",
        "target": "voice_protocol.py",
        "desc": "Pixel Spreekt - Emotionele Stem"
    },
    {
        "id": "XI",
        "name": "THE LISTENER",
        "target": "listener_protocol.py",
        "desc": "Pixel Hoort - Spraakherkenning"
    },
    {
        "id": "XII",
        "name": "THE DIALOGUE",
        "target": "dialogue_protocol.py",
        "desc": "Pixel Converseert - Spraakdialoog"
    },
]

def run_smart_audit():
    if RICH_AVAILABLE:
        console.clear()
        console.print(Panel.fit(
            "[bold cyan]Ω OMEGA SMART AUDIT v2.0"
            "[/bold cyan]\n"
            "[dim]Scanning file structure...[/dim]"
        ))

    results = []
    unity_score = 0
    total_pillars = len(PILLARS)

    # Gebruik rich track of simpele loop
    if RICH_AVAILABLE:
        iterator = track(
            PILLARS,
            description="Searching Artifacts...",
        )
    else:
        iterator = PILLARS

    for pillar in iterator:
        time.sleep(0.1)

        # 1. Zoek bestand
        found_path = find_file_in_project(pillar["target"])

        # 2. Probeer fallback als het niet gevonden is
        if not found_path and "fallback" in pillar:
            found_path = find_file_in_project(
                pillar["fallback"]
            )

        if found_path:
            unity_score += 1
            if RICH_AVAILABLE:
                status = "[bold green]FOUND[/bold green]"
                location = f"[dim]{found_path}[/dim]"
            else:
                status = "FOUND"
                location = found_path
            icon = "v"
        else:
            if RICH_AVAILABLE:
                status = "[bold red]MISSING[/bold red]"
                location = "[red]Not found[/red]"
            else:
                status = "MISSING"
                location = "Not found"
            icon = "x"

        results.append([
            pillar["id"],
            pillar["name"],
            location,
            status,
            icon,
        ])

    # Tabel tonen
    if RICH_AVAILABLE:
        table = Table(title="THE COSMIC BLUEPRINT STATUS")
        table.add_column(
            "Quest", style="cyan", justify="center",
        )
        table.add_column("Pillar Name", style="white")
        table.add_column("Location Found", style="blue")
        table.add_column("Status", justify="center")
        table.add_column("", justify="center")

        for row in results:
            table.add_row(*row)
        console.print(table)

        # Score
        score_pct = (unity_score / total_pillars) * 100
        console.print(
            f"\n[bold]UNITY SCORE:[/bold]"
            f" [magenta]{score_pct:.1f}%[/magenta]"
        )
    else:
        # Fallback tekst output
        print("\n--- AUDIT RESULTS ---")
        for row in results:
            print(
                f"{row[0]} | {row[1]}"
                f" | {row[3]} | {row[2]}"
            )
        score_pct = (unity_score / total_pillars) * 100
        print(f"\nUNITY SCORE: {score_pct:.1f}%")


if __name__ == "__main__":
    run_smart_audit()
