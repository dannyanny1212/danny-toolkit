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
        print("0. Terug naar hoofdmenu")
        print("===========================")

    def run(self):
        """Start de app."""
        clear_scherm()
        print("Welkom bij de Slimme Rekenmachine!")

        operaties = {
            "1": (self.optellen, "+"),
            "2": (self.aftrekken, "-"),
            "3": (self.vermenigvuldigen, "*"),
            "4": (self.delen, "/"),
            "5": (self.machtsverheffen, "^"),
        }

        while True:
            self._toon_menu()
            keuze = input("\nKies een optie (0-5): ").strip()

            if keuze == "0":
                print("Terug naar hoofdmenu...")
                break

            if keuze not in operaties:
                print("Ongeldige keuze. Kies een nummer van 0 tot 5.")
                continue

            getal1 = self._get_getal("Voer het eerste getal in: ")
            getal2 = self._get_getal("Voer het tweede getal in: ")

            try:
                functie, operator = operaties[keuze]
                resultaat = functie(getal1, getal2)
                print(f"\nResultaat: {getal1} {operator} {getal2} = {resultaat}")
            except ValueError as e:
                print(f"\nFout: {e}")
            except Exception as e:
                print(f"\nOnverwachte fout: {e}")
