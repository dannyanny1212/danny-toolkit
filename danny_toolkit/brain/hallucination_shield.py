"""
HallucinatieSchild — Anti-hallucinatie poort (Invention #23).
==============================================================
Phase 30 "SCHILD EN VRIEND": finale gate voor output naar de gebruiker.

Beoordeelt payloads op:
- Claim-context overlap (word-level)
- TruthAnchor score integratie
- Tribunal validatie bonus/penalty
- Contradicties tussen agents
- Regelcheck (percentage>100, toekomstige datums, zekerheidswoorden)

Gebruik:
    from danny_toolkit.brain.hallucination_shield import HallucinatieSchild

    schild = HallucinatieSchild()
    rapport = schild.beoordeel(payloads, user_input)
    if rapport.geblokkeerd:
        print(rapport.reden_blokkade)
"""

import logging
import re
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

try:
    from danny_toolkit.core.neural_bus import get_bus, EventTypes
    HAS_BUS = True
except ImportError:
    HAS_BUS = False

try:
    from danny_toolkit.brain.black_box import BlackBox
    HAS_BLACKBOX = True
except ImportError:
    HAS_BLACKBOX = False


# ── Enums & Dataclasses ──

class BeoordelingNiveau(Enum):
    """Betrouwbaarheidsniveau van een claim."""
    GEVERIFIEERD = "geverifieerd"   # >= 0.75
    WAARSCHIJNLIJK = "waarschijnlijk"  # >= 0.50
    ONZEKER = "onzeker"            # >= 0.30
    VERDACHT = "verdacht"          # < 0.30


def _bepaal_niveau(score: float) -> BeoordelingNiveau:
    """Bepaal beoordelingsniveau op basis van score."""
    if score >= 0.75:
        return BeoordelingNiveau.GEVERIFIEERD
    elif score >= 0.50:
        return BeoordelingNiveau.WAARSCHIJNLIJK
    elif score >= 0.30:
        return BeoordelingNiveau.ONZEKER
    return BeoordelingNiveau.VERDACHT


@dataclass
class ClaimBeoordeling:
    """Beoordeling van een individuele claim."""
    claim_tekst: str
    vertrouwen: float  # 0.0 - 1.0
    niveau: BeoordelingNiveau = BeoordelingNiveau.ONZEKER
    bronnen: List[str] = field(default_factory=list)
    problemen: List[str] = field(default_factory=list)


@dataclass
class HallucinatieRapport:
    """Resultaat van een volledige hallucinatie-beoordeling."""
    totaal_score: float  # 0.0 - 1.0 (hoger = betrouwbaarder)
    claims: List[ClaimBeoordeling] = field(default_factory=list)
    contradictions: List[Dict[str, Any]] = field(default_factory=list)
    geblokkeerd: bool = False
    reden_blokkade: str = ""
    regel_schendingen: List[str] = field(default_factory=list)
    tijdstip: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        """Serialiseer rapport naar dict."""
        return {
            "totaal_score": round(self.totaal_score, 3),
            "aantal_claims": len(self.claims),
            "contradictions": len(self.contradictions),
            "geblokkeerd": self.geblokkeerd,
            "reden_blokkade": self.reden_blokkade,
            "regel_schendingen": self.regel_schendingen,
            "tijdstip": self.tijdstip,
        }


# ── Hoofdklasse ──

