# HARDENING_CHECKLIST.md

# Danny Toolkit v5 – Hardening Checklist

Beveiligingschecklist voor de repository, runtime en systeem.

---

## 1. GitHub & repo-toegang

- [ ] Repo privé houden
- [ ] 2FA op GitHub
- [ ] Geen collaborators tenzij bewust
- [ ] Nooit .env of API-keys committen
- [ ] data/, logs/, __pycache__/ in .gitignore

## 2. Gevoelige data

- [ ] .env blijft lokaal
- [ ] Geen echte persoonsgegevens in MEMEX
- [ ] Geen gevoelige screenshots of logs in de repo

## 3. Runtime-veiligheid

- [ ] Alles lokaal draaien
- [ ] Geen port-forwarding, geen ngrok, geen publieke endpoints
- [ ] Windows-firewall aan
- [ ] Telegram bot-token nooit delen

## 4. Code-veiligheid

- [ ] Nieuwe features op een nieuwe branch
- [ ] Kleine commits
- [ ] Golden snapshot (v5.0.0) nooit wijzigen
- [ ] Dependencies up-to-date

## 5. Backups & snapshots

- [ ] Offline kopie van de projectmap
- [ ] Golden state nooit wijzigen
- [ ] Nieuwe versies altijd vanuit een nieuwe branch

## 6. Systeem-hardening

- [ ] Geen onbekende scripts uitvoeren
- [ ] Geen externe code zonder review
- [ ] Geen automatische deployment pipelines
- [ ] Geen remote execution agents
