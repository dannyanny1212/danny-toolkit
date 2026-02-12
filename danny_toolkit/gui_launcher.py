"""
Danny Toolkit GUI Launcher — Tkinter visueel venster.

Start alle 57 apps via knoppen, gegroepeerd per sectie.
Entry point: danny-gui
"""

import subprocess
import sys
import tkinter as tk
from datetime import datetime


# ── Donker thema kleuren ──
BG = "#0d1117"
BG_HEADER = "#161b22"
BG_KNOP = "#21262d"
BG_KNOP_HOVER = "#30363d"
BG_KNOP_ACTIEF = "#0e4429"
BG_KNOP_ACTIEF_HOVER = "#196c2e"
FG = "#c9d1d9"
FG_DIM = "#8b949e"
FG_ACTIEF = "#3fb950"

SECTIE_KLEUREN = {
    "nexus": "#00d4ff",
    "omega": "#d55fde",
    "engineering": "#3fb950",
    "subroutines": "#8b949e",
}

# ── App namen (key -> naam) uit launcher.py ──
APP_NAMEN = {
    "1": "Boodschappenlijst",
    "2": "Slimme Rekenmachine",
    "3": "Virtueel Huisdier",
    "4": "Schatzoek Game",
    "5": "Code Analyse",
    "6": "Mini-RAG Demo",
    "7": "Production RAG",
    "8": "Nieuws Agent",
    "9": "Weer Agent",
    "10": "Claude Chat",
    "11": "Notitie App",
    "12": "Wachtwoord Generator",
    "13": "Pomodoro Timer",
    "14": "Habit Tracker",
    "15": "Expense Tracker",
    "16": "Flashcards",
    "17": "Unit Converter",
    "18": "Agenda Planner",
    "19": "Mood Tracker",
    "20": "Citaten Generator",
    "21": "Vector Data Studio",
    "22": "Goals Tracker",
    "23": "Room Planner",
    "24": "Artificial Life",
    "25": "NLP Studio",
    "26": "Music Composer",
    "27": "Recipe Generator",
    "28": "Fitness Tracker",
    "29": "Dream Journal",
    "30": "Code Snippets",
    "31": "Language Tutor",
    "32": "Decision Maker",
    "33": "Time Capsule",
    "34": "Advanced Questions",
    "35": "ML Studio",
    "36": "Central Brain",
    "37": "Knowledge Companion",
    "38": "Legendary Companion",
    "39": "Digital Daemon",
    "40": "Trinity Symbiosis",
    "41": "Omega AI",
    "42": "Sanctuary Dashboard",
    "43": "Dream Monitor",
    "44": "Nexus Bridge",
    "45": "Visual Nexus",
    "46": "Prometheus Brain",
    "47": "Pulse Protocol",
    "48": "Voice Protocol",
    "49": "Listener Protocol",
    "50": "Dialogue Protocol",
    "51": "Will Protocol",
    "52": "Heartbeat Daemon",
    "53": "Pixel Eye",
    "54": "Project Map",
    "55": "Oracle Agent",
    "56": "Singularity Engine",
    "57": "Security Research",
    "58": "FastAPI Server",
    "59": "Telegram Bot",
}

# ── Sectie definities (volgorde uit launcher.py) ──
SECTIES = {
    "NEXUS PRIME": {
        "kleur": "nexus",
        "keys": [
            "42", "46", "36", "40", "39",
            "43", "44", "45", "53", "54",
            "55", "56", "57", "58", "59",
        ],
    },
    "OMEGA PROTOCOLS": {
        "kleur": "omega",
        "keys": [
            "41", "47", "48", "49", "50", "51", "52",
        ],
    },
    "ENGINEERING DECK": {
        "kleur": "engineering",
        "keys": [
            "5", "6", "7", "8", "9", "10",
            "21", "24", "25", "34", "35", "37", "38",
        ],
    },
    "SUBROUTINES": {
        "kleur": "subroutines",
        "keys": [
            "1", "2", "3", "4",
            "11", "12", "13", "14", "15", "16", "17",
            "18", "19", "20", "22", "23",
            "26", "27", "28", "29", "30", "31", "32", "33",
        ],
    },
}


