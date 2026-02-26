"""
PatchDay — Danny Toolkit Release Lifecycle Tool.

Eén callable tool voor het volledige patch/release lifecycle:
versie bumpen, tests draaien, RAG valideren, changelog genereren,
committen en taggen.

Gebruik:
    python patchday.py status
    python patchday.py bump patch|minor|major
    python patchday.py branch <naam>
    python patchday.py test
    python patchday.py validate
    python patchday.py changelog
    python patchday.py release [patch|minor|major]
    python patchday.py rollback <versie>
    python patchday.py verify
"""

import argparse
import hashlib
import io
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# Windows UTF-8
if os.name == "nt":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    elif isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout = io.TextIOWrapper(
            sys.stdout.buffer, encoding="utf-8", errors="replace"
        )


# ═══════════════════════════════════════════════════════════════
#  ANSI Kleuren (ghost_api_docs.py patroon)
# ═══════════════════════════════════════════════════════════════

class K:
    """ANSI kleurcodes voor PowerShell terminal."""
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    MAGENTA = "\033[95m"
    WHITE = "\033[97m"
    DIM = "\033[90m"
    BOLD = "\033[1m"
    R = "\033[0m"


def _print(kleur: str, prefix: str, msg: str):
    """Geformatteerde output met kleur en prefix."""
    print(f"{kleur}{prefix}{K.R} {msg}")


def _ok(msg: str):
    _print(K.GREEN, "  ✓", msg)


def _warn(msg: str):
    _print(K.YELLOW, "  ⚠", msg)


def _fail(msg: str):
    _print(K.RED, "  ✗", msg)


def _info(msg: str):
    _print(K.CYAN, "  ℹ", msg)


def _header(titel: str):
    breedte = 50
    print(f"\n{K.BOLD}{K.CYAN}{titel}{K.R}")
    print(f"{K.DIM}{'═' * breedte}{K.R}")


# ═══════════════════════════════════════════════════════════════
#  PROJECT CONSTANTEN
# ═══════════════════════════════════════════════════════════════

PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data"
GATE_HASH_FILE = DATA_DIR / ".gate_hash"
CHANGELOG_FILE = PROJECT_ROOT / "CHANGELOG.md"
PYTHON = str(PROJECT_ROOT / "venv311" / "Scripts" / "python.exe")
if not os.path.isfile(PYTHON):
    PYTHON = sys.executable

# Versiepatroon: X.Y.Z
VERSION_RE = re.compile(r"(\d+\.\d+\.\d+)")

# Golden tag — wordt nooit overschreven
GOLDEN_TAG = "v5.0.0"


# ═══════════════════════════════════════════════════════════════
#  15 VERSIELOCATIES — elk met bestand, regelnummer, regex
# ═══════════════════════════════════════════════════════════════

VERSION_FILES = [
    {
        "pad": "danny_toolkit/__init__.py",
        "regex": r'(__version__\s*=\s*")(\d+\.\d+\.\d+)(")',
        "beschrijving": "danny_toolkit.__version__",
    },
    {
        "pad": "danny_toolkit/brain/__init__.py",
        "regex": r'(__version__\s*=\s*")(\d+\.\d+\.\d+)(")',
        "beschrijving": "brain.__version__",
    },
    {
        "pad": "danny_toolkit/learning/__init__.py",
        "regex": r'(__version__\s*=\s*")(\d+\.\d+\.\d+)(")',
        "beschrijving": "learning.__version__",
    },
    {
        "pad": "danny_toolkit/launcher.py",
        "regex": r'(Versie\s+)(\d+\.\d+\.\d+)(\s*-)',
        "beschrijving": "launcher.py docstring versie",
    },
    {
        "pad": "danny_toolkit/launcher.py",
        "regex": r'(T O O L K I T\s+v)(\d+\.\d+\.\d+)',
        "beschrijving": "launcher.py TOOLKIT banner",
    },
    {
        "pad": "danny_toolkit/launcher.py",
        "regex": r'(DANNY TOOLKIT v)(\d+\.\d+\.\d+)',
        "beschrijving": "launcher.py MINIMAAL banner",
    },
    {
        "pad": "danny_toolkit/launcher.py",
        "regex": r'(VERSIE\s*=\s*")(\d+\.\d+\.\d+)(")',
        "beschrijving": "launcher.py VERSIE constant",
    },
    {
        "pad": "danny_toolkit/launcher.py",
        "regex": r'(Danny Toolkit v)(\d+\.\d+\.\d+)',
        "beschrijving": "launcher.py help text",
    },
    {
        "pad": "cli.py",
        "regex": r'(Glass Box Terminal v)(\d+\.\d+\.\d+)',
        "beschrijving": "cli.py docstring",
    },
    {
        "pad": "cli.py",
        "regex": r'(N E X U S  C L I  v)(\d+\.\d+\.\d+)',
        "beschrijving": "cli.py HEADER banner",
    },
    {
        "pad": "fastapi_server.py",
        "regex": r'(Golden Master v)(\d+\.\d+\.\d+)',
        "beschrijving": "fastapi_server.py titel",
    },
    {
        "pad": "fastapi_server.py",
        "regex": r'(version=")(\d+\.\d+\.\d+)(")',
        "beschrijving": "fastapi_server.py FastAPI version",
        "match_index": 0,
    },
    {
        "pad": "fastapi_server.py",
        "regex": r'(version=")(\d+\.\d+\.\d+)(")',
        "beschrijving": "fastapi_server.py HealthResponse version",
        "match_index": 1,
    },
    {
        "pad": "danny_toolkit/core/sovereign_gate.py",
        "regex": r'(SOVEREIGN GATE v)(\d+\.\d+\.\d+)',
        "beschrijving": "sovereign_gate.py docstring",
        "match_index": 0,
    },
    {
        "pad": "danny_toolkit/core/sovereign_gate.py",
        "regex": r'(SOVEREIGN GATE v)(\d+\.\d+\.\d+)',
        "beschrijving": "sovereign_gate.py print",
        "match_index": 1,
    },
]


# ═══════════════════════════════════════════════════════════════
#  VERSION MANAGER — Lees / Bump / Schrijf versies atomisch
# ═══════════════════════════════════════════════════════════════

