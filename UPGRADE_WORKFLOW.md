# UPGRADE_WORKFLOW.md

# Danny Toolkit – Volledige Upgrade-Workflow

Deze workflow zorgt ervoor dat elke upgrade:

- veilig is
- omkeerbaar blijft
- documentatie automatisch synchroon blijft
- je golden snapshot (v5.0.0) nooit breekt
- professioneel en consistent verloopt

---

## 1. Voorbereiding

### 1.1. Werk nooit rechtstreeks op main of op v5.0.0
De golden snapshot blijft altijd onaangeroerd.

### 1.2. Maak een nieuwe branch voor elke wijziging
Gebruik duidelijke namen:

- `feature/<naam>`
- `fix/<naam>`
- `upgrade/v5.1.0`

Voorbeeld:

```bash
git checkout -b feature/context-analysis
```

---

## 2. Code-ontwikkeling

### 2.1. Bouw in kleine, veilige stappen
- kleine commits
- duidelijke commit-messages
- geen grote sprongen in één keer

Voorbeeld:

```bash
git add .
git commit -m "Added analyze_context() to SwarmEngine"
```

### 2.2. Test lokaal
- CLI
- FastAPI
- Sanctuary UI
- Telegram bot

Alles blijft lokaal draaien.

---

## 3. Documentatie automatisch bijwerken

### 3.1. Open Claude Code en gebruik de update-prompt
Gebruik deze prompt:

```
Voer een documentatie-update uit op basis van de laatste commit.

Taken:
1. Analyseer de codewijzigingen in de meest recente commit.
2. Update alle relevante documentatiebestanden zodat ze overeenkomen met de huidige codebase.
3. Synchroniseer subsystemen, pipelines, agents en interne documenten.
4. Genereer een changelog voor deze update (semver: patch/minor/major).
5. Rapporteer welke documenten zijn aangepast en waarom.

Belangrijk:
- Wijzig GEEN code.
- Pas alleen documentatie aan.
- Respecteer de bestaande structuur van de repo.
- Houd de golden snapshot (v5.0.0) intact.
```

### 3.2. Commit de documentatie

```bash
git add .
git commit -m "Docs updated for analyze_context()"
```

---

## 4. Versiebeheer (semver)

### PATCH (v5.0.1, v5.0.2)
Gebruik bij:
- kleine fixes
- documentatiecorrecties
- bugfixes
- geen nieuwe features

### MINOR (v5.1.0, v5.2.0)
Gebruik bij:
- nieuwe features
- uitbreidingen
- backwards-compatible wijzigingen

### MAJOR (v6.0.0, v7.0.0)
Gebruik bij:
- grote architectuurwijzigingen
- breaking changes
- herstructurering

---

## 5. Merge naar main

Wanneer:
- code werkt
- documentatie volledig is
- changelog aanwezig is
- branch getest is

```bash
git checkout main
git merge feature/context-analysis
```

---

## 6. Tag de nieuwe versie

```bash
git tag v5.1.0
git push --tags
```

---

## 7. Golden snapshot blijft onaangeroerd

Je raakt v5.0.0 nooit aan.

Waarom:
- het is je perfecte referentiepunt
- je kan altijd terug
- upgrades blijven veilig
- je systeem blijft stabiel

---

## 8. Terugrollen (rollback)

Altijd mogelijk:

```bash
git checkout main
git reset --hard v5.0.0
```

Of:

```bash
git checkout <commit-hash>
```

Niets is permanent.
Alles blijft omkeerbaar.

---

## 9. Release-flow

1. Nieuwe branch
2. Code toevoegen
3. Committen
4. Claude update docs
5. Commit docs
6. Merge naar main
7. Tag nieuwe versie
8. Push

---

## 10. Veiligheidsregels blijven gelden

- geen code in golden snapshot
- geen secrets in repo
- alles lokaal draaien
- geen port-forwarding
- geen onbekende scripts
- .env blijft lokaal
- .gitignore blijft correct
