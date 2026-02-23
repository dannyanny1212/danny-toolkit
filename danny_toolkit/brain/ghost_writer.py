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

import ast
import logging
import os
from typing import Optional

from groq import AsyncGroq
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


class GhostWriter:
    """
    THE GHOST WRITER (Invention #9)
    -------------------------------
    Watches your code. If you write a function without a docstring,
    it writes one for you. Supports dry-run (print only) and
    write-back (modify source files) modes.
    """

    def __init__(self, watch_dir: str = None):
        self.watch_dir = watch_dir or str(Config.BASE_DIR / "danny_toolkit")
        if HAS_KEY_MANAGER:
            km = get_key_manager()
            self.client = km.create_async_client("GhostWriter") or AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))
        else:
            self.client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))
        self.model = Config.LLM_MODEL

    async def haunt(self, dry_run: bool = True, max_functies: int = 10):
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
                                    except Exception:
                                        pass
                            self._log_suggestion(
                                filepath, node.name, docstring, not dry_run,
                            )
                            verwerkt += 1
            return verwerkt
        except Exception as e:
            logger.debug("GhostWriter _inspect_file fout: %s", e)
            return 0

    async def _generate_docstring(
        self, node: ast.AST, full_source: str,
    ) -> Optional[str]:
        """Genereer een Google-style docstring via Groq."""
        try:
            segment = ast.get_source_segment(full_source, node)
            if not segment:
                return None

            prompt = (
                "Write a Google-style docstring for this Python function.\n"
                f"Function Code:\n{segment}\n\n"
                "Return ONLY the docstring string (no triple quotes, no code)."
            )
            chat = await self.client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=self.model,
                temperature=0.3,
            )
            return chat.choices[0].message.content
        except Exception as e:
            logger.debug("GhostWriter _generate_docstring fout: %s", e)
            return None

    def _write_back(
        self, filepath: str, source: str,
        node, docstring: str,
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
    ):
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
