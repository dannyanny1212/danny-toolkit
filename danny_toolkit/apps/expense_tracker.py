"""
Expense Tracker v2.0 - AI-Powered uitgaven tracker.
"""

from datetime import datetime
from collections import defaultdict
from ..core.utils import clear_scherm
from .base_app import BaseApp


class ExpenseTrackerApp(BaseApp):
    """AI-Powered uitgaven en budget tracker."""

    def __init__(self):
        super().__init__("expenses.json")

    def _get_default_data(self) -> dict:
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

    def _log_memory_event(self, event_type, data):
        """Log event naar Unified Memory."""
        try:
            if not hasattr(self, "_memory"):
                from ..brain.unified_memory import UnifiedMemory
                self._memory = UnifiedMemory()
            self._memory.store_event(
                app="expense_tracker",
                event_type=event_type,
                data=data
            )
        except Exception:
            pass  # Memory is optioneel

    def run(self):
        """Start de expense tracker."""
        while True:
            clear_scherm()
            print("+" + "=" * 50 + "+")
            print("|          EXPENSE TRACKER v2.0                     |")
            if self.client:
                print("|          [AI POWERED]                            |")
            print("+" + "=" * 50 + "+")
            self._toon_saldo()
            print("+" + "-" * 50 + "+")
            print("|  1. Uitgave toevoegen                             |")
            print("|  2. Inkomen toevoegen                             |")
            print("|  3. Overzicht deze maand                          |")
            print("|  4. Uitgaven per categorie                        |")
            print("|  5. Budget instellen                              |")
            print("|  6. Alle transacties                              |")
            print("+" + "-" * 50 + "+")
            print("|  [AI FUNCTIES]                                    |")
            print("|  7. AI Uitgaven Analyse                           |")
            print("|  8. AI Budget Advies                              |")
            print("|  9. AI Spaartips                                  |")
            print("+" + "-" * 50 + "+")
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
            elif keuze == "7":
                self._ai_uitgaven_analyse()
            elif keuze == "8":
                self._ai_budget_advies()
            elif keuze == "9":
                self._ai_spaartips()

            input("\nDruk op Enter...")

    def _toon_saldo(self):
        """Toon huidig saldo."""
        totaal_inkomen = sum(i["bedrag"] for i in self.data["inkomsten"])
        totaal_uitgaven = sum(u["bedrag"] for u in self.data["uitgaven"])
        saldo = totaal_inkomen - totaal_uitgaven

        if saldo >= 0:
            saldo_str = f"+€{saldo:.2f}"
        else:
            saldo_str = f"-€{abs(saldo):.2f}"
        padding = " " * max(0, 38 - len(saldo_str))
        print(f"|  Saldo: {saldo_str}{padding}|")

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
        self._log_memory_event("expense_added", {
            "bedrag": bedrag, "categorie": categorie
        })

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
        self._log_memory_event("income_added", {
            "bedrag": bedrag
        })

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

    # ==================== AI FUNCTIES ====================

    def _get_finance_context(self) -> str:
        """Verzamel financiele data voor AI."""
        maand = datetime.now().strftime("%Y-%m")
        uitgaven = [u for u in self.data["uitgaven"] if u["datum"].startswith(maand)]
        inkomsten = [i for i in self.data["inkomsten"] if i["datum"].startswith(maand)]

        totaal_uit = sum(u["bedrag"] for u in uitgaven)
        totaal_in = sum(i["bedrag"] for i in inkomsten)

        per_cat = defaultdict(float)
        for u in uitgaven:
            per_cat[u["categorie"]] += u["bedrag"]

        context = f"Financieel overzicht deze maand:\n"
        context += f"- Inkomen: €{totaal_in:.2f}\n"
        context += f"- Uitgaven: €{totaal_uit:.2f}\n"
        context += f"- Verschil: €{totaal_in - totaal_uit:.2f}\n\n"
        context += "Uitgaven per categorie:\n"
        for cat, bedrag in sorted(per_cat.items(), key=lambda x: x[1], reverse=True):
            pct = (bedrag / totaal_uit * 100) if totaal_uit > 0 else 0
            context += f"- {cat}: €{bedrag:.2f} ({pct:.0f}%)\n"

        return context

    def _ai_uitgaven_analyse(self):
        """AI analyseert je uitgavenpatronen."""
        print("\n--- AI UITGAVEN ANALYSE ---")

        if not self.data["uitgaven"]:
            print("[!] Geen uitgaven om te analyseren.")
            return

        context = self._get_finance_context()

        if not self.client:
            maand = datetime.now().strftime("%Y-%m")
            uitgaven = [u for u in self.data["uitgaven"] if u["datum"].startswith(maand)]
            totaal = sum(u["bedrag"] for u in uitgaven)
            print(f"\n[Analyse]: €{totaal:.2f} uitgegeven deze maand.")
            if totaal > 1000:
                print("  Let op je grote uitgaven!")
            return

        print("\n[AI analyseert...]")
        prompt = f"""Analyseer deze uitgaven en geef inzichten.

{context}

Geef:
1. Uitgavenpatroon observaties
2. Opvallende posten
3. Vergelijking met typische huishoudens
4. Concrete bespaartips

Wees specifiek en praktisch. Nederlands."""

        response = self._ai_request(prompt, max_tokens=500)
        if response:
            print(f"\n[AI Analyse]:\n{response}")

    def _ai_budget_advies(self):
        """AI geeft budget advies."""
        print("\n--- AI BUDGET ADVIES ---")

        context = self._get_finance_context()

        if not self.client:
            print("\n[Advies]: Algemene budgetregel 50/30/20:")
            print("  - 50% voor vaste lasten")
            print("  - 30% voor wensen")
            print("  - 20% voor sparen")
            return

        print("\n[AI genereert advies...]")
        prompt = f"""Geef persoonlijk budget advies op basis van:

{context}

Budgetten ingesteld: {self.data.get('budget', {})}

Geef:
1. Evaluatie huidige verdeling
2. Aanbevolen budget per categorie
3. Tips voor budget discipline
4. Prioriteiten stellen

Praktisch en haalbaar. Nederlands."""

        response = self._ai_request(prompt, max_tokens=500)
        if response:
            print(f"\n[AI Budget Advies]:\n{response}")

    def _ai_spaartips(self):
        """AI geeft spaartips."""
        print("\n--- AI SPAARTIPS ---")

        context = self._get_finance_context()

        if not self.client:
            print("\n[Spaartips]:")
            print("  • Maak een automatische spaaropdracht")
            print("  • Wacht 24 uur voor grote aankopen")
            print("  • Maak boodschappenlijstjes")
            print("  • Vergelijk prijzen online")
            return

        print("\n[AI genereert tips...]")
        prompt = f"""Geef gepersonaliseerde spaartips op basis van:

{context}

Geef 5-7 concrete spaartips:
- Specifiek voor de grootste uitgavencategorien
- Praktisch en direct toepasbaar
- Mix van kleine en grote besparingen

Nederlands, motiverend."""

        response = self._ai_request(prompt, max_tokens=500)
        if response:
            print(f"\n[AI Spaartips]:\n{response}")
