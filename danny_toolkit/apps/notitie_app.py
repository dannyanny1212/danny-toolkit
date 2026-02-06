"""
Notitie App - Notities maken en organiseren.
"""

import json
from datetime import datetime
from pathlib import Path
from ..core.config import Config
from ..core.utils import clear_scherm


class NotitieApp:
    """Een app voor het maken en organiseren van notities."""

    def __init__(self):
        Config.ensure_dirs()
        self.bestand = Config.APPS_DATA_DIR / "notities.json"
        self.notities = self._laad_notities()

    def _laad_notities(self) -> dict:
        """Laad notities uit bestand."""
        if self.bestand.exists():
            try:
                with open(self.bestand, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return {"notities": [], "categorieen": ["Algemeen", "Werk", "Persoonlijk", "Ideeen"]}

    def _sla_op(self):
        """Sla notities op."""
        with open(self.bestand, "w", encoding="utf-8") as f:
            json.dump(self.notities, f, indent=2, ensure_ascii=False)

    def run(self):
        """Start de notitie app."""
        while True:
            clear_scherm()
            print("+" + "=" * 50 + "+")
            print("|          NOTITIE APP                             |")
            print("+" + "=" * 50 + "+")
            print(f"|  Totaal notities: {len(self.notities['notities']):<30}|")
            print("+" + "-" * 50 + "+")
            print("|  1. Nieuwe notitie                               |")
            print("|  2. Notities bekijken                            |")
            print("|  3. Notitie zoeken                               |")
            print("|  4. Notitie verwijderen                          |")
            print("|  5. Categorieen beheren                          |")
            print("|  0. Terug                                        |")
            print("+" + "=" * 50 + "+")

            keuze = input("\nKeuze: ").strip()

            if keuze == "0":
                break
            elif keuze == "1":
                self._nieuwe_notitie()
            elif keuze == "2":
                self._bekijk_notities()
            elif keuze == "3":
                self._zoek_notitie()
            elif keuze == "4":
                self._verwijder_notitie()
            elif keuze == "5":
                self._beheer_categorieen()

            input("\nDruk op Enter...")

    def _nieuwe_notitie(self):
        """Maak een nieuwe notitie."""
        print("\n--- NIEUWE NOTITIE ---")

        # Kies categorie
        print("\nCategorieen:")
        for i, cat in enumerate(self.notities["categorieen"], 1):
            print(f"  {i}. {cat}")

        try:
            cat_idx = int(input("\nKies categorie: ").strip()) - 1
            categorie = self.notities["categorieen"][cat_idx]
        except (ValueError, IndexError):
            categorie = "Algemeen"

        titel = input("Titel: ").strip()
        if not titel:
            print("[!] Titel is verplicht!")
            return

        print("Inhoud (typ 'KLAAR' op een nieuwe regel als je klaar bent):")
        inhoud_regels = []
        while True:
            regel = input()
            if regel.strip().upper() == "KLAAR":
                break
            inhoud_regels.append(regel)

        inhoud = "\n".join(inhoud_regels)

        notitie = {
            "id": len(self.notities["notities"]) + 1,
            "titel": titel,
            "inhoud": inhoud,
            "categorie": categorie,
            "gemaakt": datetime.now().isoformat(),
            "gewijzigd": datetime.now().isoformat()
        }

        self.notities["notities"].append(notitie)
        self._sla_op()
        print(f"\n[OK] Notitie '{titel}' opgeslagen!")

    def _bekijk_notities(self):
        """Bekijk alle notities."""
        print("\n--- ALLE NOTITIES ---")

        if not self.notities["notities"]:
            print("Geen notities gevonden.")
            return

        # Groepeer per categorie
        per_categorie = {}
        for n in self.notities["notities"]:
            cat = n.get("categorie", "Algemeen")
            if cat not in per_categorie:
                per_categorie[cat] = []
            per_categorie[cat].append(n)

        for cat, notities in per_categorie.items():
            print(f"\n[{cat}]")
            for n in notities:
                datum = n["gemaakt"][:10]
                print(f"  {n['id']}. {n['titel'][:30]} ({datum})")

        # Detail bekijken
        keuze = input("\nNotitie ID om te lezen (of Enter): ").strip()
        if keuze:
            try:
                notitie_id = int(keuze)
                for n in self.notities["notities"]:
                    if n["id"] == notitie_id:
                        print(f"\n{'=' * 50}")
                        print(f"TITEL: {n['titel']}")
                        print(f"Categorie: {n['categorie']}")
                        print(f"Datum: {n['gemaakt'][:10]}")
                        print(f"{'=' * 50}")
                        print(n["inhoud"])
                        print(f"{'=' * 50}")
                        break
            except ValueError:
                pass

    def _zoek_notitie(self):
        """Zoek in notities."""
        zoekterm = input("\nZoekterm: ").strip().lower()
        if not zoekterm:
            return

        resultaten = []
        for n in self.notities["notities"]:
            if zoekterm in n["titel"].lower() or zoekterm in n["inhoud"].lower():
                resultaten.append(n)

        print(f"\n--- RESULTATEN ({len(resultaten)}) ---")
        for n in resultaten:
            print(f"  {n['id']}. {n['titel']} [{n['categorie']}]")

    def _verwijder_notitie(self):
        """Verwijder een notitie."""
        self._bekijk_notities()
        try:
            notitie_id = int(input("\nNotitie ID om te verwijderen: ").strip())
            for i, n in enumerate(self.notities["notities"]):
                if n["id"] == notitie_id:
                    bevestig = input(f"'{n['titel']}' verwijderen? (j/n): ").strip().lower()
                    if bevestig == "j":
                        self.notities["notities"].pop(i)
                        self._sla_op()
                        print("[OK] Notitie verwijderd!")
                    break
        except ValueError:
            pass

    def _beheer_categorieen(self):
        """Beheer categorieen."""
        print("\n--- CATEGORIEEN ---")
        for i, cat in enumerate(self.notities["categorieen"], 1):
            print(f"  {i}. {cat}")

        print("\n  a. Nieuwe categorie")
        print("  0. Terug")

        keuze = input("\nKeuze: ").strip().lower()
        if keuze == "a":
            nieuwe = input("Nieuwe categorie naam: ").strip()
            if nieuwe and nieuwe not in self.notities["categorieen"]:
                self.notities["categorieen"].append(nieuwe)
                self._sla_op()
                print(f"[OK] Categorie '{nieuwe}' toegevoegd!")
