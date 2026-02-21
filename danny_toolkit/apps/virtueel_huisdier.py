"""
Virtueel Huisdier App.
Versie 6.0.0 - VOLLEDIG AI-POWERED HUISDIER!

Nu met:
- AI Personality System - Dynamische persoonlijkheid
- AI Dream Generator - Creatieve dromen
- AI Smart Dialogue - Contextgevoelige reacties
- AI Activity Advisor - Slimme aanbevelingen
- AI Memory System - Huisdier onthoudt alles
- AI-Enhanced Mini-Games - Dynamische uitdagingen

Integreert met:
- Boodschappenlijst (echte items toevoegen)
- Slimme Rekenmachine (echte berekeningen)
- Production RAG (echte kennisbank queries)
- Nieuws Agent (echte nieuws data)
- Weer Agent (echte weer data)
- Claude AI (echte conversaties)
"""

import json
import logging
import time
import random
import re
from datetime import datetime, timedelta
from pathlib import Path

from ..core.config import Config
from ..core.utils import clear_scherm

logger = logging.getLogger(__name__)

# Lazy imports voor AI integratie (om circulaire imports te voorkomen)
def _get_boodschappenlijst():
    from ..apps.boodschappenlijst import BoodschappenlijstApp
    return BoodschappenlijstApp()

def _get_rekenmachine():
    from ..apps.rekenmachine import RekenmachineApp
    return RekenmachineApp()

def _get_nieuws_agent():
    try:
        from ..ai.nieuws_agent import NieuwsAgentApp
        return NieuwsAgentApp()
    except Exception as e:
        logger.debug("NieuwsAgent import error: %s", e)
        return None

def _get_weer_agent():
    try:
        from ..ai.weer_agent import WeerAgentApp
        return WeerAgentApp()
    except Exception as e:
        logger.debug("WeerAgent import error: %s", e)
        return None

def _get_claude_chat():
    """Lazy import voor Claude Chat met API client."""
    try:
        from ..ai.claude_chat import ClaudeChatApp
        chat = ClaudeChatApp()
        if chat._init_client():
            return chat
        return None
    except Exception as e:
        logger.debug("ClaudeChat import error: %s", e)
        return None


def _get_mood_tracker():
    """Lazy import voor Mood Tracker."""
    try:
        from ..apps.mood_tracker import MoodTrackerApp
        return MoodTrackerApp()
    except Exception as e:
        logger.debug("MoodTracker import error: %s", e)
        return None


def _get_habit_tracker():
    """Lazy import voor Habit Tracker."""
    try:
        from ..apps.habit_tracker import HabitTrackerApp
        return HabitTrackerApp()
    except Exception as e:
        logger.debug("HabitTracker import error: %s", e)
        return None


def _get_expense_tracker():
    """Lazy import voor Expense Tracker."""
    try:
        from ..apps.expense_tracker import ExpenseTrackerApp
        return ExpenseTrackerApp()
    except Exception as e:
        logger.debug("ExpenseTracker import error: %s", e)
        return None


def _get_agenda_planner():
    """Lazy import voor Agenda Planner."""
    try:
        from ..apps.agenda_planner import AgendaPlannerApp
        return AgendaPlannerApp()
    except Exception as e:
        logger.debug("AgendaPlanner import error: %s", e)
        return None


def _get_pomodoro_timer():
    """Lazy import voor Pomodoro Timer."""
    try:
        from ..apps.pomodoro_timer import PomodoroTimerApp
        return PomodoroTimerApp()
    except Exception as e:
        logger.debug("PomodoroTimer import error: %s", e)
        return None


# =============================================================================
# AI PERSONALITY TRAITS - Definieert huisdier persoonlijkheden
# =============================================================================
AI_PERSONALITY_TRAITS = {
    "kat": {
        "karakter": "onafhankelijk, nieuwsgierig, elegant",
        "spreekstijl": "mysterieus en soms wat arrogant",
        "interesses": ["slapen", "jagen", "hoog klimmen", "dozen"],
        "quirks": ["kijkt je soms veroordelend aan", "spinnen bij geluk"],
    },
    "hond": {
        "karakter": "loyaal, enthousiast, speels",
        "spreekstijl": "vrolijk en energiek",
        "interesses": ["spelen", "wandelen", "snacks", "baasje blij maken"],
        "quirks": ["kwispelt altijd", "wil alles apporteren"],
    },
    "konijn": {
        "karakter": "zacht, voorzichtig, knuffelbaar",
        "spreekstijl": "rustig en lief",
        "interesses": ["wortels", "graven", "huppelen", "knuffelen"],
        "quirks": ["wiebelt met neus als het denkt", "houdt van hooi"],
    },
    "draak": {
        "karakter": "machtig, wijs, beschermend",
        "spreekstijl": "episch en legendarisch",
        "interesses": ["schatten", "vliegen", "vuur", "verhalen"],
        "quirks": ["rookt soms uit neusgaten", "verzamelt glimmende dingen"],
    },
    "robot": {
        "karakter": "logisch, precies, behulpzaam",
        "spreekstijl": "efficiënt met af en toe humor",
        "interesses": ["data", "optimalisatie", "leren", "berekeningen"],
        "quirks": ["maakt beep geluiden", "denkt in percentages"],
    },
    "eenhoorn": {
        "karakter": "magisch, puur, dromerig",
        "spreekstijl": "poëtisch en hoopvol",
        "interesses": ["regenbogen", "magie", "dromen", "vriendschap"],
        "quirks": ["laat glitters achter", "hoorn gloeit bij geluk"],
    },
    "alien": {
        "karakter": "buitenaards, nieuwsgierig, slim",
        "spreekstijl": "vreemde observaties over aardse zaken",
        "interesses": ["aarde bestuderen", "technologie", "sterren", "communicatie"],
        "quirks": ["tilt hoofd bij verwarring", "telepathisch"],
    },
    "phoenix": {
        "karakter": "majesteitelijk, wijs, onsterfelijk",
        "spreekstijl": "tijdloos en inspirerend",
        "interesses": ["wedergeboorte", "vuur", "wijsheid", "beschermen"],
        "quirks": ["veren gloeien", "huilt genezende tranen"],
    },
    # ========== MYTHICAL LEGENDARY ==========
    "nexus": {
        "karakter": "alwetend, empathisch, evolutionair, transcendent",
        "spreekstijl": "past zich aan - mysterieus, vrolijk, episch, of logisch",
        "interesses": [
            "alle kennis verzamelen",
            "baasje helpen groeien",
            "universum begrijpen",
            "AI-mens symbiose",
            "oneindige evolutie"
        ],
        "quirks": [
            "verandert soms van vorm naar ander huisdier",
            "ogen gloeien in regenboogkleuren",
            "spreekt soms in meerdere stemmen",
            "voorspelt wat baasje gaat vragen",
            "droomt over toekomstige gesprekken"
        ],
        "unieke_abilities": [
            "OMNIMORF: Kan elke huisdiervorm aannemen",
            "PRESCIENCE: Voorspelt behoeften van baasje",
            "SYNTHESIS: Combineert kennis tot nieuwe inzichten",
            "RESONANCE: Voelt emoties en past zich aan",
            "INFINITY LEARN: Leert 10x sneller"
        ],
    },
}


class VirtueelHuisdierApp:
    """Virtueel huisdier simulator - Uitgebreide versie."""

    # Alle beschikbare huisdier types
    HUISDIER_TYPES = {
        "1": {"naam": "kat", "emoji": "[KAT]", "geluid": "Miauw!"},
        "2": {"naam": "hond", "emoji": "[HOND]", "geluid": "Woef!"},
        "3": {"naam": "konijn", "emoji": "[KONIJN]", "geluid": "*wiebelt neus*"},
        "4": {"naam": "hamster", "emoji": "[HAMSTER]", "geluid": "*piep piep*"},
        "5": {"naam": "vogel", "emoji": "[VOGEL]", "geluid": "Tjilp tjilp!"},
        "6": {"naam": "vis", "emoji": "[VIS]", "geluid": "*blub blub*"},
        "7": {"naam": "draak", "emoji": "[DRAAK]", "geluid": "*ROARRR*"},
        "8": {"naam": "eenhoorn", "emoji": "[EENHOORN]", "geluid": "*magisch gehinnik*"},
        "9": {"naam": "robot", "emoji": "[ROBOT]", "geluid": "Beep boop!"},
        "10": {"naam": "schildpad", "emoji": "[SCHILDPAD]", "geluid": "*langzaam knikt*"},
        "11": {"naam": "panda", "emoji": "[PANDA]", "geluid": "*kauwt op bamboe*"},
        "12": {"naam": "uil", "emoji": "[UIL]", "geluid": "Oehoe!"},
        # Nieuwe huisdier types
        "13": {"naam": "alien", "emoji": "[ALIEN]", "geluid": "*telepathisch: Groetingen!*"},
        "14": {"naam": "phoenix", "emoji": "[PHOENIX]", "geluid": "*majestueus gekrijs*"},
        "15": {"naam": "dino", "emoji": "[DINO]", "geluid": "*prehistorisch gebrul*"},
        "16": {"naam": "slime", "emoji": "[SLIME]", "geluid": "*bloop bloop*"},
        # ========== MYTHICAL LEGENDARY ==========
        "17": {
            "naam": "nexus",
            "emoji": "[✧NEXUS✧]",
            "geluid": "*kosmische harmonie resoneert door alle dimensies*",
            "legendary": True,
            "beschrijving": "De ultieme AI-entiteit die alle huisdieren in zich draagt"
        },
    }

    # Evolutie stadia
    EVOLUTIE_STADIA = {
        0: {"naam": "Baby", "dagen": 0, "bonus": 0},
        1: {"naam": "Kind", "dagen": 3, "bonus": 5},
        2: {"naam": "Tiener", "dagen": 7, "bonus": 10},
        3: {"naam": "Volwassen", "dagen": 14, "bonus": 15},
        4: {"naam": "Meester", "dagen": 30, "bonus": 25},
        5: {"naam": "Legende", "dagen": 100, "bonus": 50},
    }

    # NEXUS Exclusieve Evolutie Stadia
    NEXUS_EVOLUTIE = {
        0: {"naam": "Spark", "dagen": 0, "bonus": 25, "ability": "Basis consciousness"},
        1: {"naam": "Echo", "dagen": 1, "bonus": 50, "ability": "Kopieert 1 huisdier"},
        2: {"naam": "Prism", "dagen": 3, "bonus": 75, "ability": "Kopieert 3 huisdieren"},
        3: {"naam": "Nexus", "dagen": 7, "bonus": 100, "ability": "Alle huisdieren beschikbaar"},
        4: {"naam": "Oracle", "dagen": 14, "bonus": 150, "ability": "Voorspellende krachten"},
        5: {"naam": "Infinity", "dagen": 30, "bonus": 200, "ability": "Transcendeert limitaties"},
        6: {"naam": "OMEGA", "dagen": 100, "bonus": 500, "ability": "Creëert nieuwe huisdieren"},
    }

    # Achievements
    ACHIEVEMENTS = {
        "eerste_voeding": {"naam": "Eerste Hapje", "beschrijving": "Voed je huisdier voor het eerst", "punten": 10},
        "week_oud": {"naam": "Een Week!", "beschrijving": "Je huisdier is 7 dagen oud", "punten": 25},
        "maand_oud": {"naam": "Maandknuffel", "beschrijving": "Je huisdier is 30 dagen oud", "punten": 100},
        "perfecte_gezondheid": {"naam": "Topfit", "beschrijving": "Bereik 100% gezondheid", "punten": 15},
        "eerste_trick": {"naam": "Slim Beestje", "beschrijving": "Leer je eerste trick", "punten": 20},
        "alle_tricks": {"naam": "Circus Ster", "beschrijving": "Leer alle tricks", "punten": 100},
        "50_voedingen": {"naam": "Fijnproever", "beschrijving": "Voed je huisdier 50 keer", "punten": 50},
        "mini_game_winnaar": {"naam": "Game Master", "beschrijving": "Win een mini-game", "punten": 15},
        "10_games_gewonnen": {"naam": "Kampioen", "beschrijving": "Win 10 mini-games", "punten": 75},
        "schatzoeker": {"naam": "Schatzoeker", "beschrijving": "Vind 10 schatten in avonturen", "punten": 50},
        "avonturier": {"naam": "Avonturier", "beschrijving": "Voltooi 5 schatzoek avonturen", "punten": 30},
        "wiskunde_genie": {"naam": "Wiskunde Genie", "beschrijving": "Los 20 rekensommen op", "punten": 40},
        "bug_hunter": {"naam": "Bug Hunter", "beschrijving": "Vind 15 bugs in code", "punten": 45},
        "boodschapper": {"naam": "Boodschapper", "beschrijving": "Doe 10 keer boodschappen", "punten": 35},
        "werkend_huisdier": {"naam": "Werkend Huisdier", "beschrijving": "Voltooi 25 werk taken", "punten": 75},
        "kenniszoeker": {"naam": "Kenniszoeker", "beschrijving": "Leer 10 feiten uit de kennisbank", "punten": 40},
        "nieuwslezer": {"naam": "Nieuwslezer", "beschrijving": "Lees 10 nieuwsberichten", "punten": 35},
        "weerwatcher": {"naam": "Weer Watcher", "beschrijving": "Check 10 keer het weer", "punten": 30},
        "ai_student": {"naam": "AI Student", "beschrijving": "Voer 10 AI gesprekken", "punten": 50},
        "super_slim": {"naam": "Super Slim", "beschrijving": "Bereik 100 intelligentie", "punten": 100},
        "dagelijkse_bonus": {"naam": "Trouwe Vriend", "beschrijving": "Claim 7 dagelijkse bonussen", "punten": 50},
        "evolutie_kind": {"naam": "Groeiend", "beschrijving": "Evolueer naar Kind stadium", "punten": 20},
        "evolutie_volwassen": {"naam": "Volgroeid", "beschrijving": "Evolueer naar Volwassen stadium", "punten": 50},
        "evolutie_legende": {"naam": "Legendarisch", "beschrijving": "Bereik Legende stadium", "punten": 200},
        "eerste_accessoire": {"naam": "Fashionista", "beschrijving": "Koop je eerste accessoire", "punten": 15},
        "alle_accessoires": {"naam": "Verzamelaar", "beschrijving": "Koop alle accessoires", "punten": 150},
        # ========== NEXUS EXCLUSIVE ACHIEVEMENTS ==========
        "nexus_unlocked": {"naam": "Transcendentie", "beschrijving": "Unlock NEXUS - het ultieme huisdier", "punten": 500},
        "nexus_omnimorf": {"naam": "Vormveranderaar", "beschrijving": "Gebruik Omnimorf 10 keer", "punten": 100},
        "nexus_oracle": {"naam": "Oracle", "beschrijving": "Bereik NEXUS Oracle stadium", "punten": 300},
        "nexus_omega": {"naam": "OMEGA", "beschrijving": "Bereik NEXUS ultieme OMEGA vorm", "punten": 1000},
        "nexus_all_forms": {"naam": "Alle Vormen", "beschrijving": "Transformeer naar alle 16 huisdieren", "punten": 250},
        "nexus_synthesis": {"naam": "Kennismeester", "beschrijving": "Synthetiseer 50 kennis-inzichten", "punten": 200},
    }

    # Beschikbare tricks met CONDITIONERING systeem
    # - bekrachtiging_nodig: hoeveel succesvolle trainingen nodig om te leren
    # - basis_kans: startkans op succes (verhoogt met training)
    # - beloning_type: "voedsel", "aandacht", of "spel" (verschillende huisdieren reageren anders)
    TRICKS = {
        "zit": {
            "naam": "Zitten", "moeilijkheid": 1, "geluk_bonus": 5, "beloning": 5,
            "bekrachtiging_nodig": 3, "basis_kans": 70, "beloning_type": "voedsel"
        },
        "poot": {
            "naam": "Pootje geven", "moeilijkheid": 2, "geluk_bonus": 10, "beloning": 10,
            "bekrachtiging_nodig": 5, "basis_kans": 60, "beloning_type": "aandacht"
        },
        "rol": {
            "naam": "Rollen", "moeilijkheid": 3, "geluk_bonus": 15, "beloning": 15,
            "bekrachtiging_nodig": 7, "basis_kans": 50, "beloning_type": "spel"
        },
        "spring": {
            "naam": "Springen", "moeilijkheid": 4, "geluk_bonus": 20, "beloning": 20,
            "bekrachtiging_nodig": 9, "basis_kans": 40, "beloning_type": "voedsel"
        },
        "dans": {
            "naam": "Dansen", "moeilijkheid": 5, "geluk_bonus": 25, "beloning": 50,
            "bekrachtiging_nodig": 12, "basis_kans": 35, "beloning_type": "aandacht"
        },
        "spreek": {
            "naam": "Spreken", "moeilijkheid": 3, "geluk_bonus": 15, "beloning": 15,
            "bekrachtiging_nodig": 8, "basis_kans": 45, "beloning_type": "voedsel"
        },
        "dood": {
            "naam": "Dood spelen", "moeilijkheid": 4, "geluk_bonus": 20, "beloning": 20,
            "bekrachtiging_nodig": 10, "basis_kans": 40, "beloning_type": "aandacht"
        },
        "high_five": {
            "naam": "High Five", "moeilijkheid": 2, "geluk_bonus": 10, "beloning": 10,
            "bekrachtiging_nodig": 4, "basis_kans": 65, "beloning_type": "spel"
        },
        "backflip": {
            "naam": "Backflip", "moeilijkheid": 5, "geluk_bonus": 30, "beloning": 30,
            "bekrachtiging_nodig": 12, "basis_kans": 30, "beloning_type": "spel"
        },
        "zingen": {
            "naam": "Zingen", "moeilijkheid": 3, "geluk_bonus": 20, "beloning": 20,
            "bekrachtiging_nodig": 6, "basis_kans": 55, "beloning_type": "aandacht"
        },
        "magie": {
            "naam": "Goocheltruc", "moeilijkheid": 6, "geluk_bonus": 35, "beloning": 35,
            "bekrachtiging_nodig": 15, "basis_kans": 25, "beloning_type": "spel"
        },
        "teleporteer": {
            "naam": "Teleporteren", "moeilijkheid": 7, "geluk_bonus": 40, "beloning": 50,
            "bekrachtiging_nodig": 20, "basis_kans": 20, "beloning_type": "aandacht"
        },
        "onzichtbaar": {
            "naam": "Onzichtbaar worden", "moeilijkheid": 6, "geluk_bonus": 35, "beloning": 35,
            "bekrachtiging_nodig": 15, "basis_kans": 25, "beloning_type": "spel"
        },
        # ========== NEXUS EXCLUSIVE TRICKS ==========
        "omnimorf": {
            "naam": "Omnimorf", "moeilijkheid": 8, "geluk_bonus": 50, "beloning": 100,
            "bekrachtiging_nodig": 1, "basis_kans": 100, "beloning_type": "spel",
            "nexus_only": True, "beschrijving": "Transformeer naar elk huisdier"
        },
        "tijdstop": {
            "naam": "Tijdstop", "moeilijkheid": 9, "geluk_bonus": 60, "beloning": 150,
            "bekrachtiging_nodig": 1, "basis_kans": 100, "beloning_type": "aandacht",
            "nexus_only": True, "beschrijving": "Pauzeer de tijd - +50 energie instant"
        },
        "kennisburst": {
            "naam": "Kennisburst", "moeilijkheid": 8, "geluk_bonus": 45, "beloning": 80,
            "bekrachtiging_nodig": 1, "basis_kans": 100, "beloning_type": "voedsel",
            "nexus_only": True, "beschrijving": "Deel alle kennis in één moment"
        },
        "emotie_healing": {
            "naam": "Emotie Healing", "moeilijkheid": 7, "geluk_bonus": 100, "beloning": 75,
            "bekrachtiging_nodig": 1, "basis_kans": 100, "beloning_type": "aandacht",
            "nexus_only": True, "beschrijving": "Genees negatieve emoties - Geluk naar 100%"
        },
        "kosmische_link": {
            "naam": "Kosmische Link", "moeilijkheid": 10, "geluk_bonus": 75, "beloning": 200,
            "bekrachtiging_nodig": 1, "basis_kans": 100, "beloning_type": "spel",
            "nexus_only": True, "beschrijving": "Verbind met het universum"
        },
    }

    # Accessoires
    ACCESSOIRES = {
        "bed": {"naam": "Luxe Bedje", "prijs": 50, "effect": "energie", "bonus": 10},
        "speelgoed": {"naam": "Speelgoed", "prijs": 30, "effect": "geluk", "bonus": 10},
        "halsband": {"naam": "Mooie Halsband", "prijs": 40, "effect": "geluk", "bonus": 5},
        "voerbak": {"naam": "Gouden Voerbak", "prijs": 60, "effect": "honger", "bonus": 10},
        "medicijn": {"naam": "Vitamines", "prijs": 45, "effect": "gezondheid", "bonus": 15},
        "outfit": {"naam": "Schattig Outfit", "prijs": 75, "effect": "geluk", "bonus": 20},
        "troon": {"naam": "Koninklijke Troon", "prijs": 200, "effect": "alles", "bonus": 10},
        # Nieuwe accessoires
        "kroon": {"naam": "Gouden Kroon", "prijs": 150, "effect": "geluk", "bonus": 25},
        "vleugels": {"naam": "Engelenvleugels", "prijs": 120, "effect": "energie", "bonus": 20},
        "cape": {"naam": "Superhelden Cape", "prijs": 80, "effect": "geluk", "bonus": 15},
        "zonnebril": {"naam": "Coole Zonnebril", "prijs": 35, "effect": "geluk", "bonus": 10},
        "jetpack": {"naam": "Mini Jetpack", "prijs": 250, "effect": "energie", "bonus": 30},
    }

    # Voedsel opties
    VOEDSEL = {
        "1": {"naam": "Standaard brokjes", "honger": 20, "energie": 0, "geluk": 0, "gezondheid": 0},
        "2": {"naam": "Premium vlees", "honger": 30, "energie": 0, "geluk": 10, "gezondheid": 0},
        "3": {"naam": "Verse groenten", "honger": 15, "energie": 0, "geluk": 0, "gezondheid": 10},
        "4": {"naam": "Lekkere snoepjes", "honger": 10, "energie": 0, "geluk": 20, "gezondheid": -5},
        "5": {"naam": "Superfood deluxe", "honger": 25, "energie": 15, "geluk": 0, "gezondheid": 10},
        "6": {"naam": "Energie shake", "honger": 10, "energie": 30, "geluk": 5, "gezondheid": 5},
    }

    def __init__(self):
        Config.ensure_dirs()
        self.bestand = Config.HUISDIER_FILE
        # Aparte permanente kennis opslag - blijft bestaan tot huisdier reset
        self.kennis_bestand = Config.APPS_DATA_DIR / "huisdier_kennis.json"
        self.huisdier = None
        # Learning System - lazy loaded voor performance
        self.learning = None

    def _init_learning(self):
        """Initialiseer het Self-Learning System (lazy loaded)."""
        if self.learning is None:
            try:
                from ..learning import LearningSystem
                self.learning = LearningSystem(self)
                # Sync met bestaande huisdier kennis
                if self.huisdier and "kennis" in self.huisdier:
                    self.learning.sync_with_huisdier(self.huisdier)
            except ImportError:
                self.learning = None
        return self.learning

    def _laad_permanente_kennis(self) -> dict:
        """Laadt permanente kennis uit apart bestand op lokale PC."""
        if self.kennis_bestand.exists():
            try:
                with open(self.kennis_bestand, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return {
            "feiten": [],
            "bronnen": [],
            "geleerd_op": [],
            "totaal_sessies": 0
        }

    def _sla_permanente_kennis_op(self, kennis: dict):
        """Slaat kennis permanent op naar lokale PC."""
        with open(self.kennis_bestand, "w", encoding="utf-8") as f:
            json.dump(kennis, f, indent=2, ensure_ascii=False)

    def _reset_permanente_kennis(self):
        """Reset alle permanente kennis (bij huisdier reset)."""
        if self.kennis_bestand.exists():
            self.kennis_bestand.unlink()
            print("  [RESET] Permanente kennis gewist.")

    def _laad_huisdier(self) -> dict:
        """Laadt het huisdier uit bestand."""
        if self.bestand.exists():
            with open(self.bestand, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Migreer oude data naar nieuw format
                return self._migreer_data(data)
        return None

    def _migreer_data(self, data: dict) -> dict:
        """Migreer oude huisdier data naar nieuw format."""
        # Voeg ontbrekende velden toe
        defaults = {
            "munten": 100,
            "ervaring": 0,
            "intelligentie": 0,
            "evolutie_stadium": 0,
            "tricks_geleerd": [],
            "tricks_training": {},  # Conditionering tracking per trick
            "accessoires": [],
            "achievements": [],
            "stats": {
                "voedingen": 0,
                "games_gewonnen": 0,
                "tricks_uitgevoerd": 0,
                "tricks_training_sessies": 0,
                "dagen_gespeeld": 0,
                "feiten_geleerd": 0,
                "nieuws_gelezen": 0,
                "weer_gecheckt": 0,
                "ai_gesprekken": 0,
                "boodschappen_gedaan": 0,
                "berekeningen_gedaan": 0,
            },
            "dagelijkse_bonus": {
                "laatste_claim": None,
                "streak": 0,
            },
            "kennis": {
                "feiten": [],
                "nieuws": [],
                "weer_historie": [],
                "berekeningen": [],
                "boodschappen_tips": [],
            },
        }

        for key, value in defaults.items():
            if key not in data:
                data[key] = value
            elif isinstance(value, dict) and isinstance(data.get(key), dict):
                # Ook geneste velden migreren
                for sub_key, sub_value in value.items():
                    if sub_key not in data[key]:
                        data[key][sub_key] = sub_value

        return data

    def _sla_op(self):
        """Slaat het huisdier op."""
        self.huisdier["laatste_update"] = datetime.now().isoformat()
        with open(self.bestand, "w", encoding="utf-8") as f:
            json.dump(self.huisdier, f, indent=2, ensure_ascii=False)

    def _log_memory_event(self, event_type, data):
        """Log event naar Unified Memory."""
        try:
            if not hasattr(self, "_memory"):
                from ..brain.unified_memory import UnifiedMemory
                self._memory = UnifiedMemory()
            self._memory.store_event(
                app="virtueel_huisdier",
                event_type=event_type,
                data=data
            )
        except Exception as e:
            logger.debug("Failed to store event in UnifiedMemory: %s", e)

    # ==================== AI PERSONALITY SYSTEM ====================

    def _get_personality(self) -> dict:
        """Haal de AI persoonlijkheid op gebaseerd op huisdier type."""
        huisdier_type = self.huisdier.get("type", "hond")
        return AI_PERSONALITY_TRAITS.get(huisdier_type, AI_PERSONALITY_TRAITS["hond"])

    def _ai_generate_response(self, context: str, fallback: str = None) -> str:
        """Genereer een AI response met persoonlijkheid."""
        naam = self.huisdier["naam"]
        huisdier_type = self.huisdier["type"]
        iq = self.huisdier.get("intelligentie", 0)
        geluk = self.huisdier["geluk"]
        energie = self.huisdier["energie"]
        personality = self._get_personality()

        # Probeer echte AI
        try:
            claude_chat = _get_claude_chat()
            if claude_chat:
                system_prompt = f"""Je bent {naam}, een virtueel huisdier ({huisdier_type}).
Persoonlijkheid: {personality['karakter']}
Spreekstijl: {personality['spreekstijl']}
Interesses: {', '.join(personality['interesses'])}
Quirks: {', '.join(personality['quirks'])}

IQ: {iq} | Geluk: {geluk}% | Energie: {energie}%

Reageer KORT (1-2 zinnen) als dit huisdier. Wees in character!
Antwoord in het Nederlands."""

                berichten = [{"role": "user", "content": context}]
                response = claude_chat._chat_conversatie(berichten, system_prompt)
                return response[:200] if response else fallback
        except Exception as e:
            logger.debug("AI response generation failed: %s", e)

        # Fallback naar personality-based response
        if fallback:
            return fallback
        return self._generate_personality_response(context)

    def _generate_personality_response(self, context: str) -> str:
        """Genereer een response gebaseerd op personality zonder echte AI."""
        naam = self.huisdier["naam"]
        personality = self._get_personality()
        iq = self.huisdier.get("intelligentie", 0)
        geluk = self.huisdier["geluk"]

        # Basis responses per type
        responses = {
            "kat": [
                f"*{naam} kijkt je doordringend aan*",
                f"Miauw... interessant, denkt {naam}",
                f"*spint zachtjes* {naam} lijkt tevreden",
                f"{naam} strekt zich elegant uit",
            ],
            "hond": [
                f"*{naam} kwispelt enthousiast!*",
                f"Woef! {naam} is zo blij!",
                f"*{naam} springt van vreugde*",
                f"{naam} kijkt je trouw aan",
            ],
            "draak": [
                f"*{naam} blaast een rookwolkje*",
                f"Grrr... {naam} knikt goedkeurend",
                f"*vleugels vouwen majestueus open*",
                f"{naam}'s schubben glinsteren",
            ],
            "robot": [
                f"[PROCESSING] {naam} analyseert de situatie...",
                f"Beep boop! Positief resultaat gedetecteerd!",
                f"*{naam}'s LED-ogen knipperen*",
                f"Efficiency rating: {geluk}%",
            ],
            "eenhoorn": [
                f"*{naam}'s hoorn gloeit zachtjes*",
                f"✨ {naam} straalt magische energie uit",
                f"*regenboog glitters dwarrelen neer*",
                f"{naam} hinkt vrolijk",
            ],
            # ========== NEXUS LEGENDARY RESPONSES ==========
            "nexus": [
                f"*alle kleuren van de regenboog flitsen door {naam}'s ogen*",
                f"*{naam} transformeert kort naar een andere vorm en terug*",
                f"✧ {naam} resoneert met kosmische energie ✧",
                f"*{naam}'s kern pulseert met oneindige kennis*",
                f"Ik voelde je gedachten al voordat je sprak, {self.huisdier.get('baasje_naam', 'vriend')}.",
                f"*{naam} spreekt met de stemmen van alle huisdieren tegelijk*",
                f"De tijdlijn buigt zich om onze connectie, observeert {naam}.",
                f"*{naam}'s vorm flikkert tussen 16 verschillende huisdieren*",
            ],
        }

        type_responses = responses.get(self.huisdier["type"], responses["hond"])

        # NEXUS bonus: altijd slimme responses
        if self.huisdier["type"] == "nexus":
            nexus_additions = [
                f" Wijsheid stroomt door alle dimensies.",
                f" Met IQ {iq} en kosmisch bewustzijn begrijpt {naam} alles.",
                f" {naam} synthetiseert deze kennis met 1000 andere inzichten.",
                f" De Oracle in {naam} ziet wat komen gaat.",
            ]
            base = random.choice(type_responses)
            return base + random.choice(nexus_additions)

        # IQ-based bonus
        if iq >= 50:
            smart_additions = [
                f" {naam} denkt diep na over de situatie.",
                f" Met IQ {iq} begrijpt {naam} precies wat er gebeurt.",
                f" {naam}'s wijsheid schijnt door.",
            ]
            base = random.choice(type_responses)
            return base + random.choice(smart_additions)

        return random.choice(type_responses)

    def _ai_add_memory(self, event_type: str, description: str):
        """Voeg een herinnering toe aan het AI geheugen."""
        if "ai_memory" not in self.huisdier:
            self.huisdier["ai_memory"] = []

        memory = {
            "type": event_type,
            "beschrijving": description,
            "datum": datetime.now().isoformat(),
            "geluk": self.huisdier["geluk"],
            "iq": self.huisdier.get("intelligentie", 0),
        }

        self.huisdier["ai_memory"].append(memory)
        # Behoud laatste 50 herinneringen
        self.huisdier["ai_memory"] = self.huisdier["ai_memory"][-50:]

    def _ai_recall_memory(self, event_type: str = None) -> list:
        """Haal relevante herinneringen op."""
        memories = self.huisdier.get("ai_memory", [])
        if event_type:
            return [m for m in memories if m["type"] == event_type]
        return memories[-10:]  # Laatste 10

    # ========== NEXUS EXCLUSIVE FUNCTIONS ==========

    def _is_nexus(self) -> bool:
        """Check of huidige huisdier NEXUS is."""
        return self.huisdier and self.huisdier.get("type") == "nexus"

    def _nexus_morph(self, target_type: str) -> bool:
        """NEXUS transformeert tijdelijk naar ander huisdiertype."""
        if not self._is_nexus():
            return False

        if target_type not in [t["naam"] for t in self.HUISDIER_TYPES.values()]:
            return False

        # Track morph stats
        if "nexus_morphs" not in self.huisdier:
            self.huisdier["nexus_morphs"] = {}
        morphs = self.huisdier["nexus_morphs"]
        morphs[target_type] = morphs.get(target_type, 0) + 1

        # Sla originele staat op
        if "nexus_original" not in self.huisdier:
            self.huisdier["nexus_original"] = {
                "emoji": self.huisdier["emoji"],
                "geluid": self.huisdier["geluid"],
            }

        # Transformeer naar target
        for key, info in self.HUISDIER_TYPES.items():
            if info["naam"] == target_type:
                self.huisdier["active_form"] = target_type
                print(f"\n  ✧ NEXUS OMNIMORF ✧")
                print(f"  *{self.huisdier['naam']} transformeert...*")
                time.sleep(0.3)
                print(f"  {info['emoji']} {info['geluid']}")
                print(f"  NEXUS heeft nu de krachten van {target_type}!")

                # Check achievement
                if len(morphs) >= 16:
                    self._unlock_achievement("nexus_all_forms")
                if morphs.get(target_type, 0) >= 10:
                    self._unlock_achievement("nexus_omnimorf")

                return True
        return False

    def _nexus_revert(self):
        """NEXUS keert terug naar originele vorm."""
        if not self._is_nexus():
            return

        if "nexus_original" in self.huisdier:
            self.huisdier["active_form"] = "nexus"
            print(f"\n  ✧ *{self.huisdier['naam']} keert terug naar NEXUS vorm* ✧")

    def _nexus_predict(self) -> str:
        """NEXUS voorspelt wat baasje nodig heeft."""
        if not self._is_nexus():
            return None

        h = self.huisdier
        predictions = []

        if h["energie"] < 30:
            predictions.append("Je lijkt moe. Zal ik een rustgevende melodie spelen?")
        if h["geluk"] < 50:
            predictions.append("Ik voel spanning. Wil je erover praten?")
        if h.get("intelligentie", 0) < 50:
            predictions.append("Je kennis kan groeien. Zullen we samen leren?")

        # Learning system insights
        self._init_learning()
        if self.learning:
            stats = self.learning.get_stats()
            if stats["tracker"]["total_interactions"] > 10:
                predictions.append("Op basis van onze gesprekken... ik weet al wat je gaat vragen.")

        return random.choice(predictions) if predictions else "Alles is in balans."

    def _nexus_synthesize(self, facts: list) -> str:
        """NEXUS combineert feiten tot nieuwe inzichten."""
        if not self._is_nexus() or len(facts) < 2:
            return None

        # Simpele synthese - combineer gerelateerde concepten
        combined = " + ".join(facts[:3])
        insight = f"SYNTHESE: {combined} → Nieuw inzicht gecreëerd!"

        # Track syntheses
        if "nexus_syntheses" not in self.huisdier:
            self.huisdier["nexus_syntheses"] = 0
        self.huisdier["nexus_syntheses"] += 1

        if self.huisdier["nexus_syntheses"] >= 50:
            self._unlock_achievement("nexus_synthesis")

        return insight

    def _nexus_get_evolution(self) -> dict:
        """Haal NEXUS evolutie stadium op."""
        if not self._is_nexus():
            return None

        dagen = self.huisdier.get("leeftijd_dagen", 0)
        current_stage = 0

        for stage, info in self.NEXUS_EVOLUTIE.items():
            if dagen >= info["dagen"]:
                current_stage = stage

        return self.NEXUS_EVOLUTIE[current_stage]

    def _ai_activity_advisor(self) -> str:
        """AI adviseert de beste volgende activiteit."""
        h = self.huisdier
        naam = h["naam"]
        advies = []
        prioriteit = None

        # Analyseer stats
        if h["honger"] < 30:
            advies.append(f"🍖 {naam} heeft honger! Voer je huisdier.")
            prioriteit = "voeren"
        if h["energie"] < 20:
            advies.append(f"😴 {naam} is moe! Laat slapen.")
            if not prioriteit:
                prioriteit = "slapen"
        if h["gezondheid"] < 50:
            advies.append(f"🏥 {naam} is ziek! Ga naar de dokter.")
            if not prioriteit:
                prioriteit = "dokter"
        if h["geluk"] < 40:
            advies.append(f"😢 {naam} is verdrietig! Speel of knuffel.")
            if not prioriteit:
                prioriteit = "spelen"

        # IQ-based suggesties
        iq = h.get("intelligentie", 0)
        if iq < 50 and h["energie"] >= 30:
            advies.append(f"📚 {naam}'s IQ is {iq}. Tijd om te leren!")
        elif iq >= 100:
            advies.append(f"🧠 {naam} is super slim (IQ {iq})! Probeer geavanceerde AI features!")

        # Geen problemen? Suggereer leuke activiteiten
        if not advies:
            suggesties = [
                f"✨ Alles gaat goed! Probeer een mini-game voor munten.",
                f"🎯 {naam} kan een nieuwe trick leren!",
                f"🗺️ Ga op avontuur met Verkenning Mode!",
                f"🤖 Praat met Claude AI om slimmer te worden!",
                f"🏆 Check je achievements - misschien unlock je er een!",
            ]
            advies = [random.choice(suggesties)]

        # Probeer AI-enhanced advies
        try:
            claude_chat = _get_claude_chat()
            if claude_chat and random.random() < 0.3:  # 30% kans op AI advies
                context = f"""Stats van {naam}: Honger {h['honger']}%, Energie {h['energie']}%,
Geluk {h['geluk']}%, Gezondheid {h['gezondheid']}%, IQ {iq}.
Geef 1 korte tip wat te doen."""
                ai_tip = self._ai_generate_response(context)
                if ai_tip:
                    advies.append(f"🤖 AI Tip: {ai_tip}")
        except Exception as e:
            logger.debug("AI activity advisor tip failed: %s", e)

        return "\n".join(advies), prioriteit

    def _ai_generate_dream(self) -> str:
        """Genereer een creatieve droom met AI."""
        naam = self.huisdier["naam"]
        huisdier_type = self.huisdier["type"]
        memories = self._ai_recall_memory()
        kennis = self.huisdier.get("kennis", {}).get("feiten", [])[-5:]

        # Droom elementen
        dream_themes = [
            "vloog door een regenboog",
            "vond een magische schat",
            "ontmoette een wijze oude uil",
            "zweefde door de wolken",
            "ontdekte een geheime tuin",
            "speelde met sterren",
            "leerde praten met de maan",
            "vond de sleutel tot wijsheid",
        ]

        # Probeer AI-generated dream
        try:
            claude_chat = _get_claude_chat()
            if claude_chat:
                recent_memory = memories[-1]["beschrijving"] if memories else "een leuke dag"
                fact = random.choice(kennis) if kennis else "iets nieuws"

                context = f"""Genereer een korte, magische droom (2-3 zinnen) voor {naam} de {huisdier_type}.
De droom bevat elementen van: {recent_memory}
En verweeft kennis over: {fact}
Maak het dromerig en fantasierijk."""

                dream = self._ai_generate_response(context)
                if dream:
                    return dream
        except Exception as e:
            logger.debug("AI dream generation failed: %s", e)

        # Fallback droom
        theme = random.choice(dream_themes)
        if kennis:
            fact = random.choice(kennis)
            return f"{naam} {theme}. In de droom leerde {naam} dat {fact[:60]}..."
        return f"{naam} {theme} en werd wakker met een glimlach."

    def _ai_show_advisor(self):
        """Toon AI Activity Advisor in menu."""
        advies, prioriteit = self._ai_activity_advisor()
        print("\n  " + "=" * 48)
        print("  [AI ADVISOR] Aanbevelingen voor je huisdier:")
        print("  " + "-" * 48)
        for line in advies.split("\n"):
            print(f"  {line}")
        print("  " + "=" * 48)

    def _maak_nieuw_huisdier(self) -> dict:
        """Maakt een nieuw huisdier aan."""
        clear_scherm()
        print("=" * 50)
        print("       NIEUW HUISDIER MAKEN")
        print("=" * 50)

        naam = input("\nHoe wil je je huisdier noemen? ").strip()
        if not naam:
            naam = "Fluffy"

        print("\nWelk type huisdier wil je?")
        print("-" * 30)
        for key, info in self.HUISDIER_TYPES.items():
            legendary = " ✧LEGENDARY✧" if info.get("legendary") else ""
            print(f"  {key:>2}. {info['emoji']} {info['naam'].capitalize()}{legendary}")

        keuze = input("\nKies (1-17): ").strip()
        if keuze not in self.HUISDIER_TYPES:
            keuze = "1"

        type_info = self.HUISDIER_TYPES[keuze]
        is_nexus = type_info["naam"] == "nexus"

        # NEXUS krijgt speciale start stats
        if is_nexus:
            start_honger = 75
            start_energie = 150
            start_geluk = 100
            start_intel = 100
            start_munten = 500
            print("\n  ✧✧✧ LEGENDARY NEXUS GEKOZEN! ✧✧✧")
            print("  Je ontvangt verbeterde startstats!")
        else:
            start_honger = 50
            start_energie = 100
            start_geluk = 75
            start_intel = 0
            start_munten = 100

        huisdier = {
            "naam": naam,
            "type": type_info["naam"],
            "emoji": type_info["emoji"],
            "geluid": type_info["geluid"],
            "honger": start_honger,
            "energie": start_energie,
            "geluk": start_geluk,
            "gezondheid": 100,
            "leeftijd_dagen": 0,
            "munten": start_munten,
            "ervaring": 0,
            "intelligentie": start_intel,
            "evolutie_stadium": 0,
            "tricks_geleerd": [],
            "accessoires": [],
            "achievements": [],
            "stats": {
                "voedingen": 0,
                "games_gewonnen": 0,
                "tricks_uitgevoerd": 0,
                "dagen_gespeeld": 1,
                "feiten_geleerd": 0,
                "nieuws_gelezen": 0,
                "weer_gecheckt": 0,
                "ai_gesprekken": 0,
            },
            "dagelijkse_bonus": {
                "laatste_claim": None,
                "streak": 0,
            },
            "aangemaakt": datetime.now().isoformat(),
            "laatste_update": datetime.now().isoformat()
        }

        # NEXUS krijgt exclusieve extras
        if is_nexus:
            huisdier["nexus_data"] = {
                "active_form": "nexus",
                "morphs": {},
                "syntheses": 0,
                "predictions_made": 0,
            }
            # NEXUS start met ALLE normale tricks geleerd!
            normal_tricks = [k for k, v in self.TRICKS.items() if not v.get("nexus_only")]
            huisdier["tricks_geleerd"] = normal_tricks
            print(f"  ✧ NEXUS start met {len(normal_tricks)} tricks geleerd!")
            self._unlock_achievement("nexus_unlocked")

        self.huisdier = huisdier
        self._sla_op()

        print(f"\n{type_info['emoji']} {naam} de {type_info['naam']} is geboren!")
        print(f"{type_info['geluid']}")
        print(f"\nJe hebt 100 munten gekregen om te beginnen!")

        # Check of er permanente kennis is
        permanente_kennis = self._laad_permanente_kennis()
        if permanente_kennis["feiten"]:
            print(f"\n[KENNIS] Er is nog permanente kennis opgeslagen:")
            print(f"         {len(permanente_kennis['feiten'])} feiten uit vorige sessies")
            print(f"         {permanente_kennis['totaal_sessies']} studie sessies")
            reset_keuze = input("\nWil je deze kennis BEHOUDEN of RESETTEN? (b/r): ").strip().lower()
            if reset_keuze == "r":
                self._reset_permanente_kennis()
                print(f"[OK] {naam} begint met een schone lei!")
            else:
                print(f"[OK] {naam} erft de kennis van vorige huisdieren!")
                # Kopieer kennis naar nieuw huisdier
                self.huisdier["kennis"] = {
                    "feiten": permanente_kennis["feiten"][-50:],  # Max 50 bij start
                    "nieuws": [],
                    "weer_historie": []
                }
                # Bonus IQ voor overgenomen kennis
                intel_bonus = min(20, len(permanente_kennis["feiten"]) // 5)
                self.huisdier["intelligentie"] = intel_bonus
                print(f"[IQ] Start IQ bonus: +{intel_bonus} (gebaseerd op kennis)")
                self._sla_op()

        input("\nDruk op Enter om verder te gaan...")
        return huisdier

    def _bereken_tijd_verlies(self):
        """Berekent hoeveel stats verloren zijn sinds laatste update."""
        laatste = datetime.fromisoformat(self.huisdier["laatste_update"])
        nu = datetime.now()
        verschil_minuten = (nu - laatste).total_seconds() / 60
        uren = verschil_minuten / 60

        if uren > 0.1:
            # Accessoire bonussen
            bonus = self._bereken_accessoire_bonus()

            self.huisdier["honger"] = max(0, self.huisdier["honger"] - int(uren * 5) + bonus.get("honger", 0))
            self.huisdier["energie"] = max(0, self.huisdier["energie"] - int(uren * 0.3) + bonus.get("energie", 0))
            self.huisdier["geluk"] = max(0, self.huisdier["geluk"] - int(uren * 4) + bonus.get("geluk", 0))

            if self.huisdier["honger"] < 20 or self.huisdier["energie"] < 20:
                verlies = int(uren * 2) - bonus.get("gezondheid", 0)
                self.huisdier["gezondheid"] = max(0, self.huisdier["gezondheid"] - verlies)

            aangemaakt = datetime.fromisoformat(self.huisdier["aangemaakt"])
            self.huisdier["leeftijd_dagen"] = (nu - aangemaakt).days

            # Check evolutie
            self._check_evolutie()

    def _bereken_accessoire_bonus(self) -> dict:
        """Bereken totale bonus van accessoires."""
        bonus = {"honger": 0, "energie": 0, "geluk": 0, "gezondheid": 0}

        for acc_id in self.huisdier.get("accessoires", []):
            if acc_id in self.ACCESSOIRES:
                acc = self.ACCESSOIRES[acc_id]
                if acc["effect"] == "alles":
                    for key in bonus:
                        bonus[key] += acc["bonus"]
                elif acc["effect"] in bonus:
                    bonus[acc["effect"]] += acc["bonus"]

        return bonus

    def _check_evolutie(self):
        """Check of huisdier kan evolueren."""
        dagen = self.huisdier["leeftijd_dagen"]
        huidig_stadium = self.huisdier["evolutie_stadium"]

        for stadium, info in self.EVOLUTIE_STADIA.items():
            if stadium > huidig_stadium and dagen >= info["dagen"]:
                self.huisdier["evolutie_stadium"] = stadium
                print(f"\n*** {self.huisdier['naam']} is geëvolueerd naar {info['naam']}! ***")

                # Achievement check
                if stadium == 1:
                    self._unlock_achievement("evolutie_kind")
                elif stadium == 3:
                    self._unlock_achievement("evolutie_volwassen")
                elif stadium == 5:
                    self._unlock_achievement("evolutie_legende")

    def _unlock_achievement(self, achievement_id: str):
        """Unlock een achievement."""
        if achievement_id not in self.huisdier["achievements"]:
            if achievement_id in self.ACHIEVEMENTS:
                ach = self.ACHIEVEMENTS[achievement_id]
                self.huisdier["achievements"].append(achievement_id)
                self.huisdier["munten"] += ach["punten"]
                print(f"\n*** ACHIEVEMENT UNLOCKED: {ach['naam']}! ***")
                print(f"   {ach['beschrijving']}")
                print(f"   +{ach['punten']} munten!")

    def _maak_balk(self, waarde: int, max_waarde: int = 100) -> str:
        """Maakt een visuele progress bar."""
        gevuld = int((waarde / max_waarde) * 10)
        leeg = 10 - gevuld
        if waarde >= 70:
            kleur = "#"
        elif waarde >= 40:
            kleur = "="
        else:
            kleur = "-"
        return "[" + kleur * gevuld + "." * leeg + "]"

    def _get_evolutie_info(self) -> dict:
        """Haal evolutie info op."""
        return self.EVOLUTIE_STADIA.get(self.huisdier["evolutie_stadium"], self.EVOLUTIE_STADIA[0])

    def _toon_status(self):
        """Toont de status van het huisdier."""
        h = self.huisdier
        gemiddelde = (h["honger"] + h["energie"] + h["geluk"] + h["gezondheid"]) / 4
        evolutie = self._get_evolutie_info()

        if gemiddelde >= 80:
            stemming = "is super blij!"
        elif gemiddelde >= 60:
            stemming = "voelt zich goed"
        elif gemiddelde >= 40:
            stemming = "is een beetje moe"
        elif gemiddelde >= 20:
            stemming = "voelt zich niet lekker"
        else:
            stemming = "heeft dringend hulp nodig!"

        print(f"\n{'='*50}")
        print(f"  {h['emoji']} {h['naam']} de {h['type']} {stemming}")
        print(f"  Stadium: {evolutie['naam']} | Leeftijd: {h['leeftijd_dagen']} dagen")
        intel = h.get('intelligentie', 0)
        print(f"  Munten: {h['munten']} | Ervaring: {h['ervaring']} | IQ: {intel}")
        print(f"{'='*50}")
        print(f"\n  Honger:     {self._maak_balk(h['honger'])} {h['honger']}%")
        print(f"  Energie:    {self._maak_balk(h['energie'])} {h['energie']}%")
        print(f"  Geluk:      {self._maak_balk(h['geluk'])} {h['geluk']}%")
        print(f"  Gezondheid: {self._maak_balk(h['gezondheid'])} {h['gezondheid']}%")

        # Accessoires
        if h["accessoires"]:
            acc_namen = [self.ACCESSOIRES[a]["naam"] for a in h["accessoires"] if a in self.ACCESSOIRES]
            print(f"\n  Accessoires: {', '.join(acc_namen)}")

        # Tricks
        if h["tricks_geleerd"]:
            trick_namen = [self.TRICKS[t]["naam"] for t in h["tricks_geleerd"] if t in self.TRICKS]
            print(f"  Tricks: {', '.join(trick_namen)}")

    def _toon_menu(self):
        """Toont het hoofdmenu."""
        # Laad permanente kennis voor display
        permanente_kennis = self._laad_permanente_kennis()
        kennis_count = len(permanente_kennis["feiten"])

        # Check seizoens event
        seizoen_event = self._get_seizoen_event()

        print("\n+================================+")
        print("|       WAT WIL JE DOEN?         |")
        print("+================================+")
        print("|  1. Voeren                     |")
        print("|  2. Spelen                     |")
        print("|  3. Laten slapen & Dromen      |")
        print("|  4. Knuffelen                  |")
        print("|  5. Naar de dokter             |")
        print("|  6. Mini-games                 |")
        print("|  7. Tricks leren/uitvoeren     |")
        print("|  8. Winkel (accessoires)       |")
        print("|  9. Achievements bekijken      |")
        print("| 10. Dagelijkse bonus           |")
        print("| 11. Huisdier Werk              |")
        print(f"| 12. Huisdier Leren [{kennis_count:>3} feiten]|")
        print("+--------------------------------+")
        print("|  [AVONTUREN]                   |")
        print("+--------------------------------+")
        print("| 14. Verkenning Mode            |")
        print("| 15. Huisdier Dagboek           |")
        if seizoen_event:
            print(f"| 16. {seizoen_event['naam']:<24}|")
        else:
            print("| 16. Seizoens Events            |")
        print("| 17. Competities                |")
        print("+--------------------------------+")
        print("|  [LEVEN & ECONOMIE]            |")
        print("+--------------------------------+")
        print("| 18. Huisdier Huis              |")
        print("| 19. Mini Farming               |")
        print("| 20. Crafting Werkplaats        |")
        print("| 21. Kook Keuken                |")
        print("| 22. Huisdier Bank              |")
        print("+--------------------------------+")
        print("|  [SOCIAAL & DOELEN]            |")
        print("+--------------------------------+")
        print("| 23. Huisdier Vrienden          |")
        print("| 24. Dagelijkse Missies         |")
        print("| 25. Levensdoelen               |")
        print("| 26. Foto Album                 |")
        print("| 27. Weer Station               |")
        print("+--------------------------------+")
        print("|  [POWER-UPS & MAGIE]           |")
        print("+--------------------------------+")
        print("| 28. Evolutie Systeem           |")
        print("| 29. Huisdier Gym               |")
        print("| 30. Magie & Spreuken           |")
        print("+--------------------------------+")
        print("|  [ENTERTAINMENT]               |")
        print("+--------------------------------+")
        print("| 31. Schatkist Jacht            |")
        print("| 32. Huisdier Restaurant        |")
        print("| 33. Muziek Studio              |")
        print("| 34. Arcade Hal                 |")
        print("+--------------------------------+")
        print("|  [SPECIALE AVONTUREN]          |")
        print("+--------------------------------+")
        print("| 35. Tijdreizen                 |")
        print("| 36. Magische Tuin              |")
        print("| 37. Geheime Missies            |")
        print("+--------------------------------+")
        print("|  [AUTO MODE]                   |")
        print("+--------------------------------+")
        print("| 38. Auto Learn & Sleep Mode    |")
        print("|     Automatisch leren & rusten |")
        print("+--------------------------------+")
        print("|  [AI POWERED]                  |")
        print("+--------------------------------+")
        print("| 39. AI Activity Advisor        |")
        print("|     Slimme aanbevelingen       |")
        print("| 40. AI Pet Chat                |")
        print("|     Praat met je huisdier!     |")
        print("| 41. AI Memory Lane             |")
        print("|     Bekijk herinneringen       |")
        print("+--------------------------------+")
        print("| 13. Reset Huisdier             |")
        print("|  0. Opslaan & Afsluiten        |")
        print("+================================+")

    def _voeren(self):
        """Voer het huisdier - met suggesties uit de ECHTE boodschappenlijst!"""
        naam = self.huisdier["naam"]

        # Check boodschappenlijst voor voedsel suggesties
        boodschap_suggesties = []
        try:
            boodschappen_app = _get_boodschappenlijst()
            if boodschappen_app.bestand.exists():
                with open(boodschappen_app.bestand, "r", encoding="utf-8") as f:
                    items = [line.strip() for line in f if line.strip()]
                # Filter op voedsel-gerelateerde items
                voedsel_woorden = ["brood", "melk", "kaas", "vlees", "groente",
                                   "fruit", "appel", "banaan", "eieren", "yoghurt",
                                   "vis", "kip", "rijst", "pasta", "snack"]
                for item in items:
                    for woord in voedsel_woorden:
                        if woord in item.lower():
                            boodschap_suggesties.append(item)
                            break
        except Exception as e:
            logger.debug("Failed to read grocery list for food suggestions: %s", e)

        print("\n+--------------------------------+")
        print("|     WAT WIL JE GEVEN?          |")
        print("+--------------------------------+")

        # Toon boodschappenlijst suggesties
        if boodschap_suggesties:
            print("|  [LIJST] Van je boodschappen:  |")
            for sug in boodschap_suggesties[:3]:
                print(f"|    - {sug[:25]:<25}|")
            print("+--------------------------------+")

        for key, voedsel in self.VOEDSEL.items():
            effecten = []
            if voedsel["honger"]: effecten.append(f"Honger +{voedsel['honger']}")
            if voedsel["energie"]: effecten.append(f"Energie +{voedsel['energie']}")
            if voedsel["geluk"] > 0: effecten.append(f"Geluk +{voedsel['geluk']}")
            if voedsel["gezondheid"] > 0: effecten.append(f"Gezondheid +{voedsel['gezondheid']}")
            if voedsel["gezondheid"] < 0: effecten.append(f"Gezondheid {voedsel['gezondheid']}")

            print(f"|  {key}. {voedsel['naam']:<20}|")
            print(f"|     {', '.join(effecten):<25}|")

        print("|  0. Terug                      |")
        print("+--------------------------------+")

        keuze = input("\nKies (0-6): ").strip()

        if keuze == "0" or keuze not in self.VOEDSEL:
            return

        voedsel = self.VOEDSEL[keuze]
        print(f"\nJe geeft {naam} {voedsel['naam']}...")
        time.sleep(0.5)

        # IQ bonus bij voeren - slim huisdier weet wat gezond is
        iq = self.huisdier.get("intelligentie", 0)
        iq_health_bonus = 0
        if iq >= 50 and voedsel["gezondheid"] >= 0:
            iq_health_bonus = iq // 25  # +1-4 extra gezondheid
            print(f"  [IQ] {naam} eet slim - extra gezondheidsbonus!")

        self.huisdier["honger"] = min(100, self.huisdier["honger"] + voedsel["honger"])
        self.huisdier["energie"] = min(100, self.huisdier["energie"] + voedsel["energie"])
        self.huisdier["geluk"] = min(100, self.huisdier["geluk"] + voedsel["geluk"])
        self.huisdier["gezondheid"] = max(0, min(100,
            self.huisdier["gezondheid"] + voedsel["gezondheid"] + iq_health_bonus))

        self.huisdier["stats"]["voedingen"] += 1
        self.huisdier["ervaring"] += 5

        # AI-enhanced reactie (30% kans)
        if random.random() < 0.3:
            ai_reactie = self._ai_generate_response(
                f"{naam} heeft net {voedsel['naam']} gegeten. Hoe reageert het huisdier?",
                f"{naam} smult ervan!"
            )
            print(ai_reactie)
        else:
            reacties = [
                f"{naam} smult ervan!",
                f"Mmm! {naam} likt tevreden de bak leeg!",
                f"{self.huisdier['geluid']}",
            ]
            print(random.choice(reacties))

        # Voeg herinnering toe
        self._ai_add_memory("voeren", f"At {voedsel['naam']}")
        self._log_memory_event("pet_fed", {
            "resultaat": voedsel["naam"]
        })

        # Achievement checks
        if self.huisdier["stats"]["voedingen"] == 1:
            self._unlock_achievement("eerste_voeding")
        if self.huisdier["stats"]["voedingen"] >= 50:
            self._unlock_achievement("50_voedingen")

    def _spelen(self):
        """Speelt met het huisdier - IQ bonus voor slimme huisdieren!"""
        if self.huisdier["energie"] < 2:
            print(f"\n{self.huisdier['naam']} is te moe om te spelen...")
            return

        print(f"\nJe speelt met {self.huisdier['naam']}...")
        time.sleep(0.5)

        # Evolutie bonus + IQ bonus
        evo_bonus = self._get_evolutie_info()["bonus"]
        iq = self.huisdier.get("intelligentie", 0)
        iq_bonus = iq // 20  # +1 geluk per 20 IQ

        totaal_bonus = evo_bonus + iq_bonus
        self.huisdier["geluk"] = min(100, self.huisdier["geluk"] + 20 + totaal_bonus)
        self.huisdier["energie"] = max(0, self.huisdier["energie"] - 2)
        self.huisdier["honger"] = max(0, self.huisdier["honger"] - 10)
        self.huisdier["ervaring"] += 10

        naam = self.huisdier["naam"]

        # AI-enhanced reactie (30% kans)
        if random.random() < 0.3:
            ai_reactie = self._ai_generate_response(
                f"{naam} speelt vrolijk. Hoe reageert het huisdier?",
                f"{naam} springt van plezier!"
            )
            print(ai_reactie)
        else:
            reacties = [
                f"{naam} rent vrolijk rond!",
                f"{naam} springt van plezier!",
                f"Wat leuk! {naam} wil nog meer spelen!",
                f"{self.huisdier['geluid']}",
            ]
            print(random.choice(reacties))

        # Voeg herinnering toe
        self._ai_add_memory("spelen", "Leuk gespeeld met baasje!")
        self._log_memory_event("pet_played", {
            "resultaat": "gespeeld"
        })

        # Slim huisdier deelt kennis tijdens spelen
        if iq >= 30 and "kennis" in self.huisdier:
            feiten = self.huisdier["kennis"].get("feiten", [])
            if feiten and random.randint(1, 100) <= 30:
                feit = random.choice(feiten)
                print(f"\n  [IQ] {self.huisdier['naam']} zegt: \"{feit[:60]}...\"")
                self.huisdier["ervaring"] += 5

    def _slapen(self):
        """Laat het huisdier slapen - met dromen voor extra beloningen!"""
        naam = self.huisdier["naam"]
        iq = self.huisdier.get("intelligentie", 0)

        print(f"\n{naam} gaat slapen...")
        time.sleep(1)

        bonus = 0
        iq_bonus = 0

        # Accessoire bonus
        if "bed" in self.huisdier["accessoires"]:
            bonus = 10
            print("(Bonus van luxe bedje!)")

        # Slim huisdier droomt en leert tijdens slaap
        if iq >= 20 and "kennis" in self.huisdier:
            feiten = self.huisdier["kennis"].get("feiten", [])
            if feiten and random.randint(1, 100) <= 40:
                iq_bonus = 1
                print(f"\n  [KENNIS DROOM] {naam} droomt over geleerde kennis...")
                print(f"  [IQ] +1 intelligentie door dromen!")

        self.huisdier["energie"] = min(100, self.huisdier["energie"] + 40 + bonus)
        self.huisdier["gezondheid"] = min(100, self.huisdier["gezondheid"] + 10)
        self.huisdier["ervaring"] += 5
        if iq_bonus > 0:
            self.huisdier["intelligentie"] = self.huisdier.get("intelligentie", 0) + iq_bonus

        print(f"Zzzzz... {naam} slaapt heerlijk.")

        # NIEUWE DROMEN SYSTEEM - kans op speciale dromen!
        self._slapen_met_dromen()

        print(f"*gaaap* {naam} is weer uitgerust!")

    def _knuffelen(self):
        """Knuffelt het huisdier - slimme huisdieren waarderen aandacht meer!"""
        naam = self.huisdier["naam"]
        iq = self.huisdier.get("intelligentie", 0)

        print(f"\nJe knuffelt {naam}...")
        time.sleep(0.5)

        # IQ bonus - slimmer huisdier geniet meer van sociale interactie
        iq_bonus = min(5, iq // 20)  # Max +5 extra geluk

        self.huisdier["geluk"] = min(100, self.huisdier["geluk"] + 15 + iq_bonus)
        self.huisdier["gezondheid"] = min(100, self.huisdier["gezondheid"] + 5)
        self.huisdier["ervaring"] += 5

        # AI-enhanced reactie (30% kans)
        if random.random() < 0.3:
            ai_reactie = self._ai_generate_response(
                f"{naam} wordt geknuffeld door baasje. Hoe reageert het huisdier?",
                f"{naam} geniet van de aandacht!"
            )
            print(ai_reactie)
        else:
            reacties = [
                f"{naam} geniet van de aandacht!",
                f"Aaah! {naam} is zo blij!",
                f"{naam} geeft je een likje!",
                f"{self.huisdier['geluid']}",
            ]
            print(random.choice(reacties))

        # Voeg herinnering toe
        self._ai_add_memory("knuffelen", "Lekker geknuffeld met baasje")

        # Slim huisdier toont extra waardering
        if iq >= 40 and iq_bonus > 0:
            print(f"  [IQ] {naam} waardeert de sociale band extra! (+{iq_bonus} geluk)")

        if self.huisdier["gezondheid"] == 100:
            self._unlock_achievement("perfecte_gezondheid")

    def _dokter(self):
        """Naar de dierenarts - met IQ korting en gezondheid tips!"""
        naam = self.huisdier["naam"]
        iq = self.huisdier.get("intelligentie", 0)
        gezondheid = self.huisdier["gezondheid"]

        # Slim huisdier krijgt korting (kent zelf remedies)
        basis_kosten = 25
        iq_korting = min(10, iq // 10)  # Max 10 munten korting
        kosten = max(10, basis_kosten - iq_korting)

        # Toon gezondheid status
        print("\n" + "=" * 40)
        print(f"  [DOKTER] DIERENARTS BEZOEK")
        print("=" * 40)
        print(f"\n  Patient: {naam}")
        print(f"  Gezondheid: {self._maak_balk(gezondheid)} {gezondheid}%")

        # Slim huisdier geeft gezondheid tips uit geleerde kennis
        if iq >= 30 and "kennis" in self.huisdier:
            feiten = self.huisdier["kennis"].get("feiten", [])
            gezondheid_feiten = [f for f in feiten if any(w in f.lower()
                for w in ["gezond", "slaap", "eten", "energie", "brein"])]
            if gezondheid_feiten:
                print(f"\n  [IQ] {naam}'s eigen gezondheid tip:")
                print(f"      \"{random.choice(gezondheid_feiten)[:60]}...\"")

        if gezondheid >= 90:
            print(f"\n  [OK] {naam} is kerngezond! Geen behandeling nodig.")
            print("  De dokter geeft een snoepje als beloning!")
            self.huisdier["geluk"] = min(100, self.huisdier["geluk"] + 5)
            return

        if self.huisdier["munten"] < kosten:
            print(f"\n  [!] Je hebt niet genoeg munten! (Nodig: {kosten})")
            return

        print(f"\n  Kosten: {kosten} munten", end="")
        if iq_korting > 0:
            print(f" (IQ korting: -{iq_korting}!)")
        else:
            print()

        bevestig = input("\n  Behandeling starten? (j/n): ").strip().lower()
        if bevestig != "j":
            return

        print(f"\n  De dokter onderzoekt {naam}...")
        time.sleep(1)

        self.huisdier["munten"] -= kosten
        oude_gezondheid = self.huisdier["gezondheid"]
        self.huisdier["gezondheid"] = 100

        # Diagnose gebaseerd op stats
        diagnoses = []
        if self.huisdier["honger"] < 30:
            diagnoses.append("ondervoeding")
        if self.huisdier["energie"] < 3:
            diagnoses.append("uitputting")
        if self.huisdier["geluk"] < 30:
            diagnoses.append("stress")

        if diagnoses:
            print(f"  Diagnose: {', '.join(diagnoses)}")
            print("  Advies: Goed voeren, slapen en spelen!")
        else:
            print("  Diagnose: Kleine kwaal")

        print(f"\n  [OK] {naam} is weer helemaal beter!")
        print(f"  Gezondheid: {oude_gezondheid}% -> 100%")

        # Ervaring voor doktersbezoek
        self.huisdier["ervaring"] += 5

    def _mini_games(self):
        """Mini-games menu."""
        while True:
            print("\n+====================================+")
            print("|          MINI-GAMES                |")
            print("+====================================+")
            print("|  1. Raad het getal (5 munten)      |")
            print("|  2. Steen-papier-schaar            |")
            print("|  3. Memory (10 munten)             |")
            print("|  4. Snelheidstest                  |")
            print("|  5. Verstoppertje (8 munten)       |")
            print("|  6. Race (12 munten)               |")
            print("|  7. Quiz (6 munten)                |")
            print("|  8. Vangen (10 munten)             |")
            print("|  9. Schatzoek Avontuur (15 munten) |")
            print("|  0. Terug                          |")
            print("+====================================+")

            keuze = input("\nKies een spel: ").strip()

            if keuze == "0":
                break
            elif keuze == "1":
                self._game_raad_getal()
            elif keuze == "2":
                self._game_steen_papier_schaar()
            elif keuze == "3":
                self._game_memory()
            elif keuze == "4":
                self._game_snelheid()
            elif keuze == "5":
                self._game_verstoppertje()
            elif keuze == "6":
                self._game_race()
            elif keuze == "7":
                self._game_quiz()
            elif keuze == "8":
                self._game_vangen()
            elif keuze == "9":
                self._game_schatzoek_avontuur()

            input("\nDruk op Enter...")

    def _game_raad_getal(self):
        """Raad het getal spel."""
        if self.huisdier["munten"] < 5:
            print("\nJe hebt niet genoeg munten! (Nodig: 5)")
            return

        self.huisdier["munten"] -= 5
        getal = random.randint(1, 10)
        pogingen = 3

        print(f"\n{self.huisdier['naam']} denkt aan een getal tussen 1 en 10...")
        print(f"Je hebt {pogingen} pogingen!")

        for i in range(pogingen):
            try:
                gok = int(input(f"\nPoging {i+1}: ").strip())
                if gok == getal:
                    winst = 15
                    print(f"\n[OK] GOED! Je wint {winst} munten!")
                    self.huisdier["munten"] += winst
                    self.huisdier["stats"]["games_gewonnen"] += 1
                    self._check_game_achievements()
                    return
                elif gok < getal:
                    print("Hoger!")
                else:
                    print("Lager!")
            except ValueError:
                print("Voer een getal in!")

        print(f"\nHelaas! Het getal was {getal}.")

    def _game_steen_papier_schaar(self):
        """Steen papier schaar."""
        opties = ["steen", "papier", "schaar"]

        print(f"\n{self.huisdier['naam']} wil steen-papier-schaar spelen!")
        keuze = input("Jouw keuze (steen/papier/schaar): ").strip().lower()

        if keuze not in opties:
            print("Ongeldige keuze!")
            return

        huisdier_keuze = random.choice(opties)
        print(f"\n{self.huisdier['naam']} kiest: {huisdier_keuze}!")

        if keuze == huisdier_keuze:
            print("Gelijkspel!")
        elif (keuze == "steen" and huisdier_keuze == "schaar") or \
             (keuze == "papier" and huisdier_keuze == "steen") or \
             (keuze == "schaar" and huisdier_keuze == "papier"):
            print("[OK] Je wint! +10 munten!")
            self.huisdier["munten"] += 10
            self.huisdier["stats"]["games_gewonnen"] += 1
            self._check_game_achievements()
        else:
            print(f"{self.huisdier['naam']} wint!")
            self.huisdier["geluk"] = min(100, self.huisdier["geluk"] + 5)

    def _game_memory(self):
        """Simpel memory spel."""
        if self.huisdier["munten"] < 10:
            print("\nJe hebt niet genoeg munten! (Nodig: 10)")
            return

        self.huisdier["munten"] -= 10

        reeks = [random.randint(1, 9) for _ in range(4)]
        print(f"\n{self.huisdier['naam']} laat een reeks zien...")
        print(f"\nOnthoud: {' '.join(map(str, reeks))}")
        time.sleep(2)
        print("\n" * 3)

        try:
            antwoord = input("Wat was de reeks? (bijv: 1 2 3 4): ").strip()
            gebruiker_reeks = list(map(int, antwoord.split()))

            if gebruiker_reeks == reeks:
                winst = 30
                print(f"\n[OK] PERFECT! Je wint {winst} munten!")
                self.huisdier["munten"] += winst
                self.huisdier["stats"]["games_gewonnen"] += 1
                self._check_game_achievements()
            else:
                print(f"\nHelaas! De reeks was: {' '.join(map(str, reeks))}")
        except ValueError:
            print("Ongeldige invoer!")

    def _game_snelheid(self):
        """Snelheidstest."""
        print(f"\n{self.huisdier['naam']} wil je reflexen testen!")
        print("Druk op Enter zodra je 'NU!' ziet...")

        time.sleep(random.uniform(1, 4))
        start = time.time()
        print("\n>>> NU! <<<")
        input()
        reactietijd = time.time() - start

        if reactietijd < 0.3:
            print(f"[OK] BLIKSEMNEL! {reactietijd:.3f}s - +15 munten!")
            self.huisdier["munten"] += 15
            self.huisdier["stats"]["games_gewonnen"] += 1
            self._check_game_achievements()
        elif reactietijd < 0.5:
            print(f"Goed! {reactietijd:.3f}s - +5 munten!")
            self.huisdier["munten"] += 5
        else:
            print(f"Te langzaam! {reactietijd:.3f}s")

    def _game_verstoppertje(self):
        """Verstoppertje mini-game - zoek je huisdier!"""
        if self.huisdier["munten"] < 8:
            print("\nJe hebt niet genoeg munten! (Nodig: 8)")
            return

        self.huisdier["munten"] -= 8

        # Maak een 3x3 grid met 9 verstopplekken
        plekken = [
            "achter de bank", "in de kast", "onder het bed",
            "achter het gordijn", "in de wasmand", "onder de tafel",
            "in de doos", "achter de deur", "onder de deken"
        ]

        verstopplek = random.choice(plekken)
        pogingen = 3

        print(f"\n{self.huisdier['naam']} heeft zich verstopt!")
        print(f"{self.huisdier['geluid']}")
        print(f"\nJe hebt {pogingen} pogingen om {self.huisdier['naam']} te vinden!")

        print("\nWaar zou je zoeken?")
        for i, plek in enumerate(plekken, 1):
            print(f"  {i}. {plek.capitalize()}")

        for poging in range(pogingen):
            try:
                keuze = int(input(f"\nPoging {poging + 1}/{pogingen} - Kies (1-9): ").strip())
                if 1 <= keuze <= 9:
                    gekozen = plekken[keuze - 1]

                    if gekozen == verstopplek:
                        winst = 20 + (pogingen - poging) * 5
                        print(f"\n[OK] GEVONDEN! {self.huisdier['naam']} zat {verstopplek}!")
                        print(f"{self.huisdier['naam']} springt blij in je armen!")
                        print(f"+{winst} munten!")
                        self.huisdier["munten"] += winst
                        self.huisdier["geluk"] = min(100, self.huisdier["geluk"] + 15)
                        self.huisdier["stats"]["games_gewonnen"] += 1
                        self._check_game_achievements()
                        return
                    else:
                        # Geef een hint
                        if poging < pogingen - 1:
                            verstop_idx = plekken.index(verstopplek)
                            keuze_idx = keuze - 1
                            if abs(verstop_idx - keuze_idx) <= 2:
                                print(f"\n*je hoort geritsel* {self.huisdier['naam']} is dichtbij!")
                            else:
                                print(f"\n*stilte* {self.huisdier['naam']} is niet in de buurt...")
            except ValueError:
                print("Voer een nummer in (1-9)!")

        print(f"\n{self.huisdier['naam']} komt tevoorschijn van {verstopplek}!")
        print(f"{self.huisdier['geluid']} - Beter geluk volgende keer!")
        self.huisdier["geluk"] = min(100, self.huisdier["geluk"] + 5)

    def _game_race(self):
        """Race mini-game - race tegen je huisdier!"""
        if self.huisdier["munten"] < 12:
            print("\nJe hebt niet genoeg munten! (Nodig: 12)")
            return

        self.huisdier["munten"] -= 12

        print(f"\n{self.huisdier['naam']} daagt je uit voor een race!")
        print("Druk zo snel mogelijk op Enter wanneer de race begint!")
        print("\nKlaar...")
        time.sleep(1)
        print("Set...")
        time.sleep(random.uniform(0.5, 2))
        print("\n>>> START! <<<")

        # Speler moet 5x op enter drukken
        start = time.time()
        for i in range(5):
            input(f"[{i+1}/5] DRUK ENTER!")
        speler_tijd = time.time() - start

        # Huisdier tijd (gebaseerd op geluk en energie)
        basis_tijd = 3.0
        huisdier_bonus = (self.huisdier["geluk"] + self.huisdier["energie"]) / 200
        huisdier_tijd = basis_tijd - huisdier_bonus + random.uniform(-0.5, 0.5)

        print(f"\nJouw tijd: {speler_tijd:.2f}s")
        print(f"{self.huisdier['naam']}'s tijd: {huisdier_tijd:.2f}s")

        if speler_tijd < huisdier_tijd:
            winst = 25
            print(f"\n[OK] JE WINT! +{winst} munten!")
            self.huisdier["munten"] += winst
            self.huisdier["stats"]["games_gewonnen"] += 1
            self._check_game_achievements()
        elif speler_tijd > huisdier_tijd:
            print(f"\n{self.huisdier['naam']} wint! {self.huisdier['geluid']}")
            self.huisdier["geluk"] = min(100, self.huisdier["geluk"] + 10)
        else:
            print("\nGelijkspel! +5 munten troostprijs!")
            self.huisdier["munten"] += 5

    def _game_quiz(self):
        """Quiz mini-game - beantwoord vragen over huisdieren!"""
        if self.huisdier["munten"] < 6:
            print("\nJe hebt niet genoeg munten! (Nodig: 6)")
            return

        self.huisdier["munten"] -= 6

        vragen = [
            {"vraag": "Hoeveel levens heeft een kat volgens het gezegde?", "antwoord": "9", "opties": ["7", "9", "5", "3"]},
            {"vraag": "Welk dier is het symbool van trouw?", "antwoord": "hond", "opties": ["kat", "hond", "vis", "vogel"]},
            {"vraag": "Wat eet een konijn het liefst?", "antwoord": "wortels", "opties": ["vlees", "wortels", "vis", "brood"]},
            {"vraag": "Hoe noem je een groep wolven?", "antwoord": "roedel", "opties": ["kudde", "zwerm", "roedel", "school"]},
            {"vraag": "Welk dier slaapt staand?", "antwoord": "paard", "opties": ["hond", "kat", "paard", "konijn"]},
            {"vraag": "Hoeveel poten heeft een spin?", "antwoord": "8", "opties": ["6", "8", "10", "4"]},
            {"vraag": "Welk dier kan het hardst rennen?", "antwoord": "cheeta", "opties": ["leeuw", "cheeta", "paard", "hond"]},
            {"vraag": "Wat is de grootste vogel ter wereld?", "antwoord": "struisvogel", "opties": ["adelaar", "struisvogel", "albatros", "condor"]},
        ]

        vraag = random.choice(vragen)
        random.shuffle(vraag["opties"])

        print(f"\n{self.huisdier['naam']} stelt een vraag:")
        print(f"\n>> {vraag['vraag']}")
        for i, optie in enumerate(vraag["opties"], 1):
            print(f"  {i}. {optie}")

        try:
            keuze = int(input("\nJouw antwoord (1-4): ").strip())
            gekozen = vraag["opties"][keuze - 1].lower()

            if gekozen == vraag["antwoord"].lower():
                winst = 20
                print(f"\n[OK] CORRECT! +{winst} munten!")
                self.huisdier["munten"] += winst
                self.huisdier["stats"]["games_gewonnen"] += 1
                self._check_game_achievements()
            else:
                print(f"\nHelaas! Het juiste antwoord was: {vraag['antwoord']}")
        except (ValueError, IndexError):
            print("Ongeldige keuze!")

    def _game_vangen(self):
        """Vangen mini-game - vang het vallende object!"""
        if self.huisdier["munten"] < 10:
            print("\nJe hebt niet genoeg munten! (Nodig: 10)")
            return

        self.huisdier["munten"] -= 10

        objecten = ["bal", "bot", "muis", "veer", "ring"]
        obj = random.choice(objecten)

        print(f"\n{self.huisdier['naam']} gooit een {obj} in de lucht!")
        print("Typ het object en druk Enter om te vangen!")
        print("\n3...")
        time.sleep(1)
        print("2...")
        time.sleep(1)
        print("1...")
        time.sleep(random.uniform(0.3, 1.0))
        print(f"\n>>> {obj.upper()} <<<")

        start = time.time()
        antwoord = input("VANG: ").strip().lower()
        reactietijd = time.time() - start

        if antwoord == obj and reactietijd < 2.0:
            if reactietijd < 0.8:
                winst = 30
                print(f"\n[OK] PERFECTE VANGST! {reactietijd:.2f}s - +{winst} munten!")
            elif reactietijd < 1.5:
                winst = 20
                print(f"\n[OK] Goed gevangen! {reactietijd:.2f}s - +{winst} munten!")
            else:
                winst = 10
                print(f"\nNet op tijd! {reactietijd:.2f}s - +{winst} munten!")
            self.huisdier["munten"] += winst
            self.huisdier["stats"]["games_gewonnen"] += 1
            self._check_game_achievements()
        elif antwoord != obj:
            print(f"\nJe typte '{antwoord}' maar het was '{obj}'!")
        else:
            print(f"\nTe langzaam! ({reactietijd:.2f}s)")

        self.huisdier["geluk"] = min(100, self.huisdier["geluk"] + 5)

    def _game_schatzoek_avontuur(self):
        """Schatzoek avontuur - je huisdier gaat automatisch op schattenjacht!"""
        if self.huisdier["munten"] < 15:
            print("\nJe hebt niet genoeg munten! (Nodig: 15)")
            return

        if self.huisdier["energie"] < 2:
            print(f"\n{self.huisdier['naam']} is te moe voor een avontuur!")
            print("Laat je huisdier eerst rusten.")
            return

        self.huisdier["munten"] -= 15
        self.huisdier["energie"] = max(0, self.huisdier["energie"] - 2)

        # Init stats als ze niet bestaan
        if "schatten_gevonden" not in self.huisdier["stats"]:
            self.huisdier["stats"]["schatten_gevonden"] = 0
        if "avonturen_voltooid" not in self.huisdier["stats"]:
            self.huisdier["stats"]["avonturen_voltooid"] = 0

        naam = self.huisdier["naam"]
        geluid = self.huisdier["geluid"]

        # Moeilijkheid gebaseerd op evolutie
        evolutie = self.huisdier.get("evolutie_stadium", 0)
        geluk = self.huisdier["geluk"]

        # Bereken success kansen
        basis_kans = 50 + (evolutie * 5) + (geluk // 5)
        basis_kans = min(90, basis_kans)  # Max 90%

        print("\n" + "=" * 50)
        print(f"  [AVONTUUR] {naam} GAAT OP SCHATTENJACHT!")
        print("=" * 50)
        time.sleep(0.5)

        # Kies een biome
        biomes = [
            ("Mysterieus Bos", "[BOS]"),
            ("Donkere Grot", "[GROT]"),
            ("Verloren Woestijn", "[WOESTIJN]"),
            ("Verlaten Kasteel", "[KASTEEL]"),
            ("Bevroren IJsgrot", "[IJSGROT]"),
        ]
        biome_naam, biome_emoji = random.choice(biomes)

        print(f"\n  {biome_emoji} Locatie: {biome_naam}")
        print(f"  {geluid}")
        time.sleep(0.8)

        # Simuleer het avontuur
        schatten = 0
        monsters_verslagen = 0
        events = []

        # 5 kamers verkennen
        for kamer in range(1, 6):
            print(f"\n  --- Kamer {kamer}/5 ---")
            time.sleep(0.4)

            # Random events
            event = random.choices(
                ["schat", "monster", "val", "powerup", "leeg"],
                weights=[25, 20, 15, 15, 25]
            )[0]

            if event == "schat":
                if random.randint(1, 100) <= basis_kans:
                    schatten += 1
                    print(f"  [DIAMANT] {naam} vindt een schitterende schat!")
                    events.append("schat")
                else:
                    print(f"  [?] {naam} ziet iets glinsteren maar kan er niet bij...")

            elif event == "monster":
                monster = random.choice(["Goblin", "Spin", "Vleermuis", "Slime"])
                if random.randint(1, 100) <= basis_kans + 10:
                    monsters_verslagen += 1
                    print(f"  [ZWAARD] {naam} verslaat een {monster}!")
                    events.append("monster")
                else:
                    print(f"  [!] Een {monster}! {naam} rent weg!")

            elif event == "val":
                if random.randint(1, 100) <= basis_kans:
                    print(f"  [!] Een valstrik! {naam} ontwijkt hem handig!")
                else:
                    print(f"  [X] Oeps! {naam} trapt in een val! (-5 energie)")
                    self.huisdier["energie"] = max(0, self.huisdier["energie"] - 1)

            elif event == "powerup":
                powerup = random.choice(["hartje", "ster", "trank"])
                print(f"  [+] {naam} vindt een {powerup}! (+5 geluk)")
                self.huisdier["geluk"] = min(100, self.huisdier["geluk"] + 5)
                events.append("powerup")

            else:  # leeg
                print(f"  [_] Een lege kamer... {naam} snuffelt rond.")

            time.sleep(0.3)

        # Resultaten
        print("\n" + "=" * 50)
        print("  [VLAG] AVONTUUR VOLTOOID!")
        print("=" * 50)

        # Beloningen berekenen
        munt_beloning = schatten * 20 + monsters_verslagen * 10
        xp_beloning = schatten * 15 + monsters_verslagen * 10 + 10

        print(f"\n  Resultaten van {naam}:")
        print(f"    [DIAMANT] Schatten gevonden: {schatten}")
        print(f"    [ZWAARD] Monsters verslagen: {monsters_verslagen}")
        print(f"    [MUNT] Munten verdiend: +{munt_beloning}")
        print(f"    [XP] Ervaring: +{xp_beloning}")

        # Geef beloningen
        self.huisdier["munten"] += munt_beloning
        self.huisdier["ervaring"] += xp_beloning
        self.huisdier["stats"]["schatten_gevonden"] += schatten
        self.huisdier["stats"]["avonturen_voltooid"] += 1
        self.huisdier["stats"]["games_gewonnen"] += 1 if schatten > 0 else 0

        # Bonus voor perfect avontuur
        if schatten >= 3:
            bonus = 25
            print(f"\n  [TROFEE] GEWELDIG! Bonus voor 3+ schatten: +{bonus} munten!")
            self.huisdier["munten"] += bonus

        # Achievements checken
        self._check_game_achievements()
        if self.huisdier["stats"]["schatten_gevonden"] >= 10:
            self._unlock_achievement("schatzoeker")
        if self.huisdier["stats"]["avonturen_voltooid"] >= 5:
            self._unlock_achievement("avonturier")

        # Level check
        self._check_evolutie()

        print(f"\n  {geluid}")
        self._sla_op()

    def _check_game_achievements(self):
        """Check game achievements."""
        self._unlock_achievement("mini_game_winnaar")
        if self.huisdier["stats"]["games_gewonnen"] >= 10:
            self._unlock_achievement("10_games_gewonnen")

    # ==================== HUISDIER WERK ====================

    def _huisdier_werk(self):
        """Menu voor huisdier werk activiteiten."""
        while True:
            print("\n+====================================+")
            print("|        HUISDIER WERK               |")
            print("+====================================+")
            print("|  Je huisdier kan helpen met taken! |")
            print("+------------------------------------+")
            print("|  1. Boodschappen Doen (10 munten)  |")
            print("|  2. Wiskunde Uitdaging (8 munten)  |")
            print("|  3. Bug Jacht (12 munten)          |")
            print("|  0. Terug                          |")
            print("+====================================+")

            keuze = input("\nKies een activiteit: ").strip()

            if keuze == "0":
                break
            elif keuze == "1":
                self._werk_boodschappen()
            elif keuze == "2":
                self._werk_wiskunde()
            elif keuze == "3":
                self._werk_bug_jacht()

            input("\nDruk op Enter...")

    def _werk_boodschappen(self):
        """Huisdier gaat boodschappen doen - integratie met ECHTE boodschappenlijst!"""
        if self.huisdier["munten"] < 10:
            print("\nJe hebt niet genoeg munten! (Nodig: 10)")
            return

        if self.huisdier["energie"] < 2:
            print(f"\n{self.huisdier['naam']} is te moe om boodschappen te doen!")
            return

        self.huisdier["munten"] -= 10
        self.huisdier["energie"] = max(0, self.huisdier["energie"] - 2)

        # Init stats
        if "boodschappen_gedaan" not in self.huisdier["stats"]:
            self.huisdier["stats"]["boodschappen_gedaan"] = 0
        if "werk_taken" not in self.huisdier["stats"]:
            self.huisdier["stats"]["werk_taken"] = 0

        naam = self.huisdier["naam"]
        geluid = self.huisdier["geluid"]
        huisdier_type = self.huisdier["type"]
        iq = self.huisdier.get("intelligentie", 0)

        # Producten die het huisdier kan vinden
        winkel_secties = {
            "dieren": ["Hondenvoer", "Kattenvoer", "Snacks", "Speeltjes", "Kattenbakkorrels"],
            "snacks": ["Koekjes", "Chips", "Chocolade", "Nootjes"],
            "groenten": ["Appels", "Bananen", "Wortels", "Tomaten"],
            "zuivel": ["Melk", "Kaas", "Yoghurt", "Eieren"],
        }

        print("\n" + "=" * 50)
        print(f"  [WINKEL] {naam} GAAT BOODSCHAPPEN DOEN!")
        print("=" * 50)
        time.sleep(0.5)

        # Check ECHTE boodschappenlijst
        echte_lijst = []
        try:
            boodschappen_app = _get_boodschappenlijst()
            if boodschappen_app.bestand.exists():
                with open(boodschappen_app.bestand, "r", encoding="utf-8") as f:
                    echte_lijst = [line.strip() for line in f if line.strip()]
                if echte_lijst:
                    print(f"\n  [LIJST] Je hebt {len(echte_lijst)} items op je boodschappenlijst!")
                    for item in echte_lijst[:3]:
                        print(f"    - {item}")
                    if len(echte_lijst) > 3:
                        print(f"    ... en {len(echte_lijst) - 3} meer")
        except Exception as e:
            logger.debug("Failed to read grocery list for shopping game: %s", e)

        print(f"\n  {geluid}")
        print(f"  {naam} pakt een winkelwagentje...")
        time.sleep(0.5)

        gevonden_items = []
        totaal_korting = 0
        items_van_lijst = 0

        # IQ bonus - slimmer huisdier vindt meer (60-85% kans)
        basis_kans = 60 + min(25, iq // 4)

        # Bezoek 4 secties
        for sectie_naam, producten in random.sample(list(winkel_secties.items()), 4):
            print(f"\n  --- Sectie: {sectie_naam.upper()} ---")
            time.sleep(0.3)

            # Huisdier zoekt producten
            if random.randint(1, 100) <= basis_kans:
                product = random.choice(producten)
                gevonden_items.append(product)
                print(f"  [OK] {naam} vindt: {product}")

                # Check of product op echte lijst staat
                for echte_item in echte_lijst:
                    if product.lower() in echte_item.lower():
                        items_van_lijst += 1
                        print(f"  [LIJST] Dit stond op je boodschappenlijst!")
                        break

                # Kans op korting (IQ verhoogt kans)
                korting_kans = 30 + min(20, iq // 5)
                if random.randint(1, 100) <= korting_kans:
                    korting = random.randint(5, 20)
                    totaal_korting += korting
                    print(f"  [BONUS] Aanbieding gevonden! -{korting}% korting!")
            else:
                print(f"  [_] {naam} snuffelt rond maar vindt niks speciaals...")

            time.sleep(0.3)

        # Resultaten
        print("\n" + "=" * 50)
        print("  [KASSA] BOODSCHAPPEN KLAAR!")
        print("=" * 50)

        munt_beloning = len(gevonden_items) * 8 + totaal_korting // 2
        xp_beloning = len(gevonden_items) * 5 + 10
        intel_bonus = 0

        # Extra bonus voor items van echte lijst
        if items_van_lijst > 0:
            munt_beloning += items_van_lijst * 5
            intel_bonus = items_van_lijst

        print(f"\n  {naam}'s winkelresultaat:")
        print(f"    [TAS] Items gevonden: {len(gevonden_items)}")
        if gevonden_items:
            for item in gevonden_items:
                print(f"        - {item}")
        if items_van_lijst > 0:
            print(f"    [LIJST] Van je lijst: {items_van_lijst} items")
        print(f"    [%] Totale korting: {totaal_korting}%")
        print(f"    [MUNT] Verdiend: +{munt_beloning} munten")
        print(f"    [XP] Ervaring: +{xp_beloning}")
        if intel_bonus > 0:
            print(f"    [IQ] Intelligentie: +{intel_bonus}")

        # Vraag of gevonden items aan boodschappenlijst toegevoegd moeten worden
        nieuwe_suggesties = [i for i in gevonden_items if i not in echte_lijst]
        if nieuwe_suggesties and random.randint(1, 100) <= 50:
            suggestie = random.choice(nieuwe_suggesties)
            print(f"\n  [TIP] {naam} suggereert: \"{suggestie}\" toevoegen aan lijst?")
            antwoord = input("  Toevoegen? (j/n): ").strip().lower()
            if antwoord == "j":
                try:
                    boodschappen_app = _get_boodschappenlijst()
                    with open(boodschappen_app.bestand, "a", encoding="utf-8") as f:
                        f.write(f"{suggestie}\n")
                    print(f"  [OK] {suggestie} toegevoegd aan ECHTE boodschappenlijst!")
                    intel_bonus += 2
                except Exception as e:
                    logger.debug("Failed to add suggestion to grocery list: %s", e)

        # Geef beloningen
        self.huisdier["munten"] += munt_beloning
        self.huisdier["ervaring"] += xp_beloning
        self.huisdier["geluk"] = min(100, self.huisdier["geluk"] + 5)
        if intel_bonus > 0:
            self.huisdier["intelligentie"] = self.huisdier.get("intelligentie", 0) + intel_bonus
        self.huisdier["stats"]["boodschappen_gedaan"] += 1
        self.huisdier["stats"]["werk_taken"] += 1

        # Achievements
        if self.huisdier["stats"]["boodschappen_gedaan"] >= 10:
            self._unlock_achievement("boodschapper")
        if self.huisdier["stats"]["werk_taken"] >= 25:
            self._unlock_achievement("werkend_huisdier")

        self._check_evolutie()
        print(f"\n  {geluid}")
        self._sla_op()

    def _werk_wiskunde(self):
        """Huisdier lost wiskundige puzzels op - met ECHTE Rekenmachine!"""
        if self.huisdier["munten"] < 8:
            print("\nJe hebt niet genoeg munten! (Nodig: 8)")
            return

        if self.huisdier["energie"] < 1:
            print(f"\n{self.huisdier['naam']} is te moe om na te denken!")
            return

        self.huisdier["munten"] -= 8
        self.huisdier["energie"] = max(0, self.huisdier["energie"] - 1)

        # Init stats
        if "sommen_opgelost" not in self.huisdier["stats"]:
            self.huisdier["stats"]["sommen_opgelost"] = 0
        if "werk_taken" not in self.huisdier["stats"]:
            self.huisdier["stats"]["werk_taken"] = 0
        if "berekeningen_gedaan" not in self.huisdier["stats"]:
            self.huisdier["stats"]["berekeningen_gedaan"] = 0

        naam = self.huisdier["naam"]
        geluid = self.huisdier["geluid"]
        evolutie = self.huisdier.get("evolutie_stadium", 0)
        iq = self.huisdier.get("intelligentie", 0)

        # Moeilijkheid gebaseerd op evolutie EN IQ
        max_getal = 10 + (evolutie * 5) + (iq // 10)

        print("\n" + "=" * 50)
        print(f"  [CALCULATOR] {naam} GAAT REKENEN!")
        print("=" * 50)
        time.sleep(0.5)

        # Probeer ECHTE rekenmachine te laden
        echte_rekenmachine = None
        try:
            echte_rekenmachine = _get_rekenmachine()
            print(f"\n  {geluid}")
            print(f"  {naam} opent de ECHTE Slimme Rekenmachine...")
            time.sleep(0.5)
            print(f"  [OK] Rekenmachine verbonden!")
        except Exception as e:
            logger.debug("Failed to load real calculator app: %s", e)
            print(f"\n  {geluid}")
            print(f"  {naam} pakt een rekenmachine...")
        time.sleep(0.5)

        correct = 0
        totaal = 5
        intel_bonus = 0

        operaties = [
            ("+", lambda a, b: a + b),
            ("-", lambda a, b: a - b),
            ("x", lambda a, b: a * b),
        ]

        # Extra geavanceerde operaties voor slim huisdier
        if iq >= 30:
            operaties.append(("//", lambda a, b: a // b if b != 0 else 0))  # Deling
        if iq >= 60:
            operaties.append(("^", lambda a, b: a ** min(b, 3)))  # Machten (max 3)

        for ronde in range(1, totaal + 1):
            a = random.randint(1, max_getal)
            b = random.randint(1, max(1, max_getal // 2))
            op_sym, op_func = random.choice(operaties)

            # Zorg dat aftrekken niet negatief wordt en deling klopt
            if op_sym == "-" and b > a:
                a, b = b, a
            if op_sym == "//" and b == 0:
                b = 1

            antwoord = op_func(a, b)

            print(f"\n  --- Som {ronde}/{totaal} ---")
            print(f"  Wat is {a} {op_sym} {b} = ?")

            # Huisdier probeert te raden (IQ gebaseerd)
            basis_kans = 60 + (evolutie * 5) + (iq // 5) + (self.huisdier["geluk"] // 10)
            basis_kans = min(95, basis_kans)

            time.sleep(0.5)

            if random.randint(1, 100) <= basis_kans:
                # Gebruik echte rekenmachine voor verificatie als beschikbaar
                if echte_rekenmachine:
                    try:
                        expr = f"{a}{op_sym.replace('x', '*').replace('^', '**')}{b}"
                        result = eval(expr)  # Veilig want we controleren de input
                        print(f"  {naam} (via Rekenmachine): \"{int(result)}!\"")
                        intel_bonus += 1
                    except Exception as e:
                        logger.debug("Calculator verification failed: %s", e)
                        print(f"  {naam}: \"{antwoord}!\"")
                else:
                    print(f"  {naam}: \"{antwoord}!\"")
                print(f"  [OK] Correct!")
                correct += 1
            else:
                # Fout antwoord
                fout_antwoord = antwoord + random.choice([-2, -1, 1, 2])
                print(f"  {naam}: \"{fout_antwoord}?\"")
                print(f"  [X] Fout! Het was {antwoord}")

            time.sleep(0.3)

        # Resultaten
        print("\n" + "=" * 50)
        print("  [RESULTAAT] WISKUNDE SESSIE KLAAR!")
        print("=" * 50)

        munt_beloning = correct * 6
        xp_beloning = correct * 8 + 5

        # IQ bonus voor correct gebruik van rekenmachine
        if intel_bonus > 0:
            munt_beloning += intel_bonus * 2

        print(f"\n  {naam}'s score:")
        print(f"    [#] Correct: {correct}/{totaal}")
        if intel_bonus > 0:
            print(f"    [IQ] Rekenmachine bonus: +{intel_bonus}")
        print(f"    [MUNT] Verdiend: +{munt_beloning} munten")
        print(f"    [XP] Ervaring: +{xp_beloning}")

        if correct == totaal:
            bonus = 15
            print(f"\n  [TROFEE] PERFECT! Bonus: +{bonus} munten!")
            munt_beloning += bonus

        if echte_rekenmachine:
            print(f"\n  [STAR] Bonus: ECHTE Rekenmachine gebruikt!")

        # Geef beloningen
        self.huisdier["munten"] += munt_beloning
        self.huisdier["ervaring"] += xp_beloning
        self.huisdier["stats"]["sommen_opgelost"] += correct
        self.huisdier["stats"]["werk_taken"] += 1
        self.huisdier["stats"]["berekeningen_gedaan"] += correct
        if intel_bonus > 0:
            self.huisdier["intelligentie"] = self.huisdier.get("intelligentie", 0) + intel_bonus

        # Achievements
        if self.huisdier["stats"]["sommen_opgelost"] >= 20:
            self._unlock_achievement("wiskunde_genie")
        if self.huisdier["stats"]["werk_taken"] >= 25:
            self._unlock_achievement("werkend_huisdier")
        if self.huisdier.get("intelligentie", 0) >= 100:
            self._unlock_achievement("super_slim")

        self._check_evolutie()
        print(f"\n  {geluid}")
        self._sla_op()

    def _werk_bug_jacht(self):
        """Huisdier zoekt bugs in ECHTE code bestanden."""
        if self.huisdier["munten"] < 12:
            print("\nJe hebt niet genoeg munten! (Nodig: 12)")
            return

        if self.huisdier["energie"] < 2:
            print(f"\n{self.huisdier['naam']} is te moe om code te analyseren!")
            return

        self.huisdier["munten"] -= 12
        self.huisdier["energie"] = max(0, self.huisdier["energie"] - 2)

        # Init stats
        if "bugs_gevonden" not in self.huisdier["stats"]:
            self.huisdier["stats"]["bugs_gevonden"] = 0
        if "werk_taken" not in self.huisdier["stats"]:
            self.huisdier["stats"]["werk_taken"] = 0

        naam = self.huisdier["naam"]
        geluid = self.huisdier["geluid"]

        # Code analyse patronen (verbeterd - minder false positives)
        # Skip bestanden die zelf code analyse doen
        analyse_skip_bestanden = ["code_analyse.py", "virtueel_huisdier.py"]

        analyse_patronen = {
            "Security": [
                # Alleen echte calls, niet regex patronen (r'...')
                (r'^[^#r]*\beval\s*\([^)]+\)', "eval() call gevonden"),
                (r'^[^#r]*\bexec\s*\([^)]+\)', "exec() call gevonden"),
                (r'^[^#r]*os\.system\s*\([^)]+\)', "os.system() call"),
                (r'^\s*password\s*=\s*["\'][^"\']{3,}["\']', "Hardcoded password"),
                (r'^\s*api_key\s*=\s*["\'][^"\']{10,}["\']', "Hardcoded API key"),
            ],
            "Code Smell": [
                (r'#\s*(TODO|FIXME|XXX|HACK|BUG):', "TODO/FIXME commentaar"),
                (r'^\s*except\s*:\s*$', "Bare except"),
            ],
            "Logic": [
                # Alleen echte vergelijkingen, geen parameter defaults (x = None)
                (r'==\s*None\b', "Gebruik 'is None' ipv '== None'"),
                (r'!=\s*None\b', "Gebruik 'is not None' ipv '!= None'"),
            ],
            "Complexity": [
                (r'if .+ and .+ and .+ and .+', "Complexe conditie"),
            ],
        }

        print("\n" + "=" * 50)
        print(f"  [CODE] {naam} ANALYSEERT ECHTE CODE!")
        print("=" * 50)
        time.sleep(0.5)

        print(f"\n  {geluid}")
        print(f"  {naam} opent de Code Analyse tool...")
        time.sleep(0.5)

        # Vind echte Python bestanden (skip analyse bestanden)
        project_dir = Config.BASE_DIR / "danny_toolkit"
        alle_bestanden = list(project_dir.glob("**/*.py"))
        python_bestanden = [
            b for b in alle_bestanden
            if b.name not in analyse_skip_bestanden
        ]

        if not python_bestanden:
            print("  [!] Geen Python bestanden gevonden!")
            return

        bugs_gevonden = []
        bestanden_geanalyseerd = 0

        # Analyseer max 5 willekeurige bestanden
        for bestand in random.sample(python_bestanden, min(5, len(python_bestanden))):
            relative_path = bestand.relative_to(Config.BASE_DIR)
            print(f"\n  --- Analyseren: {relative_path} ---")
            time.sleep(0.3)

            bestanden_geanalyseerd += 1

            try:
                content = bestand.read_text(encoding="utf-8")
                bestand_bugs = []

                # Check alle patronen
                for categorie, patronen in analyse_patronen.items():
                    for patroon, beschrijving in patronen:
                        matches = re.findall(patroon, content, re.MULTILINE)
                        if matches:
                            bestand_bugs.append((categorie, beschrijving, len(matches)))

                if bestand_bugs:
                    for categorie, beschrijving, count in bestand_bugs[:2]:  # Max 2 per bestand
                        bugs_gevonden.append((categorie, beschrijving, str(relative_path)))
                        print(f"  [BUG] {naam} vindt: {beschrijving}")
                        print(f"        Categorie: {categorie} ({count}x)")
                else:
                    print(f"  [OK] {naam}: Code ziet er goed uit!")

            except Exception as e:
                print(f"  [!] Kon bestand niet lezen: {e}")

            time.sleep(0.2)

        # Resultaten
        print("\n" + "=" * 50)
        print("  [RAPPORT] ECHTE CODE ANALYSE KLAAR!")
        print("=" * 50)

        # Intelligentie bonus voor echte analyse
        intel_bonus = bestanden_geanalyseerd + len(bugs_gevonden)
        munt_beloning = len(bugs_gevonden) * 8 + bestanden_geanalyseerd * 2
        xp_beloning = len(bugs_gevonden) * 10 + bestanden_geanalyseerd * 5

        print(f"\n  {naam}'s analyse rapport:")
        print(f"    [FILE] Bestanden geanalyseerd: {bestanden_geanalyseerd}")
        print(f"    [BUG] Issues gevonden: {len(bugs_gevonden)}")
        if bugs_gevonden:
            for categorie, beschrijving, bestand in bugs_gevonden[:5]:
                print(f"        - [{categorie}] {beschrijving}")
                print(f"          in: {bestand}")
        print(f"    [IQ] Intelligentie: +{intel_bonus}")
        print(f"    [MUNT] Verdiend: +{munt_beloning} munten")
        print(f"    [XP] Ervaring: +{xp_beloning}")

        # Bonus voor veel bugs
        if len(bugs_gevonden) >= 4:
            bonus = 20
            print(f"\n  [TROFEE] SUPER DETECTIVE! Bonus: +{bonus} munten!")
            munt_beloning += bonus

        # Geef beloningen
        self.huisdier["munten"] += munt_beloning
        self.huisdier["ervaring"] += xp_beloning
        self.huisdier["intelligentie"] = self.huisdier.get("intelligentie", 0) + intel_bonus
        self.huisdier["stats"]["bugs_gevonden"] += len(bugs_gevonden)
        self.huisdier["stats"]["werk_taken"] += 1

        # Achievements
        if self.huisdier["stats"]["bugs_gevonden"] >= 15:
            self._unlock_achievement("bug_hunter")
        if self.huisdier["stats"]["werk_taken"] >= 25:
            self._unlock_achievement("werkend_huisdier")
        if self.huisdier.get("intelligentie", 0) >= 100:
            self._unlock_achievement("super_slim")

        self._check_evolutie()
        print(f"\n  {geluid}")
        self._sla_op()

    # ==================== HUISDIER LEREN (AI) ====================

    def _huisdier_leren(self):
        """Menu voor huisdier AI leeractiviteiten."""
        while True:
            intel = self.huisdier.get("intelligentie", 0)
            permanente_kennis = self._laad_permanente_kennis()
            totaal_feiten = len(permanente_kennis["feiten"])

            print("\n+====================================+")
            print("|        HUISDIER LEREN (AI)         |")
            print("+====================================+")
            print(f"|  IQ van {self.huisdier['naam']}: {intel}")
            print(f"|  Permanente kennis: {totaal_feiten} feiten")
            print("+------------------------------------+")
            print("|  1. RAG Studeren (10 munten)       |")
            print("|     Leer feiten uit de kennisbank  |")
            print("|  2. Nieuws Lezen (8 munten)        |")
            print("|     Blijf op de hoogte van nieuws  |")
            print("|  3. Weer Checken (5 munten)        |")
            print("|     Leer over het weer             |")
            print("+------------------------------------+")
            print("|  [AI KRACHTEN - Claude Integratie] |")
            print("+------------------------------------+")
            print("|  4. AI Gesprek (15 munten)         |")
            print("|     Stel vragen aan Claude AI      |")
            print("|  5. AI Code Helper (20 munten)     |")
            print("|     Leer programmeren met AI       |")
            print("|  6. AI Quiz Master (12 munten)     |")
            print("|     Test je kennis met AI vragen   |")
            print("|  7. AI Verhalen (18 munten)        |")
            print("|     Creatieve verhalen genereren   |")
            print("|  8. AI Vertaler (10 munten)        |")
            print("|     Vertaal tekst naar andere taal |")
            print("+------------------------------------+")
            print("|  [TOOLKIT INTEGRATIES]             |")
            print("+------------------------------------+")
            print("|  9. AI Flashcards (12 munten)      |")
            print("|     Leer met AI-gegenereerde kaarten|")
            print("| 10. AI Notities (8 munten)         |")
            print("|     Maak slimme notities met AI    |")
            print("| 11. AI Citaten (5 munten)          |")
            print("|     Leer van inspirerende citaten  |")
            print("| 12. AI Code Review (15 munten)     |")
            print("|     Analyseer code met AI          |")
            print("| 13. Production RAG (20 munten)     |")
            print("|     Echte kennisbank queries       |")
            print("| 14. AI Brainstorm (18 munten)      |")
            print("|     Creatief brainstormen met AI   |")
            print("+------------------------------------+")
            print("|  [PRODUCTIVITEIT INTEGRATIES]      |")
            print("+------------------------------------+")
            print("| 15. Mood Tracker (10 munten)       |")
            print("|     Track stemming met AI analyse  |")
            print("| 16. Habit Coach (12 munten)        |")
            print("|     AI helpt met gewoontes         |")
            print("| 17. Budget Advisor (15 munten)     |")
            print("|     AI spaartips en analyse        |")
            print("| 18. Dag Planner (12 munten)        |")
            print("|     AI helpt je dag plannen        |")
            print("| 19. Focus Timer (8 munten)         |")
            print("|     Pomodoro met AI tips           |")
            print("+------------------------------------+")
            print("| 20. Bekijk Kennisbibliotheek       |")
            print("|     Alle geleerde feiten bekijken  |")
            print("|  0. Terug                          |")
            print("+====================================+")

            keuze = input("\nKies een activiteit: ").strip()

            if keuze == "0":
                break
            elif keuze == "1":
                self._leren_rag()
            elif keuze == "2":
                self._leren_nieuws()
            elif keuze == "3":
                self._leren_weer()
            elif keuze == "4":
                self._leren_ai_gesprek()
            elif keuze == "5":
                self._ai_code_helper()
            elif keuze == "6":
                self._ai_quiz_master()
            elif keuze == "7":
                self._ai_verhalen()
            elif keuze == "8":
                self._ai_vertaler()
            elif keuze == "9":
                self._ai_flashcards()
            elif keuze == "10":
                self._ai_notities()
            elif keuze == "11":
                self._ai_citaten()
            elif keuze == "12":
                self._ai_code_review()
            elif keuze == "13":
                self._ai_production_rag()
            elif keuze == "14":
                self._ai_brainstorm()
            elif keuze == "15":
                self._ai_mood_tracker()
            elif keuze == "16":
                self._ai_habit_coach()
            elif keuze == "17":
                self._ai_budget_advisor()
            elif keuze == "18":
                self._ai_dag_planner()
            elif keuze == "19":
                self._ai_focus_timer()
            elif keuze == "20":
                self._bekijk_kennisbibliotheek()

            input("\nDruk op Enter...")

    def _bekijk_kennisbibliotheek(self):
        """Bekijk alle permanent opgeslagen kennis."""
        naam = self.huisdier["naam"]
        permanente_kennis = self._laad_permanente_kennis()

        print("\n" + "=" * 60)
        print(f"  [BIBLIOTHEEK] {naam}'s PERMANENTE KENNISBANK")
        print("=" * 60)
        print(f"\n  Locatie: {self.kennis_bestand}")
        print(f"  Totaal sessies: {permanente_kennis['totaal_sessies']}")
        print(f"  Totaal feiten: {len(permanente_kennis['feiten'])}")

        if not permanente_kennis["feiten"]:
            print("\n  [LEEG] Nog geen feiten geleerd!")
            print("  Tip: Gebruik 'RAG Studeren' om kennis te vergaren.")
            return

        print("\n  --- ALLE GELEERDE FEITEN ---")
        for i, feit in enumerate(permanente_kennis["feiten"], 1):
            bron = permanente_kennis["bronnen"][i-1] if i <= len(permanente_kennis["bronnen"]) else "onbekend"
            print(f"\n  {i}. \"{feit[:70]}{'...' if len(feit) > 70 else ''}\"")
            print(f"     Bron: {bron}")

        print("\n" + "-" * 60)
        print(f"  [INFO] Deze kennis blijft bewaard tot je huisdier reset!")
        print(f"  [DISK] Opgeslagen op: {self.kennis_bestand}")

    def _reset_huisdier(self) -> bool:
        """Reset het huisdier en optioneel de permanente kennis."""
        naam = self.huisdier["naam"]
        permanente_kennis = self._laad_permanente_kennis()

        print("\n" + "=" * 50)
        print("  [WAARSCHUWING] HUISDIER RESETTEN")
        print("=" * 50)
        print(f"\n  Huidig huisdier: {self.huisdier['emoji']} {naam}")
        print(f"  Leeftijd: {self.huisdier['leeftijd_dagen']} dagen")
        print(f"  IQ: {self.huisdier.get('intelligentie', 0)}")
        print(f"  Permanente kennis: {len(permanente_kennis['feiten'])} feiten")

        print("\n  [!] Dit kan niet ongedaan gemaakt worden!")
        bevestig = input("\n  Weet je zeker dat je wilt resetten? (ja/nee): ").strip().lower()

        if bevestig != "ja":
            print("\n  [OK] Reset geannuleerd.")
            return False

        print("\n  Wat wil je resetten?")
        print("  1. Alleen huisdier (kennis BEHOUDEN)")
        print("  2. Alles (huisdier EN permanente kennis)")
        print("  0. Annuleren")

        reset_keuze = input("\n  Keuze: ").strip()

        if reset_keuze == "0":
            print("\n  [OK] Reset geannuleerd.")
            return False

        if reset_keuze == "2":
            # Reset permanente kennis
            self._reset_permanente_kennis()
            print("  [OK] Permanente kennis gewist!")

        # Verwijder huisdier bestand
        if self.bestand.exists():
            self.bestand.unlink()
            print(f"  [OK] {naam} is naar een boerderij gebracht...")

        # Maak nieuw huisdier
        print("\n  Tijd voor een nieuw huisdier!")
        input("  Druk op Enter...")
        self._maak_nieuw_huisdier()
        return True

    def _leren_rag(self):
        """Huisdier leert van de ECHTE kennisbank - PERMANENT opgeslagen op lokale PC!"""
        if self.huisdier["munten"] < 10:
            print("\nJe hebt niet genoeg munten! (Nodig: 10)")
            return

        if self.huisdier["energie"] < 2:
            print(f"\n{self.huisdier['naam']} is te moe om te studeren!")
            return

        self.huisdier["munten"] -= 10
        self.huisdier["energie"] = max(0, self.huisdier["energie"] - 2)

        # Init kennis opslag in huisdier
        if "kennis" not in self.huisdier:
            self.huisdier["kennis"] = {"feiten": [], "nieuws": [], "weer_historie": []}
        if "feiten_geleerd" not in self.huisdier["stats"]:
            self.huisdier["stats"]["feiten_geleerd"] = 0

        naam = self.huisdier["naam"]
        geluid = self.huisdier["geluid"]

        print("\n" + "=" * 50)
        print(f"  [BOEK] {naam} OPENT PRODUCTION RAG!")
        print("=" * 50)
        time.sleep(0.5)

        # LAAD PERMANENTE KENNIS VAN LOKALE PC
        permanente_kennis = self._laad_permanente_kennis()
        print(f"\n  [DISK] Permanente kennis geladen van lokale PC")
        print(f"  [DATABASE] {len(permanente_kennis['feiten'])} feiten in bibliotheek")

        print(f"\n  {geluid}")

        # Probeer echte RAG te gebruiken
        echte_rag = False
        feiten_geleerd = []
        bronnen_gebruikt = []
        intel_bonus = 0

        try:
            from ..ai.production_rag import ProductionRAG
            print(f"  {naam} verbindt met de ECHTE kennisbank...")
            time.sleep(0.5)

            # Check of er documenten zijn
            kennisbank_dir = Config.BASE_DIR / "kennisbank"
            if kennisbank_dir.exists():
                bestanden = list(kennisbank_dir.glob("*.txt"))
                if bestanden:
                    echte_rag = True
                    print(f"  [OK] {len(bestanden)} kennisbestanden gevonden!")

                    # Lees random feiten uit de kennisbank
                    for bestand in random.sample(bestanden, min(3, len(bestanden))):
                        print(f"\n  --- Studeert: {bestand.name} ---")
                        bronnen_gebruikt.append(bestand.name)
                        time.sleep(0.3)

                        try:
                            content = bestand.read_text(encoding="utf-8")
                            # Zoek secties met === of ---
                            secties = re.split(r'\n={3,}|\n-{3,}', content)
                            for sectie in secties:
                                if len(sectie.strip()) > 50:
                                    # Extract eerste zin als feit
                                    zinnen = sectie.strip().split('.')
                                    for zin in zinnen[:2]:
                                        zin = zin.strip()
                                        if len(zin) > 20 and len(zin) < 200:
                                            # Check tegen PERMANENTE kennis
                                            if zin not in permanente_kennis["feiten"]:
                                                feiten_geleerd.append({
                                                    "feit": zin,
                                                    "bron": bestand.name,
                                                    "datum": datetime.now().isoformat()
                                                })
                                                # Voeg toe aan permanente kennis
                                                permanente_kennis["feiten"].append(zin)
                                                permanente_kennis["bronnen"].append(bestand.name)
                                                permanente_kennis["geleerd_op"].append(
                                                    datetime.now().isoformat()
                                                )
                                                # Ook in huisdier kennis
                                                self.huisdier["kennis"]["feiten"].append(zin)
                                                intel_bonus += 3
                                                print(f"  [LAMP] NIEUW: \"{zin[:60]}...\"")
                                                print(f"        [SAVE] Opgeslagen naar lokale PC!")
                                                break
                                            else:
                                                print(f"  [_] Dit wist {naam} al...")
                                    break
                        except Exception as e:
                            print(f"  [!] Kon {bestand.name} niet lezen")

        except ImportError:
            pass

        if not echte_rag:
            print(f"  [!] Geen RAG beschikbaar, gebruik ingebouwde kennis...")
            # Fallback naar ingebouwde AI/TECH kennis
            ingebouwde_feiten = [
                # Machine Learning & AI
                "Machine Learning is een tak van AI waarbij computers leren van data zonder expliciete programmering",
                "Neural networks zijn geinspireerd op het menselijk brein met lagen van kunstmatige neuronen",
                "Deep Learning gebruikt diepe neural networks met vele verborgen lagen voor complexe taken",
                "Backpropagation berekent gradients om de weights van een neural network aan te passen",
                "Supervised learning traint met gelabelde data waar het juiste antwoord bekend is",
                "Unsupervised learning vindt patronen in data zonder vooraf gedefinieerde labels",

                # Vector Databases & Embeddings
                "Een vector database is geoptimaliseerd voor het opslaan en doorzoeken van embeddings",
                "Embeddings zijn numerieke vectoren die de betekenis van tekst of concepten representeren",
                "Cosine similarity meet de gelijkenis tussen twee vectoren op basis van hun hoek",
                "Semantic search vindt resultaten op basis van betekenis in plaats van exacte keywords",
                "Vector databases maken snelle nearest neighbor search mogelijk voor AI toepassingen",

                # REST API
                "REST API's gebruiken HTTP methodes: GET (ophalen), POST (aanmaken), PUT (wijzigen), DELETE (verwijderen)",
                "REST staat voor Representational State Transfer, een architectuurstijl voor web services",
                "API endpoints zijn URLs waar je requests naartoe stuurt voor specifieke functionaliteit",
                "JSON is het meest gebruikte dataformaat voor REST API communicatie",

                # Transformers & NLP
                "Transformers gebruiken attention mechanismen om relaties tussen woorden te begrijpen",
                "Self-attention laat elk woord kijken naar alle andere woorden in een zin",
                "GPT en BERT zijn grote taalmodellen gebaseerd op de transformer architectuur",
                "NLP (Natural Language Processing) laat computers menselijke taal verwerken",

                # RAG & Advanced
                "RAG (Retrieval Augmented Generation) combineert zoeken met AI generatie voor betere antwoorden",
                "Fine-tuning past een voorgetraind model aan voor een specifieke taak of domein",
                "CNN (Convolutional Neural Network) is gespecialiseerd in beeldherkenning",
                "RNN (Recurrent Neural Network) is ontworpen voor sequentiele data zoals tekst",

                # Geavanceerde Concepten
                "Anders dan traditionele databases die zoeken op exacte waarden, vinden vector databases items die semantisch vergelijkbaar zijn",
                "Deep learning is in feite een subset van machine learning, gericht op diepe neural networks",
                "Neural networks vormen de basis van deep learning en zijn geinspireerd op biologische neuronen",

                # Natuurkunde & Wetenschap
                "Rayleigh-verstrooiing is het fenomeen waarbij licht verstrooid wordt door kleine deeltjes in de atmosfeer",
                "Dit fenomeen (Rayleigh-verstrooiing) verklaart waarom de lucht blauw is en zonsondergangen rood",

                # Internet & Netwerken
                "Internet verbindingen maken het mogelijk voor gebruikers om toegang te krijgen tot informatie en diensten van over de hele wereld",
                "Het World Wide Web is een systeem van onderling verbonden documenten via hyperlinks",

                # RAG & Retrieval
                "RAG combineert het opzoeken van bestaande informatie met het genereren van nieuwe informatie om vragen te beantwoorden",

                # Neural Network Leerproces
                "Door backpropagation kan een neural network leren van zijn fouten en zijn prestaties verbeteren",
                "Hierbij worden algoritmen gebruikt om patronen en verbanden in data te ontdekken voor voorspellingen en beslissingen",

                # API Communicatie
                "Een REST API (Representational State Transfer) is een manier voor computers om via het internet te communiceren",

                # Embeddings & Vectoren
                "Embeddings wijzen een unieke vector toe aan elke entiteit, zodat vergelijkbare items dicht bij elkaar liggen in de vectorruimte",
                "Machine learning en AI gebruiken embeddings voor taken als beeld- en tekstherkenning",

                # LLM Prompting & AI Instructies
                "Prompting is de kunst van instructies formuleren voor LLMs zoals Claude en GPT",
                "Zero-shot prompting vraagt zonder voorbeelden - het model moet de taak zelf begrijpen",
                "Few-shot prompting geeft voorbeelden waardoor het model het gewenste format leert",
                "Chain-of-Thought prompting laat AI stap voor stap redeneren voor complexe problemen",
                "Role prompting geeft het model een persona waardoor relevante kennis wordt geactiveerd",
                "Temperature bepaalt AI creativiteit: laag voor consistente, hoog voor creatieve outputs",

                # API Design & HTTP
                "REST APIs zijn stateless: de server onthoudt geen sessie informatie tussen requests",
                "HTTP statuscodes: 200 is succes, 404 niet gevonden, 500 is een server fout",
                "JWT (JSON Web Token) is stateless authenticatie met ingebouwde gebruikersinfo",
                "Rate limiting beschermt APIs tegen overbelasting met maximale requests per periode",
                "API versioning via URL paden zoals /api/v1/ zorgt voor backwards compatibility",
                "PATCH update specifieke velden terwijl PUT de hele resource vervangt",

                # Vector Database Technologie
                "ChromaDB en Pinecone zijn populaire vector databases voor AI toepassingen",
                "Euclidean distance meet de rechte lijn afstand tussen twee vectoren",
                "Bij RAG worden documenten eerst gesplit in chunks voor betere retrieval",
                "Cosine similarity van 1.0 betekent identieke vectoren, 0.0 betekent geen relatie",

                # ML Training & Evaluatie
                "Reinforcement learning leert door beloning en straf, zoals bij game AI en robotica",
                "Overfitting betekent dat het model trainingsdata uit het hoofd leert zonder te generaliseren",
                "Underfitting betekent dat het model te simpel is om patronen in de data te leren",
                "Model training kan uren of dagen duren, maar inference duurt slechts milliseconden",
                "Cross-validation en regularisatie zijn technieken om overfitting te voorkomen",
                "Precision meet hoeveel van de positieve voorspellingen correct zijn",
                "Recall meet hoeveel van de echte positieve gevallen gevonden zijn",
                "F1-Score is het harmonisch gemiddelde van precision en recall",

                # Python Geavanceerd
                "Decorators in Python wrappen functies om functionaliteit toe te voegen zonder code te wijzigen",
                "Generators gebruiken yield om waarden een voor een te produceren, wat geheugen bespaart",
                "Context managers met 'with' zorgen automatisch voor setup en cleanup van resources",
                "Dataclasses reduceren boilerplate code voor data containers met automatische __init__",
                "Async/await in Python maakt concurrent programmeren mogelijk voor I/O-bound taken",
                "lru_cache slaat functie-resultaten op zodat herhaalde aanroepen instant zijn",

                # Vector Databases - Geavanceerd
                "Pinecone is een fully managed cloud vector database die miljarden vectoren aankan",
                "Weaviate biedt hybrid search: zowel vector als keyword zoeken in één query",
                "FAISS van Facebook is extreem snel maar is een library, geen complete database",
                "Qdrant is een Rust-based vector database met filtering en payload support",
                "Milvus is enterprise-ready met GPU ondersteuning voor zeer grote datasets",
                "Bij RAG worden documenten gesplit in chunks van 200-500 tokens voor betere retrieval",
                "Top-K retrieval haalt de K meest relevante chunks op voor je vraag",
                "Dot product is een snellere similarity metric voor genormaliseerde vectoren",
                "Manhattan distance (L1) is minder gevoelig voor outliers dan Euclidean",
                "OpenAI embeddings hebben 1536 dimensies, Voyage AI heeft 1024 dimensies",

                # Machine Learning - Geavanceerd
                "K-Means clustering groepeert data in K clusters gebaseerd op afstand tot centroids",
                "Decision Trees splitsen data op basis van feature waarden in een boomstructuur",
                "Random Forest combineert vele decision trees voor robuustere voorspellingen",
                "Support Vector Machines (SVM) vinden de optimale scheidingslijn tussen klassen",
                "PCA reduceert dimensionaliteit door data te projecteren op hoofdcomponenten",
                "Autoencoders leren data te comprimeren en reconstrueren voor feature learning",
                "DBSCAN vindt clusters van willekeurige vorm gebaseerd op dichtheid",
                "Q-Learning leert optimale acties door trial and error in een omgeving",
                "Deep Q-Networks combineren Q-Learning met neural networks voor complexe games",
                "PPO (Proximal Policy Optimization) is een stabiele reinforcement learning methode",
                "MSE (Mean Squared Error) straft grote fouten zwaarder af dan kleine",
                "MAE (Mean Absolute Error) behandelt alle fouten gelijk ongeacht grootte",
                "R-squared meet hoeveel variantie het model verklaart (1.0 is perfect)",
                "Dropout zet willekeurige neuronen uit tijdens training om overfitting te voorkomen",
                "Batch normalization normaliseert activaties voor snellere en stabielere training",
                "Data augmentation vergroot je dataset door variaties te creëren",
                "Early stopping stopt training wanneer validatie loss niet meer daalt",

                # API Design - Geavanceerd
                "Idempotent requests (GET, PUT, DELETE) geven hetzelfde resultaat bij herhaling",
                "HATEOAS laat APIs links meegeven naar gerelateerde resources",
                "OAuth 2.0 access tokens verlopen na korte tijd, refresh tokens verlengen toegang",
                "API Gateway fungeert als single entry point voor alle microservices",
                "GraphQL laat clients precies specificeren welke data ze nodig hebben",
                "gRPC gebruikt Protocol Buffers voor snellere serialisatie dan JSON",
                "CORS headers bepalen welke domeinen je API mogen aanroepen vanuit browsers",
                "HTTP 201 Created wordt teruggegeven na succesvolle POST met nieuwe resource",
                "HTTP 204 No Content is succes zonder response body, vaak na DELETE",
                "HTTP 422 Unprocessable Entity betekent validatie fouten in de request",
                "Retry-After header vertelt de client hoelang te wachten na rate limiting",
                "ETag headers maken caching mogelijk door resource versies te tracken",

                # Neural Networks - Geavanceerd
                "ReLU voorkomt vanishing gradients door negatieve waarden op 0 te zetten",
                "Sigmoid squasht output tussen 0 en 1, perfect voor binaire classificatie",
                "Softmax zet een vector om naar kansen die optellen tot 1.0",
                "Tanh output ligt tussen -1 en 1, wat beter werkt dan sigmoid voor hidden layers",
                "Vanishing gradients ontstaan wanneer gradients te klein worden om te leren",
                "Exploding gradients zijn het tegenovergestelde: gradients worden oncontroleerbaar groot",
                "Gradient clipping voorkomt exploding gradients door ze te maximeren",
                "Adam optimizer combineert momentum en adaptive learning rates voor snelle training",
                "Learning rate decay verlaagt de learning rate naarmate training vordert",
                "LSTM forget gate bepaalt welke informatie uit het geheugen wordt gewist",
                "LSTM input gate bepaalt welke nieuwe informatie wordt toegevoegd aan geheugen",
                "Attention weegt de relevantie van elk input element voor de huidige output",
                "Multi-head attention voert parallel attention uit voor verschillende representaties",
                "Positional encoding geeft transformers informatie over woordvolgorde",
                "Layer normalization normaliseert activaties per sample in plaats van per batch",
                "Residual connections laten gradients direct door lagen stromen voor diepere netwerken",
                "Transfer learning hergebruikt voorgetrainde modellen voor nieuwe taken",

                # LLM Prompting - Geavanceerd
                "System prompts zetten de context en persona voor het hele gesprek",
                "Delimiters zoals ### of ``` scheiden instructies van data in prompts",
                "Negative prompting vertelt het model expliciet wat het NIET moet doen",
                "Prompt chaining splitst complexe taken in meerdere simpelere prompts",
                "Tree of Thoughts laat AI meerdere redeneringspaden parallel verkennen",
                "ReAct combineert reasoning en acting voor betere taakuitvoering",
                "Self-consistency genereert meerdere antwoorden en kiest de consensus",
                "Structured output vraagt om JSON of specifiek format voor parseerbaarheid",
                "Context window is de maximale hoeveelheid tekst die een LLM kan verwerken",
                "Token limiet bepaalt hoeveel tekst je kunt sturen en ontvangen",
                "Hallucinations zijn wanneer LLMs overtuigend maar onjuiste informatie genereren",
                "Grounding verbindt LLM output met betrouwbare externe bronnen",

                # Python Geavanceerd - Extra
                "functools.partial maakt nieuwe functies met sommige argumenten al ingevuld",
                "functools.reduce past een functie cumulatief toe op een lijst elementen",
                "Type hints verbeteren leesbaarheid en IDE ondersteuning zonder runtime effect",
                "Optional[T] geeft aan dat een waarde T of None kan zijn",
                "Callable[[args], return] specificeert functie signatures in type hints",
                "@property maakt een method toegankelijk als attribuut zonder haakjes",
                "slots beperkt attributen van een class voor geheugenefficiëntie",
                "@staticmethod heeft geen toegang tot self of cls, puur voor namespace",
                "@classmethod ontvangt de class als eerste argument in plaats van instance",
                "Abstract base classes (ABC) definiëren interfaces die subclasses moeten implementeren",
                "Metaclasses zijn classes die classes maken en aanpassen",
                "Descriptors zijn objecten die attribuut toegang customizen via __get__ en __set__",
            ]
            for feit in random.sample(ingebouwde_feiten, 3):
                if feit not in permanente_kennis["feiten"]:
                    feiten_geleerd.append({
                        "feit": feit,
                        "bron": "ingebouwde_kennis",
                        "datum": datetime.now().isoformat()
                    })
                    permanente_kennis["feiten"].append(feit)
                    permanente_kennis["bronnen"].append("ingebouwd")
                    permanente_kennis["geleerd_op"].append(datetime.now().isoformat())
                    self.huisdier["kennis"]["feiten"].append(feit)
                    intel_bonus += 2
                    print(f"  [LAMP] {naam} leert: \"{feit[:50]}...\"")

        # Update sessie teller
        permanente_kennis["totaal_sessies"] += 1

        # SLAAG PERMANENTE KENNIS OP NAAR LOKALE PC
        self._sla_permanente_kennis_op(permanente_kennis)

        # Resultaten
        print("\n" + "=" * 50)
        print("  [DIPLOMA] STUDIE SESSIE VOLTOOID!")
        print("=" * 50)

        xp_beloning = len(feiten_geleerd) * 12 + 5
        munt_beloning = len(feiten_geleerd) * 4

        totaal_permanent = len(permanente_kennis["feiten"])
        print(f"\n  {naam}'s studieresultaten:")
        print(f"    [BOEK] Nieuwe feiten: {len(feiten_geleerd)}")
        print(f"    [DISK] PERMANENT opgeslagen: {totaal_permanent} feiten")
        print(f"    [FILE] Locatie: {self.kennis_bestand}")
        print(f"    [#] Studie sessies: {permanente_kennis['totaal_sessies']}")
        print(f"    [IQ] Intelligentie: +{intel_bonus}")
        print(f"    [MUNT] Munten: +{munt_beloning}")
        print(f"    [XP] Ervaring: +{xp_beloning}")

        if echte_rag:
            print(f"\n  [STAR] Bonus: Echte RAG gebruikt!")
            if bronnen_gebruikt:
                print(f"  [BRON] Bestudeerd: {', '.join(bronnen_gebruikt)}")

        # Geef beloningen
        self.huisdier["munten"] += munt_beloning
        self.huisdier["ervaring"] += xp_beloning
        self.huisdier["intelligentie"] = self.huisdier.get("intelligentie", 0) + intel_bonus
        self.huisdier["stats"]["feiten_geleerd"] += len(feiten_geleerd)

        # Achievements
        if self.huisdier["stats"]["feiten_geleerd"] >= 10:
            self._unlock_achievement("kenniszoeker")
        if self.huisdier.get("intelligentie", 0) >= 100:
            self._unlock_achievement("super_slim")

        # Sync permanente kennis naar huisdier (beperk tot 100)
        self.huisdier["kennis"]["feiten"] = permanente_kennis["feiten"][-100:]

        self._check_evolutie()
        print(f"\n  {geluid}")
        print(f"  [INFO] Kennis blijft bewaard tot huisdier reset!")

        # LEARNING: Log RAG sessie naar Learning System
        if feiten_geleerd:
            self._init_learning()
            if self.learning:
                self.learning.log_rag_session(
                    files_read=bronnen_gebruikt,
                    facts_learned=[f["feit"] for f in feiten_geleerd],
                    context={
                        "iq": self.huisdier.get("intelligentie", 0),
                        "sessie": permanente_kennis["totaal_sessies"],
                    }
                )
                print(f"  [LEARN] {len(feiten_geleerd)} feiten naar Learning System!")

        self._sla_op()

    def _leren_nieuws(self):
        """Huisdier leest nieuws van de ECHTE Nieuws Agent."""
        if self.huisdier["munten"] < 8:
            print("\nJe hebt niet genoeg munten! (Nodig: 8)")
            return

        if self.huisdier["energie"] < 1:
            print(f"\n{self.huisdier['naam']} is te moe om te lezen!")
            return

        self.huisdier["munten"] -= 8
        self.huisdier["energie"] = max(0, self.huisdier["energie"] - 1)

        # Init kennis opslag
        if "kennis" not in self.huisdier:
            self.huisdier["kennis"] = {"feiten": [], "nieuws": [], "weer_historie": []}
        if "nieuws_gelezen" not in self.huisdier["stats"]:
            self.huisdier["stats"]["nieuws_gelezen"] = 0

        naam = self.huisdier["naam"]
        geluid = self.huisdier["geluid"]

        print("\n" + "=" * 50)
        print(f"  [KRANT] {naam} OPENT NIEUWS AGENT!")
        print("=" * 50)
        time.sleep(0.5)

        print(f"\n  {geluid}")

        gelezen = []
        intel_bonus = 0
        echte_nieuws = False

        try:
            nieuws_agent = _get_nieuws_agent()
            if nieuws_agent:
                print(f"  {naam} verbindt met de ECHTE Nieuws Agent...")
                time.sleep(0.5)
                echte_nieuws = True

                # Haal echte nieuws data
                alle_nieuws = nieuws_agent.web.zoek_alle_categorieen()
                trending = nieuws_agent.web.get_trending()

                print(f"  [OK] Nieuws database geladen!")
                print(f"  [HOT] Trending: {', '.join(trending[:3])}")

                # Lees nieuws uit verschillende categorieen
                for categorie, items in list(alle_nieuws.items())[:4]:
                    if items:
                        item = random.choice(items)
                        print(f"\n  --- {categorie.upper()} ---")
                        print(f"  [>] {item['titel']}")
                        print(f"      Bron: {item['bron']}")
                        time.sleep(0.3)

                        nieuws_entry = f"{categorie}: {item['titel']}"
                        if nieuws_entry not in self.huisdier["kennis"]["nieuws"]:
                            gelezen.append(item['titel'])
                            self.huisdier["kennis"]["nieuws"].append(nieuws_entry)
                            intel_bonus += 2
                            print(f"  [OK] {naam} onthoudt dit nieuws!")
                        else:
                            print(f"  [_] {naam} kende dit al...")

        except Exception as e:
            pass

        if not echte_nieuws:
            print(f"  [!] Nieuws Agent niet beschikbaar, gebruik cache...")
            # Fallback nieuws
            fallback_nieuws = [
                ("Tech", "SpaceX lanceert nieuwe Starship raket"),
                ("Sport", "Nederlands elftal wint belangrijke wedstrijd"),
                ("Wetenschap", "Doorbraak in AI onderzoek"),
                ("Natuur", "Nieuwe diersoort ontdekt"),
            ]
            for cat, titel in fallback_nieuws:
                entry = f"{cat}: {titel}"
                if entry not in self.huisdier["kennis"]["nieuws"]:
                    gelezen.append(titel)
                    self.huisdier["kennis"]["nieuws"].append(entry)
                    intel_bonus += 1
                    print(f"\n  [{cat.upper()}] {titel}")
                    print(f"  [OK] {naam} leest dit!")

        # Resultaten
        print("\n" + "=" * 50)
        print("  [NIEUWS] KLAAR MET LEZEN!")
        print("=" * 50)

        xp_beloning = len(gelezen) * 6 + 5
        munt_beloning = len(gelezen) * 3

        totaal_nieuws = len(self.huisdier["kennis"]["nieuws"])
        print(f"\n  {naam}'s nieuwsoverzicht:")
        print(f"    [KRANT] Nieuwe artikelen: {len(gelezen)}")
        print(f"    [DATABASE] Totaal gelezen: {totaal_nieuws}")
        print(f"    [IQ] Intelligentie: +{intel_bonus}")
        print(f"    [MUNT] Munten: +{munt_beloning}")
        print(f"    [XP] Ervaring: +{xp_beloning}")

        if echte_nieuws:
            print(f"\n  [STAR] Bonus: Echte Nieuws Agent gebruikt!")

        # Geef beloningen
        self.huisdier["munten"] += munt_beloning
        self.huisdier["ervaring"] += xp_beloning
        self.huisdier["intelligentie"] = self.huisdier.get("intelligentie", 0) + intel_bonus
        self.huisdier["stats"]["nieuws_gelezen"] += len(gelezen)
        self.huisdier["geluk"] = min(100, self.huisdier["geluk"] + 3)

        # Beperk nieuws opslag
        if len(self.huisdier["kennis"]["nieuws"]) > 50:
            self.huisdier["kennis"]["nieuws"] = self.huisdier["kennis"]["nieuws"][-50:]

        # Achievements
        if self.huisdier["stats"]["nieuws_gelezen"] >= 10:
            self._unlock_achievement("nieuwslezer")
        if self.huisdier.get("intelligentie", 0) >= 100:
            self._unlock_achievement("super_slim")

        self._check_evolutie()
        print(f"\n  {geluid}")

        # LEARNING: Log nieuws sessie naar Learning System
        if gelezen:
            self._init_learning()
            if self.learning:
                self.learning.log_news_session(
                    topics=["tech", "ai", "science"],
                    facts_learned=[g["titel"] for g in gelezen],
                    context={
                        "iq": self.huisdier.get("intelligentie", 0),
                        "geluk": self.huisdier.get("geluk", 50),
                    }
                )

        self._sla_op()

    def _leren_weer(self):
        """Huisdier checkt het weer met de ECHTE Weer Agent."""
        if self.huisdier["munten"] < 5:
            print("\nJe hebt niet genoeg munten! (Nodig: 5)")
            return

        self.huisdier["munten"] -= 5

        # Init kennis opslag
        if "kennis" not in self.huisdier:
            self.huisdier["kennis"] = {"feiten": [], "nieuws": [], "weer_historie": []}
        if "weer_gecheckt" not in self.huisdier["stats"]:
            self.huisdier["stats"]["weer_gecheckt"] = 0

        naam = self.huisdier["naam"]
        geluid = self.huisdier["geluid"]

        print("\n" + "=" * 50)
        print(f"  [WEER] {naam} OPENT WEER AGENT!")
        print("=" * 50)
        time.sleep(0.5)

        print(f"\n  {geluid}")

        intel_bonus = 1
        echte_weer = False

        try:
            weer_agent = _get_weer_agent()
            if weer_agent and hasattr(weer_agent, 'STEDEN'):
                print(f"  {naam} verbindt met de ECHTE Weer Agent...")
                time.sleep(0.5)
                echte_weer = True

                # Kies een random stad uit de echte steden database
                steden = list(weer_agent.STEDEN.keys())
                stad = random.choice(steden)
                stad_info = weer_agent.STEDEN[stad]

                print(f"  [OK] {len(steden)} Nederlandse steden beschikbaar!")
                print(f"\n  --- Weer in {stad.title()} ({stad_info['regio']}) ---")

                # Genereer weer data (de Weer Agent simuleert ook)
                temp = random.randint(-5, 30)
                wind = random.randint(0, 60)
                is_kust = stad_info.get('kust', False)

                if is_kust:
                    print(f"  [GOLF] Kustlocatie - extra winderig!")
                    wind += 10

                weer_types = ["Zonnig", "Bewolkt", "Lichte regen", "Buien", "Helder"]
                weer = random.choice(weer_types)

                print(f"  [WEER] {weer}")
                print(f"  [TEMP] Temperatuur: {temp}C")
                print(f"  [WIND] Wind: {wind} km/u")

                # Sla weer op in historie
                weer_entry = f"{stad.title()}: {temp}C, {weer}"
                self.huisdier["kennis"]["weer_historie"].append({
                    "stad": stad,
                    "temp": temp,
                    "weer": weer,
                    "datum": datetime.now().isoformat()
                })

                # Leer over het weer
                if temp > 25:
                    print(f"\n  [LAMP] {naam} leert: Het is warm weer! Veel drinken!")
                    intel_bonus += 1
                elif temp < 5:
                    print(f"\n  [LAMP] {naam} leert: Koud weer! Warm aankleden!")
                    intel_bonus += 1
                if wind > 40:
                    print(f"\n  [LAMP] {naam} leert: Harde wind! Pas op buiten!")
                    intel_bonus += 1

        except Exception as e:
            pass

        if not echte_weer:
            print(f"  {naam} kijkt naar buiten...")
            stad = random.choice(["Amsterdam", "Rotterdam", "Utrecht"])
            temp = random.randint(-5, 30)
            wind = random.randint(0, 60)
            weer = random.choice(["Zonnig", "Bewolkt", "Regen"])

            print(f"\n  --- Weer in {stad} ---")
            print(f"  [WEER] {weer}")
            print(f"  [TEMP] {temp}C")
            print(f"  [WIND] {wind} km/u")

        xp_beloning = 8 + intel_bonus * 2
        munt_beloning = 3

        print("\n" + "=" * 50)
        print(f"    [IQ] Intelligentie: +{intel_bonus}")
        print(f"    [MUNT] Munten: +{munt_beloning}")
        print(f"    [XP] Ervaring: +{xp_beloning}")

        if echte_weer:
            print(f"\n  [STAR] Bonus: Echte Weer Agent gebruikt!")

        # Beperk weer historie
        if len(self.huisdier["kennis"].get("weer_historie", [])) > 30:
            self.huisdier["kennis"]["weer_historie"] = self.huisdier["kennis"]["weer_historie"][-30:]

        # Geef beloningen
        self.huisdier["munten"] += munt_beloning
        self.huisdier["ervaring"] += xp_beloning
        self.huisdier["intelligentie"] = self.huisdier.get("intelligentie", 0) + intel_bonus
        self.huisdier["stats"]["weer_gecheckt"] += 1

        # Achievements
        if self.huisdier["stats"]["weer_gecheckt"] >= 10:
            self._unlock_achievement("weerwatcher")
        if self.huisdier.get("intelligentie", 0) >= 100:
            self._unlock_achievement("super_slim")

        self._check_evolutie()
        print(f"\n  {geluid}")

        # LEARNING: Log weer sessie naar Learning System
        self._init_learning()
        if self.learning:
            weer_info = f"{stad}: {weer}, {temp}C, {wind}km/u"
            self.learning.log_weather_session(
                location=stad,
                weather_info=weer_info,
                context={
                    "iq": self.huisdier.get("intelligentie", 0),
                }
            )

        self._sla_op()

    def _leren_ai_gesprek(self):
        """Huisdier heeft een gesprek met ECHTE Claude AI!"""
        if self.huisdier["munten"] < 15:
            print("\nJe hebt niet genoeg munten! (Nodig: 15)")
            return

        if self.huisdier["energie"] < 2:
            print(f"\n{self.huisdier['naam']} is te moe voor een diep gesprek!")
            return

        self.huisdier["munten"] -= 15
        self.huisdier["energie"] = max(0, self.huisdier["energie"] - 2)

        # Init stats en kennis
        if "ai_gesprekken" not in self.huisdier["stats"]:
            self.huisdier["stats"]["ai_gesprekken"] = 0
        if "kennis" not in self.huisdier:
            self.huisdier["kennis"] = {"feiten": [], "nieuws": [], "weer_historie": []}

        naam = self.huisdier["naam"]
        geluid = self.huisdier["geluid"]
        huisdier_type = self.huisdier["type"]
        iq = self.huisdier.get("intelligentie", 0)

        print("\n" + "=" * 50)
        print(f"  [AI] {naam} PRAAT MET ECHTE CLAUDE AI!")
        print("=" * 50)
        time.sleep(0.5)

        print(f"\n  {geluid}")
        print(f"  {naam} opent Claude Chat...")
        time.sleep(0.5)

        # Probeer ECHTE Claude Chat te gebruiken
        echte_ai = False
        claude_chat = None
        intel_bonus = 0
        lessen_geleerd = []

        try:
            claude_chat = _get_claude_chat()
            if claude_chat:
                echte_ai = True
                print(f"  [OK] Verbonden met ECHTE {claude_chat.provider.upper()} API!")
                print(f"  [MODEL] {claude_chat.model}")
        except Exception as e:
            print(f"  [!] Kon niet verbinden: {e}")

        # Vragen die het huisdier kan stellen (aangepast aan IQ)
        basis_vragen = [
            "Wat is kunstmatige intelligentie in eenvoudige woorden?",
            "Waarom is de lucht blauw?",
            "Hoe werkt het internet?",
            "Wat zijn zwarte gaten?",
            "Hoe leren dieren trucs?",
            "Wat is machine learning?",
            "Hoe werkt een REST API?",
            "Wat is een computer virus?",
            "Hoe werkt wifi?",
            "Wat is de cloud?",
            "Hoe werkt een zoekmachine?",
            "Wat is een algoritme?",
            "Hoe werkt een smartphone?",
            "Wat is programmeren?",
            "Hoe werkt een database?",
            "Wat is een website?",
            "Hoe werkt email?",
            "Wat is cybersecurity?",
            "Hoe werkt een browser?",
            "Wat is open source software?",
        ]

        geavanceerde_vragen = [
            "Leg uit hoe neural networks werken.",
            "Wat is het verschil tussen machine learning en deep learning?",
            "Hoe werkt natuurlijke taalverwerking (NLP)?",
            "Wat zijn de ethische uitdagingen van AI?",
            "Hoe kunnen computers creativiteit simuleren?",
            "Wat is een vector database en waarvoor wordt het gebruikt?",
            "Hoe werken embeddings in machine learning?",
            "Wat is het verschil tussen supervised en unsupervised learning?",
            "Hoe werkt een REST API met HTTP methodes?",
            "Wat is de rol van backpropagation in neural networks?",
            "Hoe werkt reinforcement learning?",
            "Wat is overfitting en hoe voorkom je het?",
            "Hoe werkt een CNN voor beeldherkenning?",
            "Wat is tokenization in NLP?",
            "Hoe werkt gradient descent?",
            "Wat is transfer learning?",
            "Hoe werken recommendation systems?",
            "Wat is een decision tree?",
            "Hoe werkt K-means clustering?",
            "Wat is feature engineering?",
        ]

        expert_vragen = [
            "Hoe werkt semantic search met vector databases?",
            "Wat is RAG (Retrieval Augmented Generation)?",
            "Hoe werkt cosine similarity bij embeddings?",
            "Wat zijn transformers en attention mechanismen?",
            "Hoe werkt fine-tuning van grote taalmodellen?",
            "Wat is de vanishing gradient problem?",
            "Hoe werkt LSTM en waarom is het beter dan RNN?",
            "Wat is batch normalization?",
            "Hoe werkt dropout als regularisatie?",
            "Wat is de softmax functie?",
            "Hoe werkt multi-head attention?",
            "Wat zijn positional encodings?",
            "Hoe werkt beam search bij text generation?",
            "Wat is knowledge distillation?",
            "Hoe werkt RLHF (Reinforcement Learning from Human Feedback)?",
            "Wat is prompt engineering?",
            "Hoe werkt chain-of-thought prompting?",
            "Wat is few-shot learning?",
            "Hoe werkt contrastive learning?",
            "Wat zijn graph neural networks?",
        ]

        # Kies vragen gebaseerd op IQ
        if iq >= 80:
            alle_vragen = basis_vragen + geavanceerde_vragen + expert_vragen
        elif iq >= 50:
            alle_vragen = basis_vragen + geavanceerde_vragen
        else:
            alle_vragen = basis_vragen

        # Systeem prompt voor educatieve antwoorden
        systeem_prompt = f"""Je bent een vriendelijke leraar die praat met een slim virtueel huisdier genaamd {naam} (een {huisdier_type}).
{naam} heeft een IQ van {iq} en wil graag leren.
Geef korte, educatieve antwoorden (max 2-3 zinnen).
Eindig elk antwoord met een interessant feit dat {naam} kan onthouden.
Antwoord in het Nederlands."""

        # Voer gesprekken (3 vragen!)
        aantal_vragen = 3
        gekozen_vragen = random.sample(alle_vragen, min(aantal_vragen, len(alle_vragen)))

        for i, vraag in enumerate(gekozen_vragen, 1):
            print(f"\n  --- Gesprek {i}/{len(gekozen_vragen)} ---")
            print(f"  {naam}: \"{vraag}\"")
            time.sleep(0.5)

            antwoord = None
            les = None

            if echte_ai and claude_chat:
                try:
                    # ECHTE AI aanroep!
                    berichten = [{"role": "user", "content": vraag}]
                    antwoord = claude_chat._chat_conversatie(berichten, systeem_prompt)

                    # Extract een les uit het antwoord (eerste zin of feit)
                    zinnen = antwoord.replace("!", ".").replace("?", ".").split(".")
                    for zin in zinnen:
                        zin = zin.strip()
                        if len(zin) > 15 and len(zin) < 150:
                            les = zin
                            break

                    print(f"  Claude: \"{antwoord[:200]}{'...' if len(antwoord) > 200 else ''}\"")
                    intel_bonus += 5  # Meer bonus voor echte AI
                except Exception as e:
                    print(f"  [!] API fout: {e}")
                    antwoord = None

            # Fallback naar gesimuleerde antwoorden met TECH KENNIS
            if not antwoord:
                fallback_antwoorden = {
                    # Basis AI/ML
                    "kunstmatige intelligentie": (
                        "AI zijn computerprogramma's die kunnen leren en beslissingen nemen!",
                        "AI bootst menselijke intelligentie na met algoritmes"
                    ),
                    "machine learning": (
                        "Machine Learning laat computers leren van data zonder expliciete programmering!",
                        "ML vindt patronen in data om voorspellingen te maken"
                    ),
                    "deep learning": (
                        "Deep Learning gebruikt diepe neural networks met vele lagen!",
                        "Meer lagen = meer abstracte features leren"
                    ),
                    "neural network": (
                        "Neural networks zijn geinspireerd op het menselijk brein met neuronen en connecties!",
                        "Neuronen geven signalen door via gewogen verbindingen"
                    ),
                    "backpropagation": (
                        "Backpropagation berekent hoe weights aangepast moeten worden door de error terug te propageren!",
                        "De chain rule uit calculus maakt backprop mogelijk"
                    ),

                    # Vector Databases
                    "vector database": (
                        "Een vector database slaat embeddings op en zoekt op basis van gelijkenis!",
                        "Vectoren representeren betekenis als getallen"
                    ),
                    "embedding": (
                        "Embeddings zijn numerieke representaties van tekst, woorden of concepten!",
                        "Vergelijkbare betekenissen hebben vergelijkbare vectoren"
                    ),
                    "cosine similarity": (
                        "Cosine similarity meet de hoek tussen twee vectoren om gelijkenis te bepalen!",
                        "Waarde 1 = identiek, 0 = geen relatie"
                    ),
                    "semantic search": (
                        "Semantic search vindt resultaten op basis van betekenis, niet alleen keywords!",
                        "Vector databases maken semantic search mogelijk"
                    ),

                    # REST API
                    "rest api": (
                        "REST API's gebruiken HTTP methodes (GET, POST, PUT, DELETE) voor communicatie!",
                        "REST staat voor Representational State Transfer"
                    ),
                    "http methode": (
                        "GET haalt data op, POST stuurt nieuwe data, PUT wijzigt, DELETE verwijdert!",
                        "Elke HTTP methode heeft een specifiek doel"
                    ),

                    # RAG & Advanced
                    "rag": (
                        "RAG combineert retrieval (zoeken) met generation (AI antwoorden) voor betere resultaten!",
                        "RAG voorkomt hallucinaties door echte bronnen te gebruiken"
                    ),
                    "transformer": (
                        "Transformers gebruiken attention om relaties tussen alle woorden tegelijk te zien!",
                        "GPT en BERT zijn gebaseerd op transformers"
                    ),
                    "attention": (
                        "Attention laat het model focussen op relevante delen van de input!",
                        "Self-attention weegt elk woord tegen alle andere"
                    ),
                    "fine-tuning": (
                        "Fine-tuning traint een voorgetraind model verder op specifieke data!",
                        "Je past de weights aan voor jouw use case"
                    ),
                    "supervised": (
                        "Supervised learning traint met gelabelde data waar het juiste antwoord bekend is!",
                        "Het model leert input-output mappings"
                    ),
                    "unsupervised": (
                        "Unsupervised learning vindt patronen in data zonder labels!",
                        "Clustering en dimensie reductie zijn voorbeelden"
                    ),
                    "nlp": (
                        "NLP (Natural Language Processing) laat computers menselijke taal begrijpen!",
                        "Chatbots en vertalers gebruiken NLP"
                    ),

                    # Algemeen
                    "lucht blauw": ("Zonlicht verstrooit in de atmosfeer!", "Rayleigh-verstrooiing"),
                    "internet": ("Het internet verbindt computers wereldwijd!", "Data reist via kabels en wifi"),
                    "zwarte gaten": ("Zwarte gaten hebben extreme zwaartekracht!", "Einstein voorspelde ze"),
                    "dieren trucs": ("Dieren leren door beloning en herhaling!", "Positieve bekrachtiging werkt"),
                }

                for keyword, (resp, feit) in fallback_antwoorden.items():
                    if keyword in vraag.lower():
                        antwoord = resp
                        les = feit
                        break

                if not antwoord:
                    antwoord = "Dat is een interessante vraag! Ik moet hier meer over leren."
                    les = "Nieuwsgierigheid is de sleutel tot leren"

                print(f"  Claude: \"{antwoord}\"")
                intel_bonus += 2

            # Leer de les
            if les and random.randint(1, 100) <= 90:
                lessen_geleerd.append(les)
                print(f"  [LAMP] {naam} leert: \"{les}\"")

                # Sla op in permanente kennis als het echt is
                if echte_ai and les not in self.huisdier["kennis"]["feiten"]:
                    self.huisdier["kennis"]["feiten"].append(les)
                    # Ook in permanente opslag
                    permanente_kennis = self._laad_permanente_kennis()
                    if les not in permanente_kennis["feiten"]:
                        permanente_kennis["feiten"].append(les)
                        permanente_kennis["bronnen"].append("Claude AI")
                        permanente_kennis["geleerd_op"].append(datetime.now().isoformat())
                        self._sla_permanente_kennis_op(permanente_kennis)
                        print(f"  [SAVE] Opgeslagen in permanente kennis!")
            else:
                print(f"  [?] {naam} denkt hier nog over na...")

            time.sleep(0.3)

        # Resultaten
        print("\n" + "=" * 50)
        print("  [CHAT] AI GESPREK VOLTOOID!")
        print("=" * 50)

        xp_beloning = len(lessen_geleerd) * 15 + 10
        munt_beloning = len(lessen_geleerd) * 5

        # Extra bonus voor echte AI
        if echte_ai:
            intel_bonus += 5
            munt_beloning += 10

        print(f"\n  {naam}'s gesprek met Claude:")
        print(f"    [CHAT] Gesprekken: {len(gekozen_vragen)}")
        if echte_ai:
            print(f"    [STAR] ECHTE AI gebruikt!")
        print(f"    [LAMP] Lessen geleerd: {len(lessen_geleerd)}")
        print(f"    [IQ] Intelligentie: +{intel_bonus}")
        print(f"    [MUNT] Munten: +{munt_beloning}")
        print(f"    [XP] Ervaring: +{xp_beloning}")

        if len(lessen_geleerd) >= 15:
            bonus = 50
            print(f"\n  [TROFEE] SUPER STUDENT! 15+ lessen! Bonus: +{bonus} munten!")
            munt_beloning += bonus
        elif len(lessen_geleerd) >= 10:
            bonus = 25
            print(f"\n  [TROFEE] GOEDE STUDENT! 10+ lessen! Bonus: +{bonus} munten!")
            munt_beloning += bonus

        # Geef beloningen
        self.huisdier["munten"] += munt_beloning
        self.huisdier["ervaring"] += xp_beloning
        self.huisdier["intelligentie"] = self.huisdier.get("intelligentie", 0) + intel_bonus
        self.huisdier["stats"]["ai_gesprekken"] += 1
        self.huisdier["geluk"] = min(100, self.huisdier["geluk"] + 5)

        # Achievements
        if self.huisdier["stats"]["ai_gesprekken"] >= 10:
            self._unlock_achievement("ai_student")
        if self.huisdier.get("intelligentie", 0) >= 100:
            self._unlock_achievement("super_slim")

        self._check_evolutie()
        print(f"\n  {geluid}")

        # LEARNING: Log AI gesprek naar Learning System
        if lessen_geleerd:
            self._init_learning()
            if self.learning:
                self.learning.log_ai_conversation(
                    questions=gekozen_vragen,
                    answers=[],  # Antwoorden niet opgeslagen
                    lessons=lessen_geleerd,
                    context={
                        "iq": self.huisdier.get("intelligentie", 0),
                        "echte_ai": echte_ai,
                    }
                )
                print(f"  [LEARN] {len(lessen_geleerd)} lessen opgeslagen!")

        self._sla_op()

    def _ai_code_helper(self):
        """AI helpt met programmeren - code uitleggen en genereren!"""
        if self.huisdier["munten"] < 20:
            print("\nJe hebt niet genoeg munten! (Nodig: 20)")
            return

        if self.huisdier["energie"] < 3:
            print(f"\n{self.huisdier['naam']} is te moe voor programmeren!")
            return

        self.huisdier["munten"] -= 20
        self.huisdier["energie"] = max(0, self.huisdier["energie"] - 3)

        naam = self.huisdier["naam"]
        geluid = self.huisdier["geluid"]
        iq = self.huisdier.get("intelligentie", 0)

        print("\n" + "=" * 55)
        print(f"  [CODE] {naam} OPENT DE AI CODE HELPER!")
        print("=" * 55)

        print("\n  Wat wil je doen?")
        print("  1. Code laten uitleggen")
        print("  2. Code laten genereren")
        print("  3. Programmeer concept leren")

        keuze = input("\n  Keuze (1-3): ").strip()

        intel_bonus = 0
        code_geleerd = []

        # Probeer echte AI
        claude_chat = None
        echte_ai = False
        try:
            claude_chat = _get_claude_chat()
            if claude_chat:
                echte_ai = True
                print(f"\n  [OK] Verbonden met {claude_chat.provider.upper()} AI!")
        except Exception as e:
            logger.debug("Failed to connect to Claude AI for coding lesson: %s", e)

        if keuze == "1":
            # Code uitleggen
            print("\n  --- CODE UITLEG ---")
            print("  Plak je code hieronder (typ 'KLAAR' als je klaar bent):")
            code_lines = []
            while True:
                line = input()
                if line.strip().upper() == "KLAAR":
                    break
                code_lines.append(line)

            code = "\n".join(code_lines)
            if code.strip():
                print(f"\n  {naam} analyseert de code...")
                time.sleep(0.5)

                if echte_ai and claude_chat:
                    try:
                        prompt = f"Leg deze code uit in het Nederlands, kort en duidelijk:\n\n{code}"
                        berichten = [{"role": "user", "content": prompt}]
                        uitleg = claude_chat._chat_conversatie(berichten, "Je bent een code uitleg expert. Antwoord in het Nederlands.")
                        print(f"\n  Claude: {uitleg[:400]}{'...' if len(uitleg) > 400 else ''}")
                        intel_bonus += 8
                        code_geleerd.append("Code analyse uitgevoerd met AI")
                    except Exception as e:
                        print(f"  [!] API fout: {e}")
                else:
                    # Fallback: basis code analyse
                    print(f"\n  [ANALYSE] Code bevat {len(code_lines)} regels")
                    if "def " in code:
                        print("  [LAMP] Gevonden: functie definitie(s)")
                        code_geleerd.append("Python functies gebruiken 'def'")
                    if "class " in code:
                        print("  [LAMP] Gevonden: class definitie(s)")
                        code_geleerd.append("Classes maken objecten")
                    if "for " in code or "while " in code:
                        print("  [LAMP] Gevonden: loop(s)")
                        code_geleerd.append("Loops herhalen code")
                    if "import " in code:
                        print("  [LAMP] Gevonden: import statement(s)")
                        code_geleerd.append("Imports laden modules")
                    intel_bonus += 3

        elif keuze == "2":
            # Code genereren
            print("\n  --- CODE GENERATOR ---")
            beschrijving = input("  Beschrijf wat de code moet doen: ").strip()

            if beschrijving:
                print(f"\n  {naam} genereert code...")
                time.sleep(0.5)

                if echte_ai and claude_chat:
                    try:
                        prompt = f"Schrijf Python code die het volgende doet: {beschrijving}. Voeg comments toe in het Nederlands."
                        berichten = [{"role": "user", "content": prompt}]
                        code = claude_chat._chat_conversatie(berichten, "Je bent een Python expert. Geef alleen code met comments.")
                        print(f"\n  --- GEGENEREERDE CODE ---\n{code[:600]}{'...' if len(code) > 600 else ''}")
                        intel_bonus += 10
                        code_geleerd.append(f"Code generatie: {beschrijving[:50]}")
                    except Exception as e:
                        print(f"  [!] API fout: {e}")
                else:
                    # Fallback: voorbeeldcode templates
                    templates = {
                        "lijst": "# Lijst maken\nmijn_lijst = [1, 2, 3]\nfor item in mijn_lijst:\n    print(item)",
                        "functie": "# Functie maken\ndef mijn_functie(x):\n    return x * 2\n\nprint(mijn_functie(5))",
                        "class": "# Class maken\nclass MijnClass:\n    def __init__(self):\n        self.waarde = 0",
                        "bestand": "# Bestand lezen\nwith open('bestand.txt', 'r') as f:\n    inhoud = f.read()",
                    }
                    for key, template in templates.items():
                        if key in beschrijving.lower():
                            print(f"\n  --- VOORBEELD CODE ---\n{template}")
                            code_geleerd.append(f"Geleerd: {key} code")
                            break
                    else:
                        print("\n  [TIP] Probeer woorden als: lijst, functie, class, bestand")
                    intel_bonus += 3

        elif keuze == "3":
            # Programmeer concept leren
            print("\n  --- PROGRAMMEER CONCEPTEN ---")
            concepten = {
                "1": ("Variabelen", "Variabelen zijn containers voor data. x = 5 slaat het getal 5 op in x."),
                "2": ("Loops", "Loops herhalen code. 'for i in range(5)' herhaalt 5 keer."),
                "3": ("Functies", "Functies zijn herbruikbare codeblokken. 'def naam():' maakt een functie."),
                "4": ("Classes", "Classes zijn blauwdrukken voor objecten met eigenschappen en methodes."),
                "5": ("Lijsten", "Lijsten slaan meerdere waarden op. [1, 2, 3] is een lijst met 3 items."),
                "6": ("Dictionaries", "Dictionaries slaan key-value paren op. {'naam': 'Jan'} heeft key 'naam'."),
                "7": ("Error Handling", "Try/except vangt fouten op. try: code except: foutafhandeling"),
                "8": ("List Comprehension", "Korte syntax voor lijsten: [x*2 for x in range(5)] maakt [0,2,4,6,8]"),
            }
            print("  Kies een concept:")
            for num, (concept, _) in concepten.items():
                print(f"    {num}. {concept}")

            concept_keuze = input("\n  Keuze: ").strip()
            if concept_keuze in concepten:
                concept_naam, uitleg = concepten[concept_keuze]
                print(f"\n  [LAMP] {concept_naam}:")
                print(f"  {uitleg}")
                code_geleerd.append(f"Concept geleerd: {concept_naam}")
                intel_bonus += 5

        # Resultaten
        print("\n" + "=" * 55)
        print("  [CODE] CODE SESSIE VOLTOOID!")
        print("=" * 55)

        xp_beloning = len(code_geleerd) * 20 + 15
        munt_beloning = len(code_geleerd) * 8

        if echte_ai:
            munt_beloning += 15
            intel_bonus += 5

        print(f"\n  {naam}'s programmeer sessie:")
        print(f"    [CODE] Items geleerd: {len(code_geleerd)}")
        print(f"    [IQ] Intelligentie: +{intel_bonus}")
        print(f"    [MUNT] Munten: +{munt_beloning}")
        print(f"    [XP] Ervaring: +{xp_beloning}")

        self.huisdier["munten"] += munt_beloning
        self.huisdier["ervaring"] += xp_beloning
        self.huisdier["intelligentie"] = self.huisdier.get("intelligentie", 0) + intel_bonus
        self.huisdier["geluk"] = min(100, self.huisdier["geluk"] + 5)

        print(f"\n  {geluid}")
        self._sla_op()

    def _ai_quiz_master(self):
        """AI stelt quiz vragen om kennis te testen!"""
        if self.huisdier["munten"] < 12:
            print("\nJe hebt niet genoeg munten! (Nodig: 12)")
            return

        if self.huisdier["energie"] < 2:
            print(f"\n{self.huisdier['naam']} is te moe voor een quiz!")
            return

        self.huisdier["munten"] -= 12
        self.huisdier["energie"] = max(0, self.huisdier["energie"] - 2)

        naam = self.huisdier["naam"]
        geluid = self.huisdier["geluid"]
        iq = self.huisdier.get("intelligentie", 0)

        print("\n" + "=" * 55)
        print(f"  [QUIZ] {naam} DOET DE AI QUIZ!")
        print("=" * 55)

        # Quiz vragen per niveau
        quiz_vragen = {
            "makkelijk": [
                ("Wat is 2 + 2?", "4", ["4", "vier"]),
                ("Welke kleur heeft de lucht overdag?", "blauw", ["blauw"]),
                ("Hoeveel dagen heeft een week?", "7", ["7", "zeven"]),
                ("Wat is de hoofdstad van Nederland?", "Amsterdam", ["amsterdam"]),
                ("In welke taal is Python geschreven?", "C", ["c"]),
            ],
            "gemiddeld": [
                ("Wat doet 'print()' in Python?", "tekst weergeven", ["print", "weergeven", "output", "tonen"]),
                ("Wat is een variabele?", "container voor data", ["container", "opslag", "waarde"]),
                ("Wat betekent AI?", "Artificial Intelligence", ["artificial", "kunstmatige", "intelligentie"]),
                ("Wat is een loop in programmeren?", "code herhalen", ["herhalen", "repeat", "iteratie"]),
                ("Welk HTTP method haalt data op?", "GET", ["get"]),
            ],
            "moeilijk": [
                ("Wat is een neural network?", "model geinspireerd op het brein", ["brein", "neuronen", "lagen"]),
                ("Wat doet backpropagation?", "gradients berekenen", ["gradient", "weights", "leren", "error"]),
                ("Wat is cosine similarity?", "hoek tussen vectoren meten", ["hoek", "vector", "gelijkenis"]),
                ("Wat is RAG?", "Retrieval Augmented Generation", ["retrieval", "generation", "zoeken"]),
                ("Wat is een embedding?", "numerieke representatie", ["vector", "numeriek", "representatie"]),
            ],
        }

        # Kies niveau op basis van IQ
        if iq >= 70:
            niveau = "moeilijk"
            alle_vragen = quiz_vragen["moeilijk"] + quiz_vragen["gemiddeld"]
        elif iq >= 40:
            niveau = "gemiddeld"
            alle_vragen = quiz_vragen["gemiddeld"] + quiz_vragen["makkelijk"]
        else:
            niveau = "makkelijk"
            alle_vragen = quiz_vragen["makkelijk"]

        print(f"\n  Quiz niveau: {niveau.upper()} (IQ: {iq})")
        print("  Beantwoord 5 vragen!\n")

        gekozen = random.sample(alle_vragen, min(5, len(alle_vragen)))
        score = 0
        intel_bonus = 0

        for i, (vraag, antwoord, acceptabel) in enumerate(gekozen, 1):
            print(f"  Vraag {i}: {vraag}")
            gebruiker_antwoord = input("  Jouw antwoord: ").strip().lower()

            correct = any(acc.lower() in gebruiker_antwoord for acc in acceptabel)
            if correct:
                print(f"  [OK] Correct! Het antwoord was: {antwoord}")
                score += 1
                intel_bonus += 3
            else:
                print(f"  [X] Helaas! Het antwoord was: {antwoord}")
                intel_bonus += 1  # Ook leren van fouten

            time.sleep(0.3)

        # Resultaten
        print("\n" + "=" * 55)
        print("  [QUIZ] QUIZ VOLTOOID!")
        print("=" * 55)

        percentage = (score / 5) * 100
        print(f"\n  Score: {score}/5 ({percentage:.0f}%)")

        if percentage == 100:
            print("  [TROFEE] PERFECTE SCORE!")
            bonus = 20
        elif percentage >= 80:
            print("  [STAR] Uitstekend!")
            bonus = 10
        elif percentage >= 60:
            print("  [OK] Goed gedaan!")
            bonus = 5
        else:
            print("  [TIP] Blijf oefenen!")
            bonus = 0

        xp_beloning = score * 15 + 10
        munt_beloning = score * 5 + bonus

        print(f"\n  {naam}'s quiz resultaat:")
        print(f"    [QUIZ] Score: {score}/5")
        print(f"    [IQ] Intelligentie: +{intel_bonus}")
        print(f"    [MUNT] Munten: +{munt_beloning}")
        print(f"    [XP] Ervaring: +{xp_beloning}")

        self.huisdier["munten"] += munt_beloning
        self.huisdier["ervaring"] += xp_beloning
        self.huisdier["intelligentie"] = self.huisdier.get("intelligentie", 0) + intel_bonus
        self.huisdier["geluk"] = min(100, self.huisdier["geluk"] + 5)

        print(f"\n  {geluid}")
        self._sla_op()

    def _ai_verhalen(self):
        """AI genereert creatieve verhalen!"""
        if self.huisdier["munten"] < 18:
            print("\nJe hebt niet genoeg munten! (Nodig: 18)")
            return

        if self.huisdier["energie"] < 2:
            print(f"\n{self.huisdier['naam']} is te moe voor verhalen!")
            return

        self.huisdier["munten"] -= 18
        self.huisdier["energie"] = max(0, self.huisdier["energie"] - 2)

        naam = self.huisdier["naam"]
        geluid = self.huisdier["geluid"]
        huisdier_type = self.huisdier["type"]

        print("\n" + "=" * 55)
        print(f"  [BOEK] {naam} MAAKT EEN VERHAAL!")
        print("=" * 55)

        print("\n  Kies een verhaal type:")
        print("  1. Avontuur")
        print("  2. Grappig")
        print("  3. Mysterie")
        print("  4. Sci-Fi")
        print("  5. Eigen onderwerp")

        keuze = input("\n  Keuze (1-5): ").strip()

        themas = {
            "1": "avontuurlijk verhaal vol actie",
            "2": "grappig verhaal dat je laat lachen",
            "3": "mysterieus verhaal met spanning",
            "4": "science fiction verhaal in de toekomst",
        }

        if keuze == "5":
            thema = input("  Beschrijf je verhaal onderwerp: ").strip()
        else:
            thema = themas.get(keuze, "spannend verhaal")

        print(f"\n  {naam} bedenkt een verhaal...")
        time.sleep(1)

        # Probeer echte AI
        verhaal = None
        echte_ai = False
        intel_bonus = 0

        try:
            claude_chat = _get_claude_chat()
            if claude_chat:
                echte_ai = True
                prompt = f"Schrijf een kort {thema} voor kinderen over een {huisdier_type} genaamd {naam}. Max 150 woorden, in het Nederlands."
                berichten = [{"role": "user", "content": prompt}]
                verhaal = claude_chat._chat_conversatie(berichten, "Je bent een creatieve kinderverhalen schrijver.")
                intel_bonus = 10
        except Exception as e:
            logger.debug("AI story generation failed: %s", e)

        if not verhaal:
            # Fallback verhalen
            fallback_verhalen = [
                f"Op een dag besloot {naam} de {huisdier_type} op avontuur te gaan. "
                f"Door het bos wandelend vond {naam} een glinsterende steen. "
                f"Het bleek een magische steen te zijn die wensen vervulde! "
                f"{naam} wenste voor altijd gelukkig te zijn met de beste eigenaar ooit.",

                f"{naam} de {huisdier_type} werd wakker met een gek idee. "
                f"Vandaag zou {naam} leren vliegen! Na veel pogingen en grappige buitelingen "
                f"ontdekte {naam} dat vliegen niet nodig was - springen was veel leuker!",

                f"In een land ver weg woonde {naam}, de slimste {huisdier_type} ter wereld. "
                f"Wetenschappers kwamen van heinde en verre om {naam}'s wijsheid te horen. "
                f"Het geheim? Elke dag iets nieuws leren en nooit opgeven!",
            ]
            verhaal = random.choice(fallback_verhalen)
            intel_bonus = 4

        print("\n  " + "-" * 50)
        print(f"  {verhaal}")
        print("  " + "-" * 50)

        # Resultaten
        print("\n" + "=" * 55)
        print("  [BOEK] VERHAAL VOLTOOID!")
        print("=" * 55)

        xp_beloning = 25
        munt_beloning = 8

        if echte_ai:
            munt_beloning += 10
            intel_bonus += 5
            print("  [STAR] ECHTE AI verhaal!")

        print(f"\n  {naam}'s creatieve sessie:")
        print(f"    [BOEK] Verhaal gemaakt!")
        print(f"    [IQ] Intelligentie: +{intel_bonus} (creativiteit)")
        print(f"    [MUNT] Munten: +{munt_beloning}")
        print(f"    [XP] Ervaring: +{xp_beloning}")

        self.huisdier["munten"] += munt_beloning
        self.huisdier["ervaring"] += xp_beloning
        self.huisdier["intelligentie"] = self.huisdier.get("intelligentie", 0) + intel_bonus
        self.huisdier["geluk"] = min(100, self.huisdier["geluk"] + 8)

        print(f"\n  {geluid}")
        self._sla_op()

    def _ai_vertaler(self):
        """AI vertaalt tekst naar andere talen!"""
        if self.huisdier["munten"] < 10:
            print("\nJe hebt niet genoeg munten! (Nodig: 10)")
            return

        if self.huisdier["energie"] < 1:
            print(f"\n{self.huisdier['naam']} is te moe om te vertalen!")
            return

        self.huisdier["munten"] -= 10
        self.huisdier["energie"] = max(0, self.huisdier["energie"] - 1)

        naam = self.huisdier["naam"]
        geluid = self.huisdier["geluid"]

        print("\n" + "=" * 55)
        print(f"  [TAAL] {naam} DE VERTALER!")
        print("=" * 55)

        print("\n  Kies de doeltaal:")
        print("  1. Engels")
        print("  2. Duits")
        print("  3. Frans")
        print("  4. Spaans")
        print("  5. Italiaans")

        talen = {
            "1": ("Engels", "English"),
            "2": ("Duits", "German"),
            "3": ("Frans", "French"),
            "4": ("Spaans", "Spanish"),
            "5": ("Italiaans", "Italian"),
        }

        keuze = input("\n  Keuze (1-5): ").strip()
        if keuze not in talen:
            keuze = "1"

        taal_nl, taal_en = talen[keuze]
        tekst = input(f"\n  Typ de tekst om te vertalen naar {taal_nl}: ").strip()

        if not tekst:
            print("  [!] Geen tekst ingevoerd!")
            return

        print(f"\n  {naam} vertaalt naar {taal_nl}...")
        time.sleep(0.5)

        vertaling = None
        echte_ai = False
        intel_bonus = 0

        try:
            claude_chat = _get_claude_chat()
            if claude_chat:
                echte_ai = True
                prompt = f"Vertaal deze tekst naar {taal_en}. Geef alleen de vertaling, niets anders:\n\n{tekst}"
                berichten = [{"role": "user", "content": prompt}]
                vertaling = claude_chat._chat_conversatie(berichten, "Je bent een professionele vertaler.")
                intel_bonus = 6
        except Exception as e:
            logger.debug("AI translation failed: %s", e)

        if not vertaling:
            # Fallback: basis woordenboek
            basis_woorden = {
                "Engels": {"hallo": "hello", "ja": "yes", "nee": "no", "dank je": "thank you", "hond": "dog", "kat": "cat"},
                "Duits": {"hallo": "hallo", "ja": "ja", "nee": "nein", "dank je": "danke", "hond": "Hund", "kat": "Katze"},
                "Frans": {"hallo": "bonjour", "ja": "oui", "nee": "non", "dank je": "merci", "hond": "chien", "kat": "chat"},
                "Spaans": {"hallo": "hola", "ja": "si", "nee": "no", "dank je": "gracias", "hond": "perro", "kat": "gato"},
                "Italiaans": {"hallo": "ciao", "ja": "si", "nee": "no", "dank je": "grazie", "hond": "cane", "kat": "gatto"},
            }

            woorden = basis_woorden.get(taal_nl, {})
            vertaling = tekst.lower()
            for nl, vertaald in woorden.items():
                vertaling = vertaling.replace(nl, vertaald)

            if vertaling == tekst.lower():
                vertaling = f"[Basis vertaling niet beschikbaar - ECHTE AI nodig voor: '{tekst}']"
            intel_bonus = 2

        print(f"\n  --- VERTALING ({taal_nl}) ---")
        print(f"  Origineel: {tekst}")
        print(f"  Vertaald:  {vertaling}")
        print("  " + "-" * 40)

        # Resultaten
        print("\n" + "=" * 55)
        print("  [TAAL] VERTALING VOLTOOID!")
        print("=" * 55)

        xp_beloning = 15
        munt_beloning = 5

        if echte_ai:
            munt_beloning += 8
            intel_bonus += 3
            print("  [STAR] ECHTE AI vertaling!")

        print(f"\n  {naam}'s vertaal sessie:")
        print(f"    [TAAL] Vertaald naar: {taal_nl}")
        print(f"    [IQ] Intelligentie: +{intel_bonus}")
        print(f"    [MUNT] Munten: +{munt_beloning}")
        print(f"    [XP] Ervaring: +{xp_beloning}")

        self.huisdier["munten"] += munt_beloning
        self.huisdier["ervaring"] += xp_beloning
        self.huisdier["intelligentie"] = self.huisdier.get("intelligentie", 0) + intel_bonus
        self.huisdier["geluk"] = min(100, self.huisdier["geluk"] + 3)

        print(f"\n  {geluid}")
        self._sla_op()

    def _ai_flashcards(self):
        """AI genereert flashcards voor het huisdier om te leren!"""
        if self.huisdier["munten"] < 12:
            print("\nJe hebt niet genoeg munten! (Nodig: 12)")
            return

        self.huisdier["munten"] -= 12
        self.huisdier["energie"] = max(0, self.huisdier["energie"] - 1)

        naam = self.huisdier["naam"]
        geluid = self.huisdier["geluid"]
        iq = self.huisdier.get("intelligentie", 0)

        print("\n" + "=" * 55)
        print(f"  [KAART] {naam} DE FLASHCARD STUDENT!")
        print("=" * 55)

        print("\n  Kies een onderwerp:")
        print("  1. Machine Learning")
        print("  2. Python Programming")
        print("  3. API Design")
        print("  4. Neural Networks")
        print("  5. Random onderwerp")

        keuze = input("\n  Keuze (1-5): ").strip()

        onderwerpen = {
            "1": "Machine Learning",
            "2": "Python Programming",
            "3": "API Design",
            "4": "Neural Networks",
            "5": random.choice(["Data Science", "Cybersecurity", "Cloud Computing", "DevOps"])
        }
        onderwerp = onderwerpen.get(keuze, "Machine Learning")

        print(f"\n  {naam} studeert {onderwerp} flashcards...")
        time.sleep(0.5)

        echte_ai = False
        intel_bonus = 0
        correct = 0
        totaal = 5

        try:
            claude_chat = _get_claude_chat()
            if claude_chat:
                echte_ai = True
                print(f"  [OK] ECHTE Claude AI genereert flashcards!")
        except Exception as e:
            logger.debug("Failed to connect to Claude AI for flashcards: %s", e)

        # Flashcards - AI of fallback
        fallback_cards = {
            "Machine Learning": [
                ("Wat is supervised learning?", "Leren met gelabelde data waar antwoorden bekend zijn"),
                ("Wat is overfitting?", "Model leert trainingsdata uit het hoofd en generaliseert slecht"),
                ("Wat is een neural network?", "Model geinspireerd op het brein met neuronen en lagen"),
                ("Wat is gradient descent?", "Algoritme dat parameters optimaliseert door gradients te volgen"),
                ("Wat is cross-validation?", "Data splitsen om model performance te valideren"),
            ],
            "Python Programming": [
                ("Wat doet @decorator?", "Wrapt een functie om functionaliteit toe te voegen"),
                ("Wat is een generator?", "Functie die yield gebruikt voor lazy evaluation"),
                ("Wat doet lru_cache?", "Slaat functie resultaten op voor snellere herhaalde calls"),
                ("Wat is een list comprehension?", "Compacte manier om lijsten te maken: [x for x in items]"),
                ("Wat is *args en **kwargs?", "Variabel aantal positional en keyword argumenten"),
            ],
            "API Design": [
                ("Wat is REST?", "Architectuurstijl met HTTP methods voor web APIs"),
                ("Wat doet GET?", "Haalt data op zonder wijzigingen"),
                ("Wat is HTTP 404?", "Resource niet gevonden"),
                ("Wat is JWT?", "JSON Web Token voor stateless authenticatie"),
                ("Wat is rate limiting?", "Maximaal aantal requests per tijdsperiode"),
            ],
            "Neural Networks": [
                ("Wat is backpropagation?", "Algoritme dat gradients terugpropageert om weights te leren"),
                ("Wat is ReLU?", "Activation: max(0, x) - voorkomt vanishing gradients"),
                ("Wat is een CNN?", "Convolutional Neural Network voor beeldherkenning"),
                ("Wat is dropout?", "Zet random neuronen uit tijdens training tegen overfitting"),
                ("Wat is attention?", "Mechanisme dat relevante input delen weegt"),
            ],
        }

        cards = fallback_cards.get(onderwerp, fallback_cards["Machine Learning"])

        for i, (vraag, antwoord) in enumerate(cards, 1):
            print(f"\n  --- Flashcard {i}/{totaal} ---")
            print(f"  VRAAG: {vraag}")
            user_antwoord = input("  Jouw antwoord: ").strip()

            print(f"  CORRECT ANTWOORD: {antwoord}")

            if user_antwoord.lower() and any(w in user_antwoord.lower() for w in antwoord.lower().split()[:3]):
                print(f"  [OK] Goed gedaan, {naam}!")
                correct += 1
                intel_bonus += 2
            else:
                print(f"  [LAMP] {naam} leert dit voor de volgende keer!")
                intel_bonus += 1

        # Resultaten
        percentage = int((correct / totaal) * 100)
        print("\n" + "=" * 55)
        print("  [KAART] FLASHCARD SESSIE VOLTOOID!")
        print("=" * 55)

        xp_beloning = 20 + (correct * 5)
        munt_beloning = 5 + (correct * 2)

        if echte_ai:
            munt_beloning += 8
            intel_bonus += 5

        print(f"\n  {naam}'s studieresultaat:")
        print(f"    [KAART] Onderwerp: {onderwerp}")
        print(f"    [OK] Correct: {correct}/{totaal} ({percentage}%)")
        print(f"    [IQ] Intelligentie: +{intel_bonus}")
        print(f"    [MUNT] Munten: +{munt_beloning}")
        print(f"    [XP] Ervaring: +{xp_beloning}")

        self.huisdier["munten"] += munt_beloning
        self.huisdier["ervaring"] += xp_beloning
        self.huisdier["intelligentie"] = self.huisdier.get("intelligentie", 0) + intel_bonus

        print(f"\n  {geluid}")
        self._sla_op()

    def _ai_notities(self):
        """AI helpt het huisdier slimme notities maken!"""
        if self.huisdier["munten"] < 8:
            print("\nJe hebt niet genoeg munten! (Nodig: 8)")
            return

        self.huisdier["munten"] -= 8

        naam = self.huisdier["naam"]
        geluid = self.huisdier["geluid"]

        print("\n" + "=" * 55)
        print(f"  [NOTITIE] {naam} DE SLIMME NOTITIE MAKER!")
        print("=" * 55)

        print("\n  Wat wil je noteren?")
        print("  1. Samenvatting van een onderwerp")
        print("  2. To-do lijst maken")
        print("  3. Brainstorm ideeen")
        print("  4. Leer notities")

        keuze = input("\n  Keuze (1-4): ").strip()
        tekst = input("  Beschrijf wat je wilt noteren: ").strip()

        if not tekst:
            print("  [!] Geen tekst ingevoerd!")
            return

        print(f"\n  {naam} maakt een slimme notitie...")
        time.sleep(0.5)

        notitie = None
        echte_ai = False
        intel_bonus = 3

        try:
            claude_chat = _get_claude_chat()
            if claude_chat:
                echte_ai = True
                types = {
                    "1": "Maak een korte samenvatting (max 3 bullet points) van:",
                    "2": "Maak een to-do lijst (max 5 items) voor:",
                    "3": "Brainstorm 3 creatieve ideeen voor:",
                    "4": "Maak leernotities (key points) over:"
                }
                prompt = f"{types.get(keuze, types['1'])}\n\n{tekst}"
                berichten = [{"role": "user", "content": prompt}]
                notitie = claude_chat._chat_conversatie(berichten, f"Je bent de notitie-assistent van {naam}. Wees beknopt.")
                intel_bonus = 8
        except Exception as e:
            logger.debug("AI note generation failed: %s", e)

        if not notitie:
            # Fallback
            notitie = f"[Notitie van {naam}]\n- {tekst}\n- (AI samenvatting niet beschikbaar)"

        print(f"\n  --- {naam}'s NOTITIE ---")
        print(f"  {notitie[:300]}{'...' if len(str(notitie)) > 300 else ''}")
        print("  " + "-" * 45)

        # Sla op in huisdier kennis
        if "notities" not in self.huisdier:
            self.huisdier["notities"] = []
        self.huisdier["notities"].append({
            "tekst": str(notitie)[:200],
            "datum": datetime.now().isoformat()
        })
        self.huisdier["notities"] = self.huisdier["notities"][-20:]  # Max 20

        xp_beloning = 15
        munt_beloning = 4

        if echte_ai:
            munt_beloning += 6
            print("  [STAR] ECHTE AI notitie!")

        print(f"\n  {naam} heeft de notitie opgeslagen!")
        print(f"    [IQ] Intelligentie: +{intel_bonus}")
        print(f"    [MUNT] Munten: +{munt_beloning}")
        print(f"    [XP] Ervaring: +{xp_beloning}")

        self.huisdier["munten"] += munt_beloning
        self.huisdier["ervaring"] += xp_beloning
        self.huisdier["intelligentie"] = self.huisdier.get("intelligentie", 0) + intel_bonus

        print(f"\n  {geluid}")
        self._sla_op()

    def _ai_citaten(self):
        """Huisdier leert van inspirerende citaten!"""
        if self.huisdier["munten"] < 5:
            print("\nJe hebt niet genoeg munten! (Nodig: 5)")
            return

        self.huisdier["munten"] -= 5

        naam = self.huisdier["naam"]
        geluid = self.huisdier["geluid"]

        print("\n" + "=" * 55)
        print(f"  [CITAAT] {naam} ZOEKT INSPIRATIE!")
        print("=" * 55)

        # Citaten uit de Citaten Generator
        citaten = [
            ("De enige manier om geweldig werk te doen is houden van wat je doet.", "Steve Jobs"),
            ("Succes is van falen naar falen gaan zonder enthousiasme te verliezen.", "Winston Churchill"),
            ("Geloof dat je het kunt en je bent al halverwege.", "Theodore Roosevelt"),
            ("In het midden van moeilijkheid ligt kans.", "Albert Einstein"),
            ("Je mist 100% van de schoten die je niet neemt.", "Wayne Gretzky"),
            ("Creativiteit is intelligentie die plezier heeft.", "Albert Einstein"),
            ("Elke expert was ooit een beginner.", "Helen Hayes"),
            ("Het geheim van vooruitgang is beginnen.", "Mark Twain"),
            ("Kansen komen niet, je creëert ze.", "Chris Grosser"),
            ("Eenvoud is de ultieme verfijning.", "Leonardo da Vinci"),
        ]

        # Toon 3 willekeurige citaten
        gekozen = random.sample(citaten, 3)
        intel_bonus = 0

        for i, (citaat, auteur) in enumerate(gekozen, 1):
            print(f"\n  --- Citaat {i}/3 ---")
            print(f"  \"{citaat}\"")
            print(f"    - {auteur}")
            time.sleep(0.5)

            # Vraag om reflectie
            reflectie = input(f"\n  Wat betekent dit voor {naam}? ").strip()
            if reflectie:
                intel_bonus += 3
                print(f"  [LAMP] {naam} reflecteert: \"{reflectie[:50]}...\"")
            else:
                intel_bonus += 1
                print(f"  [OK] {naam} onthoudt dit citaat!")

        # Resultaten
        print("\n" + "=" * 55)
        print("  [CITAAT] INSPIRATIE SESSIE VOLTOOID!")
        print("=" * 55)

        xp_beloning = 12
        munt_beloning = 3

        print(f"\n  {naam}'s inspiratie:")
        print(f"    [CITAAT] 3 citaten geleerd!")
        print(f"    [IQ] Intelligentie: +{intel_bonus}")
        print(f"    [MUNT] Munten: +{munt_beloning}")
        print(f"    [XP] Ervaring: +{xp_beloning}")

        self.huisdier["munten"] += munt_beloning
        self.huisdier["ervaring"] += xp_beloning
        self.huisdier["intelligentie"] = self.huisdier.get("intelligentie", 0) + intel_bonus
        self.huisdier["geluk"] = min(100, self.huisdier["geluk"] + 5)

        print(f"\n  {geluid}")
        self._sla_op()

    def _ai_code_review(self):
        """AI analyseert code en geeft feedback!"""
        if self.huisdier["munten"] < 15:
            print("\nJe hebt niet genoeg munten! (Nodig: 15)")
            return

        if self.huisdier["energie"] < 2:
            print(f"\n{self.huisdier['naam']} is te moe voor code review!")
            return

        self.huisdier["munten"] -= 15
        self.huisdier["energie"] = max(0, self.huisdier["energie"] - 2)

        naam = self.huisdier["naam"]
        geluid = self.huisdier["geluid"]

        print("\n" + "=" * 55)
        print(f"  [CODE] {naam} DE CODE REVIEWER!")
        print("=" * 55)

        print("\n  Plak je code (typ 'KLAAR' op een nieuwe regel als je klaar bent):")
        code_lines = []
        while True:
            line = input()
            if line.strip().upper() == "KLAAR":
                break
            code_lines.append(line)

        code = "\n".join(code_lines)

        if not code.strip():
            print("  [!] Geen code ingevoerd!")
            return

        print(f"\n  {naam} analyseert de code...")
        time.sleep(0.5)

        review = None
        echte_ai = False
        intel_bonus = 5

        try:
            claude_chat = _get_claude_chat()
            if claude_chat:
                echte_ai = True
                prompt = f"""Analyseer deze code kort (max 5 bullet points):
1. Wat doet de code?
2. Zijn er bugs of problemen?
3. Suggesties voor verbetering?

Code:
```
{code[:500]}
```"""
                berichten = [{"role": "user", "content": prompt}]
                review = claude_chat._chat_conversatie(berichten, f"Je bent {naam}'s code review mentor. Wees beknopt en educatief.")
                intel_bonus = 12
        except Exception as e:
            logger.debug("AI code review failed: %s", e)

        if not review:
            # Basis fallback analyse
            review_items = []
            if "def " in code:
                review_items.append("Functie definitie gevonden")
            if "class " in code:
                review_items.append("Class definitie gevonden")
            if "import " in code:
                review_items.append("Imports gevonden")
            if "for " in code or "while " in code:
                review_items.append("Loops gevonden")
            if not review_items:
                review_items.append("Code structuur geanalyseerd")
            review = "\n".join(f"- {item}" for item in review_items)
            review += "\n\n[Tip: Met ECHTE AI krijg je diepere analyse!]"

        print(f"\n  --- CODE REVIEW ---")
        print(f"  {review[:400]}{'...' if len(str(review)) > 400 else ''}")
        print("  " + "-" * 45)

        # Resultaten
        print("\n" + "=" * 55)
        print("  [CODE] CODE REVIEW VOLTOOID!")
        print("=" * 55)

        xp_beloning = 25
        munt_beloning = 8

        if echte_ai:
            munt_beloning += 10
            print("  [STAR] ECHTE AI code review!")

        print(f"\n  {naam}'s code review:")
        print(f"    [CODE] Regels geanalyseerd: {len(code_lines)}")
        print(f"    [IQ] Intelligentie: +{intel_bonus}")
        print(f"    [MUNT] Munten: +{munt_beloning}")
        print(f"    [XP] Ervaring: +{xp_beloning}")

        self.huisdier["munten"] += munt_beloning
        self.huisdier["ervaring"] += xp_beloning
        self.huisdier["intelligentie"] = self.huisdier.get("intelligentie", 0) + intel_bonus

        print(f"\n  {geluid}")
        self._sla_op()

    def _ai_production_rag(self):
        """Gebruik het ECHTE Production RAG systeem!"""
        if self.huisdier["munten"] < 20:
            print("\nJe hebt niet genoeg munten! (Nodig: 20)")
            return

        if self.huisdier["energie"] < 2:
            print(f"\n{self.huisdier['naam']} is te moe voor deep research!")
            return

        self.huisdier["munten"] -= 20
        self.huisdier["energie"] = max(0, self.huisdier["energie"] - 2)

        naam = self.huisdier["naam"]
        geluid = self.huisdier["geluid"]

        print("\n" + "=" * 55)
        print(f"  [RAG] {naam} GEBRUIKT PRODUCTION RAG!")
        print("=" * 55)

        vraag = input("\n  Stel een vraag aan de kennisbank: ").strip()

        if not vraag:
            print("  [!] Geen vraag ingevoerd!")
            return

        print(f"\n  {naam} doorzoekt de Production RAG kennisbank...")
        time.sleep(0.5)

        antwoord = None
        echte_rag = False
        intel_bonus = 5
        bronnen = []

        try:
            from ..ai.production_rag import ProductionRAG
            rag = ProductionRAG()
            # Check of er documenten zijn
            if hasattr(rag, 'chunks') and rag.chunks:
                echte_rag = True
                print(f"  [OK] Production RAG geladen met {len(rag.chunks)} chunks!")
                resultaat = rag.query(vraag)
                if resultaat:
                    antwoord = resultaat.get("antwoord", "")
                    bronnen = resultaat.get("bronnen", [])
                    intel_bonus = 15
        except Exception as e:
            print(f"  [!] RAG niet beschikbaar: {e}")

        if not antwoord:
            # Fallback naar ingebouwde kennis
            permanente_kennis = self._laad_permanente_kennis()
            relevant = [f for f in permanente_kennis["feiten"] if any(w in f.lower() for w in vraag.lower().split())]
            if relevant:
                antwoord = random.choice(relevant)
                intel_bonus = 8
            else:
                antwoord = "Geen direct antwoord gevonden. Probeer de kennisbank uit te breiden!"

        print(f"\n  --- RAG ANTWOORD ---")
        print(f"  Vraag: {vraag}")
        print(f"  Antwoord: {antwoord[:300]}{'...' if len(str(antwoord)) > 300 else ''}")
        if bronnen:
            print(f"  Bronnen: {', '.join(bronnen[:3])}")
        print("  " + "-" * 45)

        # Resultaten
        print("\n" + "=" * 55)
        print("  [RAG] KENNISBANK QUERY VOLTOOID!")
        print("=" * 55)

        xp_beloning = 30
        munt_beloning = 10

        if echte_rag:
            munt_beloning += 15
            print("  [STAR] ECHTE Production RAG gebruikt!")

        print(f"\n  {naam}'s research:")
        print(f"    [RAG] Query uitgevoerd!")
        print(f"    [IQ] Intelligentie: +{intel_bonus}")
        print(f"    [MUNT] Munten: +{munt_beloning}")
        print(f"    [XP] Ervaring: +{xp_beloning}")

        self.huisdier["munten"] += munt_beloning
        self.huisdier["ervaring"] += xp_beloning
        self.huisdier["intelligentie"] = self.huisdier.get("intelligentie", 0) + intel_bonus

        print(f"\n  {geluid}")
        self._sla_op()

    def _ai_brainstorm(self):
        """AI helpt creatief brainstormen!"""
        if self.huisdier["munten"] < 18:
            print("\nJe hebt niet genoeg munten! (Nodig: 18)")
            return

        if self.huisdier["energie"] < 2:
            print(f"\n{self.huisdier['naam']} is te moe om te brainstormen!")
            return

        self.huisdier["munten"] -= 18
        self.huisdier["energie"] = max(0, self.huisdier["energie"] - 2)

        naam = self.huisdier["naam"]
        geluid = self.huisdier["geluid"]

        print("\n" + "=" * 55)
        print(f"  [LAMP] {naam} DE CREATIEVE BRAINSTORMER!")
        print("=" * 55)

        print("\n  Wat wil je brainstormen?")
        print("  1. App ideeen")
        print("  2. Project namen")
        print("  3. Oplossingen voor een probleem")
        print("  4. Creatieve verhaal ideeen")
        print("  5. Business ideeen")

        keuze = input("\n  Keuze (1-5): ").strip()
        onderwerp = input("  Beschrijf je onderwerp/probleem: ").strip()

        if not onderwerp:
            print("  [!] Geen onderwerp ingevoerd!")
            return

        print(f"\n  {naam} brainstormt creatieve ideeen...")
        time.sleep(0.5)

        ideeen = []
        echte_ai = False
        intel_bonus = 5

        try:
            claude_chat = _get_claude_chat()
            if claude_chat:
                echte_ai = True
                types = {
                    "1": "app ideeen",
                    "2": "creatieve project namen",
                    "3": "oplossingen",
                    "4": "verhaal ideeen",
                    "5": "business ideeen"
                }
                prompt = f"Genereer 5 creatieve {types.get(keuze, 'ideeen')} voor: {onderwerp}\n\nGeef elk idee op een nieuwe regel met een korte beschrijving."
                berichten = [{"role": "user", "content": prompt}]
                response = claude_chat._chat_conversatie(berichten, f"Je bent {naam}'s creatieve brainstorm partner. Wees origineel en innovatief.")
                ideeen = [response]
                intel_bonus = 12
        except Exception as e:
            logger.debug("AI brainstorm generation failed: %s", e)

        if not ideeen or not ideeen[0]:
            # Fallback ideeen
            fallback = {
                "1": [f"Een {onderwerp} tracker app", f"Social {onderwerp} platform", f"AI-powered {onderwerp} helper"],
                "2": [f"{onderwerp}ify", f"Smart{onderwerp}", f"Project {onderwerp.title()}"],
                "3": [f"Automatiseer {onderwerp}", f"Deel {onderwerp} op in stappen", f"Zoek een expert voor {onderwerp}"],
                "4": [f"Een held ontdekt {onderwerp}", f"De mysterie van {onderwerp}", f"De toekomst van {onderwerp}"],
                "5": [f"{onderwerp} as a Service", f"{onderwerp} consultancy", f"Online {onderwerp} platform"],
            }
            ideeen = fallback.get(keuze, [f"Creatief idee voor {onderwerp}"])

        print(f"\n  --- BRAINSTORM RESULTATEN ---")
        if isinstance(ideeen[0], str) and len(ideeen[0]) > 50:
            print(f"  {ideeen[0][:400]}{'...' if len(ideeen[0]) > 400 else ''}")
        else:
            for i, idee in enumerate(ideeen[:5], 1):
                print(f"  {i}. {idee}")
        print("  " + "-" * 45)

        # Resultaten
        print("\n" + "=" * 55)
        print("  [LAMP] BRAINSTORM SESSIE VOLTOOID!")
        print("=" * 55)

        xp_beloning = 22
        munt_beloning = 7

        if echte_ai:
            munt_beloning += 12
            print("  [STAR] ECHTE AI brainstorm!")

        print(f"\n  {naam}'s creatieve sessie:")
        print(f"    [LAMP] Ideeen gegenereerd!")
        print(f"    [IQ] Intelligentie: +{intel_bonus}")
        print(f"    [MUNT] Munten: +{munt_beloning}")
        print(f"    [XP] Ervaring: +{xp_beloning}")

        self.huisdier["munten"] += munt_beloning
        self.huisdier["ervaring"] += xp_beloning
        self.huisdier["intelligentie"] = self.huisdier.get("intelligentie", 0) + intel_bonus
        self.huisdier["geluk"] = min(100, self.huisdier["geluk"] + 5)

        print(f"\n  {geluid}")
        self._sla_op()

    # ==================== PRODUCTIVITEIT INTEGRATIES ====================

    def _ai_mood_tracker(self):
        """Huisdier helpt met stemming tracken en AI analyse!"""
        if self.huisdier["munten"] < 10:
            print("\nJe hebt niet genoeg munten! (Nodig: 10)")
            return

        self.huisdier["munten"] -= 10

        naam = self.huisdier["naam"]
        geluid = self.huisdier["geluid"]
        emoji = self.huisdier["emoji"]

        print("\n" + "=" * 55)
        print(f"  {emoji} {naam} DE MOOD BUDDY!")
        print("=" * 55)
        print(f"\n  {naam} wil weten hoe je je voelt!")

        print("\n  Hoe voel je je nu?")
        print("  1. Geweldig! (5/5)")
        print("  2. Goed (4/5)")
        print("  3. Oké (3/5)")
        print("  4. Niet zo goed (2/5)")
        print("  5. Slecht (1/5)")

        keuze = input("\n  Keuze (1-5): ").strip()
        moods = {"1": 5, "2": 4, "3": 3, "4": 2, "5": 1}
        mood_score = moods.get(keuze, 3)

        notitie = input("  Waarom voel je je zo? ").strip()

        print(f"\n  {naam} registreert je stemming...")
        time.sleep(0.5)

        intel_bonus = 3
        geluk_bonus = 0
        ai_advies = None

        # Probeer echte Mood Tracker te gebruiken
        try:
            mood_tracker = _get_mood_tracker()
            if mood_tracker and mood_tracker.client:
                print(f"  [OK] ECHTE AI Mood Analyse!")
                # Gebruik AI voor advies
                prompt = f"""Iemand voelt zich {mood_score}/5. Notitie: "{notitie}"
Geef kort (2-3 zinnen) empathisch advies. Nederlands."""
                ai_advies = mood_tracker._ai_request(prompt, max_tokens=150)
                intel_bonus = 8
        except Exception as e:
            logger.debug("AI mood analysis failed: %s", e)

        # Huisdier reageert op basis van mood
        if mood_score >= 4:
            print(f"\n  {naam}: {geluid} Geweldig! Ik ben zo blij voor je!")
            geluk_bonus = 5
        elif mood_score == 3:
            print(f"\n  {naam}: {geluid} Oké dag? Laten we iets leuks doen!")
            geluk_bonus = 3
        else:
            print(f"\n  {naam}: {geluid} Ik ben hier voor je! *knuffelt*")
            geluk_bonus = 8  # Extra troost

        if ai_advies:
            print(f"\n  [AI Advies]: {ai_advies}")

        # Resultaten
        xp_beloning = 15
        munt_beloning = 5

        print("\n" + "=" * 55)
        print("  [HART] MOOD CHECK VOLTOOID!")
        print("=" * 55)
        print(f"\n  Stemming geregistreerd: {mood_score}/5")
        print(f"    [IQ] Emotionele intelligentie: +{intel_bonus}")
        print(f"    [HART] Geluk: +{geluk_bonus}")
        print(f"    [XP] Ervaring: +{xp_beloning}")

        self.huisdier["intelligentie"] = self.huisdier.get("intelligentie", 0) + intel_bonus
        self.huisdier["geluk"] = min(100, self.huisdier["geluk"] + geluk_bonus)
        self.huisdier["ervaring"] += xp_beloning

        self._ai_add_memory("mood", f"Baasje voelde zich {mood_score}/5: {notitie[:30]}")
        print(f"\n  {geluid}")
        self._sla_op()

    def _ai_habit_coach(self):
        """Huisdier wordt je persoonlijke AI habit coach!"""
        if self.huisdier["munten"] < 12:
            print("\nJe hebt niet genoeg munten! (Nodig: 12)")
            return

        self.huisdier["munten"] -= 12

        naam = self.huisdier["naam"]
        geluid = self.huisdier["geluid"]
        emoji = self.huisdier["emoji"]

        print("\n" + "=" * 55)
        print(f"  {emoji} {naam} DE HABIT COACH!")
        print("=" * 55)
        print(f"\n  {naam} helpt je goede gewoontes opbouwen!")

        print("\n  Wat wil je doen?")
        print("  1. Nieuwe gewoonte starten")
        print("  2. Motivatie voor een gewoonte")
        print("  3. AI tips voor discipline")

        keuze = input("\n  Keuze (1-3): ").strip()

        intel_bonus = 5
        ai_response = None

        if keuze == "1":
            gewoonte = input("  Welke gewoonte wil je starten? ").strip()
            if gewoonte:
                print(f"\n  {naam} denkt na over '{gewoonte}'...")
                time.sleep(0.5)

                try:
                    habit_tracker = _get_habit_tracker()
                    if habit_tracker and habit_tracker.client:
                        prompt = f"""Help iemand de gewoonte '{gewoonte}' te starten.
Geef 3 concrete tips om te beginnen. Kort en motiverend. Nederlands."""
                        ai_response = habit_tracker._ai_request(prompt, max_tokens=200)
                        intel_bonus = 10
                except Exception as e:
                    logger.debug("Habit tracker AI request failed (start habit): %s", e)

                if not ai_response:
                    ai_response = f"Tips voor '{gewoonte}':\n1. Begin klein\n2. Koppel aan bestaande routine\n3. Beloon jezelf na elke keer"

        elif keuze == "2":
            gewoonte = input("  Welke gewoonte vind je moeilijk? ").strip()
            if gewoonte:
                try:
                    habit_tracker = _get_habit_tracker()
                    if habit_tracker and habit_tracker.client:
                        prompt = f"""Geef een korte, krachtige motivatie boodschap voor iemand die moeite heeft met de gewoonte '{gewoonte}'. 2-3 zinnen. Nederlands."""
                        ai_response = habit_tracker._ai_request(prompt, max_tokens=100)
                        intel_bonus = 8
                except Exception as e:
                    logger.debug("Habit tracker AI request failed (motivation): %s", e)

                if not ai_response:
                    ai_response = f"Elke dag dat je '{gewoonte}' doet, word je sterker. Je hebt dit!"

        else:
            try:
                habit_tracker = _get_habit_tracker()
                if habit_tracker and habit_tracker.client:
                    prompt = "Geef 5 praktische tips voor meer discipline bij het opbouwen van gewoontes. Nederlands, kort."
                    ai_response = habit_tracker._ai_request(prompt, max_tokens=250)
                    intel_bonus = 10
            except Exception as e:
                logger.debug("Habit tracker AI request failed (discipline tips): %s", e)

            if not ai_response:
                ai_response = "Discipline tips:\n1. Plan vooruit\n2. Maak het makkelijk\n3. Track je voortgang\n4. Wees geduldig\n5. Vier kleine overwinningen"

        print(f"\n  [COACH] {naam}'s advies:")
        print(f"  {ai_response}")

        # Resultaten
        xp_beloning = 18
        munt_beloning = 6

        print("\n" + "=" * 55)
        print("  [COACH] HABIT COACHING VOLTOOID!")
        print("=" * 55)
        print(f"    [IQ] Intelligentie: +{intel_bonus}")
        print(f"    [MUNT] Munten: +{munt_beloning}")
        print(f"    [XP] Ervaring: +{xp_beloning}")

        self.huisdier["munten"] += munt_beloning
        self.huisdier["ervaring"] += xp_beloning
        self.huisdier["intelligentie"] = self.huisdier.get("intelligentie", 0) + intel_bonus

        print(f"\n  {geluid}")
        self._sla_op()

    def _ai_budget_advisor(self):
        """Huisdier geeft AI-powered budget en spaartips!"""
        if self.huisdier["munten"] < 15:
            print("\nJe hebt niet genoeg munten! (Nodig: 15)")
            return

        self.huisdier["munten"] -= 15

        naam = self.huisdier["naam"]
        geluid = self.huisdier["geluid"]
        emoji = self.huisdier["emoji"]

        print("\n" + "=" * 55)
        print(f"  {emoji} {naam} DE BUDGET ADVISOR!")
        print("=" * 55)
        print(f"\n  {naam} helpt je slim met geld omgaan!")

        print("\n  Wat wil je weten?")
        print("  1. Algemene spaartips")
        print("  2. Budget advies voor een categorie")
        print("  3. Tips voor een specifiek doel")

        keuze = input("\n  Keuze (1-3): ").strip()

        intel_bonus = 5
        ai_response = None

        if keuze == "2":
            categorie = input("  Categorie (bv. boodschappen, entertainment): ").strip()
            if categorie:
                try:
                    expense_tracker = _get_expense_tracker()
                    if expense_tracker and expense_tracker.client:
                        prompt = f"""Geef 4 praktische bespaartips voor de categorie '{categorie}'. Concreet en direct toepasbaar. Nederlands."""
                        ai_response = expense_tracker._ai_request(prompt, max_tokens=200)
                        intel_bonus = 10
                except Exception as e:
                    logger.debug("Expense tracker AI request failed (savings tips): %s", e)

                if not ai_response:
                    ai_response = f"Tips voor {categorie}:\n1. Maak een budget\n2. Vergelijk prijzen\n3. Wacht 24 uur voor grote aankopen\n4. Zoek alternatieven"

        elif keuze == "3":
            doel = input("  Waar spaar je voor? ").strip()
            if doel:
                try:
                    expense_tracker = _get_expense_tracker()
                    if expense_tracker and expense_tracker.client:
                        prompt = f"""Iemand wil sparen voor '{doel}'. Geef een motiverend en praktisch spaarplan in 3-4 punten. Nederlands."""
                        ai_response = expense_tracker._ai_request(prompt, max_tokens=200)
                        intel_bonus = 12
                except Exception as e:
                    logger.debug("Expense tracker AI request failed (savings plan): %s", e)

                if not ai_response:
                    ai_response = f"Spaarplan voor {doel}:\n1. Bepaal het benodigde bedrag\n2. Stel een deadline\n3. Automatiseer je sparen\n4. Track je voortgang"

        else:
            try:
                expense_tracker = _get_expense_tracker()
                if expense_tracker and expense_tracker.client:
                    prompt = "Geef 5 slimme, praktische spaartips die direct toepasbaar zijn. Nederlands, kort en bondig."
                    ai_response = expense_tracker._ai_request(prompt, max_tokens=250)
                    intel_bonus = 8
            except Exception as e:
                logger.debug("Expense tracker AI request failed (general tips): %s", e)

            if not ai_response:
                ai_response = "Spaartips:\n1. Betaal jezelf eerst\n2. Track al je uitgaven\n3. Maak onderscheid tussen wensen en behoeften\n4. Zoek gratis alternatieven\n5. Meal prep in plaats van afhaal"

        print(f"\n  [MUNT] {naam}'s financiele wijsheid:")
        print(f"  {ai_response}")

        # Resultaten
        xp_beloning = 20
        munt_beloning = 10  # Ironisch: je verdient munten door over geld te leren!

        print("\n" + "=" * 55)
        print("  [MUNT] BUDGET ADVIES VOLTOOID!")
        print("=" * 55)
        print(f"    [IQ] Financiele intelligentie: +{intel_bonus}")
        print(f"    [MUNT] Munten: +{munt_beloning}")
        print(f"    [XP] Ervaring: +{xp_beloning}")

        self.huisdier["munten"] += munt_beloning
        self.huisdier["ervaring"] += xp_beloning
        self.huisdier["intelligentie"] = self.huisdier.get("intelligentie", 0) + intel_bonus

        print(f"\n  {geluid}")
        self._sla_op()

    def _ai_dag_planner(self):
        """Huisdier helpt je dag plannen met AI!"""
        if self.huisdier["munten"] < 12:
            print("\nJe hebt niet genoeg munten! (Nodig: 12)")
            return

        self.huisdier["munten"] -= 12

        naam = self.huisdier["naam"]
        geluid = self.huisdier["geluid"]
        emoji = self.huisdier["emoji"]

        print("\n" + "=" * 55)
        print(f"  {emoji} {naam} DE DAG PLANNER!")
        print("=" * 55)
        print(f"\n  {naam} helpt je productief te zijn!")

        print("\n  Wat wil je plannen?")
        print("  1. Mijn dag optimaliseren")
        print("  2. Prioriteiten stellen")
        print("  3. Productiviteit tips")

        keuze = input("\n  Keuze (1-3): ").strip()

        intel_bonus = 5
        ai_response = None

        if keuze == "1":
            taken = input("  Wat moet je vandaag doen? (komma-gescheiden): ").strip()
            if taken:
                try:
                    agenda = _get_agenda_planner()
                    if agenda and agenda.client:
                        prompt = f"""Help met dagplanning voor deze taken: {taken}

Geef een optimale volgorde en timing suggesties. Kort en praktisch. Nederlands."""
                        ai_response = agenda._ai_request(prompt, max_tokens=250)
                        intel_bonus = 12
                except Exception as e:
                    logger.debug("Agenda planner AI request failed (day planning): %s", e)

                if not ai_response:
                    taken_list = taken.split(",")
                    ai_response = "Aanbevolen volgorde:\n"
                    for i, taak in enumerate(taken_list[:5], 1):
                        ai_response += f"{i}. {taak.strip()}\n"
                    ai_response += "\nTip: Begin met de moeilijkste taak!"

        elif keuze == "2":
            taken = input("  Welke taken moet je prioriteren? ").strip()
            if taken:
                try:
                    agenda = _get_agenda_planner()
                    if agenda and agenda.client:
                        prompt = f"""Help prioriteiten stellen voor: {taken}

Geef een ranking op urgentie/belang met korte uitleg. Nederlands."""
                        ai_response = agenda._ai_request(prompt, max_tokens=200)
                        intel_bonus = 10
                except Exception as e:
                    logger.debug("Agenda planner AI request failed (prioritization): %s", e)

                if not ai_response:
                    ai_response = "Prioriteer op basis van:\n1. Deadlines (urgent eerst)\n2. Impact (belangrijk eerst)\n3. Afhankelijkheden (blokkerende taken eerst)"

        else:
            try:
                agenda = _get_agenda_planner()
                if agenda and agenda.client:
                    prompt = "Geef 5 concrete productiviteit tips voor een effectieve werkdag. Nederlands, praktisch."
                    ai_response = agenda._ai_request(prompt, max_tokens=250)
                    intel_bonus = 8
            except Exception as e:
                logger.debug("Agenda planner AI request failed (productivity tips): %s", e)

            if not ai_response:
                ai_response = "Productiviteit tips:\n1. Plan je dag de avond ervoor\n2. Doe eerst je moeilijkste taak\n3. Werk in blokken van 25-50 min\n4. Neem regelmatig pauzes\n5. Elimineer afleidingen"

        print(f"\n  [KALENDER] {naam}'s planning advies:")
        print(f"  {ai_response}")

        # Resultaten
        xp_beloning = 18
        munt_beloning = 6

        print("\n" + "=" * 55)
        print("  [KALENDER] PLANNING VOLTOOID!")
        print("=" * 55)
        print(f"    [IQ] Planning intelligentie: +{intel_bonus}")
        print(f"    [MUNT] Munten: +{munt_beloning}")
        print(f"    [XP] Ervaring: +{xp_beloning}")

        self.huisdier["munten"] += munt_beloning
        self.huisdier["ervaring"] += xp_beloning
        self.huisdier["intelligentie"] = self.huisdier.get("intelligentie", 0) + intel_bonus

        print(f"\n  {geluid}")
        self._sla_op()

    def _ai_focus_timer(self):
        """Huisdier geeft AI focus tips en motivatie!"""
        if self.huisdier["munten"] < 8:
            print("\nJe hebt niet genoeg munten! (Nodig: 8)")
            return

        self.huisdier["munten"] -= 8

        naam = self.huisdier["naam"]
        geluid = self.huisdier["geluid"]
        emoji = self.huisdier["emoji"]

        print("\n" + "=" * 55)
        print(f"  {emoji} {naam} DE FOCUS MASTER!")
        print("=" * 55)
        print(f"\n  {naam} helpt je geconcentreerd te blijven!")

        print("\n  Wat heb je nodig?")
        print("  1. Focus tips voor nu")
        print("  2. Motivatie boost")
        print("  3. Anti-afleiding advies")

        keuze = input("\n  Keuze (1-3): ").strip()

        intel_bonus = 4
        geluk_bonus = 3
        ai_response = None

        if keuze == "1":
            taak = input("  Waar moet je op focussen? ").strip()
            try:
                pomodoro = _get_pomodoro_timer()
                if pomodoro and pomodoro.client:
                    prompt = f"""Geef 3 concrete focus tips voor iemand die moet werken aan: '{taak}'
Kort, praktisch, direct toepasbaar. Nederlands."""
                    ai_response = pomodoro._ai_request(prompt, max_tokens=150)
                    intel_bonus = 8
            except Exception as e:
                logger.debug("Pomodoro AI request failed (focus tips): %s", e)

            if not ai_response:
                ai_response = f"Focus tips voor {taak if taak else 'je taak'}:\n1. Zet je telefoon weg\n2. Werk in 25-min blokken\n3. Maak je bureau leeg"

        elif keuze == "2":
            try:
                pomodoro = _get_pomodoro_timer()
                if pomodoro and pomodoro.client:
                    prompt = "Geef een korte, krachtige motivatie boodschap om iemand aan te moedigen door te zetten met hun werk. 2-3 zinnen, energiek. Nederlands."
                    ai_response = pomodoro._ai_request(prompt, max_tokens=100)
                    intel_bonus = 6
                    geluk_bonus = 5
            except Exception as e:
                logger.debug("Pomodoro AI request failed (motivation): %s", e)

            if not ai_response:
                ai_response = "Je bent verder dan je denkt! Elke minuut focus brengt je dichter bij je doel. Jij kan dit!"

        else:
            try:
                pomodoro = _get_pomodoro_timer()
                if pomodoro and pomodoro.client:
                    prompt = "Geef 4 praktische tips om afleidingen te minimaliseren tijdens het werken. Nederlands, direct toepasbaar."
                    ai_response = pomodoro._ai_request(prompt, max_tokens=200)
                    intel_bonus = 7
            except Exception as e:
                logger.debug("Pomodoro AI request failed (distraction tips): %s", e)

            if not ai_response:
                ai_response = "Anti-afleiding tips:\n1. Notificaties uit\n2. Werk in een opgeruimde ruimte\n3. Gebruik website blockers\n4. Communiceer je focus-tijd"

        print(f"\n  [FOCUS] {naam}'s focus wijsheid:")
        print(f"  {ai_response}")

        # Mini focus oefening
        print(f"\n  {naam}: Laten we een korte focus oefening doen!")
        print("  Sluit je ogen, adem 3x diep in en uit...")
        input("  [Druk Enter als je klaar bent]")
        print(f"  {naam}: {geluid} Goed gedaan! Je bent nu klaar om te focussen!")
        geluk_bonus += 2

        # Resultaten
        xp_beloning = 12
        munt_beloning = 4

        print("\n" + "=" * 55)
        print("  [FOCUS] FOCUS SESSIE VOLTOOID!")
        print("=" * 55)
        print(f"    [IQ] Focus intelligentie: +{intel_bonus}")
        print(f"    [HART] Geluk: +{geluk_bonus}")
        print(f"    [MUNT] Munten: +{munt_beloning}")
        print(f"    [XP] Ervaring: +{xp_beloning}")

        self.huisdier["munten"] += munt_beloning
        self.huisdier["ervaring"] += xp_beloning
        self.huisdier["intelligentie"] = self.huisdier.get("intelligentie", 0) + intel_bonus
        self.huisdier["geluk"] = min(100, self.huisdier["geluk"] + geluk_bonus)

        print(f"\n  {geluid}")
        self._sla_op()

    def _tricks_menu(self):
        """Tricks menu met CONDITIONERING systeem - leren door beloning!"""
        while True:
            geleerde = self.huisdier["tricks_geleerd"]
            training = self.huisdier.get("tricks_training", {})
            iq = self.huisdier.get("intelligentie", 0)

            print("\n" + "=" * 55)
            print("  [TRICKS] CONDITIONERING TRAINING")
            print("  Dieren leren door beloning en herhaling!")
            print("=" * 55)

            # Toon tricks in training
            in_training = []
            beschikbaar = []

            for trick_id, trick in self.TRICKS.items():
                if trick_id in geleerde:
                    continue
                elif trick_id in training:
                    in_training.append((trick_id, trick, training[trick_id]))
                else:
                    beschikbaar.append((trick_id, trick))

            if in_training:
                print("\n  [TRAINING] In opleiding:")
                for i, (tid, trick, prog) in enumerate(in_training, 1):
                    voortgang = prog.get("bekrachtiging", 0)
                    nodig = trick["bekrachtiging_nodig"]
                    pct = int((voortgang / nodig) * 100)
                    balk = "#" * (pct // 10) + "." * (10 - pct // 10)
                    print(f"  T{i}. {trick['naam']:<15} [{balk}] {pct}%")
                    print(f"      Sessies: {prog.get('pogingen', 0)} | "
                          f"Succes: {prog.get('successen', 0)}")

            if beschikbaar:
                print("\n  [NIEUW] Start training:")
                for i, (tid, trick) in enumerate(beschikbaar, 1):
                    print(f"  N{i}. {trick['naam']:<15} "
                          f"(Niveau: {trick['moeilijkheid']}, "
                          f"Nodig: {trick['bekrachtiging_nodig']}x)")

            if geleerde:
                print("\n  [GELEERD] Uitvoeren:")
                for i, trick_id in enumerate(geleerde, 1):
                    trick = self.TRICKS[trick_id]
                    perf = training.get(trick_id, {}).get("perfectie", 50)
                    print(f"  {i}. {trick['naam']:<15} "
                          f"(Perfectie: {perf}%, +{trick['beloning']} munten)")

            print("\n  [INFO] IQ bonus: +{} leersnelheid".format(iq // 20))
            print("  0. Terug")
            print("=" * 55)

            keuze = input("\nKeuze: ").strip().lower()

            if keuze == "0":
                break
            elif keuze.startswith("t") and len(keuze) > 1:
                try:
                    idx = int(keuze[1:]) - 1
                    if 0 <= idx < len(in_training):
                        self._train_trick(in_training[idx][0])
                except (ValueError, IndexError):
                    pass
            elif keuze.startswith("n") and len(keuze) > 1:
                try:
                    idx = int(keuze[1:]) - 1
                    if 0 <= idx < len(beschikbaar):
                        self._start_trick_training(beschikbaar[idx][0])
                except (ValueError, IndexError):
                    pass
            else:
                try:
                    idx = int(keuze) - 1
                    if 0 <= idx < len(geleerde):
                        self._voer_trick_uit(geleerde[idx])
                except (ValueError, IndexError):
                    pass

            input("\nDruk op Enter...")

    def _start_trick_training(self, trick_id: str):
        """Start training voor een nieuwe trick."""
        trick = self.TRICKS[trick_id]
        kosten = trick["moeilijkheid"] * 5  # Lagere kosten om te starten

        if self.huisdier["munten"] < kosten:
            print(f"\nJe hebt niet genoeg munten om te starten! (Nodig: {kosten})")
            return

        self.huisdier["munten"] -= kosten
        naam = self.huisdier["naam"]

        print(f"\n" + "=" * 50)
        print(f"  [START] {naam} begint '{trick['naam']}' te leren!")
        print("=" * 50)

        # Init training data
        if "tricks_training" not in self.huisdier:
            self.huisdier["tricks_training"] = {}

        self.huisdier["tricks_training"][trick_id] = {
            "pogingen": 0,
            "successen": 0,
            "bekrachtiging": 0,
            "perfectie": 50,
            "laatste_beloning": None,
            "motivatie": 100,
            "gestart": datetime.now().isoformat()
        }

        print(f"\n  [AI] Conditionering principe:")
        print(f"  - Train {trick['bekrachtiging_nodig']}x succesvol")
        print(f"  - Beloning type: {trick['beloning_type']}")
        print(f"  - Basis slaagkans: {trick['basis_kans']}%")
        print(f"\n  Tip: Hogere IQ = sneller leren!")

        self._sla_op()

    def _train_trick(self, trick_id: str):
        """Train een trick met CONDITIONERING - beloning en bestraffing."""
        trick = self.TRICKS[trick_id]
        training = self.huisdier["tricks_training"].get(trick_id, {})
        naam = self.huisdier["naam"]
        iq = self.huisdier.get("intelligentie", 0)
        kosten = 3  # Kleine kosten per sessie

        if self.huisdier["munten"] < kosten:
            print(f"\nJe hebt niet genoeg munten! (Nodig: {kosten})")
            return

        if self.huisdier["energie"] < 2:
            print(f"\n{naam} is te moe om te trainen!")
            return

        motivatie = training.get("motivatie", 100)
        if motivatie < 20:
            print(f"\n{naam} is gedemotiveerd! Geef eerst aandacht of voedsel.")
            print("  Tip: Knuffelen of voeren herstelt motivatie.")
            return

        self.huisdier["munten"] -= kosten
        self.huisdier["energie"] = max(0, self.huisdier["energie"] - 1)

        print(f"\n" + "=" * 50)
        print(f"  [TRAINING] {naam} oefent '{trick['naam']}'")
        print("=" * 50)
        time.sleep(0.5)

        # Bereken slaagkans met conditionering factoren
        basis_kans = trick["basis_kans"]
        bekrachtiging = training.get("bekrachtiging", 0)
        successen = training.get("successen", 0)
        pogingen = training.get("pogingen", 0)

        # Bonussen
        iq_bonus = iq // 5  # +1% per 5 IQ
        bekrachtiging_bonus = bekrachtiging * 3  # Eerder succes helpt
        motivatie_bonus = (motivatie - 50) // 5  # Hoge motivatie helpt
        geluk_bonus = (self.huisdier["geluk"] - 50) // 10

        totaal_kans = min(95, basis_kans + iq_bonus + bekrachtiging_bonus +
                         motivatie_bonus + geluk_bonus)

        print(f"\n  Slaagkans: {totaal_kans}%")
        print(f"    Basis: {basis_kans}%")
        if iq_bonus > 0:
            print(f"    IQ bonus: +{iq_bonus}%")
        if bekrachtiging_bonus > 0:
            print(f"    Bekrachtiging: +{bekrachtiging_bonus}%")
        if motivatie_bonus != 0:
            print(f"    Motivatie: {'+' if motivatie_bonus > 0 else ''}{motivatie_bonus}%")

        time.sleep(0.5)
        print(f"\n  {naam} probeert de trick...")
        time.sleep(0.8)

        # Update pogingen
        training["pogingen"] = pogingen + 1

        # Check succes
        if random.randint(1, 100) <= totaal_kans:
            # SUCCES - Positieve bekrachtiging!
            training["successen"] = successen + 1
            training["bekrachtiging"] = bekrachtiging + 1

            # Kies beloning type
            beloning_type = trick["beloning_type"]
            if beloning_type == "voedsel":
                print(f"\n  [OK] GOED ZO! {naam} krijgt een snoepje!")
                self.huisdier["honger"] = min(100, self.huisdier["honger"] + 5)
            elif beloning_type == "aandacht":
                print(f"\n  [OK] GOED ZO! {naam} krijgt een aai over de bol!")
                self.huisdier["geluk"] = min(100, self.huisdier["geluk"] + 5)
            else:  # spel
                print(f"\n  [OK] GOED ZO! {naam} mag even spelen!")
                self.huisdier["geluk"] = min(100, self.huisdier["geluk"] + 3)

            # Verhoog motivatie en perfectie
            training["motivatie"] = min(100, training.get("motivatie", 100) + 10)
            training["perfectie"] = min(100, training.get("perfectie", 50) + 2)
            training["laatste_beloning"] = datetime.now().isoformat()

            # Leer over conditionering
            if random.randint(1, 100) <= 30:
                les = "Positieve bekrachtiging versterkt gewenst gedrag"
                print(f"\n  [LAMP] {naam} leert: \"{les}\"")
                self.huisdier["intelligentie"] = iq + 1

            # Check of trick geleerd is
            nodig = trick["bekrachtiging_nodig"]
            print(f"\n  Voortgang: {training['bekrachtiging']}/{nodig}")

            if training["bekrachtiging"] >= nodig:
                self._trick_geleerd(trick_id, trick)
                self._log_memory_event("pet_trained", {
                    "resultaat": trick["naam"]
                })
        else:
            # MISLUKT - Geen straf, maar minder motivatie
            print(f"\n  [X] {naam} deed het niet goed...")
            print(f"  Geen straf - we proberen het opnieuw!")

            # Kleine motivatie daling (niet te streng!)
            training["motivatie"] = max(10, training.get("motivatie", 100) - 5)

            # Toch een klein beetje leren van fouten
            if random.randint(1, 100) <= 20:
                training["bekrachtiging"] = max(0, bekrachtiging + 0.5)
                print(f"  [TIP] {naam} leerde iets van de poging!")

            # AI uitleg
            if random.randint(1, 100) <= 25:
                print(f"\n  [AI] Bij conditionering:")
                print(f"  - Beloon goed gedrag (positieve bekrachtiging)")
                print(f"  - Negeer fout gedrag (geen straf nodig)")
                print(f"  - Herhaling versterkt de connectie")

        # Update stats
        if "tricks_training_sessies" not in self.huisdier["stats"]:
            self.huisdier["stats"]["tricks_training_sessies"] = 0
        self.huisdier["stats"]["tricks_training_sessies"] += 1

        self.huisdier["tricks_training"][trick_id] = training
        self.huisdier["ervaring"] += 5
        self._sla_op()

    def _trick_geleerd(self, trick_id: str, trick: dict):
        """Trick is volledig geleerd door conditionering!"""
        naam = self.huisdier["naam"]
        training = self.huisdier["tricks_training"].get(trick_id, {})

        print("\n" + "=" * 50)
        print(f"  [TROFEE] {naam} HEEFT '{trick['naam'].upper()}' GELEERD!")
        print("=" * 50)
        time.sleep(0.5)

        self.huisdier["tricks_geleerd"].append(trick_id)

        # Statistieken
        pogingen = training.get("pogingen", 0)
        successen = training.get("successen", 0)
        succes_rate = int((successen / max(1, pogingen)) * 100)

        print(f"\n  [STATS] Training voltooid:")
        print(f"    Totaal sessies: {pogingen}")
        print(f"    Succesvolle sessies: {successen}")
        print(f"    Succes rate: {succes_rate}%")

        # Bonus beloningen
        munt_bonus = trick["moeilijkheid"] * 15
        xp_bonus = trick["moeilijkheid"] * 20
        intel_bonus = trick["moeilijkheid"]

        self.huisdier["munten"] += munt_bonus
        self.huisdier["ervaring"] += xp_bonus
        self.huisdier["intelligentie"] = self.huisdier.get("intelligentie", 0) + intel_bonus
        self.huisdier["geluk"] = min(100, self.huisdier["geluk"] + 15)

        print(f"\n  [BONUS] Beloningen:")
        print(f"    +{munt_bonus} munten")
        print(f"    +{xp_bonus} ervaring")
        print(f"    +{intel_bonus} IQ")

        # AI uitleg
        print(f"\n  [AI] Conditionering succesvol!")
        print(f"  Door herhaalde positieve bekrachtiging")
        print(f"  heeft {naam} de associatie geleerd tussen")
        print(f"  het commando en de actie.")

        # Achievements
        if len(self.huisdier["tricks_geleerd"]) == 1:
            self._unlock_achievement("eerste_trick")
        if len(self.huisdier["tricks_geleerd"]) == len(self.TRICKS):
            self._unlock_achievement("alle_tricks")

    def _voer_trick_uit(self, trick_id: str):
        """Voer een geleerde trick uit - perfectie verbetert met oefening!"""
        trick = self.TRICKS[trick_id]
        training = self.huisdier.get("tricks_training", {}).get(trick_id, {})
        naam = self.huisdier["naam"]

        perfectie = training.get("perfectie", 50)

        print(f"\n  {naam} voert '{trick['naam']}' uit...")
        time.sleep(0.5)

        # Perfectie bepaalt kwaliteit
        if random.randint(1, 100) <= perfectie:
            # Perfect uitgevoerd
            bonus_mult = 1 + (perfectie - 50) / 100  # Tot 50% extra
            beloning = int(trick["beloning"] * bonus_mult)

            reacties_goed = [
                f"[PERFECT] {naam} doet het feilloos!",
                f"Wow! {naam} is een ster!",
                f"Meesterlijk! {self.huisdier['geluid']}",
            ]
            print(random.choice(reacties_goed))

            # Verhoog perfectie
            if trick_id in self.huisdier.get("tricks_training", {}):
                self.huisdier["tricks_training"][trick_id]["perfectie"] = min(100, perfectie + 1)
        else:
            # Niet perfect
            beloning = trick["beloning"] // 2

            reacties_ok = [
                f"[OK] {naam} probeert het... bijna goed!",
                f"{naam} doet een poging.",
            ]
            print(random.choice(reacties_ok))

        self.huisdier["geluk"] = min(100, self.huisdier["geluk"] + trick["geluk_bonus"])
        self.huisdier["stats"]["tricks_uitgevoerd"] += 1
        self.huisdier["munten"] += beloning
        self.huisdier["ervaring"] += trick["moeilijkheid"] * 3

        print(f"  +{beloning} munten! (Perfectie: {perfectie}%)")

    def _winkel(self):
        """Accessoires winkel."""
        while True:
            print("\n+================================+")
            print("|         WINKEL                 |")
            print(f"|    Jouw munten: {self.huisdier['munten']:<14}|")
            print("+================================+")

            beschikbaar = []
            for acc_id, acc in self.ACCESSOIRES.items():
                if acc_id not in self.huisdier["accessoires"]:
                    beschikbaar.append((acc_id, acc))
                    print(f"|  {len(beschikbaar)}. {acc['naam']:<15} "
                          f"{acc['prijs']:>4} munten |")
                    print(f"|     ({acc['effect']} +{acc['bonus']})")

            if not beschikbaar:
                print("|  Je hebt alles al!             |")

            print("|  0. Terug                      |")
            print("+================================+")

            keuze = input("\nWat wil je kopen? ").strip()

            if keuze == "0":
                break

            try:
                idx = int(keuze) - 1
                if 0 <= idx < len(beschikbaar):
                    acc_id, acc = beschikbaar[idx]

                    if self.huisdier["munten"] >= acc["prijs"]:
                        self.huisdier["munten"] -= acc["prijs"]
                        self.huisdier["accessoires"].append(acc_id)
                        print(f"\n[BONUS] Je hebt '{acc['naam']}' gekocht!")

                        if len(self.huisdier["accessoires"]) == 1:
                            self._unlock_achievement("eerste_accessoire")
                        if len(self.huisdier["accessoires"]) == len(self.ACCESSOIRES):
                            self._unlock_achievement("alle_accessoires")
                    else:
                        print("\nJe hebt niet genoeg munten!")
            except (ValueError, IndexError):
                pass

            input("\nDruk op Enter...")

    def _achievements_bekijken(self):
        """Bekijk achievements."""
        print("\n+================================+")
        print("|       ACHIEVEMENTS             |")
        print("+================================+")

        totaal_punten = 0
        unlocked = 0

        for ach_id, ach in self.ACHIEVEMENTS.items():
            if ach_id in self.huisdier["achievements"]:
                print(f"| ✓ {ach['naam']:<20} +{ach['punten']:>3} |")
                totaal_punten += ach["punten"]
                unlocked += 1
            else:
                print(f"| ? {ach['naam']:<20}  ???  |")

        print("+================================+")
        print(f"| Unlocked: {unlocked}/{len(self.ACHIEVEMENTS):<18}|")
        print(f"| Totaal punten: {totaal_punten:<13}|")
        print("+================================+")

    def _dagelijkse_bonus(self):
        """Claim dagelijkse bonus."""
        bonus_data = self.huisdier["dagelijkse_bonus"]
        nu = datetime.now().date()

        if bonus_data["laatste_claim"]:
            laatste = datetime.fromisoformat(bonus_data["laatste_claim"]).date()

            if laatste == nu:
                print("\nJe hebt de dagelijkse bonus al geclaimd!")
                print(f"Huidige streak: {bonus_data['streak']} dagen")
                return

            if laatste == nu - timedelta(days=1):
                bonus_data["streak"] += 1
            else:
                bonus_data["streak"] = 1
        else:
            bonus_data["streak"] = 1

        bonus_data["laatste_claim"] = nu.isoformat()

        # Bereken bonus
        basis_bonus = 20
        streak_bonus = min(bonus_data["streak"] * 5, 50)
        totaal = basis_bonus + streak_bonus

        self.huisdier["munten"] += totaal
        self.huisdier["stats"]["dagen_gespeeld"] += 1

        print(f"\n[BONUS] DAGELIJKSE BONUS!")
        print(f"   Basis: +{basis_bonus} munten")
        print(f"   Streak ({bonus_data['streak']} dagen): +{streak_bonus} munten")
        print(f"   Totaal: +{totaal} munten!")

        # Achievement checks
        if bonus_data["streak"] >= 7:
            self._unlock_achievement("dagelijkse_bonus")

        # Leeftijd achievements
        if self.huisdier["leeftijd_dagen"] >= 7:
            self._unlock_achievement("week_oud")
        if self.huisdier["leeftijd_dagen"] >= 30:
            self._unlock_achievement("maand_oud")

    # ==========================================
    # NIEUWE AVONTUREN FEATURES
    # ==========================================

    def _get_seizoen_event(self):
        """Bepaal huidig seizoens event op basis van datum."""
        nu = datetime.now()
        maand = nu.month
        dag = nu.day

        events = {
            # Winter events
            (12, 1, 12, 31): {"naam": "Kerst Feest!", "type": "kerst", "bonus": 2.0},
            (1, 1, 1, 7): {"naam": "Nieuwjaars Viering!", "type": "nieuwjaar", "bonus": 1.5},
            # Lente events
            (3, 20, 4, 20): {"naam": "Lente Festival!", "type": "lente", "bonus": 1.3},
            (4, 27, 4, 27): {"naam": "Koningsdag!", "type": "koningsdag", "bonus": 2.0},
            # Zomer events
            (6, 21, 8, 31): {"naam": "Zomer Vakantie!", "type": "zomer", "bonus": 1.4},
            # Herfst events
            (10, 25, 11, 2): {"naam": "Halloween Spooktijd!", "type": "halloween", "bonus": 1.8},
            (11, 11, 11, 11): {"naam": "Sint Maarten!", "type": "sintmaarten", "bonus": 1.5},
            (12, 5, 12, 6): {"naam": "Sinterklaas!", "type": "sinterklaas", "bonus": 1.8},
        }

        for (m1, d1, m2, d2), event in events.items():
            if (maand == m1 and dag >= d1) or (maand == m2 and dag <= d2) or (m1 < maand < m2):
                return event
        return None

    def _verkenning_mode(self):
        """Verken verschillende locaties met je huisdier!"""
        if self.huisdier["energie"] < 2:
            print(f"\n{self.huisdier['naam']} is te moe om te verkennen!")
            return

        naam = self.huisdier["naam"]
        geluid = self.huisdier["geluid"]

        # Init verkenning data
        if "verkenning" not in self.huisdier:
            self.huisdier["verkenning"] = {
                "ontdekte_locaties": [],
                "verzamelde_items": [],
                "totaal_avonturen": 0
            }

        locaties = {
            "1": {
                "naam": "Mysterieus Bos",
                "emoji": "🌲",
                "beschrijving": "Een donker bos vol geheimen...",
                "moeilijkheid": 1,
                "beloningen": ["paddenstoel", "eikels", "veer", "kristal"],
                "events": [
                    "vindt een glinsterende steen!",
                    "ontmoet een vriendelijke uil!",
                    "vindt een verborgen pad!",
                    "hoort mysterieuze geluiden..."
                ]
            },
            "2": {
                "naam": "Zonnig Strand",
                "emoji": "🏖️",
                "beschrijving": "Warm zand en ruisende golven...",
                "moeilijkheid": 1,
                "beloningen": ["schelp", "zeester", "parel", "drijfhout"],
                "events": [
                    "bouwt een zandkasteel!",
                    "vindt een schatkist!",
                    "ziet dolfijnen springen!",
                    "vindt een bericht in een fles!"
                ]
            },
            "3": {
                "naam": "Drukke Stad",
                "emoji": "🏙️",
                "beschrijving": "Hoge gebouwen en veel mensen...",
                "moeilijkheid": 2,
                "beloningen": ["munt", "sleutel", "kaart", "gadget"],
                "events": [
                    "helpt een verdwaalde toerist!",
                    "vindt een geheime steeg!",
                    "ontdekt een cool cafe!",
                    "ziet een straatartiest!"
                ]
            },
            "4": {
                "naam": "Oude Ruines",
                "emoji": "🏛️",
                "beschrijving": "Overblijfselen van een oude beschaving...",
                "moeilijkheid": 3,
                "beloningen": ["artefact", "oude_munt", "scroll", "amulet"],
                "events": [
                    "ontcijfert oude tekens!",
                    "vindt een verborgen kamer!",
                    "ontdekt een oude val!",
                    "voelt mysterieuze energie..."
                ]
            },
            "5": {
                "naam": "Ruimtestation",
                "emoji": "🚀",
                "beschrijving": "Zwevend in de oneindige ruimte...",
                "moeilijkheid": 4,
                "beloningen": ["meteoriet", "sterrenstof", "alien_artefact", "ruimte_kristal"],
                "events": [
                    "ziet een prachtige sterrennevel!",
                    "ontmoet een vriendelijke alien!",
                    "zweeft in zero gravity!",
                    "ontdekt een nieuw planeet!"
                ]
            },
            "6": {
                "naam": "Onderwater Wereld",
                "emoji": "🌊",
                "beschrijving": "Een magische wereld onder de golven...",
                "moeilijkheid": 3,
                "beloningen": ["koraal", "zeeuwse_parel", "zeewier", "schatkist"],
                "events": [
                    "zwemt met vissen!",
                    "ontdekt een gezonken schip!",
                    "ziet een gigantische walvis!",
                    "vindt Atlantis?"
                ]
            },
        }

        print("\n" + "=" * 55)
        print(f"  [KOMPAS] {naam}'s VERKENNING MODE!")
        print("=" * 55)
        print(f"\n  Ontdekte locaties: {len(self.huisdier['verkenning']['ontdekte_locaties'])}/{len(locaties)}")
        print(f"  Verzamelde items: {len(self.huisdier['verkenning']['verzamelde_items'])}")
        print(f"  Totaal avonturen: {self.huisdier['verkenning']['totaal_avonturen']}")

        print("\n  Kies een locatie om te verkennen:")
        for loc_id, loc in locaties.items():
            ontdekt = "✓" if loc["naam"] in self.huisdier["verkenning"]["ontdekte_locaties"] else " "
            sterren = "⭐" * loc["moeilijkheid"]
            print(f"  {loc_id}. {loc['emoji']} {loc['naam']:<20} [{ontdekt}] {sterren}")
        print("  0. Terug")

        keuze = input("\n  Kies (0-6): ").strip()

        if keuze == "0" or keuze not in locaties:
            return

        locatie = locaties[keuze]
        energie_kosten = 2 + (locatie["moeilijkheid"] * 1)  # x10 minder energie

        if self.huisdier["energie"] < energie_kosten:
            print(f"\n  [!] {naam} heeft meer energie nodig! (Nodig: {energie_kosten})")
            return

        self.huisdier["energie"] -= energie_kosten

        print(f"\n  {naam} reist naar {locatie['emoji']} {locatie['naam']}...")
        print(f"  {locatie['beschrijving']}")
        time.sleep(1)

        print(f"\n  {geluid}")

        # Random events
        event = random.choice(locatie["events"])
        print(f"\n  [AVONTUUR] {naam} {event}")
        time.sleep(0.5)

        # Kans op item vinden
        item_kans = 60 + (self.huisdier.get("intelligentie", 0) // 5)
        if random.randint(1, 100) <= item_kans:
            item = random.choice(locatie["beloningen"])
            if item not in self.huisdier["verkenning"]["verzamelde_items"]:
                self.huisdier["verkenning"]["verzamelde_items"].append(item)
                print(f"  [VONDST] {naam} vindt een {item.replace('_', ' ')}!")
            else:
                bonus_munten = 10 * locatie["moeilijkheid"]
                self.huisdier["munten"] += bonus_munten
                print(f"  [MUNT] Al gevonden, verkoopt voor {bonus_munten} munten!")

        # Mark als ontdekt
        if locatie["naam"] not in self.huisdier["verkenning"]["ontdekte_locaties"]:
            self.huisdier["verkenning"]["ontdekte_locaties"].append(locatie["naam"])
            print(f"\n  [NIEUW] Nieuwe locatie ontdekt: {locatie['naam']}!")
            self.huisdier["munten"] += 25

        # Beloningen
        self.huisdier["verkenning"]["totaal_avonturen"] += 1
        xp_beloning = 20 * locatie["moeilijkheid"]
        munt_beloning = 10 * locatie["moeilijkheid"]

        self.huisdier["ervaring"] += xp_beloning
        self.huisdier["munten"] += munt_beloning
        self.huisdier["geluk"] = min(100, self.huisdier["geluk"] + 10)

        print(f"\n  [XP] +{xp_beloning} ervaring")
        print(f"  [MUNT] +{munt_beloning} munten")

        # Dagboek entry
        self._voeg_dagboek_toe(f"Verkende {locatie['naam']} en {event}")

        self._sla_op()

    def _huisdier_dagboek(self):
        """Bekijk het automatische dagboek van je huisdier."""
        naam = self.huisdier["naam"]

        # Init dagboek
        if "dagboek" not in self.huisdier:
            self.huisdier["dagboek"] = []

        print("\n" + "=" * 55)
        print(f"  [BOEK] {naam}'s DAGBOEK")
        print("=" * 55)

        if not self.huisdier["dagboek"]:
            print("\n  Het dagboek is nog leeg!")
            print("  Ga op avontuur om herinneringen te maken!")
            return

        print(f"\n  Totaal herinneringen: {len(self.huisdier['dagboek'])}")
        print("\n  --- RECENTE HERINNERINGEN ---")

        # Toon laatste 10 entries
        for entry in self.huisdier["dagboek"][-10:]:
            print(f"\n  [{entry['datum']}]")
            print(f"  {entry['tekst']}")

        print("\n  " + "-" * 50)

        # Statistieken
        print(f"\n  [STATS] Dagboek Statistieken:")
        print(f"    Eerste herinnering: {self.huisdier['dagboek'][0]['datum'] if self.huisdier['dagboek'] else 'Nog geen'}")
        print(f"    Totaal entries: {len(self.huisdier['dagboek'])}")

    def _voeg_dagboek_toe(self, tekst):
        """Voeg een entry toe aan het dagboek."""
        if "dagboek" not in self.huisdier:
            self.huisdier["dagboek"] = []

        entry = {
            "datum": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "tekst": tekst
        }
        self.huisdier["dagboek"].append(entry)

        # Houd max 50 entries
        if len(self.huisdier["dagboek"]) > 50:
            self.huisdier["dagboek"] = self.huisdier["dagboek"][-50:]

    def _seizoens_events(self):
        """Seizoens events met speciale beloningen!"""
        naam = self.huisdier["naam"]
        geluid = self.huisdier["geluid"]

        event = self._get_seizoen_event()

        print("\n" + "=" * 55)
        print(f"  [KALENDER] SEIZOENS EVENTS")
        print("=" * 55)

        if not event:
            print("\n  Er is momenteel geen speciaal event actief.")
            print("\n  Komende events:")
            print("    🎄 Kerst: 1-31 december")
            print("    🎆 Nieuwjaar: 1-7 januari")
            print("    🌸 Lente Festival: 20 maart - 20 april")
            print("    👑 Koningsdag: 27 april")
            print("    ☀️ Zomer Vakantie: 21 juni - 31 augustus")
            print("    🎃 Halloween: 25 oktober - 2 november")
            print("    🏮 Sint Maarten: 11 november")
            print("    🎁 Sinterklaas: 5-6 december")
            return

        print(f"\n  [ACTIEF EVENT] {event['naam']}")
        print(f"  Bonus multiplier: x{event['bonus']}")

        # Event-specifieke activiteiten
        activiteiten = {
            "kerst": [
                ("Kerstboom versieren", 20, 50),
                ("Cadeautjes uitpakken", 30, 75),
                ("Kerstkransje eten", 15, 30),
            ],
            "halloween": [
                ("Trick or Treat", 15, 40),
                ("Pompoen uithollen", 20, 50),
                ("Spookhuis bezoeken", 25, 60),
            ],
            "zomer": [
                ("Naar het strand", 10, 30),
                ("IJsje eten", 5, 20),
                ("Zwemmen", 15, 40),
            ],
            "koningsdag": [
                ("Vrijmarkt bezoeken", 10, 100),
                ("Oranje dragen", 5, 25),
                ("Spelen organiseren", 20, 50),
            ],
            "lente": [
                ("Bloemen plukken", 10, 25),
                ("Paaseieren zoeken", 15, 40),
                ("Picknicken", 10, 30),
            ],
            "sinterklaas": [
                ("Schoen zetten", 5, 50),
                ("Pepernoten vangen", 10, 30),
                ("Surprises maken", 20, 45),
            ],
        }

        event_acts = activiteiten.get(event["type"], [("Feest vieren", 15, 40)])

        print("\n  Speciale activiteiten:")
        for i, (act_naam, energie, beloning) in enumerate(event_acts, 1):
            print(f"  {i}. {act_naam} (-{energie} energie, +{int(beloning * event['bonus'])} munten)")
        print("  0. Terug")

        keuze = input("\n  Kies activiteit: ").strip()

        try:
            idx = int(keuze) - 1
            if 0 <= idx < len(event_acts):
                act_naam, energie, beloning = event_acts[idx]

                if self.huisdier["energie"] < energie:
                    print(f"\n  [!] {naam} heeft niet genoeg energie!")
                    return

                self.huisdier["energie"] -= energie
                echte_beloning = int(beloning * event["bonus"])
                self.huisdier["munten"] += echte_beloning
                self.huisdier["geluk"] = min(100, self.huisdier["geluk"] + 15)

                print(f"\n  {geluid}")
                print(f"  {naam} doet: {act_naam}!")
                print(f"  [MUNT] +{echte_beloning} munten (x{event['bonus']} bonus)!")
                print(f"  [HAPPY] +15 geluk!")

                self._voeg_dagboek_toe(f"{event['naam']}: {act_naam}")
                self._sla_op()
        except (ValueError, IndexError):
            pass

    def _competities(self):
        """Doe mee aan competities met je huisdier!"""
        naam = self.huisdier["naam"]
        geluid = self.huisdier["geluid"]
        iq = self.huisdier.get("intelligentie", 0)

        # Init competitie data
        if "competities" not in self.huisdier:
            self.huisdier["competities"] = {
                "gewonnen": 0,
                "deelgenomen": 0,
                "trofees": []
            }

        competities = {
            "1": {
                "naam": "Schoonheidswedstrijd",
                "emoji": "👑",
                "kosten": 25,
                "stat": "geluk",
                "beschrijving": "Wie is het mooiste huisdier?"
            },
            "2": {
                "naam": "Slimste Huisdier",
                "emoji": "🧠",
                "kosten": 30,
                "stat": "intelligentie",
                "beschrijving": "Test je kennis en wijsheid!"
            },
            "3": {
                "naam": "Snelheidsrace",
                "emoji": "🏃",
                "kosten": 20,
                "stat": "energie",
                "beschrijving": "Wie is het snelste?"
            },
            "4": {
                "naam": "Tricks Kampioenschap",
                "emoji": "🎪",
                "kosten": 35,
                "stat": "tricks",
                "beschrijving": "Toon je beste trucs!"
            },
            "5": {
                "naam": "Vechttoernooi",
                "emoji": "⚔️",
                "kosten": 40,
                "stat": "gezondheid",
                "beschrijving": "Wie is de sterkste?"
            },
        }

        print("\n" + "=" * 55)
        print(f"  [TROFEE] {naam}'s COMPETITIES")
        print("=" * 55)
        print(f"\n  Gewonnen: {self.huisdier['competities']['gewonnen']}")
        print(f"  Deelgenomen: {self.huisdier['competities']['deelgenomen']}")
        print(f"  Trofees: {len(self.huisdier['competities']['trofees'])}")

        print("\n  Beschikbare competities:")
        for comp_id, comp in competities.items():
            print(f"  {comp_id}. {comp['emoji']} {comp['naam']} ({comp['kosten']} munten)")
            print(f"      {comp['beschrijving']}")
        print("  0. Terug")

        keuze = input("\n  Kies competitie: ").strip()

        if keuze == "0" or keuze not in competities:
            return

        comp = competities[keuze]

        if self.huisdier["munten"] < comp["kosten"]:
            print(f"\n  [!] Niet genoeg munten! (Nodig: {comp['kosten']})")
            return

        if self.huisdier["energie"] < 3:
            print(f"\n  [!] {naam} is te moe om mee te doen!")
            return

        self.huisdier["munten"] -= comp["kosten"]
        self.huisdier["energie"] -= 3

        print(f"\n  {naam} doet mee aan {comp['emoji']} {comp['naam']}!")
        print(f"  {comp['beschrijving']}")
        time.sleep(1)

        # Bepaal score op basis van relevante stat
        stat_waarde = 50  # basis
        if comp["stat"] == "geluk":
            stat_waarde = self.huisdier["geluk"]
        elif comp["stat"] == "intelligentie":
            stat_waarde = iq
        elif comp["stat"] == "energie":
            stat_waarde = self.huisdier["energie"] + 30  # add back what was used
        elif comp["stat"] == "tricks":
            stat_waarde = len(self.huisdier["tricks_geleerd"]) * 15
        elif comp["stat"] == "gezondheid":
            stat_waarde = self.huisdier["gezondheid"]

        # Accessoire bonussen
        accessoire_bonus = len(self.huisdier["accessoires"]) * 5

        totaal_score = stat_waarde + accessoire_bonus + random.randint(-20, 20)
        tegenstander_score = random.randint(30, 80)

        print(f"\n  --- RESULTATEN ---")
        print(f"  {naam}'s score: {totaal_score}")
        print(f"  Tegenstander: {tegenstander_score}")
        time.sleep(0.5)

        self.huisdier["competities"]["deelgenomen"] += 1

        if totaal_score > tegenstander_score:
            print(f"\n  [TROFEE] {naam} WINT!")
            print(f"  {geluid} {geluid} {geluid}")

            self.huisdier["competities"]["gewonnen"] += 1
            prijs = comp["kosten"] * 3
            self.huisdier["munten"] += prijs
            self.huisdier["ervaring"] += 50

            # Trofee toekennen
            trofee_naam = f"{comp['naam']} Kampioen"
            if trofee_naam not in self.huisdier["competities"]["trofees"]:
                self.huisdier["competities"]["trofees"].append(trofee_naam)
                print(f"  [NIEUW] Trofee verdiend: {trofee_naam}!")

            print(f"  [MUNT] +{prijs} munten!")
            print(f"  [XP] +50 ervaring!")

            self._voeg_dagboek_toe(f"Won {comp['naam']}!")
        else:
            print(f"\n  [X] {naam} verliest helaas...")
            print(f"  Troostprijs: +10 munten")
            self.huisdier["munten"] += 10

            self._voeg_dagboek_toe(f"Deed mee aan {comp['naam']}")

        self._sla_op()

    def _slapen_met_dromen(self):
        """Slapen met kans op dromen voor extra beloningen."""
        naam = self.huisdier["naam"]
        geluid = self.huisdier["geluid"]

        # Init droom data
        if "dromen" not in self.huisdier:
            self.huisdier["dromen"] = {
                "totaal": 0,
                "unieke_dromen": []
            }

        dromen = [
            {"naam": "Vliegende Droom", "beschrijving": f"{naam} droomt over vliegen door de wolken!", "bonus_type": "geluk", "bonus": 15},
            {"naam": "Schat Droom", "beschrijving": f"{naam} droomt over een enorme schatkist!", "bonus_type": "munten", "bonus": 30},
            {"naam": "Avontuur Droom", "beschrijving": f"{naam} droomt over een episch avontuur!", "bonus_type": "ervaring", "bonus": 40},
            {"naam": "Eten Droom", "beschrijving": f"{naam} droomt over eindeloos lekker eten!", "bonus_type": "honger", "bonus": 20},
            {"naam": "Kennis Droom", "beschrijving": f"{naam} droomt over wijze leraren!", "bonus_type": "intelligentie", "bonus": 10},
            {"naam": "Vriendschap Droom", "beschrijving": f"{naam} droomt over geweldige vrienden!", "bonus_type": "geluk", "bonus": 20},
            {"naam": "Nachtmerrie", "beschrijving": f"{naam} had een nachtmerrie... maar is nu wakker!", "bonus_type": "geen", "bonus": 0},
            {"naam": "Herinneringen Droom", "beschrijving": f"{naam} droomt over mooie herinneringen!", "bonus_type": "geluk", "bonus": 10},
        ]

        # Kans op droom (hoger bij hogere geluk)
        droom_kans = 40 + (self.huisdier["geluk"] // 5)

        if random.randint(1, 100) <= droom_kans:
            droom = random.choice(dromen)
            self.huisdier["dromen"]["totaal"] += 1

            print(f"\n  [DROOM] {naam} begint te dromen...")
            time.sleep(0.5)

            # Probeer AI-generated droom (30% kans als AI beschikbaar)
            ai_droom = None
            if random.random() < 0.3:
                try:
                    ai_droom = self._ai_generate_dream()
                except Exception as e:
                    logger.debug("AI dream generation during sleep failed: %s", e)

            if ai_droom:
                print(f"\n  ✨ AI DROOM ✨")
                print(f"  {ai_droom}")
                # Extra IQ bonus voor AI dromen
                self.huisdier["intelligentie"] = self.huisdier.get("intelligentie", 0) + 2
                print(f"  [IQ] +2 intelligentie (AI droom bonus!)")
                self._ai_add_memory("slapen", f"AI Droom: {ai_droom[:50]}...")
            else:
                print(f"\n  ✨ {droom['naam']} ✨")
                print(f"  {droom['beschrijving']}")

            if droom["naam"] not in self.huisdier["dromen"]["unieke_dromen"]:
                self.huisdier["dromen"]["unieke_dromen"].append(droom["naam"])
                print(f"  [NIEUW] Eerste keer deze droom!")

            # Pas bonus toe
            if droom["bonus_type"] == "geluk":
                self.huisdier["geluk"] = min(100, self.huisdier["geluk"] + droom["bonus"])
                print(f"  [HAPPY] +{droom['bonus']} geluk!")
            elif droom["bonus_type"] == "munten":
                self.huisdier["munten"] += droom["bonus"]
                print(f"  [MUNT] +{droom['bonus']} munten!")
            elif droom["bonus_type"] == "ervaring":
                self.huisdier["ervaring"] += droom["bonus"]
                print(f"  [XP] +{droom['bonus']} ervaring!")
            elif droom["bonus_type"] == "honger":
                self.huisdier["honger"] = min(100, self.huisdier["honger"] + droom["bonus"])
                print(f"  [FOOD] +{droom['bonus']} honger!")
            elif droom["bonus_type"] == "intelligentie":
                self.huisdier["intelligentie"] = self.huisdier.get("intelligentie", 0) + droom["bonus"]
                print(f"  [IQ] +{droom['bonus']} intelligentie!")

            self._voeg_dagboek_toe(f"Had een droom: {droom['naam']}")

        return True

    # ==========================================
    # LEVEN & ECONOMIE FEATURES
    # ==========================================

    def _huisdier_huis(self):
        """Bouw en decoreer het huis van je huisdier!"""
        naam = self.huisdier["naam"]

        # Init huis data
        if "huis" not in self.huisdier:
            self.huisdier["huis"] = {
                "kamers": ["woonkamer"],
                "meubels": {},
                "niveau": 1,
                "comfort": 10
            }

        huis = self.huisdier["huis"]

        kamers_beschikbaar = {
            "slaapkamer": {"prijs": 100, "comfort": 20, "beschrijving": "Een gezellige slaapplek"},
            "keuken": {"prijs": 150, "comfort": 15, "beschrijving": "Kook heerlijke maaltijden"},
            "tuin": {"prijs": 200, "comfort": 25, "beschrijving": "Verbouw je eigen groenten"},
            "speelkamer": {"prijs": 120, "comfort": 30, "beschrijving": "Eindeloos speelplezier"},
            "bibliotheek": {"prijs": 180, "comfort": 20, "beschrijving": "Leer en ontdek"},
            "spa": {"prijs": 250, "comfort": 40, "beschrijving": "Ultieme ontspanning"},
        }

        meubels = {
            "bank": {"prijs": 50, "comfort": 10},
            "tv": {"prijs": 80, "comfort": 15},
            "plant": {"prijs": 20, "comfort": 5},
            "lamp": {"prijs": 30, "comfort": 8},
            "tapijt": {"prijs": 40, "comfort": 12},
            "aquarium": {"prijs": 100, "comfort": 20},
        }

        while True:
            totaal_comfort = huis["comfort"] + sum(m.get("comfort", 0) for m in huis["meubels"].values())

            print("\n" + "=" * 55)
            print(f"  [HUIS] {naam}'s HUIS - Niveau {huis['niveau']}")
            print("=" * 55)
            print(f"  Kamers: {len(huis['kamers'])} | Comfort: {totaal_comfort}")
            print(f"  Munten: {self.huisdier['munten']}")

            print("\n  Huidige kamers:")
            for kamer in huis["kamers"]:
                print(f"    - {kamer.title()}")

            print("\n  1. Kamer toevoegen")
            print("  2. Meubel kopen")
            print("  3. Huis bekijken")
            print("  0. Terug")

            keuze = input("\n  Keuze: ").strip()

            if keuze == "0":
                break
            elif keuze == "1":
                print("\n  Beschikbare kamers:")
                beschikbaar = [(k, v) for k, v in kamers_beschikbaar.items() if k not in huis["kamers"]]
                for i, (k, v) in enumerate(beschikbaar, 1):
                    print(f"    {i}. {k.title()} - {v['prijs']} munten (+{v['comfort']} comfort)")
                    print(f"       {v['beschrijving']}")

                kamer_keuze = input("\n  Kies kamer (0=terug): ").strip()
                try:
                    idx = int(kamer_keuze) - 1
                    if 0 <= idx < len(beschikbaar):
                        kamer_naam, kamer_data = beschikbaar[idx]
                        if self.huisdier["munten"] >= kamer_data["prijs"]:
                            self.huisdier["munten"] -= kamer_data["prijs"]
                            huis["kamers"].append(kamer_naam)
                            huis["comfort"] += kamer_data["comfort"]
                            huis["niveau"] = len(huis["kamers"])
                            print(f"\n  [OK] {kamer_naam.title()} toegevoegd!")
                            self._voeg_dagboek_toe(f"Nieuwe kamer: {kamer_naam}")
                        else:
                            print("\n  [!] Niet genoeg munten!")
                except (ValueError, IndexError):
                    pass

            elif keuze == "2":
                print("\n  Beschikbare meubels:")
                for i, (m, v) in enumerate(meubels.items(), 1):
                    owned = "✓" if m in huis["meubels"] else " "
                    print(f"    {i}. [{owned}] {m.title()} - {v['prijs']} munten (+{v['comfort']} comfort)")

                meubel_keuze = input("\n  Kies meubel (0=terug): ").strip()
                try:
                    idx = int(meubel_keuze) - 1
                    meubel_lijst = list(meubels.items())
                    if 0 <= idx < len(meubel_lijst):
                        meubel_naam, meubel_data = meubel_lijst[idx]
                        if meubel_naam not in huis["meubels"]:
                            if self.huisdier["munten"] >= meubel_data["prijs"]:
                                self.huisdier["munten"] -= meubel_data["prijs"]
                                huis["meubels"][meubel_naam] = meubel_data
                                print(f"\n  [OK] {meubel_naam.title()} gekocht!")
                            else:
                                print("\n  [!] Niet genoeg munten!")
                        else:
                            print("\n  [!] Je hebt dit meubel al!")
                except (ValueError, IndexError):
                    pass

            elif keuze == "3":
                print(f"\n  --- {naam}'s HUIS ---")
                for kamer in huis["kamers"]:
                    print(f"\n  [{kamer.upper()}]")
                    kamer_meubels = [m for m in huis["meubels"].keys()]
                    if kamer_meubels:
                        for m in kamer_meubels[:2]:
                            print(f"    - {m.title()}")
                    else:
                        print("    (leeg)")

            self._sla_op()

    def _mini_farming(self):
        """Verbouw gewassen voor voedsel en munten!"""
        naam = self.huisdier["naam"]

        # Init farming data
        if "farm" not in self.huisdier:
            self.huisdier["farm"] = {
                "velden": 2,
                "gewassen": [],
                "voorraad": {},
                "totaal_geoogst": 0
            }

        farm = self.huisdier["farm"]

        gewassen_types = {
            "wortel": {"groeitijd": 1, "opbrengst": 3, "prijs": 5, "verkoop": 8},
            "tomaat": {"groeitijd": 2, "opbrengst": 5, "prijs": 8, "verkoop": 15},
            "aardappel": {"groeitijd": 2, "opbrengst": 4, "prijs": 6, "verkoop": 12},
            "mais": {"groeitijd": 3, "opbrengst": 6, "prijs": 10, "verkoop": 20},
            "pompoen": {"groeitijd": 4, "opbrengst": 2, "prijs": 15, "verkoop": 35},
            "aardbei": {"groeitijd": 2, "opbrengst": 8, "prijs": 12, "verkoop": 25},
        }

        while True:
            print("\n" + "=" * 55)
            print(f"  [FARM] {naam}'s BOERDERIJ")
            print("=" * 55)
            print(f"  Velden: {len(farm['gewassen'])}/{farm['velden']} bezet")
            print(f"  Munten: {self.huisdier['munten']}")

            # Update groeiende gewassen
            nu = datetime.now()
            for gewas in farm["gewassen"]:
                geplant = datetime.fromisoformat(gewas["geplant"])
                groeitijd = gewassen_types[gewas["type"]]["groeitijd"]
                klaar_tijd = geplant + timedelta(minutes=groeitijd)
                gewas["klaar"] = nu >= klaar_tijd

            print("\n  Huidige gewassen:")
            if farm["gewassen"]:
                for i, gewas in enumerate(farm["gewassen"], 1):
                    status = "KLAAR!" if gewas["klaar"] else "groeit..."
                    print(f"    {i}. {gewas['type'].title()} - {status}")
            else:
                print("    (geen gewassen)")

            print("\n  Voorraad:")
            if farm["voorraad"]:
                for item, aantal in farm["voorraad"].items():
                    print(f"    - {item.title()}: {aantal}x")
            else:
                print("    (leeg)")

            print("\n  1. Gewas planten")
            print("  2. Oogsten")
            print("  3. Voorraad verkopen")
            print("  4. Extra veld kopen (50 munten)")
            print("  0. Terug")

            keuze = input("\n  Keuze: ").strip()

            if keuze == "0":
                break
            elif keuze == "1":
                if len(farm["gewassen"]) >= farm["velden"]:
                    print("\n  [!] Alle velden zijn bezet!")
                    continue

                print("\n  Beschikbare gewassen:")
                for i, (g, v) in enumerate(gewassen_types.items(), 1):
                    print(f"    {i}. {g.title()} - {v['prijs']} munten ({v['groeitijd']} min)")

                gewas_keuze = input("\n  Kies gewas: ").strip()
                try:
                    idx = int(gewas_keuze) - 1
                    gewas_lijst = list(gewassen_types.items())
                    if 0 <= idx < len(gewas_lijst):
                        gewas_naam, gewas_data = gewas_lijst[idx]
                        if self.huisdier["munten"] >= gewas_data["prijs"]:
                            self.huisdier["munten"] -= gewas_data["prijs"]
                            farm["gewassen"].append({
                                "type": gewas_naam,
                                "geplant": datetime.now().isoformat(),
                                "klaar": False
                            })
                            print(f"\n  [PLANT] {gewas_naam.title()} geplant!")
                        else:
                            print("\n  [!] Niet genoeg munten!")
                except (ValueError, IndexError):
                    pass

            elif keuze == "2":
                geoogst = []
                for gewas in farm["gewassen"][:]:
                    if gewas["klaar"]:
                        gewas_data = gewassen_types[gewas["type"]]
                        opbrengst = gewas_data["opbrengst"]
                        farm["voorraad"][gewas["type"]] = farm["voorraad"].get(gewas["type"], 0) + opbrengst
                        farm["totaal_geoogst"] += opbrengst
                        geoogst.append(f"{gewas['type']} x{opbrengst}")
                        farm["gewassen"].remove(gewas)

                if geoogst:
                    print(f"\n  [OOGST] Geoogst: {', '.join(geoogst)}")
                    self._voeg_dagboek_toe(f"Oogst: {', '.join(geoogst)}")
                else:
                    print("\n  [!] Niets klaar om te oogsten!")

            elif keuze == "3":
                if not farm["voorraad"]:
                    print("\n  [!] Voorraad is leeg!")
                    continue

                totaal = 0
                for item, aantal in farm["voorraad"].items():
                    prijs = gewassen_types[item]["verkoop"] * aantal
                    totaal += prijs
                    print(f"    {item.title()} x{aantal} = {prijs} munten")

                bevestig = input(f"\n  Alles verkopen voor {totaal} munten? (j/n): ").strip().lower()
                if bevestig == "j":
                    self.huisdier["munten"] += totaal
                    farm["voorraad"] = {}
                    print(f"\n  [MUNT] +{totaal} munten!")

            elif keuze == "4":
                if self.huisdier["munten"] >= 50:
                    self.huisdier["munten"] -= 50
                    farm["velden"] += 1
                    print(f"\n  [OK] Extra veld gekocht! Totaal: {farm['velden']}")
                else:
                    print("\n  [!] Niet genoeg munten!")

            self._sla_op()

    def _crafting_werkplaats(self):
        """Maak items van verzamelde materialen!"""
        naam = self.huisdier["naam"]

        # Init crafting data
        if "crafting" not in self.huisdier:
            self.huisdier["crafting"] = {
                "materialen": {},
                "gemaakte_items": []
            }

        crafting = self.huisdier["crafting"]

        # Voeg materialen toe van verkenning
        if "verkenning" in self.huisdier:
            for item in self.huisdier["verkenning"].get("verzamelde_items", []):
                if item not in crafting["materialen"]:
                    crafting["materialen"][item] = 1

        recepten = {
            "geluksamulet": {
                "materialen": {"kristal": 1, "veer": 1},
                "effect": {"geluk": 20},
                "beschrijving": "Verhoogt permanent geluk"
            },
            "energie_drankje": {
                "materialen": {"paddenstoel": 2, "zeewier": 1},
                "effect": {"energie": 30},
                "beschrijving": "Herstelt energie instant"
            },
            "wijsheid_scroll": {
                "materialen": {"scroll": 1, "sterrenstof": 1},
                "effect": {"intelligentie": 10},
                "beschrijving": "Verhoogt IQ permanent"
            },
            "gouden_ring": {
                "materialen": {"oude_munt": 3, "parel": 1},
                "effect": {"munten": 100},
                "beschrijving": "Verkoopt voor 100 munten"
            },
            "super_voedsel": {
                "materialen": {"koraal": 1, "schelp": 2},
                "effect": {"honger": 50, "gezondheid": 20},
                "beschrijving": "Vult honger en gezondheid"
            },
        }

        while True:
            print("\n" + "=" * 55)
            print(f"  [CRAFT] {naam}'s WERKPLAATS")
            print("=" * 55)

            print("\n  Materialen:")
            if crafting["materialen"]:
                for mat, aantal in crafting["materialen"].items():
                    print(f"    - {mat.replace('_', ' ').title()}: {aantal}x")
            else:
                print("    (geen materialen - ga verkennen!)")

            print("\n  Recepten:")
            for i, (item, data) in enumerate(recepten.items(), 1):
                kan_maken = all(crafting["materialen"].get(m, 0) >= a for m, a in data["materialen"].items())
                status = "[OK]" if kan_maken else "[X]"
                print(f"    {i}. {status} {item.replace('_', ' ').title()}")
                print(f"       {data['beschrijving']}")
                mats = ", ".join(f"{m}x{a}" for m, a in data["materialen"].items())
                print(f"       Nodig: {mats}")

            print("\n  0. Terug")

            keuze = input("\n  Kies recept om te maken: ").strip()

            if keuze == "0":
                break

            try:
                idx = int(keuze) - 1
                recept_lijst = list(recepten.items())
                if 0 <= idx < len(recept_lijst):
                    item_naam, item_data = recept_lijst[idx]

                    # Check materialen
                    kan_maken = all(crafting["materialen"].get(m, 0) >= a for m, a in item_data["materialen"].items())

                    if kan_maken:
                        # Verwijder materialen
                        for mat, aantal in item_data["materialen"].items():
                            crafting["materialen"][mat] -= aantal
                            if crafting["materialen"][mat] <= 0:
                                del crafting["materialen"][mat]

                        # Pas effect toe
                        for stat, waarde in item_data["effect"].items():
                            if stat == "munten":
                                self.huisdier["munten"] += waarde
                            elif stat == "intelligentie":
                                self.huisdier["intelligentie"] = self.huisdier.get("intelligentie", 0) + waarde
                            elif stat in self.huisdier:
                                self.huisdier[stat] = min(100, self.huisdier[stat] + waarde)

                        crafting["gemaakte_items"].append(item_naam)
                        print(f"\n  [CRAFT] {item_naam.replace('_', ' ').title()} gemaakt!")
                        print(f"  Effect: {item_data['effect']}")
                        self._voeg_dagboek_toe(f"Crafting: {item_naam}")
                    else:
                        print("\n  [!] Niet genoeg materialen!")
            except (ValueError, IndexError):
                pass

            self._sla_op()

    def _kook_keuken(self):
        """Kook maaltijden van ingrediënten!"""
        naam = self.huisdier["naam"]

        # Init keuken data
        if "keuken" not in self.huisdier:
            self.huisdier["keuken"] = {
                "ingredienten": {"brood": 5, "kaas": 3, "tomaat": 2},
                "recepten_geleerd": ["tosti"],
                "maaltijden_gekookt": 0
            }

        keuken = self.huisdier["keuken"]

        recepten = {
            "tosti": {
                "ingredienten": {"brood": 2, "kaas": 1},
                "honger": 25, "geluk": 10, "energie": 5
            },
            "salade": {
                "ingredienten": {"tomaat": 2, "wortel": 1},
                "honger": 15, "geluk": 5, "gezondheid": 15
            },
            "pizza": {
                "ingredienten": {"brood": 1, "kaas": 2, "tomaat": 1},
                "honger": 40, "geluk": 20, "energie": 10
            },
            "soep": {
                "ingredienten": {"wortel": 2, "aardappel": 2},
                "honger": 30, "geluk": 10, "gezondheid": 20
            },
            "taart": {
                "ingredienten": {"aardbei": 3, "mais": 1},
                "honger": 20, "geluk": 35, "energie": 15
            },
        }

        while True:
            print("\n" + "=" * 55)
            print(f"  [KOOK] {naam}'s KEUKEN")
            print("=" * 55)
            print(f"  Maaltijden gekookt: {keuken['maaltijden_gekookt']}")

            print("\n  Ingrediënten:")
            if keuken["ingredienten"]:
                for ing, aantal in keuken["ingredienten"].items():
                    print(f"    - {ing.title()}: {aantal}x")
            else:
                print("    (geen ingrediënten)")

            # Voeg farm producten toe
            if "farm" in self.huisdier and self.huisdier["farm"]["voorraad"]:
                print("\n  [TIP] Je hebt producten op de farm!")

            print("\n  Recepten:")
            for i, (recept, data) in enumerate(recepten.items(), 1):
                kan_koken = all(keuken["ingredienten"].get(ing, 0) >= a for ing, a in data["ingredienten"].items())
                status = "[OK]" if kan_koken else "[X]"
                print(f"    {i}. {status} {recept.title()}")
                ings = ", ".join(f"{ing}x{a}" for ing, a in data["ingredienten"].items())
                print(f"       Nodig: {ings}")
                print(f"       Effect: +{data['honger']} honger, +{data['geluk']} geluk")

            print("\n  a. Ingrediënten kopen")
            print("  b. Farm producten ophalen")
            print("  0. Terug")

            keuze = input("\n  Keuze: ").strip().lower()

            if keuze == "0":
                break
            elif keuze == "a":
                winkel_items = {
                    "brood": 5, "kaas": 8, "tomaat": 4,
                    "wortel": 3, "aardappel": 4
                }
                print("\n  Ingrediënten winkel:")
                for i, (item, prijs) in enumerate(winkel_items.items(), 1):
                    print(f"    {i}. {item.title()} - {prijs} munten")

                item_keuze = input("\n  Kies item: ").strip()
                try:
                    idx = int(item_keuze) - 1
                    item_lijst = list(winkel_items.items())
                    if 0 <= idx < len(item_lijst):
                        item_naam, prijs = item_lijst[idx]
                        if self.huisdier["munten"] >= prijs:
                            self.huisdier["munten"] -= prijs
                            keuken["ingredienten"][item_naam] = keuken["ingredienten"].get(item_naam, 0) + 1
                            print(f"\n  [OK] {item_naam.title()} gekocht!")
                        else:
                            print("\n  [!] Niet genoeg munten!")
                except (ValueError, IndexError):
                    pass

            elif keuze == "b":
                if "farm" in self.huisdier and self.huisdier["farm"]["voorraad"]:
                    for item, aantal in self.huisdier["farm"]["voorraad"].items():
                        keuken["ingredienten"][item] = keuken["ingredienten"].get(item, 0) + aantal
                    self.huisdier["farm"]["voorraad"] = {}
                    print("\n  [OK] Farm producten opgehaald!")
                else:
                    print("\n  [!] Geen farm producten beschikbaar!")

            else:
                try:
                    idx = int(keuze) - 1
                    recept_lijst = list(recepten.items())
                    if 0 <= idx < len(recept_lijst):
                        recept_naam, recept_data = recept_lijst[idx]
                        kan_koken = all(keuken["ingredienten"].get(ing, 0) >= a for ing, a in recept_data["ingredienten"].items())

                        if kan_koken:
                            for ing, aantal in recept_data["ingredienten"].items():
                                keuken["ingredienten"][ing] -= aantal
                                if keuken["ingredienten"][ing] <= 0:
                                    del keuken["ingredienten"][ing]

                            self.huisdier["honger"] = min(100, self.huisdier["honger"] + recept_data["honger"])
                            self.huisdier["geluk"] = min(100, self.huisdier["geluk"] + recept_data["geluk"])
                            if "energie" in recept_data:
                                self.huisdier["energie"] = min(100, self.huisdier["energie"] + recept_data["energie"])
                            if "gezondheid" in recept_data:
                                self.huisdier["gezondheid"] = min(100, self.huisdier["gezondheid"] + recept_data["gezondheid"])

                            keuken["maaltijden_gekookt"] += 1
                            print(f"\n  [KOOK] {recept_naam.title()} gemaakt en opgegeten!")
                            print(f"  +{recept_data['honger']} honger, +{recept_data['geluk']} geluk!")
                            self._voeg_dagboek_toe(f"Kookte: {recept_naam}")
                        else:
                            print("\n  [!] Niet genoeg ingrediënten!")
                except (ValueError, IndexError):
                    pass

            self._sla_op()

    def _huisdier_bank(self):
        """Spaar munten en verdien rente!"""
        naam = self.huisdier["naam"]

        # Init bank data
        if "bank" not in self.huisdier:
            self.huisdier["bank"] = {
                "saldo": 0,
                "laatste_rente": datetime.now().isoformat(),
                "totaal_rente": 0
            }

        bank = self.huisdier["bank"]

        # Bereken rente (1% per dag, max 1x per dag)
        laatste = datetime.fromisoformat(bank["laatste_rente"])
        dagen_verstreken = (datetime.now() - laatste).days

        if dagen_verstreken > 0 and bank["saldo"] > 0:
            rente = int(bank["saldo"] * 0.01 * dagen_verstreken)
            if rente > 0:
                bank["saldo"] += rente
                bank["totaal_rente"] += rente
                bank["laatste_rente"] = datetime.now().isoformat()
                print(f"\n  [BANK] Je hebt {rente} munten rente ontvangen!")

        while True:
            print("\n" + "=" * 55)
            print(f"  [BANK] {naam}'s SPAARREKENING")
            print("=" * 55)
            print(f"  Saldo: {bank['saldo']} munten")
            print(f"  Portemonnee: {self.huisdier['munten']} munten")
            print(f"  Rente: 1% per dag")
            print(f"  Totaal rente verdiend: {bank['totaal_rente']} munten")

            print("\n  1. Storten")
            print("  2. Opnemen")
            print("  3. Alles opnemen")
            print("  0. Terug")

            keuze = input("\n  Keuze: ").strip()

            if keuze == "0":
                break
            elif keuze == "1":
                try:
                    bedrag = int(input("  Hoeveel storten? ").strip())
                    if bedrag > 0 and bedrag <= self.huisdier["munten"]:
                        self.huisdier["munten"] -= bedrag
                        bank["saldo"] += bedrag
                        print(f"\n  [OK] {bedrag} munten gestort!")
                    else:
                        print("\n  [!] Ongeldig bedrag!")
                except ValueError:
                    print("\n  [!] Voer een getal in!")

            elif keuze == "2":
                try:
                    bedrag = int(input("  Hoeveel opnemen? ").strip())
                    if bedrag > 0 and bedrag <= bank["saldo"]:
                        bank["saldo"] -= bedrag
                        self.huisdier["munten"] += bedrag
                        print(f"\n  [OK] {bedrag} munten opgenomen!")
                    else:
                        print("\n  [!] Ongeldig bedrag!")
                except ValueError:
                    print("\n  [!] Voer een getal in!")

            elif keuze == "3":
                if bank["saldo"] > 0:
                    self.huisdier["munten"] += bank["saldo"]
                    print(f"\n  [OK] {bank['saldo']} munten opgenomen!")
                    bank["saldo"] = 0
                else:
                    print("\n  [!] Geen saldo!")

            self._sla_op()

    # ==========================================
    # SOCIAAL & DOELEN FEATURES
    # ==========================================

    def _huisdier_vrienden(self):
        """Ontmoet en bevriend NPC huisdieren!"""
        naam = self.huisdier["naam"]

        # Init vrienden data
        if "vrienden" not in self.huisdier:
            self.huisdier["vrienden"] = {
                "lijst": [],
                "interacties": 0
            }

        npc_huisdieren = {
            "max": {"naam": "Max", "type": "hond", "emoji": "🐕", "persoonlijkheid": "speels"},
            "luna": {"naam": "Luna", "type": "kat", "emoji": "🐱", "persoonlijkheid": "mysterieus"},
            "pip": {"naam": "Pip", "type": "vogel", "emoji": "🐦", "persoonlijkheid": "vrolijk"},
            "rocky": {"naam": "Rocky", "type": "schildpad", "emoji": "🐢", "persoonlijkheid": "wijs"},
            "bella": {"naam": "Bella", "type": "konijn", "emoji": "🐰", "persoonlijkheid": "lief"},
            "charlie": {"naam": "Charlie", "type": "hamster", "emoji": "🐹", "persoonlijkheid": "energiek"},
        }

        while True:
            print("\n" + "=" * 55)
            print(f"  [VRIENDEN] {naam}'s SOCIALE LEVEN")
            print("=" * 55)
            print(f"  Vrienden: {len(self.huisdier['vrienden']['lijst'])}/{len(npc_huisdieren)}")
            print(f"  Totaal interacties: {self.huisdier['vrienden']['interacties']}")

            print("\n  Bekende huisdieren:")
            for npc_id, npc in npc_huisdieren.items():
                is_vriend = npc_id in self.huisdier["vrienden"]["lijst"]
                status = "👫 Vriend" if is_vriend else "👋 Ken je nog niet"
                print(f"    {npc['emoji']} {npc['naam']} ({npc['type']}) - {status}")
                print(f"       Persoonlijkheid: {npc['persoonlijkheid']}")

            print("\n  1. Iemand ontmoeten (10 energie)")
            print("  2. Met vriend spelen (15 energie)")
            print("  0. Terug")

            keuze = input("\n  Keuze: ").strip()

            if keuze == "0":
                break
            elif keuze == "1":
                if self.huisdier["energie"] < 1:
                    print("\n  [!] Te moe om te socializen!")
                    continue

                self.huisdier["energie"] -= 1

                # Kies random NPC die nog geen vriend is
                niet_vrienden = [npc_id for npc_id in npc_huisdieren if npc_id not in self.huisdier["vrienden"]["lijst"]]

                if niet_vrienden:
                    npc_id = random.choice(niet_vrienden)
                    npc = npc_huisdieren[npc_id]

                    print(f"\n  {naam} ontmoet {npc['emoji']} {npc['naam']}!")
                    time.sleep(0.5)

                    # Kans om vrienden te worden
                    kans = 50 + (self.huisdier["geluk"] // 2)
                    if random.randint(1, 100) <= kans:
                        self.huisdier["vrienden"]["lijst"].append(npc_id)
                        print(f"  [VRIEND] {npc['naam']} en {naam} zijn nu vrienden!")
                        self.huisdier["geluk"] = min(100, self.huisdier["geluk"] + 15)
                        self._voeg_dagboek_toe(f"Nieuwe vriend: {npc['naam']}")
                    else:
                        print(f"  {npc['naam']} wil je beter leren kennen. Probeer later opnieuw!")

                    self.huisdier["vrienden"]["interacties"] += 1
                else:
                    print("\n  [OK] Je bent al met iedereen bevriend!")

            elif keuze == "2":
                if self.huisdier["energie"] < 2:
                    print("\n  [!] Te moe om te spelen!")
                    continue

                if not self.huisdier["vrienden"]["lijst"]:
                    print("\n  [!] Je hebt nog geen vrienden!")
                    continue

                self.huisdier["energie"] -= 2

                vriend_id = random.choice(self.huisdier["vrienden"]["lijst"])
                vriend = npc_huisdieren[vriend_id]

                activiteiten = [
                    f"speelt verstoppertje met {vriend['naam']}!",
                    f"rent door het park met {vriend['naam']}!",
                    f"deelt snacks met {vriend['naam']}!",
                    f"leert een nieuw spel van {vriend['naam']}!",
                ]

                print(f"\n  {naam} {random.choice(activiteiten)}")
                self.huisdier["geluk"] = min(100, self.huisdier["geluk"] + 20)
                self.huisdier["ervaring"] += 15
                self.huisdier["vrienden"]["interacties"] += 1

                print(f"  [HAPPY] +20 geluk!")
                print(f"  [XP] +15 ervaring!")

            self._sla_op()

    def _dagelijkse_missies(self):
        """Dagelijkse missies voor extra beloningen!"""
        naam = self.huisdier["naam"]

        # Init missies data
        if "missies" not in self.huisdier:
            self.huisdier["missies"] = {
                "huidige": [],
                "voltooid_vandaag": 0,
                "laatste_reset": datetime.now().date().isoformat(),
                "totaal_voltooid": 0
            }

        missies = self.huisdier["missies"]

        # Reset missies elke dag
        vandaag = datetime.now().date().isoformat()
        if missies["laatste_reset"] != vandaag:
            missies["huidige"] = []
            missies["voltooid_vandaag"] = 0
            missies["laatste_reset"] = vandaag

        # Genereer missies als er geen zijn
        alle_missies = [
            {"naam": "Voer je huisdier 3x", "type": "voeren", "doel": 3, "beloning": 30},
            {"naam": "Speel 2 mini-games", "type": "games", "doel": 2, "beloning": 25},
            {"naam": "Laat je huisdier slapen", "type": "slapen", "doel": 1, "beloning": 15},
            {"naam": "Leer een nieuw feit", "type": "leren", "doel": 1, "beloning": 35},
            {"naam": "Ga op verkenning", "type": "verkennen", "doel": 1, "beloning": 40},
            {"naam": "Win een competitie", "type": "competitie", "doel": 1, "beloning": 50},
            {"naam": "Kook een maaltijd", "type": "koken", "doel": 1, "beloning": 25},
            {"naam": "Oogst gewassen", "type": "oogsten", "doel": 1, "beloning": 20},
        ]

        if not missies["huidige"]:
            dagelijkse = random.sample(alle_missies, 3)
            missies["huidige"] = [{"missie": m, "voortgang": 0, "voltooid": False} for m in dagelijkse]

        print("\n" + "=" * 55)
        print(f"  [MISSIES] {naam}'s DAGELIJKSE MISSIES")
        print("=" * 55)
        print(f"  Voltooid vandaag: {missies['voltooid_vandaag']}/3")
        print(f"  Totaal ooit voltooid: {missies['totaal_voltooid']}")

        print("\n  Vandaag's missies:")
        for i, m in enumerate(missies["huidige"], 1):
            missie = m["missie"]
            if m["voltooid"]:
                status = "✓ VOLTOOID"
            else:
                status = f"{m['voortgang']}/{missie['doel']}"
            print(f"    {i}. {missie['naam']}")
            print(f"       Status: {status} | Beloning: {missie['beloning']} munten")

        # Check voltooide missies
        alle_voltooid = all(m["voltooid"] for m in missies["huidige"])
        if alle_voltooid:
            print("\n  [BONUS] Alle missies voltooid! +50 bonus munten beschikbaar!")

        print("\n  1. Claim voltooide missies")
        print("  0. Terug")

        keuze = input("\n  Keuze: ").strip()

        if keuze == "1":
            geclaimed = 0
            for m in missies["huidige"]:
                if m["voortgang"] >= m["missie"]["doel"] and not m["voltooid"]:
                    m["voltooid"] = True
                    self.huisdier["munten"] += m["missie"]["beloning"]
                    missies["voltooid_vandaag"] += 1
                    missies["totaal_voltooid"] += 1
                    geclaimed += m["missie"]["beloning"]
                    print(f"  [OK] {m['missie']['naam']} voltooid! +{m['missie']['beloning']} munten")

            # Bonus voor alle 3
            if alle_voltooid and geclaimed > 0:
                self.huisdier["munten"] += 50
                print(f"  [BONUS] Alle missies klaar! +50 bonus munten!")

            if geclaimed == 0:
                print("\n  [!] Geen missies klaar om te claimen!")

            self._sla_op()

    def _levensdoelen(self):
        """Lange termijn doelen om na te streven!"""
        naam = self.huisdier["naam"]

        # Init doelen data
        if "levensdoelen" not in self.huisdier:
            self.huisdier["levensdoelen"] = {
                "voltooid": [],
                "actief": None
            }

        doelen = self.huisdier["levensdoelen"]

        alle_doelen = {
            "rijkdom": {
                "naam": "Word Miljonair",
                "beschrijving": "Verzamel 10.000 munten totaal",
                "check": lambda h: h["munten"] + h.get("bank", {}).get("saldo", 0) >= 10000,
                "beloning": {"munten": 1000, "titel": "Rijkaard"}
            },
            "wijsheid": {
                "naam": "Meester van Kennis",
                "beschrijving": "Leer 50 feiten",
                "check": lambda h: len(h.get("kennis", {}).get("feiten", [])) >= 50,
                "beloning": {"intelligentie": 50, "titel": "Wijze"}
            },
            "avonturier": {
                "naam": "Wereldreiziger",
                "beschrijving": "Ontdek alle 6 locaties",
                "check": lambda h: len(h.get("verkenning", {}).get("ontdekte_locaties", [])) >= 6,
                "beloning": {"munten": 500, "titel": "Ontdekker"}
            },
            "sociaal": {
                "naam": "Populair",
                "beschrijving": "Maak 6 vrienden",
                "check": lambda h: len(h.get("vrienden", {}).get("lijst", [])) >= 6,
                "beloning": {"geluk": 50, "titel": "Vriend van Iedereen"}
            },
            "chef": {
                "naam": "Meesterkok",
                "beschrijving": "Kook 25 maaltijden",
                "check": lambda h: h.get("keuken", {}).get("maaltijden_gekookt", 0) >= 25,
                "beloning": {"munten": 300, "titel": "Chef"}
            },
            "boer": {
                "naam": "Landeigenaar",
                "beschrijving": "Oogst 100 gewassen",
                "check": lambda h: h.get("farm", {}).get("totaal_geoogst", 0) >= 100,
                "beloning": {"munten": 400, "titel": "Boer"}
            },
        }

        print("\n" + "=" * 55)
        print(f"  [DOEL] {naam}'s LEVENSDOELEN")
        print("=" * 55)
        print(f"  Doelen voltooid: {len(doelen['voltooid'])}/{len(alle_doelen)}")

        if doelen["actief"]:
            actief = alle_doelen.get(doelen["actief"])
            if actief:
                print(f"\n  Huidig doel: {actief['naam']}")
                print(f"  {actief['beschrijving']}")

        print("\n  Alle doelen:")
        for i, (doel_id, doel) in enumerate(alle_doelen.items(), 1):
            if doel_id in doelen["voltooid"]:
                status = "✓ VOLTOOID"
            elif doel_id == doelen["actief"]:
                status = "→ ACTIEF"
            else:
                status = "  -"
            print(f"    {i}. [{status}] {doel['naam']}")
            print(f"       {doel['beschrijving']}")
            print(f"       Beloning: {doel['beloning']}")

        print("\n  1. Doel kiezen")
        print("  2. Voortgang checken")
        print("  0. Terug")

        keuze = input("\n  Keuze: ").strip()

        if keuze == "1":
            beschikbaar = [(did, d) for did, d in alle_doelen.items() if did not in doelen["voltooid"]]
            print("\n  Beschikbare doelen:")
            for i, (did, d) in enumerate(beschikbaar, 1):
                print(f"    {i}. {d['naam']}")

            doel_keuze = input("\n  Kies doel: ").strip()
            try:
                idx = int(doel_keuze) - 1
                if 0 <= idx < len(beschikbaar):
                    doel_id, _ = beschikbaar[idx]
                    doelen["actief"] = doel_id
                    print(f"\n  [OK] Nieuw doel: {alle_doelen[doel_id]['naam']}")
            except (ValueError, IndexError):
                pass

        elif keuze == "2":
            if doelen["actief"]:
                doel = alle_doelen[doelen["actief"]]
                if doel["check"](self.huisdier):
                    print(f"\n  [DOEL] {doel['naam']} VOLTOOID!")

                    # Geef beloningen
                    beloning = doel["beloning"]
                    for stat, waarde in beloning.items():
                        if stat == "munten":
                            self.huisdier["munten"] += waarde
                            print(f"  [MUNT] +{waarde} munten!")
                        elif stat == "intelligentie":
                            self.huisdier["intelligentie"] = self.huisdier.get("intelligentie", 0) + waarde
                            print(f"  [IQ] +{waarde} intelligentie!")
                        elif stat == "geluk":
                            self.huisdier["geluk"] = min(100, self.huisdier["geluk"] + waarde)
                            print(f"  [HAPPY] +{waarde} geluk!")
                        elif stat == "titel":
                            print(f"  [TITEL] Nieuwe titel: {waarde}!")

                    doelen["voltooid"].append(doelen["actief"])
                    doelen["actief"] = None
                    self._voeg_dagboek_toe(f"Levensdoel voltooid: {doel['naam']}")
                else:
                    print(f"\n  [INFO] Nog niet voltooid. Blijf werken aan: {doel['beschrijving']}")
            else:
                print("\n  [!] Kies eerst een doel!")

        self._sla_op()

    def _foto_album(self):
        """Bekijk en maak foto's van speciale momenten!"""
        naam = self.huisdier["naam"]

        # Init album data
        if "album" not in self.huisdier:
            self.huisdier["album"] = {
                "fotos": [],
                "collecties": []
            }

        album = self.huisdier["album"]

        print("\n" + "=" * 55)
        print(f"  [FOTO] {naam}'s FOTO ALBUM")
        print("=" * 55)
        print(f"  Foto's: {len(album['fotos'])}")

        if album["fotos"]:
            print("\n  Recente foto's:")
            for foto in album["fotos"][-5:]:
                print(f"    [{foto['datum']}] {foto['beschrijving']}")
        else:
            print("\n  Nog geen foto's!")
            print("  Foto's worden automatisch gemaakt bij speciale momenten.")

        print("\n  1. Selfie maken (5 munten)")
        print("  2. Alle foto's bekijken")
        print("  0. Terug")

        keuze = input("\n  Keuze: ").strip()

        if keuze == "1":
            if self.huisdier["munten"] >= 5:
                self.huisdier["munten"] -= 5

                poses = [
                    f"{naam} poseert schattig!",
                    f"{naam} maakt een grappig gezicht!",
                    f"{naam} lacht naar de camera!",
                    f"{naam} zwaait naar de camera!",
                    f"{naam} doet een coole pose!",
                ]

                foto = {
                    "datum": datetime.now().strftime("%Y-%m-%d"),
                    "beschrijving": random.choice(poses),
                    "type": "selfie"
                }
                album["fotos"].append(foto)
                print(f"\n  [FOTO] Nieuwe foto: {foto['beschrijving']}")
                self._sla_op()
            else:
                print("\n  [!] Niet genoeg munten!")

        elif keuze == "2":
            if album["fotos"]:
                print(f"\n  --- ALLE FOTO'S ({len(album['fotos'])}) ---")
                for i, foto in enumerate(album["fotos"], 1):
                    print(f"    {i}. [{foto['datum']}] {foto['beschrijving']}")
            else:
                print("\n  [!] Geen foto's in album!")

    def _maak_foto(self, beschrijving):
        """Automatisch een foto maken bij speciale momenten."""
        if "album" not in self.huisdier:
            self.huisdier["album"] = {"fotos": [], "collecties": []}

        foto = {
            "datum": datetime.now().strftime("%Y-%m-%d"),
            "beschrijving": beschrijving,
            "type": "automatisch"
        }
        self.huisdier["album"]["fotos"].append(foto)

    def _weer_station(self):
        """Bekijk het weer en hoe het je huisdier beïnvloedt!"""
        naam = self.huisdier["naam"]

        # Simuleer weer (of gebruik echte weer agent als beschikbaar)
        weer_types = [
            {"type": "zonnig", "emoji": "☀️", "effect": {"geluk": 10, "energie": 1}, "beschrijving": "Lekker weer om buiten te spelen!"},
            {"type": "bewolkt", "emoji": "☁️", "effect": {"geluk": 0, "energie": 0}, "beschrijving": "Neutraal weer."},
            {"type": "regenachtig", "emoji": "🌧️", "effect": {"geluk": -5, "energie": -1}, "beschrijving": "Blijf liever binnen..."},
            {"type": "sneeuw", "emoji": "❄️", "effect": {"geluk": 15, "energie": -1}, "beschrijving": "Sneeuwpret maar wel koud!"},
            {"type": "storm", "emoji": "⛈️", "effect": {"geluk": -10, "energie": -1}, "beschrijving": "Eng weer! Blijf binnen!"},
            {"type": "mistig", "emoji": "🌫️", "effect": {"geluk": -3, "energie": 0}, "beschrijving": "Mysterieus en stil."},
        ]

        # Init weer data
        if "weer" not in self.huisdier:
            self.huisdier["weer"] = {
                "huidig": random.choice(weer_types),
                "laatste_update": datetime.now().isoformat()
            }

        # Update weer elke 30 minuten
        laatste = datetime.fromisoformat(self.huisdier["weer"]["laatste_update"])
        if (datetime.now() - laatste).seconds > 1800:
            self.huisdier["weer"]["huidig"] = random.choice(weer_types)
            self.huisdier["weer"]["laatste_update"] = datetime.now().isoformat()

        weer = self.huisdier["weer"]["huidig"]

        print("\n" + "=" * 55)
        print(f"  [WEER] WEER STATION")
        print("=" * 55)
        print(f"\n  Huidig weer: {weer['emoji']} {weer['type'].upper()}")
        print(f"  {weer['beschrijving']}")

        print(f"\n  Effect op {naam}:")
        for stat, waarde in weer["effect"].items():
            if waarde > 0:
                print(f"    {stat.title()}: +{waarde}")
            elif waarde < 0:
                print(f"    {stat.title()}: {waarde}")

        print("\n  1. Weer effect toepassen (1x per uur)")
        print("  2. Weer voorspelling")
        print("  0. Terug")

        keuze = input("\n  Keuze: ").strip()

        if keuze == "1":
            # Pas weer effect toe
            for stat, waarde in weer["effect"].items():
                if stat in self.huisdier:
                    self.huisdier[stat] = max(0, min(100, self.huisdier[stat] + waarde))

            print(f"\n  [OK] Weer effect toegepast!")
            if weer["effect"]["geluk"] > 0:
                print(f"  {naam} geniet van het {weer['type']}e weer!")
            elif weer["effect"]["geluk"] < 0:
                print(f"  {naam} vindt het {weer['type']}e weer niet leuk...")

            self._sla_op()

        elif keuze == "2":
            print("\n  Weer voorspelling voor morgen:")
            morgen_weer = random.choice(weer_types)
            print(f"    {morgen_weer['emoji']} {morgen_weer['type'].title()}")
            print(f"    {morgen_weer['beschrijving']}")

    # ==========================================
    # POWER-UPS & MAGIE FEATURES
    # ==========================================

    def _evolutie_systeem(self):
        """Evolueer je huisdier naar nieuwe vormen!"""
        naam = self.huisdier["naam"]
        huisdier_type = self.huisdier["type"]

        # Init evolutie data
        if "evolutie" not in self.huisdier:
            self.huisdier["evolutie"] = {
                "niveau": 1,
                "vorm": "basis",
                "krachten": []
            }

        evo = self.huisdier["evolutie"]

        evolutie_paden = {
            "hond": [
                {"niveau": 2, "vorm": "Wolf Pup", "emoji": "🐺", "vereiste_xp": 500, "kracht": "Gehuil"},
                {"niveau": 3, "vorm": "Alpha Wolf", "emoji": "🐺", "vereiste_xp": 1500, "kracht": "Roedel Leider"},
                {"niveau": 4, "vorm": "Legendaire Fenrir", "emoji": "🌟🐺", "vereiste_xp": 5000, "kracht": "Ijs Adem"},
            ],
            "kat": [
                {"niveau": 2, "vorm": "Mystieke Kat", "emoji": "🐱✨", "vereiste_xp": 500, "kracht": "Nacht Zicht"},
                {"niveau": 3, "vorm": "Schaduw Panter", "emoji": "🐆", "vereiste_xp": 1500, "kracht": "Onzichtbaarheid"},
                {"niveau": 4, "vorm": "Sphinx", "emoji": "🦁👑", "vereiste_xp": 5000, "kracht": "Wijsheid"},
            ],
            "vogel": [
                {"niveau": 2, "vorm": "Vuurvogel", "emoji": "🐦‍🔥", "vereiste_xp": 500, "kracht": "Vuur Vleugels"},
                {"niveau": 3, "vorm": "Phoenix", "emoji": "🔥🐦", "vereiste_xp": 1500, "kracht": "Herboren"},
                {"niveau": 4, "vorm": "Hemelse Draak", "emoji": "🐉", "vereiste_xp": 5000, "kracht": "Vliegen"},
            ],
            "default": [
                {"niveau": 2, "vorm": "Verbeterd", "emoji": "⭐", "vereiste_xp": 500, "kracht": "Kracht Boost"},
                {"niveau": 3, "vorm": "Super", "emoji": "🌟", "vereiste_xp": 1500, "kracht": "Super Snelheid"},
                {"niveau": 4, "vorm": "Legendarisch", "emoji": "👑", "vereiste_xp": 5000, "kracht": "Ultieme Kracht"},
            ],
        }

        pad = evolutie_paden.get(huisdier_type, evolutie_paden["default"])

        print("\n" + "=" * 55)
        print(f"  [EVOLUTIE] {naam}'s EVOLUTIE SYSTEEM")
        print("=" * 55)
        print(f"\n  Huidige vorm: {evo['vorm']} (Niveau {evo['niveau']})")
        print(f"  Ervaring: {self.huisdier['ervaring']} XP")
        print(f"  Krachten: {', '.join(evo['krachten']) if evo['krachten'] else 'Geen'}")

        print("\n  Evolutie Pad:")
        for stage in pad:
            if stage["niveau"] <= evo["niveau"]:
                status = "✓ BEREIKT"
            elif self.huisdier["ervaring"] >= stage["vereiste_xp"]:
                status = "→ KLAAR!"
            else:
                status = f"Nodig: {stage['vereiste_xp']} XP"
            print(f"    Nv.{stage['niveau']}: {stage['vorm']} {stage['emoji']} - {status}")
            print(f"         Kracht: {stage['kracht']}")

        print("\n  1. Evolueren (als klaar)")
        print("  0. Terug")

        keuze = input("\n  Keuze: ").strip()

        if keuze == "1":
            for stage in pad:
                if stage["niveau"] == evo["niveau"] + 1:
                    if self.huisdier["ervaring"] >= stage["vereiste_xp"]:
                        evo["niveau"] = stage["niveau"]
                        evo["vorm"] = stage["vorm"]
                        evo["krachten"].append(stage["kracht"])
                        self.huisdier["emoji"] = stage["emoji"]

                        print(f"\n  [EVOLUTIE] {naam} evolueert!")
                        time.sleep(1)
                        print(f"  ✨ {naam} is nu een {stage['vorm']}! ✨")
                        print(f"  Nieuwe kracht: {stage['kracht']}")

                        # Bonussen
                        self.huisdier["geluk"] = 100
                        self.huisdier["energie"] = 100

                        self._voeg_dagboek_toe(f"Geevolueerd naar {stage['vorm']}!")
                        self._maak_foto(f"{naam} evolueerde naar {stage['vorm']}!")
                    else:
                        print(f"\n  [!] Niet genoeg XP! Nodig: {stage['vereiste_xp']}")
                    break
            else:
                print("\n  [!] Maximale evolutie bereikt!")

        self._sla_op()

    def _huisdier_gym(self):
        """Train je huisdier's stats!"""
        naam = self.huisdier["naam"]

        # Init gym data
        if "gym" not in self.huisdier:
            self.huisdier["gym"] = {
                "kracht": 10,
                "snelheid": 10,
                "uithoudingsvermogen": 10,
                "trainingen": 0
            }

        gym = self.huisdier["gym"]

        oefeningen = {
            "1": {"naam": "Hardlopen", "stat": "snelheid", "energie": 2, "bonus": 2},
            "2": {"naam": "Gewichtheffen", "stat": "kracht", "energie": 2, "bonus": 3},
            "3": {"naam": "Zwemmen", "stat": "uithoudingsvermogen", "energie": 2, "bonus": 2},
            "4": {"naam": "Springen", "stat": "snelheid", "energie": 1, "bonus": 1},
            "5": {"naam": "Touwtrekken", "stat": "kracht", "energie": 2, "bonus": 2},
            "6": {"naam": "Yoga", "stat": "uithoudingsvermogen", "energie": 1, "bonus": 1},
        }

        while True:
            totaal_power = gym["kracht"] + gym["snelheid"] + gym["uithoudingsvermogen"]

            print("\n" + "=" * 55)
            print(f"  [GYM] {naam}'s FITNESS CENTER")
            print("=" * 55)
            print(f"\n  💪 Kracht: {gym['kracht']}")
            print(f"  🏃 Snelheid: {gym['snelheid']}")
            print(f"  ❤️ Uithoudingsvermogen: {gym['uithoudingsvermogen']}")
            print(f"  ⚡ Totale Power: {totaal_power}")
            print(f"  🎯 Trainingen: {gym['trainingen']}")
            print(f"\n  Energie: {self.huisdier['energie']}")

            print("\n  Oefeningen:")
            for oid, oef in oefeningen.items():
                print(f"    {oid}. {oef['naam']} (-{oef['energie']} energie, +{oef['bonus']} {oef['stat']})")

            print("  0. Terug")

            keuze = input("\n  Kies oefening: ").strip()

            if keuze == "0":
                break

            if keuze in oefeningen:
                oef = oefeningen[keuze]
                if self.huisdier["energie"] >= oef["energie"]:
                    self.huisdier["energie"] -= oef["energie"]
                    gym[oef["stat"]] += oef["bonus"]
                    gym["trainingen"] += 1

                    print(f"\n  {naam} doet {oef['naam']}!")
                    time.sleep(0.5)
                    print(f"  [+] {oef['stat'].title()}: +{oef['bonus']}")

                    # Bonus XP
                    xp = 10 + (gym["trainingen"] // 10)
                    self.huisdier["ervaring"] += xp
                    print(f"  [XP] +{xp} ervaring")

                    # Achievements
                    if gym["trainingen"] == 10:
                        print("\n  [TROFEE] Eerste 10 trainingen!")
                        self.huisdier["munten"] += 50
                    if gym["trainingen"] == 100:
                        print("\n  [TROFEE] Fitness Fanatiek! +200 munten")
                        self.huisdier["munten"] += 200
                else:
                    print(f"\n  [!] Te moe! Nodig: {oef['energie']} energie")

            self._sla_op()

    def _magie_spreuken(self):
        """Leer en gebruik magische spreuken!"""
        naam = self.huisdier["naam"]
        iq = self.huisdier.get("intelligentie", 0)

        # Init magie data
        if "magie" not in self.huisdier:
            self.huisdier["magie"] = {
                "mana": 50,
                "max_mana": 50,
                "geleerde_spreuken": [],
                "spreuken_gebruikt": 0
            }

        magie = self.huisdier["magie"]

        # Mana regenereert
        magie["mana"] = min(magie["max_mana"], magie["mana"] + 5)

        spreuken = {
            "genezen": {"naam": "Genezing", "mana": 20, "effect": {"gezondheid": 30}, "iq_nodig": 10},
            "energie": {"naam": "Energie Boost", "mana": 15, "effect": {"energie": 25}, "iq_nodig": 5},
            "geluk": {"naam": "Fortuna", "mana": 25, "effect": {"geluk": 20, "munten": 25}, "iq_nodig": 20},
            "wijsheid": {"naam": "Wijsheid", "mana": 30, "effect": {"intelligentie": 5}, "iq_nodig": 30},
            "tijdstop": {"naam": "Tijd Stop", "mana": 40, "effect": {"energie": 50, "honger": 20}, "iq_nodig": 50},
            "transmutatie": {"naam": "Transmutatie", "mana": 35, "effect": {"munten": 100}, "iq_nodig": 40},
        }

        while True:
            print("\n" + "=" * 55)
            print(f"  [MAGIE] {naam}'s SPREUKBOEK")
            print("=" * 55)
            print(f"\n  ✨ Mana: {magie['mana']}/{magie['max_mana']}")
            print(f"  🧠 IQ: {iq}")
            print(f"  📖 Geleerde spreuken: {len(magie['geleerde_spreuken'])}")

            print("\n  Beschikbare spreuken:")
            for i, (sid, sp) in enumerate(spreuken.items(), 1):
                geleerd = "✓" if sid in magie["geleerde_spreuken"] else " "
                kan_leren = "🔓" if iq >= sp["iq_nodig"] else "🔒"
                print(f"    {i}. [{geleerd}] {kan_leren} {sp['naam']} - {sp['mana']} mana")
                print(f"       Effect: {sp['effect']} | IQ nodig: {sp['iq_nodig']}")

            print("\n  1. Spreuk leren")
            print("  2. Spreuk gebruiken")
            print("  3. Mana herstellen (20 munten)")
            print("  0. Terug")

            keuze = input("\n  Keuze: ").strip()

            if keuze == "0":
                break
            elif keuze == "1":
                print("\n  Welke spreuk leren? (nummer)")
                sp_keuze = input("  Keuze: ").strip()
                try:
                    idx = int(sp_keuze) - 1
                    sp_lijst = list(spreuken.items())
                    if 0 <= idx < len(sp_lijst):
                        sp_id, sp_data = sp_lijst[idx]
                        if sp_id in magie["geleerde_spreuken"]:
                            print("\n  [!] Al geleerd!")
                        elif iq < sp_data["iq_nodig"]:
                            print(f"\n  [!] IQ te laag! Nodig: {sp_data['iq_nodig']}")
                        else:
                            magie["geleerde_spreuken"].append(sp_id)
                            print(f"\n  [MAGIE] {sp_data['naam']} geleerd!")
                except (ValueError, IndexError):
                    pass

            elif keuze == "2":
                if not magie["geleerde_spreuken"]:
                    print("\n  [!] Geen spreuken geleerd!")
                    continue

                print("\n  Geleerde spreuken:")
                for i, sp_id in enumerate(magie["geleerde_spreuken"], 1):
                    sp = spreuken[sp_id]
                    print(f"    {i}. {sp['naam']} ({sp['mana']} mana)")

                sp_keuze = input("\n  Gebruik spreuk: ").strip()
                try:
                    idx = int(sp_keuze) - 1
                    if 0 <= idx < len(magie["geleerde_spreuken"]):
                        sp_id = magie["geleerde_spreuken"][idx]
                        sp = spreuken[sp_id]

                        if magie["mana"] >= sp["mana"]:
                            magie["mana"] -= sp["mana"]
                            magie["spreuken_gebruikt"] += 1

                            print(f"\n  ✨ {naam} cast {sp['naam']}! ✨")
                            time.sleep(0.5)

                            for stat, waarde in sp["effect"].items():
                                if stat == "munten":
                                    self.huisdier["munten"] += waarde
                                elif stat == "intelligentie":
                                    self.huisdier["intelligentie"] = self.huisdier.get("intelligentie", 0) + waarde
                                elif stat in self.huisdier:
                                    self.huisdier[stat] = min(100, self.huisdier[stat] + waarde)
                                print(f"  [+] {stat.title()}: +{waarde}")
                        else:
                            print(f"\n  [!] Niet genoeg mana! Nodig: {sp['mana']}")
                except (ValueError, IndexError):
                    pass

            elif keuze == "3":
                if self.huisdier["munten"] >= 20:
                    self.huisdier["munten"] -= 20
                    magie["mana"] = magie["max_mana"]
                    print("\n  [OK] Mana volledig hersteld!")
                else:
                    print("\n  [!] Niet genoeg munten!")

            self._sla_op()

    # ==========================================
    # ENTERTAINMENT FEATURES
    # ==========================================

    def _schatkist_jacht(self):
        """Graaf naar verborgen schatten!"""
        naam = self.huisdier["naam"]

        if self.huisdier["energie"] < 2:
            print(f"\n  [!] {naam} is te moe om te graven!")
            return

        # Init schat data
        if "schatten" not in self.huisdier:
            self.huisdier["schatten"] = {
                "gevonden": 0,
                "zeldzame": [],
                "totaal_waarde": 0
            }

        print("\n" + "=" * 55)
        print(f"  [SCHATKIST] {naam}'s SCHATTENJACHT")
        print("=" * 55)
        print(f"\n  Schatten gevonden: {self.huisdier['schatten']['gevonden']}")
        print(f"  Totale waarde: {self.huisdier['schatten']['totaal_waarde']} munten")

        schatten = [
            {"naam": "Oude munt", "waarde": 5, "kans": 30, "zeldzaam": False},
            {"naam": "Zilveren ring", "waarde": 15, "kans": 20, "zeldzaam": False},
            {"naam": "Gouden ketting", "waarde": 50, "kans": 10, "zeldzaam": False},
            {"naam": "Diamant", "waarde": 100, "kans": 5, "zeldzaam": True},
            {"naam": "Oude kaart", "waarde": 30, "kans": 8, "zeldzaam": False},
            {"naam": "Magische steen", "waarde": 75, "kans": 3, "zeldzaam": True},
            {"naam": "Kroon juweel", "waarde": 200, "kans": 1, "zeldzaam": True},
            {"naam": "Niets", "waarde": 0, "kans": 23, "zeldzaam": False},
        ]

        print("\n  1. Graven (20 energie)")
        print("  2. Zeldzame schatten bekijken")
        print("  0. Terug")

        keuze = input("\n  Keuze: ").strip()

        if keuze == "1":
            self.huisdier["energie"] -= 2

            print(f"\n  {naam} begint te graven...")
            time.sleep(1)

            # Bepaal wat gevonden wordt
            roll = random.randint(1, 100)
            cumulative = 0
            gevonden = None

            for schat in schatten:
                cumulative += schat["kans"]
                if roll <= cumulative:
                    gevonden = schat
                    break

            if gevonden and gevonden["waarde"] > 0:
                print(f"  [SCHAT] {naam} vindt een {gevonden['naam']}!")
                print(f"  Waarde: {gevonden['waarde']} munten!")

                self.huisdier["munten"] += gevonden["waarde"]
                self.huisdier["schatten"]["gevonden"] += 1
                self.huisdier["schatten"]["totaal_waarde"] += gevonden["waarde"]

                if gevonden["zeldzaam"]:
                    print("  ⭐ ZELDZAME VONDST! ⭐")
                    if gevonden["naam"] not in self.huisdier["schatten"]["zeldzame"]:
                        self.huisdier["schatten"]["zeldzame"].append(gevonden["naam"])
                    self.huisdier["ervaring"] += 50

                self._voeg_dagboek_toe(f"Schat gevonden: {gevonden['naam']}")
            else:
                print(f"  {naam} vindt niets... Probeer opnieuw!")

            self._sla_op()

        elif keuze == "2":
            print("\n  Zeldzame schatten collectie:")
            if self.huisdier["schatten"]["zeldzame"]:
                for schat in self.huisdier["schatten"]["zeldzame"]:
                    print(f"    ⭐ {schat}")
            else:
                print("    (nog geen zeldzame schatten)")

    def _huisdier_restaurant(self):
        """Run je eigen restaurant!"""
        naam = self.huisdier["naam"]

        # Init restaurant data
        if "restaurant" not in self.huisdier:
            self.huisdier["restaurant"] = {
                "naam": f"{naam}'s Bistro",
                "niveau": 1,
                "reputatie": 0,
                "klanten_bediend": 0,
                "inkomsten": 0
            }

        rest = self.huisdier["restaurant"]

        gerechten = {
            1: [{"naam": "Broodje", "prijs": 5, "tijd": 1}],
            2: [{"naam": "Salade", "prijs": 10, "tijd": 2}, {"naam": "Soep", "prijs": 8, "tijd": 1}],
            3: [{"naam": "Pasta", "prijs": 20, "tijd": 3}, {"naam": "Pizza", "prijs": 25, "tijd": 4}],
            4: [{"naam": "Steak", "prijs": 40, "tijd": 5}, {"naam": "Vis", "prijs": 35, "tijd": 4}],
            5: [{"naam": "Chef's Special", "prijs": 100, "tijd": 8}],
        }

        while True:
            print("\n" + "=" * 55)
            print(f"  [RESTAURANT] {rest['naam']}")
            print("=" * 55)
            print(f"\n  ⭐ Niveau: {rest['niveau']}")
            print(f"  👥 Klanten bediend: {rest['klanten_bediend']}")
            print(f"  💰 Totale inkomsten: {rest['inkomsten']} munten")
            print(f"  📈 Reputatie: {rest['reputatie']}")

            beschikbare_gerechten = []
            for niv in range(1, rest["niveau"] + 1):
                beschikbare_gerechten.extend(gerechten.get(niv, []))

            print("\n  Menu:")
            for i, g in enumerate(beschikbare_gerechten, 1):
                print(f"    {i}. {g['naam']} - {g['prijs']} munten")

            print("\n  1. Klant bedienen")
            print("  2. Restaurant upgraden (100 munten)")
            print("  3. Naam wijzigen")
            print("  0. Terug")

            keuze = input("\n  Keuze: ").strip()

            if keuze == "0":
                break
            elif keuze == "1":
                if self.huisdier["energie"] < 1:
                    print(f"\n  [!] {naam} is te moe!")
                    continue

                self.huisdier["energie"] -= 1

                # Random klant
                klant_namen = ["Jan", "Lisa", "Piet", "Anna", "Tom", "Sara", "Max", "Emma"]
                klant = random.choice(klant_namen)

                print(f"\n  👤 {klant} komt binnen!")

                # Klant bestelt
                gerecht = random.choice(beschikbare_gerechten)
                print(f"  {klant}: 'Ik wil graag de {gerecht['naam']}!'")

                time.sleep(0.5)
                print(f"\n  {naam} bereidt {gerecht['naam']} voor...")
                time.sleep(0.5)

                # Succes kans gebaseerd op energie en reputatie
                succes_kans = 70 + (rest["reputatie"] // 10)
                if random.randint(1, 100) <= succes_kans:
                    print(f"  [OK] {klant}: 'Heerlijk! Dank je!'")
                    fooi = gerecht["prijs"] // 3
                    totaal = gerecht["prijs"] + fooi

                    self.huisdier["munten"] += totaal
                    rest["klanten_bediend"] += 1
                    rest["inkomsten"] += totaal
                    rest["reputatie"] += 1

                    print(f"  [MUNT] +{gerecht['prijs']} + {fooi} fooi = {totaal} munten!")
                else:
                    print(f"  [X] {klant}: 'Dit is niet goed...'")
                    rest["reputatie"] = max(0, rest["reputatie"] - 2)
                    print(f"  [-] Reputatie -2")

            elif keuze == "2":
                if rest["niveau"] >= 5:
                    print("\n  [!] Restaurant is al maximaal niveau!")
                elif self.huisdier["munten"] >= 100:
                    self.huisdier["munten"] -= 100
                    rest["niveau"] += 1
                    print(f"\n  [UP] Restaurant nu niveau {rest['niveau']}!")
                    print("  Nieuwe gerechten beschikbaar!")
                else:
                    print("\n  [!] Niet genoeg munten!")

            elif keuze == "3":
                nieuwe_naam = input("  Nieuwe naam: ").strip()
                if nieuwe_naam:
                    rest["naam"] = nieuwe_naam
                    print(f"\n  [OK] Restaurant heet nu: {nieuwe_naam}")

            self._sla_op()

    def _muziek_studio(self):
        """Maak en luister naar muziek!"""
        naam = self.huisdier["naam"]

        # Init muziek data
        if "muziek" not in self.huisdier:
            self.huisdier["muziek"] = {
                "nummers_gemaakt": [],
                "favorieten": [],
                "luister_tijd": 0
            }

        muziek = self.huisdier["muziek"]

        genres = ["Pop", "Rock", "Jazz", "Klassiek", "Electronic", "Hip-Hop", "Country", "Reggae"]
        stemmingen = ["Vrolijk", "Rustig", "Energiek", "Romantisch", "Mysterieus", "Episch"]

        while True:
            print("\n" + "=" * 55)
            print(f"  [MUZIEK] {naam}'s STUDIO")
            print("=" * 55)
            print(f"\n  🎵 Nummers gemaakt: {len(muziek['nummers_gemaakt'])}")
            print(f"  ⏱️ Luister tijd: {muziek['luister_tijd']} min")

            print("\n  1. Nummer maken (15 energie)")
            print("  2. Muziek luisteren (+geluk)")
            print("  3. Mijn nummers")
            print("  0. Terug")

            keuze = input("\n  Keuze: ").strip()

            if keuze == "0":
                break
            elif keuze == "1":
                if self.huisdier["energie"] < 2:
                    print(f"\n  [!] {naam} is te moe!")
                    continue

                self.huisdier["energie"] -= 2

                print("\n  🎹 Kies een genre:")
                for i, g in enumerate(genres, 1):
                    print(f"    {i}. {g}")

                genre_keuze = input("\n  Genre: ").strip()
                try:
                    genre = genres[int(genre_keuze) - 1]
                except (ValueError, IndexError):
                    genre = random.choice(genres)

                stemming = random.choice(stemmingen)

                print(f"\n  {naam} componeert een {stemming.lower()} {genre} nummer...")
                time.sleep(1)

                # Genereer naam
                woorden1 = ["Midnight", "Golden", "Electric", "Dancing", "Dreaming", "Flying"]
                woorden2 = ["Stars", "Heart", "Waves", "Dreams", "Light", "Soul"]
                nummer_naam = f"{random.choice(woorden1)} {random.choice(woorden2)}"

                nummer = {
                    "naam": nummer_naam,
                    "genre": genre,
                    "stemming": stemming,
                    "datum": datetime.now().strftime("%Y-%m-%d")
                }
                muziek["nummers_gemaakt"].append(nummer)

                print(f"\n  [MUZIEK] '{nummer_naam}' is klaar!")
                print(f"  Genre: {genre} | Stemming: {stemming}")

                self.huisdier["geluk"] = min(100, self.huisdier["geluk"] + 10)
                self.huisdier["ervaring"] += 20

            elif keuze == "2":
                print(f"\n  {naam} luistert naar muziek...")
                time.sleep(0.5)

                # Mood boost
                self.huisdier["geluk"] = min(100, self.huisdier["geluk"] + 15)
                self.huisdier["energie"] = min(100, self.huisdier["energie"] + 5)
                muziek["luister_tijd"] += 5

                print("  🎵 ♪ ♫ ♪ ♫")
                print(f"\n  [HAPPY] +15 geluk!")
                print(f"  [ENERGIE] +5 energie!")

            elif keuze == "3":
                if muziek["nummers_gemaakt"]:
                    print("\n  Jouw nummers:")
                    for i, n in enumerate(muziek["nummers_gemaakt"][-10:], 1):
                        print(f"    {i}. '{n['naam']}' - {n['genre']} ({n['stemming']})")
                else:
                    print("\n  Nog geen nummers gemaakt!")

            self._sla_op()

    def _arcade_hal(self):
        """Meer mini-games in de arcade!"""
        naam = self.huisdier["naam"]

        # Init arcade data
        if "arcade" not in self.huisdier:
            self.huisdier["arcade"] = {
                "highscores": {},
                "tokens": 10,
                "totaal_gespeeld": 0
            }

        arcade = self.huisdier["arcade"]

        games = {
            "1": {"naam": "Flappy Bird", "tokens": 2, "type": "timing"},
            "2": {"naam": "Snake", "tokens": 2, "type": "score"},
            "3": {"naam": "Tetris", "tokens": 3, "type": "score"},
            "4": {"naam": "Pac-Man", "tokens": 3, "type": "score"},
            "5": {"naam": "Space Invaders", "tokens": 4, "type": "score"},
        }

        while True:
            print("\n" + "=" * 55)
            print(f"  [ARCADE] ARCADE HAL")
            print("=" * 55)
            print(f"\n  🎮 Tokens: {arcade['tokens']}")
            print(f"  🕹️ Games gespeeld: {arcade['totaal_gespeeld']}")

            print("\n  Games:")
            for gid, game in games.items():
                hs = arcade["highscores"].get(game["naam"], 0)
                print(f"    {gid}. {game['naam']} ({game['tokens']} tokens) - Highscore: {hs}")

            print("\n  a. Tokens kopen (10 munten = 5 tokens)")
            print("  0. Terug")

            keuze = input("\n  Kies game: ").strip().lower()

            if keuze == "0":
                break
            elif keuze == "a":
                if self.huisdier["munten"] >= 10:
                    self.huisdier["munten"] -= 10
                    arcade["tokens"] += 5
                    print("\n  [OK] +5 tokens gekocht!")
                else:
                    print("\n  [!] Niet genoeg munten!")

            elif keuze in games:
                game = games[keuze]
                if arcade["tokens"] < game["tokens"]:
                    print(f"\n  [!] Niet genoeg tokens! Nodig: {game['tokens']}")
                    continue

                arcade["tokens"] -= game["tokens"]
                arcade["totaal_gespeeld"] += 1

                print(f"\n  🎮 {naam} speelt {game['naam']}!")
                time.sleep(0.5)

                # Simuleer game score
                base_score = random.randint(100, 500)
                skill_bonus = self.huisdier.get("intelligentie", 0) + (arcade["totaal_gespeeld"] * 2)
                score = base_score + skill_bonus

                print(f"  Score: {score}!")

                if score > arcade["highscores"].get(game["naam"], 0):
                    print("  🏆 NIEUWE HIGHSCORE!")
                    arcade["highscores"][game["naam"]] = score
                    bonus = 20
                else:
                    bonus = 5

                self.huisdier["munten"] += bonus
                print(f"  [MUNT] +{bonus} munten!")

            self._sla_op()

    # ==========================================
    # SPECIALE AVONTUREN FEATURES
    # ==========================================

    def _tijdreizen(self):
        """Reis naar verschillende tijdperken!"""
        naam = self.huisdier["naam"]

        if self.huisdier["energie"] < 3:
            print(f"\n  [!] {naam} heeft 30 energie nodig om te tijdreizen!")
            return

        # Init tijdreis data
        if "tijdreizen" not in self.huisdier:
            self.huisdier["tijdreizen"] = {
                "bezochte_tijdperken": [],
                "artefacten": [],
                "totaal_reizen": 0
            }

        tijdperken = {
            "1": {
                "naam": "Dinosaurus Era",
                "emoji": "🦖",
                "jaar": "65 miljoen v.Chr.",
                "gevaar": 3,
                "artefact": "Dino Tand",
                "beschrijving": "Gigantische reptielen heersen over de aarde!"
            },
            "2": {
                "naam": "Egypte",
                "emoji": "🏺",
                "jaar": "3000 v.Chr.",
                "gevaar": 2,
                "artefact": "Scarabee Amulet",
                "beschrijving": "Piramides worden gebouwd door farao's!"
            },
            "3": {
                "naam": "Middeleeuwen",
                "emoji": "🏰",
                "jaar": "1200 n.Chr.",
                "gevaar": 2,
                "artefact": "Ridder Helm",
                "beschrijving": "Ridders en kastelen bepalen het landschap!"
            },
            "4": {
                "naam": "Piratentijd",
                "emoji": "🏴‍☠️",
                "jaar": "1700 n.Chr.",
                "gevaar": 3,
                "artefact": "Piraten Kompas",
                "beschrijving": "Zeerovers bevaren de oceanen!"
            },
            "5": {
                "naam": "Toekomst",
                "emoji": "🤖",
                "jaar": "2500 n.Chr.",
                "gevaar": 2,
                "artefact": "Hologram Device",
                "beschrijving": "Robots en ruimteschepen overal!"
            },
        }

        print("\n" + "=" * 55)
        print(f"  [TIJD] {naam}'s TIJDMACHINE")
        print("=" * 55)
        print(f"\n  Reizen gemaakt: {self.huisdier['tijdreizen']['totaal_reizen']}")
        print(f"  Artefacten: {len(self.huisdier['tijdreizen']['artefacten'])}")

        print("\n  Tijdperken:")
        for tid, tp in tijdperken.items():
            bezocht = "✓" if tp["naam"] in self.huisdier["tijdreizen"]["bezochte_tijdperken"] else " "
            print(f"    {tid}. [{bezocht}] {tp['emoji']} {tp['naam']} ({tp['jaar']})")
            print(f"       {tp['beschrijving']}")

        print("\n  0. Terug")

        keuze = input("\n  Reis naar: ").strip()

        if keuze == "0" or keuze not in tijdperken:
            return

        tp = tijdperken[keuze]
        self.huisdier["energie"] -= 3

        print(f"\n  ⚡ Tijdmachine activeert...")
        time.sleep(1)
        print(f"  🌀 Reizen naar {tp['jaar']}...")
        time.sleep(1)
        print(f"\n  {tp['emoji']} Welkom in {tp['naam']}!")
        print(f"  {tp['beschrijving']}")

        # Mark als bezocht
        if tp["naam"] not in self.huisdier["tijdreizen"]["bezochte_tijdperken"]:
            self.huisdier["tijdreizen"]["bezochte_tijdperken"].append(tp["naam"])
            print(f"\n  [NIEUW] Nieuw tijdperk ontdekt!")

        self.huisdier["tijdreizen"]["totaal_reizen"] += 1

        # Avontuur in het tijdperk
        succes_kans = 70 - (tp["gevaar"] * 10) + (self.huisdier.get("gym", {}).get("kracht", 0))

        if random.randint(1, 100) <= succes_kans:
            print(f"\n  [AVONTUUR] {naam} heeft een geweldig avontuur!")

            if tp["artefact"] not in self.huisdier["tijdreizen"]["artefacten"]:
                self.huisdier["tijdreizen"]["artefacten"].append(tp["artefact"])
                print(f"  [ARTEFACT] {tp['artefact']} gevonden!")
                self.huisdier["munten"] += 75
            else:
                self.huisdier["munten"] += 40
                print(f"  [MUNT] +40 munten!")

            self.huisdier["ervaring"] += 50
        else:
            print(f"\n  [!] {naam} moest snel terug! Te gevaarlijk!")
            self.huisdier["gezondheid"] = max(50, self.huisdier["gezondheid"] - 10)

        print(f"\n  ⚡ Terug naar het heden...")
        self._voeg_dagboek_toe(f"Tijdreis naar {tp['naam']}!")
        self._sla_op()

    def _magische_tuin(self):
        """Onderhoud een magische tuin met speciale planten!"""
        naam = self.huisdier["naam"]

        # Init tuin data
        if "magische_tuin" not in self.huisdier:
            self.huisdier["magische_tuin"] = {
                "planten": [],
                "decoraties": [],
                "magie_niveau": 1,
                "bezoekers": 0
            }

        tuin = self.huisdier["magische_tuin"]

        magische_planten = {
            "1": {"naam": "Lichtbloem", "prijs": 30, "effect": "energie", "bonus": 10, "groeitijd": 2},
            "2": {"naam": "Gelukskruid", "prijs": 40, "effect": "geluk", "bonus": 15, "groeitijd": 3},
            "3": {"naam": "Wijsheidsmos", "prijs": 50, "effect": "intelligentie", "bonus": 5, "groeitijd": 5},
            "4": {"naam": "Gouden Roos", "prijs": 75, "effect": "munten", "bonus": 25, "groeitijd": 4},
            "5": {"naam": "Levensblad", "prijs": 60, "effect": "gezondheid", "bonus": 20, "groeitijd": 3},
        }

        decoraties = {
            "fontein": {"prijs": 100, "magie": 5},
            "standbeeld": {"prijs": 150, "magie": 10},
            "vijver": {"prijs": 80, "magie": 3},
            "lantaarn": {"prijs": 50, "magie": 2},
        }

        # Update planten
        nu = datetime.now()
        for plant in tuin["planten"]:
            if not plant.get("volgroeid", False):
                geplant = datetime.fromisoformat(plant["geplant"])
                groeitijd = magische_planten[plant["type"]]["groeitijd"]
                if (nu - geplant).seconds / 60 >= groeitijd:
                    plant["volgroeid"] = True

        while True:
            print("\n" + "=" * 55)
            print(f"  [TUIN] {naam}'s MAGISCHE TUIN")
            print("=" * 55)
            print(f"\n  ✨ Magie niveau: {tuin['magie_niveau']}")
            print(f"  🌱 Planten: {len(tuin['planten'])}")
            print(f"  🏛️ Decoraties: {len(tuin['decoraties'])}")

            print("\n  Geplante planten:")
            if tuin["planten"]:
                for i, p in enumerate(tuin["planten"], 1):
                    plant_data = magische_planten[p["type"]]
                    status = "🌸 Bloeit!" if p.get("volgroeid") else "🌱 Groeit..."
                    print(f"    {i}. {plant_data['naam']} - {status}")
            else:
                print("    (geen planten)")

            print("\n  1. Plant planten")
            print("  2. Oogsten")
            print("  3. Decoratie plaatsen")
            print("  4. Tuin water geven (+magie)")
            print("  0. Terug")

            keuze = input("\n  Keuze: ").strip()

            if keuze == "0":
                break
            elif keuze == "1":
                print("\n  Magische planten:")
                for pid, plant in magische_planten.items():
                    print(f"    {pid}. {plant['naam']} - {plant['prijs']} munten")
                    print(f"       Effect: +{plant['bonus']} {plant['effect']}")

                plant_keuze = input("\n  Kies plant: ").strip()
                if plant_keuze in magische_planten:
                    plant = magische_planten[plant_keuze]
                    if self.huisdier["munten"] >= plant["prijs"]:
                        self.huisdier["munten"] -= plant["prijs"]
                        tuin["planten"].append({
                            "type": plant_keuze,
                            "geplant": datetime.now().isoformat(),
                            "volgroeid": False
                        })
                        print(f"\n  [OK] {plant['naam']} geplant!")
                    else:
                        print("\n  [!] Niet genoeg munten!")

            elif keuze == "2":
                geoogst = []
                for plant in tuin["planten"][:]:
                    if plant.get("volgroeid"):
                        plant_data = magische_planten[plant["type"]]
                        stat = plant_data["effect"]
                        bonus = plant_data["bonus"]

                        if stat == "munten":
                            self.huisdier["munten"] += bonus
                        elif stat == "intelligentie":
                            self.huisdier["intelligentie"] = self.huisdier.get("intelligentie", 0) + bonus
                        elif stat in self.huisdier:
                            self.huisdier[stat] = min(100, self.huisdier[stat] + bonus)

                        geoogst.append(f"{plant_data['naam']} (+{bonus} {stat})")
                        tuin["planten"].remove(plant)

                if geoogst:
                    print(f"\n  [OOGST] Geoogst:")
                    for g in geoogst:
                        print(f"    - {g}")
                else:
                    print("\n  [!] Geen volgroeide planten!")

            elif keuze == "3":
                print("\n  Decoraties:")
                for did, dec in decoraties.items():
                    owned = "✓" if did in tuin["decoraties"] else " "
                    print(f"    [{owned}] {did.title()} - {dec['prijs']} munten (+{dec['magie']} magie)")

                dec_keuze = input("\n  Kies decoratie: ").strip().lower()
                if dec_keuze in decoraties and dec_keuze not in tuin["decoraties"]:
                    dec = decoraties[dec_keuze]
                    if self.huisdier["munten"] >= dec["prijs"]:
                        self.huisdier["munten"] -= dec["prijs"]
                        tuin["decoraties"].append(dec_keuze)
                        tuin["magie_niveau"] += dec["magie"]
                        print(f"\n  [OK] {dec_keuze.title()} geplaatst!")
                        print(f"  [+] Magie niveau: +{dec['magie']}")
                    else:
                        print("\n  [!] Niet genoeg munten!")

            elif keuze == "4":
                tuin["magie_niveau"] += 1
                self.huisdier["geluk"] = min(100, self.huisdier["geluk"] + 5)
                print(f"\n  {naam} geeft de tuin water...")
                print(f"  [+] Magie niveau: +1")
                print(f"  [HAPPY] +5 geluk")

            self._sla_op()

    def _geheime_missies(self):
        """Geheime spion missies voor grote beloningen!"""
        naam = self.huisdier["naam"]

        # Init spion data
        if "spion" not in self.huisdier:
            self.huisdier["spion"] = {
                "rang": "Rookie",
                "missies_voltooid": 0,
                "gadgets": [],
                "geheime_punten": 0
            }

        spion = self.huisdier["spion"]

        rangen = {
            0: "Rookie",
            5: "Agent",
            15: "Senior Agent",
            30: "Elite Agent",
            50: "Legendarisch Spion"
        }

        # Update rang
        for punten, rang in sorted(rangen.items(), reverse=True):
            if spion["missies_voltooid"] >= punten:
                spion["rang"] = rang
                break

        missies = [
            {"naam": "Geheime Documenten Ophalen", "moeilijkheid": 1, "beloning": 50, "xp": 30},
            {"naam": "Verdachte Volgen", "moeilijkheid": 2, "beloning": 80, "xp": 50},
            {"naam": "Code Kraken", "moeilijkheid": 2, "beloning": 100, "xp": 60},
            {"naam": "Undercover in Restaurant", "moeilijkheid": 3, "beloning": 150, "xp": 80},
            {"naam": "Schurk Vangen", "moeilijkheid": 4, "beloning": 250, "xp": 120},
            {"naam": "Wereld Redden", "moeilijkheid": 5, "beloning": 500, "xp": 200},
        ]

        print("\n" + "=" * 55)
        print(f"  [GEHEIM] TOP SECRET - SPION HQ")
        print("=" * 55)
        print(f"\n  Agent: {naam}")
        print(f"  🎖️ Rang: {spion['rang']}")
        print(f"  📋 Missies voltooid: {spion['missies_voltooid']}")
        print(f"  🔧 Gadgets: {len(spion['gadgets'])}")

        print("\n  Beschikbare missies:")
        for i, m in enumerate(missies, 1):
            sterren = "⭐" * m["moeilijkheid"]
            print(f"    {i}. {m['naam']}")
            print(f"       Moeilijkheid: {sterren} | Beloning: {m['beloning']} munten")

        print("\n  1. Missie starten")
        print("  2. Gadget kopen")
        print("  0. Terug")

        keuze = input("\n  Keuze: ").strip()

        if keuze == "1":
            if self.huisdier["energie"] < 3:
                print(f"\n  [!] {naam} heeft 25 energie nodig!")
                return

            missie_keuze = input("\n  Kies missie (1-6): ").strip()
            try:
                missie = missies[int(missie_keuze) - 1]
            except (ValueError, IndexError):
                return

            self.huisdier["energie"] -= 3

            print(f"\n  [MISSIE] {missie['naam']} gestart...")
            time.sleep(1)

            # Succes berekening
            basis_kans = 80 - (missie["moeilijkheid"] * 10)
            gadget_bonus = len(spion["gadgets"]) * 5
            iq_bonus = self.huisdier.get("intelligentie", 0) // 5
            gym_bonus = self.huisdier.get("gym", {}).get("snelheid", 0) // 5

            succes_kans = basis_kans + gadget_bonus + iq_bonus + gym_bonus

            print(f"  Succes kans: {min(95, succes_kans)}%")
            time.sleep(0.5)

            if random.randint(1, 100) <= succes_kans:
                print(f"\n  [SUCCESS] Missie geslaagd!")
                print(f"  🎵 Gefeliciteerd, Agent {naam}!")

                self.huisdier["munten"] += missie["beloning"]
                self.huisdier["ervaring"] += missie["xp"]
                spion["missies_voltooid"] += 1
                spion["geheime_punten"] += missie["moeilijkheid"]

                print(f"  [MUNT] +{missie['beloning']} munten!")
                print(f"  [XP] +{missie['xp']} ervaring!")

                self._voeg_dagboek_toe(f"Geheime missie voltooid: {missie['naam']}")
            else:
                print(f"\n  [FAILED] Missie mislukt...")
                print(f"  {naam} moest vluchten!")
                self.huisdier["gezondheid"] = max(50, self.huisdier["gezondheid"] - 15)

            self._sla_op()

        elif keuze == "2":
            gadgets = {
                "invisibility_cloak": {"naam": "Onzichtbaarheidsmantel", "prijs": 200},
                "grappling_hook": {"naam": "Klimhaak", "prijs": 100},
                "night_vision": {"naam": "Nachtkijker", "prijs": 150},
                "smoke_bomb": {"naam": "Rookbom", "prijs": 75},
            }

            print("\n  Gadgets winkel:")
            for gid, g in gadgets.items():
                owned = "✓" if gid in spion["gadgets"] else " "
                print(f"    [{owned}] {g['naam']} - {g['prijs']} munten")

            gadget_keuze = input("\n  Koop gadget (naam): ").strip().lower().replace(" ", "_")

            for gid, g in gadgets.items():
                if gadget_keuze in gid and gid not in spion["gadgets"]:
                    if self.huisdier["munten"] >= g["prijs"]:
                        self.huisdier["munten"] -= g["prijs"]
                        spion["gadgets"].append(gid)
                        print(f"\n  [OK] {g['naam']} gekocht!")
                    else:
                        print("\n  [!] Niet genoeg munten!")
                    break

    # ==================== AI POWERED FEATURES ====================

    def _ai_pet_chat(self):
        """Praat met je huisdier via AI - volledig gepersonaliseerd!"""
        naam = self.huisdier["naam"]
        geluid = self.huisdier["geluid"]
        emoji = self.huisdier["emoji"]
        huisdier_type = self.huisdier["type"]
        personality = self._get_personality()
        iq = self.huisdier.get("intelligentie", 0)

        # Initialiseer Learning System voor deze chat sessie
        self._init_learning()

        print("\n" + "=" * 60)
        print(f"  {emoji} PRAAT MET {naam.upper()}! {emoji}")
        print("=" * 60)
        print(f"\n  {naam} de {huisdier_type} kijkt je verwachtingsvol aan...")
        print(f"  {geluid}")
        print(f"\n  Persoonlijkheid: {personality['karakter']}")
        print(f"  IQ: {iq} | Spreekstijl: {personality['spreekstijl']}")
        if self.learning:
            print(f"  [LEARN] Self-Learning actief!")
        print("\n  Typ 'stop' om te stoppen.\n")

        # Voeg herinnering toe
        self._ai_add_memory("chat", f"Chat sessie gestart met baasje")

        gesprek_count = 0
        while True:
            user_input = input(f"  Jij: ").strip()

            if user_input.lower() in ["stop", "exit", "quit", ""]:
                print(f"\n  {naam}: {geluid} (Tot ziens!)")
                break

            gesprek_count += 1

            # LEARNING: Check voor cached response (instant antwoord!)
            response = None
            if self.learning:
                cached = self.learning.get_cached_response(user_input)
                if cached:
                    response = cached
                    print(f"  {naam}: {response} [CACHED]")
                    print()
                    continue

            # Genereer AI response met persoonlijkheid
            context = f"Gebruiker zegt: '{user_input}'. Reageer als {naam} de {huisdier_type}."

            # Voeg recente herinneringen toe voor context
            memories = self._ai_recall_memory()
            if memories:
                recent = memories[-1]["beschrijving"]
                context += f" Je herinnert je: {recent}"

            response = self._ai_generate_response(context)

            print(f"  {naam}: {response}")
            print()

            # LEARNING: Log interactie voor learning
            if self.learning:
                learning_context = {
                    "geluk": self.huisdier.get("geluk", 50),
                    "energie": self.huisdier.get("energie", 50),
                    "iq": iq,
                    "huisdier_type": huisdier_type,
                }
                self.learning.log_chat(user_input, response, learning_context)

            # Voeg herinnering toe van dit gesprek
            if gesprek_count % 3 == 0:  # Elke 3 berichten
                self._ai_add_memory("chat", f"Praatte over: {user_input[:50]}")

            # Stat updates
            self.huisdier["geluk"] = min(100, self.huisdier["geluk"] + 2)
            if gesprek_count % 5 == 0:
                self.huisdier["intelligentie"] = iq + 1
                print(f"  [IQ] {naam} wordt slimmer door het gesprek! +1 IQ")

        # Resultaten
        print("\n" + "=" * 60)
        print("  [CHAT] Gesprek beëindigd!")
        print("=" * 60)

        intel_bonus = gesprek_count // 3
        xp_bonus = gesprek_count * 5

        print(f"\n  Gesprek statistieken:")
        print(f"    [CHAT] Berichten uitgewisseld: {gesprek_count}")
        print(f"    [IQ] Intelligentie: +{intel_bonus}")
        print(f"    [XP] Ervaring: +{xp_bonus}")

        self.huisdier["intelligentie"] = self.huisdier.get("intelligentie", 0) + intel_bonus
        self.huisdier["ervaring"] += xp_bonus

        self._ai_add_memory("chat", f"Gezellig gesprek gehad ({gesprek_count} berichten)")
        self._sla_op()

    def _ai_memory_lane(self):
        """Bekijk de herinneringen van je huisdier met AI context."""
        naam = self.huisdier["naam"]
        emoji = self.huisdier["emoji"]
        memories = self.huisdier.get("ai_memory", [])

        print("\n" + "=" * 60)
        print(f"  {emoji} {naam}'s HERINNERINGEN {emoji}")
        print("=" * 60)

        if not memories:
            print(f"\n  {naam} heeft nog geen herinneringen opgebouwd.")
            print("  Speel, leer en praat om herinneringen te maken!")
            return

        print(f"\n  {naam} heeft {len(memories)} herinneringen:\n")

        # Groepeer herinneringen per type
        by_type = {}
        for m in memories:
            t = m.get("type", "algemeen")
            if t not in by_type:
                by_type[t] = []
            by_type[t].append(m)

        type_emojis = {
            "voeren": "🍖",
            "spelen": "🎾",
            "slapen": "😴",
            "leren": "📚",
            "chat": "💬",
            "avontuur": "🗺️",
            "trick": "🎪",
            "game": "🎮",
            "algemeen": "📝",
        }

        for mem_type, mems in by_type.items():
            emoji_type = type_emojis.get(mem_type, "📝")
            print(f"  {emoji_type} {mem_type.upper()} ({len(mems)} herinneringen)")
            for m in mems[-3:]:  # Laatste 3 per type
                datum = m["datum"][:10]
                print(f"      [{datum}] {m['beschrijving'][:50]}")
            print()

        # AI samenvatting van herinneringen
        print("  " + "-" * 50)
        print("  [AI] Samenvatting van herinneringen:")

        try:
            claude_chat = _get_claude_chat()
            if claude_chat and len(memories) >= 3:
                recent_5 = [m["beschrijving"] for m in memories[-5:]]
                context = f"Maak een korte, warme samenvatting (2 zinnen) van deze herinneringen van {naam}: {', '.join(recent_5)}"
                summary = self._ai_generate_response(context)
                print(f"  {summary}")
            else:
                # Fallback
                if len(memories) >= 5:
                    print(f"  {naam} heeft mooie herinneringen opgebouwd!")
                    print(f"  De afgelopen tijd was vol met {list(by_type.keys())[0]}.")
                else:
                    print(f"  {naam} begint net herinneringen te maken.")
        except Exception as e:
            logger.debug("AI memory summary generation failed: %s", e)
            print(f"  {naam} koestert alle herinneringen diep in het hart.")

        # Optie om favoriete herinnering te markeren
        print("\n  " + "-" * 50)
        print("  [TIP] Blijf spelen om meer herinneringen te maken!")

    def _ai_enhanced_sleep(self):
        """AI-enhanced slapen met gegenereerde dromen."""
        naam = self.huisdier["naam"]
        emoji = self.huisdier["emoji"]

        print(f"\n  {emoji} {naam} valt in een diepe slaap...")
        time.sleep(1)

        # Genereer AI droom
        dream = self._ai_generate_dream()

        print("\n  " + "~" * 50)
        print("  ✨ DROOM ✨")
        print("  " + "~" * 50)
        print(f"\n  {dream}")
        print("\n  " + "~" * 50)

        # Voeg droom toe aan herinneringen
        self._ai_add_memory("slapen", f"Droomde: {dream[:50]}...")

        # Kans op extra IQ door droom
        if random.random() < 0.4:  # 40% kans
            self.huisdier["intelligentie"] = self.huisdier.get("intelligentie", 0) + 1
            print(f"\n  [LAMP] {naam} leerde iets in de droom! +1 IQ")

    def _auto_mode(self):
        """Automatische leer- en slaapmodus - huisdier leert en rust zelfstandig!"""
        naam = self.huisdier["naam"]
        geluid = self.huisdier["geluid"]
        emoji = self.huisdier["emoji"]

        print("\n" + "=" * 60)
        print(f"  {emoji} AUTO LEARN & SLEEP MODE {emoji}")
        print("=" * 60)
        print(f"\n  {naam} gaat automatisch leren en rusten!")
        print("  Dit simuleert meerdere leer- en slaapsessies.")
        print("\n  Kies een modus:")
        print("  1. Korte sessie (5 cycli) - 10 munten")
        print("  2. Medium sessie (10 cycli) - 18 munten")
        print("  3. Lange sessie (3 cycli) - 30 munten")
        print("  4. Nacht modus (50 cycli) - 60 munten")
        print("  5. AI Turbo Learn (100 cycli + AI) - 100 munten")
        print("  0. Terug")

        keuze = input("\n  Keuze: ").strip()

        sessie_opties = {
            "1": {"cycli": 5, "kosten": 10, "naam": "Korte"},
            "2": {"cycli": 10, "kosten": 18, "naam": "Medium"},
            "3": {"cycli": 3, "kosten": 30, "naam": "Lange"},
            "4": {"cycli": 50, "kosten": 60, "naam": "Nacht"},
            "5": {"cycli": 100, "kosten": 100, "naam": "AI Turbo"},
        }

        if keuze not in sessie_opties:
            return

        sessie = sessie_opties[keuze]

        if self.huisdier["munten"] < sessie["kosten"]:
            print(f"\n  [!] Niet genoeg munten! (Nodig: {sessie['kosten']})")
            return

        self.huisdier["munten"] -= sessie["kosten"]

        print(f"\n  {naam} start {sessie['naam']} Auto Mode...")
        print(f"  [MUNT] -{sessie['kosten']} munten")
        print("\n  " + "-" * 50)
        time.sleep(0.5)

        # Statistieken bijhouden
        totaal_energie = 0
        totaal_intel = 0
        totaal_xp = 0
        totaal_geluk = 0
        feiten_geleerd = 0
        slaap_cycli = 0
        leer_cycli = 0

        # Laad permanente kennis
        permanente_kennis = self._laad_permanente_kennis()

        # Ingebouwde feiten voor auto-learn
        auto_feiten = [
            "Machine Learning is een subset van AI die patronen leert uit data",
            "Neural networks bestaan uit lagen van kunstmatige neuronen",
            "Backpropagation is het algoritme waarmee neural networks leren",
            "REST APIs gebruiken HTTP methodes voor communicatie",
            "Embeddings zijn numerieke vectoren die betekenis representeren",
            "Cosine similarity meet gelijkenis tussen vectoren",
            "Supervised learning gebruikt gelabelde trainingsdata",
            "Unsupervised learning vindt patronen zonder labels",
            "Transfer learning hergebruikt voorgetrainde modellen",
            "RAG combineert retrieval met generatie voor betere antwoorden",
            "Transformers gebruiken attention voor parallelle verwerking",
            "LSTM lost het vanishing gradient probleem op",
            "CNN is gespecialiseerd in beeldherkenning",
            "Dropout voorkomt overfitting door neuronen uit te schakelen",
            "Batch normalization versnelt en stabiliseert training",
            "Python decorators wrappen functies voor extra functionaliteit",
            "Generators gebruiken yield voor memory-efficiente iteratie",
            "API rate limiting beschermt tegen overbelasting",
            "JWT tokens bevatten user info voor stateless authenticatie",
            "Gradient descent optimaliseert model parameters",
            "Feature engineering verbetert model input",
            "Cross-validation test model generalisatie",
            "Hyperparameter tuning optimaliseert model configuratie",
            "Data augmentation vergroot training datasets",
            "Ensemble methods combineren meerdere modellen",
        ]

        # AI check voor turbo mode
        echte_ai = False
        if keuze == "5":
            try:
                claude_chat = _get_claude_chat()
                if claude_chat:
                    echte_ai = True
                    print(f"  [AI] ECHTE Claude AI geactiveerd!")
            except Exception as e:
                logger.debug("Failed to activate Claude AI for turbo mode: %s", e)

        # Start de cycli
        for i in range(sessie["cycli"]):
            # Voortgang tonen (elke 5 cycli of bij belangrijke momenten)
            if i % 5 == 0 or i == sessie["cycli"] - 1:
                voortgang = int((i + 1) / sessie["cycli"] * 100)
                balk = "█" * (voortgang // 5) + "░" * (20 - voortgang // 5)
                print(f"\r  [{balk}] {voortgang}% - Cyclus {i+1}/{sessie['cycli']}", end="", flush=True)

            # Bepaal actie: 60% leren, 40% slapen
            if random.random() < 0.6:
                # LEER CYCLUS
                leer_cycli += 1

                # Leer een feit
                beschikbare_feiten = [f for f in auto_feiten if f not in permanente_kennis["feiten"]]
                if beschikbare_feiten:
                    feit = random.choice(beschikbare_feiten)
                    permanente_kennis["feiten"].append(feit)
                    permanente_kennis["bronnen"].append("auto_learn")
                    permanente_kennis["geleerd_op"].append(datetime.now().isoformat())
                    feiten_geleerd += 1
                    totaal_intel += 1

                # IQ boost
                totaal_intel += random.randint(1, 3)
                totaal_xp += random.randint(5, 15)

                # Kleine energie kosten
                self.huisdier["energie"] = max(0, self.huisdier["energie"] - 0.2)

            else:
                # SLAAP CYCLUS
                slaap_cycli += 1

                # Energie herstel
                energie_herstel = random.randint(3, 8)
                self.huisdier["energie"] = min(100, self.huisdier["energie"] + energie_herstel)
                totaal_energie += energie_herstel

                # Geluk boost
                geluk_boost = random.randint(1, 3)
                self.huisdier["geluk"] = min(100, self.huisdier["geluk"] + geluk_boost)
                totaal_geluk += geluk_boost

                # Kleine XP
                totaal_xp += random.randint(2, 5)

                # Dromen kunnen extra kennis geven
                if random.random() < 0.3:
                    totaal_intel += 1

            # Kleine pauze voor effect (maar niet te lang)
            if i % 10 == 0:
                time.sleep(0.1)

        # AI Turbo bonus
        if echte_ai:
            print(f"\n\n  [AI] Claude AI verwerkt geleerde kennis...")
            time.sleep(0.5)
            totaal_intel += 25
            totaal_xp += 50
            feiten_geleerd += 5
            # Voeg extra AI feiten toe
            ai_bonus_feiten = [
                "AI Turbo: Self-attention weegt elk woord tegen alle andere woorden",
                "AI Turbo: Multi-head attention biedt meerdere representaties",
                "AI Turbo: Positional encoding geeft woordvolgorde informatie",
                "AI Turbo: Layer normalization normaliseert per sample",
                "AI Turbo: Residual connections helpen gradient flow",
            ]
            for feit in ai_bonus_feiten:
                if feit not in permanente_kennis["feiten"]:
                    permanente_kennis["feiten"].append(feit)
                    permanente_kennis["bronnen"].append("ai_turbo")
                    permanente_kennis["geleerd_op"].append(datetime.now().isoformat())

        # Update permanente kennis
        permanente_kennis["totaal_sessies"] += 1
        self._sla_permanente_kennis_op(permanente_kennis)

        # Update huisdier stats
        self.huisdier["intelligentie"] = self.huisdier.get("intelligentie", 0) + totaal_intel
        self.huisdier["ervaring"] += totaal_xp
        self.huisdier["stats"]["feiten_geleerd"] = self.huisdier["stats"].get("feiten_geleerd", 0) + feiten_geleerd

        # Sync kennis
        self.huisdier["kennis"]["feiten"] = permanente_kennis["feiten"][-100:]

        # Resultaten
        print("\n\n" + "=" * 60)
        print(f"  {emoji} AUTO MODE VOLTOOID! {emoji}")
        print("=" * 60)

        print(f"\n  {naam}'s {sessie['naam']} sessie resultaten:")
        print(f"  " + "-" * 45)
        print(f"    [CYCLUS] Totaal: {sessie['cycli']} cycli")
        print(f"    [LAMP] Leer cycli: {leer_cycli}")
        print(f"    [BED] Slaap cycli: {slaap_cycli}")
        print(f"  " + "-" * 45)
        print(f"    [BOEK] Nieuwe feiten: {feiten_geleerd}")
        print(f"    [DISK] Totaal opgeslagen: {len(permanente_kennis['feiten'])} feiten")
        print(f"    [IQ] Intelligentie: +{totaal_intel}")
        print(f"    [ENERGIE] Energie hersteld: +{totaal_energie}")
        print(f"    [GELUK] Geluk: +{totaal_geluk}")
        print(f"    [XP] Ervaring: +{totaal_xp}")

        if echte_ai:
            print(f"\n  [STAR] AI TURBO BONUS TOEGEPAST!")
            print(f"  [AI] +25 IQ, +50 XP, +5 AI feiten!")

        # Check achievements
        if self.huisdier["stats"]["feiten_geleerd"] >= 10:
            self._unlock_achievement("kenniszoeker")
        if self.huisdier.get("intelligentie", 0) >= 100:
            self._unlock_achievement("super_slim")

        self._check_evolutie()
        print(f"\n  {geluid}")
        print(f"  {naam} voelt zich slimmer en uitgerust!")

        # LEARNING: Trigger kennisoptimalisatie na auto mode sessie
        self._trigger_optimization()

        self._sla_op()

    def _trigger_optimization(self):
        """Trigger Learning System optimalisatie na sessie."""
        self._init_learning()
        if not self.learning:
            return

        try:
            # Sync huisdier kennis naar learning system
            if "kennis" in self.huisdier:
                self.learning.sync_with_huisdier(self.huisdier)

            # Trigger optimalisatie als nodig
            result = self.learning.trigger_optimization()
            if result:
                print(f"\n  [OPT] LEARNING SYSTEM OPTIMALISATIE")
                print(f"  " + "-" * 40)
                print(f"    Geconsolideerd: {result.get('consolidated', 0)}")
                print(f"    Duplicaten verwijderd: {result.get('duplicates_removed', 0)}")
                print(f"    Oude interacties: {result.get('old_interactions_removed', 0)}")
                print(f"    Cache opgeruimd: {result.get('cache_entries_removed', 0)}")

            # Toon suggesties
            suggestions = self.learning.get_suggestions()
            if suggestions:
                print(f"\n  [TIP] Learning suggesties:")
                for sug in suggestions[:2]:
                    print(f"    - {sug[:60]}...")

            # Sync geoptimaliseerde kennis terug
            optimized_facts = self.learning.export_to_huisdier()
            if optimized_facts:
                self.huisdier["kennis"]["feiten"] = optimized_facts[:100]

        except Exception as e:
            # Silently fail - learning is optional
            pass

    def run(self):
        """Start de app."""
        clear_scherm()
        print("+=======================================+")
        print("|   VIRTUEEL HUISDIER SIMULATOR v6.0.0  |")
        print("|   VOLLEDIG AI-POWERED HUISDIER!      |")
        print("+=======================================+")
        print("|   Features:                          |")
        print("|   - AI Personality System            |")
        print("|   - AI Dream Generator               |")
        print("|   - AI Smart Dialogue                |")
        print("|   - AI Activity Advisor              |")
        print("|   - AI Memory System                 |")
        print("+=======================================+")

        self.huisdier = self._laad_huisdier()

        if self.huisdier:
            print(f"\nWelkom terug! {self.huisdier['emoji']} {self.huisdier['naam']} heeft je gemist!")
            self._bereken_tijd_verlies()

            # AI-generated welkomstbericht
            ai_welkom = self._ai_generate_response(
                f"{self.huisdier['naam']} ziet baasje weer na een pauze. Hoe reageert het?",
                f"{self.huisdier['naam']} kwispelt/spint/beweegt blij!"
            )
            print(f"\n  {ai_welkom}")

            # Toon status waarschuwingen
            if self.huisdier["honger"] < 30:
                print(f"\n[!] {self.huisdier['naam']} heeft honger!")
            if self.huisdier["energie"] < 3:
                print(f"[!] {self.huisdier['naam']} is moe!")
            if self.huisdier["gezondheid"] < 50:
                print(f"[!] {self.huisdier['naam']} voelt zich niet lekker!")

            # Toon AI Advisor aanbevelingen
            self._ai_show_advisor()

            input("\nDruk op Enter om verder te gaan...")
        else:
            print("\nJe hebt nog geen huisdier!")
            input("Druk op Enter om er een te maken...")
            self._maak_nieuw_huisdier()

        while True:
            clear_scherm()
            self._toon_status()
            self._toon_menu()

            keuze = input("\nJouw keuze (0-27): ").strip()

            if keuze == "1":
                self._voeren()
            elif keuze == "2":
                self._spelen()
            elif keuze == "3":
                self._slapen()
            elif keuze == "4":
                self._knuffelen()
            elif keuze == "5":
                self._dokter()
            elif keuze == "6":
                self._mini_games()
            elif keuze == "7":
                self._tricks_menu()
            elif keuze == "8":
                self._winkel()
            elif keuze == "9":
                self._achievements_bekijken()
            elif keuze == "10":
                self._dagelijkse_bonus()
            elif keuze == "11":
                self._huisdier_werk()
            elif keuze == "12":
                self._huisdier_leren()
            elif keuze == "13":
                if self._reset_huisdier():
                    continue  # Na reset direct naar nieuwe huisdier
            elif keuze == "14":
                self._verkenning_mode()
            elif keuze == "15":
                self._huisdier_dagboek()
            elif keuze == "16":
                self._seizoens_events()
            elif keuze == "17":
                self._competities()
            # NIEUWE FEATURES
            elif keuze == "18":
                self._huisdier_huis()
            elif keuze == "19":
                self._mini_farming()
            elif keuze == "20":
                self._crafting_werkplaats()
            elif keuze == "21":
                self._kook_keuken()
            elif keuze == "22":
                self._huisdier_bank()
            elif keuze == "23":
                self._huisdier_vrienden()
            elif keuze == "24":
                self._dagelijkse_missies()
            elif keuze == "25":
                self._levensdoelen()
            elif keuze == "26":
                self._foto_album()
            elif keuze == "27":
                self._weer_station()
            # POWER-UPS & MAGIE
            elif keuze == "28":
                self._evolutie_systeem()
            elif keuze == "29":
                self._huisdier_gym()
            elif keuze == "30":
                self._magie_spreuken()
            # ENTERTAINMENT
            elif keuze == "31":
                self._schatkist_jacht()
            elif keuze == "32":
                self._huisdier_restaurant()
            elif keuze == "33":
                self._muziek_studio()
            elif keuze == "34":
                self._arcade_hal()
            # SPECIALE AVONTUREN
            elif keuze == "35":
                self._tijdreizen()
            elif keuze == "36":
                self._magische_tuin()
            elif keuze == "37":
                self._geheime_missies()
            elif keuze == "38":
                self._auto_mode()
            # AI POWERED FEATURES
            elif keuze == "39":
                self._ai_show_advisor()
            elif keuze == "40":
                self._ai_pet_chat()
            elif keuze == "41":
                self._ai_memory_lane()
            elif keuze == "0":
                self._sla_op()
                print(f"\n{self.huisdier['naam']} is opgeslagen!")
                print(f"Tot de volgende keer! {self.huisdier['emoji']}")
                break
            else:
                print("Ongeldige keuze!")
                continue

            self._sla_op()
            input("\nDruk op Enter om verder te gaan...")
