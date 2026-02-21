"""
Energie vs. Tech Aandelen — Hypothetische Correlatie Plot
=========================================================

Visualiseert de relatie tussen stijgende energieprijzen
(gedreven door AI-datacenters) en tech-aandelenwaarde.

Data is hypothetisch maar gebaseerd op werkelijke trends:
- IEA: datacenters 415 TWh in 2024, 945 TWh in 2030
- AI energieverbruik overtreft Bitcoin mining sinds 2025
- Bitcoin prijs feb 2026: ~$69.000 (na selloff van $100K+)

Gebruik: python -m danny_toolkit.apps.energie_vs_tech
"""

import logging

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

logger = logging.getLogger(__name__)


def genereer_data():
    """Genereer hypothetische dataset 2020-2030."""
    jaren = np.arange(2020, 2031)

    # Energieprijs index (basis 2020 = 100)
    # Stijgt door datacenter-vraag + geopolitiek
    energieprijs = np.array([
        100, 108, 130, 125, 140,
        155, 170, 190, 215, 245, 280,
    ])

    # Tech aandelen index (basis 2020 = 100)
    # NASDAQ-achtige groei met AI-boom en correctie
    tech_aandelen = np.array([
        100, 127, 110, 135, 155,
        195, 230, 260, 285, 310, 340,
    ])

    # AI datacenter energieverbruik (TWh)
    # Bron: IEA projecties
    ai_energie_twh = np.array([
        25, 30, 38, 50, 65,
        85, 115, 155, 210, 280, 370,
    ])

    # Bitcoin mining energieverbruik (TWh)
    # Stabielere groei, ~120 TWh in 2024
    btc_energie_twh = np.array([
        70, 90, 100, 110, 120,
        125, 130, 135, 140, 145, 150,
    ])

    return {
        "jaren": jaren,
        "energieprijs": energieprijs,
        "tech_aandelen": tech_aandelen,
        "ai_energie": ai_energie_twh,
        "btc_energie": btc_energie_twh,
    }


