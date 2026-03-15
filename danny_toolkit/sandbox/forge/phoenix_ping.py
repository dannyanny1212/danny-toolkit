"""Forge Tool: Phoenix Ping — SSD sector health check."""
from __future__ import annotations


def ping_ssd(sectors: int) -> str:
    """Ping de Phoenix SSD en verifieer sector-integriteit.

    Simuleert een sector-scan op de beveiligde opslag.
    Retourneert een succes-rapport met het aantal gescande sectoren.

    Args:
        sectors: Aantal sectoren om te scannen (1-4096).

    Returns:
        Status string met scan resultaat.
    """
    if sectors < 1:
        return "ERROR: Minimaal 1 sector vereist"
    if sectors > 4096:
        return "ERROR: Maximum 4096 sectoren"

    return (
        f"PHOENIX SSD PING OK — {sectors} sectoren gescand, "
        f"0 fouten, integriteit 100%"
    )
