# danny_toolkit/cli.py — Unified CLI for Danny Toolkit
import argparse
import sys
import io

# Windows UTF-8 fix
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


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

    prompt = (
        f"<|system|>\n"
        f"Je bent een behulpzame assistent. Antwoord kort en bondig in het Nederlands. "
        f"Verzin NIETS en blijf bij het onderwerp.\n"
        f"<|end|>\n"
        f"<|user|>\n{args.question}\n<|end|>\n<|assistant|>\n"
    )
    output = llm(prompt, max_tokens=256, temperature=0.0, top_p=0.9, repeat_penalty=1.1)
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
    from danny_toolkit.core.index_store import IndexStore

    if args.rebuild:
        store = IndexStore()
        if not store.exists():
            print("Geen index gevonden. Draai eerst: danny index <directory>")
            sys.exit(1)

        print("=== Danny Index: Rebuild ===")
        store._load()

        texts = [m["text"] for m in store.metadata]
        if not texts:
            print("  Geen chunks gevonden om te rebuilden.")
            sys.exit(1)

        print(f"  Chunks geladen:      {len(texts)}")
        print("  Embeddings berekenen...")

        from danny_toolkit.core.embeddings import TorchGPUEmbeddings
        embedder = TorchGPUEmbeddings()
        vectors = embedder.embed(texts).numpy().astype("float32")

        model_name = getattr(embedder, "model_name", "sentence-transformers/all-MiniLM-L6-v2")
        print(f"  Embeddings berekend: {len(texts)} ({model_name})")

        store.index = None  # Reset zodat build() een nieuwe index maakt
        store.build(vectors, store.metadata)

        print(f"  FAISS herbouwd:      ja")
        print(f"  Schema:              v{store._schema_version}")
        print(f"\nResultaat: REBUILD COMPLEET")
        return

    if args.upgrade:
        store = IndexStore()
        if not store.exists():
            print("Geen index gevonden. Draai eerst: danny index <directory>")
            sys.exit(1)

        print("=== Danny Index: Upgrade ===")
        result = store.upgrade()

        print(f"  Schema:              v{result['old_schema']} \u2192 v{result['new_schema']}")
        print(f"  Hashes toegevoegd:   {result['hashes_added']}")
        print(f"  Duplicaten verwijderd: {result['duplicates_removed']}")
        print(f"  Lege chunks verwijderd: {result['empty_removed']}")
        print(f"  Index herbouwd:      ja")
        print(f"  Finaal:              {result['final_count']} chunks")
        print(f"\nResultaat: UPGRADE COMPLEET")
        return

    if args.repair:
        store = IndexStore()
        if not store.exists():
            print("Geen index gevonden. Draai eerst: danny index <directory>")
            sys.exit(1)

        print("=== Danny Index: Repair Mode ===")
        result = store.repair()

        print(f"\n=== Repair Klaar ===")
        print(f"  Origineel:           {result['original_count']} chunks")
        print(f"  Hashes toegevoegd:   {result['hashes_added']}")
        print(f"  Duplicaten verwijderd: {result['duplicates_removed']}")
        print(f"  Finaal:              {result['final_count']} chunks")
        return

    if not args.directory:
        print("Geef een directory op, of gebruik --repair / --upgrade.")
        sys.exit(1)

    from danny_toolkit.core.doc_loader import load_directory
    from danny_toolkit.core.embeddings import TorchGPUEmbeddings

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
    store.append(vectors, chunks)

    print(f"\n=== Klaar! {len(chunks)} chunks geindexeerd ===")


