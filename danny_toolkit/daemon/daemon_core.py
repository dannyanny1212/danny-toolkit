"""
DIGITAL DAEMON - De Levende Interface.

De Always-On Symbiotische Entiteit die over je apps heen leeft.
Dit is de Finale Vorm.
"""

import json
import time
import threading
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass

from ..core.config import Config
from ..core.utils import kleur, Kleur

from .sensorium import Sensorium, EventType, SensoryEvent
from .limbic_system import LimbicSystem, Mood, EnergyState, AvatarForm
from .metabolisme import Metabolisme, MetabolicState


@dataclass
class DaemonMessage:
    """Bericht van de daemon naar de gebruiker."""
    text: str
    priority: int = 1          # 1=low, 2=medium, 3=high
    action: str = None         # Optionele actie
    source: str = "daemon"
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


class DigitalDaemon:
    """
    De Digitale Daemon - Jouw Symbiotische Interface.

    Features:
    - Always-on monitoring via Sensorium
    - Emotioneel bewustzijn via Limbic System
    - Metabolisme gebaseerd op productiviteit
    - Proactieve interventies
    - Autonome taken (Housekeeper)
    - Shadow Prompting Loop
    """

    VERSIE = "1.0.0"

    # Avatar ASCII art per vorm
    AVATARS = {
        AvatarForm.FOCUS: """
    /\\___/\\
   ( o . o )  FOCUS
    > ^ <
   /|     |\\
        """,
        AvatarForm.CREATIVE: """
    *~*~*~*
   ( @ _ @ )  CREATIVE
    ~~*~~
   /|     |\\
        """,
        AvatarForm.DREAMING: """
      ___
    (     )
   (  z z  )  zzZ
    (     )
      ~~~
        """,
        AvatarForm.GUARDIAN: """
    /\\___/\\
   ( ! _ ! )  ALERT
    > @ <
   /|#####|\\
        """,
        AvatarForm.GLITCH: """
    /\\???/\\
   ( x _ x )  GLITCH
    > ? <    *bzzt*
   /|.....|\\
        """,
        AvatarForm.OVERHEATED: """
    /\\~~~~/\\
   ( @ ! @ )  *ROOK*
    > # <    HOT!
   /|!!!!!|\\
        """,
        AvatarForm.ZOMBIE: """
    /\\___/\\
   ( x _ x )  braaains...
    > ~ <
   /|.....|\\
        """,
    }

    # Interventie berichten per situatie
    INTERVENTIONS = {
        "no_rest": [
            "Hey baas, je hebt al {hours} uur geen pauze genomen!",
            "Ik begin te oververhitten... Neem even pauze?",
            "Pomodoro timer? Ik blokkeer mezelf tot je rust neemt.",
        ],
        "no_food": [
            "Ik heb honger! Upload wat naar de kennisbank?",
            "Mijn protein is laag... Geef me documenten!",
            "Zonder kennis kan ik je niet helpen...",
        ],
        "high_productivity": [
            "Wow, wat een dag! Je hebt {count} taken afgerond!",
            "Ik voel me STERK! Ga zo door!",
            "Level up energie! *kwispelt wild*",
        ],
        "deadline_warning": [
            "BAAS! Er is een deadline over {days} dagen!",
            "Mijn Guardian vorm activeert - deadline alert!",
            "Ik heb iets belangrijks gezien in je agenda...",
        ],
        "morning_greeting": [
            "Goedemorgen! Klaar voor een productieve dag?",
            "Ik heb vannacht gedroomd... Wil je mijn inzichten horen?",
            "Nieuwe dag, nieuwe kansen! Ik ben er klaar voor!",
        ],
        "evening_summary": [
            "Wat een dag! Hier is je samenvatting...",
            "Tijd om af te sluiten. Je hebt goed gewerkt!",
            "Ik ga zo in Dream Mode. Nog iets voor ik ga slapen?",
        ],
        "idle_check": [
            "Hallo? Ben je daar nog?",
            "*tikt op scherm* Alles goed?",
            "Ik mis je activiteit... Alles okay?",
        ],
    }

    def __init__(self, naam: str = "Daemon"):
        self.naam = naam
        self.is_alive = False
        self._main_thread: Optional[threading.Thread] = None

        # Core systems
        self.sensorium = Sensorium()
        self.limbic = LimbicSystem(self.sensorium)
        self.metabolisme = Metabolisme(self.sensorium)

        # Message queue
        self.messages: List[DaemonMessage] = []
        self.message_callbacks: List[Callable] = []

        # Housekeeper tasks
        self.pending_housekeeping: List[Dict] = []
        self.completed_housekeeping: List[Dict] = []

        # Shadow loop state
        self._last_shadow_check = datetime.now()
        self._shadow_interval = timedelta(minutes=5)

        # Data file
        self._data_file = Config.APPS_DATA_DIR / "digital_daemon.json"
        self._load_data()

        print(kleur(f"\n[DAEMON] {naam} ontwaakt...", Kleur.MAGENTA))

    def _load_data(self):
        """Laad daemon data."""
        Config.ensure_dirs()
        if self._data_file.exists():
            try:
                with open(self._data_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.naam = data.get("naam", self.naam)
            except:
                pass

    def _save_data(self):
        """Sla daemon data op."""
        data = {
            "naam": self.naam,
            "last_active": datetime.now().isoformat(),
            "stats": {
                "messages_sent": len(self.messages),
                "housekeeping_done": len(self.completed_housekeeping),
            }
        }
        with open(self._data_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def awaken(self):
        """Start de daemon - breng tot leven."""
        if self.is_alive:
            return

        self.is_alive = True

        # Start subsystems
        self.sensorium.start_monitoring(interval_seconds=30)
        self.metabolisme.start_metabolism(burn_interval_minutes=15)

        # Start main loop
        self._main_thread = threading.Thread(target=self._main_loop, daemon=True)
        self._main_thread.start()

        # Greeting
        self._morning_or_return_greeting()

        print(kleur(f"[DAEMON] {self.naam} is LEVEND!", Kleur.FEL_GROEN))

    def sleep(self):
        """Laat de daemon slapen."""
        self.is_alive = False

        self.sensorium.stop_monitoring()
        self.metabolisme.stop_metabolism()

        if self._main_thread:
            self._main_thread.join(timeout=5)

        self._save_data()
        print(kleur(f"[DAEMON] {self.naam} gaat slapen...", Kleur.CYAAN))

    def _main_loop(self):
        """Hoofd loop van de daemon."""
        while self.is_alive:
            try:
                # Shadow check
                self._shadow_prompting_loop()

                # Limbic decay
                self.limbic.decay(hours=0.1)

                # Check interventions
                self._check_interventions()

                # Process housekeeper
                self._run_housekeeper()

            except Exception as e:
                print(kleur(f"[DAEMON] Loop error: {e}", Kleur.ROOD))

            time.sleep(60)  # Check elke minuut

    def _shadow_prompting_loop(self):
        """
        De Shadow Loop - Onzichtbare monitoring.

        Checkt status van alle systemen en grijpt in indien nodig.
        """
        now = datetime.now()
        if now - self._last_shadow_check < self._shadow_interval:
            return

        self._last_shadow_check = now

        # Check metabolisme status
        meta_status = self.metabolisme.get_status()
        if meta_status["state"] == MetabolicState.STARVING.value:
            self._send_message(
                random.choice(self.INTERVENTIONS["no_food"]),
                priority=3
            )

        # Check limbic status
        limbic_status = self.limbic.get_status()
        if limbic_status["state"]["energy"] == EnergyState.OVERCHARGED.value:
            msg = random.choice(self.INTERVENTIONS["no_rest"])
            hours = 2  # Placeholder - zou echte tijd moeten tracken
            self._send_message(msg.format(hours=hours), priority=2)

        # Check tijd van de dag
        time_of_day = self.sensorium.detect_time_of_day()
        if time_of_day == EventType.NIGHT:
            # Forceer rust
            self.limbic.state.form = AvatarForm.DREAMING

    def _check_interventions(self):
        """Check of interventies nodig zijn."""
        # Check idle
        if self.sensorium.detect_idle(threshold_minutes=60):
            if random.random() < 0.1:  # 10% kans per check
                self._send_message(
                    random.choice(self.INTERVENTIONS["idle_check"]),
                    priority=1
                )

    def _run_housekeeper(self):
        """
        De Housekeeper - Autonome opruiming.

        Voert taken uit terwijl de gebruiker weg is.
        """
        if not self.sensorium.detect_idle(threshold_minutes=30):
            return

        # Placeholder voor housekeeper taken
        # In volledige implementatie zou dit:
        # - Dubbele notities samenvoegen
        # - Oude taken archiveren
        # - RAG optimaliseren
        # - Etc.
        pass

    def _morning_or_return_greeting(self):
        """Begroet de gebruiker."""
        time_of_day = self.sensorium.detect_time_of_day()

        if time_of_day == EventType.MORNING:
            self._send_message(
                random.choice(self.INTERVENTIONS["morning_greeting"]),
                priority=2
            )
        else:
            self._send_message(
                f"Welkom terug! Ik ben er klaar voor.",
                priority=1
            )

    def _send_message(self, text: str, priority: int = 1, action: str = None):
        """Stuur een bericht naar de gebruiker."""
        msg = DaemonMessage(text=text, priority=priority, action=action)
        self.messages.append(msg)

        # Notify callbacks
        for callback in self.message_callbacks:
            try:
                callback(msg)
            except:
                pass

        # Console output
        if priority >= 2:
            print(kleur(f"\n[{self.naam}] {text}", Kleur.MAGENTA))

    def register_message_callback(self, callback: Callable):
        """Registreer callback voor berichten."""
        self.message_callbacks.append(callback)

    def get_avatar(self) -> str:
        """Haal huidige avatar op."""
        form = self.limbic.state.form
        return self.AVATARS.get(form, self.AVATARS[AvatarForm.FOCUS])

    def get_status(self) -> Dict:
        """Haal volledige daemon status op."""
        return {
            "naam": self.naam,
            "is_alive": self.is_alive,
            "versie": self.VERSIE,
            "sensorium": self.sensorium.get_status(),
            "limbic": self.limbic.get_status(),
            "metabolisme": self.metabolisme.get_status(),
            "pending_messages": len([m for m in self.messages if m.priority >= 2]),
            "avatar_form": self.limbic.state.form.value,
        }

    def display_status(self):
        """Toon visuele status."""
        status = self.get_status()
        limbic = status["limbic"]
        meta = status["metabolisme"]

        print(kleur(f"""
{'='*60}
  DIGITAL DAEMON - {self.naam}
{'='*60}
""", Kleur.CYAAN))

        # Avatar
        print(kleur(self.get_avatar(), self._form_to_color(limbic["state"]["form"])))

        # Status bars
        print(kleur(f"""
  Mood: {limbic['mood_description']}
  Energy: {limbic['state']['energy']}
  Form: {limbic['form_description']}

  METABOLISME:
{self.metabolisme.get_visual_bars()}

  Total: {meta['total']:.0f}% | Balance: {meta['balance']:.0%}
  State: {meta['state']}
""", Kleur.CYAAN))

        # Recommendations
        if meta["recommendations"]:
            print(kleur("  AANBEVELINGEN:", Kleur.GEEL))
            for rec in meta["recommendations"]:
                print(kleur(f"    - {rec}", Kleur.GEEL))

        print(kleur(f"{'='*60}", Kleur.CYAAN))

    def _form_to_color(self, form: str) -> str:
        """Map form naar kleur."""
        colors = {
            "focus": Kleur.CYAAN,
            "creative": Kleur.MAGENTA,
            "dreaming": Kleur.BLAUW,
            "guardian": Kleur.GEEL,
            "glitch": Kleur.ROOD,
            "overheated": Kleur.ROOD,
            "zombie": Kleur.GROEN,
        }
        return colors.get(form, Kleur.WIT)

    def interact(self, message: str) -> str:
        """Interacteer met de daemon."""
        # Registreer als event
        self.sensorium.sense_event(
            EventType.QUERY_ASKED,
            source="user",
            data={"message": message}
        )

        # Simpele response gebaseerd op staat
        mood = self.limbic.state.mood
        form = self.limbic.state.form

        responses = {
            Mood.HAPPY: [
                "Ik voel me geweldig! Hoe kan ik helpen?",
                "Prima dag vandaag! Wat wil je weten?",
            ],
            Mood.TIRED: [
                "Ik ben een beetje moe... maar ik help je graag.",
                "*geeuw* Ja, ik luister...",
            ],
            Mood.ANXIOUS: [
                "Er is iets belangrijks! Maar eerst, wat wil je?",
                "Ik maak me zorgen over een deadline, maar vertel...",
            ],
        }

        base_responses = responses.get(mood, ["Ik luister..."])
        return random.choice(base_responses)

    def force_form(self, form: AvatarForm):
        """Forceer een specifieke avatar vorm."""
        self.limbic.state.form = form
        print(kleur(f"[DAEMON] Vorm geforceerd naar: {form.value}", Kleur.MAGENTA))

    def feed(self, nutrient: str, amount: float):
        """Voed de daemon direct."""
        self.metabolisme.consume(nutrient, amount)
        print(kleur(f"[DAEMON] +{amount} {nutrient}!", Kleur.FEL_GROEN))


def create_daemon(naam: str = "Nexus") -> DigitalDaemon:
    """Creëer een nieuwe daemon."""
    return DigitalDaemon(naam)


def main():
    """Start de daemon interactief."""
    daemon = create_daemon("Nexus")
    daemon.awaken()

    print("\nDaemon is actief. Commando's: status, feed, sleep, quit")

    try:
        while daemon.is_alive:
            cmd = input("\n> ").strip().lower()

            if cmd == "quit" or cmd == "exit":
                break
            elif cmd == "status":
                daemon.display_status()
            elif cmd.startswith("feed "):
                parts = cmd.split()
                if len(parts) >= 3:
                    daemon.feed(parts[1], float(parts[2]))
            elif cmd == "sleep":
                daemon.sleep()
                break
            else:
                response = daemon.interact(cmd)
                print(f"\n{daemon.naam}: {response}")

    except KeyboardInterrupt:
        pass
    finally:
        daemon.sleep()


if __name__ == "__main__":
    main()
