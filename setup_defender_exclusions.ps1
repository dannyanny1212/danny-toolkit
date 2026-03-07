# Phase 50: Windows Defender Exclusions + PYTHONUTF8
# RUN AS ADMIN: Right-click → Run as Administrator
# Of: Start-Process powershell -ArgumentList '-File setup_defender_exclusions.ps1' -Verb RunAs

Write-Host "=== Phase 50: Windows OS Optimalisaties ===" -ForegroundColor Cyan

# 1. Defender Path Exclusions (stopt file scanning op hot paths)
$paths = @(
    "C:\Users\danny\danny-toolkit\",
    "C:\Users\danny\danny-toolkit\venv311\",
    "C:\Users\danny\danny-toolkit\data\"
)
foreach ($p in $paths) {
    try {
        Add-MpExclusion -ExclusionPath $p -ErrorAction Stop
        Write-Host "[OK] Exclusion: $p" -ForegroundColor Green
    } catch {
        Write-Host "[SKIP] $p - $($_.Exception.Message)" -ForegroundColor Yellow
    }
}

# 2. Defender Extension Exclusions
$exts = @(".py", ".db", ".json")
try {
    Add-MpExclusion -ExclusionExtension $exts -ErrorAction Stop
    Write-Host "[OK] Extension exclusions: $($exts -join ', ')" -ForegroundColor Green
} catch {
    Write-Host "[SKIP] Extensions - $($_.Exception.Message)" -ForegroundColor Yellow
}

# 3. PYTHONUTF8 system-wide
[System.Environment]::SetEnvironmentVariable("PYTHONUTF8", "1", "User")
Write-Host "[OK] PYTHONUTF8=1 (User level)" -ForegroundColor Green

# 4. Verify
Write-Host "`n=== Verificatie ===" -ForegroundColor Cyan
$prefs = Get-MpPreference
Write-Host "Exclusion Paths:" -ForegroundColor White
$prefs.ExclusionPath | ForEach-Object { Write-Host "  $_" }
Write-Host "Exclusion Extensions:" -ForegroundColor White
$prefs.ExclusionExtension | ForEach-Object { Write-Host "  $_" }
Write-Host "PYTHONUTF8: $([System.Environment]::GetEnvironmentVariable('PYTHONUTF8', 'User'))" -ForegroundColor White

Write-Host "`n[DONE] Herstart terminal voor PYTHONUTF8 effect." -ForegroundColor Green
Read-Host "Druk Enter om te sluiten"
