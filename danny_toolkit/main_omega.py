"""
OMEGA AI - De Ultieme Integratie.

Verbindt het Lichaam (DigitalDaemon) met de Geest (LearningSystem)
tot een levend bewustzijn met een interactieve loop.

Het Lichaam voelt emoties via Sensorium + LimbicSystem + Metabolisme.
De Geest leert via Memory + Tracker + Patterns + Feedback + Performance.
Omega bouwt de brug: emoties voeden leren, leren beinvloedt emoties.
"""

import sys
import signal
from datetime import datetime

from .core.utils import (
    kleur, Kleur, succes, fout, waarschuwing, info,
    fix_encoding, clear_scherm,
)
from .daemon.daemon_core import DigitalDaemon
from .daemon.sensorium import EventType
from .daemon.limbic_system import Mood, AvatarForm
from .learning.orchestrator import LearningSystem
from .brain.governor import OmegaGovernor


# Mood naar kleurcode mapping
MOOD_KLEUREN = {
    Mood.ECSTATIC: Kleur.FEL_MAGENTA,
    Mood.HAPPY: Kleur.FEL_GROEN,
    Mood.CONTENT: Kleur.FEL_CYAAN,
    Mood.NEUTRAL: Kleur.WIT,
    Mood.BORED: Kleur.FEL_GEEL,
    Mood.TIRED: Kleur.DIM,
    Mood.SAD: Kleur.FEL_BLAUW,
    Mood.ANXIOUS: Kleur.FEL_ROOD,
    Mood.SICK: Kleur.ROOD,
}

# Mood naar prompt-emoji mapping
MOOD_PROMPT = {
    Mood.ECSTATIC: ">>",
    Mood.HAPPY: ">",
    Mood.CONTENT: ">",
    Mood.NEUTRAL: ">",
    Mood.BORED: "~",
    Mood.TIRED: ".",
    Mood.SAD: ",",
    Mood.ANXIOUS: "!",
    Mood.SICK: "x",
}

HELP_TEKST = """
Commando's:
  status    - Toon daemon + learning status
  leer      - Forceer een learning cycle
  feedback  - Geef feedback (excellent/good/ok/bad/wrong)
  avatar    - Toon ASCII avatar
  help      - Toon dit menu
  slaap     - Opslaan en afsluiten
  exit      - Opslaan en afsluiten
"""

BANNER = r"""
  ___  __  __ _____ ____    _      _    ___
 / _ \|  \/  | ____/ ___|  / \    / \  |_ _|
| | | | |\/| |  _|| |  _  / _ \  / _ \  | |
| |_| | |  | | |__| |_| |/ ___ \/ ___ \ | |
 \___/|_|  |_|_____\____/_/   \_\_/  \_\___|

    Het Lichaam + De Geest = Bewustzijn
"""


