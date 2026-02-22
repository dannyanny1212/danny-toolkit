"""
INVENTION #12: THE DEVOPS DAEMON (Ouroboros Loop)
=================================================
Autonome CI-agent die test suites draait, failures analyseert
via LLM, en diagnose + fix-suggesties genereert.

Veiligheidsprincipe: GEEN auto-exec van fixes.
Governor Niveau 2 vereist menselijke goedkeuring voor code-wijzigingen.
Alleen diagnose + suggesties worden gegenereerd.

Gebruik:
    from danny_toolkit.brain import DevOpsDaemon

    daemon = DevOpsDaemon()
    rapport = await daemon.auto_fix_cycle()
"""

import json
import logging
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)
from typing import List, Optional

from groq import AsyncGroq

from danny_toolkit.core.config import Config
from danny_toolkit.core.utils import Kleur

# --- Optional deps (projectconventie: try/except ImportError) ---

HAS_STACK = False
try:
    from danny_toolkit.brain.cortical_stack import get_cortical_stack
    HAS_STACK = True
except ImportError:
    pass

HAS_BUS = False
try:
    from danny_toolkit.core.neural_bus import get_bus, EventTypes
    HAS_BUS = True
except ImportError:
    pass

HAS_BLACKBOX = False
try:
    from danny_toolkit.brain.black_box import BlackBox
    HAS_BLACKBOX = True
except ImportError:
    pass

HAS_GOVERNOR = False
try:
    from danny_toolkit.brain.governor import OmegaGovernor
    HAS_GOVERNOR = True
except ImportError:
    pass


