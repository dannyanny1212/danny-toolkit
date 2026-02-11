"""
Universal Ingest Protocol — De Digitale Stofzuiger v2.0

Nu met Batch Processing & Code Awareness.

Gebruik:
    python ingest.py --batch --method code
    python ingest.py --batch --method paragraph
    python ingest.py --reset
    python ingest.py --stats
"""

import sys
import io
import argparse
import os
import warnings
import logging

# --- WINDOWS UTF-8 FIX ---
sys.stdout = io.TextIOWrapper(
    sys.stdout.buffer, encoding="utf-8"
)
sys.stderr = io.TextIOWrapper(
    sys.stderr.buffer, encoding="utf-8"
)

# --- SILENT MODE ---
warnings.filterwarnings("ignore")
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
logging.getLogger("transformers").setLevel(
    logging.ERROR
)
logging.getLogger("chromadb").setLevel(
    logging.ERROR
)

from rich.console import Console

# ─── V6 / V5 Import Fallback ───

try:
    from danny_toolkit.skills.librarian import (
        TheLibrarian,
    )
    from danny_toolkit.core.processor import (
        BatchProcessor,
    )
except ImportError:
    try:
        from librarian import TheLibrarian
        from processor import BatchProcessor
    except ImportError:
        print(
            "\u274c CRITICAL: Kan 'librarian.py'"
            " of 'processor.py' niet vinden."
        )
        print(
            "   Zorg dat deze bestanden bestaan"
            " in 'danny_toolkit/' of de root."
        )
        sys.exit(1)

console = Console()


# ─── Entry Point ───

def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description=(
            "Universal Ingest Protocol v2.0"
        ),
    )

    # Standaard argumenten
    parser.add_argument(
        "--path", "-p",
        type=str,
        default=".",
        help="Map om te scannen",
    )
    parser.add_argument(
        "--reset", "-r",
        action="store_true",
        help="Wis database en herstart",
    )
    parser.add_argument(
        "--stats", "-s",
        action="store_true",
        help="Toon database statistieken",
    )

    # Batch opties
    parser.add_argument(
        "--batch", "-b",
        action="store_true",
        help="Gebruik de nieuwe BatchProcessor",
    )
    parser.add_argument(
        "--method", "-m",
        type=str,
        default="fixed",
        choices=["fixed", "paragraph", "code"],
        help="Chunking strategie"
             " (default: fixed)",
    )
    parser.add_argument(
        "--chunk-size", "-c",
        type=int,
        default=500,
        help="Woorden per chunk (bij fixed)",
    )

    args = parser.parse_args()

    # 1. Start de Librarian (Verbinding met DB)
    try:
        librarian = TheLibrarian(
            reset=args.reset
        )
    except Exception as e:
        console.print(
            f"[bold red]\u274c Fout bij starten"
            f" TheLibrarian: {e}[/bold red]"
        )
        sys.exit(1)

    # 2. Stats modus
    if args.stats:
        librarian.toon_stats()
        return

    # 3. Batch modus
    if args.batch:
        bestanden = librarian.scan_bestanden(
            args.path
        )
        if not bestanden:
            console.print(
                "[red]Geen bestanden gevonden!"
                "[/red]"
            )
            return
        batch = BatchProcessor(librarian)
        batch.process_batch(
            bestanden,
            method=args.method,
            chunk_size=args.chunk_size,
        )
        batch.print_report()
        return

    # 4. Standaard ingest
    librarian.ingest(
        pad=args.path,
        chunk_size=args.chunk_size,
    )


if __name__ == "__main__":
    main()
