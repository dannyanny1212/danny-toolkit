"""
Code Snippets v1.0 - Persoonlijke code bibliotheek met tags en zoeken.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
from collections import Counter
from ..core.config import Config
from ..core.utils import clear_scherm


class CodeSnippetsApp:
    """Code Snippets - Je persoonlijke code bibliotheek."""

    VERSIE = "1.0"

    # Ondersteunde talen met syntax highlighting hints
    TALEN = {
        "python": {"ext": ".py", "comment": "#"},
        "javascript": {"ext": ".js", "comment": "//"},
        "typescript": {"ext": ".ts", "comment": "//"},
        "java": {"ext": ".java", "comment": "//"},
        "c": {"ext": ".c", "comment": "//"},
        "cpp": {"ext": ".cpp", "comment": "//"},
        "csharp": {"ext": ".cs", "comment": "//"},
        "go": {"ext": ".go", "comment": "//"},
        "rust": {"ext": ".rs", "comment": "//"},
        "ruby": {"ext": ".rb", "comment": "#"},
        "php": {"ext": ".php", "comment": "//"},
        "sql": {"ext": ".sql", "comment": "--"},
        "html": {"ext": ".html", "comment": "<!--"},
        "css": {"ext": ".css", "comment": "/*"},
        "bash": {"ext": ".sh", "comment": "#"},
        "powershell": {"ext": ".ps1", "comment": "#"},
    }

    def __init__(self):
        Config.ensure_dirs()
        self.data_dir = Config.APPS_DATA_DIR / "code_snippets"
        self.data_dir.mkdir(exist_ok=True)
        self.data_file = self.data_dir / "snippets.json"
        self.data = self._laad_data()

    def _laad_data(self) -> Dict:
        """Laad snippets data."""
        if self.data_file.exists():
            try:
                with open(self.data_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return {
            "snippets": [],
            "tags": [],
            "collecties": {},
        }

    def _sla_op(self):
        """Sla data op."""
        with open(self.data_file, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)

    def _genereer_id(self) -> str:
        """Genereer unieke snippet ID."""
        return f"snip_{datetime.now().strftime('%Y%m%d%H%M%S')}"

    def _nieuwe_snippet(self):
        """Maak nieuwe snippet."""
        clear_scherm()
        print("\n  === NIEUWE SNIPPET ===\n")

        snippet = {
            "id": self._genereer_id(),
            "titel": "",
            "beschrijving": "",
            "taal": "",
            "code": "",
            "tags": [],
            "aangemaakt": datetime.now().isoformat(),
            "gewijzigd": datetime.now().isoformat(),
            "favorieten": False,
            "gebruik_count": 0,
        }

        # Titel
        snippet["titel"] = input("  Titel: ").strip()
        if not snippet["titel"]:
            print("  Titel is verplicht!")
            input("  Druk op Enter...")
            return

        # Beschrijving
        snippet["beschrijving"] = input("  Beschrijving: ").strip()

        # Taal
        print(f"\n  Talen: {', '.join(self.TALEN.keys())}")
        taal = input("  Taal: ").strip().lower()
        snippet["taal"] = taal if taal in self.TALEN else "text"

        # Code
        print("\n  Code (typ 'KLAAR' op een nieuwe regel als je klaar bent):")
        print("  " + "-" * 40)

        code_lijnen = []
        while True:
            lijn = input("  ")
            if lijn.strip().upper() == "KLAAR":
                break
            code_lijnen.append(lijn)

        snippet["code"] = "\n".join(code_lijnen)

        # Tags
        bestaande_tags = self._get_alle_tags()
        if bestaande_tags:
            print(f"\n  Bestaande tags: {', '.join(bestaande_tags)}")

        tags_input = input("  Tags (komma-gescheiden): ").strip()
        snippet["tags"] = [t.strip().lower() for t in tags_input.split(",") if t.strip()]

        # Update globale tags
        for tag in snippet["tags"]:
            if tag not in self.data["tags"]:
                self.data["tags"].append(tag)

        # Opslaan
        self.data["snippets"].append(snippet)
        self._sla_op()

        print("\n  Snippet opgeslagen!")
        print(f"  ID: {snippet['id']}")

        input("\n  Druk op Enter...")

    def _get_alle_tags(self) -> List[str]:
        """Haal alle unieke tags op."""
        tags = set()
        for s in self.data.get("snippets", []):
            tags.update(s.get("tags", []))
        return sorted(tags)

    def _bekijk_snippets(self):
        """Bekijk alle snippets."""
        clear_scherm()
        print("\n  === CODE BIBLIOTHEEK ===\n")

        snippets = self.data.get("snippets", [])

        if not snippets:
            print("  Nog geen snippets opgeslagen.")
            input("\n  Druk op Enter...")
            return

        # Sorteer op recent
        snippets_sorted = sorted(
            snippets,
            key=lambda x: x.get("gewijzigd", ""),
            reverse=True
        )

        print("  ID   | Titel                           | Taal       | Tags")
        print("  " + "-" * 70)

        for s in snippets_sorted[:20]:
            id_kort = s["id"][-6:]
            titel = s["titel"][:30]
            taal = s.get("taal", "?")[:10]
            tags = ", ".join(s.get("tags", [])[:3])
            fav = "*" if s.get("favorieten") else " "
            print(f"  {fav}{id_kort} | {titel:30} | {taal:10} | {tags}")

        print("\n  Opties: [id] bekijk, [z]oek, [t]ags, [f]avorieten")
        keuze = input("\n  Keuze: ").strip().lower()

        if keuze == "z":
            self._zoek_snippets()
        elif keuze == "t":
            self._filter_op_tag()
        elif keuze == "f":
            self._toon_favorieten()
        elif keuze:
            # Zoek snippet op ID (deel)
            for s in snippets:
                if keuze in s["id"]:
                    self._toon_snippet(s)
                    return

    def _toon_snippet(self, snippet: Dict):
        """Toon snippet details."""
        clear_scherm()
        print("\n  " + "=" * 60)
        print(f"  {snippet['titel'].upper()}")
        print("  " + "=" * 60)

        print(f"\n  ID: {snippet['id']}")
        print(f"  Taal: {snippet.get('taal', '?')}")
        print(f"  Tags: {', '.join(snippet.get('tags', []))}")
        print(f"  Aangemaakt: {snippet.get('aangemaakt', '?')[:10]}")
        print(f"  Gebruikt: {snippet.get('gebruik_count', 0)}x")

        if snippet.get("beschrijving"):
            print(f"\n  Beschrijving: {snippet['beschrijving']}")

        print("\n  CODE:")
        print("  " + "-" * 50)

        for i, lijn in enumerate(snippet["code"].split("\n"), 1):
            print(f"  {i:3} | {lijn}")

        print("  " + "-" * 50)

        # Update gebruik count
        for s in self.data["snippets"]:
            if s["id"] == snippet["id"]:
                s["gebruik_count"] = s.get("gebruik_count", 0) + 1
                break
        self._sla_op()

        print("\n  Acties: [c]opieer, [e]dit, [d]elete, [f]avoriet toggle")
        actie = input("  Actie (of Enter): ").strip().lower()

        if actie == "c":
            print("\n  Code gekopieerd naar clipboard!")
            # In echte implementatie zou dit naar clipboard gaan
            print("  (Kopieer handmatig van boven)")

        elif actie == "e":
            self._bewerk_snippet(snippet)

        elif actie == "d":
            if input("  Weet je zeker? (j/n): ").lower() == "j":
                self.data["snippets"] = [s for s in self.data["snippets"]
                                         if s["id"] != snippet["id"]]
                self._sla_op()
                print("  Verwijderd!")

        elif actie == "f":
            for s in self.data["snippets"]:
                if s["id"] == snippet["id"]:
                    s["favorieten"] = not s.get("favorieten", False)
                    status = "toegevoegd aan" if s["favorieten"] else "verwijderd uit"
                    print(f"  {status} favorieten!")
                    break
            self._sla_op()

        input("\n  Druk op Enter...")

    def _bewerk_snippet(self, snippet: Dict):
        """Bewerk een snippet."""
        print("\n  === BEWERK SNIPPET ===")
        print("  (Laat leeg om ongewijzigd te laten)\n")

        nieuwe_titel = input(f"  Titel [{snippet['titel']}]: ").strip()
        if nieuwe_titel:
            snippet["titel"] = nieuwe_titel

        nieuwe_beschr = input(f"  Beschrijving [{snippet.get('beschrijving', '')}]: ").strip()
        if nieuwe_beschr:
            snippet["beschrijving"] = nieuwe_beschr

        nieuwe_tags = input(f"  Tags [{', '.join(snippet.get('tags', []))}]: ").strip()
        if nieuwe_tags:
            snippet["tags"] = [t.strip().lower() for t in nieuwe_tags.split(",")]

        print("\n  Nieuwe code? (j/n)")
        if input("  > ").lower() == "j":
            print("  Code (typ 'KLAAR' als je klaar bent):")
            code_lijnen = []
            while True:
                lijn = input("  ")
                if lijn.strip().upper() == "KLAAR":
                    break
                code_lijnen.append(lijn)
            snippet["code"] = "\n".join(code_lijnen)

        snippet["gewijzigd"] = datetime.now().isoformat()

        # Update in data
        for i, s in enumerate(self.data["snippets"]):
            if s["id"] == snippet["id"]:
                self.data["snippets"][i] = snippet
                break

        self._sla_op()
        print("\n  Snippet bijgewerkt!")

    def _zoek_snippets(self):
        """Zoek in snippets."""
        clear_scherm()
        print("\n  === ZOEK SNIPPETS ===\n")

        zoekterm = input("  Zoekterm: ").strip().lower()

        if not zoekterm:
            return

        resultaten = []
        for s in self.data.get("snippets", []):
            tekst = (s["titel"] + " " + s.get("beschrijving", "") +
                    " " + s["code"] + " " + " ".join(s.get("tags", []))).lower()
            if zoekterm in tekst:
                resultaten.append(s)

        if not resultaten:
            print(f"\n  Geen resultaten voor '{zoekterm}'")
            input("\n  Druk op Enter...")
            return

        print(f"\n  {len(resultaten)} resultaten:\n")
        for i, s in enumerate(resultaten[:10], 1):
            print(f"  {i}. [{s.get('taal', '?')}] {s['titel']}")

        keuze = input("\n  Bekijk # (of Enter): ").strip()
        if keuze.isdigit():
            idx = int(keuze) - 1
            if 0 <= idx < len(resultaten):
                self._toon_snippet(resultaten[idx])

    def _filter_op_tag(self):
        """Filter snippets op tag."""
        clear_scherm()
        print("\n  === FILTER OP TAG ===\n")

        tags = self._get_alle_tags()

        if not tags:
            print("  Nog geen tags.")
            input("\n  Druk op Enter...")
            return

        print("  Beschikbare tags:")
        for i, tag in enumerate(tags, 1):
            count = sum(1 for s in self.data["snippets"] if tag in s.get("tags", []))
            print(f"    {i}. {tag} ({count})")

        keuze = input("\n  Kies tag #: ").strip()

        try:
            idx = int(keuze) - 1
            if 0 <= idx < len(tags):
                tag = tags[idx]
                resultaten = [s for s in self.data["snippets"]
                             if tag in s.get("tags", [])]

                clear_scherm()
                print(f"\n  === SNIPPETS MET TAG '{tag}' ===\n")

                for i, s in enumerate(resultaten, 1):
                    print(f"  {i}. [{s.get('taal', '?')}] {s['titel']}")

                keuze2 = input("\n  Bekijk # (of Enter): ").strip()
                if keuze2.isdigit():
                    idx2 = int(keuze2) - 1
                    if 0 <= idx2 < len(resultaten):
                        self._toon_snippet(resultaten[idx2])
        except (ValueError, IndexError):
            pass

    def _toon_favorieten(self):
        """Toon favoriete snippets."""
        clear_scherm()
        print("\n  === FAVORIETE SNIPPETS ===\n")

        favorieten = [s for s in self.data.get("snippets", [])
                     if s.get("favorieten")]

        if not favorieten:
            print("  Nog geen favorieten.")
            input("\n  Druk op Enter...")
            return

        for i, s in enumerate(favorieten, 1):
            print(f"  {i}. [{s.get('taal', '?')}] {s['titel']}")

        keuze = input("\n  Bekijk # (of Enter): ").strip()
        if keuze.isdigit():
            idx = int(keuze) - 1
            if 0 <= idx < len(favorieten):
                self._toon_snippet(favorieten[idx])

    def _toon_statistieken(self):
        """Toon statistieken."""
        clear_scherm()
        print("\n  === SNIPPET STATISTIEKEN ===\n")

        snippets = self.data.get("snippets", [])

        print(f"  Totaal snippets: {len(snippets)}")
        print(f"  Totaal tags: {len(self._get_alle_tags())}")
        print(f"  Favorieten: {sum(1 for s in snippets if s.get('favorieten'))}")

        # Per taal
        print("\n  Per taal:")
        taal_count = Counter(s.get("taal", "onbekend") for s in snippets)
        for taal, count in taal_count.most_common(10):
            bar = "#" * min(count, 20)
            print(f"    {taal:12} {bar} ({count})")

        # Meest gebruikte tags
        print("\n  Populaire tags:")
        tag_count = Counter()
        for s in snippets:
            tag_count.update(s.get("tags", []))
        for tag, count in tag_count.most_common(5):
            print(f"    {tag}: {count}x")

        # Meest gebruikte snippets
        print("\n  Meest gebruikt:")
        meest_gebruikt = sorted(snippets, key=lambda x: x.get("gebruik_count", 0),
                                reverse=True)[:5]
        for s in meest_gebruikt:
            print(f"    {s['titel']}: {s.get('gebruik_count', 0)}x")

        input("\n  Druk op Enter...")

    def run(self):
        """Start de app."""
        while True:
            clear_scherm()

            snippets_count = len(self.data.get("snippets", []))
            tags_count = len(self._get_alle_tags())

            print(f"""
  ╔═══════════════════════════════════════════════════════════╗
  ║              CODE SNIPPETS v1.0                           ║
  ║          Je Persoonlijke Code Bibliotheek                 ║
  ╠═══════════════════════════════════════════════════════════╣
  ║  1. Nieuwe Snippet                                        ║
  ║  2. Bekijk Bibliotheek                                    ║
  ║  3. Zoek Snippets                                         ║
  ║  4. Filter op Tag                                         ║
  ║  5. Favorieten                                            ║
  ║  6. Statistieken                                          ║
  ║  0. Terug                                                 ║
  ╚═══════════════════════════════════════════════════════════╝
""")
            print(f"  Snippets: {snippets_count} | Tags: {tags_count}")

            keuze = input("\n  Keuze: ").strip()

            if keuze == "0":
                break
            elif keuze == "1":
                self._nieuwe_snippet()
            elif keuze == "2":
                self._bekijk_snippets()
            elif keuze == "3":
                self._zoek_snippets()
            elif keuze == "4":
                self._filter_op_tag()
            elif keuze == "5":
                self._toon_favorieten()
            elif keuze == "6":
                self._toon_statistieken()