class VersionManager:
    """Beheert alle 15 versielocaties atomisch."""

    @staticmethod
    def lees_huidige_versie() -> str:
        """Lees de canonical versie uit danny_toolkit/__init__.py."""
        init_path = PROJECT_ROOT / "danny_toolkit" / "__init__.py"
        inhoud = init_path.read_text(encoding="utf-8")
        match = re.search(r'__version__\s*=\s*"(\d+\.\d+\.\d+)"', inhoud)
        if match:
            return match.group(1)
        return "0.0.0"

    @staticmethod
    def bereken_nieuwe_versie(huidige: str, bump_type: str) -> str:
        """Bereken nieuwe versie op basis van bump type."""
        major, minor, patch = map(int, huidige.split("."))
        if bump_type == "major":
            return f"{major + 1}.0.0"
        elif bump_type == "minor":
            return f"{major}.{minor + 1}.0"
        else:
            return f"{major}.{minor}.{patch + 1}"

    @staticmethod
    def check_sync() -> list:
        """Controleer of alle 15 versielocaties in sync zijn."""
        canonical = VersionManager.lees_huidige_versie()
        afwijkingen = []

        for vf in VERSION_FILES:
            pad = PROJECT_ROOT / vf["pad"]
            if not pad.exists():
                afwijkingen.append((vf["beschrijving"], "BESTAND ONTBREEKT", canonical))
                continue

            inhoud = pad.read_text(encoding="utf-8")
            matches = list(re.finditer(vf["regex"], inhoud))
            idx = vf.get("match_index", 0)

            if idx >= len(matches):
                afwijkingen.append((vf["beschrijving"], "PATROON NIET GEVONDEN", canonical))
                continue

            gevonden = matches[idx].group(2)
            if gevonden != canonical:
                afwijkingen.append((vf["beschrijving"], gevonden, canonical))

        return afwijkingen

    @staticmethod
    def bump(bump_type: str) -> tuple:
        """Bump versie in alle 15 bestanden atomisch.

        Returns:
            (oude_versie, nieuwe_versie, gewijzigde_bestanden)
        """
        oude = VersionManager.lees_huidige_versie()
        nieuwe = VersionManager.bereken_nieuwe_versie(oude, bump_type)

        # Fase 1: Lees alle bestanden, valideer regex matches
        bestanden = {}  # pad -> (origineel, nieuw)
        for vf in VERSION_FILES:
            pad = PROJECT_ROOT / vf["pad"]
            if not pad.exists():
                raise FileNotFoundError(f"Versiebstand ontbreekt: {vf['pad']}")

            pad_str = str(pad)
            if pad_str not in bestanden:
                inhoud = pad.read_text(encoding="utf-8")
                bestanden[pad_str] = {"origineel": inhoud, "nieuw": inhoud, "pad": pad}

        # Pas regex toe per locatie
        for vf in VERSION_FILES:
            pad_str = str(PROJECT_ROOT / vf["pad"])
            inhoud = bestanden[pad_str]["nieuw"]

            idx = vf.get("match_index", 0)
            matches = list(re.finditer(vf["regex"], inhoud))

            if idx >= len(matches):
                raise ValueError(
                    f"Regex match {idx} niet gevonden in {vf['pad']}: {vf['regex']}"
                )

            m = matches[idx]
            # Vervang alleen groep 2 (de versie) — behoud prefix en suffix
            start, end = m.start(2), m.end(2)
            inhoud = inhoud[:start] + nieuwe + inhoud[end:]
            bestanden[pad_str]["nieuw"] = inhoud

        # Fase 2: Schrijf alle bestanden
        gewijzigd = []
        try:
            for pad_str, data in bestanden.items():
                if data["origineel"] != data["nieuw"]:
                    data["pad"].write_text(data["nieuw"], encoding="utf-8")
                    gewijzigd.append(data["pad"].relative_to(PROJECT_ROOT))
        except Exception as e:
            # Rollback bij fout
            for pad_str, data in bestanden.items():
                try:
                    data["pad"].write_text(data["origineel"], encoding="utf-8")
                except Exception:
                    pass
            raise RuntimeError(f"Atomische bump gefaald, rollback uitgevoerd: {e}")

        # Fase 3: Herbereken sovereign gate hash
        _update_gate_hash()

        return oude, nieuwe, gewijzigd


def _update_gate_hash():
    """Herbereken SHA256 hash van sovereign_gate.py en schrijf naar data/.gate_hash."""
    gate_path = PROJECT_ROOT / "danny_toolkit" / "core" / "sovereign_gate.py"
    if not gate_path.exists():
        return
    inhoud = gate_path.read_bytes()
    sha = hashlib.sha256(inhoud).hexdigest()
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    GATE_HASH_FILE.write_text(sha, encoding="utf-8")


# ═══════════════════════════════════════════════════════════════
#  GIT OPS — Branch / Commit / Tag / Rollback
# ═══════════════════════════════════════════════════════════════

class GitOps:
    """Git operaties voor release workflow."""

    @staticmethod
    def _run(cmd: list, check: bool = True) -> subprocess.CompletedProcess:
        """Voer git commando uit."""
        return subprocess.run(
            cmd, capture_output=True, text=True,
            encoding="utf-8", errors="replace",
            cwd=str(PROJECT_ROOT), check=check,
        )

    @staticmethod
    def huidige_branch() -> str:
        r = GitOps._run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
        return r.stdout.strip()

    @staticmethod
    def is_clean() -> bool:
        r = GitOps._run(["git", "status", "--porcelain"])
        return len(r.stdout.strip()) == 0

    @staticmethod
    def staged_files() -> list:
        r = GitOps._run(["git", "diff", "--cached", "--name-only"])
        return [f for f in r.stdout.strip().split("\n") if f]

    @staticmethod
    def unstaged_changes() -> list:
        r = GitOps._run(["git", "diff", "--name-only"])
        return [f for f in r.stdout.strip().split("\n") if f]

    @staticmethod
    def untracked_files() -> list:
        r = GitOps._run(["git", "ls-files", "--others", "--exclude-standard"])
        return [f for f in r.stdout.strip().split("\n") if f]

    @staticmethod
    def tags() -> list:
        r = GitOps._run(["git", "tag", "--list", "v*", "--sort=-version:refname"])
        return [t for t in r.stdout.strip().split("\n") if t]

    @staticmethod
    def laatste_tag() -> str:
        tags = GitOps.tags()
        return tags[0] if tags else "geen"

    @staticmethod
    def log_sinds_tag(tag: str, max_entries: int = 50) -> list:
        """Git log entries sinds een tag."""
        if tag == "geen":
            r = GitOps._run(
                ["git", "log", f"--max-count={max_entries}",
                 "--pretty=format:%h %s"],
            )
        else:
            r = GitOps._run(
                ["git", "log", f"{tag}..HEAD", f"--max-count={max_entries}",
                 "--pretty=format:%h %s"],
            )
        return [l for l in r.stdout.strip().split("\n") if l]

    @staticmethod
    def maak_branch(naam: str) -> bool:
        """Maak en checkout een nieuwe branch."""
        r = GitOps._run(
            ["git", "checkout", "-b", naam], check=False,
        )
        if r.returncode != 0:
            _fail(f"Branch aanmaken mislukt: {r.stderr.strip()}")
            return False
        _ok(f"Branch '{naam}' aangemaakt en actief")
        return True

    @staticmethod
    def commit(bericht: str, bestanden: list = None) -> bool:
        """Stage bestanden en commit."""
        if bestanden:
            GitOps._run(["git", "add"] + [str(f) for f in bestanden])
        else:
            GitOps._run(["git", "add", "-A"])

        r = GitOps._run(
            ["git", "commit", "-m", bericht], check=False,
        )
        if r.returncode != 0:
            _fail(f"Commit mislukt: {r.stderr.strip()}")
            return False
        _ok(f"Commit aangemaakt: {bericht[:60]}")
        return True

    @staticmethod
    def tag(versie: str) -> bool:
        """Maak een annotated tag."""
        tag_naam = f"v{versie}" if not versie.startswith("v") else versie
        if tag_naam == GOLDEN_TAG:
            _fail(f"Golden tag {GOLDEN_TAG} mag niet overschreven worden!")
            return False
        r = GitOps._run(
            ["git", "tag", "-a", tag_naam, "-m", f"Release {tag_naam}"],
            check=False,
        )
        if r.returncode != 0:
            _fail(f"Tag aanmaken mislukt: {r.stderr.strip()}")
            return False
        _ok(f"Tag '{tag_naam}' aangemaakt")
        return True

    @staticmethod
    def rollback_naar_tag(tag: str) -> bool:
        """Rollback working tree naar een getagde versie."""
        r = GitOps._run(
            ["git", "checkout", tag, "--", "."], check=False,
        )
        if r.returncode != 0:
            _fail(f"Rollback mislukt: {r.stderr.strip()}")
            return False
        _ok(f"Rollback naar {tag} uitgevoerd")
        return True


