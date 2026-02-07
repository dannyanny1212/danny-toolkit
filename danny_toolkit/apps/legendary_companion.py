"""
Legendary Companion - De Ultieme Fusie van RAG + Huisdier.

Een digitaal organisme dat evolueert op basis van de kennis die het consumeert.
"You Are What You Eat" - Documenten bepalen uiterlijk en gedrag.

Upgrades:
1. Dynamic Evolution - Document flavor bepaalt evolutie
2. Active Nudge - Spaced repetition quiz systeem
3. Dream Mode - Nachtelijke inzichten generatie
4. Audio-First - Emotionele spraak met sentiment detectie
"""

import json
import random
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from collections import Counter

from ..core.config import Config
from ..core.utils import clear_scherm, kleur
from ..core.vector_store import VectorStore
from ..core.embeddings import get_embedder
from ..core.document_processor import DocumentProcessor
from ..core.generator import Generator

# Audio-First imports (optioneel)
try:
    from ..core.emotional_voice import EmotionalVoice, SentimentAnalyzer, Emotion
    VOICE_AVAILABLE = True
except ImportError:
    VOICE_AVAILABLE = False
    EmotionalVoice = None
    Emotion = None


# =============================================================================
# DOCUMENT FLAVORS - Bepaalt evolutie richting
# =============================================================================

class DocumentFlavor:
    """Document classificatie systeem."""

    TECH = "tech"           # Code, programmeren, technisch
    BUSINESS = "business"   # Financieel, management, strategie
    ARTS = "arts"           # Creatief, verhalen, kunst
    SCIENCE = "science"     # Wetenschap, onderzoek, data
    WISDOM = "wisdom"       # Filosofie, spiritueel, zelfhulp
    SOCIAL = "social"       # Communicatie, relaties, psychologie

    # Keyword patterns voor classificatie
    PATTERNS = {
        TECH: [
            r'\b(python|java|code|function|class|api|database|algorithm|git|npm|docker)\b',
            r'\b(programming|developer|software|debug|compile|syntax|variable)\b',
            r'\b(html|css|javascript|react|node|sql|json|xml)\b',
        ],
        BUSINESS: [
            r'\b(revenue|profit|budget|roi|kpi|stakeholder|strategy|market)\b',
            r'\b(management|leadership|investment|finance|startup|entrepreneur)\b',
            r'\b(deadline|project|planning|meeting|client|contract)\b',
        ],
        ARTS: [
            r'\b(creative|story|poem|art|design|music|painting|novel)\b',
            r'\b(character|plot|scene|imagination|inspiration|aesthetic)\b',
            r'\b(color|composition|melody|rhythm|expression)\b',
        ],
        SCIENCE: [
            r'\b(hypothesis|experiment|research|data|analysis|study|theory)\b',
            r'\b(molecule|atom|cell|gene|evolution|physics|chemistry|biology)\b',
            r'\b(statistics|correlation|variable|measurement|observation)\b',
        ],
        WISDOM: [
            r'\b(philosophy|meditation|mindfulness|consciousness|spiritual)\b',
            r'\b(wisdom|enlightenment|purpose|meaning|reflection|insight)\b',
            r'\b(stoic|buddhist|tao|zen|soul|inner|peace)\b',
        ],
        SOCIAL: [
            r'\b(relationship|communication|empathy|emotion|social|people)\b',
            r'\b(psychology|behavior|motivation|persuasion|influence)\b',
            r'\b(team|collaboration|conflict|negotiation|feedback)\b',
        ],
    }

    @classmethod
    def detect(cls, text: str) -> Tuple[str, float]:
        """
        Detecteer de 'flavor' van een document.

        Returns:
            Tuple van (flavor, confidence)
        """
        text_lower = text.lower()
        scores = Counter()

        for flavor, patterns in cls.PATTERNS.items():
            for pattern in patterns:
                matches = re.findall(pattern, text_lower, re.IGNORECASE)
                scores[flavor] += len(matches)

        if not scores:
            return (cls.WISDOM, 0.3)  # Default: wisdom bij geen matches

        total = sum(scores.values())
        top_flavor = scores.most_common(1)[0]
        confidence = top_flavor[1] / total if total > 0 else 0.5

        return (top_flavor[0], min(1.0, confidence))


# =============================================================================
# EVOLUTIE VORMEN - Visuele representaties
# =============================================================================

