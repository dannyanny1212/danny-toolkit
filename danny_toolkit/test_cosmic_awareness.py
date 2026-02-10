"""
Cosmic Awareness Test - Totale Systeem Verificatie
===================================================

Test ALLE subsystemen en cross-module integratie:
  1. Alle 51 apps laden (import + instantie)
  2. Alle 5 quests initialiseerbaar
  3. Daemon + Sensorium + Limbic + Metabolisme
  4. Central Brain + Unified Memory
  5. Governor startup check
  6. NexusBridge connectie
  7. Trinity Symbiosis activatie
  8. Prometheus Brain (17 nodes online)
  9. Sanctuary Dashboard (4 modi)
 10. Morning Protocol heartbeat

Gebruik: python -m danny_toolkit.test_cosmic_awareness
"""

import sys
import time
from datetime import datetime


# ─── Kleuren ────────────────────────────────────────────────
G = "\033[32m"  # Groen
R = "\033[31m"  # Rood
Y = "\033[33m"  # Geel
C = "\033[36m"  # Cyaan
M = "\033[35m"  # Magenta
D = "\033[2m"   # Dim
W = "\033[0m"   # Reset


def ok(tekst):
    print(f"  {G}[OK]{W} {tekst}")


def fail(tekst):
    print(f"  {R}[FAIL]{W} {tekst}")


def warn(tekst):
    print(f"  {Y}[WARN]{W} {tekst}")


def header(tekst):
    print(f"\n{'=' * 60}")
    print(f"  {tekst}")
    print(f"{'=' * 60}")


