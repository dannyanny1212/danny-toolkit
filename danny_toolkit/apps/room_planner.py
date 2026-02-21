"""
Room Planner v1.0 - Virtuele ruimte-indeling optimizer.
Plan je kamer met ASCII visualisatie en slimme tips.
"""

import logging
from datetime import datetime
from ..core.utils import clear_scherm
from .base_app import BaseApp

logger = logging.getLogger(__name__)


class RoomPlannerApp(BaseApp):
    """Virtuele ruimte planner met ASCII visualisatie."""

    # Beschikbare meubels met symbolen en afmetingen
    MEUBELS = {
        "bed": {
            "naam": "Bed",
            "symbool": "B",
            "breedte": 4,
            "hoogte": 6,
            "kleur": "blauw"
        },
        "bed_enkel": {
            "naam": "Eenpersoonsbed",
            "symbool": "b",
            "breedte": 3,
            "hoogte": 6,
            "kleur": "blauw"
        },
        "bureau": {
            "naam": "Bureau",
            "symbool": "D",
            "breedte": 4,
            "hoogte": 2,
            "kleur": "bruin"
        },
        "kast": {
            "naam": "Kledingkast",
            "symbool": "K",
            "breedte": 3,
            "hoogte": 2,
            "kleur": "bruin"
        },
        "bank": {
            "naam": "Bank",
            "symbool": "S",
            "breedte": 5,
            "hoogte": 2,
            "kleur": "grijs"
        },
        "stoel": {
            "naam": "Stoel",
            "symbool": "s",
            "breedte": 1,
            "hoogte": 1,
            "kleur": "bruin"
        },
        "tafel": {
            "naam": "Eettafel",
            "symbool": "T",
            "breedte": 4,
            "hoogte": 3,
            "kleur": "bruin"
        },
        "salontafel": {
            "naam": "Salontafel",
            "symbool": "t",
            "breedte": 3,
            "hoogte": 2,
            "kleur": "bruin"
        },
        "tv": {
            "naam": "TV Meubel",
            "symbool": "V",
            "breedte": 4,
            "hoogte": 1,
            "kleur": "zwart"
        },
        "plant": {
            "naam": "Plant",
            "symbool": "P",
            "breedte": 1,
            "hoogte": 1,
            "kleur": "groen"
        },
        "lamp": {
            "naam": "Staande Lamp",
            "symbool": "L",
            "breedte": 1,
            "hoogte": 1,
            "kleur": "geel"
        },
        "boekenkast": {
            "naam": "Boekenkast",
            "symbool": "E",
            "breedte": 3,
            "hoogte": 1,
            "kleur": "bruin"
        },
        "nachtkastje": {
            "naam": "Nachtkastje",
            "symbool": "n",
            "breedte": 1,
            "hoogte": 1,
            "kleur": "bruin"
        },
        "deur": {
            "naam": "Deur",
            "symbool": "=",
            "breedte": 2,
            "hoogte": 1,
            "kleur": "wit"
        },
        "raam": {
            "naam": "Raam",
            "symbool": "#",
            "breedte": 3,
            "hoogte": 1,
            "kleur": "lichtblauw"
        }
    }

    def __init__(self):
        super().__init__("room_planner.json")
        self.huidig_project = None

    def _get_default_data(self) -> dict:
        """Standaard data structuur."""
        return {
            "projecten": [],
            "stats": {
                "totaal_projecten": 0,
                "totaal_meubels_geplaatst": 0
            }
        }

    def run(self):
        """Start de room planner."""
        while True:
            clear_scherm()
            self._toon_header()
            print("+" + "-" * 50 + "+")
            print("|  1. Nieuw Kamer Project                           |")
            print("|  2. Project Laden                                 |")
            print("|  3. Kamer Bekijken                                |")
            print("|  4. Meubel Plaatsen                               |")
            print("|  5. Meubel Verplaatsen                            |")
            print("|  6. Meubel Verwijderen                            |")
            print("|  7. Project Opslaan                               |")
            print("+" + "-" * 50 + "+")
            print("|  [AI FUNCTIES]                                    |")
            print("|  8. AI Indelings Suggesties                       |")
            print("|  9. AI Ruimte Analyse                             |")
            print("+" + "-" * 50 + "+")
            print("|  0. Terug                                         |")
            print("+" + "=" * 50 + "+")

            keuze = input("\nKeuze: ").strip()

            if keuze == "0":
                break
            elif keuze == "1":
                self._nieuw_project()
            elif keuze == "2":
                self._laad_project()
            elif keuze == "3":
                self._bekijk_kamer()
            elif keuze == "4":
                self._plaats_meubel()
            elif keuze == "5":
                self._verplaats_meubel()
            elif keuze == "6":
                self._verwijder_meubel()
            elif keuze == "7":
                self._sla_project_op()
            elif keuze == "8":
                self._ai_suggesties()
            elif keuze == "9":
                self._ai_analyse()

            input("\nDruk op Enter...")

    def _toon_header(self):
        """Toon header."""
        print("+" + "=" * 50 + "+")
        print("|          ROOM PLANNER v1.0                        |")
        if self.client:
            print("|          [AI POWERED]                            |")
        print("+" + "=" * 50 + "+")

        if self.huidig_project:
            naam = self.huidig_project["naam"][:20]
            breedte = self.huidig_project["breedte"]
            hoogte = self.huidig_project["hoogte"]
            meubels = len(self.huidig_project.get("meubels", []))
            print(f"|  Project: {naam:<15} {breedte}x{hoogte}m  "
                  f"Meubels: {meubels:<3}|")
        else:
            print("|  Geen project geladen                            |")

    # =========================================================================
    # PROJECT BEHEER
    # =========================================================================

    def _nieuw_project(self):
        """Maak nieuw kamer project."""
        print("\n--- NIEUW KAMER PROJECT ---")

        naam = input("Project naam: ").strip()
        if not naam:
            print("[!] Naam is verplicht!")
            return

        print("\nKamer type:")
        print("  1. Slaapkamer (4x4m)")
        print("  2. Woonkamer (6x5m)")
        print("  3. Studeerkamer (3x3m)")
        print("  4. Aangepast formaat")

        type_keuze = input("\nKeuze (1-4): ").strip()

        formaten = {
            "1": (16, 16, "Slaapkamer"),
            "2": (24, 20, "Woonkamer"),
            "3": (12, 12, "Studeerkamer")
        }

        if type_keuze in formaten:
            breedte, hoogte, kamer_type = formaten[type_keuze]
        else:
            try:
                breedte = int(input("Breedte (in grid units, 1 unit = 25cm): ").strip())
                hoogte = int(input("Hoogte (in grid units): ").strip())
                breedte = max(8, min(40, breedte))
                hoogte = max(8, min(30, hoogte))
                kamer_type = "Aangepast"
            except ValueError:
                breedte, hoogte, kamer_type = 16, 16, "Standaard"

        project = {
            "id": len(self.data["projecten"]) + 1,
            "naam": naam,
            "type": kamer_type,
            "breedte": breedte,
            "hoogte": hoogte,
            "meubels": [],
            "aangemaakt": datetime.now().isoformat()
        }

        self.data["projecten"].append(project)
        self.data["stats"]["totaal_projecten"] += 1
        self.huidig_project = project
        self._sla_op()

        print(f"\n[OK] Project '{naam}' aangemaakt!")
        print(f"     Afmetingen: {breedte} x {hoogte} grid units")
        print(f"     ({breedte * 0.25:.1f}m x {hoogte * 0.25:.1f}m)")

        # Vraag of ze muren/deuren willen plaatsen
        muren = input("\nWil je deuren/ramen toevoegen? (j/n): ").strip().lower()
        if muren == "j":
            self._voeg_openingen_toe()

    def _voeg_openingen_toe(self):
        """Voeg deuren en ramen toe."""
        print("\n--- DEUREN EN RAMEN ---")

        # Deur toevoegen
        print("\nWaar is de deur? (kant van de kamer)")
        print("  1. Boven   2. Onder   3. Links   4. Rechts")

        deur_kant = input("Keuze (1-4): ").strip()
        kant_map = {"1": "boven", "2": "onder", "3": "links", "4": "rechts"}
        deur_positie = kant_map.get(deur_kant, "onder")

        # Bereken deur positie
        if deur_positie == "boven":
            x = self.huidig_project["breedte"] // 2 - 1
            y = 0
        elif deur_positie == "onder":
            x = self.huidig_project["breedte"] // 2 - 1
            y = self.huidig_project["hoogte"] - 1
        elif deur_positie == "links":
            x = 0
            y = self.huidig_project["hoogte"] // 2
        else:
            x = self.huidig_project["breedte"] - 1
            y = self.huidig_project["hoogte"] // 2

        self.huidig_project["meubels"].append({
            "type": "deur",
            "x": x,
            "y": y,
            "rotatie": 0 if deur_positie in ["boven", "onder"] else 90
        })

        # Raam toevoegen
        raam = input("\nWil je een raam toevoegen? (j/n): ").strip().lower()
        if raam == "j":
            print("\nWaar is het raam?")
            print("  1. Boven   2. Onder   3. Links   4. Rechts")

            raam_kant = input("Keuze (1-4): ").strip()
            raam_positie = kant_map.get(raam_kant, "boven")

            if raam_positie == "boven":
                x = self.huidig_project["breedte"] // 2 - 1
                y = 0
            elif raam_positie == "onder":
                x = self.huidig_project["breedte"] // 2 - 1
                y = self.huidig_project["hoogte"] - 1
            elif raam_positie == "links":
                x = 0
                y = self.huidig_project["hoogte"] // 3
            else:
                x = self.huidig_project["breedte"] - 1
                y = self.huidig_project["hoogte"] // 3

            self.huidig_project["meubels"].append({
                "type": "raam",
                "x": x,
                "y": y,
                "rotatie": 0 if raam_positie in ["boven", "onder"] else 90
            })

        self._sla_op()
        print("\n[OK] Openingen toegevoegd!")

    def _laad_project(self):
        """Laad bestaand project."""
        print("\n--- PROJECT LADEN ---")

        if not self.data["projecten"]:
            print("[!] Geen projecten gevonden.")
            return

        print("\nBeschikbare projecten:")
        for p in self.data["projecten"]:
            meubels = len(p.get("meubels", []))
            print(f"  {p['id']}. {p['naam']} ({p['type']}, "
                  f"{p['breedte']}x{p['hoogte']}, {meubels} meubels)")

        try:
            project_id = int(input("\nProject ID: ").strip())
            project = next((p for p in self.data["projecten"]
                           if p["id"] == project_id), None)

            if not project:
                print("[!] Project niet gevonden!")
                return

            self.huidig_project = project
            print(f"\n[OK] Project '{project['naam']}' geladen!")

        except ValueError:
            print("[!] Ongeldig nummer!")

    def _sla_project_op(self):
        """Sla huidig project op."""
        if not self.huidig_project:
            print("\n[!] Geen project om op te slaan!")
            return

        self._sla_op()
        print(f"\n[OK] Project '{self.huidig_project['naam']}' opgeslagen!")

    # =========================================================================
    # VISUALISATIE
    # =========================================================================

    def _bekijk_kamer(self):
        """Bekijk de kamer layout."""
        if not self.huidig_project:
            print("\n[!] Laad eerst een project!")
            return

        self._render_kamer()

    def _render_kamer(self):
        """Render de kamer als ASCII art."""
        project = self.huidig_project
        breedte = project["breedte"]
        hoogte = project["hoogte"]

        # Maak lege grid
        grid = [["." for _ in range(breedte)] for _ in range(hoogte)]

        # Plaats meubels
        for meubel in project.get("meubels", []):
            meubel_def = self.MEUBELS.get(meubel["type"], {})
            symbool = meubel_def.get("symbool", "?")
            m_breedte = meubel_def.get("breedte", 1)
            m_hoogte = meubel_def.get("hoogte", 1)

            # Rotatie aanpassen
            if meubel.get("rotatie", 0) == 90:
                m_breedte, m_hoogte = m_hoogte, m_breedte

            x, y = meubel["x"], meubel["y"]

            for dy in range(m_hoogte):
                for dx in range(m_breedte):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < breedte and 0 <= ny < hoogte:
                        grid[ny][nx] = symbool

        # Render
        print(f"\n  KAMER: {project['naam']} ({project['type']})")
        print(f"  Afmetingen: {breedte * 0.25:.1f}m x {hoogte * 0.25:.1f}m")
        print()

        # Bovenkant muur
        print("  +" + "-" * breedte + "+")

        for row in grid:
            print("  |" + "".join(row) + "|")

        # Onderkant muur
        print("  +" + "-" * breedte + "+")

        # Legenda
        print("\n  LEGENDA:")
        geplaatste_types = set(m["type"] for m in project.get("meubels", []))

        for type_naam in geplaatste_types:
            if type_naam in self.MEUBELS:
                meubel = self.MEUBELS[type_naam]
                print(f"    {meubel['symbool']} = {meubel['naam']}")

        print("    . = Lege ruimte")

        # Statistieken
        print(f"\n  Meubels geplaatst: {len(project.get('meubels', []))}")
        vrije_ruimte = self._bereken_vrije_ruimte()
        print(f"  Vrije ruimte: {vrije_ruimte}%")

    def _bereken_vrije_ruimte(self) -> int:
        """Bereken percentage vrije ruimte."""
        if not self.huidig_project:
            return 100

        totaal = self.huidig_project["breedte"] * self.huidig_project["hoogte"]
        bezet = 0

        for meubel in self.huidig_project.get("meubels", []):
            meubel_def = self.MEUBELS.get(meubel["type"], {})
            m_breedte = meubel_def.get("breedte", 1)
            m_hoogte = meubel_def.get("hoogte", 1)

            if meubel.get("rotatie", 0) == 90:
                m_breedte, m_hoogte = m_hoogte, m_breedte

            bezet += m_breedte * m_hoogte

        vrij = ((totaal - bezet) / totaal) * 100
        return max(0, int(vrij))

    # =========================================================================
    # MEUBEL BEHEER
    # =========================================================================

    def _plaats_meubel(self):
        """Plaats een nieuw meubel."""
        if not self.huidig_project:
            print("\n[!] Laad eerst een project!")
            return

        print("\n--- MEUBEL PLAATSEN ---")

        # Toon beschikbare meubels
        print("\nBeschikbare meubels:")
        meubel_lijst = list(self.MEUBELS.items())

        for i, (key, meubel) in enumerate(meubel_lijst, 1):
            afm = f"{meubel['breedte']}x{meubel['hoogte']}"
            print(f"  {i:2}. {meubel['symbool']} {meubel['naam']:<20} ({afm})")

        try:
            meubel_keuze = int(input("\nMeubel nummer: ").strip()) - 1
            if meubel_keuze < 0 or meubel_keuze >= len(meubel_lijst):
                print("[!] Ongeldige keuze!")
                return

            meubel_type, meubel_def = meubel_lijst[meubel_keuze]

            # Toon huidige kamer
            self._render_kamer()

            print(f"\nPlaats {meubel_def['naam']} "
                  f"({meubel_def['breedte']}x{meubel_def['hoogte']})")

            x = int(input("X positie (0 = links): ").strip())
            y = int(input("Y positie (0 = boven): ").strip())

            # Valideer positie
            breedte = self.huidig_project["breedte"]
            hoogte = self.huidig_project["hoogte"]

            if x < 0 or x >= breedte or y < 0 or y >= hoogte:
                print("[!] Positie buiten de kamer!")
                return

            # Rotatie
            rotatie = 0
            if meubel_def["breedte"] != meubel_def["hoogte"]:
                rot = input("Roteren? (j/n): ").strip().lower()
                if rot == "j":
                    rotatie = 90

            # Check overlap
            if self._check_overlap(x, y, meubel_type, rotatie):
                print("[!] Overlapt met bestaand meubel!")
                toch = input("Toch plaatsen? (j/n): ").strip().lower()
                if toch != "j":
                    return

            # Plaats meubel
            self.huidig_project["meubels"].append({
                "type": meubel_type,
                "x": x,
                "y": y,
                "rotatie": rotatie
            })

            self.data["stats"]["totaal_meubels_geplaatst"] += 1
            self._sla_op()

            print(f"\n[OK] {meubel_def['naam']} geplaatst op ({x}, {y})!")

            # Toon resultaat
            self._render_kamer()

        except ValueError:
            print("[!] Voer geldige nummers in!")

    def _check_overlap(self, x: int, y: int, meubel_type: str,
                       rotatie: int) -> bool:
        """Check of meubel overlapt met bestaande meubels."""
        meubel_def = self.MEUBELS.get(meubel_type, {})
        m_breedte = meubel_def.get("breedte", 1)
        m_hoogte = meubel_def.get("hoogte", 1)

        if rotatie == 90:
            m_breedte, m_hoogte = m_hoogte, m_breedte

        nieuw_cells = set()
        for dy in range(m_hoogte):
            for dx in range(m_breedte):
                nieuw_cells.add((x + dx, y + dy))

        for meubel in self.huidig_project.get("meubels", []):
            bestaand_def = self.MEUBELS.get(meubel["type"], {})
            b_breedte = bestaand_def.get("breedte", 1)
            b_hoogte = bestaand_def.get("hoogte", 1)

            if meubel.get("rotatie", 0) == 90:
                b_breedte, b_hoogte = b_hoogte, b_breedte

            bx, by = meubel["x"], meubel["y"]
            for dy in range(b_hoogte):
                for dx in range(b_breedte):
                    if (bx + dx, by + dy) in nieuw_cells:
                        return True

        return False

    def _verplaats_meubel(self):
        """Verplaats een bestaand meubel."""
        if not self.huidig_project:
            print("\n[!] Laad eerst een project!")
            return

        meubels = self.huidig_project.get("meubels", [])
        if not meubels:
            print("\n[!] Geen meubels om te verplaatsen!")
            return

        print("\n--- MEUBEL VERPLAATSEN ---")
        self._render_kamer()

        print("\nGeplaatste meubels:")
        for i, m in enumerate(meubels, 1):
            meubel_def = self.MEUBELS.get(m["type"], {})
            print(f"  {i}. {meubel_def.get('naam', m['type'])} "
                  f"op ({m['x']}, {m['y']})")

        try:
            keuze = int(input("\nMeubel nummer: ").strip()) - 1
            if keuze < 0 or keuze >= len(meubels):
                print("[!] Ongeldige keuze!")
                return

            meubel = meubels[keuze]

            print(f"\nNieuwe positie voor {self.MEUBELS[meubel['type']]['naam']}:")
            x = int(input("X positie: ").strip())
            y = int(input("Y positie: ").strip())

            # Valideer
            breedte = self.huidig_project["breedte"]
            hoogte = self.huidig_project["hoogte"]

            if x < 0 or x >= breedte or y < 0 or y >= hoogte:
                print("[!] Positie buiten de kamer!")
                return

            meubel["x"] = x
            meubel["y"] = y

            self._sla_op()
            print(f"\n[OK] Meubel verplaatst naar ({x}, {y})!")
            self._render_kamer()

        except ValueError:
            print("[!] Voer geldige nummers in!")

    def _verwijder_meubel(self):
        """Verwijder een meubel."""
        if not self.huidig_project:
            print("\n[!] Laad eerst een project!")
            return

        meubels = self.huidig_project.get("meubels", [])
        if not meubels:
            print("\n[!] Geen meubels om te verwijderen!")
            return

        print("\n--- MEUBEL VERWIJDEREN ---")
        self._render_kamer()

        print("\nGeplaatste meubels:")
        for i, m in enumerate(meubels, 1):
            meubel_def = self.MEUBELS.get(m["type"], {})
            print(f"  {i}. {meubel_def.get('naam', m['type'])} "
                  f"op ({m['x']}, {m['y']})")

        try:
            keuze = int(input("\nMeubel nummer om te verwijderen: ").strip()) - 1
            if keuze < 0 or keuze >= len(meubels):
                print("[!] Ongeldige keuze!")
                return

            meubel = meubels[keuze]
            naam = self.MEUBELS[meubel["type"]]["naam"]

            bevestig = input(f"'{naam}' verwijderen? (j/n): ").strip().lower()
            if bevestig == "j":
                meubels.pop(keuze)
                self._sla_op()
                print(f"\n[OK] {naam} verwijderd!")
                self._render_kamer()

        except ValueError:
            print("[!] Voer een geldig nummer in!")

    # =========================================================================
    # AI FUNCTIES
    # =========================================================================

    def _get_room_context(self) -> str:
        """Verzamel kamer context voor AI."""
        if not self.huidig_project:
            return "Geen kamer project geladen."

        project = self.huidig_project
        context = f"Kamer: {project['naam']} ({project['type']})\n"
        context += f"Afmetingen: {project['breedte'] * 0.25:.1f}m x "
        context += f"{project['hoogte'] * 0.25:.1f}m\n"
        context += f"Vrije ruimte: {self._bereken_vrije_ruimte()}%\n\n"

        context += "Geplaatste meubels:\n"
        for m in project.get("meubels", []):
            meubel_def = self.MEUBELS.get(m["type"], {})
            context += f"- {meubel_def.get('naam', m['type'])} op positie "
            context += f"({m['x']}, {m['y']})\n"

        if not project.get("meubels"):
            context += "Geen meubels geplaatst.\n"

        return context

    def _ai_suggesties(self):
        """AI geeft indelings suggesties."""
        print("\n--- AI INDELINGS SUGGESTIES ---")

        if not self.huidig_project:
            print("[!] Laad eerst een project!")
            return

        if not self.client:
            print("\n[Suggesties voor optimale indeling]:")
            print("  1. Plaats het bed tegen de muur tegenover het raam")
            print("  2. Zorg voor looppaden van minimaal 60cm")
            print("  3. Plaats het bureau bij het raam voor natuurlijk licht")
            print("  4. Houd de deur vrij van obstakels")
            print("  5. Gebruik hoeken voor opbergruimte")
            return

        context = self._get_room_context()
        prompt = f"""Je bent een interieur designer. Analyseer deze kamer:

{context}

Geef 5-7 concrete suggesties voor:
1. Optimale meubel plaatsing
2. Ruimte benutting
3. Looppaden en ergonomie
4. Licht en sfeer
5. Praktische tips

Wees specifiek met posities en afmetingen. Antwoord in het Nederlands."""

        print("\n[AI analyseert je kamer...]")
        response = self._ai_request(prompt, max_tokens=600)
        if response:
            print(f"\n[AI Suggesties]:\n{response}")

    def _ai_analyse(self):
        """AI analyseert de ruimte."""
        print("\n--- AI RUIMTE ANALYSE ---")

        if not self.huidig_project:
            print("[!] Laad eerst een project!")
            return

        if not self.client:
            vrij = self._bereken_vrije_ruimte()
            print(f"\n[Ruimte Analyse]:")
            print(f"  Vrije ruimte: {vrij}%")
            if vrij > 60:
                print("  Status: Veel ruimte beschikbaar")
            elif vrij > 40:
                print("  Status: Goede balans")
            else:
                print("  Status: Ruimte wordt krap")
            return

        context = self._get_room_context()
        prompt = f"""Analyseer deze kamer indeling grondig:

{context}

Geef een analyse met:
1. Sterke punten van de huidige indeling
2. Verbeterpunten
3. Feng Shui / energie flow
4. Functionaliteit score (1-10)
5. Ruimtelijkheid score (1-10)
6. Concrete aanbevelingen

Wees eerlijk maar constructief. Antwoord in het Nederlands."""

        print("\n[AI analyseert...]")
        response = self._ai_request(prompt, max_tokens=700)
        if response:
            print(f"\n[AI Analyse]:\n{response}")
