# OMEGA SOVEREIGN - Cognitive Tiers (T1 t/m T6)

## T1: Intent Analysis & Routing (The Gatekeeper)

**Doel:** Het autonoom scheiden van conversationele verzoeken (MIND) en fysieke systeemtaken (BODY) op milliseconde-niveau.

### Automatisering

**Snelle Intentie-Classificatie:**
- Keyword pre-check tegen 30+ Nederlandse/Engelse actiewoorden (0ms)
- LLM fallback via Groq met `temperature=0.0` en `max_tokens=5`
- Classificeert als PRAAT of ACTIE

**Asynchrone Routering:**
- `routeer_commando()` wissel het verkeer onzichtbaar om
- Handmatige `swarm:` prefix dient altijd als absolute override (noodrem)
- Visuele routing-indicator in UI: `Routing: ACTIE → BODY` / `Routing: PRAAT → MIND`

**Implementatie:** `omega_v4.py` — `_bepaal_intentie()`, `_snelle_actie_check()`, `routeer_commando()`

---

## T2: Vector/Query Optimization (CorticalStack)

**Doel:** Optimaliseer zoekprestaties via vector_studio en verminder de token-load voor het LLM.

### Automatisering

**Semantisch gefilterde queries:**
- Voordat de SwarmEngine zoekt, wordt de query geoptimaliseerd om irrelevante ruis te elimineren
- `nlp_studio` voor semantische filtering

**Cache-mechanisme voor herhaalde queries:**
- `SemanticCache` (Voyage 256d) slaat veelvoorkomende antwoorden op
- Responstijd <0.1s voor cache hits, bespaart API-kosten

**Implementatie:** `danny_toolkit/core/semantic_cache.py`, `danny_toolkit/brain/cortical_stack.py`

---

## T3: Knowledge Synchronization (The SOUL)

**Doel:** Houd kennis up-to-date en synchroniseer de korte- en langetermijnherinneringen tussen systemen.

### Automatisering

**Contextuele injectie via vector_studio:**
- Memex agent verbonden met vector database voor accurate RAG-zoekopdrachten
- `TheCortex` Knowledge Graph (SQLite+NetworkX) voor hybrid search

**Herinnering-consolidatie:**
- `Dreamer` nachtelijke REM cycle (04:00): backup, vacuum, GhostWriter, anticipatie
- `daily_knowledge_backup()` — samenvat logs van afgelopen 24 uur
- Comprimeert en slaat op als permanente synapse

**Implementatie:** `danny_toolkit/brain/dreamer.py`, `danny_toolkit/brain/cortex.py`, `danny_toolkit/brain/unified_memory.py`

---

## T4: Error Handling & Self-Heal (Het Immuunsysteem)

**Doel:** Automatiseer foutafhandeling, rate-limits en herstelstrategieën zonder dat de applicatie crasht.

### Automatisering

**Geautomatiseerde herstel via error_classified logs:**
- Detecteer 429 Rate Limit of AttributeError
- Forceer autonoom een retry_task op de achtergrond
- `BlackBox` negative RAG: leert van fouten, antibody escalatie voorkomt herhalingen

**Fallback-mechanismen:**
- Streaming fallback chain: Groq Primary → Groq Fallback (aparte key) → NVIDIA NIM
- Bij 429: naadloze overschakeling zonder dataverlies
- NIM 400: non-streaming fallback als last resort
- `_build_stream_chain()` bouwt provider-specifieke kwargs

**Implementatie:** `danny_toolkit/brain/central_brain.py` — `genereer_stream()`, `_build_stream_chain()`

---

## T5: Swarm Orchestration & Tool Execution (The BODY)

**Doel:** Het delegeren van complexe, multi-step fysieke taken aan gespecialiseerde sub-agents.

### Automatisering

**Dynamische Agent Selectie:**
- `SwarmEngine` (4000+ regels) met AdaptiveRouter
- Nexus agent bepaalt autonoom of Strategist, Oracle, Memex of FileCreator nodig is
- `TaskArbitrator` voor auction-based agent assignment

**Anti-Hallucinatie & Output Verificatie:**
- `HallucinatieSchild` controleert output met harde score (0.00 tot 1.00)
- Context-aware bypass voor generatieve agents (16 agents whitelisted)
- `TruthAnchor` CPU cross-encoder fact verification voor RAG
- IJzeren Executie-Wet in streaming prompt: verbiedt fictieve acties

**Implementatie:** `swarm_engine.py`, `danny_toolkit/brain/hallucination_shield.py`, `danny_toolkit/brain/adversarial_tribunal.py`

---

## T6: System Evolution & Meta-Cognition (Singularity)

**Doel:** De hoogste vorm van autonomie waarbij het systeem zijn eigen code, tools en prompts kan evalueren en herschrijven.

### Automatisering

**Zelf-Genererende Tools:**
- `Artificer` schrijft autonoom nieuwe skills via forge-verify-execute loop
- `GhostWriter` scant AST en genereert automatisch docstrings via Groq
- `DevOpsDaemon` Ouroboros CI loop: test → analyze → BlackBox → NeuralBus

**Prompt-Evolutie:**
- Systeem leert van eerdere mislukkingen uit `BlackBox` error logs
- Voegt autonoom nieuwe waarschuwingen toe aan Systeem Prompt
- `TheSynapse` Hebbian routing: leert welke paden het beste werken
- `ThePhantom` anticipatory intelligence: voorspelt queries en pre-warmt context

**Implementatie:** `danny_toolkit/brain/artificer.py`, `danny_toolkit/brain/singularity.py`, `danny_toolkit/brain/synapse.py`, `danny_toolkit/brain/phantom.py`

---

## Architectuur Overzicht

```
T1 (Gatekeeper) ──→ PRAAT ──→ T2 (Cache) ──→ T3 (SOUL/RAG) ──→ MIND Stream
                 └→ ACTIE ──→ T4 (Self-Heal) ──→ T5 (BODY/Swarm) ──→ Tool Executie
                                                                    └→ T6 (Evolution)
```

| Tier | Naam | Locatie | Latency |
|------|------|---------|---------|
| T1 | Gatekeeper | omega_v4.py | 0-200ms |
| T2 | CorticalStack | semantic_cache.py | <100ms |
| T3 | SOUL | dreamer.py, cortex.py | 100-500ms |
| T4 | Immuunsysteem | central_brain.py | 0ms (inline) |
| T5 | BODY | swarm_engine.py | 1-30s |
| T6 | Singularity | artificer.py, singularity.py | async/overnight |
