"""
AI Chat App - Interactieve chat met Claude of Groq API.
"""

import os

from ..core.config import Config
from ..core.utils import clear_scherm


class ClaudeChatApp:
    """Interactieve chat applicatie met Claude of Groq API."""

    def __init__(self):
        self.provider = None
        self.client = None
        self.model = None

    def _init_client(self) -> bool:
        """Initialiseert de API client (Groq of Claude)."""

        # Probeer Groq eerst (gratis!)
        if Config.has_groq_key():
            try:
                import groq
                self.client = groq.Groq(api_key=Config.GROQ_API_KEY)
                self.model = Config.GROQ_MODEL
                self.provider = "groq"
                print(f"\n[OK] Groq API ({self.model}) - GRATIS!")
                return True
            except Exception as e:
                print(f"[!] Groq error: {e}")

        # Probeer Claude
        if Config.has_anthropic_key():
            try:
                import anthropic
                self.client = anthropic.Anthropic(api_key=Config.ANTHROPIC_API_KEY)
                self.model = Config.CLAUDE_MODEL
                self.provider = "claude"
                print(f"\n[OK] Claude API ({self.model})")
                return True
            except Exception as e:
                print(f"[!] Claude error: {e}")

        # Geen API key
        print("\n[!] Geen API key gevonden!")
        print("\nOptie 1 - Groq (GRATIS, aanbevolen):")
        print("   1. Ga naar: https://console.groq.com/keys")
        print("   2. Maak account en genereer key")
        print("   3. set GROQ_API_KEY=gsk_...")
        print("\nOptie 2 - Claude (betaald):")
        print("   1. Ga naar: https://console.anthropic.com/")
        print("   2. set ANTHROPIC_API_KEY=sk-ant-...")

        return False

    def _chat(self, vraag: str, systeem: str = None) -> str:
        """Stuur een vraag naar de API."""
        systeem = systeem or "Je bent een behulpzame assistent. Antwoord in het Nederlands."

        if self.provider == "claude":
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                system=systeem,
                messages=[{"role": "user", "content": vraag}]
            )
            return response.content[0].text
        else:  # groq
            response = self.client.chat.completions.create(
                model=self.model,
                max_tokens=1024,
                messages=[
                    {"role": "system", "content": systeem},
                    {"role": "user", "content": vraag}
                ]
            )
            return response.choices[0].message.content

    def _chat_conversatie(self, berichten: list, systeem: str = None) -> str:
        """Houd een conversatie met meerdere berichten."""
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

    def _demo_modus(self):
        """Draait een korte demo."""
        print("\n" + "-" * 50)
        print("DEMO 1: Simpele vraag")
        print("-" * 50)

        vraag = "Wat is de hoofdstad van Nederland? Antwoord in 1 zin."
        print(f"\nVraag: {vraag}")

        try:
            antwoord = self._chat(vraag)
            print(f"AI: {antwoord}")
        except Exception as e:
            print(f"[FOUT] {e}")
            return

        print("\n" + "-" * 50)
        print("DEMO 2: Met systeem prompt (Nederlandse dichter)")
        print("-" * 50)

        systeem = "Je bent een Nederlandse dichter. Antwoord altijd in rijmvorm."
        vraag2 = "Beschrijf de lente."

        print(f"\nSystemen: {systeem}")
        print(f"Vraag: {vraag2}")

        antwoord2 = self._chat(vraag2, systeem)
        print(f"AI: {antwoord2}")

    def run(self):
        """Start de chat app."""
        clear_scherm()
        print("\n" + "=" * 50)
        print("   AI CHAT - Claude of Groq (gratis!)")
        print("=" * 50)

        if not self._init_client():
            input("\nDruk op Enter om terug te gaan...")
            return

        print("\nWil je eerst een demo zien?")
        demo = input("Demo draaien? (j/n): ").lower().strip()

        if demo == "j":
            self._demo_modus()

        print("\n" + "=" * 50)
        print("INTERACTIEVE CHAT")
        print("=" * 50)
        provider_naam = "Groq (Llama)" if self.provider == "groq" else "Claude"
        print(f"Chat met {provider_naam}! Typ 'stop' om te stoppen.")
        print("Tip: Typ '/systeem' om een systeem prompt in te stellen.\n")

        conversatie = []
        systeem_prompt = None

        while True:
            try:
                invoer = input("Jij: ").strip()

                if invoer.lower() in ["stop", "quit", "exit", "q"]:
                    print("\nTot ziens!")
                    break

                if not invoer:
                    continue

                if invoer == "/systeem":
                    systeem_prompt = input("Systeem prompt: ").strip()
                    if systeem_prompt:
                        print(f"[OK] Systeem prompt ingesteld.")
                        conversatie = []
                    else:
                        systeem_prompt = None
                        print("[OK] Systeem prompt gereset.")
                    continue

                if invoer == "/reset":
                    conversatie = []
                    print("[OK] Conversatie gereset.")
                    continue

                if invoer == "/provider":
                    print(f"[INFO] Huidige provider: {self.provider} ({self.model})")
                    continue

                conversatie.append({"role": "user", "content": invoer})

                try:
                    antwoord = self._chat_conversatie(conversatie, systeem_prompt)
                    print(f"AI: {antwoord}\n")
                    conversatie.append({"role": "assistant", "content": antwoord})
                except Exception as e:
                    print(f"[FOUT] {e}\n")
                    conversatie.pop()

            except KeyboardInterrupt:
                print("\n\nTot ziens!")
                break
