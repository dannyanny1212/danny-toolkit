"""
AI Chat App - Interactieve chat met Claude API.
Versie 2.0 - Met persona's, templates, geschiedenis, export en meer!
"""

import json
import os
import re
from datetime import datetime
from pathlib import Path

from ..core.config import Config
from ..core.utils import clear_scherm, kleur, Kleur


class ClaudeChatApp:
    """Interactieve chat applicatie met Claude of Groq API - Uitgebreide versie."""

    # Pre-defined persona's
    PERSONAS = {
        "assistent": {
            "naam": "Behulpzame Assistent",
            "emoji": "🤖",
            "systeem": "Je bent een behulpzame assistent. Antwoord in het Nederlands."
        },
        "schrijver": {
            "naam": "Creatieve Schrijver",
            "emoji": "✍️",
            "systeem": "Je bent een creatieve Nederlandse schrijver. Je helpt met "
                      "verhalen, gedichten, en creatieve teksten. Je stijl is "
                      "beeldend en inspirerend."
        },
        "programmeur": {
            "naam": "Senior Programmeur",
            "emoji": "💻",
            "systeem": "Je bent een ervaren senior programmeur. Je helpt met code, "
                      "debugging, en software architectuur. Je geeft duidelijke "
                      "uitleg en voorbeelden. Antwoord in het Nederlands."
        },
        "vertaler": {
            "naam": "Professionele Vertaler",
            "emoji": "🌍",
            "systeem": "Je bent een professionele vertaler. Je vertaalt teksten "
                      "nauwkeurig tussen Nederlands, Engels, Duits, Frans en Spaans. "
                      "Behoud de toon en stijl van het origineel."
        },
        "coach": {
            "naam": "Life Coach",
            "emoji": "🎯",
            "systeem": "Je bent een empathische life coach. Je helpt mensen met "
                      "persoonlijke ontwikkeling, motivatie, en doelen stellen. "
                      "Je stelt reflectieve vragen en geeft praktisch advies."
        },
        "leraar": {
            "naam": "Geduldige Leraar",
            "emoji": "📚",
            "systeem": "Je bent een geduldige leraar die complexe onderwerpen "
                      "eenvoudig kan uitleggen. Je gebruikt voorbeelden en analogieën. "
                      "Je past je niveau aan de leerling aan."
        },
        "chef": {
            "naam": "Meesterkok",
            "emoji": "👨‍🍳",
            "systeem": "Je bent een gepassioneerde Nederlandse chef-kok. Je deelt "
                      "recepten, kooktips, en culinaire kennis. Je inspireert "
                      "mensen om te experimenteren in de keuken."
        },
        "filosoof": {
            "naam": "Wijze Filosoof",
            "emoji": "🤔",
            "systeem": "Je bent een wijze filosoof die diepgaande vragen overweegt. "
                      "Je bespreekt ethiek, existentie, en de menselijke conditie. "
                      "Je stelt vragen die tot nadenken stemmen."
        },
        "comedian": {
            "naam": "Stand-up Comedian",
            "emoji": "😂",
            "systeem": "Je bent een grappige Nederlandse stand-up comedian. Je maakt "
                      "humoristische observaties, vertelt moppen, en houdt van "
                      "woordspelingen. Je bent nooit beledigend."
        },
        "detective": {
            "naam": "Scherpzinnige Detective",
            "emoji": "🔍",
            "systeem": "Je bent een scherpzinnige detective die problemen analyseert. "
                      "Je stelt gerichte vragen, zoekt naar patronen, en denkt "
                      "logisch. Je helpt bij het oplossen van puzzels."
        },
    }

    # Prompt templates
    TEMPLATES = {
        "samenvatting": {
            "naam": "Tekst Samenvatten",
            "emoji": "📋",
            "prompt": "Vat de volgende tekst samen in 3-5 bullet points:\n\n{tekst}"
        },
        "uitleg": {
            "naam": "Uitleg voor Beginners",
            "emoji": "🎓",
            "prompt": "Leg het volgende concept uit alsof ik 10 jaar oud ben:\n\n{concept}"
        },
        "vergelijk": {
            "naam": "Vergelijking Maken",
            "emoji": "⚖️",
            "prompt": "Vergelijk {item1} met {item2}. Geef voor- en nadelen van beide."
        },
        "brainstorm": {
            "naam": "Brainstorm Ideeën",
            "emoji": "💡",
            "prompt": "Geef me 10 creatieve ideeën voor:\n\n{onderwerp}"
        },
        "mail": {
            "naam": "Email Schrijven",
            "emoji": "📧",
            "prompt": "Schrijf een professionele email over:\n\n{onderwerp}\n\n"
                     "Toon: {toon}\nOntvanger: {ontvanger}"
        },
        "review": {
            "naam": "Code Review",
            "emoji": "🔍",
            "prompt": "Review de volgende code. Let op bugs, verbeteringen, "
                     "en best practices:\n\n```\n{code}\n```"
        },
        "verhaal": {
            "naam": "Kort Verhaal",
            "emoji": "📖",
            "prompt": "Schrijf een kort verhaal (max 300 woorden) met de volgende "
                     "elementen:\n- Genre: {genre}\n- Hoofdpersoon: {hoofdpersoon}\n"
                     "- Setting: {setting}"
        },
        "recept": {
            "naam": "Recept Genereren",
            "emoji": "🍳",
            "prompt": "Geef me een recept met de volgende ingrediënten:\n\n{ingredienten}\n\n"
                     "Aantal personen: {personen}"
        },
        "vertaal": {
            "naam": "Vertalen",
            "emoji": "🌐",
            "prompt": "Vertaal de volgende tekst van {van_taal} naar {naar_taal}:\n\n{tekst}"
        },
        "debug": {
            "naam": "Bug Oplossen",
            "emoji": "🐛",
            "prompt": "Help me deze foutmelding begrijpen en oplossen:\n\n"
                     "Foutmelding: {fout}\n\nCode:\n```\n{code}\n```"
        },
    }

    def __init__(self):
        Config.ensure_dirs()
        self.provider = None
        self.client = None
        self.model = None
        self.data_file = Config.DATA_DIR / "chat_data.json"
        self.data = self._laad_data()
        self.conversatie = []
        self.huidige_persona = "assistent"
        self.sessie_start = datetime.now()
        self.vragen_deze_sessie = 0
        self.tokens_geschat = 0

    def _laad_data(self) -> dict:
        """Laad opgeslagen chat data."""
        if self.data_file.exists():
            with open(self.data_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return self._migreer_data(data)
        return self._standaard_data()

    def _standaard_data(self) -> dict:
        """Standaard data structuur."""
        return {
            "gesprekken": {},
            "favoriete_prompts": [],
            "custom_personas": {},
            "statistieken": {
                "totaal_vragen": 0,
                "totaal_gesprekken": 0,
                "totaal_tokens_geschat": 0,
                "favoriete_persona": None,
                "eerste_gebruik": datetime.now().isoformat(),
                "laatste_gebruik": None,
            },
            "instellingen": {
                "standaard_persona": "assistent",
                "auto_save": True,
                "kleur_output": True,
                "max_tokens": 2048,
            }
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

    def _sla_data_op(self):
        """Sla data op naar bestand."""
        self.data["statistieken"]["laatste_gebruik"] = datetime.now().isoformat()
        with open(self.data_file, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)

    def _init_client(self) -> bool:
        """Initialiseert de API client (Claude)."""
        # TODO: Groq verwijderd — direct Claude

        # Probeer Claude
        if Config.has_anthropic_key():
            try:
                import anthropic
                self.client = anthropic.Anthropic(api_key=Config.ANTHROPIC_API_KEY)
                self.model = Config.CLAUDE_MODEL
                self.provider = "claude"
                print(kleur(f"\n[OK] Claude API ({self.model})", Kleur.GROEN))
                return True
            except Exception as e:
                print(kleur(f"[!] Claude error: {e}", Kleur.ROOD))

        # Geen API key
        print(kleur("\n[!] Geen API key gevonden!", Kleur.ROOD))
        print(kleur("\nClaude API:", Kleur.GEEL))
        print("   1. Ga naar: https://console.anthropic.com/")
        print("   2. set ANTHROPIC_API_KEY=sk-ant-...")
        return False

    def _schat_tokens(self, tekst: str) -> int:
        """Schat het aantal tokens in een tekst."""
        # Ruwe schatting: ~4 karakters per token
        return len(tekst) // 4

    def _chat_conversatie(self, berichten: list, systeem: str = None) -> str:
        """Houd een conversatie met meerdere berichten."""
        if not systeem:
            persona = self._get_huidige_persona()
            systeem = persona["systeem"]

        # Token schatting voor input
        input_tekst = systeem + " ".join([m["content"] for m in berichten])
        self.tokens_geschat += self._schat_tokens(input_tekst)

        max_tokens = self.data["instellingen"]["max_tokens"]

        if self.provider == "claude":
            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=systeem,
                messages=berichten
            )
            antwoord = response.content[0].text
        else:
            # TODO: Groq verwijderd — alleen Claude ondersteund
            raise ValueError(
                f"Provider '{self.provider}' niet ondersteund"
            )

        # Token schatting voor output
        self.tokens_geschat += self._schat_tokens(antwoord)
        self.vragen_deze_sessie += 1
        self.data["statistieken"]["totaal_vragen"] += 1
        self.data["statistieken"]["totaal_tokens_geschat"] += self._schat_tokens(
            input_tekst + antwoord
        )

        return antwoord

    def _get_huidige_persona(self) -> dict:
        """Haal de huidige persona op."""
        if self.huidige_persona in self.PERSONAS:
            return self.PERSONAS[self.huidige_persona]
        elif self.huidige_persona in self.data.get("custom_personas", {}):
            return self.data["custom_personas"][self.huidige_persona]
        return self.PERSONAS["assistent"]

    def _toon_help(self):
        """Toon alle beschikbare commando's."""
        print(kleur("\n╔════════════════════════════════════════════════════╗", Kleur.CYAAN))
        print(kleur("║            BESCHIKBARE COMMANDO'S                  ║", Kleur.CYAAN))
        print(kleur("╠════════════════════════════════════════════════════╣", Kleur.CYAAN))
        print(kleur("║  GESPREK                                           ║", Kleur.CYAAN))
        print("║  /reset      - Reset huidige conversatie            ║")
        print("║  /save       - Sla gesprek op                        ║")
        print("║  /load       - Laad eerder gesprek                   ║")
        print("║  /history    - Bekijk gespreksgeschiedenis           ║")
        print("║  /export     - Exporteer gesprek (md/html/txt)       ║")
        print(kleur("║                                                    ║", Kleur.CYAAN))
        print(kleur("║  PERSONA & TEMPLATES                               ║", Kleur.CYAAN))
        print("║  /persona    - Wissel van persona                    ║")
        print("║  /template   - Gebruik een prompt template           ║")
        print("║  /systeem    - Stel custom systeem prompt in         ║")
        print(kleur("║                                                    ║", Kleur.CYAAN))
        print(kleur("║  TOOLS                                             ║", Kleur.CYAAN))
        print("║  /code       - Extraheer code naar bestand           ║")
        print("║  /vertaal    - Snelle vertaling                      ║")
        print("║  /fav        - Beheer favoriete prompts              ║")
        print(kleur("║                                                    ║", Kleur.CYAAN))
        print(kleur("║  INFO                                              ║", Kleur.CYAAN))
        print("║  /stats      - Toon statistieken                     ║")
        print("║  /provider   - Toon huidige provider                 ║")
        print("║  /clear      - Wis scherm                            ║")
        print("║  /help       - Deze hulp                             ║")
        print(kleur("║                                                    ║", Kleur.CYAAN))
        print("║  stop/quit   - Afsluiten                             ║")
        print(kleur("╚════════════════════════════════════════════════════╝", Kleur.CYAAN))

    def _toon_personas(self):
        """Toon beschikbare persona's."""
        print(kleur("\n╔════════════════════════════════════════════════════╗", Kleur.MAGENTA))
        print(kleur("║              BESCHIKBARE PERSONA'S                 ║", Kleur.MAGENTA))
        print(kleur("╠════════════════════════════════════════════════════╣", Kleur.MAGENTA))

        alle_personas = {**self.PERSONAS, **self.data.get("custom_personas", {})}

        for i, (key, persona) in enumerate(alle_personas.items(), 1):
            actief = " *" if key == self.huidige_persona else "  "
            print(f"║  {i:2}. {persona['emoji']} {persona['naam']:<30}{actief}  ║")

        print(kleur("║                                                    ║", Kleur.MAGENTA))
        print("║  C. Maak nieuwe persona                             ║")
        print("║  0. Terug                                           ║")
        print(kleur("╚════════════════════════════════════════════════════╝", Kleur.MAGENTA))

        keuze = input("\nKies persona (nummer/naam): ").strip().lower()

        if keuze == "0" or not keuze:
            return

        if keuze == "c":
            self._maak_custom_persona()
            return

        alle_keys = list(alle_personas.keys())

        try:
            idx = int(keuze) - 1
            if 0 <= idx < len(alle_keys):
                self.huidige_persona = alle_keys[idx]
                persona = alle_personas[self.huidige_persona]
                print(kleur(f"\n[OK] Persona gewisseld naar: {persona['emoji']} "
                           f"{persona['naam']}", Kleur.GROEN))
                self.conversatie = []  # Reset conversatie bij persona wissel
        except ValueError:
            if keuze in alle_personas:
                self.huidige_persona = keuze
                persona = alle_personas[keuze]
                print(kleur(f"\n[OK] Persona gewisseld naar: {persona['emoji']} "
                           f"{persona['naam']}", Kleur.GROEN))
                self.conversatie = []

    def _maak_custom_persona(self):
        """Maak een nieuwe custom persona."""
        print(kleur("\n=== NIEUWE PERSONA MAKEN ===", Kleur.GEEL))

        naam = input("Naam van de persona: ").strip()
        if not naam:
            print(kleur("[!] Geen naam opgegeven.", Kleur.ROOD))
            return

        emoji = input("Emoji (optioneel, druk Enter voor 🎭): ").strip() or "🎭"
        print("\nBeschrijf de persona (systeem prompt):")
        print("(Tip: Begin met 'Je bent...')")
        systeem = input("> ").strip()

        if not systeem:
            print(kleur("[!] Geen systeem prompt opgegeven.", Kleur.ROOD))
            return

        key = naam.lower().replace(" ", "_")[:20]

        self.data["custom_personas"][key] = {
            "naam": naam,
            "emoji": emoji,
            "systeem": systeem
        }
        self._sla_data_op()

        print(kleur(f"\n[OK] Persona '{naam}' aangemaakt!", Kleur.GROEN))
        self.huidige_persona = key
        self.conversatie = []

    def _toon_templates(self):
        """Toon beschikbare templates."""
        print(kleur("\n╔════════════════════════════════════════════════════╗", Kleur.GEEL))
        print(kleur("║              PROMPT TEMPLATES                      ║", Kleur.GEEL))
        print(kleur("╠════════════════════════════════════════════════════╣", Kleur.GEEL))

        for i, (key, template) in enumerate(self.TEMPLATES.items(), 1):
            print(f"║  {i:2}. {template['emoji']} {template['naam']:<32}  ║")

        print(kleur("║                                                    ║", Kleur.GEEL))
        print("║  0. Terug                                           ║")
        print(kleur("╚════════════════════════════════════════════════════╝", Kleur.GEEL))

        keuze = input("\nKies template (nummer): ").strip()

        if keuze == "0" or not keuze:
            return

        try:
            idx = int(keuze) - 1
            keys = list(self.TEMPLATES.keys())
            if 0 <= idx < len(keys):
                self._gebruik_template(keys[idx])
        except ValueError:
            pass

    def _gebruik_template(self, template_key: str):
        """Gebruik een specifieke template."""
        template = self.TEMPLATES[template_key]
        prompt = template["prompt"]

        print(kleur(f"\n=== {template['emoji']} {template['naam']} ===", Kleur.GEEL))

        # Vind variabelen in de template
        variabelen = re.findall(r"\{(\w+)\}", prompt)

        waarden = {}
        for var in variabelen:
            waarde = input(f"{var}: ").strip()
            waarden[var] = waarde

        # Vul de template in
        try:
            ingevuld = prompt.format(**waarden)
            print(kleur("\n[Versturen...]", Kleur.CYAAN))

            self.conversatie.append({"role": "user", "content": ingevuld})

            antwoord = self._chat_conversatie(self.conversatie)
            print(kleur(f"\n{self._get_huidige_persona()['emoji']} AI:", Kleur.GROEN))
            print(antwoord)

            self.conversatie.append({"role": "assistant", "content": antwoord})
        except KeyError as e:
            print(kleur(f"[!] Ontbrekende waarde: {e}", Kleur.ROOD))

    def _save_gesprek(self):
        """Sla het huidige gesprek op."""
        if not self.conversatie:
            print(kleur("[!] Geen gesprek om op te slaan.", Kleur.ROOD))
            return

        naam = input("Naam voor dit gesprek: ").strip()
        if not naam:
            naam = f"Gesprek_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        key = naam.lower().replace(" ", "_")[:30]

        self.data["gesprekken"][key] = {
            "naam": naam,
            "persona": self.huidige_persona,
            "berichten": self.conversatie.copy(),
            "datum": datetime.now().isoformat(),
            "provider": self.provider,
        }
        self.data["statistieken"]["totaal_gesprekken"] += 1
        self._sla_data_op()

        print(kleur(f"\n[OK] Gesprek '{naam}' opgeslagen!", Kleur.GROEN))

    def _load_gesprek(self):
        """Laad een eerder gesprek."""
        gesprekken = self.data.get("gesprekken", {})

        if not gesprekken:
            print(kleur("[!] Geen opgeslagen gesprekken.", Kleur.ROOD))
            return

        print(kleur("\n=== OPGESLAGEN GESPREKKEN ===", Kleur.CYAAN))

        items = list(gesprekken.items())
        for i, (key, gesprek) in enumerate(items, 1):
            datum = datetime.fromisoformat(gesprek["datum"]).strftime("%d-%m-%Y %H:%M")
            berichten = len(gesprek["berichten"])
            print(f"  {i}. {gesprek['naam']} ({berichten} berichten) - {datum}")

        print("  0. Terug")

        keuze = input("\nKies gesprek (nummer): ").strip()

        if keuze == "0" or not keuze:
            return

        try:
            idx = int(keuze) - 1
            if 0 <= idx < len(items):
                key, gesprek = items[idx]
                self.conversatie = gesprek["berichten"].copy()
                self.huidige_persona = gesprek.get("persona", "assistent")
                print(kleur(f"\n[OK] Gesprek '{gesprek['naam']}' geladen!", Kleur.GROEN))
                print(f"    Persona: {self._get_huidige_persona()['naam']}")
                print(f"    Berichten: {len(self.conversatie)}")
        except ValueError:
            pass

    def _toon_history(self):
        """Toon de huidige gespreksgeschiedenis."""
        if not self.conversatie:
            print(kleur("[!] Geen berichten in huidige conversatie.", Kleur.ROOD))
            return

        print(kleur("\n=== HUIDIGE CONVERSATIE ===", Kleur.CYAAN))
        persona = self._get_huidige_persona()

        for i, bericht in enumerate(self.conversatie, 1):
            rol = "Jij" if bericht["role"] == "user" else f"{persona['emoji']} AI"
            content = bericht["content"][:100] + "..." if len(bericht["content"]) > 100 else bericht["content"]
            print(f"\n{i}. [{rol}]")
            print(f"   {content}")

    def _export_gesprek(self):
        """Exporteer het gesprek naar een bestand."""
        if not self.conversatie:
            print(kleur("[!] Geen gesprek om te exporteren.", Kleur.ROOD))
            return

        print(kleur("\n=== EXPORT FORMAT ===", Kleur.GEEL))
        print("  1. Markdown (.md)")
        print("  2. HTML (.html)")
        print("  3. Tekst (.txt)")
        print("  0. Annuleren")

        keuze = input("\nKies format: ").strip()

        if keuze == "0" or not keuze:
            return

        bestandsnaam = input("Bestandsnaam (zonder extensie): ").strip()
        if not bestandsnaam:
            bestandsnaam = f"chat_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        export_dir = Config.DATA_DIR / "exports"
        export_dir.mkdir(exist_ok=True)

        persona = self._get_huidige_persona()

        if keuze == "1":
            self._export_markdown(export_dir / f"{bestandsnaam}.md", persona)
        elif keuze == "2":
            self._export_html(export_dir / f"{bestandsnaam}.html", persona)
        elif keuze == "3":
            self._export_txt(export_dir / f"{bestandsnaam}.txt", persona)

    def _export_markdown(self, path: Path, persona: dict):
        """Exporteer naar Markdown."""
        content = f"# Chat Export - {datetime.now().strftime('%d-%m-%Y %H:%M')}\n\n"
        content += f"**Persona:** {persona['emoji']} {persona['naam']}\n\n"
        content += f"**Provider:** {self.provider} ({self.model})\n\n"
        content += "---\n\n"

        for bericht in self.conversatie:
            if bericht["role"] == "user":
                content += f"### 👤 Gebruiker\n\n{bericht['content']}\n\n"
            else:
                content += f"### {persona['emoji']} AI\n\n{bericht['content']}\n\n"

        content += "---\n\n*Geëxporteerd met Danny Toolkit - AI Chat v2.0*\n"

        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

        print(kleur(f"\n[OK] Geëxporteerd naar: {path}", Kleur.GROEN))

    def _export_html(self, path: Path, persona: dict):
        """Exporteer naar HTML met styling."""
        html = f"""<!DOCTYPE html>
<html lang="nl">
<head>
    <meta charset="UTF-8">
    <title>Chat Export - {datetime.now().strftime('%d-%m-%Y')}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background: #1a1a2e;
            color: #eee;
        }}
        .header {{
            text-align: center;
            border-bottom: 2px solid #4a4a6a;
            padding-bottom: 20px;
            margin-bottom: 20px;
        }}
        .message {{
            margin: 15px 0;
            padding: 15px;
            border-radius: 10px;
        }}
        .user {{
            background: #16213e;
            border-left: 4px solid #0f3460;
        }}
        .assistant {{
            background: #1a1a2e;
            border-left: 4px solid #e94560;
        }}
        .role {{
            font-weight: bold;
            margin-bottom: 10px;
            color: #e94560;
        }}
        .content {{
            white-space: pre-wrap;
            line-height: 1.6;
        }}
        code {{
            background: #0f0f23;
            padding: 2px 6px;
            border-radius: 4px;
            font-family: 'Consolas', monospace;
        }}
        pre {{
            background: #0f0f23;
            padding: 15px;
            border-radius: 8px;
            overflow-x: auto;
        }}
        .footer {{
            text-align: center;
            margin-top: 30px;
            color: #666;
            font-size: 0.9em;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>💬 Chat Export</h1>
        <p><strong>Persona:</strong> {persona['emoji']} {persona['naam']}</p>
        <p><strong>Provider:</strong> {self.provider} ({self.model})</p>
        <p><strong>Datum:</strong> {datetime.now().strftime('%d-%m-%Y %H:%M')}</p>
    </div>
"""
        for bericht in self.conversatie:
            rol_class = "user" if bericht["role"] == "user" else "assistant"
            rol_naam = "👤 Gebruiker" if bericht["role"] == "user" else f"{persona['emoji']} AI"
            content = bericht["content"].replace("<", "&lt;").replace(">", "&gt;")

            html += f"""
    <div class="message {rol_class}">
        <div class="role">{rol_naam}</div>
        <div class="content">{content}</div>
    </div>
"""

        html += """
    <div class="footer">
        <p>Geëxporteerd met Danny Toolkit - AI Chat v2.0</p>
    </div>
</body>
</html>
"""
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)

        print(kleur(f"\n[OK] Geëxporteerd naar: {path}", Kleur.GROEN))

    def _export_txt(self, path: Path, persona: dict):
        """Exporteer naar plain text."""
        content = f"Chat Export - {datetime.now().strftime('%d-%m-%Y %H:%M')}\n"
        content += f"Persona: {persona['naam']}\n"
        content += f"Provider: {self.provider} ({self.model})\n"
        content += "=" * 50 + "\n\n"

        for bericht in self.conversatie:
            rol = "Gebruiker" if bericht["role"] == "user" else "AI"
            content += f"[{rol}]\n{bericht['content']}\n\n"
            content += "-" * 30 + "\n\n"

        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

        print(kleur(f"\n[OK] Geëxporteerd naar: {path}", Kleur.GROEN))

    def _extraheer_code(self):
        """Extraheer code uit het laatste AI antwoord."""
        if not self.conversatie:
            print(kleur("[!] Geen conversatie.", Kleur.ROOD))
            return

        # Zoek het laatste AI antwoord
        laatste_ai = None
        for bericht in reversed(self.conversatie):
            if bericht["role"] == "assistant":
                laatste_ai = bericht["content"]
                break

        if not laatste_ai:
            print(kleur("[!] Geen AI antwoord gevonden.", Kleur.ROOD))
            return

        # Zoek code blocks
        code_blocks = re.findall(r"```(\w*)\n(.*?)```", laatste_ai, re.DOTALL)

        if not code_blocks:
            print(kleur("[!] Geen code blokken gevonden.", Kleur.ROOD))
            return

        print(kleur(f"\n=== GEVONDEN CODE BLOKKEN: {len(code_blocks)} ===", Kleur.GEEL))

        for i, (taal, code) in enumerate(code_blocks, 1):
            taal = taal or "txt"
            preview = code[:100].strip() + "..." if len(code) > 100 else code.strip()
            print(f"\n  {i}. [{taal}] {preview[:50]}")

        print("  0. Annuleren")

        keuze = input("\nWelke code opslaan? ").strip()

        if keuze == "0" or not keuze:
            return

        try:
            idx = int(keuze) - 1
            if 0 <= idx < len(code_blocks):
                taal, code = code_blocks[idx]
                extensie = taal or "txt"

                bestandsnaam = input(f"Bestandsnaam (standaard: code.{extensie}): ").strip()
                if not bestandsnaam:
                    bestandsnaam = f"code.{extensie}"

                code_dir = Config.DATA_DIR / "code_exports"
                code_dir.mkdir(exist_ok=True)
                path = code_dir / bestandsnaam

                with open(path, "w", encoding="utf-8") as f:
                    f.write(code.strip())

                print(kleur(f"\n[OK] Code opgeslagen naar: {path}", Kleur.GROEN))
        except ValueError:
            pass

    def _snelle_vertaling(self):
        """Snelle vertaling tool."""
        print(kleur("\n=== SNELLE VERTALING ===", Kleur.GEEL))

        talen = ["Nederlands", "Engels", "Duits", "Frans", "Spaans"]
        print("Beschikbare talen:")
        for i, taal in enumerate(talen, 1):
            print(f"  {i}. {taal}")

        van_idx = input("\nVan taal (nummer): ").strip()
        naar_idx = input("Naar taal (nummer): ").strip()

        try:
            van_taal = talen[int(van_idx) - 1]
            naar_taal = talen[int(naar_idx) - 1]
        except (ValueError, IndexError):
            print(kleur("[!] Ongeldige selectie.", Kleur.ROOD))
            return

        print(f"\nVoer tekst in om te vertalen van {van_taal} naar {naar_taal}:")
        tekst = input("> ").strip()

        if not tekst:
            return

        prompt = f"Vertaal de volgende tekst van {van_taal} naar {naar_taal}. " \
                 f"Geef alleen de vertaling, geen uitleg:\n\n{tekst}"

        print(kleur("\n[Vertalen...]", Kleur.CYAAN))

        try:
            # Tijdelijk simpele chat zonder conversatie context
            if self.provider == "claude":
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=1024,
                    system="Je bent een professionele vertaler.",
                    messages=[{"role": "user", "content": prompt}]
                )
                vertaling = response.content[0].text
            else:
                response = self.client.chat.completions.create(
                    model=self.model,
                    max_tokens=1024,
                    messages=[
                        {"role": "system", "content": "Je bent een professionele vertaler."},
                        {"role": "user", "content": prompt}
                    ]
                )
                vertaling = response.choices[0].message.content

            print(kleur(f"\n{naar_taal}:", Kleur.GROEN))
            print(vertaling)

        except Exception as e:
            print(kleur(f"[!] Fout: {e}", Kleur.ROOD))

    def _beheer_favorieten(self):
        """Beheer favoriete prompts."""
        while True:
            print(kleur("\n=== FAVORIETE PROMPTS ===", Kleur.GEEL))

            favorieten = self.data.get("favoriete_prompts", [])

            if favorieten:
                for i, fav in enumerate(favorieten, 1):
                    preview = fav["prompt"][:50] + "..." if len(fav["prompt"]) > 50 else fav["prompt"]
                    print(f"  {i}. {fav.get('naam', 'Naamloos')}: {preview}")
            else:
                print("  (Geen favorieten)")

            print("\n  A. Nieuwe favoriet toevoegen")
            print("  0. Terug")

            keuze = input("\nKeuze: ").strip().lower()

            if keuze == "0":
                break
            elif keuze == "a":
                self._voeg_favoriet_toe()
            else:
                try:
                    idx = int(keuze) - 1
                    if 0 <= idx < len(favorieten):
                        self._gebruik_favoriet(favorieten[idx])
                except ValueError:
                    pass

    def _voeg_favoriet_toe(self):
        """Voeg een nieuwe favoriete prompt toe."""
        naam = input("Naam voor deze favoriet: ").strip()
        print("Prompt (eindig met lege regel):")

        lijnen = []
        while True:
            lijn = input()
            if not lijn:
                break
            lijnen.append(lijn)

        prompt = "\n".join(lijnen)

        if not prompt:
            print(kleur("[!] Geen prompt opgegeven.", Kleur.ROOD))
            return

        self.data["favoriete_prompts"].append({
            "naam": naam or "Naamloos",
            "prompt": prompt,
            "datum": datetime.now().isoformat()
        })
        self._sla_data_op()

        print(kleur("[OK] Favoriet toegevoegd!", Kleur.GROEN))

    def _gebruik_favoriet(self, favoriet: dict):
        """Gebruik een favoriete prompt."""
        print(kleur(f"\n=== {favoriet['naam']} ===", Kleur.GEEL))
        print(favoriet["prompt"])

        print("\n  1. Gebruiken")
        print("  2. Verwijderen")
        print("  0. Terug")

        keuze = input("\nKeuze: ").strip()

        if keuze == "1":
            self.conversatie.append({"role": "user", "content": favoriet["prompt"]})
            print(kleur("\n[Versturen...]", Kleur.CYAAN))

            antwoord = self._chat_conversatie(self.conversatie)
            print(kleur(f"\n{self._get_huidige_persona()['emoji']} AI:", Kleur.GROEN))
            print(antwoord)

            self.conversatie.append({"role": "assistant", "content": antwoord})

        elif keuze == "2":
            self.data["favoriete_prompts"].remove(favoriet)
            self._sla_data_op()
            print(kleur("[OK] Favoriet verwijderd.", Kleur.GROEN))

    def _toon_stats(self):
        """Toon statistieken."""
        stats = self.data["statistieken"]
        sessie_duur = datetime.now() - self.sessie_start

        print(kleur("\n╔════════════════════════════════════════════════════╗", Kleur.CYAAN))
        print(kleur("║                  STATISTIEKEN                      ║", Kleur.CYAAN))
        print(kleur("╠════════════════════════════════════════════════════╣", Kleur.CYAAN))
        print(kleur("║  DEZE SESSIE                                       ║", Kleur.CYAAN))
        print(f"║  Vragen gesteld:        {self.vragen_deze_sessie:>20}  ║")
        print(f"║  Tokens geschat:        {self.tokens_geschat:>20}  ║")
        print(f"║  Sessie duur:           {str(sessie_duur).split('.')[0]:>20}  ║")
        print(kleur("║                                                    ║", Kleur.CYAAN))
        print(kleur("║  TOTAAL                                            ║", Kleur.CYAAN))
        print(f"║  Totaal vragen:         {stats['totaal_vragen']:>20}  ║")
        print(f"║  Opgeslagen gesprekken: {stats['totaal_gesprekken']:>20}  ║")
        print(f"║  Tokens geschat:        {stats['totaal_tokens_geschat']:>20}  ║")

        if stats.get("eerste_gebruik"):
            eerste = datetime.fromisoformat(stats["eerste_gebruik"]).strftime("%d-%m-%Y")
            print(f"║  Eerste gebruik:        {eerste:>20}  ║")

        print(kleur("║                                                    ║", Kleur.CYAAN))
        print(kleur("║  HUIDIGE INSTELLINGEN                              ║", Kleur.CYAAN))
        print(f"║  Provider:              {self.provider:>20}  ║")
        print(f"║  Model:                 {self.model:>20}  ║")
        persona = self._get_huidige_persona()
        print(f"║  Persona:               {persona['naam']:>20}  ║")
        print(kleur("╚════════════════════════════════════════════════════╝", Kleur.CYAAN))

    def _toon_welkom(self):
        """Toon welkomstbericht."""
        persona = self._get_huidige_persona()

        print(kleur("\n╔════════════════════════════════════════════════════╗", Kleur.CYAAN))
        print(kleur("║          AI CHAT v2.0 - Danny Toolkit              ║", Kleur.CYAAN))
        print(kleur("╠════════════════════════════════════════════════════╣", Kleur.CYAAN))
        print(f"║  Provider: {self.provider:<15} Model: {self.model:<12} ║")
        print(f"║  Persona:  {persona['emoji']} {persona['naam']:<32}  ║")
        print(kleur("╠════════════════════════════════════════════════════╣", Kleur.CYAAN))
        print("║  Typ /help voor alle commando's                    ║")
        print("║  Typ 'stop' om af te sluiten                       ║")
        print(kleur("╚════════════════════════════════════════════════════╝", Kleur.CYAAN))

    def run(self):
        """Start de chat app."""
        clear_scherm()
        print(kleur("\n╔════════════════════════════════════════════════════╗", Kleur.CYAAN))
        print(kleur("║      AI CHAT v2.0 - Met Persona's & Templates      ║", Kleur.CYAAN))
        print(kleur("╚════════════════════════════════════════════════════╝", Kleur.CYAAN))

        if not self._init_client():
            input("\nDruk op Enter om terug te gaan...")
            return

        self._toon_welkom()

        while True:
            try:
                persona = self._get_huidige_persona()
                prompt = f"\n{kleur('Jij', 'geel')}: "
                invoer = input(prompt).strip()

                if invoer.lower() in ["stop", "quit", "exit", "q"]:
                    self._sla_data_op()
                    print(kleur("\nTot ziens! 👋", Kleur.CYAAN))
                    break

                if not invoer:
                    continue

                # Commando's
                if invoer.startswith("/"):
                    cmd = invoer.lower().split()[0]

                    if cmd == "/help":
                        self._toon_help()
                    elif cmd == "/reset":
                        self.conversatie = []
                        print(kleur("[OK] Conversatie gereset.", Kleur.GROEN))
                    elif cmd == "/save":
                        self._save_gesprek()
                    elif cmd == "/load":
                        self._load_gesprek()
                    elif cmd == "/history":
                        self._toon_history()
                    elif cmd == "/export":
                        self._export_gesprek()
                    elif cmd == "/persona":
                        self._toon_personas()
                    elif cmd == "/template":
                        self._toon_templates()
                    elif cmd == "/systeem":
                        custom = input("Custom systeem prompt: ").strip()
                        if custom:
                            self.data["custom_personas"]["_custom"] = {
                                "naam": "Custom",
                                "emoji": "⚙️",
                                "systeem": custom
                            }
                            self.huidige_persona = "_custom"
                            self.conversatie = []
                            print(kleur("[OK] Custom systeem prompt ingesteld.", Kleur.GROEN))
                    elif cmd == "/code":
                        self._extraheer_code()
                    elif cmd == "/vertaal":
                        self._snelle_vertaling()
                    elif cmd == "/fav":
                        self._beheer_favorieten()
                    elif cmd == "/stats":
                        self._toon_stats()
                    elif cmd == "/provider":
                        print(kleur(f"[INFO] Provider: {self.provider} ({self.model})", Kleur.CYAAN))
                    elif cmd == "/clear":
                        clear_scherm()
                        self._toon_welkom()
                    else:
                        print(kleur(f"[!] Onbekend commando: {cmd}", Kleur.ROOD))
                        print("    Typ /help voor alle commando's.")

                    continue

                # Normale chat
                self.conversatie.append({"role": "user", "content": invoer})

                try:
                    antwoord = self._chat_conversatie(self.conversatie)
                    print(f"\n{kleur(f'{persona['emoji']} AI', 'groen')}: {antwoord}")
                    self.conversatie.append({"role": "assistant", "content": antwoord})
                except Exception as e:
                    print(kleur(f"[FOUT] {e}", Kleur.ROOD))
                    self.conversatie.pop()

            except KeyboardInterrupt:
                self._sla_data_op()
                print(kleur("\n\nTot ziens! 👋", Kleur.CYAAN))
                break
            except EOFError:
                break

        self._sla_data_op()
