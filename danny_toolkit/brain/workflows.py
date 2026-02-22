"""
Super-Workflows voor Central Brain.

Definieert de drie hoofd workflows:
1. Health & Life Loop - Fitness, recepten, boodschappen, budget
2. Deep Work Loop - Pomodoro, goals, code analyse, snippets
3. Second Brain Loop - Nieuws, RAG, decision making
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum


class WorkflowStatus(Enum):
    """Status van een workflow."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


@dataclass
class WorkflowStep:
    """Een stap in een workflow."""
    index: int
    app: str
    actie: str
    beschrijving: str
    input_template: Dict[str, str] = field(default_factory=dict)
    output_var: str = None
    depends_on: List[int] = field(default_factory=list)
    optional: bool = False

    # Runtime state
    status: WorkflowStatus = WorkflowStatus.PENDING
    result: Any = None
    error: str = None
    started_at: datetime = None
    completed_at: datetime = None


@dataclass
class WorkflowDefinition:
    """Definitie van een workflow."""
    naam: str
    beschrijving: str
    stappen: List[WorkflowStep]
    categorie: str = "general"
    prioriteit: int = 5

    def get_required_apps(self) -> List[str]:
        """Haal benodigde apps op."""
        return list(set(s.app for s in self.stappen))


# =============================================================================
# SUPER-WORKFLOW DEFINITIONS
# =============================================================================