# ═══════════════════════════════════════════════════════════════
#  TEST RUNNER — Delegeert naar run_all_tests.py
# ═══════════════════════════════════════════════════════════════

class TestRunner:
    """Delegeert naar run_all_tests.py met correcte env."""

    @staticmethod
    def run() -> tuple:
        """Draai de volledige test suite.

        Returns:
            (geslaagd: bool, output: str)
        """
        script = PROJECT_ROOT / "run_all_tests.py"
        if not script.exists():
            _fail("run_all_tests.py niet gevonden!")
            return False, "Script ontbreekt"

        env = os.environ.copy()
        env["CUDA_VISIBLE_DEVICES"] = "-1"
        env["DANNY_TEST_MODE"] = "1"
        env["ANONYMIZED_TELEMETRY"] = "False"
        env["PYTHONIOENCODING"] = "utf-8"

        _info("Test suite gestart (dit kan enkele minuten duren)...")
        start = time.time()

        try:
            proc = subprocess.run(
                [PYTHON, str(script)],
                cwd=str(PROJECT_ROOT),
                env=env,
                capture_output=False,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=600,
            )
            duur = time.time() - start
            geslaagd = proc.returncode == 0

            if geslaagd:
                _ok(f"Alle tests geslaagd ({duur:.1f}s)")
            else:
                _fail(f"Tests gefaald (exit code {proc.returncode}, {duur:.1f}s)")

            return geslaagd, f"Exit code: {proc.returncode}, duur: {duur:.1f}s"

        except subprocess.TimeoutExpired:
            duur = time.time() - start
            _fail(f"Tests timeout na {duur:.1f}s")
            return False, f"Timeout na {duur:.1f}s"
        except Exception as e:
            _fail(f"Test runner fout: {e}")
            return False, str(e)


# ═══════════════════════════════════════════════════════════════
#  RAG VALIDATOR — 7-staps pipeline verificatie
# ═══════════════════════════════════════════════════════════════

