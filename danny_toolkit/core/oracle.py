"""
OracleAgent — WAV-Loop (Will-Action-Verification).

De overgang van waarnemer naar operator.
Verbindt de "wil" (LLM reasoning) met de "handen"
(KineticUnit) en de "ogen" (PixelEye) in een
gesloten feedback-lus: Will -> Action -> Verification.

Gebruik:
    from danny_toolkit.core.oracle import OracleAgent
    agent = OracleAgent()
    agent.run()
"""

import asyncio
import json
import sys
import time
from datetime import datetime
from pathlib import Path

from ..agents.base import Agent, AgentConfig
from ..core.config import Config
from ..core.utils import kleur, Kleur, clear_scherm

# Root pad voor kinesis.py import
_root = Path(__file__).parent.parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))


# ─── Constanten ───

MAX_CORRECTIES = 2
REPAIR_LOG_PAD = (
    Config.DATA_DIR / "repair_logs.json"
)

ORACLE_SYSTEM_PROMPT = """\
Je bent Oracle, de uitvoerende agent van Project Omega.
Je taak is om doelstellingen te vertalen naar concrete
computeracties die via muis en toetsenbord worden
uitgevoerd.

Wanneer je een plan maakt, antwoord ALLEEN met een JSON
array van stappen. Geen extra tekst, geen uitleg,
ENKEL de JSON array:

[
  {
    "actie": "launch_app",
    "args": {"app_name": "notepad"},
    "verwachting": "Notepad is geopend"
  },
  {
    "actie": "type_text",
    "args": {"text": "Hallo wereld!"},
    "verwachting": "Tekst 'Hallo wereld!' is zichtbaar"
  }
]

Beschikbare acties:
- type_text: {"text": "...", "interval": 0.05}
- click: {"x": 100, "y": 200, "button": "left", "clicks": 1}
- press_key: {"key": "enter"}
- hotkey: {"keys": ["ctrl", "c"]}
- launch_app: {"app_name": "notepad"}
- scroll: {"amount": 3, "x": null, "y": null}
- drag_drop: {"sx": 0, "sy": 0, "ex": 100, "ey": 100}
- screenshot: {}

Regels:
- Houd stappen klein en verifieerbaar.
- Elke stap heeft een duidelijke verwachting.
- Verwachtingen in het Nederlands.
- Bij correctie: pas ALLEEN de gefaalde stap aan.
"""

# Actie dispatch: actie-type -> (methode_naam, args_mapping)
ACTIE_DISPATCH = {
    "type_text": lambda body, args: body.type_text(
        args.get("text", ""),
        args.get("interval", 0.05),
    ),
    "click": lambda body, args: body.click(
        args.get("x", 0),
        args.get("y", 0),
        args.get("button", "left"),
        args.get("clicks", 1),
    ),
    "press_key": lambda body, args: body.press_key(
        args.get("key", "enter"),
    ),
    "hotkey": lambda body, args: body.hotkey(
        *args.get("keys", []),
    ),
    "launch_app": lambda body, args: body.launch_app(
        args.get("app_name", ""),
    ),
    "scroll": lambda body, args: body.scroll(
        args.get("amount", 0),
        args.get("x"),
        args.get("y"),
    ),
    "drag_drop": lambda body, args: body.drag_drop(
        args.get("sx", 0),
        args.get("sy", 0),
        args.get("ex", 0),
        args.get("ey", 0),
    ),
    "screenshot": lambda body, args: body.take_screenshot(),
}


