"""
Centrale configuratie voor Danny Toolkit.
Versie 4.0 - COSMIC_OMEGA_V4. Met thema's, talen en validatie.
"""

import os
import json
from pathlib import Path
from typing import Optional


class Thema:
    """Visuele thema's voor de toolkit."""

    THEMAS = {
        "standaard": {
            "naam": "Standaard",
            "primair": "=",
            "secundair": "-",
            "hoek": "+",
            "verticaal": "|",
            "succes": "[OK]",
            "fout": "[X]",
            "waarschuwing": "[!]",
            "info": "[i]"
        },
        "modern": {
            "naam": "Modern",
            "primair": "─",
            "secundair": "·",
            "hoek": "┌",
            "verticaal": "│",
            "succes": "✓",
            "fout": "✗",
            "waarschuwing": "⚠",
            "info": "ℹ"
        },
        "minimaal": {
            "naam": "Minimaal",
            "primair": "-",
            "secundair": " ",
            "hoek": " ",
            "verticaal": " ",
            "succes": "+",
            "fout": "-",
            "waarschuwing": "!",
            "info": "*"
        },
        "retro": {
            "naam": "Retro",
            "primair": "#",
            "secundair": "~",
            "hoek": "*",
            "verticaal": ":",
            "succes": ":)",
            "fout": ":(",
            "waarschuwing": ":o",
            "info": ":>"
        }
    }

    @classmethod
    def get(cls, naam: str) -> dict:
        """Haal thema op bij naam."""
        return cls.THEMAS.get(naam, cls.THEMAS["standaard"])

    @classmethod
    def lijst(cls) -> list:
        """Lijst van beschikbare thema's."""
        return list(cls.THEMAS.keys())


class Taal:
    """Meertalige ondersteuning."""

    TALEN = {
        "nl": {
            "naam": "Nederlands",
            "welkom": "Welkom",
            "terug": "Terug naar hoofdmenu",
            "keuze": "Kies een optie",
            "opslaan": "Opslaan",
            "laden": "Laden",
            "succes": "Gelukt",
            "fout": "Fout",
            "bevestig": "Weet je het zeker?",
            "ja": "j",
            "nee": "n",
            "druk_enter": "Druk op Enter om verder te gaan...",
            "ongeldige_keuze": "Ongeldige keuze",
            "niet_gevonden": "Niet gevonden",
            "leeg": "Leeg",
            "items": "items",
            "voltooien": "Voltooien"
        },
        "en": {
            "naam": "English",
            "welkom": "Welcome",
            "terug": "Back to main menu",
            "keuze": "Choose an option",
            "opslaan": "Save",
            "laden": "Load",
            "succes": "Success",
            "fout": "Error",
            "bevestig": "Are you sure?",
            "ja": "y",
            "nee": "n",
            "druk_enter": "Press Enter to continue...",
            "ongeldige_keuze": "Invalid choice",
            "niet_gevonden": "Not found",
            "leeg": "Empty",
            "items": "items",
            "voltooien": "Complete"
        },
        "de": {
            "naam": "Deutsch",
            "welkom": "Willkommen",
            "terug": "Zurück zum Hauptmenü",
            "keuze": "Wähle eine Option",
            "opslaan": "Speichern",
            "laden": "Laden",
            "succes": "Erfolg",
            "fout": "Fehler",
            "bevestig": "Bist du sicher?",
            "ja": "j",
            "nee": "n",
            "druk_enter": "Drücke Enter um fortzufahren...",
            "ongeldige_keuze": "Ungültige Auswahl",
            "niet_gevonden": "Nicht gefunden",
            "leeg": "Leer",
            "items": "Elemente",
            "voltooien": "Abschließen"
        },
        "fr": {
            "naam": "Français",
            "welkom": "Bienvenue",
            "terug": "Retour au menu principal",
            "keuze": "Choisissez une option",
            "opslaan": "Sauvegarder",
            "laden": "Charger",
            "succes": "Succès",
            "fout": "Erreur",
            "bevestig": "Êtes-vous sûr?",
            "ja": "o",
            "nee": "n",
            "druk_enter": "Appuyez sur Entrée pour continuer...",
            "ongeldige_keuze": "Choix invalide",
            "niet_gevonden": "Non trouvé",
            "leeg": "Vide",
            "items": "éléments",
            "voltooien": "Terminer"
        }
    }

    @classmethod
    def get(cls, code: str) -> dict:
        """Haal taal op bij code."""
        return cls.TALEN.get(code, cls.TALEN["nl"])

    @classmethod
    def lijst(cls) -> list:
        """Lijst van beschikbare talen."""
        return [(code, data["naam"]) for code, data in cls.TALEN.items()]