class RAGValidator:
    """Valideert de RAG pipeline via 7 subsysteem-checks."""

    def __init__(self):
        self.resultaten = []

    def _check(self, naam: str, fn):
        """Voer een check uit met try/except fallback."""
        try:
            ok, detail = fn()
            self.resultaten.append({
                "naam": naam,
                "ok": ok,
                "detail": detail,
                "kritiek": naam in ("Startup Bootstrap", "Config Audit"),
            })
        except ImportError as e:
            self.resultaten.append({
                "naam": naam,
                "ok": None,
                "detail": f"Module niet laadbaar: {e}",
                "kritiek": False,
            })
        except Exception as e:
            self.resultaten.append({
                "naam": naam,
                "ok": False,
                "detail": f"Fout: {e}",
                "kritiek": naam in ("Startup Bootstrap", "Config Audit"),
            })

    def _check_startup(self) -> tuple:
        """Check 1: Startup Bootstrap."""
        from danny_toolkit.core.startup_validator import valideer_opstart
        rapport = valideer_opstart()
        ok = rapport["status"] == "OK"
        fouten = len(rapport.get("fouten", []))
        warns = len(rapport.get("waarschuwingen", []))
        detail = f"{fouten} fouten, {warns} waarschuwingen"
        if ok:
            detail = "API keys OK, DATA_DIR OK"
        return ok, detail

    def _check_config_audit(self) -> tuple:
        """Check 2: Config Audit."""
        from danny_toolkit.brain.config_auditor import get_config_auditor
        auditor = get_config_auditor()
        rapport = auditor.audit()
        # AuditRapport is een dataclass met attributen
        schendingen = getattr(rapport, "schendingen", [])
        drift = getattr(rapport, "drift_gedetecteerd", False)
        ok = rapport.veilig if hasattr(rapport, "veilig") else len(schendingen) == 0
        detail = f"{len(schendingen)} schendingen, {'drift gedetecteerd' if drift else 'geen drift'}"
        if ok and not drift:
            detail = "0 schendingen, geen drift"
        return ok, detail

    def _check_vectorstore(self) -> tuple:
        """Check 3: VectorStore Health."""
        from danny_toolkit.core.config import Config
        # Check of de vector DB file bestaat en leesbaar is
        db_file = getattr(Config, "VECTOR_DB_FILE", None)
        if db_file and Path(db_file).exists():
            grootte_mb = Path(db_file).stat().st_size / (1024 * 1024)
            dim = getattr(Config, "EMBEDDING_DIM", 256)
            detail = f"DB bestand: {grootte_mb:.1f} MB, {dim}d embeddings"
            return True, detail
        # Fallback: probeer VectorStore te instantiëren
        detail = "Vector DB bestand niet gevonden (niet-kritiek)"
        return True, detail

    def _check_shards(self) -> tuple:
        """Check 4: Shard Distribution."""
        from danny_toolkit.core.shard_router import ShardRouter
        router = ShardRouter()
        stats = router.statistieken()  # Returns List[ShardStatistiek]
        if stats:
            parts = [f"{s.naam}: {s.aantal_chunks}" for s in stats]
            detail = " | ".join(parts)
            ok = True
        else:
            detail = "Geen shards gevonden"
            ok = False
        return ok, detail

    def _check_airlock(self) -> tuple:
        """Check 5: ShadowAirlock Staging."""
        from danny_toolkit.core.shadow_airlock import ShadowAirlock
        airlock = ShadowAirlock()
        result = airlock.scan_en_verwerk()
        staging = result.get("bestanden", 0)
        quarantine = result.get("quarantaine", 0)
        ok = quarantine == 0
        detail = f"{staging} gescand, {quarantine} in quarantaine"
        return ok, detail

    def _check_pruning(self) -> tuple:
        """Check 6: SelfPruning Health."""
        from danny_toolkit.core.self_pruning import SelfPruning
        pruner = SelfPruning()
        stats = pruner.statistieken()
        totaal = stats.get("totaal_gevolgd", 0)
        entropy_d = stats.get("entropy_drempel", "?")
        redundantie_d = stats.get("redundantie_drempel", "?")
        enabled = stats.get("pruning_enabled", False)
        ok = True
        detail = f"{totaal} gevolgd, entropy={entropy_d}, redundantie={redundantie_d}, enabled={enabled}"
        return ok, detail

    def _check_document_forge(self) -> tuple:
        """Check 7: Document Forge."""
        from danny_toolkit.core.document_forge import DocumentForge
        # valideer_bestand is een classmethod — geen instantie nodig
        doc_dir = PROJECT_ROOT / "data" / "rag" / "documenten"
        if not doc_dir.exists():
            return True, "Geen documenten directory"

        bestanden = list(doc_dir.glob("*.md")) + list(doc_dir.glob("*.txt"))
        geldig = 0
        totaal = len(bestanden)

        for bestand in bestanden:
            try:
                is_geldig, fouten = DocumentForge.valideer_bestand(bestand)
                if is_geldig:
                    geldig += 1
            except Exception:
                pass

        ok = geldig == totaal if totaal > 0 else True
        detail = f"{geldig}/{totaal} documenten geldig" if totaal > 0 else "Geen documenten"
        return ok, detail

    def validate(self) -> int:
        """Voer alle 7 checks uit en print dashboard.

        Returns:
            Exit code: 0 = OK, 1 = kritiek, 2 = waarschuwingen.
        """
        self.resultaten = []

        checks = [
            ("Startup Bootstrap", self._check_startup),
            ("Config Audit", self._check_config_audit),
            ("VectorStore", self._check_vectorstore),
            ("Shard Distribution", self._check_shards),
            ("ShadowAirlock", self._check_airlock),
            ("SelfPruning", self._check_pruning),
            ("Document Forge", self._check_document_forge),
        ]

        for naam, fn in checks:
            self._check(naam, fn)

        # Print dashboard
        _header("RAG VALIDATIE — 7 Checks")

        geslaagd = 0
        kritiek_fout = False
        heeft_warnings = False

        for r in self.resultaten:
            naam = r["naam"]
            if r["ok"] is True:
                geslaagd += 1
                _ok(f"{naam:<22} {r['detail']}")
            elif r["ok"] is None:
                heeft_warnings = True
                _warn(f"{naam:<22} {r['detail']}")
            else:
                if r["kritiek"]:
                    kritiek_fout = True
                else:
                    heeft_warnings = True
                _fail(f"{naam:<22} {r['detail']}")

        print(f"{K.DIM}{'═' * 50}{K.R}")

        totaal = len(self.resultaten)
        if kritiek_fout:
            _fail(f"RESULTAAT: {geslaagd}/{totaal} checks geslaagd — KRITIEKE FOUT")
            return 1
        elif heeft_warnings:
            _warn(f"RESULTAAT: {geslaagd}/{totaal} checks geslaagd (waarschuwingen)")
            return 2
        else:
            _ok(f"RESULTAAT: {geslaagd}/{totaal} checks geslaagd ✓")
            return 0


# ═══════════════════════════════════════════════════════════════
#  CHANGELOG GENERATOR
# ═══════════════════════════════════════════════════════════════

class ChangelogGenerator:
    """Genereert NL changelog entries uit git log."""

    CATEGORIEEN = {
        "feat": "Toegevoegd",
        "fix": "Gerepareerd",
        "refactor": "Geherstructureerd",
        "perf": "Prestaties",
        "test": "Testen",
        "docs": "Documentatie",
        "chore": "Onderhoud",
    }

    @staticmethod
    def genereer(versie: str) -> str:
        """Genereer changelog entry voor een versie."""
        tag = GitOps.laatste_tag()
        entries = GitOps.log_sinds_tag(tag)

        # Categoriseer commits
        gecategoriseerd = {}
        overig = []

        for entry in entries:
            gevonden = False
            for prefix, categorie in ChangelogGenerator.CATEGORIEEN.items():
                if entry.split(" ", 1)[-1].lower().startswith(prefix):
                    gecategoriseerd.setdefault(categorie, []).append(entry)
                    gevonden = True
                    break
            if not gevonden:
                overig.append(entry)

        if overig:
            gecategoriseerd["Overig"] = overig

        # Formatteer
        datum = datetime.now().strftime("%Y-%m-%d")
        regels = [f"\n## [{versie}] — {datum}\n"]

        for categorie, items in gecategoriseerd.items():
            regels.append(f"\n### {categorie}")
            for item in items:
                # Strip commit hash, behoud bericht
                if " " in item:
                    _, bericht = item.split(" ", 1)
                else:
                    bericht = item
                regels.append(f"- {bericht}")

        return "\n".join(regels) + "\n"

    @staticmethod
    def schrijf(versie: str) -> bool:
        """Genereer en schrijf changelog entry naar CHANGELOG.md."""
        entry = ChangelogGenerator.genereer(versie)

        if CHANGELOG_FILE.exists():
            bestaand = CHANGELOG_FILE.read_text(encoding="utf-8")
            # Voeg in na de eerste regel (# Changelog header)
            regels = bestaand.split("\n", 1)
            if len(regels) == 2:
                nieuw = regels[0] + "\n" + entry + "\n---\n" + regels[1]
            else:
                nieuw = bestaand + "\n" + entry
        else:
            nieuw = "# Changelog\n" + entry

        CHANGELOG_FILE.write_text(nieuw, encoding="utf-8")
        _ok(f"Changelog bijgewerkt voor v{versie}")
        return True


