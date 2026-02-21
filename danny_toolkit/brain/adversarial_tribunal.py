# danny_toolkit/brain/adversarial_tribunal.py
"""
Adversarial Tribunal — Multi-Agent Consensus for Hallucination Prevention
Uses a Generator → Skeptic → Judge loop to catch logic hallucinations.

Agent A (Generator): Proposes an answer.
Agent B (Skeptic): Hostile fact-checker that finds lies or logic errors.
The Judge (Governor): Accepts if Skeptic says TRUE, loops back if FALSE.

Max 3 retries before returning a system error.
"""

import asyncio
import logging
from typing import Optional, Dict, List

from danny_toolkit.core.utils import Kleur

try:
    from anthropic import Anthropic
    _HAS_ANTHROPIC = True
except ImportError:
    _HAS_ANTHROPIC = False

try:
    import requests as _requests
    _HAS_REQUESTS = True
except ImportError:
    _HAS_REQUESTS = False

logger = logging.getLogger(__name__)

# Skeptic system prompt — designed to be adversarial
_SKEPTIC_PROMPT = (
    "Je bent een vijandige feitenchecker. Je ENIGE taak is om PRECIES EEN "
    "leugen, logische fout, of onondersteunde bewering te vinden in de "
    "gegeven tekst. Vergelijk ELKE claim met de context.\n\n"
    "Regels:\n"
    "- Als je een fout vindt: antwoord EXACT met 'FALSE: [reden]'\n"
    "- Als alles klopt: antwoord EXACT met 'TRUE'\n"
    "- Wees meedogenloos. Vertrouw niets zonder bewijs in de context.\n"
    "- Controleer ook wiskundige berekeningen en logische gevolgtrekkingen."
)

# Generator system prompt — produces cited answers
_GENERATOR_PROMPT = (
    "Je bent een nauwkeurige AI-assistent. Beantwoord de vraag ALLEEN "
    "op basis van de gegeven context. Als informatie niet in de context "
    "staat, zeg dat eerlijk. Wees precies en feitelijk."
)


