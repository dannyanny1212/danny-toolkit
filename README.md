# Danny Toolkit

Unified Python Toolkit met AI/RAG systemen en standalone apps.

## Installatie

```bash
git clone https://github.com/dannyanny1212/danny-toolkit.git
cd danny-toolkit
pip install -r requirements.txt
```

## API Keys (optioneel)

```bash
# Groq (GRATIS - aanbevolen)
set GROQ_API_KEY=gsk_...

# Claude (betaald)
set ANTHROPIC_API_KEY=sk-ant-...

# Voyage Embeddings (optioneel)
set VOYAGE_API_KEY=...
```

Groq API key aanmaken: https://console.groq.com/keys

## Gebruik

```bash
python main.py
```

## Applicaties

| # | App | Beschrijving |
|---|-----|--------------|
| 1 | Boodschappenlijst | Items toevoegen/verwijderen met opslag |
| 2 | Slimme Rekenmachine | Veilige expressie evaluatie |
| 3 | Virtueel Huisdier | Tamagotchi-style pet met state management |
| 4 | Schatzoek Game | Grid-based treasure hunting game |
| 5 | Code Analyse | Python code statistieken en analyse |

## AI Systemen

| # | App | Beschrijving |
|---|-----|--------------|
| 6 | Mini-RAG Demo | Simpele RAG demonstratie |
| 7 | Production RAG | Volledige RAG met embeddings en vector DB |
| 8 | Nieuws Agent | Multi-agent nieuws analyse systeem |
| 9 | Weer Agent | Agentic Loop demonstratie |
| 10 | Claude Chat | Interactieve chat met Groq/Claude |

## Project Structuur

```
danny-toolkit/
├── main.py                 # Entry point
├── requirements.txt        # Dependencies
├── danny_toolkit/
│   ├── launcher.py         # Hoofdmenu
│   ├── core/               # Gedeelde infrastructure
│   │   ├── config.py       # Configuratie & API keys
│   │   ├── utils.py        # Hulpfuncties
│   │   ├── embeddings.py   # Embedding providers
│   │   ├── vector_store.py # Vector database
│   │   ├── document_processor.py
│   │   └── generator.py    # LLM API (Groq/Claude)
│   ├── apps/               # Standalone apps
│   └── ai/                 # AI/RAG systemen
└── data/                   # Data opslag
```

## Technologieën

- **LLM**: Groq (Llama 3.3 70B) of Claude
- **Embeddings**: Hash-based of Voyage AI
- **Vector DB**: JSON-based met cosine similarity
- **RAG**: Retrieval-Augmented Generation

## Licentie

MIT License

## Auteur

Danny (danny.laurent1988@gmail.com)
