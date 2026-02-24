#!/usr/bin/env python3
# LINE 1: The Gate MUST be first.
import danny_toolkit.core.sovereign_gate  # noqa: F401, E402
"""
Danny Toolkit - Unified Python Applications
Entry point voor de toolkit.

Eigendom van danny.laurent1988@gmail.com
"""

import sys

# Fix Windows encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ("--version", "-V"):
        from danny_toolkit import __version__
        print(f"Danny Toolkit v{__version__} — OMEGA_SOVEREIGN")
        sys.exit(0)

    from danny_toolkit.launcher import main
    main()
