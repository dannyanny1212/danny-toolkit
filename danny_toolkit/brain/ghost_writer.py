"""
GhostWriter — AST Scanner + Auto-Docstring Generator.


Scant Python bestanden op functies zonder docstring, genereert
Google-style docstrings via Groq, en schrijft ze optioneel terug
naar het bronbestand. CorticalStack dedup voorkomt herverwerking.

Gebruik:
    from danny_toolkit.brain.ghost_writer import GhostWriter

    writer = GhostWriter()
    await writer.haunt(dry_run=True)   # print suggesties
    await writer.haunt(dry_run=False)  # schrijf terug naar bestanden
"""

from __future__ import annotations

import ast
import logging
import os
import re
from typing import Optional

try:
    from groq import AsyncGroq
    HAS_GROQ = True
except ImportError:
    HAS_GROQ = False

from danny_toolkit.core.config import Config
from danny_toolkit.core.utils import Kleur

logger = logging.getLogger(__name__)

try:
    from danny_toolkit.core.key_manager import get_key_manager
    HAS_KEY_MANAGER = True
except ImportError:
    HAS_KEY_MANAGER = False

try:
    from danny_toolkit.brain.cortical_stack import get_cortical_stack
    HAS_STACK = True
except ImportError:
    HAS_STACK = False

try:
    from danny_toolkit.brain.model_sync import get_model_registry
    HAS_REGISTRY = True
except ImportError:
    HAS_REGISTRY = False


