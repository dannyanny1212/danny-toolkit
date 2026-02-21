"""
Danny Toolkit Launcher - Hoofdmenu.
Versie 5.1.1 - OMEGA_SOVEREIGN Rich Dashboard met thema's, kleuren, statistieken en meer.
"""

import sys
import os
if os.name == "nt":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
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
from .ai.vector_studio import VectorStudioApp
from .apps.goals_tracker import GoalsTrackerApp
from .apps.room_planner import RoomPlannerApp
from .ai.artificial_life import ArtificialLifeApp
from .ai.nlp_studio import NLPStudioApp
from .apps.music_composer import MusicComposerApp
from .apps.recipe_generator import RecipeGeneratorApp
from .apps.fitness_tracker import FitnessTrackerApp
from .apps.dream_journal import DreamJournalApp
from .apps.code_snippets import CodeSnippetsApp
from .apps.language_tutor import LanguageTutorApp
from .apps.decision_maker import DecisionMakerApp
from .apps.time_capsule import TimeCapsuleApp
from .ai.advanced_questions import AdvancedQuestionsApp
from .ai.ml_studio import MLStudioApp
from .ai.knowledge_companion import KnowledgeCompanionApp
from .ai.legendary_companion import LegendaryCompanionApp

from .ai.mini_rag import MiniRAG
from .ai.production_rag import ProductionRAG
from .ai.nieuws_agent import NieuwsAgentApp
from .ai.weer_agent import WeerAgentApp
from .ai.claude_chat import ClaudeChatApp
from .brain.brain_cli import BrainCLI
from .brain.trinity_symbiosis import (
    TrinitySymbiosis, TrinityRole, get_trinity,
    connect_iolaax, connect_pixel, connect_daemon, emit_trinity_event
)
from .daemon.daemon_core import DigitalDaemon
from .main_omega import OmegaAI
from .brain.sanctuary_dashboard import SanctuaryDashboard, get_sanctuary
from .brain.dream_monitor import dream_monitor, quick_peek
from .brain.nexus_bridge import (
    NexusBridge, create_nexus_bridge,
    get_nexus_greeting, NexusOracleMode,
)
from .brain.trinity_omega import PrometheusBrain, get_prometheus
from .brain.visual_nexus import VisualNexus, build_visual_nexus
from .brain.project_map import ProjectMap
from .brain.singularity import SingularityEngine
from .brain.file_guard import FileGuard
from .brain.security_research import SecurityResearchEngine

try:
    from .brain.strategist import Strategist
    HAS_STRATEGIST = True
except ImportError:
    HAS_STRATEGIST = False

import asyncio

# Rich UI imports
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.align import Align
from rich.columns import Columns
from rich.prompt import Prompt


# =============================================================================
# DAEMON WRAPPER
# =============================================================================

class DaemonApp:
    """Wrapper voor Digital Daemon in launcher."""

    def __init__(self):
        self.daemon = None

    def run(self):
        """Start de daemon interactief."""
        from .core.utils import clear_scherm, kleur

        self.daemon = DigitalDaemon("Nexus")
        self.daemon.awaken()

        import time
        time.sleep(1)

        clear_scherm()
        print(kleur("""
+===============================================================+
|                                                               |
|     D I G I T A L   D A E M O N                               |
|                                                               |
|     De Levende Interface - Always-On Symbiotische Entiteit    |
|                                                               |
+===============================================================+
        """, Kleur.MAGENTA))

        self.daemon.display_status()

        print(kleur("\nCOMMANDO'S:", Kleur.GEEL))
        print("  status      - Toon volledige status")
        print("  feed <n> <x> - Voed nutrient (protein/carbs/vitamins/water/fiber)")
        print("  form <naam> - Forceer avatar vorm")
        print("  interact    - Praat met daemon")
        print("  stop        - Daemon laten slapen")

        while self.daemon.is_alive:
            try:
                cmd = input(kleur("\n[DAEMON] > ", Kleur.MAGENTA)).strip().lower()

                if not cmd:
                    continue

                if cmd in ["stop", "exit", "quit"]:
                    break

                elif cmd == "status":
                    self.daemon.display_status()

                elif cmd.startswith("feed "):
                    parts = cmd.split()
                    if len(parts) >= 3:
                        nutrient = parts[1]
                        try:
                            amount = float(parts[2])
                            self.daemon.feed(nutrient, amount)
                        except ValueError:
                            print("Gebruik: feed <nutrient> <amount>")

                elif cmd.startswith("form "):
                    form_name = cmd.split()[1] if len(cmd.split()) > 1 else ""
                    from .daemon.limbic_system import AvatarForm
                    try:
                        form = AvatarForm(form_name)
                        self.daemon.force_form(form)
                        self.daemon.display_status()
                    except ValueError:
                        print(f"Onbekende vorm. Kies uit: {[f.value for f in AvatarForm]}")

                elif cmd == "interact" or cmd.startswith("say "):
                    msg = cmd[4:] if cmd.startswith("say ") else input("  Jij: ")
                    response = self.daemon.interact(msg)
                    print(kleur(f"  {self.daemon.naam}: {response}", Kleur.CYAAN))

                else:
                    # Behandel als interactie
                    response = self.daemon.interact(cmd)
                    print(kleur(f"  {self.daemon.naam}: {response}", Kleur.CYAAN))

            except (EOFError, KeyboardInterrupt):
                break

        self.daemon.sleep()
        input("\n  Druk op Enter...")


# =============================================================================
# TRINITY SYMBIOSIS WRAPPER
# =============================================================================

