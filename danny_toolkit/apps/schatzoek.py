"""
Schatzoek Game App v2.0 - Uitgebreide dungeon crawler.

Features:
- Campagne modus met 10 levels
- Monster systeem met bewegende vijanden
- Character classes (Ontdekker, Ninja, Tank)
- Uitgebreid power-up systeem
- Items, muntjes en shop
- Achievements
- Fog of War
- Sleutels en deuren
- Boss fights
- Time Attack modus
- Dagelijkse uitdagingen
- Experience en leveling
"""

import json
import random
import time
from datetime import datetime, date
from pathlib import Path
from ..core.config import Config
from ..core.utils import clear_scherm, kleur, succes, fout, waarschuwing, info


class SchatzoekApp:
    """Schatzoek game v2.0 - Uitgebreide dungeon crawler."""

    VERSIE = "2.0"

    # Character classes
    CLASSES = {
        "ontdekker": {
            "naam": "Ontdekker",
            "emoji": "🧭",
            "hp": 100,
            "zicht": 3,
            "snelheid": 1,
            "special": "Kompas altijd beschikbaar",
            "beschrijving": "Balanced karakter met extra kompas"
        },
        "ninja": {
            "naam": "Ninja",
            "emoji": "🥷",
            "hp": 75,
            "zicht": 4,
            "snelheid": 2,
            "special": "Kan door vallen zonder schade",
            "beschrijving": "Snel en wendig, maar fragiel"
        },
        "tank": {
            "naam": "Tank",
            "emoji": "🛡️",
            "hp": 150,
            "zicht": 2,
            "snelheid": 1,
            "special": "Halve schade van monsters",
            "beschrijving": "Veel HP maar beperkt zicht"
        }
    }

    # Biomes/thema's voor levels
    BIOMES = {
        "bos": {
            "naam": "Mysterieus Bos",
            "emoji": "🌲",
            "muur": "🌳",
            "vloer": "🌿",
            "kleur": "groen"
        },
        "grot": {
            "naam": "Donkere Grot",
            "emoji": "🕳️",
            "muur": "🪨",
            "vloer": "⬛",
            "kleur": "grijs"
        },
        "woestijn": {
            "naam": "Verloren Woestijn",
            "emoji": "🏜️",
            "muur": "🏔️",
            "vloer": "🟨",
            "kleur": "geel"
        },
        "kasteel": {
            "naam": "Verlaten Kasteel",
            "emoji": "🏰",
            "muur": "🧱",
            "vloer": "⬜",
            "kleur": "wit"
        },
        "vulkaan": {
            "naam": "Vuurberg",
            "emoji": "🌋",
            "muur": "🔥",
            "vloer": "🟥",
            "kleur": "rood"
        }
    }

    # Campagne levels
    CAMPAGNE_LEVELS = [
        {"naam": "Het Begin", "biome": "bos", "grid": 5, "schatten": 1,
         "monsters": 0, "boss": False, "verhaal": "Je begint je avontuur in het mysterieuze bos..."},
        {"naam": "Eerste Gevaar", "biome": "bos", "grid": 6, "schatten": 2,
         "monsters": 1, "boss": False, "verhaal": "Er bewegen schaduwen tussen de bomen..."},
        {"naam": "De Grot Ingang", "biome": "grot", "grid": 6, "schatten": 2,
         "monsters": 2, "boss": False, "verhaal": "Je vindt een donkere grot ingang."},
        {"naam": "Dieper de Grot In", "biome": "grot", "grid": 7, "schatten": 3,
         "monsters": 2, "boss": False, "verhaal": "Het wordt steeds donkerder..."},
        {"naam": "De Grot Bewaker", "biome": "grot", "grid": 7, "schatten": 2,
         "monsters": 1, "boss": True, "verhaal": "Een enorm wezen blokkeert de uitgang!"},
        {"naam": "Woestijn Oase", "biome": "woestijn", "grid": 8, "schatten": 3,
         "monsters": 3, "boss": False, "verhaal": "De hitte is ondraaglijk..."},
        {"naam": "Zandstorm", "biome": "woestijn", "grid": 8, "schatten": 4,
         "monsters": 3, "boss": False, "verhaal": "Een zandstorm beperkt je zicht!"},
        {"naam": "Het Oude Kasteel", "biome": "kasteel", "grid": 9, "schatten": 4,
         "monsters": 4, "boss": False, "verhaal": "De muren fluisteren geheimen..."},
        {"naam": "De Troonzaal", "biome": "kasteel", "grid": 9, "schatten": 3,
         "monsters": 3, "boss": False, "verhaal": "Je nadert het hart van het kasteel."},
        {"naam": "De Eindbaas", "biome": "vulkaan", "grid": 10, "schatten": 5,
         "monsters": 2, "boss": True, "verhaal": "De ultieme uitdaging wacht..."}
    ]

    # Moeilijkheden voor vrij spel
    MOEILIJKHEID = {
        "makkelijk": {"grid": 5, "schatten": 2, "muren": 3, "vallen": 1,
                     "powerups": 3, "monsters": 0, "muntjes": 5},
        "normaal": {"grid": 7, "schatten": 3, "muren": 5, "vallen": 2,
                   "powerups": 3, "monsters": 2, "muntjes": 8},
        "moeilijk": {"grid": 9, "schatten": 5, "muren": 8, "vallen": 4,
                    "powerups": 3, "monsters": 4, "muntjes": 10},
        "extreem": {"grid": 12, "schatten": 7, "muren": 15, "vallen": 6,
                   "powerups": 4, "monsters": 6, "muntjes": 15}
    }

    # Power-ups
    POWERUPS = {
        "kompas": {"emoji": "🧭", "beschrijving": "Toont richting naar schat"},
        "radar": {"emoji": "📡", "beschrijving": "Toont afstand tot alle schatten"},
        "teleport": {"emoji": "🌀", "beschrijving": "Teleporteer naar een plek"},
        "schild": {"emoji": "🛡️", "beschrijving": "Blokkeert 1 aanval"},
        "snelheid": {"emoji": "⚡", "beschrijving": "2 stappen per beurt"},
        "bom": {"emoji": "💣", "beschrijving": "Vernietigt muren en monsters"},
        "xray": {"emoji": "👁️", "beschrijving": "Zie door muren"},
        "onzichtbaar": {"emoji": "👻", "beschrijving": "Monsters zien je niet"},
        "gezondheid": {"emoji": "❤️", "beschrijving": "Herstel 25 HP"},
        "sleutel": {"emoji": "🗝️", "beschrijving": "Open een deur"}
    }

    # Monsters
    MONSTERS = {
        "slijm": {"emoji": "🟢", "hp": 20, "schade": 10, "snelheid": 1, "xp": 10},
        "vleermuis": {"emoji": "🦇", "hp": 15, "schade": 15, "snelheid": 2, "xp": 15},
        "skelet": {"emoji": "💀", "hp": 30, "schade": 20, "snelheid": 1, "xp": 25},
        "geest": {"emoji": "👻", "hp": 25, "schade": 25, "snelheid": 1, "xp": 30},
        "orc": {"emoji": "👹", "hp": 50, "schade": 30, "snelheid": 1, "xp": 50}
    }

    # Bosses
    BOSSES = {
        "grot_bewaker": {"emoji": "🐉", "naam": "Grot Draak", "hp": 100,
                        "schade": 25, "xp": 200},
        "eindbaas": {"emoji": "😈", "naam": "Demon Lord", "hp": 200,
                    "schade": 40, "xp": 500}
    }

    # Achievements
    ACHIEVEMENTS = {
        "eerste_schat": {"naam": "Schatzoeker", "beschrijving": "Vind je eerste schat", "xp": 50},
        "tien_schatten": {"naam": "Goudkoorts", "beschrijving": "Vind 10 schatten", "xp": 100},
        "vijftig_schatten": {"naam": "Schatmeester", "beschrijving": "Vind 50 schatten", "xp": 250},
        "eerste_monster": {"naam": "Monsterjager", "beschrijving": "Versla je eerste monster", "xp": 50},
        "tien_monsters": {"naam": "Veteraan", "beschrijving": "Versla 10 monsters", "xp": 150},
        "eerste_boss": {"naam": "Bossslayer", "beschrijving": "Versla een boss", "xp": 200},
        "alle_bosses": {"naam": "Legende", "beschrijving": "Versla alle bosses", "xp": 500},
        "geen_schade": {"naam": "Onkwetsbaar", "beschrijving": "Rond een level af zonder schade", "xp": 100},
        "snelle_run": {"naam": "Speedrunner", "beschrijving": "Rond een level af in <20 stappen", "xp": 150},
        "rijkaard": {"naam": "Rijkaard", "beschrijving": "Verzamel 100 muntjes", "xp": 100},
        "verzamelaar": {"naam": "Verzamelaar", "beschrijving": "Gebruik 10 power-ups", "xp": 75},
        "ontdekker": {"naam": "Wereldreiziger", "beschrijving": "Bezoek alle biomes", "xp": 200},
        "campagne_klaar": {"naam": "Held", "beschrijving": "Voltooi de campagne", "xp": 500},
        "level_10": {"naam": "Ervaren", "beschrijving": "Bereik level 10", "xp": 300},
        "dagelijks_5": {"naam": "Toegewijd", "beschrijving": "Voltooi 5 dagelijkse uitdagingen", "xp": 200}
    }

    # Shop items
    SHOP_ITEMS = {
        "gezondheid": {"prijs": 10, "beschrijving": "Herstel 25 HP"},
        "schild": {"prijs": 15, "beschrijving": "Blokkeert 1 aanval"},
        "bom": {"prijs": 20, "beschrijving": "Vernietigt nabije vijanden"},
        "teleport": {"prijs": 25, "beschrijving": "Teleporteer waar je wilt"},
        "xray": {"prijs": 30, "beschrijving": "Zie alle schatten"},
        "extra_leven": {"prijs": 50, "beschrijving": "Extra leven bij dood"}
    }

    def __init__(self):
        Config.ensure_dirs()
        self.save_file = Config.APPS_DATA_DIR / "schatzoek_v2.json"
        self.data = self._laad_data()
        self._init_game_state()

    def _laad_data(self) -> dict:
        """Laadt opgeslagen data."""
        if self.save_file.exists():
            try:
                with open(self.save_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except json.JSONDecodeError:
                pass
        return self._maak_lege_data()

    def _maak_lege_data(self) -> dict:
        """Maakt lege datastructuur."""
        return {
            "versie": self.VERSIE,
            "profiel": {
                "naam": "Avonturier",
                "class": "ontdekker",
                "level": 1,
                "xp": 0,
                "xp_nodig": 100,
                "totaal_xp": 0,
                "muntjes": 0,
                "totaal_muntjes": 0
            },
            "statistieken": {
                "schatten_gevonden": 0,
                "monsters_verslagen": 0,
                "bosses_verslagen": 0,
                "levels_voltooid": 0,
                "stappen_totaal": 0,
                "powerups_gebruikt": 0,
                "deaths": 0,
                "biomes_bezocht": [],
                "dagelijkse_voltooid": 0
            },
            "campagne": {
                "huidig_level": 0,
                "voltooid": []
            },
            "achievements": [],
            "highscores": {
                "makkelijk": [],
                "normaal": [],
                "moeilijk": [],
                "extreem": []
            },
            "inventory": [],
            "dagelijkse": {
                "datum": None,
                "voltooid": False,
                "seed": 0
            }
        }

    def _sla_op(self):
        """Slaat data op."""
        with open(self.save_file, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)

    def _init_game_state(self):
        """Initialiseert game state variabelen."""
        self.grid_grootte = 7
        self.speler_positie = (0, 0)
        self.speler_hp = 100
        self.max_hp = 100
        self.schatten = set()
        self.gevonden_schatten = set()
        self.muren = set()
        self.vallen = set()
        self.powerups = {}
        self.muntjes = {}
        self.monsters = {}
        self.deuren = set()
        self.sleutels = set()
        self.boss = None
        self.stappen = 0
        self.schade_genomen = 0
        self.actieve_effecten = []
        self.fog_of_war = True
        self.zicht_radius = 3
        self.biome = "bos"

    # ==================== UI HELPERS ====================

    def _toon_header(self, titel: str):
        """Toont een mooie header."""
        print()
        print(kleur("╔" + "═" * 50 + "╗", "cyan"))
        print(kleur("║", "cyan") + f" {titel:^48} " + kleur("║", "cyan"))
        print(kleur("╚" + "═" * 50 + "╝", "cyan"))

    def _toon_profiel(self):
        """Toont speler profiel."""
        p = self.data["profiel"]
        s = self.data["statistieken"]
        char_class = self.CLASSES.get(p["class"], self.CLASSES["ontdekker"])

        print(kleur(f"\n  {char_class['emoji']} {p['naam']} - {char_class['naam']}", "geel"))
        print(f"    Level {p['level']} | XP: {p['xp']}/{p['xp_nodig']}")
        print(f"    💰 {p['muntjes']} muntjes")
        print(f"    📊 {s['schatten_gevonden']} schatten | {s['monsters_verslagen']} monsters")

    # ==================== GRID & RENDERING ====================

    def _is_zichtbaar(self, pos: tuple) -> bool:
        """Checkt of een positie zichtbaar is (fog of war)."""
        if not self.fog_of_war:
            return True

        afstand = abs(pos[0] - self.speler_positie[0]) + \
                  abs(pos[1] - self.speler_positie[1])
        return afstand <= self.zicht_radius

    def _toon_grid(self):
        """Toont het speelveld met fog of war."""
        biome_info = self.BIOMES.get(self.biome, self.BIOMES["bos"])

        # Header met coördinaten
        print("\n    ", end="")
        for x in range(self.grid_grootte):
            print(f"{x:2}", end="")
        print()

        for y in range(self.grid_grootte):
            print(f"  {y:2} ", end="")
            for x in range(self.grid_grootte):
                pos = (x, y)
                zichtbaar = self._is_zichtbaar(pos)

                if pos == self.speler_positie:
                    char_class = self.CLASSES.get(
                        self.data["profiel"]["class"], self.CLASSES["ontdekker"]
                    )
                    print(char_class["emoji"], end="")
                elif not zichtbaar:
                    print("▓▓", end="")
                elif pos in self.gevonden_schatten:
                    print("💎", end="")
                elif pos in self.muren:
                    print(biome_info["muur"], end="")
                elif pos in self.deuren:
                    print("🚪", end="")
                elif pos in self.monsters:
                    monster = self.monsters[pos]
                    print(monster["emoji"], end="")
                elif self.boss and pos == self.boss["positie"]:
                    print(self.boss["emoji"], end="")
                elif pos in self.powerups:
                    pu = self.powerups[pos]
                    print(self.POWERUPS.get(pu, {}).get("emoji", "?"), end="")
                elif pos in self.muntjes:
                    print("🪙", end="")
                elif pos in self.sleutels:
                    print("🗝️", end="")
                else:
                    print("· ", end="")
            print()

    def _toon_status(self):
        """Toont status balk."""
        p = self.data["profiel"]
        char_class = self.CLASSES.get(p["class"], self.CLASSES["ontdekker"])

        # HP balk
        hp_pct = self.speler_hp / self.max_hp
        hp_bars = int(hp_pct * 10)
        hp_color = "groen" if hp_pct > 0.5 else ("geel" if hp_pct > 0.25 else "rood")
        hp_bar = kleur("█" * hp_bars, hp_color) + kleur("░" * (10 - hp_bars), "grijs")

        print(kleur(f"\n  ❤️ HP: [{hp_bar}] {self.speler_hp}/{self.max_hp}", "wit"))
        print(f"  📍 Positie: {self.speler_positie} | 👣 Stappen: {self.stappen}")
        print(f"  💎 Schatten: {len(self.gevonden_schatten)}/{len(self.schatten)}")
        print(f"  💰 Muntjes: {self.data['profiel']['muntjes']}")

        if self.actieve_effecten:
            effecten = ", ".join(self.actieve_effecten)
            print(kleur(f"  ✨ Actief: {effecten}", "magenta"))

        if self.data["inventory"]:
            inv = ", ".join([self.POWERUPS.get(i, {}).get("emoji", i)
                           for i in self.data["inventory"][:5]])
            print(f"  🎒 Inventory: {inv}")

    # ==================== LEVEL GENERATIE ====================

    def _genereer_level(self, settings: dict, biome: str = "bos", is_boss: bool = False):
        """Genereert een nieuw level."""
        self._init_game_state()
        self.grid_grootte = settings.get("grid", 7)
        self.biome = biome

        # Class bonussen
        char_class = self.CLASSES.get(self.data["profiel"]["class"], self.CLASSES["ontdekker"])
        self.max_hp = char_class["hp"]
        self.speler_hp = self.max_hp
        self.zicht_radius = char_class["zicht"]

        # Speler start positie
        self.speler_positie = (0, 0)
        bezet = {self.speler_positie}

        # Plaats schatten
        for _ in range(settings.get("schatten", 3)):
            pos = self._random_pos(bezet)
            if pos:
                self.schatten.add(pos)
                bezet.add(pos)

        # Plaats muren
        for _ in range(settings.get("muren", 5)):
            pos = self._random_pos(bezet)
            if pos:
                self.muren.add(pos)
                bezet.add(pos)

        # Plaats vallen
        for _ in range(settings.get("vallen", 2)):
            pos = self._random_pos(bezet)
            if pos:
                self.vallen.add(pos)
                bezet.add(pos)

        # Plaats powerups
        powerup_types = list(self.POWERUPS.keys())
        for _ in range(settings.get("powerups", 3)):
            pos = self._random_pos(bezet)
            if pos:
                self.powerups[pos] = random.choice(powerup_types)
                bezet.add(pos)

        # Plaats muntjes
        for _ in range(settings.get("muntjes", 5)):
            pos = self._random_pos(bezet)
            if pos:
                self.muntjes[pos] = random.randint(1, 3)
                bezet.add(pos)

        # Plaats monsters
        monster_types = list(self.MONSTERS.keys())
        for _ in range(settings.get("monsters", 2)):
            pos = self._random_pos(bezet)
            if pos:
                monster_type = random.choice(monster_types)
                self.monsters[pos] = {
                    **self.MONSTERS[monster_type],
                    "type": monster_type,
                    "positie": pos
                }
                bezet.add(pos)

        # Plaats boss
        if is_boss:
            pos = self._random_pos(bezet, min_afstand=3)
            if pos:
                boss_type = "eindbaas" if self.data["campagne"]["huidig_level"] >= 9 else "grot_bewaker"
                self.boss = {
                    **self.BOSSES[boss_type],
                    "type": boss_type,
                    "positie": pos,
                    "max_hp": self.BOSSES[boss_type]["hp"]
                }

        # Sleutels en deuren (soms)
        if random.random() < 0.3 and self.grid_grootte >= 7:
            # Plaats deur
            deur_pos = self._random_pos(bezet)
            if deur_pos:
                self.deuren.add(deur_pos)
                bezet.add(deur_pos)
                # Plaats sleutel
                sleutel_pos = self._random_pos(bezet)
                if sleutel_pos:
                    self.sleutels.add(sleutel_pos)

    def _random_pos(self, bezet: set, min_afstand: int = 1) -> tuple:
        """Genereert een random positie die niet bezet is."""
        for _ in range(100):
            pos = (random.randint(0, self.grid_grootte - 1),
                   random.randint(0, self.grid_grootte - 1))
            if pos not in bezet:
                if min_afstand > 1:
                    afstand = abs(pos[0] - self.speler_positie[0]) + \
                              abs(pos[1] - self.speler_positie[1])
                    if afstand >= min_afstand:
                        return pos
                else:
                    return pos
        return None

    # ==================== BEWEGING & ACTIES ====================

    def _beweeg(self, richting: str) -> bool:
        """Beweegt de speler in een richting."""
        dx, dy = 0, 0
        if richting == "n":
            dy = -1
        elif richting == "z":
            dy = 1
        elif richting == "o":
            dx = 1
        elif richting == "w":
            dx = -1
        else:
            return False

        # Snelheid bonus
        stappen = 2 if "snelheid" in self.actieve_effecten else 1

        for _ in range(stappen):
            nieuwe_x = self.speler_positie[0] + dx
            nieuwe_y = self.speler_positie[1] + dy
            nieuwe_pos = (nieuwe_x, nieuwe_y)

            # Check grenzen
            if not (0 <= nieuwe_x < self.grid_grootte and
                    0 <= nieuwe_y < self.grid_grootte):
                fout("Je kunt niet van het grid af!")
                return False

            # Check muren
            if nieuwe_pos in self.muren:
                fout("Daar staat een muur!")
                return False

            # Check deuren
            if nieuwe_pos in self.deuren:
                if "sleutel" in self.data["inventory"]:
                    self.data["inventory"].remove("sleutel")
                    self.deuren.remove(nieuwe_pos)
                    succes("Je opent de deur met de sleutel!")
                else:
                    fout("Je hebt een sleutel nodig!")
                    return False

            # Beweeg
            self.speler_positie = nieuwe_pos
            self.stappen += 1
            self.data["statistieken"]["stappen_totaal"] += 1

        return True

    def _check_tile(self):
        """Checkt de huidige tile voor items/events."""
        pos = self.speler_positie

        # Schat
        if pos in self.schatten and pos not in self.gevonden_schatten:
            self.gevonden_schatten.add(pos)
            self.data["statistieken"]["schatten_gevonden"] += 1
            self._geef_xp(20)
            succes("💎 SCHAT GEVONDEN! +20 XP")
            self._check_achievement("eerste_schat", self.data["statistieken"]["schatten_gevonden"] >= 1)
            self._check_achievement("tien_schatten", self.data["statistieken"]["schatten_gevonden"] >= 10)
            self._check_achievement("vijftig_schatten", self.data["statistieken"]["schatten_gevonden"] >= 50)

        # Muntje
        if pos in self.muntjes:
            aantal = self.muntjes.pop(pos)
            self.data["profiel"]["muntjes"] += aantal
            self.data["profiel"]["totaal_muntjes"] += aantal
            succes(f"🪙 +{aantal} muntjes!")
            self._check_achievement("rijkaard", self.data["profiel"]["totaal_muntjes"] >= 100)

        # Sleutel
        if pos in self.sleutels:
            self.sleutels.remove(pos)
            self.data["inventory"].append("sleutel")
            succes("🗝️ Je hebt een sleutel gevonden!")

        # Power-up
        if pos in self.powerups:
            powerup = self.powerups.pop(pos)
            self.data["inventory"].append(powerup)
            pu_info = self.POWERUPS.get(powerup, {})
            succes(f"{pu_info.get('emoji', '?')} Power-up: {powerup}!")

        # Val
        if pos in self.vallen:
            char_class = self.data["profiel"]["class"]
            if char_class == "ninja":
                info("Je ontwijkt de val elegant!")
            else:
                self.vallen.remove(pos)
                schade = 15
                self._neem_schade(schade)
                fout(f"💥 Je bent in een val gestapt! -{schade} HP")

        # Monster
        if pos in self.monsters:
            self._gevecht_monster(pos)

        # Boss
        if self.boss and pos == self.boss["positie"]:
            self._gevecht_boss()

    def _neem_schade(self, schade: int):
        """Verwerkt schade aan speler."""
        # Check schild
        if "schild" in self.actieve_effecten:
            self.actieve_effecten.remove("schild")
            info("🛡️ Je schild absorbeert de aanval!")
            return

        # Tank class halveert schade
        if self.data["profiel"]["class"] == "tank":
            schade = schade // 2

        self.speler_hp -= schade
        self.schade_genomen += schade

        if self.speler_hp <= 0:
            self.speler_hp = 0

    def _gevecht_monster(self, pos: tuple):
        """Gevecht met een monster."""
        monster = self.monsters[pos]

        self._toon_header(f"⚔️ Gevecht met {monster['type'].title()}!")

        while monster["hp"] > 0 and self.speler_hp > 0:
            print(f"\n  {monster['emoji']} {monster['type'].title()}: {monster['hp']} HP")
            print(f"  Je HP: {self.speler_hp}")

            print(kleur("\n  [a]anvallen | [v]luchten | [i]tem gebruiken", "geel"))
            keuze = input(kleur("  Actie: ", "cyan")).strip().lower()

            if keuze == "a":
                # Speler aanval
                schade = random.randint(15, 25)
                monster["hp"] -= schade
                print(kleur(f"\n  Je doet {schade} schade!", "groen"))

                # Monster aanval (als nog leeft)
                if monster["hp"] > 0:
                    self._neem_schade(monster["schade"])
                    print(kleur(f"  {monster['type'].title()} doet {monster['schade']} schade!", "rood"))

            elif keuze == "v":
                # Vluchten
                if random.random() < 0.5:
                    succes("Je bent ontsnapt!")
                    return
                else:
                    fout("Vluchten mislukt!")
                    self._neem_schade(monster["schade"])

            elif keuze == "i":
                self._toon_inventory_gevecht()

        if monster["hp"] <= 0:
            del self.monsters[pos]
            self._geef_xp(monster["xp"])
            self.data["statistieken"]["monsters_verslagen"] += 1
            succes(f"🎉 {monster['type'].title()} verslagen! +{monster['xp']} XP")
            self._check_achievement("eerste_monster", self.data["statistieken"]["monsters_verslagen"] >= 1)
            self._check_achievement("tien_monsters", self.data["statistieken"]["monsters_verslagen"] >= 10)

    def _gevecht_boss(self):
        """Gevecht met een boss."""
        self._toon_header(f"👑 BOSS FIGHT: {self.boss['naam']}!")

        print(kleur(f"\n  {self.boss['emoji']} {self.boss['naam']} verschijnt!", "rood"))
        input(kleur("\n  Druk op Enter om te beginnen...", "grijs"))

        while self.boss["hp"] > 0 and self.speler_hp > 0:
            clear_scherm()
            print(kleur(f"\n  === BOSS: {self.boss['naam']} ===", "rood"))

            # Boss HP balk
            boss_pct = self.boss["hp"] / self.boss["max_hp"]
            boss_bars = int(boss_pct * 20)
            boss_bar = kleur("█" * boss_bars, "rood") + "░" * (20 - boss_bars)
            print(f"  {self.boss['emoji']} [{boss_bar}] {self.boss['hp']}/{self.boss['max_hp']}")

            # Speler HP balk
            hp_pct = self.speler_hp / self.max_hp
            hp_bars = int(hp_pct * 20)
            hp_bar = kleur("█" * hp_bars, "groen") + "░" * (20 - hp_bars)
            print(f"  ❤️ [{hp_bar}] {self.speler_hp}/{self.max_hp}")

            print(kleur("\n  [a]anvallen | [s]peciale aanval | [i]tem", "geel"))
            keuze = input(kleur("  Actie: ", "cyan")).strip().lower()

            if keuze == "a":
                schade = random.randint(20, 35)
                self.boss["hp"] -= schade
                print(kleur(f"\n  Je doet {schade} schade!", "groen"))

            elif keuze == "s":
                # Speciale aanval (kost meer maar doet meer schade)
                if random.random() < 0.7:
                    schade = random.randint(40, 60)
                    self.boss["hp"] -= schade
                    print(kleur(f"\n  💥 KRITIEKE TREFFER! {schade} schade!", "geel"))
                else:
                    print(kleur("\n  Speciale aanval mist!", "rood"))

            elif keuze == "i":
                self._toon_inventory_gevecht()
                continue

            # Boss aanval
            if self.boss["hp"] > 0:
                # Boss heeft speciale aanvallen
                if random.random() < 0.3:
                    schade = self.boss["schade"] * 2
                    print(kleur(f"\n  💀 {self.boss['naam']} gebruikt MEGA AANVAL!", "rood"))
                else:
                    schade = self.boss["schade"]
                self._neem_schade(schade)
                print(kleur(f"  Je neemt {schade} schade!", "rood"))

            input(kleur("\n  Druk op Enter...", "grijs"))

        if self.boss["hp"] <= 0:
            self._geef_xp(self.boss["xp"])
            self.data["statistieken"]["bosses_verslagen"] += 1
            succes(f"\n  🎊 {self.boss['naam']} VERSLAGEN! +{self.boss['xp']} XP")
            self._check_achievement("eerste_boss", self.data["statistieken"]["bosses_verslagen"] >= 1)
            self._check_achievement("alle_bosses", self.data["statistieken"]["bosses_verslagen"] >= 2)
            self.boss = None

    def _toon_inventory_gevecht(self):
        """Toont inventory tijdens gevecht."""
        inv = self.data["inventory"]
        if not inv:
            waarschuwing("Je inventory is leeg!")
            return

        print(kleur("\n  Inventory:", "geel"))
        for i, item in enumerate(inv[:5], 1):
            pu_info = self.POWERUPS.get(item, {})
            print(f"    {i}. {pu_info.get('emoji', '?')} {item}")

        keuze = input(kleur("  Gebruik item (nummer): ", "cyan")).strip()
        try:
            idx = int(keuze) - 1
            if 0 <= idx < len(inv):
                item = inv[idx]
                if item == "gezondheid":
                    self.data["inventory"].remove(item)
                    heal = min(25, self.max_hp - self.speler_hp)
                    self.speler_hp += heal
                    succes(f"❤️ +{heal} HP!")
                elif item == "schild":
                    self.data["inventory"].remove(item)
                    self.actieve_effecten.append("schild")
                    succes("🛡️ Schild geactiveerd!")
                elif item == "bom":
                    self.data["inventory"].remove(item)
                    return "bom"  # Special return voor gevecht
        except (ValueError, IndexError):
            pass

    # ==================== MONSTER AI ====================

    def _beweeg_monsters(self):
        """Beweegt alle monsters richting de speler."""
        if "onzichtbaar" in self.actieve_effecten:
            return

        nieuwe_monsters = {}
        for pos, monster in self.monsters.items():
            # Bereken richting naar speler
            dx = 0
            dy = 0
            if pos[0] < self.speler_positie[0]:
                dx = 1
            elif pos[0] > self.speler_positie[0]:
                dx = -1
            if pos[1] < self.speler_positie[1]:
                dy = 1
            elif pos[1] > self.speler_positie[1]:
                dy = -1

            # Beweeg (50% kans per as)
            if random.random() < 0.5:
                nieuwe_x = pos[0] + dx
                nieuwe_y = pos[1]
            else:
                nieuwe_x = pos[0]
                nieuwe_y = pos[1] + dy

            nieuwe_pos = (nieuwe_x, nieuwe_y)

            # Check of nieuwe positie geldig is
            if (0 <= nieuwe_x < self.grid_grootte and
                0 <= nieuwe_y < self.grid_grootte and
                nieuwe_pos not in self.muren and
                nieuwe_pos not in nieuwe_monsters):
                nieuwe_monsters[nieuwe_pos] = monster
                monster["positie"] = nieuwe_pos
            else:
                nieuwe_monsters[pos] = monster

        self.monsters = nieuwe_monsters

        # Check of monster op speler staat
        if self.speler_positie in self.monsters:
            self._gevecht_monster(self.speler_positie)

    # ==================== POWER-UPS ====================

    def _gebruik_powerup(self, powerup: str) -> bool:
        """Gebruikt een power-up."""
        if powerup not in self.data["inventory"]:
            fout(f"Je hebt geen {powerup}!")
            return False

        self.data["inventory"].remove(powerup)
        self.data["statistieken"]["powerups_gebruikt"] += 1
        self._check_achievement("verzamelaar", self.data["statistieken"]["powerups_gebruikt"] >= 10)

        if powerup == "kompas":
            self._gebruik_kompas()
        elif powerup == "radar":
            self._gebruik_radar()
        elif powerup == "teleport":
            self._gebruik_teleport()
        elif powerup == "schild":
            self.actieve_effecten.append("schild")
            succes("🛡️ Schild geactiveerd!")
        elif powerup == "snelheid":
            self.actieve_effecten.append("snelheid")
            succes("⚡ Snelheidsboost geactiveerd!")
        elif powerup == "bom":
            self._gebruik_bom()
        elif powerup == "xray":
            self.fog_of_war = False
            succes("👁️ Je ziet nu alles!")
        elif powerup == "onzichtbaar":
            self.actieve_effecten.append("onzichtbaar")
            succes("👻 Je bent onzichtbaar!")
        elif powerup == "gezondheid":
            heal = min(25, self.max_hp - self.speler_hp)
            self.speler_hp += heal
            succes(f"❤️ +{heal} HP!")

        return True

    def _gebruik_kompas(self):
        """Kompas: toont richting naar dichtstbijzijnde schat."""
        niet_gevonden = self.schatten - self.gevonden_schatten
        if not niet_gevonden:
            info("Alle schatten al gevonden!")
            return

        dichtstbij = min(niet_gevonden,
                        key=lambda s: self._bereken_afstand(self.speler_positie, s))
        richting = self._krijg_richting(dichtstbij)
        print(kleur(f"\n  🧭 De schat ligt richting: {richting}", "geel"))

    def _gebruik_radar(self):
        """Radar: toont afstand tot alle schatten."""
        niet_gevonden = self.schatten - self.gevonden_schatten
        if not niet_gevonden:
            info("Alle schatten al gevonden!")
            return

        print(kleur("\n  📡 Afstanden tot schatten:", "geel"))
        for i, schat in enumerate(niet_gevonden, 1):
            afstand = self._bereken_afstand(self.speler_positie, schat)
            print(f"    Schat {i}: {afstand} stappen")

    def _gebruik_teleport(self):
        """Teleport: spring naar een positie."""
        try:
            coords = input(kleur("  Teleport naar (x,y): ", "cyan")).strip()
            x, y = map(int, coords.replace(" ", "").split(","))

            if not (0 <= x < self.grid_grootte and 0 <= y < self.grid_grootte):
                fout("Ongeldige coördinaten!")
                return

            if (x, y) in self.muren:
                fout("Je kunt niet naar een muur teleporteren!")
                return

            self.speler_positie = (x, y)
            succes(f"🌀 Je bent nu op ({x}, {y})!")

        except ValueError:
            fout("Gebruik format: x,y (bijv: 3,4)")

    def _gebruik_bom(self):
        """Bom: vernietigt nabije muren en monsters."""
        x, y = self.speler_positie
        vernietigde = 0

        # Check alle nabije posities
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                pos = (x + dx, y + dy)
                if pos in self.muren:
                    self.muren.remove(pos)
                    vernietigde += 1
                if pos in self.monsters:
                    del self.monsters[pos]
                    self.data["statistieken"]["monsters_verslagen"] += 1
                    vernietigde += 1

        succes(f"💣 BOEM! {vernietigde} objecten vernietigd!")

    def _bereken_afstand(self, pos1: tuple, pos2: tuple) -> int:
        """Berekent Manhattan-afstand."""
        return abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1])

    def _krijg_richting(self, doel: tuple) -> str:
        """Geeft de richting naar een doel."""
        x, y = self.speler_positie
        dx, dy = doel[0] - x, doel[1] - y

        richtingen = []
        if dy < 0:
            richtingen.append("Noord")
        elif dy > 0:
            richtingen.append("Zuid")
        if dx > 0:
            richtingen.append("Oost")
        elif dx < 0:
            richtingen.append("West")

        return "-".join(richtingen) if richtingen else "Hier!"

    def _krijg_hint(self) -> str:
        """Geeft een hint gebaseerd op afstand."""
        niet_gevonden = self.schatten - self.gevonden_schatten
        if not niet_gevonden:
            return "Alle schatten gevonden!"

        kleinste = min(self._bereken_afstand(self.speler_positie, s) for s in niet_gevonden)

        if kleinste == 0:
            return "💎 SCHAT GEVONDEN!"
        elif kleinste == 1:
            return "🔥 Gloeiend heet!"
        elif kleinste == 2:
            return "🌡️ Warm!"
        elif kleinste <= 4:
            return "😐 Lauw..."
        else:
            return "❄️ Koud..."

    # ==================== XP & LEVELING ====================

    def _geef_xp(self, xp: int):
        """Geeft XP aan de speler."""
        self.data["profiel"]["xp"] += xp
        self.data["profiel"]["totaal_xp"] += xp

        # Check level up
        while self.data["profiel"]["xp"] >= self.data["profiel"]["xp_nodig"]:
            self.data["profiel"]["xp"] -= self.data["profiel"]["xp_nodig"]
            self.data["profiel"]["level"] += 1
            self.data["profiel"]["xp_nodig"] = int(self.data["profiel"]["xp_nodig"] * 1.5)
            succes(f"\n  🎉 LEVEL UP! Je bent nu level {self.data['profiel']['level']}!")
            self._check_achievement("level_10", self.data["profiel"]["level"] >= 10)

    # ==================== ACHIEVEMENTS ====================

    def _check_achievement(self, achievement_id: str, voorwaarde: bool):
        """Checkt en unlockt een achievement."""
        if voorwaarde and achievement_id not in self.data["achievements"]:
            self.data["achievements"].append(achievement_id)
            ach = self.ACHIEVEMENTS.get(achievement_id, {})
            print(kleur(f"\n  🏆 ACHIEVEMENT UNLOCKED: {ach.get('naam', achievement_id)}!", "geel"))
            self._geef_xp(ach.get("xp", 0))

    def _toon_achievements(self):
        """Toont alle achievements."""
        self._toon_header("🏆 Achievements")

        unlocked = len(self.data["achievements"])
        total = len(self.ACHIEVEMENTS)
        print(f"\n  Unlocked: {unlocked}/{total}")

        for ach_id, ach in self.ACHIEVEMENTS.items():
            if ach_id in self.data["achievements"]:
                status = kleur("✓", "groen")
            else:
                status = kleur("✗", "grijs")
            print(f"    {status} {ach['naam']}: {ach['beschrijving']}")

    # ==================== SHOP ====================

    def _toon_shop(self):
        """Toont de shop."""
        while True:
            self._toon_header("🏪 Shop")
            print(f"\n  💰 Je hebt {self.data['profiel']['muntjes']} muntjes")

            print(kleur("\n  Items te koop:", "geel"))
            items = list(self.SHOP_ITEMS.items())
            for i, (item, info) in enumerate(items, 1):
                pu_emoji = self.POWERUPS.get(item, {}).get("emoji", "📦")
                print(f"    {i}. {pu_emoji} {item.title()} - {info['prijs']} 🪙")
                print(kleur(f"       {info['beschrijving']}", "grijs"))

            print(kleur("\n    0. Terug", "grijs"))

            keuze = input(kleur("\n  Koop item (nummer): ", "cyan")).strip()

            if keuze == "0":
                break

            try:
                idx = int(keuze) - 1
                if 0 <= idx < len(items):
                    item, info = items[idx]
                    if self.data["profiel"]["muntjes"] >= info["prijs"]:
                        self.data["profiel"]["muntjes"] -= info["prijs"]
                        self.data["inventory"].append(item)
                        succes(f"Je hebt {item} gekocht!")
                    else:
                        fout("Niet genoeg muntjes!")
            except ValueError:
                pass

            input(kleur("\n  Druk op Enter...", "grijs"))

    # ==================== GAME MODES ====================

    def _campagne_menu(self):
        """Campagne mode menu."""
        while True:
            self._toon_header("⚔️ Campagne Modus")

            huidig = self.data["campagne"]["huidig_level"]
            print(f"\n  Voortgang: Level {huidig + 1}/10")

            print(kleur("\n  Levels:", "geel"))
            for i, level in enumerate(self.CAMPAGNE_LEVELS):
                if i < huidig:
                    status = kleur("✓", "groen")
                elif i == huidig:
                    status = kleur("►", "geel")
                else:
                    status = kleur("🔒", "grijs")
                biome_emoji = self.BIOMES[level["biome"]]["emoji"]
                boss_ind = " 👑" if level["boss"] else ""
                print(f"    {status} {i+1}. {biome_emoji} {level['naam']}{boss_ind}")

            print(kleur("\n  [s]tart level | [0] terug", "geel"))

            keuze = input(kleur("\n  Keuze: ", "cyan")).strip().lower()

            if keuze == "0":
                break
            elif keuze == "s":
                if huidig < len(self.CAMPAGNE_LEVELS):
                    self._speel_campagne_level(huidig)

            input(kleur("\n  Druk op Enter...", "grijs"))

    def _speel_campagne_level(self, level_idx: int):
        """Speelt een campagne level."""
        level = self.CAMPAGNE_LEVELS[level_idx]
        self.data["campagne"]["huidig_level"] = level_idx

        # Verhaal
        clear_scherm()
        self._toon_header(f"📖 {level['naam']}")
        print(kleur(f"\n  {level['verhaal']}", "geel"))
        input(kleur("\n  Druk op Enter om te beginnen...", "grijs"))

        # Genereer level
        settings = {
            "grid": level["grid"],
            "schatten": level["schatten"],
            "muren": level["grid"],
            "vallen": level["grid"] // 3,
            "powerups": 3,
            "monsters": level["monsters"],
            "muntjes": level["grid"]
        }
        self._genereer_level(settings, level["biome"], level["boss"])

        # Track biome
        if level["biome"] not in self.data["statistieken"]["biomes_bezocht"]:
            self.data["statistieken"]["biomes_bezocht"].append(level["biome"])
            self._check_achievement("ontdekker",
                                   len(self.data["statistieken"]["biomes_bezocht"]) >= 5)

        # Speel
        resultaat = self._speel_level()

        if resultaat == "gewonnen":
            if level_idx not in self.data["campagne"]["voltooid"]:
                self.data["campagne"]["voltooid"].append(level_idx)
            self.data["campagne"]["huidig_level"] = level_idx + 1
            self.data["statistieken"]["levels_voltooid"] += 1

            if self.schade_genomen == 0:
                self._check_achievement("geen_schade", True)
            if self.stappen < 20:
                self._check_achievement("snelle_run", True)

            if level_idx == 9:
                self._check_achievement("campagne_klaar", True)
                self._toon_einde_campagne()

        self._sla_op()

    def _toon_einde_campagne(self):
        """Toont einde van campagne."""
        clear_scherm()
        print(kleur("""
    ╔═══════════════════════════════════════════════════╗
    ║                                                   ║
    ║   🏆  GEFELICITEERD!  🏆                         ║
    ║                                                   ║
    ║   Je hebt de campagne voltooid!                  ║
    ║                                                   ║
    ║   Je bent een ware HELD!                         ║
    ║                                                   ║
    ╚═══════════════════════════════════════════════════╝
        """, "geel"))

    def _vrij_spel_menu(self):
        """Vrij spel menu."""
        self._toon_header("🎮 Vrij Spel")

        print(kleur("\n  Kies moeilijkheid:", "geel"))
        print("    1. Makkelijk (5x5, 2 schatten)")
        print("    2. Normaal (7x7, 3 schatten)")
        print("    3. Moeilijk (9x9, 5 schatten)")
        print("    4. Extreem (12x12, 7 schatten)")

        keuze = input(kleur("\n  Keuze (1-4): ", "cyan")).strip()
        moeilijkheid = {"1": "makkelijk", "2": "normaal", "3": "moeilijk", "4": "extreem"}.get(keuze, "normaal")

        # Kies biome
        print(kleur("\n  Kies biome:", "geel"))
        biomes = list(self.BIOMES.items())
        for i, (key, biome) in enumerate(biomes, 1):
            print(f"    {i}. {biome['emoji']} {biome['naam']}")

        biome_keuze = input(kleur("\n  Keuze: ", "cyan")).strip()
        try:
            biome_idx = int(biome_keuze) - 1
            biome = biomes[biome_idx][0] if 0 <= biome_idx < len(biomes) else "bos"
        except ValueError:
            biome = "bos"

        # Genereer en speel
        self._genereer_level(self.MOEILIJKHEID[moeilijkheid], biome)
        resultaat = self._speel_level()

        if resultaat == "gewonnen":
            self._check_highscore(moeilijkheid, self.stappen)

        self._sla_op()

    def _dagelijkse_uitdaging(self):
        """Dagelijkse uitdaging."""
        vandaag = str(date.today())

        if self.data["dagelijkse"]["datum"] == vandaag and self.data["dagelijkse"]["voltooid"]:
            info("Je hebt de dagelijkse uitdaging al voltooid!")
            input(kleur("\n  Druk op Enter...", "grijs"))
            return

        # Genereer met seed gebaseerd op datum
        if self.data["dagelijkse"]["datum"] != vandaag:
            self.data["dagelijkse"]["datum"] = vandaag
            self.data["dagelijkse"]["voltooid"] = False
            self.data["dagelijkse"]["seed"] = hash(vandaag) % 1000000

        random.seed(self.data["dagelijkse"]["seed"])

        self._toon_header("📅 Dagelijkse Uitdaging")
        print(kleur(f"\n  Datum: {vandaag}", "geel"))
        print("  Voltooi de uitdaging voor bonus XP!")
        input(kleur("\n  Druk op Enter om te beginnen...", "grijs"))

        # Genereer speciaal level
        settings = {
            "grid": 8,
            "schatten": 4,
            "muren": 6,
            "vallen": 3,
            "powerups": 2,
            "monsters": 3,
            "muntjes": 10
        }
        self._genereer_level(settings, random.choice(list(self.BIOMES.keys())))

        random.seed()  # Reset seed

        resultaat = self._speel_level()

        if resultaat == "gewonnen":
            self.data["dagelijkse"]["voltooid"] = True
            self.data["statistieken"]["dagelijkse_voltooid"] += 1
            self._geef_xp(100)  # Bonus XP
            succes("🎉 Dagelijkse uitdaging voltooid! +100 bonus XP!")
            self._check_achievement("dagelijks_5",
                                   self.data["statistieken"]["dagelijkse_voltooid"] >= 5)

        self._sla_op()

    # ==================== MAIN GAME LOOP ====================

    def _speel_level(self) -> str:
        """Speelt een level. Returns 'gewonnen', 'verloren', of 'gestopt'."""
        while True:
            clear_scherm()

            # Check win conditie
            if len(self.gevonden_schatten) >= len(self.schatten):
                if self.boss is None:
                    return self._level_gewonnen()

            # Check verlies conditie
            if self.speler_hp <= 0:
                return self._level_verloren()

            # Toon game state
            biome_info = self.BIOMES.get(self.biome, self.BIOMES["bos"])
            print(kleur(f"\n  === {biome_info['emoji']} {biome_info['naam']} ===", biome_info["kleur"]))

            self._toon_grid()
            self._toon_status()

            # Hint
            hint = self._krijg_hint()
            print(kleur(f"\n  Hint: {hint}", "magenta"))

            # Controls
            print(kleur("\n  [n/z/o/w] bewegen | [i]nventory | [q]uit", "grijs"))

            actie = input(kleur("  Actie: ", "cyan")).strip().lower()

            if actie == "q":
                return "gestopt"
            elif actie == "i":
                self._toon_inventory_menu()
            elif actie in ["n", "z", "o", "w"]:
                if self._beweeg(actie):
                    self._check_tile()
                    self._beweeg_monsters()
                    # Clear tijdelijke effecten
                    if "snelheid" in self.actieve_effecten:
                        self.actieve_effecten.remove("snelheid")

    def _level_gewonnen(self) -> str:
        """Verwerkt gewonnen level."""
        clear_scherm()
        print(kleur("""
    ╔═══════════════════════════════════════════════════╗
    ║                                                   ║
    ║   🎊  LEVEL VOLTOOID!  🎊                        ║
    ║                                                   ║
    ╚═══════════════════════════════════════════════════╝
        """, "groen"))

        print(f"  💎 Schatten: {len(self.gevonden_schatten)}")
        print(f"  👣 Stappen: {self.stappen}")
        print(f"  ❤️ HP over: {self.speler_hp}/{self.max_hp}")

        # Bonus voor geen schade
        if self.schade_genomen == 0:
            self._geef_xp(50)
            print(kleur("  🛡️ Geen schade bonus: +50 XP!", "geel"))

        input(kleur("\n  Druk op Enter...", "grijs"))
        return "gewonnen"

    def _level_verloren(self) -> str:
        """Verwerkt verloren level."""
        clear_scherm()
        self.data["statistieken"]["deaths"] += 1

        print(kleur("""
    ╔═══════════════════════════════════════════════════╗
    ║                                                   ║
    ║   💀  GAME OVER  💀                              ║
    ║                                                   ║
    ╚═══════════════════════════════════════════════════╝
        """, "rood"))

        print(f"  💎 Schatten gevonden: {len(self.gevonden_schatten)}/{len(self.schatten)}")
        print(f"  👣 Stappen: {self.stappen}")

        input(kleur("\n  Druk op Enter...", "grijs"))
        return "verloren"

    def _toon_inventory_menu(self):
        """Toont inventory menu."""
        inv = self.data["inventory"]
        if not inv:
            waarschuwing("Je inventory is leeg!")
            input(kleur("\n  Druk op Enter...", "grijs"))
            return

        print(kleur("\n  🎒 Inventory:", "geel"))
        for i, item in enumerate(inv, 1):
            pu_info = self.POWERUPS.get(item, {})
            print(f"    {i}. {pu_info.get('emoji', '?')} {item} - {pu_info.get('beschrijving', '')}")

        print(kleur("\n    0. Terug", "grijs"))

        keuze = input(kleur("\n  Gebruik item (nummer): ", "cyan")).strip()

        if keuze == "0":
            return

        try:
            idx = int(keuze) - 1
            if 0 <= idx < len(inv):
                self._gebruik_powerup(inv[idx])
        except ValueError:
            pass

        input(kleur("\n  Druk op Enter...", "grijs"))

    def _check_highscore(self, moeilijkheid: str, stappen: int):
        """Checkt en slaat highscore op."""
        scores = self.data["highscores"].get(moeilijkheid, [])
        is_highscore = len(scores) < 5 or (scores and stappen < scores[-1]["stappen"])

        if is_highscore:
            print(kleur("\n  🏆 NIEUWE HIGHSCORE!", "geel"))
            naam = input(kleur("  Voer je naam in: ", "cyan")).strip() or "Anoniem"

            scores.append({"naam": naam, "stappen": stappen})
            scores.sort(key=lambda x: x["stappen"])
            self.data["highscores"][moeilijkheid] = scores[:5]

    def _toon_highscores(self):
        """Toont highscores."""
        self._toon_header("🏆 Highscores")

        for niveau in ["makkelijk", "normaal", "moeilijk", "extreem"]:
            scores = self.data["highscores"].get(niveau, [])
            print(kleur(f"\n  [{niveau.upper()}]", "geel"))
            if scores:
                for i, score in enumerate(scores[:5], 1):
                    print(f"    {i}. {score['naam']}: {score['stappen']} stappen")
            else:
                print(kleur("    Nog geen scores!", "grijs"))

    def _kies_class(self):
        """Laat speler een class kiezen."""
        self._toon_header("🎭 Kies je Class")

        for i, (key, char_class) in enumerate(self.CLASSES.items(), 1):
            print(f"\n  {i}. {char_class['emoji']} {char_class['naam']}")
            print(kleur(f"     {char_class['beschrijving']}", "grijs"))
            print(f"     HP: {char_class['hp']} | Zicht: {char_class['zicht']} | Special: {char_class['special']}")

        keuze = input(kleur("\n  Keuze (1-3): ", "cyan")).strip()
        classes = list(self.CLASSES.keys())
        try:
            idx = int(keuze) - 1
            if 0 <= idx < len(classes):
                self.data["profiel"]["class"] = classes[idx]
                succes(f"Je speelt nu als {self.CLASSES[classes[idx]]['naam']}!")
        except ValueError:
            pass

    # ==================== MAIN MENU ====================

    def _toon_hoofdmenu(self):
        """Toont het hoofdmenu."""
        print()
        print(kleur("┌" + "─" * 44 + "┐", "cyan"))
        print(kleur("│", "cyan") + kleur("     🗺️ SCHATZOEK GAME v2.0", "geel") +
              kleur("              │", "cyan"))
        print(kleur("├" + "─" * 44 + "┤", "cyan"))

        menu_items = [
            ("1", "Campagne"),
            ("2", "Vrij Spel"),
            ("3", "Dagelijkse Uitdaging"),
            ("", ""),
            ("4", "Shop"),
            ("5", "Kies Class"),
            ("6", "Achievements"),
            ("7", "Highscores"),
            ("", ""),
            ("0", "Terug naar hoofdmenu")
        ]

        for key, label in menu_items:
            if key == "":
                print(kleur("│", "cyan") + " " * 44 + kleur("│", "cyan"))
            else:
                print(kleur("│", "cyan") + f"  {kleur(key, 'groen'):>5}. {label:<36}" +
                      kleur("│", "cyan"))

        print(kleur("└" + "─" * 44 + "┘", "cyan"))

    def run(self):
        """Start de app."""
        clear_scherm()

        print(kleur("""
    ╔═══════════════════════════════════════════════════╗
    ║                                                   ║
    ║   🗺️  SCHATZOEK GAME  v2.0                       ║
    ║                                                   ║
    ║   Campagne • Classes • Monsters • Achievements   ║
    ║                                                   ║
    ╚═══════════════════════════════════════════════════╝
        """, "cyan"))

        self._toon_profiel()

        while True:
            self._toon_hoofdmenu()
            keuze = input(kleur("\n  Kies een optie: ", "cyan")).strip()

            if keuze == "0":
                self._sla_op()
                print(kleur("\n  Terug naar hoofdmenu...", "grijs"))
                break
            elif keuze == "1":
                self._campagne_menu()
            elif keuze == "2":
                self._vrij_spel_menu()
            elif keuze == "3":
                self._dagelijkse_uitdaging()
            elif keuze == "4":
                self._toon_shop()
            elif keuze == "5":
                self._kies_class()
            elif keuze == "6":
                self._toon_achievements()
                input(kleur("\n  Druk op Enter...", "grijs"))
            elif keuze == "7":
                self._toon_highscores()
                input(kleur("\n  Druk op Enter...", "grijs"))
            else:
                fout("Ongeldige keuze.")
