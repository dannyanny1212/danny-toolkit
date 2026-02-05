"""
Mini-RAG Systeem - Eenvoudige RAG implementatie.
"""

import json
import math
from pathlib import Path
from collections import Counter

from ..core.config import Config
from ..core.utils import clear_scherm


class MiniRAG:
    """Mini-RAG systeem met lokale embeddings."""

    def __init__(self, documenten_map: Path = None):
        Config.ensure_dirs()
        self.documenten_map = documenten_map or Config.DOCUMENTEN_DIR
        self.documenten = []
        self.index = {}

    def _maak_chunks(self, tekst: str, chunk_grootte: int = 200) -> list:
        """Splitst tekst in kleinere stukjes."""
        woorden = tekst.split()
        chunks = []

        for i in range(0, len(woorden), chunk_grootte // 2):
            chunk = " ".join(woorden[i:i + chunk_grootte])
            if chunk:
                chunks.append(chunk)

        return chunks

    def _maak_embedding(self, tekst: str) -> dict:
        """Maakt een simpele TF embedding."""
        woorden = tekst.lower().split()
        woorden = [w.strip(".,!?:;()[]{}\"'") for w in woorden]
        woorden = [w for w in woorden if len(w) > 2]
        return dict(Counter(woorden))

    def _cosine_similarity(self, vec1: dict, vec2: dict) -> float:
        """Berekent Cosine Similarity."""
        gemeenschappelijk = set(vec1.keys()) & set(vec2.keys())
        dot = sum(vec1[w] * vec2[w] for w in gemeenschappelijk)
        mag1 = math.sqrt(sum(v ** 2 for v in vec1.values()))
        mag2 = math.sqrt(sum(v ** 2 for v in vec2.values()))
        if mag1 == 0 or mag2 == 0:
            return 0.0
        return dot / (mag1 * mag2)

    def indexeer(self):
        """Indexeert alle documenten."""
        print("\n[INDEXEREN] Documenten laden...")

        if not self.documenten_map.exists():
            self.documenten_map.mkdir(parents=True, exist_ok=True)
            print(f"   Map aangemaakt: {self.documenten_map}")
            print("   Plaats .txt bestanden in deze map en herstart.")
            return

        for bestand in self.documenten_map.glob("*.txt"):
            with open(bestand, "r", encoding="utf-8") as f:
                inhoud = f.read()

            doc = {
                "id": len(self.documenten),
                "naam": bestand.name,
                "inhoud": inhoud,
                "chunks": self._maak_chunks(inhoud)
            }
            self.documenten.append(doc)
            print(f"   [OK] {bestand.name} geladen ({len(doc['chunks'])} chunks)")

        # Maak embeddings
        print("\n[INDEXEREN] Embeddings maken...")
        for doc in self.documenten:
            for i, chunk in enumerate(doc["chunks"]):
                chunk_id = f"{doc['id']}_{i}"
                self.index[chunk_id] = {
                    "doc_naam": doc["naam"],
                    "chunk": chunk,
                    "embedding": self._maak_embedding(chunk)
                }

        print(f"   [OK] {len(self.index)} chunks geindexeerd")

    def zoek(self, vraag: str, top_k: int = 3) -> list:
        """Zoekt relevante chunks."""
        query_emb = self._maak_embedding(vraag)
        scores = []

        for chunk_id, data in self.index.items():
            score = self._cosine_similarity(query_emb, data["embedding"])
            if score > 0:
                scores.append({
                    "chunk_id": chunk_id,
                    "doc_naam": data["doc_naam"],
                    "chunk": data["chunk"],
                    "score": score
                })

        scores.sort(key=lambda x: x["score"], reverse=True)
        return scores[:top_k]

    def genereer_antwoord(self, vraag: str, chunks: list) -> str:
        """Genereert een antwoord op basis van gevonden chunks."""
        if not chunks:
            return "Ik kon geen relevante informatie vinden."

        vraag_lower = vraag.lower()
        relevante_info = []

        for chunk in chunks:
            zinnen = chunk["chunk"].split(".")
            for zin in zinnen:
                zin = zin.strip()
                if len(zin) > 20:
                    vraag_woorden = set(vraag_lower.split())
                    zin_woorden = set(zin.lower().split())
                    overlap = vraag_woorden & zin_woorden
                    if len(overlap) >= 2:
                        relevante_info.append(zin)

        if relevante_info:
            antwoord = "Op basis van de documenten:\n\n"
            for info in relevante_info[:5]:
                antwoord += f"- {info}.\n"
            bronnen = set(c["doc_naam"] for c in chunks)
            antwoord += f"\nBronnen: {', '.join(bronnen)}"
        else:
            antwoord = "Relevante context gevonden:\n\n"
            for chunk in chunks[:2]:
                tekst = chunk["chunk"][:200]
                antwoord += f"[{chunk['doc_naam']}]:\n{tekst}...\n\n"

        return antwoord

    def vraag(self, vraag: str) -> str:
        """Beantwoordt een vraag met RAG."""
        print(f"\n[ZOEKEN] \"{vraag}\"")
        chunks = self.zoek(vraag)

        if chunks:
            print(f"   [OK] {len(chunks)} chunks gevonden:")
            for c in chunks:
                print(f"      - {c['doc_naam']} (score: {c['score']:.3f})")

        return self.genereer_antwoord(vraag, chunks)

    def run(self):
        """Start de interactieve Mini-RAG modus."""
        clear_scherm()
        print("\n" + "=" * 50)
        print("   MINI-RAG: Je Eerste RAG Systeem!")
        print("=" * 50)

        self.indexeer()

        if not self.index:
            print("\nGeen documenten gevonden.")
            print(f"Plaats .txt bestanden in: {self.documenten_map}")
            input("\nDruk op Enter...")
            return

        print("\n" + "=" * 50)
        print("VRAAG & ANTWOORD")
        print("=" * 50)
        print("\nStel vragen over de documenten!")
        print("Typ 'stop' om te stoppen.\n")

        while True:
            vraag = input("Vraag: ").strip()

            if vraag.lower() in ["stop", "quit", "exit", "q"]:
                print("\nTot ziens!")
                break

            if not vraag:
                continue

            antwoord = self.vraag(vraag)
            print("\n" + "-" * 50)
            print("ANTWOORD:")
            print("-" * 50)
            print(antwoord)
            print()
