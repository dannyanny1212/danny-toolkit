"""
Multi-Agent Orchestrator.
Versie 2.0 - Met task queue, workflows, monitoring, retry logic en meer!
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from collections import deque
from typing import Callable, Optional, Any
from enum import Enum

from .base import Agent
from ..core.config import Config
from ..core.utils import kleur


class TaskStatus(Enum):
    """Status van een taak."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class TaskPriority(Enum):
    """Prioriteit van een taak."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


class Task:
    """Representatie van een taak."""

    def __init__(self, agent_naam: str, taak: str,
                 priority: TaskPriority = TaskPriority.NORMAL,
                 timeout: float = 60.0,
                 retries: int = 0,
                 metadata: dict = None):
        self.id = datetime.now().strftime("%Y%m%d%H%M%S%f")
        self.agent_naam = agent_naam
        self.taak = taak
        self.priority = priority
        self.timeout = timeout
        self.max_retries = retries
        self.retry_count = 0
        self.metadata = metadata or {}
        self.status = TaskStatus.PENDING
        self.result = None
        self.error = None
        self.created_at = datetime.now()
        self.started_at = None
        self.completed_at = None

    def to_dict(self) -> dict:
        """Converteer naar dictionary."""
        return {
            "id": self.id,
            "agent_naam": self.agent_naam,
            "taak": self.taak[:100],
            "priority": self.priority.name,
            "status": self.status.value,
            "retry_count": self.retry_count,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error": str(self.error) if self.error else None,
        }


class Workflow:
    """Definitie van een workflow met meerdere stappen."""

    def __init__(self, naam: str, beschrijving: str = ""):
        self.naam = naam
        self.beschrijving = beschrijving
        self.stappen: list[dict] = []
        self.variabelen: dict = {}

    def voeg_stap_toe(self, agent_naam: str, taak_template: str,
                      depends_on: list[int] = None,
                      output_var: str = None):
        """Voeg een stap toe aan de workflow."""
        stap = {
            "index": len(self.stappen),
            "agent_naam": agent_naam,
            "taak_template": taak_template,
            "depends_on": depends_on or [],
            "output_var": output_var,
            "status": TaskStatus.PENDING,
            "result": None,
        }
        self.stappen.append(stap)
        return len(self.stappen) - 1

    def set_variabele(self, naam: str, waarde: Any):
        """Stel een workflow variabele in."""
        self.variabelen[naam] = waarde


class Orchestrator:
    """
    Coordineert meerdere agents voor complexe taken - Uitgebreide versie.
    """

    def __init__(self):
        Config.ensure_dirs()
        self.agents: dict[str, Agent] = {}
        self.task_queue: deque[Task] = deque()
        self.active_tasks: dict[str, Task] = {}
        self.completed_tasks: list[Task] = []
        self.workflows: dict[str, Workflow] = {}
        self.data_file = Config.DATA_DIR / "orchestrator_data.json"
        self.data = self._laad_data()

        # Event hooks
        self.on_task_start: list[Callable] = []
        self.on_task_complete: list[Callable] = []
        self.on_task_fail: list[Callable] = []

        # Statistics
        self.stats = {
            "taken_voltooid": 0,
            "taken_gefaald": 0,
            "totale_uitvoertijd": 0.0,
        }

    def _laad_data(self) -> dict:
        """Laad opgeslagen orchestrator data."""
        if self.data_file.exists():
            with open(self.data_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return self._standaard_data()

    def _standaard_data(self) -> dict:
        """Standaard data structuur."""
        return {
            "taak_geschiedenis": [],
            "statistieken": {
                "totaal_taken": 0,
                "succesvolle_taken": 0,
                "gefaalde_taken": 0,
                "totale_uitvoertijd_sec": 0.0,
                "gemiddelde_uitvoertijd_sec": 0.0,
            },
            "workflow_runs": [],
        }

    def _sla_data_op(self):
        """Sla data op naar bestand."""
        with open(self.data_file, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)

    def registreer(self, agent: Agent):
        """Registreer een agent."""
        self.agents[agent.naam] = agent
        print(kleur(f"   [OK] Agent '{agent.naam}' geregistreerd", "groen"))

    def verwijder_agent(self, agent_naam: str) -> bool:
        """Verwijder een agent."""
        if agent_naam in self.agents:
            del self.agents[agent_naam]
            print(kleur(f"   [OK] Agent '{agent_naam}' verwijderd", "geel"))
            return True
        return False

    def lijst_agents(self) -> list[str]:
        """Lijst alle geregistreerde agents."""
        return list(self.agents.keys())

    def get_agent_info(self, agent_naam: str) -> dict:
        """Haal agent informatie op."""
        agent = self.agents.get(agent_naam)
        if not agent:
            return None

        return {
            "naam": agent.naam,
            "type": type(agent).__name__,
            "heeft_tools": hasattr(agent, "tools") and bool(agent.tools),
        }

    # === Task Queue Management ===

    def queue_task(self, agent_naam: str, taak: str,
                   priority: TaskPriority = TaskPriority.NORMAL,
                   timeout: float = 60.0,
                   retries: int = 0,
                   metadata: dict = None) -> Task:
        """Voeg een taak toe aan de queue."""
        task = Task(
            agent_naam=agent_naam,
            taak=taak,
            priority=priority,
            timeout=timeout,
            retries=retries,
            metadata=metadata
        )

        # Sorteer op prioriteit (high priority eerst)
        inserted = False
        for i, existing in enumerate(self.task_queue):
            if task.priority.value > existing.priority.value:
                self.task_queue.insert(i, task)
                inserted = True
                break

        if not inserted:
            self.task_queue.append(task)

        print(kleur(f"   [+] Taak {task.id[:8]}... toegevoegd "
                   f"(priority: {priority.name})", "cyaan"))
        return task

    def get_queue_status(self) -> dict:
        """Haal queue status op."""
        return {
            "pending": len(self.task_queue),
            "active": len(self.active_tasks),
            "completed": len(self.completed_tasks),
            "by_priority": {
                "CRITICAL": sum(1 for t in self.task_queue
                               if t.priority == TaskPriority.CRITICAL),
                "HIGH": sum(1 for t in self.task_queue
                           if t.priority == TaskPriority.HIGH),
                "NORMAL": sum(1 for t in self.task_queue
                             if t.priority == TaskPriority.NORMAL),
                "LOW": sum(1 for t in self.task_queue
                          if t.priority == TaskPriority.LOW),
            }
        }

    def cancel_task(self, task_id: str) -> bool:
        """Annuleer een taak."""
        for task in self.task_queue:
            if task.id == task_id:
                task.status = TaskStatus.CANCELLED
                self.task_queue.remove(task)
                print(kleur(f"   [X] Taak {task_id[:8]}... geannuleerd", "geel"))
                return True
        return False

    # === Event Hooks ===

    def add_hook(self, event: str, callback: Callable):
        """Voeg een event hook toe."""
        if event == "task_start":
            self.on_task_start.append(callback)
        elif event == "task_complete":
            self.on_task_complete.append(callback)
        elif event == "task_fail":
            self.on_task_fail.append(callback)

    def _trigger_hooks(self, event: str, task: Task):
        """Trigger event hooks."""
        hooks = {
            "task_start": self.on_task_start,
            "task_complete": self.on_task_complete,
            "task_fail": self.on_task_fail,
        }.get(event, [])

        for hook in hooks:
            try:
                hook(task)
            except Exception as e:
                print(kleur(f"   [!] Hook error: {e}", "rood"))

    # === Task Execution ===

    async def _execute_task(self, task: Task) -> str:
        """Voer een enkele taak uit met timeout en retry."""
        agent = self.agents.get(task.agent_naam)
        if not agent:
            task.status = TaskStatus.FAILED
            task.error = f"Agent '{task.agent_naam}' niet gevonden"
            return None

        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now()
        self.active_tasks[task.id] = task
        self._trigger_hooks("task_start", task)

        print(kleur(f"\n[RUN] {task.agent_naam}: {task.taak[:40]}...", "cyaan"))

        while task.retry_count <= task.max_retries:
            try:
                # Uitvoeren met timeout
                result = await asyncio.wait_for(
                    agent.run(task.taak),
                    timeout=task.timeout
                )

                task.status = TaskStatus.COMPLETED
                task.result = result
                task.completed_at = datetime.now()

                # Bereken uitvoertijd
                duration = (task.completed_at - task.started_at).total_seconds()
                self.stats["taken_voltooid"] += 1
                self.stats["totale_uitvoertijd"] += duration

                # Update persistente stats
                self.data["statistieken"]["totaal_taken"] += 1
                self.data["statistieken"]["succesvolle_taken"] += 1
                self.data["statistieken"]["totale_uitvoertijd_sec"] += duration

                self._trigger_hooks("task_complete", task)
                print(kleur(f"   [OK] Voltooid in {duration:.2f}s", "groen"))

                return result

            except asyncio.TimeoutError:
                task.retry_count += 1
                if task.retry_count <= task.max_retries:
                    print(kleur(f"   [!] Timeout - retry {task.retry_count}/"
                               f"{task.max_retries}", "geel"))
                else:
                    task.status = TaskStatus.TIMEOUT
                    task.error = f"Timeout na {task.timeout}s"

            except Exception as e:
                task.retry_count += 1
                if task.retry_count <= task.max_retries:
                    print(kleur(f"   [!] Error - retry {task.retry_count}/"
                               f"{task.max_retries}: {e}", "geel"))
                else:
                    task.status = TaskStatus.FAILED
                    task.error = str(e)

        # Taak gefaald
        task.completed_at = datetime.now()
        self.stats["taken_gefaald"] += 1
        self.data["statistieken"]["totaal_taken"] += 1
        self.data["statistieken"]["gefaalde_taken"] += 1

        self._trigger_hooks("task_fail", task)
        print(kleur(f"   [X] Gefaald: {task.error}", "rood"))

        return None

    async def delegeer(self, agent_naam: str, taak: str,
                       timeout: float = 60.0) -> str:
        """Delegeer een taak aan een specifieke agent."""
        task = Task(agent_naam=agent_naam, taak=taak, timeout=timeout)
        result = await self._execute_task(task)

        # Cleanup
        if task.id in self.active_tasks:
            del self.active_tasks[task.id]
        self.completed_tasks.append(task)

        # Log opslaan
        self.data["taak_geschiedenis"].append(task.to_dict())
        if len(self.data["taak_geschiedenis"]) > 100:
            self.data["taak_geschiedenis"] = self.data["taak_geschiedenis"][-100:]
        self._sla_data_op()

        return result or f"[FAILED] {task.error}"

    async def process_queue(self, max_concurrent: int = 3) -> list[str]:
        """Verwerk alle taken in de queue."""
        if not self.task_queue:
            print(kleur("[INFO] Queue is leeg", "geel"))
            return []

        print(kleur(f"\n[QUEUE] {len(self.task_queue)} taken verwerken "
                   f"(max {max_concurrent} parallel)...", "cyaan"))

        resultaten = []
        semaphore = asyncio.Semaphore(max_concurrent)

        async def process_with_semaphore(task: Task):
            async with semaphore:
                result = await self._execute_task(task)
                if task.id in self.active_tasks:
                    del self.active_tasks[task.id]
                self.completed_tasks.append(task)
                return result

        tasks_to_process = list(self.task_queue)
        self.task_queue.clear()

        coroutines = [process_with_semaphore(t) for t in tasks_to_process]
        results = await asyncio.gather(*coroutines, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                resultaten.append(f"[ERROR] {result}")
            else:
                resultaten.append(result or "[NO RESULT]")

        self._sla_data_op()
        return resultaten

    async def pipeline(self, taken: list[tuple[str, str]],
                       stop_on_error: bool = True) -> list[str]:
        """
        Voer taken sequentieel uit.

        Args:
            taken: List van (agent_naam, taak) tuples
            stop_on_error: Stop bij eerste fout
        """
        resultaten = []
        context = {}  # Deel resultaten tussen stappen

        for i, (agent_naam, taak) in enumerate(taken, 1):
            print(kleur(f"\n{'='*50}", "cyaan"))
            print(kleur(f"[STAP {i}/{len(taken)}] {agent_naam}", "cyaan"))
            print(kleur("=" * 50, "cyaan"))

            # Vervang placeholders met eerdere resultaten
            for key, value in context.items():
                taak = taak.replace(f"{{{key}}}", str(value)[:500])

            result = await self.delegeer(agent_naam, taak)
            resultaten.append(result)

            # Sla resultaat op voor volgende stappen
            context[f"stap_{i}"] = result
            context["vorige"] = result

            if stop_on_error and result.startswith("[FAILED]"):
                print(kleur(f"\n[!] Pipeline gestopt bij stap {i}", "rood"))
                break

        return resultaten

    async def parallel(self, taken: list[tuple[str, str]],
                       timeout: float = 120.0) -> list[str]:
        """
        Voer taken parallel uit.

        Args:
            taken: List van (agent_naam, taak) tuples
            timeout: Totale timeout voor alle taken
        """
        print(kleur(f"\n[PARALLEL] {len(taken)} taken starten...", "cyaan"))

        async def run_task(agent_naam: str, taak: str):
            return await self.delegeer(agent_naam, taak)

        try:
            coroutines = [run_task(an, t) for an, t in taken]
            resultaten = await asyncio.wait_for(
                asyncio.gather(*coroutines, return_exceptions=True),
                timeout=timeout
            )

            return [
                str(r) if not isinstance(r, Exception) else f"[ERROR] {r}"
                for r in resultaten
            ]
        except asyncio.TimeoutError:
            print(kleur("[!] Parallel timeout bereikt", "rood"))
            return ["[TIMEOUT]" for _ in taken]

    # === Workflow Engine ===

    def create_workflow(self, naam: str, beschrijving: str = "") -> Workflow:
        """Maak een nieuwe workflow."""
        workflow = Workflow(naam, beschrijving)
        self.workflows[naam] = workflow
        return workflow

    async def run_workflow(self, workflow_naam: str,
                           variabelen: dict = None) -> dict:
        """Voer een workflow uit."""
        workflow = self.workflows.get(workflow_naam)
        if not workflow:
            return {"error": f"Workflow '{workflow_naam}' niet gevonden"}

        print(kleur(f"\n{'='*50}", "magenta"))
        print(kleur(f"[WORKFLOW] {workflow.naam}", "magenta"))
        if workflow.beschrijving:
            print(kleur(f"           {workflow.beschrijving}", "magenta"))
        print(kleur("=" * 50, "magenta"))

        # Zet variabelen
        if variabelen:
            for k, v in variabelen.items():
                workflow.set_variabele(k, v)

        resultaten = {}
        voltooid = set()

        while len(voltooid) < len(workflow.stappen):
            for stap in workflow.stappen:
                if stap["index"] in voltooid:
                    continue

                # Check dependencies
                deps_ok = all(d in voltooid for d in stap["depends_on"])
                if not deps_ok:
                    continue

                # Vervang variabelen in taak
                taak = stap["taak_template"]
                for var_naam, var_waarde in workflow.variabelen.items():
                    taak = taak.replace(f"{{{var_naam}}}", str(var_waarde))

                print(kleur(f"\n[STAP {stap['index'] + 1}] "
                           f"{stap['agent_naam']}", "cyaan"))

                result = await self.delegeer(stap["agent_naam"], taak)
                stap["result"] = result
                stap["status"] = TaskStatus.COMPLETED

                # Sla output op als variabele
                if stap["output_var"]:
                    workflow.set_variabele(stap["output_var"], result)

                resultaten[stap["index"]] = result
                voltooid.add(stap["index"])

        # Log workflow run
        self.data["workflow_runs"].append({
            "workflow": workflow_naam,
            "datum": datetime.now().isoformat(),
            "stappen": len(workflow.stappen),
            "variabelen": list(workflow.variabelen.keys()),
        })
        self._sla_data_op()

        return {
            "workflow": workflow_naam,
            "stappen": len(workflow.stappen),
            "resultaten": resultaten,
        }

    # === Monitoring & Statistics ===

    def toon_status(self):
        """Toon orchestrator status."""
        queue_status = self.get_queue_status()

        print(kleur("\n╔════════════════════════════════════════════════════╗", "cyaan"))
        print(kleur("║           ORCHESTRATOR STATUS                      ║", "cyaan"))
        print(kleur("╠════════════════════════════════════════════════════╣", "cyaan"))
        print(kleur("║  AGENTS                                            ║", "cyaan"))
        print(f"║  Geregistreerd:         {len(self.agents):>20}  ║")
        for naam in list(self.agents.keys())[:5]:
            print(f"║    • {naam:<40}  ║")
        if len(self.agents) > 5:
            print(f"║    ... en {len(self.agents) - 5} meer{' '*28}║")
        print(kleur("║                                                    ║", "cyaan"))
        print(kleur("║  TASK QUEUE                                        ║", "cyaan"))
        print(f"║  Pending:               {queue_status['pending']:>20}  ║")
        print(f"║  Active:                {queue_status['active']:>20}  ║")
        print(f"║  Completed:             {queue_status['completed']:>20}  ║")
        print(kleur("║                                                    ║", "cyaan"))
        print(kleur("║  STATISTIEKEN                                      ║", "cyaan"))
        s = self.data["statistieken"]
        print(f"║  Totaal taken:          {s['totaal_taken']:>20}  ║")
        print(f"║  Succesvol:             {s['succesvolle_taken']:>20}  ║")
        print(f"║  Gefaald:               {s['gefaalde_taken']:>20}  ║")
        if s['totaal_taken'] > 0:
            success_rate = (s['succesvolle_taken'] / s['totaal_taken']) * 100
            print(f"║  Success rate:          {success_rate:>19.1f}%  ║")
            avg_time = s['totale_uitvoertijd_sec'] / s['totaal_taken']
            print(f"║  Gem. uitvoertijd:      {avg_time:>18.2f}s  ║")
        print(kleur("╚════════════════════════════════════════════════════╝", "cyaan"))

    def toon_log(self, limit: int = 10):
        """Toon de taak log."""
        geschiedenis = self.data["taak_geschiedenis"]

        if not geschiedenis:
            print(kleur("[INFO] Geen taak geschiedenis", "geel"))
            return

        print(kleur("\n=== RECENTE TAKEN ===", "cyaan"))

        for item in reversed(geschiedenis[-limit:]):
            status_kleur = "groen" if item["status"] == "completed" else "rood"
            datum = datetime.fromisoformat(item["created_at"]).strftime("%d-%m %H:%M")
            print(f"\n  [{datum}] {kleur(item['agent_naam'], 'geel')}")
            print(f"    Taak: {item['taak']}")
            print(f"    Status: {kleur(item['status'], status_kleur)}")
            if item.get("error"):
                print(f"    Error: {kleur(item['error'], 'rood')}")

    def toon_workflows(self):
        """Toon gedefinieerde workflows."""
        if not self.workflows:
            print(kleur("[INFO] Geen workflows gedefinieerd", "geel"))
            return

        print(kleur("\n=== WORKFLOWS ===", "magenta"))

        for naam, workflow in self.workflows.items():
            print(f"\n  {kleur(naam, 'geel')}")
            if workflow.beschrijving:
                print(f"    {workflow.beschrijving}")
            print(f"    Stappen: {len(workflow.stappen)}")
            for stap in workflow.stappen:
                deps = f" (depends: {stap['depends_on']})" if stap['depends_on'] else ""
                print(f"      {stap['index'] + 1}. {stap['agent_naam']}{deps}")

    def reset_stats(self):
        """Reset statistieken."""
        self.data["statistieken"] = {
            "totaal_taken": 0,
            "succesvolle_taken": 0,
            "gefaalde_taken": 0,
            "totale_uitvoertijd_sec": 0.0,
            "gemiddelde_uitvoertijd_sec": 0.0,
        }
        self.stats = {
            "taken_voltooid": 0,
            "taken_gefaald": 0,
            "totale_uitvoertijd": 0.0,
        }
        self._sla_data_op()
        print(kleur("[OK] Statistieken gereset", "groen"))

    def clear_queue(self):
        """Wis de task queue."""
        count = len(self.task_queue)
        self.task_queue.clear()
        print(kleur(f"[OK] {count} taken uit queue verwijderd", "groen"))

    def export_stats(self) -> dict:
        """Exporteer statistieken."""
        return {
            "agents": self.lijst_agents(),
            "queue_status": self.get_queue_status(),
            "statistieken": self.data["statistieken"],
            "workflows": list(self.workflows.keys()),
            "recent_tasks": self.data["taak_geschiedenis"][-10:],
        }
