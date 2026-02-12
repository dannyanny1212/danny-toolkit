"""
Security & Crypto Research Engine v2.0

Automatische beveiligingsscanner voor:
1. Wallet monitoring + balance tracking (BTC/ETH/SOL)
2. Markt & portfolio (prijzen, crashes, whale alerts)
3. Code security audit (18 patronen, inclusief C2/mining)
4. Systeem integriteit (FileGuard, Governor, Coherentie)
5. RAG research (CVE/exploit/hack zoeken in ChromaDB)
6. Forensische diepte-scan (velocity, contracten)
7. Config integriteits-verificatie (SHA256 hash)

Draait elk uur via HeartbeatDaemon of handmatig via
launcher app 57 / sneltoets 'sr'.

Wallet adressen staan in data/security_config.json
(NOOIT in code, NOOIT gecommit).
"""

import json
import os
import re
import sys
import time
import hashlib
from datetime import datetime
from pathlib import Path

if os.name == "nt":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

from ..core.config import Config
from ..core.utils import kleur, Kleur


# ── Config pad ────────────────────────────────────────

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
        "swarm_engine.py",
    ],
}


# ── Ernst niveaus ─────────────────────────────────────

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


# ══════════════════════════════════════════════════════
# SecurityConfig
# ══════════════════════════════════════════════════════

class SecurityConfig:
    """Laadt en beheert security configuratie.

    Config bestand: data/security_config.json
    Wordt automatisch aangemaakt met defaults.
    Danny vult zelf wallet adressen in.
    """

    def __init__(self):
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

    # ── Config integriteits-hash ──────────────────────

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
        except Exception:
            pass

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
        except Exception:
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


# ══════════════════════════════════════════════════════
# SecurityResearchEngine
# ══════════════════════════════════════════════════════

