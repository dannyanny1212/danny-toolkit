"""
Test CLI — Sanctuary CLI Verificatie
=====================================

Test de visualisatie-functies en media-integratie
van cli.py en swarm_core.py media generators.

1. render_metrics() — Cipher Market Ticker tabel
2. render_chart_ascii() — DataFrame → ASCII bars
3. render_media() — dispatch naar juiste renderer
4. Media generators — _crypto_metrics, _health_chart,
   _data_chart, _code_media
5. Pipeline integratie — Hub & Spoke met media output

Gebruik: python test_cli.py
"""

import sys
import os
import io
import time

# Windows UTF-8 fix
if os.name == "nt":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

# Voeg project root toe aan path
sys.path.insert(0, os.path.dirname(__file__))

import numpy as np
import pandas as pd
from rich.table import Table
from rich.console import Console

from swarm_core import (
    _crypto_metrics,
    _health_chart,
    _data_chart,
    _code_media,
    _generate_media,
    run_hub_spoke_pipeline,
)
from cli import render_metrics, render_chart_ascii


def test_crypto_metrics():
    """Test 1: _crypto_metrics() structuur."""
    print("\n" + "=" * 60)
    print("  TEST 1: Crypto Metrics Generator")
    print("=" * 60)

    media = _crypto_metrics()
    checks = []

    # Type check
    checks.append((
        "type == 'metrics'",
        media["type"] == "metrics",
    ))

    # Category check
    checks.append((
        "category == 'CRYPTO'",
        media["category"] == "CRYPTO",
    ))

    # 4 metric items
    checks.append((
        "4 metric tickers",
        len(media["metrics"]) == 4,
    ))

    # Elke metric heeft label, value, delta
    all_keys = all(
        "label" in m and "value" in m and "delta" in m
        for m in media["metrics"]
    )
    checks.append((
        "metrics hebben label/value/delta",
        all_keys,
    ))

    # BTC is eerste ticker
    checks.append((
        "BTC is eerste ticker",
        "Bitcoin" in media["metrics"][0]["label"],
    ))

    # Data is een DataFrame met 30 rijen
    checks.append((
        "data DataFrame 30 rijen",
        isinstance(media["data"], pd.DataFrame)
        and len(media["data"]) == 30,
    ))

    # Extra (volume) is een DataFrame
    checks.append((
        "extra DataFrame aanwezig",
        isinstance(media["extra"], pd.DataFrame)
        and len(media["extra"]) == 30,
    ))

    return _print_checks(checks)


def test_health_chart():
    """Test 2: _health_chart() structuur."""
    print("\n" + "=" * 60)
    print("  TEST 2: Health Chart Generator")
    print("=" * 60)

    media = _health_chart()
    checks = []

    checks.append((
        "type == 'area_chart'",
        media["type"] == "area_chart",
    ))

    checks.append((
        "category == 'HEALTH'",
        media["category"] == "HEALTH",
    ))

    checks.append((
        "data DataFrame 24 rijen",
        isinstance(media["data"], pd.DataFrame)
        and len(media["data"]) == 24,
    ))

    checks.append((
        "kolommen: HRV + Hartslag",
        "HRV (ms)" in media["data"].columns
        and "Hartslag" in media["data"].columns,
    ))

    return _print_checks(checks)


def test_data_chart():
    """Test 3: _data_chart() structuur."""
    print("\n" + "=" * 60)
    print("  TEST 3: Data Chart Generator")
    print("=" * 60)

    media = _data_chart()
    checks = []

    checks.append((
        "type == 'bar_chart'",
        media["type"] == "bar_chart",
    ))

    checks.append((
        "category == 'DATA'",
        media["category"] == "DATA",
    ))

    checks.append((
        "6 systeem-metrics",
        len(media["data"]) == 6,
    ))

    expected = {"CPU", "RAM", "Disk", "Net", "GPU", "Cache"}
    checks.append((
        "labels: CPU/RAM/Disk/Net/GPU/Cache",
        set(media["data"].index) == expected,
    ))

    return _print_checks(checks)


def test_code_media():
    """Test 4: _code_media() extractie."""
    print("\n" + "=" * 60)
    print("  TEST 4: Code Media Extractie")
    print("=" * 60)

    checks = []

    # Met code block
    output_met_code = (
        "Hier is de code:\n"
        "```python\nprint('hello')\n```\n"
        "Klaar."
    )
    media = _code_media(output_met_code)
    checks.append((
        "code block gevonden",
        media is not None,
    ))
    checks.append((
        "type == 'code'",
        media["type"] == "code",
    ))
    checks.append((
        "code content correct",
        "print('hello')" in media["code"],
    ))

    # Zonder code block
    media_none = _code_media("Gewone tekst zonder code")
    checks.append((
        "geen code → None",
        media_none is None,
    ))

    return _print_checks(checks)


def test_generate_media_dispatch():
    """Test 5: _generate_media() dispatcher."""
    print("\n" + "=" * 60)
    print("  TEST 5: Media Dispatcher")
    print("=" * 60)

    checks = []

    # CRYPTO → metrics
    m = _generate_media("CRYPTO", "")
    checks.append((
        "CRYPTO → metrics",
        m is not None and m["type"] == "metrics",
    ))

    # HEALTH → area_chart
    m = _generate_media("HEALTH", "")
    checks.append((
        "HEALTH → area_chart",
        m is not None and m["type"] == "area_chart",
    ))

    # DATA → bar_chart
    m = _generate_media("DATA", "")
    checks.append((
        "DATA → bar_chart",
        m is not None and m["type"] == "bar_chart",
    ))

    # CODE met block → code
    m = _generate_media(
        "CODE", "```python\nx = 1\n```"
    )
    checks.append((
        "CODE → code block",
        m is not None and m["type"] == "code",
    ))

    # CASUAL → None
    m = _generate_media("CASUAL", "hallo")
    checks.append((
        "CASUAL → None",
        m is None,
    ))

    return _print_checks(checks)


