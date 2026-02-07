"""
Knowledge Companion - Fusie van Production RAG met Virtueel Huisdier.

Het huisdier "groeit" door kennis te consumeren. Documenten zijn voedsel,
queries zijn training, en het huisdier ontwikkelt een unieke persoonlijkheid
gebaseerd op de opgenomen kennis.

XP Systeem:
- Document Upload: +50 XP per document
- Query gesteld: +10 XP per vraag
- Nieuw feit geleerd: +25 XP
- Dagelijks studeren: +100 XP streak bonus
"""

import json
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from ..core.config import Config
from ..core.utils import clear_scherm, kleur, Kleur
from ..core.vector_store import VectorStore
from ..core.embeddings import get_embedder
from ..core.document_processor import DocumentProcessor
from ..core.generator import Generator


# ============================================================================
# COMPANION PERSONAS - Hoe de companion reageert gebaseerd op kennis
# ============================================================================
COMPANION_PERSONAS = {
    "baby": {
        "naam": "Curious Spark",
        "emoji": "[SPARK]",
        "stijl": "nieuwsgierig en enthousiast maar onwetend",
        "voorvoegsel": ["Ooh!", "Wauw!", "Huh?"],
        "min_docs": 0,
        "min_xp": 0,
    },
    "leerling": {
        "naam": "Knowledge Seeker",
        "emoji": "[SEEKER]",
        "stijl": "leergierig en groeiend in wijsheid",
        "voorvoegsel": ["Ik begin te begrijpen...", "Interessant!", "Laat me denken..."],
        "min_docs": 5,
        "min_xp": 500,
    },
    "student": {
        "naam": "Wisdom Walker",
        "emoji": "[WALKER]",
        "stijl": "bedachtzaam met groeiende expertise",
        "voorvoegsel": ["Gebaseerd op wat ik geleerd heb...", "Dit herinnert me aan...", "In mijn kennis..."],
        "min_docs": 15,
        "min_xp": 2000,
    },
    "geleerde": {
        "naam": "Knowledge Keeper",
        "emoji": "[KEEPER]",
        "stijl": "wijs en verbindend tussen concepten",
        "voorvoegsel": ["Mijn verzamelde wijsheid zegt...", "Ik synthetiseer...", "De patronen tonen..."],
        "min_docs": 30,
        "min_xp": 5000,
    },
    "meester": {
        "naam": "Omniscient Oracle",
        "emoji": "[ORACLE]",
        "stijl": "alwetend, diepzinnig, transcendent",
        "voorvoegsel": ["De kennisrivier stroomt...", "Ik heb gezien...", "In de diepte van begrip..."],
        "min_docs": 50,
        "min_xp": 15000,
    },
}

# XP Rewards
XP_REWARDS = {
    "document_upload": 50,
    "query_gesteld": 10,
    "nieuw_feit": 25,
    "dagelijkse_studie": 100,
    "synthese_gemaakt": 75,
    "url_geindexeerd": 40,
    "perfect_recall": 50,  # Als het antwoord zeer relevant was
}


