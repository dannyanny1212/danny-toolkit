"""
App Tool Definitions voor Central Brain.

Definieert alle 31+ apps als Anthropic-compatible tools met hun acties.
Elke app wordt geregistreerd met beschrijving en callable acties.
"""

from typing import Dict, List, Any, Callable, Optional
from dataclasses import dataclass, field
from enum import Enum


class AppCategorie(Enum):
    """Categorieën voor apps."""
    PRODUCTIVITEIT = "productiviteit"
    AI = "ai"
    GEZONDHEID = "gezondheid"
    FINANCIEN = "financien"
    CREATIEF = "creatief"
    LEREN = "leren"
    LIFESTYLE = "lifestyle"


@dataclass
class AppActie:
    """Definitie van een app actie."""
    naam: str
    beschrijving: str
    parameters: Dict[str, dict]
    returns: str = "string"
    vereist_data: bool = False  # True als app data nodig heeft


@dataclass
class AppDefinition:
    """Definitie van een app als tool."""
    naam: str
    beschrijving: str
    categorie: AppCategorie
    acties: List[AppActie]
    module_path: str
    class_name: str
    prioriteit: int = 5  # 1-10, hoger = belangrijker voor workflows

    def to_anthropic_tool(self, actie_naam: str = None) -> dict:
        """Converteer naar Anthropic tool format."""
        if actie_naam:
            actie = next((a for a in self.acties if a.naam == actie_naam), None)
            if not actie:
                return None
            return {
                "name": f"{self.naam}_{actie.naam}",
                "description": f"[{self.naam}] {actie.beschrijving}",
                "input_schema": {
                    "type": "object",
                    "properties": actie.parameters,
                    "required": [k for k, v in actie.parameters.items()
                                if v.get("required", False)]
                }
            }

        # Return alle acties als afzonderlijke tools
        tools = []
        for actie in self.acties:
            tools.append({
                "name": f"{self.naam}_{actie.naam}",
                "description": f"[{self.naam}] {actie.beschrijving}",
                "input_schema": {
                    "type": "object",
                    "properties": actie.parameters,
                    "required": [k for k, v in actie.parameters.items()
                                if v.get("required", False)]
                }
            })
        return tools


# =============================================================================
# APP TOOL DEFINITIONS - Alle 31+ apps
# =============================================================================

