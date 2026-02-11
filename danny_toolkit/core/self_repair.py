"""
SelfRepairProtocol — Zelf-diagnose en -reparatie.

Verbindt Governor's diagnostiek met deterministische fixes
en LLM-fallback. Drie commando's:
  - diagnose: classificeer problemen via health report
  - repair:   diagnose -> fix per probleem -> herdiagnose
  - rapport:  visueel gezondheidsrapport

Gebruik:
    from danny_toolkit.core.self_repair import SelfRepairProtocol
    sr = SelfRepairProtocol()
    d = sr.diagnose()
    r = sr.repair()
"""

import asyncio
import time
from datetime import datetime

from ..core.utils import kleur, Kleur
from ..core.config import Config


class SelfRepairProtocol:
    """Zelf-diagnose en -reparatie via Governor + LLM."""

    def __init__(self):
        self._governor = None
        self._oracle = None
        self._reparatie_log = []

    # ─── Lazy Properties ───

    @property
    def governor(self):
        """Lazy OmegaGovernor."""
        if self._governor is None:
            from ..brain.governor import OmegaGovernor
            self._governor = OmegaGovernor()
        return self._governor

    @property
    def oracle(self):
        """Lazy OracleAgent (voor LLM fallback)."""
        if self._oracle is None:
            from ..core.oracle import OracleAgent
            self._oracle = OracleAgent(persist=False)
        return self._oracle

    # ─── Diagnose ───

    def diagnose(self):
        """Classificeer systeemproblemen via Governor.

        Returns:
            dict met status, problemen, rapport, timestamp.
        """
        rapport = self.governor.get_health_report()
        problemen = []

        # Check state files
        for naam, geldig in rapport.get(
            "state_files", {}
        ).items():
            if not geldig:
                problemen.append({
                    "type": "state_corrupt",
                    "detail": f"{naam} is ongeldig"
                        " of ontbreekt",
                    "ernst": "kritiek",
                    "auto_fix": True,
                    "bestand": naam,
                })

        # Check circuit breaker
        cb = rapport.get("circuit_breaker", {})
        if cb.get("status") != "CLOSED":
            problemen.append({
                "type": "circuit_breaker",
                "detail": (
                    f"Circuit breaker {cb.get('status')}"
                    f" ({cb.get('failures', 0)}"
                    f" failures)"
                ),
                "ernst": (
                    "kritiek"
                    if cb.get("status") == "OPEN"
                    else "waarschuwing"
                ),
                "auto_fix": True,
            })

        # Check learning saturatie
        lr = rapport.get("learning", {})
        cycles = lr.get("cycles_this_hour", 0)
        max_cycles = lr.get("max_per_hour", 20)
        if cycles >= max_cycles:
            problemen.append({
                "type": "learning_saturatie",
                "detail": (
                    f"Learning op limiet:"
                    f" {cycles}/{max_cycles}"
                    " cycles dit uur"
                ),
                "ernst": "waarschuwing",
                "auto_fix": False,
            })

        # Check config dirs
        ontbrekend = []
        for d in [
            Config.DATA_DIR,
            Config.APPS_DATA_DIR,
            Config.RAG_DATA_DIR,
            Config.OUTPUT_DIR,
            Config.BACKUP_DIR,
            Config.LOG_DIR,
        ]:
            if not d.exists():
                ontbrekend.append(str(d.name))
        if ontbrekend:
            problemen.append({
                "type": "config_ontbreekt",
                "detail": (
                    f"Ontbrekende dirs: "
                    f"{', '.join(ontbrekend)}"
                ),
                "ernst": "waarschuwing",
                "auto_fix": True,
                "dirs": ontbrekend,
            })

        # Status bepalen
        kritieken = sum(
            1 for p in problemen
            if p["ernst"] == "kritiek"
        )
        if kritieken > 0:
            status = "KRITIEK"
        elif problemen:
            status = "WAARSCHUWING"
        else:
            status = "GEZOND"

        return {
            "status": status,
            "problemen": problemen,
            "rapport": rapport,
            "timestamp": datetime.now().isoformat(),
        }

    # ─── Repair ───

    def repair(self):
        """Volledige loop: diagnose -> fix -> herdiagnose.

        Returns:
            dict met voor, acties, na, duur,
            volledig_hersteld.
        """
        start = time.time()
        voor = self.diagnose()
        acties = []

        for probleem in voor["problemen"]:
            ptype = probleem["type"]

            if ptype == "state_corrupt":
                actie = self._fix_state_corrupt(probleem)
            elif ptype == "circuit_breaker":
                actie = self._fix_circuit_breaker(probleem)
            elif ptype == "learning_saturatie":
                actie = self._fix_learning_saturatie(
                    probleem
                )
            elif ptype == "config_ontbreekt":
                actie = self._fix_config_ontbreekt(probleem)
            else:
                actie = self._llm_advies(probleem)

            acties.append(actie)
            self._reparatie_log.append(actie)

        na = self.diagnose()
        duur = time.time() - start

        return {
            "voor": voor,
            "acties": acties,
            "na": na,
            "duur": duur,
            "volledig_hersteld": (
                na["status"] == "GEZOND"
            ),
        }

    # ─── Deterministische Handlers ───

    def _fix_state_corrupt(self, probleem):
        """Herstel corrupte state files via Governor.

        Bij 3+ corrupte bestanden: rescue_family().
        Anders: restore_state() per bestand.
        """
        bestand = probleem.get("bestand", "")
        detail = probleem["detail"]

        # Tel totaal corrupte bestanden in huidige run
        rapport = self.governor.get_health_report()
        corrupte = sum(
            1 for geldig
            in rapport.get("state_files", {}).values()
            if not geldig
        )

        if corrupte >= 3:
            # Noodprotocol
            result = self.governor.rescue_family()
            hersteld = result.get("hersteld", 0)
            return {
                "probleem": detail,
                "actie": (
                    f"rescue_family() uitgevoerd"
                    f" ({hersteld} hersteld)"
                ),
                "resultaat": hersteld > 0,
                "detail": (
                    f"Gezond: {result.get('gezond', 0)},"
                    f" hersteld: {hersteld},"
                    f" verloren: "
                    f"{result.get('verloren', 0)}"
                ),
            }

        # Enkel bestand herstellen
        data_dir = self.governor._data_dir
        file_path = data_dir / bestand
        ok = self.governor.restore_state(file_path)

        return {
            "probleem": detail,
            "actie": (
                f"restore_state({bestand})"
                f" -> {'OK' if ok else 'MISLUKT'}"
            ),
            "resultaat": ok,
            "detail": (
                "Hersteld van backup" if ok
                else "Geen geldige backup gevonden"
            ),
        }

    def _fix_circuit_breaker(self, probleem):
        """Wacht op cooldown en check API health.

        Respecteert cooldown, max 65s wacht.
        """
        detail = probleem["detail"]
        countdown = self.governor.get_breaker_countdown()

        if countdown > 65:
            return {
                "probleem": detail,
                "actie": "Wachttijd te lang",
                "resultaat": False,
                "detail": (
                    f"Cooldown nog {countdown}s,"
                    " niet gewacht"
                ),
            }

        if countdown > 0:
            time.sleep(countdown)

        ok = self.governor.check_api_health()
        return {
            "probleem": detail,
            "actie": (
                f"Gewacht {countdown}s +"
                f" check_api_health()"
                f" -> {'OK' if ok else 'GEBLOKT'}"
            ),
            "resultaat": ok,
            "detail": (
                "API weer beschikbaar" if ok
                else "Breaker nog actief"
            ),
        }

    def _fix_learning_saturatie(self, probleem):
        """Learning saturatie: niet auto-fixbaar."""
        return {
            "probleem": probleem["detail"],
            "actie": "Waarschuwing (niet auto-fixbaar)",
            "resultaat": False,
            "detail": (
                "Wacht tot volgend uur voor reset"
                " van learning cycles"
            ),
        }

    def _fix_config_ontbreekt(self, probleem):
        """Maak ontbrekende config dirs aan."""
        try:
            Config.ensure_dirs()
            return {
                "probleem": probleem["detail"],
                "actie": "Config.ensure_dirs() uitgevoerd",
                "resultaat": True,
                "detail": "Ontbrekende directories aangemaakt",
            }
        except Exception as e:
            return {
                "probleem": probleem["detail"],
                "actie": f"ensure_dirs() mislukt: {e}",
                "resultaat": False,
                "detail": str(e),
            }

    # ─── LLM Fallback ───

    def _llm_advies(self, probleem):
        """LLM-fallback voor onbekende probleemtypen.

        Gebruikt OracleAgent._call_api() voor advies.
        """
        detail = probleem.get("detail", "onbekend")

        try:
            berichten = [{
                "role": "user",
                "content": (
                    "Je bent de zelf-reparatie module van"
                    " Project Omega. Analyseer dit"
                    " probleem en geef EEN concrete"
                    " aanbeveling in 1-2 zinnen.\n\n"
                    f"Probleem: {detail}\n"
                    f"Type: {probleem.get('type')}\n"
                    f"Ernst: {probleem.get('ernst')}"
                ),
            }]

            loop = asyncio.new_event_loop()
            try:
                response = loop.run_until_complete(
                    self.oracle._call_api(berichten)
                )
            finally:
                loop.close()

            # Extraheer tekst
            tekst = ""
            for block in response.get("content", []):
                if isinstance(block, dict):
                    tekst += block.get("text", "")
                elif hasattr(block, "text"):
                    tekst += block.text

            return {
                "probleem": detail,
                "actie": f"LLM advies: {tekst[:120]}",
                "resultaat": False,
                "detail": tekst,
            }
        except Exception as e:
            return {
                "probleem": detail,
                "actie": f"LLM fallback mislukt: {e}",
                "resultaat": False,
                "detail": str(e),
            }

    # ─── Display ───

    def toon_diagnose(self, diagnose):
        """Toon diagnose-resultaat met kleuren."""
        status = diagnose["status"]
        problemen = diagnose["problemen"]

        # Status header
        if status == "GEZOND":
            status_kleur = Kleur.FEL_GROEN
        elif status == "WAARSCHUWING":
            status_kleur = Kleur.FEL_GEEL
        else:
            status_kleur = Kleur.FEL_ROOD

        print(kleur(
            f"\n  DIAGNOSE: {status}",
            status_kleur,
        ))
        print(kleur("  " + "=" * 40, Kleur.DIM))

        if not problemen:
            print(kleur(
                "  Alle systemen operationeel.",
                Kleur.GROEN,
            ))
            return

        for p in problemen:
            ernst = p["ernst"]
            if ernst == "kritiek":
                icoon = kleur("[!!]", Kleur.FEL_ROOD)
            else:
                icoon = kleur("[!]", Kleur.FEL_GEEL)

            fix_label = (
                kleur("auto", Kleur.GROEN)
                if p["auto_fix"]
                else kleur("manueel", Kleur.DIM)
            )

            print(
                f"  {icoon} {p['type']}"
                f" [{fix_label}]"
            )
            print(kleur(
                f"      {p['detail']}",
                Kleur.DIM,
            ))

        print(kleur(
            f"\n  Totaal: {len(problemen)}"
            f" probleem/problemen",
            Kleur.DIM,
        ))

    def toon_rapport(self, rapport):
        """Toon reparatierapport met OK/X status."""
        acties = rapport["acties"]
        duur = rapport["duur"]
        hersteld = rapport["volledig_hersteld"]

        status = (
            "VOLLEDIG HERSTELD" if hersteld
            else "GEDEELTELIJK HERSTELD"
        )
        status_kleur = (
            Kleur.FEL_GROEN if hersteld
            else Kleur.FEL_GEEL
        )

        print(kleur(
            f"\n  REPARATIE: {status} ({duur:.1f}s)",
            status_kleur,
        ))
        print(kleur("  " + "=" * 40, Kleur.DIM))

        if not acties:
            print(kleur(
                "  Geen reparaties nodig.",
                Kleur.GROEN,
            ))
            return

        for a in acties:
            ok = a["resultaat"]
            icoon = (
                kleur("[OK]", Kleur.GROEN) if ok
                else kleur("[X]", Kleur.ROOD)
            )
            print(f"  {icoon} {a['actie']}")
            print(kleur(
                f"      {a['detail']}",
                Kleur.DIM,
            ))

        # Voor/na samenvatting
        voor_status = rapport["voor"]["status"]
        na_status = rapport["na"]["status"]
        print(kleur(
            f"\n  Voor: {voor_status}"
            f" -> Na: {na_status}",
            Kleur.DIM,
        ))


__all__ = ["SelfRepairProtocol"]
