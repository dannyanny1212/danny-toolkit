"""
Document processor voor RAG systemen.
Versie 2.0 - Met PDF/Markdown support en metadata extractie.
"""

import logging
import re
from pathlib import Path
from datetime import datetime
from typing import List, Dict
from .config import Config

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """Verwerkt documenten tot chunks voor RAG."""

    ONDERSTEUNDE_EXTENSIES = {
        ".txt": "tekst",
        ".md": "markdown",
        ".py": "python",
        ".js": "javascript",
        ".json": "json",
        ".csv": "csv",
        ".html": "html",
        ".xml": "xml",
        ".pdf": "pdf"
    }

    def __init__(self, chunk_size: int = None, overlap: int = None):
        self.chunk_size = chunk_size or Config.CHUNK_SIZE
        self.overlap = overlap or Config.CHUNK_OVERLAP

    def laad_bestand(self, pad: Path) -> str:
        """Laad tekst uit bestand."""
        extensie = pad.suffix.lower()

        if extensie == ".pdf":
            return self._laad_pdf(pad)

        with open(pad, "r", encoding="utf-8") as f:
            return f.read()

    def _laad_pdf(self, pad: Path) -> str:
        """Laad tekst uit PDF bestand."""
        try:
            import pypdf
            tekst_delen = []

            with open(pad, "rb") as f:
                reader = pypdf.PdfReader(f)
                for pagina in reader.pages:
                    tekst = pagina.extract_text()
                    if tekst:
                        tekst_delen.append(tekst)

            return "\n\n".join(tekst_delen)

        except ImportError:
            print("   [!] pypdf niet geinstalleerd. Installeer met: pip install pypdf")
            return ""
        except Exception as e:
            print(f"   [!] PDF laden mislukt: {e}")
            return ""

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
        """Verwerk alle ondersteunde bestanden in een map."""
        alle_chunks = []

        for extensie in self.ONDERSTEUNDE_EXTENSIES:
            for bestand in map_pad.glob(f"*{extensie}"):
                print(f"   [DOC] {bestand.name}")
                tekst = self.laad_bestand(bestand)
                if tekst:
                    chunks = self.chunk_tekst(tekst, bestand.stem)
                    alle_chunks.extend(chunks)
                    print(f"      -> {len(chunks)} chunks")

        return alle_chunks

    # =========================================================================
    # MARKDOWN PROCESSING
    # =========================================================================

    def parse_markdown(self, tekst: str) -> Dict:
        """
        Parse markdown naar structuur.

        Returns:
            Dict met secties, headers, links, etc.
        """
        resultaat = {
            "headers": [],
            "secties": [],
            "links": [],
            "code_blokken": [],
            "lijsten": [],
            "metadata": {}
        }

        lijnen = tekst.split("\n")
        huidige_sectie = {"header": None, "niveau": 0, "inhoud": []}

        for lijn in lijnen:
            # Headers
            header_match = re.match(r"^(#{1,6})\s+(.+)$", lijn)
            if header_match:
                # Sla vorige sectie op
                if huidige_sectie["inhoud"]:
                    resultaat["secties"].append({
                        "header": huidige_sectie["header"],
                        "niveau": huidige_sectie["niveau"],
                        "tekst": "\n".join(huidige_sectie["inhoud"])
                    })

                niveau = len(header_match.group(1))
                header_tekst = header_match.group(2)
                resultaat["headers"].append({
                    "niveau": niveau,
                    "tekst": header_tekst
                })
                huidige_sectie = {
                    "header": header_tekst,
                    "niveau": niveau,
                    "inhoud": []
                }
                continue

            # Links
            links = re.findall(r"\[([^\]]+)\]\(([^)]+)\)", lijn)
            for link_tekst, url in links:
                resultaat["links"].append({
                    "tekst": link_tekst,
                    "url": url
                })

            huidige_sectie["inhoud"].append(lijn)

        # Laatste sectie
        if huidige_sectie["inhoud"]:
            resultaat["secties"].append({
                "header": huidige_sectie["header"],
                "niveau": huidige_sectie["niveau"],
                "tekst": "\n".join(huidige_sectie["inhoud"])
            })

        # Code blokken
        code_matches = re.findall(r"```(\w*)\n(.*?)```", tekst, re.DOTALL)
        for taal, code in code_matches:
            resultaat["code_blokken"].append({
                "taal": taal or "tekst",
                "code": code.strip()
            })

        return resultaat

    def chunk_markdown(self, tekst: str, doc_id: str) -> list:
        """
        Chunk markdown op basis van headers.

        Slimmer dan gewone chunking - behoudt sectie context.
        """
        parsed = self.parse_markdown(tekst)
        chunks = []

        for i, sectie in enumerate(parsed["secties"]):
            sectie_tekst = sectie["tekst"].strip()
            if not sectie_tekst:
                continue

            # Als sectie te groot is, chunk verder
            if len(sectie_tekst) > self.chunk_size:
                sub_chunks = self.chunk_tekst(sectie_tekst, f"{doc_id}_s{i}")
                for sub in sub_chunks:
                    sub["metadata"]["sectie"] = sectie["header"]
                    sub["metadata"]["sectie_niveau"] = sectie["niveau"]
                chunks.extend(sub_chunks)
            else:
                chunks.append({
                    "id": f"{doc_id}_sectie_{i}",
                    "tekst": sectie_tekst,
                    "metadata": {
                        "bron": doc_id,
                        "sectie": sectie["header"],
                        "sectie_niveau": sectie["niveau"],
                        "chunk_nr": i
                    }
                })

        return chunks

    # =========================================================================
    # METADATA EXTRACTIE
    # =========================================================================

    def extraheer_metadata(self, pad: Path) -> Dict:
        """
        Extraheer metadata uit bestand.

        Returns:
            Dict met bestandsinfo en geëxtraheerde metadata
        """
        metadata = {
            "bestandsnaam": pad.name,
            "extensie": pad.suffix.lower(),
            "type": self.ONDERSTEUNDE_EXTENSIES.get(pad.suffix.lower(), "onbekend"),
            "grootte_bytes": 0,
            "aangemaakt": None,
            "gewijzigd": None
        }

        try:
            stat = pad.stat()
            metadata["grootte_bytes"] = stat.st_size
            metadata["gewijzigd"] = datetime.fromtimestamp(stat.st_mtime).isoformat()

            # Windows heeft geen st_birthtime altijd
            try:
                metadata["aangemaakt"] = datetime.fromtimestamp(
                    stat.st_birthtime
                ).isoformat()
            except AttributeError:
                metadata["aangemaakt"] = metadata["gewijzigd"]

        except OSError:
            pass

        # Type-specifieke metadata
        if pad.suffix.lower() == ".md":
            metadata.update(self._extraheer_markdown_metadata(pad))
        elif pad.suffix.lower() == ".py":
            metadata.update(self._extraheer_python_metadata(pad))
        elif pad.suffix.lower() == ".pdf":
            metadata.update(self._extraheer_pdf_metadata(pad))

        return metadata

    def _extraheer_markdown_metadata(self, pad: Path) -> Dict:
        """Extraheer metadata uit markdown bestand."""
        metadata = {}

        try:
            with open(pad, "r", encoding="utf-8") as f:
                inhoud = f.read()

            # YAML frontmatter
            frontmatter_match = re.match(r"^---\s*\n(.*?)\n---", inhoud, re.DOTALL)
            if frontmatter_match:
                for lijn in frontmatter_match.group(1).split("\n"):
                    if ":" in lijn:
                        key, value = lijn.split(":", 1)
                        metadata[f"fm_{key.strip()}"] = value.strip()

            # Tel headers, links, woorden
            parsed = self.parse_markdown(inhoud)
            metadata["aantal_headers"] = len(parsed["headers"])
            metadata["aantal_links"] = len(parsed["links"])
            metadata["aantal_code_blokken"] = len(parsed["code_blokken"])
            metadata["aantal_woorden"] = len(inhoud.split())

        except Exception as e:
            logger.debug("Markdown metadata extractie mislukt: %s", e)

        return metadata

    def _extraheer_python_metadata(self, pad: Path) -> Dict:
        """Extraheer metadata uit Python bestand."""
        metadata = {}

        try:
            with open(pad, "r", encoding="utf-8") as f:
                inhoud = f.read()

            # Docstring
            docstring_match = re.match(r'^"""(.*?)"""', inhoud, re.DOTALL)
            if not docstring_match:
                docstring_match = re.match(r"^'''(.*?)'''", inhoud, re.DOTALL)

            if docstring_match:
                metadata["module_docstring"] = docstring_match.group(1).strip()[:200]

            # Tel functies en classes
            metadata["aantal_functies"] = len(re.findall(r"^def \w+", inhoud, re.M))
            metadata["aantal_classes"] = len(re.findall(r"^class \w+", inhoud, re.M))
            metadata["aantal_imports"] = len(re.findall(r"^(?:import|from)", inhoud, re.M))
            metadata["aantal_regels"] = inhoud.count("\n") + 1

        except Exception as e:
            logger.debug("Python metadata extractie mislukt: %s", e)

        return metadata

    def _extraheer_pdf_metadata(self, pad: Path) -> Dict:
        """Extraheer metadata uit PDF bestand."""
        metadata = {}

        try:
            import pypdf
            with open(pad, "rb") as f:
                reader = pypdf.PdfReader(f)
                metadata["aantal_paginas"] = len(reader.pages)

                if reader.metadata:
                    if reader.metadata.title:
                        metadata["pdf_titel"] = reader.metadata.title
                    if reader.metadata.author:
                        metadata["pdf_auteur"] = reader.metadata.author
                    if reader.metadata.subject:
                        metadata["pdf_onderwerp"] = reader.metadata.subject

        except ImportError:
            pass
        except Exception as e:
            logger.debug("PDF metadata extractie mislukt: %s", e)

        return metadata

    # =========================================================================
    # SLIMME CHUNKING STRATEGIEEN
    # =========================================================================

    def chunk_op_paragrafen(self, tekst: str, doc_id: str,
                            min_lengte: int = 100) -> list:
        """
        Chunk tekst op basis van paragrafen.

        Behoudt natuurlijke tekststructuur.
        """
        chunks = []
        paragrafen = tekst.split("\n\n")

        huidige_chunk = ""
        chunk_nr = 0

        for para in paragrafen:
            para = para.strip()
            if not para:
                continue

            # Als toevoegen binnen limiet blijft
            if len(huidige_chunk) + len(para) + 2 <= self.chunk_size:
                huidige_chunk += ("\n\n" if huidige_chunk else "") + para
            else:
                # Sla huidige chunk op als groot genoeg
                if len(huidige_chunk) >= min_lengte:
                    chunks.append({
                        "id": f"{doc_id}_para_{chunk_nr}",
                        "tekst": huidige_chunk,
                        "metadata": {
                            "bron": doc_id,
                            "chunk_nr": chunk_nr,
                            "methode": "paragraaf"
                        }
                    })
                    chunk_nr += 1

                # Start nieuwe chunk met huidige paragraaf
                if len(para) > self.chunk_size:
                    # Paragraaf te groot, normale chunking
                    sub_chunks = self.chunk_tekst(para, f"{doc_id}_para_{chunk_nr}")
                    chunks.extend(sub_chunks)
                    chunk_nr += len(sub_chunks)
                    huidige_chunk = ""
                else:
                    huidige_chunk = para

        # Laatste chunk
        if len(huidige_chunk) >= min_lengte:
            chunks.append({
                "id": f"{doc_id}_para_{chunk_nr}",
                "tekst": huidige_chunk,
                "metadata": {
                    "bron": doc_id,
                    "chunk_nr": chunk_nr,
                    "methode": "paragraaf"
                }
            })

        return chunks

    def chunk_op_zinnen(self, tekst: str, doc_id: str,
                        zinnen_per_chunk: int = 5) -> list:
        """
        Chunk tekst op basis van zinnen.

        Handig voor precieze retrieval.
        """
        # Simpele zin-splitsing
        zinnen = re.split(r"(?<=[.!?])\s+", tekst)
        chunks = []
        chunk_nr = 0

        for i in range(0, len(zinnen), zinnen_per_chunk):
            chunk_zinnen = zinnen[i:i + zinnen_per_chunk]
            chunk_tekst = " ".join(chunk_zinnen).strip()

            if chunk_tekst:
                chunks.append({
                    "id": f"{doc_id}_zin_{chunk_nr}",
                    "tekst": chunk_tekst,
                    "metadata": {
                        "bron": doc_id,
                        "chunk_nr": chunk_nr,
                        "methode": "zinnen",
                        "zinnen_bereik": f"{i}-{min(i+zinnen_per_chunk, len(zinnen))}"
                    }
                })
                chunk_nr += 1

        return chunks

    def chunk_semantisch(self, tekst: str, doc_id: str) -> list:
        """
        Semantische chunking - probeert betekenisvolle eenheden te behouden.

        Combineert meerdere heuristieken.
        """
        # Detecteer type content
        is_code = tekst.count("def ") > 3 or tekst.count("function") > 3
        is_markdown = tekst.count("#") > 5 or tekst.count("```") > 0
        is_lijst = tekst.count("\n- ") > 10 or tekst.count("\n* ") > 10

        if is_code:
            # Voor code: chunk op functies/classes
            return self._chunk_code(tekst, doc_id)
        elif is_markdown:
            return self.chunk_markdown(tekst, doc_id)
        elif is_lijst:
            return self.chunk_op_paragrafen(tekst, doc_id)
        else:
            # Default: paragraaf-gebaseerd met fallback naar overlap
            chunks = self.chunk_op_paragrafen(tekst, doc_id)
            if not chunks:
                chunks = self.chunk_tekst(tekst, doc_id)
            return chunks

    def _chunk_code(self, tekst: str, doc_id: str) -> list:
        """Chunk code op basis van functies en classes."""
        chunks = []
        chunk_nr = 0

        # Match Python functies en classes
        pattern = r"((?:^class |^def |^async def ).+?(?=\n(?:class |def |async def )|\Z))"
        matches = re.findall(pattern, tekst, re.MULTILINE | re.DOTALL)

        for match in matches:
            match = match.strip()
            if len(match) > 50:  # Filter kleine stukken
                # Bepaal type
                if match.startswith("class "):
                    chunk_type = "class"
                elif match.startswith("async def "):
                    chunk_type = "async_functie"
                else:
                    chunk_type = "functie"

                # Haal naam
                naam_match = re.match(r"(?:class|async def|def)\s+(\w+)", match)
                naam = naam_match.group(1) if naam_match else "onbekend"

                chunks.append({
                    "id": f"{doc_id}_code_{chunk_nr}",
                    "tekst": match,
                    "metadata": {
                        "bron": doc_id,
                        "chunk_nr": chunk_nr,
                        "methode": "code",
                        "code_type": chunk_type,
                        "naam": naam
                    }
                })
                chunk_nr += 1

        # Als geen matches, fall back naar normale chunking
        if not chunks:
            chunks = self.chunk_tekst(tekst, doc_id)

        return chunks


