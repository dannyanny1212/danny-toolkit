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
import sys
import time
from pathlib import Path

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

# ─── Constanten ───

BASE_DIR = Path(__file__).parent
DEFAULT_DOCS = BASE_DIR / "data" / "rag" / "documenten"
CHROMA_DIR = str(BASE_DIR / "data" / "rag" / "chromadb")
COLLECTION_NAME = "danny_knowledge"
CHUNK_SIZE = 400       # tokens per chunk
CHUNK_OVERLAP = 50     # overlap tussen chunks
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

# Ondersteunde extensies
SUPPORTED_EXT = {
    ".txt", ".md", ".py", ".json", ".csv",
    ".log", ".yaml", ".yml", ".toml", ".cfg",
    ".ini", ".xml", ".html", ".pdf",
}

console = Console()


# ─── Chunking ───

def chunk_text(text, chunk_size=CHUNK_SIZE,
               overlap=CHUNK_OVERLAP):
    """Splits tekst in overlappende chunks."""
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


# ─── Bestandslezers ───

def lees_pdf(pad):
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


def lees_tekst(pad):
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


def lees_bestand(pad):
    """Lees een bestand op basis van extensie."""
    if pad.suffix.lower() == ".pdf":
        return lees_pdf(pad)
    return lees_tekst(pad)


# ─── Scanner ───

def scan_bestanden(pad):
    """Vind alle ondersteunde bestanden recursief."""
    pad = Path(pad)
    if not pad.exists():
        console.print(
            f"[red]Map niet gevonden: {pad}[/red]"
        )
        return []

    bestanden = []
    for f in sorted(pad.rglob("*")):
        if (
            f.is_file()
            and f.suffix.lower() in SUPPORTED_EXT
        ):
            bestanden.append(f)
    return bestanden


# ─── ChromaDB ───

def get_collection(reset=False):
    """Maak of open ChromaDB collectie."""
    import chromadb
    from chromadb.utils.embedding_functions import (
        SentenceTransformerEmbeddingFunction,
    )

    # Zorg dat de map bestaat
    os.makedirs(CHROMA_DIR, exist_ok=True)

    client = chromadb.PersistentClient(
        path=CHROMA_DIR
    )

    if reset:
        try:
            client.delete_collection(COLLECTION_NAME)
            console.print(
                "[yellow]Database gereset.[/yellow]"
            )
        except Exception:
            pass

    embedding_fn = SentenceTransformerEmbeddingFunction(
        model_name=EMBEDDING_MODEL
    )

    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=embedding_fn,
        metadata={
            "description": "Danny Toolkit Knowledge Base",
        },
    )

    return collection


# ─── Ingest Pipeline ───

def ingest(pad, chunk_size=CHUNK_SIZE,
           overlap=CHUNK_OVERLAP, reset=False):
    """Hoofdfunctie: scan → lees → chunk → opslaan."""
    start_time = time.time()

    console.print(Panel(
        "[bold magenta]UNIVERSAL INGEST PROTOCOL"
        "[/bold magenta]\n"
        "[dim]De Digitale Stofzuiger v1.0[/dim]",
        border_style="magenta",
    ))

    # 1. Scan bestanden
    bestanden = scan_bestanden(pad)
    if not bestanden:
        console.print(
            "[red]Geen bestanden gevonden![/red]"
        )
        return

    console.print(
        f"\n[cyan]Gevonden:[/cyan]"
        f" {len(bestanden)} bestanden in {pad}"
    )

    # 2. ChromaDB collectie
    console.print(
        "\n[cyan]ChromaDB initialiseren...[/cyan]"
    )
    collection = get_collection(reset=reset)
    bestaand = collection.count()
    console.print(
        f"  Collectie: [green]{COLLECTION_NAME}[/green]"
        f" ({bestaand} bestaande chunks)"
    )
    console.print(
        f"  Model: [green]{EMBEDDING_MODEL}[/green]"
    )

    # 3. Ingest met progress bar
    totaal_chunks = 0
    totaal_skip = 0

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
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
            tekst = lees_bestand(bestand)
            if not tekst.strip():
                progress.advance(taak)
                continue

            # Chunk
            chunks = chunk_text(
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
                chunk_id = (
                    f"{rel_pad}::chunk_{i}"
                )

                # Check of chunk al bestaat
                try:
                    existing = collection.get(
                        ids=[chunk_id]
                    )
                    if existing and existing["ids"]:
                        totaal_skip += 1
                        continue
                except Exception:
                    pass

                ids.append(chunk_id)
                documents.append(chunk)
                metadatas.append({
                    "bron": naam,
                    "pad": rel_pad,
                    "chunk_nr": i,
                    "totaal_chunks": len(chunks),
                    "extensie": bestand.suffix,
                    "grootte_bytes": bestand.stat().st_size,
                })

            # Batch upsert
            if ids:
                collection.add(
                    ids=ids,
                    documents=documents,
                    metadatas=metadatas,
                )
                totaal_chunks += len(ids)

            progress.advance(taak)

    # 4. Resultaat
    elapsed = time.time() - start_time
    nieuw_totaal = collection.count()

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
        "Nieuwe chunks",
        f"[green]{totaal_chunks}[/green]",
    )
    result_table.add_row(
        "Overgeslagen (duplicaat)",
        f"[yellow]{totaal_skip}[/yellow]",
    )
    result_table.add_row(
        "Totaal in database",
        f"[bold green]{nieuw_totaal}[/bold green]",
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
        "\n[bold green]Ingest compleet![/bold green]"
    )


# ─── Stats ───

def toon_stats():
    """Toon database statistieken."""
    collection = get_collection()
    totaal = collection.count()

    console.print(Panel(
        "[bold cyan]KNOWLEDGE BASE STATS"
        "[/bold cyan]",
        border_style="cyan",
    ))

    if totaal == 0:
        console.print(
            "[yellow]Database is leeg."
            " Draai eerst: python ingest.py[/yellow]"
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

    # Toon bronnen overzicht
    try:
        sample = collection.get(
            limit=totaal,
            include=["metadatas"],
        )
        bronnen = {}
        for m in sample["metadatas"]:
            bron = m.get("bron", "onbekend")
            bronnen[bron] = bronnen.get(bron, 0) + 1

        stats_table.add_row("", "")
        stats_table.add_row(
            "[bold]Bronnen[/bold]",
            f"[bold]{len(bronnen)} bestanden[/bold]",
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

    if args.stats:
        toon_stats()
        return

    ingest(
        pad=args.path,
        chunk_size=args.chunk_size,
        overlap=args.overlap,
        reset=args.reset,
    )


if __name__ == "__main__":
    main()