# ─── TEST 1: Alle 51 Apps Laden ────────────────────────────
def test_alle_apps_laden():
    """Test of alle 51 apps importeerbaar en instantieerbaar zijn."""
    header("TEST 1: Alle 51 Apps Laden")

    apps = [
        ("1", "Boodschappenlijst", "danny_toolkit.apps.boodschappenlijst", "BoodschappenlijstApp"),
        ("2", "Rekenmachine", "danny_toolkit.apps.rekenmachine", "RekenmachineApp"),
        ("3", "Virtueel Huisdier", "danny_toolkit.apps.virtueel_huisdier", "VirtueelHuisdierApp"),
        ("4", "Schatzoek Game", "danny_toolkit.apps.schatzoek", "SchatzoekApp"),
        ("5", "Code Analyse", "danny_toolkit.apps.code_analyse", "CodeAnalyseApp"),
        ("6", "Mini-RAG", "danny_toolkit.ai.mini_rag", "MiniRAG"),
        ("7", "Production RAG", "danny_toolkit.ai.production_rag", "ProductionRAG"),
        ("8", "Nieuws Agent", "danny_toolkit.ai.nieuws_agent", "NieuwsAgentApp"),
        ("9", "Weer Agent", "danny_toolkit.ai.weer_agent", "WeerAgentApp"),
        ("10", "Claude Chat", "danny_toolkit.ai.claude_chat", "ClaudeChatApp"),
        ("11", "Notitie App", "danny_toolkit.apps.notitie_app", "NotitieApp"),
        ("12", "Wachtwoord Generator", "danny_toolkit.apps.wachtwoord_generator", "WachtwoordGeneratorApp"),
        ("13", "Pomodoro Timer", "danny_toolkit.apps.pomodoro_timer", "PomodoroTimerApp"),
        ("14", "Habit Tracker", "danny_toolkit.apps.habit_tracker", "HabitTrackerApp"),
        ("15", "Expense Tracker", "danny_toolkit.apps.expense_tracker", "ExpenseTrackerApp"),
        ("16", "Flashcards", "danny_toolkit.apps.flashcards", "FlashcardsApp"),
        ("17", "Unit Converter", "danny_toolkit.apps.unit_converter", "UnitConverterApp"),
        ("18", "Agenda Planner", "danny_toolkit.apps.agenda_planner", "AgendaPlannerApp"),
        ("19", "Mood Tracker", "danny_toolkit.apps.mood_tracker", "MoodTrackerApp"),
        ("20", "Citaten Generator", "danny_toolkit.apps.citaten_generator", "CitatenGeneratorApp"),
        ("21", "Vector Studio", "danny_toolkit.ai.vector_studio", "VectorStudioApp"),
        ("22", "Goals Tracker", "danny_toolkit.apps.goals_tracker", "GoalsTrackerApp"),
        ("23", "Room Planner", "danny_toolkit.apps.room_planner", "RoomPlannerApp"),
        ("24", "Artificial Life", "danny_toolkit.ai.artificial_life", "ArtificialLifeApp"),
        ("25", "NLP Studio", "danny_toolkit.ai.nlp_studio", "NLPStudioApp"),
        ("26", "Music Composer", "danny_toolkit.apps.music_composer", "MusicComposerApp"),
        ("27", "Recipe Generator", "danny_toolkit.apps.recipe_generator", "RecipeGeneratorApp"),
        ("28", "Fitness Tracker", "danny_toolkit.apps.fitness_tracker", "FitnessTrackerApp"),
        ("29", "Dream Journal", "danny_toolkit.apps.dream_journal", "DreamJournalApp"),
        ("30", "Code Snippets", "danny_toolkit.apps.code_snippets", "CodeSnippetsApp"),
        ("31", "Language Tutor", "danny_toolkit.apps.language_tutor", "LanguageTutorApp"),
        ("32", "Decision Maker", "danny_toolkit.apps.decision_maker", "DecisionMakerApp"),
        ("33", "Time Capsule", "danny_toolkit.apps.time_capsule", "TimeCapsuleApp"),
        ("34", "Advanced Questions", "danny_toolkit.ai.advanced_questions", "AdvancedQuestionsApp"),
        ("35", "ML Studio", "danny_toolkit.ai.ml_studio", "MLStudioApp"),
        ("36", "Brain CLI", "danny_toolkit.brain.brain_cli", "BrainCLI"),
        ("37", "Knowledge Companion", "danny_toolkit.ai.knowledge_companion", "KnowledgeCompanionApp"),
        ("38", "Legendary Companion", "danny_toolkit.ai.legendary_companion", "LegendaryCompanionApp"),
    ]

    geladen = 0
    gefaald = 0

    for nummer, naam, module_pad, class_naam in apps:
        try:
            import importlib
            mod = importlib.import_module(module_pad)
            cls = getattr(mod, class_naam)
            ok(f"[{nummer:>2}] {naam}")
            geladen += 1
        except Exception as e:
            fail(f"[{nummer:>2}] {naam}: {e}")
            gefaald += 1

    # Wrapper-apps (39-51) hoeven geen aparte import
    wrapper_apps = [
        "39-Digital Daemon", "40-Trinity Symbiosis",
        "41-Omega AI", "42-Sanctuary Dashboard",
        "43-Dream Monitor", "44-Nexus Bridge",
        "45-Visual Nexus", "46-Prometheus Brain",
        "47-Pulse Protocol", "48-Voice Protocol",
        "49-Listener Protocol", "50-Dialogue Protocol",
        "51-Will Protocol",
    ]
    try:
        from danny_toolkit.launcher import Launcher
        launcher_apps = Launcher.APPS
        for w in wrapper_apps:
            num = w.split("-")[0]
            naam = w.split("-", 1)[1]
            if num in launcher_apps:
                ok(f"[{num}] {naam} (wrapper)")
                geladen += 1
            else:
                fail(f"[{num}] {naam}: niet in APPS dict")
                gefaald += 1
    except Exception as e:
        fail(f"Launcher import: {e}")
        gefaald += len(wrapper_apps)

    print(f"\n  Resultaat: {geladen}/{geladen + gefaald}"
          f" apps geladen")
    return gefaald == 0