class ConfigValidator:
    """Valideert configuratie instellingen."""

    @staticmethod
    def valideer_api_key(key: str, provider: str) -> tuple:
        """
        Valideer API key format.
        Returns: (is_valid, message)
        """
        if not key:
            return False, f"Geen {provider} API key gevonden"

        # Basis lengte checks
        min_lengths = {
            "anthropic": 40,
            "voyage": 20,
            "groq": 30
        }

        min_len = min_lengths.get(provider.lower(), 20)
        if len(key) < min_len:
            return False, f"{provider} key lijkt te kort (min {min_len} karakters)"

        # Prefix checks
        prefixes = {
            "anthropic": "sk-ant-",
            "groq": "gsk_"
        }

        expected_prefix = prefixes.get(provider.lower())
        if expected_prefix and not key.startswith(expected_prefix):
            return False, f"{provider} key moet beginnen met '{expected_prefix}'"

        return True, f"{provider} key format OK"

    @staticmethod
    def valideer_pad(pad: Path, moet_bestaan: bool = False) -> tuple:
        """
        Valideer een pad.
        Returns: (is_valid, message)
        """
        try:
            if moet_bestaan and not pad.exists():
                return False, f"Pad bestaat niet: {pad}"
            if pad.exists() and not os.access(pad, os.R_OK):
                return False, f"Geen leesrechten: {pad}"
            return True, f"Pad OK: {pad}"
        except Exception as e:
            return False, f"Pad fout: {e}"

    @staticmethod
    def valideer_geheel_getal(waarde: str, min_val: int = None,
                              max_val: int = None) -> tuple:
        """
        Valideer een geheel getal.
        Returns: (is_valid, parsed_value or message)
        """
        try:
            getal = int(waarde)
            if min_val is not None and getal < min_val:
                return False, f"Waarde moet minimaal {min_val} zijn"
            if max_val is not None and getal > max_val:
                return False, f"Waarde moet maximaal {max_val} zijn"
            return True, getal
        except ValueError:
            return False, "Geen geldig geheel getal"


