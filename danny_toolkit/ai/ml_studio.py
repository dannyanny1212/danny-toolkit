"""
Advanced ML Studio v1.0 - Machine Learning & Text Generation Lab.

Geavanceerde ML concepten:
- Text Generation met Transformers
- Chain-of-Thought Prompting
- RAG (Retrieval-Augmented Generation)
- Tokenizer Visualisatie
- Embedding Explorer
- Prompt Engineering
"""

import json
import logging
import time
import math
import hashlib
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from collections import Counter
from ..core.config import Config
from ..core.utils import clear_scherm

logger = logging.getLogger(__name__)

# Hugging Face Transformers
try:
    from transformers import pipeline, AutoTokenizer, AutoModel
    import torch
    HF_BESCHIKBAAR = True
except ImportError:
    HF_BESCHIKBAAR = False

# Anthropic
try:
    from anthropic import Anthropic
    ANTHROPIC_BESCHIKBAAR = True
except ImportError:
    ANTHROPIC_BESCHIKBAAR = False


# =============================================================================
# TOKENIZER COMPONENTEN
# =============================================================================

class SimpleTokenizer:
    """Simpele BPE-achtige tokenizer voor demonstratie."""

    # Basis vocabulary (gesimuleerd)
    SPECIAL_TOKENS = {
        "<PAD>": 0,
        "<UNK>": 1,
        "<BOS>": 2,
        "<EOS>": 3,
    }

    def __init__(self):
        self.vocab = dict(self.SPECIAL_TOKENS)
        self._build_basic_vocab()

    def _build_basic_vocab(self):
        """Bouw basis vocabulary."""
        # Voeg letters toe
        for i, char in enumerate("abcdefghijklmnopqrstuvwxyz"):
            self.vocab[char] = len(self.vocab)
            self.vocab[char.upper()] = len(self.vocab)

        # Voeg cijfers toe
        for digit in "0123456789":
            self.vocab[digit] = len(self.vocab)

        # Voeg punctuatie toe
        for punct in ".,!?;:'\"-()[]{}":
            self.vocab[punct] = len(self.vocab)

        # Voeg spatie toe
        self.vocab[" "] = len(self.vocab)

        # Voeg veelvoorkomende subwoorden toe (BPE-stijl)
        common_subwords = [
            "the", "ing", "tion", "er", "ed", "es", "en", "al", "re",
            "de", "het", "een", "van", "en", "te", "in", "op", "aan",
            "##s", "##en", "##er", "##ing", "##heid", "##lijk",
        ]
        for subword in common_subwords:
            if subword not in self.vocab:
                self.vocab[subword] = len(self.vocab)

    def tokenize(self, text: str) -> List[str]:
        """Tokeniseer tekst naar subwoord tokens."""
        tokens = []
        i = 0
        text_lower = text.lower()

        while i < len(text):
            # Probeer langste match te vinden
            matched = False
            for length in range(min(10, len(text) - i), 0, -1):
                subword = text_lower[i:i+length]
                if subword in self.vocab:
                    tokens.append(text[i:i+length])
                    i += length
                    matched = True
                    break

            if not matched:
                # Karakter voor karakter
                tokens.append(text[i])
                i += 1

        return tokens

    def encode(self, text: str) -> List[int]:
        """Converteer tekst naar token IDs."""
        tokens = self.tokenize(text)
        ids = []
        for token in tokens:
            token_lower = token.lower()
            if token_lower in self.vocab:
                ids.append(self.vocab[token_lower])
            else:
                ids.append(self.vocab["<UNK>"])
        return ids

    def decode(self, ids: List[int]) -> str:
        """Converteer token IDs terug naar tekst."""
        reverse_vocab = {v: k for k, v in self.vocab.items()}
        tokens = [reverse_vocab.get(id_, "<UNK>") for id_ in ids]
        return "".join(tokens)

    def vocab_size(self) -> int:
        """Retourneer vocabulary grootte."""
        return len(self.vocab)


