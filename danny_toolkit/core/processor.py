"""
BatchProcessor — De Heavy Lifter van Project Omega.

Verwerkt lijsten met bestanden, past chunking toe
en houdt statistieken bij. Werkt samen met
TheLibrarian voor bestandslezers en ChromaDB opslag.
"""

import logging
import time

from tqdm import tqdm


class BatchProcessor:
    """De Heavy Lifter van Project Omega.

    Verwerkt lijsten met bestanden, past chunking toe
    en houdt statistieken bij.
    """

    def __init__(self, librarian_instance):
        """
        Args:
            librarian_instance: Een instantie van
                TheLibrarian (moet .collection hebben).
        """
        self.lib = librarian_instance
        self.stats = {
            "start_time": 0,
            "end_time": 0,
            "files_processed": 0,
            "files_failed": 0,
            "total_chunks": 0,
            "errors": [],
        }

    # ─── Chunking Strategieën ───

    def _strategy_fixed_size(
        self, text, size=500, overlap=50
    ):
        """Standaard: Woord-gebaseerde chunks."""
        woorden = text.split()
        chunks = []
        for i in range(
            0, len(woorden), size - overlap
        ):
            chunk = " ".join(woorden[i:i + size])
            if len(chunk) > 50:
                chunks.append(chunk)
        return chunks

    def _strategy_paragraph(self, text):
        """Splitsen op witregels
        (artikelen/wetteksten).
        """
        paras = text.split("\n\n")
        return [
            p.strip() for p in paras
            if len(p.strip()) > 50
        ]

    def _strategy_code(self, text):
        """Splitsen op class/def definities."""
        lines = text.split("\n")
        chunks = []
        current_chunk = []

        for line in lines:
            if line.strip().startswith(
                ("def ", "class ", "@")
            ):
                if current_chunk:
                    chunks.append(
                        "\n".join(current_chunk)
                    )
                    current_chunk = []
            current_chunk.append(line)

            # Breek af als chunk te groot wordt
            if len(current_chunk) > 150:
                chunks.append(
                    "\n".join(current_chunk)
                )
                current_chunk = []

        if current_chunk:
            chunks.append("\n".join(current_chunk))
        return chunks

    # ─── Main Process ───

    def process_batch(
        self, files, method="fixed", chunk_size=500
    ):
        """Verwerkt een lijst met bestanden.

        Args:
            files: Lijst met Path objecten.
            method: "fixed", "paragraph" of "code".
            chunk_size: Woorden per chunk (fixed).

        Returns:
            Stats dict.
        """
        self.stats["start_time"] = time.time()
        self.stats["files_processed"] = 0
        self.stats["files_failed"] = 0
        self.stats["total_chunks"] = 0
        self.stats["errors"] = []

        print(
            f"\U0001f680 BatchProcessor gestart:"
            f" {len(files)} bestanden"
            f" via methode '{method}'"
        )

        for file_path in tqdm(
            files, desc="Processing", unit="file"
        ):
            try:
                # 1. Lezen via TheLibrarian
                text = self.lib._lees_bestand(
                    file_path
                )
                if not text:
                    continue

                # 2. Chunking (kies strategie)
                if (
                    method == "code"
                    or file_path.suffix == ".py"
                ):
                    chunks = self._strategy_code(
                        text
                    )
                elif method == "paragraph":
                    chunks = self._strategy_paragraph(
                        text
                    )
                else:
                    chunks = self._strategy_fixed_size(
                        text, size=chunk_size
                    )

                if not chunks:
                    continue

                # 3. Opslaan in ChromaDB
                ids = [
                    f"{file_path.name}_{i}"
                    for i in range(len(chunks))
                ]
                metadatas = [
                    {
                        "bron": file_path.name,
                        "pad": str(file_path),
                        "chunk_method": method,
                        "type": (
                            "code"
                            if method == "code"
                            else "text"
                        ),
                    }
                    for _ in chunks
                ]

                self.lib.collection.upsert(
                    ids=ids,
                    documents=chunks,
                    metadatas=metadatas,
                )

                # 4. Stats update
                self.stats["files_processed"] += 1
                self.stats["total_chunks"] += (
                    len(chunks)
                )

            except Exception as e:
                self.stats["files_failed"] += 1
                error_msg = (
                    f"Fout bij {file_path.name}:"
                    f" {e}"
                )
                self.stats["errors"].append(
                    error_msg
                )
                logging.error(error_msg)

        self.stats["end_time"] = time.time()
        return self.stats

    def print_report(self):
        """Print een samenvatting."""
        duration = (
            self.stats["end_time"]
            - self.stats["start_time"]
        )
        print(
            "\n\U0001f4ca BATCH RAPPORT"
        )
        print(
            f"\u23f1\ufe0f  Duur:        "
            f"{duration:.2f}s"
        )
        print(
            f"\u2705 Verwerkt:    "
            f"{self.stats['files_processed']}"
        )
        print(
            f"\u274c Mislukt:     "
            f"{self.stats['files_failed']}"
        )
        print(
            f"\U0001f4da Totaal Chunks:"
            f" {self.stats['total_chunks']}"
        )

        if self.stats["errors"]:
            print("\n\u26a0\ufe0f Fouten:")
            for err in self.stats["errors"][:5]:
                print(f"  - {err}")


__all__ = ["BatchProcessor"]