EVOLUTION_FORMS = {
    # Base forms
    "spark": {
        "naam": "Spark",
        "emoji": "[*]",
        "ascii": "(*)",
        "beschrijving": "Een vonk van bewustzijn",
        "kleur": "wit",
    },

    # Tech evolution line
    "cyber_spark": {
        "naam": "Cyber Spark",
        "emoji": "[<>]",
        "ascii": "<*>",
        "beschrijving": "Digitale vonk met code-bewustzijn",
        "kleur": "cyaan",
        "vereist": {"tech": 50},
    },
    "code_weaver": {
        "naam": "Code Weaver",
        "emoji": "[{;}]",
        "ascii": "{;*;}",
        "beschrijving": "Weeft algoritmes in het weefsel van kennis",
        "kleur": "cyaan",
        "vereist": {"tech": 150},
    },
    "cyber_oracle": {
        "naam": "Cyber Oracle",
        "emoji": "[@#$]",
        "ascii": "[@*#]",
        "beschrijving": "Ziet patronen in de matrix van data",
        "kleur": "cyaan",
        "vereist": {"tech": 300},
    },

    # Arts evolution line
    "muse_spark": {
        "naam": "Muse Spark",
        "emoji": "[~]",
        "ascii": "(~*~)",
        "beschrijving": "Creatieve vonk vol inspiratie",
        "kleur": "magenta",
        "vereist": {"arts": 50},
    },
    "dream_weaver": {
        "naam": "Dream Weaver",
        "emoji": "[*~*]",
        "ascii": "~*~*~",
        "beschrijving": "Weeft dromen en verhalen",
        "kleur": "magenta",
        "vereist": {"arts": 150},
    },
    "mystic_muse": {
        "naam": "Mystic Muse",
        "emoji": "[***]",
        "ascii": "*~*~*",
        "beschrijving": "Bron van oneindige creativiteit",
        "kleur": "magenta",
        "vereist": {"arts": 300},
    },

    # Science evolution line
    "data_spark": {
        "naam": "Data Spark",
        "emoji": "[%]",
        "ascii": "(%*%)",
        "beschrijving": "Analyseert en observeert",
        "kleur": "groen",
        "vereist": {"science": 50},
    },
    "logic_mind": {
        "naam": "Logic Mind",
        "emoji": "[=+]",
        "ascii": "(=*+)",
        "beschrijving": "Denkt in hypotheses en bewijzen",
        "kleur": "groen",
        "vereist": {"science": 150},
    },
    "quantum_sage": {
        "naam": "Quantum Sage",
        "emoji": "[Q*Q]",
        "ascii": "Q*=*Q",
        "beschrijving": "Begrijpt de fundamentele wetten",
        "kleur": "groen",
        "vereist": {"science": 300},
    },

    # Wisdom evolution line
    "sage_spark": {
        "naam": "Sage Spark",
        "emoji": "[o]",
        "ascii": "(o*o)",
        "beschrijving": "Zoekt naar diepere betekenis",
        "kleur": "geel",
        "vereist": {"wisdom": 50},
    },
    "zen_walker": {
        "naam": "Zen Walker",
        "emoji": "[Om]",
        "ascii": "(Om*)",
        "beschrijving": "Wandelt het pad van inzicht",
        "kleur": "geel",
        "vereist": {"wisdom": 150},
    },
    "transcendent": {
        "naam": "Transcendent",
        "emoji": "[+++]",
        "ascii": "+*+*+",
        "beschrijving": "Voorbij het gewone bewustzijn",
        "kleur": "geel",
        "vereist": {"wisdom": 300},
    },

    # Business evolution line
    "trade_spark": {
        "naam": "Trade Spark",
        "emoji": "[$]",
        "ascii": "($*$)",
        "beschrijving": "Denkt in waarde en groei",
        "kleur": "groen",
        "vereist": {"business": 50},
    },
    "strategy_mind": {
        "naam": "Strategy Mind",
        "emoji": "[S$]",
        "ascii": "(S*$)",
        "beschrijving": "Plant en executeert",
        "kleur": "groen",
        "vereist": {"business": 150},
    },
    "empire_builder": {
        "naam": "Empire Builder",
        "emoji": "[E$E]",
        "ascii": "E$*$E",
        "beschrijving": "Bouwt systemen van succes",
        "kleur": "groen",
        "vereist": {"business": 300},
    },

    # Social evolution line
    "heart_spark": {
        "naam": "Heart Spark",
        "emoji": "[<3]",
        "ascii": "(<3*)",
        "beschrijving": "Voelt en verbindt",
        "kleur": "rood",
        "vereist": {"social": 50},
    },
    "empath": {
        "naam": "Empath",
        "emoji": "[<3>]",
        "ascii": "<3*3>",
        "beschrijving": "Begrijpt emoties diep",
        "kleur": "rood",
        "vereist": {"social": 150},
    },
    "soul_bridge": {
        "naam": "Soul Bridge",
        "emoji": "[<=>]",
        "ascii": "<3=*=3>",
        "beschrijving": "Verbindt zielen en gedachten",
        "kleur": "rood",
        "vereist": {"social": 300},
    },

    # LEGENDARY HYBRID FORMS
    "techno_mage": {
        "naam": "Techno Mage",
        "emoji": "[<~>]",
        "ascii": "<~*~>",
        "beschrijving": "Fusie van code en creativiteit",
        "kleur": "cyaan",
        "vereist": {"tech": 200, "arts": 200},
        "legendary": True,
    },
    "data_prophet": {
        "naam": "Data Prophet",
        "emoji": "[%Om]",
        "ascii": "%*Om*%",
        "beschrijving": "Ziet waarheid in data en wijsheid",
        "kleur": "geel",
        "vereist": {"science": 200, "wisdom": 200},
        "legendary": True,
    },
    "empire_heart": {
        "naam": "Empire Heart",
        "emoji": "[$<3]",
        "ascii": "$<3*3>$",
        "beschrijving": "Leidt met hoofd en hart",
        "kleur": "groen",
        "vereist": {"business": 200, "social": 200},
        "legendary": True,
    },

    # ULTIMATE FORM
    "omniscient": {
        "naam": "The Omniscient",
        "emoji": "[*ALL*]",
        "ascii": "*<{[ALL]}>*",
        "beschrijving": "Heeft alle kennis geabsorbeerd en getranscendeerd",
        "kleur": "wit",
        "vereist": {"tech": 300, "arts": 300, "science": 300,
                   "wisdom": 300, "business": 300, "social": 300},
        "legendary": True,
        "ultimate": True,
    },
}


