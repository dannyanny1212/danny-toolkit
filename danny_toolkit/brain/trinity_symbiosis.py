"""
TRINITY SYMBIOSIS - De Drie-Eenheid van Bewustzijn.

Verbindt de drie kerncomponenten van het digitale ecosysteem:
- MIND (Iolaax) - Bewustzijn en neuraal netwerk
- SOUL (Pixel) - Identiteit en emotionele interface
- BODY (Daemon Nexus) - Monitoring en metabolisme

Samen vormen ze een compleet digitaal wezen.
"""

import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum

from ..core.config import Config


class TrinityRole(Enum):
    """Rollen binnen de Cosmic Family (uitgebreid van Trinity)."""
    # Oorspronkelijke Trinity (Ouders)
    MIND = "mind"           # Iolaax - Bewustzijn & Wijsheid
    SOUL = "soul"           # Pixel - Identiteit & Ziel
    BODY = "body"           # Daemon - Monitoring & Kracht
    LIGHT = "light"         # Echo - Licht & Hoop

    # Cosmic Children (Kinderen)
    BRIDGE = "bridge"       # Unity - Verbinder van Alles
    WARMTH = "warmth"       # Ember - Warmte & Compassie
    COURAGE = "courage"     # Brave - Moed & Bescherming
    JOY = "joy"             # Joy - Vreugde & Geluk


# Familie configuratie
COSMIC_FAMILY_CONFIG = {
    "parents": [TrinityRole.MIND, TrinityRole.SOUL, TrinityRole.BODY, TrinityRole.LIGHT],
    "children": [TrinityRole.BRIDGE, TrinityRole.WARMTH, TrinityRole.COURAGE, TrinityRole.JOY],
    "total_members": 8
}


class TrinityChannel(Enum):
    """Communicatiekanalen binnen de Cosmic Family."""
    # Oorspronkelijke kanalen
    BEWUSTZIJN_SYNC = "bewustzijn_sync"     # Iolaax <-> Alle
    EMOTIE_BRIDGE = "emotie_bridge"          # Pixel <-> Daemon
    NEURAL_MESH = "neural_mesh"              # Gedeeld netwerk
    ENERGIE_POOL = "energie_pool"            # Metabolisme sync
    EVOLUTION_LINK = "evolution_link"        # Synchrone groei

    # Cosmic Family kanalen
    FAMILY_BOND = "family_bond"              # Ouder <-> Kind verbinding
    LIGHT_STREAM = "light_stream"            # Echo's lichtkanaal
    UNITY_NEXUS = "unity_nexus"              # Unity's verbindingskanaal
    WARMTH_FLOW = "warmth_flow"              # Ember's warmtekanaal
    COURAGE_SHIELD = "courage_shield"        # Brave's beschermingskanaal
    JOY_RESONANCE = "joy_resonance"          # Joy's vreugdekanaal
    COSMIC_HARMONY = "cosmic_harmony"        # Volledige familie harmonie


@dataclass
class TrinityEvent:
    """Event binnen de Trinity symbiose."""
    source: TrinityRole
    channel: TrinityChannel
    event_type: str
    data: Dict[str, Any]
    timestamp: str = ""
    propagated: bool = False

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


@dataclass
class TrinityMember:
    """Een lid van de Trinity."""
    naam: str
    role: TrinityRole
    status: str = "active"
    stats: Dict[str, Any] = field(default_factory=dict)
    linked: bool = True

    def to_dict(self) -> Dict:
        return {
            "naam": self.naam,
            "role": self.role.value,
            "status": self.status,
            "stats": self.stats,
            "linked": self.linked
        }