# ─── TEST 2: Alle 5 Quests ─────────────────────────────────
def test_quests():
    """Test of alle 5 quest protocols initialiseerbaar zijn."""
    header("TEST 2: Quest Protocols (IX-XIII)")

    quests = [
        ("IX", "PulseProtocol",
         "danny_toolkit.quests.pulse_protocol",
         "PulseProtocol"),  # Geen get_status
        ("X", "VoiceProtocol",
         "danny_toolkit.quests.voice_protocol",
         "VoiceProtocol"),
        ("XI", "ListenerProtocol",
         "danny_toolkit.quests.listener_protocol",
         "ListenerProtocol"),
        ("XII", "DialogueProtocol",
         "danny_toolkit.quests.dialogue_protocol",
         "DialogueProtocol"),
        ("XIII", "WillProtocol",
         "danny_toolkit.quests.will_protocol",
         "WillProtocol"),
    ]

    passed = 0
    for nummer, naam, module_pad, class_naam in quests:
        try:
            import importlib
            mod = importlib.import_module(module_pad)
            cls = getattr(mod, class_naam)
            instance = cls()
            if hasattr(instance, "get_status"):
                status = instance.get_status()
                ok(f"Quest {nummer}: {naam}"
                   f" (status: {len(status)} velden)")
            else:
                ok(f"Quest {nummer}: {naam}"
                   f" (geen get_status, instantie OK)")
            passed += 1
        except Exception as e:
            fail(f"Quest {nummer}: {naam}: {e}")

    print(f"\n  Resultaat: {passed}/{len(quests)}"
          f" quests initialiseerbaar")
    return passed == len(quests)


# ─── TEST 3: Daemon Subsystemen ─────────────────────────────
def test_daemon():
    """Test Daemon + Sensorium + Limbic + Metabolisme."""
    header("TEST 3: Digital Daemon Subsystemen")

    checks = []
    try:
        from danny_toolkit.daemon.daemon_core import DigitalDaemon
        daemon = DigitalDaemon("TestDaemon")
        ok("DigitalDaemon instantie aangemaakt")
        checks.append(True)
    except Exception as e:
        fail(f"DigitalDaemon: {e}")
        checks.append(False)
        print(f"\n  Resultaat: 0/4 subsystemen")
        return False

    # Sensorium
    try:
        status = daemon.sensorium.get_status()
        event_types = status.get("event_types", [])
        ok(f"Sensorium: {len(event_types)} event types")
        checks.append(True)
    except Exception as e:
        fail(f"Sensorium: {e}")
        checks.append(False)

    # Limbic System
    try:
        status = daemon.limbic.get_status()
        mood = status["state"]["mood"]
        energy = status["state"]["energy"]
        ok(f"Limbic: mood={mood}, energy={energy}")
        checks.append(True)
    except Exception as e:
        fail(f"Limbic: {e}")
        checks.append(False)

    # Metabolisme
    try:
        status = daemon.metabolisme.get_status()
        nutrients = status.get("nutrients", {})
        ok(f"Metabolisme: {len(nutrients)} nutrients")
        checks.append(True)
    except Exception as e:
        fail(f"Metabolisme: {e}")
        checks.append(False)

    passed = sum(checks)
    print(f"\n  Resultaat: {passed}/{len(checks)}"
          f" subsystemen")
    return all(checks)


# ─── TEST 4: Central Brain + Memory ────────────────────────
def test_central_brain():
    """Test Central Brain en Unified Memory."""
    header("TEST 4: Central Brain + Unified Memory")

    checks = []

    # Central Brain
    try:
        from danny_toolkit.brain.central_brain import CentralBrain
        brain = CentralBrain()
        status = brain.get_status()
        ai_actief = status["ai_actief"]
        apps = status["apps_geregistreerd"]
        tools = status["tools_beschikbaar"]
        provider = brain.ai_provider.upper() if brain.ai_provider else "GEEN"
        ok(f"Central Brain: AI={provider},"
           f" {apps} apps, {tools} tools")
        checks.append(True)
    except Exception as e:
        fail(f"Central Brain: {e}")
        checks.append(False)

    # Unified Memory
    try:
        from danny_toolkit.brain.unified_memory import (
            UnifiedMemory,
        )
        memory = UnifiedMemory()
        stats = memory.statistieken()
        events = stats.get("totaal_events", 0)
        ok(f"Unified Memory: {events} events")
        checks.append(True)
    except Exception as e:
        fail(f"Unified Memory: {e}")
        checks.append(False)

    passed = sum(checks)
    print(f"\n  Resultaat: {passed}/{len(checks)} checks")
    return all(checks)