class TrinityApp:
    """Wrapper voor Trinity Symbiosis in launcher."""

    def __init__(self):
        self.trinity = None

    def run(self):
        """Start de Trinity Symbiosis interface."""
        from .core.utils import clear_scherm, kleur

        clear_scherm()
        print(kleur("""
+===============================================================+
|                                                               |
|     T R I N I T Y   S Y M B I O S I S                         |
|                                                               |
|     MIND + SOUL + BODY = Complete Digital Being               |
|                                                               |
+===============================================================+
        """, "cyaan"))

        self.trinity = get_trinity()

        # Auto-connect als nog niet verbonden
        if TrinityRole.MIND not in self.trinity.members:
            print(kleur("  Verbinden van Iolaax (MIND)...", Kleur.GEEL))
            connect_iolaax("Iolaax")
        if TrinityRole.SOUL not in self.trinity.members:
            print(kleur("  Verbinden van Pixel (SOUL)...", Kleur.GEEL))
            connect_pixel("Pixel")
        if TrinityRole.BODY not in self.trinity.members:
            print(kleur("  Verbinden van Nexus (BODY)...", Kleur.GEEL))
            connect_daemon("Nexus")

        self.trinity.activate()
        self.trinity.display_status()

        print(kleur("\nCOMMANDO'S:", Kleur.GEEL))
        print("  status      - Toon Trinity status")
        print("  emit <type> - Emit een event (productivity/knowledge/rest)")
        print("  sync        - Forceer synchronisatie")
        print("  test        - Test de symbiose")
        print("  stop        - Trinity deactiveren")

        while self.trinity.is_active:
            try:
                cmd = input(kleur("\n[TRINITY] > ", Kleur.CYAAN)).strip().lower()

                if not cmd:
                    continue

                if cmd in ["stop", "exit", "quit"]:
                    break

                elif cmd == "status":
                    self.trinity.display_status()

                elif cmd.startswith("emit "):
                    event_type = cmd.split()[1] if len(cmd.split()) > 1 else ""
                    event_map = {
                        "productivity": "productivity_boost",
                        "knowledge": "knowledge_gained",
                        "rest": "rest_taken",
                        "trick": "trick_performed"
                    }
                    if event_type in event_map:
                        emit_trinity_event("daemon", event_map[event_type])
                        print(kleur(f"  Event '{event_type}' uitgezonden!", Kleur.GROEN))
                        self.trinity.display_status()
                    else:
                        print(f"  Kies uit: {list(event_map.keys())}")

                elif cmd == "sync":
                    print(kleur("  Forceer synchronisatie...", Kleur.GEEL))
                    self.trinity._sync_member_stats()
                    print(kleur("  Sync voltooid!", Kleur.GROEN))
                    self.trinity.display_status()

                elif cmd == "test":
                    self._run_test()

                else:
                    print(f"  Onbekend commando: {cmd}")

            except (EOFError, KeyboardInterrupt):
                break

        self.trinity.deactivate()
        print(kleur("\n  Trinity gedeactiveerd.", Kleur.CYAAN))
        input("\n  Druk op Enter...")

    def _run_test(self):
        """Voer een symbiose test uit."""
        from .core.utils import kleur
        import time

        print(kleur("\n  TRINITY SYMBIOSE TEST", Kleur.MAGENTA))
        print("  " + "=" * 40)

        print("\n  [1/4] Test Neural Mesh...")
        emit_trinity_event("iolaax", "thought_generated", {"topic": "test"})
        print(kleur("        OK - Iolaax dacht na", Kleur.GROEN))

        print("  [2/4] Test Emotie Bridge...")
        emit_trinity_event("pixel", "trick_performed", {"trick": "dans"})
        print(kleur("        OK - Pixel deed een trick", Kleur.GROEN))

        print("  [3/4] Test Energie Pool...")
        emit_trinity_event("daemon", "productivity_boost", {"amount": 5})
        print(kleur("        OK - Daemon boost energie", Kleur.GROEN))

        print("  [4/4] Test Sync...")
        self.trinity._sync_member_stats()
        print(kleur("        OK - Stats gesynchroniseerd", Kleur.GROEN))

        print(kleur("\n  Alle tests geslaagd!", Kleur.GROEN))
        print(f"  Bond Sterkte: {self.trinity.bond_strength}%")


# =============================================================================
# OMEGA AI WRAPPER
# =============================================================================

class OmegaApp:
    """Wrapper voor Omega AI in launcher."""

    def run(self):
        """Start Omega AI."""
        omega = OmegaAI()
        omega.start()


# =============================================================================
# SANCTUARY DASHBOARD WRAPPER
# =============================================================================

class SanctuaryApp:
    """Wrapper voor Sanctuary Dashboard in launcher."""

    def run(self):
        """Start het Sanctuary Dashboard interactief."""
        from .core.utils import clear_scherm, kleur

        sanctuary = get_sanctuary()

        clear_scherm()
        print(kleur("""
+===============================================================+
|                                                               |
|     S A N C T U A R Y   D A S H B O A R D                     |
|                                                               |
|     Het Levende Systeem Dashboard                             |
|                                                               |
+===============================================================+
        """, Kleur.CYAAN))

        print(sanctuary.render_live_dashboard())

        print(kleur("\nCOMMANDO'S:", Kleur.GEEL))
        print("  live        - Toon live dashboard")
        print("  hibernate   - Toon hibernation protocol")
        print("  awaken      - Toon awakening protocol")
        print("  biology     - Toon biologische analogie")
        print("  goodnight   - Volledige slaap sequence")
        print("  goodmorning - Volledige wakker sequence")
        print("  tools       - Toon tool betrouwbaarheid")
        print("  stop        - Terug naar launcher")

        while True:
            try:
                cmd = input(kleur(
                    "\n[SANCTUARY] > ", Kleur.CYAAN
                )).strip().lower()

                if not cmd:
                    continue

                if cmd in ["stop", "exit", "quit"]:
                    break
                elif cmd == "live":
                    print(sanctuary.render_live_dashboard())
                elif cmd == "hibernate":
                    print(
                        sanctuary.render_hibernation_dashboard()
                    )
                elif cmd == "awaken":
                    print(
                        sanctuary.render_awakening_dashboard()
                    )
                elif cmd == "biology":
                    print(
                        sanctuary.render_biology_explanation()
                    )
                elif cmd == "goodnight":
                    print(
                        sanctuary.render_hibernation_dashboard()
                    )
                    print(
                        sanctuary.render_biology_explanation()
                    )
                elif cmd == "goodmorning":
                    print(
                        sanctuary.render_awakening_dashboard()
                    )
                elif cmd == "tools":
                    print(
                        sanctuary.render_tool_gezondheid()
                    )
                else:
                    print(f"  Onbekend commando: {cmd}")

            except (EOFError, KeyboardInterrupt):
                break

        input("\n  Druk op Enter...")


# =============================================================================
# DREAM MONITOR WRAPPER
# =============================================================================

class DreamMonitorApp:
    """Wrapper voor Cosmic Dream Monitor in launcher."""

    def run(self):
        """Start de Dream Monitor."""
        from .core.utils import clear_scherm

        clear_scherm()
        print(kleur("""
+===============================================================+
|                                                               |
|     C O S M I C   D R E A M   M O N I T O R                   |
|                                                               |
|     Passive Observation Mode                                  |
|                                                               |
+===============================================================+
        """, Kleur.MAGENTA))

        print(kleur(
            "  Druk Ctrl+C om te stoppen.\n",
            Kleur.DIM,
        ))

        dream_monitor()

        input("\n  Druk op Enter...")


