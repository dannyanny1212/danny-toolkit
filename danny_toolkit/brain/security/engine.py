"""
Security Research Engine — Kern scan-logica.

from __future__ import annotations

Bevat SecurityResearchEngine met alle 7 scans + CLI.
Erft SecurityDisplayMixin voor visuele output.

Geëxtraheerd uit security_research.py (Fase C.2 monoliet split).
"""

import json
import logging
import os
import re
import sys
import time
from collections import OrderedDict
from datetime import datetime

from danny_toolkit.core.config import Config
from danny_toolkit.core.utils import kleur, Kleur
from danny_toolkit.brain.security.utils import (
    _fetch_json, _scrub_adres, HAS_REQUESTS,
)
from danny_toolkit.brain.security.config import (
    Ernst, SecurityConfig,
)
from danny_toolkit.brain.security.scanners import (
    AUDIT_PATRONEN, RAG_ZOEKTERMEN,
)
from danny_toolkit.brain.security.display import SecurityDisplayMixin

logger = logging.getLogger(__name__)


class SecurityResearchEngine(SecurityDisplayMixin):
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

    # Backward compat: class-level references
    _AUDIT_PATRONEN = AUDIT_PATRONEN
    _RAG_ZOEKTERMEN = RAG_ZOEKTERMEN

    def __init__(self, brain: object=None, daemon: object=None) -> None:
        """Init  ."""
        self._brain = brain
        self._daemon = daemon
        self._governor = None
        self._stack = None
        self._file_guard = None
        self._coherentie = None
        self.config = SecurityConfig()
        self._alerts = []
        self._eth_tx_cache: OrderedDict = OrderedDict()
        self._eth_tx_cache_max = 100
        self._eth_tx_cache_ttl = 300  # seconds

    # -- Lazy properties --

    @property
    def governor(self) -> None:
        """Governor."""
        if self._governor is None:
            try:
                from danny_toolkit.brain.governor import OmegaGovernor
                self._governor = OmegaGovernor()
            except Exception as e:
                logger.debug("OmegaGovernor init failed: %s", e)
        return self._governor

    @property
    def stack(self) -> None:
        """Stack."""
        if self._stack is None:
            try:
                from danny_toolkit.brain.cortical_stack import (
                    get_cortical_stack,
                )
                self._stack = get_cortical_stack()
            except Exception as e:
                logger.debug("CorticalStack init failed: %s", e)
        return self._stack

    @property
    def file_guard(self) -> None:
        """File guard."""
        if self._file_guard is None:
            try:
                from danny_toolkit.brain.file_guard import FileGuard
                self._file_guard = FileGuard()
            except Exception as e:
                logger.debug("FileGuard init failed: %s", e)
        return self._file_guard

    @property
    def coherentie(self) -> None:
        """Coherentie."""
        if self._coherentie is None:
            try:
                from danny_toolkit.daemon.coherentie import (
                    CoherentieMonitor,
                )
                self._coherentie = CoherentieMonitor()
            except Exception as e:
                logger.debug("CoherentieMonitor init failed: %s", e)
        return self._coherentie

    # ======================================================
    # SCAN 1: Wallets
    # ======================================================

    def scan_wallets(self) -> dict:
        """Check balance, transacties en tokens per wallet."""
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
                if bal_data and isinstance(bal_data, dict):
                    cs = bal_data.get("chain_stats", {})
                    funded = cs.get("funded_txo_sum", 0)
                    spent = cs.get("spent_txo_sum", 0)
                    btc_bal = (funded - spent) / 1e8
                    balances[scrub] = {
                        "chain": "BTC",
                        "balance": round(btc_bal, 8),
                        "unit": "BTC",
                    }
            except Exception as e:
                logger.debug("BTC balance check failed: %s", e)

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
                            "txid": tx.get("txid", "?")[:16] + "...",
                            "status": (
                                "bevestigd"
                                if tx.get("status", {}).get("confirmed")
                                else "onbevestigd"
                            ),
                        })
            except Exception as e:
                fouten.append(f"BTC {scrub}: {str(e)[:60]}")

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
                if bal_data and isinstance(bal_data, dict):
                    raw = bal_data.get("coin_balance", "0")
                    eth_bal = int(raw) / 1e18
                    balances[scrub] = {
                        "chain": "ETH",
                        "balance": round(eth_bal, 6),
                        "unit": "ETH",
                    }
            except Exception as e:
                logger.debug("ETH balance check failed: %s", e)

            # Transacties met richting
            try:
                url = (
                    "https://eth.blockscout.com/api"
                    "/v2/addresses"
                    f"/{adres}/transactions"
                )
                data = _fetch_json(url)
                # Cache voor scan_forensisch (bounded + TTL)
                if data:
                    self._eth_tx_cache[adres] = (time.time(), data)
                    while len(self._eth_tx_cache) > self._eth_tx_cache_max:
                        self._eth_tx_cache.popitem(last=False)
                if data and isinstance(data, dict):
                    items = data.get("items", [])
                    for tx in items[:5]:
                        waarde_raw = tx.get("value", "0")
                        try:
                            waarde_eth = int(waarde_raw) / 1e18
                        except (ValueError, TypeError):
                            waarde_eth = 0.0

                        tx_from = tx.get("from", {})
                        if isinstance(tx_from, dict):
                            from_addr = tx_from.get("hash", "").lower()
                        else:
                            from_addr = str(tx_from).lower()

                        richting = "OUT" if from_addr == adres_lower else "IN"
                        ernst = Ernst.MEDIUM
                        if waarde_eth > whale_drempel_eth:
                            ernst = Ernst.HOOG

                        bevindingen.append({
                            "ernst": ernst,
                            "type": "eth_transactie",
                            "adres": scrub,
                            "hash": tx.get("hash", "?")[:16] + "...",
                            "waarde_eth": round(waarde_eth, 6),
                            "richting": richting,
                        })
            except Exception as e:
                fouten.append(f"ETH {scrub}: {str(e)[:60]}")

            # Token transfers
            try:
                tok_url = (
                    "https://eth.blockscout.com/api"
                    "/v2/addresses"
                    f"/{adres}/token-transfers"
                    "?type=ERC-20"
                )
                tok_data = _fetch_json(tok_url)
                if tok_data and isinstance(tok_data, dict):
                    tok_items = tok_data.get("items", [])
                    for tok in tok_items[:5]:
                        token_info = tok.get("token", {})
                        symbool = token_info.get("symbol", "?")
                        tok_from = tok.get("from", {})
                        if isinstance(tok_from, dict):
                            tf_addr = tok_from.get("hash", "").lower()
                        else:
                            tf_addr = str(tok_from).lower()
                        tok_richting = "OUT" if tf_addr == adres_lower else "IN"
                        bevindingen.append({
                            "ernst": Ernst.MEDIUM,
                            "type": "eth_token",
                            "adres": scrub,
                            "token": symbool,
                            "richting": tok_richting,
                        })
            except Exception as e:
                logger.debug("ETH token transfer check failed: %s", e)

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
                                tx.get("signature", "?")
                            )[:16] + "...",
                        })
            except Exception as e:
                fouten.append(f"SOL {scrub}: {str(e)[:60]}")

        return {
            "bevindingen": bevindingen,
            "balances": balances,
            "gescand": gescand,
            "fouten": fouten,
        }

    # ======================================================
    # SCAN 2: Markt
    # ======================================================

    def scan_markt(self) -> dict:
        """Check prijzen en genereer alerts bij drempels."""
        prijzen = {}
        alerts = []
        fouten = []

        if not HAS_REQUESTS:
            fouten.append("requests niet geinstalleerd")
            return {"prijzen": prijzen, "alerts": alerts, "fouten": fouten}

        watchlist = self.config.watchlist
        if not watchlist:
            return {"prijzen": prijzen, "alerts": alerts, "fouten": fouten}

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
                return {"prijzen": prijzen, "alerts": alerts, "fouten": fouten}

            drempels = self.config.drempels
            daling_pct = drempels.get("prijs_daling_pct", 5.0)
            stijging_pct = drempels.get("stijging_pct", 10.0)

            for coin_id, info in data.items():
                prijs = info.get("usd", 0)
                change = info.get("usd_24h_change", 0) or 0

                prijzen[coin_id] = {
                    "prijs_usd": prijs,
                    "change_24h": round(change, 2),
                }

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
            fouten.append(f"CoinGecko: {str(e)[:60]}")

        return {"prijzen": prijzen, "alerts": alerts, "fouten": fouten}

    # ======================================================
    # SCAN 3: Code Audit
    # ======================================================

    def scan_code_audit(self) -> dict:
        """Regex scan op gevaarlijke patronen in code."""
        bevindingen = []
        gescand = 0
        fouten = []

        repo_root = Config.BASE_DIR
        bestanden = self.config.audit_bestanden

        for rel_pad in bestanden:
            absoluut = repo_root / rel_pad
            if not absoluut.is_file():
                fouten.append(f"Bestand niet gevonden: {rel_pad}")
                continue

            gescand += 1
            try:
                with open(absoluut, "r", encoding="utf-8") as f:
                    inhoud = f.read()

                regels = inhoud.split("\n")
                for ernst, naam, patroon in self._AUDIT_PATRONEN:
                    for i, regel in enumerate(regels, 1):
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
                fouten.append(f"{rel_pad}: {str(e)[:60]}")

        return {"bevindingen": bevindingen, "gescand": gescand, "fouten": fouten}

    # ======================================================
    # SCAN 4: Systeem
    # ======================================================

    def scan_systeem(self) -> dict:
        """Check FileGuard, Governor health, CoherentieMonitor."""
        bevindingen = []
        result = {
            "file_guard": None, "governor": None,
            "coherentie": None, "bevindingen": bevindingen,
        }

        fg = self.file_guard
        if fg:
            try:
                rapport = fg.controleer_integriteit()
                result["file_guard"] = rapport
                if rapport["status"] == "KRITIEK":
                    bevindingen.append({"ernst": Ernst.KRITIEK, "type": "file_guard_kritiek", "ontbrekend": len(rapport["ontbrekend"])})
                elif rapport["status"] == "WAARSCHUWING":
                    bevindingen.append({"ernst": Ernst.HOOG, "type": "file_guard_waarschuwing", "ontbrekend": len(rapport["ontbrekend"])})
            except Exception as e:
                logger.debug("FileGuard integriteit check failed: %s", e)
                result["file_guard"] = {"status": "FOUT"}

        gov = self.governor
        if gov:
            try:
                health = gov.get_health_report()
                result["governor"] = health
                cb_status = health.get("circuit_breaker", {}).get("status", "CLOSED")
                if cb_status == "OPEN":
                    bevindingen.append({"ernst": Ernst.HOOG, "type": "circuit_breaker_open", "failures": health.get("circuit_breaker", {}).get("failures", 0)})
            except Exception as e:
                logger.debug("Governor health check failed: %s", e)
                result["governor"] = {"status": "FOUT"}

        coh = self.coherentie
        if coh:
            try:
                scan_result = coh.scan(samples=10, interval=0.3)
                result["coherentie"] = scan_result
                verdict = scan_result.get("verdict", "PASS")
                if verdict == "ALARM":
                    bevindingen.append({"ernst": Ernst.KRITIEK, "type": "gpu_misbruik", "details": scan_result.get("details", "")[:80], "correlatie": scan_result.get("correlatie", 0)})
                elif verdict == "WAARSCHUWING":
                    bevindingen.append({"ernst": Ernst.HOOG, "type": "gpu_anomalie", "details": scan_result.get("details", "")[:80], "correlatie": scan_result.get("correlatie", 0)})
            except Exception as e:
                logger.debug("Coherentie scan failed: %s", e)
                result["coherentie"] = {"status": "FOUT"}

        return result

    # ======================================================
    # SCAN 5: RAG Research
    # ======================================================

    def scan_rag_research(self) -> dict:
        """Zoek dreigings-termen in ChromaDB + CorticalStack."""
        chromadb_hits = []
        stack_hits = []
        fouten = []

        try:
            from danny_toolkit.ai.production_rag import ProductionRAG
            rag = ProductionRAG()
            if hasattr(rag, "zoek") or hasattr(rag, "search"):
                for term in self._RAG_ZOEKTERMEN[:4]:
                    try:
                        if hasattr(rag, "zoek"):
                            resultaten = rag.zoek(term, k=3)
                        else:
                            resultaten = rag.search(term, k=3)
                        if resultaten:
                            for r in resultaten:
                                chromadb_hits.append({"term": term, "tekst": str(r)[:120]})
                    except Exception as e:
                        logger.debug("RAG search for %s failed: %s", term, e)
        except Exception as e:
            fouten.append(f"ChromaDB: {str(e)[:60]}")

        stk = self.stack
        if stk:
            try:
                for term in self._RAG_ZOEKTERMEN[:4]:
                    try:
                        events = stk.search_events(term, limit=3)
                        for ev in (events or []):
                            stack_hits.append({"term": term, "tekst": str(ev)[:120]})
                        feiten = stk.recall_all(prefix=term, min_confidence=0.0)
                        for f in (feiten or []):
                            stack_hits.append({"term": term, "tekst": str(f)[:120]})
                    except Exception as e:
                        logger.debug("Stack search for %s failed: %s", term, e)
            except Exception as e:
                fouten.append(f"CorticalStack: {str(e)[:60]}")

        return {"chromadb_hits": chromadb_hits, "stack_hits": stack_hits, "fouten": fouten}

    # ======================================================
    # SCAN 6: Forensisch
    # ======================================================

    def scan_forensisch(self) -> dict:
        """Forensische diepte-scan op gemonitorde wallets."""
        bevindingen = []
        details = {}
        fouten = []

        if not HAS_REQUESTS:
            fouten.append("requests niet geinstalleerd")
            return {"bevindingen": bevindingen, "details": details, "fouten": fouten}

        wallets = self.config.wallets

        for adres in wallets.get("eth", []):
            scrub = _scrub_adres(adres)

            try:
                cached = self._eth_tx_cache.get(adres)
                data = None
                if cached:
                    cache_ts, cache_data = cached
                    if time.time() - cache_ts < self._eth_tx_cache_ttl:
                        data = cache_data
                    else:
                        del self._eth_tx_cache[adres]
                if data is None:
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
                        timestamps = []
                        for tx in items:
                            ts = tx.get("timestamp")
                            if ts:
                                timestamps.append(ts)

                        details[scrub] = {
                            "totaal_tx": len(items),
                            "contract_tx": 0,
                        }

                        if len(timestamps) >= 2:
                            try:
                                nieuwste = datetime.fromisoformat(
                                    timestamps[0].replace("Z", "+00:00")
                                )
                                tx_laatste_uur = 0
                                for ts in timestamps:
                                    t = datetime.fromisoformat(
                                        ts.replace("Z", "+00:00")
                                    )
                                    delta = nieuwste - t
                                    if delta.total_seconds() <= 3600:
                                        tx_laatste_uur += 1
                                if tx_laatste_uur > 5:
                                    bevindingen.append({
                                        "ernst": Ernst.HOOG,
                                        "type": "hoge_tx_velocity",
                                        "adres": scrub,
                                        "tx_per_uur": tx_laatste_uur,
                                    })
                                details[scrub]["tx_laatste_uur"] = tx_laatste_uur
                            except Exception as e:
                                logger.debug("Velocity timestamp parse failed: %s", e)

                        contract_count = 0
                        for tx in items:
                            to_info = tx.get("to", {})
                            if isinstance(to_info, dict):
                                is_contract = to_info.get("is_contract", False)
                                is_verified = to_info.get("is_verified", True)
                                if is_contract:
                                    contract_count += 1
                                    if not is_verified:
                                        bevindingen.append({
                                            "ernst": Ernst.HOOG,
                                            "type": "unverified_contract",
                                            "adres": scrub,
                                            "contract": _scrub_adres(to_info.get("hash", "?")),
                                        })
                        details[scrub]["contract_tx"] = contract_count

            except Exception as e:
                fouten.append(f"Forensisch ETH {scrub}: {str(e)[:60]}")

        return {"bevindingen": bevindingen, "details": details, "fouten": fouten}

    # ======================================================
    # VOLLEDIG RAPPORT
    # ======================================================

    def volledig_rapport(self) -> dict:
        """Orchestrator: draai alle 7 scans."""
        start = time.time()
        self._eth_tx_cache.clear()

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

        self._eth_tx_cache.clear()
        rapport["duur_seconden"] = round(time.time() - start, 2)

        alle_bevindingen = []
        alle_bevindingen.extend(rapport["wallets"].get("bevindingen", []))
        alle_bevindingen.extend(rapport["markt"].get("alerts", []))
        alle_bevindingen.extend(rapport["code_audit"].get("bevindingen", []))
        alle_bevindingen.extend(rapport["systeem"].get("bevindingen", []))
        alle_bevindingen.extend(rapport["forensisch"].get("bevindingen", []))

        rapport["totaal_bevindingen"] = len(alle_bevindingen)

        ernst_prio = [Ernst.KRITIEK, Ernst.HOOG, Ernst.MEDIUM, Ernst.LAAG]
        for e in ernst_prio:
            if any(b.get("ernst") == e for b in alle_bevindingen):
                rapport["hoogste_ernst"] = e
                break

        self._log_scan(rapport)

        for b in alle_bevindingen:
            if b.get("ernst") in (Ernst.KRITIEK, Ernst.HOOG):
                self._bewaar_alert(b)

        return rapport

    # -- Logging --

    def _log_scan(self, rapport: object) -> None:
        """Log scan resultaat naar CorticalStack."""
        stk = self.stack
        if stk is None:
            return
        try:
            stk.log_event(
                actor="security_research",
                action="scan_voltooid",
                details={
                    "bevindingen": rapport.get("totaal_bevindingen", 0),
                    "hoogste_ernst": rapport.get("hoogste_ernst", "LAAG"),
                    "duur": rapport.get("duur_seconden", 0),
                },
                source="security",
            )
        except Exception as e:
            logger.debug("Scan logging failed: %s", e)

    def _bewaar_alert(self, bevinding: object) -> None:
        """Bewaar kritiek/hoog alert voor later."""
        self._alerts.append({
            "timestamp": datetime.now().isoformat(),
            **bevinding,
        })
        if len(self._alerts) > 100:
            self._alerts = self._alerts[-100:]

        stk = self.stack
        if stk:
            try:
                stk.remember_fact(
                    f"security_alert_{len(self._alerts)}",
                    json.dumps(bevinding, ensure_ascii=False),
                    confidence=0.8,
                )
            except Exception as e:
                logger.debug("Alert opslag failed: %s", e)

    def get_alerts(self) -> list:
        """Haal opgeslagen alerts op."""
        return list(self._alerts)

    def get_status(self) -> dict:
        """Haal engine status op."""
        hash_ok = not getattr(self.config, "_hash_gewijzigd", False)
        return {
            "versie": self.VERSION,
            "config_pad": str(self.config._pad),
            "config_hash": "OK" if hash_ok else "GEWIJZIGD",
            "heeft_wallets": self.config.heeft_wallets(),
            "watchlist": self.config.watchlist,
            "alerts": len(self._alerts),
            "governor": "beschikbaar" if self.governor else "niet geladen",
            "stack": "beschikbaar" if self.stack else "niet geladen",
            "file_guard": "beschikbaar" if self.file_guard else "niet geladen",
            "coherentie": "beschikbaar" if self.coherentie else "niet geladen",
        }

    # ======================================================
    # INTERACTIEVE CLI
    # ======================================================

    def run(self) -> None:
        """Start de interactieve CLI."""
        # Windows UTF-8 (niet op import-time)
        if os.name == "nt":
            if hasattr(sys.stdout, "reconfigure"):
                sys.stdout.reconfigure(encoding="utf-8")
            if hasattr(sys.stderr, "reconfigure"):
                sys.stderr.reconfigure(encoding="utf-8")

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
                    "\n[SECURITY] > ", Kleur.FEL_CYAAN,
                )).strip().lower()

                if not cmd:
                    continue

                if cmd in ("stop", "exit", "quit"):
                    break
                elif cmd == "scan":
                    print(kleur("  Scan bezig...", Kleur.FEL_GEEL))
                    laatste_rapport = self.volledig_rapport()
                    self.toon_rapport(laatste_rapport)
                elif cmd == "rapport":
                    if laatste_rapport:
                        self.toon_rapport(laatste_rapport)
                    else:
                        print(kleur("  Nog geen rapport. Gebruik 'scan' eerst.", Kleur.DIM))
                elif cmd == "wallets":
                    print(kleur("  Wallet scan...", Kleur.FEL_GEEL))
                    self._toon_wallet_resultaat(self.scan_wallets())
                elif cmd == "markt":
                    print(kleur("  Markt scan...", Kleur.FEL_GEEL))
                    self._toon_markt_resultaat(self.scan_markt())
                elif cmd == "audit":
                    print(kleur("  Code audit...", Kleur.FEL_GEEL))
                    self._toon_audit_resultaat(self.scan_code_audit())
                elif cmd == "systeem":
                    print(kleur("  Systeem scan...", Kleur.FEL_GEEL))
                    self._toon_systeem_resultaat(self.scan_systeem())
                elif cmd == "research":
                    print(kleur("  RAG research...", Kleur.FEL_GEEL))
                    self._toon_rag_resultaat(self.scan_rag_research())
                elif cmd == "forensisch":
                    print(kleur("  Forensische scan...", Kleur.FEL_GEEL))
                    self._toon_forensisch_resultaat(self.scan_forensisch())
                elif cmd == "balance":
                    print(kleur("  Balance check...", Kleur.FEL_GEEL))
                    self._toon_balance(self.scan_wallets())
                elif cmd == "hash":
                    self.config.herbereken_hash()
                elif cmd == "config":
                    self.config.toon()
                elif cmd == "alerts":
                    self._toon_alerts()
                elif cmd == "status":
                    self._toon_status()
                else:
                    print(f"  Onbekend commando: {cmd}")

            except (EOFError, KeyboardInterrupt):
                break

        print(kleur("\n  Security Research gestopt.", Kleur.FEL_CYAAN))