class GhostWriter:
    """
    THE GHOST WRITER (Invention #9)
    -------------------------------
    Multi-model token generator. Watches your code. If you write a
    function without a docstring, it writes one for you via the
    ModelRegistry fallback chain: Groq → Anthropic → NVIDIA NIM → Ollama.
    Supports dry-run (print only) and write-back (modify source files).
    """

    # Provider volgorde voor token generatie (snelste eerst)
    PROVIDER_CHAIN = ["groq", "nvidia_nim", "gemini", "ollama"]

    def __init__(self, watch_dir: str = None) -> None:
        """Init  ."""
        self.watch_dir = watch_dir or str(Config.BASE_DIR / "danny_toolkit")
        # Primary Groq client (backward-compatible)
        if not HAS_GROQ:
            self.client = None
        elif HAS_KEY_MANAGER:
            km = get_key_manager()
            self.client = km.create_async_client("GhostWriter")
            if not self.client:
                self.client = AsyncGroq(api_key=km.get_key("GhostWriter"))
        else:
            self.client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))
        self.model = Config.LLM_MODEL
        # Multi-model registry (lazy init)
        self._registry = None
        self._token_stats = {
            "totaal_tokens": 0,
            "totaal_calls": 0,
            "per_provider": {},
        }

    async def haunt(self, dry_run: bool = True, max_functies: int = 10) -> None:
        """Scan voor functies zonder docstring en genereer/pas ze toe.

        Args:
            dry_run: True = alleen printen, False = schrijf naar bestanden.
            max_functies: Maximum functies per cycle.
        """
        try:
            print(f"{Kleur.MAGENTA}GhostWriter haunt "
                  f"(dry_run={dry_run}, max={max_functies})...{Kleur.RESET}")
            verwerkt = 0
            for root, _, files in os.walk(self.watch_dir):
                for file in files:
                    if file.endswith(".py"):
                        filepath = os.path.join(root, file)
                        n = await self._inspect_file(
                            filepath, dry_run, max_functies - verwerkt,
                        )
                        verwerkt += n
                        if verwerkt >= max_functies:
                            print(f"{Kleur.GEEL}GhostWriter: max "
                                  f"{max_functies} bereikt, stop.{Kleur.RESET}")
                            return
        except Exception as e:
            logger.debug("GhostWriter haunt fout: %s", e)

    async def _inspect_file(
        self, filepath: str, dry_run: bool = True, max_remaining: int = 10,
    ) -> int:
        """Inspecteer een bestand, retourneer aantal verwerkte functies."""
        try:
            # Safety: alleen bestanden onder danny_toolkit/
            if "danny_toolkit" not in filepath.replace("\\", "/"):
                return 0

            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    source = f.read()
            except (IOError, UnicodeDecodeError):
                return 0

            # Skip bestanden met opt-out comment
            if "# no-ghost-write" in source:
                return 0

            try:
                tree = ast.parse(source)
            except SyntaxError:
                return 0

            verwerkt = 0
            for node in ast.walk(tree):
                if verwerkt >= max_remaining:
                    break
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if ast.get_docstring(node) is None:
                        # Check of al eerder verwerkt
                        if self._already_processed(filepath, node.name):
                            continue

                        print(f"{Kleur.GEEL}GhostWriter: "
                              f"{filepath} -> {node.name}{Kleur.RESET}")
                        docstring = await self._generate_docstring(
                            node, source,
                        )
                        if docstring:
                            if dry_run:
                                print(f"{Kleur.GROEN}Suggestie:\n"
                                      f"{docstring}{Kleur.RESET}")
                            else:
                                succes = self._write_back(
                                    filepath, source, node, docstring,
                                )
                                if succes:
                                    # Herlaad source na write
                                    try:
                                        with open(filepath, "r",
                                                  encoding="utf-8") as f:
                                            source = f.read()
                                    except Exception as e:
                                        logger.debug("GhostWriter re-read failed %s: %s", filepath, e)
                            self._log_suggestion(
                                filepath, node.name, docstring, not dry_run,
                            )
                            verwerkt += 1
            return verwerkt
        except Exception as e:
            logger.debug("GhostWriter _inspect_file fout: %s", e)
            return 0

    def _get_registry(self) -> None:
        """Lazy init ModelRegistry met auto-discover."""
        if self._registry is None and HAS_REGISTRY:
            try:
                self._registry = get_model_registry()
                self._registry.auto_discover()
            except Exception as e:
                logger.debug("GhostWriter registry init fout: %s", e)
        return self._registry

    def _track_tokens(self, provider: str, tokens: int) -> None:
        """Track token verbruik per provider."""
        self._token_stats["totaal_tokens"] += tokens
        self._token_stats["totaal_calls"] += 1
        stats = self._token_stats["per_provider"]
        if provider not in stats:
            stats[provider] = {"tokens": 0, "calls": 0}
        stats[provider]["tokens"] += tokens
        stats[provider]["calls"] += 1

    def get_token_stats(self) -> dict:
        """Return token generatie statistieken."""
        return dict(self._token_stats)

    async def _generate_docstring(
        self, node: ast.AST, full_source: str,
    ) -> Optional[str]:
        """Genereer een Google-style docstring via multi-model fallback chain.

        Chain: Groq (primary) → ModelRegistry workers (Groq fallback,
        Anthropic, NVIDIA NIM, Ollama) als primary faalt.
        """
        try:
            segment = ast.get_source_segment(full_source, node)
            if not segment:
                return None

            prompt = (
                "Write a Google-style docstring for this Python function.\n"
                f"Function Code:\n{segment}\n\n"
                "Return ONLY the docstring string (no triple quotes, no code)."
            )

            # Poging 1: Primary Groq client (snelste path)
            result = await self._try_groq_primary(prompt)
            if result:
                return result

            # Poging 2: ModelRegistry fallback chain
            result = await self._try_registry_chain(prompt)
            if result:
                return result

            logger.debug("GhostWriter: alle providers gefaald voor %s", node.name)
            return None
        except Exception as e:
            logger.debug("GhostWriter _generate_docstring fout: %s", e)
            return None

    async def _try_groq_primary(self, prompt: str) -> Optional[str]:
        """Probeer token generatie via primary Groq client."""
        try:
            if not self.client:
                return None
            chat = await self.client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=self.model,
                temperature=0.3,
            )
            content = chat.choices[0].message.content if chat.choices else ""
            tokens = getattr(chat.usage, "total_tokens", 0) if chat.usage else 0
            self._track_tokens("groq_primary", tokens)
            return content
        except Exception as e:
            logger.debug("GhostWriter groq primary fout: %s", e)
            return None

    @staticmethod
    def _strip_think_tags(text: str) -> str:
        """Verwijder <think>...</think> tags uit reasoning model output (qwen3-32b)."""
        return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()

    async def _try_registry_chain(self, prompt: str) -> Optional[str]:
        """Probeer token generatie via ModelRegistry fallback chain."""
        registry = self._get_registry()
        if not registry:
            return None

        for provider in self.PROVIDER_CHAIN:
            worker = registry.get_by_provider(provider)
            if worker and worker.is_available():
                try:
                    response = await worker.generate(
                        prompt=prompt,
                        system="You are a Python documentation expert. Generate concise Google-style docstrings.",
                    )
                    if response.content:
                        content = self._strip_think_tags(response.content)
                        if not content:
                            continue
                        self._track_tokens(
                            f"{response.provider}/{response.model_id}",
                            response.tokens_used,
                        )
                        logger.debug(
                            "GhostWriter: tokens via %s/%s (%d tokens, %.0fms)",
                            response.provider, response.model_id,
                            response.tokens_used, response.latency_ms,
                        )
                        return content
                except Exception as e:
                    logger.debug("GhostWriter %s fout: %s", provider, e)
                    continue

        return None

    def _write_back(
        self, filepath: str, source: str,
        node: object, docstring: str,
    ) -> bool:
        """Voeg gegenereerde docstring in het bronbestand in.

        Args:
            filepath: Pad naar het bronbestand.
            source: Huidige broncode.
            node: AST node (FunctionDef/AsyncFunctionDef).
            docstring: Gegenereerde docstring tekst.

        Returns:
            True als schrijven gelukt.
        """
        try:
            lines = source.splitlines(keepends=True)
            # Insert punt: regel voor eerste body statement
            insert_line = node.body[0].lineno - 1  # 0-indexed

            # Bepaal indentatie
            body_line = lines[insert_line] if insert_line < len(lines) else ""
            indent = len(body_line) - len(body_line.lstrip())
            if indent == 0:
                indent = (node.col_offset or 0) + 4

            # Formatteer docstring met triple quotes
            pad = " " * indent
            clean = docstring.strip().strip('"').strip("'").strip()
            formatted = f'{pad}"""{clean}"""\n'

            # Insert voor de eerste body statement
            lines.insert(insert_line, formatted)

            new_source = "".join(lines)

            # Verifieer syntax voor we schrijven
            try:
                ast.parse(new_source)
            except SyntaxError:
                logger.debug(
                    "GhostWriter: syntax error na insert, skip %s.%s",
                    filepath, node.name,
                )
                return False

            with open(filepath, "w", encoding="utf-8") as f:
                f.write(new_source)

            print(f"{Kleur.GROEN}GhostWriter: docstring geschreven "
                  f"-> {node.name}{Kleur.RESET}")
            return True
        except Exception as e:
            logger.debug("GhostWriter _write_back fout: %s", e)
            return False

    def _already_processed(self, filepath: str, func_name: str) -> bool:
        """Check CorticalStack of functie al eerder verwerkt is."""
        try:
            if not HAS_STACK:
                return False
            stack = get_cortical_stack()
            events = stack.get_recent_events(count=500)
            for evt in events:
                if (evt.get("action") == "ghost_write_applied"
                        and evt.get("details", {}).get("filepath") == filepath
                        and evt.get("details", {}).get("function") == func_name):
                    return True
            return False
        except Exception as e:
            logger.debug("GhostWriter _already_processed fout: %s", e)
            return False

    def _log_suggestion(
        self, filepath: str, func_name: str,
        docstring: str, applied: bool,
    ) -> None:
        """Log gegenereerde suggestie naar CorticalStack."""
        try:
            if not HAS_STACK:
                return
            stack = get_cortical_stack()
            action = "ghost_write_applied" if applied else "ghost_write_suggested"
            stack.log_event(
                actor="GhostWriter",
                action=action,
                details={
                    "filepath": filepath,
                    "function": func_name,
                    "docstring_length": len(docstring),
                    "applied": applied,
                },
            )
        except Exception as e:
            logger.debug("GhostWriter _log_suggestion fout: %s", e)
