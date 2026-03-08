"""Advanced Knowledge Bridge — Afgeschermde RAG namespace voor Omega Advanced kennisdocs.

Koppelt de 13 Advanced MD-bestanden aan een dedicated ChromaDB collectie
('omega_advanced_skills') gescheiden van TheLibrarian's 'danny_knowledge'.
Gebruikt Markdown-aware chunking met header-hiërarchie behoud.
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

# Alle 13 advanced kennisdocumenten
ADVANCED_MODULES = [
    "omega_rag_advanced_architecture.md",
    "omega_mind_advanced.md",
    "omega_body_advanced.md",
    "omega_soul_advanced.md",
    "omega_security_advanced.md",
    "omega_wiring_advanced.md",
    "omega_resources_advanced.md",
    "omega_apps_advanced.md",
    "omega_learning_advanced.md",
    "omega_persona_advanced.md",
    "omega_ui_advanced.md",
    "omega_quests_advanced.md",
    "omega_skills_advanced.md",
]


class AdvancedKnowledgeBridge:
    """Koppelt Advanced MD-bestanden aan afgeschermde RAG-collectie.

    Gebruikt MarkdownHeaderTextSplitter voor structuur-bewuste chunking
    met header-hiërarchie behoud (H1/H2/H3 metadata per chunk).
    Gescheiden van TheLibrarian's 'danny_knowledge' collectie.
    """

    def __init__(self, db_path: str | None = None):
        if chromadb is None:
            raise ImportError("chromadb is vereist voor AdvancedKnowledgeBridge")
        if MarkdownHeaderTextSplitter is None:
            raise ImportError("langchain_text_splitters is vereist")

        if db_path is None:
            if Config is not None:
                db_path = str(Config.DATA_DIR / "rag" / "chromadb")
            else:
                db_path = os.path.join("data", "rag", "chromadb")

        self.client = chromadb.PersistentClient(path=db_path)
        self.collection = self.client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"description": "Omega Advanced Knowledge — 13 domeinen"},
        )
        self._doc_dir: Path | None = None

    @property
    def doc_dir(self) -> Path:
        """Pad naar de advanced kennisdocumenten."""
        if self._doc_dir is None:
            if Config is not None:
                self._doc_dir = Config.DATA_DIR / DOCS_SUBDIR
            else:
                self._doc_dir = Path("data") / DOCS_SUBDIR
        return self._doc_dir

    def ingest_all(self, doc_dir: str | None = None) -> int:
        """Ingest alle 13 advanced modules. Retourneert totaal chunks."""
        return self.ingest_modules(ADVANCED_MODULES, doc_dir=doc_dir)

    def ingest_modules(
        self,
        modules: list[str] | None = None,
        doc_dir: str | None = None,
    ) -> int:
        """Scant en indexeert advanced MD-bestanden met header-hiërarchie behoud."""
        if modules is None:
            modules = ADVANCED_MODULES

        target_dir = Path(doc_dir) if doc_dir else self.doc_dir

        # Markdown-aware splitters
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

            # Fase 1: split op Markdown headers (structuur behoud)
            md_splits = md_splitter.split_text(content)
            # Fase 2: split grote secties op chunk_size
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
            return {"error": "Collectie leeg — run eerst ingest_all()"}

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
                "sectie": meta.get("Header 2", meta.get("Header 1", "?")),
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
    bridge.ingest_all()
