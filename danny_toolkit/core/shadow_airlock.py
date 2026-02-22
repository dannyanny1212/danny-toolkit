"""
SHADOW AIRLOCK — Zero-Crash RAG Ingestion Pipeline (Phase 30)
==============================================================
Periodieke scanner die de staging-map (data/shadow_rag/documenten/)
bewaakt en bestanden valideert voordat ze naar productie gaan.

Workflow:
    1. Scan staging-map voor nieuwe/gewijzigde bestanden
    2. Repareer ontbrekende of foutieve YAML-frontmatter (DocumentForge)
    3. Dry-run validatie: simuleer ingest om crashes te detecteren
    4. Exit code 0 → verplaats naar productie (data/rag/documenten/)
    5. Exit code != 0 → quarantaine, log fout, laat bestand staan
    6. Na succesvolle promotie → trigger batch ingest

De ShadowAirlock kan standalone draaien of als taak in de HeartbeatDaemon.

Gebruik:
    from danny_toolkit.core.shadow_airlock import ShadowAirlock

    airlock = ShadowAirlock()
    resultaat = airlock.scan_en_verwerk()    # Één scan-cyclus
    airlock.start_periodiek(interval=60)      # Blokkerende loop
"""

import logging
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

try:
    from danny_toolkit.core.config import Config
    HAS_CONFIG = True
except ImportError:
    HAS_CONFIG = False

try:
    from danny_toolkit.core.document_forge import DocumentForge
    HAS_FORGE = True
except ImportError:
    HAS_FORGE = False

try:
    from danny_toolkit.core.utils import Kleur
except ImportError:
    class Kleur:
        GROEN = ROOD = GEEL = CYAAN = RESET = ""

try:
    from danny_toolkit.brain.cortical_stack import get_cortical_stack
    HAS_STACK = True
except ImportError:
    HAS_STACK = False

try:
    from danny_toolkit.core.alerter import get_alerter, AlertLevel
    HAS_ALERTER = True
except ImportError:
    HAS_ALERTER = False

try:
    from danny_toolkit.core.env_bootstrap import VENV_PYTHON, get_subprocess_env
except ImportError:
    VENV_PYTHON = sys.executable
    def get_subprocess_env(test_mode=False):
        env = os.environ.copy()
        env.update({
            "CUDA_VISIBLE_DEVICES": "-1",
            "ANONYMIZED_TELEMETRY": "False",
            "PYTHONIOENCODING": "utf-8",
        })
        return env


