from __future__ import annotations

import os


def ensure_directory(path: str) -> None:
    """Maakt de directory aan als deze nog niet bestaat."""
    if not os.path.exists(path):
        os.makedirs(path)
