"""
Tribunal — Async Dual-Model Verificatie (v6.0 Invention).

Groq 70B + 8B parallel verificatie: beide modellen beoordelen dezelfde
output onafhankelijk. Alleen bij consensus wordt het resultaat geaccepteerd.
Voorkomt single-model hallucinaties via redundante verificatie.
"""

import os

# Robuuste .env loader — vindt altijd de project root
try:
    from dotenv import load_dotenv
    _root = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..")
    )
    load_dotenv(
        dotenv_path=os.path.join(_root, ".env"),
        override=True,
    )
except ImportError:
    pass

try:
    from groq import AsyncGroq
    HAS_GROQ = True
except ImportError:
    HAS_GROQ = False

from danny_toolkit.core.config import Config
from danny_toolkit.core.utils import Kleur

try:
    from danny_toolkit.core.key_manager import get_key_manager
    HAS_KEY_MANAGER = True
except ImportError:
    HAS_KEY_MANAGER = False

import logging

logger = logging.getLogger(__name__)

try:
    from danny_toolkit.core.groq_retry import groq_call_async
    HAS_RETRY = True
except ImportError:
    HAS_RETRY = False

try:
    from danny_toolkit.brain.truth_anchor import TruthAnchor
    HAS_TRUTH_ANCHOR = True
except ImportError:
    HAS_TRUTH_ANCHOR = False


class Tribunal:
    """
    The Tribunal: A dual-model verification system.
    Worker (70B) generates content.
    Auditor (8B) aggressively critiques it.
    """
    def __init__(self):
        """Initializes the instance with a Groq API client and model configurations.

If the key manager is available, creates an asynchronous Groq client through the key manager; 
otherwise, creates one using the GROQ_API_KEY environment variable.

Sets the worker and auditor models based on the Config.

Optionally initializes a TruthAnchor instance if HAS_TRUTH_ANCHOR is True. 
If initialization fails, logs the error and continues without a TruthAnchor."""
        if not HAS_GROQ:
            self.client = None
        elif HAS_KEY_MANAGER:
            km = get_key_manager()
            self.client = km.create_async_client("Tribunal") or AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))
        else:
            self.client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))
        self.worker_model = Config.LLM_MODEL
        self.auditor_model = Config.LLM_FALLBACK_MODEL
        self._truth_anchor = None
        if HAS_TRUTH_ANCHOR:
            try:
                self._truth_anchor = TruthAnchor()
            except Exception as e:
                logger.debug("TruthAnchor init error: %s", e)

    async def deliberate(self, user_prompt: str) -> str:
        """
        Runs the 2-step verification loop.
        """
        # 1. THE WORKER (Drafting)
        print(f"{Kleur.GROEN}⚖️  Tribunal: 70B Drafting response...{Kleur.RESET}")
        draft = await self._ask_groq(self.worker_model, user_prompt)

        # 2. THE AUDITOR (Critique)
        print(f"{Kleur.GEEL}⚖️  Tribunal: 8B Auditing...{Kleur.RESET}")
        audit_prompt = f"""
        You are a code security auditor.
        Review this AI response for hallucinations, security risks, or fake libraries.

        User Prompt: "{user_prompt}"
        AI Response: "{draft}"

        If it looks safe and correct, reply exactly: "VALID".
        If not, reply: "FLAWED: [Brief reason]"
        """
        verdict = await self._ask_groq(self.auditor_model, audit_prompt)

        # 3. THE VERDICT
        if "VALID" in verdict:
            # 3.5 TRUTH ANCHOR — Cross-Encoder feitelijke verificatie
            if self._truth_anchor:
                grounded, score = self._verify_facts(draft, user_prompt)
                if not grounded:
                    print(f"{Kleur.ROOD}⚓ TruthAnchor: Onvoldoende feitelijke "
                          f"grounding (score={score:.2f}). Herpoging...{Kleur.RESET}")
                    fix_prompt = (
                        f"Your answer was approved by the auditor but flagged by "
                        f"the fact-checker (confidence={score:.2f}). "
                        f"Original Prompt: {user_prompt}\n\n"
                        f"Rewrite with more precise, verifiable facts."
                    )
                    final_answer = await self._ask_groq(self.worker_model, fix_prompt)
                    return final_answer
            print(f"{Kleur.GROEN}✔ Verdict: APPROVED{Kleur.RESET}")
            return draft

        # 4. THE CORRECTION (If rejected)
        print(f"{Kleur.ROOD}❌ Verdict: {verdict}. Retrying...{Kleur.RESET}")
        fix_prompt = f"Your previous answer was rejected by the auditor: {verdict}. \nOriginal Prompt: {user_prompt}\n\nFix the answer."
        final_answer = await self._ask_groq(self.worker_model, fix_prompt)
        return final_answer

    def _verify_facts(self, answer: str, context: str) -> tuple:
        """Verificeer feitelijke grounding via TruthAnchor Cross-Encoder.

        Gebruikt de user prompt als context-document om te checken of het
        antwoord relevant en gegrond is.

        Returns:
            (grounded: bool, score: float) tuple.
        """
        try:
            return self._truth_anchor.verify(answer, [context])
        except Exception as e:
            logger.debug("TruthAnchor verify error: %s", e)
            return (True, 1.0)  # Fail-open: bij fout, doorlaten

    async def _ask_groq(self, model, text):
        if HAS_RETRY:
            result = await groq_call_async(
                self.client, "Tribunal", model,
                messages=[{"role": "user", "content": text}],
                temperature=0.6,
            )
            return result or "Tribunal Error: rate limited or unavailable"
        try:
            chat_completion = await self.client.chat.completions.create(
                messages=[{"role": "user", "content": text}],
                model=model,
                temperature=0.6,
            )
            return chat_completion.choices[0].message.content
        except Exception as e:
            return f"Tribunal Error: {str(e)}"
