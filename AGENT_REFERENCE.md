# AGENT_REFERENCE.md

# Danny Toolkit v5 – Agent Reference

Dit document beschrijft de belangrijkste agents, hun rol en hun typische gebruik.

## 1. Architectuur

Agents draaien bovenop:

- SwarmEngine (orchestratie)
- PrometheusBrain (rol/fallback)
- Governor (veiligheid)

## 2. Kernagents

### CodeAgent
- Rol: Code genereren, refactoren, analyseren
- Input: Beschrijving, bestaande code, foutmeldingen
- Output: Python‑code, uitleg, diffs

### RAGAgent / ResearchAgent
- Rol: Kennis opvragen via MEMEX
- Input: Vraag in natuurlijke taal
- Output: Samenvatting + bronnen

### VisionAgent / PixelEyeAgent
- Rol: Afbeeldingen analyseren
- Input: Image + prompt
- Output: Detecties, verificaties

### OSAgent
- Rol: OS‑automatisatie
- Input: Taakbeschrijving
- Output: Acties / logs

### QuestAgent
- Rol: Diagnostische workflows
- Output: Stappenplan, status

### OracleAgent
- Rol: Self‑healing
- Output: Diagnose + fix‑voorstel

## 3. Agent Lifecycle

1. SwarmEngine selecteert agents
2. PrometheusBrain wijst rol + model toe
3. Governor valideert input
4. Agent draait taak
5. Resultaat terug naar SwarmEngine
6. SwarmEngine combineert outputs
