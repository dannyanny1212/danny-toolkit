# danny_toolkit/core/faiss_index.py
import logging
import math
import threading

import torch
import faiss

logger = logging.getLogger(__name__)

# Below this threshold, use a simple Flat index (no IVF clustering needed).
_FLAT_THRESHOLD = 256


def _to_numpy_f32(t: torch.Tensor):
    """Safely convert any torch tensor (CPU or CUDA) to float32 numpy."""
    if t.is_cuda:
        t = t.cpu()
    return t.detach().numpy().astype("float32")


class FaissIndex:
    """
    Unified FAISS index with automatic GPU fallback.
    - Small datasets (< 256 vectors): uses IndexFlatL2 (exact search)
    - Large datasets: uses IVF index with proper nprobe (sqrt(nlist))
    - If GPU resources are available: use GPU index
    - Otherwise: use CPU index
    """

    def __init__(self, dim: int, nlist: int = 1024):
        self.dim = dim
        self.nlist = nlist
        self.gpu = False
        self.index = None
        self.trained = False
        self._lock = threading.Lock()

    def _build_index(self, n: int):
        """Build the appropriate index based on dataset size."""
        if n < _FLAT_THRESHOLD:
            cpu_index = faiss.IndexFlatL2(self.dim)
        else:
            effective_nlist = min(self.nlist, n)
            cpu_index = faiss.index_factory(
                self.dim, f"IVF{effective_nlist},Flat", faiss.METRIC_L2
            )

        # Try to move to GPU
        try:
            res = faiss.StandardGpuResources()
            self.index = faiss.index_cpu_to_gpu(res, 0, cpu_index)
            self._gpu_res = res  # prevent GC
            self.gpu = True
        except (RuntimeError, AttributeError) as e:
            logger.warning("FAISS GPU niet beschikbaar, fallback naar CPU: %s", e)
            self.index = cpu_index
            self.gpu = False

    def train(self, xb: torch.Tensor):
        """Train the index (if needed) and add vectors. Safe to call once."""
        xb_np = _to_numpy_f32(xb)
        n = xb_np.shape[0]

        with self._lock:
            if self.trained:
                return

            self._build_index(n)

            if not self.index.is_trained:
                self.index.train(xb_np)

            self.index.add(xb_np)
            self.trained = True

    def add(self, xb: torch.Tensor):
        """Add vectors to an already-trained index."""
        if self.index is None:
            raise RuntimeError("Index is not built yet — call train() first.")
        xb_np = _to_numpy_f32(xb)
        with self._lock:
            self.index.add(xb_np)

    def search(self, xq: torch.Tensor, k: int = 5):
        """Search the index for the k nearest neighbours."""
        if self.index is None:
            raise RuntimeError("Index is not built yet — call train() first.")
        xq_np = _to_numpy_f32(xq)

        with self._lock:
            # For IVF indexes, probe sqrt(nlist) clusters for good recall
            if hasattr(self.index, "nprobe"):
                self.index.nprobe = min(
                    self.index.nlist, max(1, int(math.sqrt(self.index.nlist)))
                )

            D, I = self.index.search(xq_np, k)

        return D, I
