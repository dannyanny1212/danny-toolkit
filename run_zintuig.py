"""
Zesde Zintuig Launcher — Omega Sovereign Neural Monitor.

Usage:
    python run_zintuig.py
"""
from __future__ import annotations

import sys

# Windows UTF-8
try:
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

from danny_toolkit.brain.zesde_zintuig import main

if __name__ == "__main__":
    main()
