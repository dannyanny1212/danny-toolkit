"""
Flashcards - Leer met digitale flashcards.
"""

import json
import random
from datetime import datetime, timedelta
from ..core.config import Config
from ..core.utils import clear_scherm


class FlashcardsApp:
    """Leer met spaced repetition flashcards."""

    def __init__(self):
        Config.ensure_dirs()
        self.bestand = Config.APPS_DATA_DIR / "flashcards.json"
        self.data = self._laad_data()

    def _laad_data(self) -> dict:
        """Laad flashcard data."""
        if self.bestand.exists():
            try:
                with open(self.bestand, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return {
            "decks": [],
            "stats": {
                "totaal_reviews": 0,
                "correct": 0
            }
        }

    def _sla_op(self):
        """Sla data op."""
        with open(self.bestand, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)

    def run(self):
        """Start de flashcard app."""
        while True:
            clear_scherm()
            print("+" + "=" * 50 + "+")
            print("|          FLASHCARDS                               |")
            print("+" + "=" * 50 + "+")
            print(f"|  Decks: {len(self.data['decks']):<41}|")
            print(f"|  Reviews: {self.data['stats']['totaal_reviews']:<39}|")
            print("+" + "-" * 50 + "+")
            print("|  1. Studeren                                      |")
            print("|  2. Nieuw deck maken                              |")
            print("|  3. Kaart toevoegen                               |")
            print("|  4. Decks bekijken                                |")
            print("|  5. Statistieken                                  |")
            print("|  6. Deck verwijderen                              |")
            print("|  0. Terug                                         |")
            print("+" + "=" * 50 + "+")

            keuze = input("\nKeuze: ").strip()

            if keuze == "0":
                break
            elif keuze == "1":
                self._studeren()
            elif keuze == "2":
                self._nieuw_deck()
            elif keuze == "3":
                self._kaart_toevoegen()
            elif keuze == "4":
                self._bekijk_decks()
            elif keuze == "5":
                self._statistieken()
            elif keuze == "6":
                self._verwijder_deck()

            input("\nDruk op Enter...")

    def _nieuw_deck(self):
        """Maak een nieuw deck."""
        print("\n--- NIEUW DECK ---")

        naam = input("Deck naam: ").strip()
        if not naam:
            print("[!] Naam is verplicht!")
            return

        if any(d["naam"].lower() == naam.lower() for d in self.data["decks"]):
            print("[!] Dit deck bestaat al!")
            return

        deck = {
            "id": len(self.data["decks"]) + 1,
            "naam": naam,
            "kaarten": [],
            "aangemaakt": datetime.now().isoformat()
        }

        self.data["decks"].append(deck)
        self._sla_op()

        print(f"\n[OK] Deck '{naam}' aangemaakt!")
        print("     Voeg nu kaarten toe met optie 3.")

    def _kies_deck(self) -> dict:
        """Laat gebruiker een deck kiezen."""
        if not self.data["decks"]:
            print("[!] Geen decks gevonden. Maak eerst een deck!")
            return None

        print("\nKies een deck:")
        for d in self.data["decks"]:
            print(f"  {d['id']}. {d['naam']} ({len(d['kaarten'])} kaarten)")

        try:
            keuze = int(input("\nDeck ID: ").strip())
            deck = next((d for d in self.data["decks"] if d["id"] == keuze), None)
            return deck
        except ValueError:
            return None

    def _kaart_toevoegen(self):
        """Voeg een kaart toe aan een deck."""
        print("\n--- KAART TOEVOEGEN ---")

        deck = self._kies_deck()
        if not deck:
            return

        print(f"\nKaart toevoegen aan: {deck['naam']}")
        print("(Typ 'stop' om te stoppen)\n")

        while True:
            voorkant = input("Voorkant (vraag): ").strip()
            if voorkant.lower() == "stop":
                break

            achterkant = input("Achterkant (antwoord): ").strip()
            if achterkant.lower() == "stop":
                break

            kaart = {
                "id": len(deck["kaarten"]) + 1,
                "voorkant": voorkant,
                "achterkant": achterkant,
                "niveau": 0,
                "volgende_review": datetime.now().isoformat()
            }

            deck["kaarten"].append(kaart)
            print(f"[OK] Kaart toegevoegd!\n")

        self._sla_op()
        print(f"\nDeck '{deck['naam']}' heeft nu {len(deck['kaarten'])} kaarten.")

    def _studeren(self):
        """Studeer kaarten met spaced repetition."""
        print("\n--- STUDEREN ---")

        deck = self._kies_deck()
        if not deck:
            return

        if not deck["kaarten"]:
            print(f"[!] Deck '{deck['naam']}' heeft geen kaarten!")
            return

        # Filter kaarten die review nodig hebben
        nu = datetime.now()
        te_reviewen = [
            k for k in deck["kaarten"]
            if datetime.fromisoformat(k["volgende_review"]) <= nu
        ]

        if not te_reviewen:
            print("\n[OK] Alle kaarten zijn up-to-date!")
            print("     Kom later terug voor meer reviews.")
            return

        random.shuffle(te_reviewen)
        correct = 0
        totaal = len(te_reviewen)

        print(f"\n{totaal} kaarten te reviewen. Laten we beginnen!\n")
        print("(Druk Enter om antwoord te zien)")
        print("-" * 40)

        for i, kaart in enumerate(te_reviewen, 1):
            print(f"\nKaart {i}/{totaal}")
            print(f"\n  VRAAG: {kaart['voorkant']}")

            input("\n  [Druk Enter voor antwoord...]")

            print(f"\n  ANTWOORD: {kaart['achterkant']}")

            wist = input("\n  Wist je het? (j/n): ").strip().lower()

            if wist == "j":
                correct += 1
                kaart["niveau"] = min(kaart["niveau"] + 1, 5)
            else:
                kaart["niveau"] = max(kaart["niveau"] - 1, 0)

            # Bereken volgende review (spaced repetition)
            dagen = [0, 1, 3, 7, 14, 30][kaart["niveau"]]
            kaart["volgende_review"] = (
                datetime.now() + timedelta(days=dagen)
            ).isoformat()

        # Update stats
        self.data["stats"]["totaal_reviews"] += totaal
        self.data["stats"]["correct"] += correct
        self._sla_op()

        # Resultaat
        percentage = int((correct / totaal) * 100)
        print(f"\n{'=' * 40}")
        print(f"  RESULTAAT: {correct}/{totaal} correct ({percentage}%)")
        print(f"{'=' * 40}")

        if percentage == 100:
            print("  Perfect! Geweldig gedaan!")
        elif percentage >= 80:
            print("  Heel goed! Blijf zo doorgaan!")
        elif percentage >= 60:
            print("  Goed bezig! Oefen de moeilijke kaarten.")
        else:
            print("  Blijf oefenen, je wordt steeds beter!")

    def _bekijk_decks(self):
        """Bekijk alle decks en kaarten."""
        print("\n--- ALLE DECKS ---")

        if not self.data["decks"]:
            print("Geen decks gevonden.")
            return

        for d in self.data["decks"]:
            print(f"\n  [{d['naam']}] - {len(d['kaarten'])} kaarten")

            # Toon eerste 3 kaarten
            for k in d["kaarten"][:3]:
                print(f"    • {k['voorkant'][:30]}...")

            if len(d["kaarten"]) > 3:
                print(f"    ... en {len(d['kaarten']) - 3} meer")

    def _statistieken(self):
        """Toon leerstatistieken."""
        print("\n--- STATISTIEKEN ---")

        totaal_kaarten = sum(len(d["kaarten"]) for d in self.data["decks"])
        reviews = self.data["stats"]["totaal_reviews"]
        correct = self.data["stats"]["correct"]

        print(f"\n  Totaal decks: {len(self.data['decks'])}")
        print(f"  Totaal kaarten: {totaal_kaarten}")
        print(f"  Totaal reviews: {reviews}")

        if reviews > 0:
            percentage = int((correct / reviews) * 100)
            print(f"  Correct: {correct} ({percentage}%)")

        # Kaarten per niveau
        if totaal_kaarten > 0:
            print("\n  Kaarten per niveau:")
            niveaus = [0] * 6
            for d in self.data["decks"]:
                for k in d["kaarten"]:
                    niveaus[k.get("niveau", 0)] += 1

            niveau_namen = ["Nieuw", "Leren", "Jong", "Volwassen", "Matuur", "Meester"]
            for i, count in enumerate(niveaus):
                if count > 0:
                    print(f"    {niveau_namen[i]}: {count}")

    def _verwijder_deck(self):
        """Verwijder een deck."""
        deck = self._kies_deck()
        if not deck:
            return

        bevestig = input(f"Deck '{deck['naam']}' verwijderen? (j/n): ").strip().lower()
        if bevestig == "j":
            self.data["decks"].remove(deck)
            self._sla_op()
            print("[OK] Deck verwijderd!")
