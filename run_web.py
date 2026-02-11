import sys
import streamlit.web.cli as stcli
from pathlib import Path

if __name__ == "__main__":
    script_path = Path(
        "sanctuary_ui.py"
    ).absolute()
    sys.argv = [
        "streamlit", "run", str(script_path),
    ]
    sys.exit(stcli.main())