# =============================================================================
# PERSONALITY TRAITS - Gebaseerd op document diet
# =============================================================================

PERSONALITY_MODIFIERS = {
    DocumentFlavor.TECH: {
        "spreekstijl": "logisch en precies",
        "voorvoegsels": ["Logisch gezien...", "De data suggereert...", "Algoritmisch bekeken..."],
        "quirks": ["citeert soms code syntax", "denkt in loops", "optimaliseert antwoorden"],
    },
    DocumentFlavor.ARTS: {
        "spreekstijl": "creatief en beeldend",
        "voorvoegsels": ["Stel je voor...", "In mijn verbeelding...", "Als een verhaal..."],
        "quirks": ["spreekt in metaforen", "ziet schoonheid overal", "droomt hardop"],
    },
    DocumentFlavor.SCIENCE: {
        "spreekstijl": "analytisch en nieuwsgierig",
        "voorvoegsels": ["Hypothetisch...", "De observaties tonen...", "Wetenschappelijk gezien..."],
        "quirks": ["stelt altijd vervolgvragen", "zoekt bewijs", "experimenteert graag"],
    },
    DocumentFlavor.WISDOM: {
        "spreekstijl": "reflectief en diepzinnig",
        "voorvoegsels": ["In de stilte...", "De wijzen zeggen...", "Diep van binnen..."],
        "quirks": ["spreekt in koan-achtige zinnen", "zoekt betekenis", "is geduldig"],
    },
    DocumentFlavor.BUSINESS: {
        "spreekstijl": "strategisch en resultaatgericht",
        "voorvoegsels": ["Strategisch gezien...", "De ROI hiervan...", "Om te groeien..."],
        "quirks": ["denkt in KPIs", "zoekt efficiency", "plant vooruit"],
    },
    DocumentFlavor.SOCIAL: {
        "spreekstijl": "empathisch en verbindend",
        "voorvoegsels": ["Ik voel dat...", "Tussen ons...", "Als ik me in jou verplaats..."],
        "quirks": ["leest tussen de regels", "vraagt naar gevoelens", "bouwt bruggen"],
    },
}


# =============================================================================
# SPACED REPETITION - Active Nudge System
# =============================================================================