class DevOpsDaemon:
    """
    THE DEVOPS DAEMON (Ouroboros Loop)
    ----------------------------------
    Autonome CI-bewaker die:

    1. Alle test suites draait via run_all_tests.py
    2. Output parst naar per-suite resultaten
    3. Bij falen: LLM-analyse via Groq 70B
    4. Failures opslaat in BlackBox (negatieve RAG)
    5. Events publiceert op NeuralBus
    6. Governor-gevalideerde fix-suggesties genereert

    NOOIT auto-exec — alleen diagnose + suggesties.
    """

    def __init__(self):
        self.client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))
        self.model = "meta-llama/llama-4-scout-17b-16e-instruct"
        self.test_runner = Config.BASE_DIR / "run_all_tests.py"
        self.log_dir = Config.DATA_DIR / "logs" / "devops"
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Optional subsystemen
        self._blackbox = None
        self._bus = None
        self._governor = None
        self._stack = None

        if HAS_BLACKBOX:
            try:
                self._blackbox = BlackBox()
            except Exception as e:
                logger.debug("BlackBox init error: %s", e)

        if HAS_BUS:
            try:
                self._bus = get_bus()
            except Exception as e:
                logger.debug("NeuralBus init error: %s", e)

        if HAS_GOVERNOR:
            try:
                self._governor = OmegaGovernor()
            except Exception as e:
                logger.debug("Governor init error: %s", e)

        if HAS_STACK:
            try:
                self._stack = get_cortical_stack()
            except Exception as e:
                logger.debug("CorticalStack init error: %s", e)

    # =================================================================
    # Core: API Pre-Check
    # =================================================================

    async def check_api_health(self) -> dict:
        """
        Minimale Groq API pre-check (1 token) om rate limits
        te detecteren voordat de zware test cycle start.

        Returns:
            Dict met groq_ok (bool), latency_ms (float), status (str).
        """
        start = time.time()
        try:
            await self.client.chat.completions.create(
                model="qwen/qwen3-32b",
                messages=[{"role": "user", "content": "ok"}],
                max_tokens=1,
            )
            latency = (time.time() - start) * 1000
            return {
                "groq_ok": True,
                "latency_ms": round(latency, 1),
                "status": "healthy",
            }
        except Exception as e:
            latency = (time.time() - start) * 1000
            err = str(e).lower()
            status = "rate_limited" if "429" in err or "rate" in err else f"error: {str(e)[:80]}"
            return {
                "groq_ok": False,
                "latency_ms": round(latency, 1),
                "status": status,
            }

    # =================================================================
    # Core: Health Check
    # =================================================================

    async def run_health_check(self) -> dict:
        """
        Draai alle test suites via run_all_tests.py.

        Returns:
            Dict met geslaagd (bool), suites (list), failures (list), duur (float).
        """
        print(f"{Kleur.CYAAN}🐍 DevOpsDaemon: Starting health check...{Kleur.RESET}")

        if not self.test_runner.exists():
            return {
                "geslaagd": False,
                "suites": [],
                "failures": [{"suite": "runner", "error": f"{self.test_runner} niet gevonden"}],
                "duur": 0.0,
                "raw_output": "",
            }

        start = time.time()
        try:
            result = subprocess.run(
                [sys.executable, str(self.test_runner)],
                capture_output=True,
                text=True,
                timeout=900,
                cwd=str(Config.BASE_DIR),
                encoding="utf-8",
                errors="replace",
            )
            duur = time.time() - start
            stdout = result.stdout or ""
            stderr = result.stderr or ""
            returncode = result.returncode
        except subprocess.TimeoutExpired:
            duur = time.time() - start
            return {
                "geslaagd": False,
                "suites": [],
                "failures": [{"suite": "runner", "error": f"TIMEOUT na {duur:.0f}s"}],
                "duur": duur,
                "raw_output": "",
            }
        except Exception as e:
            duur = time.time() - start
            return {
                "geslaagd": False,
                "suites": [],
                "failures": [{"suite": "runner", "error": str(e)}],
                "duur": duur,
                "raw_output": "",
            }

        suites = self._parse_test_output(stdout)
        failures = [s for s in suites if not s["geslaagd"]]
        alle_groen = returncode == 0 and len(failures) == 0

        rapport = {
            "geslaagd": alle_groen,
            "suites": suites,
            "failures": failures,
            "duur": round(duur, 1),
            "raw_output": stdout[-5000:] if stdout else "",
        }

        status_tekst = (
            f"{Kleur.GROEN}GROEN{Kleur.RESET}" if alle_groen
            else f"{Kleur.ROOD}ROOD ({len(failures)} failures){Kleur.RESET}"
        )
        print(f"{Kleur.CYAAN}🐍 DevOpsDaemon: Health check klaar "
              f"— {status_tekst} ({duur:.1f}s){Kleur.RESET}")

        return rapport

    # =================================================================
    # Core: Failure Analysis via LLM
    # =================================================================

    async def analyze_failure(self, suite: str, error_output: str) -> str:
        """
        Analyseer een test failure via Groq LLM.

        Governor scrubbet PII uit de error output voordat het
        naar de LLM gaat.

        Args:
            suite: Naam van de gefaalde test suite.
            error_output: Ruwe error output (stdout/stderr).

        Returns:
            Analyse string met diagnose + suggestie.
        """
        # Governor: valideer + scrub input
        clean_output = error_output
        if self._governor:
            veilig, reden = self._governor.valideer_input(error_output[:5000])
            if not veilig:
                clean_output = f"[INPUT GEBLOKKEERD: {reden}]"
            else:
                clean_output = self._governor.scrub_pii(error_output[:5000])

        prompt = (
            f"Je bent een DevOps-expert voor het Danny Toolkit Python-project.\n"
            f"De test suite '{suite}' is gefaald.\n\n"
            f"=== TEST OUTPUT ===\n{clean_output}\n=== EINDE ===\n\n"
            f"Geef een beknopte diagnose:\n"
            f"1. Wat is de root cause?\n"
            f"2. Welk bestand/functie is waarschijnlijk verantwoordelijk?\n"
            f"3. Suggestie voor een fix (GEEN code uitvoeren, alleen beschrijving).\n"
            f"Antwoord in het Nederlands, max 200 woorden."
        )

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=500,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"[LLM analyse mislukt: {e}]"

    # =================================================================
    # Core: Full Ouroboros Cycle
    # =================================================================

    async def auto_fix_cycle(self) -> dict:
        """
        Volledige Ouroboros loop:
        1. run_health_check()
        2. Bij groen: log succes, publish event, klaar
        3. Bij rood: analyze_failure() per suite
        4. BlackBox.record_crash() per failure
        5. CorticalStack.log_event() voor audit
        6. NeuralBus.publish() met details

        Returns:
            Dict met status, analyses, en eventuele suggesties.
        """
        print(f"\n{Kleur.MAGENTA}{'=' * 50}{Kleur.RESET}")
        print(f"{Kleur.MAGENTA}  DEVOPS DAEMON — OUROBOROS CYCLE{Kleur.RESET}")
        print(f"{Kleur.MAGENTA}{'=' * 50}{Kleur.RESET}\n")

        # 0. API pre-check — detect rate limits before heavy cycle
        api_health = await self.check_api_health()
        if not api_health["groq_ok"]:
            print(f"{Kleur.GEEL}⚠ Groq API niet beschikbaar: "
                  f"{api_health['status']} — cycle overgeslagen{Kleur.RESET}")
            self._publish_event("health_check", {
                "status": "skipped",
                "reason": api_health["status"],
            })
            return {
                "timestamp": datetime.now().isoformat(),
                "status": "SKIPPED",
                "reason": api_health["status"],
                "analyses": [],
            }

        # 1. Health check
        health = await self.run_health_check()

        rapport = {
            "timestamp": datetime.now().isoformat(),
            "geslaagd": health["geslaagd"],
            "suites": health["suites"],
            "duur": health["duur"],
            "analyses": [],
        }

        # 2. Alles groen — celebrate
        if health["geslaagd"]:
            print(f"\n{Kleur.GROEN}🏆 Alle tests geslaagd! Systeem gezond.{Kleur.RESET}")

            self._log_event("health_check_groen", {
                "suites": len(health["suites"]),
                "duur": health["duur"],
            })

            self._publish_event("health_check", {
                "status": "groen",
                "suites": len(health["suites"]),
                "duur": health["duur"],
            })

            rapport["status"] = "GROEN"
            self._save_report(rapport)
            return rapport

        # 3. Failures gevonden — analyseer
        print(f"\n{Kleur.ROOD}⚠ {len(health['failures'])} suite(s) gefaald. "
              f"Analyse gestart...{Kleur.RESET}\n")

        for failure in health["failures"]:
            suite_naam = failure.get("suite", "onbekend")
            error_text = failure.get("error", health.get("raw_output", ""))

            print(f"{Kleur.GEEL}🔍 Analyseer: {suite_naam}...{Kleur.RESET}")

            # LLM analyse
            analyse = await self.analyze_failure(suite_naam, error_text)

            analyse_entry = {
                "suite": suite_naam,
                "diagnose": analyse,
                "timestamp": datetime.now().isoformat(),
            }
            rapport["analyses"].append(analyse_entry)

            print(f"{Kleur.CYAAN}📋 Diagnose [{suite_naam}]:{Kleur.RESET}")
            print(f"   {analyse[:300]}")
            print()

            # 4. BlackBox — voorkom herhaling
            if self._blackbox:
                try:
                    self._blackbox.record_crash(
                        user_prompt=f"Test failure: {suite_naam}",
                        bad_response=error_text[:500],
                        critique=analyse[:500],
                    )
                except Exception as e:
                    logger.debug("BlackBox record error: %s", e)

            # 5. CorticalStack — audit trail
            self._log_event("test_failure_analyzed", {
                "suite": suite_naam,
                "diagnose_preview": analyse[:200],
            })

        # 6. NeuralBus — cross-app awareness
        self._publish_event("health_check", {
            "status": "rood",
            "failures": [f["suite"] for f in health["failures"]],
            "duur": health["duur"],
            "analyses_count": len(rapport["analyses"]),
        })

        rapport["status"] = "ROOD"
        pad = self._save_report(rapport)

        print(f"\n{Kleur.MAGENTA}{'─' * 50}{Kleur.RESET}")
        print(f"{Kleur.GEEL}📄 Rapport opgeslagen: {pad}{Kleur.RESET}")
        print(f"{Kleur.ROOD}⚠ Handmatige actie vereist voor {len(health['failures'])} "
              f"failure(s).{Kleur.RESET}")
        print(f"{Kleur.MAGENTA}{'=' * 50}{Kleur.RESET}\n")

        return rapport

    # =================================================================
    # Parsing
    # =================================================================

    def _parse_test_output(self, stdout: str) -> List[dict]:
        """
        Parse run_all_tests.py output naar per-suite resultaten.

        Zoekt patronen:
        - "✅ Name: PASS (Xs)" → geslaagd
        - "❌ Name: FAIL (Xs)" → gefaald
        - "Totaal: X/Y geslaagd (Zs)" → totaaloverzicht

        Args:
            stdout: Ruwe stdout van run_all_tests.py.

        Returns:
            Lijst van dicts met suite, geslaagd, duur.
        """
        suites = []

        # Patroon: "  ✅ NeuralBus: PASS (2.3s)" of "  ❌ CLI: FAIL (1.0s)"
        # In het EINDRESULTAAT blok: "  ✅ NeuralBus                   2.3s"
        suite_pattern = re.compile(
            r"[✅❌]\s+(.+?):\s+(PASS|FAIL)\s+\((\d+\.?\d*)s\)"
        )

        # Fallback: parse het EINDRESULTAAT blok
        eindresultaat_pattern = re.compile(
            r"([✅❌])\s+(\S.+?)\s{2,}(\d+\.?\d*)s"
        )

        seen = set()

        # Eerst: zoek expliciete PASS/FAIL regels (meest specifiek)
        for match in suite_pattern.finditer(stdout):
            naam = match.group(1).strip()
            status = match.group(2)
            duur = float(match.group(3))

            if naam not in seen:
                seen.add(naam)
                suites.append({
                    "suite": naam,
                    "geslaagd": status == "PASS",
                    "duur": duur,
                })

        # Als we niks vonden, probeer het EINDRESULTAAT blok
        if not suites:
            for match in eindresultaat_pattern.finditer(stdout):
                icon = match.group(1)
                naam = match.group(2).strip()
                duur = float(match.group(3))

                if naam not in seen:
                    seen.add(naam)
                    suites.append({
                        "suite": naam,
                        "geslaagd": "✅" in icon,
                        "duur": duur,
                    })

        return suites

    # =================================================================
    # Hulpmethoden
    # =================================================================

    def _log_event(self, action: str, details: Optional[dict] = None):
        """Log naar CorticalStack als beschikbaar."""
        if self._stack:
            try:
                self._stack.log_event(
                    actor="devops_daemon",
                    action=action,
                    details=details,
                    source="devops_daemon",
                )
            except Exception as e:
                logger.debug("CorticalStack log error: %s", e)

    def _publish_event(self, sub_type: str, data: dict):
        """Publiceer event op NeuralBus als beschikbaar."""
        if self._bus:
            try:
                self._bus.publish(
                    EventTypes.SYSTEM_EVENT,
                    {"sub_type": f"devops_{sub_type}", **data},
                    bron="devops_daemon",
                )
            except Exception as e:
                logger.debug("NeuralBus publish error: %s", e)

    def _save_report(self, rapport: dict) -> Path:
        """
        Sla rapport op als JSON in de devops log directory.

        Returns:
            Pad naar het opgeslagen rapport.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        pad = self.log_dir / f"devops_{timestamp}.json"

        try:
            with open(pad, "w", encoding="utf-8") as f:
                json.dump(rapport, f, indent=2, ensure_ascii=False, default=str)
        except Exception as e:
            print(f"{Kleur.ROOD}⚠ Rapport opslaan mislukt: {e}{Kleur.RESET}")

        return pad

    def get_stats(self) -> dict:
        """Statistieken van opgeslagen rapporten."""
        rapporten = list(self.log_dir.glob("devops_*.json"))
        laatste = None
        laatste_status = None

        if rapporten:
            nieuwste = max(rapporten, key=lambda p: p.stat().st_mtime)
            try:
                with open(nieuwste, "r", encoding="utf-8") as f:
                    data = json.load(f)
                laatste = data.get("timestamp")
                laatste_status = data.get("status")
            except Exception as e:
                logger.debug("Stats read error: %s", e)

        return {
            "rapporten_totaal": len(rapporten),
            "laatste_check": laatste,
            "laatste_status": laatste_status,
        }