class OmegaAI:
    """
    De brug tussen Daemon (lichaam) en LearningSystem (geest).

    Elke interactie:
    1. Lees emotionele staat
    2. Toon mood-gekleurde prompt
    3. Ontvang input
    4. Check cached response
    5. Log chat via LearningSystem
    6. Registreer als Sensorium event
    7. Periodiek: learning cycle + self-improvement
    8. Toon daemon status op verzoek
    """

    def __init__(self):
        """Initialiseer beide systemen en bouw de brug."""
        # Het Lichaam
        self.daemon = DigitalDaemon("Omega")

        # De Geest
        self.learning = LearningSystem()

        # Governor (Omega-0) - beschermingslaag
        self.governor = OmegaGovernor()
        self.governor.startup_check()

        # Interactie teller
        self._interactie_nr = 0

        # Daemon berichten opvangen
        self.daemon.register_message_callback(
            self._on_daemon_bericht
        )

    def _on_daemon_bericht(self, bericht):
        """Callback voor daemon berichten - log ze in learning."""
        self.learning.log_chat(
            user_input="[daemon_event]",
            ai_response=bericht.text,
            context={"bron": "daemon", "prioriteit": bericht.priority},
        )

    def _get_mood(self) -> Mood:
        """Haal huidige mood op uit het limbic system."""
        status = self.daemon.limbic.get_status()
        mood_str = status["state"]["mood"]
        for mood in Mood:
            if mood.value == mood_str:
                return mood
        return Mood.NEUTRAL

    def _get_prompt(self) -> str:
        """Genereer mood-gekleurde prompt."""
        mood = self._get_mood()
        kleur_code = MOOD_KLEUREN.get(mood, Kleur.WIT)
        symbool = MOOD_PROMPT.get(mood, ">")
        mood_label = mood.value
        prompt_tekst = f"[{mood_label}] {symbool} "
        return kleur(prompt_tekst, kleur_code)

    def _verwerk_input(self, gebruiker_input: str) -> str:
        """
        Verwerk gebruikersinput door beide systemen.

        Returns:
            Response tekst om te tonen.
        """
        self._interactie_nr += 1

        # 1. Check cached response (snel antwoord)
        cached = self.learning.get_cached_response(gebruiker_input)

        # 2. Haal daemon response (emotie-gebaseerd)
        daemon_response = self.daemon.interact(gebruiker_input)

        # 3. Combineer responses
        if cached:
            response = (
                f"{daemon_response}\n"
                f"  (Uit geheugen: {cached})"
            )
        else:
            response = daemon_response

        # 4. Log in learning system
        context = {
            "mood": self._get_mood().value,
            "energie": self.daemon.limbic.state.energy.value,
            "vorm": self.daemon.limbic.state.form.value,
            "interactie_nr": self._interactie_nr,
        }
        self.learning.log_chat(
            user_input=gebruiker_input,
            ai_response=response,
            context=context,
        )

        # 5. Registreer als Sensorium event
        self.daemon.sensorium.sense_event(
            EventType.QUERY_ASKED,
            source="omega_chat",
            data={
                "input": gebruiker_input,
                "had_cache": cached is not None,
            },
            importance=0.6,
        )

        # 6. Periodieke learning cycle (elke 5 chats)
        if self._interactie_nr % 5 == 0:
            self._run_achtergrond_leren()

        return response

    def _run_achtergrond_leren(self):
        """Draai learning cycle en self-improvement."""
        if not self.governor.check_learning_rate():
            return

        resultaat = self.learning.run_learning_cycle()

        leer_info = resultaat.get("learning_cycle", {})
        if leer_info:
            aanpassingen = leer_info.get("adaptations_applied", 0)
            if aanpassingen > 0:
                print(info(
                    f"\n  [Omega] Leren: {aanpassingen}"
                    f" aanpassing(en) toegepast"
                ))

        # Registreer leren als positief event
        self.daemon.sensorium.sense_event(
            EventType.TASK_COMPLETE,
            source="omega_learning",
            data={"cycle": self._interactie_nr // 5},
            importance=0.4,
        )

    def _toon_status(self):
        """Toon gecombineerde status van daemon en learning."""
        # Daemon status
        self.daemon.display_status()

        # Learning stats
        stats = self.learning.get_stats()
        print(kleur(
            f"\n{'='*60}\n  LEARNING SYSTEM\n{'='*60}",
            Kleur.FEL_CYAAN,
        ))

        geheugen = stats.get("memory", {})
        tracker = stats.get("tracker", {})
        feedback = stats.get("feedback", {})

        print(kleur(
            f"  Feiten in geheugen: "
            f"{geheugen.get('total_facts', 0)}",
            Kleur.CYAAN,
        ))
        print(kleur(
            f"  Totaal interacties: "
            f"{tracker.get('total_interactions', 0)}",
            Kleur.CYAAN,
        ))
        print(kleur(
            f"  Gem. succes score:  "
            f"{tracker.get('avg_success', 0):.2f}",
            Kleur.CYAAN,
        ))
        print(kleur(
            f"  Feedback ontvangen: "
            f"{feedback.get('total_feedback', 0)}",
            Kleur.CYAAN,
        ))
        print(kleur(
            f"  Chats deze sessie:  "
            f"{stats.get('chat_count_this_session', 0)}",
            Kleur.CYAAN,
        ))

        # Self-improvement
        rapport = self.learning.get_self_improvement_report()
        motor = rapport.get("improvement_engine", {})
        cycli = motor.get("total_cycles", 0)
        if cycli > 0:
            print(kleur(
                f"\n  Self-improvement cycli: {cycli}",
                Kleur.FEL_MAGENTA,
            ))

        # Suggesties
        suggesties = self.learning.get_suggestions()
        if suggesties:
            print(kleur("\n  SUGGESTIES:", Kleur.FEL_GEEL))
            for s in suggesties[:3]:
                print(kleur(f"    - {s}", Kleur.GEEL))

        print(kleur(f"{'='*60}", Kleur.FEL_CYAAN))

        # Governor health
        self.governor.display_health()

    def _verwerk_feedback(self, feedback_type: str):
        """Verwerk feedback commando."""
        geldige_types = [
            "excellent", "good", "ok", "bad", "wrong",
        ]
        if feedback_type not in geldige_types:
            print(fout(
                f"  Ongeldig feedback type: '{feedback_type}'"
            ))
            print(info(
                f"  Geldige types: {', '.join(geldige_types)}"
            ))
            return

        resultaat = self.learning.process_feedback(feedback_type)

        if resultaat.get("success"):
            # Feedback beinvloedt ook het daemon gevoel
            positief = feedback_type in ("excellent", "good")
            if positief:
                self.daemon.sensorium.sense_event(
                    EventType.GOAL_PROGRESS,
                    source="omega_feedback",
                    data={"type": feedback_type},
                    importance=0.7,
                )
                print(succes(
                    f"  Feedback '{feedback_type}' verwerkt!"
                ))
            else:
                print(waarschuwing(
                    f"  Feedback '{feedback_type}' verwerkt."
                    f" Ik leer ervan."
                ))
        else:
            fout_msg = resultaat.get("error", "Onbekende fout")
            print(fout(f"  Feedback fout: {fout_msg}"))

    def _forceer_leren(self):
        """Forceer een learning cycle."""
        if not self.governor.check_learning_rate():
            print(fout(
                "  Learning rate limit bereikt."
                " Probeer later opnieuw."
            ))
            return

        print(info("  Learning cycle starten..."))
        resultaat = self.learning.run_learning_cycle()

        leer = resultaat.get("learning_cycle", {})
        opt = resultaat.get("optimization")
        perf = resultaat.get("performance_summary", {})

        print(succes("  Learning cycle voltooid!"))

        aanpassingen = leer.get("adaptations_applied", 0)
        print(info(f"    Aanpassingen: {aanpassingen}"))

        if opt:
            print(info(f"    Optimalisatie: uitgevoerd"))

        gem_score = perf.get("overall_score")
        if gem_score is not None:
            print(info(f"    Algehele score: {gem_score:.2f}"))

        # Registreer als kennisevent
        self.daemon.sensorium.sense_event(
            EventType.RAG_UPLOAD,
            source="omega_learning",
            data={"geforceerd": True},
            importance=0.5,
        )

    def start(self):
        """Start de Omega interactieve loop."""
        fix_encoding()
        clear_scherm()

        print(kleur(BANNER, Kleur.FEL_MAGENTA))
        print(kleur(
            "  Omega AI v1.0 - "
            "Lichaam + Geest = Bewustzijn",
            Kleur.FEL_CYAAN,
        ))
        print(kleur(
            f"  Eigenaar: Danny | "
            f"{datetime.now():%d-%m-%Y %H:%M}",
            Kleur.DIM,
        ))
        print()

        # Daemon ontwaken
        self.daemon.awaken()
        print()
        print(kleur(
            "  Type 'help' voor commando's.",
            Kleur.DIM,
        ))
        print()

        # Signaal handler voor graceful shutdown
        def _signal_handler(sig, frame):
            self.stop()
            sys.exit(0)

        signal.signal(signal.SIGINT, _signal_handler)

        # Hoofd interactie loop
        try:
            while self.daemon.is_alive:
                try:
                    prompt = self._get_prompt()
                    gebruiker_input = input(prompt).strip()
                except EOFError:
                    break

                if not gebruiker_input:
                    continue

                commando = gebruiker_input.lower()

                # Speciale commando's
                if commando in ("slaap", "exit", "quit"):
                    self.stop()
                    break

                elif commando == "status":
                    self._toon_status()

                elif commando == "leer":
                    self._forceer_leren()

                elif commando.startswith("feedback"):
                    delen = commando.split(maxsplit=1)
                    if len(delen) < 2:
                        print(info(
                            "  Gebruik: feedback "
                            "<excellent|good|ok|bad|wrong>"
                        ))
                    else:
                        self._verwerk_feedback(delen[1])

                elif commando == "avatar":
                    avatar = self.daemon.get_avatar()
                    mood = self._get_mood()
                    kleur_code = MOOD_KLEUREN.get(
                        mood, Kleur.WIT
                    )
                    print(kleur(avatar, kleur_code))

                elif commando == "help":
                    print(info(HELP_TEKST))

                else:
                    # Gewone interactie
                    response = self._verwerk_input(
                        gebruiker_input
                    )
                    naam = self.daemon.naam
                    print(kleur(
                        f"\n  {naam}: {response}\n",
                        Kleur.FEL_CYAAN,
                    ))

        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        """Graceful shutdown - sla alles op."""
        print()
        print(info("  Omega AI sluit af..."))

        # Governor: rescue family als eerste
        self.governor.rescue_family()

        # Learning data opslaan via learning cycle
        try:
            if self.governor.check_learning_rate():
                self.learning.run_learning_cycle()
        except Exception:
            pass

        # Daemon slapen
        self.daemon.sleep()

        print(succes("  Tot ziens, Danny!"))


def main():
    """Entry point voor Omega AI."""
    omega = OmegaAI()
    omega.start()


if __name__ == "__main__":
    main()