class OracleAgent(Agent):
    """WAV-Loop operator — Will, Action, Verification.

    Vertaalt doelstellingen naar computeracties via:
    1. _plan()              -> LLM genereert stappen
    2. _execute()           -> KineticUnit voert uit
    3. _verify()            -> PixelEye verifieert
    4. _diagnose_and_fix()  -> diagnose + correctie
    5. execute_mission()    -> extern plan uitvoeren
    """

    def __init__(self, persist=True):
        super().__init__(
            naam="Oracle",
            systeem_prompt=ORACLE_SYSTEM_PROMPT,
            config=AgentConfig(max_iteraties=5),
            persist=persist,
        )
        self._body = None
        self._eye = None
        self._repair_protocol = None
        self.repair_history = []

    # ─── Lazy Properties ───

    @property
    def body(self):
        """Lazy KineticUnit — geen import overhead."""
        if self._body is None:
            from kinesis import KineticUnit
            self._body = KineticUnit()
            self.log("KineticUnit geladen", Kleur.GROEN)
        return self._body

    @property
    def eye(self):
        """Lazy PixelEye — geen import overhead."""
        if self._eye is None:
            from ..skills.pixel_eye import PixelEye
            self._eye = PixelEye()
            self.log("PixelEye geladen", Kleur.GROEN)
        return self._eye

    @property
    def repair_protocol(self):
        """Lazy SelfRepairProtocol."""
        if self._repair_protocol is None:
            from ..core.self_repair import (
                SelfRepairProtocol,
            )
            self._repair_protocol = (
                SelfRepairProtocol()
            )
            self.log(
                "SelfRepairProtocol geladen",
                Kleur.GROEN,
            )
        return self._repair_protocol

    # ─── WAV-Loop Kern ───

    def _extract_text(self, response):
        """Extraheer tekst uit een API response.

        Args:
            response: dict met content blokken.

        Returns:
            str — samengevoegde tekst.
        """
        tekst = ""
        for block in response.get("content", []):
            if isinstance(block, dict):
                tekst += block.get("text", "")
            elif hasattr(block, "text"):
                tekst += block.text
        return tekst

    async def _plan(self, doelstelling):
        """LLM genereert een plan als JSON stappen.

        Args:
            doelstelling: Wat er bereikt moet worden.

        Returns:
            list van stap-dicts, elk met actie,
            args, verwachting.
        """
        self.log(
            f"Planning: {doelstelling[:60]}...",
            Kleur.CYAAN,
        )

        berichten = [{
            "role": "user",
            "content": (
                f"Maak een plan voor: {doelstelling}\n"
                "Antwoord ALLEEN met een JSON array."
            ),
        }]

        response = await self._call_api(berichten)

        # Parse JSON uit het antwoord
        tekst = self._extract_text(response)
        stappen = self._parse_plan_json(tekst)

        if stappen:
            self.log(
                f"Plan: {len(stappen)} stappen",
                Kleur.GROEN,
            )
        else:
            self.log("Geen geldig plan ontvangen", Kleur.ROOD)

        return stappen

    def _parse_plan_json(self, tekst):
        """Parse JSON stappen uit LLM output.

        Zoekt naar een JSON array in de tekst,
        ook als er extra tekst omheen staat.

        Args:
            tekst: Raw LLM output.

        Returns:
            list van stap-dicts of lege lijst.
        """
        tekst = tekst.strip()

        # Probeer directe parse
        try:
            result = json.loads(tekst)
            if isinstance(result, list):
                return result
        except json.JSONDecodeError:
            pass

        # Zoek JSON array in de tekst
        start = tekst.find("[")
        einde = tekst.rfind("]")
        if start != -1 and einde != -1 and einde > start:
            try:
                result = json.loads(tekst[start:einde + 1])
                if isinstance(result, list):
                    return result
            except json.JSONDecodeError:
                pass

        return []

    def _execute(self, stap):
        """Voer een actie-stap uit via KineticUnit.

        Args:
            stap: dict met actie, args, verwachting.

        Returns:
            str resultaat van de actie.
        """
        actie = stap.get("actie", "")
        args = stap.get("args", {})

        self.log(
            f"Uitvoeren: {actie} {args}",
            Kleur.GEEL,
        )

        handler = ACTIE_DISPATCH.get(actie)
        if not handler:
            fout_msg = f"Onbekende actie: {actie}"
            self.log(fout_msg, Kleur.ROOD)
            return fout_msg

        try:
            result = handler(self.body, args)
            self.log(f"Resultaat: {result}", Kleur.GROEN)
            return result
        except Exception as e:
            fout_msg = f"Uitvoerfout: {e}"
            self.log(fout_msg, Kleur.ROOD)
            return fout_msg

    def _verify(self, verwachting):
        """Verifieer via PixelEye of het resultaat klopt.

        Args:
            verwachting: Wat er zichtbaar zou moeten zijn.

        Returns:
            dict met match (bool) en analyse (str).
        """
        self.log(
            f"Verificatie: {verwachting[:50]}...",
            Kleur.MAGENTA,
        )

        result = self.eye.check_state(verwachting)

        if result.get("match"):
            self.log("Verificatie: MATCH", Kleur.GROEN)
        else:
            self.log(
                "Verificatie: GEEN MATCH",
                Kleur.ROOD,
            )

        return result

    def _parse_stap_json(self, tekst):
        """Parse een enkele stap-dict uit LLM output.

        Args:
            tekst: Raw LLM output.

        Returns:
            dict of None.
        """
        tekst = tekst.strip()

        try:
            result = json.loads(tekst)
            if isinstance(result, dict):
                return result
        except json.JSONDecodeError:
            pass

        start = tekst.find("{")
        einde = tekst.rfind("}")
        if start != -1 and einde != -1 and einde > start:
            try:
                result = json.loads(
                    tekst[start:einde + 1]
                )
                if isinstance(result, dict):
                    return result
            except json.JSONDecodeError:
                pass

        return None

    async def _diagnose_and_fix(self, stap, verificatie):
        """Diagnose + fix voor een gefaalde stap.

        Twee-staps correctie:
        1. Diagnose — LLM analyseert wat er mis ging
        2. Fix — LLM stelt gecorrigeerde stap voor
           met diagnose als extra context

        Args:
            stap: De originele stap die faalde.
            verificatie: Het verificatie-resultaat.

        Returns:
            Nieuwe stap-dict of None.
        """
        analyse = verificatie.get("analyse", "onbekend")

        # ── Stap 1: Diagnose ──
        self.log("Diagnose aanvragen...", Kleur.GEEL)

        diag_berichten = [{
            "role": "user",
            "content": (
                f"De volgende stap is mislukt:\n"
                f"{json.dumps(stap, ensure_ascii=False)}"
                f"\n\nVisuele analyse: {analyse}\n\n"
                "Wat ging er mis? Geef een korte"
                " diagnose in 1-2 zinnen."
            ),
        }]

        diag_response = await self._call_api(
            diag_berichten
        )
        diagnose = self._extract_text(
            diag_response
        ).strip() or "Onbekende fout"

        self.log(f"Diagnose: {diagnose[:60]}", Kleur.GEEL)

        # ── Stap 2: Fix ──
        self.log("Correctie aanvragen...", Kleur.GEEL)

        fix_berichten = [{
            "role": "user",
            "content": (
                f"De volgende stap is mislukt:\n"
                f"{json.dumps(stap, ensure_ascii=False)}"
                f"\n\nVisuele analyse: {analyse}"
                f"\nDiagnose: {diagnose}\n\n"
                "Geef EEN gecorrigeerde stap als JSON"
                " object (geen array):\n"
                '{"actie": "...", "args": {...},'
                ' "verwachting": "..."}'
            ),
        }]

        fix_response = await self._call_api(
            fix_berichten
        )
        fix_tekst = self._extract_text(fix_response)
        nieuwe_stap = self._parse_stap_json(fix_tekst)

        # ── Log in repair_history ──
        geslaagd = nieuwe_stap is not None
        self.repair_history.append({
            "stap": stap,
            "fout": analyse,
            "diagnose": diagnose,
            "fix": (
                nieuwe_stap.get("actie", "")
                if nieuwe_stap else "geen fix"
            ),
            "geslaagd": geslaagd,
            "timestamp": datetime.now().isoformat(),
        })

        if not nieuwe_stap:
            self.log(
                "Geen geldige correctie",
                Kleur.ROOD,
            )

        return nieuwe_stap

    async def _execute_plan(self, stappen):
        """Voer een lijst stappen uit met WAV-loop.

        Gedeelde kern voor fulfill_will() en
        execute_mission(). Elke stap wordt uitgevoerd,
        geverifieerd, en bij falen gediagnosticeerd +
        gecorrigeerd (max MAX_CORRECTIES keer).

        Args:
            stappen: list van stap-dicts (actie, args,
                     verwachting).

        Returns:
            list van resultaat-dicts per stap.
        """
        resultaten = []

        for i, stap in enumerate(stappen):
            stap_nr = i + 1
            totaal = len(stappen)
            self.log(
                f"Stap {stap_nr}/{totaal}:"
                f" {stap.get('actie', '?')}",
                Kleur.FEL_GEEL,
            )

            correcties = 0
            huidige_stap = stap

            while correcties <= MAX_CORRECTIES:
                # Uitvoeren
                actie_result = self._execute(
                    huidige_stap
                )

                # Kort wachten voor visuele feedback
                time.sleep(1)

                # Verifieer
                verwachting = huidige_stap.get(
                    "verwachting", ""
                )
                if not verwachting:
                    resultaten.append({
                        "stap": huidige_stap,
                        "result": actie_result,
                        "verificatie": None,
                        "status": "uitgevoerd",
                    })
                    break

                verificatie = self._verify(verwachting)

                if verificatie.get("match"):
                    resultaten.append({
                        "stap": huidige_stap,
                        "result": actie_result,
                        "verificatie": verificatie,
                        "status": "geslaagd",
                    })
                    break

                # Niet gematcht — correctie
                correcties += 1
                if correcties > MAX_CORRECTIES:
                    self.log(
                        f"Max correcties bereikt"
                        f" voor stap {stap_nr}",
                        Kleur.ROOD,
                    )
                    resultaten.append({
                        "stap": huidige_stap,
                        "result": actie_result,
                        "verificatie": verificatie,
                        "status": "gefaald",
                    })
                    break

                self.log(
                    f"Correctie {correcties}/"
                    f"{MAX_CORRECTIES}...",
                    Kleur.GEEL,
                )
                nieuwe_stap = (
                    await self._diagnose_and_fix(
                        huidige_stap, verificatie
                    )
                )
                if nieuwe_stap:
                    huidige_stap = nieuwe_stap
                else:
                    resultaten.append({
                        "stap": huidige_stap,
                        "result": actie_result,
                        "verificatie": verificatie,
                        "status": "gefaald",
                    })
                    break

        return resultaten

    def _exporteer_repair_log(self):
        """Exporteer repair_history naar bestand."""
        if not self.repair_history:
            return

        pad = REPAIR_LOG_PAD

        # Lees bestaande data
        bestaand = {"sessies": []}
        if pad.exists():
            try:
                with open(
                    pad, "r", encoding="utf-8"
                ) as f:
                    bestaand = json.load(f)
            except (json.JSONDecodeError, IOError):
                pass

        # Voeg nieuwe sessie toe
        bestaand["sessies"].append({
            "timestamp":
                datetime.now().isoformat(),
            "entries": self.repair_history,
        })

        # Schrijf terug
        try:
            with open(
                pad, "w", encoding="utf-8"
            ) as f:
                json.dump(
                    bestaand, f, indent=2,
                    ensure_ascii=False,
                )
            self.log(
                f"Repair log:"
                f" {len(self.repair_history)}"
                f" entries opgeslagen",
                Kleur.GROEN,
            )
        except IOError as e:
            self.log(
                f"Repair log export mislukt: {e}",
                Kleur.ROOD,
            )

    def _wrap_resultaten(
        self, doelstelling, resultaten, start
    ):
        """Wrap resultaten in standaard output format.

        Args:
            doelstelling: Beschrijving van de missie.
            resultaten: list van stap-resultaten.
            start: time.time() bij aanvang.

        Returns:
            dict met doelstelling, stappen, geslaagd,
            tijd.
        """
        elapsed = time.time() - start
        geslaagd_count = sum(
            1 for r in resultaten
            if r["status"] in ("geslaagd", "uitgevoerd")
        )
        totaal_geslaagd = (
            geslaagd_count == len(resultaten)
            and len(resultaten) > 0
        )

        status_kleur = (
            Kleur.FEL_GROEN if totaal_geslaagd
            else Kleur.FEL_ROOD
        )
        self.log(
            f"WAV-Loop voltooid:"
            f" {geslaagd_count}/{len(resultaten)}"
            f" stappen OK ({elapsed:.1f}s)",
            status_kleur,
        )

        # Onthoud resultaat
        status = (
            "geslaagd" if totaal_geslaagd
            else "gefaald"
        )
        self.remember(
            f"'{doelstelling[:40]}...': {status}"
            f" ({geslaagd_count}/{len(resultaten)}"
            f" stappen)",
            categorie="wav_loop",
        )

        # Sla repair_history op
        if self.repair_history:
            self.remember(
                f"Repairs: {len(self.repair_history)}"
                f" correcties uitgevoerd",
                categorie="repair_history",
            )
        self._sla_state_op()
        self._exporteer_repair_log()

        return {
            "doelstelling": doelstelling,
            "stappen": resultaten,
            "geslaagd": totaal_geslaagd,
            "tijd": elapsed,
        }

    async def fulfill_will(self, doelstelling):
        """Volledige WAV-loop: Will -> Action -> Verify.

        Genereert een plan via LLM en voert het uit.

        Args:
            doelstelling: Wat er bereikt moet worden.

        Returns:
            dict met doelstelling, stappen (met status),
            geslaagd (bool), tijd.
        """
        start = time.time()
        self.log(
            f"WIL: {doelstelling}",
            Kleur.FEL_CYAAN,
        )

        # 1. WILL — Plan genereren
        stappen = await self._plan(doelstelling)
        if not stappen:
            return {
                "doelstelling": doelstelling,
                "stappen": [],
                "geslaagd": False,
                "tijd": time.time() - start,
                "reden": "Geen plan gegenereerd",
            }

        # 2. ACTION + VERIFICATION
        resultaten = await self._execute_plan(stappen)

        return self._wrap_resultaten(
            doelstelling, resultaten, start
        )

    async def execute_mission(self, intentie, plan):
        """Voer een kant-en-klaar plan uit.

        Verschil met fulfill_will(): slaat LLM planning
        over en gebruikt het meegegeven plan direct.

        Args:
            intentie: Beschrijving van de missie.
            plan: list van stap-dicts, elk met actie,
                  args, verwachting.

        Returns:
            dict met doelstelling, stappen (met status),
            geslaagd (bool), tijd.
        """
        start = time.time()
        self.log(
            f"MISSIE: {intentie}",
            Kleur.FEL_CYAAN,
        )
        self.log(
            f"Plan: {len(plan)} stappen (extern)",
            Kleur.GROEN,
        )

        resultaten = await self._execute_plan(plan)

        return self._wrap_resultaten(
            intentie, resultaten, start
        )

    # ─── Interactieve CLI ───

    def run(self):
        """Start de interactieve Oracle Agent CLI."""
        clear_scherm()
        print(kleur("""
+===============================================+
|                                               |
|     O R A C L E   A G E N T                   |
|                                               |
|     WAV-Loop: Will -> Action -> Verify        |
|                                               |
+===============================================+
        """, Kleur.FEL_CYAAN))

        print(kleur(
            f"  Provider: {self.provider.value}"
            f" ({self.model})",
            Kleur.DIM,
        ))
        print()

        print(kleur("COMMANDO'S:", Kleur.GEEL))
        print("  wil <doel>    - Voer doelstelling"
              " uit (WAV-loop)")
        print("  missie <doel> - Voer extern plan"
              " uit (JSON)")
        print("  plan <doel>   - Toon plan zonder"
              " uitvoering")
        print("  diagnose      - Systeem diagnose")
        print("  repair        - Automatische"
              " reparatie")
        print("  rapport       - Governor health"
              " report")
        print("  status        - Toon agent status")
        print("  ogen          - Screenshot +"
              " analyse")
        print("  stop          - Terug naar"
              " launcher")

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            while True:
                try:
                    cmd = input(kleur(
                        "\n[ORACLE] > ",
                        Kleur.FEL_CYAAN,
                    )).strip()
                    cmd_lower = cmd.lower()

                    if not cmd_lower:
                        continue

                    if cmd_lower in ("stop", "exit", "quit"):
                        break

                    elif cmd_lower.startswith("wil "):
                        doel = cmd[4:].strip()
                        if doel:
                            result = loop.run_until_complete(
                                self.fulfill_will(doel)
                            )
                            self._toon_resultaat(result)
                        else:
                            print("  Geef een doelstelling"
                                  " op.")

                    elif cmd_lower.startswith("missie "):
                        intentie = cmd[7:].strip()
                        if not intentie:
                            print(
                                "  Geef een intentie"
                                " op."
                            )
                            continue
                        print(
                            "  Voer JSON plan in"
                            " (sluit af met lege"
                            " regel):"
                        )
                        regels = []
                        while True:
                            regel = input("  ")
                            if not regel.strip():
                                break
                            regels.append(regel)
                        tekst = "\n".join(regels)
                        plan = (
                            self._parse_plan_json(
                                tekst
                            )
                        )
                        if plan:
                            result = (
                                loop.run_until_complete(
                                    self.execute_mission(
                                        intentie, plan
                                    )
                                )
                            )
                            self._toon_resultaat(
                                result
                            )
                        else:
                            print(kleur(
                                "  Ongeldig JSON plan.",
                                Kleur.ROOD,
                            ))

                    elif cmd_lower.startswith("plan "):
                        doel = cmd[5:].strip()
                        if doel:
                            stappen = (
                                loop.run_until_complete(
                                    self._plan(doel)
                                )
                            )
                            self._toon_plan(stappen)
                        else:
                            print("  Geef een doelstelling"
                                  " op.")

                    elif cmd_lower == "diagnose":
                        d = self.repair_protocol.diagnose()
                        self.repair_protocol.toon_diagnose(
                            d
                        )

                    elif cmd_lower == "repair":
                        r = self.repair_protocol.repair()
                        self.repair_protocol.toon_rapport(r)

                    elif cmd_lower == "rapport":
                        self.repair_protocol.governor\
                            .display_health()

                    elif cmd_lower == "status":
                        self.toon_status()

                    elif cmd_lower == "ogen":
                        vraag = input(
                            "  Vraag (optioneel): "
                        ).strip()
                        result = self.eye.analyze_screen(
                            vraag or None
                        )
                        if result.get("analyse"):
                            print(f"\n{result['analyse']}")

                    else:
                        print(
                            f"  Onbekend commando:"
                            f" {cmd}"
                        )

                except (EOFError, KeyboardInterrupt):
                    break
        finally:
            loop.close()

        self._sla_state_op()
        self._exporteer_repair_log()
        input("\n  Druk op Enter...")

    def _toon_plan(self, stappen):
        """Toon een plan in leesbaar formaat."""
        if not stappen:
            print(kleur(
                "  Geen plan gegenereerd.",
                Kleur.ROOD,
            ))
            return

        print(kleur(
            f"\n  PLAN ({len(stappen)} stappen):",
            Kleur.FEL_GEEL,
        ))
        print(kleur("  " + "-" * 40, Kleur.DIM))

        for i, stap in enumerate(stappen, 1):
            actie = stap.get("actie", "?")
            args = stap.get("args", {})
            verwachting = stap.get("verwachting", "-")

            print(kleur(
                f"\n  [{i}] {actie}",
                Kleur.FEL_CYAAN,
            ))
            print(kleur(
                f"      Args: {json.dumps(args, ensure_ascii=False)}",
                Kleur.DIM,
            ))
            print(kleur(
                f"      Verwacht: {verwachting}",
                Kleur.GEEL,
            ))

    def _toon_resultaat(self, result):
        """Toon WAV-loop resultaat."""
        geslaagd = result.get("geslaagd", False)
        stappen = result.get("stappen", [])
        tijd = result.get("tijd", 0)

        status = "GESLAAGD" if geslaagd else "GEFAALD"
        status_kleur = (
            Kleur.FEL_GROEN if geslaagd
            else Kleur.FEL_ROOD
        )

        print(kleur(
            f"\n  WAV-LOOP: {status} ({tijd:.1f}s)",
            status_kleur,
        ))
        print(kleur("  " + "=" * 40, Kleur.DIM))

        for i, s in enumerate(stappen, 1):
            stap = s.get("stap", {})
            stap_status = s.get("status", "?")

            if stap_status in ("geslaagd", "uitgevoerd"):
                icoon = kleur("[OK]", Kleur.GROEN)
            else:
                icoon = kleur("[X]", Kleur.ROOD)

            print(
                f"  {icoon} Stap {i}:"
                f" {stap.get('actie', '?')}"
                f" -> {stap_status}"
            )


__all__ = ["OracleAgent"]
