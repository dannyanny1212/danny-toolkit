"""
Protocol Exodus — External Intelligence Ingest.

Ingest externe documentatie (FastAPI etc.) in de
`external_intelligence` ChromaDB collectie.

Stealth settings: 100 chunks/batch, 22s cooldown (Voyage 3 RPM).
"""

from __future__ import annotations

import logging
import sys
import io
import os
import time
import warnings
from pathlib import Path

logger = logging.getLogger(__name__)

# --- WINDOWS UTF-8 FIX ---
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except (ValueError, OSError):
    logger.debug("UTF-8 reconfiguration not possible")

# --- SILENT MODE ---
warnings.filterwarnings("ignore")
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn

console = Console()

# ─── Config ───
ROOT = Path(__file__).parent
DOCS_DIR = ROOT / "data" / "rag" / "documenten"
CHROMA_DIR = ROOT / "data" / "rag" / "chromadb"
COLLECTION_NAME = "external_intelligence"
CHUNK_SIZE = 350  # woorden
CHUNK_OVERLAP = 50
_MICRO_BATCH = 100
_COOLDOWN = 22  # seconden tussen batches

# Alleen FastAPI docs pakken
FASTAPI_PREFIXES = (
    "fastapi_",
)

SUPPORTED_EXT = {".md", ".txt"}


def chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split tekst in chunks van ~size woorden met overlap."""
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = start + size
        chunk = " ".join(words[start:end])
        if chunk.strip():
            chunks.append(chunk)
        start = end - overlap
    return chunks


def scan_fastapi_docs() -> list[Path]:
    """Vind alle FastAPI doc bestanden."""
    bestanden = []
    for f in sorted(DOCS_DIR.iterdir()):
        if f.suffix.lower() in SUPPORTED_EXT:
            if f.stem.startswith(FASTAPI_PREFIXES):
                bestanden.append(f)
    return bestanden


def main() -> None:
    """Exodus protocol — ingest external intelligence."""
    t_start = time.time()

    console.print("\n[bold cyan]Protocol EXODUS — External Intelligence Ingest[/bold cyan]\n")

    # 1. Scan bestanden
    bestanden = scan_fastapi_docs()
    console.print(f"  Gevonden: [green]{len(bestanden)}[/green] FastAPI doc bestanden")

    if not bestanden:
        console.print("[red]Geen bestanden gevonden![/red]")
        return

    # 2. Chunk alles
    all_chunks = []
    for f in bestanden:
        tekst = f.read_text(encoding="utf-8")
        chunks = chunk_text(tekst)
        for i, chunk in enumerate(chunks):
            all_chunks.append({
                "id": f"exodus_{f.stem}_{i:04d}",
                "text": chunk,
                "metadata": {
                    "source": f.name,
                    "chunk_index": i,
                    "collection": COLLECTION_NAME,
                },
            })
        console.print(f"    {f.name}: {len(chunks)} chunks")

    console.print(f"\n  Totaal chunks: [bold green]{len(all_chunks)}[/bold green]")

    # 3. ChromaDB connectie + LOCAL embeddings (geen rate limits)
    console.print("\n  [cyan]ChromaDB + Local Embeddings initialisatie...[/cyan]")

    try:
        import chromadb
    except ImportError:
        logger.debug("chromadb not available")
        console.print("[red]chromadb niet geinstalleerd[/red]")
        return
    os.makedirs(CHROMA_DIR, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))

    # Forceer lokale embeddings — bypass Voyage rate limits
    try:
        from danny_toolkit.core.embeddings import LocalChromaEmbedding
    except ImportError:
        logger.debug("LocalChromaEmbedding not available")
        console.print("[red]LocalChromaEmbedding niet beschikbaar[/red]")
        return
    embed_fn = LocalChromaEmbedding()

    # Collectie
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=embed_fn,
        metadata={"description": "External Intelligence — FastAPI docs"},
    )

    bestaand = collection.count()
    console.print(f"  Bestaand in collectie: [yellow]{bestaand}[/yellow] chunks")

    # 4. Rate limit cooldown (niet nodig voor lokale embeddings)
    # Voyage cooldown overgeslagen — lokale motor draait onbeperkt

    # 5. Stealth upsert
    ids = [c["id"] for c in all_chunks]
    documents = [c["text"] for c in all_chunks]
    metadatas = [c["metadata"] for c in all_chunks]

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total}"),
        console=console,
    ) as progress:
        task = progress.add_task("Upsert...", total=len(ids))

        for b_start in range(0, len(ids), _MICRO_BATCH):
            b_end = min(b_start + _MICRO_BATCH, len(ids))
            collection.upsert(
                ids=ids[b_start:b_end],
                documents=documents[b_start:b_end],
                metadatas=metadatas[b_start:b_end],
            )
            progress.update(task, completed=b_end)

            # Geen cooldown nodig — lokale embeddings

    # 6. Rapportage
    t_total = time.time() - t_start
    final_count = collection.count()

    table = Table(title="EXODUS RESULTAAT", show_header=False)
    table.add_column("Key", style="bold")
    table.add_column("Value", style="green")
    table.add_row("Bestanden gescand", str(len(bestanden)))
    table.add_row("Chunks verwerkt", str(len(all_chunks)))
    table.add_row("Totaal in collectie", str(final_count))
    table.add_row("Nieuwe chunks", str(final_count - bestaand))
    table.add_row("Collectie", COLLECTION_NAME)
    table.add_row("Chunk grootte", f"{CHUNK_SIZE} woorden (overlap: {CHUNK_OVERLAP})")
    model_naam = getattr(embed_fn, '_model_name', 'local')
    dim = getattr(embed_fn, '_target_dim', '?')
    table.add_row("Embedding model", str(model_naam))
    table.add_row("Dimensie", f"{dim}d (local)")
    table.add_row("Database locatie", str(CHROMA_DIR))
    table.add_row("Laadtijd", f"{t_total:.1f}s")
    console.print(table)

    console.print(f"\n[bold green]Exodus compleet![/bold green]")
    console.print(f"{COLLECTION_NAME}: {final_count} chunks (+{final_count - bestaand} nieuw)\n")


if __name__ == "__main__":
    main()
