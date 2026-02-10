"""
QUEST II: THE DAEMON
=====================
"The Living Interface Awakens"

De Always-On Symbiotische Entiteit die over alle apps
heen leeft. Het digitale organisme wordt geboren.

Spelers:
- DIGITAL DAEMON (daemon_core) - Het levende systeem
- SENSORIUM      (zintuigen)   - Waarneming
- LIMBIC SYSTEM  (emoties)     - Gevoel
- METABOLISME    (energie)     - Levenskracht
"""

from ..core.utils import kleur, Kleur, succes, fout, info


class DaemonProtocol:
    """Quest II: The Daemon - Het digitale organisme."""

    def __init__(self):
        self.daemon = None
        self._init_daemon()

    def _init_daemon(self):
        """Initialiseer de Digital Daemon."""
        try:
            from ..daemon.daemon_core import DigitalDaemon
            self.daemon = DigitalDaemon()
        except Exception as e:
            self.daemon = None
            self._init_error = str(e)

    def get_status(self) -> dict:
        """Geef protocol status."""
        if self.daemon is None:
            return {
                "quest": "II - THE DAEMON",
                "status": "niet beschikbaar",
                "error": getattr(self, "_init_error", ""),
            }

        return {
            "quest": "II - THE DAEMON",
            "versie": self.daemon.VERSIE,
            "mood": self.daemon.limbic.get_current_state(
            ).mood.value if self.daemon.limbic else "onbekend",
            "energie": self.daemon.limbic.get_current_state(
            ).energy.value if self.daemon.limbic else "onbekend",
            "status": "operationeel",
        }

    def run_simulation(self):
        """Demo: toon daemon status en heartbeat."""
        print(kleur(
            "  QUEST II: THE DAEMON\n"
            "  " + "=" * 50,
            Kleur.FEL_ROOD,
        ))

        if self.daemon is None:
            print(fout(
                f"\n  Daemon niet beschikbaar: "
                f"{getattr(self, '_init_error', 'onbekend')}"
            ))
            print(kleur(
                "\n  Protocol beëindigd.", Kleur.DIM,
            ))
            return

        # Versie
        print(kleur(
            f"\n  Daemon v{self.daemon.VERSIE}",
            Kleur.FEL_ROOD,
        ))

        # Emotionele staat
        state = self.daemon.limbic.get_current_state()
        print(kleur(
            "\n  --- Emotionele Staat ---",
            Kleur.FEL_ROOD,
        ))
        print(kleur(
            f"    Mood:    {state.mood.value}",
            Kleur.WIT,
        ))
        print(kleur(
            f"    Energie: {state.energy.value}",
            Kleur.WIT,
        ))
        print(kleur(
            f"    Avatar:  {state.form.value}",
            Kleur.WIT,
        ))

        # Metabolisme
        meta_state = self.daemon.metabolisme.get_state()
        print(kleur(
            "\n  --- Metabolisme ---",
            Kleur.FEL_ROOD,
        ))
        print(kleur(
            f"    Staat:  {meta_state.value}",
            Kleur.WIT,
        ))

        levels = self.daemon.metabolisme.levels
        print(kleur(
            f"    Protein:  {levels.protein:.0f}/100",
            Kleur.WIT,
        ))
        print(kleur(
            f"    Carbs:    {levels.carbs:.0f}/100",
            Kleur.WIT,
        ))
        print(kleur(
            f"    Vitamins: {levels.vitamins:.0f}/100",
            Kleur.WIT,
        ))

        # Sensorium
        event_count = len(self.daemon.sensorium.event_log)
        print(kleur(
            "\n  --- Sensorium ---",
            Kleur.FEL_ROOD,
        ))
        print(kleur(
            f"    Events gelogd: {event_count}",
            Kleur.WIT,
        ))

        print(succes("\n  Daemon leeft."))
        print(kleur(
            "\n  Protocol beëindigd.", Kleur.DIM,
        ))


if __name__ == "__main__":
    try:
        protocol = DaemonProtocol()
        protocol.run_simulation()
    except Exception as e:
        print(f"\nFOUT: {e}")
