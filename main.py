#!/usr/bin/env python3
"""
Danny Toolkit - Unified Python Applications
Entry point voor de toolkit.

Eigendom van danny.laurent1988@gmail.com
"""

import sys

# Fix Windows encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from danny_toolkit.launcher import main

if __name__ == "__main__":
    main()