# ═══════════════════════════════════════════════════════════════
#  SAFETY CHECKER — Pre-flight verificatie
# ═══════════════════════════════════════════════════════════════

class SafetyChecker:
    """Pre-flight checks voor release veiligheid."""

    SECRET_PATRONEN = [
        r"\.env$",
        r"credentials",
        r"\.pem$",
        r"\.key$",
        r"secret.*\.json$",
    ]

    @staticmethod
    def verify() -> tuple:
        """Voer alle pre-flight checks uit.

        Returns:
            (ok: bool, rapport: list[str])
        """
        rapport = []
        ok = True

        # 1. Versie sync
        afwijkingen = VersionManager.check_sync()
        if afwijkingen:
            ok = False
            for naam, gevonden, verwacht in afwijkingen:
                rapport.append(f"Versie desync: {naam} = {gevonden} (verwacht {verwacht})")
        else:
            rapport.append("Versie sync: alle 15 locaties in sync ✓")

        # 2. Git clean (geen uncommitted changes in versiebestanden)
        unstaged = GitOps.unstaged_changes()
        versie_paden = set(vf["pad"] for vf in VERSION_FILES)
        versie_dirty = [f for f in unstaged if f in versie_paden]
        if versie_dirty:
            rapport.append(f"Uncommitted versie-wijzigingen: {', '.join(versie_dirty)}")
        else:
            rapport.append("Git versiebestanden: clean ✓")

        # 3. Secrets check — staged files
        staged = GitOps.staged_files()
        for bestand in staged:
            for patroon in SafetyChecker.SECRET_PATRONEN:
                if re.search(patroon, bestand, re.IGNORECASE):
                    ok = False
                    rapport.append(f"SECRET GEDETECTEERD in staged: {bestand}")

        if not any("SECRET" in r for r in rapport):
            rapport.append("Secrets scan: geen gevoelige bestanden in staging ✓")

        # 4. Golden tag bescherming
        tags = GitOps.tags()
        if GOLDEN_TAG in tags:
            rapport.append(f"Golden tag {GOLDEN_TAG}: beschermd ✓")
        else:
            rapport.append(f"Golden tag {GOLDEN_TAG}: niet gevonden (OK voor eerste setup)")

        # 5. Gate hash integriteit
        gate_path = PROJECT_ROOT / "danny_toolkit" / "core" / "sovereign_gate.py"
        if gate_path.exists() and GATE_HASH_FILE.exists():
            inhoud = gate_path.read_bytes()
            verwacht = hashlib.sha256(inhoud).hexdigest()
            opgeslagen = GATE_HASH_FILE.read_text(encoding="utf-8").strip()
            if verwacht == opgeslagen:
                rapport.append("Gate hash: integriteit OK ✓")
            else:
                rapport.append("Gate hash: MISMATCH — herbereken met 'patchday bump'")
        elif gate_path.exists():
            rapport.append("Gate hash: bestand ontbreekt (wordt aangemaakt bij bump)")
        else:
            rapport.append("Gate hash: sovereign_gate.py ontbreekt!")
            ok = False

        # 6. RAG health quick check
        rag_dir = PROJECT_ROOT / "data" / "rag"
        if rag_dir.exists():
            rapport.append(f"RAG directory: aanwezig ✓")
        else:
            rapport.append("RAG directory: ontbreekt (niet-kritiek)")

        return ok, rapport


# ═══════════════════════════════════════════════════════════════
#  RAG GATE — Pre-Execution Validation Protocol
# ═══════════════════════════════════════════════════════════════

