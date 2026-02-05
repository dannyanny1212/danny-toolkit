"""
Danny Toolkit Launcher - Hoofdmenu.
"""

from .core.utils import clear_scherm, fix_encoding
from .core.config import Config

from .apps.boodschappenlijst import BoodschappenlijstApp
from .apps.rekenmachine import RekenmachineApp
from .apps.virtueel_huisdier import VirtueelHuisdierApp
from .apps.schatzoek import SchatzoekApp
from .apps.code_analyse import CodeAnalyseApp

from .ai.mini_rag import MiniRAG
from .ai.production_rag import ProductionRAG
from .ai.nieuws_agent import NieuwsAgentApp
from .ai.weer_agent import WeerAgentApp
from .ai.claude_chat import ClaudeChatApp


def toon_menu():
    """Toont het hoofdmenu."""
    clear_scherm()
    print("=" * 60)
    print("     DANNY TOOLKIT - Unified Python Applications")
    print("=" * 60)
    print()
    print("  === APPLICATIES ===")
    print("  1. Boodschappenlijst")
    print("  2. Slimme Rekenmachine")
    print("  3. Virtueel Huisdier")
    print("  4. Schatzoek Game")
    print("  5. Code Analyse")
    print()
    print("  === AI SYSTEMEN ===")
    print("  6. Mini-RAG Demo")
    print("  7. Production RAG")
    print("  8. Nieuws Agent")
    print("  9. Weer Agent")
    print("  10. Claude Chat")
    print()
    print("  === SYSTEEM ===")
    print("  0. Afsluiten")
    print("  i. Info & Instellingen")
    print()
    print("=" * 60)


def toon_info():
    """Toont informatie over de toolkit."""
    clear_scherm()
    print("=" * 60)
    print("     DANNY TOOLKIT - Info & Instellingen")
    print("=" * 60)
    print()
    print(f"  Versie: 1.0.0")
    print(f"  Eigenaar: danny.laurent1988@gmail.com")
    print()
    print("  === PADEN ===")
    print(f"  Data directory: {Config.DATA_DIR}")
    print(f"  RAG documenten: {Config.DOCUMENTEN_DIR}")
    print(f"  Rapporten: {Config.RAPPORTEN_DIR}")
    print()
    print("  === API STATUS ===")
    anthropic_status = "[OK]" if Config.has_anthropic_key() else "[NIET INGESTELD]"
    voyage_status = "[OK]" if Config.has_voyage_key() else "[NIET INGESTELD]"
    print(f"  ANTHROPIC_API_KEY: {anthropic_status}")
    print(f"  VOYAGE_API_KEY: {voyage_status}")
    print()
    print("  === API KEYS INSTELLEN ===")
    print("  Windows CMD:")
    print("    set ANTHROPIC_API_KEY=sk-ant-...")
    print("    set VOYAGE_API_KEY=pa-...")
    print()
    print("  Windows PowerShell:")
    print("    $env:ANTHROPIC_API_KEY = \"sk-ant-...\"")
    print("    $env:VOYAGE_API_KEY = \"pa-...\"")
    print()
    print("=" * 60)
    input("\nDruk op Enter om terug te gaan...")


def main():
    """Hoofdfunctie van de launcher."""
    fix_encoding()
    Config.ensure_dirs()

    apps = {
        "1": ("Boodschappenlijst", BoodschappenlijstApp),
        "2": ("Slimme Rekenmachine", RekenmachineApp),
        "3": ("Virtueel Huisdier", VirtueelHuisdierApp),
        "4": ("Schatzoek Game", SchatzoekApp),
        "5": ("Code Analyse", CodeAnalyseApp),
        "6": ("Mini-RAG Demo", MiniRAG),
        "7": ("Production RAG", ProductionRAG),
        "8": ("Nieuws Agent", NieuwsAgentApp),
        "9": ("Weer Agent", WeerAgentApp),
        "10": ("Claude Chat", ClaudeChatApp),
    }

    while True:
        toon_menu()
        keuze = input("  Keuze: ").strip().lower()

        if keuze == "0":
            clear_scherm()
            print("\nTot ziens! Bedankt voor het gebruiken van Danny Toolkit.\n")
            break

        elif keuze == "i":
            toon_info()

        elif keuze in apps:
            naam, app_class = apps[keuze]
            print(f"\n  Starting {naam}...\n")
            try:
                app = app_class()
                app.run()
            except KeyboardInterrupt:
                print("\n\n  [Onderbroken] Terug naar hoofdmenu...")
            except Exception as e:
                print(f"\n  [FOUT] {e}")
                input("\n  Druk op Enter om terug te gaan...")

        else:
            print("\n  Ongeldige keuze. Probeer opnieuw.")
            input("  Druk op Enter...")


if __name__ == "__main__":
    main()