APP_TOOLS: Dict[str, AppDefinition] = {
    # === GEZONDHEID & FITNESS ===
    "fitness_tracker": AppDefinition(
        naam="fitness_tracker",
        beschrijving="Track workouts, calorieën, sets/reps en personal records",
        categorie=AppCategorie.GEZONDHEID,
        module_path="danny_toolkit.apps.fitness_tracker",
        class_name="FitnessTrackerApp",
        prioriteit=9,
        acties=[
            AppActie(
                naam="log_workout",
                beschrijving="Log een nieuwe workout met oefeningen",
                parameters={
                    "workout_type": {
                        "type": "string",
                        "description": "Type workout: kracht, cardio, of mix",
                        "enum": ["kracht", "cardio", "mix"]
                    },
                    "oefeningen": {
                        "type": "array",
                        "description": "Lijst van oefeningen met sets/reps",
                        "items": {"type": "object"}
                    },
                    "duur_min": {
                        "type": "integer",
                        "description": "Duur in minuten"
                    }
                }
            ),
            AppActie(
                naam="get_stats",
                beschrijving="Haal workout statistieken op",
                parameters={
                    "periode": {
                        "type": "string",
                        "description": "Periode: vandaag, week, maand, alles",
                        "enum": ["vandaag", "week", "maand", "alles"]
                    }
                },
                vereist_data=True
            ),
            AppActie(
                naam="get_burned_calories",
                beschrijving="Bereken verbrande calorieën",
                parameters={
                    "periode": {
                        "type": "string",
                        "description": "Periode voor berekening",
                        "enum": ["vandaag", "week", "maand"]
                    }
                },
                vereist_data=True
            ),
            AppActie(
                naam="check_streak",
                beschrijving="Check workout streak status",
                parameters={},
                vereist_data=True
            ),
            AppActie(
                naam="get_personal_records",
                beschrijving="Haal personal records op",
                parameters={
                    "oefening": {
                        "type": "string",
                        "description": "Specifieke oefening (optioneel)"
                    }
                },
                vereist_data=True
            ),
        ]
    ),

    "mood_tracker": AppDefinition(
        naam="mood_tracker",
        beschrijving="Track dagelijkse stemming en emoties",
        categorie=AppCategorie.GEZONDHEID,
        module_path="danny_toolkit.apps.mood_tracker",
        class_name="MoodTrackerApp",
        prioriteit=8,
        acties=[
            AppActie(
                naam="log_mood",
                beschrijving="Log huidige stemming",
                parameters={
                    "score": {
                        "type": "integer",
                        "description": "Stemming score 1-10",
                        "minimum": 1,
                        "maximum": 10
                    },
                    "notitie": {
                        "type": "string",
                        "description": "Optionele notitie"
                    }
                }
            ),
            AppActie(
                naam="get_mood_trend",
                beschrijving="Haal mood trend op",
                parameters={
                    "dagen": {
                        "type": "integer",
                        "description": "Aantal dagen terug"
                    }
                },
                vereist_data=True
            ),
            AppActie(
                naam="analyze_mood",
                beschrijving="Analyseer mood patronen",
                parameters={},
                vereist_data=True
            ),
        ]
    ),

    # === PRODUCTIVITEIT ===
    "goals_tracker": AppDefinition(
        naam="goals_tracker",
        beschrijving="Track doelen en voortgang",
        categorie=AppCategorie.PRODUCTIVITEIT,
        module_path="danny_toolkit.apps.goals_tracker",
        class_name="GoalsTrackerApp",
        prioriteit=9,
        acties=[
            AppActie(
                naam="add_goal",
                beschrijving="Voeg nieuw doel toe",
                parameters={
                    "titel": {
                        "type": "string",
                        "description": "Titel van het doel",
                        "required": True
                    },
                    "beschrijving": {
                        "type": "string",
                        "description": "Beschrijving"
                    },
                    "deadline": {
                        "type": "string",
                        "description": "Deadline (YYYY-MM-DD)"
                    }
                }
            ),
            AppActie(
                naam="get_active_goals",
                beschrijving="Haal actieve doelen op",
                parameters={},
                vereist_data=True
            ),
            AppActie(
                naam="update_progress",
                beschrijving="Update voortgang van een doel",
                parameters={
                    "goal_id": {
                        "type": "string",
                        "description": "ID van het doel"
                    },
                    "voortgang": {
                        "type": "integer",
                        "description": "Voortgang percentage 0-100"
                    },
                    "notitie": {
                        "type": "string",
                        "description": "Optionele notitie"
                    }
                }
            ),
        ]
    ),

    "agenda_planner": AppDefinition(
        naam="agenda_planner",
        beschrijving="Beheer agenda en afspraken",
        categorie=AppCategorie.PRODUCTIVITEIT,
        module_path="danny_toolkit.apps.agenda_planner",
        class_name="AgendaPlannerApp",
        prioriteit=8,
        acties=[
            AppActie(
                naam="add_event",
                beschrijving="Voeg afspraak toe",
                parameters={
                    "titel": {
                        "type": "string",
                        "description": "Titel van de afspraak",
                        "required": True
                    },
                    "datum": {
                        "type": "string",
                        "description": "Datum (YYYY-MM-DD)",
                        "required": True
                    },
                    "tijd": {
                        "type": "string",
                        "description": "Tijd (HH:MM)"
                    },
                    "duur_min": {
                        "type": "integer",
                        "description": "Duur in minuten"
                    }
                }
            ),
            AppActie(
                naam="get_today",
                beschrijving="Haal afspraken van vandaag op",
                parameters={},
                vereist_data=True
            ),
            AppActie(
                naam="get_upcoming",
                beschrijving="Haal komende afspraken op",
                parameters={
                    "dagen": {
                        "type": "integer",
                        "description": "Aantal dagen vooruit"
                    }
                },
                vereist_data=True
            ),
        ]
    ),

    "pomodoro_timer": AppDefinition(
        naam="pomodoro_timer",
        beschrijving="Pomodoro timer voor focus sessies",
        categorie=AppCategorie.PRODUCTIVITEIT,
        module_path="danny_toolkit.apps.pomodoro_timer",
        class_name="PomodoroTimerApp",
        prioriteit=7,
        acties=[
            AppActie(
                naam="start_session",
                beschrijving="Start een focus sessie",
                parameters={
                    "duur_min": {
                        "type": "integer",
                        "description": "Sessie duur (default 25)"
                    },
                    "taak": {
                        "type": "string",
                        "description": "Beschrijving van de taak"
                    }
                }
            ),
            AppActie(
                naam="get_stats",
                beschrijving="Haal pomodoro statistieken op",
                parameters={},
                vereist_data=True
            ),
        ]
    ),

    "habit_tracker": AppDefinition(
        naam="habit_tracker",
        beschrijving="Track dagelijkse gewoontes",
        categorie=AppCategorie.PRODUCTIVITEIT,
        module_path="danny_toolkit.apps.habit_tracker",
        class_name="HabitTrackerApp",
        prioriteit=8,
        acties=[
            AppActie(
                naam="log_habit",
                beschrijving="Log een gewoonte als gedaan",
                parameters={
                    "habit_naam": {
                        "type": "string",
                        "description": "Naam van de gewoonte",
                        "required": True
                    }
                }
            ),
            AppActie(
                naam="get_habits",
                beschrijving="Haal alle gewoontes op",
                parameters={},
                vereist_data=True
            ),
            AppActie(
                naam="get_streaks",
                beschrijving="Haal habit streaks op",
                parameters={},
                vereist_data=True
            ),
        ]
    ),

    # === FINANCIEN ===
    "expense_tracker": AppDefinition(
        naam="expense_tracker",
        beschrijving="Track uitgaven en budget",
        categorie=AppCategorie.FINANCIEN,
        module_path="danny_toolkit.apps.expense_tracker",
        class_name="ExpenseTrackerApp",
        prioriteit=9,
        acties=[
            AppActie(
                naam="add_expense",
                beschrijving="Voeg uitgave toe",
                parameters={
                    "bedrag": {
                        "type": "number",
                        "description": "Bedrag in euro",
                        "required": True
                    },
                    "categorie": {
                        "type": "string",
                        "description": "Categorie van de uitgave"
                    },
                    "beschrijving": {
                        "type": "string",
                        "description": "Beschrijving"
                    }
                }
            ),
            AppActie(
                naam="get_budget_status",
                beschrijving="Haal budget status op",
                parameters={},
                vereist_data=True
            ),
            AppActie(
                naam="get_monthly_summary",
                beschrijving="Haal maandoverzicht op",
                parameters={
                    "maand": {
                        "type": "integer",
                        "description": "Maand nummer (1-12)"
                    }
                },
                vereist_data=True
            ),
            AppActie(
                naam="estimate_cost",
                beschrijving="Schat kosten voor items",
                parameters={
                    "items": {
                        "type": "array",
                        "description": "Lijst van items",
                        "items": {"type": "string"}
                    }
                }
            ),
            AppActie(
                naam="ai_analyse",
                beschrijving="AI analyse van uitgaven",
                parameters={},
                vereist_data=True
            ),
        ]
    ),

    # === VOEDING ===
    "recipe_generator": AppDefinition(
        naam="recipe_generator",
        beschrijving="Genereer recepten en meal planning",
        categorie=AppCategorie.LIFESTYLE,
        module_path="danny_toolkit.apps.recipe_generator",
        class_name="RecipeGeneratorApp",
        prioriteit=8,
        acties=[
            AppActie(
                naam="generate_recipe",
                beschrijving="Genereer recept op basis van ingrediënten",
                parameters={
                    "ingredienten": {
                        "type": "array",
                        "description": "Beschikbare ingrediënten",
                        "items": {"type": "string"},
                        "required": True
                    },
                    "dieet": {
                        "type": "string",
                        "description": "Dieet voorkeur",
                        "enum": ["normaal", "vegetarisch", "veganistisch", "keto"]
                    }
                }
            ),
            AppActie(
                naam="generate_protein_meal",
                beschrijving="Genereer eiwitrijk recept",
                parameters={
                    "calorieen": {
                        "type": "integer",
                        "description": "Streef calorieën"
                    },
                    "eiwit_gram": {
                        "type": "integer",
                        "description": "Gewenste eiwitten in gram"
                    }
                }
            ),
            AppActie(
                naam="get_meal_plan",
                beschrijving="Haal weekmenu op",
                parameters={},
                vereist_data=True
            ),
            AppActie(
                naam="get_shopping_list",
                beschrijving="Genereer boodschappenlijst",
                parameters={
                    "dagen": {
                        "type": "integer",
                        "description": "Aantal dagen"
                    }
                },
                vereist_data=True
            ),
        ]
    ),

    "boodschappenlijst": AppDefinition(
        naam="boodschappenlijst",
        beschrijving="Beheer boodschappenlijst",
        categorie=AppCategorie.LIFESTYLE,
        module_path="danny_toolkit.apps.boodschappenlijst",
        class_name="BoodschappenlijstApp",
        prioriteit=6,
        acties=[
            AppActie(
                naam="add_item",
                beschrijving="Voeg item toe aan lijst",
                parameters={
                    "item": {
                        "type": "string",
                        "description": "Item naam",
                        "required": True
                    },
                    "aantal": {
                        "type": "integer",
                        "description": "Aantal"
                    }
                }
            ),
            AppActie(
                naam="add_items",
                beschrijving="Voeg meerdere items toe",
                parameters={
                    "items": {
                        "type": "array",
                        "description": "Lijst van items",
                        "items": {"type": "string"},
                        "required": True
                    }
                }
            ),
            AppActie(
                naam="get_list",
                beschrijving="Haal huidige lijst op",
                parameters={},
                vereist_data=True
            ),
            AppActie(
                naam="add_missing_ingredients",
                beschrijving="Voeg ontbrekende ingrediënten toe",
                parameters={
                    "ingredienten": {
                        "type": "array",
                        "description": "Benodigde ingrediënten",
                        "items": {"type": "string"},
                        "required": True
                    }
                }
            ),
        ]
    ),

    # === AI SYSTEMEN ===
    "production_rag": AppDefinition(
        naam="production_rag",
        beschrijving="RAG systeem voor kennisbeheer",
        categorie=AppCategorie.AI,
        module_path="danny_toolkit.ai.production_rag",
        class_name="ProductionRAG",
        prioriteit=9,
        acties=[
            AppActie(
                naam="query",
                beschrijving="Zoek in kennisbank",
                parameters={
                    "vraag": {
                        "type": "string",
                        "description": "Zoekvraag",
                        "required": True
                    }
                }
            ),
            AppActie(
                naam="store_document",
                beschrijving="Sla document op in kennisbank",
                parameters={
                    "tekst": {
                        "type": "string",
                        "description": "Tekst om op te slaan",
                        "required": True
                    },
                    "metadata": {
                        "type": "object",
                        "description": "Metadata voor het document"
                    }
                }
            ),
            AppActie(
                naam="store_and_index",
                beschrijving="Sla op en indexeer voor zoeken",
                parameters={
                    "content": {
                        "type": "string",
                        "description": "Content om te indexeren",
                        "required": True
                    },
                    "bron": {
                        "type": "string",
                        "description": "Bron van de content"
                    }
                }
            ),
        ]
    ),

    "nieuws_agent": AppDefinition(
        naam="nieuws_agent",
        beschrijving="Haal en analyseer nieuws",
        categorie=AppCategorie.AI,
        module_path="danny_toolkit.ai.nieuws_agent",
        class_name="NieuwsAgentApp",
        prioriteit=7,
        acties=[
            AppActie(
                naam="get_news",
                beschrijving="Haal recent nieuws op",
                parameters={
                    "categorie": {
                        "type": "string",
                        "description": "Nieuwscategorie"
                    }
                }
            ),
            AppActie(
                naam="get_relevant_news",
                beschrijving="Haal relevant nieuws op basis van interesses",
                parameters={
                    "onderwerp": {
                        "type": "string",
                        "description": "Specifiek onderwerp"
                    }
                }
            ),
            AppActie(
                naam="summarize_news",
                beschrijving="Vat nieuws samen",
                parameters={},
                vereist_data=True
            ),
        ]
    ),

    "weer_agent": AppDefinition(
        naam="weer_agent",
        beschrijving="Weer informatie en voorspellingen",
        categorie=AppCategorie.AI,
        module_path="danny_toolkit.ai.weer_agent",
        class_name="WeerAgentApp",
        prioriteit=6,
        acties=[
            AppActie(
                naam="get_weather",
                beschrijving="Haal huidig weer op",
                parameters={
                    "locatie": {
                        "type": "string",
                        "description": "Stad of locatie"
                    }
                }
            ),
            AppActie(
                naam="get_forecast",
                beschrijving="Haal weersvoorspelling op",
                parameters={
                    "locatie": {
                        "type": "string",
                        "description": "Stad of locatie"
                    },
                    "dagen": {
                        "type": "integer",
                        "description": "Aantal dagen"
                    }
                }
            ),
        ]
    ),

    # === CODE & DEVELOPMENT ===
    "code_analyse": AppDefinition(
        naam="code_analyse",
        beschrijving="Analyseer en verbeter code",
        categorie=AppCategorie.AI,
        module_path="danny_toolkit.apps.code_analyse",
        class_name="CodeAnalyseApp",
        prioriteit=8,
        acties=[
            AppActie(
                naam="analyze_file",
                beschrijving="Analyseer een code bestand",
                parameters={
                    "bestand": {
                        "type": "string",
                        "description": "Pad naar bestand",
                        "required": True
                    }
                }
            ),
            AppActie(
                naam="find_issues",
                beschrijving="Vind problemen in code",
                parameters={
                    "bestand": {
                        "type": "string",
                        "description": "Pad naar bestand"
                    }
                }
            ),
            AppActie(
                naam="analyze_if_stuck",
                beschrijving="Analyseer waarom code vastloopt",
                parameters={
                    "probleem": {
                        "type": "string",
                        "description": "Beschrijving van het probleem"
                    }
                }
            ),
        ]
    ),

    "code_snippets": AppDefinition(
        naam="code_snippets",
        beschrijving="Beheer en zoek code snippets",
        categorie=AppCategorie.AI,
        module_path="danny_toolkit.apps.code_snippets",
        class_name="CodeSnippetsApp",
        prioriteit=7,
        acties=[
            AppActie(
                naam="search",
                beschrijving="Zoek code snippets",
                parameters={
                    "query": {
                        "type": "string",
                        "description": "Zoekterm",
                        "required": True
                    },
                    "taal": {
                        "type": "string",
                        "description": "Programmeertaal"
                    }
                }
            ),
            AppActie(
                naam="add_snippet",
                beschrijving="Voeg nieuwe snippet toe",
                parameters={
                    "titel": {
                        "type": "string",
                        "description": "Titel",
                        "required": True
                    },
                    "code": {
                        "type": "string",
                        "description": "De code",
                        "required": True
                    },
                    "taal": {
                        "type": "string",
                        "description": "Programmeertaal"
                    }
                }
            ),
            AppActie(
                naam="find_solution",
                beschrijving="Vind snippet oplossing voor probleem",
                parameters={
                    "probleem": {
                        "type": "string",
                        "description": "Probleem beschrijving",
                        "required": True
                    }
                }
            ),
        ]
    ),

    # === BESLISSINGEN ===
    "decision_maker": AppDefinition(
        naam="decision_maker",
        beschrijving="Hulp bij beslissingen",
        categorie=AppCategorie.PRODUCTIVITEIT,
        module_path="danny_toolkit.apps.decision_maker",
        class_name="DecisionMakerApp",
        prioriteit=7,
        acties=[
            AppActie(
                naam="analyze_decision",
                beschrijving="Analyseer een beslissing",
                parameters={
                    "vraag": {
                        "type": "string",
                        "description": "De beslissing/vraag",
                        "required": True
                    },
                    "opties": {
                        "type": "array",
                        "description": "Mogelijke opties",
                        "items": {"type": "string"}
                    }
                }
            ),
            AppActie(
                naam="use_knowledge_for_decision",
                beschrijving="Gebruik kennis voor beslissing",
                parameters={
                    "context": {
                        "type": "string",
                        "description": "Context voor de beslissing",
                        "required": True
                    }
                }
            ),
        ]
    ),

    # === NOTITIES & LEREN ===
    "notitie_app": AppDefinition(
        naam="notitie_app",
        beschrijving="Notities maken en beheren",
        categorie=AppCategorie.PRODUCTIVITEIT,
        module_path="danny_toolkit.apps.notitie_app",
        class_name="NotitieApp",
        prioriteit=6,
        acties=[
            AppActie(
                naam="add_note",
                beschrijving="Maak nieuwe notitie",
                parameters={
                    "titel": {
                        "type": "string",
                        "description": "Titel",
                        "required": True
                    },
                    "inhoud": {
                        "type": "string",
                        "description": "Inhoud van de notitie",
                        "required": True
                    }
                }
            ),
            AppActie(
                naam="search_notes",
                beschrijving="Zoek in notities",
                parameters={
                    "query": {
                        "type": "string",
                        "description": "Zoekterm",
                        "required": True
                    }
                }
            ),
        ]
    ),

    "flashcards": AppDefinition(
        naam="flashcards",
        beschrijving="Flashcards voor leren",
        categorie=AppCategorie.LEREN,
        module_path="danny_toolkit.apps.flashcards",
        class_name="FlashcardsApp",
        prioriteit=5,
        acties=[
            AppActie(
                naam="study",
                beschrijving="Start studeersessie",
                parameters={
                    "deck": {
                        "type": "string",
                        "description": "Deck naam"
                    }
                }
            ),
            AppActie(
                naam="add_card",
                beschrijving="Voeg flashcard toe",
                parameters={
                    "vraag": {
                        "type": "string",
                        "description": "Vraag",
                        "required": True
                    },
                    "antwoord": {
                        "type": "string",
                        "description": "Antwoord",
                        "required": True
                    }
                }
            ),
        ]
    ),

    "language_tutor": AppDefinition(
        naam="language_tutor",
        beschrijving="Talen leren",
        categorie=AppCategorie.LEREN,
        module_path="danny_toolkit.apps.language_tutor",
        class_name="LanguageTutorApp",
        prioriteit=5,
        acties=[
            AppActie(
                naam="practice",
                beschrijving="Oefen taal",
                parameters={
                    "taal": {
                        "type": "string",
                        "description": "Te oefenen taal"
                    }
                }
            ),
            AppActie(
                naam="translate",
                beschrijving="Vertaal tekst",
                parameters={
                    "tekst": {
                        "type": "string",
                        "description": "Te vertalen tekst",
                        "required": True
                    },
                    "naar": {
                        "type": "string",
                        "description": "Doeltaal"
                    }
                }
            ),
        ]
    ),

    # === CREATIEF ===
    "music_composer": AppDefinition(
        naam="music_composer",
        beschrijving="Componeer muziek",
        categorie=AppCategorie.CREATIEF,
        module_path="danny_toolkit.apps.music_composer",
        class_name="MusicComposerApp",
        prioriteit=4,
        acties=[
            AppActie(
                naam="compose",
                beschrijving="Componeer melodie",
                parameters={
                    "stijl": {
                        "type": "string",
                        "description": "Muziekstijl"
                    },
                    "stemming": {
                        "type": "string",
                        "description": "Gewenste stemming"
                    }
                }
            ),
        ]
    ),

    "citaten_generator": AppDefinition(
        naam="citaten_generator",
        beschrijving="Genereer inspirerende citaten",
        categorie=AppCategorie.CREATIEF,
        module_path="danny_toolkit.apps.citaten_generator",
        class_name="CitatenGeneratorApp",
        prioriteit=4,
        acties=[
            AppActie(
                naam="get_quote",
                beschrijving="Haal random citaat op",
                parameters={
                    "categorie": {
                        "type": "string",
                        "description": "Categorie citaat"
                    }
                }
            ),
        ]
    ),

    # === LIFESTYLE ===
    "dream_journal": AppDefinition(
        naam="dream_journal",
        beschrijving="Dromen loggen en analyseren",
        categorie=AppCategorie.LIFESTYLE,
        module_path="danny_toolkit.apps.dream_journal",
        class_name="DreamJournalApp",
        prioriteit=4,
        acties=[
            AppActie(
                naam="log_dream",
                beschrijving="Log een droom",
                parameters={
                    "beschrijving": {
                        "type": "string",
                        "description": "Beschrijving van de droom",
                        "required": True
                    },
                    "emoties": {
                        "type": "array",
                        "description": "Gevoelde emoties",
                        "items": {"type": "string"}
                    }
                }
            ),
            AppActie(
                naam="analyze_patterns",
                beschrijving="Analyseer droompatronen",
                parameters={},
                vereist_data=True
            ),
        ]
    ),

    "time_capsule": AppDefinition(
        naam="time_capsule",
        beschrijving="Berichten naar de toekomst",
        categorie=AppCategorie.LIFESTYLE,
        module_path="danny_toolkit.apps.time_capsule",
        class_name="TimeCapsuleApp",
        prioriteit=3,
        acties=[
            AppActie(
                naam="create_capsule",
                beschrijving="Maak time capsule",
                parameters={
                    "bericht": {
                        "type": "string",
                        "description": "Bericht",
                        "required": True
                    },
                    "open_datum": {
                        "type": "string",
                        "description": "Datum om te openen (YYYY-MM-DD)",
                        "required": True
                    }
                }
            ),
        ]
    ),

    # === UTILITIES ===
    "rekenmachine": AppDefinition(
        naam="rekenmachine",
        beschrijving="Slimme rekenmachine",
        categorie=AppCategorie.PRODUCTIVITEIT,
        module_path="danny_toolkit.apps.rekenmachine",
        class_name="RekenmachineApp",
        prioriteit=3,
        acties=[
            AppActie(
                naam="calculate",
                beschrijving="Voer berekening uit",
                parameters={
                    "expressie": {
                        "type": "string",
                        "description": "Wiskundige expressie",
                        "required": True
                    }
                }
            ),
        ]
    ),

    "unit_converter": AppDefinition(
        naam="unit_converter",
        beschrijving="Eenheden converteren",
        categorie=AppCategorie.PRODUCTIVITEIT,
        module_path="danny_toolkit.apps.unit_converter",
        class_name="UnitConverterApp",
        prioriteit=3,
        acties=[
            AppActie(
                naam="convert",
                beschrijving="Converteer eenheden",
                parameters={
                    "waarde": {
                        "type": "number",
                        "description": "Te converteren waarde",
                        "required": True
                    },
                    "van": {
                        "type": "string",
                        "description": "Bron eenheid",
                        "required": True
                    },
                    "naar": {
                        "type": "string",
                        "description": "Doel eenheid",
                        "required": True
                    }
                }
            ),
        ]
    ),

    "wachtwoord_generator": AppDefinition(
        naam="wachtwoord_generator",
        beschrijving="Genereer veilige wachtwoorden",
        categorie=AppCategorie.PRODUCTIVITEIT,
        module_path="danny_toolkit.apps.wachtwoord_generator",
        class_name="WachtwoordGeneratorApp",
        prioriteit=3,
        acties=[
            AppActie(
                naam="generate",
                beschrijving="Genereer wachtwoord",
                parameters={
                    "lengte": {
                        "type": "integer",
                        "description": "Lengte wachtwoord"
                    },
                    "speciale_tekens": {
                        "type": "boolean",
                        "description": "Inclusief speciale tekens"
                    }
                }
            ),
        ]
    ),

    # === AI STUDIO'S ===
    "nlp_studio": AppDefinition(
        naam="nlp_studio",
        beschrijving="NLP experimenten en analyse",
        categorie=AppCategorie.AI,
        module_path="danny_toolkit.apps.nlp_studio",
        class_name="NLPStudioApp",
        prioriteit=6,
        acties=[
            AppActie(
                naam="analyze_text",
                beschrijving="Analyseer tekst",
                parameters={
                    "tekst": {
                        "type": "string",
                        "description": "Te analyseren tekst",
                        "required": True
                    }
                }
            ),
            AppActie(
                naam="sentiment",
                beschrijving="Sentiment analyse",
                parameters={
                    "tekst": {
                        "type": "string",
                        "description": "Tekst voor sentiment",
                        "required": True
                    }
                }
            ),
        ]
    ),

    "ml_studio": AppDefinition(
        naam="ml_studio",
        beschrijving="Machine Learning experimenten",
        categorie=AppCategorie.AI,
        module_path="danny_toolkit.apps.ml_studio",
        class_name="MLStudioApp",
        prioriteit=6,
        acties=[
            AppActie(
                naam="train_model",
                beschrijving="Train een model",
                parameters={
                    "model_type": {
                        "type": "string",
                        "description": "Type model"
                    },
                    "data": {
                        "type": "object",
                        "description": "Training data"
                    }
                }
            ),
        ]
    ),

    "vector_studio": AppDefinition(
        naam="vector_studio",
        beschrijving="Vector database experimenten",
        categorie=AppCategorie.AI,
        module_path="danny_toolkit.apps.vector_studio",
        class_name="VectorStudioApp",
        prioriteit=5,
        acties=[
            AppActie(
                naam="search",
                beschrijving="Zoek in vector store",
                parameters={
                    "query": {
                        "type": "string",
                        "description": "Zoekvraag",
                        "required": True
                    }
                }
            ),
        ]
    ),

    "advanced_questions": AppDefinition(
        naam="advanced_questions",
        beschrijving="Complexe vraag-antwoord systeem",
        categorie=AppCategorie.AI,
        module_path="danny_toolkit.apps.advanced_questions",
        class_name="AdvancedQuestionsApp",
        prioriteit=7,
        acties=[
            AppActie(
                naam="ask",
                beschrijving="Stel een vraag",
                parameters={
                    "vraag": {
                        "type": "string",
                        "description": "De vraag",
                        "required": True
                    }
                }
            ),
        ]
    ),
}