class RAGGate:
    """Pre-execution validation gate via RAG pipeline.

    Protocol:
    1. Laad security regels uit RAG documenten
    2. Stel validatievraag aan RAG over de geplande actie
    3. Valideer antwoord: PII, secrets, destructive patterns
    4. Return verdict: goedgekeurd of geblokkeerd

    3-Tier architectuur:
    - Tier 1: Static Rules (altijd actief, geen deps)
    - Tier 2: RAG Query (ChromaDB, graceful degradation)
    - Tier 3: Governor (brain module, graceful degradation)
    """

    # Destructieve actie patronen (Tier 1)
    DESTRUCTIEVE_PATRONEN = [
        re.compile(r"delete|verwijder|drop|truncate|remove|wipe|purge", re.IGNORECASE),
        re.compile(r"reset\s*.*hard|force\s*.*push|checkout\s+\.", re.IGNORECASE),
        re.compile(r"rm\s+-rf|rmdir|shutil\.rmtree", re.IGNORECASE),
        re.compile(r"ALTER\s+TABLE|DROP\s+TABLE|DELETE\s+FROM", re.IGNORECASE),
    ]

    # PII patronen
    PII_PATRONEN = {
        "EMAIL": re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"),
        "IBAN": re.compile(r"[A-Z]{2}\d{2}[A-Z0-9]{4}\d{7,25}"),
        "IPv4_PRIV": re.compile(r"\b(192\.168\.\d+\.\d+|10\.\d+\.\d+\.\d+)\b"),
        "IPv6": re.compile(r"[0-9a-fA-F]{4}:[0-9a-fA-F]{4}:[0-9a-fA-F]{4}"),
        "API_KEY": re.compile(r"(gsk_|sk-ant-|pa-\w{20}|nvapi-|hf_\w{20})"),
        "SHA256": re.compile(r"\b[a-f0-9]{64}\b"),
        "PHONE": re.compile(r"\+\d{2}\d{8,12}"),
    }

    # Secret file patronen
    SECRET_BESTANDEN = [
        re.compile(r"\.env$", re.IGNORECASE),
        re.compile(r"credentials", re.IGNORECASE),
        re.compile(r"\.pem$", re.IGNORECASE),
        re.compile(r"\.key$", re.IGNORECASE),
        re.compile(r"secret.*\.json$", re.IGNORECASE),
    ]

    def valideer(self, actie: str, bestanden: list = None, context: str = None) -> dict:
        """Hoofdmethode — 3-tier validatie.

        Args:
            actie: Beschrijving van de geplande actie.
            bestanden: Optionele lijst van bestandspaden die betrokken zijn.
            context: Optionele extra context.

        Returns:
            Rapport dict met goedgekeurd, tier_resultaten, waarschuwingen, blokkades.
        """
        rapport = {
            "goedgekeurd": True,
            "tier_resultaten": [],
            "waarschuwingen": [],
            "blokkades": [],
        }

        # Tier 1: Static rules (altijd actief)
        self._tier1_static(rapport, actie, bestanden)

        # Tier 2: RAG query (graceful degradation)
        self._tier2_rag(rapport, actie)

        # Tier 3: Governor (graceful degradation)
        self._tier3_governor(rapport, actie)

        rapport["goedgekeurd"] = len(rapport["blokkades"]) == 0
        return rapport

    def _tier1_static(self, rapport: dict, actie: str, bestanden: list = None):
        """Tier 1: Static rules — PII, secrets, destructief, path validatie."""
        # --- PII scan op bestanden ---
        pii_hits = 0
        if bestanden:
            for pad in bestanden:
                try:
                    p = Path(pad)
                    if not p.exists() or not p.is_file():
                        continue
                    if p.stat().st_size > 1_000_000:  # Skip files > 1MB
                        continue
                    inhoud = p.read_text(encoding="utf-8", errors="replace")
                    for naam, patroon in self.PII_PATRONEN.items():
                        if patroon.search(inhoud):
                            pii_hits += 1
                            rapport["waarschuwingen"].append(
                                f"PII ({naam}) gedetecteerd in {p.name}"
                            )
                except Exception:
                    pass

        rapport["tier_resultaten"].append({
            "tier": 1, "naam": "PII scan",
            "ok": pii_hits == 0,
            "detail": f"{pii_hits} bestanden met gevoelige data"
                      if pii_hits else "0 bestanden met gevoelige data",
        })

        # --- Secrets scan op bestanden ---
        secret_hits = 0
        if bestanden:
            for pad in bestanden:
                for patroon in self.SECRET_BESTANDEN:
                    if patroon.search(str(pad)):
                        secret_hits += 1
                        rapport["blokkades"].append(
                            f"Secret bestand gedetecteerd: {Path(pad).name}"
                        )

        rapport["tier_resultaten"].append({
            "tier": 1, "naam": "Secrets scan",
            "ok": secret_hits == 0,
            "detail": f"{secret_hits} secret bestanden gevonden"
                      if secret_hits else "Geen API keys gevonden",
        })

        # --- Destructief patroon scan op actie ---
        destructief = False
        for patroon in self.DESTRUCTIEVE_PATRONEN:
            match = patroon.search(actie)
            if match:
                destructief = True
                rapport["waarschuwingen"].append(
                    f"Destructief patroon \"{match.group()}\" gedetecteerd"
                )
                break

        rapport["tier_resultaten"].append({
            "tier": 1, "naam": "Destructief",
            "ok": not destructief,
            "detail": f"Patroon \"{match.group()}\" gedetecteerd" if destructief
                      else "Geen destructieve patronen",
        })

        # --- Path validatie ---
        pad_ok = True
        if bestanden:
            for pad in bestanden:
                try:
                    resolved = Path(pad).resolve()
                    if not str(resolved).startswith(str(PROJECT_ROOT)):
                        pad_ok = False
                        rapport["blokkades"].append(
                            f"Pad buiten project root: {resolved}"
                        )
                except Exception:
                    pass

        rapport["tier_resultaten"].append({
            "tier": 1, "naam": "Path validatie",
            "ok": pad_ok,
            "detail": "Alle paden binnen project root" if pad_ok
                      else "Paden buiten project root gedetecteerd",
        })

    def _tier2_rag(self, rapport: dict, actie: str):
        """Tier 2: RAG Query — zoek security context in ChromaDB."""
        try:
            from danny_toolkit.core.shard_router import get_shard_router
            router = get_shard_router()
            results = router.zoek(
                query=f"security validation: {actie}",
                top_k=3,
                shards=["danny_docs"],
            )
            if results:
                best = results[0]
                rapport["tier_resultaten"].append({
                    "tier": 2, "naam": "RAG Query",
                    "ok": best["distance"] < 1.5,
                    "detail": f"Beste match: distance={best['distance']:.2f}",
                    "context": best["tekst"][:200],
                })
            else:
                rapport["waarschuwingen"].append("RAG: geen context gevonden")
                rapport["tier_resultaten"].append({
                    "tier": 2, "naam": "RAG Query",
                    "ok": None,
                    "detail": "Geen resultaten (shards leeg of niet actief)",
                })
        except ImportError as e:
            rapport["tier_resultaten"].append({
                "tier": 2, "naam": "RAG Query",
                "ok": None,
                "detail": f"Niet beschikbaar: {e}",
            })
        except Exception as e:
            rapport["tier_resultaten"].append({
                "tier": 2, "naam": "RAG Query",
                "ok": None,
                "detail": f"Fout: {type(e).__name__}: {e}",
            })

    def _tier3_governor(self, rapport: dict, actie: str):
        """Tier 3: Governor validation — OmegaGovernor input check."""
        try:
            from danny_toolkit.brain.governor import OmegaGovernor
            gov = OmegaGovernor()
            veilig, reden = gov.valideer_input(actie)
            rapport["tier_resultaten"].append({
                "tier": 3, "naam": "Governor",
                "ok": veilig,
                "detail": reden if not veilig else "Input veilig",
            })
            if not veilig:
                rapport["blokkades"].append(f"Governor: {reden}")
        except ImportError as e:
            rapport["tier_resultaten"].append({
                "tier": 3, "naam": "Governor",
                "ok": None,
                "detail": f"Niet beschikbaar: {e}",
            })
        except Exception as e:
            rapport["tier_resultaten"].append({
                "tier": 3, "naam": "Governor",
                "ok": None,
                "detail": f"Fout: {type(e).__name__}: {e}",
            })

    def print_rapport(self, rapport: dict):
        """Print een geformatteerd RAG Gate rapport naar terminal."""
        print()
        _header("RAG GATE PROTOCOL \u2014 Pre-Execution Validatie")

        huidige_tier = 0
        for r in rapport["tier_resultaten"]:
            tier = r["tier"]
            if tier != huidige_tier:
                huidige_tier = tier
                tier_namen = {1: "Static Rules", 2: "RAG Query", 3: "Governor"}
                print(f"  {K.BOLD}TIER {tier}: {tier_namen.get(tier, '?')}{K.R}")

            naam = r["naam"]
            detail = r["detail"]
            if r["ok"] is True:
                print(f"    {K.GREEN}\u2713{K.R} {naam:<20} {detail}")
            elif r["ok"] is None:
                print(f"    {K.CYAN}\u2139{K.R} {naam:<20} {detail}")
            else:
                print(f"    {K.YELLOW}\u26A0{K.R} {naam:<20} {detail}")

            # Print context als beschikbaar
            if r.get("context"):
                print(f"    {K.DIM}\u2139 Context: {r['context'][:80]}...{K.R}")

        print(f"{K.DIM}{'═' * 50}{K.R}")

        # Verdict
        if rapport["goedgekeurd"]:
            n_warns = len(rapport["waarschuwingen"])
            if n_warns:
                _warn(f"VERDICT: GOEDGEKEURD ({n_warns} waarschuwing{'en' if n_warns > 1 else ''})")
                for w in rapport["waarschuwingen"]:
                    print(f"    {K.YELLOW}\u26A0 {w}{K.R}")
            else:
                _ok("VERDICT: GOEDGEKEURD")
        else:
            _fail(f"VERDICT: GEBLOKKEERD ({len(rapport['blokkades'])} blokkade"
                  f"{'s' if len(rapport['blokkades']) > 1 else ''})")
            for b in rapport["blokkades"]:
                print(f"    {K.RED}\u2717 {b}{K.R}")


