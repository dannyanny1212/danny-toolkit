"""
VRAM Manager — RTX 3060 Ti (8 GB) geheugen monitor + budget guard.

Budget:
  - Embedding model (mpnet-base-v2): ~400 MB
  - Ollama llava (vision):           ~4.7 GB
  - Totaal verwacht:                 ~5.1 GB
  - Veilige marge:                   ~2.9 GB vrij

Budget Guard:
  - VRAMBudgetGuard prevents TorchGPU and Ollama from competing for VRAM.
  - Callers acquire a slot before GPU work; guard checks free VRAM first.

Gebruik:
  from danny_toolkit.core.vram_manager import check_vram_status, vram_rapport
  from danny_toolkit.core.vram_manager import vram_guard
  check_vram_status()          # Print diagnose naar terminal
  rapport = vram_rapport()     # Dict voor dashboard/NeuralBus
  with vram_guard("embeddings", 400):  # Acquire 400 MB budget slot
      model.embed(texts)
"""
from __future__ import annotations

import logging
import threading

try:
    import torch
    _HAS_TORCH = True
except ImportError:
    _HAS_TORCH = False

logger = logging.getLogger(__name__)

# Drempel in MB — waarschuw als minder dan dit vrij is
VRAM_WARN_THRESHOLD_MB = 1500  # 1.5 GB

# Minimum free VRAM required before allowing a new GPU workload (MB)
_VRAM_MIN_FREE_MB = 1000


def _systeembrede_vram() -> tuple:
    """Lees systeembrede VRAM via torch.cuda.mem_get_info (niet per-proces).

    Returns:
        (vrij_mb, totaal_mb, in_gebruik_mb, gpu_naam) of None als niet beschikbaar.
    """
    if not _HAS_TORCH or not torch.cuda.is_available():
        return None

    vrij_bytes, totaal_bytes = torch.cuda.mem_get_info(0)
    props = torch.cuda.get_device_properties(0)

    totaal_mb = totaal_bytes / (1024 ** 2)
    vrij_mb = vrij_bytes / (1024 ** 2)
    in_gebruik_mb = totaal_mb - vrij_mb

    return vrij_mb, totaal_mb, in_gebruik_mb, props.name


def check_vram_status() -> bool:
    """Print VRAM diagnose naar terminal. Returns True als CUDA beschikbaar."""
    info = _systeembrede_vram()
    if info is None:
        print("[VRAM] CUDA niet beschikbaar — draait op CPU")
        return False

    vrij_mb, totaal_mb, in_gebruik_mb, gpu_naam = info

    print(f"\n=== VRAM DIAGNOSE: {gpu_naam} ===")
    print(f"  Totaal:       {totaal_mb:,.0f} MB")
    print(f"  In gebruik:   {in_gebruik_mb:,.0f} MB")
    print(f"  Vrij:         {vrij_mb:,.0f} MB")

    if vrij_mb < VRAM_WARN_THRESHOLD_MB:
        print(f"  [!] WAARSCHUWING: minder dan {VRAM_WARN_THRESHOLD_MB} MB vrij")
    else:
        print("  [OK] VRAM is gezond")

    return True


def vram_rapport() -> dict:
    """Retourneert systeembrede VRAM status als dict (voor dashboard/NeuralBus).

    Gebruikt torch.cuda.mem_get_info() — meet alle processen (Ollama, embeddings, etc.),
    niet alleen PyTorch geheugen van dit proces.

    Returns:
        Dict met keys: beschikbaar, gpu_naam, totaal_mb, in_gebruik_mb,
        vrij_mb, gezond.
        Als CUDA niet beschikbaar: {"beschikbaar": False}.
    """
    info = _systeembrede_vram()
    if info is None:
        return {"beschikbaar": False}

    vrij_mb, totaal_mb, in_gebruik_mb, gpu_naam = info

    return {
        "beschikbaar": True,
        "gpu_naam": gpu_naam,
        "totaal_mb": round(totaal_mb),
        "in_gebruik_mb": round(in_gebruik_mb),
        "vrij_mb": round(vrij_mb),
        "gezond": vrij_mb >= VRAM_WARN_THRESHOLD_MB,
    }


# =============================================================================
# VRAM BUDGET GUARD — prevents Ollama + TorchGPU VRAM contention
# =============================================================================


class VRAMBudgetGuard:
    """Serializes GPU workloads to prevent OOM on shared 8 GB VRAM.

    Only one heavy GPU consumer (embeddings OR vision) can hold the lock
    at a time.  Before acquiring, checks that enough free VRAM exists.
    If not, the caller either waits (blocking=True) or gets a RuntimeError.

    Usage:
        with vram_guard("embeddings", required_mb=400):
            model.embed(texts)
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._holder: str | None = None

    def acquire(self, name: str, required_mb: int = 0, blocking: bool = True) -> bool:
        """Acquire the VRAM budget slot.

        Args:
            name: Identifier for the workload (e.g. "embeddings", "ollama").
            required_mb: Minimum free VRAM needed before acquiring.
            blocking: Wait for the lock or fail immediately.

        Returns:
            True if acquired, False if non-blocking and unavailable.

        Raises:
            RuntimeError: If not enough free VRAM after acquiring the lock.
        """
        acquired = self._lock.acquire(blocking=blocking)
        if not acquired:
            return False

        # Check free VRAM before committing
        if required_mb > 0:
            info = _systeembrede_vram()
            if info is not None:
                vrij_mb = info[0]
                if vrij_mb < required_mb:
                    self._lock.release()
                    msg = (
                        f"VRAM budget denied for '{name}': need {required_mb} MB "
                        f"but only {vrij_mb:.0f} MB free"
                    )
                    logger.warning(msg)
                    raise RuntimeError(msg)

        self._holder = name
        logger.debug("VRAM budget acquired by '%s' (required=%d MB)", name, required_mb)
        return True

    def release(self):
        """Release the VRAM budget slot."""
        holder = self._holder
        self._holder = None
        if self._lock.locked():
            self._lock.release()
        logger.debug("VRAM budget released by '%s'", holder)

    @property
    def current_holder(self) -> str | None:
        """Name of the current VRAM budget holder, or None."""
        return self._holder


# Module-level singleton
_vram_guard = VRAMBudgetGuard()


class vram_guard:
    """Context manager for VRAM budget acquisition.

    Usage:
        with vram_guard("embeddings", 400):
            model.embed(texts)
    """

    def __init__(self, name: str, required_mb: int = 0, blocking: bool = True):
        self._name = name
        self._required_mb = required_mb
        self._blocking = blocking

    def __enter__(self):
        _vram_guard.acquire(self._name, self._required_mb, self._blocking)
        return _vram_guard

    def __exit__(self, *exc):
        _vram_guard.release()
        return False


def get_vram_guard() -> VRAMBudgetGuard:
    """Return the module-level VRAMBudgetGuard singleton."""
    return _vram_guard
