"""Advanced Knowledge Bridge — Afgeschermde RAG namespace voor Omega Advanced kennisdocs.

Koppelt de 13 Advanced MD-bestanden aan een dedicated ChromaDB collectie
('omega_advanced_skills') gescheiden van TheLibrarian's 'danny_knowledge'.
Gebruikt Markdown-aware chunking met header-hiërarchie behoud.
Autonome pad-detectie: vindt danny-toolkit root waar je het ook draait.
"""
from __future__ import annotations

import os
import logging
from pathlib import Path

try:
    import chromadb
except ImportError:
    chromadb = None

try:
    from langchain_text_splitters import (
        MarkdownHeaderTextSplitter,
        RecursiveCharacterTextSplitter,
    )
except ImportError:
    MarkdownHeaderTextSplitter = None
    RecursiveCharacterTextSplitter = None

try:
    from danny_toolkit.core.config import Config
except ImportError:
    Config = None

try:
    from danny_toolkit.core.utils import Kleur, kleur
except ImportError:
    Kleur = None

    def kleur(tekst: str, _kleur: object = None) -> str:
        return str(tekst)


logger = logging.getLogger(__name__)

# --- Constanten (respecteert TheLibrarian limieten) ---
COLLECTION_NAME = "omega_advanced_skills"
CHUNK_SIZE = 350
CHUNK_OVERLAP = 50
DOCS_SUBDIR = "rag/documenten"

# Geen hardcoded lijst meer — find_md_files() scant dynamisch


def _detect_base_dir() -> Path:
    """Detecteer danny-toolkit root automatisch.

    Prioriteit:
    1. Config.BASE_DIR (als danny_toolkit.core.config beschikbaar is)
    2. Loop omhoog vanaf dit bestand tot 'danny-toolkit' gevonden
    3. Loop omhoog vanaf cwd tot 'danny-toolkit' gevonden
    4. Fallback: cwd
    """
    # 1. Config
    if Config is not None:
        try:
            return Path(Config.BASE_DIR)
        except Exception:
            pass

    # 2. Vanuit dit bestand omhoog klimmen
    for anchor in (Path(__file__).resolve(), Path.cwd()):
        current = anchor
        while current != current.parent:
            if current.name == "danny-toolkit":
                return current
            current = current.parent

    # 3. Fallback
    return Path.cwd()


