# core/gpu.py
import os

# Guard: lege string veroorzaakt CUDA segfault op Windows (0xC0000005)
if os.environ.get("CUDA_VISIBLE_DEVICES", None) in ("", "-1"):
    os.environ["CUDA_VISIBLE_DEVICES"] = "-1"

import torch


def get_device() -> torch.device:
    """Returns the device to be used for PyTorch operations, prioritizing a CUDA device if available.

 Args:
  None

 Returns:
  torch.device: The device to be used for PyTorch operations, either 'cuda' or 'cpu'."""
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")
