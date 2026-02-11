"""
AI Generator voor RAG systemen.
Versie 2.0 - Met streaming, retry logic en templates.
Ondersteunt: Claude API
"""

import time
from typing import Generator as TypingGenerator, List, Dict, Optional, Callable
from .config import Config


# =============================================================================
# PROMPT TEMPLATES
# =============================================================================

class PromptTemplates:
    """Verzameling van prompt templates voor verschillende taken."""

    RAG_SYSTEEM = """Je bent een behulpzame AI-assistent die vragen beantwoordt.

INSTRUCTIES:
1. Gebruik de informatie uit de DOCUMENTEN sectie om de vraag te beantwoorden
2. Geef ALLE relevante details uit de documenten - wees niet te kort
3. Als informatie in de documenten staat, geef deze volledig weer
4. Citeer de bron met [Bron: naam]
5. Antwoord in het Nederlands
6. Alleen als er echt GEEN informatie is, zeg dat dan"""

    RAG_USER = """DOCUMENTEN:
{context}

VRAAG: {vraag}

Beantwoord de vraag op basis van de documenten."""

    SAMENVATTING = """Maak een beknopte samenvatting van de volgende tekst.
Focus op de hoofdpunten en belangrijkste informatie.

TEKST:
{tekst}

SAMENVATTING:"""

    VERTALING = """Vertaal de volgende tekst naar {taal}.
Behoud de oorspronkelijke betekenis en toon.

TEKST:
{tekst}

VERTALING:"""

    CODE_REVIEW = """Analyseer de volgende code en geef feedback.
Let op: bugs, security issues, performance, leesbaarheid.

CODE:
```{taal}
{code}
```

ANALYSE:"""

    CODE_UITLEG = """Leg de volgende code uit in begrijpelijke taal.
Beschrijf wat de code doet, stap voor stap.

CODE:
```{taal}
{code}
```

UITLEG:"""

    VRAAG_BEANTWOORDING = """Beantwoord de volgende vraag zo volledig mogelijk.

VRAAG: {vraag}

ANTWOORD:"""

    CONVERSATIE = """Je bent een behulpzame assistent.
Antwoord in het Nederlands tenzij anders gevraagd.
Wees vriendelijk maar professioneel."""

    CREATIEF_SCHRIJVEN = """Je bent een creatieve schrijver.
Schrijf {type} over het volgende onderwerp.
Stijl: {stijl}

ONDERWERP: {onderwerp}"""

    @classmethod
    def custom(cls, template: str, **kwargs) -> str:
        """Vul een custom template in met variabelen."""
        return template.format(**kwargs)


# =============================================================================
# RETRY LOGIC
# =============================================================================

class RetryConfig:
    """Configuratie voor retry logic."""

    def __init__(self, max_pogingen: int = 3,
                 basis_wachttijd: float = 1.0,
                 max_wachttijd: float = 30.0,
                 exponentieel: bool = True):
        """
        Initialiseer retry configuratie.

        Args:
            max_pogingen: Maximum aantal pogingen
            basis_wachttijd: Basis wachttijd in seconden
            max_wachttijd: Maximum wachttijd in seconden
            exponentieel: Gebruik exponential backoff
        """
        self.max_pogingen = max_pogingen
        self.basis_wachttijd = basis_wachttijd
        self.max_wachttijd = max_wachttijd
        self.exponentieel = exponentieel

    def bereken_wachttijd(self, poging: int) -> float:
        """Bereken wachttijd voor huidige poging."""
        if self.exponentieel:
            wachttijd = self.basis_wachttijd * (2 ** poging)
        else:
            wachttijd = self.basis_wachttijd

        return min(wachttijd, self.max_wachttijd)


