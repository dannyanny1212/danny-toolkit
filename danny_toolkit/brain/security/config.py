"""
Security Config — Configuratie en ernst-niveaus.

Bevat:
- Ernst           — Ernst niveaus klasse
- SecurityConfig  — Config laden/opslaan/hash verificatie
- _ERNST_KLEUR    — Kleur mapping per ernst
"""

import hashlib
import json
import logging

from danny_toolkit.core.config import Config
from danny_toolkit.core.utils import kleur, Kleur
from danny_toolkit.brain.security.utils import _scrub_adres

logger = logging.getLogger(__name__)


# -- Config pad --

_CONFIG_PAD = Config.DATA_DIR / "security_config.json"
_CONFIG_HASH_PAD = Config.DATA_DIR / ".security_config_hash"

_DEFAULT_CONFIG = {
    "wallets": {
        "btc": [],
        "eth": [],
        "sol": [],
    },
    "watchlist": [
        "bitcoin", "ethereum", "solana",
    ],
    "drempels": {
        "prijs_daling_pct": 5.0,
        "stijging_pct": 10.0,
        "whale_alert_usd": 100000,
        "whale_alert_eth": 10.0,
    },
    "audit_bestanden": [
        "danny_toolkit/brain/governor.py",
        "danny_toolkit/brain/cortical_stack.py",
        "danny_toolkit/brain/singularity.py",
        "danny_toolkit/brain/arbitrator.py",
        "swarm_engine.py",
    ],
}


# -- Ernst niveaus --

class Ernst:
    """Ernst niveaus voor bevindingen."""
    KRITIEK = "KRITIEK"
    HOOG = "HOOG"
    MEDIUM = "MEDIUM"
    LAAG = "LAAG"


_ERNST_KLEUR = {
    Ernst.KRITIEK: Kleur.FEL_ROOD,
    Ernst.HOOG: Kleur.ROOD,
    Ernst.MEDIUM: Kleur.FEL_GEEL,
    Ernst.LAAG: Kleur.DIM,
}


# -- SecurityConfig --

class SecurityConfig:
    """Laadt en beheert security configuratie.

    Config bestand: data/security_config.json
    Wordt automatisch aangemaakt met defaults.
    Danny vult zelf wallet adressen in.
    """

    def __init__(self):
        """Initializes a new instance, ensuring required directories exist, 
loading initial data, and setting default configuration values. 
Configures the pad and tracks hash changes."""
        Config.ensure_dirs()
        self._pad = _CONFIG_PAD
        self._hash_gewijzigd = False
        self._data = self._laad()

    def _laad(self) -> dict:
        """Laad config of maak defaults aan."""
        if self._pad.exists():
            try:
                with open(
                    self._pad, "r", encoding="utf-8"
                ) as f:
                    data = json.load(f)
                # Merge met defaults voor nieuwe velden
                for key, val in _DEFAULT_CONFIG.items():
                    if key not in data:
                        data[key] = val
                    elif isinstance(val, dict):
                        for sk, sv in val.items():
                            if sk not in data[key]:
                                data[key][sk] = sv
                # Verifieer integriteit
                self._verifieer_hash(data)
                return data
            except (json.JSONDecodeError, IOError):
                pass

        # Eerste keer: schrijf defaults
        self._schrijf(_DEFAULT_CONFIG)
        return dict(_DEFAULT_CONFIG)

    def _schrijf(self, data: dict):
        """Schrijf config naar bestand."""
        with open(
            self._pad, "w", encoding="utf-8"
        ) as f:
            json.dump(
                data, f, indent=2, ensure_ascii=False
            )
        self._schrijf_hash(data)

    def opslaan(self):
        """Sla huidige config op."""
        self._schrijf(self._data)

    # -- Config integriteits-hash --

    def _bereken_hash(self, data: dict) -> str:
        """Bereken SHA256 hash van config data."""
        inhoud = json.dumps(
            data, sort_keys=True, ensure_ascii=False
        )
        return hashlib.sha256(
            inhoud.encode("utf-8")
        ).hexdigest()

    def _schrijf_hash(self, data: dict):
        """Sla config hash op naar apart bestand."""
        try:
            h = self._bereken_hash(data)
            with open(
                _CONFIG_HASH_PAD, "w", encoding="utf-8"
            ) as f:
                f.write(h)
        except Exception as e:
            logger.debug("Config hash schrijven failed: %s", e)

    def _verifieer_hash(self, data: dict):
        """Controleer of config niet extern gewijzigd is."""
        if not _CONFIG_HASH_PAD.exists():
            # Eerste keer, maak hash aan
            self._schrijf_hash(data)
            return
        try:
            with open(
                _CONFIG_HASH_PAD, "r", encoding="utf-8"
            ) as f:
                opgeslagen = f.read().strip()
            huidige = self._bereken_hash(data)
            if opgeslagen != huidige:
                self._hash_gewijzigd = True
                print(kleur(
                    "  WAARSCHUWING: security_config.json"
                    " is extern gewijzigd!",
                    Kleur.FEL_ROOD,
                ))
                print(kleur(
                    "  Gebruik 'hash' commando om te"
                    " herberekenen na verificatie.",
                    Kleur.FEL_GEEL,
                ))
            else:
                self._hash_gewijzigd = False
        except Exception as e:
            logger.debug("Config hash verificatie failed: %s", e)
            self._hash_gewijzigd = False

    def herbereken_hash(self):
        """Herbereken en sla config hash op."""
        self._schrijf_hash(self._data)
        self._hash_gewijzigd = False
        print(kleur(
            "  Config hash herberekend.",
            Kleur.FEL_GROEN,
        ))

    @property
    def wallets(self) -> dict:
        return self._data.get("wallets", {})

    @property
    def watchlist(self) -> list:
        return self._data.get("watchlist", [])

    @property
    def drempels(self) -> dict:
        return self._data.get("drempels", {})

    @property
    def audit_bestanden(self) -> list:
        return self._data.get("audit_bestanden", [])

    def heeft_wallets(self) -> bool:
        """Check of er wallet adressen geconfigureerd zijn."""
        for chain, adressen in self.wallets.items():
            if adressen:
                return True
        return False

    def toon(self):
        """Toon huidige configuratie."""
        print(kleur(
            "\n  SECURITY CONFIG",
            Kleur.FEL_CYAAN,
        ))
        print(kleur(
            f"  Bestand: {self._pad}",
            Kleur.DIM,
        ))

        # Wallets
        print(kleur(
            "\n  Wallets:", Kleur.FEL_GEEL,
        ))
        for chain, adressen in self.wallets.items():
            if adressen:
                for adres in adressen:
                    print(f"    {chain.upper()}: "
                          f"{_scrub_adres(adres)}")
            else:
                print(kleur(
                    f"    {chain.upper()}: (niet ingesteld)",
                    Kleur.DIM,
                ))

        # Watchlist
        print(kleur(
            f"\n  Watchlist: "
            f"{', '.join(self.watchlist)}",
            Kleur.FEL_GEEL,
        ))

        # Drempels
        dr = self.drempels
        print(kleur(
            "\n  Drempels:", Kleur.FEL_GEEL,
        ))
        print(f"    Daling alert:  "
              f"{dr.get('prijs_daling_pct', 5)}%")
        print(f"    Stijging alert: "
              f"{dr.get('stijging_pct', 10)}%")
        print(f"    Whale alert:   "
              f"${dr.get('whale_alert_usd', 100000):,}")

        print()