class ScrollFrame(tk.Frame):
    """Scrollbaar frame via canvas + scrollbar patroon."""

    def __init__(self, parent, **kw):
        super().__init__(parent, bg=BG, **kw)

        self.canvas = tk.Canvas(
            self, bg=BG, highlightthickness=0, bd=0,
        )
        self.scrollbar = tk.Scrollbar(
            self, orient="vertical",
            command=self.canvas.yview,
        )
        self.inner = tk.Frame(self.canvas, bg=BG)

        self.inner.bind(
            "<Configure>",
            lambda e: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")
            ),
        )
        self.canvas_window = self.canvas.create_window(
            (0, 0), window=self.inner, anchor="nw",
        )
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        # Canvas breedte meeschalen
        self.canvas.bind("<Configure>", self._on_canvas_resize)

        # Muiswiel scrollen
        self.inner.bind("<Enter>", self._bind_muiswiel)
        self.inner.bind("<Leave>", self._unbind_muiswiel)

    def _on_canvas_resize(self, event):
        self.canvas.itemconfig(
            self.canvas_window, width=event.width,
        )

    def _bind_muiswiel(self, _event):
        self.canvas.bind_all(
            "<MouseWheel>", self._on_muiswiel,
        )

    def _unbind_muiswiel(self, _event):
        self.canvas.unbind_all("<MouseWheel>")

    def _on_muiswiel(self, event):
        self.canvas.yview_scroll(
            int(-1 * (event.delta / 120)), "units",
        )


