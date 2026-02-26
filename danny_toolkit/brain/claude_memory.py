"""
ClaudeMemory — Persistent Semantisch Geheugen voor Claude Code.

Gebruikt de VectorStore (JSON + cosine similarity) om kennis op te slaan
en semantisch doorzoekbaar te maken. Breidt het vlakke MEMORY.md bestand
uit met onbeperkt vectorgeheugen.

Categorieën:
- architecture: systeemarchitectuur, patronen, conventions
- phases: phase history, commits, test resultaten
- lessons: harde lessen, bugs, fixes
- wirings: cross-module verbindingen
- preferences: gebruikersvoorkeuren
- decisions: architecturale beslissingen

Singleton: ``get_claude_memory()``.
"""

import json
import logging
import os
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

from danny_toolkit.core.config import Config

try:
    from danny_toolkit.core.vector_store import VectorStore
    from danny_toolkit.core.embeddings import get_torch_embedder
    HAS_VECTOR = True
except ImportError:
    HAS_VECTOR = False


# ── Geheugen Categorieën ──

MEMORY_CATEGORIES = [
    "architecture",   # Systeemarchitectuur, patronen
    "phases",         # Phase history, commits
    "lessons",        # Harde lessen, bugs
    "wirings",        # Cross-module verbindingen
    "preferences",    # Gebruikersvoorkeuren
    "decisions",      # Architecturale beslissingen
    "modules",        # Module details, APIs
    "config",         # Configuratie, env vars
    "security",       # Beveiligingslagen, audits
]


