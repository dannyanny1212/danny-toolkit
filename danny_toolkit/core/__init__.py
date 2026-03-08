"""Core module - Gedeelde infrastructure."""

from __future__ import annotations

from danny_toolkit.core.config import Config
from danny_toolkit.core.utils import clear_scherm, fix_encoding
from danny_toolkit.core.embeddings import (
    EmbeddingProvider,
    VoyageEmbeddings,
    HashEmbeddings,
    VoyageChromaEmbedding,
    get_chroma_embed_fn,
)
from danny_toolkit.core.vector_store import VectorStore
from danny_toolkit.core.document_processor import DocumentProcessor
from danny_toolkit.core.generator import Generator

try:
    from danny_toolkit.core.key_manager import SmartKeyManager, get_key_manager
    _HAS_KEY_MANAGER = True
except ImportError:
    _HAS_KEY_MANAGER = False
import logging

logger = logging.getLogger(__name__)

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
