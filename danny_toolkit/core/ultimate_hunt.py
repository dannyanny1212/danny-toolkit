"""
THE HUNT - Ultimate Go Fetch System.

Transformeert saaie zoekbalk naar een autonoom agent-avontuur.
Je virtuele huisdier jaagt door meerdere bronnen om de perfecte info te vangen.

Fases:
1. SNIFFING - Context analyse (agenda, notities, geschiedenis)
2. HUNTING - Multi-source parallel zoeken
3. DIGGING - Deep dive in gevonden bronnen
4. RETRIEVING - Resultaten ophalen en syntheseren
5. PRESENTING - Trophy presentatie met gamificatie
"""

import asyncio
import logging
import re
import time
from datetime import datetime
from enum import Enum
from typing import List, Dict, Any
from dataclasses import dataclass, field

from .utils import kleur, Kleur

logger = logging.getLogger(__name__)


# =============================================================================
# HUNT STATUS - Visuele Experience
# =============================================================================

class HuntStatus(Enum):
    """Status van de jacht met visuele representatie."""
    IDLE = ("idle", "Wachtend...", "[zzz]")
    SNIFFING = ("sniffing", "Ruikt het spoor...", "[snif snif]")
    ANALYZING = ("analyzing", "Analyseert context...", "[hmm...]")
    HUNTING = ("hunting", "Op jacht!", "[>>>]")
    DIGGING_RAG = ("digging_rag", "Graaft in documenten...", "[boeken]")
    DIGGING_WEB = ("digging_web", "Vliegt door het web...", "[www]")
    DIGGING_CODE = ("digging_code", "Doorzoekt code...", "[</>]")
    DIGGING_NEWS = ("digging_news", "Snuffelt in nieuws...", "[news]")
    DIGGING_ARCHIVE = ("digging_archive", "Graaft in archief...", "[oud]")
    RETRIEVING = ("retrieving", "Komt terug met buit!", "[!!!]")
    PROUD = ("proud", "Kwispelt trots!", "[*wag*]")
    SAD = ("sad", "Laat oren hangen...", "[:(]")
    ERROR = ("error", "Geschrokken!", "[!?!]")

    def __init__(self, key: str, beschrijving: str, emoji: str):
        self.key = key
        self.beschrijving = beschrijving
        self.emoji = emoji


@dataclass
class HuntResult:
    """Resultaat van een jacht."""
    bron: str                    # Waar gevonden (rag, web, code, news, archive)
    titel: str                   # Korte titel
    content: str                 # De inhoud
    confidence: float            # 0-1 betrouwbaarheid
    relevance: float             # 0-1 relevantie voor vraag
    timestamp: str = ""          # Wanneer gevonden
    metadata: Dict = field(default_factory=dict)

    @property
    def trophy_type(self) -> str:
        """Bepaal type trofee."""
        if self.confidence > 0.9 and self.relevance > 0.8:
            return "treasure"    # Schatkist - compleet dossier
        elif self.confidence > 0.7:
            return "bone"        # Bot - simpel feitje
        elif self.confidence < 0.4:
            return "rabbit"      # Vies konijn - onbetrouwbaar
        else:
            return "stick"       # Stok - basis resultaat


@dataclass
class HuntContext:
    """Context voor de jacht (de 'geur')."""
    original_query: str
    enriched_query: str = ""
    detected_intent: str = ""
    topics: List[str] = field(default_factory=list)
    sources_to_check: List[str] = field(default_factory=list)
    user_history: List[str] = field(default_factory=list)
    agenda_context: List[str] = field(default_factory=list)
    notes_context: List[str] = field(default_factory=list)


# =============================================================================
# HUNT ANIMATIONS - CLI Visuals
# =============================================================================

