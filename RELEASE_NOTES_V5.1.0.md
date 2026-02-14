# Danny Toolkit v5.1.0 – Release Notes
Datum: 2026-02-14

## Overzicht
Deze minor-release introduceert een nieuwe utility-functie en brengt de documentatie volledig in lijn met de huidige codebase.
De release is backwards-compatible en bevat geen breaking changes.

---

## Nieuwe features
### ensure_directory utility
- Nieuwe functie `ensure_directory(path: str)` toegevoegd in `danny_toolkit/utils/ensure_directory.py`.
- Maakt automatisch directories aan indien ze nog niet bestaan.
- Handig voor pipelines, agents en RAG-workflows.

---

## Documentatie-updates
- MASTER_INDEX.md uitgebreid met nieuwe subsystem-verwijzingen.
- DEVELOPER_GUIDE.md bijgewerkt voor v5.1.0.
- CHANGELOG.md aangevuld met de nieuwe release-entry.
- Interne documentatie gesynchroniseerd via Claude Code.

---

## Upgrade-instructies
1. Pull de laatste wijzigingen van `master`.
2. Geen verdere acties vereist — deze release bevat geen breaking changes.

---

## Compatibiliteit
- Backwards-compatible: **Ja**
- Breaking changes: **Nee**
