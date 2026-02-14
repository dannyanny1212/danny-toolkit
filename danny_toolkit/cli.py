# danny_toolkit/cli.py — Unified CLI for Danny Toolkit
import argparse
import sys


def cmd_gpu(args):
    """GPU inference met llama-cpp-python + Phi-3 GGUF."""
    import os
    cuda_bin = r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.1\bin"
    if cuda_bin not in os.environ.get("PATH", ""):
        os.environ["PATH"] = cuda_bin + os.pathsep + os.environ.get("PATH", "")

    from llama_cpp import Llama

    model_path = args.model or r"C:\models\phi3.Q4_K_M.gguf"
    print(f"Model laden: {model_path}")

    llm = Llama(
        model_path=model_path,
        n_gpu_layers=-1,
        n_ctx=4096,
        verbose=False,
    )

    prompt = f"<|user|>\n{args.question}\n<|end|>\n<|assistant|>\n"
    output = llm(prompt, max_tokens=256, temperature=0.2, top_p=0.9)
    antwoord = output["choices"][0]["text"].strip()

    print(f"\n=== GPU Antwoord ===\n{antwoord}")


def cmd_chain(args):
    """Volledige RAG chain: embeddings → FAISS → Phi-3 LLM."""
    from danny_toolkit.core.embeddings import TorchGPUEmbeddings
    from danny_toolkit.core.faiss_index import FaissIndex
    from danny_toolkit.pipelines.rag_chain import load_llm, generate_answer

    docs = [
        "PyTorch met CUDA draait nu op je RTX 3060 Ti.",
        "FAISS CPU werkt als fallback wanneer GPU-FAISS niet beschikbaar is.",
        "Embeddings worden berekend op de GPU voor maximale snelheid.",
        "RAG combineert retrieval en LLM-inference om contextuele antwoorden te genereren.",
    ]

    print("Embeddings berekenen...")
    embedder = TorchGPUEmbeddings()
    doc_vecs = embedder.embed(docs)

    print("FAISS index bouwen...")
    index = FaissIndex(dim=doc_vecs.shape[1])
    index.train(doc_vecs)

    q_vec = embedder.embed([args.question])
    D, I = index.search(q_vec, k=3)
    retrieved = [docs[idx] for idx in I[0]]

    print("\n=== Retrieved Docs ===")
    for d in retrieved:
        print(f"  - {d}")

    print("\nLLM laden...")
    tokenizer, model = load_llm()
    context = "\n".join(retrieved)
    answer = generate_answer(tokenizer, model, args.question, context)

    print(f"\n=== Antwoord ===\n{answer}")


def cmd_cpu(args):
    """CPU-only retrieval met FAISS (geen LLM)."""
    from danny_toolkit.core.embeddings import TorchGPUEmbeddings
    from danny_toolkit.core.faiss_index import FaissIndex

    docs = [
        "PyTorch met CUDA draait nu op je RTX 3060 Ti.",
        "FAISS CPU werkt als fallback wanneer GPU-FAISS niet beschikbaar is.",
        "Dit is een testdocument voor retrieval.",
        "Embeddings worden berekend op de GPU voor maximale snelheid.",
        "RAG combineert retrieval en LLM-inference om contextuele antwoorden te genereren.",
    ]

    print("Embeddings berekenen...")
    embedder = TorchGPUEmbeddings()
    doc_vecs = embedder.embed(docs)

    print("FAISS index bouwen...")
    index = FaissIndex(dim=doc_vecs.shape[1])
    index.train(doc_vecs)

    q_vec = embedder.embed([args.question])
    D, I = index.search(q_vec, k=3)

    print(f"\n=== CPU Retrieval: '{args.question}' ===")
    for rank, idx in enumerate(I[0]):
        print(f"  {rank+1}. {docs[idx]}  (distance={D[0][rank]:.4f})")


