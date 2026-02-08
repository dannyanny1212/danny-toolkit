"""
NLP Studio v1.0 - Natuurlijke Taalverwerking & Machine Learning.
Een compleet systeem voor tekstanalyse, classificatie en begrip.
"""

import json
import os
import re
import math
import random
import hashlib
from datetime import datetime
from collections import Counter, defaultdict
from typing import List, Dict, Tuple, Optional
from ..core.config import Config
from ..core.utils import clear_scherm

# AI Integration
try:
    from anthropic import Anthropic
    AI_BESCHIKBAAR = True
except ImportError:
    AI_BESCHIKBAAR = False


# =============================================================================
# NLP KERNCOMPONENTEN
# =============================================================================

class Tokenizer:
    """Tokenisatie van tekst."""

    # Nederlandse stopwoorden
    STOPWOORDEN = {
        "de", "het", "een", "en", "van", "in", "is", "op", "te", "dat",
        "die", "voor", "zijn", "met", "aan", "er", "maar", "om", "ook",
        "als", "dan", "naar", "bij", "of", "uit", "nog", "wel", "geen",
        "moet", "kan", "zou", "dit", "wat", "werd", "worden", "wordt",
        "hebben", "heeft", "had", "zo", "al", "door", "over", "tot",
        "zeer", "meer", "veel", "waar", "nu", "hier", "daar", "hoe",
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to",
        "for", "of", "with", "is", "are", "was", "were", "be", "been",
        "being", "have", "has", "had", "do", "does", "did", "will",
        "would", "could", "should", "may", "might", "must", "shall"
    }

    @staticmethod
    def tokenize(tekst: str) -> List[str]:
        """Splits tekst in tokens (woorden)."""
        # Lowercase en splits op niet-alfanumerieke karakters
        tekst = tekst.lower()
        tokens = re.findall(r'\b[a-zA-Z0-9àáâãäåèéêëìíîïòóôõöùúûüýÿ]+\b', tekst)
        return tokens

    @staticmethod
    def tokenize_zinnen(tekst: str) -> List[str]:
        """Splits tekst in zinnen."""
        # Split op ., !, ? gevolgd door spatie of einde
        zinnen = re.split(r'[.!?]+\s*', tekst)
        return [z.strip() for z in zinnen if z.strip()]

    @classmethod
    def verwijder_stopwoorden(cls, tokens: List[str]) -> List[str]:
        """Verwijder stopwoorden uit tokens."""
        return [t for t in tokens if t.lower() not in cls.STOPWOORDEN]

    @staticmethod
    def ngrams(tokens: List[str], n: int = 2) -> List[Tuple[str, ...]]:
        """Genereer n-grams van tokens."""
        return [tuple(tokens[i:i+n]) for i in range(len(tokens) - n + 1)]


class Stemmer:
    """Simpele Nederlandse/Engelse stemmer."""

    # Suffix regels voor stemming
    SUFFIXEN_NL = [
        ("heid", ""), ("ing", ""), ("lijk", ""), ("isch", ""),
        ("baar", ""), ("achtig", ""), ("eren", ""), ("en", ""),
        ("er", ""), ("te", ""), ("de", ""), ("s", "")
    ]

    SUFFIXEN_EN = [
        ("ation", ""), ("ness", ""), ("ment", ""), ("able", ""),
        ("ible", ""), ("ful", ""), ("less", ""), ("ous", ""),
        ("ive", ""), ("ing", ""), ("ed", ""), ("ly", ""),
        ("er", ""), ("est", ""), ("s", "")
    ]

    @classmethod
    def stem(cls, woord: str, taal: str = "nl") -> str:
        """Reduceer woord tot stam."""
        woord = woord.lower()
        suffixen = cls.SUFFIXEN_NL if taal == "nl" else cls.SUFFIXEN_EN

        for suffix, replacement in suffixen:
            if woord.endswith(suffix) and len(woord) > len(suffix) + 2:
                return woord[:-len(suffix)] + replacement

        return woord

    @classmethod
    def stem_tokens(cls, tokens: List[str], taal: str = "nl") -> List[str]:
        """Stem alle tokens."""
        return [cls.stem(t, taal) for t in tokens]


