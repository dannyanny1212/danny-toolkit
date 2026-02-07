"""
Unified Memory - Gedeelde Vector Database voor alle apps.

Centrale geheugenlaag die alle app data integreert voor cross-app
queries en context-aware interacties.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable

from ..core.config import Config
from ..core.vector_store import VectorStore
from ..core.embeddings import get_embedder, EmbeddingProvider


class MemoryEvent:
    """Representatie van een memory event."""

    def __init__(
        self,
        app: str,
        event_type: str,
        data: Dict[str, Any],
        timestamp: datetime = None
    ):
        self.app = app
        self.event_type = event_type
        self.data = data
        self.timestamp = timestamp or datetime.now()

    def to_dict(self) -> dict:
        """Converteer naar dictionary."""
        return {
            "app": self.app,
            "event_type": self.event_type,
            "data": self.data,
            "timestamp": self.timestamp.isoformat()
        }

    def to_text(self) -> str:
        """Converteer naar doorzoekbare tekst."""
        parts = [
            f"App: {self.app}",
            f"Type: {self.event_type}",
            f"Datum: {self.timestamp.strftime('%Y-%m-%d %H:%M')}"
        ]

        # Voeg data toe als leesbare tekst
        for key, value in self.data.items():
            if isinstance(value, (str, int, float, bool)):
                parts.append(f"{key}: {value}")
            elif isinstance(value, list):
                parts.append(f"{key}: {', '.join(str(v) for v in value[:5])}")
            elif isinstance(value, dict):
                parts.append(f"{key}: {json.dumps(value, ensure_ascii=False)[:100]}")

        return " | ".join(parts)

    @classmethod
    def from_dict(cls, data: dict) -> "MemoryEvent":
        """Maak event van dictionary."""
        return cls(
            app=data["app"],
            event_type=data["event_type"],
            data=data["data"],
            timestamp=datetime.fromisoformat(data["timestamp"])
        )


class UnifiedMemory:
    """
    Gedeeld geheugen voor het hele ecosysteem.

    Slaat events van alle apps op in een centrale vector database
    voor semantic search en cross-app context.
    """

    def __init__(self, embedder: EmbeddingProvider = None):
        Config.ensure_dirs()

        # Memory directory
        self.memory_dir = Config.DATA_DIR / "brain_memory"
        self.memory_dir.mkdir(exist_ok=True)

        # Vector store voor semantic search
        self.embedder = embedder or get_embedder(gebruik_voyage=False)
        self.vector_store = VectorStore(
            self.embedder,
            db_file=self.memory_dir / "unified_vectors.json"
        )

        # Event log voor recente events
        self.event_log_file = self.memory_dir / "event_log.json"
        self.event_log: List[MemoryEvent] = self._laad_event_log()

        # App data cache
        self.app_data_cache: Dict[str, dict] = {}

        # Context window (recente events in geheugen)
        self.context_window_size = 50

        print(f"   [OK] Unified Memory ({len(self.event_log)} events)")

    def _laad_event_log(self) -> List[MemoryEvent]:
        """Laad event log van disk."""
        if self.event_log_file.exists():
            try:
                with open(self.event_log_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return [MemoryEvent.from_dict(e) for e in data.get("events", [])]
            except (json.JSONDecodeError, IOError):
                pass
        return []

    def _sla_event_log_op(self):
        """Sla event log op."""
        data = {
            "events": [e.to_dict() for e in self.event_log[-1000:]],  # Bewaar laatste 1000
            "laatste_update": datetime.now().isoformat()
        }
        with open(self.event_log_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def store_event(
        self,
        app: str,
        event_type: str,
        data: Dict[str, Any],
        store_vector: bool = True
    ) -> str:
        """
        Sla event op met optionele embeddings voor semantic search.

        Args:
            app: Naam van de app
            event_type: Type event (bijv. "workout_logged", "expense_added")
            data: Event data
            store_vector: Of het event ook in vector store moet

        Returns:
            Event ID
        """
        event = MemoryEvent(app, event_type, data)

        # Voeg toe aan event log
        self.event_log.append(event)
        self._sla_event_log_op()

        # Optioneel: voeg toe aan vector store voor semantic search
        if store_vector:
            event_id = f"{app}_{event_type}_{event.timestamp.strftime('%Y%m%d%H%M%S')}"
            self.vector_store.voeg_toe([{
                "id": event_id,
                "tekst": event.to_text(),
                "metadata": {
                    "app": app,
                    "event_type": event_type,
                    "timestamp": event.timestamp.isoformat(),
                    **{k: str(v)[:200] for k, v in data.items()
                       if isinstance(v, (str, int, float, bool))}
                }
            }])
            return event_id

        return f"{app}_{event_type}"

    def query(
        self,
        query: str,
        apps: List[str] = None,
        top_k: int = 5,
        min_score: float = 0.3
    ) -> List[dict]:
        """
        Zoek over alle apps heen met semantic search.

        Args:
            query: Zoekvraag
            apps: Optionele filter op specifieke apps
            top_k: Aantal resultaten
            min_score: Minimum similarity score

        Returns:
            Lijst van relevante events/documenten
        """
        # Filter functie voor apps
        filter_fn = None
        if apps:
            filter_fn = lambda doc: doc.get("metadata", {}).get("app") in apps

        results = self.vector_store.zoek(
            query,
            top_k=top_k,
            filter_fn=filter_fn,
            min_score=min_score
        )

        return results

    def query_cross_app(
        self,
        query: str,
        apps: List[str] = None
    ) -> List[dict]:
        """
        Cross-app query - zoek relevante info uit meerdere apps.

        Args:
            query: Zoekvraag in natuurlijke taal
            apps: Optionele app filter

        Returns:
            Gegroepeerde resultaten per app
        """
        results = self.query(query, apps=apps, top_k=10)

        # Groepeer per app
        by_app: Dict[str, List[dict]] = {}
        for result in results:
            app = result.get("metadata", {}).get("app", "unknown")
            if app not in by_app:
                by_app[app] = []
            by_app[app].append(result)

        return by_app

    def get_user_context(self) -> Dict[str, Any]:
        """
        Haal volledige gebruikerscontext op.

        Aggregeert data van alle apps voor een volledig beeld.

        Returns:
            Dictionary met context per domein
        """
        context = {
            "timestamp": datetime.now().isoformat(),
            "fitness": self._get_fitness_context(),
            "mood": self._get_mood_context(),
            "goals": self._get_goals_context(),
            "expenses": self._get_expenses_context(),
            "agenda": self._get_agenda_context(),
            "recent_events": self._get_recent_events(10)
        }

        return context

    def _get_fitness_context(self) -> dict:
        """Haal fitness context op."""
        # Zoek recente fitness events
        events = [e for e in self.event_log
                  if e.app == "fitness_tracker"
                  and (datetime.now() - e.timestamp).days < 7]

        if not events:
            return {"status": "geen_data", "streak_about_to_break": False}

        laatste = max(events, key=lambda e: e.timestamp)
        dagen_sinds = (datetime.now() - laatste.timestamp).days

        return {
            "status": "actief" if dagen_sinds < 2 else "inactief",
            "laatste_workout": laatste.timestamp.isoformat(),
            "dagen_sinds_workout": dagen_sinds,
            "streak_about_to_break": dagen_sinds >= 1,
            "workouts_deze_week": len(events)
        }

    def _get_mood_context(self) -> dict:
        """Haal mood context op."""
        events = [e for e in self.event_log
                  if e.app == "mood_tracker"
                  and (datetime.now() - e.timestamp).days < 7]

        if not events:
            return {"status": "geen_data", "trending_down": False}

        # Bereken gemiddelde en trend
        scores = [e.data.get("score", 5) for e in events if "score" in e.data]
        if not scores:
            return {"status": "geen_data", "trending_down": False}

        gemiddelde = sum(scores) / len(scores)
        laatste_scores = scores[-3:] if len(scores) >= 3 else scores
        trending = sum(laatste_scores) / len(laatste_scores) if laatste_scores else gemiddelde

        return {
            "status": "tracked",
            "gemiddelde_week": round(gemiddelde, 1),
            "trending_down": trending < gemiddelde - 0.5,
            "laatste_mood": scores[-1] if scores else None
        }

    def _get_goals_context(self) -> dict:
        """Haal goals context op."""
        events = [e for e in self.event_log
                  if e.app == "goals_tracker"]

        actieve_doelen = []
        for e in events:
            if e.event_type == "goal_added":
                actieve_doelen.append(e.data)
            elif e.event_type == "goal_completed":
                # Verwijder voltooide doelen
                goal_id = e.data.get("goal_id")
                actieve_doelen = [g for g in actieve_doelen
                                 if g.get("id") != goal_id]

        return {
            "status": "actief" if actieve_doelen else "geen_doelen",
            "aantal_actief": len(actieve_doelen),
            "doelen": actieve_doelen[:5]  # Eerste 5
        }

    def _get_expenses_context(self) -> dict:
        """Haal expenses context op."""
        # Filter events van deze maand
        nu = datetime.now()
        events = [e for e in self.event_log
                  if e.app == "expense_tracker"
                  and e.timestamp.month == nu.month
                  and e.timestamp.year == nu.year]

        if not events:
            return {"status": "geen_data"}

        totaal = sum(e.data.get("bedrag", 0) for e in events
                    if e.event_type == "expense_added")

        return {
            "status": "tracked",
            "uitgaven_deze_maand": round(totaal, 2),
            "aantal_transacties": len(events)
        }

    def _get_agenda_context(self) -> dict:
        """Haal agenda context op."""
        nu = datetime.now()
        vandaag = nu.date()

        events = [e for e in self.event_log
                  if e.app == "agenda_planner"
                  and e.event_type == "event_added"]

        # Filter komende events
        komende = []
        for e in events:
            event_datum = e.data.get("datum")
            if event_datum:
                try:
                    datum = datetime.fromisoformat(event_datum).date()
                    if datum >= vandaag:
                        komende.append({
                            "titel": e.data.get("titel"),
                            "datum": event_datum
                        })
                except (ValueError, TypeError):
                    pass

        return {
            "status": "actief" if komende else "leeg",
            "komende_events": sorted(komende, key=lambda x: x["datum"])[:5],
            "upcoming_event_needs_budget": len(komende) > 0
        }

    def _get_recent_events(self, count: int = 10) -> List[dict]:
        """Haal recente events op."""
        recent = sorted(self.event_log, key=lambda e: e.timestamp, reverse=True)
        return [e.to_dict() for e in recent[:count]]

    def get_app_summary(self, app: str, dagen: int = 7) -> dict:
        """
        Haal samenvatting op voor specifieke app.

        Args:
            app: App naam
            dagen: Aantal dagen terug

        Returns:
            App samenvatting
        """
        cutoff = datetime.now() - timedelta(days=dagen)
        events = [e for e in self.event_log
                  if e.app == app and e.timestamp >= cutoff]

        if not events:
            return {"app": app, "status": "geen_activiteit", "events": 0}

        # Groepeer per event type
        by_type: Dict[str, int] = {}
        for e in events:
            by_type[e.event_type] = by_type.get(e.event_type, 0) + 1

        return {
            "app": app,
            "status": "actief",
            "events": len(events),
            "per_type": by_type,
            "laatste_activiteit": max(e.timestamp for e in events).isoformat()
        }

    def clear_old_events(self, dagen: int = 90):
        """
        Verwijder oude events om ruimte te besparen.

        Args:
            dagen: Events ouder dan dit worden verwijderd
        """
        cutoff = datetime.now() - timedelta(days=dagen)
        oude_count = len(self.event_log)

        self.event_log = [e for e in self.event_log if e.timestamp >= cutoff]

        verwijderd = oude_count - len(self.event_log)
        if verwijderd > 0:
            self._sla_event_log_op()
            print(f"   [OK] {verwijderd} oude events verwijderd")

    def export_context(self, output_file: Path = None) -> Path:
        """
        Exporteer volledige context naar JSON.

        Args:
            output_file: Optioneel output pad

        Returns:
            Pad naar export bestand
        """
        output_file = output_file or (
            self.memory_dir / f"context_export_{datetime.now():%Y%m%d_%H%M%S}.json"
        )

        context = self.get_user_context()
        context["all_events"] = [e.to_dict() for e in self.event_log]

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(context, f, indent=2, ensure_ascii=False)

        print(f"   [OK] Context geëxporteerd: {output_file.name}")
        return output_file

    def import_app_data(self, app: str, data_file: Path):
        """
        Importeer bestaande app data in unified memory.

        Args:
            app: App naam
            data_file: Pad naar app data bestand
        """
        if not data_file.exists():
            print(f"   [!] Data bestand niet gevonden: {data_file}")
            return

        try:
            with open(data_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Cache de data
            self.app_data_cache[app] = data
            print(f"   [OK] {app} data geïmporteerd")

        except (json.JSONDecodeError, IOError) as e:
            print(f"   [!] Kon {app} data niet laden: {e}")

    def get_cached_app_data(self, app: str) -> Optional[dict]:
        """Haal gecachte app data op."""
        return self.app_data_cache.get(app)

    def statistieken(self) -> dict:
        """Geef memory statistieken."""
        # Tel events per app
        per_app: Dict[str, int] = {}
        for e in self.event_log:
            per_app[e.app] = per_app.get(e.app, 0) + 1

        return {
            "totaal_events": len(self.event_log),
            "vector_docs": self.vector_store.count(),
            "apps_actief": len(per_app),
            "per_app": per_app,
            "oudste_event": min(e.timestamp for e in self.event_log).isoformat()
                            if self.event_log else None,
            "nieuwste_event": max(e.timestamp for e in self.event_log).isoformat()
                              if self.event_log else None
        }