def met_retry(func: Callable, retry_config: RetryConfig = None,
              retry_excepties: tuple = None) -> Callable:
    """
    Decorator voor retry logic.

    Args:
        func: Functie om te wrappen
        retry_config: Retry configuratie
        retry_excepties: Tuple van exceptie types om te retryen
    """
    config = retry_config or RetryConfig()
    excepties = retry_excepties or (Exception,)

    def wrapper(*args, **kwargs):
        laatste_exceptie = None

        for poging in range(config.max_pogingen):
            try:
                return func(*args, **kwargs)
            except excepties as e:
                laatste_exceptie = e
                if poging < config.max_pogingen - 1:
                    wachttijd = config.bereken_wachttijd(poging)
                    print(f"   [!] Poging {poging + 1} mislukt: {e}")
                    print(f"       Wacht {wachttijd:.1f}s voor volgende poging...")
                    time.sleep(wachttijd)

        raise laatste_exceptie

    return wrapper


# =============================================================================
# GENERATOR CLASS
# =============================================================================

class Generator:
    """Genereert antwoorden met Claude API."""

    def __init__(self, provider: str = "auto", api_key: str = None,
                 retry_config: RetryConfig = None):
        """
        Initialiseer generator.

        Args:
            provider: "claude" of "auto" (kiest beste beschikbare)
            api_key: Optionele API key (anders uit environment)
            retry_config: Optionele retry configuratie
        """
        self.provider = provider
        self.client = None
        self.model = None
        self.retry_config = retry_config or RetryConfig()
        self._statistieken = {
            "api_calls": 0,
            "tokens_in": 0,
            "tokens_uit": 0,
            "fouten": 0
        }

        if provider == "auto":
            # TODO: Groq verwijderd — alleen Claude
            if Config.has_anthropic_key():
                self._init_claude(api_key)
            else:
                raise ValueError(
                    "Geen API key gevonden (ANTHROPIC_API_KEY)"
                )
        elif provider == "groq":
            raise ValueError(
                "Groq provider is verwijderd"
            )
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
        """Groq API verwijderd."""
        # TODO: Groq verwijderd — voeg hier een nieuwe provider toe
        raise ValueError("Groq provider is verwijderd")

    def genereer(self, vraag: str, context: list, max_tokens: int = 2048) -> str:
        """Genereer antwoord op basis van vraag en context."""
        context_str = "\n\n---\n\n".join([
            f"[Bron: {c['metadata'].get('bron', 'onbekend')}]\n{c['tekst']}"
            for c in context
        ])

        user_prompt = PromptTemplates.RAG_USER.format(
            context=context_str,
            vraag=vraag
        )

        return self._call_api_met_retry(
            PromptTemplates.RAG_SYSTEEM,
            user_prompt,
            max_tokens
        )

    def chat(self, berichten: list, systeem: str = None,
             max_tokens: int = 1024) -> str:
        """Simpele chat zonder RAG context."""
        systeem = systeem or PromptTemplates.CONVERSATIE

        if self.provider == "claude":
            response = self._claude_chat(berichten, systeem, max_tokens)
        else:
            response = self._groq_chat(berichten, systeem, max_tokens)

        self._statistieken["api_calls"] += 1
        return response

    def _claude_chat(self, berichten: list, systeem: str,
                     max_tokens: int) -> str:
        """Chat via Claude API."""
        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=systeem,
            messages=berichten
        )
        self._update_token_stats(response)
        return response.content[0].text

    def _groq_chat(self, berichten: list, systeem: str,
                   max_tokens: int) -> str:
        """Groq API verwijderd."""
        # TODO: Groq verwijderd
        raise ValueError("Groq provider is verwijderd")

    def _call_api_met_retry(self, systeem: str, user: str,
                            max_tokens: int) -> str:
        """Roep API aan met retry logic."""

        def _api_call():
            return self._call_api(systeem, user, max_tokens)

        try:
            return met_retry(
                _api_call,
                self.retry_config,
                (Exception,)
            )()
        except Exception as e:
            self._statistieken["fouten"] += 1
            raise e

    def _call_api(self, systeem: str, user: str, max_tokens: int) -> str:
        """Roep de API aan (Claude of Groq)."""
        self._statistieken["api_calls"] += 1

        if self.provider == "claude":
            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=systeem,
                messages=[{"role": "user", "content": user}]
            )
            self._update_token_stats(response)
            return response.content[0].text
        else:
            # TODO: Groq verwijderd
            raise ValueError(
                f"Provider '{self.provider}' niet ondersteund"
            )

    def _update_token_stats(self, response):
        """Update token statistieken voor Claude."""
        try:
            self._statistieken["tokens_in"] += response.usage.input_tokens
            self._statistieken["tokens_uit"] += response.usage.output_tokens
        except AttributeError:
            pass

    def _update_token_stats_groq(self, response):
        """Groq verwijderd — stub."""
        # TODO: Groq verwijderd
        pass

    # =========================================================================
    # STREAMING
    # =========================================================================

    def stream(self, vraag: str, context: list = None,
               systeem: str = None) -> TypingGenerator[str, None, None]:
        """
        Stream antwoord token voor token.

        Args:
            vraag: De vraag/prompt
            context: Optionele RAG context
            systeem: Optionele systeem prompt

        Yields:
            Tokens van het antwoord
        """
        if context:
            context_str = "\n\n---\n\n".join([
                f"[Bron: {c['metadata'].get('bron', 'onbekend')}]\n{c['tekst']}"
                for c in context
            ])
            user_prompt = PromptTemplates.RAG_USER.format(
                context=context_str,
                vraag=vraag
            )
            systeem = systeem or PromptTemplates.RAG_SYSTEEM
        else:
            user_prompt = vraag
            systeem = systeem or PromptTemplates.CONVERSATIE

        self._statistieken["api_calls"] += 1

        if self.provider == "claude":
            yield from self._stream_claude(systeem, user_prompt)
        else:
            # TODO: Groq verwijderd
            raise ValueError(
                f"Provider '{self.provider}' niet ondersteund"
            )

    def _stream_claude(self, systeem: str,
                       user: str) -> TypingGenerator[str, None, None]:
        """Stream via Claude API."""
        with self.client.messages.stream(
            model=self.model,
            max_tokens=2048,
            system=systeem,
            messages=[{"role": "user", "content": user}]
        ) as stream:
            for text in stream.text_stream:
                yield text

    def _stream_groq(self, systeem: str,
                     user: str) -> TypingGenerator[str, None, None]:
        """Groq verwijderd — stub."""
        # TODO: Groq verwijderd
        raise ValueError("Groq provider is verwijderd")

    def stream_print(self, vraag: str, context: list = None,
                     systeem: str = None) -> str:
        """Stream en print direct naar console, retourneer volledige tekst."""
        volledige_tekst = ""

        for token in self.stream(vraag, context, systeem):
            print(token, end="", flush=True)
            volledige_tekst += token

        print()  # Nieuwe regel aan het eind
        return volledige_tekst

    # =========================================================================
    # TEMPLATE HELPERS
    # =========================================================================

    def samenvatting(self, tekst: str, max_tokens: int = 500) -> str:
        """Maak een samenvatting van tekst."""
        prompt = PromptTemplates.SAMENVATTING.format(tekst=tekst)
        return self._call_api_met_retry(
            "Je bent een expert in het samenvatten van tekst.",
            prompt,
            max_tokens
        )

    def vertaal(self, tekst: str, taal: str = "Engels",
                max_tokens: int = 2048) -> str:
        """Vertaal tekst naar een andere taal."""
        prompt = PromptTemplates.VERTALING.format(tekst=tekst, taal=taal)
        return self._call_api_met_retry(
            "Je bent een professionele vertaler.",
            prompt,
            max_tokens
        )

    def code_review(self, code: str, taal: str = "python",
                    max_tokens: int = 1024) -> str:
        """Analyseer code."""
        prompt = PromptTemplates.CODE_REVIEW.format(code=code, taal=taal)
        return self._call_api_met_retry(
            "Je bent een senior software engineer die code reviews doet.",
            prompt,
            max_tokens
        )

    def code_uitleg(self, code: str, taal: str = "python",
                    max_tokens: int = 1024) -> str:
        """Leg code uit."""
        prompt = PromptTemplates.CODE_UITLEG.format(code=code, taal=taal)
        return self._call_api_met_retry(
            "Je bent een geduldige programmeerleraar.",
            prompt,
            max_tokens
        )

    def beantwoord(self, vraag: str, max_tokens: int = 1024) -> str:
        """Beantwoord een algemene vraag."""
        prompt = PromptTemplates.VRAAG_BEANTWOORDING.format(vraag=vraag)
        return self._call_api_met_retry(
            "Je bent een kennisrijke assistent.",
            prompt,
            max_tokens
        )

    def creatief(self, onderwerp: str, type_: str = "verhaal",
                 stijl: str = "neutraal", max_tokens: int = 2048) -> str:
        """Genereer creatieve tekst."""
        prompt = PromptTemplates.CREATIEF_SCHRIJVEN.format(
            type=type_,
            stijl=stijl,
            onderwerp=onderwerp
        )
        return self._call_api_met_retry(
            "Je bent een creatieve schrijver.",
            prompt,
            max_tokens
        )

    # =========================================================================
    # STATISTIEKEN
    # =========================================================================

    def statistieken(self) -> dict:
        """Retourneer gebruiksstatistieken."""
        return {
            "provider": self.provider,
            "model": self.model,
            **self._statistieken,
            "totaal_tokens": (
                self._statistieken["tokens_in"] +
                self._statistieken["tokens_uit"]
            )
        }

    def reset_statistieken(self):
        """Reset statistieken."""
        self._statistieken = {
            "api_calls": 0,
            "tokens_in": 0,
            "tokens_uit": 0,
            "fouten": 0
        }