class KnowledgeCompanion:
    """
    Een AI Companion die groeit door kennis te consumeren.

    Combineert:
    - VectorStore (RAG) voor kennisopslag
    - Gamification (XP, levels, achievements)
    - Personality System (evolueert met kennis)
    """

    VERSIE = "1.0.0"

    def __init__(self, naam: str = None):
        Config.ensure_dirs()

        # Data bestanden
        self.data_file = Config.APPS_DATA_DIR / "knowledge_companion.json"
        self.data = self._laad_data()

        # Companion naam
        if naam:
            self.data["naam"] = naam
            self._sla_op()

        print(kleur("\n[INIT] Knowledge Companion laden...", Kleur.CYAAN))

        # Vector Store (eigen database voor companion)
        self.embedder = get_embedder(True)
        companion_db = Config.DATA_DIR / "knowledge_companion_vectors.json"
        self.vector_store = VectorStore(self.embedder, db_file=companion_db)

        # Document processor
        self.processor = DocumentProcessor()

        # Generator voor antwoorden
        self.generator = None
        try:
            if Config.has_groq_key() or Config.has_anthropic_key():
                self.generator = Generator()
                print(kleur(f"   [OK] Generator: {self.generator.provider.upper()}", Kleur.GROEN))
        except Exception as e:
            print(kleur(f"   [!] Generator error: {e}", Kleur.GEEL))

        # Sync stats met vector store
        self.data["stats"]["totaal_docs"] = self.vector_store.count()

        print(kleur(f"   [OK] Companion: {self._get_companion_naam()}", Kleur.GROEN))
        print(kleur(f"   [OK] Level: {self._get_level()}", Kleur.GROEN))
        print(kleur(f"   [OK] Documenten: {self.data['stats']['totaal_docs']}", Kleur.GROEN))

    def _laad_data(self) -> dict:
        """Laad companion data."""
        if self.data_file.exists():
            with open(self.data_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return self._migreer_data(data)
        return self._standaard_data()

    def _standaard_data(self) -> dict:
        """Standaard data voor nieuwe companion."""
        return {
            "naam": "Kennis",
            "xp": 0,
            "level": 1,
            "persona": "baby",
            "stats": {
                "totaal_docs": 0,
                "totaal_queries": 0,
                "totaal_feiten": 0,
                "syntheses": 0,
                "streak_dagen": 0,
                "laatste_studie": None,
            },
            "geschiedenis": [],
            "favoriete_onderwerpen": [],
            "achievements": [],
            "created": datetime.now().isoformat(),
            "laatste_interactie": datetime.now().isoformat(),
        }

    def _migreer_data(self, data: dict) -> dict:
        """Migreer oude data naar nieuw format."""
        defaults = self._standaard_data()
        for key, value in defaults.items():
            if key not in data:
                data[key] = value
            elif isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    if sub_key not in data[key]:
                        data[key][sub_key] = sub_value
        return data

    def _sla_op(self):
        """Sla data op."""
        self.data["laatste_interactie"] = datetime.now().isoformat()
        with open(self.data_file, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)

    # ========================================================================
    # XP & LEVEL SYSTEEM
    # ========================================================================

    def _geef_xp(self, actie: str, bonus: int = 0) -> int:
        """Geef XP voor een actie."""
        base_xp = XP_REWARDS.get(actie, 10)
        totaal_xp = base_xp + bonus

        self.data["xp"] += totaal_xp

        # Check voor level up
        oud_level = self.data["level"]
        nieuw_level = self._bereken_level()

        if nieuw_level > oud_level:
            self.data["level"] = nieuw_level
            self._update_persona()
            print(kleur(f"\n  *** LEVEL UP! ***", Kleur.GEEL))
            print(kleur(f"  {self._get_companion_naam()} is nu level {nieuw_level}!", Kleur.GEEL))

            # Achievement check
            if nieuw_level >= 5:
                self._unlock_achievement("level_5")
            if nieuw_level >= 10:
                self._unlock_achievement("level_10")

        self._sla_op()
        return totaal_xp

    def _bereken_level(self) -> int:
        """Bereken level gebaseerd op XP."""
        xp = self.data["xp"]
        # Level formule: sqrt(xp / 100)
        import math
        return max(1, int(math.sqrt(xp / 100)) + 1)

    def _update_persona(self):
        """Update persona gebaseerd op XP en docs."""
        xp = self.data["xp"]
        docs = self.data["stats"]["totaal_docs"]

        # Bepaal hoogste persona waarvoor we kwalificeren
        beste_persona = "baby"
        for key, info in COMPANION_PERSONAS.items():
            if xp >= info["min_xp"] and docs >= info["min_docs"]:
                beste_persona = key

        if beste_persona != self.data["persona"]:
            self.data["persona"] = beste_persona
            print(kleur(f"\n  ** EVOLUTIE! **", Kleur.MAGENTA))
            print(kleur(f"  Je companion is nu: {COMPANION_PERSONAS[beste_persona]['naam']}!", Kleur.MAGENTA))
            self._sla_op()

    def _get_persona(self) -> dict:
        """Haal huidige persona op."""
        return COMPANION_PERSONAS.get(self.data["persona"], COMPANION_PERSONAS["baby"])

    def _get_companion_naam(self) -> str:
        """Haal companion naam op met emoji."""
        persona = self._get_persona()
        return f"{persona['emoji']} {self.data['naam']} de {persona['naam']}"

    def _get_level(self) -> str:
        """Haal level string op."""
        return f"Level {self.data['level']} ({self.data['xp']} XP)"

    # ========================================================================
    # KENNIS VOEDEN (DOCUMENT INDEXEREN)
    # ========================================================================

    def voed(self, bron, tags: list = None) -> dict:
        """
        Voed de companion met kennis (indexeer document).

        Returns:
            dict met resultaten (chunks, xp, etc.)
        """
        print(kleur(f"\n[VOEDEN] {self._get_companion_naam()} consumeert kennis...", Kleur.CYAAN))

        pad = Path(bron) if isinstance(bron, str) else bron
        chunks = []

        if pad.is_file():
            tekst = self.processor.laad_bestand(pad)
            chunks = self.processor.chunk_tekst(tekst, pad.stem)
            print(kleur(f"   [OK] {pad.name} verteerd", Kleur.GROEN))

        elif pad.is_dir():
            chunks = self.processor.verwerk_map(pad)
            print(kleur(f"   [OK] Map {pad.name} verteerd", Kleur.GROEN))

        if not chunks:
            return {"error": "Geen content gevonden", "xp": 0}

        # Voeg toe aan vector store
        self.vector_store.voeg_toe(chunks)

        # Update stats
        self.data["stats"]["totaal_docs"] += 1

        # XP reward
        bonus_xp = len(chunks) * 2  # Bonus voor grotere documenten
        earned_xp = self._geef_xp("document_upload", bonus_xp)

        # Update persona
        self._update_persona()

        # Companion reactie
        persona = self._get_persona()
        reactie = random.choice(persona["voorvoegsel"])
        print(kleur(f"\n  {persona['emoji']} \"{reactie} Mmm, heerlijke kennis!\"", Kleur.MAGENTA))

        self._sla_op()

        return {
            "chunks": len(chunks),
            "xp": earned_xp,
            "nieuw_totaal": self.data["stats"]["totaal_docs"],
            "level": self.data["level"],
        }

    def voed_tekst(self, tekst: str, doc_id: str = "document", tags: list = None) -> dict:
        """Voed met directe tekst."""
        chunks = self.processor.chunk_tekst(tekst, doc_id)
        self.vector_store.voeg_toe(chunks)

        self.data["stats"]["totaal_docs"] += 1
        earned_xp = self._geef_xp("document_upload")
        self._update_persona()
        self._sla_op()

        return {"chunks": len(chunks), "xp": earned_xp}

    def voed_url(self, url: str, tags: list = None) -> dict:
        """Voed met URL content."""
        print(kleur(f"\n[URL] {self._get_companion_naam()} verkent het web...", Kleur.CYAAN))

        try:
            import urllib.request
            import re

            with urllib.request.urlopen(url, timeout=10) as response:
                html = response.read().decode("utf-8")

            # Strip HTML
            tekst = re.sub(r'<script[\s\S]*?</script>', '', html)
            tekst = re.sub(r'<style[\s\S]*?</style>', '', tekst)
            tekst = re.sub(r'<[^>]+>', ' ', tekst)
            tekst = re.sub(r'\s+', ' ', tekst).strip()

            if len(tekst) < 100:
                return {"error": "Te weinig content", "xp": 0}

            doc_id = url.split("/")[-1][:30] or "web_page"
            result = self.voed_tekst(tekst, doc_id, tags)

            # Extra XP voor URL
            extra_xp = self._geef_xp("url_geindexeerd")
            result["xp"] += extra_xp

            return result

        except Exception as e:
            return {"error": str(e), "xp": 0}

    # ========================================================================
    # PERSONA-RAG: VRAAG STELLEN
    # ========================================================================

    def vraag(self, vraag: str) -> str:
        """
        Stel een vraag aan de Knowledge Companion.

        Het antwoord wordt gekleurd door de persona van de companion.
        """
        persona = self._get_persona()
        naam = self.data["naam"]

        print(kleur(f"\n[ZOEKEN] {persona['emoji']} doorzoekt geheugen...", Kleur.CYAAN))

        # Zoek in vector store
        resultaten = self.vector_store.zoek(vraag)

        if not resultaten:
            self._geef_xp("query_gesteld")
            self._sla_op()

            return f"{random.choice(persona['voorvoegsel'])} Ik heb hier nog geen kennis over. " \
                   f"Voed me met relevante documenten!"

        # XP voor query
        self._geef_xp("query_gesteld")
        self.data["stats"]["totaal_queries"] += 1

        # Genereer Persona-RAG antwoord
        antwoord = self._genereer_persona_antwoord(vraag, resultaten, persona)

        # Sla vraag op in geschiedenis
        self.data["geschiedenis"].append({
            "vraag": vraag,
            "resultaten": len(resultaten),
            "datum": datetime.now().isoformat(),
        })

        # Beperk geschiedenis
        if len(self.data["geschiedenis"]) > 100:
            self.data["geschiedenis"] = self.data["geschiedenis"][-100:]

        self._sla_op()

        return antwoord

    def _genereer_persona_antwoord(self, vraag: str, resultaten: list, persona: dict) -> str:
        """Genereer antwoord met persona-karakteristieken."""

        # Bouw context
        context_tekst = "\n\n".join([r["tekst"] for r in resultaten[:5]])

        if self.generator:
            # Persona-RAG prompt
            system_prompt = f"""Je bent {self.data['naam']}, een Knowledge Companion met de volgende eigenschappen:

PERSONA: {persona['naam']}
STIJL: {persona['stijl']}
NIVEAU: Level {self.data['level']} ({self.data['xp']} XP)
KENNIS BASIS: {self.data['stats']['totaal_docs']} documenten geconsumeerd

INSTRUCTIES:
- Begin je antwoord met een passende opener uit: {persona['voorvoegsel']}
- Geef antwoorden in de stijl van je persona
- Baseer je antwoord ALLEEN op de gegeven context
- Als de context niet genoeg info bevat, zeg dat eerlijk
- Wees behulpzaam maar blijf in karakter

CONTEXT UIT KENNISBANK:
{context_tekst}"""

            try:
                # Gebruik chat methode met custom system prompt
                berichten = [{"role": "user", "content": vraag}]
                antwoord = self.generator.chat(berichten, systeem=system_prompt)
                return antwoord
            except Exception as e:
                pass

        # Fallback: eenvoudig antwoord zonder AI
        voorvoegsel = random.choice(persona["voorvoegsel"])
        bronnen = [r["metadata"].get("bron", "?") for r in resultaten[:3]]

        antwoord = f"{voorvoegsel}\n\n"
        antwoord += f"Uit mijn geheugen ({', '.join(bronnen)}):\n\n"
        antwoord += context_tekst[:800]
        if len(context_tekst) > 800:
            antwoord += "..."

        return antwoord

    # ========================================================================
    # SYNTHESE: KENNIS COMBINEREN
    # ========================================================================

    def synthetiseer(self, onderwerp: str) -> str:
        """
        Combineer kennis over een onderwerp tot nieuwe inzichten.

        Dit is een speciale actie die meerdere documenten combineert.
        """
        persona = self._get_persona()

        print(kleur(f"\n[SYNTHESE] {persona['emoji']} synthetiseert kennis...", Kleur.MAGENTA))

        # Zoek meerdere relevante chunks
        resultaten = self.vector_store.zoek(onderwerp, top_k=10)

        if len(resultaten) < 3:
            return f"{random.choice(persona['voorvoegsel'])} " \
                   f"Ik heb niet genoeg kennis om te synthetiseren. " \
                   f"Voed me met meer documenten over '{onderwerp}'!"

        # XP voor synthese
        self._geef_xp("synthese_gemaakt")
        self.data["stats"]["syntheses"] += 1

        if self.generator:
            context = "\n\n---\n\n".join([r["tekst"] for r in resultaten])

            system_prompt = f"""Je bent {self.data['naam']}, een Knowledge Companion.

TAAK: Synthetiseer de volgende informatiebronnen tot een coherent nieuw inzicht.

REGELS:
- Combineer de informatie tot iets nieuws
- Zoek patronen en verbanden
- Presenteer het als een "synthese" of "nieuw inzicht"
- Gebruik de stijl: {persona['stijl']}
- Begin met: "{random.choice(persona['voorvoegsel'])}"

BRONNEN OM TE SYNTHETISEREN:
{context}"""

            try:
                # Gebruik chat methode met custom system prompt
                berichten = [{"role": "user", "content": f"Synthetiseer kennis over: {onderwerp}"}]
                synthese = self.generator.chat(berichten, systeem=system_prompt)

                self._sla_op()
                return synthese
            except Exception:
                pass

        # Fallback
        self._sla_op()
        bronnen = set(r["metadata"].get("bron", "?") for r in resultaten)
        return f"{random.choice(persona['voorvoegsel'])} " \
               f"Synthese uit {len(bronnen)} bronnen over '{onderwerp}' is complex. " \
               f"Voeg een AI generator toe voor diepere synthese!"

    # ========================================================================
    # ACHIEVEMENTS
    # ========================================================================

    def _unlock_achievement(self, key: str):
        """Unlock een achievement."""
        if key not in self.data["achievements"]:
            self.data["achievements"].append(key)
            print(kleur(f"\n  [ACHIEVEMENT] UNLOCKED: {key}!", Kleur.GEEL))
            self._sla_op()

    # ========================================================================
    # STATUS & STATS
    # ========================================================================

    def status(self) -> dict:
        """Haal volledige status op."""
        persona = self._get_persona()

        return {
            "naam": self._get_companion_naam(),
            "persona": persona["naam"],
            "level": self.data["level"],
            "xp": self.data["xp"],
            "xp_tot_volgende": (self.data["level"] ** 2) * 100,
            "documenten": self.data["stats"]["totaal_docs"],
            "queries": self.data["stats"]["totaal_queries"],
            "syntheses": self.data["stats"]["syntheses"],
            "achievements": len(self.data["achievements"]),
        }

    def toon_status(self):
        """Print formatted status."""
        status = self.status()
        persona = self._get_persona()

        print(kleur("\n" + "=" * 50, Kleur.CYAAN))
        print(kleur(f"  {status['naam']}", Kleur.CYAAN))
        print(kleur("=" * 50, Kleur.CYAAN))

        print(f"\n  Persona:     {persona['emoji']} {persona['naam']}")
        print(f"  Stijl:       {persona['stijl']}")
        print(f"\n  Level:       {status['level']}")
        print(f"  XP:          {status['xp']} / {status['xp_tot_volgende']}")

        # XP bar
        progress = min(1.0, status['xp'] / status['xp_tot_volgende'])
        bar_len = 30
        filled = int(bar_len * progress)
        bar = "[" + "#" * filled + "-" * (bar_len - filled) + "]"
        print(f"  Progress:    {bar}")

        print(f"\n  Documenten:  {status['documenten']}")
        print(f"  Queries:     {status['queries']}")
        print(f"  Syntheses:   {status['syntheses']}")
        print(f"  Achievements:{status['achievements']}")

        print(kleur("\n" + "=" * 50, Kleur.CYAAN))

    # ========================================================================
    # INTERACTIEVE CLI
    # ========================================================================

    def run(self):
        """Start interactieve modus."""
        clear_scherm()

        print(kleur("""
+===============================================================+
|                                                               |
|     K N O W L E D G E   C O M P A N I O N                     |
|                                                               |
|     Je AI die groeit door kennis te consumeren                |
|                                                               |
+===============================================================+
        """, Kleur.CYAAN))

        self.toon_status()

        print(kleur("\nCOMMANDO'S:", Kleur.GEEL))
        print("  vraag <tekst>     - Stel een vraag")
        print("  voed <pad>        - Voed met document/map")
        print("  url <url>         - Voed met webpagina")
        print("  tekst             - Voed met directe tekst")
        print("  synthese <topic>  - Synthetiseer kennis")
        print("  status            - Toon status")
        print("  help              - Toon alle commando's")
        print("  stop              - Afsluiten")

        while True:
            try:
                persona = self._get_persona()
                prompt = f"\n{persona['emoji']} > "
                invoer = input(kleur(prompt, Kleur.GROEN)).strip()
            except (EOFError, KeyboardInterrupt):
                print(kleur("\n\nTot ziens!", Kleur.CYAAN))
                break

            if not invoer:
                continue

            delen = invoer.split(maxsplit=1)
            cmd = delen[0].lower()
            args = delen[1] if len(delen) > 1 else ""

            if cmd == "stop" or cmd == "exit":
                print(kleur(f"\n{persona['emoji']} Tot ziens! Kom snel terug met meer kennis!", Kleur.CYAAN))
                break

            elif cmd == "vraag" and args:
                antwoord = self.vraag(args)
                print(kleur("\n" + "=" * 50, Kleur.GROEN))
                print(antwoord)
                print(kleur("=" * 50, Kleur.GROEN))

            elif cmd == "voed" and args:
                result = self.voed(args)
                if "error" in result:
                    print(kleur(f"[!] {result['error']}", Kleur.ROOD))
                else:
                    print(kleur(f"\n[OK] {result['chunks']} chunks toegevoegd (+{result['xp']} XP)", Kleur.GROEN))

            elif cmd == "url" and args:
                result = self.voed_url(args)
                if "error" in result:
                    print(kleur(f"[!] {result['error']}", Kleur.ROOD))
                else:
                    print(kleur(f"\n[OK] URL geindexeerd (+{result['xp']} XP)", Kleur.GROEN))

            elif cmd == "tekst":
                print("Voer tekst in (lege regel om te stoppen):")
                lijnen = []
                while True:
                    lijn = input()
                    if not lijn:
                        break
                    lijnen.append(lijn)

                if lijnen:
                    tekst = "\n".join(lijnen)
                    doc_id = input("Document ID: ").strip() or "document"
                    result = self.voed_tekst(tekst, doc_id)
                    print(kleur(f"\n[OK] Tekst toegevoegd (+{result['xp']} XP)", Kleur.GROEN))

            elif cmd == "synthese" and args:
                synthese = self.synthetiseer(args)
                print(kleur("\n" + "=" * 50, Kleur.MAGENTA))
                print(kleur("SYNTHESE:", Kleur.MAGENTA))
                print(synthese)
                print(kleur("=" * 50, Kleur.MAGENTA))

            elif cmd == "status":
                self.toon_status()

            elif cmd == "help":
                print(kleur("\n=== KNOWLEDGE COMPANION HELP ===", Kleur.CYAAN))
                print("\nBASIS COMMANDO'S:")
                print("  vraag <tekst>     - Stel een vraag aan je companion")
                print("  voed <pad>        - Voed met bestand of map")
                print("  url <url>         - Voed met webpagina")
                print("  tekst             - Voed met directe tekst invoer")
                print("  synthese <topic>  - Combineer kennis tot nieuw inzicht")
                print("  status            - Bekijk level, XP, stats")
                print("  stop              - Afsluiten")

                print(kleur("\nXP SYSTEEM:", Kleur.GEEL))
                print("  Document uploaden:  +50 XP")
                print("  Vraag stellen:      +10 XP")
                print("  URL indexeren:      +40 XP")
                print("  Synthese maken:     +75 XP")

                print(kleur("\nPERSONA'S:", Kleur.MAGENTA))
                for key, info in COMPANION_PERSONAS.items():
                    print(f"  {info['emoji']} {info['naam']}")
                    print(f"     Vereist: {info['min_docs']} docs, {info['min_xp']} XP")

            else:
                # Behandel als vraag als geen commando
                if invoer:
                    antwoord = self.vraag(invoer)
                    print(kleur("\n" + "=" * 50, Kleur.GROEN))
                    print(antwoord)
                    print(kleur("=" * 50, Kleur.GROEN))

        self._sla_op()


class KnowledgeCompanionApp:
    """Wrapper class voor launcher en Central Brain compatibiliteit."""

    def __init__(self):
        # Lazy load companion voor performance
        self._companion = None

    @property
    def companion(self):
        """Lazy load de companion."""
        if self._companion is None:
            self._companion = KnowledgeCompanion()
        return self._companion

    def run(self):
        """Start de interactieve Knowledge Companion."""
        self.companion.run()

    # === DELEGATE METHODS VOOR CENTRAL BRAIN ===

    def vraag(self, vraag: str) -> str:
        """Stel een vraag aan de companion."""
        return self.companion.vraag(vraag)

    def voed(self, pad: str) -> dict:
        """Voed de companion met een document."""
        return self.companion.voed(pad)

    def voed_url(self, url: str) -> dict:
        """Voed de companion met een URL."""
        return self.companion.voed_url(url)

    def voed_tekst(self, tekst: str, doc_id: str = "document") -> dict:
        """Voed de companion met tekst."""
        return self.companion.voed_tekst(tekst, doc_id)

    def synthetiseer(self, onderwerp: str) -> str:
        """Synthetiseer kennis over een onderwerp."""
        return self.companion.synthetiseer(onderwerp)

    def status(self) -> dict:
        """Haal de status van de companion op."""
        return self.companion.status()


def main():
    """Start Knowledge Companion."""
    app = KnowledgeCompanionApp()
    app.run()


if __name__ == "__main__":
    main()