SUPER_WORKFLOWS: Dict[str, WorkflowDefinition] = {
    "health_life_loop": WorkflowDefinition(
        naam="Health & Life Loop",
        beschrijving="Fitness + Recipe + Boodschappen + Expense integratie",
        categorie="gezondheid",
        prioriteit=9,
        stappen=[
            WorkflowStep(
                index=0,
                app="fitness_tracker",
                actie="get_burned_calories",
                beschrijving="Haal verbrande calorieën van vandaag op",
                input_template={"periode": "vandaag"},
                output_var="verbrande_cals"
            ),
            WorkflowStep(
                index=1,
                app="fitness_tracker",
                actie="check_streak",
                beschrijving="Check workout streak status",
                input_template={},
                output_var="streak_status"
            ),
            WorkflowStep(
                index=2,
                app="recipe_generator",
                actie="generate_protein_meal",
                beschrijving="Genereer eiwitrijk recept op basis van verbrande calorieën",
                input_template={
                    "calorieen": "{verbrande_cals}",
                    "eiwit_gram": "30"
                },
                depends_on=[0],
                output_var="recept"
            ),
            WorkflowStep(
                index=3,
                app="boodschappenlijst",
                actie="add_missing_ingredients",
                beschrijving="Voeg ontbrekende ingrediënten toe aan boodschappenlijst",
                input_template={"ingredienten": "{recept.ingredienten}"},
                depends_on=[2],
                output_var="boodschappen"
            ),
            WorkflowStep(
                index=4,
                app="expense_tracker",
                actie="estimate_cost",
                beschrijving="Schat kosten van boodschappen",
                input_template={"items": "{boodschappen}"},
                depends_on=[3],
                output_var="geschatte_kosten"
            ),
        ]
    ),

    "deep_work_loop": WorkflowDefinition(
        naam="Deep Work Loop",
        beschrijving="Pomodoro + Goals + Code Analyse + Code Snippets",
        categorie="productiviteit",
        prioriteit=8,
        stappen=[
            WorkflowStep(
                index=0,
                app="goals_tracker",
                actie="get_active_goals",
                beschrijving="Haal actieve doelen op",
                input_template={},
                output_var="actieve_doelen"
            ),
            WorkflowStep(
                index=1,
                app="pomodoro_timer",
                actie="start_session",
                beschrijving="Start focus sessie",
                input_template={
                    "duur_min": "25",
                    "taak": "{actieve_doelen[0].titel}"
                },
                depends_on=[0],
                output_var="sessie"
            ),
            WorkflowStep(
                index=2,
                app="code_analyse",
                actie="analyze_if_stuck",
                beschrijving="Analyseer als je vastloopt",
                input_template={"probleem": "{user_input}"},
                optional=True,
                output_var="analyse"
            ),
            WorkflowStep(
                index=3,
                app="code_snippets",
                actie="find_solution",
                beschrijving="Zoek snippet oplossing",
                input_template={"probleem": "{analyse.probleem}"},
                depends_on=[2],
                optional=True,
                output_var="oplossing"
            ),
            WorkflowStep(
                index=4,
                app="goals_tracker",
                actie="update_progress",
                beschrijving="Update voortgang na sessie",
                input_template={
                    "goal_id": "{actieve_doelen[0].id}",
                    "voortgang": "{sessie.voortgang}",
                    "notitie": "Pomodoro sessie voltooid"
                },
                depends_on=[1, 0],
                output_var="voortgang_update"
            ),
        ]
    ),

    "second_brain_loop": WorkflowDefinition(
        naam="Second Brain Loop",
        beschrijving="Nieuws + RAG + Decision Making",
        categorie="kennis",
        prioriteit=8,
        stappen=[
            WorkflowStep(
                index=0,
                app="nieuws_agent",
                actie="get_relevant_news",
                beschrijving="Haal relevant nieuws op",
                input_template={"onderwerp": "{user_interest}"},
                output_var="nieuws"
            ),
            WorkflowStep(
                index=1,
                app="production_rag",
                actie="store_and_index",
                beschrijving="Sla nieuws op in kennisbank",
                input_template={
                    "content": "{nieuws.samenvatting}",
                    "bron": "nieuws"
                },
                depends_on=[0],
                output_var="stored"
            ),
            WorkflowStep(
                index=2,
                app="production_rag",
                actie="query",
                beschrijving="Zoek relevante kennis",
                input_template={"vraag": "{user_question}"},
                output_var="kennis"
            ),
            WorkflowStep(
                index=3,
                app="decision_maker",
                actie="use_knowledge_for_decision",
                beschrijving="Gebruik kennis voor beslissing",
                input_template={"context": "{kennis.resultaten}"},
                depends_on=[2],
                output_var="beslissing"
            ),
        ]
    ),

    "morning_routine": WorkflowDefinition(
        naam="Morning Routine",
        beschrijving="Ochtend check-in workflow",
        categorie="lifestyle",
        prioriteit=7,
        stappen=[
            WorkflowStep(
                index=0,
                app="mood_tracker",
                actie="log_mood",
                beschrijving="Log ochtend mood",
                input_template={"score": "{user_mood}", "notitie": "Ochtend check-in"},
                output_var="mood"
            ),
            WorkflowStep(
                index=1,
                app="agenda_planner",
                actie="get_today",
                beschrijving="Haal agenda van vandaag op",
                input_template={},
                output_var="agenda"
            ),
            WorkflowStep(
                index=2,
                app="goals_tracker",
                actie="get_active_goals",
                beschrijving="Bekijk actieve doelen",
                input_template={},
                output_var="doelen"
            ),
            WorkflowStep(
                index=3,
                app="habit_tracker",
                actie="get_habits",
                beschrijving="Bekijk habits voor vandaag",
                input_template={},
                output_var="habits"
            ),
            WorkflowStep(
                index=4,
                app="weer_agent",
                actie="get_weather",
                beschrijving="Check het weer",
                input_template={"locatie": "Nederland"},
                output_var="weer"
            ),
        ]
    ),

    "evening_review": WorkflowDefinition(
        naam="Evening Review",
        beschrijving="Avond review workflow",
        categorie="lifestyle",
        prioriteit=7,
        stappen=[
            WorkflowStep(
                index=0,
                app="mood_tracker",
                actie="log_mood",
                beschrijving="Log avond mood",
                input_template={"score": "{user_mood}", "notitie": "Avond review"},
                output_var="mood"
            ),
            WorkflowStep(
                index=1,
                app="habit_tracker",
                actie="get_streaks",
                beschrijving="Check habit streaks",
                input_template={},
                output_var="streaks"
            ),
            WorkflowStep(
                index=2,
                app="expense_tracker",
                actie="get_budget_status",
                beschrijving="Check budget status",
                input_template={},
                output_var="budget"
            ),
            WorkflowStep(
                index=3,
                app="fitness_tracker",
                actie="get_stats",
                beschrijving="Bekijk fitness stats van vandaag",
                input_template={"periode": "vandaag"},
                output_var="fitness"
            ),
        ]
    ),
}


