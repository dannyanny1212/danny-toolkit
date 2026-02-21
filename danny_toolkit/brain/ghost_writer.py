import os
import ast
from typing import Optional

from groq import AsyncGroq
from danny_toolkit.core.config import Config
from danny_toolkit.core.utils import Kleur


class GhostWriter:
    """
    THE GHOST WRITER (Invention #9)
    -------------------------------
    Watches your code. If you write a function without a docstring,
    it writes one for you.
    """
    def __init__(self, watch_dir: str = None):
        self.watch_dir = watch_dir or str(Config.BASE_DIR / "danny_toolkit")
        self.client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))
        self.model = "llama-3.1-8b-instant"

    async def haunt(self):
        """
        Scans for modified files and undocumented functions.
        """
        print(f"{Kleur.MAGENTA}👻 Ghost Writer is haunting the codebase...{Kleur.RESET}")
        for root, _, files in os.walk(self.watch_dir):
            for file in files:
                if file.endswith(".py"):
                    await self._inspect_file(os.path.join(root, file))

    async def _inspect_file(self, filepath: str):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                source = f.read()
        except (IOError, UnicodeDecodeError):
            return

        try:
            tree = ast.parse(source)
        except SyntaxError:
            return

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if ast.get_docstring(node) is None:
                    print(f"{Kleur.GEEL}👻 Missing docstring in "
                          f"{filepath} -> {node.name}{Kleur.RESET}")
                    docstring = await self._generate_docstring(node, source)
                    if docstring:
                        print(f"{Kleur.GROEN}Suggestion:\n{docstring}{Kleur.RESET}")

    async def _generate_docstring(self, node: ast.AST,
                                  full_source: str) -> Optional[str]:
        segment = ast.get_source_segment(full_source, node)
        if not segment:
            return None

        prompt = f"""
        Write a Google-style docstring for this Python function.
        Function Code:
        {segment}

        Return ONLY the docstring string (no triple quotes, no code).
        """
        try:
            chat = await self.client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=self.model,
                temperature=0.3,
            )
            return chat.choices[0].message.content
        except Exception as e:
            print(f"{Kleur.ROOD}👻 Ghost Writer Error: {e}{Kleur.RESET}")
            return None
