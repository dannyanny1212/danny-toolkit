"""Nuke & Rebuild omega_advanced_skills collectie.

Chirurgische ingreep: drop de collectie direct via ChromaDB client,
dan re-ingest via AdvancedKnowledgeBridge met correcte embedding function.

Gebruik:
    python danny_toolkit/sandbox/nuke_omega.py
"""
from __future__ import annotations

import logging
import sys
import os
from pathlib import Path

logger = logging.getLogger(__name__)

# Project root op path
_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_root))

# Windows UTF-8
if os.name == "nt":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except (ValueError, OSError) as _enc_err:
        logger.debug("UTF-8 reconfigure skipped: %s", _enc_err)


def rebuild_omega() -> None:
    """Drop en herbouw omega_advanced_skills collectie.

    Twee-fase rebuild: eerst drop via directe client,
    dan per-file ingestie met retry bij stale collection refs.
    """
    import time
    import chromadb
    from langchain_text_splitters import (
        MarkdownHeaderTextSplitter,
        RecursiveCharacterTextSplitter,
    )

    DB_PATH = str(_root / "data" / "rag" / "chromadb")
    COLL_NAME = "omega_advanced_skills"
    DOCS_DIR = _root / "data" / "rag" / "documenten"

    # 1. Direct drop
    client = chromadb.PersistentClient(path=DB_PATH)
    try:
        client.delete_collection(COLL_NAME)
        print("[SYSTEM] omega_advanced_skills DROPPED", flush=True)
    except Exception as e:
        print(f"[WARN] Drop mislukt (mogelijk bestond hij niet): {e}")

    # 2. Embed fn laden
    try:
        from danny_toolkit.core.embeddings import get_chroma_embed_fn
        embed_fn = get_chroma_embed_fn()
        print("[SYSTEM] Embedding function geladen", flush=True)
    except Exception:
        embed_fn = None
        print("[WARN] Geen embed_fn, fallback naar ChromaDB default")

    # 3. Fresh collection
    kwargs = {"name": COLL_NAME, "metadata": {"description": "Omega Advanced Knowledge"}}
    if embed_fn is not None:
        kwargs["embedding_function"] = embed_fn
    collection = client.get_or_create_collection(**kwargs)

    # 4. Splitters
    md_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=[("#", "H1"), ("##", "H2"), ("###", "H3")],
    )
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=350, chunk_overlap=50)

    # 5. Per-file ingestie met retry
    md_files = sorted(DOCS_DIR.glob("*.md"))
    print(f"[SYSTEM] {len(md_files)} markdown bestanden gevonden", flush=True)
    totaal = 0
    fouten = 0

    for filepath in md_files:
        name = filepath.name
        content = filepath.read_text(encoding="utf-8")
        md_splits = md_splitter.split_text(content)
        final_splits = text_splitter.split_documents(md_splits)
        if not final_splits:
            continue

        documents = [s.page_content for s in final_splits]
        metadatas = [{"source": name, "type": "omega_advanced", **s.metadata} for s in final_splits]
        ids = [f"{name}_chunk_{i}" for i in range(len(final_splits))]

        # Batch upsert met retry bij stale collection
        BATCH = 100
        for b_start in range(0, len(ids), BATCH):
            b_end = min(b_start + BATCH, len(ids))
            for attempt in range(3):
                try:
                    collection.upsert(
                        documents=documents[b_start:b_end],
                        metadatas=metadatas[b_start:b_end],
                        ids=ids[b_start:b_end],
                    )
                    break
                except Exception as e:
                    if attempt < 2:
                        print(f"  [RETRY] {name} batch {b_start}: {e}")
                        time.sleep(2)
                        # Re-acquire collection
                        collection = client.get_or_create_collection(**kwargs)
                    else:
                        print(f"  [FAIL] {name} batch {b_start}: {e}")
                        fouten += 1
            if b_end < len(ids):
                time.sleep(1)

        totaal += len(final_splits)
        print(f"  [OK] {name:<45} {len(final_splits):>4} chunks", flush=True)

    # 6. Validatie
    final_count = collection.count()
    print(f"\n[RESULT] {totaal} chunks verwerkt, {fouten} fouten")
    print(f"[RESULT] Collectie grootte: {final_count}")


if __name__ == "__main__":
    rebuild_omega()
