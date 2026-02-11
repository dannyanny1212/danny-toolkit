import os
from pathlib import Path

# --- PROJECT PADEN ---
ROOT_DIR = Path(__file__).parent
DATA_DIR = ROOT_DIR / "data"

# Knowledge Base
KNOWLEDGE_DIR = DATA_DIR / "knowledge_base"
CHROMA_DIR = KNOWLEDGE_DIR / "chromadb"
DOCS_DIR = KNOWLEDGE_DIR / "documenten"

# Media & Logs
MEDIA_DIR = DATA_DIR / "media"
LOGS_DIR = DATA_DIR / "logs"

# Database
DB_PATH = DATA_DIR / "cortical_stack.db"

# --- MODEL SETTINGS ---
DEFAULT_MODEL = "groq/llama3-70b"
FALLBACK_MODEL = "ollama/llama3"
VISION_MODEL = "llava"
