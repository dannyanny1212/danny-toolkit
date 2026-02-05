"""
Production RAG Systeem met echte embeddings.
"""

from pathlib import Path

from ..core.config import Config
from ..core.utils import clear_scherm
from ..core.embeddings import get_embedder, HashEmbeddings
from ..core.vector_store import VectorStore
from ..core.document_processor import DocumentProcessor
from ..core.generator import Generator


class ProductionRAG:
    """Compleet productie-klaar RAG systeem."""

    def __init__(self, gebruik_voyage: bool = True):
        Config.ensure_dirs()
        print("\n[INIT] PRODUCTION RAG INITIALISEREN...")
        print("-" * 40)

        # Kies embedding provider
        self.embedder = get_embedder(gebruik_voyage)

        # Initialiseer componenten
        self.vector_store = VectorStore(self.embedder)
        self.processor = DocumentProcessor()

        # Probeer generator (Groq gratis, of Claude)
        if Config.has_groq_key() or Config.has_anthropic_key():
            try:
                self.generator = Generator()  # Auto-selecteert beste provider
            except Exception as e:
                print(f"   [!] API error: {e}")
                self.generator = None
        else:
            self.generator = None
            print("   [!] Geen API key - alleen retrieval (set GROQ_API_KEY voor gratis AI)")

        print("-" * 40)
        print("[OK] RAG systeem klaar!\n")

    def indexeer(self, bron):
        """Indexeer documenten uit bestand of map."""
        print("\n[INDEXEREN] Documenten indexeren...")

        pad = Path(bron)

        if pad.is_file():
            tekst = self.processor.laad_bestand(pad)
            chunks = self.processor.chunk_tekst(tekst, pad.stem)
        elif pad.is_dir():
            chunks = self.processor.verwerk_map(pad)
        else:
            raise ValueError(f"Ongeldig pad: {pad}")

        self.vector_store.voeg_toe(chunks)
        print(f"\n[OK] {len(chunks)} chunks geindexeerd")

    def indexeer_tekst(self, tekst: str, doc_id: str = "document"):
        """Indexeer tekst direct."""
        chunks = self.processor.chunk_tekst(tekst, doc_id)
        self.vector_store.voeg_toe(chunks)
        return len(chunks)

    def vraag(self, vraag: str, toon_bronnen: bool = True) -> str:
        """Beantwoord een vraag met RAG."""
        vraag_kort = vraag[:50] + "..." if len(vraag) > 50 else vraag
        print(f"\n[ZOEKEN] \"{vraag_kort}\"")

        # Retrieval
        resultaten = self.vector_store.zoek(vraag)

        if not resultaten:
            return "Geen relevante documenten gevonden."

        if toon_bronnen:
            print(f"   [OK] {len(resultaten)} chunks gevonden:")
            for r in resultaten[:3]:
                bron = r["metadata"].get("bron", "?")
                print(f"      - {bron} (score: {r['score']:.3f})")

        # Generation
        if self.generator:
            provider = self.generator.provider.upper()
            print(f"   [AI] {provider} genereert antwoord...")
            try:
                antwoord = self.generator.genereer(vraag, resultaten)
            except Exception as e:
                antwoord = f"API Error: {e}\n\nRelevante context:\n"
                for r in resultaten[:2]:
                    antwoord += f"\n- {r['tekst'][:200]}..."
        else:
            antwoord = "[INFO] Relevante informatie (geen API key):\n\n"
            for r in resultaten[:3]:
                bron = r["metadata"].get("bron", "Bron")
                antwoord += f"**{bron}:**\n{r['tekst'][:300]}...\n\n"

        return antwoord

    def stats(self):
        """Toon statistieken."""
        print(f"\n[STATS]")
        print(f"   Documenten: {self.vector_store.count()}")
        print(f"   Embedding dim: {self.embedder.dimensies}")
        print(f"   Chunk grootte: {Config.CHUNK_SIZE}")
        print(f"   Top-K: {Config.TOP_K}")

    def _laad_demo_data(self):
        """Laad demo documenten."""
        demo_docs = {
            "ai_engineering": """AI Engineering in 2026

Een AI-Engineer bouwt systemen die zelfstandig kunnen denken en handelen.
Dit noemen we "Agentic AI" - AI die proactief problemen oplost.

De Agentic Loop:
1. Perceptie: De AI verzamelt informatie uit de omgeving
2. Planning: De AI analyseert en maakt een strategie
3. Actie: De AI voert taken uit met beschikbare tools
4. Verificatie: De AI controleert of het doel bereikt is

Belangrijke AI modellen in 2026:
- Claude Opus 4.5: Het krachtigste model van Anthropic
- Claude Sonnet: Sneller en goedkoper, ideaal voor dagelijks gebruik
- Claude Haiku: Razendsnel voor simpele taken

RAG (Retrieval-Augmented Generation) is essentieel voor productie AI:
- Geeft AI toegang tot actuele, externe kennis
- Voorkomt hallucinaties door antwoorden te baseren op bronnen
- Werkt met embeddings (vector representaties) en vector databases""",

            "rag_techniek": """RAG: Retrieval-Augmented Generation Uitgelegd

RAG is een architectuur die LLMs combineert met externe kennisbronnen.

Het RAG proces stap voor stap:
1. INDEXEREN: Documenten worden gesplitst in chunks
2. EMBEDDING: Elke chunk wordt omgezet naar een vector
3. OPSLAG: Vectoren worden opgeslagen in een vector database
4. QUERY: Gebruikersvraag wordt ook omgezet naar een vector
5. RETRIEVAL: Database zoekt meest vergelijkbare vectoren
6. AUGMENTATION: Gevonden documenten worden toegevoegd aan prompt
7. GENERATION: LLM genereert antwoord gebaseerd op de context

Cosine Similarity formule:
similarity = (A . B) / (||A|| x ||B||)

Productie tools:
- Voyage AI: State-of-the-art embeddings
- ChromaDB: Open-source vector database
- Pinecone: Managed cloud vector database"""
        }

        for doc_id, tekst in demo_docs.items():
            self.indexeer_tekst(tekst, doc_id)

    def run(self):
        """Start de interactieve RAG modus."""
        clear_scherm()
        print("\n" + "=" * 50)
        print("   PRODUCTION RAG SYSTEEM")
        print("   Hash Embeddings + Vector DB + AI (Groq/Claude)")
        print("=" * 50)

        # Check voor bestaande data
        if self.vector_store.count() > 0:
            print(f"\n[INFO] Database bevat {self.vector_store.count()} documenten")
            herindex = input("Opnieuw indexeren? (j/n): ").lower().strip()
            if herindex == "j":
                self.vector_store.wis()

        # Demo data als database leeg is
        if self.vector_store.count() == 0:
            print("\n[DEMO] Demo data laden...")
            self._laad_demo_data()

        self.stats()

        # Interactieve loop
        print("\n" + "=" * 50)
        print("VRAAG & ANTWOORD")
        print("=" * 50)
        print("Commando's: /stats, /wis, /stop\n")

        while True:
            try:
                vraag = input("Vraag: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n\nTot ziens!")
                break

            if not vraag:
                continue

            if vraag == "/stop":
                print("\nTot ziens!")
                break
            elif vraag == "/stats":
                self.stats()
                continue
            elif vraag == "/wis":
                self.vector_store.wis()
                print("[OK] Database gewist")
                continue

            try:
                antwoord = self.vraag(vraag)
                print(f"\n{'='*40}\nANTWOORD:\n{'='*40}\n{antwoord}\n")
            except Exception as e:
                print(f"\n[FOUT] {e}\n")
