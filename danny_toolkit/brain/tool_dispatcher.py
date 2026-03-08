"""
Tool Dispatcher — 2-Layer Hierarchical Tool Selection.

Reduceert 92 tool definitions naar 8-20 per LLM call via:
  Pass 1: Keyword matching (0ms) — NL+EN categorieën + directe app-matches
  Pass 2: LLM fallback (zeldzaam) — compact manifest, temperature=0
  Pass 3: Priority fallback — top-5 apps als niets matcht

Impact: ~80% minder tokens, nul parameter-verwarring.
"""

from __future__ import annotations

import logging
import os
import re
import threading
from typing import FrozenSet, Optional, Set

logger = logging.getLogger(__name__)

# --- Singleton ---
_instance: Optional["ToolDispatcher"] = None
_lock = threading.Lock()


def get_tool_dispatcher() -> "ToolDispatcher":
    """Thread-safe singleton factory."""
    global _instance
    if _instance is None:
        with _lock:
            if _instance is None:
                _instance = ToolDispatcher()
    return _instance


# --- Constants ---

# Apps die ALTIJD meegestuurd worden (systeemkritisch)
ALWAYS_INCLUDE: FrozenSet[str] = frozenset({"omega_core", "omega_advanced_knowledge"})

# Max apps geselecteerd (excl. ALWAYS_INCLUDE)
MAX_SELECTED = 8

# Top-5 priority fallback als geen match gevonden
_PRIORITY_FALLBACK = [
    "legendary_companion",
    "knowledge_companion",
    "production_rag",
    "fitness_tracker",
    "goals_tracker",
]

