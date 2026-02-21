import asyncio
import io
import json
import logging
import os
import shutil
import sqlite3
import subprocess
import sys
import time
import urllib.request

logger = logging.getLogger(__name__)

# Windows UTF-8 fix (project conventie)
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# Forceer het pad
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from danny_toolkit.core.utils import Kleur

class OmegaIgnition:
    def __init__(self):
        self.root_dir = os.path.dirname(os.path.abspath(__file__))
        self.db_path = os.path.join(self.root_dir, "danny_toolkit", "data", "brain", "cortical_stack.db")
        self.errors = 0

    async def boot_sequence(self):
        self.clear_screen()
        print(f"{Kleur.CYAAN}")
        print("   ____  __  __ _____ ____    _      ___ ____ _   _ ___ _____ ___ ___  _   _ ")
        print("  / __ \\|  \\/  | ____/ ___|  / \\    |_ _/ ___| \\ | |_ _|_   _|_ _/ _ \\| \\ | |")
        print(" | |  | | |\\/| |  _|| |  _  / _ \\    | | |  _|  \\| || |  | |  | | | | |  \\| |")
        print(" | |__| | |  | | |__| |_| |/ ___ \\   | | |_| | |\\  || |  | |  | | |_| | |\\  |")
        print("  \\____/|_|  |_|_____|\\____/_/   \\_\\ |___|\\____|_| \\_|___| |_| |___|\\___/|_| \\_|")
        print(f"                                                             v6.0 Bootloader{Kleur.RESET}\n")

        print(f"{Kleur.MAGENTA}Initiating pre-flight diagnostics...{Kleur.RESET}\n")
        time.sleep(1)

        await self.fase_1_hardware_api()
        await self.fase_2_neural_link()
        self.fase_3_optimalisatie()

        if self.errors > 0:
            print(f"\n{Kleur.ROOD}⚠️ Boot sequence completed with {self.errors} errors. Systeem is mogelijk instabiel.{Kleur.RESET}")
            keuze = input("Wil je toch doorgaan naar Omega Core? (j/n): ")
            if keuze.lower() != 'j':
                sys.exit(1)
        else:
            print(f"\n{Kleur.GROEN}✅ All systems nominal. Ignition in 3 seconds...{Kleur.RESET}")
            time.sleep(3)

        self.launch_omega()

    async def fase_1_hardware_api(self):
        print(f"{Kleur.GEEL}[1/3] HARDWARE & API CHECK{Kleur.RESET}")

        # Groq
        if os.getenv("GROQ_API_KEY"):
            print(f"  {Kleur.GROEN}✔ Groq API Key: Actief{Kleur.RESET}")
        else:
            print(f"  {Kleur.ROOD}❌ Groq API Key: ONTBREEKT{Kleur.RESET}")
            self.errors += 1

        # Ollama
        try:
            req = urllib.request.Request("http://localhost:11434/api/tags")
            with urllib.request.urlopen(req, timeout=2) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode())
                    if any("llava" in m['name'] for m in data.get('models', [])):
                        print(f"  {Kleur.GROEN}✔ Visual Cortex (Ollama/Llava): Online{Kleur.RESET}")
                    else:
                        print(f"  {Kleur.GEEL}⚠ Ollama draait, maar 'llava' ontbreekt.{Kleur.RESET}")
        except Exception as e:
            logger.debug("Ollama check mislukt: %s", e)
            print(f"  {Kleur.ROOD}❌ Visual Cortex (Ollama): Offline.{Kleur.RESET}")
            self.errors += 1

    async def fase_2_neural_link(self):
        print(f"\n{Kleur.GEEL}[2/3] NEURAL LINK CHECK (v6.0 Modules){Kleur.RESET}")
        try:
            # Onderdruk stdout tijdens import — voorkomt dat Daemon/Governor
            # banners door de diagnostics heen schieten
            _real_stdout = sys.stdout
            _devnull = open(os.devnull, "w", encoding="utf-8")
            sys.stdout = _devnull
            try:
                from danny_toolkit.brain import Strategist, Tribunal, VoidWalker
                from danny_toolkit.brain import TheCortex, TheOracleEye
                from danny_toolkit.core.neural_bus import get_bus
                bus = get_bus()
            finally:
                sys.stdout = _real_stdout
                _devnull.close()

            print(f"  {Kleur.GROEN}✔ Neural Pathways: Geimporteerd (Strategist, Tribunal, VoidWalker){Kleur.RESET}")
            print(f"  {Kleur.GROEN}✔ NeuralBus: Actief (Event Bus online){Kleur.RESET}")

        except ImportError as e:
            print(f"  {Kleur.ROOD}❌ Neural Link Error: {e}{Kleur.RESET}")
            self.errors += 1

        # TheCortex — Knowledge Graph
        try:
            _real_stdout = sys.stdout
            _devnull = open(os.devnull, "w", encoding="utf-8")
            sys.stdout = _devnull
            try:
                from danny_toolkit.brain import TheCortex
                cortex = TheCortex()
                stats = cortex.get_stats()
            finally:
                sys.stdout = _real_stdout
                _devnull.close()
            print(f"  {Kleur.GROEN}✔ TheCortex: Online ({stats.get('db_entities', 0)} entities, {stats.get('db_triples', 0)} triples){Kleur.RESET}")
        except Exception as e:
            print(f"  {Kleur.GEEL}⚠ TheCortex: {e}{Kleur.RESET}")

        # TheOracleEye — Predictive Scaler
        try:
            _real_stdout = sys.stdout
            _devnull = open(os.devnull, "w", encoding="utf-8")
            sys.stdout = _devnull
            try:
                from danny_toolkit.brain import TheOracleEye
                oracle = TheOracleEye()
                peaks = oracle.get_peak_hours()
            finally:
                sys.stdout = _real_stdout
                _devnull.close()
            if peaks:
                peak_str = ", ".join(f"{h:02d}:00" for h in peaks[:3])
                print(f"  {Kleur.GROEN}✔ TheOracleEye: Online (piekuren: {peak_str}){Kleur.RESET}")
            else:
                print(f"  {Kleur.GROEN}✔ TheOracleEye: Online (nog geen patronen){Kleur.RESET}")
        except Exception as e:
            print(f"  {Kleur.GEEL}⚠ TheOracleEye: {e}{Kleur.RESET}")

    def fase_3_optimalisatie(self):
        print(f"\n{Kleur.GEEL}[3/3] MEMORY & CACHE OPTIMALISATIE{Kleur.RESET}")

        # SQLite Vacuum
        if os.path.exists(self.db_path):
            try:
                conn = sqlite3.connect(self.db_path)
                conn.execute("VACUUM")
                conn.close()
                print(f"  {Kleur.GROEN}✔ CorticalStack: Gedefragmenteerd{Kleur.RESET}")
            except Exception as e:
                print(f"  {Kleur.ROOD}❌ CorticalStack optimalisatie gefaald: {e}{Kleur.RESET}")
        else:
            print(f"  {Kleur.MAGENTA}  CorticalStack: Nieuw (nog niet aangemaakt){Kleur.RESET}")

        # Clear Cache
        pycache = os.path.join(self.root_dir, "danny_toolkit", "brain", "__pycache__")
        if os.path.exists(pycache):
            shutil.rmtree(pycache)
            print(f"  {Kleur.GROEN}✔ Synaptic Cache: Geklaard (frisse start){Kleur.RESET}")

    def launch_omega(self):
        self.clear_screen()
        # Hand over process control to main_omega.py
        print(f"{Kleur.CYAAN}Handing over control to OMEGA CORE...{Kleur.RESET}")
        time.sleep(1)

        # Uitvoeren als subprocess in dezelfde terminal
        subprocess.run([sys.executable, "-m", "danny_toolkit.main_omega"], cwd=self.root_dir)

    def clear_screen(self):
        os.system('cls' if os.name == 'nt' else 'clear')

if __name__ == "__main__":
    ignition = OmegaIgnition()
    asyncio.run(ignition.boot_sequence())
