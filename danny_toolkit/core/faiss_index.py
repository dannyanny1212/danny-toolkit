# danny_toolkit/core/faiss_index.py
import torch
import faiss

# Below this threshold, use a simple Flat index (no IVF clustering needed).
_FLAT_THRESHOLD = 256


class FaissIndex:
    """
    Unified FAISS index with automatic GPU fallback.
    - Small datasets (< 256 vectors): uses IndexFlatL2 (exact search)
    - Large datasets: uses IVF index with proper nprobe
    - If GPU resources are available: use GPU index
    - Otherwise: use CPU index
    """

    def __init__(self, dim: int, nlist: int = 1024):
        self.dim = dim
        self.nlist = nlist
        self.gpu = False
        self.index = None
        self.trained = False

    def _build_index(self, n: int):
        """Build the appropriate index based on dataset size."""
        if n < _FLAT_THRESHOLD:
            # Exact search — no training needed, works perfectly for small datasets
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
        except Exception:
            self.index = cpu_index
            self.gpu = False

    def train(self, xb: torch.Tensor):
        xb_np = xb.numpy().astype("float32")
        n = xb_np.shape[0]

        if not self.trained:
            self._build_index(n)

            # Flat indexes don't need training; IVF indexes do
            if not self.index.is_trained:
                self.index.train(xb_np)
            self.trained = True

        self.index.add(xb_np)

    def search(self, xq: torch.Tensor, k: int = 5):
        xq_np = xq.numpy().astype("float32")

        # For IVF indexes, probe enough clusters for good recall
        if hasattr(self.index, "nprobe"):
            self.index.nprobe = min(self.index.nlist, max(1, k * 2))

        D, I = self.index.search(xq_np, k)
        return D, I
