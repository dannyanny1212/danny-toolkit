"""
QUEST IX: THE PULSE PROTOCOL
=============================
"Connecting the Heart to the Chain"

Een prototype waarbij gesimuleerde biologische hartslag
direct bepaalt of een crypto-transactie wordt goedgekeurd.

Spelers:
- [VITA]     (Tier 3): Simuleert hartslag-data (BPM & HRV)
- [IOLAAX]   (Tier 1): Analyseert stress level
- [CIPHER]   (Tier 3): Ondertekent transactie met Bio-Salt
- [GOVERNOR] (Tier 2): Blokkeert als Bio-Auth faalt
"""

import time
import random
import hashlib
import sys

# Probeer rich te importeren, val terug op simpele print
try:
    from rich.console import Console
    from rich.live import Live
    from rich.table import Table
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    print(
        "TIP: Installeer 'rich' voor betere visuals "
        "(pip install rich)"
    )


class PulseProtocol:
    """Bio-Digital Bridge: Hart -> Stress -> Crypto."""

    def __init__(self):
        self.wallet_balance = 10.5

    def vita_heartbeat(self):
        """[VITA] Genereert hartslag data."""
        base_bpm = 60
        fluctuation = random.randint(-5, 45)
        bpm = base_bpm + fluctuation

        # Hoge BPM = Lage HRV (Stress)
        if bpm < 85:
            hrv = random.randint(20, 100)
        else:
            hrv = random.randint(5, 30)

        return {"bpm": bpm, "hrv": hrv}

    def iolaax_analyze(self, bio_data):
        """[IOLAAX] Berekent Stress Score."""
        stress_score = (
            (bio_data["bpm"] / 2) - (bio_data["hrv"] / 4)
        )
        # Drempelwaarde: Alles onder 35 is "Kalm"
        is_calm = stress_score < 35
        return is_calm, stress_score

    def cipher_sign(self, bio_data):
        """[CIPHER] Tekent de transactie."""
        salt = str(bio_data["bpm"])
        tx_hash = hashlib.sha256(
            f"ETH_TX_{salt}".encode()
        ).hexdigest()[:12]
        return tx_hash

    def run_simulation(self):
        """Draai de Pulse Protocol simulatie."""
        if not RICH_AVAILABLE:
            print("--- START SIMULATIE (Tekst Mode) ---")
            for i in range(5):
                row = self._step(i)
                print(
                    f"  {row[0]} | {row[1]} | "
                    f"Stress: {row[2]} | {row[3]} | "
                    f"{row[4]}"
                )
                time.sleep(1)
            return

        # Rich GUI Mode
        console = Console(force_terminal=True)
        table = Table(
            title="[bold green]QUEST IX: "
            "PULSE PROTOCOL[/bold green]"
        )
        table.add_column("Tijd")
        table.add_column("VITA (Hart)")
        table.add_column("IOLAAX (Stress)")
        table.add_column("GOVERNOR")
        table.add_column("CIPHER (Hash)")

        with Live(
            table, refresh_per_second=4, console=console
        ) as live:
            for i in range(12):
                time.sleep(1)
                row = self._step(i)

                status_color = (
                    "green" if "AUTHORIZED" in row[3]
                    else "red"
                )

                table.add_row(
                    row[0],
                    row[1],
                    row[2],
                    f"[{status_color}]{row[3]}"
                    f"[/{status_color}]",
                    row[4],
                )

    def _step(self, i):
        """Voert een logische stap uit."""
        bio = self.vita_heartbeat()
        calm, score = self.iolaax_analyze(bio)

        if calm:
            status = "AUTHORIZED"
            tx_hash = self.cipher_sign(bio)
            icon = "<3"
        else:
            status = "BLOCKED"
            tx_hash = "LOCKED"
            icon = "!!"

        return (
            f"00:{i:02d}",
            f"{icon} {bio['bpm']} BPM",
            f"{score:.1f}",
            status,
            tx_hash,
        )


if __name__ == "__main__":
    try:
        protocol = PulseProtocol()
        protocol.run_simulation()
    except Exception as e:
        print(f"\nKRITIEKE FOUT: {e}")
        print(">> Controleer je code op typo's!")
