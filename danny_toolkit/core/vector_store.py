"""
Vector database met JSON backend.
Versie 2.0 - Met backup/restore, statistieken en filtering.
"""

import json
import math
import shutil
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Callable
from .config import Config
from .embeddings import EmbeddingProvider


class VectorStore:
    """
    Persistente vector store met JSON backend.
    Werkt altijd, geen externe dependencies.
    """

    def __init__(self, embedding_provider: EmbeddingProvider, db_file: Path = None):
        self.embedder = embedding_provider
        self.db_file = db_file or Config.VECTOR_DB_FILE
        self.documenten: Dict[str, dict] = {}
        self._statistieken = {
            "queries": 0,
            "toevoegingen": 0,
            "verwijderingen": 0,
            "laatste_query": None,
            "laatste_toevoeging": None
        }

        # Laad bestaande data
        if self.db_file.exists():
            with open(self.db_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Ondersteuning voor oud en nieuw format
                if isinstance(data, dict) and "documenten" in data:
                    self.documenten = data["documenten"]
                    self._statistieken.update(data.get("statistieken", {}))
                else:
                    self.documenten = data
            print(f"   [OK] Vector DB geladen ({len(self.documenten)} docs)")
        else:
            print(f"   [OK] Vector DB (nieuw)")

    def _opslaan(self):
        """Sla database op naar disk."""
        self.db_file.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "documenten": self.documenten,
            "statistieken": self._statistieken,
            "versie": "2.0"
        }
        with open(self.db_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def voeg_toe(self, documenten: list):
        """
        Voeg documenten toe.
        Args: documenten: List van {"id": str, "tekst": str, "metadata": dict}
        """
        if not documenten:
            return

        teksten = [d["tekst"] for d in documenten]
        embeddings = self.embedder.embed(teksten)

        for doc, emb in zip(documenten, embeddings):
            self.documenten[doc["id"]] = {
                "tekst": doc["tekst"],
                "metadata": doc.get("metadata", {}),
                "embedding": emb,
                "toegevoegd_op": datetime.now().isoformat()
            }

        self._statistieken["toevoegingen"] += len(documenten)
        self._statistieken["laatste_toevoeging"] = datetime.now().isoformat()

        self._opslaan()
        print(f"   [OK] {len(documenten)} documenten toegevoegd")

    def zoek(self, query: str, top_k: int = None,
             filter_fn: Callable[[dict], bool] = None,
             min_score: float = 0.0) -> list:
        """
        Zoek relevante documenten met Cosine Similarity.

        Args:
            query: Zoekquery
            top_k: Aantal resultaten (default uit config)
            filter_fn: Optionele filter functie voor metadata
            min_score: Minimum similarity score

        Returns:
            Lijst van relevante documenten
        """
        top_k = top_k or Config.TOP_K

        if not self.documenten:
            return []

        query_emb = self.embedder.embed_query(query)
        scores = []

        for doc_id, data in self.documenten.items():
            # Filter op metadata
            if filter_fn and not filter_fn(data):
                continue

            score = self._cosine_similarity(query_emb, data["embedding"])

            if score >= min_score:
                scores.append({
                    "id": doc_id,
                    "tekst": data["tekst"],
                    "metadata": data["metadata"],
                    "score": score
                })

        scores.sort(key=lambda x: x["score"], reverse=True)

        # Update statistieken
        self._statistieken["queries"] += 1
        self._statistieken["laatste_query"] = datetime.now().isoformat()

        return scores[:top_k]

    def zoek_op_metadata(self, veld: str, waarde, exact: bool = True) -> list:
        """
        Zoek documenten op metadata veld.

        Args:
            veld: Metadata veld naam
            waarde: Gezochte waarde
            exact: Exacte match (False voor contains)

        Returns:
            Lijst van matchende documenten
        """
        resultaten = []

        for doc_id, data in self.documenten.items():
            meta_waarde = data["metadata"].get(veld)

            if meta_waarde is None:
                continue

            match = False
            if exact:
                match = meta_waarde == waarde
            else:
                # String contains check
                match = str(waarde).lower() in str(meta_waarde).lower()

            if match:
                resultaten.append({
                    "id": doc_id,
                    "tekst": data["tekst"],
                    "metadata": data["metadata"]
                })

        return resultaten

    def _cosine_similarity(self, vec1: list, vec2: list) -> float:
        """Bereken cosine similarity tussen twee vectoren."""
        dot = sum(a * b for a, b in zip(vec1, vec2))
        mag1 = math.sqrt(sum(a**2 for a in vec1))
        mag2 = math.sqrt(sum(b**2 for b in vec2))
        if mag1 == 0 or mag2 == 0:
            return 0.0
        return dot / (mag1 * mag2)

    def verwijder(self, doc_id: str) -> bool:
        """
        Verwijder een document.

        Args:
            doc_id: ID van het document

        Returns:
            True als verwijderd, False als niet gevonden
        """
        if doc_id in self.documenten:
            del self.documenten[doc_id]
            self._statistieken["verwijderingen"] += 1
            self._opslaan()
            return True
        return False

    def verwijder_meerdere(self, doc_ids: List[str]) -> int:
        """
        Verwijder meerdere documenten.

        Returns:
            Aantal verwijderde documenten
        """
        verwijderd = 0
        for doc_id in doc_ids:
            if doc_id in self.documenten:
                del self.documenten[doc_id]
                verwijderd += 1

        if verwijderd > 0:
            self._statistieken["verwijderingen"] += verwijderd
            self._opslaan()

        return verwijderd

    def wis(self):
        """Wis alle documenten."""
        self.documenten = {}
        self._opslaan()

    def count(self) -> int:
        """Aantal documenten."""
        return len(self.documenten)

    def get(self, doc_id: str) -> Optional[dict]:
        """
        Haal specifiek document op.

        Returns:
            Document data of None
        """
        if doc_id in self.documenten:
            data = self.documenten[doc_id]
            return {
                "id": doc_id,
                "tekst": data["tekst"],
                "metadata": data["metadata"]
            }
        return None

    def update_metadata(self, doc_id: str, metadata: dict) -> bool:
        """
        Update metadata van een document.

        Args:
            doc_id: Document ID
            metadata: Nieuwe metadata (wordt gemerged)

        Returns:
            True als succesvol
        """
        if doc_id in self.documenten:
            self.documenten[doc_id]["metadata"].update(metadata)
            self._opslaan()
            return True
        return False

    # =========================================================================
    # BACKUP EN RESTORE
    # =========================================================================

    def maak_backup(self, backup_naam: str = None) -> Path:
        """
        Maak een backup van de database.

        Args:
            backup_naam: Optionele naam voor de backup

        Returns:
            Pad naar backup bestand
        """
        Config.ensure_dirs()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_naam = backup_naam or f"vector_db_backup_{timestamp}"
        backup_pad = Config.BACKUP_DIR / f"{backup_naam}.json"

        # Kopieer huidige database
        data = {
            "documenten": self.documenten,
            "statistieken": self._statistieken,
            "backup_datum": datetime.now().isoformat(),
            "origineel_bestand": str(self.db_file),
            "versie": "2.0"
        }

        with open(backup_pad, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"   [OK] Backup gemaakt: {backup_pad.name}")
        return backup_pad

    def herstel_backup(self, backup_pad: Path) -> bool:
        """
        Herstel database vanuit backup.

        Args:
            backup_pad: Pad naar backup bestand

        Returns:
            True als succesvol
        """
        if not backup_pad.exists():
            print(f"   [X] Backup niet gevonden: {backup_pad}")
            return False

        try:
            with open(backup_pad, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.documenten = data.get("documenten", {})
            self._statistieken = data.get("statistieken", self._statistieken)
            self._opslaan()

            print(f"   [OK] Backup hersteld: {len(self.documenten)} documenten")
            return True

        except (json.JSONDecodeError, IOError) as e:
            print(f"   [X] Backup herstel mislukt: {e}")
            return False

    def lijst_backups(self) -> List[dict]:
        """
        Lijst alle beschikbare backups.

        Returns:
            Lijst van backup informatie
        """
        backups = []

        if not Config.BACKUP_DIR.exists():
            return backups

        for bestand in Config.BACKUP_DIR.glob("vector_db_backup_*.json"):
            try:
                stat = bestand.stat()
                backups.append({
                    "naam": bestand.stem,
                    "pad": bestand,
                    "grootte": stat.st_size,
                    "datum": datetime.fromtimestamp(stat.st_mtime)
                })
            except OSError:
                continue

        backups.sort(key=lambda x: x["datum"], reverse=True)
        return backups

    # =========================================================================
    # STATISTIEKEN
    # =========================================================================

    def statistieken(self) -> dict:
        """
        Uitgebreide statistieken over de database.

        Returns:
            Dictionary met statistieken
        """
        stats = {
            "totaal_documenten": len(self.documenten),
            "queries_uitgevoerd": self._statistieken["queries"],
            "documenten_toegevoegd": self._statistieken["toevoegingen"],
            "documenten_verwijderd": self._statistieken["verwijderingen"],
            "laatste_query": self._statistieken["laatste_query"],
            "laatste_toevoeging": self._statistieken["laatste_toevoeging"]
        }

        if self.documenten:
            # Embedding dimensies
            eerste_doc = next(iter(self.documenten.values()))
            stats["embedding_dimensies"] = len(eerste_doc.get("embedding", []))

            # Tekst statistieken
            tekst_lengtes = [
                len(d["tekst"]) for d in self.documenten.values()
            ]
            stats["gem_tekst_lengte"] = sum(tekst_lengtes) // len(tekst_lengtes)
            stats["min_tekst_lengte"] = min(tekst_lengtes)
            stats["max_tekst_lengte"] = max(tekst_lengtes)

            # Metadata velden
            alle_velden = set()
            for doc in self.documenten.values():
                alle_velden.update(doc.get("metadata", {}).keys())
            stats["metadata_velden"] = list(alle_velden)

            # Database grootte
            stats["db_grootte_bytes"] = self.db_file.stat().st_size if \
                self.db_file.exists() else 0

        return stats

    def toon_statistieken(self) -> str:
        """
        Genereer leesbare statistieken.

        Returns:
            Geformatteerde statistieken string
        """
        stats = self.statistieken()

        lijnen = []
        lijnen.append("=" * 50)
        lijnen.append("VECTOR DATABASE STATISTIEKEN")
        lijnen.append("=" * 50)

        lijnen.append(f"\n[Algemeen]")
        lijnen.append(f"  Documenten:      {stats['totaal_documenten']}")
        lijnen.append(f"  Queries:         {stats['queries_uitgevoerd']}")
        lijnen.append(f"  Toevoegingen:    {stats['documenten_toegevoegd']}")
        lijnen.append(f"  Verwijderingen:  {stats['documenten_verwijderd']}")

        if stats['laatste_query']:
            lijnen.append(f"  Laatste query:   {stats['laatste_query'][:19]}")
        if stats['laatste_toevoeging']:
            lijnen.append(f"  Laatste toevoeging: {stats['laatste_toevoeging'][:19]}")

        if stats['totaal_documenten'] > 0:
            lijnen.append(f"\n[Embeddings]")
            lijnen.append(f"  Dimensies:       {stats.get('embedding_dimensies', 'N/A')}")

            lijnen.append(f"\n[Tekst]")
            lijnen.append(f"  Gemiddeld:       {stats.get('gem_tekst_lengte', 0)} karakters")
            lijnen.append(f"  Minimum:         {stats.get('min_tekst_lengte', 0)} karakters")
            lijnen.append(f"  Maximum:         {stats.get('max_tekst_lengte', 0)} karakters")

            if stats.get("metadata_velden"):
                lijnen.append(f"\n[Metadata velden]")
                for veld in stats["metadata_velden"]:
                    lijnen.append(f"  - {veld}")

            # Format grootte
            grootte = stats.get("db_grootte_bytes", 0)
            if grootte > 1024 * 1024:
                grootte_str = f"{grootte / 1024 / 1024:.1f} MB"
            elif grootte > 1024:
                grootte_str = f"{grootte / 1024:.1f} KB"
            else:
                grootte_str = f"{grootte} B"
            lijnen.append(f"\n[Opslag]")
            lijnen.append(f"  Database:        {grootte_str}")

        lijnen.append("=" * 50)

        return "\n".join(lijnen)

    # =========================================================================
    # EXPORT EN IMPORT
    # =========================================================================

    def exporteer_teksten(self, output_pad: Path = None) -> Path:
        """
        Exporteer alle teksten naar een bestand.

        Args:
            output_pad: Optioneel output pad

        Returns:
            Pad naar geëxporteerd bestand
        """
        Config.ensure_dirs()
        output_pad = output_pad or (
            Config.OUTPUT_DIR / f"teksten_export_{datetime.now():%Y%m%d_%H%M%S}.txt"
        )

        with open(output_pad, "w", encoding="utf-8") as f:
            for doc_id, data in self.documenten.items():
                f.write(f"=== {doc_id} ===\n")
                f.write(data["tekst"])
                f.write("\n\n")

        print(f"   [OK] Teksten geëxporteerd: {output_pad.name}")
        return output_pad

    def importeer_teksten(self, input_pad: Path, bron: str = None) -> int:
        """
        Importeer teksten uit bestand.

        Args:
            input_pad: Pad naar tekstbestand
            bron: Bron naam voor metadata

        Returns:
            Aantal geïmporteerde documenten
        """
        if not input_pad.exists():
            print(f"   [X] Bestand niet gevonden: {input_pad}")
            return 0

        with open(input_pad, "r", encoding="utf-8") as f:
            inhoud = f.read()

        # Simpele chunking op paragrafen
        paragrafen = [p.strip() for p in inhoud.split("\n\n") if p.strip()]

        documenten = []
        for i, tekst in enumerate(paragrafen):
            if len(tekst) > 50:  # Filter zeer korte stukken
                documenten.append({
                    "id": f"{input_pad.stem}_{i}",
                    "tekst": tekst,
                    "metadata": {
                        "bron": bron or input_pad.name,
                        "chunk_nr": i
                    }
                })

        if documenten:
            self.voeg_toe(documenten)

        return len(documenten)


class VectorStoreManager:
    """Manager voor meerdere vector stores."""

    def __init__(self, embedder: EmbeddingProvider):
        self.embedder = embedder
        self.stores: Dict[str, VectorStore] = {}
        self._laad_stores()

    def _laad_stores(self):
        """Laad bestaande stores."""
        if Config.RAG_DATA_DIR.exists():
            for bestand in Config.RAG_DATA_DIR.glob("vector_db_*.json"):
                naam = bestand.stem.replace("vector_db_", "")
                if naam and naam != "backup":
                    self.stores[naam] = VectorStore(
                        self.embedder,
                        db_file=bestand
                    )

    def maak(self, naam: str) -> VectorStore:
        """Maak nieuwe store."""
        if naam in self.stores:
            return self.stores[naam]

        db_file = Config.RAG_DATA_DIR / f"vector_db_{naam}.json"
        store = VectorStore(self.embedder, db_file=db_file)
        self.stores[naam] = store
        return store

    def get(self, naam: str) -> Optional[VectorStore]:
        """Haal store op bij naam."""
        return self.stores.get(naam)

    def verwijder(self, naam: str) -> bool:
        """Verwijder een store."""
        if naam in self.stores:
            store = self.stores[naam]
            if store.db_file.exists():
                store.db_file.unlink()
            del self.stores[naam]
            return True
        return False

    def lijst(self) -> List[str]:
        """Lijst van alle store namen."""
        return list(self.stores.keys())