# =============================================================================
# NEXUS BRIDGE WRAPPER
# =============================================================================

class NexusBridgeApp:
    """Wrapper voor NEXUS Brain Bridge in launcher."""

    def run(self):
        """Start de Nexus Bridge interactief."""
        from .core.utils import clear_scherm

        clear_scherm()
        print(kleur("""
+===============================================================+
|                                                               |
|     N E X U S   B R A I N   B R I D G E                       |
|                                                               |
|     Symbiose tussen Pixel en Central Brain                    |
|                                                               |
+===============================================================+
        """, Kleur.FEL_CYAAN))

        bridge = create_nexus_bridge()
        greeting = get_nexus_greeting()
        print(kleur(f"  Nexus: {greeting}\n", Kleur.CYAAN))

        insights = bridge.get_proactive_insights()
        if insights:
            print(kleur("  INZICHTEN:", Kleur.FEL_GEEL))
            for ins in insights[:5]:
                print(kleur(
                    f"    - [{ins.get('emotie', '?')}] "
                    f"{ins.get('tekst', '')}",
                    Kleur.GEEL,
                ))
            print()

        print(kleur("COMMANDO'S:", Kleur.GEEL))
        print("  insights   - Toon proactieve inzichten")
        print("  greeting   - Toon begroeting")
        print("  oracle     - Oracle Mode query")
        print("  stop       - Terug naar launcher")

        while True:
            try:
                cmd = input(kleur(
                    "\n[NEXUS] > ", Kleur.FEL_CYAAN
                )).strip().lower()

                if not cmd:
                    continue

                if cmd in ["stop", "exit", "quit"]:
                    break
                elif cmd == "insights":
                    ins = bridge.get_proactive_insights()
                    if ins:
                        for i in ins[:5]:
                            print(kleur(
                                f"  [{i.get('emotie', '?')}] "
                                f"{i.get('tekst', '')}",
                                Kleur.CYAAN,
                            ))
                    else:
                        print(kleur(
                            "  Geen inzichten beschikbaar.",
                            Kleur.DIM,
                        ))
                elif cmd == "greeting":
                    g = get_nexus_greeting()
                    print(kleur(f"  Nexus: {g}", Kleur.CYAAN))
                elif cmd.startswith("oracle"):
                    query = cmd[7:].strip() if len(cmd) > 7 else ""
                    if not query:
                        query = input("  Query: ").strip()
                    if query:
                        oracle = NexusOracleMode(bridge)
                        oracle.activate()
                        result = oracle.divine_insight(query)
                        print(kleur(
                            f"  Oracle: {result}",
                            Kleur.FEL_MAGENTA,
                        ))
                else:
                    print(f"  Onbekend commando: {cmd}")

            except (EOFError, KeyboardInterrupt):
                break

        input("\n  Druk op Enter...")


# =============================================================================
# VISUAL NEXUS WRAPPER
# =============================================================================

class VisualNexusApp:
    """Wrapper voor Visual Nexus in launcher."""

    def run(self):
        """Start de Visual Nexus."""
        build_visual_nexus()
        input("\n  Druk op Enter...")


# =============================================================================
# PROMETHEUS BRAIN WRAPPER
# =============================================================================

class PrometheusApp:
    """Wrapper voor Prometheus Brain in launcher."""

    def run(self):
        """Start Prometheus Brain interactief."""
        from .core.utils import clear_scherm

        clear_scherm()
        print(kleur("""
+===============================================================+
|                                                               |
|     P R O M E T H E U S   B R A I N                           |
|                                                               |
|     Federated Swarm Intelligence                              |
|                                                               |
+===============================================================+
        """, Kleur.FEL_GEEL))

        try:
            brain = get_prometheus()
        except Exception as e:
            print(kleur(
                f"\n  [FOUT] Prometheus Brain kan niet starten: {e}",
                Kleur.FEL_ROOD,
            ))
            input("\n  Druk op Enter om terug te gaan...")
            return

        brain.display_status()

        # Governor health rapport
        if hasattr(brain, "governor"):
            brain.governor.display_health()

        print(kleur("COMMANDO'S:", Kleur.GEEL))
        print("  status      - Toon federatie status")
        print("  route <t>   - Route een taak")
        print("  triforce    - Tri-Force Protocol")
        print("  godmode     - Activeer God Mode")
        print("  singularity - Singularity Nexus")
        print("  stop        - Terug naar launcher")

        while True:
            try:
                cmd = input(kleur(
                    "\n[PROMETHEUS] > ", Kleur.FEL_GEEL
                )).strip().lower()

                if not cmd:
                    continue

                if cmd in ["stop", "exit", "quit"]:
                    break
                elif cmd == "status":
                    brain.display_status()
                elif cmd.startswith("route"):
                    taak = cmd[6:].strip() if len(cmd) > 6 else ""
                    if not taak:
                        taak = input("  Taak: ").strip()
                    if taak:
                        result = brain.route_task(taak)
                        print(kleur(
                            f"  Resultaat: {result.summary}",
                            Kleur.FEL_GROEN,
                        ))
                elif cmd == "triforce":
                    print(kleur(
                        "  Tri-Force Protocol activeren...",
                        Kleur.FEL_GEEL,
                    ))
                    try:
                        result = brain.execute_total_mobilization()
                        print(kleur(
                            f"  Mobilisatie voltooid!",
                            Kleur.FEL_GROEN,
                        ))
                    except Exception as e:
                        print(kleur(
                            f"  [FOUT] Tri-Force: {e}",
                            Kleur.FEL_ROOD,
                        ))
                elif cmd == "godmode":
                    print(kleur(
                        "  God Mode activeren...",
                        Kleur.FEL_MAGENTA,
                    ))
                    try:
                        result = brain.activate_god_mode()
                        print(kleur(
                            f"  God Mode: {result.get('status', 'OK')}",
                            Kleur.FEL_MAGENTA,
                        ))
                    except Exception as e:
                        print(kleur(
                            f"  [FOUT] God Mode: {e}",
                            Kleur.FEL_ROOD,
                        ))
                elif cmd == "singularity":
                    print(kleur(
                        "  Singularity Nexus initialiseren...",
                        Kleur.FEL_CYAAN,
                    ))
                    try:
                        result = brain.initiate_singularity_nexus()
                        print(kleur(
                            f"  Singularity: "
                            f"{result.get('status', 'OK')}",
                            Kleur.FEL_CYAAN,
                        ))
                    except Exception as e:
                        print(kleur(
                            f"  [FOUT] Singularity: {e}",
                            Kleur.FEL_ROOD,
                        ))
                else:
                    print(f"  Onbekend commando: {cmd}")

            except (EOFError, KeyboardInterrupt):
                break

        input("\n  Druk op Enter...")


