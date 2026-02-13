# RAG_PIPELINE.md

# Danny Toolkit v5 – RAG Pipeline (MEMEX)

## 1. Ingestie
- PDF, TXT, MD, CODE
- `python ingest.py --batch --method paragraph`
- `python ingest.py --batch --method code`

## 2. Chunking
- Paragraph‑gebaseerd
- Code‑aware
- Metadata per chunk

## 3. Embeddings
- Voyage embeddings
- ChromaDB opslag

## 4. Query Flow
1. Vraag → SwarmEngine
2. Router → RAGAgent
3. PLAN‑fase
4. Query naar ChromaDB
5. Top‑k documenten
6. Synthese via LLM
7. Antwoord + bronnen

## 5. Kwaliteitsprincipes
- Altijd bronverwijzingen
- Geen hallucinaties
- Logging van queries
