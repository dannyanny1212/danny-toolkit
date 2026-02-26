# Danny Toolkit v6.7.0 — RAG Pipeline

> MEMEX + ShardRouter + ShadowAirlock + RAG Gate
>
> **Brain CLI**: `python -m danny_toolkit.brain.brain_cli` → `r` (RAG Query) of `g` (RAG Gate)

---

## Pipeline Overzicht

```
Documenten → ShadowAirlock staging → DocumentForge YAML → Productie RAG
                                                              │
                                            ShardRouter (3 collecties)
                                                              │
                                         ┌────────┬───────────┤
                                    danny_code  danny_docs  danny_data
                                         │
                                    Voyage AI embeddings (MRL 256d)
                                         │
                                    ChromaDB vector store
```

## 1. Ingest Pipeline

### Bronformaten
PDF, TXT, MD, HTML, Code (.py, .js, .ts, .java, .go, .rs)

### Chunking
- **Paragraph** method: splits op dubbele newlines
- **Code-aware**: respecteert functie/class grenzen
- `CHUNK_SIZE = 350` (canonical uit Config)

### Embeddings
- **Provider**: Voyage AI (`voyage-3-lite`)
- **Native dim**: 1024d
- **MRL truncatie**: 1024d → 256d + L2 hernormalisatie
- **Rate limit**: Free tier = 3 RPM
- **Fallback**: SentenceTransformer paraphrase-multilingual-mpnet-base-v2
- **embed_query() fix**: `VoyageChromaEmbedding.embed_query()` retourneert nu een platte `list[float]` in plaats van `list[list[float]]`, waardoor ChromaDB `query_texts` compatibiliteit gegarandeerd is

### Shard Routing (ShardRouter)
| Shard | Extensies | Doel |
|-------|-----------|------|
| `danny_code` | .py, .js, .ts, .java, .go, .rs, .c, .cpp | Broncode |
| `danny_docs` | .md, .txt, .html, .pdf | Documentatie |
| `danny_data` | .json, .csv, .yaml, .yml, .toml, .xml | Data/config |

## 2. Shadow RAG Staging

Nieuwe documenten gaan NOOIT direct naar productie:

1. Schrijf naar `data/shadow_rag/documenten/`
2. `ShadowAirlock.scan_en_verwerk()` valideert:
   - YAML frontmatter check (DocumentForge)
   - Dry-run ingest validatie
   - SHA256 verificatie bij copy naar productie
3. Gepromoveerde docs → `data/rag/documenten/`
4. Batch ingest triggert automatisch

## 3. Query Pipeline (7 stappen)

1. Gebruiker stelt vraag (Brain CLI → `r`)
2. Query embedding via Voyage AI (input_type="query")
3. ShardRouter fan-out over geselecteerde shards
4. ChromaDB nearest-neighbor search
5. Resultaten merge + sort op distance
6. **TruthAnchor** — cross-encoder fact verification
7. **HallucinatieSchild** — claim-scoring, contradictie-detectie

## 4. RAG Gate Protocol (3-Tier)

Elke schrijfactie doorloopt 3-tier pre-execution validatie (ge-implementeerd in `patchday.py`):

| Tier | Naam | Functie | Altijd actief? |
|------|------|---------|----------------|
| 1 | Static Rules | PII scan, secrets, destructief patroon, path check | Ja |
| 2 | RAG Query | Security context lookup in ChromaDB | Graceful degradation |
| 3 | Governor | OmegaGovernor input validatie + injection detectie | Graceful degradation |

Toegang via:
- `python patchday.py gate "actie beschrijving"`
- Brain CLI → `g` (RAG Gate menu)

## 5. Kwaliteitsborging

| Systeem | Functie |
|---------|---------|
| **BlackBox** | Negative RAG — failure memory voorkomt herhaling |
| **SelfPruning** | Verwijdert lage-kwaliteit vectors (entropy/recency/redundancy) |
| **CitationMarshall** | Strict RAG verificatie via masked mean pooling |
| **EmbeddingCache** | LRU cache (10K entries), dim-aware keys |
