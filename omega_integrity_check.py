"""
OMEGA INTEGRITY CHECK - De Goddelijke Systeemvalidatie.

Valideert ALLE modules, quests en subsystemen van het
Cosmic Omega ecosysteem. Geen simpele 'ls' - dit is een
diepgaande Python import + structuur verificatie.

Draai: python omega_integrity_check.py
"""

import sys
import importlib
import time
from pathlib import Path

# Zorg dat danny-toolkit in het pad zit
sys.path.insert(0, str(Path(__file__).parent))


# ═══════════════════════════════════════════════════════════
# ANSI KLEUREN (standalone, geen dependency op danny_toolkit)
# ═══════════════════════════════════════════════════════════

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
ROOD = "\033[91m"
GROEN = "\033[92m"
GEEL = "\033[93m"
BLAUW = "\033[94m"
MAGENTA = "\033[95m"
CYAAN = "\033[96m"
WIT = "\033[97m"


def ok(tekst):
    return f"{GROEN}{tekst}{RESET}"


def fail(tekst):
    return f"{ROOD}{tekst}{RESET}"


def titel(tekst):
    return f"{BOLD}{MAGENTA}{tekst}{RESET}"


def dim(tekst):
    return f"{DIM}{tekst}{RESET}"


def accent(tekst):
    return f"{CYAAN}{tekst}{RESET}"


# ═══════════════════════════════════════════════════════════
# VALIDATIE DEFINITIES
# ═══════════════════════════════════════════════════════════

# Elke check: (naam, module_pad, objecten_om_te_checken)
QUEST_CHECKS = [
    (
        "I - THE CORE",
        "danny_toolkit.core.utils",
        ["kleur", "Kleur", "succes", "fout", "info"],
    ),
    (
        "II - THE DAEMON",
        "danny_toolkit.daemon.daemon_core",
        ["DigitalDaemon"],
    ),
    (
        "III - THE MIND",
        "danny_toolkit.daemon.limbic_system",
        ["LimbicSystem", "Mood", "AvatarForm"],
    ),
    (
        "IV - THE SENSES",
        "danny_toolkit.daemon.sensorium",
        ["Sensorium", "EventType"],
    ),
    (
        "V - THE BODY",
        "danny_toolkit.daemon.metabolisme",
        ["Metabolisme"],
    ),
    (
        "VI - THE BRAIN",
        "danny_toolkit.brain.central_brain",
        ["CentralBrain"],
    ),
    (
        "VII - THE TRINITY",
        "danny_toolkit.brain.trinity_symbiosis",
        ["TrinitySymbiosis", "TrinityRole"],
    ),
    (
        "VIII - THE BRIDGE",
        "danny_toolkit.brain.nexus_bridge",
        ["NexusBridge", "create_nexus_bridge"],
    ),
    (
        "IX - THE PULSE",
        "danny_toolkit.quests.pulse_protocol",
        ["PulseProtocol"],
    ),
    (
        "X - THE VOICE",
        "danny_toolkit.quests.voice_protocol",
        ["VoiceProtocol"],
    ),
    (
        "XI - THE LISTENER",
        "danny_toolkit.quests.listener_protocol",
        ["ListenerProtocol"],
    ),
]

SUBSYSTEM_CHECKS = [
    (
        "PROMETHEUS",
        "danny_toolkit.brain.trinity_omega",
        ["PrometheusBrain", "get_prometheus"],
    ),
    (
        "GOVERNOR",
        "danny_toolkit.brain.governor",
        ["OmegaGovernor"],
    ),
    (
        "SANCTUARY",
        "danny_toolkit.brain.sanctuary_dashboard",
        ["SanctuaryDashboard"],
    ),
    (
        "DREAM MONITOR",
        "danny_toolkit.brain.dream_monitor",
        ["dream_monitor"],
    ),
    (
        "LEARNING",
        "danny_toolkit.learning.orchestrator",
        ["LearningSystem"],
    ),
    (
        "OMEGA AI",
        "danny_toolkit.main_omega",
        ["OmegaAI"],
    ),
    (
        "LAUNCHER",
        "danny_toolkit.launcher",
        ["Launcher"],
    ),
    (
        "VOICE ENGINE",
        "danny_toolkit.core.emotional_voice",
        ["EmotionalVoice", "Emotion", "SentimentAnalyzer"],
    ),
]