def test_render_metrics():
    """Test 6: render_metrics() → Rich Table."""
    print("\n" + "=" * 60)
    print("  TEST 6: CLI render_metrics()")
    print("=" * 60)

    media = _crypto_metrics()
    table = render_metrics(media)
    checks = []

    checks.append((
        "retourneert Rich Table",
        isinstance(table, Table),
    ))

    checks.append((
        "3 kolommen",
        len(table.columns) == 3,
    ))

    checks.append((
        "4 rijen (tickers)",
        table.row_count == 4,
    ))

    return _print_checks(checks)


def test_render_chart_ascii():
    """Test 7: render_chart_ascii() → ASCII string."""
    print("\n" + "=" * 60)
    print("  TEST 7: CLI render_chart_ascii()")
    print("=" * 60)

    checks = []

    # Normale DataFrame
    df = pd.DataFrame(
        {"Waarde": [10, 50, 90]},
        index=["A", "B", "C"],
    )
    output = render_chart_ascii(df)
    checks.append((
        "output is string",
        isinstance(output, str),
    ))
    checks.append((
        "bevat bar chars",
        "\u2588" in output,
    ))
    checks.append((
        "bevat kolom labels",
        "Waarde" in output,
    ))

    # Lege DataFrame
    empty_df = pd.DataFrame()
    output_empty = render_chart_ascii(empty_df)
    checks.append((
        "lege df → geen crash",
        isinstance(output_empty, str),
    ))

    # None
    output_none = render_chart_ascii(None)
    checks.append((
        "None → fallback tekst",
        "Geen data" in output_none,
    ))

    # Met titel
    output_title = render_chart_ascii(df, title="Test")
    checks.append((
        "titel wordt getoond",
        "Test" in output_title,
    ))

    return _print_checks(checks)


def test_pipeline_media_integration():
    """Test 8: Hub & Spoke pipeline met media."""
    print("\n" + "=" * 60)
    print("  TEST 8: Pipeline Media Integratie")
    print("=" * 60)

    from contextlib import redirect_stdout
    from danny_toolkit.brain.trinity_omega import (
        PrometheusBrain,
    )

    buf = io.StringIO()
    with redirect_stdout(buf):
        brain = PrometheusBrain()

    checks = []
    logs = []

    def test_callback(msg):
        logs.append(msg)

    # Crypto query → moet media genereren
    buf = io.StringIO()
    with redirect_stdout(buf):
        result, assigned, output, media = (
            run_hub_spoke_pipeline(
                "Bitcoin blockchain analyse",
                brain,
                callback=test_callback,
            )
        )

    checks.append((
        "result is niet None",
        result is not None,
    ))

    checks.append((
        "callback logs ontvangen",
        len(logs) > 0,
    ))

    checks.append((
        "PIPELINE COMPLETE in logs",
        any("COMPLETE" in l for l in logs),
    ))

    checks.append((
        "crypto → media gegenereerd",
        media is not None,
    ))

    if media:
        checks.append((
            "media type is metrics",
            media["type"] == "metrics",
        ))
    else:
        checks.append((
            "media type is metrics",
            False,
        ))

    return _print_checks(checks)


# --- HELPER ---

def _print_checks(checks):
    """Print check resultaten en return True als alles OK."""
    passed = 0
    failed = 0
    for name, ok in checks:
        icon = "[OK]" if ok else "[FAIL]"
        if ok:
            passed += 1
        else:
            failed += 1
        print(f"  {icon} {name}")

    print(
        f"\n  Resultaat: {passed}/{passed + failed}"
        f" geslaagd"
    )
    return failed == 0


def main():
    """Draai alle CLI tests."""
    print()
    print("=" * 60)
    print("  CLI TEST — Sanctuary CLI Verificatie")
    print("=" * 60)

    start = time.time()
    results = []

    # Unit tests (geen brain nodig)
    results.append((
        "Crypto Metrics",
        test_crypto_metrics(),
    ))
    results.append((
        "Health Chart",
        test_health_chart(),
    ))
    results.append((
        "Data Chart",
        test_data_chart(),
    ))
    results.append((
        "Code Media",
        test_code_media(),
    ))
    results.append((
        "Media Dispatcher",
        test_generate_media_dispatch(),
    ))
    results.append((
        "CLI render_metrics",
        test_render_metrics(),
    ))
    results.append((
        "CLI render_chart_ascii",
        test_render_chart_ascii(),
    ))

    # Integratie test (laadt brain)
    results.append((
        "Pipeline Integratie",
        test_pipeline_media_integration(),
    ))

    elapsed = time.time() - start
    passed = sum(1 for _, ok in results if ok)
    total = len(results)

    print()
    print("=" * 60)
    print("  EINDRESULTAAT")
    print("=" * 60)
    for name, ok in results:
        icon = "[OK]" if ok else "[FAIL]"
        print(f"  {icon} {name}")
    print(
        f"\n  {passed}/{total} tests geslaagd"
        f" ({elapsed:.1f}s)"
    )
    print("=" * 60)

    if passed < total:
        print("\n  SOMMIGE TESTS GEFAALD!")
        sys.exit(1)
    else:
        print("\n  ALLE TESTS GESLAAGD!")


if __name__ == "__main__":
    main()