class AdversarialTribunal:
    """
    THE ADVERSARIAL TRIBUNAL
    ------------------------
    Multi-agent consensus loop that catches logic hallucinations by
    pitting a Generator against a Skeptic under Governor supervision.

    Flow:
        1. Generator produces answer from context
        2. Skeptic reviews answer against context
        3. If Skeptic says TRUE → return answer
        4. If Skeptic says FALSE → feed critique back to Generator
        5. Repeat up to max_retries times

    Usage:
        tribunal = AdversarialTribunal()
        result = tribunal.deliberate("Wat is RAG?", context_text)
        print(result.final_answer)
        print(result.rounds)  # how many rounds it took
    """

    def __init__(self, brain=None, max_retries: int = 3):
        """
        Initialize the Tribunal.

        Args:
            brain: Optional CentralBrain instance for LLM calls.
                   If None, uses direct Anthropic/Ollama API.
            max_retries: Maximum Generator→Skeptic rounds (default 3)
        """
        self.brain = brain
        self.max_retries = max_retries
        self.stats = {"accepted": 0, "retried": 0, "failed": 0}
        self._transcript: List[Dict] = []

        # Direct API setup (when no brain provided)
        self._client = None
        self._provider = None
        if brain is None:
            self._init_direct_client()

    def _init_direct_client(self):
        """Initialize a direct LLM client (Anthropic or Ollama)."""
        from danny_toolkit.core.config import Config

        if _HAS_ANTHROPIC and Config.has_anthropic_key():
            self._client = Anthropic()
            self._provider = "anthropic"
            logger.info("Tribunal using direct Anthropic client")
        elif _HAS_REQUESTS:
            # Check Ollama availability
            try:
                resp = _requests.get("http://localhost:11434/api/tags", timeout=3)
                if resp.status_code == 200:
                    self._provider = "ollama"
                    logger.info("Tribunal using direct Ollama client")
            except Exception:
                pass

        if not self._provider:
            logger.warning("Tribunal: geen AI provider beschikbaar")

    def _ask_llm(self, system: str, user_message: str) -> str:
        """Send a message to the LLM and return the response text."""
        if self.brain is not None:
            # Use CentralBrain's process_request (handles full fallback chain)
            return self.brain.process_request(
                user_input=user_message,
                use_tools=False,
            )

        # Direct Anthropic
        if self._provider == "anthropic" and self._client:
            response = self._client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=1500,
                system=system,
                messages=[{"role": "user", "content": user_message}],
            )
            return response.content[0].text

        # Direct Ollama
        if self._provider == "ollama":
            resp = _requests.post(
                "http://localhost:11434/api/chat",
                json={
                    "model": "gemma3:4b",
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user_message},
                    ],
                    "stream": False,
                },
                timeout=120,
            )
            return resp.json().get("message", {}).get("content", "")

        return "[Tribunal Error: Geen AI provider beschikbaar]"

    def deliberate(self, question: str, context: str) -> "TribunalVerdict":
        """
        Run the full Generator → Skeptic → Judge deliberation loop.

        Args:
            question: The user's question
            context: Retrieved context (from RAG or other source)

        Returns:
            TribunalVerdict with final_answer, rounds, and transcript
        """
        self._transcript = []

        print(f"\n{Kleur.BLAUW}[TRIBUNAL]{Kleur.RESET} Deliberation started "
              f"(max {self.max_retries} rounds)")

        # Round 1: Generator produces initial answer
        generator_prompt = (
            f"Context:\n{context}\n\n"
            f"Vraag: {question}\n\n"
            "Geef een nauwkeurig antwoord gebaseerd op de context."
        )
        current_answer = self._ask_llm(_GENERATOR_PROMPT, generator_prompt)

        self._transcript.append({
            "round": 0,
            "agent": "Generator",
            "content": current_answer,
        })
        print(f"  {Kleur.GEEL}[Generator]{Kleur.RESET} Answer proposed "
              f"({len(current_answer)} chars)")

        # Skeptic review loop
        for attempt in range(self.max_retries):
            round_num = attempt + 1

            # Skeptic reviews
            skeptic_prompt = (
                f"Controleer dit antwoord tegen de context.\n\n"
                f"Context:\n{context}\n\n"
                f"Antwoord om te controleren:\n{current_answer}\n\n"
                f"Oorspronkelijke vraag: {question}\n\n"
                "Als je een fout vindt: 'FALSE: [reden]'\n"
                "Als alles klopt: 'TRUE'"
            )
            critique = self._ask_llm(_SKEPTIC_PROMPT, skeptic_prompt)

            self._transcript.append({
                "round": round_num,
                "agent": "Skeptic",
                "content": critique,
            })

            # Judge evaluates Skeptic's verdict
            critique_upper = critique.strip().upper()

            if critique_upper.startswith("TRUE") or "NO ERROR" in critique_upper:
                # ACCEPTED
                print(f"  {Kleur.GROEN}[Skeptic R{round_num}]{Kleur.RESET} "
                      f"TRUE — answer accepted")
                self.stats["accepted"] += 1
                return TribunalVerdict(
                    final_answer=current_answer,
                    accepted=True,
                    rounds=round_num,
                    transcript=self._transcript,
                )

            # REJECTED — extract reason
            reason = critique
            if "FALSE:" in critique.upper():
                reason = critique.split(":", 1)[1].strip() if ":" in critique else critique

            print(f"  {Kleur.ROOD}[Skeptic R{round_num}]{Kleur.RESET} "
                  f"FALSE — {reason[:80]}...")
            self.stats["retried"] += 1

            self._transcript.append({
                "round": round_num,
                "agent": "Judge",
                "content": f"REJECTED: {reason}",
            })

            # Generator corrects based on feedback
            correction_prompt = (
                f"Je vorige antwoord is afgekeurd door de feitenchecker.\n\n"
                f"Kritiek: {reason}\n\n"
                f"Originele context:\n{context}\n\n"
                f"Originele vraag: {question}\n\n"
                "Corrigeer je antwoord. Wees preciezer en feitelijker."
            )
            current_answer = self._ask_llm(_GENERATOR_PROMPT, correction_prompt)

            self._transcript.append({
                "round": round_num,
                "agent": "Generator",
                "content": current_answer,
            })
            print(f"  {Kleur.GEEL}[Generator R{round_num}]{Kleur.RESET} "
                  f"Corrected answer ({len(current_answer)} chars)")

        # Exhausted retries
        print(f"  {Kleur.ROOD}[TRIBUNAL]{Kleur.RESET} "
              f"Failed after {self.max_retries} rounds")
        self.stats["failed"] += 1

        return TribunalVerdict(
            final_answer=(
                "[Tribunal: Kon waarheid niet verifiëren na "
                f"{self.max_retries} pogingen]\n\n"
                f"Laatste antwoord (ONGEVALIDEERD):\n{current_answer}"
            ),
            accepted=False,
            rounds=self.max_retries,
            transcript=self._transcript,
        )

    def get_stats(self) -> Dict:
        """Return tribunal statistics."""
        total = sum(self.stats.values())
        return {
            **self.stats,
            "total": total,
            "acceptance_rate": (
                f"{self.stats['accepted'] / total * 100:.1f}%"
                if total > 0 else "N/A"
            ),
        }

    async def adeliberate(self, question: str, context: str = "") -> "TribunalVerdict":
        """Async wrapper — draait sync deliberate() in thread."""
        return await asyncio.to_thread(self.deliberate, question, context)

    def get_transcript(self) -> List[Dict]:
        """Return the full transcript of the last deliberation."""
        return self._transcript


class TribunalVerdict:
    """Result of an Adversarial Tribunal deliberation."""

    __slots__ = ("final_answer", "accepted", "rounds", "transcript")

    def __init__(self, final_answer: str, accepted: bool, rounds: int,
                 transcript: List[Dict]):
        self.final_answer = final_answer
        self.accepted = accepted
        self.rounds = rounds
        self.transcript = transcript

    def __bool__(self):
        return self.accepted

    def __repr__(self):
        status = "ACCEPTED" if self.accepted else "REJECTED"
        return f"TribunalVerdict({status}, rounds={self.rounds})"
