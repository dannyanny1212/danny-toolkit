@echo off
color 0D
echo ===================================================
echo   OMEGA SOVEREIGN v6.1 - INITIALIZING ENVIRONMENT
echo ===================================================

:: 1. Ga naar de juiste map
cd /d "C:\Users\danny\danny-toolkit"

:: 2. Activeer de veilige virtuele omgeving (venv311)
call "venv311\Scripts\activate.bat"
echo [OK] venv311 geactiveerd. CUDA isolatie actief.

:: 3. Start het dashboard
echo [OK] Starten van Sovereign Dashboard...
python sovereign_app.py

:: 4. Houd het venster open als er een crash is
pause
