"""
TheLibrarian — De Bibliothecaris van Project Omega.



Beheert de Knowledge Base: leest bestanden, chunked
tekst en slaat op in ChromaDB met sentence-transformer
embeddings (paraphrase-multilingual-mpnet-base-v2).
"""

from __future__ import annotations

import os

# Forceer TQDM (sentence-transformers) om stil te zijn
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["TQDM_DISABLE"] = "True"

import json
import logging
import time
from pathlib import Path
from typing import List

logger = logging.getLogger(__name__)

from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
)
from rich.table import Table

# ─── Config import (root config.py) ───
import sys

_root = Path(__file__).parent.parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from config import CHROMA_DIR, DOCS_DIR

# ─── Constanten ───

COLLECTION_NAME = "danny_knowledge"
try:
    from danny_toolkit.core.config import Config as _Cfg
    CHUNK_SIZE = getattr(_Cfg, 'CHUNK_SIZE', 350)
except ImportError:
    CHUNK_SIZE = 350
CHUNK_OVERLAP = 50
EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"

# Lazy import TheCortex voor Knowledge Graph population
try:
    from danny_toolkit.brain.cortex import TheCortex
    _HAS_CORTEX = True
except ImportError:
    _HAS_CORTEX = False

REPAIR_LOG_PAD = _root / "data" / "repair_logs.json"

# Maximale bestandsgrootte (10 MB) — voorkomt memory exhaustion
_MAX_FILE_BYTES = 10 * 1024 * 1024

SUPPORTED_EXT = {
    ".txt", ".md", ".py", ".json", ".csv",
    ".log", ".yaml", ".yml", ".toml", ".cfg",
    ".ini", ".xml", ".html", ".pdf",
}

SKIP_FILES = {
    "interactions.json",
    "vector_db.json",
}

console = Console()


def _sanitize_error(msg: str) -> str:
    """Strip API keys uit error messages (anti-leak)."""
    try:
        from danny_toolkit.core.config import Config as _Cfg
        for attr in ("VOYAGE_API_KEY", "GROQ_API_KEY"):
            key = getattr(_Cfg, attr, "")
            if key and key in msg:
                msg = msg.replace(key, "***REDACTED***")
    except ImportError:
        pass
    return msg


