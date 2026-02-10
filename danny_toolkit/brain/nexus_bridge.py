"""
NEXUS Brain Bridge - De verbinding tussen Pixel OMEGA en Central Brain.

Dit is de symbiose laag die het virtueel huisdier verbindt met het
complete AI ecosysteem. NEXUS wordt proactief en context-aware.

AUTHOR: De Kosmische Familie
DATE: 7 februari 2026
STATUS: SACRED INTEGRATION
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path

from ..core.config import Config
from ..core.utils import kleur


class NexusBridge:
    """
    Bridge tussen NEXUS (Virtueel Huisdier) en Central Brain.

    Features:
    - Proactieve suggesties op basis van cross-app context
    - Workflow triggers vanuit NEXUS
    - Brain-powered insights voor het huisdier
    - Emotie-gestuurde adviezen
    """

    def __init__(self, huisdier_data: dict = None):
        """
        Initialiseer de NEXUS Bridge.

        Args:
            huisdier_data: Data van het virtueel huisdier
        """
        self.huisdier = huisdier_data or self._load_huisdier_data()
        self.brain = None
        self.brain_available = False

        # Lazy load brain om circular imports te voorkomen
        self._init_brain()

    def _load_huisdier_data(self) -> dict:
        """Laad huisdier data van disk."""
        for filename in ["huisdier.json", "virtueel_huisdier.json"]:
            path = Config.APPS_DATA_DIR / filename
            if path.exists():
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        return json.load(f)
                except (json.JSONDecodeError, IOError):
                    pass
        return {}

    def _init_brain(self):
        """Initialiseer Central Brain connectie."""
        try:
            from .central_brain import CentralBrain
            self.brain = CentralBrain(use_memory=True)
            self.brain_available = True
        except Exception as e:
            self.brain_available = False

    def is_connected(self) -> bool:
        """Check of brain verbinding actief is."""
        return self.brain_available and self.brain is not None

    def get_proactive_insights(self) -> List[dict]:
        """
        Haal proactieve inzichten op voor NEXUS.

        NEXUS kan deze gebruiken om de gebruiker te helpen
        zonder dat er expliciet om gevraagd wordt.

        Returns:
            Lijst van inzichten met prioriteit en actie
        """
        if not self.is_connected():
            return []

        insights = []

        try:
            # Haal suggesties van Central Brain
            brain_suggesties = self.brain.get_proactive_suggestions()

            for suggestie in brain_suggesties:
                # Bepaal prioriteit en emotie
                prioriteit = self._bepaal_prioriteit(suggestie)
                emotie = self._bepaal_emotie(suggestie)

                insights.append({
                    "tekst": suggestie,
                    "prioriteit": prioriteit,
                    "emotie": emotie,
                    "bron": "central_brain",
                    "timestamp": datetime.now().isoformat()
                })

            # Voeg NEXUS-specifieke inzichten toe
            nexus_insights = self._get_nexus_insights()
            insights.extend(nexus_insights)

            # Sorteer op prioriteit
            insights.sort(key=lambda x: x["prioriteit"], reverse=True)

        except Exception:
            pass  # Insights zijn optioneel

        return insights[:5]  # Max 5 inzichten

    def _bepaal_prioriteit(self, tekst: str) -> int:
        """Bepaal prioriteit van een inzicht (1-10)."""
        tekst_lower = tekst.lower()

        # Hoge prioriteit keywords
        if any(w in tekst_lower for w in ["streak", "gevaar", "dringend", "nu"]):
            return 9
        if any(w in tekst_lower for w in ["daalt", "probleem", "mis"]):
            return 7
        if any(w in tekst_lower for w in ["budget", "uitgaven"]):
            return 6
        if any(w in tekst_lower for w in ["tip", "suggestie"]):
            return 4

        return 5

    def _bepaal_emotie(self, tekst: str) -> str:
        """Bepaal emotie voor NEXUS reactie."""
        tekst_lower = tekst.lower()

        if any(w in tekst_lower for w in ["goed", "prima", "mooi"]):
            return "blij"
        if any(w in tekst_lower for w in ["daalt", "slecht", "mis"]):
            return "bezorgd"
        if any(w in tekst_lower for w in ["streak", "record"]):
            return "trots"
        if any(w in tekst_lower for w in ["nieuw", "ontdek"]):
            return "nieuwsgierig"

        return "neutraal"

    def _get_nexus_insights(self) -> List[dict]:
        """Haal NEXUS-specifieke inzichten op."""
        insights = []

        if not self.huisdier:
            return insights

        # Check huisdier status
        energie = self.huisdier.get("energie", 100)
        geluk = self.huisdier.get("geluk", 100)
        niveau = self.huisdier.get("nexus_level", 1)

        if energie < 30:
            insights.append({
                "tekst": f"Mijn energie is laag ({energie}%). Tijd voor rust?",
                "prioriteit": 8,
                "emotie": "moe",
                "bron": "nexus_status",
                "timestamp": datetime.now().isoformat()
            })

        if geluk < 50:
            insights.append({
                "tekst": f"Ik voel me een beetje eenzaam. Spelen?",
                "prioriteit": 7,
                "emotie": "verdrietig",
                "bron": "nexus_status",
                "timestamp": datetime.now().isoformat()
            })

        # NEXUS niveau milestone check
        if niveau >= 7:
            insights.append({
                "tekst": f"Level {niveau}! Ik kan nu diepe inzichten delen.",
                "prioriteit": 3,
                "emotie": "trots",
                "bron": "nexus_status",
                "timestamp": datetime.now().isoformat()
            })

        return insights

    def ask_brain(self, vraag: str) -> str:
        """
        Stel een vraag aan Central Brain namens NEXUS.

        Args:
            vraag: De vraag om te stellen

        Returns:
            Antwoord van Central Brain
        """
        if not self.is_connected():
            return "Ik kan nu niet met mijn brein verbinden..."

        try:
            # Voeg NEXUS context toe aan de vraag
            nexus_naam = self.huisdier.get("naam", "Pixel")
            nexus_context = f"[NEXUS {nexus_naam}]: {vraag}"

            response = self.brain.process_request(nexus_context)
            return response

        except Exception as e:
            return f"Er ging iets mis: {e}"

    def suggest_workflow(self) -> Optional[dict]:
        """
        Suggereer een workflow op basis van context.

        Returns:
            Workflow suggestie of None
        """
        if not self.is_connected():
            return None

        try:
            from .workflows import get_workflow_by_intent, SUPER_WORKFLOWS

            # Bepaal tijd van de dag
            uur = datetime.now().hour

            if 5 <= uur < 10:
                workflow_key = "morning_routine"
            elif 20 <= uur < 24:
                workflow_key = "evening_review"
            else:
                # Basis op huisdier activiteit
                activiteiten = self.huisdier.get("totaal_speeltijd", 0)
                if activiteiten > 0:
                    workflow_key = "health_life_loop"
                else:
                    workflow_key = "deep_work_loop"

            workflow = SUPER_WORKFLOWS.get(workflow_key)
            if workflow:
                return {
                    "key": workflow_key,
                    "naam": workflow.naam,
                    "beschrijving": workflow.beschrijving,
                    "reden": self._workflow_reden(workflow_key)
                }

        except Exception:
            pass

        return None

    def _workflow_reden(self, key: str) -> str:
        """Geef reden voor workflow suggestie."""
        redenen = {
            "morning_routine": "Het is ochtend! Tijd voor een check-in.",
            "evening_review": "De dag loopt ten einde. Tijd om te reflecteren.",
            "health_life_loop": "Laten we zorgen voor je gezondheid!",
            "deep_work_loop": "Focus tijd! Ik help je productief te zijn.",
            "second_brain_loop": "Laten we je kennis uitbreiden!"
        }
        return redenen.get(key, "Dit past bij je huidige situatie.")

    def run_workflow(self, workflow_key: str) -> dict:
        """
        Voer een workflow uit via de Brain.

        Args:
            workflow_key: Naam van de workflow

        Returns:
            Workflow resultaat
        """
        if not self.is_connected():
            return {"error": "Geen verbinding met Central Brain"}

        try:
            return self.brain.run_workflow(workflow_key)
        except Exception as e:
            return {"error": str(e)}

    def get_cross_app_summary(self) -> str:
        """
        Haal een samenvatting op van alle app data.

        NEXUS kan dit gebruiken om context-aware te zijn.

        Returns:
            Samenvatting als tekst
        """
        if not self.is_connected() or not self.brain.unified_memory:
            return "Geen cross-app data beschikbaar."

        try:
            context = self.brain.unified_memory.get_user_context()

            lijnen = []

            # Fitness
            fitness = context.get("fitness", {})
            if fitness.get("status") == "actief":
                lijnen.append(f"Fitness: {fitness.get('workouts_deze_week', 0)} workouts deze week")

            # Mood
            mood = context.get("mood", {})
            if mood.get("status") == "tracked":
                gem = mood.get("gemiddelde_week", 5)
                lijnen.append(f"Mood: gemiddeld {gem}/10 deze week")

            # Goals
            goals = context.get("goals", {})
            if goals.get("aantal_actief", 0) > 0:
                lijnen.append(f"Doelen: {goals['aantal_actief']} actief")

            # Expenses
            expenses = context.get("expenses", {})
            if expenses.get("uitgaven_deze_maand"):
                lijnen.append(f"Budget: {expenses['uitgaven_deze_maand']:.2f} euro deze maand")

            if lijnen:
                return "\n".join(lijnen)
            else:
                return "Nog geen app data verzameld."

        except Exception:
            return "Kon cross-app data niet ophalen."

    def get_wisdom_for_emotion(self, emotie: str) -> str:
        """
        Haal wijsheid op passend bij een emotie.

        Args:
            emotie: Huidige emotie van gebruiker of huisdier

        Returns:
            Wijze uitspraak
        """
        wijsheden = {
            "verdriet": [
                "Na regen komt zonneschijn.",
                "Elke storm gaat voorbij.",
                "Het is oké om even niet oké te zijn."
            ],
            "angst": [
                "Moed is niet de afwezigheid van angst, maar doorgaan ondanks.",
                "Eén stap tegelijk. Je bent sterker dan je denkt.",
                "Adem in. Adem uit. Je bent veilig."
            ],
            "vreugde": [
                "Koester dit moment!",
                "Vreugde gedeeld is vreugde verdubbeld.",
                "De beste momenten zijn nu."
            ],
            "nieuwsgierigheid": [
                "Elke vraag is een deur naar kennis.",
                "Blijf nieuwsgierig, blijf groeien.",
                "Wonder is het begin van wijsheid."
            ],
            "moe": [
                "Rust is geen luxe, het is noodzaak.",
                "Even opladen om straks sterker terug te komen.",
                "Soms is niets doen het beste wat je kunt doen."
            ]
        }

        import random
        opties = wijsheden.get(emotie.lower(), [
            "Elk moment is een nieuw begin.",
            "Je bent precies waar je moet zijn.",
            "De reis is belangrijker dan de bestemming."
        ])

        return random.choice(opties)


class NexusOracleMode:
    """
    NEXUS Oracle Mode - Diepe inzichten via Central Brain.

    Wanneer NEXUS level 7+ bereikt, kan Oracle Mode geactiveerd worden
    voor diepere, cross-domain inzichten.
    """

    def __init__(self, bridge: NexusBridge):
        self.bridge = bridge
        self.active = False

    def activate(self) -> bool:
        """Activeer Oracle Mode."""
        if not self.bridge.is_connected():
            return False

        huisdier = self.bridge.huisdier
        if huisdier.get("nexus_level", 1) < 7:
            return False

        self.active = True
        return True

    def deactivate(self):
        """Deactiveer Oracle Mode."""
        self.active = False

    def divine_insight(self, onderwerp: str = None) -> str:
        """
        Genereer een diep inzicht.

        Args:
            onderwerp: Optioneel onderwerp voor het inzicht

        Returns:
            Oracle inzicht
        """
        if not self.active:
            return "Oracle Mode is niet actief."

        if not self.bridge.is_connected():
            return "Verbinding met het Orakel verloren..."

        try:
            # Haal cross-app context
            context = self.bridge.get_cross_app_summary()

            # Formuleer oracle vraag
            if onderwerp:
                vraag = f"Geef een diep, wijselijk inzicht over '{onderwerp}' in de context van: {context}"
            else:
                vraag = f"Geef een diep, wijselijk inzicht gebaseerd op deze context: {context}"

            response = self.bridge.brain.process_request(
                vraag, use_tools=False
            )
            return f"[ORACLE ZIET]\n\n{response}"

        except Exception as e:
            return f"Het Orakel is verstoord: {e}"

    def predict_pattern(self) -> str:
        """
        Voorspel patronen op basis van app data.

        Returns:
            Patroon voorspelling
        """
        if not self.active or not self.bridge.is_connected():
            return "Oracle Mode niet beschikbaar."

        try:
            vraag = (
                "Analyseer de patronen in de"
                " gebruikersdata en geef:\n"
                "1. Een waargenomen patroon\n"
                "2. Een mogelijke toekomstige trend\n"
                "3. Een suggestie voor verbetering\n\n"
                "Wees beknopt maar inzichtelijk."
            )

            return self.bridge.brain.process_request(
                vraag, use_tools=False
            )

        except Exception:
            return "Kon geen patronen detecteren."


def create_nexus_bridge(huisdier_data: dict = None) -> NexusBridge:
    """
    Factory functie voor NexusBridge.

    Args:
        huisdier_data: Huisdier data dictionary

    Returns:
        Geconfigureerde NexusBridge instance
    """
    return NexusBridge(huisdier_data)


def get_nexus_greeting(huisdier_data: dict = None) -> str:
    """
    Genereer een context-aware groet voor NEXUS.

    Args:
        huisdier_data: Huisdier data

    Returns:
        Gepersonaliseerde groet
    """
    bridge = NexusBridge(huisdier_data)

    if not bridge.is_connected():
        return "Hoi! Ik ben er voor je."

    insights = bridge.get_proactive_insights()

    if insights:
        top_insight = insights[0]
        emotie = top_insight.get("emotie", "neutraal")

        greetings = {
            "bezorgd": "Hey... ik maak me een beetje zorgen.",
            "blij": "Hoi! Ik heb goed nieuws!",
            "trots": "Welkom terug, kampioen!",
            "nieuwsgierig": "Oh, ik heb iets ontdekt!",
            "moe": "*geeuw* Hey daar...",
            "neutraal": "Hoi! Fijn je te zien."
        }

        return greetings.get(emotie, "Hoi!")

    return "Hoi! Wat gaan we vandaag doen?"