class ClaudeMemory:
    """
    Persistent semantisch geheugen voor Claude Code.

    Gebruikt VectorStore voor onbeperkt, doorzoekbaar geheugen.
    Elk geheugen-item heeft een categorie, tekst en metadata.
    """

    def __init__(self):
        """Initializes a ClaudeMemory instance.

 Configures and initializes the underlying VectorStore for storing and retrieving 
 memory data if the required dependencies (HAS_VECTOR) are available.

 Loads the index from the specified file path, which maps IDs to their respective 
 categories, summaries, and timestamps.

 Attributes:
     _store (Optional[VectorStore]): The VectorStore instance for storing memory data.
     _db_path (Path): The file path for storing memory data.
     _index_path (Path): The file path for storing the index data.
     _index (Dict[str, dict]): The in-memory index mapping IDs to their metadata."""
        self._store: Optional[VectorStore] = None
        self._db_path = Config.DATA_DIR / "memory" / "claude_memory.json"
        self._index_path = Config.DATA_DIR / "memory" / "claude_memory_index.json"
        self._index: Dict[str, dict] = {}   # id → {categorie, samenvatting, timestamp}

        # Initialiseer VectorStore
        if HAS_VECTOR:
            try:
                embedder = get_torch_embedder()
                self._store = VectorStore(
                    embedding_provider=embedder,
                    db_file=self._db_path,
                )
            except Exception as e:
                logger.debug("ClaudeMemory VectorStore init: %s", e)

        # Laad index
        self._load_index()

    def _load_index(self):
        """Laad de geheugen-index van schijf."""
        if self._index_path.exists():
            try:
                with open(self._index_path, "r", encoding="utf-8") as f:
                    self._index = json.load(f)
            except Exception as e:
                logger.debug("Index load error: %s", e)

    def _save_index(self):
        """Sla de geheugen-index op."""
        try:
            self._index_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._index_path, "w", encoding="utf-8") as f:
                json.dump(self._index, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.debug("Index save error: %s", e)

    # ── Onthoud ──

    def onthoud(self, tekst: str, categorie: str = "general",
                samenvatting: str = "", metadata: dict = None) -> str:
        """
        Sla een geheugen-item op in de VectorStore.

        Args:
            tekst: De volledige tekst om te onthouden
            categorie: Een van MEMORY_CATEGORIES
            samenvatting: Korte samenvatting (voor index)
            metadata: Extra metadata

        Returns:
            ID van het opgeslagen item
        """
        if not self._store:
            return ""

        entry_id = f"mem_{categorie}_{int(time.time())}_{len(self._index)}"

        meta = {
            "categorie": categorie,
            "samenvatting": samenvatting or tekst[:100],
            "timestamp": datetime.now().isoformat(),
            **(metadata or {}),
        }

        try:
            self._store.voeg_toe([{
                "id": entry_id,
                "tekst": tekst,
                "metadata": meta,
            }])

            # Update index
            self._index[entry_id] = {
                "categorie": categorie,
                "samenvatting": samenvatting or tekst[:100],
                "timestamp": meta["timestamp"],
            }
            self._save_index()

            logger.debug("ClaudeMemory: opgeslagen %s (%s)", entry_id, categorie)
            return entry_id

        except Exception as e:
            logger.debug("ClaudeMemory onthoud error: %s", e)
            return ""

    # ── Herinner ──

    def herinner(self, vraag: str, top_k: int = 5,
                 categorie: str = None, min_score: float = 0.3) -> List[dict]:
        """
        Zoek semantisch in het geheugen.

        Args:
            vraag: De zoekvraag (semantisch)
            top_k: Max aantal resultaten
            categorie: Filter op categorie (optioneel)
            min_score: Minimum cosine similarity

        Returns:
            Lijst van relevante geheugen-items
        """
        if not self._store or not self._store.documenten:
            return []

        filter_fn = None
        if categorie:
            filter_fn = lambda d: d.get("metadata", {}).get("categorie") == categorie

        try:
            results = self._store.zoek(
                query=vraag,
                top_k=top_k,
                filter_fn=filter_fn,
                min_score=min_score,
            )
            return results
        except Exception as e:
            logger.debug("ClaudeMemory herinner error: %s", e)
            return []

    # ── Vergeet ──

    def vergeet(self, entry_id: str) -> bool:
        """Verwijder een geheugen-item."""
        if not self._store:
            return False

        ok = self._store.verwijder(entry_id)
        if ok and entry_id in self._index:
            del self._index[entry_id]
            self._save_index()
        return ok

    # ── Bulk Ingest ──

    def ingest_bestand(self, pad: Path, categorie: str = "general") -> int:
        """
        Ingesteer een markdown/tekst bestand in het geheugen.
        Splitst op secties (## headers) of paragrafen.

        Returns:
            Aantal opgeslagen chunks
        """
        if not self._store or not pad.exists():
            return 0

        try:
            with open(pad, "r", encoding="utf-8") as f:
                inhoud = f.read()
        except Exception as e:
            logger.debug("Bestand lezen error: %s", e)
            return 0

        # Split op markdown secties (## headers)
        chunks = self._split_markdown(inhoud)

        count = 0
        for i, chunk in enumerate(chunks):
            if len(chunk.strip()) < 50:
                continue

            header = chunk.split("\n")[0].strip("# ").strip()
            entry_id = self.onthoud(
                tekst=chunk.strip(),
                categorie=categorie,
                samenvatting=f"{pad.name}: {header[:80]}",
                metadata={"bron": pad.name, "chunk_nr": i},
            )
            if entry_id:
                count += 1

        return count

    @staticmethod
    def _split_markdown(tekst: str) -> List[str]:
        """Split markdown op ## secties."""
        lines = tekst.split("\n")
        chunks = []
        current = []

        for line in lines:
            if line.startswith("## ") and current:
                chunks.append("\n".join(current))
                current = [line]
            else:
                current.append(line)

        if current:
            chunks.append("\n".join(current))

        return chunks

    # ── Bulk Ingest vanuit Memory Directory ──

    def ingest_all_memory_files(self) -> Dict[str, int]:
        """
        Ingesteer alle markdown bestanden uit de Claude memory directory.

        Returns:
            Dict met bestandsnaam → aantal chunks
        """
        memory_dir = Path(os.path.expanduser(
            "~/.claude/projects/C--Users-danny-danny-toolkit/memory"
        ))

        resultaat = {}

        if not memory_dir.exists():
            return resultaat

        # Categoriseer bestanden
        file_categories = {
            "MEMORY.md": "architecture",
            "phases.md": "phases",
            "phase15_cleanup.md": "phases",
        }

        for md_file in memory_dir.glob("*.md"):
            cat = file_categories.get(md_file.name, "general")
            count = self.ingest_bestand(md_file, categorie=cat)
            if count > 0:
                resultaat[md_file.name] = count

        return resultaat

    # ── Statistieken ──

    def get_stats(self) -> dict:
        """Geheugen statistieken."""
        stats = {
            "totaal_items": len(self._index),
            "store_docs": self._store.count() if self._store else 0,
            "categorieën": {},
            "oudste": None,
            "nieuwste": None,
        }

        # Tel per categorie
        for entry in self._index.values():
            cat = entry.get("categorie", "unknown")
            stats["categorieën"][cat] = stats["categorieën"].get(cat, 0) + 1

        # Tijdstempels
        timestamps = [e.get("timestamp", "") for e in self._index.values()]
        if timestamps:
            stats["oudste"] = min(timestamps)
            stats["nieuwste"] = max(timestamps)

        return stats

    def toon_index(self) -> str:
        """Toon leesbare index van alle geheugen-items."""
        if not self._index:
            return "Geheugen is leeg."

        lines = [
            "=" * 60,
            "CLAUDE MEMORY INDEX",
            "=" * 60,
        ]

        # Groepeer per categorie
        per_cat: Dict[str, list] = {}
        for entry_id, meta in self._index.items():
            cat = meta.get("categorie", "unknown")
            if cat not in per_cat:
                per_cat[cat] = []
            per_cat[cat].append((entry_id, meta))

        for cat in sorted(per_cat.keys()):
            lines.append(f"\n[{cat.upper()}] ({len(per_cat[cat])} items)")
            for entry_id, meta in per_cat[cat]:
                ts = meta.get("timestamp", "")[:10]
                sam = meta.get("samenvatting", "")[:60]
                lines.append(f"  {ts} | {sam}")

        lines.append("")
        lines.append("=" * 60)
        lines.append(f"Totaal: {len(self._index)} items in {len(per_cat)} categorieën")
        lines.append("=" * 60)

        return "\n".join(lines)


# ── Singleton Factory ──

_claude_memory_instance: Optional["ClaudeMemory"] = None
_claude_memory_lock = threading.Lock()


def get_claude_memory() -> "ClaudeMemory":
    """Return the process-wide ClaudeMemory singleton."""
    global _claude_memory_instance
    if _claude_memory_instance is None:
        with _claude_memory_lock:
            if _claude_memory_instance is None:
                _claude_memory_instance = ClaudeMemory()
    return _claude_memory_instance
