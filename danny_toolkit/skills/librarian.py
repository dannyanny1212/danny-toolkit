"""
TheLibrarian — De Bibliothecaris van Project Omega.

Beheert de Knowledge Base: leest bestanden, chunked
tekst en slaat op in ChromaDB met sentence-transformer
embeddings (paraphrase-multilingual-mpnet-base-v2).
"""

import os

# Forceer TQDM (sentence-transformers) om stil te zijn
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["TQDM_DISABLE"] = "True"

import json
import time
from pathlib import Path
from typing import List

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
CHUNK_SIZE = 400
CHUNK_OVERLAP = 50
EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"

REPAIR_LOG_PAD = _root / "data" / "repair_logs.json"

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


class TheLibrarian:
    """De Bibliothecaris — beheert de Knowledge Base.

    Leest bestanden, chunked tekst en slaat op in
    ChromaDB met sentence-transformer embeddings.
    """

    def __init__(self, reset=False):
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
            except Exception:
                pass

        # Embedding model — Voyage AI of fallback
        from ..core.embeddings import get_chroma_embed_fn
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

    # ─── Bestandslezers ───

    def _lees_pdf(self, pad):
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
                f" {e}[/red]"
            )
            return ""

    def _lees_tekst(self, pad):
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

    def _lees_bestand(self, pad):
        """Lees een bestand op basis van extensie."""
        if pad.suffix.lower() == ".pdf":
            return self._lees_pdf(pad)
        return self._lees_tekst(pad)

    # ─── Scanner ───

    def scan_bestanden(self, pad) -> List[Path]:
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

    def chunk_text(self, text, chunk_size=CHUNK_SIZE,
                   overlap=CHUNK_OVERLAP) -> List[str]:
        """Hakt tekst in overlappende chunks."""
        from ..core.document_processor import (
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

    def ingest(self, pad, chunk_size=CHUNK_SIZE,
               overlap=CHUNK_OVERLAP):
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
                    ids.append(
                        f"{rel_pad}::chunk_{i}"
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

                # Upsert (voeg toe of update)
                if ids:
                    self.collection.upsert(
                        ids=ids,
                        documents=documents,
                        metadatas=metadatas,
                    )
                    totaal_chunks += len(ids)

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

    # ─── Single File Ingest ───

    def ingest_file(self, pad,
                    chunk_size=CHUNK_SIZE,
                    overlap=CHUNK_OVERLAP) -> int:
        """Indexeer één bestand naar ChromaDB.

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
            metadatas.append({
                "bron": pad.name,
                "pad": str(pad),
                "chunk_nr": i,
                "totaal_chunks": len(chunks),
                "extensie": pad.suffix,
                "grootte_bytes":
                    pad.stat().st_size,
            })

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

    def toon_stats(self):
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
        except Exception:
            pass

        console.print(stats_table)

    # ─── Query (voor MemexAgent) ───

    def query(self, vraag, n_results=5):
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

    def ingest_repair_logs(self):
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
        self, vraag, n_results=5, n_lessen=3
    ):
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
        except Exception:
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
