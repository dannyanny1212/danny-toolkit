"""
Forge Loader — Dynamic Tool Hot-Reloading (Phase 56)
=====================================================
Scant danny_toolkit/sandbox/forge/ op .py bestanden, laadt functies
dynamisch via importlib, en genereert OpenAI-compatible tool schemas
uit docstrings en type hints.

Veiligheidsmaatregelen:
- Syntax check via compile() vóór import
- Blocklist voor schadelijke imports (os.system, subprocess, eval, exec)
- Elke tool draait in try/except — crash isoleert, server :8001 blijft live
- Module reload bij file change (mtime tracking)

Gebruik:
    from danny_toolkit.core.forge_loader import scan_and_load_tools, execute_forged_tool
    tools, schemas = scan_and_load_tools()
    result = execute_forged_tool("tool_name", {"param": "value"})
"""

from __future__ import annotations

import ast
import importlib
import importlib.util
import inspect
import logging
import re
import time
import typing
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ── Forge directory ──────────────────────────────────────────────
_FORGE_DIR = Path(__file__).parent.parent / "sandbox" / "forge"

# ── Security: blocked patterns in source code ────────────────────
_BLOCKED_PATTERNS = [
    r"\bos\.system\b",
    r"\bsubprocess\b",
    r"\b__import__\b",
    r"\beval\s*\(",
    r"\bexec\s*\(",
    r"\bcompile\s*\(",
    r"\bopen\s*\(.*(\/etc|C:\\Windows|\.env)",
    r"\bshutil\.rmtree\b",
    r"\bglobals\s*\(\s*\)",
    r"\bsetattr\s*\(",
]
_BLOCKED_RE = re.compile("|".join(_BLOCKED_PATTERNS), re.IGNORECASE)

# ── Registry: loaded tools + mtime cache ─────────────────────────
_tool_registry: Dict[str, Dict[str, Any]] = {}
_file_mtimes: Dict[str, float] = {}


def _is_safe(source: str, filepath: Path) -> bool:
    """Validate source code safety: syntax + blocklist check."""
    # 1. Syntax check
    try:
        compile(source, str(filepath), "exec")
    except SyntaxError as e:
        logger.warning("Forge: syntax error in %s: %s", filepath.name, e)
        return False

    # 2. Blocked pattern scan
    match = _BLOCKED_RE.search(source)
    if match:
        logger.warning(
            "Forge: blocked pattern '%s' in %s — skipped",
            match.group(), filepath.name,
        )
        return False

    return True


def _python_type_to_json(annotation: Any) -> str:
    """Convert Python type annotation to JSON schema type string."""
    if annotation is inspect.Parameter.empty:
        return "string"

    origin = getattr(annotation, "__origin__", None)
    if origin is list or origin is typing.List:
        return "array"

    type_map = {
        str: "string",
        int: "integer",
        float: "number",
        bool: "boolean",
        list: "array",
        dict: "object",
    }

    if isinstance(annotation, type):
        return type_map.get(annotation, "string")

    # String annotation fallback
    ann_str = str(annotation).lower()
    for py_type, json_type in [
        ("str", "string"), ("int", "integer"), ("float", "number"),
        ("bool", "boolean"), ("list", "array"), ("dict", "object"),
    ]:
        if py_type in ann_str:
            return json_type

    return "string"


def _func_to_schema(func: Callable, module_name: str) -> Dict:
    """Generate OpenAI-compatible tool schema from function signature.

    Uses inspect to extract parameters, type hints, and docstring.
    """
    sig = inspect.signature(func)
    doc = inspect.getdoc(func) or f"Forged tool: {func.__name__}"

    # Parse parameters
    properties = {}
    required = []
    for name, param in sig.parameters.items():
        if name in ("self", "cls"):
            continue

        prop: Dict[str, Any] = {
            "type": _python_type_to_json(param.annotation),
        }

        # Extract param description from docstring (Args: section)
        param_doc = _extract_param_doc(doc, name)
        if param_doc:
            prop["description"] = param_doc

        properties[name] = prop

        if param.default is inspect.Parameter.empty:
            required.append(name)

    tool_name = f"forge_{module_name}_{func.__name__}"

    return {
        "type": "function",
        "function": {
            "name": tool_name,
            "description": doc.split("\n")[0],  # First line only
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        },
    }


def _extract_param_doc(docstring: str, param_name: str) -> Optional[str]:
    """Extract parameter description from docstring Args section."""
    if not docstring:
        return None
    pattern = rf"^\s*{re.escape(param_name)}\s*[:(].*?[):]?\s*(.+)"
    for line in docstring.split("\n"):
        match = re.match(pattern, line.strip())
        if match:
            return match.group(1).strip()
    return None


