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

from groq import AsyncGroq
from danny_toolkit.core.utils import Kleur


class Tribunal:
    """
    The Tribunal: A dual-model verification system.
    Worker (70B) generates content.
    Auditor (8B) aggressively critiques it.
    """
    def __init__(self):
        self.client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))
        self.worker_model = "meta-llama/llama-4-scout-17b-16e-instruct"
        self.auditor_model = "qwen/qwen3-32b"

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
            print(f"{Kleur.GROEN}✔ Verdict: APPROVED{Kleur.RESET}")
            return draft

        # 4. THE CORRECTION (If rejected)
        print(f"{Kleur.ROOD}❌ Verdict: {verdict}. Retrying...{Kleur.RESET}")
        fix_prompt = f"Your previous answer was rejected by the auditor: {verdict}. \nOriginal Prompt: {user_prompt}\n\nFix the answer."
        final_answer = await self._ask_groq(self.worker_model, fix_prompt)
        return final_answer

    async def _ask_groq(self, model, text):
        try:
            chat_completion = await self.client.chat.completions.create(
                messages=[{"role": "user", "content": text}],
                model=model,
                temperature=0.6,
            )
            return chat_completion.choices[0].message.content
        except Exception as e:
            return f"Tribunal Error: {str(e)}"