# =============================================================================
# EMBEDDING COMPONENTEN
# =============================================================================

class SimpleEmbedding:
    """Simpele embedding generator voor demonstratie."""

    def __init__(self, dim: int = 128):
        self.dim = dim

    def embed(self, text: str) -> List[float]:
        """Genereer een pseudo-embedding via hashing."""
        # Gebruik hash voor deterministische output
        text_hash = hashlib.sha256(text.lower().encode()).hexdigest()

        # Converteer hash naar floats
        embedding = []
        for i in range(0, min(len(text_hash), self.dim * 2), 2):
            val = int(text_hash[i:i+2], 16) / 255.0
            embedding.append(val * 2 - 1)  # Schaal naar [-1, 1]

        # Vul aan tot gewenste dimensie
        while len(embedding) < self.dim:
            embedding.append(0.0)

        # Normaliseer
        magnitude = math.sqrt(sum(x**2 for x in embedding))
        if magnitude > 0:
            embedding = [x / magnitude for x in embedding]

        return embedding[:self.dim]

    def similarity(self, emb1: List[float], emb2: List[float]) -> float:
        """Bereken cosine similarity."""
        dot = sum(a * b for a, b in zip(emb1, emb2))
        mag1 = math.sqrt(sum(a**2 for a in emb1))
        mag2 = math.sqrt(sum(b**2 for b in emb2))
        if mag1 == 0 or mag2 == 0:
            return 0.0
        return dot / (mag1 * mag2)


# =============================================================================
# TEXT GENERATION
# =============================================================================

class TextGenerator:
    """Text generator met verschillende backends."""

    def __init__(self):
        self.hf_pipeline = None
        self.anthropic_client = None
        self._init_backends()

    def _init_backends(self):
        """Initialiseer beschikbare backends."""
        if ANTHROPIC_BESCHIKBAAR and Config.has_anthropic_key():
            self.anthropic_client = Anthropic()

    def generate_with_hf(self, prompt: str, max_length: int = 100,
                         temperature: float = 0.7) -> Optional[str]:
        """Genereer tekst met Hugging Face."""
        if not HF_BESCHIKBAAR:
            return None

        try:
            if self.hf_pipeline is None:
                print("  Loading GPT-2 model (eerste keer duurt even)...")
                self.hf_pipeline = pipeline(
                    'text-generation',
                    model='gpt2',
                    device=-1  # CPU
                )

            result = self.hf_pipeline(
                prompt,
                max_length=max_length,
                num_return_sequences=1,
                temperature=temperature,
                do_sample=True,
                pad_token_id=50256
            )
            return result[0]['generated_text']
        except Exception as e:
            return f"Fout: {e}"

    def generate_with_anthropic(self, prompt: str, max_tokens: int = 500,
                                 temperature: float = 0.7,
                                 system: str = None) -> Optional[str]:
        """Genereer tekst met Anthropic Claude."""
        if not self.anthropic_client:
            return None

        try:
            kwargs = {
                "model": Config.CLAUDE_MODEL,
                "max_tokens": max_tokens,
                "messages": [{"role": "user", "content": prompt}]
            }
            if system:
                kwargs["system"] = system

            response = self.anthropic_client.messages.create(**kwargs)
            return response.content[0].text
        except Exception as e:
            return f"Fout: {e}"

    def chain_of_thought(self, question: str) -> Optional[str]:
        """Gebruik Chain-of-Thought prompting."""
        cot_prompt = f"""Beantwoord de volgende vraag stap voor stap.
Denk hardop na en toon je redenering voordat je tot een conclusie komt.

Vraag: {question}

Laten we dit stap voor stap doordenken:"""

        return self.generate_with_anthropic(
            cot_prompt,
            max_tokens=1000,
            system="Je bent een analytische denker die problemen stap voor stap oplost. "
                   "Toon altijd je redenering voordat je een conclusie geeft."
        )


