"""
Flashcards v2.0 - AI-Powered digitale flashcards.
"""

import random
from datetime import datetime, timedelta
from ..core.utils import clear_scherm
from .base_app import BaseApp


class FlashcardsApp(BaseApp):
    """AI-Powered spaced repetition flashcards."""

    def __init__(self):
        super().__init__("flashcards.json")

    def _get_default_data(self) -> dict:
        return {
            "decks": [],
            "stats": {
                "totaal_reviews": 0,
                "correct": 0
            }
        }

    def run(self):
        """Start de flashcard app."""
        while True:
            clear_scherm()
            print("+" + "=" * 50 + "+")
            print("|          FLASHCARDS v2.0                          |")
            if self.client:
                print("|          [AI POWERED]                            |")
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
            print("+" + "-" * 50 + "+")
            print("|  [AI FUNCTIES]                                    |")
            print("|  7. AI Kaarten Genereren                          |")
            print("|  8. AI Uitleg                                     |")
            print("|  9. AI Quiz Mode                                  |")
            print("+" + "-" * 50 + "+")
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
            elif keuze == "7":
                self._ai_kaarten_genereren()
            elif keuze == "8":
                self._ai_uitleg()
            elif keuze == "9":
                self._ai_quiz_mode()

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

    # ==================== AI FUNCTIES ====================

    def _ai_kaarten_genereren(self):
        """AI genereert flashcards over een onderwerp."""
        print("\n--- AI KAARTEN GENEREREN ---")

        onderwerp = input("Onderwerp voor kaarten: ").strip()
        if not onderwerp:
            print("[!] Geen onderwerp ingevoerd.")
            return

        aantal = input("Aantal kaarten (5-20): ").strip()
        try:
            aantal = max(5, min(20, int(aantal)))
        except ValueError:
            aantal = 10

        if not self.client:
            print("\n[!] AI niet beschikbaar. Voeg handmatig kaarten toe.")
            return

        print(f"\n[AI genereert {aantal} kaarten over '{onderwerp}'...]")

        prompt = f"""Genereer {aantal} flashcards over: {onderwerp}

Format elke kaart als:
VRAAG: [vraag]
ANTWOORD: [antwoord]
---

Maak de vragen duidelijk en de antwoorden beknopt maar compleet.
Varieer in moeilijkheid. Nederlands."""

        response = self._ai_request(prompt, max_tokens=1000)
        if response:
            print("\n[AI Kaarten]:")
            print(response)

            # Vraag of ze toegevoegd moeten worden
            toevoegen = input("\nToevoegen aan deck? (j/n): ").strip().lower()
            if toevoegen == "j":
                deck = self._kies_deck()
                if not deck:
                    # Maak nieuw deck
                    deck = {
                        "id": len(self.data["decks"]) + 1,
                        "naam": onderwerp,
                        "kaarten": [],
                        "aangemaakt": datetime.now().isoformat()
                    }
                    self.data["decks"].append(deck)

                # Parse kaarten
                kaarten_raw = response.split("---")
                toegevoegd = 0
                for k in kaarten_raw:
                    if "VRAAG:" in k and "ANTWOORD:" in k:
                        try:
                            vraag = k.split("VRAAG:")[1].split("ANTWOORD:")[0].strip()
                            antwoord = k.split("ANTWOORD:")[1].strip()
                            if vraag and antwoord:
                                deck["kaarten"].append({
                                    "id": len(deck["kaarten"]) + 1,
                                    "voorkant": vraag,
                                    "achterkant": antwoord,
                                    "niveau": 0,
                                    "volgende_review": datetime.now().isoformat()
                                })
                                toegevoegd += 1
                        except (IndexError, ValueError):
                            print("Fout: AI-kaart kon niet"
                                  " worden geparsed, overgeslagen.")
                            continue

                self._sla_op()
                print(f"[OK] {toegevoegd} kaarten toegevoegd aan '{deck['naam']}'!")

    def _ai_uitleg(self):
        """AI legt een concept uit."""
        print("\n--- AI UITLEG ---")

        concept = input("Welk concept wil je uitgelegd hebben? ").strip()
        if not concept:
            return

        if not self.client:
            print("\n[!] AI niet beschikbaar.")
            return

        print("\n[AI legt uit...]")
        prompt = f"""Leg dit concept duidelijk uit: {concept}

Geef:
1. Simpele definitie
2. Uitgebreidere uitleg
3. Praktisch voorbeeld
4. Veelgemaakte fouten

Geschikt voor studenten. Nederlands."""

        response = self._ai_request(prompt, max_tokens=600)
        if response:
            print(f"\n[AI Uitleg]:\n{response}")

    def _ai_quiz_mode(self):
        """AI stelt vragen over je kaarten."""
        print("\n--- AI QUIZ MODE ---")

        deck = self._kies_deck()
        if not deck or not deck["kaarten"]:
            print("[!] Kies een deck met kaarten.")
            return

        if not self.client:
            # Fallback: gewoon studeren
            self._studeren()
            return

        print(f"\n[AI Quiz over '{deck['naam']}']")
        print("De AI stelt vragen op basis van je kaarten.\n")

        # Verzamel kaarten context
        kaarten_info = "\n".join([
            f"- {k['voorkant']}: {k['achterkant']}"
            for k in deck["kaarten"][:15]  # Max 15
        ])

        for ronde in range(3):  # 3 vragen
            print(f"\n--- Vraag {ronde + 1}/3 ---")

            prompt = f"""Op basis van deze flashcards, stel een creatieve vraag:

{kaarten_info}

Stel een vraag die de kennis test maar anders geformuleerd is dan de originele kaarten.
Geef alleen de vraag, geen antwoord. Nederlands."""

            vraag = self._ai_request(prompt, max_tokens=150)
            if vraag:
                print(f"\n{vraag}")
                antwoord = input("\nJouw antwoord: ").strip()

                # Laat AI evalueren
                eval_prompt = f"""Evalueer dit antwoord.
Vraag: {vraag}
Gegeven antwoord: {antwoord}
Relevante kaarten: {kaarten_info}

Geef kort feedback: is het correct, deels correct, of onjuist?
Geef het juiste antwoord als het fout was. Nederlands, 2-3 zinnen."""

                feedback = self._ai_request(eval_prompt, max_tokens=200)
                if feedback:
                    print(f"\n[Feedback]: {feedback}")

        print("\n[OK] Quiz voltooid!")