# --- Category Keywords (NL+EN) ---
# Elke categorie matcht naar een set app-namen
_CATEGORY_KEYWORDS: dict[str, list[str]] = {
    # Gezondheid & Fitness
    "gezondheid": [
        "fitness_tracker", "mood_tracker",
    ],
    r"\bfitness\b|\bworkout\b|\btraining\b|\boefening\b|\bexercise\b|\bgym\b|\bsport\b|\bcardio\b|\bkracht\b|"
    r"\bcalorieën\b|\bcalories\b|\breps\b|\bsets\b|personal record|\bpr\b|\bstreak\b": [
        "fitness_tracker",
    ],
    "mood|stemming|emotie|emotion|gevoel|feeling|humeur": [
        "mood_tracker",
    ],

    # Productiviteit
    "goal|doel|voortgang|progress|milestone": [
        "goals_tracker",
    ],
    "agenda|afspraak|appointment|event|planning|schedule|kalender|calendar": [
        "agenda_planner",
    ],
    "pomodoro|focus|timer|sessie|concentratie": [
        "pomodoro_timer",
    ],
    "habit|gewoonte|streak|dagelijks|daily|routine": [
        "habit_tracker",
    ],
    "beslissing|decision|keuze|choice|optie|option|afweging": [
        "decision_maker",
    ],

    # Financiën
    "expense|uitgave|budget|geld|money|kosten|cost|euro|betaling|payment|"
    "financ|salar|inkomen|income|boodschap": [
        "expense_tracker", "boodschappenlijst",
    ],

    # Voeding & Recepten
    "recept|recipe|koken|cook|meal|maaltijd|ingredient|eten|food|"
    "eiwit|protein|dieet|diet|vegetarisch|vegan|keto|calorie": [
        "recipe_generator",
    ],
    "boodschap|grocery|shopping|winkel|supermarkt": [
        "boodschappenlijst",
    ],

    # AI & Kennis
    "rag|kennisbank|knowledge|zoek.*kennis|search.*knowledge|companion|"
    "legendary|voed|feed|quiz|dream mode|evolutie|evolution|hunt": [
        "legendary_companion", "knowledge_companion",
    ],
    "nieuws|news|headlines|actualiteit": [
        "nieuws_agent",
    ],
    r"\bweer\b|\bweather\b|\btemperatuur\b|\btemperature\b|\bregen\b|\brain\b|\bforecast\b|\bvoorspelling\b": [
        "weer_agent",
    ],

    # Code & Dev
    r"\bcode\b|\banalyse\b|\banalyze\b|\bbug\b|\bissue\b|\berror\b|\bfout\b|\bdebug\b|\bsnippet\b|\bprogrammeer\b|"
    r"\bprogram\b|\brefactor\b|\blint\b": [
        "code_analyse", "code_snippets",
    ],
    "nlp|sentiment|tekst.*analy|text.*analy|natural language": [
        "nlp_studio",
    ],
    "machine learning|ml|train.*model|neural|dataset": [
        "ml_studio",
    ],
    "vector|embedding|faiss|chroma": [
        "vector_studio",
    ],
    "vraag|question|answer|antwoord": [
        "advanced_questions",
    ],

    # Notities & Leren
    "notitie|note|opschrijven|memo": [
        "notitie_app",
    ],
    "flashcard|studeren|study|leren|onthouden|memorize|spaced repetition": [
        "flashcards",
    ],
    "taal|language|vertaal|translate|engels|english|frans|french|"
    "spaans|spanish|duits|german": [
        "language_tutor",
    ],

    # Creatief
    "muziek|music|componeer|compose|melodie|melody|akkoord|chord": [
        "music_composer",
    ],
    "citaat|quote|inspiratie|inspiration|wijsheid|wisdom": [
        "citaten_generator",
    ],

    # Lifestyle
    "droom|dream|nachtmerrie|nightmare|slaap|sleep": [
        "dream_journal",
    ],
    "time capsule|toekomst|future|bericht.*later|message.*later": [
        "time_capsule",
    ],

    # Utilities
    "reken|calcul|berekening|wiskunde|math|som": [
        "rekenmachine",
    ],
    "convert|omzetten|eenheid|unit|kilogram|meter|celsius|fahrenheit": [
        "unit_converter",
    ],
    "wachtwoord|password|genere.*wachtwoord|generate.*password": [
        "wachtwoord_generator",
    ],

    # Localhost & Dev Server
    r"scan.*poort|localhost|local.?host|dev.?server|lokale.?server|mijn.?site|my.?site|"
    r"localhost:\d|127\.0\.0\.1|lokale.?pagina|local.?page|"
    r"scrape.*local|lees.*local|read.*local|bekijk.*site|view.*site|"
    r"observatie.*modus|sane.*bridge|observeer.*poort|lees.*poort": [
        "local_bridge",
    ],

    # Omega Systeem
    "omega|scan|tier|system|health|neural|cortex|memory.*recall|"
    "immune|black.?box|arbitrator|swarm|synapse|phantom|sentinel|"
    "dashboard|sovereign|brain|introspect": [
        "omega_core",
    ],

    # GPU Control
    r"gpu.*clock|gpu.*mhz|gpu.*performance|gpu.*power|nvidia.*smi|"
    r"gpu.*reset|gpu.*boost|gpu.*status|gpu.*temp|zet.*gpu|"
    r"clock.*speed|overclock|underclock|power.*mode": [
        "gpu_control",
    ],

    # OMEGA Advanced Knowledge (architectuur, protocollen, skills, quests)
    r"architectuur|protocol|skill|quest|raadpleeg|omega.*skill|"
    r"advanced.*knowledge|interne.*werking|hoe.*werkt|pixel.*eye|"
    r"librarian|artificer|limbic|metabolisme|sensorium|trinity|"
    r"daemon|persona|learning.*system|tool.*dispatch|workflow.*engine|"
    r"nexus.*design|autopsie|wachtrij|verhouding": [
        "omega_advanced_knowledge",
    ],
}

