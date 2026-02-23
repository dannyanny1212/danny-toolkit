"""
╔══════════════════════════════════════════════════════════════╗
║  OMEGA SOVEREIGN — COMMAND DECK LAUNCHER                   ║
║  Native Desktop Window (pywebview + Streamlit backend)     ║
║                                                            ║
║  Start: python launch_deck.py                              ║
╚══════════════════════════════════════════════════════════════╝
"""

import sys
import io
import os
import time
import socket
import subprocess
import atexit

# --- Windows UTF-8 ---
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import webview


# ══════════════════════════════════════════════════════════════
# CONFIGURATIE
# ══════════════════════════════════════════════════════════════

TITEL = "OMEGA SOVEREIGN — The Command Deck"
BREEDTE = 1600
HOOGTE = 950
POORT = 8502  # Aparte poort zodat het niet botst met andere Streamlit apps
STREAMLIT_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "command_deck.py")
VENV_PYTHON = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "venv311", "Scripts", "python.exe")
VENV_STREAMLIT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "venv311", "Scripts", "streamlit.exe")


# ══════════════════════════════════════════════════════════════
# HELPER FUNCTIES
# ══════════════════════════════════════════════════════════════

_streamlit_proc = None


def poort_vrij(poort: int) -> bool:
    """Check of een poort vrij is."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", poort)) != 0


def wacht_op_server(poort: int, timeout: float = 15.0) -> bool:
    """Wacht tot de Streamlit server draait."""
    start = time.time()
    while time.time() - start < timeout:
        if not poort_vrij(poort):
            return True
        time.sleep(0.3)
    return False


def start_streamlit() -> subprocess.Popen:
    """Start Streamlit als achtergrondproces."""
    global _streamlit_proc

    # Gebruik de venv streamlit als die bestaat, anders systeembreed
    streamlit_cmd = VENV_STREAMLIT if os.path.exists(VENV_STREAMLIT) else "streamlit"

    cmd = [
        streamlit_cmd,
        "run", STREAMLIT_SCRIPT,
        "--server.headless", "true",
        "--server.port", str(POORT),
        "--server.address", "127.0.0.1",
        "--browser.gatherUsageStats", "false",
        "--global.developmentMode", "false",
        "--server.fileWatcherType", "none",
    ]

    _streamlit_proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
    )

    print(f"[DECK] Streamlit gestart op PID {_streamlit_proc.pid}")
    return _streamlit_proc


def stop_streamlit():
    """Stop het Streamlit achtergrondproces."""
    global _streamlit_proc
    if _streamlit_proc and _streamlit_proc.poll() is None:
        print(f"[DECK] Streamlit stoppen (PID {_streamlit_proc.pid})...")
        _streamlit_proc.terminate()
        try:
            _streamlit_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _streamlit_proc.kill()
        print("[DECK] Streamlit gestopt.")
    _streamlit_proc = None


# ══════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════

def main():
    print("╔══════════════════════════════════════════════════════╗")
    print("║  OMEGA SOVEREIGN — The Command Deck                ║")
    print("║  Native Desktop Launcher                           ║")
    print("╚══════════════════════════════════════════════════════╝")
    print()

    # Cleanup registreren
    atexit.register(stop_streamlit)

    # Check of poort al bezet is
    if not poort_vrij(POORT):
        print(f"[DECK] Poort {POORT} is al in gebruik — hergebruik bestaande server.")
    else:
        # Start Streamlit backend
        print(f"[DECK] Streamlit starten op poort {POORT}...")
        start_streamlit()

        # Wacht tot server klaar is
        print("[DECK] Wachten op server...", end="", flush=True)
        if wacht_op_server(POORT):
            print(" ONLINE")
        else:
            print(" TIMEOUT — probeer toch te openen")

    url = f"http://127.0.0.1:{POORT}"
    print(f"[DECK] Native venster openen: {url}")
    print()

    # Window API voor custom controls vanuit JavaScript
    class VensterAPI:
        def minimize(self):
            webview.windows[0].minimize()

        def maximize(self):
            webview.windows[0].toggle_fullscreen()

        def close(self):
            webview.windows[0].destroy()

    api = VensterAPI()

    # Native desktop venster — FRAMELESS (geen Windows titelbalk)
    venster = webview.create_window(
        title=TITEL,
        url=url,
        width=BREEDTE,
        height=HOOGTE,
        resizable=True,
        frameless=True,
        easy_drag=True,
        min_size=(1200, 700),
        background_color="#050510",
        text_select=True,
        js_api=api,
    )

    # Start pywebview (blokkeert tot venster sluit)
    webview.start(
        debug=False,
        private_mode=True,
    )

    # Venster gesloten — cleanup
    print("[DECK] Venster gesloten.")
    stop_streamlit()
    print("[DECK] Tot ziens, Commandant.")


if __name__ == "__main__":
    main()
