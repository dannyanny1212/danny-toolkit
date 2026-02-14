# Retrieval-Augmented Generation (RAG)

De toolkit bevat een GPU-versnelde RAG-pipeline:

- Document parsing
- Embedding generation
- FAISS indexing
- Context retrieval
- Phi-3 inference

## Pipeline starten

```bash
python -m danny_toolkit.pipelines.rag_chain
```

## Architectuur

```
Documenten
    |
    v
TorchGPUEmbeddings (paraphrase-multilingual-mpnet-base-v2)
    |
    v
FaissIndex (GPU/CPU hybrid)
    |
    v
Query embedding + Top-K retrieval
    |
    v
Phi-3 Mini Instruct (GGUF, CUDA offload)
    |
    v
Contextueel antwoord
```

## Componenten

| Component | Bestand | Beschrijving |
|-----------|---------|--------------|
| Embeddings | `core/embeddings.py` | GPU-accelerated sentence embeddings |
| FAISS Index | `core/faiss_index.py` | Hybrid GPU/CPU vector index |
| RAG Demo | `pipelines/rag_gpu.py` | Retrieval-only demo |
| RAG Chain | `pipelines/rag_chain.py` | Volledige RAG met LLM generatie |
| GPU Utility | `core/gpu.py` | CUDA device detectie |