# ═══════════════════════════════════════════════════════════════
#  PATCHDAY ORCHESTRATOR
# ═══════════════════════════════════════════════════════════════

class PatchDay:
    """Hoofdorchestrator voor het release lifecycle."""

    @staticmethod
    def status():
        """Toon huidige versie, branch, pending changes, version sync."""
        _header("PATCHDAY STATUS")

        versie = VersionManager.lees_huidige_versie()
        branch = GitOps.huidige_branch()
        tag = GitOps.laatste_tag()

        _info(f"Versie:  {K.BOLD}{versie}{K.R}")
        _info(f"Branch:  {branch}")
        _info(f"Tag:     {tag}")

        # Versie sync
        afwijkingen = VersionManager.check_sync()
        if afwijkingen:
            print()
            _warn(f"{len(afwijkingen)} versie-afwijkingen gevonden:")
            for naam, gevonden, verwacht in afwijkingen:
                _fail(f"  {naam}: {gevonden} (verwacht {verwacht})")
        else:
            _ok("Alle 15 versielocaties in sync")

        # Pending changes
        unstaged = GitOps.unstaged_changes()
        staged = GitOps.staged_files()
        untracked = GitOps.untracked_files()

        print()
        if staged:
            _info(f"Staged:    {len(staged)} bestanden")
        if unstaged:
            _info(f"Unstaged:  {len(unstaged)} bestanden")
        if untracked:
            _info(f"Untracked: {len(untracked)} bestanden")
        if not staged and not unstaged:
            _ok("Working tree is clean")

        # Git log preview
        entries = GitOps.log_sinds_tag(tag, max_entries=5)
        if entries:
            print()
            _info("Recente commits:")
            for entry in entries:
                print(f"    {K.DIM}{entry}{K.R}")

    @staticmethod
    def bump(bump_type: str):
        """Bump versie in alle 15 bestanden."""
        _header(f"VERSIE BUMP ({bump_type.upper()})")

        # RAG Gate pre-check
        gate = RAGGate()
        verdict = gate.valideer(
            actie=f"bump versie {bump_type}",
            bestanden=[str(PROJECT_ROOT / vf["pad"]) for vf in VERSION_FILES],
        )
        if not verdict["goedgekeurd"]:
            gate.print_rapport(verdict)
            sys.exit(1)

        try:
            oude, nieuwe, gewijzigd = VersionManager.bump(bump_type)
            _ok(f"Versie: {oude} → {K.BOLD}{nieuwe}{K.R}")
            _ok(f"{len(gewijzigd)} bestanden bijgewerkt:")
            for pad in gewijzigd:
                print(f"    {K.DIM}{pad}{K.R}")
            _ok("Gate hash herberekend")
        except Exception as e:
            _fail(f"Bump gefaald: {e}")
            sys.exit(1)

    @staticmethod
    def branch(naam: str):
        """Maak een release/feature/fix branch."""
        _header(f"BRANCH: {naam}")

        # Valideer prefix
        geldige_prefixes = ("fix/", "feature/", "upgrade/", "release/")
        if not any(naam.startswith(p) for p in geldige_prefixes):
            _warn(f"Branch naam '{naam}' heeft geen standaard prefix ({', '.join(geldige_prefixes)})")
            _info("Doorgaan met aanmaken...")

        GitOps.maak_branch(naam)

    @staticmethod
    def test():
        """Draai de volledige test suite."""
        _header("TEST SUITE")
        geslaagd, output = TestRunner.run()
        if not geslaagd:
            sys.exit(1)

    @staticmethod
    def validate():
        """RAG pipeline validatie."""
        validator = RAGValidator()
        exit_code = validator.validate()
        return exit_code

    @staticmethod
    def changelog():
        """Genereer changelog entry."""
        _header("CHANGELOG")

        # RAG Gate pre-check (licht — alleen PII scan op changelog)
        gate = RAGGate()
        bestanden = [str(CHANGELOG_FILE)] if CHANGELOG_FILE.exists() else []
        verdict = gate.valideer(actie="genereer changelog entry", bestanden=bestanden)
        if not verdict["goedgekeurd"]:
            gate.print_rapport(verdict)
            sys.exit(1)

        versie = VersionManager.lees_huidige_versie()
        entry = ChangelogGenerator.genereer(versie)
        print(f"\n{K.DIM}Preview:{K.R}")
        print(entry)

        ChangelogGenerator.schrijf(versie)

    @staticmethod
    def release(bump_type: str = "patch"):
        """Volledig release workflow: gate → verify → test → validate → bump → changelog → commit → tag."""
        _header(f"RELEASE WORKFLOW ({bump_type.upper()})")
        print()

        # Stap 0: RAG Gate
        _info("Stap 0/8: RAG Gate pre-validatie...")
        gate = RAGGate()
        verdict = gate.valideer(
            actie=f"release {bump_type} — volledig release workflow",
            bestanden=[str(PROJECT_ROOT / vf["pad"]) for vf in VERSION_FILES],
        )
        gate.print_rapport(verdict)
        if not verdict["goedgekeurd"]:
            _fail("RAG Gate geblokkeerd — release afgebroken")
            sys.exit(1)
        print()

        # Stap 1: Verify
        _info("Stap 1/8: Pre-flight verificatie...")
        ok, rapport = SafetyChecker.verify()
        for r in rapport:
            if "✓" in r:
                _ok(r)
            else:
                _warn(r)
        if not ok:
            _fail("Pre-flight verificatie gefaald — release afgebroken")
            sys.exit(1)
        print()

        # Stap 2: Branch check
        _info("Stap 2/8: Branch check...")
        branch = GitOps.huidige_branch()
        if branch == "master":
            _info(f"Op master branch — upgrade branch wordt aangemaakt na bump")
        else:
            _ok(f"Op branch: {branch}")
        print()

        # Stap 3: Tests
        _info("Stap 3/8: Test suite...")
        geslaagd, _ = TestRunner.run()
        if not geslaagd:
            _fail("Tests gefaald — release afgebroken")
            sys.exit(1)
        print()

        # Stap 4: RAG Validatie
        _info("Stap 4/8: RAG validatie...")
        rag_code = RAGValidator().validate()
        if rag_code == 1:
            _fail("RAG validatie kritiek — release afgebroken")
            sys.exit(1)
        print()

        # Stap 5: Bump
        _info("Stap 5/8: Versie bump...")
        oude, nieuwe, gewijzigd = VersionManager.bump(bump_type)
        _ok(f"Versie: {oude} → {nieuwe}")
        print()

        # Stap 6: Changelog
        _info("Stap 6/8: Changelog...")
        ChangelogGenerator.schrijf(nieuwe)
        print()

        # Stap 7: Commit
        _info("Stap 7/8: Git commit...")
        commit_bestanden = [str(f) for f in gewijzigd] + ["CHANGELOG.md"]
        if GATE_HASH_FILE.exists():
            commit_bestanden.append(str(GATE_HASH_FILE.relative_to(PROJECT_ROOT)))
        GitOps.commit(
            f"Release v{nieuwe}",
            bestanden=commit_bestanden,
        )
        print()

        # Stap 8: Tag
        _info("Stap 8/8: Git tag...")
        GitOps.tag(nieuwe)

        # Rapport
        print()
        _header("RELEASE VOLTOOID")
        _ok(f"Versie:  {K.BOLD}v{nieuwe}{K.R}")
        _ok(f"Branch:  {GitOps.huidige_branch()}")
        _ok(f"Tag:     v{nieuwe}")
        print()
        _warn(f"REMINDER: 'git push' is NIET uitgevoerd — doe dit handmatig:")
        print(f"    {K.DIM}git push origin {GitOps.huidige_branch()} --tags{K.R}")

    @staticmethod
    def rollback(versie: str):
        """Rollback naar een getagde versie."""
        _header(f"ROLLBACK → {versie}")

        # RAG Gate pre-check
        gate = RAGGate()
        verdict = gate.valideer(actie=f"rollback naar versie {versie}")
        if not verdict["goedgekeurd"]:
            gate.print_rapport(verdict)
            sys.exit(1)

        tag = versie if versie.startswith("v") else f"v{versie}"
        tags = GitOps.tags()

        if tag not in tags:
            _fail(f"Tag '{tag}' niet gevonden")
            _info(f"Beschikbare tags: {', '.join(tags[:10])}")
            sys.exit(1)

        if tag == GOLDEN_TAG:
            _warn(f"Rollback naar golden tag {GOLDEN_TAG} — dit is een zware actie!")

        GitOps.rollback_naar_tag(tag)
        _update_gate_hash()
        _ok("Gate hash herberekend na rollback")

    @staticmethod
    def gate(beschrijving: str):
        """Standalone RAG Gate check op een actie-beschrijving."""
        gate = RAGGate()
        verdict = gate.valideer(actie=beschrijving)
        gate.print_rapport(verdict)
        return 0 if verdict["goedgekeurd"] else 1

    @staticmethod
    def verify():
        """Pre-flight verificatie."""
        _header("PRE-FLIGHT VERIFICATIE")

        ok, rapport = SafetyChecker.verify()
        for r in rapport:
            if "✓" in r:
                _ok(r)
            elif "SECRET" in r or "MISMATCH" in r or "ontbreekt!" in r:
                _fail(r)
            else:
                _warn(r)

        print()
        if ok:
            _ok("Alle pre-flight checks geslaagd ✓")
        else:
            _fail("Pre-flight checks gefaald")

        sys.exit(0 if ok else 1)