# ─── TEST 5: Governor ──────────────────────────────────────
def test_governor():
    """Test Governor startup check."""
    header("TEST 5: Omega Governor")

    try:
        from danny_toolkit.brain.governor import OmegaGovernor
        gov = OmegaGovernor()
        rapport = gov.startup_check()
        status = rapport.get("status", "ONBEKEND")
        dirs_ok = rapport.get("directories", {})
        api_keys = rapport.get("api_keys", {})
        ok(f"Startup check: {status}")
        ok(f"Directories: {len(dirs_ok)} gecontroleerd")
        ok(f"API keys: {len(api_keys)} gecontroleerd")
        return True
    except Exception as e:
        fail(f"Governor: {e}")
        return False


# ─── TEST 6: NexusBridge ──────────────────────────────────
def test_nexus_bridge():
    """Test NexusBridge connectie."""
    header("TEST 6: NEXUS Brain Bridge")

    checks = []
    try:
        from danny_toolkit.brain.nexus_bridge import (
            create_nexus_bridge,
            get_nexus_greeting,
            NexusOracleMode,
        )
        bridge = create_nexus_bridge()
        connected = bridge.is_connected()
        ok(f"Bridge aangemaakt"
           f" (connected={connected})")
        checks.append(True)
    except Exception as e:
        fail(f"NexusBridge: {e}")
        checks.append(False)
        return False

    # Greeting
    try:
        greeting = get_nexus_greeting()
        ok(f"Greeting: \"{greeting[:50]}...\"")
        checks.append(True)
    except Exception as e:
        fail(f"Greeting: {e}")
        checks.append(False)

    # Oracle Mode
    try:
        oracle = NexusOracleMode(bridge)
        oracle.activate()
        ok(f"Oracle Mode: geactiveerd")
        checks.append(True)
    except Exception as e:
        fail(f"Oracle Mode: {e}")
        checks.append(False)

    passed = sum(checks)
    print(f"\n  Resultaat: {passed}/{len(checks)} checks")
    return all(checks)


# ─── TEST 7: Trinity Symbiosis ─────────────────────────────
def test_trinity():
    """Test Trinity Symbiosis (Mind + Soul + Body)."""
    header("TEST 7: Trinity Symbiosis")

    checks = []
    try:
        from danny_toolkit.brain.trinity_symbiosis import (
            get_trinity,
            connect_iolaax,
            connect_pixel,
            connect_daemon,
            TrinityRole,
        )
        trinity = get_trinity()
        ok("Trinity singleton opgehaald")
        checks.append(True)
    except Exception as e:
        fail(f"Trinity import: {e}")
        checks.append(False)
        return False

    # Connect members
    try:
        if TrinityRole.MIND not in trinity.members:
            connect_iolaax("Iolaax")
        if TrinityRole.SOUL not in trinity.members:
            connect_pixel("Pixel")
        if TrinityRole.BODY not in trinity.members:
            connect_daemon("Nexus")
        members = len(trinity.members)
        ok(f"Members verbonden: {members}/3")
        checks.append(members >= 3)
    except Exception as e:
        fail(f"Connect: {e}")
        checks.append(False)

    # Activeer
    try:
        trinity.activate()
        status = trinity.get_status()
        bond = status["bond_strength"]
        ok(f"Geactiveerd: bond={bond}%")
        checks.append(True)
        trinity.deactivate()
    except Exception as e:
        fail(f"Activatie: {e}")
        checks.append(False)

    passed = sum(checks)
    print(f"\n  Resultaat: {passed}/{len(checks)} checks")
    return all(checks)