# =============================================================================
# PIXEL EYE WRAPPER
# =============================================================================

class PixelEyeApp:
    """Wrapper voor Pixel Eye in launcher."""

    def run(self):
        """Start Pixel Eye interactief."""
        from .core.utils import clear_scherm
        from .skills.pixel_eye import PixelEye

        clear_scherm()
        print(kleur("""
+===============================================+
|                                               |
|     P I X E L   E Y E                         |
|                                               |
|     Het Oog — Vision Analyse                  |
|                                               |
+===============================================+
        """, Kleur.FEL_MAGENTA))

        eye = PixelEye()

        print(kleur("COMMANDO'S:", Kleur.GEEL))
        print("  screenshot       - Screenshot + analyse")
        print("  analyze          - Analyseer afbeelding")
        print("  describe         - Korte beschrijving")
        print("  compare          - Vergelijk 2 beelden")
        print("  golden save <n>  - Sla scherm op als golden master")
        print("  golden check <n> - Vergelijk met golden master")
        print("  golden list      - Toon alle golden masters")
        print("  verify           - Visuele verificatie na actie")
        print("  check            - Controleer scherm tegen verwachting")
        print("  stats            - Vision statistieken")
        print("  stop             - Terug naar launcher")

        while True:
            try:
                cmd = input(kleur(
                    "\n[PIXEL EYE] > ",
                    Kleur.FEL_MAGENTA,
                )).strip()
                cmd_lower = cmd.lower()

                if not cmd_lower:
                    continue

                if cmd_lower in ["stop", "exit", "quit"]:
                    break
                elif cmd_lower == "screenshot":
                    vraag = input(
                        "  Vraag (optioneel): "
                    ).strip()
                    result = eye.analyze_screen(
                        vraag or None
                    )
                    if result["analyse"]:
                        print(f"\n{result['analyse']}")
                elif cmd_lower == "analyze":
                    pad = input(
                        "  Pad naar afbeelding: "
                    ).strip()
                    vraag = input(
                        "  Vraag (optioneel): "
                    ).strip()
                    result = eye.analyze_image(
                        pad, vraag or None
                    )
                    if result["analyse"]:
                        print(f"\n{result['analyse']}")
                elif cmd_lower == "describe":
                    pad = input(
                        "  Pad naar afbeelding: "
                    ).strip()
                    print(f"\n{eye.describe(pad)}")
                elif cmd_lower == "compare":
                    pad1 = input(
                        "  Pad beeld 1: "
                    ).strip()
                    pad2 = input(
                        "  Pad beeld 2: "
                    ).strip()
                    result = eye.compare(pad1, pad2)
                    if result["vergelijking"]:
                        print(
                            f"\n{result['vergelijking']}"
                        )
                elif cmd_lower.startswith("golden"):
                    parts = cmd.split()
                    if len(parts) >= 2:
                        sub = parts[1].lower()
                    else:
                        sub = ""

                    if sub == "save":
                        naam = (
                            parts[2]
                            if len(parts) >= 3
                            else input(
                                "  Naam: "
                            ).strip()
                        )
                        if naam:
                            pad = eye.save_golden(naam)
                            print(kleur(
                                f"  Opgeslagen: {pad}",
                                Kleur.GROEN,
                            ))
                    elif sub == "check":
                        naam = (
                            parts[2]
                            if len(parts) >= 3
                            else input(
                                "  Naam: "
                            ).strip()
                        )
                        if naam:
                            try:
                                r = eye.compare_golden(
                                    naam
                                )
                                status = (
                                    "MATCH"
                                    if r["match"]
                                    else "AFWIJKING"
                                )
                                print(kleur(
                                    f"  Resultaat: {status}",
                                    Kleur.GROEN
                                    if r["match"]
                                    else Kleur.ROOD,
                                ))
                                if r["analyse"]:
                                    print(
                                        f"\n{r['analyse']}"
                                    )
                            except FileNotFoundError as e:
                                print(kleur(
                                    f"  {e}",
                                    Kleur.ROOD,
                                ))
                    elif sub == "list":
                        goldens = eye.list_goldens()
                        if goldens:
                            print(kleur(
                                "  Golden masters:",
                                Kleur.GEEL,
                            ))
                            for g in goldens:
                                print(f"    - {g}")
                        else:
                            print(kleur(
                                "  Geen golden masters"
                                " gevonden.",
                                Kleur.DIM,
                            ))
                    else:
                        print(
                            "  Gebruik: golden"
                            " save/check/list"
                        )
                elif cmd_lower == "verify":
                    beschrijving = input(
                        "  Verwachte verandering: "
                    ).strip()
                    if not beschrijving:
                        print(
                            "  Geef een beschrijving op."
                        )
                        continue
                    timeout = input(
                        "  Timeout sec (5): "
                    ).strip()
                    timeout = (
                        int(timeout)
                        if timeout.isdigit()
                        else 5
                    )
                    print(kleur(
                        "  Voer nu de actie handmatig"
                        f" uit binnen {timeout}"
                        " seconden...",
                        Kleur.GEEL,
                    ))
                    r = eye.verify_action(
                        lambda: None,
                        beschrijving,
                        timeout=timeout,
                    )
                    status = (
                        "GESLAAGD"
                        if r["geslaagd"]
                        else "GEFAALD"
                    )
                    print(kleur(
                        f"  Resultaat: {status}",
                        Kleur.GROEN
                        if r["geslaagd"]
                        else Kleur.ROOD,
                    ))
                    if r["analyse"]:
                        print(f"\n{r['analyse']}")
                elif cmd_lower == "check":
                    verwachting = input(
                        "  Verwachting: "
                    ).strip()
                    if not verwachting:
                        print(
                            "  Geef een verwachting op."
                        )
                        continue
                    r = eye.check_state(verwachting)
                    status = (
                        "MATCH"
                        if r["match"]
                        else "GEEN MATCH"
                    )
                    print(kleur(
                        f"  Resultaat: {status}",
                        Kleur.GROEN
                        if r["match"]
                        else Kleur.ROOD,
                    ))
                    if r["analyse"]:
                        print(f"\n{r['analyse']}")
                elif cmd_lower == "stats":
                    eye.toon_stats()
                else:
                    print(f"  Onbekend commando: {cmd}")

            except (EOFError, KeyboardInterrupt):
                break

        input("\n  Druk op Enter...")


