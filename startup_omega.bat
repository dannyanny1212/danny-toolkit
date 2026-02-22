@echo off
title OMEGA STARTUP — Danny Toolkit
color 0A
echo ============================================================
echo   OMEGA SOVEREIGN CORE — Startup Sequence
echo ============================================================
echo.

:: Wait for Ollama to be ready (auto-starts via Startup shortcut)
echo [1/4] Wachten op Ollama...
:wait_ollama
curl -s http://localhost:11434/api/tags >nul 2>&1
if errorlevel 1 (
    timeout /t 2 /noplay >nul
    goto wait_ollama
)
echo   OK  Ollama online

:: Warm up llava into VRAM
echo [2/4] LLaVA laden in VRAM...
curl -s http://localhost:11434/api/generate -d "{\"model\": \"llava:latest\", \"prompt\": \"ready\", \"stream\": false}" >nul 2>&1
echo   OK  LLaVA geladen (~4.7 GB VRAM)

:: Activate venv311
echo [3/4] venv311 activeren...
call C:\Users\danny\danny-toolkit\venv311\Scripts\activate.bat
echo   OK  Python venv311 actief

:: GPU status
echo [4/4] GPU Status:
echo.
nvidia-smi --query-gpu=name,memory.used,memory.total,temperature.gpu,power.draw --format=csv,noheader
echo.
echo ============================================================
echo   OMEGA READY — Alle systemen operationeel
echo ============================================================
echo.

:: Keep window open with GPU monitor loop (refresh every 30s)
echo GPU Monitor actief (elke 30s, Ctrl+C om te stoppen)
echo.
:monitor
echo [%time%] GPU:
nvidia-smi --query-gpu=memory.used,memory.total,temperature.gpu,power.draw --format=csv,noheader,nounits
timeout /t 30 /noplay >nul
goto monitor
