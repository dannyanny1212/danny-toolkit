# danny_toolkit/brain/reality_anchor.py
"""
Reality Anchor — Code Symbol Validator (Library Hallucination Prevention)
Scans the actual danny_toolkit codebase via AST to build a Truth Map of
valid classes, functions, and methods. Rejects LLM-generated code that
references symbols which do not exist.
"""

import ast
import logging
import os
from typing import Dict, List, Set, Optional

from danny_toolkit.core.utils import Kleur

logger = logging.getLogger(__name__)


class RealityAnchor:
    """
    THE REALITY ANCHOR
    ------------------
    Builds a Truth Map of every class, function, and method in the codebase
    by parsing Python source files with the AST module. Validates LLM-generated
    code blocks against this map to catch "library hallucination" — when the LLM
    invents methods like danny_toolkit.core.engine.run_fast() that don't exist.

    Usage:
        anchor = RealityAnchor("C:/Users/danny/danny-toolkit/danny_toolkit")
        result = anchor.validate_code_block(llm_generated_code)
        if not result.is_valid:
            print(result.violations)  # list of fake symbols the LLM invented
    """

    def __init__(self, root_dir: str):
        self.root_dir = str(root_dir)
        self.valid_symbols: Dict[str, Set[str]] = {}  # {module: {symbols}}
        self.class_methods: Dict[str, Dict[str, Set[str]]] = {}  # {module: {class: {methods}}}
        self._total_files = 0
        self._total_symbols = 0
        self._scan_codebase()

    def _scan_codebase(self):
        """Walk the codebase and build the Truth Map via AST parsing."""
        print(f"{Kleur.BLAUW}[ANCHOR]{Kleur.RESET} Scanning reality (codebase)...")

        for root, dirs, files in os.walk(self.root_dir):
            # Skip __pycache__, venv, .git
            dirs[:] = [d for d in dirs if d not in {"__pycache__", "venv", ".git", "node_modules"}]

            for filename in files:
                if filename.endswith(".py"):
                    self._parse_file(os.path.join(root, filename))

        print(
            f"{Kleur.GROEN}[ANCHOR]{Kleur.RESET} Truth Map: "
            f"{self._total_files} files, {len(self.valid_symbols)} modules, "
            f"{self._total_symbols} symbols"
        )

    def _parse_file(self, filepath: str):
        """Parse a single Python file and extract all defined symbols."""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                source = f.read()
            tree = ast.parse(source, filename=filepath)
        except (SyntaxError, UnicodeDecodeError) as e:
            logger.debug("Skipping unparseable file %s: %s", filepath, e)
            return

        # Convert path to module notation: danny_toolkit/core/engine.py → danny_toolkit.core.engine
        rel_path = os.path.relpath(filepath, os.path.dirname(self.root_dir))
        module_name = rel_path.replace(os.sep, ".").replace(".py", "")
        if module_name.endswith(".__init__"):
            module_name = module_name[: -len(".__init__")]

        symbols: Set[str] = set()
        class_methods: Dict[str, Set[str]] = {}

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                symbols.add(node.name)
            elif isinstance(node, ast.ClassDef):
                symbols.add(node.name)
                # Extract methods of this class
                methods: Set[str] = set()
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        methods.add(item.name)
                class_methods[node.name] = methods

        if symbols:
            self.valid_symbols[module_name] = symbols
            self.class_methods[module_name] = class_methods
            self._total_files += 1
            self._total_symbols += len(symbols)

    def validate_code_block(self, llm_code: str) -> "ValidationResult":
        """
        Validate LLM-generated code against the Truth Map.

        Checks:
        1. from danny_toolkit.x.y import Z → does Z exist in module x.y?
        2. import danny_toolkit.x.y → does module x.y exist?
        3. danny_toolkit.x.y.func() attribute chains → does func exist?

        Returns:
            ValidationResult with is_valid flag and list of violations
        """
        violations: List[str] = []

        try:
            tree = ast.parse(llm_code)
        except SyntaxError as e:
            return ValidationResult(
                is_valid=False,
                violations=[f"SyntaxError in LLM code: {e}"]
            )

        # Check imports
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                self._check_import_from(node, violations)
            elif isinstance(node, ast.Import):
                self._check_import(node, violations)
            elif isinstance(node, ast.Attribute):
                self._check_attribute_chain(node, violations)

        is_valid = len(violations) == 0

        if not is_valid:
            for v in violations:
                print(f"  {Kleur.ROOD}[ANCHOR] FAKE:{Kleur.RESET} {v}")
            logger.warning("RealityAnchor rejected code: %d violations", len(violations))

        return ValidationResult(is_valid=is_valid, violations=violations)

    def _check_import_from(self, node: ast.ImportFrom, violations: List[str]):
        """Check: from danny_toolkit.x.y import Z"""
        module = node.module or ""
        if not module.startswith("danny_toolkit"):
            return

        # Check if the module itself exists
        if module not in self.valid_symbols:
            violations.append(f"Module does not exist: '{module}'")
            return

        # Check each imported name
        valid = self.valid_symbols[module]
        for alias in node.names:
            name = alias.name
            if name == "*":
                continue
            if name not in valid:
                violations.append(
                    f"'{name}' does not exist in '{module}' "
                    f"(valid: {', '.join(sorted(valid)[:10])}{'...' if len(valid) > 10 else ''})"
                )

    def _check_import(self, node: ast.Import, violations: List[str]):
        """Check: import danny_toolkit.x.y"""
        for alias in node.names:
            name = alias.name
            if not name.startswith("danny_toolkit"):
                continue
            # Check if any known module starts with this path
            if not any(m == name or m.startswith(name + ".") for m in self.valid_symbols):
                violations.append(f"Module does not exist: '{name}'")

    def _check_attribute_chain(self, node: ast.Attribute, violations: List[str]):
        """Check attribute access chains like danny_toolkit.core.engine.run_fast()."""
        chain = self._resolve_attribute_chain(node)
        if not chain or not chain.startswith("danny_toolkit."):
            return

        parts = chain.split(".")
        # Try to find the longest matching module prefix
        for i in range(len(parts), 1, -1):
            candidate_module = ".".join(parts[:i])
            if candidate_module in self.valid_symbols:
                # Remaining parts are symbol references
                remaining = parts[i:]
                if remaining:
                    symbol = remaining[0]
                    valid = self.valid_symbols[candidate_module]
                    if symbol not in valid:
                        violations.append(
                            f"'{symbol}' does not exist in '{candidate_module}'"
                        )
                    elif len(remaining) > 1:
                        # Check class.method (e.g., FaissIndex.nonexistent)
                        method = remaining[1]
                        class_methods = self.class_methods.get(candidate_module, {})
                        if symbol in class_methods and method not in class_methods[symbol]:
                            violations.append(
                                f"'{symbol}.{method}' does not exist in '{candidate_module}'"
                            )
                return

    def _resolve_attribute_chain(self, node: ast.Attribute) -> Optional[str]:
        """Recursively resolve a.b.c.d attribute chain to a dotted string."""
        parts = []
        current = node
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        if isinstance(current, ast.Name):
            parts.append(current.id)
            return ".".join(reversed(parts))
        return None

    def get_module_symbols(self, module: str) -> Optional[Set[str]]:
        """Look up valid symbols for a specific module."""
        return self.valid_symbols.get(module)

    def search_symbol(self, name: str) -> List[str]:
        """Find which modules contain a given symbol name."""
        results = []
        for module, symbols in self.valid_symbols.items():
            if name in symbols:
                results.append(module)
        return results

    def get_stats(self) -> Dict:
        """Return Truth Map statistics."""
        total_classes = sum(
            len(classes) for classes in self.class_methods.values()
        )
        total_methods = sum(
            sum(len(methods) for methods in classes.values())
            for classes in self.class_methods.values()
        )
        return {
            "modules": len(self.valid_symbols),
            "files_parsed": self._total_files,
            "total_symbols": self._total_symbols,
            "total_classes": total_classes,
            "total_methods": total_methods,
        }


class ValidationResult:
    """Result of a RealityAnchor validation check."""

    __slots__ = ("is_valid", "violations")

    def __init__(self, is_valid: bool, violations: List[str]):
        self.is_valid = is_valid
        self.violations = violations

    def __bool__(self):
        return self.is_valid

    def __repr__(self):
        if self.is_valid:
            return "ValidationResult(VALID)"
        return f"ValidationResult(INVALID, {len(self.violations)} violations)"
