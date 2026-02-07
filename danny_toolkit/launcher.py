"""
Danny Toolkit Launcher - Hoofdmenu.
Versie 2.0 - Met thema's, kleuren, statistieken en meer.
"""

import sys
import json
from datetime import datetime
from pathlib import Path

from .core.utils import (
    clear_scherm, fix_encoding, kleur, succes, fout, waarschuwing, info,
    vet, Kleur, TabelFormatter, kies_uit_lijst
)
from .core.config import Config, Thema, Taal

from .apps.boodschappenlijst import BoodschappenlijstApp
from .apps.rekenmachine import RekenmachineApp
from .apps.virtueel_huisdier import VirtueelHuisdierApp
from .apps.schatzoek import SchatzoekApp
from .apps.code_analyse import CodeAnalyseApp
from .apps.notitie_app import NotitieApp
from .apps.wachtwoord_generator import WachtwoordGeneratorApp
from .apps.pomodoro_timer import PomodoroTimerApp
from .apps.habit_tracker import HabitTrackerApp
from .apps.expense_tracker import ExpenseTrackerApp
from .apps.flashcards import FlashcardsApp
from .apps.unit_converter import UnitConverterApp
from .apps.agenda_planner import AgendaPlannerApp
from .apps.mood_tracker import MoodTrackerApp
from .apps.citaten_generator import CitatenGeneratorApp
from .apps.vector_studio import VectorStudioApp
from .apps.goals_tracker import GoalsTrackerApp
from .apps.room_planner import RoomPlannerApp
from .apps.artificial_life import ArtificialLifeApp

from .ai.mini_rag import MiniRAG
from .ai.production_rag import ProductionRAG
from .ai.nieuws_agent import NieuwsAgentApp
from .ai.weer_agent import WeerAgentApp
from .ai.claude_chat import ClaudeChatApp


# =============================================================================
# ASCII BANNERS
# =============================================================================

BANNER_STANDAARD = """
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║     ██████╗  █████╗ ███╗   ██╗███╗   ██╗██╗   ██╗            ║
║     ██╔══██╗██╔══██╗████╗  ██║████╗  ██║╚██╗ ██╔╝            ║
║     ██║  ██║███████║██╔██╗ ██║██╔██╗ ██║ ╚████╔╝             ║
║     ██║  ██║██╔══██║██║╚██╗██║██║╚██╗██║  ╚██╔╝              ║
║     ██████╔╝██║  ██║██║ ╚████║██║ ╚████║   ██║               ║
║     ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═══╝╚═╝  ╚═══╝   ╚═╝               ║
║                                                               ║
║              T O O L K I T   v2.0                             ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
"""

BANNER_MINIMAAL = """
============================================================
     DANNY TOOLKIT v2.0
============================================================
"""

BANNER_RETRO = r"""
************************************************************
*    ____    _    _   _ _   _ __   __                      *
*   |  _ \  / \  | \ | | \ | |\ \ / /                      *
*   | | | |/ _ \ |  \| |  \| | \ V /                       *
*   | |_| / ___ \| |\  | |\  |  | |                        *
*   |____/_/   \_\_| \_|_| \_|  |_|  TOOLKIT               *
*                                                          *
************************************************************
"""


