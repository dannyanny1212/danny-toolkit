"""Core module - Gedeelde infrastructure."""

from .config import Config
from .utils import clear_scherm, fix_encoding
from .embeddings import (
    EmbeddingProvider,
    VoyageEmbeddings,
    HashEmbeddings,
    VoyageChromaEmbedding,
    get_chroma_embed_fn,
)
from .vector_store import VectorStore
from .document_processor import DocumentProcessor
from .generator import Generator

try:
    from .key_manager import SmartKeyManager, get_key_manager
    _HAS_KEY_MANAGER = True
except ImportError:
    _HAS_KEY_MANAGER = False

__all__ = [
    "Config",
    "clear_scherm",
    "fix_encoding",
    "EmbeddingProvider",
    "VoyageEmbeddings",
    "HashEmbeddings",
    "VoyageChromaEmbedding",
    "get_chroma_embed_fn",
    "VectorStore",
    "DocumentProcessor",
    "Generator",
]

if _HAS_KEY_MANAGER:
    __all__.extend(["SmartKeyManager", "get_key_manager"])