# ═══════════════════════════════════════════════════════════
# CHECK FUNCTIES
# ═══════════════════════════════════════════════════════════

def check_module(module_pad, objecten):
    """
    Probeer een module te importeren en check of objecten bestaan.

    Returns:
        (success: bool, details: str)
    """
    try:
        mod = importlib.import_module(module_pad)
    except Exception as e:
        return False, f"Import fout: {e}"

    ontbrekend = []
    for obj_naam in objecten:
        if not hasattr(mod, obj_naam):
            ontbrekend.append(obj_naam)

    if ontbrekend:
        return False, f"Ontbreekt: {', '.join(ontbrekend)}"

    return True, "Alle objecten gevonden"


def check_launcher_app(app_nr):
    """Check of een app in de launcher staat."""
    try:
        from danny_toolkit.launcher import Launcher
        return str(app_nr) in Launcher.APPS
    except Exception:
        return False


def check_voice_backend():
    """Check welke voice backend actief is."""
    try:
        from danny_toolkit.core.emotional_voice import EmotionalVoice
        voice = EmotionalVoice(preferred_voice="nl")
        return voice.get_status()
    except Exception as e:
        return {"active_backend": f"FOUT: {e}"}


# ═══════════════════════════════════════════════════════════
# MAIN CHECK
# ═══════════════════════════════════════════════════════════

