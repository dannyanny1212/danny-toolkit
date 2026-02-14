# RAG_PIPELINE.md

# Danny Toolkit v5 – RAG Pipeline (MEMEX)

Dit document beschrijft de volledige RAG‑pipeline van MEMEX.

## 1. Ingestie

Bronnen in `data/rag/documenten/`:

- PDF
- TXT
- MD
- CODE
- Batch ingest via:
  - `python ingest.py --batch --method paragraph`
  - `python ingest.py --batch --method code`

## 2. Chunking

- Paragraph‑gebaseerd voor gewone tekst
- Code‑aware chunking voor broncode
- Metadata per chunk:
  - pad
  - type
  - timestamp

## 3. Embeddings

- Voyage embeddings
- Vectoren opgeslagen in ChromaDB (`data/rag/chromadb/`)

## 4. Query Flow

1. Gebruiker stelt vraag
2. SwarmEngine routeert naar RAGAgent / ResearchAgent
3. PLAN‑fase: entiteiten en intentie bepalen
4. Query naar ChromaDB
5. Top‑k documenten ophalen
6. Context + vraag naar LLM
7. Antwoord + bronverwijzingen terug

## 5. Kwaliteitsprincipes

- Altijd bronverwijzingen tonen
- Geen hallucinaties zonder bron
- Logging van queries voor debugging
- Geen destructieve acties op basis van RAG alleen
