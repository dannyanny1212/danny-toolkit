"""
Quest XIII: THE WILL - Pixel Handelt Autonoom.

De beslissingsmotor: analyseert systeemstaat, beslist wat er
moet gebeuren, en voert het zelf uit.

Architectuur:
  [Sensorium events] + [Systeem status] + [Daemon mood]
       |
       v
  WillProtocol._scan()     -> kandidaat-operaties
  WillProtocol._beslis()   -> filter + prioriteer
  WillProtocol._voer_uit() -> Governor goedkeuring -> executie
       |
       v
  [Log] + [Sensorium TASK_COMPLETE event]

Geen nieuwe dependencies. Gebruikt stdlib + bestaande API's.
"""

import json
import shutil
import sqlite3
import subprocess
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..core.config import Config
from ..core.utils import kleur, Kleur, info, succes, fout


class OperationType(Enum):
    """Typen autonome operaties."""
    BACKUP = "backup"
    CLEANUP = "cleanup"
    HEALTH_CHECK = "health_check"
    OPTIMIZE = "optimize"
    SCRIPT = "script"
    NURTURE = "nurture"
    RAG_CLEANUP = "rag_cleanup"


class Beslissing(Enum):
    """Resultaat van een beslissing."""
    UITGEVOERD = "uitgevoerd"
    GEWEIGERD = "geweigerd"
    OVERGESLAGEN = "overgeslagen"
    FOUT = "fout"


@dataclass
class WilOperatie:
    """Een kandidaat-operatie."""
    type: OperationType
    reden: str
    prioriteit: int = 1       # 1=laag, 2=medium, 3=hoog
    data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UitvoerLog:
    """Log van een uitgevoerde operatie."""
    operatie: str
    reden: str
    resultaat: str
    details: str = ""
    duur_ms: int = 0
    visueel: str = ""  # "", "OK", "AFWIJKING"
    timestamp: str = field(
        default_factory=lambda: datetime.now().isoformat()
    )


