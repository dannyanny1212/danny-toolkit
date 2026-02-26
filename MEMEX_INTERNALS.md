# Danny Toolkit v6.7.0 — MEMEX Internals

> RAG Kennissysteem | ShardRouter + ShadowAirlock + ChromaDB
>
> **Brain CLI**: `python -m danny_toolkit.brain.brain_cli` → `r` (RAG Query)

---

## 1. Overzicht

MEMEX is het RAG-kennissysteem van Danny Toolkit. Het combineert:
- **ChromaDB** vector store (3 shards)
- **Voyage AI** embeddings (MRL 256d)
- **ShardRouter** fan-out queries
- **ShadowAirlock** zero-crash staging
- **TruthAnchor** cross-encoder verificatie

---

## 2. Directory Structuur

```
data/
├── rag/
│   ├── chromadb/          # ChromaDB vector store (3 shards)
│   │   ├── danny_code/    # Broncode chunks
│   │   ├── danny_docs/    # Documentatie chunks
│   │   └── danny_data/    # Data/config chunks
│   ├── documenten/        # Productie bronbestanden (MD, TXT)
│   └── embedding_cache.json  # LRU embedding cache
├── shadow_rag/
│   └── documenten/        # Staging area (ShadowAirlock)
├── cortical_stack.db      # Episodisch geheugen (SQLite WAL)
└── apps/                  # Per-app JSON state
```

---

## 3. Ingest Process

### Stap 1: Staging (ShadowAirlock)
- Nieuwe docs → `data/shadow_rag/documenten/`
- DocumentForge repareert/valideert YAML frontmatter
- Dry-run ingest test in subprocess
- SHA256 verificatie bij copy naar productie
- Quarantaine bij falen (staging bestand blijft)

### Stap 2: Chunking
- Paragraph method: split op dubbele newlines
- `CHUNK_SIZE = 350` tokens (Config canonical)
- Code-aware: respecteert functie/class grenzen

### Stap 3: Embedding
- Voyage AI `voyage-3-lite` (1024d native)
- MRL truncatie → 256d + L2 hernormalisatie
- `VoyageChromaEmbedding.__call__()` voor documents
- `VoyageChromaEmbedding.embed_query()` voor queries — **fix v6.7.0**: retourneert nu platte `list[float]` (was `list[list[float]]`) voor correcte ChromaDB `query_texts` compatibiliteit
- Retry met backoff bij rate limits (3 RPM free tier)

### Stap 4: Shard Routing
ShardRouter bepaalt collectie op basis van extensie:
- `.py, .js, .ts` → `danny_code`
- `.md, .txt, .pdf` → `danny_docs`
- `.json, .yaml, .csv` → `danny_data`

### Stap 5: Opslag
ChromaDB PersistentClient met Voyage embedding functie.

---

## 4. Query Pipeline

1. **Query ontvangst** (Brain CLI → `r`, of ShardRouter.zoek())
2. **Embedding** — Voyage AI met input_type="query"
3. **Fan-out** — ShardRouter zoekt over geselecteerde shards
4. **Nearest-neighbor** — ChromaDB cosine distance
5. **Merge + sort** — Alle resultaten gesorteerd op distance
6. **TruthAnchor** — Cross-encoder fact verification
7. **HallucinatieSchild** — Claim-scoring, contradictie-detectie

---

## 5. Kwaliteitssystemen

| Systeem | Module | Functie |
|---------|--------|---------|
| **BlackBox** | brain/black_box.py | Negative RAG: failure memory |
| **SelfPruning** | core/self_pruning.py | Vector maintenance (entropy/recency) |
| **CitationMarshall** | brain/citation_marshall.py | Masked mean pooling verificatie |
| **EmbeddingCache** | core/embeddings.py | LRU cache, 10K entries, dim-aware |
| **SemanticCache** | core/semantic_cache.py | Vector-based LLM response cache |

---

## 6. Herindexering

Na dimensie-wijziging of grote doc updates:
```bash
python ingest.py --reset --stats
python ingest.py --batch --method paragraph --path data/rag/documenten
```
