"""
Tijd Info v2.0 - Tijdweergave en tijdzone-informatie.

Toont epoch-tijd, lokale tijd, UTC, en tijdsverschillen.
"""

import logging
import time
from datetime import datetime, timezone
from ..core.utils import clear_scherm
from .base_app import BaseApp

logger = logging.getLogger(__name__)


class TijdInfoApp(BaseApp):
    """Tijdweergave app met epoch, lokaal, UTC en opgeslagen momenten."""

    def __init__(self):
        super().__init__("tijd_info.json")

    def _get_default_data(self) -> dict:
        return {"opgeslagen_momenten": []}

    def run(self):
        """Start de tijd info app."""
        while True:
            clear_scherm()
            print("+" + "=" * 55 + "+")
            print("|              TIJD INFO v2.0                          |")
            print("+" + "=" * 55 + "+")
            self._toon_huidige_tijd()
            print("+" + "-" * 55 + "+")
            print("|  1. Ververs tijd                                     |")
            print("|  2. Moment opslaan                                   |")
            print("|  3. Opgeslagen momenten bekijken                     |")
            print("|  4. Tijd sinds moment berekenen                      |")
            print("|  5. Epoch naar datum converteren                     |")
            print("|  6. Momenten wissen                                  |")
            print("+" + "-" * 55 + "+")
            print("|  0. Terug                                            |")
            print("+" + "-" * 55 + "+")

            keuze = input("\n  Keuze: ").strip()
            if keuze == "0":
                break
            elif keuze == "1":
                continue
            elif keuze == "2":
                self._sla_moment_op()
            elif keuze == "3":
                self._toon_momenten()
            elif keuze == "4":
                self._tijd_sinds_moment()
            elif keuze == "5":
                self._epoch_naar_datum()
            elif keuze == "6":
                self._wis_momenten()
            else:
                print("  Ongeldige keuze.")
                input("\n  [Enter] om door te gaan...")

    def _toon_huidige_tijd(self):
        """Toon uitgebreide tijdinformatie."""
        nu = time.time()
        lokaal = datetime.now()
        utc = datetime.now(timezone.utc)

        print(f"|  Epoch (seconden):  {nu:<34.6f} |")
        print(f"|  Lokale tijd:       {lokaal.strftime('%Y-%m-%d %H:%M:%S'):<34} |")
        print(f"|  UTC tijd:          {utc.strftime('%Y-%m-%d %H:%M:%S'):<34} |")
        print(f"|  Leesbaar:          {time.ctime(nu):<34} |")
        print(f"|  Tijdzone:          {time.tzname[0]:<34} |")
        print(f"|  UTC offset:        {lokaal.astimezone().strftime('%z'):<34} |")

    def _sla_moment_op(self):
        """Sla het huidige moment op met een label."""
        label = input("\n  Label voor dit moment: ").strip()
        if not label:
            print("  Geen label opgegeven.")
            input("\n  [Enter] om door te gaan...")
            return

        moment = {
            "label": label,
            "epoch": time.time(),
            "lokaal": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        self.data["opgeslagen_momenten"].append(moment)
        self._sla_op()
        print(f"  Moment '{label}' opgeslagen op {moment['lokaal']}")
        input("\n  [Enter] om door te gaan...")

    def _toon_momenten(self):
        """Toon alle opgeslagen momenten."""
        momenten = self.data["opgeslagen_momenten"]
        if not momenten:
            print("\n  Geen opgeslagen momenten.")
            input("\n  [Enter] om door te gaan...")
            return

        print(f"\n  {'#':<4} {'Label':<25} {'Tijdstip':<22} {'Epoch'}")
        print("  " + "-" * 70)
        for i, m in enumerate(momenten, 1):
            print(f"  {i:<4} {m['label']:<25} {m['lokaal']:<22} {m['epoch']:.2f}")
        input("\n  [Enter] om door te gaan...")

    def _tijd_sinds_moment(self):
        """Bereken verstreken tijd sinds een opgeslagen moment."""
        momenten = self.data["opgeslagen_momenten"]
        if not momenten:
            print("\n  Geen opgeslagen momenten.")
            input("\n  [Enter] om door te gaan...")
            return

        for i, m in enumerate(momenten, 1):
            print(f"  {i}. {m['label']} ({m['lokaal']})")

        try:
            keuze = int(input("\n  Welk moment? ")) - 1
            if 0 <= keuze < len(momenten):
                verschil = time.time() - momenten[keuze]["epoch"]
                print(f"\n  Tijd sinds '{momenten[keuze]['label']}':")
                print(f"  {self._formatteer_duur(verschil)}")
            else:
                print("  Ongeldige keuze.")
        except ValueError:
            print("  Voer een nummer in.")
        input("\n  [Enter] om door te gaan...")

    def _epoch_naar_datum(self):
        """Converteer een epoch timestamp naar leesbare datum."""
        try:
            epoch = float(input("\n  Epoch timestamp: "))
            lokaal = datetime.fromtimestamp(epoch)
            utc = datetime.fromtimestamp(epoch, tz=timezone.utc)
            print(f"\n  Lokaal:   {lokaal.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"  UTC:      {utc.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"  Leesbaar: {time.ctime(epoch)}")
        except (ValueError, OSError):
            print("  Ongeldige timestamp.")
        input("\n  [Enter] om door te gaan...")

    def _wis_momenten(self):
        """Wis alle opgeslagen momenten."""
        if not self.data["opgeslagen_momenten"]:
            print("\n  Geen momenten om te wissen.")
            input("\n  [Enter] om door te gaan...")
            return

        bevestig = input("\n  Alle momenten wissen? (j/n): ").strip().lower()
        if bevestig == "j":
            self.data["opgeslagen_momenten"] = []
            self._sla_op()
            print("  Alle momenten gewist.")
        else:
            print("  Geannuleerd.")
        input("\n  [Enter] om door te gaan...")

    @staticmethod
    def _formatteer_duur(seconden: float) -> str:
        """Formatteer seconden naar leesbare duur."""
        s = int(seconden)
        dagen, rest = divmod(s, 86400)
        uren, rest = divmod(rest, 3600)
        minuten, sec = divmod(rest, 60)
        delen = []
        if dagen:
            delen.append(f"{dagen}d")
        if uren:
            delen.append(f"{uren}u")
        if minuten:
            delen.append(f"{minuten}m")
        delen.append(f"{sec}s")
        return " ".join(delen)
