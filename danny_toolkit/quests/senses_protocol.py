"""
QUEST IV: THE SENSES
=====================
"The Organism Perceives"

De zintuigen van het digitale organisme. Luistert naar events
van alle 35+ apps en voedt het brein met waarnemingen.

Spelers:
- SENSORIUM   (event engine)   - Centrale waarneming
- EVENT TYPE  (17 types)       - Soorten waarneming
- NUTRITION   (voedingswaarde) - Event -> energie mapping
"""

from ..core.utils import kleur, Kleur, succes, fout, info
from ..daemon.sensorium import Sensorium, EventType


class SensesProtocol:
    """Quest IV: The Senses - De zintuigen van het organisme."""

    def __init__(self):
        self.sensorium = None
        self._init_sensorium()

    def _init_sensorium(self):
        """Initialiseer het Sensorium."""
        try:
            self.sensorium = Sensorium()
        except Exception as e:
            self.sensorium = None
            self._init_error = str(e)

    def get_status(self) -> dict:
        """Geef protocol status."""
        if self.sensorium is None:
            return {
                "quest": "IV - THE SENSES",
                "status": "niet beschikbaar",
                "error": getattr(self, "_init_error", ""),
            }

        return {
            "quest": "IV - THE SENSES",
            "event_types": len(EventType),
            "events_gelogd": len(
                self.sensorium.events
            ),
            "nutrition_mappings": len(
                Sensorium.EVENT_NUTRITION
            ),
            "status": "operationeel",
        }

    def run_simulation(self):
        """Demo: toon event types en nutrition mapping."""
        print(kleur(
            "  QUEST IV: THE SENSES\n"
            "  " + "=" * 50,
            Kleur.FEL_GEEL,
        ))

        if self.sensorium is None:
            print(fout(
                f"\n  Sensorium niet beschikbaar: "
                f"{getattr(self, '_init_error', 'onbekend')}"
            ))
            print(kleur(
                "\n  Protocol beëindigd.", Kleur.DIM,
            ))
            return

        # Event Types
        print(kleur(
            "\n  --- Event Types (Zintuigen) ---",
            Kleur.FEL_GEEL,
        ))

        categorieen = {
            "Voeding": [
                EventType.RAG_UPLOAD,
                EventType.TASK_COMPLETE,
                EventType.CODE_COMMIT,
                EventType.NOTE_CREATED,
                EventType.GOAL_PROGRESS,
            ],
            "Activiteit": [
                EventType.QUERY_ASKED,
                EventType.HUNT_STARTED,
                EventType.WORKOUT_LOGGED,
                EventType.EXPENSE_ADDED,
                EventType.MOOD_LOGGED,
            ],
            "Systeem": [
                EventType.APP_OPENED,
                EventType.APP_CLOSED,
                EventType.POMODORO_BREAK,
                EventType.POMODORO_WORK,
            ],
            "Tijd": [
                EventType.MORNING,
                EventType.EVENING,
                EventType.NIGHT,
                EventType.IDLE,
            ],
        }

        for cat, events in categorieen.items():
            print(kleur(
                f"\n    [{cat}]", Kleur.FEL_GEEL,
            ))
            for evt in events:
                # Check of er nutrition mapping is
                nut = Sensorium.EVENT_NUTRITION.get(evt)
                nut_str = (
                    f" -> {nut[0]} +{nut[1]}"
                    if nut else ""
                )
                print(kleur(
                    f"      {evt.value:<20}{nut_str}",
                    Kleur.WIT,
                ))

        # Event log
        event_count = len(self.sensorium.events)
        print(kleur(
            f"\n  --- Event Log ---",
            Kleur.FEL_GEEL,
        ))
        print(kleur(
            f"    Events gelogd: {event_count}",
            Kleur.WIT,
        ))

        print(kleur(
            "\n  Protocol beëindigd.", Kleur.DIM,
        ))


if __name__ == "__main__":
    try:
        protocol = SensesProtocol()
        protocol.run_simulation()
    except Exception as e:
        print(f"\nFOUT: {e}")
