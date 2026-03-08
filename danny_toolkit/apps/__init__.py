"""Apps module - Standalone applicaties."""

from __future__ import annotations

from danny_toolkit.apps.boodschappenlijst import BoodschappenlijstApp
from danny_toolkit.apps.rekenmachine import RekenmachineApp
from danny_toolkit.apps.virtueel_huisdier import VirtueelHuisdierApp
from danny_toolkit.apps.schatzoek import SchatzoekApp
from danny_toolkit.apps.code_analyse import CodeAnalyseApp
from danny_toolkit.apps.goals_tracker import GoalsTrackerApp
from danny_toolkit.apps.room_planner import RoomPlannerApp
from danny_toolkit.apps.music_composer import MusicComposerApp
from danny_toolkit.apps.recipe_generator import RecipeGeneratorApp
from danny_toolkit.apps.fitness_tracker import FitnessTrackerApp
from danny_toolkit.apps.dream_journal import DreamJournalApp
from danny_toolkit.apps.code_snippets import CodeSnippetsApp
from danny_toolkit.apps.language_tutor import LanguageTutorApp
from danny_toolkit.apps.decision_maker import DecisionMakerApp
from danny_toolkit.apps.time_capsule import TimeCapsuleApp
import logging

logger = logging.getLogger(__name__)

__all__ = [
    "BoodschappenlijstApp",
    "RekenmachineApp",
    "VirtueelHuisdierApp",
    "SchatzoekApp",
    "CodeAnalyseApp",
    "GoalsTrackerApp",
    "RoomPlannerApp",
    "MusicComposerApp",
    "RecipeGeneratorApp",
    "FitnessTrackerApp",
    "DreamJournalApp",
    "CodeSnippetsApp",
    "LanguageTutorApp",
    "DecisionMakerApp",
    "TimeCapsuleApp",
]