def cmd_index(args):
    """Index een directory met documenten naar FAISS."""
    from danny_toolkit.core.doc_loader import load_directory
    from danny_toolkit.core.embeddings import TorchGPUEmbeddings
    from danny_toolkit.core.index_store import IndexStore

    print(f"=== Danny Index: {args.directory} ===")
    chunks = load_directory(args.directory, chunk_size=args.chunk_size)

    if not chunks:
        print("Geen documenten gevonden.")
        sys.exit(1)

    texts = [c["text"] for c in chunks]

    print("Embeddings berekenen...")
    embedder = TorchGPUEmbeddings()
    vectors = embedder.embed(texts).numpy().astype("float32")

    print("FAISS index bouwen...")
    store = IndexStore()
    store.build(vectors, chunks)

    print(f"\n=== Klaar! {len(chunks)} chunks geindexeerd ===")


def cmd_ask(args):
    """Stel een vraag aan je geindexeerde documenten."""
    import os
    cuda_bin = r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.1\bin"
    if cuda_bin not in os.environ.get("PATH", ""):
        os.environ["PATH"] = cuda_bin + os.pathsep + os.environ.get("PATH", "")

    from danny_toolkit.core.embeddings import TorchGPUEmbeddings
    from danny_toolkit.core.index_store import IndexStore
    from llama_cpp import Llama

    store = IndexStore()
    if not store.exists():
        print("Geen index gevonden. Draai eerst: danny index <directory>")
        sys.exit(1)

    print(f"=== Danny Ask: '{args.question}' ===")

    # 1. Embed query
    embedder = TorchGPUEmbeddings()
    q_vec = embedder.embed([args.question]).numpy().astype("float32")

    # 2. Retrieve
    results = store.search(q_vec, k=args.top_k)

    print(f"\n--- Top {len(results)} bronnen ---")
    for r in results:
        src = os.path.basename(r["source"])
        print(f"  {r['rank']}. [{src}] {r['text'][:80]}...")

    # 3. Build context
    context = "\n\n".join(r["text"] for r in results)

    # 4. LLM answer
    model_path = args.model or r"C:\models\phi3.Q4_K_M.gguf"
    print(f"\nLLM laden: {model_path}")
    llm = Llama(model_path=model_path, n_gpu_layers=-1, n_ctx=4096, verbose=False)

    prompt = (
        f"<|user|>\n"
        f"Gebruik de context hieronder om de vraag te beantwoorden.\n\n"
        f"Context:\n{context}\n\n"
        f"Vraag: {args.question}\n"
        f"<|end|>\n<|assistant|>\n"
    )
    output = llm(prompt, max_tokens=512, temperature=0.2, top_p=0.9)
    antwoord = output["choices"][0]["text"].strip()

    print(f"\n=== Antwoord ===\n{antwoord}")


def main():
    parser = argparse.ArgumentParser(
        prog="danny",
        description="Danny Toolkit CLI — GPU RAG & Inference",
    )
    sub = parser.add_subparsers(dest="command")

    # danny gpu "vraag"
    p_gpu = sub.add_parser("gpu", help="GPU inference met Phi-3 GGUF")
    p_gpu.add_argument("question", help="Vraag voor het model")
    p_gpu.add_argument("--model", help="Pad naar GGUF model", default=None)

    # danny chain "vraag"
    p_chain = sub.add_parser("chain", help="Volledige RAG chain (retrieval + LLM)")
    p_chain.add_argument("question", help="Vraag voor de RAG chain")

    # danny cpu "vraag"
    p_cpu = sub.add_parser("cpu", help="CPU-only FAISS retrieval")
    p_cpu.add_argument("question", help="Vraag voor retrieval")

    # danny index <directory>
    p_index = sub.add_parser("index", help="Index een directory met documenten")
    p_index.add_argument("directory", help="Pad naar directory met documenten")
    p_index.add_argument("--chunk-size", type=int, default=500, help="Woorden per chunk")

    # danny ask "vraag"
    p_ask = sub.add_parser("ask", help="Stel een vraag aan je geindexeerde docs")
    p_ask.add_argument("question", help="Vraag over je documenten")
    p_ask.add_argument("--top-k", type=int, default=5, help="Aantal bronnen")
    p_ask.add_argument("--model", help="Pad naar GGUF model", default=None)

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    commands = {
        "gpu": cmd_gpu, "chain": cmd_chain, "cpu": cmd_cpu,
        "index": cmd_index, "ask": cmd_ask,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