def _load_module(filepath: Path) -> Optional[object]:
    """Dynamically load a Python module from filepath."""
    module_name = f"forge_{filepath.stem}"
    spec = importlib.util.spec_from_file_location(module_name, str(filepath))
    if spec is None or spec.loader is None:
        return None

    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
        return module
    except Exception as e:
        logger.warning("Forge: failed to load %s: %s", filepath.name, e)
        return None


def scan_and_load_tools() -> Tuple[Dict[str, Callable], List[Dict]]:
    """Scan forge/ directory for .py files and load tools dynamically.

    Returns:
        Tuple of:
        - Dict[tool_name -> callable function]
        - List of OpenAI-compatible tool schemas

    Thread-safe: only reloads modules whose mtime changed.
    Skips __init__.py, files with syntax errors, and unsafe code.
    """
    global _tool_registry, _file_mtimes

    if not _FORGE_DIR.exists():
        return {}, []

    py_files = [
        f for f in _FORGE_DIR.glob("*.py")
        if f.name != "__init__.py" and f.is_file()
    ]

    if not py_files:
        return (
            {k: v["func"] for k, v in _tool_registry.items()},
            [v["schema"] for v in _tool_registry.values()],
        )

    changed = False
    for filepath in py_files:
        mtime = filepath.stat().st_mtime
        cached_mtime = _file_mtimes.get(str(filepath))

        if cached_mtime is not None and mtime == cached_mtime:
            continue  # No change

        # Read and validate source
        try:
            source = filepath.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            logger.warning("Forge: can't read %s: %s", filepath.name, e)
            continue

        if not _is_safe(source, filepath):
            continue

        # Load module
        module = _load_module(filepath)
        if module is None:
            continue

        # Extract public functions (not starting with _)
        module_name = filepath.stem
        for name, func in inspect.getmembers(module, inspect.isfunction):
            if name.startswith("_"):
                continue
            if func.__module__ != f"forge_{module_name}":
                continue  # Skip imported functions

            tool_name = f"forge_{module_name}_{name}"
            schema = _func_to_schema(func, module_name)

            _tool_registry[tool_name] = {
                "func": func,
                "schema": schema,
                "source": str(filepath),
                "loaded_at": time.time(),
            }
            logger.info("Forge: loaded tool %s from %s", tool_name, filepath.name)

        _file_mtimes[str(filepath)] = mtime
        changed = True

    # Clean up tools from deleted files
    existing_sources = {str(f) for f in py_files}
    stale_keys = [
        k for k, v in _tool_registry.items()
        if v["source"] not in existing_sources
    ]
    for k in stale_keys:
        del _tool_registry[k]
        changed = True

    tools = {k: v["func"] for k, v in _tool_registry.items()}
    schemas = [v["schema"] for v in _tool_registry.values()]

    if changed:
        logger.info("Forge: %d tools loaded from %d files", len(tools), len(py_files))

    return tools, schemas


def execute_forged_tool(tool_name: str, arguments: Dict[str, Any]) -> Any:
    """Execute a dynamically loaded forge tool by name.

    S-Tier error handling: any failure returns an error dict,
    never crashes the caller or server :8001.

    Args:
        tool_name: Full tool name (e.g. 'forge_calculator_add').
        arguments: Dict of function arguments.

    Returns:
        Tool result or error dict on failure.
    """
    entry = _tool_registry.get(tool_name)
    if entry is None:
        return {
            "error": f"Forged tool '{tool_name}' niet gevonden",
            "available": list(_tool_registry.keys()),
        }

    func = entry["func"]
    try:
        result = func(**arguments)
        return {"result": result, "tool": tool_name, "status": "success"}
    except TypeError as e:
        return {
            "error": f"Argument mismatch: {e}",
            "tool": tool_name,
            "expected": list(inspect.signature(func).parameters.keys()),
        }
    except Exception as e:
        logger.error("Forge tool %s crashed: %s", tool_name, e, exc_info=True)
        return {
            "error": f"Tool execution failed: {type(e).__name__}: {e}",
            "tool": tool_name,
            "status": "error",
        }


def get_forge_status() -> Dict[str, Any]:
    """Return forge loader status for dashboard/API."""
    return {
        "forge_dir": str(_FORGE_DIR),
        "tools_loaded": len(_tool_registry),
        "tools": {
            name: {
                "source": info["source"],
                "loaded_at": info["loaded_at"],
            }
            for name, info in _tool_registry.items()
        },
        "files_tracked": len(_file_mtimes),
    }
