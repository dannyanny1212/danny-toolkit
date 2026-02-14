# MEMEX_INTERNALS.md

# Danny Toolkit v5 – MEMEX Internals

Dit document beschrijft de interne werking van MEMEX, het RAG‑systeem van Danny Toolkit v5.

## 1. Overzicht

MEMEX is het Retrieval-Augmented Generation subsysteem dat documenten verwerkt, embed, opslaat en opvraagt via ChromaDB.
Het wordt gebruikt door ResearchAgent, RAGAgent en diagnostische workflows.

## 2. Directory-structuur

- data/rag/documents/
  Bevat alle ruwe documenten (PDF, TXT, MD, CODE)

- data/rag/chromadb/
  Persistente vectorstore

- data/rag/cache/
  Query‑cache en tijdelijke resultaten

## 3. Ingestieproces

1. Documenten worden ingelezen
2. Chunking gebeurt op basis van:
   - paragrafen
   - code‑structuur
   - metadata
3. Embeddings worden berekend met Voyage
4. Vectoren worden opgeslagen in ChromaDB
5. Metadata wordt gekoppeld:
   - pad
   - type
   - timestamp
   - bron

## 4. Query Pipeline

1. Gebruiker stelt vraag
2. SwarmEngine routeert naar RAGAgent
3. Intentie‑analyse
4. Query naar ChromaDB
5. Top‑k resultaten ophalen
6. Context + vraag naar LLM
7. Antwoord + bronverwijzingen terug

## 5. Kwaliteitsgaranties

- Geen antwoorden zonder bron
- Logging van alle queries
- Deduplicatie van chunks
- Automatische her‑embedding bij documentupdates

## 6. Beperkingen

- Geen realtime websearch
- Afhankelijk van documentkwaliteit
- Embedding‑kwaliteit bepaalt recall
