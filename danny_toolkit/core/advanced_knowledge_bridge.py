"""Advanced Knowledge Bridge — Afgeschermde RAG namespace voor Omega Advanced kennisdocs.

Koppelt de 13 Advanced MD-bestanden aan een dedicated ChromaDB collectie
('omega_advanced_skills') gescheiden van TheLibrarian's 'danny_knowledge'.
Gebruikt Markdown-aware chunking met header-hiërarchie behoud.
Autonome pad-detectie: vindt danny-toolkit root waar je het ook draait.

LAZY INSTANTIATIE: ChromaDB PersistentClient wordt pas geladen bij eerste
gebruik, NIET in __init__. Dit voorkomt asyncio event loop clashes wanneer
CentralBrain de class lazy-instantieert via importlib.
"""
from __future__ import annotations

import os
import logging
from pathlib import Path

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
    from danny_toolkit.core.embeddings import get_chroma_embed_fn
    _HAS_VOYAGE = True
except ImportError:
    _HAS_VOYAGE = False

try:
    from danny_toolkit.core.utils import Kleur, kleur
except ImportError:
    Kleur = None

    def kleur(tekst: str, _kleur: object = None) -> str:
        """Kleur."""
        return str(tekst)


logger = logging.getLogger(__name__)

# --- Constanten (respecteert TheLibrarian limieten) ---
COLLECTION_NAME = "omega_advanced_skills"
CHUNK_SIZE = 350
CHUNK_OVERLAP = 50
DOCS_SUBDIR = "rag/documenten"


def _detect_base_dir() -> Path:
    """Detecteer danny-toolkit root automatisch.

    Prioriteit:
    1. Config.BASE_DIR (als danny_toolkit.core.config beschikbaar is)
    2. Loop omhoog vanaf dit bestand tot 'danny-toolkit' gevonden
    3. Loop omhoog vanaf cwd tot 'danny-toolkit' gevonden
    4. Fallback: cwd
    """
    if Config is not None:
        try:
            return Path(Config.BASE_DIR)
        except Exception:
            logger.debug("Suppressed error")

    for anchor in (Path(__file__).resolve(), Path.cwd()):
        current = anchor
        while current != current.parent:
            if current.name == "danny-toolkit":
                return current
            current = current.parent

    return Path.cwd()


