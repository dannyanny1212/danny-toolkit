"""
AI Generator voor RAG systemen.
Ondersteunt: Claude API en Groq API (gratis!)
"""

from .config import Config


class Generator:
    """Genereert antwoorden met Claude of Groq API."""

    def __init__(self, provider: str = "auto", api_key: str = None):
        """
        Initialiseer generator.

        Args:
            provider: "claude", "groq", of "auto" (kiest beste beschikbare)
            api_key: Optionele API key (anders uit environment)
        """
        self.provider = provider
        self.client = None
        self.model = None

        if provider == "auto":
            # Probeer Groq eerst (gratis), dan Claude
            if Config.has_groq_key():
                self._init_groq(api_key)
            elif Config.has_anthropic_key():
                self._init_claude(api_key)
            else:
                raise ValueError("Geen API key gevonden (GROQ_API_KEY of ANTHROPIC_API_KEY)")
        elif provider == "groq":
            self._init_groq(api_key)
        elif provider == "claude":
            self._init_claude(api_key)
        else:
            raise ValueError(f"Onbekende provider: {provider}")

    def _init_claude(self, api_key: str = None):
        """Initialiseer Claude API."""
        import anthropic
        self.client = anthropic.Anthropic(
            api_key=api_key or Config.ANTHROPIC_API_KEY
        )
        self.model = Config.CLAUDE_MODEL
        self.provider = "claude"
        print(f"   [OK] Claude API ({self.model})")

    def _init_groq(self, api_key: str = None):
        """Initialiseer Groq API."""
        import groq
        self.client = groq.Groq(
            api_key=api_key or Config.GROQ_API_KEY
        )
        self.model = Config.GROQ_MODEL
        self.provider = "groq"
        print(f"   [OK] Groq API ({self.model}) - GRATIS!")

    def genereer(self, vraag: str, context: list) -> str:
        """Genereer antwoord op basis van vraag en context."""
        context_str = "\n\n---\n\n".join([
            f"[Bron: {c['metadata'].get('bron', 'onbekend')}]\n{c['tekst']}"
            for c in context
        ])

        systeem_prompt = """Je bent een nauwkeurige AI-assistent.

REGELS:
1. Gebruik ALLEEN informatie uit de gegeven documenten
2. Als het antwoord niet in de documenten staat, zeg dat eerlijk
3. Citeer bronnen waar relevant
4. Antwoord in het Nederlands
5. Wees beknopt maar volledig"""

        user_prompt = f"""DOCUMENTEN:
{context_str}

VRAAG: {vraag}

Beantwoord de vraag op basis van de documenten."""

        return self._call_api(systeem_prompt, user_prompt)

    def chat(self, berichten: list, systeem: str = None) -> str:
        """Simpele chat zonder RAG context."""
        systeem = systeem or "Je bent een behulpzame assistent. Antwoord in het Nederlands."

        if self.provider == "claude":
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                system=systeem,
                messages=berichten
            )
            return response.content[0].text
        else:  # groq
            messages = [{"role": "system", "content": systeem}] + berichten
            response = self.client.chat.completions.create(
                model=self.model,
                max_tokens=1024,
                messages=messages
            )
            return response.choices[0].message.content

    def _call_api(self, systeem: str, user: str) -> str:
        """Roep de API aan (Claude of Groq)."""
        if self.provider == "claude":
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2048,
                system=systeem,
                messages=[{"role": "user", "content": user}]
            )
            return response.content[0].text
        else:  # groq
            response = self.client.chat.completions.create(
                model=self.model,
                max_tokens=2048,
                messages=[
                    {"role": "system", "content": systeem},
                    {"role": "user", "content": user}
                ]
            )
            return response.choices[0].message.content


class GroqGenerator(Generator):
    """Specifieke generator voor Groq (gratis!)."""

    def __init__(self, api_key: str = None):
        super().__init__(provider="groq", api_key=api_key)


class ClaudeGenerator(Generator):
    """Specifieke generator voor Claude."""

    def __init__(self, api_key: str = None):
        super().__init__(provider="claude", api_key=api_key)
