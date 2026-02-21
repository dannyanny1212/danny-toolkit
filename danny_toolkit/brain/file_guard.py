"""
FileGuard — Integriteitscontrole voor Danny Toolkit broncode.
Laag 2 van het bestandsbeschermingssysteem.

Genereert een manifest van alle git-tracked bestanden (pad + SHA256),
detecteert ontbrekende/gewijzigde bestanden en kan auto-herstel uitvoeren.
"""

import hashlib
import json
import os
import sys
import subprocess
from datetime import datetime
from pathlib import Path

if os.name == "nt":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")

from ..core.config import Config
from ..core.utils import kleur, Kleur


_MANIFEST_PAD = Config.DATA_DIR / "file_manifest.json"


class FileGuard:
    """Bewaakt de integriteit van bronbestanden."""

    def __init__(self):
        self.repo_root = Config.BASE_DIR
        self.manifest_pad = _MANIFEST_PAD

    # ── Manifest generatie ──────────────────────────────

    def genereer_manifest(self) -> dict:
        """Maak een snapshot van alle git-tracked bestanden.

        Returns:
            dict met "bestanden" (pad→sha256), "aantal",
            "gegenereerd" timestamp.
        """
        bestanden = self._git_tracked_bestanden()
        hashes = {}
        for rel_pad in bestanden:
            absoluut = self.repo_root / rel_pad
            if absoluut.is_file():
                hashes[rel_pad] = self._sha256(absoluut)

        manifest = {
            "bestanden": hashes,
            "aantal": len(hashes),
            "gegenereerd": datetime.now().isoformat(),
        }

        Config.ensure_dirs()
        with open(self.manifest_pad, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)

        return manifest

    # ── Integriteitscontrole ────────────────────────────

    def controleer_integriteit(self) -> dict:
        """Vergelijk manifest met huidige bestanden.

        Returns:
            dict met "status" (OK/WAARSCHUWING/KRITIEK),
            "ontbrekend" (list), "gewijzigd" (list),
            "nieuw" (list), "totaal_manifest", "totaal_huidig".
        """
        manifest = self._laad_manifest()
        if manifest is None:
            # Eerste keer: genereer manifest
            manifest = self.genereer_manifest()

        manifest_bestanden = manifest.get("bestanden", {})
        huidige_bestanden = self._git_tracked_bestanden()

        ontbrekend = []
        gewijzigd = []
        nieuw = []

        # Check elk bestand in manifest
        for rel_pad, verwachte_hash in manifest_bestanden.items():
            absoluut = self.repo_root / rel_pad
            if not absoluut.is_file():
                ontbrekend.append(rel_pad)
            else:
                huidige_hash = self._sha256(absoluut)
                if huidige_hash != verwachte_hash:
                    gewijzigd.append(rel_pad)

        # Check voor nieuwe bestanden (in git maar niet in manifest)
        for rel_pad in huidige_bestanden:
            if rel_pad not in manifest_bestanden:
                nieuw.append(rel_pad)

        # Bepaal status
        if len(ontbrekend) > 5:
            status = "KRITIEK"
        elif ontbrekend:
            status = "WAARSCHUWING"
        else:
            status = "OK"

        return {
            "status": status,
            "ontbrekend": ontbrekend,
            "gewijzigd": gewijzigd,
            "nieuw": nieuw,
            "totaal_manifest": len(manifest_bestanden),
            "totaal_huidig": len(huidige_bestanden),
            "manifest_datum": manifest.get("gegenereerd", "?"),
        }

    # ── Herstel ─────────────────────────────────────────

    def herstel_bestanden(self, bestanden=None) -> dict:
        """Herstel ontbrekende bestanden vanuit git HEAD.

        Args:
            bestanden: lijst van paden om te herstellen,
                of None voor alle ontbrekende.

        Returns:
            dict met "hersteld" (list), "mislukt" (list).
        """
        if bestanden is None:
            rapport = self.controleer_integriteit()
            bestanden = rapport["ontbrekend"]

        if not bestanden:
            return {"hersteld": [], "mislukt": []}

        hersteld = []
        mislukt = []

        for rel_pad in bestanden:
            try:
                subprocess.run(
                    ["git", "checkout", "HEAD", "--", rel_pad],
                    cwd=str(self.repo_root),
                    capture_output=True,
                    check=True,
                )
                hersteld.append(rel_pad)
            except subprocess.CalledProcessError:
                mislukt.append(rel_pad)

        # Update manifest na herstel
        if hersteld:
            self.genereer_manifest()

        return {"hersteld": hersteld, "mislukt": mislukt}

    # ── Rapport ─────────────────────────────────────────

    def toon_rapport(self, rapport=None):
        """Toon visueel rapport van integriteitscontrole."""
        if rapport is None:
            rapport = self.controleer_integriteit()

        status = rapport["status"]
        if status == "OK":
            status_kleur = Kleur.FEL_GROEN
        elif status == "WAARSCHUWING":
            status_kleur = Kleur.FEL_GEEL
        else:
            status_kleur = Kleur.FEL_ROOD

        print()
        print(kleur(
            "  ══════════════════════════════════════",
            Kleur.CYAAN,
        ))
        print(kleur(
            "  FILE GUARD — Integriteitsrapport",
            Kleur.FEL_CYAAN,
        ))
        print(kleur(
            "  ══════════════════════════════════════",
            Kleur.CYAAN,
        ))

        print(kleur(
            f"\n  Status: {status}",
            status_kleur,
        ))
        print(kleur(
            f"  Manifest: {rapport['totaal_manifest']}"
            f" bestanden",
            Kleur.DIM,
        ))
        print(kleur(
            f"  Huidig:   {rapport['totaal_huidig']}"
            f" bestanden (git-tracked)",
            Kleur.DIM,
        ))
        print(kleur(
            f"  Datum:    {rapport['manifest_datum']}",
            Kleur.DIM,
        ))

        if rapport["ontbrekend"]:
            print(kleur(
                f"\n  ONTBREKEND ({len(rapport['ontbrekend'])}):",
                Kleur.FEL_ROOD,
            ))
            for pad in rapport["ontbrekend"][:20]:
                print(kleur(f"    - {pad}", Kleur.ROOD))
            rest = len(rapport["ontbrekend"]) - 20
            if rest > 0:
                print(kleur(
                    f"    ... en nog {rest} meer",
                    Kleur.DIM,
                ))

        if rapport["gewijzigd"]:
            print(kleur(
                f"\n  GEWIJZIGD ({len(rapport['gewijzigd'])}):",
                Kleur.FEL_GEEL,
            ))
            for pad in rapport["gewijzigd"][:10]:
                print(kleur(f"    ~ {pad}", Kleur.GEEL))
            rest = len(rapport["gewijzigd"]) - 10
            if rest > 0:
                print(kleur(
                    f"    ... en nog {rest} meer",
                    Kleur.DIM,
                ))

        if rapport["nieuw"]:
            print(kleur(
                f"\n  NIEUW ({len(rapport['nieuw'])}):",
                Kleur.FEL_GROEN,
            ))
            for pad in rapport["nieuw"][:10]:
                print(kleur(f"    + {pad}", Kleur.GROEN))
            rest = len(rapport["nieuw"]) - 10
            if rest > 0:
                print(kleur(
                    f"    ... en nog {rest} meer",
                    Kleur.DIM,
                ))

        if status == "OK" and not rapport["ontbrekend"]:
            print(kleur(
                "\n  Alle bestanden intact.",
                Kleur.FEL_GROEN,
            ))

        print()

    # ── Snelle startup check ────────────────────────────

    def startup_check(self) -> bool:
        """Snelle check bij launcher startup.

        Returns:
            True als alles OK, False als er problemen zijn.
        """
        rapport = self.controleer_integriteit()

        if rapport["status"] == "OK":
            return True

        # Toon waarschuwing
        self.toon_rapport(rapport)

        if rapport["ontbrekend"]:
            print(kleur(
                "  Wil je ontbrekende bestanden herstellen"
                " vanuit git? (j/n): ",
                Kleur.FEL_GEEL,
            ), end="")
            try:
                antwoord = input().strip().lower()
                if antwoord == "j":
                    resultaat = self.herstel_bestanden()
                    hersteld = len(resultaat["hersteld"])
                    mislukt = len(resultaat["mislukt"])
                    if hersteld:
                        print(kleur(
                            f"\n  {hersteld} bestanden"
                            f" hersteld!",
                            Kleur.FEL_GROEN,
                        ))
                    if mislukt:
                        print(kleur(
                            f"  {mislukt} bestanden"
                            f" konden niet hersteld worden.",
                            Kleur.FEL_ROOD,
                        ))
                    print()
            except (EOFError, KeyboardInterrupt):
                print()

        return False

    # ── Interne helpers ─────────────────────────────────

    def _git_tracked_bestanden(self) -> list:
        """Haal lijst van git-tracked bestanden op."""
        try:
            result = subprocess.run(
                ["git", "ls-files"],
                cwd=str(self.repo_root),
                capture_output=True,
                text=True,
                check=True,
            )
            bestanden = [
                l for l in result.stdout.strip().split("\n")
                if l.strip()
            ]
            return bestanden
        except (subprocess.CalledProcessError, FileNotFoundError):
            return []

    def _sha256(self, pad: Path) -> str:
        """Bereken SHA256 hash van een bestand."""
        h = hashlib.sha256()
        with open(pad, "rb") as f:
            for blok in iter(lambda: f.read(8192), b""):
                h.update(blok)
        return h.hexdigest()

    def _laad_manifest(self) -> dict | None:
        """Laad bestaand manifest of None."""
        if not self.manifest_pad.exists():
            return None
        try:
            with open(
                self.manifest_pad, "r", encoding="utf-8"
            ) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return None
