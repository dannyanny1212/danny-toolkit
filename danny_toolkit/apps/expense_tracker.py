"""
Expense Tracker - Houd je uitgaven bij.
"""

import json
from datetime import datetime
from collections import defaultdict
from ..core.config import Config
from ..core.utils import clear_scherm


class ExpenseTrackerApp:
    """Beheer je uitgaven en budget."""

    def __init__(self):
        Config.ensure_dirs()
        self.bestand = Config.APPS_DATA_DIR / "expenses.json"
        self.data = self._laad_data()

    def _laad_data(self) -> dict:
        """Laad expense data."""
        if self.bestand.exists():
            try:
                with open(self.bestand, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return {
            "uitgaven": [],
            "inkomsten": [],
            "categorieen": [
                "Boodschappen", "Transport", "Entertainment",
                "Eten & Drinken", "Wonen", "Gezondheid",
                "Kleding", "Overig"
            ],
            "budget": {}
        }

    def _sla_op(self):
        """Sla data op."""
        with open(self.bestand, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)

    def run(self):
        """Start de expense tracker."""
        while True:
            clear_scherm()
            print("+" + "=" * 50 + "+")
            print("|          EXPENSE TRACKER                          |")
            print("+" + "=" * 50 + "+")
            self._toon_saldo()
            print("+" + "-" * 50 + "+")
            print("|  1. Uitgave toevoegen                             |")
            print("|  2. Inkomen toevoegen                             |")
            print("|  3. Overzicht deze maand                          |")
            print("|  4. Uitgaven per categorie                        |")
            print("|  5. Budget instellen                              |")
            print("|  6. Alle transacties                              |")
            print("|  0. Terug                                         |")
            print("+" + "=" * 50 + "+")

            keuze = input("\nKeuze: ").strip()

            if keuze == "0":
                break
            elif keuze == "1":
                self._voeg_uitgave_toe()
            elif keuze == "2":
                self._voeg_inkomen_toe()
            elif keuze == "3":
                self._maand_overzicht()
            elif keuze == "4":
                self._per_categorie()
            elif keuze == "5":
                self._budget_instellen()
            elif keuze == "6":
                self._alle_transacties()

            input("\nDruk op Enter...")

    def _toon_saldo(self):
        """Toon huidig saldo."""
        totaal_inkomen = sum(i["bedrag"] for i in self.data["inkomsten"])
        totaal_uitgaven = sum(u["bedrag"] for u in self.data["uitgaven"])
        saldo = totaal_inkomen - totaal_uitgaven

        kleur = "+" if saldo >= 0 else ""
        print(f"|  Saldo: {kleur}€{saldo:.2f}{' ' * (38 - len(f'{saldo:.2f}'))}|")

    def _voeg_uitgave_toe(self):
        """Voeg een uitgave toe."""
        print("\n--- UITGAVE TOEVOEGEN ---")

        try:
            bedrag = float(input("Bedrag (€): ").strip().replace(",", "."))
            if bedrag <= 0:
                print("[!] Bedrag moet positief zijn!")
                return
        except ValueError:
            print("[!] Ongeldig bedrag!")
            return

        print("\nCategorie:")
        for i, cat in enumerate(self.data["categorieen"], 1):
            print(f"  {i}. {cat}")

        try:
            cat_idx = int(input("\nKies categorie: ").strip()) - 1
            categorie = self.data["categorieen"][cat_idx]
        except (ValueError, IndexError):
            categorie = "Overig"

        beschrijving = input("Beschrijving: ").strip() or "Geen beschrijving"

        uitgave = {
            "id": len(self.data["uitgaven"]) + 1,
            "bedrag": bedrag,
            "categorie": categorie,
            "beschrijving": beschrijving,
            "datum": datetime.now().isoformat()
        }

        self.data["uitgaven"].append(uitgave)
        self._sla_op()

        print(f"\n[OK] Uitgave van €{bedrag:.2f} toegevoegd!")

        # Check budget
        maand = datetime.now().strftime("%Y-%m")
        if categorie in self.data["budget"]:
            maand_uitgaven = sum(
                u["bedrag"] for u in self.data["uitgaven"]
                if u["categorie"] == categorie and u["datum"].startswith(maand)
            )
            budget = self.data["budget"][categorie]
            if maand_uitgaven > budget:
                print(f"[!] Let op: Budget voor {categorie} overschreden!")
                print(f"    Uitgegeven: €{maand_uitgaven:.2f} / Budget: €{budget:.2f}")

    def _voeg_inkomen_toe(self):
        """Voeg inkomen toe."""
        print("\n--- INKOMEN TOEVOEGEN ---")

        try:
            bedrag = float(input("Bedrag (€): ").strip().replace(",", "."))
            if bedrag <= 0:
                print("[!] Bedrag moet positief zijn!")
                return
        except ValueError:
            print("[!] Ongeldig bedrag!")
            return

        beschrijving = input("Bron/beschrijving: ").strip() or "Inkomen"

        inkomen = {
            "id": len(self.data["inkomsten"]) + 1,
            "bedrag": bedrag,
            "beschrijving": beschrijving,
            "datum": datetime.now().isoformat()
        }

        self.data["inkomsten"].append(inkomen)
        self._sla_op()

        print(f"\n[OK] Inkomen van €{bedrag:.2f} toegevoegd!")

    def _maand_overzicht(self):
        """Toon overzicht van deze maand."""
        print("\n--- MAAND OVERZICHT ---")

        maand = datetime.now().strftime("%Y-%m")
        maand_naam = datetime.now().strftime("%B %Y")

        uitgaven = [u for u in self.data["uitgaven"] if u["datum"].startswith(maand)]
        inkomsten = [i for i in self.data["inkomsten"] if i["datum"].startswith(maand)]

        totaal_uit = sum(u["bedrag"] for u in uitgaven)
        totaal_in = sum(i["bedrag"] for i in inkomsten)
        verschil = totaal_in - totaal_uit

        print(f"\n  {maand_naam}")
        print(f"  {'-' * 30}")
        print(f"  Inkomen:   +€{totaal_in:.2f}")
        print(f"  Uitgaven:  -€{totaal_uit:.2f}")
        print(f"  {'-' * 30}")
        print(f"  Verschil:  {'+'if verschil >= 0 else ''}€{verschil:.2f}")

        if uitgaven:
            print(f"\n  Recente uitgaven:")
            for u in uitgaven[-5:]:
                print(f"    - €{u['bedrag']:.2f} ({u['categorie']})")

    def _per_categorie(self):
        """Toon uitgaven per categorie."""
        print("\n--- UITGAVEN PER CATEGORIE ---")

        maand = datetime.now().strftime("%Y-%m")
        per_cat = defaultdict(float)

        for u in self.data["uitgaven"]:
            if u["datum"].startswith(maand):
                per_cat[u["categorie"]] += u["bedrag"]

        if not per_cat:
            print("Geen uitgaven deze maand.")
            return

        totaal = sum(per_cat.values())

        # Sorteer op bedrag
        gesorteerd = sorted(per_cat.items(), key=lambda x: x[1], reverse=True)

        print(f"\n  Deze maand (totaal: €{totaal:.2f}):\n")
        for cat, bedrag in gesorteerd:
            percentage = (bedrag / totaal) * 100
            bar_len = int(percentage / 5)
            bar = "█" * bar_len

            budget = self.data["budget"].get(cat)
            budget_str = f" / €{budget:.0f}" if budget else ""

            print(f"  {cat:15} €{bedrag:7.2f}{budget_str}")
            print(f"                  {bar} {percentage:.0f}%")

    def _budget_instellen(self):
        """Stel maandelijks budget in per categorie."""
        print("\n--- BUDGET INSTELLEN ---")

        print("\nHuidige budgetten:")
        for cat in self.data["categorieen"]:
            budget = self.data["budget"].get(cat, 0)
            print(f"  {cat}: €{budget:.2f}")

        print("\nKies categorie:")
        for i, cat in enumerate(self.data["categorieen"], 1):
            print(f"  {i}. {cat}")

        try:
            cat_idx = int(input("\nKeuze: ").strip()) - 1
            categorie = self.data["categorieen"][cat_idx]

            bedrag = float(input(f"Maandbudget voor {categorie} (€): ").strip().replace(",", "."))
            if bedrag < 0:
                print("[!] Budget kan niet negatief zijn!")
                return

            self.data["budget"][categorie] = bedrag
            self._sla_op()

            print(f"\n[OK] Budget voor {categorie} ingesteld op €{bedrag:.2f}")

        except (ValueError, IndexError):
            print("[!] Ongeldige invoer!")

    def _alle_transacties(self):
        """Bekijk alle transacties."""
        print("\n--- ALLE TRANSACTIES ---")

        # Combineer en sorteer
        alle = []
        for u in self.data["uitgaven"]:
            alle.append({**u, "type": "uitgave"})
        for i in self.data["inkomsten"]:
            alle.append({**i, "type": "inkomen"})

        alle.sort(key=lambda x: x["datum"], reverse=True)

        if not alle:
            print("Geen transacties.")
            return

        print(f"\n  Laatste 20 transacties:\n")
        for t in alle[:20]:
            datum = t["datum"][:10]
            if t["type"] == "uitgave":
                print(f"  {datum}  -€{t['bedrag']:7.2f}  {t['categorie'][:15]}")
            else:
                print(f"  {datum}  +€{t['bedrag']:7.2f}  {t['beschrijving'][:15]}")