# Direct app-name match (als user letterlijk de app-naam noemt)
_APP_DIRECT_NAMES: dict[str, str] = {
    "fitness tracker": "fitness_tracker",
    "fitness": "fitness_tracker",
    "mood tracker": "mood_tracker",
    "mood": "mood_tracker",
    "goals tracker": "goals_tracker",
    "goals": "goals_tracker",
    "agenda": "agenda_planner",
    "pomodoro": "pomodoro_timer",
    "habit tracker": "habit_tracker",
    "habits": "habit_tracker",
    "expense tracker": "expense_tracker",
    "expenses": "expense_tracker",
    "budget": "expense_tracker",
    "recipe": "recipe_generator",
    "recepten": "recipe_generator",
    "boodschappen": "boodschappenlijst",
    "boodschappenlijst": "boodschappenlijst",
    "rag": "production_rag",
    "knowledge companion": "knowledge_companion",
    "legendary companion": "legendary_companion",
    "companion": "legendary_companion",
    "nieuws": "nieuws_agent",
    "news": "nieuws_agent",
    "weer": "weer_agent",
    "weather": "weer_agent",
    "code analyse": "code_analyse",
    "code snippets": "code_snippets",
    "nlp studio": "nlp_studio",
    "ml studio": "ml_studio",
    "vector studio": "vector_studio",
    "notities": "notitie_app",
    "notes": "notitie_app",
    "flashcards": "flashcards",
    "language tutor": "language_tutor",
    "talen": "language_tutor",
    "music composer": "music_composer",
    "muziek": "music_composer",
    "citaten": "citaten_generator",
    "dream journal": "dream_journal",
    "dromen": "dream_journal",
    "time capsule": "time_capsule",
    "rekenmachine": "rekenmachine",
    "calculator": "rekenmachine",
    "unit converter": "unit_converter",
    "password": "wachtwoord_generator",
    "wachtwoord": "wachtwoord_generator",
    "decision maker": "decision_maker",
    "omega": "omega_core",
    "system scan": "omega_core",
    "omega core": "omega_core",
    "localhost": "local_bridge",
    "local bridge": "local_bridge",
    "dev server": "local_bridge",
    "mijn site": "local_bridge",
    "my site": "local_bridge",
}

# Pre-compiled regex patterns per category
_COMPILED_PATTERNS: dict[re.Pattern, list[str]] = {}


def _compile_patterns() -> None:
    """Compile category keyword patterns eenmalig."""
    global _COMPILED_PATTERNS
    if _COMPILED_PATTERNS:
        return
    for pattern_str, apps in _CATEGORY_KEYWORDS.items():
        try:
            _COMPILED_PATTERNS[re.compile(pattern_str, re.IGNORECASE)] = apps
        except re.error:
            logger.warning("Ongeldige regex in _CATEGORY_KEYWORDS: %s", pattern_str)


# LLM compact manifest (1 regel per app) voor Pass 2
_APP_MANIFEST = """fitness_tracker: workout/exercise/calories tracking
mood_tracker: daily mood/emotion logging
goals_tracker: goals and progress tracking
agenda_planner: agenda/appointments/calendar
pomodoro_timer: focus sessions/pomodoro
habit_tracker: daily habits/streaks
expense_tracker: expenses/budget/money
recipe_generator: recipes/meals/cooking
boodschappenlijst: grocery/shopping list
production_rag: RAG knowledge search
nieuws_agent: news/headlines
weer_agent: weather/forecast
code_analyse: code analysis/debugging
code_snippets: code snippets search
decision_maker: decisions/choices
notitie_app: notes/memos
flashcards: flashcards/study
language_tutor: language learning/translation
music_composer: music composition
citaten_generator: quotes/inspiration
dream_journal: dream logging
time_capsule: future messages
rekenmachine: calculations/math
unit_converter: unit conversion
wachtwoord_generator: password generation
nlp_studio: NLP/sentiment analysis
ml_studio: machine learning
vector_studio: vector search
advanced_questions: complex Q&A
knowledge_companion: AI knowledge companion
legendary_companion: evolved AI companion + hunt
omega_core: system scan/health/tiers/memory/neural
omega_advanced_knowledge: OMEGA advanced architecture/protocols/skills/quests/learning/persona/UI knowledge from vector DB
local_bridge: localhost/dev-server page reading (read-only)
gpu_control: GPU clock/power management via nvidia-smi"""


