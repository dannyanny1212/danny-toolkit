"""
Claude Chat App - Interactieve chat met Claude API.
"""

import os

from ..core.config import Config
from ..core.utils import clear_scherm


class ClaudeChatApp:
    """Interactieve chat applicatie met Claude API."""

    def __init__(self):
        self.api_key = Config.ANTHROPIC_API_KEY
        self.client = None
        self.model = Config.CLAUDE_MODEL

    def _init_client(self) -> bool:
        """Initialiseert de Anthropic client."""
        if not self.api_key:
            print("\n[!] Geen API key gevonden!")
            print("\nZo krijg je een API key:")
            print("1. Ga naar: https://console.anthropic.com/")
            print("2. Maak een account of log in")
            print("3. Ga naar 'API Keys'")
            print("4. Klik 'Create Key'")
            print("\nStel de key in:")
            print("  Windows: set ANTHROPIC_API_KEY=sk-ant-...")
            print("  Mac/Linux: export ANTHROPIC_API_KEY=sk-ant-...")
            print("\nOf voer hier je key in (alleen voor testen):")

            self.api_key = input("\nAPI Key: ").strip()
            if not self.api_key:
                print("Geen key ingevoerd.")
                return False

        try:
            import anthropic
            self.client = anthropic.Anthropic(api_key=self.api_key)
            print("\n[OK] API key gevalideerd!")
            return True
        except Exception as e:
            print(f"\n[FOUT] {e}")
            return False

    def _chat(self, vraag: str, systeem: str = None) -> str:
        """Stuur een vraag naar Claude."""
        response = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            system=systeem or "Je bent een behulpzame assistent. Antwoord in het Nederlands.",
            messages=[{"role": "user", "content": vraag}]
        )
        return response.content[0].text

    def _chat_conversatie(self, berichten: list, systeem: str = None) -> str:
        """Houd een conversatie met meerdere berichten."""
        response = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            system=systeem or "Je bent een behulpzame assistent. Antwoord in het Nederlands.",
            messages=berichten
        )
        return response.content[0].text

    def _demo_modus(self):
        """Draait een korte demo."""
        print("\n" + "-" * 50)
        print("DEMO 1: Simpele vraag")
        print("-" * 50)

        vraag = "Wat is de hoofdstad van Nederland? Antwoord in 1 zin."
        print(f"\nVraag: {vraag}")

        try:
            antwoord = self._chat(vraag)
            print(f"Claude: {antwoord}")
        except Exception as e:
            print(f"[FOUT] {e}")
            return

        print("\n" + "-" * 50)
        print("DEMO 2: Met systeem prompt (Nederlandse dichter)")
        print("-" * 50)

        systeem = "Je bent een Nederlandse dichter. Antwoord altijd in rijmvorm."
        vraag2 = "Beschrijf het weer vandaag."

        print(f"\nSystemen: {systeem}")
        print(f"Vraag: {vraag2}")

        antwoord2 = self._chat(vraag2, systeem)
        print(f"Claude: {antwoord2}")

    def run(self):
        """Start de chat app."""
        clear_scherm()
        print("\n" + "=" * 50)
        print("   CLAUDE CHAT - Interactieve AI Chat")
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
        print("Chat met Claude! Typ 'stop' om te stoppen.")
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
                        conversatie = []  # Reset conversatie
                    else:
                        systeem_prompt = None
                        print("[OK] Systeem prompt gereset.")
                    continue

                if invoer == "/reset":
                    conversatie = []
                    print("[OK] Conversatie gereset.")
                    continue

                conversatie.append({"role": "user", "content": invoer})

                try:
                    antwoord = self._chat_conversatie(conversatie, systeem_prompt)
                    print(f"Claude: {antwoord}\n")
                    conversatie.append({"role": "assistant", "content": antwoord})
                except Exception as e:
                    print(f"[FOUT] {e}\n")
                    conversatie.pop()  # Verwijder mislukte vraag

            except KeyboardInterrupt:
                print("\n\nTot ziens!")
                break
