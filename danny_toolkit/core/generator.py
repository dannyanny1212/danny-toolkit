"""
Claude API Generator voor RAG systemen.
"""

from .config import Config


class Generator:
    """Genereert antwoorden met Claude API."""

    def __init__(self, api_key: str = None):
        import anthropic
        self.client = anthropic.Anthropic(
            api_key=api_key or Config.ANTHROPIC_API_KEY
        )
        self.model = Config.CLAUDE_MODEL
        print(f"   [OK] Claude API ({self.model})")

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

        response = self.client.messages.create(
            model=self.model,
            max_tokens=2048,
            system=systeem_prompt,
            messages=[{"role": "user", "content": user_prompt}]
        )

        return response.content[0].text

    def chat(self, berichten: list, systeem: str = None) -> str:
        """Simpele chat zonder RAG context."""
        response = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            system=systeem or "Je bent een behulpzame assistent. Antwoord in het Nederlands.",
            messages=berichten
        )
        return response.content[0].text