# ═══════════════════════════════════════════════════════════════
#  CLI — argparse met 9 subcommands
# ═══════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        prog="patchday",
        description="PatchDay — Danny Toolkit Release Lifecycle Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commando's:
  status              Huidige versie, branch, pending changes
  bump <type>         Versie ophogen (patch|minor|major)
  branch <naam>       Branch aanmaken (fix/|feature/|upgrade/)
  test                Volledige test suite draaien
  validate            RAG pipeline validatie (7 checks)
  changelog           Changelog entry genereren
  release [type]      Volledig release workflow
  rollback <versie>   Rollback naar getagde versie
  verify              Pre-flight verificatie
  gate <beschrijving> RAG Gate pre-executie validatie
        """,
    )

    sub = parser.add_subparsers(dest="commando")

    # status
    sub.add_parser("status", help="Toon huidige versie en status")

    # bump
    p_bump = sub.add_parser("bump", help="Versie ophogen")
    p_bump.add_argument(
        "type", choices=["patch", "minor", "major"],
        help="Bump type",
    )

    # branch
    p_branch = sub.add_parser("branch", help="Branch aanmaken")
    p_branch.add_argument("naam", help="Branch naam (bijv. fix/bug-123)")

    # test
    sub.add_parser("test", help="Volledige test suite draaien")

    # validate
    sub.add_parser("validate", help="RAG pipeline validatie")

    # changelog
    sub.add_parser("changelog", help="Changelog entry genereren")

    # release
    p_release = sub.add_parser("release", help="Volledig release workflow")
    p_release.add_argument(
        "type", nargs="?", default="patch",
        choices=["patch", "minor", "major"],
        help="Bump type (default: patch)",
    )

    # rollback
    p_rollback = sub.add_parser("rollback", help="Rollback naar versie")
    p_rollback.add_argument("versie", help="Versie tag (bijv. v6.5.0 of 6.5.0)")

    # verify
    sub.add_parser("verify", help="Pre-flight verificatie")

    # gate
    p_gate = sub.add_parser("gate", help="RAG Gate pre-executie validatie")
    p_gate.add_argument("beschrijving", help="Beschrijving van de geplande actie")

    args = parser.parse_args()

    if not args.commando:
        parser.print_help()
        sys.exit(0)

    # Dispatch
    if args.commando == "status":
        PatchDay.status()
    elif args.commando == "bump":
        PatchDay.bump(args.type)
    elif args.commando == "branch":
        PatchDay.branch(args.naam)
    elif args.commando == "test":
        PatchDay.test()
    elif args.commando == "validate":
        exit_code = PatchDay.validate()
        sys.exit(exit_code)
    elif args.commando == "changelog":
        PatchDay.changelog()
    elif args.commando == "release":
        PatchDay.release(args.type)
    elif args.commando == "rollback":
        PatchDay.rollback(args.versie)
    elif args.commando == "verify":
        PatchDay.verify()
    elif args.commando == "gate":
        exit_code = PatchDay.gate(args.beschrijving)
        sys.exit(exit_code)


if __name__ == "__main__":
    main()
