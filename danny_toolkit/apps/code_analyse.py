"""
Code Analyse App - Python best practices demo.
"""

from collections import Counter
from statistics import mean, median, stdev
from typing import List, Dict, Any, Optional

from ..core.utils import clear_scherm


class CodeAnalyseApp:
    """Demonstreert Python best practices en code analyse."""

    @staticmethod
    def bereken_som(getallen: List[float]) -> float:
        """Berekent de som van een lijst getallen."""
        return sum(getallen)

    @staticmethod
    def bereken_gemiddelde(getallen: List[float]) -> Optional[float]:
        """Berekent het gemiddelde, None bij lege lijst."""
        if not getallen:
            return None
        return mean(getallen)

    @staticmethod
    def bereken_statistieken(getallen: List[float]) -> Dict[str, Any]:
        """Berekent uitgebreide statistieken van een lijst getallen."""
        if not getallen:
            return {"fout": "Lege lijst"}

        return {
            "som": sum(getallen),
            "gemiddelde": mean(getallen),
            "mediaan": median(getallen),
            "minimum": min(getallen),
            "maximum": max(getallen),
            "bereik": max(getallen) - min(getallen),
            "aantal": len(getallen),
            "standaarddeviatie": stdev(getallen) if len(getallen) > 1 else 0
        }

    @staticmethod
    def bevat(getallen: List[Any], waarde: Any) -> bool:
        """Controleert of een waarde in de lijst zit."""
        return waarde in getallen

    @staticmethod
    def zoek_index(getallen: List[Any], waarde: Any) -> Optional[int]:
        """Geeft de index van een waarde, of None als niet gevonden."""
        try:
            return getallen.index(waarde)
        except ValueError:
            return None

    @staticmethod
    def sorteer(getallen: List[float], omgekeerd: bool = False) -> List[float]:
        """Sorteert een lijst (optioneel omgekeerd)."""
        return sorted(getallen, reverse=omgekeerd)

    @staticmethod
    def tel_woorden(tekst: str, hoofdlettergevoelig: bool = False) -> Dict[str, int]:
        """
        Telt woorden in een tekst.
        Verwijdert leestekens en kan hoofdletterongevoelig tellen.
        """
        if not hoofdlettergevoelig:
            tekst = tekst.lower()

        for teken in ".,!?;:\"'()[]{}":
            tekst = tekst.replace(teken, "")

        woorden = tekst.split()
        return dict(Counter(woorden))

    @staticmethod
    def meest_voorkomende_woorden(tekst: str, aantal: int = 3) -> List[tuple]:
        """Geeft de N meest voorkomende woorden."""
        telling = Counter(tekst.lower().split())
        return telling.most_common(aantal)

    def run(self):
        """Start de app."""
        clear_scherm()
        print("=" * 50)
        print("DEMO: Python Code Analyse")
        print("=" * 50)

        # Getallen statistieken
        getallen = [5, 2, 8, 1, 9, 3]
        print(f"\nGetallen: {getallen}")

        stats = self.bereken_statistieken(getallen)
        print("\nStatistieken:")
        for sleutel, waarde in stats.items():
            if isinstance(waarde, float):
                print(f"  {sleutel}: {waarde:.2f}")
            else:
                print(f"  {sleutel}: {waarde}")

        # Zoeken
        print(f"\nBevat 8: {self.bevat(getallen, 8)}")
        print(f"Index van 8: {self.zoek_index(getallen, 8)}")
        print(f"Bevat 99: {self.bevat(getallen, 99)}")

        # Sorteren
        print(f"\nOplopend: {self.sorteer(getallen)}")
        print(f"Aflopend: {self.sorteer(getallen, omgekeerd=True)}")

        # Woordtelling
        print("\n" + "-" * 50)
        zin = "De kat zat op de mat. De mat was rood, heel rood!"
        print(f"Zin: \"{zin}\"")
        print(f"\nWoordtelling: {self.tel_woorden(zin)}")
        print(f"Top 3 woorden: {self.meest_voorkomende_woorden(zin)}")

        # Interactieve modus
        print("\n" + "=" * 50)
        print("INTERACTIEVE MODUS")
        print("=" * 50)

        while True:
            print("\n1. Analyseer eigen getallen")
            print("2. Tel woorden in eigen tekst")
            print("0. Terug naar hoofdmenu")

            keuze = input("\nKeuze: ").strip()

            if keuze == "0":
                break
            elif keuze == "1":
                invoer = input("Voer getallen in (gescheiden door spaties): ")
                try:
                    nummers = [float(x) for x in invoer.split()]
                    if nummers:
                        stats = self.bereken_statistieken(nummers)
                        print("\nResultaat:")
                        for k, v in stats.items():
                            print(f"  {k}: {v}")
                    else:
                        print("Geen geldige getallen.")
                except ValueError:
                    print("Fout: voer geldige getallen in.")
            elif keuze == "2":
                tekst = input("Voer een tekst in: ")
                if tekst:
                    telling = self.tel_woorden(tekst)
                    top = self.meest_voorkomende_woorden(tekst)
                    print(f"\nAantal unieke woorden: {len(telling)}")
                    print(f"Top 3: {top}")
                else:
                    print("Geen tekst ingevoerd.")
            else:
                print("Ongeldige keuze.")
