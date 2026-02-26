"""Launcher voor OMEGA SOVEREIGN UI dashboard op poort 8502."""

import sys
import streamlit.web.cli as stcli
from pathlib import Path

if __name__ == "__main__":
    script_path = Path("omega_sovereign_ui.py").absolute()
    sys.argv = [
        "streamlit", "run", str(script_path),
        "--server.port", "8502",
        "--server.headless", "true",
    ]
    sys.exit(stcli.main())