class BatchProcessor:
    """Verwerk meerdere documenten in batch."""

    def __init__(self, processor: DocumentProcessor = None):
        self.processor = processor or DocumentProcessor()
        self.statistieken = {
            "verwerkt": 0,
            "mislukt": 0,
            "totaal_chunks": 0
        }

    def verwerk_bestanden(self, paden: List[Path],
                          chunking_methode: str = "standaard") -> list:
        """
        Verwerk meerdere bestanden.

        Args:
            paden: Lijst van bestandspaden
            chunking_methode: "standaard", "paragraaf", "zinnen", "semantisch"

        Returns:
            Alle chunks
        """
        alle_chunks = []

        for pad in paden:
            try:
                print(f"   [DOC] {pad.name}")
                tekst = self.processor.laad_bestand(pad)

                if not tekst:
                    self.statistieken["mislukt"] += 1
                    continue

                # Kies chunking methode
                if chunking_methode == "paragraaf":
                    chunks = self.processor.chunk_op_paragrafen(tekst, pad.stem)
                elif chunking_methode == "zinnen":
                    chunks = self.processor.chunk_op_zinnen(tekst, pad.stem)
                elif chunking_methode == "semantisch":
                    chunks = self.processor.chunk_semantisch(tekst, pad.stem)
                else:
                    chunks = self.processor.chunk_tekst(tekst, pad.stem)

                # Voeg bestandsmetadata toe
                bestand_meta = self.processor.extraheer_metadata(pad)
                for chunk in chunks:
                    chunk["metadata"].update(bestand_meta)

                alle_chunks.extend(chunks)
                self.statistieken["verwerkt"] += 1
                self.statistieken["totaal_chunks"] += len(chunks)
                print(f"      -> {len(chunks)} chunks")

            except Exception as e:
                print(f"   [X] {pad.name}: {e}")
                self.statistieken["mislukt"] += 1

        return alle_chunks

    def toon_statistieken(self) -> str:
        """Toon verwerkingsstatistieken."""
        return (
            f"Verwerkt: {self.statistieken['verwerkt']} | "
            f"Mislukt: {self.statistieken['mislukt']} | "
            f"Chunks: {self.statistieken['totaal_chunks']}"
        )
