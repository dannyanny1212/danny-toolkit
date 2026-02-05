"""
Centrale configuratie voor Danny Toolkit.
"""

import os
from pathlib import Path


class Config:
    """Centrale configuratie voor alle modules."""

    # API Keys
    ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
    VOYAGE_API_KEY = os.environ.get("VOYAGE_API_KEY", "")
    GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

    # Models
    CLAUDE_MODEL = "claude-sonnet-4-20250514"
    VOYAGE_MODEL = "voyage-3"
    GROQ_MODEL = "llama-3.3-70b-versatile"  # Gratis en snel!

    # RAG Settings
    CHUNK_SIZE = 500
    CHUNK_OVERLAP = 100
    TOP_K = 5

    # Paths
    BASE_DIR = Path(__file__).parent.parent.parent
    DATA_DIR = BASE_DIR / "data"
    APPS_DATA_DIR = DATA_DIR / "apps"
    RAG_DATA_DIR = DATA_DIR / "rag"
    OUTPUT_DIR = DATA_DIR / "output"

    # App-specific files
    BOODSCHAPPENLIJST_FILE = APPS_DATA_DIR / "boodschappenlijst.txt"
    HUISDIER_FILE = APPS_DATA_DIR / "huisdier.json"
    VECTOR_DB_FILE = RAG_DATA_DIR / "vector_db.json"
    DOCUMENTEN_DIR = RAG_DATA_DIR / "documenten"
    RAPPORTEN_DIR = OUTPUT_DIR / "rapporten"

    @classmethod
    def ensure_dirs(cls):
        """Maak alle directories aan indien nodig."""
        cls.DATA_DIR.mkdir(exist_ok=True)
        cls.APPS_DATA_DIR.mkdir(exist_ok=True)
        cls.RAG_DATA_DIR.mkdir(exist_ok=True)
        cls.OUTPUT_DIR.mkdir(exist_ok=True)
        cls.DOCUMENTEN_DIR.mkdir(exist_ok=True)
        cls.RAPPORTEN_DIR.mkdir(exist_ok=True)

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
