"""
Brain CLI - Command-line interface voor Central Brain.

Interactieve interface om met het AI ecosysteem te communiceren.
"""

import json
from datetime import datetime

from ..core.utils import clear_scherm, kleur, fix_encoding
from ..core.config import Config

from .central_brain import CentralBrain
from .workflows import SUPER_WORKFLOWS


class BrainCLI:
    """CLI interface voor Central Brain."""

    VERSIE = "1.0.0"

    def __init__(self):
        fix_encoding()
        print(kleur("\n   Laden van Central Brain...\n", "cyaan"))
        self.brain = CentralBrain()

    def _print_header(self, titel: str):
        """Print een header."""
        clear_scherm()
        print(kleur("""
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║     ██████╗ ██████╗  █████╗ ██╗███╗   ██╗                    ║
║     ██╔══██╗██╔══██╗██╔══██╗██║████╗  ██║                    ║
║     ██████╔╝██████╔╝███████║██║██╔██╗ ██║                    ║
║     ██╔══██╗██╔══██╗██╔══██║██║██║╚██╗██║                    ║
║     ██████╔╝██║  ██║██║  ██║██║██║ ╚████║                    ║
║     ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝╚═╝  ╚═══╝                    ║
║                                                               ║
║              C E N T R A L   B R A I N   v1.0                 ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
""", "cyaan"))
        print(kleur(f"  {titel}", "geel"))
        print()

    def _print_divider(self):
        """Print scheidingslijn."""
        print(kleur("  " + "─" * 55, "cyaan"))

    def run(self):
        """Start de Brain CLI."""
        while True:
            self._print_header("Jouw AI Ecosysteem Orkestrator")

            # Status
            status = self.brain.get_status()
            ai_status = kleur("[AI ACTIEF]", "groen") if status["ai_actief"] else kleur("[OFFLINE]", "geel")
            memory_status = kleur("[MEMORY OK]", "groen") if status["memory_actief"] else kleur("[NO MEM]", "geel")

            print(f"  Status: {ai_status} {memory_status}")
            print(f"  Apps: {status['apps_geregistreerd']} | Tools: {status['tools_beschikbaar']} | Workflows: {status['workflows_beschikbaar']}")
            print()

            # Proactieve suggesties
            suggesties = self.brain.get_proactive_suggestions()
            if suggesties:
                print(kleur("  ★ AANDACHTSPUNTEN", "geel"))
                for s in suggesties[:3]:
                    print(f"     • {s}")
                print()

            self._print_divider()

            # Menu opties
            print(kleur("  HOOFD FUNCTIES", "geel"))
            print(f"     {kleur('1', 'groen')}. Chat met Brain (Function Calling)")
            print(f"     {kleur('2', 'groen')}. Start Workflow")
            print(f"     {kleur('3', 'groen')}. Quick Actions")
            print()

            print(kleur("  WORKFLOWS", "magenta"))
            print(f"     {kleur('h', 'groen')}. Health & Life Loop")
            print(f"     {kleur('d', 'groen')}. Deep Work Loop")
            print(f"     {kleur('s', 'groen')}. Second Brain Loop")
            print(f"     {kleur('m', 'groen')}. Morning Routine")
            print(f"     {kleur('e', 'groen')}. Evening Review")
            print()

            print(kleur("  INFO & STATUS", "cyaan"))
            print(f"     {kleur('4', 'groen')}. Bekijk Apps")
            print(f"     {kleur('5', 'groen')}. Memory Status")
            print(f"     {kleur('6', 'groen')}. Brain Statistieken")
            print()

            print(f"     {kleur('0', 'rood')}. Terug naar Launcher")
            print()

            keuze = input("  Keuze: ").strip().lower()

            if keuze == "0":
                break
            elif keuze == "1":
                self._chat_mode()
            elif keuze == "2":
                self._workflow_menu()
            elif keuze == "3":
                self._quick_actions()
            elif keuze == "4":
                self._bekijk_apps()
            elif keuze == "5":
                self._memory_status()
            elif keuze == "6":
                self._brain_stats()
            elif keuze == "h":
                self._run_workflow("health_life_loop")
            elif keuze == "d":
                self._run_workflow("deep_work_loop")
            elif keuze == "s":
                self._run_workflow("second_brain_loop")
            elif keuze == "m":
                self._run_workflow("morning_routine")
            elif keuze == "e":
                self._run_workflow("evening_review")

    def _chat_mode(self):
        """Interactieve chat met Central Brain."""
        self._print_header("Chat met Central Brain")

        print(kleur("  Je kunt nu chatten met Central Brain.", "cyaan"))
        print(kleur("  Brain kan alle apps aansturen via function calling.", "cyaan"))
        print(kleur("  Typ 'stop' om terug te gaan.\n", "geel"))

        while True:
            try:
                user_input = input(kleur("  Jij: ", "groen")).strip()

                if not user_input:
                    continue

                if user_input.lower() in ["stop", "exit", "quit", "q"]:
                    break

                if user_input.lower() == "clear":
                    self.brain.clear_conversation()
                    continue

                print(kleur("\n  Brain denkt na...\n", "cyaan"))

                response = self.brain.process_request(user_input)

                print(kleur("  Brain:", "magenta"))
                # Wrap response
                for line in response.split("\n"):
                    print(f"    {line}")
                print()

            except KeyboardInterrupt:
                print("\n")
                break

        input("\n  Druk op Enter...")

    def _workflow_menu(self):
        """Workflow selectie menu."""
        self._print_header("Workflow Selectie")

        workflows = self.brain.list_workflows()

        print(kleur("  Beschikbare Workflows:\n", "geel"))

        for i, wf in enumerate(workflows, 1):
            print(f"     {kleur(str(i), 'groen')}. {wf['naam']}")
            print(f"        {wf['beschrijving']}")
            print(f"        Apps: {', '.join(wf['apps'][:4])}")
            print(f"        Stappen: {wf['stappen']}")
            print()

        print(f"     {kleur('0', 'rood')}. Terug")
        print()

        keuze = input("  Kies workflow: ").strip()

        if keuze == "0":
            return

        try:
            idx = int(keuze) - 1
            if 0 <= idx < len(workflows):
                self._run_workflow(workflows[idx]["key"])
        except ValueError:
            # Probeer op naam
            for wf in workflows:
                if keuze.lower() in wf["key"]:
                    self._run_workflow(wf["key"])
                    break

    def _run_workflow(self, workflow_naam: str):
        """Voer een workflow uit."""
        self._print_header(f"Workflow: {workflow_naam}")

        workflow = SUPER_WORKFLOWS.get(workflow_naam)
        if not workflow:
            print(kleur(f"  Workflow '{workflow_naam}' niet gevonden.", "rood"))
            input("\n  Druk op Enter...")
            return

        print(kleur(f"  {workflow.beschrijving}\n", "cyaan"))
        print(f"  Apps: {', '.join(workflow.get_required_apps())}")
        print(f"  Stappen: {len(workflow.stappen)}")
        print()

        # Vraag om bevestiging
        bevestig = input("  Start workflow? (j/n): ").strip().lower()
        if bevestig != "j":
            return

        print()

        # Vraag optioneel om context
        context = {}
        print(kleur("  Optionele context (leeg = skip):", "geel"))

        if workflow_naam == "health_life_loop":
            cals = input("    Verbrande calorieën [auto]: ").strip()
            if cals:
                context["verbrande_cals"] = int(cals)

        elif workflow_naam == "second_brain_loop":
            interest = input("    Onderwerp van interesse: ").strip()
            if interest:
                context["user_interest"] = interest
            question = input("    Vraag voor kennisbank: ").strip()
            if question:
                context["user_question"] = question

        elif workflow_naam in ["morning_routine", "evening_review"]:
            mood = input("    Huidige mood (1-10): ").strip()
            if mood:
                context["user_mood"] = int(mood)

        print()

        # Voer workflow uit
        result = self.brain.run_workflow(workflow_naam, context)

        print()
        self._print_divider()

        if result.get("error"):
            print(kleur(f"  [ERROR] {result['error']}", "rood"))
        else:
            print(kleur("  [OK] Workflow voltooid!", "groen"))
            print()

            # Toon resultaten
            if "results" in result:
                print(kleur("  Resultaten:", "geel"))
                for key, value in result["results"].items():
                    if isinstance(value, dict):
                        print(f"    {key}: {json.dumps(value, ensure_ascii=False)[:100]}...")
                    else:
                        print(f"    {key}: {str(value)[:100]}")

        input("\n  Druk op Enter...")

    def _quick_actions(self):
        """Snelle acties menu."""
        self._print_header("Quick Actions")

        print(kleur("  Snelle vragen aan Brain:\n", "geel"))

        actions = [
            ("Hoe gaat het met mijn fitness?", "fitness_tracker"),
            ("Wat is mijn mood trend?", "mood_tracker"),
            ("Hoeveel heb ik uitgegeven?", "expense_tracker"),
            ("Wat zijn mijn actieve doelen?", "goals_tracker"),
            ("Wat staat er op de agenda?", "agenda_planner"),
            ("Genereer een gezond recept", "recipe_generator"),
        ]

        for i, (vraag, app) in enumerate(actions, 1):
            print(f"     {kleur(str(i), 'groen')}. {vraag}")

        print(f"\n     {kleur('0', 'rood')}. Terug")
        print()

        keuze = input("  Keuze: ").strip()

        if keuze == "0":
            return

        try:
            idx = int(keuze) - 1
            if 0 <= idx < len(actions):
                vraag, _ = actions[idx]
                print(kleur(f"\n  Vraag: {vraag}\n", "cyaan"))
                print(kleur("  Brain denkt na...\n", "geel"))

                response = self.brain.process_request(vraag)

                print(kleur("  Antwoord:", "magenta"))
                for line in response.split("\n"):
                    print(f"    {line}")

        except ValueError:
            pass

        input("\n  Druk op Enter...")

    def _bekijk_apps(self):
        """Bekijk alle beschikbare apps."""
        self._print_header("Beschikbare Apps")

        apps = self.brain.list_apps()

        # Groepeer per categorie
        by_cat = {}
        for app in apps:
            cat = app["categorie"]
            if cat not in by_cat:
                by_cat[cat] = []
            by_cat[cat].append(app)

        for cat, cat_apps in sorted(by_cat.items()):
            print(kleur(f"  ═══ {cat.upper()} ═══", "geel"))
            for app in sorted(cat_apps, key=lambda x: -x["prioriteit"]):
                prio = "★" * min(app["prioriteit"], 5)
                print(f"    {app['naam']} {kleur(prio, 'geel')}")
                print(f"      {app['beschrijving'][:60]}")
                print(f"      Acties: {', '.join(app['acties'][:5])}")
                print()

        input("\n  Druk op Enter...")

    def _memory_status(self):
        """Toon memory status."""
        self._print_header("Unified Memory Status")

        stats = self.brain.memory_stats()

        if stats.get("status") == "niet_actief":
            print(kleur("  Memory is niet actief.", "geel"))
        else:
            print(kleur("  Memory Statistieken:\n", "cyaan"))
            print(f"    Totaal events:    {stats.get('totaal_events', 0)}")
            print(f"    Vector documents: {stats.get('vector_docs', 0)}")
            print(f"    Actieve apps:     {stats.get('apps_actief', 0)}")

            per_app = stats.get("per_app", {})
            if per_app:
                print(kleur("\n  Events per app:", "geel"))
                for app, count in sorted(per_app.items(),
                                         key=lambda x: -x[1])[:10]:
                    print(f"    {app}: {count}")

            if stats.get("nieuwste_event"):
                print(f"\n  Nieuwste event: {stats['nieuwste_event'][:19]}")

        # Context preview
        if self.brain.unified_memory:
            print(kleur("\n  Huidige Context:", "magenta"))
            context = self.brain.unified_memory.get_user_context()

            for key, value in context.items():
                if key == "timestamp":
                    continue
                if isinstance(value, dict):
                    status = value.get("status", "")
                    print(f"    {key}: {status}")
                elif isinstance(value, list):
                    print(f"    {key}: {len(value)} items")

        input("\n  Druk op Enter...")

    def _brain_stats(self):
        """Toon brain statistieken."""
        self._print_header("Brain Statistieken")

        status = self.brain.get_status()
        stats = status.get("statistieken", {})

        print(kleur("  Systeem Status:\n", "cyaan"))
        print(f"    Versie:              {status['versie']}")
        print(f"    AI Actief:           {'Ja' if status['ai_actief'] else 'Nee'}")
        print(f"    Memory Actief:       {'Ja' if status['memory_actief'] else 'Nee'}")
        print(f"    Apps Geregistreerd:  {status['apps_geregistreerd']}")
        print(f"    Apps Geladen:        {status['apps_geladen']}")
        print(f"    Tools Beschikbaar:   {status['tools_beschikbaar']}")

        print(kleur("\n  Gebruik Statistieken:\n", "geel"))
        print(f"    Requests Verwerkt:   {stats.get('requests_verwerkt', 0)}")
        print(f"    Tool Calls:          {stats.get('tool_calls', 0)}")
        print(f"    Workflows Uitgevoerd: {stats.get('workflows_uitgevoerd', 0)}")

        if stats.get("laatste_gebruik"):
            print(f"    Laatste Gebruik:     {stats['laatste_gebruik'][:19]}")

        input("\n  Druk op Enter...")


def main():
    """Start Brain CLI."""
    cli = BrainCLI()
    cli.run()


if __name__ == "__main__":
    main()