def get_all_tools() -> List[dict]:
    """Haal alle app tools op in Anthropic format."""
    tools = []
    for app_def in APP_TOOLS.values():
        app_tools = app_def.to_anthropic_tool()
        if isinstance(app_tools, list):
            tools.extend(app_tools)
        elif app_tools:
            tools.append(app_tools)
    return tools


def get_tools_by_category(categorie: AppCategorie) -> List[dict]:
    """Haal tools op per categorie."""
    tools = []
    for app_def in APP_TOOLS.values():
        if app_def.categorie == categorie:
            app_tools = app_def.to_anthropic_tool()
            if isinstance(app_tools, list):
                tools.extend(app_tools)
    return tools


def get_priority_tools(min_prioriteit: int = 7) -> List[dict]:
    """Haal high-priority tools op voor workflows."""
    tools = []
    for app_def in APP_TOOLS.values():
        if app_def.prioriteit >= min_prioriteit:
            app_tools = app_def.to_anthropic_tool()
            if isinstance(app_tools, list):
                tools.extend(app_tools)
    return tools


def parse_tool_call(tool_name: str) -> tuple:
    """
    Parse tool name naar app en actie.

    Args:
        tool_name: bijv. "fitness_tracker_log_workout"

    Returns:
        Tuple van (app_naam, actie_naam)
    """
    for app_naam, app_def in APP_TOOLS.items():
        for actie in app_def.acties:
            full_name = f"{app_naam}_{actie.naam}"
            if tool_name == full_name:
                return (app_naam, actie.naam)
    return (None, None)


def get_app_definition(app_naam: str) -> Optional[AppDefinition]:
    """Haal app definitie op."""
    return APP_TOOLS.get(app_naam)
