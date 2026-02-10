# PROJECT OMEGA: The Danny Toolkit v5

> *"Not just a Chatbot. An Autonomous Digital Organism."*

Project Omega is een geavanceerd, lokaal draaiend AI Swarm System.
Het overstijgt standaard chatbots door actieve interactie met het
besturingssysteem, visuele waarneming, en diepgaand geheugenbeheer.

Gebouwd op **Swarm Engine v5.0**: Een asynchrone, object-georienteerde
architectuur voor parallelle agent-executie.

---

## Key Capabilities

| Module | Functie | Beschrijving |
|--------|---------|--------------|
| Prometheus Brain | Intelligence | Hybride LLM-routing (Groq 70b -> Llama 8b -> Ollama Lokaal) met automatische fallback. |
| Swarm Engine v5 | Orchestration | Async/Await architectuur. Meerdere specialisten (bv. Coder + Search) werken tegelijkertijd. |
| Memex RAG | Knowledge | "Plan-Search-Cite" protocol. Zoekt in lokale PDF's/Code en episodisch geheugen. Citeert bronnen expliciet. |
| Project Oculus | Vision | Pixel Agent. Kan het scherm zien (screenshots) en analyseren via LLaVA 7B. |
| Project Kinesis | Action | Legion Agent. Bestuurt muis & toetsenbord. Opent apps, typt tekst en voert systeemtaken uit. |
| Heartbeat Daemon | Life | Autonoom achtergrondproces dat op eigen initiatief taken uitvoert zonder user input. |

---

## Architecture

Het systeem gebruikt een Hub & Spoke model met een centrale asynchrone
event loop.

```
User / Daemon
    |
    v
Swarm Engine v5 (asyncio.gather)
    |
    v
Nexus Router (keyword multi-intent)
    |
    +---> Iolaax Agent (Code)
    +---> Memex Agent (Knowledge)
    |       +---> ChromaDB (Vector Store)
    |       +---> CorticalStack (SQLite)
    |       +---> Navigator (Web Fallback)
    +---> Legion Agent (OS Control)
    |       +---> KineticUnit (PyAutoGUI)
    +---> Pixel Agent (Vision)
    |       +---> LLaVA 7B (Ollama)
    +---> Cipher Agent (Finance)
    +---> Vita Agent (Health)
    +---> Oracle Agent (Reasoning)
    +---> Echo Agent (Fast-Track)
    |
    v
List[SwarmPayload] --> Streamlit / CLI / Daemon
```

---

## Installation & Setup

### 1. Prerequisites

- Python 3.10+
- [Ollama](https://ollama.ai) (voor lokaal draaien van Llama3 & LLaVA)
- Git

### 2. Installatie

```bash
git clone https://github.com/dannyanny1212/danny-toolkit.git
cd danny-toolkit
pip install -r requirements.txt
```

### 3. Modellen

Zorg dat Ollama de juiste modellen heeft voor fallback en vision:

```bash
ollama pull llama3.2:3b   # Lokale fallback
ollama pull llava          # Project Oculus (Vision)
```

### 4. Configuratie (.env)

```ini
GROQ_API_KEY=gsk_...
ANTHROPIC_API_KEY=sk-ant-...
```

Groq API key aanmaken: https://console.groq.com/keys

---

## Usage

### The Launcher (Central Command)

Start alles vanuit een menu:

```bash
python launcher.py
```

Kies optie **42** voor de Streamlit GUI of **1** voor de Terminal Interface.

### Feed The Mind (RAG Ingest)

Om documenten (PDF, TXT, PY) aan het brein toe te voegen:

1. Sleep bestanden naar `data/rag/documenten/` (of gebruik de UI uploader).
2. Run de librarian:

```bash
python ingest.py
```

### Start The Daemon (Background Mode)

Om het systeem autonoom te laten werken:

```bash
python daemon_heartbeat.py
```

De Daemon logt zijn activiteiten in de terminal en kan zelfstandig
taken uitvoeren.

---

## The Agent Roster

Elke agent is een gespecialiseerde Python class in `swarm_engine.py`.

| Agent | Rol | Beschrijving |
|-------|-----|--------------|
| **NEXUS** | Router | De verkeersleider. Bepaalt wie de taak moet doen. |
| **IOLAAX** | Engineer | Code, logica en complexe berekeningen. |
| **CIPHER** | Finance | Crypto, aandelen en blockchain data. |
| **MEMEX** | Archivist | Beheert kennis. Combineert Vector Search met History. |
| **PIXEL** | Eye | Multimodaal. Kan het scherm lezen via LLaVA 7B vision. |
| **LEGION** | Operator | Systeemautomatisering. **FAILSAFE=True**: muis naar linkerbovenhoek = noodstop. |
| **NAVIGATOR** | Search | Web search fallback bij knowledge gaps. |
| **ORACLE** | Reasoning | Diep nadenken, filosofie, hypotheses. |
| **VITA** | Health | Gezondheid, biometrics, HRV data. |
| **SPARK** | Creative | Brainstorm, ideeen, kunst. |
| **SENTINEL** | Security | Beveiliging, audits, threat analysis. |
| **ECHO** | Interface | Fast-track smalltalk (regex, geen AI nodig). |

---

## Directory Structure

```
danny-toolkit/
|-- swarm_engine.py          # The Core: v5.0 Async Engine & Agent Classes
|-- kinesis.py               # De "Handen" (PyAutoGUI wrappers) voor Legion
|-- ingest.py                # De "Maag" (PDF verwerking & Vectorisatie)
|-- daemon_heartbeat.py      # Het "Hart" (Scheduling & Autonomie)
|-- sanctuary_ui.py          # Het "Gezicht" (Streamlit Frontend)
|-- cli.py                   # Het "Oor" (Rich Terminal Interface)
|-- launcher.py              # Central Command (Rich Dashboard)
|-- danny_toolkit/
|   |-- brain/
|   |   |-- trinity_omega.py # PrometheusBrain + CosmicRole Federation
|   |   |-- cortical_stack.py# Episodisch geheugen (SQLite)
|   |   +-- governor.py      # Circuit breaker & rate limiting
|   +-- apps/                # 52 standalone applicaties
|-- data/
|   |-- rag/
|   |   |-- chromadb/        # Lange-termijn geheugen (Vector Store)
|   |   +-- documenten/      # Bronbestanden voor ingest
|   |-- cortical_stack.db    # Episodisch geheugen (SQL)
|   +-- plots/               # Screenshots en gegenereerde media
+-- tests/
    +-- test_swarm_engine.py  # 8 tests, 59 checks
```

---

## Safety Protocols

- **Governor**: Circuit-breaker in PrometheusBrain voorkomt API-spam
  en kosten-overschrijding.
- **Legion Kill-Switch**: Muis naar (0,0) (linkerbovenhoek) stopt
  direct alle fysieke automatisering.
- **Local-First**: Kennis (RAG) verlaat de machine niet (tenzij
  cloud-LLM wordt gebruikt voor inference).
- **AI Fallback Keten**: Groq 70b -> Groq 8b -> Ollama lokaal ->
  Anthropic. Voorkomt single point of failure.

---

## Licentie

MIT License

## Auteur

Built by Danny. Powered by Silicon & Starlight. Est. 2024
