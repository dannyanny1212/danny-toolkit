"""
Project Map — Oracle's Cartografie.

Analyseert de RAG kennisbank (ChromaDB) en rendert een
visuele architectuurkaart van het project. Twee modes:
metadata-only (lichtgewicht) en query-mode (semantisch).
"""

import os
import sys
from pathlib import Path
from collections import defaultdict

if os.name == "nt":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")

from ..core.utils import kleur, Kleur, clear_scherm

# ─── Paden (zelfde als config.py in root) ───
_ROOT = Path(__file__).parent.parent.parent
_CHROMA_DIR = _ROOT / "data" / "rag" / "chromadb"
_COLLECTION_NAME = "danny_knowledge"
_EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"

# ─── Cluster queries voor semantische analyse ───
CLUSTER_QUERIES = {
    "autonomie": "autonome operaties beslissingen",
    "leren": "learning verbeteren patronen feedback",
    "visueel": "visueel dashboard scherm beeld",
    "emotie": "emotie mood gevoel limbisch",
    "beveiliging": "governor bewaker bescherming",
    "kennis": "RAG embeddings zoeken knowledge",
    "actie": "kinetic muis toetsenbord klik automatie uitvoeren",
    "geheugen": "sessie geschiedenis ervaring episodisch herinnering log",
    "wil": "will doel missie intentie autonoom besluit drive motivatie",
}