class HuntAnimator:
    """Visuele animaties voor de jacht."""

    SNIFFING_FRAMES = [
        "    /\\_/\\  ",
        "   ( o.o ) snif snif...",
        "    > ^ <  ",
    ]

    DIGGING_FRAMES = [
        "  \\(o.o)/  *graaf*",
        "   (o.o)   *graaf graaf*",
        "  /(o.o)\\  *GRAAF*",
    ]

    RUNNING_FRAMES = [
        "   ~~>",
        "  ~~~>>",
        " ~~~~>>>",
        "~~~~~>>>>",
    ]

    PROUD_FRAMES = [
        "   /\\_/\\   *kwispel*",
        "  ( ^.^ )  !!!",
        "   |   |   *KWISPEL*",
    ]

    SAD_FRAMES = [
        "   /\\_/\\",
        "  ( ;.; )",
        "   |   |  ...",
    ]

    @classmethod
    def show_status(cls, status: HuntStatus, message: str = "", bron: str = ""):
        """Toon hunt status met animatie."""
        # Kleur per status type
        kleur_map = {
            "sniffing": Kleur.CYAAN,
            "analyzing": Kleur.CYAAN,
            "hunting": Kleur.GEEL,
            "digging": Kleur.MAGENTA,
            "retrieving": Kleur.GROEN,
            "proud": Kleur.GROEN,
            "sad": Kleur.GEEL,
            "error": Kleur.ROOD,
        }

        status_type = status.key.split("_")[0]
        color = kleur_map.get(status_type, Kleur.WIT)

        # Bouw output
        emoji = status.emoji
        desc = status.beschrijving

        if bron:
            desc = f"{desc} [{bron}]"

        line = f"  {emoji} {desc}"
        if message:
            line += f" - {message}"

        print(kleur(line, color))

    @classmethod
    def show_trophy(cls, result: HuntResult):
        """Toon gevonden trofee."""
        trophy_icons = {
            "treasure": "[***SCHATKIST***]",
            "bone": "[bot]",
            "stick": "[stok]",
            "rabbit": "[?konijn?]",
        }

        trophy_colors = {
            "treasure": Kleur.GEEL,
            "bone": Kleur.GROEN,
            "stick": Kleur.CYAAN,
            "rabbit": Kleur.ROOD,
        }

        icon = trophy_icons.get(result.trophy_type, "[?]")
        color = trophy_colors.get(result.trophy_type, Kleur.WIT)

        print(kleur(f"\n  {icon} GEVONDEN in {result.bron.upper()}", color))
        print(kleur(f"  Confidence: {result.confidence:.0%} | Relevantie: {result.relevance:.0%}", Kleur.CYAAN))


# =============================================================================
# CONTEXT ANALYZER - De "Geur"
# =============================================================================

class ContextAnalyzer:
    """Analyseert context om de 'geur' te bepalen."""

    # Intent patterns
    INTENT_PATTERNS = {
        "code": [
            r'\b(code|functie|class|bug|error|python|javascript|api)\b',
            r'\b(implementeer|programmeer|debug|fix|refactor)\b',
            r'\b(github|stackoverflow|npm|pip)\b',
        ],
        "news": [
            r'\b(nieuws|recent|vandaag|gisteren|breaking)\b',
            r'\b(aankondiging|update|release|lancering)\b',
            r'\b(markt|aandelen|beurs|crypto)\b',
        ],
        "research": [
            r'\b(onderzoek|studie|paper|artikel|thesis)\b',
            r'\b(wetenschappelijk|data|analyse|statistiek)\b',
        ],
        "personal": [
            r'\b(mijn|ik|we|ons|onze)\b',
            r'\b(notitie|agenda|plan|doel|project)\b',
        ],
        "history": [
            r'\b(vorig|eerder|toen|ooit|archief)\b',
            r'\b(herinner|vergeten|besproken|gezegd)\b',
        ],
    }

    @classmethod
    def analyze(cls, query: str, notes: List[str] = None,
                agenda: List[str] = None) -> HuntContext:
        """
        Analyseer query en context om intent te bepalen.

        Returns:
            HuntContext met verrijkte informatie
        """
        context = HuntContext(original_query=query)
        query_lower = query.lower()

        # Detecteer intents
        intent_scores = {}
        for intent, patterns in cls.INTENT_PATTERNS.items():
            score = 0
            for pattern in patterns:
                matches = re.findall(pattern, query_lower)
                score += len(matches)
            if score > 0:
                intent_scores[intent] = score

        # Bepaal primaire intent
        if intent_scores:
            context.detected_intent = max(intent_scores, key=intent_scores.get)
        else:
            context.detected_intent = "general"

        # Bepaal welke bronnen te checken
        context.sources_to_check = cls._determine_sources(context.detected_intent)

        # Voeg context toe van notities en agenda
        if notes:
            context.notes_context = notes[:5]
            # Zoek relevante topics uit notities
            for note in notes[:3]:
                topics = cls._extract_topics(note)
                context.topics.extend(topics)

        if agenda:
            context.agenda_context = agenda[:3]
            # Zoek relevante context uit agenda
            for item in agenda[:3]:
                topics = cls._extract_topics(item)
                context.topics.extend(topics)

        # Verrijk de query
        context.enriched_query = cls._enrich_query(query, context)

        return context

    @classmethod
    def _determine_sources(cls, intent: str) -> List[str]:
        """Bepaal welke bronnen te doorzoeken."""
        source_map = {
            "code": ["rag", "code", "web"],
            "news": ["news", "web", "rag"],
            "research": ["rag", "web", "news"],
            "personal": ["rag", "archive", "notes"],
            "history": ["archive", "rag", "notes"],
            "general": ["rag", "web", "news"],
        }
        return source_map.get(intent, ["rag", "web"])

    @classmethod
    def _extract_topics(cls, text: str) -> List[str]:
        """Extraheer topics uit tekst."""
        # Simpele topic extractie - belangrijke woorden
        words = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', text)
        return list(set(words))[:5]

    @classmethod
    def _enrich_query(cls, query: str, context: HuntContext) -> str:
        """Verrijk query met context."""
        enriched = query

        # Voeg relevante topics toe
        if context.topics:
            enriched += f" (context: {', '.join(context.topics[:3])})"

        return enriched


