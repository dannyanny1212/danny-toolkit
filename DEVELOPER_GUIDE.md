# DEVELOPER_GUIDE.md

**Danny Toolkit – Developer Guide**

Deze gids helpt ontwikkelaars (jij of toekomstige AI-agents) om consistent en veilig aan de toolkit te werken.

---

# 1. Basisprincipes

- Alles gebeurt lokaal
- Geen secrets in de repo
- Golden snapshot blijft onaangeroerd
- Elke wijziging krijgt een eigen branch
- Documentatie blijft synchroon met code

---

# 2. Workflow voor nieuwe functies

1. Maak een nieuwe branch
2. Voeg code toe in kleine stappen
3. Commit regelmatig
4. Test lokaal (CLI, FastAPI, UI, Telegram)
5. Laat Claude documentatie bijwerken
6. Commit documentatie
7. Merge naar `main`
8. Tag release

---

# 3. Documentatie-regels

- Elke functie moet in de juiste .md terechtkomen
- Gebruik de automatische update-prompt
- Houd subsystemen consistent
- Update changelog bij elke release

---

# 4. Veiligheidsregels

- `.env` blijft lokaal
- Geen port-forwarding
- Geen onbekende scripts
- Geen remote execution agents
- `.gitignore` blijft correct

---

# 5. Versiebeheer

Gebruik semver:

| Type   | Voorbeeld | Gebruik wanneer…      |
|--------|-----------|-----------------------|
| PATCH  | v5.0.1    | kleine fixes          |
| MINOR  | v5.1.0    | nieuwe features       |
| MAJOR  | v6.0.0    | breaking changes      |

---

# 6. Rollback

Altijd mogelijk:

```bash
git checkout main
git reset --hard v5.0.0
```
