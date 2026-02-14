# PIXEL_EYE_INTERNALS.md

# Danny Toolkit v5 – PixelEye Internals

Dit document beschrijft de interne werking van PixelEye, het vision‑subsysteem van Danny Toolkit v5.

## 1. Overzicht

PixelEye is het visuele analysemodule dat afbeeldingen verwerkt, UI‑states herkent en visuele verificatie uitvoert via logic gates.
Het wordt gebruikt door VisionAgent, OSAgent en diagnostische workflows.

## 2. Componenten

- Preprocessor
  Verantwoordelijk voor resizing, normalisatie en kleurcorrectie.

- Vision Model
  LLaVA‑gebaseerd model voor beeldinterpretatie.

- Visual State Manager
  Houdt UI‑states bij en vergelijkt deze met verwachte patronen.

- Logic Gate Engine
  Voert conditionele checks uit zoals:
  - element aanwezig
  - tekst zichtbaar
  - kleur binnen tolerantie
  - state match

## 3. Pipeline

1. Afbeelding ontvangen
2. Preprocessing
3. Vision Model extracteert:
   - objecten
   - tekst
   - UI‑elementen
   - globale beschrijving
4. Visual State Manager vergelijkt met bekende states
5. Logic Gates bepalen pass/fail
6. Resultaat terug naar SwarmEngine

## 4. Gebruiksscenario's

- UI‑validatie
- Automatisatie van OS‑taken
- Visuele debugging
- Verificatie van success/failure op schermniveau

## 5. Beperkingen

- Afhankelijk van modelkwaliteit
- Niet geschikt voor pixel‑nauwkeurige taken
- Latentie hoger dan tekst‑only workflows