# =============================================================================
# RAG SYSTEEM
# =============================================================================

class SimpleRAG:
    """Simpel RAG (Retrieval-Augmented Generation) systeem."""

    def __init__(self):
        self.documents = []
        self.embedder = SimpleEmbedding(dim=64)
        self.doc_embeddings = []

    def add_document(self, text: str, metadata: dict = None):
        """Voeg document toe aan de kennisbank."""
        embedding = self.embedder.embed(text)
        self.documents.append({
            "text": text,
            "metadata": metadata or {},
            "added": datetime.now().isoformat()
        })
        self.doc_embeddings.append(embedding)

    def retrieve(self, query: str, top_k: int = 3) -> List[Dict]:
        """Haal relevante documenten op."""
        if not self.documents:
            return []

        query_emb = self.embedder.embed(query)

        # Bereken similarities
        scores = []
        for i, doc_emb in enumerate(self.doc_embeddings):
            sim = self.embedder.similarity(query_emb, doc_emb)
            scores.append((i, sim))

        # Sorteer op similarity
        scores.sort(key=lambda x: x[1], reverse=True)

        # Return top-k
        results = []
        for idx, score in scores[:top_k]:
            results.append({
                "document": self.documents[idx],
                "score": score
            })

        return results

    def generate_with_context(self, query: str, generator: TextGenerator) -> str:
        """Genereer antwoord met context uit documenten."""
        # Retrieve relevante documenten
        retrieved = self.retrieve(query, top_k=3)

        if not retrieved:
            return "Geen relevante documenten gevonden."

        # Bouw context
        context_parts = []
        for i, r in enumerate(retrieved, 1):
            context_parts.append(f"Document {i} (relevantie: {r['score']:.2f}):\n{r['document']['text']}")

        context = "\n\n".join(context_parts)

        # RAG prompt
        rag_prompt = f"""Gebruik de volgende context om de vraag te beantwoorden.
Baseer je antwoord ALLEEN op de gegeven context. Als de context niet genoeg informatie bevat, zeg dat dan.

CONTEXT:
{context}

VRAAG: {query}

ANTWOORD:"""

        return generator.generate_with_anthropic(
            rag_prompt,
            max_tokens=500,
            system="Je bent een behulpzame assistent die vragen beantwoordt op basis van de gegeven context. "
                   "Verzin geen informatie die niet in de context staat."
        )


# =============================================================================
# PROMPT ENGINEERING
# =============================================================================

class PromptTemplates:
    """Verzameling van prompt engineering templates."""

    TEMPLATES = {
        "zero_shot": {
            "naam": "Zero-Shot",
            "beschrijving": "Directe vraag zonder voorbeelden",
            "template": "{vraag}"
        },
        "few_shot": {
            "naam": "Few-Shot",
            "beschrijving": "Met voorbeelden voor context",
            "template": """Hier zijn enkele voorbeelden:

{voorbeelden}

Nu jouw beurt:
{vraag}"""
        },
        "chain_of_thought": {
            "naam": "Chain-of-Thought",
            "beschrijving": "Stapsgewijs redeneren",
            "template": """Beantwoord de volgende vraag stap voor stap.
Denk hardop na en toon je redenering.

Vraag: {vraag}

Laten we dit stap voor stap doordenken:"""
        },
        "role_play": {
            "naam": "Role-Play",
            "beschrijving": "AI neemt een specifieke rol aan",
            "template": """Je bent een {rol}.
Beantwoord de vraag vanuit dat perspectief.

Vraag: {vraag}

Antwoord als {rol}:"""
        },
        "structured_output": {
            "naam": "Structured Output",
            "beschrijving": "Vraag om specifiek formaat",
            "template": """Beantwoord de vraag in het volgende formaat:

FORMAT:
{format}

VRAAG: {vraag}

ANTWOORD (in het gevraagde formaat):"""
        },
        "socratic": {
            "naam": "Socratisch",
            "beschrijving": "Beantwoord met verhelderende vragen",
            "template": """In plaats van direct te antwoorden, stel verhelderende vragen
die helpen om het probleem beter te begrijpen.

Onderwerp: {vraag}

Verhelderende vragen:"""
        },
        "adversarial": {
            "naam": "Adversarial",
            "beschrijving": "Zoek zwakke punten",
            "template": """Analyseer het volgende standpunt kritisch.
Zoek naar zwakke punten, tegenargumenten en mogelijke fouten.

Standpunt: {vraag}

Kritische analyse:"""
        },
        "summary": {
            "naam": "Samenvatting",
            "beschrijving": "Comprimeer tot essentie",
            "template": """Vat de volgende tekst samen in maximaal {max_woorden} woorden.
Focus op de belangrijkste punten.

TEKST:
{vraag}

SAMENVATTING:"""
        }
    }

    SYSTEM_PROMPTS = {
        "expert": "Je bent een expert op dit gebied met decennia aan ervaring.",
        "teacher": "Je bent een geduldige leraar die concepten helder uitlegt.",
        "critic": "Je bent een kritische analist die altijd de andere kant bekijkt.",
        "creative": "Je bent een creatieve denker die buiten de gebaande paden denkt.",
        "concise": "Je geeft korte, bondige antwoorden zonder onnodige uitweiding.",
        "detailed": "Je geeft uitgebreide, gedetailleerde antwoorden met voorbeelden.",
    }