def cmd_ask(args):
    """Stel een vraag aan je geindexeerde documenten."""
    import os
    cuda_bin = r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.1\bin"
    if cuda_bin not in os.environ.get("PATH", ""):
        os.environ["PATH"] = cuda_bin + os.pathsep + os.environ.get("PATH", "")

    from danny_toolkit.core.embeddings import TorchGPUEmbeddings
    from danny_toolkit.core.index_store import IndexStore

    try:
        from llama_cpp import Llama
        has_llm = True
    except ImportError:
        has_llm = False

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

    # 3. Build context (max ~3000 tokens ≈ 12000 chars om binnen 4096 context te blijven)
    context_parts = []
    char_count = 0
    used_count = 0
    for r in results:
        if char_count + len(r["text"]) > 12000:
            r["_used"] = False
        else:
            r["_used"] = True
            context_parts.append(r["text"])
            char_count += len(r["text"])
            used_count += 1
    context = "\n\n".join(context_parts)

    # --trace output
    if getattr(args, "trace", False):
        from rich.console import Console
        from rich.table import Table

        console = Console()
        table = Table(
            title=f"Trace: {len(results)} chunks, {used_count} gebruikt ({char_count} chars)",
            border_style="cyan",
        )
        table.add_column("#", style="bold", width=3)
        table.add_column("Status", width=8)
        table.add_column("Dist", width=8)
        table.add_column("Bron", width=20)
        table.add_column("Chunk", width=6)
        table.add_column("Hash", width=14)
        table.add_column("Preview")

        for r in results:
            status = "[green]GEBRUIKT[/green]" if r.get("_used") else "[yellow]AFGEKAPT[/yellow]"
            h = r.get("hash", "-")[:12] if r.get("hash") else "-"
            src = os.path.basename(r["source"])
            preview = r["text"][:80].replace("\n", " ")
            table.add_row(
                str(r["rank"]), status, f"{r['distance']:.4f}",
                src, str(r["chunk"]), h, preview + "...",
            )

        console.print(table)

    # 4. LLM answer
    if not has_llm:
        print("\n[llama-cpp-python niet geinstalleerd — alleen retrieval weergegeven]")
        return

    model_path = args.model or r"C:\models\phi3.Q4_K_M.gguf"
    print(f"\nLLM laden: {model_path}")
    llm = Llama(model_path=model_path, n_gpu_layers=-1, n_ctx=4096, verbose=False)

    prompt = (
        f"<|system|>\n"
        f"Je bent een behulpzame assistent. Beantwoord ALLEEN op basis van de gegeven context. "
        f"Verzin NIETS. Als het antwoord niet in de context staat, zeg dat eerlijk. "
        f"Antwoord kort en bondig in het Nederlands.\n"
        f"<|end|>\n"
        f"<|user|>\n"
        f"Context:\n{context}\n\n"
        f"Vraag: {args.question}\n"
        f"<|end|>\n<|assistant|>\n"
    )
    output = llm(prompt, max_tokens=256, temperature=0.0, top_p=0.9, repeat_penalty=1.1)
    antwoord = output["choices"][0]["text"].strip()

    print(f"\n=== Antwoord ===\n{antwoord}")


def cmd_stats(args):
    """Toon statistieken over de FAISS index."""
    from danny_toolkit.core.index_store import IndexStore

    store = IndexStore()
    if not store.exists():
        print("Geen index gevonden. Draai eerst: danny index <directory>")
        sys.exit(1)

    s = store.stats()

    print("=== Index Statistieken ===")
    print(f"  Totaal chunks:    {s['total_chunks']}")
    print(f"  Totaal bronnen:   {s['total_sources']}")
    print(f"  Chunks met hash:  {s['has_hashes']}")
    print(f"  Index type:       {s['index_type']}")
    print(f"  Vectors grootte:  {s['vectors_size_mb']} MB")
    print(f"  Metadata grootte: {s['metadata_size_mb']} MB")

    if s["sources"]:
        print(f"\n--- Bronnen ({s['total_sources']}) ---")
        for src in s["sources"]:
            print(f"  - {src}")

    if s["domains"]:
        print(f"\n--- Domeinen ({len(s['domains'])}) ---")
        for d in s["domains"]:
            print(f"  - {d}")


def cmd_verify(args):
    """Verifieer consistentie van de FAISS index."""
    from danny_toolkit.core.index_store import IndexStore

    store = IndexStore()
    if not store.exists():
        print("Geen index gevonden. Draai eerst: danny index <directory>")
        sys.exit(1)

    result = store.verify()

    print("=== Index Verificatie ===")
    for check in result["checks"]:
        status = "OK" if check["passed"] else "FAIL"
        print(f"  [{status}] {check['name']}: {check['detail']}")

    print()
    if result["ok"]:
        print("Resultaat: ALLES OK")
    else:
        print("Resultaat: FOUTEN GEVONDEN")
        sys.exit(1)