class ProjectMap:
    """Visuele RAG-gestuurde projectkaart."""

    def __init__(self):
        self._collection = None
        self._query_collection = None
        self._bronnen = None

    # ─── ChromaDB connecties ───

    def _get_collection(self):
        """Metadata-only (lichtgewicht, geen model)."""
        if self._collection is None:
            import chromadb
            client = chromadb.PersistentClient(
                path=str(_CHROMA_DIR)
            )
            self._collection = client.get_collection(
                _COLLECTION_NAME
            )
        return self._collection

    def _get_query_collection(self):
        """Met embedding functie (voor .query())."""
        if self._query_collection is None:
            import chromadb
            from ..core.embeddings import get_chroma_embed_fn

            # Suppress model load spam
            import io as _io
            _old_stdout = sys.stdout
            _old_stderr = sys.stderr
            sys.stdout = _io.StringIO()
            sys.stderr = _io.StringIO()
            try:
                embed_fn = get_chroma_embed_fn()
            finally:
                sys.stdout = _old_stdout
                sys.stderr = _old_stderr

            client = chromadb.PersistentClient(
                path=str(_CHROMA_DIR)
            )
            self._query_collection = (
                client.get_collection(
                    _COLLECTION_NAME,
                    embedding_function=embed_fn,
                )
            )
        return self._query_collection

    # ─── Data verzameling ───

    def _verzamel_bronnen(self):
        """Haal alle metadata op, groepeer per directory."""
        if self._bronnen is not None:
            return self._bronnen

        coll = self._get_collection()
        resultaat = coll.get(
            include=["metadatas"]
        )

        bronnen = defaultdict(
            lambda: {
                "bestanden": defaultdict(int),
                "totaal_chunks": 0,
            }
        )

        for meta in resultaat["metadatas"]:
            # Metadata keys: pad, bron, extensie etc.
            raw_pad = meta.get("pad", "")
            bestandsnaam = meta.get("bron", Path(raw_pad).name)
            pad = Path(raw_pad.replace("\\", "/"))

            # Bepaal directory-groep
            delen = pad.parts
            if "danny_toolkit" in delen:
                idx = delen.index("danny_toolkit")
                if idx + 1 < len(delen):
                    groep = delen[idx + 1] + "/"
                else:
                    groep = "root/"
            elif len(delen) > 1:
                groep = delen[0] + "/"
            else:
                groep = "root/"

            bronnen[groep]["bestanden"][bestandsnaam] += 1
            bronnen[groep]["totaal_chunks"] += 1

        self._bronnen = dict(bronnen)
        return self._bronnen

    # ─── Render methodes ───

    def render_header(self):
        """Toon ASCII header met statistieken."""
        bronnen = self._verzamel_bronnen()
        totaal_chunks = sum(
            g["totaal_chunks"] for g in bronnen.values()
        )
        totaal_bestanden = sum(
            len(g["bestanden"]) for g in bronnen.values()
        )

        breedte = 49
        titel = "PROJECT MAP — Oracle's Cartografie"
        stats = (
            f"{totaal_chunks} chunks | "
            f"{totaal_bestanden} bronbestanden"
        )

        c = Kleur.FEL_CYAAN
        header = (
            f"\n"
            f"{kleur('╔' + '═' * breedte + '╗', c)}\n"
            f"{kleur('║', c)}"
            f"  {titel}"
            f"{' ' * (breedte - 2 - len(titel))}"
            f"{kleur('║', c)}\n"
            f"{kleur('║', c)}"
            f"  {stats}"
            f"{' ' * (breedte - 2 - len(stats))}"
            f"{kleur('║', c)}\n"
            f"{kleur('╚' + '═' * breedte + '╝', c)}"
        )
        print(header)

    def render_boom(self):
        """Toon ASCII directory tree met chunk-aantallen."""
        bronnen = self._verzamel_bronnen()

        print(kleur(
            "\n─── DIRECTORY BOOM ───",
            Kleur.FEL_GEEL,
        ))

        # Sorteer op chunks (meeste eerst)
        gesorteerd = sorted(
            bronnen.items(),
            key=lambda x: x[1]["totaal_chunks"],
            reverse=True,
        )

        print(kleur("  danny_toolkit/", Kleur.FEL_CYAAN))

        for i, (groep, data) in enumerate(gesorteerd):
            is_laatste = i == len(gesorteerd) - 1
            prefix = "└── " if is_laatste else "├── "
            kind_prefix = "    " if is_laatste else "│   "

            chunks = data["totaal_chunks"]
            bestanden = data["bestanden"]
            n_bestanden = len(bestanden)

            print(
                f"  {kleur(prefix, Kleur.DIM)}"
                f"{kleur(groep, Kleur.FEL_CYAAN)}"
                f"{' ' * max(1, 16 - len(groep))}"
                f"{kleur(str(chunks), Kleur.FEL_GROEN)}"
                f" chunks  "
                f"{kleur(f'[{n_bestanden} bestanden]', Kleur.DIM)}"
            )

            # Top 5 bestanden per groep
            top_bestanden = sorted(
                bestanden.items(),
                key=lambda x: x[1],
                reverse=True,
            )[:5]

            for j, (naam, count) in enumerate(
                top_bestanden
            ):
                is_laatste_b = j == len(top_bestanden) - 1
                b_prefix = (
                    "└── " if is_laatste_b else "├── "
                )
                print(
                    f"  {kind_prefix}"
                    f"{kleur(b_prefix, Kleur.DIM)}"
                    f"{naam}"
                    f"{' ' * max(1, 28 - len(naam))}"
                    f"{kleur(f'({count})', Kleur.DIM)}"
                )

            # Toon overige als er meer zijn
            overige = n_bestanden - len(top_bestanden)
            if overige > 0:
                print(
                    f"  {kind_prefix}"
                    f"{kleur(f'    ... +{overige} meer', Kleur.DIM)}"
                )

    def render_domeinen(self):
        """Toon horizontale balk-grafiek per module."""
        bronnen = self._verzamel_bronnen()

        print(kleur(
            "\n─── DOMEIN ANALYSE ───",
            Kleur.FEL_GEEL,
        ))

        totaal = sum(
            g["totaal_chunks"] for g in bronnen.values()
        )
        if totaal == 0:
            print(kleur(
                "  Geen data beschikbaar.",
                Kleur.DIM,
            ))
            return

        # Sorteer op grootte
        gesorteerd = sorted(
            bronnen.items(),
            key=lambda x: x[1]["totaal_chunks"],
            reverse=True,
        )

        balk_breedte = 20
        max_naam = max(len(g) for g, _ in gesorteerd)

        for groep, data in gesorteerd:
            chunks = data["totaal_chunks"]
            percentage = chunks / totaal
            gevuld = int(balk_breedte * percentage)
            leeg = balk_breedte - gevuld

            balk = (
                kleur("█" * gevuld, Kleur.FEL_GROEN)
                + kleur("░" * leeg, Kleur.DIM)
            )

            print(
                f"  {kleur(groep, Kleur.FEL_CYAAN)}"
                f"{' ' * (max_naam - len(groep) + 2)}"
                f"{chunks:>4}  {balk}  "
                f"{kleur(f'{percentage * 100:.0f}%', Kleur.DIM)}"
            )

    def render_clusters(self):
        """Toon semantische clusters via RAG queries."""
        print(kleur(
            "\n─── SEMANTISCHE CLUSTERS ───",
            Kleur.FEL_GEEL,
        ))
        print(kleur(
            "  Embedding model laden...",
            Kleur.DIM,
        ))

        try:
            coll = self._get_query_collection()
        except Exception as e:
            print(kleur(
                f"  Fout bij laden model: {e}",
                Kleur.FEL_ROOD,
            ))
            return

        print(kleur(
            "  Model geladen. Queries draaien...\n",
            Kleur.DIM,
        ))

        for thema, query in CLUSTER_QUERIES.items():
            try:
                resultaat = coll.query(
                    query_texts=[query],
                    n_results=5,
                )

                # Unieke bestanden uit resultaten
                bestanden = []
                gezien = set()
                for meta in resultaat["metadatas"][0]:
                    bron = meta.get("bron", meta.get("pad", ""))
                    naam = Path(bron).name
                    if naam not in gezien:
                        gezien.add(naam)
                        bestanden.append(naam)

                print(
                    f"  {kleur(thema, Kleur.FEL_MAGENTA)}"
                    f"{' ' * (14 - len(thema))}"
                    f"→ {kleur(', '.join(bestanden[:4]), Kleur.CYAAN)}"
                )
            except Exception as e:
                print(
                    f"  {kleur(thema, Kleur.FEL_MAGENTA)}"
                    f"{' ' * (14 - len(thema))}"
                    f"→ {kleur(f'Fout: {e}', Kleur.ROOD)}"
                )

    def zoek(self, query):
        """Zoek in de RAG en toon resultaten."""
        print(kleur(
            f"\n  Zoeken naar: \"{query}\"...",
            Kleur.DIM,
        ))

        try:
            coll = self._get_query_collection()
            resultaat = coll.query(
                query_texts=[query],
                n_results=5,
            )

            print(kleur(
                "\n─── ZOEKRESULTATEN ───",
                Kleur.FEL_GEEL,
            ))

            for i, (doc, meta) in enumerate(zip(
                resultaat["documents"][0],
                resultaat["metadatas"][0],
            )):
                bron = Path(
                    meta.get("bron", meta.get("pad", "?"))
                ).name
                print(
                    f"\n  {kleur(f'[{i + 1}]', Kleur.FEL_GROEN)}"
                    f" {kleur(bron, Kleur.FEL_CYAAN)}"
                )
                # Toon eerste 120 tekens van chunk
                fragment = doc[:120].replace("\n", " ")
                print(
                    f"  {kleur(fragment + '...', Kleur.DIM)}"
                )

        except Exception as e:
            print(kleur(
                f"  Zoekfout: {e}",
                Kleur.FEL_ROOD,
            ))

    def bestand_info(self, naam):
        """Toon info over een specifiek bestand."""
        bronnen = self._verzamel_bronnen()

        gevonden = False
        for groep, data in bronnen.items():
            for bestand, count in data["bestanden"].items():
                if naam.lower() in bestand.lower():
                    gevonden = True
                    print(
                        f"\n  {kleur(bestand, Kleur.FEL_CYAAN)}"
                        f"  ({kleur(groep, Kleur.DIM)})"
                        f"  {kleur(f'{count} chunks', Kleur.FEL_GROEN)}"
                    )

        if not gevonden:
            print(kleur(
                f"\n  Geen bestand gevonden met \"{naam}\".",
                Kleur.DIM,
            ))

    def render(self):
        """Volledige kaart (header + boom + domeinen)."""
        self.render_header()
        self.render_boom()
        self.render_domeinen()

    # ─── Interactieve modus ───

    def run(self):
        """Start interactieve Project Map CLI."""
        clear_scherm()
        print(kleur("""
+===============================================+
|                                               |
|     P R O J E C T   M A P                     |
|                                               |
|     Oracle's Cartografie                      |
|                                               |
+===============================================+
        """, Kleur.FEL_CYAAN))

        try:
            self.render()
        except Exception as e:
            print(kleur(
                f"\n  [FOUT] Kan kaart niet laden: {e}",
                Kleur.FEL_ROOD,
            ))
            print(kleur(
                "  Zorg dat de RAG kennisbank gevuld is"
                " (librarian ingest).",
                Kleur.DIM,
            ))

        print(kleur("\nCOMMANDO'S:", Kleur.GEEL))
        print("  boom        - Directory boom")
        print("  domeinen    - Domein balk-grafiek")
        print("  clusters    - Semantische clusters"
              " (laadt model)")
        print("  zoek <q>    - Zoek in RAG (laadt model)")
        print("  bestand <n> - Info over bestand")
        print("  volledig    - Volledige kaart")
        print("  stop        - Terug naar launcher")

        while True:
            try:
                cmd = input(kleur(
                    "\n[MAP] > ", Kleur.FEL_CYAAN
                )).strip()
                cmd_lower = cmd.lower()

                if not cmd_lower:
                    continue

                if cmd_lower in ["stop", "exit", "quit"]:
                    break
                elif cmd_lower == "boom":
                    self.render_boom()
                elif cmd_lower == "domeinen":
                    self.render_domeinen()
                elif cmd_lower == "clusters":
                    self.render_clusters()
                elif cmd_lower.startswith("zoek"):
                    query = cmd[5:].strip() if len(cmd) > 5 else ""
                    if not query:
                        query = input("  Query: ").strip()
                    if query:
                        self.zoek(query)
                elif cmd_lower.startswith("bestand"):
                    naam = cmd[8:].strip() if len(cmd) > 8 else ""
                    if not naam:
                        naam = input(
                            "  Bestandsnaam: "
                        ).strip()
                    if naam:
                        self.bestand_info(naam)
                elif cmd_lower == "volledig":
                    self.render()
                else:
                    print(
                        f"  Onbekend commando: {cmd}"
                    )

            except (EOFError, KeyboardInterrupt):
                break

        input("\n  Druk op Enter...")
