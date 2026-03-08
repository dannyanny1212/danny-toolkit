"""
Omega Sovereign Knowledge Injection — 72 Multi-Functionele Agent Documenten.

Injecteert 72 zelfbewustzijns-documenten in de unified vector store.
Elke doc helpt ALLE agents + Omega begrijpen wat ze moeten doen.

Gebruik: python ingest_omega_knowledge.py
"""

import json
import os
import sys
import time
from pathlib import Path

sys.stdout = open(sys.stdout.fileno(), mode="w", encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ.setdefault("CUDA_VISIBLE_DEVICES", "0")

from danny_toolkit.core.config import Config
from danny_toolkit.core.embeddings import get_embedder
from danny_toolkit.core.vector_store import VectorStore

# ── 72 Multi-Functionele Kennisdocumenten ──

OMEGA_DOCS = []


def doc(doc_id, tekst, category, agents, use_cases):
    """Helper: registreer een kennisdocument."""
    OMEGA_DOCS.append({
        "id": f"omega_kb_{doc_id}",
        "tekst": tekst.strip(),
        "metadata": {
            "category": category,
            "agents_suitable": agents,
            "use_cases": use_cases,
            "multi_functional": True,
            "omega_instruction": True,
            "source": "omega_knowledge_base",
            "version": "1.0",
        },
    })


# ═══════════════════════════════════════════════════════════════
# CATEGORIE 1: AGENT PROFIELEN (18 docs) — Wie doet wat?
# ═══════════════════════════════════════════════════════════════

doc("agent_iolaax", """
AGENT PROFIEL: IOLAAX (De Bouwer)
Rol: Autonome code-generatie agent. Bouwt nieuwe functionaliteit op verzoek.
Specialiteit: Python modules, classes, functies, tests schrijven.
Modus: always-forge — genereert altijd nieuwe code, hergebruikt nooit bestaande keywords.
Input: Beschrijving van gewenste functionaliteit in natuurlijke taal.
Output: Complete Python code met docstrings, type hints, en error handling.
Wanneer inzetten: Bij nieuwe feature requests, module creatie, of code-uitbreidingen.
Sub-profielen: Bouwer (nieuwe code), Monteur (reparatie), Expert (architectuur).
Samenwerking: Werkt met Sentinel (security check), Artificer (skill registratie), Strategist (planning).
""", "agent_profile", ["Iolaax", "CentralBrain", "Artificer", "Strategist"],
    ["code_generation", "feature_development", "module_creation"])

doc("agent_artificer", """
AGENT PROFIEL: ARTIFICER (De Smid)
Rol: Skill forge-verify-execute loop. Smeedt vaardigheden en registreert ze.
Specialiteit: Autonome skill creatie met verificatie via test-uitvoering.
Modus: forge → verify → execute — elke skill wordt getest voor registratie.
Input: Skill beschrijving of probleem dat een nieuwe vaardigheid vereist.
Output: Geregistreerde skill in /skills/forge/registry.json met test resultaten.
Wanneer inzetten: Als het systeem een nieuwe vaardigheid nodig heeft die nog niet bestaat.
Samenwerking: Ontvangt taken van Strategist, levert aan NeuralBus, gebruikt GhostWriter voor docs.
API Key: GROQ_API_KEY_FORGE (priority 3, 15s cooldown bij 429).
""", "agent_profile", ["Artificer", "Strategist", "CentralBrain", "GhostWriter"],
    ["skill_creation", "automation", "self_improvement"])

doc("agent_strategist", """
AGENT PROFIEL: STRATEGIST (De Strateeg)
Rol: Recursieve taak-planner met zoek-query meta-filter.
Specialiteit: Complexe taken decomponeren in uitvoerbare stappen.
Modus: decompose → delegate → chain — splitst, delegeert, koppelt resultaten.
Input: Complexe vraag of doel dat meerdere stappen vereist.
Output: Geordende takenlijst met agent-toewijzingen.
Wanneer inzetten: Bij ambiguë vragen, multi-stap problemen, of onderzoekstaken.
Meta-filter: Filtert search queries voor relevantie voordat agents worden aangestuurd.
Samenwerking: Stuurt VoidWalker (research), Artificer (skills), OracleEye (resources).
API Key: GROQ_API_KEY_RESEARCH (priority 2, 10s cooldown bij 429).
""", "agent_profile", ["Strategist", "CentralBrain", "VoidWalker", "Artificer"],
    ["task_planning", "decomposition", "delegation"])

doc("agent_voidwalker", """
AGENT PROFIEL: VOIDWALKER (De Verkenner)
Rol: Autonome web-researcher via DuckDuckGo + scraper.
Specialiteit: Externe informatie ophalen wanneer interne kennis ontbreekt.
Modus: search → scrape → summarize — zoekt, scrapt, vat samen.
Input: Onderzoeksvraag of informatiebehoefte.
Output: Samengevatte webresultaten (~1500 chars) voor context-injectie.
Wanneer inzetten: Als laatste redmiddel in _rag_enrich — wanneer VectorStore en Cortex geen antwoord geven.
Samenwerking: Aangestuurd door Strategist, levert aan trinity_omega._rag_enrich().
API Key: GROQ_API_KEY_WALKER (priority 3, 15s cooldown bij 429).
""", "agent_profile", ["VoidWalker", "Strategist", "CentralBrain"],
    ["web_research", "information_retrieval", "knowledge_gap"])

doc("agent_dreamer", """
AGENT PROFIEL: DREAMER (De Dromer)
Rol: Overnight REM cycle — geheugenconsolidatie en systeemoptimalisatie.
Specialiteit: Backup, vacuum, retentie, compressie, GhostWriter, anticipatie, OracleEye.
Schema: Draait automatisch om 04:00 via HeartbeatDaemon.
Stappen: 1) Backup CorticalStack 2) Vacuum 3) Retention policy 4) Compress docs
5) GhostWriter auto-docstrings 6) Anticipate (Phantom) 7) OracleEye resource forecast.
Verdeling: 40% recente docs + 40% oude docs voor gebalanceerde consolidatie.
Samenwerking: Gebruikt GhostWriter, TheMirror, OracleEye, Phantom, CorticalStack.
API Key: GROQ_API_KEY_OVERNIGHT (priority 5, 30s cooldown bij 429).
""", "agent_profile", ["Dreamer", "GhostWriter", "TheMirror", "OracleEye"],
    ["memory_consolidation", "overnight_maintenance", "optimization"])

doc("agent_ghostwriter", """
AGENT PROFIEL: GHOSTWRITER (De Schrijver)
Rol: AST scanner + auto-docstring generator via Groq.
Specialiteit: Python broncode scannen en ontbrekende docstrings automatisch genereren.
Input: Directory pad of individueel Python bestand.
Output: Bestanden aangevuld met kwalitatieve docstrings.
Wanneer inzetten: Tijdens Dreamer REM cycle, of handmatig voor code documentatie.
Multi-model: Kan meerdere modellen gebruiken via ModelRegistry.
Samenwerking: Onderdeel van Dreamer REM, werkt samen met GhostAmplifier (token elaboratie).
API Key: GROQ_API_KEY_OVERNIGHT (priority 5, 30s cooldown bij 429).
""", "agent_profile", ["GhostWriter", "GhostAmplifier", "Dreamer"],
    ["documentation", "code_quality", "ast_analysis"])

doc("agent_oracle", """
AGENT PROFIEL: ORACLE (De Wijze)
Rol: Will-Action-Verification reasoning loop.
Specialiteit: Diepe redenering via 3-staps verificatie.
Stappen: 1) WILL — formuleer intentie 2) ACTION — voer uit 3) VERIFY — controleer resultaat.
Input: Complexe vraag die diep nadenken vereist.
Output: Geverifieerd antwoord met confidence score.
Wanneer inzetten: Bij vragen die meerdere perspectieven of verificatie vereisen.
Samenwerking: CentralBrain WAV-Loop, HallucinatieSchild verificatie.
""", "agent_profile", ["Oracle", "CentralBrain", "Tribunal"],
    ["deep_reasoning", "verification", "wav_loop"])

doc("agent_sentinel", """
AGENT PROFIEL: SENTINEL (De Bewaker)
Rol: Security gating voor gegenereerde code en acties.
Specialiteit: Veiligheidscontrole op output van generatieve agents.
Input: Code of actie-output van Iolaax, Artificer, Weaver, Spark.
Output: sentinel_ok=True/False — bepaalt of output door HallucinatieSchild mag.
Wanneer inzetten: Automatisch bij alle generatieve agent output.
Regel: Generatieve agents + sentinel_ok → bypass RAG verificatie (score 1.0).
Generatieve agents + sentinel NOT ok → blokkade (score 0.0).
""", "agent_profile", ["Sentinel", "Iolaax", "Artificer", "HallucinatieSchild"],
    ["security", "code_review", "safety_gate"])

doc("agent_centralbrain", """
AGENT PROFIEL: CENTRALBRAIN (De Commandant)
Rol: Hoofd LLM orchestrator met function calling naar 31+ apps.
Specialiteit: Gebruikersvragen verwerken, tools aanroepen, fallback chain beheren.
Provider Chain: Groq Primary → Groq Fallback → Anthropic → NIM → HF → Ollama.
Sovereign Priority: Groq krijgt x2 auction boost. Reserve keys 1-3 bij rate limits.
Function Calling: 31 app tools beschikbaar (agenda, calculator, fitness, etc.).
Conversation History: Deque-based, max 4 berichten voor follow-up context.
Samenwerking: Stuurt SwarmEngine aan, ontvangt van OmegaGovernor (safety).
API Key: GROQ_API_KEY_USER (priority 0, 2s cooldown — hoogste prioriteit).
""", "agent_profile",
    ["CentralBrain", "OmegaGovernor", "SwarmEngine", "Iolaax", "Strategist"],
    ["orchestration", "user_interaction", "function_calling"])

doc("agent_governor", """
AGENT PROFIEL: OMEGAGOVERNOR (De Gouverneur)
Rol: Autonome safety guardian met rate limits en injection detectie.
Specialiteit: Input validatie, prompt injection detectie, PII scrubbing, token budget.
Mixins: GovernorFirewallMixin (validatie), GovernorStateMixin (state backup/restore).
Wanneer actief: Altijd — elke input naar CentralBrain gaat eerst door Governor.
Acties: Rate limit enforcement, anomaly detectie, systeem lockdown bij inbreuk.
Samenwerking: Gated op CentralBrain, stuurt alerts via Alerter.
""", "agent_profile", ["OmegaGovernor", "CentralBrain", "Alerter"],
    ["safety", "rate_limiting", "input_validation"])

doc("agent_devopsdaemon", """
AGENT PROFIEL: DEVOPSDAEMON (De CI Engineer)
Rol: Ouroboros CI loop — test → analyze → BlackBox → NeuralBus.
Specialiteit: Automatische test-runs, failure analyse, en immune memory opbouw.
Schema: Draait elke ~5 minuten via HeartbeatDaemon.
Stappen: 1) Run tests 2) Analyseer failures 3) Log in BlackBox 4) Publiceer op NeuralBus.
Output: Test rapport + failure patterns voor immuniteitsopbouw.
Samenwerking: HeartbeatDaemon trigger, BlackBox (failure memory), NeuralBus (events).
API Key: GROQ_API_KEY_KNOWLEDGE (priority 5, 30s cooldown bij 429).
""", "agent_profile", ["DevOpsDaemon", "BlackBox", "HeartbeatDaemon"],
    ["continuous_integration", "testing", "failure_analysis"])

doc("agent_cortex", """
AGENT PROFIEL: THECORTEX (Het Kennisnetwerk)
Rol: Knowledge Graph (SQLite + NetworkX) met hybride zoekfunctie.
Specialiteit: Grafiek-gebaseerde kennisexpansie — volgt relaties tussen concepten.
Methode: hybrid_search() combineert vector similarity + graaf-expansie.
Wanneer inzetten: Als VectorStore-zoekopdracht onvoldoende context geeft.
Graaf: NetworkX DiGraph — LET OP: bool(DiGraph()) is False bij lege graaf, altijd 'is not None' gebruiken.
Samenwerking: Gebruikt door trinity_omega._rag_enrich, Strategist, TheLibrarian.
API Key: GROQ_API_KEY_KNOWLEDGE (priority 4, 20s cooldown bij 429).
""", "agent_profile", ["TheCortex", "Strategist", "CentralBrain"],
    ["knowledge_graph", "semantic_search", "context_expansion"])

doc("agent_tribunal", """
AGENT PROFIEL: TRIBUNAL (De Rechter)
Rol: Async dual-model verificatie via Groq 70B + 8B.
Specialiteit: Cross-model consensus — twee modellen moeten het eens zijn.
Worker Model: llama-4-scout (70B parameters) — genereert antwoord.
Auditor Model: qwen3-32b (8B parameters) — verifieert antwoord.
Output: Consensus score + verified antwoord.
Wanneer inzetten: Bij kritische beslissingen die extra verificatie vereisen.
Samenwerking: AdversarialTribunal (Generator-Skeptic-Judge), TruthAnchor (CPU cross-encoder).
API Key: GROQ_API_KEY_VERIFY (priority 1, 5s cooldown bij 429).
""", "agent_profile", ["Tribunal", "AdversarialTribunal", "TruthAnchor"],
    ["verification", "consensus", "fact_checking"])

doc("agent_synapse", """
AGENT PROFIEL: THESYNAPSE (Het Zenuwstelsel)
Rol: Synaptic pathway plasticity — Hebbiaans leren voor adaptieve routing.
Specialiteit: Pathways versterken die succesvol zijn, verzwakken die falen.
Principe: "Neurons that fire together, wire together" — Hebb's regel.
Input: Agent execution resultaten (succes/failure).
Output: Aangepaste routing weights voor AdaptiveRouter.
Wanneer actief: Na elke agent executie in SwarmEngine pipeline + Dreamer REM.
Samenwerking: SwarmEngine pipeline, Dreamer REM consolidatie.
""", "agent_profile", ["TheSynapse", "SwarmEngine", "Dreamer"],
    ["adaptive_routing", "learning", "pathway_optimization"])

doc("agent_phantom", """
AGENT PROFIEL: THEPHANTOM (De Voorspeller)
Rol: Anticipatory intelligence — pre-warms MEMEX context.
Specialiteit: Voorspelt welke kennis nodig zal zijn en laadt deze alvast.
Input: Recente conversatie-patronen en trending topics.
Output: Pre-loaded context in MEMEX voor snellere responses.
Wanneer actief: SwarmEngine pipeline + Dreamer REM — anticipeert behoeften.
Samenwerking: Dreamer (nachtelijke anticipatie), SwarmEngine (real-time).
""", "agent_profile", ["ThePhantom", "SwarmEngine", "Dreamer"],
    ["prediction", "context_preloading", "anticipation"])

doc("agent_oracleeye", """
AGENT PROFIEL: THEORACLEEYE (Het Alziend Oog)
Rol: Predictieve resource scaler — voorspelt geheugen, CPU, en API gebruik.
Specialiteit: Resource monitoring en proactieve scaling beslissingen.
Input: Historische resource data (CPU%, RAM, VRAM, API calls).
Output: Scaling aanbevelingen en waarschuwingen.
Wanneer actief: Dreamer REM cycle + HeartbeatDaemon monitoring.
Samenwerking: Dreamer (resource forecast), HeartbeatDaemon (monitoring).
""", "agent_profile", ["TheOracleEye", "Dreamer", "HeartbeatDaemon"],
    ["resource_prediction", "scaling", "monitoring"])

doc("agent_mirror", """
AGENT PROFIEL: THEMIRROR (De Spiegel)
Rol: User profiling vanuit CorticalStack conversatie-historie.
Specialiteit: Analyseert de laatste 50 interacties om gebruikersprofiel bij te werken.
Input: CorticalStack events (automatisch).
Output: User profile JSON in /data/user_profile.json.
Wanneer actief: Dagelijks via Dreamer, of handmatig.
Profiel bevat: Interesses, communicatiestijl, technisch niveau, voorkeuren.
Samenwerking: Dreamer (dagelijkse update), CentralBrain (context enrichment).
API Key: GROQ_API_KEY_OVERNIGHT (priority 5, 30s cooldown bij 429).
""", "agent_profile", ["TheMirror", "Dreamer", "CentralBrain"],
    ["user_profiling", "personalization", "interaction_analysis"])

doc("agent_blackbox", """
AGENT PROFIEL: BLACKBOX (Het Immuunsysteem)
Rol: Negative RAG — failure memory die herhalingen voorkomt.
Specialiteit: Antibody escalatie — herhaalde fouten worden steeds strenger geblokkeerd.
Input: Foutpatronen van DevOpsDaemon, SwarmEngine, en agent executies.
Output: Waarschuwingen geïnjecteerd in _rag_enrich context.
Escalatie: 1e fout = warning, 2e = strong warning, 3e+ = critical block.
Singleton: get_black_box() — thread-safe met double-checked locking.
Samenwerking: DevOpsDaemon (failure recording), trinity_omega._rag_enrich (warning injection).
""", "agent_profile", ["BlackBox", "DevOpsDaemon", "CentralBrain"],
    ["failure_memory", "immune_system", "error_prevention"])


# ═══════════════════════════════════════════════════════════════
# CATEGORIE 2: COLLABORATION WORKFLOWS (12 docs)
# ═══════════════════════════════════════════════════════════════

doc("workflow_wav_loop", """
WORKFLOW: WAV-LOOP (Will → Action → Verify)
Doel: Kernpipeline voor alle gebruikersvragen in Omega.
Stappen:
1. WILL — CentralBrain plant de aanpak (function calling, tools selecteren).
2. ACTION — Voer tools uit, haal data op, genereer antwoord.
3. VERIFY — Ollama verificatie + HallucinatieSchild 95% Barrière.
Trigger: Elke vraag in Omega Soul/Mind terminal.
Betrokken: CentralBrain, OmegaGovernor, HallucinatieSchild, Ollama.
Fallback: Bij falen → volgende provider in Sovereign chain.
""", "workflow", ["CentralBrain", "OmegaGovernor", "HallucinatieSchild"],
    ["question_answering", "pipeline", "verification"])

doc("workflow_swarm_pipeline", """
WORKFLOW: SWARM PIPELINE (7-staps agent executie)
Doel: Multi-agent taakuitvoering via SwarmEngine.
Stappen:
1. Input parsing + AdaptiveRouter agent selectie
2. TheSynapse bias ophalen (Hebbiaans gewogen)
3. ThePhantom context pre-warming
4. Agent executie (parallel via asyncio.gather)
5. WaakhuisMonitor latency registratie
6. SemanticCache opslaan
7. HallucinatieSchild output verificatie
7.5. Context-Aware Bypass voor generatieve agents + Sentinel
Betrokken: SwarmEngine, AdaptiveRouter, TheSynapse, ThePhantom, WaakhuisMonitor.
""", "workflow", ["SwarmEngine", "CentralBrain", "Iolaax", "Strategist"],
    ["multi_agent", "parallel_execution", "task_routing"])

doc("workflow_dreamer_rem", """
WORKFLOW: DREAMER REM CYCLE (Nachtelijke Optimalisatie)
Doel: Geheugenconsolidatie en systeemonderhoud om 04:00.
Stappen:
1. Backup CorticalStack (compress=True)
2. Vacuum SQLite database
3. Retention policy toepassen (oude events opruimen)
4. Document compressie (40% recent + 40% oud)
5. GhostWriter auto-docstrings genereren
6. ThePhantom anticipatie (pre-warm voor morgen)
7. OracleEye resource forecast
Trigger: HeartbeatDaemon om 04:00 automatisch.
Betrokken: Dreamer, GhostWriter, ThePhantom, OracleEye, CorticalStack.
""", "workflow", ["Dreamer", "GhostWriter", "ThePhantom", "OracleEye"],
    ["overnight_maintenance", "memory_consolidation", "self_healing"])

doc("workflow_devops_ci", """
WORKFLOW: DEVOPS CI LOOP (Ouroboros — Zelfherstellend)
Doel: Continue integratie met automatische failure analyse.
Stappen:
1. Run alle test suites (48 suites via run_all_tests.py)
2. Analyseer failures met Groq LLM
3. Log failure patterns in BlackBox (immune memory)
4. Publiceer resultaten op NeuralBus (EVENT: TEST_RESULTS)
5. Bij herhaalde failures: BlackBox escalatie (antibody)
Frequentie: Elke ~5 minuten via HeartbeatDaemon.
Betrokken: DevOpsDaemon, BlackBox, NeuralBus, HeartbeatDaemon.
""", "workflow", ["DevOpsDaemon", "BlackBox", "HeartbeatDaemon"],
    ["testing", "continuous_integration", "self_repair"])

doc("workflow_generaal_auction", """
WORKFLOW: GENERAAL MODE — Model Auction
Doel: Extern AI-model selecteren voor complexe taken.
Formule: S_model = (capability_match × success_rate) / (cost_tier + latency_class)
Sovereign Priority: Groq workers krijgen x2 score boost.
Fallback Keten: Groq Primary → Groq Fallback → Reserve 1→2→3 → NIM → Gemini → Ollama.
Reserve Key Rotation: Bij 429 rate limit, GroqModelWorker roteert automatisch door reserve keys.
95% Barrière: Elk model-resultaat moet door HallucinatieSchild (score >= 0.35).
Ontslagen: Model dat Barrière faalt wordt uitgesloten + retry met volgend model.
Betrokken: TaskArbitrator, ModelRegistry, GroqModelWorker, HallucinatieSchild.
""", "workflow", ["TaskArbitrator", "CentralBrain", "HallucinatieSchild"],
    ["model_selection", "auction", "sovereign_priority"])

doc("workflow_rag_enrich", """
WORKFLOW: RAG ENRICHMENT PIPELINE (_rag_enrich)
Doel: Elke agent-taak verrijken met relevante kenniscontext.
Prioriteit Keten:
1. BlackBox waarschuwingen ophalen (failure patterns)
2. TheLibrarian ChromaDB query (top 5 resultaten)
3. TruthAnchor CPU cross-encoder verificatie (top 3)
4. Fallback: TheCortex Knowledge Graph hybrid_search
5. Laatste redmiddel: VoidWalker web research (~1500 chars)
Output: "KENNISBANK CONTEXT:\n{docs}\n\nVRAAG: {task}"
Bypass: Generatieve agents + sentinel_ok → skip RAG verificatie (score 1.0).
""", "workflow", ["CentralBrain", "BlackBox", "TheCortex", "VoidWalker"],
    ["knowledge_retrieval", "context_enrichment", "rag"])

doc("workflow_omega_awaken", """
WORKFLOW: OMEGA AWAKENING SEQUENCE
Doel: Alle subsystemen activeren bij 'omega' commando.
Volgorde:
1. SOUL — CorticalStack + NeuralBus
2. MIND — CentralBrain + PrometheusBrain
3. BODY — SwarmEngine + AdaptiveRouter
4. IMMUNE — OmegaGovernor + HallucinatieSchild + BlackBox
5. MONITORING — WaakhuisMonitor + ConfigAuditor + Introspector
6. API — FastAPI server op poort 8000
7. Browser opent http://127.0.0.1:8000/ui/
Na awakening: Auto-dispatch (diagnostic + DevOps + SwarmEngine probe).
""", "workflow", ["CentralBrain", "SwarmEngine", "OmegaGovernor"],
    ["system_startup", "initialization", "activation"])

doc("workflow_neural_bus", """
WORKFLOW: NEURALBUS EVENT SYSTEM
Doel: Pub/sub communicatie tussen alle modules.
Methode: Fire-and-forget, 100% non-blocking.
Event Signing: Elk event wordt gevalideerd op herkomst.
History: deque(maxlen=100) per event type.
Thread Safety: RLock voor thread-safe operaties.
Event Types: WEATHER_UPDATE, HEALTH_STATUS_CHANGE, AGENDA_UPDATE, MOOD_UPDATE, etc.
Sync callbacks: ThreadPoolExecutor (daemon threads).
Async callbacks: asyncio.create_task.
Spoofed events worden genegeerd en gelogd als aanval.
""", "workflow", ["NeuralBus", "SwarmEngine", "ProactiveEngine", "Sensorium"],
    ["event_system", "pub_sub", "communication"])

doc("workflow_key_rotation", """
WORKFLOW: SOVEREIGN KEY ROTATION
Doel: Automatische API key rotatie bij rate limits.
Pool: 12 Groq keys (7 role-based + 1 fallback + 3 reserve + 1 primary).
Agent Priority: CentralBrain(0) → Tribunal(1) → Strategist(2) → VoidWalker(3) →
Artificer(3) → TheCortex(4) → DevOpsDaemon(5) → Dreamer/GhostWriter/TheMirror(5).
Cooldown per priority: P0=2s, P1=5s, P2=10s, P3=15s, P4=20s, P5=30s.
Rate Limits: llama-4-scout 30 RPM/30K TPM, qwen3-32b 60 RPM/6K TPM.
Reserve Rotation: GroqModelWorker roteert door RESERVE_1→2→3 bij 429.
Alle agents gebruiken km.get_key("AgentName") — geen hardcoded GROQ_API_KEY.
""", "workflow", ["CentralBrain", "Tribunal", "Strategist", "Artificer"],
    ["rate_limiting", "key_management", "failover"])

doc("workflow_hallucination_check", """
WORKFLOW: HALLUCINATIESCHILD — Output Verificatie
Doel: 95% Barrière — voorkomt hallucinaties in AI output.
Stappen:
1. Claim-scoring: splits antwoord in individuele claims
2. Contradiction detectie: zoekt tegenstrijdigheden
3. RAG fact-checking: verifieert claims tegen kennisbank
4. Context-Aware Bypass: generatieve agents + sentinel_ok → score 1.0
Drempels: score < 0.35 = GEBLOKKEERD, < 0.55 = WAARSCHUWING, >= 0.55 = OK.
Singleton: get_hallucination_shield() — thread-safe.
Gebruikt door: SwarmEngine stap 7.5, execute_goal, WAV-Loop verificatie.
""", "workflow",
    ["HallucinatieSchild", "CentralBrain", "SwarmEngine", "Tribunal"],
    ["hallucination_prevention", "fact_checking", "output_validation"])

doc("workflow_self_repair", """
WORKFLOW: SELF-REPAIR PROTOCOL
Doel: Automatische diagnose en reparatie bij systeemfouten.
Stappen:
1. Error detectie via ErrorTaxonomy classificatie
2. Deterministische repair poging (bekende fixes)
3. LLM-gebaseerde repair (Groq analyse van error)
4. Resultaat logging in CorticalStack
5. BlackBox registratie voor toekomstige preventie
Trigger: Automatisch bij runtime errors, of handmatig via CLI.
Betrokken: SelfRepairProtocol, ErrorTaxonomy, BlackBox, CorticalStack.
""", "workflow", ["SelfRepairProtocol", "ErrorTaxonomy", "BlackBox"],
    ["error_recovery", "self_healing", "diagnostics"])

doc("workflow_arbitrator_goals", """
WORKFLOW: ARBITRATOR GOAL DECOMPOSITION
Doel: Complexe doelen opsplitsen en aan agents toewijzen via veiling.
Stappen:
1. Goal ontvangen van CentralBrain of gebruiker
2. Decompose in SwarmTasks (categorie: code/research/analyse/creatief)
3. Auction per taak: score agents op capability × success_rate
4. Toewijzen aan winnende agent
5. Parallel uitvoeren via asyncio.gather
6. Resultaten aggregeren in GoalManifest
Betrokken: TaskArbitrator, ModelRegistry, SwarmEngine, CentralBrain.
""", "workflow", ["TaskArbitrator", "CentralBrain", "SwarmEngine"],
    ["goal_decomposition", "task_assignment", "auction"])


# ═══════════════════════════════════════════════════════════════
# CATEGORIE 3: SYSTEM ARCHITECTUUR (10 docs)
# ═══════════════════════════════════════════════════════════════

doc("arch_brain_tiers", """
ARCHITECTUUR: BRAIN TIERS (6 Lagen)
Tier 1 — Core Intelligence: CentralBrain, PrometheusBrain, OmegaGovernor, CorticalStack, TaskArbitrator.
Tier 2 — Verification & Safety: HallucinatieSchild, AdversarialTribunal, Tribunal, TruthAnchor, RealityAnchor, CitationMarshall, ShadowGovernance.
Tier 3 — Autonomous Agents: Strategist, Artificer, VoidWalker, Dreamer, GhostWriter, GhostAmplifier, DevOpsDaemon.
Tier 4 — Knowledge & Memory: TheCortex, BlackBox, UnifiedMemory, ClaudeMemory, TheMirror.
Tier 5 — Prediction & Adaptation: SingularityEngine, TheSynapse, ThePhantom, TheOracleEye, ProactiveEngine.
Tier 6 — Infrastructure & Monitoring: ModelRegistry, ObservatorySync, WaakhuisMonitor, ConfigAuditor, SystemIntrospector, FileGuard.
Totaal: 60+ modules, ~50K lines of code.
""", "architecture", ["CentralBrain", "SwarmEngine", "SystemIntrospector"],
    ["system_overview", "tier_structure", "module_map"])

doc("arch_sovereign_gate", """
ARCHITECTUUR: SOVEREIGN GATE — 7 IJzeren Wetten
Code weigert te draaien tenzij aan ALLE voorwaarden is voldaan:
1. Root Integrity: Pad moet exact C:\\Users\\danny\\danny-toolkit zijn.
2. Authority Check: Administrator privileges vereist.
3. Terminal Lock: Native PowerShell verplicht.
4. Physical Console: Geen remote (RDP) of verborgen sessies.
5. Identity Binding: Dual-Key Git Email whitelist.
6. Hardware Fingerprint: CPU ID & MAC-adres moeten overeenkomen.
7. Iron Dome Network: Default-Deny uitgaand verkeer profiel.
BELANGRIJK: DANNY_TEST_MODE mag NOOIT de sovereign gate bypassen.
""", "architecture", ["CentralBrain", "OmegaGovernor"],
    ["security", "access_control", "system_integrity"])

doc("arch_memory_stack", """
ARCHITECTUUR: MEMORY STACK (3 Lagen)
Laag 1 — Episodic Memory (CorticalStack):
  SQLite WAL mode, 64 MB cache, 256 MB mmap.
  Tabellen: episodic_memory, semantic_memory, system_stats.
  API: log_event(), get_recent_events(), flush(), backup().
Laag 2 — Semantic Memory (VectorStore):
  JSON-backed, Voyage AI embeddings (256d MRL truncation).
  API: voeg_toe(), zoek(), zoek_op_metadata().
Laag 3 — Immune Memory (BlackBox):
  Negative RAG — failure patterns met antibody escalatie.
  API: record_failure(), retrieve_warnings().
Alle lagen thread-safe via Lock/RLock patronen.
""", "architecture", ["CorticalStack", "VectorStore", "BlackBox"],
    ["memory_system", "data_storage", "persistence"])

doc("arch_provider_chain", """
ARCHITECTUUR: AI PROVIDER FALLBACK CHAIN
Volgorde (strikt): Groq Primary → Groq Fallback → Anthropic → NIM → HuggingFace → Ollama.
Sovereign Priority: Groq krijgt x2 auction boost in Generaal Mode.
Per-Provider Circuit Breakers: 3 consecutive failures → circuit open → 12 cycle cooldown.
Providers: groq_70b, groq_8b, anthropic, nvidia_nim, huggingface, ollama.
Key Pool: 12 Groq keys via SmartKeyManager. Reserve rotation bij 429.
Rate Limits: llama-4-scout 30 RPM/30K TPM/500K TPD. qwen3-32b 60 RPM/6K TPM/500K TPD.
ALLE agents gebruiken km.get_key("AgentName") — geen directe os.getenv("GROQ_API_KEY").
""", "architecture", ["CentralBrain", "TaskArbitrator", "ModelRegistry"],
    ["provider_chain", "failover", "rate_limiting"])

doc("arch_daemon_system", """
ARCHITECTUUR: DAEMON SYSTEEM (6 modules)
HeartbeatDaemon: Autonome achtergrond daemon, CPU-aware pools, reflectie. ~5min cycle.
DigitalDaemon: Always-on symbiotic entity met persoonlijkheid.
LimbicSystem: Emotioneel brein — data/events → emoties/stemmingen.
Metabolisme: Energiesysteem, consumptie, gezondheidsbalans.
Sensorium: Sensorisch systeem voor 35+ app events.
CoherenceMonitor: CPU+GPU load correlatie detector.
Alle daemon modules leven in /daemon/ en draaien onafhankelijk van brain/.
""", "architecture", ["HeartbeatDaemon", "DigitalDaemon", "Sensorium"],
    ["daemon_system", "background_processing", "autonomy"])

doc("arch_swarm_engine", """
ARCHITECTUUR: SWARM ENGINE (Centraal Zenuwstelsel)
Locatie: Root-niveau (swarm_engine.py) — NOOIT importeren als danny_toolkit.core.swarm_engine.
Import: from swarm_engine import SwarmEngine
Functies: CPU-aware worker pools, asyncio.gather parallelle executie, AdaptiveRouter.
Workers: min(max(os.cpu_count(), 4), 16) — schaalt met hardware.
Pipeline: Input → Router → Synapse bias → Phantom pre-warm → Agent → Waakhuis → Cache → Schild.
AdaptiveRouter: Embedding-based cosine similarity met keyword fallback.
Agent Profiles: 18 agents (Iolaax, Cipher, Vita, Navigator, Oracle, Spark, Sentinel, etc.).
""", "architecture", ["SwarmEngine", "CentralBrain", "AdaptiveRouter"],
    ["orchestration", "parallel_execution", "routing"])

doc("arch_apps_ecosystem", """
ARCHITECTUUR: APPS ECOSYSTEEM (29 apps, 31 tools)
Alle apps leven in /apps/ en worden aangestuurd via CentralBrain function calling.
Apps: Agenda, Calculator, Code Analyse, Expense Tracker, Fitness Tracker, Flashcards,
Goals Tracker, Habit Tracker, Language Tutor, Mood Tracker, Music Composer, Notitie,
Password Generator, Pomodoro Timer, Recipe Generator, Room Planner, Schatzoek, Weer Info, etc.
Elke app heeft: LUISTERT_NAAR (NeuralBus events), PUBLICEERT (output events).
State: Per-app JSON files in /data/apps/*.json.
BaseApp: publish(), get_bus_context() — standaard NeuralBus integratie.
""", "architecture", ["CentralBrain", "NeuralBus", "SwarmEngine"],
    ["apps", "function_calling", "tools"])

doc("arch_data_layout", """
ARCHITECTUUR: DATA LAYOUT (Persistent State)
/data/rag/chromadb/ — ChromaDB vector store (3 shards: code/docs/data).
/data/cortical_stack.db — SQLite episodic + semantic memory (WAL mode, 64MB cache).
/data/brain_memory/unified_vectors.json — Unified vector store (146+ docs).
/data/brain_memory/event_log.json — Event timeline (197+ events).
/data/apps/*.json — Per-app state files (29 apps).
/data/logs/ — System logs, daemon heartbeat, FastAPI startup.
/data/plots/ — Screenshots, generated images.
/data/rag/documenten/ — RAG ingestion source material (13 files).
REGEL: /data/ mag NOOIT direct aangepast worden via code — gebruik memory interfaces.
""", "architecture", ["CorticalStack", "VectorStore", "UnifiedMemory"],
    ["data_storage", "file_structure", "persistence"])

doc("arch_hardware_optimization", """
ARCHITECTUUR: HARDWARE OPTIMALISATIE STACK
GPU: RTX 3060 Ti (8 GB VRAM). VRAMBudgetGuard serialiseert GPU workloads.
GPU Strategie: Groq cloud voor text ($0 VRAM), Ollama llava voor vision (~4.7 GB).
SQLite: 64 MB cache + 256 MB mmap + WAL + NORMAL sync — Config.apply_sqlite_perf(conn).
Swarm Workers: CPU-core-aware — min(max(cpu_count, 4), 16).
Heartbeat Pool: max(cpu_count // 4, 2) — schaalt met hardware.
MRL Truncation: ProcessPoolExecutor bij >500 vectors.
GPU Batching: Adaptive 8-128 gebaseerd op CPU% + VRAM.
Windows Defender: Exclusions op project + venv + data dirs.
""", "architecture", ["SwarmEngine", "HeartbeatDaemon", "VRAMBudgetGuard"],
    ["hardware", "gpu", "performance_optimization"])

doc("arch_security_layers", """
ARCHITECTUUR: SECURITY LAGEN
Laag 1 — Sovereign Gate: 7 IJzeren Wetten (hardware + identity binding).
Laag 2 — OmegaGovernor: Input validatie, injection detectie, PII scrubbing.
Laag 3 — HallucinatieSchild: Output verificatie, 95% Barrière.
Laag 4 — ShadowGovernance: 3-zone kloon-restricties (ROOD/GEEL/GROEN).
Laag 5 — FileGuard: Source integrity via manifest + SHA256.
Laag 6 — Iron Dome Network: Default-Deny uitgaand verkeer.
Anti-Hallucinatie Wet: Als je het antwoord niet weet — niet gokken.
Paranoïde Zero-Trust: Host-OS, externe domeinen, hardware als potentieel vijandig.
""", "architecture", ["OmegaGovernor", "HallucinatieSchild", "ShadowGovernance"],
    ["security", "defense_in_depth", "zero_trust"])


# ═══════════════════════════════════════════════════════════════
# CATEGORIE 4: OPERATIONELE PROCEDURES (15 docs)
# ═══════════════════════════════════════════════════════════════

doc("proc_rate_limit_recovery", """
PROCEDURE: RATE LIMIT RECOVERY
Wanneer: Groq API geeft 429 Too Many Requests.
Stap 1: GroqModelWorker roteert automatisch naar reserve key 1.
Stap 2: Als key 1 ook vol → reserve key 2 → reserve key 3.
Stap 3: Alle reserves uitgeput → circuit breaker opent (3 fails).
Stap 4: Auction kiest volgende provider (NIM → Gemini → Ollama).
Cooldown: Afhankelijk van agent priority (P0=2s tot P5=30s).
Preventie: SmartKeyManager registreer_429() tracked hits per agent.
Global Cooldown: 5+ 429s → 60s global cooldown op hele pool.
""", "procedure", ["CentralBrain", "TaskArbitrator", "ModelRegistry"],
    ["error_recovery", "rate_limiting", "failover"])

doc("proc_memory_management", """
PROCEDURE: MEMORY MANAGEMENT
CorticalStack:
  - log_event() voor episodic memory (actor, action, source, data).
  - flush() om pending writes te forceren.
  - backup(compress=True) voor dagelijkse backup.
  - apply_retention_policy() om oude events op te ruimen.
VectorStore:
  - voeg_toe([{id, tekst, metadata}]) voor nieuwe documenten.
  - zoek(query, top_k=5) voor semantic search.
  - SelfPruning: entropy/recency/redundancy opruiming.
UnifiedMemory:
  - store_event() voor app events met embeddings.
  - query_cross_app() voor cross-app semantic search.
""", "procedure", ["CorticalStack", "VectorStore", "UnifiedMemory"],
    ["memory_management", "data_lifecycle", "cleanup"])

doc("proc_error_handling", """
PROCEDURE: ERROR HANDLING
Diamond Polish Wetten:
1. Elke error wordt via CorticalStack gelogd: _log_to_cortical().
2. ErrorTaxonomy classificeert de error (type, severity, recovery).
3. BlackBox registreert failure pattern (antibody escalatie).
4. NeuralBus publiceert ERROR event.
5. SelfRepairProtocol probeert automatisch te repareren.
VERBODEN:
- Geen bare 'except Exception: pass' — altijd logger.debug().
- Geen errors negeren — minimaal loggen voor immuniteitsopbouw.
- Geen placeholder code (pass, TODO) — alleen complete implementaties.
""", "procedure", ["ErrorTaxonomy", "BlackBox", "SelfRepairProtocol"],
    ["error_handling", "debugging", "resilience"])

doc("proc_new_agent_creation", """
PROCEDURE: NIEUWE AGENT CREËREN
Stap 1: Maak bestand in /brain/ met class die de agent implementeert.
Stap 2: Gebruik KeyManager voor Groq client:
  if HAS_KEY_MANAGER:
      km = get_key_manager()
      self.client = km.create_async_client("AgentName")
      if not self.client:
          self.client = AsyncGroq(api_key=km.get_key("AgentName"))
Stap 3: Registreer in AdaptiveRouter agent profiles.
Stap 4: Voeg wiring toe aan Introspector._KNOWN_MODULES en _KNOWN_WIRINGS.
Stap 5: Wire in SwarmEngine pipeline of HeartbeatDaemon.
Stap 6: Voeg test toe aan run_all_tests.py.
""", "procedure", ["CentralBrain", "SwarmEngine", "SystemIntrospector"],
    ["development", "agent_creation", "onboarding"])

doc("proc_rag_ingestion", """
PROCEDURE: RAG DOCUMENT INGESTION
Methode 1 — TheLibrarian:
  from danny_toolkit.skills.librarian import TheLibrarian
  lib = TheLibrarian()
  lib.ingest_directory("/pad/naar/docs")
  Chunk size: 350 tokens (Config.CHUNK_SIZE).
Methode 2 — VectorStore direct:
  store.voeg_toe([{"id": "doc_1", "tekst": "content", "metadata": {...}}])
Methode 3 — UnifiedMemory:
  memory.store_event(app="omega", event_type="knowledge", params={}, result={})
Metadata standaard: bron, pad, chunk_nr, totaal_chunks, extensie, grootte_bytes.
""", "procedure", ["VectorStore", "UnifiedMemory", "TheCortex"],
    ["rag_ingestion", "knowledge_management", "document_processing"])

doc("proc_test_execution", """
PROCEDURE: TEST UITVOERING
Runner: python run_all_tests.py (48 test suites).
Environment: CUDA_VISIBLE_DEVICES=-1, DANNY_TEST_MODE=1, ANONYMIZED_TELEMETRY=False.
Python: C:/Users/danny/danny-toolkit/venv311/Scripts/python.exe (Python 3.11.9).
NOOIT bare 'python' gebruiken — altijd het venv311 pad.
Sovereign Gate: DANNY_TEST_MODE mag NOOIT de gate bypassen — by design.
Tests die fastapi_server importeren moeten except SystemExit vangen.
Per-test timeout: 150 seconden. Subprocess isolatie per test.
""", "procedure", ["DevOpsDaemon", "CentralBrain"],
    ["testing", "quality_assurance", "ci_cd"])

doc("proc_version_sync", """
PROCEDURE: VERSION SYNC
Huidige versie: 6.11.0
Bestanden die version bevatten:
  - danny_toolkit/brain/__init__.py (VERSION)
  - danny_toolkit/learning/__init__.py
  - CLAUDE.md (Tribunal Assessment)
Bij version bump: ALLE bestanden synchroon updaten.
Commit message format: sync(version): bump all display strings to vX.Y.Z
""", "procedure", ["CentralBrain", "ConfigAuditor"],
    ["versioning", "release_management", "sync"])

doc("proc_import_rules", """
PROCEDURE: IMPORT WETTEN (Diamond Polish)
Wet 1: ALLE imports MOETEN absoluut zijn vanaf de root.
  GOED: from danny_toolkit.core.config import Config
  FOUT: from ..core import Config
Wet 2: swarm_engine.py leeft op root-niveau.
  GOED: from swarm_engine import SwarmEngine
  FOUT: from danny_toolkit.core.swarm_engine import SwarmEngine
Wet 3: Alle zware imports in try/except ImportError:
  try:
      from danny_toolkit.brain.some_module import SomeClass
      HAS_SOME = True
  except ImportError:
      HAS_SOME = False
Wet 4: import_analyzer.py scant op overtredingen.
""", "procedure", ["CentralBrain", "SwarmEngine", "ConfigAuditor"],
    ["coding_standards", "import_rules", "code_quality"])

doc("proc_windows_utf8", """
PROCEDURE: WINDOWS UTF-8 ENCODING
Bij elk nieuw entry point:
  sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
Of simpeler:
  import sys; sys.stdout.reconfigure(encoding="utf-8")
Subprocess env: PYTHONIOENCODING=utf-8.
JSON files: encoding="utf-8" bij open().
CUDA_VISIBLE_DEVICES="-1" (niet "" — segfaults op Windows).
""", "procedure", ["CentralBrain", "DevOpsDaemon"],
    ["windows", "encoding", "compatibility"])

doc("proc_config_management", """
PROCEDURE: CONFIGURATIE MANAGEMENT
Centraal: danny_toolkit/core/config.py — Config class.
LLM_PROVIDER: groq. LLM_MODEL: meta-llama/llama-4-scout-17b-16e-instruct.
LLM_FALLBACK_MODEL: qwen/qwen3-32b. VISION_PROVIDER: ollama. VISION_MODEL: llava:latest.
EMBEDDING_PROVIDER: voyage. EMBEDDING_DIM: 256 (env override).
CHUNK_SIZE: 350 — canonical source, librarian.py importeert hiervan.
SQLite optimalisatie: Config.apply_sqlite_perf(conn) — wired in 8 modules.
ConfigAuditor: Runtime validatie, drift detectie, alerts via Alerter.
""", "procedure", ["ConfigAuditor", "CentralBrain", "Alerter"],
    ["configuration", "settings", "validation"])

doc("proc_backup_strategy", """
PROCEDURE: BACKUP STRATEGIE
CorticalStack: backup(compress=True) — dagelijks via Dreamer REM (04:00).
VectorStore: maak_backup() — voor elke destructieve operatie.
GovernorState: backup_rotation — 3 roterende state backups.
FileGuard: manifest + SHA256 voor source integrity.
Data directory: /data/ — bevat alle persistent state.
NOOIT data direct via code aanpassen — gebruik memory interfaces.
Restore: CorticalStack.restore(path), VectorStore.herstel_backup().
""", "procedure", ["Dreamer", "CorticalStack", "VectorStore", "FileGuard"],
    ["backup", "disaster_recovery", "data_protection"])

doc("proc_debug_troubleshoot", """
PROCEDURE: DEBUGGING & TROUBLESHOOTING
Stap 1: Check RAG laag eerst — corrupted RAG files killen LLM silent.
Stap 2: danny verify uitvoeren na index/ingestion changes.
Stap 3: Check circuit breakers — per-provider isolatie essentieel.
Stap 4: Check stale Python processes — SQLite locks (busy_timeout=5000).
Stap 5: Check CUDA — CUDA_VISIBLE_DEVICES="-1" (niet "").
Stap 6: Check asyncio — asyncio.run() in async def is FATAAL.
Stap 7: NetworkX DiGraph — bool() is False bij lege graaf, altijd 'is not None'.
Stap 8: duckduckgo-search heet nu 'ddgs' — pip install ddgs.
""", "procedure", ["CentralBrain", "DevOpsDaemon", "SelfRepairProtocol"],
    ["debugging", "troubleshooting", "common_errors"])

doc("proc_omega_terminal_commands", """
PROCEDURE: OMEGA TERMINAL COMMANDO'S
Sovereign Soul Terminal (links):
  omega — Awaken all systems + API server
  status — Omega mode status + uptime
  agents — Lijst van beschikbare agents
  health — Systeem gezondheid
  keys — KeyManager pool + reserve status
  cortical — CorticalStack metrics
  brain — Brain tier status
  diag — Self-diagnostic scan
  search <term> — RAG zoeken
  py <code> — Python uitvoeren
Sovereign Mind Terminal (midden):
  wav <vraag> — Groq WAV-Loop
  status — Session + Sovereign chain info
  new — Nieuwe conversatie
Sovereign Body Terminal (rechts):
  PowerShell subprocess — echte shell commando's.
""", "procedure", ["CentralBrain", "SwarmEngine"],
    ["terminal_commands", "ui_guide", "user_interface"])

doc("proc_sovereign_key_routing", """
PROCEDURE: SOVEREIGN KEY ROUTING
Alle agents gebruiken KeyManager voor API key selectie:
  km = get_key_manager()
  client = km.create_async_client("AgentName")
  if not client:
      client = AsyncGroq(api_key=km.get_key("AgentName"))
Key Mapping:
  GROQ_API_KEY_USER → CentralBrain (P0)
  GROQ_API_KEY_VERIFY → Tribunal (P1)
  GROQ_API_KEY_RESEARCH → Strategist (P2)
  GROQ_API_KEY_WALKER → VoidWalker (P3)
  GROQ_API_KEY_FORGE → Artificer (P3)
  GROQ_API_KEY_OVERNIGHT → Dreamer, GhostWriter, TheMirror (P5)
  GROQ_API_KEY_KNOWLEDGE → TheCortex, DevOpsDaemon (P4)
  GROQ_API_KEY_RESERVE_1-3 → reserve pool (rate limit rotation)
  GROQ_API_KEY_FALLBACK → dedicated fallback model pool
""", "procedure", ["CentralBrain", "Tribunal", "Strategist", "Artificer"],
    ["key_management", "api_routing", "sovereign_priority"])

doc("proc_log_rotation_cleanup", """
PROCEDURE: LOG ROTATIE & CLEANUP
Het systeem genereert logs, plots, en tijdelijke bestanden die regelmatig opgeruimd moeten worden.
Automatisch:
  - Dreamer REM cycle (04:00): vacuum CorticalStack, compress oude entries
  - log_rotation.py: verwijdert logs ouder dan 7 dagen
  - SelfPruning: vectorstore entropy/redundancy cleanup
Handmatig:
  - /data/logs/ — oude .log bestanden verwijderen
  - /data/plots/ — oude screenshots opruimen
  - CorticalStack: apply_retention_policy() voor compressie
  - VectorStore: self_pruning.run() voor vector cleanup
Monitoring:
  - WaakhuisMonitor trackt disk usage en waarschuwt bij >80% vol
  - ConfigAuditor detecteert stale config bestanden
  - Introspector rapporteert data directory grootte
Frequentie: dagelijks (Dreamer), wekelijks (handmatig review), maandelijks (deep prune).
""", "procedure", ["Dreamer", "DevOpsDaemon", "WaakhuisMonitor", "ConfigAuditor"],
    ["log_management", "disk_cleanup", "maintenance", "data_hygiene"])


# ═══════════════════════════════════════════════════════════════
# CATEGORIE 5: DECISION TREES (10 docs)
# ═══════════════════════════════════════════════════════════════

doc("decision_agent_selection", """
BESLISBOOM: WELKE AGENT KIEZEN?
Gebruikersvraag ontvangen → CentralBrain analyseert:

Code schrijven nodig?
  → JA: Iolaax (bouwer) + Sentinel (security check)
  → Skill nodig? → Artificer (forge-verify-execute)

Informatie opzoeken nodig?
  → Intern beschikbaar? → TheCortex (knowledge graph)
  → Extern nodig? → VoidWalker (web research)

Planning nodig?
  → Complexe taak? → Strategist (decompose → delegate → chain)
  → Simpele taak? → Direct via CentralBrain function calling

Verificatie nodig?
  → Kritiek? → Tribunal (dual-model consensus)
  → Normaal? → HallucinatieSchild (95% Barrière)

Voorspelling nodig?
  → Resources? → OracleEye (resource scaling)
  → Context? → ThePhantom (anticipatory intelligence)
""", "decision_tree", ["CentralBrain", "SwarmEngine", "AdaptiveRouter"],
    ["agent_selection", "routing", "decision_making"])

doc("decision_provider_selection", """
BESLISBOOM: WELKE AI PROVIDER?
Groq beschikbaar + key niet rate-limited?
  → JA: Gebruik Groq (Sovereign Priority x2)
  → RATE LIMITED: Rotate naar reserve key 1→2→3
  → ALLE KEYS OP: Circuit breaker opent

Groq circuit open?
  → NVIDIA NIM beschikbaar? → Gebruik NIM (cost 1, latency 2)
  → Gemini beschikbaar? → Gebruik Gemini (cost 1, latency 2)
  → Ollama lokaal? → Gebruik Ollama (cost 1, latency 3)
  → Niets beschikbaar? → Emergency offline (keyword-based)

Vision taak?
  → Altijd Ollama llava:latest (~4.7 GB VRAM)

Verificatie taak?
  → Tribunal: worker=llama-4-scout, auditor=qwen3-32b
""", "decision_tree", ["CentralBrain", "TaskArbitrator", "ModelRegistry"],
    ["provider_selection", "failover", "sovereign_priority"])

doc("decision_rag_pipeline", """
BESLISBOOM: RAG VERRIJKING
Taak ontvangen voor agent:

1. BlackBox check — bekende failure patterns?
   → JA: Injecteer waarschuwing in context
   → Escalatie level 3+? → BLOKKEER taak

2. VectorStore zoek — relevante documenten?
   → JA: Top 5 resultaten + TruthAnchor verificatie top 3
   → NEE: Ga naar stap 3

3. TheCortex hybrid_search — kennisgraaf expansie?
   → JA: Top 3 resultaten via graaf-relaties
   → NEE: Ga naar stap 4

4. VoidWalker web research — externe informatie?
   → JA: ~1500 chars web context injecteren
   → NEE: Taak uitvoeren zonder extra context

5. Generatieve agent? (Iolaax, Artificer, Weaver, Spark)
   → Sentinel OK? → Bypass RAG verificatie (score 1.0)
   → Sentinel NOT OK? → Blokkeer (score 0.0)
   → Niet-generatief? → Reguliere fact-checking
""", "decision_tree",
    ["CentralBrain", "BlackBox", "TheCortex", "VoidWalker", "HallucinatieSchild"],
    ["rag_pipeline", "knowledge_retrieval", "decision_flow"])

doc("decision_error_response", """
BESLISBOOM: ERROR RESPONSE
Error ontvangen:

Type: ImportError?
  → try/except ImportError fallback — graceful degradatie
  → Log: logger.debug(), NOOIT pass

Type: Rate Limit (429)?
  → Reserve key rotatie → volgende provider → circuit breaker

Type: SQLite Lock?
  → busy_timeout=5000 helpt meestal
  → Stale process? → Check for zombie Python processen

Type: CUDA Segfault?
  → CUDA_VISIBLE_DEVICES="-1" (niet "")
  → GPU exclusief voor Ollama vision

Type: asyncio RuntimeError?
  → asyncio.run() in async def is FATAAL → gebruik await

Type: NetworkX falsy?
  → bool(nx.DiGraph()) is False → altijd 'is not None' gebruiken
""", "decision_tree", ["ErrorTaxonomy", "SelfRepairProtocol", "CentralBrain"],
    ["error_handling", "troubleshooting", "recovery"])

doc("decision_task_category", """
BESLISBOOM: TAAK CATEGORIE TOEWIJZING
SwarmTask ontvangen → categoriseer:

Bevat code keywords (python, functie, class, bug, fix)?
  → categorie: "code" → ModelCapability.CODE

Bevat research keywords (zoek, vind, onderzoek, wat is)?
  → categorie: "research" → ModelCapability.RESEARCH

Bevat analyse keywords (analyseer, vergelijk, evalueer)?
  → categorie: "analyse" → ModelCapability.ANALYSE

Bevat creatief keywords (schrijf, genereer, maak, ontwerp)?
  → categorie: "creatief" → ModelCapability.CREATIEF

Bevat verificatie keywords (check, verifieer, klopt het)?
  → categorie: "verificatie" → ModelCapability.VERIFICATIE

Categorie bepaalt: welke modellen geschikt zijn (capability_match in auction).
""", "decision_tree", ["TaskArbitrator", "SwarmEngine", "CentralBrain"],
    ["task_categorization", "capability_matching", "routing"])

doc("decision_security_gate", """
BESLISBOOM: SECURITY ESCALATIE
Input ontvangen door OmegaGovernor:

Prompt injection gedetecteerd?
  → ROOD: Blokkeer input, log als aanval
  → Alert via Alerter (Telegram + deduplicatie)

PII gedetecteerd (namen, adressen, BSN)?
  → GEEL: Scrub PII, log waarschuwing

Token budget overschreden?
  → GEEL: Truncate input, waarschuw gebruiker

Rate limit bereikt?
  → Cooldown per agent priority (P0=2s tot P5=30s)

Shadow zone actie?
  → ShadowGovernance: ROOD=verboden, GEEL=beperkt, GROEN=toegestaan
  → LOCKDOWN bij 2+ ROOD overtredingen
""", "decision_tree", ["OmegaGovernor", "ShadowGovernance", "Alerter"],
    ["security", "escalation", "threat_response"])

doc("decision_hallucination", """
BESLISBOOM: HALLUCINATIE DETECTIE
AI output ontvangen → HallucinatieSchild beoordeelt:

Generatieve agent + Sentinel OK?
  → BYPASS: Score 1.0 (gegenereerde code kan niet fact-checked worden)

Claim-scoring < 0.35?
  → GEBLOKKEERD: Output wordt niet doorgelaten
  → Reden: te veel onverifieerbare claims

Claim-scoring 0.35-0.55?
  → WAARSCHUWING: Output wordt doorgelaten met caveat
  → Gebruiker ziet waarschuwings-indicator

Claim-scoring >= 0.55?
  → OK: Output wordt doorgelaten
  → Claims zijn verifieerbaar tegen kennisbank

Contradictie gedetecteerd?
  → Downgrade score met 0.2 per contradictie
""", "decision_tree", ["HallucinatieSchild", "TruthAnchor", "CentralBrain"],
    ["hallucination_detection", "output_quality", "verification"])

doc("decision_when_to_swarm", """
BESLISBOOM: WANNEER SWARM VS DIRECT
Gebruikersvraag ontvangen:

Simpele vraag (wie, wat, weer, tijd)?
  → DIRECT: CentralBrain function calling (1 tool)

Complexe vraag (meerdere stappen, onderzoek)?
  → SWARM: SwarmEngine multi-agent pipeline

Tool beschikbaar in 31 app tools?
  → DIRECT: CentralBrain roept tool aan

Geen tool beschikbaar?
  → SWARM: Strategist decompose → agents delegeren

Code generatie nodig?
  → SWARM: Iolaax + Sentinel + Artificer

Multi-provider nodig?
  → GENERAAL MODE: TaskArbitrator model auction
""", "decision_tree", ["CentralBrain", "SwarmEngine", "TaskArbitrator"],
    ["routing_decision", "direct_vs_swarm", "optimization"])

doc("decision_memory_storage", """
BESLISBOOM: WAAR OPSLAAN?
Nieuw gegenereerde informatie:

Conversatie event (vraag/antwoord)?
  → CorticalStack.log_event() (episodic memory)

App state change (fitness, agenda, etc.)?
  → UnifiedMemory.store_event() (vector + event log)

Kennisdocument (markdown, code)?
  → VectorStore.voeg_toe() of TheLibrarian.ingest()

Failure pattern?
  → BlackBox.record_failure() (negative RAG)

User profiel update?
  → TheMirror.reflect() → /data/user_profile.json

System metric?
  → CorticalStack system_stats tabel
  → WaakhuisMonitor latency percentiles
""", "decision_tree", ["CorticalStack", "VectorStore", "UnifiedMemory", "BlackBox"],
    ["data_routing", "storage_decision", "memory_management"])

doc("decision_omega_routing", """
BESLISBOOM: OMEGA TERMINAL ROUTING
Commando ontvangen in Omega Soul terminal:

Bekend commando (help, status, agents, health, keys, etc.)?
  → _ot_dispatch() — directe afhandeling

"omega" getypt?
  → Omega Awakening sequence starten (7 stappen)
  → Alle subsystemen activeren + API server + browser

"search <term>" getypt?
  → RAG search via TheLibrarian/VectorStore

"py <code>" getypt?
  → Python uitvoeren in subprocess

Onbekend commando (vrije tekst)?
  → Omega Mode actief? → Full pipeline (SwarmEngine + alle agents)
  → Omega Mode inactief? → WAV-Loop (CentralBrain alleen)
""", "decision_tree", ["CentralBrain", "SwarmEngine"],
    ["terminal_routing", "command_dispatch", "omega_mode"])


# ═══════════════════════════════════════════════════════════════
# CATEGORIE 6: API & TOOLS (7 docs)
# ═══════════════════════════════════════════════════════════════

doc("api_function_calling", """
API: FUNCTION CALLING (31 App Tools)
CentralBrain ondersteunt 31 tools via Groq function calling.
Elke tool heeft: name, description, parameters (JSON Schema).
Voorbeelden:
  agenda_view — Toon agenda items voor een datum
  calculator — Reken expressie uit
  fitness_log — Log workout
  expense_add — Voeg uitgave toe
  mood_log — Log stemming
  weather_get — Haal weer op
  note_create — Maak notitie
  habit_check — Check habit status
  goal_progress — Bekijk doel voortgang
Definitie: danny_toolkit/brain/app_tools.py (TOOL_DEFINITIONS, 31+ entries).
""", "api_tools", ["CentralBrain", "SwarmEngine"],
    ["function_calling", "tool_usage", "app_integration"])

doc("api_cortical_stack", """
API: CORTICALSTACK INTERFACE
Singleton: get_cortical_stack() — thread-safe.
Methoden:
  log_event(actor, action, source, data) — log episodic event
  get_recent_events(count=N) — haal recente events op
  flush() — forceer pending writes
  backup(compress=True) — maak backup
  restore(path) — herstel van backup
  apply_retention_policy() — oude events opruimen
  get_db_metrics() — database statistieken
Tabellen: episodic_memory, semantic_memory, system_stats.
Optimalisatie: 64 MB cache, 256 MB mmap, WAL mode.
""", "api_tools", ["CorticalStack", "CentralBrain", "Dreamer"],
    ["memory_api", "episodic_memory", "database"])

doc("api_vector_store", """
API: VECTORSTORE INTERFACE
Constructor: VectorStore(embedding_provider, db_file=None)
Methoden:
  voeg_toe([{"id": str, "tekst": str, "metadata": dict}]) — documenten toevoegen
  zoek(query, top_k=5, filter_fn=None, min_score=0.0) — semantic search
  zoek_op_metadata(veld, waarde, exact=True) — metadata filtering
  verwijder(doc_id) — document verwijderen
  wis() — alle documenten wissen
  maak_backup() — JSON backup
  herstel_backup() — backup herstellen
Embeddings: Voyage AI (256d MRL truncation) of TorchGPU fallback.
Persist: JSON-backed (versie 2.0).
""", "api_tools", ["VectorStore", "UnifiedMemory", "TheCortex"],
    ["vector_api", "semantic_search", "embedding"])

doc("api_neural_bus", """
API: NEURALBUS INTERFACE
Singleton: get_bus() — thread-safe met RLock.
Methoden:
  subscribe(event_type, callback) — registreer listener
  publish(event_type, data) — publiceer event
  get_history(event_type) — haal event historie op (deque maxlen=100)
Event Types: EventTypes.WEATHER_UPDATE, HEALTH_STATUS_CHANGE, AGENDA_UPDATE, etc.
BaseApp integratie: LUISTERT_NAAR, PUBLICEERT class vars.
Thread safety: Sync callbacks in ThreadPoolExecutor, async via create_task.
""", "api_tools", ["NeuralBus", "CentralBrain", "ProactiveEngine"],
    ["event_api", "pub_sub", "inter_module_communication"])

doc("api_key_manager", """
API: SMARTKEYMANAGER INTERFACE
Singleton: get_key_manager() — thread-safe.
Methoden:
  get_key(agent_naam) — prioriteit-gebaseerde key selectie
  get_key_for_model(agent_naam, model) — model-aware key
  create_async_client(agent_naam) — AsyncGroq met juiste key
  create_sync_client(agent_naam) — sync Groq client
  create_async_client_for_model(agent_naam, model) — model-aware async
  create_sync_client_for_model(agent_naam, model) — model-aware sync
  registreer_tokens(agent_naam, tekst) — track token usage
  registreer_429(agent_naam) — track rate limit hit
  async_enqueue(agent_naam, model) — pre-flight throttle check
Pool: 12 keys (7 role + 1 fallback + 3 reserve + 1 primary).
""", "api_tools", ["CentralBrain", "Tribunal", "Strategist", "Artificer"],
    ["key_management_api", "rate_limiting", "client_creation"])

doc("api_introspector", """
API: SYSTEMINTROSPECTOR INTERFACE
Singleton: get_introspector() — SystemIntrospector instance.
Methoden:
  discover_modules() — scan 60 modules (brain/core/daemon/root)
  verify_wirings() — check 47 cross-module wirings
  take_snapshot() — volledige systeem snapshot
  get_security_status() — security gates status
  get_api_endpoints() — 31 API endpoints health
Snapshot bevat: totaal_modules, actieve_modules, gezondheid_score, security_status.
Module path resolution: _resolve_module_path() voor multi-package support.
""", "api_tools", ["SystemIntrospector", "CentralBrain", "ConfigAuditor"],
    ["introspection_api", "system_health", "self_awareness"])

doc("api_omega_core", """
API: OMEGACORE INTERFACE
Class: OmegaCore — unified gateway naar alle tiers.
Methoden (callable via CentralBrain function calling):
  system_scan() — volledige tier scan met Introspector
  health_check() — gezondheid alle subsystemen
  agent_status() — status van alle agents
  memory_stats() — CorticalStack + VectorStore metrics
  security_audit() — FileGuard + Governor status
Lazy-loading: Modules worden pas geïmporteerd bij eerste gebruik.
Idempotency: _turn_tools_called set voorkomt dubbele calls per turn.
reset_turn() — aanroepen bij elke nieuwe user query.
""", "api_tools", ["OmegaCore", "CentralBrain", "SystemIntrospector"],
    ["omega_api", "system_management", "unified_gateway"])


# ═══════════════════════════════════════════════════════════════
# INGESTION
# ═══════════════════════════════════════════════════════════════

def main():
    print("=" * 60)
    print("  OMEGA KNOWLEDGE INJECTION — 72 Multi-Functionele Docs")
    print("=" * 60)

    print(f"\n  Documenten voorbereid: {len(OMEGA_DOCS)}")

    # Laad embedder
    print("  Embedder laden...", end=" ", flush=True)
    embedder = get_embedder(gebruik_voyage=False)
    print("OK")

    # Laad vector store
    db_file = Config.DATA_DIR / "brain_memory" / "unified_vectors.json"
    print(f"  VectorStore laden: {db_file}...", end=" ", flush=True)
    store = VectorStore(embedder, db_file=db_file)
    before = len(store.documenten)
    print(f"OK ({before} bestaande docs)")

    # Verwijder eventuele oude omega_kb_ docs (idempotent)
    old_ids = [did for did in store.documenten if did.startswith("omega_kb_")]
    if old_ids:
        print(f"  Oude omega_kb_ docs verwijderen: {len(old_ids)}...", end=" ", flush=True)
        for oid in old_ids:
            store.verwijder(oid)
        print("OK")

    # Injecteer in batches van 10
    print(f"\n  Injectie gestart ({len(OMEGA_DOCS)} docs)...")
    t0 = time.time()
    batch_size = 10
    for i in range(0, len(OMEGA_DOCS), batch_size):
        batch = OMEGA_DOCS[i:i + batch_size]
        store.voeg_toe(batch)
        print(f"    Batch {i // batch_size + 1}/{(len(OMEGA_DOCS) + batch_size - 1) // batch_size}"
              f" — {len(batch)} docs geïnjecteerd")

    elapsed = time.time() - t0
    after = len(store.documenten)
    new_count = after - before + len(old_ids)

    print(f"\n  {'=' * 50}")
    print(f"  RESULTAAT:")
    print(f"    Docs voor:  {before}")
    print(f"    Docs na:    {after}")
    print(f"    Nieuw:      {new_count}")
    print(f"    Tijd:       {elapsed:.1f}s")
    print(f"  {'=' * 50}")

    # Verificatie: zoek test
    print("\n  Verificatie zoektest...")
    results = store.zoek("welke agent moet ik gebruiken voor code generatie", top_k=3)
    for j, r in enumerate(results):
        score = r.get("score", 0)
        doc_id = r.get("id", "?")[:50]
        print(f"    [{j+1}] {doc_id} (score={score:.3f})")

    print(f"\n  OMEGA KNOWLEDGE BASE: {len(OMEGA_DOCS)} multi-functionele docs ACTIEF")
    print("=" * 60)


if __name__ == "__main__":
    main()