class HallucinatieSchild:
    """
    Finale anti-hallucinatie gate.

    Beoordeelt swarm payloads op betrouwbaarheid via gewogen
    aggregatie van TruthAnchor, Tribunal, en regelchecks.
    Blokkeert output onder de drempel.
    """

    # Drempels
    BLOKKADE_DREMPEL = 0.35     # Onder deze score → blokkade
    WAARSCHUWING_DREMPEL = 0.55  # Onder deze score → waarschuwing

    # Gewichten voor totaalscore
    GEWICHT_TRUTH_ANCHOR = 0.40
    GEWICHT_TRIBUNAL = 0.35
    GEWICHT_REGELCHECK = 0.25

    # Contradictie penalty per gevonden contradictie
    _CONTRADICTIE_PENALTY = 0.15

    # Negatie woorden voor contradictie detectie
    _NEGATIE_WOORDEN = {
        "niet", "geen", "nooit", "fout", "onjuist",
        "incorrect", "verkeerd", "onwaar", "vals",
    }

    # Zekerheidswoorden die op hallucinatie wijzen
    _ZEKERHEIDS_PATRONEN = [
        r"absoluut\s+zeker",
        r"100\s*%\s*bewezen",
        r"onomstotelijk",
        r"onweerlegbaar",
        r"staat\s+vast\s+dat",
        r"wetenschappelijk\s+bewezen\s+feit",
    ]

    def __init__(self):
        self._lock = threading.Lock()
        self._stats = {
            "beoordeeld": 0,
            "geblokkeerd": 0,
            "waarschuwingen": 0,
            "doorgelaten": 0,
        }

    def beoordeel(
        self,
        payloads: list,
        user_input: str,
        context_docs: Optional[List[str]] = None,
        truth_anchor_score: Optional[float] = None,
        tribunal_gevalideerd: Optional[bool] = None,
    ) -> HallucinatieRapport:
        """Beoordeel payloads op hallucinatie-risico.

        Args:
            payloads: Lijst van SwarmPayload objecten.
            user_input: Oorspronkelijke gebruikersinvoer.
            context_docs: RAG context documenten (optioneel).
            truth_anchor_score: TruthAnchor score als beschikbaar.
            tribunal_gevalideerd: Tribunal uitspraak als beschikbaar.

        Returns:
            HallucinatieRapport met score en blokkade-beslissing.
        """
        with self._lock:
            self._stats["beoordeeld"] += 1

        # 1. Claims extraheren
        claims = self._extraheer_claims(payloads)

        # 2. Claims scoren
        beoordelingen = []
        for agent_naam, claim_tekst in claims:
            beoordeling = self._score_claim(
                claim_tekst, context_docs, truth_anchor_score,
            )
            beoordelingen.append(beoordeling)

        # 3. Contradicties detecteren
        contradicties = self._detecteer_contradicties(claims)

        # 4. Regelcheck over alle tekst
        alle_tekst = " ".join(
            str(getattr(p, "display_text", "") or getattr(p, "content", ""))
            for p in payloads
        )
        regel_schendingen = self._regelcheck(alle_tekst)

        # 5. Totaalscore berekenen
        totaal_score = self._bereken_totaal_score(
            beoordelingen, contradicties,
            truth_anchor_score, tribunal_gevalideerd,
            regel_schendingen,
        )

        # 6. Rapport opbouwen
        rapport = HallucinatieRapport(
            totaal_score=totaal_score,
            claims=beoordelingen,
            contradictions=contradicties,
            regel_schendingen=regel_schendingen,
        )

        # 7. Blokkade beslissing
        if totaal_score < self.BLOKKADE_DREMPEL:
            rapport.geblokkeerd = True
            rapport.reden_blokkade = (
                f"Score {totaal_score:.2f} onder blokkadedrempel "
                f"({self.BLOKKADE_DREMPEL})"
            )
            with self._lock:
                self._stats["geblokkeerd"] += 1
            self._log_naar_blackbox(rapport, payloads, user_input)
            self._publiceer_event(rapport, user_input)
        elif totaal_score < self.WAARSCHUWING_DREMPEL:
            with self._lock:
                self._stats["waarschuwingen"] += 1
            logger.info(
                "HallucinatieSchild waarschuwing: score %.2f < %.2f",
                totaal_score, self.WAARSCHUWING_DREMPEL,
            )
        else:
            with self._lock:
                self._stats["doorgelaten"] += 1

        return rapport

    def _extraheer_claims(
        self, payloads: list,
    ) -> List[Tuple[str, str]]:
        """Extraheer (agent, claim) paren uit payloads.

        Splitst display_text op zinsgrenzen.
        """
        claims = []
        for payload in payloads:
            agent_naam = getattr(payload, "agent", "unknown")
            tekst = str(
                getattr(payload, "display_text", "")
                or getattr(payload, "content", "")
            )
            if not tekst.strip():
                continue

            # Split op zinsgrenzen (., !, ?)
            zinnen = re.split(r'(?<=[.!?])\s+', tekst.strip())
            for zin in zinnen:
                zin = zin.strip()
                if len(zin) > 10:  # Skip te korte fragmenten
                    claims.append((agent_naam, zin))

        return claims

    def _score_claim(
        self,
        claim: str,
        context_docs: Optional[List[str]],
        truth_anchor_score: Optional[float],
    ) -> ClaimBeoordeling:
        """Score een individuele claim.

        Gebruikt word-overlap met context documenten en
        TruthAnchor score als bonus.
        """
        problemen = []
        bronnen = []
        score = 0.5  # Basiswaarde zonder context

        if context_docs:
            # Word-overlap scoring
            claim_woorden = set(claim.lower().split())
            # Filter stopwoorden (korte woorden)
            claim_woorden = {w for w in claim_woorden if len(w) > 3}

            if claim_woorden:
                beste_overlap = 0.0
                for doc in context_docs:
                    doc_woorden = set(doc.lower().split())
                    doc_woorden = {w for w in doc_woorden if len(w) > 3}
                    if doc_woorden:
                        overlap = len(claim_woorden & doc_woorden) / len(claim_woorden)
                        if overlap > beste_overlap:
                            beste_overlap = overlap
                            bronnen.append(doc[:100])

                score = 0.3 + beste_overlap * 0.5  # 0.3-0.8 range

        # TruthAnchor bonus
        if truth_anchor_score is not None:
            ta_bonus = (truth_anchor_score - 0.5) * self.GEWICHT_TRUTH_ANCHOR
            score += ta_bonus

        # Regelcheck op individuele claim
        claim_regelproblemen = self._regelcheck(claim)
        if claim_regelproblemen:
            score -= 0.05 * len(claim_regelproblemen)
            problemen.extend(claim_regelproblemen)

        score = max(0.0, min(1.0, score))
        niveau = _bepaal_niveau(score)

        return ClaimBeoordeling(
            claim_tekst=claim[:200],
            vertrouwen=round(score, 3),
            niveau=niveau,
            bronnen=bronnen[:3],
            problemen=problemen,
        )

    def _detecteer_contradicties(
        self, claims: List[Tuple[str, str]],
    ) -> List[Dict[str, Any]]:
        """Detecteer contradicties tussen claims van verschillende agents.

        Methoden:
        - Negatie-woord detectie in vergelijkbare claims
        - Numerieke divergentie (>50% verschil)
        """
        contradicties = []
        if len(claims) < 2:
            return contradicties

        # Groepeer claims per agent
        agent_claims: Dict[str, List[str]] = {}
        for agent, claim in claims:
            agent_claims.setdefault(agent, []).append(claim)

        agents = list(agent_claims.keys())
        if len(agents) < 2:
            return contradicties

        # Cross-agent vergelijking
        for i in range(len(agents)):
            for j in range(i + 1, len(agents)):
                for claim_a in agent_claims[agents[i]]:
                    for claim_b in agent_claims[agents[j]]:
                        # Negatie check
                        woorden_a = set(claim_a.lower().split())
                        woorden_b = set(claim_b.lower().split())

                        # Gedeelde inhoud woorden (>3 chars)
                        inhoud_a = {w for w in woorden_a if len(w) > 3}
                        inhoud_b = {w for w in woorden_b if len(w) > 3}
                        gedeeld = inhoud_a & inhoud_b

                        if len(gedeeld) < 2:
                            continue  # Te weinig overlap om te vergelijken

                        # Check negatie in een van de claims
                        negatie_a = woorden_a & self._NEGATIE_WOORDEN
                        negatie_b = woorden_b & self._NEGATIE_WOORDEN
                        if negatie_a != negatie_b and (negatie_a or negatie_b):
                            contradicties.append({
                                "agent_a": agents[i],
                                "agent_b": agents[j],
                                "claim_a": claim_a[:150],
                                "claim_b": claim_b[:150],
                                "type": "negatie",
                            })

                        # Numerieke divergentie
                        getallen_a = re.findall(r'\b\d+(?:\.\d+)?\b', claim_a)
                        getallen_b = re.findall(r'\b\d+(?:\.\d+)?\b', claim_b)
                        if getallen_a and getallen_b:
                            try:
                                num_a = float(getallen_a[0])
                                num_b = float(getallen_b[0])
                                if num_a > 0 and num_b > 0:
                                    verhouding = max(num_a, num_b) / min(num_a, num_b)
                                    if verhouding > 1.5:  # >50% verschil
                                        contradicties.append({
                                            "agent_a": agents[i],
                                            "agent_b": agents[j],
                                            "claim_a": claim_a[:150],
                                            "claim_b": claim_b[:150],
                                            "type": "numeriek",
                                            "waarden": [num_a, num_b],
                                        })
                            except (ValueError, ZeroDivisionError):
                                pass

        return contradicties

    def _regelcheck(self, tekst: str) -> List[str]:
        """Regel-gebaseerde checks op output tekst.

        Detecteert:
        - Percentages > 100%
        - Toekomstige datums (jaar > huidig + 2)
        - Zekerheidswoorden die op hallucinatie wijzen
        """
        problemen = []
        if not tekst:
            return problemen

        # 1. Percentage > 100%
        for match in re.finditer(r'(\d{3,})\s*%', tekst):
            waarde = int(match.group(1))
            if waarde > 100:
                problemen.append(
                    f"Onmogelijk percentage: {waarde}%"
                )

        # 2. Toekomstige datums
        huidig_jaar = datetime.now().year
        for match in re.finditer(
            r'(?:in|op|sinds|vanaf)\s+(\d{4})', tekst, re.IGNORECASE,
        ):
            jaar = int(match.group(1))
            if jaar > huidig_jaar + 2:
                problemen.append(
                    f"Toekomstige datum: {jaar}"
                )

        # 3. Zekerheidswoorden
        tekst_lower = tekst.lower()
        for patroon in self._ZEKERHEIDS_PATRONEN:
            if re.search(patroon, tekst_lower):
                problemen.append(
                    f"Zekerheidswoord gedetecteerd: {patroon}"
                )

        return problemen

    def _bereken_totaal_score(
        self,
        claims: List[ClaimBeoordeling],
        contradicties: List[Dict],
        truth_anchor_score: Optional[float],
        tribunal_gevalideerd: Optional[bool],
        regel_schendingen: List[str],
    ) -> float:
        """Bereken gewogen totaalscore.

        Formule:
        - Basis: gemiddelde claim vertrouwen
        - Contradictie penalty: 0.15 per contradictie
        - TruthAnchor bonus: (score - 0.5) * 0.40
        - Tribunal bonus: +0.10 * 0.35 als gevalideerd, -0.05 * 0.35 anders
        - Regelpenalty: 0.05 per schending
        """
        if not claims:
            return 0.6  # Geen claims → neutraal

        # Basis: gemiddelde vertrouwen
        basis = sum(c.vertrouwen for c in claims) / len(claims)

        # Contradictie penalty
        contradictie_aftrek = len(contradicties) * self._CONTRADICTIE_PENALTY
        basis -= contradictie_aftrek

        # TruthAnchor component
        if truth_anchor_score is not None:
            ta_component = (truth_anchor_score - 0.5) * self.GEWICHT_TRUTH_ANCHOR
            basis += ta_component

        # Tribunal component
        if tribunal_gevalideerd is not None:
            if tribunal_gevalideerd:
                basis += 0.10 * self.GEWICHT_TRIBUNAL
            else:
                basis -= 0.05 * self.GEWICHT_TRIBUNAL

        # Regelpenalty
        basis -= 0.05 * len(regel_schendingen)

        return max(0.0, min(1.0, round(basis, 3)))

    def _log_naar_blackbox(
        self, rapport: HallucinatieRapport,
        payloads: list, user_input: str,
    ):
        """Log geblokkeerde output naar BlackBox."""
        if not HAS_BLACKBOX:
            return

        try:
            bb = BlackBox()
            output = " | ".join(
                str(getattr(p, "display_text", "") or getattr(p, "content", ""))[:200]
                for p in payloads
            )
            bb.record_crash(
                user_prompt=user_input[:500],
                bad_response=output[:500],
                critique=f"HallucinatieSchild blokkade: {rapport.reden_blokkade}",
                source="hallucination_shield",
            )
        except Exception as e:
            logger.debug("BlackBox logging mislukt: %s", e)

    def _publiceer_event(
        self, rapport: HallucinatieRapport, user_input: str,
    ):
        """Publiceer HALLUCINATION_BLOCKED event op NeuralBus."""
        if not HAS_BUS:
            return

        try:
            get_bus().publish(
                EventTypes.HALLUCINATION_BLOCKED,
                {
                    "score": rapport.totaal_score,
                    "reden": rapport.reden_blokkade,
                    "claims": len(rapport.claims),
                    "contradicties": len(rapport.contradictions),
                    "input_preview": user_input[:100],
                },
                bron="hallucination_shield",
            )
        except Exception as e:
            logger.debug("NeuralBus publicatie mislukt: %s", e)

    def get_stats(self) -> dict:
        """Retourneer thread-safe statistieken."""
        with self._lock:
            return dict(self._stats)

    def reset_stats(self):
        """Reset statistieken (voor tests)."""
        with self._lock:
            for key in self._stats:
                self._stats[key] = 0