class DannyToolkitGUI:
    """Hoofdvenster voor Danny Toolkit GUI."""

    def __init__(self):
        self.root = tk.Tk()
        self.sessie_nr = 1
        self.app_runs = 0
        self.start_tijd = datetime.now()
        self.status_var = tk.StringVar(
            value="Gereed \u2014 Kies een app om te starten"
        )
        # Track actieve processen: key -> Popen object
        self.processen = {}
        # Track knoppen: key -> (Button, originele_kleur)
        self.knoppen = {}

        self._configureer_venster()
        self._bouw_header()

        self.scroll = ScrollFrame(self.root)
        self.scroll.pack(fill="both", expand=True, padx=8)

        self._bouw_secties(self.scroll.inner)
        self._bouw_statusbalk()

        # Poll elke 2 seconden of processen nog draaien
        self._poll_processen()

    def _configureer_venster(self):
        self.root.title(
            "Danny Toolkit v4.0 // COSMIC_OMEGA_V4"
        )
        self.root.configure(bg=BG)
        self.root.geometry("780x700")
        self.root.minsize(600, 400)

        # Icoon (optioneel, faalt graceful)
        try:
            self.root.iconbitmap(default="")
        except tk.TclError:
            pass

    def _bouw_header(self):
        header = tk.Frame(self.root, bg=BG_HEADER, pady=10)
        header.pack(fill="x")

        titel = tk.Label(
            header,
            text="DANNY TOOLKIT v4.0 // COSMIC_OMEGA_V4",
            font=("Consolas", 16, "bold"),
            fg=SECTIE_KLEUREN["nexus"],
            bg=BG_HEADER,
        )
        titel.pack()

        self.stats_label = tk.Label(
            header,
            text=self._stats_tekst(),
            font=("Consolas", 10),
            fg=FG_DIM,
            bg=BG_HEADER,
        )
        self.stats_label.pack(pady=(4, 0))

    def _stats_tekst(self):
        nu = datetime.now().strftime("%H:%M")
        actief = len(self.processen)
        actief_txt = (
            f"  |  {actief} actief" if actief > 0 else ""
        )
        return (
            f"Sessie #{self.sessie_nr}  |  "
            f"{self.app_runs} app runs  |  "
            f"{len(APP_NAMEN)} apps{actief_txt}  |  {nu}"
        )

    def _bouw_secties(self, parent):
        """Bouw 2x2 grid van sectie frames."""
        parent.columnconfigure(0, weight=1, uniform="col")
        parent.columnconfigure(1, weight=1, uniform="col")

        sectie_lijst = list(SECTIES.items())
        posities = [(0, 0), (0, 1), (1, 0), (1, 1)]

        for (naam, info), (rij, kolom) in zip(
            sectie_lijst, posities
        ):
            self._bouw_sectie_frame(
                parent, naam, info, rij, kolom,
            )

    def _bouw_sectie_frame(
        self, parent, naam, info, rij, kolom
    ):
        kleur = SECTIE_KLEUREN[info["kleur"]]
        keys = info["keys"]
        aantal = len(keys)

        frame = tk.LabelFrame(
            parent,
            text=f"  {naam} ({aantal})  ",
            font=("Consolas", 11, "bold"),
            fg=kleur,
            bg=BG,
            bd=1,
            relief="groove",
            labelanchor="n",
        )
        frame.grid(
            row=rij, column=kolom,
            padx=6, pady=6,
            sticky="nsew",
        )
        parent.rowconfigure(rij, weight=1)

        for key in keys:
            naam_app = APP_NAMEN.get(key, f"App {key}")
            self._maak_app_knop(frame, key, naam_app, kleur)

    def _maak_app_knop(self, parent, key, naam, kleur):
        tekst = f"[{key}] {naam}"

        knop = tk.Button(
            parent,
            text=tekst,
            font=("Consolas", 10),
            fg=kleur,
            bg=BG_KNOP,
            activeforeground="#ffffff",
            activebackground=BG_KNOP_HOVER,
            bd=0,
            relief="flat",
            cursor="hand2",
            anchor="w",
            padx=10,
            pady=4,
            command=lambda k=key, n=naam: self._start_app(
                k, n
            ),
        )
        knop.pack(fill="x", padx=4, pady=2)

        # Bewaar knop referentie + originele kleur
        self.knoppen[key] = (knop, kleur)

        # Hover effect (respecteert actieve state)
        knop.bind(
            "<Enter>",
            lambda e, k=key: self._on_hover(k, True),
        )
        knop.bind(
            "<Leave>",
            lambda e, k=key: self._on_hover(k, False),
        )

    def _on_hover(self, key, entering):
        """Hover effect dat actieve state respecteert."""
        knop, _kleur = self.knoppen[key]
        if key in self.processen:
            bg = BG_KNOP_ACTIEF_HOVER if entering else BG_KNOP_ACTIEF
        else:
            bg = BG_KNOP_HOVER if entering else BG_KNOP
        knop.configure(bg=bg)

    def _markeer_actief(self, key):
        """Markeer knop als actief (groen stip + achtergrond)."""
        knop, _kleur = self.knoppen[key]
        naam = APP_NAMEN.get(key, f"App {key}")
        knop.configure(
            text=f"\u25cf [{key}] {naam}",
            fg=FG_ACTIEF,
            bg=BG_KNOP_ACTIEF,
        )

    def _markeer_inactief(self, key):
        """Reset knop naar normale staat."""
        knop, kleur = self.knoppen[key]
        naam = APP_NAMEN.get(key, f"App {key}")
        knop.configure(
            text=f"[{key}] {naam}",
            fg=kleur,
            bg=BG_KNOP,
        )

    def _start_app(self, key, naam):
        """Start app in nieuw cmd venster via subprocess."""
        self.app_runs += 1
        self.stats_label.configure(text=self._stats_tekst())
        self._update_status(f"Starten: {naam}...")

        python_code = (
            "from danny_toolkit.launcher import Launcher;"
            f"Launcher().start_app('{key}')"
        )

        try:
            proc = subprocess.Popen(
                [
                    "cmd", "/c", "start",
                    f"Danny Toolkit - {naam}",
                    "cmd", "/k",
                    sys.executable, "-c", python_code,
                ],
                shell=False,
            )
            self.processen[key] = proc
            self._markeer_actief(key)
            self._update_actief_teller()
            self._update_status(f"Gestart: {naam}")
        except OSError as e:
            self._update_status(f"Fout bij starten: {e}")

    def _bouw_statusbalk(self):
        balk = tk.Frame(self.root, bg=BG_HEADER, pady=6)
        balk.pack(fill="x", side="bottom")

        status = tk.Label(
            balk,
            textvariable=self.status_var,
            font=("Consolas", 9),
            fg=FG_DIM,
            bg=BG_HEADER,
            anchor="w",
        )
        status.pack(side="left", padx=12)

        versie = tk.Label(
            balk,
            text="v4.0",
            font=("Consolas", 9, "bold"),
            fg=SECTIE_KLEUREN["nexus"],
            bg=BG_HEADER,
        )
        versie.pack(side="right", padx=12)

    def _update_status(self, tekst):
        self.status_var.set(tekst)

    def _update_actief_teller(self):
        self.stats_label.configure(text=self._stats_tekst())

    def _poll_processen(self):
        """Check elke 2s welke processen nog draaien."""
        gestopt = []
        for key, proc in self.processen.items():
            if proc.poll() is not None:
                gestopt.append(key)

        for key in gestopt:
            del self.processen[key]
            self._markeer_inactief(key)
            naam = APP_NAMEN.get(key, f"App {key}")
            self._update_status(f"Gestopt: {naam}")

        if gestopt:
            self._update_actief_teller()

        # Herplan volgende poll
        self.root.after(2000, self._poll_processen)

    def run(self):
        self.root.mainloop()


def main():
    """Entry point voor danny-gui commando."""
    app = DannyToolkitGUI()
    app.run()


if __name__ == "__main__":
    main()