# =============================================================================
# ML STUDIO APP
# =============================================================================

class MLStudioApp:
    """Advanced ML Studio - Machine Learning & Text Generation Lab."""

    VERSIE = "1.0"

    def __init__(self):
        Config.ensure_dirs()
        self.data_dir = Config.APPS_DATA_DIR / "ml_studio"
        self.data_dir.mkdir(exist_ok=True)
        self.data_file = self.data_dir / "data.json"
        self.data = self._laad_data()

        # Componenten
        self.tokenizer = SimpleTokenizer()
        self.embedder = SimpleEmbedding()
        self.generator = TextGenerator()
        self.rag = SimpleRAG()

        # Laad opgeslagen RAG documenten
        self._laad_rag_docs()

    def _laad_data(self) -> Dict:
        """Laad opgeslagen data."""
        if self.data_file.exists():
            try:
                with open(self.data_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return {
            "generaties": [],
            "rag_documenten": [],
            "experimenten": [],
        }

    def _sla_op(self):
        """Sla data op."""
        with open(self.data_file, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)

    def _laad_rag_docs(self):
        """Laad opgeslagen RAG documenten."""
        for doc in self.data.get("rag_documenten", []):
            self.rag.add_document(doc["text"], doc.get("metadata"))

    def _text_generation(self):
        """Text generation lab."""
        clear_scherm()
        print("\n  === TEXT GENERATION LAB ===\n")

        print("  Beschikbare backends:")
        print(f"    1. Hugging Face (GPT-2): {'Beschikbaar' if HF_BESCHIKBAAR else 'Niet geinstalleerd'}")
        print(f"    2. Anthropic (Claude): {'Beschikbaar' if self.generator.anthropic_client else 'Niet geconfigureerd'}")

        if not HF_BESCHIKBAAR and not self.generator.anthropic_client:
            print("\n  Geen backends beschikbaar!")
            print("  Installeer: pip install transformers torch")
            print("  Of configureer ANTHROPIC_API_KEY")
            input("\n  Druk op Enter...")
            return

        backend = input("\n  Kies backend (1/2): ").strip()

        prompt = input("\n  Prompt: ").strip()
        if not prompt:
            return

        try:
            temp = float(input("  Temperature (0.1-1.5) [0.7]: ").strip() or "0.7")
            temp = max(0.1, min(1.5, temp))
        except ValueError:
            temp = 0.7

        print("\n  Genereren...")

        if backend == "1" and HF_BESCHIKBAAR:
            result = self.generator.generate_with_hf(prompt, temperature=temp)
        else:
            result = self.generator.generate_with_anthropic(prompt, temperature=temp)

        if result:
            print("\n  " + "=" * 50)
            print("  GEGENEREERDE TEKST:")
            print("  " + "=" * 50)

            # Wrap output
            for line in result.split("\n"):
                while len(line) > 70:
                    print(f"  {line[:70]}")
                    line = line[70:]
                print(f"  {line}")

            # Opslaan
            self.data["generaties"].append({
                "prompt": prompt,
                "result": result,
                "temperature": temp,
                "backend": "hf" if backend == "1" else "anthropic",
                "datum": datetime.now().isoformat()
            })
            self._sla_op()

        input("\n  Druk op Enter...")

    def _chain_of_thought(self):
        """Chain-of-Thought prompting demo."""
        clear_scherm()
        print("\n  === CHAIN-OF-THOUGHT PROMPTING ===\n")

        print("  Chain-of-Thought dwingt het model om stapsgewijs te redeneren.")
        print("  Dit verhoogt nauwkeurigheid bij complexe problemen.\n")

        if not self.generator.anthropic_client:
            print("  Vereist: ANTHROPIC_API_KEY")
            input("\n  Druk op Enter...")
            return

        print("  Voorbeeld vragen:")
        print("    - 'Als ik 3 appels heb en 2 weggeef, hoeveel heb ik dan?'")
        print("    - 'Wat is het volgende getal: 2, 4, 8, 16, ?'")
        print("    - 'Een trein rijdt 60 km/u. Hoe ver komt hij in 2.5 uur?'")

        vraag = input("\n  Jouw vraag: ").strip()
        if not vraag:
            return

        print("\n  Denken met Chain-of-Thought...")

        result = self.generator.chain_of_thought(vraag)

        if result:
            print("\n  " + "=" * 50)
            print("  STAPSGEWIJZE REDENERING:")
            print("  " + "=" * 50)

            for line in result.split("\n"):
                print(f"  {line}")

        input("\n  Druk op Enter...")

    def _rag_demo(self):
        """RAG (Retrieval-Augmented Generation) demo."""
        while True:
            clear_scherm()
            print("\n  === RAG DEMO ===\n")

            print("  RAG = Retrieval-Augmented Generation")
            print("  Het model zoekt eerst in documenten voordat het antwoordt.\n")

            print(f"  Documenten in kennisbank: {len(self.rag.documents)}")

            print("\n  Opties:")
            print("    1. Document toevoegen")
            print("    2. Documenten bekijken")
            print("    3. Vraag stellen (met RAG)")
            print("    4. Kennisbank wissen")
            print("    0. Terug")

            keuze = input("\n  Keuze: ").strip()

            if keuze == "0":
                break

            elif keuze == "1":
                print("\n  Voer document in (typ 'KLAAR' op nieuwe regel):")
                lines = []
                while True:
                    line = input("  > ")
                    if line.upper() == "KLAAR":
                        break
                    lines.append(line)

                if lines:
                    text = "\n".join(lines)
                    titel = input("  Titel (optioneel): ").strip()

                    self.rag.add_document(text, {"titel": titel})
                    self.data["rag_documenten"].append({
                        "text": text,
                        "metadata": {"titel": titel}
                    })
                    self._sla_op()
                    print("\n  Document toegevoegd!")

                input("\n  Druk op Enter...")

            elif keuze == "2":
                if not self.rag.documents:
                    print("\n  Geen documenten.")
                else:
                    print("\n  DOCUMENTEN:")
                    for i, doc in enumerate(self.rag.documents, 1):
                        titel = doc.get("metadata", {}).get("titel", "Geen titel")
                        preview = doc["text"][:50].replace("\n", " ")
                        print(f"    {i}. [{titel}] {preview}...")

                input("\n  Druk op Enter...")

            elif keuze == "3":
                if not self.rag.documents:
                    print("\n  Voeg eerst documenten toe!")
                    input("\n  Druk op Enter...")
                    continue

                if not self.generator.anthropic_client:
                    print("\n  Vereist: ANTHROPIC_API_KEY")
                    input("\n  Druk op Enter...")
                    continue

                vraag = input("\n  Jouw vraag: ").strip()
                if not vraag:
                    continue

                print("\n  Zoeken in kennisbank...")
                retrieved = self.rag.retrieve(vraag)

                print("\n  Gevonden documenten:")
                for r in retrieved:
                    score = r["score"]
                    titel = r["document"].get("metadata", {}).get("titel", "?")
                    print(f"    - {titel} (score: {score:.2f})")

                print("\n  Genereren met context...")
                result = self.rag.generate_with_context(vraag, self.generator)

                print("\n  " + "=" * 50)
                print("  RAG ANTWOORD:")
                print("  " + "=" * 50)
                for line in result.split("\n"):
                    print(f"  {line}")

                input("\n  Druk op Enter...")

            elif keuze == "4":
                if input("\n  Weet je zeker? (j/n): ").lower() == "j":
                    self.rag = SimpleRAG()
                    self.data["rag_documenten"] = []
                    self._sla_op()
                    print("  Kennisbank gewist!")
                input("\n  Druk op Enter...")

    def _tokenizer_lab(self):
        """Tokenizer visualisatie lab."""
        clear_scherm()
        print("\n  === TOKENIZER LAB ===\n")

        print("  Tokenizers splitsen tekst in subwoord-eenheden (tokens).")
        print("  Dit is hoe LLMs tekst 'zien'.\n")

        print(f"  Vocabulary grootte: {self.tokenizer.vocab_size()}")

        tekst = input("\n  Tekst om te tokeniseren: ").strip()
        if not tekst:
            return

        # Tokenize
        tokens = self.tokenizer.tokenize(tekst)
        ids = self.tokenizer.encode(tekst)

        print("\n  " + "=" * 50)
        print("  TOKENISATIE RESULTAAT:")
        print("  " + "=" * 50)

        print(f"\n  Origineel: {tekst}")
        print(f"  Aantal tokens: {len(tokens)}")

        print("\n  Tokens:")
        token_str = " | ".join(f"'{t}'" for t in tokens)
        print(f"    {token_str}")

        print("\n  Token IDs:")
        print(f"    {ids}")

        # Statistieken
        print("\n  Statistieken:")
        print(f"    Karakters: {len(tekst)}")
        print(f"    Tokens: {len(tokens)}")
        print(f"    Ratio: {len(tekst)/len(tokens):.2f} karakters/token")

        # Als HF beschikbaar, vergelijk met echte tokenizer
        if HF_BESCHIKBAAR:
            try:
                from transformers import GPT2Tokenizer
                gpt2_tok = GPT2Tokenizer.from_pretrained('gpt2')
                gpt2_tokens = gpt2_tok.tokenize(tekst)
                gpt2_ids = gpt2_tok.encode(tekst)

                print("\n  GPT-2 Tokenizer (ter vergelijking):")
                print(f"    Tokens: {len(gpt2_tokens)}")
                print(f"    {' | '.join(gpt2_tokens[:10])}...")
            except Exception as e:
                logger.debug("GPT-2 tokenizer comparison failed: %s", e)

        input("\n  Druk op Enter...")

    def _embedding_explorer(self):
        """Embedding explorer."""
        clear_scherm()
        print("\n  === EMBEDDING EXPLORER ===\n")

        print("  Embeddings zijn vectorrepresentaties van tekst.")
        print("  Vergelijkbare teksten hebben vergelijkbare embeddings.\n")

        print("  Voer teksten in om te vergelijken (leeg = klaar):")

        teksten = []
        while True:
            tekst = input(f"  Tekst {len(teksten) + 1}: ").strip()
            if not tekst:
                break
            teksten.append(tekst)

        if len(teksten) < 2:
            print("\n  Minimaal 2 teksten nodig!")
            input("\n  Druk op Enter...")
            return

        # Genereer embeddings
        embeddings = [self.embedder.embed(t) for t in teksten]

        print("\n  " + "=" * 50)
        print("  SIMILARITY MATRIX:")
        print("  " + "=" * 50)

        # Header
        header = "        "
        for i in range(len(teksten)):
            header += f"  T{i+1}   "
        print(header)

        # Matrix
        for i, t1 in enumerate(teksten):
            row = f"  T{i+1}  "
            for j, t2 in enumerate(teksten):
                sim = self.embedder.similarity(embeddings[i], embeddings[j])
                row += f" {sim:5.2f} "
            print(row)

        # Meest vergelijkbaar paar
        if len(teksten) > 2:
            best_sim = -1
            best_pair = (0, 1)
            for i in range(len(teksten)):
                for j in range(i + 1, len(teksten)):
                    sim = self.embedder.similarity(embeddings[i], embeddings[j])
                    if sim > best_sim:
                        best_sim = sim
                        best_pair = (i, j)

            print(f"\n  Meest vergelijkbaar: T{best_pair[0]+1} en T{best_pair[1]+1} ({best_sim:.2f})")

        # Toon teksten
        print("\n  Teksten:")
        for i, t in enumerate(teksten, 1):
            print(f"    T{i}: {t[:50]}...")

        input("\n  Druk op Enter...")

    def _prompt_engineering(self):
        """Prompt engineering templates."""
        while True:
            clear_scherm()
            print("\n  === PROMPT ENGINEERING ===\n")

            print("  Templates voor effectieve prompts:\n")

            for i, (key, template) in enumerate(PromptTemplates.TEMPLATES.items(), 1):
                print(f"    {i}. {template['naam']}: {template['beschrijving']}")

            print("\n    0. Terug")

            keuze = input("\n  Keuze: ").strip()

            if keuze == "0":
                break

            try:
                idx = int(keuze) - 1
                keys = list(PromptTemplates.TEMPLATES.keys())
                if 0 <= idx < len(keys):
                    template = PromptTemplates.TEMPLATES[keys[idx]]

                    clear_scherm()
                    print(f"\n  === {template['naam'].upper()} ===\n")
                    print(f"  {template['beschrijving']}\n")
                    print("  Template:")
                    print("  " + "-" * 40)
                    for line in template['template'].split("\n"):
                        print(f"  {line}")
                    print("  " + "-" * 40)

                    if self.generator.anthropic_client:
                        if input("\n  Uitproberen? (j/n): ").lower() == "j":
                            vraag = input("\n  Jouw input: ").strip()

                            if vraag:
                                # Vul template in
                                prompt = template['template'].format(
                                    vraag=vraag,
                                    voorbeelden="[voorbeelden hier]",
                                    rol="expert",
                                    format="JSON",
                                    max_woorden="50"
                                )

                                print("\n  Genereren...")
                                result = self.generator.generate_with_anthropic(prompt)

                                if result:
                                    print("\n  " + "=" * 50)
                                    print("  RESULTAAT:")
                                    print("  " + "=" * 50)
                                    for line in result.split("\n"):
                                        print(f"  {line}")

                    input("\n  Druk op Enter...")

            except (ValueError, IndexError):
                pass

    def _model_benchmark(self):
        """Vergelijk model prestaties."""
        clear_scherm()
        print("\n  === MODEL BENCHMARK ===\n")

        if not self.generator.anthropic_client:
            print("  Vereist: ANTHROPIC_API_KEY")
            input("\n  Druk op Enter...")
            return

        print("  Test verschillende prompt strategieën op dezelfde vraag.\n")

        vraag = input("  Test vraag: ").strip()
        if not vraag:
            return

        strategies = [
            ("Zero-Shot", vraag),
            ("Chain-of-Thought", f"Beantwoord stap voor stap: {vraag}"),
            ("Expert Role", f"Als expert, beantwoord: {vraag}"),
        ]

        results = []

        for naam, prompt in strategies:
            print(f"\n  Testing: {naam}...")
            start = time.time()

            result = self.generator.generate_with_anthropic(
                prompt,
                max_tokens=200
            )

            elapsed = time.time() - start
            results.append({
                "naam": naam,
                "tijd": elapsed,
                "lengte": len(result) if result else 0,
                "result": result
            })

        # Toon resultaten
        print("\n  " + "=" * 50)
        print("  BENCHMARK RESULTATEN:")
        print("  " + "=" * 50)

        for r in results:
            print(f"\n  {r['naam']}:")
            print(f"    Tijd: {r['tijd']:.2f}s")
            print(f"    Output lengte: {r['lengte']} karakters")
            if r['result']:
                preview = r['result'][:100].replace("\n", " ")
                print(f"    Preview: {preview}...")

        input("\n  Druk op Enter...")

    def _statistieken(self):
        """Toon statistieken."""
        clear_scherm()
        print("\n  === ML STUDIO STATISTIEKEN ===\n")

        print(f"  Generaties: {len(self.data.get('generaties', []))}")
        print(f"  RAG Documenten: {len(self.data.get('rag_documenten', []))}")

        print("\n  Backend Status:")
        print(f"    Hugging Face: {'Beschikbaar' if HF_BESCHIKBAAR else 'Niet geinstalleerd'}")
        print(f"    Anthropic: {'Beschikbaar' if self.generator.anthropic_client else 'Niet geconfigureerd'}")

        print(f"\n  Tokenizer:")
        print(f"    Vocabulary: {self.tokenizer.vocab_size()} tokens")

        print(f"\n  Embedder:")
        print(f"    Dimensie: {self.embedder.dim}")

        # Per backend statistieken
        generaties = self.data.get("generaties", [])
        if generaties:
            hf_count = sum(1 for g in generaties if g.get("backend") == "hf")
            anthropic_count = sum(1 for g in generaties if g.get("backend") == "anthropic")

            print(f"\n  Generaties per backend:")
            print(f"    Hugging Face: {hf_count}")
            print(f"    Anthropic: {anthropic_count}")

        input("\n  Druk op Enter...")

    def run(self):
        """Start de app."""
        while True:
            clear_scherm()

            hf_status = "OK" if HF_BESCHIKBAAR else "X"
            anthropic_status = "OK" if self.generator.anthropic_client else "X"

            print(f"""
  ╔═══════════════════════════════════════════════════════════╗
  ║              ADVANCED ML STUDIO v1.0                      ║
  ║         Machine Learning & Text Generation Lab            ║
  ╠═══════════════════════════════════════════════════════════╣
  ║  1. Text Generation                                       ║
  ║  2. Chain-of-Thought Prompting                            ║
  ║  3. RAG Demo (Retrieval-Augmented Generation)             ║
  ║  4. Tokenizer Lab                                         ║
  ║  5. Embedding Explorer                                    ║
  ║  6. Prompt Engineering Templates                          ║
  ║  7. Model Benchmark                                       ║
  ║  8. Statistieken                                          ║
  ║  0. Terug                                                 ║
  ╚═══════════════════════════════════════════════════════════╝
  Backends: HuggingFace [{hf_status}] | Anthropic [{anthropic_status}]
""")
            keuze = input("  Keuze: ").strip()

            if keuze == "0":
                break
            elif keuze == "1":
                self._text_generation()
            elif keuze == "2":
                self._chain_of_thought()
            elif keuze == "3":
                self._rag_demo()
            elif keuze == "4":
                self._tokenizer_lab()
            elif keuze == "5":
                self._embedding_explorer()
            elif keuze == "6":
                self._prompt_engineering()
            elif keuze == "7":
                self._model_benchmark()
            elif keuze == "8":
                self._statistieken()