class TheLibrarian:
    """De Bibliothecaris — beheert de Knowledge Base.

    Leest bestanden, chunked tekst en slaat op in
    ChromaDB met sentence-transformer embeddings.
    """

    def __init__(self, reset: object=False) -> None:
        """Init  ."""
        console.print(
            "[bold cyan]Initializing"
            " The Librarian...[/bold cyan]"
        )

        import chromadb

        # Database (persistent op schijf)
        os.makedirs(CHROMA_DIR, exist_ok=True)
        self.client = chromadb.PersistentClient(
            path=str(CHROMA_DIR)
        )

        # Reset indien gevraagd
        if reset:
            try:
                self.client.delete_collection(
                    COLLECTION_NAME
                )
                console.print(
                    "[yellow]Database gereset."
                    "[/yellow]"
                )
            except Exception as e:
                logger.debug("Failed to delete collection on reset: %s", e)

        # Embedding model — Voyage AI of fallback
        from danny_toolkit.core.embeddings import get_chroma_embed_fn
        import io as _io
        _old_stdout = sys.stdout
        _old_stderr = sys.stderr
        sys.stdout = _io.StringIO()
        sys.stderr = _io.StringIO()
        try:
            self.embed_fn = get_chroma_embed_fn()
        finally:
            sys.stdout = _old_stdout
            sys.stderr = _old_stderr

        # Collectie maken of laden
        self.collection = (
            self.client.get_or_create_collection(
                name=COLLECTION_NAME,
                embedding_function=self.embed_fn,
                metadata={
                    "description":
                        "Danny Toolkit Knowledge Base",
                },
            )
        )

        # Phase 34: Lazy ShardRouter
        self._shard_router = None

    def _get_shard_router(self) -> None:
        """Lazy init ShardRouter (Phase 34)."""
        if self._shard_router is not None:
            return self._shard_router
        try:
            from danny_toolkit.core.config import Config as _Cfg
            if not getattr(_Cfg, "SHARD_ENABLED", False):
                return None
            from danny_toolkit.core.shard_router import (
                get_shard_router,
            )
            self._shard_router = get_shard_router()
            return self._shard_router
        except Exception as e:
            logger.debug("ShardRouter init fout: %s", e)
            return None

    # ─── Bestandslezers ───

    def _lees_pdf(self, pad: object) -> None:
        """Lees tekst uit een PDF bestand."""
        try:
            from pypdf import PdfReader
            reader = PdfReader(str(pad))
            tekst = ""
            for pagina in reader.pages:
                extracted = pagina.extract_text()
                if extracted:
                    tekst += extracted + "\n"
            return tekst
        except Exception as e:
            console.print(
                f"  [red]Fout bij PDF {pad.name}:"
                f" {_sanitize_error(str(e))}[/red]"
            )
            return ""

    def _lees_tekst(self, pad: object) -> None:
        """Lees tekst uit een tekstbestand."""
        encodings = ["utf-8", "latin-1", "cp1252"]
        for enc in encodings:
            try:
                return pad.read_text(encoding=enc)
            except (UnicodeDecodeError, Exception):
                continue
        console.print(
            f"  [red]Kan {pad.name} niet lezen[/red]"
        )
        return ""

    def _validate_pad(self, pad: Path) -> bool:
        """Security: valideer dat pad binnen DOCS_DIR blijft (anti-traversal)."""
        try:
            resolved = pad.resolve()
            docs_resolved = Path(DOCS_DIR).resolve()
            return str(resolved).startswith(str(docs_resolved))
        except (OSError, ValueError):
            return False

    def _lees_bestand(self, pad: object) -> None:
        """Lees een bestand op basis van extensie.

        Security guards:
        - Path traversal check (moet binnen DOCS_DIR blijven)
        - File size limit (_MAX_FILE_BYTES)
        - Extension whitelist (SUPPORTED_EXT)
        """
        pad = Path(pad)

        # Guard 1: path traversal
        if not self._validate_pad(pad):
            logger.warning("Path traversal geblokkeerd: %s", pad.name)
            return ""

        # Guard 2: extensie whitelist
        if pad.suffix.lower() not in SUPPORTED_EXT:
            logger.warning("Extensie niet toegestaan: %s", pad.suffix)
            return ""

        # Guard 3: file size limit
        try:
            if pad.stat().st_size > _MAX_FILE_BYTES:
                logger.warning("Bestand te groot (%d bytes): %s", pad.stat().st_size, pad.name)
                return ""
        except OSError:
            return ""

        if pad.suffix.lower() == ".pdf":
            return self._lees_pdf(pad)
        return self._lees_tekst(pad)

    # ─── Scanner ───

    def scan_bestanden(self, pad: object) -> List[Path]:
        """Vind alle ondersteunde bestanden recursief."""
        pad = Path(pad)
        if not pad.exists():
            os.makedirs(str(pad), exist_ok=True)
            console.print(
                f"[yellow]Map aangemaakt: {pad}."
                " Zet hier je bestanden in![/yellow]"
            )
            return []

        bestanden = []
        for f in sorted(pad.rglob("*")):
            if (
                f.is_file()
                and f.suffix.lower() in SUPPORTED_EXT
                and f.name not in SKIP_FILES
            ):
                bestanden.append(f)
        return bestanden

    # ─── Chunking ───

    def chunk_text(self, text: str, chunk_size: object=CHUNK_SIZE,
                   overlap: object=CHUNK_OVERLAP) -> List[str]:
        """Hakt tekst in overlappende chunks."""
        from danny_toolkit.core.document_processor import (
            DocumentProcessor,
        )
        processor = DocumentProcessor(
            chunk_size=chunk_size * 6,
            overlap=overlap * 6,
        )
        chunk_dicts = processor.chunk_tekst(
            text, "doc"
        )
        return [c["tekst"] for c in chunk_dicts]

    # ─── Ingest Pipeline ───

    def ingest(self, pad: object, chunk_size: object=CHUNK_SIZE,
               overlap: object=CHUNK_OVERLAP) -> None:
        """Hoofdproces: scan -> lees -> chunk -> opslaan.
        """
        start_time = time.time()

        console.print(Panel(
            "[bold magenta]UNIVERSAL INGEST PROTOCOL"
            "[/bold magenta]\n"
            "[dim]De Digitale Stofzuiger v2.0[/dim]",
            border_style="magenta",
        ))

        # 1. Scan bestanden
        bestanden = self.scan_bestanden(pad)
        if not bestanden:
            console.print(
                "[red]Geen bestanden gevonden![/red]"
            )
            return

        bestaand = self.collection.count()
        console.print(
            f"\n[cyan]Gevonden:[/cyan]"
            f" {len(bestanden)} bestanden in {pad}"
        )
        console.print(
            f"  Collectie: [green]{COLLECTION_NAME}"
            f"[/green]"
            f" ({bestaand} bestaande chunks)"
        )
        model_naam = (
            getattr(self.embed_fn, "model", None)
            or EMBEDDING_MODEL
        )
        console.print(
            f"  Model: [green]{model_naam}"
            f"[/green]"
        )

        # 2. Lees, chunk en upsert
        totaal_chunks = 0

        with Progress(
            SpinnerColumn(),
            TextColumn(
                "[progress.description]"
                "{task.description}"
            ),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        ) as progress:
            taak = progress.add_task(
                "Bestanden verwerken...",
                total=len(bestanden),
            )

            for bestand in bestanden:
                naam = bestand.name
                rel_pad = str(
                    bestand.relative_to(Path(pad))
                )

                # Lees bestand
                tekst = self._lees_bestand(bestand)
                if not tekst.strip():
                    progress.advance(taak)
                    continue

                # Chunk
                chunks = self.chunk_text(
                    tekst, chunk_size, overlap
                )
                if not chunks:
                    progress.advance(taak)
                    continue

                # Bereid batch voor
                ids = []
                documents = []
                metadatas = []

                for i, chunk in enumerate(chunks):
                    # Sanitize ID: alleen alfanumeriek + veilige tekens
                    safe_pad = "".join(
                        c if c.isalnum() or c in "._-/" else "_"
                        for c in rel_pad
                    )
                    ids.append(
                        f"{safe_pad}::chunk_{i}"
                    )
                    documents.append(chunk)
                    metadatas.append({
                        "bron": naam,
                        "pad": rel_pad,
                        "chunk_nr": i,
                        "totaal_chunks": len(chunks),
                        "extensie": bestand.suffix,
                        "grootte_bytes":
                            bestand.stat().st_size,
                    })

                # Upsert — stealth batches: grote payload + 22s cooldown
                # Voyage free tier: 3 RPM = 1 call/20s. 22s = mathematisch veilig.
                _MICRO_BATCH = 100
                if ids:
                    for b_start in range(0, len(ids), _MICRO_BATCH):
                        b_end = min(b_start + _MICRO_BATCH, len(ids))
                        self.collection.upsert(
                            ids=ids[b_start:b_end],
                            documents=documents[b_start:b_end],
                            metadatas=metadatas[b_start:b_end],
                        )
                        if b_end < len(ids):
                            time.sleep(22)
                    totaal_chunks += len(ids)

                    # Phase 34: ShardRouter parallel ingest
                    shard_router = self._get_shard_router()
                    if shard_router is not None:
                        try:
                            shard_docs = [
                                {"id": i, "tekst": d, "metadata": m}
                                for i, d, m in zip(ids, documents, metadatas)
                            ]
                            shard_router.ingest(shard_docs)
                        except Exception as e:
                            logger.debug("ShardRouter ingest fout: %s", e)

                    # Auto-extract triples voor Knowledge Graph
                    if _HAS_CORTEX and documents:
                        try:
                            import asyncio as _aio
                            cortex = TheCortex()
                            for chunk in documents[:3]:
                                triples = _aio.run(cortex.extract_triples(chunk))
                                for t in triples:
                                    cortex.add_triple(
                                        t.subject, t.predicaat, t.object,
                                        t.confidence, t.bron,
                                    )
                        except Exception as e:
                            logger.debug("Failed to extract triples for Knowledge Graph: %s", e)

                progress.advance(taak)

        # 3. Resultaat
        elapsed = time.time() - start_time
        nieuw_totaal = self.collection.count()

        result_table = Table(
            title="INGEST RESULTAAT",
            border_style="green",
            show_header=False,
        )
        result_table.add_column("label", width=25)
        result_table.add_column("waarde")

        result_table.add_row(
            "Bestanden gescand",
            f"[cyan]{len(bestanden)}[/cyan]",
        )
        result_table.add_row(
            "Chunks verwerkt",
            f"[green]{totaal_chunks}[/green]",
        )
        result_table.add_row(
            "Totaal in database",
            f"[bold green]{nieuw_totaal}"
            f"[/bold green]",
        )
        result_table.add_row(
            "Chunk grootte",
            f"{chunk_size} woorden"
            f" (overlap: {overlap})",
        )
        result_table.add_row(
            "Embedding model",
            f"[cyan]{model_naam}[/cyan]",
        )
        dim_info = getattr(self.embed_fn, '_target_dim', None)
        if dim_info and dim_info < 1024:
            result_table.add_row("Dimensie", f"[green]{dim_info}d (MRL)[/green]")
        else:
            result_table.add_row("Dimensie", f"[cyan]{dim_info or 1024}d[/cyan]")
        result_table.add_row(
            "Database locatie",
            f"[dim]{CHROMA_DIR}[/dim]",
        )
        result_table.add_row(
            "Tijd",
            f"[cyan]{elapsed:.1f}s[/cyan]",
        )

        console.print()
        console.print(result_table)
        console.print(
            "\n[bold green]Ingest compleet!"
            "[/bold green]"
        )

    # ─── Atomic Staging (crash-proof ingest) ───

    def _create_staging_collection(self, job_id: str) -> object:
        """Maak een tijdelijke staging-collectie voor atomic ingest.

        Data wordt hier eerst naartoe geschreven. Pas na succesvolle
        verwerking wordt het naar de hoofdcollectie geswapped.
        Bij crash/error wordt de staging collectie gedropt — geen
        half-bakken data in de hoofdcollectie.
        """
        staging_name = f"staging-{job_id}"
        collection = self.client.get_or_create_collection(
            name=staging_name,
            embedding_function=self.embed_fn,
            metadata={"description": f"Staging voor job {job_id}"},
        )
        logger.info("Staging collectie aangemaakt: %s", staging_name)
        return collection

    def _commit_staging(self, job_id: str) -> int:
        """Verplaats alle chunks van staging naar de hoofdcollectie.

        Embeddings worden NIET meegekopieerd — de hoofdcollectie
        herberekent ze via zijn eigen embed_fn. Dit voorkomt
        dimensie-conflicten (bv. staging=384d local, hoofd=256d Voyage).

        Returns:
            Aantal chunks overgedragen.

        Raises:
            Exception: als de swap mislukt (staging blijft intact
            voor debug, caller moet _cleanup_staging aanroepen).
        """
        staging_name = f"staging-{job_id}"
        try:
            staging = self.client.get_collection(
                name=staging_name,
                embedding_function=self.embed_fn,
            )
        except Exception as e:
            logger.error("Staging collectie niet gevonden: %s — %s", staging_name, e)
            raise

        count = staging.count()
        if count == 0:
            self._cleanup_staging(job_id)
            return 0

        # Lees documenten + metadata (GEEN embeddings — hoofd herberekent)
        data = staging.get(
            limit=count,
            include=["documents", "metadatas"],
        )

        # Upsert naar hoofdcollectie — embed_fn van hoofd genereert vectors
        _BATCH = 100
        ids = data["ids"]
        docs = data["documents"]
        metas = data["metadatas"]

        for b_start in range(0, len(ids), _BATCH):
            b_end = min(b_start + _BATCH, len(ids))
            self.collection.upsert(
                ids=ids[b_start:b_end],
                documents=docs[b_start:b_end],
                metadatas=metas[b_start:b_end],
            )

        # Swap geslaagd — drop staging
        self._cleanup_staging(job_id)
        logger.info(
            "Staging commit voltooid: %d chunks → %s",
            count, COLLECTION_NAME,
        )
        return count

    def _cleanup_staging(self, job_id: str) -> None:
        """Drop de staging-collectie (cleanup na crash of success)."""
        staging_name = f"staging-{job_id}"
        try:
            self.client.delete_collection(staging_name)
            logger.info("Staging collectie gedropt: %s", staging_name)
        except Exception as e:
            logger.debug("Staging cleanup (al verwijderd?): %s", e)

    # ─── Single File Ingest ───

    def ingest_file(self, pad: object,
                    chunk_size: object = CHUNK_SIZE,
                    overlap: object = CHUNK_OVERLAP,
                    job_id: str = "",
                    extra_metadata: object = None) -> int:
        """Indexeer één bestand naar ChromaDB.

        Args:
            pad: Pad naar het bestand.
            chunk_size: Chunk grootte in woorden.
            overlap: Overlap in woorden.
            job_id: Optioneel — als meegegeven, gebruik atomic
                staging-swap (crash-proof). Data gaat eerst naar
                een staging-collectie en wordt pas na succes
                gecommit naar de hoofdcollectie.
            extra_metadata: Optionele dict met extra metadata
                velden (bijv. tags) die aan elke chunk worden
                toegevoegd.

        Returns:
            Aantal chunks verwerkt.
        """
        pad = Path(pad)
        if not pad.is_file():
            console.print(
                f"[red]Bestand niet gevonden:"
                f" {pad}[/red]"
            )
            return 0

        tekst = self._lees_bestand(pad)
        if not tekst.strip():
            return 0

        chunks = self.chunk_text(
            tekst, chunk_size, overlap
        )
        if not chunks:
            return 0

        ids = []
        documents = []
        metadatas = []

        for i, chunk in enumerate(chunks):
            ids.append(
                f"{pad.name}::chunk_{i}"
            )
            documents.append(chunk)
            meta = {
                "bron": pad.name,
                "pad": str(pad),
                "chunk_nr": i,
                "totaal_chunks": len(chunks),
                "extensie": pad.suffix,
                "grootte_bytes":
                    pad.stat().st_size,
            }
            if extra_metadata and isinstance(
                extra_metadata, dict
            ):
                meta.update(extra_metadata)
            metadatas.append(meta)

        # Atomic staging of directe upsert
        if job_id:
            staging = self._create_staging_collection(job_id)
            staging.upsert(
                ids=ids,
                documents=documents,
                metadatas=metadatas,
            )
            # Commit: staging → hoofdcollectie
            committed = self._commit_staging(job_id)
            console.print(
                f"[green]{committed} chunks"
                f" atomic-ingested: {pad.name}[/green]"
            )
            return committed
        else:
            self.collection.upsert(
                ids=ids,
                documents=documents,
                metadatas=metadatas,
            )
            console.print(
                f"[green]{len(ids)} chunks"
                f" geïndexeerd: {pad.name}[/green]"
            )
            return len(ids)

    # ─── Stats ───

    def toon_stats(self) -> None:
        """Toon database statistieken."""
        totaal = self.collection.count()

        console.print(Panel(
            "[bold cyan]KNOWLEDGE BASE STATS"
            "[/bold cyan]",
            border_style="cyan",
        ))

        if totaal == 0:
            console.print(
                "[yellow]Database is leeg."
                " Draai eerst:"
                " python ingest.py[/yellow]"
            )
            return

        stats_table = Table(
            border_style="cyan",
            show_header=False,
        )
        stats_table.add_column("label", width=25)
        stats_table.add_column("waarde")

        stats_table.add_row(
            "Totaal chunks",
            f"[bold green]{totaal}[/bold green]",
        )
        stats_table.add_row(
            "Collectie",
            f"[cyan]{COLLECTION_NAME}[/cyan]",
        )
        model_naam = (
            getattr(self.embed_fn, "model", None)
            or EMBEDDING_MODEL
        )
        stats_table.add_row(
            "Embedding model",
            f"[cyan]{model_naam}[/cyan]",
        )
        dim_info = getattr(self.embed_fn, '_target_dim', None)
        if dim_info and dim_info < 1024:
            stats_table.add_row("Dimensie", f"[green]{dim_info}d (MRL)[/green]")
        else:
            stats_table.add_row("Dimensie", f"[cyan]{dim_info or 1024}d[/cyan]")
        stats_table.add_row(
            "Database locatie",
            f"[dim]{CHROMA_DIR}[/dim]",
        )

        # Bronnen overzicht
        try:
            sample = self.collection.get(
                limit=totaal,
                include=["metadatas"],
            )
            bronnen = {}
            for m in sample["metadatas"]:
                bron = m.get("bron", "onbekend")
                bronnen[bron] = (
                    bronnen.get(bron, 0) + 1
                )

            stats_table.add_row("", "")
            stats_table.add_row(
                "[bold]Bronnen[/bold]",
                f"[bold]{len(bronnen)}"
                f" bestanden[/bold]",
            )
            for bron, count in sorted(
                bronnen.items(),
                key=lambda x: -x[1],
            ):
                stats_table.add_row(
                    f"  {bron}",
                    f"{count} chunks",
                )
        except Exception as e:
            logger.debug("Failed to retrieve source metadata for stats: %s", e)

        console.print(stats_table)

    # ─── Query (voor MemexAgent) ───

    def query(self, vraag: object, n_results: object=5) -> None:
        """Doorzoek de knowledge base."""
        results = self.collection.query(
            query_texts=[vraag],
            n_results=n_results,
            include=[
                "documents", "metadatas", "distances",
            ],
        )
        return results


    # ─── Lessons Learned ───

    def ingest_repair_logs(self) -> None:
        """Ingest repair logs als Lessons Learned."""
        if not REPAIR_LOG_PAD.exists():
            console.print(
                "[yellow]Geen repair logs"
                " gevonden.[/yellow]"
            )
            return

        try:
            with open(
                REPAIR_LOG_PAD, "r",
                encoding="utf-8",
            ) as f:
                data = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            console.print(
                f"[red]Kan repair logs niet"
                f" lezen: {e}[/red]"
            )
            return

        sessies = data.get("sessies", [])
        if not sessies:
            console.print(
                "[yellow]Geen sessies in"
                " repair logs.[/yellow]"
            )
            return

        ids = []
        documents = []
        metadatas = []

        for si, sessie in enumerate(sessies):
            entries = sessie.get("entries", [])
            for ei, entry in enumerate(entries):
                doc_id = (
                    f"repair_log::"
                    f"s{si}_e{ei}"
                )

                # Bouw leesbare tekst
                actie = entry.get("stap", {}).get(
                    "actie", "onbekend"
                )
                fout = entry.get(
                    "fout", "onbekend"
                )
                diagnose = entry.get(
                    "diagnose", "onbekend"
                )
                fix = entry.get(
                    "fix", "geen fix"
                )
                geslaagd = entry.get(
                    "geslaagd", False
                )

                tekst = (
                    f"Repair log: actie"
                    f" '{actie}' faalde."
                    f" Fout: {fout}."
                    f" Diagnose: {diagnose}."
                    f" Fix: {fix}."
                    f" Resultaat:"
                    f" {'geslaagd' if geslaagd else 'gefaald'}."
                )

                ids.append(doc_id)
                documents.append(tekst)
                metadatas.append({
                    "bron": "repair_logs",
                    "pad": "repair_logs.json",
                    "categorie":
                        "lessons_learned",
                })

        if ids:
            self.collection.upsert(
                ids=ids,
                documents=documents,
                metadatas=metadatas,
            )
            console.print(
                f"[green]{len(ids)} repair"
                f" entries ingested als"
                f" Lessons Learned.[/green]"
            )

    def query_met_lessen(
        self, vraag: object, n_results: object=5, n_lessen: object=3
    ) -> None:
        """Doorzoek knowledge base + lessons learned."""
        resultaten = self.query(vraag, n_results)

        try:
            lessen = self.collection.query(
                query_texts=[vraag],
                n_results=n_lessen,
                where={
                    "categorie": "lessons_learned",
                },
                include=[
                    "documents", "metadatas",
                    "distances",
                ],
            )
        except Exception as e:
            logger.debug("Failed to query lessons learned: %s", e)
            lessen = {
                "documents": [[]],
                "metadatas": [[]],
                "distances": [[]],
            }

        return {
            "resultaten": resultaten,
            "lessen": lessen,
        }


__all__ = ["TheLibrarian"]