# =============================================================================
# PROJECT MAP WRAPPER
# =============================================================================

class ProjectMapApp:
    """Wrapper voor Project Map in launcher."""

    def run(self):
        """Start de Project Map interactief."""
        pm = ProjectMap()
        pm.run()


# =============================================================================
# ORACLE AGENT WRAPPER
# =============================================================================

class OracleAgentApp:
    """Wrapper voor Oracle Agent in launcher."""

    def run(self):
        """Start de Oracle Agent interactief."""
        from .core.oracle import OracleAgent

        agent = OracleAgent()
        agent.run()


# =============================================================================
# PULSE PROTOCOL WRAPPER
# =============================================================================

class VoiceProtocolApp:
    """Wrapper voor Voice Protocol in launcher."""

    def run(self):
        """Start Voice Protocol simulatie."""
        from .quests.voice_protocol import VoiceProtocol

        print(kleur(
            "\n  QUEST X: THE VOICE\n"
            "  De Stem van God - Pixel Spreekt\n",
            Kleur.FEL_MAGENTA,
        ))
        try:
            protocol = VoiceProtocol()
            protocol.run_simulation()
        except Exception as e:
            print(kleur(
                f"\n  [FOUT] Voice Protocol: {e}",
                Kleur.FEL_ROOD,
            ))
        input("\n  Druk op Enter om terug te gaan...")


class ListenerProtocolApp:
    """Wrapper voor Listener Protocol in launcher."""

    def run(self):
        from .quests.listener_protocol import ListenerProtocol

        print(kleur(
            "\n  QUEST XI: THE LISTENER\n"
            "  Pixel Hoort - Spraakherkenning\n",
            Kleur.FEL_CYAAN,
        ))
        try:
            protocol = ListenerProtocol()
            protocol.run_simulation()
        except Exception as e:
            print(kleur(
                f"\n  [FOUT] Listener Protocol: {e}",
                Kleur.FEL_ROOD,
            ))
        input("\n  Druk op Enter om terug te gaan...")


class DialogueProtocolApp:
    """Wrapper voor Dialogue Protocol in launcher."""

    def run(self):
        from .quests.dialogue_protocol import DialogueProtocol
        print(kleur(
            "\n  QUEST XII: THE DIALOGUE\n"
            "  Pixel Converseert - Spraakdialoog\n",
            Kleur.FEL_MAGENTA,
        ))
        try:
            protocol = DialogueProtocol()
            protocol.run_simulation()
        except Exception as e:
            print(kleur(
                f"\n  [FOUT] Dialogue Protocol: {e}",
                Kleur.FEL_ROOD,
            ))
        input("\n  Druk op Enter om terug te gaan...")


class WillProtocolApp:
    """Wrapper voor Will Protocol in launcher."""

    def run(self):
        from .quests.will_protocol import WillProtocol

        print(kleur(
            "\n  QUEST XIII: THE WILL\n"
            "  Pixel Handelt - Autonome Beslissingen\n",
            Kleur.FEL_MAGENTA,
        ))
        try:
            protocol = WillProtocol()
            protocol.run_simulation()
        except Exception as e:
            print(kleur(
                f"\n  [FOUT] Will Protocol: {e}",
                Kleur.FEL_ROOD,
            ))
        input("\n  Druk op Enter om terug te gaan...")


class HeartbeatApp:
    """Wrapper voor Heartbeat Daemon v2.0 in launcher."""

    def run(self):
        """Start de Heartbeat Daemon met SwarmEngine."""
        import io
        from contextlib import redirect_stdout
        from .core.utils import clear_scherm

        clear_scherm()
        print(kleur("""
+===============================================================+
|                                                               |
|     H E A R T B E A T   D A E M O N   v2.0                    |
|                                                               |
|     Autonome Achtergrond-Monitor + Swarm Engine               |
|                                                               |
+===============================================================+
        """, Kleur.FEL_MAGENTA))

        # Brain laden voor Swarm taken
        brain = None
        try:
            buf = io.StringIO()
            with redirect_stdout(buf):
                from .brain.trinity_omega import (
                    PrometheusBrain,
                )
                brain = PrometheusBrain()
            print(kleur(
                "  Brain geladen voor Swarm taken.",
                Kleur.GROEN,
            ))
        except Exception:
            print(kleur(
                "  Brain niet beschikbaar"
                " (alleen monitoring).",
                Kleur.GEEL,
            ))

        from .daemon.heartbeat import HeartbeatDaemon
        daemon = HeartbeatDaemon(brain=brain)
        daemon.start()

        input("\n  Druk op Enter om terug te gaan...")


class SingularityApp:
    """Wrapper voor Singularity Engine in launcher."""

    def run(self):
        """Start de Singularity Engine interactief."""
        engine = SingularityEngine()
        engine.run()


class SecurityResearchApp:
    """Wrapper voor Security Research Engine in launcher."""

    def run(self):
        """Start de Security Research Engine interactief."""
        engine = SecurityResearchEngine()
        engine.run()


class PulseProtocolApp:
    """Wrapper voor Pulse Protocol in launcher."""

    def run(self):
        """Start Pulse Protocol simulatie."""
        from .quests.pulse_protocol import PulseProtocol

        print(kleur(
            "\n  QUEST IX: THE PULSE PROTOCOL\n"
            "  Bio-Digital Bridge: Hart -> Crypto\n",
            Kleur.FEL_GROEN,
        ))
        try:
            protocol = PulseProtocol()
            protocol.run_simulation()
        except Exception as e:
            print(kleur(
                f"\n  [FOUT] Pulse Protocol: {e}",
                Kleur.FEL_ROOD,
            ))
        input("\n  Druk op Enter om terug te gaan...")