class WillProtocol:
    """Quest XIII: The Will - Pixel Handelt Autonoom."""

    SCRIPT_WHITELIST = {
        "integrity_check": "omega_integrity_check.py",
        "morning_protocol": "morning_protocol.py",
    }

    COOLDOWNS = {
        OperationType.BACKUP: 3600,
        OperationType.CLEANUP: 7200,
        OperationType.HEALTH_CHECK: 1800,
        OperationType.OPTIMIZE: 7200,
        OperationType.SCRIPT: 3600,
        OperationType.NURTURE: 900,
        OperationType.RAG_CLEANUP: 86400,
    }

    RAG_DB_PAD = (
        Config.BASE_DIR / "data" / "rag" / "chromadb"
    )

    MAX_OPERATIES_PER_SESSIE = 50

    VISUELE_VERWACHTINGEN = {
        OperationType.HEALTH_CHECK:
            "Er is een systeem health rapport zichtbaar",
        OperationType.SCRIPT:
            "Het script heeft visuele output geproduceerd",
    }

    def __init__(self):
        self._sensorium = None
        self._governor = None
        self._daemon = None
        self._eye = None
        self.actief = False

        # Tracking
        self._sessie_operaties = 0
        self._totaal_uitgevoerd = 0
        self._totaal_geweigerd = 0
        self._laatste_uitvoer = {}  # type -> timestamp
        self._log = []              # Lijst van UitvoerLog
        self._thread = None
        self._stop_event = threading.Event()

        # Log bestand
        Config.ensure_dirs()
        self._log_pad = Config.LOG_DIR / "will_protocol.json"
        self._laad_log()

    def _laad_log(self):
        """Laad bestaande log."""
        if self._log_pad.exists():
            try:
                with open(
                    self._log_pad, "r", encoding="utf-8"
                ) as f:
                    data = json.load(f)
                self._totaal_uitgevoerd = data.get(
                    "totaal_uitgevoerd", 0
                )
                self._totaal_geweigerd = data.get(
                    "totaal_geweigerd", 0
                )
            except (json.JSONDecodeError, IOError):
                pass

    def _bewaar_log(self):
        """Bewaar log naar bestand (max 200 entries)."""
        entries = []
        for entry in self._log[-200:]:
            entries.append({
                "operatie": entry.operatie,
                "reden": entry.reden,
                "resultaat": entry.resultaat,
                "details": entry.details,
                "duur_ms": entry.duur_ms,
                "visueel": entry.visueel,
                "timestamp": entry.timestamp,
            })

        data = {
            "totaal_uitgevoerd": self._totaal_uitgevoerd,
            "totaal_geweigerd": self._totaal_geweigerd,
            "entries": entries,
        }

        try:
            with open(
                self._log_pad, "w", encoding="utf-8"
            ) as f:
                json.dump(
                    data, f, indent=2, ensure_ascii=False
                )
        except IOError:
            pass

    # ─── Lazy Init + Koppeling ───

    def _get_sensorium(self):
        """Lazy Sensorium."""
        if self._sensorium is None:
            from ..daemon.sensorium import Sensorium
            self._sensorium = Sensorium()
        return self._sensorium

    def _get_governor(self):
        """Lazy OmegaGovernor."""
        if self._governor is None:
            from ..brain.governor import OmegaGovernor
            self._governor = OmegaGovernor()
        return self._governor

    def _get_eye(self):
        """Lazy PixelEye."""
        if self._eye is None:
            from ..skills.pixel_eye import PixelEye
            self._eye = PixelEye()
        return self._eye

    def koppel_systemen(
        self, sensorium=None, governor=None,
        daemon=None, eye=None
    ):
        """Koppel bestaande instanties (vanuit OmegaAI)."""
        if sensorium is not None:
            self._sensorium = sensorium
        if governor is not None:
            self._governor = governor
        if daemon is not None:
            self._daemon = daemon
        if eye is not None:
            self._eye = eye

    # ─── Beslissingsmotor ───

    def _scan(self) -> List[WilOperatie]:
        """Scan systeem en genereer kandidaat-operaties."""
        kandidaten = []
        governor = self._get_governor()

        # 1. State files corrupt? -> BACKUP (prio 3)
        for sf in governor.KRITIEKE_STATE_FILES:
            pad = governor._data_dir / sf
            if pad.exists():
                try:
                    with open(pad, "r", encoding="utf-8") as f:
                        json.load(f)
                except (json.JSONDecodeError, IOError):
                    kandidaten.append(WilOperatie(
                        type=OperationType.BACKUP,
                        reden=f"Corrupt state file: {sf}",
                        prioriteit=3,
                        data={"file": sf},
                    ))

        # 2. Periodieke backup verlopen?
        laatste = self._laatste_uitvoer.get(
            OperationType.BACKUP, 0
        )
        if time.time() - laatste > 3600:
            kandidaten.append(WilOperatie(
                type=OperationType.BACKUP,
                reden="Periodieke backup (>1 uur)",
                prioriteit=1,
            ))

        # 3. Meer dan 10 log bestanden?
        try:
            logs = list(Config.LOG_DIR.glob("*.log"))
            if len(logs) > 10:
                kandidaten.append(WilOperatie(
                    type=OperationType.CLEANUP,
                    reden=f"{len(logs)} log bestanden",
                    prioriteit=1,
                    data={"aantal": len(logs)},
                ))
        except Exception:
            pass

        # 4. Systeem idle >30 min? -> HEALTH_CHECK
        sensorium = self._get_sensorium()
        try:
            events = sensorium.get_recent_events(1)
            if events:
                laatste_event = events[0]
                leeftijd = (
                    time.time()
                    - laatste_event.get("timestamp", time.time())
                )
                if leeftijd > 1800:
                    kandidaten.append(WilOperatie(
                        type=OperationType.HEALTH_CHECK,
                        reden="Systeem idle >30 min",
                        prioriteit=2,
                    ))
        except (AttributeError, TypeError):
            pass

        # 5. Grote state files (>100KB)?
        for sf in governor.KRITIEKE_STATE_FILES:
            pad = governor._data_dir / sf
            if pad.exists():
                try:
                    grootte = pad.stat().st_size
                    if grootte > 102400:
                        kandidaten.append(WilOperatie(
                            type=OperationType.OPTIMIZE,
                            reden=(
                                f"{sf} is "
                                f"{grootte // 1024}KB"
                            ),
                            prioriteit=1,
                            data={"file": sf},
                        ))
                except OSError:
                    pass

        # 6. Daemon nutrient tekorten?
        if self._daemon is not None:
            try:
                meta = self._daemon.metabolisme
                nutrients = meta.nutrients
                for naam in [
                    "protein", "carbs", "vitamins",
                    "water", "fiber",
                ]:
                    niveau = getattr(nutrients, naam, 50.0)
                    if niveau < 20.0:
                        kandidaten.append(WilOperatie(
                            type=OperationType.NURTURE,
                            reden=(
                                f"{naam} laag "
                                f"({niveau:.0f})"
                            ),
                            prioriteit=2,
                            data={"nutrient": naam},
                        ))
            except (AttributeError, TypeError):
                pass

        # 7. ChromaDB wees-mappen?
        try:
            wezen = self._scan_rag_wezen()
            if wezen:
                kandidaten.append(WilOperatie(
                    type=OperationType.RAG_CLEANUP,
                    reden=(
                        f"{len(wezen)} wees-mappen"
                        " in ChromaDB"
                    ),
                    prioriteit=2,
                    data={"wezen": wezen},
                ))
        except Exception:
            pass

        # 8. Nacht? -> Extra backup
        uur = datetime.now().hour
        if uur >= 23 or uur <= 5:
            laatste_nacht = self._laatste_uitvoer.get(
                "nacht_backup", 0
            )
            if time.time() - laatste_nacht > 7200:
                kandidaten.append(WilOperatie(
                    type=OperationType.BACKUP,
                    reden="Nachtelijke backup",
                    prioriteit=2,
                ))

        return kandidaten

    def _beslis(
        self, kandidaten: List[WilOperatie]
    ) -> List[WilOperatie]:
        """Filter en prioriteer kandidaten."""
        goedgekeurd = []

        # Sessie limiet
        if (
            self._sessie_operaties
            >= self.MAX_OPERATIES_PER_SESSIE
        ):
            return []

        for op in kandidaten:
            # Check cooldown
            cooldown = self.COOLDOWNS.get(op.type, 3600)
            laatste = self._laatste_uitvoer.get(op.type, 0)
            if time.time() - laatste < cooldown:
                continue

            goedgekeurd.append(op)

        # Sorteer op prioriteit (hoog eerst)
        goedgekeurd.sort(
            key=lambda o: o.prioriteit, reverse=True
        )

        return goedgekeurd

    def _voer_uit(self, operatie: WilOperatie) -> UitvoerLog:
        """Voer een operatie uit na Governor goedkeuring."""
        start = time.time()
        governor = self._get_governor()

        # Governor gate: check API health
        if not governor.check_api_health():
            self._totaal_geweigerd += 1
            return UitvoerLog(
                operatie=operatie.type.value,
                reden=operatie.reden,
                resultaat=Beslissing.GEWEIGERD.value,
                details="Governor circuit breaker actief",
            )

        # Dispatch naar executor
        try:
            executors = {
                OperationType.BACKUP: self._exec_backup,
                OperationType.CLEANUP: self._exec_cleanup,
                OperationType.HEALTH_CHECK:
                    self._exec_health_check,
                OperationType.OPTIMIZE: self._exec_optimize,
                OperationType.SCRIPT: self._exec_script,
                OperationType.NURTURE: self._exec_nurture,
                OperationType.RAG_CLEANUP:
                    self._exec_rag_cleanup,
            }

            executor = executors.get(operatie.type)
            if executor is None:
                return UitvoerLog(
                    operatie=operatie.type.value,
                    reden=operatie.reden,
                    resultaat=Beslissing.FOUT.value,
                    details="Onbekend operatie type",
                )

            details = executor(operatie)

            # Visuele verificatie (closed-loop)
            visueel = self._verificeer(operatie, details)
            if visueel is not None:
                details += f" | Visueel: {visueel}"

            # Update tracking
            duur = int((time.time() - start) * 1000)
            self._sessie_operaties += 1
            self._totaal_uitgevoerd += 1
            self._laatste_uitvoer[operatie.type] = time.time()

            # Sensorium event
            try:
                from ..daemon.sensorium import EventType
                self._get_sensorium().sense_event(
                    EventType.TASK_COMPLETE,
                    source="will_protocol",
                    data={
                        "type": operatie.type.value,
                        "reden": operatie.reden,
                    },
                    importance=0.5,
                )
            except (AttributeError, TypeError):
                pass

            log = UitvoerLog(
                operatie=operatie.type.value,
                reden=operatie.reden,
                resultaat=Beslissing.UITGEVOERD.value,
                details=details,
                duur_ms=duur,
                visueel=visueel or "",
            )
            self._log.append(log)
            self._bewaar_log()
            return log

        except Exception as e:
            duur = int((time.time() - start) * 1000)
            log = UitvoerLog(
                operatie=operatie.type.value,
                reden=operatie.reden,
                resultaat=Beslissing.FOUT.value,
                details=str(e),
                duur_ms=duur,
            )
            self._log.append(log)
            self._bewaar_log()
            return log

    # Operaties met filesystem verificatie
    FILESYSTEM_VERIFICATIES = {
        OperationType.RAG_CLEANUP:
            "_verificeer_rag_cleanup",
    }

    def _verificeer(self, operatie, details):
        """Verificatie na executie (filesystem of visueel).

        Controleert of de operatie het verwachte resultaat
        heeft opgeleverd. Filesystem checks gaan voor op
        visuele checks via PixelEye.

        Returns:
            None als geen check, "OK" of "AFWIJKING".
        """
        # 1. Filesystem verificatie (Oracle kijkt)
        fs_methode = self.FILESYSTEM_VERIFICATIES.get(
            operatie.type
        )
        if fs_methode is not None:
            try:
                return getattr(self, fs_methode)(operatie)
            except Exception:
                return None

        # 2. Visuele verificatie (PixelEye kijkt)
        verwachting = self.VISUELE_VERWACHTINGEN.get(
            operatie.type
        )
        if verwachting is None:
            return None

        try:
            eye = self._get_eye()
            result = eye.check_state(verwachting)
            return "OK" if result["match"] else "AFWIJKING"
        except Exception:
            return None

    # ─── Operatie Executors ───

    def _exec_backup(self, operatie: WilOperatie) -> str:
        """Backup kritieke state files."""
        governor = self._get_governor()
        gebackupt = []

        if operatie.data.get("file"):
            # Specifiek bestand
            bestanden = [operatie.data["file"]]
        else:
            # Alle kritieke files
            bestanden = governor.KRITIEKE_STATE_FILES

        for sf in bestanden:
            pad = governor._data_dir / sf
            if pad.exists():
                try:
                    governor.backup_state(pad)
                    gebackupt.append(sf)
                except Exception:
                    pass

        return f"Backup: {len(gebackupt)} bestanden"

    def _exec_cleanup(self, operatie: WilOperatie) -> str:
        """Verwijder oude .log bestanden (bewaar 5 nieuwste)."""
        try:
            logs = sorted(
                Config.LOG_DIR.glob("*.log"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
        except Exception:
            return "Geen logs gevonden"

        # Bewaar 5 nieuwste
        te_verwijderen = logs[5:]
        verwijderd = 0

        for log_pad in te_verwijderen:
            try:
                log_pad.unlink()
                verwijderd += 1
            except OSError:
                pass

        return f"Verwijderd: {verwijderd} log bestanden"

    def _exec_health_check(
        self, operatie: WilOperatie
    ) -> str:
        """Volledige Governor health report."""
        governor = self._get_governor()
        rapport = governor.get_health_report()
        status = rapport.get("overall_status", "ONBEKEND")
        return f"Health: {status}"

    def _exec_optimize(self, operatie: WilOperatie) -> str:
        """Herformateer grote JSON files (compacteer)."""
        governor = self._get_governor()
        bestand = operatie.data.get("file")

        if not bestand:
            return "Geen bestand opgegeven"

        pad = governor._data_dir / bestand
        if not pad.exists():
            return f"{bestand} niet gevonden"

        try:
            with open(pad, "r", encoding="utf-8") as f:
                data = json.load(f)

            oud_grootte = pad.stat().st_size

            with open(pad, "w", encoding="utf-8") as f:
                json.dump(
                    data, f, indent=2, ensure_ascii=False
                )

            nieuw_grootte = pad.stat().st_size
            verschil = oud_grootte - nieuw_grootte

            return (
                f"Geoptimaliseerd: {bestand} "
                f"({verschil:+d} bytes)"
            )
        except (json.JSONDecodeError, IOError) as e:
            return f"Optimize fout: {e}"

    def _exec_script(self, operatie: WilOperatie) -> str:
        """Draai een whitelisted script."""
        script_naam = operatie.data.get("script", "")

        if script_naam not in self.SCRIPT_WHITELIST:
            return f"Script niet in whitelist: {script_naam}"

        bestand = self.SCRIPT_WHITELIST[script_naam]
        pad = Config.BASE_DIR / bestand

        # Veiligheidscheck: moet binnen BASE_DIR vallen
        try:
            pad.resolve().relative_to(
                Config.BASE_DIR.resolve()
            )
        except ValueError:
            return f"Script buiten projectmap: {bestand}"

        if not pad.exists():
            return f"Script niet gevonden: {bestand}"

        try:
            result = subprocess.run(
                ["python", str(pad)],
                timeout=30,
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                return f"Script OK: {bestand}"
            else:
                return (
                    f"Script fout (exit {result.returncode})"
                )
        except subprocess.TimeoutExpired:
            return f"Script timeout: {bestand}"
        except Exception as e:
            return f"Script uitvoerfout: {e}"

    def _exec_nurture(self, operatie: WilOperatie) -> str:
        """Voed daemon nutrienten die tekort komen."""
        if self._daemon is None:
            return "Geen daemon gekoppeld"

        nutrient = operatie.data.get("nutrient", "water")

        try:
            self._daemon.metabolisme.consume(nutrient, 5.0)
            return f"Gevoed: {nutrient} +5.0"
        except (AttributeError, TypeError) as e:
            return f"Nurture fout: {e}"

    def _scan_rag_wezen(self) -> List[str]:
        """Detecteer wees-mappen in ChromaDB opslag.

        Vergelijkt UUID-mappen op schijf met actieve
        segments in de SQLite metadata.

        Returns:
            Lijst van wees UUID-namen.
        """
        db_root = self.RAG_DB_PAD
        sqlite_pad = db_root / "chroma.sqlite3"

        if not sqlite_pad.exists():
            return []

        # Actieve segment UUIDs uit SQLite
        conn = sqlite3.connect(str(sqlite_pad))
        try:
            cur = conn.cursor()
            cur.execute("SELECT id FROM segments")
            actieve_ids = {row[0] for row in cur.fetchall()}
        finally:
            conn.close()

        # UUID-mappen op schijf vs actieve segments
        wezen = []
        for d in db_root.iterdir():
            if (
                d.is_dir()
                and len(d.name) > 30
                and d.name not in actieve_ids
            ):
                wezen.append(d.name)

        return wezen

    def _exec_rag_cleanup(
        self, operatie: WilOperatie
    ) -> str:
        """Verwijder wees-mappen uit ChromaDB opslag.

        Alleen mappen die NIET in de actieve SQLite
        segments staan worden verwijderd.
        """
        db_root = self.RAG_DB_PAD
        wezen = operatie.data.get("wezen", [])

        if not wezen:
            return "Geen wees-mappen opgegeven"

        verwijderd = 0
        vergrendeld = 0

        for naam in wezen:
            pad = db_root / naam
            if not pad.exists():
                continue
            try:
                shutil.rmtree(str(pad))
                verwijderd += 1
            except (PermissionError, OSError):
                vergrendeld += 1

        return (
            f"RAG cleanup: {verwijderd} verwijderd"
            f", {vergrendeld} vergrendeld"
        )

    def _verificeer_rag_cleanup(
        self, operatie
    ) -> str:
        """Filesystem verificatie na RAG cleanup.

        Telt UUID-mappen op schijf en vergelijkt met
        actieve segments. Closed-loop: de Oracle kijkt
        naar de realiteit.

        Returns:
            "OK" of "AFWIJKING".
        """
        try:
            rest_wezen = self._scan_rag_wezen()
            if not rest_wezen:
                return "OK"
            return "AFWIJKING"
        except Exception:
            return None

    def verifieer_intentie(
        self, actie_fn, beschrijving, timeout=5
    ):
        """Voer een actie uit en verifieer visueel.

        Closed-loop voor externe callers: actie uitvoeren,
        screenshot voor/na, LLaVA vergelijkt.

        Args:
            actie_fn: Callable die de actie uitvoert.
            beschrijving: Wat er zou moeten veranderen.
            timeout: Wachttijd na actie (seconden).

        Returns:
            dict met geslaagd, analyse, voor_pad, na_pad.
        """
        eye = self._get_eye()
        return eye.verify_action(
            actie_fn, beschrijving, timeout
        )

    # ─── Autonome Loop ───

    def start(self, interval_seconden=300):
        """Start autonome loop als daemon thread."""
        if self.actief:
            return

        self.actief = True
        self._stop_event.clear()

        def _loop():
            while not self._stop_event.is_set():
                try:
                    self.cyclus()
                except Exception as e:
                    print(f"  [WIL] Cyclus fout: {e}")
                self._stop_event.wait(interval_seconden)
            self.actief = False

        self._thread = threading.Thread(
            target=_loop,
            name="will-protocol",
            daemon=True,
        )
        self._thread.start()

    def stop(self):
        """Stop de autonome loop."""
        self._stop_event.set()
        self.actief = False

    def cyclus(self) -> List[UitvoerLog]:
        """Enkele beslissingscyclus (handmatig)."""
        kandidaten = self._scan()
        goedgekeurd = self._beslis(kandidaten)

        resultaten = []
        for operatie in goedgekeurd:
            log = self._voer_uit(operatie)
            resultaten.append(log)

        return resultaten

    # ─── Status en Demo ───

    def get_status(self) -> dict:
        """Return huidige status."""
        recente = []
        for entry in self._log[-5:]:
            recente.append({
                "operatie": entry.operatie,
                "resultaat": entry.resultaat,
                "timestamp": entry.timestamp,
            })

        return {
            "actief": self.actief,
            "sessie_operaties": self._sessie_operaties,
            "totaal_uitgevoerd": self._totaal_uitgevoerd,
            "totaal_geweigerd": self._totaal_geweigerd,
            "recente_acties": recente,
        }

    def run_simulation(self):
        """Voert 1 cyclus uit met visuele output."""
        print(kleur(
            "\n  ╔═══════════════════════════════════════╗",
            Kleur.FEL_MAGENTA,
        ))
        print(kleur(
            "  ║  QUEST XIII: THE WILL                ║",
            Kleur.FEL_MAGENTA,
        ))
        print(kleur(
            "  ║  Pixel Handelt Autonoom              ║",
            Kleur.FEL_MAGENTA,
        ))
        print(kleur(
            "  ╚═══════════════════════════════════════╝",
            Kleur.FEL_MAGENTA,
        ))
        print()

        # Fase 1: Scan
        print(kleur(
            "  [FASE 1] Systeem scannen...",
            Kleur.FEL_CYAAN,
        ))
        kandidaten = self._scan()
        print(kleur(
            f"    Kandidaten gevonden: {len(kandidaten)}",
            Kleur.CYAAN,
        ))
        for k in kandidaten:
            prio_label = {
                1: "LAAG", 2: "MEDIUM", 3: "HOOG",
            }.get(k.prioriteit, "?")
            print(kleur(
                f"    - [{prio_label}] {k.type.value}:"
                f" {k.reden}",
                Kleur.DIM,
            ))
        print()

        # Fase 2: Beslissen
        print(kleur(
            "  [FASE 2] Beslissingen nemen...",
            Kleur.FEL_GEEL,
        ))
        goedgekeurd = self._beslis(kandidaten)
        afgewezen = len(kandidaten) - len(goedgekeurd)
        print(kleur(
            f"    Goedgekeurd: {len(goedgekeurd)}"
            f" | Afgewezen: {afgewezen}",
            Kleur.GEEL,
        ))
        print()

        # Fase 3: Uitvoeren
        print(kleur(
            "  [FASE 3] Operaties uitvoeren...",
            Kleur.FEL_GROEN,
        ))

        if not goedgekeurd:
            print(kleur(
                "    Geen operaties nodig."
                " Systeem is gezond.",
                Kleur.DIM,
            ))
        else:
            for operatie in goedgekeurd:
                log = self._voer_uit(operatie)
                if log.resultaat == Beslissing.UITGEVOERD.value:
                    symbool = succes("[OK]")
                elif log.resultaat == Beslissing.GEWEIGERD.value:
                    symbool = fout("[GEWEIGERD]")
                else:
                    symbool = fout("[FOUT]")
                visueel_label = ""
                if log.visueel:
                    visueel_label = kleur(
                        f" [{log.visueel}]",
                        Kleur.FEL_CYAAN
                        if log.visueel == "OK"
                        else Kleur.FEL_ROOD,
                    )
                print(
                    f"    {symbool} {log.operatie}:"
                    f" {log.details}"
                    f" ({log.duur_ms}ms)"
                    f"{visueel_label}"
                )

        print()

        # Status
        status = self.get_status()
        print(kleur(
            "  ─── WILL STATUS ───",
            Kleur.FEL_MAGENTA,
        ))
        print(kleur(
            f"    Actief:         "
            f"{'JA' if status['actief'] else 'NEE'}",
            Kleur.CYAAN,
        ))
        print(kleur(
            f"    Sessie ops:     "
            f"{status['sessie_operaties']}",
            Kleur.CYAAN,
        ))
        print(kleur(
            f"    Totaal OK:      "
            f"{status['totaal_uitgevoerd']}",
            Kleur.CYAAN,
        ))
        print(kleur(
            f"    Totaal afgewezen:"
            f" {status['totaal_geweigerd']}",
            Kleur.CYAAN,
        ))
        print()
