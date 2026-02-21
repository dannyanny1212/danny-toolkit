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
import json
import logging
import subprocess
import time
from datetime import datetime

from ..core.utils import kleur, Kleur
from ..core.config import Config

logger = logging.getLogger(__name__)


class SelfRepairProtocol:
    """Zelf-diagnose en -reparatie via Governor + LLM."""

    _collection = None  # Lazy ChromaDB connectie

    _GOVERNOR_ACTIES = {
        "rescue_family": "rescue_family",
        "restore_state": "restore_state",
        "startup_check": "startup_check",
        "enforce_directories": "enforce_directories",
    }

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

    @property
    def eye(self):
        """Lazy PixelEye — via Oracle's eye."""
        return self.oracle.eye

    @property
    def body(self):
        """Lazy KineticUnit — via Oracle's body."""
        return self.oracle.body

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

    # ─── ChromaDB ───

    def _get_collection(self):
        """Lazy ChromaDB connectie (zelfde DB als ingest)."""
        if self._collection is not None:
            return self._collection
        try:
            import chromadb
            from .embeddings import get_chroma_embed_fn
            import io as _io
            import sys as _sys

            chroma_dir = str(
                Config.RAG_DATA_DIR / "chromadb"
            )
            client = chromadb.PersistentClient(
                path=chroma_dir
            )
            # Suppress model load spam
            _old_out = _sys.stdout
            _old_err = _sys.stderr
            _sys.stdout = _io.StringIO()
            _sys.stderr = _io.StringIO()
            try:
                embed_fn = get_chroma_embed_fn()
            finally:
                _sys.stdout = _old_out
                _sys.stderr = _old_err
            self._collection = (
                client.get_collection(
                    name="danny_knowledge",
                    embedding_function=embed_fn,
                )
            )
            return self._collection
        except Exception as e:
            logger.debug("ChromaDB collectie laden mislukt: %s", e)
            return None

    # ─── Orchestratie Methodes ───

    def _diagnose_visueel(self):
        """Visuele diagnose via PixelEye.

        Maakt een screenshot en analyseert op
        foutmeldingen.

        Returns:
            dict met fout_tekst, scherm_analyse,
            pad, tijd.
        """
        try:
            result = self.eye.analyze_screen(
                "Zoek naar foutmeldingen, error "
                "dialogen, rode waarschuwingen of "
                "crashes op het scherm. Beschrijf "
                "exact welke fout je ziet."
            )
            return {
                "fout_tekst": result.get(
                    "analyse", ""
                ),
                "scherm_analyse": result.get(
                    "analyse", ""
                ),
                "pad": result.get("pad", ""),
                "tijd": result.get("tijd", 0),
            }
        except Exception as e:
            return {
                "fout_tekst": str(e),
                "scherm_analyse": f"Visuele diagnose"
                    f" mislukt: {e}",
                "pad": "",
                "tijd": 0,
            }

    def _zoek_kennis(self, zoekterm, n_results=5):
        """Zoek relevante kennis in ChromaDB.

        Args:
            zoekterm: Zoekterm voor ChromaDB.
            n_results: Max aantal resultaten.

        Returns:
            list van dicts met tekst, bron, afstand.
        """
        collection = self._get_collection()
        if not collection:
            return []
        try:
            results = collection.query(
                query_texts=[zoekterm],
                n_results=n_results,
            )
            kennis = []
            docs = results.get("documents", [[]])[0]
            metas = results.get("metadatas", [[]])[0]
            dists = results.get("distances", [[]])[0]
            for doc, meta, dist in zip(
                docs, metas, dists
            ):
                kennis.append({
                    "tekst": doc,
                    "bron": meta.get("bron", "onbekend"),
                    "afstand": dist,
                })
            return kennis
        except Exception as e:
            logger.debug("Kennis zoeken mislukt: %s", e)
            return []

    def _genereer_herstelplan(
        self, diagnose, kennis, fout
    ):
        """Genereer multi-step herstelplan via LLM.

        Args:
            diagnose: dict van _diagnose_visueel().
            kennis: list van _zoek_kennis().
            fout: Originele foutbeschrijving.

        Returns:
            list van stap-dicts of lege lijst.
        """
        kennis_tekst = ""
        for k in kennis[:3]:
            kennis_tekst += (
                f"\n- [{k['bron']}]: "
                f"{k['tekst'][:200]}"
            )

        visueel = diagnose.get(
            "scherm_analyse", ""
        )

        berichten = [{
            "role": "user",
            "content": (
                "Je bent de repair-orchestrator van"
                " Project Omega. Genereer een"
                " herstelplan.\n\n"
                f"FOUT: {fout}\n"
                f"VISUEEL: {visueel[:300]}\n"
                f"KENNIS: {kennis_tekst[:500]}\n\n"
                "Geef een JSON array van stappen."
                " Elke stap heeft:\n"
                '- "type": "shell" | "gui" |'
                ' "governor"\n'
                '- "actie": het commando of de'
                " methode\n"
                '- "args": {} parameters\n'
                '- "verwachting": wat het resultaat'
                " moet zijn\n\n"
                "Voorbeelden:\n"
                '[{"type": "shell", "actie":'
                ' "pip install X", "args": {},'
                ' "verwachting": "Package'
                ' geinstalleerd"}]\n'
                '[{"type": "governor", "actie":'
                ' "rescue_family", "args": {},'
                ' "verwachting": "State hersteld"}]\n'
                '[{"type": "gui", "actie": "click",'
                ' "args": {"x": 100, "y": 200},'
                ' "verwachting": "Dialoog gesloten"}]'
                "\n\nAntwoord ALLEEN met JSON array."
            ),
        }]

        try:
            loop = asyncio.new_event_loop()
            try:
                response = loop.run_until_complete(
                    self.oracle._call_api(berichten)
                )
            finally:
                loop.close()

            tekst = ""
            for block in response.get("content", []):
                if isinstance(block, dict):
                    tekst += block.get("text", "")
                elif hasattr(block, "text"):
                    tekst += block.text

            stappen = (
                self.oracle._parse_plan_json(tekst)
            )
            return stappen
        except Exception as e:
            logger.debug("Herstelplan genereren mislukt: %s", e)
            return []

    def _voer_stap_uit(self, stap):
        """Voer een herstelstap uit.

        Dispatcht naar shell, gui of governor handler.

        Args:
            stap: dict met type, actie, args,
                  verwachting.

        Returns:
            dict met stap, resultaat, geslaagd, detail.
        """
        stap_type = stap.get("type", "")
        actie = stap.get("actie", "")
        args = stap.get("args", {})

        if stap_type == "shell":
            return self._voer_shell_uit(actie, args)
        elif stap_type == "gui":
            return self._voer_gui_uit(actie, args)
        elif stap_type == "governor":
            return self._voer_governor_uit(
                actie, args
            )
        else:
            return {
                "stap": stap,
                "resultaat": "onbekend type",
                "geslaagd": False,
                "detail": (
                    f"Onbekend stap-type: {stap_type}"
                ),
            }

    def _voer_shell_uit(self, commando, args):
        """Voer een shell-commando uit.

        Args:
            commando: Het uit te voeren commando.
            args: Extra args (ongebruikt).

        Returns:
            dict met stap, resultaat, geslaagd, detail.
        """
        try:
            result = subprocess.run(
                commando,
                shell=True,
                capture_output=True,
                text=True,
                timeout=60,
            )
            geslaagd = result.returncode == 0
            detail = (
                result.stdout.strip()
                if geslaagd
                else result.stderr.strip()
            )

            actie_log = {
                "type": "shell",
                "commando": commando,
                "geslaagd": geslaagd,
                "timestamp":
                    datetime.now().isoformat(),
            }
            self._reparatie_log.append(actie_log)

            return {
                "stap": f"shell: {commando}",
                "resultaat": (
                    "OK" if geslaagd else "FOUT"
                ),
                "geslaagd": geslaagd,
                "detail": detail[:200],
            }
        except subprocess.TimeoutExpired:
            return {
                "stap": f"shell: {commando}",
                "resultaat": "TIMEOUT",
                "geslaagd": False,
                "detail": "Commando duurde langer"
                    " dan 60 seconden",
            }
        except Exception as e:
            return {
                "stap": f"shell: {commando}",
                "resultaat": "FOUT",
                "geslaagd": False,
                "detail": str(e),
            }

    def _voer_gui_uit(self, actie, args):
        """Voer een GUI-actie uit via KineticUnit.

        Args:
            actie: Actie-type (click, type_text, etc).
            args: Args voor de actie.

        Returns:
            dict met stap, resultaat, geslaagd, detail.
        """
        from ..core.oracle import ACTIE_DISPATCH

        handler = ACTIE_DISPATCH.get(actie)
        if not handler:
            return {
                "stap": f"gui: {actie}",
                "resultaat": "ONBEKEND",
                "geslaagd": False,
                "detail": f"Onbekende actie: {actie}",
            }

        try:
            result = handler(self.body, args)
            return {
                "stap": f"gui: {actie}",
                "resultaat": "OK",
                "geslaagd": True,
                "detail": str(result)[:200],
            }
        except Exception as e:
            return {
                "stap": f"gui: {actie}",
                "resultaat": "FOUT",
                "geslaagd": False,
                "detail": str(e),
            }

    def _voer_governor_uit(self, actie, args):
        """Voer een Governor-actie uit (whitelist).

        Args:
            actie: Naam van de Governor methode.
            args: Args voor de methode.

        Returns:
            dict met stap, resultaat, geslaagd, detail.
        """
        if actie not in self._GOVERNOR_ACTIES:
            return {
                "stap": f"governor: {actie}",
                "resultaat": "GEBLOKKEERD",
                "geslaagd": False,
                "detail": (
                    f"'{actie}' staat niet op de"
                    " whitelist"
                ),
            }

        methode_naam = self._GOVERNOR_ACTIES[actie]
        methode = getattr(
            self.governor, methode_naam, None
        )
        if not methode:
            return {
                "stap": f"governor: {actie}",
                "resultaat": "NIET GEVONDEN",
                "geslaagd": False,
                "detail": (
                    f"Methode '{methode_naam}'"
                    " niet gevonden"
                ),
            }

        try:
            result = methode(**args)
            return {
                "stap": f"governor: {actie}",
                "resultaat": "OK",
                "geslaagd": True,
                "detail": str(result)[:200],
            }
        except Exception as e:
            return {
                "stap": f"governor: {actie}",
                "resultaat": "FOUT",
                "geslaagd": False,
                "detail": str(e),
            }

    def _verifieer_visueel(self, verwachting):
        """Visuele verificatie via PixelEye.

        Args:
            verwachting: Wat er zichtbaar moet zijn.

        Returns:
            dict met match, analyse, pad, etc.
        """
        try:
            return self.eye.check_state(verwachting)
        except Exception as e:
            return {
                "match": False,
                "analyse": f"Verificatie mislukt: {e}",
            }

    def orchestrate_repair(
        self, fout_beschrijving, verwachting=None
    ):
        """Multi-agent repair pipeline.

        Combineert visuele diagnose, kennis-lookup,
        LLM-planning, executie en verificatie.

        Args:
            fout_beschrijving: Wat er mis is.
            verwachting: Optionele visuele verwachting
                na reparatie.

        Returns:
            dict met status, diagnose, kennis, plan,
            resultaten, verificatie, duur.
        """
        start = time.time()

        # [1/5] Visuele diagnose
        diagnose = self._diagnose_visueel()

        # [2/5] Kennis opzoeken
        zoekterm = fout_beschrijving
        if diagnose.get("fout_tekst"):
            zoekterm += " " + diagnose[
                "fout_tekst"
            ][:100]
        kennis = self._zoek_kennis(zoekterm)

        # [3/5] Herstelplan genereren
        plan = self._genereer_herstelplan(
            diagnose, kennis, fout_beschrijving
        )

        # [4/5] Plan uitvoeren
        resultaten = []
        for stap in plan:
            result = self._voer_stap_uit(stap)
            resultaten.append(result)

        # [5/5] Visuele verificatie (optioneel)
        verificatie = None
        if verwachting:
            verificatie = self._verifieer_visueel(
                verwachting
            )

        duur = time.time() - start

        # Status bepalen
        if not plan:
            status = "MISLUKT"
        elif all(
            r["geslaagd"] for r in resultaten
        ):
            status = "HERSTELD"
        elif any(
            r["geslaagd"] for r in resultaten
        ):
            status = "GEDEELTELIJK"
        else:
            status = "MISLUKT"

        return {
            "status": status,
            "diagnose": diagnose,
            "kennis": kennis,
            "plan": plan,
            "resultaten": resultaten,
            "verificatie": verificatie,
            "duur": duur,
        }

    # ─── Display ───

    def toon_orchestratie(self, result):
        """Toon orchestratie-resultaat met kleuren."""
        status = result["status"]
        duur = result["duur"]

        if status == "HERSTELD":
            status_kleur = Kleur.FEL_GROEN
        elif status == "GEDEELTELIJK":
            status_kleur = Kleur.FEL_GEEL
        else:
            status_kleur = Kleur.FEL_ROOD

        print(kleur(
            f"\n  ORCHESTRATIE: {status}"
            f" ({duur:.1f}s)",
            status_kleur,
        ))
        print(kleur("  " + "=" * 40, Kleur.DIM))

        # Bronnen
        kennis = result.get("kennis", [])
        if kennis:
            print(kleur(
                f"  Bronnen: {len(kennis)}"
                " documenten gevonden",
                Kleur.CYAAN,
            ))
            for k in kennis[:3]:
                print(kleur(
                    f"    - {k['bron']}"
                    f" (afstand: {k['afstand']:.2f})",
                    Kleur.DIM,
                ))

        # Stappen
        resultaten = result.get("resultaten", [])
        if resultaten:
            print(kleur(
                f"\n  Stappen: {len(resultaten)}",
                Kleur.GEEL,
            ))
            for r in resultaten:
                ok = r["geslaagd"]
                icoon = (
                    kleur("[OK]", Kleur.GROEN) if ok
                    else kleur("[X]", Kleur.ROOD)
                )
                print(f"  {icoon} {r['stap']}")
                print(kleur(
                    f"      {r['detail'][:60]}",
                    Kleur.DIM,
                ))
        elif not result.get("plan"):
            print(kleur(
                "  Geen herstelplan gegenereerd.",
                Kleur.ROOD,
            ))

        # Verificatie
        verificatie = result.get("verificatie")
        if verificatie:
            match = verificatie.get("match", False)
            v_kleur = (
                Kleur.GROEN if match
                else Kleur.ROOD
            )
            v_label = "MATCH" if match else "GEEN MATCH"
            print(kleur(
                f"\n  Verificatie: {v_label}",
                v_kleur,
            ))
            analyse = verificatie.get("analyse", "")
            if analyse:
                print(kleur(
                    f"    {analyse[:80]}",
                    Kleur.DIM,
                ))

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
