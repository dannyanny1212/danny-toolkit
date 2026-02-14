# danny_toolkit/core/faiss_index.py
import torch
import faiss

class FaissIndex:
    """
    Unified FAISS index with automatic GPU fallback.
    - If GPU resources are available: use GPU index
    - Otherwise: use CPU index
    """

    def __init__(self, dim: int, nlist: int = 1024):
        self.dim = dim
        self.nlist = nlist

        # Try GPU
        try:
            self.res = faiss.StandardGpuResources()
            cpu_index = faiss.index_factory(dim, f"IVF{nlist},Flat", faiss.METRIC_L2)
            self.index = faiss.index_cpu_to_gpu(self.res, 0, cpu_index)
            self.gpu = True
        except Exception:
            # Fallback to CPU
            self.index = faiss.index_factory(dim, f"IVF{nlist},Flat", faiss.METRIC_L2)
            self.gpu = False

        self.trained = False

    def train(self, xb: torch.Tensor):
        xb_np = xb.numpy().astype("float32")
        n = xb_np.shape[0]

        if not self.trained:
            # Rebuild index if nlist > n
            if n < self.nlist:
                effective_nlist = max(1, n)
                try:
                    self.res = faiss.StandardGpuResources()
                    cpu_index = faiss.index_factory(self.dim, f"IVF{effective_nlist},Flat", faiss.METRIC_L2)
                    self.index = faiss.index_cpu_to_gpu(self.res, 0, cpu_index)
                    self.gpu = True
                except Exception:
                    self.index = faiss.index_factory(self.dim, f"IVF{effective_nlist},Flat", faiss.METRIC_L2)
                    self.gpu = False

            self.index.train(xb_np)
            self.trained = True
        self.index.add(xb_np)

    def search(self, xq: torch.Tensor, k: int = 5):
        xq = xq.numpy().astype("float32")
        D, I = self.index.search(xq, k)
        return D, I
