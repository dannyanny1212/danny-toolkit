"""
Phase 20 Tests — Web GUI (FastAPI + HTMX)
==========================================
Verifieert dat alle template/static bestanden bestaan,
routes correct reageren, en auth werkt op metrics.

6 tests, standalone uitvoerbaar: python test_phase20.py
"""

import io
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

passed = 0
failed = 0


def check(label: str, condition: bool):
    global passed, failed
    if condition:
        passed += 1
        print(f"  ✅ {label}")
    else:
        failed += 1
        print(f"  ❌ {label}")


print("=" * 60)
print("  Phase 20: Web GUI (FastAPI + HTMX)")
print("=" * 60)

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
WEB_DIR = os.path.join(PROJECT_ROOT, "danny_toolkit", "web")

# ── Test 1: Template files bestaan ──
print("\n[1] Template bestanden bestaan")
templates = [
    "templates/base.html",
    "templates/dashboard.html",
    "templates/partials/agent_grid.html",
    "templates/partials/governor.html",
    "templates/partials/rate_limits.html",
    "templates/partials/cortex_stats.html",
    "templates/partials/event_feed.html",
]
for t in templates:
    path = os.path.join(WEB_DIR, t)
    check(f"{t} exists", os.path.isfile(path))

# ── Test 2: Static CSS bestaat ──
print("\n[2] Static CSS bestaat")
css_path = os.path.join(WEB_DIR, "static", "style.css")
check("static/style.css exists", os.path.isfile(css_path))
if os.path.isfile(css_path):
    with open(css_path, "r", encoding="utf-8") as f:
        css_content = f.read()
    check("CSS bevat dark theme vars", "--bg-primary" in css_content)
    check("CSS bevat responsive media query", "@media" in css_content)

# ── Test 3-6: FastAPI routes testen via TestClient ──
print("\n[3-6] FastAPI route tests")
try:
    from fastapi.testclient import TestClient
    from fastapi_server import app

    client = TestClient(app)

    # Test 3: Root redirects to /ui/
    print("\n[3] Root redirect naar /ui/")
    resp = client.get("/", follow_redirects=False)
    check("GET / returns 307 redirect", resp.status_code == 307)
    check("Redirect location bevat /ui/", "/ui/" in resp.headers.get("location", ""))

    # Test 4: Dashboard returns HTML
    print("\n[4] Dashboard retourneert HTML")
    resp = client.get("/ui/")
    check("GET /ui/ returns 200", resp.status_code == 200)
    check("Response bevat 'OMEGA Dashboard'", "OMEGA Dashboard" in resp.text)
    check("Response bevat htmx script", "htmx.org" in resp.text)

    # Test 5: Partials return HTML
    print("\n[5] Partials retourneren HTML")
    for partial in ["/ui/partials/agents", "/ui/partials/governor",
                    "/ui/partials/rate-limits", "/ui/partials/cortex"]:
        resp = client.get(partial)
        check(f"GET {partial} returns 200", resp.status_code == 200)

    # Test 6: Metrics requires auth
    print("\n[6] Metrics endpoint vereist auth")
    resp = client.get("/api/v1/metrics")
    check("GET /api/v1/metrics without key returns 422/401",
          resp.status_code in (401, 422))

    # Met correcte key
    import fastapi_server
    key = fastapi_server.FASTAPI_SECRET_KEY
    resp = client.get("/api/v1/metrics", headers={"X-API-Key": key})
    check("GET /api/v1/metrics with key returns 200", resp.status_code == 200)
    data = resp.json()
    check("Metrics bevat 'uptime'", "uptime" in data)

except ImportError as e:
    print(f"  ⚠️  Kan TestClient niet laden: {e}")
    print("  Installeer: pip install httpx")
    for _ in range(10):
        failed += 1

# ── Resultaat ──
print(f"\n{'=' * 60}")
total = passed + failed
print(f"  Resultaat: {passed}/{total} checks geslaagd")
if failed == 0:
    print("  🏆 Phase 20: ALL CHECKS PASSED")
else:
    print(f"  ⚠️  {failed} check(s) gefaald!")
print(f"{'=' * 60}")

sys.exit(0 if failed == 0 else 1)
