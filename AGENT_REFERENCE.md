# AGENT_REFERENCE.md

# Danny Toolkit v5 – Agent Reference

## 1. Architectuur
Agents draaien bovenop:
- SwarmEngine
- PrometheusBrain
- Governor

## 2. Kernagents
### CodeAgent
- Code genereren, refactoren, analyseren

### RAGAgent / ResearchAgent
- Kennis opvragen via MEMEX

### VisionAgent / PixelEyeAgent
- Afbeeldingen analyseren

### OSAgent
- OS‑automatisatie

### QuestAgent
- Diagnostische workflows

### OracleAgent
- Self‑healing

## 3. Agent Lifecycle
1. SwarmEngine selecteert agents
2. PrometheusBrain wijst rol + model toe
3. Governor valideert input
4. Agent draait taak
5. Resultaat terug naar SwarmEngine
6. SwarmEngine combineert outputs
