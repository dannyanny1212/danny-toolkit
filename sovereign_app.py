# sovereign_app.py — OMEGA SOVEREIGN v6.1 Command Center
"""
Danny Toolkit Sovereign Dashboard — CustomTkinter GUI.

Knoppen starten de bestaande test-scripts uit run_all_tests.py.
Live console output, Cognitive Load meter, Neural Pulse indicator.

Entry point: python sovereign_app.py
"""

import io
import os
import subprocess
import sys
import threading
import random

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import customtkinter as ctk
from PIL import Image

# Pad naar project root (waar dit script staat)
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))


class SovereignDashboard(ctk.CTk):
    def __init__(self):
        super().__init__()

        # --- Configuratie ---
        self.title("OMEGA SOVEREIGN v6.1 - Command Center")
        self.geometry("1200x850")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.logo_path = os.path.join(PROJECT_ROOT, "image_50b93f.png")
        self.running = False

        # --- UI Layout ---
        self.grid_columnconfigure(1, weight=3)
        self.grid_columnconfigure(2, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # 1. ZIJBALK (Navigatie)
        self.sidebar = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")

        if os.path.exists(self.logo_path):
            img = Image.open(self.logo_path)
            self.logo_img = ctk.CTkImage(light_image=img, dark_image=img, size=(80, 80))
            self.logo_label = ctk.CTkLabel(self.sidebar, image=self.logo_img, text="")
            self.logo_label.pack(pady=10)

        self.label = ctk.CTkLabel(
            self.sidebar, text="OMEGA OS",
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        self.label.pack(pady=5)

        # Separator
        ctk.CTkLabel(
            self.sidebar, text="TEST SUITES",
            font=ctk.CTkFont(size=11), text_color="gray",
        ).pack(pady=(15, 5))

        # Knoppen — paden exact uit run_all_tests.py
        tests = [
            ("Neural Bus",       [sys.executable, os.path.join(PROJECT_ROOT, "test_neural_bus.py")]),
            ("Proactive",        [sys.executable, os.path.join(PROJECT_ROOT, "test_proactive.py")]),
            ("Singularity",      [sys.executable, os.path.join(PROJECT_ROOT, "test_singularity.py")]),
            ("CLI",              [sys.executable, os.path.join(PROJECT_ROOT, "test_cli.py")]),
            ("Neural Hub",       [sys.executable, os.path.join(PROJECT_ROOT, "test_neural_hub.py")]),
            ("Swarm Engine",     [sys.executable, os.path.join(PROJECT_ROOT, "test_swarm_engine.py")]),
            ("Full Chain",       [sys.executable, "-m", "danny_toolkit.test_full_chain"]),
            ("Cosmic Awareness", [sys.executable, "-m", "danny_toolkit.test_cosmic_awareness"]),
        ]

        self.test_buttons = []
        for naam, cmd in tests:
            btn = ctk.CTkButton(
                self.sidebar, text=naam,
                command=lambda c=cmd, n=naam: self.run_test(n, c),
            )
            btn.pack(pady=5, padx=20, fill="x")
            self.test_buttons.append(btn)

        # Run All
        ctk.CTkLabel(self.sidebar, text="").pack(pady=2)
        self.btn_all = ctk.CTkButton(
            self.sidebar, text="Run All Tests",
            fg_color="#6A0DAD", hover_color="#8B2FC9",
            command=lambda: self.run_test(
                "All Tests",
                [sys.executable, os.path.join(PROJECT_ROOT, "run_all_tests.py")],
            ),
        )
        self.btn_all.pack(pady=5, padx=20, fill="x")

        # Launch Omega
        self.btn_ignition = ctk.CTkButton(
            self.sidebar, text="LAUNCH OMEGA",
            fg_color="darkgreen", hover_color="#228B22",
            command=lambda: self.run_test(
                "Omega Ignition",
                [sys.executable, os.path.join(PROJECT_ROOT, "omega_ignition.py")],
            ),
        )
        self.btn_ignition.pack(pady=(15, 10), padx=20, fill="x")

        # 2. CENTRAAL PANEEL (Console)
        self.console_frame = ctk.CTkFrame(self, corner_radius=10)
        self.console_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        self.console_frame.grid_rowconfigure(0, weight=1)
        self.console_frame.grid_columnconfigure(0, weight=1)

        self.console = ctk.CTkTextbox(
            self.console_frame,
            font=("Consolas", 12),
            fg_color="#1a1a1a",
        )
        self.console.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        self.console.insert("0.0", "--- [SYSTEM READY] Wachten op input van Sovereign ---\n")

        # 3. RECHTER PANEEL (Status & Meters)
        self.status_sidebar = ctk.CTkFrame(self, width=250, fg_color="#121212")
        self.status_sidebar.grid(row=0, column=2, padx=10, pady=10, sticky="nsew")

        # Bewustzijnsmeter
        self.awareness_label = ctk.CTkLabel(
            self.status_sidebar, text="COGNITIVE LOAD",
            font=("Segoe UI", 12, "bold"),
        )
        self.awareness_label.pack(pady=(20, 5))
        self.awareness_bar = ctk.CTkProgressBar(
            self.status_sidebar,
            orientation="horizontal",
            progress_color="#A020F0",
        )
        self.awareness_bar.pack(padx=20, fill="x")
        self.awareness_bar.set(0.347)

        # Swarm Stats
        self.stats_frame = ctk.CTkFrame(self.status_sidebar, fg_color="transparent")
        self.stats_frame.pack(pady=20, padx=10, fill="x")

        self._add_stat("TOTAL AGENTS", "347")
        self._add_stat("TIER 1 (TRINITY)", "3 ACTIVE")
        self._add_stat("TIER 2 (GUARDIANS)", "4 ACTIVE")
        self._add_stat("MICRO-NODES", "340 ONLINE")

        # Neural Pulse
        self.pulse_label = ctk.CTkLabel(
            self.status_sidebar, text="NEURAL PULSE",
            font=("Segoe UI", 12, "bold"),
        )
        self.pulse_label.pack(pady=(20, 5))
        self.pulse_display = ctk.CTkLabel(
            self.status_sidebar, text="||||||||||||",
            font=("Consolas", 14), text_color="#00FF00",
        )
        self.pulse_display.pack()

        # Status label
        self.status_label = ctk.CTkLabel(
            self.status_sidebar, text="IDLE",
            font=("Consolas", 11, "bold"), text_color="gray",
        )
        self.status_label.pack(pady=(30, 5))

        self._update_live_meters()

    def _add_stat(self, label, value):
        f = ctk.CTkFrame(self.stats_frame, fg_color="transparent")
        f.pack(fill="x", pady=2)
        ctk.CTkLabel(f, text=label, font=("Segoe UI", 10)).pack(side="left")
        ctk.CTkLabel(
            f, text=value,
            font=("Segoe UI", 10, "bold"), text_color="#A020F0",
        ).pack(side="right")

    def _update_live_meters(self):
        val = random.uniform(0.3, 0.7) if self.running else 0.15
        self.awareness_bar.set(val)

        bars = "|" * random.randint(5, 20) if self.running else "|||"
        self.pulse_display.configure(text=bars)

        if self.running:
            color = "red" if val > 0.6 else "#00FF00"
        else:
            color = "gray"
        self.pulse_display.configure(text_color=color)

        self.after(1000, self._update_live_meters)

    def _append(self, text):
        self.console.insert("end", text)
        self.console.see("end")

    def run_test(self, naam, cmd):
        if self.running:
            self._append("\n[WARN] Er draait al een taak. Wacht tot deze klaar is.\n")
            return
        self.running = True
        self.status_label.configure(text=f"RUNNING: {naam}", text_color="#00FF00")
        self._append(f"\n{'=' * 50}\n>>> [INITIATING] {naam}...\n{'=' * 50}\n")

        thread = threading.Thread(target=self._execute, args=(naam, cmd), daemon=True)
        thread.start()

    def _execute(self, naam, cmd):
        try:
            process = subprocess.Popen(
                cmd,
                cwd=PROJECT_ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
            )
            for line in process.stdout:
                self.after(0, self._append, line)
            process.stdout.close()
            process.wait()

            if process.returncode == 0:
                self.after(0, self._append, f"\n>>> [COMPLETED] {naam} succesvol afgerond.\n")
            else:
                self.after(0, self._append, f"\n>>> [FINISHED] {naam} (exit code {process.returncode})\n")
        except Exception as e:
            self.after(0, self._append, f"\n[CRITICAL ERROR] {e}\n")
        finally:
            self.running = False
            self.after(0, lambda: self.status_label.configure(text="IDLE", text_color="gray"))


if __name__ == "__main__":
    app = SovereignDashboard()
    app.mainloop()