class POSTagger:
    """Simpele Part-of-Speech tagger gebaseerd op patronen."""

    # Simpele regels voor POS tagging
    PATTERNS = [
        # Werkwoorden
        (r'.*en$', 'VERB'),
        (r'.*ing$', 'VERB'),
        (r'.*ed$', 'VERB'),
        (r'(is|zijn|was|were|be|been|have|has|had|do|does|did)$', 'VERB'),

        # Bijvoeglijke naamwoorden
        (r'.*lijk$', 'ADJ'),
        (r'.*isch$', 'ADJ'),
        (r'.*ig$', 'ADJ'),
        (r'.*baar$', 'ADJ'),
        (r'.*ful$', 'ADJ'),
        (r'.*ous$', 'ADJ'),
        (r'.*ive$', 'ADJ'),

        # Bijwoorden
        (r'.*ly$', 'ADV'),

        # Zelfstandige naamwoorden
        (r'.*heid$', 'NOUN'),
        (r'.*ness$', 'NOUN'),
        (r'.*ment$', 'NOUN'),
        (r'.*tion$', 'NOUN'),
        (r'.*sion$', 'NOUN'),

        # Cijfers
        (r'^\d+$', 'NUM'),
        (r'^\d+[\.,]\d+$', 'NUM'),
    ]

    # Bekende woorden
    KNOWN_WORDS = {
        # Lidwoorden
        "de": "DET", "het": "DET", "een": "DET", "the": "DET", "a": "DET", "an": "DET",
        # Voornaamwoorden
        "ik": "PRON", "jij": "PRON", "hij": "PRON", "zij": "PRON", "wij": "PRON",
        "i": "PRON", "you": "PRON", "he": "PRON", "she": "PRON", "we": "PRON",
        "it": "PRON", "they": "PRON", "me": "PRON", "him": "PRON", "her": "PRON",
        # Voorzetsels
        "in": "PREP", "op": "PREP", "aan": "PREP", "van": "PREP", "voor": "PREP",
        "on": "PREP", "at": "PREP", "to": "PREP", "for": "PREP", "with": "PREP",
        # Voegwoorden
        "en": "CONJ", "of": "CONJ", "maar": "CONJ", "and": "CONJ", "or": "CONJ", "but": "CONJ",
    }

    @classmethod
    def tag(cls, tokens: List[str]) -> List[Tuple[str, str]]:
        """Tag tokens met POS tags."""
        result = []

        for token in tokens:
            token_lower = token.lower()

            # Check bekende woorden
            if token_lower in cls.KNOWN_WORDS:
                result.append((token, cls.KNOWN_WORDS[token_lower]))
                continue

            # Check patronen
            tagged = False
            for pattern, tag in cls.PATTERNS:
                if re.match(pattern, token_lower):
                    result.append((token, tag))
                    tagged = True
                    break

            # Default naar NOUN
            if not tagged:
                result.append((token, "NOUN"))

        return result


class NamedEntityRecognizer:
    """Simpele Named Entity Recognition."""

    # Bekende entiteiten
    PERSONEN = {"jan", "piet", "maria", "john", "mary", "peter", "anna", "danny"}
    LOCATIES = {"amsterdam", "rotterdam", "nederland", "europa", "london", "paris",
                "new york", "berlin", "tokyo", "china", "usa", "uk"}
    ORGANISATIES = {"google", "microsoft", "apple", "amazon", "facebook", "twitter",
                    "ing", "abn", "philips", "shell", "unilever"}

    @classmethod
    def recognize(cls, tokens: List[str]) -> List[Tuple[str, str]]:
        """Herken named entities in tokens."""
        entities = []

        for i, token in enumerate(tokens):
            token_lower = token.lower()

            # Check bekende entiteiten
            if token_lower in cls.PERSONEN:
                entities.append((token, "PERSON"))
            elif token_lower in cls.LOCATIES:
                entities.append((token, "LOCATION"))
            elif token_lower in cls.ORGANISATIES:
                entities.append((token, "ORGANIZATION"))
            # Check voor hoofdletters (potentiele eigennamen)
            elif token[0].isupper() and len(token) > 1:
                entities.append((token, "ENTITY"))
            # Check voor getallen met context
            elif token.isdigit():
                if i > 0 and tokens[i-1].lower() in ["€", "$", "euro", "dollar"]:
                    entities.append((token, "MONEY"))
                elif i > 0 and tokens[i-1].lower() in ["jaar", "jaren", "year", "years"]:
                    entities.append((token, "DATE"))
                else:
                    entities.append((token, "NUMBER"))

        return entities


