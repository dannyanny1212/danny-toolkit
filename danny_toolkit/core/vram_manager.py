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
