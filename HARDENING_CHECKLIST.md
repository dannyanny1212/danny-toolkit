# Danny Toolkit v6.7.0 — Hardening Checklist

> Omega Sovereign Core | Security Protocol
>
> **Brain CLI verificatie**: `python -m danny_toolkit.brain.brain_cli` → `a` (Architectuur Scan)

---

## 1. Sovereign Gate — 7 IJzeren Wetten

| # | Wet | Verificatie |
|---|-----|-------------|
| 1 | **Root Integrity** | Pad = `C:\Users\danny\danny-toolkit` |
| 2 | **Authority Check** | Administrator privileges |
| 3 | **Terminal Lock** | Native PowerShell (geen verborgen cmd.exe) |
| 4 | **Physical Console** | Geen RDP of verborgen sessies |
| 5 | **Identity Binding** | Git email whitelist verificatie |
| 6 | **Hardware Fingerprint** | CPU ID + MAC-adres = Sovereign Master Hash |
| 7 | **Iron Dome Network** | Default-Deny uitgaand verkeer, alleen whitelist |

**Gate is ONAANRAAKBAAR**: geen test modus, geen bypass.

---

## 2. RAG Gate Protocol (Pre-Execution Validatie)

| Tier | Check | Blokkade? |
|------|-------|-----------|
| 1 | PII scan (email, IBAN, IPv4, API keys, SHA256, telefoon) | Waarschuwing |
| 1 | Secrets detectie (.env, credentials, .pem, .key) | BLOKKADE |
| 1 | Destructieve patronen (delete, drop, rm -rf, force push) | Waarschuwing |
| 1 | Path validatie (buiten project root) | BLOKKADE |
| 2 | RAG context match in security docs | Informatief |
| 3 | OmegaGovernor input validatie | BLOKKADE bij injectie |

**Implementatie**: `patchday.py` bevat de volledige RAG Gate als 3-tier pre-execution validatie. Standalone toegankelijk via `python patchday.py gate "actie"`.

---

## 3. Repository Security

- [ ] Geen secrets in git history (.env, API keys, tokens)
- [ ] `.gitignore` bevat: .env, *.pem, *.key, credentials*, data/
- [ ] Pre-commit hooks actief voor secret scanning
- [ ] Golden tag `v5.0.0` beschermd tegen overschrijving

---

## 4. Runtime Security

- [ ] OmegaGovernor actief (rate-limits, injection detectie, PII scrubbing)
- [ ] HallucinatieSchild in swarm pipeline (stap 7.5)
- [ ] Per-provider circuit breakers (Groq, Anthropic, NIM, Ollama)
- [ ] AgentKeyManager: 10-key isolatie, geen key sharing
- [ ] ShadowGovernance: 3-zone clone restricties (ROOD/GEEL/GROEN)

---

## 5. Data Security

- [ ] CorticalStack: WAL mode, busy_timeout=5000
- [ ] ChromaDB: 3 shards gescheiden (code/docs/data)
- [ ] ShadowAirlock: copy-verify-delete promotie (SHA256 check)
- [ ] FileGuard: source integrity via manifest + SHA256
- [ ] Embedding cache: dim-aware keys voorkomen stale data

---

## 6. Backup & Recovery

- [ ] CorticalStack backup via Dreamer REM cycle (04:00)
- [ ] AutoSaver: 30-minuten backup daemon
- [ ] Golden snapshot bewaard bij elke release
- [ ] Rollback via `patchday.py rollback <versie>`

---

## 7. Test Isolatie

- [ ] `CUDA_VISIBLE_DEVICES=-1` (voorkomt GPU segfaults)
- [ ] `DANNY_TEST_MODE=1` (skip ChromaDB PersistentClient)
- [ ] `ANONYMIZED_TELEMETRY=False`
- [ ] Sovereign Gate NOOIT bypassed in tests
