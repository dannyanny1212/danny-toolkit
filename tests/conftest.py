# tests/conftest.py — Zorg dat project root op sys.path staat
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
