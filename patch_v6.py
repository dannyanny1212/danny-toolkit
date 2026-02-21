import os
import sys
import io

# Windows UTF-8 fix (project conventie)
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from danny_toolkit.core.utils import Kleur


def patch_system():
    root_dir = os.path.dirname(os.path.abspath(__file__))

    print(f"{Kleur.CYAAN}======================================")
    print(f" OMEGA v6.0 AUTO-PATCHER")
    print(f"======================================{Kleur.RESET}\n")

    # Alle bestanden met v5.1.1 / COSMIC_OMEGA_V5 referenties
    targets = [
        # Root bestanden
        "cli.py",
        "sanctuary_ui.py",
        "main.py",
        "OMEGA_PROTOCOL.py",
        # danny_toolkit/
        "danny_toolkit/launcher.py",
        "danny_toolkit/gui_launcher.py",
        # Agents
        "danny_toolkit/agents/base.py",
        "danny_toolkit/agents/orchestrator.py",
        "danny_toolkit/agents/tool.py",
        # Brain
        "danny_toolkit/brain/trinity_omega.py",
        "danny_toolkit/brain/morning_protocol.py",
        # Core
        "danny_toolkit/core/config.py",
        # Apps
        "danny_toolkit/apps/virtueel_huisdier.py",
    ]

    # Gerichte vervangingen (veilig, geen blanket replace)
    replacements = [
        ("v5.1.1", "v6.0.0"),
        ("COSMIC_OMEGA_V5", "OMEGA_SOVEREIGN"),
        ("Versie 5.1.1 - COSMIC_OMEGA_V5", "Versie 6.0.0 - OMEGA_SOVEREIGN"),
        ("Versie 5.0.0 - COSMIC_OMEGA_V5", "Versie 6.0.0 - OMEGA_SOVEREIGN"),
    ]

    patched_files = 0
    total_replacements = 0

    for rel_path in targets:
        filepath = os.path.join(root_dir, rel_path)
        if not os.path.exists(filepath):
            print(f"  {Kleur.GEEL}-- {rel_path}: niet gevonden (overgeslagen){Kleur.RESET}")
            continue

        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        original = content
        file_changes = 0

        for old, new in replacements:
            count = content.count(old)
            if count > 0:
                content = content.replace(old, new)
                file_changes += count

        if file_changes > 0:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"  {Kleur.GROEN}+ {rel_path}: {file_changes} vervangingen{Kleur.RESET}")
            patched_files += 1
            total_replacements += file_changes
        else:
            print(f"  {Kleur.MAGENTA}  {rel_path}: al up-to-date{Kleur.RESET}")

    # Samenvatting
    print(f"\n{Kleur.CYAAN}--------------------------------------{Kleur.RESET}")
    print(f"  Bestanden gepatcht: {patched_files}")
    print(f"  Totaal vervangingen: {total_replacements}")
    print(f"{Kleur.CYAAN}--------------------------------------{Kleur.RESET}")

    if patched_files > 0:
        print(f"\n{Kleur.GROEN}Patch succesvol! Herstart met: python omega_ignition.py{Kleur.RESET}")
    else:
        print(f"\n{Kleur.MAGENTA}Alles was al v6.0.0 — geen wijzigingen nodig.{Kleur.RESET}")

    # Autonomie uitleg
    print(f"\n{Kleur.GEEL}HOE DE AUTONOMIE WERKT IN v6.0:{Kleur.RESET}")
    print("  In het COMMAND >: menu heb je twee opties:")
    print("  1. Typ een GETAL (bijv. '41') -> Opent de specifieke app.")
    print("  2. Open App 41 (Omega AI) -> Volledig autonoom via Strategist.")
    print("  Typ in [content] >: 'Analyseer mijn code' en de AI doet de rest.")


if __name__ == "__main__":
    patch_system()
