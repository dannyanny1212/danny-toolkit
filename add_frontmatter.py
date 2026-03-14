"""Smart Frontmatter Injector — Upgrade .md bestanden naar S-Tier RAG geheugen.

Scant alle .md bestanden in data/rag/documenten/ en voegt YAML frontmatter
toe op basis van bestandsnaam, eerste header en inhoud-analyse.

Alleen bestanden ZONDER bestaande frontmatter worden geüpgraded.
Bestaande inhoud wordt NOOIT gewijzigd — frontmatter wordt vooraan toegevoegd.

Gebruik:
    python add_frontmatter.py              # dry-run (toont wat er zou veranderen)
    python add_frontmatter.py --apply      # voer de wijzigingen uit
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

DOCS_DIR = Path("data/rag/documenten")

# Categorie-detectie op basis van bestandsnaam prefix
CATEGORY_MAP = {
    "fastapi_": "fastapi_docs",
    "pydantic_": "pydantic_docs",
    "python_": "python_docs",
    "sqlalchemy_": "sqlalchemy_docs",
    "omega_": "omega_architecture",
    "daily_lesson": "lessons",
    "deep_dive": "analysis",
    "diamond_polish": "quality_standards",
    "MYTHICAL": "design",
}

# Tag-detectie op basis van inhoud keywords
TAG_KEYWORDS = {
    "fastapi": "fastapi",
    "pydantic": "pydantic",
    "asyncio": "async",
    "websocket": "websocket",
    "docker": "docker",
    "security": "security",
    "oauth": "auth",
    "database": "database",
    "sqlalchemy": "sqlalchemy",
    "swarm": "swarm",
    "ouroboros": "ouroboros",
    "agent": "agents",
    "governor": "safety",
    "cortical": "memory",
    "chromadb": "rag",
    "embedding": "embeddings",
    "tribunal": "verification",
    "sovereign": "sovereign",
    "synapse": "routing",
    "middleware": "middleware",
    "testing": "testing",
    "deployment": "deployment",
    "graphql": "graphql",
    "typing": "typing",
    "validator": "validation",
}


def detect_category(filename: str) -> str:
    """Detecteer categorie op basis van bestandsnaam prefix."""
    for prefix, category in CATEGORY_MAP.items():
        if filename.startswith(prefix):
            return category
    return "knowledge"


def detect_tags(content: str, filename: str) -> list[str]:
    """Detecteer tags op basis van inhoud en bestandsnaam."""
    content_lower = content.lower()
    tags = set()
    for keyword, tag in TAG_KEYWORDS.items():
        if keyword in content_lower:
            tags.add(tag)
    # Voeg categorie-gerelateerde tag toe
    for prefix in CATEGORY_MAP:
        if filename.startswith(prefix):
            tags.add(prefix.rstrip("_"))
            break
    return sorted(tags)[:8]  # Max 8 tags


def extract_title(content: str, filename: str) -> str:
    """Extraheer titel uit eerste H1 header of genereer uit bestandsnaam."""
    match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
    if match:
        return match.group(1).strip()
    # Genereer uit bestandsnaam
    name = filename.replace(".md", "").replace("_", " ").title()
    return name


def count_words(content: str) -> int:
    """Tel woorden in content (exclusief code blocks)."""
    # Strip code blocks
    cleaned = re.sub(r"```.*?```", "", content, flags=re.DOTALL)
    return len(cleaned.split())


def generate_frontmatter(filepath: Path) -> str:
    """Genereer YAML frontmatter voor een .md bestand."""
    content = filepath.read_text(encoding="utf-8")
    filename = filepath.name

    title = extract_title(content, filename)
    category = detect_category(filename)
    tags = detect_tags(content, filename)
    words = count_words(content)

    # Weight class op basis van grootte
    if words > 5000:
        weight = "heavy"
    elif words > 1500:
        weight = "medium"
    else:
        weight = "light"

    tags_str = ", ".join(f'"{t}"' for t in tags)

    frontmatter = f'''---
title: "{title}"
category: "{category}"
tags: [{tags_str}]
weight_class: "{weight}"
word_count: {words}
---

'''
    return frontmatter


def main() -> None:
    """Scan en upgrade .md bestanden."""
    apply = "--apply" in sys.argv

    if not DOCS_DIR.exists():
        print(f"Map niet gevonden: {DOCS_DIR}")
        sys.exit(1)

    md_files = sorted(DOCS_DIR.glob("*.md"))
    print(f"Gevonden: {len(md_files)} .md bestanden in {DOCS_DIR}")

    upgraded = 0
    skipped = 0

    for filepath in md_files:
        content = filepath.read_text(encoding="utf-8")

        # Skip als frontmatter al bestaat
        if content.startswith("---"):
            skipped += 1
            continue

        frontmatter = generate_frontmatter(filepath)

        if apply:
            filepath.write_text(frontmatter + content, encoding="utf-8")
            print(f"  [OK] {filepath.name}")
        else:
            # Dry-run: toon wat er zou veranderen
            lines = frontmatter.strip().split("\n")
            print(f"  [DRY] {filepath.name} -> {lines[1]}, {lines[3]}")

        upgraded += 1

    print(f"\n{'APPLIED' if apply else 'DRY-RUN'}: {upgraded} geüpgraded, {skipped} overgeslagen")
    if not apply and upgraded > 0:
        print("Draai met --apply om de wijzigingen door te voeren.")


if __name__ == "__main__":
    main()