# =============================================================================
# SPECIFIEKE GENERATORS
# =============================================================================

class GroqGenerator(Generator):
    """Groq verwijderd — gebruik ClaudeGenerator."""

    def __init__(self, api_key: str = None, retry_config: RetryConfig = None):
        # TODO: Groq verwijderd — fallback naar Claude
        super().__init__(
            provider="claude",
            api_key=api_key,
            retry_config=retry_config
        )


class ClaudeGenerator(Generator):
    """Specifieke generator voor Claude."""

    def __init__(self, api_key: str = None, retry_config: RetryConfig = None):
        super().__init__(
            provider="claude",
            api_key=api_key,
            retry_config=retry_config
        )


# =============================================================================
# MULTI-PROVIDER FALLBACK
# =============================================================================

class FallbackGenerator:
    """Generator met automatische fallback naar andere providers."""

    def __init__(self, primair: str = "claude", secundair: str = "claude"):
        """
        Initialiseer met primaire en secundaire provider.

        Args:
            primair: Eerste keuze provider
            secundair: Fallback provider
        """
        self.primair = None
        self.secundair = None
        self.actief = None

        # Probeer primaire provider
        try:
            self.primair = Generator(provider=primair)
            self.actief = self.primair
        except Exception as e:
            print(f"   [!] Primaire provider ({primair}) niet beschikbaar: {e}")

        # Probeer secundaire provider
        try:
            self.secundair = Generator(provider=secundair)
            if self.actief is None:
                self.actief = self.secundair
        except Exception as e:
            print(f"   [!] Secundaire provider ({secundair}) niet beschikbaar: {e}")

        if self.actief is None:
            raise ValueError("Geen enkele provider beschikbaar")

    def genereer(self, vraag: str, context: list, **kwargs) -> str:
        """Genereer met automatische fallback."""
        try:
            return self.actief.genereer(vraag, context, **kwargs)
        except Exception as e:
            print(f"   [!] {self.actief.provider} mislukt: {e}")

            # Probeer andere provider
            andere = self.secundair if self.actief == self.primair else self.primair
            if andere:
                print(f"   [>] Fallback naar {andere.provider}")
                self.actief = andere
                return self.actief.genereer(vraag, context, **kwargs)

            raise e

    def __getattr__(self, naam):
        """Delegate andere methoden naar actieve generator."""
        return getattr(self.actief, naam)
