import json
import os

from groq import AsyncGroq
from danny_toolkit.core.config import Config
from danny_toolkit.core.utils import Kleur

try:
    from danny_toolkit.brain.cortical_stack import get_cortical_stack
    HAS_STACK = True
except ImportError:
    HAS_STACK = False


class TheMirror:
    """
    THE MIRROR (Invention #8)
    -------------------------
    Reads the CorticalStack (memories) to build a dynamic User Profile.
    Injects this profile into every AI interaction context.
    """
    def __init__(self):
        self.profile_path = Config.DATA_DIR / "user_profile.json"
        self.client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))
        self.model = "meta-llama/llama-4-scout-17b-16e-instruct"

    async def reflect(self):
        """
        Analyzes the last 50 interactions to update the User Profile.
        Runs in background (e.g., daily).
        """
        if not HAS_STACK:
            return

        print(f"{Kleur.MAGENTA}🪞 The Mirror: Reflecting on user patterns...{Kleur.RESET}")

        # 1. Fetch recent history
        stack = get_cortical_stack()
        recent_events = stack.get_recent_events(count=50)
        if not recent_events:
            return

        # 2. Ask Groq to analyze you
        current_profile = self.load_profile()
        prompt = f"""
        Analyze these recent user interactions:
        {json.dumps(recent_events, default=str, ensure_ascii=False)}

        Current Profile: {json.dumps(current_profile, ensure_ascii=False)}

        Update the profile with:
        1. User's Coding Style (e.g., "Prefers async", "Hates comments")
        2. Knowledge Level (e.g., "Expert in Python, Novice in Docker")
        3. Current Goals (e.g., "Building a Jarvis")
        4. Mood/Tone preference.

        Return ONLY valid JSON with keys: coding_style, knowledge_level, current_goal, tone_preference
        """

        try:
            chat = await self.client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=self.model,
                temperature=0.4,
            )
            new_profile_json = chat.choices[0].message.content
            self.save_profile(new_profile_json)
            print(f"{Kleur.GROEN}🪞 Profile Updated.{Kleur.RESET}")
        except Exception as e:
            print(f"{Kleur.ROOD}🪞 Mirror Error: {e}{Kleur.RESET}")

    def get_context_injection(self) -> str:
        """
        Returns a system prompt snippet to inject into CentralBrain.
        """
        p = self.load_profile()
        if not p:
            return ""
        return (
            "[USER PROFILE]\n"
            f"- Style: {p.get('coding_style', 'Standard')}\n"
            f"- Level: {p.get('knowledge_level', 'Intermediate')}\n"
            f"- Goal: {p.get('current_goal', 'Unknown')}\n"
            f"- Tone: {p.get('tone_preference', 'Direct')}\n"
            "Adjust your answers to match this persona."
        )

    def load_profile(self) -> dict:
        if self.profile_path.exists():
            try:
                with open(self.profile_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return {}
        return {}

    def save_profile(self, data: str):
        """Parse JSON string from Groq and save."""
        try:
            parsed = json.loads(data)
        except json.JSONDecodeError:
            # Strip markdown fences if Groq wraps the response
            cleaned = data.strip().removeprefix("```json").removesuffix("```").strip()
            try:
                parsed = json.loads(cleaned)
            except json.JSONDecodeError:
                print(f"{Kleur.ROOD}🪞 Could not parse profile JSON{Kleur.RESET}")
                return

        Config.ensure_dirs()
        with open(self.profile_path, "w", encoding="utf-8") as f:
            json.dump(parsed, f, indent=2, ensure_ascii=False)
