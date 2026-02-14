# BRANCH_STRATEGY.md

**Danny Toolkit – Branching Strategy**

Deze strategie zorgt voor stabiliteit, voorspelbaarheid en veilige upgrades.

---

# 1. Branch-types

## 1.1. `main`
- Altijd stabiel
- Nooit direct op werken
- Bevat alleen geteste releases
- Golden snapshot (v5.0.0) blijft onaangeroerd

## 1.2. Feature branches
Naamgeving:
- `feature/<naam>`
Voorbeeld:
- `feature/context-analysis`

Gebruik:
- Nieuwe functies
- Nieuwe subsystemen
- Uitbreidingen

## 1.3. Fix branches
Naamgeving:
- `fix/<naam>`
Voorbeeld:
- `fix/telegram-timeout`

Gebruik:
- Bugfixes
- Kleine correcties

## 1.4. Upgrade branches
Naamgeving:
- `upgrade/vX.Y.Z`
Voorbeeld:
- `upgrade/v5.1.0`

Gebruik:
- Versie-upgrades
- Grote refactors
- Architectuurwijzigingen

---

# 2. Workflow

1. Maak nieuwe branch
2. Voeg code toe
3. Commit regelmatig
4. Laat Claude documentatie bijwerken
5. Commit documentatie
6. Merge naar `main`
7. Tag release

---

# 3. Regels

- Nooit direct op `main` werken
- Nooit golden snapshot wijzigen
- Elke wijziging krijgt een eigen branch
- Branches blijven klein en doelgericht
