"""
Slimme Rekenmachine App.
"""

from ..core.utils import clear_scherm


class RekenmachineApp:
    """Interactieve rekenmachine applicatie."""

    @staticmethod
    def optellen(a: float, b: float) -> float:
        return a + b

    @staticmethod
    def aftrekken(a: float, b: float) -> float:
        return a - b

    @staticmethod
    def vermenigvuldigen(a: float, b: float) -> float:
        return a * b

    @staticmethod
    def delen(a: float, b: float) -> float:
        if b == 0:
            raise ValueError("Kan niet delen door nul!")
        return a / b

    @staticmethod
    def machtsverheffen(a: float, b: float) -> float:
        return a ** b

    @staticmethod
    def worteltrekken(a: float) -> float:
        if a < 0:
            raise ValueError("Kan geen wortel trekken van een negatief getal!")
        return a ** 0.5

    @staticmethod
    def _get_getal(prompt: str) -> float:
        """Vraagt om een getal met foutafhandeling."""
        while True:
            try:
                return float(input(prompt))
            except ValueError:
                print("Ongeldige invoer. Voer een geldig getal in.")

    def _toon_menu(self):
        """Toont het menu."""
        print("\n=== Slimme Rekenmachine ===")
        print("1. Optellen (+)")
        print("2. Aftrekken (-)")
        print("3. Vermenigvuldigen (*)")
        print("4. Delen (/)")
        print("5. Machtsverheffen (^)")
        print("6. Worteltrekken (√)")
        print("0. Terug naar hoofdmenu")
        print("===========================")

    def run(self):
        """Start de app."""
        clear_scherm()
        print("Welkom bij de Slimme Rekenmachine!")

        operaties = {
            "1": (self.optellen, "+", False),
            "2": (self.aftrekken, "-", False),
            "3": (self.vermenigvuldigen, "*", False),
            "4": (self.delen, "/", False),
            "5": (self.machtsverheffen, "^", False),
            "6": (self.worteltrekken, "√", True),
        }

        while True:
            self._toon_menu()
            keuze = input("\nKies een optie (0-6): ").strip()

            if keuze == "0":
                print("Terug naar hoofdmenu...")
                break

            if keuze not in operaties:
                print("Ongeldige keuze. Kies een nummer van 0 tot 6.")
                continue

            functie, operator, enkel_getal = operaties[keuze]

            if enkel_getal:
                getal1 = self._get_getal("Voer het getal in: ")
                try:
                    resultaat = functie(getal1)
                    print(f"\nResultaat: {operator}{getal1} = {resultaat}")
                except ValueError as e:
                    print(f"\nFout: {e}")
                continue

            getal1 = self._get_getal("Voer het eerste getal in: ")
            getal2 = self._get_getal("Voer het tweede getal in: ")

            try:
                resultaat = functie(getal1, getal2)
                print(f"\nResultaat: {getal1} {operator} {getal2} = {resultaat}")
            except ValueError as e:
                print(f"\nFout: {e}")
            except Exception as e:
                print(f"\nOnverwachte fout: {e}")