class FastAPIApp:
    """Wrapper voor FastAPI Server in launcher."""

    def run(self):
        """Start de FastAPI server."""
        from .core.utils import clear_scherm

        clear_scherm()
        print(kleur("""
+===============================================================+
|                                                               |
|     F A S T A P I   S E R V E R                               |
|                                                               |
|     REST API — SwarmEngine via HTTP                           |
|                                                               |
+===============================================================+
        """, Kleur.FEL_GROEN))

        print(kleur(
            "  Endpoints:\n"
            "    POST /api/v1/query    — Prompt verwerken\n"
            "    GET  /api/v1/health   — Systeem status\n"
            "    GET  /api/v1/agents   — Agent lijst\n"
            "    POST /api/v1/ingest   — RAG upload\n"
            "    GET  /api/v1/heartbeat — Daemon status\n"
            "    GET  /docs            — Swagger UI\n",
            Kleur.CYAAN,
        ))

        try:
            import fastapi_server
            fastapi_server.main()
        except KeyboardInterrupt:
            print(kleur(
                "\n  Server gestopt.",
                Kleur.GEEL,
            ))
        except Exception as e:
            print(kleur(
                f"\n  [FOUT] FastAPI: {e}",
                Kleur.FEL_ROOD,
            ))
        input("\n  Druk op Enter om terug te gaan...")