# =============================================================================
# HUNT ROUTER - Welke bronnen doorzoeken?
# =============================================================================

class HuntRouter:
    """Router die bepaalt waar te zoeken."""

    def __init__(self):
        self.source_handlers = {}
        self._register_default_handlers()

    def _register_default_handlers(self):
        """Registreer standaard bron handlers."""
        self.source_handlers = {
            "rag": self._search_rag,
            "news": self._search_news,
            "web": self._search_web,
            "code": self._search_code,
            "archive": self._search_archive,
            "notes": self._search_notes,
        }

    async def hunt(self, context: HuntContext,
                   status_callback=None) -> List[HuntResult]:
        """
        Voer de jacht uit over meerdere bronnen.

        Args:
            context: De hunt context met query en bronnen
            status_callback: Callback voor status updates

        Returns:
            Lijst van HuntResult objecten
        """
        results = []

        for source in context.sources_to_check:
            handler = self.source_handlers.get(source)
            if not handler:
                continue

            # Status update
            if status_callback:
                status = getattr(HuntStatus, f"DIGGING_{source.upper()}", HuntStatus.HUNTING)
                status_callback(status, f"Doorzoeken...", source)

            try:
                source_results = await handler(context)
                results.extend(source_results)
            except Exception as e:
                if status_callback:
                    status_callback(HuntStatus.ERROR, str(e), source)

        return results

    async def _search_rag(self, context: HuntContext) -> List[HuntResult]:
        """Zoek in lokale RAG database."""
        try:
            from ..apps.legendary_companion import LegendaryCompanion

            # Lazy load companion
            companion = LegendaryCompanion()
            search_results = companion.vector_store.zoek(
                context.enriched_query or context.original_query,
                top_k=5
            )

            results = []
            for r in search_results:
                results.append(HuntResult(
                    bron="rag",
                    titel=r.get("metadata", {}).get("bron", "Document"),
                    content=r.get("tekst", ""),
                    confidence=r.get("score", 0.5),
                    relevance=r.get("score", 0.5),
                    timestamp=datetime.now().isoformat(),
                    metadata=r.get("metadata", {})
                ))

            return results

        except Exception as e:
            return [HuntResult(
                bron="rag",
                titel="Error",
                content=f"Kon RAG niet doorzoeken: {e}",
                confidence=0,
                relevance=0
            )]

    async def _search_news(self, context: HuntContext) -> List[HuntResult]:
        """Zoek in nieuws bronnen."""
        try:
            # Probeer nieuws agent te gebruiken
            from ..ai.nieuws_agent import NieuwsAgentApp

            agent = NieuwsAgentApp()
            # Simplified - in werkelijkheid zou dit de agent aanroepen
            return [HuntResult(
                bron="news",
                titel="Nieuws zoeken",
                content=f"Zoek naar: {context.original_query}",
                confidence=0.6,
                relevance=0.5,
                timestamp=datetime.now().isoformat()
            )]

        except Exception as e:
            logger.debug("News search failed: %s", e)
            return []

    async def _search_web(self, context: HuntContext) -> List[HuntResult]:
        """Zoek op het web (indien API beschikbaar)."""
        # Placeholder - zou Tavily/Google Search API kunnen gebruiken
        return []

    async def _search_code(self, context: HuntContext) -> List[HuntResult]:
        """Zoek in code bronnen."""
        try:
            from ..apps.code_analyse import CodeAnalyseApp

            # Simplified
            return [HuntResult(
                bron="code",
                titel="Code analyse",
                content=f"Code zoeken: {context.original_query}",
                confidence=0.5,
                relevance=0.5,
                timestamp=datetime.now().isoformat()
            )]

        except Exception as e:
            logger.debug("Code search failed: %s", e)
            return []

    async def _search_archive(self, context: HuntContext) -> List[HuntResult]:
        """Zoek in time capsule archief."""
        try:
            from ..apps.time_capsule import TimeCapsuleApp

            # Simplified
            return []

        except Exception as e:
            logger.debug("Archive search failed: %s", e)
            return []

    async def _search_notes(self, context: HuntContext) -> List[HuntResult]:
        """Zoek in notities."""
        try:
            from ..apps.notitie_app import NotitieApp

            # Simplified
            return []

        except Exception as e:
            logger.debug("Notes search failed: %s", e)
            return []


