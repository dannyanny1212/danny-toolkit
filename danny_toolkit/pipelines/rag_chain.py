# danny_toolkit/pipelines/rag_chain.py

import gc

try:
    from transformers import AutoModelForCausalLM, AutoTokenizer
    _HAS_TRANSFORMERS = True
except ImportError:
    _HAS_TRANSFORMERS = False

import torch

from danny_toolkit.core.embeddings import TorchGPUEmbeddings, get_torch_embedder
from danny_toolkit.core.faiss_index import FaissIndex
from danny_toolkit.brain.citation_marshall import CitationMarshall


def _flush_vram():
    """Force garbage collection and flush CUDA cache."""
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


def load_llm(model_name="microsoft/Phi-3-mini-4k-instruct"):
    if not _HAS_TRANSFORMERS:
        raise ImportError(
            "rag_chain vereist 'transformers'. "
            "Installeer met: pip install transformers"
        )
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        torch_dtype=torch.float16,
        device_map="auto",
    )
    return tokenizer, model


def generate_answer(tokenizer, model, question, context, max_context_tokens=3072):
    # Truncate context to stay within model's 4k window
    context_ids = tokenizer.encode(context, add_special_tokens=False)
    if len(context_ids) > max_context_tokens:
        context = tokenizer.decode(
            context_ids[:max_context_tokens], skip_special_tokens=True
        )

    prompt = (
        "Je bent een behulpzame AI-assistent.\n"
        "Gebruik de context hieronder om de vraag te beantwoorden.\n\n"
        f"Context:\n{context}\n\n"
        f"Vraag: {question}\n"
        "Antwoord:"
    )

    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
    input_len = inputs["input_ids"].shape[1]

    with torch.inference_mode():
        output = model.generate(
            **inputs,
            max_new_tokens=256,
            do_sample=True,
            temperature=0.2,
            top_p=0.9,
        )

    # Slice off the prompt tokens so only the answer is returned
    answer_ids = output[0][input_len:]
    return tokenizer.decode(answer_ids, skip_special_tokens=True)


def run_rag_chain():
    print("=== GPU-RAG Chain ===")

    # 1. Documenten
    docs = [
        "PyTorch met CUDA draait nu op je RTX 3060 Ti.",
        "FAISS CPU werkt als fallback wanneer GPU-FAISS niet beschikbaar is.",
        "Embeddings worden berekend op de GPU voor maximale snelheid.",
        "RAG combineert retrieval en LLM-inference om contextuele antwoorden te genereren."
    ]

    # 2. Embeddings
    embedder = get_torch_embedder()
    doc_vecs = embedder.embed(docs)

    print(f"Embeddings shape: {doc_vecs.shape}")
    print("Building FAISS index...")

    # 3. FAISS index
    index = FaissIndex(dim=doc_vecs.shape[1])
    index.train(doc_vecs)

    # 4. Query
    question = "Hoe werkt GPU versnelling in een RAG pipeline?"
    q_vec = embedder.embed([question])

    # 5. Retrieval
    D, I = index.search(q_vec, k=3)

    # Filter out invalid FAISS indices (-1 means no result)
    retrieved_docs = [docs[idx] for idx in I[0] if 0 <= idx < len(docs)]

    print("\n=== Retrieved Docs ===")
    for d in retrieved_docs:
        print("-", d)

    # =========================================================================
    # MEMORY HANDSHAKE — VRAM Choreography
    # =========================================================================
    # Embedder (~400 MB) stays parked in VRAM while LLM (~2.5 GB) loads.
    # If VRAM can't hold both (OOM), fall back to Slow Path: release embedder
    # before LLM, then reload embedder for Marshall verification.
    # =========================================================================

    # 6. Free vectors but keep embedder for Fast Path
    del doc_vecs, q_vec
    _flush_vram()
    print("\n>> Vectors freed, embedder stays alive (~400 MB parked)")

    # 7. LLM laden — try Fast Path (embedder + LLM coexist)
    slow_path = False
    print("\n>> Loading LLM (Fast Path: embedder stays in VRAM)...")
    try:
        tokenizer, model = load_llm()
    except RuntimeError as e:
        if "out of memory" in str(e).lower() or "CUDA" in str(e):
            # OOM: switch to Slow Path
            print(f"\n>> OOM detected, switching to Slow Path...")
            del embedder
            _flush_vram()
            slow_path = True
            tokenizer, model = load_llm()
        else:
            raise

    # 8. Context bouwen
    context = "\n".join(retrieved_docs)

    # 9. Antwoord genereren
    raw_answer = generate_answer(tokenizer, model, question, context)

    print("\n=== Raw Antwoord ===")
    print(raw_answer)

    # 10. Free LLM VRAM before verification
    del tokenizer, model
    _flush_vram()
    print(">> LLM freed")

    # 11. Citation Marshall — hallucination check
    if slow_path:
        # Slow Path: reload embedder for Marshall
        print(">> Slow Path: reloading embedder for verification...")
        embedder = TorchGPUEmbeddings()

    print("\n=== Citation Verification ===")
    marshall = CitationMarshall(embedding_provider=embedder)
    source_docs = [{"content": doc} for doc in retrieved_docs]
    verified_answer = marshall.verify_response(raw_answer, source_docs)

    print("\n=== Verified Antwoord ===")
    print(verified_answer)

    stats = marshall.get_stats()
    path_label = "Slow Path" if slow_path else "Fast Path"
    print(f"\n=== Marshall Stats ({path_label}) ===")
    print(f"Verified: {stats['verified']} | Flagged: {stats['flagged']} | "
          f"Uncited: {stats['uncited']} | Trust Rate: {stats['trust_rate']}")

    # 12. Final cleanup
    del embedder, marshall
    _flush_vram()
    print(">> All VRAM freed")

if __name__ == "__main__":
    run_rag_chain()