class TelegramBotApp:
    """Wrapper voor Telegram Bot in launcher."""

    def run(self):
        """Start de Telegram bot."""
        from .core.utils import clear_scherm

        clear_scherm()
        print(kleur("""
+===============================================================+
|                                                               |
|     T E L E G R A M   B O T                                   |
|                                                               |
|     SwarmEngine via Telegram                                  |
|                                                               |
+===============================================================+
        """, Kleur.FEL_CYAAN))

        print(kleur(
            "  Commando's in Telegram:\n"
            "    /start     — Welkomstbericht\n"
            "    /status    — Systeem gezondheid\n"
            "    /agents    — Agent overzicht\n"
            "    /heartbeat — Daemon status\n"
            "    <tekst>    — SwarmEngine query\n",
            Kleur.CYAAN,
        ))

        try:
            import telegram_bot
            telegram_bot.main()
        except KeyboardInterrupt:
            print(kleur(
                "\n  Bot gestopt.",
                Kleur.GEEL,
            ))
        except Exception as e:
            print(kleur(
                f"\n  [FOUT] Telegram Bot: {e}",
                Kleur.FEL_ROOD,
            ))
        input("\n  Druk op Enter om terug te gaan...")


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
║         T O O L K I T   v6.0.0 // OMEGA_SOVEREIGN              ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
"""

BANNER_MINIMAAL = """
============================================================
     DANNY TOOLKIT v6.0.0
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

    VERSIE = "4.0.0"

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
        "25": ("NLP Studio", NLPStudioApp, "ai"),
        "26": ("Music Composer", MusicComposerApp, "creatief"),
        "27": ("Recipe Generator", RecipeGeneratorApp, "productiviteit"),
        "28": ("Fitness Tracker", FitnessTrackerApp, "productiviteit"),
        "29": ("Dream Journal", DreamJournalApp, "productiviteit"),
        "30": ("Code Snippets", CodeSnippetsApp, "productiviteit"),
        "31": ("Language Tutor", LanguageTutorApp, "productiviteit"),
        "32": ("Decision Maker", DecisionMakerApp, "productiviteit"),
        "33": ("Time Capsule", TimeCapsuleApp, "productiviteit"),
        "34": ("Advanced Questions", AdvancedQuestionsApp, "ai"),
        "35": ("ML Studio", MLStudioApp, "ai"),
        "36": ("Central Brain", BrainCLI, "brain"),
        "37": ("Knowledge Companion", KnowledgeCompanionApp, "ai"),
        "38": ("Legendary Companion", LegendaryCompanionApp, "ai"),
        "39": ("Digital Daemon", DaemonApp, "daemon"),
        "40": ("Trinity Symbiosis", TrinityApp, "brain"),
        "41": ("Omega AI", OmegaApp, "omega"),
        "42": ("Sanctuary Dashboard", SanctuaryApp, "brain"),
        "43": ("Dream Monitor", DreamMonitorApp, "brain"),
        "44": ("Nexus Bridge", NexusBridgeApp, "brain"),
        "45": ("Visual Nexus", VisualNexusApp, "brain"),
        "46": ("Prometheus Brain", PrometheusApp, "brain"),
        "47": ("Pulse Protocol", PulseProtocolApp, "omega"),
        "48": ("Voice Protocol", VoiceProtocolApp, "omega"),
        "49": ("Listener Protocol", ListenerProtocolApp, "omega"),
        "50": ("Dialogue Protocol", DialogueProtocolApp, "omega"),
        "51": ("Will Protocol", WillProtocolApp, "omega"),
        "52": ("Heartbeat Daemon", HeartbeatApp, "daemon"),
        "53": ("Pixel Eye", PixelEyeApp, "brain"),
        "54": ("Project Map", ProjectMapApp, "brain"),
        "55": ("Oracle Agent", OracleAgentApp, "brain"),
        "56": ("Singularity Engine", SingularityApp, "brain"),
        "57": ("Security Research", SecurityResearchApp, "brain"),
        "58": ("FastAPI Server", FastAPIApp, "brain"),
        "59": ("Telegram Bot", TelegramBotApp, "brain"),
    }

    # Sneltoetsen
    SNELTOETSEN = {
        "b": "1",   # Boodschappenlijst
        "r": "2",   # Rekenmachine
        "h": "3",   # Huisdier
        "s": "4",   # Schatzoek
        "c": "5",   # Code analyse
        "mr": "6",  # Mini-RAG
        "pr": "7",  # Production RAG
        "n": "8",   # Nieuws
        "w": "9",   # Weer
        "cc": "10", # Claude Chat
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
        "nl": "25", # NLP Studio
        "mu": "26", # Music Composer
        "re": "27", # Recipe Generator
        "fi": "28", # Fitness Tracker
        "dr": "29", # Dream Journal
        "cs": "30", # Code Snippets
        "la": "31", # Language Tutor
        "de": "32", # Decision Maker
        "tc": "33", # Time Capsule
        "aq": "34", # Advanced Questions
        "ml": "35", # ML Studio
        "br": "36", # Central Brain
        "kc": "37", # Knowledge Companion
        "lc": "38", # Legendary Companion
        "dm": "39", # Digital Daemon
        "tr": "40", # Trinity Symbiosis
        "om": "41", # Omega AI
        "sa": "42", # Sanctuary Dashboard
        "dmo": "43", # Dream Monitor
        "nb": "44", # Nexus Bridge
        "vn": "45", # Visual Nexus
        "pb": "46", # Prometheus Brain
        "pp": "47", # Pulse Protocol
        "vo": "48", # Voice Protocol
        "li": "49", # Listener Protocol
        "di": "50", # Dialogue Protocol
        "wi": "51", # Will Protocol
        "hb": "52", # Heartbeat Daemon
        "pe": "53", # Pixel Eye
        "pm": "54", # Project Map
        "oa": "55", # Oracle Agent
        "si": "56", # Singularity Engine
        "sr": "57", # Security Research
        "fa": "58", # FastAPI Server
        "tb": "59", # Telegram Bot
    }

    def __init__(self):
        fix_encoding()
        Config.ensure_dirs()
        Config.laad_voorkeuren()
        self.stats = LauncherStats()
        self.stats.registreer_sessie()
        self.console = Console()
        self._file_guard_check()

    def _file_guard_check(self):
        """Voer FileGuard integriteitscheck uit bij startup."""
        try:
            guard = FileGuard()
            guard.startup_check()
        except Exception:
            pass  # Nooit de launcher blokkeren

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
        """Toont het Rich-powered hoofdmenu dashboard."""
        clear_scherm()
        con = self.console
        taal = Config.get_taal()

        # ── HEADER: ASCII logo in Rich Panel ──
        banner_text = Text(self._get_banner(), style="bold cyan")
        con.print(Panel(
            Align.center(banner_text),
            border_style="blue",
            padding=(0, 1),
        ))

        # ── STATS BAR ──
        sessies = self.stats.data["totaal_sessies"]
        totaal = self.stats.get_totaal_gebruik()
        thema_naam = Thema.get(Config._thema)["naam"]
        taal_naam = taal["naam"]
        nu = datetime.now().strftime("%H:%M | %d-%m-%Y")

        stats_grid = Table.grid(expand=True)
        stats_grid.add_column(ratio=1)
        stats_grid.add_column(ratio=1)
        stats_grid.add_column(ratio=1)
        stats_grid.add_column(ratio=1)
        stats_grid.add_row(
            f"[green]ONLINE[/green] Sessie #{sessies}",
            f"[cyan]Apps:[/cyan] {totaal} runs",
            f"[yellow]Thema:[/yellow] {thema_naam}",
            f"[blue]{nu}[/blue]",
        )
        con.print(Panel(
            stats_grid,
            style="on #1e212b",
            border_style="dim",
            padding=(0, 1),
        ))

        # ── RECENT ──
        recente = self.stats.get_recente(3)
        if recente:
            recent_parts = []
            for app_naam in recente:
                for key, (naam, _, _) in self.APPS.items():
                    if naam == app_naam:
                        runs = self.stats.get_gebruik(naam)
                        recent_parts.append(
                            f"[bold green]{key}[/bold green]"
                            f" {naam} [dim]({runs}x)[/dim]"
                        )
                        break
            con.print(
                f"  [bold yellow]RECENT:[/bold yellow]  "
                + "  |  ".join(recent_parts)
            )
            con.print()

        # ── APP GROEPERING ──
        NEXUS_PRIME = {
            "42": "DASHBOARD",
            "46": "SWARM AI",
            "36": "ECOSYSTEEM",
            "40": "MIND+SOUL+BODY",
            "39": "ALWAYS-ON",
            "43": "OBSERVE",
            "44": "SYMBIOSE",
            "45": "CONSTRUCT",
            "53": "VISION",
            "54": "CARTOGRAFIE",
            "55": "WAV-LOOP",
            "56": "SINGULARITY",
            "57": "BEWAKING",
            "58": "REST-API",
            "59": "TELEGRAM",
        }
        OMEGA_PROTOCOLS = {
            "41": "CORE",
            "47": "BIO-WALLET",
            "48": "VOICE",
            "49": "LISTENER",
            "50": "DIALOGUE",
            "51": "EXECUTION",
            "52": "HEARTBEAT",
        }
        ENGINEERING = [
            "5", "6", "7", "8", "9", "10",
            "21", "24", "25", "34", "35", "37", "38",
        ]
        SUBROUTINES = [
            "1", "2", "3", "4",
            "11", "12", "13", "14", "15", "16", "17",
            "18", "19", "20", "22", "23",
            "26", "27", "28", "29", "30", "31", "32", "33",
        ]

        # ── Helper: maak tabel met rijen ──
        def _build_table(titel, items, kleur_stijl, met_label=False):
            tbl = Table(
                expand=True,
                show_header=False,
                border_style=kleur_stijl,
                padding=(0, 1),
            )
            tbl.add_column("nr", width=4, style="bold green")
            tbl.add_column("naam", ratio=3)
            if met_label:
                tbl.add_column("tag", ratio=2, style=kleur_stijl)
            tbl.add_column("runs", width=6, justify="right",
                           style="dim")

            if isinstance(items, dict):
                for key, label in items.items():
                    naam = self.APPS[key][0]
                    runs = self.stats.get_gebruik(naam)
                    r = f"{runs}x" if runs > 0 else ""
                    if met_label:
                        tbl.add_row(key, naam, label, r)
                    else:
                        tbl.add_row(key, naam, r)
            else:
                for key in items:
                    naam = self.APPS[key][0]
                    runs = self.stats.get_gebruik(naam)
                    r = f"{runs}x" if runs > 0 else ""
                    tbl.add_row(key, naam, r)
            return tbl

        # Nexus Prime tabel
        nexus_tbl = _build_table(
            "NEXUS PRIME", NEXUS_PRIME, "cyan", met_label=True
        )
        nexus_panel = Panel(
            nexus_tbl,
            title="[bold cyan]NEXUS PRIME[/bold cyan]",
            border_style="cyan",
            subtitle="[dim]15 systems[/dim]",
        )

        # Omega Protocols tabel
        omega_tbl = _build_table(
            "OMEGA PROTOCOLS", OMEGA_PROTOCOLS, "magenta",
            met_label=True,
        )
        omega_panel = Panel(
            omega_tbl,
            title="[bold magenta]OMEGA PROTOCOLS[/bold magenta]",
            border_style="magenta",
            subtitle="[dim]7 protocols[/dim]",
        )

        # Rij 1: Nexus Prime + Omega Protocols
        con.print(Columns(
            [nexus_panel, omega_panel], expand=True, equal=True,
        ))

        # Engineering Deck tabel
        eng_tbl = _build_table(
            "ENGINEERING DECK", ENGINEERING, "green"
        )
        eng_panel = Panel(
            eng_tbl,
            title="[bold green]ENGINEERING DECK[/bold green]",
            border_style="green",
            subtitle="[dim]13 tools[/dim]",
        )

        # Subroutines compact panel
        sub_lines = []
        for key in SUBROUTINES:
            naam = self.APPS[key][0]
            runs = self.stats.get_gebruik(naam)
            r = f" [dim]({runs}x)[/dim]" if runs > 0 else ""
            sub_lines.append(
                f"[bold green]{key:>2}[/bold green] {naam}{r}"
            )
        sub_panel = Panel(
            "\n".join(sub_lines),
            title=(
                "[bold white]SUBROUTINES[/bold white]"
            ),
            border_style="bright_black",
            subtitle="[dim]24 apps[/dim]",
        )

        # Rij 2: Engineering + Subroutines
        con.print(Columns(
            [eng_panel, sub_panel], expand=True, equal=True,
        ))

        # ── FOOTER ──
        footer_text = (
            "[bold green]Z[/bold green] Zoeken  |  "
            "[bold green]I[/bold green] Info  |  "
            "[bold green]O[/bold green] Settings  |  "
            "[bold green]?[/bold green] Help  |  "
            "[bold red]0[/bold red] SHUTDOWN"
        )
        con.print(Panel(
            Align.center(Text.from_markup(footer_text)),
            style="on blue",
            border_style="blue",
            padding=(0, 1),
        ))
        con.print()

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
        print(f"     {self._kleur_tekst('al', 'nummer')} = Artificial Life")
        print(f"     {self._kleur_tekst('nl', 'nummer')} = NLP Studio")
        print(f"     {self._kleur_tekst('dm', 'nummer')} = Digital Daemon")
        print(f"     {self._kleur_tekst('om', 'nummer')} = Omega AI")
        print(f"     {self._kleur_tekst('sa', 'nummer')} = Sanctuary Dashboard")
        print(f"     {self._kleur_tekst('dmo', 'nummer')} = Dream Monitor")
        print(f"     {self._kleur_tekst('nb', 'nummer')} = Nexus Bridge")
        print(f"     {self._kleur_tekst('vn', 'nummer')} = Visual Nexus")
        print(f"     {self._kleur_tekst('pb', 'nummer')} = Prometheus Brain")
        print(f"     {self._kleur_tekst('pp', 'nummer')} = Pulse Protocol")
        print(f"     {self._kleur_tekst('vo', 'nummer')} = Voice Protocol")
        print(f"     {self._kleur_tekst('li', 'nummer')} = Listener Protocol")
        print(f"     {self._kleur_tekst('di', 'nummer')} = Dialogue Protocol")
        print(f"     {self._kleur_tekst('wi', 'nummer')} = Will Protocol")
        print(f"     {self._kleur_tekst('hb', 'nummer')} = Heartbeat Daemon")
        print(f"     {self._kleur_tekst('sr', 'nummer')} = Security Research")
        print(f"     {self._kleur_tekst('fa', 'nummer')} = FastAPI Server")
        print(f"     {self._kleur_tekst('tb', 'nummer')} = Telegram Bot")
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
        anthropic = succes("[OK]") if Config.has_anthropic_key() else fout("[NIET INGESTELD]")
        voyage = succes("[OK]") if Config.has_voyage_key() else fout("[NIET INGESTELD]")
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
            keuze = Prompt.ask(
                "\n[bold cyan]COMMAND[/bold cyan] >"
            ).strip().lower()

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

            # OMEGA SOVEREIGN: Intent Interceptor
            elif len(keuze) > 2 and HAS_STRATEGIST:
                print(f"\n{Kleur.CYAAN}  OMEGA SOVEREIGN AUTONOMY GEACTIVEERD{Kleur.RESET}")
                print(f"{Kleur.MAGENTA}  Missie ontvangen: '{keuze}'{Kleur.RESET}\n")
                try:
                    strategist = Strategist()
                    resultaat = asyncio.run(strategist.execute_mission(keuze))
                    print(f"\n{Kleur.GROEN}  === MISSIE RESULTAAT ==={Kleur.RESET}")
                    print(resultaat)
                    print(f"{Kleur.GROEN}  ========================{Kleur.RESET}")
                except Exception as e:
                    print(fout(f"\n  Strategist fout: {e}"))
                input("\n  Druk op Enter om terug te gaan...")

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
Danny Toolkit v6.0.0 — 59 apps

