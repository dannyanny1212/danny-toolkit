"""Core module — Gedeelde infrastructure + X32 Security API.

Direct imports (altijd beschikbaar):
    Config, VectorStore, DocumentProcessor, Generator,
    EmbeddingProvider, VoyageEmbeddings, HashEmbeddings

Lazy imports (via try/except — zware deps):
    NeuralBus, get_bus, EventTypes, OmegaSeal, BusEvent,
    generate_silicon_seal, runtime_hardware_guard,
    get_sandbox, SmartKeyManager, get_key_manager
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

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

# ── Lazy imports: Security (zware deps, WMIC scans, .env parsing) ──

try:
    from danny_toolkit.core.key_manager import SmartKeyManager, get_key_manager
    _HAS_KEY_MANAGER = True
except ImportError:
    _HAS_KEY_MANAGER = False

try:
    from danny_toolkit.core.neural_bus import (
        NeuralBus, BusEvent, EventTypes, OmegaSeal, get_bus,
    )
    _HAS_BUS = True
except ImportError:
    _HAS_BUS = False

try:
    from danny_toolkit.core.hardware_anchor import (
        generate_silicon_seal, runtime_hardware_guard, is_virtual_machine,
    )
    _HAS_HARDWARE = True
except ImportError:
    _HAS_HARDWARE = False

try:
    from danny_toolkit.core.sandbox import get_sandbox
    _HAS_SANDBOX = True
except ImportError:
    _HAS_SANDBOX = False

# ── Public API ──

__all__ = [
    # Config & Utils
    "Config",
    "clear_scherm",
    "fix_encoding",
    # Embeddings
    "EmbeddingProvider",
    "VoyageEmbeddings",
    "HashEmbeddings",
    "VoyageChromaEmbedding",
    "get_chroma_embed_fn",
    # Data
    "VectorStore",
    "DocumentProcessor",
    "Generator",
]

if _HAS_KEY_MANAGER:
    __all__.extend(["SmartKeyManager", "get_key_manager"])
if _HAS_BUS:
    __all__.extend(["NeuralBus", "BusEvent", "EventTypes", "OmegaSeal", "get_bus"])
if _HAS_HARDWARE:
    __all__.extend(["generate_silicon_seal", "runtime_hardware_guard", "is_virtual_machine"])
if _HAS_SANDBOX:
    __all__.append("get_sandbox")