class ToolDispatcher:
    """2-Layer Hierarchical Tool Dispatcher.

    Selecteert 2-8 relevante apps per user query i.p.v. alle 32.
    Pass 1: Keyword regex matching (instant)
    Pass 2: LLM classification (alleen als Pass 1 nul matches)
    Pass 3: Priority fallback (als alles faalt)
    """

    def __init__(self) -> None:
        """Init  ."""
        _compile_patterns()
        self._groq_client = None
        self._groq_model: str = ""
        self._init_llm()

    def _init_llm(self) -> None:
        """Initialiseer Groq client voor Pass 2 LLM fallback."""
        try:
            from danny_toolkit.core.key_manager import get_key_manager
            km = get_key_manager()
            self._groq_client = km.create_sync_client("Tribunal")
            self._groq_model = "meta-llama/llama-4-scout-17b-16e-instruct"
        except ImportError:
            logger.debug("Suppressed error")

        if not self._groq_client:
            try:
                from groq import Groq
                key = os.getenv("GROQ_API_KEY_VERIFY") or os.getenv("GROQ_API_KEY")
                if key:
                    self._groq_client = Groq(api_key=key)
                    self._groq_model = "meta-llama/llama-4-scout-17b-16e-instruct"
            except ImportError:
                logger.debug("Suppressed error")

    def select_tools(self, user_input: str) -> Set[str]:
        """Selecteer relevante apps voor de user query.

        Returns:
            Set van app-namen (altijd inclusief ALWAYS_INCLUDE).
        """
        if not user_input or not user_input.strip():
            return set(ALWAYS_INCLUDE) | set(_PRIORITY_FALLBACK)

        query = user_input.strip().lower()

        # --- Pass 1: Keyword matching (0ms) ---
        matched = self._keyword_match(query)

        # --- Pass 2: LLM fallback (alleen als Pass 1 nul matches) ---
        if not matched and self._groq_client:
            try:
                matched = self._llm_classify(query)
            except Exception as e:
                logger.debug("ToolDispatcher LLM fallback fout: %s", e)

        # --- Pass 3: Priority fallback ---
        if not matched:
            matched = set(_PRIORITY_FALLBACK)

        # Always include + cap
        result = matched | set(ALWAYS_INCLUDE)
        return self._cap_selection(result)

    def _keyword_match(self, query: str) -> Set[str]:
        """Pass 1: Regex keyword matching over categorieën + directe namen."""
        matched: Set[str] = set()

        # Directe app-naam match
        for name, app in _APP_DIRECT_NAMES.items():
            if name in query:
                matched.add(app)

        # Category regex matching
        for pattern, apps in _COMPILED_PATTERNS.items():
            if pattern.search(query):
                matched.update(apps)

        return matched

    def _llm_classify(self, query: str) -> Set[str]:
        """Pass 2: LLM-based classification met compact manifest."""
        if not self._groq_client:
            return set()

        prompt = (
            "Given this user query, return ONLY the app names (comma-separated) "
            "that are relevant. Return 1-5 app names, nothing else.\n\n"
            f"Apps:\n{_APP_MANIFEST}\n\n"
            f"Query: {query}\n\n"
            "Answer (comma-separated app names only):"
        )

        response = self._groq_client.chat.completions.create(
            model=self._groq_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=60,
        )

        content = response.choices[0].message.content or ""
        # Parse app names uit response
        valid_apps = set(_APP_MANIFEST_NAMES)
        matched: Set[str] = set()
        for part in content.replace("\n", ",").split(","):
            name = part.strip().lower()
            if name in valid_apps:
                matched.add(name)
        return matched

    def _cap_selection(self, apps: Set[str]) -> Set[str]:
        """Cap op MAX_SELECTED apps (excl. ALWAYS_INCLUDE)."""
        always = apps & set(ALWAYS_INCLUDE)
        rest = apps - set(ALWAYS_INCLUDE)

        if len(rest) <= MAX_SELECTED:
            return apps

        # Sorteer op prioriteit (hoog→laag), neem top MAX_SELECTED
        from danny_toolkit.brain.app_tools import APP_TOOLS
        prioritized = sorted(
            rest,
            key=lambda a: APP_TOOLS[a].prioriteit if a in APP_TOOLS else 0,
            reverse=True,
        )
        return set(prioritized[:MAX_SELECTED]) | always


# Valid app names for LLM response parsing
_APP_MANIFEST_NAMES = frozenset({
    "fitness_tracker", "mood_tracker", "goals_tracker", "agenda_planner",
    "pomodoro_timer", "habit_tracker", "expense_tracker", "recipe_generator",
    "boodschappenlijst", "production_rag", "nieuws_agent", "weer_agent",
    "code_analyse", "code_snippets", "decision_maker", "notitie_app",
    "flashcards", "language_tutor", "music_composer", "citaten_generator",
    "dream_journal", "time_capsule", "rekenmachine", "unit_converter",
    "wachtwoord_generator", "nlp_studio", "ml_studio", "vector_studio",
    "advanced_questions", "knowledge_companion", "legendary_companion",
    "omega_core", "omega_advanced_knowledge", "local_bridge", "gpu_control",
})
