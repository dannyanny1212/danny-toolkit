# Test Strategie — Danny Toolkit

## Overzicht

| Suite | Type | Runner | Bestanden |
|-------|------|--------|-----------|
| SwarmEngine | Unit + integratie | standalone + pytest | `test_swarm_engine.py` |
| CLI | Unit | standalone + pytest | `test_cli.py` |
| ProactiveEngine | Unit | standalone + pytest | `test_proactive.py` |
| SingularityEngine | Unit | standalone + pytest | `test_singularity.py` |
| Neural Hub | Live integratie | standalone | `test_neural_hub.py` |
| Cosmic Awareness | Unit | pytest | `danny_toolkit/test_cosmic_awareness.py` |
| Full Chain | Integratie (fixture) | pytest | `danny_toolkit/test_full_chain.py` |
| Stress & Concurrency | Performance | pytest (`stress` marker) | `tests/test_swarm_stress.py` |

## Commands

```bash
# Standaard tests (zonder stress)
danny test

# Inclusief stress/concurrency tests
danny test --stress

# Met coverage rapport
danny test --coverage

# Coverage + HTML rapport (htmlcov/index.html)
danny test --html

# Alles samen
danny test --stress --html

# Volledige CI pipeline (tests + stress + coverage + lint)
danny ci

# Standalone scripts (originele manier)
python test_swarm_engine.py
python test_cli.py
python test_proactive.py
python test_singularity.py
python test_neural_hub.py
```

## Test Categorien

### Unit Tests
Testen individuele componenten in isolatie:
- `SwarmPayload` dataclass
- `EchoAgent` responses
- `OmegaGovernor` input validatie
- `PipelineTuner` skip-logica
- `AdaptiveRouter` embedding routing
- PII scrubbing
- Command injection blocking

### Integratie Tests
Testen de volledige pipeline:
- `SwarmEngine.run()` met en zonder brain
- Multi-intent routing (meerdere agents parallel)
- Media generators (crypto, health, data charts)
- MEMEX context injectie
- Fast-track regex routing

### Stress & Concurrency Tests
Marker: `@pytest.mark.stress` — standaard uitgesloten.

| Test | Wat | Load |
|------|-----|------|
| `test_swarm_concurrency_stress` | 50 parallelle `engine.run()` | Hoog |
| `test_swarm_no_brain_stress` | 30 parallelle requests zonder brain | Medium |
| `test_routing_stress` | 100 parallelle `engine.route()` | Hoog |
| `test_mixed_load` | 20 fast-track + 20 routed gemixed | Medium |

Alle stress tests draaien zonder brain (geen API calls nodig).

## CI Pipeline

GitHub Actions (`.github/workflows/ci.yml`) draait bij elke push/PR naar `master`:

1. **Checkout** + Python 3.11 setup
2. **Install** dependencies (`pip install .[dev]`)
3. **Tests** met coverage (`pytest --cov=danny_toolkit`)

Lokaal exact hetzelfde draaien: `danny ci`

## Coverage

Coverage rapport wordt gegenereerd met `pytest-cov`:
- Terminal: `danny test --coverage`
- HTML: `danny test --html` → `htmlcov/index.html`

De CI pipeline genereert altijd een HTML rapport.

## Pytest Config

In `pyproject.toml`:
- Standaard: stress tests uitgesloten (`-m 'not stress'`)
- Coverage: altijd `danny_toolkit/` package
- Marker: `stress` geregistreerd (geen warnings)

## Nieuwe Tests Toevoegen

1. **Unit/integratie**: voeg toe aan bestaande `test_*.py` of maak nieuw bestand in root
2. **Stress tests**: voeg toe aan `tests/test_swarm_stress.py` met `@pytest.mark.stress`
3. **Pytest fixtures**: definieer in `tests/conftest.py`
