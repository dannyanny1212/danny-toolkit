"""
Universal Ingest Protocol — De Digitale Stofzuiger.

Scant een map, leest PDF's en tekstbestanden, hakt ze
in chunks en slaat ze op in ChromaDB met
sentence-transformer embeddings (all-MiniLM-L6-v2).

Gebruik:
    python ingest.py                     # Default: data/rag/documenten
    python ingest.py --path pad/naar/map
    python ingest.py --path docs --chunk-size 500
    python ingest.py --stats             # Toon database statistieken
    python ingest.py --reset             # Wis database en herstart

ChromaDB wordt opgeslagen in data/rag/chromadb/
"""

import argparse
import os
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

# ─── Config import ───
from config import CHROMA_DIR, DOCS_DIR, KNOWLEDGE_DIR

# ─── Constanten ───

BASE_DIR = Path(__file__).parent
DEFAULT_DOCS = DOCS_DIR
COLLECTION_NAME = "danny_knowledge"
CHUNK_SIZE = 400       # woorden per chunk
CHUNK_OVERLAP = 50     # overlap tussen chunks
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

# Ondersteunde extensies
SUPPORTED_EXT = {
    ".txt", ".md", ".py", ".json", ".csv",
    ".log", ".yaml", ".yml", ".toml", ".cfg",
    ".ini", ".xml", ".html", ".pdf",
}

# Bestanden die worden overgeslagen bij ingest
# (conversatie-data, geen kennisbron)
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
        from chromadb.utils.embedding_functions import (
            SentenceTransformerEmbeddingFunction,
        )

        # Database (persistent op schijf)
        os.makedirs(CHROMA_DIR, exist_ok=True)
        self.client = chromadb.PersistentClient(
            path=CHROMA_DIR
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

        # Embedding model (lokaal, geen API kosten)
        self.embed_fn = (
            SentenceTransformerEmbeddingFunction(
                model_name=EMBEDDING_MODEL
            )
        )

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
        woorden = text.split()
        chunks = []
        start = 0
        while start < len(woorden):
            eind = start + chunk_size
            chunk = " ".join(woorden[start:eind])
            if chunk.strip():
                chunks.append(chunk)
            start += chunk_size - overlap
        return chunks

    # ─── Ingest Pipeline ───

    def ingest(self, pad, chunk_size=CHUNK_SIZE,
               overlap=CHUNK_OVERLAP):
        """Hoofdproces: scan -> lees -> chunk -> opslaan."""
        start_time = time.time()

        console.print(Panel(
            "[bold magenta]UNIVERSAL INGEST PROTOCOL"
            "[/bold magenta]\n"
            "[dim]De Digitale Stofzuiger v1.0[/dim]",
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
        console.print(
            f"  Model: [green]{EMBEDDING_MODEL}"
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
            f"[cyan]{EMBEDDING_MODEL}[/cyan]",
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
        stats_table.add_row(
            "Embedding model",
            f"[cyan]{EMBEDDING_MODEL}[/cyan]",
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


# ─── Entry Point ───

def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Universal Ingest Protocol"
    )
    parser.add_argument(
        "--path", "-p",
        type=str,
        default=str(DEFAULT_DOCS),
        help="Map om te scannen"
             f" (default: {DEFAULT_DOCS})",
    )
    parser.add_argument(
        "--chunk-size", "-c",
        type=int,
        default=CHUNK_SIZE,
        help=f"Woorden per chunk"
             f" (default: {CHUNK_SIZE})",
    )
    parser.add_argument(
        "--overlap", "-o",
        type=int,
        default=CHUNK_OVERLAP,
        help=f"Overlap tussen chunks"
             f" (default: {CHUNK_OVERLAP})",
    )
    parser.add_argument(
        "--stats", "-s",
        action="store_true",
        help="Toon database statistieken",
    )
    parser.add_argument(
        "--reset", "-r",
        action="store_true",
        help="Wis database en herstart",
    )

    args = parser.parse_args()

    librarian = TheLibrarian(reset=args.reset)

    if args.stats:
        librarian.toon_stats()
        return

    librarian.ingest(
        pad=args.path,
        chunk_size=args.chunk_size,
        overlap=args.overlap,
    )


if __name__ == "__main__":
    main()
