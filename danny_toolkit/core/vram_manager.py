"""
VRAM Manager — RTX 3060 Ti (8 GB) geheugen monitor.

Budget:
  - Embedding model (mpnet-base-v2): ~400 MB
  - Ollama llava (vision):           ~4.7 GB
  - Totaal verwacht:                 ~5.1 GB
  - Veilige marge:                   ~2.9 GB vrij

Gebruik:
  from danny_toolkit.core.vram_manager import check_vram_status, vram_rapport
  check_vram_status()          # Print diagnose naar terminal
  rapport = vram_rapport()     # Dict voor dashboard/NeuralBus
"""

try:
    import torch
    _HAS_TORCH = True
except ImportError:
    _HAS_TORCH = False

# Drempel in MB — waarschuw als minder dan dit vrij is
VRAM_WARN_THRESHOLD_MB = 1500  # 1.5 GB


def check_vram_status() -> bool:
    """Print VRAM diagnose naar terminal. Returns True als CUDA beschikbaar."""
    if not _HAS_TORCH or not torch.cuda.is_available():
        print("[VRAM] CUDA niet beschikbaar — draait op CPU")
        return False

    props = torch.cuda.get_device_properties(0)
    totaal_mb = props.total_memory / (1024 ** 2)
    alloc_mb = torch.cuda.memory_allocated(0) / (1024 ** 2)
    reserved_mb = torch.cuda.memory_reserved(0) / (1024 ** 2)
    vrij_mb = totaal_mb - alloc_mb

    print(f"\n=== VRAM DIAGNOSE: {props.name} ===")
    print(f"  Totaal:       {totaal_mb:,.0f} MB")
    print(f"  In gebruik:   {alloc_mb:,.0f} MB")
    print(f"  Gereserveerd: {reserved_mb:,.0f} MB")
    print(f"  Vrij:         {vrij_mb:,.0f} MB")

    if vrij_mb < VRAM_WARN_THRESHOLD_MB:
        print(f"  [!] WAARSCHUWING: minder dan {VRAM_WARN_THRESHOLD_MB} MB vrij")
    else:
        print("  [OK] VRAM is gezond")

    return True


def vram_rapport() -> dict:
    """Retourneert VRAM status als dict (voor dashboard/NeuralBus).

    Returns:
        Dict met keys: beschikbaar, gpu_naam, totaal_mb, in_gebruik_mb,
        gereserveerd_mb, vrij_mb, gezond.
        Als CUDA niet beschikbaar: {"beschikbaar": False}.
    """
    if not _HAS_TORCH or not torch.cuda.is_available():
        return {"beschikbaar": False}

    props = torch.cuda.get_device_properties(0)
    totaal_mb = props.total_memory / (1024 ** 2)
    alloc_mb = torch.cuda.memory_allocated(0) / (1024 ** 2)
    reserved_mb = torch.cuda.memory_reserved(0) / (1024 ** 2)
    vrij_mb = totaal_mb - alloc_mb

    return {
        "beschikbaar": True,
        "gpu_naam": props.name,
        "totaal_mb": round(totaal_mb),
        "in_gebruik_mb": round(alloc_mb),
        "gereserveerd_mb": round(reserved_mb),
        "vrij_mb": round(vrij_mb),
        "gezond": vrij_mb >= VRAM_WARN_THRESHOLD_MB,
    }
