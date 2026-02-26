# Danny Toolkit v6.7.0 — Developer Guide

> Omega Sovereign Core | Diamond Polish Protocol
>
> **Centraal aansturingspunt**: `python -m danny_toolkit.brain.brain_cli`

---

## 1. De Onbreekbare Wetten (Diamond Polish)

### Wet 1: Absolute Imports (Zero Tolerance)
Elke import MOET absoluut zijn vanaf de root:
```python
# GOED
from danny_toolkit.core.config import Config
from danny_toolkit.brain.governor import OmegaGovernor

# FOUT — nooit relative imports
from ..core import Config
from .governor import OmegaGovernor
```

### Wet 2: God Mode Error Handling
Elke error wordt gelogd naar CorticalStack. Geen bare `except: pass`.
```python
# GOED
except Exception as e:
    logger.debug("Context: %s", e)

# FOUT
except:
    pass
```

### Wet 3: Windows UTF-8
Elk nieuw entry point herconfigureert stdout:
```python
import io, os, sys
if os.name == "nt":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
```

---

## 2. Development Workflow

### Branch Strategie
- `fix/` — bugfixes
- `feature/` — nieuwe functionaliteit
- `upgrade/` — systeem upgrades
- `release/` — release branches

### Test Omgeving
Verplichte environment variabelen:
```bash
CUDA_VISIBLE_DEVICES=-1      # Geen GPU (voorkomt segfaults)
DANNY_TEST_MODE=1             # Skip ChromaDB PersistentClient
ANONYMIZED_TELEMETRY=False    # Geen telemetrie
```

### Python Executable
Altijd venv311 gebruiken:
```bash
C:/Users/danny/danny-toolkit/venv311/Scripts/python.exe
```
Nooit bare `python`.

---

## 3. Code Kwaliteit

- Geen placeholders (`pass`, `TODO`) — schrijf complete code
- Inputs ALTIJD sanitizen (voorkom prompt injection, path traversal)
- Type hints en docstrings voor statische analyse
- `try/except ImportError` fallbacks (project conventie)
- Singleton factories: double-checked locking met `threading.Lock`

---

## 4. Brain CLI Verificatie

Na elke wijziging: draai Brain CLI Architectuur Scan:
```bash
python -m danny_toolkit.brain.brain_cli
# Kies 'a' (Architectuur Scan)
```

Dit verifieert alle 5 lagen + alle .md bestanden automatisch.

---

## 5. RAG Gate Protocol

Alle schrijfacties in patchday doorlopen automatisch de RAG Gate (3-tier pre-execution validatie).

### `gate` subcommand
Standalone RAG Gate validatie voor willekeurige acties:
```bash
python patchday.py gate "beschrijving van de actie"
```
Dit voert de volledige 3-tier check uit (Static Rules, RAG Query, Governor) zonder een daadwerkelijke schrijfactie.

---

## 6. PatchDay Lifecycle

```bash
python patchday.py status    # Versie, branch, sync check
python patchday.py verify    # Pre-flight verificatie
python patchday.py test      # Volledige test suite
python patchday.py validate  # RAG pipeline validatie (7 checks)
python patchday.py bump patch|minor|major  # Versie ophogen (15 locaties)
python patchday.py release   # Volledig release workflow
python patchday.py gate "actie"  # RAG Gate validatie
```

---

## 7. Sovereign Gate

De Sovereign Gate (`sovereign_gate.py`) is ONAANRAAKBAAR:
- `DANNY_TEST_MODE` mag NOOIT de gate bypassen
- Gate heeft geen test modus, by design
- Tests die `fastapi_server` importeren moeten `except SystemExit` vangen