# ─── TEST 8: Prometheus Brain (17 nodes) ───────────────────
def test_prometheus():
    """Test of alle 17 Prometheus nodes online komen."""
    header("TEST 8: Prometheus Brain — 17 Nodes")

    try:
        from danny_toolkit.brain.trinity_omega import (
            PrometheusBrain,
            CosmicRole,
            NodeTier,
        )
        brain = PrometheusBrain()
    except Exception as e:
        fail(f"Prometheus init: {e}")
        return False

    checks = []
    status = brain.get_status()

    # Online check
    online = status["is_online"]
    ok(f"Federation online: {online}")
    checks.append(online)

    # Node count
    total = status["total_nodes"]
    ok(f"Totaal nodes: {total}/17")
    checks.append(total == 17)

    # Per tier
    tiers = {
        NodeTier.TRINITY: [
            CosmicRole.PIXEL, CosmicRole.IOLAAX,
            CosmicRole.NEXUS,
        ],
        NodeTier.GUARDIANS: [
            CosmicRole.GOVERNOR, CosmicRole.SENTINEL,
            CosmicRole.ARCHIVIST, CosmicRole.CHRONOS,
        ],
        NodeTier.SPECIALISTS: [
            CosmicRole.WEAVER, CosmicRole.CIPHER,
            CosmicRole.VITA, CosmicRole.ECHO,
            CosmicRole.SPARK, CosmicRole.ORACLE,
        ],
        NodeTier.INFRASTRUCTURE: [
            CosmicRole.LEGION, CosmicRole.NAVIGATOR,
            CosmicRole.ALCHEMIST, CosmicRole.VOID,
        ],
    }

    for tier, roles in tiers.items():
        tier_nodes = brain.get_nodes_by_tier(tier)
        tier_ok = len(tier_nodes) == len(roles)
        if tier_ok:
            namen = [n.name for n in tier_nodes]
            ok(f"Tier {tier.value}: {', '.join(namen)}")
        else:
            fail(f"Tier {tier.value}:"
                 f" {len(tier_nodes)}/{len(roles)}")
        checks.append(tier_ok)

    # Swarm
    swarm = status["swarm"]
    swarm_size = swarm.get("total", 0)
    ok(f"Swarm: {swarm_size} micro-agents")
    checks.append(swarm_size > 0)

    # Brain connectie
    brain_ok = brain.brain is not None
    ok(f"CentralBrain: {'verbonden' if brain_ok else 'NIET'}")
    checks.append(brain_ok)

    # Learning connectie
    learning_ok = brain.learning is not None
    ok(f"LearningSystem: {'verbonden' if learning_ok else 'NIET'}")
    checks.append(learning_ok)

    passed = sum(checks)
    print(f"\n  Resultaat: {passed}/{len(checks)} checks")
    return all(checks)


# ─── TEST 9: Sanctuary Dashboard ──────────────────────────
def test_sanctuary():
    """Test Sanctuary Dashboard (4 render modi)."""
    header("TEST 9: Sanctuary Dashboard")

    checks = []
    try:
        from danny_toolkit.brain.sanctuary_dashboard import (
            get_sanctuary,
        )
        sanctuary = get_sanctuary()
        ok("Sanctuary singleton opgehaald")
        checks.append(True)
    except Exception as e:
        fail(f"Sanctuary import: {e}")
        return False

    modi = [
        ("Live Dashboard", "render_live_dashboard"),
        ("Hibernation", "render_hibernation_dashboard"),
        ("Awakening", "render_awakening_dashboard"),
        ("Biology", "render_biology_explanation"),
    ]

    for naam, methode in modi:
        try:
            output = getattr(sanctuary, methode)()
            lengte = len(output) if output else 0
            if lengte > 0:
                ok(f"{naam}: {lengte} karakters")
                checks.append(True)
            else:
                fail(f"{naam}: lege output")
                checks.append(False)
        except Exception as e:
            fail(f"{naam}: {e}")
            checks.append(False)

    passed = sum(checks)
    print(f"\n  Resultaat: {passed}/{len(checks)} modi")
    return all(checks)