class WorkflowEngine:
    """
    Engine voor het uitvoeren van workflows.

    Ondersteunt:
    - Dependency resolution
    - Variable substitution
    - Async execution
    - Error handling
    """

    def __init__(self, app_executor: Callable = None):
        """
        Initialiseer workflow engine.

        Args:
            app_executor: Functie om app acties uit te voeren
                         Signature: (app: str, actie: str, params: dict) -> Any
        """
        self.app_executor = app_executor
        self.running_workflows: Dict[str, WorkflowDefinition] = {}
        self.workflow_history: List[dict] = []

    def set_executor(self, executor: Callable):
        """Set de app executor."""
        self.app_executor = executor

    def list_workflows(self) -> List[dict]:
        """Lijst alle beschikbare workflows."""
        return [
            {
                "naam": w.naam,
                "key": key,
                "beschrijving": w.beschrijving,
                "categorie": w.categorie,
                "stappen": len(w.stappen),
                "apps": w.get_required_apps()
            }
            for key, w in SUPER_WORKFLOWS.items()
        ]

    def get_workflow(self, naam: str) -> Optional[WorkflowDefinition]:
        """Haal workflow definitie op."""
        return SUPER_WORKFLOWS.get(naam)

    def _substitute_variables(
        self,
        template: Dict[str, str],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Substitueer variabelen in template.

        Args:
            template: Input template met {variabele} placeholders
            context: Beschikbare variabelen

        Returns:
            Gesubstitueerde parameters
        """
        result = {}

        for key, value in template.items():
            if isinstance(value, str) and "{" in value:
                # Eenvoudige substitutie
                for var_name, var_value in context.items():
                    placeholder = "{" + var_name + "}"
                    if placeholder in value:
                        if value == placeholder:
                            # Hele waarde is de variabele
                            result[key] = var_value
                        else:
                            # Deel van de string
                            result[key] = value.replace(placeholder, str(var_value))
                        break
                else:
                    result[key] = value
            else:
                result[key] = value

        return result

    async def run_workflow(
        self,
        workflow_naam: str,
        initial_context: Dict[str, Any] = None,
        on_step_complete: Callable = None
    ) -> Dict[str, Any]:
        """
        Voer een workflow uit.

        Args:
            workflow_naam: Naam van de workflow
            initial_context: Initiële variabelen
            on_step_complete: Callback na elke stap

        Returns:
            Workflow resultaten
        """
        workflow = self.get_workflow(workflow_naam)
        if not workflow:
            return {"error": f"Workflow '{workflow_naam}' niet gevonden"}

        if not self.app_executor:
            return {"error": "Geen app executor geconfigureerd"}

        print(f"\n{'='*50}")
        print(f"[WORKFLOW] {workflow.naam}")
        print(f"           {workflow.beschrijving}")
        print(f"{'='*50}")

        # Reset stappen
        for stap in workflow.stappen:
            stap.status = WorkflowStatus.PENDING
            stap.result = None
            stap.error = None

        # Context voor variabele substitutie
        context = initial_context or {}
        results = {}
        completed = set()

        # Track workflow
        self.running_workflows[workflow_naam] = workflow

        try:
            while len(completed) < len(workflow.stappen):
                # Vind volgende uitvoerbare stappen
                ready_steps = []
                for stap in workflow.stappen:
                    if stap.index in completed:
                        continue
                    if all(dep in completed for dep in stap.depends_on):
                        ready_steps.append(stap)

                if not ready_steps:
                    # Geen stappen klaar - mogelijke deadlock
                    pending = [s.index for s in workflow.stappen
                              if s.index not in completed]
                    return {
                        "error": f"Workflow vastgelopen. Pending: {pending}",
                        "partial_results": results
                    }

                # Voer klaarstaande stappen uit
                for stap in ready_steps:
                    stap.status = WorkflowStatus.RUNNING
                    stap.started_at = datetime.now()

                    print(f"\n[STAP {stap.index + 1}] {stap.app}.{stap.actie}")
                    print(f"         {stap.beschrijving}")

                    try:
                        # Substitueer variabelen
                        params = self._substitute_variables(
                            stap.input_template,
                            context
                        )

                        # Voer app actie uit
                        result = await self._execute_step(
                            stap.app,
                            stap.actie,
                            params
                        )

                        stap.result = result
                        stap.status = WorkflowStatus.COMPLETED
                        stap.completed_at = datetime.now()

                        # Sla resultaat op
                        results[f"stap_{stap.index}"] = result
                        if stap.output_var:
                            context[stap.output_var] = result

                        print(f"   [OK] Voltooid")

                        # Callback
                        if on_step_complete:
                            on_step_complete(stap, result)

                    except Exception as e:
                        stap.error = str(e)
                        if stap.optional:
                            stap.status = WorkflowStatus.COMPLETED
                            print(f"   [!] Optionele stap gefaald: {e}")
                        else:
                            stap.status = WorkflowStatus.FAILED
                            print(f"   [X] Gefaald: {e}")
                            return {
                                "error": f"Stap {stap.index} gefaald: {e}",
                                "partial_results": results
                            }

                    completed.add(stap.index)

            # Workflow voltooid
            print(f"\n{'='*50}")
            print(f"[OK] Workflow voltooid!")
            print(f"{'='*50}")

            # Log in history
            self.workflow_history.append({
                "workflow": workflow_naam,
                "timestamp": datetime.now().isoformat(),
                "stappen": len(workflow.stappen),
                "status": "completed"
            })

            return {
                "status": "completed",
                "workflow": workflow_naam,
                "results": results,
                "context": context
            }

        finally:
            del self.running_workflows[workflow_naam]

    async def _execute_step(
        self,
        app: str,
        actie: str,
        params: dict
    ) -> Any:
        """Voer een workflow stap uit."""
        if asyncio.iscoroutinefunction(self.app_executor):
            return await self.app_executor(app, actie, params)
        else:
            return self.app_executor(app, actie, params)

    def run_workflow_sync(
        self,
        workflow_naam: str,
        initial_context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Synchrone wrapper voor run_workflow."""
        return asyncio.run(self.run_workflow(workflow_naam, initial_context))

    def get_workflow_status(self, workflow_naam: str) -> Optional[dict]:
        """Haal status op van running workflow."""
        workflow = self.running_workflows.get(workflow_naam)
        if not workflow:
            return None

        return {
            "naam": workflow.naam,
            "stappen": [
                {
                    "index": s.index,
                    "app": s.app,
                    "actie": s.actie,
                    "status": s.status.value,
                    "error": s.error
                }
                for s in workflow.stappen
            ]
        }

    def get_history(self, limit: int = 10) -> List[dict]:
        """Haal workflow history op."""
        return list(reversed(self.workflow_history[-limit:]))


def get_workflow_by_intent(intent: str) -> Optional[str]:
    """
    Match user intent naar workflow.

    Args:
        intent: User intent beschrijving

    Returns:
        Workflow naam of None
    """
    intent_lower = intent.lower()

    # Health keywords
    if any(w in intent_lower for w in ["workout", "fitness", "recept", "eten",
                                         "calorieën", "boodschappen"]):
        return "health_life_loop"

    # Deep work keywords
    if any(w in intent_lower for w in ["focus", "pomodoro", "code", "programmeren",
                                         "doel", "goal", "werken"]):
        return "deep_work_loop"

    # Knowledge keywords
    if any(w in intent_lower for w in ["nieuws", "kennis", "beslissing",
                                         "research", "informatie"]):
        return "second_brain_loop"

    # Morning keywords
    if any(w in intent_lower for w in ["ochtend", "morning", "opstaan",
                                         "begin dag"]):
        return "morning_routine"

    # Evening keywords
    if any(w in intent_lower for w in ["avond", "evening", "review",
                                         "eind dag"]):
        return "evening_review"

    return None
