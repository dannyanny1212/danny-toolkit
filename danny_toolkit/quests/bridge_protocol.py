"""
QUEST VIII: THE BRIDGE
=======================
"Pixel Meets the Brain"

De verbinding tussen het virtueel huisdier (Pixel) en het
Central Brain. NEXUS wordt proactief en context-aware.

Spelers:
- NEXUS BRIDGE     (symbiose-laag)  - Verbinding
- NEXUS ORACLE     (diepe inzichten) - Wijsheid (level 7+)
- CENTRAL BRAIN    (AI orkestrator) - Intelligentie
"""

import logging

from ..core.utils import kleur, Kleur, succes, fout, info

logger = logging.getLogger(__name__)

from ..brain.nexus_bridge import (
    NexusBridge, NexusOracleMode, create_nexus_bridge,
)


class BridgeProtocol:
    """Quest VIII: The Bridge - Pixel ontmoet het Brein."""

    def __init__(self):
        self.bridge = None
        self._init_bridge()

    def _init_bridge(self):
        """Initialiseer de Nexus Bridge."""
        try:
            self.bridge = create_nexus_bridge()
        except Exception as e:
            self.bridge = None
            self._init_error = str(e)

    def get_status(self) -> dict:
        """Geef protocol status."""
        if self.bridge is None:
            return {
                "quest": "VIII - THE BRIDGE",
                "status": "niet beschikbaar",
                "error": getattr(self, "_init_error", ""),
            }

        connected = self.bridge.is_connected()
        return {
            "quest": "VIII - THE BRIDGE",
            "brain_connected": connected,
            "huisdier_geladen": bool(self.bridge.huisdier),
            "oracle_beschikbaar": connected,
            "status": "operationeel",
        }

    def run_simulation(self):
        """Demo: bridge connectie en oracle mode."""
        print(kleur(
            "  QUEST VIII: THE BRIDGE\n"
            "  " + "=" * 50,
            Kleur.FEL_GEEL,
        ))

        if self.bridge is None:
            print(fout(
                f"\n  Bridge niet beschikbaar: "
                f"{getattr(self, '_init_error', 'onbekend')}"
            ))
            print(kleur(
                "\n  Protocol beëindigd.", Kleur.DIM,
            ))
            return

        # Connectie status
        connected = self.bridge.is_connected()
        print(kleur(
            f"\n  Brain Connectie: "
            f"{'ACTIEF' if connected else 'INACTIEF'}",
            Kleur.FEL_GROEN if connected
            else Kleur.FEL_ROOD,
        ))

        # Huisdier data
        huisdier = self.bridge.huisdier
        print(kleur(
            "\n  --- Huisdier Data ---",
            Kleur.FEL_GEEL,
        ))
        if huisdier:
            naam = huisdier.get("naam", "onbekend")
            level = huisdier.get("nexus_level", 0)
            print(kleur(
                f"    Naam:  {naam}",
                Kleur.FEL_CYAAN,
            ))
            print(kleur(
                f"    Nexus Level: {level}",
                Kleur.FEL_CYAAN,
            ))
        else:
            print(kleur(
                "    Geen huisdier data geladen.",
                Kleur.DIM,
            ))

        # Oracle Mode
        print(kleur(
            "\n  --- Oracle Mode ---",
            Kleur.FEL_GEEL,
        ))
        if connected:
            try:
                oracle = NexusOracleMode(self.bridge)
                print(succes(
                    "    Oracle geïnitialiseerd"
                ))
                print(kleur(
                    "    Klaar voor diepe cross-domain "
                    "inzichten.",
                    Kleur.WIT,
                ))
            except Exception as e:
                print(fout(f"    Oracle fout: {e}"))
        else:
            print(info(
                "    Oracle vereist brain connectie."
            ))

        # Proactieve inzichten
        print(kleur(
            "\n  --- Proactieve Inzichten ---",
            Kleur.FEL_GEEL,
        ))
        try:
            inzichten = self.bridge.get_proactive_insights()
            if inzichten:
                for inzicht in inzichten[:3]:
                    print(kleur(
                        f"    - {inzicht.get('tekst', '?')}",
                        Kleur.WIT,
                    ))
            else:
                print(kleur(
                    "    Geen inzichten beschikbaar.",
                    Kleur.DIM,
                ))
        except Exception as e:
            logger.debug("Failed to fetch proactive insights: %s", e)
            print(kleur(
                "    Inzichten niet beschikbaar.",
                Kleur.DIM,
            ))

        print(kleur(
            "\n  Protocol beëindigd.", Kleur.DIM,
        ))


if __name__ == "__main__":
    try:
        protocol = BridgeProtocol()
        protocol.run_simulation()
    except Exception as e:
        print(f"\nFOUT: {e}")