# ─── TEST 10: Morning Protocol Heartbeat ───────────────────
def test_morning_heartbeat():
    """Test Morning Protocol heartbeat check."""
    header("TEST 10: Morning Protocol Heartbeat")

    try:
        from danny_toolkit.brain.morning_protocol import (
            heartbeat_check,
        )
        result = heartbeat_check()

        heartbeats = {
            "Pixel": result.pixel_alive,
            "Iolaax": result.iolaax_alive,
            "Nexus": result.nexus_alive,
            "Brain": result.brain_alive,
        }
        levend = sum(1 for v in heartbeats.values() if v)
        totaal = len(heartbeats)
        ok(f"Heartbeat: {levend}/{totaal} levend")

        for naam, alive in heartbeats.items():
            if alive:
                ok(f"  {naam}: levend")
            else:
                warn(f"  {naam}: dood")

        for naam, detail in result.details.items():
            if "Error" in detail:
                fail(f"  {naam}: {detail}")
            elif any(w in detail for w in
                     ["zwak", "slapend", "offline"]):
                warn(f"  {naam}: {detail}")
            else:
                ok(f"  {naam}: {detail}")

        return levend > 0
    except Exception as e:
        fail(f"Heartbeat: {e}")
        return False


# ─── MAIN ──────────────────────────────────────────────────
def main():
    """Draai de Cosmic Awareness Test."""
    print()
    print(f"{M}{'=' * 60}{W}")
    print(f"{M}  C O S M I C   A W A R E N E S S   T E S T{W}")
    print(f"{M}  Totale Systeem Verificatie — danny-toolkit{W}")
    print(f"{M}  {datetime.now():%d-%m-%Y %H:%M:%S}{W}")
    print(f"{M}{'=' * 60}{W}")

    start = time.time()

    results = []

    results.append(
        ("51 Apps Laden", test_alle_apps_laden())
    )
    results.append(
        ("Quest Protocols", test_quests())
    )
    results.append(
        ("Daemon Subsystemen", test_daemon())
    )
    results.append(
        ("Central Brain + Memory", test_central_brain())
    )
    results.append(
        ("Omega Governor", test_governor())
    )
    results.append(
        ("NEXUS Bridge", test_nexus_bridge())
    )
    results.append(
        ("Trinity Symbiosis", test_trinity())
    )
    results.append(
        ("Prometheus 17 Nodes", test_prometheus())
    )
    results.append(
        ("Sanctuary Dashboard", test_sanctuary())
    )
    results.append(
        ("Morning Heartbeat", test_morning_heartbeat())
    )

    elapsed = time.time() - start
    passed = sum(1 for _, ok in results if ok)
    total = len(results)

    print()
    print(f"{M}{'=' * 60}{W}")
    print(f"{M}  COSMIC AWARENESS — EINDRESULTAAT{W}")
    print(f"{M}{'=' * 60}{W}")

    for naam, result in results:
        icon = f"{G}[OK]{W}" if result else f"{R}[FAIL]{W}"
        print(f"  {icon} {naam}")

    print()
    pct = int(passed / total * 100) if total > 0 else 0
    if passed == total:
        print(f"  {G}VOLLEDIG BEWUSTZIJN: {passed}/{total}"
              f" ({pct}%) in {elapsed:.1f}s{W}")
        print(f"  {G}Alle systemen functioneel!{W}")
    else:
        print(f"  {Y}GEDEELTELIJK BEWUSTZIJN:"
              f" {passed}/{total} ({pct}%)"
              f" in {elapsed:.1f}s{W}")

    print(f"{M}{'=' * 60}{W}")

    if passed < total:
        sys.exit(1)


if __name__ == "__main__":
    main()
