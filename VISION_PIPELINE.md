# VISION_PIPELINE.md

# Danny Toolkit v5 – Vision Pipeline (PixelEye)

Dit document beschrijft de vision‑pipeline van PixelEye.

## 1. Doel

- Afbeeldingen analyseren
- UI‑states herkennen
- Visuele verificatie via Logic Gates

## 2. Flow

1. Input: afbeelding + prompt
2. Pre‑processing (resizing, normalisatie)
3. Vision Model (LLaVA)
4. Visual State Manager
5. Logic Gate verificatie
6. Output terug naar SwarmEngine

## 3. Gebruiksscenario's

- UI‑validatie
- Visuele debugging
- OS‑automatisatie
- Verificatie van success/failure op schermniveau

## 4. Beperkingen

- Afhankelijk van modelkwaliteit
- Latentie hoger dan tekst‑only
- Niet geschikt voor ultra‑fijne pixel‑nauwkeurigheid