class AdvancedKnowledgeBridge:
    """Koppelt Advanced MD-bestanden aan afgeschermde RAG-collectie.

    LAZY DESIGN: __init__ doet GEEN I/O. ChromaDB PersistentClient wordt
    pas geladen bij eerste _get_collection() aanroep. Dit voorkomt
    asyncio event loop clashes in CentralBrain's tool dispatch.
    """

    def __init__(self, db_path: str | None = None) -> None:
        """Init  ."""
        if MarkdownHeaderTextSplitter is None:
            raise ImportError("langchain_text_splitters is vereist")

        self.base_dir = _detect_base_dir()
        self.db_path = db_path or str(self.base_dir / "data" / "rag" / "chromadb")

        # Lazy — wordt pas geladen bij eerste gebruik
        self._client = None
        self._collection = None
        self._embed_fn = None

    def _get_collection(self) -> None:
        """Lazy instantiatie in geïsoleerde thread — voorkomt asyncio clashes.

        ChromaDB PersistentClient gebruikt intern asyncio-componenten.
        Als CentralBrain al in een event loop draait, clasht dit.
        Oplossing: init in een schone thread zonder event loop context.

        Gebruikt Voyage AI embeddings (256d MRL) indien beschikbaar,
        anders ChromaDB default. Dit zorgt voor consistente embeddings
        over alle collecties heen.
        """
        if self._collection is None:
            import threading

            _cyaan = Kleur.FEL_CYAAN if Kleur else None
            logger.debug("AdvancedKnowledgeBridge: lazy ChromaDB init op %s", self.db_path)
            print(kleur(f"  [BRIDGE] Soul (ChromaDB): {self.db_path}", _cyaan))

            # Voyage embed_fn laden buiten thread (vermijdt import issues)
            if _HAS_VOYAGE and self._embed_fn is None:
                try:
                    import io as _io, sys as _sys
                    _old_out, _old_err = _sys.stdout, _sys.stderr
                    _sys.stdout = _io.StringIO()
                    _sys.stderr = _io.StringIO()
                    try:
                        self._embed_fn = get_chroma_embed_fn()
                    finally:
                        _sys.stdout = _old_out
                        _sys.stderr = _old_err
                    print(kleur("  [BRIDGE] Voyage AI embeddings geladen (256d MRL)", _cyaan))
                except Exception as e:
                    logger.debug("Voyage embed_fn niet beschikbaar, fallback naar default: %s", e)

            init_error = [None]
            embed_fn = self._embed_fn

            def _do_init() -> None:
                """Do init."""
                try:
                    import chromadb
                    self._client = chromadb.PersistentClient(path=self.db_path)
                    kwargs = {
                        "name": COLLECTION_NAME,
                        "metadata": {"description": "Omega Advanced Knowledge — 13 domeinen"},
                    }
                    if embed_fn is not None:
                        kwargs["embedding_function"] = embed_fn
                    self._collection = self._client.get_or_create_collection(**kwargs)
                except Exception as exc:
                    init_error[0] = exc

            thread = threading.Thread(target=_do_init, daemon=True)
            thread.start()
            thread.join(timeout=30)

            if init_error[0] is not None:
                raise init_error[0]

        return self._collection

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

        collection = self._get_collection()
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

            # Rate-limited batching (100 chunks, 22s cooldown voor Voyage 3 RPM)
            _MICRO_BATCH = 100
            for b_start in range(0, len(ids), _MICRO_BATCH):
                b_end = min(b_start + _MICRO_BATCH, len(ids))
                collection.upsert(
                    documents=documents[b_start:b_end],
                    metadatas=metadatas[b_start:b_end],
                    ids=ids[b_start:b_end],
                )
                if b_end < len(ids):
                    import time
                    time.sleep(22)
            totaal += len(final_splits)
            print(kleur(
                f"  [OK] {name:<40} {len(final_splits):>3} chunks",
                _groen,
            ))

        print(kleur(
            f"  [DONE] +{totaal} chunks | Collectie: {collection.count()} docs",
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

        collection = self._get_collection()
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

            # Rate-limited batching (100 chunks, 22s cooldown voor Voyage 3 RPM)
            _MICRO_BATCH = 100
            for b_start in range(0, len(ids), _MICRO_BATCH):
                b_end = min(b_start + _MICRO_BATCH, len(ids))
                collection.upsert(
                    documents=documents[b_start:b_end],
                    metadatas=metadatas[b_start:b_end],
                    ids=ids[b_start:b_end],
                )
                if b_end < len(ids):
                    import time
                    time.sleep(22)
            totaal += len(final_splits)
            print(kleur(
                f"  [OK] {filename}: {len(final_splits)} chunks",
                _groen,
            ))

        print(kleur(
            f"  [TOTAAL] +{totaal} chunks | Collectie: {collection.count()} docs",
            _groen,
        ))
        return totaal

    def query(self, vraag: str, n_results: int = 5) -> dict:
        """Doorzoek de advanced knowledge collectie."""
        collection = self._get_collection()
        return collection.query(
            query_texts=[vraag],
            n_results=min(n_results, collection.count() or 1),
        )

    def raadpleeg_omega_skills(self, query: str, n_results: int = 5) -> dict:
        """Anthropic tool interface — doorzoek advanced knowledge.

        Draait VOLLEDIG in een geïsoleerde thread om asyncio event loop
        clashes te voorkomen wanneer CentralBrain deze methode aanroept
        vanuit zijn async tool dispatch pipeline.
        """
        import threading

        result_holder: list = [None]
        error_holder: list = [None]

        def _do_query() -> None:
            """Do query."""
            try:
                collection = self._get_collection()

                if collection.count() == 0:
                    result_holder[0] = {
                        "error": "Collectie leeg — run eerst ingest() of ingest_all()"
                    }
                    return

                raw = collection.query(
                    query_texts=[query],
                    n_results=min(n_results, collection.count() or 1),
                )
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

                result_holder[0] = {
                    "query": query,
                    "resultaten": results,
                    "totaal_in_collectie": collection.count(),
                }
            except Exception as exc:
                error_holder[0] = exc

        thread = threading.Thread(target=_do_query, daemon=True)
        thread.start()
        thread.join(timeout=30)

        if error_holder[0] is not None:
            return {"error": f"Query gefaald: {error_holder[0]}"}
        return result_holder[0] or {"error": "Timeout na 30s"}

    def count(self) -> int:
        """Aantal documenten in de collectie."""
        return self._get_collection().count()

    def reset(self) -> None:
        """Verwijder en hermaak de collectie (clean slate).

        Maakt rechtstreeks een client aan en dropt de collectie
        VOORDAT _get_collection() wordt aangeroepen — voorkomt
        embedding function conflict bij provider-switch.
        """
        import threading
        import chromadb

        # Stap 1: client init + drop (in thread voor asyncio veiligheid)
        if self._client is None:
            init_error = [None]

            def _do_init() -> None:
                try:
                    self._client = chromadb.PersistentClient(path=self.db_path)
                except Exception as exc:
                    init_error[0] = exc

            thread = threading.Thread(target=_do_init, daemon=True)
            thread.start()
            thread.join(timeout=30)
            if init_error[0] is not None:
                raise init_error[0]

        # Stap 2: drop collectie (negeert als niet bestaat)
        try:
            self._client.delete_collection(COLLECTION_NAME)
        except Exception:
            pass

        # Stap 3: reset interne state zodat _get_collection() vers begint
        self._collection = None
        logger.info("AdvancedKnowledgeBridge collectie gereset")


if __name__ == "__main__":
    bridge = AdvancedKnowledgeBridge()
    print(f"Collectie '{COLLECTION_NAME}': {bridge.count()} docs")
    bridge.ingest()
