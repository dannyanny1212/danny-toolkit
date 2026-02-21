"""
Create a Windows desktop shortcut for Omega Sovereign.

Uses a temporary VBScript to create the .lnk file — no pywin32 needed.
Run once: python create_desktop_icon.py
"""

import os
import subprocess
import sys
import tempfile

# Paths
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
DESKTOP = os.path.join(os.path.expanduser("~"), "Desktop")
SHORTCUT_PATH = os.path.join(DESKTOP, "Omega Sovereign.lnk")
TARGET = os.path.join(PROJECT_DIR, "launch_omega.bat")
ICON = os.path.join(PROJECT_DIR, "sovereign.ico")
WORKING_DIR = PROJECT_DIR


def create_shortcut():
    """Create .lnk via a tiny VBScript (standard Windows, no dependencies)."""

    # Escape backslashes for VBScript string literals
    vbs_lines = [
        'Set oWS = WScript.CreateObject("WScript.Shell")',
        f'Set oLink = oWS.CreateShortcut("{SHORTCUT_PATH}")',
        f'oLink.TargetPath = "{TARGET}"',
        f'oLink.WorkingDirectory = "{WORKING_DIR}"',
        'oLink.WindowStyle = 1',
        f'oLink.Description = "Omega Sovereign v6.1 — Strategist + Artificer + VoidWalker + TheCortex + NeuralBus"',
    ]

    if os.path.isfile(ICON):
        vbs_lines.append(f'oLink.IconLocation = "{ICON}"')

    vbs_lines.append("oLink.Save")

    vbs_script = "\r\n".join(vbs_lines)

    # Write temp VBScript and execute
    fd, vbs_path = tempfile.mkstemp(suffix=".vbs")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(vbs_script)

        result = subprocess.run(
            ["cscript", "//Nologo", vbs_path],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode == 0:
            print(f"[OK] Snelkoppeling aangemaakt: {SHORTCUT_PATH}")
            print(f"     Target: {TARGET}")
            print(f"     Icon:   {ICON if os.path.isfile(ICON) else '(default)'}")
        else:
            print(f"[FOUT] VBScript error:\n{result.stderr}")
            sys.exit(1)
    finally:
        os.unlink(vbs_path)


if __name__ == "__main__":
    if not os.path.isfile(TARGET):
        print(f"[FOUT] Target niet gevonden: {TARGET}")
        print("       Maak eerst launch_omega.bat aan.")
        sys.exit(1)

    create_shortcut()
