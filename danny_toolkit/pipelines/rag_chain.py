# danny_toolkit/pipelines/rag_chain.py

from danny_toolkit.core.embeddings import TorchGPUEmbeddings
from danny_toolkit.core.faiss_index import FaissIndex
from danny_toolkit.core.gpu import get_device
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

def load_llm(model_name="microsoft/Phi-3-mini-4k-instruct"):
    device = get_device()
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        dtype=torch.float16,
        device_map="auto"
    )
    return tokenizer, model

def generate_answer(tokenizer, model, question, context):
    prompt = (
        "Je bent een behulpzame AI-assistent.\n"
        "Gebruik de context hieronder om de vraag te beantwoorden.\n\n"
        f"Context:\n{context}\n\n"
        f"Vraag: {question}\n"
        "Antwoord:"
    )

    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
    output = model.generate(
        **inputs,
        max_new_tokens=256,
        temperature=0.2,
        top_p=0.9
    )
    return tokenizer.decode(output[0], skip_special_tokens=True)

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
    embedder = TorchGPUEmbeddings()
    doc_vecs = embedder.embed(docs)

    # 3. FAISS index
    index = FaissIndex(dim=doc_vecs.shape[1])
    index.train(doc_vecs)

    # 4. Query
    question = "Hoe werkt GPU versnelling in een RAG pipeline?"
    q_vec = embedder.embed([question])

    # 5. Retrieval
    D, I = index.search(q_vec, k=3)
    retrieved_docs = [docs[idx] for idx in I[0]]

    print("\n=== Retrieved Docs ===")
    for d in retrieved_docs:
        print("-", d)

    # 6. LLM laden
    print("\nLLM laden...")
    tokenizer, model = load_llm()

    # 7. Context bouwen
    context = "\n".join(retrieved_docs)

    # 8. Antwoord genereren
    answer = generate_answer(tokenizer, model, question, context)

    print("\n=== Antwoord ===")
    print(answer)

if __name__ == "__main__":
    run_rag_chain()
