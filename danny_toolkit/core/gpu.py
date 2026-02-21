# core/gpu.py
import os

# Guard: lege string veroorzaakt CUDA segfault op Windows (0xC0000005)
if os.environ.get("CUDA_VISIBLE_DEVICES", None) in ("", "-1"):
    os.environ["CUDA_VISIBLE_DEVICES"] = "-1"

import torch


def get_device() -> torch.device:
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")
