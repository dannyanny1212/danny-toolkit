"""Bulk Assimilator — Massa-ingestie van externe projecten.

Loopt recursief door een lokaal pad, kopieert ondersteunde bestanden
naar de Librarian's DOCS_DIR, en roept de bestaande Atomic Staging-Swap
pipeline aan (384d LocalEmbeddings → ChromaDB danny_knowledge).

Usage:
    python bulk_assimilator.py C:/Users/danny/mijn_project
    python bulk_assimilator.py C:/Users/danny/mijn_project --tags "project:frontend, bron:extern"
    python bulk_assimilator.py C:/Users/danny/mijn_project --dry-run
    python bulk_assimilator.py C:/Users/danny/mijn_project --batch-size 20
"""

from __future__ import annotations

import argparse
import logging
import shutil
import sys
import time
import uuid
from pathlib import Path

# ── Project root op sys.path ──
_ROOT = Path(__file__).parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from danny_toolkit.core.config import Config

logger = logging.getLogger(__name__)

# ── Constanten ──

SUPPORTED_EXT = {
    ".txt", ".md", ".py", ".json", ".csv",
    ".log", ".yaml", ".yml", ".toml", ".cfg",
    ".ini", ".xml", ".html", ".pdf",
}

SKIP_DIRS = {
    ".git", ".hg", ".svn", "__pycache__", "node_modules",
    ".tox", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    "venv", "venv311", ".venv", "env", ".env",
    "dist", "build", "egg-info", ".eggs",
}

SKIP_FILES = {
    "interactions.json", "vector_db.json",
    "package-lock.json", "yarn.lock", "poetry.lock",
}

MAX_FILE_BYTES = 10 * 1024 * 1024  # 10 MB


# ── Kleuren ──

class K:
    """Minimale ANSI kleuren."""
    GR = "\033[92m"
    GE = "\033[93m"
    RO = "\033[91m"
    CY = "\033[96m"
    RS = "\033[0m"


def _discover_files(source_dir: Path) -> list[Path]:
    """Recursief alle ondersteunde bestanden vinden."""
    bestanden = []
    for f in sorted(source_dir.rglob("*")):
        # Skip uitgesloten directories
        if any(part in SKIP_DIRS for part in f.parts):
            continue
        if not f.is_file():
            continue
        if f.suffix.lower() not in SUPPORTED_EXT:
            continue
        if f.name in SKIP_FILES:
            continue
        if f.stat().st_size > MAX_FILE_BYTES:
            continue
        if f.stat().st_size == 0:
            continue
        bestanden.append(f)
    return bestanden


def _parse_tags(tags_str: str) -> dict:
    """Parse comma-separated tags naar metadata dict."""
    if not tags_str:
        return {}
    meta = {}
    tag_list = []
    for part in tags_str.split(","):
        part = part.strip()
        if ":" in part:
            k, v = part.split(":", 1)
            meta[k.strip()] = v.strip()
        elif part:
            tag_list.append(part)
    if tag_list:
        meta["tags"] = ", ".join(tag_list)
    return meta