def cmd_trace(args):
    """Trace retrieval resultaten zonder LLM."""
    import os
    cuda_bin = r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.1\bin"
    if cuda_bin not in os.environ.get("PATH", ""):
        os.environ["PATH"] = cuda_bin + os.pathsep + os.environ.get("PATH", "")

    from danny_toolkit.core.embeddings import TorchGPUEmbeddings
    from danny_toolkit.core.index_store import IndexStore
    from rich.console import Console
    from rich.table import Table

    store = IndexStore()
    if not store.exists():
        print("Geen index gevonden. Draai eerst: danny index <directory>")
        sys.exit(1)

    # 1. Embed query
    embedder = TorchGPUEmbeddings()
    q_vec = embedder.embed([args.question]).numpy().astype("float32")

    # 2. Retrieve
    results = store.search(q_vec, k=args.top_k)

    # 3. Rich Table
    console = Console()
    table = Table(
        title=f"Trace: '{args.question}' — {len(results)} resultaten",
        border_style="cyan",
    )
    table.add_column("#", style="bold", width=3)
    table.add_column("Dist", width=8)
    table.add_column("Bron", width=20)
    table.add_column("Chunk", width=6)
    table.add_column("Hash", width=14)
    table.add_column("Preview")

    for r in results:
        h = r.get("hash", "-")[:12] if r.get("hash") else "-"
        src = os.path.basename(r["source"])
        preview = r["text"][:80].replace("\n", " ")
        table.add_row(
            str(r["rank"]), f"{r['distance']:.4f}",
            src, str(r["chunk"]), h, preview + "...",
        )

    console.print(table)

    # 4. HTML export
    if args.html:
        from datetime import datetime
        from pathlib import Path

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_dir = Path("data/output")
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / f"trace_{timestamp}.html"

        rows_html = ""
        for r in results:
            dist = r["distance"]
            # Kleurcodering: groen (dichtbij) → rood (ver)
            # Normaliseer distance naar 0-1 range (0=groen, 1=rood)
            ratio = min(dist / 2.0, 1.0)
            red = int(ratio * 220)
            green = int((1 - ratio) * 180)
            color = f"rgb({red}, {green}, 60)"

            h = r.get("hash", "-")[:12] if r.get("hash") else "-"
            src = os.path.basename(r["source"])
            text_escaped = r["text"].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            rows_html += f"""<tr>
  <td>{r['rank']}</td>
  <td style="color:{color};font-weight:bold">{dist:.4f}</td>
  <td>{src}</td>
  <td>{r['chunk']}</td>
  <td><code>{h}</code></td>
  <td class="text">{text_escaped}</td>
</tr>
"""

        html = f"""<!DOCTYPE html>
<html lang="nl">
<head>
<meta charset="utf-8">
<title>Danny Trace — {args.question}</title>
<style>
  body {{ font-family: 'Segoe UI', Tahoma, sans-serif; background: #1a1a2e; color: #e0e0e0; margin: 2em; }}
  h1 {{ color: #00d4ff; font-size: 1.4em; }}
  .meta {{ color: #888; margin-bottom: 1.5em; }}
  table {{ border-collapse: collapse; width: 100%; }}
  th {{ background: #16213e; color: #00d4ff; padding: 8px 12px; text-align: left; }}
  td {{ padding: 8px 12px; border-bottom: 1px solid #2a2a4a; }}
  tr:hover {{ background: #16213e; }}
  code {{ background: #2a2a4a; padding: 2px 6px; border-radius: 3px; font-size: 0.85em; }}
  .text {{ max-width: 500px; white-space: pre-wrap; word-break: break-word; font-size: 0.9em; }}
</style>
</head>
<body>
<h1>Danny Trace Resultaten</h1>
<div class="meta">
  Query: <strong>{args.question}</strong><br>
  Timestamp: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}<br>
  Resultaten: {len(results)} (top-k={args.top_k})
</div>
<table>
<thead>
<tr><th>#</th><th>Distance</th><th>Bron</th><th>Chunk</th><th>Hash</th><th>Tekst</th></tr>
</thead>
<tbody>
{rows_html}
</tbody>
</table>
</body>
</html>"""

        out_file.write_text(html, encoding="utf-8")
        console.print(f"\n[green]HTML export:[/green] {out_file}")