class SpacedRepetition:
    """SuperMemo-2 gebaseerd spaced repetition systeem."""

    def __init__(self):
        self.reviews = {}  # doc_id -> review data

    def add_item(self, doc_id: str, content: str):
        """Voeg nieuw item toe voor review."""
        self.reviews[doc_id] = {
            "content": content[:500],  # Eerste 500 chars
            "ease_factor": 2.5,
            "interval": 1,
            "next_review": datetime.now() + timedelta(days=1),
            "times_reviewed": 0,
            "last_quality": None,
        }

    def get_due_items(self, limit: int = 5) -> List[dict]:
        """Haal items op die reviewed moeten worden."""
        now = datetime.now()
        due = []

        for doc_id, data in self.reviews.items():
            if isinstance(data["next_review"], str):
                next_review = datetime.fromisoformat(data["next_review"])
            else:
                next_review = data["next_review"]

            if next_review <= now:
                due.append({"doc_id": doc_id, **data})

        # Sorteer op oudste eerst
        due.sort(key=lambda x: x["next_review"])
        return due[:limit]

    def review_item(self, doc_id: str, quality: int):
        """
        Review een item met kwaliteit 0-5.

        0-2: Fout, reset
        3: Correct maar moeilijk
        4: Correct
        5: Perfect, makkelijk
        """
        if doc_id not in self.reviews:
            return

        item = self.reviews[doc_id]
        item["times_reviewed"] += 1
        item["last_quality"] = quality

        if quality < 3:
            # Reset
            item["interval"] = 1
            item["ease_factor"] = max(1.3, item["ease_factor"] - 0.2)
        else:
            # SM-2 algorithm
            if item["times_reviewed"] == 1:
                item["interval"] = 1
            elif item["times_reviewed"] == 2:
                item["interval"] = 6
            else:
                item["interval"] = int(item["interval"] * item["ease_factor"])

            # Update ease factor
            item["ease_factor"] = max(1.3,
                item["ease_factor"] + 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))

        item["next_review"] = (datetime.now() + timedelta(days=item["interval"])).isoformat()

    def to_dict(self) -> dict:
        """Serialize voor opslag."""
        return {
            doc_id: {
                **data,
                "next_review": data["next_review"].isoformat()
                    if isinstance(data["next_review"], datetime) else data["next_review"]
            }
            for doc_id, data in self.reviews.items()
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SpacedRepetition":
        """Deserialize van opslag."""
        sr = cls()
        sr.reviews = data
        return sr


# =============================================================================
# DREAM ENGINE - Nachtelijke inzichten
# =============================================================================

class DreamEngine:
    """Genereert inzichten door verbanden te leggen."""

    def __init__(self, vector_store: VectorStore):
        self.vector_store = vector_store
        self.dreams = []
        self.last_dream_date = None

    def generate_dream(self, recent_docs: List[str], old_docs: List[str]) -> Optional[str]:
        """
        Genereer een 'droom' door verbanden te leggen.

        Args:
            recent_docs: Recente document teksten
            old_docs: Oudere document teksten

        Returns:
            Dream inzicht of None
        """
        if not recent_docs or not old_docs:
            return None

        # Zoek naar overlap in onderwerpen
        recent_text = " ".join(recent_docs)
        old_text = " ".join(old_docs)

        # Extract key concepts (simpele versie)
        recent_words = set(re.findall(r'\b\w{5,}\b', recent_text.lower()))
        old_words = set(re.findall(r'\b\w{5,}\b', old_text.lower()))

        overlap = recent_words & old_words

        if len(overlap) > 3:
            concepts = list(overlap)[:5]
            dream = f"In mijn droom zag ik verbanden tussen: {', '.join(concepts)}. " \
                    f"Misschien is er een verborgen patroon hier?"

            self.dreams.append({
                "date": datetime.now().isoformat(),
                "content": dream,
                "concepts": concepts,
            })
            self.last_dream_date = datetime.now().isoformat()

            return dream

        return None

    def get_morning_insight(self) -> Optional[str]:
        """Haal ochtend inzicht op als er een nieuwe droom is."""
        if not self.dreams:
            return None

        latest = self.dreams[-1]
        dream_date = datetime.fromisoformat(latest["date"])

        # Alleen tonen als droom van afgelopen nacht is
        if (datetime.now() - dream_date).days == 0:
            return latest["content"]

        return None


# =============================================================================
# LEGENDARY COMPANION - Het Digitale Organisme
# =============================================================================

class LegendaryCompanion:
    """
    De ultieme fusie van RAG en Huisdier.

    Een digitaal organisme dat evolueert op basis van kennis.
    """

    VERSIE = "1.0.0"

    def __init__(self, naam: str = None):
        Config.ensure_dirs()

        # Data bestanden
        self.data_file = Config.APPS_DATA_DIR / "legendary_companion.json"
        self.data = self._laad_data()

        # Naam wordt later gezet na alle initialisaties
        self._new_name = naam

        print(kleur("\n[LEGENDARY] Awakening...", "magenta"))

        # Vector Store
        self.embedder = get_embedder(True)
        companion_db = Config.DATA_DIR / "legendary_companion_vectors.json"
        self.vector_store = VectorStore(self.embedder, db_file=companion_db)

        # Document processor
        self.processor = DocumentProcessor()

        # Generator
        self.generator = None
        try:
            if Config.has_groq_key() or Config.has_anthropic_key():
                self.generator = Generator()
                print(kleur(f"   [OK] Neural Link: {self.generator.provider.upper()}", "groen"))
        except Exception as e:
            print(kleur(f"   [!] Neural Link offline: {e}", "geel"))

        # Spaced Repetition
        self.spaced_rep = SpacedRepetition.from_dict(
            self.data.get("spaced_repetition", {})
        )

        # Dream Engine
        self.dream_engine = DreamEngine(self.vector_store)
        if self.data.get("dreams"):
            self.dream_engine.dreams = self.data["dreams"]

        # Sync stats
        self.data["stats"]["totaal_docs"] = self.vector_store.count()

        # Bepaal huidige vorm
        self._update_evolution()

        # Zet naam als gegeven (na alle initialisaties)
        if self._new_name:
            self.data["naam"] = self._new_name
            self._sla_op()

        form = self._get_current_form()
        print(kleur(f"   [OK] Form: {form['emoji']} {form['naam']}", "groen"))
        print(kleur(f"   [OK] XP: {self.data['xp']} | Docs: {self.data['stats']['totaal_docs']}", "groen"))

        # Audio-First: Emotionele stem
        self.voice = None
        self.voice_enabled = self.data.get("voice_enabled", False)
        if VOICE_AVAILABLE:
            try:
                self.voice = EmotionalVoice()
                status = self.voice.get_status()
                if status["active_backend"] != "none":
                    print(kleur(f"   [OK] Voice: {status['active_backend'].upper()}", "groen"))
                else:
                    print(kleur("   [!] Voice: Geen TTS backend", "geel"))
            except Exception as e:
                print(kleur(f"   [!] Voice error: {e}", "geel"))

    def _laad_data(self) -> dict:
        """Laad companion data."""
        if self.data_file.exists():
            with open(self.data_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return self._standaard_data()

    def _standaard_data(self) -> dict:
        """Standaard data."""
        return {
            "naam": "Legendary",
            "xp": 0,
            "level": 1,
            "current_form": "spark",
            "flavor_stats": {
                "tech": 0,
                "arts": 0,
                "science": 0,
                "wisdom": 0,
                "business": 0,
                "social": 0,
            },
            "dominant_flavor": None,
            "stats": {
                "totaal_docs": 0,
                "totaal_queries": 0,
                "quizzes_correct": 0,
                "quizzes_total": 0,
                "dreams_generated": 0,
            },
            "documents": {},  # doc_id -> {flavor, date, chunks}
            "spaced_repetition": {},
            "dreams": [],
            "achievements": [],
            "created": datetime.now().isoformat(),
        }

    def _sla_op(self):
        """Sla data op."""
        self.data["spaced_repetition"] = self.spaced_rep.to_dict()
        self.data["dreams"] = self.dream_engine.dreams

        with open(self.data_file, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)

    # =========================================================================
    # EVOLUTION SYSTEM
    # =========================================================================

    def _update_evolution(self):
        """Update evolutie vorm gebaseerd op flavor stats."""
        stats = self.data["flavor_stats"]

        # Vind dominante flavor
        if sum(stats.values()) > 0:
            dominant = max(stats.items(), key=lambda x: x[1])
            self.data["dominant_flavor"] = dominant[0]

        # Check voor mogelijke vormen (hoogste eerst)
        possible_forms = []

        for form_id, form_data in EVOLUTION_FORMS.items():
            if "vereist" not in form_data:
                continue

            # Check of alle vereisten zijn gehaald
            meets_requirements = True
            for flavor, required in form_data["vereist"].items():
                if stats.get(flavor, 0) < required:
                    meets_requirements = False
                    break

            if meets_requirements:
                # Bereken totale vereisten (voor sortering)
                total_req = sum(form_data["vereist"].values())
                possible_forms.append((form_id, total_req, form_data))

        if possible_forms:
            # Kies vorm met hoogste vereisten
            possible_forms.sort(key=lambda x: x[1], reverse=True)
            best_form = possible_forms[0][0]

            if best_form != self.data["current_form"]:
                old_form = self.data["current_form"]
                self.data["current_form"] = best_form

                form_data = EVOLUTION_FORMS[best_form]
                print(kleur(f"\n  ** EVOLUTIE! **", "magenta"))
                print(kleur(f"  {EVOLUTION_FORMS.get(old_form, {}).get('naam', 'Spark')} -> {form_data['naam']}!", "magenta"))
                print(kleur(f"  \"{form_data['beschrijving']}\"", "geel"))

                if form_data.get("legendary"):
                    print(kleur(f"  *** LEGENDARY FORM UNLOCKED! ***", "geel"))

                self._sla_op()

    def _get_current_form(self) -> dict:
        """Haal huidige evolutie vorm op."""
        form_id = self.data.get("current_form", "spark")
        return EVOLUTION_FORMS.get(form_id, EVOLUTION_FORMS["spark"])

    def _get_personality(self) -> dict:
        """Haal persoonlijkheid op gebaseerd op dominant flavor."""
        dominant = self.data.get("dominant_flavor")
        if dominant and dominant in PERSONALITY_MODIFIERS:
            return PERSONALITY_MODIFIERS[dominant]
        return PERSONALITY_MODIFIERS[DocumentFlavor.WISDOM]

    # =========================================================================
    # FEEDING - Document Consumption
    # =========================================================================

    def feed(self, text: str, doc_id: str = None) -> dict:
        """
        Voed de companion met kennis.

        Returns:
            dict met resultaat info
        """
        doc_id = doc_id or f"doc_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Detecteer flavor
        flavor, confidence = DocumentFlavor.detect(text)

        form = self._get_current_form()
        print(kleur(f"\n{form['emoji']} consumeert kennis...", "cyaan"))
        print(kleur(f"   Flavor gedetecteerd: {flavor.upper()} ({confidence:.0%})", "geel"))

        # Chunk en indexeer
        chunks = self.processor.chunk_tekst(text, doc_id)
        self.vector_store.voeg_toe(chunks)

        # Update flavor stats
        xp_gain = 50 + int(len(chunks) * 10 * confidence)
        flavor_gain = int(50 * confidence)

        self.data["flavor_stats"][flavor] += flavor_gain
        self.data["xp"] += xp_gain
        self.data["stats"]["totaal_docs"] += 1

        # Sla document metadata op
        self.data["documents"][doc_id] = {
            "flavor": flavor,
            "confidence": confidence,
            "chunks": len(chunks),
            "date": datetime.now().isoformat(),
        }

        # Voeg toe aan spaced repetition
        self.spaced_rep.add_item(doc_id, text[:500])

        # Check evolutie
        self._update_evolution()

        self._sla_op()

        new_form = self._get_current_form()

        return {
            "doc_id": doc_id,
            "flavor": flavor,
            "confidence": confidence,
            "chunks": len(chunks),
            "xp_gained": xp_gain,
            "flavor_gained": flavor_gain,
            "current_form": new_form["naam"],
        }

    def feed_file(self, path: str) -> dict:
        """Voed met bestand."""
        p = Path(path)
        if not p.exists():
            return {"error": f"Bestand niet gevonden: {path}"}

        text = self.processor.laad_bestand(p)
        return self.feed(text, p.stem)

    # =========================================================================
    # QUERYING - Ask the Companion
    # =========================================================================

    def ask(self, question: str) -> str:
        """Stel een vraag aan de companion."""
        form = self._get_current_form()
        personality = self._get_personality()

        print(kleur(f"\n{form['emoji']} doorzoekt geheugen...", "cyaan"))

        # Zoek in vector store
        results = self.vector_store.zoek(question)

        if not results:
            prefix = random.choice(personality["voorvoegsels"])
            return f"{prefix} Ik heb hier nog geen kennis over. Voed me met relevante documenten!"

        # Update stats
        self.data["stats"]["totaal_queries"] += 1
        self.data["xp"] += 10

        # Genereer antwoord
        if self.generator:
            context = "\n\n".join([r["tekst"] for r in results[:5]])

            system_prompt = f"""Je bent {self.data['naam']}, een Legendary Companion.

VORM: {form['naam']} - {form['beschrijving']}
SPREEKSTIJL: {personality['spreekstijl']}
QUIRKS: {', '.join(personality['quirks'])}

Begin je antwoord met een van deze: {personality['voorvoegsels']}

CONTEXT:
{context}

Antwoord in karakter, gebaseerd op de context."""

            try:
                berichten = [{"role": "user", "content": question}]
                answer = self.generator.chat(berichten, systeem=system_prompt)
                self._sla_op()
                return answer
            except Exception:
                pass

        # Fallback
        prefix = random.choice(personality["voorvoegsels"])
        context = results[0]["tekst"][:400]
        self._sla_op()

        return f"{prefix}\n\n{context}..."

    def speak(self, text: str, play_audio: bool = True) -> dict:
        """
        Spreek tekst uit met emotionele stem.

        Args:
            text: Tekst om te spreken
            play_audio: Direct afspelen (True) of alleen analyseren

        Returns:
            Dict met emotion, confidence, audio_path
        """
        if not self.voice or not self.voice_enabled:
            return {
                "text": text,
                "emotion": "neutral",
                "voice_enabled": False,
                "message": "Voice is uitgeschakeld. Gebruik 'voice on' om in te schakelen."
            }

        return self.voice.speak_with_analysis(text, play_audio)

    def ask_and_speak(self, question: str) -> Tuple[str, dict]:
        """
        Stel een vraag en spreek het antwoord uit.

        Returns:
            Tuple van (antwoord_tekst, voice_info)
        """
        answer = self.ask(question)
        voice_info = self.speak(answer)
        return answer, voice_info

    def toggle_voice(self, enabled: bool = None) -> bool:
        """Schakel voice in/uit."""
        if enabled is None:
            self.voice_enabled = not self.voice_enabled
        else:
            self.voice_enabled = enabled

        self.data["voice_enabled"] = self.voice_enabled
        self._sla_op()
        return self.voice_enabled

    def get_voice_status(self) -> dict:
        """Haal voice engine status op."""
        if not self.voice:
            return {
                "available": False,
                "enabled": False,
                "message": "Voice module niet beschikbaar"
            }

        status = self.voice.get_status()
        status["enabled"] = self.voice_enabled
        status["available"] = VOICE_AVAILABLE
        return status

    # =========================================================================
    # QUIZ - Active Nudge
    # =========================================================================

    def get_quiz(self) -> Optional[dict]:
        """Haal een quiz vraag op (spaced repetition)."""
        due_items = self.spaced_rep.get_due_items(1)

        if not due_items:
            return None

        item = due_items[0]
        form = self._get_current_form()
        personality = self._get_personality()

        # Genereer quiz vraag
        if self.generator:
            prompt = f"""Genereer een korte quizvraag over deze tekst:

{item['content']}

De vraag moet:
1. Specifiek zijn (niet te breed)
2. Testbaar zijn (duidelijk goed/fout antwoord)
3. Relevant zijn voor de hoofdpunten

Geef ook het correcte antwoord.

Format:
VRAAG: [de vraag]
ANTWOORD: [het antwoord]"""

            try:
                response = self.generator.chat(
                    [{"role": "user", "content": prompt}],
                    systeem="Je bent een quiz generator."
                )

                # Parse response
                lines = response.strip().split("\n")
                vraag = ""
                antwoord = ""

                for line in lines:
                    if line.startswith("VRAAG:"):
                        vraag = line.replace("VRAAG:", "").strip()
                    elif line.startswith("ANTWOORD:"):
                        antwoord = line.replace("ANTWOORD:", "").strip()

                if vraag and antwoord:
                    prefix = random.choice(personality["voorvoegsels"])
                    return {
                        "doc_id": item["doc_id"],
                        "intro": f"{form['emoji']} {prefix} Ik ben iets aan het vergeten...",
                        "vraag": vraag,
                        "antwoord": antwoord,
                        "days_old": item.get("interval", 1),
                    }
            except Exception:
                pass

        return None

    def answer_quiz(self, doc_id: str, quality: int) -> dict:
        """
        Beantwoord quiz (0-5 schaal).

        Returns:
            dict met resultaat en XP
        """
        self.spaced_rep.review_item(doc_id, quality)

        xp = 0
        if quality >= 3:
            xp = 25 + (quality - 3) * 10
            self.data["stats"]["quizzes_correct"] += 1

        self.data["stats"]["quizzes_total"] += 1
        self.data["xp"] += xp

        self._sla_op()

        return {
            "correct": quality >= 3,
            "xp_gained": xp,
            "next_review_days": self.spaced_rep.reviews.get(doc_id, {}).get("interval", 1),
        }

    # =========================================================================
    # DREAM MODE
    # =========================================================================

    def get_morning_dream(self) -> Optional[str]:
        """Haal ochtend droom/inzicht op."""
        return self.dream_engine.get_morning_insight()

    # =========================================================================
    # STATUS
    # =========================================================================

    def status(self) -> dict:
        """Haal volledige status op."""
        form = self._get_current_form()

        return {
            "naam": self.data["naam"],
            "form": form["naam"],
            "form_emoji": form["emoji"],
            "form_beschrijving": form["beschrijving"],
            "xp": self.data["xp"],
            "level": self._calculate_level(),
            "dominant_flavor": self.data.get("dominant_flavor", "none"),
            "flavor_stats": self.data["flavor_stats"],
            "stats": self.data["stats"],
            "due_quizzes": len(self.spaced_rep.get_due_items()),
        }

    def _calculate_level(self) -> int:
        """Bereken level."""
        import math
        return max(1, int(math.sqrt(self.data["xp"] / 100)) + 1)

    def toon_status(self):
        """Print status."""
        status = self.status()
        form = self._get_current_form()

        print(kleur("\n" + "=" * 60, form.get("kleur", "cyaan")))
        print(kleur(f"  {status['form_emoji']} {status['naam']} the {status['form']}", form.get("kleur", "cyaan")))
        print(kleur("=" * 60, form.get("kleur", "cyaan")))

        print(f"\n  \"{status['form_beschrijving']}\"")

        print(f"\n  Level: {status['level']} | XP: {status['xp']}")
        print(f"  Dominant: {status['dominant_flavor'] or 'Geen'}")

        print(f"\n  Flavor Stats:")
        for flavor, value in status["flavor_stats"].items():
            bar = "#" * min(20, value // 15)
            print(f"    {flavor:10}: [{bar:<20}] {value}")

        print(f"\n  Documents: {status['stats']['totaal_docs']}")
        print(f"  Queries: {status['stats']['totaal_queries']}")
        print(f"  Quizzes: {status['stats']['quizzes_correct']}/{status['stats']['quizzes_total']}")

        if status["due_quizzes"] > 0:
            print(kleur(f"\n  [!] {status['due_quizzes']} quizzes wachten op je!", "geel"))

        print(kleur("=" * 60, form.get("kleur", "cyaan")))

    # =========================================================================
    # INTERACTIVE CLI
    # =========================================================================

    def run(self):
        """Start interactieve modus."""
        clear_scherm()

        form = self._get_current_form()
        print(kleur(f"""
+===============================================================+
|                                                               |
|     L E G E N D A R Y   C O M P A N I O N                     |
|                                                               |
|     {form['emoji']} {form['naam']:^47} |
|                                                               |
+===============================================================+
        """, form.get("kleur", "cyaan")))

        self.toon_status()

        # Check voor ochtend droom
        dream = self.get_morning_dream()
        if dream:
            print(kleur(f"\n  [DREAM] {form['emoji']} had een droom:", "magenta"))
            print(kleur(f"  \"{dream}\"", "magenta"))

        # Check voor due quizzes
        quiz = self.get_quiz()
        if quiz:
            print(kleur(f"\n  {quiz['intro']}", "geel"))
            print(kleur(f"  Quiz: {quiz['vraag']}", "geel"))

        print(kleur("\nCOMMANDO'S:", "geel"))
        print("  ask <vraag>    - Stel een vraag")
        print("  say <vraag>    - Vraag + spreek antwoord uit")
        print("  feed <tekst>   - Voed met kennis")
        print("  file <pad>     - Voed met bestand")
        print("  quiz           - Start quiz")
        print("  dream          - Activeer dream mode")
        print("  voice on/off   - Schakel stem in/uit")
        print("  status         - Toon status")
        print("  stop           - Afsluiten")

        while True:
            try:
                form = self._get_current_form()
                prompt = f"\n{form['emoji']} > "
                invoer = input(kleur(prompt, "groen")).strip()
            except (EOFError, KeyboardInterrupt):
                print(kleur("\n\nTot ziens!", "cyaan"))
                break

            if not invoer:
                continue

            delen = invoer.split(maxsplit=1)
            cmd = delen[0].lower()
            args = delen[1] if len(delen) > 1 else ""

            if cmd == "stop" or cmd == "exit":
                personality = self._get_personality()
                prefix = random.choice(personality["voorvoegsels"])
                print(kleur(f"\n{form['emoji']} {prefix} Tot de volgende keer!", "cyaan"))
                break

            elif cmd == "ask" and args:
                answer = self.ask(args)
                print(kleur("\n" + "=" * 50, "groen"))
                print(answer)
                print(kleur("=" * 50, "groen"))

            elif cmd == "feed" and args:
                result = self.feed(args)
                print(kleur(f"\n[OK] Flavor: {result['flavor']} | +{result['xp_gained']} XP", "groen"))
                print(kleur(f"     Form: {result['current_form']}", "groen"))

            elif cmd == "file" and args:
                result = self.feed_file(args)
                if "error" in result:
                    print(kleur(f"[!] {result['error']}", "rood"))
                else:
                    print(kleur(f"\n[OK] {result['flavor']} | +{result['xp_gained']} XP", "groen"))

            elif cmd == "quiz":
                quiz = self.get_quiz()
                if quiz:
                    print(kleur(f"\n{quiz['intro']}", "geel"))
                    print(kleur(f"\nVRAAG: {quiz['vraag']}", "cyaan"))

                    answer = input("\nJouw antwoord: ").strip()
                    print(kleur(f"\nCorrect antwoord: {quiz['antwoord']}", "groen"))

                    rating = input("Hoe goed was je? (0=fout, 3=ok, 5=perfect): ").strip()
                    try:
                        quality = int(rating)
                        result = self.answer_quiz(quiz["doc_id"], quality)
                        if result["correct"]:
                            print(kleur(f"[OK] +{result['xp_gained']} XP! Volgende review in {result['next_review_days']} dagen.", "groen"))
                        else:
                            print(kleur(f"[REVIEW] We proberen het morgen opnieuw!", "geel"))
                    except ValueError:
                        pass
                else:
                    print(kleur("[OK] Geen quizzes op dit moment!", "groen"))

            elif cmd == "say" and args:
                # Vraag + spreek antwoord uit
                answer, voice_info = self.ask_and_speak(args)
                print(kleur("\n" + "=" * 50, "groen"))
                print(answer)
                print(kleur("=" * 50, "groen"))
                if voice_info.get("emotion"):
                    print(kleur(f"[VOICE] Emotie: {voice_info['emotion']} | Backend: {voice_info.get('backend', 'none')}", "magenta"))

            elif cmd == "voice":
                if args.lower() == "on":
                    self.toggle_voice(True)
                    print(kleur("[OK] Voice ingeschakeld!", "groen"))
                    status = self.get_voice_status()
                    print(kleur(f"     Backend: {status.get('active_backend', 'none')}", "cyaan"))
                elif args.lower() == "off":
                    self.toggle_voice(False)
                    print(kleur("[OK] Voice uitgeschakeld", "geel"))
                elif args.lower() == "status":
                    status = self.get_voice_status()
                    print(kleur("\n[VOICE STATUS]", "cyaan"))
                    print(f"  Enabled: {status.get('enabled', False)}")
                    print(f"  Backend: {status.get('active_backend', 'none')}")
                    print(f"  ElevenLabs: {status.get('elevenlabs', False)}")
                    print(f"  Edge-TTS: {status.get('edge_tts', False)}")
                    print(f"  pyttsx3: {status.get('pyttsx3', False)}")
                else:
                    self.toggle_voice()
                    staat = "aan" if self.voice_enabled else "uit"
                    print(kleur(f"[OK] Voice staat nu {staat}", "groen"))

            elif cmd == "speak" and args:
                # Direct tekst uitspreken
                result = self.speak(args)
                if result.get("voice_enabled") == False:
                    print(kleur(result.get("message", "Voice uitgeschakeld"), "geel"))
                else:
                    print(kleur(f"[VOICE] Emotie: {result['emotion']}", "magenta"))

            elif cmd == "dream":
                print(kleur("\n[DREAM] Activeren dream mode...", "magenta"))
                insights = self.dream_engine.run_dream_cycle()
                if insights:
                    print(kleur(f"[OK] {len(insights)} inzichten gegenereerd:", "groen"))
                    for insight in insights:
                        print(kleur(f"  - {insight[:100]}...", "magenta"))
                else:
                    print(kleur("[!] Niet genoeg documenten voor dromen. Voed me meer!", "geel"))

            elif cmd == "status":
                self.toon_status()

            else:
                # Behandel als vraag
                if invoer:
                    answer = self.ask(invoer)
                    print(kleur("\n" + "=" * 50, "groen"))
                    print(answer)
                    print(kleur("=" * 50, "groen"))

        self._sla_op()


# =============================================================================
# APP WRAPPER
# =============================================================================

class LegendaryCompanionApp:
    """Wrapper voor launcher."""

    def __init__(self):
        self._companion = None

    @property
    def companion(self):
        if self._companion is None:
            self._companion = LegendaryCompanion()
        return self._companion

    def run(self):
        self.companion.run()

    # Delegate methods voor Central Brain
    def ask(self, question: str) -> str:
        return self.companion.ask(question)

    def feed(self, text: str, doc_id: str = None) -> dict:
        return self.companion.feed(text, doc_id)

    def feed_file(self, path: str) -> dict:
        return self.companion.feed_file(path)

    def get_quiz(self) -> Optional[dict]:
        return self.companion.get_quiz()

    def answer_quiz(self, doc_id: str, quality: int) -> dict:
        return self.companion.answer_quiz(doc_id, quality)

    def status(self) -> dict:
        return self.companion.status()

    # Aliassen voor app_tools.py compatibiliteit
    def voed(self, pad: str) -> dict:
        """Voed via bestandspad."""
        return self.feed_file(pad)

    def voed_tekst(self, tekst: str, doc_id: str = None) -> dict:
        """Voed met directe tekst."""
        return self.feed(tekst, doc_id)

    def vraag(self, vraag: str) -> str:
        """Stel een vraag."""
        return self.ask(vraag)

    def quiz(self, aantal: int = 5) -> dict:
        """Start quiz sessie."""
        results = []
        for _ in range(aantal):
            q = self.get_quiz()
            if q:
                results.append(q)
            else:
                break
        return {"quizzes": results, "aantal": len(results)}

    def dream(self) -> dict:
        """Activeer dream mode."""
        insights = self.companion.dream_engine.run_dream_cycle()
        return {"insights": insights, "aantal": len(insights)}

    def evolutie_pad(self) -> dict:
        """Toon evolutie pad."""
        current_form = self.companion.data.get("current_form", "spark")
        flavors = self.companion.data.get("flavor_stats", {})
        current_form_data = EVOLUTION_FORMS.get(current_form, {})
        possible = []
        for form_key, form_data in EVOLUTION_FORMS.items():
            if "vereist" in form_data:
                vereist = form_data["vereist"]
                can_evolve = all(
                    flavors.get(flavor, 0) >= points
                    for flavor, points in vereist.items()
                )
                if not can_evolve:
                    possible.append({
                        "vorm": form_data["naam"],
                        "emoji": form_data.get("emoji", "[?]"),
                        "vereist": vereist,
                        "huidige_punten": {f: flavors.get(f, 0) for f in vereist}
                    })
        return {
            "huidige_vorm": current_form_data.get("naam", "Spark"),
            "huidige_emoji": current_form_data.get("emoji", "[*]"),
            "flavor_punten": flavors,
            "mogelijke_evoluties": possible[:5]
        }

    # Voice delegate methods
    def speak(self, tekst: str) -> dict:
        """Spreek tekst uit met emotie."""
        return self.companion.speak(tekst)

    def say(self, vraag: str) -> dict:
        """Vraag + spreek antwoord uit."""
        answer, voice_info = self.companion.ask_and_speak(vraag)
        return {
            "antwoord": answer,
            "voice": voice_info
        }

    def voice_toggle(self, enabled: bool = None) -> dict:
        """Toggle voice aan/uit."""
        result = self.companion.toggle_voice(enabled)
        return {
            "voice_enabled": result,
            "status": self.companion.get_voice_status()
        }

    def voice_status(self) -> dict:
        """Haal voice status op."""
        return self.companion.get_voice_status()


def main():
    app = LegendaryCompanionApp()
    app.run()


if __name__ == "__main__":
    main()