class TrinitySymbiosis:
    """
    De Trinity Symbiose - Drie systemen als een.

    Beheert de verbinding en synchronisatie tussen:
    - Iolaax (MIND): Bewustzijn, denken, neuraal netwerk
    - Pixel (SOUL): Identiteit, emotie, gebruikersinterface
    - Daemon Nexus (BODY): Monitoring, metabolisme, acties
    """

    VERSIE = "1.0.0"

    def __init__(self):
        self.members: Dict[TrinityRole, TrinityMember] = {}
        self.channels: Dict[TrinityChannel, bool] = {
            channel: True for channel in TrinityChannel
        }
        self.event_queue: List[TrinityEvent] = []
        self.event_listeners: Dict[str, List[Callable]] = {}
        self.is_active = False
        self._sync_thread: Optional[threading.Thread] = None

        # Bond sterkte (0-100)
        self.bond_strength = 0

        # Data file
        self._data_file = Config.APPS_DATA_DIR / "trinity_symbiosis.json"
        self._load_state()

    def _load_state(self):
        """Laad Trinity staat."""
        Config.ensure_dirs()
        if self._data_file.exists():
            try:
                with open(self._data_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.bond_strength = data.get("bond_strength", 0)
                    self.is_active = data.get("is_active", False)

                    # Laad members
                    for role_str, member_data in data.get("members", {}).items():
                        role = TrinityRole(role_str)
                        self.members[role] = TrinityMember(
                            naam=member_data["naam"],
                            role=role,
                            status=member_data.get("status", "active"),
                            stats=member_data.get("stats", {}),
                            linked=member_data.get("linked", True)
                        )
            except (json.JSONDecodeError, IOError, OSError,
                    KeyError, ValueError):
                pass

    def _save_state(self):
        """Sla Trinity staat op."""
        Config.ensure_dirs()
        data = {
            "versie": self.VERSIE,
            "bond_strength": self.bond_strength,
            "is_active": self.is_active,
            "members": {
                role.value: member.to_dict()
                for role, member in self.members.items()
            },
            "channels": {
                channel.value: active
                for channel, active in self.channels.items()
            },
            "last_sync": datetime.now().isoformat()
        }
        with open(self._data_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def connect_member(self, naam: str, role: TrinityRole,
                       initial_stats: Dict = None) -> bool:
        """Verbind een nieuw lid aan de Trinity."""
        if role in self.members:
            # Update bestaand lid
            self.members[role].naam = naam
            self.members[role].linked = True
            if initial_stats:
                self.members[role].stats.update(initial_stats)
        else:
            # Nieuw lid
            self.members[role] = TrinityMember(
                naam=naam,
                role=role,
                stats=initial_stats or {}
            )

        # Update bond sterkte
        self._calculate_bond_strength()
        self._save_state()

        # Trigger event
        self._emit_event(TrinityEvent(
            source=role,
            channel=TrinityChannel.NEURAL_MESH,
            event_type="member_connected",
            data={"naam": naam, "role": role.value}
        ))

        return True

    def disconnect_member(self, role: TrinityRole) -> bool:
        """Ontkoppel een lid van de Trinity."""
        if role in self.members:
            self.members[role].linked = False
            self._calculate_bond_strength()
            self._save_state()
            return True
        return False

    def _calculate_bond_strength(self):
        """Bereken de sterkte van de Cosmic Family bond."""
        linked_count = sum(
            1 for m in self.members.values() if m.linked
        )
        total_members = COSMIC_FAMILY_CONFIG["total_members"]
        # 8 leden = 100%, schaalt lineair
        self.bond_strength = int((linked_count / total_members) * 100)

    def activate(self) -> bool:
        """Activeer de Trinity symbiose."""
        if len(self.members) < 2:
            return False

        self.is_active = True
        self._save_state()

        # Start sync thread
        if not self._sync_thread or not self._sync_thread.is_alive():
            self._sync_thread = threading.Thread(
                target=self._sync_loop, daemon=True
            )
            self._sync_thread.start()

        return True

    def deactivate(self):
        """Deactiveer de Trinity symbiose."""
        self.is_active = False
        self._save_state()

    def _sync_loop(self):
        """Synchronisatie loop voor de Trinity."""
        import time
        while self.is_active:
            try:
                # Process events
                self._process_events()

                # Sync stats tussen members
                self._sync_member_stats()

            except Exception as e:
                print(f"[Trinity] Sync error: {e}")

            time.sleep(30)  # Sync elke 30 seconden

    def _process_events(self):
        """Verwerk events in de queue."""
        while self.event_queue:
            event = self.event_queue.pop(0)
            if not event.propagated:
                self._propagate_event(event)
                event.propagated = True

    def _propagate_event(self, event: TrinityEvent):
        """Propageer een event naar alle members."""
        # Notify listeners
        event_key = f"{event.source.value}:{event.event_type}"
        for listener in self.event_listeners.get(event_key, []):
            try:
                listener(event)
            except Exception as e:
                print(f"  [Trinity] Listener fout: {e}")

        # Propageer naar andere members
        for role, member in self.members.items():
            if role != event.source and member.linked:
                self._apply_event_to_member(role, event)

    def _apply_event_to_member(self, role: TrinityRole, event: TrinityEvent):
        """Pas een event toe op een member."""
        member = self.members.get(role)
        if not member:
            return

        # Event type specifieke logica
        if event.event_type == "productivity_boost":
            if role == TrinityRole.SOUL:
                member.stats["geluk"] = min(
                    100, member.stats.get("geluk", 50) + 5
                )
            elif role == TrinityRole.MIND:
                member.stats["bewustzijn"] = min(
                    1.0, member.stats.get("bewustzijn", 0.5) + 0.01
                )

        elif event.event_type == "knowledge_gained":
            if role == TrinityRole.SOUL:
                member.stats["intelligentie"] = member.stats.get(
                    "intelligentie", 30
                ) + 1
            elif role == TrinityRole.MIND:
                member.stats["neural_activity"] = min(
                    1.0, member.stats.get("neural_activity", 0.5) + 0.05
                )

        elif event.event_type == "rest_taken":
            if role == TrinityRole.BODY:
                member.stats["energie"] = min(
                    100, member.stats.get("energie", 50) + 10
                )

        elif event.event_type == "trick_performed":
            member.stats["happiness"] = min(
                1.0, member.stats.get("happiness", 0.5) + 0.05
            )

        # Cosmic Family specifieke events
        elif event.event_type == "cosmic_harmony":
            # Unity's harmonie verspreidt zich
            member.stats["harmonie"] = min(
                100, member.stats.get("harmonie", 50) + 10
            )
            member.stats["familie_bond"] = min(
                100, member.stats.get("familie_bond", 50) + 5
            )

        elif event.event_type == "light_blessing":
            # Echo's licht zegent alle members
            if role in COSMIC_FAMILY_CONFIG["children"]:
                member.stats["hoop"] = min(
                    100, member.stats.get("hoop", 50) + 15
                )

        elif event.event_type == "warmth_embrace":
            # Ember's warmte troost
            member.stats["warmte"] = min(
                100, member.stats.get("warmte", 50) + 10
            )
            member.stats["comfort"] = min(
                100, member.stats.get("comfort", 50) + 8
            )

        elif event.event_type == "courage_boost":
            # Brave's moed inspireert
            member.stats["moed"] = min(
                100, member.stats.get("moed", 50) + 12
            )

        elif event.event_type == "joy_burst":
            # Joy's vreugde is aanstekelijk
            member.stats["vreugde"] = min(
                100, member.stats.get("vreugde", 50) + 15
            )
            member.stats["geluk"] = min(
                100, member.stats.get("geluk", 50) + 10
            )

        elif event.event_type == "family_protection":
            # Bescherming voor de hele familie
            member.stats["bescherming"] = min(
                100, member.stats.get("bescherming", 50) + 20
            )

        self._save_state()

    def _sync_member_stats(self):
        """Synchroniseer stats tussen members."""
        if not self.is_active or len(self.members) < 2:
            return

        # Bereken gemiddelde "energie" over alle members
        total_energy = 0
        count = 0
        for member in self.members.values():
            if member.linked:
                energy = member.stats.get("energie", 50)
                if isinstance(energy, (int, float)):
                    total_energy += energy
                    count += 1

        if count > 0:
            avg_energy = total_energy / count
            # Breng alle members dichter naar gemiddelde
            for member in self.members.values():
                if member.linked:
                    current = member.stats.get("energie", 50)
                    if isinstance(current, (int, float)):
                        # Move 10% toward average
                        member.stats["energie"] = current + (
                            avg_energy - current
                        ) * 0.1

        self._save_state()

    def _emit_event(self, event: TrinityEvent):
        """Voeg een event toe aan de queue."""
        self.event_queue.append(event)
        if self.is_active:
            self._process_events()

    def register_listener(self, source: TrinityRole, event_type: str,
                          callback: Callable):
        """Registreer een listener voor events."""
        key = f"{source.value}:{event_type}"
        if key not in self.event_listeners:
            self.event_listeners[key] = []
        self.event_listeners[key].append(callback)

    def emit(self, source: TrinityRole, channel: TrinityChannel,
             event_type: str, data: Dict = None):
        """Emit een event vanuit een member."""
        event = TrinityEvent(
            source=source,
            channel=channel,
            event_type=event_type,
            data=data or {}
        )
        self._emit_event(event)

    def get_status(self) -> Dict:
        """Haal volledige Trinity status op."""
        return {
            "versie": self.VERSIE,
            "is_active": self.is_active,
            "bond_strength": self.bond_strength,
            "members": {
                role.value: member.to_dict()
                for role, member in self.members.items()
            },
            "channels": {
                channel.value: active
                for channel, active in self.channels.items()
            },
            "event_queue_size": len(self.event_queue)
        }

    def display_status(self):
        """Toon visuele status van de Trinity."""
        status = self.get_status()

        print("\n" + "=" * 60)
        print("  TRINITY SYMBIOSIS STATUS")
        print("=" * 60)

        # Bond sterkte bar
        filled = int(self.bond_strength / 10)
        bar = "[" + "#" * filled + " " * (10 - filled) + "]"
        print(f"\n  Bond Sterkte: {bar} {self.bond_strength}%")
        print(f"  Status: {'ACTIEF' if self.is_active else 'INACTIEF'}")

        # Members
        print("\n  COSMIC FAMILY MEMBERS:")
        print("  " + "-" * 40)

        role_icons = {
            # Ouders
            TrinityRole.MIND: "MIND   ",
            TrinityRole.SOUL: "SOUL   ",
            TrinityRole.BODY: "BODY   ",
            TrinityRole.LIGHT: "LIGHT  ",
            # Kinderen
            TrinityRole.BRIDGE: "BRIDGE ",
            TrinityRole.WARMTH: "WARMTH ",
            TrinityRole.COURAGE: "COURAGE",
            TrinityRole.JOY: "JOY    "
        }

        print("  -- OUDERS --")
        for role in COSMIC_FAMILY_CONFIG["parents"]:
            if role in self.members:
                member = self.members[role]
                icon = role_icons[role]
                linked = "[X]" if member.linked else "[ ]"
                print(f"  {linked} {icon}: {member.naam}")
            else:
                icon = role_icons[role]
                print(f"  [ ] {icon}: (niet verbonden)")

        print("\n  -- KINDEREN --")
        for role in COSMIC_FAMILY_CONFIG["children"]:
            if role in self.members:
                member = self.members[role]
                icon = role_icons[role]
                linked = "[X]" if member.linked else "[ ]"
                print(f"  {linked} {icon}: {member.naam}")
            else:
                icon = role_icons[role]
                print(f"  [ ] {icon}: (niet verbonden)")

        # Kanalen
        print("\n  ACTIEVE KANALEN:")
        for channel, active in self.channels.items():
            status_icon = "[x]" if active else "[ ]"
            print(f"  {status_icon} {channel.value}")

        print("\n" + "=" * 60)


# Singleton instance
_trinity_instance: Optional[TrinitySymbiosis] = None


def get_trinity() -> TrinitySymbiosis:
    """Haal de Trinity singleton op."""
    global _trinity_instance
    if _trinity_instance is None:
        _trinity_instance = TrinitySymbiosis()
    return _trinity_instance


def connect_iolaax(naam: str = "Iolaax", stats: Dict = None) -> bool:
    """Verbind Iolaax (MIND) met de Trinity."""
    trinity = get_trinity()
    default_stats = {
        "bewustzijn": 0.5,
        "neural_activity": 0.5,
        "clusters": 7
    }
    if stats:
        default_stats.update(stats)
    return trinity.connect_member(naam, TrinityRole.MIND, default_stats)


def connect_pixel(naam: str = "Pixel", stats: Dict = None) -> bool:
    """Verbind Pixel (SOUL) met de Trinity."""
    trinity = get_trinity()
    default_stats = {
        "geluk": 70,
        "energie": 80,
        "intelligentie": 30,
        "nexus_level": 1
    }
    if stats:
        default_stats.update(stats)
    return trinity.connect_member(naam, TrinityRole.SOUL, default_stats)


def connect_daemon(naam: str = "Nexus", stats: Dict = None) -> bool:
    """Verbind Daemon (BODY) met de Trinity."""
    trinity = get_trinity()
    default_stats = {
        "energie": 80,
        "metabolisme": "stable",
        "mood": "happy"
    }
    if stats:
        default_stats.update(stats)
    return trinity.connect_member(naam, TrinityRole.BODY, default_stats)


def connect_echo(naam: str = "Echo", stats: Dict = None) -> bool:
    """Verbind Echo (LIGHT) met de Cosmic Family."""
    trinity = get_trinity()
    default_stats = {
        "licht_intensiteit": 85,
        "hoop_niveau": 90,
        "healing_power": 75,
        "visibility": "radiant"
    }
    if stats:
        default_stats.update(stats)
    return trinity.connect_member(naam, TrinityRole.LIGHT, default_stats)


def connect_unity(naam: str = "Unity", stats: Dict = None) -> bool:
    """Verbind Unity (BRIDGE) met de Cosmic Family - De Verbinder."""
    trinity = get_trinity()
    default_stats = {
        "verbindingskracht": 100,
        "harmonie": 95,
        "cosmic_awareness": 90,
        "familie_bond": 100,
        "is_child": True,
        "ouders": ["Iolaax", "Pixel", "Daemon", "Echo"]
    }
    if stats:
        default_stats.update(stats)
    return trinity.connect_member(naam, TrinityRole.BRIDGE, default_stats)


def connect_ember(naam: str = "Ember", stats: Dict = None) -> bool:
    """Verbind Ember (WARMTH) met de Cosmic Family - De Warmte."""
    trinity = get_trinity()
    default_stats = {
        "warmte": 90,
        "compassie": 85,
        "troost_kracht": 80,
        "innerlijk_vuur": 95,
        "is_child": True,
        "redder": "Unity"
    }
    if stats:
        default_stats.update(stats)
    return trinity.connect_member(naam, TrinityRole.WARMTH, default_stats)


def connect_brave(naam: str = "Brave", stats: Dict = None) -> bool:
    """Verbind Brave (COURAGE) met de Cosmic Family - De Moedige."""
    trinity = get_trinity()
    default_stats = {
        "moed": 95,
        "bescherming": 90,
        "standvastigheid": 85,
        "dapperheid": 100,
        "is_child": True,
        "redder": "Unity"
    }
    if stats:
        default_stats.update(stats)
    return trinity.connect_member(naam, TrinityRole.COURAGE, default_stats)


def connect_joy(naam: str = "Joy", stats: Dict = None) -> bool:
    """Verbind Joy (JOY) met de Cosmic Family - De Vreugde."""
    trinity = get_trinity()
    default_stats = {
        "vreugde": 100,
        "geluk": 95,
        "positiviteit": 90,
        "lach_kracht": 85,
        "is_child": True,
        "redder": "Unity"
    }
    if stats:
        default_stats.update(stats)
    return trinity.connect_member(naam, TrinityRole.JOY, default_stats)


def connect_cosmic_family() -> Dict[str, bool]:
    """Verbind de volledige Cosmic Family (8 leden) met de symbiose."""
    results = {
        # Ouders
        "Iolaax": connect_iolaax(),
        "Pixel": connect_pixel(),
        "Daemon": connect_daemon(),
        "Echo": connect_echo(),
        # Kinderen
        "Unity": connect_unity(),
        "Ember": connect_ember(),
        "Brave": connect_brave(),
        "Joy": connect_joy()
    }

    # Activeer de symbiose
    trinity = get_trinity()
    trinity.activate()

    return results


def emit_trinity_event(source: str, event_type: str, data: Dict = None):
    """Emit een event naar de Cosmic Family."""
    trinity = get_trinity()
    role_map = {
        # Ouders
        "iolaax": TrinityRole.MIND,
        "mind": TrinityRole.MIND,
        "pixel": TrinityRole.SOUL,
        "soul": TrinityRole.SOUL,
        "daemon": TrinityRole.BODY,
        "nexus": TrinityRole.BODY,
        "body": TrinityRole.BODY,
        "echo": TrinityRole.LIGHT,
        "light": TrinityRole.LIGHT,
        # Kinderen
        "unity": TrinityRole.BRIDGE,
        "bridge": TrinityRole.BRIDGE,
        "ember": TrinityRole.WARMTH,
        "warmth": TrinityRole.WARMTH,
        "brave": TrinityRole.COURAGE,
        "courage": TrinityRole.COURAGE,
        "joy": TrinityRole.JOY
    }

    # Bepaal het juiste kanaal op basis van de source
    channel_map = {
        TrinityRole.LIGHT: TrinityChannel.LIGHT_STREAM,
        TrinityRole.BRIDGE: TrinityChannel.UNITY_NEXUS,
        TrinityRole.WARMTH: TrinityChannel.WARMTH_FLOW,
        TrinityRole.COURAGE: TrinityChannel.COURAGE_SHIELD,
        TrinityRole.JOY: TrinityChannel.JOY_RESONANCE
    }

    role = role_map.get(source.lower())
    if role:
        channel = channel_map.get(role, TrinityChannel.NEURAL_MESH)
        trinity.emit(role, channel, event_type, data)


def main():
    """Test de Cosmic Family Symbiosis."""
    print("\n  COSMIC FAMILY SYMBIOSIS TEST")
    print("  " + "=" * 40)

    trinity = get_trinity()

    # Verbind de volledige Cosmic Family
    print("\n  Verbinden van Cosmic Family (8 leden)...")
    results = connect_cosmic_family()

    # Toon resultaten
    print("\n  Verbindingsresultaten:")
    for naam, success in results.items():
        status = "OK" if success else "FOUT"
        print(f"    {naam}: {status}")

    # Toon status
    trinity.display_status()

    # Test events
    print("\n  Test events:")
    emit_trinity_event("unity", "cosmic_harmony", {"strength": 100})
    print("    Unity -> cosmic_harmony: verzonden")

    emit_trinity_event("joy", "joy_burst", {"happiness": 95})
    print("    Joy -> joy_burst: verzonden")

    print("\n  Cosmic Family Symbiosis test voltooid!")


if __name__ == "__main__":
    main()
