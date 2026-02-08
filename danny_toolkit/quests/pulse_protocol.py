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
from rich.console import Console
from rich.live import Live
from rich.table import Table

console = Console(force_terminal=True)


class PulseProtocol:
    """Bio-Digital Bridge: Hart -> Stress -> Crypto."""

    def __init__(self):
        self.wallet_balance = 10.5  # ETH (Simulatie)
        self.is_stressed = False

    def vita_heartbeat(self):
        """[VITA NODE] Simuleert Danny's hartslag."""
        # Normaal ritme: 60-80 BPM. Stress: 100+ BPM.
        base_bpm = 70
        fluctuation = random.randint(-5, 40)
        bpm = base_bpm + fluctuation

        # HRV is laag bij stress, hoog bij rust.
        if bpm < 90:
            hrv = random.randint(20, 100)
        else:
            hrv = random.randint(5, 30)

        return {"bpm": bpm, "hrv": hrv}

    def iolaax_analyze(self, bio_data):
        """[IOLAAX NODE] Bepaalt of Danny kalm is."""
        stress_score = (
            (bio_data["bpm"] / 2) - (bio_data["hrv"] / 4)
        )
        is_calm = stress_score < 45
        return is_calm, stress_score

    def cipher_sign(self, bio_data):
        """[CIPHER NODE] Tekent transactie met Bio-Salt."""
        salt = str(bio_data["bpm"])
        transaction = f"SEND 1 ETH | SALT:{salt}"
        tx_hash = hashlib.sha256(
            transaction.encode()
        ).hexdigest()[:16]
        return tx_hash

    def run_simulation(self):
        """Draai de Pulse Protocol simulatie."""
        table = Table(
            title="[bold green]QUEST IX: "
            "THE PULSE PROTOCOL[/bold green]"
        )
        table.add_column("Tijd")
        table.add_column("VITA (Hart)")
        table.add_column("IOLAAX (Stress)")
        table.add_column("GOVERNOR (Status)")
        table.add_column("CIPHER (Hash)")

        with Live(table, refresh_per_second=1, console=console) as live:
            for i in range(10):
                time.sleep(1)

                # 1. VITA meet
                bio = self.vita_heartbeat()

                # 2. IOLAAX denkt
                calm, score = self.iolaax_analyze(bio)

                # 3. GOVERNOR beslist
                if calm:
                    status = "[green]AUTHORIZED[/green]"
                    # 4. CIPHER handelt
                    tx_hash = self.cipher_sign(bio)
                else:
                    status = "[red]BLOCKED (STRESS)[/red]"
                    tx_hash = "LOCKED"

                # Render Row
                viz_heart = (
                    "[green]<3[/green]" if calm
                    else "[red]!![/red]"
                )
                table.add_row(
                    f"00:0{i}",
                    f"{viz_heart} {bio['bpm']} BPM "
                    f"(HRV: {bio['hrv']})",
                    f"{score:.1f} / 100",
                    status,
                    tx_hash,
                )


if __name__ == "__main__":
    protocol = PulseProtocol()
    protocol.run_simulation()
