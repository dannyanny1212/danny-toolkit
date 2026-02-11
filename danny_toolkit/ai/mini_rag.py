"""
Mini-RAG Systeem - Eenvoudige RAG implementatie.
Versie 2.0 - Met TF-IDF, BM25, meerdere formaten, AI integratie en meer!
"""

import json
import math
import re
import csv
from pathlib import Path
from collections import Counter
from datetime import datetime

from ..core.config import Config
from ..core.utils import clear_scherm, kleur, Kleur
from ..core.embeddings import TFIDFEmbeddings
from ..core.document_processor import DocumentProcessor


class MiniRAG:
    """Mini-RAG systeem met lokale embeddings - Uitgebreide versie."""

    # Stopwoorden voor betere zoekresultaten
    STOPWOORDEN = {
        "de", "het", "een", "en", "van", "in", "is", "op", "te", "dat",
        "die", "voor", "zijn", "met", "als", "aan", "er", "maar", "om",
        "ook", "dan", "naar", "bij", "tot", "uit", "door", "over", "nog",
        "wel", "geen", "meer", "al", "worden", "wordt", "werd", "waren",
        "zou", "kunnen", "moeten", "zal", "hebben", "heeft", "had", "was",
        "niet", "kan", "mag", "wil", "moet", "deze", "dit", "zo", "toch",
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to",
        "for", "of", "with", "by", "from", "is", "are", "was", "were",
        "be", "been", "being", "have", "has", "had", "do", "does", "did",
    }

    # Chunk strategieën
    CHUNK_STRATEGIES = {
        "woorden": "Vaste hoeveelheid woorden",
        "zinnen": "Per zin splitsen",
        "paragraaf": "Per paragraaf splitsen",
        "sliding": "Sliding window met overlap",
    }

    def __init__(self, documenten_map: Path = None):
        Config.ensure_dirs()
        self.documenten_map = documenten_map or Config.DOCUMENTEN_DIR
        self.data_file = Config.DATA_DIR / "rag_data.json"
        self.documenten = []
        self.index = {}
        self.tfidf_embedder = None
        self.processor = DocumentProcessor()
        self.data = self._laad_data()
        self.chunk_strategie = "sliding"
        self.chunk_grootte = 150
        self.ai_client = None
        self.ai_provider = None

    def _laad_data(self) -> dict:
        """Laad opgeslagen RAG data."""
        if self.data_file.exists():
            with open(self.data_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return self._migreer_data(data)
        return self._standaard_data()

    def _standaard_data(self) -> dict:
        """Standaard data structuur."""
        return {
            "zoekgeschiedenis": [],
            "favoriete_vragen": [],
            "statistieken": {
                "totaal_zoekopdrachten": 0,
                "documenten_geindexeerd": 0,
                "chunks_totaal": 0,
                "eerste_gebruik": datetime.now().isoformat(),
                "laatste_gebruik": None,
            },
            "instellingen": {
                "chunk_strategie": "sliding",
                "chunk_grootte": 150,
                "top_k": 5,
                "min_score": 0.1,
                "gebruik_ai": False,
            },
            "cached_index": None,
        }

    def _migreer_data(self, data: dict) -> dict:
        """Migreer oude data naar nieuw format."""
        defaults = self._standaard_data()
        for key, value in defaults.items():
            if key not in data:
                data[key] = value
            elif isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    if sub_key not in data[key]:
                        data[key][sub_key] = sub_value
        return data

    def _sla_data_op(self):
        """Sla data op naar bestand."""
        self.data["statistieken"]["laatste_gebruik"] = datetime.now().isoformat()
        with open(self.data_file, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)

    def _init_ai(self) -> bool:
        """Initialiseer AI client voor betere antwoorden."""
        # TODO: Groq verwijderd — direct Claude

        # Probeer Claude
        if Config.has_anthropic_key():
            try:
                import anthropic
                self.ai_client = anthropic.Anthropic(api_key=Config.ANTHROPIC_API_KEY)
                self.ai_provider = "claude"
                return True
            except Exception:
                pass

        return False

    def _maak_chunks(self, tekst: str,
                      doc_id: str = "doc") -> list:
        """Splits tekst in chunks via DocumentProcessor."""
        strategie = self.chunk_strategie
        if strategie == "zinnen":
            chunk_dicts = self.processor.chunk_op_zinnen(
                tekst, doc_id
            )
        elif strategie == "paragraaf":
            chunk_dicts = self.processor.chunk_op_paragrafen(
                tekst, doc_id
            )
        else:
            chunk_dicts = self.processor.chunk_tekst(
                tekst, doc_id
            )
        return [c["tekst"] for c in chunk_dicts]

    def _bm25_score(self, query_terms: list,
                    chunk_data: dict,
                    k1: float = 1.5,
                    b: float = 0.75) -> float:
        """Bereken BM25 score."""
        tf = chunk_data["tf"]
        doc_len = chunk_data.get("length", 100)
        avg_doc_len = self.data["statistieken"].get(
            "avg_chunk_length", 100
        )

        score = 0.0
        for term in query_terms:
            if term in tf:
                term_tf = tf[term] * doc_len
                idf = self.tfidf_embedder.idf.get(term, 0)
                numerator = term_tf * (k1 + 1)
                denominator = (
                    term_tf
                    + k1 * (1 - b + b * (doc_len / avg_doc_len))
                )
                if denominator > 0:
                    score += idf * (numerator / denominator)

        return score

    def _cosine_dense(self, vec1: list,
                       vec2: list) -> float:
        """Cosine similarity voor dense vectoren."""
        dot = sum(a * b for a, b in zip(vec1, vec2))
        mag1 = math.sqrt(sum(a ** 2 for a in vec1))
        mag2 = math.sqrt(sum(b ** 2 for b in vec2))
        if mag1 == 0 or mag2 == 0:
            return 0.0
        return dot / (mag1 * mag2)

    def _lees_bestand(self, pad: Path) -> str:
        """Lees bestand in verschillende formaten."""
        suffix = pad.suffix.lower()

        try:
            if suffix == ".txt":
                with open(pad, "r", encoding="utf-8") as f:
                    return f.read()

            elif suffix == ".md":
                with open(pad, "r", encoding="utf-8") as f:
                    tekst = f.read()
                    # Verwijder markdown syntax voor betere indexering
                    tekst = re.sub(r'#+ ', '', tekst)  # Headers
                    tekst = re.sub(r'\*\*(.+?)\*\*', r'\1', tekst)  # Bold
                    tekst = re.sub(r'\*(.+?)\*', r'\1', tekst)  # Italic
                    tekst = re.sub(r'\[(.+?)\]\(.+?\)', r'\1', tekst)  # Links
                    tekst = re.sub(r'```[\s\S]*?```', '', tekst)  # Code blocks
                    return tekst

            elif suffix == ".json":
                with open(pad, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # Converteer JSON naar tekst
                    return self._json_naar_tekst(data)

            elif suffix == ".csv":
                with open(pad, "r", encoding="utf-8", newline="") as f:
                    reader = csv.reader(f)
                    rows = list(reader)
                    if not rows:
                        return ""
                    # Eerste rij als headers
                    headers = rows[0]
                    tekst_delen = []
                    for row in rows[1:]:
                        rij_tekst = ". ".join(
                            f"{headers[i]}: {row[i]}"
                            for i in range(min(len(headers), len(row)))
                            if row[i].strip()
                        )
                        if rij_tekst:
                            tekst_delen.append(rij_tekst)
                    return "\n".join(tekst_delen)

            elif suffix == ".html":
                with open(pad, "r", encoding="utf-8") as f:
                    html = f.read()
                    # Verwijder HTML tags
                    tekst = re.sub(r'<script[\s\S]*?</script>', '', html)
                    tekst = re.sub(r'<style[\s\S]*?</style>', '', tekst)
                    tekst = re.sub(r'<[^>]+>', ' ', tekst)
                    tekst = re.sub(r'\s+', ' ', tekst)
                    return tekst.strip()

            else:
                # Probeer als tekst te lezen
                with open(pad, "r", encoding="utf-8") as f:
                    return f.read()

        except Exception as e:
            print(kleur(f"   [!] Fout bij lezen {pad.name}: {e}", Kleur.ROOD))
            return ""

    def _json_naar_tekst(self, data, prefix: str = "") -> str:
        """Converteer JSON data naar leesbare tekst."""
        delen = []

        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, (dict, list)):
                    delen.append(self._json_naar_tekst(value, f"{prefix}{key}."))
                else:
                    delen.append(f"{prefix}{key}: {value}")
        elif isinstance(data, list):
            for i, item in enumerate(data):
                if isinstance(item, (dict, list)):
                    delen.append(self._json_naar_tekst(item, f"{prefix}[{i}]."))
                else:
                    delen.append(f"{prefix}{i}: {item}")
        else:
            delen.append(str(data))

        return "\n".join(delen)

    def indexeer(self, toon_voortgang: bool = True):
        """Indexeer alle documenten."""
        if toon_voortgang:
            print(kleur("\n[INDEXEREN] Documenten laden...", Kleur.CYAAN))

        if not self.documenten_map.exists():
            self.documenten_map.mkdir(parents=True, exist_ok=True)
            if toon_voortgang:
                print(kleur(f"   Map aangemaakt: {self.documenten_map}", Kleur.GEEL))
                print("   Plaats bestanden (.txt, .md, .json, .csv, .html) in deze map.")
            return

        # Ondersteunde formaten
        formaten = ["*.txt", "*.md", "*.json", "*.csv", "*.html"]
        bestanden = []
        for formaat in formaten:
            bestanden.extend(self.documenten_map.glob(formaat))

        if not bestanden:
            if toon_voortgang:
                print(kleur(f"   Geen documenten gevonden in: {self.documenten_map}", Kleur.GEEL))
            return

        totaal_chunks = 0

        for bestand in bestanden:
            inhoud = self._lees_bestand(bestand)

            if not inhoud or len(inhoud) < 50:
                continue

            chunks = self._maak_chunks(inhoud, bestand.stem)

            doc = {
                "id": len(self.documenten),
                "naam": bestand.name,
                "pad": str(bestand),
                "formaat": bestand.suffix.lower(),
                "inhoud_preview": inhoud[:500],
                "chunks": chunks,
                "woorden": len(inhoud.split()),
                "geindexeerd": datetime.now().isoformat(),
            }
            self.documenten.append(doc)

            if toon_voortgang:
                print(kleur(f"   [OK] {bestand.name}", Kleur.GROEN) +
                      f" ({len(chunks)} chunks, {doc['woorden']} woorden)")

            totaal_chunks += len(chunks)

        # Bouw index
        if toon_voortgang:
            print(kleur(
                "\n[INDEXEREN] Index opbouwen...", Kleur.CYAAN
            ))

        totaal_lengte = 0
        chunk_teksten = []
        chunk_ids = []

        for doc in self.documenten:
            for i, chunk in enumerate(doc["chunks"]):
                chunk_id = f"{doc['id']}_{i}"
                chunk_len = len(chunk.split())
                totaal_lengte += chunk_len
                chunk_teksten.append(chunk)
                chunk_ids.append(chunk_id)

                self.index[chunk_id] = {
                    "doc_id": doc["id"],
                    "doc_naam": doc["naam"],
                    "chunk_idx": i,
                    "chunk": chunk,
                    "length": chunk_len,
                }

        # Train TF-IDF embedder
        dim = min(512, max(100, len(chunk_teksten)))
        self.tfidf_embedder = TFIDFEmbeddings(dimensies=dim)
        self.tfidf_embedder.fit(chunk_teksten)

        # Embed chunks en bereken TF voor BM25
        vectors = self.tfidf_embedder.embed(chunk_teksten)
        for idx, chunk_id in enumerate(chunk_ids):
            self.index[chunk_id]["tfidf_vector"] = vectors[idx]
            # Raw TF voor BM25
            woorden = self.tfidf_embedder._tokenize(
                self.index[chunk_id]["chunk"]
            )
            tf = Counter(woorden)
            totaal = sum(tf.values())
            if totaal > 0:
                for w in tf:
                    tf[w] = tf[w] / totaal
            self.index[chunk_id]["tf"] = dict(tf)

        # Update statistieken
        avg_len = totaal_lengte / len(self.index) if self.index else 100
        self.data["statistieken"]["avg_chunk_length"] = avg_len
        self.data["statistieken"]["documenten_geindexeerd"] = len(self.documenten)
        self.data["statistieken"]["chunks_totaal"] = len(self.index)
        self._sla_data_op()

        if toon_voortgang:
            print(kleur(f"   [OK] {len(self.index)} chunks geïndexeerd", Kleur.GROEN))
            print(kleur(f"   [OK] {len(self.tfidf_embedder.idf) if self.tfidf_embedder else 0} unieke termen", Kleur.GROEN))

    def zoek(self, vraag: str, top_k: int = None, methode: str = "hybrid") -> list:
        """Zoek relevante chunks met verschillende methodes."""
        if not self.index:
            return []

        top_k = top_k or self.data["instellingen"]["top_k"]
        min_score = self.data["instellingen"]["min_score"]

        query_terms = self.tfidf_embedder._tokenize(vraag)
        query_vector = self.tfidf_embedder._embed_one(vraag)

        scores = []

        for chunk_id, chunk_data in self.index.items():
            if methode == "tfidf":
                score = self._cosine_dense(
                    query_vector,
                    chunk_data["tfidf_vector"]
                )
            elif methode == "bm25":
                score = self._bm25_score(
                    query_terms, chunk_data
                )
            else:  # hybrid
                tfidf_score = self._cosine_dense(
                    query_vector,
                    chunk_data["tfidf_vector"]
                )
                bm25_score = self._bm25_score(
                    query_terms, chunk_data
                )
                score = 0.5 * tfidf_score + 0.5 * (
                    bm25_score / 10
                    if bm25_score > 0 else 0
                )

            if score > min_score:
                scores.append({
                    "chunk_id": chunk_id,
                    "doc_naam": chunk_data["doc_naam"],
                    "doc_id": chunk_data["doc_id"],
                    "chunk": chunk_data["chunk"],
                    "score": score,
                })

        scores.sort(key=lambda x: x["score"], reverse=True)

        # Update zoekgeschiedenis
        self.data["zoekgeschiedenis"].append({
            "vraag": vraag,
            "resultaten": len(scores),
            "top_score": scores[0]["score"] if scores else 0,
            "datum": datetime.now().isoformat(),
        })
        self.data["statistieken"]["totaal_zoekopdrachten"] += 1

        # Beperk geschiedenis tot laatste 100
        if len(self.data["zoekgeschiedenis"]) > 100:
            self.data["zoekgeschiedenis"] = self.data["zoekgeschiedenis"][-100:]

        self._sla_data_op()

        return scores[:top_k]

    def _genereer_ai_antwoord(self, vraag: str, context: str) -> str:
        """Genereer antwoord met AI op basis van context."""
        if not self.ai_client:
            return None

        systeem = """Je bent een behulpzame assistent die vragen beantwoordt op basis
van de gegeven context. Antwoord alleen met informatie uit de context.
Als de context geen antwoord bevat, zeg dat eerlijk. Antwoord in het Nederlands."""

        prompt = f"""Context:
{context}

Vraag: {vraag}

Geef een beknopt en accuraat antwoord gebaseerd op de context."""

        try:
            if self.ai_provider == "claude":
                response = self.ai_client.messages.create(
                    model=Config.CLAUDE_MODEL,
                    max_tokens=512,
                    system=systeem,
                    messages=[{"role": "user", "content": prompt}]
                )
                return response.content[0].text
            else:
                # TODO: Groq verwijderd
                return None
        except Exception as e:
            print(kleur(f"   [!] AI fout: {e}", Kleur.ROOD))
            return None

    def genereer_antwoord(self, vraag: str, chunks: list) -> str:
        """Genereer een antwoord op basis van gevonden chunks."""
        if not chunks:
            return "Ik kon geen relevante informatie vinden in de documenten."

        # Bouw context
        context = "\n\n".join([
            f"[{c['doc_naam']}]:\n{c['chunk']}"
            for c in chunks[:3]
        ])

        # Probeer AI antwoord als ingeschakeld
        if self.data["instellingen"]["gebruik_ai"] and self.ai_client:
            ai_antwoord = self._genereer_ai_antwoord(vraag, context)
            if ai_antwoord:
                bronnen = set(c["doc_naam"] for c in chunks)
                return f"{ai_antwoord}\n\n" + kleur(f"Bronnen: {', '.join(bronnen)}", Kleur.CYAAN)

        # Fallback: extractief antwoord
        vraag_lower = vraag.lower()
        vraag_woorden = set(
            w for w in vraag.lower().split()
            if len(w) > 2 and w not in self.STOPWOORDEN
        )
        relevante_zinnen = []

        for chunk in chunks:
            zinnen = re.split(r'(?<=[.!?])\s+', chunk["chunk"])
            for zin in zinnen:
                zin = zin.strip()
                if len(zin) > 30:
                    zin_woorden = set(
                        w for w in zin.lower().split()
                        if len(w) > 2
                        and w not in self.STOPWOORDEN
                    )
                    overlap = vraag_woorden & zin_woorden
                    if len(overlap) >= 2:
                        relevante_zinnen.append((zin, len(overlap), chunk["doc_naam"]))

        if relevante_zinnen:
            # Sorteer op overlap
            relevante_zinnen.sort(key=lambda x: x[1], reverse=True)

            antwoord = kleur("Op basis van de documenten:\n", Kleur.GROEN)
            gezien = set()
            for zin, _, bron in relevante_zinnen[:5]:
                if zin not in gezien:
                    antwoord += f"\n• {zin}"
                    if not zin.endswith(('.', '!', '?')):
                        antwoord += "."
                    gezien.add(zin)

            bronnen = set(c["doc_naam"] for c in chunks)
            antwoord += "\n\n" + kleur(f"Bronnen: {', '.join(bronnen)}", Kleur.CYAAN)
            return antwoord

        # Fallback: toon relevante context
        antwoord = kleur("Relevante context gevonden:\n", Kleur.GEEL)
        for chunk in chunks[:2]:
            tekst = chunk["chunk"][:300]
            antwoord += f"\n[{chunk['doc_naam']}]:\n{tekst}...\n"

        return antwoord

    def vraag(self, vraag: str, toon_scores: bool = True) -> str:
        """Beantwoord een vraag met RAG."""
        if toon_scores:
            print(kleur(f"\n[ZOEKEN] \"{vraag}\"", Kleur.CYAAN))

        chunks = self.zoek(vraag)

        if chunks and toon_scores:
            print(kleur(f"   [OK] {len(chunks)} relevante chunks gevonden:", Kleur.GROEN))
            for c in chunks[:3]:
                print(f"      • {c['doc_naam']} (score: {c['score']:.3f})")

        return self.genereer_antwoord(vraag, chunks)

    def _extraheer_keywords(self, top_n: int = 20) -> list:
        """Extraheer belangrijkste keywords uit alle documenten."""
        # Gebruik IDF scores voor belangrijkheid
        keywords = sorted(self.tfidf_embedder.idf.items(), key=lambda x: x[1], reverse=True)
        return keywords[:top_n]

    def _toon_document_info(self, doc_idx: int):
        """Toon gedetailleerde info over een document."""
        if doc_idx < 0 or doc_idx >= len(self.documenten):
            print(kleur("[!] Ongeldig document nummer.", Kleur.ROOD))
            return

        doc = self.documenten[doc_idx]

        print(kleur(f"\n{'='*50}", Kleur.CYAAN))
        print(kleur(f"DOCUMENT: {doc['naam']}", Kleur.CYAAN))
        print(kleur(f"{'='*50}", Kleur.CYAAN))
        print(f"  Formaat:     {doc['formaat']}")
        print(f"  Woorden:     {doc['woorden']}")
        print(f"  Chunks:      {len(doc['chunks'])}")
        print(f"  Geïndexeerd: {doc['geindexeerd'][:19]}")
        print(kleur("\nPreview:", Kleur.GEEL))
        print(f"  {doc['inhoud_preview'][:300]}...")

        # Keywords voor dit document
        doc_terms = Counter()
        for i, chunk in enumerate(doc["chunks"]):
            chunk_id = f"{doc['id']}_{i}"
            if chunk_id in self.index:
                tf = self.index[chunk_id].get("tf", {})
                for term, tf_score in tf.items():
                    idf = self.tfidf_embedder.idf.get(
                        term, 0
                    )
                    doc_terms[term] += tf_score * idf

        top_terms = doc_terms.most_common(10)
        if top_terms:
            print(kleur("\nBelangrijkste termen:", Kleur.GEEL))
            for term, score in top_terms:
                print(f"  • {term} ({score:.3f})")

    def _toon_statistieken(self):
        """Toon uitgebreide statistieken."""
        stats = self.data["statistieken"]

        print(kleur("\n╔════════════════════════════════════════════════════╗", Kleur.CYAAN))
        print(kleur("║              RAG STATISTIEKEN                      ║", Kleur.CYAAN))
        print(kleur("╠════════════════════════════════════════════════════╣", Kleur.CYAAN))
        print(kleur("║  INDEX                                             ║", Kleur.CYAAN))
        print(f"║  Documenten:            {stats['documenten_geindexeerd']:>20}  ║")
        print(f"║  Chunks:                {stats['chunks_totaal']:>20}  ║")
        print(f"║  Unieke termen:         {len(self.tfidf_embedder.idf) if self.tfidf_embedder else 0:>20}  ║")
        print(f"║  Gem. chunk lengte:     {stats.get('avg_chunk_length', 0):>17.1f}  ║")
        print(kleur("║                                                    ║", Kleur.CYAAN))
        print(kleur("║  GEBRUIK                                           ║", Kleur.CYAAN))
        print(f"║  Totaal zoekopdrachten: {stats['totaal_zoekopdrachten']:>20}  ║")
        print(f"║  Zoekgeschiedenis:      {len(self.data['zoekgeschiedenis']):>20}  ║")
        print(f"║  Favoriete vragen:      {len(self.data['favoriete_vragen']):>20}  ║")

        if stats.get("eerste_gebruik"):
            eerste = datetime.fromisoformat(stats["eerste_gebruik"]).strftime("%d-%m-%Y")
            print(f"║  Eerste gebruik:        {eerste:>20}  ║")

        print(kleur("║                                                    ║", Kleur.CYAAN))
        print(kleur("║  INSTELLINGEN                                      ║", Kleur.CYAAN))
        inst = self.data["instellingen"]
        print(f"║  Chunk strategie:       {inst['chunk_strategie']:>20}  ║")
        print(f"║  Chunk grootte:         {inst['chunk_grootte']:>20}  ║")
        print(f"║  Top K resultaten:      {inst['top_k']:>20}  ║")
        ai_status = "Aan" if inst['gebruik_ai'] and self.ai_client else "Uit"
        print(f"║  AI antwoorden:         {ai_status:>20}  ║")
        print(kleur("╚════════════════════════════════════════════════════╝", Kleur.CYAAN))

    def _toon_zoekgeschiedenis(self):
        """Toon recente zoekgeschiedenis."""
        geschiedenis = self.data["zoekgeschiedenis"]

        if not geschiedenis:
            print(kleur("[!] Geen zoekgeschiedenis.", Kleur.ROOD))
            return

        print(kleur("\n=== RECENTE ZOEKOPDRACHTEN ===", Kleur.CYAAN))

        for i, item in enumerate(reversed(geschiedenis[-10:]), 1):
            datum = datetime.fromisoformat(item["datum"]).strftime("%d-%m %H:%M")
            print(f"  {i}. [{datum}] \"{item['vraag'][:40]}...\"")
            print(f"     Resultaten: {item['resultaten']}, Top score: {item['top_score']:.3f}")

    def _beheer_favorieten(self):
        """Beheer favoriete vragen."""
        while True:
            print(kleur("\n=== FAVORIETE VRAGEN ===", Kleur.GEEL))

            favorieten = self.data["favoriete_vragen"]

            if favorieten:
                for i, fav in enumerate(favorieten, 1):
                    print(f"  {i}. {fav['vraag'][:50]}")
            else:
                print("  (Geen favorieten)")

            print("\n  A. Nieuwe favoriet toevoegen")
            print("  0. Terug")

            keuze = input("\nKeuze: ").strip().lower()

            if keuze == "0":
                break
            elif keuze == "a":
                vraag = input("Vraag om op te slaan: ").strip()
                if vraag:
                    self.data["favoriete_vragen"].append({
                        "vraag": vraag,
                        "datum": datetime.now().isoformat()
                    })
                    self._sla_data_op()
                    print(kleur("[OK] Favoriet toegevoegd!", Kleur.GROEN))
            else:
                try:
                    idx = int(keuze) - 1
                    if 0 <= idx < len(favorieten):
                        # Gebruik favoriet
                        vraag = favorieten[idx]["vraag"]
                        antwoord = self.vraag(vraag)
                        print("\n" + "-" * 50)
                        print(kleur("ANTWOORD:", Kleur.GROEN))
                        print("-" * 50)
                        print(antwoord)
                except ValueError:
                    pass

    def _instellingen_menu(self):
        """Instellingen aanpassen."""
        while True:
            inst = self.data["instellingen"]

            print(kleur("\n╔════════════════════════════════════════════════════╗", Kleur.GEEL))
            print(kleur("║              INSTELLINGEN                          ║", Kleur.GEEL))
            print(kleur("╠════════════════════════════════════════════════════╣", Kleur.GEEL))
            print(f"║  1. Chunk strategie:    {inst['chunk_strategie']:>20}  ║")
            print(f"║  2. Chunk grootte:      {inst['chunk_grootte']:>20}  ║")
            print(f"║  3. Top K resultaten:   {inst['top_k']:>20}  ║")
            print(f"║  4. Min. score:         {inst['min_score']:>20}  ║")
            ai_status = "Aan" if inst['gebruik_ai'] else "Uit"
            print(f"║  5. AI antwoorden:      {ai_status:>20}  ║")
            print(kleur("║                                                    ║", Kleur.GEEL))
            print("║  0. Terug (en herindexeer indien nodig)            ║")
            print(kleur("╚════════════════════════════════════════════════════╝", Kleur.GEEL))

            keuze = input("\nKeuze: ").strip()

            if keuze == "0":
                break
            elif keuze == "1":
                print("\nChunk strategieën:")
                for key, beschrijving in self.CHUNK_STRATEGIES.items():
                    print(f"  {key}: {beschrijving}")
                nieuwe = input("Keuze: ").strip().lower()
                if nieuwe in self.CHUNK_STRATEGIES:
                    inst["chunk_strategie"] = nieuwe
                    self.chunk_strategie = nieuwe
            elif keuze == "2":
                try:
                    nieuwe = int(input("Nieuwe chunk grootte (50-500): "))
                    if 50 <= nieuwe <= 500:
                        inst["chunk_grootte"] = nieuwe
                        self.chunk_grootte = nieuwe
                except ValueError:
                    pass
            elif keuze == "3":
                try:
                    nieuwe = int(input("Nieuwe top K (1-20): "))
                    if 1 <= nieuwe <= 20:
                        inst["top_k"] = nieuwe
                except ValueError:
                    pass
            elif keuze == "4":
                try:
                    nieuwe = float(input("Nieuwe min. score (0.01-0.5): "))
                    if 0.01 <= nieuwe <= 0.5:
                        inst["min_score"] = nieuwe
                except ValueError:
                    pass
            elif keuze == "5":
                inst["gebruik_ai"] = not inst["gebruik_ai"]
                if inst["gebruik_ai"] and not self.ai_client:
                    if self._init_ai():
                        print(kleur(f"[OK] AI geactiveerd ({self.ai_provider})", Kleur.GROEN))
                    else:
                        print(kleur("[!] Geen AI beschikbaar (geen API key)", Kleur.ROOD))
                        inst["gebruik_ai"] = False

            self._sla_data_op()

    def _toon_help(self):
        """Toon hulp informatie."""
        print(kleur("\n╔════════════════════════════════════════════════════╗", Kleur.CYAAN))
        print(kleur("║              MINI-RAG HELP                         ║", Kleur.CYAAN))
        print(kleur("╠════════════════════════════════════════════════════╣", Kleur.CYAAN))
        print("║  COMMANDO'S                                        ║")
        print("║  /docs       - Bekijk geïndexeerde documenten      ║")
        print("║  /stats      - Toon statistieken                   ║")
        print("║  /history    - Zoekgeschiedenis                    ║")
        print("║  /fav        - Favoriete vragen                    ║")
        print("║  /keywords   - Belangrijkste keywords              ║")
        print("║  /settings   - Instellingen aanpassen              ║")
        print("║  /reindex    - Herindexeer documenten              ║")
        print("║  /help       - Deze hulp                           ║")
        print("║  stop        - Afsluiten                           ║")
        print(kleur("║                                                    ║", Kleur.CYAAN))
        print("║  TIPS                                              ║")
        print("║  • Stel specifieke vragen voor betere resultaten   ║")
        print("║  • Gebruik meerdere zoektermen                     ║")
        print("║  • Zet AI aan voor betere antwoorden               ║")
        print(kleur("╚════════════════════════════════════════════════════╝", Kleur.CYAAN))

    def _toon_documenten(self):
        """Toon lijst van geïndexeerde documenten."""
        if not self.documenten:
            print(kleur("[!] Geen documenten geïndexeerd.", Kleur.ROOD))
            return

        print(kleur("\n=== GEÏNDEXEERDE DOCUMENTEN ===", Kleur.CYAAN))

        for i, doc in enumerate(self.documenten, 1):
            print(f"\n  {i}. {kleur(doc['naam'], 'groen')}")
            print(f"     Formaat: {doc['formaat']} | "
                  f"Woorden: {doc['woorden']} | "
                  f"Chunks: {len(doc['chunks'])}")

        print("\n  0. Terug")
        keuze = input("\nBekijk document (nummer): ").strip()

        if keuze != "0":
            try:
                idx = int(keuze) - 1
                self._toon_document_info(idx)
            except ValueError:
                pass

    def _toon_keywords(self):
        """Toon belangrijkste keywords."""
        if not self.tfidf_embedder or not self.tfidf_embedder.idf:
            print(kleur("[!] Geen index beschikbaar.", Kleur.ROOD))
            return

        print(kleur("\n=== BELANGRIJKSTE KEYWORDS ===", Kleur.CYAAN))
        keywords = self._extraheer_keywords(20)

        for i, (term, score) in enumerate(keywords, 1):
            bar_len = int(score * 5)
            bar = "█" * bar_len
            print(f"  {i:2}. {term:<20} {bar} ({score:.2f})")

    def run(self):
        """Start de interactieve Mini-RAG modus."""
        clear_scherm()
        print(kleur("\n╔════════════════════════════════════════════════════╗", Kleur.CYAAN))
        print(kleur("║      MINI-RAG v2.0 - Document Vraag & Antwoord     ║", Kleur.CYAAN))
        print(kleur("║      Met TF-IDF, BM25 en AI integratie             ║", Kleur.CYAAN))
        print(kleur("╚════════════════════════════════════════════════════╝", Kleur.CYAAN))

        # Laad instellingen
        self.chunk_strategie = self.data["instellingen"]["chunk_strategie"]
        self.chunk_grootte = self.data["instellingen"]["chunk_grootte"]

        # Initialiseer AI indien gewenst
        if self.data["instellingen"]["gebruik_ai"]:
            if self._init_ai():
                print(kleur(f"[OK] AI geactiveerd ({self.ai_provider})", Kleur.GROEN))

        # Indexeer documenten
        self.indexeer()

        if not self.index:
            print(kleur(f"\nGeen documenten gevonden in: {self.documenten_map}", Kleur.GEEL))
            print("Ondersteunde formaten: .txt, .md, .json, .csv, .html")
            input("\nDruk op Enter...")
            return

        print(kleur("\n" + "=" * 50, Kleur.CYAAN))
        print(kleur("VRAAG & ANTWOORD - Typ /help voor commando's", Kleur.CYAAN))
        print(kleur("=" * 50, Kleur.CYAAN))

        while True:
            try:
                vraag = input(kleur("\nVraag: ", Kleur.GEEL)).strip()

                if vraag.lower() in ["stop", "quit", "exit", "q"]:
                    print(kleur("\nTot ziens!", Kleur.CYAAN))
                    break

                if not vraag:
                    continue

                # Commando's
                if vraag.startswith("/"):
                    cmd = vraag.lower().split()[0]

                    if cmd == "/help":
                        self._toon_help()
                    elif cmd == "/docs":
                        self._toon_documenten()
                    elif cmd == "/stats":
                        self._toon_statistieken()
                    elif cmd == "/history":
                        self._toon_zoekgeschiedenis()
                    elif cmd == "/fav":
                        self._beheer_favorieten()
                    elif cmd == "/keywords":
                        self._toon_keywords()
                    elif cmd == "/settings":
                        self._instellingen_menu()
                        # Herindexeer na instellingen wijziging
                        print(kleur("\n[HERINDEXEREN]...", Kleur.CYAAN))
                        self.documenten = []
                        self.index = {}
                        self.indexeer(toon_voortgang=False)
                        print(kleur("[OK] Herindexeren voltooid.", Kleur.GROEN))
                    elif cmd == "/reindex":
                        print(kleur("\n[HERINDEXEREN]...", Kleur.CYAAN))
                        self.documenten = []
                        self.index = {}
                        self.indexeer()
                    else:
                        print(kleur(f"[!] Onbekend commando: {cmd}", Kleur.ROOD))

                    continue

                # Beantwoord vraag
                antwoord = self.vraag(vraag)
                print("\n" + "-" * 50)
                print(kleur("ANTWOORD:", Kleur.GROEN))
                print("-" * 50)
                print(antwoord)

            except KeyboardInterrupt:
                print(kleur("\n\nTot ziens!", Kleur.CYAAN))
                break
            except EOFError:
                break

        self._sla_data_op()
