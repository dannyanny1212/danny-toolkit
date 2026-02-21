"""
Time Capsule v1.0 - Berichten naar je toekomstige zelf schrijven.
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional
from ..core.config import Config
from ..core.utils import clear_scherm

logger = logging.getLogger(__name__)


class TimeCapsuleApp:
    """Time Capsule - Schrijf berichten naar je toekomstige zelf."""

    VERSIE = "1.0"

    # Voorgestelde periodes
    PERIODES = [
        ("1 week", 7),
        ("1 maand", 30),
        ("3 maanden", 90),
        ("6 maanden", 180),
        ("1 jaar", 365),
        ("5 jaar", 1825),
    ]

    # Prompt vragen
    PROMPTS = [
        "Wat houdt je op dit moment het meest bezig?",
        "Wat zijn je grootste dromen en doelen?",
        "Waar ben je dankbaar voor?",
        "Wat wil je tegen je toekomstige zelf zeggen?",
        "Welke uitdagingen ervaar je nu?",
        "Wat maakt je gelukkig?",
        "Welk advies zou je jezelf geven?",
        "Wat hoop je te hebben bereikt als je dit leest?",
    ]

    def __init__(self):
        Config.ensure_dirs()
        self.data_dir = Config.APPS_DATA_DIR / "time_capsule"
        self.data_dir.mkdir(exist_ok=True)
        self.data_file = self.data_dir / "capsules.json"
        self.data = self._laad_data()

    def _laad_data(self) -> Dict:
        """Laad capsules data."""
        if self.data_file.exists():
            try:
                with open(self.data_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.debug("Time capsule data load error: %s", e)
        return {
            "capsules": [],
            "geopend": [],
        }

    def _sla_op(self):
        """Sla data op."""
        with open(self.data_file, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)

    def _nieuwe_capsule(self):
        """Maak nieuwe time capsule."""
        clear_scherm()
        print("\n  === NIEUWE TIME CAPSULE ===\n")

        capsule = {
            "id": f"cap_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "aangemaakt": datetime.now().isoformat(),
            "open_datum": None,
            "titel": "",
            "berichten": [],
            "stemming": "",
            "doelen": [],
            "geopend": False,
        }

        # Titel
        print("  Geef je capsule een titel:")
        capsule["titel"] = input("  > ").strip() or "Mijn Time Capsule"

        # Wanneer openen
        print("\n  Wanneer mag deze capsule geopend worden?")
        for i, (naam, dagen) in enumerate(self.PERIODES, 1):
            open_datum = datetime.now() + timedelta(days=dagen)
            print(f"    {i}. {naam} ({open_datum.strftime('%d-%m-%Y')})")
        print("    7. Eigen datum")

        keuze = input("\n  Keuze: ").strip()

        if keuze == "7":
            datum_str = input("  Datum (DD-MM-YYYY): ").strip()
            try:
                open_datum = datetime.strptime(datum_str, "%d-%m-%Y")
            except ValueError:
                open_datum = datetime.now() + timedelta(days=30)
        else:
            try:
                idx = int(keuze) - 1
                dagen = self.PERIODES[idx][1]
                open_datum = datetime.now() + timedelta(days=dagen)
            except (ValueError, IndexError):
                open_datum = datetime.now() + timedelta(days=30)

        capsule["open_datum"] = open_datum.isoformat()

        # Huidige stemming
        print("\n  Hoe voel je je nu? (1 woord of korte zin):")
        capsule["stemming"] = input("  > ").strip()

        # Berichten schrijven
        print("\n  === SCHRIJF JE BERICHTEN ===")
        print("  (Beantwoord de vragen of schrijf vrij)")
        print("  Typ 'klaar' om te stoppen.\n")

        import random
        beschikbare_prompts = list(self.PROMPTS)
        random.shuffle(beschikbare_prompts)

        for prompt in beschikbare_prompts:
            print(f"\n  {prompt}")
            print("  (Typ je antwoord, of 'skip' om over te slaan, 'klaar' om te stoppen)")

            lijnen = []
            while True:
                lijn = input("  > ")
                if lijn.lower() == "klaar":
                    break
                if lijn.lower() == "skip":
                    lijnen = []
                    break
                if lijn == "":
                    if lijnen:
                        break
                    continue
                lijnen.append(lijn)

            if lijn.lower() == "klaar":
                break

            if lijnen:
                capsule["berichten"].append({
                    "prompt": prompt,
                    "antwoord": "\n".join(lijnen),
                })

        # Vrij bericht
        print("\n  Wil je nog een vrij bericht toevoegen? (j/n)")
        if input("  > ").lower() == "j":
            print("\n  Schrijf je bericht (leeg = klaar):")
            lijnen = []
            while True:
                lijn = input("  > ")
                if lijn == "":
                    break
                lijnen.append(lijn)

            if lijnen:
                capsule["berichten"].append({
                    "prompt": "Vrij bericht",
                    "antwoord": "\n".join(lijnen),
                })

        # Doelen
        print("\n  Wat hoop je bereikt te hebben als je dit opent?")
        print("  (Een doel per regel, leeg = klaar)")

        while True:
            doel = input("  - ").strip()
            if not doel:
                break
            capsule["doelen"].append(doel)

        # Opslaan
        self.data["capsules"].append(capsule)
        self._sla_op()

        # Bevestiging
        clear_scherm()
        print("\n  " + "=" * 50)
        print("  TIME CAPSULE VERZEGELD!")
        print("  " + "=" * 50)
        print(f"\n  Titel: {capsule['titel']}")
        print(f"  Berichten: {len(capsule['berichten'])}")
        print(f"  Doelen: {len(capsule['doelen'])}")
        print(f"\n  Kan geopend worden op: {open_datum.strftime('%d %B %Y')}")

        dagen_tot = (open_datum - datetime.now()).days
        print(f"  Dat is over {dagen_tot} dagen!")

        input("\n  Druk op Enter...")

    def _bekijk_capsules(self):
        """Bekijk alle capsules."""
        clear_scherm()
        print("\n  === MIJN TIME CAPSULES ===\n")

        capsules = self.data.get("capsules", [])

        if not capsules:
            print("  Nog geen time capsules gemaakt.")
            input("\n  Druk op Enter...")
            return

        nu = datetime.now()

        # Categoriseer
        te_openen = []
        nog_wachten = []
        al_geopend = []

        for c in capsules:
            open_datum = datetime.fromisoformat(c["open_datum"])

            if c.get("geopend"):
                al_geopend.append(c)
            elif open_datum <= nu:
                te_openen.append(c)
            else:
                nog_wachten.append(c)

        # Toon te openen
        if te_openen:
            print("  KLAAR OM TE OPENEN:")
            for c in te_openen:
                print(f"    [{c['id'][-6:]}] {c['titel']} - OPEN MIJ!")

        # Toon wachtende
        if nog_wachten:
            print("\n  NOG VERZEGELD:")
            for c in nog_wachten:
                open_datum = datetime.fromisoformat(c["open_datum"])
                dagen = (open_datum - nu).days
                print(f"    [{c['id'][-6:]}] {c['titel']} - nog {dagen} dagen")

        # Toon geopende
        if al_geopend:
            print("\n  REEDS GEOPEND:")
            for c in al_geopend:
                print(f"    [{c['id'][-6:]}] {c['titel']}")

        # Actie
        if te_openen:
            print("\n  Je hebt capsules klaar om te openen!")

        keuze = input("\n  Typ capsule ID om te openen (of Enter): ").strip()

        if keuze:
            for c in capsules:
                if keuze in c["id"]:
                    self._open_capsule(c)
                    return

    def _open_capsule(self, capsule: Dict):
        """Open een time capsule."""
        open_datum = datetime.fromisoformat(capsule["open_datum"])
        nu = datetime.now()

        if open_datum > nu and not capsule.get("geopend"):
            dagen = (open_datum - nu).days
            print(f"\n  Deze capsule kan nog niet geopend worden!")
            print(f"  Nog {dagen} dagen wachten...")

            force = input("\n  Toch openen? (ja/nee): ").strip().lower()
            if force != "ja":
                input("\n  Druk op Enter...")
                return

        clear_scherm()
        print("\n  " + "=" * 60)
        print("  TIME CAPSULE WORDT GEOPEND...")
        print("  " + "=" * 60)

        input("\n  Druk op Enter om te openen...")

        clear_scherm()

        aangemaakt = datetime.fromisoformat(capsule["aangemaakt"])
        dagen_geleden = (nu - aangemaakt).days

        print("\n  " + "*" * 60)
        print(f"  {capsule['titel'].upper()}")
        print("  " + "*" * 60)

        print(f"\n  Geschreven op: {aangemaakt.strftime('%d %B %Y')}")
        print(f"  Dat is {dagen_geleden} dagen geleden!")

        if capsule.get("stemming"):
            print(f"\n  Je stemming toen: {capsule['stemming']}")

        print("\n  " + "-" * 60)
        print("  BERICHTEN VAN JE VERLEDEN ZELF:")
        print("  " + "-" * 60)

        for bericht in capsule.get("berichten", []):
            print(f"\n  {bericht['prompt']}")
            print("  " + "~" * 40)
            for lijn in bericht["antwoord"].split("\n"):
                print(f"    {lijn}")

        if capsule.get("doelen"):
            print("\n  " + "-" * 60)
            print("  DOELEN DIE JE HAD GESTELD:")
            print("  " + "-" * 60)

            for doel in capsule["doelen"]:
                print(f"\n    [ ] {doel}")
                bereikt = input("        Bereikt? (j/n): ").strip().lower()
                if bereikt == "j":
                    print("        Gefeliciteerd!")

        # Markeer als geopend
        for c in self.data["capsules"]:
            if c["id"] == capsule["id"]:
                c["geopend"] = True
                c["geopend_op"] = nu.isoformat()
                break

        self.data["geopend"].append(capsule["id"])
        self._sla_op()

        print("\n  " + "=" * 60)
        print("  Time Capsule ervaring compleet!")
        print("  " + "=" * 60)

        input("\n  Druk op Enter...")

    def _snelle_notitie(self):
        """Schrijf een snelle notitie voor later."""
        clear_scherm()
        print("\n  === SNELLE NOTITIE ===\n")
        print("  Schrijf een kort bericht voor je toekomstige zelf.\n")

        bericht = input("  Bericht: ").strip()

        if not bericht:
            return

        print("\n  Wanneer herinneren?")
        print("    1. Morgen")
        print("    2. Volgende week")
        print("    3. Volgende maand")

        keuze = input("\n  Keuze: ").strip()

        dagen = {"1": 1, "2": 7, "3": 30}.get(keuze, 7)
        open_datum = datetime.now() + timedelta(days=dagen)

        capsule = {
            "id": f"note_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "aangemaakt": datetime.now().isoformat(),
            "open_datum": open_datum.isoformat(),
            "titel": "Snelle Notitie",
            "berichten": [{"prompt": "Notitie", "antwoord": bericht}],
            "stemming": "",
            "doelen": [],
            "geopend": False,
        }

        self.data["capsules"].append(capsule)
        self._sla_op()

        print(f"\n  Notitie opgeslagen voor {open_datum.strftime('%d-%m-%Y')}!")
        input("\n  Druk op Enter...")

    def _check_herinneringen(self):
        """Check of er capsules klaar zijn om te openen."""
        nu = datetime.now()
        te_openen = []

        for c in self.data.get("capsules", []):
            if not c.get("geopend"):
                open_datum = datetime.fromisoformat(c["open_datum"])
                if open_datum <= nu:
                    te_openen.append(c)

        return te_openen

    def _statistieken(self):
        """Toon statistieken."""
        clear_scherm()
        print("\n  === TIME CAPSULE STATISTIEKEN ===\n")

        capsules = self.data.get("capsules", [])

        totaal = len(capsules)
        geopend = sum(1 for c in capsules if c.get("geopend"))
        verzegeld = totaal - geopend

        print(f"  Totaal capsules: {totaal}")
        print(f"  Geopend: {geopend}")
        print(f"  Nog verzegeld: {verzegeld}")

        te_openen = self._check_herinneringen()
        if te_openen:
            print(f"\n  Klaar om te openen: {len(te_openen)}")

        # Gemiddelde wachttijd
        if geopend > 0:
            wachttijden = []
            for c in capsules:
                if c.get("geopend") and c.get("geopend_op"):
                    aangemaakt = datetime.fromisoformat(c["aangemaakt"])
                    geopend_op = datetime.fromisoformat(c["geopend_op"])
                    wachttijden.append((geopend_op - aangemaakt).days)

            if wachttijden:
                gem = sum(wachttijden) / len(wachttijden)
                print(f"\n  Gemiddelde wachttijd: {gem:.0f} dagen")

        # Volgende te openen
        nog_verzegeld = [c for c in capsules if not c.get("geopend")]
        if nog_verzegeld:
            volgende = min(nog_verzegeld,
                          key=lambda x: x["open_datum"])
            open_datum = datetime.fromisoformat(volgende["open_datum"])
            dagen = (open_datum - datetime.now()).days

            print(f"\n  Volgende capsule: {volgende['titel']}")
            if dagen > 0:
                print(f"  Over {dagen} dagen")
            else:
                print("  Nu te openen!")

        input("\n  Druk op Enter...")

    def run(self):
        """Start de app."""
        # Check herinneringen bij start
        te_openen = self._check_herinneringen()

        while True:
            clear_scherm()

            capsules = len(self.data.get("capsules", []))
            verzegeld = sum(1 for c in self.data.get("capsules", [])
                          if not c.get("geopend"))

            print(f"""
  ╔═══════════════════════════════════════════════════════════╗
  ║              TIME CAPSULE v1.0                            ║
  ║         Berichten naar je Toekomstige Zelf                ║
  ╠═══════════════════════════════════════════════════════════╣
  ║  1. Nieuwe Time Capsule                                   ║
  ║  2. Bekijk Capsules                                       ║
  ║  3. Snelle Notitie                                        ║
  ║  4. Statistieken                                          ║
  ║  0. Terug                                                 ║
  ╚═══════════════════════════════════════════════════════════╝
""")
            print(f"  Capsules: {capsules} | Verzegeld: {verzegeld}")

            if te_openen:
                print(f"\n  *** {len(te_openen)} capsule(s) klaar om te openen! ***")

            keuze = input("\n  Keuze: ").strip()

            if keuze == "0":
                break
            elif keuze == "1":
                self._nieuwe_capsule()
            elif keuze == "2":
                self._bekijk_capsules()
            elif keuze == "3":
                self._snelle_notitie()
            elif keuze == "4":
                self._statistieken()

            # Refresh herinneringen
            te_openen = self._check_herinneringen()
