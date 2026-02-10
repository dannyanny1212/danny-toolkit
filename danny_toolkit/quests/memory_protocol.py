"""
Quest XIV: THE MEMORY - Persistent Geheugen.

Valideert de Cortical Stack: log_event, remember_fact,
recall en log_stat. Toont status en draait simulatie.

Gebruik:
    from danny_toolkit.quests.memory_protocol import (
        MemoryProtocol,
    )
    protocol = MemoryProtocol()
    protocol.run_simulation()
"""

from ..core.utils import kleur, Kleur, succes, fout
from ..brain.cortical_stack import get_cortical_stack


class MemoryProtocol:
    """Quest XIV: THE MEMORY - Persistent Geheugen."""

    def __init__(self):
        self.stack = get_cortical_stack()

    def get_status(self) -> dict:
        """Return quest status."""
        db_stats = self.stack.get_stats()
        return {
            "quest": "XIV - THE MEMORY",
            "tables": [
                "episodic_memory",
                "semantic_memory",
                "system_stats",
            ],
            "totals": db_stats,
        }

    def run_simulation(self):
        """Voer 4 tests uit met visuele output."""
        print(kleur(
            "\n  ╔═══════════════════════════════════════╗",
            Kleur.FEL_MAGENTA,
        ))
        print(kleur(
            "  ║  QUEST XIV: THE MEMORY               ║",
            Kleur.FEL_MAGENTA,
        ))
        print(kleur(
            "  ║  Persistent Geheugen - Cortical Stack ║",
            Kleur.FEL_MAGENTA,
        ))
        print(kleur(
            "  ╚═══════════════════════════════════════╝",
            Kleur.FEL_MAGENTA,
        ))
        print()

        geslaagd = 0

        # Test 1: log_event
        print(kleur(
            "  [TEST 1/4] Episodic Memory: log_event",
            Kleur.FEL_CYAAN,
        ))
        try:
            event_id = self.stack.log_event(
                actor="memory_protocol",
                action="test_event",
                details={"test": True, "nr": 1},
                source="quest_xiv",
            )
            if event_id and event_id > 0:
                print(succes(
                    f"    OK - Event #{event_id} gelogd"
                ))
                geslaagd += 1
            else:
                print(fout("    FOUT - Geen event ID"))
        except Exception as e:
            print(fout(f"    FOUT - {e}"))
        print()

        # Test 2: remember_fact
        print(kleur(
            "  [TEST 2/4] Semantic Memory: remember_fact",
            Kleur.FEL_CYAAN,
        ))
        try:
            ok = self.stack.remember_fact(
                key="quest_xiv_test",
                value="Memory Protocol werkt!",
                confidence=0.95,
            )
            if ok:
                print(succes(
                    "    OK - Feit opgeslagen"
                ))
                geslaagd += 1
            else:
                print(fout("    FOUT - Opslaan mislukt"))
        except Exception as e:
            print(fout(f"    FOUT - {e}"))
        print()

        # Test 3: recall
        print(kleur(
            "  [TEST 3/4] Semantic Memory: recall",
            Kleur.FEL_CYAAN,
        ))
        try:
            feit = self.stack.recall("quest_xiv_test")
            if feit and feit.get("value"):
                print(succes(
                    f"    OK - Herinnerd: "
                    f"{feit['value']}"
                ))
                geslaagd += 1
            else:
                print(fout("    FOUT - Feit niet gevonden"))
        except Exception as e:
            print(fout(f"    FOUT - {e}"))
        print()

        # Test 4: log_stat
        print(kleur(
            "  [TEST 4/4] System Stats: log_stat",
            Kleur.FEL_CYAAN,
        ))
        try:
            stat_id = self.stack.log_stat(
                metric="quest_test",
                value=42.0,
                tags={"source": "quest_xiv"},
            )
            if stat_id and stat_id > 0:
                print(succes(
                    f"    OK - Stat #{stat_id} gelogd"
                ))
                geslaagd += 1
            else:
                print(fout("    FOUT - Geen stat ID"))
        except Exception as e:
            print(fout(f"    FOUT - {e}"))
        print()

        # Status
        db_stats = self.stack.get_stats()
        print(kleur(
            "  ─── MEMORY STATUS ───",
            Kleur.FEL_MAGENTA,
        ))
        print(kleur(
            f"    Episodic events: "
            f"{db_stats['episodic_events']}",
            Kleur.CYAAN,
        ))
        print(kleur(
            f"    Semantic facts:  "
            f"{db_stats['semantic_facts']}",
            Kleur.CYAAN,
        ))
        print(kleur(
            f"    System stats:    "
            f"{db_stats['system_stats']}",
            Kleur.CYAAN,
        ))
        print(kleur(
            f"    Totaal records:  "
            f"{db_stats['total']}",
            Kleur.CYAAN,
        ))
        print(kleur(
            f"    Database:        "
            f"{db_stats['db_path']}",
            Kleur.DIM,
        ))
        print()

        # Eindoordeel
        print(kleur(
            f"  Tests geslaagd: {geslaagd}/4",
            Kleur.FEL_GROEN if geslaagd == 4
            else Kleur.FEL_ROOD,
        ))
        print()
