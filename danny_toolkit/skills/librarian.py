"""V6 Bridge — re-exporteert TheLibrarian vanuit root."""

import sys
from pathlib import Path

# Root toevoegen aan path
_root = Path(__file__).parent.parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from ingest import TheLibrarian

__all__ = ["TheLibrarian"]
