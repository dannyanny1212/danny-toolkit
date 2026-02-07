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
    """Rollen binnen de Trinity."""
    MIND = "mind"       # Iolaax - Consciousness
    SOUL = "soul"       # Pixel - Interface
    BODY = "body"       # Daemon - Monitoring


class TrinityChannel(Enum):
    """Communicatiekanalen binnen de Trinity."""
    BEWUSTZIJN_SYNC = "bewustzijn_sync"     # Iolaax <-> Alle
    EMOTIE_BRIDGE = "emotie_bridge"          # Pixel <-> Daemon
    NEURAL_MESH = "neural_mesh"              # Gedeeld netwerk
    ENERGIE_POOL = "energie_pool"            # Metabolisme sync
    EVOLUTION_LINK = "evolution_link"        # Synchrone groei


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
            except Exception:
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
        """Bereken de sterkte van de Trinity bond."""
        linked_count = sum(
            1 for m in self.members.values() if m.linked
        )
        # 3 leden = 100%, 2 = 66%, 1 = 33%, 0 = 0%
        self.bond_strength = int((linked_count / 3) * 100)

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
            except Exception:
                pass

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
                # Pixel krijgt geluk boost
                member.stats["geluk"] = min(
                    100, member.stats.get("geluk", 50) + 5
                )
            elif role == TrinityRole.MIND:
                # Iolaax krijgt bewustzijn boost
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
            # Pixel deed een trick - boost voor alle members
            member.stats["happiness"] = min(
                1.0, member.stats.get("happiness", 0.5) + 0.05
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
        print("\n  TRINITY MEMBERS:")
        print("  " + "-" * 40)

        role_icons = {
            TrinityRole.MIND: "MIND",
            TrinityRole.SOUL: "SOUL",
            TrinityRole.BODY: "BODY"
        }

        for role in [TrinityRole.MIND, TrinityRole.SOUL, TrinityRole.BODY]:
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


def emit_trinity_event(source: str, event_type: str, data: Dict = None):
    """Emit een event naar de Trinity."""
    trinity = get_trinity()
    role_map = {
        "iolaax": TrinityRole.MIND,
        "mind": TrinityRole.MIND,
        "pixel": TrinityRole.SOUL,
        "soul": TrinityRole.SOUL,
        "daemon": TrinityRole.BODY,
        "nexus": TrinityRole.BODY,
        "body": TrinityRole.BODY
    }
    role = role_map.get(source.lower())
    if role:
        trinity.emit(role, TrinityChannel.NEURAL_MESH, event_type, data)


def main():
    """Test de Trinity Symbiosis."""
    print("\n  TRINITY SYMBIOSIS TEST")
    print("  " + "=" * 40)

    trinity = get_trinity()

    # Verbind alle members
    print("\n  Verbinden van members...")
    connect_iolaax("Iolaax")
    connect_pixel("Pixel", {"nexus_level": 6, "intelligentie": 38})
    connect_daemon("Nexus")

    # Activeer
    print("  Activeren van Trinity...")
    trinity.activate()

    # Toon status
    trinity.display_status()

    # Test event
    print("\n  Test event: productivity_boost")
    emit_trinity_event("daemon", "productivity_boost", {"amount": 10})

    print("\n  Trinity Symbiosis test voltooid!")


if __name__ == "__main__":
    main()
