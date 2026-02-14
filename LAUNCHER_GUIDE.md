# LAUNCHER_GUIDE.md

# Danny Toolkit v5 – Launcher Guide

Dit document beschrijft hoe de toolkit wordt gestart, welke entrypoints bestaan en hoe subsystemen worden geactiveerd.

## 1. Hoofd-entrypoints

### CLI Launcher
Commando: python cli.py
- Interactieve CLI
- Ondersteunt commands, agents, workflows

### FastAPI Server
Commando: python fastapi_server.py
- REST-API
- Geschikt voor integraties en externe tools

### Sanctuary UI
Commando: python sanctuary_ui.py
- Lokale desktop-achtige interface
- Visualisatie van state, logs, agents

### Telegram Bot
Commando: python telegram_bot.py
- Chat-interface
- Beperkte OS-acties

## 2. Configuratie

- .env voor API-keys
- config/ voor model-instellingen
- data/ voor persistentie

## 3. Subsystem Activation

- MEMEX start automatisch bij RAG-queries
- PixelEye start bij vision-prompts
- Quest System start bij diagnostische taken
- Governor draait altijd als safety-laag

## 4. Logging

- data/logs/engine.log
- data/logs/agents.log
- data/logs/memex.log

## 5. Troubleshooting

- Check .env
- Check permissies in data/
- Check model-keys
- Herstart FastAPI bij model-wijzigingen
