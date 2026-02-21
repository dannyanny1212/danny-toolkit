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

# Forceer de root map in het path zodat modules goed laden
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from danny_toolkit.core.utils import Kleur

class OmegaOptimizer:
    def __init__(self):
        self.root_dir = os.path.dirname(os.path.abspath(__file__))
        self.db_path = os.path.join(self.root_dir, "danny_toolkit", "data", "brain", "cortical_stack.db")
        self.cache_dirs = [
            os.path.join(self.root_dir, "danny_toolkit", "__pycache__"),
            os.path.join(self.root_dir, "danny_toolkit", "brain", "__pycache__"),
            os.path.join(self.root_dir, "danny_toolkit", "core", "__pycache__")
        ]

    def run(self):
        print(f"{Kleur.CYAAN}==================================================")
        print(f" ⚙️  PROJECT OMEGA v6.0 - SYSTEM OPTIMIZER & ANALYST")
        print(f"=================================================={Kleur.RESET}\n")

        self.fase_1_controle()
        self.fase_2_analyse()
        self.fase_3_optimalisatie()

        print(f"\n{Kleur.GROEN}✨ Systeem is Volledig Geoptimaliseerd en Klaar voor Gebruik!{Kleur.RESET}")

    def fase_1_controle(self):
        print(f"{Kleur.GEEL}--- FASE 1: SYSTEEM CONTROLE ---{Kleur.RESET}")

        # 1. Groq API Check
        groq_key = os.getenv("GROQ_API_KEY")
        if groq_key:
            print(f"{Kleur.GROEN}✔ Groq API Key: Aanwezig ({len(groq_key)} chars){Kleur.RESET}")
        else:
            print(f"{Kleur.ROOD}❌ Groq API Key: ONTBREEKT (Check je .env bestand!){Kleur.RESET}")

        # 2. Ollama / GPU Check
        print(f"{Kleur.BLAUW}  > Pinging Ollama (Vision Engine)...{Kleur.RESET}")
        try:
            req = urllib.request.Request("http://localhost:11434/api/tags")
            with urllib.request.urlopen(req, timeout=2) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode())
                    models = [m['name'] for m in data.get('models', [])]
                    if any("llava" in m for m in models):
                        print(f"{Kleur.GROEN}✔ Ollama: Online (Llava is beschikbaar){Kleur.RESET}")
                    else:
                        print(f"{Kleur.GEEL}⚠ Ollama: Online, maar Llava ontbreekt! Run 'ollama pull llava'{Kleur.RESET}")
        except Exception as e:
            logger.debug("Ollama check mislukt: %s", e)
            print(f"{Kleur.ROOD}❌ Ollama: Offline of onbereikbaar.{Kleur.RESET}")

        # 3. VRAM Check via nvidia-smi
        try:
            result = subprocess.run(['nvidia-smi', '--query-gpu=memory.free', '--format=csv,noheader,nounits'], capture_output=True, text=True)
            vram_free = int(result.stdout.strip())
            if vram_free > 2000:
                print(f"{Kleur.GROEN}✔ GPU VRAM: {vram_free} MB Vrij (Gezond){Kleur.RESET}")
            else:
                print(f"{Kleur.ROOD}⚠ GPU VRAM: Slechts {vram_free} MB Vrij! Kans op Out-Of-Memory.{Kleur.RESET}")
        except FileNotFoundError:
             print(f"{Kleur.GEEL}⚠ GPU VRAM: Kon nvidia-smi niet uitvoeren.{Kleur.RESET}")

    def fase_2_analyse(self):
        print(f"\n{Kleur.GEEL}--- FASE 2: DATA & MEMORY ANALYSE ---{Kleur.RESET}")

        # 1. CorticalStack (SQLite) Size
        if os.path.exists(self.db_path):
            size_kb = os.path.getsize(self.db_path) / 1024
            print(f"  > CorticalStack Database: {size_kb:.2f} KB")
            if size_kb > 50000: # 50 MB is quite large for text logs
                print(f"{Kleur.GEEL}  ⚠ Let op: Je CorticalStack wordt erg groot. Optimalisatie nodig.{Kleur.RESET}")
            else:
                print(f"{Kleur.GROEN}✔ CorticalStack grootte is optimaal.{Kleur.RESET}")
        else:
            print(f"{Kleur.MAGENTA}  > CorticalStack: Nog niet aangemaakt (Nieuw systeem){Kleur.RESET}")

    def fase_3_optimalisatie(self):
        print(f"\n{Kleur.GEEL}--- FASE 3: SYSTEEM OPTIMALISATIE ---{Kleur.RESET}")

        # 1. SQLite Vacuum (Defragmentatie)
        if os.path.exists(self.db_path):
            print(f"{Kleur.BLAUW}  > CorticalStack defragmenteren (VACUUM)...{Kleur.RESET}")
            try:
                conn = sqlite3.connect(self.db_path)
                conn.execute("VACUUM")
                conn.close()
                print(f"{Kleur.GROEN}✔ Database geoptimaliseerd.{Kleur.RESET}")
            except Exception as e:
                print(f"{Kleur.ROOD}❌ Vacuum gefaald: {e}{Kleur.RESET}")

        # 2. VRAM Cleanup (Ollama modellen unloaden)
        print(f"{Kleur.BLAUW}  > VRAM flush forceren (Ollama)...{Kleur.RESET}")
        try:
            # Forceer Ollama om actieve modellen uit het geheugen te halen
            req = urllib.request.Request("http://localhost:11434/api/generate", data=json.dumps({"model": "llava", "keep_alive": 0}).encode(), headers={'Content-Type': 'application/json'})
            urllib.request.urlopen(req, timeout=3)
            print(f"{Kleur.GROEN}✔ VRAM succesvol vrijgemaakt.{Kleur.RESET}")
        except Exception as e:
            logger.debug("VRAM flush mislukt: %s", e)
            print(f"{Kleur.MAGENTA}  > VRAM flush overgeslagen (Ollama reageerde niet).{Kleur.RESET}")

        # 3. Python Cache Cleanup
        print(f"{Kleur.BLAUW}  > Oude Python cache opschonen...{Kleur.RESET}")
        cleaned = 0
        for cache_dir in self.cache_dirs:
            if os.path.exists(cache_dir):
                shutil.rmtree(cache_dir)
                cleaned += 1
        print(f"{Kleur.GROEN}✔ {cleaned} Cache mappen verwijderd.{Kleur.RESET}")

if __name__ == "__main__":
    opt = OmegaOptimizer()
    opt.run()