def cmd_benchmark(args):
    """Benchmark embedding providers: snelheid en similarity."""
    import time as _time
    from rich.console import Console
    from rich.table import Table

    console = Console()

    # Test teksten
    test_teksten = [
        "PyTorch met CUDA draait nu op je RTX 3060 Ti voor GPU-versnelde inferentie.",
        "FAISS CPU werkt als fallback wanneer GPU-FAISS niet beschikbaar is.",
        "Embeddings worden berekend op de GPU voor maximale snelheid bij retrieval.",
        "RAG combineert retrieval en LLM-inference om contextuele antwoorden te genereren.",
        "Vector databases slaan hoge-dimensionale embeddings op voor nearest-neighbor search.",
        "Prompt injection is een aanval waarbij kwaadaardige instructies in de input worden verborgen.",
        "Document chunking splitst lange teksten in kleinere stukken voor betere retrieval nauwkeurigheid.",
        "Cosine similarity meet de hoek tussen twee vectoren als maat voor semantische gelijkenis.",
        "TF-IDF weegt termen op basis van hun frequentie in het document versus het gehele corpus.",
        "Sentence transformers produceren dense embeddings die semantische betekenis vastleggen.",
    ]

    if args.extended:
        # Meer teksten voor betrouwbaardere timing
        test_teksten = test_teksten * 5

    similarity_paren = [
        ("GPU versnelling voor machine learning", "CUDA inferentie op een videokaart"),
        ("Hoe werkt RAG?", "retrieval augmented generation pipeline"),
        ("prompt injection aanval", "kwaadaardige input in LLM systemen"),
    ]

    providers = {}

    # --- Hash Embeddings ---
    console.print("\n[cyan]Providers laden...[/cyan]")
    from danny_toolkit.core.embeddings import HashEmbeddings, TFIDFEmbeddings
    providers["Hash (256d)"] = HashEmbeddings(dimensies=256)

    # --- TF-IDF ---
    tfidf = TFIDFEmbeddings(dimensies=512)
    tfidf.fit(test_teksten)
    providers["TF-IDF (512d)"] = tfidf

    # --- TorchGPU ---
    from danny_toolkit.core.embeddings import TorchGPUEmbeddings
    import torch
    torch_emb = TorchGPUEmbeddings()
    providers[f"TorchGPU ({torch_emb.device})"] = torch_emb

    # --- Voyage (optioneel) ---
    if args.voyage:
        from danny_toolkit.core.config import Config
        if Config.has_voyage_key():
            try:
                from danny_toolkit.core.embeddings import VoyageEmbeddings
                providers["Voyage (1024d)"] = VoyageEmbeddings()
            except Exception as e:
                console.print(f"[yellow]Voyage overgeslagen: {e}[/yellow]")

    # === Speed Benchmark ===
    console.print(f"\n[cyan]Speed benchmark ({len(test_teksten)} teksten)...[/cyan]")

    speed_table = Table(title="Embedding Speed Benchmark", border_style="cyan")
    speed_table.add_column("Provider", width=22)
    speed_table.add_column("Teksten", justify="right", width=8)
    speed_table.add_column("Totaal (ms)", justify="right", width=12)
    speed_table.add_column("Per tekst (ms)", justify="right", width=14)
    speed_table.add_column("Teksten/sec", justify="right", width=12)

    embed_cache = {}

    failed_providers = set()

    for naam, prov in providers.items():
        try:
            # Warmup
            prov.embed([test_teksten[0]])

            start = _time.perf_counter()
            result = prov.embed(test_teksten)
            elapsed = _time.perf_counter() - start

            embed_cache[naam] = (prov, result)

            per_tekst = elapsed / len(test_teksten) * 1000
            per_sec = len(test_teksten) / elapsed if elapsed > 0 else 0

            speed_table.add_row(
                naam,
                str(len(test_teksten)),
                f"{elapsed * 1000:.1f}",
                f"{per_tekst:.2f}",
                f"{per_sec:.1f}",
            )
        except Exception as e:
            failed_providers.add(naam)
            err = "rate limit" if "RateLimit" in type(e).__name__ or "429" in str(e) else str(e)[:40]
            speed_table.add_row(naam, "-", "-", "-", f"[red]{err}[/red]")

    console.print(speed_table)

    # === Similarity Benchmark ===
    import math

    def cosine_sim(v1, v2):
        if hasattr(v1, "tolist"):
            v1 = v1.tolist()
        if hasattr(v2, "tolist"):
            v2 = v2.tolist()
        dot = sum(a * b for a, b in zip(v1, v2))
        m1 = math.sqrt(sum(a ** 2 for a in v1))
        m2 = math.sqrt(sum(b ** 2 for b in v2))
        return dot / (m1 * m2) if m1 > 0 and m2 > 0 else 0.0

    console.print(f"\n[cyan]Similarity benchmark ({len(similarity_paren)} paren)...[/cyan]")

    sim_table = Table(title="Cosine Similarity Vergelijking", border_style="cyan")
    sim_table.add_column("Paar", width=50)
    for naam in providers:
        sim_table.add_column(naam, justify="right", width=14)

    for tekst_a, tekst_b in similarity_paren:
        row = [f"{tekst_a[:24]}.. vs {tekst_b[:22]}.."]
        for naam, prov in providers.items():
            if naam in failed_providers:
                row.append("[dim]skipped[/dim]")
                continue
            try:
                va = prov.embed([tekst_a])[0]
                vb = prov.embed([tekst_b])[0]
                sim = cosine_sim(va, vb)
                if sim > 0.7:
                    row.append(f"[green]{sim:.4f}[/green]")
                elif sim > 0.4:
                    row.append(f"[yellow]{sim:.4f}[/yellow]")
                else:
                    row.append(f"[red]{sim:.4f}[/red]")
            except Exception as e:
                err = "rate limit" if "RateLimit" in type(e).__name__ or "429" in str(e) else str(e)[:20]
                row.append(f"[dim]{err}[/dim]")
        sim_table.add_row(*row)

    console.print(sim_table)
    console.print(f"\n[green]Benchmark compleet![/green]")