def main():
    parser = argparse.ArgumentParser(
        description="Bulk Assimilator — massa-ingestie van externe projecten",
    )
    parser.add_argument(
        "source",
        type=str,
        help="Absoluut pad naar de bronmap (bijv. C:/Users/danny/mijn_project)",
    )
    parser.add_argument(
        "--tags",
        type=str,
        default="",
        help="Comma-separated tags (bijv. 'project:frontend, bron:extern')",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=10,
        help="Aantal bestanden per staging batch (default: 10)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Toon bestanden zonder te ingesten",
    )
    parser.add_argument(
        "--keep-copies",
        action="store_true",
        help="Bewaar kopieën in DOCS_DIR na ingestie",
    )

    args = parser.parse_args()
    source = Path(args.source).resolve()

    if not source.is_dir():
        print(f"{K.RO}Bronmap niet gevonden: {source}{K.RS}")
        sys.exit(1)

    print(f"\n{K.CY}{'=' * 60}")
    print(f"  BULK ASSIMILATOR — Mass Ingestion Protocol")
    print(f"  Bron: {source}")
    print(f"  Tags: {args.tags or '(geen)'}")
    print(f"  Batch: {args.batch_size} bestanden/batch")
    print(f"{'=' * 60}{K.RS}\n")

    # ── Stap 1: Discovery ──
    print(f"{K.GE}[1/4] Scanning bronmap...{K.RS}")
    bestanden = _discover_files(source)

    if not bestanden:
        print(f"{K.RO}Geen ondersteunde bestanden gevonden.{K.RS}")
        sys.exit(0)

    total_bytes = sum(f.stat().st_size for f in bestanden)
    print(f"{K.GR}  Gevonden: {len(bestanden)} bestanden "
          f"({total_bytes / 1024:.0f} KB){K.RS}")

    # Extensie breakdown
    ext_counts: dict[str, int] = {}
    for f in bestanden:
        ext = f.suffix.lower()
        ext_counts[ext] = ext_counts.get(ext, 0) + 1
    for ext, count in sorted(ext_counts.items(), key=lambda x: -x[1]):
        print(f"    {ext:8s}  {count:>4d} bestanden")

    if args.dry_run:
        print(f"\n{K.GE}[DRY RUN] Bestanden die zouden worden ingested:{K.RS}")
        for f in bestanden:
            rel = f.relative_to(source)
            print(f"    {rel}  ({f.stat().st_size} bytes)")
        print(f"\n{K.GE}Totaal: {len(bestanden)} bestanden. "
              f"Gebruik zonder --dry-run om te ingesten.{K.RS}")
        return

    # ── Stap 2: Kopieer naar DOCS_DIR ──
    print(f"\n{K.GE}[2/4] Kopiëren naar Librarian staging area...{K.RS}")
    Config.ensure_dirs()
    docs_dir = Config.RAG_DATA_DIR / "documenten"
    docs_dir.mkdir(parents=True, exist_ok=True)

    # Unieke subdirectory per bulk run (voorkomt naamconflicten)
    run_id = uuid.uuid4().hex[:8]
    bulk_dir = docs_dir / f"bulk_{run_id}"
    bulk_dir.mkdir(parents=True, exist_ok=True)

    copied = []
    for f in bestanden:
        # Behoud directorystructuur relatief aan source
        rel = f.relative_to(source)
        dest = bulk_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(f, dest)
        copied.append(dest)

    print(f"{K.GR}  {len(copied)} bestanden gekopieerd naar {bulk_dir}{K.RS}")

    # ── Stap 3: Batch ingestie via Librarian ──
    print(f"\n{K.GE}[3/4] Ingesting via Librarian pipeline "
          f"(384d LocalEmbeddings + Atomic Staging)...{K.RS}")

    from danny_toolkit.skills.librarian import TheLibrarian
    librarian = TheLibrarian()

    extra_meta = _parse_tags(args.tags)
    extra_meta["bulk_run_id"] = run_id
    extra_meta["bron_project"] = source.name

    total_chunks = 0
    success_count = 0
    fail_count = 0
    t0 = time.time()

    # Batch processing
    batches = [
        copied[i:i + args.batch_size]
        for i in range(0, len(copied), args.batch_size)
    ]

    for batch_idx, batch in enumerate(batches):
        batch_job = f"bulk_{run_id}_{batch_idx}"
        batch_chunks = 0

        print(f"\n  {K.CY}Batch {batch_idx + 1}/{len(batches)} "
              f"({len(batch)} bestanden)...{K.RS}")

        for file_path in batch:
            rel = file_path.relative_to(bulk_dir)
            try:
                chunks = librarian.ingest_file(
                    file_path,
                    job_id=batch_job,
                    extra_metadata=extra_meta,
                )
                total_chunks += chunks
                batch_chunks += chunks
                success_count += 1
                print(f"    {K.GR}+{chunks:>3d} chunks{K.RS}  {rel}")
            except Exception as e:
                fail_count += 1
                print(f"    {K.RO}FAIL{K.RS}       {rel}: {e}")

        print(f"  {K.GR}Batch {batch_idx + 1}: "
              f"{batch_chunks} chunks ingested{K.RS}")

    elapsed = time.time() - t0

    # ── Stap 4: Cleanup ──
    if not args.keep_copies:
        print(f"\n{K.GE}[4/4] Cleanup staging kopieën...{K.RS}")
        shutil.rmtree(bulk_dir, ignore_errors=True)
        print(f"{K.GR}  {bulk_dir.name}/ verwijderd{K.RS}")
    else:
        print(f"\n{K.GE}[4/4] Kopieën bewaard in {bulk_dir}{K.RS}")

    # ── Rapport ──
    rate = total_chunks / elapsed if elapsed > 0 else 0
    print(f"\n{K.CY}{'=' * 60}")
    print(f"  ASSIMILATION COMPLETE")
    print(f"  Bestanden:  {success_count} OK / {fail_count} FAIL")
    print(f"  Chunks:     {total_chunks}")
    print(f"  Duur:       {elapsed:.1f}s ({rate:.1f} chunks/sec)")
    print(f"  Run ID:     {run_id}")
    if args.tags:
        print(f"  Tags:       {args.tags}")
    print(f"{'=' * 60}{K.RS}\n")


if __name__ == "__main__":
    main()
