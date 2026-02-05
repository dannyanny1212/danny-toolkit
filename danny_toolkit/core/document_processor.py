"""
Document processor voor RAG systemen.
"""

from pathlib import Path
from .config import Config


class DocumentProcessor:
    """Verwerkt documenten tot chunks voor RAG."""

    def __init__(self, chunk_size: int = None, overlap: int = None):
        self.chunk_size = chunk_size or Config.CHUNK_SIZE
        self.overlap = overlap or Config.CHUNK_OVERLAP

    def laad_bestand(self, pad: Path) -> str:
        """Laad tekst uit bestand."""
        with open(pad, "r", encoding="utf-8") as f:
            return f.read()

    def chunk_tekst(self, tekst: str, doc_id: str) -> list:
        """Split tekst in overlappende chunks."""
        chunks = []
        start = 0
        chunk_nr = 0

        while start < len(tekst):
            eind = start + self.chunk_size
            chunk = tekst[start:eind]

            # Probeer op zin-grens te eindigen
            if eind < len(tekst):
                laatste_punt = chunk.rfind(". ")
                if laatste_punt > self.chunk_size // 2:
                    chunk = chunk[:laatste_punt + 1]
                    eind = start + laatste_punt + 1

            if chunk.strip():
                chunks.append({
                    "id": f"{doc_id}_chunk_{chunk_nr}",
                    "tekst": chunk.strip(),
                    "metadata": {
                        "bron": doc_id,
                        "chunk_nr": chunk_nr
                    }
                })
                chunk_nr += 1

            start = eind - self.overlap

        return chunks

    def verwerk_map(self, map_pad: Path) -> list:
        """Verwerk alle .txt bestanden in een map."""
        alle_chunks = []

        for bestand in map_pad.glob("*.txt"):
            print(f"   [DOC] {bestand.name}")
            tekst = self.laad_bestand(bestand)
            chunks = self.chunk_tekst(tekst, bestand.stem)
            alle_chunks.extend(chunks)
            print(f"      -> {len(chunks)} chunks")

        return alle_chunks