class SecurityResearchEngine:
    """Automatische security & crypto research engine.

    Draait 7 scans:
    1. scan_wallets()      — balance + transacties + tokens
    2. scan_markt()        — prijzen + alerts
    3. scan_code_audit()   — 18 regex patronen
    4. scan_systeem()      — FileGuard + Governor + Coherentie
    5. scan_rag_research() — CVE/exploit in RAG + Stack
    6. scan_forensisch()   — velocity + contracten
    7. volledig_rapport()  — alles gecombineerd
    """

    VERSION = "2.0.0"

    # Code audit patronen (uitgebreid van SentinelValidator)
    _AUDIT_PATRONEN = [
        (Ernst.KRITIEK, "private_key",
         r"(?i)(private[_\s]?key|secret[_\s]?key|seed[_\s]?"
         r"phrase)\s*[=:]\s*['\"][^'\"]{10,}"),
        (Ernst.KRITIEK, "hardcoded_api_key",
         r"(?i)(api[_\s]?key|token|bearer)\s*[=:]\s*"
         r"['\"][A-Za-z0-9_\-]{20,}['\"]"),
        (Ernst.HOOG, "eval_exec",
         r"\b(eval|exec)\s*\("),
        (Ernst.HOOG, "shell_true",
         r"subprocess\.(?:call|run|Popen)\s*\("
         r".*shell\s*=\s*True"),
        (Ernst.HOOG, "os_system",
         r"\bos\.system\s*\("),
        (Ernst.MEDIUM, "http_url",
         r"['\"]http://[^'\"]+['\"]"),
        (Ernst.MEDIUM, "rm_rf",
         r"\brm\s+-rf\b"),
        (Ernst.MEDIUM, "shutil_rmtree",
         r"\bshutil\.rmtree\s*\("),
        (Ernst.LAAG, "import_dunder",
         r"\b__import__\s*\("),
        (Ernst.LAAG, "open_write",
         r"\bopen\s*\(.*['\"]w['\"]\s*\)"),
        # v2.0 — forensische patronen
        (Ernst.KRITIEK, "hardcoded_wallet",
         r"0x[a-fA-F0-9]{40}"),
        (Ernst.KRITIEK, "base64_secret",
         r"base64\.(b64)?decode\s*\("),
        (Ernst.HOOG, "c2_callback",
         r"requests\.(get|post)\s*\(.*"
         r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}"),
        (Ernst.HOOG, "reverse_shell",
         r"socket\.socket\s*\(.*SOCK_STREAM"),
        (Ernst.HOOG, "crypto_mining",
         r"(stratum|mining[_\-]?pool|hashrate)"),
        (Ernst.MEDIUM, "dns_exfil",
         r"socket\.gethost(byname|name)\s*\("),
        (Ernst.MEDIUM, "pickle_load",
         r"pickle\.loads?\s*\("),
        (Ernst.LAAG, "temp_file_write",
         r"tempfile\.(Named)?Temp"),
    ]

    # RAG zoektermen
    _RAG_ZOEKTERMEN = [
        "CVE", "exploit", "hack", "vulnerability",
        "kwetsbaarheid", "aanval", "breach", "malware",
    ]

    def __init__(self, brain=None, daemon=None):
        self._brain = brain
        self._daemon = daemon
        self._governor = None
        self._stack = None
        self._file_guard = None
        self._coherentie = None
        self.config = SecurityConfig()
        self._alerts = []
        self._eth_tx_cache = {}

    # ── Lazy properties ───────────────────────────────

    @property
    def governor(self):
        if self._governor is None:
            try:
                from .governor import OmegaGovernor
                self._governor = OmegaGovernor()
            except Exception:
                pass
        return self._governor

    @property
    def stack(self):
        if self._stack is None:
            try:
                from .cortical_stack import (
                    get_cortical_stack,
                )
                self._stack = get_cortical_stack()
            except Exception:
                pass
        return self._stack

    @property
    def file_guard(self):
        if self._file_guard is None:
            try:
                from .file_guard import FileGuard
                self._file_guard = FileGuard()
            except Exception:
                pass
        return self._file_guard

    @property
    def coherentie(self):
        if self._coherentie is None:
            try:
                from ..daemon.coherentie import (
                    CoherentieMonitor,
                )
                self._coherentie = CoherentieMonitor()
            except Exception:
                pass
        return self._coherentie

    # ══════════════════════════════════════════════════
    # SCAN 1: Wallets
    # ══════════════════════════════════════════════════

    def scan_wallets(self) -> dict:
        """Check balance, transacties en tokens per wallet.

        Gebruikt gratis API's:
        - BTC: Blockstream.info
        - ETH: Blockscout.com (balance + tokens)
        - SOL: Solscan.io (public)

        Returns:
            dict met "bevindingen", "balances",
            "gescand", "fouten".
        """
        bevindingen = []
        balances = {}
        gescand = 0
        fouten = []
        whale_drempel_eth = self.config.drempels.get(
            "whale_alert_eth", 10.0
        )

        if not HAS_REQUESTS:
            fouten.append("requests niet geinstalleerd")
            return {
                "bevindingen": bevindingen,
                "balances": balances,
                "gescand": gescand,
                "fouten": fouten,
            }

        wallets = self.config.wallets

        # BTC wallets via Blockstream
        for adres in wallets.get("btc", []):
            gescand += 1
            scrub = _scrub_adres(adres)

            # Balance check
            try:
                bal_url = (
                    "https://blockstream.info/api"
                    f"/address/{adres}"
                )
                bal_data = _fetch_json(bal_url)
                if bal_data and isinstance(
                    bal_data, dict
                ):
                    cs = bal_data.get(
                        "chain_stats", {}
                    )
                    funded = cs.get(
                        "funded_txo_sum", 0
                    )
                    spent = cs.get(
                        "spent_txo_sum", 0
                    )
                    btc_bal = (funded - spent) / 1e8
                    balances[scrub] = {
                        "chain": "BTC",
                        "balance": round(
                            btc_bal, 8
                        ),
                        "unit": "BTC",
                    }
            except Exception:
                pass

            # Transacties
            try:
                url = (
                    "https://blockstream.info/api"
                    f"/address/{adres}/txs/recent"
                )
                data = _fetch_json(url)
                if data and isinstance(data, list):
                    for tx in data[:5]:
                        bevindingen.append({
                            "ernst": Ernst.MEDIUM,
                            "type": "btc_transactie",
                            "adres": scrub,
                            "txid": tx.get(
                                "txid", "?"
                            )[:16] + "...",
                            "status": (
                                "bevestigd"
                                if tx.get(
                                    "status", {}
                                ).get("confirmed")
                                else "onbevestigd"
                            ),
                        })
            except Exception as e:
                fouten.append(
                    f"BTC {scrub}: {str(e)[:60]}"
                )

        # ETH wallets via Blockscout
        for adres in wallets.get("eth", []):
            gescand += 1
            scrub = _scrub_adres(adres)
            adres_lower = adres.lower()

            # Balance check
            try:
                bal_url = (
                    "https://eth.blockscout.com/api"
                    f"/v2/addresses/{adres}"
                )
                bal_data = _fetch_json(bal_url)
                if bal_data and isinstance(
                    bal_data, dict
                ):
                    raw = bal_data.get(
                        "coin_balance", "0"
                    )
                    eth_bal = int(raw) / 1e18
                    balances[scrub] = {
                        "chain": "ETH",
                        "balance": round(eth_bal, 6),
                        "unit": "ETH",
                    }
            except Exception:
                pass

            # Transacties met richting
            try:
                url = (
                    "https://eth.blockscout.com/api"
                    "/v2/addresses"
                    f"/{adres}/transactions"
                )
                data = _fetch_json(url)
                # Cache voor scan_forensisch
                if data:
                    self._eth_tx_cache[adres] = data
                if data and isinstance(data, dict):
                    items = data.get("items", [])
                    for tx in items[:5]:
                        waarde_raw = tx.get(
                            "value", "0"
                        )
                        try:
                            waarde_eth = (
                                int(waarde_raw) / 1e18
                            )
                        except (ValueError, TypeError):
                            waarde_eth = 0.0

                        # Richting bepalen
                        tx_from = tx.get(
                            "from", {}
                        )
                        if isinstance(tx_from, dict):
                            from_addr = tx_from.get(
                                "hash", ""
                            ).lower()
                        else:
                            from_addr = str(
                                tx_from
                            ).lower()

                        richting = (
                            "OUT"
                            if from_addr == adres_lower
                            else "IN"
                        )

                        ernst = Ernst.MEDIUM
                        # Whale alert
                        if waarde_eth > whale_drempel_eth:
                            ernst = Ernst.HOOG

                        bevindingen.append({
                            "ernst": ernst,
                            "type": "eth_transactie",
                            "adres": scrub,
                            "hash": tx.get(
                                "hash", "?"
                            )[:16] + "...",
                            "waarde_eth": round(
                                waarde_eth, 6
                            ),
                            "richting": richting,
                        })
            except Exception as e:
                fouten.append(
                    f"ETH {scrub}: {str(e)[:60]}"
                )

            # Token transfers
            try:
                tok_url = (
                    "https://eth.blockscout.com/api"
                    "/v2/addresses"
                    f"/{adres}/token-transfers"
                    "?type=ERC-20"
                )
                tok_data = _fetch_json(tok_url)
                if tok_data and isinstance(
                    tok_data, dict
                ):
                    tok_items = tok_data.get(
                        "items", []
                    )
                    for tok in tok_items[:5]:
                        token_info = tok.get(
                            "token", {}
                        )
                        symbool = token_info.get(
                            "symbol", "?"
                        )
                        tok_from = tok.get(
                            "from", {}
                        )
                        if isinstance(tok_from, dict):
                            tf_addr = tok_from.get(
                                "hash", ""
                            ).lower()
                        else:
                            tf_addr = str(
                                tok_from
                            ).lower()
                        tok_richting = (
                            "OUT"
                            if tf_addr == adres_lower
                            else "IN"
                        )
                        bevindingen.append({
                            "ernst": Ernst.MEDIUM,
                            "type": "eth_token",
                            "adres": scrub,
                            "token": symbool,
                            "richting": tok_richting,
                        })
            except Exception:
                pass  # Token transfers zijn optioneel

        # SOL wallets via Solscan
        for adres in wallets.get("sol", []):
            gescand += 1
            scrub = _scrub_adres(adres)
            try:
                url = (
                    "https://api.solscan.io"
                    f"/v2/account/transfer"
                    f"?address={adres}&page=1"
                    f"&page_size=5"
                )
                data = _fetch_json(url)
                if data and isinstance(data, dict):
                    items = data.get("data", [])
                    for tx in items[:5]:
                        bevindingen.append({
                            "ernst": Ernst.MEDIUM,
                            "type": "sol_transactie",
                            "adres": scrub,
                            "signature": str(
                                tx.get(
                                    "signature", "?"
                                )
                            )[:16] + "...",
                        })
            except Exception as e:
                fouten.append(
                    f"SOL {scrub}: {str(e)[:60]}"
                )

        return {
            "bevindingen": bevindingen,
            "balances": balances,
            "gescand": gescand,
            "fouten": fouten,
        }

    # ══════════════════════════════════════════════════
    # SCAN 2: Markt
    # ══════════════════════════════════════════════════

    def scan_markt(self) -> dict:
        """Check prijzen en genereer alerts bij drempels.

        Gebruikt CoinGecko gratis API.

        Returns:
            dict met "prijzen", "alerts", "fouten".
        """
        prijzen = {}
        alerts = []
        fouten = []

        if not HAS_REQUESTS:
            fouten.append("requests niet geinstalleerd")
            return {
                "prijzen": prijzen,
                "alerts": alerts,
                "fouten": fouten,
            }

        watchlist = self.config.watchlist
        if not watchlist:
            return {
                "prijzen": prijzen,
                "alerts": alerts,
                "fouten": fouten,
            }

        ids = ",".join(watchlist)
        url = (
            "https://api.coingecko.com/api/v3"
            "/simple/price"
            f"?ids={ids}"
            "&vs_currencies=usd"
            "&include_24hr_change=true"
        )

        try:
            data = _fetch_json(url)
            if not data or not isinstance(data, dict):
                fouten.append("Geen data van CoinGecko")
                return {
                    "prijzen": prijzen,
                    "alerts": alerts,
                    "fouten": fouten,
                }

            drempels = self.config.drempels
            daling_pct = drempels.get(
                "prijs_daling_pct", 5.0
            )
            stijging_pct = drempels.get(
                "stijging_pct", 10.0
            )

            for coin_id, info in data.items():
                prijs = info.get("usd", 0)
                change = info.get(
                    "usd_24h_change", 0
                ) or 0

                prijzen[coin_id] = {
                    "prijs_usd": prijs,
                    "change_24h": round(change, 2),
                }

                # Check drempels
                if change <= -daling_pct:
                    alerts.append({
                        "ernst": Ernst.HOOG,
                        "type": "prijs_daling",
                        "coin": coin_id,
                        "change": round(change, 2),
                        "prijs": prijs,
                    })
                elif change >= stijging_pct:
                    alerts.append({
                        "ernst": Ernst.MEDIUM,
                        "type": "prijs_stijging",
                        "coin": coin_id,
                        "change": round(change, 2),
                        "prijs": prijs,
                    })

        except Exception as e:
            fouten.append(
                f"CoinGecko: {str(e)[:60]}"
            )

        return {
            "prijzen": prijzen,
            "alerts": alerts,
            "fouten": fouten,
        }

    # ══════════════════════════════════════════════════
    # SCAN 3: Code Audit
    # ══════════════════════════════════════════════════

    def scan_code_audit(self) -> dict:
        """Regex scan op gevaarlijke patronen in code.

        Scant de bestanden uit audit_bestanden config.
        Hergebruikt en breidt SentinelValidator patronen uit.

        Returns:
            dict met "bevindingen", "gescand", "fouten".
        """
        bevindingen = []
        gescand = 0
        fouten = []

        repo_root = Config.BASE_DIR
        bestanden = self.config.audit_bestanden

        for rel_pad in bestanden:
            absoluut = repo_root / rel_pad
            if not absoluut.is_file():
                fouten.append(
                    f"Bestand niet gevonden: {rel_pad}"
                )
                continue

            gescand += 1
            try:
                with open(
                    absoluut, "r", encoding="utf-8"
                ) as f:
                    inhoud = f.read()

                regels = inhoud.split("\n")
                for ernst, naam, patroon in (
                    self._AUDIT_PATRONEN
                ):
                    for i, regel in enumerate(regels, 1):
                        # Skip commentaarregels
                        stripped = regel.strip()
                        if stripped.startswith("#"):
                            continue

                        if re.search(patroon, regel):
                            bevindingen.append({
                                "ernst": ernst,
                                "type": naam,
                                "bestand": rel_pad,
                                "regel": i,
                                "tekst": stripped[:80],
                            })

            except Exception as e:
                fouten.append(
                    f"{rel_pad}: {str(e)[:60]}"
                )

        return {
            "bevindingen": bevindingen,
            "gescand": gescand,
            "fouten": fouten,
        }

    # ══════════════════════════════════════════════════
    # SCAN 4: Systeem
    # ══════════════════════════════════════════════════

    def scan_systeem(self) -> dict:
        """Check FileGuard, Governor health, CoherentieMonitor.

        Returns:
            dict met "file_guard", "governor", "coherentie",
            "bevindingen".
        """
        bevindingen = []
        result = {
            "file_guard": None,
            "governor": None,
            "coherentie": None,
            "bevindingen": bevindingen,
        }

        # FileGuard
        fg = self.file_guard
        if fg:
            try:
                rapport = fg.controleer_integriteit()
                result["file_guard"] = rapport

                if rapport["status"] == "KRITIEK":
                    bevindingen.append({
                        "ernst": Ernst.KRITIEK,
                        "type": "file_guard_kritiek",
                        "ontbrekend": len(
                            rapport["ontbrekend"]
                        ),
                    })
                elif rapport["status"] == "WAARSCHUWING":
                    bevindingen.append({
                        "ernst": Ernst.HOOG,
                        "type": "file_guard_waarschuwing",
                        "ontbrekend": len(
                            rapport["ontbrekend"]
                        ),
                    })
            except Exception:
                result["file_guard"] = {"status": "FOUT"}

        # Governor
        gov = self.governor
        if gov:
            try:
                health = gov.get_health_report()
                result["governor"] = health

                cb_status = health.get(
                    "circuit_breaker", {}
                ).get("status", "CLOSED")
                if cb_status == "OPEN":
                    bevindingen.append({
                        "ernst": Ernst.HOOG,
                        "type": "circuit_breaker_open",
                        "failures": health.get(
                            "circuit_breaker", {}
                        ).get("failures", 0),
                    })
            except Exception:
                result["governor"] = {"status": "FOUT"}

        # CoherentieMonitor — actieve scan
        coh = self.coherentie
        if coh:
            try:
                scan_result = coh.scan(
                    samples=10, interval=0.3
                )
                result["coherentie"] = scan_result
                verdict = scan_result.get(
                    "verdict", "PASS"
                )
                if verdict == "ALARM":
                    bevindingen.append({
                        "ernst": Ernst.KRITIEK,
                        "type": "gpu_misbruik",
                        "details": scan_result.get(
                            "details", ""
                        )[:80],
                        "correlatie": scan_result.get(
                            "correlatie", 0
                        ),
                    })
                elif verdict == "WAARSCHUWING":
                    bevindingen.append({
                        "ernst": Ernst.HOOG,
                        "type": "gpu_anomalie",
                        "details": scan_result.get(
                            "details", ""
                        )[:80],
                        "correlatie": scan_result.get(
                            "correlatie", 0
                        ),
                    })
            except Exception:
                result["coherentie"] = {"status": "FOUT"}

        return result

    # ══════════════════════════════════════════════════
    # SCAN 5: RAG Research
    # ══════════════════════════════════════════════════

    def scan_rag_research(self) -> dict:
        """Zoek dreigings-termen in ChromaDB + CorticalStack.

        Returns:
            dict met "chromadb_hits", "stack_hits",
            "fouten".
        """
        chromadb_hits = []
        stack_hits = []
        fouten = []

        # ChromaDB search
        try:
            from ..ai.production_rag import ProductionRAG
            rag = ProductionRAG()
            if hasattr(rag, "zoek") or hasattr(rag, "search"):
                for term in self._RAG_ZOEKTERMEN[:4]:
                    try:
                        if hasattr(rag, "zoek"):
                            resultaten = rag.zoek(term, k=3)
                        else:
                            resultaten = rag.search(
                                term, k=3
                            )
                        if resultaten:
                            for r in resultaten:
                                tekst = str(r)[:120]
                                chromadb_hits.append({
                                    "term": term,
                                    "tekst": tekst,
                                })
                    except Exception:
                        pass
        except Exception as e:
            fouten.append(
                f"ChromaDB: {str(e)[:60]}"
            )

        # CorticalStack search (episodic + semantic)
        stk = self.stack
        if stk:
            try:
                for term in self._RAG_ZOEKTERMEN[:4]:
                    try:
                        # Episodic: zoek events
                        events = stk.search_events(
                            term, limit=3
                        )
                        for ev in (events or []):
                            stack_hits.append({
                                "term": term,
                                "tekst": str(ev)[:120],
                            })
                        # Semantic: zoek feiten
                        feiten = stk.recall_all(
                            prefix=term,
                            min_confidence=0.0,
                        )
                        for f in (feiten or []):
                            stack_hits.append({
                                "term": term,
                                "tekst": str(f)[:120],
                            })
                    except Exception:
                        pass
            except Exception as e:
                fouten.append(
                    f"CorticalStack: {str(e)[:60]}"
                )

        return {
            "chromadb_hits": chromadb_hits,
            "stack_hits": stack_hits,
            "fouten": fouten,
        }

    # ══════════════════════════════════════════════════
    # SCAN 6: Forensisch
    # ══════════════════════════════════════════════════

    def scan_forensisch(self) -> dict:
        """Forensische diepte-scan op gemonitorde wallets.

        Controleert:
        - Transactie velocity (>5 tx/uur = alert)
        - Contract interacties (unverified = alert)
        - Verdachte patronen in transactiegeschiedenis

        Returns:
            dict met "bevindingen", "details", "fouten".
        """
        bevindingen = []
        details = {}
        fouten = []

        if not HAS_REQUESTS:
            fouten.append("requests niet geinstalleerd")
            return {
                "bevindingen": bevindingen,
                "details": details,
                "fouten": fouten,
            }

        wallets = self.config.wallets

        for adres in wallets.get("eth", []):
            scrub = _scrub_adres(adres)

            # Transactie velocity check
            try:
                cached = self._eth_tx_cache.get(adres)
                if cached:
                    data = cached
                else:
                    url = (
                        "https://eth.blockscout.com"
                        "/api/v2/addresses"
                        f"/{adres}/transactions"
                        "?limit=50"
                    )
                    data = _fetch_json(url)
                if data and isinstance(data, dict):
                    items = data.get("items", [])
                    if items:
                        # Check timestamps
                        timestamps = []
                        for tx in items:
                            ts = tx.get("timestamp")
                            if ts:
                                timestamps.append(ts)

                        details[scrub] = {
                            "totaal_tx": len(items),
                            "contract_tx": 0,
                        }

                        # Velocity: tel tx in
                        # laatste uur (als timestamps)
                        if len(timestamps) >= 2:
                            try:
                                nieuwste = datetime.fromisoformat(
                                    timestamps[0].replace(
                                        "Z", "+00:00"
                                    )
                                )
                                tx_laatste_uur = 0
                                for ts in timestamps:
                                    t = datetime.fromisoformat(
                                        ts.replace(
                                            "Z",
                                            "+00:00",
                                        )
                                    )
                                    delta = (
                                        nieuwste - t
                                    )
                                    if (
                                        delta.total_seconds()
                                        <= 3600
                                    ):
                                        tx_laatste_uur += 1
                                if tx_laatste_uur > 5:
                                    bevindingen.append({
                                        "ernst": Ernst.HOOG,
                                        "type":
                                            "hoge_tx_velocity",
                                        "adres": scrub,
                                        "tx_per_uur":
                                            tx_laatste_uur,
                                    })
                                details[scrub][
                                    "tx_laatste_uur"
                                ] = tx_laatste_uur
                            except Exception:
                                pass

                        # Contract interacties
                        contract_count = 0
                        for tx in items:
                            to_info = tx.get("to", {})
                            if isinstance(
                                to_info, dict
                            ):
                                is_contract = to_info.get(
                                    "is_contract",
                                    False,
                                )
                                is_verified = to_info.get(
                                    "is_verified",
                                    True,
                                )
                                if is_contract:
                                    contract_count += 1
                                    if not is_verified:
                                        bevindingen.append({
                                            "ernst":
                                                Ernst.HOOG,
                                            "type":
                                                "unverified"
                                                "_contract",
                                            "adres": scrub,
                                            "contract":
                                                _scrub_adres(
                                                    to_info.get(
                                                        "hash",
                                                        "?"
                                                    )
                                                ),
                                        })
                        details[scrub][
                            "contract_tx"
                        ] = contract_count

            except Exception as e:
                fouten.append(
                    f"Forensisch ETH {scrub}: "
                    f"{str(e)[:60]}"
                )

        return {
            "bevindingen": bevindingen,
            "details": details,
            "fouten": fouten,
        }

    # ══════════════════════════════════════════════════
    # VOLLEDIG RAPPORT
    # ══════════════════════════════════════════════════

    def volledig_rapport(self) -> dict:
        """Orchestrator: draai alle 7 scans.

        Returns:
            dict met alle scan resultaten + metadata.
        """
        start = time.time()
        self._eth_tx_cache = {}

        wallet_result = self.scan_wallets()

        rapport = {
            "timestamp": datetime.now().isoformat(),
            "versie": self.VERSION,
            "wallets": wallet_result,
            "markt": self.scan_markt(),
            "code_audit": self.scan_code_audit(),
            "systeem": self.scan_systeem(),
            "rag_research": self.scan_rag_research(),
            "forensisch": self.scan_forensisch(),
            "duur_seconden": 0,
            "totaal_bevindingen": 0,
            "hoogste_ernst": Ernst.LAAG,
        }

        self._eth_tx_cache = {}

        rapport["duur_seconden"] = round(
            time.time() - start, 2
        )

        # Tel bevindingen en bepaal hoogste ernst
        alle_bevindingen = []
        alle_bevindingen.extend(
            rapport["wallets"].get("bevindingen", [])
        )
        alle_bevindingen.extend(
            rapport["markt"].get("alerts", [])
        )
        alle_bevindingen.extend(
            rapport["code_audit"].get("bevindingen", [])
        )
        alle_bevindingen.extend(
            rapport["systeem"].get("bevindingen", [])
        )
        alle_bevindingen.extend(
            rapport["forensisch"].get(
                "bevindingen", []
            )
        )

        rapport["totaal_bevindingen"] = len(
            alle_bevindingen
        )

        ernst_prio = [
            Ernst.KRITIEK, Ernst.HOOG,
            Ernst.MEDIUM, Ernst.LAAG,
        ]
        for e in ernst_prio:
            if any(
                b.get("ernst") == e
                for b in alle_bevindingen
            ):
                rapport["hoogste_ernst"] = e
                break

        # Log naar CorticalStack
        self._log_scan(rapport)

        # Bewaar kritieke alerts
        for b in alle_bevindingen:
            if b.get("ernst") in (
                Ernst.KRITIEK, Ernst.HOOG
            ):
                self._bewaar_alert(b)

        return rapport

    # ══════════════════════════════════════════════════
    # DISPLAY
    # ══════════════════════════════════════════════════

    def toon_rapport(self, rapport=None):
        """Toon visueel rapport (zelfde stijl als FileGuard)."""
        if rapport is None:
            rapport = self.volledig_rapport()

        hoogste = rapport.get(
            "hoogste_ernst", Ernst.LAAG
        )
        status_kleur = _ERNST_KLEUR.get(
            hoogste, Kleur.DIM
        )

        print()
        print(kleur(
            "  ══════════════════════════════════════",
            Kleur.CYAAN,
        ))
        print(kleur(
            "  SECURITY RESEARCH ENGINE"
            f" v{self.VERSION}",
            Kleur.FEL_CYAAN,
        ))
        print(kleur(
            "  ══════════════════════════════════════",
            Kleur.CYAAN,
        ))

        print(kleur(
            f"\n  Status: {hoogste}",
            status_kleur,
        ))
        print(kleur(
            f"  Bevindingen: "
            f"{rapport['totaal_bevindingen']}",
            Kleur.DIM,
        ))
        print(kleur(
            f"  Duur: {rapport['duur_seconden']}s",
            Kleur.DIM,
        ))
        print(kleur(
            f"  Tijd: {rapport['timestamp']}",
            Kleur.DIM,
        ))

        # ── Wallets ──
        w = rapport.get("wallets", {})
        w_bev = w.get("bevindingen", [])
        w_bal = w.get("balances", {})
        w_fouten = w.get("fouten", [])
        print(kleur(
            f"\n  WALLETS ({w.get('gescand', 0)}"
            f" gescand, {len(w_bev)} tx)",
            Kleur.FEL_GEEL,
        ))
        if not self.config.heeft_wallets():
            print(kleur(
                "    Geen wallets geconfigureerd."
                " Pas data/security_config.json aan.",
                Kleur.DIM,
            ))
        # Balances
        for adres, bal in w_bal.items():
            print(kleur(
                f"    {adres}: "
                f"{bal['balance']} {bal['unit']}",
                Kleur.FEL_CYAAN,
            ))
        for b in w_bev[:10]:
            ek = _ERNST_KLEUR.get(
                b["ernst"], Kleur.DIM
            )
            richting = b.get("richting", "")
            extra = ""
            if richting:
                extra = f" [{richting}]"
            if b.get("waarde_eth"):
                extra += (
                    f" {b['waarde_eth']} ETH"
                )
            print(kleur(
                f"    [{b['ernst']}] "
                f"{b['type']} {b.get('adres', '')}"
                f"{extra}",
                ek,
            ))
        for f_err in w_fouten[:3]:
            print(kleur(
                f"    [FOUT] {f_err}", Kleur.ROOD,
            ))

        # ── Markt ──
        m = rapport.get("markt", {})
        prijzen = m.get("prijzen", {})
        m_alerts = m.get("alerts", [])
        print(kleur(
            f"\n  MARKT ({len(prijzen)} coins,"
            f" {len(m_alerts)} alerts)",
            Kleur.FEL_GEEL,
        ))
        for coin_id, info in prijzen.items():
            prijs = info.get("prijs_usd", 0)
            change = info.get("change_24h", 0)
            change_kleur = (
                Kleur.FEL_GROEN if change >= 0
                else Kleur.FEL_ROOD
            )
            teken = "+" if change >= 0 else ""
            print(
                f"    {coin_id:>12}: "
                f"${prijs:>10,.2f}  "
                + kleur(
                    f"{teken}{change}%",
                    change_kleur,
                )
            )
        for a in m_alerts:
            ek = _ERNST_KLEUR.get(
                a["ernst"], Kleur.DIM
            )
            print(kleur(
                f"    [{a['ernst']}] "
                f"{a['type']}: {a['coin']} "
                f"({a.get('change', 0)}%)",
                ek,
            ))

        # ── Code Audit ──
        ca = rapport.get("code_audit", {})
        ca_bev = ca.get("bevindingen", [])
        print(kleur(
            f"\n  CODE AUDIT ({ca.get('gescand', 0)}"
            f" bestanden, {len(ca_bev)} bevindingen)",
            Kleur.FEL_GEEL,
        ))
        if not ca_bev:
            print(kleur(
                "    Geen gevaarlijke patronen gevonden.",
                Kleur.FEL_GROEN,
            ))
        for b in ca_bev[:15]:
            ek = _ERNST_KLEUR.get(
                b["ernst"], Kleur.DIM
            )
            print(kleur(
                f"    [{b['ernst']}] "
                f"{b['bestand']}:{b['regel']} "
                f"— {b['type']}",
                ek,
            ))
        for f_err in ca.get("fouten", [])[:3]:
            print(kleur(
                f"    [FOUT] {f_err}", Kleur.ROOD,
            ))

        # ── Systeem ──
        s = rapport.get("systeem", {})
        s_bev = s.get("bevindingen", [])
        print(kleur(
            f"\n  SYSTEEM ({len(s_bev)} bevindingen)",
            Kleur.FEL_GEEL,
        ))

        # FileGuard
        fg = s.get("file_guard")
        if fg:
            fg_status = fg.get("status", "?")
            fg_kleur = (
                Kleur.FEL_GROEN if fg_status == "OK"
                else Kleur.FEL_ROOD
            )
            print(kleur(
                f"    FileGuard: {fg_status}",
                fg_kleur,
            ))
        else:
            print(kleur(
                "    FileGuard: niet beschikbaar",
                Kleur.DIM,
            ))

        # Governor
        gov = s.get("governor")
        if gov:
            cb = gov.get("circuit_breaker", {})
            cb_status = cb.get("status", "?")
            cb_kleur = (
                Kleur.FEL_GROEN
                if cb_status == "CLOSED"
                else Kleur.FEL_ROOD
            )
            print(kleur(
                f"    Governor: Circuit Breaker"
                f" {cb_status}",
                cb_kleur,
            ))
        else:
            print(kleur(
                "    Governor: niet beschikbaar",
                Kleur.DIM,
            ))

        # Coherentie
        coh = s.get("coherentie")
        if coh and isinstance(coh, dict):
            verdict = coh.get("verdict", "?")
            if verdict == "ALARM":
                v_kleur = Kleur.FEL_ROOD
            elif verdict == "WAARSCHUWING":
                v_kleur = Kleur.FEL_GEEL
            else:
                v_kleur = Kleur.FEL_GROEN
            corr = coh.get("correlatie", "?")
            print(kleur(
                f"    Coherentie: {verdict}"
                f" (r={corr})",
                v_kleur,
            ))
        else:
            print(kleur(
                "    Coherentie: niet beschikbaar",
                Kleur.DIM,
            ))

        for b in s_bev:
            ek = _ERNST_KLEUR.get(
                b["ernst"], Kleur.DIM
            )
            print(kleur(
                f"    [{b['ernst']}] {b['type']}",
                ek,
            ))

        # ── RAG Research ──
        r = rapport.get("rag_research", {})
        chroma = r.get("chromadb_hits", [])
        stack = r.get("stack_hits", [])
        print(kleur(
            f"\n  RAG RESEARCH ({len(chroma)} ChromaDB,"
            f" {len(stack)} Stack hits)",
            Kleur.FEL_GEEL,
        ))
        if not chroma and not stack:
            print(kleur(
                "    Geen dreigingen gevonden in RAG.",
                Kleur.FEL_GROEN,
            ))
        for h in (chroma + stack)[:8]:
            print(kleur(
                f"    [{h['term']}] "
                f"{h['tekst'][:80]}",
                Kleur.DIM,
            ))

        # ── Forensisch ──
        fr = rapport.get("forensisch", {})
        fr_bev = fr.get("bevindingen", [])
        fr_det = fr.get("details", {})
        print(kleur(
            f"\n  FORENSISCH ({len(fr_bev)}"
            f" bevindingen, {len(fr_det)} wallets)",
            Kleur.FEL_GEEL,
        ))
        if not fr_bev:
            print(kleur(
                "    Geen verdachte patronen.",
                Kleur.FEL_GROEN,
            ))
        for b in fr_bev[:10]:
            ek = _ERNST_KLEUR.get(
                b["ernst"], Kleur.DIM
            )
            print(kleur(
                f"    [{b['ernst']}] "
                f"{b['type']} {b.get('adres', '')}",
                ek,
            ))
        for adres, det in fr_det.items():
            tx_uur = det.get("tx_laatste_uur", "?")
            contr = det.get("contract_tx", 0)
            print(kleur(
                f"    {adres}: {tx_uur} tx/uur,"
                f" {contr} contract-interacties",
                Kleur.DIM,
            ))
        for f_err in fr.get("fouten", [])[:3]:
            print(kleur(
                f"    [FOUT] {f_err}", Kleur.ROOD,
            ))

        print()

    # ── Logging ───────────────────────────────────────

    def _log_scan(self, rapport):
        """Log scan resultaat naar CorticalStack."""
        stk = self.stack
        if stk is None:
            return
        try:
            stk.log_event(
                actor="security_research",
                action="scan_voltooid",
                details={
                    "bevindingen": rapport.get(
                        "totaal_bevindingen", 0
                    ),
                    "hoogste_ernst": rapport.get(
                        "hoogste_ernst", "LAAG"
                    ),
                    "duur": rapport.get(
                        "duur_seconden", 0
                    ),
                },
                source="security",
            )
        except Exception:
            pass

    def _bewaar_alert(self, bevinding):
        """Bewaar kritiek/hoog alert voor later."""
        self._alerts.append({
            "timestamp": datetime.now().isoformat(),
            **bevinding,
        })
        # Max 100 alerts in geheugen
        if len(self._alerts) > 100:
            self._alerts = self._alerts[-100:]

        # Log naar stack
        stk = self.stack
        if stk:
            try:
                stk.remember_fact(
                    f"security_alert_"
                    f"{len(self._alerts)}",
                    json.dumps(bevinding,
                               ensure_ascii=False),
                    confidence=0.8,
                )
            except Exception:
                pass

    def get_alerts(self) -> list:
        """Haal opgeslagen alerts op."""
        return list(self._alerts)

    def get_status(self) -> dict:
        """Haal engine status op."""
        hash_ok = not getattr(
            self.config, "_hash_gewijzigd", False
        )
        return {
            "versie": self.VERSION,
            "config_pad": str(self.config._pad),
            "config_hash": (
                "OK" if hash_ok else "GEWIJZIGD"
            ),
            "heeft_wallets": (
                self.config.heeft_wallets()
            ),
            "watchlist": self.config.watchlist,
            "alerts": len(self._alerts),
            "governor": (
                "beschikbaar"
                if self.governor else "niet geladen"
            ),
            "stack": (
                "beschikbaar"
                if self.stack else "niet geladen"
            ),
            "file_guard": (
                "beschikbaar"
                if self.file_guard
                else "niet geladen"
            ),
            "coherentie": (
                "beschikbaar"
                if self.coherentie
                else "niet geladen"
            ),
        }

    # ══════════════════════════════════════════════════
    # INTERACTIEVE CLI
    # ══════════════════════════════════════════════════

    def run(self):
        """Start de interactieve CLI."""
        print(kleur("""
+===============================================+
|                                               |
|     S E C U R I T Y   R E S E A R C H         |
|                                               |
|     Automatische Bewakings-Engine             |
|                                               |
+===============================================+
        """, Kleur.FEL_CYAAN))

        print(kleur("COMMANDO'S:", Kleur.GEEL))
        print("  scan        - Volledig rapport")
        print("  wallets     - Alleen wallet scan")
        print("  markt       - Alleen markt scan")
        print("  audit       - Alleen code audit")
        print("  systeem     - Alleen systeem scan")
        print("  research    - Alleen RAG research")
        print("  forensisch  - Forensische diepte-scan")
        print("  balance     - Wallet balances")
        print("  config      - Toon configuratie")
        print("  alerts      - Toon opgeslagen alerts")
        print("  hash        - Herbereken config hash")
        print("  status      - Engine status")
        print("  rapport     - Laatste volledig rapport")
        print("  stop        - Terug naar launcher")

        laatste_rapport = None

        while True:
            try:
                cmd = input(kleur(
                    "\n[SECURITY] > ",
                    Kleur.FEL_CYAAN,
                )).strip().lower()

                if not cmd:
                    continue

                if cmd in ("stop", "exit", "quit"):
                    break

                elif cmd == "scan":
                    print(kleur(
                        "  Scan bezig...",
                        Kleur.FEL_GEEL,
                    ))
                    laatste_rapport = (
                        self.volledig_rapport()
                    )
                    self.toon_rapport(laatste_rapport)

                elif cmd == "rapport":
                    if laatste_rapport:
                        self.toon_rapport(
                            laatste_rapport
                        )
                    else:
                        print(kleur(
                            "  Nog geen rapport."
                            " Gebruik 'scan' eerst.",
                            Kleur.DIM,
                        ))

                elif cmd == "wallets":
                    print(kleur(
                        "  Wallet scan...",
                        Kleur.FEL_GEEL,
                    ))
                    r = self.scan_wallets()
                    self._toon_wallet_resultaat(r)

                elif cmd == "markt":
                    print(kleur(
                        "  Markt scan...",
                        Kleur.FEL_GEEL,
                    ))
                    r = self.scan_markt()
                    self._toon_markt_resultaat(r)

                elif cmd == "audit":
                    print(kleur(
                        "  Code audit...",
                        Kleur.FEL_GEEL,
                    ))
                    r = self.scan_code_audit()
                    self._toon_audit_resultaat(r)

                elif cmd == "systeem":
                    print(kleur(
                        "  Systeem scan...",
                        Kleur.FEL_GEEL,
                    ))
                    r = self.scan_systeem()
                    self._toon_systeem_resultaat(r)

                elif cmd == "research":
                    print(kleur(
                        "  RAG research...",
                        Kleur.FEL_GEEL,
                    ))
                    r = self.scan_rag_research()
                    self._toon_rag_resultaat(r)

                elif cmd == "forensisch":
                    print(kleur(
                        "  Forensische scan...",
                        Kleur.FEL_GEEL,
                    ))
                    r = self.scan_forensisch()
                    self._toon_forensisch_resultaat(r)

                elif cmd == "balance":
                    print(kleur(
                        "  Balance check...",
                        Kleur.FEL_GEEL,
                    ))
                    r = self.scan_wallets()
                    self._toon_balance(r)

                elif cmd == "hash":
                    self.config.herbereken_hash()

                elif cmd == "config":
                    self.config.toon()

                elif cmd == "alerts":
                    self._toon_alerts()

                elif cmd == "status":
                    self._toon_status()

                else:
                    print(
                        f"  Onbekend commando: {cmd}"
                    )

            except (EOFError, KeyboardInterrupt):
                break

        print(kleur(
            "\n  Security Research gestopt.",
            Kleur.FEL_CYAAN,
        ))

    # ── CLI sub-displays ──────────────────────────────

    def _toon_wallet_resultaat(self, r):
        bev = r.get("bevindingen", [])
        bal = r.get("balances", {})
        print(kleur(
            f"\n  WALLETS: {r.get('gescand', 0)}"
            f" gescand, {len(bev)} transacties",
            Kleur.FEL_GEEL,
        ))
        for adres, b_info in bal.items():
            print(kleur(
                f"    {adres}: "
                f"{b_info['balance']} "
                f"{b_info['unit']}",
                Kleur.FEL_CYAAN,
            ))
        for b in bev[:10]:
            richting = b.get("richting", "")
            extra = ""
            if richting:
                extra = f" [{richting}]"
            if b.get("waarde_eth"):
                extra += f" {b['waarde_eth']} ETH"
            print(f"    {b['type']} "
                  f"{b.get('adres', '')}{extra}")
        for f_err in r.get("fouten", []):
            print(kleur(
                f"    [FOUT] {f_err}", Kleur.ROOD,
            ))
        if not bev and not r.get("fouten"):
            if self.config.heeft_wallets():
                print(kleur(
                    "    Geen recente transacties.",
                    Kleur.FEL_GROEN,
                ))
            else:
                print(kleur(
                    "    Geen wallets geconfigureerd.",
                    Kleur.DIM,
                ))

    def _toon_markt_resultaat(self, r):
        prijzen = r.get("prijzen", {})
        alerts = r.get("alerts", [])
        print(kleur(
            f"\n  MARKT: {len(prijzen)} coins",
            Kleur.FEL_GEEL,
        ))
        for coin_id, info in prijzen.items():
            prijs = info.get("prijs_usd", 0)
            change = info.get("change_24h", 0)
            teken = "+" if change >= 0 else ""
            ck = (
                Kleur.FEL_GROEN if change >= 0
                else Kleur.FEL_ROOD
            )
            print(
                f"    {coin_id:>12}: "
                f"${prijs:>10,.2f}  "
                + kleur(f"{teken}{change}%", ck)
            )
        for a in alerts:
            print(kleur(
                f"    [{a['ernst']}] "
                f"{a['coin']}: {a.get('change')}%",
                _ERNST_KLEUR.get(
                    a["ernst"], Kleur.DIM
                ),
            ))

    def _toon_audit_resultaat(self, r):
        bev = r.get("bevindingen", [])
        print(kleur(
            f"\n  CODE AUDIT: {r.get('gescand', 0)}"
            f" bestanden, {len(bev)} bevindingen",
            Kleur.FEL_GEEL,
        ))
        if not bev:
            print(kleur(
                "    Geen gevaarlijke patronen.",
                Kleur.FEL_GROEN,
            ))
        for b in bev[:20]:
            ek = _ERNST_KLEUR.get(
                b["ernst"], Kleur.DIM
            )
            print(kleur(
                f"    [{b['ernst']}] "
                f"{b['bestand']}:{b['regel']} "
                f"— {b['type']}",
                ek,
            ))

    def _toon_systeem_resultaat(self, r):
        print(kleur(
            "\n  SYSTEEM:", Kleur.FEL_GEEL,
        ))
        fg = r.get("file_guard")
        if fg:
            st = fg.get("status", "?")
            ck = (
                Kleur.FEL_GROEN if st == "OK"
                else Kleur.FEL_ROOD
            )
            print(kleur(
                f"    FileGuard: {st}", ck,
            ))
        gov = r.get("governor")
        if gov:
            cb = gov.get(
                "circuit_breaker", {}
            ).get("status", "?")
            ck = (
                Kleur.FEL_GROEN
                if cb == "CLOSED"
                else Kleur.FEL_ROOD
            )
            print(kleur(
                f"    Governor CB: {cb}", ck,
            ))
        coh = r.get("coherentie")
        if coh:
            verdict = coh.get("verdict", "?")
            ck = (
                Kleur.FEL_GROEN
                if verdict == "PASS"
                else Kleur.FEL_ROOD
            )
            corr = coh.get("correlatie", 0)
            print(kleur(
                f"    Coherentie: {verdict}"
                f" (correlatie: {corr:.2f})",
                ck,
            ))
        for b in r.get("bevindingen", []):
            print(kleur(
                f"    [{b['ernst']}] {b['type']}",
                _ERNST_KLEUR.get(
                    b["ernst"], Kleur.DIM
                ),
            ))

    def _toon_rag_resultaat(self, r):
        chroma = r.get("chromadb_hits", [])
        stack = r.get("stack_hits", [])
        print(kleur(
            f"\n  RAG RESEARCH: "
            f"{len(chroma)} ChromaDB,"
            f" {len(stack)} Stack hits",
            Kleur.FEL_GEEL,
        ))
        if not chroma and not stack:
            print(kleur(
                "    Geen dreigingen gevonden.",
                Kleur.FEL_GROEN,
            ))
        for h in (chroma + stack)[:10]:
            print(kleur(
                f"    [{h['term']}] "
                f"{h['tekst'][:80]}",
                Kleur.DIM,
            ))

    def _toon_alerts(self):
        alerts = self.get_alerts()
        print(kleur(
            f"\n  ALERTS ({len(alerts)}):",
            Kleur.FEL_GEEL,
        ))
        if not alerts:
            print(kleur(
                "    Geen alerts opgeslagen.",
                Kleur.FEL_GROEN,
            ))
        for a in alerts[-20:]:
            ek = _ERNST_KLEUR.get(
                a.get("ernst"), Kleur.DIM
            )
            print(kleur(
                f"    [{a.get('ernst', '?')}] "
                f"{a.get('type', '?')} "
                f"— {a.get('timestamp', '')[:19]}",
                ek,
            ))

    def _toon_forensisch_resultaat(self, r):
        bev = r.get("bevindingen", [])
        det = r.get("details", {})
        print(kleur(
            f"\n  FORENSISCH: {len(bev)} bevindingen",
            Kleur.FEL_GEEL,
        ))
        if not bev:
            print(kleur(
                "    Geen verdachte patronen.",
                Kleur.FEL_GROEN,
            ))
        for b in bev[:10]:
            ek = _ERNST_KLEUR.get(
                b["ernst"], Kleur.DIM
            )
            print(kleur(
                f"    [{b['ernst']}] "
                f"{b['type']} {b.get('adres', '')}",
                ek,
            ))
        for adres, d in det.items():
            tx_uur = d.get("tx_laatste_uur", "?")
            contr = d.get("contract_tx", 0)
            print(kleur(
                f"    {adres}: {tx_uur} tx/uur,"
                f" {contr} contract-interacties",
                Kleur.DIM,
            ))
        for f_err in r.get("fouten", [])[:3]:
            print(kleur(
                f"    [FOUT] {f_err}", Kleur.ROOD,
            ))

    def _toon_balance(self, r):
        bal = r.get("balances", {})
        print(kleur(
            f"\n  BALANCES ({len(bal)} wallets):",
            Kleur.FEL_GEEL,
        ))
        if not bal:
            if self.config.heeft_wallets():
                print(kleur(
                    "    Geen balance data beschikbaar.",
                    Kleur.DIM,
                ))
            else:
                print(kleur(
                    "    Geen wallets geconfigureerd.",
                    Kleur.DIM,
                ))
        for adres, info in bal.items():
            print(kleur(
                f"    {info['chain']} {adres}: "
                f"{info['balance']} {info['unit']}",
                Kleur.FEL_CYAAN,
            ))
        for f_err in r.get("fouten", [])[:3]:
            print(kleur(
                f"    [FOUT] {f_err}", Kleur.ROOD,
            ))

    def _toon_status(self):
        status = self.get_status()
        print(kleur(
            "\n  ENGINE STATUS:", Kleur.FEL_CYAAN,
        ))
        for key, val in status.items():
            print(f"    {key}: {val}")


# ══════════════════════════════════════════════════════
# HELPERS (module-level)
# ══════════════════════════════════════════════════════

def _fetch_json(url, timeout=10) -> dict | list | None:
    """Haal JSON op van een URL.

    Returns:
        Parsed JSON of None bij fout.
    """
    if not HAS_REQUESTS:
        return None
    try:
        resp = requests.get(
            url,
            timeout=timeout,
            headers={
                "User-Agent": "DannyToolkit/2.0",
            },
        )
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return None


def _scrub_adres(adres: str) -> str:
    """Maskeer een wallet adres voor display.

    Toont eerste 6 en laatste 4 karakters.
    Voorbeeld: bc1q4x...7k2m
    """
    if not adres or len(adres) < 12:
        return adres or ""
    return f"{adres[:6]}...{adres[-4:]}"