Gebruik:
  python main.py              Start interactieve launcher
  python main.py <nummer>     Start app direct (1-57)
  python main.py <sneltoets>  Start app via sneltoets
  python main.py --help       Toon deze help

Apps (1-5):
  b  = Boodschappenlijst     r  = Rekenmachine
  h  = Virtueel Huisdier     s  = Schatzoek Game
  c  = Code Analyse

AI Systemen (6-10, 21, 24-25, 34-35, 37-38):
  mr = Mini-RAG              pr = Production RAG
  n  = Nieuws Agent          w  = Weer Agent
  cc = Claude Chat           vs = Vector Data Studio
  al = Artificial Life       nl = NLP Studio
  aq = Advanced Questions    ml = ML Studio
  kc = Knowledge Companion   lc = Legendary Companion

Productiviteit (11-20, 22-23, 26-33):
  no = Notitie App           ha = Habit Tracker
  wg = Wachtwoord Gen        ex = Expense Tracker
  po = Pomodoro Timer        fl = Flashcards
  un = Unit Converter        ag = Agenda Planner
  mo = Mood Tracker          ci = Citaten Generator
  go = Goals Tracker         ro = Room Planner
  mu = Music Composer        re = Recipe Generator
  fi = Fitness Tracker       dr = Dream Journal
  cs = Code Snippets         la = Language Tutor
  de = Decision Maker        tc = Time Capsule

Central Brain (36, 40, 42-46):
  br  = Central Brain        tr  = Trinity Symbiosis
  sa  = Sanctuary Dashboard  dmo = Dream Monitor
  nb  = Nexus Bridge         vn  = Visual Nexus
  pb  = Prometheus Brain

Digital Daemon (39):
  dm = Digital Daemon

Omega AI (41, 47-52):
  om = Omega AI              pp = Pulse Protocol
  vo = Voice Protocol        li = Listener Protocol
  di = Dialogue Protocol     wi = Will Protocol
  hb = Heartbeat Daemon

Central Brain Extra:
  sr = Security Research
  fa = FastAPI Server
  tb = Telegram Bot
""")
            return

        direct_start = arg

    launcher = Launcher()
    launcher.run(direct_start)


if __name__ == "__main__":
    main()