class Config:
    """Centrale configuratie voor alle modules."""

    # API Keys
    ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
    VOYAGE_API_KEY = os.environ.get("VOYAGE_API_KEY", "")
    GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
    ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

    # Models
    CLAUDE_MODEL = "claude-opus-4-3-20250514"
    MAX_TOKENS = 10000
    VOYAGE_MODEL = "voyage-3"
    GROQ_MODEL = "llama-3.3-70b-versatile"

    # RAG Settings
    CHUNK_SIZE = 350
    CHUNK_OVERLAP = 50
    TOP_K = 5

    # Paths
    BASE_DIR = Path(__file__).parent.parent.parent
    DATA_DIR = BASE_DIR / "data"
    APPS_DATA_DIR = DATA_DIR / "apps"
    RAG_DATA_DIR = DATA_DIR / "rag"
    OUTPUT_DIR = DATA_DIR / "output"
    CONFIG_FILE = DATA_DIR / "toolkit_config.json"

    # App-specific files
    BOODSCHAPPENLIJST_FILE = APPS_DATA_DIR / "boodschappenlijst.txt"
    HUISDIER_FILE = APPS_DATA_DIR / "huisdier.json"
    VECTOR_DB_FILE = RAG_DATA_DIR / "vector_db.json"
    DOCUMENTEN_DIR = RAG_DATA_DIR / "documenten"
    RAPPORTEN_DIR = OUTPUT_DIR / "rapporten"
    BACKUP_DIR = DATA_DIR / "backups"
    LOG_DIR = DATA_DIR / "logs"

    # User preferences (defaults)
    _taal = "nl"
    _thema = "standaard"
    _debug_mode = False

    @classmethod
    def ensure_dirs(cls):
        """Maak alle directories aan indien nodig."""
        dirs = [
            cls.DATA_DIR,
            cls.APPS_DATA_DIR,
            cls.RAG_DATA_DIR,
            cls.OUTPUT_DIR,
            cls.DOCUMENTEN_DIR,
            cls.RAPPORTEN_DIR,
            cls.BACKUP_DIR,
            cls.LOG_DIR
        ]
        for d in dirs:
            d.mkdir(exist_ok=True, parents=True)

    @classmethod
    def has_anthropic_key(cls) -> bool:
        """Check of Anthropic API key beschikbaar is."""
        return bool(cls.ANTHROPIC_API_KEY)

    @classmethod
    def has_voyage_key(cls) -> bool:
        """Check of Voyage API key beschikbaar is."""
        return bool(cls.VOYAGE_API_KEY)

    @classmethod
    def has_groq_key(cls) -> bool:
        """Check of Groq API key beschikbaar is."""
        return bool(cls.GROQ_API_KEY)

    @classmethod
    def has_elevenlabs_key(cls) -> bool:
        """Check of ElevenLabs API key beschikbaar is."""
        return bool(cls.ELEVENLABS_API_KEY)

    @classmethod
    def has_openai_key(cls) -> bool:
        """Check of OpenAI API key beschikbaar is."""
        return bool(cls.OPENAI_API_KEY)

    @classmethod
    def laad_env_bestand(cls, pad: Path = None) -> dict:
        """
        Laad environment variables uit .env bestand.
        Returns: dict met geladen variabelen
        """
        pad = pad or cls.BASE_DIR / ".env"
        geladen = {}

        if not pad.exists():
            return geladen

        with open(pad, "r", encoding="utf-8") as f:
            for regel in f:
                regel = regel.strip()
                if regel and not regel.startswith("#") and "=" in regel:
                    key, value = regel.split("=", 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    os.environ[key] = value
                    geladen[key] = value

        # Update class attributes
        cls.ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
        cls.VOYAGE_API_KEY = os.environ.get("VOYAGE_API_KEY", "")
        cls.GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
        cls.ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")
        cls.OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

        return geladen

    @classmethod
    def get_taal(cls) -> dict:
        """Haal huidige taal instellingen op."""
        return Taal.get(cls._taal)

    @classmethod
    def set_taal(cls, code: str):
        """Stel taal in."""
        if code in Taal.TALEN:
            cls._taal = code
            cls._sla_voorkeuren_op()

    @classmethod
    def get_thema(cls) -> dict:
        """Haal huidig thema op."""
        return Thema.get(cls._thema)

    @classmethod
    def set_thema(cls, naam: str):
        """Stel thema in."""
        if naam in Thema.THEMAS:
            cls._thema = naam
            cls._sla_voorkeuren_op()

    @classmethod
    def is_debug(cls) -> bool:
        """Check of debug mode aan staat."""
        return cls._debug_mode

    @classmethod
    def set_debug(cls, aan: bool):
        """Zet debug mode aan/uit."""
        cls._debug_mode = aan
        cls._sla_voorkeuren_op()

    @classmethod
    def _sla_voorkeuren_op(cls):
        """Sla gebruikersvoorkeuren op."""
        cls.ensure_dirs()
        voorkeuren = {
            "taal": cls._taal,
            "thema": cls._thema,
            "debug_mode": cls._debug_mode
        }
        try:
            with open(cls.CONFIG_FILE, "w",
                       encoding="utf-8") as f:
                json.dump(voorkeuren, f, indent=2,
                          ensure_ascii=False)
        except (IOError, OSError) as e:
            print(f"  Waarschuwing: voorkeuren niet"
                  f" opgeslagen: {e}")

    @classmethod
    def laad_voorkeuren(cls):
        """Laad gebruikersvoorkeuren."""
        if cls.CONFIG_FILE.exists():
            try:
                with open(cls.CONFIG_FILE, "r", encoding="utf-8") as f:
                    voorkeuren = json.load(f)
                cls._taal = voorkeuren.get("taal", "nl")
                cls._thema = voorkeuren.get("thema", "standaard")
                cls._debug_mode = voorkeuren.get("debug_mode", False)
            except (json.JSONDecodeError, IOError):
                pass

    @classmethod
    def valideer_alle_keys(cls) -> list:
        """
        Valideer alle API keys.
        Returns: lijst van (provider, is_valid, message)
        """
        resultaten = []

        if cls.ANTHROPIC_API_KEY:
            valid, msg = ConfigValidator.valideer_api_key(
                cls.ANTHROPIC_API_KEY, "Anthropic"
            )
            resultaten.append(("Anthropic", valid, msg))

        if cls.VOYAGE_API_KEY:
            valid, msg = ConfigValidator.valideer_api_key(
                cls.VOYAGE_API_KEY, "Voyage"
            )
            resultaten.append(("Voyage", valid, msg))

        if cls.GROQ_API_KEY:
            valid, msg = ConfigValidator.valideer_api_key(
                cls.GROQ_API_KEY, "Groq"
            )
            resultaten.append(("Groq", valid, msg))

        return resultaten

    @classmethod
    def toon_status(cls) -> str:
        """Genereer een status rapport van de configuratie."""
        lijnen = []
        lijnen.append("=== CONFIGURATIE STATUS ===\n")

        # API Keys
        lijnen.append("[API Keys]")
        lijnen.append(f"  Anthropic: {'Ja' if cls.has_anthropic_key() else 'Nee'}")
        lijnen.append(f"  Voyage:    {'Ja' if cls.has_voyage_key() else 'Nee'}")
        lijnen.append(f"  Groq:      {'Ja' if cls.has_groq_key() else 'Nee'}")

        # Voorkeuren
        lijnen.append("\n[Voorkeuren]")
        lijnen.append(f"  Taal:  {Taal.get(cls._taal)['naam']} ({cls._taal})")
        lijnen.append(f"  Thema: {Thema.get(cls._thema)['naam']}")
        lijnen.append(f"  Debug: {'Aan' if cls._debug_mode else 'Uit'}")

        # Paths
        lijnen.append("\n[Directories]")
        lijnen.append(f"  Data:    {cls.DATA_DIR}")
        lijnen.append(f"  Apps:    {cls.APPS_DATA_DIR}")
        lijnen.append(f"  RAG:     {cls.RAG_DATA_DIR}")
        lijnen.append(f"  Output:  {cls.OUTPUT_DIR}")
        lijnen.append(f"  Backups: {cls.BACKUP_DIR}")

        return "\n".join(lijnen)


# Laad voorkeuren bij import
Config.laad_voorkeuren()
