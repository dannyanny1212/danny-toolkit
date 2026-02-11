"""Root config — afgeleid van danny_toolkit.core.config."""

from danny_toolkit.core.config import Config

# --- PROJECT PADEN (afgeleid van Config) ---
ROOT_DIR = Config.BASE_DIR
DATA_DIR = Config.DATA_DIR

# Knowledge Base (RAG)
KNOWLEDGE_DIR = Config.RAG_DATA_DIR
CHROMA_DIR = KNOWLEDGE_DIR / "chromadb"
DOCS_DIR = Config.DOCUMENTEN_DIR

# Media & Logs
MEDIA_DIR = DATA_DIR / "plots"
LOGS_DIR = Config.LOG_DIR

# Vision (Golden Masters)
GOLDEN_DIR = DATA_DIR / "screenshots" / "golden"

# Database (Episodisch Geheugen)
DB_PATH = DATA_DIR / "cortical_stack.db"

# --- MODEL SETTINGS ---
DEFAULT_MODEL = "ollama/llama3"
FALLBACK_MODEL = "ollama/llama3"
VISION_MODEL = "llava"

# --- AGENT SETTINGS ---
MAX_LOOPS = 5