class ShadowAirlock:
    """Nachtwaker die de staging-map bewaakt en bestanden valideert.

    Kenmerken:
    - Periodieke scan (geen watchdog dependency — Windows-veilig)
    - DocumentForge-reparatie voor foute/ontbrekende YAML-headers
    - Dry-run ingest validatie via subprocess
    - Atomaire verplaatsing naar productie bij succes
    - Quarantaine bij falen (bestand blijft in staging)
    - CorticalStack logging voor audit trail
    """

    # Toegestane bestandstypes voor RAG-ingestion
    TOEGESTANE_EXTENSIES = {".md", ".txt"}

    # Maximale bestandsgrootte (10 MB — bescherming tegen dumps)
    MAX_BESTANDSGROOTTE = 10 * 1024 * 1024

    def __init__(self):
        # Mappen instellen
        if HAS_CONFIG:
            self._staging_dir = Config.SHADOW_RAG_DIR
            self._productie_dir = Config.DOCUMENTEN_DIR
            self._ingest_script = str(Config.BASE_DIR / "ingest.py")
        else:
            self._staging_dir = Path("data/shadow_rag/documenten")
            self._productie_dir = Path("data/rag/documenten")
            self._ingest_script = "ingest.py"

        # Statistieken per sessie
        self._stats = {
            "scans": 0,
            "gerepareerd": 0,
            "gepromoveerd": 0,
            "quarantaine": 0,
            "ingest_triggers": 0,
        }

        # Zorg dat mappen bestaan
        self._staging_dir.mkdir(parents=True, exist_ok=True)
        self._productie_dir.mkdir(parents=True, exist_ok=True)

    def scan_staging(self) -> List[Path]:
        """Scan de staging-map voor verwerkte bestanden.

        Returns:
            Lijst van bestanden die klaar zijn voor validatie.
        """
        bestanden = []
        if not self._staging_dir.exists():
            return bestanden

        for pad in self._staging_dir.iterdir():
            # Alleen bestanden, geen mappen
            if not pad.is_file():
                continue

            # Extensie check
            if pad.suffix.lower() not in self.TOEGESTANE_EXTENSIES:
                logger.debug("Airlock: overgeslagen (extensie): %s", pad.name)
                continue

            # Grootte check
            if pad.stat().st_size > self.MAX_BESTANDSGROOTTE:
                logger.warning("Airlock: te groot (>10MB): %s", pad.name)
                continue

            # Leeg bestand check
            if pad.stat().st_size == 0:
                logger.debug("Airlock: overgeslagen (leeg): %s", pad.name)
                continue

            bestanden.append(pad)

        return bestanden

    def _repareer_en_valideer(self, pad: Path) -> tuple:
        """Repareer YAML-frontmatter en valideer het bestand.

        Args:
            pad: Pad naar het staging-bestand.

        Returns:
            (is_geldig: bool, fouten: list[str])
        """
        if not HAS_FORGE:
            # Zonder DocumentForge kunnen we alleen basale checks doen
            try:
                with open(pad, "r", encoding="utf-8") as f:
                    inhoud = f.read()
                if inhoud.startswith("---"):
                    return True, []
                return False, ["geen frontmatter, DocumentForge niet beschikbaar"]
            except Exception as e:
                return False, [str(e)]

        # Stap 1: Repareer indien nodig
        try:
            gerepareerd = DocumentForge.repareer_bestand(pad)
            if gerepareerd:
                self._stats["gerepareerd"] += 1
                logger.info("Airlock: gerepareerd: %s", pad.name)
        except Exception as e:
            return False, [f"reparatiefout: {e}"]

        # Stap 2: Valideer
        is_geldig, fouten = DocumentForge.valideer_bestand(pad)
        return is_geldig, fouten

    def _dry_run_ingest(self, pad: Path) -> tuple:
        """Simuleer RAG-ingestion voor één bestand.

        Voert een dry-run uit om te controleren of het bestand
        zonder crashes door de ingest-pipeline komt.

        Args:
            pad: Pad naar het te testen bestand.

        Returns:
            (geslaagd: bool, foutmelding: str)
        """
        # Validatie-commando: probeer het bestand te lezen en te parsen
        # We gebruiken een lichtgewicht check i.p.v. volledige ingest
        validatie_code = (
            "import sys; "
            "f = open(sys.argv[1], 'r', encoding='utf-8'); "
            "inhoud = f.read(); f.close(); "
            "assert inhoud.startswith('---'), 'Geen YAML header'; "
            "assert '\\n---' in inhoud[3:], 'Gebroken header'; "
            "body = inhoud.split('---', 2)[-1].strip(); "
            "assert len(body) > 10, 'Body te kort'; "
            "print('OK:', len(inhoud), 'bytes')"
        )

        try:
            env = get_subprocess_env(test_mode=False)
            env["PYTHONIOENCODING"] = "utf-8"
            result = subprocess.run(
                [VENV_PYTHON, "-c", validatie_code, str(pad)],
                capture_output=True,
                timeout=15,
                env=env,
                encoding="utf-8",
                errors="replace",
            )

            if result.returncode == 0:
                return True, result.stdout.strip()
            else:
                fout = result.stderr.strip() or result.stdout.strip()
                return False, fout[:500]

        except subprocess.TimeoutExpired:
            return False, "timeout (>15s)"
        except Exception as e:
            return False, str(e)

    def _promoveer_naar_productie(self, pad: Path) -> Optional[Path]:
        """Verplaats een gevalideerd bestand van staging naar productie.

        Gebruikt shutil.move() voor atomaire verplaatsing.
        Bij naamconflict: voeg timestamp toe.

        Args:
            pad: Pad in staging-map.

        Returns:
            Nieuw pad in productie, of None bij falen.
        """
        doel = self._productie_dir / pad.name

        # Naamconflict afhandelen
        if doel.exists():
            stam = pad.stem
            ext = pad.suffix
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            doel = self._productie_dir / f"{stam}_{ts}{ext}"

        try:
            shutil.move(str(pad), str(doel))
            logger.info("Airlock: gepromoveerd: %s → %s", pad.name, doel.name)
            return doel
        except Exception as e:
            logger.error("Airlock: verplaatsen mislukt: %s → %s", pad.name, e)
            return None

    def _trigger_ingest(self, bestanden: List[Path]):
        """Trigger batch ingest voor gepromoveerde bestanden.

        Roept ingest.py aan met de productie-map als pad.
        """
        if not bestanden:
            return

        ingest_pad = str(self._productie_dir)

        logger.info(
            "Airlock: batch ingest triggeren voor %d bestand(en)...",
            len(bestanden),
        )

        try:
            env = get_subprocess_env(test_mode=False)
            env["PYTHONIOENCODING"] = "utf-8"
            result = subprocess.run(
                [
                    VENV_PYTHON, self._ingest_script,
                    "--batch", "--method", "paragraph",
                    "--path", ingest_pad,
                ],
                capture_output=True,
                timeout=120,
                env=env,
                encoding="utf-8",
                errors="replace",
            )

            if result.returncode == 0:
                self._stats["ingest_triggers"] += 1
                logger.info("Airlock: ingest succesvol afgerond.")
                print(f"{Kleur.GROEN}  Airlock: ingest afgerond.{Kleur.RESET}")
            else:
                fout = result.stderr[:500] if result.stderr else "onbekende fout"
                logger.warning("Airlock: ingest fout: %s", fout)
                print(f"{Kleur.ROOD}  Airlock: ingest fout: {fout[:200]}{Kleur.RESET}")

        except subprocess.TimeoutExpired:
            logger.warning("Airlock: ingest timeout (>120s)")
        except Exception as e:
            logger.error("Airlock: ingest trigger mislukt: %s", e)

    def _log_naar_cortical(self, actie: str, details: dict):
        """Log airlock-activiteit naar CorticalStack."""
        if not HAS_STACK:
            return
        try:
            stack = get_cortical_stack()
            stack.log_event(
                actor="shadow_airlock",
                action=actie,
                details=details,
            )
        except Exception as e:
            logger.debug("CorticalStack log mislukt: %s", e)

    def scan_en_verwerk(self) -> Dict:
        """Één volledige scan-cyclus: scan → repareer → valideer → promoveer → ingest.

        Returns:
            Dict met resultaten: {bestanden, gerepareerd, gepromoveerd, quarantaine, fouten}
        """
        self._stats["scans"] += 1
        resultaat = {
            "bestanden": 0,
            "gerepareerd": 0,
            "gepromoveerd": 0,
            "quarantaine": 0,
            "fouten": [],
        }

        # Stap 1: Scan staging
        bestanden = self.scan_staging()
        resultaat["bestanden"] = len(bestanden)

        if not bestanden:
            return resultaat

        print(f"{Kleur.CYAAN}🔒 ShadowAirlock: {len(bestanden)} bestand(en) in staging{Kleur.RESET}")

        gepromoveerd = []

        for pad in bestanden:
            naam = pad.name
            print(f"{Kleur.GEEL}  📋 Verwerken: {naam}{Kleur.RESET}")

            # Stap 2: Repareer en valideer YAML
            is_geldig, fouten = self._repareer_en_valideer(pad)
            if not is_geldig:
                print(f"{Kleur.ROOD}  ❌ Validatiefout: {'; '.join(fouten)}{Kleur.RESET}")
                resultaat["quarantaine"] += 1
                resultaat["fouten"].append(f"{naam}: {'; '.join(fouten)}")
                self._log_naar_cortical("quarantaine", {
                    "bestand": naam,
                    "fouten": fouten,
                })
                continue

            # Stap 3: Dry-run ingest validatie
            geslaagd, melding = self._dry_run_ingest(pad)
            if not geslaagd:
                print(f"{Kleur.ROOD}  ❌ Dry-run mislukt: {melding[:200]}{Kleur.RESET}")
                resultaat["quarantaine"] += 1
                resultaat["fouten"].append(f"{naam}: dry-run: {melding[:200]}")
                self._stats["quarantaine"] += 1
                self._log_naar_cortical("dry_run_mislukt", {
                    "bestand": naam,
                    "fout": melding[:500],
                })
                continue

            # Stap 4: Promoveer naar productie
            nieuw_pad = self._promoveer_naar_productie(pad)
            if nieuw_pad:
                print(f"{Kleur.GROEN}  ✅ Gepromoveerd: {nieuw_pad.name}{Kleur.RESET}")
                resultaat["gepromoveerd"] += 1
                self._stats["gepromoveerd"] += 1
                gepromoveerd.append(nieuw_pad)
                self._log_naar_cortical("gepromoveerd", {
                    "bestand": naam,
                    "doel": str(nieuw_pad.name),
                })
            else:
                resultaat["quarantaine"] += 1
                self._stats["quarantaine"] += 1

        resultaat["gerepareerd"] = self._stats["gerepareerd"]

        # Stap 5: Trigger ingest voor gepromoveerde bestanden
        if gepromoveerd:
            self._trigger_ingest(gepromoveerd)

        # Alert bij quarantaine
        if resultaat["quarantaine"] > 0 and HAS_ALERTER:
            try:
                get_alerter().alert(
                    AlertLevel.WAARSCHUWING,
                    f"ShadowAirlock: {resultaat['quarantaine']} bestand(en) in quarantaine",
                    bron="shadow_airlock",
                )
            except Exception as e:
                logger.debug("Alerter fout: %s", e)

        return resultaat

    def start_periodiek(self, interval: int = 60):
        """Start een blokkerende periodieke scan-loop.

        Args:
            interval: Seconden tussen scans (standaard: 60).
        """
        print(f"{Kleur.CYAAN}🔒 ShadowAirlock daemon gestart (interval: {interval}s){Kleur.RESET}")
        print(f"   Staging: {self._staging_dir}")
        print(f"   Productie: {self._productie_dir}")
        print(f"   Ctrl+C om te stoppen\n")

        try:
            while True:
                resultaat = self.scan_en_verwerk()
                if resultaat["bestanden"] > 0:
                    print(
                        f"{Kleur.CYAAN}  📊 Resultaat: "
                        f"{resultaat['gepromoveerd']} gepromoveerd, "
                        f"{resultaat['quarantaine']} quarantaine"
                        f"{Kleur.RESET}"
                    )
                time.sleep(interval)
        except KeyboardInterrupt:
            print(f"\n{Kleur.ROOD}ShadowAirlock gestopt.{Kleur.RESET}")

    def get_stats(self) -> Dict:
        """Retourneer sessie-statistieken."""
        return dict(self._stats)