class SentimentAnalyzer:
    """Sentiment analyse met lexicon-gebaseerde aanpak."""

    # Sentiment lexicon (woord -> score)
    POSITIEF = {
        # Nederlands
        "goed": 2, "mooi": 2, "fantastisch": 3, "geweldig": 3, "uitstekend": 3,
        "leuk": 2, "fijn": 2, "blij": 2, "gelukkig": 3, "tevreden": 2,
        "liefde": 3, "prachtig": 3, "perfect": 3, "super": 3, "top": 2,
        "positief": 2, "succes": 2, "winst": 2, "voordeel": 1, "beter": 1,
        # Engels
        "good": 2, "great": 3, "excellent": 3, "amazing": 3, "wonderful": 3,
        "love": 3, "happy": 2, "joy": 3, "beautiful": 2, "perfect": 3,
        "best": 3, "better": 1, "nice": 2, "awesome": 3, "fantastic": 3,
        "success": 2, "win": 2, "positive": 2, "brilliant": 3
    }

    NEGATIEF = {
        # Nederlands
        "slecht": -2, "lelijk": -2, "verschrikkelijk": -3, "vreselijk": -3,
        "verdrietig": -2, "boos": -2, "kwaad": -2, "teleurgesteld": -2,
        "haat": -3, "pijn": -2, "probleem": -1, "fout": -2, "mis": -1,
        "negatief": -2, "verlies": -2, "nadeel": -1, "slechter": -1,
        "helaas": -1, "jammer": -1, "spijt": -2, "bang": -2,
        # Engels
        "bad": -2, "terrible": -3, "horrible": -3, "awful": -3, "worst": -3,
        "hate": -3, "sad": -2, "angry": -2, "disappointed": -2, "pain": -2,
        "problem": -1, "wrong": -2, "fail": -2, "failure": -2, "loss": -2,
        "negative": -2, "poor": -2, "ugly": -2, "stupid": -2
    }

    INTENSIFIERS = {
        "zeer": 1.5, "heel": 1.5, "erg": 1.5, "super": 1.5, "enorm": 2,
        "very": 1.5, "really": 1.5, "extremely": 2, "incredibly": 2,
        "absoluut": 1.5, "totaal": 1.5, "completely": 1.5
    }

    NEGATIONS = {"niet", "geen", "nooit", "not", "no", "never", "dont", "doesn't", "won't"}

    @classmethod
    def analyze(cls, tekst: str) -> Dict:
        """Analyseer sentiment van tekst."""
        tokens = Tokenizer.tokenize(tekst)

        pos_score = 0
        neg_score = 0
        pos_words = []
        neg_words = []

        negation_active = False
        intensifier = 1.0

        for i, token in enumerate(tokens):
            token_lower = token.lower()

            # Check voor negatie
            if token_lower in cls.NEGATIONS:
                negation_active = True
                continue

            # Check voor intensifier
            if token_lower in cls.INTENSIFIERS:
                intensifier = cls.INTENSIFIERS[token_lower]
                continue

            # Check sentiment
            if token_lower in cls.POSITIEF:
                score = cls.POSITIEF[token_lower] * intensifier
                if negation_active:
                    neg_score += score
                    neg_words.append(f"niet {token}")
                else:
                    pos_score += score
                    pos_words.append(token)
            elif token_lower in cls.NEGATIEF:
                score = abs(cls.NEGATIEF[token_lower]) * intensifier
                if negation_active:
                    pos_score += score
                    pos_words.append(f"niet {token}")
                else:
                    neg_score += score
                    neg_words.append(token)

            # Reset na gebruik
            if token_lower not in cls.INTENSIFIERS:
                intensifier = 1.0
            if token_lower not in cls.NEGATIONS:
                negation_active = False

        # Bereken totale score
        totaal = pos_score - neg_score
        max_score = max(pos_score + neg_score, 1)
        normalized = totaal / max_score

        # Bepaal label
        if normalized > 0.2:
            label = "POSITIEF"
        elif normalized < -0.2:
            label = "NEGATIEF"
        else:
            label = "NEUTRAAL"

        return {
            "label": label,
            "score": normalized,
            "positief_score": pos_score,
            "negatief_score": neg_score,
            "positieve_woorden": pos_words,
            "negatieve_woorden": neg_words,
            "confidence": min(1.0, abs(normalized) + 0.3)
        }


# =============================================================================
# MACHINE LEARNING COMPONENTEN
# =============================================================================

class TFIDFVectorizer:
    """TF-IDF vectorisatie."""

    def __init__(self):
        self.vocabulary = {}
        self.idf = {}
        self.doc_count = 0

    def fit(self, documenten: List[str]):
        """Train de vectorizer op documenten."""
        self.doc_count = len(documenten)
        doc_freq = Counter()

        # Bouw vocabulary en tel document frequenties
        for doc in documenten:
            tokens = set(Tokenizer.tokenize(doc))
            tokens = Tokenizer.verwijder_stopwoorden(list(tokens))

            for token in tokens:
                doc_freq[token] += 1

        # Bereken IDF en bouw vocabulary
        for i, (token, freq) in enumerate(doc_freq.most_common(1000)):
            self.vocabulary[token] = i
            # IDF = log(N / df)
            self.idf[token] = math.log(self.doc_count / (freq + 1)) + 1

    def transform(self, tekst: str) -> List[float]:
        """Transformeer tekst naar TF-IDF vector."""
        tokens = Tokenizer.tokenize(tekst)
        tokens = Tokenizer.verwijder_stopwoorden(tokens)

        # Tel term frequenties
        tf = Counter(tokens)
        max_tf = max(tf.values()) if tf else 1

        # Bouw vector
        vector = [0.0] * len(self.vocabulary)

        for token, count in tf.items():
            if token in self.vocabulary:
                idx = self.vocabulary[token]
                # Normalized TF * IDF
                vector[idx] = (count / max_tf) * self.idf.get(token, 1)

        # L2 normalisatie
        norm = math.sqrt(sum(v**2 for v in vector))
        if norm > 0:
            vector = [v / norm for v in vector]

        return vector

    def fit_transform(self, documenten: List[str]) -> List[List[float]]:
        """Fit en transform in een keer."""
        self.fit(documenten)
        return [self.transform(doc) for doc in documenten]


