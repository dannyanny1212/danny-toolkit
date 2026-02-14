# danny_toolkit/rag_gui.py — RAG Desktop App (Tkinter)
"""
Danny Toolkit RAG GUI — GPU Inference & Document Search.

Knoppen: GPU Inference, RAG Chain, Index Documenten, Ask
Tekstvak voor vragen, output-venster, directory-picker.

Entry point: danny-rag
"""

import os
import sys
import threading
import tkinter as tk
from tkinter import filedialog, scrolledtext

# ── Donker thema ──
BG = "#0d1117"
BG_HEADER = "#161b22"
BG_INPUT = "#1c2128"
BG_OUTPUT = "#161b22"
BG_KNOP = "#21262d"
BG_KNOP_HOVER = "#30363d"
FG = "#c9d1d9"
FG_DIM = "#8b949e"
FG_BLAUW = "#58a6ff"
FG_GROEN = "#3fb950"
FG_ORANJE = "#d29922"
FG_PAARS = "#d55fde"
FG_ROOD = "#f85149"

CUDA_BIN = r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.1\bin"


class RagGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Danny Toolkit — RAG Desktop")
        self.root.configure(bg=BG)
        self.root.geometry("900x700")
        self.root.minsize(700, 500)
        self.running = False

        self._ensure_cuda_path()
        self._bouw_header()
        self._bouw_input_sectie()
        self._bouw_knoppen()
        self._bouw_output()
        self._bouw_statusbalk()

    def _ensure_cuda_path(self):
        if CUDA_BIN not in os.environ.get("PATH", ""):
            os.environ["PATH"] = CUDA_BIN + os.pathsep + os.environ.get("PATH", "")

    # ══════════════════════════════════════════
    # HEADER
    # ══════════════════════════════════════════
    def _bouw_header(self):
        header = tk.Frame(self.root, bg=BG_HEADER, pady=12)
        header.pack(fill="x")

        tk.Label(
            header,
            text="DANNY TOOLKIT — RAG DESKTOP",
            font=("Consolas", 18, "bold"),
            fg=FG_BLAUW, bg=BG_HEADER,
        ).pack()

        tk.Label(
            header,
            text="GPU Inference  |  RAG Chain  |  Document Search  |  Phi-3 GGUF + FAISS",
            font=("Consolas", 10),
            fg=FG_DIM, bg=BG_HEADER,
        ).pack(pady=(4, 0))

    # ══════════════════════════════════════════
    # INPUT SECTIE
    # ══════════════════════════════════════════
    def _bouw_input_sectie(self):
        frame = tk.Frame(self.root, bg=BG, pady=8)
        frame.pack(fill="x", padx=16)

        # Directory picker
        dir_frame = tk.Frame(frame, bg=BG)
        dir_frame.pack(fill="x", pady=(0, 8))

        tk.Label(
            dir_frame, text="Document directory:",
            font=("Consolas", 10), fg=FG_DIM, bg=BG, anchor="w",
        ).pack(side="left")

        self.dir_var = tk.StringVar(value="C:/docs/")
        self.dir_entry = tk.Entry(
            dir_frame, textvariable=self.dir_var,
            font=("Consolas", 11), fg=FG, bg=BG_INPUT,
            insertbackground=FG, bd=0, relief="flat",
        )
        self.dir_entry.pack(side="left", fill="x", expand=True, padx=(8, 4))

        browse_btn = tk.Button(
            dir_frame, text="Browse...",
            font=("Consolas", 9), fg=FG_DIM, bg=BG_KNOP,
            activeforeground=FG, activebackground=BG_KNOP_HOVER,
            bd=0, cursor="hand2", padx=8,
            command=self._browse_directory,
        )
        browse_btn.pack(side="right")

        # Vraag input
        tk.Label(
            frame, text="Vraag / Query:",
            font=("Consolas", 10), fg=FG_DIM, bg=BG, anchor="w",
        ).pack(fill="x")

        input_frame = tk.Frame(frame, bg=BG_INPUT, bd=1, relief="solid")
        input_frame.pack(fill="x", pady=(4, 0))

        self.vraag_entry = tk.Entry(
            input_frame,
            font=("Consolas", 13), fg=FG, bg=BG_INPUT,
            insertbackground=FG_BLAUW, bd=0, relief="flat",
        )
        self.vraag_entry.pack(fill="x", padx=8, pady=8)
        self.vraag_entry.insert(0, "Wat staat er in mijn documenten?")
        self.vraag_entry.bind("<Return>", lambda e: self._run_ask())

    # ══════════════════════════════════════════
    # KNOPPEN
    # ══════════════════════════════════════════
    def _bouw_knoppen(self):
        frame = tk.Frame(self.root, bg=BG, pady=8)
        frame.pack(fill="x", padx=16)

        knoppen_config = [
            ("GPU Inference", FG_GROEN, self._run_gpu),
            ("RAG Chain", FG_PAARS, self._run_chain),
            ("Index Documenten", FG_ORANJE, self._run_index),
            ("Ask", FG_BLAUW, self._run_ask),
        ]

        for i, (tekst, kleur, cmd) in enumerate(knoppen_config):
            btn = tk.Button(
                frame, text=tekst,
                font=("Consolas", 12, "bold"),
                fg=kleur, bg=BG_KNOP,
                activeforeground="#ffffff",
                activebackground=BG_KNOP_HOVER,
                bd=0, relief="flat", cursor="hand2",
                padx=16, pady=10,
                command=cmd,
            )
            btn.pack(side="left", fill="x", expand=True, padx=4)

            btn.bind("<Enter>", lambda e, b=btn: b.configure(bg=BG_KNOP_HOVER))
            btn.bind("<Leave>", lambda e, b=btn: b.configure(bg=BG_KNOP))

    # ══════════════════════════════════════════
    # OUTPUT VENSTER
    # ══════════════════════════════════════════
    def _bouw_output(self):
        frame = tk.Frame(self.root, bg=BG, pady=4)
        frame.pack(fill="both", expand=True, padx=16)

        tk.Label(
            frame, text="Output:",
            font=("Consolas", 10), fg=FG_DIM, bg=BG, anchor="w",
        ).pack(fill="x")

        self.output = scrolledtext.ScrolledText(
            frame,
            font=("Consolas", 11),
            fg=FG, bg=BG_OUTPUT,
            insertbackground=FG,
            bd=1, relief="solid",
            wrap="word", state="disabled",
        )
        self.output.pack(fill="both", expand=True, pady=(4, 0))

        # Tags voor kleuren
        self.output.tag_configure("info", foreground=FG_BLAUW)
        self.output.tag_configure("success", foreground=FG_GROEN)
        self.output.tag_configure("warn", foreground=FG_ORANJE)
        self.output.tag_configure("error", foreground=FG_ROOD)
        self.output.tag_configure("header", foreground=FG_PAARS, font=("Consolas", 12, "bold"))

    # ══════════════════════════════════════════
    # STATUSBALK
    # ══════════════════════════════════════════
    def _bouw_statusbalk(self):
        balk = tk.Frame(self.root, bg=BG_HEADER, pady=6)
        balk.pack(fill="x", side="bottom")

        self.status_var = tk.StringVar(value="Gereed")
        tk.Label(
            balk, textvariable=self.status_var,
            font=("Consolas", 9), fg=FG_DIM, bg=BG_HEADER, anchor="w",
        ).pack(side="left", padx=12)

        tk.Label(
            balk, text="Phi-3 GGUF + FAISS + CUDA 12.1",
            font=("Consolas", 9, "bold"), fg=FG_BLAUW, bg=BG_HEADER,
        ).pack(side="right", padx=12)

    # ══════════════════════════════════════════
    # OUTPUT HELPERS
    # ══════════════════════════════════════════
    def _print(self, tekst, tag=None):
        self.output.configure(state="normal")
        if tag:
            self.output.insert("end", tekst + "\n", tag)
        else:
            self.output.insert("end", tekst + "\n")
        self.output.see("end")
        self.output.configure(state="disabled")

    def _clear_output(self):
        self.output.configure(state="normal")
        self.output.delete("1.0", "end")
        self.output.configure(state="disabled")

    def _set_status(self, tekst):
        self.status_var.set(tekst)

    def _browse_directory(self):
        d = filedialog.askdirectory(initialdir=self.dir_var.get())
        if d:
            self.dir_var.set(d)

    def _get_vraag(self):
        return self.vraag_entry.get().strip()

    # ══════════════════════════════════════════
    # THREADED RUNNER
    # ══════════════════════════════════════════
    def _run_threaded(self, naam, func):
        if self.running:
            self._print("Er draait al een taak. Wacht tot deze klaar is.", "warn")
            return
        self.running = True
        self._clear_output()
        self._print(f"=== {naam} ===", "header")
        self._set_status(f"Bezig: {naam}...")

        def worker():
            try:
                func()
                self.root.after(0, lambda: self._print(f"\nKlaar!", "success"))
                self.root.after(0, lambda: self._set_status("Gereed"))
            except Exception as e:
                self.root.after(0, lambda: self._print(f"\nFout: {e}", "error"))
                self.root.after(0, lambda: self._set_status(f"Fout: {e}"))
            finally:
                self.running = False

        t = threading.Thread(target=worker, daemon=True)
        t.start()

    # ══════════════════════════════════════════
    # GPU INFERENCE
    # ══════════════════════════════════════════
    def _run_gpu(self):
        vraag = self._get_vraag()
        if not vraag:
            self._print("Voer een vraag in.", "warn")
            return

        def work():
            self.root.after(0, lambda: self._print("Model laden: Phi-3 GGUF...", "info"))
            from llama_cpp import Llama

            model_path = r"C:\models\phi3.Q4_K_M.gguf"
            llm = Llama(model_path=model_path, n_gpu_layers=-1, n_ctx=4096, verbose=False)

            self.root.after(0, lambda: self._print("Genereren...\n", "info"))

            prompt = f"<|user|>\n{vraag}\n<|end|>\n<|assistant|>\n"
            output = llm(prompt, max_tokens=512, temperature=0.2, top_p=0.9)
            antwoord = output["choices"][0]["text"].strip()

            self.root.after(0, lambda: self._print(antwoord))

        self._run_threaded("GPU Inference", work)

    # ══════════════════════════════════════════
    # RAG CHAIN
    # ══════════════════════════════════════════
    def _run_chain(self):
        vraag = self._get_vraag()
        if not vraag:
            self._print("Voer een vraag in.", "warn")
            return

        def work():
            self.root.after(0, lambda: self._print("Embeddings laden...", "info"))
            from danny_toolkit.core.embeddings import TorchGPUEmbeddings
            from danny_toolkit.core.faiss_index import FaissIndex
            from danny_toolkit.pipelines.rag_chain import load_llm, generate_answer

            docs = [
                "PyTorch met CUDA draait nu op je RTX 3060 Ti.",
                "FAISS CPU werkt als fallback wanneer GPU-FAISS niet beschikbaar is.",
                "Embeddings worden berekend op de GPU voor maximale snelheid.",
                "RAG combineert retrieval en LLM-inference om contextuele antwoorden te genereren.",
            ]

            embedder = TorchGPUEmbeddings()
            doc_vecs = embedder.embed(docs)

            self.root.after(0, lambda: self._print("FAISS index bouwen...", "info"))
            index = FaissIndex(dim=doc_vecs.shape[1])
            index.train(doc_vecs)

            q_vec = embedder.embed([vraag])
            D, I = index.search(q_vec, k=3)
            retrieved = [docs[idx] for idx in I[0]]

            self.root.after(0, lambda: self._print("\nRetrieved docs:", "info"))
            for d in retrieved:
                self.root.after(0, lambda d=d: self._print(f"  - {d}"))

            self.root.after(0, lambda: self._print("\nLLM laden...", "info"))
            tokenizer, model = load_llm()
            context = "\n".join(retrieved)
            answer = generate_answer(tokenizer, model, vraag, context)

            self.root.after(0, lambda: self._print(f"\n{answer}"))

        self._run_threaded("RAG Chain", work)

    # ══════════════════════════════════════════
    # INDEX DOCUMENTEN
    # ══════════════════════════════════════════
    def _run_index(self):
        directory = self.dir_var.get().strip()
        if not directory:
            self._print("Selecteer een directory.", "warn")
            return

        def work():
            self.root.after(0, lambda: self._print(f"Directory: {directory}", "info"))
            from danny_toolkit.core.doc_loader import load_directory
            from danny_toolkit.core.embeddings import TorchGPUEmbeddings
            from danny_toolkit.core.index_store import IndexStore

            chunks = load_directory(directory)
            if not chunks:
                self.root.after(0, lambda: self._print("Geen documenten gevonden.", "warn"))
                return

            self.root.after(0, lambda: self._print(
                f"{len(chunks)} chunks gevonden", "info"))

            texts = [c["text"] for c in chunks]
            bronnen = set(os.path.basename(c["source"]) for c in chunks)
            for b in sorted(bronnen):
                self.root.after(0, lambda b=b: self._print(f"  - {b}"))

            self.root.after(0, lambda: self._print("\nEmbeddings berekenen...", "info"))
            embedder = TorchGPUEmbeddings()
            vectors = embedder.embed(texts).numpy().astype("float32")

            self.root.after(0, lambda: self._print("FAISS index bouwen...", "info"))
            store = IndexStore()
            store.build(vectors, chunks)

            self.root.after(0, lambda: self._print(
                f"\n{len(chunks)} chunks geindexeerd!", "success"))

        self._run_threaded("Index Documenten", work)

    # ══════════════════════════════════════════
    # ASK
    # ══════════════════════════════════════════
    def _run_ask(self):
        vraag = self._get_vraag()
        if not vraag:
            self._print("Voer een vraag in.", "warn")
            return

        def work():
            from danny_toolkit.core.embeddings import TorchGPUEmbeddings
            from danny_toolkit.core.index_store import IndexStore
            from llama_cpp import Llama

            store = IndexStore()
            if not store.exists():
                self.root.after(0, lambda: self._print(
                    "Geen index gevonden. Klik eerst 'Index Documenten'.", "error"))
                return

            self.root.after(0, lambda: self._print("Query embedden...", "info"))
            embedder = TorchGPUEmbeddings()
            q_vec = embedder.embed([vraag]).numpy().astype("float32")

            results = store.search(q_vec, k=5)

            self.root.after(0, lambda: self._print(f"\nTop {len(results)} bronnen:", "info"))
            for r in results:
                src = os.path.basename(r["source"])
                self.root.after(0, lambda r=r, s=src: self._print(
                    f"  {r['rank']}. [{s}] {r['text'][:100]}..."))

            context = "\n\n".join(r["text"] for r in results)

            self.root.after(0, lambda: self._print("\nPhi-3 GGUF laden...", "info"))
            model_path = r"C:\models\phi3.Q4_K_M.gguf"
            llm = Llama(model_path=model_path, n_gpu_layers=-1, n_ctx=4096, verbose=False)

            prompt = (
                f"<|user|>\n"
                f"Gebruik de context hieronder om de vraag te beantwoorden.\n\n"
                f"Context:\n{context}\n\n"
                f"Vraag: {vraag}\n"
                f"<|end|>\n<|assistant|>\n"
            )
            output = llm(prompt, max_tokens=512, temperature=0.2, top_p=0.9)
            antwoord = output["choices"][0]["text"].strip()

            self.root.after(0, lambda: self._print(f"\n{'='*50}", "header"))
            self.root.after(0, lambda: self._print(antwoord))

        self._run_threaded("Ask — Document RAG", work)

    # ══════════════════════════════════════════
    # RUN
    # ══════════════════════════════════════════
    def run(self):
        self.root.mainloop()


def main():
    app = RagGUI()
    app.run()


if __name__ == "__main__":
    main()
