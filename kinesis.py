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

    def double_click(self, x, y):
        """Dubbelklik op een positie."""
        print(f"[Kinesis] Double-click: ({x},{y})")
        pyautogui.doubleClick(x, y)
        return f"Double-clicked ({x},{y})"

    def right_click(self, x, y):
        """Rechts-klik op een positie."""
        print(f"[Kinesis] Right-click: ({x},{y})")
        pyautogui.rightClick(x, y)
        return f"Right-clicked ({x},{y})"

    def hotkey(self, *keys):
        """Combo's zoals Ctrl+C, Alt+Tab, Ctrl+Shift+S.

        Args:
            *keys: Toetsen in volgorde (modifiers eerst).

        Voorbeelden:
            hotkey("ctrl", "c")        # Kopieer
            hotkey("ctrl", "v")        # Plak
            hotkey("alt", "tab")       # Wissel venster
            hotkey("ctrl", "shift", "s")  # Opslaan als
            hotkey("win", "d")         # Bureaublad
        """
        combo = "+".join(keys)
        print(f"[Kinesis] Hotkey: {combo}")
        pyautogui.hotkey(*keys)
        return f"Hotkey {combo}"

    def drag_drop(self, start_x, start_y,
                  end_x, end_y, duration=0.5):
        """Sleep een element van A naar B.

        Args:
            start_x: X-coordinaat startpositie.
            start_y: Y-coordinaat startpositie.
            end_x: X-coordinaat eindpositie.
            end_y: Y-coordinaat eindpositie.
            duration: Sleeptijd in seconden.
        """
        print(
            f"[Kinesis] Drag: ({start_x},{start_y})"
            f" -> ({end_x},{end_y})"
        )
        pyautogui.moveTo(start_x, start_y)
        pyautogui.drag(
            end_x - start_x,
            end_y - start_y,
            duration=duration,
            button="left",
        )
        return (
            f"Dragged ({start_x},{start_y})"
            f" -> ({end_x},{end_y})"
        )

    def click(self, x, y, button="left", clicks=1):
        """Klik op een positie.

        Args:
            x: X-coordinaat.
            y: Y-coordinaat.
            button: "left", "right" of "middle".
            clicks: Aantal klikken (2 = dubbelklik).
        """
        print(
            f"[Kinesis] Click: ({x},{y})"
            f" [{button}] x{clicks}"
        )
        pyautogui.click(
            x, y, clicks=clicks, button=button,
        )
        return (
            f"Clicked ({x},{y})"
            f" [{button}] x{clicks}"
        )

    def scroll(self, amount, x=None, y=None):
        """Scroll omhoog (positief) of omlaag (negatief).

        Args:
            amount: Scroll-eenheden (+ = omhoog,
                    - = omlaag).
            x: Optioneel X-coordinaat.
            y: Optioneel Y-coordinaat.
        """
        richting = "omhoog" if amount > 0 else "omlaag"
        print(
            f"[Kinesis] Scroll: {amount}"
            f" ({richting})"
        )
        pyautogui.scroll(amount, x=x, y=y)
        return f"Scrolled {amount} ({richting})"

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