class NaiveBayesClassifier:
    """Naive Bayes tekst classifier."""

    def __init__(self):
        self.class_counts = Counter()
        self.word_counts = defaultdict(Counter)
        self.vocabulary = set()
        self.total_docs = 0

    def train(self, documenten: List[str], labels: List[str]):
        """Train de classifier."""
        self.fit(documenten, labels)

    def fit(self, documenten: List[str], labels: List[str]):
        """Train de classifier (alias voor train)."""
        self.total_docs = len(documenten)

        for doc, label in zip(documenten, labels):
            self.class_counts[label] += 1

            tokens = Tokenizer.tokenize(doc)
            tokens = Tokenizer.verwijder_stopwoorden(tokens)

            for token in tokens:
                self.word_counts[label][token] += 1
                self.vocabulary.add(token)

    def predict(self, tekst: str) -> Tuple[str, Dict[str, float]]:
        """Voorspel de klasse van een tekst."""
        tokens = Tokenizer.tokenize(tekst)
        tokens = Tokenizer.verwijder_stopwoorden(tokens)

        scores = {}
        vocab_size = len(self.vocabulary)

        for label, count in self.class_counts.items():
            # Prior probability
            score = math.log(count / self.total_docs)

            # Word probabilities met Laplace smoothing
            total_words = sum(self.word_counts[label].values())

            for token in tokens:
                word_count = self.word_counts[label].get(token, 0)
                prob = (word_count + 1) / (total_words + vocab_size)
                score += math.log(prob)

            scores[label] = score

        # Normaliseer naar probabiliteiten
        max_score = max(scores.values())
        probs = {k: math.exp(v - max_score) for k, v in scores.items()}
        total = sum(probs.values())
        probs = {k: v / total for k, v in probs.items()}

        best_label = max(scores, key=scores.get)
        return best_label, probs

    def save(self) -> dict:
        """Exporteer model."""
        return {
            "class_counts": dict(self.class_counts),
            "word_counts": {k: dict(v) for k, v in self.word_counts.items()},
            "vocabulary": list(self.vocabulary),
            "total_docs": self.total_docs
        }

    def load(self, data: dict):
        """Laad model."""
        self.class_counts = Counter(data.get("class_counts", {}))
        self.word_counts = defaultdict(Counter)
        for k, v in data.get("word_counts", {}).items():
            self.word_counts[k] = Counter(v)
        self.vocabulary = set(data.get("vocabulary", []))
        self.total_docs = data.get("total_docs", 0)


class KNNClassifier:
    """K-Nearest Neighbors classifier."""

    def __init__(self, k: int = 3):
        self.k = k
        self.training_data = []
        self.vectorizer = TFIDFVectorizer()

    def train(self, documenten: List[str], labels: List[str]):
        """Train de classifier."""
        self.fit(documenten, labels)

    def fit(self, documenten: List[str], labels: List[str]):
        """Train de classifier (alias voor train)."""
        vectors = self.vectorizer.fit_transform(documenten)
        self.training_data = list(zip(vectors, labels))

    def _cosine_similarity(self, v1: List[float], v2: List[float]) -> float:
        """Bereken cosine similarity."""
        dot = sum(a * b for a, b in zip(v1, v2))
        mag1 = math.sqrt(sum(a**2 for a in v1))
        mag2 = math.sqrt(sum(b**2 for b in v2))
        if mag1 == 0 or mag2 == 0:
            return 0.0
        return dot / (mag1 * mag2)

    def predict(self, tekst: str) -> Tuple[str, float]:
        """Voorspel de klasse."""
        if not self.training_data:
            return "unknown", 0.0

        query_vector = self.vectorizer.transform(tekst)

        # Bereken similarities
        similarities = []
        for vec, label in self.training_data:
            sim = self._cosine_similarity(query_vector, vec)
            similarities.append((sim, label))

        # Sorteer en neem top-k
        similarities.sort(reverse=True)
        top_k = similarities[:self.k]

        # Tel labels
        label_counts = Counter(label for _, label in top_k)
        best_label = label_counts.most_common(1)[0][0]

        # Confidence is gemiddelde similarity van de winnende klasse
        winning_sims = [sim for sim, label in top_k if label == best_label]
        confidence = sum(winning_sims) / len(winning_sims)

        return best_label, confidence


class IntentRecognizer:
    """Intent herkenning voor conversatie."""

    # Ingebouwde intents met voorbeelden
    INTENTS = {
        "begroeting": [
            "hallo", "hoi", "hey", "goedemorgen", "goedemiddag", "hi", "hello"
        ],
        "afscheid": [
            "doei", "dag", "tot ziens", "bye", "goodbye", "later"
        ],
        "vraag": [
            "wat", "wie", "waar", "wanneer", "waarom", "hoe", "what", "who",
            "where", "when", "why", "how", "kun je", "kan je", "weet je"
        ],
        "bedankt": [
            "bedankt", "dankjewel", "thanks", "thank you", "dank", "merci"
        ],
        "hulp": [
            "help", "hulp", "assistentie", "probleem", "issue", "support"
        ],
        "positief": [
            "ja", "yes", "ok", "oke", "prima", "goed", "akkoord", "sure"
        ],
        "negatief": [
            "nee", "no", "niet", "nope", "nooit", "never"
        ]
    }

    def __init__(self):
        self.custom_intents = {}
        self.classifier = NaiveBayesClassifier()
        self._train_builtin()

    def _train_builtin(self):
        """Train op ingebouwde intents."""
        docs = []
        labels = []

        for intent, examples in self.INTENTS.items():
            for example in examples:
                docs.append(example)
                labels.append(intent)

        if docs:
            self.classifier.train(docs, labels)

    def add_intent(self, intent: str, voorbeelden: List[str]):
        """Voeg custom intent toe."""
        self.custom_intents[intent] = voorbeelden

        # Hertrain
        docs = []
        labels = []

        for int_name, examples in {**self.INTENTS, **self.custom_intents}.items():
            for example in examples:
                docs.append(example)
                labels.append(int_name)

        self.classifier.train(docs, labels)

    def recognize(self, tekst: str) -> Tuple[str, float]:
        """Herken intent van tekst."""
        label, probs = self.classifier.predict(tekst)
        confidence = probs.get(label, 0)
        return label, confidence