def cmd_scrape(args):
    """Scrape een website en voeg toe aan de FAISS index."""
    from danny_toolkit.core.web_scraper import scrape_with_depth
    from danny_toolkit.core.embeddings import TorchGPUEmbeddings
    from danny_toolkit.core.index_store import IndexStore

    print(f"=== Danny Scrape: {args.url} (depth={args.depth}) ===")
    chunks = scrape_with_depth(args.url, depth=args.depth, chunk_size=args.chunk_size)

    if not chunks:
        print("Geen content gevonden.")
        sys.exit(1)

    texts = [c["text"] for c in chunks]

    print("Embeddings berekenen...")
    embedder = TorchGPUEmbeddings()
    vectors = embedder.embed(texts).numpy().astype("float32")

    print("FAISS index bijwerken...")
    store = IndexStore()
    store.append(vectors, chunks)

    print(f"\n=== Klaar! {len(chunks)} chunks toegevoegd van {args.url} ===")


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

    # danny index <directory> | danny index --repair | danny index --upgrade
    p_index = sub.add_parser("index", help="Index een directory met documenten")
    p_index.add_argument("directory", nargs="?", default=None, help="Pad naar directory met documenten")
    p_index.add_argument("--chunk-size", type=int, default=500, help="Woorden per chunk")
    p_index.add_argument("--repair", action="store_true", help="Repareer bestaande index: backfill hashes + dedup")
    p_index.add_argument("--upgrade", action="store_true", help="Unified upgrade: schema migratie + repair + rebuild")
    p_index.add_argument("--rebuild", action="store_true", help="Herbereken embeddings voor alle chunks en herbouw FAISS index")

    # danny scrape <url>
    p_scrape = sub.add_parser("scrape", help="Scrape een website en indexeer de content")
    p_scrape.add_argument("url", help="URL om te scrapen")
    p_scrape.add_argument("--depth", type=int, default=0, help="Diepte voor link-crawling (0=alleen die pagina)")
    p_scrape.add_argument("--chunk-size", type=int, default=500, help="Woorden per chunk")

    # danny ask "vraag"
    p_ask = sub.add_parser("ask", help="Stel een vraag aan je geindexeerde docs")
    p_ask.add_argument("question", help="Vraag over je documenten")
    p_ask.add_argument("--top-k", type=int, default=5, help="Aantal bronnen")
    p_ask.add_argument("--model", help="Pad naar GGUF model", default=None)
    p_ask.add_argument("--trace", action="store_true", help="Toon welke chunks gebruikt zijn")

    # danny trace "vraag"
    p_trace = sub.add_parser("trace", help="Trace retrieval resultaten (geen LLM)")
    p_trace.add_argument("question", help="Query om te tracen")
    p_trace.add_argument("--top-k", type=int, default=10, help="Aantal resultaten")
    p_trace.add_argument("--html", action="store_true", help="Exporteer als HTML bestand")

    # danny benchmark
    p_bench = sub.add_parser("benchmark", help="Benchmark embedding providers (snelheid + similarity)")
    p_bench.add_argument("--extended", action="store_true", help="5x meer teksten voor betrouwbaardere timing")
    p_bench.add_argument("--voyage", action="store_true", help="Inclusief Voyage AI (vereist API key)")

    # danny stats
    sub.add_parser("stats", help="Toon index statistieken")

    # danny verify
    sub.add_parser("verify", help="Verifieer index consistentie")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    commands = {
        "gpu": cmd_gpu, "chain": cmd_chain, "cpu": cmd_cpu,
        "index": cmd_index, "scrape": cmd_scrape, "ask": cmd_ask,
        "trace": cmd_trace, "benchmark": cmd_benchmark,
        "stats": cmd_stats, "verify": cmd_verify,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
