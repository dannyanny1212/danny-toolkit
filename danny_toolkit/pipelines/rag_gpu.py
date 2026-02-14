# danny_toolkit/pipelines/rag_gpu.py

from danny_toolkit.core.embeddings import TorchGPUEmbeddings
from danny_toolkit.core.faiss_index import FaissIndex

def run_demo():
    print("=== GPU-RAG Pipeline Demo ===")

    # 1. Documenten
    docs = [
        "PyTorch met CUDA draait nu op je RTX 3060 Ti.",
        "FAISS CPU werkt als fallback wanneer GPU-FAISS niet beschikbaar is.",
        "Dit is een testdocument voor retrieval.",
        "Embeddings worden berekend op de GPU voor maximale snelheid.",
    ]

    # 2. Embeddings (GPU)
    embedder = TorchGPUEmbeddings()
    doc_vecs = embedder.embed(docs)

    print(f"Embeddings shape: {doc_vecs.shape}")
    print("Building FAISS index...")

    # 3. FAISS index (CPU fallback)
    index = FaissIndex(dim=doc_vecs.shape[1])
    index.train(doc_vecs)

    # 4. Query
    query = "hoe werkt GPU versnelling in RAG?"
    q_vec = embedder.embed([query])

    # 5. Retrieval
    D, I = index.search(q_vec, k=3)

    print("\n=== Retrieval Results ===")
    for rank, idx in enumerate(I[0]):
        print(f"{rank+1}. {docs[idx]}  (distance={D[0][rank]:.4f})")

if __name__ == "__main__":
    run_demo()
