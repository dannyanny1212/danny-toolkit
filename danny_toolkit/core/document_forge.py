"""
DOCUMENT FORGE — De I/O Trechter (Phase 30: Shadow Airlock)
============================================================
Centrale module voor alle document-opslag door AI-agenten.

Agenten mogen NIET meer direct bestanden schrijven met open().
Alle documenten gaan via DocumentForge.sla_document_op(), die:
  1. Machinaal een foutloze YAML-frontmatter header genereert
  2. Metadata-velden forceert (model: voyage, altijd lowercase)
  3. Bestanden opslaat in de staging-map (data/shadow_rag/documenten/)
  4. Bestanden NOOIT direct in productie (data/rag/documenten/) plaatst

De ShadowAirlock valideert staging-bestanden voordat ze naar productie gaan.

Gebruik:
    from danny_toolkit.core.document_forge import DocumentForge

    DocumentForge.sla_document_op(
        bestandsnaam="mijn_rapport.md",
        ruwe_tekst="Dit is de inhoud van het rapport.",
        auteur="Artificer",
        categorie="research",
        tags=["python", "async"],
    )
"""

import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)

try:
    from danny_toolkit.core.config import Config
    HAS_CONFIG = True
except ImportError:
    HAS_CONFIG = False


class DocumentForge:
    """De I/O Trechter — de ENIGE manier hoe een agent een document mag opslaan.

    Alle metadata wordt machinaal aangemaakt, niet door de LLM.
    Dit voorkomt inconsistenties zoals 'Voyage' i.p.v. 'voyage',
    ontbrekende frontmatter, of verkeerde bestandspaden.
    """

    # Verplichte metadata-velden met hun defaultwaarden
    VERPLICHTE_VELDEN = {
        "model": "voyage",       # Embedding model — altijd lowercase
        "language": "nl",        # Standaardtaal
    }

    # Toegestane categorieën (validatie)
    CATEGORIEËN = {
        "knowledge", "research", "tutorial", "reference",
        "rapport", "notitie", "documentatie", "intern",
    }

    # Toegestane extensies
    EXTENSIES = {".md", ".txt"}

    @classmethod
    def _get_staging_dir(cls) -> Path:
        """Geef het staging-pad terug (shadow_rag)."""
        if HAS_CONFIG:
            return Config.SHADOW_RAG_DIR
        return Path("data/shadow_rag/documenten")

    @classmethod
    def _maak_yaml_header(
        cls,
        bestandsnaam: str,
        auteur: str,
        categorie: str,
        tags: List[str],
        extra: Optional[dict] = None,
    ) -> str:
        """Genereer een foutloze YAML-frontmatter header.

        Alle velden worden machinaal gevalideerd en genormaliseerd.
        De LLM heeft hier GEEN invloed op — dit is de kern van de I/O Trechter.

        Args:
            bestandsnaam: Naam van het bestand (wordt titel).
            auteur: Naam van de agent/schrijver.
            categorie: Documentcategorie.
            tags: Lijst van tags.
            extra: Optionele extra metadata-velden.

        Returns:
            Volledige YAML-header string (inclusief --- delimiters).
        """
        # Titel: bestandsnaam zonder extensie, underscores → spaties
        titel = Path(bestandsnaam).stem.replace("_", " ").replace("-", " ").title()

        # Categorie valideren
        if categorie.lower() not in cls.CATEGORIEËN:
            categorie = "intern"
        else:
            categorie = categorie.lower()

        # Tags normaliseren: lowercase, geen duplicaten, max 10
        tags_schoon = list(dict.fromkeys(
            t.lower().strip() for t in tags if t.strip()
        ))[:10]

        # Datum
        nu = datetime.now()

        # Bouw de header regel voor regel (geen yaml library nodig)
        regels = [
            "---",
            f"title: \"{titel}\"",
            f"author: \"{auteur}\"",
            f"model: {cls.VERPLICHTE_VELDEN['model']}",
            f"language: {cls.VERPLICHTE_VELDEN['language']}",
            f"category: {categorie}",
            f"date: {nu.strftime('%Y-%m-%d')}",
            f"created: {nu.isoformat(timespec='seconds')}",
        ]

        # Tags als YAML-lijst
        if tags_schoon:
            tags_str = ", ".join(tags_schoon)
            regels.append(f"tags: [{tags_str}]")

        # Extra metadata (gefilterd — geen overschrijving van verplichte velden)
        if extra:
            verboden = {"title", "author", "model", "date", "created", "tags", "category"}
            for key, value in extra.items():
                if key.lower() not in verboden:
                    # Sanitize: geen newlines of YAML-brekers in waarden
                    waarde = str(value).replace("\n", " ").strip()
                    regels.append(f"{key}: \"{waarde}\"")

        regels.append("---")
        regels.append("")  # Lege regel na header

        return "\n".join(regels)

    @classmethod
    def _sanitize_bestandsnaam(cls, naam: str) -> str:
        """Normaliseer en valideer de bestandsnaam.

        - Verwijder onveilige karakters
        - Forceer toegestane extensie
        - Lowercase
        """
        # Strip pad-componenten (alleen de filename)
        naam = Path(naam).name

        # Verwijder onveilige karakters
        naam = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', naam)

        # Check extensie
        stam = Path(naam).stem
        ext = Path(naam).suffix.lower()
        if ext not in cls.EXTENSIES:
            ext = ".md"

        # Lowercase, max 100 chars
        return f"{stam[:100].lower()}{ext}"

    @classmethod
    def _sanitize_tekst(cls, tekst: str) -> str:
        """Verwijder eventuele bestaande YAML-frontmatter uit de ruwe tekst.

        Agenten proberen soms zelf frontmatter toe te voegen — wij strippen
        dat er altijd uit en vervangen het door onze eigen header.
        """
        # Strip bestaande frontmatter (--- ... ---)
        pattern = r'^---\s*\n.*?\n---\s*\n?'
        tekst = re.sub(pattern, '', tekst, count=1, flags=re.DOTALL)
        return tekst.strip()

    @classmethod
    def sla_document_op(
        cls,
        bestandsnaam: str,
        ruwe_tekst: str,
        auteur: str = "Shadow",
        categorie: str = "intern",
        tags: Optional[List[str]] = None,
        extra_metadata: Optional[dict] = None,
    ) -> Path:
        """Sla een document op met geforceerde YAML-frontmatter.

        Dit is de ENIGE manier hoe een agent een document mag opslaan.
        Het bestand gaat naar de staging-map (shadow_rag), NIET naar productie.
        De ShadowAirlock valideert en promoveert bestanden naar productie.

        Args:
            bestandsnaam: Gewenste bestandsnaam (wordt gesanitized).
            ruwe_tekst: De inhoud van het document (zonder frontmatter).
            auteur: Naam van de schrijvende agent.
            categorie: Documentcategorie (zie CATEGORIEËN).
            tags: Optionele lijst van tags.
            extra_metadata: Optionele extra velden voor de header.

        Returns:
            Path naar het opgeslagen bestand in staging.

        Raises:
            ValueError: Als ruwe_tekst leeg is.
        """
        if not ruwe_tekst or not ruwe_tekst.strip():
            raise ValueError("DocumentForge: ruwe_tekst mag niet leeg zijn.")

        # Stap 1: Bestandsnaam normaliseren
        bestandsnaam = cls._sanitize_bestandsnaam(bestandsnaam)

        # Stap 2: Eventuele LLM-gegenereerde frontmatter strippen
        schone_tekst = cls._sanitize_tekst(ruwe_tekst)

        # Stap 3: Machinale YAML-header genereren
        header = cls._maak_yaml_header(
            bestandsnaam=bestandsnaam,
            auteur=auteur,
            categorie=categorie,
            tags=tags or [],
            extra=extra_metadata,
        )

        # Stap 4: Combineer header + tekst
        volledig_document = header + schone_tekst + "\n"

        # Stap 5: Opslaan in staging-map
        staging_dir = cls._get_staging_dir()
        staging_dir.mkdir(parents=True, exist_ok=True)
        pad = staging_dir / bestandsnaam

        with open(pad, "w", encoding="utf-8") as f:
            f.write(volledig_document)

        logger.info(
            "DocumentForge: '%s' opgeslagen in staging (%d bytes, auteur=%s)",
            bestandsnaam, len(volledig_document), auteur,
        )

        return pad

    @classmethod
    def repareer_bestand(cls, pad: Path) -> bool:
        """Repareer of voeg YAML-frontmatter toe aan een bestaand bestand.

        Gebruikt door de ShadowAirlock Nachtwaker om bestanden te fixen
        die handmatig of door externe scripts in de map zijn geplaatst.

        Args:
            pad: Absoluut pad naar het bestand.

        Returns:
            True als het bestand gerepareerd is, False als het al correct was.
        """
        if not pad.exists():
            return False

        try:
            with open(pad, "r", encoding="utf-8") as f:
                inhoud = f.read()
        except (UnicodeDecodeError, IOError) as e:
            logger.warning("DocumentForge: kan '%s' niet lezen: %s", pad.name, e)
            return False

        # Check of er al een geldige frontmatter is
        heeft_header = inhoud.startswith("---")
        header_correct = True
        fouten = []

        if heeft_header:
            # Parse bestaande frontmatter
            match = re.match(r'^---\s*\n(.*?)\n---', inhoud, re.DOTALL)
            if match:
                header_tekst = match.group(1)
                # Check verplichte velden
                for veld, waarde in cls.VERPLICHTE_VELDEN.items():
                    # Zoek naar het veld in de header
                    veld_match = re.search(
                        rf'^{veld}\s*:\s*(.+)$', header_tekst, re.MULTILINE,
                    )
                    if not veld_match:
                        fouten.append(f"ontbreekt: {veld}")
                        header_correct = False
                    elif veld_match.group(1).strip().lower() != waarde:
                        fouten.append(
                            f"{veld}: '{veld_match.group(1).strip()}' → '{waarde}'",
                        )
                        header_correct = False
            else:
                # Gebroken frontmatter (--- zonder sluitend ---)
                header_correct = False
                fouten.append("gebroken frontmatter (geen sluitend ---)")

        if heeft_header and header_correct:
            return False  # Alles OK, geen reparatie nodig

        # Reparatie: strip oude header, genereer nieuwe
        schone_tekst = cls._sanitize_tekst(inhoud)
        header = cls._maak_yaml_header(
            bestandsnaam=pad.name,
            auteur="auto-repair",
            categorie="intern",
            tags=[],
        )

        volledig = header + schone_tekst + "\n"
        with open(pad, "w", encoding="utf-8") as f:
            f.write(volledig)

        logger.info(
            "DocumentForge: '%s' gerepareerd (%s)",
            pad.name, "; ".join(fouten) if fouten else "header toegevoegd",
        )
        return True

    @classmethod
    def valideer_bestand(cls, pad: Path) -> tuple:
        """Valideer of een bestand correcte YAML-frontmatter heeft.

        Args:
            pad: Pad naar het bestand.

        Returns:
            (is_geldig: bool, fouten: list[str])
        """
        fouten = []

        if not pad.exists():
            return False, ["bestand bestaat niet"]

        try:
            with open(pad, "r", encoding="utf-8") as f:
                inhoud = f.read()
        except (UnicodeDecodeError, IOError) as e:
            return False, [f"leesfout: {e}"]

        # Check frontmatter aanwezigheid
        if not inhoud.startswith("---"):
            fouten.append("geen YAML-frontmatter gevonden")
            return False, fouten

        match = re.match(r'^---\s*\n(.*?)\n---', inhoud, re.DOTALL)
        if not match:
            fouten.append("gebroken frontmatter (geen sluitend ---)")
            return False, fouten

        header_tekst = match.group(1)

        # Check verplichte velden
        for veld, waarde in cls.VERPLICHTE_VELDEN.items():
            veld_match = re.search(
                rf'^{veld}\s*:\s*(.+)$', header_tekst, re.MULTILINE,
            )
            if not veld_match:
                fouten.append(f"ontbreekt: {veld}")
            elif veld_match.group(1).strip().strip('"').lower() != waarde:
                fouten.append(
                    f"{veld} onjuist: '{veld_match.group(1).strip()}' (verwacht: '{waarde}')",
                )

        # Check inhoud niet leeg
        body = inhoud[match.end():].strip()
        if not body:
            fouten.append("document body is leeg")

        return len(fouten) == 0, fouten