# =============================================================================
# HOOFDAPPLICATIE
# =============================================================================

class NLPStudioApp:
    """NLP Studio - Natuurlijke Taalverwerking & Machine Learning."""

    VERSIE = "1.0"

    def __init__(self):
        Config.ensure_dirs()
        self.bestand = Config.APPS_DATA_DIR / "nlp_studio.json"
        self.data = self._laad_data()

        # Componenten
        self.tokenizer = Tokenizer()
        self.stemmer = Stemmer()
        self.pos_tagger = POSTagger()
        self.ner = NamedEntityRecognizer()
        self.sentiment = SentimentAnalyzer()
        self.vectorizer = TFIDFVectorizer()
        self.intent_recognizer = IntentRecognizer()

        # Classifiers
        self.nb_classifier = NaiveBayesClassifier()
        self.knn_classifier = KNNClassifier()

        # Laad getrainde modellen
        self._laad_modellen()

        # AI
        self.client = None
        self._init_ai()

    def _init_ai(self):
        """Initialiseer AI client."""
        if AI_BESCHIKBAAR:
            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if api_key:
                try:
                    self.client = Anthropic(api_key=api_key)
                except Exception:
                    self.client = None

    def _ai_request(self, prompt: str, max_tokens: int = 500) -> str:
        """Maak een AI request."""
        if not self.client:
            return None
        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text
        except Exception:
            return None

    def _laad_data(self) -> dict:
        """Laad data."""
        if self.bestand.exists():
            try:
                with open(self.bestand, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return {
            "modellen": {},
            "training_data": {},
            "analyses": [],
            "stats": {
                "teksten_geanalyseerd": 0,
                "modellen_getraind": 0
            }
        }

    def _sla_op(self):
        """Sla data op."""
        with open(self.bestand, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)

    def _laad_modellen(self):
        """Laad getrainde modellen."""
        if "nb_classifier" in self.data.get("modellen", {}):
            self.nb_classifier.load(self.data["modellen"]["nb_classifier"])

    def _sla_modellen_op(self):
        """Sla getrainde modellen op."""
        self.data["modellen"]["nb_classifier"] = self.nb_classifier.save()
        self._sla_op()

    def run(self):
        """Start de app."""
        while True:
            clear_scherm()
            self._toon_header()
            self._toon_menu()

            keuze = input("\nKeuze: ").strip()

            if keuze == "0":
                break
            elif keuze == "1":
                self._tekst_analyse()
            elif keuze == "2":
                self._sentiment_analyse()
            elif keuze == "3":
                self._entity_herkenning()
            elif keuze == "4":
                self._keyword_extractie()
            elif keuze == "5":
                self._tekst_classificatie()
            elif keuze == "6":
                self._train_classifier()
            elif keuze == "7":
                self._intent_herkenning()
            elif keuze == "8":
                self._tekst_vergelijking()
            elif keuze == "9":
                self._ai_analyse()

            input("\nDruk op Enter...")

    def _toon_header(self):
        """Toon header."""
        print("+" + "=" * 54 + "+")
        print("|             NLP STUDIO v1.0                          |")
        print("|    Natuurlijke Taalverwerking & Machine Learning     |")
        if self.client:
            print("|                 [AI POWERED]                         |")
        print("+" + "=" * 54 + "+")

        stats = self.data["stats"]
        print(f"|  Geanalyseerd: {stats['teksten_geanalyseerd']:<8} "
              f"Modellen: {stats['modellen_getraind']:<12}|")

    def _toon_menu(self):
        """Toon menu."""
        print("+" + "-" * 54 + "+")
        print("|  [ANALYSE]                                           |")
        print("|  1. Tekst Analyse (tokens, POS, stats)               |")
        print("|  2. Sentiment Analyse                                |")
        print("|  3. Entity Herkenning (NER)                          |")
        print("|  4. Keyword Extractie                                |")
        print("+" + "-" * 54 + "+")
        print("|  [MACHINE LEARNING]                                  |")
        print("|  5. Tekst Classificatie                              |")
        print("|  6. Train Classifier                                 |")
        print("|  7. Intent Herkenning                                |")
        print("|  8. Tekst Vergelijking (Similarity)                  |")
        print("+" + "-" * 54 + "+")
        print("|  [AI]                                                |")
        print("|  9. AI Tekst Analyse                                 |")
        print("+" + "-" * 54 + "+")
        print("|  0. Terug                                            |")
        print("+" + "=" * 54 + "+")

    # =========================================================================
    # ANALYSE FUNCTIES
    # =========================================================================

    def _tekst_analyse(self):
        """Volledige tekst analyse."""
        print("\n--- TEKST ANALYSE ---")

        tekst = input("\nVoer tekst in: ").strip()
        if not tekst:
            return

        print("\n" + "=" * 50)
        print("ANALYSE RESULTATEN")
        print("=" * 50)

        # Basis statistieken
        print("\n[Statistieken]")
        zinnen = Tokenizer.tokenize_zinnen(tekst)
        tokens = Tokenizer.tokenize(tekst)
        woorden_uniek = set(tokens)

        print(f"  Karakters: {len(tekst)}")
        print(f"  Woorden: {len(tokens)}")
        print(f"  Unieke woorden: {len(woorden_uniek)}")
        print(f"  Zinnen: {len(zinnen)}")
        print(f"  Gem. woorden/zin: {len(tokens) / max(1, len(zinnen)):.1f}")

        # Tokens
        print(f"\n[Tokens] (eerste 15)")
        print(f"  {', '.join(tokens[:15])}")
        if len(tokens) > 15:
            print(f"  ... en {len(tokens) - 15} meer")

        # POS Tagging
        print(f"\n[POS Tags]")
        pos_tags = self.pos_tagger.tag(tokens[:10])
        for token, tag in pos_tags:
            print(f"  {token:<15} -> {tag}")
        if len(tokens) > 10:
            print(f"  ... en {len(tokens) - 10} meer")

        # Stemming
        print(f"\n[Stemming] (voorbeelden)")
        for token in tokens[:5]:
            stem = self.stemmer.stem(token)
            if stem != token:
                print(f"  {token} -> {stem}")

        # N-grams
        print(f"\n[Bigrams] (top 5)")
        bigrams = Tokenizer.ngrams(tokens, 2)
        bigram_counts = Counter(bigrams)
        for bigram, count in bigram_counts.most_common(5):
            print(f"  \"{' '.join(bigram)}\" ({count}x)")

        self.data["stats"]["teksten_geanalyseerd"] += 1
        self._sla_op()

    def _sentiment_analyse(self):
        """Sentiment analyse."""
        print("\n--- SENTIMENT ANALYSE ---")

        tekst = input("\nVoer tekst in: ").strip()
        if not tekst:
            return

        result = self.sentiment.analyze(tekst)

        print("\n" + "=" * 50)
        print("SENTIMENT RESULTATEN")
        print("=" * 50)

        # Visuele score
        score = result["score"]
        bar_pos = int(max(0, score) * 10)
        bar_neg = int(max(0, -score) * 10)

        print(f"\n  Negatief {'█' * bar_neg}{'░' * (10 - bar_neg)} | "
              f"{'░' * (10 - bar_pos)}{'█' * bar_pos} Positief")

        print(f"\n  Label: {result['label']}")
        print(f"  Score: {score:+.2f} (-1 tot +1)")
        print(f"  Confidence: {result['confidence']:.0%}")

        print(f"\n  Positieve score: +{result['positief_score']:.1f}")
        if result["positieve_woorden"]:
            print(f"    Woorden: {', '.join(result['positieve_woorden'][:5])}")

        print(f"\n  Negatieve score: -{result['negatief_score']:.1f}")
        if result["negatieve_woorden"]:
            print(f"    Woorden: {', '.join(result['negatieve_woorden'][:5])}")

        self.data["stats"]["teksten_geanalyseerd"] += 1
        self._sla_op()

    def _entity_herkenning(self):
        """Named Entity Recognition."""
        print("\n--- ENTITY HERKENNING (NER) ---")

        tekst = input("\nVoer tekst in: ").strip()
        if not tekst:
            return

        tokens = Tokenizer.tokenize(tekst)
        entities = self.ner.recognize(tokens)

        print("\n" + "=" * 50)
        print("GEVONDEN ENTITIES")
        print("=" * 50)

        if not entities:
            print("\n  Geen entities gevonden.")
        else:
            # Groepeer per type
            by_type = defaultdict(list)
            for entity, etype in entities:
                by_type[etype].append(entity)

            for etype, ents in by_type.items():
                print(f"\n  [{etype}]")
                for e in ents:
                    print(f"    - {e}")

        self.data["stats"]["teksten_geanalyseerd"] += 1
        self._sla_op()

    def _keyword_extractie(self):
        """Keyword extractie met TF-IDF."""
        print("\n--- KEYWORD EXTRACTIE ---")

        tekst = input("\nVoer tekst in: ").strip()
        if not tekst:
            return

        # Tokenize en verwijder stopwoorden
        tokens = Tokenizer.tokenize(tekst)
        tokens = Tokenizer.verwijder_stopwoorden(tokens)

        # Tel frequenties
        freq = Counter(tokens)

        # Bereken simpele TF-IDF scores
        scores = {}
        for token, count in freq.items():
            tf = count / len(tokens)
            # Simpele IDF schatting gebaseerd op woordlengte en frequentie
            idf = math.log(len(tokens) / (count + 1)) + 1
            scores[token] = tf * idf

        # Sorteer op score
        keywords = sorted(scores.items(), key=lambda x: -x[1])

        print("\n" + "=" * 50)
        print("KEYWORDS (top 10)")
        print("=" * 50)

        for word, score in keywords[:10]:
            bar = "█" * int(score * 20)
            print(f"  {word:<20} {bar} ({score:.3f})")

        self.data["stats"]["teksten_geanalyseerd"] += 1
        self._sla_op()

    # =========================================================================
    # MACHINE LEARNING FUNCTIES
    # =========================================================================

    def _tekst_classificatie(self):
        """Classificeer tekst met getraind model."""
        print("\n--- TEKST CLASSIFICATIE ---")

        if self.nb_classifier.total_docs == 0:
            print("\n[!] Geen getraind model. Train eerst via optie 6.")
            return

        tekst = input("\nVoer tekst in om te classificeren: ").strip()
        if not tekst:
            return

        label, probs = self.nb_classifier.predict(tekst)

        print("\n" + "=" * 50)
        print("CLASSIFICATIE RESULTATEN")
        print("=" * 50)

        print(f"\n  Voorspelde klasse: {label}")
        print(f"\n  Waarschijnlijkheden:")

        for klasse, prob in sorted(probs.items(), key=lambda x: -x[1]):
            bar = "█" * int(prob * 30)
            print(f"    {klasse:<15} {bar} {prob:.1%}")

        self.data["stats"]["teksten_geanalyseerd"] += 1
        self._sla_op()

    def _train_classifier(self):
        """Train een classifier."""
        print("\n--- TRAIN CLASSIFIER ---")

        print("\n  1. Nieuw model trainen")
        print("  2. Voorbeelden toevoegen aan bestaand model")
        print("  3. Demo model laden (sentiment)")

        keuze = input("\nKeuze: ").strip()

        if keuze == "1":
            self._train_nieuw_model()
        elif keuze == "2":
            self._voeg_training_data_toe()
        elif keuze == "3":
            self._laad_demo_model()

    def _train_nieuw_model(self):
        """Train nieuw model."""
        print("\n[Nieuw Model Trainen]")
        print("\nVoer training data in:")
        print("Format: <label>: <tekst>")
        print("Typ 'klaar' om te stoppen\n")

        documenten = []
        labels = []

        while True:
            invoer = input("> ").strip()
            if invoer.lower() == "klaar":
                break

            if ":" in invoer:
                label, tekst = invoer.split(":", 1)
                labels.append(label.strip())
                documenten.append(tekst.strip())
                print(f"  [+] Toegevoegd: {label.strip()}")

        if len(documenten) < 2:
            print("\n[!] Minimaal 2 voorbeelden nodig.")
            return

        self.nb_classifier.train(documenten, labels)
        self._sla_modellen_op()

        self.data["stats"]["modellen_getraind"] += 1
        self._sla_op()

        print(f"\n[OK] Model getraind met {len(documenten)} voorbeelden!")
        print(f"     Klassen: {', '.join(set(labels))}")

    def _voeg_training_data_toe(self):
        """Voeg extra training data toe."""
        if self.nb_classifier.total_docs == 0:
            print("\n[!] Geen bestaand model. Maak eerst een nieuw model.")
            return

        print("\n[Training Data Toevoegen]")
        print(f"Bestaande klassen: {', '.join(self.nb_classifier.class_counts.keys())}")
        print("\nFormat: <label>: <tekst>")
        print("Typ 'klaar' om te stoppen\n")

        documenten = []
        labels = []

        while True:
            invoer = input("> ").strip()
            if invoer.lower() == "klaar":
                break

            if ":" in invoer:
                label, tekst = invoer.split(":", 1)
                labels.append(label.strip())
                documenten.append(tekst.strip())

        if documenten:
            # Voeg toe aan bestaande data en hertrain
            alle_docs = []
            alle_labels = []

            # Bestaande data (uit word counts reconstrueren is niet ideaal,
            # maar voor demo doeleinden)
            for label, words in self.nb_classifier.word_counts.items():
                for word, count in words.items():
                    for _ in range(count):
                        alle_docs.append(word)
                        alle_labels.append(label)

            alle_docs.extend(documenten)
            alle_labels.extend(labels)

            self.nb_classifier.train(alle_docs, alle_labels)
            self._sla_modellen_op()

            print(f"\n[OK] {len(documenten)} voorbeelden toegevoegd!")

    def _laad_demo_model(self):
        """Laad demo sentiment model."""
        print("\n[Demo Model Laden]")

        # Demo training data
        pos_teksten = [
            "Dit is geweldig en fantastisch",
            "Ik ben heel blij en gelukkig",
            "Wat een mooie dag",
            "Super goed gedaan",
            "Uitstekend werk",
            "Ik hou hiervan",
            "Perfecte oplossing",
            "Heel tevreden"
        ]

        neg_teksten = [
            "Dit is verschrikkelijk slecht",
            "Ik ben heel verdrietig",
            "Wat een vreselijke situatie",
            "Heel teleurgesteld",
            "Slechte ervaring",
            "Ik haat dit",
            "Grote fout",
            "Heel ontevreden"
        ]

        documenten = pos_teksten + neg_teksten
        labels = ["positief"] * len(pos_teksten) + ["negatief"] * len(neg_teksten)

        self.nb_classifier.train(documenten, labels)
        self._sla_modellen_op()

        self.data["stats"]["modellen_getraind"] += 1
        self._sla_op()

        print(f"\n[OK] Demo model geladen!")
        print(f"     {len(documenten)} voorbeelden (positief/negatief)")

    def _intent_herkenning(self):
        """Intent herkenning."""
        print("\n--- INTENT HERKENNING ---")

        print("\nIngebouwde intents:")
        for intent in self.intent_recognizer.INTENTS:
            print(f"  - {intent}")

        tekst = input("\nVoer tekst in: ").strip()
        if not tekst:
            return

        intent, confidence = self.intent_recognizer.recognize(tekst)

        print("\n" + "=" * 50)
        print("INTENT RESULTATEN")
        print("=" * 50)

        print(f"\n  Tekst: \"{tekst}\"")
        print(f"  Intent: {intent}")
        print(f"  Confidence: {confidence:.0%}")

        # Toon voorbeelden van herkende intent
        if intent in self.intent_recognizer.INTENTS:
            voorbeelden = self.intent_recognizer.INTENTS[intent][:3]
            print(f"\n  Voorbeelden van '{intent}':")
            for v in voorbeelden:
                print(f"    - {v}")

        self.data["stats"]["teksten_geanalyseerd"] += 1
        self._sla_op()

    def _tekst_vergelijking(self):
        """Vergelijk teksten op similarity."""
        print("\n--- TEKST VERGELIJKING ---")

        print("\nVoer twee teksten in om te vergelijken:")
        tekst1 = input("Tekst 1: ").strip()
        tekst2 = input("Tekst 2: ").strip()

        if not tekst1 or not tekst2:
            return

        # Train vectorizer op beide teksten
        self.vectorizer.fit([tekst1, tekst2])
        vec1 = self.vectorizer.transform(tekst1)
        vec2 = self.vectorizer.transform(tekst2)

        # Bereken cosine similarity
        dot = sum(a * b for a, b in zip(vec1, vec2))
        mag1 = math.sqrt(sum(a**2 for a in vec1))
        mag2 = math.sqrt(sum(b**2 for b in vec2))
        similarity = dot / (mag1 * mag2) if mag1 > 0 and mag2 > 0 else 0

        print("\n" + "=" * 50)
        print("VERGELIJKING RESULTATEN")
        print("=" * 50)

        bar = "█" * int(similarity * 30)
        print(f"\n  Similarity: {bar} {similarity:.1%}")

        if similarity > 0.8:
            print("  Interpretatie: Zeer vergelijkbaar")
        elif similarity > 0.5:
            print("  Interpretatie: Redelijk vergelijkbaar")
        elif similarity > 0.2:
            print("  Interpretatie: Enigszins vergelijkbaar")
        else:
            print("  Interpretatie: Weinig overeenkomst")

        # Toon gemeenschappelijke woorden
        tokens1 = set(Tokenizer.tokenize(tekst1))
        tokens2 = set(Tokenizer.tokenize(tekst2))
        gemeenschappelijk = tokens1 & tokens2

        if gemeenschappelijk:
            print(f"\n  Gemeenschappelijke woorden: {', '.join(list(gemeenschappelijk)[:10])}")

        self.data["stats"]["teksten_geanalyseerd"] += 1
        self._sla_op()

    # =========================================================================
    # AI FUNCTIES
    # =========================================================================

    def _ai_analyse(self):
        """AI-powered tekst analyse."""
        print("\n--- AI TEKST ANALYSE ---")

        if not self.client:
            print("\n[!] AI niet beschikbaar.")
            print("    Set ANTHROPIC_API_KEY voor AI functies.")
            return

        tekst = input("\nVoer tekst in voor AI analyse: ").strip()
        if not tekst:
            return

        print("\n[AI analyseert...]")

        prompt = f"""Analyseer de volgende tekst grondig:

"{tekst}"

Geef een analyse met:
1. Samenvatting (1-2 zinnen)
2. Sentiment (positief/negatief/neutraal met uitleg)
3. Belangrijkste thema's/onderwerpen
4. Taalgebruik en stijl
5. Eventuele entiteiten (personen, locaties, organisaties)

Antwoord in het Nederlands, gestructureerd en beknopt."""

        response = self._ai_request(prompt, max_tokens=600)

        if response:
            print("\n" + "=" * 50)
            print("AI ANALYSE")
            print("=" * 50)
            print(f"\n{response}")
        else:
            print("\n[!] AI analyse mislukt.")

        self.data["stats"]["teksten_geanalyseerd"] += 1
        self._sla_op()