class AdvancedKnowledgeBridge:
    """Koppelt Advanced MD-bestanden aan afgeschermde RAG-collectie.

    Autonome pad-detectie: vindt danny-toolkit root automatisch.
    Gebruikt MarkdownHeaderTextSplitter voor structuur-bewuste chunking
    met header-hiërarchie behoud (H1/H2/H3 metadata per chunk).
    Gescheiden van TheLibrarian's 'danny_knowledge' collectie.
    """

    def __init__(self, db_path: str | None = None):
        if chromadb is None:
            raise ImportError("chromadb is vereist voor AdvancedKnowledgeBridge")
        if MarkdownHeaderTextSplitter is None:
            raise ImportError("langchain_text_splitters is vereist")

        self.base_dir = _detect_base_dir()

        if db_path is None:
            db_path = str(self.base_dir / "data" / "rag" / "chromadb")

        _cyaan = Kleur.FEL_CYAAN if Kleur else None
        print(kleur(f"  [BRIDGE] Soul (ChromaDB): {db_path}", _cyaan))

        self.client = chromadb.PersistentClient(path=db_path)
        self.collection = self.client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"description": "Omega Advanced Knowledge — 13 domeinen"},
        )

    @property
    def doc_dir(self) -> Path:
        """Pad naar de advanced kennisdocumenten."""
        return self.base_dir / "data" / DOCS_SUBDIR

    def find_md_files(self) -> dict[str, Path]:
        """Scan data/rag/documenten/ voor ALLE markdown kennis.

        Geen hardcoded lijsten — pakt alles wat in de knowledge kluis staat.
        Toekomstbestendig: drop een nieuw .md bestand, draai het script, klaar.
        """
        docs_dir = self.doc_dir
        found: dict[str, Path] = {}

        if not docs_dir.exists():
            _geel = Kleur.FEL_GEEL if Kleur else None
            print(kleur(f"  [SKIP] Doelmap niet gevonden: {docs_dir}", _geel))
            return found

        for path in sorted(docs_dir.glob("*.md")):
            found[path.name] = path

        _cyaan = Kleur.FEL_CYAAN if Kleur else None
        print(kleur(
            f"  [SCAN] {len(found)} markdown bestanden in {docs_dir}",
            _cyaan,
        ))
        return found

    def ingest_all(self, doc_dir: str | None = None) -> int:
        """Ingest alle markdown bestanden uit de knowledge kluis."""
        files = self.find_md_files() if doc_dir is None else None
        if files is not None:
            modules = list(files.keys())
        else:
            modules = [p.name for p in sorted(Path(doc_dir).glob("*.md"))]
        return self.ingest_modules(modules, doc_dir=doc_dir)

    def ingest(self) -> int:
        """Autonome ingestie: vind en ingest alle advanced bestanden."""
        files = self.find_md_files()

        _geel = Kleur.FEL_GEEL if Kleur else None
        if not files:
            print(kleur("  [SKIP] Geen advanced MD bestanden gevonden", _geel))
            return 0

        # Markdown-aware splitters
        headers_to_split_on = [
            ("#", "H1"),
            ("##", "H2"),
            ("###", "H3"),
        ]
        md_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=headers_to_split_on,
        )
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
        )

        _groen = Kleur.FEL_GROEN if Kleur else None
        totaal = 0

        print(kleur(
            f"  [START] Ingestie van {len(files)} Advanced Modules...",
            Kleur.FEL_CYAAN if Kleur else None,
        ))

        for name, filepath in files.items():
            content = filepath.read_text(encoding="utf-8")

            md_splits = md_splitter.split_text(content)
            final_splits = text_splitter.split_documents(md_splits)

            if not final_splits:
                continue

            documents = [split.page_content for split in final_splits]
            metadatas = [
                {"source": name, "type": "omega_advanced", **split.metadata}
                for split in final_splits
            ]
            ids = [f"{name}_chunk_{i}" for i in range(len(final_splits))]

            self.collection.upsert(
                documents=documents,
                metadatas=metadatas,
                ids=ids,
            )
            totaal += len(final_splits)
            print(kleur(
                f"  [OK] {name:<40} {len(final_splits):>3} chunks",
                _groen,
            ))

        print(kleur(
            f"  [DONE] +{totaal} chunks | Collectie: {self.collection.count()} docs",
            _groen,
        ))
        return totaal

    def ingest_modules(
        self,
        modules: list[str] | None = None,
        doc_dir: str | None = None,
    ) -> int:
        """Ingest specifieke modules vanuit een directory."""
        if modules is None:
            # Dynamisch: scan de docs directory
            target = Path(doc_dir) if doc_dir else self.doc_dir
            modules = [p.name for p in sorted(target.glob("*.md"))]

        target_dir = Path(doc_dir) if doc_dir else self.doc_dir

        headers_to_split_on = [
            ("#", "Header 1"),
            ("##", "Header 2"),
            ("###", "Header 3"),
        ]
        md_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=headers_to_split_on,
        )
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
        )

        totaal = 0
        _groen = Kleur.FEL_GROEN if Kleur else None
        _geel = Kleur.FEL_GEEL if Kleur else None

        for filename in modules:
            filepath = target_dir / filename
            if not filepath.exists():
                msg = f"Bestand niet gevonden: {filepath}"
                print(kleur(f"  [SKIP] {msg}", _geel))
                logger.warning(msg)
                continue

            content = filepath.read_text(encoding="utf-8")

            md_splits = md_splitter.split_text(content)
            final_splits = text_splitter.split_documents(md_splits)

            if not final_splits:
                continue

            documents = [split.page_content for split in final_splits]
            metadatas = [
                {
                    "source": filename,
                    "type": "omega_advanced",
                    **split.metadata,
                }
                for split in final_splits
            ]
            ids = [f"{filename}_chunk_{i}" for i in range(len(final_splits))]

            self.collection.upsert(
                documents=documents,
                metadatas=metadatas,
                ids=ids,
            )
            totaal += len(final_splits)
            print(kleur(
                f"  [OK] {filename}: {len(final_splits)} chunks",
                _groen,
            ))

        print(kleur(
            f"  [TOTAAL] +{totaal} chunks | Collectie: {self.collection.count()} docs",
            _groen,
        ))
        return totaal

    def query(self, vraag: str, n_results: int = 5) -> dict:
        """Doorzoek de advanced knowledge collectie."""
        return self.collection.query(
            query_texts=[vraag],
            n_results=min(n_results, self.collection.count() or 1),
        )

    def raadpleeg_omega_skills(self, query: str, n_results: int = 5) -> dict:
        """Anthropic tool interface — doorzoek advanced knowledge.

        Retourneert geformatteerde resultaten met score, bron en sectie
        zodat CentralBrain deze direct kan opnemen in de LLM context.
        """
        if self.collection.count() == 0:
            return {"error": "Collectie leeg — run eerst ingest() of ingest_all()"}

        raw = self.query(query, n_results=n_results)
        results = []
        docs = raw.get("documents", [[]])[0]
        metas = raw.get("metadatas", [[]])[0]
        dists = raw.get("distances", [[]])[0]

        for doc, meta, dist in zip(docs, metas, dists):
            score = max(0.0, 1.0 - dist)
            results.append({
                "score": round(score, 3),
                "bron": meta.get("source", "?"),
                "sectie": meta.get("H2", meta.get("Header 2",
                         meta.get("H1", meta.get("Header 1", "?")))),
                "tekst": doc[:500],
            })

        return {
            "query": query,
            "resultaten": results,
            "totaal_in_collectie": self.collection.count(),
        }

    def count(self) -> int:
        """Aantal documenten in de collectie."""
        return self.collection.count()

    def reset(self) -> None:
        """Verwijder en hermaak de collectie (clean slate)."""
        self.client.delete_collection(COLLECTION_NAME)
        self.collection = self.client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"description": "Omega Advanced Knowledge — 13 domeinen"},
        )
        logger.info("AdvancedKnowledgeBridge collectie gereset")


if __name__ == "__main__":
    bridge = AdvancedKnowledgeBridge()
    print(f"Collectie '{COLLECTION_NAME}': {bridge.count()} docs")
    bridge.ingest()
