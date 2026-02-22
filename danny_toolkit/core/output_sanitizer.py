"""
Output Sanitizer — Voorkomt AI feedback loops.

Filtert ANSI kleurcodes, box-drawing tekens, en decoratieve
formatting uit tekst voordat het naar een LLM wordt gestuurd.

Gebruik:
    from danny_toolkit.core.output_sanitizer import sanitize_for_llm
    clean = sanitize_for_llm(raw_stdout)
"""

import re

# ANSI escape codes (kleuren, cursor, formatting)
_ANSI_RE = re.compile(r'\x1b\[[0-9;]*[a-zA-Z]')

# Unicode box-drawing en decoratieve tekens
_BOX_CHARS = set(
    '╔╗╚╝═║─│├┤┬┴┼┌┐└┘╠╣╦╩╬'
    '━┃┏┓┗┛┣┫┳┻╋╭╮╯╰'
    '▀▁▂▃▄▅▆▇█▉▊▋▌▍▎▏'
    '░▒▓■□▢▣▤▥▦▧▨▩'
    '★☆●○◆◇◈◉◊'
    '►◄▲▼◀▶'
)

# Patronen die hallucinatie triggeren bij LLMs
_HALLUCINATION_TRIGGERS = re.compile(
    r'(?:QUEST\s+(?:XIII|X[IV]+)|'
    r'THE\s+WILL|'
    r'AUTONOMOUS\s+MODE|'
    r'SELF[\-_]EXECUTE|'
    r'ACTIVATE\s+PROTOCOL)',
    re.IGNORECASE,
)


def strip_ansi(text: str) -> str:
    """Verwijder ANSI escape sequences."""
    return _ANSI_RE.sub('', text)


def strip_box_drawing(text: str) -> str:
    """Verwijder box-drawing en decoratieve Unicode tekens."""
    return ''.join(c for c in text if c not in _BOX_CHARS)


def strip_hallucination_triggers(text: str) -> str:
    """Vervang bekende hallucinatie-triggers door neutrale tekst."""
    return _HALLUCINATION_TRIGGERS.sub('[FILTERED]', text)


def collapse_whitespace(text: str) -> str:
    """Normaliseer witruimte: meerdere lege regels → enkele."""
    # Meerdere opeenvolgende lege regels → max 1
    text = re.sub(r'\n{3,}', '\n\n', text)
    # Regels met alleen spaties/tabs → lege regels
    text = re.sub(r'^[ \t]+$', '', text, flags=re.MULTILINE)
    return text.strip()


def sanitize_for_llm(text: str, max_chars: int = 5000) -> str:
    """
    Volledige sanitisatie van subprocess output voor LLM consumptie.

    Verwijdert:
    - ANSI kleurcodes
    - Box-drawing tekens (╔═╗ etc.)
    - Decoratieve Unicode symbolen
    - Bekende hallucinatie-triggers
    - Overmatige witruimte

    Trunceert naar max_chars (standaard 5000).
    """
    if not text:
        return ""

    text = strip_ansi(text)
    text = strip_box_drawing(text)
    text = strip_hallucination_triggers(text)
    text = collapse_whitespace(text)

    # Trunceer (behoud einde — meest recente output is relevantst)
    if len(text) > max_chars:
        text = text[-max_chars:]

    return text


def is_mostly_decorative(text: str, threshold: float = 0.3) -> bool:
    """
    Check of tekst voornamelijk decoratief is (>30% box/symbol chars).

    Nuttig als gate vóór LLM injection — decoratieve output
    bevat geen semantische waarde maar triggert hallucinaties.
    """
    if not text:
        return False
    decorative = sum(1 for c in text if c in _BOX_CHARS)
    total = len(text)
    return (decorative / total) > threshold if total > 0 else False
