import os
from pathlib import Path

# --- PROJECT PADEN ---
ROOT_DIR = Path(__file__).parent
DATA_DIR = ROOT_DIR / "data"

# Knowledge Base (RAG)
KNOWLEDGE_DIR = DATA_DIR / "rag"
CHROMA_DIR = KNOWLEDGE_DIR / "chromadb"
DOCS_DIR = KNOWLEDGE_DIR / "documenten"

# Media & Logs
MEDIA_DIR = DATA_DIR / "plots"
LOGS_DIR = DATA_DIR / "logs"

# Database (Episodisch Geheugen)
DB_PATH = DATA_DIR / "cortical_stack.db"

# --- MODEL SETTINGS ---
DEFAULT_MODEL = "groq/llama3-70b"
FALLBACK_MODEL = "ollama/llama3"
VISION_MODEL = "llava"

# --- AGENT SETTINGS ---
MAX_LOOPS = 5
