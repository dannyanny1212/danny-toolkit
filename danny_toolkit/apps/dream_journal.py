"""
Dream Journal v1.0 - Log dromen, analyseer patronen, ontdek symbolen.
"""

import json
import random
from datetime import datetime, timedelta
from collections import Counter
from pathlib import Path
from typing import List, Dict, Optional
from ..core.config import Config
from ..core.utils import clear_scherm


class DreamJournalApp:
    """Dream Journal - Log en analyseer je dromen."""

    VERSIE = "1.0"

    # Droom symbolen en hun betekenissen
    SYMBOLEN = {
        "water": "Emoties, onderbewustzijn, reiniging",
        "vliegen": "Vrijheid, ambitie, ontsnapping",
        "vallen": "Controleverlies, angst, onzekerheid",
        "achtervolging": "Vermijding, angst, stress",
        "tanden": "Zelfbeeld, communicatie, zorgen",
        "huis": "Zelf, identiteit, veiligheid",
        "auto": "Levensrichting, controle, ambitie",
        "dood": "Verandering, einde, nieuwe begin",
        "baby": "Nieuw begin, onschuld, potentieel",
        "school": "Leren, onzekerheid, beoordeling",
        "werk": "Prestatie, stress, verantwoordelijkheid",
        "slang": "Transformatie, angst, wijsheid",
        "spin": "Creativiteit, angst, vrouwelijke kracht",
        "hond": "Loyaliteit, vriendschap, bescherming",
        "kat": "Onafhankelijkheid, intuïtie, mysterie",
        "vogel": "Vrijheid, spiritualiteit, boodschappen",
        "berg": "Obstakels, doelen, prestatie",
        "bos": "Onderbewustzijn, verwarring, groei",
        "zee": "Emoties, onbekende, diepte",
        "zon": "Energie, bewustzijn, succes",
        "maan": "Intuïtie, emoties, vrouwelijkheid",
        "regen": "Emoties, reiniging, verdriet",
        "vuur": "Passie, transformatie, woede",
        "bloemen": "Groei, schoonheid, vergankelijkheid",
    }

    # Droom categorieën
    CATEGORIEEN = [
        "nachtmerrie",
        "lucide",
        "terugkerend",
        "profetisch",
        "avontuur",
        "romantisch",
        "bizar",
        "alledaags",
    ]

    # Emoties
    EMOTIES = [
        "blij", "verdrietig", "bang", "boos", "verrast",
        "verward", "vredig", "angstig", "opgewonden", "nostalgisch",
    ]

    def __init__(self):
        Config.ensure_dirs()
        self.data_dir = Config.APPS_DATA_DIR / "dream_journal"
        self.data_dir.mkdir(exist_ok=True)
        self.data_file = self.data_dir / "dreams.json"
        self.data = self._laad_data()

    def _laad_data(self) -> Dict:
        """Laad dromen data."""
        if self.data_file.exists():
            try:
                with open(self.data_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return {
            "dromen": [],
            "symbolen_count": {},
            "streak": 0,
            "laatste_log": None,
        }

    def _sla_op(self):
        """Sla data op."""
        with open(self.data_file, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)

    def _log_droom(self):
        """Log een nieuwe droom."""
        clear_scherm()
        print("\n  === NIEUWE DROOM LOGGEN ===\n")

        droom = {
            "datum": datetime.now().isoformat(),
            "titel": "",
            "beschrijving": "",
            "emoties": [],
            "symbolen": [],
            "categorie": "",
            "helderheid": 3,
            "notities": "",
        }

        # Titel
        droom["titel"] = input("  Titel: ").strip() or "Naamloze droom"

        # Beschrijving
        print("\n  Beschrijf je droom (typ 'klaar' op nieuwe regel als je klaar bent):")
        lijnen = []
        while True:
            lijn = input("  > ")
            if lijn.lower() == "klaar":
                break
            lijnen.append(lijn)
        droom["beschrijving"] = "\n".join(lijnen)

        # Emoties
        print(f"\n  Emoties (kies meerdere, komma-gescheiden):")
        print(f"  Opties: {', '.join(self.EMOTIES)}")
        emotie_input = input("  Emoties: ").strip().lower()
        droom["emoties"] = [e.strip() for e in emotie_input.split(",") if e.strip()]

        # Categorie
        print(f"\n  Categorieën: {', '.join(self.CATEGORIEEN)}")
        droom["categorie"] = input("  Categorie: ").strip().lower() or "alledaags"

        # Helderheid (1-5)
        try:
            helderheid = int(input("\n  Helderheid (1-5): ").strip() or "3")
            droom["helderheid"] = max(1, min(5, helderheid))
        except ValueError:
            droom["helderheid"] = 3

        # Automatische symbool detectie
        tekst = (droom["titel"] + " " + droom["beschrijving"]).lower()
        gevonden_symbolen = []

        for symbool in self.SYMBOLEN:
            if symbool in tekst:
                gevonden_symbolen.append(symbool)
                # Update symbolen count
                if symbool not in self.data["symbolen_count"]:
                    self.data["symbolen_count"][symbool] = 0
                self.data["symbolen_count"][symbool] += 1

        droom["symbolen"] = gevonden_symbolen

        if gevonden_symbolen:
            print(f"\n  Gevonden symbolen: {', '.join(gevonden_symbolen)}")
            print("  Betekenissen:")
            for s in gevonden_symbolen:
                print(f"    - {s}: {self.SYMBOLEN[s]}")

        # Extra symbolen toevoegen
        extra = input("\n  Extra symbolen (komma-gescheiden, of Enter): ").strip()
        if extra:
            for s in extra.split(","):
                s = s.strip().lower()
                if s and s not in droom["symbolen"]:
                    droom["symbolen"].append(s)

        # Notities
        droom["notities"] = input("\n  Persoonlijke notities: ").strip()

        # Opslaan
        self.data["dromen"].append(droom)

        # Update streak (check vorige log VOOR update)
        vorige_log = self.data["laatste_log"]
        if vorige_log:
            laatste = datetime.fromisoformat(vorige_log)
            dagen_verschil = (datetime.now() - laatste).days
            if dagen_verschil == 0:
                pass  # Zelfde dag, streak ongewijzigd
            elif dagen_verschil == 1:
                self.data["streak"] += 1
            else:
                self.data["streak"] = 1
        else:
            self.data["streak"] = 1

        self.data["laatste_log"] = droom["datum"]

        self._sla_op()

        print("\n  " + "=" * 40)
        print("  DROOM OPGESLAGEN!")
        print(f"  Streak: {self.data['streak']} nachten")
        print("  " + "=" * 40)

        input("\n  Druk op Enter...")

    def _bekijk_dromen(self):
        """Bekijk dromen geschiedenis."""
        clear_scherm()
        print("\n  === DROMEN GESCHIEDENIS ===\n")

        dromen = self.data.get("dromen", [])

        if not dromen:
            print("  Nog geen dromen gelogd.")
            input("\n  Druk op Enter...")
            return

        # Toon laatste 10
        print("  Recente dromen:")
        for i, d in enumerate(reversed(dromen[-10:]), 1):
            datum = d["datum"][:10]
            titel = d["titel"][:30]
            emoties = ", ".join(d.get("emoties", [])[:2])
            helderheid = "*" * d.get("helderheid", 3)
            print(f"  {i}. {datum} | {titel:30} | {helderheid} | {emoties}")

        keuze = input("\n  Bekijk # (of Enter): ").strip()
        if keuze.isdigit():
            idx = len(dromen) - int(keuze)
            if 0 <= idx < len(dromen):
                self._toon_droom_details(dromen[idx])

    def _toon_droom_details(self, droom: Dict):
        """Toon details van een droom."""
        clear_scherm()
        print("\n  " + "=" * 50)
        print(f"  {droom['titel'].upper()}")
        print("  " + "=" * 50)

        print(f"\n  Datum: {droom['datum'][:10]}")
        print(f"  Categorie: {droom.get('categorie', '-')}")
        print(f"  Helderheid: {'*' * droom.get('helderheid', 3)}")
        print(f"  Emoties: {', '.join(droom.get('emoties', []))}")

        print(f"\n  BESCHRIJVING:")
        for lijn in droom.get("beschrijving", "").split("\n"):
            print(f"    {lijn}")

        symbolen = droom.get("symbolen", [])
        if symbolen:
            print(f"\n  SYMBOLEN:")
            for s in symbolen:
                betekenis = self.SYMBOLEN.get(s, "Persoonlijke betekenis")
                print(f"    - {s}: {betekenis}")

        if droom.get("notities"):
            print(f"\n  NOTITIES: {droom['notities']}")

        input("\n  Druk op Enter...")

    def _analyseer_patronen(self):
        """Analyseer droom patronen."""
        clear_scherm()
        print("\n  === DROOM ANALYSE ===\n")

        dromen = self.data.get("dromen", [])

        if len(dromen) < 3:
            print("  Minimaal 3 dromen nodig voor analyse.")
            input("\n  Druk op Enter...")
            return

        # Symbolen frequentie
        print("  MEEST VOORKOMENDE SYMBOLEN:")
        symbolen_count = Counter()
        for d in dromen:
            symbolen_count.update(d.get("symbolen", []))

        for symbool, count in symbolen_count.most_common(5):
            betekenis = self.SYMBOLEN.get(symbool, "?")
            bar = "#" * min(count, 10)
            print(f"    {symbool:15} {bar} ({count}x)")
            print(f"      -> {betekenis}")

        # Emoties frequentie
        print("\n  MEEST VOORKOMENDE EMOTIES:")
        emoties_count = Counter()
        for d in dromen:
            emoties_count.update(d.get("emoties", []))

        for emotie, count in emoties_count.most_common(5):
            bar = "#" * min(count, 10)
            print(f"    {emotie:15} {bar} ({count}x)")

        # Categorieën
        print("\n  DROOM CATEGORIEËN:")
        cat_count = Counter(d.get("categorie", "onbekend") for d in dromen)
        for cat, count in cat_count.most_common():
            pct = count / len(dromen) * 100
            print(f"    {cat:15} {pct:5.1f}%")

        # Gemiddelde helderheid
        gem_helderheid = sum(d.get("helderheid", 3) for d in dromen) / len(dromen)
        print(f"\n  Gemiddelde helderheid: {'*' * round(gem_helderheid)} ({gem_helderheid:.1f}/5)")

        # Lucide dromen percentage
        lucide = sum(1 for d in dromen if d.get("categorie") == "lucide")
        lucide_pct = lucide / len(dromen) * 100
        print(f"  Lucide dromen: {lucide_pct:.1f}%")

        input("\n  Druk op Enter...")

    def _symbolen_gids(self):
        """Toon symbolen gids."""
        clear_scherm()
        print("\n  === DROOM SYMBOLEN GIDS ===\n")

        # Sorteer op frequentie
        symbolen_count = self.data.get("symbolen_count", {})

        for symbool, betekenis in sorted(self.SYMBOLEN.items()):
            count = symbolen_count.get(symbool, 0)
            count_str = f" (je dromen: {count}x)" if count > 0 else ""
            print(f"  {symbool:15}: {betekenis}{count_str}")

        input("\n  Druk op Enter...")

    def _zoek_dromen(self):
        """Zoek in dromen."""
        clear_scherm()
        print("\n  === ZOEK IN DROMEN ===\n")

        zoekterm = input("  Zoekterm: ").strip().lower()

        if not zoekterm:
            return

        dromen = self.data.get("dromen", [])
        resultaten = []

        for d in dromen:
            tekst = (d["titel"] + " " + d["beschrijving"]).lower()
            if zoekterm in tekst:
                resultaten.append(d)

        if not resultaten:
            print(f"\n  Geen dromen gevonden met '{zoekterm}'")
        else:
            print(f"\n  {len(resultaten)} dromen gevonden:\n")
            for i, d in enumerate(resultaten, 1):
                print(f"  {i}. {d['datum'][:10]} - {d['titel']}")

            keuze = input("\n  Bekijk # (of Enter): ").strip()
            if keuze.isdigit():
                idx = int(keuze) - 1
                if 0 <= idx < len(resultaten):
                    self._toon_droom_details(resultaten[idx])
                    return

        input("\n  Druk op Enter...")

    def _random_interpretatie(self):
        """Genereer een random droom interpretatie."""
        clear_scherm()
        print("\n  === DROOM INTERPRETATIE ===\n")

        dromen = self.data.get("dromen", [])

        if not dromen:
            print("  Log eerst wat dromen!")
            input("\n  Druk op Enter...")
            return

        # Kies random droom
        droom = random.choice(dromen)

        print(f"  Droom: {droom['titel']}")
        print("  " + "-" * 40)

        symbolen = droom.get("symbolen", [])
        emoties = droom.get("emoties", [])

        if symbolen:
            print("\n  Mogelijke interpretatie:\n")

            interpretaties = [
                f"De aanwezigheid van '{symbolen[0]}' suggereert dat je "
                f"bezig bent met {self.SYMBOLEN.get(symbolen[0], 'iets belangrijks')}."
            ]

            if len(symbolen) > 1:
                interpretaties.append(
                    f"De combinatie met '{symbolen[1]}' wijst op een verband "
                    f"met {self.SYMBOLEN.get(symbolen[1], 'andere aspecten')}."
                )

            if emoties:
                interpretaties.append(
                    f"De {emoties[0]} gevoelens kunnen wijzen op hoe je je "
                    f"voelt over deze thema's in je wakkere leven."
                )

            if droom.get("categorie") == "terugkerend":
                interpretaties.append(
                    "Als terugkerende droom vraagt dit onderwerp om je aandacht."
                )

            for interp in interpretaties:
                print(f"    {interp}")
        else:
            print("\n  Geen symbolen gevonden voor interpretatie.")
            print("  Probeer symbolen handmatig toe te voegen bij het loggen.")

        input("\n  Druk op Enter...")

    def run(self):
        """Start de app."""
        while True:
            clear_scherm()

            streak = self.data.get("streak", 0)
            dromen_count = len(self.data.get("dromen", []))

            print(f"""
  ╔═══════════════════════════════════════════════════════════╗
  ║              DREAM JOURNAL v1.0                           ║
  ║           Log & Analyseer je Dromen                       ║
  ╠═══════════════════════════════════════════════════════════╣
  ║  1. Log Nieuwe Droom                                      ║
  ║  2. Bekijk Dromen                                         ║
  ║  3. Analyseer Patronen                                    ║
  ║  4. Symbolen Gids                                         ║
  ║  5. Zoek in Dromen                                        ║
  ║  6. Random Interpretatie                                  ║
  ║  0. Terug                                                 ║
  ╚═══════════════════════════════════════════════════════════╝
""")
            print(f"  Dromen: {dromen_count} | Streak: {streak} nachten")

            keuze = input("\n  Keuze: ").strip()

            if keuze == "0":
                break
            elif keuze == "1":
                self._log_droom()
            elif keuze == "2":
                self._bekijk_dromen()
            elif keuze == "3":
                self._analyseer_patronen()
            elif keuze == "4":
                self._symbolen_gids()
            elif keuze == "5":
                self._zoek_dromen()
            elif keuze == "6":
                self._random_interpretatie()
