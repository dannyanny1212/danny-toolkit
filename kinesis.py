"""
KINETIC CORE — De fysieke manipulator voor LEGION.

Gereedschapskist met acties voor muis, toetsenbord
en applicatiebeheer. Gescheiden van AI-logica
voor veiligheid.

pyautogui.FAILSAFE = True → duw muis naar
linkerbovenhoek om ALLES te stoppen.

Gebruik:
    from kinesis import KineticUnit
    k = KineticUnit()
    k.launch_app("notepad")
    k.type_text("Hallo wereld!")
"""

import os
import platform
import subprocess
import sys
import time

import pyautogui

# Windows UTF-8 fix
if os.name == "nt":
    sys.stdout.reconfigure(encoding="utf-8")

# FAIL-SAFE: Duw muis naar linkerbovenhoek om te stoppen!
pyautogui.FAILSAFE = True


class KineticUnit:
    """De fysieke manipulator voor LEGION."""

    def __init__(self):
        self.os_type = platform.system()

    def launch_app(self, app_name):
        """Start een applicatie (Windows geoptimaliseerd)."""
        print(f"[Kinesis] Launching: {app_name}")
        try:
            if self.os_type == "Windows":
                subprocess.Popen(
                    f"start {app_name}", shell=True
                )
            elif self.os_type == "Darwin":
                subprocess.Popen(
                    ["open", "-a", app_name]
                )
            else:
                subprocess.Popen([app_name])
            time.sleep(2)
            return f"Opened {app_name}"
        except Exception as e:
            return f"Fout bij openen {app_name}: {e}"

    def type_text(self, text, interval=0.05):
        """Typt als een mens (niet in 1x plakken)."""
        print(f"[Kinesis] Typing: {text[:30]}...")
        pyautogui.write(text, interval=interval)
        return "Typing complete"

    def press_key(self, key):
        """Drukt op speciale toetsen (enter, tab, esc, win)."""
        pyautogui.press(key)
        return f"Pressed {key}"

    def hotkey(self, *keys):
        """Combo's zoals Ctrl+C."""
        pyautogui.hotkey(*keys)
        return f"Combo {keys}"

    def take_screenshot(self):
        """Maakt een screenshot (ogen voor Pixel)."""
        screenshot_dir = os.path.join(
            os.path.dirname(__file__), "data"
        )
        os.makedirs(screenshot_dir, exist_ok=True)
        path = os.path.join(
            screenshot_dir, "last_screenshot.png"
        )
        pyautogui.screenshot(path)
        return path

    def capture_screen(
        self, filename="vision_input.png"
    ):
        """Oculus: Maakt een screenshot voor analyse.

        Slaat op in data/plots/ voor de vision
        pipeline (Pixel + Brain closed loop).
        """
        try:
            base = os.path.dirname(__file__)
            filepath = os.path.join(
                base, "data", "plots", filename
            )
            os.makedirs(
                os.path.dirname(filepath),
                exist_ok=True,
            )
            screenshot = pyautogui.screenshot()
            screenshot.save(filepath)
            print(
                f"[Oculus] Screenshot captured:"
                f" {filepath}"
            )
            return filepath
        except Exception as e:
            return f"Fout bij screenshot: {e}"
