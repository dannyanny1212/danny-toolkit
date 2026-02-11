"""
Production RAG Systeem met echte embeddings.
Versie 2.0 - Met conversatie geheugen, analytics, filtering en meer!
"""

import json
import re
from pathlib import Path
from datetime import datetime
from collections import Counter

from ..core.config import Config
from ..core.utils import clear_scherm, kleur, Kleur
from ..core.embeddings import get_embedder
from ..core.vector_store import VectorStore
from ..core.document_processor import DocumentProcessor
from ..core.generator import Generator


class ProductionRAG:
    """Compleet productie-klaar RAG systeem - Uitgebreide versie."""

    def __init__(self, gebruik_voyage: bool = True):
        Config.ensure_dirs()
        self.data_file = Config.DATA_DIR / "production_rag_data.json"
        self.data = self._laad_data()

        print(kleur("\n[INIT] PRODUCTION RAG v2.0 INITIALISEREN...", Kleur.CYAAN))
        print("-" * 50)

        # Kies embedding provider
        self.embedder = get_embedder(gebruik_voyage)
        print(kleur(f"   [OK] Embedder: {type(self.embedder).__name__}", Kleur.GROEN))

        # Initialiseer componenten
        self.vector_store = VectorStore(self.embedder)
        self.processor = DocumentProcessor()

        # Probeer generator (Groq gratis, of Claude)
        self.generator = None
        self.generator_provider = None

        if Config.has_groq_key() or Config.has_anthropic_key():
            try:
                self.generator = Generator()
                self.generator_provider = self.generator.provider
                print(kleur(f"   [OK] Generator: {self.generator_provider.upper()}", Kleur.GROEN))
            except Exception as e:
                print(kleur(f"   [!] Generator error: {e}", Kleur.ROOD))
        else:
            print(kleur("   [!] Geen API key - alleen retrieval", Kleur.GEEL))
            print("       Tip: set GROQ_API_KEY voor gratis AI")

        # Conversatie geheugen
        self.conversatie = []
        self.max_conversatie_lengte = 10

        # Document metadata
        self.document_metadata = {}

        print("-" * 50)
        print(kleur("[OK] RAG systeem klaar!", Kleur.GROEN))

    def _laad_data(self) -> dict:
        """Laad opgeslagen data."""
        if self.data_file.exists():
            with open(self.data_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return self._migreer_data(data)
        return self._standaard_data()

    def _standaard_data(self) -> dict:
        """Standaard data structuur."""
        return {
            "query_geschiedenis": [],
            "favoriete_queries": [],
            "document_stats": {},
            "statistieken": {
                "totaal_queries": 0,
                "totaal_documenten": 0,
                "totaal_chunks": 0,
                "succesvolle_antwoorden": 0,
                "eerste_gebruik": datetime.now().isoformat(),
                "laatste_gebruik": None,
            },
            "instellingen": {
                "chunk_size": Config.CHUNK_SIZE,
                "chunk_overlap": Config.CHUNK_OVERLAP,
                "top_k": Config.TOP_K,
                "gebruik_conversatie": True,
                "query_expansion": True,
                "show_sources": True,
            },
            "tags": {},
        }

    def _migreer_data(self, data: dict) -> dict:
        """Migreer oude data naar nieuw format."""
        defaults = self._standaard_data()
        for key, value in defaults.items():
            if key not in data:
                data[key] = value
            elif isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    if sub_key not in data[key]:
                        data[key][sub_key] = sub_value
        return data

    def _sla_data_op(self):
        """Sla data op naar bestand."""
        self.data["statistieken"]["laatste_gebruik"] = datetime.now().isoformat()
        with open(self.data_file, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)

    def _expand_query(self, query: str) -> str:
        """Breid query uit voor betere zoekresultaten."""
        if not self.data["instellingen"]["query_expansion"]:
            return query

        # Simpele query expansion met synoniemen
        expansions = {
            "wat is": ["definitie", "betekenis", "uitleg"],
            "hoe werkt": ["proces", "mechanisme", "werking"],
            "waarom": ["reden", "oorzaak", "motivatie"],
            "wanneer": ["tijdstip", "moment", "datum"],
            "wie": ["persoon", "auteur", "maker"],
            "waar": ["locatie", "plaats", "plek"],
            "voorbeeld": ["illustratie", "demonstratie", "case"],
        }

        expanded = query
        for trigger, synonyms in expansions.items():
            if trigger in query.lower():
                expanded += " " + " ".join(synonyms[:2])
                break

        return expanded

    def _format_conversatie_context(self) -> str:
        """Formatteer conversatie context voor de prompt."""
        if not self.conversatie or not self.data["instellingen"]["gebruik_conversatie"]:
            return ""

        context = "Eerdere conversatie:\n"
        for item in self.conversatie[-5:]:  # Laatste 5 exchanges
            context += f"Vraag: {item['vraag']}\n"
            context += f"Antwoord: {item['antwoord'][:200]}...\n\n"

        return context

    def indexeer(self, bron, tags: list = None):
        """Indexeer documenten uit bestand of map."""
        print(kleur("\n[INDEXEREN] Documenten laden...", Kleur.CYAAN))

        pad = Path(bron)
        chunks = []

        if pad.is_file():
            tekst = self.processor.laad_bestand(pad)
            chunks = self.processor.chunk_tekst(tekst, pad.stem)
            print(kleur(f"   [OK] {pad.name} geladen", Kleur.GROEN))

            # Sla metadata op
            self.document_metadata[pad.stem] = {
                "naam": pad.name,
                "pad": str(pad),
                "type": pad.suffix,
                "grootte": pad.stat().st_size,
                "chunks": len(chunks),
                "tags": tags or [],
                "geindexeerd": datetime.now().isoformat(),
            }

        elif pad.is_dir():
            chunks = self.processor.verwerk_map(pad)
            print(kleur(f"   [OK] Map {pad.name} verwerkt", Kleur.GROEN))

            # Metadata voor alle bestanden
            for bestand in pad.glob("*"):
                if bestand.is_file():
                    self.document_metadata[bestand.stem] = {
                        "naam": bestand.name,
                        "pad": str(bestand),
                        "type": bestand.suffix,
                        "tags": tags or [],
                        "geindexeerd": datetime.now().isoformat(),
                    }
        else:
            raise ValueError(f"Ongeldig pad: {pad}")

        self.vector_store.voeg_toe(chunks)

        # Update statistieken
        self.data["statistieken"]["totaal_documenten"] += 1
        self.data["statistieken"]["totaal_chunks"] += len(chunks)

        # Tags opslaan
        if tags:
            for tag in tags:
                if tag not in self.data["tags"]:
                    self.data["tags"][tag] = []
                self.data["tags"][tag].append(pad.stem)

        self._sla_data_op()

        print(kleur(f"\n[OK] {len(chunks)} chunks geïndexeerd", Kleur.GROEN))
        return len(chunks)

    def indexeer_tekst(self, tekst: str, doc_id: str = "document",
                       tags: list = None) -> int:
        """Indexeer tekst direct."""
        chunks = self.processor.chunk_tekst(tekst, doc_id)
        self.vector_store.voeg_toe(chunks)

        # Metadata
        self.document_metadata[doc_id] = {
            "naam": doc_id,
            "type": "tekst",
            "lengte": len(tekst),
            "chunks": len(chunks),
            "tags": tags or [],
            "geindexeerd": datetime.now().isoformat(),
        }

        # Update statistieken
        self.data["statistieken"]["totaal_documenten"] += 1
        self.data["statistieken"]["totaal_chunks"] += len(chunks)

        if tags:
            for tag in tags:
                if tag not in self.data["tags"]:
                    self.data["tags"][tag] = []
                self.data["tags"][tag].append(doc_id)

        self._sla_data_op()
        return len(chunks)

    def indexeer_url(self, url: str, tags: list = None) -> int:
        """Indexeer content van een URL."""
        print(kleur(f"\n[URL] Fetching: {url[:50]}...", Kleur.CYAAN))

        try:
            import urllib.request
            with urllib.request.urlopen(url, timeout=10) as response:
                html = response.read().decode("utf-8")

            # Strip HTML tags
            tekst = re.sub(r'<script[\s\S]*?</script>', '', html)
            tekst = re.sub(r'<style[\s\S]*?</style>', '', tekst)
            tekst = re.sub(r'<[^>]+>', ' ', tekst)
            tekst = re.sub(r'\s+', ' ', tekst).strip()

            if len(tekst) < 100:
                print(kleur("   [!] Te weinig content gevonden", Kleur.ROOD))
                return 0

            # Gebruik URL als doc_id
            doc_id = url.split("/")[-1][:30] or "web_page"
            chunks = self.indexeer_tekst(tekst, doc_id, tags)

            print(kleur(f"   [OK] {chunks} chunks van URL geïndexeerd", Kleur.GROEN))
            return chunks

        except Exception as e:
            print(kleur(f"   [!] URL error: {e}", Kleur.ROOD))
            return 0

    def vraag(self, vraag: str, filter_tags: list = None,
              toon_bronnen: bool = None) -> str:
        """Beantwoord een vraag met RAG."""
        if toon_bronnen is None:
            toon_bronnen = self.data["instellingen"]["show_sources"]

        vraag_kort = vraag[:50] + "..." if len(vraag) > 50 else vraag
        print(kleur(f"\n[ZOEKEN] \"{vraag_kort}\"", Kleur.CYAAN))

        # Query expansion
        expanded_query = self._expand_query(vraag)
        if expanded_query != vraag:
            print(kleur(f"   [+] Query expanded", Kleur.GEEL))

        # Retrieval
        resultaten = self.vector_store.zoek(expanded_query)

        # Filter op tags indien gewenst
        if filter_tags and resultaten:
            gefilterd = []
            for r in resultaten:
                doc_id = r["metadata"].get("bron", "")
                if doc_id in self.document_metadata:
                    doc_tags = self.document_metadata[doc_id].get("tags", [])
                    if any(tag in doc_tags for tag in filter_tags):
                        gefilterd.append(r)
            if gefilterd:
                resultaten = gefilterd
                print(kleur(f"   [*] Gefilterd op tags: {filter_tags}", Kleur.GEEL))

        if not resultaten:
            return "Geen relevante documenten gevonden."

        if toon_bronnen:
            print(kleur(f"   [OK] {len(resultaten)} chunks gevonden:", Kleur.GROEN))
            for r in resultaten[:3]:
                bron = r["metadata"].get("bron", "?")
                score = r.get("score", 0)
                print(f"      • {bron} (score: {score:.3f})")

        # Generation
        antwoord = self._genereer_antwoord(vraag, resultaten)

        # Update statistieken en geschiedenis
        self.data["statistieken"]["totaal_queries"] += 1
        if antwoord and "error" not in antwoord.lower():
            self.data["statistieken"]["succesvolle_antwoorden"] += 1

        self.data["query_geschiedenis"].append({
            "vraag": vraag,
            "resultaten": len(resultaten),
            "top_score": resultaten[0].get("score", 0) if resultaten else 0,
            "datum": datetime.now().isoformat(),
        })

        # Beperk geschiedenis
        if len(self.data["query_geschiedenis"]) > 100:
            self.data["query_geschiedenis"] = self.data["query_geschiedenis"][-100:]

        # Conversatie geheugen
        self.conversatie.append({
            "vraag": vraag,
            "antwoord": antwoord[:500],
        })
        if len(self.conversatie) > self.max_conversatie_lengte:
            self.conversatie = self.conversatie[-self.max_conversatie_lengte:]

        self._sla_data_op()
        return antwoord

    def _genereer_antwoord(self, vraag: str, resultaten: list) -> str:
        """Genereer antwoord met of zonder AI."""
        if self.generator:
            provider = self.generator_provider.upper()
            print(kleur(f"   [AI] {provider} genereert antwoord...", Kleur.MAGENTA))

            try:
                # Voeg conversatie context toe
                context = self._format_conversatie_context()
                if context:
                    vraag_met_context = f"{context}\nHuidige vraag: {vraag}"
                else:
                    vraag_met_context = vraag

                antwoord = self.generator.genereer(vraag_met_context, resultaten)
                return antwoord

            except Exception as e:
                antwoord = kleur(f"[API Error] {e}\n\n", Kleur.ROOD)
                antwoord += kleur("Relevante context:\n", Kleur.GEEL)
                for r in resultaten[:2]:
                    antwoord += f"\n• {r['tekst'][:200]}..."
                return antwoord
        else:
            # Geen generator - toon relevante chunks
            antwoord = kleur("[INFO] Relevante informatie (geen API key):\n\n", Kleur.GEEL)
            for r in resultaten[:3]:
                bron = r["metadata"].get("bron", "Bron")
                antwoord += kleur(f"[{bron}]:\n", Kleur.CYAAN)
                antwoord += f"{r['tekst'][:300]}...\n\n"
            return antwoord

    def batch_vraag(self, vragen: list) -> list:
        """Beantwoord meerdere vragen in batch."""
        print(kleur(f"\n[BATCH] {len(vragen)} vragen verwerken...", Kleur.CYAAN))

        antwoorden = []
        for i, vraag in enumerate(vragen, 1):
            print(kleur(f"\n--- Vraag {i}/{len(vragen)} ---", Kleur.GEEL))
            antwoord = self.vraag(vraag, toon_bronnen=False)
            antwoorden.append({
                "vraag": vraag,
                "antwoord": antwoord,
            })

        return antwoorden

    def zoek_documenten(self, query: str = None, tags: list = None) -> list:
        """Zoek in document metadata."""
        resultaten = []

        for doc_id, meta in self.document_metadata.items():
            match = True

            if query:
                if query.lower() not in doc_id.lower() and \
                   query.lower() not in meta.get("naam", "").lower():
                    match = False

            if tags:
                doc_tags = meta.get("tags", [])
                if not any(tag in doc_tags for tag in tags):
                    match = False

            if match:
                resultaten.append({
                    "id": doc_id,
                    **meta
                })

        return resultaten

    def stats(self):
        """Toon uitgebreide statistieken."""
        s = self.data["statistieken"]

        print(kleur("\n╔════════════════════════════════════════════════════╗", Kleur.CYAAN))
        print(kleur("║          PRODUCTION RAG STATISTIEKEN               ║", Kleur.CYAAN))
        print(kleur("╠════════════════════════════════════════════════════╣", Kleur.CYAAN))
        print(kleur("║  INDEX                                             ║", Kleur.CYAAN))
        print(f"║  Documenten in DB:      {self.vector_store.count():>20}  ║")
        print(f"║  Totaal geïndexeerd:    {s['totaal_documenten']:>20}  ║")
        print(f"║  Totaal chunks:         {s['totaal_chunks']:>20}  ║")
        print(f"║  Embedding dimensies:   {self.embedder.dimensies:>20}  ║")
        print(kleur("║                                                    ║", Kleur.CYAAN))
        print(kleur("║  QUERIES                                           ║", Kleur.CYAAN))
        print(f"║  Totaal queries:        {s['totaal_queries']:>20}  ║")
        print(f"║  Succesvolle antwoorden:{s['succesvolle_antwoorden']:>20}  ║")

        if s['totaal_queries'] > 0:
            success_rate = (s['succesvolle_antwoorden'] / s['totaal_queries']) * 100
            print(f"║  Success rate:          {success_rate:>19.1f}%  ║")

        print(kleur("║                                                    ║", Kleur.CYAAN))
        print(kleur("║  CONFIGURATIE                                      ║", Kleur.CYAAN))
        inst = self.data["instellingen"]
        print(f"║  Chunk grootte:         {inst['chunk_size']:>20}  ║")
        print(f"║  Top-K resultaten:      {inst['top_k']:>20}  ║")
        conv = "Aan" if inst['gebruik_conversatie'] else "Uit"
        print(f"║  Conversatie geheugen:  {conv:>20}  ║")
        gen = self.generator_provider.upper() if self.generator else "Geen"
        print(f"║  Generator:             {gen:>20}  ║")
        print(kleur("╚════════════════════════════════════════════════════╝", Kleur.CYAAN))

    def _toon_documenten(self):
        """Toon geïndexeerde documenten."""
        if not self.document_metadata:
            print(kleur("[!] Geen documenten geïndexeerd.", Kleur.ROOD))
            return

        print(kleur("\n=== GEÏNDEXEERDE DOCUMENTEN ===", Kleur.CYAAN))

        for i, (doc_id, meta) in enumerate(self.document_metadata.items(), 1):
            tags_str = ", ".join(meta.get("tags", [])) or "geen"
            print(f"\n  {i}. {kleur(doc_id, 'groen')}")
            print(f"     Type: {meta.get('type', '?')} | "
                  f"Chunks: {meta.get('chunks', '?')} | "
                  f"Tags: {tags_str}")

    def _toon_tags(self):
        """Toon alle tags."""
        if not self.data["tags"]:
            print(kleur("[!] Geen tags gedefinieerd.", Kleur.ROOD))
            return

        print(kleur("\n=== DOCUMENT TAGS ===", Kleur.CYAAN))

        for tag, docs in self.data["tags"].items():
            print(f"\n  {kleur(tag, 'geel')}: {len(docs)} documenten")
            for doc in docs[:5]:
                print(f"    • {doc}")
            if len(docs) > 5:
                print(f"    ... en {len(docs) - 5} meer")

    def _toon_geschiedenis(self):
        """Toon query geschiedenis."""
        geschiedenis = self.data["query_geschiedenis"]

        if not geschiedenis:
            print(kleur("[!] Geen query geschiedenis.", Kleur.ROOD))
            return

        print(kleur("\n=== RECENTE QUERIES ===", Kleur.CYAAN))

        for i, item in enumerate(reversed(geschiedenis[-10:]), 1):
            datum = datetime.fromisoformat(item["datum"]).strftime("%d-%m %H:%M")
            vraag = item["vraag"][:40] + "..." if len(item["vraag"]) > 40 else item["vraag"]
            print(f"  {i}. [{datum}] \"{vraag}\"")
            print(f"     Resultaten: {item['resultaten']}, Score: {item['top_score']:.3f}")

    def _instellingen_menu(self):
        """Instellingen aanpassen."""
        while True:
            inst = self.data["instellingen"]

            print(kleur("\n╔════════════════════════════════════════════════════╗", Kleur.GEEL))
            print(kleur("║              INSTELLINGEN                          ║", Kleur.GEEL))
            print(kleur("╠════════════════════════════════════════════════════╣", Kleur.GEEL))
            print(f"║  1. Top-K resultaten:   {inst['top_k']:>20}  ║")
            conv = "Aan" if inst['gebruik_conversatie'] else "Uit"
            print(f"║  2. Conversatie geheugen:{conv:>19}  ║")
            exp = "Aan" if inst['query_expansion'] else "Uit"
            print(f"║  3. Query expansion:    {exp:>20}  ║")
            src = "Aan" if inst['show_sources'] else "Uit"
            print(f"║  4. Toon bronnen:       {src:>20}  ║")
            print(kleur("║                                                    ║", Kleur.GEEL))
            print("║  0. Terug                                          ║")
            print(kleur("╚════════════════════════════════════════════════════╝", Kleur.GEEL))

            keuze = input("\nKeuze: ").strip()

            if keuze == "0":
                break
            elif keuze == "1":
                try:
                    nieuwe = int(input("Nieuwe top-K (1-20): "))
                    if 1 <= nieuwe <= 20:
                        inst["top_k"] = nieuwe
                except ValueError:
                    pass
            elif keuze == "2":
                inst["gebruik_conversatie"] = not inst["gebruik_conversatie"]
                if not inst["gebruik_conversatie"]:
                    self.conversatie = []
            elif keuze == "3":
                inst["query_expansion"] = not inst["query_expansion"]
            elif keuze == "4":
                inst["show_sources"] = not inst["show_sources"]

            self._sla_data_op()

    def _export_resultaten(self, vraag: str, antwoord: str):
        """Exporteer vraag en antwoord."""
        export_dir = Config.DATA_DIR / "rag_exports"
        export_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        bestand = export_dir / f"rag_export_{timestamp}.txt"

        content = f"PRODUCTION RAG EXPORT\n"
        content += f"Datum: {datetime.now().strftime('%d-%m-%Y %H:%M')}\n"
        content += "=" * 50 + "\n\n"
        content += f"VRAAG:\n{vraag}\n\n"
        content += f"ANTWOORD:\n{antwoord}\n"

        with open(bestand, "w", encoding="utf-8") as f:
            f.write(content)

        print(kleur(f"\n[OK] Geëxporteerd naar: {bestand}", Kleur.GROEN))

    def _toon_help(self):
        """Toon help informatie."""
        print(kleur("\n╔════════════════════════════════════════════════════╗", Kleur.CYAAN))
        print(kleur("║           PRODUCTION RAG HELP                      ║", Kleur.CYAAN))
        print(kleur("╠════════════════════════════════════════════════════╣", Kleur.CYAAN))
        print("║  COMMANDO'S                                        ║")
        print("║  /stats      - Toon statistieken                   ║")
        print("║  /docs       - Bekijk geïndexeerde documenten      ║")
        print("║  /tags       - Bekijk document tags                ║")
        print("║  /history    - Query geschiedenis                  ║")
        print("║  /settings   - Instellingen aanpassen              ║")
        print("║  /add        - Voeg document/URL toe               ║")
        print("║  /wis        - Wis database                        ║")
        print("║  /export     - Exporteer laatste antwoord          ║")
        print("║  /reset      - Reset conversatie                   ║")
        print("║  /help       - Deze hulp                           ║")
        print("║  /stop       - Afsluiten                           ║")
        print(kleur("║                                                    ║", Kleur.CYAAN))
        print("║  TIPS                                              ║")
        print("║  • Gebruik specifieke vragen voor betere results   ║")
        print("║  • Filter met [tag:naam] in je vraag               ║")
        print("║  • Conversatie geheugen onthoudt context           ║")
        print(kleur("╚════════════════════════════════════════════════════╝", Kleur.CYAAN))

    def _laad_demo_data(self):
        """Laad demo documenten."""
        demo_docs = {
            "ai_engineering": {
                "tekst": """AI Engineering in 2026

Een AI-Engineer bouwt systemen die zelfstandig kunnen denken en handelen.
Dit noemen we "Agentic AI" - AI die proactief problemen oplost.

De Agentic Loop:
1. Perceptie: De AI verzamelt informatie uit de omgeving
2. Planning: De AI analyseert en maakt een strategie
3. Actie: De AI voert taken uit met beschikbare tools
4. Verificatie: De AI controleert of het doel bereikt is

Belangrijke AI modellen in 2026:
- Claude Opus 4.3: Het krachtigste model van Anthropic
- Claude Sonnet: Sneller en goedkoper, ideaal voor dagelijks gebruik
- Claude Haiku: Razendsnel voor simpele taken

RAG (Retrieval-Augmented Generation) is essentieel voor productie AI:
- Geeft AI toegang tot actuele, externe kennis
- Voorkomt hallucinaties door antwoorden te baseren op bronnen
- Werkt met embeddings (vector representaties) en vector databases""",
                "tags": ["ai", "engineering", "agentic"]
            },
            "rag_techniek": {
                "tekst": """RAG: Retrieval-Augmented Generation Uitgelegd

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
- Pinecone: Managed cloud vector database""",
                "tags": ["rag", "techniek", "embeddings"]
            },
            "python_tips": {
                "tekst": """Python Best Practices voor AI Projecten

Code Organisatie:
- Gebruik duidelijke mapstructuur (src/, tests/, docs/)
- Splits code in modules met één verantwoordelijkheid
- Schrijf docstrings voor alle publieke functies

Error Handling:
- Vang specifieke exceptions, niet bare except
- Log errors met context informatie
- Gebruik custom exception classes

Performance:
- Profile code voor optimalisatie
- Gebruik generators voor grote datasets
- Cache dure berekeningen met functools.lru_cache

Testing:
- Schrijf unit tests met pytest
- Gebruik fixtures voor test data
- Aim voor >80% code coverage""",
                "tags": ["python", "tips", "programming"]
            }
        }

        for doc_id, data in demo_docs.items():
            self.indexeer_tekst(data["tekst"], doc_id, data["tags"])

    def _voeg_document_toe(self):
        """Interactief document toevoegen."""
        print(kleur("\n=== DOCUMENT TOEVOEGEN ===", Kleur.GEEL))
        print("  1. Bestand/map pad")
        print("  2. URL")
        print("  3. Directe tekst")
        print("  0. Annuleren")

        keuze = input("\nKeuze: ").strip()

        if keuze == "0":
            return

        tags_input = input("Tags (komma-gescheiden, optioneel): ").strip()
        tags = [t.strip() for t in tags_input.split(",") if t.strip()] or None

        if keuze == "1":
            pad = input("Pad naar bestand of map: ").strip()
            if pad:
                try:
                    self.indexeer(pad, tags)
                except Exception as e:
                    print(kleur(f"[!] Fout: {e}", Kleur.ROOD))

        elif keuze == "2":
            url = input("URL: ").strip()
            if url:
                self.indexeer_url(url, tags)

        elif keuze == "3":
            print("Voer tekst in (eindig met lege regel):")
            lijnen = []
            while True:
                lijn = input()
                if not lijn:
                    break
                lijnen.append(lijn)

            tekst = "\n".join(lijnen)
            if tekst:
                doc_id = input("Document ID: ").strip() or "document"
                self.indexeer_tekst(tekst, doc_id, tags)

    def run(self):
        """Start de interactieve RAG modus."""
        clear_scherm()
        print(kleur("\n╔════════════════════════════════════════════════════╗", Kleur.CYAAN))
        print(kleur("║      PRODUCTION RAG v2.0 - Enterprise Ready        ║", Kleur.CYAAN))
        print(kleur("║      Hash Embeddings + Vector DB + AI Generation   ║", Kleur.CYAAN))
        print(kleur("╚════════════════════════════════════════════════════╝", Kleur.CYAAN))

        # Check voor bestaande data
        if self.vector_store.count() > 0:
            print(kleur(f"\n[INFO] Database bevat {self.vector_store.count()} documenten", Kleur.GEEL))
            herindex = input("Opnieuw indexeren? (j/n): ").lower().strip()
            if herindex == "j":
                self.vector_store.wis()
                self.document_metadata = {}

        # Demo data als database leeg is
        if self.vector_store.count() == 0:
            print(kleur("\n[DEMO] Demo data laden...", Kleur.CYAAN))
            self._laad_demo_data()

        self.stats()

        # Interactieve loop
        print(kleur("\n" + "=" * 50, Kleur.CYAAN))
        print(kleur("VRAAG & ANTWOORD - Typ /help voor commando's", Kleur.CYAAN))
        print(kleur("=" * 50, Kleur.CYAAN))

        laatste_antwoord = ""
        laatste_vraag = ""

        while True:
            try:
                vraag = input(kleur("\nVraag: ", Kleur.GEEL)).strip()
            except (EOFError, KeyboardInterrupt):
                print(kleur("\n\nTot ziens!", Kleur.CYAAN))
                break

            if not vraag:
                continue

            # Commando's
            if vraag.startswith("/"):
                cmd = vraag.lower().split()[0]

                if cmd == "/stop":
                    print(kleur("\nTot ziens!", Kleur.CYAAN))
                    break
                elif cmd == "/stats":
                    self.stats()
                elif cmd == "/docs":
                    self._toon_documenten()
                elif cmd == "/tags":
                    self._toon_tags()
                elif cmd == "/history":
                    self._toon_geschiedenis()
                elif cmd == "/settings":
                    self._instellingen_menu()
                elif cmd == "/add":
                    self._voeg_document_toe()
                elif cmd == "/wis":
                    bevestig = input("Weet je het zeker? (j/n): ").lower().strip()
                    if bevestig == "j":
                        self.vector_store.wis()
                        self.document_metadata = {}
                        self.conversatie = []
                        print(kleur("[OK] Database gewist", Kleur.GROEN))
                elif cmd == "/export":
                    if laatste_vraag and laatste_antwoord:
                        self._export_resultaten(laatste_vraag, laatste_antwoord)
                    else:
                        print(kleur("[!] Geen antwoord om te exporteren", Kleur.ROOD))
                elif cmd == "/reset":
                    self.conversatie = []
                    print(kleur("[OK] Conversatie gereset", Kleur.GROEN))
                elif cmd == "/help":
                    self._toon_help()
                else:
                    print(kleur(f"[!] Onbekend commando: {cmd}", Kleur.ROOD))

                continue

            # Check voor tag filter in vraag
            filter_tags = None
            tag_match = re.search(r'\[tag:(\w+)\]', vraag)
            if tag_match:
                filter_tags = [tag_match.group(1)]
                vraag = re.sub(r'\[tag:\w+\]', '', vraag).strip()

            try:
                antwoord = self.vraag(vraag, filter_tags=filter_tags)
                laatste_vraag = vraag
                laatste_antwoord = antwoord

                print(kleur(f"\n{'='*50}", Kleur.GROEN))
                print(kleur("ANTWOORD:", Kleur.GROEN))
                print(kleur("=" * 50, Kleur.GROEN))
                print(antwoord)

            except Exception as e:
                print(kleur(f"\n[FOUT] {e}", Kleur.ROOD))

        self._sla_data_op()
