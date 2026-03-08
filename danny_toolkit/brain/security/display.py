"""
Security Display Mixin — Alle visuele output methoden.

Bevat SecurityDisplayMixin met:
- toon_rapport()                — Volledig visueel rapport
- _toon_wallet_resultaat()      — Wallet scan output
- _toon_markt_resultaat()       — Markt scan output
- _toon_audit_resultaat()       — Code audit output
- _toon_systeem_resultaat()     — Systeem scan output
- _toon_rag_resultaat()         — RAG research output
- _toon_forensisch_resultaat()  — Forensisch scan output
- _toon_balance()               — Balance display
- _toon_alerts()                — Alerts display
- _toon_status()                — Engine status display

Geëxtraheerd uit security_research.py (Fase C.2 monoliet split).
"""

from __future__ import annotations

from danny_toolkit.core.utils import kleur, Kleur
from danny_toolkit.brain.security.config import Ernst, _ERNST_KLEUR
import logging

logger = logging.getLogger(__name__)


class SecurityDisplayMixin:
    """Mixin met alle display/toon methoden voor SecurityResearchEngine.

    Vereist dat de host-klasse de volgende attributen heeft:
    - self.VERSION, self.config
    - self.get_alerts(), self.get_status()
    - self.volledig_rapport()
    """

    def toon_rapport(self, rapport=None) -> None:
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

        # -- Wallets --
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

        # -- Markt --
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

        # -- Code Audit --
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

        # -- Systeem --
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

        # -- RAG Research --
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

        # -- Forensisch --
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

    # -- CLI sub-displays --

    def _toon_wallet_resultaat(self, r) -> None:
        """Toon wallet resultaat."""
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

    def _toon_markt_resultaat(self, r) -> None:
        """Toon markt resultaat."""
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

    def _toon_audit_resultaat(self, r) -> None:
        """Toon audit resultaat."""
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

    def _toon_systeem_resultaat(self, r) -> None:
        """Toon systeem resultaat."""
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

    def _toon_rag_resultaat(self, r) -> None:
        """Toon rag resultaat."""
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

    def _toon_alerts(self) -> None:
        """Toon alerts."""
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

    def _toon_forensisch_resultaat(self, r) -> None:
        """Toon forensisch resultaat."""
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

    def _toon_balance(self, r) -> None:
        """Toon balance."""
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

    def _toon_status(self) -> None:
        """Toon status."""
        status = self.get_status()
        print(kleur(
            "\n  ENGINE STATUS:", Kleur.FEL_CYAAN,
        ))
        for key, val in status.items():
            print(f"    {key}: {val}")