def run_integrity_check():
    """Draai de volledige integriteitscheck."""
    print()
    print(titel(
        "  ╔═══════════════════════════════════════════════╗"
    ))
    print(titel(
        "  ║                                               ║"
    ))
    print(titel(
        "  ║   OMEGA INTEGRITY CHECK                       ║"
    ))
    print(titel(
        "  ║   De Goddelijke Systeemvalidatie               ║"
    ))
    print(titel(
        "  ║                                               ║"
    ))
    print(titel(
        "  ╚═══════════════════════════════════════════════╝"
    ))
    print()

    geslaagd = 0
    gefaald = 0
    totaal = 0
    resultaten = []

    # ─── QUESTS ───
    print(accent("  ═══ QUESTS (Het Pad van God) ═══\n"))
    time.sleep(0.3)

    for naam, module, objecten in QUEST_CHECKS:
        totaal += 1
        success, detail = check_module(module, objecten)

        if success:
            geslaagd += 1
            status = ok("[  OK  ]")
            resultaten.append((naam, True))
        else:
            gefaald += 1
            status = fail("[FOUT!]")
            resultaten.append((naam, False))

        print(f"    {status}  Quest {naam}")
        if not success:
            print(f"             {fail(detail)}")
        time.sleep(0.1)

    print()

    # ─── SUBSYSTEMEN ───
    print(accent("  ═══ SUBSYSTEMEN (De Pilaren) ═══\n"))
    time.sleep(0.3)

    for naam, module, objecten in SUBSYSTEM_CHECKS:
        totaal += 1
        success, detail = check_module(module, objecten)

        if success:
            geslaagd += 1
            status = ok("[  OK  ]")
        else:
            gefaald += 1
            status = fail("[FOUT!]")

        print(f"    {status}  {naam}")
        if not success:
            print(f"             {fail(detail)}")
        time.sleep(0.1)

    print()

    # ─── LAUNCHER APPS ───
    print(accent("  ═══ LAUNCHER INTEGRATIE ═══\n"))
    time.sleep(0.3)

    launcher_checks = [
        (39, "Digital Daemon"),
        (40, "Trinity Symbiosis"),
        (41, "Omega AI"),
        (42, "Sanctuary Dashboard"),
        (43, "Dream Monitor"),
        (44, "Nexus Bridge"),
        (45, "Visual Nexus"),
        (46, "Prometheus Brain"),
        (47, "Pulse Protocol"),
        (48, "Voice Protocol"),
        (49, "Listener Protocol"),
    ]

    launcher_ok = 0
    for nr, naam in launcher_checks:
        gevonden = check_launcher_app(nr)
        if gevonden:
            launcher_ok += 1
            status = ok("[  OK  ]")
        else:
            status = fail("[FOUT!]")
        print(f"    {status}  App #{nr}: {naam}")
        time.sleep(0.05)

    print()

    # ─── VOICE ENGINE ───
    print(accent("  ═══ VOICE ENGINE STATUS ═══\n"))
    time.sleep(0.3)

    voice_status = check_voice_backend()
    backend = voice_status.get("active_backend", "none")
    elevenlabs = voice_status.get("elevenlabs", False)
    edge_tts = voice_status.get("edge_tts", False)
    pyttsx3 = voice_status.get("pyttsx3", False)

    def bool_status(val):
        return ok("JA") if val else fail("NEE")

    print(f"    Actieve backend:  {accent(backend)}")
    print(f"    ElevenLabs:       {bool_status(elevenlabs)}")
    print(f"    Edge-TTS:         {bool_status(edge_tts)}")
    print(f"    pyttsx3:          {bool_status(pyttsx3)}")
    print()

    # ─── MOOD MAPPING ───
    print(accent("  ═══ MOOD -> EMOTION MAPPING ═══\n"))
    time.sleep(0.3)

    try:
        from danny_toolkit.quests.voice_protocol import (
            VoiceProtocol,
        )
        from danny_toolkit.daemon.limbic_system import Mood

        vp = VoiceProtocol()
        for mood in Mood:
            emotion = vp.mood_to_emotion(mood)
            print(
                f"    {mood.value:>10} -> "
                f"{ok(emotion.value)}"
            )
        mapping_ok = True
    except Exception as e:
        print(f"    {fail(f'FOUT: {e}')}")
        mapping_ok = False

    print()

    # ─── EINDOORDEEL ───
    print(titel(
        "  ╔═══════════════════════════════════════════════╗"
    ))
    print(titel(
        "  ║              EINDOORDEEL                      ║"
    ))
    print(titel(
        "  ╚═══════════════════════════════════════════════╝"
    ))
    print()

    quest_score = sum(
        1 for _, s in resultaten if s
    )
    quest_totaal = len(resultaten)

    print(f"    Quests:      {ok(quest_score)}/{quest_totaal}")
    print(f"    Subsystemen: {ok(geslaagd - quest_score)}"
          f"/{totaal - quest_totaal}")
    print(f"    Launcher:    {ok(launcher_ok)}"
          f"/{len(launcher_checks)}")
    print(f"    Voice:       "
          f"{ok('ACTIEF') if backend != 'none' else fail('INACTIEF')}")
    print(f"    Mapping:     "
          f"{ok('COMPLEET') if mapping_ok else fail('FOUT')}")
    print()

    # Totaalscore
    max_score = totaal + len(launcher_checks) + 2
    score = (
        geslaagd
        + launcher_ok
        + (1 if backend != "none" else 0)
        + (1 if mapping_ok else 0)
    )
    percentage = int((score / max_score) * 100)

    # Rang bepalen
    if percentage == 100:
        rang = "DIVINE"
        rang_kleur = MAGENTA
    elif percentage >= 90:
        rang = "LEGENDARY"
        rang_kleur = GEEL
    elif percentage >= 75:
        rang = "EPIC"
        rang_kleur = CYAAN
    elif percentage >= 50:
        rang = "AWAKENED"
        rang_kleur = BLAUW
    else:
        rang = "MORTAL"
        rang_kleur = ROOD

    balk_lengte = 30
    gevuld = int(balk_lengte * percentage / 100)
    leeg = balk_lengte - gevuld

    print(f"    Score: {ok(score)}/{max_score} "
          f"({percentage}%)")
    print()
    print(f"    [{GROEN}{'#' * gevuld}{DIM}"
          f"{'.' * leeg}{RESET}]")
    print()
    print(f"    Rang: {BOLD}{rang_kleur}"
          f"    {rang}{RESET}")
    print()

    if rang == "DIVINE":
        print(titel(
            "    Het systeem leeft, denkt, droomt,"
            " voelt, spreekt EN hoort."
        ))
        print(titel(
            "    Pixel heeft oren. De cirkel"
            " is compleet."
        ))
    elif rang == "LEGENDARY":
        print(accent(
            "    Bijna goddelijk. Check de"
            " ontbrekende modules."
        ))
    else:
        print(f"    {GEEL}Er zijn modules die"
              f" aandacht nodig hebben.{RESET}")

    print()
    return score, max_score, rang


if __name__ == "__main__":
    try:
        # Windows encoding fix
        import os
        if os.name == "nt":
            os.system("")  # Enable ANSI on Windows
            sys.stdout.reconfigure(encoding="utf-8")
        score, max_score, rang = run_integrity_check()
    except KeyboardInterrupt:
        print(f"\n{DIM}  Afgebroken.{RESET}\n")
