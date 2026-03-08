"""
Boodschappenlijst App v2.0 - Complete winkelassistent.

Features:
- Meerdere lijsten voor verschillende winkels
- Budget & prijzen tracking
- Recepten systeem
- Voorraad beheer
- Aankoopgeschiedenis & statistieken
- Prioriteit systeem
- Slimme suggesties
- Export/delen functionaliteit
- Sjablonen voor wekelijkse boodschappen
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from danny_toolkit.core.config import Config
from danny_toolkit.core.utils import clear_scherm, kleur, Kleur, succes, fout, waarschuwing, info

try:
    import danny_toolkit.brain.unified_memory
    HAS_UNIFIED_MEMORY = True
except ImportError:
    HAS_UNIFIED_MEMORY = False

try:
    import re
    HAS_RE = True
except ImportError:
    HAS_RE = False


logger = logging.getLogger(__name__)


class BoodschappenlijstApp:
    """Uitgebreide boodschappenlijst applicatie v2.0."""

    VERSIE = "2.0"

    CATEGORIEEN = {
        "groenten": {"naam": "Groenten & Fruit", "emoji": "🥬", "volgorde": 1},
        "zuivel": {"naam": "Zuivel", "emoji": "🥛", "volgorde": 2},
        "vlees": {"naam": "Vlees & Vis", "emoji": "🥩", "volgorde": 3},
        "brood": {"naam": "Brood & Bakkerij", "emoji": "🍞", "volgorde": 4},
        "dranken": {"naam": "Dranken", "emoji": "🥤", "volgorde": 5},
        "pasta": {"naam": "Pasta & Rijst", "emoji": "🍝", "volgorde": 6},
        "conserven": {"naam": "Conserven & Sauzen", "emoji": "🥫", "volgorde": 7},
        "snacks": {"naam": "Snacks & Snoep", "emoji": "🍪", "volgorde": 8},
        "diepvries": {"naam": "Diepvries", "emoji": "🧊", "volgorde": 9},
        "huishouden": {"naam": "Huishouden", "emoji": "🧹", "volgorde": 10},
        "verzorging": {"naam": "Verzorging", "emoji": "🧴", "volgorde": 11},
        "dieren": {"naam": "Dierbenodigdheden", "emoji": "🐾", "volgorde": 12},
        "overig": {"naam": "Overig", "emoji": "📦", "volgorde": 13}
    }

    PRIORITEITEN = {
        "hoog": {"naam": "Hoog", "kleur": Kleur.ROOD, "symbool": "!!!"},
        "normaal": {"naam": "Normaal", "kleur": Kleur.WIT, "symbool": ""},
        "laag": {"naam": "Laag", "kleur": "grijs", "symbool": "..."}
    }

    STANDAARD_PRODUCTEN = {
        "groenten": ["Appels", "Bananen", "Tomaten", "Komkommer", "Sla",
                     "Paprika", "Uien", "Knoflook", "Aardappelen", "Wortels"],
        "zuivel": ["Melk", "Boter", "Kaas", "Yoghurt", "Eieren", "Room"],
        "vlees": ["Kipfilet", "Gehakt", "Spekjes", "Zalm", "Garnalen"],
        "brood": ["Brood", "Croissants", "Beschuit", "Crackers"],
        "dranken": ["Water", "Sinaasappelsap", "Cola", "Bier", "Wijn", "Koffie", "Thee"],
        "pasta": ["Spaghetti", "Penne", "Rijst", "Noodles", "Couscous"],
        "conserven": ["Tomatensaus", "Bonen", "Mais", "Olijfolie", "Azijn"],
        "snacks": ["Chips", "Nootjes", "Chocolade", "Koekjes", "Popcorn"],
        "diepvries": ["Pizza", "Ijsjes", "Groenten mix", "Friet"],
        "huishouden": ["Afwasmiddel", "Schoonmaakspray", "Toiletpapier", "Vuilniszakken"],
        "verzorging": ["Shampoo", "Tandpasta", "Zeep", "Deodorant"],
        "dieren": ["Hondenvoer", "Kattenvoer", "Kattenbakkorrels", "Snacks hond",
                   "Snacks kat", "Vogelzaad", "Visvoer", "Knaagdiervoer"],
        "overig": ["Batterijen", "Lampen", "Tape"]
    }

    STANDAARD_RECEPTEN = {
        "Spaghetti Bolognese": {
            "ingredienten": [
                {"naam": "Spaghetti", "hoeveelheid": "500g", "categorie": "pasta"},
                {"naam": "Gehakt", "hoeveelheid": "500g", "categorie": "vlees"},
                {"naam": "Tomatensaus", "hoeveelheid": "1 pot", "categorie": "conserven"},
                {"naam": "Uien", "hoeveelheid": "2 stuks", "categorie": "groenten"},
                {"naam": "Knoflook", "hoeveelheid": "3 teentjes", "categorie": "groenten"},
                {"naam": "Kaas", "hoeveelheid": "100g", "categorie": "zuivel"}
            ],
            "personen": 4
        },
        "Pannenkoeken": {
            "ingredienten": [
                {"naam": "Bloem", "hoeveelheid": "250g", "categorie": "overig"},
                {"naam": "Melk", "hoeveelheid": "500ml", "categorie": "zuivel"},
                {"naam": "Eieren", "hoeveelheid": "3 stuks", "categorie": "zuivel"},
                {"naam": "Boter", "hoeveelheid": "50g", "categorie": "zuivel"}
            ],
            "personen": 4
        },
        "Salade": {
            "ingredienten": [
                {"naam": "Sla", "hoeveelheid": "1 krop", "categorie": "groenten"},
                {"naam": "Tomaten", "hoeveelheid": "4 stuks", "categorie": "groenten"},
                {"naam": "Komkommer", "hoeveelheid": "1 stuk", "categorie": "groenten"},
                {"naam": "Olijfolie", "hoeveelheid": "2 el", "categorie": "conserven"},
                {"naam": "Kaas", "hoeveelheid": "50g", "categorie": "zuivel"}
            ],
            "personen": 2
        }
    }

    def __init__(self) -> None:
        """Init  ."""
        Config.ensure_dirs()
        self.bestand = Config.APPS_DATA_DIR / "boodschappenlijst_v2.json"
        self.export_dir = Config.APPS_DATA_DIR / "exports"
        self.export_dir.mkdir(exist_ok=True)
        self.data = self._laad_data()
        self._migreer_data()
        self.huidige_lijst = "standaard"

    def _laad_data(self) -> dict:
        """Laadt de data uit bestand."""
        if self.bestand.exists():
            try:
                with open(self.bestand, "r", encoding="utf-8") as f:
                    return json.load(f)
            except json.JSONDecodeError:
                waarschuwing("Corrupt databestand, nieuwe data aangemaakt.")
        return self._maak_lege_data()

    def _maak_lege_data(self) -> dict:
        """Maakt een lege datastructuur."""
        return {
            "versie": self.VERSIE,
            "lijsten": {
                "standaard": {
                    "naam": "Mijn Boodschappen",
                    "winkel": "Algemeen",
                    "items": [],
                    "aangemaakt": datetime.now().isoformat()
                }
            },
            "favorieten": [],
            "recepten": dict(self.STANDAARD_RECEPTEN),
            "voorraad": [],
            "geschiedenis": [],
            "sjablonen": {
                "weekboodschappen": {
                    "naam": "Wekelijkse Boodschappen",
                    "items": [
                        {"naam": "Melk", "categorie": "zuivel"},
                        {"naam": "Brood", "categorie": "brood"},
                        {"naam": "Eieren", "categorie": "zuivel"},
                        {"naam": "Kaas", "categorie": "zuivel"},
                        {"naam": "Boter", "categorie": "zuivel"}
                    ]
                }
            },
            "statistieken": {
                "totaal_items_gekocht": 0,
                "totaal_uitgegeven": 0.0,
                "meest_gekocht": {},
                "uitgaven_per_maand": {}
            },
            "instellingen": {
                "budget_limiet": 0.0,
                "toon_prijzen": True,
                "sorteer_op_categorie": True,
                "auto_suggesties": True
            }
        }

    def _migreer_data(self) -> None:
        """Migreert oude data naar nieuwe structuur."""
        gewijzigd = False

        # Check versie
        if "versie" not in self.data:
            self.data["versie"] = self.VERSIE
            gewijzigd = True

        # Migreer oude items naar lijsten structuur
        if "items" in self.data and "lijsten" not in self.data:
            oude_items = self.data.pop("items")
            self.data["lijsten"] = {
                "standaard": {
                    "naam": "Mijn Boodschappen",
                    "winkel": "Algemeen",
                    "items": oude_items,
                    "aangemaakt": datetime.now().isoformat()
                }
            }
            gewijzigd = True

        # Voeg ontbrekende velden toe
        defaults = self._maak_lege_data()
        for key in defaults:
            if key not in self.data:
                self.data[key] = defaults[key]
                gewijzigd = True

        if gewijzigd:
            self._sla_op(stil=True)

    def _sla_op(self, stil=False) -> None:
        """Slaat de data op naar bestand."""
        self.data["versie"] = self.VERSIE
        with open(self.bestand, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)
        if not stil:
            succes("Opgeslagen!")

    def _log_memory_event(self, event_type, data) -> None:
        """Log event naar Unified Memory."""
        try:
            if not hasattr(self, "_memory"):
                pass  # import moved to top-level
                self._memory = UnifiedMemory()
            self._memory.store_event(
                app="boodschappenlijst",
                event_type=event_type,
                data=data
            )
        except Exception as e:
            logger.debug("Memory event error: %s", e)

    def _get_huidige_lijst(self) -> dict:
        """Haalt de huidige actieve lijst op."""
        return self.data["lijsten"].get(self.huidige_lijst,
            self.data["lijsten"]["standaard"])

    def _get_items(self) -> list:
        """Haalt items van huidige lijst."""
        return self._get_huidige_lijst().get("items", [])

    # ==================== WEERGAVE ====================

    def _toon_header(self, titel: str) -> None:
        """Toont een mooie header."""
        print()
        print(kleur("╔" + "═" * 50 + "╗", "cyan"))
        print(kleur("║", "cyan") + f" {titel:^48} " + kleur("║", "cyan"))
        print(kleur("╚" + "═" * 50 + "╝", "cyan"))

    def _toon_lijst(self, compact=False) -> None:
        """Toont de huidige lijst, gegroepeerd per categorie."""
        lijst = self._get_huidige_lijst()
        items = lijst.get("items", [])

        self._toon_header(f"📋 {lijst['naam']} ({lijst['winkel']})")

        if not items:
            print(kleur("\n  De boodschappenlijst is leeg.", Kleur.GEEL))
            return

        # Groepeer per categorie
        per_categorie = {cat: [] for cat in self.CATEGORIEEN}
        for i, item in enumerate(items):
            cat = item.get("categorie", "overig")
            if cat not in per_categorie:
                cat = "overig"
            per_categorie[cat].append((i, item))

        # Sorteer categorieën op volgorde
        gesorteerd = sorted(self.CATEGORIEEN.items(),
                           key=lambda x: x[1]["volgorde"])

        totaal_prijs = 0.0
        item_nr = 1

        for cat_key, cat_info in gesorteerd:
            cat_items = per_categorie[cat_key]
            if cat_items:
                emoji = cat_info["emoji"]
                naam = cat_info["naam"]
                print(kleur(f"\n  {emoji} {naam.upper()}", Kleur.GEEL))

                for idx, item in cat_items:
                    # Status
                    if item.get("afgevinkt", False):
                        status = kleur("[✓]", Kleur.GROEN)
                        naam_kleur = "grijs"
                    else:
                        status = "[ ]"
                        naam_kleur = Kleur.WIT

                    # Prioriteit
                    prio = item.get("prioriteit", "normaal")
                    prio_info = self.PRIORITEITEN.get(prio, self.PRIORITEITEN["normaal"])
                    prio_sym = prio_info["symbool"]

                    # Naam en hoeveelheid
                    naam = item["naam"]
                    hoeveelheid = item.get("hoeveelheid", "")
                    if hoeveelheid:
                        tekst = f"{hoeveelheid} {naam}"
                    else:
                        tekst = naam

                    # Prijs
                    prijs = item.get("prijs", 0)
                    if prijs > 0:
                        prijs_str = kleur(f" €{prijs:.2f}", Kleur.GROEN)
                        if not item.get("afgevinkt", False):
                            totaal_prijs += prijs
                    else:
                        prijs_str = ""

                    # Notitie indicator
                    notitie = " 📝" if item.get("notitie") else ""

                    if prio == "hoog":
                        tekst = kleur(tekst, Kleur.ROOD)
                    elif item.get("afgevinkt"):
                        tekst = kleur(tekst, "grijs")

                    print(f"    {item_nr:2}. {status} {tekst}{prijs_str}{notitie} {prio_sym}")
                    item_nr += 1

        # Statistieken
        totaal = len(items)
        afgevinkt = sum(1 for i in items if i.get("afgevinkt", False))

        print(kleur("\n  " + "─" * 48, "cyan"))

        # Budget info
        budget = self.data["instellingen"].get("budget_limiet", 0)
        if totaal_prijs > 0:
            if budget > 0:
                rest = budget - totaal_prijs
                if rest < 0:
                    budget_str = kleur(f" | Budget: €{rest:.2f}", Kleur.ROOD)
                else:
                    budget_str = kleur(f" | Budget over: €{rest:.2f}", Kleur.GROEN)
            else:
                budget_str = ""
            print(f"  💰 Totaal: €{totaal_prijs:.2f}{budget_str}")

        print(f"  📊 Items: {totaal} | Afgevinkt: {afgevinkt}/{totaal}")

    def _toon_menu(self) -> None:
        """Toont het hoofdmenu."""
        lijst = self._get_huidige_lijst()
        items_count = len(lijst.get("items", []))
        afgevinkt = sum(1 for i in lijst.get("items", [])
                       if i.get("afgevinkt", False))

        print()
        print(kleur("┌" + "─" * 40 + "┐", "cyan"))
        print(kleur("│", "cyan") + kleur("     🛒 BOODSCHAPPENLIJST v2.0", Kleur.GEEL) +
              kleur("        │", "cyan"))
        print(kleur("│", "cyan") +
              f"     Lijst: {lijst['naam'][:20]:<20}" + kleur("│", "cyan"))
        print(kleur("│", "cyan") +
              f"     Items: {items_count} | Klaar: {afgevinkt:<13}" + kleur("│", "cyan"))
        print(kleur("├" + "─" * 40 + "┤", "cyan"))

        menu_items = [
            ("1", "Toon lijst"),
            ("2", "Voeg item toe"),
            ("3", "Snel toevoegen (favoriet)"),
            ("4", "Afvinken/onafvinken"),
            ("5", "Bewerk item"),
            ("6", "Verwijder item(s)"),
            ("", ""),
            ("r", "Recepten"),
            ("v", "Voorraad beheer"),
            ("s", "Sjablonen"),
            ("", ""),
            ("l", "Lijsten beheren"),
            ("f", "Favorieten beheren"),
            ("i", "Instellingen"),
            ("t", "Statistieken"),
            ("e", "Exporteren"),
            ("", ""),
            ("8", "Opslaan"),
            ("0", "Terug naar hoofdmenu")
        ]

        for key, label in menu_items:
            if key == "":
                print(kleur("│", "cyan") + " " * 40 + kleur("│", "cyan"))
            else:
                print(kleur("│", "cyan") + f"  {kleur(key, 'groen'):>5}. {label:<32}" +
                      kleur("│", "cyan"))

        print(kleur("└" + "─" * 40 + "┘", "cyan"))

    # ==================== ITEMS BEHEREN ====================

    def _kies_categorie(self) -> str:
        """Laat gebruiker een categorie kiezen."""
        print(kleur("\n  Kies een categorie:", Kleur.GEEL))

        cats = sorted(self.CATEGORIEEN.items(), key=lambda x: x[1]["volgorde"])
        for i, (key, cat) in enumerate(cats, 1):
            print(f"    {i:2}. {cat['emoji']} {cat['naam']}")

        keuze = input(kleur("\n  Categorie (1-13): ", "cyan")).strip()
        try:
            idx = int(keuze) - 1
            if 0 <= idx < len(cats):
                return cats[idx][0]
        except ValueError:
            logger.debug("Suppressed error")
        return "overig"

    def _voeg_toe(self) -> None:
        """Voegt een item toe met alle opties."""
        self._toon_header("➕ Item Toevoegen")

        # Suggesties tonen
        if self.data["instellingen"].get("auto_suggesties", True):
            self._toon_suggesties()

        naam = input(kleur("\n  Wat wil je toevoegen? ", "cyan")).strip()
        if not naam:
            fout("Geen item ingevoerd.")
            return

        hoeveelheid = input(kleur("  Hoeveelheid (optioneel): ", "cyan")).strip()
        categorie = self._kies_categorie()

        # Prijs
        prijs_str = input(kleur("  Prijs in euro (optioneel): ", "cyan")).strip()
        try:
            prijs = float(prijs_str.replace(",", ".")) if prijs_str else 0
        except ValueError:
            prijs = 0

        # Prioriteit
        print(kleur("\n  Prioriteit:", Kleur.GEEL))
        print("    1. Normaal")
        print("    2. Hoog (urgent)")
        print("    3. Laag")
        prio_keuze = input(kleur("  Keuze (1-3): ", "cyan")).strip()
        prioriteit = {"1": "normaal", "2": "hoog", "3": "laag"}.get(prio_keuze, "normaal")

        # Notitie
        notitie = input(kleur("  Notitie (optioneel): ", "cyan")).strip()

        item = {
            "naam": naam,
            "hoeveelheid": hoeveelheid,
            "categorie": categorie,
            "prijs": prijs,
            "prioriteit": prioriteit,
            "notitie": notitie,
            "afgevinkt": False,
            "toegevoegd": datetime.now().isoformat()
        }

        self._get_huidige_lijst()["items"].append(item)
        self._log_memory_event("item_added", {
            "item": naam, "categorie": categorie
        })
        succes(f"'{naam}' toegevoegd!")

        # Vraag of het een favoriet moet worden
        if naam.lower() not in [f["naam"].lower() for f in self.data["favorieten"]]:
            fav = input(kleur("  Toevoegen aan favorieten? (j/n): ", "cyan")).lower()
            if fav == "j":
                self.data["favorieten"].append({
                    "naam": naam,
                    "categorie": categorie,
                    "hoeveelheid": hoeveelheid
                })
                succes(f"'{naam}' toegevoegd aan favorieten!")

    def _toon_suggesties(self) -> None:
        """Toont slimme suggesties gebaseerd op geschiedenis."""
        # Meest gekochte items
        meest_gekocht = self.data["statistieken"].get("meest_gekocht", {})
        if meest_gekocht:
            top_items = sorted(meest_gekocht.items(),
                             key=lambda x: x[1], reverse=True)[:5]
            if top_items:
                print(kleur("\n  💡 Suggesties (vaak gekocht):", Kleur.GEEL))
                for naam, aantal in top_items:
                    print(f"      • {naam} ({aantal}x)")

        # Items uit voorraad die op zijn
        voorraad_laag = [v for v in self.data["voorraad"]
                        if v.get("aantal", 0) <= 1]
        if voorraad_laag:
            print(kleur("\n  ⚠️  Bijna op (uit voorraad):", Kleur.GEEL))
            for item in voorraad_laag[:3]:
                print(f"      • {item['naam']}")

    def _voeg_favoriet_toe(self) -> None:
        """Voegt snel een favoriet toe aan de lijst."""
        favorieten = self.data["favorieten"]

        if not favorieten:
            waarschuwing("Je hebt nog geen favorieten.")
            info("Voeg eerst items toe en markeer ze als favoriet!")
            return

        self._toon_header("⭐ Snel Toevoegen")
        print()
        for i, fav in enumerate(favorieten, 1):
            cat_info = self.CATEGORIEEN.get(fav.get("categorie", "overig"),
                                            self.CATEGORIEEN["overig"])
            print(f"    {i:2}. {cat_info['emoji']} {fav['naam']}")
        print(kleur("\n     0. Annuleren", "grijs"))
        print(kleur("     a. Alle favorieten toevoegen", Kleur.GEEL))

        keuze = input(kleur("\n  Welke toevoegen? ", "cyan")).strip().lower()

        if keuze == "0":
            return
        elif keuze == "a":
            for fav in favorieten:
                item = {
                    "naam": fav["naam"],
                    "hoeveelheid": fav.get("hoeveelheid", ""),
                    "categorie": fav.get("categorie", "overig"),
                    "prijs": 0,
                    "prioriteit": "normaal",
                    "notitie": "",
                    "afgevinkt": False,
                    "toegevoegd": datetime.now().isoformat()
                }
                self._get_huidige_lijst()["items"].append(item)
            succes(f"Alle {len(favorieten)} favorieten toegevoegd!")
        else:
            try:
                idx = int(keuze) - 1
                if 0 <= idx < len(favorieten):
                    fav = favorieten[idx]
                    hoeveelheid = input(
                        kleur(f"  Hoeveelheid voor {fav['naam']} (optioneel): ", "cyan")
                    ).strip()

                    item = {
                        "naam": fav["naam"],
                        "hoeveelheid": hoeveelheid or fav.get("hoeveelheid", ""),
                        "categorie": fav.get("categorie", "overig"),
                        "prijs": 0,
                        "prioriteit": "normaal",
                        "notitie": "",
                        "afgevinkt": False,
                        "toegevoegd": datetime.now().isoformat()
                    }
                    self._get_huidige_lijst()["items"].append(item)
                    succes(f"'{fav['naam']}' toegevoegd!")
                else:
                    fout("Ongeldige keuze.")
            except ValueError:
                fout("Voer een nummer in.")

    def _afvinken(self) -> None:
        """Vinkt items af of haalt vinkjes weg."""
        items = self._get_items()

        if not items:
            waarschuwing("De lijst is leeg.")
            return

        self._toon_lijst()
        print(kleur("\n  Opties:", Kleur.GEEL))
        print("    [nummer]  = Afvinken/onafvinken")
        print("    [n1,n2]   = Meerdere afvinken (bijv: 1,3,5)")
        print("    a         = Alles afvinken")
        print("    o         = Alles onafvinken")

        keuze = input(kleur("\n  Keuze: ", "cyan")).strip().lower()

        if keuze == "a":
            for item in items:
                item["afgevinkt"] = True
            succes("Alle items afgevinkt!")
        elif keuze == "o":
            for item in items:
                item["afgevinkt"] = False
            succes("Alle items onafgevinkt!")
        elif "," in keuze:
            nummers = [n.strip() for n in keuze.split(",")]
            for num in nummers:
                try:
                    idx = int(num) - 1
                    if 0 <= idx < len(items):
                        items[idx]["afgevinkt"] = not items[idx]["afgevinkt"]
                except ValueError:
                    logger.debug("Suppressed error")
            succes("Items bijgewerkt!")
        else:
            try:
                idx = int(keuze) - 1
                if 0 <= idx < len(items):
                    items[idx]["afgevinkt"] = not items[idx]["afgevinkt"]
                    status = "afgevinkt" if items[idx]["afgevinkt"] else "niet afgevinkt"
                    self._log_memory_event("item_toggled", {
                        "item": items[idx]["naam"]
                    })
                    succes(f"'{items[idx]['naam']}' is nu {status}!")
                else:
                    fout("Ongeldig nummer.")
            except ValueError:
                fout("Voer een nummer in.")

    def _bewerk_item(self) -> None:
        """Bewerkt een bestaand item."""
        items = self._get_items()

        if not items:
            waarschuwing("De lijst is leeg.")
            return

        self._toon_lijst()
        keuze = input(kleur("\n  Welk item bewerken? ", "cyan")).strip()

        try:
            idx = int(keuze) - 1
            if 0 <= idx < len(items):
                item = items[idx]
                self._toon_header(f"✏️ Bewerk: {item['naam']}")

                print(kleur("\n  Laat leeg om huidige waarde te behouden.", "grijs"))

                naam = input(f"  Naam [{item['naam']}]: ").strip()
                if naam:
                    item["naam"] = naam

                hoeveelheid = input(
                    f"  Hoeveelheid [{item.get('hoeveelheid', '')}]: "
                ).strip()
                if hoeveelheid:
                    item["hoeveelheid"] = hoeveelheid

                prijs_str = input(f"  Prijs [{item.get('prijs', 0)}]: ").strip()
                if prijs_str:
                    try:
                        item["prijs"] = float(prijs_str.replace(",", "."))
                    except ValueError:
                        logger.debug("Suppressed error")

                notitie = input(f"  Notitie [{item.get('notitie', '')}]: ").strip()
                if notitie:
                    item["notitie"] = notitie

                succes("Item bijgewerkt!")
            else:
                fout("Ongeldig nummer.")
        except ValueError:
            fout("Voer een nummer in.")

    def _verwijder(self) -> None:
        """Verwijdert items."""
        items = self._get_items()

        if not items:
            waarschuwing("De lijst is leeg.")
            return

        self._toon_lijst()
        print(kleur("\n  Opties:", Kleur.GEEL))
        print("    [nummer]  = Verwijder specifiek item")
        print("    a         = Verwijder alle afgevinkte items")
        print("    w         = Wis hele lijst")

        keuze = input(kleur("\n  Keuze: ", "cyan")).strip().lower()

        if keuze == "a":
            # Voeg afgevinkte items toe aan geschiedenis
            afgevinkte = [i for i in items if i.get("afgevinkt", False)]
            self._voeg_toe_aan_geschiedenis(afgevinkte)

            oude_len = len(items)
            self._get_huidige_lijst()["items"] = [
                i for i in items if not i.get("afgevinkt", False)
            ]
            verwijderd = oude_len - len(self._get_items())
            succes(f"{verwijderd} afgevinkte item(s) verwijderd!")

        elif keuze == "w":
            bevestig = input(kleur(
                "  Weet je zeker dat je alles wilt wissen? (j/n): ", Kleur.ROOD
            )).lower()
            if bevestig == "j":
                self._voeg_toe_aan_geschiedenis(items)
                self._get_huidige_lijst()["items"] = []
                succes("Lijst gewist!")
            else:
                info("Actie geannuleerd.")
        else:
            try:
                idx = int(keuze) - 1
                if 0 <= idx < len(items):
                    verwijderd = items.pop(idx)
                    succes(f"'{verwijderd['naam']}' verwijderd!")
                else:
                    fout("Ongeldig nummer.")
            except ValueError:
                fout("Ongeldige invoer.")

    def _voeg_toe_aan_geschiedenis(self, items: list) -> None:
        """Voegt items toe aan aankoopgeschiedenis."""
        if not items:
            return

        datum = datetime.now().isoformat()
        totaal_prijs = sum(i.get("prijs", 0) for i in items)

        # Update statistieken
        stats = self.data["statistieken"]
        stats["totaal_items_gekocht"] += len(items)
        stats["totaal_uitgegeven"] += totaal_prijs

        # Meest gekocht bijwerken
        for item in items:
            naam = item["naam"]
            stats["meest_gekocht"][naam] = stats["meest_gekocht"].get(naam, 0) + 1

        # Maandelijkse uitgaven
        maand = datetime.now().strftime("%Y-%m")
        stats["uitgaven_per_maand"][maand] = (
            stats["uitgaven_per_maand"].get(maand, 0) + totaal_prijs
        )

        # Toevoegen aan geschiedenis
        self.data["geschiedenis"].append({
            "datum": datum,
            "items": [{"naam": i["naam"], "prijs": i.get("prijs", 0)} for i in items],
            "totaal": totaal_prijs
        })

        # Houd geschiedenis beperkt (laatste 50)
        if len(self.data["geschiedenis"]) > 50:
            self.data["geschiedenis"] = self.data["geschiedenis"][-50:]

    # ==================== RECEPTEN ====================

    def _recepten_menu(self) -> None:
        """Toont het recepten menu."""
        while True:
            self._toon_header("🍳 Recepten")

            recepten = self.data["recepten"]
            print()
            for i, (naam, recept) in enumerate(recepten.items(), 1):
                personen = recept.get("personen", "?")
                aantal_ing = len(recept.get("ingredienten", []))
                print(f"    {i:2}. {naam} ({personen} pers, {aantal_ing} ingrediënten)")

            print(kleur("\n  Opties:", Kleur.GEEL))
            print("    [nummer] = Ingrediënten toevoegen aan lijst")
            print("    n        = Nieuw recept maken")
            print("    v        = Recept verwijderen")
            print("    s        = Suggesties (op basis van je lijst)")
            print("    0        = Terug")

            keuze = input(kleur("\n  Keuze: ", "cyan")).strip().lower()

            if keuze == "0":
                break
            elif keuze == "n":
                self._maak_recept()
            elif keuze == "v":
                self._verwijder_recept()
            elif keuze == "s":
                self._suggereer_recepten()
            else:
                try:
                    idx = int(keuze) - 1
                    recept_namen = list(recepten.keys())
                    if 0 <= idx < len(recept_namen):
                        self._voeg_recept_toe_aan_lijst(recept_namen[idx])
                    else:
                        fout("Ongeldig nummer.")
                except ValueError:
                    fout("Voer een nummer in.")

            input(kleur("\n  Druk op Enter om verder te gaan...", "grijs"))

    def _voeg_recept_toe_aan_lijst(self, recept_naam: str) -> None:
        """Voegt ingrediënten van een recept toe aan de boodschappenlijst."""
        recept = self.data["recepten"].get(recept_naam)
        if not recept:
            fout("Recept niet gevonden.")
            return

        print(kleur(f"\n  📋 {recept_naam}", Kleur.GEEL))
        print(f"     Voor {recept.get('personen', '?')} personen")

        personen = input(kleur(
            f"\n  Voor hoeveel personen? [{recept.get('personen', 4)}]: ", "cyan"
        )).strip()

        try:
            gewenst = int(personen) if personen else recept.get("personen", 4)
            factor = gewenst / recept.get("personen", 4)
        except ValueError:
            factor = 1

        toegevoegd = 0
        for ing in recept.get("ingredienten", []):
            # Pas hoeveelheid aan
            hoeveelheid = ing.get("hoeveelheid", "")
            # Simpele vermenigvuldiging voor getallen in hoeveelheid
            if factor != 1 and hoeveelheid:
                pass  # import moved to top-level
                match = re.match(r"(\d+)", hoeveelheid)
                if match:
                    getal = int(match.group(1))
                    nieuw_getal = int(getal * factor)
                    hoeveelheid = re.sub(r"\d+", str(nieuw_getal), hoeveelheid, count=1)

            item = {
                "naam": ing["naam"],
                "hoeveelheid": hoeveelheid,
                "categorie": ing.get("categorie", "overig"),
                "prijs": 0,
                "prioriteit": "normaal",
                "notitie": f"Voor: {recept_naam}",
                "afgevinkt": False,
                "toegevoegd": datetime.now().isoformat()
            }
            self._get_huidige_lijst()["items"].append(item)
            toegevoegd += 1

        succes(f"{toegevoegd} ingrediënten toegevoegd voor {recept_naam}!")

    def _maak_recept(self) -> None:
        """Maakt een nieuw recept aan."""
        self._toon_header("📝 Nieuw Recept")

        naam = input(kleur("\n  Naam van het recept: ", "cyan")).strip()
        if not naam:
            fout("Geen naam ingevoerd.")
            return

        personen_str = input(kleur("  Voor hoeveel personen? ", "cyan")).strip()
        try:
            personen = int(personen_str) if personen_str else 4
        except ValueError:
            personen = 4

        ingredienten = []
        print(kleur("\n  Voeg ingrediënten toe (leeg = klaar):", Kleur.GEEL))

        while True:
            ing_naam = input(kleur("    Ingrediënt: ", "cyan")).strip()
            if not ing_naam:
                break

            ing_hoev = input(kleur("    Hoeveelheid: ", "cyan")).strip()
            ing_cat = self._kies_categorie()

            ingredienten.append({
                "naam": ing_naam,
                "hoeveelheid": ing_hoev,
                "categorie": ing_cat
            })
            succes(f"    '{ing_naam}' toegevoegd!")

        if ingredienten:
            self.data["recepten"][naam] = {
                "ingredienten": ingredienten,
                "personen": personen
            }
            succes(f"Recept '{naam}' opgeslagen met {len(ingredienten)} ingrediënten!")
        else:
            waarschuwing("Geen ingrediënten toegevoegd, recept niet opgeslagen.")

    def _verwijder_recept(self) -> None:
        """Verwijdert een recept."""
        recepten = list(self.data["recepten"].keys())
        if not recepten:
            waarschuwing("Geen recepten om te verwijderen.")
            return

        print(kleur("\n  Welk recept verwijderen?", Kleur.GEEL))
        for i, naam in enumerate(recepten, 1):
            print(f"    {i}. {naam}")

        keuze = input(kleur("\n  Nummer: ", "cyan")).strip()
        try:
            idx = int(keuze) - 1
            if 0 <= idx < len(recepten):
                naam = recepten[idx]
                bevestig = input(kleur(
                    f"  Weet je zeker dat je '{naam}' wilt verwijderen? (j/n): ", Kleur.ROOD
                )).lower()
                if bevestig == "j":
                    del self.data["recepten"][naam]
                    succes(f"Recept '{naam}' verwijderd!")
            else:
                fout("Ongeldig nummer.")
        except ValueError:
            fout("Voer een nummer in.")

    def _suggereer_recepten(self) -> None:
        """Suggereert recepten op basis van items in de boodschappenlijst."""
        self._toon_header("💡 Recept Suggesties")

        items = self._get_items()
        if not items:
            waarschuwing("Je boodschappenlijst is leeg. Voeg eerst items toe!")
            return

        # Verzamel alle item namen (lowercase voor vergelijking)
        lijst_items = set()
        for item in items:
            lijst_items.add(item["naam"].lower())

        recepten = self.data["recepten"]
        suggesties = []

        for recept_naam, recept in recepten.items():
            ingredienten = recept.get("ingredienten", [])
            if not ingredienten:
                continue

            # Tel hoeveel ingrediënten al op de lijst staan
            gevonden = 0
            ontbrekend = []

            for ing in ingredienten:
                ing_naam = ing["naam"].lower()
                if any(ing_naam in item or item in ing_naam
                       for item in lijst_items):
                    gevonden += 1
                else:
                    ontbrekend.append(ing["naam"])

            totaal = len(ingredienten)
            percentage = (gevonden / totaal) * 100 if totaal > 0 else 0

            if gevonden > 0:
                suggesties.append({
                    "naam": recept_naam,
                    "gevonden": gevonden,
                    "totaal": totaal,
                    "percentage": percentage,
                    "ontbrekend": ontbrekend,
                    "personen": recept.get("personen", 4)
                })

        # Sorteer op percentage (hoogste eerst)
        suggesties.sort(key=lambda x: x["percentage"], reverse=True)

        if not suggesties:
            info("Geen recepten gevonden die passen bij je huidige items.")
            print(kleur("\n  Tip: Voeg meer items toe of maak nieuwe recepten!", "grijs"))
            return

        print(kleur("\n  Recepten die je kunt maken met je huidige items:", Kleur.GEEL))
        print()

        for i, sug in enumerate(suggesties[:5], 1):
            # Kleur gebaseerd op completeness
            if sug["percentage"] >= 80:
                status_kleur = Kleur.GROEN
                status = "✓ Bijna compleet!"
            elif sug["percentage"] >= 50:
                status_kleur = Kleur.GEEL
                status = "◐ Goed op weg"
            else:
                status_kleur = Kleur.WIT
                status = "○ Begin gemaakt"

            print(f"    {i}. {kleur(sug['naam'], 'cyan')}")
            print(f"       {sug['gevonden']}/{sug['totaal']} ingrediënten "
                  f"({sug['percentage']:.0f}%) - "
                  f"{kleur(status, status_kleur)}")

            if sug["ontbrekend"] and len(sug["ontbrekend"]) <= 3:
                ontbrekend_str = ", ".join(sug["ontbrekend"])
                print(kleur(f"       Nog nodig: {ontbrekend_str}", "grijs"))
            elif sug["ontbrekend"]:
                print(kleur(f"       Nog {len(sug['ontbrekend'])} "
                           f"ingrediënten nodig", "grijs"))
            print()

        # Optie om ontbrekende ingrediënten toe te voegen
        print(kleur("  Wil je ontbrekende ingrediënten toevoegen?", Kleur.GEEL))
        keuze = input(kleur("  Nummer van recept (of 0 = terug): ", "cyan")).strip()

        if keuze == "0" or not keuze:
            return

        try:
            idx = int(keuze) - 1
            if 0 <= idx < len(suggesties):
                sug = suggesties[idx]
                if not sug["ontbrekend"]:
                    succes(f"Je hebt alle ingrediënten voor {sug['naam']}!")
                    return

                print(kleur(f"\n  Ontbrekende ingrediënten voor {sug['naam']}:", Kleur.GEEL))
                for ont in sug["ontbrekend"]:
                    print(f"    • {ont}")

                toevoegen = input(kleur(
                    "\n  Alle ontbrekende toevoegen? (j/n): ", "cyan"
                )).lower()

                if toevoegen == "j":
                    # Zoek recept voor categorie info
                    recept = recepten[sug["naam"]]
                    ing_dict = {i["naam"].lower(): i
                               for i in recept.get("ingredienten", [])}

                    for ont in sug["ontbrekend"]:
                        ing_info = ing_dict.get(ont.lower(), {})
                        nieuw_item = {
                            "naam": ont,
                            "hoeveelheid": ing_info.get("hoeveelheid", ""),
                            "categorie": ing_info.get("categorie", "overig"),
                            "prijs": 0,
                            "prioriteit": "normaal",
                            "notitie": f"Voor: {sug['naam']}",
                            "afgevinkt": False,
                            "toegevoegd": datetime.now().isoformat()
                        }
                        self._get_huidige_lijst()["items"].append(nieuw_item)

                    succes(f"{len(sug['ontbrekend'])} ingrediënten toegevoegd!")
        except ValueError:
            fout("Voer een geldig nummer in.")

    # ==================== VOORRAAD ====================

    def _voorraad_menu(self) -> None:
        """Beheer je voorraad thuis."""
        while True:
            self._toon_header("🏠 Voorraad Beheer")

            voorraad = self.data["voorraad"]
            if voorraad:
                print()
                for i, item in enumerate(voorraad, 1):
                    aantal = item.get("aantal", 0)
                    if aantal <= 1:
                        status = kleur("⚠️ Bijna op!", Kleur.ROOD)
                    elif aantal <= 3:
                        status = kleur("📉 Weinig", Kleur.GEEL)
                    else:
                        status = kleur("✓ Voldoende", Kleur.GROEN)

                    print(f"    {i:2}. {item['naam']}: {aantal} {status}")
            else:
                print(kleur("\n  Je voorraad is nog leeg.", Kleur.GEEL))

            print(kleur("\n  Opties:", Kleur.GEEL))
            print("    n = Nieuw item toevoegen")
            print("    [nummer] = Aantal aanpassen")
            print("    v = Item verwijderen")
            print("    l = Lage voorraad naar boodschappenlijst")
            print("    0 = Terug")

            keuze = input(kleur("\n  Keuze: ", "cyan")).strip().lower()

            if keuze == "0":
                break
            elif keuze == "n":
                self._voorraad_toevoegen()
            elif keuze == "v":
                self._voorraad_verwijderen()
            elif keuze == "l":
                self._voorraad_naar_lijst()
            else:
                try:
                    idx = int(keuze) - 1
                    if 0 <= idx < len(voorraad):
                        self._voorraad_aanpassen(idx)
                    else:
                        fout("Ongeldig nummer.")
                except ValueError:
                    fout("Ongeldige invoer.")

            input(kleur("\n  Druk op Enter om verder te gaan...", "grijs"))

    def _voorraad_toevoegen(self) -> None:
        """Voegt een item toe aan de voorraad."""
        naam = input(kleur("\n  Product naam: ", "cyan")).strip()
        if not naam:
            return

        aantal_str = input(kleur("  Aantal: ", "cyan")).strip()
        try:
            aantal = int(aantal_str) if aantal_str else 1
        except ValueError:
            aantal = 1

        categorie = self._kies_categorie()

        self.data["voorraad"].append({
            "naam": naam,
            "aantal": aantal,
            "categorie": categorie
        })
        succes(f"'{naam}' ({aantal}x) toegevoegd aan voorraad!")

    def _voorraad_aanpassen(self, idx: int) -> None:
        """Past de hoeveelheid van een voorraad item aan."""
        item = self.data["voorraad"][idx]
        print(kleur(f"\n  {item['naam']}: huidig aantal = {item['aantal']}", Kleur.GEEL))

        nieuw = input(kleur("  Nieuw aantal: ", "cyan")).strip()
        try:
            item["aantal"] = int(nieuw)
            succes(f"Aantal aangepast naar {item['aantal']}!")
        except ValueError:
            fout("Voer een geldig nummer in.")

    def _voorraad_verwijderen(self) -> None:
        """Verwijdert een voorraad item."""
        voorraad = self.data["voorraad"]
        if not voorraad:
            return

        keuze = input(kleur("\n  Welk nummer verwijderen? ", "cyan")).strip()
        try:
            idx = int(keuze) - 1
            if 0 <= idx < len(voorraad):
                verwijderd = voorraad.pop(idx)
                succes(f"'{verwijderd['naam']}' verwijderd uit voorraad!")
            else:
                fout("Ongeldig nummer.")
        except ValueError:
            fout("Voer een nummer in.")

    def _voorraad_naar_lijst(self) -> None:
        """Voegt items met lage voorraad toe aan de boodschappenlijst."""
        laag = [v for v in self.data["voorraad"] if v.get("aantal", 0) <= 1]

        if not laag:
            info("Geen items met lage voorraad!")
            return

        print(kleur("\n  Items met lage voorraad:", Kleur.GEEL))
        for item in laag:
            print(f"    • {item['naam']} ({item.get('aantal', 0)}x)")

        bevestig = input(kleur(
            "\n  Allemaal toevoegen aan boodschappenlijst? (j/n): ", "cyan"
        )).lower()

        if bevestig == "j":
            for item in laag:
                nieuw_item = {
                    "naam": item["naam"],
                    "hoeveelheid": "",
                    "categorie": item.get("categorie", "overig"),
                    "prijs": 0,
                    "prioriteit": "hoog",
                    "notitie": "Uit voorraad - bijna op",
                    "afgevinkt": False,
                    "toegevoegd": datetime.now().isoformat()
                }
                self._get_huidige_lijst()["items"].append(nieuw_item)

            succes(f"{len(laag)} items toegevoegd aan boodschappenlijst!")

    # ==================== SJABLONEN ====================

    def _sjablonen_menu(self) -> None:
        """Beheer sjablonen voor terugkerende boodschappen."""
        while True:
            self._toon_header("📋 Sjablonen")

            sjablonen = self.data["sjablonen"]
            if sjablonen:
                print()
                for i, (key, sjabloon) in enumerate(sjablonen.items(), 1):
                    aantal = len(sjabloon.get("items", []))
                    print(f"    {i}. {sjabloon['naam']} ({aantal} items)")
            else:
                print(kleur("\n  Geen sjablonen.", Kleur.GEEL))

            print(kleur("\n  Opties:", Kleur.GEEL))
            print("    [nummer] = Sjabloon toevoegen aan lijst")
            print("    n        = Nieuw sjabloon maken")
            print("    h        = Huidige lijst als sjabloon opslaan")
            print("    v        = Sjabloon verwijderen")
            print("    0        = Terug")

            keuze = input(kleur("\n  Keuze: ", "cyan")).strip().lower()

            if keuze == "0":
                break
            elif keuze == "n":
                self._maak_sjabloon()
            elif keuze == "h":
                self._huidige_als_sjabloon()
            elif keuze == "v":
                self._verwijder_sjabloon()
            else:
                try:
                    idx = int(keuze) - 1
                    sjabloon_keys = list(sjablonen.keys())
                    if 0 <= idx < len(sjabloon_keys):
                        self._pas_sjabloon_toe(sjabloon_keys[idx])
                    else:
                        fout("Ongeldig nummer.")
                except ValueError:
                    fout("Voer een nummer in.")

            input(kleur("\n  Druk op Enter om verder te gaan...", "grijs"))

    def _maak_sjabloon(self) -> None:
        """Maakt een nieuw sjabloon."""
        naam = input(kleur("\n  Naam van het sjabloon: ", "cyan")).strip()
        if not naam:
            return

        key = naam.lower().replace(" ", "_")
        items = []

        print(kleur("\n  Voeg items toe (leeg = klaar):", Kleur.GEEL))
        while True:
            item_naam = input(kleur("    Item: ", "cyan")).strip()
            if not item_naam:
                break

            categorie = self._kies_categorie()
            items.append({"naam": item_naam, "categorie": categorie})

        if items:
            self.data["sjablonen"][key] = {
                "naam": naam,
                "items": items
            }
            succes(f"Sjabloon '{naam}' opgeslagen!")

    def _huidige_als_sjabloon(self) -> None:
        """Slaat de huidige lijst op als sjabloon."""
        items = self._get_items()
        if not items:
            waarschuwing("De huidige lijst is leeg.")
            return

        naam = input(kleur("\n  Naam voor dit sjabloon: ", "cyan")).strip()
        if not naam:
            return

        key = naam.lower().replace(" ", "_")
        sjabloon_items = [
            {"naam": i["naam"], "categorie": i.get("categorie", "overig")}
            for i in items
        ]

        self.data["sjablonen"][key] = {
            "naam": naam,
            "items": sjabloon_items
        }
        succes(f"Sjabloon '{naam}' opgeslagen met {len(sjabloon_items)} items!")

    def _pas_sjabloon_toe(self, key: str) -> None:
        """Past een sjabloon toe op de huidige lijst."""
        sjabloon = self.data["sjablonen"].get(key)
        if not sjabloon:
            return

        for item in sjabloon.get("items", []):
            nieuw_item = {
                "naam": item["naam"],
                "hoeveelheid": "",
                "categorie": item.get("categorie", "overig"),
                "prijs": 0,
                "prioriteit": "normaal",
                "notitie": "",
                "afgevinkt": False,
                "toegevoegd": datetime.now().isoformat()
            }
            self._get_huidige_lijst()["items"].append(nieuw_item)

        succes(f"{len(sjabloon['items'])} items toegevoegd uit sjabloon!")

    def _verwijder_sjabloon(self) -> None:
        """Verwijdert een sjabloon."""
        sjablonen = list(self.data["sjablonen"].keys())
        if not sjablonen:
            return

        keuze = input(kleur("\n  Welk nummer verwijderen? ", "cyan")).strip()
        try:
            idx = int(keuze) - 1
            if 0 <= idx < len(sjablonen):
                key = sjablonen[idx]
                naam = self.data["sjablonen"][key]["naam"]
                del self.data["sjablonen"][key]
                succes(f"Sjabloon '{naam}' verwijderd!")
        except (ValueError, KeyError):
            fout("Ongeldige keuze.")

    # ==================== LIJSTEN BEHEREN ====================

    def _lijsten_menu(self) -> None:
        """Beheer meerdere boodschappenlijsten."""
        while True:
            self._toon_header("📑 Lijsten Beheren")

            lijsten = self.data["lijsten"]
            print()
            for i, (key, lijst) in enumerate(lijsten.items(), 1):
                actief = " ◄ ACTIEF" if key == self.huidige_lijst else ""
                items = len(lijst.get("items", []))
                print(f"    {i}. {lijst['naam']} ({lijst['winkel']}) - {items} items{kleur(actief, 'groen')}")

            print(kleur("\n  Opties:", Kleur.GEEL))
            print("    [nummer] = Selecteer lijst")
            print("    n        = Nieuwe lijst maken")
            print("    v        = Lijst verwijderen")
            print("    0        = Terug")

            keuze = input(kleur("\n  Keuze: ", "cyan")).strip().lower()

            if keuze == "0":
                break
            elif keuze == "n":
                self._maak_lijst()
            elif keuze == "v":
                self._verwijder_lijst()
            else:
                try:
                    idx = int(keuze) - 1
                    lijst_keys = list(lijsten.keys())
                    if 0 <= idx < len(lijst_keys):
                        self.huidige_lijst = lijst_keys[idx]
                        succes(f"Lijst gewisseld naar '{lijsten[self.huidige_lijst]['naam']}'!")
                except ValueError:
                    fout("Voer een nummer in.")

            input(kleur("\n  Druk op Enter om verder te gaan...", "grijs"))

    def _maak_lijst(self) -> None:
        """Maakt een nieuwe boodschappenlijst."""
        naam = input(kleur("\n  Naam van de lijst: ", "cyan")).strip()
        if not naam:
            return

        winkel = input(kleur("  Winkel (bijv. Albert Heijn, Lidl): ", "cyan")).strip()
        if not winkel:
            winkel = "Algemeen"

        key = naam.lower().replace(" ", "_")

        self.data["lijsten"][key] = {
            "naam": naam,
            "winkel": winkel,
            "items": [],
            "aangemaakt": datetime.now().isoformat()
        }
        self.huidige_lijst = key
        succes(f"Lijst '{naam}' aangemaakt en geselecteerd!")

    def _verwijder_lijst(self) -> None:
        """Verwijdert een boodschappenlijst."""
        lijsten = list(self.data["lijsten"].keys())

        if len(lijsten) <= 1:
            waarschuwing("Je kunt de laatste lijst niet verwijderen.")
            return

        keuze = input(kleur("\n  Welk nummer verwijderen? ", "cyan")).strip()
        try:
            idx = int(keuze) - 1
            if 0 <= idx < len(lijsten):
                key = lijsten[idx]
                if key == self.huidige_lijst:
                    fout("Je kunt de actieve lijst niet verwijderen. Selecteer eerst een andere.")
                    return

                naam = self.data["lijsten"][key]["naam"]
                bevestig = input(kleur(
                    f"  Weet je zeker dat je '{naam}' wilt verwijderen? (j/n): ", Kleur.ROOD
                )).lower()

                if bevestig == "j":
                    del self.data["lijsten"][key]
                    succes(f"Lijst '{naam}' verwijderd!")
        except (ValueError, KeyError):
            fout("Ongeldige keuze.")

    # ==================== FAVORIETEN ====================

    def _favorieten_menu(self) -> None:
        """Beheer favorieten."""
        while True:
            self._toon_header("⭐ Favorieten Beheren")

            favorieten = self.data["favorieten"]
            if favorieten:
                print()
                for i, fav in enumerate(favorieten, 1):
                    cat_info = self.CATEGORIEEN.get(
                        fav.get("categorie", "overig"),
                        self.CATEGORIEEN["overig"]
                    )
                    print(f"    {i}. {cat_info['emoji']} {fav['naam']}")
            else:
                print(kleur("\n  Nog geen favorieten!", Kleur.GEEL))

            print(kleur("\n  Opties:", Kleur.GEEL))
            print("    n        = Nieuwe favoriet")
            print("    [nummer] = Favoriet verwijderen")
            print("    0        = Terug")

            keuze = input(kleur("\n  Keuze: ", "cyan")).strip().lower()

            if keuze == "0":
                break
            elif keuze == "n":
                self._voeg_favoriet_toe_handmatig()
            else:
                try:
                    idx = int(keuze) - 1
                    if 0 <= idx < len(favorieten):
                        verwijderd = favorieten.pop(idx)
                        succes(f"'{verwijderd['naam']}' verwijderd uit favorieten!")
                except ValueError:
                    fout("Voer een nummer in.")

            input(kleur("\n  Druk op Enter om verder te gaan...", "grijs"))

    def _voeg_favoriet_toe_handmatig(self) -> None:
        """Voegt handmatig een favoriet toe."""
        naam = input(kleur("\n  Naam van favoriet: ", "cyan")).strip()
        if not naam:
            return

        categorie = self._kies_categorie()
        hoeveelheid = input(kleur("  Standaard hoeveelheid (optioneel): ", "cyan")).strip()

        self.data["favorieten"].append({
            "naam": naam,
            "categorie": categorie,
            "hoeveelheid": hoeveelheid
        })
        succes(f"'{naam}' toegevoegd aan favorieten!")

    # ==================== INSTELLINGEN ====================

    def _instellingen_menu(self) -> None:
        """Instellingen menu."""
        while True:
            self._toon_header("⚙️ Instellingen")

            inst = self.data["instellingen"]
            print()
            print(f"    1. Budget limiet: €{inst.get('budget_limiet', 0):.2f}")
            print(f"    2. Toon prijzen: {'Ja' if inst.get('toon_prijzen', True) else 'Nee'}")
            print(f"    3. Sorteer op categorie: {'Ja' if inst.get('sorteer_op_categorie', True) else 'Nee'}")
            print(f"    4. Auto suggesties: {'Ja' if inst.get('auto_suggesties', True) else 'Nee'}")
            print()
            print(kleur("    0. Terug", "grijs"))

            keuze = input(kleur("\n  Keuze: ", "cyan")).strip()

            if keuze == "0":
                break
            elif keuze == "1":
                budget = input(kleur("  Nieuw budget (0 = geen limiet): ", "cyan")).strip()
                try:
                    inst["budget_limiet"] = float(budget.replace(",", "."))
                    succes("Budget aangepast!")
                except ValueError:
                    fout("Ongeldig bedrag.")
            elif keuze == "2":
                inst["toon_prijzen"] = not inst.get("toon_prijzen", True)
                succes(f"Prijzen {'getoond' if inst['toon_prijzen'] else 'verborgen'}!")
            elif keuze == "3":
                inst["sorteer_op_categorie"] = not inst.get("sorteer_op_categorie", True)
                succes("Sortering aangepast!")
            elif keuze == "4":
                inst["auto_suggesties"] = not inst.get("auto_suggesties", True)
                succes(f"Suggesties {'aan' if inst['auto_suggesties'] else 'uit'}!")

            input(kleur("\n  Druk op Enter om verder te gaan...", "grijs"))

    # ==================== STATISTIEKEN ====================

    def _toon_statistieken(self) -> None:
        """Toont aankoopstatistieken."""
        self._toon_header("📊 Statistieken")

        stats = self.data["statistieken"]

        print(kleur("\n  Algemeen:", Kleur.GEEL))
        print(f"    • Totaal items gekocht: {stats.get('totaal_items_gekocht', 0)}")
        print(f"    • Totaal uitgegeven: €{stats.get('totaal_uitgegeven', 0):.2f}")

        # Meest gekocht
        meest = stats.get("meest_gekocht", {})
        if meest:
            print(kleur("\n  Top 10 meest gekocht:", Kleur.GEEL))
            top = sorted(meest.items(), key=lambda x: x[1], reverse=True)[:10]
            for i, (naam, aantal) in enumerate(top, 1):
                print(f"    {i:2}. {naam}: {aantal}x")

        # Uitgaven per maand
        per_maand = stats.get("uitgaven_per_maand", {})
        if per_maand:
            print(kleur("\n  Uitgaven per maand:", Kleur.GEEL))
            for maand in sorted(per_maand.keys(), reverse=True)[:6]:
                bedrag = per_maand[maand]
                print(f"    • {maand}: €{bedrag:.2f}")

        # Geschiedenis
        gesch = self.data["geschiedenis"]
        if gesch:
            print(kleur(f"\n  Laatste {min(5, len(gesch))} aankopen:", Kleur.GEEL))
            for entry in gesch[-5:]:
                datum = entry["datum"][:10]
                aantal = len(entry["items"])
                totaal = entry["totaal"]
                print(f"    • {datum}: {aantal} items (€{totaal:.2f})")

    # ==================== EXPORT ====================

    def _exporteer_menu(self) -> None:
        """Export opties."""
        self._toon_header("📤 Exporteren")

        print(kleur("\n  Opties:", Kleur.GEEL))
        print("    1. Exporteer als tekst (.txt)")
        print("    2. Exporteer als JSON")
        print("    3. Kopieerbare lijst (simpel)")
        print("    0. Terug")

        keuze = input(kleur("\n  Keuze: ", "cyan")).strip()

        if keuze == "1":
            self._exporteer_txt()
        elif keuze == "2":
            self._exporteer_json()
        elif keuze == "3":
            self._toon_kopieerbaar()

    def _exporteer_txt(self) -> None:
        """Exporteert de lijst als tekstbestand."""
        lijst = self._get_huidige_lijst()
        items = lijst.get("items", [])

        if not items:
            waarschuwing("De lijst is leeg.")
            return

        datum = datetime.now().strftime("%Y%m%d_%H%M")
        bestandsnaam = f"boodschappen_{datum}.txt"
        pad = self.export_dir / bestandsnaam

        with open(pad, "w", encoding="utf-8") as f:
            f.write(f"BOODSCHAPPENLIJST - {lijst['naam']}\n")
            f.write(f"Winkel: {lijst['winkel']}\n")
            f.write(f"Datum: {datetime.now().strftime('%d-%m-%Y %H:%M')}\n")
            f.write("=" * 40 + "\n\n")

            # Groepeer per categorie
            per_cat = {}
            for item in items:
                cat = item.get("categorie", "overig")
                if cat not in per_cat:
                    per_cat[cat] = []
                per_cat[cat].append(item)

            for cat_key, cat_items in per_cat.items():
                cat_naam = self.CATEGORIEEN.get(cat_key, {}).get("naam", cat_key)
                f.write(f"[{cat_naam.upper()}]\n")
                for item in cat_items:
                    status = "[x]" if item.get("afgevinkt") else "[ ]"
                    hoev = item.get("hoeveelheid", "")
                    tekst = f"{hoev} {item['naam']}" if hoev else item["naam"]
                    prijs = f" - €{item['prijs']:.2f}" if item.get("prijs") else ""
                    f.write(f"  {status} {tekst}{prijs}\n")
                f.write("\n")

            # Totaal
            totaal = sum(i.get("prijs", 0) for i in items if not i.get("afgevinkt"))
            f.write(f"TOTAAL: €{totaal:.2f}\n")

        succes(f"Geëxporteerd naar: {pad}")

    def _exporteer_json(self) -> None:
        """Exporteert de lijst als JSON bestand."""
        lijst = self._get_huidige_lijst()

        datum = datetime.now().strftime("%Y%m%d_%H%M")
        bestandsnaam = f"boodschappen_{datum}.json"
        pad = self.export_dir / bestandsnaam

        with open(pad, "w", encoding="utf-8") as f:
            json.dump(lijst, f, indent=2, ensure_ascii=False)

        succes(f"Geëxporteerd naar: {pad}")

    def _toon_kopieerbaar(self) -> None:
        """Toont een simpele kopieerbare lijst."""
        items = self._get_items()

        if not items:
            waarschuwing("De lijst is leeg.")
            return

        print(kleur("\n  Kopieerbare lijst:", Kleur.GEEL))
        print("  " + "-" * 30)

        for item in items:
            if not item.get("afgevinkt"):
                hoev = item.get("hoeveelheid", "")
                tekst = f"{hoev} {item['naam']}" if hoev else item["naam"]
                print(f"  • {tekst}")

        print("  " + "-" * 30)

    # ==================== MAIN LOOP ====================

    def run(self) -> None:
        """Start de app."""
        clear_scherm()

        print(kleur("""
    ╔═══════════════════════════════════════════════════╗
    ║                                                   ║
    ║   🛒  BOODSCHAPPENLIJST  v2.0                    ║
    ║                                                   ║
    ║   Budget • Recepten • Voorraad • Statistieken    ║
    ║                                                   ║
    ╚═══════════════════════════════════════════════════╝
        """, "cyan"))

        # Toon status
        lijst = self._get_huidige_lijst()
        items_count = len(lijst.get("items", []))
        fav_count = len(self.data["favorieten"])
        recept_count = len(self.data["recepten"])

        print(f"    Geladen: {items_count} items, {fav_count} favorieten, {recept_count} recepten")
        print(f"    Actieve lijst: {lijst['naam']} ({lijst['winkel']})")

        while True:
            self._toon_menu()
            keuze = input(kleur("\n  Kies een optie: ", "cyan")).strip().lower()

            if keuze == "1":
                self._toon_lijst()
            elif keuze == "2":
                self._voeg_toe()
            elif keuze == "3":
                self._voeg_favoriet_toe()
            elif keuze == "4":
                self._afvinken()
            elif keuze == "5":
                self._bewerk_item()
            elif keuze == "6":
                self._verwijder()
            elif keuze == "r":
                self._recepten_menu()
            elif keuze == "v":
                self._voorraad_menu()
            elif keuze == "s":
                self._sjablonen_menu()
            elif keuze == "l":
                self._lijsten_menu()
            elif keuze == "f":
                self._favorieten_menu()
            elif keuze == "i":
                self._instellingen_menu()
            elif keuze == "t":
                self._toon_statistieken()
            elif keuze == "e":
                self._exporteer_menu()
            elif keuze == "8":
                self._sla_op()
            elif keuze == "0":
                opslaan = input(kleur(
                    "  Wil je opslaan voor het afsluiten? (j/n): ", "cyan"
                )).lower()
                if opslaan == "j":
                    self._sla_op()
                print(kleur("\n  Terug naar hoofdmenu...", "grijs"))
                break
            else:
                fout("Ongeldige keuze.")

            input(kleur("\n  Druk op Enter om verder te gaan...", "grijs"))
