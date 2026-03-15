from __future__ import annotations

import logging
import os
from io import BytesIO

logger = logging.getLogger(__name__)

try:
    import requests
    from PIL import Image
    import pandas as pd
    _HAS_DEPS = True
except ImportError:
    _HAS_DEPS = False


def fetch_image(url: str) -> bytes:
    """Fetches an image from a URL."""
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return response.content


def save_image(image_bytes: bytes, filename: str) -> None:
    """Saves an image to the sandbox directory."""
    from danny_toolkit.core.config import Config
    filepath = os.path.join(str(Config.BASE_DIR / "danny_toolkit" / "sandbox"), filename)
    with open(filepath, "wb") as f:
        f.write(image_bytes)


def resize_image(image_path: str, new_size: tuple[int, int]) -> None:
    """Resizes an image and saves it."""
    image = Image.open(image_path)
    image = image.resize(new_size)
    image.save(image_path)


def process_image_data(image_data: bytes) -> object:
    """Processes image data into a DataFrame."""
    image = Image.open(BytesIO(image_data))
    data = {
        "width": [image.width],
        "height": [image.height],
    }
    return pd.DataFrame(data)
