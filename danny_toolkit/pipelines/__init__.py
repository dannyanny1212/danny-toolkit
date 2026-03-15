"""Danny Toolkit — Pipeline modules (RAG chain, GPU inference)."""
from __future__ import annotations

try:
    from danny_toolkit.pipelines.rag_chain import run_rag_chain
    from danny_toolkit.pipelines.rag_gpu import run_demo as run_gpu_demo
    _HAS_PIPELINES = True
except ImportError:
    _HAS_PIPELINES = False

__all__ = []
if _HAS_PIPELINES:
    __all__.extend(["run_rag_chain", "run_gpu_demo"])