# =============================================================================
# THE ULTIMATE HUNT - Main Class
# =============================================================================

class UltimateHunt:
    """
    THE HUNT - Ultimate Go Fetch System.

    Stuurt je virtuele huisdier de digitale wildernis in om
    de perfecte informatie te vangen.
    """

    def __init__(self, pet_name: str = "Buddy"):
        self.pet_name = pet_name
        self.router = HuntRouter()
        self.analyzer = ContextAnalyzer()
        self.history: List[Dict] = []
        self.xp = 0

        # Feedback learning
        self.source_scores: Dict[str, float] = {
            "rag": 1.0,
            "news": 1.0,
            "web": 1.0,
            "code": 1.0,
            "archive": 1.0,
        }

    def _status_callback(self, status: HuntStatus, message: str = "", bron: str = ""):
        """Callback voor status updates."""
        HuntAnimator.show_status(status, message, bron)

    async def hunt(self, query: str, notes: List[str] = None,
                   agenda: List[str] = None) -> Dict[str, Any]:
        """
        Start een jacht!

        Args:
            query: De zoekvraag
            notes: Recente notities voor context
            agenda: Agenda items voor context

        Returns:
            Dict met resultaten en metadata
        """
        start_time = time.time()

        print(kleur(f"\n{'='*60}", Kleur.CYAAN))
        print(kleur(f"  THE HUNT - {self.pet_name} gaat op jacht!", Kleur.GEEL))
        print(kleur(f"  Query: \"{query}\"", Kleur.CYAAN))
        print(kleur(f"{'='*60}\n", Kleur.CYAAN))

        # Fase 1: SNIFFING - Analyseer context
        self._status_callback(HuntStatus.SNIFFING, "Ruikt het spoor...")
        context = self.analyzer.analyze(query, notes, agenda)

        self._status_callback(HuntStatus.ANALYZING,
                              f"Intent: {context.detected_intent}")
        print(kleur(f"  Bronnen: {', '.join(context.sources_to_check)}", Kleur.CYAAN))

        if context.topics:
            print(kleur(f"  Topics: {', '.join(context.topics[:5])}", Kleur.CYAAN))

        # Fase 2: HUNTING - Multi-source zoeken
        print()
        self._status_callback(HuntStatus.HUNTING, "Op jacht!")

        results = await self.router.hunt(context, self._status_callback)

        # Fase 3: RETRIEVING - Resultaten verwerken
        print()
        self._status_callback(HuntStatus.RETRIEVING, f"{len(results)} resultaten gevonden")

        if not results:
            self._status_callback(HuntStatus.SAD, "Niks gevonden...")
            return {
                "success": False,
                "query": query,
                "results": [],
                "message": f"{self.pet_name} heeft overal gezocht maar niks gevonden...",
                "duration": time.time() - start_time
            }

        # Sorteer op relevantie * confidence
        results.sort(key=lambda r: r.confidence * r.relevance, reverse=True)

        # Fase 4: PRESENTING - Toon trofeeën
        best_result = results[0]
        HuntAnimator.show_trophy(best_result)

        if best_result.trophy_type == "treasure":
            self._status_callback(HuntStatus.PROUD, "SCHATKIST gevonden!")
            self.xp += 50
        elif best_result.trophy_type == "bone":
            self._status_callback(HuntStatus.PROUD, "Goed botje!")
            self.xp += 20
        else:
            self._status_callback(HuntStatus.SAD, "Alleen klein resultaat...")
            self.xp += 5

        # Toon beste resultaat
        print(kleur(f"\n  RESULTAAT:", Kleur.GROEN))
        print(kleur(f"  {'-'*50}", Kleur.GROEN))

        # Pre-chewed output
        output = self._format_output(best_result, context)
        print(output)

        print(kleur(f"  {'-'*50}", Kleur.GROEN))

        duration = time.time() - start_time
        print(kleur(f"\n  Jacht duurde {duration:.1f}s | XP: +{self.xp}", Kleur.CYAAN))

        # Sla op in history
        self.history.append({
            "query": query,
            "context": context.detected_intent,
            "results": len(results),
            "best_source": best_result.bron,
            "confidence": best_result.confidence,
            "timestamp": datetime.now().isoformat()
        })

        return {
            "success": True,
            "query": query,
            "results": results,
            "best": best_result,
            "output": output,
            "duration": duration,
            "xp_gained": self.xp
        }

    def _format_output(self, result: HuntResult, context: HuntContext) -> str:
        """Format resultaat als 'pre-chewed' output."""
        lines = []

        # Intro gebaseerd op bron
        bron_intros = {
            "rag": f"  Kijk baas! Ik vond dit in onze eigen documenten:",
            "news": f"  Waf! Dit kwam net binnen van het nieuws:",
            "code": f"  *hijg* Ik heb dit opgegraven uit de code:",
            "web": f"  Ik vloog door het hele internet en vond:",
            "archive": f"  Dit lag verstopt in het archief:",
        }

        intro = bron_intros.get(result.bron, "  Ik vond dit:")
        lines.append(kleur(intro, Kleur.MAGENTA))
        lines.append("")

        # Content (beperkt)
        content = result.content[:500]
        if len(result.content) > 500:
            content += "..."

        for line in content.split("\n"):
            lines.append(f"  {line}")

        # Cross-reference als er context was
        if context.notes_context:
            lines.append("")
            lines.append(kleur("  [!] Dit sluit aan bij je recente notities!", Kleur.GEEL))

        return "\n".join(lines)

    def give_feedback(self, was_good: bool, source: str = None):
        """
        Good Boy / Bad Dog feedback.

        Args:
            was_good: True = Good Boy, False = Bad Dog
            source: Welke bron feedback krijgt
        """
        if was_good:
            print(kleur(f"\n  {self.pet_name}: *kwispelt wild* BRAAF! +10 XP", Kleur.GROEN))
            self.xp += 10
            if source and source in self.source_scores:
                self.source_scores[source] = min(2.0, self.source_scores[source] + 0.1)
        else:
            print(kleur(f"\n  {self.pet_name}: *laat oren hangen* Sorry baas...", Kleur.GEEL))
            if source and source in self.source_scores:
                self.source_scores[source] = max(0.1, self.source_scores[source] - 0.2)

    def get_stats(self) -> Dict:
        """Haal jacht statistieken op."""
        return {
            "total_hunts": len(self.history),
            "xp": self.xp,
            "source_scores": self.source_scores,
            "favorite_source": max(self.source_scores, key=self.source_scores.get),
            "recent_hunts": self.history[-5:] if self.history else []
        }


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def hunt(query: str, pet_name: str = "Buddy") -> Dict:
    """
    Snelle hunt functie.

    Args:
        query: Zoekvraag
        pet_name: Naam van het huisdier

    Returns:
        Hunt resultaten
    """
    hunter = UltimateHunt(pet_name)
    return asyncio.run(hunter.hunt(query))


def create_hunter(pet_name: str = "Buddy") -> UltimateHunt:
    """Maak een nieuwe hunter aan."""
    return UltimateHunt(pet_name)