def plot_correlatie(data, output_pad):
    """Plot 3-panel grafiek."""
    fig, axes = plt.subplots(3, 1, figsize=(12, 14))
    fig.suptitle(
        "AI Energiebehoefte vs. Tech Markt — "
        "Correlatie Analyse 2020-2030",
        fontsize=16, fontweight="bold", y=0.98,
    )

    jaren = data["jaren"]

    # === PANEL 1: Energieprijs vs Tech Aandelen ===
    ax1 = axes[0]
    kleur1 = "#e74c3c"
    kleur2 = "#2980b9"

    ln1 = ax1.plot(
        jaren, data["energieprijs"],
        color=kleur1, linewidth=2.5,
        marker="o", label="Energieprijs Index",
    )
    ax1.set_ylabel(
        "Energieprijs Index (2020=100)",
        color=kleur1, fontsize=11,
    )
    ax1.tick_params(axis="y", labelcolor=kleur1)

    ax2 = ax1.twinx()
    ln2 = ax2.plot(
        jaren, data["tech_aandelen"],
        color=kleur2, linewidth=2.5,
        marker="s", label="Tech Aandelen Index",
    )
    ax2.set_ylabel(
        "Tech Aandelen Index (2020=100)",
        color=kleur2, fontsize=11,
    )
    ax2.tick_params(axis="y", labelcolor=kleur2)

    lns = ln1 + ln2
    labs = [l.get_label() for l in lns]
    ax1.legend(lns, labs, loc="upper left")
    ax1.set_title(
        "Panel A: Energieprijs vs. Tech Aandelen",
        fontsize=13,
    )
    ax1.grid(True, alpha=0.3)

    # Correlatie berekenen
    corr = np.corrcoef(
        data["energieprijs"], data["tech_aandelen"]
    )[0, 1]
    ax1.text(
        0.98, 0.05,
        f"Pearson r = {corr:.3f}",
        transform=ax1.transAxes,
        ha="right", fontsize=11,
        bbox=dict(
            boxstyle="round,pad=0.3",
            facecolor="yellow", alpha=0.8,
        ),
    )

    # === PANEL 2: AI vs BTC Energieverbruik ===
    ax3 = axes[1]
    ax3.bar(
        jaren - 0.2, data["ai_energie"],
        width=0.4, color="#8e44ad",
        label="AI Datacenters (TWh)", alpha=0.85,
    )
    ax3.bar(
        jaren + 0.2, data["btc_energie"],
        width=0.4, color="#f39c12",
        label="Bitcoin Mining (TWh)", alpha=0.85,
    )
    ax3.set_ylabel("Energieverbruik (TWh)", fontsize=11)
    ax3.legend(loc="upper left")
    ax3.set_title(
        "Panel B: AI vs. Bitcoin Energieverbruik",
        fontsize=13,
    )
    ax3.grid(True, alpha=0.3, axis="y")

    # Kruispunt markeren
    verschil = data["ai_energie"] - data["btc_energie"]
    kruis_idx = np.where(np.diff(np.sign(verschil)))[0]
    if len(kruis_idx) > 0:
        kruis_jaar = jaren[kruis_idx[0]]
        ax3.axvline(
            x=kruis_jaar + 0.5, color="red",
            linestyle="--", linewidth=1.5,
        )
        ax3.text(
            kruis_jaar + 0.7,
            max(data["ai_energie"]) * 0.5,
            f"AI overtreft BTC\n(~{kruis_jaar + 1})",
            fontsize=10, color="red",
        )

    # === PANEL 3: Totaal Digitaal Energieverbruik ===
    ax4 = axes[2]
    totaal = data["ai_energie"] + data["btc_energie"]
    ax4.fill_between(
        jaren, 0, data["btc_energie"],
        color="#f39c12", alpha=0.6,
        label="Bitcoin Mining",
    )
    ax4.fill_between(
        jaren, data["btc_energie"], totaal,
        color="#8e44ad", alpha=0.6,
        label="AI Datacenters",
    )
    ax4.set_ylabel(
        "Totaal Verbruik (TWh)", fontsize=11,
    )
    ax4.set_xlabel("Jaar", fontsize=11)
    ax4.legend(loc="upper left")
    ax4.set_title(
        "Panel C: Gecombineerd Digitaal "
        "Energieverbruik",
        fontsize=13,
    )
    ax4.grid(True, alpha=0.3, axis="y")

    # Annotatie
    ax4.text(
        0.98, 0.05,
        "Bron: Hypothetisch model\n"
        "gebaseerd op IEA projecties",
        transform=ax4.transAxes,
        ha="right", fontsize=9,
        style="italic", alpha=0.7,
    )

    plt.tight_layout(rect=[0, 0, 1, 0.96])
    plt.savefig(output_pad, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  [OK] Grafiek opgeslagen: {output_pad}")
    return corr


def main():
    """Hoofdprogramma."""
    print()
    print("=" * 60)
    print("  ENERGIE vs. TECH — Correlatie Analyse")
    print("  AI Datacenters | Bitcoin Mining | Markt")
    print("=" * 60)
    print()

    # Genereer data
    data = genereer_data()
    print("  [OK] Hypothetische dataset gegenereerd"
          " (2020-2030)")

    # Output pad
    output_dir = (
        Path(__file__).parent.parent.parent
        / "data" / "plots"
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    output_pad = output_dir / "energie_vs_tech.png"

    # Plot
    corr = plot_correlatie(data, output_pad)

    # Statistieken
    e_groei = data["energieprijs"][-1] - data["energieprijs"][0]
    t_groei = data["tech_aandelen"][-1] - data["tech_aandelen"][0]
    ratio = data["ai_energie"][-1] / data["btc_energie"][-1]

    print()
    print("  --- Kerncijfers ---")
    print(f"  Pearson correlatie: {corr:.3f}")
    print(f"  Energieprijs groei 2020-2030: +{e_groei}%")
    print(f"  Tech aandelen groei 2020-2030: +{t_groei}%")
    print(f"  AI energie 2030: {data['ai_energie'][-1]} TWh")
    print(f"  BTC energie 2030: {data['btc_energie'][-1]} TWh")
    print(f"  Ratio AI/BTC 2030: {ratio:.1f}x")

    print()
    print("=" * 60)
    print("  ANALYSE VOLTOOID")
    print("=" * 60)


if __name__ == "__main__":
    main()