class LauncherStats:
    """Beheert launcher statistieken en recente apps."""

    def __init__(self):
        Config.ensure_dirs()
        self.stats_file = Config.APPS_DATA_DIR / "launcher_stats.json"
        self.data = self._laad()

    def _laad(self) -> dict:
        """Laad statistieken."""
        if self.stats_file.exists():
            try:
                with open(self.stats_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return {
            "gebruik": {},
            "recente": [],
            "totaal_sessies": 0,
            "eerste_gebruik": datetime.now().isoformat()
        }

    def _opslaan(self):
        """Sla statistieken op."""
        with open(self.stats_file, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)

    def registreer_gebruik(self, app_naam: str):
        """Registreer dat een app is gebruikt."""
        # Update gebruik teller
        if app_naam not in self.data["gebruik"]:
            self.data["gebruik"][app_naam] = 0
        self.data["gebruik"][app_naam] += 1

        # Update recente lijst
        if app_naam in self.data["recente"]:
            self.data["recente"].remove(app_naam)
        self.data["recente"].insert(0, app_naam)
        self.data["recente"] = self.data["recente"][:5]  # Bewaar laatste 5

        self._opslaan()

    def registreer_sessie(self):
        """Registreer een nieuwe sessie."""
        self.data["totaal_sessies"] += 1
        self._opslaan()

    def get_recente(self, max_aantal: int = 3) -> list:
        """Haal recente apps op."""
        return self.data["recente"][:max_aantal]

    def get_gebruik(self, app_naam: str) -> int:
        """Haal gebruik teller op voor een app."""
        return self.data["gebruik"].get(app_naam, 0)

    def get_totaal_gebruik(self) -> int:
        """Totaal aantal app starts."""
        return sum(self.data["gebruik"].values())

    def get_favorieten(self, max_aantal: int = 3) -> list:
        """Haal meest gebruikte apps op."""
        gesorteerd = sorted(
            self.data["gebruik"].items(),
            key=lambda x: x[1],
            reverse=True
        )
        return [naam for naam, _ in gesorteerd[:max_aantal]]


class Launcher:
    """Hoofdlauncher voor Danny Toolkit."""

    VERSIE = "2.0.0"

    # Alle beschikbare apps
    APPS = {
        "1": ("Boodschappenlijst", BoodschappenlijstApp, "apps"),
        "2": ("Slimme Rekenmachine", RekenmachineApp, "apps"),
        "3": ("Virtueel Huisdier", VirtueelHuisdierApp, "apps"),
        "4": ("Schatzoek Game", SchatzoekApp, "apps"),
        "5": ("Code Analyse", CodeAnalyseApp, "apps"),
        "6": ("Mini-RAG Demo", MiniRAG, "ai"),
        "7": ("Production RAG", ProductionRAG, "ai"),
        "8": ("Nieuws Agent", NieuwsAgentApp, "ai"),
        "9": ("Weer Agent", WeerAgentApp, "ai"),
        "10": ("Claude Chat", ClaudeChatApp, "ai"),
        "11": ("Notitie App", NotitieApp, "productiviteit"),
        "12": ("Wachtwoord Generator", WachtwoordGeneratorApp, "productiviteit"),
        "13": ("Pomodoro Timer", PomodoroTimerApp, "productiviteit"),
        "14": ("Habit Tracker", HabitTrackerApp, "productiviteit"),
        "15": ("Expense Tracker", ExpenseTrackerApp, "productiviteit"),
        "16": ("Flashcards", FlashcardsApp, "productiviteit"),
        "17": ("Unit Converter", UnitConverterApp, "productiviteit"),
        "18": ("Agenda Planner", AgendaPlannerApp, "productiviteit"),
        "19": ("Mood Tracker", MoodTrackerApp, "productiviteit"),
        "20": ("Citaten Generator", CitatenGeneratorApp, "productiviteit"),
        "21": ("Vector Data Studio", VectorStudioApp, "ai"),
        "22": ("Goals Tracker", GoalsTrackerApp, "productiviteit"),
        "23": ("Room Planner", RoomPlannerApp, "productiviteit"),
        "24": ("Artificial Life", ArtificialLifeApp, "ai"),
    }

    # Sneltoetsen
    SNELTOETSEN = {
        "b": "1",   # Boodschappenlijst
        "r": "2",   # Rekenmachine
        "h": "3",   # Huisdier
        "s": "4",   # Schatzoek
        "c": "5",   # Code analyse
        "n": "8",   # Nieuws
        "w": "9",   # Weer
        "no": "11", # Notitie
        "wg": "12", # Wachtwoord Generator
        "po": "13", # Pomodoro
        "ha": "14", # Habit
        "ex": "15", # Expense
        "fl": "16", # Flashcards
        "un": "17", # Unit
        "ag": "18", # Agenda
        "mo": "19", # Mood
        "ci": "20", # Citaten
        "vs": "21", # Vector Studio
        "go": "22", # Goals Tracker
        "ro": "23", # Room Planner
        "al": "24", # Artificial Life
    }

    def __init__(self):
        fix_encoding()
        Config.ensure_dirs()
        Config.laad_voorkeuren()
        self.stats = LauncherStats()
        self.stats.registreer_sessie()

    def _get_banner(self) -> str:
        """Haal de juiste banner op basis van thema."""
        thema_naam = Config._thema
        if thema_naam == "minimaal":
            return BANNER_MINIMAAL
        elif thema_naam == "retro":
            return BANNER_RETRO
        return BANNER_STANDAARD

    def _kleur_tekst(self, tekst: str, type_: str = "normaal") -> str:
        """Kleur tekst op basis van type."""
        kleuren = {
            "titel": Kleur.FEL_CYAAN,
            "categorie": Kleur.FEL_GEEL,
            "optie": Kleur.FEL_WIT,
            "nummer": Kleur.FEL_GROEN,
            "info": Kleur.FEL_BLAUW,
            "waarschuwing": Kleur.FEL_GEEL,
            "fout": Kleur.FEL_ROOD,
            "succes": Kleur.FEL_GROEN,
        }
        return kleur(tekst, kleuren.get(type_, ""))

    def toon_menu(self):
        """Toont het hoofdmenu."""
        clear_scherm()
        taal = Config.get_taal()
        thema = Config.get_thema()

        # Banner
        print(self._kleur_tekst(self._get_banner(), "titel"))

        # Recente apps
        recente = self.stats.get_recente(3)
        if recente:
            print(self._kleur_tekst("  ★ RECENT GEBRUIKT", "categorie"))
            for app_naam in recente:
                # Vind de key voor deze app
                for key, (naam, _, _) in self.APPS.items():
                    if naam == app_naam:
                        gebruik = self.stats.get_gebruik(app_naam)
                        print(f"     {self._kleur_tekst(key, 'nummer')}. {naam} "
                              f"{self._kleur_tekst(f'({gebruik}x)', 'info')}")
                        break
            print()

        # Applicaties
        print(self._kleur_tekst("  ═══ APPLICATIES ═══", "categorie"))
        for key in ["1", "2", "3", "4", "5"]:
            naam, _, _ = self.APPS[key]
            gebruik = self.stats.get_gebruik(naam)
            gebruik_str = f" ({gebruik}x)" if gebruik > 0 else ""
            print(f"     {self._kleur_tekst(key, 'nummer')}. {naam}"
                  f"{self._kleur_tekst(gebruik_str, 'info')}")
        print()

        # AI Systemen
        print(self._kleur_tekst("  ═══ AI SYSTEMEN ═══", "categorie"))
        for key in ["6", "7", "8", "9", "10", "21", "24"]:
            naam, _, _ = self.APPS[key]
            gebruik = self.stats.get_gebruik(naam)
            gebruik_str = f" ({gebruik}x)" if gebruik > 0 else ""
            print(f"     {self._kleur_tekst(key, 'nummer')}. {naam}"
                  f"{self._kleur_tekst(gebruik_str, 'info')}")
        print()

        # Productiviteit Apps
        print(self._kleur_tekst("  ═══ PRODUCTIVITEIT ═══", "categorie"))
        for key in ["11", "12", "13", "14", "15", "16", "17", "18", "19", "20",
                    "22", "23"]:
            naam, _, _ = self.APPS[key]
            gebruik = self.stats.get_gebruik(naam)
            gebruik_str = f" ({gebruik}x)" if gebruik > 0 else ""
            print(f"     {self._kleur_tekst(key, 'nummer')}. {naam}"
                  f"{self._kleur_tekst(gebruik_str, 'info')}")
        print()

        # Systeem opties
        print(self._kleur_tekst("  ═══ SYSTEEM ═══", "categorie"))
        print(f"     {self._kleur_tekst('z', 'nummer')}. Zoeken")
        print(f"     {self._kleur_tekst('i', 'nummer')}. Info & Statistieken")
        print(f"     {self._kleur_tekst('o', 'nummer')}. Instellingen")
        print(f"     {self._kleur_tekst('?', 'nummer')}. Help / Sneltoetsen")
        print(f"     {self._kleur_tekst('0', 'nummer')}. Afsluiten")
        print()

        # Status balk
        sessies = self.stats.data["totaal_sessies"]
        totaal = self.stats.get_totaal_gebruik()
        thema_naam = Thema.get(Config._thema)["naam"]
        taal_naam = taal["naam"]
        print(f"  {self._kleur_tekst(f'Sessies: {sessies} | Apps: {totaal} | Thema: {thema_naam} | Taal: {taal_naam}', 'info')}")
        print()

    def toon_help(self):
        """Toont help en sneltoetsen."""
        clear_scherm()
        print(self._kleur_tekst("\n  ═══ HELP & SNELTOETSEN ═══\n", "categorie"))

        print("  Sneltoetsen voor apps:")
        print(f"     {self._kleur_tekst('b', 'nummer')} = Boodschappenlijst")
        print(f"     {self._kleur_tekst('r', 'nummer')} = Rekenmachine")
        print(f"     {self._kleur_tekst('h', 'nummer')} = Huisdier")
        print(f"     {self._kleur_tekst('s', 'nummer')} = Schatzoek")
        print(f"     {self._kleur_tekst('c', 'nummer')} = Code Analyse")
        print(f"     {self._kleur_tekst('n', 'nummer')} = Nieuws Agent")
        print(f"     {self._kleur_tekst('w', 'nummer')} = Weer Agent")
        print()

        print("  Productiviteit sneltoetsen:")
        print(f"     {self._kleur_tekst('no', 'nummer')} = Notitie App")
        print(f"     {self._kleur_tekst('wg', 'nummer')} = Wachtwoord Generator")
        print(f"     {self._kleur_tekst('po', 'nummer')} = Pomodoro Timer")
        print(f"     {self._kleur_tekst('ha', 'nummer')} = Habit Tracker")
        print(f"     {self._kleur_tekst('ex', 'nummer')} = Expense Tracker")
        print(f"     {self._kleur_tekst('fl', 'nummer')} = Flashcards")
        print(f"     {self._kleur_tekst('un', 'nummer')} = Unit Converter")
        print(f"     {self._kleur_tekst('ag', 'nummer')} = Agenda Planner")
        print(f"     {self._kleur_tekst('mo', 'nummer')} = Mood Tracker")
        print(f"     {self._kleur_tekst('ci', 'nummer')} = Citaten Generator")
        print(f"     {self._kleur_tekst('vs', 'nummer')} = Vector Data Studio")
        print(f"     {self._kleur_tekst('go', 'nummer')} = Goals Tracker")
        print(f"     {self._kleur_tekst('ro', 'nummer')} = Room Planner")
        print()

        print("  Systeem commando's:")
        print(f"     {self._kleur_tekst('z <zoekterm>', 'nummer')} = Zoek apps")
        print(f"     {self._kleur_tekst('i', 'nummer')} = Info & Statistieken")
        print(f"     {self._kleur_tekst('o', 'nummer')} = Instellingen")
        print(f"     {self._kleur_tekst('0 of q', 'nummer')} = Afsluiten")
        print()

        print("  Command line:")
        print(f"     python main.py {self._kleur_tekst('<nummer>', 'nummer')} = Start app direct")
        print(f"     python main.py {self._kleur_tekst('--help', 'nummer')} = Toon help")
        print()

        input("  Druk op Enter om terug te gaan...")

    def toon_info(self):
        """Toont informatie en statistieken."""
        clear_scherm()
        print(self._kleur_tekst("\n  ═══ INFO & STATISTIEKEN ═══\n", "categorie"))

        # Algemene info
        print(f"  {self._kleur_tekst('Versie:', 'info')} {self.VERSIE}")
        print(f"  {self._kleur_tekst('Eigenaar:', 'info')} danny.laurent1988@gmail.com")
        print(f"  {self._kleur_tekst('Eerste gebruik:', 'info')} {self.stats.data.get('eerste_gebruik', 'Onbekend')[:10]}")
        print()

        # Statistieken
        print(self._kleur_tekst("  ─── Gebruik ───", "categorie"))
        print(f"  Totaal sessies: {self.stats.data['totaal_sessies']}")
        print(f"  Totaal app starts: {self.stats.get_totaal_gebruik()}")
        print()

        # Top apps
        print(self._kleur_tekst("  ─── Meest Gebruikt ───", "categorie"))
        for i, app_naam in enumerate(self.stats.get_favorieten(5), 1):
            aantal = self.stats.get_gebruik(app_naam)
            print(f"  {i}. {app_naam}: {aantal}x")
        print()

        # Paden
        print(self._kleur_tekst("  ─── Paden ───", "categorie"))
        print(f"  Data: {Config.DATA_DIR}")
        print(f"  Apps: {Config.APPS_DATA_DIR}")
        print(f"  RAG:  {Config.RAG_DATA_DIR}")
        print()

        # API Status
        print(self._kleur_tekst("  ─── API Status ───", "categorie"))
        groq = succes("[OK] GRATIS!") if Config.has_groq_key() else fout("[NIET INGESTELD]")
        anthropic = succes("[OK]") if Config.has_anthropic_key() else fout("[NIET INGESTELD]")
        voyage = succes("[OK]") if Config.has_voyage_key() else fout("[NIET INGESTELD]")
        print(f"  GROQ_API_KEY:      {groq}")
        print(f"  ANTHROPIC_API_KEY: {anthropic}")
        print(f"  VOYAGE_API_KEY:    {voyage}")
        print()

        input("  Druk op Enter om terug te gaan...")

    def toon_instellingen(self):
        """Toont en beheert instellingen."""
        while True:
            clear_scherm()
            print(self._kleur_tekst("\n  ═══ INSTELLINGEN ═══\n", "categorie"))

            # Huidige instellingen
            thema = Thema.get(Config._thema)
            taal = Taal.get(Config._taal)

            print(f"  1. Thema:  {thema['naam']} ({Config._thema})")
            print(f"  2. Taal:   {taal['naam']} ({Config._taal})")
            print(f"  3. Debug:  {'Aan' if Config._debug_mode else 'Uit'}")
            print(f"  4. Kleuren: {'Aan' if Kleur.is_aan() else 'Uit'}")
            print()
            print(f"  5. Reset statistieken")
            print(f"  0. Terug")
            print()

            keuze = input("  Keuze: ").strip()

            if keuze == "0":
                break

            elif keuze == "1":
                # Thema kiezen
                print("\n  Beschikbare thema's:")
                themas = Thema.lijst()
                for i, t in enumerate(themas, 1):
                    info = Thema.get(t)
                    print(f"    {i}. {info['naam']}")

                try:
                    t_keuze = int(input("\n  Kies thema (1-4): ").strip()) - 1
                    if 0 <= t_keuze < len(themas):
                        Config.set_thema(themas[t_keuze])
                        print(succes(f"\n  Thema gewijzigd naar {themas[t_keuze]}!"))
                except (ValueError, IndexError):
                    print(fout("\n  Ongeldige keuze."))
                input("  Druk op Enter...")

            elif keuze == "2":
                # Taal kiezen
                print("\n  Beschikbare talen:")
                talen = Taal.lijst()
                for i, (code, naam) in enumerate(talen, 1):
                    print(f"    {i}. {naam} ({code})")

                try:
                    t_keuze = int(input("\n  Kies taal (1-4): ").strip()) - 1
                    if 0 <= t_keuze < len(talen):
                        code, _ = talen[t_keuze]
                        Config.set_taal(code)
                        print(succes(f"\n  Taal gewijzigd naar {code}!"))
                except (ValueError, IndexError):
                    print(fout("\n  Ongeldige keuze."))
                input("  Druk op Enter...")

            elif keuze == "3":
                # Toggle debug
                Config.set_debug(not Config._debug_mode)
                status = "aan" if Config._debug_mode else "uit"
                print(succes(f"\n  Debug mode staat nu {status}."))
                input("  Druk op Enter...")

            elif keuze == "4":
                # Toggle kleuren
                if Kleur.is_aan():
                    Kleur.uit()
                    print("\n  Kleuren uitgeschakeld.")
                else:
                    Kleur.aan()
                    print(succes("\n  Kleuren ingeschakeld!"))
                input("  Druk op Enter...")

            elif keuze == "5":
                # Reset statistieken
                bevestig = input("\n  Weet je zeker? (j/n): ").lower().strip()
                if bevestig == "j":
                    self.stats.data = {
                        "gebruik": {},
                        "recente": [],
                        "totaal_sessies": 1,
                        "eerste_gebruik": datetime.now().isoformat()
                    }
                    self.stats._opslaan()
                    print(succes("\n  Statistieken gereset!"))
                else:
                    print("\n  Geannuleerd.")
                input("  Druk op Enter...")

    def zoek_apps(self, zoekterm: str = None):
        """Zoek apps op naam."""
        if not zoekterm:
            zoekterm = input("\n  Zoekterm: ").strip().lower()

        if not zoekterm:
            return None

        resultaten = []
        for key, (naam, app_class, categorie) in self.APPS.items():
            if zoekterm in naam.lower():
                resultaten.append((key, naam, categorie))

        if not resultaten:
            print(fout(f"\n  Geen apps gevonden voor '{zoekterm}'"))
            input("  Druk op Enter...")
            return None

        if len(resultaten) == 1:
            # Direct starten als er maar 1 resultaat is
            return resultaten[0][0]

        print(f"\n  Gevonden ({len(resultaten)}):")
        for key, naam, cat in resultaten:
            print(f"    {self._kleur_tekst(key, 'nummer')}. {naam} [{cat}]")

        keuze = input("\n  Start app (nummer): ").strip()
        if keuze in [r[0] for r in resultaten]:
            return keuze
        return None

    def start_app(self, key: str):
        """Start een app op basis van key."""
        if key not in self.APPS:
            print(fout(f"\n  Ongeldige keuze: {key}"))
            return

        naam, app_class, _ = self.APPS[key]
        self.stats.registreer_gebruik(naam)

        print(f"\n  {self._kleur_tekst('Starting', 'info')} {self._kleur_tekst(naam, 'titel')}...")
        print()

        try:
            app = app_class()
            app.run()
        except KeyboardInterrupt:
            print(waarschuwing("\n\n  [Onderbroken] Terug naar hoofdmenu..."))
        except Exception as e:
            print(fout(f"\n  [FOUT] {e}"))
            if Config.is_debug():
                import traceback
                traceback.print_exc()
            input("\n  Druk op Enter om terug te gaan...")

    def run(self, direct_start: str = None):
        """Start de launcher."""
        # Direct start via command line
        if direct_start:
            if direct_start in self.APPS:
                self.start_app(direct_start)
                return
            elif direct_start in self.SNELTOETSEN:
                self.start_app(self.SNELTOETSEN[direct_start])
                return
            else:
                print(fout(f"Onbekende app: {direct_start}"))
                return

        # Interactieve modus
        while True:
            self.toon_menu()
            keuze = input("  Keuze: ").strip().lower()

            # Afsluiten
            if keuze in ["0", "q", "quit", "exit"]:
                clear_scherm()
                print(self._kleur_tekst(
                    "\n  Tot ziens! Bedankt voor het gebruiken van Danny Toolkit.\n",
                    "succes"
                ))
                break

            # Info
            elif keuze == "i":
                self.toon_info()

            # Instellingen
            elif keuze == "o":
                self.toon_instellingen()

            # Help
            elif keuze == "?":
                self.toon_help()

            # Zoeken
            elif keuze == "z" or keuze.startswith("z "):
                zoekterm = keuze[2:].strip() if keuze.startswith("z ") else None
                resultaat = self.zoek_apps(zoekterm)
                if resultaat:
                    self.start_app(resultaat)

            # Sneltoetsen
            elif keuze in self.SNELTOETSEN:
                self.start_app(self.SNELTOETSEN[keuze])

            # Directe app keuze
            elif keuze in self.APPS:
                self.start_app(keuze)

            else:
                print(fout("\n  Ongeldige keuze. Typ '?' voor help."))
                input("  Druk op Enter...")


def main():
    """Hoofdfunctie van de launcher."""
    # Check voor command line argumenten
    direct_start = None

    if len(sys.argv) > 1:
        arg = sys.argv[1]

        if arg in ["--help", "-h"]:
            print("""
Danny Toolkit v2.0

Gebruik:
  python main.py              Start interactieve launcher
  python main.py <nummer>     Start app direct (1-20)
  python main.py <sneltoets>  Start app via sneltoets
  python main.py --help       Toon deze help

Apps (1-5):               AI (6-10):
  b = Boodschappenlijst     n = Nieuws Agent
  r = Rekenmachine          w = Weer Agent
  h = Huisdier
  s = Schatzoek
  c = Code Analyse

Productiviteit (11-20, 22-23):
  no = Notitie App          ha = Habit Tracker
  wg = Wachtwoord Gen       ex = Expense Tracker
  po = Pomodoro Timer       fl = Flashcards
  un = Unit Converter       ag = Agenda Planner
  mo = Mood Tracker         ci = Citaten Generator
  go = Goals Tracker        ro = Room Planner

AI Extra (21):
  vs = Vector Data Studio
""")
            return

        direct_start = arg

    launcher = Launcher()
    launcher.run(direct_start)


if __name__ == "__main__":
    main()
